"""Exclusive dedicated-database slots, using Spanner transactions and tenant fences.

Schema installation and initial registration are explicit provisioning operations.
Ordinary claims never adopt a database. Expiry revokes authority; it never makes
unclean data available to another run. No database is dropped by this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast

from context_graph.adapters.spanner.lifecycle import key_set
from context_graph.adapters.spanner.tenant_control import TenantFence

POOL_DDL = """CREATE TABLE WorkbenchSandbox (
    slot_id STRING(16) NOT NULL,
    pool_id STRING(64) NOT NULL,
    state STRING(16) NOT NULL,
    epoch INT64 NOT NULL,
    run_id STRING(128) NOT NULL,
    lease_until TIMESTAMP,
    error_code STRING(64) NOT NULL
) PRIMARY KEY (slot_id)"""

SLOT_COLUMNS = ("pool_id", "state", "epoch", "run_id", "lease_until", "error_code")
OWNER_COLUMNS = (
    "tenant_id",
    "database_resource",
    "binding_id",
    "epoch",
    "bundle_digest",
    "serving_state",
)
# Keep control rows outside cleanup. Fixed identifiers only; never interpolate UI input.
DATA_KEYS = {
    "GraphEdges": ("src_label", "src_id", "edge_type", "dst_label", "dst_id"),
    "GraphNodes": ("label", "node_id"),
    "ConsumerDeadLetters": ("group_name", "event_id"),
    "ConsumerDeliveries": ("group_name", "event_id"),
    "ConsumerCursors": ("group_name", "shard"),
    "ConsumerGroups": ("group_name",),
    "Events": ("event_id",),
}


class SlotUnavailableError(RuntimeError):
    """No usable capacity; not an event-processing failure."""


class SlotOwnershipError(RuntimeError):
    """The database or claim is not owned by this sandbox operation."""


@dataclass(frozen=True)
class Lease:
    pool_id: str
    fence: TenantFence


class DedicatedSlot:
    def __init__(self, database: Any, *, resource: str, pool_id: str):
        if database.name != resource or not re.fullmatch(
            r"projects/[a-z0-9-]+/instances/[a-z0-9-]+/databases/[a-z0-9-]+", resource
        ):
            raise ValueError("Sandbox database must match its configured resource")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", pool_id):
            raise ValueError("Invalid sandbox pool identity")
        self.database = database
        self.resource = resource
        self.pool_id = pool_id

    def status(self) -> dict[str, Any]:
        with self.database.snapshot(multi_use=True) as snapshot:
            row = self._slot(snapshot)
            owner = self._read(snapshot, "TenantControl", OWNER_COLUMNS)
            if (
                owner is None
                or owner[0:2] != ["wb-" + self.pool_id, self.resource]
                or owner[3] != row[2]
            ):
                raise SlotOwnershipError("Sandbox status lacks matching database ownership")
            expected_state = "active" if row[1] == "leased" else "frozen"
            if owner[-1] != expected_state or (row[1] != "ready" and owner[2] != row[3]):
                raise SlotOwnershipError("Sandbox status is inconsistent with its write fence")
        return {
            "resource": self.resource,
            "state": row[1],
            "epoch": row[2],
            "run_id": row[3] or None,
            "lease_until": row[4],
            "reason": row[5] or None,
        }

    @staticmethod
    def _read(transaction: Any, table: str, columns: tuple[str, ...]) -> list[Any] | None:

        rows = list(transaction.read(table, columns, key_set(keys=[["active"]])))
        if len(rows) > 1:
            raise SlotOwnershipError("Ambiguous sandbox control record")
        return list(rows[0]) if rows else None

    def _slot(self, transaction: Any) -> list[Any]:
        row = self._read(transaction, "WorkbenchSandbox", SLOT_COLUMNS)
        if row is None or row[0] != self.pool_id:
            raise SlotOwnershipError("Database is not registered to this sandbox pool")
        if (
            row[1] not in {"ready", "leased", "cleaning", "quarantined"}
            or type(row[2]) is not int
            or row[2] < 1
        ):
            raise SlotOwnershipError("Invalid sandbox control state")
        return row

    def _owned(self, transaction: Any, lease: Lease) -> list[Any]:
        if lease.pool_id != self.pool_id:
            raise SlotOwnershipError("Wrong pool claim")
        lease.fence.check_database(self.database)
        row = self._slot(transaction)
        owner = self._read(transaction, "TenantControl", OWNER_COLUMNS)
        if (row[2], row[3]) != (lease.fence.epoch, lease.fence.binding_id) or (
            owner is None or tuple(owner[:-1]) != lease.fence._identity()
        ):
            raise SlotOwnershipError("Sandbox claim has been superseded")
        return row

    def _write_slot(self, transaction: Any, row: list[Any]) -> None:
        transaction.update("WorkbenchSandbox", ("slot_id", *SLOT_COLUMNS), [("active", *row)])

    @staticmethod
    def _empty(transaction: Any) -> bool:
        return not any(
            list(transaction.execute_sql(f"SELECT 1 FROM {t} LIMIT 1")) for t in DATA_KEYS
        )

    def register_empty(self) -> None:
        """Provisioner only: refuse customer ownership and populated databases."""
        with self.database.snapshot() as snapshot:
            tables = {
                row[0]
                for row in snapshot.execute_sql(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA = '' AND TABLE_TYPE = 'BASE TABLE'"
                )
            }
        if tables != {*DATA_KEYS, "TenantControl", "WorkbenchSandbox"}:
            raise SlotOwnershipError("Sandbox registration requires the dedicated schema only")

        def register(transaction: Any) -> None:
            slot = self._read(transaction, "WorkbenchSandbox", SLOT_COLUMNS)
            owner = self._read(transaction, "TenantControl", OWNER_COLUMNS)
            if slot is not None or owner is not None:
                raise SlotOwnershipError(
                    "Database already has control records; adoption is forbidden"
                )
            if not self._empty(transaction):
                raise SlotOwnershipError("Sandbox registration requires an empty database")
            transaction.insert(
                "WorkbenchSandbox",
                ("slot_id", *SLOT_COLUMNS),
                [("active", self.pool_id, "ready", 1, "", None, "")],
            )
            transaction.insert(
                "TenantControl",
                ("control_id", *OWNER_COLUMNS),
                [
                    (
                        "active",
                        "wb-" + self.pool_id,
                        self.resource,
                        "unassigned",
                        1,
                        "sha256:" + "0" * 64,
                        "frozen",
                    )
                ],
            )

        self.database.run_in_transaction(register, timeout_secs=15)

    def claim(self, *, run_id: str, bundle_digest: str, lease_seconds: int = 300) -> Lease:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", run_id):
            raise ValueError("Invalid run identity")
        if not 30 <= lease_seconds <= 1200:
            raise ValueError("Sandbox lease must be between 30 and 1200 seconds")

        def acquire(transaction: Any) -> Lease:
            row = self._slot(transaction)
            if row[1] != "ready":
                raise SlotUnavailableError(f"Sandbox slot is {row[1]}")
            owner = self._read(transaction, "TenantControl", OWNER_COLUMNS)
            if (
                owner is None
                or owner[0:2] != ["wb-" + self.pool_id, self.resource]
                or (owner[3] != row[2] or owner[-1] != "frozen")
            ):
                raise SlotOwnershipError("Ready slot lacks matching frozen ownership")
            if not self._empty(transaction):
                raise SlotOwnershipError("Ready slot contains data; refuse reuse")
            fence = TenantFence(
                "wb-" + self.pool_id, self.resource, run_id, row[2] + 1, bundle_digest
            )
            now = list(transaction.execute_sql("SELECT CURRENT_TIMESTAMP()"))[0][0]
            self._write_slot(
                transaction,
                [
                    self.pool_id,
                    "leased",
                    fence.epoch,
                    run_id,
                    now + timedelta(seconds=lease_seconds),
                    "",
                ],
            )
            transaction.update(
                "TenantControl",
                ("control_id", *OWNER_COLUMNS),
                [("active", *fence._identity(), "active")],
            )
            return Lease(self.pool_id, fence)

        return cast("Lease", self.database.run_in_transaction(acquire, timeout_secs=15))

    def quarantine(self, lease: Lease, code: str = "cleanup_failed") -> None:
        if code not in {"cleanup_failed", "lease_expired", "run_interrupted"}:
            raise ValueError("Unknown quarantine reason")

        def revoke(transaction: Any) -> None:
            row = self._owned(transaction, lease)
            row[1], row[5] = "quarantined", code
            self._write_slot(transaction, row)
            transaction.update(
                "TenantControl",
                ("control_id", *OWNER_COLUMNS),
                [("active", *lease.fence._identity(), "frozen")],
            )

        self.database.run_in_transaction(revoke)

    def cleanup(self, lease: Lease) -> None:
        """Revoke writes first, then bounded deletes, then prove emptiness before reuse."""

        def begin(transaction: Any) -> None:
            row = self._owned(transaction, lease)
            if row[1] not in {"leased", "quarantined", "cleaning"}:
                raise SlotOwnershipError("Claim is not eligible for cleanup")
            row[1] = "cleaning"
            self._write_slot(transaction, row)
            transaction.update(
                "TenantControl",
                ("control_id", *OWNER_COLUMNS),
                [("active", *lease.fence._identity(), "frozen")],
            )

        self.database.run_in_transaction(begin)
        try:
            for table, keys in DATA_KEYS.items():

                def clear_batch(
                    transaction: Any, table: str = table, keys: tuple[str, ...] = keys
                ) -> bool:
                    row = self._owned(transaction, lease)
                    if row[1] != "cleaning":
                        raise SlotOwnershipError("Cleanup authority changed")
                    found = list(transaction.read(table, keys, key_set(all_=True), limit=50))
                    if found:
                        transaction.delete(table, key_set(keys=[list(r) for r in found]))
                    return bool(found)

                for _ in range(1000):
                    if not self.database.run_in_transaction(clear_batch):
                        break
                else:
                    raise RuntimeError("Sandbox cleanup exceeded its bounded work limit")

            def release(transaction: Any) -> None:
                row = self._owned(transaction, lease)
                owner = self._read(transaction, "TenantControl", OWNER_COLUMNS)
                if (
                    row[1] != "cleaning"
                    or owner is None
                    or owner[-1] != "frozen"
                    or not self._empty(transaction)
                ):
                    raise SlotOwnershipError("Sandbox cleanup was not verified")
                self._write_slot(transaction, [self.pool_id, "ready", row[2], "", None, ""])

            self.database.run_in_transaction(release)
        except Exception:
            self.quarantine(lease)
            raise

    def recover_expired(self) -> Lease | None:
        """Fence expired work without assuming its process has stopped. Leave quarantined."""

        def recover(transaction: Any) -> Lease | None:
            row = self._slot(transaction)
            now = list(transaction.execute_sql("SELECT CURRENT_TIMESTAMP()"))[0][0]
            if row[1] not in {"leased", "cleaning"} or row[4] is None or row[4] > now:
                return None
            owner = self._read(transaction, "TenantControl", OWNER_COLUMNS)
            if owner is None:
                raise SlotOwnershipError("Expired slot has no owner")
            lease = Lease(self.pool_id, TenantFence(*owner[:-1]))
            self._owned(transaction, lease)
            row[1], row[5] = "quarantined", "lease_expired"
            self._write_slot(transaction, row)
            transaction.update(
                "TenantControl",
                ("control_id", *OWNER_COLUMNS),
                [("active", *lease.fence._identity(), "frozen")],
            )
            return lease

        return cast("Lease | None", self.database.run_in_transaction(recover))


class SandboxPool:
    """Small configured allowlist; capacity exhaustion never falls back to memory."""

    def __init__(self, slots: tuple[DedicatedSlot, ...]):
        if not slots or len(slots) > 5:
            raise ValueError("Configure between one and five dedicated sandbox slots")
        if len({slot.resource for slot in slots}) != len(slots):
            raise ValueError("Sandbox resources must be distinct")
        if len({slot.pool_id for slot in slots}) != 1:
            raise ValueError("Sandbox slots must share the configured pool identity")
        self.slots = slots

    def claim(
        self, *, run_id: str, bundle_digest: str, lease_seconds: int = 300
    ) -> tuple[DedicatedSlot, Lease]:
        for slot in self.slots:
            try:
                lease = slot.claim(
                    run_id=run_id, bundle_digest=bundle_digest, lease_seconds=lease_seconds
                )
                return slot, lease
            except SlotUnavailableError:
                continue
        raise SlotUnavailableError("All sandbox slots are in use or require cleanup")

    def status(self) -> dict[str, Any]:
        slots = []
        for slot in self.slots:
            try:
                slots.append(slot.status())
            except Exception:
                # An unreachable or unowned resource is never available. Do not
                # expose SDK errors, credentials or another pool's run identity.
                slots.append(
                    {
                        "resource": slot.resource,
                        "state": "unavailable",
                        "reason": "ownership_or_connection_check_failed",
                    }
                )
        return {
            "backend": "spanner",
            "capacity": len(slots),
            "available": sum(s["state"] == "ready" for s in slots),
            "slots": slots,
        }
