"""Differential tests: disabled historical data cannot consume a read limit."""

from unittest.mock import AsyncMock

import pytest

from context_graph.adapters.composed_reads import ComposedGraphReads, ComposedReadView, ReadScope
from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import SubgraphQuery
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.domain.pack_intents import RegistryIntents, UnsupportedIntentError
from context_graph.ontology.loader import load_registry
from context_graph.ports.pack_graph import NodeRef, NodeWrite
from context_graph.ports.search import SearchHit
from context_graph.retrieval.artifacts import ArtifactQuery, ArtifactRetriever
from context_graph.retrieval.engine import RetrievalEngine
from context_graph.settings import DecaySettings


def view(graph, packs=()):
    bundle = resolve_bundle(load_registry(list(packs), builtin_packs=[]))
    return ComposedReadView(graph, ReadScope.from_bundle(bundle)), bundle


async def test_disabled_neighbors_and_invalid_endpoints_do_not_consume_limit():
    graph = MemoryGraphStore()
    await graph._upsert_nodes(
        [
            (("Event", "e"), {"event_id": "e"}),
            (("Entity", "good"), {"entity_id": "good"}),
            (("UserProfile", "hidden"), {"profile_id": "hidden"}),
            (("Change", "wrong-endpoint"), {"node_id": "wrong-endpoint"}),
        ]
    )
    await graph._upsert_edges(
        [
            ((("Event", "e"), "REFERENCES", ("UserProfile", "hidden")), {}),
            ((("Event", "e"), "REFERENCES", ("Change", "wrong-endpoint")), {}),
            ((("Event", "e"), "REFERENCES", ("Entity", "good")), {}),
        ]
    )
    selected, _bundle = view(graph, ["pdlc"])
    rows = await selected.reads.event_neighbors(["e"], 1)
    assert len(rows) == 1 and rows[0]["neighbor_entity_id"] == "good"
    assert await selected.find_nodes("UserProfile", {}, 1) == []
    assert await selected.get_nodes([NodeRef("UserProfile", "hidden", "profile_id")]) == {}


async def test_disabled_and_wrong_typed_edges_cannot_change_seed_ranking():
    graph = MemoryGraphStore()
    await graph._upsert_nodes(
        [
            (("Event", "a"), {"event_id": "a", "session_id": "s", "occurred_at": "2026-01-01"}),
            (("Event", "b"), {"event_id": "b", "session_id": "s", "occurred_at": "2026-01-02"}),
            (("Entity", "good"), {"entity_id": "good"}),
            (("UserProfile", "hidden"), {"profile_id": "hidden"}),
        ]
    )
    await graph._upsert_edges(
        [
            ((("Event", "a"), "REFERENCES", ("Entity", "good")), {}),
            ((("Event", "b"), "REFERENCES", ("UserProfile", "hidden")), {}),
            ((("UserProfile", "hidden"), "CAUSED_BY", ("Event", "b")), {}),
        ]
    )
    selected, _bundle = view(graph)
    seeds = await selected.reads.seed_events("entity_hubs", "s", 1)
    assert [row["event_id"] for row in seeds] == ["a"]
    assert await selected.reads.seed_events("causal_roots", "s", 1) == []


async def test_rejected_links_do_not_consume_neighbor_limit():
    graph = MemoryGraphStore()
    await graph._upsert_nodes(
        [
            (("Event", "e"), {"event_id": "e"}),
            (("Entity", "a"), {"entity_id": "a"}),
            (("Entity", "b"), {"entity_id": "b"}),
        ]
    )
    await graph._upsert_edges(
        [
            ((("Event", "e"), "REFERENCES", ("Entity", "a")), {"link_status": "rejected"}),
            ((("Event", "e"), "REFERENCES", ("Entity", "b")), {"link_status": "confirmed"}),
        ]
    )
    selected, _bundle = view(graph)
    assert (await selected.reads.event_neighbors(["e"], 1))[0]["neighbor_entity_id"] == "b"


async def test_inactive_superseding_node_cannot_hide_active_artifact():
    graph = MemoryGraphStore()
    await graph._upsert_nodes(
        [
            (("Requirement", "Requirement:r1"), {"node_id": "Requirement:r1", "status": "active"}),
            (("RetiredType", "past"), {"node_id": "past"}),
        ]
    )
    await graph._upsert_edges(
        [
            ((("RetiredType", "past"), "SUPERSEDES", ("Requirement", "Requirement:r1")), {}),
        ]
    )
    selected, bundle = view(graph, ["pdlc"])
    retriever = ArtifactRetriever(
        selected,
        bundle.registry,
        default_max_depth=2,
        seed_limit=10,
        neighbor_limit=1,
        provenance_source="memory",
    )
    response = await retriever.retrieve(
        ArtifactQuery("requirement", seed_node_ids=("Requirement:r1",))
    )
    assert "Requirement:r1" in response.nodes
    assert all(node.node_type != "RetiredType" for node in response.nodes.values())


async def test_read_view_refuses_writes_and_forwards_only_existing_event_access():
    graph = MemoryGraphStore()
    await graph._upsert_nodes([(("Event", "exists"), {"event_id": "exists"})])
    selected, _bundle = view(graph)
    with pytest.raises(PermissionError):
        await selected.upsert_nodes([NodeWrite(NodeRef("Event", "new", "event_id"))])
    await ComposedGraphReads(selected).record_access(["exists", "absent"], "2026-01-01")
    assert graph.nodes[("Event", "exists")]["access_count"] == 1
    assert ("Event", "absent") not in graph.nodes


async def test_mismatched_keys_and_dangling_edges_cannot_consume_limits():
    graph = MemoryGraphStore()
    graph.nodes[("Event", "a")] = {"event_id": "b", "session_id": "s"}
    graph.nodes[("Event", "b")] = {"event_id": "b", "session_id": "s"}
    graph.nodes[("Entity", "z-valid")] = {"entity_id": "z-valid"}
    graph.edges[(("Event", "b"), "REFERENCES", ("Entity", "a-missing"))] = {}
    graph.edges[(("Event", "b"), "REFERENCES", ("Entity", "z-valid"))] = {}
    selected, _bundle = view(graph)
    assert await selected._get_nodes([("Event", "a")]) == {}
    assert await selected.find_nodes("Event", {"session_id": "s"}, 10) == [
        graph.nodes[("Event", "b")]
    ]
    assert (await selected.reads.event_neighbors(["b"], 1))[0]["neighbor_entity_id"] == "z-valid"


def test_artifact_neighbor_rejects_wrong_near_direction_and_far_identity():
    selected, bundle = view(MemoryGraphStore(), ["pdlc"])
    retriever = ArtifactRetriever(
        selected,
        bundle.registry,
        default_max_depth=2,
        seed_limit=10,
        neighbor_limit=10,
        provenance_source="memory",
    )
    ref = NodeRef("Spec", "Spec:r1")
    row = {
        "source_label": "Spec",
        "source_key": "Spec:r2",
        "target_label": "Spec",
        "target_key": "Spec:r1",
        "edge_type": "SUPERSEDES",
        "node_label": "Spec",
        "node": {"node_id": "Spec:r2"},
        "properties": {},
    }
    assert retriever._valid_neighbor(row, [ref], ["SUPERSEDES"], "in")
    assert not retriever._valid_neighbor(row, [ref], ["SUPERSEDES"], "out")
    assert not retriever._valid_neighbor(row, [NodeRef("Spec", "absent")], ["SUPERSEDES"], "in")
    row["node"] = {"node_id": "wrong"}
    assert not retriever._valid_neighbor(row, [ref], ["SUPERSEDES"], "in")


async def test_explicit_unresolved_seed_is_not_assumed_to_be_entity():
    graph = AsyncMock()
    graph.seed_events.return_value = []
    graph.get_event_nodes.return_value = []
    graph.event_neighbors.return_value = []
    graph.cross_session_entity_events.return_value = []
    bundle = resolve_bundle(load_registry([], builtin_packs=[]))
    engine = RetrievalEngine(
        graph,
        decay=DecaySettings(),
        bundle=bundle,
        intents=RegistryIntents.for_events(bundle.registry),
    )
    response = await engine.get_subgraph(
        SubgraphQuery(query="hello", session_id="s", agent_id="a", seed_nodes=["UserProfile:past"])
    )
    graph.event_neighbors.assert_not_awaited()
    assert response.nodes == {} and response.meta.seed_nodes == []


async def test_disabled_user_explicit_intent_rejected_before_any_provider_call():
    graph, llm = AsyncMock(), AsyncMock()
    bundle = resolve_bundle(load_registry([], builtin_packs=[]))
    engine = RetrievalEngine(
        graph,
        decay=DecaySettings(),
        bundle=bundle,
        intents=RegistryIntents.for_events(bundle.registry),
        llm_client=llm,
    )
    with pytest.raises(UnsupportedIntentError):
        await engine.get_subgraph(
            SubgraphQuery(
                query="preferences",
                session_id="s",
                agent_id="a",
                intent="personalize",
                use_hyde=True,
            )
        )
    assert graph.mock_calls == llm.mock_calls == []


async def test_entity_vector_seed_with_colliding_event_id_expands_typed_references():
    graph = MemoryGraphStore()
    await graph._upsert_nodes(
        [
            (("Event", "same"), {"event_id": "same"}),
            (("Event", "correct"), {"event_id": "correct"}),
            (("Entity", "same"), {"entity_id": "same"}),
        ]
    )
    await graph._upsert_edges([((("Event", "correct"), "REFERENCES", ("Entity", "same")), {})])
    selected, bundle = view(graph)
    vector = AsyncMock()
    vector.nearest.return_value = [SearchHit("same", 0, 0.9), SearchHit("absent", 1, 0.8)]
    engine = RetrievalEngine(
        ComposedGraphReads(selected),
        decay=DecaySettings(),
        bundle=bundle,
        pack_graph=selected,
        vector_index=vector,
    )
    assert await engine._get_vector_seeds([1.0], 10) == [("correct", 0.9)]


async def test_spanner_read_view_preserves_storage_error_translation():
    from google.api_core.exceptions import ServiceUnavailable

    from context_graph.adapters.spanner.graph import SpannerGraphStore
    from context_graph.ports.errors import UnavailableError

    graph = SpannerGraphStore(AsyncMock(), embedding_dimensions=3)
    graph._get_nodes = AsyncMock(side_effect=ServiceUnavailable("test unavailable"))
    selected, _bundle = view(graph)
    with pytest.raises(UnavailableError):
        await selected.get_nodes([NodeRef("Event", "e", "event_id")])


async def test_storage_factory_exposes_scoped_reads_and_original_privacy_store():
    from context_graph.adapters.registry import open_stores
    from context_graph.settings import OntologySettings, Settings, StorageSettings

    stores = await open_stores(
        Settings(
            ontology=OntologySettings(packs=["pdlc"], builtin_packs=[]),
            storage=StorageSettings(
                event_log="memory",
                graph="memory",
                subscription="memory",
                keyword_index="memory",
                vector_index="memory",
            ),
        )
    )
    try:
        await stores.graph.write_user_profile({"user_id": "past"})
        assert stores.pack_reads is not None
        assert await stores.pack_reads.find_nodes("UserProfile", {}, 10) == []
        assert await stores.graph.get_user_profile("past") is not None
        assert isinstance(stores.graph_reads, ComposedGraphReads)
    finally:
        await stores.close()


@pytest.mark.parametrize(
    ("label", "edge_type", "key_field", "row_field", "stale_field"),
    [
        ("Entity", "REFERENCES", "entity_id", "neighbor_entity_id", "neighbor_event_id"),
        ("Event", "CAUSED_BY", "event_id", "neighbor_event_id", "neighbor_entity_id"),
    ],
)
async def test_neighbor_identity_uses_validated_label_not_stale_properties(
    label, edge_type, key_field, row_field, stale_field
):
    graph = AsyncMock()
    graph.event_neighbors.return_value = [
        {
            "seed_event_id": "seed",
            "rel_type": edge_type,
            "neighbor_labels": [label],
            row_field: "good",
            stale_field: "wrong",
            "neighbor_props": {
                key_field: "good",
                "event_id": "good" if label == "Event" else "wrong",
            },
        }
    ]
    bundle = resolve_bundle(load_registry([], builtin_packs=[]))
    engine = RetrievalEngine(graph, decay=DecaySettings(), bundle=bundle)
    nodes, edges, seen = {}, [], set()
    await engine._expand_neighbors(["seed"], nodes, edges, seen, {}, None)
    assert set(nodes) == {"good"}
    assert nodes["good"].node_type == label
    assert [(e.source, e.target, e.edge_type) for e in edges] == [("seed", "good", edge_type)]
