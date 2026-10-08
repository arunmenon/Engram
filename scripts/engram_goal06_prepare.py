"""Prepare only the separate G06 disposable DB; preserve G05 fingerprints."""

import argparse
import fcntl
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from engram_experiment_support import (
    CONTROL_COLUMNS,
    durable_json,
    fingerprint,
    load_credentials,
    read_owner,
    runtime_settings,
)
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.adapters.spanner.schema import schema_statements
from context_graph.adapters.spanner.tenant_control import TENANT_CONTROL_DDL, TenantFence
from context_graph.tenancy import TenantBinding

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    values = load_credentials(args.credentials)
    assert (values["GOOGLE_CLOUD_PROJECT"], values["SPANNER_INSTANCE_ID"]) == (
        "portiq-mvp",
        "engram-experiment",
    )
    retained = json.loads(
        (
            ROOT / "docs/review/spanner-compatibility/runs/"
            "20261008-cloud-g05-all-01/retained-dataset.json"
        ).read_text()
    )
    ddl = [*schema_statements(384), TENANT_CONTROL_DDL]
    manifest = {
        "kind": "G06 separate database preparation",
        "target": "engram-g06-target",
        "preserved_database": "engram-compat-target",
        "ddl": ddl,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Create only absent G06 database and bootstrap empty core owner; no G05 writes",
    }
    tracker = ROOT / "scripts/track_spanner_compatibility.py"
    with Path("/private/tmp/engram-spanner-compat.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m = Path("/private/tmp/engram-g06-prepare-manifest.json")
        durable_json(m, manifest)
        subprocess.run(
            [sys.executable, str(tracker), "start", "--run-id", args.run_id, "--manifest", str(m)],
            check=True,
        )
        directory = ROOT / "docs/review/spanner-compatibility/runs" / args.run_id
        client = spanner.Client(
            project=values["GOOGLE_CLOUD_PROJECT"],
            credentials=Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"]),
        )
        instance = client.instance("engram-experiment")
        pool = BurstyPool()
        g05 = instance.database("engram-compat-target", pool=pool)
        prepare_cleanup(g05, client, pool)
        g06 = None
        evidence, checks = {}, []
        try:
            evidence["g05_before"] = fingerprint(g05)
            evidence["g05_owner_before"] = read_owner(g05)
            assert evidence["g05_before"] == retained["fingerprints"]
            assert evidence["g05_owner_before"] == [retained["owner"]]
            durable_json(directory / "observations.json", evidence)
            g06 = instance.database("engram-g06-target", ddl_statements=ddl)
            assert not g06.exists(), "Existing G06 database requires explicit reconciliation"
            evidence["creation_intent"] = {"database": g06.name, "ddl": ddl}
            durable_json(directory / "observations.json", evidence)
            operation = g06.create()
            evidence["operation"] = operation.operation.name
            durable_json(directory / "observations.json", evidence)
            operation.result(timeout=300)
            pool06 = BurstyPool()
            g06 = instance.database("engram-g06-target", pool=pool06)
            prepare_cleanup(g06, client, pool06)
            assert not any(t["count"] for t in fingerprint(g06).values())
            assert not read_owner(g06)
            settings = runtime_settings(values, database="engram-g06-target")
            binding = TenantBinding.from_settings(
                "compat-control",
                "compat-control-binding",
                1,
                settings,
                engine_revision="tenant-control-conformance-v1",
            )
            owner = [*TenantFence.from_binding(binding)._identity(), "active"]
            evidence["owner_intent"] = owner
            durable_json(directory / "observations.json", evidence)
            with g06.batch() as batch:
                batch.insert(
                    "TenantControl", ["control_id", *CONTROL_COLUMNS], [["active", *owner]]
                )
            evidence["g06_owner"] = read_owner(g06)
            evidence["g06_tables"] = fingerprint(g06)
            assert evidence["g06_owner"] == [owner]
            assert not any(t["count"] for t in evidence["g06_tables"].values())
            checks.append(
                {"name": "G06 separate empty database prepared", "passed": True, "scenarios": []}
            )
        except BaseException as exc:
            evidence["error"] = type(exc).__name__ + ": " + str(exc)
            raise
        finally:
            try:
                evidence["g05_after"] = fingerprint(g05)
                evidence["g05_owner_after"] = read_owner(g05)
                assert evidence["g05_after"] == retained["fingerprints"]
                assert evidence["g05_owner_after"] == [retained["owner"]]
                checks.append(
                    {"name": "G05 retained data unchanged", "passed": True, "scenarios": []}
                )
            finally:
                durable_json(directory / "observations.json", evidence)
                if g06 is not None:
                    close_database(g06)
                close_database(g05)
                results = {
                    "checks": checks,
                    "scenarios": [],
                    "summary": "G06 preparation only; no journey compatibility claim",
                    "cleanup": "G05 unchanged; G06 schema/core owner retained",
                }
                r = directory / "finish-input.json"
                durable_json(r, results)
                subprocess.run(
                    [
                        sys.executable,
                        str(tracker),
                        "finish",
                        "--run-id",
                        args.run_id,
                        "--results",
                        str(r),
                    ],
                    check=True,
                )


if __name__ == "__main__":
    main()
