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
