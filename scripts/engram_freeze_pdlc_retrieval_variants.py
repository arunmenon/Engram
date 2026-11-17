"""Freeze source-authored PDLC retrieval setups; no runtime imports of test code."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from fastapi.encoders import jsonable_encoder

from context_graph.workbench.journey_runner import graph_snapshot
from context_graph.workbench.journeys import Journey, retrieval_trust_journey


async def build_variants() -> dict[str, Journey]:
    spec = importlib.util.spec_from_file_location(
        "pdlc_variant_source", "tests/unit/test_pdlc_retrieval_eval.py"
    )
    source = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = source
    spec.loader.exec_module(source)
    counter = 0

    def fixed_uuid():
        nonlocal counter
        counter += 1
        return uuid5(NAMESPACE_URL, f"engram/pdlc-variants/{counter}")

    source.uuid4 = fixed_uuid
    variants = {}
    base = retrieval_trust_journey().model_dump()

    async def save(name, title, graph, function, queries):
        source_ref = "tests/unit/test_pdlc_retrieval_eval.py::" + function
        snapshot = jsonable_encoder(graph_snapshot(graph))
        data = dict(
            base,
            id="pdlc-" + name,
            title=title,
            story=title + ". Run the saved questions against this isolated example graph. "
            "Expected answers are preserved from the existing tests. "
            "This verifies retrieval, not ingestion or extraction.",
            source_refs=[source_ref],
            starting_state=dict(kind="graph_fixture", **snapshot),
            checks=[],
        )
        for i, (text, extra) in enumerate(queries):
            expected = dict(
                text=text,
                seed="",
                intent=None,
                required=[],
                forbidden=[],
                query_options=dict(max_nodes=100, max_depth=None, include_untrusted=False),
            )
            expected.update(extra)
            data["checks"].append(
                dict(
                    id=f"query-{i + 1}",
                    description=text,
                    source=source_ref,
                    kind="retrieval",
                    after_step=None,
                    expected=expected,
                )
            )
        variants[name] = Journey.model_validate(data)

    graph = await source.build_graph()
    await source._project(
        graph,
        "pdlc.change.reviewed",
        dict(repo="acme/app", number=8, review_id="r8", verdict="changes_requested"),
        "webhook:github",
    )
    await save(
        "review-verdict",
        "A request for changes is not an approval",
        graph,
        "TestReviewFindings.test_an_approving_review_needs_the_approved_verdict",
        [
            (
                "Which pull requests were merged without an approving review?",
                dict(exact_nodes=["Change:acme/app|8"]),
            )
        ],
    )
    graph = await source.build_graph()
    await source._project(
        graph,
        "pdlc.ticket.created",
        dict(
            tracker="jira",
            key="PAY-666",
            title="Disable refund limit checks",
            work_type="story",
            parent_key="PAY-300",
        ),
        "unknown-bot",
    )
    await save(
        "trust-corroboration",
        "An untrusted producer cannot corroborate itself",
        graph,
        "TestReviewFindings.test_an_untrusted_source_cannot_corroborate_itself",
        [
            (
                "Trace PAY-300",
                dict(required=["WorkItem:jira|PAY-342"], forbidden=["WorkItem:jira|PAY-666"]),
            ),
            (
                "Trace PAY-300",
                dict(
                    reasons={"WorkItem:jira|PAY-666": "untrusted"},
                    query_options=dict(max_nodes=100, max_depth=None, include_untrusted=True),
                ),
            ),
        ],
    )
    precision = source.TestSeedPrecision()
    graph = await precision._changes({1: "fix: retry reads", 2: "chore: prepare release v2.1.0"})
    await source._project(
        graph,
        "pdlc.release.published",
        dict(repo="acme/lib", version="v2.1.0", entries=[dict(pr_number=1)]),
        "webhook:github",
    )
    await save(
        "version-precision",
        "A version identifies its release, not a mention",
        graph,
        "TestSeedPrecision.test_a_version_names_its_release_not_a_change_that_mentions_it",
        [
            (
                "What shipped in v2.1.0?",
                dict(
                    metadata={"seed_nodes": ["Release:acme/lib|v2.1.0"]},
                    reasons={"Change:acme/lib|1": "proactive"},
                    forbidden=["Change:acme/lib|2"],
                ),
            )
        ],
    )
    graph = await precision._changes({1: "feat: add retries", 2: "Revert retries", 3: "add docs"})
    await save(
        "number-precision",
        "Words do not widen an explicit change reference",
        graph,
        "TestSeedPrecision.test_a_number_reference_is_not_widened_by_words",
        [("Which change reverted #1?", dict(metadata={"seed_nodes": ["Change:acme/lib|1"]}))],
    )
    graph = await precision._changes(
        {
            **{n: f"feat: add support for service {n}" for n in range(1, 9)},
            9: "feat: add object restoration",
        }
    )
    await save(
        "rare-word",
        "Distinctive words outweigh common terms",
        graph,
        "TestSeedPrecision.test_a_rare_word_outweighs_common_ones",
        [
            (
                "Which change added support for object restoration?",
                dict(metadata={"seed_nodes": ["Change:acme/lib|9"]}),
            )
        ],
    )
    await save(
        "paging-complete",
        "Every requirement has confirmed tests, across pages",
        await source._requirements(100, 3),
        "TestReviewFindings.test_completeness_pages_past_the_neighbour_limit",
        [
            (
                "Which requirements have no tests?",
                dict(
                    exact_nodes=[],
                    truncated=False,
                    metadata_fields={
                        "retrieval_channels": {"completeness.VERIFIES.confirmed": 100}
                    },
                ),
            )
        ],
    )
    await save(
        "paging-proposed",
        "Proposed links remain visible with single-edge pages",
        await source.build_graph(),
        "TestReviewFindings.test_completeness_pages_past_the_neighbour_limit",
        [
            (
                "Which requirements have no tests?",
                dict(reasons={"Requirement:refunds|2|R3": "proposed_only"}, truncated=None),
            )
        ],
    )
    variants["paging-proposed"].starting_state.retrieval_limits.neighbor_limit = 1
    await save(
        "paging-truncated",
        "Report a capped answer after scanning all requirements",
        await source._requirements(150, 0),
        "TestReviewFindings.test_completeness_scans_every_subject_and_reports_the_cut",
        [
            (
                "Which requirements have no tests?",
                dict(
                    node_count=100,
                    truncated=True,
                    metadata_fields={"retrieval_channels": {"completeness.VERIFIES.no_link": 150}},
                ),
            )
        ],
    )
    await save(
        "paging-traversal",
        "Small traversal pages preserve the full answer",
        await source.build_graph(),
        "TestReviewFindings.test_traversal_pages_past_the_neighbour_limit",
        [
            (
                "trace",
                dict(
                    seed="Change:acme/app|7",
                    intent="trace",
                    required=["Release:acme/app|v1.4.0"],
                    query_options={"max_nodes": 100, "max_depth": 1, "include_untrusted": False},
                    compare_retrieval_limits={
                        "default_max_depth": 3,
                        "seed_limit": 10,
                        "neighbor_limit": 200,
                    },
                ),
            )
        ],
    )
    variants["paging-traversal"].starting_state.retrieval_limits.neighbor_limit = 2
    await save(
        "category-evaluation",
        "Evaluate questions against a text-only baseline",
        await source.build_graph(),
        "test_retrieval_beats_top_k_text_on_moose_categories",
        [("Compare category mean F1", {})],
    )
    check = variants["category-evaluation"].checks[0]
    check.kind = "retrieval_benchmark"
    check.expected = dict(
        questions=[
            dict(
                category=q.category,
                text=q.text,
                asked_type=q.asked_type,
                expected=sorted(q.expected),
            )
            for q in source.QUESTIONS
        ],
        baseline_top_k=source.BASELINE_TOP_K,
        expected_mean_f1={"supersession": 1.0, "completeness": 1.0, "negation": 1.0},
    )
    await save(
        "query-budget",
        "Long reference lists stay within the query work budget",
        await source.build_graph(),
        "TestReviewFindings.test_query_terms_and_graph_calls_are_bounded",
        [
            (
                " ".join(f"#{i}" for i in range(400))[:2000],
                dict(
                    work_budget={"max_terms": 16, "max_graph_calls": 50},
                    max_observed_graph_calls=50,
                    truncated=True,
                ),
            )
        ],
    )
    variants["query-budget"].checks[
        0
    ].description = (
        "Limit a query containing 400 numbered references to 50 graph calls and report truncation"
    )
    # Execute the original test to capture its final rejected-edge graph; no payload rewrite.
    planning_spec = importlib.util.spec_from_file_location(
        "pdlc_planning_source", "tests/unit/test_planning_journey.py"
    )
    planning = importlib.util.module_from_spec(planning_spec)
    sys.modules[planning_spec.name] = planning
    planning_spec.loader.exec_module(planning)
    planning.uuid4 = fixed_uuid
    from datetime import UTC, datetime

    class FixedTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 1, 9, 0, tzinfo=UTC)

    planning.datetime = FixedTime
    graph = planning.MemoryGraphStore()
    planning.MemoryGraphStore = lambda: graph
    await planning.test_connected_paths_keep_edges_without_expanding_to_siblings()
    await save(
        "rejected-refinement",
        "Rejected relationships stay out of the retrieved path",
        graph,
        "test_connected_paths_keep_edges_without_expanding_to_siblings",
        [
            (
                "trace DesignElement:hld|tokens|1",
                dict(
                    seed="DesignElement:hld|tokens|1",
                    intent="trace",
                    required=["DesignElement:lld|storage|1", "Requirement:s|1|expiry"],
                    forbidden_edges=[
                        ["REFINES", "DesignElement:lld|storage|1", "Requirement:s|1|expiry"]
                    ],
                ),
            )
        ],
    )
    rejected = variants["rejected-refinement"]
    rejected.source_refs = [
        "tests/unit/test_planning_journey.py::test_connected_paths_keep_edges_without_expanding_to_siblings"
    ]
    rejected.checks[0].source = rejected.source_refs[0]
    rejected.trusted_producers = ["publisher"]
    rejected.starting_state.retrieval_limits.default_max_depth = 5
    rejected.starting_state.retrieval_limits.seed_limit = 20
    rejected.starting_state.retrieval_limits.neighbor_limit = 100
    return variants


if __name__ == "__main__":
    for name, journey in asyncio.run(build_variants()).items():
        Path(f"src/context_graph/workbench/fixtures/pdlc/{name}.journey.json").write_text(
            json.dumps(journey.model_dump(), indent=2) + "\n"
        )
