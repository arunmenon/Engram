"""Integration tests for archival lifecycle management (ADR-0014).

Tests archive-before-delete, session stream cleanup, dedup set cleanup,
and Lua global_position correctness against live Redis.

Requires: Docker Redis Stack running (docker-compose up -d redis).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import orjson

if TYPE_CHECKING:
    from pathlib import Path
import pytest
from redis.asyncio import Redis

from context_graph.adapters.fs.archive import FilesystemArchiveStore
from context_graph.adapters.redis.trimmer import (
    archive_and_delete_expired_events,
    cleanup_dedup_set,
    cleanup_session_streams,
)


@pytest.fixture()
async def redis_client():
    """Create a Redis client connected to the test Redis instance."""
    client = Redis(host="localhost", port=6379, db=15, decode_responses=False)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


@pytest.fixture()
def archive_store(tmp_path: Path) -> FilesystemArchiveStore:
    return FilesystemArchiveStore(base_path=tmp_path)


# ---------------------------------------------------------------------------
# Session stream cleanup
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSessionStreamCleanup:
    async def test_deletes_old_session_streams(self, redis_client: Redis):
        """Old session streams are deleted."""
        # Create a "recent" session stream
        await redis_client.xadd("events:session:recent-1", {"event_id": "e1"})

        # Create an "old" session stream by adding then sleeping isn't practical,
        # so we test the function with max_age_hours=0 (everything is old)
        await redis_client.xadd("events:session:old-1", {"event_id": "e2"})

        deleted = await cleanup_session_streams(
            redis_client=redis_client,
            prefix="events:session:",
            max_age_hours=0,  # Everything is "old"
        )

        assert deleted == 2
        assert not await redis_client.exists("events:session:recent-1")
        assert not await redis_client.exists("events:session:old-1")

    async def test_keeps_recent_session_streams(self, redis_client: Redis):
        """Recent session streams are kept."""
        await redis_client.xadd("events:session:recent-1", {"event_id": "e1"})

        deleted = await cleanup_session_streams(
            redis_client=redis_client,
            prefix="events:session:",
            max_age_hours=24,  # 24h — stream just created
        )

        assert deleted == 0
        assert await redis_client.exists("events:session:recent-1")


# ---------------------------------------------------------------------------
# Dedup set cleanup
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDedupSetCleanup:
    async def test_removes_old_dedup_entries(self, redis_client: Redis):
        """Old dedup entries are removed."""
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        old_ms = int((datetime.now(UTC) - timedelta(days=100)).timestamp() * 1000)

        # Add old and fresh entries
        await redis_client.zadd("dedup:test", {"old-event": old_ms, "fresh-event": now_ms})

        removed = await cleanup_dedup_set(
            redis_client=redis_client,
            dedup_key="dedup:test",
            retention_ceiling_days=90,
        )

        assert removed == 1
        assert await redis_client.zscore("dedup:test", "fresh-event") is not None
        assert await redis_client.zscore("dedup:test", "old-event") is None


# ---------------------------------------------------------------------------
# Archive-before-delete lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestArchiveLifecycle:
    async def test_archive_before_delete(
        self,
        redis_client: Redis,
        archive_store: FilesystemArchiveStore,
        tmp_path: Path,
    ):
        """Full lifecycle: ingest → archive → delete → verify."""
        # Create an "old" event document
        old_epoch_ms = int((datetime.now(UTC) - timedelta(days=100)).timestamp() * 1000)
        event_doc = {
            "event_id": "test-evt-1",
            "event_type": "agent.invoke",
            "occurred_at_epoch_ms": old_epoch_ms,
            "session_id": "sess-1",
        }
        await redis_client.execute_command(
            "JSON.SET", "evt:test-evt-1", "$", orjson.dumps(event_doc).decode()
        )

        # Create a "fresh" event document
        fresh_epoch_ms = int(datetime.now(UTC).timestamp() * 1000)
        fresh_doc = {
            "event_id": "test-evt-2",
            "event_type": "tool.execute",
            "occurred_at_epoch_ms": fresh_epoch_ms,
            "session_id": "sess-2",
        }
        await redis_client.execute_command(
            "JSON.SET", "evt:test-evt-2", "$", orjson.dumps(fresh_doc).decode()
        )

        # Run archive-before-delete
        archived, deleted = await archive_and_delete_expired_events(
            redis_client=redis_client,
            key_prefix="evt:",
            max_age_days=90,
            archive_store=archive_store,
        )

        # Verify: old event archived and deleted, fresh event kept
        assert archived == 1
        assert deleted == 1
        assert not await redis_client.exists("evt:test-evt-1")
        assert await redis_client.exists("evt:test-evt-2")

        # Verify archive file exists and is readable
        archives = await archive_store.list_archives()
        assert len(archives) == 1
        restored = await archive_store.restore_archive(archives[0]["archive_id"])
        assert len(restored) == 1
        assert restored[0]["event_id"] == "test-evt-1"


# ---------------------------------------------------------------------------
# Lua global_position correctness
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestLuaGlobalPosition:
    async def test_global_position_set_correctly(self, redis_client: Redis):
        """Verify global_position is set via JSON.SET path, not string.gsub."""
        import importlib.resources

        lua_path = importlib.resources.files("context_graph.adapters.redis.lua").joinpath(
            "ingest.lua"
        )
        lua_source = lua_path.read_text(encoding="utf-8")
        script_sha = await redis_client.script_load(lua_source)

        # Create an event JSON with null global_position
        event = {
            "event_id": "lua-test-1",
            "event_type": "agent.invoke",
            "occurred_at": "2026-02-23T12:00:00Z",
            "session_id": "sess-lua",
            "agent_id": "agent-1",
            "trace_id": "trace-1",
            "payload_ref": "ref-1",
            "global_position": None,
            "occurred_at_epoch_ms": 1000000,
        }
        event_json = orjson.dumps(event).decode()

        result = await redis_client.evalsha(
            script_sha,
            4,
            "events:__global__",
            "evt:lua-test-1",
            "dedup:events",
            "events:session:sess-lua",
            "lua-test-1",
            event_json,
            "1000000",
            "0",  # maxlen = 0 (uncapped)
        )
        entry_id = result.decode() if isinstance(result, bytes) else str(result)

        # Verify the stored global_position matches the stream entry ID
        stored = await redis_client.execute_command("JSON.GET", "evt:lua-test-1", "$")
        stored_str = stored.decode() if isinstance(stored, bytes) else stored
        parsed = orjson.loads(stored_str)
        doc = parsed[0] if isinstance(parsed, list) else parsed
        assert doc["global_position"] == entry_id

        # Verify no string.gsub artifacts (the event_type field should be clean)
        assert doc["event_type"] == "agent.invoke"

    async def test_global_position_in_payload_not_corrupted(self, redis_client: Redis):
        """Ensure 'global_position' appearing in payload data is not affected."""
        import importlib.resources

        lua_path = importlib.resources.files("context_graph.adapters.redis.lua").joinpath(
            "ingest.lua"
        )
        lua_source = lua_path.read_text(encoding="utf-8")
        script_sha = await redis_client.script_load(lua_source)

        # Event with "global_position" appearing inside payload data
        event = {
            "event_id": "lua-test-2",
            "event_type": "agent.invoke",
            "occurred_at": "2026-02-23T12:00:00Z",
            "session_id": "sess-lua-2",
            "agent_id": "agent-1",
            "trace_id": "trace-1",
            "payload_ref": "ref-1",
            "global_position": None,
            "occurred_at_epoch_ms": 2000000,
            "payload": {
                "message": "The global_position field tracks ordering",
                "nested": {"global_position": "should-not-change"},
            },
        }
        event_json = orjson.dumps(event).decode()

        result = await redis_client.evalsha(
            script_sha,
            4,
            "events:__global__",
            "evt:lua-test-2",
            "dedup:events",
            "events:session:sess-lua-2",
            "lua-test-2",
            event_json,
            "2000000",
            "0",
        )
        entry_id = result.decode() if isinstance(result, bytes) else str(result)

        stored = await redis_client.execute_command("JSON.GET", "evt:lua-test-2", "$")
        stored_str = stored.decode() if isinstance(stored, bytes) else stored
        parsed = orjson.loads(stored_str)
        doc = parsed[0] if isinstance(parsed, list) else parsed

        # Top-level global_position should be the entry ID
        assert doc["global_position"] == entry_id

        # Nested payload data should NOT be corrupted
        assert doc["payload"]["message"] == "The global_position field tracks ordering"
        assert doc["payload"]["nested"]["global_position"] == "should-not-change"
