"""G07-D contracts and projection at the approved pure public seams."""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import load_registry

REGISTRY = load_registry(["pdlc"])
EVENT_ID = UUID("00000000-0000-0000-0000-000000000057")
IDENTITY = {"repo": "acme/app", "service": "api", "environment": "prod", "artifact_id": "abc"}
TARGET = "Deployment:acme/app|api|prod|abc|2026-10-08T10:00:00+00:00"
ACTION = f"DeploymentRollback:{EVENT_ID}"


def plan(kind, payload, at="2026-10-08T11:00:00+00:00", event_id=EVENT_ID):
    event = Event(
        event_id=event_id,
        event_type=f"pdlc.service.{kind}",
        occurred_at=datetime.fromisoformat(at),
        session_id="g07",
        agent_id="fixture",
        trace_id="g07",
        payload_ref="fixture",
        global_position="1-0",
    )
    return PackProjector(REGISTRY, frozenset({"fixture"})).plan(event, {"payload": payload})


def test_unknown_rollback_preserves_action_evidence_without_observing_target():
    result = plan("rolledback", IDENTITY | {"target_started_at": "2026-10-08T10:00:00Z"})
    assert not result.rejected
    observed = {n.ref.key for n in result.nodes if "source_trust" in n.properties}
    assert observed == {ACTION}
    assert {(e.edge_type, e.source.key, e.target.key) for e in result.edges} == {
        ("ROLLS_BACK", ACTION, TARGET),
        ("DERIVED_FROM", ACTION, str(EVENT_ID)),
    }
    target = next(n for n in result.nodes if n.ref.key == TARGET)
    assert "updated_at" not in target.properties
    assert [(s.ref.key, s.to_state) for s in result.states] == [(TARGET, "rolled_back")]


@pytest.mark.parametrize(
    "timestamp",
    [
        None,
        "",
        7,
        "2026-10-08T10:00:00",
        "2026-02-30T10:00:00Z",
        "2026-10-08T24:00:00Z",
        "2026-10-08T10:00:00+24:00",
        "0001-01-01T00:00:00+01:00",
        "9999-12-31T23:00:00-02:00",
    ],
)
def test_rollback_rejects_missing_naive_or_malformed_target_timestamp(timestamp):
    payload = IDENTITY | ({"target_started_at": timestamp} if timestamp is not None else {})
    contract = REGISTRY.event_types["pdlc.service.rolledback"].definition.payload_contract
    with pytest.raises(ValidationError):
        contract.validate_payload(payload)


@pytest.mark.parametrize(
    "timestamp", ["2026-10-08T10:00:00Z", "2026-10-08T10:00:00+00:00", "2026-10-08T15:30:00+05:30"]
)
def test_target_timestamp_normalizes_equivalent_instants(timestamp):
    payload = IDENTITY | {"target_started_at": timestamp}
    REGISTRY.event_types["pdlc.service.rolledback"].definition.payload_contract.validate_payload(
        payload
    )
    assert plan("rolledback", payload).states[0].ref.key == TARGET


def test_completed_upgrade_has_own_identity_and_only_explicit_change_links():
    result = plan("upgraded", IDENTITY | {"change_numbers": [7, 9]})
    deployment = "Deployment:acme/app|api|prod|abc|2026-10-08T11:00:00+00:00"
    node = next(n for n in result.nodes if n.ref.key == deployment)
    assert node.properties["operation"] == "upgrade"
    assert [(s.ref.key, s.to_state) for s in result.states] == [(deployment, "succeeded")]
    assert {(e.edge_type, e.source.key, e.target.key) for e in result.edges} == {
        ("DERIVED_FROM", deployment, str(EVENT_ID)),
        ("DERIVED_FROM", "Component:api", str(EVENT_ID)),
        ("DEPLOYED_TO", deployment, "Component:api"),
        ("DEPLOYS", deployment, "Change:acme/app|7"),
        ("DEPLOYS", deployment, "Change:acme/app|9"),
    }
    no_changes = plan("upgraded", IDENTITY)
    assert not no_changes.lookups
    assert not [e for e in no_changes.edges if e.edge_type == "DEPLOYS"]


def test_late_success_and_failure_cannot_undo_rollback():
    for kind in ("deployed", "upgraded", "deployment_failed"):
        result = plan(kind, IDENTITY, at="2026-10-08T10:00:00+00:00")
        assert result.states[0].ref.key == TARGET
        assert "rolled_back" not in result.states[0].only_from
        assert "started" in result.states[0].only_from


def test_rollback_is_retrievable_via_action_and_deployment_traversal():
    assert "DeploymentRollback" in REGISTRY.pack("pdlc").retrieval.seed_types
    assert REGISTRY.pack("pdlc").retrieval.intents["trace"].weights["ROLLS_BACK"] > 0


class PackGraphBoundary:
    """Small external-port fake, with no database/backend runner."""

    def __init__(self):
        self.nodes = {}
        self.edges = {}

    async def upsert_nodes(self, writes):
        for w in writes:
            props = self.nodes.setdefault(w.ref, {w.ref.key_property: w.ref.key, **w.defaults})
            props.update({k: v for k, v in w.properties.items() if v is not None})
            for name in w.remove_properties:
                props.pop(name, None)

    async def change_states(self, changes):
        count = 0
        for c in changes:
            props = self.nodes.get(c.ref)
            if (
                props is not None
                and props.get("status") != c.to_state
                and (not c.only_from or props.get("status") in c.only_from)
            ):
                props.update(status=c.to_state, status_changed_at=c.changed_at)
                count += 1
        return count

    async def upsert_edges(self, writes):
        for w in writes:
            if w.source in self.nodes and w.target in self.nodes:
                self.edges[(w.source, w.edge_type, w.target)] = dict(w.properties)
        return len(writes)

    async def get_nodes(self, refs):
        return {r: dict(self.nodes[r]) for r in refs if r in self.nodes}

    async def find_nodes_matching(self, label, conditions, limit):
        return [[] for _ in conditions]

    async def search_nodes(self, label, fields, terms, limit):
        return []

    async def neighbors(self, refs, edge_types, direction, limit):
        rows = []
        for (source, kind, target), props in self.edges.items():
            if edge_types is not None and kind not in edge_types:
                continue
            far = (
                target
                if source in refs and direction in ("out", "both")
                else (source if target in refs and direction in ("in", "both") else None)
            )
            if far is not None:
                rows.append(
                    {
                        "source_label": source.label,
                        "source_key": source.key,
                        "target_label": target.label,
                        "target_key": target.key,
                        "edge_type": kind,
                        "properties": props,
                        "node_label": far.label,
                        "node": dict(self.nodes[far]),
                    }
                )
        return rows[:limit]


async def test_unknown_target_retrieval_and_late_fill_keep_distinct_observation_evidence():
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from context_graph.worker.pack_projection import apply_plan

    graph = PackGraphBoundary()
    rollback = plan("rolledback", IDENTITY | {"target_started_at": "2026-10-08T10:00:00Z"})
    await graph.upsert_nodes(
        [
            NodeWrite(
                NodeRef("Event", str(EVENT_ID), "event_id"),
                {
                    "event_id": str(EVENT_ID),
                    "occurred_at": "2026-10-08T11:00:00+00:00",
                    "session_id": "g07",
                    "global_position": "2-0",
                },
            )
        ]
    )
    await apply_plan(graph, rollback, 100)
    retriever = ArtifactRetriever(
        graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=100,
        provenance_source="boundary",
    )
    query = ArtifactQuery(query="trace", seed_node_ids=(ACTION,), intent="trace")
    response = await retriever.retrieve(query)
    assert response.nodes[TARGET].provenance is None
    assert response.nodes[TARGET].attributes["status"] == "rolled_back"
    assert response.nodes[ACTION].provenance.event_id == str(EVENT_ID)

    original = "00000000-0000-0000-0000-000000000056"
    deployed = plan(
        "deployed",
        IDENTITY | {"change_numbers": [7]},
        at="2026-10-08T10:00:00+00:00",
        event_id=UUID(original),
    )
    await graph.upsert_nodes(
        [
            NodeWrite(
                NodeRef("Event", original, "event_id"),
                {
                    "event_id": original,
                    "occurred_at": "2026-10-08T10:00:00+00:00",
                    "session_id": "g07",
                    "global_position": "1-0",
                },
            )
        ]
    )
    await apply_plan(graph, deployed, 100)
    response = await retriever.retrieve(query)
    assert response.nodes[TARGET].provenance.event_id == original
    assert response.nodes[TARGET].attributes["status"] == "rolled_back"
    assert response.nodes[ACTION].provenance.event_id == str(EVENT_ID)
    assert "Change:acme/app|7" in response.nodes


@pytest.mark.parametrize(
    "changed",
    [
        {"repo": "other/app"},
        {"service": "worker"},
        {"environment": "staging"},
        {"artifact_id": "def"},
        {"target_started_at": "2026-10-08T10:00:01Z"},
    ],
)
def test_complete_target_identity_separates_rollback_attempts(changed):
    payload = IDENTITY | {"target_started_at": "2026-10-08T10:00:00Z"} | changed
    result = plan("rolledback", payload)
    assert result.states[0].ref.key != TARGET
    assert len(result.states) == 1


@pytest.mark.parametrize("field", ["repo", "service", "environment", "artifact_id"])
@pytest.mark.parametrize("invalid", [None, "", 7, []])
def test_rollback_rejects_invalid_scoped_identity(field, invalid):
    payload = IDENTITY | {"target_started_at": "2026-10-08T10:00:00Z", field: invalid}
    contract = REGISTRY.event_types["pdlc.service.rolledback"].definition.payload_contract
    with pytest.raises(ValidationError):
        contract.validate_payload(payload)


async def test_observed_target_rollback_preserves_other_attempt_and_links():
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.worker.pack_projection import apply_plan

    graph = PackGraphBoundary()
    first = plan("upgraded", IDENTITY | {"change_numbers": [7]}, at="2026-10-08T09:00:00+00:00")
    second = plan("upgraded", IDENTITY | {"change_numbers": [9]}, at="2026-10-08T10:00:00+00:00")
    await apply_plan(graph, first, 100)
    await apply_plan(graph, second, 100)
    await apply_plan(
        graph, plan("rolledback", IDENTITY | {"target_started_at": "2026-10-08T10:00:00Z"}), 100
    )
    nodes = await graph.get_nodes(
        [
            NodeRef("Deployment", TARGET),
            NodeRef("Deployment", "Deployment:acme/app|api|prod|abc|2026-10-08T09:00:00+00:00"),
        ]
    )
    assert nodes[NodeRef("Deployment", TARGET)]["status"] == "rolled_back"
    assert (
        nodes[NodeRef("Deployment", "Deployment:acme/app|api|prod|abc|2026-10-08T09:00:00+00:00")][
            "status"
        ]
        == "succeeded"
    )
    assert nodes[NodeRef("Deployment", TARGET)]["operation"] == "upgrade"
    assert {(s.key, kind, t.key) for s, kind, t in graph.edges if s.key == TARGET} == {
        (TARGET, "DEPLOYED_TO", "Component:api"),
        (TARGET, "DEPLOYS", "Change:acme/app|9"),
    }


@pytest.mark.parametrize(
    "timestamp,canonical",
    [
        ("0001-01-01T00:00:00Z", "0001-01-01T00:00:00+00:00"),
        ("9999-12-31T23:59:59.999999Z", "9999-12-31T23:59:59.999999+00:00"),
        ("0001-01-01T01:00:00+01:00", "0001-01-01T00:00:00+00:00"),
        ("9999-12-31T21:00:00-02:00", "9999-12-31T23:00:00+00:00"),
    ],
)
def test_rollback_preserves_representable_year_boundaries(timestamp, canonical):
    payload = IDENTITY | {"target_started_at": timestamp}
    REGISTRY.event_types["pdlc.service.rolledback"].definition.payload_contract.validate_payload(
        payload
    )
    assert payload["target_started_at"] == timestamp
    result = plan("rolledback", payload)
    assert result.states[0].ref.key == "Deployment:acme/app|api|prod|abc|" + canonical


async def test_frozen_rollback_checkpoint_manifests_match_exact_retrieval():
    import json
    import sys
    from pathlib import Path

    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from context_graph.worker.pack_projection import apply_plan

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from engram_goal07_deployment_fixtures import fixtures

    data = fixtures("exact-rollback")
    graph = PackGraphBoundary()
    retriever = ArtifactRetriever(
        graph,
        REGISTRY,
        default_max_depth=5,
        seed_limit=10,
        neighbor_limit=100,
        provenance_source="boundary",
    )
    for step in data["steps"]:
        if step["expected_status"] != 201:
            continue
        request = step["request"]
        event = Event.model_validate_json(
            json.dumps(
                {k: v for k, v in request.items() if k != "payload"} | {"global_position": "1-0"}
            )
        )
        await graph.upsert_nodes(
            [
                NodeWrite(
                    NodeRef("Event", str(event.event_id), "event_id"),
                    json.loads(event.model_dump_json()),
                )
            ]
        )
        await apply_plan(
            graph,
            PackProjector(REGISTRY, frozenset({"deployment.publisher"})).plan(
                event, {"payload": request["payload"]}
            ),
            100,
        )
        for query in data["queries"]:
            if query["after_scenario"] != step["scenario"]:
                continue
            assert query["exact"] is True
            response = await retriever.retrieve(
                ArtifactQuery(
                    query=query["request"]["query"],
                    intent="trace",
                    seed_node_ids=tuple(query["request"]["seed_node_ids"]),
                )
            )
            assert set(response.nodes) == set(query["required_nodes"]), query["scenario"]
            assert {(e.edge_type, e.source, e.target) for e in response.edges} == {
                tuple(edge) for edge in query["expected_edges"]
            }, query["scenario"]
            for node_id, expected in query["expected_observation_events"].items():
                provenance = response.nodes[node_id].provenance
                assert (provenance.event_id if provenance else None) == expected
