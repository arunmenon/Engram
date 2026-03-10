"""Neo4j write operation benchmarks.

Measures throughput for single node MERGE, batch node MERGE (UNWIND),
single edge creation, batch edge creation, and entity node batch MERGE.

Prerequisites:
- Neo4j running at bolt://localhost:7687
- pytest-benchmark installed (``uv run --extra benchmark``)

Run: ``uv run pytest tests/benchmark/test_neo4j_writes.py -v``
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from tests.benchmark.conftest import (
    BENCHMARK_TENANT,
    make_bench_entity_nodes,
    make_bench_event_nodes,
    make_bench_follows_edges,
    skip_no_benchmark,
    skip_no_neo4j,
)

if TYPE_CHECKING:
    from context_graph.adapters.neo4j.store import Neo4jGraphStore

pytestmark = [
    pytest.mark.benchmark,
    skip_no_neo4j,
    skip_no_benchmark,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run an async coroutine synchronously for pytest-benchmark compatibility.

    pytest-benchmark's ``benchmark`` fixture calls the target function
    synchronously, so we need a bridge to run async store methods.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# 1. Single event node MERGE
# ---------------------------------------------------------------------------


class TestSingleMergeEventNode:
    """Benchmark single event node MERGE into Neo4j.

    Measures: nodes/sec for individual ``store.merge_event_node()`` calls.
    Expected baseline: ~500-2,000 nodes/sec on local Neo4j.
    """

    def test_single_merge_event_node(self, benchmark, neo4j_store: Neo4jGraphStore) -> None:
        """Benchmark a single ``store.merge_event_node()`` call."""
        nodes = make_bench_event_nodes(200)
        idx = {"i": 0}

        def merge_one():
            node = nodes[idx["i"] % len(nodes)]
            # Create a fresh node with unique ID to avoid dedup
            from context_graph.domain.models import EventNode

            fresh_node = EventNode(
                event_id=uuid4().hex,
                event_type=node.event_type,
                occurred_at=node.occurred_at,
                session_id=node.session_id,
                agent_id=node.agent_id,
                trace_id=node.trace_id,
                tool_name=node.tool_name,
                global_position=node.global_position,
                importance_score=node.importance_score,
            )
            idx["i"] += 1
            return _run_async(neo4j_store.merge_event_node(fresh_node, tenant_id=BENCHMARK_TENANT))

        benchmark(merge_one)


# ---------------------------------------------------------------------------
# 2. Batch event node MERGE (UNWIND)
# ---------------------------------------------------------------------------


class TestBatchMergeEventNodes:
    """Benchmark batch event node MERGE using UNWIND.

    The UNWIND strategy sends all node MERGEs in a single Cypher
    statement, dramatically reducing round-trips.
    Expected baseline: ~2,000-10,000 nodes/sec on local Neo4j.
    """

    @pytest.mark.parametrize("batch_size", [10, 50, 100])
    def test_batch_merge_event_nodes(
        self,
        benchmark,
        neo4j_store: Neo4jGraphStore,
        batch_size: int,
    ) -> None:
        """Benchmark ``store.merge_event_nodes_batch()``."""

        def merge_batch():
            nodes = make_bench_event_nodes(batch_size)
            return _run_async(
                neo4j_store.merge_event_nodes_batch(nodes, tenant_id=BENCHMARK_TENANT)
            )

        benchmark.extra_info["batch_size"] = batch_size
        benchmark(merge_batch)


# ---------------------------------------------------------------------------
# 3. Single edge creation
# ---------------------------------------------------------------------------


class TestSingleCreateEdge:
    """Benchmark single edge creation for representative edge types.

    Pre-creates event nodes, then benchmarks single-edge MERGE.
    Expected baseline: ~300-1,500 edges/sec on local Neo4j.
    """

    @pytest.fixture(autouse=True)
    def _seed_nodes(self, neo4j_store: Neo4jGraphStore) -> None:
        """Pre-create 100 event nodes for edge creation benchmarks."""
        self._nodes = make_bench_event_nodes(100, session_id="bench-edge-session")
        _run_async(neo4j_store.merge_event_nodes_batch(self._nodes, tenant_id=BENCHMARK_TENANT))

    def test_single_create_follows_edge(
        self,
        benchmark,
        neo4j_store: Neo4jGraphStore,
    ) -> None:
        """Benchmark single FOLLOWS edge creation."""
        from context_graph.domain.models import Edge, EdgeType

        idx = {"i": 1}

        def create_one():
            i = idx["i"] % (len(self._nodes) - 1) + 1
            edge = Edge(
                source=self._nodes[i].event_id,
                target=self._nodes[i - 1].event_id,
                edge_type=EdgeType.FOLLOWS,
                properties={"session_id": "bench-edge-session", "delta_ms": 100},
            )
            idx["i"] += 1
            return _run_async(neo4j_store.create_edge(edge, tenant_id=BENCHMARK_TENANT))

        benchmark(create_one)

    def test_single_create_caused_by_edge(
        self,
        benchmark,
        neo4j_store: Neo4jGraphStore,
    ) -> None:
        """Benchmark single CAUSED_BY edge creation."""
        from context_graph.domain.models import Edge, EdgeType

        idx = {"i": 2}

        def create_one():
            i = idx["i"] % (len(self._nodes) - 1) + 1
            edge = Edge(
                source=self._nodes[i].event_id,
                target=self._nodes[0].event_id,
                edge_type=EdgeType.CAUSED_BY,
                properties={"mechanism": "direct"},
            )
            idx["i"] += 1
            return _run_async(neo4j_store.create_edge(edge, tenant_id=BENCHMARK_TENANT))

        benchmark(create_one)


# ---------------------------------------------------------------------------
# 4. Batch edge creation (UNWIND)
# ---------------------------------------------------------------------------


class TestBatchCreateEdges:
    """Benchmark batch edge creation using UNWIND.

    Pre-creates event nodes, then benchmarks batch edge MERGE.
    Expected baseline: ~1,000-5,000 edges/sec on local Neo4j.
    """

    @pytest.fixture(autouse=True)
    def _seed_nodes(self, neo4j_store: Neo4jGraphStore) -> None:
        """Pre-create 200 event nodes for batch edge benchmarks."""
        self._nodes = make_bench_event_nodes(200, session_id="bench-batch-edge-session")
        _run_async(neo4j_store.merge_event_nodes_batch(self._nodes, tenant_id=BENCHMARK_TENANT))

    @pytest.mark.parametrize("batch_size", [20, 50, 100])
    def test_batch_create_edges(
        self,
        benchmark,
        neo4j_store: Neo4jGraphStore,
        batch_size: int,
    ) -> None:
        """Benchmark ``store.create_edges_batch()`` with FOLLOWS edges."""

        def create_batch():
            # Use a subset of nodes for edges to stay within bounds
            subset = self._nodes[: batch_size + 1]
            edges = make_bench_follows_edges(subset)
            return _run_async(neo4j_store.create_edges_batch(edges, tenant_id=BENCHMARK_TENANT))

        benchmark.extra_info["batch_size"] = batch_size
        benchmark(create_batch)


# ---------------------------------------------------------------------------
# 5. Batch entity node MERGE (UNWIND)
# ---------------------------------------------------------------------------


class TestBatchMergeEntityNodes:
    """Benchmark batch entity node MERGE using UNWIND.

    Expected baseline: ~1,500-8,000 nodes/sec on local Neo4j.
    """

    @pytest.mark.parametrize("batch_size", [10, 50])
    def test_batch_merge_entity_nodes(
        self,
        benchmark,
        neo4j_store: Neo4jGraphStore,
        batch_size: int,
    ) -> None:
        """Benchmark ``store.merge_entity_nodes_batch()``."""

        def merge_batch():
            nodes = make_bench_entity_nodes(batch_size)
            return _run_async(
                neo4j_store.merge_entity_nodes_batch(nodes, tenant_id=BENCHMARK_TENANT)
            )

        benchmark.extra_info["batch_size"] = batch_size
        benchmark(merge_batch)
