"""Isolated sandbox using engine admission, ledger, worker and retrieval.

Uses memory or an explicitly allocated Spanner slot, never a customer live store.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.source_trust import SourceTrustPolicy
from context_graph.ontology.evaluation import EvalSet, run_eval_set
from context_graph.retrieval.artifacts import ArtifactRetriever
from context_graph.workbench.authoring import samples
from context_graph.workbench.engine import composed, event_from_sample
from context_graph.workbench.execution import open_environment
from context_graph.workbench.storage_views import observed_dead_letters, observed_graph
from context_graph.worker.projection import ProjectionConsumer

if TYPE_CHECKING:
    from collections.abc import Callable

    from context_graph.domain.ontology import Pack
    from context_graph.domain.pack_bundle import ActiveBundle
    from context_graph.workbench.execution import RunEnvironment, SpannerExecution
    from context_graph.workbench.models import Content


def evaluation_artifact(content: Content, pack_name: str) -> dict[str, Any]:
    return {
        "pack": pack_name,
        "min_f1": content.min_f1,
        "questions": [
            {
                "id": q.id,
                "query": q.query,
                "expected": q.expected,
                "intent": q.intent,
                "seed_node_ids": q.seed_node_ids,
                "seed_mode": q.seed_mode,
                "answer": {"node_type": q.node_type},
            }
            for q in content.questions
        ],
    }


async def run_sandbox(
    content: Content,
    raw_pack: dict[str, Any],
    *,
    execution: SpannerExecution | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    with composed(content, raw_pack) as (pack, bundle, _path):
        async with open_environment(bundle, content.trusted_ids, execution, progress) as runtime:
            result = await _execute(content, pack, bundle, runtime)
        result["storage"] = dict(runtime.evidence)
        return result


async def _execute(
    content: Content, pack: Pack, bundle: ActiveBundle, runtime: RunEnvironment
) -> dict[str, Any]:
    stores, settings = runtime.stores, runtime.settings
    task = None
    consumer = None
    try:
        await stores.graph.ensure_pack_schema(bundle.registry, settings.embedding.dimensions)
        policy = compile_admission_policy(bundle)
        projector = PackProjector(
            bundle.registry,
            frozenset(content.trusted_ids),
            source_policy=SourceTrustPolicy.from_binding(runtime.binding)
            if runtime.binding
            else None,
        )
        subscription = stores.subscription("workbench", "scenario")
        await subscription.ensure_group()
        consumer = ProjectionConsumer(
            subscription, stores.event_log, stores.graph, settings, projector
        )
        task = asyncio.create_task(consumer.run())
        steps = []
        async with asyncio.timeout(180 if runtime.binding else 20):
            for index, sample in enumerate(samples(content)):
                decision = policy.decide(sample["event_type"], sample["payload"])
                event = event_from_sample(sample, index)
                if decision.allowed:
                    await runtime.writer(event).append(event, sample["payload"])
                    while await subscription.lag() or await subscription.delivery_counts(100):
                        if task.done():
                            await task
                            raise RuntimeError(
                                "Projection worker stopped before finishing examples"
                            )
                        await asyncio.sleep(0.01)
                snapshot = await observed_graph(stores.graph)
                steps.append(
                    {
                        "index": index,
                        "event_type": sample["event_type"],
                        "admitted": decision.allowed,
                        "reason": decision.reason,
                        "nodes": snapshot["nodes"],
                        "edges": snapshot["edges"],
                    }
                )
            retriever = ArtifactRetriever(
                stores.graph,
                bundle.registry,
                default_max_depth=3,
                seed_limit=20,
                neighbor_limit=100,
                provenance_source=runtime.provenance_source,
            )
            report = await run_eval_set(
                EvalSet.model_validate(evaluation_artifact(content, pack.name)),
                retriever,
                max_nodes=200,
            )
        dead_letters = await observed_dead_letters(subscription)
        observed = {row["id"] for row in steps[-1]["nodes"]} if steps else set()
        missing = sorted(set(content.expected_nodes) - observed)
        forbidden = sorted(set(content.forbidden_nodes) & observed)
        return {
            "passed": report.passed and not dead_letters and not missing and not forbidden,
            "backend": runtime.backend,
            "steps": steps,
            "evaluation": report.as_dict(),
            "dead_letters": dead_letters,
            "missing_nodes": missing,
            "forbidden_nodes": forbidden,
            "limits": [
                (
                    "Dedicated Spanner sandbox database; not a live customer deployment."
                    if runtime.binding
                    else "Fresh in-process reference backend, not Spanner or a live deployment."
                ),
                "Producer trust is a sandbox policy simulation, not producer authentication.",
                (
                    "Only deterministic projection is run; "
                    "extraction and other workers are not exercised."
                ),
                "This result does not clear any deployment's evaluation gate.",
            ],
        }
    finally:
        if consumer:
            consumer.stop()
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
