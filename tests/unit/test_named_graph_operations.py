"""Named graph operations replace raw Cypher callers (ADR-0019 C6).

Each operation must send the Cypher and parameters its caller used to
pass through ``run_session_query``; these tests pin them.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.ports.errors import InvalidRequestError


def _store_with_records(records: list[dict[str, Any]]) -> tuple[Neo4jGraphStore, MagicMock]:
    """A Neo4jGraphStore whose driver session.run yields ``records``."""
    store = Neo4jGraphStore.__new__(Neo4jGraphStore)
    session = MagicMock()

    async def _aiter():
        for record in records:
            yield record

    result = MagicMock()
    result.__aiter__ = lambda _self: _aiter()
    session.run = AsyncMock(return_value=result)
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    driver = MagicMock()
    driver.session.return_value = session_cm
    store._driver = driver
    store._database = "neo4j"
    return store, session


class TestNamedOperations:
    @pytest.mark.asyncio()
    async def test_session_agent_id(self) -> None:
        store, session = _store_with_records([{"agent_id": "agent-7"}])
        assert await store.session_agent_id("s1") == "agent-7"
        session.run.assert_awaited_once_with(
            "MATCH (e:Event {session_id: $sid}) RETURN DISTINCT e.agent_id AS agent_id LIMIT 1",
            {"sid": "s1"},
        )

    @pytest.mark.asyncio()
    async def test_session_agent_id_none_without_events(self) -> None:
        store, _session = _store_with_records([])
        assert await store.session_agent_id("s1") is None

    @pytest.mark.asyncio()
    async def test_session_events_returns_node_properties(self) -> None:
        store, session = _store_with_records([{"e": {"event_id": "e1"}}])
        assert await store.session_events("s1", limit=5) == [{"event_id": "e1"}]
        session.run.assert_awaited_once_with(
            "MATCH (e:Event {session_id: $session_id}) "
            "RETURN e ORDER BY e.occurred_at LIMIT $limit",
            {"session_id": "s1", "limit": 5},
        )

    @pytest.mark.asyncio()
    async def test_session_event_timeline(self) -> None:
        row = {"event_id": "e1", "event_type": "tool.execute"}
        store, session = _store_with_records([row])
        assert await store.session_event_timeline("s1") == [row]
        cypher, params = session.run.await_args.args
        assert cypher.startswith("MATCH (e:Event {session_id: $sid}) RETURN e.event_id AS event_id")
        assert params == {"sid": "s1"}

    @pytest.mark.asyncio()
    async def test_events_for_pruning(self) -> None:
        store, session = _store_with_records([])
        await store.events_for_pruning(10_000)
        cypher, params = session.run.await_args.args
        assert "coalesce(e.access_count, 0) AS access_count" in cypher
        assert params == {"batch_limit": 10_000}

    @pytest.mark.asyncio()
    async def test_delete_all_requires_confirm(self) -> None:
        store, session = _store_with_records([])
        with pytest.raises(InvalidRequestError):
            await store.delete_all()
        session.run.assert_not_awaited()

        await store.delete_all(confirm=True)
        session.run.assert_awaited_once_with("MATCH (n) DETACH DELETE n", {})
