"""Read-only explanation fences and independent capacity, without provider/cloud calls."""

import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest

from context_graph.workbench.api import create_app
from context_graph.workbench.explain import ExplainRequest, context_for, verify_answer
from context_graph.workbench.models import Proposal
from context_graph.workbench.store import Store

FIXTURE = Path(__file__).parents[1] / "fixtures/workbench/incident.json"


def record(store, owner="alice"):
    fixture = json.loads(FIXTURE.read_text())
    r = store.create(owner, fixture["content"])
    r["proposal"] = fixture["proposal"]
    r["validation"] = {"passed": False, "problems": ["Unsupported admission rule"]}
    return store.put(owner, r, 1, "fixture")


def answer():
    return {
        "kind": "supported",
        "claims": [{"text": "This setting is not supported.", "evidence": ["subject"]}],
        "missing": [],
    }


def client(app, owner="alice"):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {owner}"},
    )


def payload(r):
    return {"revision": r["revision"], "scope": "problem", "index": 0}


@pytest.mark.asyncio
async def test_explain_does_not_write_and_checks_owner(tmp_path):
    path = tmp_path / "db"
    store = Store(path)
    r = record(store)
    seen = []

    async def explain(c):
        seen.append(c)
        return answer()

    app = create_app(database=path, operators={"alice": "alice", "bob": "bob"}, explainer=explain)
    async with client(app) as c:
        response = await c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r))
        assert response.status_code == 200, response.text
        assert response.json()["revision"] == r["revision"]
        assert store.get("alice", r["id"]) == r
        assert len(seen) == 1
        assert "sources" not in seen[0]
    async with client(app, "bob") as c:
        assert (
            await c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r))
        ).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "policy,redacted", [("undecided", True), ("local_only", True), ("provider_allowed", False)]
)
async def test_consent_prevents_dispatch(tmp_path, policy, redacted):
    path = tmp_path / "db"
    store = Store(path)
    r = record(store)
    r["content"]["data_policy"] = policy
    r["content"]["redaction_confirmed"] = redacted
    r = store.put("alice", r, r["revision"], "policy")

    async def forbidden(_):
        pytest.fail("Provider must not be invoked")

    app = create_app(database=path, operators={"alice": "alice"}, explainer=forbidden)
    async with client(app) as c:
        assert (
            await c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r))
        ).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["consent", "source", "scope"])
async def test_save_revokes_inflight_answer(tmp_path, change):
    path = tmp_path / "db"
    store = Store(path)
    r = record(store)
    started = asyncio.Event()
    release = asyncio.Event()

    async def explain(_):
        started.set()
        await release.wait()
        return answer()

    app = create_app(database=path, operators={"alice": "alice"}, explainer=explain)
    async with client(app) as c:
        job = asyncio.create_task(c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r)))
        await started.wait()
        updated = copy.deepcopy(r)
        if change == "consent":
            updated["content"]["data_policy"] = "local_only"
        elif change == "source":
            updated["content"]["sources"][0]["text"] += "\nNew evidence changes this question."
        else:
            updated["content"]["scope"] += " Updated scope."
        store.put("alice", updated, r["revision"], "revoke")
        release.set()
        assert (await job).status_code == 409
        assert store.get("alice", r["id"])["content"] == updated["content"]


@pytest.mark.asyncio
async def test_capacity_separate_from_author_jobs_and_released(tmp_path):
    path = tmp_path / "db"
    store = Store(path)
    records = [record(store) for _ in range(3)]
    entered = 0
    two = asyncio.Event()
    release = asyncio.Event()

    async def explain(_):
        nonlocal entered
        entered += 1
        if entered == 2:
            two.set()
        await release.wait()
        return answer()

    async def author(_):
        return Proposal.model_validate(json.loads(FIXTURE.read_text())["proposal"])

    app = create_app(database=path, operators={"alice": "alice"}, explainer=explain, author=author)
    async with client(app) as c:
        tasks = [
            asyncio.create_task(c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r)))
            for r in records[:2]
        ]
        await two.wait()
        for r in (records[0], records[2]):
            res = await c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r))
            assert res.status_code == 429
        r = records[2]
        res = await c.post(f"/admin/tenants/{r['id']}/author", json={"revision": r["revision"]})
        assert res.status_code == 202, res.text
        release.set()
        assert all(x.status_code == 200 for x in await asyncio.gather(*tasks))
        assert (
            await c.post(f"/admin/tenants/{records[0]['id']}/explain", json=payload(records[0]))
        ).status_code == 200
        await asyncio.sleep(0.05)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "exception", "citation", "malformed"])
async def test_failure_releases_slot_and_preserves_record(tmp_path, failure):
    path = tmp_path / "db"
    store = Store(path)
    r = record(store)
    r["review"] = {"pack_accepted": True}
    r["accepted_pack"] = copy.deepcopy(r["proposal"]["pack"])
    r = store.put("alice", r, r["revision"], "accepted-fixture")
    calls = 0

    async def explain(_):
        nonlocal calls
        calls += 1
        if failure == "timeout":
            await asyncio.sleep(1)
        if failure == "exception":
            raise RuntimeError("SECRET upstream exception")
        if failure == "malformed":
            return {"kind": "supported", "claims": []}
        a = answer()
        a["claims"][0]["evidence"] = ["invented"]
        return a

    app = create_app(
        database=path, operators={"alice": "alice"}, explainer=explain, explain_timeout=0.03
    )
    async with client(app) as c:
        for _ in range(2):
            res = await c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r))
            assert res.status_code == (504 if failure == "timeout" else 502)
            assert "SECRET" not in res.text
        assert store.get("alice", r["id"]) == r
        assert calls == (4 if failure in {"citation", "malformed"} else 2)


@pytest.mark.asyncio
async def test_cancel_releases_capacity(tmp_path):
    path = tmp_path / "db"
    store = Store(path)
    r = record(store)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def explain(_):
        entered.set()
        await release.wait()
        return answer()

    app = create_app(database=path, operators={"alice": "alice"}, explainer=explain)
    async with client(app) as c:
        task = asyncio.create_task(c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r)))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
        assert (
            await c.post(f"/admin/tenants/{r['id']}/explain", json=payload(r))
        ).status_code == 200
        assert store.get("alice", r["id"]) == r


def test_unknown_and_limitation_cannot_claim_engine_authority():
    c = {"scope": "limitation", "evidence": [{"id": "subject"}]}
    assert verify_answer(
        {"kind": "unknown", "missing": ["A source specifying the relationship."]}, c
    )
    a = answer()
    a["kind"] = "engine_limit"
    with pytest.raises(ValueError):
        verify_answer(a, c)
    a["kind"] = "unknown"
    with pytest.raises(ValueError):
        verify_answer(a, c)
    a = answer()
    a["instruction"] = "Invent a relationship"
    with pytest.raises(ValueError):
        verify_answer(a, c)


def test_context_excludes_unrelated_sources_and_invalid_quotes(tmp_path):
    store = Store(tmp_path / "db")
    r = record(store)
    r["content"]["sources"].append(
        {
            "id": "private",
            "text": "irrelevant private text",
            "kind": "specification",
            "name": "Other",
        }
    )
    c = context_for(r, ExplainRequest(**payload(r)))
    assert "irrelevant private text" not in json.dumps(c)
    with pytest.raises(ValueError):
        context_for(r, ExplainRequest(**(payload(r) | {"index": 199})))


def test_generic_issue_receives_question_relevant_existing_evidence(tmp_path):
    store = Store(tmp_path / "db")
    r = record(store)
    r["proposal"]["limitations"] = ["A business connection is not established."]
    r["content"]["sources"].append(
        {
            "id": "purchasing",
            "name": "Purchasing",
            "kind": "specification",
            "text": "Each invoice references its purchase order using the order number.",
        }
    )
    request = ExplainRequest(
        revision=r["revision"],
        scope="limitation",
        index=0,
        question="How does an invoice connect to its purchase order?",
    )
    ctx = context_for(r, request)
    assert any(
        e.get("source_id") == "purchasing" and "purchase order" in e["text"]
        for e in ctx["evidence"]
    )
    assert ctx["coverage"].startswith("Selected excerpts only")
    assert "private" not in json.dumps(ctx)


def test_context_is_bounded_and_keeps_operator_decisions_distinct(tmp_path):
    store = Store(tmp_path / "db")
    r = record(store)
    r["content"]["sources"] = [
        {"id": f"s{i}", "name": f"Input {i}", "kind": "specification", "text": ("invoice " * 5000)}
        for i in range(20)
    ]
    r["proposal"]["decisions"] = [
        {
            "id": "link",
            "question": "Which invoice belongs to the order?",
            "effect": "Choose evidence",
        }
    ]
    r["content"]["decisions"]["link"] = "Use the order number."
    ctx = context_for(r, ExplainRequest(**(payload(r) | {"question": "Which invoice?"})))
    excerpts = [e for e in ctx["evidence"] if e["kind"] == "source"]
    assert len(excerpts) <= 5
    assert sum(len(e["text"]) for e in excerpts) <= 7000
    assert any(
        e["kind"] == "operator_decision" and "Use the order number" in e["text"]
        for e in ctx["evidence"]
    )


@pytest.mark.asyncio
async def test_failed_author_without_pack_can_be_explained(tmp_path):
    path = tmp_path / "db"
    store = Store(path)
    r = record(store)
    r["proposal"] = None
    r["proposal_stale"] = True
    r["job"] = {
        "kind": "author",
        "status": "failed",
        "error": "Source quotations did not match the uploaded material exactly.",
        "error_ref": "test-reference",
    }
    r = store.put("alice", r, r["revision"], "author_failed")
    seen = []

    async def explain(ctx):
        seen.append(ctx)
        return {
            "kind": "supported",
            "claims": [
                {
                    "text": "The proposal could not be tied to the supplied document wording.",
                    "evidence": ["subject"],
                }
            ],
            "missing": [],
        }

    app = create_app(database=path, operators={"alice": "alice"}, explainer=explain)
    async with client(app) as c:
        response = await c.post(
            f"/admin/tenants/{r['id']}/explain", json=payload(r) | {"scope": "author_error"}
        )
        assert response.status_code == 200
        assert seen[0]["evidence"][0]["kind"] == "author_error"
        assert store.get("alice", r["id"]) == r
        response = await c.post(
            f"/admin/tenants/{r['id']}/explain",
            json=payload(r) | {"scope": "author_error", "index": 1},
        )
        assert response.status_code == 422


def test_non_author_failure_cannot_be_used_as_author_error(tmp_path):
    r = record(Store(tmp_path / "db"))
    r["job"] = {"kind": "sandbox", "status": "failed", "error": "A sandbox failure"}
    with pytest.raises(ValueError):
        context_for(r, ExplainRequest(**(payload(r) | {"scope": "author_error"})))


def test_admission_context_includes_saved_type_and_trust_without_oracle(tmp_path):
    store = Store(tmp_path / "db")
    r = record(store)
    r["content"]["trusted_ids"] = ["approved-source"]
    r["content"]["trust_reviewed"] = True
    r["content"]["questions"] = [
        {"query": "Which records?", "expected_node_ids": ["SECRET_ORACLE"]}
    ]
    ctx = context_for(r, ExplainRequest(**payload(r)))
    refs = {ref["id"]: ref for ref in ctx["evidence"]}
    assert json.loads(refs["producer-policy"]["text"])["trusted_ids"] == ["approved-source"]
    schema = json.loads(refs["declared-schema"]["text"])
    for name, definition in r["proposal"]["pack"]["types"]["nodes"].items():
        assert schema["type_settings"][name]["interfaces"] == definition.get("interfaces")
    assert "SECRET_ORACLE" not in json.dumps(ctx)
    assert refs["admission-behavior"]["kind"] == "engine_capability"


@pytest.mark.asyncio
async def test_instruction_only_save_allows_fresh_explanation_but_never_old_or_changed_sources(
    tmp_path,
):
    from context_graph.workbench.authoring import verify_proposal
    from context_graph.workbench.models import Content

    store = Store(tmp_path / "db")
    r = record(store)
    r["content"]["instruction"] = "Keep the account identity unchanged."
    r["proposal"]["facts"][0]["instruction_quote"] = r["content"]["instruction"]
    r["proposal"]["limitations"] = ["Review the current trust policy."]
    verify_proposal(Proposal.model_validate(r["proposal"]), Content.model_validate(r["content"]))
    r = store.put("alice", r, r["revision"], "fixture-with-instruction")
    seen = []

    async def explain(context):
        seen.append(context)
        return answer()

    app = create_app(database=store.path, operators={"alice": "alice"}, explainer=explain)
    async with client(app) as c:
        root = f"/admin/tenants/{r['id']}"
        content = copy.deepcopy(r["content"])
        content["instruction"] = "Preserve history and revise the requested policy."
        saved = await c.put(root, json={"revision": r["revision"], "content": content})
        assert saved.status_code == 200, saved.text
        current = saved.json()
        assert current["proposal_stale"] and current["explain_stale_allowed"]
        request = {"revision": current["revision"], "scope": "limitation", "index": 0}
        assert (await c.post(root + "/explain", json=request)).status_code == 200
        assert "has not been applied" in seen[-1]["proposal_status"]
        assert (
            await c.post(root + "/explain", json=request | {"revision": r["revision"]})
        ).status_code == 409
        content["sources"][0]["text"] += " Additional evidence changes the policy."
        changed = (
            await c.put(root, json={"revision": current["revision"], "content": content})
        ).json()
        assert not changed["explain_stale_allowed"]
        assert (
            await c.post(root + "/explain", json=request | {"revision": changed["revision"]})
        ).status_code == 409
        content["instruction"] += " Try again."
        changed = (
            await c.put(root, json={"revision": changed["revision"], "content": content})
        ).json()
        assert not changed["explain_stale_allowed"]


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["pack", "node", "edge"])
async def test_element_explanation_is_scoped_read_only_and_revision_bound(tmp_path, scope):
    path = tmp_path / "elements"
    store = Store(path)
    r = record(store)
    seen = []

    async def explain(context):
        seen.append(context)
        return {
            "kind": "supported",
            "claims": [
                {"text": "This describes the selected part of the pack.", "evidence": ["subject"]}
            ],
        }

    app = create_app(database=path, operators={"alice": "alice"}, explainer=explain)
    body = {
        "revision": r["revision"],
        "scope": scope,
        "index": 0,
        "question": "What does this represent?",
    }
    async with client(app) as c:
        response = await c.post(f"/admin/tenants/{r['id']}/explain", json=body)
        assert response.status_code == 200, response.text
        subject = json.loads(seen[0]["evidence"][0]["text"])
        pack = r["proposal"]["pack"]
        if scope == "pack":
            assert subject["pack"]["name"] == pack["pack"]["name"]
        else:
            section = pack["types"]["nodes" if scope == "node" else "edges"]
            name = sorted(section)[0]
            assert subject == {name: section[name]}
        assert store.get("alice", r["id"]) == r
        bad_index = await c.post(f"/admin/tenants/{r['id']}/explain", json={**body, "index": 200})
        assert bad_index.status_code == 422
        r["content"]["data_policy"] = "local_only"
        changed = store.put("alice", r, r["revision"], "consent")
        assert (await c.post(f"/admin/tenants/{r['id']}/explain", json=body)).status_code == 409
        assert (
            await c.post(
                f"/admin/tenants/{r['id']}/explain", json={**body, "revision": changed["revision"]}
            )
        ).status_code == 403
        assert len(seen) == 1


@pytest.mark.parametrize("scope", ["pack", "node", "edge"])
def test_element_unknown_answer_cannot_invent_an_engine_limit(scope):
    r = json.loads(FIXTURE.read_text())
    context = context_for(r, ExplainRequest(revision=1, scope=scope, index=0))
    unknown = verify_answer(
        {"kind": "unknown", "missing": ["Which records should this relationship connect?"]}, context
    )
    assert unknown.kind == "unknown"
    with pytest.raises(ValueError, match="not a verified engine limit"):
        verify_answer(
            {"kind": "engine_limit", "claims": [{"text": "Unsupported", "evidence": ["subject"]}]},
            context,
        )
