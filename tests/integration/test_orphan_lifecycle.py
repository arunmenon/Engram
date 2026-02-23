"""Integration tests for Neo4j orphan node lifecycle — ADR-0014 Amendment.

Requires Neo4j running at bolt://localhost:7687 (docker-compose up).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context_graph.adapters.neo4j.maintenance import delete_orphan_nodes
from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.domain.models import (
    Edge,
    EdgeType,
    EntityNode,
    EntityType,
    EventNode,
    SummaryNode,
)
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


def _make_event_node(event_id: str, session_id: str = "sess-001") -> EventNode:
    return EventNode(
        event_id=event_id,
        event_type="tool.execute",
        occurred_at=datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
        session_id=session_id,
        agent_id="agent-001",
        trace_id="trace-001",
        global_position="1707644400000-0",
    )


def _make_entity_node(entity_id: str, name: str) -> EntityNode:
    return EntityNode(
        entity_id=entity_id,
        name=name,
        entity_type=EntityType.TOOL,
        first_seen=datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
        last_seen=datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
    )


@pytest.mark.integration
class TestOrphanEntityDeletedAfterEventRemoval:
    """Create Event+Entity with REFERENCES edge, delete event, verify orphan cleanup."""

    @pytest.mark.asyncio()
    async def test_orphan_entity_cleaned_up(self, neo4j_store: Neo4jGraphStore):
        """An entity with no remaining edges is deleted by orphan cleanup."""
        event = _make_event_node("evt-orphan-1")
        entity = _make_entity_node("ent-orphan-1", "calculator")
        edge = Edge(
            source="evt-orphan-1",
            target="ent-orphan-1",
            edge_type=EdgeType.REFERENCES,
        )

        # Write event + entity + edge
        await neo4j_store.merge_event_node(event)
        await neo4j_store.merge_entity_node(entity)
        await neo4j_store.create_edge(edge)

        # DETACH DELETE the event, leaving entity orphaned
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            await session.run(
                "MATCH (e:Event {event_id: $eid}) DETACH DELETE e",
                {"eid": "evt-orphan-1"},
            )

        # Verify entity still exists (orphaned)
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (n:Entity {entity_id: $eid}) RETURN n",
                {"eid": "ent-orphan-1"},
            )
            record = await result.single()
            assert record is not None, "Entity should still exist before orphan cleanup"

        # Run orphan cleanup
        counts, entity_ids = await delete_orphan_nodes(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
        )

        assert counts["Entity"] >= 1
        assert "ent-orphan-1" in entity_ids

        # Verify entity is gone
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (n:Entity {entity_id: $eid}) RETURN n",
                {"eid": "ent-orphan-1"},
            )
            record = await result.single()
            assert record is None, "Orphaned entity should be deleted"


@pytest.mark.integration
class TestConnectedEntitySurvivesOrphanCleanup:
    """An entity with remaining edges is NOT deleted."""

    @pytest.mark.asyncio()
    async def test_connected_entity_survives(self, neo4j_store: Neo4jGraphStore):
        """Entity connected to a surviving event should not be deleted."""
        event1 = _make_event_node("evt-survive-1")
        event2 = _make_event_node("evt-survive-2")
        entity = _make_entity_node("ent-survive-1", "web_search")

        edge1 = Edge(source="evt-survive-1", target="ent-survive-1", edge_type=EdgeType.REFERENCES)
        edge2 = Edge(source="evt-survive-2", target="ent-survive-1", edge_type=EdgeType.REFERENCES)

        await neo4j_store.merge_event_node(event1)
        await neo4j_store.merge_event_node(event2)
        await neo4j_store.merge_entity_node(entity)
        await neo4j_store.create_edge(edge1)
        await neo4j_store.create_edge(edge2)

        # Delete only one event — entity still has a connection to event2
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            await session.run(
                "MATCH (e:Event {event_id: $eid}) DETACH DELETE e",
                {"eid": "evt-survive-1"},
            )

        # Run orphan cleanup
        counts, entity_ids = await delete_orphan_nodes(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
        )

        # Entity should NOT have been deleted
        assert "ent-survive-1" not in entity_ids

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (n:Entity {entity_id: $eid}) RETURN n",
                {"eid": "ent-survive-1"},
            )
            record = await result.single()
            assert record is not None, "Connected entity should survive orphan cleanup"


@pytest.mark.integration
class TestUserProfileExemptFromOrphanCleanup:
    """UserProfile nodes with no edges should survive orphan cleanup."""

    @pytest.mark.asyncio()
    async def test_userprofile_survives(self, neo4j_store: Neo4jGraphStore):
        """An isolated UserProfile should not be deleted by orphan cleanup."""
        # Create an isolated UserProfile node
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            await session.run(
                "CREATE (u:UserProfile {user_id: $uid, name: $name})",
                {"uid": "user-exempt-1", "name": "Test User"},
            )

        # Run orphan cleanup
        counts, _ = await delete_orphan_nodes(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
        )

        # UserProfile is NOT in the orphan-eligible labels
        assert "UserProfile" not in counts

        # Verify UserProfile still exists
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (u:UserProfile {user_id: $uid}) RETURN u",
                {"uid": "user-exempt-1"},
            )
            record = await result.single()
            assert record is not None, "UserProfile should be exempt from orphan cleanup"


@pytest.mark.integration
class TestSummaryExemptFromOrphanCleanup:
    """Summary nodes with no edges should survive orphan cleanup."""

    @pytest.mark.asyncio()
    async def test_summary_survives(self, neo4j_store: Neo4jGraphStore):
        """An isolated Summary should not be deleted by orphan cleanup."""
        summary = SummaryNode(
            summary_id="sum-exempt-1",
            scope="session",
            scope_id="sess-gone",
            content="Test session summary",
            created_at=datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
            event_count=5,
            time_range=[
                datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
                datetime(2024, 2, 11, 13, 0, 0, tzinfo=UTC),
            ],
        )
        await neo4j_store.merge_summary_node(summary)

        # Run orphan cleanup
        counts, _ = await delete_orphan_nodes(
            driver=neo4j_store._driver,
            database=neo4j_store._database,
        )

        # Summary is NOT in the orphan-eligible labels
        assert "Summary" not in counts

        # Verify Summary still exists
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (s:Summary {summary_id: $sid}) RETURN s",
                {"sid": "sum-exempt-1"},
            )
            record = await result.single()
            assert record is not None, "Summary should be exempt from orphan cleanup"
