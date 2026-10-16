"""Preflight the authored completion oracle against actual projection/retrieval.

Local scripted proposals test fixture consistency, not live model usefulness.
"""

import json
from pathlib import Path

import pytest
from engram_goal03_implementation_demo import assert_retrieval_policy, fixture_observations
from engram_pilot_completion_fixtures import p02_history

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import Event
from context_graph.domain.pack_extraction import extraction_profiles
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.projection import event_to_node
from context_graph.ontology import load_registry
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.worker.pack_projection import apply_plan


@pytest.mark.parametrize("story", ["p02", "mixed-verification"])
async def test_completion_contracts_projection_and_independent_read_expectations(story):
    if story == "p02":
        group = p02_history("p02-fixture-preflight")
    else:
        path = Path(__file__).resolve().parents[2] / "docs/pilot/pilot-p01-1016-07-journeys.json"
        group = json.loads(path.read_text())["groups"][0]
    registry = load_registry(["pdlc"])
    graph = MemoryGraphStore()
    projector = PackProjector(registry, frozenset(s["request"]["agent_id"] for s in group["steps"]))
    retriever = ArtifactRetriever(
        graph,
        registry,
        default_max_depth=6,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )

    async def query(q):
        response = await retriever.retrieve(
            ArtifactQuery(
                q["text"],
                seed_node_ids=tuple(q["seeds"]),
                intent=q["intent"],
                max_depth=q["max_depth"],
            )
        )
        answer = response.model_dump(mode="json")
        actual = set(answer["nodes"])
        assert set(q["required"]) <= actual, (q["scenario"], set(q["required"]) - actual)
        assert not set(q["forbidden"]) & actual, (q["scenario"], actual)
        if q.get("exact"):
            assert actual == set(q["required"]), (q["scenario"], actual - set(q["required"]))
        assert_retrieval_policy(answer, q)
        for key, count in q.get("expected_channels", {}).items():
            assert answer["meta"]["retrieval_channels"].get(key) == count

    for index, step in enumerate(group["steps"]):
        if step["expected_status"] >= 400 or step.get("duplicate"):
            continue
        record = step["request"]
        event = Event.model_validate_json(json.dumps(record)).model_copy(
            update={"global_position": f"{index + 1}-0"}
        )
        contract = registry.event_types[event.event_type].definition.payload_contract
        if contract:
            contract.validate_payload(record["payload"])
        await graph.merge_event_node(event_to_node(event))
        plan = projector.plan(event, record)
        await apply_plan(graph, plan, 1000)
        actual = {(kind, source[1], target[1]) for source, kind, target in graph.edges}
        assert set(map(tuple, step["expected_edges"])) <= actual
        for nid in fixture_observations(step):
            assert ("DERIVED_FROM", nid, str(event.event_id)) in actual
        if step.get("required_proposed_edges"):
            from context_graph.domain.pack_extraction import KnownItem

            ids = group["ids"]
            profile = extraction_profiles(
                registry, max_nodes=10, max_links=10, max_text_chars=4000
            )[0]
            proposed = profile.plan(
                {
                    "nodes": [],
                    "links": [
                        dict(
                            type="VERIFIES",
                            **{"from": ids["planned_case"], "to": ids["proposed"]},
                            confidence=0.6,
                        )
                    ],
                },
                event,
                trusted=True,
                known=[
                    KnownItem(ids["planned_case"], "TestCase", "planned"),
                    KnownItem(ids["proposed"], "Requirement", "proposed"),
                ],
            )
            assert proposed.accepted_links == 1
            await apply_plan(graph, proposed.plan, 1000)
        for q in group["queries"]:
            if q.get("after_scenario") == step["scenario"]:
                await query(q)
    for q in group["queries"]:
        if not q.get("after_scenario"):
            await query(q)


def test_recovery_receipt_requires_exact_source_window_and_owner(tmp_path):
    from copy import deepcopy
    from types import SimpleNamespace

    from engram_pilot_completion_fixtures import (
        p03_user_stories,
        recovery_documents,
        recovery_input_hash,
        verified_recovered_user_receipt,
    )
    from engram_pilot_first_run import build_plan, material_node

    from context_graph.domain.user_extraction import prepare_extraction_receipt

    original = next(g for g in p03_user_stories("recovery-unit") if g["name"] == "user-paraphrase")
    inputs = [s["request"] for s in original["steps"]]
    state = {"events": [], "nodes": []}
    for i, request in enumerate(inputs):
        event = Event.model_validate(request, strict=False)
        stored = event.model_dump(mode="json")
        stored["payload"] = request["payload"]
        state["events"].append([request["event_id"], stored])
        props = event.model_dump(mode="json")
        props["global_position"] = f"{i + 1}-0"
        state["nodes"].append(["Event", request["event_id"], props])
    group = {
        **original,
        "steps": [],
        "recover_user_inputs": inputs,
        "recovery_input_hash": recovery_input_hash(state, inputs),
    }
    path = tmp_path / "journeys.json"
    path.write_text(json.dumps({"groups": [group], "coverage": "exact pending recovery"}))
    args = SimpleNamespace(run_id="recovery-unit", journey_file=path, journeys_only=True)
    assert build_plan(args)["execution_mode"] == "selected-journeys"
    correction_recovery = {**group, "user_story": False, "user_correction": True}
    path.write_text(
        json.dumps({"groups": [correction_recovery], "coverage": "correction recovery"})
    )
    assert build_plan(args)["execution_mode"] == "selected-journeys"
    invalid = deepcopy(group)
    invalid["owner"] = "other-owner"
    path.write_text(json.dumps({"groups": [invalid], "coverage": "invalid"}))
    with pytest.raises(ValueError, match="owner/session"):
        build_plan(args)

    documents = recovery_documents(state, inputs)
    events = [Event.model_validate(d, strict=False) for d in documents]
    receipt = prepare_extraction_receipt(events[-1], events, documents, {})
    receipt["status"] = "applied"
    state["nodes"][-1][2].update(
        user_extraction_receipt=receipt,
        user_extraction_owner=receipt["owner"],
        user_extraction_status="applied",
    )
    assert verified_recovered_user_receipt(state, group) == receipt
    verification = {**group, "verify_user_inputs": group["recover_user_inputs"]}
    verification.pop("recover_user_inputs")
    path.write_text(json.dumps({"groups": [verification], "coverage": "retained verification"}))
    assert build_plan(args)["execution_mode"] == "selected-retained-reads"
    assert verified_recovered_user_receipt(state, verification) == receipt
    path.write_text(json.dumps({"groups": [{**verification, **group}], "coverage": "invalid"}))
    with pytest.raises(ValueError, match="both recover and verify"):
        build_plan(args)
    source_before = material_node(state["nodes"][-1], {inputs[-1]["event_id"]})
    ordinary = material_node(state["nodes"][-1])
    assert "user_extraction_receipt" in ordinary
    assert "user_extraction_receipt" not in source_before
    assert "agent_id" in source_before
    for field, value in (
        ("owner", "user:foreign"),
        ("input_hash", "wrong"),
        ("input_event_ids", [inputs[-1]["event_id"]]),
    ):
        changed = deepcopy(state)
        changed["nodes"][-1][2]["user_extraction_receipt"][field] = value
        with pytest.raises(ValueError):
            verified_recovered_user_receipt(changed, group)
    changed = deepcopy(state)
    changed["events"][0][1]["payload"]["content"] = "altered source"
    with pytest.raises(ValueError, match="source differs"):
        recovery_documents(changed, inputs)

    wrong_private_owner = deepcopy(state)
    wrong_private_owner["nodes"][-1][2]["user_extraction_owner"] = "user:foreign"
    with pytest.raises(ValueError, match="frozen source window"):
        verified_recovered_user_receipt(wrong_private_owner, group)


def test_recovery_validates_decoded_spanner_receipt_and_rejects_tampering():
    from copy import deepcopy

    from engram_pilot_completion_fixtures import (
        p03_user_stories,
        recovery_documents,
        recovery_input_hash,
        verified_recovered_user_receipt,
    )

    from context_graph.adapters.spanner.log import json_param
    from context_graph.domain.user_extraction import prepare_extraction_receipt

    original = next(g for g in p03_user_stories("receipt-float") if g["name"] == "user-paraphrase")
    inputs = [s["request"] for s in original["steps"]]
    state = {"events": [], "nodes": []}
    for i, request in enumerate(inputs):
        event = Event.model_validate(request, strict=False)
        document = {**event.model_dump(mode="json"), "payload": request["payload"]}
        state["events"].append(
            [
                request["event_id"],
                json_param(document),
                json_param({"binding_id": "test-binding", "accepted_epoch": 53}),
            ]
        )
        props = {**event.model_dump(mode="json"), "global_position": f"{i + 1}-0"}
        state["nodes"].append(["Event", request["event_id"], json_param(props)])
    documents = recovery_documents(state, inputs)
    assert all(d["acceptance"]["binding_id"] == "test-binding" for d in documents)
    events = [Event.model_validate(d, strict=False) for d in documents]
    raw = dict(
        preferences=[
            dict(
                category="communication",
                key="concise",
                polarity="positive",
                confidence=0.95,
                strength=0.9,
                source="explicit",
                source_quote="Long walls of text are hard for me to use",
            )
        ]
    )
    receipt = prepare_extraction_receipt(events[-1], events, documents, raw)
    receipt["status"] = "applied"
    props.update(
        user_extraction_receipt=receipt,
        user_extraction_owner=receipt["owner"],
        user_extraction_status="applied",
    )
    state["nodes"][-1][2] = json_param(props)
    group = {
        **original,
        "recover_user_inputs": inputs,
        "recovery_input_hash": recovery_input_hash(state, inputs),
    }
    assert verified_recovered_user_receipt(state, group)["result_hash"] == receipt["result_hash"]
    saved = json.loads(json.dumps(state))
    assert verified_recovered_user_receipt(saved, group)["result_hash"] == receipt["result_hash"]
    changed = deepcopy(props)
    changed["user_extraction_receipt"]["result"]["preferences"][0]["strength"] = 0.2
    state["nodes"][-1][2] = json_param(changed)
    with pytest.raises(ValueError, match="result hash differs"):
        verified_recovered_user_receipt(state, group)

    changed = deepcopy(props)
    changed["user_extraction_status"] = "prepared"
    state["nodes"][-1][2] = json_param(changed)
    with pytest.raises(ValueError, match="frozen source window"):
        verified_recovered_user_receipt(state, group)


def test_explicit_correction_has_exact_identity_and_receipt_derived_profile_changes():
    from copy import deepcopy
    from datetime import UTC, datetime
    from uuid import UUID

    from engram_pilot_completion_fixtures import correction_expected_updates

    from context_graph.domain.user_extraction import artifact_identity, prepare_extraction_receipt

    owner = "ishan-correction-unit"
    negative = "I no longer prefer short bullet-point actions during incident response"
    fields = dict(
        category="communication",
        key="incident-short",
        context="incident",
        polarity="negative",
        about_entity="incident communication",
        scope="global",
        scope_id=None,
    )
    new_id = artifact_identity("Preference", "user:" + owner, fields)
    events = [
        Event(
            event_id=UUID(int=i),
            event_type=kind,
            occurred_at=datetime(2026, 10, 16, 10, tzinfo=UTC),
            session_id="correction-test",
            agent_id=owner,
            trace_id="test",
            payload_ref="test",
        )
        for i, kind in ((201, "observation.input"), (202, "system.session_end"))
    ]
    requests = [e.model_dump(mode="json") for e in events]
    requests[0]["payload"] = dict(
        content=negative,
        preference_corrections=[
            dict(
                previous_preference_id="preference:old",
                replacement_key=fields["key"],
                replacement_polarity="negative",
                context="incident",
            )
        ],
    )
    requests[1]["payload"] = {}
    documents = [{**r, "global_position": f"{i + 1}-0"} for i, r in enumerate(requests)]
    events = [Event.model_validate(d, strict=False) for d in documents]
    receipt = prepare_extraction_receipt(
        events[-1],
        events,
        documents,
        dict(
            model_id="gpt-6-luna",
            preferences=[
                dict(
                    **fields,
                    strength=0.9,
                    confidence=0.95,
                    source="explicit",
                    source_quote=negative,
                )
            ],
            persona=dict(name="Ishan", source_quote=negative, communication_style="updated"),
        ),
    )
    receipt["status"] = "applied"
    profile_id = "profile:user:" + owner
    before = dict(
        nodes=[
            ["Preference", "preference:old", dict(user_id="user:" + owner, polarity="positive")],
            [
                "UserProfile",
                profile_id,
                dict(
                    user_id="user:" + owner,
                    created_at="original",
                    support_event_ids=["original-source"],
                    display_name="Ishan",
                    communication_style="original",
                    technical_level=None,
                ),
            ],
        ]
    )
    after = deepcopy(before)
    after["events"] = [[r["event_id"], r] for r in requests]
    for d in documents:
        after["nodes"].append(["Event", d["event_id"], deepcopy(d)])
    after["nodes"][-1][2].update(
        user_extraction_receipt=receipt,
        user_extraction_owner="user:" + owner,
        user_extraction_status="applied",
    )
    source = requests[0]["event_id"]
    after["nodes"][0][2]["superseded_by"] = new_id
    after["nodes"].append(
        [
            "Preference",
            new_id,
            dict(
                user_id="user:" + owner,
                support_event_ids=[source],
                observation_count=1,
                **{
                    k: receipt["result"]["preferences"][0][k]
                    for k in (
                        "category",
                        "key",
                        "polarity",
                        "context",
                        "scope",
                        "scope_id",
                        "strength",
                        "confidence",
                        "source",
                    )
                },
            ),
        ]
    )
    after["edges"] = [
        [
            "Preference",
            new_id,
            "SUPERSEDES",
            "Preference",
            "preference:old",
            dict(source_event_id=source),
        ],
        [
            "Preference",
            new_id,
            "DERIVED_FROM",
            "Event",
            source,
            dict(evidence_quote=negative, extraction_event_id=requests[-1]["event_id"]),
        ],
        ["Preference", new_id, "ABOUT", "Entity", "entity:" + fields["about_entity"], {}],
        ["Preference", "preference:old", "DERIVED_FROM", "Event", source, {}],
    ]
    group = dict(
        steps=[dict(request=r) for r in requests],
        owner=owner,
        expected_previous="preference:old",
        expected_replacement=new_id,
        identity_fields=fields,
        required_negative_quote=negative,
    )
    updates, actual = correction_expected_updates(before, after, group)
    assert actual == receipt
    assert updates[("Preference", "preference:old")] == {
        **before["nodes"][0][2],
        "superseded_by": new_id,
    }
    expected_profile = updates[("UserProfile", profile_id)]
    assert expected_profile["support_event_ids"] == sorted(["original-source", source])
    assert expected_profile["created_at"] == "original"
    assert expected_profile["communication_style"] == "updated"
    assert expected_profile["updated_at"] == receipt["effective_at"]
    for bad in (
        {**group, "expected_replacement": "preference:invented"},
        {**group, "identity_fields": {**fields, "about_entity": "other-context"}},
        {**group, "required_negative_quote": "invented unsupported evidence"},
    ):
        with pytest.raises(ValueError):
            correction_expected_updates(before, after, bad)

    changed = deepcopy(after)
    changed["nodes"][-1][2]["polarity"] = "positive"
    with pytest.raises(ValueError, match="owner/source/count differs"):
        correction_expected_updates(before, changed, group)


def test_provider_observer_matches_quoted_source_without_transport_escaping():
    from engram_pilot_first_run import provider_prompt_text

    source = 'A declared context is {"key": "incident", "context": "positive label"}.'
    messages = [{"role": "system", "content": "<conversation>" + source + "</conversation>"}]
    assert source not in json.dumps(messages)
    assert source in provider_prompt_text(messages)
    assert "unrelated source" not in provider_prompt_text(messages)
