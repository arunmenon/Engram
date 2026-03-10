"""Graph compaction throughput benchmarks.

Pre-seeds a session with 200 events where 50 are covered by Summary nodes,
then benchmarks compact_session_events() throughput and get_tenant_node_budget()
latency.

Prerequisites:
- Neo4j running at bolt://localhost:7687
- pytest-benchmark installed (``uv run --extra benchmark``)

Run: ``uv run pytest tests/benchmark/test_compaction.py -v``
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from tests.benchmark.conftest import (
    BENCHMARK_TENANT,
    make_bench_event_nodes,
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


# ---------------------------------------------------------------------------
# Compaction throughput
# ---------------------------------------------------------------------------


class TestCompactionThroughput:
    """Benchmark graph compaction: replacing dense event clusters with summaries.

    Pre-seeds 1 session with 200 events. 50 of the oldest events are covered
    by a Summary node (SUMMARIZES edges). compact_session_events() should
    identify and delete those 50 events.

    Expected baseline: 10-50 events compacted/sec on local Neo4j.
    """

    @pytest.fixture(autouse=True)
    def _seed_compaction_data(self, neo4j_driver: AsyncDriver) -> None:
        """Pre-seed a session with 200 events and summary coverage for 50."""
        self._driver = neo4j_driver
        self._session_id = "bench-compact-session"

        async def _seed():
            from context_graph.adapters.neo4j import queries as q

            # Create 200 event nodes in the session
            nodes = make_bench_event_nodes(200, session_id=self._session_id)

            # Make the first 50 events old enough to be compactable
            old_time = datetime.now(UTC) - timedelta(days=30)
            for i in range(50):
                nodes[i] = nodes[i].model_copy(
                    update={"occurred_at": old_time + timedelta(minutes=i)}
                )

            # Write event nodes
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
                    "tenant_id": BENCHMARK_TENANT,
                }
                for n in nodes
            ]
            async with neo4j_driver.session() as session:
                await session.run(q.BATCH_MERGE_EVENT_NODES, {"events": params})

            # Create a Summary node covering the first 50 events
            summary_id = f"summary-bench-{uuid4().hex[:8]}"
            async with neo4j_driver.session() as session:
                await session.run(
                    q.MERGE_SUMMARY_NODE,
                    {
                        "summary_id": summary_id,
                        "scope": "session",
                        "scope_id": self._session_id,
                        "content": "Benchmark summary covering first 50 events",
                        "created_at": datetime.now(UTC).isoformat(),
                        "event_count": 50,
                        "time_range": [
                            nodes[0].occurred_at.isoformat(),
                            nodes[49].occurred_at.isoformat(),
                        ],
                        "tenant_id": BENCHMARK_TENANT,
                    },
                )

            # Create SUMMARIZES edges from summary to each of the 50 events
            edge_params = [
                {
                    "source_id": summary_id,
                    "target_id": nodes[i].event_id,
                    "props": {"created_at": datetime.now(UTC).isoformat()},
                }
                for i in range(50)
            ]
            async with neo4j_driver.session() as session:
                await session.run(
                    q.BATCH_MERGE_SUMMARIZES,
                    {"edges": edge_params, "tenant_id": BENCHMARK_TENANT},
                )

            # Create FOLLOWS edges between consecutive events
            follows_params = [
                {
                    "source_id": nodes[i].event_id,
                    "target_id": nodes[i - 1].event_id,
                    "props": {"session_id": self._session_id, "delta_ms": 100},
                }
                for i in range(1, len(nodes))
            ]
            batch_size = 500
            for i in range(0, len(follows_params), batch_size):
                batch = follows_params[i : i + batch_size]
                async with neo4j_driver.session() as session:
                    await session.run(
                        q.BATCH_MERGE_FOLLOWS,
                        {"edges": batch, "tenant_id": BENCHMARK_TENANT},
                    )

            self._nodes = nodes
            self._summary_id = summary_id

        _run_async(_seed())

    def test_compact_session_events(
        self,
        benchmark,
        neo4j_driver: AsyncDriver,
    ) -> None:
        """Benchmark compact_session_events() for a session with 200 events, 50 summarized."""
        from context_graph.adapters.neo4j.maintenance import compact_session_events

        def compact():
            return _run_async(
                compact_session_events(
                    neo4j_driver,
                    database="neo4j",
                    session_id=self._session_id,
                    tenant_id=BENCHMARK_TENANT,
                    min_events=50,
                    keep_recent=10,
                )
            )

        result = benchmark(compact)
        # On first run, should compact some events.
        # On subsequent benchmark rounds, may return 0 since events were deleted.
        assert isinstance(result, int)


class TestNodeBudgetLatency:
    """Benchmark get_tenant_node_budget() latency.

    Pre-seeds 500 nodes of mixed types to give the budget query
    realistic cardinality to count.

    Expected baseline: 5-30 ms on local Neo4j.
    """

    @pytest.fixture(autouse=True)
    def _seed_budget_data(self, neo4j_driver: AsyncDriver) -> None:
        """Pre-seed 500 event nodes for budget query benchmark."""
        self._driver = neo4j_driver

        async def _seed():
            from context_graph.adapters.neo4j import queries as q

            nodes = make_bench_event_nodes(500, session_id="bench-budget-session")
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
                    "tenant_id": BENCHMARK_TENANT,
                }
                for n in nodes
            ]
            async with neo4j_driver.session() as session:
                await session.run(q.BATCH_MERGE_EVENT_NODES, {"events": params})

        _run_async(_seed())

    def test_get_tenant_node_budget(
        self,
        benchmark,
        neo4j_driver: AsyncDriver,
    ) -> None:
        """Benchmark get_tenant_node_budget() query latency."""
        from context_graph.adapters.neo4j.maintenance import get_tenant_node_budget

        def query_budget():
            return _run_async(
                get_tenant_node_budget(
                    neo4j_driver,
                    database="neo4j",
                    tenant_id=BENCHMARK_TENANT,
                    max_nodes=100_000,
                )
            )

        result = benchmark(query_budget)
        assert isinstance(result, dict)
        assert "total_nodes" in result
        assert "utilization_pct" in result
        assert result["total_nodes"] > 0
