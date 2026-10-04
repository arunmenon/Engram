"""RetrievalEngine over in-memory ports (ADR-0019 C3, C4).

The engine imports no backend: these tests run it on plain-Python fakes of
GraphReads, KeywordIndex and VectorIndex.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.search import EventStoreKeywordIndex, GraphVectorIndex
from context_graph.domain.models import LineageQuery, SubgraphQuery
from context_graph.domain.pagination import encode_cursor
from context_graph.ports.search import SearchHit
from context_graph.retrieval import RetrievalEngine
from context_graph.settings import DecaySettings


def _event(event_id: str, minutes_ago: int = 0, session_id: str = "s1") -> dict[str, Any]:
    occurred = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return {
        "event_id": event_id,
        "event_type": "tool.execute",
        "occurred_at": occurred.isoformat(),
        "session_id": session_id,
        "agent_id": "agent-1",
        "trace_id": "trace-1",
        "global_position": f"{minutes_ago}-0",
        "importance_score": 5,
    }


class FakeGraphReads:
    """In-memory GraphReads."""

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.events = {e["event_id"]: e for e in events}
        self.edges: list[tuple[str, str, str]] = []
        self.seed_calls: list[str] = []
        self.accessed: list[str] = []

    async def seed_events(self, strategy, session_id, limit, *, timeout_s=None):
        self.seed_calls.append(strategy)
        if strategy != "general":
            return []
        ordered = sorted(self.events.values(), key=lambda e: e["occurred_at"], reverse=True)
        return [e for e in ordered if e["session_id"] == session_id][:limit]

    async def get_event_nodes(self, event_ids, *, timeout_s=None):
        return [self.events[i] for i in event_ids if i in self.events]

    async def cross_session_entity_events(self, session_id, limit, *, timeout_s=None):
        return []

    async def event_neighbors(self, event_ids, neighbor_limit, *, timeout_s=None):
        rows = []
        for source, target, edge_type in self.edges:
            if source in event_ids:
                rows.append(
                    {
                        "seed_event_id": source,
                        "rel_type": edge_type,
                        "rel_props": {},
                        "neighbor_labels": ["Event"],
                        "neighbor_props": self.events[target],
                        "neighbor_event_id": target,
                        "neighbor_entity_id": None,
                        "neighbor_summary_id": None,
                    }
                )
        return rows[:neighbor_limit]

    async def session_events_page(self, session_id, limit, *, after=None, timeout_s=None):
        session = [e for e in self.events.values() if e["session_id"] == session_id]
        if after is None:
            return sorted(session, key=lambda e: e["occurred_at"], reverse=True)[:limit]
        ordered = sorted(session, key=lambda e: (e["occurred_at"], e["event_id"]))
        return [e for e in ordered if (e["occurred_at"], e["event_id"]) > after][:limit]

    async def session_edges(self, session_id, event_ids, *, timeout_s=None):
        return [
            {"source": s, "target": t, "edge_type": k, "props": {}}
            for s, t, k in self.edges
            if s in event_ids and t in event_ids
        ]

    async def lineage_chains(self, node_id, max_depth, max_nodes, *, timeout_s=None):
        chains = []
        for source, target, edge_type in self.edges:
            if source == node_id and edge_type == "CAUSED_BY":
                chains.append(
                    {
                        "nodes": [self.events[source], self.events[target]],
                        "edges": [{"source": source, "target": target, "properties": {}}],
                    }
                )
        return chains[:max_nodes]

    async def record_access(self, event_ids, accessed_at):
        self.accessed.extend(event_ids)


class FakeKeywordIndex:
    def __init__(self, ids: list[str]) -> None:
        self.ids = ids

    @property
    def scores_are_native(self) -> bool:
        return False

    async def search(self, text, *, session_id=None, limit=50):
        return [SearchHit(id=i, rank=r, score=1.0 / (r + 1)) for r, i in enumerate(self.ids)]


def _engine(graph: FakeGraphReads, **kwargs: Any) -> RetrievalEngine:
    return RetrievalEngine(graph, decay=DecaySettings(), **kwargs)


class TestSubgraph:
    @pytest.mark.asyncio()
    async def test_fuses_graph_and_keyword_seeds_and_expands(self) -> None:
        graph = FakeGraphReads([_event("evt-1", 1), _event("evt-2", 2), _event("evt-3", 3)])
        graph.edges.append(("evt-1", "evt-3", "FOLLOWS"))
        engine = _engine(graph, keyword_index=FakeKeywordIndex(["evt-2"]))

        response = await engine.get_subgraph(
            SubgraphQuery(query="what happened", session_id="s1", agent_id="a1")
        )

        assert set(response.nodes) == {"evt-1", "evt-2", "evt-3"}
        assert response.meta.retrieval_channels == {"graph": 3, "vector": 0, "bm25": 1}
        assert response.nodes["evt-3"].retrieval_reason in {"direct", "proactive"}
        assert sorted(graph.accessed) == ["evt-1", "evt-2", "evt-3"]

    @pytest.mark.asyncio()
    async def test_strategy_without_results_falls_back_to_general(self) -> None:
        graph = FakeGraphReads([_event("evt-1")])
        engine = _engine(graph)
        await engine.get_subgraph(
            SubgraphQuery(query="why did it fail", session_id="s1", agent_id="a1")
        )
        assert graph.seed_calls[-1] == "general"
        assert len(graph.seed_calls) == 2

    @pytest.mark.asyncio()
    async def test_failing_keyword_channel_is_skipped(self) -> None:
        graph = FakeGraphReads([_event("evt-1")])
        broken = MagicMock()
        broken.search = AsyncMock(side_effect=RuntimeError("index down"))
        engine = _engine(graph, keyword_index=broken)
        response = await engine.get_subgraph(
            SubgraphQuery(query="anything", session_id="s1", agent_id="a1")
        )
        assert "evt-1" in response.nodes
        assert response.meta.retrieval_channels["bm25"] == 0

    @pytest.mark.asyncio()
    async def test_provenance_names_event_log_backend(self) -> None:
        graph = FakeGraphReads([_event("evt-1")])
        engine = _engine(graph, provenance_source="spanner")
        response = await engine.get_subgraph(
            SubgraphQuery(query="anything", session_id="s1", agent_id="a1")
        )
        assert response.nodes["evt-1"].provenance.source == "spanner"


class TestContext:
    @pytest.mark.asyncio()
    async def test_pages_with_keyset_cursor(self) -> None:
        events = [_event(f"evt-{i}", minutes_ago=10 - i) for i in range(5)]
        graph = FakeGraphReads(events)
        graph.edges.append(("evt-3", "evt-4", "FOLLOWS"))
        engine = _engine(graph)

        first = await engine.get_context("s1", max_nodes=2)
        assert len(first.nodes) == 2
        assert first.pagination.has_more is True
        assert first.pagination.cursor is not None

        cursor = encode_cursor(events[1]["occurred_at"], "evt-1")
        second = await engine.get_context("s1", max_nodes=10, cursor=cursor)
        assert set(second.nodes) == {"evt-2", "evt-3", "evt-4"}
        assert [(e.source, e.target) for e in second.edges] == [("evt-3", "evt-4")]


class TestLineage:
    @pytest.mark.asyncio()
    async def test_follows_caused_by_chains(self) -> None:
        graph = FakeGraphReads([_event("evt-1"), _event("evt-0", 5)])
        graph.edges.append(("evt-1", "evt-0", "CAUSED_BY"))
        engine = _engine(graph)

        response = await engine.get_lineage(LineageQuery(node_id="evt-1", max_depth=3))
        assert set(response.nodes) == {"evt-1", "evt-0"}
        assert response.edges[0].edge_type == "CAUSED_BY"

    @pytest.mark.asyncio()
    async def test_offset_cursor_skips_chains(self) -> None:
        graph = FakeGraphReads([_event("evt-1"), _event("evt-0", 5)])
        graph.edges.append(("evt-1", "evt-0", "CAUSED_BY"))
        engine = _engine(graph)
        cursor = base64.urlsafe_b64encode(b"1").decode()
        response = await engine.get_lineage(
            LineageQuery(node_id="evt-1", max_depth=3, cursor=cursor)
        )
        assert response.nodes == {}


class TestSearchAdapters:
    @pytest.mark.asyncio()
    async def test_keyword_index_rank_scores_in_unit_range(self) -> None:
        store = AsyncMock()
        store.search_bm25.return_value = [MagicMock(event_id="a"), MagicMock(event_id="b")]
        index = EventStoreKeywordIndex(store)
        hits = await index.search("q", session_id="s1", limit=5)
        store.search_bm25.assert_awaited_once_with("q", session_id="s1", limit=5)
        assert [(h.id, h.rank, h.score) for h in hits] == [("a", 0, 1.0), ("b", 1, 0.5)]
        assert index.scores_are_native is False

    @pytest.mark.asyncio()
    async def test_vector_index_clamps_and_keeps_fields(self) -> None:
        graph = AsyncMock()
        graph.search_similar_entities.return_value = [
            {"entity_id": "e1", "name": "n", "entity_type": "tool", "score": 1.2},
            {"entity_id": "e2", "name": "m", "entity_type": "tool", "score": 0.6},
        ]
        index = GraphVectorIndex(graph)
        hits = await index.nearest([0.1], top_k=2, threshold=0.5)
        graph.search_similar_entities.assert_awaited_once_with([0.1], top_k=2, threshold=0.5)
        assert [(h.id, h.score) for h in hits] == [("e1", 1.0), ("e2", 0.6)]
        assert hits[0].fields == {"name": "n", "entity_type": "tool"}
