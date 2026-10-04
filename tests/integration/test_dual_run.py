"""Dual run into Spanner (ADR-0019 §7, design brief phase 3).

The primary keeps its ledger and Neo4j graph; Spanner (emulator) is the
secondary. The ledger is copied, then mirrored while new events keep
arriving; each side's real projection worker builds its own graph; the
comparison must report zero divergence across ledger, graph and
retrieval.

The primary ledger is the memory backend: it implements the same
``EventLog`` port as Redis (both pass ``tests/conformance``), and Redis
Stack is not assumed to be available. Needs Neo4j (``CG_NEO4J_*``) and
the emulator (``CG_SPANNER_EMULATOR_HOST``); skipped otherwise.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from context_graph.adapters.registry import Stores, open_stores
from context_graph.migration.__main__ import target_settings
from context_graph.migration.compare import compare_graphs, compare_logs, compare_retrieval
from context_graph.migration.mirror import LogMirror
from context_graph.settings import Settings
from context_graph.worker.projection import ProjectionConsumer
from tests.fixtures.events import make_event

if TYPE_CHECKING:
    from context_graph.domain.models import Event

pytestmark = pytest.mark.integration

PRIMARY_PORTS = {
    "EVENT_LOG": "memory",
    "SUBSCRIPTION": "memory",
    "KEYWORD_INDEX": "memory",
    "GRAPH": "neo4j",
    "VECTOR_INDEX": "neo4j",
}


def _session(session_id: str, count: int, start: datetime) -> list[Event]:
    """A session whose events chain through parent_event_id (CAUSED_BY)."""
    events: list[Event] = []
    for index in range(count):
        events.append(
            make_event(
                session_id=session_id,
                occurred_at=start + timedelta(seconds=index),
                parent_event_id=events[-1].event_id if events else None,
            )
        )
    return events


class _Projector:
    """One projection worker per side, kept running like a deployed one.

    The worker keeps each session's last event in memory to draw FOLLOWS
    edges, so restarting it between phases would change the graph.
    """

    def __init__(self, stores: Stores, settings: Settings) -> None:
        group = settings.consumer.group_projection
        self._consumer = ProjectionConsumer(
            subscription=stores.subscription(group, "projection-1"),
            event_log=stores.event_log,
            graph_store=stores.graph,
            settings=settings,
        )
        self._probe = stores.subscription(group, "drain-probe")
        self._task = asyncio.create_task(self._consumer.run())

    async def drained(self) -> None:
        """Wait until the group has nothing undelivered or unacknowledged.

        The worker flushes its micro-batch only when a later delivery
        arrives (or on stop), so an idle tail is flushed here explicitly.
        """
        for _ in range(500):
            await asyncio.sleep(0.05)
            if await self._probe.lag() == 0:
                await self._consumer._flush_buffer()
                if not await self._consumer._subscription.delivery_counts(100):
                    return
        msg = "projection did not drain"
        raise AssertionError(msg)

    async def stop(self) -> None:
        self._consumer.stop()
        await asyncio.wait_for(self._task, timeout=10)


@pytest.fixture()
async def dual_stores(monkeypatch: pytest.MonkeyPatch) -> tuple[Settings, Stores, Stores]:
    emulator = os.environ.get("CG_SPANNER_EMULATOR_HOST")
    if not emulator:
        pytest.skip("Spanner emulator not configured (CG_SPANNER_EMULATOR_HOST)")
    pytest.importorskip("google.cloud.spanner")
    for port, backend in PRIMARY_PORTS.items():
        monkeypatch.setenv(f"CG_STORAGE_{port}", backend)
    monkeypatch.setenv("CG_SPANNER_DATABASE", f"dual{uuid4().hex[:12]}")
    monkeypatch.setenv("CG_SPANNER_CREATE_IF_MISSING", "true")
    monkeypatch.setenv("CG_CONSUMER_BLOCK_TIMEOUT_MS", "20")
    settings = Settings()

    primary = await open_stores(settings, prepare_ingest=True)
    try:
        reachable = await asyncio.wait_for(primary.graph.health_ping(), timeout=5)
    except Exception:  # noqa: BLE001
        reachable = False
    if not reachable:
        await primary.close()
        pytest.skip("Neo4j unreachable")
    await primary.graph.delete_all(confirm=True)  # type: ignore[attr-defined]
    secondary = await open_stores(target_settings(settings, "spanner"), prepare_ingest=True)
    try:
        yield settings, primary, secondary
    finally:
        await primary.graph.delete_all(confirm=True)  # type: ignore[attr-defined]
        with contextlib.suppress(Exception):
            await asyncio.to_thread(secondary.event_log.database.drop)  # type: ignore[attr-defined]
        await primary.close()
        await secondary.close()


async def test_copy_then_mirror_has_zero_divergence(
    dual_stores: tuple[Settings, Stores, Stores],
) -> None:
    settings, primary, secondary = dual_stores
    start = datetime.now(UTC) - timedelta(hours=1)

    # -- history: the primary's hot window before migration ------------------
    history = [e for s in range(4) for e in _session(f"hist-{s}-{uuid4().hex[:6]}", 5, start)]
    for event in history:
        await primary.event_log.append(event, payload={"text": f"turn {event.event_id}"})
    primary_projection = _Projector(primary, settings)
    await primary_projection.drained()

    # -- copy ------------------------------------------------------------------
    mirror = LogMirror(primary.event_log, secondary.event_log, batch_size=7)  # type: ignore[arg-type]
    report = await mirror.copy_once()
    assert report.imported == len(history)
    secondary_projection = _Projector(secondary, settings)

    # -- dual run: the primary keeps taking events; the mirror follows ---------
    stopping = asyncio.Event()
    mirror_task = asyncio.create_task(
        LogMirror(primary.event_log, secondary.event_log, batch_size=7).run(  # type: ignore[arg-type]
            poll_interval_s=0.05, should_stop=stopping.is_set
        )
    )
    live_start = start + timedelta(minutes=30)
    live = [e for s in range(2) for e in _session(f"live-{s}-{uuid4().hex[:6]}", 6, live_start)]
    # A late event in a history session: it must follow that session's events
    live.append(
        make_event(
            session_id=history[-1].session_id,
            occurred_at=live_start,
            parent_event_id=history[-1].event_id,
        )
    )
    for event in live:
        await primary.event_log.append(event, payload={"text": f"turn {event.event_id}"})
        await asyncio.sleep(0.01)
    total = len(history) + len(live)
    for _ in range(400):
        if await secondary.event_log.stream_length() == total:  # type: ignore[attr-defined]
            break
        await asyncio.sleep(0.05)
    stopping.set()
    assert await asyncio.wait_for(mirror_task, timeout=30) == len(live)

    # -- each side has projected its own ledger --------------------------------
    await primary_projection.drained()
    await secondary_projection.drained()
    await primary_projection.stop()
    await secondary_projection.stop()

    # -- soak check: zero divergence -------------------------------------------
    ledger = await compare_logs(primary.event_log, secondary.event_log)
    graph = await compare_graphs(primary.graph, secondary.graph, sample_sessions=0)
    retrieval = await compare_retrieval(primary.graph, secondary.graph, sample_sessions=0)

    assert ledger.ok, ledger.as_dict()
    assert graph.ok, graph.as_dict()
    assert retrieval.ok, retrieval.as_dict()
    assert ledger.checked["ledger.events"] == total
    assert "ledger.native_in_target" not in ledger.checked
    assert graph.checked["graph.events_compared"] == total
    assert retrieval.checked["retrieval.context"] == 6
    assert retrieval.checked["retrieval.lineage"] == total - 6
    assert not await secondary.event_log.has_native_events()  # type: ignore[attr-defined]
