"""The ontology version a graph was built with, and bringing a graph to a new one (ADR-0018).

Every graph records the composed packs it was projected under, as one
``OntologyState`` node (``node_id`` ``OntologyState:active``) written through
the ``PackGraph`` port: the version hash, the packs' canonical JSON, when
it was recorded, how the last change was applied and the gate results of a
rebuild. The packs themselves are stored, not only the hash, so the next
start can tell what changed (``domain/pack_versioning.classify_change``).

``reconcile`` runs when the projection worker starts:

- ``none``: nothing to do;
- ``initial`` or ``additive``: record the new version (the worker has
  already created the new schema);
- ``mapping``: replay the ledger's events of the changed types through the
  new pack rules (idempotent upserts), then record;
- ``breaking``: refuse to start, naming the changes and the rebuild
  command, unless ``CG_ONTOLOGY_ALLOW_BREAKING`` is set (the graph then
  keeps what the old rules wrote).

Backend-neutral: ``EventLog`` and ``PackGraph`` only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.domain.models import Event
from context_graph.domain.ontology import OntologyError, OntologyRegistry, Pack
from context_graph.domain.pack_versioning import ChangePlan, classify_change
from context_graph.ports.pack_graph import NodeRef, NodeWrite
from context_graph.worker.pack_projection import apply_plan

if TYPE_CHECKING:
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.pack_graph import PackGraph

log = structlog.get_logger(__name__)

STATE_LABEL = "OntologyState"
STATE_REF = NodeRef(STATE_LABEL, f"{STATE_LABEL}:active")
REBUILD_HINT = "python -m context_graph.ontology rebuild --target KEY=VALUE ..."


class OntologyChangeRefusedError(RuntimeError):
    """A breaking ontology change cannot be applied to a live graph."""

    def __init__(self, plan: ChangePlan) -> None:
        self.plan = plan
        reasons = "; ".join(r for r in plan.reasons if r)[:2000]
        super().__init__(
            f"breaking ontology change ({reasons}). Build a fresh projection under the new "
            f"packs and switch to it ({REBUILD_HINT}), or set CG_ONTOLOGY_ALLOW_BREAKING=true "
            "to keep what the old rules wrote"
        )


@dataclass
class RecordedOntology:
    version: str
    packs: list[Pack]
    recorded_at: str
    properties: dict[str, Any]

    def registry(self) -> OntologyRegistry:
        return OntologyRegistry(self.packs)


async def read_state(graph: PackGraph) -> RecordedOntology | None:
    found = await graph.get_nodes([STATE_REF])
    props = found.get(STATE_REF)
    if not props:
        return None
    packs_json = props.get("packs_json")
    packs: list[Pack] = []
    if isinstance(packs_json, str):
        packs = [Pack.model_validate(data) for data in json.loads(packs_json)]
    return RecordedOntology(
        version=str(props.get("version", "")),
        packs=packs,
        recorded_at=str(props.get("recorded_at", "")),
        properties=props,
    )


async def record_state(
    graph: PackGraph,
    registry: OntologyRegistry,
    *,
    applied: str,
    extra: dict[str, Any] | None = None,
) -> None:
    packs = [json.loads(pack.canonical_json()) for pack in registry.packs]
    await graph.upsert_nodes(
        [
            NodeWrite(
                STATE_REF,
                {
                    "node_type": STATE_LABEL,
                    "version": registry.version,
                    "packs": [f"{p.name}@{p.version}" for p in registry.packs],
                    "packs_json": json.dumps(packs, sort_keys=True, separators=(",", ":")),
                    "recorded_at": datetime.now(UTC).isoformat(),
                    "applied": applied,
                    **(extra or {}),
                },
            )
        ]
    )


async def recorded_registry(
    graph: PackGraph,
) -> tuple[RecordedOntology | None, OntologyRegistry | None]:
    """The recorded state and its registry; the registry is None when it no longer loads."""
    state = await read_state(graph)
    if state is None:
        return None, None
    try:
        return state, state.registry()
    except (OntologyError, ValueError) as exc:
        log.warning("recorded_ontology_unloadable", version=state.version, error=str(exc)[:500])
        return state, None


async def plan_change(graph: PackGraph, registry: OntologyRegistry) -> ChangePlan:
    state, recorded = await recorded_registry(graph)
    if state is not None and recorded is None:
        plan = ChangePlan()
        plan.note("breaking", f"the recorded ontology {state.version} no longer loads")
        return plan
    return classify_change(recorded, registry)


async def replay_event_types(
    event_log: EventLog,
    graph: PackGraph,
    projector: PackProjector,
    event_types: set[str],
    *,
    batch_size: int,
    lookup_limit: int,
) -> int:
    """Project the ledger's events of these types again (in log order); returns how many."""
    replayed = 0
    cursor: str | None = None
    while True:
        entries = await event_log.read_after(cursor, batch_size)
        if not entries:
            return replayed
        cursor = entries[-1].position
        for entry in entries:
            document = entry.document
            if document is None or document.get("event_type") not in event_types:
                continue
            event = Event.model_validate(document, strict=False)
            if event.global_position is None:
                event = event.model_copy(update={"global_position": entry.position})
            await apply_plan(graph, projector.plan(event, document), lookup_limit)
            replayed += 1


async def reconcile(
    graph: PackGraph,
    event_log: EventLog,
    projector: PackProjector,
    *,
    allow_breaking: bool,
    batch_size: int,
    lookup_limit: int,
) -> ChangePlan:
    """Bring the graph's recorded ontology to the projector's (see module docstring)."""
    registry = projector.registry
    plan = await plan_change(graph, registry)
    for problem in plan.version_problems:
        log.warning("ontology_version_problem", problem=problem)
    if plan.kind == "none":
        return plan
    log.info("ontology_change", **plan.as_dict())
    if plan.kind == "breaking" and not allow_breaking:
        raise OntologyChangeRefusedError(plan)
    replayed = 0
    if plan.kind == "mapping":
        replayed = await replay_event_types(
            event_log,
            graph,
            projector,
            plan.replay_event_types,
            batch_size=batch_size,
            lookup_limit=lookup_limit,
        )
        log.info("ontology_mapping_replayed", events=replayed)
    await record_state(graph, registry, applied=plan.kind, extra={"replayed_events": replayed})
    return plan
