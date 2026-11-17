# Engram architecture and operator walkthrough video plan

Status: Revised after Claude review; rehearsal and storyboard approval pending. No recording or production implementation is authorized by this plan. Date: 2026-11-02.

Current execution update (2026-11-03): the shot-by-shot narration draft is
[`engram-video-narration.md`](engram-video-narration.md). Its rehearsal ledger records
fresh browser observations and remaining gates. The root-level legacy
`demo-video-script.md` describes an earlier presentation and is not used for this
walkthrough. Later Spanner evidence in `workbench-execution-goals.md` supersedes
historical resource blockers below; it does not establish completion of every
video rehearsal. Procurement remains separate and does not gate recording.

## Purpose and audience

Produce a professional narrated walkthrough for an internal operator seeing Engram for the first time. Assume no knowledge of ontologies, packs, graphs or tenant configuration. Start with why Engram exists and its design, then explain tenants, demonstrate agent-assisted ontology onboarding, and exercise the pack framework through journeys and evaluation.

The viewer should finish able to explain the event-to-answer flow, distinguish a tenant from a draft workspace, supply useful authoring evidence, review agent proposals, run tests and interpret their limits. Both ontology authoring and journey authoring are required; one must not substitute for the other.

Target: approximately 44 minutes, with independently navigable chapters. Duration is an estimate to validate during rehearsal, not a reason to omit requested features. Optional technical detail can be placed in chaptered appendices.

## Narrative and examples

Begin with a domain-agnostic explanation: why applications and agents need shared, explicit meaning across records; what an ontology contributes; and how a pack makes supported rules executable. Establish mandatory core, reusable engine mechanisms and optional memory/user add-ons before naming domain-specific entities. Follow a generic event through the architecture. Then introduce the two domain examples, including PDLC (product-development lifecycle), and its question “Was this requirement implemented, reviewed and tested?”

Then introduce a second customer need: “Which incidents affect checkout, and what happened to them?” Use a clearly labelled synthetic incident customer to demonstrate new ontology onboarding. Explain the transition: the domain changes, while the engine and authoring workflow remain shared. Return to prepared PDLC journeys for broader framework coverage.

Each scene follows purpose → visible action → observed result → meaning. Define technical terms before using them. Avoid a menu-by-menu tour without a customer objective.

## Chapters and screen story

| Chapter | Minutes | Screen and action | Learning outcome |
| --- | ---: | --- | --- |
| 1. Why Engram and ontology packs exist | 3 | Explain shared meaning across records, core, optional add-ons and domain extensions without starting from PDLC. | Understand why explicit, testable domain interpretation matters. |
| 2. Architecture basics | 5 | Use selected HTML study-guide diagrams. Follow one event through admission, ledger, processing, graph and retrieval; explain storage boundaries and evidence. | Explain what each component contributes and why ingestion and retrieval are separate. |
| 3. Ontologies and packs | 3 | Show a small PDLC model, then corresponding pack concepts: types, relationships, scoped keys, lifecycle, contracts, mappings and retrieval. | Distinguish the domain model from the engine configuration implementing it. |
| 4. Draft workspaces and the tenant boundary | 4 | Show workspace cards and Customer setup; compare drafts in separate tabs. Cut to a tenant-binding diagram. | Distinguish local drafts from runtime settings, credential grants, pinned bundles and tenant databases. |
| 5. Agent-assisted ontology onboarding | 8 | Create a draft, provide scope and evidence, request proposals, resolve a key decision, inspect sources and generated mappings. | Understand the operator's input and review responsibilities, and the agent's role. |
| 6. Test the authored model | 4 | Validate, review expected entities, run the sandbox, inspect graph and question results, then revise or hand off. | Separate proposed model, planned delta and observed stored graph. |
| 7. Exercise the pack framework | 6 | Run selected prepared PDLC scenarios covering implementation, planning/lifecycle, release/reference behavior and retrieval evaluation. Inspect a failure and unsupported boundaries. | Evaluate more than the happy path, and understand what each run establishes. |
| 7b. Pack lifecycle from the terminal | 5 | Rehearsed status, change classification/version bumps, evaluation registration and pending/ready API responses; rebuild on disposable targets if feasible. | Explain lifecycle capabilities absent from the workbench. |
| 8. Agent-assisted journey authoring | 4 | Brief → outline → decisions → generated events and expected outcomes → review → save a separate variant → run. | Expand coverage without silently changing the baseline or generating expectations from observed results. |
| 9. Review and handoff | 3 | Review evidence, artifact identity, stale results and operational limits. Recap the complete workflow. | Know what is ready for handoff and what still requires runtime verification. |

## Architecture opening

Use `docs/research/2026-10/walkthrough.html`, titled “Engram Packs and Spanner,” as the candidate study guide. Confirm that it is the intended guide and reconcile historical content before recording. Select the big picture, common/domain pack relationship, pack declarations, ingestion and retrieval sections. Spanner is an implementation/storage explanation, not evidence that the demonstrated local sandbox runs on Spanner.

Introduce an event as a report of something that happened; a ledger as the retained event record; a graph as entities and their relationships; projection as translating event fields into graph updates; and retrieval as selecting relevant evidence to answer a question. Explain identity and provenance with the same example. Show an explicit boundary between the admin workbench and the runtime.

Do not imply every question triggers a language model or every uploaded document becomes runtime data. Explain actual supported paths after code verification.

## Tenant configuration story

Show a comparison of the configurations actually available in the demo: purpose, environment label, selected pack/bundle, evidence sources, identity choices, trust assumptions, questions and readiness. A saved workspace card is not proof of a deployed tenant or a dedicated database.

Use an architecture view to explain authenticated tenant routing, tenant-bound configuration and database boundaries where the UI cannot show them. Confirm these against runtime construction and the tenant runbook. Do not infer deployed isolation from a successful local workspace run.

If selecting roots/dependencies, provisioning, activation or live credential grants lacks a UI control, label that boundary explicitly; do not stage a nonfunctional control or imply the flow exists. Keep activation success separate from intent readiness: a newly activated tenant may need data before target-graph evaluation can pass.

## Concrete onboarding demonstration

Prepare a compact synthetic customer evidence bundle before rehearsal:

- A process specification and glossary for checkout incidents, including scope and exclusions.
- A JSON event schema with producer identity and documented field semantics.
- Representative open, update and resolve events, missing-title behavior and the same local incident number in two accounts.
- Identity, lifecycle and trust decisions, including explicit expected effects.
- Questions with independently reviewed expected entities and graph outcomes.

All synthetic materials must be labelled. Samples suggest field patterns but do not prove global uniqueness or a complete source contract.

The recorded sequence:

1. Create a tenant draft and explain what has and has not been created.
2. Define purpose/exclusions and review data handling before a model call.
3. Upload the process specification; inspect its place in the evidence inventory.
4. Add schema and sample events; explain why these supply executable grounding that prose lacks.
5. Ask the agent for a proposal. Show source references, inferences and open decisions using supported UI behavior.
6. Resolve “Can incident 42 exist in two accounts?” Show the effect on identity. Explain absent versus null fields and lifecycle decisions where supported.
7. Inspect proposed types, relationships, contracts and mappings. Follow one event into its planned graph change.
8. Define a customer question and select understandable expected entities; expose technical identifiers only as optional detail. Do not assume a usable entity picker exists without checking it.
9. Validate, review expected outcomes before running, execute in the sandbox and compare observed results.
10. Show how changed inputs make previous evidence stale, then explain review and handoff.

Model generation must use the real configured provider when presented as agentic execution. If a previously saved run is shown, label it as recorded history. Preserve generation failures and review corrections where they explain operator responsibilities. Approval is never inferred from an agent's confidence.

## Feature coverage and recording inventory

Before scripting, inventory the current UI and create a shot checklist. For every feature, record its current screen/control, prerequisite, action, observable outcome and status: demonstrable in UI, backend-only, proposed, or unavailable. This prevents the phrase “all features” from silently omitting features or claiming planned ones are built.

Required inventory areas:

- Tenant draft creation, configuration, persistence and owner scope.
- Evidence uploads, data handling, source references and operator decisions.
- Agent proposal lifecycle, validation, failure feedback and review.
- Types, relationships, identity, contracts, mappings and lifecycle behavior.
- Pack composition/dependencies and change classification where supported.
- Questions, expected entity selection, trust, retrieval and evaluation.
- Saved event journeys, graph-seeded retrieval fixtures and their different evidence boundaries.
- Timeline, observed graph, check details, failure filtering and result inspection.
- Assistant-authored journey variants and preserved baselines.
- Stale results, cancellation, review and handoff/export where supported.

Cover each demonstrable feature in a main chapter or short appendix. Consolidate repetitive actions; do not remove meaningful capability coverage to meet the duration estimate. Explain backend-only capabilities without presenting them as live UI features.

## Evidence and known limits

Source references for review:

- `docs/tenant-admin-workbench-plan.md` — intended onboarding design; not proof all planned controls exist.
- `docs/pdlc-journey-workbench-plan.md` — journey implementation and recorded completion audit.
- `docs/runbooks/tenant-api.md` — runtime tenant operation guidance.
- `demo/frontend/src/workbench/` — actual screens and controls.
- `src/context_graph/workbench/` — authoring, sandbox and persistence behavior.
- `output/workbench/pdlc/acceptance-verification.json` — prior local acceptance record, to be inspected and dated before reuse.

The journey plan records four event scenarios, thirteen retrieval scenarios and a reviewed assistant variant. Its prior acceptance summary retains two conflicting-retry failures and one unsupported group. These are historical results, not a fresh recording-session run. Recheck current artifacts and behavior before stating counts in narration.

Graph-seeded retrieval tests do not establish ingestion behavior. Local memory-backend runs do not establish deployed networking, live Spanner isolation, worker rollout or activation-race behavior. Small fixed-fixture evaluation scores are regression evidence, not broad retrieval-quality claims. Runtime evaluation gating must not be conflated with a passing sandbox question.

## Production approach

Use readable 1080p or higher capture, deliberate cursor movement, chapter cards, selective highlights, captions and a transcript. Narration should be conversational at approximately 130–145 words per minute, with room for reading and observing results. Avoid music during technical explanation.

Record short scenes so failures can be explained without forcing a continuous performance. Label shortened waits and illustrative animations. Do not substitute fabricated results for real UI output. Keep tokens, unrelated tabs, customer data and credentials out of capture. Use a clean demo workspace without deleting existing records.

Recording, editing and voice-over tooling remain to be selected and verified. Do not promise a specific voice or export format until tools are confirmed. Target deliverables are a chaptered video, captions, transcript and supporting exercise files.

## Execution and approval gates

1. Obtain review of this plan and reconcile findings.
2. Verify guide accuracy and complete the current feature/shot inventory through source inspection and computer use.
3. Prepare synthetic inputs and complete real-provider ontology onboarding and journey-authoring UI rehearsals. Rehearse the CLI/API lifecycle with a shared persistent local backend. Save inputs, decisions, model metadata, outputs and failures. Fixture-author evidence does not satisfy this gate.
4. Draft the complete narration and shot-by-shot storyboard, including exact transitions, evidence and failure explanations. Obtain user review before recording.
5. Capture a reproducible source snapshot before any take: prefer a reviewed commit, or preserve an exact archive/manifest including untracked workbench files, dependencies and sanitized run configuration. A Git tag on HEAD alone does not capture untracked files. Do not bulk-commit unrelated changes. Verify production tooling and produce a short opening sample for approval.
6. Record and edit the approved story; add captions and chapter navigation.
7. Check factual accuracy, readable text, voice/screen synchronization, secret redaction and feature coverage. Deliver video and companion artifacts with any unresolved limitations.

This task does not authorize deployment, cloud provisioning, changes to the PDLC ontology or changes to test expectations for cosmetic success. Product gaps found during rehearsal should be recorded and scoped separately before implementation.

## Questions for the reviewer

Does the opening teach enough architecture before configuration? Is the transition between PDLC and incident onboarding clear? Are tenant configuration and workspace state distinguished accurately? Are both agentic workflows concrete and grounded? Does coverage match current code without suggesting planned controls exist? Are the expected-answer review and failure story credible? Is the 44-minute structure usable, or should it be delivered as a chaptered series with the same coverage?

## Recording contracts after review

These specific scene constraints govern the chapter summaries above.

### Workspace and runtime boundary

The workbench stores local SQLite drafts. Environment is a free-text label, not provisioning. Customer setup exposes optional memory/user root checkboxes; core is required and PDLC is the only selectable existing domain pack. Trust controls are under Expected results. There is no side-by-side comparison screen: use two tabs. Runtime status pills are placeholders and the workbench cannot activate or provision tenants.

The tenant diagram shows a binding of settings, engine revision, pack identity and trust policy, with server-owned credential grants and isolated storage. The public dispatcher factory is enabled in current code and verifies startup; this is not evidence of deployment. Its catalog is fixed per process, and changes require coordinated drain/restart. The stale opening comment in `tenancy.py` must not override `api/tenants.py:create_tenant_app` and the tenant API runbook.

### Real-model onboarding rehearsal

Claude's review reports that prior pack-authoring UI acceptance used the fixture author, while a real-model incident pilot was unapproved at mean F1 0.65 against 1.0. A complete real-provider browser rehearsal is therefore mandatory before scripting its outcome. Record and diagnose failures without changing expectations to fit output. Establish whether account identity caused the failure before narrating that explanation.

Exit this rehearsal with a complete run, independently reviewed expectations and a decision to show either correction-to-success or an explicit unresolved failure. An unapproved artifact cannot be presented as approved. Freeze the resulting synthetic evidence bundle. Bound retries operationally, and label shortened model waits; real jobs can take several minutes.

### Exact onboarding shots

- Upload Markdown/text process specifications and JSON schemas/events. Current inputs accept txt/md/json, not PDF; limits are 160 KB per upload, 40,000 characters per source, 20 sources and 100 sample events.
- Identity decisions use free-text answers. Read the repeated incident number in two accounts, answer, select Apply my changes, wait for re-authoring, then show the resulting type key and planned node ID. There is no automatic before/after decision visualization. Budget a model call for this scene.
- Technical inspection is an expander inside Proposed model, not a separate navigation step. Schema and observed graphs are on different steps.
- The sandbox is an isolated in-memory run of the real admission, ledger, projection and retrieval pipeline. Planned writes and stored graph snapshots are separate views, not a computed diff. The verdict checks question F1, missing expected nodes and forbidden nodes.
- The graph drawing shows at most 12 nodes; choose small scenes or use complete node/edge tables. Expected entities have readable picker labels and optional advanced identifiers. Tenant Test shows F1 numbers; journey checks show pass/fail.
- Saved journey variants return to their own draft. Use All tenants to revisit the preserved baseline. Current journeys are PDLC-specific; incident pack authoring and sandboxing do not establish incident journey support.

### Terminal lifecycle rehearsal

Use disposable local data and a persistent backend shared by CLI and API. Separate memory processes cannot demonstrate evaluation registration and subsequent serving. Verify supported commands and prerequisites before writing command narration; no cloud provisioning is part of this plan.

Show ontology status/inspection, initial/additive/mapping/breaking classification and required version bumps. Explain worker hot/replay/refuse behavior. Demonstrate an intent pending response, evaluation recording, then query readiness with actual refresh/TTL conditions. Rebuild must target separate disposable storage and be rehearsed before capture. Do not edit frozen PDLC or existing tenant data.

Include strict properties, processing bindings, extraction boundaries and inert declarations through inspected YAML/code or labelled diagrams where live execution is impractical. Review currently classifies against no prior registry and shows initial; it is not an upgrade diff. If shared-backend or rebuild rehearsal fails, report the blocked scene and revise its presentation for review rather than fabricating or silently omitting it.

### Guide, evidence and recording limits

The HTML guide describes an October 6 state. Restrict initial selections to the big-picture, common-layer, ingestion and retrieval diagrams and verify their labels. Reconcile optional roots, PDLC counts, tenant trust, contracts, processing bindings, value-language limits and Spanner history before capture. Do not quote stale pack-authoring runbook counts.

The October 31 acceptance record, as inspected by Claude on November 2, reports 288 passed checks, 2 failed and 1 unsupported across 18 workspaces. Claude reports a fresh November 2 run of the two workbench test files with 34 passing tests. This differs from the historical wider 68-test selection; neither was rerun as part of this plan revision. Date any quoted evidence.

Before handoff, include a short limits card: no workbench provisioning/activation, in-memory sandbox, txt/md/json inputs, PDLC-only journeys and initial-only Review classification. Use local-operator, keep devtools closed, inspect raw errors before capture, and retain artifact digests where they explain reproducibility.

## Review disposition

Review source: `docs/review/2026-11-02-video-walkthrough-review.md`.

- B1 accepted for workspace/runtime separation. Two factual corrections: the public dispatcher factory is enabled, and memory/user roots have selectable checkboxes. Verified against current source; no deployment or UI activation is inferred.
- B2 accepted: real-provider browser rehearsal is a hard prerequisite with explicit failure handling.
- B3 accepted: terminal lifecycle chapter added, with persistent-backend rehearsal required. Exact commands and successful outcomes remain unverified.
- B4 accepted in purpose: require reproducible source capture before recording. A tag alone does not preserve untracked code. No commit or tag was created during this revision.
- C1–C9 incorporated in the recording contracts: dated evidence, in-memory terminology, separate graph views, re-authoring decisions, upload limits, navigation, guide drift, PDLC-only journeys and exposure controls.
- Retain the duplicate/conflict and release-unsupported scenes. Introduce PDLC only after the domain-agnostic opening and explicitly introduce incident onboarding as a second domain. This supersedes the earlier PDLC-first ordering on user instruction.

This revision changes the plan only. Browser rehearsal, fresh tests, study-guide corrections and recording remain outstanding.


## Workbench usability implementation alignment

The operator-copy and behavior specification is `docs/workbench-storyboard.md`, including its accuracy corrections and implementation evidence. Use the implemented customer/pack/story labels and six main steps plus optional 3b technical inspection when drafting shots. Answer results use mean F1, not percentage of questions passed. Pending answers and proposed data removals require explicit review before testing/approval. The browser verified readable PDLC failure explanations, recovery, two-tab conflicts and resume. Real-provider incident authoring, explicit review, example replay and handoff completed; the final refreshed-engine run scored mean F1 1.0 against 0.8 with the malformed event rejected. Preserve the known PDLC duplicate/conflict failure in narration. Evidence and the scoped completion audit are in storyboard section 16; this is not production or Spanner evidence. These UI changes do not add Spanner sandbox pooling or activation.

### Spanner follow-on recording gate — 2026-11-03

Goal 2 adds local pool configuration, capacity/cleanup UI and real-adapter runner wiring. This supersedes the earlier statement that no pooling source exists, but does not establish a demonstrated Spanner run. Latest browser PDLC evidence is revision 12, isolated-memory, 110 passed and one preserved duplicate/conflict failure (`output/workbench/usability/pdlc-storage-regression.json`). The incident historical memory evidence becomes stale when the engine changes and the UI requests revalidation. Dedicated resource capacity and ADC remain unresolved. Use the sandbox runbook and execution-goal audit; capture Spanner-labelled shots only after live acceptance and preserve the script-review gate before recording.
