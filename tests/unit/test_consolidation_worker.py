"""Unit tests for worker/consolidation.py — Consolidation worker timer + wiring."""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.worker.consolidation import ConsolidationConsumer


@pytest.fixture()
def mock_settings():
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
    return settings


@pytest.fixture()
def mock_redis():
    return AsyncMock()


@pytest.fixture()
def mock_graph_maintenance():
    return AsyncMock()


@pytest.fixture()
def mock_retention_manager():
    return AsyncMock()


@pytest.fixture()
def consumer(mock_redis, mock_graph_maintenance, mock_retention_manager, mock_settings):
    return ConsolidationConsumer(
        redis_client=mock_redis,
        graph_maintenance=mock_graph_maintenance,
        retention_manager=mock_retention_manager,
        settings=mock_settings,
    )


@pytest.fixture()
def consumer_with_llm(mock_redis, mock_graph_maintenance, mock_retention_manager, mock_settings):
    llm_client = AsyncMock()
    return ConsolidationConsumer(
        redis_client=mock_redis,
        graph_maintenance=mock_graph_maintenance,
        retention_manager=mock_retention_manager,
        settings=mock_settings,
        llm_client=llm_client,
    )


@pytest.fixture()
def consumer_with_archive(
    mock_redis, mock_graph_maintenance, mock_retention_manager, mock_settings
):
    archive_store = AsyncMock()
    return ConsolidationConsumer(
        redis_client=mock_redis,
        graph_maintenance=mock_graph_maintenance,
        retention_manager=mock_retention_manager,
        settings=mock_settings,
        archive_store=archive_store,
    )


# ── TestConsolidationTimerLoop ──────────────────────────────────────────


class TestConsolidationTimerLoop:
    """Tests for the asyncio timer loop that self-triggers consolidation."""

    @pytest.mark.asyncio()
    async def test_timer_creates_task_on_run(self, consumer):
        """run() should create a timer task alongside the base consumer loop."""
        created_tasks = []
        original_create_task = asyncio.create_task

        def capture_create_task(coro, **kwargs):
            task = original_create_task(coro, **kwargs)
            created_tasks.append(task)
            return task

        # Make super().run() return immediately to avoid infinite XREADGROUP loop
        with (
            patch.object(type(consumer).__bases__[0], "run", new_callable=AsyncMock) as mock_run,
            patch("asyncio.create_task", side_effect=capture_create_task),
        ):
            mock_run.return_value = None
            await consumer.run()

        # At least one task was created (the timer loop)
        assert len(created_tasks) >= 1
        # Clean up
        for task in created_tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task

    @pytest.mark.asyncio()
    async def test_timer_respects_interval(self, consumer, mock_settings):
        """Timer should sleep for reconsolidation_interval_hours * 3600 seconds."""
        mock_settings.decay.reconsolidation_interval_hours = 6
        expected_interval = 6 * 3600

        sleep_calls = []

        async def fake_sleep(seconds):
            sleep_calls.append(seconds)
            # Stop the consumer after first sleep to exit loop
            consumer._stopped = True

        with patch("asyncio.sleep", side_effect=fake_sleep):
            await consumer._timer_loop()

        assert len(sleep_calls) >= 1
        assert sleep_calls[0] == expected_interval

    @pytest.mark.asyncio()
    async def test_timer_stops_on_consumer_stop(self, consumer):
        """Timer loop should exit when _stopped is True."""
        consumer._stopped = True
        # Should return immediately without sleeping
        await consumer._timer_loop()
        # If we get here, the loop properly checked _stopped before sleeping

    @pytest.mark.asyncio()
    async def test_timer_survives_cycle_failure(self, consumer):
        """Timer loop should continue after an exception in the consolidation cycle.

        _run_consolidation_cycle_guarded catches exceptions internally, so the
        timer loop keeps running even when the inner cycle raises.
        """
        call_count = 0

        async def fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                consumer._stopped = True

        with (
            patch("asyncio.sleep", side_effect=fake_sleep),
            patch.object(
                consumer,
                "_run_consolidation_cycle",
                side_effect=Exception("test failure"),
            ),
        ):
            # _run_consolidation_cycle raises, but _run_consolidation_cycle_guarded
            # catches it. The timer loop should continue to the next sleep.
            await consumer._timer_loop()

        # Timer looped at least twice (slept twice before stopping)
        assert call_count >= 2


# ── TestTrimRedisWiring ─────────────────────────────────────────────────


class TestTrimRedisWiring:
    """Tests for _trim_redis method's calls to trimmer functions."""

    @pytest.mark.asyncio()
    async def test_trim_calls_dedup_cleanup(self, consumer, mock_retention_manager, mock_settings):
        """_trim_redis should call cleanup_dedup_set."""
        mock_retention_manager.trim_stream.return_value = 0
        mock_retention_manager.delete_expired_events.return_value = 0
        mock_retention_manager.cleanup_dedup_set.return_value = 5
        mock_retention_manager.cleanup_session_streams.return_value = 0

        await consumer._trim_redis()

        mock_retention_manager.cleanup_dedup_set.assert_called_once_with(
            dedup_key=mock_settings.redis.dedup_set,
            retention_ceiling_days=mock_settings.redis.retention_ceiling_days,
        )

    @pytest.mark.asyncio()
    async def test_trim_passes_consumer_groups_to_trim_stream(
        self, consumer, mock_retention_manager, mock_settings
    ):
        """_trim_redis should pass consumer group names to trim_stream for PEL-safe trimming."""
        mock_retention_manager.trim_stream.return_value = 0
        mock_retention_manager.delete_expired_events.return_value = 0
        mock_retention_manager.cleanup_dedup_set.return_value = 0
        mock_retention_manager.cleanup_session_streams.return_value = 0

        await consumer._trim_redis()

        mock_retention_manager.trim_stream.assert_called_once()
        call_kwargs = mock_retention_manager.trim_stream.call_args.kwargs
        assert "consumer_groups" in call_kwargs
        groups = call_kwargs["consumer_groups"]
        assert "graph-projection" in groups
        assert "session-extraction" in groups
        assert "enrichment" in groups
        assert "consolidation" in groups

    @pytest.mark.asyncio()
    async def test_trim_calls_session_cleanup(
        self, consumer, mock_retention_manager, mock_settings
    ):
        """_trim_redis should call cleanup_session_streams."""
        mock_retention_manager.trim_stream.return_value = 0
        mock_retention_manager.delete_expired_events.return_value = 0
        mock_retention_manager.cleanup_dedup_set.return_value = 0
        mock_retention_manager.cleanup_session_streams.return_value = 3

        await consumer._trim_redis()

        mock_retention_manager.cleanup_session_streams.assert_called_once_with(
            prefix="events:session:",
            max_age_hours=mock_settings.redis.session_stream_retention_hours,
        )

    @pytest.mark.asyncio()
    async def test_trim_uses_archive_store_when_available(
        self, consumer_with_archive, mock_retention_manager, mock_settings
    ):
        """When archive_store is set, _trim_redis should call archive_and_delete_expired_events."""
        mock_retention_manager.trim_stream.return_value = 0
        mock_retention_manager.archive_and_delete_expired_events.return_value = (10, 10)
        mock_retention_manager.cleanup_dedup_set.return_value = 0
        mock_retention_manager.cleanup_session_streams.return_value = 0

        await consumer_with_archive._trim_redis()

        mock_retention_manager.archive_and_delete_expired_events.assert_called_once_with(
            key_prefix=mock_settings.redis.event_key_prefix,
            max_age_days=mock_settings.redis.retention_ceiling_days,
            archive_store=consumer_with_archive._archive_store,
        )

    @pytest.mark.asyncio()
    async def test_trim_uses_plain_delete_when_no_archive(
        self, consumer, mock_retention_manager, mock_settings
    ):
        """When no archive_store, _trim_redis should call delete_expired_events."""
        mock_retention_manager.trim_stream.return_value = 0
        mock_retention_manager.delete_expired_events.return_value = 7
        mock_retention_manager.cleanup_dedup_set.return_value = 0
        mock_retention_manager.cleanup_session_streams.return_value = 0

        await consumer._trim_redis()

        mock_retention_manager.delete_expired_events.assert_called_once_with(
            key_prefix=mock_settings.redis.event_key_prefix,
            max_age_days=mock_settings.redis.retention_ceiling_days,
        )


# ── TestConcurrencyGuard ────────────────────────────────────────────────


class TestConcurrencyGuard:
    """Tests for the asyncio.Lock concurrency guard on consolidation cycles."""

    @pytest.mark.asyncio()
    async def test_lock_prevents_concurrent_cycles(self, consumer):
        """Second call to _run_consolidation_cycle_guarded should be skipped when lock is held."""
        cycle_entered = asyncio.Event()
        cycle_release = asyncio.Event()

        async def slow_cycle():
            cycle_entered.set()
            await cycle_release.wait()

        with patch.object(consumer, "_run_consolidation_cycle", side_effect=slow_cycle):
            # Start first cycle (will block on cycle_release)
            task1 = asyncio.create_task(consumer._run_consolidation_cycle_guarded(source="first"))
            await cycle_entered.wait()

            # Second call while first is running — should be skipped
            await consumer._run_consolidation_cycle_guarded(source="second")

            # Release the first cycle
            cycle_release.set()
            await task1

        # First cycle completed; second was skipped (no error, just a warning log)

    @pytest.mark.asyncio()
    async def test_process_message_uses_guarded_cycle(self, consumer):
        """process_message for trigger calls _run_consolidation_cycle_guarded."""
        with patch.object(
            consumer,
            "_run_consolidation_cycle_guarded",
            new_callable=AsyncMock,
        ) as mock_guarded:
            await consumer.process_message(
                entry_id="1234-0",
                data={"message_type": "consolidation_trigger"},
            )

        mock_guarded.assert_called_once_with(source="stream")

    @pytest.mark.asyncio()
    async def test_process_message_ignores_non_trigger(self, consumer):
        """process_message should skip messages that are not consolidation_trigger."""
        with patch.object(
            consumer,
            "_run_consolidation_cycle_guarded",
            new_callable=AsyncMock,
        ) as mock_guarded:
            await consumer.process_message(
                entry_id="1234-0",
                data={"message_type": "event", "event_id": "abc"},
            )

        mock_guarded.assert_not_called()


# ── TestOrphanCleanup ─────────────────────────────────────────────────


class TestOrphanCleanup:
    """Tests for ADR-0014 Amendment orphan cleanup wiring.

    Embedding zombie cleanup is no longer needed -- Neo4j DETACH DELETE
    auto-removes embedding properties when the node is deleted.
    """

    @pytest.mark.asyncio()
    async def test_forgetting_calls_orphan_cleanup(self, consumer, mock_settings):
        """_run_forgetting should call delete_orphan_nodes after archive deletion."""
        gm = consumer._graph_maintenance
        gm.get_session_event_counts.return_value = {}
        gm.delete_edges_by_type_and_age.return_value = 0
        gm.delete_cold_events.return_value = 0
        gm.get_archive_event_ids.return_value = []
        gm.delete_orphan_nodes.return_value = (
            {
                "Entity": 2,
                "Preference": 0,
                "Skill": 0,
                "Workflow": 0,
                "BehavioralPattern": 0,
            },
            ["ent-1", "ent-2"],
        )

        await consumer._run_forgetting()

        gm.delete_orphan_nodes.assert_called_once_with(
            batch_size=mock_settings.retention.orphan_cleanup_batch_size,
        )

    @pytest.mark.asyncio()
    async def test_forgetting_no_error_with_empty_orphans(self, consumer, mock_settings):
        """No error when no orphan entities are deleted."""
        gm = consumer._graph_maintenance
        gm.get_session_event_counts.return_value = {}
        gm.delete_edges_by_type_and_age.return_value = 0
        gm.delete_cold_events.return_value = 0
        gm.get_archive_event_ids.return_value = []
        gm.delete_orphan_nodes.return_value = ({"Entity": 0}, [])

        await consumer._run_forgetting()


# ── TestLLMConsolidationWiring ────────────────────────────────────────


class TestLLMConsolidationWiring:
    """Tests for LLM-powered summary generation in consolidation."""

    @pytest.mark.asyncio()
    async def test_llm_client_called_for_episode_summary(self, consumer_with_llm, mock_settings):
        """When llm_client is provided, generate_text is called for each episode."""
        gm = consumer_with_llm._graph_maintenance
        llm = consumer_with_llm._llm_client

        llm.generate_text.return_value = "Agent searched files and found results."

        # Simulate session events: 2 events in 1 episode
        gm.run_session_query.return_value = [
            {
                "e": {
                    "event_id": "evt-1",
                    "occurred_at": "2025-01-01T12:00:00+00:00",
                    "event_type": "tool.execute",
                }
            },
            {
                "e": {
                    "event_id": "evt-2",
                    "occurred_at": "2025-01-01T12:01:00+00:00",
                    "event_type": "agent.invoke",
                }
            },
        ]
        gm.write_summary_with_edges.return_value = None

        await consumer_with_llm._consolidate_session("sess-1", 2)

        # generate_text called for episode + session summaries
        assert llm.generate_text.call_count == 2
        # Summaries should use LLM text
        calls = gm.write_summary_with_edges.call_args_list
        for call in calls:
            assert call.kwargs["content"] == "Agent searched files and found results."

    @pytest.mark.asyncio()
    async def test_fallback_when_llm_returns_none(self, consumer_with_llm, mock_settings):
        """When LLM returns None, fall back to template summary."""
        gm = consumer_with_llm._graph_maintenance
        llm = consumer_with_llm._llm_client

        llm.generate_text.return_value = None

        gm.run_session_query.return_value = [
            {
                "e": {
                    "event_id": "evt-1",
                    "occurred_at": "2025-01-01T12:00:00+00:00",
                    "event_type": "tool.execute",
                }
            },
        ]
        gm.write_summary_with_edges.return_value = None

        await consumer_with_llm._consolidate_session("sess-1", 1)

        # Should still write summaries, using template content
        calls = gm.write_summary_with_edges.call_args_list
        for call in calls:
            assert "1 events" in call.kwargs["content"]

    @pytest.mark.asyncio()
    async def test_no_llm_client_uses_template(self, consumer, mock_settings):
        """When no llm_client, episode summaries use deterministic template."""
        gm = consumer._graph_maintenance

        gm.run_session_query.return_value = [
            {
                "e": {
                    "event_id": "evt-1",
                    "occurred_at": "2025-01-01T12:00:00+00:00",
                    "event_type": "tool.execute",
                }
            },
        ]
        gm.write_summary_with_edges.return_value = None

        await consumer._consolidate_session("sess-1", 1)

        calls = gm.write_summary_with_edges.call_args_list
        for call in calls:
            assert "1 events" in call.kwargs["content"]
