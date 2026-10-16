import json
from copy import deepcopy

import pytest
from engram_pilot_tenant_proof import freeze, retained_state_preserved

from context_graph.domain.memory_actions import MemoryAction
from context_graph.domain.models import Event


def test_same_identity_different_source_and_correct_subgraph_goal():
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
            assert expected == action.subject.key


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


def test_tenant_memory_reads_use_supported_session_query_contract():
    from engram_pilot_tenant_proof import memory_read_request

    from context_graph.domain.models import SubgraphQuery

    for group in freeze("unit-supported-read")["groups"]:
        body = memory_read_request(group)
        parsed = SubgraphQuery.model_validate_json(json.dumps(body))
        assert str(parsed.intent) == "when"
        assert parsed.agent_id == group["steps"][0]["request"]["agent_id"]
        assert parsed.session_id == group["steps"][0]["request"]["session_id"]
        assert "seed_node_ids" not in body


@pytest.mark.parametrize("tenant", ["a", "b"])
async def test_actual_memory_subgraph_matches_frozen_public_goal_identity(tenant):
    from engram_pilot_tenant_proof import memory_read_request

    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.projection import event_to_node
    from tests.unit.test_memory_episodes import selected_engine

    group = next(g for g in freeze("unit-real-memory-read")["groups"] if g["tenant"] == tenant)
    source = group["steps"][0]["request"]
    event = Event.model_validate_json(json.dumps(source)).model_copy(
        update={"global_position": "unit-position"}
    )
    graph = MemoryGraphStore()
    await graph.merge_event_node(event_to_node(event))
    await graph.apply_memory_action(MemoryAction.from_event(event, source["payload"], trusted=True))
    body = memory_read_request(group)
    answer = await selected_engine(graph).get_subgraph(
        SubgraphQuery.model_validate_json(json.dumps(body))
    )
    node = answer.nodes[group["goal"]]
    assert node.node_type == "Goal"
    assert node.attributes["description"] == group["text"]
    assert node.provenance.event_id == source["event_id"]
    assert node.provenance.global_position == "unit-position"
