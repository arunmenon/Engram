"""Lineage traversal endpoint.

GET /v1/nodes/{node_id}/lineage — traverse CAUSED_BY chains from a node.

Source: ADR-0009
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from context_graph.api.dependencies import TenantContext, get_graph_store, require_tenant
from context_graph.domain.models import (  # noqa: TCH001 — runtime: type annotations + response_model
    AtlasResponse,
    IntentType,
    LineageQuery,
)
from context_graph.ports.graph_store import GraphStore  # noqa: TCH001 — runtime: Depends()

router = APIRouter(tags=["lineage"])

GraphStoreDep = Annotated[GraphStore, Depends(get_graph_store)]
TenantDep = Annotated[TenantContext, Depends(require_tenant)]


@router.get("/nodes/{node_id}/lineage", response_model=AtlasResponse)
async def get_lineage(
    node_id: str,
    graph_store: GraphStoreDep,
    tenant: TenantDep,
    max_depth: int = Query(default=3, ge=1, le=10),
    max_nodes: int = Query(default=100, ge=1, le=500),
    intent: str | None = Query(default="why"),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
) -> AtlasResponse:
    """Traverse lineage (CAUSED_BY chains) from a node."""
    intent_type = IntentType(intent) if intent else None
    lineage_query = LineageQuery(
        node_id=node_id,
        max_depth=max_depth,
        max_nodes=max_nodes,
        intent=intent_type,
        cursor=cursor,
    )
    return await graph_store.get_lineage(lineage_query, tenant_id=tenant.tenant_id)
