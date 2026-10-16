import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from engram_pilot_recovery_proof import PROVIDER_REJECTION, RecoveryHooks, freeze

from context_graph.domain.memory_actions import MemoryAction
from context_graph.domain.models import Event


def hooks():
    record = {}
    return RecoveryHooks(freeze("unit-p10"), record, lambda: None)


def test_frozen_recovery_inputs_valid_and_memory_identity_matches_storage_and_read():
    plan = freeze("unit-p10")
    events = [s["request"] for g in plan["groups"] for s in g["steps"]]
    assert len(events) == len({e["event_id"] for e in events}) == 6
    for request in events:
        Event.model_validate_json(json.dumps(request))
    b = plan["groups"][1]
    for index in (0, 1, 2):
        r = b["steps"][index]["request"]
        a = MemoryAction.from_event(
            Event.model_validate_json(json.dumps(r)), r["payload"], trusted=True
        )
        assert a.subject.key == (b["positive_goal"] if index == 2 else b["goal"])
    assert b["steps"][0]["request"]["occurred_at"] > b["steps"][1]["request"]["occurred_at"]


async def test_projection_barrier_holds_actual_processing_and_releases():
    h = hooks()
    w = SimpleNamespace(process_message=AsyncMock())
    original = w.process_message
    h.install("a", "projection", w)
    task = asyncio.create_task(w.process_message("position", {"event_id": h.delay_id}))
    await asyncio.wait_for(h.projection_entered.wait(), 1)
    original.assert_not_awaited()
    assert not task.done()
    h.release_all()
    await task
    original.assert_awaited_once_with("position", {"event_id": h.delay_id})


async def test_memory_pending_skip_returns_to_parent_reads_without_touching_retry():
    h = hooks()
    w = SimpleNamespace(_memory_diagnostic=AsyncMock(), _retry_pending_memory=AsyncMock())
    retry = w._retry_pending_memory
    h.install("b", "projection", w)
    event = SimpleNamespace(event_id=h.child_id)
    await w._memory_diagnostic(event, "deferred", "reference_missing")
    assert h.child_deferred.is_set()
    await asyncio.wait_for(w._retry_pending_memory(), 0.1)
    retry.assert_not_awaited()
    h.skip_memory_retries = False
    await w._retry_pending_memory()
    retry.assert_awaited_once()


async def test_provider_context_is_marked_once_restored_on_error_and_generation_pinned():
    h = hooks()
    seen = []

    async def original(**kwargs):
        seen.append(PROVIDER_REJECTION.get())
        if len(seen) == 1:
            raise RuntimeError("test failure")
        return {}

    w = SimpleNamespace(_llm_client=SimpleNamespace(extract_from_session=original))
    h.install("a", "extraction", w)
    with pytest.raises(RuntimeError):
        await w._llm_client.extract_from_session(session_id=h.failed_session)
    assert PROVIDER_REJECTION.get() is None
    assert seen[-1]["inject"] is True and seen[-1]["generation"] == 0
    h.generation = 1
    await w._llm_client.extract_from_session(session_id=h.failed_session)
    assert seen[-1]["inject"] is False and seen[-1]["generation"] == 0
    fresh = SimpleNamespace(_llm_client=SimpleNamespace(extract_from_session=original))
    h.install("a", "extraction", fresh)
    await fresh._llm_client.extract_from_session(session_id=h.failed_session)
    assert seen[-1]["generation"] == 1 and seen[-1]["inject"] is False
    await fresh._llm_client.extract_from_session(session_id="another-session")
    assert seen[-1] is None and PROVIDER_REJECTION.get() is None


async def test_consolidation_hold_finishes_current_job_and_detects_extra_stopped_work():
    h = hooks()
    h.arm_stop = True
    w = SimpleNamespace(_consolidate_session=AsyncMock(), _stopped=False)
    original = w._consolidate_session
    h.install("a", "consolidation", w)
    task = asyncio.create_task(w._consolidate_session("session", 5))
    await asyncio.wait_for(h.held_session.wait(), 1)
    w._stopped = True
    assert not task.done()
    original.assert_not_awaited()
    h.session_release.set()
    await task
    assert h.held_finished and h.later_sessions == []
    original.assert_awaited_once_with("session", 5)
    await w._consolidate_session("forbidden-next", 5)
    assert h.later_sessions == ["forbidden-next"]


async def test_recovery_goal_public_terminal_state_uses_creation_provenance():
    from engram_pilot_tenant_proof import memory_read_request

    from context_graph.adapters.memory.graph import MemoryGraphStore
    from context_graph.domain.memory_actions import MemoryReferenceMissingError
    from context_graph.domain.models import SubgraphQuery
    from context_graph.domain.projection import event_to_node
    from tests.unit.test_memory_episodes import selected_engine

    group = freeze("unit-p10-read")["groups"][1]
    child, parent, _ = group["steps"]
    graph = MemoryGraphStore()
    events = {}
    for position, step in enumerate((child, parent), 1):
        event = Event.model_validate_json(json.dumps(step["request"])).model_copy(
            update={"global_position": "unit-" + str(position)}
        )
        events[step["scenario"]] = event
        await graph.merge_event_node(event_to_node(event))
    action = MemoryAction.from_event(events["child"], child["request"]["payload"], trusted=True)
    with pytest.raises(MemoryReferenceMissingError):
        await graph.apply_memory_action(action)
    await graph.apply_memory_action(
        MemoryAction.from_event(events["parent"], parent["request"]["payload"], trusted=True)
    )
    await graph.apply_memory_action(action)
    body = memory_read_request({"steps": [parent]})
    result = await selected_engine(graph).get_subgraph(
        SubgraphQuery.model_validate_json(json.dumps(body))
    )
    node = result.nodes[group["goal"]]
    assert node.node_type == "Goal" and node.attributes["status"] == "completed"
    assert node.provenance.event_id == parent["request"]["event_id"]
    assert node.provenance.global_position == "unit-2"
    assert node.attributes["state_revision"] == 1 and node.attributes["evidence_count"] == 2
