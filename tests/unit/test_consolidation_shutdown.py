"""Consolidation lifecycle through public run/stop and storage SDK seams."""

import asyncio
import threading
import time

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.adapters.memory.subscription import MemorySubscription
from context_graph.domain.projection import event_to_node
from context_graph.ports.errors import RuntimeFencedError, UnavailableError
from context_graph.settings import Settings
from context_graph.worker.consolidation import ConsolidationConsumer
from tests.fixtures.events import make_event


class HeldSummaryStorage:
    """Model an uncancellable synchronous SDK operation, not a worker mock."""

    def __init__(self, graph, failure=None, fail_once=False):
        self.graph = graph
        self.failure = failure
        self.fail_once = fail_once
        self.failures = 0
        self.entered = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()
        self.committed = []

    def __getattr__(self, name):
        return getattr(self.graph, name)

    def commit(self, values):
        self.entered.set()
        if not self.release.wait(10):
            raise TimeoutError("Test did not release its SDK operation")
        try:
            if self.failure:
                failure = self.failure
                self.failures += 1
                if self.fail_once:
                    self.failure = None
                raise failure
            self.committed.append(values)
        finally:
            self.finished.set()

    async def write_summary_with_edges(self, **values):
        await asyncio.to_thread(self.commit, values)
        await self.graph.write_summary_with_edges(**values)


async def make_worker(*, failure=None, interval=0.01, fail_once=False):
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    event = make_event(event_type="observation.input")
    position = await ledger.append(event, {})
    await graph.merge_event_node(
        event_to_node(event.model_copy(update={"global_position": position}))
    )
    storage = HeldSummaryStorage(graph, failure, fail_once)
    settings = Settings()
    settings.consumer.block_timeout_ms = 10
    settings.decay.reflection_threshold = 5
    settings.decay.reconsolidation_interval_hours = interval / 3600
    worker = ConsolidationConsumer(
        MemorySubscription(ledger.stream, "consolidation", "consolidation-1"),
        ledger,
        storage,
        settings,
    )
    return worker, storage, graph, ledger


async def wait_entered(storage):
    for _ in range(200):
        if storage.entered.is_set():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("A real timer cycle must reach the SDK boundary")


async def test_stop_waits_for_inflight_sdk_work_before_worker_reports_finished():
    worker, storage, graph, ledger = await make_worker()
    task = asyncio.create_task(worker.run())
    try:
        await wait_entered(storage)
        worker.stop()
        await asyncio.sleep(0.05)
        assert not task.done(), "Shutdown must wait for the SDK operation, not cancel its await"
        storage.release.set()
        await asyncio.wait_for(asyncio.shield(task), 3)
        assert storage.finished.is_set()
        committed = list(storage.committed)
        await asyncio.sleep(0.05)
        assert storage.committed == committed
        assert len(committed) == 3  # episode, session and agent summaries
    finally:
        storage.release.set()
        worker.stop()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("cancellations", [1, 3])
async def test_parent_cancellation_drains_sdk_and_whole_cycle_before_propagating(cancellations):
    worker, storage, graph, ledger = await make_worker()
    task = asyncio.create_task(worker.run())
    try:
        await wait_entered(storage)
        for _ in range(cancellations):
            task.cancel()
            await asyncio.sleep(0.02)
            assert not task.done(), "Repeated cancellation must not cancel the SDK await"
        storage.release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(asyncio.shield(task), 3)
        assert storage.finished.is_set()
        assert len(storage.committed) == 3
        assert {item["scope"] for item in storage.committed} == {"episode", "session", "agent"}
        committed = list(storage.committed)
        await asyncio.sleep(0.05)
        assert storage.committed == committed
    finally:
        storage.release.set()
        worker.stop()
        await asyncio.gather(task, return_exceptions=True)


async def test_stop_wakes_long_sleeping_timer_without_starting_a_cycle():
    worker, storage, graph, ledger = await make_worker(interval=6 * 3600)
    task = asyncio.create_task(worker.run())
    try:
        await asyncio.sleep(0.03)
        started = time.monotonic()
        worker.stop()
        worker.stop()
        await asyncio.wait_for(asyncio.shield(task), 0.5)
        assert time.monotonic() - started < 0.5
        assert not storage.entered.is_set()
    finally:
        worker.stop()
        storage.release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_stop_before_run_does_not_admit_a_timer_cycle():
    worker, storage, graph, ledger = await make_worker()
    worker.stop()
    await asyncio.wait_for(worker.run(), 0.5)
    assert not storage.entered.is_set()


@pytest.mark.parametrize("fenced", [False, True])
async def test_sdk_failure_finishes_before_shutdown_and_preserves_error_policy(fenced, capsys):
    failure = (
        RuntimeFencedError("controlled fence") if fenced else UnavailableError("controlled failure")
    )
    worker, storage, graph, ledger = await make_worker(failure=failure)
    task = asyncio.create_task(worker.run())
    try:
        await wait_entered(storage)
        worker.stop()
        await asyncio.sleep(0.02)
        assert not task.done()
        storage.release.set()
        if fenced:
            with pytest.raises(RuntimeFencedError, match="controlled fence"):
                await asyncio.wait_for(asyncio.shield(task), 3)
        else:
            await asyncio.wait_for(asyncio.shield(task), 3)
            assert "consolidation_cycle_failed" in capsys.readouterr().out
        assert storage.finished.is_set()
        assert storage.committed == []
    finally:
        storage.release.set()
        worker.stop()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("fenced", [False, True])
async def test_subscription_failure_drains_active_timer_before_error_escapes(fenced):
    worker, storage, graph, ledger = await make_worker()
    failure = (
        RuntimeFencedError("subscription fenced") if fenced else RuntimeError("subscription failed")
    )
    actual = worker._subscription

    class SubscriptionFailure:
        def __getattr__(self, name):
            return getattr(actual, name)

        async def read_new(self, count, block_ms):
            deliveries = await actual.read_new(count, block_ms)
            if storage.entered.is_set():
                raise failure
            return deliveries

    worker._subscription = SubscriptionFailure()
    task = asyncio.create_task(worker.run())
    try:
        await wait_entered(storage)
        await asyncio.sleep(0.05)
        assert not task.done(), "A failed subscription cannot cancel the timer's SDK await"
        storage.release.set()
        with pytest.raises(type(failure), match=str(failure)):
            await asyncio.wait_for(asyncio.shield(task), 3)
        assert storage.finished.is_set()
        assert len(storage.committed) == 3
    finally:
        storage.release.set()
        worker.stop()
        await asyncio.gather(task, return_exceptions=True)


async def test_timer_continues_after_a_logged_storage_failure(capsys):
    """Preserve the old ordinary-failure retry contract at the public seam."""
    worker, storage, graph, ledger = await make_worker(
        failure=UnavailableError("one controlled failure"), fail_once=True, interval=0.03
    )
    storage.release.set()
    task = asyncio.create_task(worker.run())
    try:
        for _ in range(200):
            if len(storage.committed) >= 3:
                break
            await asyncio.sleep(0.01)
        assert not task.done(), "An ordinary cycle failure must not kill the timer"
        assert storage.failures == 1
        assert {entry["scope"] for entry in storage.committed} == {"episode", "session", "agent"}
        worker.stop()
        await asyncio.wait_for(asyncio.shield(task), 3)
        assert "consolidation_cycle_failed" in capsys.readouterr().out
    finally:
        worker.stop()
        await asyncio.gather(task, return_exceptions=True)
