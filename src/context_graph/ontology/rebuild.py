"""Blue/green rebuild of the graph projection under new packs (ADR-0018 decision 8).

A breaking pack change is not applied to the live graph. Instead:

1. **Build**: a fresh graph (another Neo4j instance or database, another
   Spanner database) is filled from the ledger, in log order, by the same
   ``ProjectionConsumer`` the projection worker runs, here reading the
   ledger through ``LedgerReplay`` instead of a consumer group.
2. **Gate**: the evaluation set of every active pack with intents runs on
   the new graph (``ontology/evaluation.py``).
3. **Record**: the new graph records the packs, ``applied: rebuild`` and
   the gate results (``ontology/versioning.py``).
4. **Switch**: when the gate passes, the API and workers are pointed at
   the new graph by configuration (the storage settings the rebuild was
   given). Neo4j Community has no database aliases, so the switch is a
   settings change and a restart, not a server-side alias. The old graph
   is dropped once the switch holds.

The ledger is never changed. Enrichment, extraction and consolidation
build on the projection; their workers are run against the new graph
after the switch (their consumer groups start from the ledger's
beginning on a new backend).

Backend-neutral: ``EventLog`` and ``GraphBackend`` from the registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.ontology.evaluation import EvalReport, run_gate
from context_graph.ontology.versioning import read_state, record_state
from context_graph.ports.subscription import Delivery
from context_graph.retrieval.artifacts import ArtifactRetriever
from context_graph.worker.projection import ProjectionConsumer

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from context_graph.domain.pack_projection import PackProjector
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.graph_backend import GraphBackend
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)

REBUILD_GROUP = "ontology-rebuild"


class RebuildRefusedError(RuntimeError):
    """The target graph already holds a different projection."""


class LedgerReplay:
    """A ``Subscription`` that reads the whole ledger once, in log order.

    Nothing is acknowledged or redelivered: a rebuild that stops is run
    again from the start (projection writes are idempotent). Items the
    consumer dead-letters are kept in ``dead_lettered`` for the report.
    """

    def __init__(self, event_log: EventLog, batch_size: int) -> None:
        self._event_log = event_log
        self._batch_size = batch_size
        self._cursor: str | None = None
        self.read = 0
        self.dead_lettered: list[str] = []

    @property
    def group_name(self) -> str:
        return REBUILD_GROUP

    @property
    def consumer_name(self) -> str:
        return f"{REBUILD_GROUP}-1"

    @property
    def source_name(self) -> str:
        return "ledger"

    async def ensure_group(self) -> None:
        return None

    async def claim_orphaned(self, should_stop: Callable[[], bool] | None = None) -> int:
        return 0

    async def delivery_counts(self, limit: int) -> dict[str, int]:
        return {}

    async def read_pending(self, count: int, *, after: str | None = None) -> list[Delivery]:
        return []

    async def read_new(self, count: int, block_ms: int) -> list[Delivery]:
        entries = await self._event_log.read_after(self._cursor, min(count, self._batch_size))
        if entries:
            self._cursor = entries[-1].position
        self.read += len(entries)
        return [Delivery(e.position, {"event_id": e.event_id}) for e in entries]

    async def ack(self, *positions: str) -> None:
        return None

    async def dead_letter(self, delivery: Delivery, delivery_count: int) -> None:
        self.dead_lettered.append(delivery.position)

    async def lag(self) -> int | None:
        return None


@dataclass
class RebuildReport:
    version: str
    events: int = 0
    dead_lettered: list[str] = field(default_factory=list)
    gate: list[EvalReport] = field(default_factory=list)
    gate_skipped: bool = False

    @property
    def passed(self) -> bool:
        return not self.dead_lettered and (
            self.gate_skipped or all(report.passed for report in self.gate)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "passed": self.passed,
            "events": self.events,
            "dead_lettered": self.dead_lettered[:100],
            "gate_skipped": self.gate_skipped,
            "gate": [report.as_dict() for report in self.gate],
        }


async def project_ledger(
    event_log: EventLog,
    graph: GraphBackend,
    projector: PackProjector,
    settings: Settings,
    *,
    batch_size: int,
) -> LedgerReplay:
    """Project every ledger event into ``graph``, as the projection worker would."""
    replay = LedgerReplay(event_log, batch_size)
    consumer = ProjectionConsumer(
        subscription=replay,
        event_log=event_log,
        graph_store=graph,
        settings=settings,
        pack_projector=projector,
        pack_lookup_limit=settings.ontology.lookup_limit,
    )
    while True:
        deliveries = await replay.read_new(batch_size, 0)
        if not deliveries:
            break
        for delivery in deliveries:
            await consumer.process_message(delivery.position, delivery.fields)
    await consumer.on_stop()
    return replay


async def rebuild(
    event_log: EventLog,
    target: GraphBackend,
    projector: PackProjector,
    settings: Settings,
    *,
    eval_dirs: list[Path],
    skip_gate: bool = False,
    force: bool = False,
) -> RebuildReport:
    """Build, gate and record a projection of the ledger in ``target`` (see module docstring)."""
    registry = projector.registry
    state = await read_state(target)
    if state is not None and state.version != registry.version and not force:
        msg = (
            f"the target graph holds a projection under ontology {state.version}; "
            f"rebuild into an empty graph for {registry.version}"
        )
        raise RebuildRefusedError(msg)
    await target.ensure_constraints()
    await target.ensure_pack_schema(registry, settings.embedding.dimensions)

    report = RebuildReport(registry.version)
    replay = await project_ledger(
        event_log, target, projector, settings, batch_size=settings.ontology.replay_batch_size
    )
    report.events = replay.read
    report.dead_lettered = replay.dead_lettered
    log.info(
        "ontology_rebuild_projected", events=replay.read, dead_lettered=len(replay.dead_lettered)
    )

    if skip_gate:
        report.gate_skipped = True
    else:
        ontology = settings.ontology
        retriever = ArtifactRetriever(
            target,
            registry,
            default_max_depth=settings.query.default_max_depth,
            seed_limit=ontology.retrieval_seed_limit,
            neighbor_limit=ontology.retrieval_neighbor_limit,
            provenance_source=settings.storage.event_log,
            seed_min_ratio=ontology.retrieval_seed_min_ratio,
            max_terms=ontology.retrieval_max_terms,
            max_graph_calls=ontology.retrieval_max_graph_calls,
            scan_limit=ontology.retrieval_scan_limit,
        )
        report.gate = await run_gate(
            registry, retriever, eval_dirs, max_nodes=settings.query.default_max_nodes
        )
    await record_state(
        target,
        registry,
        applied="rebuild",
        extra={
            "rebuild_events": report.events,
            "gate_passed": report.passed,
            "gate_skipped": report.gate_skipped,
            "gate": [f"{r.pack}:{r.mean_f1:.3f}" for r in report.gate],
        },
    )
    return report
