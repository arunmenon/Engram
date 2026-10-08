# Foundation handoff gate before G04

Status: BOUNDED HANDOFF COMPLETE AFTER SEPARATE G01/G02/G03 APPROVALS. Stakeholder approved this bounded gate before G04. G04 and later stay unstarted. No historical migration or cross-version upgrade analysis/tests.

## Fixed objective and stop rule

Make the G01–G03 foundation reproducible from one Git branch before G04. "Foundation migration" here means source/handoff consolidation, never historical-data migration. Done means: (1) one self-contained branch, (2) fresh locked setup plus unit/lint/type checks, (3) all three original journeys passing through Engram on real Spanner, (4) published verification, Git issue reconciliation and stakeholder walkthrough. No broad redesign, new orchestration, whole-backlog remediation or G04 execution. Repair only failures that block these checks; otherwise record remaining scope and stop.

## Outcome

Publish one self-contained integration branch containing the source, helper scripts, dependency lock, goal definitions, reviews and evidence required to reproduce G01–G03. Review the foundation these bounded journeys actually depend on; reconcile existing findings instead of treating the WIP snapshot as broadly approved. Do not silently expand this into completing #34, all tenants/packs, or the original65 compatibility cases.

Working branch: `feature/engram-verified-foundation`, isolated checkout `/Users/arunmenon/projects/Engram-foundation-gate`, based on snapshot f6fd87ce1086522bdc6fea1846d92ab9d6f50f31. Original working tree and snapshot remain preserved. Branch naming is a target, not a verification claim before this gate passes.

## Steps and acceptance

1. Inventory driver/helper/runtime dependencies and classify snapshot deltas as exercised, shared/guarded, or outside this gate. Static imports overapproximate runtime use; optional Redis/Neo4j imports do not imply their runners are permitted. Inventory and current review notes are source evidence, not proof every imported behavior executed.
2. Create a fresh environment from the committed lock and extras; prove imports resolve into this checkout rather than the old working tree/private source copies. Run unit checks covering the foundation and the existing goal regressions, plus source lint/type checks. Local memory/fakes are diagnostic tests; no Redis/Neo4j service runners.
3. Independently review critical admission/source authority, event receipts, selected pack/worker handoffs, Spanner fence/handshake/read/write ownership, retrieval and exact owned cleanup. Reconcile prior findings with current code/tests. Public tenant dispatch and broader capability completeness remain explicitly bounded. Do not promote old source-only reviews to cloud proof.
4. Rerun G01, G02 and G03 serially from the self-contained checkout on reserved real `engram-compat-target`, using current core+PDLC and exact owner pins. Preserve original goal acceptance; record current pack version and source hashes. If a newer pack changes an oracle, document and independently review it rather than silently weakening assertions. Real configured providers and actual HTTP/workers/read path remain mandatory. Stop and repair only gate-blocking defects; retain failed attempts.
5. Publish a foundation verification/handoff document with dependency map, fresh-environment commands, review-disposition table, local/cloud results, repeat instructions, limits, issue reconciliation and stakeholder walkthrough. Commit/push integration branch and verify remote coordinates. No G04 execution without separate approval.

## Explicit limits

Passing establishes a reproducible reviewed foundation for G01–G03's single-bound normalized/webhook journeys. It does not close open live-retry, retention, ordering, cutover or public tenant-dispatch issues merely because the happy paths pass. If one of those blocks a required journey, record the actual failure and resolve only the necessary bounded repair. Migration work stays excluded. Metrics IAM limitations remain visible; original65 baseline states do not advance automatically.

## Evidence

Static inventory: [dependency CSV](2026-10-08-foundation-gate-dependencies.csv), [import graph and deltas outside closure](2026-10-08-foundation-gate-imports.json). Runtime traces/tests/review will distinguish actual exercised paths. Integration publication is pending until the gate is verified.

## Pause checkpoint

User requested immediate pause on 2026-10-08. Fresh setup, 2,531 unit tests (15 skipped), lint/type and scoped source review complete. G01 integrated rerun passed. G02 rerun interrupted after 17 checks; all workers stopped, owned cleanup verified, core epoch34 restored, all seven application tables empty. G03 not rerun; G04 unstarted. Final review, commit/push and issue publication pending. No further execution without user approval.

## Approved bounded cleanup

Stakeholder approved the necessity recommendations and requested concise, understandable, modular code. Extract only repeated experiment utilities/authentication/snapshot/shutdown into ordinary shared helpers; preserve goal fixtures, oracles and ownership cleanup, with no application runtime redesign. Verify authentication/cancellation/shutdown behavior locally and request one compact Astra diff review. The cloud gate and G04 remain paused.

## G01-only revalidation approval

Stakeholder explicitly authorized G01 only on the cleaned-up foundation. Run `20261008-cloud-cleaned-g01-01` uses source commit `a718377c101fc8ac4ca1b315dfdc7bf2d86eeaee`, explicit predecessor epoch34/digest, original eight scenarios, real HTTP/Spanner/five workers/retrieval, exact owned cleanup and evidence publication. This approval does not restart G02/G03 or G04. No code changes during the run.

G01-only revalidation completed successfully in `20261008-cloud-cleaned-g01-01`: all eight scenarios passed, Astra evidence review found no blockers, owned cleanup verified all seven tables empty and core epoch36 restored. Evidence and review published with issue updates. Execution stops here; G02/G03/G04 require separate approval.

## G02/G03 revalidation approval

Stakeholder subsequently authorized G02 and G03 on the cleaned-up code, serially, preserving original22/28 checks. StartG02 from exact empty core epoch36; startG03 only after verified G02 restoration. Archive source/evidence, independently review, reconcile issues and publish. G04 remains unstarted; no historical migration or broader platform work. This approval supersedes the prior G02/G03 pause only for these two bounded reruns.

Final checkpoint: G02 passed 22 checks, G03 passed 28 checks on cleaned helpers, both independently evidence-reviewed without blockers. Exact owned cleanup restored empty core epoch 40. All bounded gate steps are satisfied; publish evidence and issue receipts, then stop. G04 and the broader #34/#41 backlog are not authorized by this gate. Earlier pause history remains recorded above.
