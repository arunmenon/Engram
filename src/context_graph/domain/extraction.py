"""Extraction target Pydantic models for LLM-based knowledge extraction (ADR-0013 section 4).

These models serve triple duty:
  (a) Schema definitions for LLM structured output (via Instructor)
  (b) Output validation with confidence bounds and source provenance
  (c) Neo4j node mapping targets for graph projection

Pure Python + Pydantic v2 — ZERO framework imports.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Confidence ceiling by source type (ADR-0013 section 7)
# ---------------------------------------------------------------------------

CONFIDENCE_CEILINGS: dict[str, float] = {
    "explicit": 0.95,
    "implicit_intentional": 0.7,
    "implicit_unintentional": 0.5,
    "observed": 0.85,
    "declared": 0.95,
    "inferred": 0.6,
    "implicit": 0.7,
}


def apply_confidence_prior(extraction_confidence: float, source_type: str) -> float:
    """Apply source-type confidence ceilings.

    Returns the minimum of ``extraction_confidence`` and the ceiling for
    ``source_type``. Unknown source types pass through unmodified.
    """
    ceiling = CONFIDENCE_CEILINGS.get(source_type)
    if ceiling is None:
        return extraction_confidence
    return min(extraction_confidence, ceiling)


def validate_source_quote(quote: str, conversation_text: str) -> bool:
    """Fuzzy substring check — does *quote* appear (approximately) in *conversation_text*?

    Uses :class:`~difflib.SequenceMatcher` to allow for minor whitespace /
    punctuation differences introduced by the LLM.  A ratio >= 0.8 against the
    best matching window is considered a match.
    """
    if not quote or not conversation_text:
        return False

    normalized_quote = " ".join(quote.lower().split())
    normalized_text = " ".join(conversation_text.lower().split())

    # Exact substring — fast path
    if normalized_quote in normalized_text:
        return True

    # Sliding-window fuzzy match for short quotes
    window_size = len(normalized_quote)
    if window_size > len(normalized_text):
        return SequenceMatcher(None, normalized_quote, normalized_text).ratio() >= 0.8

    best_ratio = 0.0
    step = max(1, window_size // 4)
    for start in range(0, len(normalized_text) - window_size + 1, step):
        window = normalized_text[start : start + window_size]
        ratio = SequenceMatcher(None, normalized_quote, window).ratio()
        if ratio >= 0.8:
            return True
        best_ratio = max(best_ratio, ratio)

    return best_ratio >= 0.8


# ---------------------------------------------------------------------------
# Extraction target models
# ---------------------------------------------------------------------------


class ExtractedEntity(BaseModel):
    """An entity extracted from a conversation session."""

    name: str = Field(..., min_length=1)
    entity_type: Literal["agent", "user", "service", "tool", "resource", "concept"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_quote: str = Field(..., min_length=1)
    source_turn_index: int | None = None


class ExtractedPreference(BaseModel):
    """A user preference extracted from a conversation session (ADR-0012 section 1.2)."""

    category: Literal["tool", "workflow", "communication", "domain", "environment", "style"]
    key: str = Field(..., min_length=1)
    polarity: Literal["positive", "negative", "neutral"]
    strength: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: Literal["explicit", "implicit_intentional", "implicit_unintentional"]
    context: str | None = None
    about_entity: str | None = None
    source_quote: str = Field(..., min_length=1)
    source_turn_index: int | None = None


class ExtractedSkill(BaseModel):
    """A user skill / competency extracted from a conversation session."""

    name: str = Field(..., min_length=1)
    category: Literal[
        "programming_language", "tool_proficiency", "domain_knowledge", "workflow_skill"
    ]
    proficiency: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: Literal["observed", "declared", "inferred"]
    source_quote: str = Field(..., min_length=1)
    source_turn_index: int | None = None


class ExtractedInterest(BaseModel):
    """A user interest / topical affinity extracted from a conversation session."""

    entity_name: str = Field(..., min_length=1)
    entity_type: Literal["agent", "user", "service", "tool", "resource", "concept"]
    weight: float = Field(..., ge=0.0, le=1.0)
    source: Literal["explicit", "implicit", "inferred"]
    source_quote: str = Field(..., min_length=1)
    source_turn_index: int | None = None


class SessionExtractionResult(BaseModel):
    """Aggregated extraction output for an entire session."""

    session_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    model_id: str | None = None
    prompt_version: str | None = None
    entities: list[ExtractedEntity] = Field(default_factory=list)
    preferences: list[ExtractedPreference] = Field(default_factory=list)
    skills: list[ExtractedSkill] = Field(default_factory=list)
    interests: list[ExtractedInterest] = Field(default_factory=list)
