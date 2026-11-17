"""Slot lifecycle under serializable test transactions; not live Spanner evidence."""

import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

from context_graph.adapters.spanner.tenant_control import TenantFenceError
from context_graph.workbench.spanner_pool import (
    DATA_KEYS,
    DedicatedSlot,
    SandboxPool,
    SlotOwnershipError,
    SlotUnavailableError,
)

RESOURCE = "projects/test-project/instances/test-instance/databases/dedicated-sandbox"
DIGEST = "sha256:" + "a" * 64
KEYS = {**DATA_KEYS, "TenantControl": ("control_id",), "WorkbenchSandbox": ("slot_id",)}


class TransactionDatabase:
    name = RESOURCE

    def __init__(self):
        self.rows = {name: {} for name in KEYS}
        self.lock = threading.Lock()
        self.now = datetime(2026, 11, 3, tzinfo=UTC)
        self.fail_delete = False

    @contextmanager
    def snapshot(self, **kwargs):
        yield self

    def run_in_transaction(self, callback, **kwargs):
        with self.lock:
            before = copy.deepcopy(self.rows)
            try:
                return callback(self)
            except BaseException:
                self.rows = before
                raise

    def read(self, table, columns, keys, limit=None):
        selected = list(self.rows[table]) if keys.all_ else [tuple(k) for k in keys.keys]
        return [
            [self.rows[table][key][c] for c in columns]
            for key in selected[:limit]
            if key in self.rows[table]
        ]

    def insert(self, table, columns, values):
        for values_row in values:
            row = dict(zip(columns, values_row, strict=True))
            key = tuple(row[k] for k in KEYS[table])
            assert key not in self.rows[table]
            self.rows[table][key] = row

    def update(self, table, columns, values):
        for values_row in values:
            row = dict(zip(columns, values_row, strict=True))
            key = tuple(row[k] for k in KEYS[table])
            assert key in self.rows[table]
            self.rows[table][key].update(row)

    def delete(self, table, keys):
        if self.fail_delete:
            raise RuntimeError("injected cleanup failure")
        for key in keys.keys:
            self.rows[table].pop(tuple(key), None)

    def execute_sql(self, query):
        if "INFORMATION_SCHEMA.TABLES" in query:
            return [[name] for name in self.rows]
        if query == "SELECT CURRENT_TIMESTAMP()":
            return [[self.now]]
        assert query.startswith("SELECT 1 FROM ") and query.endswith(" LIMIT 1")
        table = query.split()[3]
        return [[1]] if self.rows[table] else []


def ready():
    db = TransactionDatabase()
    slot = DedicatedSlot(db, resource=RESOURCE, pool_id="workbench")
    slot.register_empty()
    return db, slot


def test_registration_never_adopts_existing_ownership_or_data():
    db = TransactionDatabase()
    db.rows["Events"][("customer",)] = {"event_id": "customer"}
    slot = DedicatedSlot(db, resource=RESOURCE, pool_id="workbench")
    with pytest.raises(SlotOwnershipError, match="empty"):
        slot.register_empty()
    assert db.rows["Events"] and not db.rows["TenantControl"]
    db.rows["Events"].clear()
    slot.register_empty()
    with pytest.raises(SlotOwnershipError, match="adoption"):
        slot.register_empty()


def test_registration_refuses_an_unrelated_database_even_when_engine_tables_are_empty():
    db = TransactionDatabase()
    db.rows["CustomerInvoices"] = {("private",): {"amount": 42}}
    slot = DedicatedSlot(db, resource=RESOURCE, pool_id="workbench")
    with pytest.raises(SlotOwnershipError, match="dedicated schema"):
        slot.register_empty()
    assert not db.rows["TenantControl"] and db.rows["CustomerInvoices"]


def test_concurrent_claims_have_one_winner_and_other_pool_cannot_claim():
    db, slot = ready()

    def claim(index):
        try:
            return slot.claim(run_id=f"run-{index}", bundle_digest=DIGEST)
        except SlotUnavailableError:
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(claim, range(8)))
    assert len([r for r in results if r is not None]) == 1
    other = DedicatedSlot(db, resource=RESOURCE, pool_id="other")
    with pytest.raises(SlotOwnershipError, match="registered"):
        other.claim(run_id="other-run", bundle_digest=DIGEST)


def test_cleanup_fences_old_writer_and_preserves_control_before_reuse():
    db, slot = ready()
    first = slot.claim(run_id="run-a", bundle_digest=DIGEST)
    first.fence.check(db, operation="processing")
    db.rows["Events"][("shared-id",)] = {"event_id": "shared-id"}
    db.rows["GraphNodes"][("Incident", "shared-id")] = {"label": "Incident", "node_id": "shared-id"}
    slot.cleanup(first)
    assert all(not db.rows[table] for table in DATA_KEYS)
    assert db.rows["TenantControl"] and db.rows["WorkbenchSandbox"]
    with pytest.raises(TenantFenceError):
        first.fence.check(db, operation="processing")
    second = slot.claim(run_id="run-b", bundle_digest=DIGEST)
    assert second.fence.epoch > first.fence.epoch
    db.rows["Events"][("shared-id",)] = {"event_id": "shared-id"}
    with pytest.raises(SlotOwnershipError, match="superseded"):
        slot.cleanup(first)
    assert db.rows["Events"]  # A stale cleanup cannot delete the new run.
    with pytest.raises(TenantFenceError):
        first.fence.check(db, operation="processing")
    second.fence.check(db, operation="processing")


def test_cleanup_failure_quarantines_until_verified_retry():
    db, slot = ready()
    lease = slot.claim(run_id="run-a", bundle_digest=DIGEST)
    db.rows["Events"][("one",)] = {"event_id": "one"}
    db.fail_delete = True
    with pytest.raises(RuntimeError, match="injected"):
        slot.cleanup(lease)
    assert db.rows["WorkbenchSandbox"][("active",)]["state"] == "quarantined"
    with pytest.raises(SlotUnavailableError):
        slot.claim(run_id="run-b", bundle_digest=DIGEST)
    with pytest.raises(TenantFenceError):
        lease.fence.check(db, operation="processing")
    db.fail_delete = False
    slot.cleanup(lease)
    assert not db.rows["Events"]
    slot.claim(run_id="run-b", bundle_digest=DIGEST)


def test_expired_process_is_revoked_not_assumed_stopped_or_empty():
    db, slot = ready()
    lease = slot.claim(run_id="run-a", bundle_digest=DIGEST, lease_seconds=30)
    assert slot.recover_expired() is None
    db.rows["Events"][("one",)] = {"event_id": "one"}
    db.now += timedelta(seconds=31)
    assert slot.recover_expired() == lease
    assert db.rows["Events"]
    with pytest.raises(TenantFenceError):
        lease.fence.check(db, operation="processing")
    with pytest.raises(SlotUnavailableError):
        slot.claim(run_id="run-b", bundle_digest=DIGEST)
    slot.cleanup(lease)
    slot.claim(run_id="run-b", bundle_digest=DIGEST)


def test_pool_capacity_is_explicit_and_busy_slots_do_not_block_free_siblings():
    first_db, first = ready()
    second_db = TransactionDatabase()
    second_db.name = RESOURCE + "-two"
    second = DedicatedSlot(second_db, resource=second_db.name, pool_id="workbench")
    second.register_empty()
    pool = SandboxPool((first, second))
    assert pool.status()["available"] == 2
    a, lease_a = pool.claim(run_id="a", bundle_digest=DIGEST)
    b, _lease_b = pool.claim(run_id="b", bundle_digest=DIGEST)
    assert a.resource != b.resource
    assert pool.status()["available"] == 0
    with pytest.raises(SlotUnavailableError, match="All sandbox"):
        pool.claim(run_id="c", bundle_digest=DIGEST)
    first_db.fail_delete = True
    first_db.rows["Events"][("one",)] = {"event_id": "one"}
    with pytest.raises(RuntimeError):
        a.cleanup(lease_a)
    assert pool.status()["slots"][0]["state"] == "quarantined"
    with pytest.raises(ValueError, match="distinct"):
        SandboxPool((first, first))


def test_status_never_advertises_a_ready_slot_with_missing_or_wrong_ownership():
    db, slot = ready()
    db.rows["TenantControl"][("active",)]["tenant_id"] = "customer"
    status = SandboxPool((slot,)).status()
    assert status["available"] == 0
    assert status["slots"][0]["state"] == "unavailable"
    assert "run_id" not in status["slots"][0]
    with pytest.raises(SlotOwnershipError):
        slot.claim(run_id="a", bundle_digest=DIGEST)
