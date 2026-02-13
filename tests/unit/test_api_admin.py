"""Unit tests for the admin API endpoints.

Tests use in-memory stubs for Redis/Neo4j — no external services required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _StubRedisClientForAdmin:
    """Stub Redis client that supports ping and xlen."""

    def __init__(self, stream_length: int = 42) -> None:
        self._stream_length = stream_length

    async def ping(self) -> bool:
        return True

    async def xlen(self, key: str) -> int:
        return self._stream_length


class _StubEventStoreForAdmin:
    """Stub event store with a Redis-like _client for admin endpoints."""

    def __init__(self, stream_length: int = 42) -> None:
        self._client = _StubRedisClientForAdmin(stream_length)

        class _Settings:
            global_stream = "events:__global__"

        self._settings = _Settings()


class _StubNeo4jSession:
    """Stub Neo4j session that returns configurable results."""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self._results = results or []
        self._idx = 0

    async def __aenter__(self) -> _StubNeo4jSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def run(self, query: str, *args: object, **kwargs: object) -> _StubAsyncResult:
        result = _StubAsyncResult(self._results)
        return result

    async def execute_write(self, fn: Any) -> Any:
        return None


class _StubAsyncResult:
    """Stub async result that yields records."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records
        self._idx = 0

    def __aiter__(self) -> _StubAsyncResult:
        self._idx = 0
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self._idx >= len(self._records):
            raise StopAsyncIteration
        record = self._records[self._idx]
        self._idx += 1
        return record

    async def single(self) -> dict[str, Any] | None:
        if self._records:
            return self._records[0]
        return None


class _StubNeo4jDriver:
    """Stub Neo4j driver that returns a configurable session."""

    def __init__(self, healthy: bool = True) -> None:
        self._healthy = healthy

    def session(self, database: str | None = None) -> _StubNeo4jSession:
        if not self._healthy:
            msg = "Neo4j unavailable"
            raise ConnectionError(msg)
        return _StubNeo4jSession()


class _StubGraphStoreForAdmin:
    """Stub graph store with a driver accessible by admin routes."""

    def __init__(self, healthy: bool = True) -> None:
        self._driver = _StubNeo4jDriver(healthy)
        self._database = "neo4j"

    async def ensure_constraints(self) -> None:
        pass

    async def close(self) -> None:
        pass


@pytest.fixture()
def admin_test_client() -> TestClient:
    """FastAPI TestClient wired with admin-compatible stubs."""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from fastapi.testclient import TestClient as _TestClient

    from context_graph.api.middleware import register_middleware
    from context_graph.api.routes.admin import router as admin_router
    from context_graph.api.routes.health import router as health_router
    from context_graph.settings import Settings

    app = FastAPI(default_response_class=ORJSONResponse)
    register_middleware(app)
    app.include_router(health_router, prefix="/v1")
    app.include_router(admin_router, prefix="/v1")

    app.state.settings = Settings()
    app.state.event_store = _StubEventStoreForAdmin(stream_length=42)
    app.state.graph_store = _StubGraphStoreForAdmin(healthy=True)

    return _TestClient(app)


# ---------------------------------------------------------------------------
# POST /v1/admin/reconsolidate
# ---------------------------------------------------------------------------


class TestReconsolidate:
    """Tests for the reconsolidate endpoint."""

    def test_reconsolidate_no_sessions(self, admin_test_client: TestClient) -> None:
        """When no sessions exist, reconsolidate returns zeros."""
        with patch(
            "context_graph.api.routes.admin.maintenance.get_session_event_counts",
            new_callable=AsyncMock,
            return_value={},
        ):
            response = admin_test_client.post("/v1/admin/reconsolidate", json={})

        assert response.status_code == 200
        body = response.json()
        assert body["sessions_processed"] == 0
        assert body["summaries_created"] == 0
        assert body["events_processed"] == 0

    def test_reconsolidate_below_threshold(self, admin_test_client: TestClient) -> None:
        """Sessions below the threshold are not processed."""
        with patch(
            "context_graph.api.routes.admin.maintenance.get_session_event_counts",
            new_callable=AsyncMock,
            return_value={"sess-1": 10},
        ):
            response = admin_test_client.post("/v1/admin/reconsolidate", json={})

        assert response.status_code == 200
        body = response.json()
        assert body["sessions_processed"] == 0

    def test_reconsolidate_specific_session(self, admin_test_client: TestClient) -> None:
        """Requesting a specific session_id processes it regardless of threshold."""
        with (
            patch(
                "context_graph.api.routes.admin.maintenance.get_session_event_counts",
                new_callable=AsyncMock,
                return_value={"sess-1": 10},
            ),
        ):
            response = admin_test_client.post(
                "/v1/admin/reconsolidate",
                json={"session_id": "sess-1"},
            )

        # No events found in the stub graph, so 0 processed
        assert response.status_code == 200
        body = response.json()
        assert body["sessions_processed"] == 0
        assert body["events_processed"] == 0

    def test_reconsolidate_empty_body(self, admin_test_client: TestClient) -> None:
        """Empty body is accepted (no specific session)."""
        with patch(
            "context_graph.api.routes.admin.maintenance.get_session_event_counts",
            new_callable=AsyncMock,
            return_value={},
        ):
            response = admin_test_client.post("/v1/admin/reconsolidate")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /v1/admin/stats
# ---------------------------------------------------------------------------


class TestStats:
    """Tests for the stats endpoint."""

    def test_stats_returns_structure(self, admin_test_client: TestClient) -> None:
        """Stats should return nodes, edges, and redis sub-keys."""
        mock_stats = {
            "nodes": {"Event": 10, "Entity": 5},
            "edges": {"FOLLOWS": 8},
            "total_nodes": 15,
            "total_edges": 8,
        }
        with patch(
            "context_graph.api.routes.admin.maintenance.get_graph_stats",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            response = admin_test_client.get("/v1/admin/stats")

        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "edges" in body
        assert "redis" in body
        assert body["nodes"]["Event"] == 10
        assert body["redis"]["stream_length"] == 42

    def test_stats_empty_graph(self, admin_test_client: TestClient) -> None:
        """Stats for an empty graph should return zero counts."""
        mock_stats = {
            "nodes": {},
            "edges": {},
            "total_nodes": 0,
            "total_edges": 0,
        }
        with patch(
            "context_graph.api.routes.admin.maintenance.get_graph_stats",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            response = admin_test_client.get("/v1/admin/stats")

        assert response.status_code == 200
        body = response.json()
        assert body["total_nodes"] == 0
        assert body["total_edges"] == 0


# ---------------------------------------------------------------------------
# POST /v1/admin/prune
# ---------------------------------------------------------------------------


class TestPrune:
    """Tests for the prune endpoint."""

    def test_prune_warm_dry_run(self, admin_test_client: TestClient) -> None:
        """Warm dry run returns planned actions without executing."""
        with patch(
            "context_graph.api.routes.admin.get_pruning_actions",
        ) as mock_actions:
            from context_graph.domain.forgetting import PruningActions

            mock_actions.return_value = PruningActions(
                delete_edges=["evt-1", "evt-2"],
                delete_nodes=[],
                archive_event_ids=[],
            )
            response = admin_test_client.post(
                "/v1/admin/prune",
                json={"tier": "warm", "dry_run": True},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is True
        assert body["pruned_edges"] == 2
        assert body["pruned_nodes"] == 0

    def test_prune_cold_dry_run(self, admin_test_client: TestClient) -> None:
        """Cold dry run returns planned node deletions."""
        with patch(
            "context_graph.api.routes.admin.get_pruning_actions",
        ) as mock_actions:
            from context_graph.domain.forgetting import PruningActions

            mock_actions.return_value = PruningActions(
                delete_edges=[],
                delete_nodes=["evt-3"],
                archive_event_ids=["evt-4"],
            )
            response = admin_test_client.post(
                "/v1/admin/prune",
                json={"tier": "cold", "dry_run": True},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is True
        assert body["pruned_nodes"] == 2

    def test_prune_invalid_tier(self, admin_test_client: TestClient) -> None:
        """Invalid tier returns 422."""
        response = admin_test_client.post(
            "/v1/admin/prune",
            json={"tier": "invalid", "dry_run": True},
        )
        assert response.status_code == 422

    def test_prune_warm_execute(self, admin_test_client: TestClient) -> None:
        """Warm prune with dry_run=false calls maintenance functions."""
        with (
            patch(
                "context_graph.api.routes.admin.get_pruning_actions",
            ) as mock_actions,
            patch(
                "context_graph.api.routes.admin.maintenance.delete_edges_by_type_and_age",
                new_callable=AsyncMock,
                return_value=3,
            ),
        ):
            from context_graph.domain.forgetting import PruningActions

            mock_actions.return_value = PruningActions(
                delete_edges=["evt-1", "evt-2", "evt-3"],
                delete_nodes=[],
                archive_event_ids=[],
            )
            response = admin_test_client.post(
                "/v1/admin/prune",
                json={"tier": "warm", "dry_run": False},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is False
        assert body["pruned_edges"] == 3

    def test_prune_cold_execute(self, admin_test_client: TestClient) -> None:
        """Cold prune with dry_run=false calls delete functions."""
        with (
            patch(
                "context_graph.api.routes.admin.get_pruning_actions",
            ) as mock_actions,
            patch(
                "context_graph.api.routes.admin.maintenance.delete_cold_events",
                new_callable=AsyncMock,
                return_value=2,
            ),
            patch(
                "context_graph.api.routes.admin.maintenance.delete_archive_events",
                new_callable=AsyncMock,
                return_value=1,
            ),
        ):
            from context_graph.domain.forgetting import PruningActions

            mock_actions.return_value = PruningActions(
                delete_edges=[],
                delete_nodes=["evt-5", "evt-6"],
                archive_event_ids=["evt-7"],
            )
            response = admin_test_client.post(
                "/v1/admin/prune",
                json={"tier": "cold", "dry_run": False},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is False
        assert body["pruned_nodes"] == 3  # 2 cold + 1 archive


# ---------------------------------------------------------------------------
# GET /v1/admin/health/detailed
# ---------------------------------------------------------------------------


class TestHealthDetailed:
    """Tests for the detailed health endpoint."""

    def test_health_detailed_healthy(self, admin_test_client: TestClient) -> None:
        """When both services are up, status is healthy."""
        mock_stats = {
            "nodes": {"Event": 5},
            "edges": {"FOLLOWS": 3},
            "total_nodes": 5,
            "total_edges": 3,
        }
        with patch(
            "context_graph.api.routes.admin.maintenance.get_graph_stats",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            response = admin_test_client.get("/v1/admin/health/detailed")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["redis"]["connected"] is True
        assert body["redis"]["stream_length"] == 42
        assert body["neo4j"]["connected"] is True
        assert body["neo4j"]["nodes"]["Event"] == 5
        assert body["version"] == "0.1.0"

    def test_health_detailed_neo4j_down(self, admin_test_client: TestClient) -> None:
        """When Neo4j fails, status is degraded."""
        with patch(
            "context_graph.api.routes.admin.maintenance.get_graph_stats",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Neo4j down"),
        ):
            response = admin_test_client.get("/v1/admin/health/detailed")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["redis"]["connected"] is True
        assert body["neo4j"]["connected"] is False
