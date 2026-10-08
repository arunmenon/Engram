"""Authoritative ledger receipts gate processing before plans, prompts or ACK."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from context_graph.adapters.spanner.log import SpannerEventLog, json_param, json_value
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.domain.event_acceptance import (
    EventInterpretationError,
    stamp_acceptance,
    validate_accepted_document,
)
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.source_trust import SourceTrustPolicy
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.subscription import Delivery
from context_graph.settings import Settings
from context_graph.worker.enrichment import EnrichmentConsumer
from context_graph.worker.extraction import ExtractionConsumer
from context_graph.worker.pack_extraction import PackExtractionConsumer
from context_graph.worker.projection import ProjectionConsumer
from tests.unit.test_event_acceptance import context, event
from tests.unit.test_spanner_event_acceptance import setup
from tests.unit.test_worker_fences import subscription


def authority(binding=None):
    from tests.unit.test_tenant_catalog import bind

    return binding or bind()


def document(payload=None):
    return {**event().model_dump(mode="json"), "payload": payload}


def test_exact_contract_allows_epoch_advance_and_derived_enrichment():
    binding = authority()
    accepted = stamp_acceptance(context(binding), event(), {"number": -0.0})
    projected, receipt = validate_accepted_document(
        replace(binding, epoch=2),
        str(event().event_id),
        {**document({"number": -0.0}), "summary": "later summary", "keywords": ["later"]},
        accepted.model_dump(),
    )
    assert projected.event_id == event().event_id and receipt == accepted
    assert receipt.accepted_epoch == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", "foreign"),
        ("database_resource", "projects/x/instances/y/databases/z"),
        ("binding_id", "foreign"),
        ("bundle_digest", "sha256:" + "f" * 64),
        ("engine_revision", "unknown"),
        ("accepted_epoch", 2),
        ("envelope_version", 2),
    ],
)
def test_unknown_receipt_interpretations_are_rejected(field, value):
    binding = authority()
    accepted = stamp_acceptance(context(binding), event(), None).model_dump()
    accepted[field] = value
    with pytest.raises(EventInterpretationError):
        validate_accepted_document(binding, str(event().event_id), document(), accepted)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault", ["missingreceipt", "changedpayload", "wrongkey", "expiredcontent", "oldcontract"]
)
async def test_authoritative_document_fetch_refuses_malformed_or_incompatible_input(fault):
    binding, db, store = setup()
    await store.append(event(), {"x": 1}, admission_context=context(binding))
    row = db.rows[str(event().event_id)]
    if fault == "missingreceipt":
        row["acceptance"] = None
    elif fault == "changedpayload":
        doc = json_value(row["document"])
        doc["payload"]["x"] = 2
        row["document"] = json_param(doc)
    elif fault == "wrongkey":
        doc = json_value(row["document"])
        doc["event_id"] = "00000000-0000-4000-8000-000000000002"
        row["document"] = json_param(doc)
    elif fault == "expiredcontent":
        row["document"] = None
    else:
        receipt = json_value(row["acceptance"])
        receipt["bundle_digest"] = "sha256:" + "f" * 64
        row["acceptance"] = json_param(receipt)
    with pytest.raises(RuntimeFencedError):
        await store.get_documents([str(event().event_id)])
    assert sum(len(tx.effects) for tx in db.transactions) == 1


@pytest.mark.asyncio
async def test_missing_processing_row_refuses_but_missing_api_read_is_absent():
    binding, db, store = setup()
    assert await store.get_documents([str(event().event_id)]) == [None]
    processing = SpannerEventLog(
        db,
        tenant_fence=TenantFence.from_binding(binding),
        tenant_engine_revision=binding.engine_revision,
        tenant_read_operation="processing",
    )
    with pytest.raises(RuntimeFencedError):
        await processing.get_documents([str(event().event_id)])


@pytest.mark.asyncio
async def test_receipt_returned_from_column_survives_epoch_only_restart():
    binding, db, store = setup()
    payload = {"number": 1.0}
    await store.append(event(), payload, admission_context=context(binding))
    advanced = replace(binding, epoch=2)
    db.owner[3] = 2
    recovered = SpannerEventLog(
        db,
        tenant_fence=TenantFence.from_binding(advanced),
        tenant_engine_revision=advanced.engine_revision,
        tenant_read_operation="processing",
    )
    (doc,) = await recovered.get_documents([str(event().event_id)])
    assert doc["acceptance"] == stamp_acceptance(context(binding), event(), payload).model_dump()
    assert doc["payload"] == payload and doc["global_position"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind", ["projection", "enrichment", "extraction", "pack_extraction", "no_profiles"]
)
async def test_actual_consumer_loop_stops_without_plan_prompt_ack_or_dlq_on_bad_receipt(kind):
    binding, db, ledger = setup()
    await ledger.append(
        event(), {"content": "do not interpret"}, admission_context=context(binding)
    )
    db.rows[str(event().event_id)]["acceptance"] = None
    port = subscription()
    port.read_new.return_value = [
        Delivery("position", {"event_id": str(event().event_id), "event_type": "spoofed"})
    ]
    settings = Settings()
    settings.consumer.projection_batch_size = 1
    graph, model = AsyncMock(), AsyncMock()
    projector = PackProjector(
        binding.bundle.registry, frozenset(), source_policy=SourceTrustPolicy.from_binding(binding)
    )
    projector.plan = MagicMock(wraps=projector.plan)
    profile = MagicMock()
    profile.handles.side_effect = lambda kind: kind == "tool.execute"
    if kind == "projection":
        consumer = ProjectionConsumer(port, ledger, graph, settings, projector)
    elif kind == "enrichment":
        consumer = EnrichmentConsumer(port, ledger, graph, settings, model)
    elif kind == "extraction":
        consumer = ExtractionConsumer(port, ledger, model, settings, graph_store=graph)
    else:
        consumer = PackExtractionConsumer(
            port,
            ledger,
            graph,
            [] if kind == "no_profiles" else [profile],
            projector,
            model,
            settings,
        )
    with pytest.raises(RuntimeFencedError):
        await asyncio.wait_for(consumer.run(), 1)
    assert consumer._stopped
    port.ack.assert_not_awaited()
    port.dead_letter.assert_not_awaited()
    assert not graph.mock_calls and not model.mock_calls
    projector.plan.assert_not_called()


@pytest.mark.asyncio
async def test_pack_extractor_selects_actual_event_type_not_delivery_hint():
    binding, _, ledger = setup()
    await ledger.append(event(), {"content": "actual"}, admission_context=context(binding))
    profile = MagicMock()
    profile.handles.side_effect = lambda kind: kind == "tool.execute"
    consumer = PackExtractionConsumer(
        subscription(),
        ledger,
        AsyncMock(),
        [profile],
        PackProjector(
            binding.bundle.registry,
            frozenset(),
            source_policy=SourceTrustPolicy.from_binding(binding),
        ),
        AsyncMock(),
        Settings(),
    )
    consumer._extract = AsyncMock()
    await consumer.process_message(
        "position", {"event_id": str(event().event_id), "event_type": "unhandled-hint"}
    )
    consumer._extract.assert_awaited_once()
    assert consumer._extract.await_args.args[1].event_type == "tool.execute"


@pytest.mark.asyncio
async def test_mixed_contract_session_refuses_before_extraction_instead_of_skipping_history():
    binding, db, ledger = setup()
    second = event().model_copy(update={"event_id": UUID("00000000-0000-4000-8000-000000000002")})
    await ledger.append_batch(
        [event(), second],
        [{"content": "one"}, {"content": "two"}],
        admission_context=context(binding),
    )
    bad = json_value(db.rows[str(second.event_id)]["acceptance"])
    bad["engine_revision"] = "unknown-history"
    db.rows[str(second.event_id)]["acceptance"] = json_param(bad)
    ledger.read_session_ids = AsyncMock(return_value=[str(event().event_id), str(second.event_id)])
    model = AsyncMock()
    consumer = ExtractionConsumer(subscription(), ledger, model, Settings())
    with pytest.raises(RuntimeFencedError):
        await consumer._collect_session_events(event().session_id)
    assert not model.mock_calls


@pytest.mark.asyncio
@pytest.mark.parametrize("reader", ["replay", "sessionsearch", "bm25"])
async def test_all_document_sql_readers_check_receipt(reader):
    binding, _, ledger = setup()
    row = [document(), datetime(2026, 1, 1, tzinfo=UTC), 0, str(event().event_id)]
    if reader == "bm25":
        row.append(0.9)
    row.append(None)
    ledger._query = AsyncMock(return_value=[row])
    with pytest.raises(RuntimeFencedError):
        if reader == "replay":
            await ledger.read_after(None, 10)
        elif reader == "sessionsearch":
            await ledger.get_by_session(event().session_id)
        else:
            await ledger.search_scored("query")


@pytest.mark.asyncio
@pytest.mark.parametrize("valid", [True, False])
async def test_archive_preserves_receipt_or_refuses_before_archive_and_delete(valid):
    binding, _, ledger = setup()
    accepted = stamp_acceptance(context(binding), event(), {"x": -0.0}).model_dump()
    ledger._query = AsyncMock(
        return_value=[
            [
                document({"x": -0.0}),
                datetime(2026, 1, 1, tzinfo=UTC),
                0,
                str(event().event_id),
                1,
                accepted if valid else None,
            ]
        ]
    )
    ledger._execute_updates = AsyncMock(return_value=[1])
    ledger._purge = AsyncMock()
    archive = AsyncMock()
    if valid:
        assert await ledger.expire(1, archive) == (1, 1)
        exported = archive.archive_events.await_args.args[0][0]
        assert exported["acceptance"] == accepted and exported["payload"] == {"x": -0.0}
        ledger._execute_updates.assert_awaited_once()
    else:
        with pytest.raises(RuntimeFencedError):
            await ledger.expire(1, archive)
        archive.archive_events.assert_not_awaited()
        ledger._execute_updates.assert_not_awaited()


@pytest.mark.asyncio
async def test_bound_enrichment_refuses_unknown_existing_receipt_before_write():
    binding, db, ledger = setup()
    await ledger.append(event(), admission_context=context(binding))
    db.rows[str(event().event_id)]["acceptance"] = None
    with pytest.raises(RuntimeFencedError):
        await ledger.set_document_fields(str(event().event_id), summary="must not write")
    assert not db.transactions[-1].effects
