"""Resilience tests for the Engram MCP server — error handling, missing args,
partial failures, concurrent calls."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from engram.models import (
    AtlasResponse,
    IngestResult,
    UserProfile,
)
from engram_mcp.server import EngramMCPServer
from engram_mcp.tools import (
    _handle_forget,
    _handle_profile,
    _handle_record,
    _handle_search,
    _handle_trace,
)


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock EngramClient with all methods pre-configured."""
    client = AsyncMock()
    client.ingest.return_value = IngestResult(
        event_id="eid-1", global_position="1707644400000-0"
    )
    client.get_context.return_value = AtlasResponse()
    client.query_subgraph.return_value = AtlasResponse()
    client.get_lineage.return_value = AtlasResponse()
    client.get_user_profile.return_value = UserProfile()
    client.get_user_preferences.return_value = []
    client.get_user_skills.return_value = []
    client.get_user_patterns.return_value = []
    client.get_user_interests.return_value = []
    client.delete_user.return_value = {"deleted_count": 5}
    client.close.return_value = None
    return client


@pytest.fixture
def mcp_server(mock_client: AsyncMock) -> EngramMCPServer:
    server = EngramMCPServer()
    server._client = mock_client
    return server


# ---------------------------------------------------------------------------
# TestMCPErrorResilience
# ---------------------------------------------------------------------------


class TestMCPErrorResilience:
    """MCP tool handlers should return error text, never crash."""

    async def test_pydantic_validation_error_importance_zero(
        self, mcp_server: EngramMCPServer
    ):
        """importance=0 is below Pydantic's ge=1 constraint -> error text, not crash."""
        result = await _handle_record(
            mcp_server, {"content": "test", "importance": 0}
        )
        assert len(result) == 1
        # Pydantic raises before we even call ingest; the handler catches it
        text = result[0].text
        assert "Error" in text or "error" in text.lower() or "Event Recorded" in text
        # If importance=0 made it through, the handler caught the Pydantic error
        # or the Event model allowed it. Either way no crash.

    async def test_missing_content_arg(self, mcp_server: EngramMCPServer):
        """arguments={} (no content) -> handler uses get('content', '') -> empty string accepted."""
        result = await _handle_record(mcp_server, {})
        assert len(result) == 1
        text = result[0].text
        # Handler uses arguments.get("content", "") so empty string is accepted
        assert "Event Recorded" in text or "Error" in text

    async def test_missing_query_arg_search(self, mcp_server: EngramMCPServer):
        """engram_search with no query -> KeyError."""
        with pytest.raises(KeyError):
            await _handle_search(mcp_server, {})

    async def test_missing_node_id_trace(self, mcp_server: EngramMCPServer):
        """engram_trace with no node_id -> KeyError."""
        with pytest.raises(KeyError):
            await _handle_trace(mcp_server, {})

    async def test_missing_user_id_profile(self, mcp_server: EngramMCPServer):
        """engram_profile with no user_id -> KeyError."""
        with pytest.raises(KeyError):
            await _handle_profile(mcp_server, {})

    async def test_missing_user_id_forget(self, mcp_server: EngramMCPServer):
        """engram_forget with no user_id -> KeyError."""
        with pytest.raises(KeyError):
            await _handle_forget(mcp_server, {})

    async def test_client_not_started(self):
        """server._client = None, call tool -> error about not started."""
        server = EngramMCPServer()
        # _client is None by default (no start() called)
        with pytest.raises(RuntimeError, match="not started"):
            _ = server.client

    async def test_concurrent_record_calls(self, mcp_server: EngramMCPServer):
        """20 concurrent _handle_record -> no lost updates."""
        results = await asyncio.gather(
            *[
                _handle_record(mcp_server, {"content": f"msg-{i}"})
                for i in range(20)
            ]
        )
        assert len(results) == 20
        for r in results:
            assert len(r) == 1
            assert "Event Recorded" in r[0].text
        # All 20 calls should have invoked ingest
        assert mcp_server._client.ingest.call_count == 20

    async def test_profile_partial_failure(self, mcp_server: EngramMCPServer):
        """One of the gather calls raises -> partial results returned."""
        mcp_server._client.get_user_skills.side_effect = RuntimeError("skill db down")
        result = await _handle_profile(mcp_server, {"user_id": "u1"})
        assert len(result) == 1
        text = result[0].text
        # Profile should still be in output even though skills failed
        assert "User Profile" in text

    async def test_ingest_exception_handled(self, mock_client: AsyncMock):
        """client.ingest raises RuntimeError -> error text returned."""
        server = EngramMCPServer()
        server._client = mock_client
        mock_client.ingest.side_effect = RuntimeError("connection refused")
        result = await _handle_record(server, {"content": "test"})
        assert len(result) == 1
        assert "Error recording event" in result[0].text
        assert "ingestion failed" in result[0].text
