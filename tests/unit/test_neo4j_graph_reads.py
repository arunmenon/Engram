"""Neo4jGraphReads sends the Cypher the retrieval code used to inline (ADR-0019)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.neo4j import queries
from context_graph.adapters.neo4j.graph_reads import (
    GET_EVENT_NODES,
    GET_SESSION_EVENTS_AFTER,
    SEED_STRATEGY_QUERIES,
    Neo4jGraphReads,
)
from context_graph.ports.graph_reads import SEED_STRATEGIES


def _reads(records: list[Any]) -> tuple[Neo4jGraphReads, MagicMock]:
    session = MagicMock()

    async def _aiter():
        for record in records:
            yield record

    result = MagicMock()
    result.__aiter__ = lambda _self: _aiter()
    session.run = AsyncMock(return_value=result)
    session.execute_write = AsyncMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    driver = MagicMock()
    driver.session.return_value = session_cm
    return Neo4jGraphReads(driver, "neo4j"), session


def test_every_port_strategy_has_a_query() -> None:
    assert set(SEED_STRATEGY_QUERIES) == set(SEED_STRATEGIES)


@pytest.mark.asyncio()
async def test_seed_events_unknown_strategy_uses_general() -> None:
    reads, session = _reads([{"e": {"event_id": "e1"}}])
    rows = await reads.seed_events("nope", "s1", 5, timeout_s=2.0)
    assert rows == [{"event_id": "e1"}]
    session.run.assert_awaited_once_with(
        queries.GET_SUBGRAPH_SEED_EVENTS, {"session_id": "s1", "seed_limit": 5}, timeout=2.0
    )


@pytest.mark.asyncio()
async def test_get_event_nodes() -> None:
    reads, session = _reads([{"e": {"event_id": "e1"}}])
    assert await reads.get_event_nodes(["e1"], timeout_s=1.0) == [{"event_id": "e1"}]
    session.run.assert_awaited_once_with(GET_EVENT_NODES, {"eids": ["e1"]}, timeout=1.0)


@pytest.mark.asyncio()
async def test_session_events_page_without_and_with_cursor() -> None:
    reads, session = _reads([])
    await reads.session_events_page("s1", 11, timeout_s=5.0)
    session.run.assert_awaited_with(
        queries.GET_SESSION_EVENTS, {"session_id": "s1", "limit": 11}, timeout=5.0
    )
    await reads.session_events_page("s1", 11, after=("2026-01-01", "e9"), timeout_s=5.0)
    session.run.assert_awaited_with(
        GET_SESSION_EVENTS_AFTER,
        {"session_id": "s1", "cursor_ts": "2026-01-01", "cursor_id": "e9", "limit": 11},
        timeout=5.0,
    )


@pytest.mark.asyncio()
async def test_neighbors_rows_are_plain_dicts() -> None:
    record = MagicMock()
    record.get.side_effect = lambda key: {"seed_event_id": "e1", "rel_type": "FOLLOWS"}.get(key)
    reads, _session = _reads([record])
    rows = await reads.event_neighbors(["e1"], 50)
    assert rows[0]["seed_event_id"] == "e1"
    assert rows[0]["rel_type"] == "FOLLOWS"
    assert rows[0]["neighbor_props"] is None


@pytest.mark.asyncio()
async def test_lineage_chains_flatten_relationships() -> None:
    rel = MagicMock()
    rel.start_node = {"event_id": "e1"}
    rel.end_node = {"event_id": "e0"}
    rel.__iter__ = lambda _self: iter([("reason", "x")])
    rel.keys = lambda: ["reason"]
    rel.__getitem__ = lambda _self, key: "x"
    record = {"chain_nodes": [{"event_id": "e1"}, {"event_id": "e0"}], "chain_rels": [rel]}
    reads, session = _reads([record])
    chains = await reads.lineage_chains("e1", 3, 11, timeout_s=5.0)
    session.run.assert_awaited_once_with(
        queries.GET_LINEAGE, {"node_id": "e1", "max_depth": 3, "max_nodes": 11}, timeout=5.0
    )
    assert chains[0]["nodes"] == [{"event_id": "e1"}, {"event_id": "e0"}]
    assert chains[0]["edges"][0]["source"] == "e1"
    assert chains[0]["edges"][0]["target"] == "e0"


@pytest.mark.asyncio()
async def test_record_access_skips_empty() -> None:
    reads, session = _reads([])
    await reads.record_access([], "2026-01-01T00:00:00+00:00")
    session.execute_write.assert_not_awaited()
    await reads.record_access(["e1"], "2026-01-01T00:00:00+00:00")
    session.execute_write.assert_awaited_once()
