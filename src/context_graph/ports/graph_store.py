"""Graph store port interface.

Uses typing.Protocol for structural subtyping (not ABCs).
The Neo4j adapter implements this protocol.

Source: ADR-0009, ADR-0005
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from context_graph.domain.models import (
        AtlasResponse,
        Edge,
        EntityNode,
        EventNode,
        LineageQuery,
        SubgraphQuery,
        SummaryNode,
    )


class GraphStore(Protocol):
    """Protocol for the graph store (Neo4j implementation)."""

    async def merge_event_node(self, node: EventNode) -> None:
        """MERGE an event node into the graph. Idempotent."""
        ...

    async def merge_entity_node(self, node: EntityNode) -> None:
        """MERGE an entity node into the graph. Idempotent."""
        ...

    async def merge_summary_node(self, node: SummaryNode) -> None:
        """MERGE a summary node into the graph. Idempotent."""
        ...

    async def create_edge(self, edge: Edge) -> None:
        """Create or update an edge between two nodes."""
        ...

    async def create_edges_batch(self, edges: list[Edge]) -> None:
        """Create or update edges in batch."""
        ...

    async def get_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        """Execute an intent-aware subgraph query.

        The system infers intent and seed nodes from the query text
        when they are not explicitly provided.
        """
        ...

    async def get_lineage(self, query: LineageQuery) -> AtlasResponse:
        """Traverse lineage (CAUSED_BY chains) from a node."""
        ...

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
    ) -> AtlasResponse:
        """Assemble working memory context for a session.

        Returns events ranked by decay score.
        """
        ...

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity and its connected events."""
        ...

    async def close(self) -> None:
        """Release connections."""
        ...
