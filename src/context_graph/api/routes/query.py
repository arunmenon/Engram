"""Subgraph query endpoint.

POST /v1/query/subgraph — execute intent-aware subgraph query.

Source: ADR-0006, ADR-0009
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from context_graph.api.dependencies import TenantContext, get_graph_store, require_tenant
from context_graph.domain.models import (  # noqa: TCH001 — runtime: type annotation + response_model
    AtlasResponse,
    SubgraphQuery,
)
from context_graph.ports.graph_store import GraphStore  # noqa: TCH001 — runtime: Depends()

router = APIRouter(tags=["query"])

GraphStoreDep = Annotated[GraphStore, Depends(get_graph_store)]
TenantDep = Annotated[TenantContext, Depends(require_tenant)]


@router.post("/query/subgraph", response_model=AtlasResponse)
async def query_subgraph(
    query: SubgraphQuery,
    graph_store: GraphStoreDep,
    tenant: TenantDep,
) -> AtlasResponse:
    """Execute intent-aware subgraph query.

    The system infers intent from query text. Optionally accepts
    explicit intent override and seed nodes.
    """
    return await graph_store.get_subgraph(query, tenant_id=tenant.tenant_id)
