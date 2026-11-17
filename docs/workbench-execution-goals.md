# Workbench execution goals

Updated 2026-11-03. The user explicitly asked that Spanner integration be included in the goals and pursued without needing to restart each phase. Execute these goals sequentially; do not treat the Spanner phase as an optional suggestion.

## Goal 1 Completed operator workbench improvement

Complete M1–M6 in `docs/workbench-storyboard.md`: accurate operator copy, safe editing/recovery, visible jobs, reviewable assistant changes and removals, truthful test results, focused tests and browser acceptance including real-provider authoring. Preserve frozen PDLC semantics and expected results. Record actual failures and limitations. Completed after the section 16 acceptance audit; known PDLC failures remain explicit.

## Goal 2 Active Spanner sandbox integration

Registered after Goal 1 acceptance. Proceed without another start request:

Implement a dedicated Spanner sandbox pool for the Engram workbench so both authored-pack sandbox runs and prepared journeys use real isolated Spanner storage through the real processing pipeline. Target four or five sandbox database slots, subject to verified instance capacity. Reuse the existing project/instance configuration after verifying current identity and ownership. Do not repurpose production/customer databases or silently delete existing data.

Sequential objectives:

1. Inventory the current Spanner adapters, schema/bootstrap tools, authentication, existing sandbox resources and ownership/fencing requirements. Establish the smallest integration using the current workbench/store abstractions. Document capacity and provisioning requirements before mutation.
2. Implement durable slot state and bounded allocation, with exclusive claims, run identity, failure recovery and fail-closed behavior. A busy pool produces a clear unavailable state rather than an arbitrary failed run. Do not infer that a lost observer means a job stopped.
3. Route sandbox and compatible journey execution through allocated Spanner stores; preserve the existing admission, ledger, projection and retrieval semantics and reviewed expectations. Explicitly identify any memory-specific fixture assertion that cannot establish Spanner behavior.
4. Verify cleanup before releasing a slot. A failed cleanup quarantines the slot; no new run may see a prior run's data. Cover cancellation, worker/process failure, stale claims, concurrent allocation and cross-run isolation.
5. Show backend, assigned slot, capacity, queue/unavailable state, progress and cleanup outcome in the UI. Distinguish a sandbox database from the customer's live database. Label memory fallback explicitly if retained; never present it as Spanner evidence.
6. Run focused automated integration tests and computer-use end-to-end acceptance for incident authoring and PDLC stories. Verify persisted graph results, question evaluation, retry/conflict semantics, isolation and cleanup. Record resource identity, engine/pack identity, outcomes and limitations without credentials.
7. Update the storyboard, runbook and video plan to reflect demonstrated Spanner behavior. Complete a requirement-by-requirement audit before declaring the goal achieved.

Continue ordinary implementation, testing and authorized sandbox work autonomously. Stop for missing access or a consequential action outside established authorization; describe the specific blocker rather than asking for repeated general permission. Do not delete existing databases merely to make space. Do not widen production access or deploy live tenant activation as part of this sandbox goal.

## Separate later scope

Production tenant activation requires its own operational design and acceptance. Video recording still waits for the user's script/storyboard review. Neither is silently included in sandbox provisioning.

## Execution handoff rule

Only one tool goal may be active at once. Goal 2 is queued here because the current goal remains unfinished. Once Goal 1 is actually verified complete, close it and create Goal 2 from the objective above, then continue. Do not stop at handing the user a plan or require another start request for Spanner.

## Spanner inventory progress

Current code uses memory-specific graph dictionaries and dead-letter arrays in both runners. Existing Spanner adapters already provide ledger, subscription, graph, transaction-local TenantFence checks and explicit schema installation. Reuse those instead of writing a second processing pipeline. Snapshot collection and dead-letter inspection need backend-specific adapters, while scenario checks/evaluation remain shared.

Access preflight: no local gcloud executable or Application Default Credentials found; the prior temporary access token returns HTTP 401 for read-only instance/database inventory. The GCP browser session remains authenticated to portiq-mvp, and console inventory is in progress. No cloud resources changed. Allocation design and provisioning remain contingent on verified dedicated resources/capacity; never infer that the two historical test databases are free pool slots.

### Verified resource inventory and first integration slice

The authenticated GCP console shows `portiq-mvp / engram-experiment` as an Enterprise free-trial instance in asia-south1, with five databases: `engram`, `engram-assess-1010a-pdlc`, `engram-compat-target`, `engram-g07-target`, and `engram-tenant-b-20261030`. All remain untouched. Google documents a five-database limit for free-trial instances: https://docs.cloud.google.com/spanner/docs/free-trial-instance . Thus the requested four/five dedicated slots cannot be added to this instance as it stands. A separate sandbox instance or explicitly designated disposable resources is required; a resource-choice question has been sent to the user. Do not treat elapsed time as approval to delete, repurpose or upgrade.

Implementation has continued independently. `workbench/storage_views.py` now collects bounded, observed graph rows from memory or a Spanner database with an explicit TenantFence. Spanner owner checking and both table reads share one consistent snapshot; a missing fence is refused. Reads fetch one row above the node/edge budget and fail rather than passing truncated evidence. Both existing runners use the shared async snapshot/dead-letter readers. No Spanner selection is enabled yet: the pool must own/allocate a slot first. Existing checks and evaluations remain unchanged.

Verification: 42 existing workbench/journey tests pass, plus three storage-view boundary tests (consistent fenced read, missing/stale binding refusal, detached memory snapshots and size limit). Mypy passes 15 workbench files. The Spanner boundary tests use test doubles and are explicitly not live integration evidence.

Next implementation: use durable per-slot allocation and the existing transaction-local TenantControl epoch fence together. A timeout alone must never free a slot. Revoke the prior run's write authority, clean only explicitly owned sandbox data, verify emptiness, then expose the slot as available; any uncertainty quarantines it. Keep configured resource allowlists and exclusive ownership checks ahead of schema/data mutation. Resource provisioning and live tests await the user resource decision and refreshed programmatic authentication; no production access expansion is implied.

### Dedicated slot lifecycle slice

`workbench/spanner_pool.py` now implements the durable per-database control record and pool allowlist. Registration is explicit and refuses existing ownership, populated engine tables or an unrelated schema. Claiming a ready slot changes its run identity/epoch and activates TenantControl in the same transaction. Busy/quarantined capacity is reported as unavailable; there is no memory fallback. Resource aliases and mixed pool identities are rejected.

Cleanup first freezes the run's transaction-local write authority. It then deletes application rows in batches of 50, preserving both control records, and proves every application table empty before marking the slot ready. Every batch checks the same run/epoch. Failed cleanup quarantines the slot; a stale cleanup cannot delete a later run. Server-time expiry revokes an abandoned run and leaves it quarantined for verified cleanup rather than assuming the old process stopped. Status reads verify the slot and tenant owner in one snapshot and never advertise inconsistent ownership as available.

Verification: eight serializable-transaction-double lifecycle tests plus three storage-view tests pass (11 total); scoped Ruff and mypy pass. Tests cover concurrent claims, unknown/custom schema, existing data/ownership, cross-pool refusal, old writer fencing, stale cleanup, cleanup failure/retry, expiry, sibling capacity and truthful unavailable status. These are algorithm/contract tests, not evidence of actual Spanner transaction behavior. No schema or cloud data has been changed. Next: wire leases to the real runner/store lifetimes and report cleanup status through the API/UI, then exercise real Spanner after the resource decision and authentication are resolved.

### Runner lifetime and control API slice

Both authored-pack and prepared-journey runners now accept an explicit Spanner execution provider. It claims a dedicated slot, constructs a resource-specific tenant binding, opens the existing adapters, uses tenant-bound event admission and Spanner provenance, closes stores, then verifies cleanup before returning a successful result. Cancellation during synchronous allocation waits for the SDK operation to settle so a late committed lease is not abandoned. Lost progress observers cannot skip cleanup. Default local execution remains explicitly isolated memory; no automatic fallback occurs.

The control API reports authenticated pool capacity and persists allocation/running/cleanup phases. Cancelling a configured Spanner run remains running until cleanup completes; another mutation/run on that draft is refused meanwhile. New runs discard stale storage status. Capacity and cleanup failures receive safe operator-readable messages. The frontend labels configured storage honestly and renders assigned-resource/cleanup progress; it no longer describes every configured run as memory.

Verification: the existing workbench/journey suite plus storage, pool and execution tests passed (56 total), and a new API lifecycle test passed separately. The API test verifies authentication, configured backend, unavailable capacity, progress persistence and cancellation remaining nonterminal until cleanup. Scoped Ruff and mypy across 17 workbench files pass. These tests use controlled Spanner boundaries; live SDK/database behavior and browser acceptance for this slice remain pending.

Still required: explicit server-owned pool configuration and provisioning workflow, process-loss recovery wiring, complete capacity UI, fresh programmatic authentication, dedicated database capacity, and real Spanner incident/PDLC acceptance. No cloud schema/data was changed and the running local backend has not yet been restarted with this slice. Goal 2 remains active.

Frontend verification note: the broad legacy demo `npm run build` fails on graph/user store methods and missing simulator scenario modules outside the workbench. Use the dedicated `build:workbench` target for this slice; do not describe the broad demo build as passing.

### Explicit configuration, recovery and capacity slice

Added `pool_config.py` and `--spanner-pool` to the existing local server. A server-owned JSON allowlist validates distinct resource identities before credentials/network, refuses an ambient emulator endpoint, checks existing registration/ownership, and never provisions or adopts automatically. Graceful server shutdown settles active jobs and recovery before closing owned handles. A 30-second recovery sweep revokes only server-time-expired claims before cleanup; unavailable siblings do not prevent healthy-slot recovery.

Added `scripts/engram_workbench_pool.py`: default is a no-network plan. Explicit `--create` refuses all existing targets before creating named databases with the engine/control schema. Concurrent creation never falls through to adoption. Partial failures leave resources intact for inspection; there is no deletion/rollback, instance or IAM management. No cloud provisioning command has been executed.

The UI now reports pool capacity, uncertainty, assigned resource and cleanup, and labels each saved result using its recorded backend. Prepared-story instructions use the configured backend instead of a memory literal. A sandbox worker that exits early now produces an immediate failure instead of waiting for the overall timeout.

Verification: 62 regression tests passed before the final worker-exit addition; that addition and its four execution peers then passed (63 unique tests across these runs). Scoped Ruff and mypy across 18 workbench modules passed; the dedicated workbench build passed. Config/provision tests cover invalid allowlists before credentials, emulator refusal, ownership refusal/handle closure and existing/concurrent-create rejection. Recovery tests cover unexpired claims and unavailable siblings. These remain local/controlled-boundary evidence.

Restarted the idle local backend with the new code, still without a Spanner allowlist. Computer-use reran the saved PDLC implementation journey: revision 12, 110 passed / 1 failed / 0 unsupported / 0 errors, explicitly isolated-memory. The original duplicate-versus-conflict failure remains visible; frozen pack and expectations are unchanged. Evidence: `output/workbench/usability/pdlc-storage-regression.json` and `.png`. The incident screen also visibly labels its historical memory result and requests revalidation after the engine change. No live Spanner result is claimed.

Runbook: `docs/runbooks/workbench-spanner-sandbox.md`. Live acceptance still requires a resource decision (full existing trial instance) and refreshed programmatic authentication. Pool-capacity/progress rendering under an actual configured Spanner run and live cancellation/recovery/isolation acceptance remain open. Goal 2 remains active.

### Remaining-requirements audit and failure-path checks

The next audit added tests for cancellation during store opening, repeated cancellation during cleanup, and closing every owned handle even when one close fails. Handle shutdown now attempts all slots before reporting its aggregate error. Allocation skips an unreachable or ownership-invalid sibling and tries another explicitly configured Spanner slot; it never falls back to memory. An ambiguous failed claim remains subject to server-side lease fencing/recovery, not assumed rolled back.

Current acceptance status:

| Requirement | Authoritative evidence | Status |
| --- | --- | --- |
| S1 adapter/schema/ownership inventory | Current adapters and resource inventory above; ADC recheck still unavailable | Code inventory done; access/capacity unresolved |
| S2 durable exclusive pool, unavailable behavior | `spanner_pool.py`, configuration/provisioner, transaction-double tests | Implemented locally; actual Spanner concurrency unverified |
| S3 both real-adapter execution paths | `execution.py`, sandbox/journey runners, API wiring | Implemented; only memory end-to-end demonstrated |
| S4 cancellation/recovery/isolation | Pool/execution/API tests, resource fences, recovery sweep | Local checks pass; live process-loss and cross-run acceptance missing |
| S5 truthful backend/capacity/progress | Frontend source and memory browser evidence | Implemented; actual Spanner browser states not yet observed |
| S6 incident and PDLC Spanner acceptance | No live run artifacts exist | Not achieved; requires approved dedicated capacity and ADC |
| S7 docs, storyboard, video accuracy | Runbook, execution record and linked scope notes | Updated as incomplete; final demonstrated-Spanner audit cannot pass yet |

Goal remains active and incomplete. No deployed activation, recording, cloud mutation or frozen-pack/oracle edit occurred. The running local service still has the previous slice loaded; these final failure-path edits need a restart before their browser behavior is claimed.

### Blocked at live acceptance — 2026-11-03

Final current-source local verification: 67 focused tests passed in 22.59 seconds; scoped Ruff and mypy across 18 modules passed. The dedicated frontend build passed in the preceding slice; no frontend edits followed it.

Revalidated the external dependency: the authenticated GCP console still lists the same five databases on the free-trial `portiq-mvp / engram-experiment` instance; ADC discovery still raises DefaultCredentialsError. The resource/authentication condition has remained unresolved across more than three consecutive goal turns. Independent implementation and local failure-path verification have now been exhausted for this scope. The remaining S4–S6 proof requires real dedicated resources and programmatic authentication; further memory reruns would not satisfy it.

Goal status: blocked, not completed. Resume after the operator identifies approved dedicated capacity (prefer a separate sandbox instance; existing databases stay protected unless explicitly redesignated) and provides an authorized authentication path. Do not infer permission to upgrade, delete, repurpose or widen IAM from the blocked status. After access is available: provision/verify slots, start with the allowlist, run live incident/PDLC and cancellation/recovery/isolation acceptance, verify UI capacity/cleanup states, then close the requirement audit. Current backend remains memory-based; latest failure-path edits have not been loaded into that process.

### Resource authorization update

The user explicitly authorized removing existing databases to free sandbox capacity. This supersedes the earlier blanket prohibition on replacing disposable test databases. Preserve `engram`; proposed replacements are `engram-assess-1010a-pdlc`, `engram-compat-target`, `engram-g07-target`, and `engram-tenant-b-20261030`, all on portiq-mvp/engram-experiment. The concrete new allowlist is `.workbench/spanner-pool.json`, containing engram-sandbox-01 through engram-sandbox-04; its plan-only command passed without network mutation.

The GCP browser deletion dialog explicitly says database deletion is permanent. The computer-use policy requires confirmation at action time even after general authorization. The first dialog (engram-g07-target) is staged, not submitted; the four-target confirmation is batched for the user. No database deletion has happened in this resumed turn. Programmatic authentication still needs restoration before provisioning and live runner tests.

### Capacity freed and first real Spanner run

The user's “done i think” was verified in GCP: the console reports deletion of `engram-g07-target`; `engram`, `engram-assess-1010a-pdlc`, `engram-compat-target`, and `engram-tenant-b-20261030` remain. Only one slot is free, so live acceptance starts with one dedicated database rather than assuming all four deletions occurred. `.workbench/spanner-pool-live.json` selects `engram-sandbox-01`; the four-slot target remains in the original plan.

Authentication correction: gcloud was absent from PATH, not absent from the machine. `/Users/arunmenon/google-cloud-sdk/bin/gcloud` has an existing signed-in account and successfully lists the project's databases. Live checks use short-lived tokens from that existing account, kept in process memory; no new IAM access or persistent credentials were created. The earlier ADC discovery result remains accurate but no longer blocks the test path.

The explicit provisioner created and registered `engram-sandbox-01` (evidence `output/workbench/spanner/provision.json`). The first live attempt exposed a missing SourceTrustPolicy on the sandbox projector; it correctly failed closed and cleaned the claimed database. Both runners now construct the same tenant-bound source policy as the production worker. The corrected incident fixture then passed on actual Spanner: mean F1 1.0 versus 0.8, resource epoch 3, cleanup verified and released. Evidence: `output/workbench/spanner/incident-first.json`. Engine and control-schema checks independently returned no differences. The SDK emits Cloud Monitoring metrics-export warnings; these are not evidence of failed data-plane checks and remain visible in local logs.

Scoped lint/types pass after the policy wiring fix; 51 affected workbench/journey/execution tests passed. PDLC live execution is next. These are direct runner checks, not yet browser Spanner acceptance. Goal work has resumed on user instruction, although the goal tool's stored blocked status cannot be set active through update_goal.

### First live runner and UI acceptance results

The frozen PDLC implementation journey initially returned 106 passed / 5 failed. All five failures were the runner's hard-coded `provenance.source == memory` assertion; the actual nodes, edges, properties and evidence event IDs matched. The frozen expected answers do not specify that literal source. Changed the runner to require the actual runtime provenance source, preserving source verification instead of dropping it. The unchanged frozen journey rerun passed all 111 checks on Spanner at epoch 5; cleanup verified. Initial diagnostic is retained at `output/workbench/spanner/pdlc-memory-provenance-check.json`, corrected result at `pdlc-first.json`. The conflict check now passes on the durable ledger; the historical memory discrepancy remains historical evidence.

The local API is now configured for the one registered Spanner slot, launched with `.workbench/serve-spanner.py`. That acceptance-only launcher uses the existing gcloud account and in-memory refreshed access tokens; it does not mint persistent credentials. The UI visibly reported 0/1 slots while the direct PDLC check ran, then 1/1 after cleanup (`ui-capacity-busy.png`). Through computer use, revalidated the existing real-provider-authored incident pack and ran its saved scenarios unchanged. Draft revision 35 completed on Spanner, mean F1 1.0 against 0.8, malformed event rejected, cleanup verified at epoch 6. Evidence: `output/workbench/spanner/ui-incident-result.json` and `ui-incident-passed.png`.

Still open at that checkpoint: PDLC invocation and result inspection through the UI after reloading its final provenance-check correction; live cancellation/restart/stale-writer/concurrency and cross-run isolation acceptance; expansion toward the requested four slots (three other proposed disposable databases remain and have not been deleted); final full requirement audit/document alignment. The running API at that checkpoint contained the bound-policy fix but predated the final one-line PDLC provenance-check correction. No customer activation or video recording occurred.

### Video rehearsal follow-up — 2026-11-03

The frozen implementation journey has now been invoked and inspected through the Chrome workbench on Spanner: 111 passed, zero failed/unsupported/errors, cleanup verified and capacity restored to 1 of 1. Evidence: `output/video/rehearsal/pdlc-ui-passed.png`. An initial attempt failed authentication and cleaned up; the local acceptance launcher was corrected to fetch a current access token for each new client instead of reusing its expired startup token. This is not a production authentication change. It closes the implementation-story UI invocation gap, not the remaining operational acceptance, other-story coverage or pool expansion. Narration and remaining video gates are recorded in `docs/engram-video-narration.md`; no full video has been recorded.
