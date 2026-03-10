"""Unit tests for Neo4j graph compaction (Task 3).

Tests cover:
- compact_session_events: preserves recent events, excludes cross-referenced,
  deletes summarized, skips sessions below threshold
- compact_stale_sessions: dispatches to compact_session_events per session
- get_tenant_node_budget: returns correct structure and utilization
- NodeBudgetSettings: defaults are correct
- Consolidation worker compaction wiring
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_driver(query_results: dict[str, list[dict]]) -> AsyncMock:
    """Create a mock AsyncDriver that returns specified results per query prefix.

    ``query_results`` maps a substring of a Cypher query to the list of records
    that should be returned. Each record is a dict.
    """
    driver = AsyncMock()
    session_ctx = AsyncMock()
    session = AsyncMock()

    # Each time session.run() is called, look up the query in query_results
    async def _run(query: str, params: dict | None = None):
        result_mock = AsyncMock()
        records = []
        for key, recs in query_results.items():
            if key in query:
                records = recs
                break

        # For execute_write, we need a different approach
        record_mocks = []
        for rec in records:
            mock_rec = MagicMock()
            mock_rec.__getitem__ = lambda self, k, r=rec: r[k]
            mock_rec.get = lambda k, default=None, r=rec: r.get(k, default)
            record_mocks.append(mock_rec)

        # Make result async-iterable
        result_mock.__aiter__ = lambda self, rms=record_mocks: aiter_from(rms)
        result_mock.single = AsyncMock(return_value=record_mocks[0] if record_mocks else None)
        return result_mock

    session.run = _run

    # For execute_write: call the function with a mock tx
    async def _execute_write(fn, *args, **kwargs):
        tx = AsyncMock()
        tx.run = _run
        return await fn(tx)

    session.execute_write = _execute_write
    session.execute_read = _execute_write

    session_ctx.__aenter__ = AsyncMock(return_value=session)
    session_ctx.__aexit__ = AsyncMock(return_value=False)
    driver.session = MagicMock(return_value=session_ctx)

    return driver


async def aiter_from(items: list):
    for item in items:
        yield item


# ---------------------------------------------------------------------------
# compact_session_events
# ---------------------------------------------------------------------------


class TestCompactSessionEvents:
    """Tests for maintenance.compact_session_events()."""

    @pytest.mark.asyncio()
    async def test_skips_when_below_min_events(self):
        """Sessions with fewer than min_events should be skipped."""
        from context_graph.adapters.neo4j.maintenance import compact_session_events

        driver = _make_mock_driver(
            {
                "count(e)": [{"event_count": 10}],
            }
        )

        result = await compact_session_events(
            driver, "neo4j", "session-1", tenant_id="default", min_events=50
        )

        assert result == 0

    @pytest.mark.asyncio()
    async def test_preserves_recent_events(self):
        """Recent events should never be deleted even if summarized."""
        from context_graph.adapters.neo4j.maintenance import compact_session_events

        # 60 events total, 15 summarized, but 10 of those are recent
        summarized_ids = [f"evt-{i}" for i in range(15)]
        recent_ids = [f"evt-{i}" for i in range(10)]  # 10 most recent overlap with summarized

        driver = _make_mock_driver(
            {
                "count(e)": [{"event_count": 60}],
                "SUMMARIZES": [{"event_id": eid} for eid in summarized_ids],
                "ORDER BY e.occurred_at DESC": [{"event_id": eid} for eid in recent_ids],
                "other.session_id": [],  # no cross-referenced
                "DETACH DELETE": [{"deleted_count": 5}],
            }
        )

        result = await compact_session_events(
            driver, "neo4j", "session-1", tenant_id="default", min_events=50, keep_recent=10
        )

        # Only summarized events NOT in recent should be deleted: 15 - 10 = 5
        assert result == 5

    @pytest.mark.asyncio()
    async def test_excludes_cross_referenced_events(self):
        """Events referenced by entities in other sessions must not be deleted."""
        from context_graph.adapters.neo4j.maintenance import compact_session_events

        summarized_ids = [f"evt-{i}" for i in range(20)]
        recent_ids = [f"evt-{i}" for i in range(5)]
        cross_ref_ids = [f"evt-{i}" for i in range(5, 10)]  # 5 cross-referenced

        driver = _make_mock_driver(
            {
                "count(e)": [{"event_count": 100}],
                "SUMMARIZES": [{"event_id": eid} for eid in summarized_ids],
                "ORDER BY e.occurred_at DESC": [{"event_id": eid} for eid in recent_ids],
                "other.session_id": [{"event_id": eid} for eid in cross_ref_ids],
                "DETACH DELETE": [{"deleted_count": 10}],
            }
        )

        result = await compact_session_events(
            driver, "neo4j", "session-1", tenant_id="default", min_events=50, keep_recent=5
        )

        # Deletable = 20 summarized - 5 recent - 5 cross_ref = 10
        assert result == 10

    @pytest.mark.asyncio()
    async def test_deletes_summarized_events(self):
        """Summarized events not recent or cross-referenced should be deleted."""
        from context_graph.adapters.neo4j.maintenance import compact_session_events

        summarized_ids = [f"evt-{i}" for i in range(30)]
        recent_ids = [f"evt-{i}" for i in range(5)]

        driver = _make_mock_driver(
            {
                "count(e)": [{"event_count": 100}],
                "SUMMARIZES": [{"event_id": eid} for eid in summarized_ids],
                "ORDER BY e.occurred_at DESC": [{"event_id": eid} for eid in recent_ids],
                "other.session_id": [],  # no cross-referenced
                "DETACH DELETE": [{"deleted_count": 25}],
            }
        )

        result = await compact_session_events(
            driver, "neo4j", "session-1", tenant_id="default", min_events=50, keep_recent=5
        )

        # 30 summarized - 5 recent - 0 cross_ref = 25
        assert result == 25

    @pytest.mark.asyncio()
    async def test_returns_zero_when_no_summarized_events(self):
        """If no events have SUMMARIZES coverage, return 0."""
        from context_graph.adapters.neo4j.maintenance import compact_session_events

        driver = _make_mock_driver(
            {
                "count(e)": [{"event_count": 100}],
                "SUMMARIZES": [],
            }
        )

        result = await compact_session_events(
            driver, "neo4j", "session-1", tenant_id="default", min_events=50
        )

        assert result == 0

    @pytest.mark.asyncio()
    async def test_returns_zero_when_all_summarized_are_recent(self):
        """If all summarized events are also recent, nothing is deletable."""
        from context_graph.adapters.neo4j.maintenance import compact_session_events

        shared_ids = [f"evt-{i}" for i in range(5)]

        driver = _make_mock_driver(
            {
                "count(e)": [{"event_count": 100}],
                "SUMMARIZES": [{"event_id": eid} for eid in shared_ids],
                "ORDER BY e.occurred_at DESC": [{"event_id": eid} for eid in shared_ids],
                "other.session_id": [],
            }
        )

        result = await compact_session_events(
            driver, "neo4j", "session-1", tenant_id="default", min_events=50, keep_recent=10
        )

        assert result == 0


# ---------------------------------------------------------------------------
# get_tenant_node_budget
# ---------------------------------------------------------------------------


class TestGetTenantNodeBudget:
    """Tests for maintenance.get_tenant_node_budget()."""

    @pytest.mark.asyncio()
    async def test_returns_correct_structure(self):
        """Budget info should include total_nodes, by_label, budget, and utilization_pct."""
        from context_graph.adapters.neo4j.maintenance import get_tenant_node_budget

        driver = _make_mock_driver(
            {
                "labels(n)": [
                    {"label": "Event", "cnt": 5000},
                    {"label": "Entity", "cnt": 1000},
                    {"label": "Summary", "cnt": 200},
                ],
            }
        )

        result = await get_tenant_node_budget(
            driver, "neo4j", tenant_id="default", max_nodes=100_000
        )

        assert result["total_nodes"] == 6200
        assert result["by_label"]["Event"] == 5000
        assert result["by_label"]["Entity"] == 1000
        assert result["by_label"]["Summary"] == 200
        assert result["budget"] == 100_000
        assert result["utilization_pct"] == pytest.approx(6.2, abs=0.01)

    @pytest.mark.asyncio()
    async def test_utilization_at_full_budget(self):
        """Utilization should be 100% when total nodes equals budget."""
        from context_graph.adapters.neo4j.maintenance import get_tenant_node_budget

        driver = _make_mock_driver(
            {
                "labels(n)": [
                    {"label": "Event", "cnt": 80_000},
                    {"label": "Entity", "cnt": 20_000},
                ],
            }
        )

        result = await get_tenant_node_budget(
            driver, "neo4j", tenant_id="default", max_nodes=100_000
        )

        assert result["total_nodes"] == 100_000
        assert result["utilization_pct"] == pytest.approx(100.0)

    @pytest.mark.asyncio()
    async def test_empty_graph(self):
        """Empty graph should have 0% utilization."""
        from context_graph.adapters.neo4j.maintenance import get_tenant_node_budget

        driver = _make_mock_driver(
            {
                "labels(n)": [],
            }
        )

        result = await get_tenant_node_budget(
            driver, "neo4j", tenant_id="default", max_nodes=100_000
        )

        assert result["total_nodes"] == 0
        assert result["by_label"] == {}
        assert result["utilization_pct"] == 0.0


# ---------------------------------------------------------------------------
# compact_stale_sessions
# ---------------------------------------------------------------------------


class TestCompactStaleSessions:
    """Tests for maintenance.compact_stale_sessions()."""

    @pytest.mark.asyncio()
    async def test_calls_compact_for_each_stale_session(self):
        """Should call compact_session_events for each stale session found."""
        from context_graph.adapters.neo4j import maintenance

        with patch.object(
            maintenance, "compact_session_events", new_callable=AsyncMock
        ) as mock_compact:
            mock_compact.return_value = 20

            driver = _make_mock_driver(
                {
                    "RETURN sid AS session_id": [
                        {"session_id": "sess-1", "event_count": 100},
                        {"session_id": "sess-2", "event_count": 80},
                    ],
                }
            )

            result = await maintenance.compact_stale_sessions(
                driver, "neo4j", tenant_id="default", min_age_hours=168, batch_limit=10
            )

            assert mock_compact.call_count == 2
            # 20 events compacted per session * 2 sessions
            assert result == 40

    @pytest.mark.asyncio()
    async def test_returns_zero_when_no_stale_sessions(self):
        """No stale sessions should result in 0 compacted."""
        from context_graph.adapters.neo4j.maintenance import compact_stale_sessions

        driver = _make_mock_driver(
            {
                "RETURN sid AS session_id": [],
            }
        )

        result = await compact_stale_sessions(
            driver, "neo4j", tenant_id="default", min_age_hours=168
        )

        assert result == 0


# ---------------------------------------------------------------------------
# NodeBudgetSettings
# ---------------------------------------------------------------------------


class TestNodeBudgetSettings:
    """Tests for settings.NodeBudgetSettings defaults."""

    def test_defaults(self):
        """Default values should match documented specification."""
        from context_graph.settings import NodeBudgetSettings

        settings = NodeBudgetSettings()

        assert settings.max_nodes_per_tenant == 100_000
        assert settings.compaction_trigger_pct == 80.0
        assert settings.min_session_age_hours == 168
        assert settings.min_events_for_compaction == 50
        assert settings.keep_recent_events == 10

    def test_included_in_root_settings(self):
        """NodeBudgetSettings should be accessible from root Settings."""
        from context_graph.settings import NodeBudgetSettings, Settings

        settings = Settings()
        assert hasattr(settings, "node_budget")
        assert isinstance(settings.node_budget, NodeBudgetSettings)
        assert settings.node_budget.max_nodes_per_tenant == 100_000


# ---------------------------------------------------------------------------
# Consolidation worker compaction wiring
# ---------------------------------------------------------------------------


class TestConsolidationWorkerCompaction:
    """Test that consolidation worker calls compaction when budget is high."""

    @pytest.fixture()
    def mock_settings(self):
        settings = MagicMock()
        settings.redis.group_projection = "graph-projection"
        settings.redis.group_extraction = "session-extraction"
        settings.redis.group_enrichment = "enrichment"
        settings.redis.group_consolidation = "consolidation"
        settings.redis.global_stream = "events:__global__"
        settings.redis.block_timeout_ms = 100
        settings.redis.hot_window_days = 7
        settings.redis.retention_ceiling_days = 90
        settings.redis.event_key_prefix = "evt:"
        settings.redis.dedup_set = "dedup:events"
        settings.redis.session_stream_retention_hours = 168
        settings.neo4j.database = "neo4j"
        settings.decay.reconsolidation_interval_hours = 6
        settings.decay.reflection_threshold = 150
        settings.retention.warm_min_similarity_score = 0.7
        settings.retention.hot_hours = 24
        settings.retention.warm_hours = 168
        settings.retention.cold_hours = 720
        settings.retention.cold_min_importance = 5
        settings.retention.cold_min_access_count = 3
        settings.retention.orphan_cleanup_batch_size = 500
        settings.consumer.max_retries = 5
        settings.consumer.claim_idle_ms = 300_000
        settings.consumer.claim_batch_size = 100
        settings.consumer.dlq_stream_suffix = ":dlq"
        settings.node_budget.max_nodes_per_tenant = 100_000
        settings.node_budget.compaction_trigger_pct = 80.0
        settings.node_budget.min_session_age_hours = 168
        settings.node_budget.min_events_for_compaction = 50
        settings.node_budget.keep_recent_events = 10
        return settings

    @pytest.mark.asyncio()
    async def test_compaction_triggered_when_utilization_high(self, mock_settings):
        """Compaction should run when node utilization exceeds trigger percentage."""
        from context_graph.worker.consolidation import ConsolidationConsumer

        mock_redis = AsyncMock()
        mock_gm = AsyncMock()
        mock_retention = AsyncMock()

        # Graph maintenance returns high utilization counts
        mock_gm.get_session_event_counts.return_value = {}
        mock_gm.run_session_query.side_effect = [
            # First call: GET_TENANT_NODE_COUNTS (high utilization = 85%)
            [{"label": "Event", "cnt": 85_000}],
            # Second call: GET_STALE_SESSIONS
            [{"session_id": "sess-old", "event_count": 60}],
            # Third call: COUNT_SESSION_EVENTS for sess-old
            [{"event_count": 60}],
            # Fourth call: GET_SUMMARIZED_EVENT_IDS
            [{"event_id": f"evt-{i}"} for i in range(30)],
            # Fifth call: GET_RECENT_EVENT_IDS
            [{"event_id": f"evt-{i}"} for i in range(10)],
            # Sixth call: GET_CROSS_REFERENCED_EVENT_IDS
            [],
            # Seventh call: DETACH_DELETE_EVENTS_BY_IDS
            [{"deleted_count": 20}],
        ]

        consumer = ConsolidationConsumer(
            redis_client=mock_redis,
            graph_maintenance=mock_gm,
            retention_manager=mock_retention,
            settings=mock_settings,
        )

        await consumer._run_graph_compaction()

        # Verify run_session_query was called (at least for node counts and stale sessions)
        assert mock_gm.run_session_query.call_count >= 2

    @pytest.mark.asyncio()
    async def test_compaction_skipped_when_utilization_low(self, mock_settings):
        """Compaction should not run when utilization is below trigger percentage."""
        from context_graph.worker.consolidation import ConsolidationConsumer

        mock_redis = AsyncMock()
        mock_gm = AsyncMock()
        mock_retention = AsyncMock()

        # Low utilization: 10% of budget
        mock_gm.get_session_event_counts.return_value = {}
        mock_gm.run_session_query.return_value = [
            {"label": "Event", "cnt": 10_000},
        ]

        consumer = ConsolidationConsumer(
            redis_client=mock_redis,
            graph_maintenance=mock_gm,
            retention_manager=mock_retention,
            settings=mock_settings,
        )

        await consumer._run_graph_compaction()

        # Only 1 call for node counts; no further calls for stale sessions
        assert mock_gm.run_session_query.call_count == 1
