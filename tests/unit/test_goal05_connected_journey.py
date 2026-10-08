"""Local G05 regressions; cloud acceptance uses actual Engram and Spanner."""

import sys
from pathlib import Path

import orjson
import pytest
from pydantic import ValidationError

from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.projection import event_to_node
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.worker.pack_projection import apply_plan
from tests.unit.test_pack_projection import REGISTRY, Harness

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from engram_goal05_fixtures import fixtures  # noqa: E402


def test_goal05_contracts():
    for step in fixtures("local-contract")["steps"]:
        contract = REGISTRY.event_types[step["request"]["event_type"]].definition.payload_contract
        if step["expected_status"] == 422:
            with pytest.raises(ValidationError):
                contract.validate_payload(step["request"]["payload"])
        else:
            contract.validate_payload(step["request"]["payload"])


async def test_connected_journey_exact_nodes_edges_and_original_questions():
    h = Harness()
    data = fixtures("local-connected")
    expected_nodes, expected_edges = {}, set()
    for index, step in enumerate(data["steps"]):
        if step["expected_status"] != 201 or step.get("duplicate"):
            continue
        request = step["request"]
        event = Event.model_validate(dict(request, global_position=f"{index + 1}-0"), strict=False)
        await h.graph.merge_event_node(event_to_node(event))
        trusted_sources = frozenset(s["request"]["agent_id"] for s in data["steps"])
        plan = PackProjector(REGISTRY, trusted_sources).plan(
            event, dict(orjson.loads(event.model_dump_json()), payload=request["payload"])
        )
        assert not plan.rejected
        await apply_plan(h.graph, plan, 1000)
        if step["expected_node"]:
            expected_nodes[step["expected_node"]] = step["expected_props"]
        expected_nodes.update(step["extra_nodes"])
        expected_edges.update(tuple(e) for e in step["expected_edges"])
        for key, props in expected_nodes.items():
            for name, value in props.items():
                assert h.node(key).get(name) == value, (step["scenario"], key, name)
    engine = ArtifactRetriever(
        h.graph,
        REGISTRY,
        default_max_depth=6,
        seed_limit=20,
        neighbor_limit=100,
        provenance_source="memory",
    )
    for query in data["queries"]:
        answer = await engine.retrieve(
            ArtifactQuery(
                query=query["text"],
                seed_node_ids=tuple(query["seeds"]),
                intent=query["intent"],
                max_nodes=50,
                max_depth=query["max_depth"],
            )
        )
        required = set(query["required"])
        assert set(answer.nodes) == required, (query["scenario"], set(answer.nodes) ^ required)
        edges = {(e.edge_type, e.source, e.target) for e in answer.edges}
        assert edges == {e for e in expected_edges if e[1] in required and e[2] in required}
        assert not answer.meta.truncated
