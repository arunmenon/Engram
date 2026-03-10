"""Consumer projection throughput benchmarks.

Simulates the projection consumer pipeline: events are ingested into Redis,
then projected into Neo4j using the domain projection logic and batch writes.

This measures the full pipeline throughput: fetch event JSON from Redis,
run domain projection (event_to_node + edge computation), batch-write to Neo4j.

Prerequisites:
- Redis Stack running at localhost:6379
- Neo4j running at bolt://localhost:7687
- pytest-benchmark installed (``uv run --extra benchmark``)

Run: ``uv run pytest tests/benchmark/test_projection_throughput.py -v``
"""

from __future__ import annotations

import asyncio
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
# Projection throughput
# ---------------------------------------------------------------------------


class TestProjectionThroughput:
    """Benchmark the projection pipeline: Redis ingest -> domain projection -> Neo4j write.

    Simulates what Consumer 1 (ProjectionConsumer) does:
    1. Events are pre-ingested into Redis (done in fixture).
    2. Projection runs domain logic to produce EventNodes + edges.
    3. Batch writes nodes and edges into Neo4j.

    Expected baseline: 50-500 events/sec for full pipeline.
    """

    @pytest.mark.parametrize("event_count", [100, 500, 1000])
    def test_projection_throughput(
        self,
        benchmark,
        redis_store: RedisEventStore,
        neo4j_store: Neo4jGraphStore,
        event_count: int,
    ) -> None:
        """Benchmark full projection pipeline for N events."""
        from context_graph.domain.projection import project_event

        session_id = f"bench-proj-{event_count}"
        events = make_bench_events(event_count, session_id=session_id)

        # Pre-ingest events into Redis so they have global_position
        _run_async(redis_store.append_batch(events, tenant_id=BENCHMARK_TENANT))

        def project_all():
            async def _project():
                all_nodes = []
                all_edges = []
                prev_event = None

                for event in events:
                    # Simulate global_position assignment
                    if event.global_position is None:
                        event = event.model_copy(update={"global_position": f"0-{id(event)}"})

                    result = project_event(event, prev_event)
                    all_nodes.append(result.node)
                    all_edges.extend(result.edges)
                    prev_event = event

                # Batch write to Neo4j
                if all_nodes:
                    await neo4j_store.merge_event_nodes_batch(all_nodes, tenant_id=BENCHMARK_TENANT)
                if all_edges:
                    await neo4j_store.create_edges_batch(all_edges, tenant_id=BENCHMARK_TENANT)

                return len(all_nodes)

            return _run_async(_project())

        benchmark.extra_info["event_count"] = event_count
        result = benchmark(project_all)
        assert result == event_count


class TestProjectionDomainOnly:
    """Benchmark the pure domain projection logic (no I/O).

    Isolates the cost of event_to_node and edge computation from
    Redis/Neo4j overhead. This represents the theoretical throughput
    ceiling for the projection consumer.

    Expected baseline: 50,000-200,000 events/sec (pure Python).
    """

    @pytest.mark.parametrize("event_count", [100, 500, 1000])
    def test_domain_projection_throughput(
        self,
        benchmark,
        event_count: int,
    ) -> None:
        """Benchmark pure domain projection (no database I/O)."""
        from context_graph.domain.projection import project_event

        session_id = f"bench-domain-proj-{event_count}"
        events = make_bench_events(event_count, session_id=session_id)

        # Pre-assign global_position to avoid ValueError
        for i, event in enumerate(events):
            if event.global_position is None:
                events[i] = event.model_copy(update={"global_position": f"0-{i}"})

        def project_all():
            all_nodes = []
            all_edges = []
            prev_event = None

            for event in events:
                result = project_event(event, prev_event)
                all_nodes.append(result.node)
                all_edges.extend(result.edges)
                prev_event = event

            return len(all_nodes)

        benchmark.extra_info["event_count"] = event_count
        result = benchmark(project_all)
        assert result == event_count
