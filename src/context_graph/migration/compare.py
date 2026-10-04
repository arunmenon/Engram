"""Compare two backends during a dual run (brief phase 3 exit check).

Three layers, each reported as a list of divergences (zero to pass):

- **Ledger**: every source event in the target, with an identical
  document, its source position as ``legacy_position``, and the target
  holding imports in source order.
- **Graph**: the projections built from each ledger agree on node and
  edge counts, per-session event counts, sampled sessions' event
  properties and edges, and entities.
- **Retrieval**: the retrieval engine gives the same context and lineage
  answers over each graph (same nodes and edges, scores within a
  tolerance).

Fields that legitimately differ between backends are ignored: positions
(each ledger assigns its own), and access bookkeeping that reads change.

Uses ports only; no backend imports.

Source: ADR-0019, docs/research/2026-10/ontology/spanner-design-brief.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from context_graph.domain.models import LineageQuery
from context_graph.retrieval.engine import RetrievalEngine
from context_graph.settings import DecaySettings

if TYPE_CHECKING:
    from context_graph.domain.models import AtlasResponse
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.graph_backend import GraphBackend

# Document fields each ledger assigns for itself
LEDGER_BOOKKEEPING = {"global_position", "legacy_position", "occurred_at_epoch_ms"}

# Graph properties that differ by ledger or change on every read
GRAPH_BOOKKEEPING = {"global_position", "access_count", "last_accessed_at"}

# Allowed difference in retrieval scores (decay depends on the query time)
SCORE_TOLERANCE = 0.01

# Divergences kept in a report; counts stay exact beyond it
MAX_REPORTED = 200


@dataclass
class Divergence:
    layer: str
    kind: str
    key: str
    detail: str = ""


@dataclass
class ComparisonReport:
    checked: dict[str, int] = field(default_factory=dict)
    divergence_counts: dict[str, int] = field(default_factory=dict)
    divergences: list[Divergence] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.divergence_counts

    def count(self, what: str, amount: int = 1) -> None:
        self.checked[what] = self.checked.get(what, 0) + amount

    def add(self, layer: str, kind: str, key: str, detail: str = "") -> None:
        name = f"{layer}.{kind}"
        self.divergence_counts[name] = self.divergence_counts.get(name, 0) + 1
        if len(self.divergences) < MAX_REPORTED:
            self.divergences.append(Divergence(layer, kind, key, detail))

    def merge(self, other: ComparisonReport) -> ComparisonReport:
        for what, amount in other.checked.items():
            self.count(what, amount)
        for name, amount in other.divergence_counts.items():
            self.divergence_counts[name] = self.divergence_counts.get(name, 0) + amount
        room = MAX_REPORTED - len(self.divergences)
        self.divergences.extend(other.divergences[: max(room, 0)])
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "divergence_counts": self.divergence_counts,
            "divergences": [d.__dict__ for d in self.divergences],
        }


def _without(document: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    return {k: v for k, v in document.items() if k not in keys}


async def _read_all(event_log: EventLog, batch_size: int) -> list[Any]:
    entries: list[Any] = []
    cursor: str | None = None
    while True:
        batch = await event_log.read_after(cursor, batch_size)
        entries.extend(batch)
        if len(batch) < batch_size:
            return entries
        cursor = batch[-1].position


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


async def compare_logs(
    source: EventLog, target: EventLog, *, batch_size: int = 500
) -> ComparisonReport:
    """Every source event is in the target, identical, with order preserved."""
    report = ComparisonReport()
    source_entries = [e for e in await _read_all(source, batch_size) if e.document is not None]
    source_order = {entry.position: index for index, entry in enumerate(source_entries)}

    for start in range(0, len(source_entries), batch_size):
        chunk = source_entries[start : start + batch_size]
        target_docs = await target.get_documents([e.event_id for e in chunk])
        for entry, target_doc in zip(chunk, target_docs, strict=True):
            report.count("ledger.events")
            if target_doc is None:
                report.add("ledger", "missing_in_target", entry.event_id, entry.position)
                continue
            if target_doc.get("legacy_position") != entry.position:
                report.add(
                    "ledger",
                    "legacy_position",
                    entry.event_id,
                    f"source {entry.position}, target {target_doc.get('legacy_position')}",
                )
            if _without(target_doc, LEDGER_BOOKKEEPING) != _without(
                entry.document, LEDGER_BOOKKEEPING
            ):
                report.add("ledger", "document_differs", entry.event_id)

    last_index = -1
    for entry in await _read_all(target, batch_size):
        legacy = (entry.document or {}).get("legacy_position")
        if not legacy:
            report.count("ledger.native_in_target")
            continue
        index = source_order.get(legacy)
        if index is None:
            # Not in the source's window any more (trimmed) or not from it
            report.count("ledger.target_only")
            continue
        if index < last_index:
            report.add("ledger", "order", entry.event_id, f"legacy {legacy} after a later one")
        last_index = max(last_index, index)
    return report


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


async def _sample_sessions(graph: GraphBackend, sample: int) -> list[str]:
    sessions = sorted(await graph.get_session_event_counts())
    return sessions if sample <= 0 else sessions[:sample]


def _edge_set(rows: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    return {(r["source"], r["target"], r["edge_type"]) for r in rows}


async def compare_graphs(
    source: GraphBackend, target: GraphBackend, *, sample_sessions: int = 50
) -> ComparisonReport:
    """The two projections agree on counts and on sampled sessions' content."""
    report = ComparisonReport()

    source_stats, target_stats = await source.get_graph_stats(), await target.get_graph_stats()
    for section in ("nodes", "edges"):
        for name in sorted(set(source_stats[section]) | set(target_stats[section])):
            report.count(f"graph.{section}_types")
            left = source_stats[section].get(name, 0)
            right = target_stats[section].get(name, 0)
            if left != right:
                report.add("graph", f"{section}_count", name, f"source {left}, target {right}")

    source_counts = await source.get_session_event_counts()
    target_counts = await target.get_session_event_counts()
    for session in sorted(set(source_counts) | set(target_counts)):
        report.count("graph.sessions")
        if source_counts.get(session) != target_counts.get(session):
            report.add(
                "graph",
                "session_event_count",
                session,
                f"source {source_counts.get(session)}, target {target_counts.get(session)}",
            )

    for session in await _sample_sessions(source, sample_sessions):
        left = {e["event_id"]: e for e in await source.session_events(session, limit=10_000)}
        right = {e["event_id"]: e for e in await target.session_events(session, limit=10_000)}
        for event_id in sorted(set(left) | set(right)):
            report.count("graph.events_compared")
            if event_id not in right or event_id not in left:
                side = "target" if event_id not in right else "source"
                report.add("graph", f"event_missing_in_{side}", event_id, session)
            elif _without(left[event_id], GRAPH_BOOKKEEPING) != _without(
                right[event_id], GRAPH_BOOKKEEPING
            ):
                report.add("graph", "event_properties", event_id, session)
        ids = sorted(left)
        source_edges = _edge_set(await source.reads.session_edges(session, ids))
        target_edges = _edge_set(await target.reads.session_edges(session, ids))
        report.count("graph.session_edges", len(source_edges | target_edges))
        for edge in sorted(source_edges ^ target_edges):
            side = "target" if edge in source_edges else "source"
            report.add("graph", f"edge_missing_in_{side}", "->".join(edge), session)

    source_entities = {e["entity_id"]: e for e in await source.get_entities(limit=100_000)}
    target_entities = {e["entity_id"]: e for e in await target.get_entities(limit=100_000)}
    for entity_id in sorted(set(source_entities) | set(target_entities)):
        report.count("graph.entities")
        if source_entities.get(entity_id) != target_entities.get(entity_id):
            report.add("graph", "entity", entity_id)
    return report


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def _compare_answers(
    report: ComparisonReport, kind: str, key: str, left: AtlasResponse, right: AtlasResponse
) -> None:
    report.count(f"retrieval.{kind}")
    if set(left.nodes) != set(right.nodes):
        missing = sorted(set(left.nodes) - set(right.nodes))
        extra = sorted(set(right.nodes) - set(left.nodes))
        report.add("retrieval", f"{kind}_nodes", key, f"missing {missing}, extra {extra}")
        return
    left_edges = {(e.source, e.target, e.edge_type) for e in left.edges}
    right_edges = {(e.source, e.target, e.edge_type) for e in right.edges}
    if left_edges != right_edges:
        report.add("retrieval", f"{kind}_edges", key)
    for node_id, node in left.nodes.items():
        other = right.nodes[node_id]
        if abs(node.scores.decay_score - other.scores.decay_score) > SCORE_TOLERANCE:
            report.add(
                "retrieval",
                f"{kind}_score",
                node_id,
                f"{node.scores.decay_score} vs {other.scores.decay_score}",
            )


async def compare_retrieval(
    source: GraphBackend,
    target: GraphBackend,
    *,
    sample_sessions: int = 50,
    decay: DecaySettings | None = None,
) -> ComparisonReport:
    """Context and lineage answers agree over the two graphs.

    Both engines run without search indexes or an embedding service, so
    the comparison isolates the graph; keyword ranking is compared by the
    retrieval evals, not here.
    """
    report = ComparisonReport()
    decay = decay or DecaySettings()
    left_engine = RetrievalEngine(source.reads, decay=decay)
    right_engine = RetrievalEngine(target.reads, decay=decay)
    for session in await _sample_sessions(source, sample_sessions):
        _compare_answers(
            report,
            "context",
            session,
            await left_engine.get_context(session, max_nodes=500),
            await right_engine.get_context(session, max_nodes=500),
        )
        event_ids = [e["event_id"] for e in await source.session_events(session, limit=10_000)]
        caused = {
            edge["source"]
            for edge in await source.reads.session_edges(session, event_ids)
            if edge["edge_type"] == "CAUSED_BY"
        }
        for event_id in sorted(caused):
            query = LineageQuery(node_id=event_id, max_depth=10, max_nodes=500)
            _compare_answers(
                report,
                "lineage",
                event_id,
                await left_engine.get_lineage(query),
                await right_engine.get_lineage(query),
            )
    return report
