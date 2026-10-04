"""Storage backend registry (ADR-0019).

Composition roots (``api/app.py``, ``worker/__main__.py``) open stores
here and never import an adapter by name. Backends are chosen by
``StorageSettings`` (``CG_STORAGE_*``); each port maps backend names to an
opener. Unknown names fail at start-up with the supported list.

Today's backends are registered: Redis for the event log, subscriptions
and keyword index; Neo4j for the graph and vector index; filesystem or
GCS for the archive.

Source: ADR-0019
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from context_graph.ports.archive import ArchiveStore
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.graph_backend import GraphBackend
    from context_graph.ports.graph_reads import GraphReads
    from context_graph.ports.search import KeywordIndex, VectorIndex
    from context_graph.ports.subscription import Subscription
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)

EVENT_LOG_BACKENDS = ("redis",)
SUBSCRIPTION_BACKENDS = ("redis",)
GRAPH_BACKENDS = ("neo4j",)
KEYWORD_INDEX_BACKENDS = ("redis",)
VECTOR_INDEX_BACKENDS = ("neo4j",)
ARCHIVE_BACKENDS = ("fs", "gcs")


class UnknownBackendError(ValueError):
    """A ``CG_STORAGE_*`` value names a backend that is not registered."""


def _require(port: str, backend: str, supported: tuple[str, ...]) -> None:
    if backend not in supported:
        msg = (
            f"Unknown {port} backend {backend!r} (CG_STORAGE_{port.upper()}); "
            f"supported: {', '.join(supported)}"
        )
        raise UnknownBackendError(msg)


@dataclass
class Stores:
    """The opened stores, one attribute per port."""

    event_log: EventLog
    graph: GraphBackend
    graph_reads: GraphReads
    keyword_index: KeywordIndex
    vector_index: VectorIndex
    archive: ArchiveStore | None
    backends: dict[str, str]
    _subscription_opener: Callable[[str, str], Subscription]
    _closers: list[Callable[[], Awaitable[None]]] = field(default_factory=list)

    def subscription(self, group_name: str, consumer_name: str) -> Subscription:
        """Open a subscription for one consumer of a group."""
        return self._subscription_opener(group_name, consumer_name)

    async def close(self) -> None:
        """Release every connection the stores hold, in the order opened."""
        for closer in self._closers:
            await closer()


async def open_stores(
    settings: Settings,
    *,
    prepare_ingest: bool = False,
    with_archive: bool = False,
) -> Stores:
    """Open the configured stores.

    Args:
        settings: Root settings; ``settings.storage`` selects backends.
        prepare_ingest: Load ingest scripts and search indexes on the event
            log (the API does; workers only read).
        with_archive: Open the archive store (only consolidation archives).

    Stores take only their own settings; retrieval dependencies (embedding,
    intent, LLM) belong to ``context_graph.retrieval.RetrievalEngine``.
    """
    storage = settings.storage
    _require("event_log", storage.event_log, EVENT_LOG_BACKENDS)
    _require("subscription", storage.subscription, SUBSCRIPTION_BACKENDS)
    _require("graph", storage.graph, GRAPH_BACKENDS)
    _require("keyword_index", storage.keyword_index, KEYWORD_INDEX_BACKENDS)
    _require("vector_index", storage.vector_index, VECTOR_INDEX_BACKENDS)
    if storage.subscription != storage.event_log:
        msg = (
            f"Subscription backend {storage.subscription!r} cannot read event log "
            f"backend {storage.event_log!r}"
        )
        raise UnknownBackendError(msg)

    closers: list[Callable[[], Awaitable[None]]] = []

    # -- Event log + subscriptions (Redis) ---------------------------------
    from redis.asyncio import Redis

    from context_graph.adapters.redis.store import RedisEventStore
    from context_graph.adapters.redis.subscription import RedisStreamSubscription

    redis_settings = settings.redis
    if prepare_ingest:
        redis_event_log = await RedisEventStore.create(redis_settings)
        await redis_event_log.ensure_indexes()
        closers.append(redis_event_log.close)
        redis_client = redis_event_log.client
    else:
        redis_client = Redis(
            host=redis_settings.host,
            port=redis_settings.port,
            db=redis_settings.db,
            password=(
                redis_settings.password.get_secret_value() if redis_settings.password else None
            ),
            decode_responses=False,
        )
        redis_event_log = RedisEventStore(client=redis_client, settings=redis_settings)
        closers.append(redis_client.aclose)

    event_log: EventLog = redis_event_log
    consumer_settings = settings.consumer

    def open_subscription(group_name: str, consumer_name: str) -> Subscription:
        return RedisStreamSubscription(
            redis_client,
            group_name,
            consumer_name,
            consumer_settings.source,
            claim_idle_ms=consumer_settings.claim_idle_ms,
            claim_batch_size=consumer_settings.claim_batch_size,
            dlq_stream_suffix=consumer_settings.dlq_stream_suffix,
        )

    # -- Graph (Neo4j) -----------------------------------------------------
    from context_graph.adapters.neo4j.store import Neo4jGraphStore

    graph = Neo4jGraphStore(settings.neo4j, query_settings=settings.query)
    await graph.ensure_constraints()
    closers.append(graph.close)

    # -- Search indexes ----------------------------------------------------
    # RediSearch BM25 is served by the Redis event log; the Neo4j vector
    # index by the Neo4j graph store.
    from context_graph.adapters.search import EventStoreKeywordIndex, GraphVectorIndex

    keyword_index = EventStoreKeywordIndex(event_log)
    vector_index = GraphVectorIndex(graph)

    # -- Archive -----------------------------------------------------------
    archive = _open_archive(settings, closers) if with_archive else None

    return Stores(
        event_log=event_log,
        graph=graph,
        graph_reads=graph.reads,
        keyword_index=keyword_index,
        vector_index=vector_index,
        archive=archive,
        backends={
            "event_log": storage.event_log,
            "subscription": storage.subscription,
            "graph": storage.graph,
            "keyword_index": storage.keyword_index,
            "vector_index": storage.vector_index,
            "archive": storage.archive,
        },
        _subscription_opener=open_subscription,
        _closers=closers,
    )


def _open_archive(
    settings: Settings,
    closers: list[Callable[[], Awaitable[None]]],
) -> ArchiveStore | None:
    """Open the archive store (ADR-0014), or None when disabled or unavailable."""
    archive_settings = settings.archive
    if not archive_settings.enabled:
        return None

    backend = settings.storage.archive or archive_settings.backend
    _require("archive", backend, ARCHIVE_BACKENDS)

    if backend == "gcs" and archive_settings.gcs_bucket:
        try:
            from context_graph.adapters.gcs.archive import GCSArchiveStore

            gcs_store = GCSArchiveStore(
                bucket_name=archive_settings.gcs_bucket,
                prefix=archive_settings.gcs_prefix,
                endpoint=archive_settings.gcs_endpoint,
            )
        except ImportError:
            log.warning(
                "gcs_archive_unavailable",
                hint="Install google-cloud-storage: pip install context-graph[gcs]",
            )
            return None
        closers.append(gcs_store.close)
        log.info(
            "archive_store_initialized",
            backend="gcs",
            bucket=archive_settings.gcs_bucket,
            endpoint=archive_settings.gcs_endpoint or "production",
        )
        return gcs_store

    from pathlib import Path

    from context_graph.adapters.fs.archive import FilesystemArchiveStore

    fs_store = FilesystemArchiveStore(base_path=Path(archive_settings.fs_base_path))
    log.info("archive_store_initialized", backend="fs", path=archive_settings.fs_base_path)
    return fs_store
