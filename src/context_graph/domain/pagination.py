"""Cursor-based pagination utilities.

Encodes/decodes opaque cursors for paginated graph queries.
Cursors encode (occurred_at, event_id) pairs as URL-safe base64.
"""

from __future__ import annotations

import base64


def encode_cursor(occurred_at: str, event_id: str) -> str:
    """Encode a pagination cursor from timestamp and event ID."""
    raw = f"{occurred_at}|{event_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, str]:
    """Decode a pagination cursor into (occurred_at, event_id).

    Raises ValueError on malformed or invalid cursors.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    except Exception as exc:
        msg = f"Invalid cursor: {cursor}"
        raise ValueError(msg) from exc

    parts = raw.split("|", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        msg = f"Invalid cursor format: {cursor}"
        raise ValueError(msg)

    return parts[0], parts[1]
