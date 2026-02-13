"""Neo4j GraphStore adapter.

Implements the GraphStore protocol using the neo4j async driver.
All writes use MERGE for idempotent upserts. Datetimes are stored
as ISO 8601 strings for Python driver compatibility.

Source: ADR-0003, ADR-0005, ADR-0009
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from neo4j import AsyncGraphDatabase

from context_graph.adapters.neo4j import queries
from context_graph.domain.intent import classify_intent, get_edge_weights
from context_graph.domain.lineage import validate_traversal_bounds
from context_graph.domain.models import (
    AtlasEdge,
    AtlasNode,
    AtlasResponse,
    EdgeType,
    NodeScores,
    Pagination,
    Provenance,
    QueryCapacity,
    QueryMeta,
)
from context_graph.domain.scoring import score_node
from context_graph.settings import INTENT_WEIGHTS

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from context_graph.domain.models import (
        Edge,
        EntityNode,
        EventNode,
        LineageQuery,
        SubgraphQuery,
        SummaryNode,
    )
    from context_graph.settings import Neo4jSettings

logger = structlog.get_logger(__name__)

# Map EdgeType -> Cypher MERGE template
_EDGE_QUERIES: dict[str, str] = {
    EdgeType.FOLLOWS: queries.MERGE_FOLLOWS,
    EdgeType.CAUSED_BY: queries.MERGE_CAUSED_BY,
    EdgeType.SIMILAR_TO: queries.MERGE_SIMILAR_TO,
    EdgeType.REFERENCES: queries.MERGE_REFERENCES,
    EdgeType.SUMMARIZES: queries.MERGE_SUMMARIZES,
    EdgeType.SAME_AS: queries.MERGE_SAME_AS,
    EdgeType.RELATED_TO: queries.MERGE_RELATED_TO,
    EdgeType.HAS_PROFILE: queries.MERGE_HAS_PROFILE,
    EdgeType.HAS_PREFERENCE: queries.MERGE_HAS_PREFERENCE,
    EdgeType.HAS_SKILL: queries.MERGE_HAS_SKILL,
    EdgeType.DERIVED_FROM: queries.MERGE_DERIVED_FROM,
    EdgeType.EXHIBITS_PATTERN: queries.MERGE_EXHIBITS_PATTERN,
    EdgeType.INTERESTED_IN: queries.MERGE_INTERESTED_IN,
    EdgeType.ABOUT: queries.MERGE_ABOUT,
    EdgeType.ABSTRACTED_FROM: queries.MERGE_ABSTRACTED_FROM,
    EdgeType.PARENT_SKILL: queries.MERGE_PARENT_SKILL,
}

# Map EdgeType -> UNWIND batch template (only for high-volume types)
_BATCH_EDGE_QUERIES: dict[str, str] = {
    EdgeType.FOLLOWS: queries.BATCH_MERGE_FOLLOWS,
    EdgeType.CAUSED_BY: queries.BATCH_MERGE_CAUSED_BY,
}


class Neo4jGraphStore:
    """Neo4j implementation of the GraphStore protocol.

    Phase 2 implements: merge_event_node, merge_entity_node, merge_summary_node,
    create_edge, create_edges_batch, ensure_constraints, close.

    Phase 3+ methods raise NotImplementedError.
    """

    def __init__(self, settings: Neo4jSettings) -> None:
        self._settings = settings
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            settings.uri,
            auth=(settings.username, settings.password),
            max_connection_pool_size=settings.max_connection_pool_size,
        )
        self._database = settings.database

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    async def merge_event_node(self, node: EventNode) -> None:
        """MERGE an event node into the graph. Idempotent."""
        params = {
            "event_id": node.event_id,
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
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(queries.MERGE_EVENT_NODE, params))
        logger.debug("merged_event_node", event_id=node.event_id)

    async def merge_entity_node(self, node: EntityNode) -> None:
        """MERGE an entity node into the graph. Idempotent."""
        params = {
            "entity_id": node.entity_id,
            "name": node.name,
            "entity_type": str(node.entity_type),
            "first_seen": node.first_seen.isoformat(),
            "last_seen": node.last_seen.isoformat(),
            "mention_count": node.mention_count,
        }
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(queries.MERGE_ENTITY_NODE, params))
        logger.debug("merged_entity_node", entity_id=node.entity_id)

    async def merge_summary_node(self, node: SummaryNode) -> None:
        """MERGE a summary node into the graph. Idempotent."""
        params = {
            "summary_id": node.summary_id,
            "scope": node.scope,
            "scope_id": node.scope_id,
            "content": node.content,
            "created_at": node.created_at.isoformat(),
            "event_count": node.event_count,
            "time_range": [dt.isoformat() for dt in node.time_range],
        }
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(queries.MERGE_SUMMARY_NODE, params))
        logger.debug("merged_summary_node", summary_id=node.summary_id)

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    async def create_edge(self, edge: Edge) -> None:
        """Create or update an edge between two nodes."""
        query = _EDGE_QUERIES.get(edge.edge_type)
        if query is None:
            msg = f"Unknown edge type: {edge.edge_type}"
            raise ValueError(msg)

        params = {
            "source_id": edge.source,
            "target_id": edge.target,
            "props": edge.properties,
        }
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(query, params))
        logger.debug(
            "created_edge",
            edge_type=edge.edge_type,
            source=edge.source,
            target=edge.target,
        )

    async def create_edges_batch(self, edges: list[Edge]) -> None:
        """Create or update edges in batch.

        Groups edges by type. Types with UNWIND batch templates use a single
        query per type. Other types fall back to individual MERGE operations.
        """
        if not edges:
            return

        # Group edges by type
        edges_by_type: dict[str, list[Edge]] = {}
        for edge in edges:
            edges_by_type.setdefault(edge.edge_type, []).append(edge)

        async with self._driver.session(database=self._database) as session:

            async def _write_batch(tx: Any) -> None:
                for edge_type, typed_edges in edges_by_type.items():
                    batch_query = _BATCH_EDGE_QUERIES.get(edge_type)
                    if batch_query is not None:
                        # Use UNWIND batch for supported types
                        edge_params = [
                            {
                                "source_id": e.source,
                                "target_id": e.target,
                                "props": e.properties,
                            }
                            for e in typed_edges
                        ]
                        await tx.run(batch_query, {"edges": edge_params})
                    else:
                        # Fall back to individual MERGE for other types
                        query = _EDGE_QUERIES.get(edge_type)
                        if query is None:
                            logger.warning("skipping_unknown_edge_type", edge_type=edge_type)
                            continue
                        for e in typed_edges:
                            await tx.run(
                                query,
                                {
                                    "source_id": e.source,
                                    "target_id": e.target,
                                    "props": e.properties,
                                },
                            )

            await session.execute_write(_write_batch)

        logger.debug("created_edges_batch", count=len(edges))

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    async def ensure_constraints(self) -> None:
        """Create uniqueness constraints if they do not exist."""
        async with self._driver.session(database=self._database) as session:
            for constraint_query in queries.ALL_CONSTRAINTS:
                await session.run(constraint_query)
        logger.info("ensured_constraints", count=len(queries.ALL_CONSTRAINTS))

    # ------------------------------------------------------------------
    # Phase 3: Query methods
    # ------------------------------------------------------------------

    def _build_atlas_node(
        self,
        record_props: dict[str, Any],
        scores: NodeScores,
        retrieval_reason: str = "direct",
    ) -> AtlasNode:
        """Convert Neo4j record properties to an AtlasNode with provenance."""
        event_id = record_props.get("event_id", "")
        occurred_at_raw = record_props.get("occurred_at")
        if isinstance(occurred_at_raw, str):
            occurred_at = datetime.fromisoformat(occurred_at_raw)
        else:
            occurred_at = datetime.now(UTC)

        provenance = Provenance(
            event_id=event_id,
            global_position=record_props.get("global_position", ""),
            source="redis",
            occurred_at=occurred_at,
            session_id=record_props.get("session_id", ""),
            agent_id=record_props.get("agent_id", ""),
            trace_id=record_props.get("trace_id", ""),
        )

        attributes = {
            k: v
            for k, v in record_props.items()
            if k
            not in {
                "event_id",
                "global_position",
                "session_id",
                "agent_id",
                "trace_id",
            }
        }

        return AtlasNode(
            node_id=event_id,
            node_type="Event",
            attributes=attributes,
            provenance=provenance,
            scores=scores,
            retrieval_reason=retrieval_reason,
        )

    async def _bump_access_counts(self, event_ids: list[str]) -> None:
        """Increment access_count for a batch of event nodes."""
        if not event_ids:
            return
        now_iso = datetime.now(UTC).isoformat()
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(
                lambda tx: tx.run(
                    queries.BATCH_UPDATE_ACCESS_COUNT,
                    {"event_ids": event_ids, "now": now_iso},
                )
            )

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
    ) -> AtlasResponse:
        """Assemble working memory context for a session."""
        start_ms = time.monotonic_ns()

        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                queries.GET_SESSION_EVENTS,
                {"session_id": session_id, "limit": max_nodes},
            )
            records = [record async for record in result]

        nodes: dict[str, AtlasNode] = {}
        scored_entries: list[tuple[str, dict[str, Any], NodeScores]] = []

        for record in records:
            props = dict(record["e"])
            event_id = props.get("event_id", "")
            scores = score_node(props)
            scored_entries.append((event_id, props, scores))

        # Sort by composite decay_score descending, take top max_nodes
        scored_entries.sort(key=lambda x: x[2].decay_score, reverse=True)
        scored_entries = scored_entries[:max_nodes]

        for event_id, props, scores in scored_entries:
            nodes[event_id] = self._build_atlas_node(props, scores)

        # Bump access counts
        event_ids = [eid for eid, _, _ in scored_entries]
        await self._bump_access_counts(event_ids)

        elapsed_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)

        meta = QueryMeta(
            query_ms=elapsed_ms,
            nodes_returned=len(nodes),
            truncated=len(records) >= max_nodes,
            capacity=QueryCapacity(
                max_nodes=max_nodes,
                used_nodes=len(nodes),
                max_depth=1,
            ),
        )

        return AtlasResponse(
            nodes=nodes,
            edges=[],
            pagination=Pagination(),
            meta=meta,
        )

    async def get_lineage(self, query: LineageQuery) -> AtlasResponse:
        """Traverse lineage (CAUSED_BY chains) from a node."""
        start_ms = time.monotonic_ns()

        clamped_depth, clamped_nodes, _timeout = validate_traversal_bounds(
            max_depth=query.max_depth,
            max_nodes=query.max_nodes,
            timeout_ms=5000,
        )

        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                queries.GET_LINEAGE,
                {
                    "node_id": query.node_id,
                    "max_depth": clamped_depth,
                    "max_nodes": clamped_nodes,
                },
            )
            records = [record async for record in result]

        nodes: dict[str, AtlasNode] = {}
        edges: list[AtlasEdge] = []
        seen_edges: set[tuple[str, str]] = set()

        for record in records:
            chain_nodes = record["chain_nodes"]
            chain_rels = record["chain_rels"]

            for neo_node in chain_nodes:
                props = dict(neo_node)
                event_id = props.get("event_id", "")
                if event_id and event_id not in nodes:
                    scores = score_node(props)
                    nodes[event_id] = self._build_atlas_node(props, scores)

            for rel in chain_rels:
                start_eid = dict(rel.start_node).get("event_id", "")
                end_eid = dict(rel.end_node).get("event_id", "")
                edge_key = (start_eid, end_eid)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append(
                        AtlasEdge(
                            source=start_eid,
                            target=end_eid,
                            edge_type="CAUSED_BY",
                            properties=dict(rel),
                        )
                    )

        await self._bump_access_counts(list(nodes.keys()))

        elapsed_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)

        meta = QueryMeta(
            query_ms=elapsed_ms,
            nodes_returned=len(nodes),
            truncated=len(nodes) >= clamped_nodes,
            capacity=QueryCapacity(
                max_nodes=clamped_nodes,
                used_nodes=len(nodes),
                max_depth=clamped_depth,
            ),
        )

        return AtlasResponse(
            nodes=nodes,
            edges=edges,
            pagination=Pagination(),
            meta=meta,
        )

    async def get_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        """Execute an intent-aware subgraph query."""
        start_ms = time.monotonic_ns()

        # Classify intent from the query text
        inferred_intents = classify_intent(query.query)

        # If explicit intent override, use that
        if query.intent is not None:
            inferred_intents = {str(query.intent): 1.0}

        # Get edge weights based on intents
        edge_weights = get_edge_weights(inferred_intents, INTENT_WEIGHTS)

        # Get seed events from the session
        async with self._driver.session(database=self._database) as session:
            seed_result = await session.run(
                queries.GET_SUBGRAPH_SEED_EVENTS,
                {"session_id": query.session_id, "seed_limit": min(10, query.max_nodes)},
            )
            seed_records = [record async for record in seed_result]

        nodes: dict[str, AtlasNode] = {}
        edges: list[AtlasEdge] = []
        seen_edges: set[tuple[str, str, str]] = set()
        seed_node_ids: list[str] = []

        # Process seed events
        for record in seed_records:
            props = dict(record["e"])
            event_id = props.get("event_id", "")
            if event_id:
                seed_node_ids.append(event_id)
                scores = score_node(props)
                nodes[event_id] = self._build_atlas_node(props, scores)

        # Override with user-provided seed_nodes if specified
        if query.seed_nodes:
            seed_node_ids = list(query.seed_nodes)
            # Fetch properties for user-provided seeds
            for seed_id in query.seed_nodes:
                if seed_id not in nodes:
                    async with self._driver.session(database=self._database) as session:
                        result = await session.run(
                            "MATCH (e:Event {event_id: $eid}) RETURN e",
                            {"eid": seed_id},
                        )
                        seed_record = await result.single()
                    if seed_record is not None:
                        props = dict(seed_record["e"])
                        scores = score_node(props)
                        nodes[seed_id] = self._build_atlas_node(props, scores)

        # For each seed, traverse neighbors
        async with self._driver.session(database=self._database) as session:
            for seed_eid in seed_node_ids:
                neighbor_result = await session.run(
                    queries.GET_EVENT_NEIGHBORS,
                    {"event_id": seed_eid},
                )
                neighbor_records = [record async for record in neighbor_result]

                for nrec in neighbor_records:
                    rel_type = nrec.get("rel_type")
                    if rel_type is None:
                        continue

                    neighbor_eid = nrec.get("neighbor_event_id")
                    neighbor_entity_id = nrec.get("neighbor_entity_id")
                    neighbor_id = neighbor_eid or neighbor_entity_id or ""
                    if not neighbor_id:
                        continue

                    # Apply edge weight as a score boost
                    weight = edge_weights.get(rel_type, 1.0)

                    if neighbor_eid and neighbor_eid not in nodes:
                        neighbor_props = nrec.get("neighbor_props", {}) or {}
                        nscores = score_node(neighbor_props)
                        # Boost the decay score by edge weight relevance
                        boosted_score = min(
                            1.0,
                            nscores.decay_score * (1.0 + weight * 0.1),
                        )
                        boosted_scores = NodeScores(
                            decay_score=round(boosted_score, 6),
                            relevance_score=nscores.relevance_score,
                            importance_score=nscores.importance_score,
                        )
                        proactive_signal = {
                            "REFERENCES": "entity_context",
                            "SIMILAR_TO": "recurring_pattern",
                            "CAUSED_BY": "causal_chain",
                            "FOLLOWS": "temporal_sequence",
                            "SUMMARIZES": "summary_context",
                        }.get(rel_type, "related_context")
                        atlas_node = self._build_atlas_node(
                            neighbor_props,
                            boosted_scores,
                            retrieval_reason="proactive",
                        )
                        atlas_node.proactive_signal = proactive_signal
                        nodes[neighbor_eid] = atlas_node

                    edge_key = (seed_eid, neighbor_id, rel_type)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        rel_props = nrec.get("rel_props", {}) or {}
                        edges.append(
                            AtlasEdge(
                                source=seed_eid,
                                target=neighbor_id,
                                edge_type=rel_type,
                                properties=rel_props,
                            )
                        )

        # Sort all nodes by score, take top max_nodes
        sorted_node_ids = sorted(
            nodes.keys(),
            key=lambda nid: nodes[nid].scores.decay_score,
            reverse=True,
        )
        if len(sorted_node_ids) > query.max_nodes:
            keep_set = set(sorted_node_ids[: query.max_nodes])
            nodes = {k: v for k, v in nodes.items() if k in keep_set}

        # Bump access counts for event nodes only
        event_ids = [nid for nid in nodes if nid.startswith("evt")]
        await self._bump_access_counts(event_ids)

        elapsed_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)

        proactive_count = sum(1 for n in nodes.values() if n.retrieval_reason == "proactive")

        meta = QueryMeta(
            query_ms=elapsed_ms,
            nodes_returned=len(nodes),
            truncated=len(sorted_node_ids) > query.max_nodes,
            inferred_intents=inferred_intents,
            intent_override=str(query.intent) if query.intent is not None else None,
            seed_nodes=seed_node_ids,
            proactive_nodes_count=proactive_count,
            capacity=QueryCapacity(
                max_nodes=query.max_nodes,
                used_nodes=len(nodes),
                max_depth=query.max_depth,
            ),
        )

        return AtlasResponse(
            nodes=nodes,
            edges=edges,
            pagination=Pagination(),
            meta=meta,
        )

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity and its connected events."""
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                queries.GET_ENTITY_WITH_EVENTS,
                {"entity_id": entity_id, "limit": 100},
            )
            records = [record async for record in result]

        if not records:
            return None

        # First record always has the entity
        entity_props = dict(records[0]["ent"])

        connected_events: list[dict[str, Any]] = []
        for record in records:
            evt = record.get("evt")
            if evt is not None:
                evt_dict = dict(evt)
                ref_props = record.get("ref_props", {}) or {}
                evt_dict["ref_props"] = ref_props
                connected_events.append(evt_dict)

        return {
            "entity": entity_props,
            "connected_events": connected_events,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Release connections."""
        await self._driver.close()
        logger.info("neo4j_driver_closed")
