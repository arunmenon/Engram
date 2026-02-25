"""E2E tests for Event Ingestion & Projection.

Exercises the full ingest pipeline against the running stack:
1. Single event ingestion via POST /v1/events
2. Redis JSON storage verification
3. Redis stream entry verification
4. Dedup idempotency
5. Batch ingestion via POST /v1/events/batch
6. Projection to Neo4j (EventNode)
7. FOLLOWS edge creation between session events
8. Session stream population
9. Importance hint preservation
10. Validation rejection on bad payloads

Prerequisites:
    - docker-compose up (redis, neo4j, api, workers)

Usage:
    python -m pytest tests/e2e/test_e2e_ingestion.py -v
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import orjson
import pytest
from neo4j import AsyncGraphDatabase
from redis.asyncio import Redis

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "http://127.0.0.1:8000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "engram-dev-password"
NEO4J_DB = "neo4j"

POLL_INTERVAL = 0.5  # seconds between poll attempts
POLL_TIMEOUT = 15.0  # max seconds to wait for projection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    event_id: str | None = None,
    event_type: str = "tool.execute",
    session_id: str = "e2e-ingest-session",
    agent_id: str = "e2e-ingest-agent",
    trace_id: str = "e2e-ingest-trace",
    payload_ref: str = "ref://test",
    parent_event_id: str | None = None,
    importance_hint: int | None = None,
    tool_name: str | None = None,
    occurred_at: str | None = None,
) -> dict:
    """Build an event dict with test defaults."""
    event = {
        "event_id": event_id or str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": occurred_at or datetime.now(tz=UTC).isoformat(),
        "session_id": session_id,
        "agent_id": agent_id,
        "trace_id": trace_id,
        "payload_ref": payload_ref,
    }
    if parent_event_id is not None:
        event["parent_event_id"] = parent_event_id
    if importance_hint is not None:
        event["importance_hint"] = importance_hint
    if tool_name is not None:
        event["tool_name"] = tool_name
    return event


async def poll_neo4j_event(driver, event_id: str, timeout: float = POLL_TIMEOUT) -> dict | None:
    """Poll Neo4j until the Event node appears or timeout."""
    elapsed = 0.0
    while elapsed < timeout:
        async with driver.session(database=NEO4J_DB) as session:
            result = await session.run(
                "MATCH (e:Event {event_id: $eid}) RETURN e",
                eid=event_id,
            )
            record = await result.single()
            if record is not None:
                return dict(record["e"])
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    return None


async def poll_neo4j_follows(
    driver, source_id: str, target_id: str, timeout: float = POLL_TIMEOUT
) -> dict | None:
    """Poll Neo4j until a FOLLOWS edge appears between two events."""
    elapsed = 0.0
    while elapsed < timeout:
        async with driver.session(database=NEO4J_DB) as session:
            result = await session.run(
                """
                MATCH (a:Event {event_id: $src})-[r:FOLLOWS]->(b:Event {event_id: $tgt})
                RETURN r
                """,
                src=source_id,
                tgt=target_id,
            )
            record = await result.single()
            if record is not None:
                return dict(record["r"])
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    return None


async def cleanup_event(redis_client: Redis, neo4j_driver, event_id: str, session_id: str):
    """Best-effort cleanup of test data from Redis and Neo4j."""
    # Redis cleanup
    try:
        await redis_client.execute_command("JSON.DEL", f"evt:{event_id}")
    except Exception:
        pass
    try:
        await redis_client.zrem("dedup:events", event_id)
    except Exception:
        pass

    # Neo4j cleanup
    try:
        async with neo4j_driver.session(database=NEO4J_DB) as session:
            await session.run(
                "MATCH (e:Event {event_id: $eid}) DETACH DELETE e",
                eid=event_id,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0, trust_env=False) as client:
        yield client


@pytest.fixture
async def redis_client():
    client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=False)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
async def neo4j_driver():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        yield driver
    finally:
        await driver.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_event_ingest(http_client, redis_client, neo4j_driver):
    """POST /v1/events returns 201 with event_id and global_position."""
    event = make_event()
    event_id = event["event_id"]

    try:
        resp = await http_client.post("/v1/events", json=event)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        body = resp.json()
        assert body["event_id"] == event_id
        assert "global_position" in body
        assert body["global_position"] != ""
        # global_position should be a Redis stream ID like "1234567890123-0"
        assert "-" in body["global_position"]
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_redis_json_storage(http_client, redis_client, neo4j_driver):
    """After ingest, the event is stored at key evt:{event_id} in Redis JSON."""
    event = make_event()
    event_id = event["event_id"]

    try:
        resp = await http_client.post("/v1/events", json=event)
        assert resp.status_code == 201

        # Verify JSON.GET returns the document
        raw = await redis_client.execute_command("JSON.GET", f"evt:{event_id}", "$")
        assert raw is not None, f"Event {event_id} not found in Redis JSON"

        raw_str = raw.decode() if isinstance(raw, bytes) else raw
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) else parsed

        assert doc["event_id"] == event_id
        assert doc["event_type"] == event["event_type"]
        assert doc["session_id"] == event["session_id"]
        assert doc["agent_id"] == event["agent_id"]
        assert doc["trace_id"] == event["trace_id"]
        assert doc["payload_ref"] == event["payload_ref"]
        # Adapter adds occurred_at_epoch_ms
        assert "occurred_at_epoch_ms" in doc
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_redis_stream_entry(http_client, redis_client, neo4j_driver):
    """After ingest, the event appears in the events:__global__ stream."""
    event = make_event()
    event_id = event["event_id"]

    try:
        resp = await http_client.post("/v1/events", json=event)
        assert resp.status_code == 201

        global_position = resp.json()["global_position"]

        # XRANGE with exact position should return the entry
        entries = await redis_client.xrange("events:__global__", min=global_position, max=global_position)
        assert len(entries) >= 1, f"No entry at position {global_position}"

        # The stream entry should carry the event_id field
        _entry_id, fields = entries[0]
        # Redis returns bytes
        stored_event_id = fields.get(b"event_id", b"").decode()
        assert stored_event_id == event_id
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_dedup_idempotency(http_client, redis_client, neo4j_driver):
    """Posting the same event_id twice returns the same global_position (dedup)."""
    event = make_event()
    event_id = event["event_id"]

    try:
        resp1 = await http_client.post("/v1/events", json=event)
        assert resp1.status_code == 201
        pos1 = resp1.json()["global_position"]

        resp2 = await http_client.post("/v1/events", json=event)
        assert resp2.status_code == 201
        pos2 = resp2.json()["global_position"]

        assert pos1 == pos2, f"Dedup failed: got different positions {pos1} vs {pos2}"

        # Verify only one entry in the stream for this event_id
        # Check the dedup set has exactly one entry for this event
        score = await redis_client.zscore("dedup:events", event_id)
        assert score is not None, "Event not found in dedup set"
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_batch_ingest(http_client, redis_client, neo4j_driver):
    """POST /v1/events/batch with 10 events returns all accepted with unique positions."""
    session_id = f"e2e-ingest-batch-{uuid.uuid4().hex[:8]}"
    events = [
        make_event(session_id=session_id)
        for _ in range(10)
    ]
    event_ids = [e["event_id"] for e in events]

    try:
        resp = await http_client.post("/v1/events/batch", json={"events": events})
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        body = resp.json()
        assert body["accepted"] == 10
        assert body["rejected"] == 0
        assert len(body["results"]) == 10
        assert len(body["errors"]) == 0

        # All positions should be unique
        positions = [r["global_position"] for r in body["results"]]
        assert len(set(positions)) == 10, f"Expected 10 unique positions, got {len(set(positions))}"

        # All event_ids should match
        returned_ids = {r["event_id"] for r in body["results"]}
        assert returned_ids == set(event_ids)
    finally:
        for eid in event_ids:
            await cleanup_event(redis_client, neo4j_driver, eid, session_id)


@pytest.mark.asyncio
async def test_projection_to_neo4j(http_client, redis_client, neo4j_driver):
    """Ingest an event, then poll Neo4j to verify the EventNode appears."""
    event = make_event()
    event_id = event["event_id"]

    try:
        resp = await http_client.post("/v1/events", json=event)
        assert resp.status_code == 201

        # Poll Neo4j for the projected event node
        node = await poll_neo4j_event(neo4j_driver, event_id)
        assert node is not None, f"Event {event_id} not projected to Neo4j within {POLL_TIMEOUT}s"

        assert node["event_id"] == event_id
        assert node["event_type"] == event["event_type"]
        assert node["session_id"] == event["session_id"]
        assert node["agent_id"] == event["agent_id"]
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_follows_edge_creation(http_client, redis_client, neo4j_driver):
    """Ingest 3 events in the same session with parent chain, verify FOLLOWS edges."""
    session_id = f"e2e-ingest-follows-{uuid.uuid4().hex[:8]}"
    base_time = datetime.now(tz=UTC)

    event1 = make_event(
        session_id=session_id,
        occurred_at=(base_time + timedelta(seconds=1)).isoformat(),
    )
    event2 = make_event(
        session_id=session_id,
        parent_event_id=event1["event_id"],
        occurred_at=(base_time + timedelta(seconds=2)).isoformat(),
    )
    event3 = make_event(
        session_id=session_id,
        parent_event_id=event2["event_id"],
        occurred_at=(base_time + timedelta(seconds=3)).isoformat(),
    )

    event_ids = [event1["event_id"], event2["event_id"], event3["event_id"]]

    try:
        # Ingest sequentially to ensure ordering for the projection worker
        for event in [event1, event2, event3]:
            resp = await http_client.post("/v1/events", json=event)
            assert resp.status_code == 201

        # Wait for all three nodes to be projected
        for eid in event_ids:
            node = await poll_neo4j_event(neo4j_driver, eid)
            assert node is not None, f"Event {eid} not projected within {POLL_TIMEOUT}s"

        # Verify FOLLOWS edges: event2 -> event1, event3 -> event2
        follows_2_1 = await poll_neo4j_follows(neo4j_driver, event2["event_id"], event1["event_id"])
        assert follows_2_1 is not None, "FOLLOWS edge from event2 to event1 not found"

        follows_3_2 = await poll_neo4j_follows(neo4j_driver, event3["event_id"], event2["event_id"])
        assert follows_3_2 is not None, "FOLLOWS edge from event3 to event2 not found"

        # Also verify CAUSED_BY edges (parent_event_id chain)
        async with neo4j_driver.session(database=NEO4J_DB) as session:
            result = await session.run(
                """
                MATCH (a:Event {event_id: $src})-[r:CAUSED_BY]->(b:Event {event_id: $tgt})
                RETURN r
                """,
                src=event2["event_id"],
                tgt=event1["event_id"],
            )
            record = await result.single()
            assert record is not None, "CAUSED_BY edge from event2 to event1 not found"

            result2 = await session.run(
                """
                MATCH (a:Event {event_id: $src})-[r:CAUSED_BY]->(b:Event {event_id: $tgt})
                RETURN r
                """,
                src=event3["event_id"],
                tgt=event2["event_id"],
            )
            record2 = await result2.single()
            assert record2 is not None, "CAUSED_BY edge from event3 to event2 not found"
    finally:
        for eid in event_ids:
            await cleanup_event(redis_client, neo4j_driver, eid, session_id)


@pytest.mark.asyncio
async def test_session_stream_populated(http_client, redis_client, neo4j_driver):
    """Ingest events in a session, verify events:session:{session_id} stream exists."""
    session_id = f"e2e-ingest-stream-{uuid.uuid4().hex[:8]}"
    events = [
        make_event(session_id=session_id)
        for _ in range(3)
    ]
    event_ids = [e["event_id"] for e in events]

    try:
        for event in events:
            resp = await http_client.post("/v1/events", json=event)
            assert resp.status_code == 201

        # Verify the session stream exists and has entries
        stream_key = f"events:session:{session_id}"
        stream_len = await redis_client.xlen(stream_key)
        assert stream_len >= 3, f"Expected >= 3 entries in {stream_key}, got {stream_len}"

        # Verify the entries contain the correct event_ids
        entries = await redis_client.xrange(stream_key)
        stored_ids = {fields.get(b"event_id", b"").decode() for _, fields in entries}
        for eid in event_ids:
            assert eid in stored_ids, f"Event {eid} not found in session stream"
    finally:
        # Clean up session stream
        try:
            await redis_client.delete(f"events:session:{session_id}")
        except Exception:
            pass
        for eid in event_ids:
            await cleanup_event(redis_client, neo4j_driver, eid, session_id)


@pytest.mark.asyncio
async def test_importance_hint_preserved(http_client, redis_client, neo4j_driver):
    """Ingest with importance_hint=9, verify it is preserved on Neo4j node."""
    event = make_event(importance_hint=9)
    event_id = event["event_id"]

    try:
        resp = await http_client.post("/v1/events", json=event)
        assert resp.status_code == 201

        # Verify in Redis JSON
        raw = await redis_client.execute_command("JSON.GET", f"evt:{event_id}", "$")
        assert raw is not None
        raw_str = raw.decode() if isinstance(raw, bytes) else raw
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) else parsed
        assert doc["importance_hint"] == 9

        # Poll Neo4j - importance_hint is stored as importance_score on the node
        node = await poll_neo4j_event(neo4j_driver, event_id)
        assert node is not None, f"Event not projected to Neo4j within {POLL_TIMEOUT}s"
        assert node.get("importance_score") == 9, (
            f"Expected importance_score=9, got {node.get('importance_score')}"
        )
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_validation_rejection_missing_fields(http_client, redis_client, neo4j_driver):
    """POST event with missing required fields returns 422, event NOT stored."""
    bad_event_id = str(uuid.uuid4())
    bad_event = {
        "event_id": bad_event_id,
        "event_type": "tool.execute",
        # Missing: occurred_at, session_id, agent_id, trace_id, payload_ref
    }

    resp = await http_client.post("/v1/events", json=bad_event)
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    # Verify the event was NOT stored in Redis
    raw = await redis_client.execute_command("JSON.GET", f"evt:{bad_event_id}", "$")
    assert raw is None, "Invalid event should not be stored in Redis"


@pytest.mark.asyncio
async def test_validation_rejection_bad_event_type(http_client):
    """POST event with invalid event_type pattern returns 422."""
    event = make_event()
    event["event_type"] = "INVALID_TYPE"  # Must be dot-namespaced lowercase

    resp = await http_client.post("/v1/events", json=event)
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_batch_partial_rejection(http_client, redis_client, neo4j_driver):
    """Batch with mix of valid and invalid events: valid accepted, invalid rejected."""
    session_id = f"e2e-ingest-partial-{uuid.uuid4().hex[:8]}"

    good_event = make_event(session_id=session_id)
    bad_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "INVALID",
        # Missing required fields
    }

    try:
        resp = await http_client.post(
            "/v1/events/batch",
            json={"events": [good_event, bad_event]},
        )
        assert resp.status_code == 201

        body = resp.json()
        assert body["accepted"] == 1
        assert body["rejected"] == 1
        assert len(body["results"]) == 1
        assert len(body["errors"]) == 1
        assert body["results"][0]["event_id"] == good_event["event_id"]
    finally:
        await cleanup_event(redis_client, neo4j_driver, good_event["event_id"], session_id)


@pytest.mark.asyncio
async def test_event_with_tool_name(http_client, redis_client, neo4j_driver):
    """Ingest event with tool_name, verify it is stored and projected."""
    event = make_event(tool_name="web_search")
    event_id = event["event_id"]

    try:
        resp = await http_client.post("/v1/events", json=event)
        assert resp.status_code == 201

        # Verify in Redis JSON
        raw = await redis_client.execute_command("JSON.GET", f"evt:{event_id}", "$")
        assert raw is not None
        raw_str = raw.decode() if isinstance(raw, bytes) else raw
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) else parsed
        assert doc["tool_name"] == "web_search"

        # Verify in Neo4j
        node = await poll_neo4j_event(neo4j_driver, event_id)
        assert node is not None, "Event not projected to Neo4j"
        assert node.get("tool_name") == "web_search"
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_event_with_payload(http_client, redis_client, neo4j_driver):
    """Ingest event with payload dict, verify payload is stored in Redis JSON."""
    event = make_event()
    event["payload"] = {"user_message": "hello world", "tokens": 42}
    event_id = event["event_id"]

    try:
        resp = await http_client.post("/v1/events", json=event)
        assert resp.status_code == 201

        # Verify payload is stored in Redis JSON
        raw = await redis_client.execute_command("JSON.GET", f"evt:{event_id}", "$")
        assert raw is not None
        raw_str = raw.decode() if isinstance(raw, bytes) else raw
        parsed = orjson.loads(raw_str)
        doc = parsed[0] if isinstance(parsed, list) else parsed
        assert doc.get("payload") == {"user_message": "hello world", "tokens": 42}
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_global_position_format(http_client, redis_client, neo4j_driver):
    """Verify global_position follows Redis Stream ID format: {ms}-{seq}."""
    event = make_event()
    event_id = event["event_id"]

    try:
        resp = await http_client.post("/v1/events", json=event)
        assert resp.status_code == 201

        gp = resp.json()["global_position"]
        parts = gp.split("-")
        assert len(parts) == 2, f"global_position should have format 'ms-seq', got '{gp}'"
        # First part should be a valid millisecond timestamp
        ms = int(parts[0])
        assert ms > 0, f"Millisecond part should be positive, got {ms}"
        # Second part is sequence number
        seq = int(parts[1])
        assert seq >= 0, f"Sequence part should be non-negative, got {seq}"
    finally:
        await cleanup_event(redis_client, neo4j_driver, event_id, event["session_id"])


@pytest.mark.asyncio
async def test_batch_empty_list_rejected(http_client):
    """Batch with empty events list returns 422."""
    resp = await http_client.post("/v1/events/batch", json={"events": []})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_missing_events_key(http_client):
    """Batch without 'events' key returns 422."""
    resp = await http_client.post("/v1/events/batch", json={"data": []})
    assert resp.status_code == 422
