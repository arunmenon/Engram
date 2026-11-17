"""Explicit artifact origins fail closed; discovery remains the legacy default."""

from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from context_graph.domain.ontology import OntologyError
from context_graph.ontology.evaluation import EvalSet, load_eval_set, run_eval_set
from context_graph.ports.pack_graph import NodeRef, NodeWrite
from context_graph.retrieval.artifacts import ArtifactQuery, UnresolvedSeedsError, _Result
from tests.unit.test_resolved_artifact_seeds import retriever

A = "Change:acme/payments|7"
B = "Change:acme/payments|8"
TICKET = "WorkItem:jira|APP-42"


def query(seeds=(A,), **kwargs):
    return ArtifactQuery(
        "trace APP-42 #8 Payment",
        seed_node_ids=seeds,
        intent="trace",
        seed_mode="explicit",
        **kwargs,
    )


async def test_explicit_disables_all_discovery_and_keeps_selection_order(monkeypatch):
    engine = await retriever()
    graph = engine._graph
    get = graph.get_nodes

    async def reversed_rows(refs):
        return dict(reversed(list((await get(refs)).items())))

    monkeypatch.setattr(graph, "get_nodes", reversed_rows)
    for method in ("search_nodes", "find_nodes"):
        monkeypatch.setattr(graph, method, AsyncMock(side_effect=AssertionError("discovery")))
    response = await engine.retrieve(query((B, A, TICKET, B)))
    assert response.meta.seed_nodes == [B, A, TICKET]
    assert response.meta.seed_strategy == "explicit_seeds"
    union = set()
    for seed in (B, A, TICKET):
        union.update((await engine.retrieve(query((seed,)))).nodes)
    assert set(response.nodes) == union


@pytest.mark.parametrize(
    "seeds,reason,unresolved",
    [
        ((), "empty", []),
        (("Unknown:x", "Change"), "unparseable", ["Unknown:x", "Change"]),
        ((A, "Change:absent|9"), "missing", ["Change:absent|9"]),
    ],
)
async def test_invalid_selection_fails_before_traversal(monkeypatch, seeds, reason, unresolved):
    engine = await retriever()
    traverse = AsyncMock()
    monkeypatch.setattr(engine, "_traverse", traverse)
    with pytest.raises(UnresolvedSeedsError) as raised:
        await engine.retrieve(query(seeds))
    assert raised.value.reason == reason
    assert raised.value.unresolved == unresolved
    traverse.assert_not_awaited()


async def test_identity_roundtrip_failure(monkeypatch):
    engine = await retriever()
    monkeypatch.setattr(
        engine._graph, "get_nodes", AsyncMock(return_value={NodeRef("Change", A): {"node_id": B}})
    )
    with pytest.raises(UnresolvedSeedsError, match="do not exist"):
        await engine.retrieve(query())


async def test_seed_resolution_budget_and_capacity():
    engine = await retriever()
    engine._max_calls = 0
    with pytest.raises(UnresolvedSeedsError) as raised:
        await engine.retrieve(query())
    assert raised.value.reason == "budget"
    default = await engine.retrieve(replace(query(), seed_mode="discover"))
    assert not default.nodes and default.meta.truncated
    engine._max_calls = 400
    with pytest.raises(UnresolvedSeedsError) as raised:
        await engine.retrieve(query((A, B, TICKET), max_nodes=2))
    assert raised.value.reason == "over_capacity"
    default = await engine.retrieve(
        replace(query((A, B, TICKET), max_nodes=2), seed_mode="discover")
    )
    assert default.meta.truncated


async def test_given_untrusted_seed_keeps_existing_admission():
    engine = await retriever()
    await engine._graph.upsert_nodes(
        [NodeWrite(NodeRef("Change", B), {"node_id": B, "source_trust": "untrusted"})]
    )
    response = await engine.retrieve(query((B,)))
    assert response.nodes[B].retrieval_reason == "direct"


@pytest.mark.parametrize("seed", [TICKET, "Change:absent|7", B])
async def test_completeness_never_scans_global_scope(monkeypatch, seed):
    engine = await retriever()
    scan = AsyncMock(side_effect=AssertionError("global scan"))
    monkeypatch.setattr(engine, "_all_of", scan)
    q = ArtifactQuery(
        "Which tickets have no tests?",
        seed_node_ids=(seed,),
        intent="completeness",
        seed_mode="explicit",
    )
    if "absent" in seed:
        with pytest.raises(UnresolvedSeedsError):
            await engine.retrieve(q)
    else:
        result = await engine.retrieve(q)
        assert not result.meta.truncated
        assert result.meta.seed_strategy == "explicit_seeds"
        assert result.meta.retrieval_channels
        if seed == B:
            assert result.nodes == {}  # a valid selected change with no subject descendants
    scan.assert_not_awaited()
    # Exercise the defensive guard independently of the resolver's fail-closed contract.
    assert await engine._completeness_scope(q, "WorkItem", "VERIFIES", _Result(), 3) == []
    scan.assert_not_awaited()


def test_yaml_default_explicit_and_invalid_mode(tmp_path):
    path = tmp_path / "pdlc.eval.yaml"
    path.write_text("""pack: pdlc
questions:
- id: explicit
  query: trace
  expected: []
  seed_mode: explicit
- id: legacy
  query: trace
  expected: []
""")
    loaded = load_eval_set(path)
    assert [q.seed_mode for q in loaded.questions] == ["explicit", "discover"]
    path.write_text(path.read_text().replace("seed_mode: explicit", "seed_mode: strict"))
    with pytest.raises(OntologyError, match="seed_mode"):
        load_eval_set(path)
    with pytest.raises(ValidationError):
        EvalSet.model_validate(
            {
                "pack": "pdlc",
                "questions": [dict(id="bad", query="trace", expected=[], seed_mode="strict")],
            }
        )


async def test_question_error_cannot_pass_gate_even_if_mean_passes():
    engine = await retriever()
    questions = [
        dict(
            id="bad",
            query="trace",
            seed_mode="explicit",
            seed_node_ids=["Change:absent|9"],
            expected=[],
        )
    ]
    questions += [
        dict(id=f"valid-{i}", query="trace", seed_mode="explicit", seed_node_ids=[B], expected=[B])
        for i in range(9)
    ]
    report = await run_eval_set(
        EvalSet.model_validate(dict(pack="pdlc", min_f1=0.8, questions=questions)),
        engine,
        max_nodes=100,
    )
    assert report.mean_f1 == 0.9 and not report.passed
    assert len(report.results) == 10
    assert report.results[0].error and report.results[0].f1 == 0
    assert report.as_dict()["questions"][0]["error"]
    assert all(r.error is None for r in report.results[1:])


@pytest.mark.parametrize("mode,expected", [("discover", 0.65), ("explicit", 1.0)])
async def test_northstar_real_projection_and_frozen_answers(mode, expected):
    import json
    from pathlib import Path

    from context_graph.workbench.models import Content
    from context_graph.workbench.sandbox import run_sandbox

    fixture = json.loads(Path("tests/fixtures/workbench/northstar-seed-mode.json").read_text())
    content = Content.model_validate(fixture["content"])
    original_answers = [q.expected[:] for q in content.questions]
    for question in content.questions:
        question.seed_mode = mode
    result = await run_sandbox(content, fixture["pack"])
    assert result["evaluation"]["mean_f1"] == expected
    assert result["passed"] == (mode == "explicit")
    assert [q["expected"] for q in result["evaluation"]["questions"]] == [
        sorted(answer) for answer in original_answers
    ]
    assert not result["dead_letters"]


async def test_valid_explicit_empty_answer_is_not_an_execution_error():
    engine = await retriever()
    evaluation = EvalSet.model_validate(
        {
            "pack": "pdlc",
            "questions": [
                {
                    "id": "valid-empty",
                    "query": "Which tickets have no tests?",
                    "intent": "completeness",
                    "seed_node_ids": [B],
                    "seed_mode": "explicit",
                    "expected": [],
                    "answer": {"node_type": "WorkItem"},
                }
            ],
        }
    )
    report = await run_eval_set(evaluation, engine, max_nodes=100)
    assert report.passed and report.mean_f1 == 1.0
    assert report.results[0].found == [] and report.results[0].error is None
