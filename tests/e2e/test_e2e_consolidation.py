"""E2E tests for Consolidation & Forgetting (Consumer 4 + admin API).

Tests the consolidation/forgetting pipeline against the running stack:
1. Admin stats endpoint
2. Manual reconsolidate trigger
3. Detailed health endpoint
4. Prune dry run
5. Session stream cleanup (direct function)
6. Dedup set maintenance (direct function)
7. Orphan node cleanup (direct function)
8. Archive before delete (direct function + filesystem archive)
9. Cold event pruning in Neo4j (via admin API)

Prerequisites:
    - docker-compose up (redis, neo4j, api, workers)
    - pip install -e ".[dev]"

Usage:
    python -m pytest tests/e2e/test_e2e_consolidation.py -v
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import orjson
import pytest
import pytest_asyncio
from neo4j import AsyncGraphDatabase
from redis.asyncio import Redis

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "http://localhost:8000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "engram-dev-password"
NEO4J_DATABASE = "neo4j"
ARCHIVE_PATH = Path("/tmp/claude/engram-e2e-consolidation-archives")

# Test isolation prefix
PREFIX = "e2e-consolidation-"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def http_client():
    async with httpx.AsyncClient(base_url=API_URL, timeout=15) as client:
        yield client


@pytest_asyncio.fixture
async def redis_client():
    client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def neo4j_driver():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    await driver.close()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_neo4j(neo4j_driver):
    """Clean up e2e-consolidation- prefixed nodes before and after each test."""
    async def _cleanup():
        async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
            await session.run(
                "MATCH (n) WHERE n.session_id STARTS WITH $prefix "
                "OR n.entity_id STARTS WITH $prefix "
                "OR n.event_id STARTS WITH $prefix "
                "OR n.summary_id STARTS WITH $prefix "
                "DETACH DELETE n",
                {"prefix": PREFIX},
            )

    await _cleanup()
    yield
    await _cleanup()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_redis(redis_client):
    """Clean up e2e-consolidation- prefixed Redis keys after each test."""
    yield
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor,
            match=f"*{PREFIX}*",
            count=100,
        )
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    session_id: str | None = None,
    event_type: str = "tool.execute",
    importance_hint: int = 5,
    event_id: str | None = None,
) -> dict:
    """Create a valid event payload for /v1/events."""
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "session_id": session_id or f"{PREFIX}{uuid.uuid4().hex[:8]}",
        "agent_id": f"{PREFIX}agent",
        "trace_id": f"trace-{uuid.uuid4().hex[:8]}",
        "payload_ref": f"ref://{uuid.uuid4().hex[:8]}",
        "importance_hint": importance_hint,
    }


# ---------------------------------------------------------------------------
# Test 1: Stats endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_endpoint(http_client: httpx.AsyncClient):
    """GET /v1/admin/stats returns valid response with redis.stream_length,
    total_nodes, and total_edges."""
    resp = await http_client.get("/v1/admin/stats")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "redis" in body, f"Missing 'redis' key: {body}"
    assert "stream_length" in body["redis"], f"Missing stream_length: {body}"
    assert isinstance(body["redis"]["stream_length"], int)
    assert "total_nodes" in body
    assert "total_edges" in body
    assert isinstance(body["total_nodes"], int)
    assert isinstance(body["total_edges"], int)
    assert "nodes" in body
    assert "edges" in body


# ---------------------------------------------------------------------------
# Test 2: Manual reconsolidate trigger
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconsolidate_trigger(http_client: httpx.AsyncClient):
    """POST /v1/admin/reconsolidate returns 200 OK with valid response shape."""
    resp = await http_client.post("/v1/admin/reconsolidate")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "sessions_processed" in body
    assert "summaries_created" in body
    assert "events_processed" in body
    assert isinstance(body["sessions_processed"], int)
    assert isinstance(body["summaries_created"], int)
    assert isinstance(body["events_processed"], int)


# ---------------------------------------------------------------------------
# Test 3: Detailed health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detailed_health(http_client: httpx.AsyncClient):
    """GET /v1/admin/health/detailed returns more info than basic health."""
    basic_resp = await http_client.get("/v1/health")
    assert basic_resp.status_code == 200

    detailed_resp = await http_client.get("/v1/admin/health/detailed")
    assert detailed_resp.status_code == 200

    basic_body = basic_resp.json()
    detailed_body = detailed_resp.json()

    # Detailed health should have more keys
    assert "status" in detailed_body
    assert "redis" in detailed_body
    assert "neo4j" in detailed_body
    assert "version" in detailed_body

    # Redis section should have connection status and stream length
    assert "connected" in detailed_body["redis"]
    assert "stream_length" in detailed_body["redis"]
    assert detailed_body["redis"]["connected"] is True

    # Neo4j section should have connection status and node/edge breakdown
    assert "connected" in detailed_body["neo4j"]
    assert detailed_body["neo4j"]["connected"] is True
    assert "nodes" in detailed_body["neo4j"]
    assert "edges" in detailed_body["neo4j"]

    # Detailed body should have richer content than basic
    # Basic health returns simple booleans for redis/neo4j;
    # detailed health returns nested dicts with connection info + stats
    assert isinstance(detailed_body["redis"], dict), (
        "Detailed redis should be a dict, not a simple value"
    )
    assert isinstance(detailed_body["neo4j"], dict), (
        "Detailed neo4j should be a dict, not a simple value"
    )
    # Basic health has simple boolean values for redis/neo4j
    assert not isinstance(basic_body.get("redis"), dict) or \
        len(detailed_body["redis"]) > len(basic_body.get("redis", {})), (
        "Detailed redis should have more info than basic"
    )


# ---------------------------------------------------------------------------
# Test 4: Prune dry run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prune_dry_run(http_client: httpx.AsyncClient):
    """POST /v1/admin/prune with dry_run=true returns valid response shape
    without deleting anything."""
    resp = await http_client.post(
        "/v1/admin/prune",
        json={"tier": "cold", "dry_run": True},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "pruned_edges" in body
    assert "pruned_nodes" in body
    assert "dry_run" in body
    assert body["dry_run"] is True
    assert isinstance(body["pruned_edges"], int)
    assert isinstance(body["pruned_nodes"], int)


@pytest.mark.asyncio
async def test_prune_warm_dry_run(http_client: httpx.AsyncClient):
    """POST /v1/admin/prune with tier=warm, dry_run=true also works."""
    resp = await http_client.post(
        "/v1/admin/prune",
        json={"tier": "warm", "dry_run": True},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["dry_run"] is True
    assert "pruned_edges" in body


# ---------------------------------------------------------------------------
# Test 5: Session stream cleanup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_stream_cleanup(redis_client: Redis):
    """Create an old session stream, clean it, verify deleted."""
    from context_graph.adapters.redis.trimmer import cleanup_session_streams

    test_key = f"events:session:{PREFIX}old"

    # Create a test session stream with an entry
    await redis_client.xadd(test_key, {"event_id": "test-old-session"})
    assert await redis_client.exists(test_key), "Stream should exist before cleanup"

    # Clean with max_age_hours=0 (everything is "old")
    deleted = await cleanup_session_streams(
        redis_client=redis_client,
        prefix=f"events:session:{PREFIX}",
        max_age_hours=0,
    )

    assert deleted >= 1, f"Expected at least 1 deleted, got {deleted}"
    assert not await redis_client.exists(test_key), "Stream should be deleted after cleanup"


@pytest.mark.asyncio
async def test_session_stream_fresh_not_cleaned(redis_client: Redis):
    """Fresh session streams should NOT be cleaned up."""
    from context_graph.adapters.redis.trimmer import cleanup_session_streams

    test_key = f"events:session:{PREFIX}fresh"

    # Create a session stream with a recent entry
    await redis_client.xadd(test_key, {"event_id": "test-fresh-session"})

    # Clean with max_age_hours=24 (stream is fresh)
    deleted = await cleanup_session_streams(
        redis_client=redis_client,
        prefix=f"events:session:{PREFIX}",
        max_age_hours=24,
    )

    assert deleted == 0, f"Fresh stream should not be deleted, got {deleted} deletions"
    assert await redis_client.exists(test_key), "Fresh stream should still exist"

    # Cleanup
    await redis_client.delete(test_key)


# ---------------------------------------------------------------------------
# Test 6: Dedup set maintenance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dedup_set_cleanup(redis_client: Redis):
    """Add old + fresh entries to a dedup sorted set, clean, verify."""
    from context_graph.adapters.redis.trimmer import cleanup_dedup_set

    test_key = f"dedup:{PREFIX}test"
    now_ms = int(time.time() * 1000)
    old_ms = int((datetime.now(UTC) - timedelta(days=100)).timestamp() * 1000)

    # Add both old and fresh entries
    await redis_client.zadd(test_key, {"old-event-1": old_ms, "old-event-2": old_ms - 1000})
    await redis_client.zadd(test_key, {"fresh-event": now_ms})

    # Verify 3 entries exist
    total_before = await redis_client.zcard(test_key)
    assert total_before == 3, f"Expected 3 entries before cleanup, got {total_before}"

    # Clean with 90-day retention
    removed = await cleanup_dedup_set(
        redis_client=redis_client,
        dedup_key=test_key,
        retention_ceiling_days=90,
    )

    assert removed == 2, f"Expected 2 removed, got {removed}"
    assert await redis_client.zscore(test_key, "fresh-event") is not None, (
        "Fresh event should be preserved"
    )
    assert await redis_client.zscore(test_key, "old-event-1") is None, (
        "Old event 1 should be removed"
    )
    assert await redis_client.zscore(test_key, "old-event-2") is None, (
        "Old event 2 should be removed"
    )


# ---------------------------------------------------------------------------
# Test 7: Orphan node cleanup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orphan_node_cleanup(neo4j_driver):
    """Create an isolated Entity node, run delete_orphan_nodes, verify deleted."""
    from context_graph.adapters.neo4j.maintenance import delete_orphan_nodes

    entity_id = f"{PREFIX}orphan-{uuid.uuid4().hex[:8]}"

    # Create an isolated Entity node (no edges)
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            "CREATE (e:Entity {entity_id: $entity_id, name: 'orphan-test', "
            "entity_type: 'test'})",
            {"entity_id": entity_id},
        )

    # Verify it exists
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            "MATCH (e:Entity {entity_id: $entity_id}) RETURN e",
            {"entity_id": entity_id},
        )
        records = [r async for r in result]
        assert len(records) == 1, f"Expected 1 orphan node, got {len(records)}"

    # Run orphan cleanup
    counts, deleted_ids = await delete_orphan_nodes(
        driver=neo4j_driver,
        database=NEO4J_DATABASE,
        batch_size=500,
    )

    # Verify the orphan was deleted
    assert entity_id in deleted_ids, (
        f"Expected {entity_id} in deleted IDs: {deleted_ids}"
    )
    assert counts.get("Entity", 0) >= 1

    # Confirm it no longer exists
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            "MATCH (e:Entity {entity_id: $entity_id}) RETURN e",
            {"entity_id": entity_id},
        )
        records = [r async for r in result]
        assert len(records) == 0, "Orphan node should have been deleted"


@pytest.mark.asyncio
async def test_connected_node_not_orphaned(neo4j_driver):
    """Entity with an edge should NOT be deleted by orphan cleanup."""
    from context_graph.adapters.neo4j.maintenance import delete_orphan_nodes

    entity_id = f"{PREFIX}connected-{uuid.uuid4().hex[:8]}"
    event_id = f"{PREFIX}evt-{uuid.uuid4().hex[:8]}"

    # Create an Entity connected to an Event
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            "CREATE (ev:Event {event_id: $event_id, session_id: $sid, "
            "event_type: 'test', occurred_at: datetime()})"
            "-[:REFERENCES]->"
            "(e:Entity {entity_id: $entity_id, name: 'connected', "
            "entity_type: 'test'})",
            {"event_id": event_id, "entity_id": entity_id, "sid": f"{PREFIX}session"},
        )

    # Run orphan cleanup
    _, deleted_ids = await delete_orphan_nodes(
        driver=neo4j_driver,
        database=NEO4J_DATABASE,
    )

    # The connected entity should NOT be deleted
    assert entity_id not in deleted_ids, (
        f"Connected entity {entity_id} should not be deleted"
    )

    # Verify it still exists
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            "MATCH (e:Entity {entity_id: $entity_id}) RETURN e",
            {"entity_id": entity_id},
        )
        records = [r async for r in result]
        assert len(records) == 1, "Connected entity should still exist"


# ---------------------------------------------------------------------------
# Test 8: Archive before delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_before_delete(redis_client: Redis):
    """Create an old Redis JSON event, archive it, verify archived + deleted."""
    from context_graph.adapters.fs.archive import FilesystemArchiveStore
    from context_graph.adapters.redis.trimmer import archive_and_delete_expired_events

    ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
    archive_store = FilesystemArchiveStore(base_path=ARCHIVE_PATH)

    # Create an old event (100 days ago)
    old_epoch_ms = int((datetime.now(UTC) - timedelta(days=100)).timestamp() * 1000)
    event_id = f"{PREFIX}archive-{uuid.uuid4().hex[:8]}"
    old_event = {
        "event_id": event_id,
        "event_type": "agent.invoke",
        "occurred_at_epoch_ms": old_epoch_ms,
        "session_id": f"{PREFIX}archive-session",
        "agent_id": f"{PREFIX}agent",
    }
    redis_key = f"e2e-cons-evt:{event_id}"
    await redis_client.execute_command(
        "JSON.SET", redis_key, "$", orjson.dumps(old_event).decode()
    )

    # Verify it exists
    assert await redis_client.exists(redis_key), "Old event should exist in Redis"

    # Run archive-before-delete
    archived, deleted = await archive_and_delete_expired_events(
        redis_client=redis_client,
        key_prefix="e2e-cons-evt:",
        max_age_days=90,
        archive_store=archive_store,
    )

    assert archived >= 1, f"Expected at least 1 archived, got {archived}"
    assert deleted >= 1, f"Expected at least 1 deleted, got {deleted}"
    assert not await redis_client.exists(redis_key), (
        "Old event should be deleted from Redis after archival"
    )

    # Verify archive is readable
    archives = await archive_store.list_archives()
    assert len(archives) >= 1, "At least one archive file should exist"

    # Find our event in the archives
    found = False
    for archive in archives:
        restored = await archive_store.restore_archive(archive["archive_id"])
        if any(e.get("event_id") == event_id for e in restored):
            found = True
            break
    assert found, f"Archived event {event_id} should be restorable from archive"


@pytest.mark.asyncio
async def test_archive_preserves_fresh_events(redis_client: Redis):
    """Fresh events should NOT be archived or deleted."""
    from context_graph.adapters.fs.archive import FilesystemArchiveStore
    from context_graph.adapters.redis.trimmer import archive_and_delete_expired_events

    ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
    archive_store = FilesystemArchiveStore(base_path=ARCHIVE_PATH)

    # Create a fresh event
    fresh_epoch_ms = int(datetime.now(UTC).timestamp() * 1000)
    event_id = f"{PREFIX}fresh-{uuid.uuid4().hex[:8]}"
    fresh_event = {
        "event_id": event_id,
        "event_type": "tool.execute",
        "occurred_at_epoch_ms": fresh_epoch_ms,
        "session_id": f"{PREFIX}fresh-session",
    }
    redis_key = f"e2e-cons-fresh:{event_id}"
    await redis_client.execute_command(
        "JSON.SET", redis_key, "$", orjson.dumps(fresh_event).decode()
    )

    # Run archive-before-delete
    archived, deleted = await archive_and_delete_expired_events(
        redis_client=redis_client,
        key_prefix="e2e-cons-fresh:",
        max_age_days=90,
        archive_store=archive_store,
    )

    assert archived == 0, f"Fresh event should not be archived, got {archived}"
    assert deleted == 0, f"Fresh event should not be deleted, got {deleted}"
    assert await redis_client.exists(redis_key), "Fresh event should still exist"

    # Cleanup
    await redis_client.delete(redis_key)


# ---------------------------------------------------------------------------
# Test 9: Cold event pruning in Neo4j
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cold_event_pruning_via_api(
    http_client: httpx.AsyncClient,
    neo4j_driver,
):
    """Create a COLD-tier Event node with low importance and access count,
    prune via API with dry_run=false, verify node deleted.

    Uses 15-day age to land in COLD tier (warm_hours=168 < 360h < cold_hours=720).
    """
    event_id = f"{PREFIX}cold-{uuid.uuid4().hex[:8]}"
    old_timestamp = (datetime.now(UTC) - timedelta(days=15)).isoformat()

    # Create an old Event node in Neo4j with low importance and access_count
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            "CREATE (e:Event {"
            "  event_id: $event_id,"
            "  session_id: $session_id,"
            "  event_type: 'test.cold',"
            "  occurred_at: $occurred_at,"
            "  importance_score: 1,"
            "  access_count: 0"
            "})",
            {
                "event_id": event_id,
                "session_id": f"{PREFIX}cold-session",
                "occurred_at": old_timestamp,
            },
        )

    # Verify the node exists
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            "MATCH (e:Event {event_id: $event_id}) RETURN e",
            {"event_id": event_id},
        )
        records = [r async for r in result]
        assert len(records) == 1, "Cold event should exist before pruning"

    # Prune cold tier (not dry run)
    resp = await http_client.post(
        "/v1/admin/prune",
        json={"tier": "cold", "dry_run": False},
    )
    assert resp.status_code == 200, f"Prune failed: {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["dry_run"] is False

    # Verify the cold event was deleted
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            "MATCH (e:Event {event_id: $event_id}) RETURN e",
            {"event_id": event_id},
        )
        records = [r async for r in result]
        assert len(records) == 0, (
            f"Cold event {event_id} should have been pruned but still exists"
        )


@pytest.mark.asyncio
async def test_important_event_not_pruned(
    http_client: httpx.AsyncClient,
    neo4j_driver,
):
    """Event with high importance should survive cold pruning.

    Uses 15-day age to land in COLD tier (warm_hours=168 < 360h < cold_hours=720).
    Events in ARCHIVE tier (>30d) are unconditionally pruned, so we must stay
    in COLD tier to test importance-based retention.
    """
    event_id = f"{PREFIX}important-{uuid.uuid4().hex[:8]}"
    old_timestamp = (datetime.now(UTC) - timedelta(days=15)).isoformat()

    # Create an Event in COLD tier with HIGH importance + access count
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            "CREATE (e:Event {"
            "  event_id: $event_id,"
            "  session_id: $session_id,"
            "  event_type: 'test.important',"
            "  occurred_at: $occurred_at,"
            "  importance_score: 9,"
            "  access_count: 50"
            "})",
            {
                "event_id": event_id,
                "session_id": f"{PREFIX}important-session",
                "occurred_at": old_timestamp,
            },
        )

    # Prune cold tier
    resp = await http_client.post(
        "/v1/admin/prune",
        json={"tier": "cold", "dry_run": False},
    )
    assert resp.status_code == 200

    # Important event should still exist (high importance + access count)
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            "MATCH (e:Event {event_id: $event_id}) RETURN e",
            {"event_id": event_id},
        )
        records = [r async for r in result]
        assert len(records) == 1, (
            f"Important event {event_id} should NOT have been pruned"
        )


# ---------------------------------------------------------------------------
# Test 10: Reconsolidate with session data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconsolidate_with_events(
    http_client: httpx.AsyncClient,
    neo4j_driver,
):
    """Ingest events into a session, trigger reconsolidate for that session,
    verify summaries are created."""
    session_id = f"{PREFIX}recon-{uuid.uuid4().hex[:8]}"

    # Create enough events in Neo4j to trigger reconsolidation
    # (threshold is usually 10 in default settings)
    event_ids = []
    async with neo4j_driver.session(database=NEO4J_DATABASE) as neo_session:
        for i in range(15):
            eid = f"{PREFIX}recon-evt-{i}-{uuid.uuid4().hex[:6]}"
            event_ids.append(eid)
            ts = (datetime.now(UTC) - timedelta(minutes=15 - i)).isoformat()
            await neo_session.run(
                "CREATE (e:Event {"
                "  event_id: $event_id,"
                "  session_id: $session_id,"
                "  event_type: $event_type,"
                "  occurred_at: $occurred_at,"
                "  tool_name: $tool_name,"
                "  status: 'completed'"
                "})",
                {
                    "event_id": eid,
                    "session_id": session_id,
                    "event_type": "tool.execute",
                    "occurred_at": ts,
                    "tool_name": f"tool-{i}",
                },
            )

    # Trigger reconsolidation for this specific session
    resp = await http_client.post(
        "/v1/admin/reconsolidate",
        json={"session_id": session_id},
    )
    assert resp.status_code == 200, f"Reconsolidate failed: {resp.text}"

    body = resp.json()
    assert body["sessions_processed"] == 1, (
        f"Expected 1 session processed, got {body['sessions_processed']}"
    )
    assert body["events_processed"] == 15, (
        f"Expected 15 events processed, got {body['events_processed']}"
    )
    assert body["summaries_created"] >= 1, (
        f"Expected at least 1 summary created, got {body['summaries_created']}"
    )

    # Verify Summary nodes exist in Neo4j with SUMMARIZES edges
    async with neo4j_driver.session(database=NEO4J_DATABASE) as neo_session:
        result = await neo_session.run(
            "MATCH (s:Summary {scope_id: $sid})-[:SUMMARIZES]->(e:Event) "
            "RETURN s.summary_id AS summary_id, count(e) AS event_count",
            {"sid": session_id},
        )
        records = [r async for r in result]
        assert len(records) >= 1, "At least one summary should exist with SUMMARIZES edges"
        total_summarized = sum(r["event_count"] for r in records)
        assert total_summarized > 0, "Summary should cover at least some events"

    # Cleanup summaries
    async with neo4j_driver.session(database=NEO4J_DATABASE) as neo_session:
        await neo_session.run(
            "MATCH (s:Summary {scope_id: $sid}) DETACH DELETE s",
            {"sid": session_id},
        )


# ---------------------------------------------------------------------------
# Test 11: Invalid prune tier rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prune_invalid_tier(http_client: httpx.AsyncClient):
    """POST /v1/admin/prune with invalid tier returns 422."""
    resp = await http_client.post(
        "/v1/admin/prune",
        json={"tier": "invalid", "dry_run": True},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for invalid tier, got {resp.status_code}"
    )
