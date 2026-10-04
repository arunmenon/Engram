"""EventLog migration conformance (ADR-0019 §7, design brief phase 3).

Every backend must read its log in order (``read_after``) and accept an
ordered, idempotent import that keeps each event's source position as
``legacy_position`` (``MigrationTarget``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import orjson

from context_graph.ports.event_log import ImportedEvent
from tests.fixtures.events import make_event

if TYPE_CHECKING:
    from context_graph.ports.event_log import MigrationTarget
    from tests.conformance.conftest import LogHarness


def _target(harness: LogHarness) -> MigrationTarget:
    return harness.log  # type: ignore[return-value]


def _document(minutes_ago: int, session_id: str) -> dict[str, Any]:
    event = make_event(
        session_id=session_id, occurred_at=datetime.now(UTC) - timedelta(minutes=minutes_ago)
    )
    document: dict[str, Any] = orjson.loads(event.model_dump_json())
    document["payload"] = {"text": f"turn {minutes_ago}"}
    document["global_position"] = f"source-{minutes_ago}"  # dropped on import
    return document


class TestReadAfter:
    async def test_reads_in_log_order_with_cursor(self, log_harness: LogHarness) -> None:
        log = log_harness.log
        session = f"conf-{uuid4().hex[:8]}"
        events = [make_event(session_id=session) for _ in range(5)]
        positions = [await log.append(event) for event in events]

        first = await log.read_after(None, 2)
        rest = await log.read_after(first[-1].position, 10)

        assert [e.position for e in first + rest] == positions
        assert [e.event_id for e in first + rest] == [str(e.event_id) for e in events]
        assert all(e.document and e.document["global_position"] == e.position for e in first)
        assert await log.read_after(positions[-1], 10) == []


class TestImport:
    async def test_empty_log(self, log_harness: LogHarness) -> None:
        target = _target(log_harness)
        assert await target.last_legacy_position() is None
        assert await target.has_native_events() is False

    async def test_import_keeps_source_order_and_legacy_positions(
        self, log_harness: LogHarness
    ) -> None:
        target = _target(log_harness)
        session = f"conf-{uuid4().hex[:8]}"
        # Source order differs from occurred_at order on purpose.
        documents = [_document(m, session) for m in (1, 30, 5)]
        imported = [
            ImportedEvent(document=d, legacy_position=f"170000000000{i}-0")
            for i, d in enumerate(documents)
        ]

        positions = await target.append_imported(imported[:2])
        positions += await target.append_imported(imported[2:])

        entries = await log_harness.log.read_after(None, 10)
        assert [e.event_id for e in entries] == [d["event_id"] for d in documents]
        assert [e.position for e in entries] == positions
        assert [e.document["legacy_position"] for e in entries if e.document] == [
            i.legacy_position for i in imported
        ]
        assert entries[0].document["payload"] == {"text": "turn 1"}  # type: ignore[index]
        assert entries[0].document["global_position"] == positions[0]  # type: ignore[index]
        assert await log_harness.log.read_session_ids(session) == [d["event_id"] for d in documents]
        assert await target.last_legacy_position() == imported[-1].legacy_position
        assert await target.has_native_events() is False

    async def test_import_is_idempotent(self, log_harness: LogHarness) -> None:
        target = _target(log_harness)
        imported = [ImportedEvent(document=_document(1, "s"), legacy_position="1700000000000-0")]
        first = await target.append_imported(imported)
        second = await target.append_imported(imported)
        assert first == second
        assert await log_harness.log.stream_length() == 1  # type: ignore[attr-defined]

    async def test_native_append_is_detected(self, log_harness: LogHarness) -> None:
        target = _target(log_harness)
        await target.append_imported(
            [ImportedEvent(document=_document(1, "s"), legacy_position="1700000000000-0")]
        )
        await log_harness.log.append(make_event())
        assert await target.has_native_events() is True
        assert await target.last_legacy_position() == "1700000000000-0"
