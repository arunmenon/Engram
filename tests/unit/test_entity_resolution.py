"""Unit tests for entity resolution (src/context_graph/domain/entity_resolution.py).

Validates normalization, alias lookup, exact match, fuzzy match, and
resolution result structures.
"""

from __future__ import annotations

from context_graph.domain.entity_resolution import (
    DOMAIN_ALIAS_DICT,
    EntityResolutionAction,
    EntityResolutionResult,
    compute_name_similarity,
    normalize_entity_name,
    resolve_alias,
    resolve_close_match,
    resolve_exact_match,
)

# ---------------------------------------------------------------------------
# normalize_entity_name
# ---------------------------------------------------------------------------


class TestNormalizeEntityName:
    def test_lowercase(self):
        assert normalize_entity_name("QuickBooks") == "quickbooks"

    def test_strip_whitespace(self):
        assert normalize_entity_name("  hello  ") == "hello"

    def test_collapse_internal_spaces(self):
        assert normalize_entity_name("Visual   Studio   Code") == "visual studio code"

    def test_empty_string(self):
        assert normalize_entity_name("") == ""

    def test_already_normalized(self):
        assert normalize_entity_name("python") == "python"

    def test_mixed_whitespace(self):
        assert normalize_entity_name("\tDocker  \n  Hub\r") == "docker hub"


# ---------------------------------------------------------------------------
# resolve_alias
# ---------------------------------------------------------------------------


class TestResolveAlias:
    def test_known_alias_qb(self):
        assert resolve_alias("QB") == "quickbooks"

    def test_known_alias_pp(self):
        assert resolve_alias("PP") == "paypal"

    def test_known_alias_vscode(self):
        assert resolve_alias("vscode") == "visual studio code"

    def test_known_alias_k8s(self):
        assert resolve_alias("k8s") == "kubernetes"

    def test_unknown_name_passthrough(self):
        assert resolve_alias("SomeUnknownTool") == "someunknowntool"

    def test_case_insensitive_alias(self):
        assert resolve_alias("GH") == "github"

    def test_canonical_name_returns_itself_normalized(self):
        assert resolve_alias("Python") == "python"


# ---------------------------------------------------------------------------
# DOMAIN_ALIAS_DICT
# ---------------------------------------------------------------------------


class TestDomainAliasDict:
    def test_has_expected_entries(self):
        assert "quickbooks" in DOMAIN_ALIAS_DICT
        assert "paypal" in DOMAIN_ALIAS_DICT
        assert "github" in DOMAIN_ALIAS_DICT

    def test_aliases_are_lists(self):
        for canonical, aliases in DOMAIN_ALIAS_DICT.items():
            assert isinstance(aliases, list), f"Aliases for {canonical} must be a list"


# ---------------------------------------------------------------------------
# EntityResolutionAction
# ---------------------------------------------------------------------------


class TestEntityResolutionAction:
    def test_all_actions(self):
        assert EntityResolutionAction.MERGE == "MERGE"
        assert EntityResolutionAction.SAME_AS == "SAME_AS"
        assert EntityResolutionAction.RELATED_TO == "RELATED_TO"
        assert EntityResolutionAction.CREATE == "CREATE"


# ---------------------------------------------------------------------------
# EntityResolutionResult
# ---------------------------------------------------------------------------


class TestEntityResolutionResult:
    def test_dataclass_creation(self):
        result = EntityResolutionResult(
            action=EntityResolutionAction.MERGE,
            canonical_name="quickbooks",
            entity_type="tool",
            confidence=1.0,
            justification="Exact match",
        )
        assert result.action == EntityResolutionAction.MERGE
        assert result.canonical_name == "quickbooks"
        assert result.confidence == 1.0


# ---------------------------------------------------------------------------
# resolve_exact_match
# ---------------------------------------------------------------------------


class TestResolveExactMatch:
    def _entities(self) -> list[dict]:
        return [
            {"name": "QuickBooks", "entity_type": "tool"},
            {"name": "Stripe", "entity_type": "service"},
            {"name": "Python", "entity_type": "concept"},
        ]

    def test_exact_match_same_type(self):
        result = resolve_exact_match("quickbooks", "tool", self._entities())
        assert result is not None
        assert result.action == EntityResolutionAction.MERGE
        assert result.confidence == 1.0

    def test_exact_match_via_alias(self):
        result = resolve_exact_match("QB", "tool", self._entities())
        assert result is not None
        assert result.action == EntityResolutionAction.MERGE

    def test_exact_match_different_type(self):
        result = resolve_exact_match("Python", "tool", self._entities())
        assert result is not None
        assert result.action == EntityResolutionAction.SAME_AS
        assert result.confidence == 0.9

    def test_no_match(self):
        result = resolve_exact_match("Terraform", "tool", self._entities())
        assert result is None

    def test_empty_entities_list(self):
        result = resolve_exact_match("anything", "tool", [])
        assert result is None


# ---------------------------------------------------------------------------
# compute_name_similarity
# ---------------------------------------------------------------------------


class TestComputeNameSimilarity:
    def test_identical_names(self):
        assert compute_name_similarity("Python", "Python") == 1.0

    def test_identical_after_normalization(self):
        assert compute_name_similarity("  Python  ", "python") == 1.0

    def test_completely_different(self):
        score = compute_name_similarity("abcdef", "xyz123")
        assert score < 0.3

    def test_similar_names(self):
        score = compute_name_similarity("QuickBooks", "QuickBook")
        assert score > 0.8

    def test_empty_name_returns_zero(self):
        assert compute_name_similarity("", "python") == 0.0
        assert compute_name_similarity("python", "") == 0.0


# ---------------------------------------------------------------------------
# resolve_close_match
# ---------------------------------------------------------------------------


class TestResolveCloseMatch:
    def _entities(self) -> list[dict]:
        return [
            {"name": "QuickBooks Online", "entity_type": "tool"},
            {"name": "PayPal", "entity_type": "service"},
        ]

    def test_close_match_found(self):
        result = resolve_close_match("QuickBooks Onlin", "tool", self._entities(), threshold=0.85)
        assert result is not None
        assert result.action == EntityResolutionAction.SAME_AS

    def test_close_match_not_found(self):
        result = resolve_close_match("Terraform", "tool", self._entities(), threshold=0.9)
        assert result is None

    def test_close_match_different_type(self):
        result = resolve_close_match(
            "QuickBooks Onlin", "service", self._entities(), threshold=0.85
        )
        assert result is not None
        assert result.action == EntityResolutionAction.RELATED_TO

    def test_close_match_empty_entities(self):
        result = resolve_close_match("anything", "tool", [], threshold=0.9)
        assert result is None

    def test_threshold_respected(self):
        # Very high threshold should reject moderate matches
        result = resolve_close_match("QuickBook", "tool", self._entities(), threshold=0.99)
        assert result is None


# ---------------------------------------------------------------------------
# Regression: close match returns SAME_AS not MERGE (Fix 3, ADR-0011)
# ---------------------------------------------------------------------------


class TestCloseMatchReturnsSameAs:
    """ADR-0011: MUST NOT auto-merge at close/related level."""

    def test_close_match_same_type_returns_same_as(self):
        entities = [{"name": "QuickBooks Online", "entity_type": "tool"}]
        result = resolve_close_match("QuickBooks Onlin", "tool", entities, threshold=0.85)
        assert result is not None
        assert result.action == EntityResolutionAction.SAME_AS

    def test_close_match_different_type_returns_related_to(self):
        entities = [{"name": "QuickBooks Online", "entity_type": "tool"}]
        result = resolve_close_match("QuickBooks Onlin", "service", entities, threshold=0.85)
        assert result is not None
        assert result.action == EntityResolutionAction.RELATED_TO


# ---------------------------------------------------------------------------
# Regression: new alias entries (Fix 8)
# ---------------------------------------------------------------------------


class TestAliasResolutionNewEntries:
    def test_alias_usps(self):
        assert resolve_alias("US Postal Service") == "usps"

    def test_alias_fedex(self):
        assert resolve_alias("Federal Express") == "fedex"

    def test_alias_csv(self):
        assert resolve_alias("comma separated values") == "csv"

    def test_alias_csv_hyphenated(self):
        assert resolve_alias("comma-separated values") == "csv"
