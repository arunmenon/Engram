"""P05 composition oracle and proof-backed retained-negative safeguards."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from engram_pilot_completion_fixtures import (
    declared_dead_letters,
    load_retained_negative,
    memory_subject_snapshot,
    p04_negative_proof,
)

ROOT = Path(__file__).parents[2]


def frozen():
    return json.loads((ROOT / "docs/pilot/pilot-p05-1016-01-journeys.json").read_text())


def graph_snapshot(graph):
    return dict(
        nodes=[[label, key, p] for (label, key), p in graph.nodes.items()],
        edges=[[a[0], a[1], kind, b[0], b[1], p] for (a, kind, b), p in graph.edges.items()],
    )


async def test_memory_pdlc_coexistence_and_explicit_completion_oracle():
    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.models import Event, SubgraphQuery
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.domain.projection import event_to_node
    from context_graph.ontology.loader import load_registry
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from context_graph.worker.pack_projection import apply_plan
    from tests.unit.test_memory_episodes import selected_engine

    group = frozen()["groups"][0]
    graph = MemoryGraphStore()
    registry = load_registry(["pdlc"], builtin_packs=["memory"])
    projector = PackProjector(registry, frozenset(s["request"]["agent_id"] for s in group["steps"]))
    for index, step in enumerate(group["steps"]):
        record = step["request"]
        event = Event.model_validate_json(json.dumps(record)).model_copy(
            update={"global_position": f"{index + 1}-0"}
        )
        contract = registry.event_types[event.event_type].definition.payload_contract
        contract.validate_payload(record["payload"])
        before = copy.deepcopy(graph_snapshot(graph))
        await graph.merge_event_node(event_to_node(event))
        if event.event_type.startswith("memory."):
            await graph.apply_memory_action(
                MemoryAction.from_event(event, record["payload"], trusted=True)
            )
        else:
            await apply_plan(graph, projector.plan(event, record), 1000)
        state = graph_snapshot(graph)
        props = next(p for (_, nid), p in graph.nodes.items() if nid == step["expected_node"])
        assert all(props.get(k) == v for k, v in step["expected_props"].items()), step["scenario"]
        edges = {(r[2], r[1], r[4]) for r in state["edges"]}
        assert set(map(tuple, step["expected_edges"])) <= edges
        if step.get("forbidden_edge_types"):
            assert not any(
                r[2] in step["forbidden_edge_types"] and step["expected_node"] in (r[1], r[4])
                for r in state["edges"]
            )
        if step.get("unchanged_subject"):
            assert memory_subject_snapshot(
                before, step["unchanged_subject"]
            ) == memory_subject_snapshot(state, step["unchanged_subject"])
            answer = await selected_engine(graph).get_subgraph(
                SubgraphQuery(
                    query="Show delivery history",
                    intent="when",
                    session_id=event.session_id,
                    agent_id=event.agent_id,
                    max_nodes=100,
                )
            )
            assert answer.nodes[step["unchanged_subject"]].attributes["status"] == "active"
    for query in group["final_queries"]:
        body = {
            k: v
            for k, v in query.items()
            if k not in {"required", "forbidden", "expected_edges", "forbidden_edges"}
        }
        answer = (
            await selected_engine(graph).get_subgraph(SubgraphQuery(**body, max_nodes=100))
        ).model_dump(mode="json")
        assert set(query["required"]) <= answer["nodes"].keys()
        assert not set(query["forbidden"]) & answer["nodes"].keys()
        edges = {(e["edge_type"], e["source"], e["target"]) for e in answer["edges"]}
        assert set(map(tuple, query.get("expected_edges", []))) <= edges
        assert not set(map(tuple, query.get("forbidden_edges", []))) & edges
    retriever = ArtifactRetriever(
        graph,
        registry,
        default_max_depth=6,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )
    q = group["queries"][0]
    answer = await retriever.retrieve(
        ArtifactQuery(q["text"], seed_node_ids=tuple(q["seeds"]), intent=q["intent"])
    )
    assert set(q["required"]) <= answer.nodes.keys()
    assert not set(q["forbidden"]) & answer.nodes.keys()


def retained_state():
    p = ROOT / "docs/review/spanner-compatibility/runs/pilot-p04-1016-01/a-final-state.json"
    state = json.loads(p.read_text())["snapshot"]
    item = load_retained_negative(p04_negative_proof(), ROOT)
    groups = [dict(tenant="b", steps=[], retained_negative_deliveries=[item])]
    return state, groups


def test_retained_negative_requires_exact_current_source_and_fields():
    state, groups = retained_state()
    assert declared_dead_letters(state, groups, "a", require_all=True)
    state["dead_letters"] = []
    assert not declared_dead_letters(state, groups, "a")


@pytest.mark.parametrize("tamper", ["fields", "source", "extra"])
def test_retained_negative_does_not_excuse_mutation_or_new_failure(tamper):
    state, groups = retained_state()
    if tamper == "extra":
        state["dead_letters"].append(["assessment-enrichment", "other"])
    elif tamper == "fields":
        state["dead_letter_fields"][0][2]["consumer"] = "other"
    else:
        eid = groups[0]["retained_negative_deliveries"][0]["request"]["event_id"]
        next(r for r in state["events"] if r[0] == eid)[1]["payload"]["expected_revision"] = 999
    assert not declared_dead_letters(state, groups, "a")


@pytest.mark.parametrize("tamper", ["hash", "verdict", "audit"])
def test_retained_proof_must_have_successful_prior_evidence(tmp_path, tamper):
    proof = p04_negative_proof()
    directory = tmp_path / "proof"
    directory.mkdir()
    original = ROOT / proof["directory"]
    proof["directory"] = "proof"
    for name in proof["sha256"]:
        data = json.loads((original / name).read_text())
        if tamper == "verdict" and name == "results.json":
            data["state"] = "failed"
        if tamper == "audit" and name == "recorded-source-audit.json":
            data["all_match"] = False
        raw = json.dumps(data).encode()
        (directory / name).write_bytes(raw)
        if tamper != "hash":
            proof["sha256"][name] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):
        load_retained_negative(proof, tmp_path)
