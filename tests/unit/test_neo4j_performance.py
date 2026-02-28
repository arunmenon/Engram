"""Unit tests for Neo4j performance improvements (H10, H11, H12, H13).

Validates:
- H11: session_id index in ALL_INDEXES
- H10: Query timeout wiring from QuerySettings
- H12: Batch neighbor query replaces N+1 pattern
- H13: Neighbor limit in queries and settings
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.adapters.neo4j import queries

# ---------------------------------------------------------------------------
# H11 — Event.session_id index
# ---------------------------------------------------------------------------


class TestSessionIdIndex:
    """Tests for the session_id performance index."""

    def test_all_indexes_contains_session_id_index(self) -> None:
        assert queries.INDEX_EVENT_SESSION_ID in queries.ALL_INDEXES

    def test_session_id_index_is_create_if_not_exists(self) -> None:
        assert "IF NOT EXISTS" in queries.INDEX_EVENT_SESSION_ID

    def test_session_id_index_targets_event_session_id(self) -> None:
        assert "Event" in queries.INDEX_EVENT_SESSION_ID
        assert "session_id" in queries.INDEX_EVENT_SESSION_ID


# ---------------------------------------------------------------------------
# H12 — Batch neighbor query
# ---------------------------------------------------------------------------


class TestBatchNeighborQuery:
    """Tests for the batched neighbor traversal query."""

    def test_batch_query_has_limit(self) -> None:
        assert "LIMIT $neighbor_limit" in queries.GET_EVENT_NEIGHBORS_BATCH

    def test_batch_query_uses_unwind(self) -> None:
        assert "UNWIND $event_ids AS eid" in queries.GET_EVENT_NEIGHBORS_BATCH

    def test_batch_query_returns_seed_event_id(self) -> None:
        assert "seed_event_id" in queries.GET_EVENT_NEIGHBORS_BATCH

    def test_batch_query_returns_all_neighbor_fields(self) -> None:
        for field in [
            "rel_type",
            "rel_props",
            "neighbor_labels",
            "neighbor_props",
            "neighbor_event_id",
            "neighbor_entity_id",
            "neighbor_summary_id",
        ]:
            assert field in queries.GET_EVENT_NEIGHBORS_BATCH


# ---------------------------------------------------------------------------
# H13 — Neighbor limit on single-node query
# ---------------------------------------------------------------------------


class TestNeighborLimit:
    """Tests for the neighbor LIMIT clause."""

    def test_single_query_has_limit(self) -> None:
        assert "LIMIT $neighbor_limit" in queries.GET_EVENT_NEIGHBORS


# ---------------------------------------------------------------------------
# H10 + H13 — Store constructor settings propagation
# ---------------------------------------------------------------------------


class TestStoreSettings:
    """Tests for QuerySettings propagation to Neo4jGraphStore."""

    def _make_store(
        self,
        timeout_ms: int | None = None,
        neighbor_limit: int | None = None,
    ) -> object:
        """Create a Neo4jGraphStore with mocked driver."""
        from context_graph.settings import Neo4jSettings, QuerySettings

        neo4j_settings = Neo4jSettings()
        query_settings = None
        if timeout_ms is not None or neighbor_limit is not None:
            kwargs: dict[str, int] = {}
            if timeout_ms is not None:
                kwargs["default_timeout_ms"] = timeout_ms
            if neighbor_limit is not None:
                kwargs["default_neighbor_limit"] = neighbor_limit
            query_settings = QuerySettings(**kwargs)

        with patch("context_graph.adapters.neo4j.store.AsyncGraphDatabase") as mock_agd:
            mock_agd.driver.return_value = MagicMock()
            from context_graph.adapters.neo4j.store import Neo4jGraphStore

            return Neo4jGraphStore(
                neo4j_settings,
                query_settings=query_settings,
            )

    def test_default_timeout_without_query_settings(self) -> None:
        store = self._make_store()
        assert store._query_timeout_s == 5.0  # noqa: SLF001

    def test_timeout_from_query_settings(self) -> None:
        store = self._make_store(timeout_ms=10000)
        assert store._query_timeout_s == 10.0  # noqa: SLF001

    def test_timeout_from_custom_value(self) -> None:
        store = self._make_store(timeout_ms=3000)
        assert store._query_timeout_s == 3.0  # noqa: SLF001

    def test_default_neighbor_limit_without_query_settings(self) -> None:
        store = self._make_store()
        assert store._neighbor_limit == 50  # noqa: SLF001

    def test_neighbor_limit_from_settings(self) -> None:
        store = self._make_store(neighbor_limit=25)
        assert store._neighbor_limit == 25  # noqa: SLF001


# ---------------------------------------------------------------------------
# H10 — Timeout wiring on read queries
# ---------------------------------------------------------------------------


class _EmptyAsyncResult:
    """Async iterable that yields nothing — simulates an empty Neo4j result."""

    def __aiter__(self) -> _EmptyAsyncResult:
        return self

    async def __anext__(self) -> None:
        raise StopAsyncIteration

    async def single(self) -> None:
        return None


class TestTimeoutWiring:
    """Tests verifying timeout is passed to session.run() on read queries."""

    @pytest.fixture()
    def mock_store(self) -> object:
        """Create a store with mocked driver for inspecting session.run calls."""
        from context_graph.settings import Neo4jSettings, QuerySettings

        neo4j_settings = Neo4jSettings()
        query_settings = QuerySettings(default_timeout_ms=7000)

        with patch("context_graph.adapters.neo4j.store.AsyncGraphDatabase") as mock_agd:
            mock_driver = MagicMock()
            mock_agd.driver.return_value = mock_driver

            # Create a mock session that tracks run() calls
            mock_session = AsyncMock()
            mock_session.run.return_value = _EmptyAsyncResult()
            mock_session.execute_write = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_driver.session.return_value = mock_session

            from context_graph.adapters.neo4j.store import Neo4jGraphStore

            store = Neo4jGraphStore(
                neo4j_settings,
                query_settings=query_settings,
            )
            store._mock_session = mock_session  # type: ignore[attr-defined]
            return store

    @pytest.mark.asyncio()
    async def test_get_context_passes_timeout(self, mock_store: object) -> None:
        store = mock_store
        await store.get_context("test-session")  # type: ignore[union-attr]
        # Check at least one session.run call included timeout
        for call in store._mock_session.run.call_args_list:  # type: ignore[union-attr]
            if "GET_SESSION_EVENTS" in str(call) or "session_id" in str(call):
                assert call.kwargs.get("timeout") == 7.0
                return
        # If session events query found, verify timeout was set
        assert any(
            c.kwargs.get("timeout") == 7.0
            for c in store._mock_session.run.call_args_list  # type: ignore[union-attr]
        )

    @pytest.mark.asyncio()
    async def test_get_lineage_passes_timeout(self, mock_store: object) -> None:
        from context_graph.domain.models import LineageQuery

        store = mock_store
        query = LineageQuery(node_id="test-node")
        await store.get_lineage(query)  # type: ignore[union-attr]
        assert any(
            c.kwargs.get("timeout") == 7.0
            for c in store._mock_session.run.call_args_list  # type: ignore[union-attr]
        )

    @pytest.mark.asyncio()
    async def test_get_entity_passes_timeout(self, mock_store: object) -> None:
        store = mock_store
        await store.get_entity("test-entity")  # type: ignore[union-attr]
        assert any(
            c.kwargs.get("timeout") == 7.0
            for c in store._mock_session.run.call_args_list  # type: ignore[union-attr]
        )


# ---------------------------------------------------------------------------
# H11 — ensure_constraints runs ALL_INDEXES
# ---------------------------------------------------------------------------


class TestEnsureConstraintsRunsIndexes:
    """Test that ensure_constraints() creates both constraints and indexes."""

    @pytest.mark.asyncio()
    async def test_ensure_constraints_runs_index_queries(self) -> None:
        from context_graph.settings import Neo4jSettings

        neo4j_settings = Neo4jSettings()

        with patch("context_graph.adapters.neo4j.store.AsyncGraphDatabase") as mock_agd:
            mock_driver = MagicMock()
            mock_agd.driver.return_value = mock_driver

            mock_session = AsyncMock()
            mock_session.run = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_driver.session.return_value = mock_session

            from context_graph.adapters.neo4j.store import Neo4jGraphStore

            store = Neo4jGraphStore(neo4j_settings)
            await store.ensure_constraints()

            # Collect all query strings passed to session.run
            run_queries = [call.args[0] for call in mock_session.run.call_args_list]

            # Verify all constraints were run
            for constraint in queries.ALL_CONSTRAINTS:
                assert constraint in run_queries

            # Verify all indexes were run
            for index in queries.ALL_INDEXES:
                assert index in run_queries
