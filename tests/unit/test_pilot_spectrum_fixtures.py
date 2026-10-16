"""Independent fixture integrity before any pilot cloud writes."""

import json

from engram_pilot_spectrum import freeze

from context_graph.api.routes.artifacts import ArtifactQueryRequest
from context_graph.domain.models import Event


def artifacts(plan):
    result = set()
    for group in plan["groups"]:
        for step in group["steps"]:
            if step["expected_status"] >= 400:
                continue
            result.update(step.get("extra_nodes", {}))
            if step.get("expected_node"):
                result.add(step["expected_node"])
            for _, source, target in step.get("expected_edges", []):
                result.update((source, target))
    return result


def test_retained_runs_have_distinct_declared_artifact_identities():
    a, b = freeze("fixture-pilot-a"), freeze("fixture-pilot-b")
    assert not artifacts(a) & artifacts(b)


def test_frozen_oracles_include_required_inputs_and_intermediate_queries():
    plan = freeze("fixture-pilot-check")
    for group in plan["groups"]:
        scenarios = {s["scenario"] for s in group["steps"]}
        for step in group["steps"]:
            Event.model_validate_json(json.dumps(step["request"]))
        for query in group.get("queries", []):
            ArtifactQueryRequest.model_validate(
                dict(
                    query=query["text"],
                    intent=query["intent"],
                    seed_node_ids=query.get("seeds")
                    or ([query["seed"]] if query.get("seed") else []),
                    max_nodes=100,
                    max_depth=query["max_depth"],
                )
            )
            if query.get("after_scenario"):
                assert query["after_scenario"] in scenarios
    catalog = next(g for g in plan["groups"] if g["name"] == "catalog")
    normalized = [s for s in catalog["steps"] if s.get("webhook")]
    assert len(normalized) == 4
    assert all(s["expected_status"] == 201 for s in normalized)
    required = next(
        q["required"] for q in catalog["queries"] if q["scenario"] == "CQ1-exact-outcomes"
    )
    assert {s["expected_node"] for s in normalized} <= set(required)


def test_global_discovery_oracle_is_frozen_and_does_not_whitelist_answers():
    from engram_pilot_spectrum import discovery_eligibility

    state = {
        "nodes": [
            ["Requirement", "old", {"statement": "Expires in fifteen minutes"}],
            ["DesignElement", "linked", {"title": "Token storage"}],
            ["Requirement", "unrelated", {"statement": "Newsletter signup"}],
            ["Decision", "proposal", {"statement": "Other topic", "method": "extracted"}],
        ],
        "edges": [
            ["DesignElement", "linked", "REFINES", "Requirement", "old", {"method": "declared"}],
            ["Decision", "proposal", "APPLIES_TO", "Requirement", "old", {"method": "inferred"}],
        ],
    }
    matching, eligible = discovery_eligibility(
        state,
        {"matching_terms": ["fifteen", "minute"], "allowed_edges": ["REFINES", "APPLIES_TO"]},
        6,
    )
    assert matching == {"old"}
    assert eligible == {"old", "linked"}


def test_summary_contrast_oracle_rejects_negations_and_opposite_outcomes():
    from engram_pilot_spectrum import summary_contrast_matches

    assert summary_contrast_matches("Investigation completed; rollout uncertain.", "forward")
    assert summary_contrast_matches("Investigation incomplete; rollout completed.", "inverse")
    for wrong in (
        "Investigation incomplete; rollout uncertain.",
        "Investigation not completed; rollout uncertain.",
        "Investigation completed; rollout completed.",
        "Investigation completed; rollout not uncertain.",
        "Investigation pending; rollout completed.",
    ):
        assert not summary_contrast_matches(wrong, "forward")
    assert not summary_contrast_matches(
        "Investigation incomplete; rollout not completed.", "inverse"
    )
    assert not summary_contrast_matches("Investigation completed; rollout incomplete.", "inverse")


def test_summary_inverse_rejects_negated_and_conflicting_incompleteness():
    from engram_pilot_spectrum import summary_contrast_matches

    assert not summary_contrast_matches(
        "Investigation not incomplete; rollout completed.", "inverse"
    )
    assert not summary_contrast_matches(
        "Investigation completed. Investigation incomplete; rollout completed.", "inverse"
    )
