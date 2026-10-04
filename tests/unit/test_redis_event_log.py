"""Unit tests for the EventLog methods on RedisEventStore (ADR-0019 step 1).

Workers and the consolidation worker now read and retain events through
the EventLog port. These tests pin the Redis commands behind each method
to the ones the workers issued directly before the change.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import orjson
import pytest

from context_graph.adapters.redis.store import RedisEventStore


def _settings() -> MagicMock:
    settings = MagicMock()
    settings.event_key_prefix = "evt:"
    settings.global_stream = "events:__global__"
    settings.dedup_set = "dedup:events"
    return settings


def _store(redis: AsyncMock) -> RedisEventStore:
    return RedisEventStore(client=redis, settings=_settings())


class TestGetDocuments:
    @pytest.mark.asyncio()
    async def test_issues_json_get_per_id_in_order(self):
        redis = AsyncMock()
        redis.execute_command.side_effect = [
            orjson.dumps([{"event_id": "a", "occurred_at_epoch_ms": 1, "payload": {"x": 1}}]),
            None,
        ]
        documents = await _store(redis).get_documents(["a", "b"])

        assert [c.args for c in redis.execute_command.call_args_list] == [
            ("JSON.GET", "evt:a", "$"),
            ("JSON.GET", "evt:b", "$"),
        ]
        assert documents == [{"event_id": "a", "payload": {"x": 1}}, None]

    @pytest.mark.asyncio()
    async def test_accepts_unwrapped_document(self):
        redis = AsyncMock()
        redis.execute_command.return_value = orjson.dumps({"event_id": "a"}).decode()
        documents = await _store(redis).get_documents(["a"])
        assert documents == [{"event_id": "a"}]


class TestReadSessionIds:
    @pytest.mark.asyncio()
    async def test_reads_per_session_stream(self):
        redis = AsyncMock()
        redis.xrange.return_value = [
            (b"1-0", {b"event_id": b"e1"}),
            (b"2-0", {b"other": b"x"}),
            (b"3-0", {"event_id": "e3"}),
        ]
        event_ids = await _store(redis).read_session_ids("s1")

        redis.xrange.assert_called_once_with("events:session:s1", min="-", max="+")
        assert event_ids == ["e1", "e3"]

    @pytest.mark.asyncio()
    async def test_propagates_read_errors(self):
        redis = AsyncMock()
        redis.xrange.side_effect = ConnectionError("down")
        with pytest.raises(ConnectionError):
            await _store(redis).read_session_ids("s1")


class TestRetention:
    @pytest.mark.asyncio()
    async def test_trim_targets_global_stream(self):
        redis = AsyncMock()
        with patch(
            "context_graph.adapters.redis.trimmer.trim_stream", new_callable=AsyncMock
        ) as trim_stream:
            trim_stream.return_value = 4
            trimmed = await _store(redis).trim(max_age_days=7, consumer_groups=["g1", "g2"])

        assert trimmed == 4
        trim_stream.assert_called_once_with(
            redis_client=redis,
            stream_key="events:__global__",
            max_age_days=7,
            consumer_groups=["g1", "g2"],
        )

    @pytest.mark.asyncio()
    async def test_expire_archives_when_archive_given(self):
        redis = AsyncMock()
        archive = AsyncMock()
        with patch(
            "context_graph.adapters.redis.trimmer.archive_and_delete_expired_events",
            new_callable=AsyncMock,
        ) as archive_and_delete:
            archive_and_delete.return_value = (10, 10)
            result = await _store(redis).expire(max_age_days=90, archive_store=archive)

        assert result == (10, 10)
        archive_and_delete.assert_called_once_with(
            redis_client=redis,
            key_prefix="evt:",
            max_age_days=90,
            archive_store=archive,
        )

    @pytest.mark.asyncio()
    async def test_expire_plain_delete_without_archive(self):
        redis = AsyncMock()
        with patch(
            "context_graph.adapters.redis.trimmer.delete_expired_events",
            new_callable=AsyncMock,
        ) as delete_expired:
            delete_expired.return_value = 7
            result = await _store(redis).expire(max_age_days=90)

        assert result == (0, 7)
        delete_expired.assert_called_once_with(
            redis_client=redis,
            key_prefix="evt:",
            max_age_days=90,
        )

    @pytest.mark.asyncio()
    async def test_housekeep_cleans_dedup_and_session_streams(self):
        redis = AsyncMock()
        with (
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_dedup_set",
                new_callable=AsyncMock,
            ) as cleanup_dedup,
            patch(
                "context_graph.adapters.redis.trimmer.cleanup_session_streams",
                new_callable=AsyncMock,
            ) as cleanup_sessions,
        ):
            cleanup_dedup.return_value = 5
            cleanup_sessions.return_value = 3
            counts = await _store(redis).housekeep(
                retention_ceiling_days=90, session_index_max_age_hours=168
            )

        assert counts == {"dedup_entries_removed": 5, "session_streams_deleted": 3}
        cleanup_dedup.assert_called_once_with(
            redis_client=redis,
            dedup_key="dedup:events",
            retention_ceiling_days=90,
        )
        cleanup_sessions.assert_called_once_with(
            redis_client=redis,
            prefix="events:session:",
            max_age_hours=168,
        )


class TestMigration:
    @pytest.mark.asyncio()
    async def test_read_after_uses_exclusive_cursor(self):
        redis = AsyncMock()
        redis.xrange.return_value = [(b"5-0", {b"event_id": b"e5"})]
        redis.execute_command.return_value = orjson.dumps([{"event_id": "e5"}])
        entries = await _store(redis).read_after("4-0", 10)

        redis.xrange.assert_called_once_with("events:__global__", min="(4-0", max="+", count=10)
        assert [(e.position, e.event_id) for e in entries] == [("5-0", "e5")]
        assert entries[0].document == {"event_id": "e5"}

    @pytest.mark.asyncio()
    async def test_read_after_from_start(self):
        redis = AsyncMock()
        redis.xrange.return_value = []
        await _store(redis).read_after(None, 3)
        redis.xrange.assert_called_once_with("events:__global__", min="-", max="+", count=3)

    @pytest.mark.asyncio()
    async def test_append_imported_runs_ingest_script_with_legacy_position(self):
        from context_graph.ports.event_log import ImportedEvent

        redis = AsyncMock()
        pipe = MagicMock()
        pipe.execute = AsyncMock(return_value=[b"9-0"])
        redis.pipeline = MagicMock(return_value=pipe)
        store = _store(redis)
        store._script_sha = "sha"
        document = {
            "event_id": "e1",
            "session_id": "s1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "global_position": "old",
        }

        positions = await store.append_imported(
            [ImportedEvent(document=document, legacy_position="1-0")]
        )

        assert positions == ["9-0"]
        args = pipe.evalsha.call_args.args
        assert args[2:6] == ("events:__global__", "evt:e1", "dedup:events", "events:session:s1")
        stored = orjson.loads(args[7])
        assert stored["legacy_position"] == "1-0"
        assert "global_position" not in stored
        assert stored["occurred_at_epoch_ms"] == 1767225600000

    @pytest.mark.asyncio()
    async def test_last_legacy_position_scans_newest_first(self):
        redis = AsyncMock()
        redis.xrevrange.return_value = [
            (b"3-0", {b"event_id": b"e3"}),
            (b"2-0", {b"event_id": b"e2"}),
        ]
        redis.execute_command.side_effect = [
            orjson.dumps([{"event_id": "e3"}]),
            orjson.dumps([{"event_id": "e2", "legacy_position": "src-2"}]),
        ]
        assert await _store(redis).last_legacy_position() == "src-2"
        redis.xrevrange.assert_called_once()

    @pytest.mark.asyncio()
    async def test_has_native_events(self):
        redis = AsyncMock()
        redis.xrange.return_value = [(b"1-0", {b"event_id": b"e1"})]
        redis.execute_command.return_value = orjson.dumps([{"event_id": "e1"}])
        assert await _store(redis).has_native_events() is True
