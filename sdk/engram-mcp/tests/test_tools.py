"""Tests for the 7 Engram MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock

from engram.models import (
    AtlasResponse,
    SubgraphQuery,
    UserProfile,
)
from engram_mcp.server import EngramMCPServer
from engram_mcp.tools import TOOL_DEFINITIONS
from tests.conftest import make_atlas_response


class TestListTools:
    """Test that list_tools returns the correct tool definitions."""

    async def test_list_tools_returns_7_tools(self, mcp_server: EngramMCPServer) -> None:
        """list_tools() returns 7 tools with correct names."""
        assert len(TOOL_DEFINITIONS) == 7

        expected_names = {
            "engram_record",
            "engram_recall",
            "engram_search",
            "engram_trace",
            "engram_profile",
            "engram_entities",
            "engram_forget",
        }
        actual_names = {t.name for t in TOOL_DEFINITIONS}
        assert actual_names == expected_names

    async def test_list_tools_schemas_have_required_fields(self) -> None:
        """Tools with required inputs have 'required' in their schema."""
        for tool in TOOL_DEFINITIONS:
            schema = tool.inputSchema
            assert "properties" in schema
            assert schema["type"] == "object"

        # Check specific required fields
        record_tool = next(t for t in TOOL_DEFINITIONS if t.name == "engram_record")
        assert "content" in record_tool.inputSchema["required"]

        search_tool = next(t for t in TOOL_DEFINITIONS if t.name == "engram_search")
        assert "query" in search_tool.inputSchema["required"]

        trace_tool = next(t for t in TOOL_DEFINITIONS if t.name == "engram_trace")
        assert "node_id" in trace_tool.inputSchema["required"]

        profile_tool = next(t for t in TOOL_DEFINITIONS if t.name == "engram_profile")
        assert "user_id" in profile_tool.inputSchema["required"]

        forget_tool = next(t for t in TOOL_DEFINITIONS if t.name == "engram_forget")
        assert "user_id" in forget_tool.inputSchema["required"]


class TestEngramRecord:
    """Test engram_record tool."""

    async def test_record_creates_and_ingests_event(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """record tool creates an event and ingests it via the client."""
        from engram_mcp.tools import _handle_record

        result = await _handle_record(mcp_server, {"content": "User asked about billing"})

        # Verify ingest was called
        mock_client.ingest.assert_called_once()
        event = mock_client.ingest.call_args[0][0]
        assert event.payload_ref == "User asked about billing"
        assert event.event_type == "observation.output"
        assert event.session_id == mcp_server.session_id
        assert event.trace_id == mcp_server.trace_id
        assert event.agent_id == mcp_server.agent_id

        # Verify response formatting
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Event Recorded" in result[0].text
        assert "Event ID" in result[0].text

    async def test_record_with_importance_and_metadata(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """record tool passes importance and metadata through to the event."""
        from engram_mcp.tools import _handle_record

        result = await _handle_record(
            mcp_server,
            {
                "content": "Critical error found",
                "event_type": "agent.invoke",
                "importance": 9,
                "metadata": {"error_code": "E500"},
            },
        )

        event = mock_client.ingest.call_args[0][0]
        assert event.event_type == "agent.invoke"
        assert event.importance_hint == 9
        assert event.payload == {"error_code": "E500"}

        assert "9/10" in result[0].text


class TestEngramRecall:
    """Test engram_recall tool."""

    async def test_recall_uses_default_session(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """recall uses the server's session_id when none is provided."""
        from engram_mcp.tools import _handle_recall

        mock_client.get_context.return_value = make_atlas_response(num_nodes=2)

        result = await _handle_recall(mcp_server, {})

        mock_client.get_context.assert_called_once_with(
            mcp_server.session_id, query=None, max_nodes=50
        )
        assert len(result) == 1
        assert "Session Context" in result[0].text

    async def test_recall_with_explicit_session(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """recall uses provided session_id instead of default."""
        from engram_mcp.tools import _handle_recall

        custom_session = "custom-session-123"
        mock_client.get_context.return_value = AtlasResponse()

        await _handle_recall(mcp_server, {"session_id": custom_session, "query": "billing"})

        mock_client.get_context.assert_called_once_with(
            custom_session, query="billing", max_nodes=50
        )


class TestEngramSearch:
    """Test engram_search tool."""

    async def test_search_calls_query_subgraph(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """search tool delegates to client.query_subgraph."""
        from engram_mcp.tools import _handle_search

        mock_client.query_subgraph.return_value = make_atlas_response(num_nodes=5)

        result = await _handle_search(mcp_server, {"query": "payment errors"})

        mock_client.query_subgraph.assert_called_once()
        query = mock_client.query_subgraph.call_args[0][0]
        assert isinstance(query, SubgraphQuery)
        assert query.query == "payment errors"
        assert query.session_id == mcp_server.session_id
        assert query.agent_id == mcp_server.agent_id

        assert "Search Results" in result[0].text
        assert "5 nodes" in result[0].text


class TestEngramTrace:
    """Test engram_trace tool."""

    async def test_trace_calls_get_lineage(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """trace tool delegates to client.get_lineage."""
        from engram_mcp.tools import _handle_trace

        mock_client.get_lineage.return_value = make_atlas_response(num_nodes=3)

        result = await _handle_trace(
            mcp_server, {"node_id": "evt-abc-123", "max_depth": 5, "intent": "when"}
        )

        mock_client.get_lineage.assert_called_once_with("evt-abc-123", max_depth=5, intent="when")
        assert "Lineage for evt-abc-123" in result[0].text


class TestEngramProfile:
    """Test engram_profile tool."""

    async def test_profile_fetches_all_user_data(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """profile tool fetches profile, preferences, skills, patterns, interests."""
        from engram_mcp.tools import _handle_profile

        mock_client.get_user_profile.return_value = UserProfile(
            user_id="user-1",
            display_name="Alice",
            timezone="America/New_York",
            technical_level="senior",
        )
        mock_client.get_user_preferences.return_value = [
            {"name": "theme", "value": "dark"},
        ]
        mock_client.get_user_skills.return_value = [
            {"name": "Python", "level": "expert"},
        ]
        mock_client.get_user_patterns.return_value = [
            {"name": "morning-coder"},
        ]
        mock_client.get_user_interests.return_value = [
            {"name": "machine-learning"},
        ]

        result = await _handle_profile(mcp_server, {"user_id": "user-1"})

        text = result[0].text
        assert "User Profile: user-1" in text
        assert "Alice" in text
        assert "America/New_York" in text
        assert "senior" in text
        assert "theme" in text
        assert "dark" in text
        assert "Python" in text
        assert "expert" in text
        assert "morning-coder" in text
        assert "machine-learning" in text


class TestEngramForget:
    """Test engram_forget tool."""

    async def test_forget_calls_delete_user(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """forget tool delegates to client.delete_user."""
        from engram_mcp.tools import _handle_forget

        mock_client.delete_user.return_value = {"deleted_count": 12}

        result = await _handle_forget(mcp_server, {"user_id": "user-42"})

        mock_client.delete_user.assert_called_once_with("user-42")
        assert "GDPR Deletion Complete" in result[0].text
        assert "user-42" in result[0].text
        assert "12" in result[0].text


class TestEventChaining:
    """Test that consecutive records chain parent_event_id."""

    async def test_consecutive_records_chain_parent_event_id(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """Each record should set parent_event_id to the previous event."""
        from engram_mcp.tools import _handle_record

        # First event has no parent
        assert mcp_server.last_event_id is None
        await _handle_record(mcp_server, {"content": "First event"})

        first_event = mock_client.ingest.call_args[0][0]
        assert first_event.parent_event_id is None
        first_event_id = mcp_server.last_event_id
        assert first_event_id is not None

        # Second event has first as parent
        await _handle_record(mcp_server, {"content": "Second event"})

        second_event = mock_client.ingest.call_args[0][0]
        assert str(second_event.parent_event_id) == first_event_id

        # Third event has second as parent
        second_event_id = mcp_server.last_event_id
        await _handle_record(mcp_server, {"content": "Third event"})

        third_event = mock_client.ingest.call_args[0][0]
        assert str(third_event.parent_event_id) == second_event_id


class TestSessionManagement:
    """Test session_id consistency across records."""

    async def test_session_id_consistent_across_records(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """All records in one MCP connection share the same session_id."""
        from engram_mcp.tools import _handle_record

        session_id = mcp_server.session_id

        for i in range(5):
            await _handle_record(mcp_server, {"content": f"Event {i}"})

        # All 5 calls should use the same session_id
        for call_args in mock_client.ingest.call_args_list:
            event = call_args[0][0]
            assert event.session_id == session_id
            assert event.trace_id == mcp_server.trace_id
            assert event.agent_id == mcp_server.agent_id


class TestErrorHandling:
    """Test that tool handlers return error text instead of raising."""

    async def test_record_error_returns_text(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """record returns error text on ingest failure."""
        from engram_mcp.tools import _handle_record

        mock_client.ingest.side_effect = ConnectionError("server unavailable")

        result = await _handle_record(mcp_server, {"content": "test"})

        assert len(result) == 1
        assert "Error recording event" in result[0].text
        assert "ingestion failed" in result[0].text
        # last_event_id should NOT be updated on failure
        assert mcp_server.last_event_id is None

    async def test_recall_error_returns_text(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """recall returns error text on failure."""
        from engram_mcp.tools import _handle_recall

        mock_client.get_context.side_effect = ConnectionError("timeout")

        result = await _handle_recall(mcp_server, {})

        assert "Error retrieving context" in result[0].text

    async def test_search_error_returns_text(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """search returns error text on failure."""
        from engram_mcp.tools import _handle_search

        mock_client.query_subgraph.side_effect = ConnectionError("refused")

        result = await _handle_search(mcp_server, {"query": "test"})

        assert "Error searching" in result[0].text

    async def test_forget_error_returns_text(
        self, mcp_server: EngramMCPServer, mock_client: AsyncMock
    ) -> None:
        """forget returns error text on failure."""
        from engram_mcp.tools import _handle_forget

        mock_client.delete_user.side_effect = ConnectionError("unauthorized")

        result = await _handle_forget(mcp_server, {"user_id": "user-1"})

        assert "Error deleting user data" in result[0].text
