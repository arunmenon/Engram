"""Scaled read degradation curve benchmarks.

Profiles Neo4j read performance at four graph sizes (S/M/L/XL) to produce
degradation curves showing how latency scales with graph cardinality.

Graph size tiers:
- S:  10K nodes,  30K edges,  100 sessions,  500 entities
- M:  100K nodes, 300K edges, 1K sessions,   5K entities
- L:  1M nodes,   3M edges,   10K sessions,  50K entities  (@slow @scaled)
- XL: 5M nodes,   15M edges,  50K sessions,  250K entities (@slow @scaled)

Queries profiled at each tier:
- session_events, lineage_depth3, lineage_depth5, neighbor_batch,
  seed_causal, seed_entity_hubs, graph_stats, compaction (node_budget)

Prerequisites:
- Neo4j running at bolt://localhost:7687
- pytest-benchmark installed (``uv run --extra benchmark``)
- For L/XL: sufficient Neo4j heap (>=4GB for L, >=16GB for XL)

Run fast tiers: ``uv run pytest tests/benchmark/test_scaled_reads.py -m "not slow" -v``
Run all tiers:  ``uv run pytest tests/benchmark/test_scaled_reads.py -v``
Run scaled only: ``uv run pytest tests/benchmark/test_scaled_reads.py -m scaled -v``
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

import pytest

from tests.benchmark.conftest import (
    BENCHMARK_TENANT,
    make_bench_caused_by_edges,
    make_bench_entity_nodes,
    make_bench_event_nodes,
    make_bench_follows_edges,
    skip_no_benchmark,
    skip_no_neo4j,
)

if TYPE_CHECKING:
    from neo4j import AsyncDriver

pytestmark = [
    pytest.mark.benchmark,
    skip_no_neo4j,
    skip_no_benchmark,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run an async coroutine synchronously for pytest-benchmark compatibility."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _lineage_params(eid: str, depth: int) -> dict[str, Any]:
    """Build parameter dict for GET_LINEAGE query."""
    return {
        "node_id": eid,
        "tenant_id": BENCHMARK_TENANT,
        "max_depth": depth,
        "max_nodes": 100,
    }


# ---------------------------------------------------------------------------
# Graph tier definitions
# ---------------------------------------------------------------------------

TIERS = {
    "S": {
        "num_events": 10_000,
        "num_entities": 500,
        "num_sessions": 100,
        "events_per_session": 100,
    },
    "M": {
        "num_events": 100_000,
        "num_entities": 5_000,
        "num_sessions": 1_000,
        "events_per_session": 100,
    },
    "L": {
        "num_events": 1_000_000,
        "num_entities": 50_000,
        "num_sessions": 10_000,
        "events_per_session": 100,
    },
    "XL": {
        "num_events": 5_000_000,
        "num_entities": 250_000,
        "num_sessions": 50_000,
        "events_per_session": 100,
    },
}


async def _seed_tier(
    neo4j_driver: AsyncDriver,
    tier_name: str,
    tenant_id: str = BENCHMARK_TENANT,
    database: str = "neo4j",
) -> dict[str, Any]:
    """Seed the graph for a given tier. Returns metadata about seeded data.

    Writes in batches of 500 to avoid Neo4j transaction size limits.
    """
    from context_graph.adapters.neo4j import queries as q

    tier = TIERS[tier_name]
    num_events = tier["num_events"]
    num_entities = tier["num_entities"]
    num_sessions = tier["num_sessions"]
    events_per_session = tier["events_per_session"]
    batch_size = 500

    session_ids: list[str] = []
    sample_event_ids: list[str] = []

    # Seed events session by session (in batches)
    for s in range(num_sessions):
        sid = f"bench-scaled-{tier_name}-s{s:06d}"
        session_ids.append(sid)
        session_events = make_bench_event_nodes(events_per_session, session_id=sid)

        # Collect sample event IDs from first session for queries
        if s == 0:
            sample_event_ids = [n.event_id for n in session_events]

        # Batch write events
        for i in range(0, len(session_events), batch_size):
            batch = session_events[i : i + batch_size]
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

        # Write FOLLOWS edges for this session
        follows = make_bench_follows_edges(session_events)
        for i in range(0, len(follows), batch_size):
            batch = follows[i : i + batch_size]
            edge_params = [
                {
                    "source_id": e.source,
                    "target_id": e.target,
                    "props": e.properties,
                }
                for e in batch
            ]
            async with neo4j_driver.session(database=database) as session:
                await session.run(
                    q.BATCH_MERGE_FOLLOWS,
                    {"edges": edge_params, "tenant_id": tenant_id},
                )

        # Write CAUSED_BY edges (sparse)
        caused_by = make_bench_caused_by_edges(session_events, density=0.05)
        if caused_by:
            for i in range(0, len(caused_by), batch_size):
                batch = caused_by[i : i + batch_size]
                edge_params = [
                    {
                        "source_id": e.source,
                        "target_id": e.target,
                        "props": e.properties,
                    }
                    for e in batch
                ]
                async with neo4j_driver.session(database=database) as session:
                    await session.run(
                        q.BATCH_MERGE_CAUSED_BY,
                        {"edges": edge_params, "tenant_id": tenant_id},
                    )

    # Seed entities
    entity_nodes = make_bench_entity_nodes(num_entities)
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

    return {
        "tier": tier_name,
        "num_events": num_events,
        "num_entities": num_entities,
        "num_sessions": num_sessions,
        "session_ids": session_ids,
        "sample_event_ids": sample_event_ids,
        "sample_session_id": session_ids[0] if session_ids else "",
    }


async def _cleanup_tier(
    neo4j_driver: AsyncDriver,
    tenant_id: str = BENCHMARK_TENANT,
    database: str = "neo4j",
) -> None:
    """Remove all benchmark nodes for the tenant."""
    async with neo4j_driver.session(database=database) as session:
        # Delete in batches to avoid timeout
        while True:
            result = await session.run(
                "MATCH (n {tenant_id: $tenant_id}) "
                "WITH n LIMIT 10000 DETACH DELETE n "
                "RETURN count(*) AS deleted",
                {"tenant_id": tenant_id},
            )
            record = await result.single()
            if record is None or record["deleted"] == 0:
                break


async def _get_neo4j_memory_stats(
    neo4j_driver: AsyncDriver,
    database: str = "neo4j",
) -> dict[str, Any]:
    """Query Neo4j JVM memory statistics."""
    try:
        async with neo4j_driver.session(database=database) as session:
            result = await session.run(
                "CALL dbms.queryJmx('java.lang:type=Memory') "
                "YIELD name, attributes "
                "RETURN attributes"
            )
            records = [r async for r in result]
            if records:
                attrs = records[0]["attributes"]
                heap_used = attrs.get("HeapMemoryUsage", {}).get("value", {}).get("used", 0)
                heap_max = attrs.get("HeapMemoryUsage", {}).get("value", {}).get("max", 0)
                return {
                    "heap_used_bytes": heap_used,
                    "heap_max_bytes": heap_max,
                }
    except Exception:
        pass
    return {"heap_used_bytes": 0, "heap_max_bytes": 0}


# ---------------------------------------------------------------------------
# Reusable query runners for each query type
# ---------------------------------------------------------------------------


def _query_session_events(neo4j_driver: AsyncDriver, sid: str) -> list:
    from context_graph.adapters.neo4j import queries as q

    async def _q():
        async with neo4j_driver.session() as s:
            r = await s.run(
                q.GET_SESSION_EVENTS,
                {
                    "session_id": sid,
                    "tenant_id": BENCHMARK_TENANT,
                    "limit": 100,
                },
            )
            return [rec async for rec in r]

    return _run_async(_q())


def _query_lineage(neo4j_driver: AsyncDriver, eid: str, depth: int) -> list:
    from context_graph.adapters.neo4j import queries as q

    async def _q():
        async with neo4j_driver.session() as s:
            r = await s.run(q.GET_LINEAGE, _lineage_params(eid, depth))
            return [rec async for rec in r]

    return _run_async(_q())


def _query_neighbors_batch(neo4j_driver: AsyncDriver, eids: list[str]) -> list:
    from context_graph.adapters.neo4j import queries as q

    async def _q():
        async with neo4j_driver.session() as s:
            r = await s.run(
                q.GET_EVENT_NEIGHBORS_BATCH,
                {
                    "event_ids": eids,
                    "tenant_id": BENCHMARK_TENANT,
                    "neighbor_limit": 50,
                },
            )
            return [rec async for rec in r]

    return _run_async(_q())


def _query_seed_causal(neo4j_driver: AsyncDriver, sid: str) -> list:
    from context_graph.adapters.neo4j import queries as q

    async def _q():
        async with neo4j_driver.session() as s:
            r = await s.run(
                q.GET_SEED_CAUSAL_ROOTS,
                {
                    "session_id": sid,
                    "tenant_id": BENCHMARK_TENANT,
                    "seed_limit": 10,
                },
            )
            return [rec async for rec in r]

    return _run_async(_q())


def _query_seed_entity_hubs(neo4j_driver: AsyncDriver, sid: str) -> list:
    from context_graph.adapters.neo4j import queries as q

    async def _q():
        async with neo4j_driver.session() as s:
            r = await s.run(
                q.GET_SEED_ENTITY_HUBS,
                {
                    "session_id": sid,
                    "tenant_id": BENCHMARK_TENANT,
                    "seed_limit": 10,
                },
            )
            return [rec async for rec in r]

    return _run_async(_q())


def _query_graph_stats(neo4j_driver: AsyncDriver) -> dict:
    from context_graph.adapters.neo4j.maintenance import get_graph_stats

    return _run_async(
        get_graph_stats(
            neo4j_driver,
            database="neo4j",
            tenant_id=BENCHMARK_TENANT,
        )
    )


def _query_node_budget(neo4j_driver: AsyncDriver) -> dict:
    from context_graph.adapters.neo4j.maintenance import (
        get_tenant_node_budget,
    )

    return _run_async(
        get_tenant_node_budget(
            neo4j_driver,
            database="neo4j",
            tenant_id=BENCHMARK_TENANT,
        )
    )


# ---------------------------------------------------------------------------
# S tier (10K nodes) -- fast
# ---------------------------------------------------------------------------


class TestScaledReadsSmall:
    """Scaled read benchmarks at S tier: 10K events, 500 entities.

    Expected baselines (local Neo4j):
    - session_events: 1-5 ms
    - lineage_depth3: 2-15 ms
    - lineage_depth5: 5-30 ms
    - neighbor_batch: 5-20 ms
    - seed_causal: 2-10 ms
    - seed_entity_hubs: 2-10 ms
    - graph_stats: 10-50 ms
    - node_budget: 5-30 ms
    """

    @pytest.fixture(autouse=True)
    def _seed(self, neo4j_driver: AsyncDriver) -> None:
        """Seed S tier graph."""
        self._driver = neo4j_driver
        self._meta = _run_async(_seed_tier(neo4j_driver, "S"))

    def test_session_events_tier_s(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Session events lookup at S tier."""
        sid = self._meta["sample_session_id"]
        benchmark.extra_info["tier"] = "S"
        result = benchmark(lambda: _query_session_events(neo4j_driver, sid))
        assert len(result) > 0

    def test_lineage_depth3_tier_s(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Lineage traversal depth 3 at S tier."""
        eid = self._meta["sample_event_ids"][50]
        benchmark.extra_info["tier"] = "S"
        benchmark(lambda: _query_lineage(neo4j_driver, eid, 3))

    def test_lineage_depth5_tier_s(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Lineage traversal depth 5 at S tier."""
        eid = self._meta["sample_event_ids"][50]
        benchmark.extra_info["tier"] = "S"
        benchmark(lambda: _query_lineage(neo4j_driver, eid, 5))

    def test_neighbor_batch_tier_s(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Batch neighbor expansion at S tier."""
        eids = self._meta["sample_event_ids"][:10]
        benchmark.extra_info["tier"] = "S"
        benchmark(lambda: _query_neighbors_batch(neo4j_driver, eids))

    def test_seed_causal_tier_s(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Causal root seed selection at S tier."""
        sid = self._meta["sample_session_id"]
        benchmark.extra_info["tier"] = "S"
        benchmark(lambda: _query_seed_causal(neo4j_driver, sid))

    def test_seed_entity_hubs_tier_s(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Entity hub seed selection at S tier."""
        sid = self._meta["sample_session_id"]
        benchmark.extra_info["tier"] = "S"
        benchmark(lambda: _query_seed_entity_hubs(neo4j_driver, sid))

    def test_graph_stats_tier_s(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Graph stats at S tier."""
        benchmark.extra_info["tier"] = "S"
        result = benchmark(lambda: _query_graph_stats(neo4j_driver))
        assert result["total_nodes"] > 0

    def test_node_budget_tier_s(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Node budget query at S tier."""
        benchmark.extra_info["tier"] = "S"
        result = benchmark(lambda: _query_node_budget(neo4j_driver))
        assert result["total_nodes"] > 0


# ---------------------------------------------------------------------------
# M tier (100K nodes) -- moderate
# ---------------------------------------------------------------------------


class TestScaledReadsMedium:
    """Scaled read benchmarks at M tier: 100K events, 5K entities.

    Expected: 2-5x latency increase over S tier for most queries.
    """

    @pytest.fixture(autouse=True)
    def _seed(self, neo4j_driver: AsyncDriver) -> None:
        """Seed M tier graph."""
        self._driver = neo4j_driver
        self._meta = _run_async(_seed_tier(neo4j_driver, "M"))

    def test_session_events_tier_m(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Session events lookup at M tier."""
        sid = self._meta["sample_session_id"]
        benchmark.extra_info["tier"] = "M"
        result = benchmark(lambda: _query_session_events(neo4j_driver, sid))
        assert len(result) > 0

    def test_lineage_depth3_tier_m(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Lineage traversal depth 3 at M tier."""
        eid = self._meta["sample_event_ids"][50]
        benchmark.extra_info["tier"] = "M"
        benchmark(lambda: _query_lineage(neo4j_driver, eid, 3))

    def test_lineage_depth5_tier_m(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Lineage traversal depth 5 at M tier."""
        eid = self._meta["sample_event_ids"][50]
        benchmark.extra_info["tier"] = "M"
        benchmark(lambda: _query_lineage(neo4j_driver, eid, 5))

    def test_neighbor_batch_tier_m(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Batch neighbor expansion at M tier."""
        eids = self._meta["sample_event_ids"][:10]
        benchmark.extra_info["tier"] = "M"
        benchmark(lambda: _query_neighbors_batch(neo4j_driver, eids))

    def test_seed_causal_tier_m(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Causal root seed selection at M tier."""
        sid = self._meta["sample_session_id"]
        benchmark.extra_info["tier"] = "M"
        benchmark(lambda: _query_seed_causal(neo4j_driver, sid))

    def test_seed_entity_hubs_tier_m(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Entity hub seed selection at M tier."""
        sid = self._meta["sample_session_id"]
        benchmark.extra_info["tier"] = "M"
        benchmark(lambda: _query_seed_entity_hubs(neo4j_driver, sid))

    def test_graph_stats_tier_m(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Graph stats at M tier."""
        benchmark.extra_info["tier"] = "M"
        result = benchmark(lambda: _query_graph_stats(neo4j_driver))
        assert result["total_nodes"] > 0

    def test_node_budget_tier_m(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Node budget query at M tier."""
        benchmark.extra_info["tier"] = "M"
        result = benchmark(lambda: _query_node_budget(neo4j_driver))
        assert result["total_nodes"] > 0


# ---------------------------------------------------------------------------
# L tier (1M nodes) -- slow
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.scaled
class TestScaledReadsLarge:
    """Scaled reads at L tier: 1M events, 50K entities, 10K sessions.

    WARNING: Seeding takes 5-15 min. Requires >= 4GB Neo4j heap.
    Expected: 5-20x latency increase over S tier.
    """

    @pytest.fixture(autouse=True)
    def _seed(self, neo4j_driver: AsyncDriver) -> None:
        """Seed L tier graph."""
        self._driver = neo4j_driver
        self._mem_before = _run_async(_get_neo4j_memory_stats(neo4j_driver))
        self._meta = _run_async(_seed_tier(neo4j_driver, "L"))
        self._mem_after = _run_async(_get_neo4j_memory_stats(neo4j_driver))

    def test_session_events_tier_l(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Session events lookup at L tier."""
        sid = self._meta["sample_session_id"]
        benchmark.extra_info["tier"] = "L"
        benchmark.extra_info["heap_before"] = self._mem_before
        benchmark.extra_info["heap_after"] = self._mem_after
        result = benchmark(lambda: _query_session_events(neo4j_driver, sid))
        assert len(result) > 0

    def test_lineage_depth3_tier_l(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Lineage traversal depth 3 at L tier."""
        eid = self._meta["sample_event_ids"][50]
        benchmark.extra_info["tier"] = "L"
        benchmark(lambda: _query_lineage(neo4j_driver, eid, 3))

    def test_lineage_depth5_tier_l(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Lineage traversal depth 5 at L tier."""
        eid = self._meta["sample_event_ids"][50]
        benchmark.extra_info["tier"] = "L"
        benchmark(lambda: _query_lineage(neo4j_driver, eid, 5))

    def test_graph_stats_tier_l(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Graph stats at L tier."""
        benchmark.extra_info["tier"] = "L"
        result = benchmark(lambda: _query_graph_stats(neo4j_driver))
        assert result["total_nodes"] > 0

    def test_node_budget_tier_l(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Node budget query at L tier."""
        benchmark.extra_info["tier"] = "L"
        result = benchmark(lambda: _query_node_budget(neo4j_driver))
        assert result["total_nodes"] > 0


# ---------------------------------------------------------------------------
# XL tier (5M nodes) -- slow, scaled
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.scaled
class TestScaledReadsExtraLarge:
    """Scaled reads at XL: 5M events, 250K entities, 50K sessions.

    WARNING: Seeding takes 30-60 min. Requires >= 16GB Neo4j heap.
    Expected: 20-100x latency increase over S tier.
    """

    @pytest.fixture(autouse=True)
    def _seed(self, neo4j_driver: AsyncDriver) -> None:
        """Seed XL tier graph."""
        self._driver = neo4j_driver
        self._mem_before = _run_async(_get_neo4j_memory_stats(neo4j_driver))
        self._meta = _run_async(_seed_tier(neo4j_driver, "XL"))
        self._mem_after = _run_async(_get_neo4j_memory_stats(neo4j_driver))

    def test_session_events_tier_xl(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Session events lookup at XL tier."""
        sid = self._meta["sample_session_id"]
        benchmark.extra_info["tier"] = "XL"
        benchmark.extra_info["heap_before"] = self._mem_before
        benchmark.extra_info["heap_after"] = self._mem_after
        result = benchmark(lambda: _query_session_events(neo4j_driver, sid))
        assert len(result) > 0

    def test_lineage_depth3_tier_xl(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Lineage traversal depth 3 at XL tier."""
        eid = self._meta["sample_event_ids"][50]
        benchmark.extra_info["tier"] = "XL"
        benchmark(lambda: _query_lineage(neo4j_driver, eid, 3))

    def test_lineage_depth5_tier_xl(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Lineage traversal depth 5 at XL tier."""
        eid = self._meta["sample_event_ids"][50]
        benchmark.extra_info["tier"] = "XL"
        benchmark(lambda: _query_lineage(neo4j_driver, eid, 5))

    def test_graph_stats_tier_xl(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Graph stats at XL tier."""
        benchmark.extra_info["tier"] = "XL"
        result = benchmark(lambda: _query_graph_stats(neo4j_driver))
        assert result["total_nodes"] > 0

    def test_node_budget_tier_xl(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Node budget query at XL tier."""
        benchmark.extra_info["tier"] = "XL"
        result = benchmark(lambda: _query_node_budget(neo4j_driver))
        assert result["total_nodes"] > 0


# ---------------------------------------------------------------------------
# Memory report (NOT a benchmark test)
# ---------------------------------------------------------------------------


class TestScaledMemoryReport:
    """Report Neo4j memory usage across tiers.

    NOT a pytest-benchmark test. Seeds S and M tiers, records heap
    before/after, and prints a sizing report.
    """

    @pytest.mark.slow
    def test_memory_sizing_report(self, neo4j_driver: AsyncDriver) -> None:
        """Measure Neo4j memory growth from empty to S and M tiers."""

        async def _measure():
            mem_empty = await _get_neo4j_memory_stats(neo4j_driver)

            # Seed S tier
            await _seed_tier(neo4j_driver, "S")
            mem_s = await _get_neo4j_memory_stats(neo4j_driver)

            # Cleanup
            await _cleanup_tier(neo4j_driver)

            # Seed M tier
            await _seed_tier(neo4j_driver, "M")
            mem_m = await _get_neo4j_memory_stats(neo4j_driver)

            # Cleanup
            await _cleanup_tier(neo4j_driver)

            return {
                "empty": mem_empty,
                "s_10k_nodes": mem_s,
                "m_100k_nodes": mem_m,
            }

        result = _run_async(_measure())

        report = {
            "memory_sizing": result,
            "recommendations": {
                "s_10k": "1-2 GB heap sufficient",
                "m_100k": "2-4 GB heap recommended",
                "l_1m": "4-8 GB heap recommended",
                "xl_5m": "16-32 GB heap recommended",
            },
        }

        print("\n--- Neo4j Memory Sizing Report ---")  # noqa: T201
        print(json.dumps(report, indent=2))  # noqa: T201
        print("--- End Report ---\n")  # noqa: T201
