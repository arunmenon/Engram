"""Unit tests for semantic entity resolution (Tier 2b).

Validates SemanticCandidate dataclass and resolve_semantic_match() from
src/context_graph/domain/entity_resolution.py.
"""

from __future__ import annotations

from context_graph.domain.entity_resolution import (
    EntityResolutionAction,
    SemanticCandidate,
    resolve_semantic_match,
)

# ---------------------------------------------------------------------------
# SemanticCandidate dataclass
# ---------------------------------------------------------------------------


class TestSemanticCandidate:
    def test_creation_with_all_fields(self):
        candidate = SemanticCandidate(
            name="quickbooks",
            entity_type="tool",
            entity_id="ent-001",
            similarity=0.92,
        )
        assert candidate.name == "quickbooks"
        assert candidate.entity_type == "tool"
        assert candidate.entity_id == "ent-001"
        assert candidate.similarity == 0.92

    def test_field_types(self):
        candidate = SemanticCandidate(
            name="stripe",
            entity_type="service",
            entity_id="ent-002",
            similarity=0.87,
        )
        assert isinstance(candidate.name, str)
        assert isinstance(candidate.entity_type, str)
        assert isinstance(candidate.entity_id, str)
        assert isinstance(candidate.similarity, float)


# ---------------------------------------------------------------------------
# resolve_semantic_match — empty / no candidates
# ---------------------------------------------------------------------------


class TestResolveSemanticMatchEmpty:
    def test_empty_candidates_returns_none(self):
        result = resolve_semantic_match("quickbooks", "tool", candidates=[])
        assert result is None

    def test_all_candidates_below_related_to_threshold_returns_none(self):
        candidates = [
            SemanticCandidate(
                name="unrelated_entity",
                entity_type="concept",
                entity_id="ent-099",
                similarity=0.50,
            ),
            SemanticCandidate(
                name="another_low",
                entity_type="tool",
                entity_id="ent-098",
                similarity=0.30,
            ),
        ]
        result = resolve_semantic_match("quickbooks", "tool", candidates)
        assert result is None


# ---------------------------------------------------------------------------
# resolve_semantic_match — SAME_AS
# ---------------------------------------------------------------------------


class TestResolveSemanticMatchSameAs:
    def test_single_candidate_above_same_as_threshold(self):
        candidates = [
            SemanticCandidate(
                name="quickbooks online",
                entity_type="tool",
                entity_id="ent-010",
                similarity=0.95,
            ),
        ]
        result = resolve_semantic_match("quickbooks", "tool", candidates)
        assert result is not None
        assert result.action == EntityResolutionAction.SAME_AS
        assert result.canonical_name == "quickbooks online"
        assert result.entity_type == "tool"

    def test_multiple_candidates_picks_first(self):
        candidates = [
            SemanticCandidate(
                name="quickbooks online",
                entity_type="tool",
                entity_id="ent-010",
                similarity=0.96,
            ),
            SemanticCandidate(
                name="quickbooks desktop",
                entity_type="tool",
                entity_id="ent-011",
                similarity=0.91,
            ),
        ]
        result = resolve_semantic_match("quickbooks", "tool", candidates)
        assert result is not None
        assert result.action == EntityResolutionAction.SAME_AS
        assert result.canonical_name == "quickbooks online"

    def test_exact_same_as_boundary(self):
        candidates = [
            SemanticCandidate(
                name="stripe api",
                entity_type="service",
                entity_id="ent-020",
                similarity=0.90,
            ),
        ]
        result = resolve_semantic_match("stripe", "service", candidates)
        assert result is not None
        assert result.action == EntityResolutionAction.SAME_AS

    def test_confidence_correctly_rounded(self):
        candidates = [
            SemanticCandidate(
                name="kubernetes",
                entity_type="concept",
                entity_id="ent-030",
                similarity=0.923456789,
            ),
        ]
        result = resolve_semantic_match("k8s cluster", "concept", candidates)
        assert result is not None
        assert result.confidence == 0.9235


# ---------------------------------------------------------------------------
# resolve_semantic_match — RELATED_TO
# ---------------------------------------------------------------------------


class TestResolveSemanticMatchRelatedTo:
    def test_candidate_between_thresholds(self):
        candidates = [
            SemanticCandidate(
                name="paypal checkout",
                entity_type="service",
                entity_id="ent-040",
                similarity=0.82,
            ),
        ]
        result = resolve_semantic_match("paypal payments", "service", candidates)
        assert result is not None
        assert result.action == EntityResolutionAction.RELATED_TO
        assert result.canonical_name == "paypal checkout"

    def test_exact_related_to_boundary(self):
        candidates = [
            SemanticCandidate(
                name="docker compose",
                entity_type="tool",
                entity_id="ent-050",
                similarity=0.75,
            ),
        ]
        result = resolve_semantic_match("docker swarm", "tool", candidates)
        assert result is not None
        assert result.action == EntityResolutionAction.RELATED_TO

    def test_justification_contains_semantic_match(self):
        candidates = [
            SemanticCandidate(
                name="postgresql",
                entity_type="concept",
                entity_id="ent-060",
                similarity=0.80,
            ),
        ]
        result = resolve_semantic_match("postgres db", "concept", candidates)
        assert result is not None
        assert "Semantic match" in result.justification


# ---------------------------------------------------------------------------
# resolve_semantic_match — custom thresholds
# ---------------------------------------------------------------------------


class TestResolveSemanticMatchCustomThresholds:
    def test_custom_same_as_threshold(self):
        candidates = [
            SemanticCandidate(
                name="github actions",
                entity_type="tool",
                entity_id="ent-070",
                similarity=0.93,
            ),
        ]
        # With default threshold (0.90) this would be SAME_AS,
        # but with a stricter threshold it should be RELATED_TO.
        result = resolve_semantic_match(
            "github ci",
            "tool",
            candidates,
            same_as_threshold=0.95,
        )
        assert result is not None
        assert result.action == EntityResolutionAction.RELATED_TO

    def test_custom_related_to_threshold(self):
        candidates = [
            SemanticCandidate(
                name="aws lambda",
                entity_type="service",
                entity_id="ent-080",
                similarity=0.78,
            ),
        ]
        # With default related_to threshold (0.75) this would be RELATED_TO,
        # but with a stricter threshold it should return None.
        result = resolve_semantic_match(
            "aws functions",
            "service",
            candidates,
            related_to_threshold=0.80,
        )
        assert result is None


# ---------------------------------------------------------------------------
# resolve_semantic_match — never produces MERGE
# ---------------------------------------------------------------------------


class TestResolveSemanticMatchNeverMerge:
    def test_high_similarity_never_produces_merge(self):
        """ADR-0011: semantic matches NEVER produce MERGE."""
        candidates = [
            SemanticCandidate(
                name="python",
                entity_type="concept",
                entity_id="ent-090",
                similarity=1.0,
            ),
        ]
        result = resolve_semantic_match("python", "concept", candidates)
        assert result is not None
        assert result.action != EntityResolutionAction.MERGE
        assert result.action == EntityResolutionAction.SAME_AS
