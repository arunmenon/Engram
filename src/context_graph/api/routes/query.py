"""Subgraph query endpoint.

POST /v1/query/subgraph — execute intent-aware subgraph query.

Source: ADR-0006, ADR-0009
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from context_graph.api.dependencies import get_retrieval
from context_graph.domain.models import (  # noqa: TCH001 — runtime: type annotation + response_model
    AtlasResponse,
    SubgraphQuery,
)
from context_graph.ports.retrieval import Retrieval  # noqa: TCH001 — runtime: Depends()

router = APIRouter(tags=["query"])

RetrievalDep = Annotated[Retrieval, Depends(get_retrieval)]


@router.post("/query/subgraph", response_model=AtlasResponse)
async def query_subgraph(
    query: SubgraphQuery,
    retrieval: RetrievalDep,
) -> AtlasResponse:
    """Execute intent-aware subgraph query.

    The system infers intent from query text. Optionally accepts
    explicit intent override and seed nodes.
    """
    return await retrieval.get_subgraph(query)
