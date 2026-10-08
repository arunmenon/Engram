"""Atomic acceptance and duplicate identity through Engram's Spanner adapter.

Transaction fake only, no emulator or cloud. Cloud verification remains required.
"""

import copy
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from context_graph.adapters.spanner.commits import CommitBudget, event_row_cost
from context_graph.adapters.spanner.event_acceptance import (
    ACCEPTANCE_COLUMN_DDL,
    AcceptanceSchemaError,
    acceptance_column_valid,
    plan_acceptance_upgrade,
)
from context_graph.adapters.spanner.log import SpannerEventLog, json_value
from context_graph.adapters.spanner.schema import schema_statements
from context_graph.adapters.spanner.tenant_control import TenantFence
from context_graph.domain.event_acceptance import EventAcceptance, stamp_acceptance
from context_graph.ports.errors import InvalidRequestError, RuntimeFencedError
from tests.unit.test_event_acceptance import context, event
from tests.unit.test_tenant_catalog import bind


class Transaction:
    committed = datetime(2026, 10, 7, tzinfo=UTC)

    def __init__(self, db):
        self.db = db
        self.rows = copy.deepcopy(db.rows)
        self.effects = []

    def read(self, table, columns, keys):
        if table == "TenantControl":
            return [self.db.owner]
        assert table == "Events"
        return [
            [self.rows[key[0]][column] for column in columns]
            for key in keys.keys
            if key[0] in self.rows
        ]

    def insert_or_update(self, table, columns, rows):
        assert table == "Events"
        for row in rows:
            data = dict(zip(columns, row, strict=True))
            data["commit_ts"] = self.committed
            self.rows[data["event_id"]] = data
            self.effects.append(data)


class Database:
    def __init__(self, binding):
        self.name = binding.database_resource
        self.owner = [
            binding.tenant_id,
            self.name,
            binding.binding_id,
            binding.epoch,
            binding.bundle_digest,
            "active",
        ]
        self.rows = {}
        self.transactions = []

    @contextmanager
    def snapshot(self, *, multi_use=False):
        assert multi_use
        yield Transaction(self)

    def run_in_transaction(self, callback):
        transaction = Transaction(self)
        self.transactions.append(transaction)
        result = callback(transaction)
        self.rows = transaction.rows
        return result


def setup(binding=None, budget=None):
    binding = binding or bind()
    db = Database(binding)
    store = SpannerEventLog(
        db,
        tenant_fence=TenantFence.from_binding(binding),
        tenant_engine_revision=binding.engine_revision,
        commit_budget=budget,
        tenant_binding=binding,
    )
    return binding, db, store


def receipt(db):
    return EventAcceptance.model_validate(json_value(db.rows[str(event().event_id)]["acceptance"]))


@pytest.mark.asyncio
async def test_atomic_stamp_duplicate_and_conflict_preserve_original():
    binding, db, store = setup()
    payload = {"nested": {"value": 1}}
    first = await store.append(event(), payload, admission_context=context(binding))
    original = copy.deepcopy(db.rows)
    retry = await store.append_batch_outcomes(
        [event()], [payload], admission_context=context(binding)
    )
    assert retry[0].status == "duplicate" and retry[0].position == first
    assert db.rows == original
    changed = await store.append_batch_outcomes(
        [event()], [{"nested": {"value": 2}}], admission_context=context(binding)
    )
    assert changed[0].status == "conflict" and changed[0].position is None
    assert db.rows == original
    assert receipt(db) == stamp_acceptance(context(binding), event(), payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("budget", [None, CommitBudget(max_mutations=1)])
async def test_same_id_in_same_or_different_chunks_has_exact_outcomes(budget):
    binding, db, store = setup(budget=budget)
    outcomes = await store.append_batch_outcomes(
        [event()] * 3, [{"x": 1}, {"x": 1}, {"x": 2}], admission_context=context(binding)
    )
    assert [outcome.status for outcome in outcomes] == ["created", "duplicate", "conflict"]
    assert outcomes[0].position == outcomes[1].position
    assert len(db.rows) == 1
    assert sum(len(t.effects) for t in db.transactions) == 1


@pytest.mark.asyncio
async def test_other_producer_conflicts_but_rotated_credentials_retry():
    binding, db, store = setup()
    await store.append(event(), admission_context=context(binding))
    retry = await store.append_batch_outcomes(
        [event()], admission_context=context(binding, credential="rotated")
    )
    assert retry[0].status == "duplicate"
    other = await store.append_batch_outcomes(
        [event()], admission_context=context(binding, source="other")
    )
    assert other[0].status == "conflict"
    assert sum(len(t.effects) for t in db.transactions) == 1


@pytest.mark.asyncio
async def test_epoch_advance_preserves_original_receipt_but_stale_duplicate_fenced():
    binding, db, store = setup()
    first = await store.append(event(), admission_context=context(binding))
    original = receipt(db)
    advanced = replace(binding, epoch=2)
    db.owner[3] = 2
    with pytest.raises(RuntimeFencedError):
        await store.append(event(), admission_context=context(binding))
    new_store = SpannerEventLog(
        db,
        tenant_fence=TenantFence.from_binding(advanced),
        tenant_engine_revision=advanced.engine_revision,
        tenant_binding=advanced,
    )
    assert await new_store.append(event(), admission_context=context(advanced)) == first
    assert receipt(db) == original and original.accepted_epoch == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("dedup_active", False), ("document", None)])
async def test_retained_row_preserves_identity_after_expiry(field, value):
    binding, db, store = setup()
    first = await store.append(event(), admission_context=context(binding))
    db.rows[str(event().event_id)][field] = value
    original = copy.deepcopy(db.rows)
    assert await store.append(event(), admission_context=context(binding)) == first
    assert db.rows == original


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [None, {}, {"envelope_version": 2}])
async def test_unknown_existing_receipt_is_control_refusal_without_writes(raw):
    binding, db, store = setup()
    await store.append(event(), admission_context=context(binding))
    db.rows[str(event().event_id)]["acceptance"] = raw
    original = copy.deepcopy(db.rows)
    with pytest.raises(RuntimeFencedError):
        await store.append(event(), admission_context=context(binding))
    assert db.rows == original and not db.transactions[-1].effects


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["frozen", "draining"])
async def test_control_refusal_happens_before_event_mutation(state):
    binding, db, store = setup()
    db.owner[-1] = state
    with pytest.raises(RuntimeFencedError):
        await store.append(event(), admission_context=context(binding))
    assert not db.rows and not db.transactions[-1].effects


@pytest.mark.asyncio
async def test_wrong_or_missing_context_refused_before_transaction():
    binding, db, store = setup()
    for supplied in (
        None,
        context(binding).model_copy(update={"engine_revision": "wrong"}),
        context(binding).model_copy(
            update={"database_resource": "projects/x/instances/y/databases/z"}
        ),
    ):
        with pytest.raises(RuntimeFencedError):
            await store.append(event(), admission_context=supplied)
    assert not db.transactions


@pytest.mark.asyncio
async def test_unstamped_bound_import_and_bare_entry_refused():
    _, db, store = setup()
    with pytest.raises(RuntimeFencedError):
        await store.append_imported([])
    with pytest.raises(RuntimeFencedError):
        await store.append_entry("x", "s")
    assert not db.transactions


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field", ["payload", "event_id", "acceptance", "source_id", "occurred_at", "search_text"]
)
async def test_bound_enrichment_cannot_change_original_identity(field):
    _, db, store = setup()
    expected_error = TypeError if field == "event_id" else InvalidRequestError
    with pytest.raises(expected_error):
        await store.set_document_fields("x", **{field: "spoofed"})
    assert not db.transactions


@pytest.mark.asyncio
async def test_caller_mutation_after_thread_handoff_cannot_change_persisted_payload():
    binding, db, store = setup()
    payload = {"nested": {"value": 1}}
    original_run = store._run

    async def mutate_then_run(fn, *args):
        payload["nested"]["value"] = 99
        return await original_run(fn, *args)

    store._run = mutate_then_run
    await store.append(event(), payload, admission_context=context(binding))
    stored = json_value(db.rows[str(event().event_id)]["document"])
    assert stored["payload"] == {"nested": {"value": 1}}
    assert (
        receipt(db).request_digest
        == stamp_acceptance(context(binding), event(), stored["payload"]).request_digest
    )


def test_acceptance_upgrade_is_additive_noop_or_explicit_refusal():
    ddl = schema_statements(384)
    assert acceptance_column_valid(ddl) and plan_acceptance_upgrade(ddl) == []
    legacy = [s.replace("            acceptance JSON,\n", "") for s in ddl]
    assert plan_acceptance_upgrade(legacy) == [ACCEPTANCE_COLUMN_DDL]
    assert event_row_cost({}, {"large": "x" * 1024})[1] - event_row_cost({})[1] >= 1024
    for invalid in (
        "acceptance STRING(MAX)",
        "acceptance JSON NOT NULL",
        "acceptance JSON AS (JSON '{}') STORED",
    ):
        with pytest.raises(AcceptanceSchemaError):
            plan_acceptance_upgrade([s.replace("acceptance JSON", invalid) for s in ddl])


@pytest.mark.asyncio
async def test_request_writers_do_not_share_producer_state():
    binding, db, store = setup()
    first = store.admission_writer(context(binding, source="first"))
    second = store.admission_writer(context(binding, source="second"))
    await first.append(event(), {"x": 1})
    outcomes = await second.append_batch_outcomes([event()], [{"x": 1}])
    assert outcomes[0].status == "conflict"
    assert receipt(db).source_id == "first"
    assert first.context.source_id == "first" and second.context.source_id == "second"


def test_authenticated_http_path_stamps_receipt_and_reports_conflict(test_client):
    from context_graph.tenancy import Principal

    binding, db, store = setup()
    test_client.app.state.event_store = store
    test_client.app.state.tenant_binding = binding

    @test_client.app.middleware("http")
    async def authenticated(request, call_next):
        request.scope["engram.principal"] = Principal(
            "credential", "a", frozenset({"api"}), "producer"
        )
        return await call_next(request)

    raw = {**event().model_dump(mode="json"), "payload": {"x": 1}}
    first = test_client.post("/v1/events", json=raw)
    assert first.status_code == 201 and first.json()["status"] == "created"
    retry = test_client.post("/v1/events", json=raw)
    assert retry.status_code == 201 and retry.json()["status"] == "duplicate"
    changed = {**raw, "payload": {"x": 2}}
    conflict = test_client.post("/v1/events", json=changed)
    assert conflict.status_code == 409
    batch = test_client.post("/v1/events/batch", json={"events": [changed]})
    assert batch.status_code == 409 and batch.json()["accepted"] == 0
    mixed = test_client.post("/v1/events/batch", json={"events": [changed, raw]})
    assert mixed.status_code == 201 and mixed.json()["accepted"] == 1
    assert mixed.json()["rejected"] == 1
    assert receipt(db).source_id == "producer"
    assert sum(len(t.effects) for t in db.transactions) == 1


@pytest.mark.parametrize("identity,status", [(None, 401), ("wrongtenant", 403), ("admin", 403)])
def test_http_writer_refuses_untrusted_principal_before_storage(test_client, identity, status):
    from context_graph.tenancy import Principal

    binding, db, store = setup()
    test_client.app.state.event_store = store
    test_client.app.state.tenant_binding = binding

    @test_client.app.middleware("http")
    async def authenticated(request, call_next):
        if identity is not None:
            request.scope["engram.principal"] = Principal(
                "credential",
                "b" if identity == "wrongtenant" else "a",
                frozenset({"admin" if identity == "admin" else "api"}),
                "producer",
            )
        return await call_next(request)

    response = test_client.post("/v1/events", json=event().model_dump(mode="json"))
    assert response.status_code == status and not db.transactions


@pytest.mark.parametrize("number", [1.0, -0.0, 0.0, 1.25])
def test_json_storage_normalization_preserves_receipt_fingerprint(number):
    import json

    from context_graph.adapters.spanner.log import json_param
    from context_graph.domain.event_acceptance import request_fingerprint

    payload = {"number": number, "literal": {"$float": "1.0"}}
    wire = json.loads(json_param(payload).serialize())

    def server_normalize(value):
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, list):
            return [server_normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: server_normalize(item) for key, item in value.items()}
        return value

    decoded = json_value(json.dumps(server_normalize(wire)))
    assert type(decoded["number"]) is float
    assert request_fingerprint(event(), decoded) == request_fingerprint(event(), payload)
