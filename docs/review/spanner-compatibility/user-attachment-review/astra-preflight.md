# Astra independent review — User attachment/retry slice

Reviewer: existing `astra_memory_episode_review` agent, GPT-6 Astra, medium effort. Scope: current source, three backend transaction implementations, selected-User worker wiring, schema/read alignment, privacy/export/deletion, and bounded real-Spanner harness. This records reviewer messages; it is not a cloud acceptance report.

## Design

Astra recommended persisting the first validated extraction result before User writes, applying User outputs/evidence/counts/completion atomically, counting distinct quoted source Events, preserving established profile identity, requiring explicit matching-context corrections, deterministic mid-session triggers, and fail-closed selected-User provider/source handling. Existing core Entity prep remains outside this User guarantee. The reviewer found one pure domain planner, one narrow port and existing backend transactions proportionate to scope.

## Implementation findings and dispositions

| Finding | Applied correction | Regression |
|---|---|---|
| Two corrections in one receipt could create competing successors. | Require predecessor to preexist; validate against current planned state before any mutation. | `test_competing_corrections_rollback_all_user_outputs` |
| Deletion retained newly private Skills under legacy shared-Skill behavior. | Delete owner-qualified Skills/evidence; preserve another owner's private Skill and legacy shared Skills. | `test_deleting_owned_skills_preserves_other_owner_and_legacy_shared_skill` |
| Missing trigger document could return successful processing. | Selected User extraction raises retryable unavailability. | `test_missing_accepted_trigger_document_is_retryable_not_success` |
| Later prefixes rescanned already-applied historical corrections. | Prior applied receipts identify completed correction sources; prepared receipts do not authorize skipping. | `test_later_trigger_does_not_reinterpret_applied_historical_correction` |

Astra's focused source recheck found no additional blocker. This is not a general platform or Neo4j cloud sign-off.

## Harness findings and dispositions

The reviewer required the correct `Change:user/control|7` identity and actual artifact API read, explicit test consolidation settings and an expected complete Episode, exact evidence rather than inclusion, a distinguishing negative correction quote, a real composed-profile read, and positive second-owner profile/personalization before exclusion checks. These were applied before the first run.

A second pass found a circular final audit: deriving expected owner/support from the node being checked could miss absent/extra nodes. The final audit instead derives the exact artifact set from frozen receipts and submitted inputs, independently recomputes identities/quotes/support unions and compares final IDs/owners/counts/edges. Astra cleared the bounded harness for execution, explicitly reserving live acceptance for saved results and final review.

Attempt 01 failed at User API authorization after real extraction: the test principal only had `api`. User endpoints require `admin`. The shared harness now accepts explicit roles while preserving its default, and this runner grants `api` + `admin` through the actual TenantCatalog. Production permissions were unchanged. The reviewer cleared that correction and the added controlled interest/Skill replay probes, requiring attempt 01 remain labeled an authorization-setup failure.

## Live-run corrections and rechecks

- Attempt02 exposed actual missing User personalization. The bounded owner-context hook was reviewed for selection, owner, canonical identity, exact evidence, counts and honest limits. A noncanonical-profile regression was added at Astra's request.
- Attempt03's User+Memory rejection oracle compared the whole database while timed consolidation was active. The same 422/no-write expectation now runs only after real workers settle, stop and are awaited; Astra confirmed this fixes synchronization without weakening expectations.
- Attempt04 transport cause remains unproven. Exact ledger reconciliation confirms the attempted PR Event ID absent. Fresh connections and pre-call intent/error journaling were reviewed; no automatic retry was added.
- Attempt05 used unsupported artifact API fields. It correctly received 422. The supported `seed_node_ids` request and actual-model preflight are now used; Astra verified the corrected fields. PDLC06 passed 12 checks.
- Attempt06 User+Memory passed 133 checks. Before final completion, Astra confirmed existing interest Entities could have `last_seen < first_seen`. Chronological max preservation now applies to owner/ABOUT/interest. The public-worker/restart regression covers differing ISO offsets, first/last timestamps, type, mention count and provider reuse. Astra cleared final-source User/User+Memory attempt07; the unchanged PDLC06 User-off result remains applicable.
