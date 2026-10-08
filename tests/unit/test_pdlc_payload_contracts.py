"""Whole-catalog local conformance. No API/backend/model execution."""

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from context_graph.domain.models import Event
from context_graph.domain.ontology import OntologyError, OntologyRegistry
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import load_registry
from context_graph.sources import github

ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / "tests/fixtures/pack_contracts/pdlc.json").read_text())
CASES = CATALOG["cases"]
REGISTRY = load_registry(["pdlc"])
EVENT_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_catalog_exactly_covers_pack_owned_events():
    owned = {n for n, e in REGISTRY.event_types.items() if e.pack == "pdlc"}
    assert len(CASES) == len(owned) == 28
    assert {c["event_type"] for c in CASES} == owned
    assert CATALOG["pack_version"] == REGISTRY.pack("pdlc").version
    assert sum(c["classification"] == "deterministic" for c in CASES) == 24
    assert sum(c["classification"] == "missing_mapping" for c in CASES) == 4


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["event_type"])
def test_contract_accepts_fixture_and_rejects_bad_required_fields(case):
    contract = REGISTRY.event_types[case["event_type"]].definition.payload_contract
    assert contract is not None
    payload = copy.deepcopy(case["payload"])
    contract.validate_payload(payload)
    assert payload == case["payload"]
    for name, field in contract.properties.items():
        if not field.required:
            continue
        missing = {k: v for k, v in payload.items() if k != name}
        with pytest.raises(ValidationError):
            contract.validate_payload(missing)
        with pytest.raises(ValidationError):
            contract.validate_payload({**payload, name: None})
        with pytest.raises(ValidationError):
            contract.validate_payload({**payload, name: []})
        if field.type == "string" and field.min_length:
            with pytest.raises(ValidationError):
                contract.validate_payload({**payload, name: ""})


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["event_type"])
def test_exact_domain_identities_edges_and_provenance_plan(case):
    event = Event(
        event_id=EVENT_ID,
        event_type=case["event_type"],
        occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
        session_id="contract-fixture",
        agent_id="fixture",
        trace_id="fixture",
        payload_ref="fixture",
        global_position="1-0",
    )
    plan = PackProjector(REGISTRY, frozenset({"fixture"})).plan(event, {"payload": case["payload"]})
    observed = {n.ref.key for n in plan.nodes if n.properties.get("source_trust") == "trusted"}
    assert observed == set(case["expected_observed_node_ids"])
    edges = {(e.edge_type, e.source.key, e.target.key) for e in plan.edges}
    expected = {tuple(e) for e in case["expected_domain_edges"]}
    expected |= {("DERIVED_FROM", node, str(EVENT_ID)) for node in observed}
    assert edges == expected
    assert {s.ref.key: s.to_state for s in plan.states} == case["expected_states"]
    assert plan.rejected == []
    if case["classification"] != "deterministic":
        assert plan.empty  # This is NOT a promise of domain output or executed extraction.


@pytest.mark.parametrize("path", ["$.entries[*].typo", "$.entries.section", "$.missing"])
def test_pack_load_refuses_undeclared_nested_or_mistyped_payload_path(path):
    pack = REGISTRY.pack("pdlc")
    data = pack.model_dump(by_alias=True)
    # Choose a known valid target field/rule, so only payload lookup is invalid.
    rule = next(r for r in data["projection"] if r["event"] == "pdlc.release.published")
    rule["upsert"][0]["set"]["breaking"] = path
    with pytest.raises(OntologyError, match="undeclared payload path"):
        OntologyRegistry(
            [*(p for p in REGISTRY.packs if p.name != "pdlc"), type(pack).model_validate(data)]
        )


def test_payload_fields_inside_expressions_are_checked():
    pack = REGISTRY.pack("pdlc")
    data = pack.model_dump(by_alias=True)
    rule = next(r for r in data["projection"] if r["event"] == "pdlc.change.updated")
    rule["upsert"][0]["set"]["title"] = "sha256($.typo)"
    with pytest.raises(OntologyError, match="undeclared payload path"):
        OntologyRegistry(
            [*(p for p in REGISTRY.packs if p.name != "pdlc"), type(pack).model_validate(data)]
        )


def test_reconstructed_existing_opendal_deliveries_match_contracts():
    fixture = json.loads((ROOT / "tests/fixtures/opendal/deliveries.json").read_text())
    for delivery in fixture["deliveries"]:
        for event in github.translate(delivery["event"], delivery["body"]):
            REGISTRY.event_types[event.event_type].definition.payload_contract.validate_payload(
                event.payload
            )


@pytest.mark.parametrize(
    "event_name,fixture",
    [
        ("pull_request", "github_pull_request_opened"),
        ("pull_request", "github_pull_request_merged"),
        ("pull_request_review", "github_pull_request_review_submitted"),
        ("check_run", "github_check_run_completed"),
        ("release", "github_release_published"),
        ("deployment_status", "github_deployment_status_success"),
        ("issues", "github_issues_closed"),
    ],
)
def test_handwritten_webhook_examples_match_contracts(event_name, fixture):
    source = json.loads((ROOT / f"tests/fixtures/webhooks/{fixture}.json").read_text())
    events = github.translate(event_name, source)
    assert events
    for event in events:
        REGISTRY.event_types[event.event_type].definition.payload_contract.validate_payload(
            event.payload
        )


def test_public_samples_in_explicitly_reconstructed_wrappers():
    # REST records are not deliveries. Wrappers below deliberately supply actions;
    # this exercises field normalization, not authenticity or historical action proof.
    corpus = ROOT / "docs/review/spanner-compatibility/public-payload-corpus"
    pulls = json.loads((corpus / "pull_requests.json").read_text())
    repo = {"full_name": "apache/opendal"}
    for review in json.loads((corpus / "pr_reviews.json").read_text()):
        assert review["pull_request_url"] == pulls[0]["url"]
        (event,) = github.translate(
            "pull_request_review",
            {
                "action": "submitted",
                "repository": repo,
                "pull_request": pulls[0],
                "review": review,
            },
        )
        assert event.event_type == "pdlc.change.reviewed"
        assert event.payload["verdict"] == "approved"
        REGISTRY.event_types[event.event_type].definition.payload_contract.validate_payload(
            event.payload
        )
    checks = json.loads((corpus / "ci_checks_expanded.json").read_text())["check_runs"]
    outcomes = set()
    for check in checks:
        (event,) = github.translate(
            "check_run",
            {
                "action": "completed",
                "repository": repo,
                "check_run": check,
            },
        )
        outcomes.add(event.payload["outcome"])
        REGISTRY.event_types[event.event_type].definition.payload_contract.validate_payload(
            event.payload
        )
    assert outcomes == {"success", "skipped", "cancel"}
    for status in json.loads((corpus / "deployment_statuses.json").read_text()):
        assert status["state"] == "failure"
        assert (
            github.translate(
                "deployment_status",
                {
                    "repository": {"full_name": "github/docs"},
                    "deployment_status": status,
                    "deployment": json.loads((corpus / "deployment_records.json").read_text())[0],
                },
            )
            == []
        )


def test_unfamiliar_pack_nested_paths_and_strict_contract_without_engine_edits():
    registry = load_registry(["lab"], [ROOT / "tests/fixtures/pack_contracts"])
    schema = registry.event_types["lab.sample.received"].definition.payload_contract
    payload = {
        "facility": "west",
        "measurements": [{"sample_id": "S-7", "reading": 12.5, "unit": "C"}],
    }
    schema.validate_payload(payload)
    assert schema.declares_path(("measurements", "[*]", "reading"))
    assert not schema.declares_path(("measurements", "reading"))
    with pytest.raises(ValidationError):
        schema.validate_payload(
            {**payload, "measurements": [{"sample_id": "S-7", "reading": "12.5", "unit": "C"}]}
        )
    with pytest.raises(ValidationError):
        schema.validate_payload({**payload, "extra": 1})
    event = Event(
        event_id=EVENT_ID,
        event_type="lab.sample.received",
        occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
        session_id="lab",
        agent_id="fixture",
        trace_id="fixture",
        payload_ref="fixture",
    )
    plan = PackProjector(registry, frozenset({"fixture"})).plan(event, {"payload": payload})
    assert [n.ref.key for n in plan.nodes] == ["LabSample:west|S-7"]
    assert plan.nodes[0].properties["reading"] == 12.5
    assert plan.nodes[0].properties["unit"] == "C"


@pytest.mark.parametrize("source_name", ["jira_issue_created", "jira_issue_updated_done"])
def test_jira_normalized_events_match_owner_contract(source_name):
    from context_graph.sources import jira

    source = json.loads((ROOT / f"tests/fixtures/webhooks/{source_name}.json").read_text())
    events = jira.translate(source)
    assert events
    for event in events:
        REGISTRY.event_types[event.event_type].definition.payload_contract.validate_payload(
            event.payload
        )


@pytest.mark.parametrize("path,valid", [("$.review_id", True), ("$.facility", False)])
def test_external_subscriber_uses_event_owners_contract(path, valid):
    combined = load_registry(["pdlc", "lab"], [ROOT / "tests/fixtures/pack_contracts"])
    pack = combined.pack("lab")
    data = pack.model_dump(by_alias=True)
    data["pack"]["requires"].append("pdlc>=1.8")
    data["projection"].append(
        {
            "event": "pdlc:pdlc.change.reviewed",
            "upsert": [
                {
                    "type": "LabSample",
                    "key": {"facility": "west", "sample_id": path},
                    "set": {"unit": "C"},
                }
            ],
        }
    )
    packs = [*(p for p in combined.packs if p.name != "lab"), type(pack).model_validate(data)]
    if valid:
        registry = OntologyRegistry(packs)
        assert {owner for owner, _rule in registry.rules_for("pdlc.change.reviewed")} == {
            "pdlc",
            "lab",
        }
    else:
        # facility belongs to lab's own event, not to the subscribed PDLC review.
        with pytest.raises(OntologyError, match="undeclared payload path"):
            OntologyRegistry(packs)
