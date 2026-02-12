"""FastAPI application factory.

Creates and configures the Context Graph API with lifespan management
for Redis and Neo4j connections.

Source: ADR-0006
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import structlog
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.adapters.redis.store import RedisEventStore
from context_graph.api.middleware import register_middleware
from context_graph.api.routes.context import router as context_router
from context_graph.api.routes.entities import router as entities_router
from context_graph.api.routes.events import router as events_router
from context_graph.api.routes.health import router as health_router
from context_graph.api.routes.lineage import router as lineage_router
from context_graph.api.routes.query import router as query_router
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

    graph_store = Neo4jGraphStore(settings.neo4j)
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

    app.include_router(events_router, prefix="/v1")
    app.include_router(health_router, prefix="/v1")
    app.include_router(context_router, prefix="/v1")
    app.include_router(query_router, prefix="/v1")
    app.include_router(lineage_router, prefix="/v1")
    app.include_router(entities_router, prefix="/v1")

    return app
