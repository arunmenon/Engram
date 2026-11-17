"""Operator intake integration: authorization, revisions, consent and real engine sandbox."""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

from context_graph.workbench.api import create_app
from context_graph.workbench.authoring import verify_proposal
from context_graph.workbench.models import Content, Proposal

FIXTURE = Path(__file__).parents[1] / "fixtures/workbench/incident.json"


@pytest.mark.parametrize("malformed", [None, [], "invalid", 42])
def test_removal_inventory_tolerates_invalid_model_sections(malformed):
    from context_graph.workbench.changes import pack_items

    assert pack_items({"types": malformed, "events": malformed, "retrieval": malformed}) == set()
    assert pack_items({"types": {"nodes": {"Incident": malformed}}}) == {"nodes.Incident"}
    assert pack_items(
        {
            "types": {
                "nodes": {"Incident": {"properties": malformed, "lifecycle": {"states": malformed}}}
            }
        }
    ) == {"nodes.Incident"}


@pytest.mark.asyncio
async def test_model_repair_records_removed_fields_and_keeps_draft_pack_version(monkeypatch):
    from types import SimpleNamespace

    from context_graph.workbench.authoring import ModelAuthor

    fixture = json.loads(FIXTURE.read_text())
    fixture["content"]["decisions"]["relationship"] = "An Incident affects a Service."
    fixture["proposal"]["facts"].append(
        {
            "id": "relationship",
            "concept": "Incident service",
            "explanation": "Requested relationship",
            "basis": "operator",
            "decision_ids": ["relationship"],
            "pack_paths": ["/types/edges/AFFECTS"],
        }
    )
    first = copy.deepcopy(fixture["proposal"])
    first["pack"]["types"]["nodes"]["Incident"]["properties"]["severity"] = "number"
    second = copy.deepcopy(fixture["proposal"])
    second["pack"]["pack"]["version"] = "9.9.9"
    responses = iter([first, second])
    calls = []

    async def completion(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(next(responses))))]
        )

    monkeypatch.setattr("litellm.acompletion", completion)
    attempts = []
    proposal = await ModelAuthor("test")(
        Content.model_validate(fixture["content"]), on_attempt=attempts.append
    )
    assert attempts == [1, 2]
    assert len(calls) == 2
    assert proposal.repair_removals == ["nodes.Incident.severity"]
    assert proposal.pack["pack"]["version"] == first["pack"]["pack"]["version"]
    instructions = json.loads(calls[0]["messages"][1]["content"])
    assert "int" in instructions["property_type_vocabulary"]["scalars"]
    assert "number" not in instructions["property_type_vocabulary"]["scalars"]
    assert "number" in instructions["engine_capabilities"]["payload_contract_field_types"]
    assert "float" not in instructions["engine_capabilities"]["payload_contract_field_types"]
    assert "NOT events.payload_contract" in instructions["property_type_vocabulary"]["scope"]
    assert "untrusted_uncorroborated" in instructions["engine_capabilities"]["admission_rules"]
    assert "Sourced.trusted_producers" not in instructions["engine_capabilities"]["admission_rules"]
    schema = instructions["proposal_schema"]
    assert schema["$defs"]["Citation"]["properties"]["quote"]["minLength"] == 20
    quote = schema["$defs"]["Fact"]["properties"]["instruction_quote"]
    assert "null unless" in quote["description"]
    assert next(v for v in quote["anyOf"] if v["type"] == "string")["minLength"] == 20


@pytest.mark.asyncio
async def test_author_attempt_is_visible_to_other_pollers_and_cancel_stays_terminal(
    tmp_path, monkeypatch
):
    from context_graph.workbench.authoring import ModelAuthor

    started = asyncio.Event()

    async def completion(**kwargs):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("litellm.acompletion", completion)
    fixture = json.loads(FIXTURE.read_text())
    app = create_app(
        database=tmp_path / "progress.db", operators={"a": "alice"}, author=ModelAuthor("test")
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        await asyncio.wait_for(started.wait(), timeout=2)
        observed = (await client.get(root)).json()
        assert observed["job"]["status"] == "running"
        assert observed["job"]["attempt"] == 1
        cancelled = await client.post(root + "/cancel", json={"revision": observed["revision"]})
        assert cancelled.status_code == 200
        final = await wait_job(client, draft["id"])
        assert final["job"]["status"] == "cancelled"
        assert final["proposal"] is None


@pytest.mark.asyncio
async def test_pending_answers_and_removed_data_require_explicit_review(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    calls = 0

    async def author(content):
        nonlocal calls
        calls += 1
        proposal = copy.deepcopy(fixture["proposal"])
        if calls == 1:
            proposal["pack"]["types"]["nodes"]["Incident"]["properties"]["severity"] = "int"
        return Proposal.model_validate(proposal)

    app = create_app(database=tmp_path / "review.db", operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        content = copy.deepcopy(draft["content"])
        content["decisions"]["identity"] += " Keep regional identities separate."
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert draft["pending_decisions"] and not draft["proposal_stale"]
        assert not draft["readiness"]["run"]["ready"]
        review = {"accepted_facts": ["incident"], "pack_accepted": True}
        assert (
            await client.post(root + "/review", json={"revision": draft["revision"], **review})
        ).status_code == 409
        assert (
            await client.post(root + "/approve", json={"revision": draft["revision"]})
        ).status_code == 409
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert not draft["pending_decisions"]
        assert draft["proposal"]["repair_removals"] == ["nodes.Incident.severity"]
        assert (
            await client.post(root + "/review", json={"revision": draft["revision"], **review})
        ).status_code == 409
        result = await client.post(
            root + "/review",
            json={
                "revision": draft["revision"],
                **review,
                "accepted_removals": ["nodes.Incident.severity"],
                "accepted_changes": [c["id"] for c in draft["proposal_changes"]],
            },
        )
        assert result.status_code == 200
        assert result.json()["review"]["accepted_removals"] == ["nodes.Incident.severity"]


@pytest.mark.asyncio
async def test_job_failure_has_safe_reason_and_correlated_log(tmp_path, caplog):
    async def broken_author(content):
        raise TimeoutError("Bearer secret-token customer-private-document")

    app = create_app(
        database=tmp_path / "errors.db", operators={"a": "alice"}, author=broken_author
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        fixture = json.loads(FIXTURE.read_text())
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        result = await wait_job(client, draft["id"])
        assert result["job"]["status"] == "failed"
        assert "exceeded its time limit" in result["job"]["error"]
        assert "Error reference:" in result["job"]["error"]
        assert "exception=TimeoutError" in caplog.text
        for secret in ("secret-token", "customer-private-document"):
            assert secret not in caplog.text
            assert secret not in json.dumps(result)


async def wait_job(client, draft_id):
    for _ in range(200):
        record = (await client.get(f"/admin/tenants/{draft_id}")).json()
        if record.get("job", {}).get("status") != "running":
            return record
        await asyncio.sleep(0.01)
    pytest.fail("job did not finish")


@pytest.mark.asyncio
async def test_intake_to_review_real_engine_and_invalidation(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    calls = []

    async def author(content):
        calls.append(content)
        return Proposal.model_validate(fixture["proposal"])

    app = create_app(
        database=tmp_path / "drafts.db", operators={"a": "alice", "b": "bob"}, author=author
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        assert (
            await client.get("/admin/tenants", headers={"Authorization": ""})
        ).status_code == 401
        content = copy.deepcopy(fixture["content"])
        content["data_policy"] = "local_only"
        r = await client.post("/admin/tenants", json=content)
        assert r.status_code == 201, r.text
        draft = r.json()
        root = f"/admin/tenants/{draft['id']}"
        assert (await client.get(root, headers={"Authorization": "Bearer b"})).status_code == 404
        assert (
            await client.get("/admin/tenants", headers={"Authorization": "Bearer b"})
        ).json() == []
        assert (
            await client.post(root + "/author", json={"revision": draft["revision"]})
        ).status_code == 409
        assert not calls
        content["data_policy"] = "provider_allowed"
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert (await client.put(root, json={"revision": 1, "content": content})).status_code == 409
        assert (
            await client.post(root + "/approve", json={"revision": draft["revision"]})
        ).status_code == 409
        r = await client.post(root + "/author", json={"revision": draft["revision"]})
        assert r.status_code == 202, r.text
        draft = await wait_job(client, draft["id"])
        assert draft["job"]["status"] == "completed", draft
        assert len(calls) == 1
        draft = (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": ["incident"],
                    "pack_accepted": True,
                },
            )
        ).json()
        draft = (await client.post(root + "/validate", json={"revision": draft["revision"]})).json()
        assert draft["validation"]["passed"], draft["validation"]
        assert draft["readiness"]["run"]["ready"], draft["readiness"]
        r = await client.post(root + "/sandbox", json={"revision": draft["revision"]})
        assert r.status_code == 202, r.text
        draft = await wait_job(client, draft["id"])
        assert draft["sandbox"]["passed"], draft
        incident = [n for n in draft["sandbox"]["steps"][1]["nodes"] if n["type"] == "Incident"][0]
        assert incident["properties"]["status"] == "resolved"
        first = [n for n in draft["sandbox"]["steps"][0]["nodes"] if n["type"] == "Incident"][0]
        assert first["properties"]["status"] == "open"
        assert incident["properties"]["title"] == "Payments outage"
        assert draft["sandbox"]["steps"][2]["admitted"] is False
        assert draft["readiness"]["approve"]["ready"]
        draft = (await client.post(root + "/approve", json={"revision": draft["revision"]})).json()
        assert draft["approval"]["digest"]
        assert draft["runtime"]["activation"] == "not_requested"
        exported = (await client.get(root + "/export")).json()
        assert "INC-1042" in exported["eval_yaml"]
        content["scope"] += " Exclude billing."
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert draft["approval"] is None and draft["sandbox"] is None and draft["proposal_stale"]
        assert not draft["readiness"]["run"]["ready"]
        assert (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": ["incident"],
                    "pack_accepted": True,
                },
            )
        ).status_code == 409
    # Records survive a new application instance, but remain operator-owned.
    restarted = create_app(database=tmp_path / "drafts.db", operators={"a": "alice", "b": "bob"})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(restarted),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        assert len((await client.get("/admin/tenants")).json()) == 1


@pytest.mark.asyncio
async def test_cancel_prevents_late_author_result(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def author(content):
        started.set()
        try:
            await asyncio.sleep(60)
        finally:
            stopped.set()
        return Proposal.model_validate(fixture["proposal"])

    app = create_app(database=tmp_path / "drafts.db", operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        draft = (await client.post(root + "/author", json={"revision": draft["revision"]})).json()
        await started.wait()
        r = await client.post(root + "/cancel", json={"revision": draft["revision"]})
        assert r.status_code == 200
        await asyncio.wait_for(stopped.wait(), 1)
        draft = (await client.get(root)).json()
        assert draft["job"]["status"] == "cancelled"
        assert draft["proposal"] is None


def test_fabricated_source_quote_is_rejected():
    fixture = json.loads(FIXTURE.read_text())
    fixture["proposal"]["facts"][0]["citations"][0]["quote"] = "This is not in the source"
    with pytest.raises(ValueError, match="exact excerpt"):
        verify_proposal(
            Proposal.model_validate(fixture["proposal"]), Content.model_validate(fixture["content"])
        )


@pytest.mark.asyncio
async def test_source_edit_supersedes_inflight_proposal(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    entered = asyncio.Event()

    async def delayed_author(content):
        entered.set()
        await asyncio.sleep(30)
        return Proposal.model_validate(fixture["proposal"])

    app = create_app(
        database=tmp_path / "drafts.db", operators={"a": "alice"}, author=delayed_author
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        draft = (await client.post(root + "/author", json={"revision": draft["revision"]})).json()
        await entered.wait()
        changed = copy.deepcopy(fixture["content"])
        changed["scope"] = "A different scope"
        saved = await client.put(root, json={"revision": draft["revision"], "content": changed})
        assert saved.status_code == 200
        await asyncio.sleep(0)
        current = (await client.get(root)).json()
        assert current["content"]["scope"] == "A different scope"
        assert current["proposal"] is None and current["job"] is None


def test_restart_recovers_interrupted_job_without_fabricated_result(tmp_path):
    from context_graph.workbench.store import Store

    store = Store(tmp_path / "drafts.db")
    fixture = json.loads(FIXTURE.read_text())
    record = store.create("alice", fixture["content"])
    record["job"] = {"kind": "author", "status": "running"}
    store.put("alice", record, 1, "author_started")
    store.recover_jobs()
    recovered = store.get("alice", record["id"])
    assert recovered["job"]["status"] == "interrupted"
    assert recovered["proposal"] is None
    assert recovered["revision"] == 3


@pytest.mark.asyncio
async def test_sandbox_wrong_answer_fails_and_runs_are_isolated():
    from context_graph.workbench.sandbox import run_sandbox

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    wrong = content.model_copy(deep=True)
    wrong.questions[0].expected = ["Incident:other|INC-1042"]
    results = await asyncio.gather(
        run_sandbox(content, fixture["proposal"]["pack"]),
        run_sandbox(wrong, fixture["proposal"]["pack"]),
    )
    assert results[0]["passed"] is True
    assert results[1]["passed"] is False
    assert results[1]["evaluation"]["mean_f1"] == 0.0


@pytest.mark.asyncio
async def test_rejected_proposals_are_carried_into_revision_and_removed_sources_are_not(tmp_path):
    from context_graph.workbench.authoring import ModelAuthor

    fixture = json.loads(FIXTURE.read_text())
    contexts = []

    class RecordingAuthor(ModelAuthor):
        async def __call__(self, content, *, previous=None, on_attempt=None):
            contexts.append(previous)
            return Proposal.model_validate(fixture["proposal"])

    app = create_app(
        database=tmp_path / "drafts.db", operators={"a": "alice"}, author=RecordingAuthor("test")
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        draft = (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": [],
                    "rejected_facts": ["incident"],
                    "pack_accepted": False,
                },
            )
        ).json()
        assert not draft["readiness"]["run"]["ready"]
        changed = copy.deepcopy(draft["content"])
        changed["instruction"] = "Revise the rejected concept"
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": changed})
        ).json()
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert contexts[-1]["review"]["rejected_facts"] == ["incident"]
        changed["sources"] = [s for s in changed["sources"] if s["id"] != "runbook"]
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": changed})
        ).json()
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert contexts[-1] is None  # do not resend removed excerpts from prior proposals
        assert draft["job"]["status"] == "failed"  # fixture still cites the now absent source


@pytest.mark.asyncio
async def test_engine_change_requires_revalidation_and_body_is_bounded(tmp_path, monkeypatch):
    fixture = json.loads(FIXTURE.read_text())

    async def author(content):
        return Proposal.model_validate(fixture["proposal"])

    monkeypatch.setattr("context_graph.workbench.api.engine_revision", lambda: "engine-one")
    app = create_app(database=tmp_path / "drafts.db", operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        assert (await client.post("/admin/tenants", content=b" " * 1_200_001)).status_code == 413
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        draft = (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": ["incident"],
                    "pack_accepted": True,
                },
            )
        ).json()
        assert draft["readiness"]["run"]["ready"]
    monkeypatch.setattr("context_graph.workbench.api.engine_revision", lambda: "engine-two")
    restarted = create_app(database=tmp_path / "drafts.db", operators={"a": "alice"})
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(restarted),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.get(root)).json()
        assert not draft["readiness"]["run"]["ready"]
        assert (
            await client.post(root + "/sandbox", json={"revision": draft["revision"]})
        ).status_code == 409
        draft = (await client.post(root + "/validate", json={"revision": draft["revision"]})).json()
        assert draft["validation"]["engine_revision"] == "engine-two"
        assert draft["readiness"]["run"]["ready"]


@pytest.mark.asyncio
async def test_oracle_changes_retest_without_reauthoring_or_losing_model_review(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    calls = []

    async def author(content):
        calls.append(content)
        return Proposal.model_validate(fixture["proposal"])

    app = create_app(database=tmp_path / "drafts.db", operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        content = copy.deepcopy(fixture["content"])
        content["questions"] = []
        draft = (await client.post("/admin/tenants", json=content)).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert [m["role"] for m in draft["author_messages"]] == ["operator", "assistant"]
        draft = (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": ["incident"],
                    "pack_accepted": True,
                },
            )
        ).json()
        assert not draft["readiness"]["run"]["ready"]
        content["questions"] = copy.deepcopy(fixture["content"]["questions"])
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert draft["review"]["pack_accepted"] and not draft["proposal_stale"]
        assert draft["readiness"]["run"]["ready"]
        await client.post(root + "/sandbox", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert draft["sandbox"]["passed"]
        draft = (await client.post(root + "/approve", json={"revision": draft["revision"]})).json()
        assert draft["approval"]
        content["questions"][0]["expected"] = ["Incident:missing|wrong"]
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert draft["approval"] is None and draft["sandbox"] is None
        assert draft["review"]["pack_accepted"] and not draft["readiness"]["run"]["ready"]
        assert not draft["content"]["questions"][0]["reviewed"]
        content = copy.deepcopy(draft["content"])
        content["questions"][0]["reviewed"] = True
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        await client.post(root + "/sandbox", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert not draft["sandbox"]["passed"] and not draft["readiness"]["approve"]["ready"]
        assert len(calls) == 1
        content["decisions"]["identity"] = "Use a different key"
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert draft["pending_decisions"] and draft["review"] is None
        assert not draft["readiness"]["run"]["ready"]
        assert (
            await client.post(root + "/sandbox", json={"revision": draft["revision"]})
        ).status_code == 409
        assert (
            await client.post(root + "/approve", json={"revision": draft["revision"]})
        ).status_code == 409


@pytest.mark.asyncio
async def test_failure_feedback_survives_saved_revision_request(tmp_path, monkeypatch):
    from context_graph.workbench.authoring import ModelAuthor

    fixture = json.loads(FIXTURE.read_text())
    contexts = []

    async def authored(self, content, *, previous=None, on_attempt=None):
        contexts.append(previous)
        return Proposal.model_validate(fixture["proposal"])

    monkeypatch.setattr(ModelAuthor, "__call__", authored)
    app = create_app(
        database=tmp_path / "drafts.db", operators={"a": "alice"}, author=ModelAuthor("test")
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        content = copy.deepcopy(fixture["content"])
        content["questions"][0]["expected"] = ["Incident:wrong|answer"]
        draft = (await client.post("/admin/tenants", json=content)).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        draft = (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": ["incident"],
                    "pack_accepted": True,
                },
            )
        ).json()
        await client.post(root + "/sandbox", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        failed = draft["sandbox"]
        assert not failed["passed"]
        content["instruction"] = (
            "Investigate the failed check without changing the expected answers"
        )
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert draft["previous_sandbox"]["result"] == failed
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert contexts[-1]["evaluation"] == failed["evaluation"]
        assert draft["previous_sandbox"]["result"] == failed
        assert draft["sandbox"] is None and draft["approval"] is None
        assert draft["author_messages"][-2]["text"] == content["instruction"]


def test_seed_mode_carriers_preserve_legacy_and_explicit_questions(tmp_path):
    import yaml

    from context_graph.ontology.evaluation import EvalSet, load_eval_set
    from context_graph.workbench.sandbox import evaluation_artifact

    fixture = json.loads(FIXTURE.read_text())
    legacy = Content.model_validate(fixture["content"])
    assert all(q.seed_mode == "discover" for q in legacy.questions)
    legacy.questions[0].seed_mode = "explicit"
    artifact = evaluation_artifact(legacy, "incident")
    loaded = EvalSet.model_validate(artifact)
    assert loaded.questions[0].seed_mode == "explicit"
    path = tmp_path / "incident.eval.yaml"
    path.write_text(yaml.safe_dump(artifact))
    assert load_eval_set(path) == loaded
    assert (
        Content.model_validate_json(legacy.model_dump_json()).questions[0].seed_mode == "explicit"
    )


def test_repeated_sample_retains_request_identity_and_explicit_trace():
    from context_graph.domain.event_acceptance import request_fingerprint
    from context_graph.workbench.engine import event_from_sample

    sample = {
        "event_id": "procurement-retry",
        "event_type": "procurement.order_line.recorded",
        "occurred_at": "2026-11-01T09:00:00Z",
        "producer_id": "procurement-adapter",
        "payload": {"company_id": "us", "order_id": "PO-100", "line_id": "1"},
    }
    first, retry = event_from_sample(sample, 4), event_from_sample(sample, 26)
    assert first == retry
    assert request_fingerprint(first, sample["payload"]) == request_fingerprint(
        retry, sample["payload"]
    )
    assert event_from_sample(dict(sample, trace_id="source-trace"), 26).trace_id == "source-trace"
    anonymous = {"event_type": "incident.opened", "payload": {}}
    assert event_from_sample(anonymous, 4).trace_id == "sample-4"


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["failure", "cancel", "restart", "success"])
@pytest.mark.parametrize("changed_scope", [False, True])
async def test_author_revision_preserves_prior_state_until_replacement(
    tmp_path, outcome, changed_scope
):
    from context_graph.workbench.store import Store

    fixture = json.loads(FIXTURE.read_text())
    entered, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def author(content):
        nonlocal calls
        calls += 1
        if calls > 1:
            entered.set()
            await release.wait()
            if outcome == "failure":
                raise TimeoutError("provider unavailable")
        return Proposal.model_validate(fixture["proposal"])

    database = tmp_path / "drafts.db"
    app = create_app(database=database, operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        draft = (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": ["incident"],
                    "pack_accepted": True,
                },
            )
        ).json()
        await client.post(root + "/sandbox", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert draft["sandbox"]["passed"]
        draft = (await client.post(root + "/approve", json={"revision": draft["revision"]})).json()
        if changed_scope:
            content = copy.deepcopy(draft["content"])
            content["scope"] += " Exclude billing."
            draft = (
                await client.put(
                    root,
                    json={
                        "revision": draft["revision"],
                        "content": content,
                    },
                )
            ).json()
        prior = copy.deepcopy(draft)
        started = await client.post(root + "/author", json={"revision": draft["revision"]})
        assert started.status_code == 202
        await asyncio.wait_for(entered.wait(), timeout=2)
        running = (await client.get(root)).json()
        for key in ("proposal", "review", "validation", "sandbox", "approval"):
            assert running.get(key) == prior.get(key), key
        assert not running["readiness"]["approve"]["ready"]
        if outcome == "cancel":
            result = await client.post(root + "/cancel", json={"revision": running["revision"]})
            assert result.status_code == 200
        elif outcome == "restart":
            # Exercise durable restart recovery and its fence against late completion.
            Store(database).recover_jobs()
        release.set()
        draft = await wait_job(client, draft["id"])
        await asyncio.sleep(0.02)
        draft = (await client.get(root)).json()
        if outcome == "success":
            assert draft["job"]["status"] == "completed"
            assert draft["review"] is None and draft["sandbox"] is None
            assert draft["approval"] is None
            assert draft["validation"]["passed"]
        else:
            expected_status = {"failure": "failed", "cancel": "cancelled", "restart": "interrupted"}
            assert draft["job"]["status"] == expected_status[outcome]
            for key in (
                "proposal",
                "review",
                "validation",
                "sandbox",
                "approval",
                "proposal_stale",
            ):
                assert draft.get(key) == prior.get(key), key
            assert draft["readiness"]["run"]["ready"] is not changed_scope
            approval = await client.post(root + "/approve", json={"revision": draft["revision"]})
            assert approval.status_code == (409 if changed_scope else 200)


@pytest.mark.parametrize("section", ["key", "initial", "guard", "handling", "retrieval", "mapping"])
def test_pack_diff_reports_behavior_changes(section):
    from context_graph.workbench.changes import pack_changes

    before = {
        "types": {
            "nodes": {"Incident": {"key": ["account", "id"], "lifecycle": {"initial": "open"}}}
        },
        "events": {"incident.opened": {"handling": "processed"}},
        "projection": [{"event": "incident.closed", "only_from": ["open"]}],
        "retrieval": {"depth": 2},
    }
    after = copy.deepcopy(before)
    if section == "key":
        after["types"]["nodes"]["Incident"]["key"] = ["id"]
    elif section == "initial":
        after["types"]["nodes"]["Incident"]["lifecycle"]["initial"] = "closed"
    elif section == "guard":
        after["projection"][0]["only_from"] = ["open", "closed"]
    elif section == "handling":
        after["events"]["incident.opened"]["handling"] = "ledger_only"
    elif section == "retrieval":
        after["retrieval"]["depth"] = 3
    else:
        after["projection"] = []
    changes = pack_changes(before, after)
    assert len(changes) == 1
    assert changes[0]["before"] != changes[0]["after"]
    assert changes[0]["id"] != pack_changes(after, before)[0]["id"]
    assert pack_changes(after, after) == []


@pytest.mark.asyncio
async def test_changed_pack_requires_acknowledgement_and_retry_cannot_hide_diff(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    calls = 0

    async def author(_content):
        nonlocal calls
        calls += 1
        proposal = copy.deepcopy(fixture["proposal"])
        if calls > 1:
            node = proposal["pack"]["types"]["nodes"]["Incident"]
            node["key"] = list(reversed(node["key"]))
            # Even a changed definition that loads must be explicitly reviewed.
            node["properties"]["extra_note"] = "string"
        return Proposal.model_validate(proposal)

    app = create_app(database=tmp_path / "diff.db", operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        draft = (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": ["incident"],
                    "pack_accepted": True,
                },
            )
        ).json()
        seen = None
        for _ in range(2):
            await client.post(root + "/author", json={"revision": draft["revision"]})
            draft = await wait_job(client, draft["id"])
            changes = [c["id"] for c in draft["proposal_changes"]]
            assert changes
            if seen is not None:
                assert changes == seen
            seen = changes
            body = {
                "revision": draft["revision"],
                "accepted_facts": ["incident"],
                "pack_accepted": True,
            }
            assert (await client.post(root + "/review", json=body)).status_code == 409
            assert not draft["readiness"]["run"]["ready"]
        body["accepted_changes"] = ["obsolete"]
        assert (await client.post(root + "/review", json=body)).status_code == 422
        body["accepted_changes"] = seen
        accepted = await client.post(root + "/review", json=body)
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["review"]["accepted_changes"] == seen


def test_author_prompt_excludes_structured_oracle_without_mutating_inputs():
    from context_graph.workbench.authoring import author_inputs
    from context_graph.workbench.models import Content

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    content.questions[0].expected = ["oracle-only-secret"]
    content.expected_nodes = ["oracle-graph-secret"]
    previous = {
        "evaluation": {
            "passed": False,
            "mean_f1": 0.0,
            "min_f1": 1.0,
            "questions": [
                {
                    "id": "q",
                    "f1": 0.0,
                    "expected": ["oracle-only-secret"],
                    "found": [],
                    "error": "Missing oracle-only-secret",
                }
            ],
        }
    }
    inputs, feedback = author_inputs(content, previous)
    serialized = json.dumps([inputs, feedback])
    assert "oracle-only-secret" not in serialized
    assert "oracle-graph-secret" not in serialized
    assert inputs["questions"][0]["query"] == content.questions[0].query
    assert not {"seed_node_ids", "node_type", "seed_mode"} & inputs["questions"][0].keys()
    assert feedback["evaluation"]["questions"][0]["has_error"]
    assert content.questions[0].expected == ["oracle-only-secret"]
    assert previous["evaluation"]["questions"][0]["expected"] == ["oracle-only-secret"]


@pytest.mark.asyncio
async def test_policy_confirmation_accepts_unchanged_pack_without_second_author_call(tmp_path):
    fixture = json.loads(FIXTURE.read_text())
    content = copy.deepcopy(fixture["content"])
    content["decisions"] = {}
    calls = 0

    async def author(_content):
        nonlocal calls
        calls += 1
        proposal = copy.deepcopy(fixture["proposal"])
        proposal["decisions"] = []
        return Proposal.model_validate(proposal)

    app = create_app(database=tmp_path / "confirm.db", operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=content)).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert not draft["readiness"]["run"]["ready"]
        accepted = await client.post(
            root + "/review",
            json={
                "revision": draft["revision"],
                "accepted_facts": ["incident"],
                "pack_accepted": True,
                "confirmed_policies": ["identity", "lifecycle"],
            },
        )
        assert accepted.status_code == 200
        draft = accepted.json()
        assert draft["readiness"]["run"]["ready"], draft["readiness"]
        assert draft["content"]["decisions"] == {}
        assert calls == 1
        # A new proposal must be reviewed again; confirmations do not carry silently.
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert draft["review"] is None
        assert not draft["readiness"]["run"]["ready"]


def test_fact_links_resolve_pack_elements_and_recorded_decisions():
    from context_graph.workbench.models import Content

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    proposal = Proposal.model_validate(fixture["proposal"])
    fact = proposal.facts[0].model_copy(deep=True)
    fact.id = "identity-link"
    proposal.facts.append(fact)
    fact.pack_paths = ["/types/nodes/Incident/key"]
    fact.basis = "operator"
    fact.decision_ids = ["identity"]
    verify_proposal(proposal, content)
    fact.decision_ids = ["invented-decision"]
    with pytest.raises(ValueError, match="unknown operator decision"):
        verify_proposal(proposal, content)
    fact.decision_ids = ["identity"]
    fact.pack_paths = ["/types/nodes/Nonexistent/key"]
    with pytest.raises(ValueError, match="does not resolve"):
        verify_proposal(proposal, content)


def test_business_expectation_is_required_for_new_question_and_withheld_from_author():
    from context_graph.workbench.api import readiness
    from context_graph.workbench.authoring import author_inputs
    from context_graph.workbench.models import Content

    fixture = json.loads(FIXTURE.read_text())
    fixture["content"]["questions"][0]["expectation_statement"] = ""
    missing = readiness({"content": fixture["content"]})["run"]["missing"]
    assert any("business expectation" in message for message in missing)
    content = Content.model_validate(fixture["content"])
    content.questions[0].expectation_statement = "Independent operator oracle"
    inputs, _ = author_inputs(content, None)
    assert "Independent operator oracle" not in json.dumps(inputs)


@pytest.mark.parametrize("quote", ["Add Sourced to Incident.", "invented request", " "])
def test_operator_instruction_provenance(quote):
    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    content.instruction = "Add Sourced to Incident. Keep its key."
    proposal = Proposal.model_validate(fixture["proposal"])
    from context_graph.workbench.models import Fact

    proposal.facts.append(
        Fact(
            id="revision",
            concept="Trust",
            explanation="Requested trust interface",
            basis="operator",
            instruction_quote=quote,
        )
    )
    if quote == "Add Sourced to Incident.":
        verify_proposal(proposal, content)
        content.instruction = "A different request"
        with pytest.raises(ValueError, match="current revision request"):
            verify_proposal(proposal, content)
    else:
        with pytest.raises(ValueError, match="at least 20 meaningful characters"):
            verify_proposal(proposal, content)


@pytest.mark.asyncio
@pytest.mark.parametrize("unsupported_first", [False, True])
async def test_missing_relationship_returns_clarification(monkeypatch, unsupported_first):
    from types import SimpleNamespace

    from context_graph.workbench.authoring import ModelAuthor

    fixture = json.loads(FIXTURE.read_text())
    proposal = copy.deepcopy(fixture["proposal"])
    proposal["pack"] = None
    for fact in proposal["facts"]:
        fact["pack_paths"] = []
    proposal["decisions"] = [
        {
            "id": "relationship",
            "question": "Which service does an incident affect?",
            "effect": "A source relationship is needed to answer this question.",
        }
    ]
    calls = []
    responses = ([fixture["proposal"]] if unsupported_first else []) + [proposal]

    async def completion(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(responses.pop(0))))]
        )

    monkeypatch.setattr("litellm.acompletion", completion)
    result = await ModelAuthor("test")(Content.model_validate(fixture["content"]))
    assert len(calls) == (2 if unsupported_first else 1)
    if unsupported_first:
        assert "Relationship AFFECTS has no linked" in calls[1]["messages"][-1]["content"]
    assert result.pack is None
    assert result.decisions[0].id == "relationship"
    assert "pack=null" in calls[0]["messages"][0]["content"]
    assert "instruction_quote" in calls[0]["messages"][0]["content"]


@pytest.mark.parametrize("basis", ["inference", "source", "operator"])
def test_generated_relationship_requires_specific_evidence_link(basis):
    from context_graph.workbench.authoring import verify_relationship_grounding
    from context_graph.workbench.models import Fact

    fixture = json.loads(FIXTURE.read_text())
    proposal = Proposal.model_validate(fixture["proposal"])
    with pytest.raises(ValueError, match="Relationship AFFECTS"):
        verify_relationship_grounding(proposal)
    fact = Fact(
        id="edge",
        concept="Affects",
        explanation="Relationship evidence",
        basis=basis,
        pack_paths=["/types/edges/AFFECTS"],
    )
    if basis == "source":
        from context_graph.workbench.models import Citation

        fact.citations = [Citation(source_id="spec", quote="An incident affects a service.")]
    if basis == "operator":
        fact.instruction_quote = "Model the incident's affected service."
    proposal.facts.append(fact)
    if basis == "inference":
        with pytest.raises(ValueError, match="Relationship AFFECTS"):
            verify_relationship_grounding(proposal)
    else:
        verify_relationship_grounding(proposal)
        fact.pack_paths = ["/types/nodes/Incident"]
        with pytest.raises(ValueError, match="Relationship AFFECTS"):
            verify_relationship_grounding(proposal)


def test_engine_missing_intent_becomes_clarification_without_changing_oracle():
    from context_graph.workbench.authoring import clarify_missing_retrieval_evidence

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    original = content.model_dump()
    proposal = Proposal.model_validate(fixture["proposal"])
    proposal.pack["types"]["edges"] = {}
    question = content.questions[0]
    checks = {"problems": [f"Question {question.id}: intent {question.intent} is not executable"]}
    result = clarify_missing_retrieval_evidence(proposal, content, checks)
    assert result is not None and result.pack is None
    assert "related entity and source" in result.decisions[-1].question
    assert content.model_dump() == original
    assert proposal.pack is not None
    assert all(not fact.pack_paths for fact in result.facts)
    assert clarify_missing_retrieval_evidence(proposal, content, {"problems": ["syntax"]}) is None


@pytest.mark.parametrize(
    "reviewed,selected,cited,valid",
    [
        (True, ["pagerduty"], ["pagerduty"], True),
        (True, [], [], True),
        (False, ["pagerduty"], ["pagerduty"], False),
        (True, ["pagerduty"], [], False),
        (True, [], ["pagerduty"], False),
    ],
)
def test_operator_trust_evidence_matches_reviewed_settings(reviewed, selected, cited, valid):
    from context_graph.workbench.models import Fact

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    content.trust_reviewed = reviewed
    content.trusted_ids = selected
    proposal = Proposal.model_validate(fixture["proposal"])
    proposal.facts.append(
        Fact(
            id="trust",
            concept="Source trust",
            explanation="Configured trust",
            basis="operator",
            trusted_producers=cited,
        )
    )
    if valid:
        verify_proposal(proposal, content)
    else:
        with pytest.raises(ValueError, match="reviewed producer settings"):
            verify_proposal(proposal, content)


def test_trust_settings_cannot_ground_a_domain_relationship():
    from context_graph.workbench.authoring import verify_relationship_grounding
    from context_graph.workbench.models import Fact

    fixture = json.loads(FIXTURE.read_text())
    proposal = Proposal.model_validate(fixture["proposal"])
    proposal.facts.append(
        Fact(
            id="edge",
            concept="Affects",
            explanation="Not supported by trust",
            basis="operator",
            trusted_producers=["pagerduty"],
            pack_paths=["/types/edges/AFFECTS"],
        )
    )
    with pytest.raises(ValueError, match="Relationship AFFECTS"):
        verify_relationship_grounding(proposal)


@pytest.mark.asyncio
@pytest.mark.parametrize("reset", ["decisions", "sources"])
async def test_accepted_baseline_survives_review_reset(tmp_path, reset):
    fixture = json.loads(FIXTURE.read_text())
    calls = 0

    async def author(content):
        nonlocal calls
        calls += 1
        proposal = copy.deepcopy(fixture["proposal"])
        if calls == 2:
            proposal["pack"]["types"]["nodes"]["Incident"]["properties"]["extra_note"] = "string"
        return Proposal.model_validate(proposal)

    app = create_app(database=tmp_path / "baseline.db", operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        for _ in range(2):
            await client.post(root + "/author", json={"revision": draft["revision"]})
            draft = await wait_job(client, draft["id"])
            draft = (
                await client.post(
                    root + "/review",
                    json={
                        "revision": draft["revision"],
                        "accepted_facts": ["incident"],
                        "pack_accepted": True,
                        "accepted_changes": [c["id"] for c in draft["proposal_changes"]],
                    },
                )
            ).json()
        content = copy.deepcopy(draft["content"])
        if reset == "decisions":
            content["decisions"]["identity"] += " Keep account isolation."
        else:
            content["sources"][0]["text"] += " Keep account isolation."
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert draft["review"] is None
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        assert any(c["path"][-1] == "extra_note" for c in draft["proposal_changes"])
        rejected = await client.post(
            root + "/review",
            json={
                "revision": draft["revision"],
                "accepted_facts": ["incident"],
                "pack_accepted": True,
                "accepted_removals": draft["proposal"]["repair_removals"],
            },
        )
        assert rejected.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("evidence_kind", ["trust", "instruction"])
async def test_saved_provenance_change_invalidates_acceptance(tmp_path, evidence_kind):
    fixture = json.loads(FIXTURE.read_text())
    fixture["content"]["instruction"] = "Add Sourced to Incident."
    fact = {
        "id": "operator",
        "concept": "Trust",
        "explanation": "Operator evidence",
        "basis": "operator",
    }
    fact.update(
        {"trusted_producers": ["pagerduty"]}
        if evidence_kind == "trust"
        else {"instruction_quote": "Add Sourced to Incident."}
    )
    fixture["proposal"]["facts"].append(fact)

    async def author(content):
        return Proposal.model_validate(fixture["proposal"])

    app = create_app(database=tmp_path / "evidence.db", operators={"a": "alice"}, author=author)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app),
        base_url="http://test",
        headers={"Authorization": "Bearer a"},
    ) as client:
        draft = (await client.post("/admin/tenants", json=fixture["content"])).json()
        root = f"/admin/tenants/{draft['id']}"
        await client.post(root + "/author", json={"revision": draft["revision"]})
        draft = await wait_job(client, draft["id"])
        draft = (
            await client.post(
                root + "/review",
                json={
                    "revision": draft["revision"],
                    "accepted_facts": ["incident", "operator"],
                    "pack_accepted": True,
                },
            )
        ).json()
        content = copy.deepcopy(draft["content"])
        if evidence_kind == "trust":
            content["trusted_ids"] = []
        else:
            content["instruction"] = "Rename Service to Component."
        draft = (
            await client.put(root, json={"revision": draft["revision"], "content": content})
        ).json()
        assert draft["proposal_stale"] and draft["review"] is None
        if evidence_kind == "trust":
            assert not draft["content"]["trust_reviewed"]
        assert (
            await client.post(root + "/sandbox", json={"revision": draft["revision"]})
        ).status_code == 409


def test_clarification_does_not_hide_other_engine_errors_or_repeat_relationship_question():
    from context_graph.workbench.authoring import clarify_missing_retrieval_evidence
    from context_graph.workbench.models import Decision

    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    proposal = Proposal.model_validate(fixture["proposal"])
    proposal.pack["types"]["edges"] = {}
    proposal.decisions = [
        Decision(
            id="edge", question="Which relationship is supported?", effect="Need edge evidence"
        )
    ]
    message = "Question status: intent incident_status is not executable"
    assert (
        clarify_missing_retrieval_evidence(
            proposal, content, {"problems": [message, "Missing contract"]}
        )
        is None
    )
    result = clarify_missing_retrieval_evidence(proposal, content, {"problems": [message]})
    assert result is not None and len(result.decisions) == 1


@pytest.mark.parametrize("quote", ["{", "the"])
def test_short_quotes_cannot_launder_relationship_evidence(quote):
    fixture = json.loads(FIXTURE.read_text())
    content = Content.model_validate(fixture["content"])
    content.instruction = "Keep the relationship unchanged. {"
    proposal = Proposal.model_validate(fixture["proposal"])
    from context_graph.workbench.models import Fact

    proposal.facts.append(
        Fact(
            id="edge",
            concept="Edge",
            explanation="Uninformative quote",
            basis="operator",
            instruction_quote=quote,
            pack_paths=["/types/edges/AFFECTS"],
        )
    )
    with pytest.raises(ValueError, match="instruction quote"):
        verify_proposal(proposal, content)
