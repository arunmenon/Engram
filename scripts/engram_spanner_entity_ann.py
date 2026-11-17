"""Tracked read-only inspection or explicit additive Entity ANN upgrade (#44).

No global reset, database creation or index deletion. Verify writes and removes
only registered synthetic fixtures. Credentials remain outside the repository.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from engram_spanner_compat import load_credentials

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["inspect", "upgrade", "verify", "startup", "bulk"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--dimensions", type=int, default=384)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--new-attempt", action="store_true")
    mode.add_argument("--resume-attempt", type=Path)
    mode.add_argument("--retry-attempt", type=Path)
    args = parser.parse_args()
    values = load_credentials(args.credentials)
    from context_graph.adapters.spanner.ddl_upgrade import EntityIndexAttempt

    resource = (
        f"projects/{values['GOOGLE_CLOUD_PROJECT']}/instances/{values['SPANNER_INSTANCE_ID']}"
        f"/databases/{values['SPANNER_DATABASE_ID']}"
    )
    attempt = None
    if args.phase == "upgrade":
        if not (args.new_attempt or args.resume_attempt or args.retry_attempt):
            parser.error(
                "upgrade requires explicit --new-attempt, --resume-attempt or --retry-attempt"
            )
        if args.resume_attempt:
            attempt = EntityIndexAttempt(**json.loads(args.resume_attempt.read_text()))
        else:
            predecessor = json.loads(args.retry_attempt.read_text()) if args.retry_attempt else None
            attempt = EntityIndexAttempt(
                resource, args.dimensions, "engram_ann_" + uuid4().hex, predecessor=predecessor
            )
        attempt.validate(resource, args.dimensions)
    source_files = [
        Path(__file__),
        ROOT / "scripts/engram_spanner_entity_ann_cases.py",
        *[
            ROOT / f"src/context_graph/adapters/spanner/{name}.py"
            for name in ("entity_index", "ddl_upgrade", "schema", "graph", "commits")
        ],
    ]
    if args.phase == "startup":
        source_files.extend((ROOT / "src").rglob("*.py"))
        source_files.extend((ROOT / "src").rglob("*.yaml"))
        source_files.extend(
            ROOT / "scripts" / name
            for name in (
                "engram_spanner_compat.py",
                "engram_spanner_compat_remaining.py",
                "engram_spanner_process_bootstrap.py",
            )
        )
    manifest = {
        "kind": "cloud_entity_ann_" + args.phase,
        "cloud_calls": True,
        "issues": [44, 41, 23, 42],
        "target": {key: values[key] for key in values if key != "GOOGLE_OAUTH_ACCESS_TOKEN"},
        "dimensions": args.dimensions,
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_files
        },
        "scope": (
            "Native ANN differential and vector evidence fixtures; no full retrieval sign-off"
            if args.phase == "verify"
            else (
                "Two independent API startups; explicit-token/provider bootstrap, no workers or ADC"
                if args.phase == "startup"
                else ("Bounded Entity bulk writes with legacy/new indexes coexisting"
                      if args.phase == "bulk" else "Physical schema/upgrade only")
            )
        ),
        "fixture_limits": {"nodes": 70, "edges": 2, "negative_vectors": 65, "top_k": 2}
        if args.phase == "verify"
        else {},
        "startup_limits": {
            "api_processes": 2,
            "concurrent_processes": 1,
            "ingestion_requests": 0,
            "metadata": "ordinary startup may ensure configured consumer groups",
        }
        if args.phase == "startup"
        else {},
        "bulk_limits": {"nodes": 6, "mutations_per_commit_estimate": 70,
                        "bytes_per_commit_estimate": 100000} if args.phase == "bulk" else {},
        "registered_attempt": attempt.record() if attempt is not None else None,
        "resume_source": str(args.resume_attempt) if args.resume_attempt else None,
    }
    tracker = ROOT / "scripts/track_spanner_compatibility.py"
    # Use the same process lock as the compatibility runner; a lock file by
    # itself is never treated as proof that another process is active.
    with Path("/private/tmp/engram-spanner-compat.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_path = Path("/private/tmp/engram-entity-ann-cloud-manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2))
        subprocess.run(
            [
                sys.executable,
                str(tracker),
                "start",
                "--run-id",
                args.run_id,
                "--manifest",
                str(manifest_path),
            ],
            check=True,
        )
        directory = ROOT / "docs/review/spanner-compatibility/runs" / args.run_id
        checks, evidence = [], {}

        def persist_attempt(record):
            temporary = directory / "attempt.tmp"
            with temporary.open("w") as stream:
                json.dump(record, stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(directory / "attempt.json")
            # Resume points at the latest record in the new evidence run.
            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)

        if attempt is not None:
            persist_attempt(attempt.record())
        database = None
        try:
            # Never inherit an emulator endpoint during a real-cloud run.
            os.environ.pop("SPANNER_EMULATOR_HOST", None)
            from google.cloud import spanner
            from google.cloud.spanner_v1.pool import BurstyPool
            from google.oauth2.credentials import Credentials

            from context_graph.adapters.spanner.ddl_upgrade import upgrade_entity_index
            from context_graph.adapters.spanner.entity_index import plan_entity_index_upgrade
            from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
            from context_graph.adapters.spanner.schema import schema_differences

            client = spanner.Client(
                project=values["GOOGLE_CLOUD_PROJECT"],
                credentials=Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"]),
            )
            pool = BurstyPool()
            database = client.instance(values["SPANNER_INSTANCE_ID"]).database(
                values["SPANNER_DATABASE_ID"], pool=pool
            )
            prepare_cleanup(database, client, pool)

            def fingerprint() -> str:
                with database.snapshot() as snapshot:
                    rows = list(
                        snapshot.execute_sql(
                            "SELECT label, node_id, props, embedding FROM GraphNodes "
                            "ORDER BY label, node_id"
                        )
                    )
                return hashlib.sha256(
                    json.dumps(rows, sort_keys=True, default=str).encode()
                ).hexdigest()

            before = fingerprint()
            database.reload()
            plan = (
                plan_entity_index_upgrade(database, args.dimensions)
                if args.phase != "upgrade"
                else attempt.statements
            )
            evidence.update(
                before_graph_sha256=before,
                planned_ddl=plan,
                before_ddl=list(database.ddl_statements),
                before_handshake=schema_differences(database, args.dimensions),
            )
            if args.phase == "upgrade":
                assert attempt is not None
                operations = client.database_admin_api.transport.operations_client
                evidence["applied_ddl"] = upgrade_entity_index(
                    database,
                    args.dimensions,
                    attempt=attempt,
                    operations_client=operations,
                    persist_attempt=persist_attempt,
                )
                evidence["second_apply_ddl"] = upgrade_entity_index(
                    database,
                    args.dimensions,
                    attempt=attempt,
                    operations_client=operations,
                    persist_attempt=persist_attempt,
                )
                evidence["operation_name"] = attempt.name
                checks.append(
                    {
                        "name": "idempotent upgrade and target handshake",
                        "passed": evidence["second_apply_ddl"] == [],
                        "scenarios": [],
                    }
                )
            elif args.phase == "verify":
                if evidence["before_handshake"]:
                    raise RuntimeError("Native ANN fixtures require a compatible ready schema")
                from engram_spanner_entity_ann_cases import verify_entity_ann

                asyncio.run(
                    verify_entity_ann(database, args.dimensions, evidence, checks, directory)
                )
            elif args.phase == "startup":
                if evidence["before_handshake"]:
                    raise RuntimeError("API startup acceptance requires a compatible ready schema")
                from engram_spanner_entity_ann_cases import verify_api_startup

                asyncio.run(
                    asyncio.wait_for(
                        verify_api_startup(values, args.credentials, evidence, checks, directory),
                        timeout=180,
                    )
                )
            elif args.phase == "bulk":
                if evidence["before_handshake"]:
                    raise RuntimeError("Bulk acceptance requires a compatible ready schema")
                if not any(
                    "GraphNodesByEmbedding" in ddl and "CREATE VECTOR INDEX" in ddl
                    for ddl in evidence["before_ddl"]
                ):
                    raise RuntimeError("Coexistence acceptance requires retained legacy index")
                from engram_spanner_entity_ann_cases import verify_entity_bulk

                asyncio.run(
                    verify_entity_bulk(database, args.dimensions, evidence, checks, directory)
                )
            database.reload()
            after = fingerprint()
            evidence.update(
                after_graph_sha256=after,
                after_ddl=list(database.ddl_statements),
                after_handshake=schema_differences(database, args.dimensions),
            )
            if args.phase == "startup":
                checks.append(
                    {
                        "name": "API startup preserves compatible physical schema",
                        "passed": evidence["before_ddl"] == evidence["after_ddl"]
                        and not evidence["after_handshake"],
                        "scenarios": [],
                    }
                )
            checks.append(
                {
                    "name": "graph properties and embeddings unchanged",
                    "passed": before == after,
                    "scenarios": [],
                }
            )
            if args.resume_attempt:
                original = args.resume_attempt.parent / "schema-evidence.json"
                if original.exists():
                    original_hash = json.loads(original.read_text()).get("before_graph_sha256")
                    evidence["original_attempt_graph_sha256"] = original_hash
                    checks.append(
                        {
                            "name": "graph unchanged from original submitted attempt",
                            "passed": bool(original_hash) and original_hash == after,
                            "scenarios": [],
                        }
                    )

        except Exception as exc:
            checks.append(
                {
                    "name": "Entity ANN " + args.phase,
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "error_detail": str(exc).replace(
                        values["GOOGLE_OAUTH_ACCESS_TOKEN"], "[redacted]"
                    )[:1000],
                    "scenarios": [],
                }
            )
            if hasattr(exc, "operation_names"):
                evidence["pending_operations"] = exc.operation_names
        finally:
            if attempt is not None:
                evidence["attempt"] = attempt.record()
            if (
                database is not None
                and "before_graph_sha256" in evidence
                and "after_graph_sha256" not in evidence
            ):
                try:
                    after_error = fingerprint()
                    evidence["after_graph_sha256"] = after_error
                    checks.append(
                        {
                            "name": "graph preserved after failed phase cleanup",
                            "passed": after_error == evidence["before_graph_sha256"],
                            "scenarios": [],
                        }
                    )
                except Exception as exc:
                    checks.append(
                        {
                            "name": "post-failure graph verification",
                            "passed": False,
                            "error_type": type(exc).__name__,
                            "scenarios": [],
                        }
                    )
            if database is not None:
                try:
                    close_database(database)
                except Exception as exc:
                    checks.append(
                        {
                            "name": "SDK cleanup",
                            "passed": False,
                            "error_type": type(exc).__name__,
                            "scenarios": [],
                        }
                    )
            (directory / "schema-evidence.json").write_text(
                json.dumps(evidence, indent=2, default=str) + "\n"
            )
            (directory / "observations.json").write_text(
                json.dumps({"checks": checks}, indent=2) + "\n"
            )
            result_path = directory / "finish-input.json"
            result_path.write_text(
                json.dumps(
                    {
                        "scenarios": [],
                        "summary": (
                            f"Entity ANN {args.phase}: "
                            f"{sum(c['passed'] for c in checks)}/{len(checks)} checks passed; "
                            "no platform compatibility closure"
                        ),
                        "cleanup": (
                            "Only run-owned fixtures written/removed; "
                            "check node/edge hashes. No global reset."
                            if args.phase in ("verify", "bulk")
                            else (
                                "No fixtures/reset; API startup may ensure consumer metadata."
                                if args.phase == "startup"
                                else "Database retained; no row writes or resets. "
                                "Check pending DDL record."
                            )
                        ),
                    }
                )
            )
            subprocess.run(
                [
                    sys.executable,
                    str(tracker),
                    "finish",
                    "--run-id",
                    args.run_id,
                    "--results",
                    str(result_path),
                ],
                check=True,
            )
            print(json.dumps({"run_id": args.run_id, "checks": checks}))
            if not checks or not all(check["passed"] for check in checks):
                raise SystemExit(1)


if __name__ == "__main__":
    main()
