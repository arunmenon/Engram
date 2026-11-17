# Review: Engram video walkthrough plan

Date: 2026-11-02. Scope: `docs/engram-video-walkthrough-plan.md` reviewed against the working tree at commit 27b4ba8 plus untracked files. Read-only review. No code, fixtures or expectations were changed; no model job, deployment or recording was started.

Fresh evidence gathered for this review: `pytest tests/unit/test_workbench.py tests/unit/test_workbench_journeys.py` passed 34 tests today. Everything else about runtime behaviour is from source inspection or the Oct 31 acceptance record.

## Verdict

The plan is honest and filmable, but not yet scriptable. The storyline and the chapter order are right, and every chapter has a real screen behind it except chapter 4. Three things must change before a storyboard is drafted:

1. Chapter 4 cannot be filmed as "tenants and configuration". The workbench "tenant" is a draft record in a local SQLite file. No tenant runtime is deployed, the tenant dispatcher is not production-enabled, and there is no activation, intent-readiness or provisioning API. The chapter must be reframed as draft workspaces plus a diagram of the tenant binding.
2. Chapter 5 has never been rehearsed end to end with a real model through the UI. The browser acceptance of pack authoring used the labelled fixture author. The one real-model incident pilot failed its sandbox at mean F1 0.65 and was never approved. The plan requires real-provider generation on camera, so a full real-model rehearsal is a prerequisite, not a step 3 nicety.
3. "No pack-framework feature missed" is not achievable through the UI alone. Roughly a third of the framework (versioning against a prior version, worker reconcile, blue/green rebuild, the evaluation gate at runtime, the ontology CLI, strict properties, extraction, processing bindings) has no workbench surface. The plan needs a terminal chapter for the pack lifecycle, not just an inventory note that these are "backend-only".

One process blocker sits above all of these: the entire workbench (frontend, backend, tests, journey plan, acceptance record) is untracked in git. A video of uncommitted code documents nothing reproducible. Commit the workbench, or at minimum tag the exact tree, before the first take.

## Findings, by consequence

### Blockers

**B1. Chapter 4 describes a product that does not exist (plan §Chapters row 4, §Tenant configuration story).**
Evidence: `src/context_graph/workbench/models.py:33` (environment is a free string), `api.py:204-208` (runtime pills hardcoded to `not_requested` / `not_evaluated`), `api.py:175` (activation capability hardcoded False), `tenancy.py:3-4` ("No production dispatcher is enabled here"), `docs/runbooks/tenant-api.md:16-37` (catalog fixed per process, no onboarding, no activation). The UI has no side-by-side comparison, roots are fixed to memory and user, and the only selectable existing pack is PDLC (`Workbench.tsx:741-779`).
Why it matters: the chapter's learning outcome, "know what differs by tenant and what is shared", would be taught from controls that do not control anything.
Smallest correction: rename the chapter "Draft workspaces and the tenant boundary". Film the tenant card grid and one draft's Customer setup step. Then cut to a diagram built from `tenancy.py` (binding = settings + engine revision + pack digests + trust policy; catalog; credential grant; per-tenant database) and say on camera that this binding is constructed by configuration today and that the workbench hands off to it rather than activating it. Delete "compare prepared PDLC and incident drafts" or film it as two browser tabs.

**B2. Agent-assisted onboarding has no real-model UI rehearsal (plan §Concrete onboarding demonstration, steps 5 to 9).**
Evidence: `docs/review/2026-10-30-workbench-implementation.md` ("UI testing used the clearly labelled fixture author"), `scripts/engram_workbench_dev.py:21-36` (`--fixture-author`), `output/workbench/northstar/exercise-record.json` (real model, validation passed, sandbox failed at F1 0.65 vs required 1.0, unapproved). Authoring calls litellm with up to three repair attempts inside 245 s (`authoring.py:162-210`) and no spend limit.
Why it matters: the plan forbids canned results when presenting agentic execution. Today there is no evidence the real path produces an approvable incident pack through the browser.
Smallest correction: make a full real-model incident run through the UI the exit criterion of gate 3, with the synthetic bundle frozen afterwards. Decide in advance whether the Northstar-style failure (US and EU incidents merged) is the on-camera failure story for step 10, because it is a genuinely good one.

**B3. The pack-framework feature set is wider than the UI (plan §Feature coverage, chapter 7).**
Evidence: see the coverage matrix below. Nothing in `demo/frontend/src/workbench/` touches the ontology CLI, `GET /v1/ontology`, `POST /v1/query/artifacts` with `eval_pending`, worker reconcile, rebuild, strict properties, extraction profiles or processing bindings. The change class shown on the Review step is always `initial` because `engine.py:130` classifies against `None`.
Why it matters: the user's requirement is that no pack-framework feature is missed. The current chapters cover authoring and journeys only.
Smallest correction: add chapter 7b, "Pack lifecycle from the terminal" (about 5 minutes): `python -m context_graph.ontology status` on the CRM or incident pack, edit the pack to show an additive and then a mapping change and the required bump, `evaluate --record`, a `curl` of `/v1/query/artifacts` returning 409 with `eval_pending` before and a result after, and `rebuild --target` for a breaking change. This needs a store the CLI and API can share, so Redis and Neo4j via docker compose or the Spanner emulator, not the in-process memory backend. Rehearse before committing to it. Narrate the Review step's change class as "initial for a new pack", never as a diff against a prior version.

**B4. Nothing being filmed is committed.**
Evidence: `git status` shows `demo/frontend/src/workbench/`, `src/context_graph/workbench/`, `src/context_graph/tenancy.py`, `src/context_graph/api/tenants.py`, both workbench test files, `docs/pdlc-journey-workbench-plan.md` and all three plan documents as untracked.
Smallest correction: commit or tag before recording, and put the commit hash in the transcript.

### Corrections required in the plan text

**C1. Historical counts are confirmed but must be dated (plan §Evidence and known limits).**
`output/workbench/pdlc/acceptance-verification.json` (mtime 2026-10-31 19:49, no internal timestamp): 288 passed, 2 failed, 1 unsupported across 18 workspaces; 4 event-driven journeys, 13 graph-seeded retrieval scenarios, 1 assistant variant; engine digest `c5579a6b…`; backend isolated-memory throughout. The two failures are the implementation and planning conflicting-retry checks (memory ledger says duplicate, fixture expects conflict). The unsupported item is the release journey's deployment-only group. The recorded "68 passed" was a wider selection; today's run of the two workbench files is 34 passed. Narration may quote these numbers only with the date.

**C2. "Sandbox in an isolated database" is wrong wording (plan §Chapters row 6, §Concrete onboarding step 9).**
`sandbox.py:47-57, 123-137`: memory backend for every port, labelled "isolated-memory, not Spanner or a live deployment". It does run the real admission policy, ledger append, ProjectionConsumer and ArtifactRetriever. Say "an isolated in-memory run of the real pipeline".

**C3. Planned versus observed is two artifacts, not a comparison (chapter 6 outcome).**
`engine.py:96-125` records the planned writes per sample; `sandbox.py:85-103` records the stored graph per event. No diff is computed. The sandbox verdict compares questions (F1), missing expected nodes and forbidden nodes (`sandbox.py:112-122`). Film the planned delta on the Technical inspection panel and the observed graph on the Test step, and narrate them as two views. Do not promise a diff.

**C4. The identity decision has no before/after view (onboarding step 6).**
`OperatorFlow.tsx:283-295`: identity and lifecycle questions are always injected as free-text boxes. The effect on the key appears only after "Apply my changes" re-authors the model and the type card changes (`OperatorFlow.tsx:349-352`). Script the scene as: read the sample with the same incident number in two accounts, answer, apply, show the key change on the type card and in the planned delta node id. Budget one model call for it.

**C5. Evidence formats (onboarding steps 3 and 4).**
`Workbench.tsx:859`: uploads accept `.txt`, `.md`, `.json` only; 160 KB per file, 40,000 characters per source, 20 sources per draft, 100 sample events max (`models.py:14-18, 39`; `authoring.py:16-35`). The process specification must be Markdown or text. Say "no PDF" on camera if documents come up.

**C6. Navigation and layout facts for the shot list.**
Step 3 "Technical inspection" has no nav button; it is an expander inside step 2 (`OperatorFlow.tsx:5`, `Workbench.tsx:1069-1276`). Schema and observed graphs live on different steps, never side by side. PackGraph renders at most 12 nodes in a fixed two-column layout (`PackGraph.tsx:30-36`), so choose samples that stay under that or use the node and edge tables. Trust controls are on the Expected results step, not next to pack selection. After "Save reviewed variant" the view switches to the new draft with no link back; returning to All tenants is how to show the baseline preserved.

**C7. Study guide drift (plan §Architecture opening).**
`docs/research/2026-10/walkthrough.html` describes the 2026-10-06 state. Wrong or stale today: memory and user "always load" (now optional via `CG_ONTOLOGY_BUILTIN_PACKS`); "17 node types" (18, DesignApproval missing); "eight edges carry confidence" (9); trust is only an allowlist (tenant-bound trust from authenticated source ids now exists); ingest checks omit payload contracts, handling and processing bindings; value language omits `match`, `map`, `each`, concatenation and the 10,000-operation cap; inert list is incomplete; no tenant content; the Spanner verification section predates the real-Spanner journey commits. Still accurate: consumer groups, three backends, shards, import caps, eval gate and 409 behaviour, five PDLC intents, three admission rules. Use only the big-picture, common-layer, ingestion and retrieval diagrams, and let narration carry the numbers. Fixing the six numbers in the HTML is a doc change the plan already allows under "reconcile historical content". Related drift: `docs/runbooks/pack-authoring.md` says PDLC has 23 payload contracts; the pack is at 2.1.0 with 25 events, all contracted. Do not quote the runbook's count.

**C8. Hardcoded PDLC in the journey UI.**
"PDLC ·" eyebrow and "PDLC retrieval" column are literals (`JourneyWorkspace.tsx:34,131`); journey names, the 13 retrieval scenarios and the frozen registry are PDLC-only (`api.py:235-253`, `journey_runner.py:38-49`); `existing_packs` is `Literal["pdlc"]` (`models.py:35`). Narration must not say journeys are domain-generic. The incident pack can be authored and sandboxed, but not journeyed.

**C9. Recording exposure.**
Header shows the operator identity; backend errors render as raw JSON; engine, input, pack and approval digests are on screen; download filename contains the draft id; the bearer token is visible in devtools. Use the default `local-operator` identity, keep devtools closed, and accept digests on screen since they are the point of the Review step.

### Optional improvements

- Chapter 1 can open on the Northstar failure instead of the PDLC question if the incident story is going to carry chapters 5 and 6 anyway; it makes the "sandbox said no" moment land harder in chapter 6.
- Chapter 7's failure story should be the duplicate-versus-conflict check. It is real, reproducible, unfixed on purpose, and explains what a ledger guarantees.
- The release journey's unsupported group is the cleanest way to say "this only exists in deployment" without a diagram.
- Per-question pass/fail is not labelled on the tenant Test step, only F1 numbers. Journeys show PASSED/FAILED per check. Pick the journey screen when the point is pass/fail.
- 39 minutes is plausible only if every model wait is cut. Author jobs run up to 250 s. Label the cut.

## Scene feasibility matrix

| Plan scene | Status | Where / note |
|---|---|---|
| 1 Why Engram exists | Narration + slides | No UI needed |
| 2 Architecture from study guide | Filmable with corrections | Four diagrams usable; numbers stale (C7) |
| 3 Ontologies and packs | Filmable | Technical inspection panel on an existing draft, or the CRM pack YAML in an editor |
| 4 Tenants and configuration | Not supported as written | Reframe per B1 |
| 5.1 Create draft, scope, environment | UI | Environment is free text; no exclusions field, prose only |
| 5.2 Data handling before model call | UI | Provider permission select + redaction checkbox gate the author button |
| 5.3 Upload specification, inventory | UI | txt/md/json only (C5) |
| 5.4 Schema + sample events | UI | JSON required; category auto-guessed |
| 5.5 Proposal with citations, inferred vs decided, open decisions | UI, real model required | Per-fact basis pills and verbatim quotes; server checks quotes (`authoring.py:67-84`) |
| 5.6 Resolve identity decision, see key change | Partial | Free text + re-author (C4) |
| 5.7 Types, contracts, mappings, planned delta | UI | Inside step-2 expander (C6) |
| 5.8 Question + expected entities | UI | EntityPicker shows readable labels; raw ids under Advanced |
| 5.9 Validate, review, sandbox, compare, F1 | UI | In-memory (C2); no planned/observed diff (C3) |
| 5.10 Stale evidence after input change | UI | Server flags; tested |
| 6 Observed graph per event | UI | Admitted/rejected per event, 12-node cap |
| 7 Prepared PDLC journeys, failure, unsupported | UI | 4 event + 13 retrieval; duplicate/conflict failure; release unsupported group |
| 7b Pack lifecycle CLI (new) | Terminal, needs rehearsal | status / classify / evaluate --record / 409 / rebuild (B3) |
| 8 Journey author brief → variant → run | UI, real model required | Must start empty, same frozen pack, ≤30 events; baseline shown via All tenants |
| 9 Review, change class, approve, export, history | UI | Change class always `initial` (B3); activation pills are placeholders |
| Activation / intent readiness | Not supported | Narration + diagram only |
| Side-by-side tenant comparison | Not supported | Two tabs or omit |

## Pack-framework coverage map

Where each feature family can appear so that nothing is silently dropped. "UI" means the workbench shows it; "CLI" means chapter 7b; "Say" means narration over a diagram or YAML.

| Feature family | Features | Cover in |
|---|---|---|
| Pack header and composition | name/version/requires, core mandatory, memory/user optional roots, dependency order, global name uniqueness, reserved `OntologyState`, composed version hash, `CG_ONTOLOGY_PACKS` | UI (roots checkboxes, Requires list, Composed bundle on Review) + Say |
| Types and lifecycle | key, properties and types, interfaces, lifecycle with `initial`/`states`/`superseded_states`, `text_fields`, edges with `requires`, `extends_core_edges`, link policy | UI (Types and lifecycle, Relationships, Transition rules) |
| Events and contracts | dot namespace ownership and 422, `payload_contract` rules, `handling` processed / ledger_only / unsupported, `processing` bindings, bundle identity | UI (Declared event contracts with handling pill; rejected events in sandbox) + Say for bindings |
| Projection and value language | upsert / transition / edges, `to_each`, `to_latest`, `match`, `when`, `only_from`, automatic `DERIVED_FROM`, stubs, fan-out zip/broadcast and 10,000-op cap, strict properties, six functions, 0.25 s regex bound | UI (MappingEvidence field buttons, expression vocabulary, planned delta) + Say for caps and strict properties |
| Retrieval | `seed_types`, `key_patterns`, intents with keywords/weights/`max_depth`/`direction`/`prefer_types`, `core_intent_weights`, `missing_links` plugin, three admission rules, 16-term / 400-call budgets, truncation, 504 | UI (Intent select, EntityPicker, sandbox F1) + CLI (`curl /v1/query/artifacts`) + Say |
| Trust and provenance | tenant-bound `trusted_source_ids` vs legacy agent allowlist, untrusted-uncorroborated admission, provenance from newest `DERIVED_FROM`, extraction proposals never confirmed | UI (Which sources should this test trust; retrieval-trust journey) + Say for extraction |
| Evaluation gate | eval set format, `min_f1`, mean F1, `eval_pending`, 409 on pending intent, 30 s state TTL, serve-unevaluated is dev only | UI (Required mean F1, eval YAML preview) + CLI (`evaluate --record`, 409 before/after) |
| Versioning and rebuild | none/initial/additive/mapping/breaking with reasons, bump rules, `eval_required`, worker reconcile (hot / replay / refuse breaking), blue/green rebuild with refusals | CLI only; Review step shows `initial` |
| CLI and HTTP | `status` / `evaluate` / `rebuild`, `GET /v1/ontology`, `POST /v1/query/artifacts` | CLI |
| Declared-but-inert | `embed_fields`, `lifecycle.decay`, `terminal_states_reduce_importance`, `extraction.derived_proposals`, `mappings`, extra link_policy keys; also silently inert: `aliases`, some admission settings, Neo4j-only indexes | UI ("Loaded but inactive" list on validation) + Say |

## Essential missing scenes

1. Chapter 7b, pack lifecycle from the terminal (B3).
2. A tenant-binding diagram scene replacing the chapter 4 controls (B1).
3. A 30-second "what the workbench cannot do" card before chapter 9: no activation, no deployed tenant, no PDF, in-memory sandbox, journeys are PDLC-only, change class is initial-only. The plan's honesty rules call for it and no chapter currently owns it.

## Not verified

- No real-model job was run. Authoring and journey synthesis behaviour comes from source and the Oct 30 and 31 records.
- The frontend was not built or opened in a browser for this review. Control inventory is from source.
- No Spanner, Redis or Neo4j instance was started. Chapter 7b feasibility on a shared store is inferred from `tests/unit/test_pack_toy_end_to_end.py` and the CLI code, not rehearsed.
- The Oct 31 acceptance record was not re-executed. Its engine digest was not recomputed against today's tree.
- Accessibility, keyboard flow and narrow layout claims in the journey plan were not re-checked.
