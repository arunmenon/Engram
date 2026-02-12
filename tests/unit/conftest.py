"""Unit test conftest with in-memory store stubs for API testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from context_graph.domain.models import Event, EventQuery


class InMemoryEventStore:
    """Minimal in-memory EventStore that satisfies the protocol for unit tests."""

    def __init__(self) -> None:
        self._events: dict[str, Event] = {}
        self._counter: int = 0

    async def append(self, event: Event) -> str:
        event_id_str = str(event.event_id)
        if event_id_str in self._events:
            return f"0-{self._counter}"
        self._counter += 1
        position = f"{self._counter}-0"
        self._events[event_id_str] = event
        return position

    async def append_batch(self, events: list[Event]) -> list[str]:
        positions: list[str] = []
        for event in events:
            position = await self.append(event)
            positions.append(position)
        return positions

    async def get_by_id(self, event_id: str) -> Event | None:
        return self._events.get(event_id)

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        after: str | None = None,
    ) -> list[Event]:
        return [e for e in self._events.values() if e.session_id == session_id][:limit]

    async def search(self, query: EventQuery) -> list[Event]:
        return list(self._events.values())[: query.limit]

    async def ensure_indexes(self) -> None:
        pass

    async def close(self) -> None:
        pass


class StubGraphStore:
    """Minimal stub GraphStore for health check tests."""

    def __init__(self, healthy: bool = True) -> None:
        self._healthy = healthy
        # Simulate driver/database for health check access
        self._driver = _StubDriver(healthy)
        self._database = "neo4j"

    async def ensure_constraints(self) -> None:
        pass

    async def close(self) -> None:
        pass


class _StubDriver:
    """Stub Neo4j driver for health checks."""

    def __init__(self, healthy: bool) -> None:
        self._healthy = healthy

    def session(self, database: str | None = None) -> _StubSession:
        return _StubSession(self._healthy)


class _StubSession:
    """Stub Neo4j session."""

    def __init__(self, healthy: bool) -> None:
        self._healthy = healthy

    async def __aenter__(self) -> _StubSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def run(self, query: str, *args: object, **kwargs: object) -> None:
        if not self._healthy:
            msg = "Neo4j unavailable"
            raise ConnectionError(msg)


class _StubRedisClient:
    """Stub Redis client for health check PING."""

    def __init__(self, healthy: bool = True) -> None:
        self._healthy = healthy

    async def ping(self) -> bool:
        if not self._healthy:
            msg = "Redis unavailable"
            raise ConnectionError(msg)
        return True


@pytest.fixture()
def in_memory_event_store() -> InMemoryEventStore:
    """Return a fresh in-memory event store."""
    return InMemoryEventStore()


@pytest.fixture()
def test_client(in_memory_event_store: InMemoryEventStore) -> TestClient:
    """FastAPI TestClient with in-memory stores (no Redis/Neo4j needed)."""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from fastapi.testclient import TestClient as _TestClient

    from context_graph.api.middleware import register_middleware
    from context_graph.api.routes.events import router as events_router
    from context_graph.api.routes.health import router as health_router

    app = FastAPI(default_response_class=ORJSONResponse)
    register_middleware(app)
    app.include_router(events_router, prefix="/v1")
    app.include_router(health_router, prefix="/v1")

    store = in_memory_event_store
    graph_store = StubGraphStore(healthy=True)

    # Wire stubs into app state
    app.state.event_store = store
    app.state.graph_store = graph_store
    # Health check accesses _client directly
    store._client = _StubRedisClient(healthy=True)  # type: ignore[attr-defined]

    return _TestClient(app)
