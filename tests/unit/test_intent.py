"""Unit tests for context_graph.domain.intent."""

from __future__ import annotations

from context_graph.domain.intent import (
    classify_intent,
    get_edge_weights,
    select_seed_strategy,
)
from context_graph.domain.models import EdgeType, IntentType
from context_graph.settings import INTENT_WEIGHTS


class TestClassifyIntent:
    """Tests for rule-based intent classification."""

    def test_why_query(self) -> None:
        """A 'why' question should produce WHY as the dominant intent."""
        result = classify_intent("why did the build fail?")
        assert IntentType.WHY in result
        assert result[IntentType.WHY] == 1.0

    def test_when_query(self) -> None:
        """A 'when' question should produce WHEN as the dominant intent."""
        result = classify_intent("when did the deploy happen?")
        assert IntentType.WHEN in result
        assert result[IntentType.WHEN] == 1.0

    def test_what_query(self) -> None:
        """A 'what' question should produce WHAT as the dominant intent."""
        result = classify_intent("what is the meaning of this error?")
        assert IntentType.WHAT in result
        assert result[IntentType.WHAT] == 1.0

    def test_general_query(self) -> None:
        """A query with no matching keywords returns GENERAL."""
        result = classify_intent("give me data")
        assert IntentType.GENERAL in result
        assert result[IntentType.GENERAL] == 0.5

    def test_multi_intent(self) -> None:
        """A query with multiple intent keywords should match multiple intents."""
        result = classify_intent("why and when did it fail?")
        assert IntentType.WHY in result
        assert IntentType.WHEN in result

    def test_who_is_query(self) -> None:
        """A 'who' question should produce WHO_IS intent."""
        result = classify_intent("who is the author of this commit?")
        assert IntentType.WHO_IS in result
        assert result[IntentType.WHO_IS] == 1.0

    def test_how_does_query(self) -> None:
        """A 'how' question should produce HOW_DOES intent."""
        result = classify_intent("how does the deployment process work?")
        assert IntentType.HOW_DOES in result

    def test_personalize_query(self) -> None:
        """Preference-related keywords should produce PERSONALIZE intent."""
        result = classify_intent("customize my preferred workflow style")
        assert IntentType.PERSONALIZE in result

    def test_case_insensitive(self) -> None:
        """Classification should be case-insensitive."""
        result = classify_intent("WHY DID THE BUILD FAIL?")
        assert IntentType.WHY in result

    def test_empty_query(self) -> None:
        """An empty query returns GENERAL."""
        result = classify_intent("")
        assert IntentType.GENERAL in result

    def test_normalized_max_is_one(self) -> None:
        """The highest-scoring intent should always be normalized to 1.0."""
        result = classify_intent("why did it fail because of the root cause?")
        max_score = max(result.values())
        assert abs(max_score - 1.0) < 1e-6


class TestGetEdgeWeights:
    """Tests for edge weight computation from intents."""

    def test_single_intent_produces_weights(self) -> None:
        """A single intent should produce edge weights from the matrix."""
        intents = {IntentType.WHY: 1.0}
        weights = get_edge_weights(intents, INTENT_WEIGHTS)
        assert EdgeType.CAUSED_BY in weights
        assert weights[EdgeType.CAUSED_BY] == 5.0

    def test_multi_intent_accumulates(self) -> None:
        """Multiple intents should accumulate edge weights."""
        intents = {IntentType.WHY: 1.0, IntentType.WHEN: 0.5}
        weights = get_edge_weights(intents, INTENT_WEIGHTS)
        # CAUSED_BY: 1.0*5.0 + 0.5*1.0 = 5.5
        assert abs(weights[EdgeType.CAUSED_BY] - 5.5) < 1e-6
        # FOLLOWS: 1.0*1.0 + 0.5*5.0 = 3.5
        assert abs(weights[EdgeType.FOLLOWS] - 3.5) < 1e-6

    def test_empty_intents(self) -> None:
        """Empty intents should produce empty edge weights."""
        weights = get_edge_weights({}, INTENT_WEIGHTS)
        assert weights == {}

    def test_unknown_intent_ignored(self) -> None:
        """An intent not in the matrix should be ignored."""
        intents = {"nonexistent_intent": 1.0}
        weights = get_edge_weights(intents, INTENT_WEIGHTS)
        assert weights == {}

    def test_confidence_scales_weights(self) -> None:
        """Confidence < 1.0 should scale edge weights proportionally."""
        intents = {IntentType.WHY: 0.5}
        weights = get_edge_weights(intents, INTENT_WEIGHTS)
        assert abs(weights[EdgeType.CAUSED_BY] - 2.5) < 1e-6


class TestSelectSeedStrategy:
    """Tests for seed node strategy selection."""

    def test_why_returns_causal_roots(self) -> None:
        assert select_seed_strategy({IntentType.WHY: 1.0}) == "causal_roots"

    def test_when_returns_temporal_anchors(self) -> None:
        assert select_seed_strategy({IntentType.WHEN: 1.0}) == "temporal_anchors"

    def test_what_returns_entity_hubs(self) -> None:
        assert select_seed_strategy({IntentType.WHAT: 1.0}) == "entity_hubs"

    def test_who_is_returns_entity_hubs(self) -> None:
        assert select_seed_strategy({IntentType.WHO_IS: 1.0}) == "entity_hubs"

    def test_related_returns_similar_cluster(self) -> None:
        assert select_seed_strategy({IntentType.RELATED: 1.0}) == "similar_cluster"

    def test_how_does_returns_workflow_pattern(self) -> None:
        assert select_seed_strategy({IntentType.HOW_DOES: 1.0}) == "workflow_pattern"

    def test_personalize_returns_user_profile(self) -> None:
        assert select_seed_strategy({IntentType.PERSONALIZE: 1.0}) == "user_profile"

    def test_general_returns_general(self) -> None:
        assert select_seed_strategy({IntentType.GENERAL: 0.5}) == "general"

    def test_empty_intents_returns_general(self) -> None:
        assert select_seed_strategy({}) == "general"

    def test_dominant_intent_wins(self) -> None:
        """When multiple intents exist, the highest-scoring one determines strategy."""
        intents = {IntentType.WHY: 0.9, IntentType.WHEN: 0.3}
        assert select_seed_strategy(intents) == "causal_roots"
