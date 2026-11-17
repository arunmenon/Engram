"""Bounded real-ledger/real-consumer refusal and pending-recovery experiment."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from engram_spanner_acceptance_cases import assert_owned, await_settled
from engram_spanner_tenant_control_cases import read_owner
from engram_spanner_tenant_runtime_cases import runtime_settings
from google.cloud.spanner_v1 import KeySet, param_types

from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.adapters.spanner.log import SpannerEventLog, json_param, json_value
from context_graph.adapters.spanner.subscription import SpannerSubscription
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.domain.models import Event
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.source_trust import SourceTrustPolicy
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.subscription import Delivery
from context_graph.tenancy import Principal, TenantBinding
from context_graph.worker.enrichment import EnrichmentConsumer
from context_graph.worker.extraction import ExtractionConsumer
from context_graph.worker.pack_extraction import PackExtractionConsumer
from context_graph.worker.projection import ProjectionConsumer


class ForbiddenProvider:
    """Explicit no-inference assertion; graph and ledger adapters remain real."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        self.calls.append(name)
        raise AssertionError("Invalid receipt reached provider")


class StopAfterAck(PackExtractionConsumer):
    async def _ack(self, *positions):
        await super()._ack(*positions)
        self.stop()


class ExhaustedConsumer(PackExtractionConsumer):
    """An exhausted-retry proof must never enter normal event processing."""

    processing_calls = 0

    async def process_message(self, entry_id, data):
        self.processing_calls += 1
        raise AssertionError("Exhausted delivery reached normal processing")


async def verify_interpretation(
    database, values, run_id, evidence, checks, fingerprint, persist, *, terminal=False
):
    try:
        await await_settled(
            _verify(database, values, run_id, evidence, checks, fingerprint, persist, terminal)
        )
    except asyncio.CancelledError:
        checks.append(
            {"name": "interpretation_cancelled_after_cleanup", "passed": False, "scenarios": []}
        )
        persist(evidence)
        raise


async def verify_terminal_disposition(
    database, values, run_id, evidence, checks, fingerprint, persist
):
    await verify_interpretation(
        database, values, run_id, evidence, checks, fingerprint, persist, terminal=True
    )


async def _verify(database, values, run_id, evidence, checks, fingerprint, persist, terminal=False):
    before = await asyncio.to_thread(fingerprint, database)
    assert not any(row["count"] for row in before.values()), "Reserved target must be empty"
    settings = runtime_settings(values)
    owner = await asyncio.to_thread(read_owner, database)
    assert len(owner) == 1 and owner[0][-1] == "active"
    binding = TenantBinding.from_settings(
        "compat-control",
        "compat-control-binding",
        owner[0][3],
        settings,
        engine_revision="tenant-control-conformance-v1",
    )
    assert_owned(owner[0], binding, {binding.epoch})
    fence = TenantFence.from_binding(binding)
    ledger = SpannerEventLog(
        database,
        tenant_fence=fence,
        tenant_engine_revision=binding.engine_revision,
        tenant_read_operation="processing",
        tenant_binding=binding,
    )
    graph = SpannerGraphStore(database, tenant_fence=fence)
    projector = PackProjector(
        binding.bundle.registry, frozenset(), source_policy=SourceTrustPolicy.from_binding(binding)
    )
    provider = ForbiddenProvider()
    event_uuid = uuid5(NAMESPACE_URL, run_id + "/interpretation")
    event_id = str(event_uuid)
    event = Event(
        event_id=event_uuid,
        event_type="tool.execute",
        occurred_at=datetime.now(UTC),
        session_id=run_id,
        agent_id="compat-control",
        trace_id=run_id,
        payload_ref="fixture:" + event_id,
    )
    kinds = ("projection", "enrichment", "extraction", "pack_extraction")
    faults = ("missing_receipt", "old_contract", "changed_payload")
    groups = [run_id + "/" + fault + "/" + kind for fault in faults for kind in kinds]
    terminal_faults = (*faults, "missing_document") if terminal else ()
    groups.extend(run_id + "/terminal/" + fault for fault in terminal_faults)
    evidence["interpretation_intent"] = {
        "owner": owner,
        "event_ids": [event_id],
        "groups": groups,
        "faults": list(faults),
        "terminal_faults": list(terminal_faults),
        "workers": list(kinds),
        "pack_profiles": [],
        "provider": "ForbiddenProvider; any access fails",
        "recovery": "Restore original row then actual empty-profile consumer ACKs pending event",
        "cleanup": "Exact owned event and group keys only; no DDL or owner transition",
    }
    persist(evidence)

    def record(name):
        checks.append({"name": name, "passed": True, "scenarios": []})
        persist(evidence)

    async def rewrite(receipt, document):
        def write(transaction):
            transaction.update(
                "Events",
                ["event_id", "acceptance", "document"],
                [[event_id, json_param(receipt), json_param(document)]],
            )

        await asyncio.to_thread(fence.run, database, write, operation="processing")

    async def counts(group):
        result = {}
        for table in ("ConsumerDeliveries", "ConsumerDeadLetters"):
            rows = await ledger._query(
                f"SELECT COUNT(*) FROM {table} WHERE group_name = @group",
                {"group": group},
                {"group": param_types.STRING},
            )
            result[table] = rows[0][0]
        return result

    async def run_bounded(consumer):
        timer = asyncio.get_running_loop().call_later(30, consumer.stop)
        try:
            await consumer.run()
        finally:
            timer.cancel()

    try:
        principal = Principal("fixture", binding.tenant_id, frozenset({"api"}), "fixture")
        await ledger.append(
            event,
            {"content": "owned original"},
            admission_context=binding.admission_context(principal),
        )
        row = (
            await ledger._query(
                "SELECT acceptance, document FROM Events WHERE event_id = @id",
                {"id": event_id},
                {"id": param_types.STRING},
            )
        )[0]
        receipt, original = map(json_value, row)
        settings.consumer.projection_batch_size = 1
        settings.consumer.block_timeout_ms = 50
        for fault in faults:
            broken_receipt, broken_document = deepcopy(receipt), deepcopy(original)
            if fault == "missing_receipt":
                broken_receipt = None
            elif fault == "old_contract":
                broken_receipt["engine_revision"] = "unknown-contract"
            else:
                broken_document["payload"]["content"] = "tampered"
            for kind in kinds:
                group = run_id + "/" + fault + "/" + kind
                evidence["current_fault_intent"] = {"fault": fault, "group": group}
                persist(evidence)
                await rewrite(broken_receipt, broken_document)
                subscription = SpannerSubscription(
                    database,
                    group,
                    "owned-consumer",
                    tenant_fence=fence,
                    tenant_engine_revision=binding.engine_revision,
                    tenant_read_operation="processing",
                    poll_interval_ms=10,
                )
                if kind == "projection":
                    consumer = ProjectionConsumer(subscription, ledger, graph, settings, projector)
                elif kind == "enrichment":
                    consumer = EnrichmentConsumer(subscription, ledger, graph, settings)
                elif kind == "extraction":
                    consumer = ExtractionConsumer(
                        subscription,
                        ledger,
                        provider,
                        settings,
                        graph_store=graph,
                        bundle=binding.bundle,
                    )
                else:
                    consumer = PackExtractionConsumer(
                        subscription,
                        ledger,
                        graph,
                        [],
                        projector,
                        provider,
                        settings,
                    )
                try:
                    await run_bounded(consumer)
                except RuntimeFencedError:
                    pass
                else:
                    raise AssertionError("Invalid receipt did not stop consumer")
                assert consumer._stopped and not provider.calls
                assert await counts(group) == {
                    "ConsumerDeliveries": 1,
                    "ConsumerDeadLetters": 0,
                }
                current = await asyncio.to_thread(fingerprint, database)
                assert current["GraphNodes"] == before["GraphNodes"]
                assert current["GraphEdges"] == before["GraphEdges"]
                record(f"{fault}_{kind}_stops_pending_no_dlq_no_graph_or_provider")
                await rewrite(receipt, original)
                recovery = StopAfterAck(
                    subscription,
                    ledger,
                    graph,
                    [],
                    projector,
                    provider,
                    settings,
                )
                await run_bounded(recovery)
                assert await counts(group) == {
                    "ConsumerDeliveries": 0,
                    "ConsumerDeadLetters": 0,
                }
                record(f"{fault}_{kind}_restored_authority_recovery_acks_pending")
        for fault in terminal_faults:
            group = run_id + "/terminal/" + fault
            evidence["current_terminal_intent"] = {
                "fault": fault,
                "group": group,
                "delivery_count": 7,
                "dispositions": [
                    "ACK refusal",
                    "DLQ refusal",
                    "exhausted retry refusal",
                    "restored valid DLQ",
                    "repeat DLQ/ACK",
                ],
            }
            persist(evidence)
            await rewrite(receipt, original)
            assert (await ledger.get_documents([event_id]))[
                0
            ]  # Earlier successful processing read.
            subscription = SpannerSubscription(
                database,
                group,
                "owned-consumer",
                tenant_fence=fence,
                tenant_engine_revision=binding.engine_revision,
                tenant_read_operation="processing",
                poll_interval_ms=10,
            )
            await subscription.ensure_group()
            (delivery,) = await subscription.read_new(1, 0)
            broken_receipt, broken_document = deepcopy(receipt), deepcopy(original)
            if fault == "missing_receipt":
                broken_receipt = None
            elif fault == "old_contract":
                broken_receipt["engine_revision"] = "unknown-contract"
            elif fault == "missing_document":
                broken_document = None
            else:
                broken_document["payload"]["content"] = "changed after processing read"
            await rewrite(broken_receipt, broken_document)

            def exhaust(transaction, owned_group=group):
                transaction.execute_update(
                    "UPDATE ConsumerDeliveries SET delivery_count = 7 "
                    "WHERE group_name = @group AND event_id = @id",
                    params={"group": owned_group, "id": event_id},
                    param_types={"group": param_types.STRING, "id": param_types.STRING},
                )

            await asyncio.to_thread(fence.run, database, exhaust, operation="processing")

            async def refuses(name, operation, owned_group=group):
                try:
                    await operation()
                except RuntimeFencedError:
                    pass
                else:
                    raise AssertionError(name + " unexpectedly succeeded")
                assert await counts(owned_group) == {
                    "ConsumerDeliveries": 1,
                    "ConsumerDeadLetters": 0,
                }
                record(name)

            await refuses(
                f"terminal_{fault}_ack_refuses_after_processing_read",
                lambda port=subscription, item=delivery: port.ack(item.position),
            )
            await refuses(
                f"terminal_{fault}_dlq_refuses_after_processing_read",
                lambda port=subscription, item=delivery: port.dead_letter(item, 7),
            )
            consumer = ExhaustedConsumer(
                subscription,
                ledger,
                graph,
                [],
                projector,
                provider,
                settings,
            )
            assert (await subscription.delivery_counts(1))[
                delivery.position
            ] > consumer._max_retries, "Fixture must exceed actual consumer retry threshold"
            await refuses(
                f"terminal_{fault}_exhausted_retry_stops_pending",
                lambda worker=consumer: run_bounded(worker),
            )
            assert consumer._stopped and consumer.processing_calls == 0 and not provider.calls
            record(f"terminal_{fault}_exhausted_branch_never_enters_processing")
            await rewrite(receipt, original)
            spoofed = Delivery(
                delivery.position,
                {
                    **delivery.fields,
                    "consumer": "spoofed",
                    "original_entry_id": "forged",
                    "acceptance": "forged",
                },
            )
            await subscription.dead_letter(spoofed, 9)
            assert await counts(group) == {"ConsumerDeliveries": 0, "ConsumerDeadLetters": 1}
            (dead_letter,) = await subscription.dead_letters()
            assert dead_letter["consumer"] == "owned-consumer"
            assert dead_letter["original_entry_id"] == delivery.position
            assert json.loads(dead_letter["acceptance"]) == receipt
            assert dead_letter["binding_id"] == binding.binding_id
            record(f"terminal_{fault}_restored_dlq_uses_authoritative_metadata")
            await subscription.dead_letter(delivery, 10)
            await subscription.ack(delivery.position)
            assert await subscription.dead_letters() == [dead_letter]
            record(f"terminal_{fault}_repeated_dlq_and_ack_are_idempotent")
        assert not provider.calls
        record("no_provider_access_across_all_faults_and_recovery")
    finally:
        rows = await asyncio.to_thread(read_owner, database)
        assert len(rows) == 1
        assert_owned(rows[0], binding, {binding.epoch})
        assert rows[0][-1] == "active"
        evidence["cleanup_intent"] = {"event_ids": [event_id], "groups": groups}
        persist(evidence)

        def clean(transaction):
            transaction.delete("Events", KeySet(keys=[[event_id]]))
            for group in groups:
                for table in (
                    "ConsumerDeliveries",
                    "ConsumerDeadLetters",
                    "ConsumerCursors",
                    "ConsumerGroups",
                ):
                    transaction.execute_update(
                        f"DELETE FROM {table} WHERE group_name = @group",
                        params={"group": group},
                        param_types={"group": param_types.STRING},
                    )

        await asyncio.to_thread(fence.run, database, clean, operation="processing")
        assert await asyncio.to_thread(fingerprint, database) == before
        assert await asyncio.to_thread(read_owner, database) == owner
        record("exact_fixture_cleanup_all_application_rows_and_owner_preserved")
