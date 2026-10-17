"""Reproduce: does a `trace` artifact read seeded on a superseded design drop it?

Builds a small PDLC graph in the in-memory backend by projecting real pdlc.*
events through the pack rules (same path as tests/unit/test_pdlc_retrieval_eval.py),
then asks ArtifactRetriever several questions and prints what came back.

Run from the repo root:
  uv run python <this file>
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import orjson

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.projection import event_to_node
from context_graph.ontology import load_registry
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.worker.pack_projection import apply_plan

REGISTRY = load_registry(["pdlc"])
START = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
TRUSTED_SOURCE = "webhook:github"

DESIGN_V1 = "DesignElement:export-hld|overview|1"
DESIGN_V2 = "DesignElement:export-hld|overview|2"
REQUIREMENT = "Requirement:export-spec|1|REQ-1"


async def build_graph() -> MemoryGraphStore:
    graph = MemoryGraphStore()
    projector = PackProjector(REGISTRY, frozenset({TRUSTED_SOURCE}))
    minute_counter = 0

    async def project(event_type: str, payload: dict[str, Any]) -> None:
        nonlocal minute_counter
        minute_counter += 1
        record = Event(
            event_id=uuid4(),
            event_type=event_type,
            occurred_at=START + timedelta(minutes=minute_counter),
            session_id="pdlc:acme/export",
            agent_id=TRUSTED_SOURCE,
            trace_id="trace-repro",
            payload_ref="payload-repro",
            global_position=f"{minute_counter}-0",
        )
        await graph.merge_event_node(event_to_node(record))
        document = orjson.loads(record.model_dump_json()) | {"payload": payload}
        plan = projector.plan(record, document)
        await apply_plan(graph, plan, 1000)

    await project(
        "pdlc.requirement.changed",
        {
            "spec_id": "export-spec",
            "spec_version": "1",
            "local_id": "REQ-1",
            "statement": "Users can export reports as CSV",
        },
    )
    requirement_link = [{"spec_id": "export-spec", "spec_version": "1", "local_id": "REQ-1"}]
    await project(
        "pdlc.design.section_changed",
        {
            "doc_id": "export-hld",
            "section_path": "overview",
            "version": "1",
            "kind": "hld",
            "title": "Export HLD overview",
            "body": "Synchronous CSV export from the API node",
            "requirements": requirement_link,
        },
    )
    await project(
        "pdlc.design.approval_recorded",
        {
            "approval_id": "approval-v1",
            "reviewer": "alex",
            "verdict": "approved",
            "doc_id": "export-hld",
            "section_path": "overview",
            "version": "1",
        },
    )
    await project(
        "pdlc.design.section_changed",
        {
            "doc_id": "export-hld",
            "section_path": "overview",
            "version": "2",
            "kind": "hld",
            "title": "Export HLD overview",
            "body": "Asynchronous CSV export through a job queue",
            "requirements": requirement_link,
            "supersedes_version": "1",
        },
    )
    return graph


def summarize(label: str, response: Any) -> None:
    print(f"--- {label}")
    print("  inferred_intents:", response.meta.inferred_intents)
    print("  seed_nodes      :", response.meta.seed_nodes)
    print("  truncated       :", response.meta.truncated)
    print("  retrieval_channels (completeness block):", response.meta.retrieval_channels)
    print("  nodes:")
    for node_id, node in response.nodes.items():
        print(
            f"    {node_id:42s} reason={node.retrieval_reason:11s} "
            f"status={node.attributes.get('status')}"
        )
    if not response.nodes:
        print("    (none)")
    print("  edges:")
    for edge in response.edges:
        print(f"    {edge.source} -[{edge.edge_type}]-> {edge.target}")
    if not response.edges:
        print("    (none)")
    print(f"  v1 present: {DESIGN_V1 in response.nodes}")


async def main() -> None:
    graph = await build_graph()
    retriever = ArtifactRetriever(
        graph,
        REGISTRY,
        default_max_depth=3,
        seed_limit=10,
        neighbor_limit=200,
        provenance_source="memory",
    )
    from context_graph.ports.pack_graph import NodeRef

    print("Graph state before any read:")
    refs = [
        NodeRef("DesignElement", DESIGN_V1),
        NodeRef("DesignElement", DESIGN_V2),
        NodeRef("Requirement", REQUIREMENT),
    ]
    stored = await graph.get_nodes(refs)
    for ref in refs:
        props = stored.get(ref, {})
        print(f"  {ref.key:42s} stored={ref in stored} status={props.get('status')}")
    supersedes_rows = await graph.neighbors([refs[0]], ["SUPERSEDES"], "in", 10)
    for row in supersedes_rows:
        print(f"  SUPERSEDES edge: {row['source_key']} -> {row['target_key']}")
    print()

    cases = [
        (
            "A. trace, given seed = v1, explicit intent",
            ArtifactQuery("trace this design", seed_node_ids=(DESIGN_V1,), intent="trace"),
        ),
        (
            "B. trace, given seed = v1, intent classified from text",
            ArtifactQuery("Trace where this design was implemented", seed_node_ids=(DESIGN_V1,)),
        ),
        (
            "C. trace, word-seeded ('Trace the export HLD overview')",
            ArtifactQuery("Trace the export HLD overview", intent="trace"),
        ),
        (
            "D. trace, given seed = v2 (SUPERSEDES edge reaches v1)",
            ArtifactQuery("trace this design", seed_node_ids=(DESIGN_V2,), intent="trace"),
        ),
        (
            "E. trace, given seed = requirement (REFINES reaches v1 and v2)",
            ArtifactQuery("trace this requirement", seed_node_ids=(REQUIREMENT,), intent="trace"),
        ),
        (
            "F. status, given seed = v1 (control: kept and labelled)",
            ArtifactQuery("is this design current", seed_node_ids=(DESIGN_V1,), intent="status"),
        ),
        (
            "G. why, given seed = v1 (control: kept and labelled)",
            ArtifactQuery("why this design", seed_node_ids=(DESIGN_V1,), intent="why"),
        ),
        (
            "H. no intent keyword, given seed = v1",
            ArtifactQuery("export overview", seed_node_ids=(DESIGN_V1,)),
        ),
    ]
    for label, query in cases:
        summarize(label, await retriever.retrieve(query))
        print()


if __name__ == "__main__":
    asyncio.run(main())
