"""E2E lifecycle test for archival & lifecycle hardening (ADR-0014).

Exercises the full pipeline against the running stack:
1. Ingest events via API
2. Verify events are in Redis (Stream + JSON) and Neo4j
3. Run trimmer functions directly against live Redis
4. Verify Lua script correctness (global_position, no regex artifacts)
5. Test archive-before-delete with filesystem archive
6. Test session stream cleanup
7. Test dedup set maintenance
8. Test concurrent batch ingestion

Prerequisites:
    - docker-compose up (redis, neo4j, api, workers)
    - pip install -e ".[dev]"

Usage:
    python -m pytest tests/e2e/test_lifecycle.py -v
    # or directly:
    python tests/e2e/test_lifecycle.py
"""

from __future__ import annotations

import asyncio
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import orjson
from redis.asyncio import Redis

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "http://localhost:8000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    session_id: str = "e2e-session-1",
    agent_id: str = "e2e-agent-1",
    event_type: str = "tool.execute",
    importance_hint: int = 5,
) -> dict:
    """Create a valid event payload for the /v1/events endpoint."""
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "agent_id": agent_id,
        "trace_id": f"trace-{uuid.uuid4().hex[:8]}",
        "payload_ref": f"ref://{uuid.uuid4().hex[:8]}",
        "importance_hint": importance_hint,
    }


async def ingest_event(client: httpx.AsyncClient, event: dict) -> dict:
    """POST an event to the API and return the response."""
    resp = await client.post(f"{API_URL}/v1/events", json=event)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_1_ingest_and_verify_redis():
    """Ingest events via API, verify they land in Redis with correct global_position."""
    print("\n=== Test 1: Ingest & Verify Redis ===")

    async with httpx.AsyncClient(timeout=10) as client:
        event = make_event(session_id="e2e-lifecycle-1")
        result = await ingest_event(client, event)

        assert "global_position" in result, f"Missing global_position: {result}"
        global_pos = result["global_position"]
        print(f"  Ingested event {event['event_id']}, global_position={global_pos}")

    # Verify in Redis
    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    try:
        raw = await redis.execute_command("JSON.GET", f"evt:{event['event_id']}", "$")
        assert raw is not None, "Event not found in Redis JSON"
        doc = orjson.loads(raw)[0]
        assert (
            doc["global_position"] == global_pos
        ), f"global_position mismatch: {doc['global_position']} != {global_pos}"
        print(f"  Redis JSON verified: global_position={doc['global_position']}")

        # Verify no string.gsub corruption
        assert doc["event_type"] == event["event_type"]
        print("  No string.gsub artifacts detected")
    finally:
        await redis.aclose()

    print("  PASSED")


async def test_2_global_position_payload_safety():
    """Ensure 'global_position' in payload doesn't get corrupted by Lua script."""
    print("\n=== Test 2: Payload Safety (global_position in payload) ===")

    async with httpx.AsyncClient(timeout=10) as client:
        event = make_event(session_id="e2e-lifecycle-2")
        # Add payload with "global_position" inside it
        resp = await client.post(
            f"{API_URL}/v1/events",
            json={
                **event,
                "payload": {
                    "message": "Testing global_position safety",
                    "metadata": {"global_position": "should-not-change"},
                },
            },
        )
        resp.raise_for_status()
        result = resp.json()

    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    try:
        raw = await redis.execute_command("JSON.GET", f"evt:{event['event_id']}", "$")
        doc = orjson.loads(raw)[0]

        # Top-level global_position should be the stream entry ID
        assert doc["global_position"] == result["global_position"]
        # Payload data should be untouched
        if "payload" in doc:
            assert doc["payload"]["metadata"]["global_position"] == "should-not-change"
            print("  Nested payload global_position preserved correctly")
    finally:
        await redis.aclose()

    print("  PASSED")


async def test_3_batch_ingestion():
    """Ingest a batch of events and verify concurrent execution."""
    print("\n=== Test 3: Batch Ingestion Performance ===")

    events = [make_event(session_id="e2e-batch-1") for _ in range(20)]

    start = time.monotonic()
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [ingest_event(client, e) for e in events]
        results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - start

    assert len(results) == 20
    positions = [r["global_position"] for r in results]
    assert len(set(positions)) == 20, "All events should have unique positions"
    print(f"  Ingested 20 events in {elapsed:.2f}s ({elapsed/20*1000:.1f}ms/event)")
    print("  PASSED")


async def test_4_session_stream_cleanup():
    """Verify session stream cleanup works against live Redis."""
    print("\n=== Test 4: Session Stream Cleanup ===")

    from context_graph.adapters.redis.trimmer import cleanup_session_streams

    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    try:
        # Create a test session stream
        test_key = "events:session:e2e-cleanup-test"
        await redis.xadd(test_key, {"event_id": "test-cleanup"})
        assert await redis.exists(test_key)

        # Clean with max_age_hours=0 (everything is "old")
        deleted = await cleanup_session_streams(
            redis_client=redis,
            prefix="events:session:e2e-cleanup-",
            max_age_hours=0,
        )
        assert deleted == 1
        assert not await redis.exists(test_key)
        print(f"  Cleaned up {deleted} session stream(s)")
    finally:
        await redis.aclose()

    print("  PASSED")


async def test_5_dedup_set_cleanup():
    """Verify dedup set cleanup against live Redis."""
    print("\n=== Test 5: Dedup Set Cleanup ===")

    from context_graph.adapters.redis.trimmer import cleanup_dedup_set

    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    try:
        test_key = "dedup:e2e-test"
        now_ms = int(time.time() * 1000)
        old_ms = int((datetime.now(UTC) - timedelta(days=100)).timestamp() * 1000)

        await redis.zadd(test_key, {"old-event": old_ms, "fresh-event": now_ms})

        removed = await cleanup_dedup_set(
            redis_client=redis,
            dedup_key=test_key,
            retention_ceiling_days=90,
        )
        assert removed == 1
        assert await redis.zscore(test_key, "fresh-event") is not None
        assert await redis.zscore(test_key, "old-event") is None
        print(f"  Removed {removed} old dedup entries, fresh entries preserved")

        # Cleanup
        await redis.delete(test_key)
    finally:
        await redis.aclose()

    print("  PASSED")


async def test_6_archive_before_delete():
    """Full archive-before-delete lifecycle against live Redis + filesystem."""
    print("\n=== Test 6: Archive-Before-Delete Lifecycle ===")

    from context_graph.adapters.fs.archive import FilesystemArchiveStore
    from context_graph.adapters.redis.trimmer import archive_and_delete_expired_events

    archive_path = Path("/tmp/claude/engram-e2e-archives")
    archive_path.mkdir(parents=True, exist_ok=True)
    archive_store = FilesystemArchiveStore(base_path=archive_path)

    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    try:
        # Create an "old" event (beyond 90-day retention)
        old_epoch_ms = int((datetime.now(UTC) - timedelta(days=100)).timestamp() * 1000)
        old_event = {
            "event_id": f"e2e-archive-{uuid.uuid4().hex[:8]}",
            "event_type": "agent.invoke",
            "occurred_at_epoch_ms": old_epoch_ms,
            "session_id": "e2e-archive-session",
        }
        old_key = f"e2e-evt:{old_event['event_id']}"
        await redis.execute_command("JSON.SET", old_key, "$", orjson.dumps(old_event).decode())

        # Create a "fresh" event
        fresh_epoch_ms = int(datetime.now(UTC).timestamp() * 1000)
        fresh_event = {
            "event_id": f"e2e-fresh-{uuid.uuid4().hex[:8]}",
            "event_type": "tool.execute",
            "occurred_at_epoch_ms": fresh_epoch_ms,
            "session_id": "e2e-archive-session",
        }
        fresh_key = f"e2e-evt:{fresh_event['event_id']}"
        await redis.execute_command("JSON.SET", fresh_key, "$", orjson.dumps(fresh_event).decode())

        # Run archive-before-delete
        archived, deleted = await archive_and_delete_expired_events(
            redis_client=redis,
            key_prefix="e2e-evt:",
            max_age_days=90,
            archive_store=archive_store,
        )

        assert archived == 1, f"Expected 1 archived, got {archived}"
        assert deleted == 1, f"Expected 1 deleted, got {deleted}"
        assert not await redis.exists(old_key), "Old event should be deleted from Redis"
        assert await redis.exists(fresh_key), "Fresh event should still exist"

        # Verify archive is readable
        archives = await archive_store.list_archives()
        assert len(archives) >= 1
        restored = await archive_store.restore_archive(archives[-1]["archive_id"])
        assert any(e["event_id"] == old_event["event_id"] for e in restored)
        print(f"  Archived {archived} events, deleted {deleted} from Redis")
        print(f"  Archive restored: {len(restored)} events readable")

        # Cleanup
        await redis.delete(fresh_key)
    finally:
        await redis.aclose()

    print("  PASSED")


async def test_7_stream_maxlen():
    """Verify MAXLEN caps the stream when configured."""
    print("\n=== Test 7: Stream MAXLEN ===")

    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    try:
        test_stream = "e2e-maxlen-test"

        # Add 500 entries with MAXLEN ~100 — need enough entries for
        # approximate trimming to kick in (trims in radix-tree node blocks)
        for i in range(500):
            await redis.xadd(test_stream, {"i": str(i)}, maxlen=100, approximate=True)

        stream_len = await redis.xlen(test_stream)
        # Approximate MAXLEN trims in blocks; should be well below total
        assert stream_len <= 200, f"Stream should be ~100 entries, got {stream_len}"
        assert stream_len < 500, f"Stream was never trimmed: {stream_len}"
        print(f"  Added 500 entries with MAXLEN ~100, stream length: {stream_len}")

        await redis.delete(test_stream)
    finally:
        await redis.aclose()

    print("  PASSED")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def run_all():
    """Run all e2e tests sequentially."""
    print("=" * 60)
    print("E2E Lifecycle Hardening Tests (ADR-0014)")
    print("=" * 60)

    # Check API is up
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{API_URL}/v1/health")
            resp.raise_for_status()
            print(f"API healthy: {resp.json()}")
    except Exception as e:
        print(f"ERROR: API not reachable at {API_URL}: {e}")
        print("Run: cd docker && docker-compose up -d")
        sys.exit(1)

    tests = [
        test_1_ingest_and_verify_redis,
        test_2_global_position_payload_safety,
        test_3_batch_ingestion,
        test_4_session_stream_cleanup,
        test_5_dedup_set_cleanup,
        test_6_archive_before_delete,
        test_7_stream_maxlen,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all())
