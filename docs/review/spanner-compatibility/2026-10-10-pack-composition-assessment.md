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
