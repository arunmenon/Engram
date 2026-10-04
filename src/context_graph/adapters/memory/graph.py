"""In-memory graph backend (ADR-0019 step 3).

Implements ``GraphBackend``: ``GraphStore``, ``GraphMaintenance``,
``UserStore`` and the ``GraphReads`` used by the retrieval engine. Each
operation mirrors the Cypher of the Neo4j adapter (``adapters/neo4j``):

- nodes are keyed by label and id field, as the uniqueness constraints;
- writes are MERGE: one node per key, one edge per (source, type, target);
- an edge whose endpoint does not exist is not created (MATCH fails);
- setting a property to None removes it, as in Neo4j;
- reads return node properties as plain dicts with the same ordering.

Vector search scores like the Neo4j cosine vector index:
``(1 + cosine) / 2``, in [0, 1].

Single-process and not durable: for tests and the reference backend.

Source: ADR-0009, ADR-0011, ADR-0012, ADR-0014, ADR-0019
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

from context_graph.ports.errors import InvalidRequestError
from context_graph.ports.graph_reads import NEIGHBOR_ROW_KEYS

if TYPE_CHECKING:
    from context_graph.domain.models import (
        AtlasResponse,
        BeliefNode,
        Edge,
        EntityNode,
        EpisodeNode,
        EventNode,
        GoalNode,
        LineageQuery,
        SubgraphQuery,
        SummaryNode,
    )
    from context_graph.retrieval.engine import RetrievalEngine
    from context_graph.settings import DecaySettings, PPRSettings

log = structlog.get_logger(__name__)

# Label -> id property (the uniqueness constraints in adapters/neo4j/queries.py)
LABEL_KEYS: dict[str, str] = {
    "Event": "event_id",
    "Entity": "entity_id",
    "Summary": "summary_id",
    "UserProfile": "profile_id",
    "Preference": "preference_id",
    "Skill": "skill_id",
    "Workflow": "workflow_id",
    "BehavioralPattern": "pattern_id",
    "Belief": "belief_id",
    "Goal": "goal_id",
    "Episode": "episode_id",
}

# Edge type -> (source label, target label), as the MERGE_* templates match
EDGE_ENDPOINTS: dict[str, tuple[str, str]] = {
    "FOLLOWS": ("Event", "Event"),
    "CAUSED_BY": ("Event", "Event"),
    "SIMILAR_TO": ("Event", "Event"),
    "REFERENCES": ("Event", "Entity"),
    "SUMMARIZES": ("Summary", "Event"),
    "SAME_AS": ("Entity", "Entity"),
    "RELATED_TO": ("Entity", "Entity"),
    "HAS_PROFILE": ("Entity", "UserProfile"),
    "HAS_PREFERENCE": ("Entity", "Preference"),
    "HAS_SKILL": ("Entity", "Skill"),
    "DERIVED_FROM": ("Preference", "Event"),
    "EXHIBITS_PATTERN": ("Entity", "BehavioralPattern"),
    "INTERESTED_IN": ("Entity", "Entity"),
    "ABOUT": ("Preference", "Entity"),
    "ABSTRACTED_FROM": ("Workflow", "Workflow"),
    "PARENT_SKILL": ("Skill", "Skill"),
    "CONTRADICTS": ("Belief", "Belief"),
    "SUPERSEDES": ("Belief", "Belief"),
    "PURSUES": ("Entity", "Goal"),
    "CONTAINS": ("Episode", "Event"),
}

# Batch edge creation supports these types natively; others go one by one
# (both paths behave the same here).
STATS_NODE_LABELS = (
    "Event",
    "Entity",
    "Summary",
    "UserProfile",
    "Preference",
    "Skill",
    "Workflow",
    "BehavioralPattern",
)
STATS_EDGE_TYPES = (
    "FOLLOWS",
    "CAUSED_BY",
    "SIMILAR_TO",
    "REFERENCES",
    "SUMMARIZES",
    "SAME_AS",
    "RELATED_TO",
)
ORPHAN_LABELS = ("Entity", "Preference", "Skill", "Workflow", "BehavioralPattern")

# DERIVED_FROM sources allowed by write_derived_from_edge (user_queries allowlist)
DERIVED_FROM_SOURCES: dict[str, str] = {
    "preference_id": "Preference",
    "skill_id": "Skill",
    "pattern_id": "BehavioralPattern",
    "workflow_id": "Workflow",
}

ENTITY_EVENTS_LIMIT = 100
SAME_AS_MAX_HOPS = 3
LINEAGE_MAX_HOPS = 10

NodeKey = tuple[str, str]  # (label, id)
EdgeKey = tuple[NodeKey, str, NodeKey]  # (source, type, target)


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _set(props: dict[str, Any], updates: dict[str, Any]) -> None:
    """Neo4j SET semantics: assign values, remove keys set to None."""
    for key, value in updates.items():
        if value is None:
            props.pop(key, None)
        else:
            props[key] = value


def _newest_first(rows: list[dict[str, Any]], key: str = "occurred_at") -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: str(r.get(key, "")), reverse=True)


@dataclass
class _GraphData:
    nodes: dict[NodeKey, dict[str, Any]] = field(default_factory=dict)
    edges: dict[EdgeKey, dict[str, Any]] = field(default_factory=dict)


class MemoryGraphReads:
    """``GraphReads`` over a ``MemoryGraphStore``."""

    def __init__(self, store: MemoryGraphStore) -> None:
        self._store = store

    def _session_events(self, session_id: str | None) -> list[dict[str, Any]]:
        return [
            props
            for (label, _id), props in self._store.data.nodes.items()
            if label == "Event" and props.get("session_id") == session_id
        ]

    async def seed_events(
        self,
        strategy: str,
        session_id: str | None,
        limit: int,
        *,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        store = self._store
        events = self._session_events(session_id)

        def ranked(rows: list[tuple[float, dict[str, Any]]]) -> list[dict[str, Any]]:
            by_time = sorted(rows, key=lambda r: str(r[1].get("occurred_at", "")), reverse=True)
            ordered = sorted(by_time, key=lambda r: r[0], reverse=True)
            return [dict(props) for _score, props in ordered[:limit]]

        if strategy == "causal_roots":
            rows = []
            for props in events:
                caused = len(store.in_edges(("Event", props["event_id"]), "CAUSED_BY"))
                if caused:
                    rows.append((float(caused), props))
            return ranked(rows)
        if strategy == "entity_hubs":
            rows = []
            for props in events:
                refs = store.out_edges(("Event", props["event_id"]), "REFERENCES")
                if refs:
                    rows.append((float(len(refs)), props))
            return ranked(rows)
        if strategy == "temporal_anchors":
            anchored = [p for p in events if p.get("importance_score") is not None]
            by_time = sorted(anchored, key=lambda p: str(p.get("occurred_at", "")))
            ordered = sorted(by_time, key=lambda p: p["importance_score"], reverse=True)
            return [dict(p) for p in ordered[:limit]]
        if strategy == "user_profile":
            rows = []
            for props in events:
                linked = 0
                for _src, _type, entity_key in store.out_edges(
                    ("Event", props["event_id"]), "REFERENCES"
                ):
                    if store.out_edges(entity_key, "HAS_PROFILE") or store.out_edges(
                        entity_key, "HAS_PREFERENCE"
                    ):
                        linked += 1
                if linked:
                    rows.append((float(linked), props))
            return ranked(rows)
        if strategy == "similar_cluster":
            rows = []
            for props in events:
                node = ("Event", props["event_id"])
                similar = len(store.out_edges(node, "SIMILAR_TO")) + len(
                    store.in_edges(node, "SIMILAR_TO")
                )
                rows.append((float(similar), props))
            return ranked(rows)
        if strategy == "workflow_pattern":
            matching = [
                p for p in events if str(p.get("event_type", "")).startswith(("tool.", "workflow."))
            ]
            ordered = sorted(matching, key=lambda p: str(p.get("occurred_at", "")))
            return [dict(p) for p in ordered[:limit]]
        # "general" and unknown strategies: most recent events
        return [dict(p) for p in _newest_first(events)[:limit]]

    async def get_event_nodes(
        self, event_ids: list[str], *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        nodes = self._store.data.nodes
        return [dict(nodes[("Event", eid)]) for eid in event_ids if ("Event", eid) in nodes]

    async def cross_session_entity_events(
        self, session_id: str | None, limit: int, *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        store = self._store
        entities: list[NodeKey] = []
        for props in self._session_events(session_id):
            for _src, _type, entity_key in store.out_edges(
                ("Event", props["event_id"]), "REFERENCES"
            ):
                if entity_key not in entities:
                    entities.append(entity_key)
        rows: list[dict[str, Any]] = []
        for entity_key in entities:
            for event_key, _type, _dst in store.in_edges(entity_key, "REFERENCES"):
                other = store.data.nodes[event_key]
                if other.get("session_id") != session_id:
                    rows.append(other)
        return [dict(r) for r in _newest_first(rows)[:limit]]

    async def event_neighbors(
        self, event_ids: list[str], neighbor_limit: int, *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        store = self._store
        rows: list[dict[str, Any]] = []
        for event_id in event_ids:
            node = ("Event", event_id)
            if node not in store.data.nodes:
                continue
            outgoing = store.out_edges(node)
            if not outgoing:
                rows.append(dict.fromkeys(NEIGHBOR_ROW_KEYS) | {"seed_event_id": event_id})
            for edge_key in outgoing:
                _src, edge_type, target = edge_key
                target_props = store.data.nodes[target]
                rows.append(
                    {
                        "seed_event_id": event_id,
                        "rel_type": edge_type,
                        "rel_props": dict(store.data.edges[edge_key]),
                        "neighbor_labels": [target[0]],
                        "neighbor_props": dict(target_props),
                        "neighbor_event_id": target_props.get("event_id"),
                        "neighbor_entity_id": target_props.get("entity_id"),
                        "neighbor_summary_id": target_props.get("summary_id"),
                    }
                )
        return rows[:neighbor_limit]

    async def session_events_page(
        self,
        session_id: str,
        limit: int,
        *,
        after: tuple[str, str] | None = None,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        events = self._session_events(session_id)
        if after is None:
            return [dict(p) for p in _newest_first(events)[:limit]]
        cursor_ts, cursor_id = after
        later = [
            p
            for p in events
            if str(p.get("occurred_at", "")) > cursor_ts
            or (str(p.get("occurred_at", "")) == cursor_ts and p["event_id"] > cursor_id)
        ]
        ordered = sorted(later, key=lambda p: str(p.get("occurred_at", "")))
        return [dict(p) for p in ordered[:limit]]

    async def session_edges(
        self, session_id: str, event_ids: list[str], *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        wanted = set(event_ids)
        nodes = self._store.data.nodes
        rows = []
        for (source, edge_type, target), props in self._store.data.edges.items():
            if source[0] != "Event" or target[0] != "Event":
                continue
            if source[1] not in wanted or target[1] not in wanted:
                continue
            if (
                nodes[source].get("session_id") != session_id
                or nodes[target].get("session_id") != session_id
            ):
                continue
            rows.append(
                {
                    "source": source[1],
                    "target": target[1],
                    "edge_type": edge_type,
                    "props": dict(props),
                }
            )
        return rows

    async def lineage_chains(
        self,
        node_id: str,
        max_depth: int,
        max_nodes: int,
        *,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        store = self._store
        start = ("Event", node_id)
        if start not in store.data.nodes:
            return []
        hop_limit = min(max_depth, LINEAGE_MAX_HOPS)
        chains: list[dict[str, Any]] = []

        def walk(path: list[NodeKey], used: list[EdgeKey]) -> None:
            if len(chains) >= max_nodes:
                return
            for edge_key in store.out_edges(path[-1], "CAUSED_BY"):
                if edge_key in used:
                    continue
                target = edge_key[2]
                next_path, next_used = [*path, target], [*used, edge_key]
                chains.append(
                    {
                        "nodes": [dict(store.data.nodes[n]) for n in next_path],
                        "edges": [
                            {
                                "source": store.data.nodes[e[0]].get("event_id", ""),
                                "target": store.data.nodes[e[2]].get("event_id", ""),
                                "properties": dict(store.data.edges[e]),
                            }
                            for e in next_used
                        ],
                    }
                )
                if len(chains) >= max_nodes:
                    return
                if len(next_used) < hop_limit:
                    walk(next_path, next_used)

        walk([start], [])
        return chains[:max_nodes]

    async def record_access(self, event_ids: list[str], accessed_at: str) -> None:
        for event_id in event_ids:
            props = self._store.data.nodes.get(("Event", event_id))
            if props is not None:
                props["access_count"] = int(props.get("access_count") or 0) + 1
                props["last_accessed_at"] = accessed_at


class MemoryGraphStore:
    """``GraphBackend`` held in process memory."""

    def __init__(
        self,
        *,
        decay_settings: DecaySettings | None = None,
        ppr_settings: PPRSettings | None = None,
    ) -> None:
        self.data = _GraphData()
        self._reads = MemoryGraphReads(self)
        self._decay_settings = decay_settings
        self._ppr_settings = ppr_settings
        self._engine: RetrievalEngine | None = None

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------

    @property
    def reads(self) -> MemoryGraphReads:
        return self._reads

    def _merge_node(self, label: str, node_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        key = (label, node_id)
        props = self.data.nodes.get(key)
        if props is None:
            props = {LABEL_KEYS[label]: node_id}
            self.data.nodes[key] = props
        _set(props, updates)
        return props

    def _merge_edge(
        self, source: NodeKey, edge_type: str, target: NodeKey, updates: dict[str, Any]
    ) -> bool:
        if source not in self.data.nodes or target not in self.data.nodes:
            return False
        props = self.data.edges.setdefault((source, edge_type, target), {})
        _set(props, updates)
        return True

    def out_edges(self, node: NodeKey, edge_type: str | None = None) -> list[EdgeKey]:
        return [
            k for k in self.data.edges if k[0] == node and (edge_type is None or k[1] == edge_type)
        ]

    def in_edges(self, node: NodeKey, edge_type: str | None = None) -> list[EdgeKey]:
        return [
            k for k in self.data.edges if k[2] == node and (edge_type is None or k[1] == edge_type)
        ]

    def _detach_delete(self, node: NodeKey) -> None:
        for edge_key in [k for k in self.data.edges if node in (k[0], k[2])]:
            del self.data.edges[edge_key]
        self.data.nodes.pop(node, None)

    def _has_edges(self, node: NodeKey) -> bool:
        return any(node in (k[0], k[2]) for k in self.data.edges)

    # ------------------------------------------------------------------
    # GraphStore: node writes
    # ------------------------------------------------------------------

    @staticmethod
    def _event_props(node: EventNode) -> dict[str, Any]:
        return {
            "event_type": node.event_type,
            "occurred_at": node.occurred_at.isoformat(),
            "session_id": node.session_id,
            "agent_id": node.agent_id,
            "trace_id": node.trace_id,
            "tool_name": node.tool_name,
            "global_position": node.global_position,
            "keywords": node.keywords,
            "summary": node.summary,
            "importance_score": node.importance_score,
            "access_count": node.access_count,
            "last_accessed_at": (
                node.last_accessed_at.isoformat() if node.last_accessed_at else None
            ),
        }

    async def merge_event_node(self, node: EventNode) -> None:
        self._merge_node("Event", node.event_id, self._event_props(node))

    async def merge_event_nodes_batch(self, nodes: list[EventNode]) -> None:
        for node in nodes:
            await self.merge_event_node(node)

    async def merge_entity_node(self, node: EntityNode) -> None:
        self._merge_node(
            "Entity",
            node.entity_id,
            {
                "name": node.name,
                "entity_type": str(node.entity_type),
                "first_seen": node.first_seen.isoformat(),
                "last_seen": node.last_seen.isoformat(),
                "mention_count": node.mention_count,
                "embedding": node.embedding,
            },
        )

    async def merge_summary_node(self, node: SummaryNode) -> None:
        self._merge_node(
            "Summary",
            node.summary_id,
            {
                "scope": node.scope,
                "scope_id": node.scope_id,
                "content": node.content,
                "created_at": node.created_at.isoformat(),
                "event_count": node.event_count,
                "time_range": [dt.isoformat() for dt in node.time_range],
            },
        )

    async def merge_belief_node(self, node: BeliefNode) -> None:
        self._merge_node(
            "Belief",
            node.belief_id,
            {
                "belief_text": node.belief_text,
                "confidence": node.confidence,
                "category": str(node.category),
                "created_at": node.created_at.isoformat(),
                "last_confirmed_at": node.last_confirmed_at.isoformat(),
                "confirmation_count": node.confirmation_count,
                "superseded_by": node.superseded_by,
            },
        )

    async def merge_goal_node(self, node: GoalNode) -> None:
        self._merge_node(
            "Goal",
            node.goal_id,
            {
                "description": node.description,
                "status": str(node.status),
                "created_at": node.created_at.isoformat(),
                "last_active_at": node.last_active_at.isoformat(),
                "priority": node.priority,
                "evidence_count": node.evidence_count,
            },
        )

    async def merge_episode_node(self, node: EpisodeNode) -> None:
        self._merge_node(
            "Episode",
            node.episode_id,
            {
                "session_id": node.session_id,
                "start_time": node.start_time.isoformat(),
                "end_time": node.end_time.isoformat(),
                "event_count": node.event_count,
                "episode_type": str(node.episode_type),
                "summary_id": node.summary_id,
            },
        )

    async def merge_entity_node_raw(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        first_seen: str,
        last_seen: str,
        mention_count: int,
        embedding: list[float] | None = None,
    ) -> None:
        self._merge_node(
            "Entity",
            entity_id,
            {
                "name": name,
                "entity_type": entity_type,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "mention_count": mention_count,
                "embedding": embedding or [],
            },
        )

    # ------------------------------------------------------------------
    # GraphStore: edges
    # ------------------------------------------------------------------

    def _merge_typed(
        self, source_id: str, target_id: str, edge_type: str, props: dict[str, Any]
    ) -> None:
        source_label, target_label = EDGE_ENDPOINTS[edge_type]
        self._merge_edge(
            (source_label, source_id), edge_type, (target_label, target_id), dict(props)
        )

    async def create_edge(self, edge: Edge) -> None:
        edge_type = str(edge.edge_type)
        if edge_type not in EDGE_ENDPOINTS:
            msg = f"Unknown edge type: {edge.edge_type}"
            raise ValueError(msg)
        self._merge_typed(edge.source, edge.target, edge_type, edge.properties)

    async def create_edges_batch(self, edges: list[Edge]) -> None:
        for edge in edges:
            edge_type = str(edge.edge_type)
            if edge_type not in EDGE_ENDPOINTS:
                log.warning("skipping_unknown_edge_type", edge_type=edge_type)
                continue
            self._merge_typed(edge.source, edge.target, edge_type, edge.properties)

    async def merge_typed_edge(
        self, source_id: str, target_id: str, edge_type: str, props: dict[str, Any] | None = None
    ) -> None:
        if edge_type not in EDGE_ENDPOINTS:
            msg = f"Unknown edge type: {edge_type}"
            raise ValueError(msg)
        self._merge_typed(source_id, target_id, edge_type, props or {})

    # ------------------------------------------------------------------
    # GraphStore: enrichment, entities, vectors
    # ------------------------------------------------------------------

    async def update_event_enrichment(
        self, event_id: str, keywords: list[str], importance_score: int
    ) -> None:
        props = self.data.nodes.get(("Event", event_id))
        if props is not None:
            _set(props, {"keywords": keywords, "importance_score": importance_score})

    async def store_event_embedding(self, event_id: str, embedding: list[float]) -> None:
        props = self.data.nodes.get(("Event", event_id))
        if props is not None:
            _set(props, {"embedding": embedding})

    async def adjust_node_importance(
        self,
        node_id: str,
        delta: int,
        min_value: int = 1,
        max_value: int = 10,
    ) -> bool:
        props = self.data.nodes.get(("Event", node_id))
        if props is None:
            return False
        current = props.get("importance_score")
        if current is None:
            props["importance_score"] = max(min_value, min(max_value, max(min_value, 5 + delta)))
        else:
            props["importance_score"] = int(max(min_value, min(max_value, current + delta)))
        return True

    async def get_entities(self, limit: int = 1000) -> list[dict[str, Any]]:
        entities = [p for (label, _id), p in self.data.nodes.items() if label == "Entity"]
        return [
            {
                "entity_id": p["entity_id"],
                "name": p.get("name"),
                "entity_type": p.get("entity_type"),
            }
            for p in entities[:limit]
        ]

    def _referencing_events(self, entity: NodeKey) -> list[dict[str, Any]]:
        rows = []
        for edge_key in self.in_edges(entity, "REFERENCES"):
            event = dict(self.data.nodes[edge_key[0]])
            event["ref_props"] = dict(self.data.edges[edge_key])
            rows.append(event)
        return rows

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        entity = ("Entity", entity_id)
        if entity not in self.data.nodes:
            return None
        events = _newest_first(self._referencing_events(entity))[:ENTITY_EVENTS_LIMIT]
        return {"entity": dict(self.data.nodes[entity]), "connected_events": events}

    async def get_entity_with_cluster(self, entity_id: str) -> dict[str, Any] | None:
        start = ("Entity", entity_id)
        if start not in self.data.nodes:
            return None
        cluster = [start]
        frontier = [start]
        for _hop in range(SAME_AS_MAX_HOPS):
            next_frontier = []
            for node in frontier:
                for source, _type, target in self.out_edges(node, "SAME_AS") + self.in_edges(
                    node, "SAME_AS"
                ):
                    other = target if source == node else source
                    if other not in cluster:
                        cluster.append(other)
                        next_frontier.append(other)
            frontier = next_frontier
        entities = {node[1]: dict(self.data.nodes[node]) for node in cluster}
        events: list[dict[str, Any]] = []
        for node in cluster:
            events.extend(self._referencing_events(node))
        return {
            "entities": entities,
            "connected_events": _newest_first(events)[:ENTITY_EVENTS_LIMIT],
        }

    async def consolidate_entity_cluster(self, cluster_ids: list[str], canonical_id: str) -> None:
        if not cluster_ids or not canonical_id:
            return
        resolved_at = _iso_now()
        for member_id in cluster_ids:
            if member_id == canonical_id:
                continue
            self._merge_edge(
                ("Entity", member_id),
                "SAME_AS",
                ("Entity", canonical_id),
                {
                    "confidence": 1.0,
                    "justification": "transitive_closure",
                    "resolved_at": resolved_at,
                },
            )

    async def search_similar_entities(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.75,
    ) -> list[dict[str, Any]]:
        query_norm = math.sqrt(sum(v * v for v in query_embedding))
        if query_norm == 0:
            return []
        scored: list[tuple[float, dict[str, Any]]] = []
        for (label, _id), props in self.data.nodes.items():
            embedding = props.get("embedding")
            if label != "Entity" or not embedding or len(embedding) != len(query_embedding):
                continue
            norm = math.sqrt(sum(v * v for v in embedding))
            if norm == 0:
                continue
            cosine = sum(a * b for a, b in zip(query_embedding, embedding, strict=True)) / (
                query_norm * norm
            )
            scored.append(((1.0 + cosine) / 2.0, props))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "entity_id": props["entity_id"],
                "name": props.get("name"),
                "entity_type": props.get("entity_type"),
                "score": score,
            }
            for score, props in scored[:top_k]
            if score >= threshold
        ]

    # ------------------------------------------------------------------
    # GraphStore: schema, health, lifecycle
    # ------------------------------------------------------------------

    async def ensure_constraints(self) -> None:
        """Uniqueness is structural: nodes are keyed by label and id."""

    async def ensure_vector_indexes(self) -> None:
        """Vector search scans entity embeddings; nothing to create."""

    async def health_ping(self) -> bool:
        return True

    async def close(self) -> None:
        """Nothing to release."""

    # ------------------------------------------------------------------
    # GraphStore: deprecated query methods (ADR-0019 C3)
    # ------------------------------------------------------------------

    def _retrieval(self) -> RetrievalEngine:
        if self._engine is None:
            from context_graph.adapters.search import GraphVectorIndex
            from context_graph.retrieval.engine import RetrievalEngine
            from context_graph.settings import DecaySettings

            self._engine = RetrievalEngine(
                self._reads,
                decay=self._decay_settings or DecaySettings(),
                vector_index=GraphVectorIndex(self),
                ppr_settings=self._ppr_settings,
                provenance_source="memory",
            )
        return self._engine

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
        max_depth: int = 3,
        cursor: str | None = None,
    ) -> AtlasResponse:
        return await self._retrieval().get_context(session_id, max_nodes, query, max_depth, cursor)

    async def get_lineage(
        self, query: LineageQuery, query_text: str | None = None
    ) -> AtlasResponse:
        return await self._retrieval().get_lineage(query, query_text)

    async def get_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        return await self._retrieval().get_subgraph(query)

    # ------------------------------------------------------------------
    # GraphMaintenance
    # ------------------------------------------------------------------

    def _events(self) -> list[dict[str, Any]]:
        return [p for (label, _id), p in self.data.nodes.items() if label == "Event"]

    async def get_session_event_counts(self) -> dict[str, int]:
        counts = Counter(p["session_id"] for p in self._events() if p.get("session_id") is not None)
        return dict(counts.most_common())

    async def get_graph_stats(self) -> dict[str, Any]:
        node_counts = {label: 0 for label in STATS_NODE_LABELS}
        for label, _id in self.data.nodes:
            if label in node_counts:
                node_counts[label] += 1
        edge_counts = {edge_type: 0 for edge_type in STATS_EDGE_TYPES}
        for _src, edge_type, _dst in self.data.edges:
            if edge_type in edge_counts:
                edge_counts[edge_type] += 1
        return {
            "nodes": node_counts,
            "edges": edge_counts,
            "total_nodes": sum(node_counts.values()),
            "total_edges": sum(edge_counts.values()),
        }

    async def write_summary_with_edges(
        self,
        summary_id: str,
        scope: str,
        scope_id: str,
        content: str,
        created_at: str,
        event_count: int,
        time_range: list[str],
        event_ids: list[str],
    ) -> None:
        self._merge_node(
            "Summary",
            summary_id,
            {
                "scope": scope,
                "scope_id": scope_id,
                "content": content,
                "created_at": created_at,
                "event_count": event_count,
                "time_range": time_range,
            },
        )
        for event_id in event_ids:
            self._merge_edge(
                ("Summary", summary_id),
                "SUMMARIZES",
                ("Event", event_id),
                {"created_at": created_at},
            )

    @staticmethod
    def _cutoff_iso(hours: int) -> str:
        return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

    async def delete_edges_by_type_and_age(self, min_score: float, max_age_hours: int) -> int:
        cutoff = self._cutoff_iso(max_age_hours)
        doomed = [
            key
            for key, props in self.data.edges.items()
            if key[1] == "SIMILAR_TO"
            and key[0][0] == "Event"
            and key[2][0] == "Event"
            and props.get("similarity_score") is not None
            and props["similarity_score"] < min_score
            and str(self.data.nodes[key[0]].get("occurred_at", "")) < cutoff
        ]
        for key in doomed:
            del self.data.edges[key]
        return len(doomed)

    async def delete_cold_events(
        self,
        max_age_hours: int,
        min_importance: int,
        min_access_count: int,
    ) -> int:
        cutoff = self._cutoff_iso(max_age_hours)
        doomed = [
            ("Event", p["event_id"])
            for p in self._events()
            if str(p.get("occurred_at", "")) < cutoff
            and (p.get("importance_score") is None or p["importance_score"] < min_importance)
            and int(p.get("access_count") or 0) < min_access_count
        ]
        for node in doomed:
            self._detach_delete(node)
        return len(doomed)

    async def delete_archive_events(self, event_ids: list[str]) -> int:
        deleted = 0
        for event_id in event_ids:
            node = ("Event", event_id)
            if node in self.data.nodes:
                self._detach_delete(node)
                deleted += 1
        return deleted

    async def get_archive_event_ids(self, max_age_hours: int) -> list[str]:
        cutoff = self._cutoff_iso(max_age_hours)
        return [p["event_id"] for p in self._events() if str(p.get("occurred_at", "")) < cutoff]

    async def delete_orphan_nodes(self, batch_size: int = 500) -> tuple[dict[str, int], list[str]]:
        counts: dict[str, int] = {}
        deleted_entity_ids: list[str] = []
        for label in ORPHAN_LABELS:
            orphans = [
                key for key in list(self.data.nodes) if key[0] == label and not self._has_edges(key)
            ]
            for node in orphans:
                self._detach_delete(node)
            counts[label] = len(orphans)
            if label == "Entity":
                deleted_entity_ids = [node[1] for node in orphans]
        return counts, deleted_entity_ids

    async def update_importance_from_centrality(self) -> int:
        updated = 0
        for props in self._events():
            in_degree = len(self.in_edges(("Event", props["event_id"])))
            if in_degree <= 0:
                continue
            if in_degree >= 10:
                props["importance_score"] = 10
            elif in_degree >= 5:
                props["importance_score"] = 8
            elif in_degree >= 3:
                props["importance_score"] = 6
            else:
                props["importance_score"] = props.get("importance_score") or 5
            updated += 1
        return updated

    async def run_session_query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Not supported: the memory backend has no query language (ADR-0019 C6)."""
        msg = "run_session_query is not supported by the memory backend; use a named operation"
        raise InvalidRequestError(msg)

    async def session_agent_id(self, session_id: str) -> str | None:
        for props in self._events():
            if props.get("session_id") == session_id:
                agent_id: str | None = props.get("agent_id")
                return agent_id
        return None

    def _session_in_time_order(self, session_id: str) -> list[dict[str, Any]]:
        events = [p for p in self._events() if p.get("session_id") == session_id]
        return sorted(events, key=lambda p: str(p.get("occurred_at", "")))

    async def session_events(self, session_id: str, limit: int) -> list[dict[str, Any]]:
        return [dict(p) for p in self._session_in_time_order(session_id)[:limit]]

    async def session_event_timeline(self, session_id: str) -> list[dict[str, Any]]:
        fields = ("event_id", "event_type", "occurred_at", "tool_name", "status")
        return [
            {name: p.get(name) for name in fields} for p in self._session_in_time_order(session_id)
        ]

    async def events_for_pruning(self, limit: int) -> list[dict[str, Any]]:
        ordered = sorted(self._events(), key=lambda p: str(p.get("occurred_at", "")))
        return [
            {
                "event_id": p.get("event_id"),
                "occurred_at": p.get("occurred_at"),
                "importance_score": p.get("importance_score"),
                "access_count": int(p.get("access_count") or 0),
                "similarity_score": p.get("similarity_score"),
            }
            for p in ordered[:limit]
        ]

    async def delete_all(self, *, confirm: bool = False) -> None:
        if not confirm:
            msg = "delete_all requires confirm=True"
            raise InvalidRequestError(msg)
        self.data = _GraphData()
        log.warning("graph_deleted_all")

    # ------------------------------------------------------------------
    # UserStore (ADR-0012), mirroring adapters/neo4j/user_queries.py
    # ------------------------------------------------------------------

    def _user_targets(self, user_id: str, edge_type: str) -> list[dict[str, Any]]:
        return [
            self.data.nodes[target]
            for _src, _type, target in self.out_edges(("Entity", user_id), edge_type)
        ]

    def _ensure_user_entity(self, user_entity_id: str, now: str) -> None:
        node = ("Entity", user_entity_id)
        if node in self.data.nodes:
            return
        self._merge_node(
            "Entity",
            user_entity_id,
            {
                "entity_type": "user",
                "name": user_entity_id,
                "first_seen": now,
                "last_seen": now,
                "mention_count": 1,
            },
        )

    def _merge_target_entity(self, entity_id: str, name: str, entity_type: str, now: str) -> None:
        node = ("Entity", entity_id)
        if node in self.data.nodes:
            self.data.nodes[node]["last_seen"] = now
            return
        self._merge_node(
            "Entity",
            entity_id,
            {
                "name": name,
                "entity_type": entity_type,
                "first_seen": now,
                "last_seen": now,
                "mention_count": 1,
            },
        )

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        profiles = self._user_targets(user_id, "HAS_PROFILE")
        return dict(profiles[0]) if profiles else None

    async def get_user_preferences(
        self, user_id: str, active_only: bool = True
    ) -> list[dict[str, Any]]:
        preferences = [
            p
            for p in self._user_targets(user_id, "HAS_PREFERENCE")
            if not active_only or p.get("superseded_by") is None
        ]
        return [dict(p) for p in _newest_first(preferences, "last_confirmed_at")]

    async def get_user_skills(self, user_id: str) -> list[dict[str, Any]]:
        skills = self._user_targets(user_id, "HAS_SKILL")
        return [dict(s) for s in sorted(skills, key=lambda s: str(s.get("name", "")))]

    async def get_user_patterns(self, user_id: str) -> list[dict[str, Any]]:
        patterns = self._user_targets(user_id, "EXHIBITS_PATTERN")
        return [dict(p) for p in _newest_first(patterns, "last_confirmed_at")]

    def _interests(self, user_id: str) -> list[dict[str, Any]]:
        rows = []
        for edge_key in self.out_edges(("Entity", user_id), "INTERESTED_IN"):
            target = self.data.nodes[edge_key[2]]
            edge = self.data.edges[edge_key]
            rows.append(
                {
                    "entity_id": target.get("entity_id"),
                    "name": target.get("name"),
                    "entity_type": target.get("entity_type"),
                    "weight": edge.get("weight"),
                    "source": edge.get("source"),
                }
            )
        return rows

    async def get_user_interests(self, user_id: str) -> list[dict[str, Any]]:
        return sorted(self._interests(user_id), key=lambda r: r.get("weight") or 0, reverse=True)

    async def write_user_profile(self, profile_data: dict[str, Any]) -> None:
        now = _iso_now()
        user_id = profile_data.get("user_id", "")
        profile_id = profile_data.get("profile_id", f"profile:{user_id}")
        display_name = profile_data.get("display_name")
        entity = ("Entity", user_id)
        if entity in self.data.nodes:
            self.data.nodes[entity]["last_seen"] = now
        else:
            self._merge_node(
                "Entity",
                user_id,
                {
                    "name": display_name,
                    "entity_type": "user",
                    "first_seen": now,
                    "last_seen": now,
                    "mention_count": 1,
                },
            )
        existing = self.data.nodes.get(("UserProfile", profile_id), {})
        self._merge_node(
            "UserProfile",
            profile_id,
            {
                "user_id": user_id,
                "display_name": display_name,
                "timezone": profile_data.get("timezone"),
                "language": profile_data.get("language"),
                "communication_style": profile_data.get("communication_style"),
                "technical_level": profile_data.get("technical_level"),
                "created_at": existing.get("created_at", now),
                "updated_at": now,
            },
        )
        self._merge_edge(entity, "HAS_PROFILE", ("UserProfile", profile_id), {})

    def _derived_from(
        self,
        source: NodeKey,
        event_id: str,
        derivation_info: dict[str, Any],
        now: str,
    ) -> None:
        self._merge_edge(
            source,
            "DERIVED_FROM",
            ("Event", event_id),
            {
                "method": derivation_info.get("method", "llm_extraction"),
                "session_id": derivation_info.get("session_id", ""),
                "extracted_at": now,
                "model_id": derivation_info.get("model_id"),
                "prompt_version": derivation_info.get("prompt_version"),
                "evidence_quote": derivation_info.get("evidence_quote"),
                "source_turn_index": derivation_info.get("source_turn_index"),
            },
        )

    async def write_preference_with_edges(
        self,
        user_entity_id: str,
        preference_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        now = _iso_now()
        preference_id = preference_data.get("preference_id", f"pref:{uuid4().hex[:12]}")
        self._ensure_user_entity(user_entity_id, now)
        existing = self.data.nodes.get(("Preference", preference_id), {})
        self._merge_node(
            "Preference",
            preference_id,
            {
                "category": preference_data.get("category", "domain"),
                "key": preference_data.get("key", ""),
                "polarity": preference_data.get("polarity", "neutral"),
                "strength": preference_data.get("strength", 0.5),
                "confidence": preference_data.get("confidence", 0.5),
                "source": preference_data.get("source", "inferred"),
                "context": preference_data.get("context"),
                "scope": preference_data.get("scope") or "global",
                "scope_id": preference_data.get("scope_id"),
                "observation_count": int(existing.get("observation_count") or 0) + 1,
                "first_observed_at": existing.get("first_observed_at", now),
                "last_confirmed_at": now,
                "superseded_by": preference_data.get("superseded_by"),
            },
        )
        preference = ("Preference", preference_id)
        self._merge_edge(("Entity", user_entity_id), "HAS_PREFERENCE", preference, {})
        about_entity = preference_data.get("about_entity")
        if about_entity:
            target_id = f"entity:{about_entity}"
            self._merge_target_entity(target_id, about_entity, "concept", now)
            self._merge_edge(preference, "ABOUT", ("Entity", target_id), {})
        for event_id in source_event_ids:
            self._derived_from(preference, event_id, derivation_info, now)

    async def write_skill_with_edges(
        self,
        user_entity_id: str,
        skill_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        now = _iso_now()
        skill_id = skill_data.get("skill_id", f"skill:{uuid4().hex[:12]}")
        self._ensure_user_entity(user_entity_id, now)
        existing = self.data.nodes.get(("Skill", skill_id), {})
        self._merge_node(
            "Skill",
            skill_id,
            {
                "name": skill_data.get("name", ""),
                "category": skill_data.get("category", "domain_knowledge"),
                "description": skill_data.get("description"),
                "created_at": existing.get("created_at", now),
            },
        )
        skill = ("Skill", skill_id)
        user = ("Entity", user_entity_id)
        edge = self.data.edges.get((user, "HAS_SKILL", skill), {})
        self._merge_edge(
            user,
            "HAS_SKILL",
            skill,
            {
                "proficiency": skill_data.get("proficiency", 0.5),
                "confidence": skill_data.get("confidence", 0.5),
                "source": skill_data.get("source", "inferred"),
                "updated_at": now,
                "last_assessed_at": now,
                "assessment_count": int(edge.get("assessment_count") or 0) + 1,
            },
        )
        for event_id in source_event_ids:
            self._derived_from(skill, event_id, derivation_info, now)

    async def write_interest_edge(
        self,
        user_entity_id: str,
        entity_name: str,
        entity_type: str,
        weight: float,
        source: str,
    ) -> None:
        now = _iso_now()
        self._ensure_user_entity(user_entity_id, now)
        target_id = f"entity:{entity_name}"
        self._merge_target_entity(target_id, entity_name, entity_type, now)
        self._merge_edge(
            ("Entity", user_entity_id),
            "INTERESTED_IN",
            ("Entity", target_id),
            {"weight": weight, "source": source, "updated_at": now},
        )

    async def write_derived_from_edge(
        self,
        source_node_id: str,
        source_id_field: str,
        event_id: str,
        method: str,
        session_id: str,
    ) -> None:
        if source_id_field not in DERIVED_FROM_SOURCES:
            msg = (
                f"Unknown source_id_field: {source_id_field!r}. "
                f"Allowed: {sorted(DERIVED_FROM_SOURCES)}"
            )
            raise ValueError(msg)
        label = DERIVED_FROM_SOURCES[source_id_field]
        self._derived_from(
            (label, source_node_id),
            event_id,
            {"method": method, "session_id": session_id},
            _iso_now(),
        )

    async def set_preference_superseded(self, preference_id: str, superseded_by: str) -> None:
        props = self.data.nodes.get(("Preference", preference_id))
        if props is not None:
            _set(props, {"superseded_by": superseded_by})

    async def delete_user_data(self, user_id: str) -> int:
        user = ("Entity", user_id)
        if user not in self.data.nodes:
            return 0
        for edge_type in ("HAS_PROFILE", "HAS_PREFERENCE", "EXHIBITS_PATTERN"):
            for _src, _type, target in self.out_edges(user, edge_type):
                self._detach_delete(target)
        for edge_type in ("HAS_SKILL", "INTERESTED_IN"):
            for edge_key in self.out_edges(user, edge_type):
                del self.data.edges[edge_key]
        for edge_key in self.out_edges(user, "SAME_AS") + self.in_edges(user, "SAME_AS"):
            self.data.edges.pop(edge_key, None)
        _set(self.data.nodes[user], {"name": "REDACTED", "entity_type": "user"})
        return 1

    async def export_user_data(self, user_id: str) -> dict[str, Any]:
        user = ("Entity", user_id)
        profiles = self._user_targets(user_id, "HAS_PROFILE")
        provenance: list[dict[str, Any]] = []
        for edge_type, source_label, id_field in (
            ("HAS_PREFERENCE", "Preference", "preference_id"),
            ("HAS_SKILL", "Skill", "skill_id"),
        ):
            for _src, _type, source in self.out_edges(user, edge_type):
                for edge_key in self.out_edges(source, "DERIVED_FROM"):
                    edge = self.data.edges[edge_key]
                    provenance.append(
                        {
                            "source_id": self.data.nodes[source].get(id_field),
                            "source_type": source_label,
                            "event_id": self.data.nodes[edge_key[2]].get("event_id"),
                            "method": edge.get("method"),
                            "session_id": edge.get("session_id"),
                            "extracted_at": edge.get("extracted_at"),
                        }
                    )
        return {
            "user_id": user_id,
            "profile": dict(profiles[0]) if profiles else None,
            "preferences": [dict(p) for p in self._user_targets(user_id, "HAS_PREFERENCE")],
            "skills": [dict(s) for s in self._user_targets(user_id, "HAS_SKILL")],
            "patterns": [dict(p) for p in self._user_targets(user_id, "EXHIBITS_PATTERN")],
            "interests": self._interests(user_id),
            "provenance_chains": provenance,
        }
