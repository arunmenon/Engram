"""Tests for domain.reranking — RRF fusion and MMR diversity re-ranking."""

from __future__ import annotations

import math

import pytest

from context_graph.domain.reranking import (
    _cosine_similarity,
    maximal_marginal_relevance,
    reciprocal_rank_fusion,
)

# ---------------------------------------------------------------------------
# RRF tests
# ---------------------------------------------------------------------------


class TestReciprocalRankFusion:
    """Tests for reciprocal_rank_fusion()."""

    def test_rrf_single_list(self) -> None:
        """A single ranked list should preserve relative order."""
        ranked = [("a", 0.9), ("b", 0.7), ("c", 0.3)]
        result = reciprocal_rank_fusion([ranked])
        ids = [item_id for item_id, _ in result]
        assert ids == ["a", "b", "c"]

    def test_rrf_three_channels(self) -> None:
        """Items appearing in multiple channels get higher RRF scores."""
        graph = [("a", 0.9), ("b", 0.7)]
        vector = [("b", 0.95), ("c", 0.8)]
        bm25 = [("a", 0.85), ("c", 0.6)]
        result = reciprocal_rank_fusion([graph, vector, bm25])
        scores = dict(result)
        # "a" appears in graph(rank 0) and bm25(rank 0)
        # "b" appears in graph(rank 1) and vector(rank 0)
        # "c" appears in vector(rank 1) and bm25(rank 1)
        # All appear in exactly 2 lists, but at different ranks
        assert "a" in scores
        assert "b" in scores
        assert "c" in scores

    def test_rrf_empty_lists(self) -> None:
        """Empty input should return empty output."""
        assert reciprocal_rank_fusion([]) == []
        assert reciprocal_rank_fusion([[], [], []]) == []

    def test_rrf_disjoint_lists(self) -> None:
        """Disjoint lists should return all items."""
        list_a = [("x", 1.0)]
        list_b = [("y", 1.0)]
        result = reciprocal_rank_fusion([list_a, list_b])
        ids = {item_id for item_id, _ in result}
        assert ids == {"x", "y"}
        # Same rank in their respective lists => equal RRF score
        scores = dict(result)
        assert scores["x"] == pytest.approx(scores["y"])

    def test_rrf_overlapping_items(self) -> None:
        """Item appearing in all lists should rank highest."""
        list_a = [("common", 1.0), ("only_a", 0.5)]
        list_b = [("common", 0.9), ("only_b", 0.4)]
        list_c = [("common", 0.8), ("only_c", 0.3)]
        result = reciprocal_rank_fusion([list_a, list_b, list_c])
        # "common" is rank 0 in all 3 lists => highest score
        assert result[0][0] == "common"

    def test_rrf_single_item(self) -> None:
        """Single item in a single list should work."""
        result = reciprocal_rank_fusion([[("solo", 0.5)]])
        assert len(result) == 1
        assert result[0][0] == "solo"
        assert result[0][1] == pytest.approx(1.0 / 61)  # k=60, rank=0 => 1/(60+1)

    def test_rrf_k_parameter(self) -> None:
        """Different k values should change scores but preserve relative order."""
        ranked = [("a", 0.9), ("b", 0.7)]
        result_k60 = reciprocal_rank_fusion([ranked], k=60)
        result_k10 = reciprocal_rank_fusion([ranked], k=10)
        # Both should have same order
        assert [x[0] for x in result_k60] == [x[0] for x in result_k10]
        # k=10 produces higher scores
        score_a_k60 = dict(result_k60)["a"]
        score_a_k10 = dict(result_k10)["a"]
        assert score_a_k10 > score_a_k60

    def test_rrf_preserves_top_items(self) -> None:
        """Items ranked highly in multiple lists should be at the top."""
        list_a = [("top", 1.0), ("mid", 0.5), ("low", 0.1)]
        list_b = [("top", 0.95), ("low", 0.4), ("mid", 0.2)]
        result = reciprocal_rank_fusion([list_a, list_b])
        # "top" is rank 0 in both => highest
        assert result[0][0] == "top"

    def test_rrf_score_computation(self) -> None:
        """Verify exact RRF score computation."""
        # Item at rank 0 in list A, rank 2 in list B, k=60
        list_a = [("target", 1.0), ("x", 0.5)]
        list_b = [("y", 1.0), ("z", 0.8), ("target", 0.3)]
        result = reciprocal_rank_fusion([list_a, list_b], k=60)
        scores = dict(result)
        expected = 1.0 / (60 + 1) + 1.0 / (60 + 3)  # rank 0 in A, rank 2 in B
        assert scores["target"] == pytest.approx(expected)

    def test_rrf_large_k_flattens_scores(self) -> None:
        """Very large k should make all rank positions nearly equal."""
        ranked = [("a", 1.0), ("b", 0.1)]
        result = reciprocal_rank_fusion([ranked], k=100000)
        scores = dict(result)
        # Difference between rank 0 and rank 1 should be tiny
        diff = scores["a"] - scores["b"]
        assert diff < 1e-8

    def test_rrf_duplicate_ids_in_same_list(self) -> None:
        """If an ID appears twice in the same list, both ranks contribute."""
        ranked = [("a", 1.0), ("a", 0.5)]
        result = reciprocal_rank_fusion([ranked])
        scores = dict(result)
        expected = 1.0 / 61 + 1.0 / 62
        assert scores["a"] == pytest.approx(expected)


# ---------------------------------------------------------------------------
# MMR tests
# ---------------------------------------------------------------------------


class TestMaximalMarginalRelevance:
    """Tests for maximal_marginal_relevance()."""

    def test_mmr_basic(self) -> None:
        """Basic MMR should return all candidates with adjusted scores."""
        candidates = [
            ("a", 0.9, [1.0, 0.0]),
            ("b", 0.8, [0.0, 1.0]),
            ("c", 0.7, [0.5, 0.5]),
        ]
        result = maximal_marginal_relevance(candidates, selected=[])
        assert len(result) == 3
        # With no selected items, MMR = lambda * relevance (max_sim=0)
        ids = [item_id for item_id, _ in result]
        assert ids[0] == "a"  # highest relevance

    def test_mmr_empty_candidates(self) -> None:
        """Empty candidates should return empty."""
        result = maximal_marginal_relevance([], selected=[])
        assert result == []

    def test_mmr_all_selected(self) -> None:
        """All candidates already selected should be penalized."""
        candidates = [
            ("a", 0.9, [1.0, 0.0]),
            ("b", 0.8, [0.0, 1.0]),
        ]
        result = maximal_marginal_relevance(candidates, selected=["a", "b"])
        # Both should have max_sim = 1.0 (self-similarity penalty)
        for _, score in result:
            # score = lambda * relevance - (1-lambda) * 1.0
            assert score < 0.5  # penalized

    def test_mmr_diversity_boost(self) -> None:
        """Items dissimilar to selected should rank higher than similar ones."""
        # "a" is already selected with embedding [1, 0]
        # "b" is similar to "a", "c" is different
        # Put "a" embedding in candidates so MMR can find it
        candidates_with_a = [
            ("a", 0.9, [1.0, 0.0]),
            ("b", 0.8, [0.95, 0.05]),  # very similar to selected "a"
            ("c", 0.8, [0.0, 1.0]),  # very different from selected "a"
        ]
        result = maximal_marginal_relevance(candidates_with_a, selected=["a"], lambda_param=0.5)
        result_dict = dict(result)
        # "c" should have higher MMR than "b" because it's more diverse
        assert result_dict["c"] > result_dict["b"]

    def test_mmr_lambda_one_ignores_diversity(self) -> None:
        """lambda=1.0 should rank purely by relevance."""
        candidates = [
            ("a", 0.9, [1.0, 0.0]),
            ("b", 0.95, [1.0, 0.0]),  # identical embedding but higher relevance
        ]
        result = maximal_marginal_relevance(candidates, selected=[], lambda_param=1.0)
        assert result[0][0] == "b"

    def test_mmr_reorders_similar_embedding_candidates(self) -> None:
        """MMR should penalize candidates that are similar to already-ranked ones."""
        # Two candidates with identical embeddings and one diverse candidate
        candidates = [
            ("a", 0.9, [1.0, 0.0, 0.0]),  # high relevance, direction X
            ("b", 0.85, [0.99, 0.01, 0.0]),  # similar to a, slightly lower relevance
            ("c", 0.8, [0.0, 1.0, 0.0]),  # different direction Y
        ]
        # With no selected: first pick is "a" (highest relevance)
        # After "a" is picked, "c" should be preferred over "b" due to diversity
        result = maximal_marginal_relevance(candidates, selected=["a"], lambda_param=0.5)
        result_dict = dict(result)
        # "c" is diverse from "a", so should get higher MMR than "b"
        assert result_dict["c"] > result_dict["b"]

    def test_mmr_lambda_zero_maximizes_diversity(self) -> None:
        """lambda=0.0 should rank purely by diversity (negative similarity)."""
        # "a" is already selected
        candidates_with_a = [
            ("a", 0.9, [1.0, 0.0]),
            ("b", 0.5, [0.0, 1.0]),  # low relevance but different
        ]
        result = maximal_marginal_relevance(candidates_with_a, selected=["a"], lambda_param=0.0)
        result_dict = dict(result)
        # "b" should score higher: -1*(sim to a) is lower for b than for a
        assert result_dict["b"] > result_dict["a"]


# ---------------------------------------------------------------------------
# Cosine similarity helper tests
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    """Tests for the internal _cosine_similarity helper."""

    def test_identical_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        assert _cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_empty_vectors(self) -> None:
        assert _cosine_similarity([], []) == 0.0

    def test_zero_vector(self) -> None:
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_mismatched_lengths(self) -> None:
        assert _cosine_similarity([1.0], [1.0, 0.0]) == 0.0

    def test_unit_vectors(self) -> None:
        v = [1.0 / math.sqrt(2), 1.0 / math.sqrt(2)]
        assert _cosine_similarity(v, v) == pytest.approx(1.0)
