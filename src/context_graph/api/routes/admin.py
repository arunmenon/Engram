"""Admin endpoints for memory intelligence operations.

POST /v1/admin/reconsolidate  — trigger re-consolidation
GET  /v1/admin/stats          — graph and stream statistics
POST /v1/admin/prune          — retention-based pruning
GET  /v1/admin/health/detailed — extended health check

Source: ADR-0008
"""

from __future__ import annotations

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, Field

from context_graph.adapters.neo4j import maintenance
from context_graph.adapters.neo4j.store import Neo4jGraphStore  # noqa: TCH001 — runtime: Depends
from context_graph.api.dependencies import get_graph_store, get_settings
from context_graph.domain.consolidation import (
    create_summary_from_events,
    group_events_into_episodes,
    should_reconsolidate,
)
from context_graph.domain.forgetting import get_pruning_actions
from context_graph.settings import Settings  # noqa: TCH001 — runtime: Depends

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Dependency type aliases
# ---------------------------------------------------------------------------

GraphStoreDep = Annotated[Neo4jGraphStore, Depends(get_graph_store)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ReconsolidateRequest(BaseModel):
    """Optional body for the reconsolidate endpoint."""

    session_id: str | None = None


class ReconsolidateResponse(BaseModel):
    """Result of a reconsolidate operation."""

    sessions_processed: int = 0
    summaries_created: int = 0
    events_processed: int = 0


class PruneRequest(BaseModel):
    """Body for the prune endpoint."""

    tier: str = Field(..., pattern=r"^(warm|cold)$")
    dry_run: bool = True


class PruneResponse(BaseModel):
    """Result of a prune operation."""

    pruned_edges: int = 0
    pruned_nodes: int = 0
    dry_run: bool = True
    details: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/reconsolidate")
async def reconsolidate(
    request: Request,
    graph_store: GraphStoreDep,
    settings: SettingsDep,
) -> ORJSONResponse:
    """Trigger re-consolidation for a session or all qualifying sessions.

    When a session_id is provided, only that session is processed.
    Otherwise all sessions whose event count exceeds the reflection
    threshold are processed.
    """
    body = await request.json() if await request.body() else {}
    session_id = body.get("session_id")
    threshold = settings.decay.reflection_threshold

    # Get session event counts from Neo4j
    session_counts = await maintenance.get_session_event_counts(
        graph_store._driver,
        graph_store._database,
    )

    # Filter sessions to process
    if session_id:
        sessions_to_process = {session_id: session_counts.get(session_id, 0)}
    else:
        sessions_to_process = {
            sid: count
            for sid, count in session_counts.items()
            if should_reconsolidate(count, threshold)
        }

    sessions_processed = 0
    summaries_created = 0
    events_processed = 0

    for sid, count in sessions_to_process.items():
        if not should_reconsolidate(count, threshold) and not session_id:
            continue

        # Fetch events for this session from Neo4j
        async with graph_store._driver.session(database=graph_store._database) as neo_session:
            result = await neo_session.run(
                "MATCH (e:Event {session_id: $sid}) "
                "RETURN e.event_id AS event_id, e.event_type AS event_type, "
                "e.occurred_at AS occurred_at, e.tool_name AS tool_name, "
                "e.status AS status "
                "ORDER BY e.occurred_at",
                {"sid": sid},
            )
            records = [record async for record in result]

        event_dicts = [dict(r) for r in records]
        if not event_dicts:
            continue

        events_processed += len(event_dicts)

        # Group into episodes
        episodes = group_events_into_episodes(event_dicts, gap_minutes=30)

        for episode in episodes:
            summary = create_summary_from_events(episode, scope="session", scope_id=sid)

            episode_event_ids = [e.get("event_id", "") for e in episode if e.get("event_id")]

            await maintenance.write_summary_with_edges(
                driver=graph_store._driver,
                database=graph_store._database,
                summary_id=summary.summary_id,
                scope=summary.scope,
                scope_id=summary.scope_id,
                content=summary.content,
                created_at=summary.created_at.isoformat(),
                event_count=summary.event_count,
                time_range=[dt.isoformat() for dt in summary.time_range],
                event_ids=episode_event_ids,
            )
            summaries_created += 1

        sessions_processed += 1

    logger.info(
        "reconsolidation_complete",
        sessions_processed=sessions_processed,
        summaries_created=summaries_created,
        events_processed=events_processed,
    )

    return ORJSONResponse(
        content={
            "sessions_processed": sessions_processed,
            "summaries_created": summaries_created,
            "events_processed": events_processed,
        },
    )


@router.get("/stats")
async def stats(
    request: Request,
    graph_store: GraphStoreDep,
) -> ORJSONResponse:
    """Return graph node/edge counts and Redis stream length."""
    graph_stats = await maintenance.get_graph_stats(
        graph_store._driver,
        graph_store._database,
    )

    # Get Redis stream length
    stream_length = 0
    try:
        event_store = request.app.state.event_store
        stream_length = await event_store._client.xlen(event_store._settings.global_stream)
    except Exception:
        logger.warning("stats_redis_stream_length_failed")

    return ORJSONResponse(
        content={
            "nodes": graph_stats["nodes"],
            "edges": graph_stats["edges"],
            "total_nodes": graph_stats["total_nodes"],
            "total_edges": graph_stats["total_edges"],
            "redis": {"stream_length": stream_length},
        },
    )


@router.post("/prune")
async def prune(
    request: Request,
    graph_store: GraphStoreDep,
    settings: SettingsDep,
) -> ORJSONResponse:
    """Run retention-based pruning on the graph.

    Accepts ``tier`` (warm or cold) and ``dry_run`` (default true).
    Returns what was (or would be) pruned.
    """
    body = await request.json()
    try:
        prune_req = PruneRequest.model_validate(body)
    except Exception as exc:
        return ORJSONResponse(status_code=422, content={"detail": str(exc)})

    retention = settings.retention

    # Fetch events from Neo4j with their properties
    async with graph_store._driver.session(database=graph_store._database) as neo_session:
        result = await neo_session.run(
            "MATCH (e:Event) "
            "RETURN e.event_id AS event_id, e.occurred_at AS occurred_at, "
            "e.importance_score AS importance_score, "
            "coalesce(e.access_count, 0) AS access_count, "
            "e.similarity_score AS similarity_score "
            "ORDER BY e.occurred_at",
        )
        records = [record async for record in result]

    event_dicts = [dict(r) for r in records]

    actions = get_pruning_actions(
        events=event_dicts,
        hot_hours=retention.hot_hours,
        warm_hours=retention.warm_hours,
        cold_hours=retention.cold_hours,
        warm_min_similarity=retention.warm_min_similarity_score,
        cold_min_importance=retention.cold_min_importance,
        cold_min_access_count=retention.cold_min_access_count,
    )

    pruned_edges = 0
    pruned_nodes = 0
    details: list[dict[str, Any]] = []

    if prune_req.tier == "warm":
        edge_ids = actions.delete_edges
        pruned_edges = len(edge_ids)
        if edge_ids:
            details.append({"action": "delete_similar_edges", "event_ids": edge_ids})
        if not prune_req.dry_run and edge_ids:
            pruned_edges = await maintenance.delete_edges_by_type_and_age(
                driver=graph_store._driver,
                database=graph_store._database,
                min_score=retention.warm_min_similarity_score,
                max_age_hours=retention.hot_hours,
            )
    elif prune_req.tier == "cold":
        node_ids = actions.delete_nodes + actions.archive_event_ids
        pruned_nodes = len(node_ids)
        if node_ids:
            details.append({"action": "delete_cold_events", "event_ids": node_ids})
        if not prune_req.dry_run and node_ids:
            deleted_cold = await maintenance.delete_cold_events(
                driver=graph_store._driver,
                database=graph_store._database,
                max_age_hours=retention.warm_hours,
                min_importance=retention.cold_min_importance,
                min_access_count=retention.cold_min_access_count,
            )
            deleted_archive = await maintenance.delete_archive_events(
                driver=graph_store._driver,
                database=graph_store._database,
                event_ids=actions.archive_event_ids,
            )
            pruned_nodes = deleted_cold + deleted_archive

    logger.info(
        "prune_complete",
        tier=prune_req.tier,
        dry_run=prune_req.dry_run,
        pruned_edges=pruned_edges,
        pruned_nodes=pruned_nodes,
    )

    return ORJSONResponse(
        content={
            "pruned_edges": pruned_edges,
            "pruned_nodes": pruned_nodes,
            "dry_run": prune_req.dry_run,
            "details": details,
        },
    )


@router.get("/health/detailed")
async def health_detailed(
    request: Request,
    graph_store: GraphStoreDep,
) -> ORJSONResponse:
    """Extended health check with Neo4j stats and Redis stream length."""
    redis_ok = False
    neo4j_ok = False
    stream_length = 0
    graph_stats: dict[str, Any] = {"nodes": {}, "edges": {}}

    # Check Redis
    try:
        event_store = request.app.state.event_store
        await event_store._client.ping()
        redis_ok = True
        stream_length = await event_store._client.xlen(event_store._settings.global_stream)
    except Exception:
        logger.warning("detailed_health_redis_failed")

    # Check Neo4j and get stats
    try:
        graph_stats = await maintenance.get_graph_stats(
            graph_store._driver,
            graph_store._database,
        )
        neo4j_ok = True
    except Exception:
        logger.warning("detailed_health_neo4j_failed")

    if redis_ok and neo4j_ok:
        status = "healthy"
    elif redis_ok or neo4j_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    return ORJSONResponse(
        content={
            "status": status,
            "redis": {"connected": redis_ok, "stream_length": stream_length},
            "neo4j": {
                "connected": neo4j_ok,
                "nodes": graph_stats.get("nodes", {}),
                "edges": graph_stats.get("edges", {}),
            },
            "version": "0.1.0",
        },
    )
