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
        max_depth: int = 3,
        cursor: str | None = None,
    ) -> AtlasResponse:
        """Assemble working memory context for a session.

        Returns events ranked by decay score.
        """
        ...

    async def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        """Retrieve an entity and its connected events."""
        ...

    async def update_event_enrichment(
        self, event_id: str, keywords: list[str], importance_score: int
    ) -> None:
        """Update keywords and importance on an Event node."""
        ...

    async def store_event_embedding(self, event_id: str, embedding: list[float]) -> None:
        """Store embedding vector on an Event node."""
        ...

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
        """MERGE an Entity node from raw parameters (no domain model)."""
        ...

    async def merge_typed_edge(
        self, source_id: str, target_id: str, edge_type: str, props: dict[str, Any] | None = None
    ) -> None:
        """MERGE a typed edge between two nodes."""
        ...

    async def get_entities(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Fetch Entity nodes for deduplication."""
        ...

    async def search_similar_entities(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.75,
    ) -> list[dict[str, Any]]:
        """Search for similar entities using vector index."""
        ...

    async def consolidate_entity_cluster(
        self, cluster_ids: list[str], canonical_id: str
    ) -> None:
        """Ensure all entities in a cluster have SAME_AS edges to the canonical."""
        ...

    async def ensure_constraints(self) -> None:
        """Create uniqueness constraints and indexes if they do not exist."""
        ...

    async def close(self) -> None:
        """Release connections."""
        ...
