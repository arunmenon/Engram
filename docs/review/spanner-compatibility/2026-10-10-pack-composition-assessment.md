# Pack-composition assessment: current behavior and pilot blockers

Status: local assessment complete; a bounded core-plus-PDLC case ran on real Spanner with real providers. Twelve basic checks passed, but the final stored-data audit found missing enrichment. Four other configurations and concurrent-tenant checks remain blocked by database capacity. This is not pilot readiness or completion of G08–G13.

G7 is treated as complete per the stakeholder checkpoint. It was not rerun or modified here. This assessment applies to `9abe3c3`, which matches the fetched `origin/feature/engram-g07-event-coverage` at assessment time. Its results do not claim to incorporate unidentified later G7 work elsewhere.

## Live assessment results

The run used a new database, `engram-assess-1010a-pdlc`. Application records entered through the authenticated private Engram HTTP API; all five real worker loops ran; both subgraph and artifact retrieval used Engram HTTP endpoints. Only the tenant-control bootstrap inserted metadata directly. There were no direct artifact inserts, scripted models, runtime fixes or historical migration.

| Configuration | Live result |
|---|---|
| Core | Not run; creation hit the instance's database limit |
| Core + user | Not run; creation hit the instance's database limit |
| Core + user + memory | Not run; initial target name exceeded 30 characters; corrected naming cannot proceed while capacity is full |
| Core + PDLC | Twelve basic checks passed; final enrichment diagnostic failed |
| Core + PDLC + memory | Not run; initial target name exceeded 30 characters; corrected naming cannot proceed while capacity is full |

The instance is `FREE_INSTANCE`. It allows five databases and now contains the four pre-existing databases plus the new assessment target. Existing databases were not modified or deleted. Continuing with separately isolated configurations requires additional database capacity. No paid instance or billing conversion was started.

### What worked in the available configuration

The twelve executed checks covered event admission; one ledger row and Event; subgraph retrieval; exact retry without another ledger event; invalid input rejected without writes; session-end admission; actual session extraction producing entities; absence of disabled user outputs; PDLC admission; Change projection; Change retrieval with originating-event evidence; and absence of dead letters.

The retained database contains three events, twelve graph nodes and fourteen edges. All five worker loops stopped cleanly; pending deliveries and dead letters are both zero. These counts do not imply that every output is correct.

### What failed or needs interpretation

**Enrichment is missing in the final graph.** The worker logged keywords and embeddings for all three events, but the final stored Event rows each have empty keywords. The post-run audit compares them with the literal expected keyword lists: `observation/input`, `system/session_end`, and `pdlc/change/created`. This confirms a live persistence problem relevant to #29. It does not yet distinguish missing-target timing from a later overwrite. No runtime fix was applied.

**Pack extraction also acted on the prose input.** It produced a Constraint about concise bullet-point answers and a proposed Decision about using Python for Orion. Both point to the source event. These were observed model outputs, not predeclared semantic acceptance cases; their suitability as PDLC knowledge needs assessment. They do not count as proof of useful Memory behavior.

**User and Memory findings remain locally grounded only.** This run did not exercise user profiles, preference retries, Memory production, concurrent tenants, public dispatch or recovery. The development unevaluated-bundle gate remains enabled. Cloud Monitoring export reported permission denial; monitoring readiness is not established.

### Evidence and repeatability

- [Original inputs, HTTP responses, checks, and final stored rows](runs/composition-1010a/pdlc-observations.json).
- [Additional enrichment audit and observed model outputs](runs/composition-1010a/post-run-audit.json). This preserves the original twelve results and adds a failed diagnostic; it does not rewrite the initial run as a clean pass.
- [Preparation results and initial expectations](runs/composition-1010a/manifest.json), with individual preparation receipts and raw logs in the same directory.
- [Retained owner and table fingerprints](runs/composition-1010a/retained-dataset.json).
- Runner: `scripts/engram_composition_assessment.py`. Seven local harness tests verify target naming and failure/blocked/empty/shutdown exit handling; lint passes.

The first preparation attempt exposed two harness naming mistakes. The runner now uses short suffixes and restricts run-ID length. It also has stricter final enrichment and exact artifact assertions, plus nonzero exit handling for failed or blocked checks. Those later harness edits have local tests; they have not been cloud-rerun. Existing evidence and the retained dataset must not be overwritten or adopted as a fresh run.

There is no new independent Astra sign-off for this live run. The pilot and any runtime fixes remain separate next steps.

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

## Verification and next checkpoint

**132 selected local regression tests passed.** [Exact command and result](runs/20261010-pack-composition-assessment-local/test-receipt.json). They cover composition, composed reads, extraction gating, tenant binding/dispatch and extraction behavior, using mocks/reference storage where applicable. They do not certify the public service, live LLMs or Spanner combinations.

The next checkpoint is to obtain capacity for the remaining isolated combinations and agree on bounded fixes plus minimum Memory behavior. This assessment does not authorize a new Memory framework or removal of the public tenant guard. The developer pilot has not started.

Before live acceptance, freeze each input and expected write/read result, then use fresh separately authorized assessment targets. Run normal Engram API → ledger → workers → graph → retrieval, including concurrent tenant IDs, recovery and evidence checks. Retained G05/G06/G7 data remains protected. Preserve failures. Historical migration, ANN stress tests and hierarchy-policy design remain outside this assessment.

## Reproduce the local diagnostics

```sh
PYTHONPATH=src .venv/bin/python docs/review/spanner-compatibility/runs/20261010-pack-composition-assessment-local/configuration-probe.py
PYTHONPATH=src .venv/bin/python docs/review/spanner-compatibility/runs/20261010-pack-composition-assessment-local/shared-logic-probe.py
```

The original configuration probe warnings are retained in configuration-probe.log. JSON results are clean machine-readable evidence. No token or credential was captured.

## Source grounding

`ontology/loader.py`, `ontology/runtime.py`, `domain/pack_bundle.py`, `ontology/packs/{core,user,memory,pdlc}.pack.yaml`, `worker/__main__.py`, the five worker modules, `adapters/graph_ops.py`, `adapters/composed_reads.py`, `api/tenants.py`, `tenancy.py`, and `retrieval/{engine,artifacts}.py`.

This assessment reuses the earlier independent Astra source review; no new independent review or cloud sign-off is claimed.
