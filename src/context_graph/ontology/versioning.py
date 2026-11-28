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
        """A rebuild whose processing or evaluation failed, including diagnostic builds."""
        return self.properties.get("gate_passed") is False

    @property
    def incomplete_rebuild(self) -> bool:
        return bool(
            self.properties.get("rebuild_in_progress")
            or self.properties.get("rebuild_complete") is False
            or self.properties.get("missing_documents")
            or self.properties.get("rebuild_failures")
            or self.properties.get("rebuild_failure_count")
            or (
                self.properties.get("gate_skipped") is True
                and self.properties.get("gate_passed") is False
            )
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
    missing_documents: int = 0
    waiting_relationships: int = 0
    blocking_relationships: int = 0
    relationship_scan_complete: bool = True

    @property
    def relationships_complete(self) -> bool:
        return not self.blocking_relationships and self.relationship_scan_complete


def check_replay_authority(event_log: EventLog, projector: PackProjector) -> None:
    """Reject known source-policy mismatches before recording any attempt."""
    if (
        getattr(event_log, "requires_source_provenance", False) is True
        and projector.requires_provenance is not True
    ):
        raise RuntimeFencedError("Bound ledger requires authenticated replay policy")
    if projector.requires_provenance is True:
        from context_graph.ports.event_log import AcceptedRecordReader

        if not isinstance(event_log, AcceptedRecordReader):
            raise RuntimeFencedError("Bound replay requires an accepted-record reader")


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
    check_replay_authority(event_log, projector)
    report = ReplayReport(failed=[])
    from context_graph.worker.relationship_recovery import RelationshipRecovery

    recovery = RelationshipRecovery(graph, event_log, projector, reinterpreting=True)
    cursor: str | None = None
    while True:
        entries = await event_log.read_after(cursor, batch_size)
        if not entries:
            relationships = await recovery.finish()
            report.waiting_relationships = relationships.waiting
            report.blocking_relationships = relationships.blocking
            report.relationship_scan_complete = relationships.complete_scan
            return report
        cursor = entries[-1].position
        for entry in entries:
            document = entry.document
            if document is None:
                # Without the document its event type cannot be checked either.
                # Silently skipping it would falsely certify a complete replay.
                assert report.failed is not None
                report.failed.append(entry.position)
                report.missing_documents += 1
                log.warning("ontology_replay_document_missing", position=entry.position)
                continue
            if document.get("event_type") not in event_types:
                continue
            try:
                event = Event.model_validate(document, strict=False)
                if event.global_position is None:
                    event = event.model_copy(update={"global_position": entry.position})
                await apply_plan(
                    graph,
                    projector.plan(event, document, provenance=entry.provenance),
                    lookup_limit,
                    recovery=recovery,
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
    if state is not None and state.incomplete_rebuild:
        raise OntologyChangeRefusedError(
            plan_for_state(state, registry),
            hint="rebuild incomplete: recover required source events or correct failed writes, "
            "then rebuild a verified replacement. Evaluation and processing overrides "
            "cannot repair missing data.",
        )
    if state is not None and state.failed_gate and not allow_breaking:
        msg = (
            f"this graph was rebuilt for {state.version} "
            "but its processing or evaluation gate failed "
            f"({state.properties.get('gate')}); fix the packs or the evaluation set and "
            "rebuild, or set CG_ONTOLOGY_ALLOW_BREAKING=true"
        )
        raise OntologyChangeRefusedError(ChangePlan(kind="breaking", reasons=[msg]))
    plan = plan_for_state(state, registry)
    if (
        state is not None
        and state.properties.get("replay_failures")
        and not state.properties.get("replay_incomplete")
    ):
        # Earlier releases stored the target packs even after a failed replay.
        # There is no trustworthy prior snapshot here to retry automatically.
        raise OntologyChangeRefusedError(
            plan,
            hint=(
                "recorded replay failures: an earlier update was marked complete "
                "despite failed work. Inspect the recorded failures and build a "
                f"verified fresh projection ({REBUILD_HINT}); a no-op is unsafe."
            ),
        )
    if (
        state is not None
        and state.properties.get("replay_incomplete")
        and (
            state.properties.get("replay_target_version") != registry.version
            or not plan.replay_event_types
        )
    ):
        raise OntologyChangeRefusedError(
            plan,
            hint=(
                "replay incomplete: this graph may contain partial update writes. "
                "Restart with the same recorded replay target packs to retry, "
                f"or build a verified fresh projection ({REBUILD_HINT}). "
                "Changing the configured packs alone is not a rollback."
            ),
        )
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
        # Reject a known authority mismatch before recording any attempt.
        check_replay_authority(event_log, projector)
        # Persist the attempt before writes, so interruption or cancellation
        # cannot leave a partially updated graph looking like a clean old one.
        await graph.upsert_nodes(
            [
                NodeWrite(
                    STATE_REF,
                    {"replay_incomplete": True, "replay_target_version": registry.version},
                )
            ]
        )
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
        if replay.failed or not replay.relationships_complete:
            # Retain the last completed version/packs so a restart still sees
            # the required mapping change rather than treating it as a no-op.
            await graph.upsert_nodes(
                [
                    NodeWrite(
                        STATE_REF,
                        {
                            "replay_incomplete": True,
                            "replay_target_version": registry.version,
                            "replay_failures": (replay.failed or [])[:100],
                            "waiting_relationships": replay.waiting_relationships,
                            "blocking_relationships": replay.blocking_relationships,
                            "relationship_scan_complete": replay.relationship_scan_complete,
                        },
                    )
                ]
            )
            raise OntologyChangeRefusedError(
                plan,
                hint=(
                    f"replay incomplete: {len(replay.failed or [])} event(s) failed; "
                    f"{replay.blocking_relationships} blocking relationship(s), "
                    f"relationship scan complete: {replay.relationship_scan_complete}; "
                    "the completed ontology version was not advanced. "
                    + (
                        f"{replay.missing_documents} unavailable event document(s). "
                        "Retry cannot recover retention-expired history. Recover the "
                        "original source history or use a separately verified fresh "
                        "projection with complete history; rebuilding alone does not "
                        "prove missing history was restored."
                        if replay.missing_documents
                        else "Resolve the failures and restart with the same target packs."
                    )
                ),
            )
    await record_state(
        graph,
        registry,
        applied=plan.kind,
        extra={
            "replayed_events": replay.replayed,
            "waiting_relationships": replay.waiting_relationships,
            "blocking_relationships": replay.blocking_relationships,
            "relationship_scan_complete": replay.relationship_scan_complete,
            "replay_failures": (replay.failed or [])[:100],
            "replay_incomplete": False,
            "replay_target_version": "",
            # Decision 10: these packs' weights wait on their evaluation sets
            # (python -m context_graph.ontology evaluate --record)
            "eval_pending": sorted(
                (plan.eval_required | set(state.properties.get("eval_pending") or []))
                & {p.name for p in registry.packs if p.name not in OPEN_PACKS}
                if state
                else plan.eval_required
            ),
        },
    )
    return plan


def pending_for_state(state: RecordedOntology | None, registry: OntologyRegistry) -> frozenset[str]:
    """Evaluation eligibility never overrides an unfinished or failed projection."""
    active = {p.name for p in registry.packs if p.name not in OPEN_PACKS}
    plan = plan_for_state(state, registry)
    if state is not None:
        try:
            state.registry()
        except (OntologyError, ValueError):
            return frozenset(active)
    if (
        (state is not None and state.packs is None)
        or (state is not None and state.version == registry.version and plan.kind != "none")
        or (
            state is not None
            and (
                state.failed_gate
                or state.incomplete_rebuild
                or state.properties.get("gate_skipped")
                or state.properties.get("replay_incomplete")
                or state.properties.get("replay_failures")
                or state.properties.get("missing_documents")
            )
        )
    ):
        return frozenset(active)
    return frozenset(
        ((set(state.properties.get("eval_pending") or []) if state else set()) | plan.eval_required)
        & active
    )


def status_for_state(
    state: RecordedOntology | None, registry: OntologyRegistry, *, allow_breaking: bool = False
) -> dict[str, Any]:
    """Recorded ontology readiness, not live worker health or proof of all history."""
    plan = plan_for_state(state, registry)
    props = state.properties if state else {}
    reasons: list[str] = []
    actions: list[str] = []
    if state is None:
        reasons.append("No completed ontology is recorded on this graph.")
        actions.append("Start the configured projection worker before serving evaluated answers.")
    elif state.packs is None:
        reasons.append("The recorded pack definitions cannot be loaded.")
        actions.append("Recover a verified projection with readable pack definitions.")
    elif state.version != registry.version or plan.kind != "none":
        reasons.append("The recorded projection does not match the configured packs.")
        actions.append("Complete the required pack update before using the new interpretation.")
    incomplete = bool(props.get("replay_incomplete") or props.get("replay_failures"))
    incomplete_build = bool(state and state.incomplete_rebuild)
    if incomplete_build:
        reasons.append("The replacement graph is incomplete or still being built.")
        actions.append(
            "Recover required events or failed writes, then build a fresh replacement target."
        )
    if incomplete:
        reasons.append("A pack update is unfinished or has recorded replay failures.")
        actions.append(
            "Inspect the unfinished update and its target; recover failed work before restarting."
        )
    if props.get("blocking_relationships") or props.get("relationship_scan_complete") is False:
        reasons.append(
            "Required relationships are unresolved or their recovery scan is unfinished."
        )
        actions.append(
            "Inspect relationship recovery status; resolve required endpoints or "
            "source authority before a fresh rebuild."
        )
    if props.get("missing_documents"):
        reasons.append("The rebuild recorded unavailable source event documents.")
        actions.append(
            "Recover and verify complete source history; passing questions cannot restore it."
        )
    failed = bool(state and state.failed_gate)
    if failed:
        reasons.append("The rebuilt projection failed its checks.")
        actions.append(
            "Correct the problem and rebuild; passing a later question set "
            "does not clear this failure."
        )
    skipped = bool(props.get("gate_skipped"))
    if skipped:
        reasons.append("Evaluation was skipped for a diagnostic build.")
        actions.append(
            "Run and record the reviewed evaluation before trusting its answers "
            "(python -m context_graph.ontology evaluate --record)."
        )
    pending = pending_for_state(state, registry)
    if pending and not reasons:
        reasons.append("Pack evaluation is still pending.")
        actions.append(
            "Run and record the reviewed pack evaluation "
            "(python -m context_graph.ontology evaluate --record)."
        )
    processing_ready = bool(
        state
        and state.packs is not None
        and state.version == registry.version
        and plan.kind == "none"
        and not incomplete
        and not incomplete_build
        and (not failed or allow_breaking)
    )
    return {
        "graph": None
        if state is None
        else {
            "version": state.version,
            "recorded_at": state.recorded_at,
            **{
                key: props.get(key)
                for key in (
                    "applied",
                    "packs",
                    "gate_passed",
                    "gate_skipped",
                    "missing_documents",
                    "replay_incomplete",
                    "replay_target_version",
                    "replay_failures",
                    "rebuild_complete",
                    "rebuild_in_progress",
                    "rebuild_target_version",
                    "rebuild_missing_positions",
                    "rebuild_failures",
                    "rebuild_failure_count",
                    "rebuild_history_basis",
                    "evaluation_status",
                    "waiting_relationships",
                    "blocking_relationships",
                    "relationship_scan_complete",
                )
            },
            "evaluation_passed": {"passed": True, "failed": False, "skipped": None}.get(
                str(props.get("evaluation_status", ""))
            ),
            "eval_pending": props.get("eval_pending", []),
        },
        "change": plan.as_dict(),
        "readiness": {
            "processing_ready": processing_ready,
            "evaluation_ready": processing_ready
            and not failed
            and not skipped
            and not pending
            and not props.get("missing_documents"),
            "pending_packs": sorted(pending),
            "diagnostic_only": skipped
            or (failed and allow_breaking)
            or bool(props.get("missing_documents")),
            "recorded_history_incomplete": bool(props.get("missing_documents")),
            "allow_breaking": allow_breaking,
            "reasons": reasons,
            "next_action": " ".join(actions) if actions else "No recorded ontology blocker.",
        },
    }


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
        self.readiness: dict[str, Any] | None = None
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
        self.readiness = status_for_state(state, self._registry)["readiness"]
        self._packs = frozenset(self.readiness["pending_packs"])
        self._read_at = now
        return self._packs
