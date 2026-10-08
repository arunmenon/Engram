"""Contract policy proves declarations without pretending writer wiring exists."""

import copy
import json
from pathlib import Path

import pytest

from context_graph.domain.ontology import OntologyError, OntologyRegistry, Pack
from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.domain.pack_contracts import PayloadContract
from context_graph.ontology import load_registry

CASES = json.loads(Path("tests/fixtures/pack_contracts/pdlc.json").read_text())["cases"]


def core():
    return load_registry([], builtin_packs=[]).pack("core")


def unfamiliar(*, handling=None, projection=True, contract=True):
    event = {}
    if contract:
        event["payload_contract"] = {
            "properties": {
                "meter": {"type": "string", "required": True},
                "reading": {"type": "number", "required": True},
                "note": {"type": "string", "nullable": True},
            }
        }
    if handling:
        event["handling"] = handling
    return Pack.model_validate(
        {
            "pack": {"name": "telemetry", "version": "1.0.0", "requires": ["core>=1.1"]},
            "types": {
                "nodes": {
                    "Meter": {
                        "key": ["meter"],
                        "properties": {"meter": "string", "reading": "float"},
                    }
                }
            },
            "events": {"telemetry.reading.recorded": event},
            "projection": [
                {
                    "event": "telemetry.reading.recorded",
                    "upsert": [
                        {
                            "type": "Meter",
                            "key": {"meter": "$.meter"},
                            "set": {"reading": "$.reading"},
                        }
                    ],
                }
            ]
            if projection
            else [],
        }
    )


def policy(pack=None):
    return compile_admission_policy(
        resolve_bundle(OntologyRegistry([core(), pack or unfamiliar()]))
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["event_type"])
def test_whole_pdlc_catalog_distinguishes_mapping_from_contract(case):
    checked = compile_admission_policy(resolve_bundle(load_registry(["pdlc"])))
    rules = {rule.event_type: rule for rule in checked.inventory if rule.owner == "pdlc"}
    assert set(rules) == {item["event_type"] for item in CASES}
    rule = rules[case["event_type"]]
    assert rule.contract_declared
    before = copy.deepcopy(case["payload"])
    decision = checked.decide(case["event_type"], case["payload"])
    assert case["payload"] == before
    if case["classification"] == "missing_mapping":
        assert not decision.allowed and rule.handling == "unsupported"
    else:
        assert decision.allowed and rule.handling == "processed" and rule.consumers


def test_unfamiliar_pack_observational_validation_preserves_omission_and_null():
    checked = policy()
    for payload in (
        {"meter": "west", "reading": 1.25, "extra": {"a": 1}},
        {"meter": "west", "reading": 1.25, "note": None},
    ):
        before = copy.deepcopy(payload)
        assert checked.decide("telemetry.reading.recorded", payload).allowed
        assert payload == before
    assert not checked.decide("telemetry.reading.recorded", {"meter": "west"}).allowed
    for value in (True, "1.25", float("nan"), float("inf")):
        assert not checked.decide(
            "telemetry.reading.recorded", {"meter": "west", "reading": value}
        ).allowed


def test_error_diagnostics_do_not_expose_secret_values_or_pydantic_context():
    decision = policy().decide(
        "telemetry.reading.recorded", {"meter": "west", "reading": "TOP_SECRET_INPUT"}
    )
    assert decision.reason == "payload_invalid"
    assert decision.problems[0].path == ("reading",)
    assert "TOP_SECRET_INPUT" not in repr(decision)


def test_unknown_extra_field_names_are_redacted_from_diagnostic_paths():
    declaration = unfamiliar().model_dump()
    declaration["events"]["telemetry.reading.recorded"]["payload_contract"]["additional_fields"] = (
        "forbid"
    )
    checked = policy(Pack.model_validate(declaration))
    decision = checked.decide(
        "telemetry.reading.recorded",
        {"meter": "west", "reading": 1.25, "SECRET_AS_FIELD_NAME": "secret"},
    )
    assert decision.problems[0].path == ("<extra>",)
    assert "SECRET_AS_FIELD_NAME" not in repr(decision)


def test_unknown_inactive_domain_and_source_alias_do_not_become_core_events():
    checked = compile_admission_policy(resolve_bundle(load_registry([], builtin_packs=[])))
    for event_type in (
        "pdlc.change.created",
        "crm.deal.created",
        "new.domain.event",
        "execute_tool",
    ):
        assert checked.decide(event_type, {}).reason == "event_unsupported"
    assert checked.decide("tool.execute", None).allowed
    assert not checked.decide("tool.custom", {}).allowed  # No implicit namespace opening.


def test_explicit_core_namespace_is_open_but_domain_namespaces_stay_closed():
    base = core().model_copy(deep=True, update={"open_event_namespaces": ["tool"]})
    checked = compile_admission_policy(resolve_bundle(OntologyRegistry([base, unfamiliar()])))
    assert checked.decide("tool.custom", {}).allowed
    assert not checked.decide("telemetry.unknown", {}).allowed
    assert not checked.decide("tool", {}).allowed
    assert not checked.decide("tool.", {}).allowed


@pytest.mark.parametrize("namespace", ["missing", "bad.namespace", ""])
def test_open_namespace_must_be_explicitly_owned_by_core(namespace):
    base = core().model_copy(deep=True, update={"open_event_namespaces": [namespace]})
    with pytest.raises(OntologyError):
        compile_admission_policy(resolve_bundle(OntologyRegistry([base])))
    custom = unfamiliar().model_copy(update={"open_event_namespaces": ["telemetry"]})
    with pytest.raises(OntologyError, match="only core"):
        policy(custom)


def test_deliberate_ledger_only_requires_contract_and_has_no_domain_consumer():
    checked = policy(unfamiliar(handling="ledger_only", projection=False))
    decision = checked.decide("telemetry.reading.recorded", {"meter": "west", "reading": 1.25})
    assert decision.allowed and decision.handling == "ledger_only"
    assert not checked.decide("telemetry.reading.recorded", {}).allowed
    with pytest.raises(OntologyError, match="contradicts"):
        policy(unfamiliar(handling="ledger_only"))
    unsupported = policy(unfamiliar(handling="processed", projection=False))
    assert unsupported.decide("telemetry.reading.recorded", {}).reason == "processing_unavailable"


def test_crm_current_contract_gap_is_visible_without_substituting_empty_contract():
    registry = load_registry(["crm"], [Path("tests/fixtures/packs/crm")], builtin_packs=[])
    checked = compile_admission_policy(resolve_bundle(registry))
    rules = [rule for rule in checked.inventory if rule.owner == "crm"]
    assert len(rules) == 6 and all(rule.consumers for rule in rules)
    assert all(rule.handling == "unsupported" and not rule.contract_declared for rule in rules)
    assert checked.decide("crm.deal.created", {}).reason == "payload_contract_missing"


def test_compiled_policy_is_snapshot_and_validators_are_not_rebuilt_per_event(monkeypatch):
    registry = OntologyRegistry([core(), unfamiliar()])
    calls = []
    original = PayloadContract.compile_validator

    def compile_once(contract):
        calls.append(1)
        return original(contract)

    monkeypatch.setattr(PayloadContract, "compile_validator", compile_once)
    bundle = resolve_bundle(registry)
    checked = compile_admission_policy(bundle)
    initial = len(calls)
    assert initial == 1
    registry.pack("telemetry").events.clear()
    bundle.registry.pack("telemetry").events.clear()
    for _ in range(3):
        assert checked.decide(
            "telemetry.reading.recorded", {"meter": "west", "reading": 1.25}
        ).allowed
    assert len(calls) == initial
    with pytest.raises(TypeError):
        checked._rules["forged"] = checked.inventory[0]


def test_absent_new_optional_declarations_preserve_existing_canonical_snapshot():
    base = core()
    canonical = json.loads(base.canonical_json())
    assert "open_event_namespaces" not in canonical
    assert all("handling" not in event for event in canonical["events"].values())
