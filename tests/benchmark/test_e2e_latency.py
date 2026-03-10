"""End-to-end latency benchmarks.

Measures the full round-trip: ingest events into Redis, project them into
Neo4j using domain logic, then query the results back. This represents the
user-visible latency from event submission to queryable graph state.

Prerequisites:
- Redis Stack running at localhost:6379
- Neo4j running at bolt://localhost:7687
- pytest-benchmark installed (``uv run --extra benchmark``)

Run: ``uv run pytest tests/benchmark/test_e2e_latency.py -v``
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING

import pytest

from tests.benchmark.conftest import (
    BENCHMARK_TENANT,
    make_bench_events,
    skip_no_benchmark,
    skip_no_neo4j,
    skip_no_redis,
)

if TYPE_CHECKING:
    from neo4j import AsyncDriver

    from context_graph.adapters.neo4j.store import Neo4jGraphStore
    from context_graph.adapters.redis.store import RedisEventStore

pytestmark = [
    pytest.mark.benchmark,
    skip_no_redis,
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


# ---------------------------------------------------------------------------
# E2E latency
# ---------------------------------------------------------------------------


class TestEndToEndLatency:
    """Benchmark end-to-end latency: ingest -> project -> query.

    Ingests N=10 events into Redis, projects them into Neo4j using
    the domain projection logic, then queries them back via session
    event lookup. Measures total round-trip time.

    Expected baseline: p50 = 50-200 ms, p95 = 100-500 ms.
    """

    def test_e2e_ingest_project_query(
        self,
        benchmark,
        redis_store: RedisEventStore,
        neo4j_store: Neo4jGraphStore,
        neo4j_driver: AsyncDriver,
    ) -> None:
        """Benchmark full round-trip: ingest -> project -> query."""
        from context_graph.adapters.neo4j import queries as q
        from context_graph.domain.projection import project_event

        event_count = 10

        def e2e_round_trip():
            async def _round_trip():
                session_id = f"bench-e2e-{id(asyncio.get_event_loop())}"
                events = make_bench_events(event_count, session_id=session_id)

                # Phase 1: Ingest into Redis
                await redis_store.append_batch(events, tenant_id=BENCHMARK_TENANT)

                # Phase 2: Project into Neo4j
                all_nodes = []
                all_edges = []
                prev_event = None

                for event in events:
                    if event.global_position is None:
                        event = event.model_copy(update={"global_position": f"0-{id(event)}"})
                    result = project_event(event, prev_event)
                    all_nodes.append(result.node)
                    all_edges.extend(result.edges)
                    prev_event = event

                if all_nodes:
                    await neo4j_store.merge_event_nodes_batch(all_nodes, tenant_id=BENCHMARK_TENANT)
                if all_edges:
                    await neo4j_store.create_edges_batch(all_edges, tenant_id=BENCHMARK_TENANT)

                # Phase 3: Query from Neo4j
                async with neo4j_driver.session() as neo_session:
                    result = await neo_session.run(
                        q.GET_SESSION_EVENTS,
                        {
                            "session_id": session_id,
                            "tenant_id": BENCHMARK_TENANT,
                            "limit": event_count,
                        },
                    )
                    records = [r async for r in result]

                return len(records)

            return _run_async(_round_trip())

        benchmark.extra_info["event_count"] = event_count
        result = benchmark(e2e_round_trip)
        assert result > 0


class TestEndToEndLatencyDetailed:
    """Detailed E2E latency measurement with phase breakdown.

    NOT a pytest-benchmark test. Instead, runs 20 iterations and reports
    p50/p95 for each phase (ingest, project, query) and total.

    This is a measurement test, not a throughput benchmark.
    """

    @pytest.mark.slow
    def test_e2e_phase_breakdown(
        self,
        redis_store: RedisEventStore,
        neo4j_store: Neo4jGraphStore,
        neo4j_driver: AsyncDriver,
    ) -> None:
        """Measure p50/p95 for each E2E phase over 20 iterations."""
        from context_graph.adapters.neo4j import queries as q
        from context_graph.domain.projection import project_event

        event_count = 10
        iterations = 20

        ingest_times = []
        project_times = []
        query_times = []
        total_times = []

        for iteration in range(iterations):

            async def _round_trip(iter_num=iteration):
                session_id = f"bench-e2e-detail-{iter_num}"
                events = make_bench_events(event_count, session_id=session_id)

                # Phase 1: Ingest
                t0 = time.monotonic()
                await redis_store.append_batch(events, tenant_id=BENCHMARK_TENANT)
                t_ingest = time.monotonic() - t0

                # Phase 2: Project
                t1 = time.monotonic()
                all_nodes = []
                all_edges = []
                prev_event = None

                for event in events:
                    if event.global_position is None:
                        event = event.model_copy(update={"global_position": f"0-{id(event)}"})
                    result = project_event(event, prev_event)
                    all_nodes.append(result.node)
                    all_edges.extend(result.edges)
                    prev_event = event

                if all_nodes:
                    await neo4j_store.merge_event_nodes_batch(all_nodes, tenant_id=BENCHMARK_TENANT)
                if all_edges:
                    await neo4j_store.create_edges_batch(all_edges, tenant_id=BENCHMARK_TENANT)
                t_project = time.monotonic() - t1

                # Phase 3: Query
                t2 = time.monotonic()
                async with neo4j_driver.session() as neo_session:
                    result = await neo_session.run(
                        q.GET_SESSION_EVENTS,
                        {
                            "session_id": session_id,
                            "tenant_id": BENCHMARK_TENANT,
                            "limit": event_count,
                        },
                    )
                    _ = [r async for r in result]
                t_query = time.monotonic() - t2

                return t_ingest, t_project, t_query

            t_ingest, t_project, t_query = _run_async(_round_trip())
            ingest_times.append(t_ingest)
            project_times.append(t_project)
            query_times.append(t_query)
            total_times.append(t_ingest + t_project + t_query)

        def percentile(data, pct):
            sorted_data = sorted(data)
            idx = int(len(sorted_data) * pct / 100)
            return sorted_data[min(idx, len(sorted_data) - 1)]

        report = {
            "iterations": iterations,
            "event_count": event_count,
            "ingest_ms": {
                "p50": round(percentile(ingest_times, 50) * 1000, 2),
                "p95": round(percentile(ingest_times, 95) * 1000, 2),
            },
            "project_ms": {
                "p50": round(percentile(project_times, 50) * 1000, 2),
                "p95": round(percentile(project_times, 95) * 1000, 2),
            },
            "query_ms": {
                "p50": round(percentile(query_times, 50) * 1000, 2),
                "p95": round(percentile(query_times, 95) * 1000, 2),
            },
            "total_ms": {
                "p50": round(percentile(total_times, 50) * 1000, 2),
                "p95": round(percentile(total_times, 95) * 1000, 2),
            },
        }

        print("\n--- E2E Phase Breakdown ---")  # noqa: T201
        print(json.dumps(report, indent=2))  # noqa: T201
        print("--- End Report ---\n")  # noqa: T201

        # Sanity: total p50 should be under 2 seconds
        assert report["total_ms"]["p50"] < 2000, (
            f"E2E p50 latency ({report['total_ms']['p50']} ms) exceeds 2s threshold"
        )
