"""Worker process entry point.

Runs the projection and enrichment consumer workers concurrently.
Extraction and consolidation consumers are excluded by default as they
require LLM clients (Phase 3+).

Usage:
    python -m context_graph.worker
"""

from __future__ import annotations

import asyncio
import signal

import structlog

from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.adapters.redis.store import RedisEventStore
from context_graph.settings import Settings
from context_graph.worker.enrichment import EnrichmentConsumer
from context_graph.worker.projection import ProjectionConsumer

log = structlog.get_logger(__name__)


async def run_workers() -> None:
    """Start projection and enrichment workers, shut down on SIGINT/SIGTERM."""
    settings = Settings()

    # --- Connect to stores ---
    event_store = await RedisEventStore.create(settings.redis)
    graph_store = Neo4jGraphStore(settings.neo4j)
    await graph_store.ensure_constraints()

    redis_client = event_store._client  # noqa: SLF001

    projection = ProjectionConsumer(
        redis_client=redis_client,
        graph_store=graph_store,
        settings=settings,
    )
    enrichment = EnrichmentConsumer(
        redis_client=redis_client,
        neo4j_driver=graph_store._driver,  # noqa: SLF001
        settings=settings,
    )

    consumers = [projection, enrichment]

    # --- Graceful shutdown ---
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: _shutdown(consumers))

    log.info("workers_starting", consumer_count=len(consumers))

    try:
        await asyncio.gather(*(c.run() for c in consumers))
    finally:
        await event_store.close()
        await graph_store.close()
        log.info("workers_stopped")


def _shutdown(consumers: list[ProjectionConsumer | EnrichmentConsumer]) -> None:
    log.info("shutdown_signal_received")
    for c in consumers:
        c.stop()


if __name__ == "__main__":
    asyncio.run(run_workers())
