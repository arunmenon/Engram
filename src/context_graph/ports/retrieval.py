"""Retrieval port: what the API asks for context (ADR-0019 C3).

Implemented by ``context_graph.retrieval.engine.RetrievalEngine``, which
composes the storage ports. Signatures match the frozen ``GraphStore``
query methods so responses are unchanged.

Source: ADR-0006, ADR-0019
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from context_graph.domain.models import AtlasResponse, LineageQuery, SubgraphQuery


class Retrieval(Protocol):
    """Context, lineage and subgraph retrieval returning Atlas responses."""

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
        max_depth: int = 3,
        cursor: str | None = None,
    ) -> AtlasResponse:
        """Assemble working-memory context for a session."""
        ...

    async def get_lineage(
        self, query: LineageQuery, query_text: str | None = None
    ) -> AtlasResponse:
        """Traverse CAUSED_BY lineage from a node."""
        ...

    async def get_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        """Run an intent-aware hybrid subgraph query."""
        ...
