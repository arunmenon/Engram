"""Tests for health probe endpoints (liveness and readiness)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.testclient import TestClient

from context_graph.api.routes.health import router as health_router
from context_graph.settings import Settings


def _make_app(redis_healthy: bool = True, neo4j_healthy: bool = True) -> FastAPI:
    """Build a minimal FastAPI app with health routes and mock stores."""
    app = FastAPI(default_response_class=ORJSONResponse)
    app.include_router(health_router)

    event_store = AsyncMock()
    event_store.health_ping = AsyncMock(return_value=redis_healthy)

    graph_store = AsyncMock()
    graph_store.health_ping = AsyncMock(return_value=neo4j_healthy)

    app.state.settings = Settings()
    app.state.event_store = event_store
    app.state.graph_store = graph_store

    return app


def test_liveness_always_200() -> None:
    """GET /health/live always returns 200 regardless of dependency state."""
    app = _make_app(redis_healthy=False, neo4j_healthy=False)
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_healthy() -> None:
    """GET /health/ready returns 200 when both Redis and Neo4j are up."""
    app = _make_app(redis_healthy=True, neo4j_healthy=True)
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["redis"] is True
    assert data["neo4j"] is True


def test_readiness_redis_down_503() -> None:
    """GET /health/ready returns 503 when Redis is down."""
    app = _make_app(redis_healthy=False, neo4j_healthy=True)
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] is False
    assert data["neo4j"] is True


def test_readiness_neo4j_down_503() -> None:
    """GET /health/ready returns 503 when Neo4j is down."""
    app = _make_app(redis_healthy=True, neo4j_healthy=False)
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] is True
    assert data["neo4j"] is False


def test_readiness_both_down_503() -> None:
    """GET /health/ready returns 503 when both are down."""
    app = _make_app(redis_healthy=False, neo4j_healthy=False)
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"


def test_backward_compat_health() -> None:
    """GET /health delegates to readiness logic."""
    app = _make_app(redis_healthy=True, neo4j_healthy=True)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readiness_redis_exception_503() -> None:
    """GET /health/ready returns 503 when Redis ping raises an exception."""
    app = _make_app(redis_healthy=True, neo4j_healthy=True)
    # Override to raise an exception
    app.state.event_store.health_ping = AsyncMock(side_effect=ConnectionError("conn refused"))
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["redis"] is False
