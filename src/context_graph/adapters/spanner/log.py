"""Spanner implementation of the EventLog port (ADR-0019 step 4).

Follows the Spanner design brief:

- D1: positions are ``<commit ts, UTC to nanoseconds>/<batch index>/<event id>``,
  fixed width; the old Redis id, when migrated, goes to ``legacy_position``;
- G2: append is one read-write transaction: read by ``event_id``; a live
  duplicate returns its position, otherwise the row is written with the
  commit timestamp and the position is built from the commit response;
- D3: rows carry ``shard = crc32(session_id) mod N`` for the sharded time
  index that subscriptions poll;
- G6: keyword search uses Spanner full-text search (``SEARCH``/``SCORE``)
  over the ``summary`` and ``keywords`` fields, as RediSearch did;
- G7: retention keeps the hot-window model. Redis keeps four structures
  (stream entry, JSON document, session stream, dedup record); here one
  row carries a flag for each (``in_log``, ``document``,
  ``in_session_index``, ``dedup_active``) and is deleted when all are gone.

The Google client is synchronous; calls run in worker threads so they do
not block the event loop (brief G12).

Source: ADR-0004, ADR-0010, ADR-0014, ADR-0019
"""

from __future__ import annotations

import asyncio
import json
import zlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import orjson
import structlog

from context_graph.adapters.errors import translate_errors
from context_graph.adapters.spanner.errors import translate_spanner_error
from context_graph.domain.models import Event
from context_graph.ports.event_log import ImportedEvent, LogEntry

if TYPE_CHECKING:
    from context_graph.domain.models import EventQuery
    from context_graph.ports.archive import ArchiveStore

log = structlog.get_logger(__name__)

EVENT_COLUMNS = [
    "event_id",
    "shard",
    "commit_ts",
    "batch_index",
    "session_id",
    "occurred_at_ms",
    "session_tag",
    "agent_tag",
    "trace_tag",
    "event_type_tag",
    "tool_name_tag",
    "document",
    "in_log",
    "in_session_index",
    "dedup_active",
    "summary",
    "keywords",
    "legacy_position",
]

# Columns that rebuild a position
POSITION_COLUMNS = "commit_ts, batch_index, event_id"


def shard_for(session_id: str, shards: int) -> int:
    """Stable shard for a session (design brief D3)."""
    return zlib.crc32(session_id.encode()) % shards


def format_position(commit_ts: datetime, batch_index: int, event_id: str) -> str:
    """Fixed-width position: sorts as a string in commit order (D1)."""
    nanos = getattr(commit_ts, "nanosecond", None)
    if nanos is None:
        nanos = commit_ts.microsecond * 1000
    utc = commit_ts.astimezone(UTC)
    return f"{utc:%Y-%m-%dT%H:%M:%S}.{nanos:09d}Z/{batch_index:06d}/{event_id}"


def event_id_of(position: str) -> str:
    """The event id a position names."""
    return position.rsplit("/", 1)[-1]


def json_value(value: Any) -> Any:
    """Plain Python value from a Spanner JSON cell (JsonObject or str)."""
    if value is None:
        return None
    serialize = getattr(value, "serialize", None)
    if serialize is not None:
        serialized = serialize()
        return json.loads(serialized) if serialized is not None else None
    if isinstance(value, str):
        return json.loads(value)
    return value


def json_param(value: Any) -> Any:
    from google.cloud.spanner_v1.data_types import JsonObject

    return JsonObject(value)


def _tag(value: Any) -> str | None:
    """RediSearch TAG fields match case-insensitively; store lowercased."""
    return str(value).lower() if value is not None else None


def _epoch_ms(moment: datetime) -> int:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return int(moment.timestamp() * 1000)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return " ".join(str(v) for v in value)
    return str(value)


@translate_errors(translate_spanner_error)
class SpannerEventLog:
    """EventLog over a Spanner database (``adapters.spanner.schema``).

    Satisfies ``EventLog``, ``EventStoreAdmin`` and ``HealthCheckable``.
    """

    def __init__(self, database: Any, *, shards: int = 16) -> None:
        self._database = database
        self._shards = shards

    @property
    def database(self) -> Any:
        """The Spanner database, shared with subscriptions by the registry."""
        return self._database

    @property
    def shards(self) -> int:
        return self._shards

    async def _run(self, fn: Any, *args: Any) -> Any:
        return await asyncio.to_thread(fn, *args)

    async def _query(
        self, sql: str, params: dict[str, Any] | None = None, types: dict[str, Any] | None = None
    ) -> list[list[Any]]:
        def query() -> list[list[Any]]:
            with self._database.snapshot() as snapshot:
                return [
                    list(row) for row in snapshot.execute_sql(sql, params=params, param_types=types)
                ]

        result: list[list[Any]] = await self._run(query)
        return result

    # -- lifecycle / admin --------------------------------------------------

    async def ensure_indexes(self) -> None:
        """Indexes are part of the schema (``adapters.spanner.schema``)."""

    async def health_ping(self) -> bool:
        try:
            await self._query("SELECT 1")
        except Exception:  # noqa: BLE001
            return False
        return True

    async def stream_length(self) -> int:
        rows = await self._query("SELECT COUNT(*) FROM Events WHERE in_log")
        return int(rows[0][0])

    async def close(self) -> None:
        """The client owns no connection that needs closing per store."""

    # -- writes -------------------------------------------------------------

    def _row(
        self,
        event_id: str,
        session_id: str,
        batch_index: int,
        document: dict[str, Any] | None,
        occurred_at_ms: int,
    ) -> list[Any]:
        from google.cloud import spanner

        doc = document or {}
        return [
            event_id,
            shard_for(session_id, self._shards),
            spanner.COMMIT_TIMESTAMP,
            batch_index,
            session_id,
            occurred_at_ms,
            _tag(session_id),
            _tag(doc.get("agent_id")),
            _tag(doc.get("trace_id")),
            _tag(doc.get("event_type")),
            _tag(doc.get("tool_name")),
            json_param(document) if document is not None else None,
            True,
            True,
            True,
            _text(doc.get("summary")),
            _text(doc.get("keywords")),
            doc.get("legacy_position"),
        ]

    def _append_entries_sync(
        self, entries: list[tuple[str, str, dict[str, Any] | None, int]]
    ) -> list[str]:
        """Append (event_id, session_id, document, occurred_at_ms) in one transaction."""
        from google.cloud.spanner_v1 import KeySet

        holder: dict[str, Any] = {}

        def work(transaction: Any) -> list[tuple[str, int] | str]:
            holder["transaction"] = transaction
            ids = sorted({event_id for event_id, _s, _d, _o in entries})
            existing: dict[str, str] = {}
            for row in transaction.read(
                "Events",
                ["event_id", "commit_ts", "batch_index", "dedup_active"],
                KeySet(keys=[[event_id] for event_id in ids]),
            ):
                event_id, commit_ts, batch_index, dedup_active = row
                if dedup_active:
                    existing[event_id] = format_position(commit_ts, batch_index, event_id)
            results: list[tuple[str, int] | str] = []
            written: dict[str, int] = {}
            rows = []
            for event_id, session_id, document, occurred_at_ms in entries:
                if event_id in existing:
                    results.append(existing[event_id])
                elif event_id in written:
                    results.append((event_id, written[event_id]))
                else:
                    batch_index = len(written)
                    written[event_id] = batch_index
                    rows.append(
                        self._row(event_id, session_id, batch_index, document, occurred_at_ms)
                    )
                    results.append((event_id, batch_index))
            if rows:
                transaction.insert_or_update("Events", EVENT_COLUMNS, rows)
            return results

        results = self._database.run_in_transaction(work)
        commit_ts = holder["transaction"].committed
        return [
            item if isinstance(item, str) else format_position(commit_ts, item[1], item[0])
            for item in results
        ]

    @staticmethod
    def _document(event: Event, payload: dict[str, Any] | None) -> dict[str, Any]:
        document: dict[str, Any] = orjson.loads(event.model_dump_json())
        if payload is not None:
            document["payload"] = payload
        return document

    async def append(self, event: Event, payload: dict[str, Any] | None = None) -> str:
        positions = await self.append_batch([event], [payload])
        return positions[0]

    async def append_batch(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
    ) -> list[str]:
        if not events:
            return []
        entries = []
        for idx, event in enumerate(events):
            payload = payloads[idx] if payloads and idx < len(payloads) else None
            entries.append(
                (
                    str(event.event_id),
                    event.session_id,
                    self._document(event, payload),
                    _epoch_ms(event.occurred_at),
                )
            )
        positions: list[str] = await self._run(self._append_entries_sync, entries)
        return positions

    # -- migration (ADR-0019 §7, design brief phase 3) ------------------------

    async def append_imported(self, events: list[ImportedEvent]) -> list[str]:
        """Import copied events in one transaction; ``batch_index`` keeps their order."""
        if not events:
            return []
        entries = []
        for imported in events:
            document = dict(imported.document)
            document.pop("global_position", None)
            document["legacy_position"] = imported.legacy_position
            occurred_at = datetime.fromisoformat(str(document["occurred_at"]))
            entries.append(
                (
                    str(document["event_id"]),
                    str(document["session_id"]),
                    document,
                    _epoch_ms(occurred_at),
                )
            )
        positions: list[str] = await self._run(self._append_entries_sync, entries)
        return positions

    async def last_legacy_position(self) -> str | None:
        rows = await self._query(
            "SELECT legacy_position FROM Events WHERE legacy_position IS NOT NULL "
            "ORDER BY commit_ts DESC, batch_index DESC, event_id DESC LIMIT 1"
        )
        return str(rows[0][0]) if rows else None

    async def has_native_events(self) -> bool:
        rows = await self._query("SELECT 1 FROM Events WHERE legacy_position IS NULL LIMIT 1")
        return bool(rows)

    async def read_after(self, position: str | None, limit: int) -> list[LogEntry]:
        from google.cloud.spanner_v1 import param_types

        where = ["in_log"]
        params: dict[str, Any] = {"limit": limit}
        types: dict[str, Any] = {"limit": param_types.INT64}
        if position:
            timestamp, batch_index, event_id = position.split("/", 2)
            where.append(
                "(commit_ts > CAST(@ts AS TIMESTAMP) OR (commit_ts = CAST(@ts AS TIMESTAMP) "
                "AND (batch_index > @batch OR (batch_index = @batch AND event_id > @event_id))))"
            )
            params.update({"ts": timestamp, "batch": int(batch_index), "event_id": event_id})
            types.update(
                {
                    "ts": param_types.STRING,
                    "batch": param_types.INT64,
                    "event_id": param_types.STRING,
                }
            )
        rows = await self._query(
            f"SELECT document, {POSITION_COLUMNS} FROM Events WHERE {' AND '.join(where)} "
            f"ORDER BY {POSITION_COLUMNS} LIMIT @limit",
            params,
            types,
        )
        return [
            LogEntry(
                position=format_position(ts, batch, eid),
                event_id=eid,
                document=self._public(doc, ts, batch, eid),
            )
            for doc, ts, batch, eid in rows
        ]

    async def append_entry(self, event_id: str, session_id: str) -> str:
        """Append a bare log entry with no document (test support for subscriptions)."""
        positions: list[str] = await self._run(
            self._append_entries_sync,
            [(event_id, session_id, None, _epoch_ms(datetime.now(UTC)))],
        )
        return positions[0]

    # -- reads --------------------------------------------------------------

    @staticmethod
    def _public(document: Any, commit_ts: datetime, batch_index: int, event_id: str) -> Any:
        doc = json_value(document)
        if doc is None:
            return None
        doc["global_position"] = format_position(commit_ts, batch_index, event_id)
        return doc

    async def _documents(self, event_ids: list[str]) -> dict[str, dict[str, Any]]:
        from google.cloud.spanner_v1 import KeySet

        if not event_ids:
            return {}

        def read() -> dict[str, dict[str, Any]]:
            out = {}
            with self._database.snapshot() as snapshot:
                for event_id, document, commit_ts, batch_index in snapshot.read(
                    "Events",
                    ["event_id", "document", "commit_ts", "batch_index"],
                    KeySet(keys=[[eid] for eid in sorted(set(event_ids))]),
                ):
                    doc = self._public(document, commit_ts, batch_index, event_id)
                    if doc is not None:
                        out[event_id] = doc
            return out

        result: dict[str, dict[str, Any]] = await self._run(read)
        return result

    async def get_documents(self, event_ids: list[str]) -> list[dict[str, Any] | None]:
        found = await self._documents(event_ids)
        return [dict(found[eid]) if eid in found else None for eid in event_ids]

    async def get_by_id(self, event_id: str) -> Event | None:
        found = await self._documents([event_id])
        doc = found.get(event_id)
        return Event.model_validate(doc, strict=False) if doc is not None else None

    async def read_session_ids(self, session_id: str) -> list[str]:
        from google.cloud.spanner_v1 import param_types

        rows = await self._query(
            "SELECT event_id FROM Events@{FORCE_INDEX=EventsBySession} "
            "WHERE session_id = @session AND in_session_index "
            f"ORDER BY {POSITION_COLUMNS}",
            {"session": session_id},
            {"session": param_types.STRING},
        )
        return [row[0] for row in rows]

    async def _search_documents(
        self,
        where: list[str],
        params: dict[str, Any],
        types: dict[str, Any],
        limit: int,
        offset: int,
    ) -> list[Event]:
        from google.cloud.spanner_v1 import param_types

        clauses = " AND ".join(["document IS NOT NULL", *where])
        params = {**params, "limit": limit, "offset": offset}
        types = {**types, "limit": param_types.INT64, "offset": param_types.INT64}
        rows = await self._query(
            f"SELECT document, {POSITION_COLUMNS} FROM Events WHERE {clauses} "
            f"ORDER BY occurred_at_ms, {POSITION_COLUMNS} LIMIT @limit OFFSET @offset",
            params,
            types,
        )
        return [
            Event.model_validate(self._public(doc, ts, batch, eid), strict=False)
            for doc, ts, batch, eid in rows
        ]

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        after: str | None = None,
    ) -> list[Event]:
        from google.cloud.spanner_v1 import param_types

        offset = 0
        if after is not None:
            try:
                offset = int(after)
            except ValueError:
                offset = 0
        return await self._search_documents(
            ["session_tag = @session"],
            {"session": session_id.lower()},
            {"session": param_types.STRING},
            limit,
            offset,
        )

    async def search(self, query: EventQuery) -> list[Event]:
        from google.cloud.spanner_v1 import param_types

        where: list[str] = []
        params: dict[str, Any] = {}
        types: dict[str, Any] = {}
        for column, value in (
            ("session_tag", query.session_id),
            ("agent_tag", query.agent_id),
            ("trace_tag", query.trace_id),
            ("event_type_tag", query.event_type),
            ("tool_name_tag", query.tool_name),
        ):
            if value:
                where.append(f"{column} = @{column}")
                params[column] = value.lower()
                types[column] = param_types.STRING
        if query.after:
            where.append("occurred_at_ms >= @after_ms")
            params["after_ms"] = _epoch_ms(query.after)
            types["after_ms"] = param_types.INT64
        if query.before:
            where.append("occurred_at_ms <= @before_ms")
            params["before_ms"] = _epoch_ms(query.before)
            types["before_ms"] = param_types.INT64
        return await self._search_documents(where, params, types, query.limit, query.offset)

    async def search_scored(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[tuple[Event, float]]:
        """Full-text search returning events with their Spanner ``SCORE``, best first."""
        from google.cloud.spanner_v1 import param_types

        if not query_text or not query_text.strip():
            return []
        where = ["document IS NOT NULL", "SEARCH(text_tokens, @q)"]
        params: dict[str, Any] = {"q": query_text.strip(), "limit": limit}
        types: dict[str, Any] = {"q": param_types.STRING, "limit": param_types.INT64}
        if session_id:
            where.append("session_tag = @session")
            params["session"] = session_id.lower()
            types["session"] = param_types.STRING
        rows = await self._query(
            f"SELECT document, {POSITION_COLUMNS}, SCORE(text_tokens, @q) AS relevance "
            f"FROM Events WHERE {' AND '.join(where)} "
            f"ORDER BY relevance DESC, {POSITION_COLUMNS} LIMIT @limit",
            params,
            types,
        )
        return [
            (Event.model_validate(self._public(doc, ts, batch, eid), strict=False), float(score))
            for doc, ts, batch, eid, score in rows
        ]

    async def search_bm25(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[Event]:
        return [event for event, _score in await self.search_scored(query_text, session_id, limit)]

    # -- retention (ADR-0014, brief G7) ---------------------------------------

    async def _execute_updates(
        self, statements: list[tuple[str, dict[str, Any], dict[str, Any]]]
    ) -> list[int]:
        def work(transaction: Any) -> list[int]:
            return [
                transaction.execute_update(sql, params=params, param_types=types)
                for sql, params, types in statements
            ]

        counts: list[int] = await self._run(self._database.run_in_transaction, work)
        return counts

    async def trim(self, max_age_days: int, consumer_groups: list[str]) -> int:
        from google.cloud.spanner_v1 import param_types

        # Commit timestamps come from the database clock, so the cutoff does
        # too: a skewed application host must not trim fresh entries.
        # An entry is still needed by a group while it is pending for it or
        # lies after the group's cursor in its shard (not yet delivered).
        sql = (
            "UPDATE Events e SET in_log = FALSE "
            "WHERE e.in_log "
            "AND e.commit_ts < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY) "
            "AND NOT EXISTS (SELECT 1 FROM ConsumerDeliveries d "
            "  WHERE d.group_name IN UNNEST(@groups) AND d.event_id = e.event_id) "
            "AND NOT EXISTS (SELECT 1 FROM ConsumerCursors c "
            "  WHERE c.group_name IN UNNEST(@groups) AND c.shard = e.shard "
            "  AND (e.commit_ts > c.commit_ts OR (e.commit_ts = c.commit_ts "
            "  AND (e.batch_index > c.batch_index OR (e.batch_index = c.batch_index "
            "  AND e.event_id > c.event_id)))))"
        )
        (trimmed,) = await self._execute_updates(
            [
                (
                    sql,
                    {"days": max_age_days, "groups": list(consumer_groups)},
                    {
                        "days": param_types.INT64,
                        "groups": param_types.Array(param_types.STRING),
                    },
                )
            ]
        )
        await self._purge()
        return trimmed

    async def expire(
        self,
        max_age_days: int,
        archive_store: ArchiveStore | None = None,
    ) -> tuple[int, int]:
        from google.cloud.spanner_v1 import param_types

        cutoff_ms = _epoch_ms(datetime.now(UTC) - timedelta(days=max_age_days))
        rows = await self._query(
            f"SELECT document, {POSITION_COLUMNS}, occurred_at_ms FROM Events "
            "WHERE document IS NOT NULL AND occurred_at_ms < @cutoff",
            {"cutoff": cutoff_ms},
            {"cutoff": param_types.INT64},
        )
        if not rows:
            return 0, 0
        expired_ids = [eid for _doc, _ts, _batch, eid, _ms in rows]
        archived = 0
        if archive_store is not None:
            documents = []
            for doc, ts, batch, eid, occurred_ms in rows:
                public = self._public(doc, ts, batch, eid)
                public["occurred_at_epoch_ms"] = occurred_ms
                documents.append(public)
            partition_key = datetime.now(UTC).strftime("%Y/%m/%d")
            try:
                await archive_store.archive_events(documents, partition_key)
            except Exception:
                log.exception("archive_failed_skipping_delete", event_count=len(documents))
                return 0, 0
            archived = len(documents)
        (deleted,) = await self._execute_updates(
            [
                (
                    "UPDATE Events SET document = NULL "
                    "WHERE event_id IN UNNEST(@ids) AND document IS NOT NULL",
                    {"ids": expired_ids},
                    {"ids": param_types.Array(param_types.STRING)},
                )
            ]
        )
        await self._purge()
        return archived, deleted

    async def housekeep(
        self,
        retention_ceiling_days: int,
        session_index_max_age_hours: int,
    ) -> dict[str, int]:
        from google.cloud.spanner_v1 import param_types

        dedup_cutoff_ms = _epoch_ms(datetime.now(UTC) - timedelta(days=retention_ceiling_days))
        stale_sessions = await self._query(
            "SELECT session_id FROM Events WHERE in_session_index GROUP BY session_id "
            "HAVING MAX(commit_ts) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)",
            {"hours": session_index_max_age_hours},
            {"hours": param_types.INT64},
        )
        session_ids = [row[0] for row in stale_sessions]
        dedup_removed, _ = await self._execute_updates(
            [
                (
                    "UPDATE Events SET dedup_active = FALSE "
                    "WHERE dedup_active AND occurred_at_ms <= @cutoff",
                    {"cutoff": dedup_cutoff_ms},
                    {"cutoff": param_types.INT64},
                ),
                (
                    "UPDATE Events SET in_session_index = FALSE "
                    "WHERE in_session_index AND session_id IN UNNEST(@sessions)",
                    {"sessions": session_ids},
                    {"sessions": param_types.Array(param_types.STRING)},
                ),
            ]
        )
        await self._purge()
        return {
            "dedup_entries_removed": dedup_removed,
            "session_streams_deleted": len(session_ids),
        }

    async def _purge(self) -> None:
        """Delete rows no structure needs any more (all four flags cleared)."""
        await self._execute_updates(
            [
                (
                    "DELETE FROM Events WHERE NOT in_log AND document IS NULL "
                    "AND NOT dedup_active AND NOT in_session_index",
                    {},
                    {},
                )
            ]
        )

    # -- test support -------------------------------------------------------

    async def set_document_fields(self, event_id: str, **fields: Any) -> None:
        """Add fields to a stored document; ``summary``/``keywords`` are indexed for search."""
        from google.cloud.spanner_v1 import KeySet

        def work(transaction: Any) -> None:
            (row,) = list(transaction.read("Events", ["document"], KeySet(keys=[[event_id]])))
            document = json_value(row[0]) or {}
            document.update(fields)
            transaction.update(
                "Events",
                ["event_id", "document", "summary", "keywords"],
                [
                    [
                        event_id,
                        json_param(document),
                        _text(document.get("summary")),
                        _text(document.get("keywords")),
                    ]
                ],
            )

        await self._run(self._database.run_in_transaction, work)
