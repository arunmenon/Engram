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
