# PDLC journey workbench execution plan

Status: verified local delivery. M1–M6 acceptance is complete within the local memory-backed scope below. Known domain failures and supplemental deployment checks remain explicit. Changes are local and uncommitted.

## Outcome and boundaries

An operator opens a prepared PDLC workspace, selects a journey, reviews its story and expectations, executes it, and inspects event handling, graph checkpoints and question results without generating a replacement pack. The same saved format later supports agent-proposed journeys for new domains. Preserve the current authoring workflow and tenant isolation. Use existing API/store/sandbox/graph components first; no separate service or workflow framework without demonstrated necessity.

Pin PDLC and dependency bytes, fixture sources and engine revision. Frozen baseline edits create a new explicit version; never silently weaken an oracle. Initial execution is local memory-backed and must say so. Historical Spanner evidence is not a new UI run. No deployment, live activation, cloud provisioning or historical migration. Payment-domain pack creation is subsequent scope.

## Milestones and objective acceptance

### M1 — Source inventory and reproducible baseline

Inventory tests/unit/test_planning_journey.py, test_implementation_journey.py, test_pdlc_end_to_end.py, test_pdlc_retrieval_eval.py, test_pdlc_opendal_eval.py, their fixture generators, evaluation YAML and scoped G02/G03 cloud verification records. Map each scenario/assertion to inputs, prerequisites and expected outputs. Pin source hashes and pack bundle. Run relevant local baseline tests and preserve failures rather than assuming historical success still applies.

Exit: every selected source assertion has an inventory row; distinction between local projection diagnostics, real admission/API checks, provider-dependent retrieval and historical cloud checks is explicit. Snapshot is reproducible. No coverage percentage without a denominator.

### M2 — Saved journeys and deterministic checks

Add bounded, versioned journey data using current persistence patterns: story/source references, pack digest, explicit starting setup, event envelopes and delivery order, checkpoints, questions and review state. Keep run records separate and tied to journey/engine digests. Support node/property presence and absence, edges, lifecycle, provenance, expected event disposition and retrieval required/forbidden nodes, edges and truncation where demanded by imported assertions. Preserve exact versus subset semantics. Existing question evaluation remains canonical; do not create competing question stores.

Exit: serialization/validation tests, deterministic rerun, exact failure diagnostics, changed inputs invalidate results. Unsupported/not-run/error are distinct from pass/fail. No fabricated HTTP status from a runner that did not exercise HTTP.

### M3 — First complete UI journey

Adapt the existing implementation fixture: requirement/design/ticket/change/reviews/failed and successful tests. Provide an existing-pack path independent of model-provider permission or authoring. UI: prepared workspace, journey catalogue, readable overview/timeline, run action, checkpoint graph and assertion results with technical detail expandable. Reuse current sandbox isolation and bounded jobs.

Exit: computer-use run from catalogue to results; original expected results retained; observable discrepancies from baseline documented. Failure path and cancellation work; no provider call needed to execute a prepared journey. Agent-free execution is a real supported path, not an empty generated pack workaround.

### M4 — PDLC coverage migration

Adapt planning revisions/approvals/placeholders, webhook release/deployment and relevant negative cases. Preserve semantic assertions, including duplicate/conflict and rejected-before-write checks where the execution path supports them. Normalize webhook fixtures through the actual adapter or label normalized execution separately from webhook verification. Large/provider-dependent fixtures may need bounded batches or explicit supplemental checks; report this rather than silently sampling. Add a connected lifecycle only with consistent identities and explicit prerequisites.

Exit: all M1 rows classified implemented/pass, implemented/fail, unsupported, or excluded with reason. No unsupported core acceptance check may be called complete; fix support needed for ordinary local PDLC journeys. Historical deployment-only guarantees remain supplemental and labelled. UI exposes journey-specific coverage and failures.

### M5 — Bounded agent journey synthesis

Within the same workspace offer a journey outline proposal grounded in pack contracts, supplied domain specifications and coverage gaps. Operator resolves meaningful assumptions, then requests synthetic events and independently reviewable checkpoints/questions. Treat uploaded text as evidence, not tool instructions. Reuse configured model, bounded task/cancellation and permissions. Save concrete generated data for reproducible runs. No arbitrary generated Python/assertion execution. Revisions preserve prior failures and invalidate review; never update expected outcomes from observed outputs automatically.

Exit: real configured-agent PDLC variant generated through UI, decisions/citations inspectable, valid events and deliberate negative cases distinguishable, expected results reviewed before run, repeat run uses identical saved inputs. Retain imported independent tests as regression/held-out evidence; once exposed, do not claim they remain unseen.

### M6 — End-to-end verification and handoff

Run scoped backend regression, frontend type/build and actual computer-use flows: prepared journey, failed check investigation, variant generation/review/run, stale result after edit, wrong-owner access and cancellation. Check readable entity labels, keyboard use and narrow layout. Verify all existing workbench tests still pass; expand testing only for new failures or changed callers. Record screenshots and exact commands/results in this document. Leave the prepared PDLC workspace open for the user.

Exit: delivered operator flow and source-to-assertion matrix, passing infrastructure tests, honest domain failures with evidence, no silent unsupported checks, preserved original authoring workflow. Goal completion means these deliverables exist, not that every domain oracle has been forced green.

## Execution protocol

One overall active goal; milestones executed in dependency order. M1 discovery can refine implementation choices, but changes to scope and acceptance must be recorded. No milestone is complete based only on helper code. Report concise progress and concrete blockers. Reuse the shared dirty working tree carefully; do not revert or commit unrelated files. No subagent delegation is implied. Agent may implement and run local reversible checks under current authorization.

## Initial inspected evidence

- Current workbench Content permits pdlc in existing_packs but generated Proposal remains a separate path; an existing-pack run must be verified, not inferred from that selector.
- G03 local test imports scripts.engram_goal03_fixtures.fixtures, projects accepted events into MemoryGraphStore, and checks explicit-seed retrieval. It deliberately skips duplicate/conflict HTTP behaviour and text-only provider-backed acceptance. UI migration must retain these distinctions.
- Historical G02/G03 records report scoped Spanner acceptance. These are source material, not proof of the new UI execution.

## Operator quick start

Open `http://127.0.0.1:5174/workbench.html` while the local API (8101) and frontend (5174) are running. The existing operator session is retained. From **All tenants → Explore an existing ontology**, choose implementation, planning, release/deployment, or reference boundaries. For query scenarios, choose an option in **Retrieval scenario** and click **Open retrieval fixture**; each option uses an isolated, already-configured test graph. Click **Run journey**, inspect the result, and select an **Event checkpoint** to see the graph actually stored at that step. Expand a failed or unsupported check to see its expectation and observation. The coverage disclosure explains which original tests are represented and which remain supplemental.

To synthesize a variant, expand **Create a new journey with the assistant**, enter the situation and domain rules, explicitly allow the supplied context to the configured model, review the outline and answer its decisions, then generate events and expectations. Review those expectations before saving a separate workspace. Running or rerunning a saved journey does not call the model. The demonstrated variant is **Design approval does not transfer to superseding revision**.

For a fresh local session, use the existing developer launcher with `ENGRAM_WORKBENCH_TOKEN` set to an operator token, `ENGRAM_WORKBENCH_DB` set to a local SQLite path, and `ENGRAM_WORKBENCH_MODEL` set to the configured model ID when synthesis is wanted: `.venv/bin/python scripts/engram_workbench_dev.py`. Start the UI with `npm --prefix demo/frontend run dev:workbench`. Prepared journeys need no model credential. These commands neither provision a cloud database nor activate a tenant binding.

## Completion audit — verified local delivery

Branch: `feature/engram-walkthrough`, with local uncommitted changes. Final engine fingerprint: `sha256:c5579a6b2cf67d1ef5fc65b6672ff134d151dbaadebdfff3bf594a36baec5dc9`.

The authoritative acceptance record is `output/workbench/pdlc/acceptance-verification.json`, with per-workspace exports `acceptance-<journey-id>.json` and `acceptance-*.jpg` browser evidence. Earlier “final” files and the progress log below are historical snapshots, not the current acceptance claim.

| Requirement | Current evidence |
| --- | --- |
| M1: inventory and frozen baseline | Manifest pins 53 files, all hashes checked with no mismatch. All 144 selected Python assertion sites are accounted for: 96 implemented and passing their mapped checks, 48 supplemental with explicit reasons, none pending. The 77 historical cloud-harness sites are separately indexed, not presented as fresh runs. Original pack bytes and test source hashes match. |
| M2: saved data and faithful checks | Bounded data-only journeys, immutable input digests, isolated memory runs, independent result records and stale-state detection. Source parity tests compare event inputs, graph variants, query parameters and benchmark scores. Negative tests detect extra nodes/edges, wrong reasons/provenance, bounds, metadata, truncation and failed score targets. No generated executable code. |
| M3: implementation through UI | Prepared implementation journey run via computer use on final engine: 23 deliveries, 110 passes and the retained conflicting-retry failure. Earlier browser failure inspection/cancellation evidence is preserved; current cancellation and stale-result regression tests pass. |
| M4: PDLC migration | Four event scenarios and thirteen retrieval scenarios refreshed through the UI. All original core graph-seeded retrieval cases, including rejected-edge filtering, paging, work limits and category evaluation, now have executable equivalents. Direct graph setups are labelled final-state retrieval evidence, not ingestion/extraction evidence. Supplemental boundaries remain below. |
| M5: real agent workflow | Persisted real-model outline/generation history in planning workspace `d7b64e8b-6ced-48bc-b051-25ab132cd89e`; six-event reviewed variant saved separately at `fb12bf84-8fde-4b09-887b-65b57d3b194a`. Final-engine UI run and repeat each pass 19 checks with identical digest `776e00bd92ada3754a5faa14da6640a6bccdbe6ef5962ae39d38861556ebcbcf`. Consent/review, owner isolation, generation failure feedback and preserved-baseline tests pass. Earlier unsuccessful generations and independent expectation corrections remain documented. |
| M6: verification and handoff | 68 scoped tests pass, Ruff and workbench mypy pass, standalone frontend type/build passes. Computer-use refresh covers 18 workspaces; original Northstar authoring still opens with six steps and saved evidence, with its appropriate stale-engine notice. Narrow viewport has 354px client/scroll width; prior keyboard selection evidence is retained. Verified question-evaluation workspace is left open. |

### Observed outcomes and limits

Across the 18 refreshed workspaces: **288 passed checks, 2 failed checks, 1 unsupported group**. These counts are not source-assertion coverage percentages. The 96 mapped source assertion sites all have passing mapped checks; the conflicting-retry expectations additionally retained from fixture requests expose a memory-ledger discrepancy.

| Scenario | Deliveries | Pass / fail / unsupported |
| --- | ---: | --- |
| Implementation | 23 | 110 / 1 / 0 |
| Planning | 17 | 78 / 1 / 0 |
| Normalized release/deployment | 8 | 33 / 0 / 1 |
| Reference boundaries | 7 | 13 / 0 / 0 |
| Base retrieval graph | 0 | 22 / 0 / 0 |
| Twelve retrieval variants | 0 | 13 / 0 / 0 (category benchmark contains nine questions) |
| Reviewed agent variant | 6 | 19 / 0 / 0 |

The two failures preserve the original conflicting-retry expectation: changed content reusing an event ID should conflict, while the memory ledger reports duplicate. They were not fixed by changing the ontology or oracle. The release unsupported group discloses deployment-only behavior. HTTP statuses shown as expectations are not fabricated observed HTTP results: `http_exercised` remains false.

The 48 supplemental source sites remain in intact original suites: runtime evaluation registration/pending gates, HTTP query response guarantees, versioning/rebuild, extraction, signed webhook/spoofing checks, and the complete 292-event OpenDAL workload. The full local original suite was run as supplemental evidence, not relabelled as UI coverage. There is no claim of fresh Spanner, deployed networking, activation, provider extraction, or production tenant-isolation certification.

Category evaluation reproduces all nine original questions and source scoring: category mean F1 is 1.0 for PDLC retrieval versus 0.533 supersession, 0.167 completeness and 0.667 negation for the text-only baseline. The operator can inspect the expected, retrieved and baseline answer sets. This small fixed fixture is regression evidence, not a general quality benchmark or a held-out model evaluation.

### Reproducible verification

- `.venv/bin/pytest tests/unit/test_workbench.py tests/unit/test_workbench_journeys.py tests/unit/test_planning_journey.py tests/unit/test_implementation_journey.py 'tests/unit/test_pdlc_end_to_end.py::test_webhooks_build_a_pdlc_graph[memory]' tests/unit/test_pdlc_opendal_eval.py tests/unit/test_pdlc_retrieval_eval.py -m 'not integration' -q` — **68 passed, 4 deprecation warnings in 19.04s**; `output/workbench/pdlc/acceptance-tests.txt`.
- `.venv/bin/ruff check src/context_graph/workbench scripts/engram_freeze_pdlc_retrieval_variants.py tests/unit/test_workbench_journeys.py` — passed.
- `.venv/bin/mypy src/context_graph/workbench --no-error-summary` — passed, with an existing unused-configuration-section note.
- `npm --prefix demo/frontend run build:workbench` — passed; `output/workbench/pdlc/acceptance-build.txt`.
- Final UI evidence: `acceptance-implementation.jpg`, `acceptance-planning.jpg`, `acceptance-release.jpg`, `acceptance-references.jpg`, all thirteen `acceptance-<retrieval-scenario>.jpg`, `acceptance-agent-variant.jpg`, `acceptance-existing-authoring.jpg`, `acceptance-narrow.jpg`, and `acceptance-handoff.jpg`.

Scoped artifact-quality gate: **PASS for this local journey-workbench delivery**, based on the requirements/evidence above. Earlier REVISE findings—blanket exclusion of graph retrieval and obsolete rejected-edge exclusion—are resolved. Known domain failures, supplemental checks and historical evidence are visible, not averaged into a green claim. No deployment, cloud provisioning, tenant activation, commit, or original ontology edit was performed. Payment packs remain subsequent work. This is not an independent security certification or a full accessibility audit.

## Progress log

The entries below are historical; the completion audit above is the current state.


- Plan and overall goal created. M1 source tracing started; no runtime or UI implementation changes yet.
- M1 progress: frozen YAML copies and SHA-256 source manifest saved under src/context_graph/workbench/fixtures/pdlc. Captured planning (17 deliveries, 5 queries) and implementation (23 deliveries, 5 queries) generator outputs, preserving expected outcomes and replacing wall-clock timestamps with deterministic fixed times. Indexed 144 Python assert sites for adaptation; this is not a count of business scenarios or exhaustive cloud-run assertions. Manifest inventory remains to be reconciled with cloud harness checks and evaluation YAML.
- Current local baseline: planning, implementation, memory webhook end-to-end and OpenDAL tests: 8 passed in 5.43s. Command: `.venv/bin/pytest tests/unit/test_planning_journey.py tests/unit/test_implementation_journey.py 'tests/unit/test_pdlc_end_to_end.py::test_webhooks_build_a_pdlc_graph[memory]' tests/unit/test_pdlc_opendal_eval.py -m 'not integration' -q`. An earlier broad parameterized invocation was interrupted after 6 passes/1 skip to restrict execution explicitly to memory; it is not acceptance evidence for external backends.
- M2 started: bounded versioned Journey/Event/Check/CheckResult contracts added in journeys.py, with checkpoint-reference and ID validation and distinct unsupported/not_run/error statuses. Runner, API integration and UI remain unimplemented. Ruff passed on the new module. Goal remains active.
- User steering: proceed step by step and avoid unnecessary complexity. Immediate implementation stays limited to one existing G03 journey; broader migration and synthesis remain later milestones, not concurrent infrastructure work.
- First fixture adapter implemented: 23 unchanged event requests and 94 explicit checks (ingestion outcomes, no-change cases, entity properties, source evidence, relationships and five retrieval expectations). This is an adapter, not a runnable UI yet. Two focused tests pass, demonstrating exact event/query preservation, deterministic round-trip and invalid checkpoint refusal. Next step is executing this journey with existing engine components, then connecting its results to the current UI.
- First runnable vertical slice delivered locally: prepared implementation workspace, existing bounded job runner/cancellation, frozen bundle, actual memory ledger and projection worker, checkpoint graphs and check results. The UI entry is “Open prepared PDLC journey”; no model call or regenerated ontology. Browser execution observed 23 deliveries, 92 passed checks, one failed semantic conflict check and one unsupported provider-dependent query. Changed-content retry is reported duplicate by memory ledger; original fixture expects conflict. Original HTTP assertions are shown but only semantic outcomes are compared, explicitly labelled; this does not claim API route coverage. Screenshot: output/workbench/pdlc/first-journey.jpg.
- Checks: 13 combined workbench tests passed (10 existing plus 3 journey tests); Ruff, mypy and standalone frontend build pass. Browser verified open → run → results → expanded failed/unsupported details. Prepared results persist in the existing operator store; no existing drafts or pack definitions changed.
- Remaining first-slice work before M3 closure: reconcile retrieval edge/property assertions and exact graph-edge oracles from original tests (current 94 checks are not full source parity), improve readable timeline/check labels, expose recorded HTTP coverage separately rather than implying equivalence, and test cancellation/rerun/stale engine results. Broader migration/synthesis remain deferred until this slice is complete.
- First-slice strengthening: imported cumulative exact domain-node/edge/property/evidence checks and retrieval required-edge/property/provenance/commit-link checks from the original G03 diagnostics/cloud oracle. Semantic run now has 111 checks: 109 pass, one changed-content retry fails, one provider-dependent text query unsupported. The UI browser run reproduced these results and now shows readable event titles. This still does not assert cloud ownership/fencing, HTTP status, extraction, or full persistent-ledger invariants; those remain supplemental coverage, not implied passes.
- Added negative tests for unexpected graph edges/stale properties, job cancellation termination without a late result, and stale engine-result labelling. 16 scoped tests pass, Ruff and mypy pass, frontend build passes. UI preserves earlier prepared baseline rather than silently replacing its oracle; the prepared entry opens the latest template, existing earlier workspace remains intact. Screenshot: output/workbench/pdlc/implementation-checkpoints.jpg.
- Next incremental journey: planning reuses the same fixture adapter, runner, persistence and UI. Added 17 original deliveries and 79 checks, including no implicit approval of revision two, identity-only placeholder before arrival, no invented placeholder provenance, and its later content/evidence. Direct run: 77 passed, one changed-content retry failure, one provider-discovery unsupported. No PDLC ontology change. The shared adapter retains frozen event identities and original queries.
- Validation: 17 scoped tests passed, Ruff/mypy/build passed. Added regression asserting that the earlier placeholder snapshot remains empty after its later event supplies content. The catalog now offers separate implementation and planning buttons; existing run results remain pinned and are marked stale after engine edits.
- Release/deployment slice: retained eight original webhook payloads plus their actual adapter-normalized outputs and original 11-question evaluation YAML. Same runner executes eight events, graph assertions and evaluation via the existing EvalSet interpreter. Direct result: 27 passed; one supplemental coverage group explicitly unsupported (signatures/spoofed identities, HTTP deployment gate, extraction/rebuild). Individual question expectations stay exact (F1=1), preserving the original test's stricter per-question assertion rather than just the YAML aggregate threshold.
- Corrected an unnecessary earlier limitation after testing: current ArtifactRetriever can execute the planning and implementation text-only questions directly over graph text. Both pass without provider calls. Runner now executes them rather than skipping on the historical local-test comment. Latest direct results: implementation 110 passed/1 conflict failure; planning 78 passed/1 conflict failure. This is graph-text evidence, not provider enrichment evidence. Existing saved runs remain stale until rerun.
- Validation: 18 scoped tests pass; Ruff/mypy and frontend build pass. Source adapter parity test checks frozen normalized payloads against both actual translators; all eleven original evaluation questions pass unchanged.

- Bounded synthesis added using the existing configured model, job lifecycle and draft store: explicit provider consent, outline, operator decisions, generated events/checks, independent expectation review, and a separate saved variant. API regression verifies consent and review gates and that the prepared source remains unchanged. No new service, database table, queue or workflow framework. Real UI/model acceptance is in progress; this is not yet a completed M5 claim.

- M5 real-model/UI acceptance completed for one small PDLC variant using configured `gpt-5.2-2025-12-11`: operator brief → outline → decisions → generated proposal → independent expectation review → separate saved workspace → run → rerun. Six deliveries and 19 checks passed on both runs. Scenario: specification, requirement, design v1, v1 approval, superseding v2, malformed design without version; assertions include no approval transfer, rejection without graph mutation, history retrieval, and DesignElement-only evaluation. No expected result was changed after observing a run.
- Real exercise found and corrected two authoring defects: missing evaluation-contract guidance produced invalid proposals; a generated answer filter selected DesignElement while expecting DesignApproval too. Added explicit expected-field examples, final-graph question validation, evaluation filter consistency validation and safe actionable validation feedback. Operator independently corrected the question scope before execution. Changed local brief/decisions now prevent saving an outdated proposal. These findings mean schema-valid output still needs domain review; model generation is not guaranteed correct.
- Variant workspace: `fb12bf84-8fde-4b09-887b-65b57d3b194a` in the local operator database. Saved journey digest on both runs: `776e00bd92ada3754a5faa14da6640a6bccdbe6ef5962ae39d38861556ebcbcf`. Engine digest: `sha256:d6d1f3c6cf49cfacc061e5b1ec12ab9cd9270ec0062fb74fdcd83aa64a9556ec`. Exported local evidence: `output/workbench/pdlc/reviewed-variant.json`; screenshots `agent-variant-result.jpg`, `agent-variant-graph.jpg`, `agent-variant-narrow.jpg`. The baseline planning journey was not overwritten.
- UX check: graph labels use source titles/statements and visible revision numbers, with technical IDs in inspection details. Verified keyboard Enter selects the approval node. Narrow viewport inspection showed wrapped readable controls and no document horizontal overflow (354px client/scroll width); desktop viewport restored. This is a scoped usability check, not a complete accessibility audit.
- Latest targeted verification: 21 tests passed (`.venv/bin/pytest tests/unit/test_workbench.py tests/unit/test_workbench_journeys.py -q`); Ruff and mypy on workbench pass; standalone frontend type/build passes. Remaining before overall goal closure: reconcile the 144-site source assertion inventory against implemented checks and supplemental exclusions; migrate any uncovered ordinary journey semantics; refresh prepared UI runs on final engine; complete final evidence review. Do not call all PDLC journeys covered yet.

- Coverage-audit follow-up: added the original multi-reference and connected-path event payloads as a fourth prepared journey (13 executable checks passed, one direct-mutation group unsupported), strengthened release to 33 executable checks plus one supplemental group, and reran all current templates through the UI. 24 workbench tests and 34 selected original source tests pass. Completion review explicitly rejected blanket supplemental classification of 58 core retrieval sites: those are now labelled pending migration in both manifest and UI. Goal remains active; next step is one bounded graph-seeded retrieval scenario.

## Incremental verification — retrieval trust fixture (2026-10-31)

Completed one bounded graph-fixture slice using the existing runner, persistence and UI. The original retrieval test graph is frozen with 48 nodes and 54 relationships; its full core/memory/user/PDLC bundle and retrieval limits match the source test. It runs two unchanged trust expectations without event deliveries. The UI explicitly distinguishes graph retrieval from ingestion/extraction evidence.

Computer-use verification opened the current prepared fixture, clicked Run journey, and observed **2 passed, 0 failed, 0 unsupported, 0 errors**. The source disclosure confirmed all four frozen packs. Screenshot: `output/workbench/pdlc/retrieval-trust-ui.jpg`. The focused backend suite passes **26 tests** (`output/workbench/pdlc/workbench-tests-graph-fixture.txt`), including exact fixture parity, source registry version, bounded options, dangling-edge rejection, and preventing agent variants from bypassing ingestion with seeded graphs.

Current source accounting supersedes the earlier snapshot: 38 implemented assertion sites, 50 supplemental, and 56 pending migration, out of 144. Earlier event-journey run records remain historical and require refreshing after engine edits. Overall goal remains active; this is not full PDLC acceptance. Continue one source scenario at a time, reusing this path; add contract fields only when the next source assertion requires them. No new infrastructure, live activation, or ontology semantics change.

### Next incremental slice — file context and dependencies

Extended the same frozen retrieval workspace with three original queries: why `refund/retry.py` exists, preflight before editing it, and inbound dependencies of the ledger service. Source-authored node membership expectations remain unchanged; exact seed and inferred-intent metadata now participate in pass/fail. A regression test deliberately changes the expected seed while preserving answer membership and confirms failure. No model call, ontology change, or new infrastructure is involved. Previously saved workspace versions remain intact.

Computer-use verification ran the updated template and observed **5 passed, 0 failed, 0 unsupported, 0 errors**, including the two prior trust checks. Evidence: `output/workbench/pdlc/retrieval-context-ui.jpg`. Backend tests: **26 passed in 8.18s** (`workbench-tests-retrieval-context.txt`). Ruff, workbench mypy and standalone frontend build passed (`build-retrieval-context.txt`).

Source accounting is now **43 implemented, 50 supplemental, 51 pending migration** out of 144 assertion sites. Full PDLC acceptance remains incomplete; next migrate the remaining original graph-retrieval expectations, preserving exact answers, metadata and bounds.

### Completeness and design-history slice

The same frozen retrieval workspace now has 12 checks. Seven added queries preserve the source oracles for missing versus proposed test links, named requirement scope, superseded design status versus trace visibility, trust admission in completeness, and scopes derived from a shipped change or parent ticket. Exact answer sets and retrieval reasons participate in pass/fail. Separate negative tests prove that an extra returned node and a wrong reason each fail; expectations were not adapted to observed output.

Computer-use run: **12 passed, 0 failed, 0 unsupported, 0 errors**. Screenshot: `output/workbench/pdlc/retrieval-completeness-ui.jpg`. Workbench plus original retrieval tests: **52 passed in 7.98s** (`workbench-tests-completeness.txt`); subsequently added negative-oracle regression: **1 passed** (`retrieval-negative-oracles.txt`). Ruff and workbench mypy passed. No frontend implementation changed in this slice.

Current source accounting: **51 implemented, 50 supplemental, 43 pending migration** of 144 assertion sites. Goal remains active; remaining retrieval scenarios and final refreshed acceptance still need work.

### Query bounds, release scope and reference ranking

Added the original explicit-seed/depth/node-limit case, release-scoped review query and numbered-reference ranking query to the same saved fixture. Metadata subfields and first-seed expectations are compared without falsely requiring equality of unrelated fields. The bounds case preserves the source's unspecified truncation expectation (`truncated: null`); earlier checks retain their existing non-truncation default. No frozen ontology edits.

UI execution: **15 passed, 0 failed, 0 unsupported, 0 errors** (`output/workbench/pdlc/retrieval-bounds-ui.jpg`). Workbench and original retrieval suite: **53 passed in 8.22s** (`workbench-tests-bounds.txt`); subsequently added negative bounds/metadata regression: **1 passed** (`retrieval-bounds-negative.txt`). Ruff and mypy passed. Negative tests confirm wrong capacity, excessive node count and incorrect first seed fail.

Source accounting: **58 implemented, 50 supplemental, 36 pending migration** of 144 assertion sites. Goal is still active. Remaining work includes provenance/type assertions, multi-seed and paging behavior, fixture mutations, category evaluation and final acceptance refresh.

### Deployment provenance and traversal scope

Seven additional queries reuse the unchanged frozen graph: deployment tracing with producer provenance, artifact-only lookup, component-only ownership, no sibling changes through a shared release, no parent epic from a reached story, family traversal from an epic seed, and preservation of all twelve explicit seeds. Source expectations distinguish required, forbidden and exact type sets; type-filtered node sets; first deployment provenance; and required seed membership.

UI execution: **22 passed, 0 failed, 0 unsupported, 0 errors** (`output/workbench/pdlc/retrieval-provenance-ui.jpg`). Workbench and original retrieval suite: **54 passed in 8.41s** (`workbench-tests-provenance.txt`); subsequent negative-oracle regression: **1 passed** (`retrieval-provenance-negative.txt`). Wrong provenance, node types, sibling scope and missing seeds all fail as expected. Ruff and mypy passed.

Current source accounting: **72 implemented, 50 supplemental, 22 pending migration** of 144 sites. Remaining core work is graph variants/paging and category evaluation, followed by final acceptance refresh. Goal remains active.

### Isolated review, trust and precision variants

Added five separate frozen graph scenarios through the existing preparation API and runner: review verdict, untrusted self-corroboration, release-version precision, numbered-reference precision and rare-word ranking. A single retrieval scenario selector chooses among them. `scripts/engram_freeze_pdlc_retrieval_variants.py` reproduces their setups from the original test helpers with deterministic event identities; production execution reads only frozen JSON. The parity test compares the entire saved journey against the reproduced setup. These snapshots do not claim ingestion or mutation execution coverage.

Each variant was selected and executed through computer use: review verdict **1 passed**, trust corroboration **2 passed**, version precision **1 passed**, number precision **1 passed**, rare word **1 passed**. Screenshots are `output/workbench/pdlc/{review-verdict,trust-corroboration,version-precision,number-precision,rare-word}-ui.jpg`. All five use separate isolated graphs. Prior workspace versions remain intact.

Scoped workbench/source tests: **56 passed in 10.35s** (`workbench-tests-variants.txt`). Ruff, workbench mypy and frontend build passed (`build-variants.txt`). Current inventory: **81 implemented, 50 supplemental, 13 pending migration** of 144 sites. Remaining retrieval work: paging/cut behavior and category comparison, then final acceptance refresh. Operator copy in the variant descriptions still exposes source method names and should be simplified before final UX acceptance; source links belong in the disclosure. Goal remains active.

### Paging and truncation slice

Four additional selectable isolated graphs preserve source paging scenarios: 100 requirements with three confirmed tests each; proposed links with neighbor pages of one; 150 untested requirements with a 100-answer cap; and comparison of two-edge traversal pages against the source's normal 200-edge pages. The comparison runs both retrieval configurations on the same isolated graph, rather than copying the observed answer into expectations.

All four passed through computer use, one check each. Screenshots: `output/workbench/pdlc/paging-{complete,proposed,truncated,traversal}-ui.jpg`. Exact-count and truncation regression tests deliberately supply wrong expectations and verify failure. A failed first adapter run exposed an extra non-truncation assumption in the proposed-link case; its source only asserts the reason, so the fixture now explicitly leaves truncation unspecified. Explicit true/false expectations in the other source cases remain enforced.

Variant descriptions now use operator-facing text and retain source methods in the provenance disclosure. Progress text says running the scenario instead of falsely claiming event processing for graph fixtures. Scoped tests and source-parity results are in `workbench-tests-paging.txt`; negative checks in `retrieval-paging-negative.txt`; frontend build in `build-paging.txt`. Ruff, mypy and build passed.

Current source accounting: **90 implemented, 50 supplemental, 4 pending migration**. The remaining four assertion sites concern category evaluation versus a lexical baseline and query-work bounds. Full acceptance refresh and audit remain required; goal stays active.

### Category evaluation against the original baseline

Added a prepared nine-question benchmark using the original category answer selection, top-5-per-type text baseline, F1 definition and mean-category comparison. Runtime implementation reads saved questions and uses the frozen graph/registry; it does not import test code. An independent parity assertion compares its category report directly with the original source `evaluate()` result, and a deliberately wrong expected mean fails. Agent-authored variants cannot introduce benchmark checks.

The UI run passed and displayed category means: supersession **1.000 vs 0.533**, completeness **1.000 vs 0.167**, negation **1.000 vs 0.667** (PDLC vs text-only baseline). All nine original questions scored 1.0. The visible table and expandable questions expose expected, retrieved and baseline answer sets. Screenshot: `output/workbench/pdlc/category-evaluation-ui.jpg`.

Scoped tests: **58 passed in 12.18s** (`workbench-tests-benchmark.txt`). Ruff, mypy and frontend build passed (`build-benchmark.txt`). Inventory: **92 implemented, 50 supplemental, 2 pending migration**. The remaining two sites are query-work instrumentation/truncation; final acceptance refresh and review are still outstanding. Goal remains active.

### Query-work budget and completion-audit follow-up

The 400-reference query scenario now uses the original max_terms=16/max_graph_calls=50 limits and counts the same three graph operations as the source test. It verifies both the call ceiling and truncation; a zero-ceiling negative test fails. Instrumented methods are restored in a finally block. The UI run passed (`output/workbench/pdlc/query-budget-ui.jpg`). Scoped workbench/source suite: **58 passed in 12.13s** (`workbench-tests-budget.txt`); added negative-budget test: **1 passed** (`retrieval-budget-negative.txt`). Ruff, mypy and build passed (`build-budget.txt`).

The audit reopened two previously supplemental planning assertions: both required endpoints must remain, but a rejected REFINES edge must disappear from retrieval. An event-only limitation no longer justifies excluding them now that graph fixtures exist. They are pending migration, not silently certified. Current accounting: **94 implemented, 48 supplemental, 2 pending migration**. Final completion remains unproven until those checks and refreshed acceptance evidence are complete.
