"""Unit tests for API key authentication guards.

Verifies that endpoints reject requests when auth keys are configured
and the correct Bearer token is not provided.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.fixture()
def auth_test_client() -> TestClient:
    """TestClient with auth keys configured — endpoints require Bearer tokens."""
    from fastapi import Depends, FastAPI
    from fastapi.responses import ORJSONResponse
    from fastapi.testclient import TestClient as _TestClient

    from context_graph.api.dependencies import require_admin_key, require_api_key
    from context_graph.api.routes.events import router as events_router
    from context_graph.api.routes.health import router as health_router
    from context_graph.api.routes.users import router as users_router
    from context_graph.settings import Settings

    app = FastAPI(default_response_class=ORJSONResponse)

    # Configure auth keys
    settings = Settings()
    settings.auth.api_key = "test-api-key"
    settings.auth.admin_key = "test-admin-key"
    app.state.settings = settings

    # Stub stores
    from tests.unit.conftest import InMemoryEventStore, StubGraphStore, _StubRedisClient

    store = InMemoryEventStore()
    store._client = _StubRedisClient(healthy=True)  # type: ignore[attr-defined]
    app.state.event_store = store
    app.state.graph_store = StubGraphStore(healthy=True)

    # Wire routers with auth guards (matches app.py pattern)
    app.include_router(events_router, prefix="/v1", dependencies=[Depends(require_api_key)])
    app.include_router(users_router, prefix="/v1", dependencies=[Depends(require_admin_key)])
    app.include_router(health_router, prefix="/v1")  # no auth

    return _TestClient(app)


class TestApiKeyAuth:
    """Tests for require_api_key guard."""

    def test_rejects_missing_auth_header(self, auth_test_client: TestClient) -> None:
        resp = auth_test_client.post("/v1/events", json={"event_type": "test"})
        assert resp.status_code == 401
        assert "API key" in resp.json()["detail"]

    def test_rejects_wrong_api_key(self, auth_test_client: TestClient) -> None:
        resp = auth_test_client.post(
            "/v1/events",
            json={"event_type": "test"},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401

    def test_accepts_correct_api_key(self, auth_test_client: TestClient) -> None:
        resp = auth_test_client.post(
            "/v1/events",
            json={"event_type": "test"},
            headers={"Authorization": "Bearer test-api-key"},
        )
        # 422 = validation error (expected, we sent incomplete event data)
        # The point is it got PAST the auth guard
        assert resp.status_code == 422

    def test_rejects_basic_auth(self, auth_test_client: TestClient) -> None:
        resp = auth_test_client.post(
            "/v1/events",
            json={"event_type": "test"},
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401


class TestAdminKeyAuth:
    """Tests for require_admin_key guard."""

    def test_rejects_missing_auth_header(self, auth_test_client: TestClient) -> None:
        resp = auth_test_client.get("/v1/users/u1/profile")
        assert resp.status_code == 401
        assert "admin key" in resp.json()["detail"]

    def test_rejects_api_key_on_admin_route(self, auth_test_client: TestClient) -> None:
        """API key should not work on admin-protected routes."""
        resp = auth_test_client.get(
            "/v1/users/u1/profile",
            headers={"Authorization": "Bearer test-api-key"},
        )
        assert resp.status_code == 401

    def test_accepts_admin_key(self, auth_test_client: TestClient) -> None:
        with patch(
            "context_graph.api.routes.users.user_queries.get_user_profile",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = auth_test_client.get(
                "/v1/users/u1/profile",
                headers={"Authorization": "Bearer test-admin-key"},
            )
        # 404 = user not found (expected, mock returns None)
        # The point is it got PAST the auth guard
        assert resp.status_code == 404


class TestHealthNoAuth:
    """Health endpoint should not require auth."""

    def test_health_accessible_without_auth(self, auth_test_client: TestClient) -> None:
        resp = auth_test_client.get("/v1/health")
        assert resp.status_code == 200


class TestTimingSafeComparison:
    """Verify that auth uses hmac.compare_digest for timing-safe comparison."""

    def test_api_key_uses_hmac_compare_digest(self, auth_test_client: TestClient) -> None:
        with patch("context_graph.api.dependencies.hmac") as mock_hmac:
            mock_hmac.compare_digest.return_value = False
            resp = auth_test_client.post(
                "/v1/events",
                json={"event_type": "test"},
                headers={"Authorization": "Bearer wrong-key"},
            )
            assert resp.status_code == 401
            mock_hmac.compare_digest.assert_called_once_with("wrong-key", "test-api-key")

    def test_admin_key_uses_hmac_compare_digest(self, auth_test_client: TestClient) -> None:
        with patch("context_graph.api.dependencies.hmac") as mock_hmac:
            mock_hmac.compare_digest.return_value = False
            resp = auth_test_client.get(
                "/v1/users/u1/profile",
                headers={"Authorization": "Bearer wrong-key"},
            )
            assert resp.status_code == 401
            mock_hmac.compare_digest.assert_called_once_with("wrong-key", "test-admin-key")


class TestAuthFailureLogging:
    """Verify that failed auth attempts are logged."""

    def test_failed_api_key_logs_warning(self, auth_test_client: TestClient) -> None:
        with patch("context_graph.api.dependencies.logger") as mock_logger:
            auth_test_client.post(
                "/v1/events",
                json={"event_type": "test"},
                headers={"Authorization": "Bearer bad-key"},
            )
            mock_logger.warning.assert_called_once_with(
                "auth_failed", path="/v1/events", guard="api_key"
            )

    def test_failed_admin_key_logs_warning(self, auth_test_client: TestClient) -> None:
        with patch("context_graph.api.dependencies.logger") as mock_logger:
            auth_test_client.get(
                "/v1/users/u1/profile",
                headers={"Authorization": "Bearer bad-key"},
            )
            mock_logger.warning.assert_called_once_with(
                "auth_failed", path="/v1/users/u1/profile", guard="admin_key"
            )

    def test_missing_token_logs_warning(self, auth_test_client: TestClient) -> None:
        with patch("context_graph.api.dependencies.logger") as mock_logger:
            auth_test_client.post("/v1/events", json={"event_type": "test"})
            mock_logger.warning.assert_called_once_with(
                "auth_failed", path="/v1/events", guard="api_key"
            )


class TestAuthDisabled:
    """When auth keys are None, all requests pass through."""

    def test_no_auth_when_keys_unset(self, test_client: TestClient) -> None:
        """Default test_client has no auth keys — events endpoint should work."""
        from datetime import UTC, datetime
        from uuid import uuid4

        event = {
            "event_id": str(uuid4()),
            "event_type": "tool.execute",
            "occurred_at": datetime.now(UTC).isoformat(),
            "session_id": "s1",
            "agent_id": "a1",
            "trace_id": "t1",
            "payload_ref": "p:1",
        }
        resp = test_client.post("/v1/events", json=event)
        assert resp.status_code == 201
