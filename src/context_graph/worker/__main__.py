"""Worker runner entry point.

Usage:
    python -m context_graph.worker --consumer projection
    python -m context_graph.worker --consumer enrichment
    python -m context_graph.worker --consumer extraction
    python -m context_graph.worker --consumer consolidation

Connects to Redis and Neo4j using CG_* environment variables, instantiates
the requested consumer, and runs the XREADGROUP loop until SIGTERM.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.settings import Settings

if TYPE_CHECKING:
    from context_graph.worker.consumer import BaseConsumer

log = structlog.get_logger(__name__)

VALID_CONSUMERS = ("projection", "enrichment", "extraction", "consolidation")


async def _build_consumer(
    consumer_type: str,
    redis_client: Any,
    settings: Settings,
) -> tuple[BaseConsumer, list[Any]]:
    """Build the consumer and return it with closeable resources."""
    closeables: list[Any] = []

    if consumer_type == "projection":
        from context_graph.adapters.neo4j.store import Neo4jGraphStore
        from context_graph.worker.projection import ProjectionConsumer

        graph_store = Neo4jGraphStore(settings.neo4j)
        await graph_store.ensure_constraints()
        closeables.append(graph_store)
        return ProjectionConsumer(
            redis_client=redis_client,
            graph_store=graph_store,
            settings=settings,
        ), closeables

    if consumer_type == "enrichment":
        from neo4j import AsyncGraphDatabase

        from context_graph.worker.enrichment import EnrichmentConsumer

        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j.uri,
            auth=(settings.neo4j.username, settings.neo4j.password.get_secret_value()),
            max_connection_pool_size=settings.neo4j.max_connection_pool_size,
        )
        closeables.append(neo4j_driver)

        # Optional embedding service for event embeddings
        embedding_service = None
        try:
            from context_graph.adapters.embedding.service import SentenceTransformerEmbedder

            emb_settings = settings.embedding
            embedding_service = SentenceTransformerEmbedder(
                model_name=emb_settings.model_name,
                device=emb_settings.device,
            )
            log.info("enrichment_embedding_service_initialized", model=emb_settings.model_name)
        except ImportError:
            log.warning(
                "enrichment_embedding_service_unavailable",
                hint="Install sentence-transformers for event embeddings",
            )

        return EnrichmentConsumer(
            redis_client=redis_client,
            neo4j_driver=neo4j_driver,
            settings=settings,
            embedding_service=embedding_service,
        ), closeables

    if consumer_type == "extraction":
        from neo4j import AsyncGraphDatabase

        from context_graph.adapters.llm.client import LLMExtractionClient
        from context_graph.adapters.neo4j.store import Neo4jGraphStore
        from context_graph.worker.extraction import ExtractionConsumer

        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j.uri,
            auth=(settings.neo4j.username, settings.neo4j.password.get_secret_value()),
            max_connection_pool_size=settings.neo4j.max_connection_pool_size,
        )
        llm_client = LLMExtractionClient(
            model_id=settings.llm.model_id,
            temperature=settings.llm.temperature,
            max_tokens=settings.llm.max_tokens,
            timeout=settings.llm.timeout_seconds,
            max_retries=settings.llm.max_retries,
        )
        closeables.append(neo4j_driver)

        # Tier 2b: Semantic entity matching via embedding service + Neo4j vector index
        embedding_service = None
        extraction_graph_store = None
        try:
            from context_graph.adapters.embedding.service import SentenceTransformerEmbedder

            emb_settings = settings.embedding
            embedding_service = SentenceTransformerEmbedder(
                model_name=emb_settings.model_name,
                device=emb_settings.device,
            )
            extraction_graph_store = Neo4jGraphStore(
                settings.neo4j, embedding_service=embedding_service
            )
            await extraction_graph_store.ensure_constraints()
            closeables.append(extraction_graph_store)
            log.info("embedding_service_initialized", model=emb_settings.model_name)
        except ImportError:
            log.warning(
                "embedding_service_unavailable",
                hint="Install sentence-transformers: pip install context-graph[embedding]",
            )

        # The Neo4jGraphStore satisfies the UserStore protocol
        user_store = extraction_graph_store if extraction_graph_store is not None else None
        if user_store is None:
            # Create a basic graph store (no embedding) for UserStore protocol
            user_graph_store = Neo4jGraphStore(settings.neo4j)
            await user_graph_store.ensure_constraints()
            closeables.append(user_graph_store)
            user_store = user_graph_store

        return ExtractionConsumer(
            redis_client=redis_client,
            neo4j_driver=neo4j_driver,
            neo4j_database=settings.neo4j.database,
            llm_client=llm_client,
            settings=settings,
            embedding_service=embedding_service,
            graph_store=extraction_graph_store,
            user_store=user_store,
        ), closeables

    if consumer_type == "consolidation":
        from context_graph.adapters.neo4j.store import Neo4jGraphStore
        from context_graph.worker.consolidation import ConsolidationConsumer

        graph_store = Neo4jGraphStore(settings.neo4j)
        await graph_store.ensure_constraints()
        closeables.append(graph_store)

        # Bootstrap archive store based on settings (ADR-0014)
        archive_store: Any = None
        archive_settings = settings.archive
        if archive_settings.enabled:
            if archive_settings.backend == "gcs" and archive_settings.gcs_bucket:
                try:
                    from context_graph.adapters.gcs.archive import GCSArchiveStore

                    archive_store = GCSArchiveStore(
                        bucket_name=archive_settings.gcs_bucket,
                        prefix=archive_settings.gcs_prefix,
                        endpoint=archive_settings.gcs_endpoint,
                    )
                    closeables.append(archive_store)
                    log.info(
                        "archive_store_initialized",
                        backend="gcs",
                        bucket=archive_settings.gcs_bucket,
                        endpoint=archive_settings.gcs_endpoint or "production",
                    )
                except ImportError:
                    log.warning(
                        "gcs_archive_unavailable",
                        hint="Install google-cloud-storage: pip install context-graph[gcs]",
                    )
            else:
                from pathlib import Path

                from context_graph.adapters.fs.archive import FilesystemArchiveStore

                archive_store = FilesystemArchiveStore(
                    base_path=Path(archive_settings.fs_base_path),
                )
                log.info(
                    "archive_store_initialized",
                    backend="fs",
                    path=archive_settings.fs_base_path,
                )

        return ConsolidationConsumer(
            redis_client=redis_client,
            graph_maintenance=graph_store,
            settings=settings,
            archive_store=archive_store,
        ), closeables

    msg = f"Unknown consumer type: {consumer_type}"
    raise ValueError(msg)


async def run_worker(consumer_type: str) -> None:
    """Instantiate and run a consumer worker until shutdown signal."""
    settings = Settings()

    log_level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )

    log.info(
        "worker_starting",
        consumer=consumer_type,
        redis_host=settings.redis.host,
        neo4j_uri=settings.neo4j.uri,
    )

    # Create Redis client
    from redis.asyncio import Redis

    redis_client = Redis(
        host=settings.redis.host,
        port=settings.redis.port,
        db=settings.redis.db,
        password=settings.redis.password.get_secret_value() if settings.redis.password else None,
        decode_responses=False,
    )

    consumer, closeables = await _build_consumer(consumer_type, redis_client, settings)

    try:
        # Register SIGTERM/SIGINT handler for graceful shutdown
        loop = asyncio.get_running_loop()

        def _signal_handler() -> None:
            log.info("shutdown_signal_received", consumer=consumer_type)
            consumer.stop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _signal_handler)

        log.info("worker_running", consumer=consumer_type)
        await consumer.run()

    finally:
        log.info("worker_shutting_down", consumer=consumer_type)
        await redis_client.aclose()
        for closeable in closeables:
            await closeable.close()
        log.info("worker_stopped", consumer=consumer_type)


def main() -> None:
    """Parse args and run the worker."""
    parser = argparse.ArgumentParser(description="Engram consumer worker")
    parser.add_argument(
        "--consumer",
        required=True,
        choices=VALID_CONSUMERS,
        help="Consumer type to run",
    )
    args = parser.parse_args()
    asyncio.run(run_worker(args.consumer))


if __name__ == "__main__":
    main()
