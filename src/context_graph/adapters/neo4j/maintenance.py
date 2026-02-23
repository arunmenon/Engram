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
WHERE r.similarity_score < $min_score
  AND a.occurred_at < $cutoff_iso
DELETE r
RETURN count(r) AS deleted_count
""".strip()

_DELETE_COLD_EVENTS = """
MATCH (e:Event)
WHERE e.occurred_at < $cutoff_iso
  AND (e.importance_score IS NULL OR e.importance_score < $min_importance)
  AND coalesce(e.access_count, 0) < $min_access_count
DETACH DELETE e
RETURN count(e) AS deleted_count
""".strip()

_DELETE_ARCHIVE_EVENTS = """
UNWIND $event_ids AS eid
MATCH (e:Event {event_id: eid})
DETACH DELETE e
RETURN count(e) AS deleted_count
""".strip()

_GET_SESSION_EVENT_COUNTS = """
MATCH (e:Event)
WHERE e.session_id IS NOT NULL
RETURN e.session_id AS session_id, count(e) AS event_count
ORDER BY event_count DESC
""".strip()

_GET_GRAPH_STATS_NODES = """
CALL {
    MATCH (e:Event) RETURN 'Event' AS label, count(e) AS cnt
    UNION ALL
    MATCH (n:Entity) RETURN 'Entity' AS label, count(n) AS cnt
    UNION ALL
    MATCH (s:Summary) RETURN 'Summary' AS label, count(s) AS cnt
    UNION ALL
    MATCH (u:UserProfile) RETURN 'UserProfile' AS label, count(u) AS cnt
    UNION ALL
    MATCH (p:Preference) RETURN 'Preference' AS label, count(p) AS cnt
    UNION ALL
    MATCH (sk:Skill) RETURN 'Skill' AS label, count(sk) AS cnt
    UNION ALL
    MATCH (w:Workflow) RETURN 'Workflow' AS label, count(w) AS cnt
    UNION ALL
    MATCH (b:BehavioralPattern) RETURN 'BehavioralPattern' AS label, count(b) AS cnt
}
RETURN label, cnt
""".strip()

_GET_GRAPH_STATS_EDGES = """
CALL {
    MATCH ()-[r:FOLLOWS]->() RETURN 'FOLLOWS' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:CAUSED_BY]->() RETURN 'CAUSED_BY' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:SIMILAR_TO]->() RETURN 'SIMILAR_TO' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:REFERENCES]->() RETURN 'REFERENCES' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:SUMMARIZES]->() RETURN 'SUMMARIZES' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:SAME_AS]->() RETURN 'SAME_AS' AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:RELATED_TO]->() RETURN 'RELATED_TO' AS rel_type, count(r) AS cnt
}
RETURN rel_type, cnt
""".strip()

_GET_ARCHIVE_EVENT_IDS = """
MATCH (e:Event)
WHERE e.occurred_at < $cutoff_iso
RETURN e.event_id AS event_id
""".strip()

# ADR-0014 Amendment: Orphan node cleanup (Gap 8)
_GET_ORPHAN_ENTITY_IDS = """
MATCH (n:Entity)
WHERE NOT (n)--()
RETURN n.entity_id AS entity_id
LIMIT $batch_size
""".strip()

_DELETE_ORPHAN_ENTITIES_BY_IDS = """
UNWIND $entity_ids AS eid
MATCH (n:Entity {entity_id: eid})
DETACH DELETE n
RETURN count(n) AS deleted_count
""".strip()

_DELETE_ORPHAN_NODES_BY_LABEL = """
MATCH (n:{label})
WHERE NOT (n)--()
WITH n LIMIT $batch_size
DELETE n
RETURN count(n) AS deleted_count
""".strip()

_UPDATE_IMPORTANCE_FROM_CENTRALITY = """
MATCH (e:Event)
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
    s.time_range = $time_range
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
                {"min_score": min_score, "cutoff_iso": cutoff_iso},
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
                {"event_ids": event_ids},
            )
            record = await result.single()
            return record["deleted_count"] if record else 0

        deleted: int = await session.execute_write(_delete)

    log.info("deleted_archive_events", requested=len(event_ids), deleted_count=deleted)
    return deleted


async def get_session_event_counts(
    driver: AsyncDriver,
    database: str,
) -> dict[str, int]:
    """Count events per session in the Neo4j graph.

    Returns a dict of {session_id: event_count}.
    """
    async with driver.session(database=database) as session:
        result = await session.run(_GET_SESSION_EVENT_COUNTS)
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
) -> dict[str, Any]:
    """Get node and edge counts by type for admin/monitoring.

    Returns a dict with 'nodes' and 'edges' sub-dicts mapping type names to counts.
    """
    node_counts: dict[str, int] = {}
    edge_counts: dict[str, int] = {}

    async with driver.session(database=database) as session:
        node_result = await session.run(_GET_GRAPH_STATS_NODES)
        node_records = [record async for record in node_result]

        edge_result = await session.run(_GET_GRAPH_STATS_EDGES)
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
) -> list[str]:
    """Get event IDs older than the specified age for archive-tier pruning.

    Returns a list of event_id strings.
    """
    from datetime import UTC, datetime, timedelta

    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    cutoff_iso = cutoff.isoformat()

    async with driver.session(database=database) as session:
        result = await session.run(_GET_ARCHIVE_EVENT_IDS, {"cutoff_iso": cutoff_iso})
        records = [record async for record in result]

    return [r["event_id"] for r in records]


async def _delete_orphan_entities(
    driver: AsyncDriver,
    database: str,
    batch_size: int,
) -> tuple[int, list[str]]:
    """Collect orphan Entity IDs, delete them, return total + IDs."""
    total_deleted = 0
    all_entity_ids: list[str] = []

    while True:
        async with driver.session(database=database) as session:

            async def _get_ids(tx: Any) -> list[str]:
                result = await tx.run(
                    _GET_ORPHAN_ENTITY_IDS,
                    {"batch_size": batch_size},
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
                    {"entity_ids": ids},
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
) -> int:
    """Delete orphan nodes for a single non-Entity label. Returns total deleted."""
    query = _DELETE_ORPHAN_NODES_BY_LABEL.replace("{label}", label)
    total_deleted = 0

    while True:
        async with driver.session(database=database) as session:

            async def _delete_batch(tx: Any, q: str = query) -> int:
                result = await tx.run(q, {"batch_size": batch_size})
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
) -> tuple[dict[str, int], list[str]]:
    """Delete orphaned nodes (no relationships) and return counts + deleted entity IDs.

    Processes 5 orphan-eligible labels: Entity, Preference, Skill, Workflow,
    BehavioralPattern. UserProfile and Summary are exempt (ADR-0014 Amendment).

    For Entity nodes, entity_ids are collected before deletion so callers
    can clean up associated embeddings (Gap 9).

    Returns a tuple of:
      - dict mapping label -> total deleted count
      - list of deleted entity IDs (for embedding cleanup)
    """
    counts: dict[str, int] = {}
    deleted_entity_ids: list[str] = []

    # Entity orphan cleanup: collect IDs first for embedding cleanup
    entity_total, entity_ids = await _delete_orphan_entities(driver, database, batch_size)
    counts["Entity"] = entity_total
    deleted_entity_ids.extend(entity_ids)

    # Non-Entity orphan-eligible labels
    for label in ("Preference", "Skill", "Workflow", "BehavioralPattern"):
        counts[label] = await _delete_orphan_nodes_for_label(driver, database, label, batch_size)

    total = sum(counts.values())
    if total > 0:
        log.info(
            "orphan_nodes_deleted",
            counts=counts,
            total=total,
            entity_ids_for_embedding_cleanup=len(deleted_entity_ids),
        )
    else:
        log.debug("no_orphan_nodes_found")

    return counts, deleted_entity_ids


async def update_importance_from_centrality(
    driver: AsyncDriver,
    database: str,
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
            result = await tx.run(_UPDATE_IMPORTANCE_FROM_CENTRALITY)
            record = await result.single()
            return record["updated_count"] if record else 0

        updated: int = await session.execute_write(_update)

    log.info("updated_importance_from_centrality", updated_count=updated)
    return updated
