"""E2E tests for Tier 0 observability: Prometheus metrics, request timing, health.

Covers:
1.  /metrics endpoint returns 200
2.  /metrics endpoint content type is prometheus text format
3.  engram_http_requests_total present after hitting /v1/health
4.  engram_http_request_duration_seconds present in metrics
5.  engram_events_ingested_total increments after event ingest
6.  engram_events_batch_size recorded after batch ingest
7.  engram_consumer_messages_processed_total is defined
8.  engram_graph_query_duration_seconds present after context query
9.  All 8 ADR-0008 metric names present in /metrics
10. Route template used (not resolved path) for label cardinality
11. X-Request-Time-Ms header is numeric
12. Health check returns 200 with status "healthy"
13. Health response structure has required keys
14. Health redis and neo4j fields are booleans
15. X-Request-ID auto-generated when none sent
16. X-Request-ID is valid UUID4 when auto-generated
17. X-Request-ID echoed back when sent by client

Prerequisites:
    - docker-compose up (redis, neo4j, api)
    - pip install -e ".[dev]"

Usage:
    python -m pytest tests/e2e/test_e2e_observability.py -v
"""

from __future__ import annotations

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

PREFIX = "e2e-obs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    *,
    session_id: str | None = None,
    event_type: str = "tool.execute",
    agent_id: str = "agent-obs-test",
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


def metric_value(metrics_text: str, metric_name: str) -> float | None:
    """Extract a metric value from Prometheus text format."""
    for line in metrics_text.splitlines():
        if line.startswith(metric_name) and not line.startswith("#"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return float(parts[-1])
                except ValueError:
                    continue
    return None


def metric_exists(metrics_text: str, metric_name: str) -> bool:
    """Check if a metric name appears in Prometheus output (including # HELP or # TYPE lines)."""
    return metric_name in metrics_text


def metric_sum(metrics_text: str, metric_name: str) -> float:
    """Sum all sample values for a given metric name (across all label sets)."""
    total = 0.0
    for line in metrics_text.splitlines():
        if line.startswith(metric_name) and not line.startswith("#"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    total += float(parts[-1])
                except ValueError:
                    continue
    return total


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
# Test 1: /metrics endpoint returns 200
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200(client: httpx.AsyncClient):
    """GET /metrics returns 200."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 2: /metrics endpoint content type is prometheus text format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_endpoint_content_type(client: httpx.AsyncClient):
    """GET /metrics returns prometheus text format content type."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200

    content_type = resp.headers.get("content-type", "")
    valid_types = [
        "text/plain",
        "text/plain; version=0.0.4",
        "application/openmetrics-text",
    ]
    matches = any(content_type.startswith(vt) for vt in valid_types)
    assert matches, f"Expected prometheus text format content type, got: {content_type}"


# ---------------------------------------------------------------------------
# Test 3: engram_http_requests_total present after hitting /v1/health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_contains_http_requests_total(client: httpx.AsyncClient):
    """After hitting /v1/health, GET /metrics contains engram_http_requests_total."""
    # Generate at least one request
    await client.get("/v1/health")

    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert metric_exists(resp.text, "engram_http_requests_total"), (
        "engram_http_requests_total not found in /metrics output"
    )


# ---------------------------------------------------------------------------
# Test 4: engram_http_request_duration_seconds present in metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_contains_http_request_duration(client: httpx.AsyncClient):
    """GET /metrics contains engram_http_request_duration_seconds."""
    # Generate a request to ensure the histogram has observations
    await client.get("/v1/health")

    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert metric_exists(resp.text, "engram_http_request_duration_seconds"), (
        "engram_http_request_duration_seconds not found in /metrics output"
    )


# ---------------------------------------------------------------------------
# Test 5: engram_events_ingested_total increments after event ingest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_events_ingested_increments(client: httpx.AsyncClient):
    """Ingest an event, then check /metrics for engram_events_ingested_total > 0."""
    session_id = f"{PREFIX}-ingest-{uuid.uuid4().hex[:8]}"
    event = make_event(session_id=session_id)

    ingest_resp = await client.post("/v1/events", json=event)
    assert ingest_resp.status_code == 201, f"Ingest failed: {ingest_resp.text}"

    resp = await client.get("/metrics")
    assert resp.status_code == 200

    assert metric_exists(resp.text, "engram_events_ingested_total"), (
        "engram_events_ingested_total not found in /metrics"
    )
    total = metric_value(resp.text, "engram_events_ingested_total")
    assert total is not None and total > 0, (
        f"Expected engram_events_ingested_total > 0, got {total}"
    )


# ---------------------------------------------------------------------------
# Test 6: engram_events_batch_size recorded after batch ingest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_batch_size_recorded(client: httpx.AsyncClient):
    """Ingest a batch of 3 events, check /metrics for engram_events_batch_size count > 0."""
    session_id = f"{PREFIX}-batch-{uuid.uuid4().hex[:8]}"
    events = [make_event(session_id=session_id) for _ in range(3)]

    batch_resp = await client.post("/v1/events/batch", json={"events": events})
    assert batch_resp.status_code == 201, f"Batch ingest failed: {batch_resp.text}"

    resp = await client.get("/metrics")
    assert resp.status_code == 200

    assert metric_exists(resp.text, "engram_events_batch_size"), (
        "engram_events_batch_size not found in /metrics"
    )
    # The _count suffix indicates how many observations the histogram has
    count = metric_value(resp.text, "engram_events_batch_size_count")
    assert count is not None and count > 0, (
        f"Expected engram_events_batch_size_count > 0, got {count}"
    )


# ---------------------------------------------------------------------------
# Test 7: engram_consumer_messages_processed_total is defined
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_contains_consumer_counters(client: httpx.AsyncClient):
    """GET /metrics contains engram_consumer_messages_processed_total (may be 0)."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert metric_exists(resp.text, "engram_consumer_messages_processed_total"), (
        "engram_consumer_messages_processed_total not found in /metrics"
    )


# ---------------------------------------------------------------------------
# Test 8: engram_graph_query_duration_seconds after context query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_contains_graph_query_duration(client: httpx.AsyncClient):
    """After GET /v1/context/{session_id}, /metrics has graph_query_duration."""
    session_id = f"{PREFIX}-ctx-{uuid.uuid4().hex[:8]}"

    # Call context endpoint to trigger a graph query
    await client.get(f"/v1/context/{session_id}")

    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert metric_exists(resp.text, "engram_graph_query_duration_seconds"), (
        "engram_graph_query_duration_seconds not found in /metrics"
    )


# ---------------------------------------------------------------------------
# Test 9: All 8 ADR-0008 metric names present
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_eight_metrics_present(client: httpx.AsyncClient):
    """Verify all 8 metric names from ADR-0008 appear in /metrics output."""
    expected_metrics = [
        "engram_http_requests_total",
        "engram_http_request_duration_seconds",
        "engram_events_ingested_total",
        "engram_events_batch_size",
        "engram_consumer_messages_processed_total",
        "engram_consumer_message_errors_total",
        "engram_consumer_lag_messages",
        "engram_graph_query_duration_seconds",
    ]

    # Generate traffic to ensure HTTP metrics have observations
    await client.get("/v1/health")

    resp = await client.get("/metrics")
    assert resp.status_code == 200

    missing = [m for m in expected_metrics if not metric_exists(resp.text, m)]
    assert not missing, f"Missing metrics in /metrics output: {missing}"


# ---------------------------------------------------------------------------
# Test 10: Route template used for label cardinality (not resolved path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_use_route_template_not_resolved_path(client: httpx.AsyncClient):
    """Hit /v1/context/test-session-xyz, then verify label uses route template."""
    await client.get("/v1/context/test-session-xyz")

    resp = await client.get("/metrics")
    assert resp.status_code == 200

    metrics_text = resp.text
    # Should see the route template, not the resolved path
    assert 'endpoint="/v1/context/{session_id}"' in metrics_text, (
        "Expected route template endpoint label, "
        "not resolved path. Metrics:\n" + metrics_text[:2000]
    )
    # Should NOT see the resolved path as a label value
    assert 'endpoint="/v1/context/test-session-xyz"' not in metrics_text, (
        "Found resolved path in metric labels — high cardinality risk"
    )


# ---------------------------------------------------------------------------
# Test 11: X-Request-Time-Ms header is numeric
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_time_header_numeric(client: httpx.AsyncClient):
    """GET /v1/health returns X-Request-Time-Ms header that parses as a positive float < 5000."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200

    raw = resp.headers.get("x-request-time-ms")
    assert raw is not None, "Missing X-Request-Time-Ms header"

    elapsed = float(raw)
    assert elapsed > 0, f"Expected X-Request-Time-Ms > 0, got {elapsed}"
    assert elapsed < 5000, f"Expected X-Request-Time-Ms < 5000, got {elapsed}"


# ---------------------------------------------------------------------------
# Test 12: Health returns 200 when healthy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_200_when_healthy(client: httpx.AsyncClient):
    """GET /v1/health returns 200 with status 'healthy'."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["status"] == "healthy", f"Expected 'healthy', got {body['status']}"


# ---------------------------------------------------------------------------
# Test 13: Health response structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_response_structure(client: httpx.AsyncClient):
    """Verify health response has keys: status, redis, neo4j, version."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200

    body = resp.json()
    required_keys = {"status", "redis", "neo4j", "version"}
    missing = required_keys - set(body.keys())
    assert not missing, f"Health response missing keys: {missing}"


# ---------------------------------------------------------------------------
# Test 14: Health redis and neo4j fields are booleans
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_redis_and_neo4j_booleans(client: httpx.AsyncClient):
    """redis and neo4j fields in health response are booleans."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200

    body = resp.json()
    assert isinstance(body["redis"], bool), (
        f"Expected 'redis' to be bool, got {type(body['redis']).__name__}"
    )
    assert isinstance(body["neo4j"], bool), (
        f"Expected 'neo4j' to be bool, got {type(body['neo4j']).__name__}"
    )


# ---------------------------------------------------------------------------
# Test 15: X-Request-ID auto-generated when none sent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_id_auto_generated(client: httpx.AsyncClient):
    """Response includes X-Request-ID header even when none sent in request."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200

    request_id = resp.headers.get("x-request-id")
    assert request_id is not None, "Missing X-Request-ID header in response"
    assert len(request_id) > 0, "X-Request-ID header is empty"


# ---------------------------------------------------------------------------
# Test 16: X-Request-ID is valid UUID4 when auto-generated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_id_is_valid_uuid4(client: httpx.AsyncClient):
    """Auto-generated X-Request-ID is a valid UUID4."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200

    request_id = resp.headers.get("x-request-id")
    assert request_id is not None, "Missing X-Request-ID header"

    parsed = uuid.UUID(request_id, version=4)
    assert str(parsed) == request_id, f"X-Request-ID is not a valid UUID4: {request_id}"


# ---------------------------------------------------------------------------
# Test 17: X-Request-ID echoed back when sent by client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_id_echoed_back(client: httpx.AsyncClient):
    """Sending X-Request-ID in request results in same ID in response."""
    custom_id = str(uuid.uuid4())
    resp = await client.get(
        "/v1/health",
        headers={"X-Request-ID": custom_id},
    )
    assert resp.status_code == 200

    returned_id = resp.headers.get("x-request-id")
    assert returned_id == custom_id, (
        f"Expected echoed X-Request-ID '{custom_id}', got '{returned_id}'"
    )
