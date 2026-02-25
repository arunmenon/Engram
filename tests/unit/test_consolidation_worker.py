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
def mock_neo4j():
    return AsyncMock()


@pytest.fixture()
def consumer(mock_redis, mock_neo4j, mock_settings):
    return ConsolidationConsumer(
        redis_client=mock_redis,
        neo4j_driver=mock_neo4j,
        settings=mock_settings,
    )


@pytest.fixture()
def consumer_with_archive(mock_redis, mock_neo4j, mock_settings):
    archive_store = AsyncMock()
    return ConsolidationConsumer(
        redis_client=mock_redis,
        neo4j_driver=mock_neo4j,
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
    async def test_trim_calls_dedup_cleanup(self, consumer, mock_settings):
        """_trim_redis should call cleanup_dedup_set."""
        with (
            patch(
                "context_graph.worker.consolidation.trim_stream",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.delete_expired_events",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=5,
            ) as mock_dedup,
            patch(
                "context_graph.worker.consolidation.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            await consumer._trim_redis()

        mock_dedup.assert_called_once_with(
            redis_client=consumer._redis,
            dedup_key=mock_settings.redis.dedup_set,
            retention_ceiling_days=mock_settings.redis.retention_ceiling_days,
        )

    @pytest.mark.asyncio()
    async def test_trim_calls_session_cleanup(self, consumer, mock_settings):
        """_trim_redis should call cleanup_session_streams."""
        with (
            patch(
                "context_graph.worker.consolidation.trim_stream",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.delete_expired_events",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=3,
            ) as mock_session,
        ):
            await consumer._trim_redis()

        mock_session.assert_called_once_with(
            redis_client=consumer._redis,
            prefix="events:session:",
            max_age_hours=mock_settings.redis.session_stream_retention_hours,
        )

    @pytest.mark.asyncio()
    async def test_trim_uses_archive_store_when_available(
        self, consumer_with_archive, mock_settings
    ):
        """When archive_store is set, _trim_redis should call archive_and_delete_expired_events."""
        with (
            patch(
                "context_graph.worker.consolidation.trim_stream",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.archive_and_delete_expired_events",
                new_callable=AsyncMock,
                return_value=(10, 10),
            ) as mock_archive,
            patch(
                "context_graph.worker.consolidation.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            await consumer_with_archive._trim_redis()

        mock_archive.assert_called_once_with(
            redis_client=consumer_with_archive._redis,
            key_prefix=mock_settings.redis.event_key_prefix,
            max_age_days=mock_settings.redis.retention_ceiling_days,
            archive_store=consumer_with_archive._archive_store,
        )

    @pytest.mark.asyncio()
    async def test_trim_uses_plain_delete_when_no_archive(self, consumer, mock_settings):
        """When no archive_store, _trim_redis should call delete_expired_events."""
        with (
            patch(
                "context_graph.worker.consolidation.trim_stream",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.delete_expired_events",
                new_callable=AsyncMock,
                return_value=7,
            ) as mock_delete,
            patch(
                "context_graph.worker.consolidation.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            await consumer._trim_redis()

        mock_delete.assert_called_once_with(
            redis_client=consumer._redis,
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

    Embedding zombie cleanup is no longer needed — Neo4j DETACH DELETE
    auto-removes embedding properties when the node is deleted.
    """

    @pytest.mark.asyncio()
    async def test_forgetting_calls_orphan_cleanup(self, consumer, mock_settings):
        """_run_forgetting should call delete_orphan_nodes after archive deletion."""
        with (
            patch(
                "context_graph.worker.consolidation.maintenance.get_session_event_counts",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "context_graph.worker.consolidation.maintenance.delete_edges_by_type_and_age",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.maintenance.delete_cold_events",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.maintenance.get_archive_event_ids",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "context_graph.worker.consolidation.maintenance.delete_orphan_nodes",
                new_callable=AsyncMock,
                return_value=(
                    {
                        "Entity": 2,
                        "Preference": 0,
                        "Skill": 0,
                        "Workflow": 0,
                        "BehavioralPattern": 0,
                    },
                    ["ent-1", "ent-2"],
                ),
            ) as mock_orphan,
        ):
            await consumer._run_forgetting()

        mock_orphan.assert_called_once_with(
            driver=consumer._neo4j_driver,
            database=consumer._neo4j_database,
            batch_size=mock_settings.retention.orphan_cleanup_batch_size,
        )

    @pytest.mark.asyncio()
    async def test_forgetting_no_error_with_empty_orphans(self, consumer, mock_settings):
        """No error when no orphan entities are deleted."""
        with (
            patch(
                "context_graph.worker.consolidation.maintenance.get_session_event_counts",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "context_graph.worker.consolidation.maintenance.delete_edges_by_type_and_age",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.maintenance.delete_cold_events",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.worker.consolidation.maintenance.get_archive_event_ids",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "context_graph.worker.consolidation.maintenance.delete_orphan_nodes",
                new_callable=AsyncMock,
                return_value=({"Entity": 0}, []),
            ),
        ):
            await consumer._run_forgetting()
