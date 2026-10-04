"""Ledger copy, mirror and comparison (ADR-0019 §7, brief phase 3).

Runs memory-to-memory: the tool uses ports only, so these pin its logic;
tests/integration/test_dual_run.py runs it into Spanner.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.domain.models import Event
from context_graph.domain.projection import project_event
from context_graph.migration.__main__ import target_settings
from context_graph.migration.compare import compare_graphs, compare_logs, compare_retrieval
from context_graph.migration.mirror import LogMirror, MirrorRefusedError
from context_graph.ports.event_log import ImportedEvent
from context_graph.settings import Settings
from tests.fixtures.events import make_event


def _session_events(session_id: str, count: int) -> list[Event]:
    base = datetime.now(UTC) - timedelta(minutes=count)
    events: list[Event] = []
    for index in range(count):
        events.append(
            make_event(
                session_id=session_id,
                occurred_at=base + timedelta(minutes=index),
                parent_event_id=events[-1].event_id if events else None,
            )
        )
    return events


async def _seed(log: MemoryEventLog, sessions: int = 3, per_session: int = 4) -> list[Event]:
    events: list[Event] = []
    for s in range(sessions):
        session_events = _session_events(f"session-{s}", per_session)
        for event in session_events:
            await log.append(event, payload={"text": str(event.event_id)})
        events.extend(session_events)
    return events


async def _project(log: MemoryEventLog, graph: MemoryGraphStore) -> None:
    """Project a ledger into a graph in log order, as the projection worker does."""
    last: dict[str, Event] = {}
    for entry in await log.read_after(None, 10_000):
        if entry.document is None:
            continue
        event = Event.model_validate(entry.document, strict=False)
        result = project_event(event, last.get(event.session_id))
        await graph.merge_event_node(result.node)
        await graph.create_edges_batch(result.edges)
        last[event.session_id] = event


class TestCopy:
    async def test_copy_keeps_order_and_legacy_positions(self) -> None:
        source, target = MemoryEventLog(), MemoryEventLog()
        events = await _seed(source)

        report = await LogMirror(source, target, batch_size=5).copy_once()

        assert report.imported == len(events)
        assert report.batches == 3
        assert (await compare_logs(source, target)).ok
        source_entries = await source.read_after(None, 100)
        assert await target.last_legacy_position() == source_entries[-1].position
        for session in ("session-0", "session-2"):
            assert await target.read_session_ids(session) == await source.read_session_ids(session)

    async def test_copy_resumes_from_target_checkpoint(self) -> None:
        source, target = MemoryEventLog(), MemoryEventLog()
        await _seed(source, sessions=1)
        mirror = LogMirror(source, target, batch_size=2)
        await mirror.copy_once()

        late = _session_events("session-late", 2)
        for event in late:
            await source.append(event)
        second = await LogMirror(source, target, batch_size=2).copy_once()

        assert second.imported == 2
        assert (await LogMirror(source, target).copy_once()).imported == 0
        assert (await compare_logs(source, target)).ok

    async def test_refuses_target_with_native_events(self) -> None:
        source, target = MemoryEventLog(), MemoryEventLog()
        await _seed(source, sessions=1)
        await target.append(make_event())

        with pytest.raises(MirrorRefusedError):
            await LogMirror(source, target).prepare()
        assert await LogMirror(source, target).prepare(allow_native=True) is None

    async def test_expired_documents_are_skipped(self) -> None:
        source, target = MemoryEventLog(), MemoryEventLog()
        old = make_event(occurred_at=datetime.now(UTC) - timedelta(days=30))
        await source.append(old)
        await _seed(source, sessions=1, per_session=2)
        await source.expire(max_age_days=7)

        report = await LogMirror(source, target).copy_once()

        assert report.imported == 2
        assert report.skipped_without_document == 1
        assert (await compare_logs(source, target)).ok


class TestMirror:
    async def test_mirror_follows_live_appends(self) -> None:
        source, target = MemoryEventLog(), MemoryEventLog()
        await _seed(source, sessions=1)
        mirror = LogMirror(source, target, batch_size=3)
        stop = asyncio.Event()
        task = asyncio.create_task(mirror.run(poll_interval_s=0.01, should_stop=stop.is_set))

        for event in _session_events("session-live", 5):
            await source.append(event)
            await asyncio.sleep(0.005)
        for _ in range(100):
            if await target.stream_length() == await source.stream_length():
                break
            await asyncio.sleep(0.01)
        stop.set()
        imported = await asyncio.wait_for(task, timeout=2)

        assert imported == 9
        assert (await compare_logs(source, target)).ok


class TestCompareLogs:
    async def test_detects_missing_changed_and_misordered(self) -> None:
        source, target = MemoryEventLog(), MemoryEventLog()
        events = await _seed(source, sessions=1, per_session=3)
        entries = await source.read_after(None, 10)
        # Import out of order, change one document, leave one out
        await target.append_imported(
            [
                ImportedEvent(
                    document=entries[1].document or {}, legacy_position=entries[1].position
                ),
                ImportedEvent(
                    document=entries[0].document or {}, legacy_position=entries[0].position
                ),
            ]
        )
        target.set_document_fields(str(events[0].event_id), tool_name="changed")

        report = await compare_logs(source, target)

        assert not report.ok
        assert report.divergence_counts == {
            "ledger.missing_in_target": 1,
            "ledger.document_differs": 1,
            "ledger.order": 1,
        }

    async def test_counts_native_target_events(self) -> None:
        source, target = MemoryEventLog(), MemoryEventLog()
        await _seed(source, sessions=1, per_session=2)
        await LogMirror(source, target).copy_once()
        await target.append(make_event())  # written after cutover
        report = await compare_logs(source, target)
        assert report.ok
        assert report.checked["ledger.native_in_target"] == 1


class TestCompareGraphs:
    async def _projected_pair(self) -> tuple[MemoryGraphStore, MemoryGraphStore]:
        source, target = MemoryEventLog(), MemoryEventLog()
        await _seed(source)
        await LogMirror(source, target).copy_once()
        source_graph, target_graph = MemoryGraphStore(), MemoryGraphStore()
        await _project(source, source_graph)
        await _project(target, target_graph)
        return source_graph, target_graph

    async def test_projections_of_mirrored_ledgers_agree(self) -> None:
        source_graph, target_graph = await self._projected_pair()
        graph_report = await compare_graphs(source_graph, target_graph)
        retrieval_report = await compare_retrieval(source_graph, target_graph)
        assert graph_report.ok, graph_report.as_dict()
        assert retrieval_report.ok, retrieval_report.as_dict()
        assert graph_report.checked["graph.events_compared"] == 12
        assert retrieval_report.checked["retrieval.lineage"] == 9

    async def test_detects_a_missing_edge_and_node(self) -> None:
        source_graph, target_graph = await self._projected_pair()
        follows = next(k for k in target_graph.edges if k[1] == "FOLLOWS")
        del target_graph.edges[follows]
        await target_graph.merge_entity_node_raw("only-here", "x", "concept", "t", "t", 1)

        graph_report = await compare_graphs(source_graph, target_graph)
        retrieval_report = await compare_retrieval(source_graph, target_graph)

        assert graph_report.divergence_counts["graph.edge_missing_in_target"] == 1
        assert graph_report.divergence_counts["graph.entity"] == 1
        assert not retrieval_report.ok


def test_target_settings_switch_every_port() -> None:
    settings = target_settings(Settings(), "spanner")
    assert {
        settings.storage.event_log,
        settings.storage.subscription,
        settings.storage.graph,
        settings.storage.keyword_index,
        settings.storage.vector_index,
    } == {"spanner"}


@pytest.mark.parametrize("unused", [str(uuid4())])
def test_module_runs_without_backend_imports(unused: str) -> None:
    import ast
    from pathlib import Path

    package = Path(__file__).resolve().parents[2] / "src" / "context_graph" / "migration"
    for module in package.glob("*.py"):
        tree = ast.parse(module.read_text())
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not any(
            name.startswith(("context_graph.adapters.redis", "context_graph.adapters.neo4j"))
            or name.startswith("context_graph.adapters.spanner")
            for name in imported
        ), module.name
