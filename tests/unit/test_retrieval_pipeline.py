"""Integration tests for the RetrievalPipeline.get_subgraph() orchestration.

Exercises the full pipeline with mocked Neo4j driver, embedding service,
event store, and entity search — verifying that all 3 retrieval channels
feed into the final AtlasResponse correctly.

Source: Review finding #6
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from context_graph.adapters.neo4j.retrieval import RetrievalDeps, RetrievalPipeline
from context_graph.domain.models import SubgraphQuery
from context_graph.settings import DecaySettings, PPRSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event_props(event_id: str, *, session_id: str = "sess-1") -> dict:
    """Build a minimal event property dict as returned by Neo4j records."""
    return {
        "event_id": event_id,
        "event_type": "tool.execute",
        "occurred_at": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "agent_id": "agent-1",
        "trace_id": "trace-1",
        "global_position": "1707644400000-0",
        "importance_score": 5,
        "access_count": 1,
        "embedding": [],
    }


def _make_neo4j_record(props: dict) -> MagicMock:
    """Build a mock Neo4j record supporting record['e'] dict access."""
    record = MagicMock()
    record.__getitem__ = MagicMock(side_effect=lambda key: props if key == "e" else None)
    record.get = MagicMock(side_effect=lambda key, default=None: props.get(key, default))
    return record


def _make_bm25_event(event_id: str) -> MagicMock:
    """Build a mock event object with an event_id attribute for BM25 results."""
    from uuid import UUID

    event = MagicMock()
    event.event_id = UUID("00000000-0000-0000-0000-" + event_id.replace("evt-", "").zfill(12))
    return event


async def _mock_async_iter(records: list):
    """Create an async iterator from a list of records."""
    for r in records:
        yield r


def _build_mock_driver(
    seed_records: list,
    fetch_records: list,
    neighbor_records: list | None = None,
) -> MagicMock:
    """Build a mock Neo4j AsyncDriver with staged query responses.

    Returns responses in the order:
    1. Graph seed query (via _get_graph_seeds)
    2. Batch fetch (via _fetch_seed_nodes)
    3. Neighbor expansion (via _expand_neighbors)
    4. Bump access counts (via _bump_access_counts, returns None)
    """
    mock_driver = MagicMock()
    call_counter = {"value": 0}

    async def mock_run(*args, **kwargs):
        """Return staged results based on call order."""
        idx = call_counter["value"]
        call_counter["value"] += 1

        result = AsyncMock()

        if idx == 0:
            # Graph seed query
            result.__aiter__ = MagicMock(return_value=_mock_async_iter(seed_records))
        elif idx == 1:
            # Batch fetch seed node properties
            result.__aiter__ = MagicMock(return_value=_mock_async_iter(fetch_records))
        elif idx == 2:
            # Neighbor expansion
            result.__aiter__ = MagicMock(return_value=_mock_async_iter(neighbor_records or []))
        else:
            # Remaining calls (bump access, etc.) — empty results
            result.__aiter__ = MagicMock(return_value=_mock_async_iter([]))

        return result

    mock_session = AsyncMock()
    mock_session.run = AsyncMock(side_effect=mock_run)
    mock_session.execute_write = AsyncMock(return_value=None)

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_driver.session.return_value = mock_session_cm

    return mock_driver


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetSubgraphPipeline:
    """Integration tests for the full get_subgraph pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_atlas_response(self) -> None:
        """Pipeline returns a well-formed AtlasResponse with nodes, edges, and meta."""
        # Build 3 seed events
        event_props_list = [_make_event_props(f"evt-{i}") for i in range(3)]
        seed_records = [_make_neo4j_record(p) for p in event_props_list]
        fetch_records = [_make_neo4j_record(p) for p in event_props_list]

        mock_driver = _build_mock_driver(seed_records, fetch_records)

        # Embedding service returns a fixed vector
        mock_embedding = AsyncMock()
        mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 384)

        # BM25 event store returns 2 events
        mock_event_store = AsyncMock()
        mock_event_store.search_bm25 = AsyncMock(
            return_value=[_make_bm25_event("evt-0"), _make_bm25_event("evt-1")]
        )

        # Vector entity search returns 1 entity match
        mock_search_entities = AsyncMock(
            return_value=[{"entity_id": "entity-payment", "score": 0.92}]
        )

        deps = RetrievalDeps(
            driver=mock_driver,
            database="neo4j",
            embedding_service=mock_embedding,
            intent_classifier=None,  # uses keyword fallback
            llm_client=None,  # no HyDE
            event_store=mock_event_store,
            decay=DecaySettings(),
            ppr_settings=None,
            query_timeout_s=5.0,
            neighbor_limit=50,
            search_similar_entities=mock_search_entities,
        )

        pipeline = RetrievalPipeline(deps)
        query = SubgraphQuery(
            query="Why did the payment fail?",
            session_id="sess-1",
            agent_id="agent-1",
        )

        response = await pipeline.get_subgraph(query)

        # Verify AtlasResponse structure
        assert response.nodes is not None
        assert len(response.nodes) > 0
        assert isinstance(response.edges, list)
        assert response.pagination is not None

        # Meta has retrieval channels for all 3 channels
        assert response.meta.retrieval_channels is not None
        assert "graph" in response.meta.retrieval_channels
        assert "vector" in response.meta.retrieval_channels
        assert "bm25" in response.meta.retrieval_channels

        # Seed nodes are populated
        assert len(response.meta.seed_nodes) > 0

        # Inferred intents have values (keyword fallback for "Why did...")
        assert len(response.meta.inferred_intents) > 0
        assert "why" in response.meta.inferred_intents

        # Seed strategy should be causal_roots for "why" intent
        assert response.meta.seed_strategy is not None

        # Capacity is set
        assert response.meta.capacity is not None
        assert response.meta.capacity.max_nodes == 100

    @pytest.mark.asyncio
    async def test_pipeline_with_no_embedding_service(self) -> None:
        """Pipeline works when embedding_service is None (vector channel empty)."""
        event_props_list = [_make_event_props(f"evt-{i}") for i in range(2)]
        seed_records = [_make_neo4j_record(p) for p in event_props_list]
        fetch_records = [_make_neo4j_record(p) for p in event_props_list]

        mock_driver = _build_mock_driver(seed_records, fetch_records)

        deps = RetrievalDeps(
            driver=mock_driver,
            database="neo4j",
            embedding_service=None,
            intent_classifier=None,
            llm_client=None,
            event_store=None,
            decay=DecaySettings(),
            ppr_settings=None,
            query_timeout_s=5.0,
            neighbor_limit=50,
            search_similar_entities=AsyncMock(return_value=[]),
        )

        pipeline = RetrievalPipeline(deps)
        query = SubgraphQuery(
            query="When did the deployment happen?",
            session_id="sess-1",
            agent_id="agent-1",
        )

        response = await pipeline.get_subgraph(query)

        assert len(response.nodes) > 0
        # Vector channel should report 0 seeds (no embedding service)
        assert response.meta.retrieval_channels["vector"] == 0
        # BM25 channel should report 0 (no event_store)
        assert response.meta.retrieval_channels["bm25"] == 0


class TestPPRIntegration:
    """Tests verifying PPR post-processing when enabled."""

    @pytest.mark.asyncio
    async def test_ppr_blends_scores_when_enabled(self) -> None:
        """When PPR is enabled, nodes should have ppr_score > 0.0."""
        event_props_list = [_make_event_props(f"evt-{i}") for i in range(3)]
        seed_records = [_make_neo4j_record(p) for p in event_props_list]
        fetch_records = [_make_neo4j_record(p) for p in event_props_list]

        # Build neighbor records that create edges for PPR adjacency
        neighbor_records = []
        for i in range(2):
            nrec = MagicMock()
            nrec.get = MagicMock(
                side_effect=lambda key, default=None, i=i: {
                    "seed_event_id": "evt-0",
                    "rel_type": "FOLLOWS",
                    "neighbor_event_id": f"evt-{i + 1}",
                    "neighbor_entity_id": None,
                    "neighbor_props": _make_event_props(f"evt-{i + 1}"),
                    "neighbor_labels": ["Event"],
                    "rel_props": {"delta_ms": 100},
                }.get(key, default)
            )
            neighbor_records.append(nrec)

        mock_driver = _build_mock_driver(seed_records, fetch_records, neighbor_records)

        deps = RetrievalDeps(
            driver=mock_driver,
            database="neo4j",
            embedding_service=None,
            intent_classifier=None,
            llm_client=None,
            event_store=None,
            decay=DecaySettings(),
            ppr_settings=PPRSettings(enabled=True, blend_weight=0.3),
            query_timeout_s=5.0,
            neighbor_limit=50,
            search_similar_entities=AsyncMock(return_value=[]),
        )

        pipeline = RetrievalPipeline(deps)
        query = SubgraphQuery(
            query="What tools were used?",
            session_id="sess-1",
            agent_id="agent-1",
        )

        response = await pipeline.get_subgraph(query)

        assert len(response.nodes) > 0
        # At least one seed node should have a non-zero PPR score
        ppr_scores = [
            n.scores.ppr_score for n in response.nodes.values() if n.scores.ppr_score > 0.0
        ]
        assert len(ppr_scores) > 0, "PPR should assign non-zero scores to at least some nodes"
