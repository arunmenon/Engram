"""Episode production and retrieval behavior through public storage/retrieval seams."""

from datetime import UTC, datetime

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.consolidation import create_summary_from_events
from context_graph.domain.episodes import episode_identity, materialize_episode_snapshot
from context_graph.ports.pack_graph import NodeRef, NodeWrite


async def test_episode_has_exact_membership_and_retry_identity():
    graph = MemoryGraphStore()
    events = [
        {
            "event_id": "event-a",
            "session_id": "session-a",
            "occurred_at": "2026-10-10T10:00:00+00:00",
        },
        {
            "event_id": "event-b",
            "session_id": "session-a",
            "occurred_at": "2026-10-10T10:05:00+00:00",
        },
    ]
    await graph.upsert_nodes(
        [NodeWrite(NodeRef("Event", e["event_id"], "event_id"), e) for e in events]
    )
    summary = create_summary_from_events(
        events, "episode", episode_identity("session-a", [e["event_id"] for e in events])
    )
    await graph.write_summary_with_edges(
        summary.summary_id,
        summary.scope,
        summary.scope_id,
        summary.content,
        summary.created_at.isoformat(),
        summary.event_count,
        [dt.isoformat() for dt in summary.time_range],
        [e["event_id"] for e in events],
    )
    first = await materialize_episode_snapshot(graph, "session-a", summary, events)
    second = await materialize_episode_snapshot(graph, "session-a", summary, list(reversed(events)))
    assert first == second
    snapshots = await graph.find_nodes("Episode", {"session_id": "session-a"}, 10)
    assert len(snapshots) == 1
    assert snapshots[0]["event_count"] == 2 and snapshots[0]["complete"] is True
    links = await graph.neighbors(
        [NodeRef("Episode", first, "episode_id")], ["CONTAINS"], "out", 10
    )
    assert {r["target_key"] for r in links} == {"event-a", "event-b"}
    assert snapshots[0]["summary_id"] == summary.summary_id


async def test_missing_source_is_not_a_complete_episode():
    graph = MemoryGraphStore()
    events = [
        {
            "event_id": "missing",
            "session_id": "session-a",
            "occurred_at": "2026-10-10T10:00:00+00:00",
        }
    ]
    summary = create_summary_from_events(
        events, "episode", episode_identity("session-a", [e["event_id"] for e in events])
    )
    await graph.write_summary_with_edges(
        summary.summary_id,
        summary.scope,
        summary.scope_id,
        summary.content,
        summary.created_at.isoformat(),
        summary.event_count,
        [dt.isoformat() for dt in summary.time_range],
        [e["event_id"] for e in events],
    )
    with pytest.raises(ValueError, match="source"):
        await materialize_episode_snapshot(graph, "session-a", summary, events)
    assert await graph.find_nodes("Episode", {"complete": True}, 10) == []
    await graph.upsert_nodes([NodeWrite(NodeRef("Event", "missing", "event_id"), events[0])])
    await graph.write_summary_with_edges(
        summary.summary_id,
        summary.scope,
        summary.scope_id,
        summary.content,
        summary.created_at.isoformat(),
        summary.event_count,
        [dt.isoformat() for dt in summary.time_range],
        ["missing"],
    )
    await materialize_episode_snapshot(graph, "session-a", summary, events)
    assert len(await graph.find_nodes("Episode", {"complete": True}, 10)) == 1


@pytest.mark.parametrize("memory_enabled", [False, True])
async def test_consolidation_keeps_core_summaries_and_gates_episodes(memory_enabled):
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.memory.stream import MemoryStream
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry
    from context_graph.settings import Settings
    from context_graph.worker.consolidation import ConsolidationConsumer

    graph = MemoryGraphStore()
    await graph.upsert_nodes(
        [
            NodeWrite(
                NodeRef("Event", "recent", "event_id"),
                {
                    "session_id": "session-a",
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "event_type": "observation.input",
                    "importance_score": 5,
                },
            )
        ]
    )
    settings = Settings()
    settings.decay.reflection_threshold = 5
    settings.archive.enabled = False
    bundle = resolve_bundle(load_registry([], builtin_packs=["memory"] if memory_enabled else []))
    worker = ConsolidationConsumer(
        MemorySubscription(MemoryStream("events"), "consolidation", "test"),
        MemoryEventLog(),
        graph,
        settings,
        bundle=bundle,
        episode_graph=graph,
    )
    await worker.process_message("trigger", {"message_type": "consolidation_trigger"})
    assert await graph.find_nodes("Summary", {"scope": "episode"}, 10)
    episodes = await graph.find_nodes("Episode", {}, 10)
    assert len(episodes) == int(memory_enabled)
    if memory_enabled:
        assert episodes[0]["complete"] is True


async def test_session_timeline_retrieves_episode_members_summary_and_evidence():
    from context_graph.adapters.composed_reads import (
        ComposedGraphReads,
        ComposedReadView,
        ReadScope,
    )
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.domain.pack_intents import RegistryIntents
    from context_graph.ontology.loader import load_registry
    from context_graph.retrieval.engine import RetrievalEngine
    from context_graph.settings import DecaySettings

    graph = MemoryGraphStore()
    events = [
        {
            "event_id": "event-a",
            "session_id": "session-a",
            "occurred_at": "2026-10-10T10:00:00+00:00",
            "global_position": "position-a",
            "agent_id": "agent-a",
        },
        {
            "event_id": "event-b",
            "session_id": "session-a",
            "occurred_at": "2026-10-10T10:05:00+00:00",
            "global_position": "position-b",
            "agent_id": "agent-a",
        },
    ]
    await graph.upsert_nodes(
        [NodeWrite(NodeRef("Event", e["event_id"], "event_id"), e) for e in events]
    )
    summary = create_summary_from_events(
        events, "episode", episode_identity("session-a", [e["event_id"] for e in events])
    )
    await graph.write_summary_with_edges(
        summary.summary_id,
        summary.scope,
        summary.scope_id,
        summary.content,
        summary.created_at.isoformat(),
        summary.event_count,
        [dt.isoformat() for dt in summary.time_range],
        [e["event_id"] for e in events],
    )
    identity = await materialize_episode_snapshot(graph, "session-a", summary, events)
    bundle = resolve_bundle(load_registry([], builtin_packs=["memory"]))
    selected = ComposedReadView(graph, ReadScope.from_bundle(bundle))
    engine = RetrievalEngine(
        ComposedGraphReads(selected),
        decay=DecaySettings(),
        bundle=bundle,
        intents=RegistryIntents.for_events(bundle.registry),
        pack_graph=selected,
    )
    answer = await engine.get_subgraph(
        SubgraphQuery(
            query="Show the session timeline",
            session_id="session-a",
            agent_id="agent-a",
            intent="when",
        )
    )
    assert set(answer.nodes) == {identity, summary.summary_id, "event-a", "event-b"}
    assert answer.nodes[identity].node_type == "Episode"
    assert answer.nodes[identity].provenance.event_id == "event-a"
    assert {(e.source, e.edge_type, e.target) for e in answer.edges} >= {
        (identity, "CONTAINS", "event-a"),
        (identity, "CONTAINS", "event-b"),
        (summary.summary_id, "SUMMARIZES", identity),
    }


async def test_summary_from_another_event_set_cannot_be_attached():
    graph = MemoryGraphStore()
    events = [
        {
            "event_id": "event-a",
            "session_id": "session-a",
            "occurred_at": "2026-10-10T10:00:00+00:00",
        }
    ]
    await graph.upsert_nodes([NodeWrite(NodeRef("Event", "event-a", "event_id"), events[0])])
    summary = create_summary_from_events(
        events, "episode", episode_identity("session-a", [e["event_id"] for e in events])
    )
    # A stored summary with no actual source links is not sufficient evidence.
    await graph.merge_summary_node(summary)
    with pytest.raises(ValueError, match="summary"):
        await materialize_episode_snapshot(graph, "session-a", summary, events)
    assert await graph.find_nodes("Episode", {"complete": True}, 10) == []


async def test_interrupted_evidence_write_stays_incomplete_and_retry_converges():
    class InterruptedGraph(MemoryGraphStore):
        fail = False

        async def upsert_edges(self, writes):
            if self.fail:
                self.fail = False
                await super().upsert_edges(writes[:1])
                raise OSError("Simulated storage interruption")
            return await super().upsert_edges(writes)

    graph = InterruptedGraph()
    events = [
        {
            "event_id": "event-a",
            "session_id": "session-a",
            "occurred_at": "2026-10-10T10:00:00+00:00",
        }
    ]
    await graph.upsert_nodes([NodeWrite(NodeRef("Event", "event-a", "event_id"), events[0])])
    summary = create_summary_from_events(
        events, "episode", episode_identity("session-a", [e["event_id"] for e in events])
    )
    await graph.write_summary_with_edges(
        summary.summary_id,
        summary.scope,
        summary.scope_id,
        summary.content,
        summary.created_at.isoformat(),
        1,
        [dt.isoformat() for dt in summary.time_range],
        ["event-a"],
    )
    graph.fail = True
    with pytest.raises(OSError):
        await materialize_episode_snapshot(graph, "session-a", summary, events)
    assert await graph.find_nodes("Episode", {"complete": True}, 10) == []
    identity = await materialize_episode_snapshot(graph, "session-a", summary, events)
    await materialize_episode_snapshot(graph, "session-a", summary, events)
    assert len(await graph.find_nodes("Episode", {"complete": True}, 10)) == 1
    assert (
        len(
            await graph.neighbors(
                [NodeRef("Episode", identity, "episode_id")],
                ["CONTAINS", "DERIVED_FROM", "SUMMARIZES"],
                "both",
                10,
            )
        )
        == 3
    )


def selected_engine(graph, memory_enabled=True):
    from context_graph.adapters.composed_reads import (
        ComposedGraphReads,
        ComposedReadView,
        ReadScope,
    )
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.domain.pack_intents import RegistryIntents
    from context_graph.ontology.loader import load_registry
    from context_graph.retrieval.engine import RetrievalEngine
    from context_graph.settings import DecaySettings

    bundle = resolve_bundle(load_registry([], builtin_packs=["memory"] if memory_enabled else []))
    selected = ComposedReadView(graph, ReadScope.from_bundle(bundle))
    return RetrievalEngine(
        ComposedGraphReads(selected),
        decay=DecaySettings(),
        bundle=bundle,
        intents=RegistryIntents.for_events(bundle.registry),
        pack_graph=selected,
    )


@pytest.mark.parametrize("memory_enabled,max_nodes", [(True, 100), (False, 100), (True, 1)])
async def test_read_is_session_bound_selection_gated_and_honest_about_limits(
    memory_enabled, max_nodes
):
    from context_graph.domain.models import SubgraphQuery

    graph = MemoryGraphStore()
    for sid in ["session-a", "session-b"]:
        events = [
            {
                "event_id": sid + "-event",
                "session_id": sid,
                "occurred_at": "2026-10-10T10:00:00+00:00",
                "global_position": "position-" + sid,
            }
        ]
        await graph.upsert_nodes(
            [NodeWrite(NodeRef("Event", events[0]["event_id"], "event_id"), events[0])]
        )
        summary = create_summary_from_events(
            events, "episode", episode_identity(sid, [e["event_id"] for e in events])
        )
        await graph.write_summary_with_edges(
            summary.summary_id,
            summary.scope,
            summary.scope_id,
            summary.content,
            summary.created_at.isoformat(),
            1,
            [dt.isoformat() for dt in summary.time_range],
            [events[0]["event_id"]],
        )
        await materialize_episode_snapshot(graph, sid, summary, events)
    answer = await selected_engine(graph, memory_enabled).get_subgraph(
        SubgraphQuery(
            query="Show the session timeline",
            session_id="session-a",
            agent_id="agent",
            intent="when",
            max_nodes=max_nodes,
        )
    )
    assert len(answer.nodes) <= max_nodes
    assert "session-b-event" not in answer.nodes
    assert all(
        node.attributes.get("session_id", "session-a") != "session-b"
        for node in answer.nodes.values()
    )
    assert all(edge.source in answer.nodes and edge.target in answer.nodes for edge in answer.edges)
    if not memory_enabled:
        assert not any(node.node_type == "Episode" for node in answer.nodes.values())
    elif max_nodes == 1:
        assert answer.meta.truncated is True
    else:
        assert sum(node.node_type == "Episode" for node in answer.nodes.values()) == 1


@pytest.mark.parametrize(
    "corruption",
    ["scope", "count", "owner", "range", "missing-evidence", "extra-member", "episode-range"],
)
async def test_corrupt_snapshot_evidence_is_not_retrieved(corruption):
    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.pack_graph import EdgeWrite

    graph = MemoryGraphStore()
    events = [
        {
            "event_id": "source",
            "session_id": "s",
            "occurred_at": "2026-10-10T10:00:00+00:00",
            "global_position": "p",
        }
    ]
    await graph.upsert_nodes([NodeWrite(NodeRef("Event", "source", "event_id"), events[0])])
    summary = create_summary_from_events(events, "episode", episode_identity("s", ["source"]))
    await graph.write_summary_with_edges(
        summary.summary_id,
        summary.scope,
        summary.scope_id,
        summary.content,
        summary.created_at.isoformat(),
        1,
        [dt.isoformat() for dt in summary.time_range],
        ["source"],
    )
    identity = await materialize_episode_snapshot(graph, "s", summary, events)
    summary_ref = NodeRef("Summary", summary.summary_id, "summary_id")
    updates = {
        "scope": {"scope": "agent"},
        "count": {"event_count": 999},
        "owner": {"scope_id": "other"},
        "range": {"time_range": []},
    }
    if corruption in updates:
        await graph.upsert_nodes([NodeWrite(summary_ref, updates[corruption])])
    elif corruption == "missing-evidence":
        # Fault injection at the reference-storage boundary, never live acceptance.
        graph.edges.pop((("Summary", summary.summary_id), "SUMMARIZES", ("Event", "source")))
    elif corruption == "episode-range":
        await graph.upsert_nodes(
            [
                NodeWrite(
                    NodeRef("Episode", identity, "episode_id"),
                    {"start_time": "2000-01-01T00:00:00+00:00"},
                )
            ]
        )
    else:
        other = NodeRef("Event", "other", "event_id")
        await graph.upsert_nodes([NodeWrite(other, {**events[0], "event_id": "other"})])
        await graph.upsert_edges(
            [EdgeWrite("CONTAINS", NodeRef("Episode", identity, "episode_id"), other)]
        )
    answer = await selected_engine(graph).get_subgraph(
        SubgraphQuery(query="Show session timeline", session_id="s", agent_id="a", intent="when")
    )
    assert identity not in answer.nodes
    if corruption in updates:
        with pytest.raises(ValueError, match="summary"):
            await materialize_episode_snapshot(graph, "s", summary, events)


async def test_public_worker_preserves_history_when_a_late_event_bridges_groups():
    from datetime import timedelta

    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.memory.stream import MemoryStream
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry
    from context_graph.settings import Settings
    from context_graph.worker.consolidation import ConsolidationConsumer

    graph = MemoryGraphStore()
    now = datetime.now(UTC)

    async def add(key, minute):
        await graph.upsert_nodes(
            [
                NodeWrite(
                    NodeRef("Event", key, "event_id"),
                    {
                        "session_id": "s",
                        "occurred_at": (now + timedelta(minutes=minute)).isoformat(),
                        "global_position": key,
                        "importance_score": 5,
                    },
                )
            ]
        )

    await add("a", -60)
    await add("b", -20)
    settings = Settings()
    settings.decay.reflection_threshold = 5
    settings.archive.enabled = False
    bundle = resolve_bundle(load_registry([], builtin_packs=["memory"]))
    worker = ConsolidationConsumer(
        MemorySubscription(MemoryStream("events"), "consolidation", "test"),
        MemoryEventLog(),
        graph,
        settings,
        bundle=bundle,
        episode_graph=graph,
    )
    await worker.process_message("first", {"message_type": "consolidation_trigger"})
    assert {tuple(p["source_event_ids"]) for p in await graph.find_nodes("Episode", {}, 10)} == {
        ("a",),
        ("b",),
    }
    await add("bridge", -40)
    await worker.process_message("late", {"message_type": "consolidation_trigger"})
    await worker.process_message("retry", {"message_type": "consolidation_trigger"})
    snapshots = await graph.find_nodes("Episode", {}, 10)
    assert {tuple(p["source_event_ids"]) for p in snapshots} == {
        ("a",),
        ("b",),
        ("a", "b", "bridge"),
    }
    assert all(p["complete"] and p["snapshot_kind"] == "membership" for p in snapshots)
    answer = await selected_engine(graph).get_subgraph(
        SubgraphQuery(query="Show timeline", session_id="s", agent_id="a", intent="when")
    )
    assert sum(n.node_type == "Episode" for n in answer.nodes.values()) == 3


async def test_public_worker_retry_repairs_partial_snapshot_before_read_exposure():
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.memory.stream import MemoryStream
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry
    from context_graph.settings import Settings
    from context_graph.worker.consolidation import ConsolidationConsumer

    class InterruptedGraph(MemoryGraphStore):
        failed = False

        async def upsert_edges(self, writes):
            if not self.failed and any(write.edge_type == "CONTAINS" for write in writes):
                self.failed = True
                await super().upsert_edges(writes[:1])
                raise OSError("Storage boundary interruption")
            return await super().upsert_edges(writes)

    graph = InterruptedGraph()
    await graph.upsert_nodes(
        [
            NodeWrite(
                NodeRef("Event", "source", "event_id"),
                {
                    "session_id": "s",
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "global_position": "p",
                    "importance_score": 5,
                },
            )
        ]
    )
    settings = Settings()
    settings.decay.reflection_threshold = 5
    settings.archive.enabled = False
    bundle = resolve_bundle(load_registry([], builtin_packs=["memory"]))
    worker = ConsolidationConsumer(
        MemorySubscription(MemoryStream("events"), "consolidation", "test"),
        MemoryEventLog(),
        graph,
        settings,
        bundle=bundle,
        episode_graph=graph,
    )
    await worker.process_message("first", {"message_type": "consolidation_trigger"})
    assert graph.failed
    assert await graph.find_nodes("Episode", {"complete": True}, 10) == []
    query = SubgraphQuery(query="Show timeline", session_id="s", agent_id="a", intent="when")
    answer = await selected_engine(graph).get_subgraph(query)
    assert not any(n.node_type == "Episode" for n in answer.nodes.values())
    await worker.process_message("retry", {"message_type": "consolidation_trigger"})
    answer = await selected_engine(graph).get_subgraph(query)
    assert sum(n.node_type == "Episode" for n in answer.nodes.values()) == 1


@pytest.mark.parametrize("snapshots,members_per_snapshot", [(11, 1), (1, 501)])
async def test_episode_storage_bounds_are_explicit(snapshots, members_per_snapshot):
    from context_graph.domain.models import SubgraphQuery

    graph = MemoryGraphStore()
    for group in range(snapshots):
        events = [
            {
                "event_id": f"e-{group}-{index}",
                "session_id": "s",
                "occurred_at": "2026-10-10T10:00:00+00:00",
                "global_position": f"p-{group}-{index}",
            }
            for index in range(members_per_snapshot)
        ]
        await graph.upsert_nodes(
            [NodeWrite(NodeRef("Event", e["event_id"], "event_id"), e) for e in events]
        )
        summary = create_summary_from_events(
            events, "episode", episode_identity("s", [e["event_id"] for e in events])
        )
        await graph.write_summary_with_edges(
            summary.summary_id,
            summary.scope,
            summary.scope_id,
            summary.content,
            summary.created_at.isoformat(),
            len(events),
            [dt.isoformat() for dt in summary.time_range],
            [e["event_id"] for e in events],
        )
        await materialize_episode_snapshot(graph, "s", summary, events)
    answer = await selected_engine(graph).get_subgraph(
        SubgraphQuery(
            query="Show session timeline",
            session_id="s",
            agent_id="a",
            intent="when",
            max_nodes=100,
        )
    )
    assert answer.meta.truncated
    assert sum(n.node_type == "Episode" for n in answer.nodes.values()) <= 10
    assert all(e.source in answer.nodes and e.target in answer.nodes for e in answer.edges)


async def test_producer_rejects_extra_summary_source_after_existing_episode_link():
    from context_graph.ports.pack_graph import EdgeWrite

    graph = MemoryGraphStore()
    events = [{"event_id": "source", "session_id": "s", "occurred_at": "2026-10-10T10:00:00+00:00"}]
    await graph.upsert_nodes(
        [
            NodeWrite(NodeRef("Event", "source", "event_id"), events[0]),
            NodeWrite(NodeRef("Event", "extra", "event_id"), {**events[0], "event_id": "extra"}),
        ]
    )
    summary = create_summary_from_events(events, "episode", episode_identity("s", ["source"]))
    await graph.write_summary_with_edges(
        summary.summary_id,
        summary.scope,
        summary.scope_id,
        summary.content,
        summary.created_at.isoformat(),
        1,
        [dt.isoformat() for dt in summary.time_range],
        ["source"],
    )
    await materialize_episode_snapshot(graph, "s", summary, events)
    await graph.upsert_edges(
        [
            EdgeWrite(
                "SUMMARIZES",
                NodeRef("Summary", summary.summary_id, "summary_id"),
                NodeRef("Event", "extra", "event_id"),
            )
        ]
    )
    with pytest.raises(ValueError, match="summary"):
        await materialize_episode_snapshot(graph, "s", summary, events)
