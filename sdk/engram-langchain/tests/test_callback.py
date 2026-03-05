"""Tests for the EngramCallbackHandler."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from engram_langchain.callback import EngramCallbackHandler, _safe_truncate


@pytest.fixture
def handler(mock_client: AsyncMock) -> EngramCallbackHandler:
    return EngramCallbackHandler(
        client=mock_client,
        session_id="test-session",
        agent_id="test-agent",
        trace_id="test-trace",
    )


class TestCallbackCapture:
    """Test that LangChain callbacks produce the correct Engram events."""

    def test_on_chain_start_creates_event(self, handler: EngramCallbackHandler) -> None:
        run_id = uuid.uuid4()
        handler.on_chain_start(
            serialized={"name": "TestChain", "id": ["langchain", "TestChain"]},
            inputs={"query": "hello"},
            run_id=run_id,
        )
        assert len(handler.buffered_events) == 1
        event = handler.buffered_events[0]
        assert event.event_type == "agent.invoke"
        assert event.event_id == run_id
        assert event.session_id == "test-session"
        assert event.agent_id == "test-agent"
        assert event.trace_id == "test-trace"
        assert "TestChain" in event.payload_ref
        assert event.payload is not None
        assert event.payload["chain_name"] == "TestChain"

    def test_on_chain_start_uses_id_fallback(self, handler: EngramCallbackHandler) -> None:
        run_id = uuid.uuid4()
        handler.on_chain_start(
            serialized={"id": ["langchain", "chains", "MyChain"]},
            inputs={},
            run_id=run_id,
        )
        event = handler.buffered_events[0]
        assert event.payload is not None
        assert event.payload["chain_name"] == "MyChain"

    def test_on_tool_start_creates_event(self, handler: EngramCallbackHandler) -> None:
        run_id = uuid.uuid4()
        handler.on_tool_start(
            serialized={"name": "web_search"},
            input_str="search for billing docs",
            run_id=run_id,
        )
        assert len(handler.buffered_events) == 1
        event = handler.buffered_events[0]
        assert event.event_type == "tool.execute"
        assert event.tool_name == "web_search"
        assert event.event_id == run_id

    def test_on_tool_end_creates_event_with_parent(self, handler: EngramCallbackHandler) -> None:
        parent_run_id = uuid.uuid4()
        handler.on_tool_end(
            output="Search results: ...",
            run_id=parent_run_id,
        )
        assert len(handler.buffered_events) == 1
        event = handler.buffered_events[0]
        assert event.event_type == "tool.result"
        assert event.parent_event_id == parent_run_id

    def test_on_llm_start_creates_event(self, handler: EngramCallbackHandler) -> None:
        run_id = uuid.uuid4()
        handler.on_llm_start(
            serialized={"name": "gpt-4"},
            prompts=["Hello, how are you?", "Tell me about billing"],
            run_id=run_id,
        )
        assert len(handler.buffered_events) == 1
        event = handler.buffered_events[0]
        assert event.event_type == "llm.invoke"
        assert event.payload is not None
        assert event.payload["model"] == "gpt-4"
        assert event.payload["prompt_count"] == 2

    def test_on_llm_end_creates_event(self, handler: EngramCallbackHandler) -> None:
        from langchain_core.outputs import Generation, LLMResult

        run_id = uuid.uuid4()
        llm_result = LLMResult(generations=[[Generation(text="Billing info here")]])
        handler.on_llm_end(response=llm_result, run_id=run_id)
        assert len(handler.buffered_events) == 1
        event = handler.buffered_events[0]
        assert event.event_type == "llm.result"
        assert event.parent_event_id == run_id
        assert event.payload is not None
        assert event.payload["generation_count"] == 1

    def test_parent_run_id_maps_to_parent_event_id(self, handler: EngramCallbackHandler) -> None:
        parent_id = uuid.uuid4()
        child_id = uuid.uuid4()
        handler.on_chain_start(serialized={"name": "Parent"}, inputs={}, run_id=parent_id)
        handler.on_tool_start(
            serialized={"name": "tool"},
            input_str="test",
            run_id=child_id,
            parent_run_id=parent_id,
        )
        assert handler.buffered_events[1].parent_event_id == parent_id

    def test_multiple_callbacks_buffer_all_events(self, handler: EngramCallbackHandler) -> None:
        handler.on_chain_start(serialized={"name": "A"}, inputs={}, run_id=uuid.uuid4())
        handler.on_tool_start(serialized={"name": "B"}, input_str="x", run_id=uuid.uuid4())
        handler.on_llm_start(serialized={"name": "C"}, prompts=["p"], run_id=uuid.uuid4())
        assert len(handler.buffered_events) == 3


class TestFlush:
    """Test the async flush mechanism."""

    @pytest.mark.asyncio
    async def test_flush_sends_batch(
        self, handler: EngramCallbackHandler, mock_client: AsyncMock
    ) -> None:
        handler.on_chain_start(serialized={"name": "Test"}, inputs={}, run_id=uuid.uuid4())
        handler.on_tool_start(serialized={"name": "tool"}, input_str="x", run_id=uuid.uuid4())
        flushed = await handler.flush()
        assert flushed == 2
        mock_client.ingest_batch.assert_awaited_once()
        call_args = mock_client.ingest_batch.call_args
        assert len(call_args[0][0]) == 2

    @pytest.mark.asyncio
    async def test_flush_clears_buffer(self, handler: EngramCallbackHandler) -> None:
        handler.on_chain_start(serialized={"name": "Test"}, inputs={}, run_id=uuid.uuid4())
        await handler.flush()
        assert len(handler.buffered_events) == 0

    @pytest.mark.asyncio
    async def test_flush_empty_buffer_returns_zero(
        self, handler: EngramCallbackHandler, mock_client: AsyncMock
    ) -> None:
        flushed = await handler.flush()
        assert flushed == 0
        mock_client.ingest_batch.assert_not_awaited()


class TestSafeTruncate:
    """Test the _safe_truncate helper."""

    def test_short_string_unchanged(self) -> None:
        assert _safe_truncate("hello") == "hello"

    def test_long_string_truncated(self) -> None:
        long_text = "x" * 3000
        result = _safe_truncate(long_text, max_length=100)
        assert len(result) < 200
        assert result.endswith("...[truncated]")

    def test_dict_values_truncated(self) -> None:
        data = {"key": "y" * 3000}
        result = _safe_truncate(data, max_length=100)
        assert isinstance(result, dict)
        assert result["key"].endswith("...[truncated]")

    def test_non_string_unchanged(self) -> None:
        assert _safe_truncate(42) == 42
        assert _safe_truncate(None) is None
