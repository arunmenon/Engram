"""Tests for L4 hybrid retrieval with RRF fusion.

Tests the RetrievalPipeline channel helpers and RRF integration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from context_graph.adapters.neo4j.retrieval import RetrievalDeps, RetrievalPipeline
from context_graph.domain.models import SubgraphQuery
from context_graph.domain.reranking import reciprocal_rank_fusion

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_neo4j_settings() -> MagicMock:
    """Reusable Neo4j settings mock."""
    settings = MagicMock()
    settings.uri = "bolt://localhost:7687"
    settings.username = "neo4j"
    settings.password = MagicMock()
    settings.password.get_secret_value.return_value = "test"
    settings.max_connection_pool_size = 5
    settings.database = "neo4j"
    return settings


@pytest.fixture
def mock_decay_settings() -> MagicMock:
    """Reusable DecaySettings mock with all required fields."""
    decay = MagicMock()
    decay.s_base = 168.0
    decay.s_boost = 24.0
    decay.entity_s_base = 336.0
    decay.entity_s_boost = 24.0
    decay.weight_recency = 1.0
    decay.weight_importance = 1.0
    decay.weight_relevance = 1.0
    decay.weight_user_affinity = 0.5
    return decay


def _make_deps(
    mock_decay_settings: MagicMock,
    driver: Any = None,
    event_store: Any = None,
    embedding_service: Any = None,
) -> RetrievalDeps:
    """Build a RetrievalDeps with sensible defaults."""
    return RetrievalDeps(
        driver=driver or AsyncMock(),
        database="neo4j",
        embedding_service=embedding_service,
        intent_classifier=None,
        llm_client=None,
        event_store=event_store,
        decay=mock_decay_settings,
        ppr_settings=None,
        query_timeout_s=5.0,
        neighbor_limit=50,
        search_similar_entities=AsyncMock(return_value=[]),
    )


def _make_event_props(event_id: str, session_id: str = "sess-1") -> dict[str, Any]:
    """Create a minimal event properties dict for Neo4j record mocking."""
    return {
        "event_id": event_id,
        "event_type": "agent.invoke",
        "occurred_at": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "agent_id": "agent-1",
        "trace_id": "trace-1",
        "global_position": "1707644400000-0",
        "importance_score": 5,
        "access_count": 0,
    }


def _make_query(query_text: str = "test query", session_id: str = "sess-1") -> SubgraphQuery:
    return SubgraphQuery(
        query=query_text,
        session_id=session_id,
        agent_id="agent-1",
        max_nodes=50,
    )


# ---------------------------------------------------------------------------
# RRF fusion integration tests (pure domain)
# ---------------------------------------------------------------------------


class TestRRFFusionIntegration:
    """Test RRF fusion with realistic multi-channel inputs."""

    def test_graph_only_channel(self) -> None:
        """When only graph channel returns results, those become the seeds."""
        graph_seeds = [("evt-1", 0.9), ("evt-2", 0.7), ("evt-3", 0.5)]
        vector_seeds: list[tuple[str, float]] = []
        bm25_seeds: list[tuple[str, float]] = []
        fused = reciprocal_rank_fusion([graph_seeds, vector_seeds, bm25_seeds])
        ids = [item_id for item_id, _ in fused]
        assert ids == ["evt-1", "evt-2", "evt-3"]

    def test_all_channels_overlap(self) -> None:
        """Items found by all three channels should rank highest."""
        graph_seeds = [("evt-1", 0.9), ("evt-2", 0.7)]
        vector_seeds = [("evt-1", 0.95), ("evt-3", 0.8)]
        bm25_seeds = [("evt-1", 0.85), ("evt-4", 0.6)]
        fused = reciprocal_rank_fusion([graph_seeds, vector_seeds, bm25_seeds])
        assert fused[0][0] == "evt-1"

    def test_disjoint_channels(self) -> None:
        """Disjoint channels should return all items."""
        graph_seeds = [("a", 0.9)]
        vector_seeds = [("b", 0.8)]
        bm25_seeds = [("c", 0.7)]
        fused = reciprocal_rank_fusion([graph_seeds, vector_seeds, bm25_seeds])
        ids = {item_id for item_id, _ in fused}
        assert ids == {"a", "b", "c"}

    def test_empty_all_channels(self) -> None:
        """If all channels are empty, fusion returns empty."""
        fused = reciprocal_rank_fusion([[], [], []])
        assert fused == []

    def test_two_channel_agreement_beats_single(self) -> None:
        """Item in 2 channels should rank above item in only 1 channel."""
        graph_seeds = [("shared", 0.9), ("only_graph", 0.8)]
        vector_seeds = [("shared", 0.7)]
        bm25_seeds: list[tuple[str, float]] = []
        fused = reciprocal_rank_fusion([graph_seeds, vector_seeds, bm25_seeds])
        scores = dict(fused)
        assert scores["shared"] > scores["only_graph"]

    def test_exception_channels_filtered(self) -> None:
        """Simulate gather with exceptions — only valid results used."""
        graph_seeds = [("evt-1", 0.9)]
        valid_lists = [graph_seeds]
        fused = reciprocal_rank_fusion(valid_lists)
        assert len(fused) == 1
        assert fused[0][0] == "evt-1"


# ---------------------------------------------------------------------------
# RetrievalPipeline channel method tests
# ---------------------------------------------------------------------------


class TestGraphSeeds:
    """Test _get_graph_seeds helper on the pipeline."""

    @pytest.mark.asyncio
    async def test_returns_ranked_seeds(self, mock_decay_settings: MagicMock) -> None:
        """Graph seeds should return (event_id, rank_score) pairs."""
        mock_records = []
        for eid in ["evt-1", "evt-2"]:
            mock_record = MagicMock()
            mock_record.__getitem__ = lambda self, key, eid=eid: _make_event_props(eid)
            mock_records.append(mock_record)

        async def make_aiter():
            for r in mock_records:
                yield r

        mock_result = MagicMock()
        mock_result.__aiter__ = lambda self: make_aiter()

        mock_session = AsyncMock()
        mock_session.run.return_value = mock_result

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session_cm

        deps = _make_deps(mock_decay_settings, driver=mock_driver)
        pipeline = RetrievalPipeline(deps)

        query = _make_query()
        seeds = await pipeline._get_graph_seeds(
            query,
            seed_limit=10,
            seed_query="MATCH (e:Event) RETURN e LIMIT $seed_limit",
            seed_strategy="general",
        )
        assert len(seeds) == 2
        assert seeds[0][0] == "evt-1"
        assert seeds[0][1] == 1.0


class TestVectorSeeds:
    """Test _get_vector_seeds helper on the pipeline."""

    @pytest.mark.asyncio
    async def test_returns_empty_without_embedding(self, mock_decay_settings: MagicMock) -> None:
        """No embedding should return empty list."""
        deps = _make_deps(mock_decay_settings)
        pipeline = RetrievalPipeline(deps)
        seeds = await pipeline._get_vector_seeds(None, limit=10)
        assert seeds == []

    @pytest.mark.asyncio
    async def test_returns_entity_seeds(self, mock_decay_settings: MagicMock) -> None:
        """Vector seeds should come from search_similar_entities."""
        deps = _make_deps(mock_decay_settings)
        deps = RetrievalDeps(
            driver=deps.driver,
            database=deps.database,
            embedding_service=deps.embedding_service,
            intent_classifier=deps.intent_classifier,
            llm_client=deps.llm_client,
            event_store=deps.event_store,
            decay=deps.decay,
            ppr_settings=deps.ppr_settings,
            query_timeout_s=deps.query_timeout_s,
            neighbor_limit=deps.neighbor_limit,
            search_similar_entities=AsyncMock(
                return_value=[
                    {"entity_id": "ent-1", "name": "test", "entity_type": "concept", "score": 0.9},
                    {"entity_id": "ent-2", "name": "test2", "entity_type": "tool", "score": 0.7},
                ]
            ),
        )
        pipeline = RetrievalPipeline(deps)
        seeds = await pipeline._get_vector_seeds([0.1, 0.2, 0.3], limit=10)
        assert len(seeds) == 2
        assert seeds[0] == ("ent-1", 0.9)

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, mock_decay_settings: MagicMock) -> None:
        """Vector channel should return empty on error, not raise."""
        deps = _make_deps(mock_decay_settings)
        deps = RetrievalDeps(
            driver=deps.driver,
            database=deps.database,
            embedding_service=deps.embedding_service,
            intent_classifier=deps.intent_classifier,
            llm_client=deps.llm_client,
            event_store=deps.event_store,
            decay=deps.decay,
            ppr_settings=deps.ppr_settings,
            query_timeout_s=deps.query_timeout_s,
            neighbor_limit=deps.neighbor_limit,
            search_similar_entities=AsyncMock(side_effect=RuntimeError("boom")),
        )
        pipeline = RetrievalPipeline(deps)
        seeds = await pipeline._get_vector_seeds([0.1, 0.2], limit=10)
        assert seeds == []


class TestBM25Seeds:
    """Test _get_bm25_seeds helper on the pipeline."""

    @pytest.mark.asyncio
    async def test_returns_empty_without_event_store(self, mock_decay_settings: MagicMock) -> None:
        """No event_store should return empty list."""
        deps = _make_deps(mock_decay_settings, event_store=None)
        pipeline = RetrievalPipeline(deps)
        seeds = await pipeline._get_bm25_seeds("test", "sess-1", 10)
        assert seeds == []

    @pytest.mark.asyncio
    async def test_returns_event_seeds(self, mock_decay_settings: MagicMock) -> None:
        """BM25 seeds should come from event store search_bm25."""
        from context_graph.domain.models import Event

        mock_event_store = AsyncMock()
        evt_id_1 = uuid4()
        evt_id_2 = uuid4()
        mock_event_store.search_bm25.return_value = [
            Event(
                event_id=evt_id_1,
                event_type="agent.invoke",
                occurred_at=datetime.now(UTC),
                session_id="sess-1",
                agent_id="agent-1",
                trace_id="trace-1",
                payload_ref="ref-1",
            ),
            Event(
                event_id=evt_id_2,
                event_type="tool.execute",
                occurred_at=datetime.now(UTC),
                session_id="sess-1",
                agent_id="agent-1",
                trace_id="trace-1",
                payload_ref="ref-2",
            ),
        ]

        deps = _make_deps(mock_decay_settings, event_store=mock_event_store)
        pipeline = RetrievalPipeline(deps)
        seeds = await pipeline._get_bm25_seeds("test query", "sess-1", 10)
        assert len(seeds) == 2
        assert seeds[0][0] == str(evt_id_1)
        assert seeds[0][1] == 1.0

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, mock_decay_settings: MagicMock) -> None:
        """BM25 channel should return empty on error, not raise."""
        mock_event_store = AsyncMock()
        mock_event_store.search_bm25.side_effect = RuntimeError("connection lost")

        deps = _make_deps(mock_decay_settings, event_store=mock_event_store)
        pipeline = RetrievalPipeline(deps)
        seeds = await pipeline._get_bm25_seeds("test", "sess-1", 10)
        assert seeds == []


# ---------------------------------------------------------------------------
# Retrieval channels in QueryMeta
# ---------------------------------------------------------------------------


class TestRetrievalChannelsMeta:
    """Test that retrieval_channels field is populated in QueryMeta."""

    def test_query_meta_has_retrieval_channels(self) -> None:
        from context_graph.domain.models import QueryMeta

        meta = QueryMeta(retrieval_channels={"graph": 5, "vector": 3, "bm25": 0})
        assert meta.retrieval_channels["graph"] == 5
        assert meta.retrieval_channels["vector"] == 3
        assert meta.retrieval_channels["bm25"] == 0

    def test_query_meta_default_empty_channels(self) -> None:
        from context_graph.domain.models import QueryMeta

        meta = QueryMeta()
        assert meta.retrieval_channels == {}
