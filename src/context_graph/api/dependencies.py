"""FastAPI dependency injection helpers.

Extracts shared resources from ``app.state`` so route handlers can
declare them via ``Depends()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request  # noqa: TCH002 — runtime: FastAPI dependency injection

if TYPE_CHECKING:
    from context_graph.adapters.neo4j.store import Neo4jGraphStore
    from context_graph.adapters.redis.store import RedisEventStore
    from context_graph.settings import Settings


def get_settings(request: Request) -> Settings:
    """Return the application settings from app state."""
    return request.app.state.settings  # type: ignore[no-any-return]


def get_event_store(request: Request) -> RedisEventStore:
    """Return the Redis event store from app state."""
    return request.app.state.event_store  # type: ignore[no-any-return]


def get_graph_store(request: Request) -> Neo4jGraphStore:
    """Return the Neo4j graph store from app state."""
    return request.app.state.graph_store  # type: ignore[no-any-return]
