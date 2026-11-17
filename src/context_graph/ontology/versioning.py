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
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.domain.models import Event
from context_graph.domain.ontology import OPEN_PACKS, OntologyError, OntologyRegistry, Pack
from context_graph.domain.pack_versioning import ChangePlan, classify_change
from context_graph.ports.errors import RuntimeFencedError
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

    def __init__(self, plan: ChangePlan, hint: str | None = None) -> None:
        self.plan = plan
        reasons = "; ".join(r for r in plan.reasons if r)[:2000]
        super().__init__(
            f"ontology change refused ({reasons}). "
            + (
                hint
                or f"Build a fresh projection under the new packs and switch to it "
                f"({REBUILD_HINT}), or set CG_ONTOLOGY_ALLOW_BREAKING=true to keep what "
                "the old rules wrote"
            )
        )


@dataclass
class RecordedOntology:
    version: str
    # None when the stored packs no longer parse (the pack model changed)
    packs: list[Pack] | None
    recorded_at: str
    properties: dict[str, Any]

    def registry(self) -> OntologyRegistry:
        if self.packs is None:
            raise OntologyError([f"the recorded packs of {self.version} no longer parse"])
        return OntologyRegistry(self.packs)

    @property
    def failed_gate(self) -> bool:
        """A rebuild whose evaluation gate ran and failed."""
        return (
            self.properties.get("applied") == "rebuild"
            and self.properties.get("gate_passed") is False
            and not self.properties.get("gate_skipped")
        )


async def read_state(graph: PackGraph) -> RecordedOntology | None:
    found = await graph.get_nodes([STATE_REF])
    props = found.get(STATE_REF)
    if not props:
        return None
    packs: list[Pack] | None = None
    try:
        packs = [Pack.model_validate(data) for data in json.loads(str(props.get("packs_json")))]
    except (ValueError, TypeError) as exc:  # JSON or pydantic validation errors
        log.warning("recorded_ontology_unparsable", error=str(exc)[:500])
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


def plan_for_state(state: RecordedOntology | None, registry: OntologyRegistry) -> ChangePlan:
    """How a graph with this recorded state is brought to ``registry``."""
    if state is None:
        return classify_change(None, registry)
    try:
        recorded = state.registry()
    except (OntologyError, ValueError) as exc:
        log.warning("recorded_ontology_unloadable", version=state.version, error=str(exc)[:500])
        plan = ChangePlan()
        plan.note("breaking", f"the recorded ontology {state.version} no longer loads")
        return plan
    return classify_change(recorded, registry)


async def plan_change(graph: PackGraph, registry: OntologyRegistry) -> ChangePlan:
    return plan_for_state(await read_state(graph), registry)


@dataclass
class ReplayReport:
    replayed: int = 0
    failed: list[str] | None = None


async def replay_event_types(
    event_log: EventLog,
    graph: PackGraph,
    projector: PackProjector,
    event_types: set[str],
    *,
    batch_size: int,
    lookup_limit: int,
) -> ReplayReport:
    """Project the ledger's events of these types again, in log order.

    One event's failure is logged and reported; the replay goes on, as the
    projection worker dead-letters a failing event and goes on.
    """
    if (
        getattr(event_log, "requires_source_provenance", False) is True
        and projector.requires_provenance is not True
    ):
        raise RuntimeFencedError("Bound ledger requires authenticated replay policy")
    if projector.requires_provenance is True:
        from context_graph.ports.event_log import AcceptedRecordReader

        if not isinstance(event_log, AcceptedRecordReader):
            raise RuntimeFencedError("Bound replay requires an accepted-record reader")
    report = ReplayReport(failed=[])
    cursor: str | None = None
    while True:
        entries = await event_log.read_after(cursor, batch_size)
        if not entries:
            return report
        cursor = entries[-1].position
        for entry in entries:
            document = entry.document
            if document is None or document.get("event_type") not in event_types:
                continue
            try:
                event = Event.model_validate(document, strict=False)
                if event.global_position is None:
                    event = event.model_copy(update={"global_position": entry.position})
                await apply_plan(
                    graph,
                    projector.plan(event, document, provenance=entry.provenance),
                    lookup_limit,
                )
                report.replayed += 1
            except RuntimeFencedError:
                raise
            except Exception:
                log.exception("ontology_replay_event_failed", position=entry.position)
                assert report.failed is not None
                report.failed.append(entry.position)


async def reconcile(
    graph: PackGraph,
    event_log: EventLog,
    projector: PackProjector,
    *,
    allow_breaking: bool,
    batch_size: int,
    lookup_limit: int,
    allow_version_problems: bool = False,
) -> ChangePlan:
    """Bring the graph's recorded ontology to the projector's (see module docstring)."""
    registry = projector.registry
    state = await read_state(graph)
    if state is not None and state.failed_gate and not allow_breaking:
        msg = (
            f"this graph was rebuilt for {state.version} but its evaluation gate failed "
            f"({state.properties.get('gate')}); fix the packs or the evaluation set and "
            "rebuild, or set CG_ONTOLOGY_ALLOW_BREAKING=true"
        )
        raise OntologyChangeRefusedError(ChangePlan(kind="breaking", reasons=[msg]))
    plan = plan_for_state(state, registry)
    if plan.kind == "none":
        return plan
    log.info("ontology_change", **plan.as_dict())
    if plan.version_problems and not allow_version_problems:
        raise OntologyChangeRefusedError(
            ChangePlan(
                kind=plan.kind, reasons=["pack versions: " + "; ".join(plan.version_problems)]
            ),
            hint="bump the pack versions, or set CG_ONTOLOGY_ALLOW_VERSION_PROBLEMS=true",
        )
    if plan.kind == "breaking" and not allow_breaking:
        raise OntologyChangeRefusedError(plan)
    replay = ReplayReport(failed=[])
    if plan.replay_event_types:
        # Every event type with pack rules, in log order: replaying only the changed
        # types would apply their transitions over states later events set
        replay = await replay_event_types(
            event_log,
            graph,
            projector,
            set(registry.projection_rules),
            batch_size=batch_size,
            lookup_limit=lookup_limit,
        )
        log.info(
            "ontology_mapping_replayed", events=replay.replayed, failed=len(replay.failed or [])
        )
    await record_state(
        graph,
        registry,
        applied=plan.kind,
        extra={
            "replayed_events": replay.replayed,
            "replay_failures": (replay.failed or [])[:100],
            # Decision 10: these packs' weights wait on their evaluation sets
            # (python -m context_graph.ontology evaluate --record)
            "eval_pending": sorted(plan.eval_required),
        },
    )
    return plan


class EvalPending:
    """Packs whose evaluation is pending on this graph (decision 10), re-read every ``ttl_s``.

    Pending: the packs the recorded ontology lists in ``eval_pending``,
    plus those the active packs would add to it (a graph that records no
    ontology, or another version, has not evaluated them). Cleared by
    ``python -m context_graph.ontology evaluate --record`` or a rebuild
    whose gate passes. A failed read keeps the last answer.
    """

    def __init__(self, graph: PackGraph, registry: OntologyRegistry, ttl_s: float) -> None:
        self._graph = graph
        self._registry = registry
        self._ttl_s = ttl_s
        self._packs: frozenset[str] | None = None
        self._read_at = 0.0

    async def packs(self) -> frozenset[str]:
        now = time.monotonic()
        if self._packs is not None and now - self._read_at < self._ttl_s:
            return self._packs
        try:
            state = await read_state(self._graph)
        except RuntimeFencedError:
            raise
        except Exception:
            if self._packs is None:
                raise
            log.warning("eval_pending_read_failed", exc_info=True)
            return self._packs
        recorded = set(state.properties.get("eval_pending") or []) if state else set()
        pending = recorded | plan_for_state(state, self._registry).eval_required
        active = {p.name for p in self._registry.packs if p.name not in OPEN_PACKS}
        self._packs = frozenset(pending & active)
        self._read_at = now
        return self._packs
