"""Neo4j read operation benchmarks.

Pre-seeds the graph with 1000 events, 100 entities, and ~2000 edges across
10 sessions, then measures read latency for session event lookup, lineage
traversal, neighbor expansion, seed selection queries, and graph stats.

Prerequisites:
- Neo4j running at bolt://localhost:7687
- pytest-benchmark installed (``uv run --extra benchmark``)

Run: ``uv run pytest tests/benchmark/test_neo4j_reads.py -v``
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from tests.benchmark.conftest import (
    BENCHMARK_TENANT,
    seed_graph,
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
# Shared seed fixture
# ---------------------------------------------------------------------------


class TestNeo4jReads:
    """All Neo4j read benchmarks share a single pre-seeded graph.

    Pre-seed: 1000 events, 100 entities, ~2000 edges across 10 sessions.

    Expected baselines (local Neo4j):
    - Session events lookup: 1-5 ms
    - Lineage depth 1: 1-5 ms
    - Lineage depth 3: 2-15 ms
    - Lineage depth 5: 5-50 ms
    - Neighbor expansion: 1-10 ms
    - Seed selection (causal): 2-20 ms
    - Seed selection (entity hub): 2-20 ms
    - Graph stats: 5-50 ms
    """

    @pytest.fixture(autouse=True)
    def _seed_graph(self, neo4j_driver: AsyncDriver) -> None:
        """Pre-seed the graph with 1000 events, 100 entities, and edges."""
        self._driver = neo4j_driver
        self._seed_data = _run_async(
            seed_graph(
                neo4j_driver,
                num_events=1000,
                num_entities=100,
                num_sessions=10,
            )
        )
        self._session_ids = self._seed_data["session_ids"]
        self._event_nodes = self._seed_data["event_nodes"]
        self._entity_nodes = self._seed_data["entity_nodes"]

    # -------------------------------------------------------------------
    # 1. Session events lookup
    # -------------------------------------------------------------------

    def test_get_session_events(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Benchmark GET_SESSION_EVENTS query for a single session."""
        from context_graph.adapters.neo4j import queries as q

        session_id = self._session_ids[0]

        def query_session():
            async def _query():
                async with neo4j_driver.session() as session:
                    result = await session.run(
                        q.GET_SESSION_EVENTS,
                        {
                            "session_id": session_id,
                            "tenant_id": BENCHMARK_TENANT,
                            "limit": 100,
                        },
                    )
                    return [r async for r in result]

            return _run_async(_query())

        result = benchmark(query_session)
        assert isinstance(result, list)
        assert len(result) > 0

    # -------------------------------------------------------------------
    # 2. Lineage traversal at varying depths
    # -------------------------------------------------------------------

    @pytest.mark.parametrize("max_depth", [1, 3, 5])
    def test_get_lineage(
        self,
        benchmark,
        neo4j_driver: AsyncDriver,
        max_depth: int,
    ) -> None:
        """Benchmark GET_LINEAGE query at varying depths."""
        from context_graph.adapters.neo4j import queries as q

        # Pick an event from the middle of a session (more likely to have lineage)
        event_id = self._event_nodes[50].event_id

        def query_lineage():
            async def _query():
                async with neo4j_driver.session() as session:
                    result = await session.run(
                        q.GET_LINEAGE,
                        {
                            "node_id": event_id,
                            "tenant_id": BENCHMARK_TENANT,
                            "max_depth": max_depth,
                            "max_nodes": 100,
                        },
                    )
                    return [r async for r in result]

            return _run_async(_query())

        benchmark.extra_info["max_depth"] = max_depth
        result = benchmark(query_lineage)
        assert isinstance(result, list)

    # -------------------------------------------------------------------
    # 3. Neighbor expansion
    # -------------------------------------------------------------------

    def test_get_neighbors(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Benchmark GET_EVENT_NEIGHBORS query for a single event."""
        from context_graph.adapters.neo4j import queries as q

        event_id = self._event_nodes[25].event_id

        def query_neighbors():
            async def _query():
                async with neo4j_driver.session() as session:
                    result = await session.run(
                        q.GET_EVENT_NEIGHBORS,
                        {
                            "event_id": event_id,
                            "tenant_id": BENCHMARK_TENANT,
                            "neighbor_limit": 50,
                        },
                    )
                    return [r async for r in result]

            return _run_async(_query())

        result = benchmark(query_neighbors)
        assert isinstance(result, list)

    # -------------------------------------------------------------------
    # 4. Seed selection: causal roots
    # -------------------------------------------------------------------

    def test_seed_selection_causal(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Benchmark GET_SEED_CAUSAL_ROOTS for a session."""
        from context_graph.adapters.neo4j import queries as q

        session_id = self._session_ids[0]

        def query_seeds():
            async def _query():
                async with neo4j_driver.session() as session:
                    result = await session.run(
                        q.GET_SEED_CAUSAL_ROOTS,
                        {
                            "session_id": session_id,
                            "tenant_id": BENCHMARK_TENANT,
                            "seed_limit": 10,
                        },
                    )
                    return [r async for r in result]

            return _run_async(_query())

        result = benchmark(query_seeds)
        assert isinstance(result, list)

    # -------------------------------------------------------------------
    # 5. Seed selection: entity hubs
    # -------------------------------------------------------------------

    def test_seed_selection_entity_hub(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Benchmark GET_SEED_ENTITY_HUBS for a session."""
        from context_graph.adapters.neo4j import queries as q

        session_id = self._session_ids[0]

        def query_seeds():
            async def _query():
                async with neo4j_driver.session() as session:
                    result = await session.run(
                        q.GET_SEED_ENTITY_HUBS,
                        {
                            "session_id": session_id,
                            "tenant_id": BENCHMARK_TENANT,
                            "seed_limit": 10,
                        },
                    )
                    return [r async for r in result]

            return _run_async(_query())

        result = benchmark(query_seeds)
        assert isinstance(result, list)

    # -------------------------------------------------------------------
    # 6. Graph statistics
    # -------------------------------------------------------------------

    def test_get_graph_stats(self, benchmark, neo4j_driver: AsyncDriver) -> None:
        """Benchmark get_graph_stats maintenance query."""
        from context_graph.adapters.neo4j.maintenance import get_graph_stats

        def query_stats():
            return _run_async(
                get_graph_stats(
                    neo4j_driver,
                    database="neo4j",
                    tenant_id=BENCHMARK_TENANT,
                )
            )

        result = benchmark(query_stats)
        assert isinstance(result, dict)
        assert "total_nodes" in result
        assert result["total_nodes"] > 0
