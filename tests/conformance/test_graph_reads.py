"""GraphReads conformance suite (ADR-0019 C3, §5).

Pins the bounded reads the retrieval engine composes: seed strategies,
neighbours, session pages with keyset cursors, session edges, lineage
paths and access recording. Ends with the engine itself running on each
backend's reads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from context_graph.domain.models import EdgeType, LineageQuery
from context_graph.ports.graph_reads import NEIGHBOR_ROW_KEYS
from context_graph.retrieval import RetrievalEngine
from context_graph.settings import DecaySettings
from tests.conformance.graph_fixtures import edge, entity_node, event_node

if TYPE_CHECKING:
    from context_graph.ports.graph_backend import GraphBackend


def _ids(rows: list[dict]) -> list[str]:
    return [row["event_id"] for row in rows]


async def _session(graph: GraphBackend) -> None:
    """s1: e1 (oldest) .. e4 (newest); e3 caused by e1 and e2; e4 references an entity."""
    await graph.merge_event_nodes_batch(
        [
            event_node("e1", minutes_ago=40, importance_score=3, event_type="agent.invoke"),
            event_node("e2", minutes_ago=30, importance_score=9),
            event_node("e3", minutes_ago=20, event_type="workflow.step"),
            event_node("e4", minutes_ago=10, event_type="llm.chat"),
            event_node("x1", session_id="s2", minutes_ago=5),
        ]
    )
    await graph.merge_entity_node(entity_node("ent-1"))
    await graph.create_edges_batch(
        [
            edge("e2", "e1", EdgeType.CAUSED_BY),
            edge("e3", "e1", EdgeType.CAUSED_BY),
            edge("e3", "e2", EdgeType.CAUSED_BY),
            edge("e2", "e1", EdgeType.FOLLOWS, delta_ms=5),
            edge("e4", "ent-1", EdgeType.REFERENCES),
            edge("x1", "ent-1", EdgeType.REFERENCES),
        ]
    )


class TestSeeds:
    async def test_general_is_most_recent(self, graph: GraphBackend) -> None:
        await _session(graph)
        assert _ids(await graph.reads.seed_events("general", "s1", 2)) == ["e4", "e3"]
        assert _ids(await graph.reads.seed_events("no-such-strategy", "s1", 1)) == ["e4"]

    async def test_causal_roots(self, graph: GraphBackend) -> None:
        await _session(graph)
        assert _ids(await graph.reads.seed_events("causal_roots", "s1", 10)) == ["e1", "e2"]

    async def test_temporal_anchors_and_workflow(self, graph: GraphBackend) -> None:
        await _session(graph)
        assert _ids(await graph.reads.seed_events("temporal_anchors", "s1", 10)) == ["e2", "e1"]
        workflow = await graph.reads.seed_events("workflow_pattern", "s1", 10)
        assert _ids(workflow) == ["e2", "e3"]  # tool.* and workflow.*, oldest first

    async def test_entity_hubs(self, graph: GraphBackend) -> None:
        await _session(graph)
        assert _ids(await graph.reads.seed_events("entity_hubs", "s1", 10)) == ["e4"]

    async def test_unknown_session_is_empty(self, graph: GraphBackend) -> None:
        assert await graph.reads.seed_events("general", "nobody", 10) == []


class TestNodesAndNeighbours:
    async def test_get_event_nodes_skips_missing(self, graph: GraphBackend) -> None:
        await _session(graph)
        rows = await graph.reads.get_event_nodes(["e1", "ghost", "ent-1"])
        assert _ids(rows) == ["e1"]

    async def test_cross_session_events(self, graph: GraphBackend) -> None:
        await _session(graph)
        assert _ids(await graph.reads.cross_session_entity_events("s1", 10)) == ["x1"]

    async def test_neighbor_rows(self, graph: GraphBackend) -> None:
        await _session(graph)
        rows = await graph.reads.event_neighbors(["e2", "e1"], 50)

        assert all(set(row) == set(NEIGHBOR_ROW_KEYS) for row in rows)
        from_e2 = {
            (r["rel_type"], r["neighbor_event_id"]) for r in rows if r["seed_event_id"] == "e2"
        }
        assert from_e2 == {("CAUSED_BY", "e1"), ("FOLLOWS", "e1")}
        follows = next(r for r in rows if r["rel_type"] == "FOLLOWS")
        assert follows["rel_props"] == {"delta_ms": 5}
        assert follows["neighbor_labels"] == ["Event"]
        assert follows["neighbor_props"]["event_id"] == "e1"
        # e1 has no outgoing edges: one row with no relationship
        (e1_row,) = [r for r in rows if r["seed_event_id"] == "e1"]
        assert e1_row["rel_type"] is None

    async def test_entity_neighbor(self, graph: GraphBackend) -> None:
        await _session(graph)
        (row,) = await graph.reads.event_neighbors(["e4"], 50)
        assert row["neighbor_entity_id"] == "ent-1"
        assert row["neighbor_event_id"] is None
        assert row["neighbor_labels"] == ["Entity"]

    async def test_neighbor_limit(self, graph: GraphBackend) -> None:
        await _session(graph)
        assert len(await graph.reads.event_neighbors(["e2", "e3"], 2)) == 2


class TestSessionPages:
    async def test_first_page_is_newest_first(self, graph: GraphBackend) -> None:
        await _session(graph)
        assert _ids(await graph.reads.session_events_page("s1", 2)) == ["e4", "e3"]

    async def test_keyset_page_is_oldest_first_after_cursor(self, graph: GraphBackend) -> None:
        await _session(graph)
        (e2,) = await graph.reads.get_event_nodes(["e2"])
        page = await graph.reads.session_events_page("s1", 10, after=(e2["occurred_at"], "e2"))
        assert _ids(page) == ["e3", "e4"]

    async def test_session_edges(self, graph: GraphBackend) -> None:
        await _session(graph)
        rows = await graph.reads.session_edges("s1", ["e1", "e2"])
        assert {(r["source"], r["target"], r["edge_type"]) for r in rows} == {
            ("e2", "e1", "CAUSED_BY"),
            ("e2", "e1", "FOLLOWS"),
        }
        follows = next(r for r in rows if r["edge_type"] == "FOLLOWS")
        assert follows["props"] == {"delta_ms": 5}


class TestLineage:
    async def test_every_path_prefix_is_a_chain(self, graph: GraphBackend) -> None:
        await _session(graph)
        chains = await graph.reads.lineage_chains("e3", max_depth=3, max_nodes=10)
        paths = sorted(tuple(n["event_id"] for n in c["nodes"]) for c in chains)
        assert paths == [("e3", "e1"), ("e3", "e2"), ("e3", "e2", "e1")]
        longest = next(c for c in chains if len(c["nodes"]) == 3)
        assert [(e["source"], e["target"]) for e in longest["edges"]] == [
            ("e3", "e2"),
            ("e2", "e1"),
        ]

    async def test_depth_and_count_bounds(self, graph: GraphBackend) -> None:
        await _session(graph)
        shallow = await graph.reads.lineage_chains("e3", max_depth=1, max_nodes=10)
        assert all(len(c["nodes"]) == 2 for c in shallow)
        assert len(await graph.reads.lineage_chains("e3", max_depth=3, max_nodes=1)) == 1
        assert await graph.reads.lineage_chains("ghost", max_depth=3, max_nodes=10) == []


class TestAccessAndEngine:
    async def test_record_access(self, graph: GraphBackend) -> None:
        await _session(graph)
        await graph.reads.record_access(["e1", "e1", "ghost"], "2026-01-01T00:00:00+00:00")
        (props,) = await graph.reads.get_event_nodes(["e1"])
        assert props["access_count"] == 2
        assert props["last_accessed_at"] == "2026-01-01T00:00:00+00:00"

    async def test_engine_answers_on_this_backend(self, graph: GraphBackend) -> None:
        await _session(graph)
        engine = RetrievalEngine(graph.reads, decay=DecaySettings())

        context = await engine.get_context("s1", max_nodes=10)
        assert set(context.nodes) == {"e1", "e2", "e3", "e4"}
        lineage = await engine.get_lineage(LineageQuery(node_id="e3", max_depth=3))
        assert set(lineage.nodes) == {"e1", "e2", "e3"}
