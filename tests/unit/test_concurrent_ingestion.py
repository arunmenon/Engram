"""Unit tests for concurrent batch ingestion in RedisEventStore.

Tests semaphore-bounded concurrent ingestion, delegation from
append_batch for large batches, and error propagation.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from context_graph.adapters.redis.store import RedisEventStore
from context_graph.domain.models import Event
from context_graph.settings import RedisSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(**overrides) -> Event:
    """Create a test Event with sensible defaults."""
    defaults = {
        "event_id": uuid4(),
        "event_type": "test.event",
        "occurred_at": datetime.now(UTC),
        "session_id": str(uuid4()),
        "agent_id": "test-agent",
        "trace_id": str(uuid4()),
        "payload_ref": "ref://test",
    }
    defaults.update(overrides)
    return Event(**defaults)


def _make_store(settings: RedisSettings | None = None) -> RedisEventStore:
    """Create a RedisEventStore with a mocked Redis client."""
    client = AsyncMock()
    if settings is None:
        settings = RedisSettings()
    store = RedisEventStore(client=client, settings=settings)
    store._script_sha = "fake_sha"
    return store


# ---------------------------------------------------------------------------
# append_batch_concurrent
# ---------------------------------------------------------------------------


class TestAppendBatchConcurrent:
    """Test the semaphore-bounded concurrent batch ingestion."""

    @pytest.mark.asyncio()
    async def test_concurrent_returns_correct_positions(self):
        """All events should be ingested and positions returned."""
        store = _make_store()
        events = [_make_event() for _ in range(5)]

        with patch.object(store, "append", new_callable=AsyncMock) as mock_append:
            mock_append.side_effect = [f"{i + 1}-0" for i in range(5)]
            positions = await store.append_batch_concurrent(events)

        assert len(positions) == 5
        assert positions == ["1-0", "2-0", "3-0", "4-0", "5-0"]
        assert mock_append.call_count == 5

    @pytest.mark.asyncio()
    async def test_semaphore_limits_concurrency(self):
        """Concurrency should be bounded by the semaphore."""
        settings = RedisSettings(batch_concurrency=2)
        store = _make_store(settings=settings)
        events = [_make_event() for _ in range(10)]

        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        original_append = AsyncMock(return_value="1-0")

        async def tracking_append(event, tenant_id="default"):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.01)  # simulate work
            result = await original_append(event, tenant_id=tenant_id)
            async with lock:
                current_concurrent -= 1
            return result

        with patch.object(store, "append", side_effect=tracking_append):
            await store.append_batch_concurrent(events)

        # Semaphore should limit to 2 concurrent
        assert max_concurrent <= 2

    @pytest.mark.asyncio()
    async def test_concurrent_empty_batch(self):
        """Empty event list should return empty positions."""
        store = _make_store()
        # append_batch_concurrent doesn't get called for empty (short-circuited in append_batch)
        # but test direct call
        with patch.object(store, "append", new_callable=AsyncMock) as mock_append:
            positions = await store.append_batch_concurrent([])
        assert positions == []
        mock_append.assert_not_called()

    @pytest.mark.asyncio()
    async def test_concurrent_propagates_errors(self):
        """Errors from individual appends should propagate through gather."""
        store = _make_store()
        events = [_make_event() for _ in range(3)]

        with patch.object(store, "append", new_callable=AsyncMock) as mock_append:
            mock_append.side_effect = [
                "1-0",
                RuntimeError("Redis connection lost"),
                "3-0",
            ]
            with pytest.raises(RuntimeError, match="Redis connection lost"):
                await store.append_batch_concurrent(events)

    @pytest.mark.asyncio()
    async def test_concurrent_passes_tenant_id(self):
        """Tenant ID should be forwarded to each append call."""
        store = _make_store()
        events = [_make_event() for _ in range(3)]

        with patch.object(store, "append", new_callable=AsyncMock) as mock_append:
            mock_append.return_value = "1-0"
            await store.append_batch_concurrent(events, tenant_id="acme")

        for call in mock_append.call_args_list:
            assert call.kwargs.get("tenant_id") == "acme"


# ---------------------------------------------------------------------------
# append_batch delegation
# ---------------------------------------------------------------------------


class TestAppendBatchDelegation:
    """Test that append_batch delegates to concurrent for large batches."""

    @pytest.mark.asyncio()
    async def test_small_batch_uses_pipeline(self):
        """Batches of 10 or fewer should use the pipeline path."""
        store = _make_store()
        events = [_make_event() for _ in range(10)]

        # Mock the pipeline path
        mock_pipe = MagicMock()
        mock_pipe.evalsha = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[b"1-0"] * 10)
        store._client.pipeline = MagicMock(return_value=mock_pipe)

        with patch.object(
            store, "append_batch_concurrent", new_callable=AsyncMock
        ) as mock_concurrent:
            positions = await store.append_batch(events)

        # Should NOT delegate to concurrent
        mock_concurrent.assert_not_called()
        assert len(positions) == 10

    @pytest.mark.asyncio()
    async def test_large_batch_delegates_to_concurrent(self):
        """Batches larger than 10 should delegate to concurrent."""
        store = _make_store()
        events = [_make_event() for _ in range(11)]

        with patch.object(
            store, "append_batch_concurrent", new_callable=AsyncMock
        ) as mock_concurrent:
            mock_concurrent.return_value = [f"{i}-0" for i in range(11)]
            positions = await store.append_batch(events)

        mock_concurrent.assert_called_once()
        assert len(positions) == 11

    @pytest.mark.asyncio()
    async def test_empty_batch_returns_early(self):
        """Empty event list should return immediately without any calls."""
        store = _make_store()

        with patch.object(
            store, "append_batch_concurrent", new_callable=AsyncMock
        ) as mock_concurrent:
            positions = await store.append_batch([])

        mock_concurrent.assert_not_called()
        assert positions == []
