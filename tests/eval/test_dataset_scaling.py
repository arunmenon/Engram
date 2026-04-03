"""Tests for dataset scaling: 59/24/3 -> ~226/80/10.

Validates data integrity, regression safety, and functional correctness across
all three dataset modes (original, extended, generated-only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.eval.dataset import (
    DatasetMode,
    load_eval_dataset,
    set_dataset_mode,
)
from tests.eval.harness import EvalResult, ScoringParams, evaluate
from tests.eval.hooks import _infer_node_scenario

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GENERATED_JSON_PATH = Path(__file__).parent / "dataset_generated.json"

ORIGINAL_NODE_COUNT = 59
ORIGINAL_QUERY_COUNT = 24
ORIGINAL_EDGE_COUNT = 106
ORIGINAL_SCENARIO_COUNT = 3

GENERATED_SCENARIO_COUNT = 7
GENERATED_NODE_COUNT = 167
GENERATED_QUERY_COUNT = 56

EXTENDED_NODE_COUNT = 226
EXTENDED_QUERY_COUNT = 80
EXTENDED_SCENARIO_COUNT = 10

ALL_INTENTS = {"why", "when", "what", "related", "general", "who_is", "how_does", "personalize"}

# Baseline score for original dataset with default ScoringParams (regression anchor).
# Computed with evaluate(ScoringParams()) on the original 3-scenario dataset.
ORIGINAL_BASELINE_SCORE = 0.5183117386967678


@pytest.fixture()
def original_dataset() -> dict[str, Any]:
    """Load original 3-scenario dataset."""
    set_dataset_mode(DatasetMode.ORIGINAL)
    return load_eval_dataset()


@pytest.fixture()
def extended_dataset() -> dict[str, Any]:
    """Load extended 10-scenario dataset."""
    set_dataset_mode(DatasetMode.EXTENDED)
    return load_eval_dataset()


@pytest.fixture()
def generated_only_dataset() -> dict[str, Any]:
    """Load generated-only 7-scenario dataset."""
    set_dataset_mode(DatasetMode.GENERATED_ONLY)
    return load_eval_dataset()


@pytest.fixture()
def generated_json() -> dict[str, Any]:
    """Load raw generated JSON artifact."""
    return json.loads(_GENERATED_JSON_PATH.read_text())


# ---------------------------------------------------------------------------
# Data Integrity: Original Dataset
# ---------------------------------------------------------------------------


class TestOriginalDataIntegrity:
    """Verify original dataset is unchanged after scaling work."""

    def test_node_count(self, original_dataset: dict[str, Any]) -> None:
        assert len(original_dataset["all_nodes"]) == ORIGINAL_NODE_COUNT

    def test_query_count(self, original_dataset: dict[str, Any]) -> None:
        assert len(original_dataset["queries"]) == ORIGINAL_QUERY_COUNT

    def test_edge_count(self, original_dataset: dict[str, Any]) -> None:
        assert len(original_dataset["all_edges"]) == ORIGINAL_EDGE_COUNT

    def test_scenario_count(self, original_dataset: dict[str, Any]) -> None:
        assert len(original_dataset["scenarios"]) == ORIGINAL_SCENARIO_COUNT

    def test_scenario_ids(self, original_dataset: dict[str, Any]) -> None:
        ids = {s.scenario_id for s in original_dataset["scenarios"]}
        assert ids == {"pay-decline-001", "fraud-inv-002", "merch-onb-003"}


# ---------------------------------------------------------------------------
# Data Integrity: Generated JSON Artifact
# ---------------------------------------------------------------------------


class TestGeneratedJsonIntegrity:
    """Validate the frozen dataset_generated.json artifact."""

    def test_file_exists(self) -> None:
        assert _GENERATED_JSON_PATH.exists(), "dataset_generated.json missing"

    def test_scenario_count(self, generated_json: dict[str, Any]) -> None:
        assert len(generated_json["scenarios"]) == GENERATED_SCENARIO_COUNT

    def test_scenario_ids(self, generated_json: dict[str, Any]) -> None:
        ids = {s["scenario_id"] for s in generated_json["scenarios"]}
        expected = {
            "refund-disp-004",
            "acct-takeover-005",
            "sub-billing-006",
            "api-ratelimit-007",
            "compliance-kyc-008",
            "lending-uw-009",
            "chargeback-res-010",
        }
        assert ids == expected

    def test_each_scenario_has_8_queries_one_per_intent(
        self,
        generated_json: dict[str, Any],
    ) -> None:
        for scenario in generated_json["scenarios"]:
            intents = sorted(q["intent"] for q in scenario["queries"])
            sid = scenario["scenario_id"]
            assert len(intents) == 8, f"{sid}: expected 8, got {len(intents)}"
            assert intents == sorted(ALL_INTENTS), (
                f"{scenario['scenario_id']}: intent mismatch {intents}"
            )

    def test_every_query_has_min_expected_top_nodes(self, generated_json: dict[str, Any]) -> None:
        for scenario in generated_json["scenarios"]:
            for query in scenario["queries"]:
                assert len(query["expected_top_nodes"]) >= 3, (
                    f"{query['query_id']}: needs >= 3 expected_top_nodes, "
                    f"got {len(query['expected_top_nodes'])}"
                )

    def test_every_query_has_must_not_appear(self, generated_json: dict[str, Any]) -> None:
        for scenario in generated_json["scenarios"]:
            for query in scenario["queries"]:
                assert len(query["must_not_appear"]) >= 1, (
                    f"{query['query_id']}: needs >= 1 must_not_appear"
                )


# ---------------------------------------------------------------------------
# Data Integrity: Extended Dataset (Merged)
# ---------------------------------------------------------------------------


class TestExtendedDataIntegrity:
    """Validate merged extended dataset (original + generated)."""

    def test_node_count(self, extended_dataset: dict[str, Any]) -> None:
        count = len(extended_dataset["all_nodes"])
        assert 200 <= count <= 300, f"Expected 200-300 nodes, got {count}"

    def test_exact_node_count(self, extended_dataset: dict[str, Any]) -> None:
        assert len(extended_dataset["all_nodes"]) == EXTENDED_NODE_COUNT

    def test_query_count(self, extended_dataset: dict[str, Any]) -> None:
        count = len(extended_dataset["queries"])
        assert 70 <= count <= 90, f"Expected 70-90 queries, got {count}"

    def test_exact_query_count(self, extended_dataset: dict[str, Any]) -> None:
        assert len(extended_dataset["queries"]) == EXTENDED_QUERY_COUNT

    def test_scenario_count(self, extended_dataset: dict[str, Any]) -> None:
        assert len(extended_dataset["scenarios"]) == EXTENDED_SCENARIO_COUNT

    def test_no_duplicate_node_ids(self, extended_dataset: dict[str, Any]) -> None:
        node_ids = list(extended_dataset["all_nodes"].keys())
        assert len(node_ids) == len(set(node_ids)), "Duplicate node IDs found"

    def test_all_edges_reference_valid_nodes(self, extended_dataset: dict[str, Any]) -> None:
        valid_ids = set(extended_dataset["all_nodes"].keys())
        bad_edges = [
            e
            for e in extended_dataset["all_edges"]
            if e.source not in valid_ids or e.target not in valid_ids
        ]
        assert not bad_edges, f"{len(bad_edges)} edges reference invalid node IDs"

    def test_all_embeddings_are_8d(self, extended_dataset: dict[str, Any]) -> None:
        bad_nodes = []
        for node_id, node in extended_dataset["all_nodes"].items():
            embedding = node.attributes.get("embedding")
            if embedding is not None and len(embedding) != 8:
                bad_nodes.append((node_id, len(embedding)))
        assert not bad_nodes, f"Non-8D embeddings: {bad_nodes}"

    def test_cross_scenario_edges_exist(self, extended_dataset: dict[str, Any]) -> None:
        cross_edges = extended_dataset["cross_edges"]
        assert len(cross_edges) > 0, "No cross-scenario edges in extended dataset"

    def test_intent_coverage_all_8(self, extended_dataset: dict[str, Any]) -> None:
        intents = {q.intent for q in extended_dataset["queries"]}
        # Normalize IntentType enum values to strings
        intent_strings = set()
        for intent in intents:
            intent_strings.add(intent.value if hasattr(intent, "value") else str(intent))
        assert intent_strings >= ALL_INTENTS, f"Missing intents: {ALL_INTENTS - intent_strings}"


# ---------------------------------------------------------------------------
# Data Integrity: Generated-Only Dataset
# ---------------------------------------------------------------------------


class TestGeneratedOnlyDataIntegrity:
    """Validate generated-only dataset mode."""

    def test_node_count(self, generated_only_dataset: dict[str, Any]) -> None:
        assert len(generated_only_dataset["all_nodes"]) == GENERATED_NODE_COUNT

    def test_query_count(self, generated_only_dataset: dict[str, Any]) -> None:
        assert len(generated_only_dataset["queries"]) == GENERATED_QUERY_COUNT

    def test_scenario_count(self, generated_only_dataset: dict[str, Any]) -> None:
        assert len(generated_only_dataset["scenarios"]) == GENERATED_SCENARIO_COUNT

    def test_no_original_nodes_leak(self, generated_only_dataset: dict[str, Any]) -> None:
        original_prefixes = ("evt-pay-", "ent-pay-", "evt-fr-", "ent-fr-", "evt-mo-", "ent-mo-")
        leaked = [
            nid
            for nid in generated_only_dataset["all_nodes"]
            if any(nid.startswith(p) for p in original_prefixes)
        ]
        assert not leaked, f"Original scenario nodes leaked into generated-only: {leaked}"


# ---------------------------------------------------------------------------
# Regression: Original Baseline Score
# ---------------------------------------------------------------------------


class TestRegression:
    """Ensure original dataset scoring is unchanged by scaling work."""

    def test_baseline_score_unchanged(self) -> None:
        set_dataset_mode(DatasetMode.ORIGINAL)
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

        result = evaluate(ScoringParams())
        assert abs(result.score - ORIGINAL_BASELINE_SCORE) < 1e-10, (
            f"Baseline score changed: {result.score} vs {ORIGINAL_BASELINE_SCORE}"
        )

    def test_baseline_violation_rate_low(self) -> None:
        set_dataset_mode(DatasetMode.ORIGINAL)
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

        result = evaluate(ScoringParams())
        assert result.mean_violation_rate < 0.01, (
            f"Violation rate too high: {result.mean_violation_rate}"
        )

    def test_baseline_ndcg_positive(self) -> None:
        set_dataset_mode(DatasetMode.ORIGINAL)
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

        result = evaluate(ScoringParams())
        assert result.mean_ndcg > 0.0, "nDCG should be positive"


# ---------------------------------------------------------------------------
# Functional: evaluate() on Extended Dataset
# ---------------------------------------------------------------------------


class TestFunctionalExtended:
    """Verify evaluate() runs end-to-end on the extended dataset."""

    def test_evaluate_extended_runs(self) -> None:
        set_dataset_mode(DatasetMode.EXTENDED)
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

        result = evaluate(ScoringParams())
        assert isinstance(result, EvalResult)
        assert result.score > 0.0
        assert result.mean_ndcg > 0.0
        assert result.mean_violation_rate < 0.10  # reasonable bound

    def test_evaluate_extended_has_query_results(self) -> None:
        set_dataset_mode(DatasetMode.EXTENDED)
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

        result = evaluate(ScoringParams())
        assert len(result.query_results) == EXTENDED_QUERY_COUNT

    def test_evaluate_extended_intent_breakdown(self) -> None:
        set_dataset_mode(DatasetMode.EXTENDED)
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

        result = evaluate(ScoringParams())
        # Should have nDCG for all 8 intents
        assert len(result.intent_ndcg) == 8


# ---------------------------------------------------------------------------
# Functional: Hooks on Extended Dataset
# ---------------------------------------------------------------------------


class TestFunctionalHooksExtended:
    """Verify hooks work correctly on extended dataset."""

    def test_evaluate_with_hooks_runs(self) -> None:
        set_dataset_mode(DatasetMode.EXTENDED)
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

        from tests.eval.autoresearch_v2 import apply_structural_hook, evaluate_with_hooks

        edge_boost = apply_structural_hook("edge_boost", {})
        result = evaluate_with_hooks(
            ScoringParams(),
            {"edge_boost": edge_boost},
        )
        assert isinstance(result, EvalResult)
        assert result.score > 0.0

    def test_scenario_focus_hook_runs(self) -> None:
        set_dataset_mode(DatasetMode.EXTENDED)
        import tests.eval.harness as harness_mod

        harness_mod._dataset_cache = None

        from tests.eval.autoresearch_v2 import apply_structural_hook, evaluate_with_hooks

        hook = apply_structural_hook("scenario_focus", {})
        result = evaluate_with_hooks(
            ScoringParams(),
            {"scenario_focus": hook},
        )
        assert isinstance(result, EvalResult)
        assert result.score > 0.0


# ---------------------------------------------------------------------------
# Functional: Scenario Inference
# ---------------------------------------------------------------------------


class TestScenarioInference:
    """Verify _infer_node_scenario covers all 10 scenarios."""

    @pytest.mark.parametrize(
        "node_id,expected_scenario",
        [
            ("evt-pay-001", "pay-decline-001"),
            ("ent-pay-gateway", "pay-decline-001"),
            ("evt-fr-010", "fraud-inv-002"),
            ("ent-fr-analyst", "fraud-inv-002"),
            ("evt-mo-020", "merch-onb-003"),
            ("ent-mo-docs", "merch-onb-003"),
            ("evt-rd-060", "refund-disp-004"),
            ("ent-rd-policy", "refund-disp-004"),
            ("evt-at-100", "acct-takeover-005"),
            ("ent-at-device", "acct-takeover-005"),
            ("evt-sb-140", "sub-billing-006"),
            ("ent-sb-billing", "sub-billing-006"),
            ("evt-ar-180", "api-ratelimit-007"),
            ("ent-ar-endpoint", "api-ratelimit-007"),
            ("evt-ck-210", "compliance-kyc-008"),
            ("ent-ck-docs", "compliance-kyc-008"),
            ("evt-lu-250", "lending-uw-009"),
            ("ent-lu-credit", "lending-uw-009"),
            ("evt-cr-290", "chargeback-res-010"),
            ("ent-cr-evidence", "chargeback-res-010"),
        ],
    )
    def test_infer_scenario(self, node_id: str, expected_scenario: str) -> None:
        result = _infer_node_scenario(node_id)
        assert result == expected_scenario, (
            f"_infer_node_scenario({node_id!r}) = {result!r}, expected {expected_scenario!r}"
        )

    def test_unknown_prefix_returns_none(self) -> None:
        assert _infer_node_scenario("unknown-node-xyz") is None

    @pytest.mark.parametrize(
        "node_id,expected_scenario",
        [
            ("user-profile-at-victim", "acct-takeover-005"),
            ("pref-at-security", "acct-takeover-005"),
            ("skill-at-monitoring", "acct-takeover-005"),
            ("user-profile-ck-officer", "compliance-kyc-008"),
            ("pref-ck-compliance", "compliance-kyc-008"),
            ("skill-ck-aml", "compliance-kyc-008"),
            ("user-profile-lu-underwriter", "lending-uw-009"),
            ("pref-lu-risk", "lending-uw-009"),
            ("skill-lu-credit", "lending-uw-009"),
        ],
    )
    def test_infer_generated_profile_nodes(self, node_id: str, expected_scenario: str) -> None:
        """Generated scenarios with user-profile/pref/skill prefixes must resolve correctly.

        This catches the prefix ordering bug where generic 'user-profile-' (fraud)
        shadows more specific 'user-profile-lu-' (lending) etc.
        """
        result = _infer_node_scenario(node_id)
        assert result == expected_scenario, (
            f"_infer_node_scenario({node_id!r}) = {result!r}, expected {expected_scenario!r}. "
            f"Likely prefix ordering bug: generic 'user-profile-' matches before "
            f"more specific prefix."
        )
