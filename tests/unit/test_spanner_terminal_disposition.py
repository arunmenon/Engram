"""Bound terminal transactions retain pending events on interpretation refusal."""

import asyncio
import copy
from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from context_graph.adapters.spanner.log import (
    SpannerEventLog,
    format_position,
    json_param,
    json_value,
)
from context_graph.adapters.spanner.subscription import SpannerSubscription
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.subscription import Delivery
from context_graph.worker.consumer import BaseConsumer
from tests.unit.test_event_acceptance import context, event
from tests.unit.test_spanner_event_acceptance import Database, Transaction
from tests.unit.test_tenant_catalog import bind
from tests.unit.test_worker_fences import subscription


class DispositionTransaction(Transaction):
    def __init__(self, db):
        super().__init__(db)
        self.pending = copy.deepcopy(db.pending)
        self.dlq = copy.deepcopy(db.dlq)
        self.reads = []

    def read(self, table, columns, keys):
        self.reads.append(table)
        source = {"ConsumerDeliveries": self.pending, "ConsumerDeadLetters": self.dlq}.get(table)
        if source is None:
            return super().read(table, columns, keys)
        return [
            [source[tuple(key)][c] for c in columns] for key in keys.keys if tuple(key) in source
        ]

    def delete(self, table, keys):
        assert table == "ConsumerDeliveries"
        self.effects.append(("delete", copy.deepcopy(keys.keys)))
        for key in keys.keys:
            self.pending.pop(tuple(key), None)

    def insert_or_update(self, table, columns, rows):
        if table == "Events":
            return super().insert_or_update(table, columns, rows)
        assert table == "ConsumerDeadLetters"
        self.effects.append(("dead_letter", copy.deepcopy(rows)))
        for row in rows:
            data = dict(zip(columns, row, strict=True))
            self.dlq[(data["group_name"], data["event_id"])] = data


class DispositionDatabase(Database):
    def __init__(self, binding):
        super().__init__(binding)
        self.pending, self.dlq = {}, {}
        self.retry_change = None

    def run_in_transaction(self, callback):
        transaction = DispositionTransaction(self)
        self.transactions.append(transaction)
        result = callback(transaction)
        if self.retry_change is not None:
            change, self.retry_change = self.retry_change, None
            change(self)
            return self.run_in_transaction(callback)
        self.rows, self.pending, self.dlq = transaction.rows, transaction.pending, transaction.dlq
        return result


async def setup():
    binding = bind()
    db = DispositionDatabase(binding)
    log = SpannerEventLog(
        db,
        tenant_fence=TenantFence.from_binding(binding),
        tenant_engine_revision=binding.engine_revision,
        tenant_binding=binding,
    )
    position = await log.append(
        event(), {"content": "original"}, admission_context=context(binding)
    )
    row = db.rows[str(event().event_id)]
    key = ("group", str(event().event_id))
    db.pending[key] = {
        "consumer": "worker",
        "commit_ts": row["commit_ts"],
        "batch_index": row["batch_index"],
        "delivery_count": 1,
    }
    port = SpannerSubscription(
        db,
        "group",
        "worker",
        tenant_fence=TenantFence.from_binding(binding),
        tenant_engine_revision=binding.engine_revision,
    )
    db.transactions.clear()
    return binding, db, log, port, Delivery(position, {"event_id": key[1]}), key


def break_content(db, fault):
    row = db.rows[str(event().event_id)]
    if fault == "missing_event":
        db.rows.clear()
    elif fault == "missing_document":
        row["document"] = None
    elif fault == "missing_receipt":
        row["acceptance"] = None
    elif fault == "payload":
        doc = json_value(row["document"])
        doc["payload"]["content"] = "changed"
        row["document"] = json_param(doc)
    else:
        receipt = json_value(row["acceptance"])
        field, value = {
            "foreign": ("tenant_id", "foreign"),
            "future": ("accepted_epoch", 2),
            "contract": ("engine_revision", "unknown"),
            "bundle": ("bundle_digest", "sha256:" + "f" * 64),
        }[fault]
        receipt[field] = value
        row["acceptance"] = json_param(receipt)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["ack", "dlq"])
@pytest.mark.parametrize(
    "fault",
    [
        "missing_event",
        "missing_document",
        "missing_receipt",
        "payload",
        "foreign",
        "future",
        "contract",
        "bundle",
    ],
)
async def test_bad_content_refuses_terminal_mutations_in_control_checked_transaction(
    operation, fault
):
    _, db, _, port, delivery, _ = await setup()
    break_content(db, fault)
    before = copy.deepcopy((db.rows, db.pending, db.dlq))
    with pytest.raises(RuntimeFencedError):
        if operation == "ack":
            await port.ack(delivery.position)
        else:
            await port.dead_letter(delivery, 7)
    assert (db.rows, db.pending, db.dlq) == before
    assert db.transactions[-1].reads == ["TenantControl", "ConsumerDeliveries", "Events"]
    assert db.transactions[-1].effects == []


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["ack", "dlq"])
@pytest.mark.parametrize("fault", ["consumer", "delivery_position", "ledger_position"])
async def test_position_and_consumer_must_match(operation, fault):
    _, db, _, port, delivery, key = await setup()
    if fault == "consumer":
        db.pending[key]["consumer"] = "another-worker"
    elif fault == "delivery_position":
        db.pending[key]["batch_index"] += 1
    else:
        db.rows[key[1]]["batch_index"] += 1
    with pytest.raises(RuntimeFencedError):
        if operation == "ack":
            await port.ack(delivery.position)
        else:
            await port.dead_letter(delivery, 7)
    assert key in db.pending and not db.dlq and not db.transactions[-1].effects


@pytest.mark.asyncio
async def test_batch_ack_validates_all_before_deleting_and_rejects_contradictory_positions():
    binding, db, log, port, delivery, key = await setup()
    second = event().model_copy(update={"event_id": UUID("00000000-0000-4000-8000-000000000002")})
    position = await log.append(second, admission_context=context(binding))
    second_key = ("group", str(second.event_id))
    db.pending[second_key] = copy.deepcopy(db.pending[key])
    db.rows[second_key[1]]["acceptance"] = None
    with pytest.raises(RuntimeFencedError):
        await port.ack(delivery.position, position)
    assert set(db.pending) == {key, second_key} and not db.transactions[-1].effects
    timestamp = db.rows[key[1]]["commit_ts"]
    with pytest.raises(RuntimeFencedError):
        await port.ack(delivery.position, format_position(timestamp, 1, key[1]))
    assert not db.transactions[-1].effects


@pytest.mark.asyncio
async def test_valid_old_epoch_enrichment_and_ack_repeat_after_content_expiry():
    binding, db, _, _, delivery, key = await setup()
    advanced = replace(binding, epoch=2)
    db.owner[3], db.owner[-1] = 2, "draining"
    doc = json_value(db.rows[key[1]]["document"])
    doc["summary"], doc["keywords"] = "derived", ["derived"]
    db.rows[key[1]]["document"] = json_param(doc)
    port = SpannerSubscription(
        db,
        "group",
        "worker",
        tenant_fence=TenantFence.from_binding(advanced),
        tenant_engine_revision=advanced.engine_revision,
    )
    await port.ack(delivery.position, delivery.position)
    assert not db.pending and not db.dlq
    db.rows.clear()
    await port.ack(delivery.position)
    assert db.transactions[-1].reads == ["TenantControl", "ConsumerDeliveries"]


@pytest.mark.asyncio
async def test_dlq_uses_authoritative_fields_and_matching_repeat_only():
    _, db, _, port, delivery, key = await setup()
    original = copy.deepcopy(db.rows)
    spoofed = Delivery(
        delivery.position,
        {
            **delivery.fields,
            "consumer": "spoofed",
            "group": "foreign",
            "original_entry_id": "forged",
            "acceptance": "forged",
            "event_type": "forged",
        },
    )
    await port.dead_letter(spoofed, 7)
    fields = json_value(db.dlq[key]["fields"])
    assert fields["consumer"] == "worker" and fields["group"] == "group"
    assert fields["original_entry_id"] == delivery.position
    assert fields["event_type"] == event().event_type
    assert fields["acceptance"] != "forged" and fields["delivery_count"] == "7"
    assert db.rows == original and not db.pending
    before = copy.deepcopy(db.dlq)
    db.rows.clear()  # Completed matching disposition does not resurrect expired content.
    await port.dead_letter(delivery, 9)
    assert db.dlq == before and not db.transactions[-1].effects
    fields["binding_id"] = "foreign"
    db.dlq[key]["fields"] = json_param(fields)
    with pytest.raises(RuntimeFencedError):
        await port.dead_letter(delivery, 9)


@pytest.mark.asyncio
async def test_dlq_without_pending_or_with_conflicting_event_hint_refuses():
    _, db, _, port, delivery, _ = await setup()
    with pytest.raises(RuntimeFencedError):
        await port.dead_letter(Delivery(delivery.position, {"event_id": "foreign"}), 7)
    assert db.pending and not db.dlq
    db.pending.clear()
    with pytest.raises(RuntimeFencedError):
        await port.dead_letter(delivery, 7)
    assert not db.dlq


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["payload", "missing_document", "frozen"])
async def test_transaction_retry_revalidates_content_and_control(fault):
    _, db, log, port, delivery, key = await setup()
    assert (await log.get_documents([key[1]]))[0]  # Successful earlier processing read.

    def change(database):
        if fault == "frozen":
            database.owner[-1] = "frozen"
        else:
            break_content(database, fault)

    db.retry_change = change
    with pytest.raises(RuntimeFencedError):
        await port.ack(delivery.position)
    assert key in db.pending and not db.dlq
    assert db.transactions[-1].reads[0] == "TenantControl"


@pytest.mark.asyncio
async def test_exhausted_pending_control_refusal_stops_without_processing_or_disposition():
    _, db, _, actual, delivery, key = await setup()
    break_content(db, "contract")
    port = subscription()
    port.read_pending.return_value = [delivery]
    port.delivery_counts.return_value = {delivery.position: 7}
    port.dead_letter.side_effect = actual.dead_letter
    consumer = BaseConsumer(port)
    consumer.process_message = AsyncMock()
    with pytest.raises(RuntimeFencedError):
        await asyncio.wait_for(consumer.run(), 1)
    assert consumer._stopped and key in db.pending and not db.dlq
    consumer.process_message.assert_not_awaited()
    port.ack.assert_not_awaited()


def test_bound_subscription_requires_pinned_engine_revision():
    binding = bind()
    with pytest.raises(ValueError, match="engine revision"):
        SpannerSubscription(
            DispositionDatabase(binding),
            "group",
            "worker",
            tenant_fence=TenantFence.from_binding(binding),
        )
