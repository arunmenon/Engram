"""Tracked control-schema setup and real-adapter fences on reserved target.

No reset/drop or populated-database adoption. Verify bootstraps a test owner,
uses exact synthetic fixtures and retains monotonically increasing ownership.
Setup submits once; uncertain operations resume by the exact recorded name.
"""

from __future__ import annotations

from engram_experiment_support import durable_json as durable_json
from engram_experiment_support import fingerprint as fingerprint

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from engram_spanner_compat import load_credentials

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/review/spanner-compatibility/runs"


def schema_preserved(before, after, *, acceptance_upgrade=False):
    """Allow exactly the reviewed Events column addition, preserving all other DDL."""
    if not acceptance_upgrade:
        return set(before).issubset(after)
    from context_graph.adapters.spanner.entity_index import ddl_statement_matches, table_columns

    def events(statement):
        return bool(re.match(r"CREATE\s+TABLE\s+`?Events`?\s*\(", statement, re.I))

    old = [statement for statement in before if events(statement)]
    new = [statement for statement in after if events(statement)]
    if len(old) != 1 or len(new) != 1:
        return False
    columns = table_columns(old, "Events")
    expected = {**columns, "acceptance": ("acceptance", "json")}
    old_key = re.search(r"PRIMARY\s+KEY\b.*", old[0], re.I | re.S)
    new_key = re.search(r"PRIMARY\s+KEY\b.*", new[0], re.I | re.S)
    return (
        bool(columns)
        and table_columns(new, "Events") == expected
        and old_key is not None
        and new_key is not None
        and ddl_statement_matches(old_key.group(), new_key.group())
        and set(statement for statement in before if not events(statement)).issubset(
            statement for statement in after if not events(statement)
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase",
        choices=(
            "inspect",
            "prepare",
            "verify",
            "runtime",
            "responses",
            "acceptance-prepare",
            "acceptance",
            "interpretation",
            "terminal",
            "source-trust",
            "expansion",
        ),
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--target-database", default="engram-compat-target")
    parser.add_argument("--resume-attempt", type=Path)
    args = parser.parse_args()
    # This harness cannot accidentally install ownership schema in the source.
    if args.target_database != "engram-compat-target":
        parser.error("Only the reserved disposable compatibility target is authorized")
    preparing = args.phase in {"prepare", "acceptance-prepare"}
    acceptance_upgrade = args.phase == "acceptance-prepare"
    if args.resume_attempt and not preparing:
        parser.error("Only prepare can resume an operation")
    values = load_credentials(args.credentials)
    if (
        values["GOOGLE_CLOUD_PROJECT"] != "portiq-mvp"
        or values["SPANNER_INSTANCE_ID"] != "engram-experiment"
    ):
        parser.error("Only portiq-mvp/engram-experiment is authorized by this experiment")
    resource = (
        f"projects/{values['GOOGLE_CLOUD_PROJECT']}/instances/{values['SPANNER_INSTANCE_ID']}"
        f"/databases/{args.target_database}"
    )
    from context_graph.adapters.spanner.event_acceptance import ACCEPTANCE_COLUMN_DDL
    from context_graph.adapters.spanner.tenant_control import TENANT_CONTROL_DDL

    statement = ACCEPTANCE_COLUMN_DDL if acceptance_upgrade else TENANT_CONTROL_DDL
    operation_prefix = "engram_acceptance_" if acceptance_upgrade else "engram_control_"
    statement_digest = hashlib.sha256(statement.encode()).hexdigest()
    attempt = None
    if preparing:
        attempt = (
            json.loads(args.resume_attempt.read_text())
            if args.resume_attempt
            else {
                "database": resource,
                "operation_id": operation_prefix + uuid4().hex,
                "statement": statement,
                "sha256": statement_digest,
                "submitted": False,
                "state": "prepared",
            }
        )
        if (
            attempt["database"] != resource
            or attempt["statement"] != statement
            or attempt["sha256"] != statement_digest
            or not attempt["operation_id"].startswith(operation_prefix)
        ):
            parser.error("Resume attempt does not match the exact target/DDL")
    sources = [
        Path(__file__),
        ROOT / "scripts/engram_spanner_tenant_control_cases.py",
        ROOT / "scripts/engram_spanner_tenant_runtime_cases.py",
        ROOT / "scripts/engram_spanner_process_bootstrap.py",
        ROOT / "scripts/engram_spanner_acceptance_cases.py",
        ROOT / "scripts/engram_spanner_interpretation_cases.py",
        ROOT / "scripts/engram_spanner_source_trust_cases.py",
        ROOT / "scripts/engram_spanner_empty_activation.py",
        ROOT / "scripts/engram_spanner_expansion_cases.py",
        ROOT / "tests/fixtures/pack_contracts/expansion.pack.yaml",
        ROOT / "tests/fixtures/pack_contracts/expansion_observer.pack.yaml",
        *list((ROOT / "src").rglob("*.py")),
        *list((ROOT / "src").rglob("*.yaml")),
    ]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    manifest = {
        "kind": "cloud_tenant_control_" + args.phase,
        "cloud_calls": True,
        "issues": [34, 36, 39, 43, 41] if args.phase == "expansion" else [34, 43, 41],
        "target": resource,
        "source_sha256": hashes,
        "scope": {
            "expansion": "Bounded projection expansion on explicit empty-target CAS activation; "
            "five synthetic unfamiliar-pack events with subscriber; real bound admission, "
            "projection consumer, exact graph properties/evidence and DLQ; exact cleanup "
            "and latest-core restoration; no native API, retrieval or worker process loops",
            "source-trust": "Explicit empty-target CAS activation core+PDLC, "
            "four normalized synthetic events; real projection/extraction consumers "
            "and stubbed model trust/evidence; exactcleanup/latestcore restore",
            "terminal": "Real bound worker refusal/recovery regression plus terminal ACK/DLQ "
            "and exhaustedretry checks; four receipt/content faults after processingread; "
            "valid DLQ metadata and repeatidempotence; oneevent/16groups exactcleanup",
            "interpretation": "Real bound consumer loops over one owned event and12groups; "
            "missingreceipt/oldcontract/tamperedcontent stop pending without graph/model/DLQ; "
            "restorecontent then emptyprofile consumer recovery ACK; exact cleanup",
            "acceptance-prepare": "Explicit additive acceptance JSON column "
            "on empty reserved target; "
            "preserve owner and existing schema/rows; no application writes",
            "acceptance": "Real adapter acceptance/duplicate/numeric/expiry/control recovery; "
            "exact synthetic event cleanup; no worker loops or pack projection",
            "verify": "Explicit test owner bootstrap,2ledger events,2nodes,1edge,onegroup; "
            "monotonic epoch; draining/frozen/stale mutation and all7snapshot read "
            "refusals; exact fixture cleanup; no API/worker processes",
            "runtime": "Private API lifespan and all5worker factories; "
            "exact metadata cleanup; no requests or worker loops",
            "responses": "Actual private API HTTP requests; cached/empty responses; "
            "freeze/finalresponse refusal and monotonic epoch recovery; "
            "no application row writes, worker factories or worker loops",
        }.get(args.phase, "Control schema only; no ownership creation or row mutation"),
        "authorized_ddl": [statement] if attempt else [],
        "operation": attempt,
        "resume_source": str(args.resume_attempt) if args.resume_attempt else None,
        "credentials": "Explicit SDK token; ordinary ADC not proved",
    }
    tracker = ROOT / "scripts/track_spanner_compatibility.py"
    with Path("/private/tmp/engram-spanner-compat.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_file = Path("/private/tmp/engram-control-cloud-manifest.json")
        manifest_file.write_text(json.dumps(manifest, indent=2))
        subprocess.run(
            [
                sys.executable,
                str(tracker),
                "start",
                "--run-id",
                args.run_id,
                "--manifest",
                str(manifest_file),
            ],
            check=True,
        )
        directory = RECORDS / args.run_id
        if attempt:
            durable_json(directory / "attempt.json", attempt)
        checks, evidence = [], {}
        database = None
        try:
            os.environ.pop("SPANNER_EMULATOR_HOST", None)
            from google.api_core.operation import from_gapic
            from google.cloud import spanner
            from google.cloud.spanner_admin_database_v1.types import UpdateDatabaseDdlMetadata
            from google.cloud.spanner_v1.pool import BurstyPool
            from google.oauth2.credentials import Credentials
            from google.protobuf.empty_pb2 import Empty

            from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
            from context_graph.adapters.spanner.tenant_control import (
                control_statement_matches,
                verify_control_schema,
            )

            client = spanner.Client(
                project=values["GOOGLE_CLOUD_PROJECT"],
                credentials=Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"]),
            )
            pool = BurstyPool()
            database = client.instance(values["SPANNER_INSTANCE_ID"]).database(
                args.target_database, pool=pool
            )
            prepare_cleanup(database, client, pool)
            before = fingerprint(database)
            database.reload()
            evidence.update(before_rows=before, before_ddl=list(database.ddl_statements))
            with database.snapshot() as snapshot:
                present = bool(
                    list(
                        snapshot.execute_sql(
                            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                            "WHERE TABLE_SCHEMA = '' AND TABLE_NAME = 'TenantControl'"
                        )
                    )
                )
            evidence["control_table_present_before"] = present
            from engram_spanner_tenant_control_cases import read_owner

            evidence["control_owner_before"] = read_owner(database) if present else []
            ddl_needed = not present
            if acceptance_upgrade:
                from context_graph.adapters.spanner.event_acceptance import plan_acceptance_upgrade

                if any(row["count"] for row in before.values()):
                    raise RuntimeError("Acceptance DDL experiment requires empty reserved target")
                ddl_needed = bool(plan_acceptance_upgrade(list(database.ddl_statements)))
            if attempt is not None:
                operation_name = resource + "/operations/" + attempt["operation_id"]
                if args.resume_attempt:
                    if not attempt["submitted"]:
                        raise RuntimeError("Unsubmitted attempt requires explicit reconciliation")
                elif ddl_needed:
                    # Persist before the only submission. Never retry with a new ID
                    # after uncertain RPC completion; resume exact database GET.
                    attempt.update(submitted=True, state="submitting")
                    durable_json(directory / "attempt.json", attempt)
                    database.update_ddl([statement], operation_id=attempt["operation_id"])
                else:
                    attempt["state"] = "existing_schema"
                if attempt["submitted"]:
                    operations = client.database_admin_api.transport.operations_client
                    for _ in range(30):
                        operation = operations.get_operation(operation_name, timeout=10)
                        if operation.name != operation_name:
                            raise RuntimeError("Operation identity mismatch")
                        future = from_gapic(
                            operation, operations, Empty, metadata_type=UpdateDatabaseDdlMetadata
                        )
                        metadata = future.metadata
                        evidence["operation_metadata"] = {
                            "database": metadata.database if metadata is not None else None,
                            "statements": list(metadata.statements) if metadata is not None else [],
                            "done": operation.done,
                        }
                        if (
                            metadata is None
                            or metadata.database != resource
                            or len(metadata.statements) != 1
                            or not control_statement_matches(statement, metadata.statements[0])
                        ):
                            raise RuntimeError("Operation request metadata mismatch")
                        attempt["state"] = "done" if operation.done else "pending"
                        durable_json(directory / "attempt.json", attempt)
                        if operation.done:
                            if operation.error.code:
                                raise RuntimeError(
                                    f"DDL operation failed: code {operation.error.code}"
                                )
                            break
                        time.sleep(1)
                    else:
                        raise TimeoutError(
                            "Known control-schema operation remains pending; resume it"
                        )
                    evidence["operation_name"] = operation_name
                if acceptance_upgrade:
                    from context_graph.adapters.spanner.event_acceptance import (
                        acceptance_column_valid,
                    )

                    database.reload()
                    if not acceptance_column_valid(list(database.ddl_statements)):
                        raise RuntimeError("Acceptance column handshake failed")
                    if read_owner(database) != evidence["control_owner_before"]:
                        raise RuntimeError("Acceptance upgrade changed protected owner")
                else:
                    verify_control_schema(database)
                attempt["state"] = "verified"
                durable_json(directory / "attempt.json", attempt)
                checks.append(
                    {
                        "name": "acceptance_column_handshake"
                        if acceptance_upgrade
                        else "protected_control_schema_handshake",
                        "passed": True,
                        "scenarios": [],
                    }
                )
            elif present:
                verify_control_schema(database)
                checks.append(
                    {"name": "existing_control_schema_handshake", "passed": True, "scenarios": []}
                )
            else:
                checks.append(
                    {"name": "control_schema_absence_observed", "passed": True, "scenarios": []}
                )
            if args.phase in (
                "verify",
                "runtime",
                "responses",
                "acceptance",
                "interpretation",
                "terminal",
                "source-trust",
                "expansion",
            ):
                if not present:
                    raise RuntimeError("Verify requires separately prepared control schema")
                from engram_spanner_tenant_control_cases import verify_fences

                if args.phase in ("runtime", "responses"):
                    from engram_spanner_tenant_runtime_cases import verify_runtime

                    verify_fences = verify_runtime
                    if args.phase == "responses":
                        from engram_spanner_tenant_runtime_cases import verify_responses

                        verify_fences = verify_responses
                if args.phase == "acceptance":
                    from engram_spanner_acceptance_cases import verify_acceptance

                    verify_fences = verify_acceptance
                if args.phase == "interpretation":
                    from engram_spanner_interpretation_cases import verify_interpretation

                    verify_fences = verify_interpretation
                if args.phase == "terminal":
                    from engram_spanner_interpretation_cases import verify_terminal_disposition

                    verify_fences = verify_terminal_disposition
                if args.phase == "source-trust":
                    from engram_spanner_source_trust_cases import verify_source_trust

                    verify_fences = verify_source_trust
                if args.phase == "expansion":
                    from engram_spanner_expansion_cases import verify_expansion

                    verify_fences = verify_expansion
                asyncio.run(
                    verify_fences(
                        database,
                        values,
                        args.run_id,
                        evidence,
                        checks,
                        fingerprint,
                        lambda value: durable_json(directory / "case-attempt.json", value),
                    )
                )
            database.reload()
            evidence["after_ddl"] = list(database.ddl_statements)
            assert schema_preserved(
                evidence["before_ddl"], evidence["after_ddl"], acceptance_upgrade=acceptance_upgrade
            )
            checks.append({"name": "existing_schema_preserved", "passed": True, "scenarios": []})
        except Exception as exc:
            checks.append(
                {
                    "name": "control_schema_" + args.phase,
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "scenarios": [],
                    "error_detail": str(exc).replace(
                        values["GOOGLE_OAUTH_ACCESS_TOKEN"], "[redacted]"
                    )[:1000],
                }
            )
        finally:
            if database is not None:
                try:
                    if "before_rows" in evidence:
                        evidence["after_rows"] = fingerprint(database)
                        checks.append(
                            {
                                "name": "all_application_rows_preserved",
                                "passed": evidence["after_rows"] == evidence["before_rows"],
                                "scenarios": [],
                            }
                        )
                except Exception as exc:
                    checks.append(
                        {
                            "name": "row_preservation_check",
                            "passed": False,
                            "error_type": type(exc).__name__,
                            "scenarios": [],
                        }
                    )
                try:
                    close_database(database)
                except Exception as exc:
                    checks.append(
                        {
                            "name": "sdk_cleanup",
                            "passed": False,
                            "error_type": type(exc).__name__,
                            "scenarios": [],
                        }
                    )
            unchanged = all(
                hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in hashes.items()
            )
            checks.append(
                {"name": "runtime_source_unchanged", "passed": unchanged, "scenarios": []}
            )
            (directory / "schema-evidence.json").write_text(
                json.dumps(evidence, indent=2, default=str)
            )
            (directory / "observations.json").write_text(json.dumps({"checks": checks}, indent=2))
            results = {
                "scenarios": [],
                "summary": f"{sum(c['passed'] for c in checks)}/{len(checks)} schema checks",
                "cleanup": (
                    "SDK/owned fixture cleanup attempted; see checks. Owner/schema retained."
                    if args.phase == "verify"
                    else "SDK cleanup attempted; see checks. DB/schema kept; no reset/adoption."
                ),
            }
            result_file = directory / "finish-input.json"
            result_file.write_text(json.dumps(results, indent=2))
            subprocess.run(
                [
                    sys.executable,
                    str(tracker),
                    "finish",
                    "--run-id",
                    args.run_id,
                    "--results",
                    str(result_file),
                ],
                check=True,
            )
        print(json.dumps({"run_id": args.run_id, "checks": checks}))
        if not all(c["passed"] for c in checks):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
