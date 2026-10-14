"""A fenced runtime stops; its event remains pending for authorized recovery."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from context_graph.ports.errors import RuntimeFencedError, is_transient
from context_graph.ports.subscription import Delivery
from context_graph.settings import Settings
from context_graph.worker.consolidation import ConsolidationConsumer
from context_graph.worker.consumer import BaseConsumer
from context_graph.worker.extraction import ExtractionConsumer
from context_graph.worker.projection import ProjectionConsumer


def subscription():
    port = AsyncMock()
    port.group_name = "group"
    port.consumer_name = "worker"
    port.source_name = "Events"
    port.delivery_counts.return_value = {}
    port.read_pending.return_value = []
    port.read_new.return_value = []
    return port


class Consumer(BaseConsumer):
    def __init__(self, port):
        super().__init__(port)
        self.process_message = AsyncMock()
        self.on_idle = AsyncMock()
        self.on_stop = AsyncMock()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["pending", "new", "idle", "ack"])
async def test_fenced_worker_exits_without_success_or_dead_letter(stage):
    port = subscription()
    consumer = Consumer(port)
    failure = RuntimeFencedError("epoch changed")
    delivery = Delivery("position", {"event_id": "same-event"})
    if stage == "pending":
        port.read_pending.return_value = [delivery]
        consumer.process_message.side_effect = failure
    elif stage == "new":
        port.read_new.return_value = [delivery]
        consumer.process_message.side_effect = failure
    elif stage == "idle":
        consumer.on_idle.side_effect = failure
    else:
        port.read_new.return_value = [delivery]
        port.ack.side_effect = failure

    with pytest.raises(RuntimeFencedError) as caught:
        await asyncio.wait_for(consumer.run(), timeout=1)
    assert caught.value is failure
    assert consumer._stopped
    port.dead_letter.assert_not_awaited()
    consumer.on_stop.assert_not_awaited()  # No graceful flush after losing authority.
    if stage != "ack":
        port.ack.assert_not_awaited()
    else:
        port.ack.assert_awaited_once_with("position")
    if stage in ("new", "pending"):
        consumer.process_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_fence_is_not_retried_as_a_transient_outage():
    consumer = Consumer(subscription())
    operation = AsyncMock(side_effect=RuntimeFencedError("changed"))
    assert not is_transient(RuntimeFencedError())
    with pytest.raises(RuntimeFencedError):
        await consumer._retry_transient(operation, "write")
    operation.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["plan", "batch", "individual"])
async def test_projection_never_dead_letters_a_control_failure(stage):
    port = subscription()
    projector = MagicMock()
    consumer = ProjectionConsumer(port, AsyncMock(), AsyncMock(), Settings(), projector)
    event = MagicMock()
    events = [("position", {"event_id": "same-event"}, event, {})]
    failure = RuntimeFencedError("changed")
    if stage == "plan":
        projector.plan.side_effect = failure
    batch = AsyncMock()
    if stage == "batch":
        batch.side_effect = failure
    elif stage == "individual":
        batch.side_effect = ValueError("ordinary batch failure")
    individual = AsyncMock(side_effect=failure)
    with (
        patch("context_graph.worker.projection.apply_plans", batch),
        patch("context_graph.worker.projection.apply_plan", individual),
        pytest.raises(RuntimeFencedError),
    ):
        await consumer._apply_pack_rules(events)
    port.dead_letter.assert_not_awaited()
    port.ack.assert_not_awaited()
    if stage != "individual":
        individual.assert_not_awaited()


@pytest.mark.asyncio
async def test_extractor_does_not_convert_fenced_reads_into_empty_session():
    port = subscription()
    ledger = AsyncMock()
    ledger.read_session_ids.side_effect = RuntimeFencedError("changed")
    consumer = ExtractionConsumer(port, ledger, AsyncMock(), Settings())
    with pytest.raises(RuntimeFencedError):
        await consumer._collect_session_events("session")
    ledger.get_documents.assert_not_awaited()


@pytest.mark.asyncio
async def test_consolidation_does_not_report_fenced_cycle_as_success():
    consumer = ConsolidationConsumer(subscription(), AsyncMock(), AsyncMock(), Settings())
    consumer._run_consolidation_cycle = AsyncMock(side_effect=RuntimeFencedError("changed"))
    with pytest.raises(RuntimeFencedError):
        await consumer._run_consolidation_cycle_guarded(source="stream")
    assert consumer._stopped
    assert not consumer._consolidation_lock.locked()


@pytest.mark.asyncio
async def test_background_fence_waits_for_inflight_subscription_read_before_exit():
    port = subscription()
    gm = AsyncMock()
    settings = Settings()
    settings.decay.reconsolidation_interval_hours = 0.01 / 3600
    consumer = ConsolidationConsumer(port, AsyncMock(), gm, settings)
    read_started = asyncio.Event()
    release_read = asyncio.Event()
    read_finished = asyncio.Event()
    failure = RuntimeFencedError("changed")

    async def read_new(*args):
        read_started.set()
        await release_read.wait()
        read_finished.set()
        return []

    async def fenced_counts():
        await read_started.wait()
        raise failure

    port.read_new.side_effect = read_new
    gm.get_session_event_counts.side_effect = fenced_counts
    task = asyncio.create_task(consumer.run())
    try:
        await asyncio.wait_for(read_started.wait(), 1)
        await asyncio.sleep(0.05)
        assert consumer._stopped
        assert not task.done(), "Fencing must not detach the in-flight subscription read"
        assert not read_finished.is_set()
        release_read.set()
        with pytest.raises(RuntimeFencedError) as caught:
            await asyncio.wait_for(asyncio.shield(task), 1)
        assert caught.value is failure
        assert read_finished.is_set()
    finally:
        release_read.set()
        consumer.stop()
        await asyncio.gather(task, return_exceptions=True)
