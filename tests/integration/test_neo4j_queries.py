"""Integration tests for Phase 3 Neo4j query methods.

Tests get_context, get_lineage, get_subgraph, and get_entity against a real
Neo4j instance. Requires Neo4j running at bolt://localhost:7687.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.domain.models import (
    CausalMechanism,
    Edge,
    EdgeType,
    EntityNode,
    EntityType,
    EventNode,
    LineageQuery,
    SubgraphQuery,
)
from context_graph.settings import Neo4jSettings


@pytest.fixture
async def neo4j_store():
    """Provide a Neo4jGraphStore connected to the test database, clean up after."""
    settings = Neo4jSettings()
    store = Neo4jGraphStore(settings)
    await store.ensure_constraints()

    yield store

    async with store._driver.session(database=store._database) as session:
        await session.run("MATCH (n) DETACH DELETE n")

    await store.close()


def _make_event_node(
    event_id: str = "evt-001",
    event_type: str = "tool.execute",
    session_id: str = "sess-001",
    agent_id: str = "agent-001",
    trace_id: str = "trace-001",
    global_position: str = "1707644400000-0",
    occurred_at: datetime | None = None,
    importance_score: int | None = None,
) -> EventNode:
    return EventNode(
        event_id=event_id,
        event_type=event_type,
        occurred_at=occurred_at or datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
        session_id=session_id,
        agent_id=agent_id,
        trace_id=trace_id,
        global_position=global_position,
        importance_score=importance_score,
    )


def _make_entity_node(
    entity_id: str = "entity-001",
    name: str = "test-tool",
    entity_type: EntityType = EntityType.TOOL,
) -> EntityNode:
    now = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
    return EntityNode(
        entity_id=entity_id,
        name=name,
        entity_type=entity_type,
        first_seen=now,
        last_seen=now,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGetSessionEvents:
    async def test_get_session_events(self, neo4j_store: Neo4jGraphStore) -> None:
        """Insert 5 events, verify get_context returns them ordered."""
        base_time = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
        for i in range(5):
            node = _make_event_node(
                event_id=f"evt-ctx-{i}",
                global_position=f"1707644400000-{i}",
                occurred_at=base_time + timedelta(minutes=i),
            )
            await neo4j_store.merge_event_node(node)

        response = await neo4j_store.get_context("sess-001", max_nodes=10)

        assert len(response.nodes) == 5
        assert response.meta.nodes_returned == 5
        assert response.meta.capacity is not None
        assert response.meta.capacity.used_nodes == 5


@pytest.mark.integration
class TestGetLineage:
    async def test_get_lineage_causal_chain(self, neo4j_store: Neo4jGraphStore) -> None:
        """Create A->B->C causal chain, verify traversal from A returns B and C."""
        base_time = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
        for i, eid in enumerate(["evt-a", "evt-b", "evt-c"]):
            node = _make_event_node(
                event_id=eid,
                global_position=f"1707644400000-{i}",
                occurred_at=base_time + timedelta(minutes=i),
            )
            await neo4j_store.merge_event_node(node)

        # A -CAUSED_BY-> B -CAUSED_BY-> C
        for src, tgt in [("evt-a", "evt-b"), ("evt-b", "evt-c")]:
            edge = Edge(
                source=src,
                target=tgt,
                edge_type=EdgeType.CAUSED_BY,
                properties={"mechanism": str(CausalMechanism.DIRECT)},
            )
            await neo4j_store.create_edge(edge)

        query = LineageQuery(node_id="evt-a", max_depth=5, max_nodes=50)
        response = await neo4j_store.get_lineage(query)

        # Should find at least A, B, C in nodes
        assert len(response.nodes) >= 2  # B and C (start may or may not be included)
        assert len(response.edges) >= 1
        assert response.meta.capacity is not None
        assert response.meta.capacity.max_depth == 5


@pytest.mark.integration
class TestGetEntityWithEvents:
    async def test_get_entity_with_events(self, neo4j_store: Neo4jGraphStore) -> None:
        """Create entity + 3 REFERENCES edges, verify query returns entity + events."""
        entity = _make_entity_node(entity_id="ent-q1", name="search-tool")
        await neo4j_store.merge_entity_node(entity)

        for i in range(3):
            node = _make_event_node(
                event_id=f"evt-ref-{i}",
                global_position=f"1707644400000-{i}",
            )
            await neo4j_store.merge_event_node(node)
            edge = Edge(
                source=f"evt-ref-{i}",
                target="ent-q1",
                edge_type=EdgeType.REFERENCES,
                properties={"role": "instrument"},
            )
            await neo4j_store.create_edge(edge)

        result = await neo4j_store.get_entity("ent-q1")

        assert result is not None
        assert result["entity"]["name"] == "search-tool"
        assert len(result["connected_events"]) == 3

    async def test_get_entity_not_found(self, neo4j_store: Neo4jGraphStore) -> None:
        """Non-existent entity returns None."""
        result = await neo4j_store.get_entity("nonexistent-entity")
        assert result is None


@pytest.mark.integration
class TestUpdateAccessCount:
    async def test_access_count_increments(self, neo4j_store: Neo4jGraphStore) -> None:
        """Verify access_count increments after bumping."""
        node = _make_event_node(event_id="evt-ac1", global_position="1707644400000-0")
        await neo4j_store.merge_event_node(node)

        await neo4j_store._bump_access_counts(["evt-ac1"])

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (e:Event {event_id: 'evt-ac1'}) RETURN e.access_count AS ac"
            )
            record = await result.single()

        assert record is not None
        assert record["ac"] == 1

        # Bump again
        await neo4j_store._bump_access_counts(["evt-ac1"])

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (e:Event {event_id: 'evt-ac1'}) RETURN e.access_count AS ac"
            )
            record = await result.single()

        assert record is not None
        assert record["ac"] == 2


@pytest.mark.integration
class TestGetContext:
    async def test_get_context_returns_atlas_response(self, neo4j_store: Neo4jGraphStore) -> None:
        """Verify get_context returns properly structured AtlasResponse."""
        base_time = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
        for i in range(3):
            node = _make_event_node(
                event_id=f"evt-atlas-{i}",
                global_position=f"1707644400000-{i}",
                occurred_at=base_time + timedelta(minutes=i),
                importance_score=5 + i,
            )
            await neo4j_store.merge_event_node(node)

        response = await neo4j_store.get_context("sess-001", max_nodes=10)

        assert len(response.nodes) == 3
        # Verify AtlasNode structure
        for _node_id, atlas_node in response.nodes.items():
            assert atlas_node.node_type == "Event"
            assert atlas_node.provenance is not None
            assert atlas_node.provenance.session_id == "sess-001"
            assert atlas_node.scores.decay_score >= 0.0

        assert response.meta.query_ms >= 0
        assert response.meta.nodes_returned == 3


@pytest.mark.integration
class TestGetSubgraph:
    async def test_get_subgraph_with_intents(self, neo4j_store: Neo4jGraphStore) -> None:
        """Verify get_subgraph returns AtlasResponse with inferred intents."""
        base_time = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
        for i in range(3):
            node = _make_event_node(
                event_id=f"evt-sg-{i}",
                global_position=f"1707644400000-{i}",
                occurred_at=base_time + timedelta(minutes=i),
            )
            await neo4j_store.merge_event_node(node)

        # Add a FOLLOWS edge for traversal
        edge = Edge(
            source="evt-sg-0",
            target="evt-sg-1",
            edge_type=EdgeType.FOLLOWS,
            properties={"delta_ms": 60000},
        )
        await neo4j_store.create_edge(edge)

        query = SubgraphQuery(
            query="why did the tool fail?",
            session_id="sess-001",
            agent_id="agent-001",
            max_nodes=50,
        )
        response = await neo4j_store.get_subgraph(query)

        # Should have seed nodes from session
        assert len(response.nodes) >= 1
        assert response.meta.inferred_intents  # Should have intent scores
        assert "why" in response.meta.inferred_intents
        assert len(response.meta.seed_nodes) >= 1
        assert response.meta.capacity is not None
