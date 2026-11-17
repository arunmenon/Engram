"""Non-PDLC authoring uses a pinned selected pack, never live pack lookup."""

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

from context_graph.workbench.api import create_app
from context_graph.workbench.draft_stories import draft_story, snapshot_registry
from context_graph.workbench.journey_authoring import JourneyOutline, validate_variant
from context_graph.workbench.journey_runner import run_journey
from context_graph.workbench.journeys import JourneyCheck
from context_graph.workbench.models import Content, Proposal
from context_graph.workbench.sandbox import evaluation_artifact

FIXTURE = Path(__file__).parents[1] / "fixtures/workbench/incident.json"


def with_question(baseline, content, snapshot):
    variant = baseline.model_copy(deep=True)
    question = evaluation_artifact(content, snapshot["primary_pack"])["questions"][0]
    variant.checks.append(
        JourneyCheck(
            id="answer",
            description="Reviewed incident answer",
            source="operator-specification",
            kind="evaluation",
            expected={"question": question, "min_f1": 1.0},
        )
    )
    return variant


def test_draft_story_snapshot_pins_dependencies_and_rejects_tampering():
    fixture = json.loads(FIXTURE.read_text())
    story, snapshot = draft_story(
        Content.model_validate(fixture["content"]), fixture["proposal"]["pack"]
    )
    registry = snapshot_registry(snapshot, story.pack_digest)
    assert {p.name for p in registry.packs} == {"core", snapshot["primary_pack"]}
    assert "pdlc" not in {p.name for p in registry.packs}
    changed = copy.deepcopy(snapshot)
    changed["primary_pack"] = "pdlc"
    with pytest.raises(ValueError, match="pinned digest"):
        snapshot_registry(changed, story.pack_digest)


@pytest.mark.asyncio
async def test_non_pdlc_story_runs_questions_and_checks_its_own_domain():
    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    baseline, snapshot = draft_story(content, fixture["proposal"]["pack"])
    variant = with_question(baseline, content, snapshot)
    validate_variant(variant, baseline, pack_snapshot=snapshot)
    with pytest.raises(ValueError, match="Review expected"):
        await run_journey(variant, pack_snapshot=snapshot)
    variant.expectations_reviewed = True
    result = await run_journey(variant, pack_snapshot=snapshot)
    assert result["passed"], result
    variant.checks.append(
        JourneyCheck(
            id="empty",
            description="Wrongly expect an empty domain",
            source="operator-specification",
            kind="graph_exact",
            expected={"nodes": {}, "edges": [], "evidence": {}},
        )
    )
    result = await run_journey(variant, pack_snapshot=snapshot)
    exact = next(check for check in result["checks"] if check["check_id"] == "empty")
    assert exact["status"] == "failed"
    assert exact["actual"]["unexpected_nodes"]


@pytest.mark.asyncio
async def test_draft_to_assistant_story_review_and_run_preserves_parent(tmp_path, monkeypatch):
    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    calls = []

    async def author(_):
        return Proposal.model_validate(fixture["proposal"])

    async def propose(model, baseline, brief, outline=None, decisions="", *, pack_snapshot=None):
        calls.append(pack_snapshot)
        assert pack_snapshot and pack_snapshot["primary_pack"] != "pdlc"
        if outline is None:
            return JourneyOutline(
                title="Incident lifecycle",
                story="Open then resolve",
                steps=["Open", "Resolve", "Reject missing identity"],
                sources=["selected-pack"],
            )
        return with_question(baseline, content, pack_snapshot)

    monkeypatch.setattr("context_graph.workbench.api.propose_journey", propose)
    app = create_app(
        database=tmp_path / "draft.db",
        operators={"a": "alice"},
        author=author,
        model_label="fixture-model",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:

        async def finish(root):
            for _ in range(200):
                record = (await client.get(root)).json()
                if record["job"]["status"] != "running":
                    assert record["job"]["status"] == "completed", record["job"]
                    return record
                await asyncio.sleep(0.01)
            pytest.fail("Job did not finish")

        parent = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{parent['id']}"
        assert (
            await client.post(root + "/story-workspace", json={"revision": parent["revision"]})
        ).status_code == 409
        await client.post(root + "/author", json={"revision": parent["revision"]})
        parent = await finish(root)
        parent = (
            await client.post(
                root + "/review",
                json={
                    "revision": parent["revision"],
                    "accepted_facts": ["incident"],
                    "pack_accepted": True,
                },
            )
        ).json()
        r = await client.post(root + "/story-workspace", json={"revision": parent["revision"]})
        assert r.status_code == 201, r.text
        draft = r.json()
        child = f"/admin/tenants/{draft['id']}"
        assert (
            await client.post(child + "/journey-run", json={"revision": draft["revision"]})
        ).status_code == 409
        brief = {
            "revision": draft["revision"],
            "goal": "Test the incident lifecycle",
            "specification": "Only an open incident may resolve; missing account must be rejected.",
        }
        assert (await client.post(child + "/journey-outline", json=brief)).status_code == 409
        await client.post(child + "/journey-outline", json={**brief, "provider_allowed": True})
        draft = await finish(child)
        await client.post(
            child + "/journey-generate",
            json={
                "revision": draft["revision"],
                "decisions": "Use the supplied account-scoped identities.",
                "outline_reviewed": True,
            },
        )
        draft = await finish(child)
        assert (
            await client.post(child + "/journey-accept", json={"revision": draft["revision"]})
        ).status_code == 409
        assert (
            await client.post(
                child + "/journey-accept",
                json={"revision": draft["revision"], "accepted_checks": ["unknown"]},
            )
        ).status_code == 409
        accepted = await client.post(
            child + "/journey-accept",
            json={
                "revision": draft["revision"],
                "accepted_checks": [c["id"] for c in draft["journey_proposal"]["checks"]],
            },
        )
        assert accepted.status_code == 201, accepted.text
        saved = accepted.json()
        saved_root = f"/admin/tenants/{saved['id']}"
        await client.post(saved_root + "/journey-run", json={"revision": saved["revision"]})
        ran = await finish(saved_root)
        assert ran["journey_result"]["passed"]
        assert (await client.get(root)).json()["revision"] == parent["revision"]
        assert len(calls) == 2


@pytest.mark.asyncio
async def test_author_receives_selected_bundle_without_pdlc_examples(monkeypatch):
    from types import SimpleNamespace

    from context_graph.workbench.journey_authoring import propose_journey

    fixture = json.loads(FIXTURE.read_text())
    baseline, snapshot = draft_story(
        Content.model_validate(fixture["content"]), fixture["proposal"]["pack"]
    )
    captured = []

    async def completion(**kwargs):
        payload = json.loads(kwargs["messages"][1]["content"])
        captured.append(payload)
        assert payload["pack"] == snapshot
        assert (
            payload["check_expected_schemas"]["node_present"]["properties"]["node"]["type"]
            == "string"
        )
        assert (
            payload["node_id_examples"]["Incident"]["node_id"]
            == "Incident:example_account|example_id"
        )
        assert "query" in payload["evaluation_question_schema"]["properties"]
        assert "seed_mode" in payload["retrieval_query_options_schema"]["properties"]
        assert "event_id" in payload["event_request_schema"]["properties"]
        assert "payload" in payload["event_request_schema"]["required"]
        assert "zero-based event index" in kwargs["messages"][0]["content"]
        assert "evaluation_example" not in payload
        assert "retrieval_example" not in payload
        outline = JourneyOutline(
            title="Incident resolution",
            story="An account-scoped incident opens and resolves.",
            steps=["Open an incident", "Resolve it"],
            sources=["selected-pack"],
        )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=outline.model_dump_json()))]
        )

    monkeypatch.setattr("litellm.acompletion", completion)
    result = await propose_journey(
        "fixture-model", baseline, {"goal": "Resolve an incident"}, pack_snapshot=snapshot
    )
    assert result.sources == ["selected-pack"]
    assert len(captured) == 1


def test_authored_domain_does_not_inherit_pdlc_no_user_nodes_assertion():
    from context_graph.workbench.journey_runner import graph_differences

    snapshot = {
        "nodes": [{"id": "UserProfile:a", "type": "UserProfile", "properties": {}}],
        "edges": [],
    }
    expected = {"nodes": {}, "edges": [], "evidence": {}}
    assert graph_differences(expected, snapshot)["unexpected_user_nodes"]
    assert not graph_differences(expected, snapshot, {"Incident"}, {"AFFECTS"})[
        "unexpected_user_nodes"
    ]


def test_contract_feedback_has_field_and_zero_based_checkpoint_without_payload_values():
    from context_graph.workbench.job_errors import job_failure_reason
    from context_graph.workbench.journey_authoring import JourneyProposalError

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    baseline, snapshot = draft_story(content, fixture["proposal"]["pack"])
    variant = with_question(baseline, content, snapshot)
    variant.events[0].request["payload"].pop("account")
    variant.events[0].request["payload"]["title"] = "secret-canary-never-in-feedback"
    with pytest.raises(JourneyProposalError) as error:
        validate_variant(variant, baseline, pack_snapshot=snapshot)
    assert "after_step=0" in str(error.value)
    assert "account" in str(error.value)
    assert "missing" in str(error.value)
    assert "secret-canary" not in str(error.value)
    reason = job_failure_reason(error.value)
    assert "zero-based checkpoint" in reason
    assert "secret-canary" not in reason


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("node_present", {"node": {"type": "Incident", "key": {"account": "us", "id": "1"}}}),
        (
            "retrieval",
            {
                "seed": {"seed_node_ids": ["Service:us|checkout"]},
                "intent": "status",
                "required": [],
                "forbidden": [],
            },
        ),
        (
            "retrieval",
            {
                "seed": "Service:us|checkout",
                "intent": "status",
                "required": {"nodes": []},
                "forbidden": [],
            },
        ),
    ],
)
def test_generated_check_objects_are_rejected_before_execution(kind, expected):
    from pydantic import ValidationError

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    baseline, snapshot = draft_story(content, fixture["proposal"]["pack"])
    variant = with_question(baseline, content, snapshot)
    variant.checks.append(
        JourneyCheck(
            id="bad-shape",
            description="Invalid representation",
            source="selected-pack",
            kind=kind,
            expected=expected,
        )
    )
    with pytest.raises(ValidationError):
        validate_variant(variant, baseline, pack_snapshot=snapshot)


def test_generated_positive_ids_have_declared_key_arity():
    from context_graph.workbench.journey_authoring import JourneyProposalError

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    baseline, snapshot = draft_story(content, fixture["proposal"]["pack"])
    variant = with_question(baseline, content, snapshot)
    variant.checks[-1].expected["question"]["expected"] = ["Incident:account=us,id=INC-1042"]
    with pytest.raises(JourneyProposalError, match="wrong number of key parts"):
        validate_variant(variant, baseline, pack_snapshot=snapshot)


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("node_absent", {"node": "Incident:INC-1042"}),
        ("node_present", {"node": "Ticket:us|42"}),
        (
            "edge_absent",
            {"type": "DEPENDS_ON", "source": "Incident:us|42", "target": "Service:us|checkout"},
        ),
        (
            "edge_absent",
            {"type": "AFFECTS", "source": "Incident:42", "target": "Service:us|checkout"},
        ),
        (
            "retrieval",
            {
                "seed": "Incident:us|42",
                "intent": None,
                "required": [],
                "forbidden": ["Incident:42"],
            },
        ),
        (
            "retrieval",
            {
                "seed": "Incident:us|42",
                "intent": None,
                "required": [],
                "forbidden": [],
                "forbidden_edges": [["UNKNOWN", "Incident:us|42", "Service:us|checkout"]],
            },
        ),
    ],
)
def test_malformed_negative_and_positive_assertions_are_rejected(kind, expected):
    from context_graph.workbench.journey_authoring import JourneyProposalError

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    baseline, snapshot = draft_story(content, fixture["proposal"]["pack"])
    variant = with_question(baseline, content, snapshot)
    variant.checks.append(
        JourneyCheck(
            id="invalid",
            description="Invalid assertion",
            source="selected-pack",
            kind=kind,
            expected=expected,
        )
    )
    with pytest.raises(JourneyProposalError):
        validate_variant(variant, baseline, pack_snapshot=snapshot)
