"""Cooperative stop completes current work without starting unrelated sessions."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.worker.consolidation import ConsolidationConsumer


def worker():
    settings = MagicMock()
    settings.consumer.block_timeout_ms = 100
    settings.consumer.max_retries = 5
    settings.decay.reflection_threshold = 1
    gm = AsyncMock()
    gm.get_session_event_counts.return_value = {"first": 1, "second": 1}
    gm.session_agent_id.return_value = None
    consumer = ConsolidationConsumer(
        subscription=MagicMock(), event_log=AsyncMock(), graph_maintenance=gm, settings=settings
    )
    consumer._recompute_importance_from_centrality = AsyncMock()
    consumer._run_forgetting = AsyncMock()
    consumer._trim_event_log = AsyncMock()
    return consumer, gm


@pytest.mark.asyncio
async def test_stop_finishes_current_session_before_joining_and_leaves_remaining_eligible():
    consumer, gm = worker()
    entered = asyncio.Event()
    release = asyncio.Event()
    visited = []

    async def session(sid, count):
        if sid == "first":
            entered.set()
            await release.wait()
        visited.append(sid)

    consumer._consolidate_session = session
    with patch("context_graph.worker.consolidation.log") as log:
        task = asyncio.create_task(consumer._run_consolidation_cycle_guarded(source="test"))
        await asyncio.wait_for(entered.wait(), 1)
        consumer.stop()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        await asyncio.wait_for(task, 1)
        assert visited == ["first"]
        assert any(
            call.args[0] == "consolidation_cycle_stopped" for call in log.info.call_args_list
        )
        assert not any(
            call.args[0] == "consolidation_cycle_completed" for call in log.info.call_args_list
        )
    gm.session_agent_id.assert_not_awaited()
    consumer._recompute_importance_from_centrality.assert_not_awaited()
    consumer._run_forgetting.assert_not_awaited()
    consumer._trim_event_log.assert_not_awaited()
    # Stop does not erase durable eligibility; an ordinary fresh worker sees both.
    fresh, _ = worker()
    fresh._graph_maintenance = gm
    fresh._consolidate_session = AsyncMock()
    await fresh._run_consolidation_cycle()
    assert [call.args[0] for call in fresh._consolidate_session.await_args_list] == [
        "first",
        "second",
    ]


@pytest.mark.asyncio
async def test_stop_before_cycle_starts_no_database_work():
    consumer, gm = worker()
    consumer._consolidate_session = AsyncMock()
    consumer.stop()
    await consumer._run_consolidation_cycle_guarded(source="test")
    gm.get_session_event_counts.assert_not_awaited()
    consumer._consolidate_session.assert_not_awaited()
    consumer._recompute_importance_from_centrality.assert_not_awaited()


@pytest.mark.asyncio
async def test_uninterrupted_cycle_keeps_sessions_and_maintenance():
    consumer, gm = worker()
    consumer._consolidate_session = AsyncMock()
    with patch("context_graph.worker.consolidation.log") as log:
        await consumer._run_consolidation_cycle_guarded(source="test")
        assert any(
            call.args[0] == "consolidation_cycle_completed" for call in log.info.call_args_list
        )
    assert [call.args[0] for call in consumer._consolidate_session.await_args_list] == [
        "first",
        "second",
    ]
    assert gm.session_agent_id.await_count == 2
    consumer._recompute_importance_from_centrality.assert_awaited_once()
    consumer._run_forgetting.assert_awaited_once()
    consumer._trim_event_log.assert_awaited_once()
