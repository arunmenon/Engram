import json
from copy import deepcopy

import pytest
from engram_pilot_tenant_proof import freeze, retained_state_preserved

from context_graph.domain.memory_actions import MemoryAction
from context_graph.domain.models import Event


def test_same_identity_different_source_and_correct_typed_goal():
    p = freeze("unit-p09")
    a, b = p["groups"]
    x, y = a["steps"][0]["request"], b["steps"][0]["request"]
    assert x["event_id"] == y["event_id"] and x["session_id"] == y["session_id"]
    assert x["agent_id"] == y["agent_id"] and x["occurred_at"] == y["occurred_at"]
    assert x["payload"] != y["payload"] and a["goal"] == b["goal"]
    for g in (a, b):
        for step in g["steps"]:
            e = Event.model_validate_json(json.dumps(step["request"]))
            action = MemoryAction.from_event(e, step["request"]["payload"], trusted=True)
            expected = g["foreign"] if step["scenario"] == "foreign-only" else g["goal"]
            assert expected == "Goal:" + action.subject.key


def state():
    return dict(
        owner=dict(epoch=1),
        events=[["event", dict(payload=dict(content="immutable")), dict(source_id="source")]],
        nodes=[
            ["Event", "event", dict(importance_score=5)],
            ["Episode", "episode", dict(complete=True)],
            ["Summary", "summary", dict(content="old", created_at="old", scope="episode")],
            ["Goal", "goal", dict(status="active")],
        ],
        edges=[
            ["Episode", "episode", "CONTAINS", "Event", "event", dict(method="temporal")],
            ["Summary", "summary", "SUMMARIZES", "Event", "event", dict(created_at="old")],
        ],
        pending=[],
        dead_letters=[["g", "negative"]],
        dead_letter_fields=[["g", "negative", dict(reason="state_conflict")]],
    )


def test_only_approved_refresh_is_ignored():
    before = state()
    after = deepcopy(before)
    after["nodes"][0][2]["importance_score"] = 6
    after["nodes"][2][2].update(content="new", created_at="new")
    after["edges"][1][5]["created_at"] = "new"
    assert retained_state_preserved(before, after)
    assert retained_state_preserved(before, deepcopy(before))


@pytest.mark.parametrize(
    "tamper",
    [
        "source",
        "acceptance",
        "owner",
        "episode",
        "membership",
        "summary_structure",
        "summary_extra_edge",
        "business_extra_edge",
        "goal",
        "new_goal",
        "pending",
        "dlq",
    ],
)
def test_forbidden_probe_effects_rejected(tamper):
    before = state()
    after = deepcopy(before)
    if tamper == "source":
        after["events"][0][1]["payload"]["content"] = "rewritten"
    if tamper == "acceptance":
        after["events"][0][2]["source_id"] = "spoof"
    if tamper == "owner":
        after["owner"]["epoch"] = 2
    if tamper == "episode":
        after["nodes"][1][2]["complete"] = False
    if tamper == "membership":
        after["edges"].append(["Episode", "episode", "CONTAINS", "Event", "foreign", {}])
    if tamper == "summary_structure":
        after["nodes"][2][2]["scope"] = "session"
    if tamper == "summary_extra_edge":
        after["edges"].append(["Summary", "summary", "SUMMARIZES", "Event", "foreign", {}])
    if tamper == "business_extra_edge":
        after["edges"].append(["Goal", "goal", "DERIVED_FROM", "Event", "event", {}])
    if tamper == "goal":
        after["nodes"][3][2]["status"] = "completed"
    if tamper == "new_goal":
        after["nodes"].append(["Goal", "new", {}])
    if tamper == "pending":
        after["pending"].append(["g", "e"])
    if tamper == "dlq":
        after["dead_letter_fields"][0][2]["reason"] = "other"
    assert not retained_state_preserved(before, after)
