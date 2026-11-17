# Workbench Spanner sandboxes

Status: local implementation, not yet live-Spanner accepted. The existing `portiq-mvp / engram-experiment` trial instance has five databases and is full. None has been adopted, reset or deleted. Dedicated capacity and refreshed Application Default Credentials are prerequisites for live acceptance. The current development service still runs memory sandboxes.

## Configure dedicated capacity

An operator-owned JSON file names one to five databases and a stable pool identity. It contains no credentials and is not editable through the workbench:

```json
{
  "pool_id": "workbench-sandbox",
  "resources": [
    "projects/PROJECT/instances/INSTANCE/databases/workbench-sandbox-01"
  ]
}
```

Replace the placeholders with approved resources (lowercase identifiers). Plan first:

```sh
.venv/bin/python scripts/engram_workbench_pool.py /absolute/path/pool.json
```

This prints only the allowlist; it does not contact Google Cloud. After capacity is approved and ADC is configured, explicitly create the absent targets:

```sh
.venv/bin/python scripts/engram_workbench_pool.py /absolute/path/pool.json --create
```

The provisioner preflights that every target is absent, creates only the named databases, installs the existing engine schema plus TenantControl and WorkbenchSandbox, and registers empty slots. It cannot create instances, change IAM, delete databases, adopt existing control records or repair customer schemas. A concurrent create is an error, never permission to adopt that database. On partial failure it leaves created resources intact and reports incomplete; inspect them before retrying. Do not assume a timed-out create failed remotely.

## Start the workbench

Keep the existing operator token and authoring model configuration. Select Spanner explicitly:

```sh
.venv/bin/python scripts/engram_workbench_dev.py --spanner-pool /absolute/path/pool.json
```

Without this argument, runs use isolated memory and the UI labels them accordingly. With it, unregistered or mismatched database ownership refuses startup; there is no fallback. Ambient SPANNER_EMULATOR_HOST is refused so emulator behavior cannot be labelled real Spanner evidence. The service remains local, single-process, and does not activate live tenants.

Authenticated `GET /admin/sandbox-capacity` reports configured capacity, available slots and safe status per resource. The UI refreshes capacity every ten seconds. Availability is an observation, not a reservation; the run's transaction claims the database.

## Run and recover

Each run pins the engine, bundle, resource, run ID and epoch; it uses tenant-bound admission, real ledger/worker/graph adapters and Spanner retrieval. Sample producer identities simulate reviewed trust policy, not authentication of an external producer.

Sample agent aliases are preserved in the original event envelope. For Spanner
admission only, the workbench derives `sample-<sha256(alias)>` as the synthetic
source identity, using the same transformation for the reviewed trust list and
the per-event principal. All aliases are transformed, including valid-looking
IDs, so a literal encoded ID cannot impersonate another sample producer. The
run records `source_identity_mode=synthetic-producer-sha256`. This supports
legacy fixture aliases such as `webhook:github` without relaxing production
source-ID validation or asserting that a webhook signature was checked.

Cancellation stays visibly running until storage operations settle and cleanup finishes. Cleanup freezes write authority, deletes application rows in bounded batches, and verifies emptiness before reuse. Control records remain. Failed or uncertain cleanup leaves the database unavailable. The UI reports allocation, execution, cleanup and the assigned resource; recorded results identify their own backend rather than inheriting the currently configured one.

The recovery sweep runs every 30 seconds and uses server time to find expired leases (ten minutes). It fences expired work before cleanup; unexpired runs are not reclaimed merely because a process disappeared. Cleanup ownership checks prevent an old sweep from deleting a newer run's data. A failed recovery stays unavailable and does not stop healthy sibling slots. Quarantined resources require engineer investigation; there is deliberately no browser reset button. Graceful shutdown waits for active jobs and recovery to settle before closing owned SDK handles.

## Acceptance still required

Run the incident and PDLC journeys against actual approved Spanner resources. Record resource/engine/pack identities, observed storage, unchanged expected answers, concurrency/isolation, duplicate/conflict outcomes and verified cleanup. Exercise cancellation, stale claims and restart recovery against live transactions. Controlled test doubles prove local contracts, not real Spanner behavior. Existing PDLC failures must remain visible until their underlying semantics are resolved; do not change the frozen pack or oracle to get a green result.
