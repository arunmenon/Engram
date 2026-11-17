"""FastAPI application factory.

Creates and configures the Context Graph API with lifespan management
for Redis and Neo4j connections.

Source: ADR-0006
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import Depends, FastAPI
from fastapi.responses import ORJSONResponse
from prometheus_client import make_asgi_app as make_metrics_app

from context_graph.adapters.registry import open_stores
from context_graph.api.dependencies import require_admin_key, require_api_key
from context_graph.api.middleware import register_middleware
from context_graph.api.rate_limit import EventQuota
from context_graph.api.routes.admin import router as admin_router
from context_graph.api.routes.artifacts import router as artifacts_router
from context_graph.api.routes.context import router as context_router
from context_graph.api.routes.entities import router as entities_router
from context_graph.api.routes.events import import_router as events_import_router
from context_graph.api.routes.events import router as events_router
from context_graph.api.routes.feedback import router as feedback_router
from context_graph.api.routes.health import router as health_router
from context_graph.api.routes.lineage import router as lineage_router
from context_graph.api.routes.ontology import router as ontology_router
from context_graph.api.routes.query import router as query_router
from context_graph.api.routes.simulate import router as simulate_router
from context_graph.api.routes.users import router as users_router
from context_graph.api.routes.webhooks import router as webhooks_router
from context_graph.domain.pack_intents import RegistryIntents
from context_graph.ontology.runtime import configured_bundle
from context_graph.ontology.versioning import EvalPending
from context_graph.retrieval import RetrievalEngine
from context_graph.retrieval.artifacts import ArtifactRetriever
from context_graph.settings import Settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from context_graph.domain.pack_bundle import ActiveBundle

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage storage connections across the app lifecycle."""
    settings = getattr(app.state, "configured_settings", None)
    if settings is None:
        settings = Settings()
    # Refuse incompatible pack selections before constructing providers/stores.
    bundle = getattr(app.state, "configured_bundle", None)
    if bundle is None:
        bundle = configured_bundle(settings.ontology)
    ontology = bundle.registry

    # Optional: embedding service for query-time relevance scoring
    embedding_service = None
    try:
        from context_graph.adapters.embedding.service import SentenceTransformerEmbedder

        embedding_service = SentenceTransformerEmbedder(
            model_name=settings.embedding.model_name,
            device=settings.embedding.device,
        )
        logger.info(
            "embedding_service_initialized",
            model=settings.embedding.model_name,
        )
    except ImportError:
        logger.info("embedding_service_unavailable", hint="relevance_score will default to 0.5")

    # Optional: LLM intent classifier
    intent_classifier = None
    if settings.intent.use_llm:
        from context_graph.adapters.llm.intent_classifier import LLMIntentClassifier

        intent_classifier = LLMIntentClassifier(
            model_id=settings.llm.model_id,
            timeout_seconds=settings.intent.timeout_seconds,
            fallback_on_error=settings.intent.fallback_on_error,
        )
        logger.info("llm_intent_classifier_initialized")

    # Optional: LLM client for HyDE and other expansions
    llm_client = None
    try:
        from context_graph.adapters.llm.client import LLMExtractionClient

        llm_client = LLMExtractionClient(
            model_id=settings.llm.model_id,
            temperature=settings.hyde.temperature,
            max_tokens=settings.hyde.max_tokens,
        )
        logger.info("llm_client_initialized")
    except ImportError:
        logger.info("llm_client_unavailable")

    # -- Startup: open the configured stores (ADR-0019) -------------------
    stores = await open_stores(settings, prepare_ingest=True, bundle=bundle)
    try:
        await stores.graph.ensure_pack_schema(ontology, settings.embedding.dimensions)

        # Retrieval engine: composes the storage ports and owns its own
        # dependencies (ADR-0019 C3)
        retrieval = RetrievalEngine(
            stores.graph_reads,
            decay=settings.decay,
            keyword_index=stores.keyword_index,
            vector_index=stores.vector_index,
            embedding_service=embedding_service,
            intent_classifier=intent_classifier,
            llm_client=llm_client,
            ppr_settings=settings.ppr,
            query_timeout_s=settings.query.default_timeout_ms / 1000.0,
            neighbor_limit=settings.query.default_neighbor_limit,
            provenance_source=settings.storage.event_log,
            intents=RegistryIntents.for_events(ontology),
            bundle=bundle,
            pack_graph=stores.pack_reads if stores.pack_reads is not None else stores.graph,
        )
        artifacts = ArtifactRetriever(
            stores.pack_reads if stores.pack_reads is not None else stores.graph,
            ontology,
            default_max_depth=settings.query.default_max_depth,
            seed_limit=settings.ontology.retrieval_seed_limit,
            neighbor_limit=settings.ontology.retrieval_neighbor_limit,
            provenance_source=settings.storage.event_log,
            seed_min_ratio=settings.ontology.retrieval_seed_min_ratio,
            max_terms=settings.ontology.retrieval_max_terms,
            max_graph_calls=settings.ontology.retrieval_max_graph_calls,
            scan_limit=settings.ontology.retrieval_scan_limit,
            word_scan_limit=settings.ontology.retrieval_word_scan_limit,
        )

        app.state.settings = settings
        app.state.stores = stores
        app.state.event_store = stores.event_log
        app.state.graph_store = stores.graph
        app.state.retrieval = retrieval
        app.state.ontology = ontology
        app.state.bundle = bundle
        app.state.artifacts = artifacts
        if settings.rate_limit.enabled and settings.ingest.events_per_minute > 0:
            app.state.event_quota = EventQuota(
                settings.ingest.events_per_minute, max_clients=settings.rate_limit.max_clients
            )
        app.state.eval_pending = EvalPending(
            stores.graph, ontology, settings.ontology.eval_state_ttl_s
        )

        logger.info(
            "app_started",
            redis_host=settings.redis.host,
            neo4j_uri=settings.neo4j.uri,
            ontology_version=ontology.version,
            ontology_packs=[f"{p.name}@{p.version}" for p in ontology.packs],
        )

        yield

    finally:
        await stores.close()
        logger.info("app_stopped")


def create_app(settings: Settings | None = None, *, bundle: ActiveBundle | None = None) -> FastAPI:
    """Build one application from a private settings snapshot.

    This factory boundary does not provide tenant authentication or durable
    database ownership fences. Those must precede production tenant routing.
    """
    configured = (settings if settings is not None else Settings()).model_copy(deep=True)
    app = FastAPI(
        title="Context Graph API",
        description="Traceability-first context graph for AI agents",
        version="0.1.0",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    app.state.configured_settings = configured
    app.state.configured_bundle = bundle
    register_middleware(app, configured)

    # Standard endpoints: require API key (disabled when CG_AUTH_API_KEY unset)
    api_key_deps = [Depends(require_api_key)]
    app.include_router(events_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(context_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(query_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(artifacts_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(ontology_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(lineage_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(entities_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(feedback_router, prefix="/v1", dependencies=api_key_deps)

    # Admin + GDPR endpoints: require admin key
    admin_key_deps = [Depends(require_admin_key)]
    app.include_router(admin_router, prefix="/v1", dependencies=admin_key_deps)
    app.include_router(events_import_router, prefix="/v1", dependencies=admin_key_deps)
    app.include_router(users_router, prefix="/v1", dependencies=admin_key_deps)

    # Simulation endpoint: standard API key auth
    app.include_router(simulate_router, prefix="/v1", dependencies=api_key_deps)

    # Tool webhooks: authenticated by their HMAC signature (ADR-0018)
    app.include_router(webhooks_router, prefix="/v1")

    # Health endpoint: no auth (used by load balancers / orchestrators)
    app.include_router(health_router, prefix="/v1")

    # Prometheus metrics endpoint
    metrics_app = make_metrics_app()
    app.mount("/metrics", metrics_app)

    return app
