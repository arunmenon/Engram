"""Unit tests for Redis memory pressure monitoring and proactive trimming.

Tests get_memory_info structure, is_memory_pressure thresholds,
and trim_under_pressure delegation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from context_graph.adapters.redis.store import RedisEventStore
from context_graph.adapters.redis.trimmer import trim_under_pressure
from context_graph.settings import RedisSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(
    memory_info: dict | None = None,
    threshold_pct: float = 80.0,
) -> RedisEventStore:
    """Create a RedisEventStore with mocked Redis INFO memory response."""
    client = AsyncMock()
    if memory_info is None:
        memory_info = {
            "used_memory": 500_000_000,
            "used_memory_peak": 600_000_000,
            "maxmemory": 1_000_000_000,
            "mem_fragmentation_ratio": 1.2,
        }
    client.info = AsyncMock(return_value=memory_info)

    settings = RedisSettings(memory_pressure_threshold_pct=threshold_pct)
    store = RedisEventStore(client=client, settings=settings)
    store._script_sha = "fake_sha"
    return store


# ---------------------------------------------------------------------------
# get_memory_info
# ---------------------------------------------------------------------------


class TestGetMemoryInfo:
    """Test Redis memory info retrieval."""

    @pytest.mark.asyncio()
    async def test_returns_expected_keys(self):
        """get_memory_info should return all documented keys."""
        store = _make_store()
        info = await store.get_memory_info()

        assert "used_memory_bytes" in info
        assert "used_memory_peak_bytes" in info
        assert "maxmemory_bytes" in info
        assert "mem_fragmentation_ratio" in info
        assert "used_memory_pct" in info

    @pytest.mark.asyncio()
    async def test_calculates_percentage_correctly(self):
        """Percentage should be used/max * 100."""
        store = _make_store(
            memory_info={
                "used_memory": 800_000_000,
                "used_memory_peak": 900_000_000,
                "maxmemory": 1_000_000_000,
                "mem_fragmentation_ratio": 1.1,
            }
        )
        info = await store.get_memory_info()
        assert info["used_memory_pct"] == pytest.approx(80.0, abs=0.01)

    @pytest.mark.asyncio()
    async def test_percentage_zero_when_maxmemory_unset(self):
        """When maxmemory is 0, percentage should be 0."""
        store = _make_store(
            memory_info={
                "used_memory": 500_000_000,
                "used_memory_peak": 600_000_000,
                "maxmemory": 0,
                "mem_fragmentation_ratio": 1.0,
            }
        )
        info = await store.get_memory_info()
        assert info["used_memory_pct"] == 0.0

    @pytest.mark.asyncio()
    async def test_values_match_redis_info(self):
        """Returned values should match what Redis INFO reports."""
        store = _make_store(
            memory_info={
                "used_memory": 123_456_789,
                "used_memory_peak": 234_567_890,
                "maxmemory": 1_000_000_000,
                "mem_fragmentation_ratio": 1.5,
            }
        )
        info = await store.get_memory_info()
        assert info["used_memory_bytes"] == 123_456_789
        assert info["used_memory_peak_bytes"] == 234_567_890
        assert info["maxmemory_bytes"] == 1_000_000_000
        assert info["mem_fragmentation_ratio"] == 1.5


# ---------------------------------------------------------------------------
# is_memory_pressure
# ---------------------------------------------------------------------------


class TestIsMemoryPressure:
    """Test memory pressure threshold detection."""

    @pytest.mark.asyncio()
    async def test_pressure_when_above_threshold(self):
        """Should return True when usage exceeds threshold."""
        store = _make_store(
            memory_info={
                "used_memory": 900_000_000,
                "used_memory_peak": 900_000_000,
                "maxmemory": 1_000_000_000,
                "mem_fragmentation_ratio": 1.0,
            },
            threshold_pct=80.0,
        )
        assert await store.is_memory_pressure() is True

    @pytest.mark.asyncio()
    async def test_no_pressure_when_below_threshold(self):
        """Should return False when usage is below threshold."""
        store = _make_store(
            memory_info={
                "used_memory": 500_000_000,
                "used_memory_peak": 600_000_000,
                "maxmemory": 1_000_000_000,
                "mem_fragmentation_ratio": 1.0,
            },
            threshold_pct=80.0,
        )
        assert await store.is_memory_pressure() is False

    @pytest.mark.asyncio()
    async def test_no_pressure_when_maxmemory_unset(self):
        """Should return False when maxmemory is 0 (uncapped)."""
        store = _make_store(
            memory_info={
                "used_memory": 999_000_000,
                "used_memory_peak": 999_000_000,
                "maxmemory": 0,
                "mem_fragmentation_ratio": 1.0,
            },
            threshold_pct=80.0,
        )
        assert await store.is_memory_pressure() is False

    @pytest.mark.asyncio()
    async def test_boundary_at_threshold(self):
        """Exactly at threshold should not be pressure (strictly greater)."""
        store = _make_store(
            memory_info={
                "used_memory": 800_000_000,
                "used_memory_peak": 800_000_000,
                "maxmemory": 1_000_000_000,
                "mem_fragmentation_ratio": 1.0,
            },
            threshold_pct=80.0,
        )
        # 80% is not > 80% -- no pressure
        assert await store.is_memory_pressure() is False

    @pytest.mark.asyncio()
    async def test_custom_threshold(self):
        """Custom threshold should be respected."""
        store = _make_store(
            memory_info={
                "used_memory": 600_000_000,
                "used_memory_peak": 600_000_000,
                "maxmemory": 1_000_000_000,
                "mem_fragmentation_ratio": 1.0,
            },
            threshold_pct=50.0,
        )
        assert await store.is_memory_pressure() is True


# ---------------------------------------------------------------------------
# trim_under_pressure
# ---------------------------------------------------------------------------


class TestTrimUnderPressure:
    """Test proactive memory pressure trimming."""

    @pytest.fixture()
    def mock_redis(self):
        return AsyncMock()

    @pytest.mark.asyncio()
    async def test_calls_all_trim_functions(self, mock_redis):
        """trim_under_pressure should call all four cleanup functions."""
        with (
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=5,
            ) as mock_sessions,
            patch(
                "context_graph.adapters.redis.trimmer.delete_expired_events",
                new_callable=AsyncMock,
                return_value=10,
            ) as mock_delete,
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=3,
            ) as mock_dedup,
            patch(
                "context_graph.adapters.redis.trimmer.trim_stream",
                new_callable=AsyncMock,
                return_value=20,
            ) as mock_trim,
        ):
            freed = await trim_under_pressure(mock_redis)

        assert freed == 38  # 5 + 10 + 3 + 20
        mock_sessions.assert_called_once()
        mock_delete.assert_called_once()
        mock_dedup.assert_called_once()
        mock_trim.assert_called_once()

    @pytest.mark.asyncio()
    async def test_uses_halved_retention(self, mock_redis):
        """Session streams should use half the normal retention."""
        with (
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_sessions,
            patch(
                "context_graph.adapters.redis.trimmer.delete_expired_events",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_delete,
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.adapters.redis.trimmer.trim_stream",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            await trim_under_pressure(
                mock_redis,
                hot_window_days=7,
                retention_ceiling_days=90,
            )

        # Session streams: (7 * 24) / 2 = 84 hours
        session_call = mock_sessions.call_args
        assert session_call.kwargs.get("max_age_hours") == 84

        # JSON docs: 90 / 2 = 45 days
        delete_call = mock_delete.call_args
        assert delete_call.kwargs.get("max_age_days") == 45

    @pytest.mark.asyncio()
    async def test_dedup_capped_at_30_days(self, mock_redis):
        """Dedup cleanup should use 30 days regardless of normal ceiling."""
        with (
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.adapters.redis.trimmer.delete_expired_events",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_dedup,
            patch(
                "context_graph.adapters.redis.trimmer.trim_stream",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            await trim_under_pressure(
                mock_redis,
                retention_ceiling_days=90,
            )

        dedup_call = mock_dedup.call_args
        assert dedup_call.kwargs.get("retention_ceiling_days") == 30

    @pytest.mark.asyncio()
    async def test_returns_total_freed(self, mock_redis):
        """Should return sum of all freed items."""
        with (
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.adapters.redis.trimmer.delete_expired_events",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=0,
            ),
            patch(
                "context_graph.adapters.redis.trimmer.trim_stream",
                new_callable=AsyncMock,
                return_value=0,
            ),
        ):
            freed = await trim_under_pressure(mock_redis)

        assert freed == 0

    @pytest.mark.asyncio()
    async def test_passes_tenant_id(self, mock_redis):
        """Tenant ID should be forwarded to all cleanup functions."""
        with (
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_session_streams",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_sessions,
            patch(
                "context_graph.adapters.redis.trimmer.delete_expired_events",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_delete,
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_dedup_set",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_dedup,
            patch(
                "context_graph.adapters.redis.trimmer.trim_stream",
                new_callable=AsyncMock,
                return_value=0,
            ) as mock_trim,
        ):
            await trim_under_pressure(mock_redis, tenant_id="acme")

        assert mock_sessions.call_args.kwargs["tenant_id"] == "acme"
        assert mock_delete.call_args.kwargs["tenant_id"] == "acme"
        assert mock_dedup.call_args.kwargs["tenant_id"] == "acme"
        assert mock_trim.call_args.kwargs["tenant_id"] == "acme"
