"""Unit tests for BaseConsumer resilience features (H4 + H5).

Tests XAUTOCLAIM orphaned message recovery, dead-letter queue, delivery
count checking, and the integrated run() flow with these features.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from context_graph.worker.consumer import BaseConsumer

# ---------------------------------------------------------------------------
# Concrete subclass for testing (BaseConsumer.process_message is abstract)
# ---------------------------------------------------------------------------


class StubConsumer(BaseConsumer):
    """Concrete consumer that records processed messages."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed: list[tuple[str, dict[str, str]]] = []

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        self.processed.append((entry_id, data))


# =========================================================================
# H4: XAUTOCLAIM for orphaned PEL messages
# =========================================================================


class TestClaimOrphanedMessages:
    """H4: XAUTOCLAIM for orphaned PEL messages."""

    @pytest.mark.asyncio()
    async def test_claim_orphaned_calls_xautoclaim(self):
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [], [])
        consumer = StubConsumer(
            redis,
            "grp",
            "c1",
            "stream:test",
            claim_idle_ms=300_000,
            claim_batch_size=100,
        )
        await consumer._claim_orphaned_messages()
        redis.xautoclaim.assert_called_once_with(
            name="stream:test",
            groupname="grp",
            consumername="c1",
            min_idle_time=300_000,
            start_id="0-0",
            count=100,
        )

    @pytest.mark.asyncio()
    async def test_claim_orphaned_returns_count(self):
        redis = AsyncMock()
        # First call returns 3 entries with next_start_id for pagination
        # Second call returns empty (done)
        redis.xautoclaim.side_effect = [
            (b"1234-5", [(b"1-0", {}), (b"2-0", {}), (b"3-0", {})], []),
            (b"0-0", [], []),
        ]
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        count = await consumer._claim_orphaned_messages()
        assert count == 3

    @pytest.mark.asyncio()
    async def test_claim_orphaned_paginates_until_zero(self):
        redis = AsyncMock()
        redis.xautoclaim.side_effect = [
            (b"100-0", [(b"1-0", {})], []),
            (b"200-0", [(b"2-0", {})], []),
            (b"0-0", [], []),
        ]
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        count = await consumer._claim_orphaned_messages()
        assert count == 2
        assert redis.xautoclaim.call_count == 3

    @pytest.mark.asyncio()
    async def test_claim_orphaned_no_messages_returns_zero(self):
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [], [])
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        count = await consumer._claim_orphaned_messages()
        assert count == 0

    @pytest.mark.asyncio()
    async def test_claim_orphaned_respects_stopped_flag(self):
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"999-0", [(b"1-0", {})], [])
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        consumer._stopped = True
        count = await consumer._claim_orphaned_messages()
        assert count == 0  # loop never entered

    @pytest.mark.asyncio()
    async def test_claim_orphaned_stops_when_next_id_is_zero(self):
        """Even with claimed entries, stop if next_start_id is 0-0."""
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [(b"1-0", {}), (b"2-0", {})], [])
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        count = await consumer._claim_orphaned_messages()
        assert count == 2
        assert redis.xautoclaim.call_count == 1


# =========================================================================
# H5: Dead-letter queue
# =========================================================================


class TestDeadLetterQueue:
    """H5: Dead-letter queue for permanently failing messages."""

    @pytest.mark.asyncio()
    async def test_dead_letter_writes_to_dlq_stream(self):
        redis = AsyncMock()
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        await consumer._dead_letter_message("123-0", {"event_id": "abc"}, 6)
        redis.xadd.assert_called_once()
        call_args = redis.xadd.call_args
        assert call_args[0][0] == "stream:test:dlq"  # DLQ stream key
        dlq_data = call_args[0][1]
        assert dlq_data["original_entry_id"] == "123-0"
        assert dlq_data["event_id"] == "abc"

    @pytest.mark.asyncio()
    async def test_dead_letter_acks_source(self):
        redis = AsyncMock()
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        await consumer._dead_letter_message("123-0", {}, 6)
        redis.xack.assert_called_once_with("stream:test", "grp", "123-0")

    @pytest.mark.asyncio()
    async def test_dead_letter_includes_metadata(self):
        redis = AsyncMock()
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        await consumer._dead_letter_message("123-0", {"event_id": "xyz"}, 7)
        dlq_data = redis.xadd.call_args[0][1]
        assert dlq_data["original_stream"] == "stream:test"
        assert dlq_data["original_entry_id"] == "123-0"
        assert dlq_data["group"] == "grp"
        assert dlq_data["consumer"] == "c1"
        assert dlq_data["delivery_count"] == "7"

    @pytest.mark.asyncio()
    async def test_dlq_stream_key_derived_correctly(self):
        consumer = StubConsumer(AsyncMock(), "grp", "c1", "events:__global__")
        assert consumer._dlq_stream_key == "events:__global__:dlq"

    @pytest.mark.asyncio()
    async def test_custom_dlq_suffix(self):
        consumer = StubConsumer(
            AsyncMock(),
            "grp",
            "c1",
            "events:__global__",
            dlq_stream_suffix=".dead",
        )
        assert consumer._dlq_stream_key == "events:__global__.dead"


# =========================================================================
# H5: Delivery count retrieval
# =========================================================================


class TestGetDeliveryCounts:
    """H5: Delivery count retrieval from XPENDING."""

    @pytest.mark.asyncio()
    async def test_get_delivery_counts_returns_dict(self):
        redis = AsyncMock()
        redis.xpending_range.return_value = [
            {"message_id": b"100-0", "times_delivered": 3},
            {"message_id": b"200-0", "times_delivered": 1},
        ]
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        counts = await consumer._get_delivery_counts()
        assert counts == {"100-0": 3, "200-0": 1}

    @pytest.mark.asyncio()
    async def test_get_delivery_counts_empty_pel(self):
        redis = AsyncMock()
        redis.xpending_range.return_value = []
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        counts = await consumer._get_delivery_counts()
        assert counts == {}

    @pytest.mark.asyncio()
    async def test_get_delivery_counts_calls_xpending_range(self):
        redis = AsyncMock()
        redis.xpending_range.return_value = []
        consumer = StubConsumer(redis, "grp", "c1", "stream:test", batch_size=20)
        await consumer._get_delivery_counts()
        redis.xpending_range.assert_called_once_with(
            name="stream:test",
            groupname="grp",
            min="-",
            max="+",
            count=200,  # batch_size * 10
            consumername="c1",
        )


# =========================================================================
# Integration: run() flow with H4 + H5
# =========================================================================


class TestRunFlowIntegration:
    """Test the full run() flow with H4 + H5 integrated."""

    @pytest.mark.asyncio()
    async def test_run_calls_claim_before_pel_drain(self):
        """Verifies run() calls _claim_orphaned_messages after ensure_group."""
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [], [])
        redis.xpending_range.return_value = []
        redis.xreadgroup.return_value = []

        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        consumer._stopped = True  # stop after PEL drain

        with patch.object(
            consumer,
            "_claim_orphaned_messages",
            wraps=consumer._claim_orphaned_messages,
        ) as mock_claim:
            await consumer.run()
            mock_claim.assert_called_once()

    @pytest.mark.asyncio()
    async def test_run_dead_letters_high_delivery_count(self):
        """Message with delivery_count > max_retries gets dead-lettered."""
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [], [])
        redis.xpending_range.return_value = [
            {"message_id": b"100-0", "times_delivered": 6},
        ]

        class FailConsumer(BaseConsumer):
            async def process_message(self, entry_id, data):
                raise AssertionError("Should not be called for dead-lettered msg")

        consumer = FailConsumer(redis, "grp", "c1", "stream:test", max_retries=5)

        # Use side_effect to stop consumer after PEL drain returns data
        call_count = 0

        async def _xreadgroup_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [(b"stream", [(b"100-0", {b"event_id": b"abc"})])]
            # Second call: empty PEL -> drain exits, then stop before main loop
            consumer._stopped = True
            return []

        redis.xreadgroup.side_effect = _xreadgroup_side_effect

        await consumer.run()

        # Verify dead-letter was written
        redis.xadd.assert_called_once()
        assert redis.xadd.call_args[0][0] == "stream:test:dlq"
        # Verify ACK from source (via _dead_letter_message)
        redis.xack.assert_called()

    @pytest.mark.asyncio()
    async def test_run_processes_normal_delivery_count(self):
        """Message with delivery_count <= max_retries is processed normally."""
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [], [])
        redis.xpending_range.return_value = [
            {"message_id": b"100-0", "times_delivered": 2},
        ]

        consumer = StubConsumer(redis, "grp", "c1", "stream:test", max_retries=5)

        call_count = 0

        async def _xreadgroup_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [(b"stream", [(b"100-0", {b"event_id": b"abc"})])]
            consumer._stopped = True
            return []

        redis.xreadgroup.side_effect = _xreadgroup_side_effect

        await consumer.run()

        # Message should have been processed, not dead-lettered
        assert len(consumer.processed) == 1
        assert consumer.processed[0][0] == "100-0"
        # No DLQ write
        redis.xadd.assert_not_called()

    @pytest.mark.asyncio()
    async def test_run_delivery_count_default(self):
        """Message not in delivery_counts dict gets default count of 1."""
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [], [])
        redis.xpending_range.return_value = []

        consumer = StubConsumer(redis, "grp", "c1", "stream:test", max_retries=5)

        call_count = 0

        async def _xreadgroup_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [(b"stream", [(b"100-0", {b"event_id": b"abc"})])]
            consumer._stopped = True
            return []

        redis.xreadgroup.side_effect = _xreadgroup_side_effect

        await consumer.run()

        # Should be processed (default count=1, which is <= 5)
        assert len(consumer.processed) == 1

    @pytest.mark.asyncio()
    async def test_max_retries_configurable(self):
        """Setting max_retries=2 causes dead-lettering at 3 deliveries."""
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [], [])
        redis.xpending_range.return_value = [
            {"message_id": b"100-0", "times_delivered": 3},
        ]

        consumer = StubConsumer(redis, "grp", "c1", "stream:test", max_retries=2)

        call_count = 0

        async def _xreadgroup_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [(b"stream", [(b"100-0", {b"event_id": b"abc"})])]
            consumer._stopped = True
            return []

        redis.xreadgroup.side_effect = _xreadgroup_side_effect

        await consumer.run()

        # Should be dead-lettered (3 > 2)
        assert len(consumer.processed) == 0
        redis.xadd.assert_called_once()


# =========================================================================
# Settings tests
# =========================================================================


class TestConsumerSettings:
    """Test ConsumerSettings defaults and env overrides."""

    def test_consumer_settings_defaults(self):
        from context_graph.settings import ConsumerSettings

        settings = ConsumerSettings()
        assert settings.claim_idle_ms == 300_000
        assert settings.claim_batch_size == 100
        assert settings.max_retries == 5
        assert settings.dlq_stream_suffix == ":dlq"

    def test_settings_includes_consumer(self):
        from context_graph.settings import Settings

        settings = Settings()
        assert hasattr(settings, "consumer")
        assert settings.consumer.max_retries == 5

    def test_consumer_settings_env_override(self, monkeypatch):
        from context_graph.settings import ConsumerSettings

        monkeypatch.setenv("CG_CONSUMER_MAX_RETRIES", "3")
        monkeypatch.setenv("CG_CONSUMER_CLAIM_IDLE_MS", "600000")
        settings = ConsumerSettings()
        assert settings.max_retries == 3
        assert settings.claim_idle_ms == 600_000


# =========================================================================
# Lag metric tests
# =========================================================================


class TestConsumerLagMetric:
    """Tests for CONSUMER_LAG gauge update."""

    @pytest.mark.asyncio()
    async def test_update_lag_metric_sets_gauge(self):
        """_update_lag_metric should set CONSUMER_LAG gauge from xinfo_groups."""
        redis = AsyncMock()
        redis.xinfo_groups.return_value = [
            {"name": "test-group", "lag": 42},
        ]
        consumer = StubConsumer(redis, "test-group", "c1", "stream:test")
        await consumer._update_lag_metric()
        redis.xinfo_groups.assert_called_once_with("stream:test")

    @pytest.mark.asyncio()
    async def test_update_lag_metric_ignores_other_groups(self):
        """Only the matching group name should be used."""
        redis = AsyncMock()
        redis.xinfo_groups.return_value = [
            {"name": "other-group", "lag": 100},
        ]
        consumer = StubConsumer(redis, "test-group", "c1", "stream:test")
        # Should not raise, just silently ignore
        await consumer._update_lag_metric()

    @pytest.mark.asyncio()
    async def test_update_lag_metric_handles_exception(self):
        """Redis errors in lag metric should be swallowed."""
        redis = AsyncMock()
        redis.xinfo_groups.side_effect = Exception("connection lost")
        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        # Should not raise
        await consumer._update_lag_metric()

    @pytest.mark.asyncio()
    async def test_lag_metric_called_every_n_iterations(self):
        """Lag metric should be called every _LAG_METRIC_INTERVAL iterations."""
        redis = AsyncMock()
        redis.xautoclaim.return_value = (b"0-0", [], [])
        redis.xpending_range.return_value = []

        consumer = StubConsumer(redis, "grp", "c1", "stream:test")
        consumer._LAG_METRIC_INTERVAL = 2  # call every 2 iterations

        iteration = 0

        async def _xreadgroup_side_effect(**kwargs):
            nonlocal iteration
            iteration += 1
            if iteration > 4:
                consumer._stopped = True
            return []

        redis.xreadgroup.side_effect = _xreadgroup_side_effect

        with patch.object(
            consumer, "_update_lag_metric", wraps=consumer._update_lag_metric
        ) as mock_lag:
            await consumer.run()
            # Should be called at iterations 2 and 4
            assert mock_lag.call_count == 2
