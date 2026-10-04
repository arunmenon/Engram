"""Text for the keyword (BM25) retrieval channel.

Two halves, shared by every event-log backend so they index and query
alike:

- ``event_search_text`` builds an event's searchable text at ingest from
  what the event already carries: the tool name and the string values of
  its payload (message ``content``, tool ``input`` and ``output`` first).
  It is computed once, when the event is written, so the ledger is never
  changed afterwards (ADR-0004).
- ``query_terms`` turns a natural-language query into the terms to look
  up. Backends match documents containing *any* term and rank by
  relevance; requiring every word of a question ("why did the payment
  fail?") to appear would almost never match.

Pure Python; no framework or storage imports.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context_graph.domain.models import Event

# Payload keys whose text is most telling, taken before any other values
PREFERRED_PAYLOAD_KEYS = ("content", "input", "output")

# RediSearch's default stopword list, plus question words, pronouns and
# auxiliaries that natural-language queries carry but say nothing about
# the events being looked for.
STOPWORDS = frozenset(
    {
        # RediSearch defaults
        "a", "is", "the", "an", "and", "are", "as", "at", "be", "but", "by",
        "for", "if", "in", "into", "it", "no", "not", "of", "on", "or", "such",
        "that", "their", "then", "there", "these", "they", "this", "to", "was",
        "will", "with",
        # Question words and auxiliaries
        "what", "why", "when", "where", "which", "who", "whom", "whose", "how",
        "do", "does", "did", "done", "can", "could", "should", "would", "has",
        "have", "had", "been", "being", "were", "am", "about", "any", "some",
        "from", "so", "than", "too", "very", "just", "also", "all",
        # Pronouns
        "i", "me", "my", "we", "us", "our", "you", "your", "he", "him", "his",
        "she", "her", "its", "them", "those",
    }
)  # fmt: skip

_TERM = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens (letters, digits and underscore), in order."""
    return [token.lower() for token in _TERM.findall(text)]


def query_terms(text: str, max_terms: int) -> list[str]:
    """Distinct, meaningful terms of a query, in first-seen order.

    Stopwords and single characters are dropped; at most ``max_terms`` are
    kept. An empty list means there is nothing to search for.
    """
    terms: list[str] = []
    for token in tokenize(text):
        if len(token) < 2 or token in STOPWORDS or token in terms:
            continue
        terms.append(token)
        if len(terms) >= max_terms:
            break
    return terms


def _string_values(value: Any, out: list[str]) -> None:
    if isinstance(value, str):
        if value.strip():
            out.append(value.strip())
    elif isinstance(value, dict):
        for item in value.values():
            _string_values(item, out)
    elif isinstance(value, list | tuple):
        for item in value:
            _string_values(item, out)


def event_search_text(event: Event, payload: dict[str, Any] | None, max_chars: int) -> str:
    """The searchable text for an event, at most ``max_chars`` long.

    Returns an empty string when the event carries no text.
    """
    parts: list[str] = []
    if event.tool_name:
        parts.append(event.tool_name)
    if payload:
        for key in PREFERRED_PAYLOAD_KEYS:
            _string_values(payload.get(key), parts)
        for key, value in payload.items():
            if key not in PREFERRED_PAYLOAD_KEYS:
                _string_values(value, parts)
    text = " ".join(parts)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # Do not index half a word
    boundary = cut.rfind(" ")
    return cut[:boundary] if boundary > 0 else cut
