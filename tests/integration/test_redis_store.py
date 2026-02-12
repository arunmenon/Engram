"""Integration tests for RedisEventStore.

Requires a running Redis Stack instance at localhost:6379.
Run with: pytest tests/integration/test_redis_store.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from context_graph.adapters.redis.store import RedisEventStore
from context_graph.domain.models import EventQuery
from context_graph.settings import RedisSettings
from tests.fixtures.events import make_event, make_tool_event

pytestmark = pytest.mark.integration


@pytest.fixture()
async def redis_store():
    """Provide a connected RedisEventStore and clean up after the test."""
    settings = RedisSettings()
    store = await RedisEventStore.create(settings)
    await store.ensure_indexes()
    yield store
    await store.close()


@pytest.fixture()
def unique_session_id() -> str:
    """Generate a unique session ID to isolate test data."""
    return f"test-session-{uuid4().hex[:12]}"


class TestAppendAndGetById:
    """Test basic append and retrieval by ID."""

    async def test_roundtrip_event(self, redis_store: RedisEventStore) -> None:
        """Append an event and retrieve it by ID — fields should match."""
        event = make_event()
        global_position = await redis_store.append(event)

        assert global_position is not None
        assert "-" in global_position  # Stream entry ID format: "timestamp-seq"

        retrieved = await redis_store.get_by_id(str(event.event_id))
        assert retrieved is not None
        assert retrieved.event_id == event.event_id
        assert retrieved.event_type == event.event_type
        assert retrieved.session_id == event.session_id
        assert retrieved.agent_id == event.agent_id
        assert retrieved.trace_id == event.trace_id
        assert retrieved.payload_ref == event.payload_ref
        assert retrieved.global_position == global_position

    async def test_get_by_id_not_found(self, redis_store: RedisEventStore) -> None:
        """Querying a nonexistent event_id returns None."""
        result = await redis_store.get_by_id(str(uuid4()))
        assert result is None


class TestAppendDedup:
    """Test idempotent ingestion."""

    async def test_same_event_id_returns_same_position(self, redis_store: RedisEventStore) -> None:
        """Appending the same event_id twice returns the same global_position."""
        event = make_event()
        position_first = await redis_store.append(event)
        position_second = await redis_store.append(event)

        assert position_first == position_second

    async def test_dedup_preserves_original_data(self, redis_store: RedisEventStore) -> None:
        """After dedup, the stored event still matches the original."""
        event = make_event()
        await redis_store.append(event)
        await redis_store.append(event)  # duplicate

        retrieved = await redis_store.get_by_id(str(event.event_id))
        assert retrieved is not None
        assert retrieved.event_id == event.event_id


class TestGetBySession:
    """Test session-based retrieval with ordering."""

    async def test_events_ordered_by_occurred_at(
        self,
        redis_store: RedisEventStore,
        unique_session_id: str,
    ) -> None:
        """Events for a session are returned in occurred_at ascending order."""
        base_time = datetime.now(UTC)
        events = []
        for i in range(5):
            event = make_event(
                session_id=unique_session_id,
                occurred_at=base_time + timedelta(seconds=i),
            )
            await redis_store.append(event)
            events.append(event)

        # RediSearch index needs a moment to catch up
        import asyncio

        await asyncio.sleep(0.5)

        retrieved = await redis_store.get_by_session(unique_session_id, limit=10)
        assert len(retrieved) == 5

        # Verify ascending order by occurred_at
        for idx in range(1, len(retrieved)):
            assert retrieved[idx].occurred_at >= retrieved[idx - 1].occurred_at

    async def test_limit_respected(
        self,
        redis_store: RedisEventStore,
        unique_session_id: str,
    ) -> None:
        """The limit parameter caps the number of returned events."""
        base_time = datetime.now(UTC)
        for i in range(5):
            event = make_event(
                session_id=unique_session_id,
                occurred_at=base_time + timedelta(seconds=i),
            )
            await redis_store.append(event)

        import asyncio

        await asyncio.sleep(0.5)

        retrieved = await redis_store.get_by_session(unique_session_id, limit=3)
        assert len(retrieved) == 3


class TestSearchByFilters:
    """Test composite search queries."""

    async def test_search_by_event_type(
        self,
        redis_store: RedisEventStore,
        unique_session_id: str,
    ) -> None:
        """Search filtered by event_type returns only matching events."""
        tool_event = make_tool_event(
            session_id=unique_session_id,
            tool_name="search-tool",
        )
        agent_event = make_event(
            session_id=unique_session_id,
            event_type="agent.invoke",
        )
        await redis_store.append(tool_event)
        await redis_store.append(agent_event)

        import asyncio

        await asyncio.sleep(0.5)

        query = EventQuery(
            session_id=unique_session_id,
            event_type="tool.execute",
        )
        results = await redis_store.search(query)
        assert len(results) == 1
        assert results[0].event_type == "tool.execute"

    async def test_search_by_tool_name(
        self,
        redis_store: RedisEventStore,
        unique_session_id: str,
    ) -> None:
        """Search filtered by tool_name returns only matching events."""
        event_a = make_tool_event(
            session_id=unique_session_id,
            tool_name="calculator",
        )
        event_b = make_tool_event(
            session_id=unique_session_id,
            tool_name="browser",
        )
        await redis_store.append(event_a)
        await redis_store.append(event_b)

        import asyncio

        await asyncio.sleep(0.5)

        query = EventQuery(
            session_id=unique_session_id,
            tool_name="calculator",
        )
        results = await redis_store.search(query)
        assert len(results) == 1
        assert results[0].tool_name == "calculator"

    async def test_search_with_time_range(
        self,
        redis_store: RedisEventStore,
        unique_session_id: str,
    ) -> None:
        """Search with after/before time bounds filters correctly."""
        base_time = datetime.now(UTC)
        early_event = make_event(
            session_id=unique_session_id,
            occurred_at=base_time - timedelta(hours=2),
        )
        recent_event = make_event(
            session_id=unique_session_id,
            occurred_at=base_time,
        )
        await redis_store.append(early_event)
        await redis_store.append(recent_event)

        import asyncio

        await asyncio.sleep(0.5)

        query = EventQuery(
            session_id=unique_session_id,
            after=base_time - timedelta(hours=1),
        )
        results = await redis_store.search(query)
        assert len(results) == 1
        assert results[0].event_id == recent_event.event_id


class TestAppendBatch:
    """Test batch append."""

    async def test_batch_returns_positions_for_all(
        self,
        redis_store: RedisEventStore,
    ) -> None:
        """append_batch returns a position for each event."""
        events = [make_event() for _ in range(3)]
        positions = await redis_store.append_batch(events)

        assert len(positions) == 3
        for position in positions:
            assert "-" in position  # Stream entry ID format

    async def test_batch_events_retrievable(
        self,
        redis_store: RedisEventStore,
    ) -> None:
        """All events from a batch are individually retrievable."""
        events = [make_event() for _ in range(3)]
        await redis_store.append_batch(events)

        for event in events:
            retrieved = await redis_store.get_by_id(str(event.event_id))
            assert retrieved is not None
            assert retrieved.event_id == event.event_id


class TestEnsureIndexes:
    """Test index creation."""

    async def test_ensure_indexes_idempotent(
        self,
        redis_store: RedisEventStore,
    ) -> None:
        """Calling ensure_indexes multiple times does not raise."""
        # First call already done in fixture; call again to verify idempotency
        await redis_store.ensure_indexes()
        await redis_store.ensure_indexes()
        # If no exception, the test passes
