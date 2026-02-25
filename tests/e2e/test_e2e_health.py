"""E2E tests for health endpoints and edge cases.

Covers:
1. Basic health check
2. Detailed health check
3. Invalid event rejection (missing fields, bad UUID, empty event_type)
4. Large batch handling (50 events)
5. Concurrent ingestion stress (30 parallel requests)
6. Non-existent entity 404
7. AtlasResponse schema validation
8. Query with empty text (422)

Prerequisites:
    - docker-compose up (redis, neo4j, api)
    - pip install -e ".[dev]"

Usage:
    python -m pytest tests/e2e/test_e2e_health.py -v
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import httpx
import pytest
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

PREFIX = "e2e-health"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    *,
    session_id: str | None = None,
    event_type: str = "tool.execute",
    agent_id: str = "agent-health-test",
    payload: dict | None = None,
) -> dict:
    """Create a valid event dict for ingestion."""
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(tz=UTC).isoformat(),
        "session_id": session_id or f"{PREFIX}-session-{uuid.uuid4().hex[:8]}",
        "agent_id": agent_id,
        "trace_id": str(uuid.uuid4()),
        "payload_ref": f"s3://test/{uuid.uuid4().hex}",
        **({"payload": payload} if payload else {}),
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        yield c


@pytest.fixture
async def redis_client():
    r = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    yield r
    await r.aclose()


@pytest.fixture
async def neo4j_driver():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    await driver.close()


@pytest.fixture(autouse=True)
async def cleanup(redis_client: Redis, neo4j_driver):
    """Clean up test data after each test."""
    yield

    # Redis cleanup: delete event JSON keys and stream entries with our prefix
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match=f"evt:{PREFIX}-*", count=200)
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break

    # Also scan for session stream keys
    cursor = 0
    while True:
        cursor, keys = await redis_client.scan(cursor, match=f"events:{PREFIX}-*", count=200)
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break

    # Neo4j cleanup
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            "MATCH (e:Event) WHERE e.session_id STARTS WITH $prefix DETACH DELETE e",
            {"prefix": PREFIX},
        )


# ---------------------------------------------------------------------------
# Test 1: Basic health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_basic_health_check(client: httpx.AsyncClient):
    """GET /v1/health returns 200 with status, redis, neo4j fields."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "status" in body, "Missing 'status' field"
    assert "redis" in body, "Missing 'redis' field"
    assert "neo4j" in body, "Missing 'neo4j' field"
    assert body["status"] == "healthy", f"Expected healthy, got {body['status']}"
    assert body["redis"] is True, "Redis should be connected"
    assert body["neo4j"] is True, "Neo4j should be connected"


# ---------------------------------------------------------------------------
# Test 2: Detailed health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detailed_health_check(client: httpx.AsyncClient):
    """GET /v1/admin/health/detailed returns 200 with extended info."""
    resp = await client.get("/v1/admin/health/detailed")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "status" in body
    assert body["status"] == "healthy"

    # Detailed health should have nested redis/neo4j objects with more info
    assert "redis" in body
    assert isinstance(body["redis"], dict), "redis should be a dict with detailed info"
    assert "connected" in body["redis"]
    assert body["redis"]["connected"] is True
    assert "stream_length" in body["redis"]

    assert "neo4j" in body
    assert isinstance(body["neo4j"], dict), "neo4j should be a dict with detailed info"
    assert "connected" in body["neo4j"]
    assert body["neo4j"]["connected"] is True
    assert "nodes" in body["neo4j"]
    assert "edges" in body["neo4j"]

    assert "version" in body


# ---------------------------------------------------------------------------
# Test 3: Invalid event — missing required field (session_id)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_event_missing_session_id(client: httpx.AsyncClient):
    """POST /v1/events with missing session_id returns 422."""
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "tool.execute",
        "occurred_at": datetime.now(tz=UTC).isoformat(),
        # session_id intentionally omitted
        "agent_id": "agent-test",
        "trace_id": str(uuid.uuid4()),
        "payload_ref": "s3://test/missing-session",
    }
    resp = await client.post("/v1/events", json=event)
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 4: Invalid event — bad event_id (not a UUID)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_event_bad_uuid(client: httpx.AsyncClient):
    """POST /v1/events with event_id='not-a-uuid' returns 422."""
    event = {
        "event_id": "not-a-uuid",
        "event_type": "tool.execute",
        "occurred_at": datetime.now(tz=UTC).isoformat(),
        "session_id": f"{PREFIX}-bad-uuid-session",
        "agent_id": "agent-test",
        "trace_id": str(uuid.uuid4()),
        "payload_ref": "s3://test/bad-uuid",
    }
    resp = await client.post("/v1/events", json=event)
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "detail" in body, "422 response should have 'detail'"


# ---------------------------------------------------------------------------
# Test 5: Invalid event — empty event_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_event_empty_event_type(client: httpx.AsyncClient):
    """POST /v1/events with event_type='' returns 422."""
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "",
        "occurred_at": datetime.now(tz=UTC).isoformat(),
        "session_id": f"{PREFIX}-empty-type-session",
        "agent_id": "agent-test",
        "trace_id": str(uuid.uuid4()),
        "payload_ref": "s3://test/empty-type",
    }
    resp = await client.post("/v1/events", json=event)
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 6: Large batch handling (50 events)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_large_batch_handling(client: httpx.AsyncClient):
    """POST /v1/events/batch with 50 events succeeds, all accepted."""
    session_id = f"{PREFIX}-large-batch-{uuid.uuid4().hex[:8]}"
    events = [make_event(session_id=session_id) for _ in range(50)]

    resp = await client.post("/v1/events/batch", json={"events": events})
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["accepted"] == 50, f"Expected 50 accepted, got {body['accepted']}"
    assert body["rejected"] == 0, f"Expected 0 rejected, got {body['rejected']}"
    assert len(body["results"]) == 50, f"Expected 50 results, got {len(body['results'])}"
    assert len(body["errors"]) == 0, f"Expected 0 errors, got {len(body['errors'])}"

    # Verify each result has required fields
    for result in body["results"]:
        assert "event_id" in result
        assert "global_position" in result
        assert result["global_position"], "global_position should not be empty"


# ---------------------------------------------------------------------------
# Test 7: Concurrent ingestion stress (30 concurrent requests)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_ingestion_stress(client: httpx.AsyncClient):
    """Send 30 concurrent POST /v1/events, all succeed with unique global_positions."""
    session_id = f"{PREFIX}-concurrent-{uuid.uuid4().hex[:8]}"
    events = [make_event(session_id=session_id) for _ in range(30)]

    async def ingest_one(event: dict) -> httpx.Response:
        return await client.post("/v1/events", json=event)

    responses = await asyncio.gather(*[ingest_one(e) for e in events])

    # All should succeed with 201
    for i, resp in enumerate(responses):
        assert resp.status_code == 201, (
            f"Event {i} failed with {resp.status_code}: {resp.text}"
        )

    # Collect all global_positions and verify uniqueness
    positions = set()
    for resp in responses:
        body = resp.json()
        pos = body["global_position"]
        assert pos not in positions, f"Duplicate global_position: {pos}"
        positions.add(pos)

    assert len(positions) == 30, f"Expected 30 unique positions, got {len(positions)}"


# ---------------------------------------------------------------------------
# Test 8: Non-existent entity returns 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nonexistent_entity_404(client: httpx.AsyncClient):
    """GET /v1/entities/nonexistent-entity-id-e2e returns 404."""
    resp = await client.get("/v1/entities/nonexistent-entity-id-e2e")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 9: AtlasResponse schema validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atlas_response_schema(client: httpx.AsyncClient):
    """POST /v1/query/subgraph returns valid AtlasResponse with all required fields."""
    # First ingest a few events so the query has data to work with
    session_id = f"{PREFIX}-atlas-{uuid.uuid4().hex[:8]}"
    events = [
        make_event(session_id=session_id, event_type="agent.invoke"),
        make_event(session_id=session_id, event_type="tool.execute"),
        make_event(session_id=session_id, event_type="tool.result"),
    ]

    batch_resp = await client.post("/v1/events/batch", json={"events": events})
    assert batch_resp.status_code == 201, f"Batch ingest failed: {batch_resp.text}"

    # Wait briefly for projection
    await asyncio.sleep(1.0)

    # Query subgraph
    query_body = {
        "query": "what happened in this session",
        "session_id": session_id,
        "agent_id": "agent-health-test",
    }
    resp = await client.post("/v1/query/subgraph", json=query_body)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()

    # Validate top-level AtlasResponse fields
    assert "nodes" in body, "Missing 'nodes' field"
    assert isinstance(body["nodes"], dict), "'nodes' should be a dict"

    assert "edges" in body, "Missing 'edges' field"
    assert isinstance(body["edges"], list), "'edges' should be a list"

    assert "pagination" in body, "Missing 'pagination' field"
    assert isinstance(body["pagination"], dict), "'pagination' should be a dict"
    assert "cursor" in body["pagination"]
    assert "has_more" in body["pagination"]

    assert "meta" in body, "Missing 'meta' field"
    assert isinstance(body["meta"], dict), "'meta' should be a dict"

    # Validate meta fields
    meta = body["meta"]
    assert "query_ms" in meta, "Missing 'query_ms' in meta"
    assert "nodes_returned" in meta, "Missing 'nodes_returned' in meta"
    assert "truncated" in meta, "Missing 'truncated' in meta"
    assert "inferred_intents" in meta, "Missing 'inferred_intents' in meta"
    assert "seed_nodes" in meta, "Missing 'seed_nodes' in meta"
    assert "scoring_weights" in meta, "Missing 'scoring_weights' in meta"


# ---------------------------------------------------------------------------
# Test 10: Query with empty text returns 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_empty_text(client: httpx.AsyncClient):
    """POST /v1/query/subgraph with query='' should return 422 (min_length=1)."""
    query_body = {
        "query": "",
        "session_id": f"{PREFIX}-empty-query",
        "agent_id": "agent-test",
    }
    resp = await client.post("/v1/query/subgraph", json=query_body)
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
