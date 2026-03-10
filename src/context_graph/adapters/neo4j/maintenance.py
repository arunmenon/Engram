"""Neo4j batch maintenance queries for memory intelligence.

Provides maintenance operations for the consolidation worker:
- Edge pruning by type and age
- Cold event deletion
- Session event counting
- Graph statistics

All writes use MERGE or targeted DELETE for safety.

Source: ADR-0008
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from neo4j import AsyncDriver

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Cypher Templates
# ---------------------------------------------------------------------------

_DELETE_SIMILAR_EDGES_BY_SCORE = """
MATCH (a:Event)-[r:SIMILAR_TO]->(b:Event)
WHERE a.tenant_id = $tenant_id
  AND r.similarity_score < $min_score
  AND a.occurred_at < $cutoff_iso
DELETE r
RETURN count(r) AS deleted_count
""".strip()

_DELETE_COLD_EVENTS = """
MATCH (e:Event)
WHERE e.tenant_id = $tenant_id
  AND e.occurred_at < $cutoff_iso
  AND (e.importance_score IS NULL OR e.importance_score < $min_importance)
  AND coalesce(e.access_count, 0) < $min_access_count
DETACH DELETE e
RETURN count(e) AS deleted_count
""".strip()

_DELETE_ARCHIVE_EVENTS = """
UNWIND $event_ids AS eid
MATCH (e:Event {event_id: eid})
WHERE e.tenant_id = $tenant_id
DETACH DELETE e
RETURN count(e) AS deleted_count
""".strip()

_GET_SESSION_EVENT_COUNTS = """
MATCH (e:Event)
WHERE e.tenant_id = $tenant_id
  AND e.session_id IS NOT NULL
RETURN e.session_id AS session_id, count(e) AS event_count
ORDER BY event_count DESC
""".strip()

_GET_GRAPH_STATS_NODES = """
CALL {
    MATCH (e:Event)
    WHERE e.tenant_id = $tenant_id
    RETURN 'Event' AS label, count(e) AS cnt
    UNION ALL
    MATCH (n:Entity)
    WHERE n.tenant_id = $tenant_id
    RETURN 'Entity' AS label, count(n) AS cnt
    UNION ALL
    MATCH (s:Summary)
    WHERE s.tenant_id = $tenant_id
    RETURN 'Summary' AS label, count(s) AS cnt
    UNION ALL
    MATCH (u:UserProfile)
    WHERE u.tenant_id = $tenant_id
    RETURN 'UserProfile' AS label, count(u) AS cnt
    UNION ALL
    MATCH (p:Preference)
    WHERE p.tenant_id = $tenant_id
    RETURN 'Preference' AS label, count(p) AS cnt
    UNION ALL
    MATCH (sk:Skill)
    WHERE sk.tenant_id = $tenant_id
    RETURN 'Skill' AS label, count(sk) AS cnt
    UNION ALL
    MATCH (w:Workflow)
    WHERE w.tenant_id = $tenant_id
    RETURN 'Workflow' AS label, count(w) AS cnt
    UNION ALL
    MATCH (b:BehavioralPattern)
    WHERE b.tenant_id = $tenant_id
    RETURN 'BehavioralPattern' AS label, count(b) AS cnt
}
RETURN label, cnt
""".strip()

_GET_GRAPH_STATS_EDGES = """
CALL {
    MATCH (a:Event)-[r:FOLLOWS]->(b:Event)
    WHERE a.tenant_id = $tenant_id
    RETURN 'FOLLOWS' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH (a:Event)-[r:CAUSED_BY]->(b:Event)
    WHERE a.tenant_id = $tenant_id
    RETURN 'CAUSED_BY' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH (a:Event)-[r:SIMILAR_TO]->(b:Event)
    WHERE a.tenant_id = $tenant_id
    RETURN 'SIMILAR_TO' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH (a:Event)-[r:REFERENCES]->(b:Entity)
    WHERE a.tenant_id = $tenant_id
    RETURN 'REFERENCES' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH (a:Summary)-[r:SUMMARIZES]->()
    WHERE a.tenant_id = $tenant_id
    RETURN 'SUMMARIZES' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH (a:Entity)-[r:SAME_AS]->(b:Entity)
    WHERE a.tenant_id = $tenant_id
    RETURN 'SAME_AS' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH (a:Entity)-[r:RELATED_TO]->(b:Entity)
    WHERE a.tenant_id = $tenant_id
    RETURN 'RELATED_TO' AS rel_type, count(r) AS cnt
}
RETURN rel_type, cnt
""".strip()

_GET_ARCHIVE_EVENT_IDS = """
MATCH (e:Event)
WHERE e.tenant_id = $tenant_id
  AND e.occurred_at < $cutoff_iso
RETURN e.event_id AS event_id
""".strip()

# ADR-0014 Amendment: Orphan node cleanup (Gap 8)
_GET_ORPHAN_ENTITY_IDS = """
MATCH (n:Entity)
WHERE n.tenant_id = $tenant_id
  AND NOT (n)--()
RETURN n.entity_id AS entity_id
LIMIT $batch_size
""".strip()

_DELETE_ORPHAN_ENTITIES_BY_IDS = """
UNWIND $entity_ids AS eid
MATCH (n:Entity {entity_id: eid})
WHERE n.tenant_id = $tenant_id
DETACH DELETE n
RETURN count(n) AS deleted_count
""".strip()

_DELETE_ORPHAN_NODES_BY_LABEL = """
MATCH (n:{label})
WHERE n.tenant_id = $tenant_id
  AND NOT (n)--()
WITH n LIMIT $batch_size
DELETE n
RETURN count(n) AS deleted_count
""".strip()

_UPDATE_IMPORTANCE_FROM_CENTRALITY = """
MATCH (e:Event)
WHERE e.tenant_id = $tenant_id
WITH e, size([(x)-[]->(e) | x]) AS in_degree
WHERE in_degree > 0
SET e.importance_score = CASE
    WHEN in_degree >= 10 THEN 10
    WHEN in_degree >= 5 THEN 8
    WHEN in_degree >= 3 THEN 6
    ELSE coalesce(e.importance_score, 5)
END
RETURN count(e) AS updated_count
""".strip()

_MERGE_SUMMARY_NODE = """
MERGE (s:Summary {summary_id: $summary_id})
SET s.scope = $scope,
    s.scope_id = $scope_id,
    s.content = $content,
    s.created_at = $created_at,
    s.event_count = $event_count,
    s.time_range = $time_range,
    s.tenant_id = $tenant_id
""".strip()

_MERGE_SUMMARIZES_EDGE = """
MATCH (s:Summary {summary_id: $summary_id})
MATCH (e:Event {event_id: $event_id})
MERGE (s)-[r:SUMMARIZES]->(e)
SET r.created_at = $created_at
""".strip()


# ---------------------------------------------------------------------------
# Maintenance Functions
# ---------------------------------------------------------------------------


async def delete_edges_by_type_and_age(
    driver: AsyncDriver,
    database: str,
    min_score: float,
    max_age_hours: int,
    tenant_id: str = "default",
) -> int:
    """Delete SIMILAR_TO edges below a similarity score threshold and older than max_age_hours.

    Returns the number of deleted edges.
    """
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    cutoff_iso = cutoff.isoformat()

    async with driver.session(database=database) as session:

        async def _delete(tx: Any) -> int:
            result = await tx.run(
                _DELETE_SIMILAR_EDGES_BY_SCORE,
                {"min_score": min_score, "cutoff_iso": cutoff_iso, "tenant_id": tenant_id},
            )
            record = await result.single()
            return record["deleted_count"] if record else 0

        deleted: int = await session.execute_write(_delete)

    log.info(
        "deleted_similar_edges",
        min_score=min_score,
        max_age_hours=max_age_hours,
        deleted_count=deleted,
    )
    return deleted


async def delete_cold_events(
    driver: AsyncDriver,
    database: str,
    max_age_hours: int,
    min_importance: int,
    min_access_count: int,
    tenant_id: str = "default",
) -> int:
    """Delete cold-tier event nodes that don't meet retention criteria.

    Removes events older than max_age_hours that have importance below
    min_importance AND access_count below min_access_count.

    Returns the number of deleted nodes.
    """
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    cutoff_iso = cutoff.isoformat()

    async with driver.session(database=database) as session:

        async def _delete(tx: Any) -> int:
            result = await tx.run(
                _DELETE_COLD_EVENTS,
                {
                    "cutoff_iso": cutoff_iso,
                    "min_importance": min_importance,
                    "min_access_count": min_access_count,
                    "tenant_id": tenant_id,
                },
            )
            record = await result.single()
            return record["deleted_count"] if record else 0

        deleted: int = await session.execute_write(_delete)

    log.info(
        "deleted_cold_events",
        max_age_hours=max_age_hours,
        min_importance=min_importance,
        min_access_count=min_access_count,
        deleted_count=deleted,
    )
    return deleted


async def delete_archive_events(
    driver: AsyncDriver,
    database: str,
    event_ids: list[str],
    tenant_id: str = "default",
) -> int:
    """Delete archived event nodes by their IDs. DETACH DELETE removes edges too.

    Returns the number of deleted nodes.
    """
    if not event_ids:
        return 0

    async with driver.session(database=database) as session:

        async def _delete(tx: Any) -> int:
            result = await tx.run(
                _DELETE_ARCHIVE_EVENTS,
                {"event_ids": event_ids, "tenant_id": tenant_id},
            )
            record = await result.single()
            return record["deleted_count"] if record else 0

        deleted: int = await session.execute_write(_delete)

    log.info("deleted_archive_events", requested=len(event_ids), deleted_count=deleted)
    return deleted


async def get_session_event_counts(
    driver: AsyncDriver,
    database: str,
    tenant_id: str = "default",
) -> dict[str, int]:
    """Count events per session in the Neo4j graph.

    Returns a dict of {session_id: event_count}.
    """
    async with driver.session(database=database) as session:
        result = await session.run(_GET_SESSION_EVENT_COUNTS, {"tenant_id": tenant_id})
        records = [record async for record in result]

    counts: dict[str, int] = {}
    for record in records:
        session_id = record["session_id"]
        event_count = record["event_count"]
        counts[session_id] = event_count

    log.debug("session_event_counts", session_count=len(counts))
    return counts


async def get_graph_stats(
    driver: AsyncDriver,
    database: str,
    tenant_id: str = "default",
) -> dict[str, Any]:
    """Get node and edge counts by type for admin/monitoring.

    Returns a dict with 'nodes' and 'edges' sub-dicts mapping type names to counts.
    """
    node_counts: dict[str, int] = {}
    edge_counts: dict[str, int] = {}
    params = {"tenant_id": tenant_id}

    async with driver.session(database=database) as session:
        node_result = await session.run(_GET_GRAPH_STATS_NODES, params)
        node_records = [record async for record in node_result]

        edge_result = await session.run(_GET_GRAPH_STATS_EDGES, params)
        edge_records = [record async for record in edge_result]

    for record in node_records:
        node_counts[record["label"]] = record["cnt"]

    for record in edge_records:
        edge_counts[record["rel_type"]] = record["cnt"]

    total_nodes = sum(node_counts.values())
    total_edges = sum(edge_counts.values())

    log.debug("graph_stats", total_nodes=total_nodes, total_edges=total_edges)

    return {
        "nodes": node_counts,
        "edges": edge_counts,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
    }


async def write_summary_with_edges(
    driver: AsyncDriver,
    database: str,
    summary_id: str,
    scope: str,
    scope_id: str,
    content: str,
    created_at: str,
    event_count: int,
    time_range: list[str],
    event_ids: list[str],
    tenant_id: str = "default",
) -> None:
    """Write a summary node and SUMMARIZES edges to the covered events.

    Uses MERGE for idempotent writes.
    """
    async with driver.session(database=database) as session:

        async def _write(tx: Any) -> None:
            # Create the summary node
            await tx.run(
                _MERGE_SUMMARY_NODE,
                {
                    "summary_id": summary_id,
                    "scope": scope,
                    "scope_id": scope_id,
                    "content": content,
                    "created_at": created_at,
                    "event_count": event_count,
                    "time_range": time_range,
                    "tenant_id": tenant_id,
                },
            )
            # Create SUMMARIZES edges to each covered event
            for event_id in event_ids:
                await tx.run(
                    _MERGE_SUMMARIZES_EDGE,
                    {
                        "summary_id": summary_id,
                        "event_id": event_id,
                        "created_at": created_at,
                    },
                )

        await session.execute_write(_write)

    log.info(
        "wrote_summary_with_edges",
        summary_id=summary_id,
        event_count=event_count,
        edge_count=len(event_ids),
    )


async def get_archive_event_ids(
    driver: AsyncDriver,
    database: str,
    max_age_hours: int,
    tenant_id: str = "default",
) -> list[str]:
    """Get event IDs older than the specified age for archive-tier pruning.

    Returns a list of event_id strings.
    """
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    cutoff_iso = cutoff.isoformat()

    async with driver.session(database=database) as session:
        result = await session.run(
            _GET_ARCHIVE_EVENT_IDS,
            {"cutoff_iso": cutoff_iso, "tenant_id": tenant_id},
        )
        records = [record async for record in result]

    return [r["event_id"] for r in records]


async def _delete_orphan_entities(
    driver: AsyncDriver,
    database: str,
    batch_size: int,
    tenant_id: str = "default",
) -> tuple[int, list[str]]:
    """Collect orphan Entity IDs, delete them, return total + IDs."""
    total_deleted = 0
    all_entity_ids: list[str] = []

    while True:
        async with driver.session(database=database) as session:

            async def _get_ids(tx: Any) -> list[str]:
                result = await tx.run(
                    _GET_ORPHAN_ENTITY_IDS,
                    {"batch_size": batch_size, "tenant_id": tenant_id},
                )
                records = [r async for r in result]
                return [r["entity_id"] for r in records]

            entity_ids: list[str] = await session.execute_read(_get_ids)

        if not entity_ids:
            break

        all_entity_ids.extend(entity_ids)

        async with driver.session(database=database) as session:

            async def _delete(tx: Any, ids: list[str] = entity_ids) -> int:
                result = await tx.run(
                    _DELETE_ORPHAN_ENTITIES_BY_IDS,
                    {"entity_ids": ids, "tenant_id": tenant_id},
                )
                record = await result.single()
                return record["deleted_count"] if record else 0

            batch_deleted: int = await session.execute_write(_delete)

        total_deleted += batch_deleted

        if batch_deleted < batch_size:
            break

    return total_deleted, all_entity_ids


async def _delete_orphan_nodes_for_label(
    driver: AsyncDriver,
    database: str,
    label: str,
    batch_size: int,
    tenant_id: str = "default",
) -> int:
    """Delete orphan nodes for a single non-Entity label. Returns total deleted."""
    query = _DELETE_ORPHAN_NODES_BY_LABEL.replace("{label}", label)
    total_deleted = 0

    while True:
        async with driver.session(database=database) as session:

            async def _delete_batch(tx: Any, q: str = query) -> int:
                result = await tx.run(q, {"batch_size": batch_size, "tenant_id": tenant_id})
                record = await result.single()
                return record["deleted_count"] if record else 0

            batch_deleted: int = await session.execute_write(_delete_batch)

        total_deleted += batch_deleted

        if batch_deleted == 0:
            break

    return total_deleted


async def delete_orphan_nodes(
    driver: AsyncDriver,
    database: str,
    batch_size: int = 500,
    tenant_id: str = "default",
) -> tuple[dict[str, int], list[str]]:
    """Delete orphaned nodes (no relationships) and return counts + deleted entity IDs.

    Processes 5 orphan-eligible labels: Entity, Preference, Skill, Workflow,
    BehavioralPattern. UserProfile and Summary are exempt (ADR-0014 Amendment).

    Entity embeddings are stored as Neo4j node properties and are automatically
    removed when nodes are deleted via DETACH DELETE.

    Returns a tuple of:
      - dict mapping label -> total deleted count
      - list of deleted entity IDs (for caller logging/auditing)
    """
    counts: dict[str, int] = {}
    deleted_entity_ids: list[str] = []

    # Entity orphan cleanup: collect IDs first for embedding cleanup
    entity_total, entity_ids = await _delete_orphan_entities(
        driver, database, batch_size, tenant_id=tenant_id
    )
    counts["Entity"] = entity_total
    deleted_entity_ids.extend(entity_ids)

    # Non-Entity orphan-eligible labels
    for label in ("Preference", "Skill", "Workflow", "BehavioralPattern"):
        counts[label] = await _delete_orphan_nodes_for_label(
            driver, database, label, batch_size, tenant_id=tenant_id
        )

    total = sum(counts.values())
    if total > 0:
        log.info(
            "orphan_nodes_deleted",
            counts=counts,
            total=total,
            deleted_entity_ids_count=len(deleted_entity_ids),
        )
    else:
        log.debug("no_orphan_nodes_found")

    return counts, deleted_entity_ids


async def compact_session_events(
    driver: AsyncDriver,
    database: str,
    session_id: str,
    tenant_id: str = "default",
    min_events: int = 50,
    keep_recent: int = 10,
) -> int:
    """Compact old events in a session by deleting those already covered by summaries.

    Preserves:
    - The most recent ``keep_recent`` events (always keep for freshness)
    - Events referenced by entities from other sessions (cross-session links)

    Only deletes events that:
    1. Are covered by a Summary node (SUMMARIZES edge exists)
    2. Are not in the most recent ``keep_recent`` events
    3. Are not cross-referenced by entities in other sessions

    Returns the number of deleted events.
    """
    from datetime import UTC, datetime

    from context_graph.adapters.neo4j import queries

    # Step 1: Count events in session; skip if below threshold
    async with driver.session(database=database) as session:
        result = await session.run(
            queries.COUNT_SESSION_EVENTS,
            {"session_id": session_id, "tenant_id": tenant_id},
        )
        record = await result.single()
        event_count = record["event_count"] if record else 0

    if event_count < min_events:
        log.debug(
            "compact_skip_too_few_events",
            session_id=session_id,
            event_count=event_count,
            min_events=min_events,
        )
        return 0

    cutoff_iso = datetime.now(UTC).isoformat()

    # Step 2: Get summarized event IDs (covered by a Summary node)
    async with driver.session(database=database) as session:
        result = await session.run(
            queries.GET_SUMMARIZED_EVENT_IDS,
            {"session_id": session_id, "tenant_id": tenant_id, "cutoff_iso": cutoff_iso},
        )
        records = [r async for r in result]
    summarized_ids = {r["event_id"] for r in records}

    if not summarized_ids:
        log.debug("compact_no_summarized_events", session_id=session_id)
        return 0

    # Step 3: Get recent event IDs to keep
    async with driver.session(database=database) as session:
        result = await session.run(
            queries.GET_RECENT_EVENT_IDS,
            {"session_id": session_id, "tenant_id": tenant_id, "keep_recent": keep_recent},
        )
        records = [r async for r in result]
    recent_ids = {r["event_id"] for r in records}

    # Step 4: Get cross-referenced event IDs to keep
    async with driver.session(database=database) as session:
        result = await session.run(
            queries.GET_CROSS_REFERENCED_EVENT_IDS,
            {"session_id": session_id, "tenant_id": tenant_id},
        )
        records = [r async for r in result]
    cross_referenced_ids = {r["event_id"] for r in records}

    # Step 5: Compute deletable = summarized - recent - cross_referenced
    deletable_ids = summarized_ids - recent_ids - cross_referenced_ids

    if not deletable_ids:
        log.debug("compact_nothing_to_delete", session_id=session_id)
        return 0

    # Step 6: DETACH DELETE in batches of 500
    total_deleted = 0
    deletable_list = list(deletable_ids)
    batch_size = 500

    for i in range(0, len(deletable_list), batch_size):
        batch = deletable_list[i : i + batch_size]

        async with driver.session(database=database) as session:

            async def _delete_batch(tx: Any, ids: list[str] = batch) -> int:
                result = await tx.run(
                    queries.DETACH_DELETE_EVENTS_BY_IDS,
                    {"event_ids": ids, "tenant_id": tenant_id},
                )
                record = await result.single()
                return record["deleted_count"] if record else 0

            batch_deleted: int = await session.execute_write(_delete_batch)

        total_deleted += batch_deleted

    log.info(
        "compact_session_events",
        session_id=session_id,
        summarized=len(summarized_ids),
        recent_kept=len(recent_ids),
        cross_referenced_kept=len(cross_referenced_ids),
        deleted=total_deleted,
    )
    return total_deleted


async def compact_stale_sessions(
    driver: AsyncDriver,
    database: str,
    tenant_id: str = "default",
    min_age_hours: int = 168,
    min_events: int = 50,
    keep_recent: int = 10,
    batch_limit: int = 10,
) -> int:
    """Find stale sessions and compact their events.

    A session is stale when its most recent event is older than ``min_age_hours``
    and it has at least ``min_events`` events.

    Returns the total number of compacted (deleted) events across all sessions.
    """
    from datetime import UTC, datetime, timedelta

    from context_graph.adapters.neo4j import queries

    cutoff = datetime.now(UTC) - timedelta(hours=min_age_hours)
    cutoff_iso = cutoff.isoformat()

    async with driver.session(database=database) as session:
        result = await session.run(
            queries.GET_STALE_SESSIONS,
            {
                "tenant_id": tenant_id,
                "min_events": min_events,
                "cutoff_iso": cutoff_iso,
                "batch_limit": batch_limit,
            },
        )
        records = [r async for r in result]

    if not records:
        log.debug("compact_no_stale_sessions", tenant_id=tenant_id)
        return 0

    total_compacted = 0
    for record in records:
        session_id = record["session_id"]
        compacted = await compact_session_events(
            driver,
            database,
            session_id,
            tenant_id=tenant_id,
            min_events=min_events,
            keep_recent=keep_recent,
        )
        total_compacted += compacted

    log.info(
        "compact_stale_sessions",
        tenant_id=tenant_id,
        sessions_processed=len(records),
        total_compacted=total_compacted,
    )
    return total_compacted


async def get_tenant_node_budget(
    driver: AsyncDriver,
    database: str,
    tenant_id: str = "default",
    max_nodes: int = 100_000,
) -> dict[str, Any]:
    """Query node counts per label and return budget utilization info.

    Returns a dict with:
    - total_nodes: total node count for the tenant
    - by_label: dict mapping label name to count
    - budget: the max_nodes budget
    - utilization_pct: percentage of budget used
    """
    from context_graph.adapters.neo4j import queries

    async with driver.session(database=database) as session:
        result = await session.run(
            queries.GET_TENANT_NODE_COUNTS,
            {"tenant_id": tenant_id},
        )
        records = [r async for r in result]

    by_label: dict[str, int] = {}
    for record in records:
        by_label[record["label"]] = record["cnt"]

    total_nodes = sum(by_label.values())
    utilization_pct = (total_nodes / max_nodes * 100) if max_nodes > 0 else 0.0

    return {
        "total_nodes": total_nodes,
        "by_label": by_label,
        "budget": max_nodes,
        "utilization_pct": utilization_pct,
    }


async def update_importance_from_centrality(
    driver: AsyncDriver,
    database: str,
    tenant_id: str = "default",
) -> int:
    """Recompute importance scores based on in-degree centrality.

    Events with higher in-degree get boosted importance scores:
    - in_degree >= 10: importance = 10
    - in_degree >= 5: importance = 8
    - in_degree >= 3: importance = 6
    - otherwise: keep existing or default to 5

    Returns the number of updated nodes.
    """
    async with driver.session(database=database) as session:

        async def _update(tx: Any) -> int:
            result = await tx.run(
                _UPDATE_IMPORTANCE_FROM_CENTRALITY,
                {"tenant_id": tenant_id},
            )
            record = await result.single()
            return record["updated_count"] if record else 0

        updated: int = await session.execute_write(_update)

    log.info("updated_importance_from_centrality", updated_count=updated)
    return updated
