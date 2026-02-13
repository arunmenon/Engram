"""Unit tests for the users API endpoints.

Tests use mocked user_queries functions — no external services required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Stub graph store
# ---------------------------------------------------------------------------


class _StubNeo4jDriver:
    """Minimal stub so graph_store._driver is not None."""

    pass


class _StubGraphStore:
    """Stub graph store exposing _driver and _database."""

    def __init__(self) -> None:
        self._driver = _StubNeo4jDriver()
        self._database = "neo4j"

    async def ensure_constraints(self) -> None:
        pass

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

_PATCH_PREFIX = "context_graph.api.routes.users.user_queries"


@pytest.fixture()
def users_test_client() -> TestClient:
    """FastAPI TestClient wired with a stub graph store for user routes."""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from fastapi.testclient import TestClient as _TestClient

    from context_graph.api.middleware import register_middleware
    from context_graph.api.routes.users import router as users_router

    app = FastAPI(default_response_class=ORJSONResponse)
    register_middleware(app)
    app.include_router(users_router, prefix="/v1")

    app.state.graph_store = _StubGraphStore()

    return _TestClient(app)


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/profile
# ---------------------------------------------------------------------------


class TestGetUserProfile:
    """Tests for the profile endpoint."""

    def test_profile_found(self, users_test_client: TestClient) -> None:
        """Returns profile data when user exists."""
        profile = {"user_id": "u1", "display_name": "Alice", "created_at": "2025-01-01"}
        with patch(
            f"{_PATCH_PREFIX}.get_user_profile",
            new_callable=AsyncMock,
            return_value=profile,
        ):
            response = users_test_client.get("/v1/users/u1/profile")

        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == "u1"
        assert body["display_name"] == "Alice"

    def test_profile_not_found(self, users_test_client: TestClient) -> None:
        """Returns 404 when user does not exist."""
        with patch(
            f"{_PATCH_PREFIX}.get_user_profile",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = users_test_client.get("/v1/users/unknown/profile")

        assert response.status_code == 404
        assert response.json()["detail"] == "User profile not found"


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/preferences
# ---------------------------------------------------------------------------


class TestGetUserPreferences:
    """Tests for the preferences endpoint."""

    def test_preferences_list(self, users_test_client: TestClient) -> None:
        """Returns a list of preferences."""
        prefs = [
            {"preference_id": "p1", "category": "tool", "value": "vim"},
            {"preference_id": "p2", "category": "language", "value": "python"},
        ]
        with patch(
            f"{_PATCH_PREFIX}.get_user_preferences",
            new_callable=AsyncMock,
            return_value=prefs,
        ):
            response = users_test_client.get("/v1/users/u1/preferences")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2

    def test_preferences_filter_by_category(self, users_test_client: TestClient) -> None:
        """Category query param filters results."""
        prefs = [
            {"preference_id": "p1", "category": "tool", "value": "vim"},
            {"preference_id": "p2", "category": "language", "value": "python"},
        ]
        with patch(
            f"{_PATCH_PREFIX}.get_user_preferences",
            new_callable=AsyncMock,
            return_value=prefs,
        ):
            response = users_test_client.get("/v1/users/u1/preferences?category=tool")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["category"] == "tool"

    def test_preferences_empty(self, users_test_client: TestClient) -> None:
        """Returns empty list when no preferences exist."""
        with patch(
            f"{_PATCH_PREFIX}.get_user_preferences",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = users_test_client.get("/v1/users/u1/preferences")

        assert response.status_code == 200
        assert response.json() == []

    def test_preferences_category_no_match(self, users_test_client: TestClient) -> None:
        """Returns empty list when category filter matches nothing."""
        prefs = [{"preference_id": "p1", "category": "tool", "value": "vim"}]
        with patch(
            f"{_PATCH_PREFIX}.get_user_preferences",
            new_callable=AsyncMock,
            return_value=prefs,
        ):
            response = users_test_client.get("/v1/users/u1/preferences?category=nonexistent")

        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/skills
# ---------------------------------------------------------------------------


class TestGetUserSkills:
    """Tests for the skills endpoint."""

    def test_skills_list(self, users_test_client: TestClient) -> None:
        """Returns a list of skills with proficiency."""
        skills = [
            {"skill_id": "s1", "name": "Python", "proficiency": 0.85},
            {"skill_id": "s2", "name": "SQL", "proficiency": 0.6},
        ]
        with patch(
            f"{_PATCH_PREFIX}.get_user_skills",
            new_callable=AsyncMock,
            return_value=skills,
        ):
            response = users_test_client.get("/v1/users/u1/skills")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["name"] == "Python"

    def test_skills_empty(self, users_test_client: TestClient) -> None:
        """Returns empty list when no skills exist."""
        with patch(
            f"{_PATCH_PREFIX}.get_user_skills",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = users_test_client.get("/v1/users/u1/skills")

        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/patterns
# ---------------------------------------------------------------------------


class TestGetUserPatterns:
    """Tests for the patterns endpoint."""

    def test_patterns_list(self, users_test_client: TestClient) -> None:
        """Returns a list of behavioral patterns."""
        patterns = [
            {"pattern_id": "bp1", "description": "Prefers TDD workflow"},
        ]
        with patch(
            f"{_PATCH_PREFIX}.get_user_patterns",
            new_callable=AsyncMock,
            return_value=patterns,
        ):
            response = users_test_client.get("/v1/users/u1/patterns")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["pattern_id"] == "bp1"


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/interests
# ---------------------------------------------------------------------------


class TestGetUserInterests:
    """Tests for the interests endpoint."""

    def test_interests_list(self, users_test_client: TestClient) -> None:
        """Returns a list of user interests."""
        interests = [
            {"entity_id": "ent-1", "name": "distributed-systems"},
            {"entity_id": "ent-2", "name": "graph-databases"},
        ]
        with patch(
            f"{_PATCH_PREFIX}.get_user_interests",
            new_callable=AsyncMock,
            return_value=interests,
        ):
            response = users_test_client.get("/v1/users/u1/interests")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/data-export
# ---------------------------------------------------------------------------


class TestExportUserData:
    """Tests for the GDPR data export endpoint."""

    def test_data_export_returns_all(self, users_test_client: TestClient) -> None:
        """Returns aggregated user data for GDPR export."""
        export = {
            "profile": {"user_id": "u1", "display_name": "Alice"},
            "preferences": [{"preference_id": "p1"}],
            "skills": [{"skill_id": "s1"}],
            "patterns": [],
            "interests": [],
        }
        with patch(
            f"{_PATCH_PREFIX}.export_user_data",
            new_callable=AsyncMock,
            return_value=export,
        ):
            response = users_test_client.get("/v1/users/u1/data-export")

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

    def test_delete_returns_count(self, users_test_client: TestClient) -> None:
        """Returns deleted_count and status on successful erasure."""
        with patch(
            f"{_PATCH_PREFIX}.delete_user_data",
            new_callable=AsyncMock,
            return_value=7,
        ):
            response = users_test_client.delete("/v1/users/u1")

        assert response.status_code == 200
        body = response.json()
        assert body["deleted_count"] == 7
        assert body["status"] == "erased"

    def test_delete_zero_records(self, users_test_client: TestClient) -> None:
        """Returns zero deleted_count when user has no data."""
        with patch(
            f"{_PATCH_PREFIX}.delete_user_data",
            new_callable=AsyncMock,
            return_value=0,
        ):
            response = users_test_client.delete("/v1/users/no-data")

        assert response.status_code == 200
        body = response.json()
        assert body["deleted_count"] == 0
        assert body["status"] == "erased"
