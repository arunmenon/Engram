"""Session context endpoint.

GET /v1/context/{session_id} — assemble working memory context for a session,
ranked by decay score.

Source: ADR-0006, ADR-0009
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from context_graph.adapters.neo4j.store import Neo4jGraphStore  # noqa: TCH001 — runtime: Depends()
from context_graph.api.dependencies import get_graph_store
from context_graph.domain.models import AtlasResponse  # noqa: TCH001 — runtime: response_model

router = APIRouter(tags=["context"])

GraphStoreDep = Annotated[Neo4jGraphStore, Depends(get_graph_store)]


@router.get("/context/{session_id}", response_model=AtlasResponse)
async def get_session_context(
    session_id: str,
    graph_store: GraphStoreDep,
    max_nodes: int = Query(default=100, ge=1, le=500),
    max_depth: int = Query(default=3, ge=1, le=10),
    query: str | None = Query(default=None),
) -> AtlasResponse:
    """Assemble working memory context for a session, ranked by decay score."""
    return await graph_store.get_context(session_id, max_nodes, query)
