"""Enrichment convergence through public worker and graph ports."""

import asyncio

import pytest

from context_graph.adapters.memory.graph import MemoryGraphStore
from context_graph.adapters.memory.log import MemoryEventLog
from context_graph.adapters.memory.subscription import MemorySubscription
from context_graph.domain.projection import event_to_node
from context_graph.ports.errors import UnavailableError
from context_graph.settings import Settings
from context_graph.worker.enrichment import EnrichmentConsumer
from tests.fixtures.events import make_event


async def test_enrichment_waits_for_projection_instead_of_losing_annotations():
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    event = make_event(event_type="observation.input", tool_name="race-tool", importance_hint=7)
    position = await ledger.append(event, {})
    worker = EnrichmentConsumer(
        MemorySubscription(ledger.stream, "enrichment", "enrichment-1"),
        ledger,
        graph,
        Settings(),
    )
    task = asyncio.create_task(worker.process_message(position, {"event_id": str(event.event_id)}))
    try:
        await asyncio.sleep(0.02)
        assert not task.done(), "Missing graph Event must keep enrichment unfinished"
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
        await asyncio.wait_for(task, 2)
        (stored,) = await graph.reads.get_event_nodes([str(event.event_id)])
        assert stored["keywords"] == ["observation", "input", "race-tool"]
        assert stored["importance_score"] == 7
    finally:
        worker.stop()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("batch", [False, True])
async def test_reprojection_and_duplicate_enrichment_preserve_annotations_and_adjustments(batch):
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    event = make_event(event_type="test.failed", tool_name="pytest", importance_hint=7)
    position = await ledger.append(event, {})
    node = event_to_node(event.model_copy(update={"global_position": position}))
    merge = graph.merge_event_nodes_batch if batch else graph.merge_event_node
    initial = node.model_copy(update={"summary": "kept summary", "access_count": 3})
    await merge([initial] if batch else initial)
    worker = EnrichmentConsumer(
        MemorySubscription(ledger.stream, "enrichment", "enrichment-1"), ledger, graph, Settings()
    )
    await worker.process_message(position, {"event_id": str(event.event_id)})
    await graph.store_event_embedding(str(event.event_id), [0.5, 0.25])
    await graph.adjust_node_importance(str(event.event_id), 2)
    await merge([node] if batch else node)
    await worker.process_message(position, {"event_id": str(event.event_id)})
    (stored,) = await graph.reads.get_event_nodes([str(event.event_id)])
    assert stored["keywords"] == ["test", "failed", "pytest"]
    assert stored["importance_score"] == 9
    assert stored["embedding"] == [0.5, 0.25]
    assert stored["summary"] == "kept summary"
    assert stored["access_count"] == 3


@pytest.mark.parametrize("embedding", [False, True])
async def test_absent_projection_never_creates_partial_event(embedding):
    graph = MemoryGraphStore()
    with pytest.raises(UnavailableError):
        if embedding:
            await graph.store_event_embedding("missing", [0.5])
        else:
            await graph.update_event_enrichment("missing", ["test"], 5)
    assert await graph.reads.get_event_nodes(["missing"]) == []


async def test_stop_before_projection_keeps_delivery_pending_for_fresh_worker():
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    event = make_event(event_type="observation.input", tool_name="restart-tool")
    position = await ledger.append(event, {})
    subscription = MemorySubscription(ledger.stream, "enrichment", "enrichment-1")
    settings = Settings()
    settings.consumer.block_timeout_ms = 10
    worker = EnrichmentConsumer(subscription, ledger, graph, settings)
    task = asyncio.create_task(worker.run())
    try:
        for _ in range(100):
            if await subscription.delivery_counts(limit=10):
                break
            await asyncio.sleep(0.01)
        assert await subscription.delivery_counts(limit=10) == {position: 1}
        worker.stop()
        await asyncio.wait_for(task, 2)
        assert await subscription.delivery_counts(limit=10) == {position: 1}
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
        fresh = EnrichmentConsumer(subscription, ledger, graph, settings)
        task = asyncio.create_task(fresh.run())
        for _ in range(100):
            if not await subscription.delivery_counts(limit=10):
                break
            await asyncio.sleep(0.01)
        assert await subscription.delivery_counts(limit=10) == {}
        (stored,) = await graph.reads.get_event_nodes([str(event.event_id)])
        assert stored["keywords"] == ["observation", "input", "restart-tool"]
        assert stored["importance_score"] == 5
        assert subscription.dead_letters == []
        fresh.stop()
        await asyncio.wait_for(task, 2)
    finally:
        worker.stop()
        if "fresh" in locals():
            fresh.stop()
        await asyncio.gather(task, return_exceptions=True)


async def test_missing_ledger_document_is_refetched_and_not_acknowledged_as_empty():
    graph, ledger = MemoryGraphStore(), MemoryEventLog()
    event = make_event(event_type="observation.input")
    worker = EnrichmentConsumer(
        MemorySubscription(ledger.stream, "enrichment", "enrichment-1"), ledger, graph, Settings()
    )
    task = asyncio.create_task(
        worker.process_message("source-position", {"event_id": str(event.event_id)})
    )
    try:
        await asyncio.sleep(0.02)
        assert not task.done()
        position = await ledger.append(event, {})
        await graph.merge_event_node(
            event_to_node(event.model_copy(update={"global_position": position}))
        )
        await asyncio.wait_for(task, 2)
        (stored,) = await graph.reads.get_event_nodes([str(event.event_id)])
        assert stored["keywords"] == ["observation", "input"]
        assert stored["importance_score"] == 5
    finally:
        worker.stop()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("existing", [None, 0, 9])
async def test_spanner_annotation_uses_transaction_current_importance(existing):
    """SDK boundary fixture: any outside snapshot would see obsolete score7.

    Only the transaction read sees the concurrent adjustment. No live-Spanner
    or serializability claim is derived from this fixture.
    """
    from context_graph.adapters.spanner.graph import SpannerGraphStore
    from context_graph.adapters.spanner.log import json_param, json_value

    class Transaction:
        def read(self, table, columns, keys):
            return [
                [
                    "Event",
                    "atomic-event",
                    json_param(
                        {
                            "event_id": "atomic-event",
                            "importance_score": existing,
                            "summary": "authoritative summary",
                            "access_count": 3,
                        }
                    ),
                    None,
                ]
            ]

        def insert_or_update(self, table, columns, rows):
            self.written = json_value(rows[0][2])

    class Database:
        def __init__(self):
            self.transaction = Transaction()

        def run_in_transaction(self, operation):
            return operation(self.transaction)

        def snapshot(self, **kwargs):
            raise AssertionError("An outside snapshot must not decide annotation ownership")

    database = Database()
    graph = SpannerGraphStore(database)
    await graph.update_event_enrichment("atomic-event", ["observation", "input"], 5)
    assert database.transaction.written["importance_score"] == (5 if existing is None else existing)
    assert database.transaction.written["keywords"] == ["observation", "input"]
    assert database.transaction.written["summary"] == "authoritative summary"
    assert database.transaction.written["access_count"] == 3


@pytest.mark.parametrize("embedding", [False, True])
async def test_spanner_missing_annotation_target_schedules_no_mutation(embedding):
    from context_graph.adapters.spanner.graph import SpannerGraphStore

    class Database:
        def run_in_transaction(self, operation):
            return operation(self)

        def read(self, *args):
            return []

        def insert_or_update(self, *args):
            raise AssertionError("Missing Event must not schedule partial node creation")

    graph = SpannerGraphStore(Database())
    with pytest.raises(UnavailableError):
        if embedding:
            await graph.store_event_embedding("missing", [0.25] * 384)
        else:
            await graph.update_event_enrichment("missing", ["observation"], 5)
