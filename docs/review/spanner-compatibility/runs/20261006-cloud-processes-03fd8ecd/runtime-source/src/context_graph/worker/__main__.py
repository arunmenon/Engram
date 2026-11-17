"""Worker runner entry point.

Usage:
    python -m context_graph.worker --consumer projection
    python -m context_graph.worker --consumer enrichment
    python -m context_graph.worker --consumer extraction
    python -m context_graph.worker --consumer consolidation
    python -m context_graph.worker --consumer pack_extraction

Opens the configured stores (CG_STORAGE_*, ADR-0019) using CG_* environment
variables, instantiates the requested consumer, and runs its loop until SIGTERM.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.adapters.registry import open_stores
from context_graph.settings import Settings

if TYPE_CHECKING:
    from context_graph.adapters.registry import Stores
    from context_graph.domain.pack_bundle import ActiveBundle
    from context_graph.worker.consumer import BaseConsumer

log = structlog.get_logger(__name__)

VALID_CONSUMERS = ("projection", "enrichment", "extraction", "consolidation", "pack_extraction")


# Consumer type -> (ConsumerSettings field holding its group, consumer name)
CONSUMER_SUBSCRIPTIONS: dict[str, tuple[str, str]] = {
    "projection": ("group_projection", "projection-1"),
    "enrichment": ("group_enrichment", "enrichment-1"),
    "extraction": ("group_extraction", "extraction-1"),
    "consolidation": ("group_consolidation", "consolidation-1"),
    "pack_extraction": ("group_pack_extraction", "pack-extraction-1"),
}


def _open_embedding_service(settings: Settings, unavailable_event: str, hint: str) -> Any:
    """Return the sentence-transformer embedder, or None if it is not installed."""
    try:
        from context_graph.adapters.embedding.service import SentenceTransformerEmbedder

        emb_settings = settings.embedding
        return SentenceTransformerEmbedder(
            model_name=emb_settings.model_name,
            device=emb_settings.device,
        )
    except ImportError:
        log.warning(unavailable_event, hint=hint)
        return None


async def _build_consumer(
    consumer_type: str, settings: Settings, *, bundle: ActiveBundle | None = None
) -> tuple[BaseConsumer, Stores]:
    """Open the stores the consumer needs and build it.

    Stores come from the registry (ADR-0019); this module never imports a
    storage adapter by name.
    """
    if consumer_type not in CONSUMER_SUBSCRIPTIONS:
        msg = f"Unknown consumer type: {consumer_type}"
        raise ValueError(msg)

    from context_graph.ontology.runtime import configured_bundle

    if bundle is None:
        bundle = configured_bundle(settings.ontology)

    stores = None
    try:
        group_field, consumer_name = CONSUMER_SUBSCRIPTIONS[consumer_type]
        group_name: str = getattr(settings.consumer, group_field)

        if consumer_type == "projection":
            from context_graph.domain.pack_projection import PackProjector
            from context_graph.ontology.versioning import reconcile
            from context_graph.worker.projection import ProjectionConsumer

            projector = PackProjector(bundle.registry, frozenset(settings.ontology.trusted_sources))
            stores = await open_stores(settings, bundle=bundle)
            await stores.graph.ensure_pack_schema(projector.registry, settings.embedding.dimensions)
            log.info("ontology_loaded", **projector.registry.summary())
            # Record the ontology version; replay changed rules; refuse breaking changes
            await reconcile(
                stores.graph,
                stores.event_log,
                projector,
                allow_breaking=settings.ontology.allow_breaking,
                allow_version_problems=settings.ontology.allow_version_problems,
                batch_size=settings.ontology.replay_batch_size,
                lookup_limit=settings.ontology.lookup_limit,
            )
            return ProjectionConsumer(
                subscription=stores.subscription(group_name, consumer_name),
                event_log=stores.event_log,
                graph_store=stores.graph,
                settings=settings,
                pack_projector=projector,
                pack_lookup_limit=settings.ontology.lookup_limit,
            ), stores

        if consumer_type == "pack_extraction":
            from context_graph.adapters.llm.client import LLMExtractionClient
            from context_graph.domain.pack_extraction import extraction_profiles
            from context_graph.domain.pack_projection import PackProjector
            from context_graph.worker.pack_extraction import PackExtractionConsumer

            projector = PackProjector(bundle.registry, frozenset(settings.ontology.trusted_sources))
            ontology = settings.ontology
            profiles = extraction_profiles(
                projector.registry,
                max_nodes=ontology.extraction_max_nodes,
                max_links=ontology.extraction_max_links,
                max_text_chars=ontology.extraction_max_text_chars,
                max_value_chars=ontology.extraction_max_value_chars,
            )
            log.info(
                "pack_extraction_profiles",
                packs=[p.pack_name for p in profiles],
                sources=sorted({s for p in profiles for s in p.sources}),
            )
            stores = await open_stores(settings, bundle=bundle)
            return PackExtractionConsumer(
                subscription=stores.subscription(group_name, consumer_name),
                event_log=stores.event_log,
                graph=stores.graph,
                profiles=profiles,
                projector=projector,
                model=LLMExtractionClient(
                    model_id=settings.llm.model_id,
                    temperature=settings.llm.temperature,
                    max_tokens=settings.llm.max_tokens,
                    timeout=settings.llm.timeout_seconds,
                    max_retries=settings.llm.max_retries,
                ),
                settings=settings,
            ), stores

        if consumer_type == "enrichment":
            from context_graph.worker.enrichment import EnrichmentConsumer

            stores = await open_stores(settings, bundle=bundle)

            # Optional embedding service for event embeddings
            embedding_service = _open_embedding_service(
                settings,
                "enrichment_embedding_service_unavailable",
                "Install sentence-transformers for event embeddings",
            )
            if embedding_service is not None:
                log.info(
                    "enrichment_embedding_service_initialized", model=settings.embedding.model_name
                )

            return EnrichmentConsumer(
                subscription=stores.subscription(group_name, consumer_name),
                event_log=stores.event_log,
                graph_store=stores.graph,
                settings=settings,
                embedding_service=embedding_service,
            ), stores

        if consumer_type == "extraction":
            from context_graph.adapters.llm.client import LLMExtractionClient
            from context_graph.worker.extraction import ExtractionConsumer

            llm_client = LLMExtractionClient(
                model_id=settings.llm.model_id,
                temperature=settings.llm.temperature,
                max_tokens=settings.llm.max_tokens,
                timeout=settings.llm.timeout_seconds,
                max_retries=settings.llm.max_retries,
                include_user=bundle.enables("user.extract.v1"),
            )

            # Tier 2b: Semantic entity matching via embedding service + graph vector index.
            # The graph store needs no embedding service: it only used one for
            # retrieval, which now lives in RetrievalEngine (ADR-0019 C3).
            embedding_service = _open_embedding_service(
                settings,
                "embedding_service_unavailable",
                "Install sentence-transformers: pip install context-graph[embedding]",
            )
            stores = await open_stores(settings, bundle=bundle)
            if embedding_service is not None:
                log.info("embedding_service_initialized", model=settings.embedding.model_name)

            # The graph store also satisfies the UserStore protocol
            return ExtractionConsumer(
                subscription=stores.subscription(group_name, consumer_name),
                event_log=stores.event_log,
                llm_client=llm_client,
                settings=settings,
                embedding_service=embedding_service,
                graph_store=stores.graph,
                user_store=stores.graph if bundle.enables("user.extract.v1") else None,
                bundle=bundle,
            ), stores

        from context_graph.worker.consolidation import ConsolidationConsumer

        # Archive store selected by CG_STORAGE_ARCHIVE / CG_ARCHIVE_* (ADR-0014)
        stores = await open_stores(settings, with_archive=True, bundle=bundle)

        # Optional: LLM client for consolidation summaries
        consolidation_llm_client: Any = None
        try:
            from context_graph.adapters.llm.client import LLMExtractionClient

            consolidation_llm_client = LLMExtractionClient(
                model_id=settings.llm.model_id,
                temperature=settings.llm.temperature,
                max_tokens=settings.llm.max_tokens,
                timeout=settings.llm.timeout_seconds,
            )
            log.info("consolidation_llm_client_initialized")
        except ImportError:
            log.info("consolidation_llm_client_unavailable")

        return ConsolidationConsumer(
            subscription=stores.subscription(group_name, consumer_name),
            event_log=stores.event_log,
            graph_maintenance=stores.graph,
            settings=settings,
            archive_store=stores.archive,
            llm_client=consolidation_llm_client,
        ), stores

    except BaseException:
        if stores is not None:
            await stores.close()
        raise


async def run_worker(
    consumer_type: str, *, settings: Settings | None = None, bundle: ActiveBundle | None = None
) -> None:
    """Instantiate and run a consumer worker until shutdown signal."""
    settings = (settings if settings is not None else Settings()).model_copy(deep=True)

    log_level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )

    log.info(
        "worker_starting",
        consumer=consumer_type,
        redis_host=settings.redis.host,
        neo4j_uri=settings.neo4j.uri,
        storage=settings.storage.model_dump(),
    )

    if bundle is None:
        consumer, stores = await _build_consumer(consumer_type, settings)
    else:
        consumer, stores = await _build_consumer(consumer_type, settings, bundle=bundle)

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
        await stores.close()
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
