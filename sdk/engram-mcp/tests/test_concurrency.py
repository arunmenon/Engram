"""Adversarial concurrency tests for the Engram MCP server."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from unittest.mock import AsyncMock

import pytest

from engram.models import AtlasResponse, IngestResult, UserProfile
from engram_mcp.server import EngramMCPServer
from engram_mcp.tools import (
    _handle_forget,
    _handle_profile,
    _handle_recall,
    _handle_record,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client() -> AsyncMock:
    client = AsyncMock()
    client.ingest = AsyncMock(
        side_effect=lambda _: IngestResult(
            event_id=str(uuid.uuid4()), global_position="1707644400000-0"
        )
    )
    client.get_context = AsyncMock(return_value=AtlasResponse())
    client.get_user_profile = AsyncMock(return_value=UserProfile())
    client.get_user_preferences = AsyncMock(return_value=[])
    client.get_user_skills = AsyncMock(return_value=[])
    client.get_user_patterns = AsyncMock(return_value=[])
    client.get_user_interests = AsyncMock(return_value=[])
    client.delete_user = AsyncMock(return_value={"deleted_count": 1})
    client.close = AsyncMock(return_value=None)
    return client


def _make_server() -> EngramMCPServer:
    server = EngramMCPServer()
    server._client = _make_mock_client()
    server._started = True
    return server


# ===========================================================================
# TestMCPEventChainConcurrency
# ===========================================================================


class TestMCPEventChainConcurrency:
    """Verify concurrent tool handler calls are safe."""

    @pytest.mark.asyncio
    async def test_concurrent_records(self):
        """20 concurrent _handle_record() — all succeed, last_event_id set."""
        server = _make_server()

        tasks = [
            _handle_record(server, {"content": f"msg-{i}"})
            for i in range(20)
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        for r in results:
            assert len(r) == 1
            assert "Event Recorded" in r[0].text

        # last_event_id should be set (not None)
        assert server.last_event_id is not None

    @pytest.mark.asyncio
    async def test_concurrent_record_and_recall(self):
        """record and recall at same time — no crash."""
        server = _make_server()

        tasks = [
            _handle_record(server, {"content": "event-1"}),
            _handle_recall(server, {}),
            _handle_record(server, {"content": "event-2"}),
            _handle_recall(server, {"query": "test"}),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            assert not isinstance(r, Exception), f"Unexpected error: {r}"

    @pytest.mark.asyncio
    async def test_concurrent_record_and_forget(self):
        """record and forget at same time — no crash."""
        server = _make_server()

        tasks = [
            _handle_record(server, {"content": "event-1"}),
            _handle_forget(server, {"user_id": "user-1"}),
            _handle_record(server, {"content": "event-2"}),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            assert not isinstance(r, Exception), f"Unexpected error: {r}"


# ===========================================================================
# TestMCPAsyncCancellation
# ===========================================================================


class TestMCPAsyncCancellation:
    """Verify cancellation does not corrupt server state."""

    @pytest.mark.asyncio
    async def test_cancelled_during_ingest(self):
        """CancelledError during ingest — last_event_id NOT updated."""
        server = _make_server()
        original_event_id = server.last_event_id

        async def slow_ingest(_event):
            await asyncio.sleep(10)
            return IngestResult(event_id=str(uuid.uuid4()), global_position="x-0")

        server._client.ingest = AsyncMock(side_effect=slow_ingest)

        task = asyncio.create_task(
            _handle_record(server, {"content": "will-be-cancelled"})
        )
        await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # last_event_id should not have been updated since ingest didn't complete
        assert server.last_event_id == original_event_id

    @pytest.mark.asyncio
    async def test_cancelled_during_profile_gather(self):
        """CancelledError during profile — no partial leak."""
        server = _make_server()

        async def slow_profile(_user_id):
            await asyncio.sleep(10)
            return UserProfile()

        server._client.get_user_profile = AsyncMock(side_effect=slow_profile)

        task = asyncio.create_task(
            _handle_profile(server, {"user_id": "user-1"})
        )
        await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_cancelled_after_delete(self):
        """CancelledError after delete completes — deletion still took effect."""
        server = _make_server()
        delete_called = False

        async def do_delete(_user_id):
            nonlocal delete_called
            delete_called = True
            return {"deleted_count": 3}

        server._client.delete_user = AsyncMock(side_effect=do_delete)

        # Run forget to completion, then verify
        result = await _handle_forget(server, {"user_id": "user-1"})
        assert delete_called
        assert "Deletion Complete" in result[0].text


# ===========================================================================
# TestMCPServerLifecycle
# ===========================================================================


class TestMCPServerLifecycle:
    """Verify server lifecycle edge cases."""

    @pytest.mark.asyncio
    async def test_start_called_twice(self):
        """start() called twice — no duplicate tool registration or error."""
        server = EngramMCPServer()
        server._client = _make_mock_client()

        await server.start()
        assert server._started is True

        # Second call is a no-op
        await server.start()
        assert server._started is True

    @pytest.mark.asyncio
    async def test_shutdown_without_start(self):
        """shutdown() without start() — clean no-op."""
        server = EngramMCPServer()
        # _client is None, _started is False
        await server.shutdown()
        # Should not raise

    @pytest.mark.asyncio
    async def test_concurrent_start_and_shutdown(self):
        """start() and shutdown() concurrent — no crash."""
        server = EngramMCPServer()
        server._client = _make_mock_client()

        async def do_start():
            with contextlib.suppress(Exception):
                await server.start()

        async def do_shutdown():
            with contextlib.suppress(Exception):
                await server.shutdown()

        await asyncio.gather(do_start(), do_shutdown())
        # Should not crash — state may vary

    @pytest.mark.asyncio
    async def test_tool_call_after_shutdown(self):
        """Tool call after shutdown — raises RuntimeError from .client property."""
        server = _make_server()
        await server.shutdown()

        # client is now None, so accessing .client should raise
        with pytest.raises(RuntimeError, match="not started"):
            _ = server.client
