"""Real Spanner atomic-acceptance assertions on exact disposable fixtures.

No workers or pack projection. Never reset tables or adopt a populated target.
"""

from __future__ import annotations

from engram_experiment_support import await_settled as await_settled

import asyncio
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from engram_spanner_tenant_control_cases import operator_transition, read_owner
from engram_spanner_tenant_runtime_cases import runtime_settings
from google.cloud.spanner_v1 import KeySet, param_types

from context_graph.adapters.spanner.commits import CommitBudget
from context_graph.adapters.spanner.log import SpannerEventLog, json_value
from context_graph.adapters.spanner.schema import schema_differences
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.domain.event_acceptance import EventAcceptance, request_fingerprint
from context_graph.domain.models import Event
from context_graph.ports.errors import InvalidRequestError, RuntimeFencedError
from context_graph.tenancy import Principal, TenantBinding


def assert_owned(row, binding, epochs):
    """Never adopt freshly observed ownership as cleanup authority."""
    assert len(row) == 6 and row[3] in epochs, "Unexpected owner epoch"
    expected = TenantFence.from_binding(replace(binding, epoch=row[3]))._identity()
    assert tuple(row[:-1]) == expected and row[-1] in {"active", "draining", "frozen"}, (
        "Unrelated owner"
    )


async def verify_acceptance(database, values, run_id, evidence, checks, fingerprint, persist):
    try:
        return await await_settled(
            _verify_acceptance(database, values, run_id, evidence, checks, fingerprint, persist)
        )
    except asyncio.CancelledError:
        checks.append(
            {
                "name": "acceptance_cancelled_after_case_settled",
                "passed": False,
                "error_type": "CancelledError",
                "scenarios": [],
            }
        )
        persist(evidence)
        raise


async def _verify_acceptance(database, values, run_id, evidence, checks, fingerprint, persist):
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
    fence = TenantFence.from_binding(binding)
    allowed_epochs = {binding.epoch}
    assert_owned(owner[0], binding, allowed_epochs)
    assert not await asyncio.to_thread(
        schema_differences, database, settings.spanner.embedding_dimensions
    )
    ids = [uuid5(NAMESPACE_URL, run_id + suffix) for suffix in ("/same-chunk", "/concurrent")]
    principal = Principal(
        "acceptance-original", binding.tenant_id, frozenset({"api"}), "acceptance-source"
    )
    context = binding.admission_context(principal)
    events = [
        Event(
            event_id=eid,
            event_type="tool.execute",
            occurred_at=datetime.now(UTC) - timedelta(days=2),
            session_id="acceptance-" + run_id,
            agent_id="compat-control",
            trace_id=run_id,
            payload_ref="fixture:" + str(eid),
        )
        for eid in ids
    ]
    payload = {
        "integral": 1.0,
        "negative_zero": -0.0,
        "fractional": 0.125,
        "integer": 1,
        "literal": {"$float": "1.0"},
        "fixture": run_id,
    }
    evidence["acceptance_intent"] = {
        "owner": owner,
        "event_ids": list(map(str, ids)),
        "max_events": 2,
        "retention_scope": "Initially empty target, two owned events only; "
        "expire/housekeep may affect only these",
        "producer": context.source_id,
        "current_epoch": binding.epoch,
        "receipt_digest": request_fingerprint(events[0], payload),
        "worker_loops": False,
        "pack_projection": False,
    }
    persist(evidence)
    ledger = SpannerEventLog(
        database,
        tenant_fence=fence,
        tenant_engine_revision=binding.engine_revision,
        tenant_binding=binding,
    )

    def record(name):
        checks.append({"name": name, "passed": True, "scenarios": []})
        evidence["acceptance_checks"] = [check["name"] for check in checks]
        persist(evidence)

    async def cell(store, event_id):
        rows = await store._query(
            "SELECT acceptance, document, commit_ts, batch_index, dedup_active "
            "FROM Events WHERE event_id = @id",
            {"id": str(event_id)},
            {"id": param_types.STRING},
        )
        assert len(rows) == 1
        raw, document, commit_ts, batch_index, dedup_active = rows[0]
        return (
            EventAcceptance.model_validate(json_value(raw)),
            json_value(document),
            commit_ts,
            batch_index,
            dedup_active,
        )

    async def refusal(name, operation, expected=RuntimeFencedError):
        try:
            await operation()
        except expected:
            record(name)
        else:
            raise AssertionError(name + " unexpectedly succeeded")

    try:
        unsupported = events[0].model_copy(update={"event_type": "tool.custom"})
        inactive = events[1].model_copy(update={"event_type": "pdlc.change.created"})
        rejected = await ledger.append_batch_outcomes(
            [unsupported, inactive],
            [payload, {"repo": "example/payments", "number": 7}],
            admission_context=context,
        )
        assert [result.status for result in rejected] == ["rejected", "rejected"]
        assert all(
            result.reason == "event_unsupported" and result.position is None for result in rejected
        )
        assert await asyncio.to_thread(fingerprint, database) == before
        evidence["admission_rejections"] = [
            {
                "event_id": str(item.event_id),
                "event_type": item.event_type,
                "status": result.status,
                "reason": result.reason,
            }
            for item, result in zip([unsupported, inactive], rejected, strict=True)
        ]
        record("unknown_core_and_inactive_domain_events_refused_without_writes")
        await refusal(
            "direct_append_enforces_active_pack_admission",
            lambda: ledger.append(unsupported, payload, admission_context=context),
            InvalidRequestError,
        )
        await refusal(
            "authenticated_proxy_enforces_active_pack_admission",
            lambda: ledger.admission_writer(context).append(inactive, {}),
            InvalidRequestError,
        )
        assert await asyncio.to_thread(fingerprint, database) == before
        record("rejected_ids_remain_unreserved_for_subsequent_valid_events")
        outcomes = await ledger.append_batch_outcomes(
            [events[0]] * 3,
            [payload, payload, {**payload, "integer": 2}],
            admission_context=context,
        )
        assert [outcome.status for outcome in outcomes] == ["created", "duplicate", "conflict"]
        assert outcomes[0].position == outcomes[1].position and outcomes[2].position is None
        original = await cell(ledger, ids[0])
        original_receipt = original[0]
        assert original_receipt.request_digest == request_fingerprint(
            events[0], original[1]["payload"]
        )
        assert type(original[1]["payload"]["integral"]) is float
        assert type(original[1]["payload"]["integer"]) is int
        evidence["original_receipt"] = original_receipt.model_dump()
        evidence["original_position"] = outcomes[0].position
        record("atomic_stamp_same_chunk_duplicate_and_conflict")
        record("real_json_numeric_roundtrip_matches_receipt_digest")

        concurrent = await asyncio.gather(
            *[
                ledger.append_batch_outcomes([events[1]], [payload], admission_context=context)
                for _ in range(4)
            ],
            return_exceptions=True,
        )
        for outcome in concurrent:
            if isinstance(outcome, BaseException):
                raise outcome
        statuses = [outcome[0].status for outcome in concurrent]
        assert statuses.count("created") == 1 and statuses.count("duplicate") == 3
        assert len({outcome[0].position for outcome in concurrent}) == 1
        evidence["concurrent_outcomes"] = [outcome[0].__dict__ for outcome in concurrent]
        record("concurrent_writers_create_once_preserve_original_position")

        chunked = SpannerEventLog(
            database,
            tenant_fence=fence,
            tenant_engine_revision=binding.engine_revision,
            commit_budget=CommitBudget(max_mutations=1),
            tenant_binding=binding,
        )
        chunks = await chunked.append_batch_outcomes(
            [events[0]] * 3,
            [payload, {**payload, "integer": 3}, payload],
            admission_context=context,
        )
        assert [outcome.status for outcome in chunks] == ["duplicate", "conflict", "duplicate"]
        assert all(
            outcome.position == outcomes[0].position
            for outcome in chunks
            if outcome.status == "duplicate"
        )
        assert (await cell(ledger, ids[0]))[0] == original_receipt
        record("different_chunk_identity_conflict_does_not_overwrite_receipt")

        rotated = binding.admission_context(replace(principal, credential_id="acceptance-rotated"))
        assert (
            await ledger.append(events[0], payload, admission_context=rotated)
            == outcomes[0].position
        )
        other = binding.admission_context(replace(principal, source_id="different-source"))
        assert (
            await ledger.append_batch_outcomes([events[0]], [payload], admission_context=other)
        )[0].status == "conflict"
        assert (await cell(ledger, ids[0])) == original
        record("credential_rotation_retries_other_producer_conflicts_without_mutation")

        await refusal("bound_import_refused", lambda: ledger.append_imported([]))
        await refusal(
            "bound_bare_append_refused",
            lambda: ledger.append_entry(str(ids[0]), events[0].session_id),
        )
        await refusal(
            "original_payload_enrichment_refused",
            lambda: ledger.set_document_fields(str(ids[0]), payload={"spoofed": True}),
            InvalidRequestError,
        )
        await ledger.set_document_fields(
            str(ids[0]), summary="acceptance test", keywords=["acceptance"]
        )
        enriched = await cell(ledger, ids[0])
        assert enriched[0] == original_receipt and enriched[1]["summary"] == "acceptance test"
        assert enriched[0].request_digest == request_fingerprint(events[0], enriched[1]["payload"])
        record("allowed_enrichment_preserves_request_and_receipt")

        assert await ledger.expire(1) == (0, 2)
        assert (await cell(ledger, ids[0]))[1] is None
        assert (
            await ledger.append(events[0], payload, admission_context=context)
            == outcomes[0].position
        )
        assert (await cell(ledger, ids[0]))[0] == original_receipt
        record("real_document_expiry_keeps_original_duplicate_identity")
        housekeeping = await ledger.housekeep(1, 48)
        assert housekeeping["dedup_entries_removed"] == 2
        expired = await cell(ledger, ids[0])
        assert expired[1] is None and expired[4] is False
        assert (
            await ledger.append(events[0], payload, admission_context=context)
            == outcomes[0].position
        )
        assert (await cell(ledger, ids[0])) == expired
        record("real_dedup_expiry_keeps_retained_row_identity_without_resurrection")

        rows = await asyncio.to_thread(read_owner, database)
        assert len(rows) == 1
        row = rows[0]
        assert_owned(row, binding, allowed_epochs)
        evidence["freeze_intent"] = {"expected": row, "state": "frozen"}
        persist(evidence)
        assert_owned(row, binding, allowed_epochs)
        row = await asyncio.to_thread(operator_transition, database, row, state="frozen")
        await refusal(
            "frozen_owner_duplicate_cannot_bypass_current_control",
            lambda: ledger.append(events[0], payload, admission_context=context),
        )
        evidence["advance_intent"] = {"expected": row, "state": "active", "advance_epoch": True}
        persist(evidence)
        assert_owned(row, binding, allowed_epochs)
        allowed_epochs.add(row[3] + 1)
        row = await asyncio.to_thread(
            operator_transition, database, row, state="active", advance=True
        )
        await refusal(
            "stale_epoch_duplicate_cannot_bypass_current_control",
            lambda: ledger.append(events[0], payload, admission_context=context),
        )
        renewed = replace(binding, epoch=row[3])
        renewed_log = SpannerEventLog(
            database,
            tenant_fence=TenantFence.from_binding(renewed),
            tenant_engine_revision=renewed.engine_revision,
            tenant_binding=renewed,
        )
        assert (
            await renewed_log.append(
                events[0], payload, admission_context=renewed.admission_context(principal)
            )
            == outcomes[0].position
        )
        assert (await cell(renewed_log, ids[0]))[0] == original_receipt
        record("new_epoch_retry_preserves_original_accepted_epoch_and_receipt")
    finally:
        rows = await asyncio.to_thread(read_owner, database)
        assert len(rows) == 1, "Cleanup owner is missing or ambiguous"
        row = rows[0]
        assert_owned(row, binding, allowed_epochs)
        if row[-1] == "frozen":
            evidence["cleanup_reactivation_intent"] = {"expected": row, "advance_epoch": True}
            persist(evidence)
            assert_owned(row, binding, allowed_epochs)
            allowed_epochs.add(row[3] + 1)
            row = await asyncio.to_thread(
                operator_transition, database, row, state="active", advance=True
            )
        assert row[-1] == "active"
        cleanup_fence = TenantFence.from_binding(replace(binding, epoch=row[3]))
        evidence["cleanup_intent"] = {"event_ids": list(map(str, ids)), "owner": row}
        persist(evidence)

        def clean(transaction):
            transaction.delete("Events", KeySet(keys=[[str(eid)] for eid in ids]))

        await asyncio.to_thread(cleanup_fence.run, database, clean, operation="processing")
        evidence["control_after"] = await asyncio.to_thread(read_owner, database)
        assert await asyncio.to_thread(fingerprint, database) == before
        record("exact_owned_events_removed_owner_and_other_application_tables_preserved")
