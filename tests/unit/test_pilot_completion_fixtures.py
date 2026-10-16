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
