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

    async def merge_event_node(self, node: EventNode, tenant_id: str = "default") -> None:
        """MERGE an event node into the graph. Idempotent."""
        ...

    async def merge_event_nodes_batch(
        self, nodes: list[EventNode], tenant_id: str = "default"
    ) -> None:
        """MERGE a batch of event nodes into the graph in a single transaction."""
        ...

    async def merge_entity_node(self, node: EntityNode, tenant_id: str = "default") -> None:
        """MERGE an entity node into the graph. Idempotent."""
        ...

    async def merge_summary_node(self, node: SummaryNode, tenant_id: str = "default") -> None:
        """MERGE a summary node into the graph. Idempotent."""
        ...

    async def create_edge(self, edge: Edge, tenant_id: str = "default") -> None:
        """Create or update an edge between two nodes."""
        ...

    async def create_edges_batch(self, edges: list[Edge], tenant_id: str = "default") -> None:
        """Create or update edges in batch."""
        ...

    async def get_subgraph(self, query: SubgraphQuery, tenant_id: str = "default") -> AtlasResponse:
        """Execute an intent-aware subgraph query.

        The system infers intent and seed nodes from the query text
        when they are not explicitly provided.
        """
        ...

    async def get_lineage(
        self, query: LineageQuery, query_text: str | None = None, tenant_id: str = "default"
    ) -> AtlasResponse:
        """Traverse lineage (CAUSED_BY chains) from a node."""
        ...

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
        max_depth: int = 3,
        cursor: str | None = None,
        tenant_id: str = "default",
    ) -> AtlasResponse:
        """Assemble working memory context for a session.

        Returns events ranked by decay score.
        """
        ...

    async def get_entity(self, entity_id: str, tenant_id: str = "default") -> dict[str, Any] | None:
        """Retrieve an entity and its connected events."""
        ...

    async def update_event_enrichment(
        self, event_id: str, keywords: list[str], importance_score: int, tenant_id: str = "default"
    ) -> None:
        """Update keywords and importance on an Event node."""
        ...

    async def store_event_embedding(
        self, event_id: str, embedding: list[float], tenant_id: str = "default"
    ) -> None:
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
        tenant_id: str = "default",
    ) -> None:
        """MERGE an Entity node from raw parameters (no domain model)."""
        ...

    async def merge_typed_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        props: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> None:
        """MERGE a typed edge between two nodes."""
        ...

    async def get_entities(
        self, limit: int = 1000, tenant_id: str = "default"
    ) -> list[dict[str, Any]]:
        """Fetch Entity nodes for deduplication."""
        ...

    async def search_similar_entities(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        threshold: float = 0.75,
        tenant_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Search for similar entities using vector index."""
        ...

    async def consolidate_entity_cluster(
        self, cluster_ids: list[str], canonical_id: str, tenant_id: str = "default"
    ) -> None:
        """Ensure all entities in a cluster have SAME_AS edges to the canonical."""
        ...

    async def adjust_node_importance(
        self,
        node_id: str,
        delta: int,
        min_value: int = 1,
        max_value: int = 10,
        tenant_id: str = "default",
    ) -> bool:
        """Adjust importance_score on an Event node by *delta*, clamped to [min_value, max_value].

        Returns True if the node was found and updated, False otherwise.
        """
        ...

    async def ensure_constraints(self, tenant_id: str = "default") -> None:
        """Create uniqueness constraints and indexes if they do not exist."""
        ...

    async def close(self) -> None:
        """Release connections."""
        ...
