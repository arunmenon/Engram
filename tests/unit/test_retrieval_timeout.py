"""Tests for LLM timeout handling in the retrieval pipeline."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.adapters.neo4j.retrieval import RetrievalDeps, RetrievalPipeline


def _make_deps(**overrides) -> RetrievalDeps:
    """Create a RetrievalDeps with sensible mock defaults."""
    defaults = {
        "driver": AsyncMock(),
        "database": "neo4j",
        "embedding_service": None,
        "intent_classifier": None,
        "llm_client": None,
        "event_store": None,
        "decay": MagicMock(
            s_base=168.0,
            s_boost=24.0,
            entity_s_base=336.0,
            entity_s_boost=24.0,
            weight_recency=1.0,
            weight_importance=1.0,
            weight_relevance=1.0,
            weight_user_affinity=0.5,
        ),
        "ppr_settings": None,
        "query_timeout_s": 5.0,
        "neighbor_limit": 50,
        "search_similar_entities": AsyncMock(return_value=[]),
    }
    defaults.update(overrides)
    return RetrievalDeps(**defaults)


class TestHyDETimeout:
    """Tests for HyDE LLM timeout handling."""

    @pytest.mark.asyncio
    async def test_hyde_timeout_falls_back_gracefully(self) -> None:
        """When HyDE LLM call times out, retrieval should continue without expansion."""
        slow_llm = AsyncMock()

        async def _slow_generate(prompt: str) -> str:
            await asyncio.sleep(10)  # simulate slow LLM
            return "expanded query"

        slow_llm.generate_text = _slow_generate

        deps = _make_deps(llm_client=slow_llm)
        pipeline = RetrievalPipeline(deps)

        query = MagicMock()
        query.query = "why did the build fail?"
        query.use_hyde = True
        query.session_id = "test-session"
        query.max_nodes = 10
        query.max_depth = 3
        query.seed_nodes = None
        query.intent = None
        query.cursor = None

        # Mock the channels to return empty results
        with (
            patch.object(pipeline, "_get_graph_seeds", new_callable=AsyncMock, return_value=[]),
            patch.object(pipeline, "_get_vector_seeds", new_callable=AsyncMock, return_value=[]),
            patch.object(pipeline, "_get_bm25_seeds", new_callable=AsyncMock, return_value=[]),
            patch.object(pipeline, "_fetch_seed_nodes", new_callable=AsyncMock),
            patch.object(pipeline, "_expand_neighbors", new_callable=AsyncMock),
            patch.object(pipeline, "_bump_access_counts", new_callable=AsyncMock),
        ):
            # Should complete without error despite LLM timeout
            result = await pipeline.get_subgraph(query)
            assert result is not None
            assert result.meta.nodes_returned == 0


class TestIntentClassificationTimeout:
    """Tests for intent classification LLM timeout handling."""

    @pytest.mark.asyncio
    async def test_intent_timeout_falls_back_to_keyword(self) -> None:
        """When LLM intent classifier times out, should fall back to keyword classifier."""
        slow_classifier = AsyncMock()

        async def _slow_classify(query: str) -> dict[str, float]:
            await asyncio.sleep(10)
            return {"why": 1.0}

        slow_classifier.classify = _slow_classify

        deps = _make_deps(intent_classifier=slow_classifier)
        pipeline = RetrievalPipeline(deps)

        query = MagicMock()
        query.query = "why did the build fail?"
        query.use_hyde = False
        query.session_id = "test-session"
        query.max_nodes = 10
        query.max_depth = 3
        query.seed_nodes = None
        query.intent = None
        query.cursor = None

        with (
            patch.object(pipeline, "_get_graph_seeds", new_callable=AsyncMock, return_value=[]),
            patch.object(pipeline, "_get_vector_seeds", new_callable=AsyncMock, return_value=[]),
            patch.object(pipeline, "_get_bm25_seeds", new_callable=AsyncMock, return_value=[]),
            patch.object(pipeline, "_fetch_seed_nodes", new_callable=AsyncMock),
            patch.object(pipeline, "_expand_neighbors", new_callable=AsyncMock),
            patch.object(pipeline, "_bump_access_counts", new_callable=AsyncMock),
        ):
            result = await pipeline.get_subgraph(query)
            assert result is not None
            # Should have inferred_intents from keyword fallback
            assert "why" in result.meta.inferred_intents
