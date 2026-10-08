"""Exact database operation recovery without instance-wide listing."""

import copy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import AlreadyExists, DeadlineExceeded, NotFound, PermissionDenied
from google.cloud.spanner_admin_database_v1.types import UpdateDatabaseDdlMetadata
from google.longrunning.operations_pb2 import Operation
from google.protobuf.empty_pb2 import Empty

from context_graph.adapters.spanner.ddl_upgrade import (
    EntityIndexAttempt,
    statement_digest,
    upgrade_entity_index,
)
from context_graph.adapters.spanner.entity_index import (
    EntityIndexUpgradeError,
    PendingEntityIndexUpgradeError,
    plan_entity_index_upgrade,
)
from tests.unit.test_spanner_entity_index import legacy_database

RESOURCE = "projects/p/instances/i/databases/d"


def operation(attempt, *, done=True, error=0, name=None, statements=None):
    raw = Operation(name=name or attempt.name, done=done)
    metadata = UpdateDatabaseDdlMetadata(
        database=attempt.database,
        statements=attempt.statements if statements is None else statements,
    )
    raw.metadata.Pack(UpdateDatabaseDdlMetadata.pb(metadata))
    if done:
        if error:
            raw.error.code, raw.error.message = error, "DDL rejected"
        else:
            raw.response.Pack(Empty())
    return raw


def context():
    db = legacy_database()
    db.name = RESOURCE
    db.list_database_operations.side_effect = AssertionError("instance listing forbidden")
    operations = MagicMock()
    operations.get_operation.side_effect = NotFound("absent")
    attempt = EntityIndexAttempt(RESOURCE, 3, "engram_test_0001")
    records = []
    return db, operations, attempt, records


def apply(db, operations, attempt, records, **kwargs):
    with patch("context_graph.adapters.spanner.schema.schema_differences", return_value=[]):
        return upgrade_entity_index(
            db,
            3,
            attempt=attempt,
            operations_client=operations,
            persist_attempt=lambda record: records.append(copy.deepcopy(record)),
            **kwargs,
        )


def test_record_before_submit_and_resume_same_success_without_new_ddl():
    db, operations, attempt, records = context()

    def submit(statements, operation_id):
        assert records[-1]["state"] == "submitting"
        assert records[-1]["digest"] == statement_digest(statements)
        assert operation_id == attempt.operation_id
        return SimpleNamespace(operation=operation(attempt))

    db.update_ddl.side_effect = submit
    assert len(apply(db, operations, attempt, records)) == 2
    assert attempt.state == "ready"
    restored = EntityIndexAttempt(**records[-1])
    operations.get_operation.side_effect = None
    operations.get_operation.return_value = operation(restored)
    assert apply(db, operations, restored, records) == []
    db.update_ddl.assert_called_once()
    assert operations.get_operation.call_args.args[0] == restored.name


def test_persistence_failure_prevents_cloud_calls():
    db, operations, attempt, _records = context()
    with pytest.raises(OSError):
        upgrade_entity_index(
            db,
            3,
            attempt=attempt,
            operations_client=operations,
            persist_attempt=MagicMock(side_effect=OSError("disk full")),
        )
    db.update_ddl.assert_not_called()
    operations.get_operation.assert_not_called()


@pytest.mark.parametrize("rpc_error", [DeadlineExceeded, AlreadyExists])
def test_lost_response_and_already_exists_recover_exact_known_name(rpc_error):
    db, operations, attempt, records = context()

    def submit(*args, **kwargs):
        operations.get_operation.side_effect = None
        operations.get_operation.return_value = operation(attempt)
        raise rpc_error("uncertain")

    db.update_ddl.side_effect = submit
    assert len(apply(db, operations, attempt, records)) == 2
    assert attempt.state == "ready"
    db.update_ddl.assert_called_once()
    assert all(call.args[0] == attempt.name for call in operations.get_operation.call_args_list)


def test_absent_after_uncertainty_replays_identical_request_and_id_once():
    db, operations, attempt, records = context()
    db.update_ddl.side_effect = DeadlineExceeded("lost response")
    with pytest.raises(PendingEntityIndexUpgradeError):
        apply(db, operations, attempt, records)
    assert db.update_ddl.call_count == 2
    assert db.update_ddl.call_args_list[0] == db.update_ddl.call_args_list[1]
    assert attempt.state == "uncertain"
    restarted = EntityIndexAttempt(**records[-1])
    with pytest.raises(PendingEntityIndexUpgradeError):
        apply(db, operations, restarted, records)
    assert db.update_ddl.call_count == 2
    assert restarted.submissions == 2


def test_pending_visible_schema_never_replanned_or_resubmitted():
    db, operations, attempt, records = context()
    attempt.statements = plan_entity_index_upgrade(db, 3)
    attempt.digest, attempt.state = statement_digest(attempt.statements), "submitting"
    operations.get_operation.side_effect = None
    operations.get_operation.return_value = operation(attempt, done=False)
    with (
        patch(
            "context_graph.adapters.spanner.ddl_upgrade.plan_entity_index_upgrade",
            side_effect=AssertionError("pending operation must not replan"),
        ),
        pytest.raises(PendingEntityIndexUpgradeError),
    ):
        apply(db, operations, attempt, records, timeout_s=0)
    assert attempt.state == "pending"
    db.update_ddl.assert_not_called()


def test_get_denied_is_not_absent_and_never_submits():
    db, operations, attempt, records = context()
    operations.get_operation.side_effect = PermissionDenied("not allowed")
    with pytest.raises(PermissionDenied):
        apply(db, operations, attempt, records)
    assert attempt.state == "registered"
    assert attempt.last_rpc_error["kind"] == "get_rpc"
    db.update_ddl.assert_not_called()


@pytest.mark.parametrize("mismatch", ["name", "statements", "digest", "database"])
def test_attempt_and_operation_identity_must_match(mismatch):
    db, operations, attempt, records = context()
    attempt.statements = plan_entity_index_upgrade(db, 3)
    attempt.digest = statement_digest(attempt.statements)
    raw = operation(
        attempt,
        name=attempt.name + "_other" if mismatch == "name" else None,
        statements=["bad"] if mismatch == "statements" else None,
    )
    if mismatch == "digest":
        attempt.digest = "changed"
    elif mismatch == "database":
        attempt.database += "_other"
    operations.get_operation.side_effect = None
    operations.get_operation.return_value = raw
    with pytest.raises(EntityIndexUpgradeError):
        apply(db, operations, attempt, records)
    db.update_ddl.assert_not_called()


def test_terminal_failure_is_saved_and_new_retry_requires_confirmed_parent():
    db, operations, attempt, records = context()
    attempt.statements = plan_entity_index_upgrade(db, 3)
    attempt.digest = statement_digest(attempt.statements)
    failed = operation(attempt, error=3)
    operations.get_operation.side_effect = None
    operations.get_operation.return_value = failed
    with pytest.raises(Exception, match="DDL rejected"):
        apply(db, operations, attempt, records)
    assert attempt.state == "failed" and attempt.error["kind"] == "operation"
    child = EntityIndexAttempt(RESOURCE, 3, "engram_test_0002", predecessor=attempt.record())
    operations.get_operation.side_effect = lambda name, **kw: (
        failed if name == attempt.name else (_ for _ in ()).throw(NotFound("absent"))
    )
    db.update_ddl.side_effect = lambda *args, **kwargs: SimpleNamespace(operation=operation(child))
    assert len(apply(db, operations, child, records)) == 2
    assert child.state == "ready"


def test_success_with_unready_schema_is_not_closed():
    db, operations, attempt, records = context()
    db.update_ddl.side_effect = lambda *args, **kwargs: SimpleNamespace(
        operation=operation(attempt)
    )
    with (
        patch(
            "context_graph.adapters.spanner.schema.schema_differences", return_value=["WRITE_ONLY"]
        ),
        pytest.raises(EntityIndexUpgradeError, match="incompatible"),
    ):
        upgrade_entity_index(
            db,
            3,
            attempt=attempt,
            operations_client=operations,
            persist_attempt=lambda r: records.append(copy.deepcopy(r)),
        )
    assert attempt.state == "failed"


def test_previously_observed_disappearance_is_unresolved():
    db, operations, attempt, records = context()
    attempt.observed, attempt.state = True, "pending"
    with pytest.raises(EntityIndexUpgradeError, match="disappeared"):
        apply(db, operations, attempt, records)
    assert attempt.state == "unresolved"
    db.update_ddl.assert_not_called()


def test_rpc_canonical_whitespace_is_same_request_without_rewriting_digest():
    db, operations, attempt, records = context()
    attempt.statements = plan_entity_index_upgrade(db, 3)
    attempt.digest = statement_digest(attempt.statements)
    original_digest = attempt.digest
    canonical = [
        s.replace("GraphNodes (embedding)", "GraphNodes(embedding)").replace(
            "OPTIONS (distance_type = 'COSINE')", "OPTIONS (\n  distance_type = 'COSINE'\n)"
        )
        for s in attempt.statements
    ]
    operations.get_operation.side_effect = None
    operations.get_operation.return_value = operation(attempt, statements=canonical)
    assert apply(db, operations, attempt, records) == []
    assert attempt.state == "ready" and attempt.digest == original_digest
    db.update_ddl.assert_not_called()


def test_get_error_cannot_erase_reconciliation_guard_or_terminal_error():
    db, operations, attempt, records = context()
    attempt.state, attempt.error = "unresolved", {"kind": "operation_identity"}
    operations.get_operation.side_effect = PermissionDenied("denied")
    with pytest.raises(PermissionDenied):
        apply(db, operations, attempt, records)
    assert attempt.state == "unresolved" and attempt.error["kind"] == "operation_identity"
    restored = EntityIndexAttempt(**records[-1])
    operations.get_operation.side_effect = NotFound("gone")
    with pytest.raises(EntityIndexUpgradeError, match="reconciliation"):
        apply(db, operations, restored, records)
    db.update_ddl.assert_not_called()


@pytest.mark.parametrize("fail_at", [2, 3])
def test_plan_or_submission_intent_persistence_failure_prevents_submit(fail_at):
    db, operations, attempt, _records = context()
    saves = 0

    def persist(record):
        nonlocal saves
        saves += 1
        if saves == fail_at:
            raise OSError("disk full")

    with pytest.raises(OSError):
        upgrade_entity_index(
            db, 3, attempt=attempt, operations_client=operations, persist_attempt=persist
        )
    db.update_ddl.assert_not_called()


def test_linked_retry_cannot_bypass_pending_parent():
    db, operations, parent, records = context()
    parent.statements = plan_entity_index_upgrade(db, 3)
    parent.digest = statement_digest(parent.statements)
    child = EntityIndexAttempt(RESOURCE, 3, "engram_test_0002", predecessor=parent.record())
    operations.get_operation.side_effect = None
    operations.get_operation.return_value = operation(parent, done=False)
    with pytest.raises(EntityIndexUpgradeError, match="not terminal failed"):
        apply(db, operations, child, records)
    db.update_ddl.assert_not_called()
