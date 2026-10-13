# Memory Episode verification and stakeholder walkthrough

Status: Memory Episode slice accepted after selected live/local verification and independent Astra evidence review. Stakeholder has expanded the overall Memory goal to include Belief and Goal producers; those are pending and are not covered by these results. This document does not establish pilot readiness.

## What changed and why

The Memory pack previously described Episode nodes without a worker producing them. This slice connects an explicit `memory.episode.v1` capability to the existing consolidation worker. Core remains mandatory. With Memory disabled, existing episode/session summaries remain available but typed Episodes are neither produced nor returned by the selected reader. Belief and Goal producers are outside this change.

Consolidation sorts actual source Events by `occurred_at` and splits when the gap exceeds 30 minutes. Each Episode identifies one exact membership snapshot. Repeating the same membership reuses its identity; a late bridging event produces a new snapshot while keeping earlier snapshots as history. This is not a latest partition, closed session, or inferred domain relationship.

The worker first stores its Summary and actual Summary-to-Event evidence. It validates stored source rows, Summary ownership/count/time bounds and exact evidence, then creates an incomplete Episode, writes CONTAINS/DERIVED_FROM and Summary-to-Episode edges, and finally marks it complete. Interrupted writes cannot expose a complete snapshot. Retrieval rechecks actual stored evidence and returns its existing nodes and relationships rather than inventing them.

Episode production is scheduled consolidation, not an immediate side effect of accepting one event. The existing defaults are a six-hour interval and reflection threshold 150 (the worker uses event count × 5 as its proxy, roughly thirty Events). The live verification explicitly uses a twenty-second interval and threshold 5 so the small fixtures qualify. These are recorded test settings, not a claim about default latency.

For core+PDLC+Memory, one accepted PDLC event participates in two complementary views: PDLC projection creates the Change and its source evidence, while Memory consolidation groups the common Event into an Episode. They meet through the Event; the Memory worker does not reinterpret a Change as a Goal or invent an Episode-to-Change relationship.

No service, database table, migration path or separate worker was added. Existing Summary prose can use the real LLM; membership remains deterministic.

## What to show in the demo

1. Core only: send two observations through the authenticated event API. Show the ledger, projected Events and episode/session Summaries, then query the session timeline. There must be no typed Episode or CONTAINS relationship.
2. Core plus Memory: send observations five minutes apart. Query the timeline and inspect the one two-member Episode, its exact Summary, both Events, CONTAINS/DERIVED_FROM, Summary evidence and originating Event provenance.
3. Add an observation forty minutes after the first. Show a separate one-member Episode because the gap from the second Event is thirty-five minutes.
4. Deliver an older observation at minute twenty. Show a new four-member Episode: it bridges both groups. Show the old two-member and one-member snapshots still present as explicit membership history.
5. Retry the identical request, then observe another consolidation output. Ledger membership and Episode/evidence identities must remain unchanged.
6. Send equivalent activity in another session. Positively retrieve its Episode in that session; demonstrate its absence from the original session's answer.
7. Ask for only one node. Show the explicit truncation indicator and no edges pointing to omitted nodes.
8. Core plus PDLC plus Memory: ingest an admitted Change event through the same event API. Show its membership in an Episode through timeline retrieval and independently retrieve the Change and source evidence through the artifact API. No Episode-to-Change link is invented.
9. Send an envelope without a session ID. Show rejection and no ledger or artifact attributable to that rejected event.

## Verification boundaries

Primary live acceptance uses authenticated HTTP -> Spanner ledger -> all five real worker loops -> Spanner graph -> HTTP retrieval. Storage inspection is a separate final audit, never a substitute for API acceptance. Real summary generation runs through the configured model client. No direct artifact insertion, scripted model result or manual repair counts as live acceptance.

M08 projection-order recovery, M09 interrupted writes, M13 disabled reads over existing Episodes, corruption cases and storage-limit probes are supplementary local tests at public worker/storage/retrieval seams. Fault injection uses reference storage only; it is not a live cloud fault-injection claim. Local and cloud results must be reported separately.

Episode context currently considers at most ten snapshots and 500 aggregate member references per query. If those bounds or the answer budget omit data, retrieval reports truncation. There is no claim that pagination advances the Episode candidate window. Invalid snapshots are suppressed. This supports bounded session context, not exhaustive historical search.

The live runtimes are privately bound authenticated applications, not the public multi-tenant dispatcher. The development unevaluated-bundle gate is enabled. Sequential database reuse does not prove concurrent tenant isolation. Existing user-attachment and enrichment findings remain separate pilot prerequisites.

## Independent review and dispositions

Astra reviewed the implementation and runner. Corrections applied:

- Validate stored Summary ownership, count, time range and exact Summary-to-Event evidence, rather than trusting a supplied object or existence alone.
- Reject extra Episode membership and reads whose edge bounds prevent establishing exactness; return actual Summary evidence.
- Derive Episode time bounds from the validated stored Summary and check them again on reads.
- Abort database reuse after any shutdown error.
- Replace inclusion-only assertions with independently computed identities, exact memberships/edges, Summary and Event checks.
- Observe a subsequent consolidation result instead of sleeping and assuming a retry was processed; positively verify the unrelated session before asserting exclusion.
- Retrieve the PDLC-containing Episode through HTTP and audit final stored rows independently.

Astra's runner rechecks identified no remaining blockers. The final independent evidence review validated both Memory-enabled configurations, the core control, source hashes, exports, subsequent consolidation cycles and final rows; no blocker remains for this scoped slice.

## Evidence and issue reconciliation

Scenario specification: `memory-episodes-goal.md`.
Runner: `scripts/engram_memory_episodes_demo.py`.
Final live attempt: `runs/memory-episodes-1013-04/`; earlier controls and retained failures are under attempts `01`, `02` and `03` (inputs, expected memberships, HTTP responses, checks, final rows, verified exports and retained fingerprints).

The runner refuses to overwrite evidence. Only the authorized assessment database is reused; prior retained rows are exported, hash-verified and checked against their saved owner/fingerprint before exact-key reset. The final dataset remains retained.

Local affected regression suite: **134 passing tests**, including **22 Memory-specific cases**. Ruff passes and mypy passes for all seven modified/new production Python files. The broader unit run returned **2,746 passed, 15 skipped and one failure**: `test_webhooks_build_a_pdlc_graph[memory]` fails its existing PDLC evaluation gate on the unchanged baseline as well. Baseline proof and complete output are saved under `runs/memory-episodes-local/`; this failure is not counted as fixed or hidden. A pre-existing stale PDLC assertion omitted the already existing `incident` intent; baseline failure was established separately before updating that expectation. This is not a new Memory intent.

The scoped results below do not close an umbrella or establish pilot readiness. #42/#34/#39/#41 progress reconciliation is published below; all four issues were reread and remain OPEN.

## Attempts and exact-source follow-up

Attempt 01 passed the core-only control but stopped at M02 because the runner incorrectly looked for Event session identity in `attributes.session_id`. Engram's canonical answer puts it in `provenance.session_id`. The actual Episode, Summary and evidence were present. Only the field-location assertion was corrected; the failed attempt remains saved.

Attempt 02 passed core-only (8 checks), core+Memory (23 checks) and core+PDLC+Memory (27 checks). While that process was running, one final producer guard was tightened: a bounded Summary source read now reserves a spare row and rejects saturation, so an existing Summary-to-Episode link cannot hide an extra source link. A regression verifies that case. Attempt 03 began reruns on that final source, but stopped at the runner synchronization failure described below; its PDLC configuration was not run. Attempt 04 reruns both Memory-enabled configurations. The core-only path does not call the changed producer. Source hashes are saved per run.

M08, M09 and M13 are **local PASS**, not live cloud fault-injection or cross-configuration database switching claims. M08 verifies missing source projection blocks completion and subsequent legitimate source/evidence writes allow retry. M09 exercises interruption through the public consolidation handler and verifies retrieval before/after retry. M13 checks a core-only composed reader over stored Memory Episodes. Additional probes cover corrupted Summary properties, missing/extra evidence, corrupted Episode bounds, late bridging history, eleven snapshots and 501 aggregate source references.


Attempt 03 stopped at a runner synchronization failure: it could capture only old two-/three-event session Summary identities before the new four-event session Summary was written, then wait for those old revisions to update. Retained rows and repeated cycle logs show the current four-event Summary continued updating normally. The runner now waits for a session Summary whose event_count matches the projected session Event count and saves M04 before/after snapshots. Astra found no blocker in that bounded correction. Attempt 04 reruns both Memory-enabled configurations without changing runtime behavior or expected graph outcomes. Attempt 03 and its retained dataset/export records remain preserved.


## Final results

**58 selected live assertions passed:** core-only control in attempt02 (8), final-source core+Memory in attempt04 (23), and final-source core+PDLC+Memory in attempt04 (27). Both final configurations shut down cleanly, with no pending deliveries or dead letters. The final PDLC+Memory dataset remains retained in the authorized assessment database; all preceding datasets have verified exports. Cloud Monitoring export still reports its existing 403 permission error; monitoring export is not claimed as verified.

| Case | Result | Verification |
|---|---|---|
| M01 core only | PASS, live | Core02 episode/session Summaries; no Episode or CONTAINS |
| M02 exact Episode and evidence | PASS, live | Memory04 and PDLC+Memory04 authenticated timeline responses and independent row audits |
| M03 temporal split | PASS, live | Two-event group plus separate later event |
| M04 retry and reconsolidation | PASS, live | Saved before/after ledger, evidence identities and changed current session Summary timestamp |
| M05 late arrival | PASS, live | Older bridge event joins groups by occurred_at |
| M06 snapshot history | PASS, live | Exact old and new membership snapshots retrieved together |
| M07 session isolation | PASS, live | Other session positively retrieved, then excluded from original session |
| M08 source projection recovery | PASS, local supplement | Missing Event prevents completion; later source/evidence projection permits retry |
| M09 interrupted write recovery | PASS, local supplement | Public worker handler and retrieval before/after reference-storage fault/retry |
| M10 bounded answer | PASS, live + local | API max_nodes=1; explicit truncation and no dangling edges; additional 10/500 storage-bound probes |
| M11 PDLC coexistence | PASS, live | Five-member Episode and Change independently retrieved through their APIs with exact evidence |
| M12 invalid envelope | PASS, live | Rejection; unchanged ledger and no artifact attributable to rejected identity |
| M13 disabled read | PASS, local supplement | Core-only composed reader excludes stored Memory Episodes |

## Repeat the live verification

Use the project Python environment with Spanner/LLM dependencies and valid experiment service-account impersonation credentials. From this branch's repository root, run:

```sh
PYTHONPATH=src:scripts python scripts/engram_memory_episodes_demo.py \
  --run-id memory-episodes-repeat-01 \
  --previous-record docs/review/spanner-compatibility/runs/memory-episodes-1013-04/pdlc-memory-retained.json \
  --configurations core memory pdlc-memory
```

Choose a fresh run ID. The previous-record file must describe the actual retained owner/fingerprints; any drift refuses reuse. This command exports the retained data, verifies it, and resets only the authorized assessment database before each configuration. It never alters other goal databases. Results and payloads are saved under the fresh run directory.

No new feature umbrella is required for this bounded slice: Episode production and optionality belong to #42, conformance to #39, and Spanner evidence to #41 under #34. Belief/Goal production, user attachment, enrichment ordering and public/concurrent tenant isolation remain outside this completion.


## Final independent verdict

Astra found **no remaining blocker for the scoped Memory Episode slice**. It independently checked 24 Episode appearances across the two final configurations, their exact source memberships and Summary edges, all nine source hashes, export digests/table-row hashes and both M04 cycle proofs. Final PDLC rows contain exactly five Episodes with member counts 1, 1, 2, 4 and 5. The Change API supplies source provenance; its Change-to-Event DERIVED_FROM relationship is independently checked in stored rows, not claimed as an edge returned by that API. No Episode-to-Change relationship exists. Final shutdown is clean.

This verdict does not establish live fault-injection coverage, public/concurrent tenant readiness, Belief/Goal producers or feature-umbrella closure. The retained database owner and all seven table fingerprints were independently reread after shutdown and match the saved retained record.


## Published issue reconciliation

Implementation and evidence commit: `acd2a46`, branch `feature/engram-memory-episodes`.

| Issue | Update | State |
|---|---|---|
| #34 | [Scoped Memory Episode progress and evidence](https://github.com/arunmenon/Engram/issues/34#issuecomment-6144942355) | OPEN |
| #39 | [Scoped Memory Episode progress and evidence](https://github.com/arunmenon/Engram/issues/39#issuecomment-6144943621) | OPEN |
| #41 | [Scoped Memory Episode progress and evidence](https://github.com/arunmenon/Engram/issues/41#issuecomment-6144944952) | OPEN |
| #42 | [Scoped Memory Episode progress and evidence](https://github.com/arunmenon/Engram/issues/42#issuecomment-6144940724) | OPEN |

No issue was closed on partial feature coverage. No new feature bucket was needed. The developer pilot and other assessment fixes have not started.


## Subsequent scope expansion

On 13 October the stakeholder explicitly required Belief and Goal producers in the overall Memory goal. Earlier exclusions in this document describe the completed Episode implementation scope, not the current overall goal. The [updated Memory goal](memory-episodes-goal.md) records required remaining journeys. Episode verification stays accepted; Memory pack completion and pilot readiness remain unclaimed.

## Belief/Goal continuation — verified bounded implementation

The Episode result above remains its own verified slice. The following work implements the stakeholder's expanded Memory scope. It does not change the earlier run's evidence or claim that the controlled pilot is ready.

The existing projection worker now consumes eight structured Memory event contracts. A stated Belief begins with one distinct supporting Event; an inferred producer proposal begins with zero. Confirmations require an exact revision. Correction preserves both Beliefs and creates SUPERSEDES, adding CONTRADICTS only when explicitly declared. A Goal begins active and requires an explicit event to become completed, abandoned or superseded. PDLC events do not automatically create or complete Goals. The existing consolidation worker continues producing Episodes.

State, source binding and evidence are committed together through the existing backend transaction. Public subgraph retrieval validates ownership, exact source receipts, counters and history before returning Memory context. Current recall omits superseded records; timeline recall preserves their declared history. Source assertions are not authenticated human judgments or guarantees of truth.

| Verification | Expected outcome |
|---|---|
| Memory disabled | Contract rejected before ledger write; stored Memory also excluded from composed reads |
| Stated and inferred Beliefs | Exact text/category/confidence, distinct origin, correct initial support and actual source provenance |
| Confirmation and retries | Only distinct applied support counts; duplicate creation does not reset current state |
| Competing revisions | One applied update, one explicit conflict; only winning evidence changes state |
| Correction | Exact predecessor/replacement, retained history, explicit contradiction only |
| Goal lifecycle | Active/completed/abandoned/superseded states and exact lifecycle source evidence |
| Ownership and scope | Default session scope; explicit agent scope crosses sessions; other owners positively retrievable under their own query and excluded from the first owner's Memory context |
| Missing parent | Pending worker retry converges after parent arrival; exhausted references dead-letter without partial state |
| Invalid body | 422 and no ledger write |
| PDLC composition | Existing Change remains retrievable; no invented Goal or implicit Memory lifecycle |
| Bounded retrieval | Explicit truncation, respected max_nodes, no dangling edges |
| Independent evidence audit | Exact API state/source/edge checks and separate final decoded Spanner-row audit; all groups settled and only expected conflict dead letters |

Astra's staging review identified and corrected two implementation defects before cloud acceptance: unauthorized history edges could be copied into answers, and Spanner node/edge budgets were checked separately instead of atomically. An additional source-validation gap was addressed by binding each accepted action's target and expected revision to its Event in the same transaction. Local negative probes reject fabricated history and substituted same-owner evidence. Combined-budget rejection schedules no mutations.

Cloud attempt `memory-actions-1013-01` remains failed: Core-only passed, and Memory API checks passed, but the final row audit compared codec-encoded confidence with a decoded float. The audit was corrected to decode actual stored properties; expected semantics were unchanged. Failed data and logs are retained. Attempt `memory-actions-1013-02` is the subsequent rerun; results must be read from its saved checks, not inferred from this narrative.

### Oracle corrections retained with the raw attempts

Attempt02 also remained failed at its DLQ audit: bound Spanner subscriptions deliberately reconstruct authoritative identity fields and do not preserve caller-added `memory_reason`. The corrected audit requires exactly the losing Event IDs, projection group and disposition epoch in ConsumerDeadLetters, plus `memory_status=conflict` AND `memory_reason=state_conflict` on each actual Event. Winner-only revision and evidence expectations were unchanged. Astra independently approved this field-location correction.

Attempt03 additionally uses a pinned batch-one configuration and two separately named projection consumers, each with independent stores in the same group. The original consumer is stopped and awaited before the two updates are admitted. Each new consumer reads a distinct accepted delivery; their handlers run concurrently. Only the winner may increment the revision and add support. Recorded start/end times establish handler overlap; there is no claim that a Spanner abort/retry was observed.

Raw attempt03 has legacy top-level summary fields `expected.belief_confirmations=2` and `expected.belief_revision=2`. Those describe the earlier single-consumer scenario and were not the acceptance oracle for the added parallel probe. Its independently reconstructed canonical `expected_state` and exact checks require **three supports, revision two after parallel confirmation, and revision three after correction**. Raw evidence is not rewritten. Astra confirmed this metadata mismatch is not a material blocker given the exact state and receipt audits.


### Final results and stakeholder walkthrough

All required types in this Memory slice now have production paths: Episodes through existing consolidation; Beliefs and Goals through eight structured contracts in existing graph projection. Independent Astra review accepted this bounded implementation with no remaining blocker. The controlled pilot and remaining assessment failures are separate work and have not started.

| Configuration | Selected live result | Evidence |
|---|---|---|
| Core only | 4/4 PASS; Memory input refused without writes | [attempt01 core](runs/memory-actions-1013-01/core.json) |
| Core+Memory | 65/65 PASS; exact state, evidence and parallel-consumer CAS | [attempt03 memory](runs/memory-actions-1013-03/memory.json) |
| Core+PDLC+Memory | 69/69 PASS; same Memory checks plus PDLC coexistence | [attempt03 composed](runs/memory-actions-1013-03/pdlc-memory.json) |

1. **Send the assertion.** Follow the `requests` entry for `memory-actions:stated`: authenticated POST `/v1/events` carries the common envelope and a `memory.belief.stated` payload with key `expiry`, text, category `world_model` and confidence 0.7. HTTP 201 means the ledger accepted it; the worker's persisted `memory_status=applied` establishes projection. A typed Belief has one support and the actual source Event.
2. **Confirm it and introduce a conflict.** Two distinct Events claim expected revision zero. Exactly one applies. Then two independent projection consumers handle distinct revision-one confirmations concurrently. Again, exactly one applies. The Belief has three supports and revision two; both losing Events are explicitly conflicted and dead-lettered. Inspect `parallel_handlers`, `dead_letters_inspected`, the API answer and `expected_edges`. A ledger acceptance is not silently treated as a successful state update.
3. **Correct it without erasing history.** An inferred replacement starts with zero confirmations. An explicit correction advances the old Belief to revision three, preserves its three supports and links replacement to predecessor via SUPERSEDES and explicitly declared CONTRADICTS. Current Belief recall omits the predecessor; `when` recall shows both with source evidence. No model-generated truth or invented confirmation is implied.
4. **Follow Goal lifecycle.** Creation yields active. Explicit commands produce completed, abandoned and superseded examples. The replacement Goal remains active. Each terminal Goal has exactly two source Events; the active replacement has one. A PDLC Change is still independently retrievable and neither creates nor completes a Goal implicitly.
5. **Check boundaries and recovery.** Session-scoped memories stay within the requested owner/session. Explicit agent scope is positively retrieved from another session. The other owner has its own positive read and is excluded from the first owner's Memory context. A confirmation delivered before its parent is held pending and then applied by worker retry. Invalid contracts produce 422 without ledger writes. Bounded answers report truncation without dangling edges.
6. **Inspect the independent final audit.** Canonical `expected_state` and `expected_edges` are derived from the submitted bodies and independently known winning revision outcomes. Both public owner-specific answers and final decoded Spanner rows match exactly. All five groups settle, pending deliveries are empty, expected conflict dispositions are exact, and shutdown is clean.

The final assessment dataset remains retained at epoch **18** in `engram-assess-1010a-pdlc`. A fresh owner/fingerprint reread matches [retained record](runs/memory-actions-1013-03/pdlc-memory-retained.json) and [retention recheck](runs/memory-actions-1013-03/retention-recheck.json). Prior datasets were exported and hash-verified before reset; no other database was reused or historical data migrated. [Source manifest](runs/memory-actions-1013-03/source-manifest.json) hashes all 210 runtime/script files, and Astra independently checked them and the export hashes.

Local verification: [181 targeted tests passed](runs/memory-actions-local/targeted-final.log), including 18 Memory action tests and 22 Episode tests; [Ruff](runs/memory-actions-local/ruff-final.log) and [mypy over 12 source files](runs/memory-actions-local/mypy-final.log) passed. The [earlier broad unit run](runs/memory-actions-local/full-unit-01.log) recorded 2,771 passes, 15 skips and two failures: an expected old eight-intent assertion was corrected and rechecked in the targeted suite; the existing PDLC evaluation-gate failure remains unrelated and open. Local injected SDK scheduling failure and combined-budget probes are supplemental tests, not live cloud fault injection.

Read [Astra's final independent review](runs/memory-actions-1013-03/astra-final-review.md) before treating this as acceptance. Limits: private bound tenant, sequential configuration reuse, explicit producer assertions, no autonomous natural-language Belief/Goal inference, no live Neo4j verification, no public/concurrent tenant isolation, no original 65-case Spanner baseline rerun. Cloud Monitoring still returns its existing permission error; telemetry export is not verified. The existing user-attachment and enrichment assessment findings remain.

Repeat with the saved runner and a NEW run ID, pointing `--previous-record` at the latest retained record. `--parallel-probe --configurations memory pdlc-memory` enables the reviewed batch-one/two-consumer check. The runner refuses evidence overwrite or owner/fingerprint mismatch. It exports and verifies the dataset before exact-key reset, so do not run it casually against data you intend to keep only in place.

### GitHub reconciliation and stop boundary

Implementation, reviewed verification and preserved attempts were pushed as `69e6b34` on `feature/engram-memory-episodes`.

| Issue | Update | Status after reread |
|---|---|---|
| #42 | Body now states current Memory producer completion; [comment](https://github.com/arunmenon/Engram/issues/42#issuecomment-6146405400) links exact scope and remaining user/composition work | OPEN |
| #34 | [Umbrella progress](https://github.com/arunmenon/Engram/issues/34#issuecomment-6146407944); this Memory slice does not close other buckets | OPEN |
| #39 | [Exact Memory conformance evidence](https://github.com/arunmenon/Engram/issues/39#issuecomment-6146408629); wider inventory remains | OPEN |
| #41 | [Real-Spanner extension evidence](https://github.com/arunmenon/Engram/issues/41#issuecomment-6146409319); original baseline/sign-off remain | OPEN |

No new feature bucket is needed for the implemented Memory work. Precommit implementation findings were resolved within #42; the two cloud failures were harness/audit mismatches, retained and independently dispositioned. No unrelated bug is marked fixed. The old broad autonomous goal remains paused. This continuation stops after the bounded Memory work; the developer pilot, user attachment/enrichment fixes and further goals require the agreed next-stage approval.
