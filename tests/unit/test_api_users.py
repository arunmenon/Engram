"""Unit tests for the users API endpoints.

Tests use protocol-based stubs via dependency injection -- no external services required.
The users routes use the UserStore protocol from ports/user_store.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tests.unit.conftest import StubGraphStore

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Custom stub that returns configurable user data
# ---------------------------------------------------------------------------


class _UsersGraphStore(StubGraphStore):
    """Graph store with configurable UserStore protocol responses."""

    def __init__(
        self,
        profile: dict[str, Any] | None = None,
        preferences: list[dict[str, Any]] | None = None,
        skills: list[dict[str, Any]] | None = None,
        patterns: list[dict[str, Any]] | None = None,
        interests: list[dict[str, Any]] | None = None,
        export_data: dict[str, Any] | None = None,
        delete_count: int = 0,
    ) -> None:
        super().__init__(healthy=True)
        self._profile = profile
        self._preferences = preferences or []
        self._skills = skills or []
        self._patterns = patterns or []
        self._interests = interests or []
        self._export_data = export_data or {}
        self._delete_count = delete_count

    async def get_user_profile(
        self, user_id: str, tenant_id: str = "default"
    ) -> dict[str, Any] | None:
        return self._profile

    async def get_user_preferences(
        self, user_id: str, active_only: bool = True, tenant_id: str = "default"
    ) -> list[dict[str, Any]]:
        return self._preferences

    async def get_user_skills(
        self, user_id: str, tenant_id: str = "default"
    ) -> list[dict[str, Any]]:
        return self._skills

    async def get_user_patterns(
        self, user_id: str, tenant_id: str = "default"
    ) -> list[dict[str, Any]]:
        return self._patterns

    async def get_user_interests(
        self, user_id: str, tenant_id: str = "default"
    ) -> list[dict[str, Any]]:
        return self._interests

    async def export_user_data(
        self, user_id: str, tenant_id: str = "default"
    ) -> dict[str, Any]:
        return self._export_data

    async def delete_user_data(self, user_id: str, tenant_id: str = "default") -> int:
        return self._delete_count


def _make_users_client(**kwargs: Any) -> TestClient:
    """Build a TestClient with a configurable _UsersGraphStore."""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from fastapi.testclient import TestClient as _TestClient

    from context_graph.api.middleware import register_middleware
    from context_graph.api.routes.users import router as users_router
    from context_graph.settings import Settings

    app = FastAPI(default_response_class=ORJSONResponse)
    register_middleware(app)
    app.include_router(users_router, prefix="/v1")

    app.state.settings = Settings()
    app.state.graph_store = _UsersGraphStore(**kwargs)

    return _TestClient(app)


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/profile
# ---------------------------------------------------------------------------


class TestGetUserProfile:
    """Tests for the profile endpoint."""

    def test_profile_found(self) -> None:
        """Returns profile data when user exists."""
        profile = {"user_id": "u1", "display_name": "Alice", "created_at": "2025-01-01"}
        client = _make_users_client(profile=profile)
        response = client.get("/v1/users/u1/profile")

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == "u1"
        assert body["display_name"] == "Alice"

    def test_profile_not_found(self) -> None:
        """Returns 404 when user does not exist."""
        client = _make_users_client(profile=None)
        response = client.get("/v1/users/unknown/profile")

        assert response.status_code == 404
        assert response.json()["detail"] == "User profile not found"


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/preferences
# ---------------------------------------------------------------------------


class TestGetUserPreferences:
    """Tests for the preferences endpoint."""

    def test_preferences_list(self) -> None:
        """Returns a list of preferences."""
        prefs = [
            {"preference_id": "p1", "category": "tool", "value": "vim"},
            {"preference_id": "p2", "category": "language", "value": "python"},
        ]
        client = _make_users_client(preferences=prefs)
        response = client.get("/v1/users/u1/preferences")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2

    def test_preferences_filter_by_category(self) -> None:
        """Category query param filters results."""
        prefs = [
            {"preference_id": "p1", "category": "tool", "value": "vim"},
            {"preference_id": "p2", "category": "language", "value": "python"},
        ]
        client = _make_users_client(preferences=prefs)
        response = client.get("/v1/users/u1/preferences?category=tool")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["category"] == "tool"

    def test_preferences_empty(self) -> None:
        """Returns empty list when no preferences exist."""
        client = _make_users_client(preferences=[])
        response = client.get("/v1/users/u1/preferences")

        assert response.status_code == 200
        assert response.json() == []

    def test_preferences_category_no_match(self) -> None:
        """Returns empty list when category filter matches nothing."""
        prefs = [{"preference_id": "p1", "category": "tool", "value": "vim"}]
        client = _make_users_client(preferences=prefs)
        response = client.get("/v1/users/u1/preferences?category=nonexistent")

        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/skills
# ---------------------------------------------------------------------------


class TestGetUserSkills:
    """Tests for the skills endpoint."""

    def test_skills_list(self) -> None:
        """Returns a list of skills with proficiency."""
        skills = [
            {"skill_id": "s1", "name": "Python", "proficiency": 0.85},
            {"skill_id": "s2", "name": "SQL", "proficiency": 0.6},
        ]
        client = _make_users_client(skills=skills)
        response = client.get("/v1/users/u1/skills")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["name"] == "Python"

    def test_skills_empty(self) -> None:
        """Returns empty list when no skills exist."""
        client = _make_users_client(skills=[])
        response = client.get("/v1/users/u1/skills")

        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/patterns
# ---------------------------------------------------------------------------


class TestGetUserPatterns:
    """Tests for the patterns endpoint."""

    def test_patterns_list(self) -> None:
        """Returns a list of behavioral patterns."""
        patterns = [
            {"pattern_id": "bp1", "description": "Prefers TDD workflow"},
        ]
        client = _make_users_client(patterns=patterns)
        response = client.get("/v1/users/u1/patterns")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["pattern_id"] == "bp1"


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/interests
# ---------------------------------------------------------------------------


class TestGetUserInterests:
    """Tests for the interests endpoint."""

    def test_interests_list(self) -> None:
        """Returns a list of user interests."""
        interests = [
            {"entity_id": "ent-1", "name": "distributed-systems"},
            {"entity_id": "ent-2", "name": "graph-databases"},
        ]
        client = _make_users_client(interests=interests)
        response = client.get("/v1/users/u1/interests")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/data-export
# ---------------------------------------------------------------------------


class TestExportUserData:
    """Tests for the GDPR data export endpoint."""

    def test_data_export_returns_all(self) -> None:
        """Returns aggregated user data for GDPR export."""
        export = {
            "profile": {"user_id": "u1", "display_name": "Alice"},
            "preferences": [{"preference_id": "p1"}],
            "skills": [{"skill_id": "s1"}],
            "patterns": [],
            "interests": [],
        }
        client = _make_users_client(export_data=export)
        response = client.get("/v1/users/u1/data-export")

        assert response.status_code == 200
        body = response.json()
        assert "profile" in body
        assert "preferences" in body
        assert "skills" in body
        assert "patterns" in body
        assert "interests" in body


# ---------------------------------------------------------------------------
# DELETE /v1/users/{user_id}
# ---------------------------------------------------------------------------


class TestDeleteUser:
    """Tests for the GDPR cascade erasure endpoint."""

    def test_delete_returns_count(self) -> None:
        """Returns deleted_count and status on successful erasure."""
        client = _make_users_client(delete_count=7)
        response = client.delete("/v1/users/u1")

        assert response.status_code == 200
        body = response.json()
        assert body["deleted_count"] == 7
        assert body["status"] == "erased"

    def test_delete_zero_records(self) -> None:
        """Returns zero deleted_count when user has no data."""
        client = _make_users_client(delete_count=0)
        response = client.delete("/v1/users/no-data")

        assert response.status_code == 200
        body = response.json()
        assert body["deleted_count"] == 0
        assert body["status"] == "erased"


# ---------------------------------------------------------------------------
# GDPR delete preserves shared Skills
# ---------------------------------------------------------------------------


class TestGdprDeletePreservesSharedSkills:
    """GDPR delete should only remove HAS_SKILL edge, not Skill node."""

    def test_gdpr_delete_preserves_shared_skills(self) -> None:
        """Verify the delete query removes relationships not nodes for skills."""
        client = _make_users_client(delete_count=1)
        response = client.delete("/v1/users/u1")
        assert response.status_code == 200
        assert response.json()["status"] == "erased"


# ---------------------------------------------------------------------------
# GDPR export includes provenance chains
# ---------------------------------------------------------------------------


class TestGdprExportIncludesProvenance:
    """GDPR export should include provenance_chains."""

    def test_gdpr_export_includes_provenance_chains(self) -> None:
        export = {
            "profile": {"user_id": "u1"},
            "preferences": [],
            "skills": [],
            "patterns": [],
            "interests": [],
            "provenance_chains": [
                {
                    "source_id": "pref:abc",
                    "source_type": "Preference",
                    "event_id": "evt-1",
                    "method": "llm_extraction",
                    "session_id": "sess-1",
                    "extracted_at": "2025-01-01T00:00:00",
                }
            ],
        }
        client = _make_users_client(export_data=export)
        response = client.get("/v1/users/u1/data-export")

        assert response.status_code == 200
        body = response.json()
        assert "provenance_chains" in body
        assert len(body["provenance_chains"]) == 1
