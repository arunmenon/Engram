"""G07-A public contract, projection-plan and artifact retrieval checks; no backend."""

from datetime import UTC, datetime
from uuid import UUID

from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.ontology import load_registry

REGISTRY = load_registry(["pdlc"])
EVENT_ID = UUID("00000000-0000-0000-0000-000000000054")


def plan(event_type, payload):
    REGISTRY.event_types[event_type].definition.payload_contract.validate_payload(payload)
    event = Event(
        event_id=EVENT_ID,
        event_type=event_type,
        occurred_at=datetime(2026, 10, 8, tzinfo=UTC),
        session_id="g07-a",
        agent_id="producer",
        trace_id="g07-a",
        payload_ref="payload",
        global_position="54-0",
    )
    return PackProjector(REGISTRY, frozenset({"producer"})).plan(event, {"payload": payload})


def test_created_request_has_exact_scoped_identity_content_initial_state_and_evidence():
    result = plan(
        "pdlc.request.created",
        {
            "source_system": "product",
            "external_id": "RESET-REQUEST",
            "title": "Prevent expired token use",
            "description": "Reject password-reset tokens after fifteen minutes",
        },
    )
    assert not result.rejected
    assert len(result.nodes) == 1
    node = result.nodes[0]
    assert node.ref.key == "Request:product|RESET-REQUEST"
    assert (
        node.properties.items()
        >= {
            "source_system": "product",
            "external_id": "RESET-REQUEST",
            "title": "Prevent expired token use",
            "description": "Reject password-reset tokens after fifteen minutes",
            "source_trust": "trusted",
        }.items()
    )
    assert node.defaults["status"] == "new"
    assert [(e.edge_type, e.source.key, e.target.key) for e in result.edges] == [
        ("DERIVED_FROM", "Request:product|RESET-REQUEST", str(EVENT_ID))
    ]


class ReadGraph:
    """Read-only PackGraph boundary fixture, with independently supplied rows."""

    def __init__(self, nodes, edges=()):
        self.nodes = nodes
        self.edges = edges

    async def get_nodes(self, refs):
        return {ref: self.nodes[ref.key] for ref in refs if ref.key in self.nodes}

    async def find_nodes(self, label, equals, limit):
        return [
            props
            for props in self.nodes.values()
            if props["node_type"] == label and all(props.get(k) == v for k, v in equals.items())
        ][:limit]

    async def search_nodes(self, label, fields, terms, limit):
        matches = []
        for props in self.nodes.values():
            if props["node_type"] != label:
                continue
            count = sum(
                any(term in str(props.get(f, "")).lower() for f in fields) for term in terms
            )
            if count:
                matches.append((props, count))
        return sorted(matches, key=lambda row: (-row[1], row[0]["node_id"]))[:limit]

    async def neighbors(self, refs, edge_types, direction, limit):
        keys = {ref.key for ref in refs}
        rows = []
        for kind, source, target, properties in self.edges:
            if edge_types is not None and kind not in edge_types:
                continue
            other = None
            if source in keys and direction in ("out", "both"):
                other = target
            elif target in keys and direction in ("in", "both"):
                other = source
            if other is not None:
                rows.append(
                    dict(
                        edge_type=kind,
                        properties=properties,
                        source_label=self.nodes[source]["node_type"],
                        source_key=source,
                        target_label=self.nodes[target]["node_type"],
                        target_key=target,
                        node_label=self.nodes[other]["node_type"],
                        node=self.nodes[other],
                    )
                )
        return sorted(rows, key=lambda r: (r["edge_type"], r["source_key"], r["target_key"]))[
            :limit
        ]


def retriever(graph):
    from context_graph.retrieval.artifacts import ArtifactRetriever

    return ArtifactRetriever(
        graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=20,
        neighbor_limit=100,
        provenance_source="spanner",
    )


async def test_request_is_discoverable_from_natural_language_without_given_seed():
    from context_graph.retrieval.artifacts import ArtifactQuery

    request = "Request:product|RESET-REQUEST"
    graph = ReadGraph(
        {
            request: dict(
                node_id=request,
                node_type="Request",
                source_system="product",
                external_id="RESET-REQUEST",
                title="Prevent expired token use",
                status="new",
                source_trust="trusted",
            )
        }
    )
    answer = await retriever(graph).retrieve(ArtifactQuery(query="Prevent expired token use"))
    assert set(answer.nodes) == {request}
    assert not answer.meta.truncated


def test_titleless_request_and_cross_source_collision_keep_separate_identities():
    for source in ("product", "support"):
        result = plan(
            "pdlc.request.created", dict(source_system=source, external_id="RESET-REQUEST")
        )
        assert not result.rejected
        assert len(result.nodes) == 1
        assert result.nodes[0].ref.key == f"Request:{source}|RESET-REQUEST"
        assert result.nodes[0].defaults["status"] == "new"
        assert result.nodes[0].properties.get("title") is None


def test_malformed_request_identities_are_rejected_at_admission_without_a_write_plan():
    import pytest
    from pydantic import ValidationError

    for name in ("source_system", "external_id"):
        base = dict(source_system="product", external_id="RESET-REQUEST")
        for payload in (
            {k: v for k, v in base.items() if k != name},
            {**base, name: None},
            {**base, name: []},
            {**base, name: ""},
        ):
            with pytest.raises(ValidationError):
                plan("pdlc.request.created", payload)


def test_approved_spec_refines_only_its_explicit_source_scoped_request():
    result = plan(
        "pdlc.spec.approved",
        dict(
            doc_id="RESET-PRD",
            version="1",
            request_system="product",
            request_ids=["RESET-REQUEST"],
        ),
    )
    assert not result.rejected
    assert [(s.ref.key, s.to_state) for s in result.states] == [("Spec:RESET-PRD|1", "approved")]
    assert {(e.edge_type, e.source.key, e.target.key) for e in result.edges} == {
        ("DERIVED_FROM", "Spec:RESET-PRD|1", str(EVENT_ID)),
        ("REFINES", "Spec:RESET-PRD|1", "Request:product|RESET-REQUEST"),
    }
    edge = next(e for e in result.edges if e.edge_type == "REFINES")
    assert edge.properties == dict(
        confidence=1.0, method="declared", link_status="confirmed", source_trust="trusted"
    )


D1 = "Decision:0e5a32cc0b91694dda1beff8480461f5a0750d2fb9b69e31b22c7fa8d67c85d7"
D2 = "Decision:f034f628d70ae8e6027dace07e68145ce5887143889b820d6bfc54c79b64d2df"
REQUIREMENT = "Requirement:RESET-PRD|1|expiry"
DESIGN = "DesignElement:RESET-HLD|tokens|1"


def test_decision_hash_state_and_scope_accept_only_explicit_permitted_typed_endpoints():
    result = plan(
        "pdlc.decision.recorded",
        dict(
            statement="Check token expiry on the server",
            rationale="Clients cannot enforce expiry",
            applies_to_node_ids=[
                REQUIREMENT,
                DESIGN,
                "Request:product|RESET-REQUEST",
                "Unknown:42",
                "no-type",
                "DesignElement:",
            ],
        ),
    )
    assert not result.rejected
    observed = [n for n in result.nodes if n.properties.get("source_trust") == "trusted"]
    assert [n.ref.key for n in observed] == [D1]
    assert observed[0].properties["rationale"] == "Clients cannot enforce expiry"
    assert [(s.ref.key, s.to_state) for s in result.states] == [(D1, "accepted")]
    assert {(e.edge_type, e.source.key, e.target.key) for e in result.edges} == {
        ("DERIVED_FROM", D1, str(EVENT_ID)),
        ("APPLIES_TO", D1, REQUIREMENT),
        ("APPLIES_TO", D1, DESIGN),
    }
    assert all(
        e.properties.get("link_status") == "confirmed"
        for e in result.edges
        if e.edge_type == "APPLIES_TO"
    )
    # node_id references address existing nodes; they never fabricate their observations.
    assert not any(n.ref.key in (REQUIREMENT, DESIGN) for n in result.nodes)


def test_replacement_decision_has_only_the_explicit_supersession_and_no_inferred_scope():
    replacement = plan(
        "pdlc.decision.recorded",
        dict(
            statement="Validate token expiry before loading the account",
            supersedes_hash=D1.split(":")[1],
        ),
    )
    assert {(e.edge_type, e.source.key, e.target.key) for e in replacement.edges} == {
        ("DERIVED_FROM", D2, str(EVENT_ID)),
        ("SUPERSEDES", D2, D1),
    }
    similar = plan("pdlc.decision.recorded", dict(statement="Check token expiry on the server too"))
    assert [e.edge_type for e in similar.edges] == ["DERIVED_FROM"]


def request_graph():
    request, other, spec = (
        "Request:product|RESET-REQUEST",
        "Request:support|RESET-REQUEST",
        "Spec:RESET-PRD|1",
    )
    nodes = {
        request: dict(
            source_system="product",
            external_id="RESET-REQUEST",
            title="Prevent expired token use",
            status="new",
        ),
        other: dict(
            source_system="support",
            external_id="RESET-REQUEST",
            title="Prevent expired token use",
            status="new",
        ),
        spec: dict(
            doc_id="RESET-PRD", version="1", title="Token expiry specification", status="approved"
        ),
    }
    nodes = {
        nid: dict(props, node_id=nid, node_type=nid.split(":")[0], source_trust="trusted")
        for nid, props in nodes.items()
    }
    return ReadGraph(
        nodes,
        [
            (
                "REFINES",
                spec,
                request,
                dict(
                    confidence=1.0,
                    method="declared",
                    link_status="confirmed",
                    source_trust="trusted",
                ),
            )
        ],
    )


async def test_request_spec_forward_and_reverse_retrieval_excludes_cross_source_collision():
    from context_graph.retrieval.artifacts import ArtifactQuery

    for seed in ("Request:product|RESET-REQUEST", "Spec:RESET-PRD|1"):
        answer = await retriever(request_graph()).retrieve(
            ArtifactQuery(query="trace", seed_node_ids=(seed,), intent="trace", max_depth=1)
        )
        assert set(answer.nodes) == {"Request:product|RESET-REQUEST", "Spec:RESET-PRD|1"}
        assert {(e.edge_type, e.source, e.target) for e in answer.edges} == {
            ("REFINES", "Spec:RESET-PRD|1", "Request:product|RESET-REQUEST"),
        }
        assert not answer.meta.truncated


async def test_titleless_request_remains_accessible_by_exact_typed_id():
    from context_graph.retrieval.artifacts import ArtifactQuery

    nid = "Request:product|MINIMAL"
    graph = ReadGraph(
        {
            nid: dict(
                node_id=nid,
                node_type="Request",
                source_system="product",
                external_id="MINIMAL",
                status="new",
                source_trust="trusted",
            )
        }
    )
    answer = await retriever(graph).retrieve(
        ArtifactQuery(query="", seed_node_ids=(nid,), intent="trace")
    )
    assert set(answer.nodes) == {nid}
    assert answer.nodes[nid].attributes["status"] == "new"


async def test_decision_status_keeps_historical_label_and_evidence_but_trace_excludes_history():
    from context_graph.retrieval.artifacts import ArtifactQuery

    event_key = str(EVENT_ID)
    nodes = {
        D1: dict(statement="Check token expiry on the server", status="accepted"),
        D2: dict(statement="Validate token expiry before loading the account", status="accepted"),
        DESIGN: dict(title="Token expiry design", status="approved"),
    }
    nodes = {
        nid: dict(props, node_id=nid, node_type=nid.split(":")[0], source_trust="trusted")
        for nid, props in nodes.items()
    }
    nodes[event_key] = dict(
        event_id=event_key,
        node_type="Event",
        occurred_at="2026-10-08T00:00:00+00:00",
        global_position="54-0",
    )
    # Event keys use the Event port identity rather than a typed node_id.
    graph = ReadGraph(
        nodes,
        [
            ("SUPERSEDES", D2, D1, dict(source_trust="trusted")),
            (
                "APPLIES_TO",
                D1,
                DESIGN,
                dict(
                    confidence=1.0,
                    method="declared",
                    link_status="confirmed",
                    source_trust="trusted",
                ),
            ),
            (
                "APPLIES_TO",
                D2,
                DESIGN,
                dict(
                    confidence=1.0,
                    method="declared",
                    link_status="confirmed",
                    source_trust="trusted",
                ),
            ),
            ("DERIVED_FROM", D1, event_key, {}),
            ("DERIVED_FROM", D2, event_key, {}),
        ],
    )
    for intent, expected in (("status", {D1, D2, DESIGN}), ("trace", {DESIGN})):
        answer = await retriever(graph).retrieve(
            ArtifactQuery(query="", seed_node_ids=(DESIGN,), intent=intent, max_depth=2)
        )
        assert set(answer.nodes) == expected
        if intent == "status":
            assert answer.nodes[D1].retrieval_reason == "superseded"
            assert answer.nodes[D2].retrieval_reason != "superseded"
            assert answer.nodes[D1].provenance.event_id == event_key
            assert answer.nodes[D2].provenance.event_id == event_key
            assert {(e.edge_type, e.source, e.target) for e in answer.edges} == {
                ("SUPERSEDES", D2, D1),
                ("APPLIES_TO", D1, DESIGN),
                ("APPLIES_TO", D2, DESIGN),
            }
        assert not answer.meta.truncated


def slice_a_fixtures():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts/engram_goal07_requests_fixtures.py"
    spec = importlib.util.spec_from_file_location("g07_a_fixtures", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fixtures("local-a", start=datetime(2026, 10, 8, tzinfo=UTC))


def test_predeclared_slice_a_inputs_match_admission_and_observed_plan_identities():
    import pytest
    from pydantic import ValidationError

    originals = {}
    for step in slice_a_fixtures()["steps"]:
        request = step["request"]
        if step["expected_status"] == 422:
            with pytest.raises(ValidationError):
                plan(request["event_type"], request["payload"])
            continue
        result = plan(request["event_type"], request["payload"])
        assert not result.rejected
        if step.get("duplicate"):
            assert request == originals[request["event_id"]]
        elif step["expected_status"] == 409:
            assert request != originals[request["event_id"]]
        else:
            originals[request["event_id"]] = request
            assert {
                n.ref.key for n in result.nodes if n.properties.get("source_trust") == "trusted"
            } == {step["expected_node"]}


async def test_predeclared_slice_a_query_sets_are_consistent_at_retrieval_boundary():
    from context_graph.retrieval.artifacts import ArtifactQuery

    data = slice_a_fixtures()
    nodes, edges = {}, []
    for step in data["steps"]:
        if step["expected_status"] != 201 or step.get("duplicate"):
            continue
        nid = step["expected_node"]
        nodes[nid] = dict(
            step["expected_props"], node_id=nid, node_type=nid.split(":")[0], source_trust="trusted"
        )
        for kind, source, target in step["expected_edges"]:
            edges.append(
                (
                    kind,
                    source,
                    target,
                    dict(
                        confidence=1.0,
                        method="declared",
                        link_status="confirmed",
                        source_trust="trusted",
                    ),
                )
            )
    for query in data["queries"]:
        answer = await retriever(ReadGraph(nodes, edges)).retrieve(
            ArtifactQuery(
                query=query["text"],
                seed_node_ids=tuple(query["seeds"]),
                intent=query["intent"],
                max_depth=query["max_depth"],
            )
        )
        assert set(answer.nodes) == set(query["required"]), query["scenario"]
        assert {(e.edge_type, e.source, e.target) for e in answer.edges} == {
            tuple(e) for e in query["expected_edges"]
        }, query["scenario"]
        for nid, reason in query.get("expected_retrieval_reasons", {}).items():
            assert answer.nodes[nid].retrieval_reason == reason
        assert not answer.meta.truncated
