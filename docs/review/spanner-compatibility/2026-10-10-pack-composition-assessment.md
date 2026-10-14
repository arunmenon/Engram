# Pack-composition assessment: current behavior and pilot blockers

Status: all five configurations have now been attempted on real Spanner. The bounded core/PDLC paths work, but enrichment persistence failed; both user-enabled configurations failed during extraction; useful Memory production remains blocked. This is an assessment with findings, not pilot readiness or completion of G08–G13.

G7 is treated as complete per the stakeholder checkpoint. It was not rerun or modified here. Runtime source is the assessment baseline `9abe3c3`; this work changes only assessment scripts, tests and records. Source hashes distinguish the initial harness from its bounded-wait correction.

## Live assessment results

Application records entered through the authenticated private Engram HTTP API. All five real worker loops and actual model providers ran against Spanner. Subgraph and artifact acceptance used Engram HTTP endpoints; direct stored-row inspection supplied independent write-side evidence. Tenant-control bootstrap/reset changed control metadata only. No direct artifact insertion, scripted model, runtime fix or historical migration was used.

| Configuration | Actual result | Remaining limitation |
|---|---|---|
| Core | 11 checks passed; 1 failed | Final Event keywords missing |
| Core + user | Run failed after 6 passing preliminary checks | Entity-interest provenance rejected `entity_id`; one extraction delivery pending; later checks not run |
| Core + user + memory | Run failed after 6 passing preliminary checks | Same worker error and pending delivery; bounded wait expired; later checks not run |
| Core + PDLC | Original run: 12 basic checks passed; additional final enrichment audit failed | No new rerun was substituted for this retained original evidence |
| Core + PDLC + memory | 12 checks passed; 1 failed; 1 blocked | Enrichment missing; useful Memory production blocked by absent registered producer |

Passing preliminary checks do not make a failed run successful. Checks after the user extraction failures, including specialized/composed user reads and preference behavior, remain **NOT RUN** in these live attempts.

### How the assessment database was reused

The free instance had reached five databases. Initial creation failures and naming mistakes remain in the original evidence. The stakeholder then authorized reuse of **only `engram-assess-1010a-pdlc`**. No paid instance or additional database was created. The four earlier databases were not modified.

For each of the four remaining configurations, the runner verified the exact target and previous owner, froze the ownership epoch, exported all application-table rows and tenant control, read the export back, verified file and table hashes, and then transactionally cleared only exported keys. The transaction rechecked ownership and dataset hashes before activating the next tenant/bundle at a new epoch. Every configuration began with empty application tables. Workers were stopped and snapshots saved before the next reset.

The four full exports preserve, in order, the original PDLC dataset, core dataset, failed user dataset and failed user-plus-memory dataset. The final **core + PDLC + memory dataset remains live at epoch 5**, with 3 events, 13 nodes, 16 edges, zero pending deliveries and zero dead letters. All four runs report clean worker shutdown. Failed user datasets retain their pending delivery in the exports; clearing it for the next experiment is not a processing fix.

This is **sequential composition testing on one reused database**. It does not prove concurrent tenant isolation, cross-database routing or the public multi-tenant dispatcher.

### What worked

Core alone admitted and retrieved an Event, rejected invalid input without writes, treated an exact retry as a duplicate, produced Entity nodes through actual session extraction, rejected an unloaded PDLC event, and produced no disabled user or PDLC outputs.

Core + PDLC + memory also admitted the selected Change event, projected the exact Change, and retrieved its expected title, type and originating-event evidence through the artifact API. User outputs stayed absent. Adding Memory did not prevent this bounded PDLC path; it did not demonstrate useful Memory production.

### What failed

**Enrichment persistence — #29.** Core alone and core + PDLC + memory ended with empty Event keywords despite logged enrichment. This matches the additional audit of the original core + PDLC run. The live evidence establishes persistence loss across these configurations, but does not distinguish missing-target timing from later overwrite. No fix was applied.

**User extraction — #20.** Actual model extraction returned interests. The worker wrote a profile and other partial results, then failed when attaching interest provenance: `Unknown source_id_field: 'entity_id'`. Both user-enabled runs retained one pending extraction delivery. This matches existing issue #20; no duplicate issue is needed. Partial profile writes are not proof of successful profile retrieval or retry safety.

**Useful Memory behavior — #42.** Memory declares Belief/Goal/Episode types but has no registered producer. The final combination records this as BLOCKED; the failed user-plus-memory run never reached that check. No new conversion semantics were invented.

**Harness correction, with failure preserved.** The first user run waited beyond the intended limit because the harness counted 300 polling cycles rather than elapsed time. It was stopped gracefully, its pending delivery and partial writes were saved, and its run was recorded as failed. Remaining configurations used a monotonic 60-second deadline checked between completed SDK calls. This does not cancel in-flight SDK work. The user-plus-memory run then failed on that bounded wait. Resume accepts only the recorded prefix with clean shutdown, a retained snapshot and matching owner/fingerprints.

Pack extraction produced Constraint/Decision artifacts from the prose inputs in the PDLC-enabled runs. These are observed model outputs with source evidence, not predeclared semantic acceptance cases. They do not count as Memory results. Public dispatch, concurrent isolation, preference retries/corrections, recovery and consolidation lifecycle coverage remain unverified by these bounded probes. The development unevaluated-bundle gate remains enabled. Cloud Monitoring export reported permission denial; monitoring readiness is not established.

### Evidence and repeatability

- [Sequential run summary](runs/composition-1010r/summary.json), [full results](runs/composition-1010r/results.json), [original expectations and target](runs/composition-1010r/manifest.json), and [raw runtime log](runs/composition-1010r/runtime.log).
- Per-configuration inputs, HTTP responses, checks and snapshots: [core](runs/composition-1010r/core-observations.json), [user](runs/composition-1010r/user-observations.json), [user + memory](runs/composition-1010r/user-memory-observations.json), [PDLC + memory](runs/composition-1010r/pdlc-memory-observations.json).
- Full exports before each reset: [original PDLC](runs/composition-1010r/before-core-export.json), [core](runs/composition-1010r/before-user-export.json), [failed user](runs/composition-1010r/before-user-memory-export.json), [failed user + memory](runs/composition-1010r/before-pdlc-memory-export.json). Corresponding `.verified.json` and `.reset.json` receipts are alongside them.
- [Final retained owner and fingerprints](runs/composition-1010r/pdlc-memory-retained.json).
- [Runner interruption and correction](runs/composition-1010r/runner-interruption.json), with [initial source hashes](runs/composition-1010r/source-sha256.json) and [resumed source hashes](runs/composition-1010r/source-sha256-v2.json).
- Original PDLC [HTTP and stored-data results](runs/composition-1010a/pdlc-observations.json), [failed additional audit](runs/composition-1010a/post-run-audit.json), and [preparation failures](runs/composition-1010a/manifest.json) remain unchanged.
- Assessment scripts: `scripts/engram_composition_assessment.py` and `scripts/engram_composition_reuse.py`. Thirteen targeted harness/safety tests passed after the correction; [test log](runs/composition-1010r/harness-tests-v2.log). Lint passed. No new independent Astra sign-off is claimed.

The reuse runner deliberately refuses a fresh invocation over existing evidence. Its `--resume` option continues only a safely recorded prefix; it is not a command to rerun or erase the completed assessment. A repeat experiment needs a separately named evidence run and the same export/owner checks. The final dataset is retained, not automatically cleaned.

## Memory historical RCA

The stakeholder requested a check for a lost producer during refactoring. The [completed RCA](2026-10-10-memory-producer-rca.md) found schema/helpers but no direct producer calls across 45 available refs/checkpoints, and no worker/API history showing such a producer removed. Original episodic behavior wrote Summary nodes and remains in the source; 74 local consolidation/composition tests passed. This supports an inherited typed-producer gap, not a demonstrated removal. It does not certify all historical Memory behavior or add cloud acceptance.

## What was assessed

Can the five selected combinations resolve into explicit worker/read configurations? What useful behavior exists, and what must be fixed or specified before the two-tenant developer pilot?

The initial local phase reused the approved [Astra grounding](2026-10-08-astra-pilot-composition-assessment.md) and [pilot brief](2026-10-08-controlled-pilot-discovery-brief.md), then executed configuration probes, shared-writer diagnostics and selected existing regression tests. That phase used no cloud database or retained goal data. The subsequent live phase is recorded above. No runtime implementation changed.

## Actual configurations

All five selections resolved. Exact manifests, types, relationships, intents, handlers, profiles and bundle identities are in [resolved-bundles.json](runs/20261010-pack-composition-assessment-local/resolved-bundles.json).

| Selection | Actual pack versions | User extraction | PDLC rules / profiles | Useful Memory producer |
|---|---|---|---|---|
| Core | core 1.1.0 | Off | None | None |
| Core + user | core 1.1.0, user 1.1.0 | On | None | None |
| Core + user + memory | core 1.1.0, user 1.1.0, memory 1.0.0 | On | None | None |
| Core + PDLC | core 1.1.0, pdlc 5.0.0 | Off | 28 deterministic rules, one extraction profile | None |
| Core + PDLC + memory | core 1.1.0, pdlc 5.0.0, memory 1.0.0 | Off | Same 28 rules and profile | None |

Adding Memory changes the vocabulary and bundle identity, but the registered handler lists remain identical in both matched comparisons. This observes configuration behavior; it does not prove useful Memory knowledge was produced.

## Configuration × worker behavior

| Worker | Core | Core + user | Core + user + memory | Core + PDLC | Core + PDLC + memory |
|---|---|---|---|---|---|
| Graph projection | Core Event/activity | Same core | Same core | Core plus matching PDLC rules | Same as core+PDLC |
| Session extraction | Core entities | Entities + gated user results | Same implemented outputs as core+user | Core entities; user writes off | Same as core+PDLC |
| Enrichment | Event annotations; optional embedding | Same shared role | Same shared role | Same role on admitted domain activity | Same shared role |
| Consolidation | Eligible core Summary and maintenance | Same shared role | Summary, not Memory Episode | Same shared role | No Memory Episode producer |
| Pack extraction | No PDLC profile | No PDLC profile | No PDLC profile | Matching prose → allowed proposals | Same profile as core+PDLC |

These are code-grounded applicability statements, not five successful end-to-end runs. Each input still needs admission and the relevant trigger/profile. Selection configures existing machinery; deployment starts workers. Session/pack extraction need model providers; enrichment embeddings are optional; consolidation has optional model summaries and deterministic paths. Graph projection is deterministic.

## Local diagnostic findings

[Full results](runs/20261010-pack-composition-assessment-local/shared-logic-probes.json).

These diagnostics call real shared GraphOperations methods over an isolated MemoryGraphStore. Direct writer calls intentionally isolate logic. They are NOT HTTP-to-Spanner, full-worker or pilot acceptance and must never be counted as such.

| Diagnostic | Actual observation | Assessment |
|---|---|---|
| Profile write and reads | Raw profile exists; specialized user reader returns it; composed reader filters it out. The registry expects user_id, while the node identity is profile:<user_id>. | Local profile identity disagreement reproduced. |
| Identical preference writes without ID | Two calls create two Preference nodes. | Missing stable result identity is unsafe if an extraction is replayed. |
| Identical preference writes with fixed ID | The observation count increments to 2. | Stable ID alone does not make the writer idempotent. |
| Enrichment before Event creation | The later-created Event lacks the earlier requested keyword. | Shared writer loses the annotation in this order. |
| Public tenant factory invocation | Raises TenantServiceNotReadyError before opening stores. | Fail-closed behavior confirmed locally; public shared service is unavailable. |

The preference probe does not establish full consumer retry/correction behavior. The enrichment probe does not establish live Spanner scheduling or recovery. Those require separately frozen full-path probes.

## What reads can actually use

- **Event/context retrieval:** activity graph, text and Entity-vector channels. It is not universal traversal of every user, Memory or domain type. Personalization depends on consistent user identity and applicable capabilities.
- **Artifact retrieval:** domain keys/text/traversal and evidence; no vector seed channel. Core/user/memory are not its generic domain-artifact seed packs.
- **User endpoints:** a third relevant read surface. A profile appearing here does not prove composed personalization can find it; the local mismatch demonstrates why both must be checked.
- **Memory:** no automatic Belief/Goal/Episode producer or Memory-to-PDLC join is registered. Selecting vocabulary is not useful-memory acceptance.
- **Tenant isolation:** private bound runtimes pin database/bundle/ownership. Local contract tests do not prove concurrent isolation on real separate databases. The public dispatcher remains disabled.

## Keep / fix / block decisions

| Decision | Smallest bounded next work | Existing ownership |
|---|---|---|
| Keep shared workers and explicit capability selection | Preserve mandatory core and supported generic rules/profiles; no worker forks per pack pair. | #35 / #42 |
| Fix profile identity boundary | Choose one canonical new-data identity; check writer, user API, composed reads and personalization together. | #42 / #39 |
| Fix or explicitly restrict preference retry behavior | Specify stable extraction-result identity/receipt and observation semantics, then verify write-before-ACK and correction scenarios. | #42 / #37 / #39 |
| Fix missing-target enrichment convergence | Defer/retry or prove a convergent update path; verify enrichment-first order with actual workers. | Existing ordering/retry scopes #29 / #14; reconcile detailed acceptance |
| Block useful Memory claims | Choose the minimum intended Memory behavior before implementing a producer. Do not invent ticket→Goal or Summary→Episode conversion. | #35 / #42 |
| Block public shared pilot claims | Specify supported dispatch/bootstrap and worker lifecycle; keep fail-closed behavior until verified. | #43 |

At the initial local checkpoint, reads confirmed #35, #39, #42 and #43 remained open, and no issue was modified. After the partial live run, progress evidence was posted to [#29](https://github.com/arunmenon/Engram/issues/29#issuecomment-6092787059) and [#34](https://github.com/arunmenon/Engram/issues/34#issuecomment-6092788351). No issue was closed. No new feature bucket is needed for the observed enrichment failure; larger Memory semantics require their own explicit specification.

After sequential reuse completed, follow-up evidence was posted to [#20](https://github.com/arunmenon/Engram/issues/20#issuecomment-6098465417), [#29](https://github.com/arunmenon/Engram/issues/29#issuecomment-6098465705), [#42](https://github.com/arunmenon/Engram/issues/42#issuecomment-6098466227), [#34](https://github.com/arunmenon/Engram/issues/34#issuecomment-6098466549), [#41](https://github.com/arunmenon/Engram/issues/41#issuecomment-6098466850). These issues remain open; no new issue or feature bucket was created. [Reconciliation receipt](runs/composition-1010r/issue-reconciliation.json).

## Verification and next checkpoint

**132 selected local regression tests passed.** [Exact command and result](runs/20261010-pack-composition-assessment-local/test-receipt.json). They cover composition, composed reads, extraction gating, tenant binding/dispatch and extraction behavior, using mocks/reference storage where applicable. They do not certify the public service, live LLMs or Spanner combinations.

The next checkpoint is to review these live findings and approve bounded fixes for #20/#29, then specify minimum useful Memory behavior. Separately isolated concurrent tenant acceptance still requires authorized capacity and a supported entry point. This assessment does not authorize a new Memory framework or removal of the public tenant guard. The developer pilot has not started.

Before broader pilot acceptance, freeze each input and expected write/read result, then use separately authorized assessment targets. Run normal Engram API → ledger → workers → graph → retrieval, including concurrent tenant IDs, recovery and evidence checks. Retained G05/G06/G7 data remains protected. Preserve failures. Historical migration, ANN stress tests and hierarchy-policy design remain outside this assessment.

## Reproduce the local diagnostics

```sh
PYTHONPATH=src .venv/bin/python docs/review/spanner-compatibility/runs/20261010-pack-composition-assessment-local/configuration-probe.py
PYTHONPATH=src .venv/bin/python docs/review/spanner-compatibility/runs/20261010-pack-composition-assessment-local/shared-logic-probe.py
```

The original configuration probe warnings are retained in configuration-probe.log. JSON results are clean machine-readable evidence. No token or credential was captured.

## Source grounding

`ontology/loader.py`, `ontology/runtime.py`, `domain/pack_bundle.py`, `ontology/packs/{core,user,memory,pdlc}.pack.yaml`, `worker/__main__.py`, the five worker modules, `adapters/graph_ops.py`, `adapters/composed_reads.py`, `api/tenants.py`, `tenancy.py`, and `retrieval/{engine,artifacts}.py`.

This assessment reuses the earlier independent Astra source review; no new independent review or cloud sign-off is claimed.

## Next checkpoint authorized — 13 October: user attachment and retry safety

Memory remediation is separately verified and published in `51bb4fd`; that does not resolve the user or enrichment findings above. The stakeholder authorized the previously agreed sequence and reaffirmed the verification and umbrella-tracking requirements. The first bounded stage is user attachment, profile identity and retry safety. Enrichment, whole-combination verification, two-tenant isolation and the pilot remain later approval checkpoints.

GitHub's native sub-issue relation was checked: #20, #29, #37, #39, #42 and #43 are actual children of feature umbrella #34. #41 remains the separate linked Spanner-verification umbrella. Existing issues cover the observed failures; no duplicate issue or new feature bucket is needed at this checkpoint.

For the first stage, reuse extraction, UserStore/graph adapters, User pack declarations, composed reads and existing user/retrieval APIs. Current grounding confirms #20's `entity_id` provenance allowlist mismatch; the profile writer uses `profile:<user_id>` while UserProfile declares `user_id`; preference writes without an explicit identity generate random IDs and increment on repeated calls. These are observed implementation boundaries, not completed fixes or a commitment to new infrastructure. Choose the smallest coherent correction after checking producer, storage and read callers.

| Case | Required observable result |
|---|---|
| UA01 interest attachment | Actual extraction creates the intended interest Entity and exact DERIVED_FROM evidence, completes and acknowledges the session-end delivery |
| UA02 profile identity | User API, composed reads and applicable personalization resolve the same canonical newly created profile and owner |
| UA03 exact retry | Reprocessing the same accepted observation/session-end does not create another preference or increase its support/observation count |
| UA04 interrupted write and restart | A fault after partial output remains recoverable; restart/retry converges to exact artifacts and evidence without double counting; label injected-provider/storage tests separately from live results |
| UA05 correction | An explicit changed preference preserves the defined prior history and source evidence; same-key unrelated context is not silently overwritten |
| UA06 owner boundary | A second owner has a positive profile/preference read and does not contaminate the first owner's applicable results; logical owner filtering is not tenant isolation sign-off |
| UA07 selection boundary | Core+User and Core+User+Memory preserve supported behavior; User-off Core+PDLC creates no User-specific outputs and preserves domain/core processing |

Freeze concrete payloads, literal identities, property values, relationship directions, source membership and forbidden effects before live execution. Run through authenticated Engram HTTP, actual ledger/workers, the authorized assessment Spanner database and public reads; raw row inspection supplements those reads. Reuse the latest epoch18 retained record only after verified export/owner/fingerprint checks, and retain final data. No historical migration or other database reset is authorized.

Completion requires targeted regressions, independent Astra review, real-Spanner case results including retries/failures, retained failed attempts, a stakeholder verification walkthrough, issue reconciliation with precise open/closed criteria and a feature-bucket assessment. Do not close #34/#42/#39/#41 from this slice alone. At this checkpoint only source/issue grounding has begun; there are no new runtime fixes or live runs to report.

Authorized scope/verification checkpoint published to [#42](https://github.com/arunmenon/Engram/issues/42#issuecomment-6147429971); the matching #34 umbrella comment records the same stage and stop boundary. These are scope updates, not new completion claims.

## User attachment/retry checkpoint completed — 13 October

The bounded UA01–UA07 slice is implemented and independently reviewed. [Verification and stakeholder walkthrough](user-attachment-verification.md) records 277 accepted real-Spanner assertions: Core+User 134 and Core+User+Memory 131 on final-source attempt08, plus User-off Core+PDLC 12 on the unchanged disabled path from attempt06. Final User+Memory data is retained at epoch 29 with a fresh matching owner/fingerprint recheck. All failed attempts remain preserved.

Interest attachment, canonical profile reads, owned personalization, frozen User output application, distinct-support retry counts and explicit context-specific preference corrections are verified for those cases. User writes also preserve shared Entity timestamp chronology. Real-model primary extraction is separated from controlled-provider exception/restart probes. Latest local results: 24 User tests, 124 affected tests, 2,809 broad unit passes/13 skips with the known baseline PDLC evaluation-gate file excluded; typing/lint pass. [Astra final review](user-attachment-review/astra-final-review.md) found no remaining blocker for this slice or bounded defects #20/#59.

A separate production shutdown defect was discovered and filed as #60, an actual child of #34: consolidation can cancel an in-flight timer SDK await and leave late writes. The harness now waits for healthy consolidation to become idle before stopping; this is not a production fix or general shutdown proof. Issue #60 remains a pilot prerequisite. The exact two late edges from failed attempt07 and fresh post-process fingerprints are reconciled in its retained evidence.

The larger #34/#42/#39/#41 scopes remain open. No new feature bucket is needed: #20/#42/#59 cover this User slice, while #60 fits existing worker reliability scope. Next is stakeholder review, then separately approved enrichment ordering (#29), wider pack combinations, isolation and remaining pilot prerequisites. None of those stages or the pilot started here. G8–G11 are not collectively marked complete from this bounded slice.

Publication reconciled: runtime `782ab1e`, evidence `61475be`, on `feature/engram-memory-episodes`. GitHub #20 and #59 are now CLOSED; #34/#42/#39/#41/#60 remain OPEN. Final parent/state verification and comment links are in the User walkthrough. No subsequent stage was started.

## 2026-10-13 — enrichment ordering checkpoint

The separately authorized #29 slice is verified: EN01–EN07 passed for Core, Core+User, Core+User+Memory, Core+PDLC and Core+PDLC+Memory on the reused assessment Spanner database (58 assertions each, 290 total). Missing projection no longer loses enrichment; stale projection and duplicate enrichment preserve derived metadata and adjusted importance. Astra cleared bounded closure. [Verification and stakeholder walkthrough](enrichment-ordering-verification.md) includes failures, exact results and scope limits.

The final epoch36 dataset is retained after verified exports of previous owners. #61 newly tracks UUID subgraph access accounting; cached replay lineage remains #18, shutdown remains #60. No new feature umbrella is needed; these fit #34. Whole-combination producer coverage, concurrent tenant isolation and the controlled pilot are not complete or started by this common-enrichment proof. Next slices still require stakeholder selection; no automatic progression.

## 2026-10-14 — consolidation shutdown checkpoint

The separately authorized #60 slice is verified: seven lifecycle cases, 109 live Spanner assertions, real SDK-held stop/cancellation/fencing and fresh-worker recovery, with exact Summary/Episode/public-read evidence. Astra cleared bounded closure. [Verification and stakeholder walkthrough](consolidation-shutdown-verification.md). Shutdown now joins the complete admitted cycle and wakes an idle timer; no external consolidation-lock workaround was used for acceptance.

The final assessment dataset is retained at epoch 37 after a verified export of the previous enrichment dataset. #34/#39/#41 remain open; #18/#61 and broader composition/tenant proofs are not resolved by this slice. No new feature umbrella is needed. No next slice or controlled pilot started.

## 2026-10-14 — UUID subgraph access accounting (#61)

The selected follow-up fixes UUID Event access accounting: subgraph retrieval now chooses returned Events by validated type after pagination. Core and Core+PDLC+Memory passed 228 real-Spanner assertions through authenticated ingestion, all five real workers and the subgraph API. Entity/Episode/Summary and unreturned Event properties remained unchanged; repeated returned Events incremented once per read. Final owner epoch 39, all table fingerprints, snapshot and217 source hashes matched fresh-process readback. Data retained in the same assessment database.

[Verification and stakeholder walkthrough](subgraph-access-verification.md). Independent closure disposition and actual GitHub reconciliation are recorded there. This is not concurrent counter, public tenant-dispatcher, full pack-combination or pilot sign-off. The next broader assessment/isolation stage still needs explicit user approval.


## 2026-10-14 — Post-remediation five-combination checkpoint

The stakeholder selected the bounded combination verification before isolation/pilot. Core; Core+User; Core+User+Memory; Core+PDLC; Core+PDLC+Memory passed 793 real-Spanner assertions across 39 accepted Events, 19 rejections and 9 duplicates. Authenticated ingress, all five production workers and the three relevant read API families were used. Fixed external provider outputs make this a composition/validation/write/read proof, not LLM quality evaluation.

The first attempt exposed #62: repeated Entity resolution reconstructed a normalized name as a different storage key, dropping later REFERENCES. Astra confirmed the cause. The correction carries and validates the existing Entity ID through exact/fuzzy/semantic resolution and uses it for evidence endpoints. Fourteen new regressions and 117 affected tests passed; the broad suite passed 2848/13 skipped with the documented PDLC evaluation-gate exclusion. The deficient first run and artifact API oracle correction remain retained.

Astra accepted the full corrected five-configuration checkpoint and bounded #62 closure. All 218 source hashes, every export digest, epoch 48 owner/fingerprints and retained graph matched fresh readback. Final PDLC+Memory data is retained; earlier stage datasets are verified exports. [Stakeholder walkthrough, evidence, review and actual GitHub reconciliation](pack-combination-verification.md). No new feature bucket is needed; umbrella34/39/41/42 remain open. Original broad goal remains paused. Stop here: two-tenant isolation and controlled pilot require the stakeholder's next selection.
