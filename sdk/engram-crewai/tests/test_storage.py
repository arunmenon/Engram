"""Tests for the EngramStorageBackend."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from engram.models import AtlasResponse
from engram_crewai.storage import EngramStorageBackend, _extract_content


class TestStorageBackendSave:
    """Test the save() method."""

    @pytest.mark.asyncio
    async def test_asave_creates_event(self, mock_client: AsyncMock) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend.agent_id = "test-agent"
        backend._scopes = set()
        backend._client = mock_client

        event_id = await backend.asave("Hello, world!", scope="session-1")
        assert event_id  # non-empty string
        mock_client.ingest.assert_awaited_once()
        event = mock_client.ingest.call_args[0][0]
        assert event.event_type == "observation.output"
        assert event.payload_ref == "Hello, world!"
        assert event.session_id == "session-1"
        assert event.agent_id == "test-agent"
        assert event.payload is not None
        assert event.payload["content"] == "Hello, world!"

    @pytest.mark.asyncio
    async def test_asave_with_metadata(self, mock_client: AsyncMock) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend.agent_id = "test-agent"
        backend._scopes = set()
        backend._client = mock_client

        await backend.asave(
            "Deploy completed",
            metadata={"env": "production", "version": "1.2.3"},
            scope="deploy-scope",
        )
        event = mock_client.ingest.call_args[0][0]
        assert event.payload is not None
        assert event.payload["env"] == "production"
        assert event.payload["version"] == "1.2.3"
        assert event.payload["content"] == "Deploy completed"

    @pytest.mark.asyncio
    async def test_asave_tracks_scope(self, mock_client: AsyncMock) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend.agent_id = "test-agent"
        backend._scopes = set()
        backend._client = mock_client

        await backend.asave("x", scope="scope-a")
        await backend.asave("y", scope="scope-b")
        assert "scope-a" in backend._scopes
        assert "scope-b" in backend._scopes

    @pytest.mark.asyncio
    async def test_asave_default_scope(self, mock_client: AsyncMock) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend.agent_id = "test-agent"
        backend._scopes = set()
        backend._client = mock_client

        await backend.asave("data")
        event = mock_client.ingest.call_args[0][0]
        assert event.session_id == "default"


class TestStorageBackendSearch:
    """Test the search() method."""

    @pytest.mark.asyncio
    async def test_asearch_returns_results(
        self, mock_client: AsyncMock, sample_search_response: AtlasResponse
    ) -> None:
        mock_client.query_subgraph.return_value = sample_search_response
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend.agent_id = "test-agent"
        backend._scopes = set()
        backend._client = mock_client

        results = await backend.asearch("deploy pipeline", limit=5, scope="project-alpha")
        assert len(results) == 2

        mock_client.query_subgraph.assert_awaited_once()
        query = mock_client.query_subgraph.call_args[0][0]
        assert query.query == "deploy pipeline"
        assert query.max_nodes == 5
        assert query.session_id == "project-alpha"

    @pytest.mark.asyncio
    async def test_asearch_result_structure(
        self, mock_client: AsyncMock, sample_search_response: AtlasResponse
    ) -> None:
        mock_client.query_subgraph.return_value = sample_search_response
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend.agent_id = "test-agent"
        backend._scopes = set()
        backend._client = mock_client

        results = await backend.asearch("deploy")
        for result in results:
            assert "id" in result
            assert "content" in result
            assert "score" in result
            assert "metadata" in result
            assert "node_type" in result["metadata"]

    @pytest.mark.asyncio
    async def test_asearch_empty_results(self, mock_client: AsyncMock) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend.agent_id = "test-agent"
        backend._scopes = set()
        backend._client = mock_client

        results = await backend.asearch("nonexistent")
        assert results == []


class TestStorageBackendDelete:
    """Test the delete() method."""

    def test_delete_returns_false(self) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        assert backend.delete("any-id") is False

    def test_delete_always_false(self) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        assert backend.delete("evt-001") is False
        assert backend.delete("evt-002") is False


class TestStorageBackendListScopes:
    """Test the list_scopes() method."""

    def test_list_scopes_empty(self) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend._scopes = set()
        assert backend.list_scopes() == []

    def test_list_scopes_sorted(self) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend._scopes = {"zebra", "alpha", "mid"}
        assert backend.list_scopes() == ["alpha", "mid", "zebra"]

    @pytest.mark.asyncio
    async def test_scopes_populated_by_save(self, mock_client: AsyncMock) -> None:
        backend = EngramStorageBackend.__new__(EngramStorageBackend)
        backend.agent_id = "test-agent"
        backend._scopes = set()
        backend._client = mock_client

        await backend.asave("a", scope="scope-x")
        await backend.asave("b", scope="scope-y")
        assert backend.list_scopes() == ["scope-x", "scope-y"]


class TestExtractContent:
    """Test _extract_content helper."""

    def test_extracts_content_key(self) -> None:
        from engram.models import AtlasNode

        node = AtlasNode(node_id="n1", node_type="Event", attributes={"content": "hello"})
        assert _extract_content(node) == "hello"

    def test_extracts_payload_ref(self) -> None:
        from engram.models import AtlasNode

        node = AtlasNode(node_id="n1", node_type="Event", attributes={"payload_ref": "data"})
        assert _extract_content(node) == "data"

    def test_empty_attributes(self) -> None:
        from engram.models import AtlasNode

        node = AtlasNode(node_id="n1", node_type="Entity", attributes={})
        assert _extract_content(node) == "[Entity:n1]"
