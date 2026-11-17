"""Read-only identity and lifecycle consequences from deterministic planner output."""

import copy
import json

import httpx
import pytest

from context_graph.workbench.api import create_app
from context_graph.workbench.decision_preview import DecisionOption, preview_options
from context_graph.workbench.explain import ExplainRequest, context_for
from context_graph.workbench.models import Content
from context_graph.workbench.store import Store


def scenario():
    contract = {
        "version": 1,
        "properties": {
            "account": {"type": "string", "required": True},
            "number": {"type": "string", "required": True},
            "service": {"type": "string", "required": True},
        },
    }
    key = {"account": "$.account", "number": "$.number"}
    pack = {
        "pack": {"name": "support", "version": "1.0.0", "requires": ["core>=1.1"]},
        "types": {
            "nodes": {
                "Case": {
                    "key": ["account", "number"],
                    "interfaces": ["Lifecycled"],
                    "properties": {"account": "string", "number": "string"},
                    "lifecycle": {"initial": "open", "states": ["open", "resolved"]},
                }
            }
        },
        "events": {
            name: {"payload_contract": contract, "handling": "processed"}
            for name in ["case.opened", "case.resolved"]
        },
        "projection": [
            {"event": "case.opened", "upsert": [{"type": "Case", "key": key}]},
            {
                "event": "case.resolved",
                "upsert": [{"type": "Case", "key": key}],
                "transition": {"type": "Case", "to": "resolved", "only_from": ["open"]},
            },
        ],
    }
    events = [
        {
            "event_type": "case.opened",
            "payload": {"account": account, "number": "42", "service": "checkout"},
        }
        for account in ["east", "west"]
    ]
    events.append(
        {
            "event_type": "case.resolved",
            "payload": {"account": "east", "number": "42", "service": "checkout"},
        }
    )
    content = Content(
        name="Support decisions",
        environment="test",
        data_policy="provider_allowed",
        redaction_confirmed=True,
        sources=[
            {
                "id": "scope",
                "kind": "specification",
                "name": "Account policy",
                "text": "Case numbers are unique only within an account.",
            },
            {
                "id": "legacy",
                "kind": "specification",
                "name": "Legacy policy",
                "text": (
                    "Case numbers are globally unique; "
                    "legacy guidance conflicts with account policy."
                ),
            },
            {
                "id": "events",
                "kind": "samples",
                "name": "Reviewed examples",
                "text": json.dumps(events),
            },
        ],
    )
    return {
        "content": content.model_dump(),
        "proposal": {
            "pack": json.loads(json.dumps(pack)),
            "facts": [],
            "limitations": [],
            "decisions": [
                {
                    "id": "identity",
                    "question": "Can Case number 42 belong to two accounts?",
                    "effect": "Separate accounts or combine histories.",
                }
            ],
        },
    }


def identity_options():
    same = {
        "kind": "identity",
        "node_type": "Case",
        "explanation": "Compare the supplied account examples.",
        "evidence": ["subject"],
    }
    return [
        DecisionOption(id="scoped", label="Keep accounts separate", **same),
        DecisionOption(
            id="global",
            label="Use the number across accounts",
            **same,
            edits=[
                {"path": ["types", "nodes", "Case", "key"], "value": ["number"]},
                *[
                    {"path": ["projection", i, "upsert", 0, "key"], "value": {"number": "$.number"}}
                    for i in [0, 1]
                ],
            ],
        ),
    ]


def lifecycle_option():
    return DecisionOption(
        id="repeat",
        label="Allow resolved cases too",
        explanation="Request the transition from open or resolved.",
        evidence=["subject"],
        kind="lifecycle",
        node_type="Case",
        edits=[
            {"path": ["projection", 1, "transition", "only_from"], "value": ["open", "resolved"]}
        ],
    )


def test_identity_preview_counts_without_mutating_inputs_or_oracles():
    r = scenario()
    saved = copy.deepcopy(r)
    results = preview_options(r, identity_options())
    assert all(result["available"] for result in results)
    assert results[0]["after"]["record_count"] == 2
    assert results[1]["before"]["record_count"] == 2
    assert results[1]["after"]["record_count"] == 1
    assert results[1]["after"]["records"][0]["samples"] == [1, 2, 3]
    assert r == saved


def test_lifecycle_preview_shows_guard_not_executed_success_and_requires_coverage():
    r = scenario()
    option = lifecycle_option()
    result = preview_options(r, [option])[0]
    assert result["available"]
    assert result["after"]["transitions"][0]["only_from"] == ("open", "resolved")
    assert result["label"] == "Planned, not executed"
    r["content"]["sources"][-1]["text"] = json.dumps(
        json.loads(r["content"]["sources"][-1]["text"])[:2]
    )
    result = preview_options(r, [option])[0]
    assert not result["available"]
    assert "not covered" in result["detail"]
    del r["proposal"]["pack"]["types"]["nodes"]["Case"]["lifecycle"]
    assert not preview_options(r, [option])[0]["available"]


@pytest.mark.parametrize(
    "path,value",
    [
        (["pack", "name"], "other"),
        (["retrieval"], {}),
        (["projection", 0, "event"], "other"),
        (["types", "nodes", "Case", "key"], ["missing"]),
    ],
)
def test_unsupported_or_invalid_candidate_is_unavailable(path, value):
    option = identity_options()[1].model_copy(update={"edits": []})
    option = DecisionOption.model_validate(
        {**option.model_dump(), "edits": [{"path": path, "value": value}]}
    )
    assert not preview_options(scenario(), [option])[0]["available"]


def test_decision_context_keeps_conflicting_source_excerpts():
    context = context_for(scenario(), ExplainRequest(revision=1, scope="decision", index=0))
    sources = {item.get("source_id") for item in context["evidence"]}
    assert {"scope", "legacy"} <= sources


@pytest.mark.asyncio
async def test_endpoint_scopes_options_and_rejects_stale_choice_context(tmp_path):
    r = scenario()
    store = Store(tmp_path / "drafts")
    draft = store.create("operator", r["content"])
    draft["proposal"] = r["proposal"]
    draft = store.put("operator", draft, 1, "fixture")

    async def explain(context):
        return {
            "kind": "supported",
            "claims": [
                {
                    "text": (
                        "Account policies disagree. Compare these sample effects before choosing."
                    ),
                    "evidence": ["subject"],
                }
            ],
            "options": [option.model_dump() for option in identity_options()],
        }

    app = create_app(database=store.path, operators={"token": "operator"}, explainer=explain)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer token"},
    ) as client:
        path = f"/admin/tenants/{draft['id']}/explain"
        body = {"revision": draft["revision"], "scope": "decision", "index": 0}
        response = await client.post(path, json=body)
        assert response.status_code == 200, response.text
        assert response.json()["option_previews"][1]["after"]["record_count"] == 1
        assert store.get("operator", draft["id"]) == draft
        changed = copy.deepcopy(draft)
        changed["content"]["sources"][0]["text"] += " Corrected policy."
        store.put("operator", changed, draft["revision"], "source-edit")
        assert (await client.post(path, json=body)).status_code == 409


def test_options_require_decision_scope_and_server_evidence():
    from context_graph.workbench.explain import verify_answer

    context = context_for(scenario(), ExplainRequest(revision=1, scope="decision", index=0))
    raw = {
        "kind": "supported",
        "claims": [{"text": "Compare the examples.", "evidence": ["subject"]}],
        "options": [identity_options()[0].model_dump()],
    }
    assert verify_answer(raw, context).options
    with pytest.raises(ValueError, match="recorded decision"):
        verify_answer(raw, {**context, "scope": "pack"})
    raw["options"][0]["evidence"] = ["invented-source"]
    with pytest.raises(ValueError, match="outside this request"):
        verify_answer(raw, context)


def test_decision_preview_is_bounded_and_unavailable_without_samples():
    r = scenario()
    r["content"]["sources"][-1]["text"] = "[]"
    assert not preview_options(r, identity_options())[0]["available"]
    original = json.loads(scenario()["content"]["sources"][-1]["text"])
    r["content"]["sources"][-1]["text"] = json.dumps(original * 8)
    result = preview_options(r, identity_options())[0]
    assert not result["available"]
    assert "at most 20" in result["detail"]


@pytest.mark.asyncio
async def test_timed_out_planner_holds_capacity_until_read_only_work_finishes(
    tmp_path, monkeypatch
):
    import asyncio
    import threading

    import context_graph.workbench.api as api

    r = scenario()
    store = Store(tmp_path / "drafts")
    draft = store.create("operator", r["content"])
    draft["proposal"] = r["proposal"]
    draft = store.put("operator", draft, 1, "fixture")
    release = threading.Event()

    def slow_preview(*_):
        release.wait(timeout=2)
        return []

    monkeypatch.setattr(api, "preview_options", slow_preview)

    async def explain(_):
        return {"kind": "supported", "claims": [{"text": "Example.", "evidence": ["subject"]}]}

    app = create_app(
        database=store.path,
        operators={"token": "operator"},
        explainer=explain,
        explain_timeout=0.03,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer token"},
    ) as client:
        path = f"/admin/tenants/{draft['id']}/explain"
        body = {"revision": draft["revision"], "scope": "decision", "index": 0}
        try:
            assert (await client.post(path, json=body)).status_code == 504
            assert (await client.post(path, json=body)).status_code == 429
        finally:
            release.set()
        await asyncio.sleep(0.05)
        assert (await client.post(path, json=body)).status_code == 200
        assert store.get("operator", draft["id"]) == draft


def test_preview_names_records_and_separates_provenance_from_business_links():
    result = preview_options(scenario(), identity_options())[0]
    assert result["after"]["records"][0]["identity"] == {"account": "east", "number": "42"}
    assert result["after"]["records"][0]["events"] == ["case.opened", "case.resolved"]
    assert result["after"]["relationships"] == []
    assert len(result["after"]["provenance_relationships"]) == 3
