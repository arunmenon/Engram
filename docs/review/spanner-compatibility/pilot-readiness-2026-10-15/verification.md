# Pilot entry checkpoint — failed, evidence retained

15 October 2026. The guide update is delivered; the first pilot checkpoint was attempted and **did not pass**. No broader pilot readiness or completion claim is made. The public acceptance retrieval queries were not reached. Do not count admission/model calls as an end-to-end journey pass.

## What happened

| Step | Expected | Actual and verdict |
|---|---|---|
| Exact existing owner/configuration | Preserve binding/epoch and reject mismatched settings | Attempt01 refused a changed timeout/consolidation policy before API/model calls. Guard worked; attempt failed and remains retained. |
| Reviewed retained-policy reconstruction | Use the exact existing policy without reset/rebind | Attempt02 matched both owner digests. Accelerated20-second consolidation/threshold5 and30-second request timeout were retained. |
| Authenticated writes | Nine new Event identities; unchanged retry adds none | Four A and five B Events were admitted via the public dispatcher; ten recorded write requests including retry. Exact appended ledger set independently verified. |
| Actual processing/providers | Both owner extractions, matching B profiles, exact graph/evidence and drained delivery | Twelve actual completion invocations returned. Existing consolidation also processed older sessions; the runner's own12-call ceiling then refused further calls. Bob's session-end extraction stayed pending. Failed. |
| Retrieval and role/isolation assertions | Execute declared public queries and inspect exact results/evidence | Not run: required processing completion failed first. No personalization, artifact-chain, foreign-source or API/admin role acceptance claim from this attempt. |
| Original source retention | Keep original ledger documents/acceptance and owner | Passed for both targets. No reset, rebind, database/schema deletion or direct artifact insert. |
| Material graph preservation | Prior material nodes/edges unchanged except declared read/Entity bookkeeping | Failed in both targets. Consolidation changed older Summary content/created_at, Summary-edge created_at and Event importance_score. No old node/edge identity was missing in the difference audit. |
| Shutdown | Stop API and all workers cooperatively, preserve diagnostics | Clean shutdown, no errors. A retains1pending extraction delivery; both DLQs empty. API/workers are stopped. |
| Fresh audit | Saved final state and source pins agree with independent process | Both exact final snapshots/owners/fingerprints and all170source hashes matched. |

Final retained A:15Events,57nodes,197edges,5groups/80cursors,1pending/0DLQ, epoch52. B:19Events,85nodes,308edges,5groups/80cursors,0pending/0DLQ, epoch6. The prior11/14ledger Events remain intact. Keep current targets and all before/after evidence; do not reset or claim unchanged derived content.

The12-call ceiling was introduced by the runner, not requested by the stakeholder or imposed by the provider. This is a setup/budget conflict exposed by the attempt, not evidence that Engram cannot process the journeys. It limits completion invocations; provider-internal retries, if configured, can add HTTP attempts. Summary fallback after a refusal must not be counted as real-model summary-quality success.

## Interpretation and next gate

Astra's final evidence review confirms the failure. The material changes match current consolidation behavior; this does not establish a new runtime regression. The pilot's preservation expectation and retained accelerated schedule conflict. Before recovery/retry, specify what derived records may change, how old and new session work shares the provider budget, and what exact pending-delivery recovery is supported. Review that bounded plan before any further live operation. Do not weaken preservation checks, silently increase limits, reset retained targets, fabricate missing outputs or reword failed questions to obtain a pass.

Rust-interest usefulness, the complete A01/A06/B02/B06 journeys, the remaining49-candidate coverage, broader18probes, external cohort onboarding, independent developer reproduction and extension remain unverified. There was no Episode/summary-quality acceptance, ANN benchmark or hierarchy/migration work.

## Evidence and repeat boundaries

- [Attempt01 results](../runs/pilot-1015-entry-01/results.json), [archived runner](../runs/pilot-1015-entry-01/runner.py).
- [Attempt02 frozen inputs](../runs/pilot-1015-entry-02/fixtures.json), [results/API/provider journal](../runs/pilot-1015-entry-02/results.json), [archived runner](../runs/pilot-1015-entry-02/runner.py), [source pins](../runs/pilot-1015-entry-02/source-hashes.json).
- [A preservation differences](../runs/pilot-1015-entry-02/a-preservation-differences.json), [B differences](../runs/pilot-1015-entry-02/b-preservation-differences.json), full a/b-before.json and a/b-final-state.json beside them.
- [Fresh-process read-only audit](../runs/pilot-1015-entry-02/independent-post-process-audit.json).
- [Astra design, corrections and failed-evidence review](../skill-reviews/2026-10-15-pilot-entry-astra.md).
- [Checkpoint specification](entry-checkpoint.md). Its original baseline is now stale for a new mutating run: the exact fingerprint guard will refuse reuse. Recovery/new execution requires a newly reviewed baseline/plan.
- [Verified raw-log archives](log-archives.json), compressed original logs and bounded timestamp summaries in this directory. The raw14.7MB second log was losslessly compressed to0.81MB; original uncompressed log is retained locally. Configured API-key values were checked absent before archiving.

The architecture/pilot guide is versioned under docs/guide; pages20–27 teach the plan and distinguish examples from measured evidence. Its live tab remains open; its local documentation server is separate from the stopped pilot APIs/workers.

## GitHub reconciliation

[Follow-up #63](https://github.com/arunmenon/Engram/issues/63) is an open native child of [#39](https://github.com/arunmenon/Engram/issues/39), within umbrella [#34](https://github.com/arunmenon/Engram/issues/34). Both #39 and #34 received actual failure/evidence updates and remain open. No issue was closed. Parent relationship and states were reread; exact comment links are in [the reconciliation record](github-reconciliation.json).

## 16 October continuation — not a pilot pass

Model-only cutover advanced A52→53 and B6→7 with exact prior acceptance epochs A[51,52], B[6], preserving every application-table fingerprint. Source and grant evidence: runs/pilot-1016-model-transition-01.

Entry03 (`runs/pilot-1016-entry-03`) failed at Alice's owner-exclusion check: Bob source Events entered through shared Entity expansion (#64). Its final preservation check also failed: entity:Rust origin/classification changed on reobservation (#65), and the previously pending Bob trigger gained its newly applied receipt. Both databases ended with no pending/DLQ and cooperative shutdown succeeded. Those facts do not turn the run into a pass. Corrective owner/Entity changes and a fresh retained baseline precede entry04. Old source documents/acceptance remain preserved; direct repairs were not performed.
