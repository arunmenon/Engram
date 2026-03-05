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
    punctuation differences introduced by the LLM.  A ratio >= 0.6 against the
    best matching window is considered a match.  The threshold is kept
    deliberately low because LLMs frequently paraphrase or truncate quotes
    while still capturing the correct evidence.
    """
    if not quote or not conversation_text:
        return False

    normalized_quote = " ".join(quote.lower().split())
    normalized_text = " ".join(conversation_text.lower().split())

    # Exact substring — fast path
    if normalized_quote in normalized_text:
        return True

    # Check if any significant words from the quote appear in the text.
    # This catches cases where the LLM summarizes the quote rather than
    # copying it verbatim.
    quote_words = {w for w in normalized_quote.split() if len(w) > 3}
    if quote_words:
        text_words = set(normalized_text.split())
        overlap = len(quote_words & text_words) / len(quote_words)
        if overlap >= 0.6:
            return True

    # Sliding-window fuzzy match for short quotes
    window_size = len(normalized_quote)
    if window_size > len(normalized_text):
        return SequenceMatcher(None, normalized_quote, normalized_text).ratio() >= 0.6

    best_ratio = 0.0
    step = max(1, window_size // 4)
    for start in range(0, len(normalized_text) - window_size + 1, step):
        window = normalized_text[start : start + window_size]
        ratio = SequenceMatcher(None, normalized_quote, window).ratio()
        if ratio >= 0.6:
            return True
        best_ratio = max(best_ratio, ratio)

    return best_ratio >= 0.6


_NEGATION_MARKERS = frozenset(
    {
        "no",
        "not",
        "never",
        "none",
        "nor",
        "neither",
        "without",
        "don't",
        "doesn't",
        "didn't",
        "won't",
        "can't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
    }
)


def verify_entailment(claim: str, evidence: str) -> bool:
    """Verify that *claim* is entailed by *evidence*.

    Uses keyword overlap heuristic with negation detection: checks whether
    a sufficient fraction of significant words in the claim also appear in
    the evidence, and whether they agree on negation.

    TODO: Integrate DeBERTa-v3 NLI model for higher accuracy.
    """
    if not claim or not evidence:
        return False

    claim_lower = claim.lower().split()
    evidence_lower = evidence.lower().split()

    # Check for negation disagreement — one text negates, the other doesn't
    claim_negations = _NEGATION_MARKERS & set(claim_lower)
    evidence_negations = _NEGATION_MARKERS & set(evidence_lower)
    if bool(claim_negations) != bool(evidence_negations):
        return False

    # Use words with len > 2 to catch "no", "not", "bad", "can" etc.
    claim_words = {w for w in claim_lower if len(w) > 2}
    if len(claim_words) < 2:
        return True  # Too short to meaningfully verify
    evidence_words = {w for w in evidence_lower if len(w) > 2}
    if not evidence_words:
        return True
    overlap = len(claim_words & evidence_words) / len(claim_words)
    return overlap >= 0.5


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


class ExtractedPersona(BaseModel):
    """User persona information extracted from a conversation session.

    Maps to :class:`UserProfile` node properties in Neo4j (ADR-0012).
    """

    name: str | None = None
    role: str | None = None
    tech_level: Literal["beginner", "intermediate", "advanced", "expert"] | None = None
    communication_style: str | None = None
    source_quote: str = Field(default="", min_length=0)


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
    persona: ExtractedPersona | None = None
