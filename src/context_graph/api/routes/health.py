"""Health check endpoint.

GET /v1/health — reports status of Redis and Neo4j dependencies.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request) -> ORJSONResponse:
    """Service health check.

    Pings Redis and Neo4j to determine overall service health.
    Returns "healthy" (200) when both are reachable, "degraded" (503) when
    only one is reachable, and "unhealthy" (503) when neither responds.
    """
    redis_ok = False
    neo4j_ok = False

    # Check Redis connectivity
    try:
        event_store = request.app.state.event_store
        await event_store._client.ping()
        redis_ok = True
    except Exception:
        logger.warning("health_check_redis_failed")

    # Check Neo4j connectivity
    try:
        graph_store = request.app.state.graph_store
        async with graph_store._driver.session(
            database=graph_store._database,
        ) as session:
            await session.run("RETURN 1")
        neo4j_ok = True
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
