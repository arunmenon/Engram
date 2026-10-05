"""In-memory implementation of the EventLog port (ADR-0019 step 3).

The reference backend for the conformance suite and for tests that must
not need Redis. Semantics follow the Redis adapter:

- append is idempotent: a duplicate ``event_id`` returns the position
  first assigned;
- every new event is published to the shared stream (``event_id`` field)
  and indexed by session in log order;
- stored documents are the event's JSON fields plus ``global_position``
  and, when given, ``payload``;
- ``search`` filters are exact, case-insensitive tag matches plus an
  inclusive time range, ordered by ``occurred_at``;
- stored documents also carry ``search_text``, built from the payload at
  ingest (``domain/keyword_search.py``);
- ``search_bm25`` matches documents containing any query term in
  ``summary``, ``keywords`` or ``search_text`` (the RediSearch index's
  fields and weights) and ranks by a saturating, IDF-weighted term count.
  Scores are not BM25.

Single-process and not durable.

Source: ADR-0004, ADR-0010, ADR-0014, ADR-0019
"""

from __future__ import annotations

import math
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import orjson
import structlog

from context_graph.adapters.memory.stream import MemoryStream, position_sort_key
from context_graph.domain.keyword_search import event_search_text, query_terms, tokenize
from context_graph.domain.models import Event
from context_graph.ports.event_log import ImportedEvent, LogEntry
from context_graph.ports.event_store import AppendOutcome
from context_graph.settings import KeywordSearchSettings

if TYPE_CHECKING:
    from collections.abc import Callable

    from context_graph.domain.models import EventQuery
    from context_graph.ports.archive import ArchiveStore

log = structlog.get_logger(__name__)

# Same field weights as the RediSearch event index (adapters/redis/indexes.py)
SUMMARY_WEIGHT = 2.0
KEYWORDS_WEIGHT = 1.5
SEARCH_TEXT_WEIGHT = 1.0


def _epoch_ms(moment: datetime) -> int:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp() * 1000)


class _DedupRecord:
    __slots__ = ("occurred_at_ms", "position")

    def __init__(self, position: str, occurred_at_ms: int) -> None:
        self.position = position
        self.occurred_at_ms = occurred_at_ms


class MemoryEventLog:
    """EventLog over in-process dicts and a ``MemoryStream``.

    Satisfies ``EventLog``, ``EventStoreAdmin`` and ``HealthCheckable``.
    """

    def __init__(
        self,
        stream: MemoryStream | None = None,
        clock: Callable[[], float] = time.time,
        keyword: KeywordSearchSettings | None = None,
    ) -> None:
        self._clock = clock
        self._keyword = keyword or KeywordSearchSettings()
        self._stream = stream if stream is not None else MemoryStream("events", clock=clock)
        self._documents: dict[str, dict[str, Any]] = {}
        self._dedup: dict[str, _DedupRecord] = {}
        self._sessions: dict[str, list[tuple[str, str, int]]] = {}

    @property
    def stream(self) -> MemoryStream:
        """The stream subscriptions read from."""
        return self._stream

    # -- lifecycle / admin --------------------------------------------------

    async def ensure_indexes(self) -> None:
        """Nothing to create: searches scan the documents."""

    async def health_ping(self) -> bool:
        return True

    async def stream_length(self) -> int:
        return len(self._stream)

    async def close(self) -> None:
        """Nothing to release."""

    # -- writes -------------------------------------------------------------

    async def append(self, event: Event, payload: dict[str, Any] | None = None) -> str:
        event_id = str(event.event_id)
        existing = self._dedup.get(event_id)
        if existing is not None:
            return existing.position

        document: dict[str, Any] = orjson.loads(event.model_dump_json())
        if payload is not None:
            document["payload"] = payload
        search_text = event_search_text(event, payload, self._keyword.text_max_chars)
        if search_text:
            document["search_text"] = search_text
        return await self._store(event_id, event.session_id, _epoch_ms(event.occurred_at), document)

    async def _store(
        self, event_id: str, session_id: str, occurred_at_ms: int, document: dict[str, Any]
    ) -> str:
        position = await self._stream.append({"event_id": event_id})
        stored = dict(document)
        stored["occurred_at_epoch_ms"] = occurred_at_ms
        stored["global_position"] = position
        self._documents[event_id] = stored

        appended_at_ms = position_sort_key(position)[0]
        self._sessions.setdefault(session_id, []).append((position, event_id, appended_at_ms))
        self._dedup[event_id] = _DedupRecord(position, occurred_at_ms)
        return position

    async def append_batch(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
    ) -> list[str]:
        positions: list[str] = []
        for idx, event in enumerate(events):
            payload = payloads[idx] if payloads and idx < len(payloads) else None
            positions.append(await self.append(event, payload))
        return positions

    async def append_batch_outcomes(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
    ) -> list[AppendOutcome]:
        outcomes: list[AppendOutcome] = []
        for idx, event in enumerate(events):
            existing = self._dedup.get(str(event.event_id))
            if existing is not None:
                outcomes.append(AppendOutcome("duplicate", existing.position))
                continue
            payload = payloads[idx] if payloads and idx < len(payloads) else None
            outcomes.append(AppendOutcome("created", await self.append(event, payload)))
        return outcomes

    # -- migration (ADR-0019 §7) ---------------------------------------------

    async def append_imported(self, events: list[ImportedEvent]) -> list[str]:
        positions: list[str] = []
        for imported in events:
            document = dict(imported.document)
            document.pop("global_position", None)
            document["legacy_position"] = imported.legacy_position
            event_id = str(document["event_id"])
            existing = self._dedup.get(event_id)
            if existing is not None:
                positions.append(existing.position)
                continue
            occurred_at_ms = _epoch_ms(datetime.fromisoformat(str(document["occurred_at"])))
            positions.append(
                await self._store(event_id, str(document["session_id"]), occurred_at_ms, document)
            )
        return positions

    async def last_legacy_position(self) -> str | None:
        for entry in reversed(self._stream.entries()):
            document = self._documents.get(entry.fields.get("event_id", ""))
            if document is not None and document.get("legacy_position"):
                return str(document["legacy_position"])
        return None

    async def has_native_events(self) -> bool:
        for entry in self._stream.entries():
            document = self._documents.get(entry.fields.get("event_id", ""))
            if document is None or not document.get("legacy_position"):
                return True
        return False

    # -- reads --------------------------------------------------------------

    async def read_after(self, position: str | None, limit: int) -> list[LogEntry]:
        after = position_sort_key(position) if position else (-1, -1)
        entries: list[LogEntry] = []
        for entry in self._stream.entries():
            if position_sort_key(entry.position) <= after:
                continue
            event_id = entry.fields.get("event_id", "")
            document = self._documents.get(event_id)
            entries.append(
                LogEntry(
                    position=entry.position,
                    event_id=event_id,
                    document=self._public(document) if document is not None else None,
                )
            )
            if len(entries) >= limit:
                break
        return entries

    @staticmethod
    def _public(document: dict[str, Any]) -> dict[str, Any]:
        public = dict(document)
        public.pop("occurred_at_epoch_ms", None)
        return public

    def _event(self, document: dict[str, Any]) -> Event:
        return Event.model_validate(self._public(document), strict=False)

    async def get_by_id(self, event_id: str) -> Event | None:
        document = self._documents.get(event_id)
        return self._event(document) if document is not None else None

    async def get_documents(self, event_ids: list[str]) -> list[dict[str, Any] | None]:
        documents: list[dict[str, Any] | None] = []
        for event_id in event_ids:
            document = self._documents.get(event_id)
            documents.append(self._public(document) if document is not None else None)
        return documents

    async def read_session_ids(self, session_id: str) -> list[str]:
        return [event_id for _pos, event_id, _ms in self._sessions.get(session_id, [])]

    def _sorted_documents(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            documents,
            key=lambda d: (d["occurred_at_epoch_ms"], position_sort_key(d["global_position"])),
        )

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        after: str | None = None,
    ) -> list[Event]:
        offset = 0
        if after is not None:
            try:
                offset = int(after)
            except ValueError:
                offset = 0
        matches = [
            d for d in self._documents.values() if _tag_equal(d.get("session_id"), session_id)
        ]
        page = self._sorted_documents(matches)[offset : offset + limit]
        return [self._event(d) for d in page]

    async def search(self, query: EventQuery) -> list[Event]:
        tag_filters = {
            "session_id": query.session_id,
            "agent_id": query.agent_id,
            "trace_id": query.trace_id,
            "event_type": query.event_type,
            "tool_name": query.tool_name,
        }
        after_ms = _epoch_ms(query.after) if query.after else None
        before_ms = _epoch_ms(query.before) if query.before else None

        def matches(document: dict[str, Any]) -> bool:
            for field_name, wanted in tag_filters.items():
                if wanted and not _tag_equal(document.get(field_name), wanted):
                    return False
            epoch_ms = document["occurred_at_epoch_ms"]
            if after_ms is not None and epoch_ms < after_ms:
                return False
            return before_ms is None or epoch_ms <= before_ms

        hits = self._sorted_documents([d for d in self._documents.values() if matches(d)])
        return [self._event(d) for d in hits[query.offset : query.offset + query.limit]]

    async def search_bm25(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[Event]:
        terms = query_terms(query_text or "", self._keyword.max_query_terms)
        if not terms:
            return []

        weighted: list[tuple[dict[str, float], dict[str, Any]]] = []
        document_frequency: dict[str, int] = dict.fromkeys(terms, 0)
        candidates = 0
        for document in self._documents.values():
            if session_id and not _tag_equal(document.get("session_id"), session_id):
                continue
            candidates += 1
            keywords = document.get("keywords") or []
            fields = (
                (SUMMARY_WEIGHT, tokenize(str(document.get("summary") or ""))),
                (KEYWORDS_WEIGHT, tokenize(" ".join(str(k) for k in keywords))),
                (SEARCH_TEXT_WEIGHT, tokenize(str(document.get("search_text") or ""))),
            )
            frequencies = {
                term: sum(weight * tokens.count(term) for weight, tokens in fields)
                for term in terms
            }
            frequencies = {term: tf for term, tf in frequencies.items() if tf > 0}
            if not frequencies:
                continue
            for term in frequencies:
                document_frequency[term] += 1
            weighted.append((frequencies, document))

        def score(frequencies: dict[str, float]) -> float:
            return sum(
                math.log(1 + candidates / document_frequency[term]) * tf / (tf + 1)
                for term, tf in frequencies.items()
            )

        scored = [(score(frequencies), document) for frequencies, document in weighted]
        scored.sort(key=lambda item: (-item[0], position_sort_key(item[1]["global_position"])))
        return [self._event(d) for _score, d in scored[:limit]]

    # -- retention (ADR-0014) -----------------------------------------------

    def _cutoff_ms(self, *, days: float = 0, hours: float = 0) -> int:
        now = datetime.fromtimestamp(self._clock(), tz=UTC)
        return _epoch_ms(now - timedelta(days=days, hours=hours))

    async def trim(self, max_age_days: int, consumer_groups: list[str]) -> int:
        min_position = f"{self._cutoff_ms(days=max_age_days)}-0"
        progress = [
            p
            for p in (self._stream.group_progress(name) for name in consumer_groups)
            if p is not None
        ]
        if progress:
            oldest = min(progress, key=position_sort_key)
            if position_sort_key(oldest) < position_sort_key(min_position):
                log.warning("consumer_groups_lagging", oldest=oldest, cutoff=min_position)
                min_position = oldest
        return self._stream.trim_before(min_position)

    async def expire(
        self,
        max_age_days: int,
        archive_store: ArchiveStore | None = None,
    ) -> tuple[int, int]:
        cutoff_ms = self._cutoff_ms(days=max_age_days)
        expired = {
            event_id: document
            for event_id, document in self._documents.items()
            if document["occurred_at_epoch_ms"] < cutoff_ms
        }
        if not expired:
            return 0, 0
        archived = 0
        if archive_store is not None:
            partition_key = datetime.fromtimestamp(self._clock(), tz=UTC).strftime("%Y/%m/%d")
            try:
                await archive_store.archive_events(
                    [dict(d) for d in expired.values()], partition_key
                )
            except Exception:
                log.exception("archive_failed_skipping_delete", event_count=len(expired))
                return 0, 0
            archived = len(expired)
        for event_id in expired:
            del self._documents[event_id]
        return archived, len(expired)

    async def housekeep(
        self,
        retention_ceiling_days: int,
        session_index_max_age_hours: int,
    ) -> dict[str, int]:
        dedup_cutoff_ms = self._cutoff_ms(days=retention_ceiling_days)
        stale_dedup = [
            event_id
            for event_id, record in self._dedup.items()
            if record.occurred_at_ms <= dedup_cutoff_ms
        ]
        for event_id in stale_dedup:
            del self._dedup[event_id]

        session_cutoff_ms = self._cutoff_ms(hours=session_index_max_age_hours)
        stale_sessions = [
            session_id
            for session_id, entries in self._sessions.items()
            if not entries or entries[-1][2] < session_cutoff_ms
        ]
        for session_id in stale_sessions:
            del self._sessions[session_id]

        return {
            "dedup_entries_removed": len(stale_dedup),
            "session_streams_deleted": len(stale_sessions),
        }

    # -- test support -------------------------------------------------------

    def set_document_fields(self, event_id: str, **fields: Any) -> None:
        """Add fields to a stored document (for example ``summary`` for keyword search).

        Test support: the Redis adapter's equivalent is ``JSON.SET`` on the
        document. Raises KeyError for an unknown event.
        """
        self._documents[event_id].update(fields)


def _tag_equal(value: Any, wanted: str) -> bool:
    """RediSearch TAG fields match case-insensitively."""
    return value is not None and str(value).lower() == wanted.lower()
