"""Authored P04 oracles and negative-delivery verifier safety, not cloud proof."""

import copy
import json
from pathlib import Path

import pytest
from engram_pilot_completion_fixtures import declared_dead_letters


def plan():
    return json.loads(
        (Path(__file__).parents[2] / "docs/pilot/pilot-p04-1016-01-journeys.json").read_text()
    )


async def test_frozen_memory_sequence_and_scope_reads():
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.domain.memory_actions import MemoryAction, MemoryActionConflictError
    from context_graph.domain.models import Event, SubgraphQuery
    from context_graph.domain.projection import event_to_node
    from tests.unit.test_memory_episodes import selected_engine

    graph = MemoryGraphStore()
    group = plan()["groups"][0]
    for i, step in enumerate(group["steps"]):
        record = step["request"]
        event = Event.model_validate_json(json.dumps(record)).model_copy(
            update={"global_position": f"{i + 1}-0"}
        )
        if step["expected_status"] >= 400:
            with pytest.raises(ValueError):
                MemoryAction.from_event(event, record["payload"])
            continue
        await graph.merge_event_node(event_to_node(event))
        if record["event_type"].startswith("memory."):
            action = MemoryAction.from_event(event, record["payload"], trusted=True)
            if step.get("expected_worker_rejection"):
                before = copy.deepcopy((graph.nodes, graph.edges))
                with pytest.raises(MemoryActionConflictError):
                    await graph.apply_memory_action(action)
                assert (graph.nodes, graph.edges) == before
            else:
                await graph.apply_memory_action(action)
        props = next(p for (label, key), p in graph.nodes.items() if key == step["expected_node"])
        assert all(props.get(k) == v for k, v in step["expected_props"].items()), step["scenario"]
        for nid, wanted in step.get("node_assertions", {}).items():
            actual = next(p for (_, key), p in graph.nodes.items() if key == nid)
            assert all(actual.get(k) == v for k, v in wanted.items())
        if step["scenario"] == "ordinary-progress":
            answer = await selected_engine(graph).get_subgraph(
                SubgraphQuery(
                    query="What goals do I have?",
                    intent="goals",
                    session_id=record["session_id"],
                    agent_id=record["agent_id"],
                )
            )
            assert answer.nodes[step["expected_node"]].attributes["status"] == "active"
    for q in group["final_queries"]:
        answer = await selected_engine(graph).get_subgraph(
            SubgraphQuery(
                **{k: v for k, v in q.items() if k not in {"required", "forbidden"}}, max_nodes=100
            )
        )
        assert set(q["required"]) <= answer.nodes.keys(), q
        assert not set(q["forbidden"]) & answer.nodes.keys(), q


def dead_letter_state():
    groups = plan()["groups"]
    step = next(s for s in groups[0]["steps"] if s.get("expected_worker_rejection"))
    eid = step["request"]["event_id"]
    accepted = dict(
        tenant_id="isolation-a",
        database_resource="a-db",
        binding_id="binding",
        bundle_digest="digest",
        engine_revision="engine",
        accepted_epoch=51,
    )
    fields = dict(
        **accepted,
        event_id=eid,
        group="assessment-projection",
        consumer="projection-1",
        original_entry_id="position",
        acceptance=json.dumps(accepted),
        disposition_epoch="53",
    )
    state = dict(
        events=[[eid, step["request"], accepted]],
        nodes=[
            [
                "Event",
                eid,
                dict(
                    global_position="position",
                    memory_status="conflict",
                    memory_reason="state_conflict",
                ),
            ]
        ],
        edges=[],
        pending=[],
        dead_letters=[["assessment-projection", eid]],
        dead_letter_fields=[["assessment-projection", eid, fields]],
    )
    return state, groups


def test_declared_negative_exact_source_and_distinct_disposition_epoch():
    state, groups = dead_letter_state()
    assert declared_dead_letters(state, groups, "a", require_all=True)
    assert not declared_dead_letters(state, groups, "b")
    state["dead_letters"].append(["assessment-enrichment", "unknown"])
    assert not declared_dead_letters(state, groups, "a")


@pytest.mark.parametrize(
    "field,value",
    [
        ("consumer", "other"),
        ("original_entry_id", "wrong"),
        ("tenant_id", "foreign"),
        ("binding_id", "wrong"),
        ("acceptance", "{}"),
    ],
)
def test_negative_delivery_tampering_rejected(field, value):
    state, groups = dead_letter_state()
    state["dead_letter_fields"][0][2][field] = value
    assert not declared_dead_letters(state, groups, "a")


def test_negative_pending_missing_details_and_missing_expected_rejected():
    state, groups = dead_letter_state()
    state["pending"] = copy.deepcopy(state["dead_letters"])
    assert not declared_dead_letters(state, groups, "a")
    state["pending"] = []
    state["dead_letter_fields"] = []
    assert not declared_dead_letters(state, groups, "a")
    state["dead_letters"] = []
    assert declared_dead_letters(state, groups, "a")
    assert not declared_dead_letters(state, groups, "a", require_all=True)
