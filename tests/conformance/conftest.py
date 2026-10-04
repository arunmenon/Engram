"""Backend harnesses for the storage conformance suites (ADR-0019 §5).

Every suite runs against each registered backend of its port:

- ``memory``: always (the reference backend);
- ``redis`` / ``neo4j``: marked ``integration``; skipped when the service
  is unreachable. Redis event-log suites need Redis Stack (RedisJSON and
  RediSearch); the subscription suite needs only Redis Streams.

Connection settings come from the usual ``CG_REDIS_*`` / ``CG_NEO4J_*``
variables. Redis harnesses use per-test key prefixes and clean up after
themselves. The Neo4j harness empties the database before and after each
test, as the existing integration tests do: never point it at data you
want to keep.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import orjson
import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from context_graph.ports.event_log import EventLog
    from context_graph.ports.graph_backend import GraphBackend
    from context_graph.ports.search import KeywordIndex
    from context_graph.ports.subscription import Subscription

# ---------------------------------------------------------------------------
# Service probes
# ---------------------------------------------------------------------------


# Probe results per session, so an unreachable service costs one timeout.
_SKIP_REASONS: dict[str, str | None] = {}

# CI sets this in the job that provides Redis Stack and Neo4j, so a missing
# service fails the run instead of silently skipping its backend.
REQUIRE_SERVICES = os.environ.get("CG_CONFORMANCE_REQUIRE_SERVICES") == "1"


def _skip(reason: str) -> None:
    if REQUIRE_SERVICES:
        pytest.fail(f"{reason} (CG_CONFORMANCE_REQUIRE_SERVICES=1)")
    pytest.skip(reason)


async def _redis_client_or_skip(*, need_stack: bool) -> Any:
    probe = "redis-stack" if need_stack else "redis"
    if _SKIP_REASONS.get(probe):
        _skip(_SKIP_REASONS[probe])  # type: ignore[arg-type]
    try:
        client = await _redis_client(need_stack=need_stack)
    except pytest.skip.Exception as skipped:
        _SKIP_REASONS[probe] = str(skipped)
        raise
    _SKIP_REASONS[probe] = None
    return client


async def _redis_client(*, need_stack: bool) -> Any:
    from redis.asyncio import Redis

    from context_graph.settings import RedisSettings

    settings = RedisSettings()
    client = Redis(
        host=settings.host,
        port=settings.port,
        db=settings.db,
        password=settings.password.get_secret_value() if settings.password else None,
        decode_responses=False,
        socket_connect_timeout=1,
    )
    try:
        await client.ping()
        if need_stack:
            modules = await client.execute_command("MODULE", "LIST")
            names = {
                (m[1] if isinstance(m, list) else m.get(b"name", b"")).decode().lower()
                for m in modules
            }
            has_json = any("json" in name for name in names)
            if not (has_json and "search" in names):
                await client.aclose()
                _skip("Redis is reachable but lacks RedisJSON/RediSearch (needs Redis Stack)")
    except pytest.skip.Exception:
        raise
    except Exception as exc:  # noqa: BLE001
        await client.aclose()
        _skip(f"Redis unreachable: {exc}")
    return client


async def _spanner_database_or_skip() -> tuple[Any, Any]:
    """A fresh database on the Spanner emulator, or skip.

    Only the emulator is used (``CG_SPANNER_EMULATOR_HOST`` or
    ``SPANNER_EMULATOR_HOST``): the suites create and drop databases.
    """
    if _SKIP_REASONS.get("spanner"):
        _skip(_SKIP_REASONS["spanner"])  # type: ignore[arg-type]
    from context_graph.settings import SpannerSettings

    emulator = os.environ.get("CG_SPANNER_EMULATOR_HOST") or os.environ.get("SPANNER_EMULATOR_HOST")
    if not emulator:
        _SKIP_REASONS["spanner"] = "Spanner emulator not configured (CG_SPANNER_EMULATOR_HOST)"
        _skip(_SKIP_REASONS["spanner"])
    try:
        import google.cloud.spanner  # noqa: F401
    except ImportError:
        _SKIP_REASONS["spanner"] = "google-cloud-spanner not installed (pip install .[spanner])"
        _skip(_SKIP_REASONS["spanner"])

    from context_graph.adapters.spanner.schema import open_database

    settings = SpannerSettings(
        emulator_host=emulator,
        database=f"conf{uuid.uuid4().hex[:12]}",
        create_if_missing=True,
    )
    try:
        database = await asyncio.wait_for(asyncio.to_thread(open_database, settings), timeout=60)
    except Exception as exc:  # noqa: BLE001
        _SKIP_REASONS["spanner"] = f"Spanner emulator unreachable: {exc}"
        _skip(_SKIP_REASONS["spanner"])
    return database, settings


async def _drop_spanner_database(database: Any) -> None:
    with contextlib.suppress(Exception):
        await asyncio.to_thread(database.drop)


# ---------------------------------------------------------------------------
# Event log harness
# ---------------------------------------------------------------------------


@dataclass
class LogHarness:
    """An EventLog plus the hooks the suite needs around it."""

    backend: str
    log: EventLog
    open_subscription: Callable[[str, str], Subscription]
    set_document_fields: Callable[[str, dict[str, Any]], Awaitable[None]]
    keyword_index: KeywordIndex | None = None

    def __post_init__(self) -> None:
        if self.keyword_index is None:
            from context_graph.adapters.search import EventStoreKeywordIndex

            self.keyword_index = EventStoreKeywordIndex(self.log)


@pytest.fixture(
    params=[
        "memory",
        pytest.param("redis", marks=pytest.mark.integration),
        pytest.param("spanner", marks=pytest.mark.integration),
    ],
)
async def log_harness(request: pytest.FixtureRequest) -> AsyncIterator[LogHarness]:
    if request.param == "spanner":
        database, spanner_settings = await _spanner_database_or_skip()
        from context_graph.adapters.spanner.log import SpannerEventLog
        from context_graph.adapters.spanner.search import SpannerKeywordIndex
        from context_graph.adapters.spanner.subscription import SpannerSubscription

        spanner_log = SpannerEventLog(database, shards=spanner_settings.shards)

        async def set_spanner_fields(event_id: str, fields: dict[str, Any]) -> None:
            await spanner_log.set_document_fields(event_id, **fields)

        try:
            yield LogHarness(
                backend="spanner",
                log=spanner_log,
                open_subscription=lambda group, consumer: SpannerSubscription(
                    database, group, consumer, shards=spanner_settings.shards
                ),
                set_document_fields=set_spanner_fields,
                keyword_index=SpannerKeywordIndex(spanner_log),
            )
        finally:
            await _drop_spanner_database(database)
        return

    if request.param == "memory":
        from context_graph.adapters.memory.log import MemoryEventLog
        from context_graph.adapters.memory.subscription import MemorySubscription

        memory_log = MemoryEventLog()

        async def set_memory_fields(event_id: str, fields: dict[str, Any]) -> None:
            memory_log.set_document_fields(event_id, **fields)

        yield LogHarness(
            backend="memory",
            log=memory_log,
            open_subscription=lambda group, consumer: MemorySubscription(
                memory_log.stream, group, consumer
            ),
            set_document_fields=set_memory_fields,
        )
        return

    from context_graph.adapters.redis.store import RedisEventStore
    from context_graph.adapters.redis.subscription import RedisStreamSubscription
    from context_graph.settings import RedisSettings

    client = await _redis_client_or_skip(need_stack=True)
    run = uuid.uuid4().hex[:10]
    settings = RedisSettings(
        global_stream=f"conf:{run}:events",
        dedup_set=f"conf:{run}:dedup",
        event_key_prefix=f"conf:{run}:evt:",
        event_index=f"conf-{run}-idx",
    )
    store = RedisEventStore(client=client, settings=settings)
    await store.ensure_indexes()

    async def set_redis_fields(event_id: str, fields: dict[str, Any]) -> None:
        key = f"{settings.event_key_prefix}{event_id}"
        for name, value in fields.items():
            await client.execute_command("JSON.SET", key, f"$.{name}", orjson.dumps(value))

    try:
        yield LogHarness(
            backend="redis",
            log=store,
            open_subscription=lambda group, consumer: RedisStreamSubscription(
                client, group, consumer, settings.global_stream
            ),
            set_document_fields=set_redis_fields,
        )
    finally:
        with contextlib.suppress(Exception):
            await client.execute_command("FT.DROPINDEX", settings.event_index)
        async for key in client.scan_iter(match=f"conf:{run}:*"):
            await client.delete(key)
        await client.aclose()


# ---------------------------------------------------------------------------
# Subscription harness
# ---------------------------------------------------------------------------


@dataclass
class SubscriptionHarness:
    """A stream to publish to and subscriptions over it."""

    backend: str
    publish: Callable[[dict[str, str]], Awaitable[str]]
    open: Callable[..., Subscription]
    dead_letters: Callable[[], Awaitable[list[dict[str, str]]]]
    cleanup: list[Callable[[], Awaitable[None]]] = field(default_factory=list)


@pytest.fixture(
    params=[
        "memory",
        pytest.param("redis", marks=pytest.mark.integration),
        pytest.param("spanner", marks=pytest.mark.integration),
    ],
)
async def subscription_harness(
    request: pytest.FixtureRequest,
) -> AsyncIterator[SubscriptionHarness]:
    if request.param == "spanner":
        database, spanner_settings = await _spanner_database_or_skip()
        from context_graph.adapters.spanner.log import SpannerEventLog
        from context_graph.adapters.spanner.subscription import SpannerSubscription

        ledger = SpannerEventLog(database, shards=spanner_settings.shards)
        opened: list[SpannerSubscription] = []

        async def spanner_publish(fields: dict[str, str]) -> str:
            # Each item gets its own session, so items spread over shards
            event_id = fields["event_id"]
            return await ledger.append_entry(event_id, session_id=f"session-{event_id}")

        def spanner_open(group: str, consumer: str, claim_idle_ms: int = 300_000) -> Subscription:
            subscription = SpannerSubscription(
                database,
                group,
                consumer,
                shards=spanner_settings.shards,
                claim_idle_ms=claim_idle_ms,
                poll_interval_ms=spanner_settings.poll_interval_ms,
            )
            opened.append(subscription)
            return subscription

        async def spanner_dead_letters() -> list[dict[str, str]]:
            letters: list[dict[str, str]] = []
            for group in sorted({s.group_name for s in opened}):
                letters.extend(await spanner_open(group, "reader").dead_letters())  # type: ignore[attr-defined]
            return letters

        try:
            yield SubscriptionHarness(
                backend="spanner",
                publish=spanner_publish,
                open=spanner_open,
                dead_letters=spanner_dead_letters,
            )
        finally:
            await _drop_spanner_database(database)
        return

    if request.param == "memory":
        from context_graph.adapters.memory.stream import MemoryStream
        from context_graph.adapters.memory.subscription import MemorySubscription

        stream = MemoryStream("conformance")

        async def memory_dead_letters() -> list[dict[str, str]]:
            return list(stream.dead_letters)

        yield SubscriptionHarness(
            backend="memory",
            publish=stream.append,
            open=lambda group, consumer, claim_idle_ms=300_000: MemorySubscription(
                stream, group, consumer, claim_idle_ms=claim_idle_ms
            ),
            dead_letters=memory_dead_letters,
        )
        return

    from context_graph.adapters.redis.subscription import RedisStreamSubscription

    client = await _redis_client_or_skip(need_stack=False)
    stream_key = f"conf:{uuid.uuid4().hex[:10]}:stream"

    async def redis_publish(fields: dict[str, str]) -> str:
        position = await client.xadd(stream_key, fields)
        return position.decode() if isinstance(position, bytes) else str(position)

    async def redis_dead_letters() -> list[dict[str, str]]:
        entries = await client.xrange(f"{stream_key}:dlq")
        return [{k.decode(): v.decode() for k, v in data.items()} for _id, data in entries]

    try:
        yield SubscriptionHarness(
            backend="redis",
            publish=redis_publish,
            open=lambda group, consumer, claim_idle_ms=300_000: RedisStreamSubscription(
                client, group, consumer, stream_key, claim_idle_ms=claim_idle_ms
            ),
            dead_letters=redis_dead_letters,
        )
    finally:
        await client.delete(stream_key, f"{stream_key}:dlq")
        await client.aclose()


# ---------------------------------------------------------------------------
# Graph harness
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=[
        "memory",
        pytest.param("neo4j", marks=pytest.mark.integration),
        pytest.param("spanner", marks=pytest.mark.integration),
    ],
)
async def graph(request: pytest.FixtureRequest) -> AsyncIterator[GraphBackend]:
    if request.param == "spanner":
        database, spanner_settings = await _spanner_database_or_skip()
        from context_graph.adapters.spanner.graph import SpannerGraphStore

        try:
            yield SpannerGraphStore(
                database, embedding_dimensions=spanner_settings.embedding_dimensions
            )
        finally:
            await _drop_spanner_database(database)
        return

    if request.param == "memory":
        from context_graph.adapters.memory.graph import MemoryGraphStore

        yield MemoryGraphStore()
        return

    from context_graph.adapters.neo4j.store import Neo4jGraphStore
    from context_graph.settings import Neo4jSettings

    if _SKIP_REASONS.get("neo4j"):
        _skip(_SKIP_REASONS["neo4j"])  # type: ignore[arg-type]
    store = Neo4jGraphStore(Neo4jSettings())
    try:
        reachable = await asyncio.wait_for(store.health_ping(), timeout=5)
    except TimeoutError:
        reachable = False
    if not reachable:
        await store.close()
        _SKIP_REASONS["neo4j"] = "Neo4j unreachable"
        _skip(_SKIP_REASONS["neo4j"])
    await store.ensure_constraints()
    await store.delete_all(confirm=True)
    try:
        yield store
    finally:
        await store.delete_all(confirm=True)
        await store.close()
