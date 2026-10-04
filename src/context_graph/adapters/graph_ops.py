"""Generic graph operations over storage primitives (ADR-0019, ADR-0018).

``GraphOperations`` implements every method of the ``GraphBackend`` port
(GraphStore, GraphMaintenance, UserStore, and ``GraphReads`` via
``reads``) in terms of a few batch primitives a backend provides:

- ``_get_nodes(keys)``, ``_find_nodes(label, where)``
- ``_upsert_nodes(items)``, ``_delete_nodes(keys)`` (detach delete)
- ``_edges(sources=, targets=, edge_type=)``
- ``_upsert_edges(items)``, ``_delete_edges(keys)``, ``_clear()``

These are the "generic fallbacks built from the basic operations" of
ADR-0019 §1. A backend may override any method with a fast path; the
conformance suite checks both give the same answers. Semantics follow the
Neo4j adapter's Cypher, which the suites pin:

- nodes are keyed by label and id property (the uniqueness constraints);
- writes are MERGE: one node per key, one edge per (source, type, target);
- an edge whose endpoint does not exist is not created (MATCH fails);
- setting a property to None removes it;
- vector scores are ``(1 + cosine) / 2`` in [0, 1], as Neo4j's index.

Multi-step writes (a preference with its edges) are not atomic across
primitives; a backend that needs atomicity overrides the method.

Source: ADR-0009, ADR-0011, ADR-0012, ADR-0014, ADR-0018, ADR-0019
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import orjson
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
    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.ports.pack_graph import (
        Direction,
        EdgeWrite,
        NodeRef,
        NodeWrite,
        StateChange,
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


def key_property(label: str) -> str:
    """The property identifying nodes of ``label``: today's id field, else ``node_id``."""
    return LABEL_KEYS.get(label, "node_id")


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
EdgeRow = tuple[EdgeKey, dict[str, Any]]


def stored_values(values: dict[str, Any]) -> dict[str, Any]:
    """Property values as every backend stores them (PackGraph contract).

    None is not written; nested maps, and lists holding maps or lists,
    become JSON text, as Neo4j properties cannot hold them.
    """
    stored: dict[str, Any] = {}
    for name, value in values.items():
        if value is None:
            continue
        if isinstance(value, dict) or (
            isinstance(value, list) and any(isinstance(item, dict | list) for item in value)
        ):
            value = orjson.dumps(value).decode()
        stored[name] = value
    return stored


def state_change_applies(props: dict[str, Any] | None, change: StateChange) -> bool:
    """Whether a transition moves this node (it exists, is elsewhere, is allowed from here)."""
    if props is None or props.get("status") == change.to_state:
        return False
    return not change.only_from or props.get("status") in change.only_from


def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def apply_set(props: dict[str, Any], updates: dict[str, Any]) -> None:
    """Neo4j SET semantics: assign values, remove keys set to None."""
    for key, value in updates.items():
        if value is None:
            props.pop(key, None)
        else:
            props[key] = value


def newest_first(rows: list[dict[str, Any]], key: str = "occurred_at") -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: str(r.get(key, "")), reverse=True)


def cosine_score(query: list[float], vector: list[float]) -> float | None:
    """Neo4j cosine vector-index score, (1 + cosine) / 2; None if undefined."""
    if not vector or len(vector) != len(query):
        return None
    query_norm = math.sqrt(sum(v * v for v in query))
    norm = math.sqrt(sum(v * v for v in vector))
    if query_norm == 0 or norm == 0:
        return None
    cosine = sum(a * b for a, b in zip(query, vector, strict=True)) / (query_norm * norm)
    return (1.0 + cosine) / 2.0


class GraphOperations:
    """Every ``GraphBackend`` method, built on primitives a subclass supplies."""

    def __init__(
        self,
        *,
        decay_settings: DecaySettings | None = None,
        ppr_settings: PPRSettings | None = None,
        provenance_source: str = "memory",
    ) -> None:
        self._reads = GraphOperationReads(self)
        self._decay_settings = decay_settings
        self._ppr_settings = ppr_settings
        self._provenance_source = provenance_source
        self._engine: RetrievalEngine | None = None

    # ------------------------------------------------------------------
    # Primitives (subclasses implement)
    # ------------------------------------------------------------------

    async def _get_nodes(self, keys: list[NodeKey]) -> dict[NodeKey, dict[str, Any]]:
        """Properties of the nodes that exist, by key."""
        raise NotImplementedError

    async def _find_nodes(
        self, label: str, where: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Properties of nodes with ``label`` whose properties equal ``where``."""
        raise NotImplementedError

    async def _upsert_nodes(self, items: list[tuple[NodeKey, dict[str, Any]]]) -> None:
        """MERGE each node by key, then apply ``apply_set`` with the updates."""
        raise NotImplementedError

    async def _delete_nodes(self, keys: list[NodeKey]) -> int:
        """Detach-delete nodes; return how many existed."""
        raise NotImplementedError

    async def _edges(
        self,
        *,
        sources: list[NodeKey] | None = None,
        targets: list[NodeKey] | None = None,
        edge_type: str | None = None,
    ) -> list[EdgeRow]:
        """Edges matching every given filter (None means any)."""
        raise NotImplementedError

    async def _upsert_edges(self, items: list[tuple[EdgeKey, dict[str, Any]]]) -> int:
        """MERGE each edge whose endpoints both exist, then apply the updates."""
        raise NotImplementedError

    async def _delete_edges(self, keys: list[EdgeKey]) -> None:
        raise NotImplementedError

    async def _clear(self) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @property
    def reads(self) -> GraphOperationReads:
        return self._reads

    async def _node(self, key: NodeKey) -> dict[str, Any] | None:
        return (await self._get_nodes([key])).get(key)

    async def _merge_node(self, label: str, node_id: str, updates: dict[str, Any]) -> None:
        await self._upsert_nodes([((label, node_id), updates)])

    async def _merge_edge(
        self, source: NodeKey, edge_type: str, target: NodeKey, updates: dict[str, Any]
    ) -> None:
        await self._upsert_edges([((source, edge_type, target), updates)])

    async def _typed_edge_items(
        self, edges: list[tuple[str, str, str, dict[str, Any]]]
    ) -> list[tuple[EdgeKey, dict[str, Any]]]:
        items = []
        for source_id, target_id, edge_type, props in edges:
            source_label, target_label = EDGE_ENDPOINTS[edge_type]
            items.append((((source_label, source_id), edge_type, (target_label, target_id)), props))
        return items

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
        await self._merge_node("Event", node.event_id, self._event_props(node))

    async def merge_event_nodes_batch(self, nodes: list[EventNode]) -> None:
        if nodes:
            await self._upsert_nodes(
                [(("Event", node.event_id), self._event_props(node)) for node in nodes]
            )

    async def merge_entity_node(self, node: EntityNode) -> None:
        await self._merge_node(
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
        await self._merge_node(
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
        await self._merge_node(
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
        await self._merge_node(
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
        await self._merge_node(
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
        await self._merge_node(
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

    async def create_edge(self, edge: Edge) -> None:
        edge_type = str(edge.edge_type)
        if edge_type not in EDGE_ENDPOINTS:
            msg = f"Unknown edge type: {edge.edge_type}"
            raise ValueError(msg)
        await self._upsert_edges(
            await self._typed_edge_items(
                [(edge.source, edge.target, edge_type, dict(edge.properties))]
            )
        )

    async def create_edges_batch(self, edges: list[Edge]) -> None:
        typed = []
        for edge in edges:
            edge_type = str(edge.edge_type)
            if edge_type not in EDGE_ENDPOINTS:
                log.warning("skipping_unknown_edge_type", edge_type=edge_type)
                continue
            typed.append((edge.source, edge.target, edge_type, dict(edge.properties)))
        if typed:
            await self._upsert_edges(await self._typed_edge_items(typed))

    async def merge_typed_edge(
        self, source_id: str, target_id: str, edge_type: str, props: dict[str, Any] | None = None
    ) -> None:
        if edge_type not in EDGE_ENDPOINTS:
            msg = f"Unknown edge type: {edge_type}"
            raise ValueError(msg)
        await self._upsert_edges(
            await self._typed_edge_items([(source_id, target_id, edge_type, props or {})])
        )

    # ------------------------------------------------------------------
    # GraphStore: enrichment, entities, vectors
    # ------------------------------------------------------------------

    async def _update_existing(self, key: NodeKey, updates: dict[str, Any]) -> bool:
        if await self._node(key) is None:
            return False
        await self._upsert_nodes([(key, updates)])
        return True

    async def update_event_enrichment(
        self, event_id: str, keywords: list[str], importance_score: int
    ) -> None:
        await self._update_existing(
            ("Event", event_id), {"keywords": keywords, "importance_score": importance_score}
        )

    async def store_event_embedding(self, event_id: str, embedding: list[float]) -> None:
        await self._update_existing(("Event", event_id), {"embedding": embedding})

    async def adjust_node_importance(
        self,
        node_id: str,
        delta: int,
        min_value: int = 1,
        max_value: int = 10,
    ) -> bool:
        props = await self._node(("Event", node_id))
        if props is None:
            return False
        current = props.get("importance_score")
        if current is None:
            value = max(min_value, min(max_value, max(min_value, 5 + delta)))
        else:
            value = int(max(min_value, min(max_value, current + delta)))
        await self._upsert_nodes([(("Event", node_id), {"importance_score": value})])
        return True

    async def get_entities(self, limit: int = 1000) -> list[dict[str, Any]]:
        entities = await self._find_nodes("Entity")
        return [
            {
                "entity_id": p["entity_id"],
                "name": p.get("name"),
                "entity_type": p.get("entity_type"),
            }
            for p in entities[:limit]
        ]

    async def _referencing_events(self, entities: list[NodeKey]) -> list[dict[str, Any]]:
        rows = await self._edges(targets=entities, edge_type="REFERENCES")
        events = await self._get_nodes([edge_key[0] for edge_key, _props in rows])
        out = []
        for edge_key, props in rows:
            event = dict(events[edge_key[0]])
            event["ref_props"] = dict(props)
            out.append(event)
        return out

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        entity = ("Entity", entity_id)
        props = await self._node(entity)
        if props is None:
            return None
        events = newest_first(await self._referencing_events([entity]))[:ENTITY_EVENTS_LIMIT]
        return {"entity": dict(props), "connected_events": events}

    async def get_entity_with_cluster(self, entity_id: str) -> dict[str, Any] | None:
        start = ("Entity", entity_id)
        if await self._node(start) is None:
            return None
        cluster = [start]
        frontier = [start]
        for _hop in range(SAME_AS_MAX_HOPS):
            if not frontier:
                break
            outgoing = await self._edges(sources=frontier, edge_type="SAME_AS")
            incoming = await self._edges(targets=frontier, edge_type="SAME_AS")
            next_frontier = []
            for (source, _type, target), _props in outgoing + incoming:
                for other in (source, target):
                    if other not in cluster:
                        cluster.append(other)
                        next_frontier.append(other)
            frontier = next_frontier
        nodes = await self._get_nodes(cluster)
        return {
            "entities": {key[1]: dict(nodes[key]) for key in cluster if key in nodes},
            "connected_events": newest_first(await self._referencing_events(cluster))[
                :ENTITY_EVENTS_LIMIT
            ],
        }

    async def consolidate_entity_cluster(self, cluster_ids: list[str], canonical_id: str) -> None:
        if not cluster_ids or not canonical_id:
            return
        resolved_at = iso_now()
        await self._upsert_edges(
            [
                (
                    (("Entity", member_id), "SAME_AS", ("Entity", canonical_id)),
                    {
                        "confidence": 1.0,
                        "justification": "transitive_closure",
                        "resolved_at": resolved_at,
                    },
                )
                for member_id in cluster_ids
                if member_id != canonical_id
            ]
        )

    async def search_similar_entities(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.75,
    ) -> list[dict[str, Any]]:
        scored: list[tuple[float, dict[str, Any]]] = []
        for props in await self._find_nodes("Entity"):
            score = cosine_score(query_embedding, props.get("embedding") or [])
            if score is not None:
                scored.append((score, props))
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
    # PackGraph: generic operations for ontology packs (ADR-0018)
    # ------------------------------------------------------------------

    async def ensure_pack_schema(
        self, registry: OntologyRegistry, embedding_dimensions: int
    ) -> None:
        """Nothing to create: nodes and edges are stored by label and key."""

    @staticmethod
    def _ref_key(ref: NodeRef) -> NodeKey:
        return (ref.label, ref.key)

    async def _merge_nodes(
        self, items: list[tuple[NodeKey, dict[str, Any], dict[str, Any]]]
    ) -> None:
        """MERGE nodes, applying ``defaults`` only to the ones created.

        Reads, then writes; a backend with concurrent writers (Spanner)
        overrides this to do both in one transaction.
        """
        existing = await self._get_nodes([key for key, _u, _d in items])
        created: set[NodeKey] = set()
        merged: list[tuple[NodeKey, dict[str, Any]]] = []
        for key, updates, defaults in items:
            if key not in existing and key not in created:
                updates = {**defaults, **updates}
                created.add(key)
            merged.append((key, updates))
        await self._upsert_nodes(merged)

    async def _apply_state_changes(self, changes: list[StateChange]) -> int:
        """Apply transitions in order; Spanner overrides this to do it in one transaction."""
        changed = 0
        for change in changes:
            key = self._ref_key(change.ref)
            props = (await self._get_nodes([key])).get(key)
            if not state_change_applies(props, change):
                continue
            await self._upsert_nodes(
                [(key, {"status": change.to_state, "status_changed_at": change.changed_at})]
            )
            changed += 1
        return changed

    async def upsert_nodes(self, writes: list[NodeWrite]) -> None:
        if not writes:
            return
        items = []
        for write in writes:
            updates = stored_values(write.properties)
            updates[write.ref.key_property] = write.ref.key
            items.append((self._ref_key(write.ref), updates, stored_values(write.defaults)))
        await self._merge_nodes(items)

    async def upsert_edges(self, writes: list[EdgeWrite]) -> int:
        """Writes whose endpoints both exist; each write counts, repeated or not."""
        if not writes:
            return 0
        ends = {self._ref_key(w.source) for w in writes} | {self._ref_key(w.target) for w in writes}
        existing = await self._get_nodes(list(ends))
        items = [
            (
                (self._ref_key(w.source), w.edge_type, self._ref_key(w.target)),
                stored_values(w.properties),
            )
            for w in writes
            if self._ref_key(w.source) in existing and self._ref_key(w.target) in existing
        ]
        if items:
            await self._upsert_edges(items)
        return len(items)

    async def change_states(self, changes: list[StateChange]) -> int:
        return await self._apply_state_changes(changes) if changes else 0

    async def get_nodes(self, refs: list[NodeRef]) -> dict[NodeRef, dict[str, Any]]:
        found = await self._get_nodes([self._ref_key(r) for r in refs])
        return {ref: dict(found[key]) for ref in refs if (key := self._ref_key(ref)) in found}

    async def find_nodes(
        self, label: str, equals: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        rows = await self._find_nodes(label, stored_values(equals))
        key = key_property(label)
        rows = sorted(rows, key=lambda row: str(row.get(key, "")))
        return [dict(row) for row in rows[:limit]]

    async def search_nodes(
        self, label: str, fields: list[str], terms: list[str], limit: int
    ) -> list[tuple[dict[str, Any], int]]:
        if not terms or not fields:
            return []
        scored = []
        for props in await self._find_nodes(label, {}):
            texts: list[str] = []
            for field_name in fields:
                value = props.get(field_name)
                if isinstance(value, str):
                    texts.append(value.lower())
                elif isinstance(value, list):
                    texts.extend(item.lower() for item in value if isinstance(item, str))
            hits = sum(1 for term in terms if any(term in text for text in texts))
            if hits:
                scored.append((dict(props), hits))
        scored.sort(key=lambda row: (-row[1], str(row[0].get(key_property(label)))))
        return scored[:limit]

    async def neighbors(
        self,
        refs: list[NodeRef],
        edge_types: list[str] | None,
        direction: Direction,
        limit: int,
    ) -> list[dict[str, Any]]:
        keys = [self._ref_key(r) for r in refs]
        if not keys:
            return []
        rows: list[EdgeRow] = []
        if direction in ("out", "both"):
            rows += await self._edges(sources=keys)
        if direction in ("in", "both"):
            rows += await self._edges(targets=keys)
        wanted = set(keys)
        seen: set[EdgeKey] = set()
        picked: list[tuple[EdgeKey, dict[str, Any], NodeKey]] = []
        for edge_key, props in rows:
            source, edge_type, target = edge_key
            if edge_key in seen or (edge_types is not None and edge_type not in edge_types):
                continue
            seen.add(edge_key)
            other = target if source in wanted and direction != "in" else source
            picked.append((edge_key, props, other))
        picked.sort(key=lambda item: (item[0][1], item[0][0], item[0][2]))
        picked = picked[:limit]
        others = await self._get_nodes(list({other for _e, _p, other in picked}))
        return [
            {
                "edge_type": edge_key[1],
                "properties": dict(props),
                "source_label": edge_key[0][0],
                "source_key": edge_key[0][1],
                "target_label": edge_key[2][0],
                "target_key": edge_key[2][1],
                "node_label": other[0],
                "node": dict(others.get(other, {})),
            }
            for edge_key, props, other in picked
        ]

    # ------------------------------------------------------------------
    # GraphStore: schema, health, lifecycle (backends override as needed)
    # ------------------------------------------------------------------

    async def ensure_constraints(self) -> None:
        """Uniqueness is structural: nodes are keyed by label and id."""

    async def ensure_vector_indexes(self) -> None:
        """Nothing to create by default."""

    async def health_ping(self) -> bool:
        return True

    async def close(self) -> None:
        """Nothing to release by default."""

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
                provenance_source=self._provenance_source,
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

    async def get_session_event_counts(self) -> dict[str, int]:
        counts = Counter(
            p["session_id"]
            for p in await self._find_nodes("Event")
            if p.get("session_id") is not None
        )
        return dict(counts.most_common())

    async def get_graph_stats(self) -> dict[str, Any]:
        node_counts = {label: len(await self._find_nodes(label)) for label in STATS_NODE_LABELS}
        edge_counts = {
            edge_type: len(await self._edges(edge_type=edge_type)) for edge_type in STATS_EDGE_TYPES
        }
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
        await self._merge_node(
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
        if event_ids:
            await self._upsert_edges(
                [
                    (
                        (("Summary", summary_id), "SUMMARIZES", ("Event", event_id)),
                        {"created_at": created_at},
                    )
                    for event_id in event_ids
                ]
            )

    @staticmethod
    def _cutoff_iso(hours: int) -> str:
        return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

    async def delete_edges_by_type_and_age(self, min_score: float, max_age_hours: int) -> int:
        cutoff = self._cutoff_iso(max_age_hours)
        rows = await self._edges(edge_type="SIMILAR_TO")
        low = [
            (key, props)
            for key, props in rows
            if key[0][0] == "Event"
            and key[2][0] == "Event"
            and props.get("similarity_score") is not None
            and props["similarity_score"] < min_score
        ]
        sources = await self._get_nodes([key[0] for key, _props in low])
        doomed = [
            key
            for key, _props in low
            if key[0] in sources and str(sources[key[0]].get("occurred_at", "")) < cutoff
        ]
        if doomed:
            await self._delete_edges(doomed)
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
            for p in await self._find_nodes("Event")
            if str(p.get("occurred_at", "")) < cutoff
            and (p.get("importance_score") is None or p["importance_score"] < min_importance)
            and int(p.get("access_count") or 0) < min_access_count
        ]
        return await self._delete_nodes(doomed) if doomed else 0

    async def delete_archive_events(self, event_ids: list[str]) -> int:
        if not event_ids:
            return 0
        return await self._delete_nodes([("Event", event_id) for event_id in event_ids])

    async def get_archive_event_ids(self, max_age_hours: int) -> list[str]:
        cutoff = self._cutoff_iso(max_age_hours)
        return [
            p["event_id"]
            for p in await self._find_nodes("Event")
            if str(p.get("occurred_at", "")) < cutoff
        ]

    async def delete_orphan_nodes(self, batch_size: int = 500) -> tuple[dict[str, int], list[str]]:
        counts: dict[str, int] = {}
        deleted_entity_ids: list[str] = []
        for label in ORPHAN_LABELS:
            id_field = LABEL_KEYS[label]
            keys = [(label, p[id_field]) for p in await self._find_nodes(label)]
            connected: set[NodeKey] = set()
            if keys:
                for (source, _type, target), _props in await self._edges(
                    sources=keys
                ) + await self._edges(targets=keys):
                    connected.update((source, target))
            orphans = [key for key in keys if key not in connected]
            counts[label] = await self._delete_nodes(orphans) if orphans else 0
            if label == "Entity":
                deleted_entity_ids = [key[1] for key in orphans]
        return counts, deleted_entity_ids

    async def update_importance_from_centrality(self) -> int:
        events = await self._find_nodes("Event")
        in_degree = (
            Counter(
                key[2]
                for key, _props in await self._edges(
                    targets=[("Event", e["event_id"]) for e in events]
                )
            )
            if events
            else Counter()
        )
        updates = []
        for props in events:
            degree = in_degree.get(("Event", props["event_id"]), 0)
            if degree <= 0:
                continue
            if degree >= 10:
                value = 10
            elif degree >= 5:
                value = 8
            elif degree >= 3:
                value = 6
            else:
                value = props.get("importance_score") or 5
            updates.append((("Event", props["event_id"]), {"importance_score": value}))
        if updates:
            await self._upsert_nodes(updates)
        return len(updates)

    async def run_session_query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Not supported: query text never crosses a port (ADR-0019 C6)."""
        msg = "run_session_query is not supported by this backend; use a named operation"
        raise InvalidRequestError(msg)

    async def session_agent_id(self, session_id: str) -> str | None:
        events = await self._find_nodes("Event", {"session_id": session_id})
        if not events:
            return None
        agent_id: str | None = events[0].get("agent_id")
        return agent_id

    async def _session_in_time_order(self, session_id: str) -> list[dict[str, Any]]:
        events = await self._find_nodes("Event", {"session_id": session_id})
        return sorted(events, key=lambda p: str(p.get("occurred_at", "")))

    async def session_events(self, session_id: str, limit: int) -> list[dict[str, Any]]:
        return [dict(p) for p in (await self._session_in_time_order(session_id))[:limit]]

    async def session_event_timeline(self, session_id: str) -> list[dict[str, Any]]:
        fields = ("event_id", "event_type", "occurred_at", "tool_name", "status")
        return [
            {name: p.get(name) for name in fields}
            for p in await self._session_in_time_order(session_id)
        ]

    async def events_for_pruning(self, limit: int) -> list[dict[str, Any]]:
        ordered = sorted(
            await self._find_nodes("Event"), key=lambda p: str(p.get("occurred_at", ""))
        )
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
        await self._clear()
        log.warning("graph_deleted_all")

    # ------------------------------------------------------------------
    # UserStore (ADR-0012), mirroring adapters/neo4j/user_queries.py
    # ------------------------------------------------------------------

    async def _user_targets(self, user_id: str, edge_type: str) -> list[dict[str, Any]]:
        rows = await self._edges(sources=[("Entity", user_id)], edge_type=edge_type)
        targets = await self._get_nodes([key[2] for key, _props in rows])
        return [targets[key[2]] for key, _props in rows if key[2] in targets]

    async def _ensure_user_entity(self, user_entity_id: str, now: str) -> None:
        if await self._node(("Entity", user_entity_id)) is not None:
            return
        await self._merge_node(
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

    async def _merge_target_entity(
        self, entity_id: str, name: str, entity_type: str, now: str
    ) -> None:
        if await self._node(("Entity", entity_id)) is not None:
            await self._merge_node("Entity", entity_id, {"last_seen": now})
            return
        await self._merge_node(
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
        profiles = await self._user_targets(user_id, "HAS_PROFILE")
        return dict(profiles[0]) if profiles else None

    async def get_user_preferences(
        self, user_id: str, active_only: bool = True
    ) -> list[dict[str, Any]]:
        preferences = [
            p
            for p in await self._user_targets(user_id, "HAS_PREFERENCE")
            if not active_only or p.get("superseded_by") is None
        ]
        return [dict(p) for p in newest_first(preferences, "last_confirmed_at")]

    async def get_user_skills(self, user_id: str) -> list[dict[str, Any]]:
        skills = await self._user_targets(user_id, "HAS_SKILL")
        return [dict(s) for s in sorted(skills, key=lambda s: str(s.get("name", "")))]

    async def get_user_patterns(self, user_id: str) -> list[dict[str, Any]]:
        patterns = await self._user_targets(user_id, "EXHIBITS_PATTERN")
        return [dict(p) for p in newest_first(patterns, "last_confirmed_at")]

    async def _interests(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._edges(sources=[("Entity", user_id)], edge_type="INTERESTED_IN")
        targets = await self._get_nodes([key[2] for key, _props in rows])
        return [
            {
                "entity_id": targets[key[2]].get("entity_id"),
                "name": targets[key[2]].get("name"),
                "entity_type": targets[key[2]].get("entity_type"),
                "weight": props.get("weight"),
                "source": props.get("source"),
            }
            for key, props in rows
            if key[2] in targets
        ]

    async def get_user_interests(self, user_id: str) -> list[dict[str, Any]]:
        return sorted(
            await self._interests(user_id), key=lambda r: r.get("weight") or 0, reverse=True
        )

    async def write_user_profile(self, profile_data: dict[str, Any]) -> None:
        now = iso_now()
        user_id = profile_data.get("user_id", "")
        profile_id = profile_data.get("profile_id", f"profile:{user_id}")
        display_name = profile_data.get("display_name")
        if await self._node(("Entity", user_id)) is not None:
            await self._merge_node("Entity", user_id, {"last_seen": now})
        else:
            await self._merge_node(
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
        existing = await self._node(("UserProfile", profile_id)) or {}
        await self._merge_node(
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
        await self._merge_edge(("Entity", user_id), "HAS_PROFILE", ("UserProfile", profile_id), {})

    async def _derived_from(
        self,
        source: NodeKey,
        event_ids: list[str],
        derivation_info: dict[str, Any],
        now: str,
    ) -> None:
        if not event_ids:
            return
        props = {
            "method": derivation_info.get("method", "llm_extraction"),
            "session_id": derivation_info.get("session_id", ""),
            "extracted_at": now,
            "model_id": derivation_info.get("model_id"),
            "prompt_version": derivation_info.get("prompt_version"),
            "evidence_quote": derivation_info.get("evidence_quote"),
            "source_turn_index": derivation_info.get("source_turn_index"),
        }
        await self._upsert_edges(
            [((source, "DERIVED_FROM", ("Event", event_id)), dict(props)) for event_id in event_ids]
        )

    async def write_preference_with_edges(
        self,
        user_entity_id: str,
        preference_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        now = iso_now()
        preference_id = preference_data.get("preference_id", f"pref:{uuid4().hex[:12]}")
        await self._ensure_user_entity(user_entity_id, now)
        existing = await self._node(("Preference", preference_id)) or {}
        await self._merge_node(
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
        await self._merge_edge(("Entity", user_entity_id), "HAS_PREFERENCE", preference, {})
        about_entity = preference_data.get("about_entity")
        if about_entity:
            target_id = f"entity:{about_entity}"
            await self._merge_target_entity(target_id, about_entity, "concept", now)
            await self._merge_edge(preference, "ABOUT", ("Entity", target_id), {})
        await self._derived_from(preference, source_event_ids, derivation_info, now)

    async def write_skill_with_edges(
        self,
        user_entity_id: str,
        skill_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        now = iso_now()
        skill_id = skill_data.get("skill_id", f"skill:{uuid4().hex[:12]}")
        await self._ensure_user_entity(user_entity_id, now)
        existing = await self._node(("Skill", skill_id)) or {}
        await self._merge_node(
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
        current = await self._edges(sources=[user], targets=[skill], edge_type="HAS_SKILL")
        assessments = int(current[0][1].get("assessment_count") or 0) if current else 0
        await self._merge_edge(
            user,
            "HAS_SKILL",
            skill,
            {
                "proficiency": skill_data.get("proficiency", 0.5),
                "confidence": skill_data.get("confidence", 0.5),
                "source": skill_data.get("source", "inferred"),
                "updated_at": now,
                "last_assessed_at": now,
                "assessment_count": assessments + 1,
            },
        )
        await self._derived_from(skill, source_event_ids, derivation_info, now)

    async def write_interest_edge(
        self,
        user_entity_id: str,
        entity_name: str,
        entity_type: str,
        weight: float,
        source: str,
    ) -> None:
        now = iso_now()
        await self._ensure_user_entity(user_entity_id, now)
        target_id = f"entity:{entity_name}"
        await self._merge_target_entity(target_id, entity_name, entity_type, now)
        await self._merge_edge(
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
        await self._derived_from(
            (DERIVED_FROM_SOURCES[source_id_field], source_node_id),
            [event_id],
            {"method": method, "session_id": session_id},
            iso_now(),
        )

    async def set_preference_superseded(self, preference_id: str, superseded_by: str) -> None:
        await self._update_existing(("Preference", preference_id), {"superseded_by": superseded_by})

    async def delete_user_data(self, user_id: str) -> int:
        user = ("Entity", user_id)
        if await self._node(user) is None:
            return 0
        owned: list[NodeKey] = []
        for edge_type in ("HAS_PROFILE", "HAS_PREFERENCE", "EXHIBITS_PATTERN"):
            owned.extend(
                key[2] for key, _props in await self._edges(sources=[user], edge_type=edge_type)
            )
        if owned:
            await self._delete_nodes(owned)
        dropped: list[EdgeKey] = []
        for edge_type in ("HAS_SKILL", "INTERESTED_IN", "SAME_AS"):
            dropped.extend(
                key for key, _p in await self._edges(sources=[user], edge_type=edge_type)
            )
        dropped.extend(key for key, _p in await self._edges(targets=[user], edge_type="SAME_AS"))
        if dropped:
            await self._delete_edges(dropped)
        await self._merge_node("Entity", user_id, {"name": "REDACTED", "entity_type": "user"})
        return 1

    async def export_user_data(self, user_id: str) -> dict[str, Any]:
        user = ("Entity", user_id)
        profiles = await self._user_targets(user_id, "HAS_PROFILE")
        provenance: list[dict[str, Any]] = []
        for edge_type, source_label in (
            ("HAS_PREFERENCE", "Preference"),
            ("HAS_SKILL", "Skill"),
        ):
            sources = [key[2] for key, _p in await self._edges(sources=[user], edge_type=edge_type)]
            if not sources:
                continue
            for (source, _type, target), props in await self._edges(
                sources=sources, edge_type="DERIVED_FROM"
            ):
                provenance.append(
                    {
                        "source_id": source[1],
                        "source_type": source_label,
                        "event_id": target[1],
                        "method": props.get("method"),
                        "session_id": props.get("session_id"),
                        "extracted_at": props.get("extracted_at"),
                    }
                )
        return {
            "user_id": user_id,
            "profile": dict(profiles[0]) if profiles else None,
            "preferences": [dict(p) for p in await self._user_targets(user_id, "HAS_PREFERENCE")],
            "skills": [dict(s) for s in await self._user_targets(user_id, "HAS_SKILL")],
            "patterns": [dict(p) for p in await self._user_targets(user_id, "EXHIBITS_PATTERN")],
            "interests": await self._interests(user_id),
            "provenance_chains": provenance,
        }


class GraphOperationReads:
    """``GraphReads`` built on a ``GraphOperations`` backend's primitives."""

    def __init__(self, ops: GraphOperations) -> None:
        self._ops = ops

    async def _session_events(self, session_id: str | None) -> list[dict[str, Any]]:
        return await self._ops._find_nodes("Event", {"session_id": session_id})

    async def seed_events(
        self,
        strategy: str,
        session_id: str | None,
        limit: int,
        *,
        timeout_s: float | None = None,
    ) -> list[dict[str, Any]]:
        ops = self._ops
        events = await self._session_events(session_id)
        keys = [("Event", p["event_id"]) for p in events]

        def ranked(rows: list[tuple[float, dict[str, Any]]]) -> list[dict[str, Any]]:
            by_time = sorted(rows, key=lambda r: str(r[1].get("occurred_at", "")), reverse=True)
            ordered = sorted(by_time, key=lambda r: r[0], reverse=True)
            return [dict(props) for _score, props in ordered[:limit]]

        if strategy == "causal_roots":
            caused = (
                Counter(key[2] for key, _p in await ops._edges(targets=keys, edge_type="CAUSED_BY"))
                if keys
                else Counter()
            )
            return ranked(
                [
                    (float(caused[("Event", p["event_id"])]), p)
                    for p in events
                    if caused[("Event", p["event_id"])]
                ]
            )
        if strategy == "entity_hubs":
            refs = (
                Counter(
                    key[0] for key, _p in await ops._edges(sources=keys, edge_type="REFERENCES")
                )
                if keys
                else Counter()
            )
            return ranked(
                [
                    (float(refs[("Event", p["event_id"])]), p)
                    for p in events
                    if refs[("Event", p["event_id"])]
                ]
            )
        if strategy == "temporal_anchors":
            anchored = [p for p in events if p.get("importance_score") is not None]
            by_time = sorted(anchored, key=lambda p: str(p.get("occurred_at", "")))
            ordered = sorted(by_time, key=lambda p: p["importance_score"], reverse=True)
            return [dict(p) for p in ordered[:limit]]
        if strategy == "user_profile":
            references = await ops._edges(sources=keys, edge_type="REFERENCES") if keys else []
            entities = sorted({key[2] for key, _p in references})
            profiled: set[NodeKey] = set()
            if entities:
                for edge_type in ("HAS_PROFILE", "HAS_PREFERENCE"):
                    profiled.update(
                        key[0]
                        for key, _p in await ops._edges(sources=entities, edge_type=edge_type)
                    )
            linked = Counter(key[0] for key, _p in references if key[2] in profiled)
            return ranked(
                [
                    (float(linked[("Event", p["event_id"])]), p)
                    for p in events
                    if linked[("Event", p["event_id"])]
                ]
            )
        if strategy == "similar_cluster":
            similar: Counter[NodeKey] = Counter()
            if keys:
                for key, _p in await ops._edges(sources=keys, edge_type="SIMILAR_TO"):
                    similar[key[0]] += 1
                for key, _p in await ops._edges(targets=keys, edge_type="SIMILAR_TO"):
                    similar[key[2]] += 1
            return ranked([(float(similar[("Event", p["event_id"])]), p) for p in events])
        if strategy == "workflow_pattern":
            matching = [
                p for p in events if str(p.get("event_type", "")).startswith(("tool.", "workflow."))
            ]
            ordered = sorted(matching, key=lambda p: str(p.get("occurred_at", "")))
            return [dict(p) for p in ordered[:limit]]
        # "general" and unknown strategies: most recent events
        return [dict(p) for p in newest_first(events)[:limit]]

    async def get_event_nodes(
        self, event_ids: list[str], *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        nodes = await self._ops._get_nodes([("Event", eid) for eid in event_ids])
        return [dict(nodes[("Event", eid)]) for eid in event_ids if ("Event", eid) in nodes]

    async def cross_session_entity_events(
        self, session_id: str | None, limit: int, *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        ops = self._ops
        keys = [("Event", p["event_id"]) for p in await self._session_events(session_id)]
        if not keys:
            return []
        entities: list[NodeKey] = []
        for key, _p in await ops._edges(sources=keys, edge_type="REFERENCES"):
            if key[2] not in entities:
                entities.append(key[2])
        if not entities:
            return []
        references = await ops._edges(targets=entities, edge_type="REFERENCES")
        events = await ops._get_nodes([key[0] for key, _p in references])
        rows = [
            events[key[0]]
            for key, _p in references
            if key[0] in events and events[key[0]].get("session_id") != session_id
        ]
        return [dict(r) for r in newest_first(rows)[:limit]]

    async def event_neighbors(
        self, event_ids: list[str], neighbor_limit: int, *, timeout_s: float | None = None
    ) -> list[dict[str, Any]]:
        ops = self._ops
        seeds = [("Event", eid) for eid in event_ids]
        existing = await ops._get_nodes(seeds)
        outgoing = await ops._edges(sources=[s for s in seeds if s in existing]) if existing else []
        targets = await ops._get_nodes(sorted({key[2] for key, _p in outgoing}))
        by_seed: dict[NodeKey, list[tuple[EdgeKey, dict[str, Any]]]] = {}
        for key, props in outgoing:
            by_seed.setdefault(key[0], []).append((key, props))
        rows: list[dict[str, Any]] = []
        for seed in seeds:
            if seed not in existing:
                continue
            edges = by_seed.get(seed, [])
            if not edges:
                rows.append(dict.fromkeys(NEIGHBOR_ROW_KEYS) | {"seed_event_id": seed[1]})
            for (_src, edge_type, target), props in edges:
                target_props = targets.get(target, {})
                rows.append(
                    {
                        "seed_event_id": seed[1],
                        "rel_type": edge_type,
                        "rel_props": dict(props),
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
        events = await self._session_events(session_id)
        if after is None:
            return [dict(p) for p in newest_first(events)[:limit]]
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
        ops = self._ops
        keys = [("Event", eid) for eid in event_ids]
        if not keys:
            return []
        nodes = await ops._get_nodes(keys)
        rows = []
        for (source, edge_type, target), props in await ops._edges(sources=keys, targets=keys):
            if source not in nodes or target not in nodes:
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
        ops = self._ops
        start = ("Event", node_id)
        if await ops._node(start) is None:
            return []
        hop_limit = min(max_depth, LINEAGE_MAX_HOPS)
        chains: list[list[EdgeRow]] = []
        frontier: list[list[EdgeRow]] = [[]]
        # Breadth-first over paths, no repeated edge within a path (TRAIL)
        while frontier and len(chains) < max_nodes:
            tips = sorted({path[-1][0][2] if path else start for path in frontier})
            outgoing = await ops._edges(sources=tips, edge_type="CAUSED_BY")
            by_source: dict[NodeKey, list[EdgeRow]] = {}
            for row in outgoing:
                by_source.setdefault(row[0][0], []).append(row)
            next_frontier: list[list[EdgeRow]] = []
            for path in frontier:
                tip = path[-1][0][2] if path else start
                used = {row[0] for row in path}
                for row in by_source.get(tip, []):
                    if row[0] in used:
                        continue
                    extended = [*path, row]
                    chains.append(extended)
                    if len(extended) < hop_limit:
                        next_frontier.append(extended)
            frontier = next_frontier
        chains = chains[:max_nodes]
        node_keys = {start} | {row[0][2] for chain in chains for row in chain}
        nodes = await ops._get_nodes(sorted(node_keys))
        return [
            {
                "nodes": [dict(nodes.get(start, {}))]
                + [dict(nodes.get(row[0][2], {})) for row in chain],
                "edges": [
                    {
                        "source": row[0][0][1],
                        "target": row[0][2][1],
                        "properties": dict(row[1]),
                    }
                    for row in chain
                ],
            }
            for chain in chains
        ]

    async def record_access(self, event_ids: list[str], accessed_at: str) -> None:
        ops = self._ops
        counts = Counter(event_ids)
        nodes = await ops._get_nodes([("Event", eid) for eid in counts])
        updates = [
            (
                key,
                {
                    "access_count": int(props.get("access_count") or 0) + counts[key[1]],
                    "last_accessed_at": accessed_at,
                },
            )
            for key, props in nodes.items()
        ]
        if updates:
            await ops._upsert_nodes(updates)
