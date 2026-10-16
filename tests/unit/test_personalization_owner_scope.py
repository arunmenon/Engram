"""Shared search/entity matches cannot import another logical owner's events."""

import pytest

from context_graph.domain.models import SubgraphQuery
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.ontology.loader import load_registry
from tests.unit.test_retrieval_engine import FakeGraphReads, FakeKeywordIndex, _engine, _event


@pytest.mark.asyncio
@pytest.mark.parametrize("intent", ["personalize", "who_is"])
async def test_personalization_scopes_search_explicit_seeds_neighbors_and_cross_session(intent):
    alice = dict(_event("alice", session_id="s-alice"), agent_id="alice")
    prior = dict(_event("alice-prior", session_id="earlier"), agent_id="alice")
    bob = dict(_event("bob", session_id="s-bob"), agent_id="bob")
    unknown = _event("unknown", session_id="s-bob")
    unknown.pop("agent_id")

    class SharedEntities(FakeGraphReads):
        async def cross_session_entity_events(self, *_args, **_kwargs):
            # Shared Rust mentions produce candidates from both owners.
            return [bob, unknown, prior]

    graph = SharedEntities([alice, prior, bob, unknown])
    graph.edges.extend([("alice", "bob", "SIMILAR_TO"), ("alice", "unknown", "FOLLOWS")])
    bundle = resolve_bundle(load_registry([], builtin_packs=["core", "user"]))
    engine = _engine(graph, keyword_index=FakeKeywordIndex(["bob", "alice"]), bundle=bundle)
    answer = await engine.get_subgraph(
        SubgraphQuery(
            query="Which answer style should be used?",
            intent=intent,
            session_id="s-alice",
            agent_id="alice",
            seed_nodes=["alice", "bob"],
        )
    )
    assert {"alice", "alice-prior"} <= answer.nodes.keys()
    assert not {"bob", "unknown"} & answer.nodes.keys()
    assert all(edge.source != "bob" and edge.target != "bob" for edge in answer.edges)
    assert not {"bob", "unknown"} & set(graph.accessed)


@pytest.mark.asyncio
async def test_general_context_keeps_existing_cross_owner_graph_semantics():
    own = dict(_event("own"), agent_id="alice")
    other = dict(_event("other"), agent_id="bob")
    graph = FakeGraphReads([own, other])
    bundle = resolve_bundle(load_registry([], builtin_packs=["core", "user"]))
    answer = await _engine(graph, bundle=bundle).get_subgraph(
        SubgraphQuery(
            query="what happened",
            intent="what",
            session_id="s1",
            agent_id="alice",
        )
    )
    assert {"own", "other"} <= answer.nodes.keys()


@pytest.mark.asyncio
async def test_mixed_personalization_intent_cannot_reenter_through_memory_episode():
    from unittest.mock import AsyncMock

    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.domain.consolidation import create_summary_from_events
    from context_graph.domain.episodes import episode_identity, materialize_episode_snapshot
    from context_graph.domain.pack_intents import RegistryIntents
    from context_graph.ports.pack_graph import NodeRef, NodeWrite

    alice = dict(_event("alice", session_id="shared"), agent_id="alice")
    bob = dict(_event("bob", session_id="shared"), agent_id="bob")
    records = [alice, bob]
    store = MemoryGraphStore()
    await store.upsert_nodes(
        [NodeWrite(NodeRef("Event", p["event_id"], "event_id"), p) for p in records]
    )
    summary = create_summary_from_events(
        records, "episode", episode_identity("shared", ["alice", "bob"])
    )
    await store.write_summary_with_edges(
        summary.summary_id,
        summary.scope,
        summary.scope_id,
        summary.content,
        summary.created_at.isoformat(),
        summary.event_count,
        [dt.isoformat() for dt in summary.time_range],
        ["alice", "bob"],
    )
    episode = await materialize_episode_snapshot(store, "shared", summary, records)
    bundle = resolve_bundle(load_registry([], builtin_packs=["core", "user", "memory"]))
    intents = RegistryIntents.for_events(bundle.registry)
    inferred = {"personalize": 0.8, "when": 0.2}
    assert intents.edge_weights(inferred)["CONTAINS"] > 0
    graph = FakeGraphReads(records)
    engine = _engine(
        graph,
        bundle=bundle,
        pack_graph=store,
        intents=intents,
        intent_classifier=type("Classifier", (), {"classify": AsyncMock(return_value=inferred)})(),
    )
    answer = await engine.get_subgraph(
        SubgraphQuery(
            query="Remember my answer style and when I said it",
            session_id="shared",
            agent_id="alice",
        )
    )
    assert "alice" in answer.nodes
    assert not {"bob", episode, summary.summary_id} & answer.nodes.keys()
    assert "bob" not in graph.accessed
