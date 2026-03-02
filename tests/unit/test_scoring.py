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


class TestScoreEntityNode:
    """Tests for score_entity_node with real embeddings."""

    def test_entity_node_with_real_embedding(self) -> None:
        """Non-empty embedding should produce relevance_score != 0.5."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": now.isoformat(),
            "mention_count": 3,
            "embedding": [1.0, 0.0, 0.0],
        }
        result = score_entity_node(entity_data, query_embedding=[1.0, 0.0, 0.0], now=now)
        assert result.relevance_score > 0.99
        assert result.relevance_score != 0.5

    def test_entity_node_empty_embedding(self) -> None:
        """Empty embedding should preserve 0.5 default relevance."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": now.isoformat(),
            "mention_count": 1,
            "embedding": [],
        }
        result = score_entity_node(entity_data, query_embedding=[1.0, 0.0, 0.0], now=now)
        assert result.relevance_score == 0.5

    def test_entity_node_orthogonal_embedding(self) -> None:
        """Orthogonal embedding should produce relevance_score of 0.0."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": now.isoformat(),
            "mention_count": 2,
            "embedding": [0.0, 1.0, 0.0],
        }
        result = score_entity_node(entity_data, query_embedding=[1.0, 0.0, 0.0], now=now)
        assert abs(result.relevance_score) < 1e-6

    def test_entity_node_no_query_embedding(self) -> None:
        """No query embedding should give 0.5 relevance regardless of node embedding."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": now.isoformat(),
            "mention_count": 5,
            "embedding": [1.0, 0.0, 0.0],
        }
        result = score_entity_node(entity_data, now=now)
        assert result.relevance_score == 0.5


class TestScoreEntityNodeConfigurable:
    """Tests for score_entity_node with configurable decay parameters."""

    def test_score_entity_node_custom_s_base(self) -> None:
        """A higher s_base should produce slower decay (higher recency for old entities)."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": (now - timedelta(hours=500)).isoformat(),
            "mention_count": 3,
            "embedding": [],
        }
        score_default = score_entity_node(entity_data, now=now)
        score_high_base = score_entity_node(entity_data, now=now, s_base=2000.0)
        assert score_high_base.decay_score > score_default.decay_score

    def test_score_entity_node_custom_weights(self) -> None:
        """Custom weights should change the composite score."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": now.isoformat(),
            "mention_count": 5,
            "embedding": [1.0, 0.0],
        }
        score_default = score_entity_node(entity_data, query_embedding=[1.0, 0.0], now=now)
        score_relevance_only = score_entity_node(
            entity_data,
            query_embedding=[1.0, 0.0],
            now=now,
            w_recency=0.0,
            w_importance=0.0,
            w_relevance=10.0,
            w_user_affinity=0.0,
        )
        # With only relevance weighted and identical embeddings, score ~1.0
        assert score_relevance_only.decay_score > 0.95
        assert score_default.decay_score != score_relevance_only.decay_score

    def test_score_entity_node_defaults_match_current_behavior(self) -> None:
        """Default params produce the same result as old hardcoded values."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": (now - timedelta(hours=100)).isoformat(),
            "mention_count": 4,
            "embedding": [0.5, 0.5],
        }
        # Call with explicit old defaults (s_base=336.0) — should match no-arg call
        score_explicit = score_entity_node(
            entity_data, query_embedding=[0.5, 0.5], now=now, s_base=336.0
        )
        score_implicit = score_entity_node(entity_data, query_embedding=[0.5, 0.5], now=now)
        assert abs(score_explicit.decay_score - score_implicit.decay_score) < 1e-9

    def test_score_node_with_all_custom_params(self) -> None:
        """score_node should accept and apply all custom decay params."""
        now = datetime.now(UTC)
        node_data = {
            "occurred_at": (now - timedelta(hours=50)).isoformat(),
            "access_count": 2,
            "importance_score": 7,
            "embedding": [1.0, 0.0],
            "in_degree": 3,
        }
        result = score_node(
            node_data,
            query_embedding=[1.0, 0.0],
            s_base=500.0,
            s_boost=50.0,
            w_recency=2.0,
            w_importance=0.5,
            w_relevance=3.0,
            w_user_affinity=0.0,
            now=now,
        )
        assert isinstance(result, NodeScores)
        assert result.decay_score > 0

    def test_composite_score_zero_weights(self) -> None:
        """All zero weights should produce decay_score of 0.0."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": now.isoformat(),
            "mention_count": 10,
            "embedding": [1.0, 0.0],
        }
        result = score_entity_node(
            entity_data,
            query_embedding=[1.0, 0.0],
            now=now,
            w_recency=0.0,
            w_importance=0.0,
            w_relevance=0.0,
            w_user_affinity=0.0,
        )
        assert result.decay_score == 0.0

    def test_entity_node_user_affinity_weight(self) -> None:
        """Changing w_user_affinity affects composite when user_affinity > 0."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": now.isoformat(),
            "mention_count": 5,
            "embedding": [],
        }
        # Entity nodes don't carry user_affinity, so the affinity component is 0.
        # Changing w_user_affinity changes total_weight divisor, thus the composite.
        score_low_w = score_entity_node(entity_data, now=now, w_user_affinity=0.0)
        score_high_w = score_entity_node(entity_data, now=now, w_user_affinity=5.0)
        # With user_affinity=0 in entity, higher w_user_affinity dilutes composite
        assert score_low_w.decay_score > score_high_w.decay_score

    def test_decay_settings_propagation(self) -> None:
        """Verify params reach compute functions by testing s_base effect on recency."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": (now - timedelta(hours=300)).isoformat(),
            "mention_count": 2,
            "embedding": [],
        }
        # Very low s_base -> fast decay -> low recency
        score_fast = score_entity_node(entity_data, now=now, s_base=10.0)
        # Very high s_base -> slow decay -> high recency
        score_slow = score_entity_node(entity_data, now=now, s_base=10000.0)
        assert score_slow.decay_score > score_fast.decay_score

    def test_entity_node_high_s_base_slower_decay(self) -> None:
        """Entity with high s_base should retain higher score over time."""
        from context_graph.domain.scoring import score_entity_node

        now = datetime.now(UTC)
        entity_data = {
            "last_seen": (now - timedelta(hours=1000)).isoformat(),
            "mention_count": 1,
            "embedding": [],
        }
        score_normal = score_entity_node(entity_data, now=now, s_base=336.0)
        score_high_base = score_entity_node(entity_data, now=now, s_base=5000.0)
        assert score_high_base.decay_score > score_normal.decay_score


class TestEntityDecaySettings:
    """Verify entity scoring uses separate s_base from events."""

    def test_entity_default_s_base_differs_from_event(self) -> None:
        """Entity s_base (336h) should differ from event s_base (168h)."""
        from context_graph.settings import DecaySettings

        settings = DecaySettings()
        assert settings.entity_s_base == 336.0
        assert settings.s_base == 168.0
        assert settings.entity_s_base > settings.s_base

    def test_entity_scoring_uses_entity_s_base(self) -> None:
        """score_entity_node default s_base should match entity_s_base."""
        import inspect

        from context_graph.domain.scoring import score_entity_node

        sig = inspect.signature(score_entity_node)
        default_s_base = sig.parameters["s_base"].default
        assert default_s_base == 336.0


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
