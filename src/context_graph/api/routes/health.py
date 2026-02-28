"""Health check endpoint.

GET /v1/health -- reports status of Redis and Neo4j dependencies.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from context_graph.api.dependencies import (  # noqa: TCH001 — runtime: Depends()
    get_event_health,
    get_graph_health,
)
from context_graph.ports.health import HealthCheckable  # noqa: TCH001 — runtime: Depends()

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    event_health: Annotated[HealthCheckable, Depends(get_event_health)],
    graph_health: Annotated[HealthCheckable, Depends(get_graph_health)],
) -> ORJSONResponse:
    """Service health check.

    Pings Redis and Neo4j to determine overall service health.
    Returns "healthy" (200) when both are reachable, "degraded" (503) when
    only one is reachable, and "unhealthy" (503) when neither responds.
    """
    redis_ok = False
    neo4j_ok = False

    try:
        redis_ok = await event_health.health_ping()
    except Exception:
        logger.warning("health_check_redis_failed")

    try:
        neo4j_ok = await graph_health.health_ping()
    except Exception:
        logger.warning("health_check_neo4j_failed")

    if redis_ok and neo4j_ok:
        status = "healthy"
    elif redis_ok or neo4j_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    content = {
        "status": status,
        "redis": redis_ok,
        "neo4j": neo4j_ok,
        "version": "0.1.0",
    }
    status_code = 200 if status == "healthy" else 503
    return ORJSONResponse(status_code=status_code, content=content)
