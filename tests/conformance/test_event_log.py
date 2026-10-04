"""EventLog conformance suite (ADR-0019 §5).

Every EventLog backend must pass these. They pin the contract the
workers, the API and retention rely on: idempotent append, read-your-
writes, order within a session, search filters, keyword matching on the
indexed text fields, and hot-tier retention.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

from context_graph.domain.models import EventQuery
from tests.fixtures.events import make_event

if TYPE_CHECKING:
    from tests.conformance.conftest import LogHarness


def _session() -> str:
    return f"conf-session-{uuid4().hex[:8]}"


class _RecordingArchive:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.archived: list[dict[str, Any]] = []

    async def archive_events(self, events: list[dict[str, Any]], partition_key: str) -> str:
        if self.fail:
            msg = "archive unavailable"
            raise RuntimeError(msg)
        self.archived.extend(events)
        return f"archive/{partition_key}"

    async def list_archives(self, prefix: str | None = None, limit: int = 100) -> list[dict]:
        return []


class TestAppend:
    async def test_append_is_idempotent(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        event = make_event(session_id=_session())
        first = await log.append(event)
        second = await log.append(event)
        assert first == second
        assert await log.stream_length() == 1  # type: ignore[attr-defined]

    async def test_positions_are_distinct_and_follow_log_order(
        self, log_harness: LogHarness
    ) -> None:
        # Positions are opaque (ADR-0019): only distinctness and the order
        # the log reports them in are part of the contract.
        log = log_harness.log
        session = _session()
        events = [make_event(session_id=session) for _ in range(3)]
        positions = [await log.append(event) for event in events]
        assert len(set(positions)) == 3
        assert await log.read_session_ids(session) == [str(e.event_id) for e in events]
        documents = await log.get_documents([str(e.event_id) for e in events])
        assert [d["global_position"] for d in documents if d] == positions

    async def test_batch_append_dedups_within_batch(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        event = make_event(session_id=_session())
        other = make_event(session_id=event.session_id)
        positions = await log.append_batch([event, other, event])
        assert positions[0] == positions[2]
        assert positions[0] != positions[1]


class TestReads:
    async def test_read_your_writes(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        event = make_event(session_id=_session(), tool_name="search")
        position = await log.append(event)
        stored = await log.get_by_id(str(event.event_id))
        assert stored is not None
        assert stored.event_id == event.event_id
        assert stored.tool_name == "search"
        assert stored.global_position == position

    async def test_missing_event(self, log_harness: LogHarness) -> None:
        assert await log_harness.log.get_by_id(str(uuid4())) is None

    async def test_get_documents_keeps_order_and_payload(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        session = _session()
        first, second = make_event(session_id=session), make_event(session_id=session)
        await log.append(first, payload={"text": "hello"})
        await log.append(second)
        missing = str(uuid4())

        documents = await log.get_documents([str(second.event_id), missing, str(first.event_id)])

        assert documents[0] is not None
        assert documents[0]["event_id"] == str(second.event_id)
        assert "payload" not in documents[0]
        assert documents[1] is None
        assert documents[2] is not None
        assert documents[2]["payload"] == {"text": "hello"}
        assert "occurred_at_epoch_ms" not in documents[2]
        assert documents[2]["global_position"]

    async def test_read_session_ids_in_log_order(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        session, other_session = _session(), _session()
        now = datetime.now(UTC)
        # Appended out of time order: the session index follows log order.
        late = make_event(session_id=session, occurred_at=now)
        early = make_event(session_id=session, occurred_at=now - timedelta(hours=1))
        await log.append(late)
        await log.append(make_event(session_id=other_session))
        await log.append(early)

        assert await log.read_session_ids(session) == [str(late.event_id), str(early.event_id)]
        assert await log.read_session_ids(_session()) == []

    async def test_get_by_session_orders_by_occurred_at(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        session = _session()
        now = datetime.now(UTC)
        events = [
            make_event(session_id=session, occurred_at=now - timedelta(minutes=m))
            for m in (1, 3, 2)
        ]
        for event in events:
            await log.append(event)

        ordered = await log.get_by_session(session)
        assert [e.occurred_at for e in ordered] == sorted(e.occurred_at for e in events)
        page = await log.get_by_session(session, limit=1, after="1")
        assert [e.event_id for e in page] == [ordered[1].event_id]


class TestSearch:
    async def test_filters_and_time_range(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        session = _session()
        now = datetime.now(UTC)
        tool = make_event(
            session_id=session, event_type="tool.execute", tool_name="grep", occurred_at=now
        )
        agent = make_event(
            session_id=session,
            event_type="agent.invoke",
            agent_id="agent-b",
            occurred_at=now - timedelta(hours=2),
        )
        await log.append(tool)
        await log.append(agent)

        by_type = await log.search(EventQuery(session_id=session, event_type="tool.execute"))
        assert [e.event_id for e in by_type] == [tool.event_id]
        by_agent = await log.search(EventQuery(session_id=session, agent_id="agent-b"))
        assert [e.event_id for e in by_agent] == [agent.event_id]
        recent = await log.search(EventQuery(session_id=session, after=now - timedelta(minutes=5)))
        assert [e.event_id for e in recent] == [tool.event_id]
        everything = await log.search(EventQuery(session_id=session))
        assert [e.event_id for e in everything] == [agent.event_id, tool.event_id]
        assert len(await log.search(EventQuery(session_id=session, limit=1, offset=1))) == 1

    async def test_keyword_search_matches_indexed_text(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        session = _session()
        rollback, deploy, unrelated = (make_event(session_id=session) for _ in range(3))
        for event in (rollback, deploy, unrelated):
            await log.append(event)
        await log_harness.set_document_fields(
            str(rollback.event_id), {"summary": "deploy failed then rollback"}
        )
        await log_harness.set_document_fields(
            str(deploy.event_id), {"summary": "deploy finished", "keywords": ["release"]}
        )
        await log_harness.set_document_fields(str(unrelated.event_id), {"summary": "lunch"})

        # Any term matches; the event with both terms ranks first
        both = await log.search_bm25("deploy rollback", session_id=session)
        assert [e.event_id for e in both] == [rollback.event_id, deploy.event_id]
        deploys = await log.search_bm25("deploy", session_id=session)
        assert {e.event_id for e in deploys} == {rollback.event_id, deploy.event_id}
        by_keyword = await log.search_bm25("release", session_id=session)
        assert [e.event_id for e in by_keyword] == [deploy.event_id]
        assert await log.search_bm25("deploy", session_id=_session()) == []
        assert await log.search_bm25("   ") == []


class TestRetention:
    async def test_trim_keeps_entries_pending_for_a_group(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        session = _session()
        for _ in range(3):
            await log.append(make_event(session_id=session))
        subscription = log_harness.open_subscription("conf-group", "c1")
        await subscription.ensure_group()
        await subscription.read_new(1, 0)  # first entry now pending, unacked
        await asyncio.sleep(0.01)

        assert await log.trim(max_age_days=0, consumer_groups=["conf-group"]) == 0
        assert await log.stream_length() == 3  # type: ignore[attr-defined]

        delivered = await subscription.read_new(10, 0)
        pending = await subscription.read_pending(10)
        await subscription.ack(*(d.position for d in delivered + pending))
        await asyncio.sleep(0.01)
        # Everything is acknowledged: older entries go. Redis keeps the
        # group's last delivered entry (XTRIM MINID); keeping it is allowed.
        trimmed = await log.trim(max_age_days=0, consumer_groups=["conf-group"])
        assert trimmed in (2, 3)
        assert await log.stream_length() == 3 - trimmed  # type: ignore[attr-defined]

    async def test_trim_without_groups_drops_old_entries(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        for _ in range(2):
            await log.append(make_event(session_id=_session()))
        await asyncio.sleep(0.01)
        assert await log.trim(max_age_days=0, consumer_groups=[]) == 2
        assert await log.trim(max_age_days=30, consumer_groups=[]) == 0

    async def test_expire_deletes_old_documents(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        session = _session()
        old = make_event(session_id=session, occurred_at=datetime.now(UTC) - timedelta(days=10))
        recent = make_event(session_id=session)
        await log.append(old)
        await log.append(recent)

        assert await log.expire(max_age_days=5) == (0, 1)
        assert await log.get_by_id(str(old.event_id)) is None
        assert await log.get_by_id(str(recent.event_id)) is not None

    async def test_expire_archives_before_deleting(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        old = make_event(session_id=_session(), occurred_at=datetime.now(UTC) - timedelta(days=10))
        await log.append(old)
        archive = _RecordingArchive()

        assert await log.expire(max_age_days=5, archive_store=archive) == (1, 1)
        assert [d["event_id"] for d in archive.archived] == [str(old.event_id)]

    async def test_expire_keeps_documents_when_archive_fails(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        old = make_event(session_id=_session(), occurred_at=datetime.now(UTC) - timedelta(days=10))
        await log.append(old)

        archived, deleted = await log.expire(
            max_age_days=5, archive_store=_RecordingArchive(fail=True)
        )
        assert (archived, deleted) == (0, 0)
        assert await log.get_by_id(str(old.event_id)) is not None

    async def test_housekeep_clears_dedup_and_session_indexes(
        self, log_harness: LogHarness
    ) -> None:
        log = log_harness.log
        session = _session()
        event = make_event(session_id=session, occurred_at=datetime.now(UTC) - timedelta(days=2))
        first_position = await log.append(event)
        await asyncio.sleep(0.01)

        counts = await log.housekeep(retention_ceiling_days=1, session_index_max_age_hours=0)

        assert counts["dedup_entries_removed"] >= 1
        assert counts["session_streams_deleted"] >= 1
        assert await log.read_session_ids(session) == []
        # With its dedup record gone, the same event appends as new.
        assert await log.append(event) != first_position


@pytest.mark.parametrize("missing", [[], [str(uuid4())]])
async def test_get_documents_edge_cases(log_harness: LogHarness, missing: list[str]) -> None:
    assert await log_harness.log.get_documents(missing) == [None] * len(missing)
