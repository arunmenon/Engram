"""Neo4j GraphStore adapter.

Implements the GraphStore protocol using the neo4j async driver.
All writes use MERGE for idempotent upserts. Datetimes are stored
as ISO 8601 strings for Python driver compatibility.

Source: ADR-0003, ADR-0005, ADR-0009
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from neo4j import AsyncGraphDatabase

from context_graph.adapters.neo4j import queries
from context_graph.domain.models import EdgeType

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from context_graph.domain.models import (
        AtlasResponse,
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
    # Phase 3+ stubs
    # ------------------------------------------------------------------

    async def get_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        """Execute an intent-aware subgraph query."""
        raise NotImplementedError("Implemented in Phase 3")

    async def get_lineage(self, query: LineageQuery) -> AtlasResponse:
        """Traverse lineage (CAUSED_BY chains) from a node."""
        raise NotImplementedError("Implemented in Phase 3")

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
    ) -> AtlasResponse:
        """Assemble working memory context for a session."""
        raise NotImplementedError("Implemented in Phase 3")

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity and its connected events."""
        raise NotImplementedError("Implemented in Phase 3")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Release connections."""
        await self._driver.close()
        logger.info("neo4j_driver_closed")
