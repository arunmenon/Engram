"""Redis EventStore adapter.

Implements the ``EventStore`` protocol using Redis Stack:
- **Streams** for the immutable event ledger (XADD via Lua)
- **JSON** for full event documents (JSON.SET / JSON.GET)
- **Search** for secondary index queries (FT.SEARCH)

All writes go through the Lua ingestion script for atomicity and dedup.

Sources: ADR-0004, ADR-0010
"""

from __future__ import annotations

import importlib.resources
from datetime import UTC
from typing import TYPE_CHECKING, Any

import orjson
import structlog
from redis.asyncio import Redis

from context_graph.adapters.redis.indexes import ensure_event_index
from context_graph.domain.models import Event

if TYPE_CHECKING:
    from context_graph.domain.models import EventQuery
    from context_graph.settings import RedisSettings

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LUA_SCRIPT_CACHE: str | None = None

# Per-session stream key prefix written by the ingest Lua script.
_SESSION_STREAM_PREFIX = "events:session:"


def _load_lua_script() -> str:
    """Load the ingest.lua script from package resources."""
    global _LUA_SCRIPT_CACHE  # noqa: PLW0603
    if _LUA_SCRIPT_CACHE is None:
        lua_path = importlib.resources.files("context_graph.adapters.redis.lua").joinpath(
            "ingest.lua"
        )
        _LUA_SCRIPT_CACHE = lua_path.read_text(encoding="utf-8")
    return _LUA_SCRIPT_CACHE


def _escape_tag_value(value: str) -> str:
    """Escape special characters in a RediSearch TAG value.

    RediSearch TAG fields need hyphens, dots, and other punctuation escaped
    with a backslash so they are treated as literal characters.
    """
    special_chars = r".,<>{}[]\"':;!@#$%^&*()-+=~/ "
    escaped = []
    for char in value:
        if char in special_chars:
            escaped.append("\\")
        escaped.append(char)
    return "".join(escaped)


def _event_to_epoch_ms(event: Event) -> int:
    """Convert the event's occurred_at to milliseconds since epoch."""
    timestamp = event.occurred_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return int(timestamp.timestamp() * 1000)


def _event_to_json_bytes(
    event: Event,
    occurred_at_epoch_ms: int,
    payload: dict[str, Any] | None = None,
) -> bytes:
    """Serialize an event to JSON bytes with the epoch_ms field injected.

    When *payload* is provided it is stored alongside the event fields in the
    Redis JSON document.  ``Event.model_validate()`` silently ignores the extra
    key on read (``extra="ignore"``), so existing deserialization is unaffected.
    """
    data = orjson.loads(event.model_dump_json())
    data["occurred_at_epoch_ms"] = occurred_at_epoch_ms
    if payload is not None:
        data["payload"] = payload
    return orjson.dumps(data)


def _deserialize_event(raw_json: bytes | str) -> Event:
    """Deserialize a JSON blob into an Event, stripping adapter-only fields."""
    raw_bytes = raw_json.encode() if isinstance(raw_json, str) else raw_json
    data = orjson.loads(raw_bytes)
    # Remove the adapter-only epoch_ms field before Pydantic validation
    data.pop("occurred_at_epoch_ms", None)
    # strict=False allows coercion from JSON string types (UUID, datetime)
    return Event.model_validate(data, strict=False)


# ---------------------------------------------------------------------------
# RedisEventStore
# ---------------------------------------------------------------------------


class RedisEventStore:
    """EventStore implementation backed by Redis Stack.

    Satisfies the ``context_graph.ports.event_store.EventStore`` protocol.
    """

    def __init__(self, client: Redis, settings: RedisSettings) -> None:
        self._client = client
        self._settings = settings
        self._script_sha: str | None = None

    # -- lifecycle ----------------------------------------------------------

    @classmethod
    async def create(cls, settings: RedisSettings) -> RedisEventStore:
        """Factory: create a connected store from settings."""
        client = Redis(
            host=settings.host,
            port=settings.port,
            db=settings.db,
            password=settings.password.get_secret_value() if settings.password else None,
            decode_responses=False,
        )
        store = cls(client=client, settings=settings)
        await store._register_script()
        return store

    @property
    def client(self) -> Redis:
        """The Redis connection, shared with subscriptions by the registry (ADR-0019)."""
        return self._client

    async def _register_script(self) -> None:
        """Load and register the Lua ingestion script with Redis."""
        lua_source = _load_lua_script()
        self._script_sha = await self._client.script_load(lua_source)
        log.info("lua_script_registered", sha=self._script_sha)

    async def ensure_indexes(self) -> None:
        """Create the RediSearch index if it does not exist."""
        await ensure_event_index(
            self._client,
            self._settings.event_index,
            self._settings.event_key_prefix,
        )

    async def health_ping(self) -> bool:
        """Return True if Redis is reachable."""
        try:
            result = await self._client.ping()  # type: ignore[misc]
            return bool(result)
        except Exception:
            return False

    async def stream_length(self) -> int:
        """Return the number of entries in the global event stream."""
        result = await self._client.xlen(self._settings.global_stream)
        return int(result)

    async def close(self) -> None:
        """Release the Redis connection."""
        await self._client.aclose()
        log.info("redis_connection_closed")

    # -- write operations ---------------------------------------------------

    async def append(
        self,
        event: Event,
        payload: dict[str, Any] | None = None,
    ) -> str:
        """Append a single event. Returns the global_position (stream entry ID).

        Idempotent: duplicate event_id submissions return the existing position.
        When *payload* is given it is persisted in the JSON document alongside
        the event fields so the extraction worker can access conversation content.
        """
        event_id_str = str(event.event_id)
        json_key = f"{self._settings.event_key_prefix}{event_id_str}"
        occurred_at_epoch_ms = _event_to_epoch_ms(event)
        event_json = _event_to_json_bytes(event, occurred_at_epoch_ms, payload=payload)

        if self._script_sha is None:
            await self._register_script()

        session_stream_key = f"events:session:{event.session_id}"
        result = await self._client.evalsha(  # type: ignore[misc]
            self._script_sha,  # type: ignore[arg-type]
            4,  # number of KEYS
            self._settings.global_stream,
            json_key,
            self._settings.dedup_set,
            session_stream_key,
            event_id_str,
            event_json,
            str(occurred_at_epoch_ms),
            str(self._settings.global_stream_maxlen),
        )

        # Conditional WAIT for replica acknowledgment
        if self._settings.replica_wait:
            await self._client.execute_command("WAIT", 1, 100)  # type: ignore[no-untyped-call]

        global_position = result.decode() if isinstance(result, bytes) else str(result)
        log.debug(
            "event_appended",
            event_id=event_id_str,
            global_position=global_position,
        )
        return global_position

    async def append_batch(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
    ) -> list[str]:
        """Append multiple events in a single Redis pipeline round-trip.

        Each event is individually atomic via the Lua ingestion script.
        Pipelining reduces batch latency from O(n * RTT) to O(RTT).
        """
        if not events:
            return []

        if self._script_sha is None:
            await self._register_script()

        pipe = self._client.pipeline(transaction=False)
        for idx, event in enumerate(events):
            event_id_str = str(event.event_id)
            json_key = f"{self._settings.event_key_prefix}{event_id_str}"
            occurred_at_epoch_ms = _event_to_epoch_ms(event)
            event_payload = payloads[idx] if payloads and idx < len(payloads) else None
            event_json = _event_to_json_bytes(event, occurred_at_epoch_ms, payload=event_payload)
            session_stream_key = f"events:session:{event.session_id}"

            pipe.evalsha(
                self._script_sha,  # type: ignore[arg-type]
                4,  # number of KEYS
                self._settings.global_stream,
                json_key,
                self._settings.dedup_set,
                session_stream_key,
                event_id_str,
                event_json,
                str(occurred_at_epoch_ms),
                str(self._settings.global_stream_maxlen),
            )

        results = await pipe.execute()

        positions: list[str] = []
        for result in results:
            global_position = result.decode() if isinstance(result, bytes) else str(result)
            positions.append(global_position)

        log.debug("batch_appended", count=len(events))
        return positions

    async def cleanup_dedup_set(self, retention_ms: int | None = None) -> int:
        """Remove old entries from the dedup sorted set.

        Removes entries with scores (epoch_ms) older than retention_ms.
        Defaults to retention_ceiling_days converted to ms.
        Returns the number of removed entries.
        """
        if retention_ms is None:
            retention_ms = self._settings.retention_ceiling_days * 86_400_000

        import time

        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - retention_ms

        removed: int = await self._client.zremrangebyscore(
            self._settings.dedup_set,
            "-inf",
            cutoff_ms,
        )
        log.info(
            "dedup_set_cleaned",
            removed=removed,
            cutoff_ms=cutoff_ms,
        )
        return removed

    # -- read operations ----------------------------------------------------

    async def get_by_id(self, event_id: str) -> Event | None:
        """Retrieve a single event by its event_id."""
        json_key = f"{self._settings.event_key_prefix}{event_id}"
        raw = await self._client.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
        if raw is None:
            return None

        raw_str = raw.decode() if isinstance(raw, bytes) else raw
        # JSON.GET with $ path returns a JSON array
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
        doc.pop("occurred_at_epoch_ms", None)
        return Event.model_validate(doc, strict=False)

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        after: str | None = None,
    ) -> list[Event]:
        """Retrieve events for a session, ordered by occurred_at ascending.

        Uses FT.SEARCH with TAG filter and SORTBY occurred_at_epoch_ms.
        The ``after`` parameter is used as a pagination offset index.
        """
        escaped_session = _escape_tag_value(session_id)
        query_str = f"@session_id:{{{escaped_session}}}"

        offset = 0
        if after is not None:
            # `after` is treated as a numeric offset for FT.SEARCH pagination
            try:
                offset = int(after)
            except ValueError:
                offset = 0

        return await self._ft_search(query_str, limit=limit, offset=offset)

    async def search(self, query: EventQuery) -> list[Event]:
        """Search events using composite RediSearch filters."""
        filters: list[str] = []

        if query.session_id:
            filters.append(f"@session_id:{{{_escape_tag_value(query.session_id)}}}")
        if query.agent_id:
            filters.append(f"@agent_id:{{{_escape_tag_value(query.agent_id)}}}")
        if query.trace_id:
            filters.append(f"@trace_id:{{{_escape_tag_value(query.trace_id)}}}")
        if query.event_type:
            filters.append(f"@event_type:{{{_escape_tag_value(query.event_type)}}}")
        if query.tool_name:
            filters.append(f"@tool_name:{{{_escape_tag_value(query.tool_name)}}}")

        # Time range filters on occurred_at_epoch_ms
        if query.after or query.before:
            after_ms = "-inf"
            before_ms = "+inf"
            if query.after:
                ts = query.after
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                after_ms = str(int(ts.timestamp() * 1000))
            if query.before:
                ts = query.before
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                before_ms = str(int(ts.timestamp() * 1000))
            filters.append(f"@occurred_at_epoch_ms:[{after_ms} {before_ms}]")

        query_str = " ".join(filters) if filters else "*"
        return await self._ft_search(query_str, limit=query.limit, offset=query.offset)

    async def search_bm25(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[Event]:
        """Full-text search events using RediSearch BM25 scoring.

        Searches across the ``summary`` and ``keywords`` text fields.
        Optionally filters by session_id. Results are ordered by BM25
        relevance (RediSearch default for text queries).
        """
        if not query_text or not query_text.strip():
            return []

        # Sanitize query text for RediSearch: escape special chars
        sanitized = query_text.strip()
        for ch in r"@{}\[]()|-!~*:^/\"'<>=;,$&+":
            sanitized = sanitized.replace(ch, f"\\{ch}")

        # Build query: full-text search on summary/keywords
        parts: list[str] = [sanitized]
        if session_id:
            escaped_session = _escape_tag_value(session_id)
            parts.append(f"@session_id:{{{escaped_session}}}")

        query_str = " ".join(parts)

        # Use FT.SEARCH with SCORER BM25 (default) — no SORTBY so results
        # are ordered by relevance score.
        index_name = self._settings.event_index
        raw_result = await self._client.execute_command(  # type: ignore[no-untyped-call]
            "FT.SEARCH",
            index_name,
            query_str,
            "LIMIT",
            "0",
            str(limit),
        )

        if not raw_result or raw_result[0] == 0:
            return []

        events: list[Event] = []
        idx = 1
        while idx < len(raw_result) - 1:
            _key = raw_result[idx]
            fields = raw_result[idx + 1]
            idx += 2

            json_doc = None
            for field_idx in range(0, len(fields) - 1, 2):
                field_name = fields[field_idx]
                if isinstance(field_name, bytes):
                    field_name = field_name.decode()
                if field_name == "$":
                    json_doc = fields[field_idx + 1]
                    break

            if json_doc is not None:
                if isinstance(json_doc, bytes):
                    json_doc = json_doc.decode()
                parsed = orjson.loads(json_doc)
                doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
                doc.pop("occurred_at_epoch_ms", None)
                events.append(Event.model_validate(doc, strict=False))

        return events

    # -- internal search helper ---------------------------------------------

    async def _ft_search(
        self,
        query_str: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        """Execute an FT.SEARCH query and return deserialized Events."""
        index_name = self._settings.event_index

        # Build raw FT.SEARCH command for full control over SORTBY/LIMIT
        raw_result = await self._client.execute_command(  # type: ignore[no-untyped-call]
            "FT.SEARCH",
            index_name,
            query_str,
            "SORTBY",
            "occurred_at_epoch_ms",
            "ASC",
            "LIMIT",
            str(offset),
            str(limit),
        )

        # FT.SEARCH returns: [total_count, key1, fields1, key2, fields2, ...]
        if not raw_result or raw_result[0] == 0:
            return []

        events: list[Event] = []
        # Iterate pairs of (key, fields) starting at index 1
        idx = 1
        while idx < len(raw_result) - 1:
            _key = raw_result[idx]
            fields = raw_result[idx + 1]
            idx += 2

            # fields is a list of alternating [field_name, value, ...]
            # For JSON index, the document is at the "$" key
            json_doc = None
            for field_idx in range(0, len(fields) - 1, 2):
                field_name = fields[field_idx]
                if isinstance(field_name, bytes):
                    field_name = field_name.decode()
                if field_name == "$":
                    json_doc = fields[field_idx + 1]
                    break

            if json_doc is not None:
                if isinstance(json_doc, bytes):
                    json_doc = json_doc.decode()
                # The "$" field from JSON index is a JSON array with one element
                parsed = orjson.loads(json_doc)
                doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
                doc.pop("occurred_at_epoch_ms", None)
                events.append(Event.model_validate(doc, strict=False))

        return events

    # -- EventLog reads for workers (ADR-0019) -----------------------------

    async def get_documents(self, event_ids: list[str]) -> list[dict[str, Any] | None]:
        """Return the stored JSON document for each id, in the order given.

        Issues one ``JSON.GET`` per id, as the workers did before reading
        through the port. The adapter-only ``occurred_at_epoch_ms`` field
        is removed; ``payload`` is kept when stored.
        """
        documents: list[dict[str, Any] | None] = []
        for event_id in event_ids:
            json_key = f"{self._settings.event_key_prefix}{event_id}"
            raw_json = await self._client.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
            if raw_json is None:
                documents.append(None)
                continue
            raw_str = raw_json.decode() if isinstance(raw_json, bytes) else raw_json
            parsed = orjson.loads(raw_str)
            doc: dict[str, Any] = (
                parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
            )
            doc.pop("occurred_at_epoch_ms", None)
            documents.append(doc)
        return documents

    async def read_session_ids(self, session_id: str) -> list[str]:
        """Return a session's event ids in order from its per-session stream."""
        session_stream_key = f"{_SESSION_STREAM_PREFIX}{session_id}"
        entries: Any = await self._client.xrange(session_stream_key, min="-", max="+")
        event_ids: list[str] = []
        for _entry_id, entry_data in entries:
            raw_event_id = entry_data.get(b"event_id", entry_data.get("event_id"))
            if not raw_event_id:
                continue
            event_ids.append(
                raw_event_id.decode() if isinstance(raw_event_id, bytes) else str(raw_event_id)
            )
        return event_ids

    # -- EventLog hot-tier retention (ADR-0014, ADR-0019) ------------------

    async def trim(self, max_age_days: int, consumer_groups: list[str]) -> int:
        """Trim the global stream's hot window, keeping entries pending for any group."""
        from context_graph.adapters.redis.trimmer import trim_stream

        return await trim_stream(
            redis_client=self._client,
            stream_key=self._settings.global_stream,
            max_age_days=max_age_days,
            consumer_groups=consumer_groups,
        )

    async def expire(
        self,
        max_age_days: int,
        archive_store: Any = None,
    ) -> tuple[int, int]:
        """Delete expired JSON documents, archiving them first when an archive is given."""
        from context_graph.adapters.redis.trimmer import (
            archive_and_delete_expired_events,
            delete_expired_events,
        )

        if archive_store is not None:
            return await archive_and_delete_expired_events(
                redis_client=self._client,
                key_prefix=self._settings.event_key_prefix,
                max_age_days=max_age_days,
                archive_store=archive_store,
            )
        deleted = await delete_expired_events(
            redis_client=self._client,
            key_prefix=self._settings.event_key_prefix,
            max_age_days=max_age_days,
        )
        return 0, deleted

    async def housekeep(
        self,
        retention_ceiling_days: int,
        session_index_max_age_hours: int,
    ) -> dict[str, int]:
        """Clean the dedup sorted set and stale per-session streams."""
        from context_graph.adapters.redis.trimmer import (
            cleanup_dedup_set,
            cleanup_session_streams,
        )

        dedup_removed = await cleanup_dedup_set(
            redis_client=self._client,
            dedup_key=self._settings.dedup_set,
            retention_ceiling_days=retention_ceiling_days,
        )
        session_streams_deleted = await cleanup_session_streams(
            redis_client=self._client,
            prefix=_SESSION_STREAM_PREFIX,
            max_age_hours=session_index_max_age_hours,
        )
        return {
            "dedup_entries_removed": dedup_removed,
            "session_streams_deleted": session_streams_deleted,
        }
