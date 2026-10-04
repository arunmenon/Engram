"""Artifact queries over ontology pack types (ADR-0018 phase 2).

``POST /v1/query/artifacts`` answers questions about the artifacts packs
add (PDLC: tickets, changes, requirements, decisions, incidents, ...)
with ``ArtifactRetriever``: intent from the pack keywords (or given),
seeds from keys in the question (or given node ids), bounded traversal
over the intent's weighted edges, the packs' admission rules, and set
differences for completeness questions. Responses use the Atlas pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from context_graph.retrieval.artifacts import ArtifactQuery

if TYPE_CHECKING:
    from context_graph.retrieval.artifacts import ArtifactRetriever
    from context_graph.settings import Settings

router = APIRouter(tags=["query"])

# Upper bounds on a request (the response is bounded by max_nodes)
MAX_QUERY_LENGTH = 2000
MAX_SEED_IDS = 50


class ArtifactQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    seed_node_ids: list[str] = Field(default_factory=list, max_length=MAX_SEED_IDS)
    intent: str | None = None
    max_depth: int | None = Field(default=None, ge=1)
    max_nodes: int | None = Field(default=None, ge=1)
    include_untrusted: bool = False


@router.post("/query/artifacts")
async def query_artifacts(body: ArtifactQueryRequest, request: Request) -> ORJSONResponse:
    retriever: ArtifactRetriever = request.app.state.artifacts
    settings: Settings = request.app.state.settings
    limits = settings.query
    if body.intent is not None and body.intent not in retriever.intents:
        return ORJSONResponse(
            status_code=422,
            content={"detail": f"intent must be one of {sorted(retriever.intents)}"},
        )
    if body.max_depth is not None and body.max_depth > limits.max_max_depth:
        return ORJSONResponse(
            status_code=422, content={"detail": f"max_depth is at most {limits.max_max_depth}"}
        )
    if body.max_nodes is not None and body.max_nodes > limits.max_max_nodes:
        return ORJSONResponse(
            status_code=422, content={"detail": f"max_nodes is at most {limits.max_max_nodes}"}
        )
    response = await retriever.retrieve(
        ArtifactQuery(
            query=body.query,
            seed_node_ids=tuple(body.seed_node_ids),
            intent=body.intent,
            max_depth=body.max_depth,
            max_nodes=body.max_nodes or limits.default_max_nodes,
            include_untrusted=body.include_untrusted,
        )
    )
    return ORJSONResponse(content=response.model_dump(mode="json"))
