"""Shared fixtures for the benchmark test suite.

Provides Redis client, RedisEventStore, Neo4j driver, Neo4jGraphStore,
event factories, graph seed helpers, and cleanup routines.
All benchmarks use tenant_id="bench-tenant" for isolation from other tests.

Benchmarks require:
- A running Redis Stack instance at localhost:6379
- A running Neo4j instance at bolt://localhost:7687
- pytest-benchmark (optional -- tests skip gracefully if unavailable)
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest

from context_graph.domain.models import (
    Edge,
    EdgeType,
    EntityNode,
    EntityType,
    Event,
    EventNode,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from neo4j import AsyncDriver

# ---------------------------------------------------------------------------
# Optional dependency detection
# ---------------------------------------------------------------------------

try:
    import pytest_benchmark  # noqa: F401

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False


def _redis_available() -> bool:
    """Check whether Redis is reachable at localhost:6379 (blocking probe)."""
    import socket

    try:
        sock = socket.create_connection(("localhost", 6379), timeout=1.0)
        sock.close()
        return True
    except OSError:
        return False


REDIS_AVAILABLE = _redis_available()


def _neo4j_available() -> bool:
    """Check whether Neo4j is reachable at localhost:7687 (blocking probe)."""
    import socket

    try:
        sock = socket.create_connection(("localhost", 7687), timeout=1.0)
        sock.close()
        return True
    except OSError:
        return False


NEO4J_AVAILABLE = _neo4j_available()

BENCHMARK_TENANT = "bench-tenant"

# Realistic event types for varied benchmark payloads
_EVENT_TYPES = [
    "agent.invoke",
    "tool.execute",
    "llm.chat",
    "llm.completion",
    "observation.input",
    "observation.output",
    "system.session_start",
    "system.session_end",
]

_TOOL_NAMES = [
    "web-search",
    "code-interpreter",
    "file-reader",
    "database-query",
    "api-caller",
    None,
    None,
    None,
]


# ---------------------------------------------------------------------------
# Event loop (session-scoped for async fixtures)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Provide a session-scoped event loop for async benchmark fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Event factories
# ---------------------------------------------------------------------------


def make_bench_events(
    n: int,
    session_id: str | None = None,
    agent_id: str = "bench-agent",
) -> list[Event]:
    """Generate *n* realistic Event objects with varied types and payloads.

    Each event gets a unique event_id and a randomized event_type drawn from
    the OTel-aligned taxonomy. Tool names are assigned to tool.execute events.
    Timestamps are spaced 100ms apart for realistic ordering.
    """
    sid = session_id or f"bench-session-{uuid4().hex[:8]}"
    trace_id = f"trace-{uuid4().hex[:8]}"
    base_time = datetime.now(UTC)
    events: list[Event] = []

    for i in range(n):
        event_type = _EVENT_TYPES[i % len(_EVENT_TYPES)]
        tool_name = _TOOL_NAMES[i % len(_TOOL_NAMES)] if event_type == "tool.execute" else None
        importance = random.randint(1, 10) if i % 3 == 0 else None  # noqa: S311

        events.append(
            Event(
                event_id=uuid4(),
                event_type=event_type,
                occurred_at=base_time + timedelta(milliseconds=i * 100),
                session_id=sid,
                agent_id=agent_id,
                trace_id=trace_id,
                payload_ref=f"payload:bench:{uuid4().hex[:8]}",
                tool_name=tool_name,
                importance_hint=importance,
            )
        )
    return events


@pytest.fixture()
def event_factory():
    """Return the ``make_bench_events`` factory callable."""
    return make_bench_events


@pytest.fixture()
def benchmark_tenant() -> str:
    """Return the benchmark tenant ID."""
    return BENCHMARK_TENANT


# ---------------------------------------------------------------------------
# Redis fixtures (skip when unavailable)
# ---------------------------------------------------------------------------

skip_no_redis = pytest.mark.skipif(
    not REDIS_AVAILABLE,
    reason="Redis not available at localhost:6379",
)

skip_no_neo4j = pytest.mark.skipif(
    not NEO4J_AVAILABLE,
    reason="Neo4j not available at localhost:7687",
)

skip_no_benchmark = pytest.mark.skipif(
    not HAS_BENCHMARK,
    reason="pytest-benchmark not installed",
)


@pytest.fixture()
async def redis_client():
    """Provide an async Redis client connected to localhost.

    Skips the test if Redis is not reachable.
    """
    if not REDIS_AVAILABLE:
        pytest.skip("Redis not available at localhost:6379")

    from redis.asyncio import Redis

    client = Redis(
        host="localhost",
        port=6379,
        db=0,
        decode_responses=False,
        max_connections=50,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )
    try:
        await client.ping()
    except Exception:
        await client.aclose()
        pytest.skip("Redis not reachable at localhost:6379")

    yield client
    await client.aclose()


@pytest.fixture()
async def redis_store(redis_client) -> AsyncGenerator:
    """Provide a connected RedisEventStore using the benchmark tenant.

    The store is created with default RedisSettings and the shared redis_client.
    Indexes are ensured before yielding.
    """
    from context_graph.adapters.redis.store import RedisEventStore
    from context_graph.settings import RedisSettings

    settings = RedisSettings()
    store = RedisEventStore(client=redis_client, settings=settings)
    await store._register_script()
    await store.ensure_indexes()
    yield store


@pytest.fixture(autouse=True)
async def cleanup_bench_keys(redis_client):
    """Delete all keys prefixed with ``t:bench-tenant:`` after each test.

    This ensures benchmark data does not leak across tests or persist
    after the benchmark session.
    """
    yield

    if redis_client is None:
        return

    cursor = 0
    pattern = f"t:{BENCHMARK_TENANT}:*"
    while True:
        cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=500)
        if keys:
            await redis_client.delete(*keys)
        if cursor == 0:
            break


# ---------------------------------------------------------------------------
# Neo4j fixtures (skip when unavailable)
# ---------------------------------------------------------------------------


@pytest.fixture()
async def neo4j_driver() -> AsyncGenerator[AsyncDriver, None]:
    """Provide an async Neo4j driver connected to localhost.

    Skips the test if Neo4j is not reachable.
    """
    if not NEO4J_AVAILABLE:
        pytest.skip("Neo4j not available at localhost:7687")

    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "engram-dev-password"),
        max_connection_pool_size=50,
    )
    try:
        async with driver.session() as session:
            await session.run("RETURN 1")
    except Exception:
        await driver.close()
        pytest.skip("Neo4j not reachable at localhost:7687")

    yield driver
    await driver.close()


@pytest.fixture()
async def neo4j_store(neo4j_driver: AsyncDriver) -> AsyncGenerator[Any, None]:
    """Provide a Neo4jGraphStore instance using the benchmark driver.

    Ensures constraints and indexes are created before yielding.
    """
    from context_graph.adapters.neo4j.store import Neo4jGraphStore
    from context_graph.settings import Neo4jSettings

    settings = Neo4jSettings()
    store = Neo4jGraphStore(settings=settings)
    # Replace the driver with our fixture driver
    store._driver = neo4j_driver
    await store.ensure_constraints()
    yield store


@pytest.fixture(autouse=True)
async def cleanup_bench_neo4j(neo4j_driver: AsyncDriver | None = None):
    """Delete all Neo4j nodes with tenant_id="bench-tenant" after each test.

    This ensures benchmark data does not leak across tests or persist
    after the benchmark session.
    """
    yield

    if neo4j_driver is None:
        return

    try:
        async with neo4j_driver.session() as session:
            await session.run(
                "MATCH (n {tenant_id: $tenant_id}) DETACH DELETE n",
                {"tenant_id": BENCHMARK_TENANT},
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Graph node/edge factories for Neo4j benchmarks
# ---------------------------------------------------------------------------

_ENTITY_NAMES = [
    "authentication",
    "database",
    "redis",
    "neo4j",
    "kafka",
    "kubernetes",
    "docker",
    "graphql",
    "rest-api",
    "postgresql",
    "elasticsearch",
    "monitoring",
    "logging",
    "security",
    "caching",
    "migrations",
    "deployment",
    "ci-cd",
    "testing",
    "refactoring",
]


def make_bench_event_nodes(
    n: int,
    session_id: str | None = None,
    agent_id: str = "bench-agent",
) -> list[EventNode]:
    """Generate *n* EventNode objects for Neo4j write benchmarks.

    Each node gets a unique event_id and realistic properties.
    Timestamps are spaced 100ms apart.
    """
    sid = session_id or f"bench-session-{uuid4().hex[:8]}"
    trace_id = f"trace-{uuid4().hex[:8]}"
    base_time = datetime.now(UTC)

    nodes: list[EventNode] = []
    for i in range(n):
        event_type = _EVENT_TYPES[i % len(_EVENT_TYPES)]
        tool_name = _TOOL_NAMES[i % len(_TOOL_NAMES)] if event_type == "tool.execute" else None
        importance = random.randint(1, 10) if i % 3 == 0 else None  # noqa: S311

        nodes.append(
            EventNode(
                event_id=uuid4().hex,
                event_type=event_type,
                occurred_at=base_time + timedelta(milliseconds=i * 100),
                session_id=sid,
                agent_id=agent_id,
                trace_id=trace_id,
                tool_name=tool_name,
                global_position=(
                    f"{int((base_time + timedelta(milliseconds=i * 100)).timestamp() * 1000)}-{i}"
                ),
                importance_score=importance,
            )
        )
    return nodes


def make_bench_entity_nodes(
    n: int,
) -> list[EntityNode]:
    """Generate *n* EntityNode objects for Neo4j write benchmarks."""
    base_time = datetime.now(UTC)
    entity_types = list(EntityType)

    nodes: list[EntityNode] = []
    for i in range(n):
        nodes.append(
            EntityNode(
                entity_id=uuid4().hex,
                name=f"{_ENTITY_NAMES[i % len(_ENTITY_NAMES)]}-{uuid4().hex[:4]}",
                entity_type=entity_types[i % len(entity_types)],
                first_seen=base_time - timedelta(hours=random.randint(1, 100)),  # noqa: S311
                last_seen=base_time,
                mention_count=random.randint(1, 20),  # noqa: S311
            )
        )
    return nodes


def make_bench_follows_edges(
    event_nodes: list[EventNode],
) -> list[Edge]:
    """Create FOLLOWS edges between consecutive event nodes (temporal chain)."""
    edges: list[Edge] = []
    for i in range(1, len(event_nodes)):
        edges.append(
            Edge(
                source=event_nodes[i].event_id,
                target=event_nodes[i - 1].event_id,
                edge_type=EdgeType.FOLLOWS,
                properties={
                    "session_id": event_nodes[i].session_id,
                    "delta_ms": 100,
                },
            )
        )
    return edges


def make_bench_references_edges(
    event_nodes: list[EventNode],
    entity_nodes: list[EntityNode],
) -> list[Edge]:
    """Create REFERENCES edges: each event references 1-3 entities."""
    edges: list[Edge] = []
    for i, event_node in enumerate(event_nodes):
        num_refs = (i % 3) + 1
        for j in range(num_refs):
            entity_idx = (i + j) % len(entity_nodes)
            edges.append(
                Edge(
                    source=event_node.event_id,
                    target=entity_nodes[entity_idx].entity_id,
                    edge_type=EdgeType.REFERENCES,
                    properties={"mention_count": 1, "role": "object"},
                )
            )
    return edges


def make_bench_caused_by_edges(
    event_nodes: list[EventNode],
    density: float = 0.1,
) -> list[Edge]:
    """Create CAUSED_BY edges at the given density (fraction of possible edges)."""
    edges: list[Edge] = []
    for i in range(2, len(event_nodes)):
        if random.random() < density:  # noqa: S311
            parent_idx = random.randint(0, i - 1)  # noqa: S311
            edges.append(
                Edge(
                    source=event_nodes[i].event_id,
                    target=event_nodes[parent_idx].event_id,
                    edge_type=EdgeType.CAUSED_BY,
                    properties={"mechanism": "direct"},
                )
            )
    return edges


async def seed_graph(
    neo4j_driver: AsyncDriver,
    num_events: int,
    num_entities: int,
    num_sessions: int,
    tenant_id: str = BENCHMARK_TENANT,
    database: str = "neo4j",
) -> dict[str, Any]:
    """Seed the Neo4j graph with events, entities, and edges.

    Returns a dict with the created nodes and edges for query benchmarks:
    - event_nodes: list of EventNode
    - entity_nodes: list of EntityNode
    - follows_edges: list of Edge
    - references_edges: list of Edge
    - caused_by_edges: list of Edge
    - session_ids: list of session IDs
    """
    from context_graph.adapters.neo4j import queries as q

    events_per_session = num_events // num_sessions
    all_event_nodes: list[EventNode] = []
    all_follows: list[Edge] = []
    all_caused_by: list[Edge] = []
    session_ids: list[str] = []

    for s in range(num_sessions):
        sid = f"bench-session-{s:04d}"
        session_ids.append(sid)
        session_events = make_bench_event_nodes(events_per_session, session_id=sid)
        all_event_nodes.extend(session_events)
        all_follows.extend(make_bench_follows_edges(session_events))
        all_caused_by.extend(make_bench_caused_by_edges(session_events, density=0.1))

    entity_nodes = make_bench_entity_nodes(num_entities)
    all_references = make_bench_references_edges(all_event_nodes, entity_nodes)

    # Batch write events in chunks of 500
    batch_size = 500
    for i in range(0, len(all_event_nodes), batch_size):
        batch = all_event_nodes[i : i + batch_size]
        params = [
            {
                "event_id": n.event_id,
                "event_type": n.event_type,
                "occurred_at": n.occurred_at.isoformat(),
                "session_id": n.session_id,
                "agent_id": n.agent_id,
                "trace_id": n.trace_id,
                "tool_name": n.tool_name,
                "global_position": n.global_position,
                "keywords": n.keywords,
                "summary": n.summary,
                "importance_score": n.importance_score,
                "access_count": n.access_count,
                "last_accessed_at": None,
                "tenant_id": tenant_id,
            }
            for n in batch
        ]
        async with neo4j_driver.session(database=database) as session:
            await session.run(q.BATCH_MERGE_EVENT_NODES, {"events": params})

    # Batch write entities
    for i in range(0, len(entity_nodes), batch_size):
        batch = entity_nodes[i : i + batch_size]
        params = [
            {
                "entity_id": n.entity_id,
                "name": n.name,
                "entity_type": str(n.entity_type),
                "first_seen": n.first_seen.isoformat(),
                "last_seen": n.last_seen.isoformat(),
                "mention_count": n.mention_count,
                "embedding": n.embedding,
                "tenant_id": tenant_id,
            }
            for n in batch
        ]
        async with neo4j_driver.session(database=database) as session:
            await session.run(q.BATCH_MERGE_ENTITY_NODES, {"nodes": params})

    # Batch write FOLLOWS edges
    for i in range(0, len(all_follows), batch_size):
        batch = all_follows[i : i + batch_size]
        edge_params = [
            {"source_id": e.source, "target_id": e.target, "props": e.properties} for e in batch
        ]
        async with neo4j_driver.session(database=database) as session:
            await session.run(q.BATCH_MERGE_FOLLOWS, {"edges": edge_params, "tenant_id": tenant_id})

    # Batch write CAUSED_BY edges
    for i in range(0, len(all_caused_by), batch_size):
        batch = all_caused_by[i : i + batch_size]
        edge_params = [
            {"source_id": e.source, "target_id": e.target, "props": e.properties} for e in batch
        ]
        async with neo4j_driver.session(database=database) as session:
            await session.run(
                q.BATCH_MERGE_CAUSED_BY, {"edges": edge_params, "tenant_id": tenant_id}
            )

    # Batch write REFERENCES edges
    for i in range(0, len(all_references), batch_size):
        batch = all_references[i : i + batch_size]
        edge_params = [
            {"source_id": e.source, "target_id": e.target, "props": e.properties} for e in batch
        ]
        async with neo4j_driver.session(database=database) as session:
            await session.run(
                q.BATCH_MERGE_REFERENCES, {"edges": edge_params, "tenant_id": tenant_id}
            )

    return {
        "event_nodes": all_event_nodes,
        "entity_nodes": entity_nodes,
        "follows_edges": all_follows,
        "references_edges": all_references,
        "caused_by_edges": all_caused_by,
        "session_ids": session_ids,
    }
