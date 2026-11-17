"""Reject ambiguous timestamps and incomplete compressed bodies before append."""

import gzip
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from context_graph.api.ingest import BodyError, read_body
from context_graph.domain.models import Event


def envelope(**changes):
    return dict(
        event_id=uuid4(),
        event_type="observation.input",
        occurred_at=datetime.now(UTC),
        session_id="time-test",
        agent_id="test",
        trace_id="trace",
        payload_ref="fixture",
        **changes,
    )


@pytest.mark.parametrize("field", ["occurred_at", "ended_at"])
def test_event_refuses_naive_timestamp(field):
    values = envelope()
    values[field] = datetime(2026, 10, 6)
    with pytest.raises(ValidationError, match="timezone"):
        Event(**values)


def test_offset_timestamps_normalize_to_utc():
    offset = timezone(timedelta(hours=5, minutes=30))
    values = envelope()
    values["occurred_at"] = datetime(2026, 10, 6, 12, tzinfo=offset)
    values["ended_at"] = datetime(2026, 10, 6, 12, 1, tzinfo=offset)
    event = Event(**values)
    assert event.occurred_at == datetime(2026, 10, 6, 6, 30, tzinfo=UTC)
    assert event.occurred_at.tzinfo is UTC and event.ended_at.tzinfo is UTC


def request(body):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request({"type": "http", "headers": [(b"content-encoding", b"gzip")]}, receive)


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_bytes", [1, 4, 8])
async def test_truncated_gzip_trailer_is_rejected(missing_bytes):
    encoded = gzip.compress(b'{"valid_json":true}')
    with pytest.raises(BodyError) as exc:
        await read_body(request(encoded[:-missing_bytes]), 1000, 1)
    assert exc.value.status == 400


@pytest.mark.asyncio
async def test_complete_gzip_is_accepted_but_trailing_data_is_not():
    body = b'{"valid_json":true}'
    encoded = gzip.compress(body)
    assert await read_body(request(encoded), 1000, 1) == body
    with pytest.raises(BodyError) as exc:
        await read_body(request(encoded + b"ignored"), 1000, 1)
    assert exc.value.status == 400
