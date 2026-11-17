"""Bounded replay of the source PDLC category evaluation and text baseline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field

from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.workbench.models import Strict

if TYPE_CHECKING:
    from context_graph.domain.models import AtlasResponse
    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.ports.graph_backend import GraphBackend


class BenchmarkQuestion(Strict):
    category: Literal["supersession", "completeness", "negation"]
    text: str = Field(min_length=1, max_length=2000)
    asked_type: str
    expected: list[str] = Field(max_length=500)


class Benchmark(Strict):
    questions: list[BenchmarkQuestion] = Field(min_length=1, max_length=50)
    expected_mean_f1: dict[str, float]
    baseline_top_k: int = Field(default=5, ge=1, le=100)


def selected_answer(category: str, asked_type: str, response: AtlasResponse) -> set[str]:
    if category == "supersession":
        asked = {k for k in response.meta.seed_nodes if k in response.nodes}
        asked |= {
            e.source for e in response.edges if e.edge_type == "SUPERSEDES" and e.target in asked
        }
        return {
            k
            for k in asked
            if response.nodes[k].node_type == asked_type
            and response.nodes[k].retrieval_reason != "superseded"
        }
    if category == "completeness":
        return {k for k, n in response.nodes.items() if n.retrieval_reason == "no_link"}
    return {
        end for e in response.edges if e.edge_type == "CONTRADICTS" for end in (e.source, e.target)
    }


def score(found: set[str], expected: set[str]) -> float:
    # Preserve source behavior, including zero for empty sets.
    if not found or not expected:
        return 0.0
    hits = len(found & expected)
    if not hits:
        return 0.0
    precision, recall = hits / len(found), hits / len(expected)
    return 2 * precision * recall / (precision + recall)


async def run_benchmark(
    graph: GraphBackend,
    registry: OntologyRegistry,
    retriever: ArtifactRetriever,
    expected: dict[str, Any],
) -> dict[str, Any]:
    spec = Benchmark.model_validate(expected)
    rows = []
    categories: dict[str, dict[str, list[float]]] = {}
    for q in spec.questions:
        response = await retriever.retrieve(ArtifactQuery(q.text))
        found = selected_answer(q.category, q.asked_type, response)
        words = [w for w in q.text.lower().replace("?", " ").split() if len(w) > 3]
        baseline: dict[str, str] = {}
        # Deliberately reproduce the source's text-only baseline, without graph expansion.
        for label in retriever._seed_types:
            node_type = registry.node_type(label)
            matches = await graph.search_nodes(
                label, retriever._search_fields(node_type), words, spec.baseline_top_k
            )
            for props, _hits in matches:
                baseline.setdefault(str(props.get(node_type.key_property)), label)
        baseline_found = {k for k, label in baseline.items() if label == q.asked_type}
        ours, theirs = score(found, set(q.expected)), score(baseline_found, set(q.expected))
        group = categories.setdefault(q.category, {"retrieval": [], "baseline": []})
        group["retrieval"].append(ours)
        group["baseline"].append(theirs)
        rows.append(
            dict(
                question=q.text,
                category=q.category,
                expected=q.expected,
                found=sorted(found),
                baseline_found=sorted(baseline_found),
                f1=ours,
                baseline_f1=theirs,
            )
        )
    means = {
        category: {system: sum(values) / len(values) for system, values in systems.items()}
        for category, systems in categories.items()
    }
    passed = {c: s["retrieval"] for c, s in means.items()} == spec.expected_mean_f1 and all(
        s["retrieval"] > s["baseline"] for s in means.values()
    )
    return dict(passed=passed, categories=means, questions=rows)


class WorkBudget(Strict):
    max_terms: int = Field(default=16, ge=1, le=64)
    max_graph_calls: int = Field(default=50, ge=1, le=400)


async def retrieve_with_work_budget(
    graph: GraphBackend,
    registry: OntologyRegistry,
    query: ArtifactQuery,
    limits: dict[str, Any],
    budget: dict[str, Any],
    *,
    provenance_source: str = "memory",
) -> tuple[AtlasResponse, dict[str, int]]:
    """Count exactly the three graph operations instrumented by the source regression."""
    bounds = WorkBudget.model_validate(budget)
    counts = {name: 0 for name in ("find_nodes", "search_nodes", "neighbors")}
    originals = {name: getattr(graph, name) for name in counts}
    for name, original in originals.items():

        async def counted(
            *args: Any, _name: str = name, _original: Any = original, **kwargs: Any
        ) -> Any:
            counts[_name] += 1
            return await _original(*args, **kwargs)

        setattr(graph, name, counted)
    try:
        retriever = ArtifactRetriever(
            graph, registry, provenance_source=provenance_source, **limits, **bounds.model_dump()
        )
        return await retriever.retrieve(query), counts
    finally:
        for name, original in originals.items():
            setattr(graph, name, original)
