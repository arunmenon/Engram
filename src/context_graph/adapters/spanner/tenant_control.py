"""Protected database ownership and transaction-local interpretation checks.

This table is deliberately outside GraphNodes and generic graph maintenance.
Creating its schema and adopting a database are explicit operator operations;
ordinary startup and transactions never create or repair ownership.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from context_graph.ports.errors import RuntimeFencedError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from context_graph.tenancy import TenantBinding

TENANT_CONTROL_DDL = """CREATE TABLE TenantControl (
    control_id STRING(16) NOT NULL,
    tenant_id STRING(128) NOT NULL,
    database_resource STRING(MAX) NOT NULL,
    binding_id STRING(128) NOT NULL,
    epoch INT64 NOT NULL,
    bundle_digest STRING(80) NOT NULL,
    serving_state STRING(16) NOT NULL
) PRIMARY KEY (control_id)"""

_COLUMNS = (
    "tenant_id",
    "database_resource",
    "binding_id",
    "epoch",
    "bundle_digest",
    "serving_state",
)


class TenantFenceError(RuntimeFencedError):
    """Control-plane refusal; never an event error to acknowledge/dead-letter."""


def control_statement_matches(expected: str, observed: str) -> bool:
    """Spanner canonicalizes CREATE TABLE with a trailing column-list comma."""
    from context_graph.adapters.spanner.entity_index import ddl_statement_matches

    def normalize(statement: str) -> str:
        return re.sub(r",\s*\)(\s*PRIMARY\s+KEY\s*\()", r")\1", statement, flags=re.I)

    return ddl_statement_matches(normalize(expected), normalize(observed))


def verify_control_schema(database: Any) -> None:
    """Refuse missing/incompatible control schema without running repair DDL."""
    expected = {
        "control_id": "STRING(16)",
        "tenant_id": "STRING(128)",
        "database_resource": "STRING(MAX)",
        "binding_id": "STRING(128)",
        "epoch": "INT64",
        "bundle_digest": "STRING(80)",
        "serving_state": "STRING(16)",
    }
    with database.snapshot(multi_use=True) as snapshot:
        columns = list(
            snapshot.execute_sql(
                "SELECT COLUMN_NAME, SPANNER_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = '' AND TABLE_NAME = 'TenantControl'"
            )
        )
        key = list(
            snapshot.execute_sql(
                "SELECT COLUMN_NAME, COLUMN_ORDERING FROM INFORMATION_SCHEMA.INDEX_COLUMNS "
                "WHERE TABLE_SCHEMA = '' AND TABLE_NAME = 'TenantControl' "
                "AND INDEX_NAME = 'PRIMARY_KEY' ORDER BY ORDINAL_POSITION"
            )
        )
    actual = {name: value_type for name, value_type, nullable in columns if nullable == "NO"}
    if (
        actual != expected
        or len(columns) != len(expected)
        or [list(row) for row in key] != [["control_id", "ASC"]]
    ):
        raise TenantFenceError("Tenant control schema is missing or incompatible")


@dataclass(frozen=True)
class TenantFence:
    tenant_id: str
    database_resource: str
    binding_id: str
    epoch: int
    bundle_digest: str

    def __post_init__(self) -> None:
        if (
            not self.tenant_id
            or not self.binding_id
            or type(self.epoch) is not int
            or self.epoch < 1
            or not self.bundle_digest.startswith("sha256:")
            or len(self.bundle_digest) != 71
        ):
            raise ValueError("Invalid tenant fence identity")

    @classmethod
    def from_binding(cls, binding: TenantBinding) -> TenantFence:
        return cls(
            binding.tenant_id,
            binding.database_resource,
            binding.binding_id,
            binding.epoch,
            binding.bundle_digest,
        )

    def _identity(self) -> tuple[Any, ...]:
        return (
            self.tenant_id,
            self.database_resource,
            self.binding_id,
            self.epoch,
            self.bundle_digest,
        )

    def check(
        self, transaction: Any, *, operation: Literal["admission", "processing", "read"]
    ) -> None:
        """Read the owner in the SAME transaction/snapshot as the guarded effect."""
        from google.cloud.spanner_v1 import KeySet

        if operation not in ("admission", "processing", "read"):
            raise ValueError("Unknown tenant fence operation")
        rows = list(transaction.read("TenantControl", _COLUMNS, KeySet(keys=[["active"]])))
        if len(rows) != 1 or tuple(rows[0][:-1]) != self._identity():
            raise TenantFenceError("Tenant ownership or interpretation does not match")
        allowed = ("active", "draining") if operation == "processing" else ("active",)
        if rows[0][-1] not in allowed:
            raise TenantFenceError("Tenant operation is unavailable in this serving state")

    def run(
        self,
        database: Any,
        callback: Callable[[Any], Any],
        *,
        operation: Literal["admission", "processing"],
    ) -> Any:
        """Spanner retry re-executes the check, never just the mutation callback."""
        self.check_database(database)

        def guarded(transaction: Any) -> Any:
            self.check(transaction, operation=operation)
            return callback(transaction)

        return database.run_in_transaction(guarded)

    def check_database(self, database: Any) -> None:
        if database.name != self.database_resource:
            raise TenantFenceError("Tenant database handle does not match")

    def bootstrap(self, database: Any, *, adopt_existing: bool = False) -> None:
        """Explicit operator call; never overwrites an existing owner or epoch.

        Without explicit adoption, refuse populated application tables. Existing
        matching ownership is idempotent only while active. Schema installation
        is separate and cannot be triggered by this method.
        """
        from google.cloud.spanner_v1 import KeySet

        self.check_database(database)

        def initialize(transaction: Any) -> None:
            rows = list(transaction.read("TenantControl", _COLUMNS, KeySet(keys=[["active"]])))
            if rows:
                self.check(transaction, operation="admission")
                return
            if not adopt_existing:
                for table in (
                    "Events",
                    "GraphNodes",
                    "GraphEdges",
                    "ConsumerGroups",
                    "ConsumerCursors",
                    "ConsumerDeliveries",
                    "ConsumerDeadLetters",
                ):
                    if list(transaction.execute_sql(f"SELECT 1 FROM {table} LIMIT 1")):
                        raise TenantFenceError(
                            "Populated tenant database requires explicit adoption"
                        )
            transaction.insert(
                "TenantControl",
                ("control_id", *_COLUMNS),
                [("active", *self._identity(), "active")],
            )

        database.run_in_transaction(initialize)


@contextmanager
def tenant_snapshot(
    database: Any, fence: TenantFence | None, *, operation: Literal["read", "processing"] = "read"
) -> Iterator[Any]:
    """Check control and consume application rows in one strong multi-use snapshot.

    This protects interpretation at the snapshot time; external callers still
    need a fresh active check before releasing a response spanning several reads.
    """
    if operation not in ("read", "processing"):
        raise ValueError("Unknown tenant read operation")
    if fence is not None:
        fence.check_database(database)
        with database.snapshot(multi_use=True) as snapshot:
            fence.check(snapshot, operation=operation)
            yield snapshot
    else:
        with database.snapshot() as snapshot:
            yield snapshot
