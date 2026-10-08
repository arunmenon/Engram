"""Bounded real-adapter fence tests; test-only operator state transitions.

Not a production activation implementation or API/worker-process journey.
Control ownership persists, epochs never decrease, exact synthetic rows removed.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from google.cloud.spanner_v1 import KeySet, param_types

from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.adapters.spanner.log import SpannerEventLog
from context_graph.adapters.spanner.subscription import SpannerSubscription
from context_graph.adapters.spanner.tenant_control import TenantFence, TenantFenceError
from context_graph.domain.models import Event
from context_graph.ports.pack_graph import EdgeWrite, NodeRef, NodeWrite
from context_graph.settings import Settings
from context_graph.tenancy import Principal, TenantBinding

COLUMNS = [
    "tenant_id",
    "database_resource",
    "binding_id",
    "epoch",
    "bundle_digest",
    "serving_state",
]


def read_owner(database):
    with database.snapshot() as snapshot:
        return [
            list(row) for row in snapshot.read("TenantControl", COLUMNS, KeySet(keys=[["active"]]))
        ]


def operator_transition(database, expected, *, state, advance=False):
    """Harness-only CAS, not a public activation API or adoption shortcut."""
    assert state in ("active", "draining", "frozen")
    if expected[-1] == "frozen" and state == "active":
        assert advance, "Never reactivate the same frozen epoch"

    def work(transaction):
        rows = list(transaction.read("TenantControl", COLUMNS, KeySet(keys=[["active"]])))
        assert len(rows) == 1 and list(rows[0]) == expected, "Owner changed during experiment"
        updated = [*expected[:-1], state]
        if advance:
            updated[3] += 1
        transaction.update("TenantControl", ["control_id", *COLUMNS], [["active", *updated]])
        return updated

    return database.run_in_transaction(work)


async def verify_fences(database, values, run_id, evidence, checks, fingerprint, persist):
    settings = Settings()
    for port in ("event_log", "subscription", "graph", "keyword_index", "vector_index"):
        setattr(settings.storage, port, "spanner")
    settings.spanner.project = values["GOOGLE_CLOUD_PROJECT"]
    settings.spanner.instance = values["SPANNER_INSTANCE_ID"]
    settings.spanner.database = "engram-compat-target"
    settings.spanner.emulator_host = None
    settings.spanner.check_schema = True
    settings.spanner.create_if_missing = False
    settings.spanner.allow_create_on_instance = False
    settings.archive.enabled = False
    settings.ontology.packs = []
    settings.ontology.builtin_packs = []
    owner = await asyncio.to_thread(read_owner, database)
    epoch = owner[0][3] if owner else 1
    binding = TenantBinding.from_settings(
        "compat-control",
        "compat-control-binding",
        epoch,
        settings,
        engine_revision="tenant-control-conformance-v1",
    )
    fence = TenantFence.from_binding(binding)
    event_ids = [uuid5(NAMESPACE_URL, run_id + suffix) for suffix in ("/a", "/b", "/rejected")]
    group = "tenant-control-" + uuid5(NAMESPACE_URL, run_id).hex
    entity_id = "entity-" + group
    event_ref = NodeRef("Event", str(event_ids[0]), "event_id")
    entity_ref = NodeRef("Entity", entity_id, "entity_id")
    evidence["fixture"] = {
        "event_ids": list(map(str, event_ids)),
        "group": group,
        "entity_id": entity_id,
        "max_events": 2,
        "max_nodes": 2,
        "max_edges": 1,
    }
    evidence["control_intent"] = {
        "tenant_id": fence.tenant_id,
        "database_resource": fence.database_resource,
        "binding_id": fence.binding_id,
        "epoch": fence.epoch,
        "bundle_digest": fence.bundle_digest,
        "bootstrap_adopt_existing": False,
        "observed_owner_before_bootstrap": owner,
    }
    persist(evidence)  # Recovery identity/keys must exist before bootstrap or fixture effects.
    # No populated-DB adoption: explicit bootstrap refuses existing application data.
    await asyncio.to_thread(fence.bootstrap, database)
    evidence["control_before"] = await asyncio.to_thread(read_owner, database)
    persist(evidence)
    ledger = SpannerEventLog(
        database,
        tenant_fence=fence,
        tenant_read_operation="processing",
        tenant_engine_revision=binding.engine_revision,
        tenant_binding=binding,
    ).admission_writer(
        binding.admission_context(
            Principal("control-fixture", binding.tenant_id, frozenset({"api"}), "control-fixture")
        )
    )
    graph = SpannerGraphStore(database, tenant_fence=fence, tenant_read_operation="processing")
    subscription = SpannerSubscription(
        database,
        group,
        "control-worker",
        tenant_fence=fence,
        tenant_read_operation="processing",
        tenant_engine_revision=binding.engine_revision,
    )

    def record(name):
        checks.append({"name": name, "passed": True, "scenarios": []})
        evidence["completed_case_checks"] = [check["name"] for check in checks]
        persist(evidence)

    async def transition(row, *, state, advance=False):
        evidence["control_transition_intent"] = {
            "expected": row,
            "next_state": state,
            "advance_epoch": advance,
        }
        persist(evidence)
        updated = await asyncio.to_thread(
            operator_transition, database, row, state=state, advance=advance
        )
        evidence["control_current"] = updated
        persist(evidence)
        return updated

    async def refused(name, operation):
        try:
            await operation()
        except TenantFenceError:
            record(name)
        else:
            raise AssertionError(name + " was unexpectedly accepted")

    async def read_paths(prefix, *, external=False, expect_refusal=False):
        mode = "read" if external else "processing"
        reader_graph = SpannerGraphStore(database, tenant_fence=fence, tenant_read_operation=mode)
        reader_log = SpannerEventLog(
            database,
            tenant_fence=fence,
            tenant_read_operation=mode,
            tenant_engine_revision=binding.engine_revision,
            tenant_binding=binding,
        )
        reader_sub = SpannerSubscription(
            database,
            group,
            "control-worker",
            tenant_fence=fence,
            tenant_read_operation=mode,
            tenant_engine_revision=binding.engine_revision,
        )
        paths = {
            "graph_query": lambda: reader_graph._query("SELECT COUNT(*) FROM GraphNodes"),
            "graph_read": lambda: reader_graph._read(
                "GraphNodes", ["label", "node_id"], KeySet(keys=[[event_ref.label, event_ref.key]])
            ),
            "ledger_query": lambda: reader_log._query("SELECT COUNT(*) FROM Events"),
            "ledger_documents": lambda: reader_log.get_documents([str(event_ids[0])]),
            "subscription_counts": lambda: reader_sub.delivery_counts(100),
            "subscription_dead_letters": reader_sub.dead_letters,
            "subscription_lag": reader_sub.lag,
        }
        for name, operation in paths.items():
            if expect_refusal:
                await refused(prefix + "_" + name, operation)
            else:
                result = await operation()
                if name in ("graph_query", "ledger_query"):
                    assert type(result[0][0]) is int and result[0][0] >= 2
                elif name == "graph_read":
                    assert result == [[event_ref.label, event_ref.key]]
                elif name == "ledger_documents":
                    assert len(result) == 1 and result[0]["event_id"] == str(event_ids[0])
                    assert result[0]["payload"]["fixture"] == group
                elif name == "subscription_counts":
                    expected_ids = event_ids[:2] if prefix.startswith("active") else event_ids[1:2]
                    expected_positions = {
                        positions[event_ids.index(event_id)] for event_id in expected_ids
                    }
                    assert set(result) == expected_positions and all(
                        value == 1 for value in result.values()
                    )
                elif name == "subscription_dead_letters":
                    assert result == []
                elif name == "subscription_lag":
                    assert type(result) is int and result == 0
                else:
                    raise AssertionError("Missing oracle for read path")
                evidence.setdefault("read_results", {})[prefix + "_" + name] = result
                record(prefix + "_" + name)

    events = [
        Event(
            event_id=event_id,
            event_type="tool.execute",
            occurred_at=datetime.now(UTC),
            session_id=group,
            agent_id="compat-control",
            trace_id=group,
            payload_ref="fixture:" + str(event_id),
        )
        for event_id in event_ids
    ]
    delayed_task = None
    try:
        positions = await ledger.append_batch(events[:2], [{"fixture": group}] * 2)
        await graph.upsert_nodes(
            [
                NodeWrite(event_ref, {"session_id": group}),
                NodeWrite(entity_ref, {"name": "control fixture"}),
            ]
        )
        assert await graph.upsert_edges([EdgeWrite("REFERENCES", event_ref, entity_ref)]) == 1
        observed_nodes = await graph.get_nodes([event_ref, entity_ref])
        assert observed_nodes[event_ref]["session_id"] == group
        assert observed_nodes[entity_ref]["name"] == "control fixture"
        evidence["active_nodes"] = [
            {"label": ref.label, "key": ref.key, "properties": properties}
            for ref, properties in observed_nodes.items()
        ]
        documents = await ledger.get_documents(list(map(str, event_ids[:2])))
        assert all(document["payload"]["fixture"] == group for document in documents)
        evidence["active_ledger_ids"] = [document["event_id"] for document in documents]
        await subscription.ensure_group()
        delivered = await subscription.read_new(100, 0)
        by_event = {item.fields["event_id"]: item for item in delivered}
        assert all(str(event_id) in by_event for event_id in event_ids[:2])
        evidence["accepted_positions"] = positions
        record("active_ledger_graph_and_delivery")
        await read_paths("active_external_read", external=True)

        row = (await asyncio.to_thread(read_owner, database))[0]
        row = await transition(row, state="draining")
        await read_paths("draining_external_refused", external=True, expect_refusal=True)
        await refused("draining_rejects_new_admission", lambda: ledger.append(events[2]))
        await graph.upsert_nodes([NodeWrite(event_ref, {"drained": True})])
        await subscription.ack(by_event[str(event_ids[0])].position)
        assert by_event[str(event_ids[1])].position in await subscription.delivery_counts(100)
        record("draining_allows_outstanding_graph_write_and_ack")
        await read_paths("draining_processing_allowed")

        row = await transition(row, state="frozen")
        await read_paths("frozen_processing_refused", expect_refusal=True)
        before_refusals = await asyncio.to_thread(fingerprint, database)
        await refused(
            "frozen_rejects_graph_write",
            lambda: graph.upsert_nodes([NodeWrite(event_ref, {"forbidden": True})]),
        )
        await refused("frozen_rejects_ack", lambda: subscription.ack(positions[1]))
        await refused(
            "frozen_rejects_deadletter",
            lambda: subscription.dead_letter(by_event[str(event_ids[1])], 1),
        )
        await refused("frozen_rejects_admission", lambda: ledger.append(events[2]))
        assert before_refusals == await asyncio.to_thread(fingerprint, database)
        record("frozen_refusals_have_zero_application_effects")

        # Models a worker/model call already in flight before activation. This
        # is a controlled handoff interleaving, not simultaneous transaction contention.
        ready, release = asyncio.Event(), asyncio.Event()

        async def delayed_old_write():
            ready.set()
            await release.wait()
            await graph.upsert_nodes([NodeWrite(event_ref, {"late_output": True})])

        delayed_task = asyncio.create_task(delayed_old_write())
        await ready.wait()
        row = await transition(row, state="active", advance=True)
        evidence["advanced_epoch"] = row[3]
        await read_paths("stale_epoch_read_refused", expect_refusal=True)
        before_refusals = await asyncio.to_thread(fingerprint, database)
        release.set()
        await refused("old_runtime_delayed_graph_output_rejected", lambda: delayed_task)
        await refused("old_runtime_admission_rejected", lambda: ledger.append(events[2]))
        await refused("old_runtime_ack_rejected", lambda: subscription.ack(positions[1]))
        assert before_refusals == await asyncio.to_thread(fingerprint, database)
        record("epoch_refusals_have_zero_application_effects")

        renewed = replace(fence, epoch=row[3])
        recovered_graph = SpannerGraphStore(database, tenant_fence=renewed)
        recovered_sub = SpannerSubscription(
            database,
            group,
            "control-worker",
            tenant_fence=renewed,
            tenant_engine_revision=binding.engine_revision,
        )
        await recovered_graph.upsert_nodes([NodeWrite(event_ref, {"recovered": True})])
        await recovered_sub.ack(positions[1])
        assert not await recovered_sub.delivery_counts(100)
        found = await recovered_graph.get_nodes([event_ref])
        assert found[event_ref]["recovered"] is True and "late_output" not in found[event_ref]
        record("new_epoch_runtime_recovers_pending_work")
        wrong_owner = SpannerGraphStore(database, tenant_fence=replace(renewed, tenant_id="wrong"))
        before_wrong_owner = await asyncio.to_thread(fingerprint, database)
        await refused(
            "wrong_tenant_graph_write_rejected",
            lambda: wrong_owner.upsert_nodes([NodeWrite(event_ref, {"wrong_owner": True})]),
        )
        assert before_wrong_owner == await asyncio.to_thread(fingerprint, database)
        record("wrong_tenant_refusal_has_zero_application_effects")
    finally:
        if delayed_task is not None:
            delayed_task.cancel()
            await asyncio.gather(delayed_task, return_exceptions=True)
        rows = await asyncio.to_thread(read_owner, database)
        assert len(rows) == 1
        row = rows[0]
        assert tuple(row[:3]) == (fence.tenant_id, fence.database_resource, fence.binding_id)
        assert row[4] == fence.bundle_digest
        if row[-1] != "active":
            row = await transition(row, state="active", advance=True)
        cleanup_fence = replace(fence, epoch=row[3])

        def clean(transaction):
            transaction.delete(
                "GraphEdges",
                KeySet(keys=[["Event", str(event_ids[0]), "REFERENCES", "Entity", entity_id]]),
            )
            transaction.delete(
                "GraphNodes", KeySet(keys=[["Event", str(event_ids[0])], ["Entity", entity_id]])
            )
            transaction.delete("Events", KeySet(keys=[[str(event_id)] for event_id in event_ids]))
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

        evidence["cleanup_intent"] = {"epoch": row[3], "fixture": evidence["fixture"]}
        persist(evidence)
        await asyncio.to_thread(cleanup_fence.run, database, clean, operation="processing")
        evidence["control_after"] = await asyncio.to_thread(read_owner, database)
        record("owned_fixture_cleanup_completed_control_owner_retained")
