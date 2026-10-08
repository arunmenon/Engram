"""Privileged harness-only CAS for the empty reserved experiment database.

Never used by normal startup. No DDL, adoption of observations, or history grants.
Intent persistence and SDK-thread settlement belong to the tracked caller.
"""

from __future__ import annotations

from engram_experiment_support import CONTROL_COLUMNS as COLUMNS
from google.cloud.spanner_v1 import KeySet

RESOURCE = "projects/portiq-mvp/instances/engram-experiment/databases/engram-compat-target"
KEYS = {
    "Events": ("event_id",),
    "GraphNodes": ("label", "node_id"),
    "GraphEdges": ("src_label", "src_id", "edge_type", "dst_label", "dst_id"),
    "ConsumerGroups": ("group_name",),
    "ConsumerCursors": ("group_name", "shard"),
    "ConsumerDeliveries": ("group_name", "event_id"),
    "ConsumerDeadLetters": ("group_name", "event_id"),
}


class ActivationRefusedError(RuntimeError):
    pass


def validate_target(database, owner):
    if (
        database.name != RESOURCE
        or len(owner) != 6
        or owner[1] != RESOURCE
        or owner[0] != "compat-control"
        or owner[2] != "compat-control-binding"
    ):
        raise ActivationRefusedError("Unrelated reserved-target authority")


def owner_at(transaction):
    rows = list(transaction.read("TenantControl", COLUMNS, KeySet(keys=[["active"]])))
    if len(rows) != 1:
        raise ActivationRefusedError("Missing or ambiguous target authority")
    return list(rows[0])


def application_keys(transaction):
    return {
        table: {
            tuple(row)
            for row in transaction.execute_sql(f"SELECT {', '.join(columns)} FROM {table}")
        }
        for table, columns in KEYS.items()
    }


def freeze_target(database, expected):
    validate_target(database, expected)
    if expected[-1] != "active":
        raise ActivationRefusedError("Freeze requires exact active predecessor")
    intended = [*expected[:-1], "frozen"]

    def work(tx):
        observed = owner_at(tx)
        if observed == intended:
            return intended  # Exact known completed intent, never an observed new epoch.
        if observed != expected:
            raise ActivationRefusedError("Owner changed before freeze")
        tx.update("TenantControl", ["control_id", *COLUMNS], [["active", *intended]])
        return intended

    return database.run_in_transaction(work)


def activate_empty_target(database, expected, target_binding):
    validate_target(database, expected)
    from dataclasses import replace

    from context_graph.adapters.spanner.tenant_control import TenantFence

    checked = replace(target_binding)
    intended = [*TenantFence.from_binding(checked)._identity(), "active"]
    validate_target(database, intended)
    if expected[-1] != "frozen" or intended[:3] != expected[:3] or intended[3] != expected[3] + 1:
        raise ActivationRefusedError("Activation requires frozen consecutive predecessor")

    def work(tx):
        observed = owner_at(tx)
        if observed not in (expected, intended):
            raise ActivationRefusedError("Owner changed before activation")
        if any(application_keys(tx).values()):
            raise ActivationRefusedError("Populated target requires historical compatibility")
        if observed != intended:
            tx.update("TenantControl", ["control_id", *COLUMNS], [["active", *intended]])
        return intended

    return database.run_in_transaction(work)


def clean_registered_target(database, expected_frozen, allowed_keys):
    validate_target(database, expected_frozen)
    if expected_frozen[-1] != "frozen" or set(allowed_keys) != set(KEYS):
        raise ActivationRefusedError("Cleanup requires frozen exact ownership manifest")
    allowed = {table: {tuple(key) for key in keys} for table, keys in allowed_keys.items()}
    if any(len(key) != len(KEYS[table]) for table, keys in allowed.items() for key in keys):
        raise ActivationRefusedError("Malformed cleanup key")

    def work(tx):
        if owner_at(tx) != expected_frozen:
            raise ActivationRefusedError("Owner changed before cleanup")
        present = application_keys(tx)
        if any(present[table] - allowed[table] for table in KEYS):
            raise ActivationRefusedError("Unexpected application keys; cleanup refused")
        for table, keys in present.items():
            if keys:
                tx.delete(table, KeySet(keys=[list(key) for key in sorted(keys)]))
        return {table: len(keys) for table, keys in present.items()}

    return database.run_in_transaction(work)
