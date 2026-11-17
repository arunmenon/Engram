# AI-native ontology onboarding: feature decision brief

Status: independently reviewed; revised scope below governs implementation planning.
No redesign implementation is claimed.
Prepared 2026-11-05. Repository HEAD at preparation: `27b4ba8`; working tree contains
extensive uncommitted changes. This brief does not authorize or claim implementation.

Execution plan: [milestones, objectives and acceptance evidence](ai-native-onboarding-milestone-plan.md).

## M0 verified corrections (2026-11-05)

Current executable probes supersede broader engine-limit statements below. With the
copied incident fixture and its supplied seed, evaluation with no explicit intent
passes, including after removing domain edges and intents. A named absent intent is
rejected. Thus relationship-based **intent eligibility** must not be described as a
ban on every relationship-free node lookup. This does not prove arbitrary questions
or scalar/count answers are supported. See `output/playwright/ai-native-onboarding/M0/baseline-20261105/capability-probes.json`.

Procurement synthetic intake files already exist under `docs/examples/procurement`;
a runnable pack and its acceptance evidence have not been verified by M0. Earlier
statements that procurement material does not exist are superseded by this inventory.


## Revised scope after independent review (2026-11-05)

Read the independent review in
`docs/review/2026-11-05-ai-native-onboarding-feature-review.md`.
This section supersedes the original feature priorities, four-activity organization,
and study-fixture assumptions below. The original proposal remains as review context,
not an additional implementation backlog.

### Decision

Build one grounded **explain-or-propose** capability. Asking about a pack element
(F1), resolving a decision (F2), and investigating a failed check (F6) use the same
server-assembled context and response contract. An explanation does not change the
pack; a proposed instruction enters the existing revision workflow only on explicit
operator action. Acceptance, validation and approval remain separate existing gates.

Keep the existing six-step sequence. Within ontology review, separate “What the
agent understood” from “Decide and accept”. Give trusted producers a clearly named
section outside question authoring, without adding a new top-level step. Align the
next-action banner with the same readiness item the operator sees in the checklist.
Explain the difference between running supplied examples and running a saved story.

First address the demonstrated problem: the successful live revision needed the
operator to name an engine admission rule. Operators should see what failed, its
business consequence, and supported choices without composing engine instructions.
Technical identifiers remain available under engineering details.

| Original feature | Revised disposition |
|---|---|
| F1 Ask this ontology | Keep narrowed; begin with validation problems and limitations. |
| F2 Decisions | Merge as a scope of F1; no recommendation badge. |
| F3 Intake | Later, source classification and deterministic sample inventory; derive missing-information guidance from actual validation. |
| F4 What-if branches | Defer until operator evidence justifies comparative execution. |
| F5 Stories | Deterministic coverage list in the existing story workspace. |
| F6 Failure investigation | Merge as a scope of F1; preserve deterministic failure guidance. |
| F7 Progress | Minimal honest stages and explicit cancellation; reuse existing jobs. |
| F8 Multimodal/voice | Remove from near-term scope. |
| F9 Source-change impact | Remove from near-term scope; retain existing stale-proposal protection. |

### First slice and acceptance

1. Assemble bounded context on the server for the authenticated tenant/draft and
   selected problem, limitation or element. Include relevant pack content, source
   excerpts, decisions and engine results; do not send unrelated tenant material.
2. Return a typed answer: `supported`, `unknown`, or `engine_limit`. Supported claims
   reference resolvable evidence. Unknown answers state what information is needed;
   they do not invent a rationale. Engine-limit answers reference the actual engine
   problem and offer only supported alternatives. Citation validation establishes
   traceability, not that the explanation is semantically correct.
3. Show the explanation beside its subject. An optional “Propose this change” action
   fills the existing revision request for operator review; asking never launches
   authoring or changes expectations, review acceptance, validation or approval.
4. Bind answers to tenant, draft, revision, proposal digest and scope. Any draft save
   invalidates the answer, including source edits; reject late responses. No context
   fingerprint or selective invalidation is needed in the first slice. Do not bump
   the revision merely to store an answer; transient answers may clear on reload.
   Refuse provider calls without current data-policy permission and apply the separate
   bounded explain capacity specified in the milestone plan.
5. Verify unchanged pack/review/evaluation state after read-only questions, tenant
   and draft separation, late responses, source edits, unsupported answers, provider
   failure and cancellation. The admission-rule repair example must be understandable
   without the operator supplying a technical rule name.

Use existing REST and typed React components. No new agent protocol, tools, renderer,
branching workspace or general-purpose chat surface is required.

### Subsequent small slices

- Add decision scope with consequences computed by the engine planner over reviewed
  samples. Label them “planned, not executed”; never present generated prose as a
  measured consequence. Unsupported comparisons remain explicitly unavailable.
- Add failed-check scope and a coverage list distinguishing defined, executed and
  passing checks. Preserve expected answers; proposed fixes identify reruns needed.
- Add thin intake assistance after observing the first slice with operators.

### Domain independence and honest limits

Replace the PDLC-only selectable-pack literal with a server-owned catalog of packs
that are actually loadable before claiming cross-domain selection. Preserve dependency
and composition validation. Derive examples from available contracts or omit them;
make lifecycle confirmation conditional on declared lifecycle behavior. Prepared
PDLC fixtures remain valid PDLC content. Do not silently default an authored domain
to PDLC when its snapshot is missing.

The review identifies real limits to explain rather than disguise: event-based
inputs, payload contracts for processed events, relationship-based artifact intents,
and expected answers represented as node-ID sets. Counts, scalar answers and
relationship-free retrieval must not be promised as supported. A relationship-free
conceptual pack may be inspected without claiming question readiness. Do not invent
relationships solely to pass an engine gate. The exact no-intent evaluation path
still needs a focused executable check before final capability wording is shipped.

Existing test material: prepared PDLC, Northstar incident material and the CRM pack.
Northstar is an incident example associated with payments, not proof of a payments
transaction ontology. CRM needs intake material and compatible contracts before UI
execution. Procurement, relationship-free and intentionally incomplete study fixtures
must be authored and reviewed; they are not existing coverage.

Use those fixtures to test the same components without domain-specific branches.
Include a wrong expected answer and an unsupported question, not just successful runs.
A human study must measure unassisted comprehension and wrong approvals. Automated
checks and a fluent agent response do not establish operator comprehension.

### Evidence status

The independent design review is complete. It did not reverify the previous 547-test
claim or live complete-v3 run, and this revision does not claim a fresh test run.
Implementation and operator validation of this revised scope remain pending. The
independent review and unrelated working-tree changes are untouched.

---

## Original proposal retained for review context

## 1. What we are trying to improve

Engram's workbench helps an internal operator configure a tenant's ontology pack:
the concepts, relationships, identities and processing/retrieval rules that turn
incoming events into useful graph context. An operator manages multiple tenants and
understands their business; we should not assume knowledge of YAML, graph identifiers,
retrieval intents, database administration or Engram's internal architecture.

Today, the agent can draft packs and stories, the engine validates and executes them,
and the operator reviews the results. The recent remediation strengthened safeguards.
It did not establish that humans find the experience understandable. More safeguards
now appear as more confirmations, technical details and separate screens.

The product goal is to move preparation and explanation to the agent while giving
operators clear business decisions. It is not to turn every interaction into chat,
make the agent autonomous by default, or choose a new framework for its own sake.

Domain independence means the same interaction works for PDLC, payments, procurement
and other supported ontologies. Names, examples, states and choices come from the
selected pack, its capabilities and tenant evidence. Domain-specific fixtures remain
valid test content; they must not become defaults in the generic authoring workflow.

## 2. Evidence and limits

The preceding assessment inspected the implementation and seven screens in actual
Chrome. Its screenshots/text are in `output/playwright/operator-usability-20261105/`.
Read `docs/review/2026-11-05-operator-flow-ai-native-review.md` for the stage-by-stage
findings and file locations. This was a heuristic assessment, not a study with novice
operators. Successful automated checks establish behavior, not comprehension.

Observed problems include:
- The ontology-review screen combines explanation, citations, assumptions, questions,
  confirmations, changes, removals and validation into a long page.
- Questions, answer scope, expected graph nodes and trust settings share one screen.
- Running supplied examples and creating a separate story workspace are distinct
  actions without a sufficiently clear operator-level distinction.
- A next-action banner can refer to confirmations as agent questions and direct users
  backwards while navigation invites them to continue.
- Existing-pack selection is PDLC-only, and generic starter content inserts an incident
  event. The underlying authored-pack/snapshot machinery is more generic than that UI.
- Real agent trials still require repair or clarification. The UI must make uncertainty
  and failure recoverable, not conceal them behind conversational confidence.

There is already useful substrate: versioned drafts, source quotations, decisions,
structural differences, real validation and sandbox results, entity pickers, composed
pack snapshots and per-check story acknowledgement. These should be reused.

The current authoring agent is a constrained, tool-free generation loop. Read-only
ontology conversation, branching what-if comparisons and automatic coverage planning
are not completed features. This brief proposes those capabilities explicitly.

## 3. Organizing the experience

Four operator activities, with one consistent context across them:

| Activity | Operator's question | Features that help |
|---|---|---|
| Describe the tenant | What do we need to understand, and what material can we use? | F3 assisted intake; F2 decisions |
| Understand and steer the ontology | Does this represent the business, and what should change? | F1 contextual questions; F2 decisions; later F4 comparisons |
| Test realistic situations | What should happen, what actually happened, and why did they differ? | F5 coverage/stories; F6 investigation |
| Review and hand off | What did we verify, what remains uncertain, and what am I approving? | F7 progress/history plus existing approval controls |

These are activities, not a requirement for four rigid pages or four new services.
Keep the ontology and selected object available while the operator changes activity.
Technical detail should remain accessible without being the primary reading path.

All examples below are illustrative product scenarios, not claims of implemented
payments/procurement integrations or existing source contracts.

## 4. Feature cards

### F1 — Ask this ontology

**Problem.** Operators can inspect a proposal but cannot have a grounded, read-only
conversation about a selected concept, relationship or rule without entering the
revision workflow.

**Trigger and experience.** Select an object in the graph or ask about the whole pack.
The agent answers in business language, identifies the exact pack revision and shows
supporting source excerpts or recorded decisions. An unsupported explanation must be
labelled as an assumption or unknown.

**Example.** “Why are these two supplier records separate?” The agent explains the
current identity rule, its evidence and a concrete example of distinct records.
“Merge them” opens a proposed change; it does not change the pack immediately.

**Existing / missing.** Graph, facts, sources and revision requests exist. Missing:
read-only question endpoint, bounded context selection, object-linked conversation,
and explicit separation between explanation and mutation. A server-supplied context
and a constrained response may suffice; a new agent orchestration framework is not
inherently required.

**Acceptance.** Asking leaves pack/review/evaluation digests unchanged. Answers cite
available evidence for the selected revision; absent evidence produces an explicit
unknown. Tenant A cannot retrieve tenant B's material. Reloading or switching drafts
cannot attach the response to another version.

**Risk.** A plausible explanation can misrepresent a valid quotation. Do not present
citations as proof of entailment or expose unsupported confidence percentages.

**Priority.** First proposed slice: high learning value and no need to automate writes.

### F2 — Decisions with consequences

**Problem.** Generic text questions and confirmations require operators to translate
engine concepts into business consequences, and repeat questions may create fatigue.

**Trigger and experience.** When evidence leaves a consequential choice unresolved,
present a focused card: the question, options, recommendation, supporting evidence,
and an example of the consequence. Include free text and “I don't know / request
more evidence”. Clearly distinguish a question from confirmation of an existing rule.

**Example.** “Can two business units use the same purchase-order number?” Show how
keeping units separate versus combining them changes the records in an example.

**Existing / missing.** Decisions, policy confirmations, changes and acceptance gates
exist. Missing: structured choice/consequence data and a renderer using a small,
application-controlled component catalog. Answers must refer to specific decisions,
pack revisions and affected elements.

**Acceptance.** A decision is asked only when relevant to the selected pack or goal.
Previously answered choices are not asked again unless their evidence changes.
Changing an answer proposes a revision and preserves the approval boundary. The UI
cannot fabricate an option unsupported by the backend.

**Risk.** Recommendations can bias reviewers; explain alternatives and uncertainty.
Do not collapse required approvals into one vague “looks good” action.

**Priority.** First phase alongside F1, initially for one common decision shape.

### F3 — Assisted intake and missing-information discovery

**Problem.** Operators must classify documents, understand source categories and
prepare technical payloads before seeing what the material enables.

**Trigger and experience.** After permission and upload, the agent proposes a source
inventory: what each item describes, candidate concepts, conflicting statements and
missing information. Ask for missing facts using their business impact. Let the
operator correct classifications before relying on them.

**Example.** “The policy permits partial refunds, but these sample events do not show
how a refund identifies its payment. Please supply that link or defer refund testing.”

**Existing / missing.** Text/Markdown/JSON upload, evidence fields and sample parsing
exist. Missing: structured intake analysis, contradiction handling and a clear
material-to-capability checklist. PDF/diagram ingestion is a separate later addition;
this feature must not imply those formats already work.

**Acceptance.** Classifications are editable and evidence-backed. The agent does not
invent fields because a document is incomplete. Consent applies before external
processing. The operator can begin a conceptual review without being told it is runnable.

**Risk.** Incorrect extraction or instructions embedded in documents. Sources remain
evidence, not authority to change the agent's permissions.

**Priority.** Next after the first review/decision slice, or move earlier if user testing
shows intake is the dominant blocker. This ordering is explicitly open for Fable.

### F4 — Compare what-if changes before applying them

**Problem.** A structural difference says what changed in a file, not necessarily what
will happen to business records or answers.

**Trigger and experience.** From a proposed identity, relationship or lifecycle change,
compare the existing and proposed rules using a small reviewed scenario. Show which
records or answers differ. Keep the proposal separate until explicitly applied.

**Example.** “What if a closed work item can reopen?” Show the existing and proposed
transition behavior on the same sequence, with the affected expectations identified.

**Existing / missing.** Pack differences and sandbox execution exist. Missing: isolated
comparison branches, same-input comparative execution, evidence binding to both
versions and a clear discard/apply path. Expected outcomes must not silently move
with the proposal.

**Acceptance.** A preview does not alter the active draft or accepted baseline.
Predictions are labelled separately from actual engine observations. Both versions
and data are identifiable; applying makes existing relevant results stale.

**Risk.** More execution cost and time; small examples are not a production migration
simulation. Show the preview's limits.

**Priority.** Later than F1/F2; validate that operators need executed comparisons before
building a general branching system.

### F5 — Coverage-guided story proposals

**Problem.** Operators may have an ontology and a few samples but not know which
important situations remain untested.

**Trigger and experience.** The agent proposes stories from the selected pack, business
questions, contracts and lifecycle rules. Each has a reason, sources and proposed
outcomes. Show supplied and generated stories in the same tenant workspace, while
retaining their distinct origins.

**Example.** “You tested a successful payment, but not a duplicate delivery or a refund
larger than the remaining amount.” Offer only cases supported by the domain contract;
absence of a refund contract is a missing capability, not permission to invent one.

**Existing / missing.** Authored-pack story snapshots, generated events/checks and
review gates exist. Missing: capability-derived coverage inventory, prioritization,
business-readable expectation cards and a unified operator path.

**Acceptance.** Every proposed story identifies its evidence and target behavior.
Generated negative checks use valid types and IDs. Each expected outcome is reviewed
before execution; observed output never automatically becomes the expected answer.
Coverage counts do not claim correctness or completeness of the business specification.

**Risk.** The same agent can invent both an interpretation and a matching oracle.
Source-backed human review remains necessary even when the tests pass.

**Priority.** After basic conversational review; reuse the current story infrastructure.

### F6 — Investigate a failure with the agent

**Problem.** A failed check may concern data, a mapping, lifecycle behavior, retrieval
scope or an incorrect expectation. Operators need a grounded explanation, not a generic
instruction to rewrite the pack.

**Trigger and experience.** Select a failed result. The agent inspects the exact event,
rule, expected outcome and observed output and explains what is known versus uncertain.
It proposes a targeted correction or requests missing evidence. Technical diagnostics
remain available to an engineer.

**Example.** “The second delivery created another record instead of reusing the first.”
Show the evidence for a key-mapping problem if present; otherwise explain what further
check would distinguish the causes.

**Existing / missing.** Result records and deterministic failure guidance exist.
Missing: failure-scoped context, grounded investigative conversation and a correction
proposal connected to the affected checks.

**Acceptance.** No expected result changes merely to make a run pass. A change creates
a reviewable revision and identifies what must rerun. When evidence does not establish
a cause, the agent says so. Question configuration and graph-writing failures stay distinct.

**Risk.** Confident misdiagnosis and circular test repair. Preserve original failures,
expectations and rerun history.

**Priority.** After F1; reuse its read-only context and proposal separation.

### F7 — Visible progress, interruptions and resumption

**Problem.** A spinner or attempt counter does not explain what completed, what is
waiting, or whether it is safe to leave. Failed or cancelled work needs a clear recovery path.

**Trigger and experience.** Show actual stages and outcomes: evidence available,
proposal returned, validation rejected/passed, decision needed, test running, result
ready. Keep the operator's input and last usable proposal intact. Show actions that
are valid for the current stage.

**Example.** “The proposal returned. Two contract checks failed. The agent is revising
those fields.” Only show this if the backend emitted those events.

**Existing / missing.** Persistent jobs, attempts, cancellation and recovery guards
exist. Missing: finer stage events, durable decision pauses/resumption where required,
and consistent guidance across tabs. Current cancellation is not a guarantee that
a later request resumes the same computation.

**Acceptance.** Every displayed stage is backed by a recorded event. Reconnection does
not duplicate writes or revive stale jobs. Approvals cannot be bypassed by streamed
updates. No invented percentages or private reasoning traces.

**Risk.** Infrastructure expansion before the operator flow is settled. Begin with the
existing job record and add only stages needed by the first slice.

**Priority.** Minimal progress honesty is foundational; advanced resumable orchestration
comes later if the existing mechanism cannot meet demonstrated needs.

## 5. Deferred opportunities

- F8: multimodal intake and optional voice. Requires document/diagram extraction,
  page/region citations, transcript confirmation, consent and accessibility. Voice
  must not be the only way to see or operate the interface.
- F9: source-change impact review. Requires source versioning and dependency tracking
  to identify affected concepts and tests. No automatic activation or cross-tenant
  reuse of confidential material.

Neither is required to prove the first interaction slice. Fable should challenge
whether either belongs on the near-term roadmap at all.

## 6. Foundations versus features

These are constraints on every feature, not separate AI products:

- Tenant and revision-bound context: sources, selected bundle, decisions, expectations
  and run results must be identified and isolated. Bound the context supplied to the
  agent; do not send every document by default.
- A server-owned catalog/capability contract: select actual supported packs, components,
  expressions and operations. Do not use a missing snapshot as a PDLC default.
- Explain / propose / apply are distinct. Asking is read-only; a proposal is not an
  approved mutation; applying does not activate a production tenant.
- Preserve existing server review gates while presenting their meaning more clearly.
- The agent may recommend review order. It cannot hide a required decision because it
  assigns itself high confidence.
- A supported ontology may lack lifecycle states or relationships. Do not force it
  into an incident-like workflow. When the engine cannot execute a requested question,
  explain the limitation rather than inventing a domain relationship.
- Stable application-controlled components, keyboard navigation, readable summaries
  and an accessible alternative to the graph are required.

## 7. Candidate technologies, not product commitments

Current primary references were checked during the preceding review:

| Pattern | Potential role | Decision still required |
|---|---|---|
| [A2UI catalogs](https://a2ui.org/concepts/catalogs/) | Declare the components an agent may request; validate their payloads. | Do existing typed React components suffice? Do not adopt a second renderer without a concrete benefit. |
| [AG-UI](https://docs.ag-ui.com/introduction) | Event/state connection between agent backend and interface. | Which needed features are actually implemented by the chosen adapter? The overview contains current and upcoming building blocks. |
| [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) | Optional review surface in supported conversational hosts. | Is another host a user requirement? This is not needed for Engram's own browser UI. |
| [Persisted interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | A reference pattern for pausing for human input and resuming with saved state. | Can the existing store/jobs meet the requirement before adopting another orchestration framework? |

A protocol's existence does not establish Engram compatibility or operator benefit.
These are implementation options; none is installed or selected by this brief. The
[agent engineering guidance](https://www.anthropic.com/research/building-effective-agents)
supports starting with simple patterns; our prioritization remains a product hypothesis.

## 8. Proposed sequence to challenge

1. Validate the current pain with a small operator task study; do not wait for a redesign
   to learn which decisions are confusing.
2. Build one complete, read-only F1 path: selected object → question → evidence-linked
   answer → clear option to propose a change. Include honest job status from F7.
3. Add one F2 decision shape and its apply/review path. Demonstrate it across different
   domains before introducing a catalog of many card types.
4. Expand based on observed bottlenecks: F3 if intake dominates; F5/F6 if story design
   and failed runs dominate. F4 should follow evidence that previews materially help.
5. Consider F8/F9 and protocol integrations only when the earlier slices demonstrate
   operator value and the additional capability is needed.

This is not a request to implement nine features at once. The proposed first slice
must work without a new agent framework, coding-agent conversion or arbitrary UI code.

## 9. How we will judge it

Use the same interaction against PDLC, a payments-related fixture and a procurement
fixture, plus a domain without lifecycle states and an incomplete-evidence case.
These are controlled acceptance fixtures, not a claim of live Concur integration.

A representative operator should be able to explain an entity's identity, find the
source for a relationship, ask a question without changing the pack, understand a
proposed change's consequence, reject an intentionally wrong expected outcome,
recover from a failed agent call and distinguish validation from handoff/activation.

Record unassisted task completion, help requests, wrong approvals, repeated questions,
recovery success and time spent interpreting controls. Compare with the captured
current flow. A shorter conversation or fewer clicks is not success if wrong approvals
increase. Do not assign invented usability scores or claim a human study has occurred.

## 10. Questions requiring an independent opinion

- Is F1 the best first slice, or does intake prevent operators from reaching it?
- Does the four-activity organization reduce work, or merely rearrange it?
- Which F1–F9 should we keep, change, defer or drop, and why?
- Are decisions easier to understand, or are we dressing up checkbox fatigue?
- Where should deterministic forms remain preferable to conversation?
- Are human expectations sufficiently independent from the agent's proposed ontology?
- Which assumptions are still specific to event-driven incident/PDLC examples?
- Are the context, revision, authority and failure boundaries implementable without
  unnecessary infrastructure? Is a protocol integration justified at all?
- What is the smallest cross-domain demonstration that would change the reviewer's mind?
