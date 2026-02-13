"""Unit tests for domain extraction models (src/context_graph/domain/extraction.py).

Validates Pydantic model construction, field constraints, confidence ceilings,
source quote validation, and session result aggregation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from context_graph.domain.extraction import (
    CONFIDENCE_CEILINGS,
    ExtractedEntity,
    ExtractedInterest,
    ExtractedPreference,
    ExtractedSkill,
    SessionExtractionResult,
    apply_confidence_prior,
    validate_source_quote,
)

# ---------------------------------------------------------------------------
# ExtractedEntity
# ---------------------------------------------------------------------------


class TestExtractedEntity:
    def test_valid_entity(self):
        entity = ExtractedEntity(
            name="QuickBooks",
            entity_type="tool",
            confidence=0.9,
            source_quote="I use QuickBooks for invoicing",
            source_turn_index=3,
        )
        assert entity.name == "QuickBooks"
        assert entity.entity_type == "tool"
        assert entity.confidence == 0.9
        assert entity.source_turn_index == 3

    def test_entity_all_types(self):
        for etype in ("agent", "user", "service", "tool", "resource", "concept"):
            entity = ExtractedEntity(
                name="test",
                entity_type=etype,
                confidence=0.5,
                source_quote="test quote",
            )
            assert entity.entity_type == etype

    def test_entity_invalid_type(self):
        with pytest.raises(ValidationError):
            ExtractedEntity(
                name="test",
                entity_type="unknown_type",
                confidence=0.5,
                source_quote="test quote",
            )

    def test_entity_confidence_too_high(self):
        with pytest.raises(ValidationError):
            ExtractedEntity(
                name="test",
                entity_type="tool",
                confidence=1.5,
                source_quote="test quote",
            )

    def test_entity_confidence_too_low(self):
        with pytest.raises(ValidationError):
            ExtractedEntity(
                name="test",
                entity_type="tool",
                confidence=-0.1,
                source_quote="test quote",
            )

    def test_entity_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ExtractedEntity(
                name="",
                entity_type="tool",
                confidence=0.5,
                source_quote="test quote",
            )

    def test_entity_empty_source_quote_rejected(self):
        with pytest.raises(ValidationError):
            ExtractedEntity(
                name="test",
                entity_type="tool",
                confidence=0.5,
                source_quote="",
            )

    def test_entity_source_turn_index_optional(self):
        entity = ExtractedEntity(
            name="test",
            entity_type="concept",
            confidence=0.8,
            source_quote="some quote",
        )
        assert entity.source_turn_index is None


# ---------------------------------------------------------------------------
# ExtractedPreference
# ---------------------------------------------------------------------------


class TestExtractedPreference:
    def test_valid_preference(self):
        pref = ExtractedPreference(
            category="tool",
            key="notification_method",
            polarity="positive",
            strength=0.8,
            confidence=0.9,
            source="explicit",
            context="work context",
            about_entity="Slack",
            source_quote="I prefer Slack notifications",
            source_turn_index=5,
        )
        assert pref.category == "tool"
        assert pref.polarity == "positive"
        assert pref.about_entity == "Slack"

    def test_preference_all_categories(self):
        for cat in ("tool", "workflow", "communication", "domain", "environment", "style"):
            pref = ExtractedPreference(
                category=cat,
                key="test_key",
                polarity="neutral",
                strength=0.5,
                confidence=0.5,
                source="explicit",
                source_quote="test quote",
            )
            assert pref.category == cat

    def test_preference_invalid_category(self):
        with pytest.raises(ValidationError):
            ExtractedPreference(
                category="invalid_cat",
                key="test_key",
                polarity="neutral",
                strength=0.5,
                confidence=0.5,
                source="explicit",
                source_quote="test quote",
            )

    def test_preference_all_polarities(self):
        for pol in ("positive", "negative", "neutral"):
            pref = ExtractedPreference(
                category="tool",
                key="test_key",
                polarity=pol,
                strength=0.5,
                confidence=0.5,
                source="explicit",
                source_quote="test quote",
            )
            assert pref.polarity == pol

    def test_preference_all_sources(self):
        for src in ("explicit", "implicit_intentional", "implicit_unintentional"):
            pref = ExtractedPreference(
                category="tool",
                key="test_key",
                polarity="neutral",
                strength=0.5,
                confidence=0.5,
                source=src,
                source_quote="test quote",
            )
            assert pref.source == src

    def test_preference_strength_out_of_range(self):
        with pytest.raises(ValidationError):
            ExtractedPreference(
                category="tool",
                key="test_key",
                polarity="neutral",
                strength=1.1,
                confidence=0.5,
                source="explicit",
                source_quote="test quote",
            )

    def test_preference_optional_fields_default_none(self):
        pref = ExtractedPreference(
            category="tool",
            key="test_key",
            polarity="neutral",
            strength=0.5,
            confidence=0.5,
            source="explicit",
            source_quote="test quote",
        )
        assert pref.context is None
        assert pref.about_entity is None
        assert pref.source_turn_index is None


# ---------------------------------------------------------------------------
# ExtractedSkill
# ---------------------------------------------------------------------------


class TestExtractedSkill:
    def test_valid_skill(self):
        skill = ExtractedSkill(
            name="Python",
            category="programming_language",
            proficiency=0.8,
            confidence=0.9,
            source="declared",
            source_quote="I'm an expert Python developer",
            source_turn_index=1,
        )
        assert skill.name == "Python"
        assert skill.proficiency == 0.8

    def test_skill_all_categories(self):
        for cat in (
            "programming_language",
            "tool_proficiency",
            "domain_knowledge",
            "workflow_skill",
        ):
            skill = ExtractedSkill(
                name="test",
                category=cat,
                proficiency=0.5,
                confidence=0.5,
                source="observed",
                source_quote="test quote",
            )
            assert skill.category == cat

    def test_skill_all_sources(self):
        for src in ("observed", "declared", "inferred"):
            skill = ExtractedSkill(
                name="test",
                category="tool_proficiency",
                proficiency=0.5,
                confidence=0.5,
                source=src,
                source_quote="test quote",
            )
            assert skill.source == src

    def test_skill_proficiency_bounds(self):
        # Valid boundaries
        ExtractedSkill(
            name="test",
            category="tool_proficiency",
            proficiency=0.0,
            confidence=0.0,
            source="observed",
            source_quote="test quote",
        )
        ExtractedSkill(
            name="test",
            category="tool_proficiency",
            proficiency=1.0,
            confidence=1.0,
            source="observed",
            source_quote="test quote",
        )

    def test_skill_proficiency_out_of_range(self):
        with pytest.raises(ValidationError):
            ExtractedSkill(
                name="test",
                category="tool_proficiency",
                proficiency=1.01,
                confidence=0.5,
                source="observed",
                source_quote="test quote",
            )


# ---------------------------------------------------------------------------
# ExtractedInterest
# ---------------------------------------------------------------------------


class TestExtractedInterest:
    def test_valid_interest(self):
        interest = ExtractedInterest(
            entity_name="machine learning",
            entity_type="concept",
            weight=0.85,
            source="explicit",
            source_quote="I'm really interested in ML",
            source_turn_index=2,
        )
        assert interest.entity_name == "machine learning"
        assert interest.weight == 0.85

    def test_interest_all_entity_types(self):
        for etype in ("agent", "user", "service", "tool", "resource", "concept"):
            interest = ExtractedInterest(
                entity_name="test",
                entity_type=etype,
                weight=0.5,
                source="explicit",
                source_quote="test quote",
            )
            assert interest.entity_type == etype

    def test_interest_all_sources(self):
        for src in ("explicit", "implicit", "inferred"):
            interest = ExtractedInterest(
                entity_name="test",
                entity_type="concept",
                weight=0.5,
                source=src,
                source_quote="test quote",
            )
            assert interest.source == src

    def test_interest_weight_out_of_range(self):
        with pytest.raises(ValidationError):
            ExtractedInterest(
                entity_name="test",
                entity_type="concept",
                weight=-0.5,
                source="explicit",
                source_quote="test quote",
            )


# ---------------------------------------------------------------------------
# SessionExtractionResult
# ---------------------------------------------------------------------------


class TestSessionExtractionResult:
    def test_empty_session_result(self):
        result = SessionExtractionResult(
            session_id="sess-001",
            agent_id="agent-001",
        )
        assert result.entities == []
        assert result.preferences == []
        assert result.skills == []
        assert result.interests == []
        assert result.model_id is None
        assert result.prompt_version is None

    def test_populated_session_result(self):
        entity = ExtractedEntity(
            name="Stripe",
            entity_type="service",
            confidence=0.9,
            source_quote="We use Stripe",
        )
        pref = ExtractedPreference(
            category="tool",
            key="payment_processor",
            polarity="positive",
            strength=0.9,
            confidence=0.85,
            source="explicit",
            source_quote="I prefer Stripe",
        )
        skill = ExtractedSkill(
            name="API integration",
            category="domain_knowledge",
            proficiency=0.7,
            confidence=0.8,
            source="observed",
            source_quote="integrated the payment API",
        )
        interest = ExtractedInterest(
            entity_name="payments",
            entity_type="concept",
            weight=0.8,
            source="implicit",
            source_quote="asked about payment flows",
        )
        result = SessionExtractionResult(
            session_id="sess-001",
            agent_id="agent-001",
            model_id="gpt-4o",
            prompt_version="v1.2",
            entities=[entity],
            preferences=[pref],
            skills=[skill],
            interests=[interest],
        )
        assert len(result.entities) == 1
        assert len(result.preferences) == 1
        assert len(result.skills) == 1
        assert len(result.interests) == 1
        assert result.model_id == "gpt-4o"


# ---------------------------------------------------------------------------
# validate_source_quote
# ---------------------------------------------------------------------------


class TestValidateSourceQuote:
    def test_exact_substring_match(self):
        text = "The user said I prefer Slack for notifications."
        assert validate_source_quote("I prefer Slack for notifications", text) is True

    def test_case_insensitive_match(self):
        text = "The user said I PREFER Slack."
        assert validate_source_quote("i prefer slack", text) is True

    def test_whitespace_normalization(self):
        text = "The user   said   I prefer   Slack."
        assert validate_source_quote("I prefer Slack", text) is True

    def test_no_match(self):
        text = "The user talked about payment processing."
        assert validate_source_quote("I prefer email notifications", text) is False

    def test_empty_quote(self):
        assert validate_source_quote("", "some conversation") is False

    def test_empty_conversation(self):
        assert validate_source_quote("some quote", "") is False

    def test_fuzzy_match_with_minor_difference(self):
        text = "I really like using Python for data analysis"
        # Minor variation
        assert validate_source_quote("I really like using Python for data", text) is True


# ---------------------------------------------------------------------------
# apply_confidence_prior
# ---------------------------------------------------------------------------


class TestApplyConfidencePrior:
    def test_explicit_cap(self):
        assert apply_confidence_prior(1.0, "explicit") == 0.95

    def test_implicit_intentional_cap(self):
        assert apply_confidence_prior(0.9, "implicit_intentional") == 0.7

    def test_implicit_unintentional_cap(self):
        assert apply_confidence_prior(0.8, "implicit_unintentional") == 0.5

    def test_below_cap_unchanged(self):
        assert apply_confidence_prior(0.3, "explicit") == 0.3

    def test_unknown_source_passthrough(self):
        assert apply_confidence_prior(0.99, "unknown_source") == 0.99

    def test_confidence_ceilings_has_expected_keys(self):
        assert "explicit" in CONFIDENCE_CEILINGS
        assert "implicit_intentional" in CONFIDENCE_CEILINGS
        assert "implicit_unintentional" in CONFIDENCE_CEILINGS
        assert "observed" in CONFIDENCE_CEILINGS
        assert "declared" in CONFIDENCE_CEILINGS
        assert "inferred" in CONFIDENCE_CEILINGS


# ---------------------------------------------------------------------------
# Source quote threshold regression (0.85)
# ---------------------------------------------------------------------------


class TestSourceQuoteThreshold085:
    """Source quote validation uses 0.85 threshold (not 0.80)."""

    def test_ratio_084_rejected(self):
        """A match with ratio ~0.84 should be rejected."""
        text = "hello world xyz extra padding here"
        assert validate_source_quote("hello world abc", text) is False

    def test_ratio_086_accepted(self):
        """A near-exact match should still be accepted."""
        text = "I prefer using Python for analysis tasks"
        assert validate_source_quote("I prefer using Python for analysis", text) is True


# ---------------------------------------------------------------------------
# Entailment stub
# ---------------------------------------------------------------------------


class TestEntailmentStub:
    def test_entailment_stub_returns_true(self):
        from context_graph.domain.extraction import verify_entailment

        assert verify_entailment("Python is fast", "Python is a fast programming language") is True

    def test_entailment_stub_always_true(self):
        from context_graph.domain.extraction import verify_entailment

        assert verify_entailment("cats are dogs", "fish swim in water") is True
