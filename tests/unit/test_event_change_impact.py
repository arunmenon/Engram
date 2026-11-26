"""Event contract edits need producer-impact diagnostics and version checks."""

import pytest

from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.domain.pack_versioning import classify_change
from tests.unit.test_pack_admission import core, unfamiliar

EVENT = "telemetry.reading.recorded"


def baseline():
    return OntologyRegistry([core(), unfamiliar()])


def revised(old, changes, version="1.1.0"):
    data = old.pack("telemetry").model_dump()
    data["pack"]["version"] = version
    for path, value in changes:
        parent = data
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = value
    return OntologyRegistry([core(), Pack.model_validate(data)])


def policy(registry):
    return compile_admission_policy(resolve_bundle(registry))


def test_required_field_change_warns_and_requires_major_without_rebuilding_graph():
    old = baseline()
    new = revised(
        old, [(("events", EVENT, "payload_contract", "properties", "note", "required"), True)]
    )
    payload = {"meter": "west", "reading": 1.25}
    assert policy(old).decide(EVENT, payload).allowed
    assert not policy(new).decide(EVENT, payload).allowed
    plan = classify_change(old, new)
    assert plan.admission_changes == {EVENT: "breaking"}
    assert plan.kind == "additive"
    assert not plan.replay_event_types
    assert any("new event" in reason and "rejected" in reason for reason in plan.reasons)
    assert any("note" in reason and "now required" in reason for reason in plan.reasons)
    assert any("major version" in problem for problem in plan.version_problems)


def test_making_required_field_optional_is_compatible():
    old = revised(
        baseline(),
        [(("events", EVENT, "payload_contract", "properties", "note", "required"), True)],
        version="1.0.0",
    )
    new = revised(
        old, [(("events", EVENT, "payload_contract", "properties", "note", "required"), False)]
    )
    payload = {"meter": "west", "reading": 1.25}
    assert not policy(old).decide(EVENT, payload).allowed
    assert policy(new).decide(EVENT, payload).allowed
    plan = classify_change(old, new)
    assert plan.admission_changes == {EVENT: "additive"}
    assert not plan.version_problems
    assert not plan.replay_event_types


@pytest.mark.parametrize(
    ("before", "after", "value"),
    [
        ({"type": "string", "min_length": 3}, {"type": "string", "min_length": 1}, "a"),
        ({"type": "string", "max_length": 2}, {"type": "string", "max_length": 4}, "abc"),
        ({"type": "string", "enum": ["a"]}, {"type": "string", "enum": ["a", "b"]}, "b"),
        ({"type": "string"}, {"type": "string", "nullable": True}, None),
        ({"type": "number", "minimum": 10}, {"type": "number", "minimum": 0}, 5),
        ({"type": "integer", "maximum": 10}, {"type": "integer", "maximum": 20}, 15),
        (
            {"type": "array", "items": {"type": "string"}, "min_length": 2},
            {"type": "array", "items": {"type": "string"}},
            [],
        ),
        (
            {"type": "array", "items": {"type": "string"}, "max_length": 1},
            {"type": "array", "items": {"type": "string"}, "max_length": 2},
            ["a", "b"],
        ),
        (
            {"type": "object", "properties": {"x": {"type": "integer", "required": True}}},
            {"type": "object", "properties": {"x": {"type": "integer"}}},
            {},
        ),
        ({"type": "object", "additional_fields": "forbid"}, {"type": "object"}, {"x": 1}),
        (
            {"type": "array", "items": {"type": "string", "enum": ["a"]}},
            {"type": "array", "items": {"type": "string", "enum": ["a", "b"]}},
            ["b"],
        ),
    ],
)
def test_proven_relaxations_and_reverse_tightenings(before, after, value):
    path = ("events", EVENT, "payload_contract", "properties", "note")
    old = revised(baseline(), [(path, before)], version="1.0.0")
    new = revised(old, [(path, after)])
    payload = {"meter": "west", "reading": 1.25, "note": value}
    assert not policy(old).decide(EVENT, payload).allowed
    assert policy(new).decide(EVENT, payload).allowed
    widening = classify_change(old, new)
    assert widening.admission_changes == {EVENT: "additive"}
    assert not widening.version_problems
    reverse = revised(new, [(path, before)], version="1.2.0")
    narrowing = classify_change(new, reverse)
    assert narrowing.admission_changes == {EVENT: "breaking"}
    assert any("major version" in p for p in narrowing.version_problems)
    assert not widening.replay_event_types and not narrowing.replay_event_types


def test_equivalent_enum_order_and_documentation_do_not_warn_about_rejection():
    path = ("events", EVENT, "payload_contract", "properties", "note", "enum")
    old = revised(baseline(), [(path, ["a", "b"])], version="1.0.0")
    new = revised(old, [(path, ["b", "a"]), (("events", EVENT, "note"), "Clearer description")])
    plan = classify_change(old, new)
    assert not plan.admission_changes
    assert not any("rejected" in reason for reason in plan.reasons)


@pytest.mark.parametrize(
    "old_mode,new_mode,kind",
    [("ledger_only", "unsupported", "breaking"), ("unsupported", "ledger_only", "additive")],
)
def test_event_handling_changes_are_visible_without_a_graph_rewrite(old_mode, new_mode, kind):
    old = OntologyRegistry([core(), unfamiliar(handling=old_mode, projection=False)])
    new = revised(old, [(("events", EVENT, "handling"), new_mode)])
    assert policy(old).decide(EVENT, {"meter": "west", "reading": 1.0}).handling == old_mode
    assert policy(new).decide(EVENT, {"meter": "west", "reading": 1.0}).handling == new_mode
    plan = classify_change(old, new)
    assert plan.admission_changes == {EVENT: kind}
    assert plan.kind == "additive" and not plan.replay_event_types
    assert bool(plan.version_problems) == (kind == "breaking")


def test_domain_contract_addition_enables_admission_and_removal_disables_it():
    old = OntologyRegistry(
        [core(), unfamiliar(handling="ledger_only", projection=False, contract=False)]
    )
    data = unfamiliar(handling="ledger_only", projection=False).model_dump()
    data["pack"]["version"] = "1.1.0"
    new = OntologyRegistry([core(), Pack.model_validate(data)])
    payload = {"meter": "west", "reading": 1.25}
    assert not policy(old).decide(EVENT, payload).allowed
    assert policy(new).decide(EVENT, payload).allowed
    assert classify_change(old, new).admission_changes == {EVENT: "additive"}
    removed = revised(new, [(("events", EVENT, "payload_contract"), None)], version="1.2.0")
    plan = classify_change(new, removed)
    assert plan.admission_changes == {EVENT: "breaking"}
    assert any("major version" in p for p in plan.version_problems)


def test_explicit_inferred_handling_is_not_a_new_rejection():
    old = baseline()
    new = revised(old, [(("events", EVENT, "handling"), "processed")])
    assert policy(old).decide(EVENT, {"meter": "west", "reading": 1.25}) == policy(new).decide(
        EVENT, {"meter": "west", "reading": 1.25}
    )
    assert not classify_change(old, new).admission_changes


@pytest.mark.parametrize(
    "old_extra, new_extra, field_change, payload, expected",
    [
        ("preserve", "preserve", {"tag": {"type": "string"}}, {"tag": 7}, "breaking"),
        ("forbid", "forbid", {"tag": {"type": "string"}}, {"tag": "ok"}, "additive"),
        ("preserve", "forbid", {}, {"extra": 7}, "breaking"),
        ("forbid", "preserve", {}, {"extra": 7}, "additive"),
    ],
)
def test_extra_fields_and_optional_new_validation(
    old_extra, new_extra, field_change, payload, expected
):
    old = revised(
        baseline(),
        [(("events", EVENT, "payload_contract", "additional_fields"), old_extra)],
        version="1.0.0",
    )
    fields = old.pack("telemetry").events[EVENT].payload_contract.model_dump()["properties"]
    fields.update(field_change)
    new = revised(
        old,
        [
            (("events", EVENT, "payload_contract", "additional_fields"), new_extra),
            (("events", EVENT, "payload_contract", "properties"), fields),
        ],
    )
    sample = {"meter": "west", "reading": 1.25, **payload}
    assert policy(old).decide(EVENT, sample).allowed != policy(new).decide(EVENT, sample).allowed
    assert classify_change(old, new).admission_changes == {EVENT: expected}


def test_core_contract_addition_and_removal_have_distinct_compatibility():
    old = OntologyRegistry([core()])
    event = "tool.execute"
    data = old.pack("core").model_dump()
    data["pack"]["version"] = "1.2.0"
    data["events"][event]["payload_contract"] = {
        "properties": {"merchant": {"type": "string", "required": True}}
    }
    new = OntologyRegistry([Pack.model_validate(data)])
    assert policy(old).decide(event, {}).allowed
    assert not policy(new).decide(event, {}).allowed
    plan = classify_change(old, new)
    assert plan.admission_changes == {event: "breaking"}
    assert any("major version" in p for p in plan.version_problems)
    data["pack"]["version"] = "1.3.0"
    data["events"][event]["payload_contract"] = None
    loosened = OntologyRegistry([Pack.model_validate(data)])
    assert classify_change(new, loosened).admission_changes == {event: "additive"}


def test_declaring_validation_for_a_previously_open_core_event_is_detected():
    data = core().model_dump()
    data["open_event_namespaces"] = ["tool"]
    old = OntologyRegistry([Pack.model_validate(data)])
    data["pack"]["version"] = "1.2.0"
    event = "tool.extra"
    data["events"][event] = {
        "payload_contract": {"properties": {"merchant": {"type": "string", "required": True}}}
    }
    new = OntologyRegistry([Pack.model_validate(data)])
    assert policy(old).decide(event, {}).allowed
    assert not policy(new).decide(event, {}).allowed
    plan = classify_change(old, new)
    assert plan.admission_changes == {event: "breaking"}
    assert any("major version" in p for p in plan.version_problems)


@pytest.mark.parametrize(
    "old_version,new_version,allowed",
    [("0.1.0", "0.1.1", False), ("0.1.0", "0.2.0", True), ("1.0.0", "2.0.0", True)],
)
def test_admission_version_requirements_preserve_pre_one_rules(old_version, new_version, allowed):
    old = revised(baseline(), [], version=old_version)
    new = revised(
        old,
        [(("events", EVENT, "payload_contract", "properties", "note", "required"), True)],
        version=new_version,
    )
    assert bool(classify_change(old, new).version_problems) is not allowed


def test_integer_to_finite_number_is_conservatively_incompatible():
    path = ("events", EVENT, "payload_contract", "properties", "note")
    old = revised(baseline(), [(path, {"type": "integer"})], version="1.0.0")
    new = revised(old, [(path, {"type": "number"})])
    payload = {"meter": "west", "reading": 1.25, "note": 10**400}
    assert policy(old).decide(EVENT, payload).allowed
    assert not policy(new).decide(EVENT, payload).allowed
    assert classify_change(old, new).admission_changes == {EVENT: "breaking"}


async def test_version_gate_preserves_existing_graph_and_does_not_replay(monkeypatch):
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.ontology.rebuild import project_ledger
    from context_graph.ontology.versioning import (
        OntologyChangeRefusedError,
        read_state,
        reconcile,
        record_state,
    )
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from tests.fixtures.events import make_event

    old, log, graph = baseline(), MemoryEventLog(), MemoryGraphStore()
    event = make_event(event_type=EVENT)
    payload = {"meter": "west", "reading": 1.25}
    await log.append(event, payload)
    await project_ledger(log, graph, PackProjector(old, frozenset()), Settings(), batch_size=2)
    await record_state(graph, old, applied="initial")
    saved = await read_state(graph)
    records = await graph.get_nodes([NodeRef("Meter", "Meter:west")])
    source = await log.get_documents([str(event.event_id)])

    async def unexpected_replay(*args, **kwargs):
        raise AssertionError("admission-only change must not replay history")

    monkeypatch.setattr(log, "read_after", unexpected_replay)
    path = ("events", EVENT, "payload_contract", "properties", "note", "required")
    minor = revised(old, [(path, True)])
    options = {"allow_breaking": False, "batch_size": 2, "lookup_limit": 100}
    with pytest.raises(OntologyChangeRefusedError, match="major version"):
        await reconcile(graph, log, PackProjector(minor, frozenset()), **options)
    assert await read_state(graph) == saved
    major = revised(old, [(path, True)], version="2.0.0")
    plan = await reconcile(graph, log, PackProjector(major, frozenset()), **options)
    assert plan.kind == "additive"
    assert plan.admission_changes == {EVENT: "breaking"}
    assert await graph.get_nodes([NodeRef("Meter", "Meter:west")]) == records
    assert await log.get_documents([str(event.event_id)]) == source


async def test_existing_status_api_exposes_compatibility_diagnostics():
    import httpx
    from fastapi import FastAPI

    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.api.routes.ontology import router
    from context_graph.ontology.versioning import record_state
    from context_graph.settings import Settings

    old, graph = baseline(), MemoryGraphStore()
    await record_state(graph, old, applied="initial")
    new = revised(
        old, [(("events", EVENT, "payload_contract", "properties", "note", "required"), True)]
    )
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.state.ontology, app.state.settings, app.state.graph_store = new, Settings(), graph
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/ontology")
    assert response.status_code == 200
    change = response.json()["change"]
    assert change["admission_changes"] == {EVENT: "breaking"}
    assert any("note" in reason and "now required" in reason for reason in change["reasons"])
    assert change["version_problems"]


@pytest.mark.parametrize("with_contract", [True, False])
def test_moving_core_event_to_domain_pack_cannot_understate_new_rejections(with_contract):
    core_data, domain_data = core().model_dump(), unfamiliar().model_dump()
    core_data["open_event_namespaces"] = []
    old = OntologyRegistry([Pack.model_validate(core_data), Pack.model_validate(domain_data)])
    event = "tool.execute"
    del core_data["events"][event]
    core_data["pack"]["version"] = "2.0.0"
    domain_data["pack"]["version"] = "1.1.0"
    domain_data["events"][event] = (
        {"payload_contract": {"properties": {"meter": {"type": "string", "required": True}}}}
        if with_contract
        else {}
    )
    domain_data["projection"].append(
        {"event": event, "upsert": [{"type": "Meter", "key": {"meter": "$.meter"}}]}
    )
    new = OntologyRegistry([Pack.model_validate(core_data), Pack.model_validate(domain_data)])
    assert policy(old).decide(event, {}).allowed
    assert not policy(new).decide(event, {}).allowed
    plan = classify_change(old, new)
    assert plan.admission_changes[event] == "breaking"
    assert any("telemetry" in p and "major version" in p for p in plan.version_problems)
    assert any("owner changed from core to telemetry" in reason for reason in plan.reasons)


def test_enum_length_inclusion_uses_values_accepted_by_real_validator():
    path = ("events", EVENT, "payload_contract", "properties", "note")
    old = revised(
        baseline(),
        [(path, {"type": "string", "enum": ["a", "too long"], "max_length": 1})],
        version="1.0.0",
    )
    new = revised(old, [(path, {"type": "string", "enum": ["a"], "max_length": 1})])
    payload = {"meter": "west", "reading": 1.25}
    assert policy(old).decide(EVENT, {**payload, "note": "a"}).allowed
    assert not policy(old).decide(EVENT, {**payload, "note": "too long"}).allowed
    assert policy(new).decide(EVENT, {**payload, "note": "a"}).allowed
    assert not classify_change(old, new).admission_changes
