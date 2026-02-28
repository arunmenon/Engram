"""E2E tests for Resilience — Consumer Groups, DLQ, Pipeline Regression.

Exercises the running stack to verify:
1. Consumer group health (existence, consumers, lag, PEL)
2. Dead-letter queue structure and metrics
3. Full pipeline regression (ingest -> project -> retrieve)
4. Consumer settings defaults

Prerequisites:
    - docker-compose up (redis, neo4j, api, workers)

Usage:
    python -m pytest tests/e2e/test_e2e_resilience.py -v
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
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

POLL_INTERVAL = 0.5
POLL_TIMEOUT = 15.0

GLOBAL_STREAM = "events:__global__"
PROJECTION_GROUP = "graph-projection"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    session_id: str,
    event_type: str = "tool.execute",
    agent_id: str = "e2e-resilience-agent",
    importance_hint: int = 5,
    occurred_at: str | None = None,
    parent_event_id: str | None = None,
) -> dict[str, Any]:
    """Build an event dict with test defaults."""
    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": occurred_at or datetime.now(tz=UTC).isoformat(),
        "session_id": session_id,
        "agent_id": agent_id,
        "trace_id": f"trace-{uuid.uuid4().hex[:8]}",
        "payload_ref": f"ref://{uuid.uuid4().hex[:8]}",
        "importance_hint": importance_hint,
    }
    if parent_event_id is not None:
        event["parent_event_id"] = parent_event_id
    return event


async def poll_neo4j_event(
    driver: Any,
    event_id: str,
    timeout: float = POLL_TIMEOUT,
) -> dict[str, Any] | None:
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
    driver: Any,
    source_id: str,
    target_id: str,
    timeout: float = POLL_TIMEOUT,
) -> dict[str, Any] | None:
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


async def cleanup_events(
    redis_client: Redis,
    neo4j_driver: Any,
    event_ids: list[str],
    session_id: str,
) -> None:
    """Best-effort cleanup of test data from Redis and Neo4j."""
    for event_id in event_ids:
        with contextlib.suppress(Exception):
            await redis_client.execute_command("JSON.DEL", f"evt:{event_id}")
        with contextlib.suppress(Exception):
            await redis_client.zrem("dedup:events", event_id)
        with contextlib.suppress(Exception):
            async with neo4j_driver.session(database=NEO4J_DB) as session:
                await session.run(
                    "MATCH (e:Event {event_id: $eid}) DETACH DELETE e",
                    eid=event_id,
                )
    # Clean up session stream
    with contextlib.suppress(Exception):
        await redis_client.delete(f"events:session:{session_id}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def redis_client():
    client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=False)
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


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        yield client


# ---------------------------------------------------------------------------
# Consumer Group Health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consumer_groups_exist(redis_client: Redis):
    """Consumer groups exist on the global stream; graph-projection is present."""
    groups = await redis_client.xinfo_groups(GLOBAL_STREAM)
    assert len(groups) >= 1, "Expected at least 1 consumer group on global stream"

    group_names = [
        g[b"name"].decode() if isinstance(g[b"name"], bytes) else g[b"name"] for g in groups
    ]
    assert (
        PROJECTION_GROUP in group_names
    ), f"Expected '{PROJECTION_GROUP}' group, found: {group_names}"


@pytest.mark.asyncio
async def test_consumer_group_has_consumers(redis_client: Redis):
    """The graph-projection group has at least 1 consumer registered."""
    consumers = await redis_client.xinfo_consumers(GLOBAL_STREAM, PROJECTION_GROUP)
    assert (
        len(consumers) >= 1
    ), f"Expected at least 1 consumer in '{PROJECTION_GROUP}', got {len(consumers)}"


@pytest.mark.asyncio
async def test_consumer_lag_reasonable(
    redis_client: Redis,
    neo4j_driver: Any,
    http_client: httpx.AsyncClient,
):
    """After ingesting and projecting an event, consumer lag is < 100."""
    session_id = f"e2e-resilience-lag-{uuid.uuid4().hex[:8]}"
    event = make_event(session_id=session_id)
    event_id = event["event_id"]

    try:
        resp = await http_client.post(f"{API_URL}/v1/events", json=event)
        assert resp.status_code == 201

        # Wait for projection
        node = await poll_neo4j_event(neo4j_driver, event_id)
        assert node is not None, f"Event {event_id} not projected within {POLL_TIMEOUT}s"

        # Check lag after projection
        groups = await redis_client.xinfo_groups(GLOBAL_STREAM)
        projection_group = None
        for group in groups:
            name = group[b"name"]
            if isinstance(name, bytes):
                name = name.decode()
            if name == PROJECTION_GROUP:
                projection_group = group
                break

        assert projection_group is not None, f"'{PROJECTION_GROUP}' group not found"

        lag = projection_group.get(b"lag")
        if lag is not None:
            lag_value = int(lag)
            assert (
                lag_value < 100
            ), f"Consumer lag for '{PROJECTION_GROUP}' is {lag_value}, expected < 100"
    finally:
        await cleanup_events(redis_client, neo4j_driver, [event_id], session_id)


@pytest.mark.asyncio
async def test_pel_mostly_empty(
    redis_client: Redis,
    neo4j_driver: Any,
    http_client: httpx.AsyncClient,
):
    """After projection completes, PEL for graph-projection is empty or very small."""
    session_id = f"e2e-resilience-pel-{uuid.uuid4().hex[:8]}"
    event = make_event(session_id=session_id)
    event_id = event["event_id"]

    try:
        resp = await http_client.post(f"{API_URL}/v1/events", json=event)
        assert resp.status_code == 201

        # Wait for projection to complete
        node = await poll_neo4j_event(neo4j_driver, event_id)
        assert node is not None, f"Event {event_id} not projected within {POLL_TIMEOUT}s"

        # Small delay to let ACK propagate
        await asyncio.sleep(0.5)

        # Check pending entries for the projection group
        groups = await redis_client.xinfo_groups(GLOBAL_STREAM)
        projection_group = None
        for group in groups:
            name = group[b"name"]
            if isinstance(name, bytes):
                name = name.decode()
            if name == PROJECTION_GROUP:
                projection_group = group
                break

        assert projection_group is not None
        pending = int(projection_group.get(b"pending", 0))
        assert pending < 5, f"PEL for '{PROJECTION_GROUP}' has {pending} entries, expected < 5"
    finally:
        await cleanup_events(redis_client, neo4j_driver, [event_id], session_id)


# ---------------------------------------------------------------------------
# DLQ Structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dlq_stream_naming(redis_client: Redis):
    """If a DLQ stream exists, its entries contain expected metadata fields."""
    dlq_key = f"{GLOBAL_STREAM}:dlq"

    try:
        await redis_client.xinfo_stream(dlq_key)
    except Exception:
        # DLQ stream doesn't exist — no messages have failed. Pass gracefully.
        pytest.skip("DLQ stream does not exist (no dead-lettered messages)")
        return

    # DLQ stream exists — verify entries have required metadata fields
    entries = await redis_client.xrange(dlq_key, count=10)
    assert len(entries) > 0, "DLQ stream exists but has no entries"

    expected_fields = {
        b"original_stream",
        b"original_entry_id",
        b"group",
        b"consumer",
        b"delivery_count",
    }

    _entry_id, fields = entries[0]
    field_keys = set(fields.keys())
    missing = expected_fields - field_keys
    assert not missing, f"DLQ entry missing expected metadata fields: {missing}"


@pytest.mark.asyncio
async def test_dlq_metric_defined(http_client: httpx.AsyncClient):
    """The dead-letter metric name appears in /metrics output."""
    resp = await http_client.get(f"{API_URL}/metrics")
    assert resp.status_code == 200, f"GET /metrics returned {resp.status_code}"

    text = resp.text
    assert (
        "engram_consumer_messages_dead_lettered_total" in text
    ), "Expected 'engram_consumer_messages_dead_lettered_total' in /metrics output"


# ---------------------------------------------------------------------------
# Pipeline Regression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ingest_and_project_pipeline(
    http_client: httpx.AsyncClient,
    redis_client: Redis,
    neo4j_driver: Any,
):
    """Full pipeline: POST /v1/events -> poll Neo4j -> verify event properties."""
    session_id = f"e2e-resilience-pipe-{uuid.uuid4().hex[:8]}"
    event = make_event(session_id=session_id, event_type="agent.invoke")
    event_id = event["event_id"]

    try:
        resp = await http_client.post(f"{API_URL}/v1/events", json=event)
        assert resp.status_code == 201

        node = await poll_neo4j_event(neo4j_driver, event_id)
        assert node is not None, f"Event {event_id} not projected within {POLL_TIMEOUT}s"

        assert node["event_id"] == event_id
        assert node["session_id"] == session_id
        assert node["event_type"] == "agent.invoke"
    finally:
        await cleanup_events(redis_client, neo4j_driver, [event_id], session_id)


@pytest.mark.asyncio
async def test_batch_ingest_and_project(
    http_client: httpx.AsyncClient,
    redis_client: Redis,
    neo4j_driver: Any,
):
    """POST /v1/events/batch with 3 events -> poll Neo4j -> verify all 3 appear."""
    session_id = f"e2e-resilience-batch-{uuid.uuid4().hex[:8]}"
    events = [make_event(session_id=session_id) for _ in range(3)]
    event_ids = [e["event_id"] for e in events]

    try:
        resp = await http_client.post(
            f"{API_URL}/v1/events/batch",
            json={"events": events},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["accepted"] == 3

        # Poll for all 3 events in Neo4j
        for event_id in event_ids:
            node = await poll_neo4j_event(neo4j_driver, event_id)
            assert node is not None, f"Event {event_id} not projected within {POLL_TIMEOUT}s"
            assert node["event_id"] == event_id
            assert node["session_id"] == session_id
    finally:
        await cleanup_events(redis_client, neo4j_driver, event_ids, session_id)


@pytest.mark.asyncio
async def test_follows_edge_created(
    http_client: httpx.AsyncClient,
    redis_client: Redis,
    neo4j_driver: Any,
):
    """Ingest 2 events in same session with sequential timestamps -> verify FOLLOWS edge."""
    session_id = f"e2e-resilience-follows-{uuid.uuid4().hex[:8]}"
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
    event_ids = [event1["event_id"], event2["event_id"]]

    try:
        # Ingest sequentially to preserve ordering
        for event in [event1, event2]:
            resp = await http_client.post(f"{API_URL}/v1/events", json=event)
            assert resp.status_code == 201

        # Wait for both nodes to be projected
        for eid in event_ids:
            node = await poll_neo4j_event(neo4j_driver, eid)
            assert node is not None, f"Event {eid} not projected within {POLL_TIMEOUT}s"

        # Verify FOLLOWS edge: event2 -> event1
        follows = await poll_neo4j_follows(neo4j_driver, event2["event_id"], event1["event_id"])
        assert follows is not None, "FOLLOWS edge from event2 to event1 not found"
    finally:
        await cleanup_events(redis_client, neo4j_driver, event_ids, session_id)


@pytest.mark.asyncio
async def test_context_retrieval_after_pipeline(
    http_client: httpx.AsyncClient,
    redis_client: Redis,
    neo4j_driver: Any,
):
    """Ingest events -> poll -> GET /v1/context/{session_id} -> verify Atlas format."""
    session_id = f"e2e-resilience-ctx-{uuid.uuid4().hex[:8]}"
    base_time = datetime.now(tz=UTC)

    events = [
        make_event(
            session_id=session_id,
            occurred_at=(base_time + timedelta(seconds=i)).isoformat(),
        )
        for i in range(3)
    ]
    event_ids = [e["event_id"] for e in events]

    try:
        for event in events:
            resp = await http_client.post(f"{API_URL}/v1/events", json=event)
            assert resp.status_code == 201

        # Wait for all events to be projected
        for eid in event_ids:
            node = await poll_neo4j_event(neo4j_driver, eid)
            assert node is not None, f"Event {eid} not projected within {POLL_TIMEOUT}s"

        # Poll context endpoint until we see at least 3 nodes
        deadline = asyncio.get_event_loop().time() + POLL_TIMEOUT
        context_data = None
        while asyncio.get_event_loop().time() < deadline:
            resp = await http_client.get(f"{API_URL}/v1/context/{session_id}")
            if resp.status_code == 200:
                data = resp.json()
                if len(data.get("nodes", {})) >= 3:
                    context_data = data
                    break
            await asyncio.sleep(POLL_INTERVAL)

        assert (
            context_data is not None
        ), f"Context endpoint did not return >= 3 nodes within {POLL_TIMEOUT}s"

        # Verify Atlas format
        assert "nodes" in context_data
        assert "edges" in context_data
        assert "meta" in context_data

        # Verify our event IDs appear in the returned nodes
        node_ids_returned = set(context_data["nodes"].keys())
        for eid in event_ids:
            assert eid in node_ids_returned, f"Event {eid} missing from context response nodes"
    finally:
        await cleanup_events(redis_client, neo4j_driver, event_ids, session_id)


# ---------------------------------------------------------------------------
# Consumer Settings Validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consumer_settings_defaults():
    """ConsumerSettings has correct defaults: max_retries=5, claim_idle_ms=300000, etc."""
    from context_graph.settings import ConsumerSettings

    settings = ConsumerSettings()

    assert settings.max_retries == 5, f"Expected max_retries=5, got {settings.max_retries}"
    assert (
        settings.claim_idle_ms == 300_000
    ), f"Expected claim_idle_ms=300000, got {settings.claim_idle_ms}"
    assert (
        settings.claim_batch_size == 100
    ), f"Expected claim_batch_size=100, got {settings.claim_batch_size}"
    assert (
        settings.dlq_stream_suffix == ":dlq"
    ), f"Expected dlq_stream_suffix=':dlq', got {settings.dlq_stream_suffix!r}"
