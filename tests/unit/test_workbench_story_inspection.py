"""Coverage and failure explanations retain reviewed oracles and distinguish weak evidence."""

import copy
import json
from pathlib import Path

import httpx
import pytest

from context_graph.workbench.api import create_app
from context_graph.workbench.draft_stories import draft_story
from context_graph.workbench.engine import digest, engine_revision
from context_graph.workbench.explain import verify_answer
from context_graph.workbench.journey_authoring import JourneyProposalError, validate_variant
from context_graph.workbench.journeys import JourneyCheck
from context_graph.workbench.models import Content
from context_graph.workbench.store import Store
from context_graph.workbench.story_inspection import (
    check_guidance,
    failure_context,
    inspect_story,
    result_stale,
)

FIXTURE = Path(__file__).parents[1] / "fixtures/workbench/incident.json"


def scenario():
    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    story, snapshot = draft_story(content, fixture["proposal"]["pack"])
    story.expectations_reviewed = True
    record = {
        "content": content.model_dump(),
        "journey": story.model_dump(),
        "journey_pack_snapshot": snapshot,
    }
    return record


def result(record, status="passed"):
    story = record["journey"]
    return {
        "journey_digest": digest(story),
        "pack_digest": story["pack_digest"],
        "engine_revision": engine_revision(),
        "steps": [],
        "checks": [
            {
                "check_id": c["id"],
                "status": status,
                "expected": c["expected"],
                "actual": {"semantic_outcome": "created"},
            }
            for c in story["checks"]
        ],
    }


def test_handling_is_not_transition_coverage_and_stale_is_not_passing():
    record = scenario()
    before = copy.deepcopy(record)
    report = inspect_story(record)
    assert any(row["status"] == "defined" for row in report["rows"])
    assert any(
        row["kind"] == "transition state assertion" and row["status"] == "no_check"
        for row in report["rows"]
    )
    assert record == before
    record["journey_result"] = result(record)
    assert any(row["status"] == "passing" for row in inspect_story(record)["rows"])
    record["journey"]["title"] += " revised"
    assert result_stale(record)
    assert not any(row["status"] == "passing" for row in inspect_story(record)["rows"])
    record = scenario()
    record["journey_result"] = result(record)
    record["journey_pack_snapshot"]["primary_pack"] = "changed"
    assert result_stale(record)
    assert inspect_story(record)["pack_issue"]


def test_missing_endpoint_and_empty_assertion_never_count_as_passing_proof():
    record = scenario()
    record["journey"]["checks"] += [
        {
            "id": "absent",
            "description": "No link",
            "source": "review",
            "kind": "edge_absent",
            "after_step": None,
            "expected": {
                "source": "Incident:missing",
                "target": "Service:missing",
                "type": "AFFECTS",
            },
        },
        {
            "id": "empty",
            "description": "Fields",
            "source": "review",
            "kind": "properties",
            "after_step": None,
            "expected": {"node": "Incident:missing", "properties": {}},
        },
    ]
    record["journey_result"] = result(record)
    checks = inspect_story(record)["checks"][-2:]
    assert all(c["status"] == "needs_review" and c["warnings"] for c in checks)


def test_different_failures_give_different_guidance_without_oracle_repair():
    categories = []
    for kind, status in [
        ("evaluation", "failed"),
        ("supplemental", "unsupported"),
        ("properties", "failed"),
        ("disposition", "failed"),
    ]:
        guide = check_guidance({"kind": kind}, {"status": status}, False)
        categories.append(guide["category"])
        assert "No reviewed domain specification" in guide["action"]
        assert "Never change" in guide["boundary"]
    assert len(set(categories)) == 4


def test_failure_context_pins_event_rule_expectation_and_observation():
    record = scenario()
    record["journey_result"] = result(record, "failed")
    before = copy.deepcopy(record)
    context = failure_context(record, 0, "Which input should I inspect?")
    assert {"event", "rules", "observed", "subject", "guidance"} <= {
        e["id"] for e in context["evidence"]
    }
    assert record == before
    with pytest.raises(ValueError, match="no expectation repair"):
        verify_answer(
            {
                "kind": "supported",
                "claims": [{"text": "Check the event", "evidence": ["event"]}],
                "instruction": "Change the expected answer",
                "instruction_evidence": ["subject"],
            },
            context,
        )


@pytest.mark.asyncio
async def test_failed_check_api_consent_owner_staleness_and_no_mutation(tmp_path):
    record = scenario()
    record["journey_result"] = result(record, "failed")
    store = Store(tmp_path / "store")
    draft = store.create("a", record["content"])
    draft.update({k: v for k, v in record.items() if k != "content"})
    draft = store.put("a", draft, 1, "fixture")
    calls = []

    async def explain(context):
        calls.append(context)
        return {
            "kind": "supported",
            "claims": [{"text": "Inspect the input before deciding.", "evidence": ["guidance"]}],
        }

    app = create_app(database=store.path, operators={"a": "a", "b": "b"}, explainer=explain)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        path = f"/admin/tenants/{draft['id']}/explain"
        body = {"revision": draft["revision"], "scope": "failed_check", "index": 0}
        assert (
            await client.post(path, json=body, headers={"Authorization": "Bearer b"})
        ).status_code == 404
        response = await client.post(path, json=body, headers={"Authorization": "Bearer a"})
        assert response.status_code == 200, response.text
        assert store.get("a", draft["id"]) == draft
        changed = copy.deepcopy(draft)
        changed["content"]["data_policy"] = "local_only"
        changed = store.put("a", changed, draft["revision"], "withdraw consent")
        body["revision"] = changed["revision"]
        assert (
            await client.post(path, json=body, headers={"Authorization": "Bearer a"})
        ).status_code == 403
        assert len(calls) == 1


@pytest.mark.parametrize(
    "kind,expected,message",
    [
        ("properties", {"node": "Incident:us|42", "properties": {}}, "at least one field"),
        (
            "edge_absent",
            {"source": "Service:checkout", "target": "Incident:us|42", "type": "AFFECTS"},
            "impossible endpoint",
        ),
    ],
)
def test_new_story_rejects_vacuous_and_impossible_assertions(kind, expected, message):
    from context_graph.workbench.journeys import Journey

    record = scenario()
    baseline = Journey.model_validate(record["journey"])
    variant = baseline.model_copy(deep=True)
    variant.checks.append(
        JourneyCheck(
            id="bad",
            description="Negative example",
            source="operator-specification",
            kind=kind,
            expected=expected,
        )
    )
    with pytest.raises(JourneyProposalError, match=message):
        validate_variant(variant, baseline, pack_snapshot=record["journey_pack_snapshot"])


@pytest.mark.asyncio
async def test_bad_projection_explanation_has_real_event_rule_and_wrong_field_evidence():
    from context_graph.workbench.journey_runner import run_journey

    fixture = json.loads(FIXTURE.read_text())
    # Deliberately broken synthetic copy; preserve the specification and original fixture.
    pack = copy.deepcopy(fixture["proposal"]["pack"])
    pack["projection"][0]["upsert"][0]["set"]["title"] = "$.id"
    story, snapshot = draft_story(Content.model_validate(fixture["content"]), pack)
    story.checks.append(
        JourneyCheck(
            id="title",
            description="Preserve the event title",
            source="operator-specification",
            kind="properties",
            after_step=0,
            expected={
                "node": "Incident:payments|INC-1042",
                "properties": {"title": "Payments outage"},
            },
        )
    )
    story.expectations_reviewed = True
    record = {
        "content": fixture["content"],
        "journey": story.model_dump(),
        "journey_pack_snapshot": snapshot,
        "journey_result": await run_journey(story, pack_snapshot=snapshot),
    }
    context = failure_context(record, len(story.checks) - 1, "Why is the title missing?")
    evidence = {item["id"]: item["text"] for item in context["evidence"]}
    assert "Payments outage" in evidence["event"]
    assert json.loads(evidence["rules"])[0]["upsert"][0]["set"]["title"] == "$.id"
    assert json.loads(evidence["observed"])["status"] == "failed"
    assert "graph or mapping" in evidence["guidance"]


def test_final_question_context_includes_explicit_retrieval_rule_without_inventing_an_event():
    record = scenario()
    record["journey"]["checks"] = [
        {
            "id": "question",
            "description": "Account answer",
            "kind": "retrieval",
            "after_step": None,
            "expected": {"intent": "incident_status", "text": "What happened?"},
        }
    ]
    record["journey_result"] = result(record, "failed")
    evidence = {
        item["id"]: json.loads(item["text"])
        for item in failure_context(record, 0, "Why?")["evidence"]
    }
    assert evidence["rules"][0]["intent"] == "incident_status"
    assert evidence["event"]["scope"].startswith("Final graph")


@pytest.mark.asyncio
async def test_vacuous_matrix_retains_runner_results_but_flags_weak_proof():
    from context_graph.workbench.journey_runner import run_journey
    from context_graph.workbench.journeys import Journey

    record = scenario()
    node = "Incident:payments|INC-1042"
    cases = [
        ("node_absent", {"node": "Incident:nobody|NONE"}),
        ("properties", {"node": node, "properties": {"node_type": "Incident"}}),
        ("properties", {"node": node, "properties": {"id": "INC-1042"}}),
        ("property_absent", {"node": node, "property": "no_such_field"}),
        (
            "retrieval",
            {
                "intent": "incident_status",
                "text": "What happened?",
                "forbidden": ["Incident:nobody|NONE"],
                "required": [],
                "seed": None,
            },
        ),
        (
            "evaluation",
            {
                "min_f1": 0,
                "question": {
                    "id": "wrong",
                    "query": "What happened?",
                    "intent": "incident_status",
                    "expected": ["Incident:nobody|NONE"],
                },
            },
        ),
    ]
    story = Journey.model_validate(record["journey"])
    baseline = story.model_copy(deep=True)
    for index, (kind, expected) in enumerate(cases):
        story.checks.append(
            JourneyCheck(
                id=f"weak-{index}",
                description="Probe",
                source="operator-specification",
                kind=kind,
                expected=expected,
            )
        )
    story.checks.append(
        JourneyCheck(
            id="meaningful",
            description="Title",
            source="operator-specification",
            kind="properties",
            expected={"node": node, "properties": {"title": "Payments outage"}},
        )
    )
    validate_variant(story, baseline, pack_snapshot=record["journey_pack_snapshot"])
    story.expectations_reviewed = True
    record["journey"] = story.model_dump()
    record["journey_result"] = await run_journey(
        story, pack_snapshot=record["journey_pack_snapshot"]
    )
    before = copy.deepcopy(record)
    details = {c["id"]: c for c in inspect_story(record)["checks"]}
    for index in range(len(cases)):
        check = details[f"weak-{index}"]
        assert check["outcome"] == "passed"
        assert check["status"] == "needs_review" and check["warnings"]
    assert details["meaningful"]["status"] == "passing"
    assert record == before


def test_pending_brief_is_never_evidence_for_existing_story():
    record = scenario()
    record["journey_result"] = result(record, "failed")
    before = failure_context(record, 0, "Why?")
    record["journey_brief"] = {"specification": "Unreviewed follow-up rule"}
    record["journey_outline"] = {"title": "Pending outline"}
    assert failure_context(record, 0, "Why?") == before
    assert (
        "No reviewed domain specification"
        in inspect_story(record)["checks"][0]["guidance"]["action"]
    )
    record["journey_origin"] = {
        "reviewer": "operator",
        "brief": {"specification": "Accepted story rule"},
    }
    evidence = {e["id"]: e["text"] for e in failure_context(record, 0, "Why?")["evidence"]}
    assert json.loads(evidence["specification"]) == "Accepted story rule"
    assert "Unreviewed" not in json.dumps(evidence)


def test_failure_comparisons_are_plain_values_not_json():
    from context_graph.workbench.story_inspection import check_differences

    lines = check_differences(
        {"kind": "properties", "expected": {"properties": {"title": "Expected title"}}},
        {"status": "failed", "actual": {"properties": {"title": "Recorded title"}}},
    )
    assert lines == ["Expected title: Expected title. Recorded: Recorded title."]
    lines = check_differences(
        {"kind": "evaluation", "expected": {}},
        {
            "status": "failed",
            "actual": {
                "questions": [{"expected": ["Incident:east|42"], "found": ["Incident:west|42"]}]
            },
        },
    )
    assert lines == ["Expected answers: Incident · east / 42. Found: Incident · west / 42."]
