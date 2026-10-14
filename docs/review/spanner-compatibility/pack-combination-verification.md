# Pack-combination verification after remediation

This is the assessment checkpoint before two-tenant isolation and the controlled developer pilot. It is not the pilot. The stakeholder selected this slice after #61 and required the same frozen expectations, real path, retained failures, independent review, walkthrough and issue reconciliation.

## What we are proving

Core is mandatory. User, Memory and PDLC are independently selected through the existing pack resolver and shared workers. The following configurations must deliver their selected behavior together, without introducing per-combination worker implementations:

| Configuration | Expected useful outputs beyond core Event/Entity/Summary |
|---|---|
| Core | No optional-pack artifacts |
| Core+User | Canonical profile; preference with distinct support; explicit correction history |
| Core+User+Memory | Same User outputs; Belief, Goal and Episode with exact source evidence |
| Core+PDLC | Created then merged Change; extracted Decision with source evidence |
| Core+PDLC+Memory | Same PDLC outputs; explicit Belief/Goal; Episodes over user-like and domain activity |

## Concrete journeys and pass/fail checks

1. Alice says she uses ResetToken and prefers short answers. Session end triggers entity extraction everywhere and User outputs only where selected. A second session-end trigger overlaps the same source: it must not count the preference twice.
2. Alice explicitly says she no longer prefers short answers, naming the previous preference and context. User-selected configurations must preserve the old preference, create one successor with the correction source, and retrieve only the active successor through normal preference/personalization reads.
3. With Memory selected, structured events state and confirm a fifteen-minute expiry Belief, then create and complete an implementation Goal. Counts/revisions and exact evidence must match the declared events. These are producer assertions, not automatic LLM inference from prose or conversion of PDLC artifacts.
4. With PDLC selected, create and merge PR7 in packmatrix/main. PR7 in packmatrix/unrelated remains a separate open Change. Artifact retrieval of the main Change must exclude the unrelated Change and retain evidence.
5. The shared pack-extraction worker receives prose declaring the expiry Decision. Only PDLC configurations may produce that Decision. An external provider supplies a frozen valid proposal; the real profile validator/planner/writer must materialize it with the source Event. No automatic Belief/Goal is expected from that Decision.
6. With Memory selected, consolidation must materialize retrievable complete Episodes and stored Summaries over the five-event Alice session, and also the two-event PR session when PDLC is selected. Membership and typed CONTAINS/DERIVED_FROM evidence must match the declared source sets.
7. Resending accepted HTTP triggers/updates must leave every application-table fingerprint unchanged. A fresh real User extraction worker also replays the applied correction receipt: it must not call the provider or change User outputs.
8. Disabled Memory/PDLC events and malformed enabled contracts must return422 and change no application table. User-off ordinary reads return404. Disabled types and User receipts must be absent from the graph.
9. Reads use the Event subgraph, User and artifact APIs. Expected identities, state, support and source evidence must return; receipts stay private. Non-access Event properties and all non-Event properties must survive reads unchanged. All five real loops must settle and join normally, with no pending work or dead letters, before final retention.

All accepted Events must retain the exact deterministic enrichment keywords. Importance starts from hint7 but consolidation intentionally recomputes it from graph centrality; the allowed final buckets are6,7,8,10. This slice records those values and does not claim smart scoring or exact centrality quality. Prior #29 evidence supplies the focused enrichment-ordering proof.

## How the run works

Authenticated HTTP ingestion → real Spanner ledger → five production worker loops → real Spanner graph → authenticated Engram read APIs. Only external extraction and summary providers are frozen fixture outputs; workers, admission, projection, receipts, graph storage and retrieval stay real. This proves composition, not model quality. Embedding services use the existing runtime; no ANN benchmark is implied.

Before the first reset, the runner saves all payloads, independent identities, selected packs and expected/forbidden outcomes plus source hashes. For each sequential configuration it requires the current owner/fingerprints, freezes ownership, exports/readback-verifies/digest-checks all registered rows, then resets exact keys and advances the epoch. Only the existing assessment database may be reused. No direct acceptance inserts or repairs. Failed attempts remain saved; final data remains retained.

This is not a claim of public/concurrent tenant isolation, concurrent access-counter atomicity, all possible pack combinations, general interruption recovery, historical migration, full PDLC catalog reevaluation or pilot readiness. Original G8–G11 and the feature umbrellas cannot all be closed from this bounded slice.

## Verification and stakeholder demo

Each configuration gets inputs, API responses, worker/provider observations, graph baseline, exact assertions, read responses and final retained state. The walkthrough will show the same source journeys across configurations, the resulting graph differences, exact retrieved evidence, failures and dispositions, Astra's final verdict, and actual GitHub states. Relevant #34/#39/#41/#42 records must be reconciled; any newly discovered blocker gets its own issue under the appropriate umbrella. No new bucket without a concrete need.

Results: first attempt retained with a real Entity evidence blocker and an artifact API oracle correction. The reviewed all-five rerun passed and Astra accepted the bounded checkpoint. Stop after this slice; the next stage needs stakeholder approval.

### Preflight record

Local checks validated every fixture envelope, accepted/rejected event contract, structured Memory action, both User-provider schemas and the actual PDLC extraction proposal under all five resolved bundles. Current versions: Core1.1.0, User1.2.0, Memory1.2.0 and PDLC5.0.0. Relevant regressions:159 passed. These are local prerequisites, not Spanner acceptance.

The first local invocation had a missing helper argument and the first test command named a nonexistent test file. Both logs remain retained; corrected commands passed. Astra caught the api-only assessment principal, inclusion-only evidence assertions, agent-summary content and legacy Memory-off episode-summary identities. All were corrected before cloud reset; production authorization, worker behavior and expected user outcomes were unchanged. [Preflight review](pack-combination-review/astra-preflight.md).

### Walkthrough at completion

| What you will inspect | What it answers |
|---|---|
| Frozen manifest and exact pack versions | What was selected, sent and expected before the run? |
| Admission responses and accepted ledger IDs | Did every accepted/rejected input use Engram's real write path? |
| Exact typed artifacts and evidence | What did each real worker create, and which input supports it? |
| User correction and Memory lifecycle results | Did state evolve without duplicate support or invented conversions? |
| Episode/Summary snapshot audit | Are membership, time bounds and stored summaries valid, including intermediate history? |
| User/subgraph/artifact API responses | Can a caller retrieve the intended state and source evidence? |
| Whole-table duplicate/rejection checks, joins and retained readback | Were forbidden writes absent and did work actually finish? |
| Astra verdict and GitHub reconciliation | What was accepted, what remains open and which stage needs approval next? |

### First live attempt — additional Entity blocker (#62)

Independent inspection of the first attempt's Core/User baselines found that repeated session extraction resolved `ResetToken` to a normalized name and reconstructed `entity:resettoken`, while the original stored key is `entity:ResetToken`. Later REFERENCES were missing. The original Entity-presence assertion did not catch this; the run is not accepted as a clean matrix pass even if its original assertions say passed.

[Issue #62](https://github.com/arunmenon/Engram/issues/62), a native child of #34, records the live failure and bounded fix. [Astra's grounded follow-up](pack-combination-review/astra-entity-followup.md) confirms that exact/fuzzy/semantic results should carry the stored Entity ID already supplied by existing ports. A public-worker regression failed for repeated mixed-case and alias matches with User on/off; additional resolver-ID checks also failed. The corrected matrix must require the exact session REFERENCES set, retain this deficient attempt, and rerun all five configurations after the reviewed correction. No casing change to fixture payloads, graph repair, migration or resolver redesign is authorized by this finding.


### Bounded correction and rerun

#62 changes two existing source files: resolution results carry the authoritative matched Entity ID, and the existing extraction worker validates and uses that ID for REFERENCES and resolution-edge targets. Missing, empty or non-string matched IDs fail visibly before related writes. Names, matching policy, storage ports and tables remain unchanged. Mixed-case/alias worker regressions, exact/fuzzy/semantic identity checks and invalid-storage-result checks reproduce the problem and verify its correction. Final targeted identity suite:14 passed; affected suite:117 passed. Ruff and mypy pass after a type-narrowing correction; the earlier typing failure is retained.

The first attempt stopped in Core+PDLC when a new public-evidence check demanded DERIVED_FROM edges from `/v1/query/artifacts`. That endpoint intentionally traverses artifact edges and returns the newest source as provenance. The corrected oracle requires the exact newest source UUID, owner, session, time, trace and ledger position in its response, alongside the full exact stored source-edge set. Event subgraph Memory checks still require their public evidence edges. This is an oracle correction to the existing endpoint contract, not a changed question or weakened stored-evidence expectation. PM was not run in that attempt. [Initial attempt disposition](runs/pack-combination-1014-01/assessment-disposition.json).

The Entity check now requires all five accepted Alice-session REFERENCES after repeated extraction; it does not merely require the Entity to exist. These are the existing coarse session extraction links, not a claim that every session-end payload mentions the Entity. No fixture casing changed. The original matrix harness and all218 frozen source hashes were verified and saved before applying the fix. [Implementation review](pack-combination-review/astra-implementation-review.md).


## Accepted rerun results

Run: [pack-combination-1014-02](runs/pack-combination-1014-02/manifest.json). Every configuration used the corrected source and strengthened Entity evidence oracle.

| Configuration | Live assertions | Accepted Events | Retained epoch at stage end |
|---|---:|---:|---:|
| [core](runs/pack-combination-1014-02/core.json) | 85 | 5 | 44 |
| [user](runs/pack-combination-1014-02/user.json) | 113 | 5 | 45 |
| [user-memory](runs/pack-combination-1014-02/user-memory.json) | 216 | 9 | 46 |
| [pdlc](runs/pack-combination-1014-02/pdlc.json) | 133 | 8 | 47 |
| [pdlc-memory](runs/pack-combination-1014-02/pdlc-memory.json) | 246 | 12 | 48 |

**793 live assertions passed**, across 39 accepted Events, 19 rejected attempts with no writes, and 9 exact HTTP duplicates with no writes. Fresh User receipt replay ran in both User configurations; it made no provider call and left every application table unchanged. Final composed data remains retained at epoch48; each prior dataset was exported/readback/digest verified before exact-key reset.

All five actual worker loops joined without the old external lock workaround, with no pending deliveries or dead letters. Every accepted Event retained its source identity and expected keywords. Optional artifacts were absent when disabled; enabled artifact identity sets, Memory receipts, lifecycle/source support, all Summary/Episode memberships and public retrieval evidence passed the declared checks. Entity REFERENCES now include all five accepted Alice-session Events under every configuration.

Local results:159 relevant regressions before the correction;117 affected tests after it;14 final identity/invalid-ID regressions after the type-narrowing correction. Broad suite:2848 passed,13 skipped, excluding the previously documented PDLC evaluation-gate test file. The broad run began before the final typing-only local-variable initialization; behavior did not change and the final14 tests ran afterward. Ruff/mypy passed. First red tests, missing-ID red tests, type-analysis failure, initial deficient cloud evidence and dispositions are retained in the review/run folders.

The test principal explicitly has api+admin roles for the established User endpoints. Models supplying session extraction, pack proposals and summary text are frozen external providers; the real validation, receipts, workers, writes and reads are exercised. This is not an LLM-quality evaluation. The development unevaluated-bundle gate stays enabled, the original65-scenario Spanner baseline was not rerun, and Cloud Monitoring export still reports403. None is presented as pilot/monitoring readiness.

To repeat, use `scripts/engram_pack_combination_demo.py --run-id <new-unique-id> --previous-record docs/review/spanner-compatibility/runs/pack-combination-1014-02/pdlc-memory-retained.json`. Only do so within an authorized rerun: it exports and replaces the current retained assessment dataset. Never use an obsolete owner record or a protected production/goal database.


## Independent final verdict and retained proof

[Astra accepted the bounded checkpoint and #62 closure](pack-combination-review/astra-final-review.md). The reviewer independently checked the exact Entity REFERENCES, User correction/replay behavior, structured Memory evidence and historical Episode/Summary snapshots, PDLC source provenance, all218 frozen runtime/YAML/script hashes and export digests. Fresh-process readback matched the final owner at epoch48, all seven application-table fingerprints and the full retained snapshot: [post-process audit](runs/pack-combination-1014-02/post-process-recheck.json).

This closes the newly discovered #62 defect only. The composition checkpoint provides the declared nine journeys across five configurations; it does not close the full G8–G11 or #34/#39/#41/#42 scopes. Two-tenant isolation, the public dispatcher, interruption/retention cases, evaluation, ANN benchmarking and the controlled developer pilot remain separate work. No next slice started. GitHub reconciliation is recorded below after the actual mutations are confirmed.
