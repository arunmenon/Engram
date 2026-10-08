"""G03 semantic checks; local memory diagnostics, never cloud acceptance."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError
from scripts.engram_goal03_fixtures import fixtures

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.projection import event_to_node
from context_graph.ontology import load_registry
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.worker.pack_projection import apply_plan


async def test_explicit_planning_code_review_and_test_trace():
    data = fixtures("local-g03")
    registry = load_registry(["pdlc"])
    graph = MemoryGraphStore()
    expected_edges = set()
    expected_props = {}
    for step in data["steps"]:
        request = step["request"]
        contract = registry.event_types[request["event_type"]].definition.payload_contract
        if step["expected_status"] == 422:
            with pytest.raises(ValidationError):
                contract.validate_payload(request["payload"])
            continue
        if step["expected_status"] != 201 or step["scenario"] == "IM11-duplicate":
            continue  # Admission duplicate/conflict behavior is verified through real HTTP.
        contract.validate_payload(request["payload"])
        event = Event.model_validate(request, strict=False).model_copy(
            update={"global_position": "1-0"}
        )
        await graph.merge_event_node(event_to_node(event))
        plan = PackProjector(registry, frozenset({"implementation.publisher"})).plan(
            event, {"payload": request["payload"]}
        )
        assert not plan.rejected
        await apply_plan(graph, plan, 100)
        expected_edges.update(tuple(e) for e in step["expected_edges"])
        expected_props[step["expected_node"]] = step["expected_props"]
        expected_props.update(step["extra_nodes"])
    domain_edges = {
        (kind, a[1], b[1])
        for a, kind, b in graph.edges
        if kind in {"IMPLEMENTS", "VERIFIES", "REFINES", "REVIEWS", "EXECUTES", "RAN_AGAINST"}
    }
    assert domain_edges == expected_edges
    engine = ArtifactRetriever(
        graph,
        registry,
        provenance_source="memory",
        default_max_depth=5,
        seed_limit=20,
        neighbor_limit=100,
    )
    for fixture in data["queries"]:
        if not fixture["seed"]:
            continue  # Text-only provider-backed acceptance remains a cloud check.
        answer = await engine.retrieve(
            ArtifactQuery(
                query="trace " + fixture["seed"],
                seed_node_ids=(fixture["seed"],),
                intent="trace",
                max_nodes=50,
                max_depth=5,
            )
        )
        required = set(fixture["required"])
        assert required <= set(answer.nodes), (fixture["scenario"], required - set(answer.nodes))
        assert not (set(fixture["forbidden"]) & set(answer.nodes))
        assert {(k, a, b) for k, a, b in expected_edges if a in required and b in required} <= {
            (e.edge_type, e.source, e.target) for e in answer.edges
        }
        for key in required:
            for prop, value in expected_props[key].items():
                assert answer.nodes[key].attributes[prop] == value
        assert not answer.meta.truncated


def test_multiple_explicit_references_keep_each_complete_identity():
    registry = load_registry(["pdlc"])
    event = Event(
        event_id=UUID(int=7),
        event_type="pdlc.ticket.created",
        occurred_at=datetime(2026, 10, 8, tzinfo=UTC),
        session_id="test",
        agent_id="publisher",
        trace_id="t",
        payload_ref="p",
        global_position="1-0",
    )
    payload = dict(
        tracker="jira",
        key="RESET-17",
        requirements=[
            dict(spec_id="reset", spec_version="1", local_id="expiry"),
            dict(spec_id="newsletter", spec_version="2", local_id="expiry"),
        ],
        designs=[
            dict(doc_id="reset-lld", section_path="storage", version="1"),
            dict(doc_id="newsletter-hld", section_path="delivery", version="2"),
        ],
    )
    plan = PackProjector(registry, frozenset({"publisher"})).plan(event, {"payload": payload})
    assert not plan.rejected
    assert {e.target.key for e in plan.edges if e.edge_type == "IMPLEMENTS"} == {
        "Requirement:reset|1|expiry",
        "Requirement:newsletter|2|expiry",
        "DesignElement:reset-lld|storage|1",
        "DesignElement:newsletter-hld|delivery|2",
    }
