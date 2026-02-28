"""Unit tests for Lua ingest script integration — ARGV handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.redis.store import RedisEventStore


@pytest.fixture()
def mock_redis_client():
    client = AsyncMock()
    client.evalsha = AsyncMock(return_value=b"1707644400000-0")
    client.script_load = AsyncMock(return_value="abc123sha")
    client.execute_command = AsyncMock()
    return client


@pytest.fixture()
def default_redis_settings():
    """Settings with default global_stream_maxlen=0."""
    settings = MagicMock()
    settings.host = "localhost"
    settings.port = 6379
    settings.db = 0
    settings.password = None
    settings.global_stream = "events:__global__"
    settings.dedup_set = "dedup:events"
    settings.event_key_prefix = "evt:"
    settings.event_index = "idx:events"
    settings.global_stream_maxlen = 0
    settings.replica_wait = False
    return settings


@pytest.fixture()
def capped_redis_settings():
    """Settings with a non-zero global_stream_maxlen."""
    settings = MagicMock()
    settings.host = "localhost"
    settings.port = 6379
    settings.db = 0
    settings.password = None
    settings.global_stream = "events:__global__"
    settings.dedup_set = "dedup:events"
    settings.event_key_prefix = "evt:"
    settings.event_index = "idx:events"
    settings.global_stream_maxlen = 100_000
    settings.replica_wait = False
    return settings


@pytest.fixture()
def sample_event():
    """Create a minimal valid Event for testing."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from context_graph.domain.models import Event

    return Event(
        event_id=uuid4(),
        event_type="test.event",
        occurred_at=datetime.now(UTC),
        session_id="sess-001",
        agent_id="agent-001",
        trace_id="trace-001",
        payload_ref="ref://test",
    )


class TestLuaArgvHandling:
    """Tests verifying the Python store passes correct ARGV to evalsha."""

    @pytest.mark.asyncio()
    async def test_append_passes_maxlen_as_fourth_argv(
        self, mock_redis_client, default_redis_settings, sample_event
    ):
        """evalsha should receive the maxlen as the last positional argument.

        evalsha(sha, num_keys, KEYS[1..4], ARGV[1..4])
        positional indices: 0=sha, 1=4, 2-5=KEYS, 6=event_id, 7=json, 8=epoch_ms, 9=maxlen
        """
        store = RedisEventStore(client=mock_redis_client, settings=default_redis_settings)
        store._script_sha = "abc123sha"

        await store.append(sample_event)

        mock_redis_client.evalsha.assert_called_once()
        positional = mock_redis_client.evalsha.call_args[0]
        # ARGV[4] = maxlen is index 9 (sha, numkeys, 4 keys, 4 args)
        maxlen_arg = positional[9]
        assert maxlen_arg == "0"

    @pytest.mark.asyncio()
    async def test_append_default_maxlen_zero(
        self, mock_redis_client, default_redis_settings, sample_event
    ):
        """Default settings should pass '0' as ARGV[4] (uncapped stream)."""
        store = RedisEventStore(client=mock_redis_client, settings=default_redis_settings)
        store._script_sha = "abc123sha"

        await store.append(sample_event)

        positional = mock_redis_client.evalsha.call_args[0]
        assert positional[9] == "0"

    @pytest.mark.asyncio()
    async def test_append_configured_maxlen(
        self, mock_redis_client, capped_redis_settings, sample_event
    ):
        """Non-zero global_stream_maxlen should be passed as ARGV[4]."""
        store = RedisEventStore(client=mock_redis_client, settings=capped_redis_settings)
        store._script_sha = "abc123sha"

        await store.append(sample_event)

        positional = mock_redis_client.evalsha.call_args[0]
        assert positional[9] == "100000"

    @pytest.mark.asyncio()
    async def test_batch_uses_pipeline(
        self, mock_redis_client, default_redis_settings, sample_event
    ):
        """append_batch should use a Redis pipeline for single-roundtrip batching."""
        mock_pipe = MagicMock()
        mock_pipe.evalsha = MagicMock()
        mock_pipe.execute = AsyncMock(
            return_value=[b"1707644400000-0", b"1707644400001-0", b"1707644400002-0"]
        )
        mock_redis_client.pipeline = MagicMock(return_value=mock_pipe)

        store = RedisEventStore(client=mock_redis_client, settings=default_redis_settings)
        store._script_sha = "abc123sha"

        events = [sample_event, sample_event, sample_event]
        results = await store.append_batch(events)

        # Verify pipeline was created without transaction
        mock_redis_client.pipeline.assert_called_once_with(transaction=False)
        # Verify evalsha was queued for each event
        assert mock_pipe.evalsha.call_count == 3
        # Verify single execute call (one round-trip)
        mock_pipe.execute.assert_called_once()
        assert len(results) == 3

    def test_no_string_gsub_in_lua(self):
        """The Lua ingest script must NOT call string.gsub for JSON patching (ADR-0014).

        Only checks non-comment lines — mentions in comments are acceptable.
        """
        import importlib.resources

        lua_path = importlib.resources.files("context_graph.adapters.redis.lua").joinpath(
            "ingest.lua"
        )
        lua_source = lua_path.read_text(encoding="utf-8")

        # Check only non-comment lines for actual string.gsub usage
        code_lines = [line for line in lua_source.splitlines() if not line.strip().startswith("--")]
        code_only = "\n".join(code_lines)

        assert "string.gsub" not in code_only, (
            "Lua ingest script should not call string.gsub in executable code — "
            "use JSON.SET path approach instead (ADR-0014)"
        )
