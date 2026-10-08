"""Actual retriever regressions for G01 cloud-discovered seed pollution (#45).

Memory graph is only a local regression aid; real Spanner acceptance is separate.
"""

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.ontology.loader import load_registry
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever


async def retriever():
    graph = MemoryGraphStore()
    changes = ["Change:acme/payments|7", "Change:acme/payments|8", "Change:acme/payments|70"]
    ticket = "WorkItem:jira|APP-42"
    await graph.upsert_nodes(
        [
            *[
                NodeWrite(
                    NodeRef("Change", cid),
                    {
                        "node_id": cid,
                        "repo": "acme/payments",
                        "number": number,
                        "title": "Payment fix",
                        "status": "open",
                        "source_trust": "trusted",
                    },
                )
                for cid, number in zip(changes, [7, 8, 70], strict=True)
            ],
            NodeWrite(
                NodeRef("WorkItem", ticket),
                {
                    "node_id": ticket,
                    "tracker": "jira",
                    "external_key": "APP-42",
                    "title": "Payment ticket",
                    "status": "todo",
                    "source_trust": "trusted",
                },
            ),
        ]
    )
    await graph.upsert_edges(
        [
            EdgeWrite(
                "IMPLEMENTS",
                NodeRef("Change", changes[0]),
                NodeRef("WorkItem", ticket),
                {"method": "declared", "confidence": 1.0, "link_status": "confirmed"},
            )
        ]
    )
    return ArtifactRetriever(
        graph,
        load_registry(["pdlc"], builtin_packs=[]),
        default_max_depth=5,
        seed_limit=20,
        neighbor_limit=100,
        provenance_source="memory",
    )


@pytest.mark.parametrize("punctuation", ["", ".", "?"])
async def test_exact_resolved_id_does_not_seed_its_repository_siblings(punctuation):
    engine = await retriever()
    response = await engine.retrieve(
        ArtifactQuery(
            query="trace Change:acme/payments|7" + punctuation,
            seed_node_ids=("Change:acme/payments|7",),
            intent="trace",
        )
    )
    assert {nid for nid, node in response.nodes.items() if node.node_type == "Change"} == {
        "Change:acme/payments|7"
    }
    assert "WorkItem:jira|APP-42" in response.nodes  # legitimate traversal preserved


async def test_independent_ticket_reference_is_still_discovered():
    engine = await retriever()
    response = await engine.retrieve(
        ArtifactQuery(
            query="trace Change:acme/payments|8 and APP-42",
            seed_node_ids=("Change:acme/payments|8",),
            intent="trace",
        )
    )
    assert "WorkItem:jira|APP-42" in response.nodes
    assert "WorkItem:jira|APP-42" in response.meta.seed_nodes


@pytest.mark.parametrize(
    "seed,literal",
    [
        ("Change:acme/payments|7", "Change:acme/payments|70"),
        ("Change:acme/payments|999", "Change:acme/payments|999"),
    ],
)
async def test_prefix_and_unresolved_ids_keep_independent_discovery(seed, literal):
    engine = await retriever()
    response = await engine.retrieve(
        ArtifactQuery(query="trace " + literal, seed_node_ids=(seed,), intent="trace")
    )
    assert "Change:acme/payments|70" in response.nodes
