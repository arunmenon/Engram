"""Redis EventStore adapter.

Implements the ``EventStore`` protocol using Redis Stack:
- **Streams** for the immutable event ledger (XADD via Lua)
- **JSON** for full event documents (JSON.SET / JSON.GET)
- **Search** for secondary index queries (FT.SEARCH)

All writes go through the Lua ingestion script for atomicity and dedup.
Tenant isolation via key prefixing: ``t:{tenant_id}:evt:{event_id}``.

Sources: ADR-0004, ADR-0010
"""

from __future__ import annotations

import asyncio
import importlib.resources
import time as _time
from datetime import UTC
from typing import TYPE_CHECKING, Any

import orjson
import structlog
from redis.asyncio import Redis

from context_graph.adapters.redis.indexes import ensure_event_index
from context_graph.domain.models import Event
from context_graph.metrics import (
    REDIS_MEMORY_FRAGMENTATION,
    REDIS_MEMORY_PEAK,
    REDIS_MEMORY_USED,
    REDIS_OP_DURATION,
    REDIS_POOL_IN_USE,
    REDIS_POOL_SIZE,
)

if TYPE_CHECKING:
    from context_graph.domain.models import EventQuery
    from context_graph.settings import RedisSettings

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LUA_SCRIPT_CACHE: str | None = None


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
    tenant_id: str = "default",
) -> bytes:
    """Serialize an event to JSON bytes with the epoch_ms field injected.

    When *payload* is provided it is stored alongside the event fields in the
    Redis JSON document.  ``Event.model_validate()`` silently ignores the extra
    key on read (``extra="ignore"``), so existing deserialization is unaffected.
    The ``tenant_id`` field is included for RediSearch TAG filtering.
    """
    data = orjson.loads(event.model_dump_json())
    data["occurred_at_epoch_ms"] = occurred_at_epoch_ms
    data["tenant_id"] = tenant_id
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
# Tenant key helpers
# ---------------------------------------------------------------------------


def _tenant_key(prefix: str, tenant_id: str) -> str:
    """Build a tenant-prefixed Redis key: ``t:{tenant_id}:{prefix}``."""
    return f"t:{tenant_id}:{prefix}"


def _tenant_event_key(base_prefix: str, event_id: str, tenant_id: str) -> str:
    """Build ``t:{tenant_id}:{base_prefix}{event_id}``."""
    return f"t:{tenant_id}:{base_prefix}{event_id}"


def _tenant_stream_key(stream_base: str, tenant_id: str) -> str:
    """Build ``t:{tenant_id}:{stream_base}``."""
    return f"t:{tenant_id}:{stream_base}"


def _tenant_session_stream(session_id: str, tenant_id: str) -> str:
    """Build ``t:{tenant_id}:events:session:{session_id}``."""
    return f"t:{tenant_id}:events:session:{session_id}"


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
            max_connections=settings.max_connections,
            socket_timeout=settings.socket_timeout,
            socket_connect_timeout=settings.socket_connect_timeout,
        )
        store = cls(client=client, settings=settings)
        await store._register_script()
        return store

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

    async def stream_length(self, tenant_id: str = "default") -> int:
        """Return the number of entries in the global event stream."""
        global_stream = _tenant_stream_key(self._settings.global_stream, tenant_id)
        result = await self._client.xlen(global_stream)
        return int(result)

    def _update_pool_metrics(self) -> None:
        """Update Redis connection pool gauges.

        Reads pool stats from the underlying connection pool (if available)
        and publishes them as Prometheus gauges.  Safe to call frequently;
        falls back silently when pool internals are unavailable.
        """
        try:
            pool = self._client.connection_pool
            pool_size = getattr(pool, "max_connections", 0)
            in_use = getattr(pool, "_created_connections", 0)
            REDIS_POOL_SIZE.set(pool_size)
            REDIS_POOL_IN_USE.set(in_use)
        except Exception:  # noqa: BLE001
            pass  # Non-critical metric

    async def close(self) -> None:
        """Release the Redis connection."""
        await self._client.aclose()
        log.info("redis_connection_closed")

    # -- write operations ---------------------------------------------------

    async def append(
        self,
        event: Event,
        payload: dict[str, Any] | None = None,
        tenant_id: str = "default",
    ) -> str:
        """Append a single event. Returns the global_position (stream entry ID).

        Idempotent: duplicate event_id submissions return the existing position.
        When *payload* is given it is persisted in the JSON document alongside
        the event fields so the extraction worker can access conversation content.
        """
        t0 = _time.monotonic()
        event_id_str = str(event.event_id)
        json_key = _tenant_event_key(self._settings.event_key_prefix, event_id_str, tenant_id)
        occurred_at_epoch_ms = _event_to_epoch_ms(event)
        event_json = _event_to_json_bytes(
            event, occurred_at_epoch_ms, payload=payload, tenant_id=tenant_id
        )

        if self._script_sha is None:
            await self._register_script()

        global_stream = _tenant_stream_key(self._settings.global_stream, tenant_id)
        session_stream_key = _tenant_session_stream(str(event.session_id), tenant_id)
        dedup_set = _tenant_key(self._settings.dedup_set, tenant_id)

        result = await self._client.evalsha(  # type: ignore[misc]
            self._script_sha,  # type: ignore[arg-type]
            4,  # number of KEYS
            global_stream,
            json_key,
            dedup_set,
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
        REDIS_OP_DURATION.labels(operation="append").observe(_time.monotonic() - t0)
        self._update_pool_metrics()
        log.debug(
            "event_appended",
            event_id=event_id_str,
            global_position=global_position,
            tenant_id=tenant_id,
        )
        return global_position

    async def append_batch(
        self,
        events: list[Event],
        payloads: list[dict[str, Any] | None] | None = None,
        tenant_id: str = "default",
    ) -> list[str]:
        """Append multiple events, choosing pipeline or concurrent strategy.

        For batches of 10 or fewer, uses a single Redis pipeline round-trip.
        For larger batches, delegates to ``append_batch_concurrent`` which
        uses a semaphore-bounded ``asyncio.gather`` to parallelize Lua
        EVALSHA calls across multiple connections.

        Each event is individually atomic via the Lua ingestion script.
        """
        if not events:
            return []

        # Large batches benefit from concurrent execution across pool connections
        if len(events) > 10:
            return await self.append_batch_concurrent(events, tenant_id=tenant_id)

        t0 = _time.monotonic()
        if self._script_sha is None:
            await self._register_script()

        global_stream = _tenant_stream_key(self._settings.global_stream, tenant_id)
        dedup_set = _tenant_key(self._settings.dedup_set, tenant_id)

        pipe = self._client.pipeline(transaction=False)
        for idx, event in enumerate(events):
            event_id_str = str(event.event_id)
            json_key = _tenant_event_key(self._settings.event_key_prefix, event_id_str, tenant_id)
            occurred_at_epoch_ms = _event_to_epoch_ms(event)
            event_payload = payloads[idx] if payloads and idx < len(payloads) else None
            event_json = _event_to_json_bytes(
                event,
                occurred_at_epoch_ms,
                payload=event_payload,
                tenant_id=tenant_id,
            )
            session_stream_key = _tenant_session_stream(str(event.session_id), tenant_id)

            pipe.evalsha(
                self._script_sha,  # type: ignore[arg-type]
                4,  # number of KEYS
                global_stream,
                json_key,
                dedup_set,
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

        REDIS_OP_DURATION.labels(operation="append_batch").observe(_time.monotonic() - t0)
        self._update_pool_metrics()
        log.debug("batch_appended", count=len(events), tenant_id=tenant_id)
        return positions

    async def append_batch_concurrent(
        self,
        events: list[Event],
        tenant_id: str = "default",
    ) -> list[str]:
        """Concurrent batch ingestion using semaphore for parallelism.

        Uses ``asyncio.Semaphore`` to limit the number of concurrent
        ``append()`` calls, distributing work across multiple Redis
        connections in the pool.  This is more effective than pipelining
        for very large batches where individual Lua EVALSHA calls are
        CPU-bound on the Redis server.
        """
        t0 = _time.monotonic()
        semaphore = asyncio.Semaphore(self._settings.batch_concurrency)

        async def _ingest_one(event: Event) -> str:
            async with semaphore:
                return await self.append(event, tenant_id=tenant_id)

        positions = list(await asyncio.gather(*[_ingest_one(e) for e in events]))
        REDIS_OP_DURATION.labels(operation="append_batch_concurrent").observe(
            _time.monotonic() - t0
        )
        self._update_pool_metrics()
        log.debug(
            "batch_concurrent_appended",
            count=len(events),
            concurrency=self._settings.batch_concurrency,
            tenant_id=tenant_id,
        )
        return positions

    async def cleanup_dedup_set(
        self,
        retention_ms: int | None = None,
        tenant_id: str = "default",
    ) -> int:
        """Remove old entries from the dedup sorted set.

        Removes entries with scores (epoch_ms) older than retention_ms.
        Defaults to retention_ceiling_days converted to ms.
        Returns the number of removed entries.
        """
        if retention_ms is None:
            retention_ms = self._settings.retention_ceiling_days * 86_400_000

        now_ms = int(_time.time() * 1000)
        cutoff_ms = now_ms - retention_ms
        dedup_set = _tenant_key(self._settings.dedup_set, tenant_id)

        removed: int = await self._client.zremrangebyscore(
            dedup_set,
            "-inf",
            cutoff_ms,
        )
        log.info(
            "dedup_set_cleaned",
            removed=removed,
            cutoff_ms=cutoff_ms,
            tenant_id=tenant_id,
        )
        return removed

    # -- read operations ----------------------------------------------------

    async def get_by_id(self, event_id: str, tenant_id: str = "default") -> Event | None:
        """Retrieve a single event by its event_id."""
        t0 = _time.monotonic()
        json_key = _tenant_event_key(self._settings.event_key_prefix, event_id, tenant_id)
        raw = await self._client.execute_command("JSON.GET", json_key, "$")  # type: ignore[no-untyped-call]
        REDIS_OP_DURATION.labels(operation="get_by_id").observe(_time.monotonic() - t0)
        self._update_pool_metrics()
        if raw is None:
            return None

        raw_str = raw.decode() if isinstance(raw, bytes) else raw
        # JSON.GET with $ path returns a JSON array
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) and len(parsed) > 0 else parsed
        doc.pop("occurred_at_epoch_ms", None)
        doc.pop("tenant_id", None)
        return Event.model_validate(doc, strict=False)

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 100,
        after: str | None = None,
        tenant_id: str = "default",
    ) -> list[Event]:
        """Retrieve events for a session, ordered by occurred_at ascending.

        Uses FT.SEARCH with TAG filter and SORTBY occurred_at_epoch_ms.
        The ``after`` parameter is used as a pagination offset index.
        """
        escaped_session = _escape_tag_value(session_id)
        escaped_tenant = _escape_tag_value(tenant_id)
        query_str = f"@tenant_id:{{{escaped_tenant}}} @session_id:{{{escaped_session}}}"

        offset = 0
        if after is not None:
            try:
                offset = int(after)
            except ValueError:
                offset = 0

        return await self._ft_search(query_str, limit=limit, offset=offset)

    async def search(self, query: EventQuery, tenant_id: str = "default") -> list[Event]:
        """Search events using composite RediSearch filters."""
        escaped_tenant = _escape_tag_value(tenant_id)
        filters: list[str] = [f"@tenant_id:{{{escaped_tenant}}}"]

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

        query_str = " ".join(filters)
        return await self._ft_search(query_str, limit=query.limit, offset=query.offset)

    async def search_bm25(
        self,
        query_text: str,
        session_id: str | None = None,
        limit: int = 50,
        tenant_id: str = "default",
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

        # Build query: tenant filter + full-text search on summary/keywords
        escaped_tenant = _escape_tag_value(tenant_id)
        parts: list[str] = [
            f"@tenant_id:{{{escaped_tenant}}}",
            sanitized,
        ]
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
                doc.pop("tenant_id", None)
                events.append(Event.model_validate(doc, strict=False))

        return events

    # -- memory monitoring ---------------------------------------------------

    async def get_memory_info(self) -> dict[str, Any]:
        """Return Redis memory usage information.

        Calls ``INFO memory`` and returns a normalized dict with key
        memory metrics.  The ``used_memory_pct`` field is 0 when
        ``maxmemory`` is not configured (0).
        """
        info = await self._client.info("memory")
        used = info.get("used_memory", 0)
        peak = info.get("used_memory_peak", 0)
        maxmem = info.get("maxmemory", 0)
        fragmentation = info.get("mem_fragmentation_ratio", 0.0)
        pct = (used / maxmem * 100) if maxmem else 0.0

        # Update Prometheus gauges
        REDIS_MEMORY_USED.set(used)
        REDIS_MEMORY_PEAK.set(peak)
        REDIS_MEMORY_FRAGMENTATION.set(fragmentation)

        return {
            "used_memory_bytes": used,
            "used_memory_peak_bytes": peak,
            "maxmemory_bytes": maxmem,
            "mem_fragmentation_ratio": fragmentation,
            "used_memory_pct": pct,
        }

    async def is_memory_pressure(self) -> bool:
        """Return True when Redis memory usage exceeds the configured threshold.

        Returns False when ``maxmemory`` is 0 (uncapped), because there is
        no ceiling to measure against.
        """
        mem_info = await self.get_memory_info()
        if mem_info["maxmemory_bytes"] == 0:
            return False
        return bool(mem_info["used_memory_pct"] > self._settings.memory_pressure_threshold_pct)

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
                doc.pop("tenant_id", None)
                events.append(Event.model_validate(doc, strict=False))

        return events
