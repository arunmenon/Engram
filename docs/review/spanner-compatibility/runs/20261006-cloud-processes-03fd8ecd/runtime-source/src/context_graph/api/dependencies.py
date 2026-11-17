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
    from context_graph.ports.retrieval import Retrieval
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


def get_retrieval(request: Request) -> Retrieval:
    """Return the retrieval engine from app state (ADR-0019 C3).

    Falls back to the graph store, whose deprecated query methods delegate
    to the same engine, when no engine was attached (for example in apps
    assembled by tests).
    """
    retrieval = getattr(request.app.state, "retrieval", None)
    if retrieval is None:
        if getattr(request.app.state, "tenant_binding", None) is not None:
            raise HTTPException(status_code=503, detail="Tenant retrieval unavailable")
        return request.app.state.graph_store  # type: ignore[no-any-return]
    return retrieval  # type: ignore[no-any-return]


def get_event_store_admin(request: Request) -> EventStoreAdmin:
    """Return the event store (admin view) from app state."""
    return request.app.state.event_store  # type: ignore[no-any-return]


def get_graph_maintenance(request: Request) -> GraphMaintenance:
    """Return the graph maintenance service from app state."""
    return request.app.state.graph_store  # type: ignore[no-any-return]


def get_user_store(request: Request) -> UserStore:
    """Ordinary user reads require the selected user schema."""
    bundle = getattr(request.app.state, "bundle", None)
    if bundle is None:
        raise HTTPException(status_code=503, detail="Pack configuration unavailable")
    if not any(name == "user" for name, _version in bundle.pack_identities):
        raise HTTPException(status_code=404, detail="User capability is not enabled")
    return get_user_privacy_store(request)


def get_user_privacy_store(request: Request) -> UserStore:
    """Retain export/erasure access to historical data when user reads are disabled.

    Authentication and tenant authorization still apply; this only separates
    privacy operations from the optional ordinary-read capability gate.
    """
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
    if getattr(request.app.state, "tenant_binding", None) is not None:
        _require_tenant_role(request, "api")
        return
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
    if getattr(request.app.state, "tenant_binding", None) is not None:
        _require_tenant_role(request, "admin")
        return
    settings: Settings = request.app.state.settings
    expected_key = settings.auth.admin_key
    if expected_key is None:
        return  # auth disabled in development mode

    token = _extract_bearer_token(request)
    if token is None or not hmac.compare_digest(token, expected_key):
        logger.warning("auth_failed", path=str(request.url.path), guard="admin_key")
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")


def _require_tenant_role(request: Request, role: str) -> None:
    from context_graph.tenancy import Principal

    principal = request.scope.get("engram.principal")
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="Tenant authentication required")
    binding = request.app.state.tenant_binding
    if principal.tenant_id != binding.tenant_id or role not in principal.roles:
        raise HTTPException(status_code=403, detail="Tenant role is not authorized")
