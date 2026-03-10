"""Unit tests for adapters/redis/trimmer.py — Redis hot-tier trimming.

Uses mock Redis client since these are unit tests (no real Redis connection).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest

from context_graph.adapters.redis.trimmer import (
    _stream_id_sort_key,
    archive_and_delete_expired_events,
    cleanup_dedup_set,
    cleanup_session_streams,
    compute_safe_trim_id,
    delete_expired_events,
    get_consumer_group_progress,
    trim_stream,
)

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
        mock_redis.scan.assert_called_with(cursor=0, match="t:default:evt:*", count=50)

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


# ---------------------------------------------------------------------------
# cleanup_session_streams (ADR-0014)
# ---------------------------------------------------------------------------


class TestCleanupSessionStreams:
    @pytest.fixture()
    def mock_redis(self):
        redis = AsyncMock()
        redis.scan = AsyncMock(return_value=(0, []))
        redis.xrevrange = AsyncMock(return_value=[])
        redis.delete = AsyncMock(return_value=1)
        return redis

    async def test_deletes_old_streams(self, mock_redis):
        """Streams whose newest entry is older than max_age_hours are deleted."""
        import time

        old_ms = int((time.time() - 200 * 3600) * 1000)
        old_entry_id = f"{old_ms}-0"

        mock_redis.scan = AsyncMock(return_value=(0, [b"events:session:old-sess"]))
        mock_redis.xrevrange = AsyncMock(return_value=[(old_entry_id.encode(), {})])

        result = await cleanup_session_streams(mock_redis, max_age_hours=168)

        assert result == 1
        mock_redis.delete.assert_called_once_with("events:session:old-sess")

    async def test_keeps_recent_streams(self, mock_redis):
        """Streams whose newest entry is within max_age_hours are kept."""
        import time

        recent_ms = int((time.time() - 1 * 3600) * 1000)  # 1 hour ago
        recent_entry_id = f"{recent_ms}-0"

        mock_redis.scan = AsyncMock(return_value=(0, [b"events:session:fresh"]))
        mock_redis.xrevrange = AsyncMock(return_value=[(recent_entry_id.encode(), {})])

        result = await cleanup_session_streams(mock_redis, max_age_hours=168)

        assert result == 0
        mock_redis.delete.assert_not_called()

    async def test_deletes_empty_streams(self, mock_redis):
        """Streams with no entries are deleted."""
        mock_redis.scan = AsyncMock(return_value=(0, [b"events:session:empty"]))
        mock_redis.xrevrange = AsyncMock(return_value=[])

        result = await cleanup_session_streams(mock_redis, max_age_hours=168)

        assert result == 1
        mock_redis.delete.assert_called_once_with("events:session:empty")

    async def test_handles_scan_pagination(self, mock_redis):
        """Handles multiple SCAN pages (cursor != 0)."""
        mock_redis.scan = AsyncMock(
            side_effect=[
                (42, [b"events:session:empty1"]),
                (0, [b"events:session:empty2"]),
            ]
        )
        mock_redis.xrevrange = AsyncMock(return_value=[])

        result = await cleanup_session_streams(mock_redis, max_age_hours=168)

        assert result == 2
        assert mock_redis.scan.call_count == 2

    async def test_returns_correct_deleted_count(self, mock_redis):
        """Counts only deleted streams (mix of old, fresh, empty)."""
        import time

        old_ms = int((time.time() - 200 * 3600) * 1000)
        recent_ms = int((time.time() - 1 * 3600) * 1000)

        mock_redis.scan = AsyncMock(
            return_value=(
                0,
                [b"events:session:old", b"events:session:fresh", b"events:session:empty"],
            )
        )
        mock_redis.xrevrange = AsyncMock(
            side_effect=[
                [(f"{old_ms}-0".encode(), {})],  # old — delete
                [(f"{recent_ms}-0".encode(), {})],  # fresh — keep
                [],  # empty — delete
            ]
        )

        result = await cleanup_session_streams(mock_redis, max_age_hours=168)

        assert result == 2


# ---------------------------------------------------------------------------
# archive_and_delete_expired_events (ADR-0014)
# ---------------------------------------------------------------------------


class TestArchiveAndDeleteExpiredEvents:
    @pytest.fixture()
    def mock_redis(self):
        redis = AsyncMock()
        redis.scan = AsyncMock(return_value=(0, []))
        return redis

    @pytest.fixture()
    def mock_archive_store(self):
        store = AsyncMock()
        store.archive_events = AsyncMock(return_value="2025/06/15/test.jsonl.gz")
        return store

    async def test_archives_expired_events_before_deletion(self, mock_redis, mock_archive_store):
        now = datetime.now(UTC)
        old_epoch_ms = int((now - timedelta(days=100)).timestamp() * 1000)
        old_doc = {"event_id": "evt-old", "occurred_at_epoch_ms": old_epoch_ms}

        mock_redis.scan = AsyncMock(return_value=(0, [b"evt:old-1"]))

        # Pipeline for JSON.GET (returns full doc)
        mock_get_pipe = AsyncMock()
        mock_get_pipe.execute = AsyncMock(return_value=[orjson.dumps([old_doc])])
        mock_get_pipe.execute_command = MagicMock()

        # Pipeline for delete
        mock_del_pipe = AsyncMock()
        mock_del_pipe.execute = AsyncMock(return_value=[1])
        mock_del_pipe.delete = MagicMock()

        mock_redis.pipeline = MagicMock(side_effect=[mock_get_pipe, mock_del_pipe])

        archived, deleted = await archive_and_delete_expired_events(
            mock_redis, "evt:", max_age_days=90, archive_store=mock_archive_store
        )

        assert archived == 1
        assert deleted == 1
        mock_archive_store.archive_events.assert_called_once()
        mock_del_pipe.delete.assert_called_once_with("evt:old-1")

    async def test_does_not_archive_fresh_events(self, mock_redis, mock_archive_store):
        now = datetime.now(UTC)
        fresh_epoch_ms = int((now - timedelta(days=10)).timestamp() * 1000)
        fresh_doc = {"event_id": "evt-fresh", "occurred_at_epoch_ms": fresh_epoch_ms}

        mock_redis.scan = AsyncMock(return_value=(0, [b"evt:fresh-1"]))

        mock_get_pipe = AsyncMock()
        mock_get_pipe.execute = AsyncMock(return_value=[orjson.dumps([fresh_doc])])
        mock_get_pipe.execute_command = MagicMock()

        mock_redis.pipeline = MagicMock(return_value=mock_get_pipe)

        archived, deleted = await archive_and_delete_expired_events(
            mock_redis, "evt:", max_age_days=90, archive_store=mock_archive_store
        )

        assert archived == 0
        assert deleted == 0
        mock_archive_store.archive_events.assert_not_called()

    async def test_archive_failure_prevents_deletion(self, mock_redis, mock_archive_store):
        """Data safety: if archiving fails, events must NOT be deleted."""
        now = datetime.now(UTC)
        old_epoch_ms = int((now - timedelta(days=100)).timestamp() * 1000)
        old_doc = {"event_id": "evt-old", "occurred_at_epoch_ms": old_epoch_ms}

        mock_redis.scan = AsyncMock(return_value=(0, [b"evt:old-1"]))

        mock_get_pipe = AsyncMock()
        mock_get_pipe.execute = AsyncMock(return_value=[orjson.dumps([old_doc])])
        mock_get_pipe.execute_command = MagicMock()

        mock_redis.pipeline = MagicMock(return_value=mock_get_pipe)

        # Make archive raise an error
        mock_archive_store.archive_events = AsyncMock(side_effect=OSError("disk full"))

        archived, deleted = await archive_and_delete_expired_events(
            mock_redis, "evt:", max_age_days=90, archive_store=mock_archive_store
        )

        assert archived == 0
        assert deleted == 0

    async def test_returns_tuple_of_counts(self, mock_redis, mock_archive_store):
        mock_redis.scan = AsyncMock(return_value=(0, []))

        result = await archive_and_delete_expired_events(
            mock_redis, "evt:", max_age_days=90, archive_store=mock_archive_store
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result == (0, 0)


# ---------------------------------------------------------------------------
# cleanup_dedup_set (ADR-0014)
# ---------------------------------------------------------------------------


class TestCleanupDedupSet:
    @pytest.fixture()
    def mock_redis(self):
        redis = AsyncMock()
        redis.zremrangebyscore = AsyncMock(return_value=0)
        return redis

    async def test_removes_old_entries(self, mock_redis):
        mock_redis.zremrangebyscore = AsyncMock(return_value=42)

        result = await cleanup_dedup_set(mock_redis, "dedup:events", retention_ceiling_days=90)

        assert result == 42
        mock_redis.zremrangebyscore.assert_called_once()
        call_args = mock_redis.zremrangebyscore.call_args
        assert call_args[0][0] == "dedup:events"
        assert call_args[0][1] == "-inf"

    async def test_default_retention_90_days(self, mock_redis):
        """Default retention_ceiling_days is 90."""
        import time

        await cleanup_dedup_set(mock_redis, "dedup:events")

        call_args = mock_redis.zremrangebyscore.call_args
        cutoff_ms = call_args[0][2]
        expected_ms = int((time.time() - 90 * 86400) * 1000)
        # Allow 1 second tolerance for test execution time
        assert abs(cutoff_ms - expected_ms) < 1000

    async def test_custom_retention_value(self, mock_redis):
        """Custom retention_ceiling_days is respected."""
        import time

        await cleanup_dedup_set(mock_redis, "dedup:events", retention_ceiling_days=30)

        call_args = mock_redis.zremrangebyscore.call_args
        cutoff_ms = call_args[0][2]
        expected_ms = int((time.time() - 30 * 86400) * 1000)
        # Allow 1 second tolerance for test execution time
        assert abs(cutoff_ms - expected_ms) < 1000


# ---------------------------------------------------------------------------
# PEL-safe stream trimming helpers
# ---------------------------------------------------------------------------


class TestStreamIdSortKey:
    def test_basic_sort_key(self):
        assert _stream_id_sort_key("1707644400000-0") == (1707644400000, 0)

    def test_sort_key_with_seq(self):
        assert _stream_id_sort_key("1707644400000-5") == (1707644400000, 5)

    def test_sort_ordering(self):
        ids = ["1707644400000-1", "1707644300000-0", "1707644400000-0"]
        sorted_ids = sorted(ids, key=_stream_id_sort_key)
        assert sorted_ids == ["1707644300000-0", "1707644400000-0", "1707644400000-1"]

    def test_no_seq_part(self):
        """Handles IDs without a sequence number (single numeric part)."""
        assert _stream_id_sort_key("1707644400000") == (1707644400000, 0)


class TestComputeSafeTrimId:
    def test_no_groups_returns_age_cutoff(self):
        result = compute_safe_trim_id("1707644400000-0", {})
        assert result == "1707644400000-0"

    def test_lagging_group_limits_trim_point(self):
        """When a group is behind the cutoff, trim is limited to that group's position."""
        group_progress = {
            "graph-projection": "1707644300000-0",  # behind cutoff
            "enrichment": "1707644500000-0",  # ahead of cutoff
        }
        result = compute_safe_trim_id("1707644400000-0", group_progress)
        assert result == "1707644300000-0"

    def test_all_groups_ahead_uses_age_cutoff(self):
        """When all groups are ahead of the cutoff, the cutoff is used."""
        group_progress = {
            "graph-projection": "1707644500000-0",
            "enrichment": "1707644600000-0",
        }
        result = compute_safe_trim_id("1707644400000-0", group_progress)
        assert result == "1707644400000-0"

    def test_multiple_lagging_groups_uses_oldest(self):
        """The oldest lagging group determines the safe trim point."""
        group_progress = {
            "group-a": "1707644100000-0",
            "group-b": "1707644200000-0",
            "group-c": "1707644500000-0",
        }
        result = compute_safe_trim_id("1707644400000-0", group_progress)
        assert result == "1707644100000-0"

    def test_equal_cutoff_uses_cutoff(self):
        """When group progress equals cutoff, the cutoff is used."""
        group_progress = {"group-a": "1707644400000-0"}
        result = compute_safe_trim_id("1707644400000-0", group_progress)
        assert result == "1707644400000-0"


class TestGetConsumerGroupProgress:
    @pytest.fixture()
    def mock_redis(self):
        return AsyncMock()

    async def test_returns_pending_min_when_available(self, mock_redis):
        mock_redis.xinfo_groups = AsyncMock(
            return_value=[{"name": "graph-projection", "last-delivered-id": "1707644500000-0"}]
        )
        mock_redis.xpending = AsyncMock(
            return_value={"min": "1707644300000-0", "max": "1707644400000-0"}
        )

        result = await get_consumer_group_progress(mock_redis, "events:__global__")

        assert result == {"graph-projection": "1707644300000-0"}

    async def test_falls_back_to_last_delivered(self, mock_redis):
        mock_redis.xinfo_groups = AsyncMock(
            return_value=[{"name": "enrichment", "last-delivered-id": "1707644500000-0"}]
        )
        mock_redis.xpending = AsyncMock(return_value={"min": None, "max": None})

        result = await get_consumer_group_progress(mock_redis, "events:__global__")

        assert result == {"enrichment": "1707644500000-0"}

    async def test_xinfo_groups_error_returns_empty(self, mock_redis):
        mock_redis.xinfo_groups = AsyncMock(side_effect=Exception("NOGROUP"))

        result = await get_consumer_group_progress(mock_redis, "events:__global__")

        assert result == {}

    async def test_xpending_error_falls_back_to_last_delivered(self, mock_redis):
        mock_redis.xinfo_groups = AsyncMock(
            return_value=[{"name": "consolidation", "last-delivered-id": "1707644500000-0"}]
        )
        mock_redis.xpending = AsyncMock(side_effect=Exception("error"))

        result = await get_consumer_group_progress(mock_redis, "events:__global__")

        assert result == {"consolidation": "1707644500000-0"}

    async def test_handles_bytes_group_name(self, mock_redis):
        mock_redis.xinfo_groups = AsyncMock(
            return_value=[{"name": b"graph-projection", "last-delivered-id": b"1707644500000-0"}]
        )
        mock_redis.xpending = AsyncMock(return_value={"min": None})

        result = await get_consumer_group_progress(mock_redis, "events:__global__")

        assert result == {"graph-projection": "1707644500000-0"}


class TestTrimStreamWithConsumerGroups:
    @pytest.fixture()
    def mock_redis(self):
        redis = AsyncMock()
        redis.xlen = AsyncMock(side_effect=[1000, 800])
        redis.xtrim = AsyncMock(return_value=200)
        redis.xinfo_groups = AsyncMock(return_value=[])
        return redis

    async def test_trim_with_consumer_groups_calls_progress(self, mock_redis):
        """When consumer_groups is provided, get_consumer_group_progress is called."""
        mock_redis.xinfo_groups = AsyncMock(return_value=[])

        await trim_stream(
            mock_redis,
            "events:__global__",
            max_age_days=7,
            consumer_groups=["graph-projection", "enrichment"],
        )

        mock_redis.xinfo_groups.assert_called_once_with("events:__global__")

    async def test_trim_without_consumer_groups_skips_progress(self, mock_redis):
        """When consumer_groups is None, no PEL check is done."""
        await trim_stream(mock_redis, "events:__global__", max_age_days=7)

        mock_redis.xinfo_groups.assert_not_called()
