"""Search text and query terms for the keyword channel (domain/keyword_search.py)."""

from __future__ import annotations

from context_graph.domain.keyword_search import event_search_text, query_terms
from tests.fixtures.events import make_event


class TestQueryTerms:
    def test_drops_stopwords_short_tokens_and_repeats(self) -> None:
        assert query_terms("Why did the payment for card 4242 fail? Payment, a card!", 16) == [
            "payment",
            "card",
            "4242",
            "fail",
        ]

    def test_caps_terms(self) -> None:
        assert query_terms("alpha beta gamma delta", 2) == ["alpha", "beta"]

    def test_nothing_to_search(self) -> None:
        assert query_terms("what is it?", 16) == []
        assert query_terms("", 16) == []


class TestEventSearchText:
    def test_tool_name_then_preferred_keys_then_the_rest(self) -> None:
        event = make_event(tool_name="web_search")
        payload = {
            "meta": {"source": "browser"},
            "output": ["first result", {"title": "second result"}],
            "input": {"query": "spanner pricing", "max": 5},
            "content": "look up prices",
        }
        assert event_search_text(event, payload, 1000) == (
            "web_search look up prices spanner pricing first result second result browser"
        )

    def test_no_text(self) -> None:
        assert event_search_text(make_event(), None, 1000) == ""
        assert event_search_text(make_event(), {"count": 3, "ok": True}, 1000) == ""

    def test_truncates_on_a_word_boundary(self) -> None:
        text = event_search_text(make_event(), {"content": "alpha beta gamma"}, 12)
        assert text == "alpha beta"
