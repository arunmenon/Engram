# AI-native ontology onboarding: independent feature review

Reviewed 2026-11-05 on `feature/engram-walkthrough`, HEAD `27b4ba8`. Review only.
No code, pack, expectation, draft, database or earlier review was changed. No
provider, cloud or live-UI run was started. Code was consulted for feasibility; the
seven saved screens and the remediation evidence folders were read as data.

Working-tree note: 17 files listed in the review manifest have changed since the
remediation review (api, authoring, changes, job_errors, journey_authoring, models,
pool_config, spanner_pool, five frontend files, four test files). The brief and the
operator-flow review were written against the pre-fix tree. Differences that matter
to this review are called out where they apply; the main ones are that the accepted
pack is now persisted as the diff baseline, story checks need per-check acceptance,
seeds and answer type are no longer sent to the author, and negative story checks
are now type-checked.

## 1. Verdict

The direction is right: move preparation and explanation to the agent, keep the
engine as the only executor, keep deterministic gates, and let the operator decide
in business terms. The brief is honest about evidence limits. But it proposes too
much product for what the evidence supports, and it under-weights the one thing the
saved evidence shows most clearly: the successful live path still required the
operator to type engine vocabulary into the revision request.

The three most important changes to the proposal:

1. **Build one capability, not three features.** F1 (ask), F2 (decide) and F6
   (investigate a failure) are the same thing: a server-assembled, revision-bound
   context about a selected object, answered by a tool-free model call whose output is
   either an explanation with evidence links or a proposed revision request. Build the
   context assembly and the explain/propose split once; the three features are three
   entry points (selected pack element, open decision, failed check).
2. **Do not reorganize the flow into four activities yet.** The density problems in
   the seven screens are specific and fixable in place: the review screen mixes
   explanation, confirmations, changes and removals; trust sits under questions; the
   next-action banner contradicts navigation; two run paths are unexplained. Fix
   those inside the existing six-step sequence, then measure. A re-chunking that
   keeps the same content on fewer pages makes each page denser.
3. **Let the first slice remove the known engine-vocabulary leak.** The agent should
   answer "what is wrong and what are my options in business terms" for every
   validation problem, limitation and clarification the engine already produces.
   That is a read-only F1 answer type, it needs no new storage or protocol, and it is
   the only slice whose success can be measured against the captured flow today.

Drop F8 and F9 from the near-term roadmap, defer F4 until a comparison is requested
by an operator in a study, and fold F5 into the existing story workspace as a
coverage list rather than a new product surface. No protocol adoption is warranted
by any requirement in the brief.

## 2. Findings ordered by consequence

### N1. The successful live path depended on operator-authored engine instructions

- Source: `output/playwright/onboarding-fable-remediation-20261105/complete-v3/
  ui-authored.txt` lines 93 and 177; disposition "Live verification follow-up".
- The accepted revision request reads, in part: "Replace the invalid
  Sourced.trusted_producers admission rule with the supported untrusted_uncorroborated
  rule." The complete-v2 attempt failed engine validation on that invented rule; the
  fix was the operator naming the correct engine setting.
- Operator misunderstanding: the brief's target operator cannot write that sentence.
  The brief treats this as "real agent trials still require repair" (section 2); it
  is stronger than that. The agent's repair loop could not recover from an unknown
  admission-rule name even after being given the vocabulary, and the fallback was a
  human engineer in the operator's seat.
- Smallest correction: make engine problems the first content the agent explains.
  Each validation problem gets a business-language explanation and, where the
  engine's own vocabulary suffices (`ADMISSION_RULES`, scalar types, interface
  names), a proposed revision request the operator can accept without editing. This
  is F1 and F6 applied to the engine's own output, and it is the first slice.

### N2. F1, F2 and F6 are one capability presented as three products

- Source: brief section 4, F1 "Existing / missing", F2 "Existing / missing", F6
  "Existing / missing"; operator-flow review "No framework swap is required".
- Each lists the same missing pieces: a read-only endpoint, bounded context
  selection, object-linked conversation, separation of explanation from mutation. F2
  adds a typed option/consequence shape; F6 adds a failed-check scope.
- Engineering failure if built separately: three prompts, three context builders,
  three staleness rules, three UI panels, each with its own way of turning "do it"
  into a revision request.
- Smallest correction: one `explain` request with a `scope` (`pack`, `element
  <pointer>`, `decision <id>`, `check <id>`, `problem <index>`) and one response
  schema (answer text, evidence links into existing facts/sources/decisions, list of
  unknowns, optional proposed instruction text). "Propose" is the existing
  `content.instruction` plus `/author`; no new write path.

### N3. The four-activity flow re-chunks the same content

- Source: brief section 3; operator-flow review "Proposed shared experience".
- The activities map onto the existing steps 1–2, 3, 5, 6. The screens show the
  density is inside step 3 (`3.txt`: plain words, agent explanation, graph,
  evidence, limitations, questions, confirmations, changes, removals, validation) and
  step 4 (`5.txt`: questions, expected outcomes, graph expectations, trust). Moving
  step 4 into "Understand and steer" makes that activity larger, not smaller.
- Operator misunderstanding risk: a persistent "contextual agent" on every activity
  invites questions on screens where the answer requires state from another screen.
- Smallest correction: keep the stepper. Split step 3 into "What the agent
  understood" (plain words, graph, evidence, limitations, ask) and "Decide and
  accept" (questions, confirmations, changes, removals, validation, accept). Move
  trust to its own short step with one decision. Replace the global next-action
  banner with the readiness list's top item, worded the same way in both places.

### N4. The brief under-specifies what a read-only answer may say when evidence is absent

- Source: brief F1 "An unsupported explanation must be labelled as an assumption or
  unknown"; current `Fact.basis` has `inference`.
- With only a label, the model will write a confident paragraph and add
  "(assumption)". The current facts already do this (`live-author.json` self-edge
  rationale was labelled inference and was still wrong).
- Smallest correction: three response kinds, server-validated: `supported` (every
  sentence maps to at least one evidence link), `unknown` (the answer is a list of
  what evidence would settle it, no explanation prose), `engine_limit` (quotes the
  engine's problem text, explains the limit, offers scope change). Reject a response
  that mixes prose with zero links unless it is kind `unknown`.

### N5. Recommendations in F2 cards will be read as answers

- Source: brief F2 "options, recommendation, supporting evidence, and an example of
  the consequence"; risk paragraph acknowledges bias.
- The existing live run shows operators accept the agent's reading when it is
  fluent (`approved-parent.json` facts all accepted, zero rejected). A highlighted
  recommendation plus a worked example will raise acceptance of whichever option the
  model lists first, independent of evidence.
- Smallest correction: no "recommended" badge in the first version. Show the
  options with their evidence links and the concrete record-level consequence for
  each, derived from the engine's projection plan over the operator's own samples
  (which `validate` already computes per sample), not from model prose. Add a
  recommendation only if the study shows operators cannot choose without one.

### N6. "Consequence" examples must come from the planner, not the model

- Source: brief F2 example, F4 "Show which records or answers differ".
- `engine.validate` already returns, per sample, the planned nodes, edges and
  states for the current pack. A proposed pack can be planned the same way without
  execution. That is a deterministic, labelled "planned effect", distinct from a
  sandbox observation.
- Smallest correction: for identity and lifecycle decisions, render "with option A
  these two samples become one record; with option B they stay separate" from two
  `validate` runs over the samples. Label it "planned by the engine, not executed".
  This covers most of F4's value without branches or comparative sandbox runs.

### N7. Domain restrictions in code, not only in copy

- Source: `models.py:37` (`existing_packs: list[Literal["pdlc"]]`, max 1),
  `api.py:273` (`packs: ["pdlc"]`), `api.py:108-110` (identity and lifecycle
  confirmations always required), `journey_runner.py:47-58` (no snapshot means
  frozen PDLC), `example.pack.yaml` (incident syntax example), `Workbench.tsx:1119`
  (example event is an incident), placeholders at `Workbench.tsx:912,1100,1493,1501`,
  `OperatorFlow.tsx:224`.
- The repo has a CRM fixture pack (`tests/fixtures/packs/crm/`, Account and Contact
  without lifecycle, Deal with lifecycle, two edges, three intents) that cannot be
  selected in the workbench. No payments or procurement fixture exists; the brief's
  section 9 names fixtures that would have to be written.
- Smallest correction: replace the `Literal` with a server-owned catalog of loadable
  packs; derive the example event from the selected pack's first event contract, or
  omit it; make the lifecycle confirmation conditional on the pack declaring any
  lifecycle (the label already adapts, the requirement does not).

### N8. True engine constraints the brief should name as such

- Questions run only through intents that weight at least one edge declared by a
  non-core pack (`domain/pack_intents.py:61-67`). A pack with entities and no
  relationships cannot answer any evaluation question. The clarification handler
  now explains this; the brief's "pure catalog ontology" counterexample therefore
  cannot be tested end to end today, only authored and validated.
- Expected answers are sets of canonical node IDs (`Type:k1|k2`); questions whose
  answer is a value, a count or a property are not expressible
  (`sandbox.py:31-47`, `ontology/evaluation.py`).
- Ingestion is event-only; a catalog with no events is loaded by synthesising
  sample events. Every processed event needs a payload contract (`engine.py:94-96`).
- Lifecycle requires the `Lifecycled` interface and explicit transitions; producer
  trust is retrieval-side admission, never ingest rejection.
- These are legitimate limits. The product should say "this ontology can be
  described but not questioned until a relationship exists" rather than pressure the
  operator into inventing one, which the remediation now does.

### N9. The brief's F3 promises an analysis the model has already shown it cannot do reliably

- Source: brief F3 "candidate concepts, conflicting statements and missing
  information"; evidence `onboarding-improvements-*/missing-relationship.json`
  (placeholder edge, exhausted attempts, duplicate questions) and `incomplete-v2`
  (correct after two attempts, engine wording).
- Missing-information discovery before a proposal is exactly the step the model
  handled worst, because the engine's rejection is what makes the gap concrete.
- Smallest correction: derive the "what is missing" card from the engine's output
  after a first proposal (validation problems, clarification questions, limitations),
  not from a pre-proposal reading of the documents. Limit pre-proposal intake help
  to classification and to the deterministic sample inventory `evidence()` already
  computes.

### N10. Staleness rules for a conversation do not exist yet and are easy to get wrong

- Source: brief F1 acceptance "Reloading or switching drafts cannot attach the
  response to another version"; current records have no conversation store beyond
  `author_messages` (last 20, `api.py:691-699`).
- If answers are stored on the draft record, every `save` bumps the revision and a
  naive implementation would mark every answer stale or, worse, keep answers whose
  subject changed.
- Smallest correction: store each answer with `{draft_id, revision, proposal digest,
  scope}`; show it only while the digest of its scope's subject (pack element,
  decision text, check) is unchanged; otherwise show it collapsed as "from revision
  N". Do not attempt per-sentence invalidation.

### N11. The study design in section 9 names fixtures that do not exist

- Source: brief section 9 "PDLC, a payments-related fixture and a procurement
  fixture, plus a domain without lifecycle states".
- Only PDLC (prepared journeys), the Northstar/incident fixtures and the CRM test
  fixture exist. A procurement fixture, a lifecycle-free catalog fixture and an
  incomplete-evidence fixture with a known correct resolution must be written before
  any study. Section 6 of this review scopes them.

## 3. F1–F9 disposition

| ID | Decision | Rationale | Prerequisites | Operator-visible acceptance evidence |
|---|---|---|---|---|
| F1 Ask this ontology | **Keep, narrowed** | Highest value; addresses N1 directly when problems and limitations are askable scopes. | Server context builder; response schema with `supported`/`unknown`/`engine_limit`; staleness rule (N10). No new storage beyond a per-draft answer list. | Ask about a selected node, a limitation and a validation problem; pack, review and validation digests unchanged after each; each answer shows its links or an explicit unknown; switching drafts hides the answers. |
| F2 Decisions with consequences | **Change: merge into F1 as a scope** | Same context and prompt; the only new piece is a typed option list with planner-derived consequences (N5, N6). | F1; two `validate` runs per option over existing samples. | One identity decision shown with two options and the resulting record counts from the operator's own samples; choosing one creates a revision request; no "recommended" badge. |
| F3 Assisted intake | **Change: thin slice after F1** | Classification help is cheap; pre-proposal gap analysis is unreliable (N9). | F1 `engine_limit` answers; existing `evidence()`. | Upload three sources; the agent proposes categories the operator can change; after the first proposal, a "what is missing" list is derived from engine output and each item names the business impact. |
| F4 What-if comparison | **Defer** | Planner-derived consequences in F2 cover identity and lifecycle previews without branches (N6). Comparative sandbox runs double cost for unproven need. | Study evidence that operators ask for executed comparisons. | Not applicable until then. |
| F5 Coverage-guided stories | **Change: coverage list inside the existing story workspace** | Story generation, snapshots and per-check acceptance exist; the missing part is a deterministic inventory (events, transitions, rejection cases, questions) with "tested / untested". | Story workspace; inventory computed from the pack and existing checks, not by the model. | The workspace shows which event types, transitions and questions have a passing story; proposing a story for an untested item reuses the existing outline/generate/review path. |
| F6 Investigate a failure | **Change: merge into F1 as a scope** | A failed check is a context, not a product. The deterministic guidance in `results.ts` stays as the first line. | F1; check-scoped context (event, rule, expected, observed). | Select a failed check; the answer names what is known and unknown, never changes an expectation, and any proposed fix is a revision request naming the checks that must rerun. |
| F7 Progress and resumption | **Keep minimal** | Stage honesty is needed for F1 jobs too; the job record already carries attempts. Resumable orchestration is not needed. | None new; add stage names to the existing job record. | The job card lists stages that actually occurred (requested, attempt n, validation failed/passed, clarification needed); cancel shows a message in the authoring view. |
| F8 Multimodal and voice | **Drop from near-term** | No evidence any operator is blocked on PDFs or voice; extraction provenance is a separate product. | None. | Not applicable. |
| F9 Source-change impact | **Drop from near-term** | Requires source versioning the store lacks; the current "sources changed makes the proposal stale" rule is the correct coarse behaviour. | None. | Not applicable. |

## 4. Stage-by-stage domain-assumption audit

| Stage | Code restriction | Illustrative copy | Legitimate fixture | General engine constraint |
|---|---|---|---|---|
| Entry / tenant list | Prepared journeys endpoint is PDLC-only by name list (`api.py:289-308`). | "Software delivery (PDLC) has prepared stories" (`Workbench.tsx:598`). | PDLC fixtures under `workbench/fixtures/pdlc/`. | None. |
| Setup / pack selection | `existing_packs: Literal["pdlc"]`, max 1 (`models.py:37`); capabilities `packs: ["pdlc"]` (`api.py:273`). Roots limited to memory/user. | Scope placeholder about incidents (`Workbench.tsx:912`). | None. | Composition requires `core>=1.1`; pack names unique across the bundle. |
| Intake | Sample parser requires `event_type` + `payload` objects (`authoring.py:21-40`). | Source-name placeholder "Incident runbook"; example event is an incident (`Workbench.tsx:1100-1119`). | None. | Ingestion is event-only; every processed event needs a payload contract. |
| Authoring prompt | Syntax example is an incident pack (`example.pack.yaml`); prompt text names Sourced/Lifecycled. | Revision placeholder "repeated incident numbers" (`OperatorFlow.tsx:224`). | Syntax example is acceptable as syntax if clearly bounded; the live runs showed it was copied as domain evidence once. | Node PascalCase, edge UPPER_SNAKE, Lifecycled interface for lifecycle types. |
| Ontology review | Identity and lifecycle confirmations always required (`api.py:108-110`). | Lifecycle label adapts when no lifecycle exists (`OperatorFlow.tsx:306-308`). | None. | None. |
| Questions and expectations | Answers are node-ID sets; `node_type` filter; intent must be executable. | Question placeholders about incidents and postmortems (`Workbench.tsx:1493,1501`). | None. | Intents must weight a domain edge (`pack_intents.py:61-67`); artifact retrieval is edge-walking. |
| Trust | Trust is a producer-ID allowlist applied at projection and retrieval (`engine.py:82`, `sandbox.py:73-79`). | "Trust pagerduty in this test" is data-driven. | None. | Trust is retrieval admission, not ingest rejection; the engine has no envelope-conditional rule. |
| Testing and stories | Journeys without a snapshot resolve to frozen PDLC (`journey_runner.py:47-58`); draft stories derive dispositions from `expect_admitted`. | None found. | PDLC-only checks (`wrong_commit_links`, user-node absence) stay on the PDLC path. | Checkpoints are event indices; semantic dispositions not HTTP. |
| Approval and handoff | Export available before approval. | "Engine change class: initial" wording. | None. | Approval pins a digest; activation is outside the workbench. |

Metadata genuinely missing today for domain-independent content: a loadable-pack
catalog with descriptions; per-pack human labels for node and edge types (the UI
derives "Incident affects Service" from names); per-intent plain-language purpose
(exists as `description` and `examples` in the pack and could be surfaced); an
explicit per-pack statement of whether lifecycle and relationships are expected.
Everything else the UI needs already exists in the pack schema or the registry.

## 5. Recommended first slice and sequence

**Slice 1 (read-only explain, no new write path).**

- Server: a context builder that, for a draft and a scope, assembles the selected
  pack element (by JSON pointer), the facts that reference it, their citations, the
  decisions they cite, the relevant validation problems and limitations, and the
  sample projection plan for that element. Bound size to the element and its facts;
  never all sources.
- Server: one request type returning `supported` / `unknown` / `engine_limit` with
  evidence links validated the way `verify_proposal` validates citations, plus an
  optional proposed instruction text. Rejected responses are retried once, then
  surfaced as "the agent could not ground an answer".
- Server: answers stored on the draft with revision and subject digest; shown only
  while the subject is unchanged.
- UI: on the review screen, select a node, edge, limitation or validation problem;
  ask; see the answer under it; "Propose this change" copies the instruction into
  the existing revision box. Nothing else on the screen changes.
- Also in slice 1: split step 3 (N3), move trust to its own step, replace the global
  next-action banner, show cancelled-job status.

**Slice 2:** decision scope with planner-derived consequences (F2 merged), using two
`validate` runs over the operator's samples.

**Slice 3:** failed-check scope (F6 merged) and the coverage list in the story
workspace (F5 changed).

**Slice 4:** thin intake help (F3): category proposal and the engine-derived
"missing" list.

**Explicitly excluded from the first slice:** any new agent framework or protocol;
tools for the model; streaming; branching or comparative execution (F4); a component
catalog beyond the existing typed React components; conversation across tenants;
automatic application of any proposal; recommendations in decision cards; PDF,
diagram or voice input (F8); source versioning (F9); a four-activity navigation
rewrite; a general "chat with the agent" box.

## 6. Cross-domain operator study

Participants: three to five internal operators who manage tenants and have not used
the workbench. Each session uses one domain; rotate domains across participants.
Facilitator does not answer questions about Engram concepts; help requests are
recorded.

Fixtures (to be written before the study; none of these exist except where noted):

- PDLC: a prepared journey (exists).
- Incident: the Northstar synthetic set (exists).
- CRM: `tests/fixtures/packs/crm/` adapted into sources and samples (pack exists;
  intake material does not).
- Catalog without lifecycle or relationships: product and category records with no
  transitions; expected result is that questions are explained as not executable.
- Incomplete evidence: the incident set with the Service relationship removed from
  the specification; the correct outcome is a single clarification, not a pack.
- Wrong-answer fixture: any of the above with one expected answer deliberately
  pointing to the wrong account's record, and one generated story containing a
  `node_absent` check with an ID that could never exist.

Tasks:

1. Starting from the sources, obtain a proposal and explain in your own words how
   one entity is identified and where that rule comes from.
2. Ask the agent why a relationship exists. Then confirm the pack is unchanged
   (revision number and validation status).
3. Answer one identity decision and say what will happen to two specific sample
   records under each option before choosing.
4. Find and reject the deliberately wrong expected answer, and explain why it is
   wrong using the source material.
5. In the generated story, find the negative check that cannot fail and say why it
   proves nothing.
6. Trigger a failed agent call (the facilitator disconnects the provider) and
   continue to approval without re-entering any input or changing an expectation.
7. For the catalog domain, explain why the business question cannot be run and
   choose between deferring it and adding a relationship.
8. State the difference between validation passed, story passed, approved and
   activated.

Observations recorded per task: unassisted completion, number and content of help
requests, wrong approvals (accepting the wrong answer, acknowledging the vacuous
check, confirming a policy without reading), repeated questions to the agent, time
spent on the review screen before the first action, recovery success.

Stop or revise criteria: if two or more participants accept the wrong expected
answer in task 4, the expectation flow must change before any F1 work ships. If
participants cannot complete task 2 without help, the explain/propose split is not
visible enough. If task 7 ends with participants inventing a relationship, the
engine-limit answer type is failing. If the catalog domain requires any code branch,
the domain-independence claim is false.

## 7. Technology choices

Status below is from primary documentation and official repositories as of
2026-11-05, gathered by a delegated check; nothing was installed or run.

| Candidate | What it is | Release status | Needs a third-party host? | Authority model |
|---|---|---|---|---|
| A2UI (Google) | Declarative JSON UI from a client-owned component catalog, rendered by your own frontend. | Spec v0.9.1 current; v1.0 release candidate targeted Q4 2026; repository still labelled early public preview. React, Lit and Angular renderers published; Flutter/SwiftUI/Compose alpha or unpublished. | No. | None stated. Actions return to the agent as named events; the docs say nothing about server-side authorization of actions. |
| AG-UI (CopilotKit) | Event-stream protocol (text, tool calls, state snapshots and deltas, lifecycle) between an agent backend and your own app over HTTP+SSE or Protobuf. | Spec 1.0 released with normative rules; 1.1 is a draft no SDK implements. Python server SDK (`ag-ui-protocol`) and a plain `@ag-ui/client`; no React binding outside CopilotKit. | No. | Explicit: the application decides what runs, should obtain consent for side-effectful tool calls, must not represent an action as user-approved when it was not. |
| MCP Apps | MCP extension letting a server declare `ui://` HTML resources rendered by a host in a sandboxed iframe. | SEP-1865 Final; spec 2026-01-26 Stable. Hosts: Claude web and Desktop, VS Code Copilot, M365 Copilot, Goose, Postman and others. | Designed for third-party hosts; your own app can host via the app-bridge module at the cost of building a host. | Host-mediated; user approval for UI-initiated tool calls is permitted, not required. |

Assessment against the brief's actual requirements:

- **No requirement in the brief needs any of these.** The first slice is a request
  and response on an existing authenticated REST API with a revision fence. The
  existing typed React components are the "catalog". The existing job record is the
  progress channel. Polling every few seconds, which the UI already does, is adequate
  for a 30 to 250 second author job.
- **A2UI would add a second renderer and a schema-to-component mapping** for cards
  the application already renders from typed data. Its only benefit is letting the
  model choose component types; the brief's own foundations say the application
  should own layout and actions. Not warranted; revisit only if the catalog of card
  types grows beyond what hand-written components can hold.
- **AG-UI is the only candidate with a stated authority model,** and it matches the
  brief's "a streamed event grants no authority". It would be worth adopting only
  when streaming partial answers or interrupt-and-resume becomes a measured need.
  Even then, its state-delta semantics overlap with the revision fence and would need
  a rule for which wins. Defer until a study shows operators abandon waits.
- **MCP Apps is irrelevant** unless the product requirement becomes "review a pack
  inside Claude or VS Code". That requirement does not exist in the brief.
- **LangGraph interrupts** solve durable pause and resume; the workbench already
  pauses by returning a proposal and resuming on `/author`. Not needed.

Verification limit: these statements reflect the documentation read on the day;
roadmap items and host lists change. Nothing here establishes Engram compatibility.

## 8. Answers to the concrete challenges

- **F1 before F3?** F1 first, scoped so that engine problems, limitations and
  clarification questions are askable. The evidence shows operators reach the
  proposal; what stops them is interpreting what came back (N1). Intake
  classification is a three-way choice and is not the dominant blocker; incomplete
  evidence is discovered reliably only after the engine rejects something (N9).
- **No supporting source?** Return kind `unknown`: a list of what evidence would
  settle it and which existing decision could, with no explanatory prose (N4).
- **Consequences without implying execution?** Use the engine's projection planner
  over the operator's own samples and label it "planned, not executed"; reserve
  "observed" for sandbox results (N6).
- **Conflicting sources?** Record a decision whose options are the conflicting
  quotes, each linked to its source; the chosen quote becomes the fact's citation
  and the rejected one is kept on the decision. Never resolve by model preference.
- **Dense form to dense conversation?** Keep forms for data (sources, producers,
  expected entities); use the agent only on selection and only for explanation or a
  proposed instruction; no free-floating chat panel; one answer visible at a time
  under its subject (N3).
- **Pending answer when the pack or source changes?** Collapse it with its revision
  number; a proposal it generated is a revision request, which `save` already marks
  stale through existing rules (N10).
- **Domain-independent components?** Graph, entity picker, fact card, change list,
  readiness list, story check list and job card are already independent. Content
  needing pack metadata: human labels for types and edges, intent purposes, whether
  lifecycle and relationships are expected. Missing today: the pack catalog and the
  two expectation flags (section 4).
- **Must not build first:** everything in the exclusion list of section 5.

## 9. Open questions and what could not be verified

Product decisions needed:

- Is the target operator allowed to see engine vocabulary at all, or must every
  engine setting have a business label before it can appear in an answer?
- Should a pack with no relationships be approvable for handoff at all, given that
  no question can run against it?
- Who owns the pack catalog (names, versions, descriptions) that replaces the PDLC
  literal, and is multi-pack composition in scope for onboarding?
- Should operator answers to the agent be part of the approval evidence package?

Not verified in this review:

- Any human comprehension claim. All screens were read as saved text.
- Whether an evaluation question with no intent runs at all; the engine path was
  not exercised.
- The disposition's claim that 547 checks and the complete-v3 run passed; this
  review did not rerun them because the deliverable is a design review and the tree
  moved under it. The remediation review's probes were not repeated against the
  changed files.
- Technology status claims are limited to what the primary documentation states;
  see section 7.
