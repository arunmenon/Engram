"""Adversarial tests for the bounded, retained P06 history proof."""

import copy
import json
from pathlib import Path

import pytest
from engram_pilot_episode_bridge import decode, episode
from engram_pilot_episode_history import (
    connected_candidates,
    load_proof,
    pin_proof,
    validated_inventory,
)

ROOT = Path(__file__).parents[2]
RUN = ROOT / "docs/review/spanner-compatibility/runs/pilot-p06-1016-02"


def check(name, passed, actual=None):
    assert passed, (name, actual)


@pytest.fixture()
def source_case():
    result = json.loads((RUN / "results.json").read_text())
    group = json.loads((RUN / "fixtures.json").read_text())["spectrum"]["groups"][0]
    full = json.loads((RUN / "a-final-state.json").read_text())["snapshot"]
    candidates = connected_candidates(group)
    candidates[group["control"]["id"]] = group["control"]
    identities = {k for e in candidates.values() for k in (e["id"], e["summary"], *e["members"])}
    state = dict(
        nodes=[copy.deepcopy(r) for r in full["nodes"] if r[1] in identities],
        edges=[
            copy.deepcopy(r) for r in full["edges"] if r[1] in identities and r[4] in identities
        ],
    )
    positions = {
        q["input"]["event_id"]: q["output"]["global_position"]
        for q in result["requests"]
        if q["tenant"] == "a" and q["path"] == "/v1/events"
    }
    prior = result["episode_bridge"]["phases"][0]["tenants"]["a"]["storage"]
    return state, group, positions, prior


def test_only_temporally_connected_frozen_subsets_are_candidates(source_case):
    state, g, positions, prior = source_case
    candidates = connected_candidates(g)
    assert len(candidates) == 6
    disconnected = episode(g["session"], [g["steps"][0]["request"], g["steps"][1]["request"]])
    assert disconnected["id"] not in candidates
    assert g["control"]["id"] not in candidates
    selected, _ = validated_inventory(state, g, positions, prior, check)
    assert len(selected) == 5  # four primary snapshots plus the unrelated-session control


@pytest.mark.parametrize(
    "tamper", ["foreign_member", "disconnected", "missing_merged", "extra_summary", "old_bounds"]
)
def test_invalid_history_cannot_be_allowed_from_response_contents(source_case, tamper):
    state, g, positions, prior = source_case
    if tamper == "foreign_member":
        state["edges"].append(["Episode", g["merged"]["id"], "CONTAINS", "Event", "foreign", {}])
    if tamper == "disconnected":
        e = episode(g["session"], [g["steps"][0]["request"], g["steps"][1]["request"]])
        state["nodes"].append(["Episode", e["id"], {"session_id": g["session"]}])
    if tamper == "missing_merged":
        state["nodes"] = [r for r in state["nodes"] if r[1] != g["merged"]["id"]]
    if tamper == "extra_summary":
        state["nodes"].append(
            ["Summary", "extra", {"scope": "episode", "scope_id": g["merged"]["id"]}]
        )
    if tamper == "old_bounds":
        row = next(r for r in state["nodes"] if r[1] == g["initial"][0]["id"])
        props = dict(decode(row[2]))
        props["end_time"] = "2020-01-01T00:00:00+00:00"
        row[2] = props
    with pytest.raises(AssertionError):
        validated_inventory(state, g, positions, prior, check)


def test_original_named_proof_prerequisites_are_required(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir()
    proof = pin_proof(RUN, ROOT)
    for name in proof["sha256"]:
        (directory / name).write_bytes((RUN / name).read_bytes())
    valid = pin_proof(directory, tmp_path)
    load_proof(valid, tmp_path)
    result = json.loads((directory / "results.json").read_text())
    result["checks"] = [
        c for c in result["checks"] if c["name"] != "b:published exact member source position"
    ]
    (directory / "results.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="prerequisites"):
        load_proof(pin_proof(directory, tmp_path), tmp_path)


def test_pinned_evidence_tampering_is_rejected(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir()
    proof = pin_proof(RUN, ROOT)
    for name in proof["sha256"]:
        (directory / name).write_bytes((RUN / name).read_bytes())
    pinned = pin_proof(directory, tmp_path)
    (directory / "results.json").write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        load_proof(pinned, tmp_path)
