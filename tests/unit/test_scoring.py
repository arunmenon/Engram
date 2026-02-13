"""Unit tests for context_graph.domain.scoring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context_graph.domain.models import NodeScores
from context_graph.domain.scoring import (
    compute_composite_score,
    compute_importance_score,
    compute_recency_score,
    compute_relevance_score,
    score_node,
)


class TestComputeRecencyScore:
    """Tests for the Ebbinghaus forgetting curve function."""

    def test_recent_event_high_score(self) -> None:
        """An event 1 hour ago should score > 0.95."""
        now = datetime.now(UTC)
        occurred_at = now - timedelta(hours=1)
        score = compute_recency_score(occurred_at, now=now)
        assert score > 0.95

    def test_old_event_low_score(self) -> None:
        """An event 720 hours (30 days) ago should score < 0.05."""
        now = datetime.now(UTC)
        occurred_at = now - timedelta(hours=720)
        score = compute_recency_score(occurred_at, now=now)
        assert score < 0.05

    def test_access_count_boosts_score(self) -> None:
        """More accesses should increase stability and produce a higher score."""
        now = datetime.now(UTC)
        occurred_at = now - timedelta(hours=200)
        score_no_access = compute_recency_score(occurred_at, access_count=0, now=now)
        score_with_access = compute_recency_score(occurred_at, access_count=10, now=now)
        assert score_with_access > score_no_access

    def test_zero_time_returns_one(self) -> None:
        """An event occurring exactly now should return 1.0."""
        now = datetime.now(UTC)
        score = compute_recency_score(now, now=now)
        assert score == 1.0

    def test_zero_stability_returns_zero(self) -> None:
        """Zero stability (s_base=0, no access) should return 0.0."""
        now = datetime.now(UTC)
        occurred_at = now - timedelta(hours=1)
        score = compute_recency_score(occurred_at, s_base=0.0, s_boost=0.0, now=now)
        assert score == 0.0

    def test_custom_stability_params(self) -> None:
        """Custom s_base and s_boost affect the decay rate."""
        now = datetime.now(UTC)
        occurred_at = now - timedelta(hours=100)
        # With high stability, score should be relatively high
        score = compute_recency_score(occurred_at, s_base=1000.0, now=now)
        assert score > 0.9

    def test_future_event_clamps_to_one(self) -> None:
        """A future occurred_at should produce max(0, negative t) = 0 -> score 1.0."""
        now = datetime.now(UTC)
        occurred_at = now + timedelta(hours=1)
        score = compute_recency_score(occurred_at, now=now)
        assert score == 1.0


class TestComputeImportanceScore:
    """Tests for importance scoring."""

    def test_default_no_hint(self) -> None:
        """No importance hint defaults to ~0.5 base."""
        score = compute_importance_score()
        assert 0.45 <= score <= 0.55

    def test_high_hint(self) -> None:
        """importance_hint=10 should produce 1.0."""
        score = compute_importance_score(importance_hint=10)
        assert score == 1.0

    def test_low_hint(self) -> None:
        """importance_hint=1 should produce ~0.1 base."""
        score = compute_importance_score(importance_hint=1)
        assert 0.05 <= score <= 0.2

    def test_access_count_boost(self) -> None:
        """High access count adds a boost."""
        base_score = compute_importance_score(importance_hint=5)
        boosted_score = compute_importance_score(importance_hint=5, access_count=100)
        assert boosted_score > base_score

    def test_in_degree_boost(self) -> None:
        """High in-degree adds a centrality boost."""
        base_score = compute_importance_score(importance_hint=5)
        boosted_score = compute_importance_score(importance_hint=5, in_degree=50)
        assert boosted_score > base_score

    def test_capped_at_one(self) -> None:
        """Score never exceeds 1.0 even with maximum boosts."""
        score = compute_importance_score(importance_hint=10, access_count=10000, in_degree=10000)
        assert score == 1.0


class TestComputeRelevanceScore:
    """Tests for cosine similarity."""

    def test_identical_vectors(self) -> None:
        """Identical vectors should have similarity 1.0."""
        score = compute_relevance_score([1.0, 0.0], [1.0, 0.0])
        assert abs(score - 1.0) < 1e-6

    def test_orthogonal_vectors(self) -> None:
        """Orthogonal vectors should have similarity 0.0."""
        score = compute_relevance_score([1.0, 0.0], [0.0, 1.0])
        assert abs(score - 0.0) < 1e-6

    def test_empty_query(self) -> None:
        """Empty query embedding should return 0.5."""
        score = compute_relevance_score([], [1.0, 0.0])
        assert score == 0.5

    def test_empty_node(self) -> None:
        """Empty node embedding should return 0.5."""
        score = compute_relevance_score([1.0, 0.0], [])
        assert score == 0.5

    def test_dimension_mismatch(self) -> None:
        """Mismatched dimensions should return 0.5."""
        score = compute_relevance_score([1.0, 0.0], [1.0, 0.0, 0.0])
        assert score == 0.5

    def test_zero_vectors(self) -> None:
        """Zero vectors should return 0.5."""
        score = compute_relevance_score([0.0, 0.0], [0.0, 0.0])
        assert score == 0.5

    def test_similar_vectors(self) -> None:
        """Slightly different but similar vectors should score high."""
        score = compute_relevance_score([1.0, 0.1], [1.0, 0.0])
        assert score > 0.99

    def test_opposite_vectors_clamped(self) -> None:
        """Opposite vectors yield negative cosine, clamped to 0.0."""
        score = compute_relevance_score([1.0, 0.0], [-1.0, 0.0])
        assert score == 0.0


class TestComputeCompositeScore:
    """Tests for the weighted composite score."""

    def test_equal_weights(self) -> None:
        """Equal weights, equal inputs should produce that value."""
        score = compute_composite_score(0.5, 0.5, 0.5, user_affinity=0.5)
        assert abs(score - 0.5) < 1e-6

    def test_zero_total_weight(self) -> None:
        """Zero total weight returns 0.0."""
        score = compute_composite_score(
            0.8,
            0.8,
            0.8,
            w_recency=0.0,
            w_importance=0.0,
            w_relevance=0.0,
            w_user_affinity=0.0,
        )
        assert score == 0.0

    def test_recency_dominates(self) -> None:
        """High recency weight should make recency dominant."""
        score = compute_composite_score(
            1.0,
            0.0,
            0.0,
            w_recency=10.0,
            w_importance=0.0,
            w_relevance=0.0,
            w_user_affinity=0.0,
        )
        assert abs(score - 1.0) < 1e-6

    def test_user_affinity_contribution(self) -> None:
        """User affinity should contribute to the composite score."""
        score_without = compute_composite_score(0.5, 0.5, 0.5, user_affinity=0.0)
        score_with = compute_composite_score(0.5, 0.5, 0.5, user_affinity=1.0)
        assert score_with > score_without


class TestScoreNode:
    """Tests for the score_node convenience function."""

    def test_returns_node_scores_model(self) -> None:
        """score_node should return a NodeScores instance."""
        now = datetime.now(UTC)
        node_data = {
            "occurred_at": now.isoformat(),
            "access_count": 0,
            "importance_score": 7,
            "embedding": [],
            "in_degree": 0,
        }
        result = score_node(node_data, now=now)
        assert isinstance(result, NodeScores)

    def test_importance_hint_preserved(self) -> None:
        """importance_score from node_data should appear in output."""
        now = datetime.now(UTC)
        node_data = {"occurred_at": now, "importance_score": 8}
        result = score_node(node_data, now=now)
        assert result.importance_score == 8

    def test_no_importance_hint_derives_score(self) -> None:
        """Without importance_score in node_data, a derived int is computed."""
        now = datetime.now(UTC)
        node_data = {"occurred_at": now}
        result = score_node(node_data, now=now)
        assert 1 <= result.importance_score <= 10

    def test_with_query_embedding(self) -> None:
        """Providing a query embedding should produce nonzero relevance."""
        now = datetime.now(UTC)
        node_data = {
            "occurred_at": now,
            "embedding": [1.0, 0.0, 0.0],
        }
        result = score_node(node_data, query_embedding=[1.0, 0.0, 0.0], now=now)
        assert result.relevance_score > 0.99

    def test_datetime_object_in_node_data(self) -> None:
        """occurred_at can be a datetime object, not just a string."""
        now = datetime.now(UTC)
        node_data = {"occurred_at": now}
        result = score_node(node_data, now=now)
        assert result.decay_score > 0

    def test_missing_occurred_at_fallback(self) -> None:
        """Missing occurred_at should fall back gracefully."""
        now = datetime.now(UTC)
        result = score_node({}, now=now)
        assert isinstance(result, NodeScores)

    def test_last_accessed_at_boosts_recency(self) -> None:
        """last_accessed_at in node_data should boost recency when more recent."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=200)
        last_accessed = now - timedelta(hours=5)
        node_with = {
            "occurred_at": occurred.isoformat(),
            "last_accessed_at": last_accessed.isoformat(),
        }
        node_without = {"occurred_at": occurred.isoformat()}
        score_with = score_node(node_with, now=now)
        score_without = score_node(node_without, now=now)
        assert score_with.decay_score > score_without.decay_score


class TestComputeRecencyWithLastAccessed:
    def test_last_accessed_after_occurred(self):
        """last_accessed_at after occurred_at should use last_accessed_at."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=100)
        last_accessed = now - timedelta(hours=10)
        score = compute_recency_score(occurred, last_accessed_at=last_accessed, now=now)
        score_without = compute_recency_score(occurred, now=now)
        assert score > score_without

    def test_last_accessed_before_occurred(self):
        """last_accessed_at before occurred_at should use occurred_at (max)."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=10)
        last_accessed = now - timedelta(hours=100)
        score = compute_recency_score(occurred, last_accessed_at=last_accessed, now=now)
        score_without = compute_recency_score(occurred, now=now)
        assert abs(score - score_without) < 1e-6

    def test_last_accessed_none_unchanged(self):
        """None last_accessed_at should behave like original function."""
        now = datetime.now(UTC)
        occurred = now - timedelta(hours=50)
        score = compute_recency_score(occurred, last_accessed_at=None, now=now)
        score_without = compute_recency_score(occurred, now=now)
        assert abs(score - score_without) < 1e-6


class TestComputeRelevanceEmptyFallback:
    def test_empty_embeddings_returns_half(self):
        """Empty query embedding should return 0.5 (not 0.0)."""
        assert compute_relevance_score([], [1.0, 0.0]) == 0.5

    def test_dimension_mismatch_returns_half(self):
        """Mismatched dimensions should return 0.5."""
        assert compute_relevance_score([1.0], [1.0, 0.0]) == 0.5

    def test_zero_vectors_returns_half(self):
        """Zero norm vectors should return 0.5."""
        assert compute_relevance_score([0.0, 0.0], [0.0, 0.0]) == 0.5


class TestComputeUserAffinity:
    def test_all_zeros(self):
        from context_graph.domain.scoring import compute_user_affinity

        assert compute_user_affinity(0.0, 0.0, 0.0) == 0.0

    def test_all_ones(self):
        from context_graph.domain.scoring import compute_user_affinity

        assert compute_user_affinity(1.0, 1.0, 1.0) == 1.0

    def test_weighted_average(self):
        from context_graph.domain.scoring import compute_user_affinity

        score = compute_user_affinity(1.0, 0.0, 0.0)
        assert abs(score - 0.4) < 1e-6
