"""Unit tests for the enrichment consumer's keyword extraction and embedding logic."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.worker.enrichment import build_event_text, extract_keywords


class TestExtractKeywords:
    def test_keyword_extraction_from_event_type(self) -> None:
        """Split event_type by '.' to get keywords."""
        result = extract_keywords("tool.execute")
        assert result == ["tool", "execute"]

    def test_keyword_extraction_with_tool_name(self) -> None:
        """tool_name is appended if not already in parts."""
        result = extract_keywords("tool.execute", tool_name="web_search")
        assert result == ["tool", "execute", "web_search"]

    def test_keyword_extraction_tool_name_dedup(self) -> None:
        """tool_name that matches a part is not duplicated."""
        result = extract_keywords("tool.execute", tool_name="tool")
        assert result == ["tool", "execute"]

    def test_keyword_extraction_agent_invoke(self) -> None:
        result = extract_keywords("agent.invoke")
        assert result == ["agent", "invoke"]

    def test_keyword_extraction_llm_chat(self) -> None:
        result = extract_keywords("llm.chat")
        assert result == ["llm", "chat"]

    def test_keyword_extraction_deep_hierarchy(self) -> None:
        result = extract_keywords("user.preference.stated")
        assert result == ["user", "preference", "stated"]

    def test_keyword_extraction_empty_string(self) -> None:
        result = extract_keywords("")
        assert result == []

    def test_keyword_extraction_none_tool_name(self) -> None:
        result = extract_keywords("tool.execute", tool_name=None)
        assert result == ["tool", "execute"]


# ---------------------------------------------------------------------------
# Event text representation for embedding
# ---------------------------------------------------------------------------


class TestBuildEventText:
    def test_basic_event_type(self) -> None:
        """Event type with no tool or keywords."""
        result = build_event_text("tool.execute", None, ["tool", "execute"])
        assert result == "tool.execute tool execute"

    def test_with_tool_name(self) -> None:
        """Tool name should appear after event type."""
        result = build_event_text("tool.execute", "web_search", ["tool", "execute", "web_search"])
        assert result == "tool.execute web_search tool execute"

    def test_deduplicates_keywords(self) -> None:
        """Keywords already in parts are not duplicated."""
        result = build_event_text("tool.execute", "tool", ["tool", "execute"])
        assert result == "tool.execute tool execute"

    def test_empty_keywords(self) -> None:
        result = build_event_text("agent.invoke", None, [])
        assert result == "agent.invoke"


# ---------------------------------------------------------------------------
# Event embedding computation and storage
# ---------------------------------------------------------------------------


def _make_enrichment_consumer(
    embedding_service: Any = None,
) -> Any:
    """Create an EnrichmentConsumer with mocked dependencies."""
    from context_graph.worker.enrichment import EnrichmentConsumer

    redis_client = AsyncMock()
    graph_store = AsyncMock()
    settings = MagicMock()
    settings.redis.group_enrichment = "enrichment"
    settings.redis.global_stream = "events:__global__"
    settings.redis.block_timeout_ms = 100
    settings.redis.event_key_prefix = "evt:"
    return EnrichmentConsumer(
        redis_client=redis_client,
        graph_store=graph_store,
        settings=settings,
        embedding_service=embedding_service,
    )


class TestEventEmbeddingComputation:
    @pytest.mark.asyncio()
    async def test_embedding_computed_and_stored(self) -> None:
        """When embedding service is available, embedding is computed and stored."""
        embedding_service = AsyncMock()
        embedding_service.embed_text.return_value = [0.1, 0.2, 0.3]

        consumer = _make_enrichment_consumer(embedding_service=embedding_service)

        await consumer._compute_and_store_event_embedding(
            event_id="evt-1",
            event_type="tool.execute",
            doc={"tool_name": "web_search"},
        )

        embedding_service.embed_text.assert_called_once()
        consumer._graph_store.store_event_embedding.assert_called_once_with(
            "evt-1", [0.1, 0.2, 0.3]
        )

    @pytest.mark.asyncio()
    async def test_embedding_skipped_when_no_service(self) -> None:
        """No error when embedding_service is None."""
        consumer = _make_enrichment_consumer(embedding_service=None)

        # Should not raise
        await consumer._compute_and_store_event_embedding(
            event_id="evt-1",
            event_type="tool.execute",
            doc={},
        )

    @pytest.mark.asyncio()
    async def test_embedding_skipped_on_error(self) -> None:
        """When embedding service raises, the method degrades gracefully."""
        embedding_service = AsyncMock()
        embedding_service.embed_text.side_effect = RuntimeError("model failed")

        consumer = _make_enrichment_consumer(embedding_service=embedding_service)

        # Should not raise even though embed_text fails
        await consumer._compute_and_store_event_embedding(
            event_id="evt-1",
            event_type="tool.execute",
            doc={},
        )
