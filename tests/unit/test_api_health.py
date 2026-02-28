"""Tests for the health check endpoint — 200 healthy, 503 degraded/unhealthy."""

from __future__ import annotations

from tests.unit.conftest import InMemoryEventStore, StubGraphStore, _StubRedisClient


def _make_health_client(redis_healthy: bool = True, neo4j_healthy: bool = True):
    """Build a FastAPI TestClient with configurable health states."""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from fastapi.testclient import TestClient

    from context_graph.api.routes.health import router as health_router
    from context_graph.settings import Settings

    app = FastAPI(default_response_class=ORJSONResponse)
    app.include_router(health_router, prefix="/v1")
    store = InMemoryEventStore()
    store._client = _StubRedisClient(healthy=redis_healthy)  # type: ignore[attr-defined]
    app.state.settings = Settings()
    app.state.event_store = store
    app.state.graph_store = StubGraphStore(healthy=neo4j_healthy)
    return TestClient(app)


class TestHealthCheckHealthy:
    """When both Redis and Neo4j are reachable."""

    def test_returns_200(self) -> None:
        client = _make_health_client(redis_healthy=True, neo4j_healthy=True)
        resp = client.get("/v1/health")
        assert resp.status_code == 200

    def test_status_is_healthy(self) -> None:
        client = _make_health_client(redis_healthy=True, neo4j_healthy=True)
        body = client.get("/v1/health").json()
        assert body["status"] == "healthy"

    def test_redis_and_neo4j_true(self) -> None:
        client = _make_health_client(redis_healthy=True, neo4j_healthy=True)
        body = client.get("/v1/health").json()
        assert body["redis"] is True
        assert body["neo4j"] is True

    def test_version_field_present(self) -> None:
        client = _make_health_client(redis_healthy=True, neo4j_healthy=True)
        body = client.get("/v1/health").json()
        assert body["version"] == "0.1.0"


class TestHealthCheckRedisDown:
    """When only Redis is unreachable — degraded."""

    def test_returns_503(self) -> None:
        client = _make_health_client(redis_healthy=False, neo4j_healthy=True)
        resp = client.get("/v1/health")
        assert resp.status_code == 503

    def test_status_is_degraded(self) -> None:
        client = _make_health_client(redis_healthy=False, neo4j_healthy=True)
        body = client.get("/v1/health").json()
        assert body["status"] == "degraded"

    def test_redis_false_neo4j_true(self) -> None:
        client = _make_health_client(redis_healthy=False, neo4j_healthy=True)
        body = client.get("/v1/health").json()
        assert body["redis"] is False
        assert body["neo4j"] is True


class TestHealthCheckNeo4jDown:
    """When only Neo4j is unreachable — degraded."""

    def test_returns_503(self) -> None:
        client = _make_health_client(redis_healthy=True, neo4j_healthy=False)
        resp = client.get("/v1/health")
        assert resp.status_code == 503

    def test_status_is_degraded(self) -> None:
        client = _make_health_client(redis_healthy=True, neo4j_healthy=False)
        body = client.get("/v1/health").json()
        assert body["status"] == "degraded"

    def test_redis_true_neo4j_false(self) -> None:
        client = _make_health_client(redis_healthy=True, neo4j_healthy=False)
        body = client.get("/v1/health").json()
        assert body["redis"] is True
        assert body["neo4j"] is False


class TestHealthCheckBothDown:
    """When both Redis and Neo4j are unreachable — unhealthy."""

    def test_returns_503(self) -> None:
        client = _make_health_client(redis_healthy=False, neo4j_healthy=False)
        resp = client.get("/v1/health")
        assert resp.status_code == 503

    def test_status_is_unhealthy(self) -> None:
        client = _make_health_client(redis_healthy=False, neo4j_healthy=False)
        body = client.get("/v1/health").json()
        assert body["status"] == "unhealthy"

    def test_redis_false_neo4j_false(self) -> None:
        client = _make_health_client(redis_healthy=False, neo4j_healthy=False)
        body = client.get("/v1/health").json()
        assert body["redis"] is False
        assert body["neo4j"] is False
