"""Integration tests for Neo4jGraphStore against a real Neo4j instance.

Requires Neo4j running at bolt://localhost:7687 (docker-compose up).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context_graph.adapters.neo4j.store import Neo4jGraphStore
from context_graph.domain.models import (
    CausalMechanism,
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

    # Ensure constraints exist
    await store.ensure_constraints()

    yield store

    # Teardown: delete all test data
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
) -> EventNode:
    return EventNode(
        event_id=event_id,
        event_type=event_type,
        occurred_at=datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC),
        session_id=session_id,
        agent_id=agent_id,
        trace_id=trace_id,
        global_position=global_position,
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


def _make_summary_node(summary_id: str = "summary-001") -> SummaryNode:
    now = datetime(2024, 2, 11, 12, 0, 0, tzinfo=UTC)
    return SummaryNode(
        summary_id=summary_id,
        scope="session",
        scope_id="sess-001",
        content="Test session summary.",
        created_at=now,
        event_count=5,
        time_range=[now],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMergeEventNode:
    async def test_merge_creates_node(self, neo4j_store: Neo4jGraphStore) -> None:
        node = _make_event_node()
        await neo4j_store.merge_event_node(node)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (e:Event {event_id: $eid}) RETURN e",
                {"eid": "evt-001"},
            )
            records = [record async for record in result]

        assert len(records) == 1
        event_props = records[0]["e"]
        assert event_props["event_type"] == "tool.execute"
        assert event_props["session_id"] == "sess-001"

    async def test_merge_is_idempotent(self, neo4j_store: Neo4jGraphStore) -> None:
        node = _make_event_node()
        await neo4j_store.merge_event_node(node)
        await neo4j_store.merge_event_node(node)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (e:Event {event_id: $eid}) RETURN count(e) AS cnt",
                {"eid": "evt-001"},
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 1

    async def test_merge_updates_properties(self, neo4j_store: Neo4jGraphStore) -> None:
        node = _make_event_node()
        await neo4j_store.merge_event_node(node)

        # Merge again with updated summary
        updated_node = _make_event_node()
        updated_node.summary = "Updated summary"
        updated_node.importance_score = 8
        await neo4j_store.merge_event_node(updated_node)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (e:Event {event_id: $eid}) RETURN e",
                {"eid": "evt-001"},
            )
            record = await result.single()

        assert record is not None
        assert record["e"]["summary"] == "Updated summary"
        assert record["e"]["importance_score"] == 8


@pytest.mark.integration
class TestMergeEntityNode:
    async def test_merge_creates_entity(self, neo4j_store: Neo4jGraphStore) -> None:
        node = _make_entity_node()
        await neo4j_store.merge_entity_node(node)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (n:Entity {entity_id: $eid}) RETURN n",
                {"eid": "entity-001"},
            )
            records = [record async for record in result]

        assert len(records) == 1
        assert records[0]["n"]["name"] == "test-tool"
        assert records[0]["n"]["entity_type"] == "tool"

    async def test_merge_entity_idempotent(self, neo4j_store: Neo4jGraphStore) -> None:
        node = _make_entity_node()
        await neo4j_store.merge_entity_node(node)
        await neo4j_store.merge_entity_node(node)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (n:Entity {entity_id: $eid}) RETURN count(n) AS cnt",
                {"eid": "entity-001"},
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 1


@pytest.mark.integration
class TestMergeSummaryNode:
    async def test_merge_creates_summary(self, neo4j_store: Neo4jGraphStore) -> None:
        node = _make_summary_node()
        await neo4j_store.merge_summary_node(node)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (s:Summary {summary_id: $sid}) RETURN s",
                {"sid": "summary-001"},
            )
            records = [record async for record in result]

        assert len(records) == 1
        assert records[0]["s"]["content"] == "Test session summary."
        assert records[0]["s"]["event_count"] == 5


@pytest.mark.integration
class TestCreateEdge:
    async def test_create_follows_edge(self, neo4j_store: Neo4jGraphStore) -> None:
        node_a = _make_event_node(event_id="evt-a", global_position="1707644400000-0")
        node_b = _make_event_node(event_id="evt-b", global_position="1707644400000-1")
        await neo4j_store.merge_event_node(node_a)
        await neo4j_store.merge_event_node(node_b)

        edge = Edge(
            source="evt-a",
            target="evt-b",
            edge_type=EdgeType.FOLLOWS,
            properties={"session_id": "sess-001", "delta_ms": 1200},
        )
        await neo4j_store.create_edge(edge)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (a:Event {event_id: 'evt-a'})-[r:FOLLOWS]->"
                "(b:Event {event_id: 'evt-b'}) RETURN r"
            )
            records = [record async for record in result]

        assert len(records) == 1
        rel_props = dict(records[0]["r"])
        assert rel_props["session_id"] == "sess-001"
        assert rel_props["delta_ms"] == 1200

    async def test_create_caused_by_edge(self, neo4j_store: Neo4jGraphStore) -> None:
        node_a = _make_event_node(event_id="evt-c", global_position="1707644400000-2")
        node_b = _make_event_node(event_id="evt-d", global_position="1707644400000-3")
        await neo4j_store.merge_event_node(node_a)
        await neo4j_store.merge_event_node(node_b)

        edge = Edge(
            source="evt-c",
            target="evt-d",
            edge_type=EdgeType.CAUSED_BY,
            properties={"mechanism": str(CausalMechanism.DIRECT)},
        )
        await neo4j_store.create_edge(edge)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (a:Event {event_id: 'evt-c'})-[r:CAUSED_BY]->"
                "(b:Event {event_id: 'evt-d'}) RETURN r"
            )
            records = [record async for record in result]

        assert len(records) == 1
        assert dict(records[0]["r"])["mechanism"] == "direct"

    async def test_create_references_edge(self, neo4j_store: Neo4jGraphStore) -> None:
        event_node = _make_event_node(event_id="evt-ref", global_position="1707644400000-4")
        entity_node = _make_entity_node(entity_id="entity-ref")
        await neo4j_store.merge_event_node(event_node)
        await neo4j_store.merge_entity_node(entity_node)

        edge = Edge(
            source="evt-ref",
            target="entity-ref",
            edge_type=EdgeType.REFERENCES,
            properties={"role": "instrument"},
        )
        await neo4j_store.create_edge(edge)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (a:Event {event_id: 'evt-ref'})-[r:REFERENCES]->"
                "(b:Entity {entity_id: 'entity-ref'}) RETURN r"
            )
            records = [record async for record in result]

        assert len(records) == 1
        assert dict(records[0]["r"])["role"] == "instrument"

    async def test_create_edge_unknown_type_raises(self, neo4j_store: Neo4jGraphStore) -> None:
        # Use model_construct to bypass Pydantic enum validation
        edge = Edge.model_construct(source="a", target="b", edge_type="NONEXISTENT", properties={})
        with pytest.raises(ValueError, match="Unknown edge type"):
            await neo4j_store.create_edge(edge)

    async def test_edge_merge_is_idempotent(self, neo4j_store: Neo4jGraphStore) -> None:
        node_a = _make_event_node(event_id="evt-idem-a", global_position="1707644400000-5")
        node_b = _make_event_node(event_id="evt-idem-b", global_position="1707644400000-6")
        await neo4j_store.merge_event_node(node_a)
        await neo4j_store.merge_event_node(node_b)

        edge = Edge(
            source="evt-idem-a",
            target="evt-idem-b",
            edge_type=EdgeType.FOLLOWS,
            properties={"session_id": "sess-001"},
        )
        await neo4j_store.create_edge(edge)
        await neo4j_store.create_edge(edge)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (a:Event {event_id: 'evt-idem-a'})-[r:FOLLOWS]->"
                "(b:Event {event_id: 'evt-idem-b'}) RETURN count(r) AS cnt"
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 1


@pytest.mark.integration
class TestCreateEdgesBatch:
    async def test_batch_creates_multiple_edges(self, neo4j_store: Neo4jGraphStore) -> None:
        # Create 3 event nodes
        for i in range(3):
            node = _make_event_node(
                event_id=f"evt-batch-{i}",
                global_position=f"1707644400000-{10 + i}",
            )
            await neo4j_store.merge_event_node(node)

        edges = [
            Edge(
                source="evt-batch-0",
                target="evt-batch-1",
                edge_type=EdgeType.FOLLOWS,
                properties={"delta_ms": 100},
            ),
            Edge(
                source="evt-batch-1",
                target="evt-batch-2",
                edge_type=EdgeType.FOLLOWS,
                properties={"delta_ms": 200},
            ),
        ]
        await neo4j_store.create_edges_batch(edges)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run(
                "MATCH (:Event)-[r:FOLLOWS]->(:Event) "
                "WHERE r.delta_ms IN [100, 200] RETURN count(r) AS cnt"
            )
            record = await result.single()

        assert record is not None
        assert record["cnt"] == 2

    async def test_batch_mixed_edge_types(self, neo4j_store: Neo4jGraphStore) -> None:
        for i in range(3):
            node = _make_event_node(
                event_id=f"evt-mix-{i}",
                global_position=f"1707644400000-{20 + i}",
            )
            await neo4j_store.merge_event_node(node)

        edges = [
            Edge(
                source="evt-mix-0",
                target="evt-mix-1",
                edge_type=EdgeType.FOLLOWS,
                properties={"delta_ms": 500},
            ),
            Edge(
                source="evt-mix-1",
                target="evt-mix-2",
                edge_type=EdgeType.CAUSED_BY,
                properties={"mechanism": "direct"},
            ),
        ]
        await neo4j_store.create_edges_batch(edges)

        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            follows_result = await session.run(
                "MATCH (:Event {event_id: 'evt-mix-0'})-[r:FOLLOWS]->(:Event) "
                "RETURN count(r) AS cnt"
            )
            follows_record = await follows_result.single()

            caused_result = await session.run(
                "MATCH (:Event {event_id: 'evt-mix-1'})-[r:CAUSED_BY]->(:Event) "
                "RETURN count(r) AS cnt"
            )
            caused_record = await caused_result.single()

        assert follows_record is not None
        assert follows_record["cnt"] == 1
        assert caused_record is not None
        assert caused_record["cnt"] == 1

    async def test_batch_empty_list(self, neo4j_store: Neo4jGraphStore) -> None:
        # Should not raise
        await neo4j_store.create_edges_batch([])


@pytest.mark.integration
class TestEnsureConstraints:
    async def test_constraints_created(self, neo4j_store: Neo4jGraphStore) -> None:
        # ensure_constraints is called in the fixture; verify constraints exist
        async with neo4j_store._driver.session(database=neo4j_store._database) as session:
            result = await session.run("SHOW CONSTRAINTS")
            constraints = [record async for record in result]

        constraint_names = {c["name"] for c in constraints}
        assert "event_pk" in constraint_names
        assert "entity_pk" in constraint_names
        assert "summary_pk" in constraint_names

    async def test_constraints_idempotent(self, neo4j_store: Neo4jGraphStore) -> None:
        # Running twice should not raise
        await neo4j_store.ensure_constraints()
        await neo4j_store.ensure_constraints()


@pytest.mark.integration
class TestPhase3Stubs:
    async def test_get_subgraph_not_implemented(self, neo4j_store: Neo4jGraphStore) -> None:
        from context_graph.domain.models import SubgraphQuery

        query = SubgraphQuery(query="test", session_id="s", agent_id="a", max_nodes=10)
        with pytest.raises(NotImplementedError, match="Phase 3"):
            await neo4j_store.get_subgraph(query)

    async def test_get_lineage_not_implemented(self, neo4j_store: Neo4jGraphStore) -> None:
        from context_graph.domain.models import LineageQuery

        query = LineageQuery(node_id="n")
        with pytest.raises(NotImplementedError, match="Phase 3"):
            await neo4j_store.get_lineage(query)

    async def test_get_context_not_implemented(self, neo4j_store: Neo4jGraphStore) -> None:
        with pytest.raises(NotImplementedError, match="Phase 3"):
            await neo4j_store.get_context("sess-001")

    async def test_get_entity_not_implemented(self, neo4j_store: Neo4jGraphStore) -> None:
        with pytest.raises(NotImplementedError, match="Phase 3"):
            await neo4j_store.get_entity("entity-001")
