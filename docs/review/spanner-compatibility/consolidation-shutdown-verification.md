# Consolidation shutdown — issue #60

Status: complete for the bounded shutdown slice, independently reviewed, published and reconciled in GitHub. Issue #60 is closed; larger feature/verification scopes remain open. This document provides the recorded stakeholder walkthrough; no live stakeholder attendance or sign-off is inferred.

## What this slice is for

When Engram says a worker has stopped, its database work must actually be finished. The previous consolidation supervisor cancelled the timer's await. A synchronous Spanner SDK thread could keep writing after the worker had joined. This slice makes shutdown wait for the whole admitted cycle and wakes a timer that is merely sleeping.

This uses existing workers, subscriptions, graph/event-log ports and Spanner transactions. No new service, queue, schema, dependency or historical migration. Source behavior changes only in ConsolidationConsumer. Restart uses a fresh instance.

## Frozen acceptance and public seams

Tests use the previously agreed authenticated HTTP input/read APIs, public worker run/stop, subscription and graph ports, and explicit external SDK/provider fault boundaries. Source events enter through Engram, never direct graph inserts. The live target is only projects/portiq-mvp/instances/engram-experiment/databases/engram-assess-1010a-pdlc. Retained epoch 36 enrichment data must be exported and verified before fenced reset; final data is retained.

One Core+PDLC+Memory configuration is sufficient for this bounded lifecycle proof: two observation.input events in one session, one owner, five real worker loops, deterministic optional summary-provider output, actual Spanner writes, and Engram timeline retrieval. The events do not exercise PDLC artifact producers or User capabilities. The test timer is pinned to 5 seconds and reflection threshold 5 before binding; local idle coverage also uses the normal six-hour interval.

| Case | What we do | Required observable result |
|---|---|---|
| SS01 | Hold a Summary mutation inside a real SDK transaction callback, then stop | Parent remains unfinished while held; release commits and drains all three Summary writes and Episode materialization before join |
| SS02 | Stop while the timer is sleeping | No cycle admitted; complete in under 3 seconds against the pinned 5-second timer; local six-hour timer stops in under 0.5 seconds |
| SS03 | Cancel the public run task three times during the held transaction | Each cancellation leaves it unfinished; release drains the entire cycle, then CancelledError propagates |
| SS04 | Raise a controlled storage exception after mutation scheduling, before SDK callback returns | Actual transaction rolls back; no cycle Summary commits; existing cycle-failed logging policy remains, no orphan work |
| SS05 | Raise a controlled RuntimeFencedError at that SDK boundary | Rollback; both loops join before the fatal fence escapes |
| SS06 | Fence the subscription while the timer transaction is held | Parent waits for the timer's complete admitted cycle, then propagates the subscription fence |
| SS07 | Start a fresh healthy worker after the interruptions/failures | This cycle itself commits all three expected summaries; exact identities/evidence are retained without duplicates |

Every successful admitted cycle must record committed SDK writes for its own episode, session and agent Summary identities; earlier artifacts cannot satisfy that oracle. The SDK gate records mutations only as committed after run_in_transaction returns successfully and discards aborted callback attempts when the SDK retries. Captured evidence is copied so later writes cannot mutate earlier observations. No strong database snapshot is requested while the test holds a read/write transaction; baseline snapshots precede the hold.

Expected final graph: exactly two Events, three Summaries, one complete Episode and the reserved matching OntologyState metadata node. Exactly twelve typed, directed edges: one FOLLOWS, six Summary→Event SUMMARIZES, four Episode→Event CONTAINS/DERIVED_FROM, and one episode-Summary→Episode SUMMARIZES. UUIDs, Summary identities, Episode membership hash, temporal bounds and edge keys are frozen in the manifest before ingestion. Sources retain the submitted owner/session/type/time/trace/tool; the Episode's ownership is evidenced by those source Events and its session, not an invented agent_id field.

After each consolidation join, ledger/graph fingerprints must remain unchanged while idle. After all five workers join, all seven application-table fingerprints must remain unchanged. SDK gates must report zero active calls. Fresh post-process owner/fingerprint and source-hash verification is required before acceptance.

## Error and guarantee boundaries

Ordinary cycle errors are currently logged and swallowed by _run_consolidation_cycle_guarded; this slice does not turn them into fatal worker exceptions or count their cycles as successful Summary production. Fencing and unexpected child failures escape after drain. Parent cancellation propagates after drain; a simultaneous fatal child error takes precedence and is logged. An active cycle has no fixed shutdown latency independent of its SDK/provider dependencies. A stuck call must leave shutdown unfinished, not falsely drained.

The guarantee covers cooperative stop and cancellation of the public run task while it owns its children. It does not retroactively recover already detached SDK work, direct cancellation of private children, SIGKILL or general cancellation of every worker. Controlled fencing exceptions test lifecycle behavior, not actual tenant revocation or concurrent tenancy. Uncertain shutdown prohibits reuse. The harness does not acquire the consolidation lock or cancel SDK awaits as a cleanup workaround.

## Local evidence and review

The first regression failed on the old implementation: run returned while the SDK-boundary thread was held. The new supervisor waits for that thread and the full cycle. [Red result](consolidation-shutdown-review/red-test.log).

Two older tests that mocked asyncio.sleep were replaced by public lifecycle/storage tests. The first broad unit run reached an older test that explicitly expected cancellation of an indefinitely blocked subscription loop; it was stopped and retained as unit-suite-01-interrupted.log, not counted as a pass. That test now supplies a controlled in-flight subscription read, verifies the supervisor waits, releases it, and checks the original fence escapes. No coverage was silently skipped to hide the changed contract.

Final targeted results: 73 passed, including ten lifecycle cases, three SDK-boundary harness checks, existing consolidation behavior and worker-fence regressions. Ruff and changed-source mypy pass. The broad unit rerun passed 2,831 with 13 skipped, excluding the previously documented tests/unit/test_pdlc_end_to_end.py evaluation-gate file. It predates one final test-only addition preserving ordinary-error timer continuation; that case passed in the final targeted run, and Astra accepted the coverage refresh. Runtime and cloud harness did not change. This is not a full baseline or live Neo4j claim.

[Astra preflight](consolidation-shutdown-review/astra-preflight.md) and [implementation/harness review](consolidation-shutdown-review/astra-implementation-review.md) support the bounded live run. [Astra final completeness review](consolidation-shutdown-review/astra-final-review.md) clears bounded #60 closure after reviewing actual SDK/cancellation/fencing, public responses, source hashes, export and retention evidence.

## Stakeholder walkthrough plan

1. Show the two accepted source payloads and their HTTP responses, ledger records and projected Events.
2. Show the gate entered inside the SDK callback after a Summary mutation was scheduled. While held, the worker must remain unfinished after stop or repeated cancellation.
3. Release the gate. Show committed SDK writes for this cycle's episode, session and agent summaries, complete Episode evidence, and the final join/error outcome.
4. Show controlled storage/fencing failures as rollbacks, not successful production. Show fresh-worker recovery with the same exact identities and source memberships.
5. Ask Engram for the session timeline. Check both source Events, the complete Episode and its Summary with exact evidence links and no unrelated artifacts.
6. Show all workers joined, zero active tracked SDK calls, unchanged post-join fingerprints, verified prior export and retained final ownership. Review GitHub issue updates and the remaining pilot prerequisites.

No next slice or pilot starts automatically. #60 belongs to #34, with #39/#41 receiving bounded proof. #18 cached replay and #61 UUID subgraph access remain separate. No new feature umbrella is needed.

## Accepted live results — consolidation-shutdown-1014-01

[Full run record](runs/consolidation-shutdown-1014-01/verification.json), [frozen inputs/expected graph](runs/consolidation-shutdown-1014-01/manifest.json), and [runner log](runs/consolidation-shutdown-1014-01/runner.log). All seven cases passed, 109 assertions total. These are lifecycle scenarios, not 109 separate business journeys. The first live attempt passed without manual repair.

| Case | Actual SDK work | Outcome |
|---|---|---|
| SS01 stop during write | 10 tracked calls returned; this cycle committed all 3 Summaries | PASS: parent stayed unfinished while held, then full cycle drained |
| SS02 idle timer | No Summary SDK call; stop took 0.201 seconds | PASS: no cycle admitted, well below the pinned 5-second interval |
| SS03 repeated cancellation | 10 calls returned; all 3 Summaries committed | PASS: three cancellations waited, then CancelledError propagated |
| SS04 ordinary storage failure | One call returned with UnavailableError; one scheduled Summary rolled back, zero committed | PASS: existing logged-cycle policy, no detached write or false production claim |
| SS05 timer fencing | One call returned with RuntimeFencedError; one rollback, zero Summary commits | PASS: fatal error escaped after drain |
| SS06 subscription fencing | 10 calls returned; all 3 Summaries committed | PASS: timer finished its admitted cycle before the fence escaped |
| SS07 fresh restart | 10 calls returned; all 3 Summaries committed again under the same stable identities | PASS: no duplicated nodes or memberships |

Every post-join business fingerprint stayed stable. After all five workers joined, all seven application tables stayed stable. The final graph contains exactly two source Events, three Summaries, one complete Episode and one matching ontology metadata node; exactly twelve typed, directed edges preserve the planned memberships. Summary scope IDs, time ranges, episode/session scripted text, Episode completion/bounds, Event owner/session/type/time/trace/tool/keywords and selected schema metadata match the frozen inputs.

Engram's authenticated timeline read returned the two source Events, complete Episode and its Summary. The independent audit also checked actual public provenance and the exact seven Episode/episode-Summary evidence links, not just node presence. No foreign artifacts or response truncation were accepted.

[Fresh post-process audit](runs/consolidation-shutdown-1014-01/post-process-recheck.json) matched epoch 37 ownership and every table fingerprint after process exit; all 216 runtime/YAML/script hashes matched; final/retained snapshots matched; the prior epoch 36 export digest verified. [Audit code](consolidation-shutdown-review/post-process-audit.py) is retained for inspection. Data remains in the assessment database. Cloud Monitoring export still reports 403; telemetry readiness is not implied.

Runtime/harness commit: `9e3ff0a`. Production change is local to worker/consolidation.py; the larger commit consists of the dedicated proof runner and tests. A final test-only addition preserves the old ordinary-failure continuation behavior using the public lifecycle seam. No runtime change followed the accepted cloud run.

## Repeat safely

With the current verified owner and existing experiment credentials, use a new run ID:

```sh
PYTHONPATH=src:scripts /Users/arunmenon/projects/Engram-foundation-gate/.venv/bin/python \
  scripts/engram_consolidation_shutdown_demo.py \
  --run-id consolidation-shutdown-repeat-UNIQUE \
  --previous-record docs/review/spanner-compatibility/runs/consolidation-shutdown-1014-01/retained.json
```

The runner refuses existing evidence paths, verifies prior ownership/fingerprints, exports and reads back the previous dataset before exact-key reset, and retains the final data. Do not rerun automatically after another slice changes ownership. No further cloud run is needed for the results above.

## Stakeholder demonstration outcome

Follow the six walkthrough steps above using the saved requests, SDK-held/returned observations and public timeline answer. The main lesson is visible at SS01/SS03: **an unfinished SDK operation keeps shutdown unfinished**. Completion occurs only after the episode, session and agent summaries, Episode evidence, maintenance and both child loops have finished. SS04/SS05 show expected failures honestly as rollbacks. SS07 shows fresh-worker recovery rather than an invented clean slate.

The three summaries are existing behavior: episode summarizes the temporal group, session covers the session, and agent covers this owner's activity. Memory's Episode records exact membership and links to the episode Summary. This slice changes when shutdown may report completion, not what those projections mean.

The initial local fixture counted only episode and agent summaries; inspection confirmed the existing session summary and corrected the local expected count to three before the cloud manifest was frozen. The cloud oracle did not change during execution.

No new feature bucket is warranted. #60 fits #34 worker reliability; #39/#41 receive bounded evidence. #18 cached predecessor/replay and #61 UUID subgraph access remain separate, as do broader pack-composition and tenant-isolation proofs. The controlled pilot and next slice are not started.

## Published GitHub reconciliation

Runtime/harness: `9e3ff0a`. Reviewed verification, raw evidence and final test-only coverage: `cf8bec8`. Pushed on `feature/engram-memory-episodes`.

| Issue | Before → after | What changed | GitHub update |
|---|---|---|---|
| [#60](https://github.com/arunmenon/Engram/issues/60) | OPEN → CLOSED | Bounded acceptance complete; resolved body and closure published | [Comment](https://github.com/arunmenon/Engram/issues/60#issuecomment-6159328178) |
| [#34](https://github.com/arunmenon/Engram/issues/34) | OPEN → OPEN | Bounded evidence/progress recorded; broader scope remains | [Comment](https://github.com/arunmenon/Engram/issues/34#issuecomment-6159329556) |
| [#39](https://github.com/arunmenon/Engram/issues/39) | OPEN → OPEN | Bounded evidence/progress recorded; broader scope remains | [Comment](https://github.com/arunmenon/Engram/issues/39#issuecomment-6159330193) |
| [#41](https://github.com/arunmenon/Engram/issues/41) | OPEN → OPEN | Bounded evidence/progress recorded; broader scope remains | [Comment](https://github.com/arunmenon/Engram/issues/41#issuecomment-6159330736) |
| [#42](https://github.com/arunmenon/Engram/issues/42) | OPEN → OPEN | Bounded evidence/progress recorded; broader scope remains | [Comment](https://github.com/arunmenon/Engram/issues/42#issuecomment-6159331400) |
| [#18](https://github.com/arunmenon/Engram/issues/18) | OPEN → OPEN | Unchanged; outside this slice | No new closure/update claimed |
| [#61](https://github.com/arunmenon/Engram/issues/61) | OPEN → OPEN | Unchanged; outside this slice | No new closure/update claimed |

The native #34→#60 sub-issue link and final states were re-read after mutation. Full recorded actions are in [GitHub reconciliation](consolidation-shutdown-review/github-reconciliation.json). No new umbrella is needed. The next slice and controlled pilot remain unstarted.
