"""Session context endpoint.

GET /v1/context/{session_id} — assemble working memory context for a session,
ranked by decay score.

Source: ADR-0006, ADR-0009
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from context_graph.api.dependencies import get_retrieval
from context_graph.domain.models import AtlasResponse  # noqa: TCH001 — runtime: response_model
from context_graph.ports.retrieval import Retrieval  # noqa: TCH001 — runtime: Depends()

router = APIRouter(tags=["context"])

RetrievalDep = Annotated[Retrieval, Depends(get_retrieval)]


@router.get("/context/{session_id}", response_model=AtlasResponse)
async def get_session_context(
    session_id: str,
    retrieval: RetrievalDep,
    max_nodes: int = Query(default=100, ge=1, le=500),
    max_depth: int = Query(default=3, ge=1, le=10),
    query: str | None = Query(default=None),
    cursor: str | None = Query(default=None, description="Pagination cursor"),
) -> AtlasResponse:
    """Assemble working memory context for a session, ranked by decay score."""
    return await retrieval.get_context(session_id, max_nodes, query, max_depth, cursor=cursor)
