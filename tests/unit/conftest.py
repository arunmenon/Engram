"""Unit test conftest with in-memory store stubs for API testing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from context_graph.domain.models import (
        AtlasResponse,
        Event,
        EventQuery,
        LineageQuery,
        SubgraphQuery,
    )


class InMemoryEventStore:
    """Minimal in-memory EventStore + EventStoreAdmin that satisfies protocols for unit tests."""

    def __init__(self) -> None:
        self._events: dict[str, Event] = {}
        self._counter: int = 0

    async def append(
        self,
        event: Event,
        payload: dict[str, Any] | None = None,
    ) -> str:
        event_id_str = str(event.event_id)
        if event_id_str in self._events:
            return f"0-{self._counter}"
        self._counter += 1
        position = f"{self._counter}-0"
        self._events[event_id_str] = event
        return position

    async def append_batch(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
    ) -> list[str]:
        positions: list[str] = []
        for idx, event in enumerate(events):
            event_payload = payloads[idx] if payloads and idx < len(payloads) else None
            position = await self.append(event, payload=event_payload)
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

    # EventStoreAdmin protocol
    async def health_ping(self) -> bool:
        return True

    async def stream_length(self) -> int:
        return self._counter


class StubGraphStore:
    """Stub GraphStore satisfying GraphStore + HealthCheckable + GraphMaintenance + UserStore."""

    def __init__(self, healthy: bool = True) -> None:
        self._healthy = healthy
        # Configurable entity lookup response
        self._entities: dict[str, dict[str, object]] = {}

    async def ensure_constraints(self) -> None:
        pass

    async def get_context(
        self,
        session_id: str,
        max_nodes: int = 100,
        query: str | None = None,
        max_depth: int = 3,
        cursor: str | None = None,
    ) -> AtlasResponse:
        from context_graph.domain.models import AtlasResponse

        return AtlasResponse()

    async def get_subgraph(self, query: SubgraphQuery) -> AtlasResponse:
        from context_graph.domain.models import AtlasResponse

        return AtlasResponse()

    async def get_lineage(self, query: LineageQuery) -> AtlasResponse:
        from context_graph.domain.models import AtlasResponse

        return AtlasResponse()

    async def get_entity(self, entity_id: str) -> dict[str, object] | None:
        return self._entities.get(entity_id)

    async def close(self) -> None:
        pass

    # HealthCheckable protocol
    async def health_ping(self) -> bool:
        return self._healthy

    # GraphMaintenance protocol
    async def get_session_event_counts(self) -> dict[str, int]:
        return {}

    async def get_graph_stats(self) -> dict[str, Any]:
        return {"nodes": {}, "edges": {}, "total_nodes": 0, "total_edges": 0}

    async def write_summary_with_edges(
        self,
        summary_id: str,
        scope: str,
        scope_id: str,
        content: str,
        created_at: str,
        event_count: int,
        time_range: list[str],
        event_ids: list[str],
    ) -> None:
        pass

    async def delete_edges_by_type_and_age(self, min_score: float, max_age_hours: int) -> int:
        return 0

    async def delete_cold_events(
        self, max_age_hours: int, min_importance: int, min_access_count: int
    ) -> int:
        return 0

    async def delete_archive_events(self, event_ids: list[str]) -> int:
        return 0

    async def get_archive_event_ids(self, max_age_hours: int) -> list[str]:
        return []

    async def delete_orphan_nodes(self, batch_size: int = 500) -> tuple[dict[str, int], list[str]]:
        return {}, []

    async def update_importance_from_centrality(self) -> int:
        return 0

    async def run_session_query(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    # UserStore protocol
    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        return None

    async def get_user_preferences(
        self, user_id: str, active_only: bool = True
    ) -> list[dict[str, Any]]:
        return []

    async def get_user_skills(self, user_id: str) -> list[dict[str, Any]]:
        return []

    async def get_user_patterns(self, user_id: str) -> list[dict[str, Any]]:
        return []

    async def get_user_interests(self, user_id: str) -> list[dict[str, Any]]:
        return []

    async def delete_user_data(self, user_id: str) -> int:
        return 0

    async def export_user_data(self, user_id: str) -> dict[str, Any]:
        return {}

    async def write_user_profile(self, profile_data: dict[str, Any]) -> None:
        pass

    async def write_preference_with_edges(
        self,
        user_entity_id: str,
        preference_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        pass

    async def write_skill_with_edges(
        self,
        user_entity_id: str,
        skill_data: dict[str, Any],
        source_event_ids: list[str],
        derivation_info: dict[str, Any],
    ) -> None:
        pass

    async def write_interest_edge(
        self,
        user_entity_id: str,
        entity_name: str,
        entity_type: str,
        weight: float,
        source: str,
    ) -> None:
        pass

    async def write_derived_from_edge(
        self,
        source_node_id: str,
        source_id_field: str,
        event_id: str,
        method: str,
        session_id: str,
    ) -> None:
        pass


@pytest.fixture()
def in_memory_event_store() -> InMemoryEventStore:
    """Return a fresh in-memory event store."""
    return InMemoryEventStore()


@pytest.fixture()
def stub_graph_store() -> StubGraphStore:
    """Return a fresh stub graph store."""
    return StubGraphStore(healthy=True)


@pytest.fixture()
def test_client(
    in_memory_event_store: InMemoryEventStore,
    stub_graph_store: StubGraphStore,
) -> TestClient:
    """FastAPI TestClient with in-memory stores (no Redis/Neo4j needed)."""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from fastapi.testclient import TestClient as _TestClient

    from context_graph.api.middleware import register_middleware
    from context_graph.api.routes.context import router as context_router
    from context_graph.api.routes.entities import router as entities_router
    from context_graph.api.routes.events import router as events_router
    from context_graph.api.routes.health import router as health_router
    from context_graph.api.routes.lineage import router as lineage_router
    from context_graph.api.routes.query import router as query_router

    app = FastAPI(default_response_class=ORJSONResponse)
    register_middleware(app)
    app.include_router(events_router, prefix="/v1")
    app.include_router(health_router, prefix="/v1")
    app.include_router(context_router, prefix="/v1")
    app.include_router(query_router, prefix="/v1")
    app.include_router(lineage_router, prefix="/v1")
    app.include_router(entities_router, prefix="/v1")

    from context_graph.settings import Settings

    # Wire stubs into app state (settings needed for auth dependency)
    app.state.settings = Settings()
    app.state.event_store = in_memory_event_store
    app.state.graph_store = stub_graph_store

    return _TestClient(app)
