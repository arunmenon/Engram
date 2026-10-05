"""Artifact queries over ontology pack types (ADR-0018 phase 2).

``POST /v1/query/artifacts`` answers questions about the artifacts packs
add (PDLC: tickets, changes, requirements, decisions, incidents, ...)
with ``ArtifactRetriever``: intent from the pack keywords (or given),
seeds from keys in the question (or given node ids), bounded traversal
over the intent's weighted edges, the packs' admission rules, and set
differences for completeness questions. Responses use the Atlas pattern.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, ConfigDict, Field

from context_graph.retrieval.artifacts import ArtifactQuery

if TYPE_CHECKING:
    from context_graph.retrieval.artifacts import ArtifactRetriever
    from context_graph.settings import Settings

router = APIRouter(tags=["query"])


class ArtifactQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    seed_node_ids: list[str] = Field(default_factory=list)
    intent: str | None = None
    max_depth: int | None = Field(default=None, ge=1)
    max_nodes: int | None = Field(default=None, ge=1)
    # Untrusted items without trusted corroboration, marked ``untrusted``
    include_untrusted: bool = False


def _invalid(detail: str) -> ORJSONResponse:
    return ORJSONResponse(status_code=422, content={"detail": detail})


@router.post("/query/artifacts")
async def query_artifacts(body: ArtifactQueryRequest, request: Request) -> ORJSONResponse:
    retriever: ArtifactRetriever = request.app.state.artifacts
    settings: Settings = request.app.state.settings
    limits = settings.query
    ontology = settings.ontology
    query = body.query.strip()
    if not query:
        return _invalid("query is empty")
    if len(query) > ontology.retrieval_max_query_length:
        return _invalid(f"query is at most {ontology.retrieval_max_query_length} characters")
    if len(body.seed_node_ids) > ontology.retrieval_max_seed_ids:
        return _invalid(f"seed_node_ids has at most {ontology.retrieval_max_seed_ids} ids")
    if body.intent is not None and body.intent not in retriever.intents:
        return _invalid(f"intent must be one of {sorted(retriever.intents)}")
    # Decision 10: packs whose evaluation set has not passed on this graph
    pending: frozenset[str] = frozenset()
    if not ontology.serve_unevaluated:
        pending = await request.app.state.eval_pending.packs()
    if body.intent is not None and request.app.state.ontology.intents[body.intent].pack in pending:
        pack = request.app.state.ontology.intents[body.intent].pack
        return ORJSONResponse(
            status_code=409,
            content={
                "detail": f"intent {body.intent!r} belongs to pack {pack!r}, whose evaluation "
                "set has not passed on this graph; run python -m context_graph.ontology "
                "evaluate --record (or set CG_ONTOLOGY_SERVE_UNEVALUATED=true in development)"
            },
        )
    if body.max_depth is not None and body.max_depth > limits.max_max_depth:
        return _invalid(f"max_depth is at most {limits.max_max_depth}")
    if body.max_nodes is not None and body.max_nodes > limits.max_max_nodes:
        return _invalid(f"max_nodes is at most {limits.max_max_nodes}")
    try:
        response = await asyncio.wait_for(
            retriever.retrieve(
                ArtifactQuery(
                    query=query,
                    seed_node_ids=tuple(body.seed_node_ids),
                    intent=body.intent,
                    max_depth=body.max_depth,
                    max_nodes=body.max_nodes or limits.default_max_nodes,
                    include_untrusted=body.include_untrusted,
                    exclude_packs=pending,
                )
            ),
            timeout=limits.default_timeout_ms / 1000.0,
        )
    except TimeoutError:
        return ORJSONResponse(
            status_code=504,
            content={"detail": f"query exceeded {limits.default_timeout_ms} ms"},
        )
    return ORJSONResponse(content=response.model_dump(mode="json"))
