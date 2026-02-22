"""FastAPI dependency injection helpers.

Extracts shared resources from ``app.state`` so route handlers can
declare them via ``Depends()``.

Includes API key authentication guards for securing endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request  # noqa: TCH002 — runtime: FastAPI dependency injection

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


# ---------------------------------------------------------------------------
# Authentication guards
# ---------------------------------------------------------------------------


def _extract_bearer_token(request: Request) -> str | None:
    """Extract a Bearer token from the Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def require_api_key(request: Request) -> None:
    """Validate ``Authorization: Bearer <api_key>`` header.

    When ``CG_AUTH_API_KEY`` is not set (None), auth is disabled and all
    requests pass through.  When set, the Bearer token must match.
    """
    settings: Settings = request.app.state.settings
    expected_key = settings.auth.api_key
    if expected_key is None:
        return  # auth disabled in development mode

    token = _extract_bearer_token(request)
    if token is None or token != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def require_admin_key(request: Request) -> None:
    """Validate ``Authorization: Bearer <admin_key>`` header.

    Admin endpoints (admin routes, GDPR delete/export) require the
    admin-level key.  When ``CG_AUTH_ADMIN_KEY`` is not set, auth is
    disabled.
    """
    settings: Settings = request.app.state.settings
    expected_key = settings.auth.admin_key
    if expected_key is None:
        return  # auth disabled in development mode

    token = _extract_bearer_token(request)
    if token is None or token != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")
