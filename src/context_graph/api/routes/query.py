"""Subgraph query endpoint.

POST /v1/query/subgraph — execute intent-aware subgraph query.

Source: ADR-0006, ADR-0009
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from context_graph.adapters.neo4j.store import Neo4jGraphStore  # noqa: TCH001 — runtime: Depends()
from context_graph.api.dependencies import get_graph_store
from context_graph.domain.models import (  # noqa: TCH001 — runtime: type annotation + response_model
    AtlasResponse,
    SubgraphQuery,
)

router = APIRouter(tags=["query"])

GraphStoreDep = Annotated[Neo4jGraphStore, Depends(get_graph_store)]


@router.post("/query/subgraph", response_model=AtlasResponse)
async def query_subgraph(
    query: SubgraphQuery,
    graph_store: GraphStoreDep,
) -> AtlasResponse:
    """Execute intent-aware subgraph query.

    The system infers intent from query text. Optionally accepts
    explicit intent override and seed nodes.
    """
    return await graph_store.get_subgraph(query)
