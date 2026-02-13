"""Integration tests for re-consolidation flow.

Creates events in Neo4j, runs consolidation, and verifies Summary nodes
and SUMMARIZES edges are created correctly.

Requires Neo4j running at bolt://localhost:7687 (docker-compose up).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context_graph.adapters.neo4j import maintenance
from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.domain.consolidation import (
    create_summary_from_events,
    group_events_into_episodes,
    should_reconsolidate,
)
from context_graph.domain.models import EventNode
from context_graph.settings import Neo4jSettings


@pytest.fixture
async def neo4j_store():
    """Provide a Neo4jGraphStore connected to the test database, clean up after."""
    settings = Neo4jSettings()
    store = Neo4jGraphStore(settings)
    await store.ensure_constraints()

    yield store

    # Teardown: delete all test data
    async with store._driver.session(database=store._database) as session:
        await session.run("MATCH (n) DETACH DELETE n")

    await store.close()


def _make_event_node(
    event_id: str,
    session_id: str = "consolidation-sess",
    occurred_at: datetime | None = None,
    event_type: str = "tool.execute",
) -> EventNode:
    """Build an EventNode with sensible defaults."""
    return EventNode(
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at or datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
        session_id=session_id,
        agent_id="agent-001",
        trace_id="trace-001",
        global_position=f"170764440{event_id[-4:]}-0",
    )


@pytest.mark.integration
class TestConsolidationFlow:
    """End-to-end: create events, consolidate, verify summaries."""

    async def test_create_events_and_consolidate(self, neo4j_store: Neo4jGraphStore) -> None:
        """Insert 6 events for a session, consolidate, verify summary + edges."""
        session_id = "consolidation-test-sess"
        base_time = datetime(2024, 2, 11, 10, 0, 0, tzinfo=UTC)

        # Create 6 event nodes in Neo4j
        event_ids = []
        event_dicts = []
        for i in range(6):
            eid = f"evt-consol-{i:03d}"
            occurred_at = base_time + timedelta(minutes=i * 5)
            node = _make_event_node(
                event_id=eid,
                session_id=session_id,
                occurred_at=occurred_at,
                event_type="tool.execute" if i % 2 == 0 else "agent.invoke",
            )
            await neo4j_store.merge_event_node(node)
            event_ids.append(eid)
            event_dicts.append(
                {
                    "event_id": eid,
                    "event_type": node.event_type,
                    "occurred_at": occurred_at.isoformat(),
                }
            )

        # Verify events exist in Neo4j
        session_counts = await maintenance.get_session_event_counts(
            neo4j_store._driver,
            neo4j_store._database,
        )
        assert session_counts.get(session_id) == 6

        # Group events into episodes (all within 5 min gap, should be 1 episode)
        episodes = group_events_into_episodes(event_dicts, gap_minutes=30)
        assert len(episodes) == 1
        assert len(episodes[0]) == 6

        # Create summary from the episode
        summary = create_summary_from_events(
            episodes[0],
            scope="session",
            scope_id=session_id,
        )
        assert summary.event_count == 6
        assert "agent.invoke" in summary.content
        assert "tool.execute" in summary.content

        # Write summary + SUMMARIZES edges to Neo4j
        await maintenance.write_summary_with_edges(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
            summary_id=summary.summary_id,
            scope=summary.scope,
            scope_id=summary.scope_id,
            content=summary.content,
            created_at=summary.created_at.isoformat(),
            event_count=summary.event_count,
            time_range=[dt.isoformat() for dt in summary.time_range],
            event_ids=event_ids,
        )

        # Verify the summary node exists
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (s:Summary {summary_id: $sid}) RETURN s",
                {"sid": summary.summary_id},
            )
            records = [record async for record in result]

        assert len(records) == 1
        summary_props = records[0]["s"]
        assert summary_props["scope"] == "session"
        assert summary_props["scope_id"] == session_id
        assert summary_props["event_count"] == 6

        # Verify SUMMARIZES edges exist to all 6 events
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (s:Summary {summary_id: $sid})-[r:SUMMARIZES]->(e:Event) "
                "RETURN e.event_id AS eid",
                {"sid": summary.summary_id},
            )
            edge_records = [record async for record in result]

        summarized_eids = {r["eid"] for r in edge_records}
        assert summarized_eids == set(event_ids)

    async def test_multiple_episodes_from_gap(self, neo4j_store: Neo4jGraphStore) -> None:
        """Events with a 2-hour gap form two separate episodes."""
        session_id = "episode-gap-sess"
        base_time = datetime(2024, 2, 11, 10, 0, 0, tzinfo=UTC)

        event_dicts = []
        event_ids = []
        # Episode 1: events 0-2 at 0, 5, 10 minutes
        for i in range(3):
            eid = f"evt-gap-{i:03d}"
            occurred_at = base_time + timedelta(minutes=i * 5)
            node = _make_event_node(
                event_id=eid,
                session_id=session_id,
                occurred_at=occurred_at,
            )
            await neo4j_store.merge_event_node(node)
            event_ids.append(eid)
            event_dicts.append(
                {
                    "event_id": eid,
                    "event_type": "tool.execute",
                    "occurred_at": occurred_at.isoformat(),
                }
            )

        # Episode 2: events 3-5 at 120, 125, 130 minutes (2-hour gap)
        for i in range(3, 6):
            eid = f"evt-gap-{i:03d}"
            occurred_at = base_time + timedelta(minutes=120 + (i - 3) * 5)
            node = _make_event_node(
                event_id=eid,
                session_id=session_id,
                occurred_at=occurred_at,
            )
            await neo4j_store.merge_event_node(node)
            event_ids.append(eid)
            event_dicts.append(
                {
                    "event_id": eid,
                    "event_type": "tool.execute",
                    "occurred_at": occurred_at.isoformat(),
                }
            )

        episodes = group_events_into_episodes(event_dicts, gap_minutes=30)
        assert len(episodes) == 2
        assert len(episodes[0]) == 3
        assert len(episodes[1]) == 3

        # Create summaries for each episode
        for episode in episodes:
            summary = create_summary_from_events(
                episode,
                scope="session",
                scope_id=session_id,
            )
            ep_event_ids = [e["event_id"] for e in episode]
            await maintenance.write_summary_with_edges(
                driver=neo4j_store._driver,
                database=neo4j_store._database,
                summary_id=summary.summary_id,
                scope=summary.scope,
                scope_id=summary.scope_id,
                content=summary.content,
                created_at=summary.created_at.isoformat(),
                event_count=summary.event_count,
                time_range=[dt.isoformat() for dt in summary.time_range],
                event_ids=ep_event_ids,
            )

        # Verify 2 summary nodes created
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (s:Summary {scope_id: $sid}) RETURN count(s) AS cnt",
                {"sid": session_id},
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 2

    async def test_should_reconsolidate_threshold(self) -> None:
        """Verify the threshold check function works correctly."""
        assert should_reconsolidate(200, threshold=150) is True
        assert should_reconsolidate(150, threshold=150) is True
        assert should_reconsolidate(149, threshold=150) is False
        assert should_reconsolidate(0, threshold=150) is False

    async def test_consolidation_idempotent(self, neo4j_store: Neo4jGraphStore) -> None:
        """Writing the same summary twice should not duplicate."""
        session_id = "idempotent-sess"
        base_time = datetime(2024, 2, 11, 10, 0, 0, tzinfo=UTC)

        event_ids = []
        event_dicts = []
        for i in range(3):
            eid = f"evt-idem-{i:03d}"
            occurred_at = base_time + timedelta(minutes=i * 5)
            node = _make_event_node(
                event_id=eid,
                session_id=session_id,
                occurred_at=occurred_at,
            )
            await neo4j_store.merge_event_node(node)
            event_ids.append(eid)
            event_dicts.append(
                {
                    "event_id": eid,
                    "event_type": "tool.execute",
                    "occurred_at": occurred_at.isoformat(),
                }
            )

        summary = create_summary_from_events(event_dicts, scope="session", scope_id=session_id)

        # Write twice
        for _ in range(2):
            await maintenance.write_summary_with_edges(
                driver=neo4j_store._driver,
                database=neo4j_store._database,
                summary_id=summary.summary_id,
                scope=summary.scope,
                scope_id=summary.scope_id,
                content=summary.content,
                created_at=summary.created_at.isoformat(),
                event_count=summary.event_count,
                time_range=[dt.isoformat() for dt in summary.time_range],
                event_ids=event_ids,
            )

        # Should still be 1 summary node
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (s:Summary {summary_id: $sid}) RETURN count(s) AS cnt",
                {"sid": summary.summary_id},
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 1

        # Should still have 3 SUMMARIZES edges (MERGE is idempotent)
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (s:Summary {summary_id: $sid})-[r:SUMMARIZES]->(e:Event) "
                "RETURN count(r) AS cnt",
                {"sid": summary.summary_id},
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 3

    async def test_graph_stats_after_consolidation(self, neo4j_store: Neo4jGraphStore) -> None:
        """Graph stats should reflect new Summary nodes and SUMMARIZES edges."""
        session_id = "stats-sess"
        base_time = datetime(2024, 2, 11, 10, 0, 0, tzinfo=UTC)

        event_ids = []
        event_dicts = []
        for i in range(3):
            eid = f"evt-stats-{i:03d}"
            occurred_at = base_time + timedelta(minutes=i * 5)
            node = _make_event_node(
                event_id=eid,
                session_id=session_id,
                occurred_at=occurred_at,
            )
            await neo4j_store.merge_event_node(node)
            event_ids.append(eid)
            event_dicts.append(
                {
                    "event_id": eid,
                    "event_type": "tool.execute",
                    "occurred_at": occurred_at.isoformat(),
                }
            )

        summary = create_summary_from_events(event_dicts, scope="session", scope_id=session_id)
        await maintenance.write_summary_with_edges(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
            summary_id=summary.summary_id,
            scope=summary.scope,
            scope_id=summary.scope_id,
            content=summary.content,
            created_at=summary.created_at.isoformat(),
            event_count=summary.event_count,
            time_range=[dt.isoformat() for dt in summary.time_range],
            event_ids=event_ids,
        )

        stats = await maintenance.get_graph_stats(
            neo4j_store._driver,
            neo4j_store._database,
        )

        assert stats["nodes"]["Event"] == 3
        assert stats["nodes"]["Summary"] == 1
        assert stats["edges"]["SUMMARIZES"] == 3
