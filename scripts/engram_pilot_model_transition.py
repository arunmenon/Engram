"""Inspect or activate the retained pilot's bounded model-only transition.

Only the two existing pilot targets are permitted. No application rows, DDL,
credentials or IAM are changed. Activation changes exact TenantControl owners
and must run with workers cooperatively stopped. Every baseline and transition
result is retained; existing output files are never overwritten.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from engram_composition_assessment import settings_for
from engram_experiment_support import durable_json, fingerprint, read_owner, snapshot
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.adapters.spanner.tenant_control import activate_model_successor
from context_graph.tenancy import TenantBinding

TARGETS = {"a": "engram-assess-1010a-pdlc", "b": "engram-g07-target"}


def pilot_binding(run_id, tenant, owner, *, model=None, predecessor=None, epochs=()):
    settings = settings_for(
        run_id,
        "user-memory" if tenant == "a" else "pdlc-memory",
        target_database=TARGETS[tenant],
    )
    settings.decay.reflection_threshold = 5
    settings.decay.reconsolidation_interval_hours = 20 / 3600
    if model is not None:
        settings.llm.model_id = model
    return TenantBinding.from_settings(
        owner[0],
        owner[2],
        owner[3],
        settings,
        engine_revision="tenant-isolation-v1",
        predecessor=predecessor,
        predecessor_epochs=epochs,
    )


def binding_from_baseline(run_id, tenant, baseline):
    owner = baseline["owner"][0]
    transition = baseline.get("model_transition")
    if transition is None:
        return pilot_binding(run_id, tenant, owner)
    old = pilot_binding(
        run_id, tenant, transition["predecessor_owner"], model=transition["old_model"]
    )
    return pilot_binding(
        run_id,
        tenant,
        owner,
        model=transition["new_model"],
        predecessor=old,
        epochs=tuple(transition["accepted_epochs"]),
    )


def prepare_transition(tenant, before, previous, saved_plan=None):
    """Validate an unchanged dataset and exact old or already-planned owner."""
    if any(before[k] != previous[k] for k in ("database", "fingerprints")):
        raise RuntimeError("Retained application baseline drift")
    owner = previous["owner"][0]
    old = pilot_binding("model-transition", tenant, owner, model="gpt-5.2-2025-12-11")
    if old.bundle_digest != owner[4]:
        raise RuntimeError("Original model policy does not match retained owner")
    epochs = tuple(sorted({r[2]["accepted_epoch"] for r in before["snapshot"]["events"]}))
    if any(
        r[2]["bundle_digest"] != old.bundle_digest
        or r[2]["tenant_id"] != old.tenant_id
        or r[2]["binding_id"] != old.binding_id
        or r[2]["database_resource"] != old.database_resource
        or r[2]["engine_revision"] != old.engine_revision
        for r in before["snapshot"]["events"]
    ):
        raise RuntimeError("Retained acceptance contracts need separate assessment")
    new_owner = [*owner]
    new_owner[3] += 1
    new = pilot_binding("model-transition", tenant, new_owner, predecessor=old, epochs=epochs)
    transition = {
        "predecessor_owner": owner,
        "old_model": old.settings().llm.model_id,
        "new_model": new.settings().llm.model_id,
        "accepted_epochs": list(epochs),
        "successor_digest": new.bundle_digest,
        "purpose": "read-and-complete-under-successor-model",
    }
    expected_owner = [
        new.tenant_id,
        new.database_resource,
        new.binding_id,
        new.epoch,
        new.bundle_digest,
        "active",
    ]
    if saved_plan is not None and saved_plan != transition:
        raise RuntimeError("Resume plan differs from the exact validated transition")
    allowed = [previous["owner"]]
    if saved_plan is not None:
        allowed.append([expected_owner])
    if before["owner"] not in allowed:
        raise RuntimeError("Retained owner is neither predecessor nor saved successor")
    return new, transition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["inspect", "activate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predecessor", type=Path)
    parser.add_argument(
        "--binding-record", type=Path, help="Existing model transition for inspection"
    )
    parser.add_argument("--resume", type=Path, help="Prior activation output after interruption")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.phase == "activate" and args.predecessor is None:
        parser.error("activate requires exact inspected predecessor")
    cloud = shutil.which("gcloud")
    if cloud is None:
        parser.error("gcloud must be on PATH")
    token = subprocess.run(
        [
            cloud,
            "auth",
            "print-access-token",
            "--impersonate-service-account=engram-experiment-sa@portiq-mvp.iam.gserviceaccount.com",
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if token.returncode:
        raise RuntimeError("Credential refresh failed; credential output suppressed")
    client = spanner.Client(
        project="portiq-mvp", credentials=Credentials(token=token.stdout.strip())
    )
    databases = {}
    planned = {}
    try:
        # Validate and durably save BOTH plans before the first owner mutation.
        for tenant, dbid in TARGETS.items():
            pool = BurstyPool()
            db = client.instance("engram-experiment").database(dbid, pool=pool)
            prepare_cleanup(db, client, pool)
            databases[tenant] = db
            before = {
                "database": db.name,
                "owner": read_owner(db),
                "fingerprints": fingerprint(db),
                "snapshot": snapshot(db),
                "observed_at": datetime.now(UTC).isoformat(),
            }
            durable_json(args.output / (tenant + "-before.json"), before)
            if args.phase == "inspect":
                if args.binding_record:
                    known = json.loads(
                        (args.binding_record / (tenant + "-read-only-state.json")).read_text()
                    )
                    before["model_transition"] = known["model_transition"]
                    binding = binding_from_baseline("inspect", tenant, before)
                    if binding.bundle_digest != before["owner"][0][4]:
                        raise RuntimeError("Known transition does not match current owner")
                durable_json(args.output / (tenant + "-read-only-state.json"), before)
                print(tenant, {k: v["count"] for k, v in before["fingerprints"].items()})
                continue
            previous = json.loads(
                (args.predecessor / (tenant + "-read-only-state.json")).read_text()
            )
            saved_plan = None
            if args.resume:
                saved_plan = json.loads(
                    (args.resume / (tenant + "-transition-plan.json")).read_text()
                )
            new, transition = prepare_transition(tenant, before, previous, saved_plan)
            durable_json(args.output / (tenant + "-transition-plan.json"), transition)
            planned[tenant] = (new, transition, before)
        for tenant, (new, transition, before) in planned.items():
            db = databases[tenant]
            changed = activate_model_successor(db, new)
            after = {
                "database": db.name,
                "owner": read_owner(db),
                "fingerprints": fingerprint(db),
                "snapshot": snapshot(db),
                "model_transition": transition,
                "activated": changed,
            }
            durable_json(args.output / (tenant + "-read-only-state.json"), after)
            if after["fingerprints"] != before["fingerprints"]:
                raise RuntimeError("Application data changed during control-only transition")
            print(tenant, "model-only transition committed; application fingerprints preserved")
    finally:
        for db in databases.values():
            close_database(db)


if __name__ == "__main__":
    main()
