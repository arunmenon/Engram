"""Unit tests for cursor-based pagination utilities."""

from __future__ import annotations

import base64

import pytest

from context_graph.domain.pagination import decode_cursor, encode_cursor


def test_encode_decode_roundtrip() -> None:
    """Cursor should survive an encode/decode round-trip."""
    cursor = encode_cursor("2024-01-15T10:30:00Z", "abc-123")
    ts, eid = decode_cursor(cursor)
    assert ts == "2024-01-15T10:30:00Z"
    assert eid == "abc-123"


def test_decode_invalid_base64() -> None:
    """Non-base64 input should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid cursor"):
        decode_cursor("not-valid-base64!!!")


def test_decode_malformed_cursor_no_pipe() -> None:
    """Base64-valid but no pipe separator should raise ValueError."""
    bad = base64.urlsafe_b64encode(b"no-pipe-here").decode()
    with pytest.raises(ValueError, match="Invalid cursor"):
        decode_cursor(bad)


def test_decode_empty_parts() -> None:
    """Base64 with pipe but empty first part should raise ValueError."""
    bad = base64.urlsafe_b64encode(b"|some-id").decode()
    with pytest.raises(ValueError, match="Invalid cursor"):
        decode_cursor(bad)


def test_encode_simple_values() -> None:
    """Simple values should roundtrip correctly."""
    cursor = encode_cursor("ts", "id")
    assert decode_cursor(cursor) == ("ts", "id")


def test_cursor_contains_pipe_in_event_id() -> None:
    """Event IDs containing pipe should be preserved (split on first pipe only)."""
    cursor = encode_cursor("2024-01-01T00:00:00Z", "id|with|pipes")
    ts, eid = decode_cursor(cursor)
    assert ts == "2024-01-01T00:00:00Z"
    assert eid == "id|with|pipes"
