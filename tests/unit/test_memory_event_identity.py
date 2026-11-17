"""Memory batch outcomes distinguish an identical retry from changed ID reuse."""

from datetime import UTC, datetime, timedelta

import pytest

from context_graph.adapters.memory.log import MemoryEventLog
from tests.fixtures.events import make_event


@pytest.mark.asyncio
async def test_retry_conflict_and_valid_sibling_preserve_original_document():
    log = MemoryEventLog()
    event = make_event()
    sibling = make_event(session_id=event.session_id)
    first = await log.append_batch_outcomes([event], [{"a": 1, "b": 2}])
    outcomes = await log.append_batch_outcomes(
        [event, event, sibling], [{"b": 2, "a": 1}, {"a": 9, "b": 2}, {"a": 3}]
    )
    assert [r.status for r in outcomes] == ["duplicate", "conflict", "created"]
    assert outcomes[0].position == first[0].position
    assert outcomes[1].position is None
    assert await log.stream_length() == 2
    assert (await log.get_documents([str(event.event_id)]))[0]["payload"] == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_envelope_changes_conflict_within_batch_but_server_position_does_not():
    log = MemoryEventLog()
    event = make_event()
    changed = event.model_copy(update={"agent_id": "another-source"})
    positioned = event.model_copy(update={"global_position": "server-position"})
    outcomes = await log.append_batch_outcomes([event, changed, positioned])
    assert [r.status for r in outcomes] == ["created", "conflict", "duplicate"]
    assert await log.stream_length() == 1


@pytest.mark.asyncio
async def test_identity_survives_document_expiry_while_dedup_is_retained():
    now = datetime.now(UTC)
    log = MemoryEventLog(clock=lambda: now.timestamp())
    event = make_event(occurred_at=now - timedelta(days=3))
    await log.append(event, {"id": 42})
    await log.expire(1, None)
    assert (await log.get_documents([str(event.event_id)])) == [None]
    outcomes = await log.append_batch_outcomes([event, event], [{"id": 42}, {"id": 43}])
    assert [r.status for r in outcomes] == ["duplicate", "conflict"]
