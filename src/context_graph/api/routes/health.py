"""Health check endpoints.

GET /health/live  -- K8s liveness: always 200 (no dependency checks).
GET /health/ready -- K8s readiness: pings Redis + Neo4j, returns 200/503.
GET /health       -- backward-compatible alias for readiness.
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


@router.get("/health/live")
async def liveness() -> ORJSONResponse:
    """Liveness probe — always returns 200.

    Used by K8s liveness probes.  No dependency checks: if the
    process is alive and accepting connections, it is live.
    """
    return ORJSONResponse(status_code=200, content={"status": "alive"})


async def _check_readiness(
    event_health: HealthCheckable,
    graph_health: HealthCheckable,
) -> ORJSONResponse:
    """Shared readiness logic for /health/ready and /health."""
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

    # Collect Redis memory information when store supports it
    redis_memory: dict[str, object] | None = None
    if redis_ok:
        try:
            get_mem = getattr(event_health, "get_memory_info", None)
            if get_mem is not None and callable(get_mem):
                mem_info = await get_mem()
                if isinstance(mem_info, dict):
                    redis_memory = {
                        "used_bytes": mem_info.get("used_memory_bytes", 0),
                        "peak_bytes": mem_info.get("used_memory_peak_bytes", 0),
                        "pressure": mem_info.get("used_memory_pct", 0) > 80.0,
                    }
        except Exception:
            logger.debug("health_check_redis_memory_info_failed")

    content: dict[str, object] = {
        "status": status,
        "redis": redis_ok,
        "neo4j": neo4j_ok,
        "version": "0.1.0",
    }

    if redis_memory is not None:
        content["redis_memory"] = redis_memory

    status_code = 200 if status == "healthy" else 503
    return ORJSONResponse(status_code=status_code, content=content)


@router.get("/health/ready")
async def readiness(
    event_health: Annotated[HealthCheckable, Depends(get_event_health)],
    graph_health: Annotated[HealthCheckable, Depends(get_graph_health)],
) -> ORJSONResponse:
    """Readiness probe — pings Redis and Neo4j.

    Returns 200 when both are reachable, 503 otherwise.
    Used by K8s readiness probes and load balancers.
    """
    return await _check_readiness(event_health, graph_health)


@router.get("/health")
async def health_check(
    event_health: Annotated[HealthCheckable, Depends(get_event_health)],
    graph_health: Annotated[HealthCheckable, Depends(get_graph_health)],
) -> ORJSONResponse:
    """Backward-compatible health check (delegates to readiness logic)."""
    return await _check_readiness(event_health, graph_health)
