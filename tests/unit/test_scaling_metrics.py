"""Unit tests for scaling-related Prometheus metric registrations.

Verifies that all new metrics added for Redis/Neo4j scaling are
properly registered and accessible.
"""

from __future__ import annotations

from prometheus_client import Gauge, Histogram

from context_graph.metrics import (
    CONSUMER_BATCH_ACTUAL_SIZE,
    CONSUMER_THROUGHPUT,
    REDIS_MEMORY_FRAGMENTATION,
    REDIS_MEMORY_PEAK,
    REDIS_MEMORY_USED,
    REDIS_POOL_IN_USE,
    REDIS_POOL_SIZE,
)


class TestRedisPoolMetrics:
    """Verify Redis connection pool metrics exist and are correct types."""

    def test_pool_size_is_gauge(self):
        assert isinstance(REDIS_POOL_SIZE, Gauge)

    def test_pool_in_use_is_gauge(self):
        assert isinstance(REDIS_POOL_IN_USE, Gauge)

    def test_pool_size_name(self):
        assert REDIS_POOL_SIZE._name == "engram_redis_pool_size"

    def test_pool_in_use_name(self):
        assert REDIS_POOL_IN_USE._name == "engram_redis_pool_in_use"


class TestRedisMemoryMetrics:
    """Verify Redis memory metrics exist and are correct types."""

    def test_memory_used_is_gauge(self):
        assert isinstance(REDIS_MEMORY_USED, Gauge)

    def test_memory_peak_is_gauge(self):
        assert isinstance(REDIS_MEMORY_PEAK, Gauge)

    def test_memory_fragmentation_is_gauge(self):
        assert isinstance(REDIS_MEMORY_FRAGMENTATION, Gauge)

    def test_memory_used_name(self):
        assert REDIS_MEMORY_USED._name == "engram_redis_memory_used_bytes"

    def test_memory_peak_name(self):
        assert REDIS_MEMORY_PEAK._name == "engram_redis_memory_peak_bytes"

    def test_memory_fragmentation_name(self):
        assert REDIS_MEMORY_FRAGMENTATION._name == "engram_redis_memory_fragmentation_ratio"


class TestConsumerMetrics:
    """Verify consumer throughput and batch size metrics."""

    def test_throughput_is_gauge(self):
        assert isinstance(CONSUMER_THROUGHPUT, Gauge)

    def test_throughput_has_consumer_label(self):
        assert "consumer" in CONSUMER_THROUGHPUT._labelnames

    def test_throughput_name(self):
        assert CONSUMER_THROUGHPUT._name == "engram_consumer_events_per_second"

    def test_batch_actual_size_is_histogram(self):
        assert isinstance(CONSUMER_BATCH_ACTUAL_SIZE, Histogram)

    def test_batch_actual_size_has_consumer_label(self):
        assert "consumer" in CONSUMER_BATCH_ACTUAL_SIZE._labelnames

    def test_batch_actual_size_name(self):
        assert CONSUMER_BATCH_ACTUAL_SIZE._name == "engram_consumer_batch_actual_size"


class TestAdaptiveBatchSettings:
    """Verify adaptive batch size setting is available."""

    def test_consumer_settings_has_adaptive_batch_size(self):
        from context_graph.settings import ConsumerSettings

        settings = ConsumerSettings()
        assert hasattr(settings, "adaptive_batch_size")
        assert settings.adaptive_batch_size is True

    def test_redis_settings_has_batch_concurrency(self):
        from context_graph.settings import RedisSettings

        settings = RedisSettings()
        assert hasattr(settings, "batch_concurrency")
        assert settings.batch_concurrency == 50

    def test_redis_settings_has_memory_pressure_threshold(self):
        from context_graph.settings import RedisSettings

        settings = RedisSettings()
        assert hasattr(settings, "memory_pressure_threshold_pct")
        assert settings.memory_pressure_threshold_pct == 80.0

    def test_redis_settings_maxlen_default(self):
        from context_graph.settings import RedisSettings

        settings = RedisSettings()
        assert settings.global_stream_maxlen == 500_000


class TestConsumerAdaptiveBatchSize:
    """Test the _compute_batch_size method on BaseConsumer."""

    def test_base_batch_size_for_low_lag(self):
        from unittest.mock import AsyncMock

        from context_graph.worker.consumer import BaseConsumer

        class StubConsumer(BaseConsumer):
            async def process_message(self, entry_id, data):
                pass

        consumer = StubConsumer(AsyncMock(), "grp", "c1", "stream", batch_size=10)
        assert consumer._compute_batch_size(0) == 10
        assert consumer._compute_batch_size(500) == 10
        assert consumer._compute_batch_size(999) == 10

    def test_2x_batch_size_for_medium_lag(self):
        from unittest.mock import AsyncMock

        from context_graph.worker.consumer import BaseConsumer

        class StubConsumer(BaseConsumer):
            async def process_message(self, entry_id, data):
                pass

        consumer = StubConsumer(AsyncMock(), "grp", "c1", "stream", batch_size=10)
        assert consumer._compute_batch_size(1_000) == 20
        assert consumer._compute_batch_size(5_000) == 20
        assert consumer._compute_batch_size(9_999) == 20

    def test_4x_batch_size_for_high_lag(self):
        from unittest.mock import AsyncMock

        from context_graph.worker.consumer import BaseConsumer

        class StubConsumer(BaseConsumer):
            async def process_message(self, entry_id, data):
                pass

        consumer = StubConsumer(AsyncMock(), "grp", "c1", "stream", batch_size=10)
        assert consumer._compute_batch_size(10_000) == 40
        assert consumer._compute_batch_size(100_000) == 40
