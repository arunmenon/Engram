# G01 — Prove PR activity end to end through Engram on real Spanner

Status: eight cloud scenarios PASSED and independently reviewed; verification document prepared for stakeholder delivery. Explicitly authorized by user on 2026-10-08. Do not start G02 or unrelated feature work. Prior combined goal remains paused; its requirements are not declared complete. G01 execution is tracked here because the available goal controls cannot replace an unfinished paused goal without falsely completing it.

Follow the [mandatory verification and stakeholder demonstration standard](goal-verification-standard.md). Populate [G01 verification](2026-10-08-goal-01-verification.md) with the full per-scenario trace and deliver the stakeholder walkthrough before reporting this goal delivered.

## Objective

Using core + PDLC with memory and user processing disabled, prove all eight scenarios below through the actual source adapter, Engram API, real Spanner ledger, running background workers, real Spanner graph, and Engram retrieval API with supporting evidence. Deliver a repeatable demonstration with separate pass/fail results and retained redacted evidence.

Example identifiers are illustrative: repository payments, PR 7, ticket APP-42; use isolated run-prefixed repositories/IDs during execution. Do not assume literal event names, source fields, relationship names, response shapes or adapter support: inspect current contracts and record exact mappings before running. Any missing support is explicit work or a blocker, never silently bypassed.

## Eight scenarios

| ID | Input and action | Required observations |
|---|---|---|
| PR01 | Submit a saved, attributed public GitHub PR-opened source payload via the real supported source adapter and ingress | Accepted event in ledger; exactly one correctly identified Change with expected repository/number/title; event-to-artifact evidence; retrieval returns correct artifact and evidence |
| PR02 | Submit a later source update changing that PR's title | Same Change updated, no extra Change; both events and their provenance retained; retrieval shows current title |
| PR03 | Resend the identical source delivery/event with the same stable identity | No extra logical event, Change or relationship; documented idempotent response; retrieval unchanged |
| PR04 | Submit incomplete PR input, including missing repository | Clear adapter/admission rejection; no rejected event in ledger, no graph effects; stage and response recorded |
| PR05 | Submit a merge source payload explicitly referencing APP-42 | Same Change marked merged; exact pack-declared WorkItem relationship; creation/merge evidence retained and retrievable; any prerequisite WorkItem created through supported ingestion, never direct graph insertion |
| PR06 | Submit a separate PR and merge it without a ticket reference | Merge succeeds; no invented ticket node/link; correct merged state and evidence retrievable |
| PR07 | Submit PR 7 in two distinct repositories | Two distinct Changes; updates and retrieval scoped correctly; no shared identity or cross-repository ticket/evidence contamination |
| PR08 | After merge, submit an older update using a distinct delivery ID | Define event ordering/tie policy before execution; verify old update cannot silently revert merged state; history/evidence preserved; retrieval matches policy |

## Execution boundary and anti-shortcut rules

- Actual Engram code and real Spanner for the full path in every accepted scenario. No memory substitute, mocked Spanner, direct ledger/graph fixture insertion, calling projector methods instead of workers, or hand-seeding expected artifacts.
- Show original source payload and adapter output. Attribute source URLs, collection time and hashes. Clearly label modified/reconstructed lifecycle payloads; do not present them as captured GitHub deliveries. No live GitHub mutation is required or authorized by this goal.
- Start real worker loops, not merely constructors. Use actual configured providers where required; disclose any scripted/non-production provider. Such a substitution cannot prove behavior that depends on that provider.
- Use the authorized disposable test database. Record project/instance/database without credentials. Preserve unrelated/source databases and serialize fixture mutation. Do not assume multi-tenant isolation is proved by this single-target goal.
- Core mandatory; memory/user disabled. Verify the effective configuration and absence of forbidden user/memory outputs. Necessary core entity/summary activity is not automatically a violation: list the enabled responsibilities first.
- Determine exact expected nodes, edges, properties, event identities and evidence IDs before each run. Record known initial state and allowed changes. Check forbidden extra writes as well as expected writes.
- Use bounded polling of durable processing outcomes; timeout is a failure or explicit blocker, not permission to repair the graph manually.
- Failed, blocked, partial, skipped or manually repaired scenarios do not count as passes. Fixes require rerunning affected scenarios through the whole path.
- Local tests and adapter/component checks are supplementary, not end-to-end evidence. Success receipts alone prove neither projection nor retrieval.

## Tracking and verification

Register each execution in the existing compatibility run tracker before running. Retain code/worktree fingerprint, pack versions/configuration, source fixture hashes, expected results, redacted HTTP requests/responses, worker outcomes, exact Spanner observations and retrieval evidence. Link confirmed defects to existing issues where applicable; document new Spanner-related defects without duplicate filing. Update affected issue/run status truthfully; do not close broader issues on this slice alone.

Checkpoints presented to user: (1) exact fixture/mapping/expected-result table and prerequisites; (2) PR01 full-path result; (3) remaining seven individual results; (4) final repeatable demo and evidence links. Do not silently switch to another goal if blocked. No general refactor or unrelated bug work; necessary prerequisites must be named and their impact on the goal reported.

## Done

All eight scenarios pass on current Engram through the complete real-Spanner path; disabled capabilities remain absent; relevant implementation review findings are resolved; demonstration script and instructions reproduce the checks; issue/run records and redacted evidence agree. Report remaining limitations. This does not claim all PDLC events, two-tenant isolation, G02, #34 completion or #41 sign-off.

## Goal command text

Complete only G01 as specified in docs/review/spanner-compatibility/2026-10-08-goal-01-pr-activity.md: prove all eight PR activity scenarios end to end through the actual source adapter, Engram API, real Spanner ledger, running workers, real Spanner graph and retrieval with evidence, with core + PDLC and memory/user disabled. Follow all fixture, no-bypass, exact-result, failure, review and evidence requirements in that specification. Preserve existing authorized work. Register and update runs and relevant issues; do not count local-only, blocked, partial or manually repaired results as passes. Deliver the repeatable demo and individual results. Stop after G01; do not start G02 or the former combined goal.
