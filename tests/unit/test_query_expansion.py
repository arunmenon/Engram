"""Tests for HyDE query expansion (L6)."""

from __future__ import annotations

from context_graph.domain.query_expansion import (
    build_hyde_prompt,
    combine_query_with_hyde,
    expand_query,
)


class TestBuildHydePrompt:
    def test_contains_query(self) -> None:
        prompt = build_hyde_prompt("Why did the payment fail?")
        assert "Why did the payment fail?" in prompt

    def test_format_has_passage_marker(self) -> None:
        prompt = build_hyde_prompt("some query")
        assert prompt.endswith("Passage:")

    def test_instructs_short_passage(self) -> None:
        prompt = build_hyde_prompt("test")
        assert "2-3 sentences" in prompt


class TestCombineQueryWithHyde:
    def test_combines_query_and_doc(self) -> None:
        result = combine_query_with_hyde("my query", "hypothetical answer")
        assert "my query" in result
        assert "hypothetical answer" in result

    def test_empty_hyde_returns_original(self) -> None:
        assert combine_query_with_hyde("my query", "") == "my query"

    def test_whitespace_hyde_returns_original(self) -> None:
        assert combine_query_with_hyde("my query", "   ") == "my query"

    def test_strips_whitespace_from_hyde(self) -> None:
        result = combine_query_with_hyde("q", "  answer  ")
        assert result == "q\n\nanswer"


class TestExpandQuery:
    def test_no_hyde_returns_original(self) -> None:
        assert expand_query("my query") == "my query"

    def test_none_hyde_returns_original(self) -> None:
        assert expand_query("my query", hypothetical_doc=None) == "my query"

    def test_with_hyde_combines(self) -> None:
        result = expand_query("my query", hypothetical_doc="doc text")
        assert "my query" in result
        assert "doc text" in result

    def test_preserves_original_when_no_doc(self) -> None:
        original = "What tools were used in session abc?"
        assert expand_query(original) == original
