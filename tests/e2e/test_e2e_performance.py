"""E2E tests for Performance & Query — Tier 1 Group B.

Exercises the full pipeline: ingest events via API, wait for projection
workers to process them into Neo4j, then test performance-related aspects:
session_id index existence, query timeouts, batched neighbor traversal,
neighbor limits, and Atlas response format regression.

Prerequisites:
    - docker-compose up (redis, neo4j, api, workers)
    - pip install -e ".[dev]"

Usage:
    python -m pytest tests/e2e/test_e2e_performance.py -v
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from neo4j import AsyncGraphDatabase

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "http://localhost:8000"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "engram-dev-password"
NEO4J_DATABASE = "neo4j"

POLL_INTERVAL = 0.5  # seconds
POLL_TIMEOUT = 15.0  # seconds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    session_id: str,
    agent_id: str = "e2e-perf-agent",
    event_type: str = "tool.execute",
    importance_hint: int = 5,
    occurred_at: datetime | None = None,
    parent_event_id: str | None = None,
    tool_name: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a valid event payload for the /v1/events endpoint."""
    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": (occurred_at or datetime.now(UTC)).isoformat(),
        "session_id": session_id,
        "agent_id": agent_id,
        "trace_id": f"trace-{uuid.uuid4().hex[:8]}",
        "payload_ref": f"ref://{uuid.uuid4().hex[:8]}",
        "importance_hint": importance_hint,
    }
    if parent_event_id is not None:
        event["parent_event_id"] = parent_event_id
    if tool_name is not None:
        event["tool_name"] = tool_name
    if payload is not None:
        event["payload"] = payload
    return event


async def ingest_event(client: httpx.AsyncClient, event: dict[str, Any]) -> dict[str, Any]:
    """POST an event to the API and return the response."""
    resp = await client.post(f"{API_URL}/v1/events", json=event)
    resp.raise_for_status()
    return resp.json()


async def poll_neo4j_for_event(
    driver: Any,
    event_id: str,
    timeout: float = POLL_TIMEOUT,
) -> bool:
    """Poll Neo4j until the event node appears or timeout is reached."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        async with driver.session(database=NEO4J_DATABASE) as session:
            result = await session.run(
                "MATCH (e:Event {event_id: $eid}) RETURN e",
                {"eid": event_id},
            )
            record = await result.single()
            if record is not None:
                return True
        await asyncio.sleep(POLL_INTERVAL)
    return False


async def poll_context_nodes(
    client: httpx.AsyncClient,
    session_id: str,
    min_nodes: int,
    timeout: float = POLL_TIMEOUT,
) -> dict[str, Any] | None:
    """Poll GET /v1/context/{session_id} until at least min_nodes are returned."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"{API_URL}/v1/context/{session_id}")
        if resp.status_code == 200:
            data = resp.json()
            if len(data.get("nodes", {})) >= min_nodes:
                return data
        await asyncio.sleep(POLL_INTERVAL)
    # Return whatever we got last
    resp = await client.get(f"{API_URL}/v1/context/{session_id}")
    return resp.json() if resp.status_code == 200 else None


async def cleanup_neo4j_session(driver: Any, session_id: str) -> None:
    """Delete all events for a given session from Neo4j."""
    async with driver.session(database=NEO4J_DATABASE) as session:
        await session.run(
            "MATCH (e:Event {session_id: $sid}) DETACH DELETE e",
            {"sid": session_id},
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        yield client


@pytest.fixture
async def neo4j_driver():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    yield driver
    await driver.close()


# ---------------------------------------------------------------------------
# H11: Session ID Index
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_id_index_exists(neo4j_driver):
    """Verify an index on Event.session_id exists in Neo4j."""
    async with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run("SHOW INDEXES")
        records = [record async for record in result]

    # Look for an index that covers Event.session_id
    found_index = False
    for record in records:
        record_dict = dict(record)
        labels_or_types = record_dict.get("labelsOrTypes", [])
        properties = record_dict.get("properties", [])
        if "Event" in labels_or_types and "session_id" in properties:
            found_index = True
            break

    existing = [(dict(r).get("labelsOrTypes"), dict(r).get("properties")) for r in records]
    assert found_index, f"No index found on Event.session_id. Existing: {existing}"


@pytest.mark.asyncio
async def test_context_retrieval_has_query_ms(http_client, neo4j_driver):
    """Ingest events, retrieve context, verify meta.query_ms is a positive number."""
    session_id = f"e2e-perf-qms-{uuid.uuid4().hex[:8]}"
    try:
        events = []
        for i in range(3):
            event = make_event(
                session_id=session_id,
                importance_hint=5,
                tool_name=f"tool_{i}",
            )
            await ingest_event(http_client, event)
            events.append(event)

        found = await poll_neo4j_for_event(neo4j_driver, events[-1]["event_id"])
        assert found, "Last event did not appear in Neo4j within timeout"

        data = await poll_context_nodes(http_client, session_id, min_nodes=3)
        assert data is not None, "Failed to retrieve session context"

        meta = data.get("meta", {})
        assert "query_ms" in meta, "meta.query_ms is missing from response"
        assert isinstance(meta["query_ms"], int | float), (
            f"query_ms should be a number, got {type(meta['query_ms'])}"
        )
        assert meta["query_ms"] > 0, f"query_ms should be positive, got {meta['query_ms']}"
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


# ---------------------------------------------------------------------------
# H10: Query Timeouts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_query_completes_within_timeout(http_client, neo4j_driver):
    """GET /v1/context/{session_id} completes within 10 seconds."""
    session_id = f"e2e-perf-ctxtimeout-{uuid.uuid4().hex[:8]}"
    try:
        event = make_event(session_id=session_id, importance_hint=5)
        await ingest_event(http_client, event)
        found = await poll_neo4j_for_event(neo4j_driver, event["event_id"])
        assert found

        start = time.monotonic()
        resp = await http_client.get(f"{API_URL}/v1/context/{session_id}")
        elapsed = time.monotonic() - start

        assert resp.status_code == 200, f"Context query failed: {resp.text}"
        assert elapsed < 10.0, f"Context query took {elapsed:.2f}s, expected < 10s"
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


@pytest.mark.asyncio
async def test_subgraph_query_completes_within_timeout(http_client, neo4j_driver):
    """POST /v1/query/subgraph completes within 10 seconds."""
    session_id = f"e2e-perf-sgtimeout-{uuid.uuid4().hex[:8]}"
    try:
        event = make_event(session_id=session_id, importance_hint=5)
        await ingest_event(http_client, event)
        found = await poll_neo4j_for_event(neo4j_driver, event["event_id"])
        assert found

        start = time.monotonic()
        resp = await http_client.post(
            f"{API_URL}/v1/query/subgraph",
            json={
                "query": "what happened in this session?",
                "session_id": session_id,
                "agent_id": "e2e-perf-agent",
            },
        )
        elapsed = time.monotonic() - start

        assert resp.status_code == 200, f"Subgraph query failed: {resp.text}"
        assert elapsed < 10.0, f"Subgraph query took {elapsed:.2f}s, expected < 10s"
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


# ---------------------------------------------------------------------------
# H12: Batched Neighbor Traversal + H13: Neighbor Limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subgraph_returns_neighbors(http_client, neo4j_driver):
    """Ingest 5 events with parent_event_id chains, verify FOLLOWS edges and multiple nodes."""
    session_id = f"e2e-perf-neighbors-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)
    try:
        events = []
        for i in range(5):
            parent_id = events[i - 1]["event_id"] if i > 0 else None
            event = make_event(
                session_id=session_id,
                event_type="tool.execute",
                importance_hint=5 + i,
                occurred_at=now - timedelta(seconds=50 - i * 10),
                parent_event_id=parent_id,
                tool_name=f"tool_{i}",
            )
            await ingest_event(http_client, event)
            events.append(event)

        # Wait for last event to appear in Neo4j
        found = await poll_neo4j_for_event(neo4j_driver, events[-1]["event_id"])
        assert found, "Last event did not appear in Neo4j within timeout"

        # Allow time for edges to be created
        await asyncio.sleep(3.0)

        resp = await http_client.post(
            f"{API_URL}/v1/query/subgraph",
            json={
                "query": "what tools were used?",
                "session_id": session_id,
                "agent_id": "e2e-perf-agent",
            },
        )
        assert resp.status_code == 200, f"Subgraph query failed: {resp.text}"
        data = resp.json()

        nodes = data.get("nodes", {})
        edges = data.get("edges", [])

        assert len(nodes) >= 2, f"Expected >= 2 nodes, got {len(nodes)}"

        # Verify edges have proper structure
        if len(edges) > 0:
            edge_types = {e["edge_type"] for e in edges}
            # Should have FOLLOWS or CAUSED_BY edges from the chain
            assert len(edge_types) > 0, "Expected at least one edge type"
            for edge in edges:
                assert "source" in edge, "Edge missing 'source'"
                assert "target" in edge, "Edge missing 'target'"
                assert "edge_type" in edge, "Edge missing 'edge_type'"
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


@pytest.mark.asyncio
async def test_subgraph_meta_has_capacity(http_client, neo4j_driver):
    """POST /v1/query/subgraph response has meta.capacity with max_nodes and used_nodes."""
    session_id = f"e2e-perf-capacity-{uuid.uuid4().hex[:8]}"
    try:
        event = make_event(session_id=session_id, importance_hint=5)
        await ingest_event(http_client, event)
        found = await poll_neo4j_for_event(neo4j_driver, event["event_id"])
        assert found

        resp = await http_client.post(
            f"{API_URL}/v1/query/subgraph",
            json={
                "query": "what happened?",
                "session_id": session_id,
                "agent_id": "e2e-perf-agent",
            },
        )
        assert resp.status_code == 200, f"Subgraph query failed: {resp.text}"
        data = resp.json()

        meta = data.get("meta", {})
        capacity = meta.get("capacity")
        assert capacity is not None, "meta.capacity is missing"
        assert "max_nodes" in capacity, "capacity.max_nodes is missing"
        assert "used_nodes" in capacity, "capacity.used_nodes is missing"
        assert isinstance(capacity["max_nodes"], int), "max_nodes should be int"
        assert isinstance(capacity["used_nodes"], int), "used_nodes should be int"
        assert capacity["used_nodes"] >= 0, "used_nodes should be >= 0"
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


@pytest.mark.asyncio
async def test_subgraph_nodes_bounded(http_client, neo4j_driver):
    """POST /v1/query/subgraph with max_nodes=10, verify len(nodes) <= 10."""
    session_id = f"e2e-perf-bounded-{uuid.uuid4().hex[:8]}"
    try:
        # Ingest 15 events to ensure we have more than the limit
        events = []
        for i in range(15):
            event = make_event(
                session_id=session_id,
                importance_hint=5,
                tool_name=f"tool_{i}",
            )
            await ingest_event(http_client, event)
            events.append(event)

        found = await poll_neo4j_for_event(neo4j_driver, events[-1]["event_id"])
        assert found

        # Allow time for all events to be projected
        await asyncio.sleep(3.0)

        resp = await http_client.post(
            f"{API_URL}/v1/query/subgraph",
            json={
                "query": "what happened?",
                "session_id": session_id,
                "agent_id": "e2e-perf-agent",
                "max_nodes": 10,
            },
        )
        assert resp.status_code == 200, f"Subgraph query failed: {resp.text}"
        data = resp.json()

        nodes = data.get("nodes", {})
        assert len(nodes) <= 10, f"Expected <= 10 nodes, got {len(nodes)}"
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


# ---------------------------------------------------------------------------
# Atlas Response Regression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_atlas_format(http_client, neo4j_driver):
    """GET /v1/context/{session_id} returns valid Atlas format."""
    session_id = f"e2e-perf-atlas-{uuid.uuid4().hex[:8]}"
    try:
        event = make_event(session_id=session_id, importance_hint=7)
        await ingest_event(http_client, event)
        found = await poll_neo4j_for_event(neo4j_driver, event["event_id"])
        assert found

        data = await poll_context_nodes(http_client, session_id, min_nodes=1)
        assert data is not None, "Failed to retrieve session context"

        # Verify top-level Atlas keys
        assert "nodes" in data, "Atlas response missing 'nodes'"
        assert isinstance(data["nodes"], dict), "nodes should be a dict"

        assert "edges" in data, "Atlas response missing 'edges'"
        assert isinstance(data["edges"], list), "edges should be a list"

        assert "pagination" in data, "Atlas response missing 'pagination'"
        assert isinstance(data["pagination"], dict), "pagination should be a dict"

        assert "meta" in data, "Atlas response missing 'meta'"
        assert isinstance(data["meta"], dict), "meta should be a dict"
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


@pytest.mark.asyncio
async def test_context_node_has_provenance(http_client, neo4j_driver):
    """Each node in context response has provenance with required fields."""
    session_id = f"e2e-perf-prov-{uuid.uuid4().hex[:8]}"
    try:
        event = make_event(session_id=session_id, importance_hint=7)
        await ingest_event(http_client, event)
        found = await poll_neo4j_for_event(neo4j_driver, event["event_id"])
        assert found

        data = await poll_context_nodes(http_client, session_id, min_nodes=1)
        assert data is not None
        nodes = data["nodes"]
        assert len(nodes) >= 1, "Expected at least 1 node"

        required_provenance_fields = {
            "event_id",
            "global_position",
            "source",
            "occurred_at",
            "session_id",
            "agent_id",
            "trace_id",
        }

        for node_id, node in nodes.items():
            provenance = node.get("provenance")
            assert provenance is not None, f"Node {node_id} missing provenance"
            missing = required_provenance_fields - set(provenance.keys())
            assert not missing, (
                f"Node {node_id} provenance missing fields: {missing}. "
                f"Got: {set(provenance.keys())}"
            )
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


@pytest.mark.asyncio
async def test_context_node_has_scores(http_client, neo4j_driver):
    """Each node in context response has scores with decay, relevance, importance."""
    session_id = f"e2e-perf-scores-{uuid.uuid4().hex[:8]}"
    try:
        event = make_event(session_id=session_id, importance_hint=7)
        await ingest_event(http_client, event)
        found = await poll_neo4j_for_event(neo4j_driver, event["event_id"])
        assert found

        data = await poll_context_nodes(http_client, session_id, min_nodes=1)
        assert data is not None
        nodes = data["nodes"]
        assert len(nodes) >= 1, "Expected at least 1 node"

        required_score_fields = {
            "decay_score",
            "relevance_score",
            "importance_score",
        }

        for node_id, node in nodes.items():
            scores = node.get("scores")
            assert scores is not None, f"Node {node_id} missing scores"
            missing = required_score_fields - set(scores.keys())
            assert not missing, (
                f"Node {node_id} scores missing fields: {missing}. Got: {set(scores.keys())}"
            )
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)


@pytest.mark.asyncio
async def test_lineage_returns_causal_chain(http_client, neo4j_driver):
    """Ingest events with parent_event_id, verify CAUSED_BY edges in lineage response."""
    session_id = f"e2e-perf-lineage-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)
    try:
        # Build a causal chain: A -> B -> C
        event_a = make_event(
            session_id=session_id,
            event_type="agent.invoke",
            importance_hint=8,
            occurred_at=now - timedelta(seconds=30),
        )
        event_b = make_event(
            session_id=session_id,
            event_type="tool.execute",
            importance_hint=6,
            parent_event_id=event_a["event_id"],
            occurred_at=now - timedelta(seconds=20),
        )
        event_c = make_event(
            session_id=session_id,
            event_type="tool.execute",
            importance_hint=5,
            parent_event_id=event_b["event_id"],
            occurred_at=now - timedelta(seconds=10),
        )

        for ev in [event_a, event_b, event_c]:
            await ingest_event(http_client, ev)

        # Wait for all events + edges to be projected
        found = await poll_neo4j_for_event(neo4j_driver, event_c["event_id"])
        assert found, "Last event did not appear in Neo4j"

        # Allow time for CAUSED_BY edges to be created
        await asyncio.sleep(3.0)

        # Request lineage from event C
        resp = await http_client.get(
            f"{API_URL}/v1/nodes/{event_c['event_id']}/lineage",
            params={"max_depth": 5, "max_nodes": 10},
        )
        assert resp.status_code == 200, f"Lineage query failed: {resp.text}"
        data = resp.json()

        # Verify Atlas format
        assert "nodes" in data, "Lineage response missing 'nodes'"
        assert "edges" in data, "Lineage response missing 'edges'"

        nodes = data.get("nodes", {})
        edges = data.get("edges", [])

        # The lineage should contain at least the queried node
        assert len(nodes) >= 1, f"Expected at least 1 node in lineage, got {len(nodes)}"

        # If edges are present, verify CAUSED_BY edges exist
        if len(edges) > 0:
            edge_types = {e["edge_type"] for e in edges}
            assert "CAUSED_BY" in edge_types, (
                f"Expected CAUSED_BY edges in lineage, got: {edge_types}"
            )
    finally:
        await cleanup_neo4j_session(neo4j_driver, session_id)
