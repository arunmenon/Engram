"""Integration tests for retention tier enforcement and pruning.

Creates events at various ages, classifies them into retention tiers,
and verifies correct pruning behavior.

Requires Neo4j running at bolt://localhost:7687 (docker-compose up).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context_graph.adapters.neo4j import maintenance
from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.domain.forgetting import (
    classify_retention_tier,
    get_pruning_actions,
    should_prune_cold,
    should_prune_warm,
)
from context_graph.domain.models import EventNode, RetentionTier
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
    session_id: str = "forgetting-sess",
    occurred_at: datetime | None = None,
    importance_score: int | None = None,
    access_count: int = 0,
) -> EventNode:
    """Build an EventNode with configurable age and retention-related properties."""
    return EventNode(
        event_id=event_id,
        event_type="tool.execute",
        occurred_at=occurred_at or datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
        session_id=session_id,
        agent_id="agent-001",
        trace_id="trace-001",
        global_position=f"170764440{event_id[-4:]}-0",
        importance_score=importance_score,
        access_count=access_count,
    )


@pytest.mark.integration
class TestRetentionTierClassification:
    """Verify tier classification based on event age."""

    async def test_hot_tier(self) -> None:
        """Events less than 24h old are HOT."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=2)
        tier = classify_retention_tier(occurred, now=now)
        assert tier == RetentionTier.HOT

    async def test_warm_tier(self) -> None:
        """Events 24h-7d old are WARM."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=48)
        tier = classify_retention_tier(occurred, now=now)
        assert tier == RetentionTier.WARM

    async def test_cold_tier(self) -> None:
        """Events 7d-30d old are COLD."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=200)
        tier = classify_retention_tier(occurred, now=now)
        assert tier == RetentionTier.COLD

    async def test_archive_tier(self) -> None:
        """Events older than 30d are ARCHIVE."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=800)
        tier = classify_retention_tier(occurred, now=now)
        assert tier == RetentionTier.ARCHIVE

    async def test_boundary_hot_warm(self) -> None:
        """Event exactly at 24h boundary is WARM (not HOT)."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=24)
        tier = classify_retention_tier(occurred, now=now)
        assert tier == RetentionTier.WARM


@pytest.mark.integration
class TestPruningRules:
    """Verify pruning rule functions."""

    async def test_warm_prune_low_similarity(self) -> None:
        """Low similarity score triggers warm pruning."""
        assert should_prune_warm({"similarity_score": 0.3}) is True
        assert should_prune_warm({"similarity_score": 0.9}) is False
        assert should_prune_warm({"similarity_score": 0.7}) is False

    async def test_cold_prune_low_importance_low_access(self) -> None:
        """Low importance AND low access triggers cold pruning."""
        assert should_prune_cold({"importance_score": 2, "access_count": 1}) is True
        assert should_prune_cold({"importance_score": 8, "access_count": 1}) is False
        assert should_prune_cold({"importance_score": 2, "access_count": 5}) is False

    async def test_cold_prune_missing_fields(self) -> None:
        """Missing fields default to zero, which triggers pruning."""
        assert should_prune_cold({}) is True


@pytest.mark.integration
class TestGetPruningActions:
    """Test the aggregated pruning actions function."""

    async def test_hot_events_not_pruned(self) -> None:
        """HOT tier events are never pruned."""
        now = datetime.now(UTC)
        events = [
            {
                "event_id": "evt-hot",
                "occurred_at": (now - timedelta(hours=1)).isoformat(),
                "importance_score": 1,
                "access_count": 0,
            },
        ]
        actions = get_pruning_actions(events, now=now)
        assert actions.delete_edges == []
        assert actions.delete_nodes == []
        assert actions.archive_event_ids == []

    async def test_warm_events_with_low_similarity(self) -> None:
        """WARM tier events with low similarity get edges marked for deletion."""
        now = datetime.now(UTC)
        events = [
            {
                "event_id": "evt-warm-low",
                "occurred_at": (now - timedelta(hours=48)).isoformat(),
                "similarity_score": 0.3,
            },
        ]
        actions = get_pruning_actions(events, now=now)
        assert "evt-warm-low" in actions.delete_edges

    async def test_cold_events_pruned(self) -> None:
        """COLD tier events with low importance/access are marked for node deletion."""
        now = datetime.now(UTC)
        events = [
            {
                "event_id": "evt-cold-prune",
                "occurred_at": (now - timedelta(hours=200)).isoformat(),
                "importance_score": 2,
                "access_count": 0,
            },
        ]
        actions = get_pruning_actions(events, now=now)
        assert "evt-cold-prune" in actions.delete_nodes

    async def test_archive_events_marked(self) -> None:
        """ARCHIVE tier events are marked for archival."""
        now = datetime.now(UTC)
        events = [
            {
                "event_id": "evt-archive",
                "occurred_at": (now - timedelta(hours=800)).isoformat(),
            },
        ]
        actions = get_pruning_actions(events, now=now)
        assert "evt-archive" in actions.archive_event_ids

    async def test_mixed_tiers(self) -> None:
        """Mixed events get correctly classified and actioned."""
        now = datetime.now(UTC)
        events = [
            {
                "event_id": "evt-h",
                "occurred_at": (now - timedelta(hours=1)).isoformat(),
            },
            {
                "event_id": "evt-w",
                "occurred_at": (now - timedelta(hours=48)).isoformat(),
                "similarity_score": 0.1,
            },
            {
                "event_id": "evt-c",
                "occurred_at": (now - timedelta(hours=200)).isoformat(),
                "importance_score": 1,
                "access_count": 0,
            },
            {
                "event_id": "evt-a",
                "occurred_at": (now - timedelta(hours=800)).isoformat(),
            },
        ]
        actions = get_pruning_actions(events, now=now)
        assert actions.delete_edges == ["evt-w"]
        assert actions.delete_nodes == ["evt-c"]
        assert actions.archive_event_ids == ["evt-a"]


@pytest.mark.integration
class TestPruningInNeo4j:
    """Test actual pruning operations against Neo4j."""

    async def test_delete_cold_events(self, neo4j_store: Neo4jGraphStore) -> None:
        """Delete cold events that don't meet retention criteria."""
        now = datetime.now(UTC)

        # Create an old event with low importance in Neo4j
        old_event = _make_event_node(
            event_id="evt-old-cold",
            occurred_at=now - timedelta(hours=200),
            importance_score=2,
            access_count=0,
        )
        await neo4j_store.merge_event_node(old_event)

        # Create a recent event that should survive
        recent_event = _make_event_node(
            event_id="evt-recent",
            occurred_at=now - timedelta(hours=1),
            importance_score=8,
            access_count=5,
        )
        await neo4j_store.merge_event_node(recent_event)

        # Delete cold events older than 168h (7 days) with low importance
        deleted = await maintenance.delete_cold_events(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
            max_age_hours=168,
            min_importance=5,
            min_access_count=3,
        )

        assert deleted == 1

        # Verify old event is gone, recent survives
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run("MATCH (e:Event) RETURN e.event_id AS eid")
            records = [record async for record in result]

        remaining_ids = {r["eid"] for r in records}
        assert "evt-old-cold" not in remaining_ids
        assert "evt-recent" in remaining_ids

    async def test_delete_archive_events(self, neo4j_store: Neo4jGraphStore) -> None:
        """Delete specific archived events by ID."""
        now = datetime.now(UTC)
        for i in range(3):
            node = _make_event_node(
                event_id=f"evt-arch-{i:03d}",
                occurred_at=now - timedelta(hours=800 + i),
            )
            await neo4j_store.merge_event_node(node)

        # Delete 2 of 3
        deleted = await maintenance.delete_archive_events(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
            event_ids=["evt-arch-000", "evt-arch-001"],
        )

        assert deleted == 2

        # Verify only evt-arch-002 remains
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run("MATCH (e:Event) RETURN e.event_id AS eid")
            records = [record async for record in result]

        remaining_ids = {r["eid"] for r in records}
        assert remaining_ids == {"evt-arch-002"}

    async def test_delete_archive_empty_list(self, neo4j_store: Neo4jGraphStore) -> None:
        """Deleting an empty list of archive events returns 0."""
        deleted = await maintenance.delete_archive_events(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
            event_ids=[],
        )
        assert deleted == 0

    async def test_graph_stats_after_pruning(self, neo4j_store: Neo4jGraphStore) -> None:
        """Graph stats update after pruning events."""
        now = datetime.now(UTC)

        # Create 5 events
        for i in range(5):
            node = _make_event_node(
                event_id=f"evt-prune-stat-{i:03d}",
                occurred_at=now - timedelta(hours=200 + i),
                importance_score=1,
                access_count=0,
            )
            await neo4j_store.merge_event_node(node)

        stats_before = await maintenance.get_graph_stats(
            neo4j_store._driver,
            neo4j_store._database,
        )
        assert stats_before["nodes"]["Event"] == 5

        # Delete 3 events
        deleted = await maintenance.delete_archive_events(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
            event_ids=[f"evt-prune-stat-{i:03d}" for i in range(3)],
        )
        assert deleted == 3

        stats_after = await maintenance.get_graph_stats(
            neo4j_store._driver,
            neo4j_store._database,
        )
        assert stats_after["nodes"]["Event"] == 2
