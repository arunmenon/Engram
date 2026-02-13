"""Lineage traversal endpoint.

GET /v1/nodes/{node_id}/lineage — traverse CAUSED_BY chains from a node.

Source: ADR-0009
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from context_graph.adapters.neo4j.store import Neo4jGraphStore  # noqa: TCH001 — runtime: Depends()
from context_graph.api.dependencies import get_graph_store
from context_graph.domain.models import (  # noqa: TCH001 — runtime: type annotations + response_model
    AtlasResponse,
    IntentType,
    LineageQuery,
)

router = APIRouter(tags=["lineage"])

GraphStoreDep = Annotated[Neo4jGraphStore, Depends(get_graph_store)]


@router.get("/nodes/{node_id}/lineage", response_model=AtlasResponse)
async def get_lineage(
    node_id: str,
    graph_store: GraphStoreDep,
    max_depth: int = Query(default=3, ge=1, le=10),
    max_nodes: int = Query(default=100, ge=1, le=500),
    intent: str | None = Query(default="why"),
) -> AtlasResponse:
    """Traverse lineage (CAUSED_BY chains) from a node."""
    intent_type = IntentType(intent) if intent else None
    lineage_query = LineageQuery(
        node_id=node_id,
        max_depth=max_depth,
        max_nodes=max_nodes,
        intent=intent_type,
    )
    return await graph_store.get_lineage(lineage_query)
