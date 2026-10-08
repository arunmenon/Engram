"""Nested catalog rejection probes reach the field named in their independent oracle."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from context_graph.ontology import load_registry

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from engram_goal07_catalog_fixtures import fixtures  # noqa: E402

EXPECTED_BRANCHES = {
    "change.created": {"work_items": ("tracker", "external_key")},
    "change.updated": {"work_items": ("tracker", "external_key")},
    "release.published": {"entries": ("pr_number", "section")},
    "testcaserun.finished": {"requirements": ("spec_id", "spec_version", "local_id")},
    "incident.lesson_recorded": {
        "change": ("repo", "number"),
        "incident": ("repo", "service", "incident_id"),
    },
    "incident.remediation_recorded": {
        "change": ("repo", "number"),
        "incident": ("repo", "service", "incident_id"),
    },
    "ticket.created": {
        "requirements": ("spec_id", "spec_version", "local_id"),
        "designs": ("doc_id", "section_path", "version"),
    },
    "ticket.updated": {
        "requirements": ("spec_id", "spec_version", "local_id"),
        "designs": ("doc_id", "section_path", "version"),
    },
    "spec.approved": {"lesson_refs": ("content_hash",)},
    "design.section_changed": {
        "requirements": ("spec_id", "spec_version", "local_id"),
        "refines_designs": ("doc_id", "section_path", "version"),
    },
}


def test_all_frozen_required_nested_fields_have_probes_with_valid_populated_parents():
    data = fixtures("nested-proof")
    assert data["unpopulated_nested_branches"] == []
    registry = load_registry(["pdlc"])
    nested = [s for s in data["steps"] if "expected_validation_location" in s]
    expected = {
        ("pdlc." + kind, branch, field)
        for kind, branches in EXPECTED_BRANCHES.items()
        for branch, fields in branches.items()
        for field in fields
    }
    actual = {
        (
            s["request"]["event_type"],
            s["expected_validation_location"][0],
            s["expected_validation_location"][-1],
        )
        for s in nested
    }
    assert actual == expected
    for step in nested:
        contract = registry.event_types[step["request"]["event_type"]].definition.payload_contract
        baseline = data["nested_validation_baselines"][step["validation_baseline"]]
        contract.validate_payload(baseline)
        location = tuple(step["expected_validation_location"])
        parent = baseline[location[0]]
        assert parent  # optional reference branches are populated before mutation
        variants = {
            s["validation_variant"]
            for s in nested
            if s["request"]["event_type"] == step["request"]["event_type"]
            and s["expected_validation_location"] == list(location)
        }
        assert {"missing", "null", "wrong-type"} <= variants
        with pytest.raises(ValidationError) as caught:
            contract.validate_payload(step["request"]["payload"])
        assert {error["loc"] for error in caught.value.errors()} == {location}


def test_nested_enum_and_nonempty_fields_include_specific_invalid_variants():
    steps = fixtures("nested-variants")["steps"]
    assert any(
        s.get("validation_variant") == "invalid-enum"
        and s.get("expected_validation_location") == ["entries", 0, "section"]
        for s in steps
    )
    assert any(
        s.get("validation_variant") == "empty"
        and s.get("expected_validation_location") == ["lesson_refs", 0, "content_hash"]
        for s in steps
    )
