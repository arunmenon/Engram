"""Neo4j GraphStore adapter.

Implements the GraphStore protocol using the neo4j async driver.
All writes use MERGE for idempotent upserts. Datetimes are stored
as ISO 8601 strings for Python driver compatibility.

Source: ADR-0003, ADR-0005, ADR-0009
"""

from __future__ import annotations

import base64
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from neo4j import AsyncGraphDatabase

from context_graph.adapters.neo4j import queries
from context_graph.adapters.neo4j.retrieval import RetrievalDeps, RetrievalPipeline
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
from context_graph.domain.pagination import decode_cursor, encode_cursor
from context_graph.domain.scoring import score_node
from context_graph.metrics import GRAPH_QUERY_DURATION

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from context_graph.domain.models import (
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
    from context_graph.ports.embedding import EmbeddingService
    from context_graph.ports.event_store import EventStore
    from context_graph.ports.intent import IntentClassifier
    from context_graph.ports.llm import LLMClient
    from context_graph.settings import DecaySettings, Neo4jSettings, PPRSettings, QuerySettings

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
    EdgeType.CONTRADICTS: queries.MERGE_CONTRADICTS,
    EdgeType.SUPERSEDES: queries.MERGE_SUPERSEDES,
    EdgeType.PURSUES: queries.MERGE_PURSUES,
    EdgeType.CONTAINS: queries.MERGE_CONTAINS,
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

    def __init__(
        self,
        settings: Neo4jSettings,
        embedding_service: EmbeddingService | None = None,
        query_settings: QuerySettings | None = None,
        decay_settings: DecaySettings | None = None,
        intent_classifier: IntentClassifier | None = None,
        llm_client: LLMClient | None = None,
        event_store: EventStore | None = None,
        ppr_settings: PPRSettings | None = None,
    ) -> None:
        self._settings = settings
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            settings.uri,
            auth=(settings.username, settings.password.get_secret_value()),
            max_connection_pool_size=settings.max_connection_pool_size,
        )
        self._database = settings.database
        self._embedding_service = embedding_service
        self._llm_client = llm_client
        self._event_store = event_store
        self._query_timeout_s: float = (
            (query_settings.default_timeout_ms / 1000.0) if query_settings else 5.0
        )
        self._neighbor_limit: int = query_settings.default_neighbor_limit if query_settings else 50
        if decay_settings is None:
            from context_graph.settings import DecaySettings as _DecaySettings

            decay_settings = _DecaySettings()
        self._decay = decay_settings
        self._intent_classifier = intent_classifier
        self._ppr_settings = ppr_settings

        # Wire up the retrieval pipeline (separated for SRP)
        self._retrieval = RetrievalPipeline(
            RetrievalDeps(
                driver=self._driver,
                database=self._database,
                embedding_service=embedding_service,
                intent_classifier=intent_classifier,
                llm_client=llm_client,
                event_store=event_store,
                decay=self._decay,
                ppr_settings=ppr_settings,
                query_timeout_s=self._query_timeout_s,
                neighbor_limit=self._neighbor_limit,
                search_similar_entities=self.search_similar_entities,
            )
        )

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

    async def merge_event_nodes_batch(self, nodes: list[EventNode]) -> None:
        """MERGE a batch of event nodes in a single UNWIND transaction."""
        if not nodes:
            return
        events_params = [
            {
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
            for node in nodes
        ]
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(
                lambda tx: tx.run(queries.BATCH_MERGE_EVENT_NODES, {"events": events_params})
            )
        logger.debug("merged_event_nodes_batch", count=len(nodes))

    async def merge_entity_node(self, node: EntityNode) -> None:
        """MERGE an entity node into the graph. Idempotent."""
        params = {
            "entity_id": node.entity_id,
            "name": node.name,
            "entity_type": str(node.entity_type),
            "first_seen": node.first_seen.isoformat(),
            "last_seen": node.last_seen.isoformat(),
            "mention_count": node.mention_count,
            "embedding": node.embedding,
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

    async def merge_belief_node(self, node: BeliefNode) -> None:
        """MERGE a belief node into the graph. Idempotent."""
        params = {
            "belief_id": node.belief_id,
            "belief_text": node.belief_text,
            "confidence": node.confidence,
            "category": str(node.category),
            "created_at": node.created_at.isoformat(),
            "last_confirmed_at": node.last_confirmed_at.isoformat(),
            "confirmation_count": node.confirmation_count,
            "superseded_by": node.superseded_by,
        }
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(queries.MERGE_BELIEF_NODE, params))
        logger.debug("merged_belief_node", belief_id=node.belief_id)

    async def merge_goal_node(self, node: GoalNode) -> None:
        """MERGE a goal node into the graph. Idempotent."""
        params = {
            "goal_id": node.goal_id,
            "description": node.description,
            "status": str(node.status),
            "created_at": node.created_at.isoformat(),
            "last_active_at": node.last_active_at.isoformat(),
            "priority": node.priority,
            "evidence_count": node.evidence_count,
        }
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(queries.MERGE_GOAL_NODE, params))
        logger.debug("merged_goal_node", goal_id=node.goal_id)

    async def merge_episode_node(self, node: EpisodeNode) -> None:
        """MERGE an episode node into the graph. Idempotent."""
        params = {
            "episode_id": node.episode_id,
            "session_id": node.session_id,
            "start_time": node.start_time.isoformat(),
            "end_time": node.end_time.isoformat(),
            "event_count": node.event_count,
            "episode_type": str(node.episode_type),
            "summary_id": node.summary_id,
        }
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(queries.MERGE_EPISODE_NODE, params))
        logger.debug("merged_episode_node", episode_id=node.episode_id)

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

    async def search_similar_entities(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.75,
    ) -> list[dict[str, Any]]:
        """Search for similar entities using the Neo4j vector index.

        Returns a list of dicts with entity_id, name, entity_type, score.
        Score is cosine similarity in [0, 1].
        """
        params = {
            "query_embedding": query_embedding,
            "top_k": top_k,
            "threshold": threshold,
        }
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                queries.SEARCH_SIMILAR_ENTITIES, params, timeout=self._query_timeout_s
            )
            records = [record async for record in result]
        return [
            {
                "entity_id": r["entity_id"],
                "name": r["name"],
                "entity_type": r["entity_type"],
                "score": r["score"],
            }
            for r in records
        ]

    async def ensure_constraints(self) -> None:
        """Create uniqueness constraints and performance indexes if they do not exist."""
        async with self._driver.session(database=self._database) as session:
            for constraint_query in queries.ALL_CONSTRAINTS:
                await session.run(constraint_query)
            for index_query in queries.ALL_INDEXES:
                await session.run(index_query)
        await self.ensure_vector_indexes()
        logger.info(
            "ensured_constraints",
            count=len(queries.ALL_CONSTRAINTS) + len(queries.ALL_INDEXES),
        )

    async def ensure_vector_indexes(self) -> None:
        """Create vector indexes for embedding search if they do not exist."""
        async with self._driver.session(database=self._database) as session:
            for vindex_query in queries.ALL_VECTOR_INDEXES:
                await session.run(vindex_query)
        logger.info("ensured_vector_indexes", count=len(queries.ALL_VECTOR_INDEXES))

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

    @staticmethod
    def _label_to_node_type(labels: list[str]) -> str:
        """Map Neo4j labels to a node type string."""
        known = {
            "Event",
            "Entity",
            "Summary",
            "UserProfile",
            "Preference",
            "Skill",
            "Workflow",
            "BehavioralPattern",
            "Belief",
            "Goal",
            "Episode",
        }
        for label in labels:
            if label in known:
                return label
        return labels[0] if labels else "Unknown"

    async def _embed_query(self, query_text: str | None) -> list[float] | None:
        """Embed query text if embedding service is available."""
        if self._embedding_service is None or not query_text:
            return None
        try:
            return await self._embedding_service.embed_text(query_text)
        except Exception:
            logger.warning("query_embedding_failed", query=query_text[:50])
            return None

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
        max_depth: int = 3,
        cursor: str | None = None,
    ) -> AtlasResponse:
        """Assemble working memory context for a session."""
        start_ms = time.monotonic_ns()

        # Embed query text for relevance scoring
        query_embedding = await self._embed_query(query)

        # Decode cursor for keyset pagination
        cursor_ts: str | None = None
        cursor_id: str | None = None
        if cursor:
            cursor_ts, cursor_id = decode_cursor(cursor)

        # Build Cypher with optional cursor WHERE clause
        fetch_limit = max_nodes + 1  # fetch one extra to detect has_more
        if cursor_ts:
            cypher = (
                "MATCH (e:Event {session_id: $session_id}) "
                "WHERE e.occurred_at > $cursor_ts "
                "   OR (e.occurred_at = $cursor_ts AND e.event_id > $cursor_id) "
                "RETURN e ORDER BY e.occurred_at ASC LIMIT $limit"
            )
            params: dict[str, Any] = {
                "session_id": session_id,
                "cursor_ts": cursor_ts,
                "cursor_id": cursor_id,
                "limit": fetch_limit,
            }
        else:
            cypher = queries.GET_SESSION_EVENTS
            params = {"session_id": session_id, "limit": fetch_limit}

        async with self._driver.session(database=self._database) as session:
            result = await session.run(cypher, params, timeout=self._query_timeout_s)
            records = [record async for record in result]

        has_more = len(records) > max_nodes
        if has_more:
            records = records[:max_nodes]

        nodes: dict[str, AtlasNode] = {}
        scored_entries: list[tuple[str, dict[str, Any], NodeScores]] = []

        for record in records:
            props = dict(record["e"])
            event_id = props.get("event_id", "")
            scores = score_node(
                props,
                query_embedding=query_embedding,
                s_base=self._decay.s_base,
                s_boost=self._decay.s_boost,
                w_recency=self._decay.weight_recency,
                w_importance=self._decay.weight_importance,
                w_relevance=self._decay.weight_relevance,
                w_user_affinity=self._decay.weight_user_affinity,
            )
            scored_entries.append((event_id, props, scores))

        # Sort by composite decay_score descending, take top max_nodes
        scored_entries.sort(key=lambda x: x[2].decay_score, reverse=True)
        scored_entries = scored_entries[:max_nodes]

        for event_id, props, scores in scored_entries:
            nodes[event_id] = self._build_atlas_node(props, scores)

        # Bump access counts
        event_ids = [eid for eid, _, _ in scored_entries]
        await self._bump_access_counts(event_ids)

        # Fetch edges between session events
        edges: list[AtlasEdge] = []
        if event_ids:
            async with self._driver.session(database=self._database) as session:
                edge_result = await session.run(
                    queries.GET_SESSION_EDGES,
                    {"session_id": session_id, "event_ids": event_ids},
                    timeout=self._query_timeout_s,
                )
                edge_records = [record async for record in edge_result]
            for erec in edge_records:
                edges.append(
                    AtlasEdge(
                        source=erec["source"],
                        target=erec["target"],
                        edge_type=erec["edge_type"],
                        properties=dict(erec["props"]) if erec["props"] else {},
                    )
                )

        # Fetch non-Event neighbor nodes (Entity, Preference, Skill, etc.)
        if event_ids:
            async with self._driver.session(database=self._database) as session:
                nbr_result = await session.run(
                    queries.GET_SESSION_NEIGHBORS,
                    {"session_id": session_id, "event_ids": event_ids},
                    timeout=self._query_timeout_s,
                )
                nbr_records = [record async for record in nbr_result]

            neighbor_ids: list[str] = []
            for nrec in nbr_records:
                nbr_id = nrec["neighbor_id"]
                if not nbr_id or nbr_id in nodes:
                    continue
                labels = list(nrec["neighbor_labels"])
                nbr_props = dict(nrec["neighbor_props"])
                node_type = self._label_to_node_type(labels)
                nodes[nbr_id] = AtlasNode(
                    node_id=nbr_id,
                    node_type=node_type,
                    attributes=nbr_props,
                    provenance=Provenance(
                        event_id=nbr_id,
                        global_position="",
                        source="neo4j",
                        occurred_at=datetime.now(UTC),
                        session_id=session_id,
                        agent_id="",
                        trace_id="",
                    ),
                    scores=NodeScores(
                        decay_score=1.0,
                        relevance_score=0.0,
                        importance_score=nbr_props.get("importance_score", 5),
                    ),
                    retrieval_reason="neighbor",
                )
                neighbor_ids.append(nbr_id)

                # Add the cross-type edge (Event → neighbor)
                edges.append(
                    AtlasEdge(
                        source=nrec["source_event_id"],
                        target=nbr_id,
                        edge_type=nrec["edge_type"],
                        properties=dict(nrec["edge_props"]) if nrec["edge_props"] else {},
                    )
                )

            # Fetch edges between neighbor nodes (SAME_AS, HAS_PREFERENCE, etc.)
            if neighbor_ids:
                async with self._driver.session(database=self._database) as session:
                    inter_result = await session.run(
                        queries.GET_NEIGHBOR_INTER_EDGES,
                        {"neighbor_ids": neighbor_ids},
                        timeout=self._query_timeout_s,
                    )
                    inter_records = [record async for record in inter_result]
                for irec in inter_records:
                    edges.append(
                        AtlasEdge(
                            source=irec["source"],
                            target=irec["target"],
                            edge_type=irec["edge_type"],
                            properties=dict(irec["props"]) if irec["props"] else {},
                        )
                    )

        # Build pagination cursor from last record
        next_cursor: str | None = None
        if has_more and records:
            last_props = dict(records[-1]["e"])
            last_ts = last_props.get("occurred_at", "")
            last_eid = last_props.get("event_id", "")
            if last_ts and last_eid:
                next_cursor = encode_cursor(str(last_ts), str(last_eid))

        elapsed_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)
        GRAPH_QUERY_DURATION.labels(query_type="context").observe(elapsed_ms / 1000.0)

        meta = QueryMeta(
            query_ms=elapsed_ms,
            nodes_returned=len(nodes),
            truncated=has_more,
            capacity=QueryCapacity(
                max_nodes=max_nodes,
                used_nodes=len(nodes),
                max_depth=max_depth,
            ),
        )

        return AtlasResponse(
            nodes=nodes,
            edges=edges,
            pagination=Pagination(cursor=next_cursor, has_more=has_more),
            meta=meta,
        )

    async def get_lineage(
        self, query: LineageQuery, query_text: str | None = None
    ) -> AtlasResponse:
        """Traverse lineage (CAUSED_BY chains) from a node."""
        start_ms = time.monotonic_ns()

        # Embed query text for relevance scoring
        query_embedding = await self._embed_query(query_text)

        clamped_depth, clamped_nodes, _timeout = validate_traversal_bounds(
            max_depth=query.max_depth,
            max_nodes=query.max_nodes,
            timeout_ms=5000,
        )

        # Decode cursor as offset for lineage pagination
        offset = 0
        if query.cursor:
            try:
                offset = int(base64.urlsafe_b64decode(query.cursor.encode()).decode())
            except (ValueError, Exception):
                offset = 0

        fetch_limit = clamped_nodes + 1

        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                queries.GET_LINEAGE,
                {
                    "node_id": query.node_id,
                    "max_depth": clamped_depth,
                    "max_nodes": fetch_limit,
                },
                timeout=self._query_timeout_s,
            )
            records = [record async for record in result]

        # Apply offset for pagination
        if offset > 0:
            records = records[offset:]

        has_more = len(records) > clamped_nodes
        if has_more:
            records = records[:clamped_nodes]

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
                    scores = score_node(
                        props,
                        query_embedding=query_embedding,
                        s_base=self._decay.s_base,
                        s_boost=self._decay.s_boost,
                        w_recency=self._decay.weight_recency,
                        w_importance=self._decay.weight_importance,
                        w_relevance=self._decay.weight_relevance,
                        w_user_affinity=self._decay.weight_user_affinity,
                    )
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

        # Build next cursor (offset-based)
        next_cursor: str | None = None
        if has_more:
            next_offset = offset + clamped_nodes
            next_cursor = base64.urlsafe_b64encode(str(next_offset).encode()).decode()

        elapsed_ms = int((time.monotonic_ns() - start_ms) / 1_000_000)
        GRAPH_QUERY_DURATION.labels(query_type="lineage").observe(elapsed_ms / 1000.0)

        meta = QueryMeta(
            query_ms=elapsed_ms,
            nodes_returned=len(nodes),
            truncated=has_more,
            capacity=QueryCapacity(
                max_nodes=clamped_nodes,
                used_nodes=len(nodes),
                max_depth=clamped_depth,
            ),
        )

        return AtlasResponse(
            nodes=nodes,
            edges=edges,
            pagination=Pagination(cursor=next_cursor, has_more=has_more),
            meta=meta,
        )

    async def get_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        """Delegate to the retrieval pipeline for subgraph queries."""
        return await self._retrieval.get_subgraph(query)

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity and its connected events."""
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                queries.GET_ENTITY_WITH_EVENTS,
                {"entity_id": entity_id, "limit": 100},
                timeout=self._query_timeout_s,
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
    # Entity cluster consolidation (transitive closure)
    # ------------------------------------------------------------------

    async def consolidate_entity_cluster(self, cluster_ids: list[str], canonical_id: str) -> None:
        """Ensure all entities in a cluster have SAME_AS edges to the canonical.

        Uses MERGE for idempotent edge creation. Members that are already
        linked via SAME_AS are unaffected (MERGE is a no-op).
        """
        if not cluster_ids or not canonical_id:
            return

        # Filter out the canonical itself; self-edges are not needed
        member_ids = [mid for mid in cluster_ids if mid != canonical_id]
        if not member_ids:
            return

        now_iso = datetime.now(UTC).isoformat()
        params: dict[str, Any] = {
            "member_ids": member_ids,
            "canonical_id": canonical_id,
            "resolved_at": now_iso,
        }

        async with self._driver.session(database=self._database) as session:

            async def _write(tx: Any) -> None:
                await tx.run(queries.CONSOLIDATE_ENTITY_CLUSTER, params)

            await session.execute_write(_write)

        logger.debug(
            "consolidated_entity_cluster",
            canonical_id=canonical_id,
            member_count=len(member_ids),
        )

    async def get_entity_with_cluster(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity, its SAME_AS cluster, and connected events."""
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                queries.GET_ENTITY_WITH_CLUSTER,
                {"entity_id": entity_id, "limit": 100},
                timeout=self._query_timeout_s,
            )
            records = [record async for record in result]

        if not records:
            return None

        entities: dict[str, dict[str, Any]] = {}
        connected_events: list[dict[str, Any]] = []

        for record in records:
            ent = record.get("ent")
            if ent is not None:
                ent_dict = dict(ent)
                eid = ent_dict.get("entity_id", "")
                if eid and eid not in entities:
                    entities[eid] = ent_dict

            evt = record.get("evt")
            if evt is not None:
                evt_dict = dict(evt)
                ref_props = record.get("ref_props", {}) or {}
                evt_dict["ref_props"] = ref_props
                connected_events.append(evt_dict)

        return {
            "entities": entities,
            "connected_events": connected_events,
        }

    # ------------------------------------------------------------------
    # HealthCheckable protocol
    # ------------------------------------------------------------------

    async def health_ping(self) -> bool:
        """Return True if Neo4j is reachable."""
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # GraphMaintenance protocol — delegates to maintenance module
    # ------------------------------------------------------------------

    async def get_session_event_counts(self) -> dict[str, int]:
        """Count events per session in the graph."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.get_session_event_counts(self._driver, self._database)

    async def get_graph_stats(self) -> dict[str, Any]:
        """Get node and edge counts by type."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.get_graph_stats(self._driver, self._database)

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
        """Write a summary node and SUMMARIZES edges."""
        from context_graph.adapters.neo4j import maintenance

        await maintenance.write_summary_with_edges(
            driver=self._driver,
            database=self._database,
            summary_id=summary_id,
            scope=scope,
            scope_id=scope_id,
            content=content,
            created_at=created_at,
            event_count=event_count,
            time_range=time_range,
            event_ids=event_ids,
        )

    async def delete_edges_by_type_and_age(
        self,
        min_score: float,
        max_age_hours: int,
    ) -> int:
        """Delete SIMILAR_TO edges below a score threshold."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.delete_edges_by_type_and_age(
            self._driver, self._database, min_score, max_age_hours
        )

    async def delete_cold_events(
        self,
        max_age_hours: int,
        min_importance: int,
        min_access_count: int,
    ) -> int:
        """Delete cold-tier event nodes."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.delete_cold_events(
            self._driver, self._database, max_age_hours, min_importance, min_access_count
        )

    async def delete_archive_events(self, event_ids: list[str]) -> int:
        """Delete archived event nodes by their IDs."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.delete_archive_events(self._driver, self._database, event_ids)

    async def get_archive_event_ids(self, max_age_hours: int) -> list[str]:
        """Get event IDs older than the specified age."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.get_archive_event_ids(self._driver, self._database, max_age_hours)

    async def delete_orphan_nodes(self, batch_size: int = 500) -> tuple[dict[str, int], list[str]]:
        """Delete orphaned nodes."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.delete_orphan_nodes(self._driver, self._database, batch_size)

    async def update_importance_from_centrality(self) -> int:
        """Recompute importance scores from in-degree centrality."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.update_importance_from_centrality(self._driver, self._database)

    async def run_session_query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Run an arbitrary read query and return records as dicts."""
        async with self._driver.session(database=self._database) as session:
            result = await session.run(cypher, params)
            records = [record async for record in result]
        return [dict(r) for r in records]

    # ------------------------------------------------------------------
    # GraphStore protocol extensions (hexagonal boundary compliance)
    # ------------------------------------------------------------------

    async def update_event_enrichment(
        self, event_id: str, keywords: list[str], importance_score: int
    ) -> None:
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(
                lambda tx: tx.run(
                    queries.UPDATE_EVENT_ENRICHMENT,
                    {
                        "event_id": event_id,
                        "keywords": keywords,
                        "importance_score": importance_score,
                    },
                )
            )

    async def store_event_embedding(self, event_id: str, embedding: list[float]) -> None:
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(
                lambda tx: tx.run(
                    queries.UPDATE_EVENT_EMBEDDING,
                    {
                        "event_id": event_id,
                        "embedding": embedding,
                    },
                )
            )

    async def adjust_node_importance(
        self,
        node_id: str,
        delta: int,
        min_value: int = 1,
        max_value: int = 10,
    ) -> bool:
        """Adjust importance_score on an Event node, clamped to [min_value, max_value]."""
        query = (
            "MATCH (e:Event {event_id: $node_id}) "
            "SET e.importance_score = "
            "CASE "
            "  WHEN e.importance_score IS NULL THEN $clamped_delta "
            "  ELSE toInteger(CASE "
            "    WHEN e.importance_score + $delta < $min_val THEN $min_val "
            "    WHEN e.importance_score + $delta > $max_val THEN $max_val "
            "    ELSE e.importance_score + $delta END) "
            "END "
            "RETURN e.event_id AS eid"
        )
        clamped_delta = max(min_value, min(max_value, max(min_value, 5 + delta)))

        async def _work(tx: Any) -> list[Any]:
            result = await tx.run(
                query,
                {
                    "node_id": node_id,
                    "delta": delta,
                    "min_val": min_value,
                    "max_val": max_value,
                    "clamped_delta": clamped_delta,
                },
            )
            return [record async for record in result]

        async with self._driver.session(database=self._database) as session:
            records = await session.execute_write(_work)
            return len(records) > 0

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
        params = {
            "entity_id": entity_id,
            "name": name,
            "entity_type": entity_type,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "mention_count": mention_count,
            "embedding": embedding or [],
        }
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(queries.MERGE_ENTITY_NODE, params))

    async def merge_typed_edge(
        self, source_id: str, target_id: str, edge_type: str, props: dict[str, Any] | None = None
    ) -> None:
        query = _EDGE_QUERIES.get(edge_type)
        if query is None:
            msg = f"Unknown edge type: {edge_type}"
            raise ValueError(msg)
        params = {"source_id": source_id, "target_id": target_id, "props": props or {}}
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(lambda tx: tx.run(query, params))

    async def get_entities(self, limit: int = 1000) -> list[dict[str, Any]]:
        query = (
            "MATCH (n:Entity) "
            "RETURN n.entity_id AS entity_id, n.name AS name, "
            "n.entity_type AS entity_type LIMIT $limit"
        )
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, {"limit": limit})
            records = [record async for record in result]
        return [
            {"entity_id": r["entity_id"], "name": r["name"], "entity_type": r["entity_type"]}
            for r in records
        ]

    # ------------------------------------------------------------------
    # UserStore protocol — delegates to user_queries module
    # ------------------------------------------------------------------

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """Fetch a user's profile node."""
        from context_graph.adapters.neo4j import user_queries

        return await user_queries.get_user_profile(self._driver, self._database, user_id)

    async def get_user_preferences(
        self, user_id: str, active_only: bool = True
    ) -> list[dict[str, Any]]:
        """Fetch a user's preferences."""
        from context_graph.adapters.neo4j import user_queries

        return await user_queries.get_user_preferences(
            self._driver, self._database, user_id, active_only=active_only
        )

    async def get_user_skills(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch a user's skills."""
        from context_graph.adapters.neo4j import user_queries

        return await user_queries.get_user_skills(self._driver, self._database, user_id)

    async def get_user_patterns(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch a user's behavioral patterns."""
        from context_graph.adapters.neo4j import user_queries

        return await user_queries.get_user_patterns(self._driver, self._database, user_id)

    async def get_user_interests(self, user_id: str) -> list[dict[str, Any]]:
        """Fetch a user's interests."""
        from context_graph.adapters.neo4j import user_queries

        return await user_queries.get_user_interests(self._driver, self._database, user_id)

    async def delete_user_data(self, user_id: str) -> int:
        """GDPR cascade delete."""
        from context_graph.adapters.neo4j import user_queries

        return await user_queries.delete_user_data(self._driver, self._database, user_id)

    async def export_user_data(self, user_id: str) -> dict[str, Any]:
        """GDPR export."""
        from context_graph.adapters.neo4j import user_queries

        return await user_queries.export_user_data(self._driver, self._database, user_id)

    async def write_user_profile(self, profile_data: dict[str, Any]) -> None:
        """Create or update a user profile."""
        from context_graph.adapters.neo4j import user_queries

        await user_queries.write_user_profile(self._driver, self._database, profile_data)

    async def write_preference_with_edges(
        self,
        user_entity_id: str,
        preference_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        """Write a Preference node with edges."""
        from context_graph.adapters.neo4j import user_queries

        await user_queries.write_preference_with_edges(
            self._driver,
            self._database,
            user_entity_id,
            preference_data,
            source_event_ids,
            derivation_info,
        )

    async def write_skill_with_edges(
        self,
        user_entity_id: str,
        skill_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        """Write a Skill node with edges."""
        from context_graph.adapters.neo4j import user_queries

        await user_queries.write_skill_with_edges(
            self._driver,
            self._database,
            user_entity_id,
            skill_data,
            source_event_ids,
            derivation_info,
        )

    async def write_interest_edge(
        self,
        user_entity_id: str,
        entity_name: str,
        entity_type: str,
        weight: float,
        source: str,
    ) -> None:
        """Create an INTERESTED_IN edge."""
        from context_graph.adapters.neo4j import user_queries

        await user_queries.write_interest_edge(
            self._driver,
            self._database,
            user_entity_id,
            entity_name,
            entity_type,
            weight,
            source,
        )

    async def write_derived_from_edge(
        self,
        source_node_id: str,
        source_id_field: str,
        event_id: str,
        method: str,
        session_id: str,
    ) -> None:
        """Write a single DERIVED_FROM edge."""
        from context_graph.adapters.neo4j import user_queries

        await user_queries.write_derived_from_edge(
            self._driver,
            self._database,
            source_node_id,
            source_id_field,
            event_id,
            method,
            session_id,
        )

    async def set_preference_superseded(
        self,
        preference_id: str,
        superseded_by: str,
    ) -> None:
        """Mark a preference as superseded by another preference."""
        from context_graph.adapters.neo4j import user_queries

        await user_queries.set_preference_superseded(
            self._driver, self._database, preference_id, superseded_by
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Release connections."""
        await self._driver.close()
        logger.info("neo4j_driver_closed")
