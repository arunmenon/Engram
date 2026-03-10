"""Unit tests for the admin API endpoints.

Tests use in-memory stubs for Redis/Neo4j -- no external services required.
The admin routes now use protocol-based DI (GraphMaintenance, EventStoreAdmin,
HealthCheckable) instead of patching module-level maintenance functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from tests.unit.conftest import InMemoryEventStore, StubGraphStore

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Custom stubs for admin tests
# ---------------------------------------------------------------------------


class _AdminGraphStore(StubGraphStore):
    """Graph store with configurable responses for admin endpoint tests."""

    def __init__(
        self,
        session_event_counts: dict[str, int] | None = None,
        graph_stats: dict[str, Any] | None = None,
        session_query_results: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(healthy=True)
        self._session_event_counts = session_event_counts or {}
        self._graph_stats = graph_stats or {
            "nodes": {},
            "edges": {},
            "total_nodes": 0,
            "total_edges": 0,
        }
        self._session_query_results = session_query_results or []

    async def get_session_event_counts(self, tenant_id: str = "default") -> dict[str, int]:
        return self._session_event_counts

    async def get_graph_stats(self, tenant_id: str = "default") -> dict[str, Any]:
        return self._graph_stats

    async def run_session_query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._session_query_results


class _AdminEventStore(InMemoryEventStore):
    """Event store with a configurable stream_length for admin tests."""

    def __init__(self, stream_length: int = 42) -> None:
        super().__init__()
        self._stream_len = stream_length

    async def stream_length(self, tenant_id: str = "default") -> int:
        return self._stream_len


def _make_admin_client(
    session_event_counts: dict[str, int] | None = None,
    graph_stats: dict[str, Any] | None = None,
    session_query_results: list[dict[str, Any]] | None = None,
    stream_length: int = 42,
) -> TestClient:
    """Build a FastAPI TestClient with admin-compatible protocol stubs."""
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
    app.state.event_store = _AdminEventStore(stream_length=stream_length)
    app.state.graph_store = _AdminGraphStore(
        session_event_counts=session_event_counts,
        graph_stats=graph_stats,
        session_query_results=session_query_results,
    )

    return _TestClient(app)


@pytest.fixture()
def admin_test_client() -> TestClient:
    """FastAPI TestClient wired with admin-compatible stubs."""
    return _make_admin_client()


# ---------------------------------------------------------------------------
# POST /v1/admin/reconsolidate
# ---------------------------------------------------------------------------


class TestReconsolidate:
    """Tests for the reconsolidate endpoint."""

    def test_reconsolidate_no_sessions(self) -> None:
        """When no sessions exist, reconsolidate returns zeros."""
        client = _make_admin_client(session_event_counts={})
        response = client.post("/v1/admin/reconsolidate", json={})

        assert response.status_code == 200
        body = response.json()
        assert body["sessions_processed"] == 0
        assert body["summaries_created"] == 0
        assert body["events_processed"] == 0

    def test_reconsolidate_below_threshold(self) -> None:
        """Sessions below the threshold are not processed."""
        client = _make_admin_client(session_event_counts={"sess-1": 2})
        response = client.post("/v1/admin/reconsolidate", json={})

        assert response.status_code == 200
        body = response.json()
        assert body["sessions_processed"] == 0

    def test_reconsolidate_specific_session(self) -> None:
        """Requesting a specific session_id processes it (no events found)."""
        client = _make_admin_client(session_event_counts={"sess-1": 10})
        response = client.post(
            "/v1/admin/reconsolidate",
            json={"session_id": "sess-1"},
        )

        # No events found in the stub graph, so 0 processed
        assert response.status_code == 200
        body = response.json()
        assert body["sessions_processed"] == 0
        assert body["events_processed"] == 0

    def test_reconsolidate_empty_body(self) -> None:
        """Empty JSON body is accepted (no specific session)."""
        client = _make_admin_client(session_event_counts={})
        response = client.post("/v1/admin/reconsolidate", json={})

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /v1/admin/stats
# ---------------------------------------------------------------------------


class TestStats:
    """Tests for the stats endpoint."""

    def test_stats_returns_structure(self) -> None:
        """Stats should return nodes, edges, and redis sub-keys."""
        client = _make_admin_client(
            graph_stats={
                "nodes": {"Event": 10, "Entity": 5},
                "edges": {"FOLLOWS": 8},
                "total_nodes": 15,
                "total_edges": 8,
            },
            stream_length=42,
        )
        response = client.get("/v1/admin/stats")

        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "edges" in body
        assert "redis" in body
        assert body["nodes"]["Event"] == 10
        assert body["redis"]["stream_length"] == 42

    def test_stats_empty_graph(self) -> None:
        """Stats for an empty graph should return zero counts."""
        client = _make_admin_client(
            graph_stats={
                "nodes": {},
                "edges": {},
                "total_nodes": 0,
                "total_edges": 0,
            },
        )
        response = client.get("/v1/admin/stats")

        assert response.status_code == 200
        body = response.json()
        assert body["total_nodes"] == 0
        assert body["total_edges"] == 0


# ---------------------------------------------------------------------------
# POST /v1/admin/prune
# ---------------------------------------------------------------------------


class TestPrune:
    """Tests for the prune endpoint."""

    def test_prune_warm_dry_run(self) -> None:
        """Warm dry run returns planned actions without executing."""
        client = _make_admin_client()
        response = client.post(
            "/v1/admin/prune",
            json={"tier": "warm", "dry_run": True},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is True

    def test_prune_cold_dry_run(self) -> None:
        """Cold dry run returns planned node deletions."""
        client = _make_admin_client()
        response = client.post(
            "/v1/admin/prune",
            json={"tier": "cold", "dry_run": True},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is True

    def test_prune_invalid_tier(self) -> None:
        """Invalid tier returns 422."""
        client = _make_admin_client()
        response = client.post(
            "/v1/admin/prune",
            json={"tier": "invalid", "dry_run": True},
        )
        assert response.status_code == 422

    def test_prune_warm_execute(self) -> None:
        """Warm prune with dry_run=false calls maintenance protocol."""
        client = _make_admin_client()
        response = client.post(
            "/v1/admin/prune",
            json={"tier": "warm", "dry_run": False},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is False

    def test_prune_cold_execute(self) -> None:
        """Cold prune with dry_run=false calls delete protocol methods."""
        client = _make_admin_client()
        response = client.post(
            "/v1/admin/prune",
            json={"tier": "cold", "dry_run": False},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["dry_run"] is False


# ---------------------------------------------------------------------------
# GET /v1/admin/health/detailed
# ---------------------------------------------------------------------------


class TestHealthDetailed:
    """Tests for the detailed health endpoint."""

    def test_health_detailed_healthy(self) -> None:
        """When both services are up, status is healthy."""
        client = _make_admin_client(
            graph_stats={
                "nodes": {"Event": 5},
                "edges": {"FOLLOWS": 3},
                "total_nodes": 5,
                "total_edges": 3,
            },
            stream_length=42,
        )
        response = client.get("/v1/admin/health/detailed")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["redis"]["connected"] is True
        assert body["redis"]["stream_length"] == 42
        assert body["neo4j"]["connected"] is True
        assert body["neo4j"]["nodes"]["Event"] == 5
        assert body["version"] == "0.1.0"


# ---------------------------------------------------------------------------
# POST /v1/admin/replay
# ---------------------------------------------------------------------------


class TestReplayEndpoint:
    """Tests for POST /v1/admin/replay."""

    def test_replay_requires_confirm(self) -> None:
        """Replay should reject when confirm is false."""
        client = _make_admin_client()
        response = client.post(
            "/v1/admin/replay",
            json={"confirm": False},
        )
        assert response.status_code == 400

    def test_replay_clears_and_rebuilds(self) -> None:
        """Replay should clear graph and replay events."""
        client = _make_admin_client()

        response = client.post(
            "/v1/admin/replay",
            json={"confirm": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert "events_replayed" in data
        assert "nodes_created" in data
        assert "edges_created" in data
        assert data["events_replayed"] == 0
