"""G04 scoped identity/outcome contract and exact deterministic topology regressions.

Local supplements only; actual goal acceptance still requires real Spanner.
"""

import importlib.util
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

path = Path(__file__).resolve().parents[2] / "scripts/engram_goal04_fixtures.py"
spec = importlib.util.spec_from_file_location("g04_fixtures", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_all_goal04_payloads_have_declared_contract_results():
    for step in module.fixtures("local-contract")["steps"]:
        event = REGISTRY.event_types.get(step["request"]["event_type"])
        if event is None:
            assert step["expected_status"] == 422
            continue
        contract = event.definition.payload_contract
        if step["expected_status"] == 422:
            with pytest.raises(ValidationError):
                contract.validate_payload(step["request"]["payload"])
        else:
            contract.validate_payload(step["request"]["payload"])


async def test_scoped_deployments_failures_placeholders_and_exact_declared_links():
    h = Harness()
    data = module.fixtures("local-projection")
    expected_nodes, expected_edges = {}, set()
    for index, step in enumerate(data["steps"]):
        if step["expected_status"] != 201 or step.get("duplicate"):
            continue
        request = step["request"]
        event = Event.model_validate(dict(request, global_position=f"{index + 1}-0"), strict=False)
        await h.graph.merge_event_node(event_to_node(event))
        plan = PackProjector(REGISTRY, frozenset({"release.publisher"})).plan(
            event, dict(orjson.loads(event.model_dump_json()), payload=request["payload"])
        )
        assert not plan.rejected
        await apply_plan(h.graph, plan, 1000)
        if step["expected_node"]:
            expected_nodes[step["expected_node"]] = step["expected_props"]
        expected_nodes.update(step["extra_nodes"])
        for key, props in expected_nodes.items():
            for name, value in props.items():
                assert h.node(key).get(name) == value, (step["scenario"], key, name)
        for placeholder in step.get("placeholders", []):
            assert not any(source == placeholder for source, _ in h.edges("DERIVED_FROM"))
        expected_edges.update(tuple(e) for e in step["expected_edges"])
        actual = {
            (kind, source, target)
            for kind in ["INCLUDES", "DEPLOYS", "DEPLOYED_TO"]
            for source, target in h.edges(kind)
        }
        assert actual == expected_edges, (step["scenario"], actual ^ expected_edges)
    assert h.node(data["ids"]["failed"])["status"] == "failed"
    assert h.node(data["ids"]["success"])["status"] == "succeeded"
    assert (
        len(
            {
                data["ids"][key]
                for key in [
                    "failed",
                    "other_deploy",
                    "other_repo_same_service",
                    "other_service_deploy",
                ]
            }
        )
        == 4
    )

    engine = ArtifactRetriever(
        h.graph,
        REGISTRY,
        default_max_depth=5,
        seed_limit=20,
        neighbor_limit=100,
        provenance_source="memory",
    )
    for query in data["queries"]:
        answer = await engine.retrieve(
            ArtifactQuery(
                query="trace " + query["seed"],
                seed_node_ids=(query["seed"],),
                intent="trace",
                max_nodes=50,
                max_depth=5,
            )
        )
        required = set(query["required"])
        assert set(answer.nodes) == required, (query["scenario"], set(answer.nodes) ^ required)
        edges = {(e.edge_type, e.source, e.target) for e in answer.edges}
        assert edges == {e for e in expected_edges if e[1] in required and e[2] in required}
        assert not answer.meta.truncated
