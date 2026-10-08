"""G02 semantic regressions; local memory aids, not cloud acceptance."""

from datetime import UTC, datetime
from uuid import uuid4

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.projection import event_to_node
from context_graph.ontology import load_registry
from context_graph.ports.pack_graph import EdgeWrite, NodeRef
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.worker.pack_projection import apply_plan


async def write(graph, event_type, payload):
    event = Event(
        event_id=uuid4(),
        event_type=event_type,
        occurred_at=datetime.now(UTC),
        session_id="planning",
        agent_id="publisher",
        trace_id="t",
        payload_ref="p",
        global_position="1-0",
    )
    await graph.merge_event_node(event_to_node(event))
    registry = load_registry(["pdlc"])
    plan = PackProjector(registry, frozenset({"publisher"})).plan(event, {"payload": payload})
    assert not plan.rejected
    await apply_plan(graph, plan, 100)
    return str(event.event_id)


async def test_revision_approval_and_explicit_refinement_are_distinct():
    graph = MemoryGraphStore()
    await write(graph, "pdlc.spec.changed", dict(doc_id="reset", version="1", title="Reset"))
    for key in ["expiry", "single-use"]:
        await write(
            graph,
            "pdlc.requirement.changed",
            dict(spec_id="reset", spec_version="1", local_id=key, statement=key),
        )
    body = dict(
        doc_id="reset-hld",
        section_path="tokens",
        version="1",
        kind="hld",
        body="Token service",
        requirements=[
            dict(spec_id="reset", spec_version="1", local_id=k) for k in ["expiry", "single-use"]
        ],
    )
    await write(graph, "pdlc.design.section_changed", body)
    await write(
        graph,
        "pdlc.design.approval_recorded",
        dict(
            approval_id="a1",
            reviewer="alex",
            verdict="approved",
            doc_id="reset-hld",
            section_path="tokens",
            version="1",
        ),
    )
    await write(
        graph,
        "pdlc.design.section_changed",
        dict(body, version="2", body="Revised token service", supersedes_version="1"),
    )
    old = "DesignElement:reset-hld|tokens|1"
    new = "DesignElement:reset-hld|tokens|2"
    assert graph.nodes[("DesignElement", old)]["body"] == "Token service"
    assert graph.nodes[("DesignElement", new)]["body"] == "Revised token service"
    approval = [(a[1], b[1]) for a, e, b in graph.edges if e == "APPROVES"]
    assert approval == [("DesignApproval:a1", old)]
    refinements = {(a[1], b[1]) for a, e, b in graph.edges if e == "REFINES"}
    assert {
        (old, "Requirement:reset|1|expiry"),
        (old, "Requirement:reset|1|single-use"),
    } <= refinements
    engine = ArtifactRetriever(
        graph,
        load_registry(["pdlc"]),
        provenance_source="memory",
        default_max_depth=5,
        seed_limit=20,
        neighbor_limit=100,
    )
    answer = await engine.retrieve(
        ArtifactQuery(query="status " + new, seed_node_ids=(new,), intent="status")
    )
    assert {old, new, "DesignApproval:a1"} <= set(answer.nodes)
    assert any(e.edge_type == "APPROVES" and e.target == old for e in answer.edges)


async def test_missing_hld_is_visible_placeholder_then_filled_without_repair():
    graph = MemoryGraphStore()
    lld = dict(
        doc_id="reset-lld",
        section_path="storage",
        version="1",
        kind="lld",
        body="Store token digest",
        refines_designs=[dict(doc_id="reset-hld", section_path="late", version="1")],
    )
    await write(graph, "pdlc.design.section_changed", lld)
    ref = ("DesignElement", "DesignElement:reset-hld|late|1")
    assert ref in graph.nodes and "body" not in graph.nodes[ref]
    assert not any(a == ref and e == "DERIVED_FROM" for a, e, b in graph.edges)
    event = await write(
        graph,
        "pdlc.design.section_changed",
        dict(
            doc_id="reset-hld",
            section_path="late",
            version="1",
            kind="hld",
            body="Token storage architecture",
        ),
    )
    assert graph.nodes[ref]["body"] == "Token storage architecture"
    assert any(a == ref and e == "DERIVED_FROM" and b[1] == event for a, e, b in graph.edges)


async def test_connected_paths_keep_edges_without_expanding_to_siblings():
    graph = MemoryGraphStore()
    await write(graph, "pdlc.spec.changed", dict(doc_id="s", version="1", title="Spec"))
    for key in ["expiry", "unrelated"]:
        await write(
            graph,
            "pdlc.requirement.changed",
            dict(spec_id="s", spec_version="1", local_id=key, statement=key),
        )

    def req(key):
        return dict(spec_id="s", spec_version="1", local_id=key)

    await write(
        graph,
        "pdlc.design.section_changed",
        dict(
            doc_id="hld",
            section_path="tokens",
            version="1",
            kind="hld",
            body="Token architecture",
            requirements=[req("expiry")],
        ),
    )
    await write(
        graph,
        "pdlc.design.section_changed",
        dict(
            doc_id="lld",
            section_path="storage",
            version="1",
            kind="lld",
            body="Token storage",
            requirements=[req("expiry"), req("unrelated")],
            refines_designs=[dict(doc_id="hld", section_path="tokens", version="1")],
        ),
    )
    await write(
        graph,
        "pdlc.design.section_changed",
        dict(
            doc_id="other",
            section_path="unrelated",
            version="1",
            kind="hld",
            body="Other design",
            requirements=[req("expiry")],
        ),
    )
    engine = ArtifactRetriever(
        graph,
        load_registry(["pdlc"]),
        provenance_source="memory",
        default_max_depth=5,
        seed_limit=20,
        neighbor_limit=100,
    )
    seed = "DesignElement:hld|tokens|1"
    answer = await engine.retrieve(
        ArtifactQuery(query="trace " + seed, seed_node_ids=(seed,), intent="trace")
    )
    assert {"DesignElement:lld|storage|1", "Requirement:s|1|expiry"} <= set(answer.nodes)
    assert "DesignElement:other|unrelated|1" not in answer.nodes
    assert "Requirement:s|1|unrelated" not in answer.nodes
    assert any(
        e.edge_type == "REFINES"
        and e.source == "DesignElement:lld|storage|1"
        and e.target == "Requirement:s|1|expiry"
        for e in answer.edges
    )

    await graph.upsert_edges(
        [
            EdgeWrite(
                "REFINES",
                NodeRef("DesignElement", "DesignElement:lld|storage|1"),
                NodeRef("Requirement", "Requirement:s|1|expiry"),
                {"method": "declared", "confidence": 1.0, "link_status": "rejected"},
            )
        ]
    )
    answer = await engine.retrieve(
        ArtifactQuery(query="trace " + seed, seed_node_ids=(seed,), intent="trace")
    )
    assert {"DesignElement:lld|storage|1", "Requirement:s|1|expiry"} <= set(answer.nodes)
    assert not any(
        e.source == "DesignElement:lld|storage|1"
        and e.target == "Requirement:s|1|expiry"
        and e.edge_type == "REFINES"
        for e in answer.edges
    )
