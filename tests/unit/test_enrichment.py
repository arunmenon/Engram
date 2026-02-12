"""Unit tests for the enrichment consumer's keyword extraction logic."""

from __future__ import annotations

from context_graph.worker.enrichment import extract_keywords


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
