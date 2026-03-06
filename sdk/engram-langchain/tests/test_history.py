"""Tests for the EngramChatMessageHistory."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from engram.models import (
    AtlasNode,
    AtlasResponse,
    Pagination,
    Provenance,
    QueryMeta,
)
from engram_langchain.history import (
    EngramChatMessageHistory,
    _message_type_to_event_type,
    _node_to_message,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


@pytest.fixture
def history(mock_client: AsyncMock) -> EngramChatMessageHistory:
    return EngramChatMessageHistory(
        client=mock_client,
        session_id="test-session",
        agent_id="test-agent",
        trace_id="test-trace",
    )


class TestHistory:
    """Test the EngramChatMessageHistory."""

    def test_sync_messages_raises_not_implemented(self, history: EngramChatMessageHistory) -> None:
        with pytest.raises(NotImplementedError, match="async"):
            _ = history.messages

    def test_sync_add_message_raises_not_implemented(
        self, history: EngramChatMessageHistory
    ) -> None:
        with pytest.raises(NotImplementedError, match="async"):
            history.add_message(HumanMessage(content="hello"))

    def test_clear_is_noop(self, history: EngramChatMessageHistory) -> None:
        history.clear()

    @pytest.mark.asyncio
    async def test_aclear_is_noop(self, history: EngramChatMessageHistory) -> None:
        await history.aclear()

    @pytest.mark.asyncio
    async def test_aget_messages_queries_context(
        self, history: EngramChatMessageHistory, mock_client: AsyncMock
    ) -> None:
        mock_client.get_context.return_value = AtlasResponse(
            nodes={
                "e1": AtlasNode(
                    node_id="e1",
                    node_type="Event",
                    attributes={"content": "Hello", "role": "human"},
                    provenance=Provenance(
                        event_id="e1",
                        global_position="100-0",
                        source="redis",
                        occurred_at=datetime(2024, 1, 1, tzinfo=UTC),
                        session_id="test-session",
                        agent_id="test-agent",
                        trace_id="test-trace",
                    ),
                ),
                "e2": AtlasNode(
                    node_id="e2",
                    node_type="Event",
                    attributes={"content": "Hi there!", "role": "ai"},
                    provenance=Provenance(
                        event_id="e2",
                        global_position="101-0",
                        source="redis",
                        occurred_at=datetime(2024, 1, 1, 0, 0, 1, tzinfo=UTC),
                        session_id="test-session",
                        agent_id="test-agent",
                        trace_id="test-trace",
                    ),
                ),
            },
            edges=[],
            pagination=Pagination(),
            meta=QueryMeta(),
        )
        messages = await history.aget_messages()
        assert len(messages) == 2
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "Hello"
        assert isinstance(messages[1], AIMessage)
        assert messages[1].content == "Hi there!"

    @pytest.mark.asyncio
    async def test_aadd_messages_ingests_events(
        self, history: EngramChatMessageHistory, mock_client: AsyncMock
    ) -> None:
        msgs = [
            HumanMessage(content="What is billing?"),
            AIMessage(content="Billing is the process of..."),
        ]
        await history.aadd_messages(msgs)
        mock_client.ingest_batch.assert_awaited_once()
        events = mock_client.ingest_batch.call_args[0][0]
        assert len(events) == 2
        assert events[0].event_type == "chat.human"
        assert events[0].payload_ref == "What is billing?"
        assert events[1].event_type == "chat.ai"

    @pytest.mark.asyncio
    async def test_aadd_messages_empty_list(
        self, history: EngramChatMessageHistory, mock_client: AsyncMock
    ) -> None:
        await history.aadd_messages([])
        mock_client.ingest_batch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_aget_messages_empty_session(
        self, history: EngramChatMessageHistory, mock_client: AsyncMock
    ) -> None:
        messages = await history.aget_messages()
        assert messages == []


class TestNodeToMessage:
    """Test _node_to_message conversion."""

    def test_human_role(self) -> None:
        node = AtlasNode(
            node_id="n1",
            node_type="Event",
            attributes={"content": "hello", "role": "human"},
        )
        msg = _node_to_message(node)
        assert isinstance(msg, HumanMessage)
        assert msg.content == "hello"

    def test_ai_role(self) -> None:
        node = AtlasNode(
            node_id="n1",
            node_type="Event",
            attributes={"content": "response", "role": "ai"},
        )
        msg = _node_to_message(node)
        assert isinstance(msg, AIMessage)

    def test_system_role(self) -> None:
        node = AtlasNode(
            node_id="n1",
            node_type="Event",
            attributes={"content": "system prompt", "role": "system"},
        )
        msg = _node_to_message(node)
        assert isinstance(msg, SystemMessage)

    def test_no_content_no_role_returns_none(self) -> None:
        node = AtlasNode(
            node_id="n1",
            node_type="Event",
            attributes={"other": "data"},
        )
        msg = _node_to_message(node)
        assert msg is None

    def test_content_without_role_defaults_to_human(self) -> None:
        node = AtlasNode(
            node_id="n1",
            node_type="Event",
            attributes={"content": "some text"},
        )
        msg = _node_to_message(node)
        assert isinstance(msg, HumanMessage)


class TestMessageTypeMapping:
    """Test _message_type_to_event_type."""

    def test_human_maps_to_chat_human(self) -> None:
        assert _message_type_to_event_type(HumanMessage(content="x")) == "chat.human"

    def test_ai_maps_to_chat_ai(self) -> None:
        assert _message_type_to_event_type(AIMessage(content="x")) == "chat.ai"

    def test_system_maps_to_chat_system(self) -> None:
        assert _message_type_to_event_type(SystemMessage(content="x")) == "chat.system"
