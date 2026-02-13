"""Three-tier entity resolution (ADR-0011 section 3).

Provides exact-match, alias-lookup, and fuzzy-match resolution for entities
extracted from conversation sessions.  Results map to MERGE / SAME_AS /
RELATED_TO / CREATE actions in the Neo4j graph projection.

Pure Python + stdlib — ZERO framework imports.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def normalize_entity_name(name: str) -> str:
    """Lowercase, strip leading/trailing whitespace, collapse internal spaces."""
    return " ".join(name.lower().split())


# ---------------------------------------------------------------------------
# Domain alias dictionary — merchant / tool aliases (extensible)
# ---------------------------------------------------------------------------

DOMAIN_ALIAS_DICT: dict[str, list[str]] = {
    "quickbooks": ["qb", "qbo", "quickbooks online"],
    "paypal": ["pp", "paypal.com"],
    "stripe": ["stripe.com", "stripe api"],
    "github": ["gh", "github.com"],
    "visual studio code": ["vscode", "vs code"],
    "javascript": ["js"],
    "typescript": ["ts"],
    "python": ["py"],
    "postgresql": ["postgres", "psql", "pg"],
    "kubernetes": ["k8s"],
    "docker": ["docker.io"],
    "amazon web services": ["aws"],
    "google cloud platform": ["gcp"],
    "microsoft azure": ["azure"],
    "usps": ["us postal service", "united states postal service"],
    "fedex": ["federal express"],
    "csv": ["comma separated values", "comma-separated values"],
}

# Build reverse lookup: alias -> canonical name
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in DOMAIN_ALIAS_DICT.items():
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias.lower()] = _canonical


def resolve_alias(name: str) -> str:
    """Return canonical name if *name* is a known alias, otherwise return normalized name."""
    normalized = normalize_entity_name(name)
    return _ALIAS_TO_CANONICAL.get(normalized, normalized)


# ---------------------------------------------------------------------------
# Resolution action and result
# ---------------------------------------------------------------------------


class EntityResolutionAction(enum.StrEnum):
    """Actions the resolution engine can recommend."""

    MERGE = "MERGE"
    SAME_AS = "SAME_AS"
    RELATED_TO = "RELATED_TO"
    CREATE = "CREATE"


@dataclass
class EntityResolutionResult:
    """Outcome of an entity resolution attempt."""

    action: EntityResolutionAction
    canonical_name: str
    entity_type: str
    confidence: float
    justification: str


# ---------------------------------------------------------------------------
# Tier 1: Exact match (after normalization + alias resolution)
# ---------------------------------------------------------------------------


def resolve_exact_match(
    name: str,
    entity_type: str,
    existing_entities: list[dict[str, Any]],
) -> EntityResolutionResult | None:
    """Tier 1: Normalize, resolve aliases, and look for an exact name match.

    ``existing_entities`` is a list of dicts with at least ``name`` and
    ``entity_type`` keys.

    Returns ``None`` if no exact match is found.
    """
    canonical = resolve_alias(name)
    for entity in existing_entities:
        existing_name = normalize_entity_name(entity.get("name", ""))
        existing_alias = resolve_alias(entity.get("name", ""))
        if canonical in (existing_name, existing_alias):
            if entity.get("entity_type", "") == entity_type:
                return EntityResolutionResult(
                    action=EntityResolutionAction.MERGE,
                    canonical_name=existing_name if canonical == existing_name else existing_alias,
                    entity_type=entity_type,
                    confidence=1.0,
                    justification=f"Exact match after normalization: '{canonical}'",
                )
            return EntityResolutionResult(
                action=EntityResolutionAction.SAME_AS,
                canonical_name=existing_name if canonical == existing_name else existing_alias,
                entity_type=entity.get("entity_type", entity_type),
                confidence=0.9,
                justification=(
                    f"Exact name match '{canonical}' but type differs "
                    f"({entity_type} vs {entity.get('entity_type')})"
                ),
            )
    return None


# ---------------------------------------------------------------------------
# Tier 2: Fuzzy / close match
# ---------------------------------------------------------------------------


def compute_name_similarity(name_a: str, name_b: str) -> float:
    """Character-level similarity between two names using SequenceMatcher.

    Both names are normalized before comparison.  Returns a value in [0.0, 1.0].
    """
    norm_a = normalize_entity_name(name_a)
    norm_b = normalize_entity_name(name_b)
    if not norm_a or not norm_b:
        return 0.0
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def resolve_close_match(
    name: str,
    entity_type: str,
    existing_entities: list[dict[str, Any]],
    threshold: float = 0.9,
) -> EntityResolutionResult | None:
    """Tier 2: Fuzzy name match above *threshold*.

    Iterates ``existing_entities`` and returns the best match with similarity
    >= *threshold*.  Returns ``None`` if no entity exceeds the threshold.
    """
    canonical = resolve_alias(name)
    normalized = normalize_entity_name(name)
    best_score = 0.0
    best_entity: dict[str, Any] | None = None

    for entity in existing_entities:
        existing_raw = normalize_entity_name(entity.get("name", ""))
        existing_canonical = resolve_alias(entity.get("name", ""))
        # Compare against both aliased and raw forms, taking the best
        score = max(
            compute_name_similarity(canonical, existing_canonical),
            compute_name_similarity(normalized, existing_raw),
            compute_name_similarity(canonical, existing_raw),
            compute_name_similarity(normalized, existing_canonical),
        )
        if score > best_score:
            best_score = score
            best_entity = entity

    if best_entity is not None and best_score >= threshold:
        existing_canonical = resolve_alias(best_entity.get("name", ""))
        if best_entity.get("entity_type", "") == entity_type:
            action = EntityResolutionAction.SAME_AS
        else:
            action = EntityResolutionAction.RELATED_TO
        return EntityResolutionResult(
            action=action,
            canonical_name=existing_canonical,
            entity_type=best_entity.get("entity_type", entity_type),
            confidence=round(best_score, 4),
            justification=(
                f"Fuzzy match '{canonical}' ~ '{existing_canonical}' (similarity={best_score:.4f})"
            ),
        )
    return None
