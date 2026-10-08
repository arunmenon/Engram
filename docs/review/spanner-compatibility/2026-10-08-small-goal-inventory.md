# Small goal inventory

Status: G01 verified, independently reviewed and recorded demonstration published; stakeholder approval not assumed. G02 explicitly authorized on 2026-10-08 and technically verified in run 20261008-cloud-g02-all-03; final review/publication reconciliation in progress; G03 and later remain proposed and unstarted. User chooses each goal to execute. The former combined autonomous goal is paused and retired from the execution plan, not completed. No automatic progression between goals.

Every goal must follow the [verification and stakeholder demonstration standard](goal-verification-standard.md), produce its own detailed verification document, and end with a stakeholder walkthrough. G01's [verification document](2026-10-08-goal-01-verification.md) contains the recorded real-Spanner results.

Owners: #34 pack integration; #42 optional memory/user within #34; #41 real-Spanner compatibility. This inventory reorganizes work and does not discard existing acceptance criteria or close issues.

## Execution control and reuse

Explicit user approval is required before starting each goal, including after the preceding goal passes. No automatic continuation into the next goal. The old broad goal is retired from this execution plan and must remain paused; available goal controls cannot delete or cancel it, and it must not be falsely marked complete to replace it.

Preserve and reuse existing authorized foundational changes, including pack composition/capabilities, tenant binding and fences, accepted-event contracts and duplicate handling, authenticated source trust, worker disposition checks and projection primitives. Check their relevance and current correctness; reuse is not an assumption that all foundations are complete. Record reused versus new work and any unresolved review findings in each verification document. Do not reset, discard or rewrite unrelated work as part of this planning transition. This documentation commit does not publish the existing runtime changes.

The first three stakeholder goals are G01 PR activity (specified below), G02 PRD→Requirement→HLD→LLD including approval/revision and invalid references (original rows 8–10), and G03 explicit design/requirement→WorkItem→Change→review/test traceability including a failing test and absent-mapping case (original rows 11–12). G02 now has an authorized detailed specification in 2026-10-08-goal-02-planning-journey.md; G03 remains proposed and unstarted. Original rows 1–7 contain supporting safety work; only the eight scenarios explicitly listed in G01 are its acceptance scope, not all possible ingestion/update cases.

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
| 25 | Upgrade and rebuild recovery | Historical interpretation and original ledger preserved |
| 26 | Spanner sign-off | 65 baseline cases plus agreed extensions pass with evidence |

Proposed buckets, in order: working PR journey; input/update safety (included in G01 where specified); planning-to-implementation; remaining PDLC lifecycle; optional/composed packs; tenant isolation; recovery and compatibility. G02 is the separately authorized PRD/Requirement/HLD/LLD journey now technically verified; subsequent goals remain unstarted.

Every execution goal must define input, action, expected result, forbidden effects, evidence, issue ownership and stop boundary before execution. Real-Spanner functional verification takes priority. No percentage or test aggregate substitutes for accepted scenarios.

## Subsequently discussed grouping (proposal; no execution approval)

G02 was separately authorized. G03 and every later goal below remain unstarted. These numbers express the stakeholder discussion; detailed predeclared scenarios are required before selecting each goal.

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
| G17 | Pack upgrade/rebuild interruption, historical interpretation and ledger preservation |
| G18 | Full65-scenario Spanner baseline plus agreed additions; evidence-backed sign-off |

Supporting safety cases not completed by the selected journeys remain explicit, including protected-field clearing, conflicting semantic identities and full historical replay. Grouping is not closure. Every goal ends with its verification document, stakeholder demo, independent review, issue reconciliation and explicit stop boundary.
