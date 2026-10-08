# G05 — One connected PDLC journey and cross-journey retrieval

Status: AUTHORIZED, not yet run. G05 only; stop before G06. Reuse reconciled foundation, existing PDLC3.0 and ordinary engine paths. No separate foundation track, G01–G04 reruns or historical migration.

## Concrete outcome

Create one password-reset journey through authenticated Engram HTTP on real Spanner: PRD → expiry Requirement → HLD → LLD → ticket → PR → reviews/tests → Release → failed/successful production attempts and staging. Add an approval for the exact HLD revision. Align tested commit, merged commit and deployed artifact to abc123. Retain the connected dataset for stakeholder review; no cleanup of a successful run without explicit later authorization.

Compose existing G03 and G04 fixture producers into the same G05 identity scope; do not directly create graph artifacts. Include a separate newsletter feature with colliding local requirement/test/PR/ticket values and its own release/deployment, plus unlinked artifacts. All explicit source references, identity fields, edge directions/properties, evidence and forbidden effects are frozen in scripts/engram_goal05_fixtures.py before execution.

## Required scenarios and verification

- CJ planning: PRD, Requirement, HLD/LLD, revision-specific HLD approval. Retrieval identifies exact artifacts and event evidence.
- CJ implementation: ticket/PR explicitly connect planning; changes-requested and approved reviews plus failed/passing TestRuns remain distinct. TestRun commit, PR head/merge and deployment artifact agree.
- CJ operations: PR merge then release, failed production attempt, later succeeded attempt, staging; all links explicit or exact declared SHA matches. Merge/release never implies deployment success.
- CJ controls: unrelated newsletter chain and unlinked PR/test/deployment/release remain separate; duplicate, conflict, invalid requirement reference and invalid deployment reference leave full seven-table fingerprints unchanged. Invalid candidate absent through HTTP.
- CQ1 Requirement→deployment: exact main graph and both production outcomes.
- CQ2 Release→requirements: exact reverse chain, with HLD approval/reviews/tests.
- CQ3 Successful deployment→design/code/tests: exact chain for that one attempt; no automatic sibling deployment expansion.
- CQ4 Explicit failed+successful production seeds: both outcomes together with their common chain; staging excluded as an unseeded sibling.
- CQ5 LLD→operations: exact forward/backward chain and evidence.
- CQ6 Text discovery: fifteen-minute question finds the expected main graph without unrelated-feature artifacts.
- CQ7 Newsletter Requirement: exact unrelated chain, main chain excluded.
- CQ8 Unlinked deployment: only its own deployment/component; no invented requirement, Change or Release.

For each input: actual HTTP response, exact ledger document and tenant/database/bundle/epoch/source authority, five worker zero lags/no DLQ/pending, exact domain nodes/properties/declared links, all stored DERIVED_FROM and newest API provenance. Queries require exact declared node/edge sets, edge properties, both review/test outcomes and no truncation. LLM-generated proposals/artifacts are separately retained, never substituted for expected explicit links. Local tests supplement, never replace cloud acceptance. Do not alter expected results to match the run; retain failed attempts.

## Retention and ownership

Start only on the known empty reserved engram-compat-target database in portiq-mvp/engram-experiment, pinned core owner epoch42. Use one private bound tenant compat-control, core+PDLC3.0, optional memory/user disabled and unevaluated experiment gate explicit. No public multi-tenant or whole-pack/baseline65 claim.

On full successful execution: stop/settle workers and HTTP server, verify all attribution and exact final owner, save all table fingerprints and registered cleanup keys, retain the active G05 owner/data instead of restoring empty core. Persist run/bundle/source provenance so a later authorized demo can reconstruct the same binding. No process stays running unattended. An interrupted/failed run keeps existing exact-owned cleanup/restoration; a successful retained run must not be cleaned or reused by a later goal without approval. Retention is a demo dataset, not historical migration.

## Completion

Astra medium read-only design/harness review, targeted local contract/projection/retrieval checks, final-source real-Spanner run, independent evidence review, detailed verification and recorded stakeholder walkthrough, GitHub issue reconciliation and feature-bucket assessment, commit/push. Broad issues close only on full acceptance. Stop before G06; stakeholder sign-off is never inferred. G01–G04 results remain their own pinned runs.

Original CQ1/CQ4 natural-language queries remain unchanged. #50 fixes resolved-seed loose-word widening; no oracle relaxation. Source review: 2026-10-08-astra-g05-source-review.md. Local baseline owner-query failure is retained separately and does not count as passing.
