import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from engram_pilot_retrieval_proof import closed_response, freeze, observe_vectors, vector_chain

from context_graph.domain.models import Event, SubgraphQuery
from context_graph.ports.search import SearchHit


def test_frozen_inputs_valid_and_distinct():
    plan = freeze("unit-p08")
    events = [s["request"] for g in plan["groups"] for s in g["steps"]]
    assert len(events) == len({e["event_id"] for e in events}) == 9
    for event in events:
        Event.model_validate_json(json.dumps(event))
    b = plan["groups"][0]
    assert b["title"] != b["paraphrase"]
    assert b["trusted"] != b["untrusted"]
    assert b["steps"][-1]["role"] == "untrusted"
    assert (
        b["steps"][-1]["request"]["payload"]["title"]
        == b["steps"][-2]["request"]["payload"]["title"]
    )


def proof():
    emb = [0.1] * 384
    state = dict(
        nodes=[
            ["Entity", "entity:VegaLedger", dict(name="VegaLedger")],
            ["Event", "source", dict(global_position="position")],
        ],
        edges=[["Event", "source", "REFERENCES", "Entity", "entity:VegaLedger", {}]],
    )
    body = dict(
        nodes={
            "source": dict(
                node_type="Event",
                provenance=dict(event_id="source", global_position="position", source="spanner"),
            )
        },
        edges=[],
    )
    row = dict(
        ann=[
            dict(
                sql="APPROX_COSINE_DISTANCE FORCE_INDEX=EntityEmbedding",
                parameters=dict(query=emb),
                dimensions=384,
                rows=[["entity:VegaLedger", {}, 0.2]],
            )
        ],
        nearest=[dict(embedding=emb, hits=[dict(id="entity:VegaLedger")])],
        seeds=[dict(embedding=emb, events=[["source", 0.8]])],
    )
    return row, state, body


def test_full_vector_chain_and_provenance_closure():
    row, state, body = proof()
    assert vector_chain(row, state, "source", body, "VegaLedger")
    assert closed_response(body, state)


@pytest.mark.parametrize(
    "missing", ["ann", "nearest", "seeds", "references", "return", "embedding", "identity", "index"]
)
def test_partial_vector_proofs_rejected(missing):
    row, state, body = proof()
    if missing in {"ann", "nearest", "seeds"}:
        row[missing] = []
    if missing == "references":
        state["edges"] = []
    if missing == "return":
        body["nodes"] = {}
    if missing == "embedding":
        row["ann"][0]["parameters"]["query"] = [0.2] * 384
    if missing == "identity":
        row["nearest"][0]["hits"][0]["id"] = "foreign"
    if missing == "index":
        row["ann"][0]["sql"] = "fallback"
    assert not vector_chain(row, state, "source", body, "VegaLedger")


def test_dangling_edge_and_wrong_source_position_rejected():
    _, state, body = proof()
    body["edges"] = [dict(source="source", target="missing")]
    assert not closed_response(body, state)
    body["edges"] = []
    body["nodes"]["source"]["provenance"]["global_position"] = "wrong"
    assert not closed_response(body, state)


@pytest.mark.asyncio
async def test_observer_preserves_results_failures_and_task_context():
    record = {}
    calls = []
    graph = SimpleNamespace(_dimensions=384)

    async def query(*args, **kwargs):
        calls.append((args, kwargs))
        return [("entity:VegaLedger", dict(name="VegaLedger"), 0.2)]

    graph._query = query

    async def nearest(embedding, **kwargs):
        await graph._query("APPROX_COSINE_DISTANCE FORCE_INDEX=Index", dict(query=embedding), {})
        return [SearchHit(id="entity:VegaLedger", rank=0, score=0.9)]

    index = SimpleNamespace(nearest=nearest)

    async def seeds(embedding, limit):
        await index.nearest(embedding, top_k=limit, threshold=0.5)
        return [("source", 0.9)]

    engine = SimpleNamespace(_vector_index=index, _get_vector_seeds=seeds)
    result = object()

    async def read(q):
        if q.query == "fail":
            raise ValueError("unchanged failure")
        await engine._get_vector_seeds([0.1] * 384, 10)
        return result

    engine.get_subgraph = read
    observe_vectors(
        SimpleNamespace(state=SimpleNamespace(retrieval=engine, graph_store=graph)),
        "a",
        record,
        lambda: None,
    )
    q = SubgraphQuery(query="VegaLedger", session_id="s", agent_id="a")
    assert await engine.get_subgraph(q) is result
    row = record["vector_observations"][0]
    assert row["state"] == "returned" and row["ann"] and row["nearest"] and row["seeds"]
    old = deepcopy(row)
    await graph._query("APPROX_COSINE_DISTANCE", {}, {})
    assert row == old
    with pytest.raises(ValueError, match="unchanged failure"):
        await engine.get_subgraph(q.model_copy(update={"query": "fail"}))
    assert record["vector_observations"][-1]["state"] == "failed"
    await graph._query("APPROX_COSINE_DISTANCE", {}, {})
    assert not record["vector_observations"][-1]["ann"]
    assert calls[0][0][1] == dict(query=[0.1] * 384)


def test_entity_without_own_receipt_requires_stored_source_path():
    _, state, body = proof()
    state["nodes"][0][2]["entity_id"] = "entity:VegaLedger"
    body["nodes"]["entity:VegaLedger"] = dict(
        node_type="Entity",
        attributes=dict(name="VegaLedger", entity_id="entity:VegaLedger"),
        provenance=None,
    )
    body["edges"] = [dict(source="source", target="entity:VegaLedger", edge_type="REFERENCES")]
    assert closed_response(body, state)
    changed = deepcopy(state)
    changed["edges"] = []
    assert not closed_response(body, changed)
    changed = deepcopy(body)
    changed["nodes"]["source"]["provenance"]["global_position"] = "wrong"
    assert not closed_response(changed, state)
    changed = deepcopy(body)
    changed["nodes"]["entity:VegaLedger"]["attributes"]["name"] = "invented"
    assert not closed_response(changed, state)
    changed = deepcopy(body)
    changed["nodes"]["entity:VegaLedger"]["node_type"] = "Goal"
    assert not closed_response(changed, state)


@pytest.fixture(scope="module")
def retained_case():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    plan = json.loads((root / "docs/pilot/pilot-p08-1016-02-journeys.json").read_text())
    original = root / plan["retained_retrieval_proof"]["directory"]
    states = {
        t: json.loads((original / (t + "-final-state.json")).read_text())["snapshot"]
        for t in ("a", "b")
    }
    return plan, states


def test_retained_full_flow_source_proof(retained_case):
    from engram_pilot_retrieval_proof import retained_sources

    plan, states = retained_case
    result = retained_sources(plan, states)
    assert result["accepted_inputs"] == 9 and result["original_verdict"] == "failed"
    assert result["unrelated_background_provider_failure"]["error_type"] == "InternalServerError"


def test_changed_retained_proof_or_question_rejected(retained_case):
    from engram_pilot_retrieval_proof import retained_sources

    plan, states = retained_case
    changed = deepcopy(plan)
    changed["retained_retrieval_proof"]["sha256"]["results.json"] = "0" * 64
    with pytest.raises(ValueError, match="proof changed"):
        retained_sources(changed, states)
    changed = deepcopy(plan)
    changed["groups"][0]["paraphrase"] = "easier changed question"
    with pytest.raises(ValueError, match="source or question changed"):
        retained_sources(changed, states)


@pytest.mark.parametrize("corruption", [None, "unlabelled", "business", "edge", "receipt"])
async def test_unresolved_reference_requires_declaring_source_and_explicit_label(corruption):
    from engram_pilot_retrieval_proof import pilot_pdlc_registry

    from context_graph.domain.event_acceptance import AdmissionContext, stamp_acceptance
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
    from tests.unit.test_pack_projection import Harness

    h = Harness()
    h.projector = PackProjector(pilot_pdlc_registry(), frozenset({"webhook:github"}))
    payload = dict(
        doc_id="stub-proof",
        version="1",
        title="Reference proof",
        request_system="jira",
        request_ids=["MISSING"],
    )
    event = await h.ingest("pdlc.spec.approved", payload)
    authority = AdmissionContext(
        tenant_id="isolation-b",
        database_resource="projects/portiq-mvp/instances/engram-experiment/databases/engram-g07-target",
        binding_id="test-binding",
        accepted_epoch=7,
        bundle_digest="sha256:" + "1" * 64,
        engine_revision="test",
        source_id="demo.query",
    )
    acceptance = stamp_acceptance(authority, event, payload)
    state = dict(
        nodes=[[label, key, props] for (label, key), props in h.graph.nodes.items()],
        edges=[
            [a[0], a[1], kind, b[0], b[1], props] for (a, kind, b), props in h.graph.edges.items()
        ],
        events=[
            [
                str(event.event_id),
                {**event.model_dump(mode="json"), "payload": payload},
                acceptance.model_dump(),
            ]
        ],
    )
    retriever = ArtifactRetriever(
        h.graph,
        h.projector.registry,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="spanner",
    )
    body = (
        await retriever.retrieve(
            ArtifactQuery(
                query="Trace this artifact", intent="trace", seed_node_ids=["Spec:stub-proof|1"]
            )
        )
    ).model_dump(mode="json")
    nid = "Request:jira|MISSING"
    if corruption == "unlabelled":
        body["nodes"][nid]["attributes"].pop("reference_state")
    elif corruption == "business":
        body["nodes"][nid]["attributes"]["title"] = "Invented factual title"
    elif corruption == "edge":
        for edge in body["edges"]:
            if nid in (edge["source"], edge["target"]):
                edge["edge_type"] = "RELATED_TO"
    elif corruption == "receipt":
        state["events"] = []
    assert closed_response(body, state) == (corruption is None)
