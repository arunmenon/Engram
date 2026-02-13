"""Unit tests for adapters/redis/trimmer.py — Redis hot-tier trimming.

Uses mock Redis client since these are unit tests (no real Redis connection).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.adapters.redis.trimmer import delete_expired_events, trim_stream

# ---------------------------------------------------------------------------
# trim_stream
# ---------------------------------------------------------------------------


class TestTrimStream:
    @pytest.fixture()
    def mock_redis(self):
        redis = AsyncMock()
        redis.xlen = AsyncMock(side_effect=[1000, 800])  # before, after
        redis.xtrim = AsyncMock(return_value=200)
        return redis

    async def test_trim_calls_xtrim_with_minid(self, mock_redis):
        result = await trim_stream(mock_redis, "events:__global__", max_age_days=7)

        mock_redis.xtrim.assert_called_once()
        call_kwargs = mock_redis.xtrim.call_args
        assert call_kwargs.kwargs["name"] == "events:__global__"
        assert call_kwargs.kwargs["approximate"] is False
        # Verify minid is a timestamp string
        min_id = call_kwargs.kwargs["minid"]
        assert "-0" in min_id
        assert result == 200

    async def test_trim_reports_correct_count(self, mock_redis):
        mock_redis.xtrim = AsyncMock(return_value=50)
        result = await trim_stream(mock_redis, "test-stream", max_age_days=1)
        assert result == 50

    async def test_trim_zero_entries(self, mock_redis):
        mock_redis.xlen = AsyncMock(side_effect=[100, 100])
        mock_redis.xtrim = AsyncMock(return_value=0)
        result = await trim_stream(mock_redis, "test-stream", max_age_days=30)
        assert result == 0

    async def test_trim_minid_calculation(self, mock_redis):
        """Verify the MINID is calculated from max_age_days."""
        with patch("context_graph.adapters.redis.trimmer.datetime") as mock_dt:
            fixed_now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = fixed_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            await trim_stream(mock_redis, "stream", max_age_days=7)

            expected_cutoff = fixed_now - timedelta(days=7)
            expected_ms = int(expected_cutoff.timestamp() * 1000)
            expected_min_id = f"{expected_ms}-0"

            call_kwargs = mock_redis.xtrim.call_args
            assert call_kwargs.kwargs["minid"] == expected_min_id


# ---------------------------------------------------------------------------
# delete_expired_events
# ---------------------------------------------------------------------------


class TestDeleteExpiredEvents:
    @pytest.fixture()
    def mock_redis(self):
        redis = AsyncMock()
        # Simulate SCAN returning no keys after first call
        redis.scan = AsyncMock(return_value=(0, []))
        return redis

    async def test_no_keys_found(self, mock_redis):
        result = await delete_expired_events(mock_redis, "evt:", max_age_days=90)
        assert result == 0

    async def test_deletes_expired_keys(self, mock_redis):
        now = datetime.now(UTC)
        old_epoch_ms = int((now - timedelta(days=100)).timestamp() * 1000)
        fresh_epoch_ms = int((now - timedelta(days=10)).timestamp() * 1000)

        # First scan returns keys, second scan returns empty (cursor=0)
        mock_redis.scan = AsyncMock(
            side_effect=[
                (0, [b"evt:old-1", b"evt:fresh-1"]),
            ]
        )

        # Pipeline for JSON.GET
        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(
            return_value=[
                f"[{old_epoch_ms}]".encode(),
                f"[{fresh_epoch_ms}]".encode(),
            ]
        )
        mock_pipe.execute_command = MagicMock()

        # Pipeline for delete
        mock_delete_pipe = AsyncMock()
        mock_delete_pipe.execute = AsyncMock(return_value=[1])
        mock_delete_pipe.delete = MagicMock()

        # Return different pipelines for get vs delete
        mock_redis.pipeline = MagicMock(side_effect=[mock_pipe, mock_delete_pipe])

        result = await delete_expired_events(mock_redis, "evt:", max_age_days=90)
        assert result == 1  # Only the old key should be deleted
        mock_delete_pipe.delete.assert_called_once_with("evt:old-1")

    async def test_handles_none_json_values(self, mock_redis):
        mock_redis.scan = AsyncMock(return_value=(0, [b"evt:no-json"]))

        mock_pipe = AsyncMock()
        mock_pipe.execute = AsyncMock(return_value=[None])
        mock_pipe.execute_command = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        result = await delete_expired_events(mock_redis, "evt:", max_age_days=90)
        assert result == 0

    async def test_batch_size_passed_to_scan(self, mock_redis):
        await delete_expired_events(mock_redis, "evt:", max_age_days=90, batch_size=50)
        mock_redis.scan.assert_called_with(cursor=0, match="evt:*", count=50)

    async def test_multiple_scan_pages(self, mock_redis):
        # First page returns cursor=42, second page returns cursor=0
        mock_redis.scan = AsyncMock(
            side_effect=[
                (42, []),
                (0, []),
            ]
        )

        result = await delete_expired_events(mock_redis, "evt:", max_age_days=90)
        assert result == 0
        assert mock_redis.scan.call_count == 2
