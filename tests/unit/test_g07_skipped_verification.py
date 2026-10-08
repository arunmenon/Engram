"""G07-C skipped runs at payload admission, translation and public planning seams."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import load_registry
from context_graph.sources import github

REGISTRY = load_registry(["pdlc"])
AT = datetime(2026, 10, 8, 10, tzinfo=UTC)
EVENT_ID = UUID("07000000-0000-0000-0000-000000000001")
PAYLOAD = {
    "repo": "g07/auth",
    "test_id": "reset-tests",
    "run_id": "skip-01",
    "outcome": "skipped",
    "name": "Reset tests",
    "path": "tests/reset.py",
    "commit_sha": "abc123",
    "change_number": 56,
}


def plan(payload, event_type="pdlc.testcaserun.skipped"):
    REGISTRY.event_types[event_type].definition.payload_contract.validate_payload(payload)
    event = Event(
        event_id=EVENT_ID,
        event_type=event_type,
        occurred_at=AT,
        session_id="g07-c",
        agent_id="webhook:github",
        trace_id="g07-c",
        payload_ref="synthetic:g07-c",
        global_position="1-0",
    )
    return PackProjector(REGISTRY, frozenset({"webhook:github"})).plan(event, {"payload": payload})


def test_skipped_run_preserves_outcome_commit_and_exact_evidence():
    result = plan(PAYLOAD)
    observed = {n.ref.key: n.properties for n in result.nodes if "source_trust" in n.properties}
    assert set(observed) == {"TestCase:g07/auth|reset-tests", "TestRun:skip-01"}
    assert observed["TestRun:skip-01"]["outcome"] == "skipped"
    assert observed["TestRun:skip-01"]["commit_sha"] == "abc123"
    assert observed["TestRun:skip-01"]["finished_at"] == AT.isoformat()
    assert observed["TestCase:g07/auth|reset-tests"]["path"] == "tests/reset.py"
    edges = {(e.edge_type, e.source.key, e.target.key) for e in result.edges}
    assert edges == {
        ("EXECUTES", "TestRun:skip-01", "TestCase:g07/auth|reset-tests"),
        ("RAN_AGAINST", "TestRun:skip-01", "Change:g07/auth|56"),
        ("DERIVED_FROM", "TestRun:skip-01", str(EVENT_ID)),
        ("DERIVED_FROM", "TestCase:g07/auth|reset-tests", str(EVENT_ID)),
    }
    ran = next(e for e in result.edges if e.edge_type == "RAN_AGAINST")
    assert ran.properties["commit_sha"] == "abc123"
    assert result.rejected == []


def test_skipped_event_rejects_finished_outcomes():
    for outcome in ("success", "failure", "cancel", "error"):
        with pytest.raises(ValidationError):
            plan({**PAYLOAD, "outcome": outcome})


@pytest.mark.parametrize("reference", [{}, {"change_number": None, "commit_sha": None}])
def test_missing_change_reference_keeps_run_without_ran_against(reference):
    payload = {k: v for k, v in PAYLOAD.items() if k not in {"change_number", "commit_sha"}}
    result = plan({**payload, **reference})
    assert {n.ref.key for n in result.nodes} == {"TestCase:g07/auth|reset-tests", "TestRun:skip-01"}
    assert {e.edge_type for e in result.edges} == {"EXECUTES", "DERIVED_FROM"}


@pytest.mark.parametrize("field", ["repo", "test_id", "run_id"])
@pytest.mark.parametrize("bad", [None, "", [], 56])
def test_malformed_identity_rejects_at_payload_admission(field, bad):
    with pytest.raises(ValidationError):
        plan({**PAYLOAD, field: bad})


@pytest.mark.parametrize("conclusion,run_id", [("skipped", 5601), ("neutral", 5602)])
def test_github_skipped_and_neutral_translate_to_skipped_plans(conclusion, run_id):
    (translated,) = github.translate(
        "check_run",
        {
            "action": "completed",
            "repository": {"full_name": "g07/auth"},
            "check_run": {
                "id": run_id,
                "name": "reset-tests",
                "conclusion": conclusion,
                "head_sha": "abc123",
                "completed_at": "2026-10-08T10:00:00Z",
                "pull_requests": [{"number": 56}],
            },
        },
    )
    assert translated.event_type == "pdlc.testcaserun.skipped"
    assert translated.payload == {
        "repo": "g07/auth",
        "test_id": "reset-tests",
        "name": "reset-tests",
        "path": None,
        "run_id": str(run_id),
        "outcome": "skipped",
        "commit_sha": "abc123",
        "change_number": 56,
    }
    result = plan(translated.payload, translated.event_type)
    runs = [n for n in result.nodes if n.ref.label == "TestRun" and "outcome" in n.properties]
    assert len(runs) == 1
    assert runs[0].ref.key == f"TestRun:{run_id}"
    assert runs[0].properties["outcome"] == "skipped"
    assert {e.edge_type for e in result.edges} == {"EXECUTES", "RAN_AGAINST", "DERIVED_FROM"}


@pytest.mark.parametrize("outcome", ["success", "failure", "cancel", "error"])
def test_finished_outcomes_remain_independent_with_exact_run_identity(outcome):
    result = plan(
        {**PAYLOAD, "run_id": "finished-" + outcome, "outcome": outcome},
        "pdlc.testcaserun.finished",
    )
    runs = [n for n in result.nodes if n.ref.label == "TestRun" and "outcome" in n.properties]
    assert len(runs) == 1
    assert runs[0].ref.key == "TestRun:finished-" + outcome
    assert runs[0].properties["outcome"] == outcome


def test_unknown_requirement_fields_do_not_fabricate_verifies():
    result = plan(
        {**PAYLOAD, "requirements": [{"spec_id": "auth", "spec_version": "1", "local_id": "reset"}]}
    )
    assert all(e.edge_type != "VERIFIES" for e in result.edges)
    assert all(n.ref.label != "Requirement" for n in result.nodes)
