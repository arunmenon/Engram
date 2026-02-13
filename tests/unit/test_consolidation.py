"""Unit tests for domain/consolidation.py — re-consolidation logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context_graph.domain.consolidation import (
    build_summary_prompt,
    create_summary_from_events,
    group_events_into_episodes,
    select_events_for_pruning,
    should_reconsolidate,
)
from context_graph.domain.models import RetentionTier
from context_graph.settings import RetentionSettings

# ---------------------------------------------------------------------------
# should_reconsolidate
# ---------------------------------------------------------------------------


class TestShouldReconsolidate:
    def test_below_threshold(self):
        assert should_reconsolidate(100.0, threshold=150.0) is False

    def test_at_threshold(self):
        assert should_reconsolidate(150.0, threshold=150.0) is True

    def test_above_threshold(self):
        assert should_reconsolidate(200.0, threshold=150.0) is True

    def test_zero_importance(self):
        assert should_reconsolidate(0.0) is False

    def test_custom_threshold(self):
        assert should_reconsolidate(50.0, threshold=50.0) is True
        assert should_reconsolidate(49.0, threshold=50.0) is False


# ---------------------------------------------------------------------------
# group_events_into_episodes
# ---------------------------------------------------------------------------


class TestGroupEventsIntoEpisodes:
    def _make_event(self, minutes_offset: int, event_id: str = "") -> dict:
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        return {
            "event_id": event_id or f"evt-{minutes_offset}",
            "occurred_at": (base + timedelta(minutes=minutes_offset)).isoformat(),
            "event_type": "tool.execute",
        }

    def test_empty_list(self):
        assert group_events_into_episodes([]) == []

    def test_single_event(self):
        events = [self._make_event(0)]
        episodes = group_events_into_episodes(events)
        assert len(episodes) == 1
        assert len(episodes[0]) == 1

    def test_all_within_gap(self):
        events = [self._make_event(i * 5) for i in range(6)]  # 0, 5, 10, 15, 20, 25
        episodes = group_events_into_episodes(events, gap_minutes=30)
        assert len(episodes) == 1
        assert len(episodes[0]) == 6

    def test_two_episodes(self):
        events = [
            self._make_event(0),
            self._make_event(10),
            self._make_event(20),
            self._make_event(60),  # 40-min gap from previous
            self._make_event(70),
        ]
        episodes = group_events_into_episodes(events, gap_minutes=30)
        assert len(episodes) == 2
        assert len(episodes[0]) == 3
        assert len(episodes[1]) == 2

    def test_each_event_is_episode(self):
        events = [self._make_event(i * 60) for i in range(3)]  # 60-min gaps
        episodes = group_events_into_episodes(events, gap_minutes=30)
        assert len(episodes) == 3

    def test_unsorted_input(self):
        events = [
            self._make_event(60),
            self._make_event(0),
            self._make_event(30),
        ]
        episodes = group_events_into_episodes(events, gap_minutes=35)
        assert len(episodes) == 1  # 0, 30, 60 — all within 35-min gap

    def test_datetime_objects(self):
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        events = [
            {"event_id": "a", "occurred_at": base, "event_type": "tool.execute"},
            {
                "event_id": "b",
                "occurred_at": base + timedelta(hours=2),
                "event_type": "tool.execute",
            },
        ]
        episodes = group_events_into_episodes(events, gap_minutes=30)
        assert len(episodes) == 2

    def test_custom_gap(self):
        events = [self._make_event(0), self._make_event(10)]
        assert len(group_events_into_episodes(events, gap_minutes=5)) == 2
        assert len(group_events_into_episodes(events, gap_minutes=15)) == 1


# ---------------------------------------------------------------------------
# create_summary_from_events
# ---------------------------------------------------------------------------


class TestCreateSummaryFromEvents:
    def _make_events(self, n: int) -> list[dict]:
        base = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        return [
            {
                "event_id": f"evt-{i}",
                "occurred_at": (base + timedelta(minutes=i)).isoformat(),
                "event_type": "tool.execute" if i % 2 == 0 else "agent.invoke",
            }
            for i in range(n)
        ]

    def test_basic_summary(self):
        events = self._make_events(5)
        summary = create_summary_from_events(events, scope="episode", scope_id="s1-ep0")
        assert summary.scope == "episode"
        assert summary.scope_id == "s1-ep0"
        assert summary.event_count == 5
        assert summary.summary_id.startswith("summary-s1-ep0-")
        assert "5 events" in summary.content
        assert len(summary.time_range) == 2

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            create_summary_from_events([], scope="episode", scope_id="s1")

    def test_single_event(self):
        events = self._make_events(1)
        summary = create_summary_from_events(events, scope="session", scope_id="s1")
        assert summary.event_count == 1
        assert summary.time_range[0] == summary.time_range[1]

    def test_deterministic_id(self):
        events = self._make_events(3)
        s1 = create_summary_from_events(events, scope="ep", scope_id="x")
        s2 = create_summary_from_events(events, scope="ep", scope_id="x")
        assert s1.summary_id == s2.summary_id

    def test_different_events_different_id(self):
        events_a = self._make_events(3)
        events_b = [
            {
                "event_id": f"other-{i}",
                "occurred_at": datetime(2025, 6, 1, tzinfo=UTC).isoformat(),
                "event_type": "llm.chat",
            }
            for i in range(3)
        ]
        s_a = create_summary_from_events(events_a, scope="ep", scope_id="x")
        s_b = create_summary_from_events(events_b, scope="ep", scope_id="x")
        assert s_a.summary_id != s_b.summary_id

    def test_content_includes_event_types(self):
        events = self._make_events(4)
        summary = create_summary_from_events(events, scope="ep", scope_id="x")
        assert "agent.invoke" in summary.content
        assert "tool.execute" in summary.content


# ---------------------------------------------------------------------------
# build_summary_prompt
# ---------------------------------------------------------------------------


class TestBuildSummaryPrompt:
    def test_prompt_structure(self):
        events = [
            {
                "event_id": "e1",
                "occurred_at": "2025-01-01T12:00:00+00:00",
                "event_type": "tool.execute",
                "tool_name": "search",
                "status": "completed",
            },
            {
                "event_id": "e2",
                "occurred_at": "2025-01-01T12:05:00+00:00",
                "event_type": "agent.invoke",
            },
        ]
        prompt = build_summary_prompt(events)
        assert "Summarize" in prompt
        assert "tool.execute" in prompt
        assert "[search]" in prompt
        assert "(completed)" in prompt
        assert "agent.invoke" in prompt
        assert "Episode summary:" in prompt

    def test_empty_events(self):
        prompt = build_summary_prompt([])
        assert "Events:" in prompt

    def test_sorted_by_time(self):
        events = [
            {
                "event_id": "e2",
                "occurred_at": "2025-01-01T12:10:00+00:00",
                "event_type": "agent.invoke",
            },
            {
                "event_id": "e1",
                "occurred_at": "2025-01-01T12:00:00+00:00",
                "event_type": "tool.execute",
            },
        ]
        prompt = build_summary_prompt(events)
        lines = prompt.split("\n")
        event_lines = [line for line in lines if line.startswith("- ")]
        assert "tool.execute" in event_lines[0]
        assert "agent.invoke" in event_lines[1]


# ---------------------------------------------------------------------------
# select_events_for_pruning
# ---------------------------------------------------------------------------


class TestSelectEventsForPruning:
    def _make_retention(self) -> RetentionSettings:
        return RetentionSettings(
            hot_hours=24,
            warm_hours=168,
            cold_hours=720,
            warm_min_similarity_score=0.7,
            cold_min_importance=5,
            cold_min_access_count=3,
        )

    def test_hot_tier_no_pruning(self):
        events = [
            {"event_id": "e1", "importance_score": 1, "access_count": 0},
        ]
        result = select_events_for_pruning(events, RetentionTier.HOT, self._make_retention())
        assert result == []

    def test_warm_tier_low_importance_no_access(self):
        events = [
            {"event_id": "e1", "importance_score": 2, "access_count": 0},
            {"event_id": "e2", "importance_score": 7, "access_count": 0},
        ]
        result = select_events_for_pruning(events, RetentionTier.WARM, self._make_retention())
        assert "e1" in result
        assert "e2" not in result

    def test_cold_tier_pruning(self):
        events = [
            {"event_id": "e1", "importance_score": 3, "access_count": 1},
            {"event_id": "e2", "importance_score": 8, "access_count": 5},
            {"event_id": "e3", "importance_score": 4, "access_count": 4},
        ]
        result = select_events_for_pruning(events, RetentionTier.COLD, self._make_retention())
        assert "e1" in result  # low importance AND low access
        assert "e2" not in result  # high importance AND high access
        assert "e3" not in result  # low importance but access >= 3 saves it

    def test_archive_tier_all_pruned(self):
        events = [
            {"event_id": "e1", "importance_score": 10, "access_count": 100},
            {"event_id": "e2", "importance_score": 1, "access_count": 0},
        ]
        result = select_events_for_pruning(events, RetentionTier.ARCHIVE, self._make_retention())
        assert len(result) == 2

    def test_missing_event_id_skipped(self):
        events = [{"importance_score": 1, "access_count": 0}]
        result = select_events_for_pruning(events, RetentionTier.COLD, self._make_retention())
        assert result == []

    def test_none_importance_treated_as_zero(self):
        events = [
            {"event_id": "e1", "importance_score": None, "access_count": 0},
        ]
        result = select_events_for_pruning(events, RetentionTier.COLD, self._make_retention())
        assert "e1" in result


# ---------------------------------------------------------------------------
# should_reconsolidate with importance sum (regression tests)
# ---------------------------------------------------------------------------


class TestShouldReconsolidateImportanceSum:
    def test_importance_sum_below_threshold(self):
        assert should_reconsolidate(100.0, threshold=150.0) is False

    def test_importance_sum_at_threshold(self):
        assert should_reconsolidate(150.0, threshold=150.0) is True

    def test_importance_sum_above_threshold(self):
        assert should_reconsolidate(200.5, threshold=150.0) is True

    def test_float_threshold(self):
        assert should_reconsolidate(149.9, threshold=150.0) is False
