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

from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.adapters.redis.store import RedisEventStore
from context_graph.api.dependencies import require_admin_key, require_api_key
from context_graph.api.middleware import register_middleware
from context_graph.api.routes.admin import router as admin_router
from context_graph.api.routes.context import router as context_router
from context_graph.api.routes.entities import router as entities_router
from context_graph.api.routes.events import router as events_router
from context_graph.api.routes.health import router as health_router
from context_graph.api.routes.lineage import router as lineage_router
from context_graph.api.routes.query import router as query_router
from context_graph.api.routes.users import router as users_router
from context_graph.settings import Settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage Redis + Neo4j connections across the app lifecycle."""
    settings = Settings()

    # -- Startup: create stores and attach to app state --------------------
    event_store = await RedisEventStore.create(settings.redis)
    await event_store.ensure_indexes()

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

    graph_store = Neo4jGraphStore(
        settings.neo4j,
        embedding_service=embedding_service,
        query_settings=settings.query,
    )
    await graph_store.ensure_constraints()

    app.state.settings = settings
    app.state.event_store = event_store
    app.state.graph_store = graph_store

    logger.info(
        "app_started",
        redis_host=settings.redis.host,
        neo4j_uri=settings.neo4j.uri,
    )

    yield

    # -- Shutdown: release connections -------------------------------------
    await event_store.close()
    await graph_store.close()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="Context Graph API",
        description="Traceability-first context graph for AI agents",
        version="0.1.0",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    register_middleware(app)

    # Standard endpoints: require API key (disabled when CG_AUTH_API_KEY unset)
    api_key_deps = [Depends(require_api_key)]
    app.include_router(events_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(context_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(query_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(lineage_router, prefix="/v1", dependencies=api_key_deps)
    app.include_router(entities_router, prefix="/v1", dependencies=api_key_deps)

    # Admin + GDPR endpoints: require admin key
    admin_key_deps = [Depends(require_admin_key)]
    app.include_router(admin_router, prefix="/v1", dependencies=admin_key_deps)
    app.include_router(users_router, prefix="/v1", dependencies=admin_key_deps)

    # Health endpoint: no auth (used by load balancers / orchestrators)
    app.include_router(health_router, prefix="/v1")

    # Prometheus metrics endpoint
    metrics_app = make_metrics_app()
    app.mount("/metrics", metrics_app)

    return app
