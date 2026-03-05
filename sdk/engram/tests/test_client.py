from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
import respx

from engram import EngramClient, EngramConfig
from engram.exceptions import NotFoundError
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
from tests.conftest import make_atlas_response, make_ingest_response


@pytest.fixture
def config() -> EngramConfig:
    return EngramConfig(base_url="http://test:8000", api_key="test-key", admin_key="admin-key")


@pytest.fixture
def mock_api():
    with respx.mock(base_url="http://test:8000/v1") as router:
        yield router


@pytest.fixture
def client(config: EngramConfig) -> EngramClient:
    return EngramClient(config=config)


def _sample_event(**overrides) -> Event:
    defaults = {
        "event_id": uuid4(),
        "event_type": "tool.execute",
        "occurred_at": datetime.now(timezone.utc),
        "session_id": "sess-1",
        "agent_id": "agent-1",
        "trace_id": "trace-1",
        "payload_ref": "test data",
    }
    defaults.update(overrides)
    return Event(**defaults)


class TestEventEndpoints:
    async def test_ingest_single_event(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.post("/events").mock(
            return_value=httpx.Response(200, json=make_ingest_response("evt-001"))
        )
        event = _sample_event()
        result = await client.ingest(event)
        assert isinstance(result, IngestResult)
        assert result.event_id == "evt-001"
        await client.close()

    async def test_ingest_batch(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.post("/events/batch").mock(
            return_value=httpx.Response(
                200,
                json={
                    "accepted": 2,
                    "rejected": 0,
                    "results": [
                        {"event_id": "e1", "global_position": "100-0"},
                        {"event_id": "e2", "global_position": "100-1"},
                    ],
                    "errors": [],
                },
            )
        )
        events = [_sample_event(), _sample_event()]
        result = await client.ingest_batch(events)
        assert isinstance(result, BatchResult)
        assert result.accepted == 2
        assert len(result.results) == 2
        await client.close()


class TestContextEndpoints:
    async def test_get_context(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/context/sess-1").mock(
            return_value=httpx.Response(200, json=make_atlas_response())
        )
        result = await client.get_context("sess-1")
        assert isinstance(result, AtlasResponse)
        await client.close()

    async def test_get_context_with_params(self, client: EngramClient, mock_api: respx.MockRouter):
        route = mock_api.get("/context/sess-1").mock(
            return_value=httpx.Response(200, json=make_atlas_response())
        )
        await client.get_context("sess-1", query="payments", max_nodes=50, max_depth=2)
        request = route.calls[0].request
        assert "query=payments" in str(request.url)
        assert "max_nodes=50" in str(request.url)
        assert "max_depth=2" in str(request.url)
        await client.close()


class TestSubgraphQuery:
    async def test_query_subgraph(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.post("/query/subgraph").mock(
            return_value=httpx.Response(200, json=make_atlas_response())
        )
        query = SubgraphQuery(query="test", session_id="s1", agent_id="a1")
        result = await client.query_subgraph(query)
        assert isinstance(result, AtlasResponse)
        await client.close()


class TestLineage:
    async def test_get_lineage(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/nodes/evt-1/lineage").mock(
            return_value=httpx.Response(200, json=make_atlas_response())
        )
        result = await client.get_lineage("evt-1")
        assert isinstance(result, AtlasResponse)
        await client.close()

    async def test_get_lineage_params(self, client: EngramClient, mock_api: respx.MockRouter):
        route = mock_api.get("/nodes/evt-1/lineage").mock(
            return_value=httpx.Response(200, json=make_atlas_response())
        )
        await client.get_lineage("evt-1", max_depth=5, intent="when", cursor="abc")
        request = route.calls[0].request
        assert "max_depth=5" in str(request.url)
        assert "intent=when" in str(request.url)
        assert "cursor=abc" in str(request.url)
        await client.close()


class TestEntityEndpoints:
    async def test_get_entity(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/entities/ent-1").mock(
            return_value=httpx.Response(
                200, json={"entity_id": "ent-1", "name": "Test", "entity_type": "concept"}
            )
        )
        result = await client.get_entity("ent-1")
        assert isinstance(result, EntityResponse)
        assert result.entity_id == "ent-1"
        assert result.name == "Test"
        assert result.entity_type == "concept"
        await client.close()

    async def test_get_entity_not_found(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/entities/missing").mock(
            return_value=httpx.Response(404, json={"detail": "not found"})
        )
        with pytest.raises(NotFoundError):
            await client.get_entity("missing")
        await client.close()


class TestUserEndpoints:
    async def test_get_user_profile(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/users/u1/profile").mock(
            return_value=httpx.Response(
                200, json={"profile_id": "p1", "user_id": "u1", "display_name": "Alice"}
            )
        )
        result = await client.get_user_profile("u1")
        assert isinstance(result, UserProfile)
        assert result.display_name == "Alice"
        await client.close()

    async def test_get_user_preferences(self, client: EngramClient, mock_api: respx.MockRouter):
        route = mock_api.get("/users/u1/preferences").mock(
            return_value=httpx.Response(
                200,
                json=[{"preference_id": "p1", "category": "ui", "key": "theme", "value": "dark"}],
            )
        )
        result = await client.get_user_preferences("u1", category="ui")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], PreferenceNode)
        assert result[0].category == "ui"
        assert result[0].key == "theme"
        request = route.calls[0].request
        assert "category=ui" in str(request.url)
        await client.close()

    async def test_get_user_skills(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/users/u1/skills").mock(
            return_value=httpx.Response(
                200,
                json=[{"skill_id": "s1", "name": "python", "level": "expert"}],
            )
        )
        result = await client.get_user_skills("u1")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], SkillNode)
        assert result[0].name == "python"
        await client.close()

    async def test_get_user_patterns(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/users/u1/patterns").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "pattern_id": "bp1",
                        "pattern_type": "temporal",
                        "description": "morning coder",
                    }
                ],
            )
        )
        result = await client.get_user_patterns("u1")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], BehavioralPatternNode)
        assert result[0].description == "morning coder"
        await client.close()

    async def test_get_user_interests(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/users/u1/interests").mock(
            return_value=httpx.Response(
                200,
                json=[{"entity_id": "e1", "name": "AI", "entity_type": "topic", "strength": 0.9}],
            )
        )
        result = await client.get_user_interests("u1")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], InterestNode)
        assert result[0].name == "AI"
        assert result[0].strength == 0.9
        await client.close()

    async def test_export_user_data(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/users/u1/data-export").mock(
            return_value=httpx.Response(200, json={"events": [], "entities": []})
        )
        result = await client.export_user_data("u1")
        assert isinstance(result, GDPRExportResponse)
        assert result.events == []
        assert result.entities == []
        await client.close()

    async def test_delete_user(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.delete("/users/u1").mock(
            return_value=httpx.Response(200, json={"deleted_nodes": 5, "deleted_edges": 10})
        )
        result = await client.delete_user("u1")
        assert isinstance(result, GDPRDeleteResponse)
        assert result.deleted_nodes == 5
        assert result.deleted_edges == 10
        await client.close()


class TestHealthAndAdmin:
    async def test_health(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/health").mock(
            return_value=httpx.Response(
                200,
                json={"status": "healthy", "redis": True, "neo4j": True, "version": "0.1.0"},
            )
        )
        result = await client.health()
        assert isinstance(result, HealthStatus)
        assert result.status == "healthy"
        await client.close()

    async def test_stats(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/admin/stats").mock(
            return_value=httpx.Response(
                200,
                json={
                    "nodes": {"Event": 100},
                    "edges": {"FOLLOWS": 50},
                    "total_nodes": 100,
                    "total_edges": 50,
                    "redis": {},
                },
            )
        )
        result = await client.stats()
        assert isinstance(result, StatsResponse)
        assert result.total_nodes == 100
        await client.close()

    async def test_reconsolidate(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.post("/admin/reconsolidate").mock(
            return_value=httpx.Response(200, json={"status": "started"})
        )
        result = await client.reconsolidate(session_id="sess-1")
        assert isinstance(result, ReconsolidateResponse)
        assert result.status == "started"
        await client.close()

    async def test_prune(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.post("/admin/prune").mock(
            return_value=httpx.Response(200, json={"pruned": 10, "dry_run": True})
        )
        result = await client.prune("cold", dry_run=True)
        assert isinstance(result, PruneResponse)
        assert result.pruned == 10
        assert result.dry_run is True
        await client.close()

    async def test_health_detailed(self, client: EngramClient, mock_api: respx.MockRouter):
        mock_api.get("/admin/health/detailed").mock(
            return_value=httpx.Response(200, json={"redis": {"connected": True}})
        )
        result = await client.health_detailed()
        assert isinstance(result, DetailedHealthResponse)
        assert result.redis == {"connected": True}
        await client.close()


class TestLifecycle:
    async def test_context_manager(self, mock_api: respx.MockRouter):
        config = EngramConfig(base_url="http://test:8000")
        mock_api.get("/health").mock(
            return_value=httpx.Response(
                200, json={"status": "healthy", "redis": True, "neo4j": True, "version": "0.1.0"}
            )
        )
        async with EngramClient(config=config) as client:
            result = await client.health()
            assert result.status == "healthy"

    def test_session_factory(self, client: EngramClient):
        sm = client.session("agent-1")
        # SessionManager is created via runtime import
        assert sm is not None
        assert hasattr(sm, "_agent_id")

    def test_paginate_context(self, client: EngramClient):
        pi = client.paginate_context("sess-1")
        assert hasattr(pi, "__aiter__")
        assert hasattr(pi, "__anext__")

    def test_paginate_lineage(self, client: EngramClient):
        pi = client.paginate_lineage("evt-1")
        assert hasattr(pi, "__aiter__")
        assert hasattr(pi, "__anext__")
