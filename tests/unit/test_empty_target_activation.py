"""Transaction-local empty-target admission and exact cleanup, no cloud."""

import copy
from dataclasses import replace

import pytest
from scripts.engram_spanner_empty_activation import (
    KEYS,
    RESOURCE,
    ActivationRefusedError,
    activate_empty_target,
    clean_registered_target,
    freeze_target,
)

from tests.unit.test_tenant_catalog import bind, configuration


def binding():
    settings = configuration("engram-compat-target")
    return replace(
        bind(tenant="compat-control", settings=settings),
        binding_id="compat-control-binding",
        epoch=7,
    )


def owner():
    return ["compat-control", RESOURCE, "compat-control-binding", 6, "sha256:" + "a" * 64, "frozen"]


class Transaction:
    def __init__(self, db):
        self.owner = copy.deepcopy(db.owner)
        self.rows = copy.deepcopy(db.rows)
        self.effects = []

    def read(self, table, columns, keys):
        assert table == "TenantControl"
        return [self.owner]

    def execute_sql(self, sql):
        table = sql.split(" FROM ")[1]
        return sorted(self.rows[table])

    def update(self, table, columns, rows):
        assert table == "TenantControl"
        self.owner = list(rows[0][1:])
        self.effects.append("control")

    def delete(self, table, keys):
        for key in keys.keys:
            self.rows[table].discard(tuple(key))
        self.effects.append(table)


class Database:
    name = RESOURCE

    def __init__(self):
        self.owner = owner()
        self.rows = {table: set() for table in KEYS}
        self.effects = []
        self.retry = None

    def run_in_transaction(self, callback):
        tx = Transaction(self)
        result = callback(tx)
        if self.retry:
            self.retry(self)
            self.retry = None
            tx = Transaction(self)
            result = callback(tx)
        self.owner, self.rows = tx.owner, tx.rows
        self.effects.extend(tx.effects)
        return result


def test_activation_and_exact_completed_intent_are_idempotent():
    db = Database()
    old = owner()
    target = binding()
    expected = [*old[:3], 7, target.bundle_digest, "active"]
    assert activate_empty_target(db, old, target) == expected
    assert activate_empty_target(db, old, target) == expected
    assert db.effects == ["control"]
    frozen = freeze_target(db, expected)
    assert freeze_target(db, expected) == frozen
    restored = activate_empty_target(db, frozen, replace(target, epoch=8))
    assert restored[3] == 8 and restored[-1] == "active"


@pytest.mark.parametrize("table", KEYS)
def test_any_populated_table_refuses_atomically(table):
    db = Database()
    db.rows[table].add(tuple("x" for _ in KEYS[table]))
    with pytest.raises(ActivationRefusedError):
        activate_empty_target(db, owner(), binding())
    assert db.owner == owner() and not db.effects


@pytest.mark.parametrize("fault", ["resource", "identity", "epoch", "active", "changed_owner"])
def test_wrong_authority_never_adopted(fault):
    db = Database()
    expected = owner()
    target = binding()
    if fault == "resource":
        db.name = RESOURCE + "-other"
    elif fault == "identity":
        target = replace(target, tenant_id="other")
    elif fault == "epoch":
        target = replace(target, epoch=9)
    elif fault == "active":
        expected[-1] = "active"
    else:
        db.owner[4] = "sha256:" + "b" * 64
    with pytest.raises(ActivationRefusedError):
        activate_empty_target(db, expected, target)
    assert not db.effects


@pytest.mark.parametrize("fault", ["row", "owner"])
def test_transaction_retry_rechecks_empty_state_and_owner(fault):
    db = Database()

    def change(db):
        if fault == "row":
            db.rows["Events"].add(("unexpected",))
        else:
            db.owner[3] = 99

    db.retry = change
    with pytest.raises(ActivationRefusedError):
        activate_empty_target(db, owner(), binding())
    assert not db.effects


def test_cleanup_only_registered_keys_and_refuses_unknowns_before_deletion():
    db = Database()
    db.rows["Events"] = {("owned",), ("foreign",)}
    allowed = {table: [] for table in KEYS}
    allowed["Events"] = [["owned"]]
    with pytest.raises(ActivationRefusedError):
        clean_registered_target(db, owner(), allowed)
    assert not db.effects and len(db.rows["Events"]) == 2
    db.rows["Events"].remove(("foreign",))
    assert clean_registered_target(db, owner(), allowed)["Events"] == 1
    assert clean_registered_target(db, owner(), allowed)["Events"] == 0
    assert not any(db.rows.values())
