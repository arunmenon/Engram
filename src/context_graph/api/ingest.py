"""Shared request handling for event ingestion (``api/routes/events.py``).

- ``read_body``: the request body, bounded in size and time, with
  ``Content-Encoding: gzip`` undone (the decoded size is bounded too);
- ``check_events``: raw items validated as events, each one's payload, and
  per-item errors in the batch response's shape.

Source: ADR-0004, ADR-0010; review of 2026-10-05 (findings 3.8, N4)
"""

from __future__ import annotations

import asyncio
import zlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError as PydanticValidationError

from context_graph.domain.models import Event
from context_graph.domain.validation import validate_event

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request

# zlib window bits for the gzip format
_GZIP = 16 + zlib.MAX_WBITS


class BodyError(Exception):
    """The body cannot be read: ``status`` is the HTTP status to answer with."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


async def read_body(request: Request, limit: int, timeout_s: float) -> bytes:
    """The body, at most ``limit`` bytes sent and ``limit`` bytes decoded, within ``timeout_s``."""
    encoding = request.headers.get("content-encoding", "identity").strip().lower()
    if encoding not in ("identity", "gzip"):
        raise BodyError(415, f"Content-Encoding {encoding!r} is not supported (use gzip)")
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise BodyError(413, f"body exceeds {limit} bytes")
    try:
        async with asyncio.timeout(timeout_s):
            raw = await _read_raw(request, limit)
    except TimeoutError as exc:
        raise BodyError(408, f"body not received within {timeout_s} s") from exc
    if encoding == "identity":
        return raw
    decompressor = zlib.decompressobj(_GZIP)
    try:
        decoded = decompressor.decompress(raw, limit + 1)
    except zlib.error as exc:
        raise BodyError(400, f"body is not valid gzip: {exc}") from exc
    if len(decoded) > limit or decompressor.unconsumed_tail:
        raise BodyError(413, f"decompressed body exceeds {limit} bytes")
    if not decompressor.eof:
        raise BodyError(400, "body is an incomplete gzip stream")
    if decompressor.unused_data:
        raise BodyError(400, "body contains data after the gzip stream")
    return decoded


async def _read_raw(request: Request, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise BodyError(413, f"body exceeds {limit} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


@dataclass
class CheckedEvents:
    """Raw items split into valid events (with their payloads and input indexes) and errors."""

    events: list[Event] = field(default_factory=list)
    payloads: list[dict[str, Any] | None] = field(default_factory=list)
    indexes: list[int] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


_RESERVED_ACCEPTANCE = frozenset(
    {
        "acceptance",
        "admission_context",
        "envelope_version",
        "tenant_id",
        "database_resource",
        "binding_id",
        "accepted_epoch",
        "bundle_digest",
        "engine_revision",
        "source_id",
        "source_identity",
        "request_digest",
        "search_text",
        "summary",
        "keywords",
    }
)


def input_contract_errors(raw: dict[str, Any]) -> list[dict[str, str]]:
    """Reject ignored authority fields and payloads that would otherwise be lost."""
    errors = [
        {"field": key, "message": "This field is assigned by the server"}
        for key in sorted(_RESERVED_ACCEPTANCE.intersection(raw))
    ]
    if raw.get("global_position") is not None:
        errors.append({"field": "global_position", "message": "Position is assigned by the server"})
    if raw.get("payload") is not None and not isinstance(raw["payload"], dict):
        errors.append({"field": "payload", "message": "Payload must be a JSON object or null"})
    return errors


def check_events(
    raw_events: list[Any], refuse: Callable[[Event], tuple[str, str] | None]
) -> CheckedEvents:
    """Validate each raw item; ``refuse`` gives (field, reason) for an event to refuse.

    Each error: ``{"index", "event_id", "errors": [{"field", "message"}]}``.
    """
    checked = CheckedEvents()
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            checked.errors.append(
                {
                    "index": index,
                    "event_id": None,
                    "errors": [{"field": "", "message": "an event must be a JSON object"}],
                }
            )
            continue
        if problems := input_contract_errors(raw):
            event_id = raw.get("event_id")
            checked.errors.append(
                {
                    "index": index,
                    "event_id": event_id if isinstance(event_id, str) else None,
                    "errors": problems,
                }
            )
            continue
        raw_payload = raw.get("payload")
        payload = raw_payload if isinstance(raw_payload, dict) else None
        try:
            event = Event.model_validate(raw, strict=False)
        except PydanticValidationError as exc:
            event_id = raw.get("event_id")
            checked.errors.append(
                {
                    "index": index,
                    "event_id": event_id if isinstance(event_id, str) else None,
                    "errors": [
                        {
                            "field": ".".join(str(part) for part in err["loc"]),
                            "message": err["msg"],
                        }
                        for err in exc.errors()
                    ],
                }
            )
            continue
        result = validate_event(event)
        problems = [{"field": e.field, "message": e.message} for e in result.errors]
        refused = refuse(event) if result.is_valid else None
        if refused is not None:
            problems.append({"field": refused[0], "message": refused[1]})
        if problems:
            checked.errors.append(
                {"index": index, "event_id": str(event.event_id), "errors": problems}
            )
            continue
        checked.events.append(event)
        checked.payloads.append(payload)
        checked.indexes.append(index)
    return checked
