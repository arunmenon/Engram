"""Export, verify, and reuse ONLY the explicitly authorized assessment database.

Does not create databases or change application code. Each configuration starts
empty under a new ownership epoch. Sequential runs do not prove concurrent
database-per-tenant isolation. All previous datasets are exported before reset.
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import hashlib
import json
from pathlib import Path

from engram_composition_assessment import (
    INSTANCE,
    PROJECT,
    ROOT,
    binding_for,
    manifest,
    run_configuration,
    token,
)
from engram_experiment_support import (
    CONTROL_COLUMNS,
    durable_json,
    fingerprint,
    read_owner,
)
from engram_spanner_empty_activation import KEYS
from google.cloud import spanner
from google.cloud.spanner_v1 import KeySet
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.adapters.spanner.tenant_control import TenantFence

TARGET = "projects/portiq-mvp/instances/engram-experiment/databases/engram-assess-1010a-pdlc"
RUN_ID = "1010r"
CONFIGURATIONS = ("core", "user", "user-memory", "pdlc-memory")


def verify_target(database):
    if database.name != TARGET:
        raise ValueError("Reuse is authorized only for the exact assessment database")


def owner_at(transaction):
    rows = list(transaction.read("TenantControl", CONTROL_COLUMNS, KeySet(keys=[["active"]])))
    if len(rows) != 1:
        raise ValueError("Missing or ambiguous owner")
    return list(rows[0])


def row_hash(rows):
    canonical = sorted(json.dumps(row, sort_keys=True, default=str) for row in rows)
    return hashlib.sha256(json.dumps(canonical).encode()).hexdigest()


def freeze_and_export(database, expected_owner, expected_fingerprints, path):
    verify_target(database)
    if path.exists():
        raise ValueError("Export already exists; reconcile instead of overwrite")
    assert expected_owner[-1] == "active"
    frozen = [*expected_owner[:-1], "frozen"]
    intent = {
        "previous_owner": expected_owner,
        "frozen_owner": frozen,
        "target": TARGET,
        "authority": "Stakeholder approved assessment DB reuse",
    }
    durable_json(path.with_suffix(".intent.json"), intent)

    def freeze(tx):
        observed = owner_at(tx)
        if observed not in (expected_owner, frozen):
            raise ValueError("Owner drift; refuse freeze")
        if observed == expected_owner:
            tx.update("TenantControl", ["control_id", *CONTROL_COLUMNS], [["active", *frozen]])

    database.run_in_transaction(freeze)
    with database.snapshot(multi_use=True) as snap:
        assert owner_at(snap) == frozen
        tables = {}
        for table in (*KEYS, "TenantControl"):
            result = snap.execute_sql(f"SELECT * FROM {table}")
            rows = [list(row) for row in result]
            tables[table] = {"columns": [field.name for field in result.fields], "rows": rows}
        hashes = {
            table: {"count": len(data["rows"]), "sha256": row_hash(data["rows"])}
            for table, data in tables.items()
            if table != "TenantControl"
        }
    assert hashes == expected_fingerprints, "Dataset drift; retain frozen target for inspection"
    payload = {"database": TARGET, "owner": frozen, "tables": tables, "fingerprints": hashes}
    # JSON normalizes SDK datetime values. The hash is over that same representation.
    normalized = json.loads(json.dumps(payload, default=str))
    durable_json(path, normalized)
    restored = json.loads(path.read_text())
    assert restored == normalized
    for table in KEYS:
        assert row_hash(restored["tables"][table]["rows"]) == hashes[table]["sha256"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    durable_json(
        path.with_suffix(".verified.json"),
        {"sha256": digest, "fingerprints": hashes, "verified": True},
    )
    return frozen, normalized, digest


def reset_to(database, frozen, exported, digest, export_path, binding):
    verify_target(database)
    if hashlib.sha256(export_path.read_bytes()).hexdigest() != digest:
        raise ValueError("Export changed; refuse deletion")
    intended = [*TenantFence.from_binding(binding)._identity(), "active"]
    assert intended[1] == TARGET and intended[3] == frozen[3] + 1
    intent_path = export_path.with_suffix(".reset.json")
    durable_json(
        intent_path,
        {"state": "intended", "source": frozen, "destination": intended, "export_sha256": digest},
    )

    def work(tx):
        if owner_at(tx) != frozen:
            raise ValueError("Owner drift; refuse deletion")
        for table, columns in KEYS.items():
            rows = [list(row) for row in tx.execute_sql(f"SELECT * FROM {table}")]
            if row_hash(rows) != exported["fingerprints"][table]["sha256"]:
                raise ValueError("Dataset drift; refuse deletion")
            data = exported["tables"][table]
            indices = [data["columns"].index(column) for column in columns]
            keys = [[row[index] for index in indices] for row in data["rows"]]
            if keys:
                tx.delete(table, KeySet(keys=keys))
        tx.update("TenantControl", ["control_id", *CONTROL_COLUMNS], [["active", *intended]])

    database.run_in_transaction(work)
    assert read_owner(database) == [intended]
    assert not any(value["count"] for value in fingerprint(database).values())
    durable_json(
        intent_path,
        {"state": "completed", "source": frozen, "destination": intended, "export_sha256": digest},
    )
    return intended


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    directory = ROOT / "docs/review/spanner-compatibility/runs/composition-1010r"
    if directory.exists() and not args.resume:
        raise ValueError("Reuse run already exists; refusing evidence overwrite")
    if not args.resume:
        directory.mkdir()
    plan = manifest(RUN_ID)
    plan.update(
        target=TARGET,
        configurations=list(CONFIGURATIONS),
        execution="Sequential export/reset/run; not concurrent tenant isolation",
        authorization="Stakeholder: Plz reuse assessment database",
    )
    if not args.resume:
        durable_json(directory / "manifest.json", plan)
    prior = json.loads(
        (
            ROOT / "docs/review/spanner-compatibility/runs/composition-1010a/retained-dataset.json"
        ).read_text()
    )
    expected_owner = prior["owner"][0]
    expected_fingerprints = prior["fingerprints"]
    results = []
    configurations = CONFIGURATIONS
    if args.resume:
        results = json.loads((directory / "results.json").read_text())["configurations"]
        completed = tuple(result["configuration"] for result in results)
        if not completed or completed != CONFIGURATIONS[:len(completed)]:
            raise ValueError("Resume requires a recorded configuration prefix")
        if any(result.get("shutdown_errors") or result.get("snapshot_error") for result in results):
            raise ValueError("Resume refuses unsettled workers or missing snapshots")
        prior = json.loads((directory / (completed[-1] + "-retained.json")).read_text())
        expected_owner = prior["owner"][0]
        expected_fingerprints = prior["fingerprints"]
        configurations = CONFIGURATIONS[len(completed):]
    with Path("/private/tmp/engram-composition-reuse.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for config in configurations:
            client = spanner.Client(
                project=PROJECT, credentials=Credentials(token=token(impersonate=True))
            )
            pool = BurstyPool()
            database = client.instance(INSTANCE).database(TARGET.rsplit("/", 1)[1], pool=pool)
            prepare_cleanup(database, client, pool)
            try:
                export_path = directory / f"before-{config}-export.json"
                frozen, exported, digest = freeze_and_export(
                    database, expected_owner, expected_fingerprints, export_path
                )
                binding = binding_for(
                    RUN_ID,
                    config,
                    target_database=database.database_id,
                    epoch=expected_owner[3] + 1,
                )
                expected_owner = reset_to(database, frozen, exported, digest, export_path, binding)
            finally:
                close_database(database)
            print(
                json.dumps(
                    {
                        "configuration": config,
                        "state": "export verified; empty epoch active",
                        "epoch": expected_owner[3],
                    }
                ),
                flush=True,
            )
            result = asyncio.run(
                run_configuration(
                    RUN_ID,
                    config,
                    directory,
                    target_database=TARGET.rsplit("/", 1)[1],
                    epoch=expected_owner[3],
                    prebound=True,
                )
            )
            results.append(result)
            durable_json(
                directory / "results.json",
                {"configurations": results, "concurrent_isolation": "NOT RUN; one reused database"},
            )
            if result.get("shutdown_errors") or result.get("snapshot_error"):
                raise RuntimeError("Unsettled workers or missing snapshot; no further reset")
            client = spanner.Client(
                project=PROJECT, credentials=Credentials(token=token(impersonate=True))
            )
            pool = BurstyPool()
            database = client.instance(INSTANCE).database(TARGET.rsplit("/", 1)[1], pool=pool)
            prepare_cleanup(database, client, pool)
            try:
                assert read_owner(database) == [expected_owner]
                expected_fingerprints = fingerprint(database)
                durable_json(
                    directory / (config + "-retained.json"),
                    {
                        "owner": [expected_owner],
                        "fingerprints": expected_fingerprints,
                        "database": TARGET,
                    },
                )
            finally:
                close_database(database)
    print(
        json.dumps(
            {
                "state": "assessment executed",
                "configurations": len(results),
                "clean_pass": all(r["state"] == "completed" for r in results),
            }
        ),
        flush=True,
    )
    raise SystemExit(0 if all(r["state"] == "completed" for r in results) else 1)


if __name__ == "__main__":
    main()
