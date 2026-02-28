"""FastAPI dependency injection helpers.

Extracts shared resources from ``app.state`` so route handlers can
declare them via ``Depends()``.

Includes API key authentication guards for securing endpoints.

All return types use port protocols, not concrete adapters, to enforce
hexagonal architecture boundaries (routes never import from adapters/).
"""

from __future__ import annotations

import hmac
from typing import TYPE_CHECKING

import structlog
from fastapi import HTTPException, Request  # noqa: TCH002 — runtime: FastAPI dependency injection

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from context_graph.ports.event_store import EventStore, EventStoreAdmin
    from context_graph.ports.graph_store import GraphStore
    from context_graph.ports.health import HealthCheckable
    from context_graph.ports.maintenance import GraphMaintenance
    from context_graph.ports.user_store import UserStore
    from context_graph.settings import Settings


def get_settings(request: Request) -> Settings:
    """Return the application settings from app state."""
    return request.app.state.settings  # type: ignore[no-any-return]


def get_event_store(request: Request) -> EventStore:
    """Return the event store from app state."""
    return request.app.state.event_store  # type: ignore[no-any-return]


def get_graph_store(request: Request) -> GraphStore:
    """Return the graph store from app state."""
    return request.app.state.graph_store  # type: ignore[no-any-return]


def get_event_store_admin(request: Request) -> EventStoreAdmin:
    """Return the event store (admin view) from app state."""
    return request.app.state.event_store  # type: ignore[no-any-return]


def get_graph_maintenance(request: Request) -> GraphMaintenance:
    """Return the graph maintenance service from app state."""
    return request.app.state.graph_store  # type: ignore[no-any-return]


def get_user_store(request: Request) -> UserStore:
    """Return the user store from app state."""
    return request.app.state.graph_store  # type: ignore[no-any-return]


def get_event_health(request: Request) -> HealthCheckable:
    """Return the event store for health checks."""
    return request.app.state.event_store  # type: ignore[no-any-return]


def get_graph_health(request: Request) -> HealthCheckable:
    """Return the graph store for health checks."""
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
    if token is None or not hmac.compare_digest(token, expected_key):
        logger.warning("auth_failed", path=str(request.url.path), guard="api_key")
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
    if token is None or not hmac.compare_digest(token, expected_key):
        logger.warning("auth_failed", path=str(request.url.path), guard="admin_key")
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")
