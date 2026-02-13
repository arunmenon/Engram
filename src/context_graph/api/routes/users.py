"""User endpoints for profile, preferences, skills, patterns, and GDPR ops.

GET    /v1/users/{user_id}/profile      — user profile
GET    /v1/users/{user_id}/preferences   — active preferences (optional category filter)
GET    /v1/users/{user_id}/skills        — skills with proficiency
GET    /v1/users/{user_id}/patterns      — behavioral patterns
GET    /v1/users/{user_id}/interests     — user interests
GET    /v1/users/{user_id}/data-export   — GDPR data export
DELETE /v1/users/{user_id}               — GDPR cascade erasure

Source: ADR-0012 §10.4
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse

from context_graph.adapters.neo4j import user_queries
from context_graph.adapters.neo4j.store import Neo4jGraphStore  # noqa: TCH001
from context_graph.api.dependencies import get_graph_store

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

GraphStoreDep = Annotated[Neo4jGraphStore, Depends(get_graph_store)]


@router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    graph_store: GraphStoreDep,
) -> ORJSONResponse:
    """Return the profile for a given user, or 404 if not found."""
    profile = await user_queries.get_user_profile(
        graph_store._driver,
        graph_store._database,
        user_id,
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile not found")
    return ORJSONResponse(content=profile)


@router.get("/{user_id}/preferences")
async def get_user_preferences(
    user_id: str,
    graph_store: GraphStoreDep,
    category: str | None = Query(default=None),
) -> ORJSONResponse:
    """Return active preferences for a user, optionally filtered by category."""
    preferences = await user_queries.get_user_preferences(
        graph_store._driver,
        graph_store._database,
        user_id,
        active_only=True,
    )
    if category is not None:
        preferences = [p for p in preferences if p.get("category") == category]
    return ORJSONResponse(content=preferences)


@router.get("/{user_id}/skills")
async def get_user_skills(
    user_id: str,
    graph_store: GraphStoreDep,
) -> ORJSONResponse:
    """Return skills with proficiency for a user."""
    skills = await user_queries.get_user_skills(
        graph_store._driver,
        graph_store._database,
        user_id,
    )
    return ORJSONResponse(content=skills)


@router.get("/{user_id}/patterns")
async def get_user_patterns(
    user_id: str,
    graph_store: GraphStoreDep,
) -> ORJSONResponse:
    """Return behavioral patterns for a user."""
    patterns = await user_queries.get_user_patterns(
        graph_store._driver,
        graph_store._database,
        user_id,
    )
    return ORJSONResponse(content=patterns)


@router.get("/{user_id}/interests")
async def get_user_interests(
    user_id: str,
    graph_store: GraphStoreDep,
) -> ORJSONResponse:
    """Return interests for a user."""
    interests = await user_queries.get_user_interests(
        graph_store._driver,
        graph_store._database,
        user_id,
    )
    return ORJSONResponse(content=interests)


@router.get("/{user_id}/data-export")
async def export_user_data(
    user_id: str,
    graph_store: GraphStoreDep,
) -> ORJSONResponse:
    """GDPR data export — return all stored data for a user."""
    data = await user_queries.export_user_data(
        graph_store._driver,
        graph_store._database,
        user_id,
    )
    logger.info("user_data_exported", user_id=user_id)
    return ORJSONResponse(content=data)


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    graph_store: GraphStoreDep,
) -> ORJSONResponse:
    """GDPR cascade erasure — delete all data associated with a user."""
    deleted_count = await user_queries.delete_user_data(
        graph_store._driver,
        graph_store._database,
        user_id,
    )
    logger.info("user_data_erased", user_id=user_id, deleted_count=deleted_count)
    return ORJSONResponse(content={"deleted_count": deleted_count, "status": "erased"})
