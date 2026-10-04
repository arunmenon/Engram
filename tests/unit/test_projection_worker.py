"""Unit tests for context_graph.worker.projection.ProjectionConsumer."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.adapters.memory.subscription import MemorySubscription
from context_graph.domain.models import Event
from context_graph.settings import Settings
from context_graph.worker.projection import ProjectionConsumer
from tests.unit.redis_ports import redis_ports


def _make_settings() -> MagicMock:
    """Create mock Settings matching the expected attribute structure."""
    settings = MagicMock()
    settings.redis.group_projection = "graph-projection"
    settings.redis.global_stream = "events:__global__"
    settings.redis.block_timeout_ms = 5000
    settings.redis.event_key_prefix = "evt:"
    settings.consumer.max_retries = 5
    settings.consumer.claim_idle_ms = 300_000
    settings.consumer.claim_batch_size = 100
    settings.consumer.dlq_stream_suffix = ":dlq"
    return settings


def _make_consumer(
    redis_client: AsyncMock | None = None,
    graph_store: AsyncMock | None = None,
) -> ProjectionConsumer:
    """Build a ProjectionConsumer with mock dependencies."""
    redis_client = redis_client or AsyncMock()
    graph_store = graph_store or AsyncMock()
    settings = _make_settings()
    return ProjectionConsumer(
        **redis_ports(redis_client, settings, "graph-projection", "projection-1"),
        graph_store=graph_store,
        settings=settings,
    )


class TestSessionCacheEviction:
    """Tests for session_last_event cache management."""

    def test_session_end_evicts(self) -> None:
        """Session should be removed from cache on system.session_end event."""
        consumer = _make_consumer()
        # Pre-populate cache
        mock_event = MagicMock(spec=Event)
        mock_event.session_id = "sess-1"
        mock_event.event_type = "tool.execute"
        consumer._session_last_event["sess-1"] = mock_event

        # Simulate session end event processing
        end_event = MagicMock(spec=Event)
        end_event.session_id = "sess-1"
        end_event.event_type = "system.session_end"

        # Manually do what _flush_buffer does for cache management
        consumer._session_last_event[end_event.session_id] = end_event
        if end_event.event_type == "system.session_end":
            consumer._session_last_event.pop(end_event.session_id, None)

        assert "sess-1" not in consumer._session_last_event

    def test_max_sessions_bounded(self) -> None:
        """Session cache should not exceed _MAX_SESSION_CACHE."""
        consumer = _make_consumer()
        # Set a small max for testing
        consumer._MAX_SESSION_CACHE = 5

        # Add more sessions than max
        for i in range(10):
            session_id = f"sess-{i}"
            mock_event = MagicMock(spec=Event)
            mock_event.session_id = session_id
            mock_event.event_type = "tool.execute"
            consumer._session_last_event[session_id] = mock_event
            # Evict if over max (same logic as in _flush_buffer)
            while len(consumer._session_last_event) > consumer._MAX_SESSION_CACHE:
                consumer._session_last_event.popitem(last=False)

        assert len(consumer._session_last_event) == 5
        # Oldest sessions should have been evicted
        assert "sess-0" not in consumer._session_last_event
        assert "sess-9" in consumer._session_last_event

    def test_session_cache_is_ordered_dict(self) -> None:
        """Session cache should be an OrderedDict for LRU behavior."""
        consumer = _make_consumer()
        assert isinstance(consumer._session_last_event, OrderedDict)


class TestMicroBatching:
    """Tests for micro-batching in ProjectionConsumer."""

    def test_buffer_initialized_empty(self) -> None:
        """Buffer should start empty."""
        consumer = _make_consumer()
        assert consumer._buffer == []

    @pytest.mark.asyncio
    async def test_batch_flush_at_size_threshold(self) -> None:
        """Buffer should flush when reaching BATCH_SIZE."""
        redis_mock = AsyncMock()
        graph_mock = AsyncMock()
        consumer = _make_consumer(redis_client=redis_mock, graph_store=graph_mock)
        consumer._BATCH_SIZE = 3
        consumer._BATCH_TIMEOUT_MS = 10_000  # high timeout so only size triggers

        # Mock _fetch_event to return None (skip actual processing but test buffering)
        with patch.object(consumer, "_fetch_event", new_callable=AsyncMock, return_value=None):
            for i in range(3):
                await consumer.process_message(f"entry-{i}", {"event_id": f"evt-{i}"})

        # Buffer should have been flushed (now empty)
        assert consumer._buffer == []

    @pytest.mark.asyncio
    async def test_batch_flush_at_timeout(self) -> None:
        """Buffer should flush when timeout has elapsed."""
        redis_mock = AsyncMock()
        graph_mock = AsyncMock()
        consumer = _make_consumer(redis_client=redis_mock, graph_store=graph_mock)
        consumer._BATCH_SIZE = 100  # high size so only timeout triggers
        consumer._BATCH_TIMEOUT_MS = 0  # immediate timeout

        with patch.object(consumer, "_fetch_event", new_callable=AsyncMock, return_value=None):
            # Set last flush time in the past
            consumer._last_flush_time = 0.0
            await consumer.process_message("entry-0", {"event_id": "evt-0"})

        # Buffer should have been flushed due to timeout
        assert consumer._buffer == []

    @pytest.mark.asyncio
    async def test_merge_event_nodes_batch_called(self) -> None:
        """When graph store has merge_event_nodes_batch, it should be used."""
        redis_mock = AsyncMock()
        graph_mock = AsyncMock()
        graph_mock.merge_event_nodes_batch = AsyncMock()
        consumer = _make_consumer(redis_client=redis_mock, graph_store=graph_mock)
        consumer._BATCH_SIZE = 1  # flush immediately
        consumer._BATCH_TIMEOUT_MS = 10_000

        mock_event = MagicMock(spec=Event)
        mock_event.session_id = "sess-1"
        mock_event.event_id = "evt-1"
        mock_event.event_type = "tool.execute"
        mock_event.global_position = "100-0"

        fetch_patch = patch.object(
            consumer, "_fetch_event", new_callable=AsyncMock, return_value=mock_event
        )
        project_patch = patch("context_graph.worker.projection.project_event")
        with fetch_patch, project_patch as mock_project:
            mock_result = MagicMock()
            mock_result.node = MagicMock()
            mock_result.edges = []
            mock_project.return_value = mock_result
            await consumer.process_message("entry-0", {"event_id": "evt-1"})

        graph_mock.merge_event_nodes_batch.assert_called_once()


def _event(session_id: str, minutes_ago: int) -> Event:
    return Event(
        event_id=uuid4(),
        event_type="tool.execute",
        occurred_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        session_id=session_id,
        agent_id="agent-1",
        trace_id="trace-1",
        payload_ref="payload:1",
        tool_name="grep",
    )


class TestIdleFlush:
    """A partial batch is projected and acked once deliveries stop (no stop() needed)."""

    @staticmethod
    def _in_memory_consumer(
        monkeypatch: pytest.MonkeyPatch,
    ) -> tuple[ProjectionConsumer, MemoryEventLog, MemoryGraphStore, MemorySubscription]:
        monkeypatch.setenv("CG_CONSUMER_BLOCK_TIMEOUT_MS", "20")
        settings = Settings()
        event_log = MemoryEventLog()
        graph_store = MemoryGraphStore()
        subscription = MemorySubscription(
            event_log.stream, settings.consumer.group_projection, "projection-1"
        )
        consumer = ProjectionConsumer(
            subscription=subscription,
            event_log=event_log,
            graph_store=graph_store,
            settings=settings,
        )
        return consumer, event_log, graph_store, subscription

    @pytest.mark.asyncio
    async def test_burst_below_batch_size_is_projected_and_acked_while_running(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        consumer, event_log, graph_store, subscription = self._in_memory_consumer(monkeypatch)
        task = asyncio.create_task(consumer.run())
        try:
            burst = [_event("sess-idle", minutes_ago=3 - i) for i in range(3)]
            assert len(burst) < consumer._BATCH_SIZE
            for event in burst:
                await event_log.append(event)

            projected_ids = {str(event.event_id) for event in burst}
            for _ in range(100):
                await asyncio.sleep(0.02)
                graph_ids = {node_id for label, node_id in graph_store.nodes if label == "Event"}
                pending = await subscription.delivery_counts(100)
                if projected_ids <= graph_ids and not pending:
                    break

            # Projected and acked while the worker keeps running: no new
            # delivery arrived and stop() was never called.
            assert not task.done()
            assert not consumer._stopped
            assert projected_ids <= graph_ids
            assert pending == {}
            assert await subscription.lag() == 0
            assert consumer._buffer == []
        finally:
            consumer.stop()
            await asyncio.wait_for(task, timeout=5)

    @pytest.mark.asyncio
    async def test_idle_waits_for_batch_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        consumer, _event_log, _graph_store, _subscription = self._in_memory_consumer(monkeypatch)
        consumer._BATCH_TIMEOUT_MS = 60_000
        consumer._buffer.append(("1-0", {"event_id": "evt-1"}))
        with patch.object(consumer, "_flush_buffer", new_callable=AsyncMock) as flush:
            await consumer.on_idle()
        flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_idle_flush_failure_leaves_items_unacked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        consumer, event_log, graph_store, subscription = self._in_memory_consumer(monkeypatch)
        await subscription.ensure_group()
        await event_log.append(_event("sess-fail", minutes_ago=1))
        (delivery,) = await subscription.read_new(10, 0)
        await consumer.process_message(delivery.position, delivery.fields)
        consumer._last_flush_time = 0.0

        failing = AsyncMock(side_effect=RuntimeError("graph down"))
        with (
            patch.object(graph_store, "merge_event_nodes_batch", failing),
            pytest.raises(RuntimeError),
        ):
            await consumer.on_idle()

        assert delivery.position in await subscription.delivery_counts(100)


class TestFollowsAcrossRestart:
    """FOLLOWS edges do not depend on which worker process projected the previous event."""

    @staticmethod
    async def _project(
        event_log: MemoryEventLog, graph_store: MemoryGraphStore, settings: Settings
    ) -> None:
        """Run a fresh worker (an empty session cache) until the group is drained."""
        subscription = MemorySubscription(
            event_log.stream, settings.consumer.group_projection, "projection-1"
        )
        consumer = ProjectionConsumer(
            subscription=subscription,
            event_log=event_log,
            graph_store=graph_store,
            settings=settings,
        )
        task = asyncio.create_task(consumer.run())
        try:
            for _ in range(200):
                await asyncio.sleep(0.02)
                if await subscription.lag() == 0 and not await subscription.delivery_counts(100):
                    break
        finally:
            consumer.stop()
            await asyncio.wait_for(task, timeout=5)

    @staticmethod
    def _follows(graph_store: MemoryGraphStore) -> dict[tuple[str, str], dict[str, object]]:
        return {
            (source[1], target[1]): props
            for (source, edge_type, target), props in graph_store.edges.items()
            if edge_type == "FOLLOWS"
        }

    @staticmethod
    def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
        monkeypatch.setenv("CG_CONSUMER_BLOCK_TIMEOUT_MS", "20")
        return Settings()

    @pytest.mark.asyncio
    async def test_restart_mid_session_matches_one_uninterrupted_run(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings = self._settings(monkeypatch)
        events = [_event("sess-restart", minutes_ago=10 - i) for i in range(5)]

        restarted_log, restarted_graph = MemoryEventLog(), MemoryGraphStore()
        for event in events[:3]:
            await restarted_log.append(event)
        await self._project(restarted_log, restarted_graph, settings)
        for event in events[3:]:
            await restarted_log.append(event)
        await self._project(restarted_log, restarted_graph, settings)  # new process

        single_log, single_graph = MemoryEventLog(), MemoryGraphStore()
        for event in events:
            await single_log.append(event)
        await self._project(single_log, single_graph, settings)

        follows = self._follows(restarted_graph)
        assert follows == self._follows(single_graph)
        across = (str(events[3].event_id), str(events[2].event_id))
        assert across in follows
        assert follows[across]["delta_ms"] == 60_000
        assert len(follows) == 4

    @pytest.mark.asyncio
    async def test_no_follows_after_session_end_on_either_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings = self._settings(monkeypatch)
        first = _event("sess-ended", minutes_ago=3)
        end = _event("sess-ended", minutes_ago=2).model_copy(
            update={"event_type": "system.session_end"}
        )
        late = _event("sess-ended", minutes_ago=1)

        restarted_log, restarted_graph = MemoryEventLog(), MemoryGraphStore()
        await restarted_log.append(first)
        await restarted_log.append(end)
        await self._project(restarted_log, restarted_graph, settings)
        await restarted_log.append(late)
        await self._project(restarted_log, restarted_graph, settings)

        single_log, single_graph = MemoryEventLog(), MemoryGraphStore()
        for event in (first, end, late):
            await single_log.append(event)
        await self._project(single_log, single_graph, settings)

        assert self._follows(restarted_graph) == self._follows(single_graph)
        assert set(self._follows(restarted_graph)) == {(str(end.event_id), str(first.event_id))}

    @pytest.mark.asyncio
    async def test_first_event_of_a_session_has_no_previous(self) -> None:
        event_log = MemoryEventLog()
        event = _event("sess-new", minutes_ago=1)
        await event_log.append(event)
        consumer = ProjectionConsumer(
            subscription=MemorySubscription(event_log.stream, "graph-projection", "p"),
            event_log=event_log,
            graph_store=MemoryGraphStore(),
            settings=Settings(),
        )
        assert await consumer._previous_event(event) is None


class TestPackFailureIsolation:
    """A pack-rule failure dead-letters its own event, not the batch (phase 1 review)."""

    @pytest.mark.asyncio
    async def test_one_failing_event_is_dead_lettered_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from context_graph.domain.pack_projection import ProjectionPlan

        class Projector:
            def handles(self, event_type: str) -> bool:
                return True

            def plan(self, event: Event, document: dict[str, object]) -> ProjectionPlan:
                if event.session_id == "sess-bad":
                    msg = "pack rule failed"
                    raise RuntimeError(msg)
                return ProjectionPlan()

        monkeypatch.setenv("CG_CONSUMER_BLOCK_TIMEOUT_MS", "20")
        settings = Settings()
        event_log = MemoryEventLog()
        subscription = MemorySubscription(
            event_log.stream, settings.consumer.group_projection, "projection-1"
        )
        consumer = ProjectionConsumer(
            subscription=subscription,
            event_log=event_log,
            graph_store=MemoryGraphStore(),
            settings=settings,
            pack_projector=Projector(),  # type: ignore[arg-type]
        )
        good, bad = _event("sess-good", minutes_ago=2), _event("sess-bad", minutes_ago=1)
        await event_log.append(good)
        await event_log.append(bad)
        await subscription.ensure_group()
        for delivery in await subscription.read_new(10, 0):
            await consumer.process_message(delivery.position, delivery.fields)
        await consumer._flush_buffer()

        assert await subscription.delivery_counts(100) == {}  # all acknowledged
        dead = event_log.stream.dead_letters
        assert [d["event_id"] for d in dead] == [str(bad.event_id)]
