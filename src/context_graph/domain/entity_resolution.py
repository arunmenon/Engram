"""Three-tier entity resolution (ADR-0011 section 3).

Provides exact-match, alias-lookup, fuzzy-match, and semantic-match
resolution for entities extracted from conversation sessions.  Results map
to MERGE / SAME_AS / RELATED_TO / CREATE actions in the Neo4j graph projection.

Tier 1:  Exact match (normalization + alias dict)
Tier 2a: Fuzzy match (SequenceMatcher >= 0.9)
Tier 2b: Semantic match (embedding cosine similarity)

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


# ---------------------------------------------------------------------------
# Tier 2b: Semantic match (embedding-based)
# ---------------------------------------------------------------------------


@dataclass
class SemanticCandidate:
    """A candidate entity returned by vector similarity search.

    Pure domain object — no adapter dependencies.  The adapter layer
    converts its internal ``SemanticMatch`` into this structure before
    passing it to the domain resolver.
    """

    name: str
    entity_type: str
    entity_id: str
    similarity: float


def resolve_semantic_match(
    name: str,
    entity_type: str,
    candidates: list[SemanticCandidate],
    same_as_threshold: float = 0.90,
    related_to_threshold: float = 0.75,
) -> EntityResolutionResult | None:
    """Tier 2b: Resolve an entity via pre-computed embedding similarity.

    Takes a list of ``SemanticCandidate`` objects (produced by the adapter
    layer's KNN search) and returns the best resolution result.

    **Key rule**: Semantic matches NEVER produce MERGE — only SAME_AS
    (>= ``same_as_threshold``) or RELATED_TO (>= ``related_to_threshold``).
    Below ``related_to_threshold``, returns ``None`` (fall through to CREATE).

    Parameters
    ----------
    name:
        The new entity name being resolved.
    entity_type:
        The new entity's type label.
    candidates:
        Pre-sorted (highest similarity first) semantic matches.
    same_as_threshold:
        Cosine similarity at or above which to emit SAME_AS.
    related_to_threshold:
        Cosine similarity at or above which to emit RELATED_TO.
    """
    if not candidates:
        return None

    best = candidates[0]

    if best.similarity < related_to_threshold:
        return None

    if best.similarity >= same_as_threshold:
        action = EntityResolutionAction.SAME_AS
    else:
        action = EntityResolutionAction.RELATED_TO

    return EntityResolutionResult(
        action=action,
        canonical_name=best.name,
        entity_type=best.entity_type,
        confidence=round(best.similarity, 4),
        justification=(
            f"Semantic match '{normalize_entity_name(name)}' ~ "
            f"'{best.name}' (cosine={best.similarity:.4f})"
        ),
    )


# ---------------------------------------------------------------------------
# Transitive closure via Union-Find (connected-component clustering)
# ---------------------------------------------------------------------------


class _UnionFind:
    """Disjoint-set / union-find data structure for entity clustering."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        """Find root with path compression."""
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path halving
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        """Union by rank."""
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return
        if self._rank[root_a] < self._rank[root_b]:
            root_a, root_b = root_b, root_a
        self._parent[root_b] = root_a
        if self._rank[root_a] == self._rank[root_b]:
            self._rank[root_a] += 1


def compute_transitive_closure(
    edges: list[tuple[str, str]],
    mention_counts: dict[str, int] | None = None,
) -> dict[str, list[str]]:
    """Compute connected-component clusters from pairwise SAME_AS edges.

    Uses Union-Find to group transitively connected entities into clusters.
    The canonical entity for each cluster is the one with the highest
    ``mention_count`` (ties broken alphabetically).

    Parameters
    ----------
    edges:
        List of ``(entity_id_a, entity_id_b)`` SAME_AS pairs.
    mention_counts:
        Optional mapping of ``entity_id -> mention_count``.  When ``None``,
        the canonical is chosen alphabetically.

    Returns
    -------
    dict mapping ``canonical_id`` to the full list of cluster member IDs
    (including the canonical itself).  Singleton entities (those appearing
    in ``edges`` with no partner beyond themselves) are included if they
    appear in the edge list.
    """
    if not edges:
        return {}

    counts = mention_counts or {}
    uf = _UnionFind()

    for a, b in edges:
        if a == b:
            # Self-edges are no-ops but ensure the node exists in UF
            uf.find(a)
            continue
        uf.union(a, b)

    # Gather clusters keyed by root
    clusters: dict[str, list[str]] = {}
    seen: set[str] = set()
    for a, b in edges:
        for node in (a, b):
            if node not in seen:
                seen.add(node)
                root = uf.find(node)
                clusters.setdefault(root, []).append(node)

    # Re-key clusters by canonical (highest mention_count, then alphabetical)
    result: dict[str, list[str]] = {}
    for members in clusters.values():
        canonical = min(
            members,
            key=lambda m: (-counts.get(m, 0), m),
        )
        result[canonical] = sorted(members)

    return result
