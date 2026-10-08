# Small goal inventory

## Current checkpoint — G06 verified; stop before G07

G01–G06 have bounded published verification records. G05's connected dataset is
retained in `engram-compat-target`; G06's separate dataset is retained in
`engram-g06-target`. Both require explicit approval before deletion or reuse.

[G06 verification and recorded stakeholder walkthrough](2026-10-08-goal-06-verification.md):
50 real-Spanner checks passed, independent evidence review found no blockers,
and [actual issue reconciliation](2026-10-08-g06-issue-reconciliation.json) closed
scoped #51–#53 while eleven broader issues remain open. Both failed full attempts
are preserved with runner/oracle explanations. No whole-pack/baseline65 or
stakeholder-sign-off claim is made. No new feature bucket was needed.

G07 and later remain unstarted and require explicit stakeholder selection. Older
status paragraphs below are historical checkpoints, not current authorization.
The retired broad goal stays paused.

## Scope decision — disposable experiments (2026-10-08)

Applies to every current goal: historical-data migration, migration adapters, conversion of old pack identities, and cross-version historical upgrade analysis/tests are OUT OF SCOPE. Do not spend implementation, review or analysis effort on them or use their absence as a completion blocker. Runs start with an explicitly owned disposable dataset. Priorities are ontology-pack composition and the actual Engram ingestion → ledger → workers/projection → Spanner graph → retrieval/evidence path.

Revision history, approvals, retries, ordering and recovery/replay of events created within the same experiment and pinned pack configuration remain functional tests. They are not historical migration. A fresh connected demo dataset must be created through Engram ingestion; retaining it for an approved demonstration does not add migration scope. Existing migration tickets/history are preserved as deferred future work; do not silently count their scenarios as passing or close them. A migration-only baseline case is explicitly deferred, not a current-goal sign-off requirement. Migration work requires a separate explicit future authorization.

Status: G01–G03 verified and reconciled. G04 separately authorized and verified: 31 real-Spanner checks, Astra evidence review clear, recorded walkthrough published and GitHub issues reconciled. G05 and later require separate approval and remain unstarted. Earlier checkpoint sections below retain history; latest G04 record is authoritative. The former broad goal remains paused/retired.

Every goal must follow the [verification and stakeholder demonstration standard](goal-verification-standard.md), produce its own detailed verification document, and end with a stakeholder walkthrough. G01's [verification document](2026-10-08-goal-01-verification.md) contains the recorded real-Spanner results.

Owners: #34 pack integration; #42 optional memory/user within #34; #41 real-Spanner compatibility. This inventory reorganizes work and does not discard existing acceptance criteria or close issues.

## Approved foundation gate before G04

Stakeholder authorized a bounded foundation handoff gate before G04: consolidate the snapshot runtime and walkthrough evidence into one reproducible integration branch, reconcile prior reviews, verify a fresh locked environment, and rerun G01–G03 serially on real Spanner. See the [gate plan](2026-10-08-foundation-gate-plan.md), [independent review](2026-10-08-foundation-gate-astra-review.md) and [verification/handoff record](2026-10-08-foundation-gate-verification.md). Gate is paused at stakeholder request; fresh local checks and G01 rerun passed, G02 rerun interrupted with verified cleanup, G03 rerun/publication pending. This approval does not start G04, resume the retired broad goal or authorize migration.

## Execution control and reuse

Explicit user approval is required before starting each goal, including after the preceding goal passes. No automatic continuation into the next goal. The old broad goal is retired from this execution plan and must remain paused; available goal controls cannot delete or cancel it, and it must not be falsely marked complete to replace it.

Preserve and reuse existing authorized foundational changes, including pack composition/capabilities, tenant binding and fences, accepted-event contracts and duplicate handling, authenticated source trust, worker disposition checks and projection primitives. Check their relevance and current correctness; reuse is not an assumption that all foundations are complete. Record reused versus new work and any unresolved review findings in each verification document. Do not reset, discard or rewrite unrelated work as part of this planning transition. This documentation commit does not publish the existing runtime changes.

The first three stakeholder goals are G01 PR activity (specified below), G02 PRD→Requirement→HLD→LLD including approval/revision and invalid references (original rows 8–10), and G03 explicit design/requirement→WorkItem→Change→review/test traceability including a failing test and absent-mapping case (original rows 11–12). G02 now has an authorized detailed specification in 2026-10-08-goal-02-planning-journey.md; G03 is separately authorized and verified. Original rows 1–7 contain supporting safety work; only the eight scenarios explicitly listed in G01 are its acceptance scope, not all possible ingestion/update cases.

## First selected goal

[G01: PR activity end to end](2026-10-08-goal-01-pr-activity.md) replaces the earlier proposed goals 1–7 as the first independently selectable execution goal. It contains eight acceptance scenarios. G01 was explicitly authorized on 2026-10-08. G02 was subsequently authorized separately; do not expand either goal into G03.

## Priority inventory

Numbers below preserve the original discussion's goal references; rows 1–7 are consolidated into G01 above. Remaining rows are planning inventory, not fully specified execution goals.

| Original order | Outcome | Observable verification |
|---|---|---|
| 1 | Activate core + PDLC without memory/user | Selected configuration runs; disabled processing absent |
| 2 | Create and retrieve PR artifact | Exact Change and event evidence |
| 3 | Merge PR and connect ticket | Same Change updated; explicit ticket link and history |
| 4 | Repeatable demonstration | Documented script with per-scenario assertions |
| 5 | Reject invalid PDLC payloads | Clear rejection and no ledger/graph writes |
| 6 | Safe duplicate delivery | Matching retry idempotent; conflicting ID rejected |
| 7 | Preserve versus clear fields | Exact values after omitted/clear/protected-field cases |
| 8 | PRD to requirements | Correct explicit links with evidence |
| 9 | Requirement to HLD to LLD | Exact connected design chain |
| 10 | Approval and revision history | Old approval retained; revision not implicitly approved |
| 11 | Design to implementation | Explicit Requirement/design/WorkItem/Change traceability |
| 12 | Reviews and verification | Correct review/test outcomes and evidence |
| 13 | Release and deployment | Correct shipped Change and deployment outcome |
| 14 | Incident and corrective action | Explicit evidence-backed feedback chain |
| 15 | All PDLC events (original 23; current 25 after G02 extensions) | Valid/invalid fixtures and exact graph/retrieval assertions |
| 16 | Core alone | Supported common processing; optional outputs absent |
| 17 | Optional memory | Enabled behavior and disabled absence |
| 18 | Optional user | Enabled behavior and disabled absence |
| 19 | CRM and unfamiliar pack | Same composition machinery; correct outputs |
| 20 | Tenant ingestion/retrieval separation | Colliding IDs in separate databases never cross |
| 21 | Tenant background/history separation | Workers, cursors, caches, replay and admin stay scoped |
| 22 | Interrupted worker recovery | Final artifacts/evidence correct; pending content retained |
| 23 | Late events and delayed relationships | Agreed ordering and repair verified |
| 24 | Honest retrieval limits | Pagination/deadlines/rejected links/incompleteness checked |
| 25 | Same-pack replay and graph recovery on disposable data | Reprocess this experiment’s accepted events; preserve its ledger; no historical migration |
| 26 | Spanner sign-off | 65 baseline cases plus agreed extensions pass with evidence |

Proposed buckets, in order: working PR journey; input/update safety (included in G01 where specified); planning-to-implementation; remaining PDLC lifecycle; optional/composed packs; tenant isolation; recovery and compatibility. G02 is the separately authorized PRD/Requirement/HLD/LLD journey now technically verified; G03 is authorized; G04 and later remain unstarted.

Every execution goal must define input, action, expected result, forbidden effects, evidence, issue ownership and stop boundary before execution. Real-Spanner functional verification takes priority. No percentage or test aggregate substitutes for accepted scenarios.

## Subsequently discussed grouping (G03 authorized; later goals proposed)

G02 was separately authorized. G03 is now separately authorized; G04 and every later goal remain unstarted. These numbers express the stakeholder discussion; detailed predeclared scenarios are required before selecting each goal.

| Goal | Proposed bounded outcome |
|---|---|
| G03 | Explicit design/requirement → ticket/PR → review and passing/failing test traceability; no invented links |
| G04 | Change → release → failed/successful deployment; merge/release does not imply deployment success |
| G05 | Rebuild the individual slices through Engram into one retained connected dataset; exercise cross-journey retrieval and unrelated-feature separation. Retain this combined demo dataset until stakeholder approves cleanup; this retention proposal does not retroactively change disposable G01/G02 cleanup |
| G06 | Incident → explicit corrective action and evidence-backed feedback |
| G07 | Reconcile whole PDLC event coverage; original23 plus approved pack extensions (G02 pack2.0 catalog25), not a fixed23-event completeness claim |
| G08 | Core alone, optional artifact absence |
| G09 | Memory capability enabled/disabled behavior and retrieval |
| G10 | User capability enabled/disabled behavior and stored-data visibility |
| G11 | CRM, unfamiliar pack and compatible compositions through same engine |
| G12 | Tenant ingestion/retrieval separation with colliding IDs in separate Spanner databases |
| G13 | Tenant workers, caches, replay and admin separation |
| G14 | Interrupted worker processing and recovery |
| G15 | Broader late-event, ordering and delayed relationship handling |
| G16 | Retrieval pagination/deadlines/rejected relationships and honest incompleteness |
| G17 | Same-pack graph rebuild/replay interruption and ledger preservation using this experiment’s own events; historical migration and cross-version upgrades deferred |
| G18 | Full65-scenario Spanner baseline plus agreed additions; evidence-backed sign-off |

Supporting safety cases not completed by the selected journeys remain explicit, including protected-field clearing, conflicting semantic identities and recovery/replay within the current experiment. Historical migration and cross-version replay are deferred. Grouping is not closure. Every goal ends with its verification document, stakeholder demo, independent review, issue reconciliation and explicit stop boundary.

G02 [verification and recorded stakeholder walkthrough](2026-10-08-goal-02-verification.md) is published; #46 closed, broad issues remain open. Stakeholder sign-off is not inferred. G03 was subsequently authorized separately. Stop boundary is now G04; all subsequent goals remain unstarted pending explicit approval.

G03 verified: [exact implementation/review/test specification](2026-10-08-goal-03-implementation-journey.md). G04 and later remain unstarted. Historical migration excluded.

G03 [verification and recorded stakeholder walkthrough](2026-10-08-goal-03-verification.md) is published:28real-Spanner checks passed, no review blockers, seven issues updated and kept open for remaining acceptance. G04 and later remain unstarted.

## Cleaned foundation revalidation checkpoint

The stakeholder separately authorized G01, then G02/G03. All passed on `feature/engram-verified-foundation`: G01 eight scenarios, G02 22 checks and G03 28 checks, with independent evidence reviews and exact cleanup. See the [bounded foundation handoff](2026-10-08-foundation-gate-verification.md). Original runs and failed/interrupted reruns remain preserved. G04 has not started and needs explicit approval. The retired broad goal remains paused.

## G04 authorization (latest checkpoint)

User explicitly authorized G04 after the completed foundation reconciliation and G02/G03 reruns. Execute [G04 release/deployment specification](2026-10-08-goal-04-release-deployment.md) only, with its [verification record](2026-10-08-goal-04-verification.md). Earlier “G04 unstarted” paragraphs are historical checkpoints. No separate foundation work or G01–G03 cloud reruns. G05 remains unstarted pending separate approval.

G04 technical result: [verification and recorded walkthrough](2026-10-08-goal-04-verification.md),31checks passed, seven application tables empty at restored epoch42. Current PDLC3.0 catalog has26events; prior23/25counts describe earlier pack versions, not current completeness. No new foundation track or G01–G03 cloud reruns. G05 remains unstarted.

## G04 completed checkpoint

G04 is verified and published with [recorded stakeholder walkthrough](2026-10-08-goal-04-verification.md), [Astra evidence review](2026-10-08-astra-g04-evidence-review.md) and [actual issue receipts](2026-10-08-g04-issue-reconciliation.json). #47 closed; eight broader issues updated and remain open. G01–G03 results remain pinned to their prior versions, not retroactively proved on PDLC 3.0. No new feature bucket, no foundation track/reruns, no migration. G05 remains unstarted pending explicit approval; the retired broad goal remains paused.
