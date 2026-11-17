"""Execute saved journeys using the allocated ledger and projection worker.

Recorded backend identifies memory or dedicated Spanner; this is not deployed HTTP evidence.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from context_graph.domain.models import Event
from context_graph.domain.ontology import OntologyRegistry
from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.source_trust import SourceTrustPolicy
from context_graph.ontology.evaluation import EvalSet, run_eval_set
from context_graph.ontology.loader import load_pack_file
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever, UnresolvedSeedsError
from context_graph.workbench.draft_stories import snapshot_registry
from context_graph.workbench.engine import digest, engine_revision
from context_graph.workbench.execution import open_environment
from context_graph.workbench.journey_benchmark import retrieve_with_work_budget, run_benchmark
from context_graph.workbench.journeys import (
    CheckResult,
    GraphFixture,
    Journey,
    QueryOptions,
    RetrievalLimits,
)
from context_graph.workbench.storage_views import (
    memory_snapshot,
    observed_dead_letters,
    observed_graph,
)
from context_graph.worker.projection import ProjectionConsumer

if TYPE_CHECKING:
    from collections.abc import Callable

    from context_graph.domain.pack_bundle import ActiveBundle
    from context_graph.workbench.execution import RunEnvironment, SpannerExecution


def frozen_registry(pack_digest: str | None = None) -> OntologyRegistry:
    """Resolve only the two frozen source bundles; a digest cannot select live files."""
    import hashlib

    root = Path(__file__).parent / "fixtures" / "pdlc"
    for names in (("core", "pdlc"), ("core", "memory", "user", "pdlc")):
        expected = hashlib.sha256(
            b"".join((root / f"{n}.pack.yaml").read_bytes() for n in names)
        ).hexdigest()
        if pack_digest is None or pack_digest == expected:
            return OntologyRegistry([load_pack_file(root / f"{n}.pack.yaml") for n in names])
    raise ValueError("Journey pack digest differs from the frozen bundles")


# Kept for existing fixture comparisons; runtime reads use observed_graph.
graph_snapshot = memory_snapshot


DOMAIN_TYPES = {
    "Spec",
    "Requirement",
    "DesignElement",
    "DesignApproval",
    "WorkItem",
    "Change",
    "Review",
    "TestCase",
    "TestRun",
}
DOMAIN_EDGES = {
    "REFINES",
    "APPROVES",
    "SUPERSEDES",
    "IMPLEMENTS",
    "REVIEWS",
    "VERIFIES",
    "EXECUTES",
    "RAN_AGAINST",
}


def graph_differences(
    expected: dict[str, Any],
    snapshot: dict[str, Any],
    domain_types: set[str] | None = None,
    domain_edges: set[str] | None = None,
) -> dict[str, Any]:
    nodes = {n["id"]: n["properties"] for n in snapshot["nodes"]}
    domain = {
        n["id"]
        for n in snapshot["nodes"]
        if n["type"] in (DOMAIN_TYPES if domain_types is None else domain_types)
    }
    edges = {(e["type"], e["source"], e["target"]) for e in snapshot["edges"]}
    wanted_edges = {tuple(e) for e in expected["edges"]}
    actual_edges = {
        e for e in edges if e[0] in (DOMAIN_EDGES if domain_edges is None else domain_edges)
    }
    return {
        "missing_nodes": sorted(set(expected["nodes"]) - domain),
        "unexpected_nodes": sorted(domain - set(expected["nodes"])),
        "wrong_properties": [
            {"node": n, "property": k, "expected": v, "actual": nodes.get(n, {}).get(k)}
            for n, props in expected["nodes"].items()
            for k, v in props.items()
            if nodes.get(n, {}).get(k) != v
        ],
        "missing_edges": sorted(wanted_edges - actual_edges),
        "unexpected_edges": sorted(actual_edges - wanted_edges),
        "missing_evidence": [
            (n, eid)
            for n, ids in expected["evidence"].items()
            for eid in ids
            if ("DERIVED_FROM", n, eid) not in edges
        ],
        "wrong_commit_links": [
            e
            for e in snapshot["edges"]
            if domain_types is None
            and e["type"] == "RAN_AGAINST"
            and e.get("properties", {}).get("commit_sha")
            != nodes.get(e["source"], {}).get("commit_sha")
        ],
        "unexpected_user_nodes": [
            n["id"]
            for n in snapshot["nodes"]
            if domain_types is None
            and n["type"] in {"UserProfile", "Preference", "Skill", "Belief", "Goal", "Episode"}
        ],
    }


def evaluate_check(
    check: Any,
    snapshot: dict[str, Any],
    previous: dict[str, Any],
    outcome: str,
    *,
    domain_types: set[str] | None = None,
    domain_edges: set[str] | None = None,
) -> CheckResult:
    expected = check.expected
    nodes = {n["id"]: n["properties"] for n in snapshot["nodes"]}
    actual: dict[str, Any] = {}
    explanation = ""
    if check.kind == "disposition":
        # Keep original fixture status visible, but compare semantic outcomes only.
        wanted = {201: {"created", "duplicate"}, 409: {"conflict"}, 422: {"rejected"}}.get(
            expected["http_status"], set()
        )
        passed = outcome in wanted
        actual = {"semantic_outcome": outcome, "http_exercised": False}
        explanation = (
            "Compared ledger/admission outcome; original HTTP status requires API acceptance."
        )
    elif check.kind == "evidence_absent":
        actual = {
            "evidence": [
                e
                for e in snapshot["edges"]
                if e["type"] == "DERIVED_FROM" and e["source"] == expected["node"]
            ]
        }
        passed = not actual["evidence"]
    elif check.kind == "graph_exact":
        actual = graph_differences(expected, snapshot, domain_types, domain_edges)
        passed = not any(actual.values())
    elif check.kind == "unchanged":
        passed = snapshot == previous
        actual = {"graph_unchanged": passed}
    elif check.kind in {"node_present", "node_absent", "properties", "property_absent"}:
        node = expected["node"]
        props = nodes.get(node)
        actual = {"node": node, "properties": props}
        if check.kind == "node_present":
            passed = props is not None
        elif check.kind == "node_absent":
            passed = props is None
        elif check.kind == "property_absent":
            passed = props is not None and expected["property"] not in props
        else:
            passed = props is not None and all(
                props.get(k) == v for k, v in expected["properties"].items()
            )
    elif check.kind == "edge_targets":
        anchor, target = (
            ("target", "source") if expected["direction"] == "in" else ("source", "target")
        )
        found = {
            e[target]
            for e in snapshot["edges"]
            if e["type"] == expected["type"] and e[anchor] == expected["node"]
        }
        actual = {"targets": sorted(found)}
        passed = found == set(expected["targets"])
    elif check.kind == "nodes_matching":
        found = {
            n["id"]
            for n in snapshot["nodes"]
            if n["type"] == expected["type"]
            and all(n["properties"].get(k) == v for k, v in expected["properties"].items())
        }
        actual = {"ids": sorted(found)}
        passed = found == set(expected["ids"])
    elif check.kind in {"edge_present", "edge_absent"}:
        present = any(
            all(e.get(k) == v for k, v in expected.items() if k != "properties")
            and all(
                e.get("properties", {}).get(k) == v
                for k, v in expected.get("properties", {}).items()
            )
            for e in snapshot["edges"]
        )
        actual = {"present": present}
        passed = present if check.kind == "edge_present" else not present
    else:
        return CheckResult(
            check_id=check.id,
            status="unsupported",
            expected=expected,
            explanation=expected.get("reason", "No executor for this assertion"),
        )
    return CheckResult(
        check_id=check.id,
        status="passed" if passed else "failed",
        expected=expected,
        actual=actual,
        explanation=explanation,
    )


async def run_journey(
    journey: Journey,
    *,
    execution: SpannerExecution | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
    pack_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = (
        snapshot_registry(pack_snapshot, journey.pack_digest)
        if pack_snapshot is not None
        else frozen_registry(journey.pack_digest)
    )
    if not journey.expectations_reviewed:
        raise ValueError("Review expected outcomes before execution")
    bundle = resolve_bundle(registry)
    async with open_environment(bundle, journey.trusted_producers, execution, progress) as runtime:
        result = await _execute(journey, bundle, runtime, pack_snapshot=pack_snapshot)
    result["storage"] = dict(runtime.evidence)
    return result


async def _execute(
    journey: Journey,
    bundle: ActiveBundle,
    runtime: RunEnvironment,
    *,
    pack_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry, pack_hash = bundle.registry, journey.pack_digest
    domains = {}
    if pack_snapshot is not None:
        domains = {
            "domain_types": {
                name
                for name, node in registry.node_types.items()
                if node.pack not in {"core", "memory", "user"}
            },
            "domain_edges": {
                name
                for name, edge in registry.edge_types.items()
                if edge.pack not in {"core", "memory", "user"}
            },
        }
    stores, settings = runtime.stores, runtime.settings
    task = None
    consumer = None
    results = []
    steps = []
    try:
        await stores.graph.ensure_pack_schema(registry, settings.embedding.dimensions)
        initial_graph = None
        if isinstance(journey.starting_state, GraphFixture):
            setup = journey.starting_state
            if any(n.type not in registry.node_types for n in setup.nodes) or any(
                e.type not in registry.edge_types for e in setup.edges
            ):
                raise ValueError("Graph fixture types must exist in the frozen ontology")
            refs = {
                n.id: NodeRef(n.type, n.id, "event_id" if n.type == "Event" else "node_id")
                for n in setup.nodes
            }
            await stores.graph.upsert_nodes(
                [NodeWrite(refs[n.id], n.properties) for n in setup.nodes]
            )
            await stores.graph.upsert_edges(
                [
                    EdgeWrite(e.type, refs[e.source], refs[e.target], e.properties)
                    for e in setup.edges
                ]
            )
            initial_graph = await observed_graph(stores.graph)
        sub = stores.subscription("workbench-journey", "scenario")
        await sub.ensure_group()
        consumer = ProjectionConsumer(
            sub,
            stores.event_log,
            stores.graph,
            settings,
            PackProjector(
                registry,
                frozenset(journey.trusted_producers),
                source_policy=SourceTrustPolicy.from_binding(runtime.binding)
                if runtime.binding
                else None,
            ),
        )
        task = asyncio.create_task(consumer.run())
        policy = compile_admission_policy(bundle)
        previous = await observed_graph(stores.graph)
        async with asyncio.timeout(180 if runtime.binding else 30):
            for index, item in enumerate(journey.events):
                raw = item.request
                decision = policy.decide(raw["event_type"], raw["payload"])
                if not decision.allowed:
                    outcome = "rejected"
                else:
                    event = Event.model_validate(raw, strict=False)
                    (receipt,) = await runtime.writer(event).append_batch_outcomes(
                        [event], [raw["payload"]]
                    )
                    outcome = receipt.status
                    while await sub.lag() or await sub.delivery_counts(100):
                        if task.done():
                            await task
                            raise RuntimeError(
                                "Projection worker stopped before completing the journey"
                            )
                        await asyncio.sleep(0.01)
                snapshot = await observed_graph(stores.graph)
                if len(snapshot["nodes"]) > 500 or len(snapshot["edges"]) > 2000:
                    raise ValueError("Journey exceeded sandbox graph limits")
                steps.append({"id": item.id, "title": item.title, "outcome": outcome, **snapshot})
                for check in journey.checks:
                    if check.after_step == index:
                        results.append(
                            evaluate_check(check, snapshot, previous, outcome, **domains)
                        )
                previous = snapshot
            retriever = ArtifactRetriever(
                stores.graph,
                registry,
                provenance_source=runtime.provenance_source,
                **(
                    journey.starting_state.retrieval_limits.model_dump()
                    if isinstance(journey.starting_state, GraphFixture)
                    else dict(default_max_depth=5, seed_limit=20, neighbor_limit=100)
                ),
            )
            for check in journey.checks:
                if check.after_step is not None:
                    continue
                if check.kind == "retrieval_benchmark":
                    benchmark = await run_benchmark(
                        stores.graph, registry, retriever, check.expected
                    )
                    results.append(
                        CheckResult(
                            check_id=check.id,
                            status="passed" if benchmark["passed"] else "failed",
                            expected=check.expected,
                            actual=benchmark,
                        )
                    )
                    continue
                if check.kind == "evaluation":
                    report = await run_eval_set(
                        EvalSet.model_validate(
                            {
                                "pack": pack_snapshot["primary_pack"] if pack_snapshot else "pdlc",
                                "min_f1": check.expected["min_f1"],
                                "questions": [check.expected["question"]],
                            }
                        ),
                        retriever,
                        max_nodes=200,
                    )
                    results.append(
                        CheckResult(
                            check_id=check.id,
                            status="passed" if report.passed else "failed",
                            expected=check.expected,
                            actual=report.as_dict(),
                        )
                    )
                    continue
                if check.kind != "retrieval":
                    results.append(evaluate_check(check, previous, previous, "not_run", **domains))
                    continue
                q = check.expected
                options = QueryOptions.model_validate(q.get("query_options", {}))
                query = ArtifactQuery(
                    query=q.get("text") or q["intent"] + " " + q["seed"],
                    seed_node_ids=tuple(q.get("seeds", [q["seed"]] if q.get("seed") else [])),
                    intent=q["intent"],
                    **options.model_dump(),
                )
                try:
                    work_calls = None
                    if "work_budget" in q:
                        answer, work_calls = await retrieve_with_work_budget(
                            stores.graph,
                            registry,
                            query,
                            journey.starting_state.retrieval_limits.model_dump()
                            if isinstance(journey.starting_state, GraphFixture)
                            else dict(default_max_depth=5, seed_limit=20, neighbor_limit=100),
                            q["work_budget"],
                            provenance_source=runtime.provenance_source,
                        )
                    else:
                        answer = await retriever.retrieve(query)
                    comparison = None
                    if "compare_retrieval_limits" in q:
                        reference = ArtifactRetriever(
                            stores.graph,
                            registry,
                            provenance_source=runtime.provenance_source,
                            **RetrievalLimits.model_validate(
                                q["compare_retrieval_limits"]
                            ).model_dump(),
                        )
                        reference_answer = await reference.retrieve(query)
                        comparison = {
                            "nodes": sorted(reference_answer.nodes),
                            "same_nodes": set(answer.nodes) == set(reference_answer.nodes),
                        }
                except UnresolvedSeedsError as exc:
                    results.append(
                        CheckResult(
                            check_id=check.id,
                            status="failed",
                            expected=check.expected,
                            actual={
                                "error": str(exc),
                                "reason": exc.reason,
                                "unresolved_seed_ids": exc.unresolved,
                            },
                        )
                    )
                    continue
                missing = sorted(set(q["required"]) - set(answer.nodes))
                forbidden = sorted(set(q["forbidden"]) & set(answer.nodes))
                returned_edges = {(e.edge_type, e.source, e.target) for e in answer.edges}
                missing_edges = sorted({tuple(e) for e in q.get("edges", [])} - returned_edges)
                forbidden_edges = sorted(
                    {tuple(e) for e in q.get("forbidden_edges", [])} & returned_edges
                )
                wrong_properties = [
                    {"node": n, "property": k, "expected": v}
                    for n, props in q.get("properties", {}).items()
                    for k, v in props.items()
                    if n not in answer.nodes or answer.nodes[n].attributes.get(k) != v
                ]
                wrong_evidence = []
                metadata = answer.meta.model_dump(mode="json")
                wrong_metadata = [
                    {"field": key, "expected": value, "actual": metadata.get(key)}
                    for key, value in q.get("metadata", {}).items()
                    if key not in metadata or metadata[key] != value
                ]
                for field, fields in q.get("metadata_fields", {}).items():
                    observed = metadata.get(field)
                    for key, value in fields.items():
                        if not isinstance(observed, dict) or observed.get(key) != value:
                            wrong_metadata.append(
                                {"field": f"{field}.{key}", "expected": value, "actual": observed}
                            )
                if "first_seed" in q and answer.meta.seed_nodes[:1] != [q["first_seed"]]:
                    wrong_metadata.append(
                        {
                            "field": "first_seed",
                            "expected": q["first_seed"],
                            "actual": answer.meta.seed_nodes[:1],
                        }
                    )
                wrong_bounds = "max_node_count" in q and len(answer.nodes) > q["max_node_count"]
                if "node_count" in q:
                    wrong_bounds = wrong_bounds or len(answer.nodes) != q["node_count"]
                expected_truncation = q.get("truncated", False)
                wrong_truncation = (
                    expected_truncation is not None and answer.meta.truncated != expected_truncation
                )
                unexpected_nodes = (
                    sorted(set(answer.nodes) - set(q["exact_nodes"])) if "exact_nodes" in q else []
                )
                if "exact_nodes" in q:
                    missing = sorted(set(missing) | (set(q["exact_nodes"]) - set(answer.nodes)))
                wrong_reasons = [
                    {"node": node_id, "expected": reason}
                    for node_id, reason in q.get("reasons", {}).items()
                    if node_id not in answer.nodes
                    or answer.nodes[node_id].retrieval_reason != reason
                ]
                wrong_shape: list[dict[str, Any]] = []
                types = {node.node_type for node in answer.nodes.values()}
                for mode, wanted in q.get("types", {}).items():
                    matches = {
                        "required": set(wanted) <= types,
                        "forbidden": not (set(wanted) & types),
                        "exact": set(wanted) == types,
                    }.get(mode, False)
                    if not matches:
                        wrong_shape.append(
                            {"types": mode, "expected": wanted, "actual": sorted(types)}
                        )
                for node_type, wanted in q.get("nodes_by_type", {}).items():
                    found = {
                        key for key, node in answer.nodes.items() if node.node_type == node_type
                    }
                    if found != set(wanted):
                        wrong_shape.append(
                            {"type": node_type, "expected": wanted, "actual": sorted(found)}
                        )
                for node_type, expected_node in q.get("first_of_type", {}).items():
                    node = next(
                        (n for n in answer.nodes.values() if n.node_type == node_type), None
                    )
                    observed = {
                        "properties": node.attributes if node else {},
                        "provenance": node.provenance.model_dump(mode="json")
                        if node and node.provenance
                        else {},
                    }
                    for section, fields in expected_node.items():
                        if node is None or any(
                            observed.get(section, {}).get(k) != v for k, v in fields.items()
                        ):
                            wrong_shape.append(
                                {
                                    "type": node_type,
                                    "section": section,
                                    "expected": fields,
                                    "actual": observed.get(section),
                                }
                            )
                for key, node in answer.nodes.items():
                    if node.retrieval_reason in q.get("forbidden_reasons", []):
                        wrong_reasons.append({"node": key, "forbidden": node.retrieval_reason})
                missing_seeds = sorted(
                    set(q.get("required_seeds", [])) - set(answer.meta.seed_nodes)
                )
                for node_id, ids in q.get("evidence", {}).items():
                    node = answer.nodes.get(node_id)
                    provenance = node.provenance if node else None
                    if (
                        provenance is None
                        or provenance.event_id not in ids
                        or provenance.source != runtime.provenance_source
                    ):
                        wrong_evidence.append(node_id)
                wrong_commits = [
                    e.model_dump()
                    for e in answer.edges
                    if e.edge_type == "RAN_AGAINST"
                    and e.source in q["required"]
                    and e.properties.get("commit_sha")
                    != answer.nodes[e.source].attributes.get("commit_sha")
                ]
                passed = not any(
                    (
                        missing,
                        forbidden,
                        missing_edges,
                        forbidden_edges,
                        wrong_properties,
                        wrong_evidence,
                        wrong_metadata,
                        unexpected_nodes,
                        wrong_reasons,
                        wrong_shape,
                        missing_seeds,
                        comparison is not None and not comparison["same_nodes"],
                        wrong_commits,
                        work_calls is not None
                        and sum(work_calls.values()) > q["max_observed_graph_calls"],
                        wrong_bounds,
                        wrong_truncation,
                    )
                )
                results.append(
                    CheckResult(
                        check_id=check.id,
                        status="passed" if passed else "failed",
                        expected=q,
                        actual={
                            "nodes": sorted(answer.nodes),
                            "node_details": {
                                k: n.model_dump(mode="json") for k, n in answer.nodes.items()
                            },
                            "query_options": options.model_dump(),
                            "missing": missing,
                            "forbidden": forbidden,
                            "truncated": answer.meta.truncated,
                            "wrong_bounds": wrong_bounds,
                            "wrong_truncation": wrong_truncation,
                            "missing_edges": missing_edges,
                            "forbidden_edges": forbidden_edges,
                            "wrong_properties": wrong_properties,
                            "wrong_evidence": wrong_evidence,
                            "metadata": metadata,
                            "wrong_metadata": wrong_metadata,
                            "unexpected_nodes": unexpected_nodes,
                            "wrong_reasons": wrong_reasons,
                            "wrong_shape": wrong_shape,
                            "missing_seeds": missing_seeds,
                            "comparison": comparison,
                            "graph_calls": work_calls,
                            "wrong_commit_links": wrong_commits,
                        },
                    )
                )
        dead_letters = await observed_dead_letters(sub)
        return {
            "journey_digest": digest(journey.model_dump()),
            "pack_digest": pack_hash,
            "pack_names": [p.name for p in registry.packs],
            "packs": [{"name": p.name, "version": p.version} for p in registry.packs],
            "engine_revision": engine_revision(),
            "backend": runtime.backend,
            "passed": all(r.status == "passed" for r in results) and not dead_letters,
            "checks": [r.model_dump() for r in results],
            "steps": steps,
            "initial_graph": initial_graph,
            "dead_letters": dead_letters,
            "limits": [
                (
                    "Saved graph fixture; records were not ingested or extracted."
                    if initial_graph is not None
                    else "Starting graph is empty."
                ),
                "Semantic outcomes only; HTTP routing and authentication are not exercised.",
                (
                    "Graph retrieval only; no ingestion, projection or model calls."
                    if initial_graph is not None and not journey.events
                    else "Projection and graph retrieval; no extraction or model calls."
                ),
                (
                    "Dedicated Spanner sandbox; "
                    "HTTP and deployed worker scheduling are not exercised."
                    if runtime.binding
                    else "Memory acceptance can differ from Spanner; failures are retained."
                ),
            ],
        }
    finally:
        if consumer:
            consumer.stop()
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
