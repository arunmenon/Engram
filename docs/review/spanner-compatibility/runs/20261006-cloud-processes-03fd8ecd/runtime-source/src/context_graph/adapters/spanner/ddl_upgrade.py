"""Recover one recorded Entity-index DDL attempt by its database operation name."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from context_graph.adapters.spanner.entity_index import (
    ENTITY_INDEX_DDL,
    MEMBERSHIP_DDL,
    EntityIndexUpgradeError,
    PendingEntityIndexUpgradeError,
    ddl_statement_matches,
    plan_entity_index_upgrade,
)


@dataclass
class EntityIndexAttempt:
    database: str
    dimensions: int
    operation_id: str
    statements: list[str] | None = None
    digest: str | None = None
    state: str = "registered"
    observed: bool = False
    submissions: int = 0
    last_rpc_error: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    predecessor: dict[str, Any] | None = None
    migration: str = "entity_ann_v1"

    @property
    def name(self) -> str:
        return f"{self.database}/operations/{self.operation_id}"

    def record(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self, database: str, dimensions: int) -> None:
        if (
            type(self.submissions) is not int
            or not 0 <= self.submissions <= 2
            or self.state
            not in {
                "registered",
                "prepared",
                "submitting",
                "uncertain",
                "observed",
                "pending",
                "failed",
                "ready",
                "noop",
                "unresolved",
            }
            or (self.statements is None and self.digest is not None)
        ):
            raise EntityIndexUpgradeError("Invalid persisted attempt state")
        if (
            self.database != database
            or self.dimensions != dimensions
            or self.migration != "entity_ann_v1"
            or not re.fullmatch(r"[a-z][a-z0-9_]{5,127}", self.operation_id)
        ):
            raise EntityIndexUpgradeError("Attempt target/version/operation ID mismatch")
        if self.statements is not None and self.digest != statement_digest(self.statements):
            raise EntityIndexUpgradeError("Attempt statement digest mismatch")
        allowed = (f"ALTER TABLE GraphNodes ADD COLUMN {MEMBERSHIP_DDL}", ENTITY_INDEX_DDL)
        if self.statements is not None and tuple(self.statements) not in (
            (),
            allowed,
            allowed[:1],
            allowed[1:],
        ):
            raise EntityIndexUpgradeError("Attempt contains unsupported migration statements")


def statement_digest(statements: list[str]) -> str:
    return hashlib.sha256(json.dumps(statements, separators=(",", ":")).encode()).hexdigest()


def upgrade_entity_index(
    database: Any,
    dimensions: int,
    *,
    attempt: EntityIndexAttempt,
    operations_client: Any,
    persist_attempt: Callable[[dict[str, Any]], None],
    timeout_s: float = 60,
) -> list[str]:
    """No listing, changing IDs, replanning uncertain requests, or silent repair.

    Persist submission intent before RPC. Recovery always GETs the same name;
    an absent uncertain request permits one identical same-ID replay only.
    """
    from google.api_core.exceptions import (
        AlreadyExists,
        DeadlineExceeded,
        NotFound,
        ServiceUnavailable,
    )
    from google.api_core.operation import from_gapic
    from google.cloud.spanner_admin_database_v1.types import UpdateDatabaseDdlMetadata
    from google.protobuf.empty_pb2 import Empty

    from context_graph.adapters.spanner.schema import schema_differences

    attempt.validate(database.name, dimensions)
    persist_attempt(attempt.record())

    def save(state: str, error: dict[str, Any] | None = None) -> None:
        attempt.state, attempt.error = state, error
        persist_attempt(attempt.record())

    def fetch(name: str) -> Any:
        return operations_client.get_operation(name, timeout=min(timeout_s, 10))

    def future_for(raw: Any, record: EntityIndexAttempt) -> Any:
        if raw.name != record.name:
            raise EntityIndexUpgradeError("Returned operation name mismatch")
        future = from_gapic(raw, operations_client, Empty, metadata_type=UpdateDatabaseDdlMetadata)
        metadata = future.metadata
        if (
            metadata is None
            or metadata.database != record.database
            or record.statements is None
            or len(metadata.statements) != len(record.statements)
            or any(
                not ddl_statement_matches(expected, observed)
                for expected, observed in zip(record.statements, metadata.statements, strict=True)
            )
        ):
            raise EntityIndexUpgradeError("Returned operation metadata/request mismatch")
        return future

    # A new retry ID is permitted only with a recorded and remotely confirmed
    # terminal failed predecessor, never merely a local timeout flag.
    if attempt.predecessor is not None:
        parent = EntityIndexAttempt(**attempt.predecessor)
        parent.validate(database.name, dimensions)
        raw_parent = fetch(parent.name)
        future_for(raw_parent, parent)
        if not raw_parent.done or not raw_parent.error.code or parent.name == attempt.name:
            raise EntityIndexUpgradeError("Retry predecessor is not terminal failed")

    submitted_here = False
    for _replay in range(2):
        try:
            raw = fetch(attempt.name)
        except NotFound:
            if attempt.observed:
                save("unresolved", {"kind": "observed_operation_disappeared"})
                raise EntityIndexUpgradeError("Previously observed operation disappeared") from None
            if attempt.state == "noop":
                if schema_differences(database, dimensions):
                    raise EntityIndexUpgradeError(
                        "Previously checked no-op schema changed"
                    ) from None
                return []
            if attempt.state in ("ready", "failed", "unresolved"):
                raise EntityIndexUpgradeError(
                    "Recorded terminal attempt requires reconciliation"
                ) from None
            if attempt.statements is None:
                plan = plan_entity_index_upgrade(database, dimensions)
                attempt.statements, attempt.digest = plan, statement_digest(plan)
                save("prepared")
            if not attempt.statements:
                differences = schema_differences(database, dimensions)
                if differences:
                    save("failed", {"kind": "schema", "differences": differences})
                    raise EntityIndexUpgradeError("Target schema not ready") from None
                save("noop")
                return []
            if attempt.submissions >= 2:
                save("uncertain", {"kind": "submission_limit"})
                raise PendingEntityIndexUpgradeError([attempt.name]) from None
            attempt.submissions += 1
            save("submitting")
            submitted_here = True
            try:
                future = database.update_ddl(attempt.statements, operation_id=attempt.operation_id)
                raw = future.operation
            except (AlreadyExists, DeadlineExceeded, ServiceUnavailable) as exc:
                save("uncertain", {"kind": "submission_rpc", "type": type(exc).__name__})
                continue
            except Exception as exc:
                save("uncertain", {"kind": "submission_rpc", "type": type(exc).__name__})
                raise
        except Exception as exc:
            attempt.last_rpc_error = {"kind": "get_rpc", "type": type(exc).__name__}
            persist_attempt(attempt.record())
            raise

        # Validation precedes observed status: a name collision is not ours.
        try:
            future = future_for(raw, attempt)
        except EntityIndexUpgradeError:
            save("unresolved", {"kind": "operation_identity"})
            raise
        attempt.observed = True
        save("observed")
        try:
            future.result(timeout=timeout_s)
        except TimeoutError:
            save("pending")
            raise PendingEntityIndexUpgradeError([attempt.name]) from None
        except Exception as exc:
            operation = future.operation
            if operation.done and operation.error.code:
                save(
                    "failed",
                    {
                        "kind": "operation",
                        "code": operation.error.code,
                        "message": operation.error.message,
                    },
                )
            else:
                save("pending", {"kind": "poll_rpc", "type": type(exc).__name__})
            raise
        differences = schema_differences(database, dimensions)
        if differences:
            save("failed", {"kind": "schema", "differences": differences})
            raise EntityIndexUpgradeError("Successful operation left target schema incompatible")
        save("ready")
        return list(attempt.statements) if submitted_here else []
    raise PendingEntityIndexUpgradeError([attempt.name])
