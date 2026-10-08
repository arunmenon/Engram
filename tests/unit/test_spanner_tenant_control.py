"""Control-row fences: rejected effects and retry revalidation."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from context_graph.adapters.spanner.tenant_control import (
    TENANT_CONTROL_DDL,
    TenantFence,
    TenantFenceError,
    control_statement_matches,
)

RESOURCE = "projects/p/instances/i/databases/d"
FENCE = TenantFence("tenant-a", RESOURCE, "binding-a", 1, "sha256:" + "a" * 64)


def test_recorded_real_spanner_ddl_canonicalization_matches_exact_request():
    path = Path(
        "docs/review/spanner-compatibility/runs/"
        "20261007-cloud-tenant-control-prepare-02/schema-evidence.json"
    )
    observed = json.loads(path.read_text())["operation_metadata"]["statements"][0]
    assert control_statement_matches(TENANT_CONTROL_DDL, observed)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda ddl: ddl.replace("epoch INT64", "epoch STRING(MAX)"),
        lambda ddl: ddl.replace("serving_state STRING(16)", "serving_state STRING(32)"),
        lambda ddl: ddl.replace("PRIMARY KEY (control_id)", "PRIMARY KEY (tenant_id)"),
        lambda ddl: ddl.replace(" NOT NULL", "", 1),
        lambda ddl: ddl.replace("TenantControl", "OtherControl"),
    ],
)
def test_metadata_comparison_does_not_accept_changed_request(mutation):
    assert not control_statement_matches(TENANT_CONTROL_DDL, mutation(TENANT_CONTROL_DDL))


class Transaction:
    def __init__(self, row=None, populated=()):
        self.row = row
        self.populated = set(populated)
        self.effects = []

    def read(self, table, columns, keys):
        assert table == "TenantControl"
        assert list(keys.keys) == [["active"]]
        return [] if self.row is None else [self.row]

    def execute_sql(self, sql):
        return [[1]] if sql.split()[3] in self.populated else []

    def insert(self, table, columns, rows):
        self.effects.append((table, tuple(columns), rows))
        self.row = list(rows[0][1:])


class Database:
    name = RESOURCE

    def __init__(self, transaction):
        self.transaction = transaction
        self.calls = 0

    def run_in_transaction(self, callback):
        self.calls += 1
        return callback(self.transaction)


def owner(state="active"):
    return ["tenant-a", RESOURCE, "binding-a", 1, "sha256:" + "a" * 64, state]


@pytest.mark.parametrize("operation", ["admission", "processing", "read"])
def test_matching_active_control_accepts(operation):
    FENCE.check(Transaction(owner()), operation=operation)


@pytest.mark.parametrize("state", ["frozen", "unknown", "", None])
@pytest.mark.parametrize("operation", ["admission", "processing", "read"])
def test_frozen_or_unknown_state_refuses(state, operation):
    with pytest.raises(TenantFenceError):
        FENCE.check(Transaction(owner(state)), operation=operation)


def test_draining_permits_processing_but_not_admission_or_reads():
    FENCE.check(Transaction(owner("draining")), operation="processing")
    for operation in ("admission", "read"):
        with pytest.raises(TenantFenceError):
            FENCE.check(Transaction(owner("draining")), operation=operation)


@pytest.mark.parametrize(
    "index,value",
    [
        (0, "tenant-b"),
        (1, RESOURCE + "-other"),
        (2, "binding-b"),
        (3, 2),
        (4, "sha256:" + "b" * 64),
    ],
)
def test_identity_mismatch_makes_zero_callback_effects(index, value):
    row = owner()
    row[index] = value
    database = Database(Transaction(row))
    effects = []
    with pytest.raises(TenantFenceError):
        FENCE.run(database, lambda transaction: effects.append(transaction), operation="processing")
    assert effects == []


def test_missing_control_is_not_automatically_bootstrapped():
    database = Database(Transaction())
    with pytest.raises(TenantFenceError):
        FENCE.run(
            database, lambda transaction: transaction.effects.append("write"), operation="admission"
        )
    assert database.transaction.effects == []


def test_retry_rechecks_owner_before_replaying_effect():
    transaction = Transaction(owner())
    effects = []

    class RetryingDatabase(Database):
        def run_in_transaction(self, callback):
            callback(transaction)  # Simulates an aborted first attempt, not a commit.
            transaction.row[3] = 2
            return callback(transaction)

    with pytest.raises(TenantFenceError):
        FENCE.run(
            RetryingDatabase(transaction),
            lambda tx: effects.append(tx.row[3]),
            operation="processing",
        )
    assert effects == [1]  # Second callback never ran with stale interpretation.


def test_wrong_database_handle_never_starts_transaction():
    database = Database(Transaction(owner()))
    database.name = RESOURCE + "-other"
    with pytest.raises(TenantFenceError):
        FENCE.run(database, lambda tx: None, operation="processing")
    with pytest.raises(TenantFenceError):
        FENCE.bootstrap(database, adopt_existing=True)
    assert database.calls == 0


def test_explicit_bootstrap_is_idempotent_and_cannot_overwrite_owner():
    database = Database(Transaction())
    FENCE.bootstrap(database)
    FENCE.bootstrap(database)
    assert len(database.transaction.effects) == 1
    with pytest.raises(TenantFenceError):
        replace(FENCE, tenant_id="tenant-b").bootstrap(database, adopt_existing=True)
    assert len(database.transaction.effects) == 1


@pytest.mark.parametrize(
    "table",
    [
        "Events",
        "GraphNodes",
        "GraphEdges",
        "ConsumerGroups",
        "ConsumerCursors",
        "ConsumerDeliveries",
        "ConsumerDeadLetters",
    ],
)
def test_existing_data_requires_explicit_adoption(table):
    database = Database(Transaction(populated=[table]))
    with pytest.raises(TenantFenceError):
        FENCE.bootstrap(database)
    assert database.transaction.effects == []
    FENCE.bootstrap(database, adopt_existing=True)
    assert len(database.transaction.effects) == 1


def test_bootstrap_does_not_reactivate_frozen_owner():
    database = Database(Transaction(owner("frozen")))
    with pytest.raises(TenantFenceError):
        FENCE.bootstrap(database, adopt_existing=True)
    assert database.transaction.effects == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action",
    [
        "append",
        "graph_clear",
        "graph_upsert",
        "ensure_group",
        "read_new",
        "ack",
        "dead_letter",
        "claim",
        "document_update",
        "retention",
        "dml",
    ],
)
async def test_store_mutations_refuse_stale_epoch_before_application_access(action):
    from datetime import UTC, datetime

    from context_graph.adapters.spanner.graph import SpannerGraphStore
    from context_graph.adapters.spanner.log import SpannerEventLog, format_position
    from context_graph.adapters.spanner.subscription import SpannerSubscription
    from context_graph.domain.event_acceptance import AdmissionContext
    from context_graph.ports.subscription import Delivery
    from tests.unit.test_event_acceptance import event
    from tests.unit.test_tenant_catalog import bind, configuration

    settings = configuration("d")
    settings.spanner.project, settings.spanner.instance = "p", "i"
    binding = bind(settings=settings)
    fence = TenantFence.from_binding(binding)
    row = [*fence._identity(), "active"]
    row[3] = 2
    database = Database(Transaction(row))
    graph = SpannerGraphStore(database, tenant_fence=fence)
    ledger = SpannerEventLog(
        database,
        tenant_fence=fence,
        tenant_engine_revision=binding.engine_revision,
        tenant_binding=binding,
    )
    subscription = SpannerSubscription(
        database, "g", "c", tenant_fence=fence, tenant_engine_revision="test"
    )
    position = format_position(datetime.now(UTC), 0, "event-1")
    admission = AdmissionContext(
        tenant_id=fence.tenant_id,
        database_resource=fence.database_resource,
        binding_id=fence.binding_id,
        accepted_epoch=fence.epoch,
        bundle_digest=fence.bundle_digest,
        engine_revision=binding.engine_revision,
        source_id="fixture",
    )
    actions = {
        "append": lambda: ledger.append(event(), admission_context=admission),
        "graph_clear": graph._clear,
        "graph_upsert": lambda: graph._upsert_nodes([(("Event", "event-1"), {})]),
        "ensure_group": subscription.ensure_group,
        "read_new": lambda: subscription.read_new(1, 0),
        "ack": lambda: subscription.ack(position),
        "dead_letter": lambda: subscription.dead_letter(Delivery(position, {}), 1),
        "claim": subscription.claim_orphaned,
        "document_update": lambda: ledger.set_document_fields("event-1", summary="changed"),
        "retention": ledger._purge,
        "dml": lambda: ledger._execute_updates([("DELETE FROM Events", {}, {})]),
    }
    with pytest.raises(TenantFenceError):
        await actions[action]()
    assert database.transaction.effects == []
    assert database.calls == (0 if action == "graph_clear" else 1)


def test_draining_ledger_admission_is_distinct_from_processing():
    from context_graph.adapters.spanner.log import SpannerEventLog

    database = Database(Transaction(owner("draining")))
    ledger = SpannerEventLog(database, tenant_fence=FENCE)
    effects = []
    ledger._transact_sync(lambda tx: effects.append("processing"))
    with pytest.raises(TenantFenceError):
        ledger._transact_sync(lambda tx: effects.append("admission"), admission=True)
    assert effects == ["processing"]
