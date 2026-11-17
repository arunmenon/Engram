"""Opt-in acceptance on a registered disposable workbench Spanner sandbox.

Set ENGRAM_SEED_MODE_SPANNER_POOL to the server-owned pool JSON. This claims and
cleans a registered sandbox slot through the normal fencing path; never point it
at customer databases. Authentication uses the normal Google client credentials.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.ontology.loader import load_registry
from context_graph.ports.pack_graph import NodeRef, NodeWrite
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever, UnresolvedSeedsError
from context_graph.workbench.models import Content
from context_graph.workbench.pool_config import configured_execution
from context_graph.workbench.sandbox import run_sandbox

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.environ.get("ENGRAM_SEED_MODE_SPANNER_POOL"),
        reason="Requires an explicitly selected registered disposable Spanner sandbox pool",
    ),
]


def execution():
    return configured_execution(Path(os.environ["ENGRAM_SEED_MODE_SPANNER_POOL"]))


def record(name, result):
    output = os.environ.get("ENGRAM_SEED_MODE_EVIDENCE_DIR")
    if output:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.json").write_text(json.dumps(result, indent=2, default=str) + "\n")


@pytest.mark.parametrize("mode,expected", [("discover", 0.65), ("explicit", 1.0)])
async def test_northstar_spanner(mode, expected):
    fixture = json.loads(Path("tests/fixtures/workbench/northstar-seed-mode.json").read_text())
    content = Content.model_validate(fixture["content"])
    for question in content.questions:
        question.seed_mode = mode
    pool = execution()
    try:
        result = await run_sandbox(content, fixture["pack"], execution=pool)
    finally:
        await pool.close()
    record(f"northstar-{mode}", result)
    assert result["backend"] == "spanner"
    assert result["evaluation"]["mean_f1"] == expected
    assert result["passed"] == (mode == "explicit")
    assert result["storage"]["phase"] == "released"
    assert [r["expected"] for r in result["evaluation"]["questions"]] == [
        sorted(q.expected) for q in content.questions
    ]


async def test_spanner_missing_selection_order_and_completeness(monkeypatch):
    pool = execution()
    registry = load_registry(["pdlc"])
    bundle = resolve_bundle(registry)
    ticket = "WorkItem:jira|SEED-1"
    absent = "WorkItem:jira|SEED-2"
    change = "Change:seed-mode/repo|7"
    try:
        async with pool.open(bundle, ["seed-mode-test"]) as runtime:
            graph = runtime.stores.graph
            await graph.ensure_pack_schema(registry, runtime.settings.embedding.dimensions)
            await graph.upsert_nodes(
                [
                    NodeWrite(
                        NodeRef("WorkItem", ticket),
                        {
                            "node_id": ticket,
                            "tracker": "jira",
                            "external_key": "SEED-1",
                            "title": "Seed selection acceptance",
                            "status": "todo",
                            "source_trust": "trusted",
                        },
                    ),
                    NodeWrite(
                        NodeRef("Change", change),
                        {
                            "node_id": change,
                            "repo": "seed-mode/repo",
                            "number": 7,
                            "source_trust": "trusted",
                        },
                    ),
                ]
            )
            engine = ArtifactRetriever(
                graph,
                registry,
                provenance_source="spanner",
                default_max_depth=3,
                seed_limit=20,
                neighbor_limit=100,
            )
            # No broadening via any text-discovery mechanism on the actual adapter.
            monkeypatch.setattr(
                graph, "search_nodes", AsyncMock(side_effect=AssertionError("search"))
            )
            monkeypatch.setattr(graph, "find_nodes", AsyncMock(side_effect=AssertionError("scan")))
            with pytest.raises(UnresolvedSeedsError) as raised:
                await engine.retrieve(
                    ArtifactQuery(
                        "trace SEED-1 #7",
                        seed_mode="explicit",
                        seed_node_ids=(ticket, absent),
                        intent="trace",
                    )
                )
            assert raised.value.unresolved == [absent]
            selected = await engine.retrieve(
                ArtifactQuery(
                    "trace SEED-1 #7",
                    seed_mode="explicit",
                    seed_node_ids=(change, ticket),
                    intent="trace",
                )
            )
            assert selected.meta.seed_nodes == [change, ticket]
            complete = await engine.retrieve(
                ArtifactQuery(
                    "Which tickets have no tests?",
                    seed_mode="explicit",
                    seed_node_ids=(ticket,),
                    intent="completeness",
                )
            )
            assert set(complete.nodes) == {ticket}
            assert complete.nodes[ticket].retrieval_reason == "no_link"
            result = {
                "missing_error": raised.value.reason,
                "selection": selected.model_dump(mode="json"),
                "completeness": complete.model_dump(mode="json"),
            }
        result["storage"] = dict(runtime.evidence)
        record("pdlc-strict-boundaries", result)
        assert result["storage"]["phase"] == "released"
    finally:
        await pool.close()
