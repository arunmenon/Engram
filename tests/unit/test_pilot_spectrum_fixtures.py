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
