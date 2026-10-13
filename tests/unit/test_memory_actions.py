"""Memory actions through the public graph-storage boundary."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.domain.models import Event
from context_graph.ports.pack_graph import NodeRef


async def test_stated_belief_has_owner_confidence_and_real_source_evidence():
    from context_graph.domain.memory_actions import MemoryAction

    graph = MemoryGraphStore()
    event = Event(
        event_id=UUID("00000000-0000-0000-0000-000000000001"),
        event_type="memory.belief.stated",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="s",
        agent_id="agent-a",
        trace_id="t",
        payload_ref="memory:test",
        global_position="1000-0",
    )
    from context_graph.domain.projection import event_to_node

    await graph.merge_event_node(event_to_node(event))
    action = MemoryAction.from_event(
        event,
        {
            "key": "token-expiry",
            "belief_text": "Reset tokens expire after fifteen minutes.",
            "category": "world_model",
            "confidence": 0.8,
        },
    )
    assert await graph.apply_memory_action(action) == "applied"
    assert await graph.apply_memory_action(action) == "duplicate"
    nodes = await graph.find_nodes("Belief", {"agent_id": "agent-a"}, 10)
    assert len(nodes) == 1
    belief = nodes[0]
    assert belief["belief_text"] == "Reset tokens expire after fifteen minutes."
    assert belief["confidence"] == 0.8 and belief["origin"] == "stated"
    assert belief["scope"] == "session" and belief["session_id"] == "s"
    assert belief["confirmation_count"] == 1 and belief["state_revision"] == 0
    edges = await graph.neighbors(
        [NodeRef("Belief", belief["belief_id"], "belief_id")], ["DERIVED_FROM"], "out", 10
    )
    assert [(r["target_key"], r["properties"]["evidence_role"]) for r in edges] == [
        (str(event.event_id), "support")
    ]


async def test_distinct_confirmations_count_once_and_stale_revision_cannot_overwrite():
    import pytest

    from context_graph.domain.memory_actions import MemoryAction, MemoryActionConflictError
    from context_graph.domain.projection import event_to_node

    graph = MemoryGraphStore()
    events = [
        Event(
            event_id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
            event_type="memory.belief.stated" if index == 1 else "memory.belief.confirmed",
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="s",
            agent_id="agent-a",
            trace_id="t",
            payload_ref="memory:test",
            global_position=f"1000-{index}",
        )
        for index in (1, 2, 3)
    ]
    for event in events:
        await graph.merge_event_node(event_to_node(event))
    await graph.apply_memory_action(
        MemoryAction.from_event(
            events[0],
            {
                "key": "expiry",
                "belief_text": "Tokens expire.",
                "category": "world_model",
                "confidence": 0.7,
            },
        )
    )
    confirmation = MemoryAction.from_event(events[1], {"key": "expiry", "expected_revision": 0})
    assert await graph.apply_memory_action(confirmation) == "applied"
    assert await graph.apply_memory_action(confirmation) == "duplicate"
    with pytest.raises(MemoryActionConflictError, match="revision"):
        await graph.apply_memory_action(
            MemoryAction.from_event(events[2], {"key": "expiry", "expected_revision": 0})
        )
    belief = (await graph.find_nodes("Belief", {"local_key": "expiry"}, 10))[0]
    assert belief["confirmation_count"] == 2 and belief["state_revision"] == 1
    assert set(belief["supporting_event_ids"]) == {str(events[0].event_id), str(events[1].event_id)}


@pytest.mark.parametrize("terminal", ["completed", "abandoned"])
async def test_goal_explicit_terminal_action_preserves_evidence(terminal):
    import pytest

    from context_graph.domain.memory_actions import MemoryAction, MemoryActionConflictError
    from context_graph.domain.projection import event_to_node

    graph = MemoryGraphStore()
    created = Event(
        event_id=UUID("00000000-0000-0000-0000-000000000011"),
        event_type="memory.goal.created",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="s",
        agent_id="agent-a",
        trace_id="t",
        payload_ref="memory:g",
        global_position="1000-11",
    )
    completed = created.model_copy(
        update={
            "event_id": UUID("00000000-0000-0000-0000-000000000012"),
            "event_type": "memory.goal." + terminal,
            "global_position": "1000-12",
        }
    )
    late_created = created.model_copy(
        update={"event_id": UUID("00000000-0000-0000-0000-000000000013")}
    )
    for event in (created, completed, late_created):
        await graph.merge_event_node(event_to_node(event))
    await graph.apply_memory_action(
        MemoryAction.from_event(
            created,
            {
                "key": "ship-expiry",
                "description": "Ship fifteen-minute token expiry.",
                "priority": 3,
            },
        )
    )
    transition = MemoryAction.from_event(completed, {"key": "ship-expiry", "expected_revision": 0})
    assert await graph.apply_memory_action(transition) == "applied"
    assert await graph.apply_memory_action(transition) == "duplicate"
    with pytest.raises(MemoryActionConflictError):
        await graph.apply_memory_action(
            MemoryAction.from_event(
                late_created,
                {"key": "ship-expiry", "description": "Late old creation", "priority": 9},
            )
        )
    goal = (await graph.find_nodes("Goal", {"agent_id": "agent-a"}, 10))[0]
    assert goal["status"] == terminal and goal["state_revision"] == 1
    assert goal["description"] == "Ship fifteen-minute token expiry." and goal["priority"] == 3
    assert goal["evidence_count"] == 2
    assert set(goal["evidence_event_ids"]) == {str(created.event_id), str(completed.event_id)}


async def test_inferred_belief_starts_unconfirmed_then_explicit_confirmation_adds_support():
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.projection import event_to_node

    graph = MemoryGraphStore()
    inferred = Event(
        event_id=UUID("00000000-0000-0000-0000-000000000021"),
        event_type="memory.belief.inferred",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="s",
        agent_id="agent-a",
        trace_id="t",
        payload_ref="memory:i",
        global_position="1000-21",
    )
    confirmed = inferred.model_copy(
        update={
            "event_id": UUID("00000000-0000-0000-0000-000000000022"),
            "event_type": "memory.belief.confirmed",
        }
    )
    for event in (inferred, confirmed):
        await graph.merge_event_node(event_to_node(event))
    await graph.apply_memory_action(
        MemoryAction.from_event(
            inferred,
            {
                "key": "inference",
                "belief_text": "The service may cache reset tokens.",
                "category": "world_model",
                "confidence": 0.6,
            },
        )
    )
    belief = (await graph.find_nodes("Belief", {"local_key": "inference"}, 10))[0]
    assert belief["origin"] == "inferred" and belief["confirmation_count"] == 0
    assert belief["supporting_event_ids"] == []
    await graph.apply_memory_action(
        MemoryAction.from_event(confirmed, {"key": "inference", "expected_revision": 0})
    )
    belief = (await graph.find_nodes("Belief", {"local_key": "inference"}, 10))[0]
    assert belief["origin"] == "inferred" and belief["confirmation_count"] == 1
    assert belief["supporting_event_ids"] == [str(confirmed.event_id)]


@pytest.mark.parametrize("contradicts", [False, True])
async def test_belief_correction_preserves_both_statements_and_explicit_history(contradicts):
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.projection import event_to_node

    graph = MemoryGraphStore()
    events = [
        Event(
            event_id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
            event_type="memory.belief.corrected" if index == 33 else "memory.belief.stated",
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="s",
            agent_id="agent-a",
            trace_id="t",
            payload_ref="memory:c",
            global_position=f"1000-{index}",
        )
        for index in (31, 32, 33)
    ]
    for event in events:
        await graph.merge_event_node(event_to_node(event))
    for event, key, text in [
        (events[0], "old-expiry", "Tokens expire after thirty minutes."),
        (events[1], "new-expiry", "Tokens expire after fifteen minutes."),
    ]:
        await graph.apply_memory_action(
            MemoryAction.from_event(
                event,
                {"key": key, "belief_text": text, "category": "world_model", "confidence": 0.8},
            )
        )
    action = MemoryAction.from_event(
        events[2],
        {
            "key": "old-expiry",
            "replacement_key": "new-expiry",
            "expected_revision": 0,
            "contradicts": contradicts,
        },
    )
    assert await graph.apply_memory_action(action) == "applied"
    assert await graph.apply_memory_action(action) == "duplicate"
    rows = {
        p["local_key"]: p for p in await graph.find_nodes("Belief", {"agent_id": "agent-a"}, 10)
    }
    old, new = rows["old-expiry"], rows["new-expiry"]
    assert old["belief_text"] == "Tokens expire after thirty minutes."
    assert old["superseded_by"] == new["belief_id"] and old["state_revision"] == 1
    assert old["confirmation_count"] == new["confirmation_count"] == 1
    edges = await graph.neighbors(
        [NodeRef("Belief", new["belief_id"], "belief_id")], ["SUPERSEDES", "CONTRADICTS"], "out", 10
    )
    assert {(edge["edge_type"], edge["target_key"]) for edge in edges} == {
        ("SUPERSEDES", old["belief_id"]),
        *([("CONTRADICTS", old["belief_id"])] if contradicts else []),
    }
    assert all(edge["properties"]["source_event_id"] == str(events[2].event_id) for edge in edges)


async def test_superseding_a_goal_links_existing_replacement_without_completing_it():
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.projection import event_to_node

    graph = MemoryGraphStore()
    events = [
        Event(
            event_id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
            event_type="memory.goal.superseded" if index == 43 else "memory.goal.created",
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="s",
            agent_id="agent-a",
            trace_id="t",
            payload_ref="memory:gs",
            global_position=f"1000-{index}",
        )
        for index in (41, 42, 43)
    ]
    for event in events:
        await graph.merge_event_node(event_to_node(event))
    for event, key, description in [
        (events[0], "old", "Ship email-only recovery."),
        (events[1], "new", "Ship verified account recovery."),
    ]:
        await graph.apply_memory_action(
            MemoryAction.from_event(event, {"key": key, "description": description})
        )
    transition = MemoryAction.from_event(
        events[2], {"key": "old", "replacement_key": "new", "expected_revision": 0}
    )
    assert await graph.apply_memory_action(transition) == "applied"
    assert await graph.apply_memory_action(transition) == "duplicate"
    goals = {p["local_key"]: p for p in await graph.find_nodes("Goal", {}, 10)}
    assert goals["old"]["status"] == "superseded" and goals["old"]["evidence_count"] == 2
    assert goals["new"]["status"] == "active" and goals["new"]["evidence_count"] == 1
    assert goals["old"]["superseded_by"] == goals["new"]["goal_id"]
    edges = await graph.neighbors(
        [NodeRef("Goal", goals["new"]["goal_id"], "goal_id")], ["SUPERSEDES"], "out", 10
    )
    assert [(r["target_key"], r["properties"]["source_event_id"]) for r in edges] == [
        (goals["old"]["goal_id"], str(events[2].event_id))
    ]


async def test_replayed_creation_repairs_its_evidence_without_resetting_terminal_goal():
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.projection import event_to_node

    graph = MemoryGraphStore()
    created = Event(
        event_id=UUID("00000000-0000-0000-0000-000000000051"),
        event_type="memory.goal.created",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="s",
        agent_id="agent-a",
        trace_id="t",
        payload_ref="memory:repair",
        global_position="1000-51",
    )
    completed = created.model_copy(
        update={
            "event_id": UUID("00000000-0000-0000-0000-000000000052"),
            "event_type": "memory.goal.completed",
        }
    )
    for event in (created, completed):
        await graph.merge_event_node(event_to_node(event))
    creation = MemoryAction.from_event(
        created, {"key": "repair", "description": "Finish account recovery."}
    )
    await graph.apply_memory_action(creation)
    await graph.apply_memory_action(
        MemoryAction.from_event(completed, {"key": "repair", "expected_revision": 0})
    )
    # Reference-storage fault boundary, not live acceptance or manual cloud repair.
    graph.edges.pop(
        (("Goal", creation.subject.key), "DERIVED_FROM", ("Event", str(created.event_id)))
    )
    assert await graph.apply_memory_action(creation) == "duplicate"
    links = await graph.neighbors([creation.subject], ["DERIVED_FROM"], "out", 10)
    assert {row["target_key"] for row in links} == {str(created.event_id), str(completed.event_id)}
    goal = (await graph.find_nodes("Goal", {}, 10))[0]
    assert (
        goal["status"] == "completed"
        and goal["evidence_count"] == 2
        and goal["state_revision"] == 1
    )


async def test_projection_worker_materializes_selected_memory_and_records_applied_outcome():
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer

    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    event = Event(
        event_id=UUID("00000000-0000-0000-0000-000000000061"),
        event_type="memory.belief.stated",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="s",
        agent_id="agent-a",
        trace_id="t",
        payload_ref="memory:worker",
    )
    position = await ledger.append(
        event,
        {
            "key": "worker",
            "belief_text": "Expiry is fifteen minutes.",
            "confidence": 0.8,
            "category": "world_model",
        },
    )
    settings = Settings()
    settings.consumer.projection_batch_size = 1
    subscription = MemorySubscription(ledger.stream, "projection", "test")
    await subscription.ensure_group()
    worker = ProjectionConsumer(
        subscription,
        ledger,
        graph,
        settings,
        bundle=resolve_bundle(load_registry([], builtin_packs=["memory"])),
        memory_store=graph,
        memory_graph=graph,
    )
    await worker.process_message(position, {"event_id": str(event.event_id)})
    beliefs = await graph.find_nodes("Belief", {"agent_id": "agent-a"}, 10)
    assert len(beliefs) == 1 and beliefs[0]["belief_text"] == "Expiry is fifteen minutes."
    source = await graph.get_nodes([NodeRef("Event", str(event.event_id), "event_id")])
    assert source[NodeRef("Event", str(event.event_id), "event_id")]["memory_status"] == "applied"


async def test_subgraph_api_engine_returns_belief_with_actual_source_and_counter():
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.projection import event_to_node
    from tests.unit.test_memory_episodes import selected_engine

    graph = MemoryGraphStore()
    event = Event(
        event_id=UUID("00000000-0000-0000-0000-000000000071"),
        event_type="memory.belief.stated",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="s",
        agent_id="agent-a",
        trace_id="t",
        payload_ref="memory:read",
        global_position="1000-71",
    )
    await graph.merge_event_node(event_to_node(event))
    action = MemoryAction.from_event(
        event,
        {
            "key": "recall",
            "belief_text": "Expiry is fifteen minutes.",
            "category": "world_model",
            "confidence": 0.8,
        },
    )
    await graph.apply_memory_action(action)
    answer = await selected_engine(graph).get_subgraph(
        SubgraphQuery(
            query="What beliefs do we have?", session_id="s", agent_id="agent-a", intent="beliefs"
        )
    )
    assert action.subject.key in answer.nodes
    assert answer.nodes[action.subject.key].node_type == "Belief"
    assert answer.nodes[action.subject.key].attributes["confirmation_count"] == 1
    assert answer.nodes[action.subject.key].provenance.event_id == str(event.event_id)
    assert (action.subject.key, "DERIVED_FROM", str(event.event_id)) in {
        (e.source, e.edge_type, e.target) for e in answer.edges
    }


async def test_recall_suppresses_unsolicited_history_between_current_beliefs():
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.projection import event_to_node
    from context_graph.ports.pack_graph import EdgeWrite
    from tests.unit.test_memory_episodes import selected_engine

    graph = MemoryGraphStore()
    subjects = []
    for i in (81, 82):
        event = Event(
            event_id=UUID(int=i),
            event_type="memory.belief.stated",
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="s",
            agent_id="agent-a",
            trace_id="t",
            payload_ref="memory:read",
            global_position=f"1000-{i}",
        )
        await graph.merge_event_node(event_to_node(event))
        action = MemoryAction.from_event(
            event,
            dict(
                key=str(i), belief_text="A declared belief.", category="world_model", confidence=0.8
            ),
        )
        await graph.apply_memory_action(action)
        subjects.append(action.subject)
    # Corrupt the reference backend only: not an acceptance write or cloud repair.
    await graph.upsert_edges(
        [EdgeWrite("CONTRADICTS", subjects[0], subjects[1], {"source_event_id": "nonexistent"})]
    )
    answer = await selected_engine(graph).get_subgraph(
        SubgraphQuery(query="beliefs", session_id="s", agent_id="agent-a", intent="beliefs")
    )
    assert all(e.edge_type != "CONTRADICTS" for e in answer.edges)
    assert answer.meta.truncated


async def test_spanner_combined_action_budget_rejects_before_scheduling_any_mutations():
    from unittest.mock import MagicMock

    from context_graph.adapters.spanner.commits import (
        EDGE_ROW_MUTATIONS,
        NODE_ROW_MUTATIONS,
        CommitBudget,
        CommitTooLarge,
    )
    from context_graph.adapters.spanner.graph import SpannerGraphStore
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.projection import event_to_node

    event = Event(
        event_id=UUID(int=91),
        event_type="memory.belief.stated",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="s",
        agent_id="agent-a",
        trace_id="t",
        payload_ref="memory:budget",
        global_position="1000-91",
    )
    source = event_to_node(event).model_dump(mode="json")
    transaction = MagicMock()
    transaction.read.return_value = [("Event", str(event.event_id), source, None)]
    db = MagicMock()
    db.run_in_transaction.side_effect = lambda fn: fn(transaction)
    # Two node writes fit separately, as does the evidence edge; the atomic sum does not.
    graph = SpannerGraphStore(
        db,
        commit_budget=CommitBudget(max_mutations=2 * NODE_ROW_MUTATIONS + EDGE_ROW_MUTATIONS - 1),
    )
    action = MemoryAction.from_event(
        event,
        dict(
            key="budget", belief_text="No partial writes.", category="world_model", confidence=0.8
        ),
    )
    with pytest.raises(CommitTooLarge):
        await graph.apply_memory_action(action)
    transaction.insert_or_update.assert_not_called()


async def test_competing_same_revision_confirmations_apply_once():
    import asyncio

    from context_graph.domain.memory_actions import MemoryAction, MemoryActionConflictError
    from context_graph.domain.projection import event_to_node

    graph = MemoryGraphStore()
    actions = []
    for i, kind in ((101, "stated"), (102, "confirmed"), (103, "confirmed")):
        event = Event(
            event_id=UUID(int=i),
            event_type="memory.belief." + kind,
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="s",
            agent_id="agent-a",
            trace_id="t",
            payload_ref="memory:race",
            global_position=f"1000-{i}",
        )
        await graph.merge_event_node(event_to_node(event))
        payload = (
            dict(key="race", expected_revision=0)
            if kind == "confirmed"
            else dict(
                key="race",
                belief_text="One winning confirmation.",
                category="world_model",
                confidence=0.8,
            )
        )
        actions.append(MemoryAction.from_event(event, payload))
    await graph.apply_memory_action(actions[0])
    outcomes = await asyncio.gather(
        *(graph.apply_memory_action(a) for a in actions[1:]), return_exceptions=True
    )
    assert outcomes.count("applied") == 1
    assert sum(isinstance(o, MemoryActionConflictError) for o in outcomes) == 1
    state = (await graph.find_nodes("Belief", {}, 10))[0]
    assert state["confirmation_count"] == 2 and state["state_revision"] == 1


async def test_missing_reference_recovers_on_idle_and_exhaustion_is_explicit():
    from context_graph.adapters.memory.log import MemoryEventLog
    from context_graph.adapters.memory.subscription import MemorySubscription
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer

    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    subscription = MemorySubscription(ledger.stream, "projection", "test")
    await subscription.ensure_group()
    settings = Settings()
    settings.consumer.projection_batch_size = 1
    worker = ProjectionConsumer(
        subscription,
        ledger,
        graph,
        settings,
        bundle=resolve_bundle(load_registry([], builtin_packs=["memory"])),
        memory_store=graph,
        memory_graph=graph,
    )

    async def deliver(number, kind, payload):
        source = Event(
            event_id=UUID(int=number),
            event_type=kind,
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="s",
            agent_id="agent-a",
            trace_id="t",
            payload_ref="memory:pending",
        )
        await ledger.append(source, payload)
        deliveries = await subscription.read_new(1, 0)
        assert len(deliveries) == 1
        delivery = deliveries[0]
        await worker.process_message(delivery.position, delivery.fields)
        return source

    early = await deliver(111, "memory.belief.confirmed", dict(key="parent", expected_revision=0))
    early_ref = NodeRef("Event", str(early.event_id), "event_id")
    assert (await graph.get_nodes([early_ref]))[early_ref]["memory_status"] == "deferred"
    await deliver(
        112,
        "memory.belief.stated",
        dict(key="parent", belief_text="A late parent.", confidence=0.7, category="world_model"),
    )
    await worker.on_idle()
    assert (await graph.get_nodes([early_ref]))[early_ref]["memory_status"] == "applied"
    assert not await subscription.read_pending(10)
    absent = await deliver(
        113, "memory.goal.completed", dict(key="never-created", expected_revision=0)
    )
    for _ in range(7):
        await worker.on_idle()
    assert any(
        d["event_id"] == str(absent.event_id) and d["memory_reason"] == "reference_missing"
        for d in subscription.dead_letters
    )
    assert not await graph.find_nodes("Goal", {}, 10)


async def test_memory_recall_rejects_unrelated_same_owner_confirmation_receipt():
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.projection import event_to_node
    from context_graph.ports.pack_graph import EdgeWrite, NodeWrite
    from tests.unit.test_memory_episodes import selected_engine

    graph = MemoryGraphStore()
    actions = []
    for number, key in [(121, "target"), (122, "unrelated")]:
        event = Event(
            event_id=UUID(int=number),
            event_type="memory.belief.stated",
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="s",
            agent_id="agent-a",
            trace_id="t",
            payload_ref="memory:evidence",
            global_position=f"1000-{number}",
        )
        await graph.merge_event_node(event_to_node(event))
        action = MemoryAction.from_event(
            event,
            dict(key=key, belief_text="A declared belief.", confidence=0.7, category="world_model"),
        )
        await graph.apply_memory_action(action)
        actions.append(action)
    # Coordinated state+edge corruption cannot substitute a source bound to another subject.
    target = (await graph.get_nodes([actions[0].subject]))[actions[0].subject]
    wrong = str(actions[1].event.event_id)
    await graph.upsert_nodes(
        [
            NodeWrite(
                actions[0].subject,
                {**target, "evidence_event_ids": [wrong], "supporting_event_ids": [wrong]},
            )
        ]
    )
    graph.edges.pop(
        (
            ("Belief", actions[0].subject.key),
            "DERIVED_FROM",
            ("Event", str(actions[0].event.event_id)),
        )
    )
    await graph.upsert_edges(
        [
            EdgeWrite(
                "DERIVED_FROM",
                actions[0].subject,
                NodeRef("Event", wrong, "event_id"),
                {"evidence_role": "support"},
            )
        ]
    )
    answer = await selected_engine(graph).get_subgraph(
        SubgraphQuery(query="beliefs", session_id="s", agent_id="agent-a", intent="beliefs")
    )
    assert actions[0].subject.key not in answer.nodes and actions[1].subject.key in answer.nodes
    assert answer.meta.truncated


async def test_disabled_memory_read_excludes_already_stored_beliefs_and_goals():
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.projection import event_to_node
    from tests.unit.test_memory_episodes import selected_engine

    graph = MemoryGraphStore()
    for number, kind, payload in [
        (
            131,
            "memory.belief.stated",
            dict(
                key="disabled",
                belief_text="A stored belief.",
                confidence=0.7,
                category="world_model",
            ),
        ),
        (132, "memory.goal.created", dict(key="disabled", description="A stored goal.")),
    ]:
        event = Event(
            event_id=UUID(int=number),
            event_type=kind,
            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
            session_id="s",
            agent_id="agent-a",
            trace_id="t",
            payload_ref="memory:disabled",
            global_position=f"1000-{number}",
        )
        await graph.merge_event_node(event_to_node(event))
        await graph.apply_memory_action(MemoryAction.from_event(event, payload))
    answer = await selected_engine(graph, memory_enabled=False).get_subgraph(
        SubgraphQuery(query="Show the timeline", session_id="s", agent_id="agent-a", intent="when")
    )
    assert not any(node.node_type in ("Belief", "Goal") for node in answer.nodes.values())


async def test_spanner_mid_action_failure_escapes_one_transaction_without_fallback_commit():
    from unittest.mock import MagicMock

    from context_graph.adapters.spanner.graph import SpannerGraphStore
    from context_graph.domain.memory_actions import MemoryAction
    from context_graph.domain.projection import event_to_node

    event = Event(
        event_id=UUID(int=141),
        event_type="memory.goal.created",
        occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
        session_id="s",
        agent_id="agent-a",
        trace_id="t",
        payload_ref="memory:rollback",
        global_position="1000-141",
    )
    source = event_to_node(event).model_dump(mode="json")
    scheduled = []
    committed = []
    db = MagicMock()

    def transaction_boundary(callback):
        transaction = MagicMock()
        transaction.read.return_value = [("Event", str(event.event_id), source, None)]

        def schedule(table, columns, rows):
            scheduled.append(table)
            if table == "GraphEdges":
                raise RuntimeError("Injected SDK mutation scheduling failure")

        transaction.insert_or_update.side_effect = schedule
        result = callback(transaction)
        committed.extend(scheduled)
        return result

    db.run_in_transaction.side_effect = transaction_boundary
    graph = SpannerGraphStore(db)
    with pytest.raises(RuntimeError, match="Injected SDK"):
        await graph.apply_memory_action(
            MemoryAction.from_event(event, dict(key="rollback", description="No half Goal."))
        )
    assert scheduled == ["GraphNodes", "GraphEdges"]
    assert not committed and db.run_in_transaction.call_count == 1
