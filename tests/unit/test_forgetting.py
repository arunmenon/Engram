"""Unit tests for domain/forgetting.py — retention tier enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context_graph.domain.forgetting import (
    PruningActions,
    classify_retention_tier,
    get_pruning_actions,
    should_prune_cold,
    should_prune_warm,
)
from context_graph.domain.models import RetentionTier

# ---------------------------------------------------------------------------
# classify_retention_tier
# ---------------------------------------------------------------------------


class TestClassifyRetentionTier:
    def _now(self) -> datetime:
        return datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)

    def test_hot_tier(self):
        now = self._now()
        occurred = now - timedelta(hours=12)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.HOT

    def test_hot_boundary(self):
        now = self._now()
        occurred = now - timedelta(hours=23, minutes=59)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.HOT

    def test_warm_tier(self):
        now = self._now()
        occurred = now - timedelta(hours=48)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.WARM

    def test_warm_boundary_start(self):
        now = self._now()
        occurred = now - timedelta(hours=24)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.WARM

    def test_cold_tier(self):
        now = self._now()
        occurred = now - timedelta(hours=200)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.COLD

    def test_cold_boundary_start(self):
        now = self._now()
        occurred = now - timedelta(hours=168)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.COLD

    def test_archive_tier(self):
        now = self._now()
        occurred = now - timedelta(hours=800)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.ARCHIVE

    def test_archive_boundary(self):
        now = self._now()
        occurred = now - timedelta(hours=720)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.ARCHIVE

    def test_custom_boundaries(self):
        now = self._now()
        occurred = now - timedelta(hours=5)
        tier = classify_retention_tier(occurred, now=now, hot_hours=2, warm_hours=10)
        assert tier == RetentionTier.WARM

    def test_future_event_is_hot(self):
        now = self._now()
        occurred = now + timedelta(hours=1)
        assert classify_retention_tier(occurred, now=now) == RetentionTier.HOT


# ---------------------------------------------------------------------------
# should_prune_warm
# ---------------------------------------------------------------------------


class TestShouldPruneWarm:
    def test_below_threshold(self):
        assert should_prune_warm({"similarity_score": 0.5}, warm_min_similarity=0.7) is True

    def test_above_threshold(self):
        assert should_prune_warm({"similarity_score": 0.9}, warm_min_similarity=0.7) is False

    def test_at_threshold(self):
        assert should_prune_warm({"similarity_score": 0.7}, warm_min_similarity=0.7) is False

    def test_missing_score_defaults_high(self):
        assert should_prune_warm({}, warm_min_similarity=0.7) is False

    def test_zero_score(self):
        assert should_prune_warm({"similarity_score": 0.0}, warm_min_similarity=0.1) is True


# ---------------------------------------------------------------------------
# should_prune_cold
# ---------------------------------------------------------------------------


class TestShouldPruneCold:
    def test_both_below(self):
        event = {"importance_score": 2, "access_count": 1}
        assert should_prune_cold(event, cold_min_importance=5, cold_min_access_count=3) is True

    def test_importance_ok_access_low(self):
        event = {"importance_score": 7, "access_count": 1}
        assert should_prune_cold(event, cold_min_importance=5, cold_min_access_count=3) is True

    def test_importance_low_access_ok(self):
        event = {"importance_score": 2, "access_count": 5}
        assert should_prune_cold(event, cold_min_importance=5, cold_min_access_count=3) is True

    def test_both_ok(self):
        event = {"importance_score": 7, "access_count": 5}
        assert should_prune_cold(event, cold_min_importance=5, cold_min_access_count=3) is False

    def test_missing_importance_is_zero(self):
        event = {"access_count": 10}
        assert should_prune_cold(event, cold_min_importance=5, cold_min_access_count=3) is True

    def test_none_importance(self):
        event = {"importance_score": None, "access_count": 10}
        assert should_prune_cold(event, cold_min_importance=5, cold_min_access_count=3) is True

    def test_missing_access_count_is_zero(self):
        event = {"importance_score": 8}
        assert should_prune_cold(event, cold_min_importance=5, cold_min_access_count=3) is True

    def test_at_exact_thresholds(self):
        event = {"importance_score": 5, "access_count": 3}
        assert should_prune_cold(event, cold_min_importance=5, cold_min_access_count=3) is False


# ---------------------------------------------------------------------------
# get_pruning_actions
# ---------------------------------------------------------------------------


class TestGetPruningActions:
    def _now(self) -> datetime:
        return datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)

    def _make_event(
        self,
        event_id: str,
        hours_ago: int,
        importance: int = 5,
        access_count: int = 0,
        similarity_score: float = 0.9,
    ) -> dict:
        now = self._now()
        occurred = now - timedelta(hours=hours_ago)
        return {
            "event_id": event_id,
            "occurred_at": occurred.isoformat(),
            "importance_score": importance,
            "access_count": access_count,
            "similarity_score": similarity_score,
        }

    def test_hot_events_untouched(self):
        events = [self._make_event("e1", hours_ago=6)]
        actions = get_pruning_actions(events, now=self._now())
        assert actions.delete_edges == []
        assert actions.delete_nodes == []
        assert actions.archive_event_ids == []

    def test_warm_low_similarity_pruned(self):
        events = [self._make_event("e1", hours_ago=48, similarity_score=0.3)]
        actions = get_pruning_actions(events, now=self._now())
        assert "e1" in actions.delete_edges

    def test_warm_high_similarity_kept(self):
        events = [self._make_event("e1", hours_ago=48, similarity_score=0.9)]
        actions = get_pruning_actions(events, now=self._now())
        assert actions.delete_edges == []

    def test_cold_low_quality_pruned(self):
        events = [
            self._make_event("e1", hours_ago=200, importance=2, access_count=1),
        ]
        actions = get_pruning_actions(events, now=self._now())
        assert "e1" in actions.delete_nodes

    def test_cold_high_quality_kept(self):
        events = [
            self._make_event("e1", hours_ago=200, importance=8, access_count=5),
        ]
        actions = get_pruning_actions(events, now=self._now())
        assert actions.delete_nodes == []

    def test_archive_always_archived(self):
        events = [
            self._make_event("e1", hours_ago=800, importance=10, access_count=100),
        ]
        actions = get_pruning_actions(events, now=self._now())
        assert "e1" in actions.archive_event_ids

    def test_mixed_tiers(self):
        events = [
            self._make_event("hot", hours_ago=6),
            self._make_event("warm-prune", hours_ago=48, similarity_score=0.3),
            self._make_event("warm-keep", hours_ago=48, similarity_score=0.9),
            self._make_event("cold-prune", hours_ago=200, importance=2, access_count=1),
            self._make_event("cold-keep", hours_ago=200, importance=8, access_count=5),
            self._make_event("archive", hours_ago=800),
        ]
        actions = get_pruning_actions(events, now=self._now())
        assert "warm-prune" in actions.delete_edges
        assert "warm-keep" not in actions.delete_edges
        assert "cold-prune" in actions.delete_nodes
        assert "cold-keep" not in actions.delete_nodes
        assert "archive" in actions.archive_event_ids
        assert "hot" not in actions.delete_edges
        assert "hot" not in actions.delete_nodes
        assert "hot" not in actions.archive_event_ids

    def test_empty_events(self):
        actions = get_pruning_actions([], now=self._now())
        assert actions == PruningActions()

    def test_missing_occurred_at_skipped(self):
        events = [{"event_id": "e1"}]
        actions = get_pruning_actions(events, now=self._now())
        assert actions == PruningActions()

    def test_missing_event_id_skipped(self):
        now = self._now()
        events = [{"occurred_at": (now - timedelta(hours=800)).isoformat()}]
        actions = get_pruning_actions(events, now=now)
        assert actions.archive_event_ids == []

    def test_datetime_objects_supported(self):
        now = self._now()
        events = [
            {
                "event_id": "e1",
                "occurred_at": now - timedelta(hours=800),
                "importance_score": 1,
                "access_count": 0,
            },
        ]
        actions = get_pruning_actions(events, now=now)
        assert "e1" in actions.archive_event_ids
