"""GraphStore + GraphMaintenance conformance suite (ADR-0019 §5).

Pins MERGE semantics (idempotent nodes and edges, missing endpoints
create nothing, None removes a property), entity reads, enrichment,
vector search scores, the maintenance operations consolidation and admin
call, and the named operations that replaced query text.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from context_graph.domain.models import EdgeType
from context_graph.ports.errors import InvalidRequestError
from tests.conformance.graph_fixtures import edge, entity_node, event_node, unit_vector

if TYPE_CHECKING:
    from context_graph.ports.graph_backend import GraphBackend


async def _stats(graph: GraphBackend) -> dict:
    return await graph.get_graph_stats()


class TestNodeMerge:
    async def test_merge_is_idempotent_and_updates(self, graph: GraphBackend) -> None:
        node = event_node("evt-1", tool_name="grep")
        await graph.merge_event_node(node)
        await graph.merge_event_node(node.model_copy(update={"tool_name": "sed"}))

        stats = await _stats(graph)
        assert stats["nodes"]["Event"] == 1
        (props,) = await graph.reads.get_event_nodes(["evt-1"])
        assert props["tool_name"] == "sed"

    async def test_none_removes_property(self, graph: GraphBackend) -> None:
        await graph.merge_event_node(event_node("evt-1", tool_name="grep"))
        await graph.merge_event_node(event_node("evt-1", tool_name=None))
        (props,) = await graph.reads.get_event_nodes(["evt-1"])
        assert "tool_name" not in props

    async def test_batch_merge(self, graph: GraphBackend) -> None:
        await graph.merge_event_nodes_batch([event_node("evt-1"), event_node("evt-2")])
        assert (await _stats(graph))["nodes"]["Event"] == 2


class TestEdges:
    async def test_edge_merge_is_idempotent(self, graph: GraphBackend) -> None:
        await graph.merge_event_nodes_batch([event_node("a"), event_node("b")])
        await graph.create_edge(edge("a", "b", EdgeType.FOLLOWS, delta_ms=10))
        await graph.create_edges_batch([edge("a", "b", EdgeType.FOLLOWS, delta_ms=20)])

        stats = await _stats(graph)
        assert stats["edges"]["FOLLOWS"] == 1
        rows = await graph.reads.event_neighbors(["a"], 10)
        assert rows[0]["rel_props"] == {"delta_ms": 20}

    async def test_missing_endpoint_creates_nothing(self, graph: GraphBackend) -> None:
        await graph.merge_event_node(event_node("a"))
        await graph.create_edge(edge("a", "ghost", EdgeType.CAUSED_BY))
        await graph.merge_typed_edge("a", "no-entity", "REFERENCES")
        assert (await _stats(graph))["total_edges"] == 0

    async def test_unknown_edge_type_rejected(self, graph: GraphBackend) -> None:
        with pytest.raises(ValueError, match="Unknown edge type"):
            await graph.merge_typed_edge("a", "b", "NOT_A_TYPE")


class TestEntities:
    async def test_get_entity_with_referencing_events(self, graph: GraphBackend) -> None:
        await graph.merge_entity_node(entity_node("ent-1", name="redis"))
        await graph.merge_event_nodes_batch(
            [event_node("old", minutes_ago=10), event_node("new", minutes_ago=1)]
        )
        await graph.create_edges_batch(
            [
                edge("old", "ent-1", EdgeType.REFERENCES, role="subject"),
                edge("new", "ent-1", EdgeType.REFERENCES),
            ]
        )

        result = await graph.get_entity("ent-1")
        assert result is not None
        assert result["entity"]["name"] == "redis"
        assert [e["event_id"] for e in result["connected_events"]] == ["new", "old"]
        assert result["connected_events"][1]["ref_props"] == {"role": "subject"}

    async def test_entity_without_events_and_missing_entity(self, graph: GraphBackend) -> None:
        await graph.merge_entity_node(entity_node("lonely"))
        assert (await graph.get_entity("lonely"))["connected_events"] == []  # type: ignore[index]
        assert await graph.get_entity("absent") is None

    async def test_cluster_consolidation(self, graph: GraphBackend) -> None:
        for entity_id in ("canon", "alias-1", "alias-2"):
            await graph.merge_entity_node(entity_node(entity_id))
        await graph.consolidate_entity_cluster(["alias-1", "alias-2", "canon"], "canon")
        await graph.consolidate_entity_cluster(["alias-1"], "canon")  # idempotent

        assert (await _stats(graph))["edges"]["SAME_AS"] == 2
        cluster = await graph.get_entity_with_cluster("alias-1")  # type: ignore[attr-defined]
        assert set(cluster["entities"]) == {"canon", "alias-1", "alias-2"}

    async def test_get_entities(self, graph: GraphBackend) -> None:
        await graph.merge_entity_node_raw("e1", "one", "tool", "t", "t", 1)
        await graph.merge_entity_node_raw("e2", "two", "concept", "t", "t", 1)
        entities = await graph.get_entities()
        assert sorted(e["entity_id"] for e in entities) == ["e1", "e2"]
        assert len(await graph.get_entities(limit=1)) == 1


class TestEnrichment:
    async def test_enrichment_and_embedding(self, graph: GraphBackend) -> None:
        await graph.merge_event_node(event_node("evt-1"))
        await graph.update_event_enrichment("evt-1", ["tool", "execute"], 7)
        await graph.store_event_embedding("evt-1", [0.5, 0.5])
        (props,) = await graph.reads.get_event_nodes(["evt-1"])
        assert props["keywords"] == ["tool", "execute"]
        assert props["importance_score"] == 7
        assert props["embedding"] == [0.5, 0.5]

    async def test_adjust_importance_clamps(self, graph: GraphBackend) -> None:
        await graph.merge_event_node(event_node("evt-1", importance_score=9))
        assert await graph.adjust_node_importance("evt-1", 5) is True
        (props,) = await graph.reads.get_event_nodes(["evt-1"])
        assert props["importance_score"] == 10
        assert await graph.adjust_node_importance("absent", 1) is False

    async def test_adjust_importance_without_score_starts_at_five(
        self, graph: GraphBackend
    ) -> None:
        await graph.merge_event_node(event_node("evt-1"))
        await graph.adjust_node_importance("evt-1", -2)
        (props,) = await graph.reads.get_event_nodes(["evt-1"])
        assert props["importance_score"] == 3


class TestVectorSearch:
    async def test_scores_in_unit_range_best_first(self, graph: GraphBackend) -> None:
        await graph.merge_entity_node(entity_node("same", embedding=unit_vector(0)))
        await graph.merge_entity_node(entity_node("close", embedding=unit_vector(0, tilt=0.5)))
        await graph.merge_entity_node(
            entity_node("opposite", embedding=[-v for v in unit_vector(0)])
        )

        results = await graph.search_similar_entities(unit_vector(0), top_k=3, threshold=0.0)

        ids = [r["entity_id"] for r in results]
        assert ids[:2] == ["same", "close"]
        scores = [r["score"] for r in results]
        assert all(0.0 <= s <= 1.0 for s in scores)
        assert scores == sorted(scores, reverse=True)
        assert scores[0] == pytest.approx(1.0, abs=1e-3)

    async def test_threshold_and_top_k(self, graph: GraphBackend) -> None:
        await graph.merge_entity_node(entity_node("same", embedding=unit_vector(0)))
        await graph.merge_entity_node(
            entity_node("opposite", embedding=[-v for v in unit_vector(0)])
        )
        assert [
            r["entity_id"]
            for r in await graph.search_similar_entities(unit_vector(0), top_k=5, threshold=0.75)
        ] == ["same"]
        assert len(await graph.search_similar_entities(unit_vector(0), top_k=1, threshold=0.0)) == 1


class TestMaintenance:
    async def test_counts_and_stats_shape(self, graph: GraphBackend) -> None:
        await graph.merge_event_nodes_batch(
            [event_node(session_id="a"), event_node(session_id="a"), event_node(session_id="b")]
        )
        assert await graph.get_session_event_counts() == {"a": 2, "b": 1}
        stats = await _stats(graph)
        assert set(stats) == {"nodes", "edges", "total_nodes", "total_edges"}
        assert stats["nodes"]["Event"] == 3
        assert stats["total_nodes"] == 3

    async def test_summary_with_edges(self, graph: GraphBackend) -> None:
        await graph.merge_event_nodes_batch([event_node("e1"), event_node("e2")])
        await graph.write_summary_with_edges(
            summary_id="sum-1",
            scope="session",
            scope_id="s1",
            content="two events",
            created_at="2026-01-01T00:00:00+00:00",
            event_count=2,
            time_range=["2026-01-01T00:00:00+00:00"],
            event_ids=["e1", "e2", "missing"],
        )
        stats = await _stats(graph)
        assert stats["nodes"]["Summary"] == 1
        assert stats["edges"]["SUMMARIZES"] == 2

    async def test_cold_and_archive_deletion(self, graph: GraphBackend) -> None:
        await graph.merge_event_nodes_batch(
            [
                event_node("cold", minutes_ago=600, importance_score=2),
                event_node("important", minutes_ago=600, importance_score=9),
                event_node("accessed", minutes_ago=600, access_count=5),
                event_node("fresh", minutes_ago=1),
            ]
        )
        await graph.create_edge(edge("fresh", "cold", EdgeType.FOLLOWS))

        assert (
            await graph.delete_cold_events(max_age_hours=1, min_importance=5, min_access_count=3)
            == 1
        )
        assert sorted(await graph.get_archive_event_ids(max_age_hours=1)) == [
            "accessed",
            "important",
        ]
        assert await graph.delete_archive_events(["accessed", "absent"]) == 1
        assert (await _stats(graph))["total_edges"] == 0

    async def test_similar_edge_pruning(self, graph: GraphBackend) -> None:
        await graph.merge_event_nodes_batch(
            [event_node("old", minutes_ago=600), event_node("b"), event_node("new")]
        )
        await graph.create_edges_batch(
            [
                edge("old", "b", EdgeType.SIMILAR_TO, similarity_score=0.2),
                edge("new", "b", EdgeType.SIMILAR_TO, similarity_score=0.2),
                edge("b", "old", EdgeType.SIMILAR_TO, similarity_score=0.95),
            ]
        )
        assert await graph.delete_edges_by_type_and_age(min_score=0.7, max_age_hours=1) == 1
        assert (await _stats(graph))["edges"]["SIMILAR_TO"] == 2

    async def test_orphan_cleanup(self, graph: GraphBackend) -> None:
        await graph.merge_entity_node(entity_node("orphan"))
        await graph.merge_entity_node(entity_node("linked"))
        await graph.merge_event_node(event_node("evt-1"))
        await graph.create_edge(edge("evt-1", "linked", EdgeType.REFERENCES))

        counts, deleted_ids = await graph.delete_orphan_nodes(batch_size=10)
        assert counts["Entity"] == 1
        assert deleted_ids == ["orphan"]
        assert await graph.get_entity("linked") is not None

    async def test_importance_from_centrality(self, graph: GraphBackend) -> None:
        events = [event_node(f"e{i}") for i in range(4)]
        await graph.merge_event_nodes_batch(events)
        await graph.create_edges_batch(
            [edge(f"e{i}", "e0", EdgeType.CAUSED_BY) for i in range(1, 4)]
        )
        assert await graph.update_importance_from_centrality() == 1
        (props,) = await graph.reads.get_event_nodes(["e0"])
        assert props["importance_score"] == 6


class TestNamedOperations:
    async def test_session_operations(self, graph: GraphBackend) -> None:
        await graph.merge_event_nodes_batch(
            [
                event_node("late", session_id="s1", minutes_ago=1, agent_id="agent-7"),
                event_node("early", session_id="s1", minutes_ago=5, agent_id="agent-7"),
                event_node("other", session_id="s2"),
            ]
        )
        assert await graph.session_agent_id("s1") == "agent-7"
        assert await graph.session_agent_id("none") is None
        assert [e["event_id"] for e in await graph.session_events("s1", limit=10)] == [
            "early",
            "late",
        ]
        assert len(await graph.session_events("s1", limit=1)) == 1
        timeline = await graph.session_event_timeline("s1")
        assert [row["event_id"] for row in timeline] == ["early", "late"]
        assert set(timeline[0]) >= {"event_id", "event_type", "occurred_at"}

    async def test_events_for_pruning(self, graph: GraphBackend) -> None:
        await graph.merge_event_nodes_batch(
            [event_node("old", minutes_ago=10), event_node("new", minutes_ago=1)]
        )
        rows = await graph.events_for_pruning(1)
        assert [r["event_id"] for r in rows] == ["old"]
        assert rows[0]["access_count"] == 0

    async def test_delete_all_requires_confirm(self, graph: GraphBackend) -> None:
        await graph.merge_event_node(event_node("evt-1"))
        with pytest.raises(InvalidRequestError):
            await graph.delete_all()
        assert (await _stats(graph))["nodes"]["Event"] == 1
        await graph.delete_all(confirm=True)
        assert (await _stats(graph))["total_nodes"] == 0
