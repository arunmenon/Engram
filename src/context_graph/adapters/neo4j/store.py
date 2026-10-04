"""Neo4j GraphStore adapter.

Implements the GraphStore protocol using the neo4j async driver.
All writes use MERGE for idempotent upserts. Datetimes are stored
as ISO 8601 strings for Python driver compatibility.

Source: ADR-0003, ADR-0005, ADR-0009
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog
from neo4j import AsyncGraphDatabase

from context_graph.adapters.errors import translate_errors
from context_graph.adapters.neo4j import queries
from context_graph.adapters.neo4j.errors import translate_neo4j_error
from context_graph.adapters.neo4j.graph_reads import Neo4jGraphReads
from context_graph.adapters.neo4j.retrieval import RetrievalDeps, RetrievalPipeline
from context_graph.domain.models import (
    AtlasResponse,
    EdgeType,
)
from context_graph.ports.errors import InvalidRequestError

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


@translate_errors(translate_neo4j_error)
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

        self._reads = Neo4jGraphReads(self._driver, self._database)

        # Retrieval pipeline behind the deprecated get_context/get_lineage/
        # get_subgraph methods (ADR-0019 C3: new code uses RetrievalEngine)
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

    @property
    def reads(self) -> Neo4jGraphReads:
        """Bounded graph reads for the retrieval engine (ADR-0019 GraphReads port)."""
        return self._reads

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
    #
    # Deprecated (ADR-0019 C3): retrieval lives in
    # context_graph.retrieval.RetrievalEngine, which the API builds from
    # the storage ports. These methods stay because the GraphStore port is
    # frozen; they delegate to the same engine, wired with the optional
    # constructor dependencies.
    # ------------------------------------------------------------------

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
        max_depth: int = 3,
        cursor: str | None = None,
    ) -> AtlasResponse:
        """Assemble working memory context for a session."""
        return await self._retrieval.get_context(session_id, max_nodes, query, max_depth, cursor)

    async def get_lineage(
        self, query: LineageQuery, query_text: str | None = None
    ) -> AtlasResponse:
        """Traverse lineage (CAUSED_BY chains) from a node."""
        return await self._retrieval.get_lineage(query, query_text)

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

    # -- Named operations (ADR-0019 C6) ----------------------------------

    async def session_agent_id(self, session_id: str) -> str | None:
        """Return the agent id recorded on a session's events, or None."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.session_agent_id(self._driver, self._database, session_id)

    async def session_events(self, session_id: str, limit: int) -> list[dict[str, Any]]:
        """Return a session's event properties ordered by occurred_at."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.session_events(self._driver, self._database, session_id, limit)

    async def session_event_timeline(self, session_id: str) -> list[dict[str, Any]]:
        """Return id, type, time, tool and status for a session's events, in time order."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.session_event_timeline(self._driver, self._database, session_id)

    async def events_for_pruning(self, limit: int) -> list[dict[str, Any]]:
        """Return the oldest events with the fields retention pruning decides on."""
        from context_graph.adapters.neo4j import maintenance

        return await maintenance.events_for_pruning(self._driver, self._database, limit)

    async def delete_all(self, *, confirm: bool = False) -> None:
        """Delete the whole graph. Admin-only; refuses unless ``confirm`` is True."""
        from context_graph.adapters.neo4j import maintenance

        if not confirm:
            msg = "delete_all requires confirm=True"
            raise InvalidRequestError(msg)
        await maintenance.delete_all(self._driver, self._database)

    async def run_session_query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Run an arbitrary read query and return records as dicts.

        Deprecated (ADR-0019): use the named operations above. Kept because
        the GraphMaintenance port is frozen; no caller outside adapters/ uses it.
        """
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
