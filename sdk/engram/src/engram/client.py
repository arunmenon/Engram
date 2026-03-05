from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from engram.config import EngramConfig, get_config
from engram.models import (
    AtlasResponse,
    BatchResult,
    BehavioralPatternNode,
    DetailedHealthResponse,
    EntityResponse,
    Event,
    GDPRDeleteResponse,
    GDPRExportResponse,
    HealthStatus,
    IngestResult,
    InterestNode,
    PreferenceNode,
    PruneResponse,
    ReconsolidateResponse,
    SkillNode,
    StatsResponse,
    SubgraphQuery,
    UserProfile,
)
from engram.transport import Transport

if TYPE_CHECKING:
    from engram.sessions import SessionManager

# Validation constants
MAX_ID_LENGTH = 512
MAX_PAYLOAD_SIZE = 10_000_000  # 10MB
MAX_NODES_LIMIT = 10_000
MAX_DEPTH_LIMIT = 100

_INVISIBLE_UNICODE_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")


def _validate_path_param(value: str, name: str) -> str:
    """Validate a path parameter to prevent injection attacks."""
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty or whitespace-only")
    if len(value) > MAX_ID_LENGTH:
        raise ValueError(f"{name} exceeds maximum length of {MAX_ID_LENGTH}")
    if "\x00" in value:
        raise ValueError(f"{name} must not contain null bytes")
    if "\r" in value or "\n" in value:
        raise ValueError(f"{name} must not contain control characters")
    if ".." in value or "/" in value or "\\" in value:
        raise ValueError(f"{name} must not contain path traversal characters")
    if "%" in value:
        raise ValueError(f"{name} must not contain URL-encoded characters")
    if _INVISIBLE_UNICODE_RE.search(value):
        raise ValueError(f"{name} must not contain invisible unicode characters")
    return value


def _validate_numeric_param(value: int, name: str, min_val: int, max_val: int) -> int:
    """Validate a numeric parameter is within bounds."""
    if value < min_val or value > max_val:
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")
    return value


class EngramClient:
    """Async Engram API client with typed methods for all endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        admin_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        config: EngramConfig | None = None,
    ) -> None:
        """Create client. Params override config; config overrides env vars."""
        effective = config if config is not None else get_config()

        overrides: dict[str, Any] = {}
        if base_url is not None:
            overrides["base_url"] = base_url
        if api_key is not None:
            overrides["api_key"] = api_key
        if admin_key is not None:
            overrides["admin_key"] = admin_key
        if timeout is not None:
            overrides["timeout"] = timeout
        if max_retries is not None:
            overrides["max_retries"] = max_retries

        if overrides:
            effective = effective.model_copy(update=overrides)

        self._config = effective
        self._transport = Transport(effective)

    # --- Event endpoints ---

    async def ingest(self, event: Event) -> IngestResult:
        """POST /v1/events — ingest a single event."""
        if len(event.payload_ref) > MAX_PAYLOAD_SIZE:
            raise ValueError(f"payload_ref exceeds maximum size of {MAX_PAYLOAD_SIZE} bytes")
        data = event.model_dump(mode="json", exclude_none=True)
        response = await self._transport.post("/events", json=data)
        return IngestResult.model_validate(response.json())

    async def ingest_batch(self, events: list[Event]) -> BatchResult:
        """POST /v1/events/batch — ingest a batch of events."""
        events_data = [e.model_dump(mode="json", exclude_none=True) for e in events]
        response = await self._transport.post("/events/batch", json={"events": events_data})
        return BatchResult.model_validate(response.json())

    # --- Context endpoint ---

    async def get_context(
        self,
        session_id: str,
        *,
        max_nodes: int = 100,
        max_depth: int = 3,
        query: str | None = None,
        cursor: str | None = None,
    ) -> AtlasResponse:
        """GET /v1/context/{session_id} — session working memory."""
        _validate_path_param(session_id, "session_id")
        _validate_numeric_param(max_nodes, "max_nodes", 1, MAX_NODES_LIMIT)
        _validate_numeric_param(max_depth, "max_depth", 1, MAX_DEPTH_LIMIT)
        params: dict[str, Any] = {"max_nodes": max_nodes, "max_depth": max_depth}
        if query is not None:
            params["query"] = query
        if cursor is not None:
            params["cursor"] = cursor
        response = await self._transport.get(f"/context/{session_id}", params=params)
        return AtlasResponse.model_validate(response.json())

    # --- Subgraph query ---

    async def query_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        """POST /v1/query/subgraph — intent-aware subgraph query."""
        response = await self._transport.post(
            "/query/subgraph", json=query.model_dump(exclude_none=True)
        )
        return AtlasResponse.model_validate(response.json())

    # --- Lineage ---

    async def get_lineage(
        self,
        node_id: str,
        *,
        max_depth: int = 3,
        max_nodes: int = 100,
        intent: str | None = "why",
        cursor: str | None = None,
    ) -> AtlasResponse:
        """GET /v1/nodes/{node_id}/lineage — causal chain traversal."""
        _validate_path_param(node_id, "node_id")
        _validate_numeric_param(max_depth, "max_depth", 1, MAX_DEPTH_LIMIT)
        _validate_numeric_param(max_nodes, "max_nodes", 1, MAX_NODES_LIMIT)
        params: dict[str, Any] = {"max_depth": max_depth, "max_nodes": max_nodes}
        if intent is not None:
            params["intent"] = intent
        if cursor is not None:
            params["cursor"] = cursor
        response = await self._transport.get(f"/nodes/{node_id}/lineage", params=params)
        return AtlasResponse.model_validate(response.json())

    # --- Entities ---

    async def get_entity(self, entity_id: str) -> EntityResponse:
        """GET /v1/entities/{entity_id} — entity with connected events."""
        _validate_path_param(entity_id, "entity_id")
        response = await self._transport.get(f"/entities/{entity_id}")
        return EntityResponse.model_validate(response.json())

    # --- Users (admin key required) ---

    async def get_user_profile(self, user_id: str) -> UserProfile:
        """GET /v1/users/{user_id}/profile."""
        _validate_path_param(user_id, "user_id")
        response = await self._transport.get(f"/users/{user_id}/profile", admin=True)
        return UserProfile.model_validate(response.json())

    async def get_user_preferences(
        self, user_id: str, category: str | None = None
    ) -> list[PreferenceNode]:
        """GET /v1/users/{user_id}/preferences."""
        _validate_path_param(user_id, "user_id")
        params: dict[str, Any] = {}
        if category is not None:
            params["category"] = category
        response = await self._transport.get(
            f"/users/{user_id}/preferences", params=params or None, admin=True
        )
        return [PreferenceNode.model_validate(p) for p in response.json()]

    async def get_user_skills(self, user_id: str) -> list[SkillNode]:
        """GET /v1/users/{user_id}/skills."""
        _validate_path_param(user_id, "user_id")
        response = await self._transport.get(f"/users/{user_id}/skills", admin=True)
        return [SkillNode.model_validate(s) for s in response.json()]

    async def get_user_patterns(self, user_id: str) -> list[BehavioralPatternNode]:
        """GET /v1/users/{user_id}/patterns."""
        _validate_path_param(user_id, "user_id")
        response = await self._transport.get(f"/users/{user_id}/patterns", admin=True)
        return [BehavioralPatternNode.model_validate(p) for p in response.json()]

    async def get_user_interests(self, user_id: str) -> list[InterestNode]:
        """GET /v1/users/{user_id}/interests."""
        _validate_path_param(user_id, "user_id")
        response = await self._transport.get(f"/users/{user_id}/interests", admin=True)
        return [InterestNode.model_validate(i) for i in response.json()]

    async def export_user_data(self, user_id: str) -> GDPRExportResponse:
        """GET /v1/users/{user_id}/data-export — GDPR export."""
        _validate_path_param(user_id, "user_id")
        response = await self._transport.get(f"/users/{user_id}/data-export", admin=True)
        return GDPRExportResponse.model_validate(response.json())

    async def delete_user(self, user_id: str) -> GDPRDeleteResponse:
        """DELETE /v1/users/{user_id} — GDPR cascade erasure."""
        _validate_path_param(user_id, "user_id")
        response = await self._transport.delete(f"/users/{user_id}", admin=True)
        return GDPRDeleteResponse.model_validate(response.json())

    # --- Health ---

    async def health(self) -> HealthStatus:
        """GET /v1/health."""
        response = await self._transport.get("/health")
        return HealthStatus.model_validate(response.json())

    # --- Admin ---

    async def stats(self) -> StatsResponse:
        """GET /v1/admin/stats."""
        response = await self._transport.get("/admin/stats", admin=True)
        return StatsResponse.model_validate(response.json())

    async def reconsolidate(self, session_id: str | None = None) -> ReconsolidateResponse:
        """POST /v1/admin/reconsolidate."""
        json_data: dict[str, Any] | None = None
        if session_id is not None:
            json_data = {"session_id": session_id}
        response = await self._transport.post("/admin/reconsolidate", json=json_data, admin=True)
        return ReconsolidateResponse.model_validate(response.json())

    async def prune(self, tier: str, dry_run: bool = True) -> PruneResponse:
        """POST /v1/admin/prune."""
        response = await self._transport.post(
            "/admin/prune", json={"tier": tier, "dry_run": dry_run}, admin=True
        )
        return PruneResponse.model_validate(response.json())

    async def health_detailed(self) -> DetailedHealthResponse:
        """GET /v1/admin/health/detailed."""
        response = await self._transport.get("/admin/health/detailed", admin=True)
        return DetailedHealthResponse.model_validate(response.json())

    # --- Session management ---

    def session(self, agent_id: str) -> SessionManager:
        """Create a SessionManager context manager for auto-managed sessions."""
        # Imported at runtime to avoid circular import
        from engram.sessions import SessionManager as _SessionManager

        return _SessionManager(client=self, agent_id=agent_id)

    # --- Pagination ---

    def paginate_context(
        self,
        session_id: str,
        *,
        max_nodes: int = 100,
        max_depth: int = 3,
        query: str | None = None,
    ) -> AsyncIterator[AtlasResponse]:
        """Async iterator that auto-paginates get_context."""
        # Imported at runtime to avoid circular import
        from engram.pagination import PageIterator as _PageIterator

        return _PageIterator(
            self.get_context,
            session_id=session_id,
            max_nodes=max_nodes,
            max_depth=max_depth,
            query=query,
        )

    def paginate_lineage(
        self,
        node_id: str,
        *,
        max_depth: int = 3,
        max_nodes: int = 100,
        intent: str | None = "why",
    ) -> AsyncIterator[AtlasResponse]:
        """Async iterator that auto-paginates get_lineage."""
        from engram.pagination import PageIterator as _PageIterator

        return _PageIterator(
            self.get_lineage,
            node_id=node_id,
            max_depth=max_depth,
            max_nodes=max_nodes,
            intent=intent,
        )

    # --- Lifecycle ---

    async def close(self) -> None:
        """Close the transport."""
        await self._transport.close()

    async def __aenter__(self) -> EngramClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
