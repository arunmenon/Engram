# Acceptance cloud harness review

2026-10-07. Astra low source-only review/recheck of the additive acceptance DDL and real-adapter disposable-target cases. Reviewer ran no tests/cloud calls and made no edits.

## Scope and findings

`engram_spanner_tenant_control.py` reuses the existing register-before-SDK, durable exact-operation submission/resume, exact DDL metadata and reserved-target guards. Acceptance preparation requires an empty reserved target, permits only nullable nongenerated Events.acceptance JSON, preserves prior column declarations/primary key/other DDL and protected ownership. No hot startup repair or adoption.

P1: finally initially read the current owner and could reactivate it without checking that it belonged to this test. Resolved by validating exact pinned tenant/database/binding/digest and an explicit authorized epoch set before every transition, including cleanup. Only the persisted own +1 transition target may extend that epoch set. Missing/ambiguous/unrelated ownership refuses cleanup effects.

P2: initial four-writer gather could raise before other writes settled, allowing late fixture recreation after cleanup. Resolved by gathering all results/exceptions before raising, and shielding the complete case so cancellation waits for SDK writes and finally cleanup before propagating. Cancellation is recorded as failed, not success.

Astra source-only recheck: P1/P2 resolved; bounded harness approved pending executor test results. This does not approve production activation or compatibility.

## Local executor evidence

`runs/20261007-local-acceptance-harness-02`:43 passed,2warnings; Ruff passed. Tests cover manifest construction for every new phase, exact additive schema preservation, foreign owner mutations and cancellation waiting for a synthetic SDK-thread write followed by cleanup. First attempt retained with lint and pre-format manifest fingerprint limitations.

Existing fence harness now supplies its explicit stable fixture producer through an immutable admission writer and pinned engine revision; it no longer relies on unstamped bound appends.

## Cloud preparation evidence

`runs/20261007-cloud-acceptance-prepare-01`:4/4 checks passed. Exact operation `engram_acceptance_a2fca0c8a9bb46d2a502c254c9a4863e` verified on reserved `engram-compat-target`; acceptance column, existing schema, all application rows and runtime source fingerprints passed. Protected owner retained unchanged. Database/schema kept, no reset or source DB modification.

The real-adapter acceptance case is tracked separately; preparation alone proves no ingestion, worker or retrieval compatibility. Full Spanner scenarios and public tenant readiness remain open.


## Cloud adapter executor evidence

`runs/20261007-cloud-acceptance-adapter-01`:19/19 checks passed through Engram's actual Spanner adapter. Same/different-chunk duplicates/conflicts, four concurrent writers creating once, producer rotation/separation, native JSON roundtrip fingerprinting, immutable originals through enrichment, forbidden bare/import paths, actual document/dedup expiry, frozen/stale duplicate refusal and epoch-only recovery all passed. Original receipt retains accepted epoch four while the current owner advances to epoch five. Exactly two owned event fixtures removed; seven application tables, schema and source fingerprints preserved. Owner remains active at epoch five. No worker loops, API lifespan or full baseline promotion in this run.

Redacted execution logs, exact operation/case intents, schema/owner/row evidence and observations are retained under the run directories. Monitoring-exporter authorization warnings, if present, are separate from storage assertions. Full-worktree typing, current source-database schema upgrade and full Spanner sign-off remain open.
