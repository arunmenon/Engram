"""Unit tests for contradiction detection and resolution.

Tests for both preference and belief contradiction detection,
resolution (supersession), and the find_contradictions aggregator.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context_graph.domain.contradiction import (
    detect_belief_contradiction,
    detect_preference_contradictions,
    find_belief_contradictions,
    resolve_belief_contradiction,
    resolve_contradiction,
)

# ---------------------------------------------------------------------------
# Preference contradiction detection
# ---------------------------------------------------------------------------


class TestDetectPreferenceContradictions:
    """Tests for detect_preference_contradictions."""

    def test_detects_same_key_opposite_polarity(self) -> None:
        prefs = [
            {"category": "tool", "key": "vim", "polarity": "positive", "preference_id": "p1"},
            {"category": "tool", "key": "vim", "polarity": "negative", "preference_id": "p2"},
        ]
        conflicts = detect_preference_contradictions(prefs)
        assert len(conflicts) == 1
        assert conflicts[0][0]["preference_id"] == "p1"
        assert conflicts[0][1]["preference_id"] == "p2"

    def test_no_conflict_same_polarity(self) -> None:
        prefs = [
            {"category": "tool", "key": "vim", "polarity": "positive", "preference_id": "p1"},
            {"category": "tool", "key": "vim", "polarity": "positive", "preference_id": "p2"},
        ]
        conflicts = detect_preference_contradictions(prefs)
        assert len(conflicts) == 0

    def test_no_conflict_different_keys(self) -> None:
        prefs = [
            {"category": "tool", "key": "vim", "polarity": "positive"},
            {"category": "tool", "key": "emacs", "polarity": "negative"},
        ]
        conflicts = detect_preference_contradictions(prefs)
        assert len(conflicts) == 0

    def test_empty_list(self) -> None:
        assert detect_preference_contradictions([]) == []


class TestResolveContradiction:
    """Tests for resolve_contradiction (preference)."""

    def test_newer_wins(self) -> None:
        older = {
            "preference_id": "p1",
            "polarity": "positive",
            "last_confirmed_at": "2025-01-01T00:00:00+00:00",
        }
        newer = {
            "preference_id": "p2",
            "polarity": "negative",
            "last_confirmed_at": "2025-06-01T00:00:00+00:00",
        }
        winner, loser = resolve_contradiction(older, newer)
        assert winner["preference_id"] == "p2"
        assert loser["superseded_by"] == "p2"

    def test_new_pref_without_timestamp_wins_over_existing(self) -> None:
        """New preferences from extraction lack timestamps and should win."""
        existing = {
            "preference_id": "p1",
            "polarity": "positive",
            "last_confirmed_at": "2025-01-01T00:00:00+00:00",
        }
        new_from_extraction = {
            "preference_id": "p2",
            "polarity": "negative",
            # No last_confirmed_at or created_at — fresh from LLM extraction
        }
        winner, loser = resolve_contradiction(existing, new_from_extraction)
        assert winner["preference_id"] == "p2"
        assert loser["superseded_by"] == "p2"

    def test_both_missing_timestamps_b_wins(self) -> None:
        """When both lack timestamps, second arg (b) wins as default."""
        pref_a = {"preference_id": "p1", "polarity": "positive"}
        pref_b = {"preference_id": "p2", "polarity": "negative"}
        winner, loser = resolve_contradiction(pref_a, pref_b)
        assert winner["preference_id"] == "p2"

    def test_datetime_objects_handled(self) -> None:
        """resolve_contradiction handles datetime objects (not just strings)."""
        now = datetime.now(UTC)
        older = {
            "preference_id": "p1",
            "last_confirmed_at": now - timedelta(days=7),
        }
        newer = {
            "preference_id": "p2",
            "last_confirmed_at": now,
        }
        winner, loser = resolve_contradiction(older, newer)
        assert winner["preference_id"] == "p2"


# ---------------------------------------------------------------------------
# Belief contradiction detection
# ---------------------------------------------------------------------------


class TestDetectBeliefContradiction:
    """Tests for detect_belief_contradiction."""

    def test_same_category_similar_text_is_contradiction(self) -> None:
        belief_a = {
            "belief_id": "b1",
            "belief_text": "The user prefers dark mode for all applications",
            "category": "user_model",
        }
        belief_b = {
            "belief_id": "b2",
            "belief_text": "The user prefers light mode for all applications",
            "category": "user_model",
        }
        assert detect_belief_contradiction(belief_a, belief_b) is True

    def test_different_category_not_contradiction(self) -> None:
        belief_a = {
            "belief_id": "b1",
            "belief_text": "The user prefers dark mode",
            "category": "user_model",
        }
        belief_b = {
            "belief_id": "b2",
            "belief_text": "The user prefers dark mode",
            "category": "world_model",
        }
        assert detect_belief_contradiction(belief_a, belief_b) is False

    def test_identical_text_not_contradiction(self) -> None:
        """Nearly identical beliefs are duplicates, not contradictions."""
        belief_a = {
            "belief_id": "b1",
            "belief_text": "Python is the best language",
            "category": "capability",
        }
        belief_b = {
            "belief_id": "b2",
            "belief_text": "Python is the best language",
            "category": "capability",
        }
        assert detect_belief_contradiction(belief_a, belief_b) is False

    def test_very_different_text_not_contradiction(self) -> None:
        """Completely different topics are not contradictions."""
        belief_a = {
            "belief_id": "b1",
            "belief_text": "The sky is blue during the day",
            "category": "world_model",
        }
        belief_b = {
            "belief_id": "b2",
            "belief_text": "Python uses indentation for blocks",
            "category": "world_model",
        }
        assert detect_belief_contradiction(belief_a, belief_b) is False

    def test_empty_text_not_contradiction(self) -> None:
        belief_a = {"belief_id": "b1", "belief_text": "", "category": "user_model"}
        belief_b = {"belief_id": "b2", "belief_text": "something", "category": "user_model"}
        assert detect_belief_contradiction(belief_a, belief_b) is False

    def test_custom_threshold(self) -> None:
        belief_a = {
            "belief_id": "b1",
            "belief_text": "The user strongly prefers using dark mode themes",
            "category": "user_model",
        }
        belief_b = {
            "belief_id": "b2",
            "belief_text": "The user strongly prefers using light mode themes",
            "category": "user_model",
        }
        # With very high threshold, they should not be detected
        assert (
            detect_belief_contradiction(belief_a, belief_b, text_similarity_threshold=0.99) is False
        )
        # With low threshold, they should be detected
        assert (
            detect_belief_contradiction(belief_a, belief_b, text_similarity_threshold=0.3) is True
        )


class TestResolveBeliefContradiction:
    """Tests for resolve_belief_contradiction."""

    def test_higher_confidence_wins(self) -> None:
        now = datetime.now(UTC)
        belief_a = {
            "belief_id": "b1",
            "confidence": 0.9,
            "last_confirmed_at": now,
            "confirmation_count": 1,
        }
        belief_b = {
            "belief_id": "b2",
            "confidence": 0.5,
            "last_confirmed_at": now,
            "confirmation_count": 1,
        }
        winner, loser = resolve_belief_contradiction(belief_a, belief_b)
        assert winner["belief_id"] == "b1"
        assert loser["superseded_by"] == "b1"

    def test_more_recent_wins_on_confidence_tie(self) -> None:
        now = datetime.now(UTC)
        old = now - timedelta(days=7)
        belief_a = {
            "belief_id": "b1",
            "confidence": 0.8,
            "last_confirmed_at": old,
            "confirmation_count": 1,
        }
        belief_b = {
            "belief_id": "b2",
            "confidence": 0.8,
            "last_confirmed_at": now,
            "confirmation_count": 1,
        }
        winner, loser = resolve_belief_contradiction(belief_a, belief_b)
        assert winner["belief_id"] == "b2"
        assert loser["superseded_by"] == "b2"

    def test_higher_confirmation_count_wins_on_full_tie(self) -> None:
        now = datetime.now(UTC)
        belief_a = {
            "belief_id": "b1",
            "confidence": 0.8,
            "last_confirmed_at": now,
            "confirmation_count": 5,
        }
        belief_b = {
            "belief_id": "b2",
            "confidence": 0.8,
            "last_confirmed_at": now,
            "confirmation_count": 2,
        }
        winner, loser = resolve_belief_contradiction(belief_a, belief_b)
        assert winner["belief_id"] == "b1"
        assert loser["superseded_by"] == "b1"

    def test_default_b_wins_on_total_tie(self) -> None:
        now = datetime.now(UTC)
        belief_a = {
            "belief_id": "b1",
            "confidence": 0.8,
            "last_confirmed_at": now,
            "confirmation_count": 1,
        }
        belief_b = {
            "belief_id": "b2",
            "confidence": 0.8,
            "last_confirmed_at": now,
            "confirmation_count": 1,
        }
        winner, loser = resolve_belief_contradiction(belief_a, belief_b)
        assert winner["belief_id"] == "b2"

    def test_sets_superseded_by_on_loser(self) -> None:
        belief_a = {
            "belief_id": "b-old",
            "confidence": 0.3,
            "last_confirmed_at": "2025-01-01T00:00:00+00:00",
            "confirmation_count": 1,
        }
        belief_b = {
            "belief_id": "b-new",
            "confidence": 0.9,
            "last_confirmed_at": "2025-06-01T00:00:00+00:00",
            "confirmation_count": 3,
        }
        winner, loser = resolve_belief_contradiction(belief_a, belief_b)
        assert loser["superseded_by"] == "b-new"


class TestFindBeliefContradictions:
    """Tests for find_belief_contradictions."""

    def test_finds_contradictions_among_active_beliefs(self) -> None:
        now = datetime.now(UTC)
        beliefs = [
            {
                "belief_id": "b1",
                "belief_text": "User prefers dark mode in all editors",
                "category": "user_model",
                "confidence": 0.7,
                "last_confirmed_at": now - timedelta(days=7),
                "confirmation_count": 1,
            },
            {
                "belief_id": "b2",
                "belief_text": "User prefers light mode in all editors",
                "category": "user_model",
                "confidence": 0.9,
                "last_confirmed_at": now,
                "confirmation_count": 2,
            },
        ]
        result = find_belief_contradictions(beliefs)
        assert len(result) == 1
        assert result[0]["winner_id"] == "b2"
        assert result[0]["loser_id"] == "b1"

    def test_skips_superseded_beliefs(self) -> None:
        now = datetime.now(UTC)
        beliefs = [
            {
                "belief_id": "b1",
                "belief_text": "User prefers dark mode in all editors",
                "category": "user_model",
                "confidence": 0.7,
                "last_confirmed_at": now,
                "confirmation_count": 1,
                "superseded_by": "b2",
            },
            {
                "belief_id": "b2",
                "belief_text": "User prefers light mode in all editors",
                "category": "user_model",
                "confidence": 0.9,
                "last_confirmed_at": now,
                "confirmation_count": 2,
            },
        ]
        result = find_belief_contradictions(beliefs)
        assert len(result) == 0

    def test_empty_list(self) -> None:
        assert find_belief_contradictions([]) == []

    def test_no_contradictions(self) -> None:
        beliefs = [
            {
                "belief_id": "b1",
                "belief_text": "The sky is blue during daytime hours",
                "category": "world_model",
                "confidence": 0.8,
            },
            {
                "belief_id": "b2",
                "belief_text": "Python uses indentation for code blocks",
                "category": "capability",
                "confidence": 0.8,
            },
        ]
        result = find_belief_contradictions(beliefs)
        assert len(result) == 0
