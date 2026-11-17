# Operator flow review: domain independence and AI-native interaction

## Verdict and evidence

The current workbench is safer than the earlier version, but remains too dense for an
operator who knows the tenant's business and does not know Engram internals. It is
partly generic, not yet consistently ontology-agnostic. A chat panel alone would not
resolve this: the workflow must move preparation to the agent and expose meaningful
business decisions to the operator.

This is a source-grounded heuristic review, not a human usability study. Seven screens
of the saved Northstar verification draft were opened in actual Chrome, without
changing draft content or invoking the agent. Text and screenshots are saved under
`output/playwright/operator-usability-20261105/`. Generated ontology and story evidence
from the preceding remediation was also inspected. The test successes in that work
establish behaviors, not human comprehension.

This document proposes product changes. No redesign or protocol integration was
implemented as part of this review. Older implementation/review records remain intact.

## Findings across the journey

| Stage | What is difficult or coupled today | Human decision to preserve | Proposed agent-led interaction |
|---|---|---|---|
| Entry and tenant setup | Prepared stories emphasize PDLC; environment and scope arrive before a clear end-to-end outcome. Sandbox capacity occupies space on every screen. | Which tenant, goal, boundaries and permitted data use? | Start with the tenant goal and desired questions. Show one recommended next action. Show capacity when testing is relevant. Keep data-use consent explicit. |
| Selecting packs | `Content.existing_packs` only permits pdlc; capabilities returns pdlc; frontend offers a PDLC checkbox. Roots are separately defined. | Which capabilities should this tenant use? | Select from a server-owned catalog with descriptions, versions and compatibility. The agent may recommend from available options, never invent an installed pack. |
| Intake | Operator classifies process docs, JSON schemas and samples; adding a file requires preview, classification and explicit save. PDF is unsupported. Many placeholders and the actual insert-example action use incidents. | Is this the right source, can it be used, and which conflicting statement is authoritative? | Agent proposes source classifications and a readable extracted inventory; operator can correct it. Explain what is usable, what is missing and why it matters. Derive sample templates from selected contracts, or request a contract before supplying an executable template. |
| Ontology review | Diagram, facts, assumptions, confirmations, agent questions, diffs, removals and validation appear on one long page. Some generic confirmations show under “Answer the agent’s questions” even when there are no questions. | Does the ontology represent the business correctly? What ambiguity needs a domain decision? | One shared ontology canvas with a contextual conversation. Select an entity/relationship, ask why or what-if, and see evidence and sample consequences. Separate explain, propose and apply. |
| Questions and expected outcomes | One screen contains business questions, answer candidates, starting points, expected graph nodes and trusted producers. Operators must understand retrieval choices to configure them correctly. | What answer should this example produce, and why? Which producer evidence is trusted? | Collect business expectations early. Agent proposes an executable question configuration with an explanation; operator reviews the meaning. Keep graph/assertion detail available, not compulsory as raw IDs. Trust gets its own contextual decision rather than an unrelated checkbox at the bottom. |
| Testing and stories | “Run examples” and “Create a story workspace” introduce two paths without explaining the distinction in operator terms. Generated checks still expose JSON; per-check review now adds visible effort. | Are these realistic stories and correct expected outcomes? Are observed results acceptable? | A story shelf in the same tenant workspace: supplied examples and proposed new stories. Each story shows business intent, expected events/outcomes, then observed results. Preserve per-check acknowledgement, expressed as readable outcomes with details available. |
| Approval and handoff | Engine classification, bundle versions and artifact identity precede the practical handoff. The disabled footer “Complete” does not express readiness. | Is this exact tested version ready to hand off, and what remains unresolved? | Show “Ready for handoff” only when gates pass; summarize covered questions, failures, remaining uncertainty and the downloadable package. Clearly state activation is unavailable here and name the next responsible role. |

Cross-cutting issue: the global next-action banner can point backwards while the footer
invites continuation. It also uses “below” on screens where the referenced control is
elsewhere. Navigation and readiness should share a coherent explanation of the next
meaningful action; visiting a screen must not imply completing its requirements.

## Where domain assumptions exist

Verified implementation locations:

- `src/context_graph/workbench/models.py`: `existing_packs: list[Literal["pdlc"]]`,
  max one. This is a real selection/composition surface restriction, not just copy.
- `src/context_graph/workbench/api.py`: capabilities advertises `packs: ["pdlc"]`.
- `demo/frontend/src/workbench/Workbench.tsx`: PDLC selection and prepared-story
  presentation; incident-only sample insertion and several incident-specific prompts.
- `src/context_graph/workbench/authoring.py` and `example.pack.yaml`: fixed Incident /
  Service / AFFECTS syntax examples. Prior live runs showed these could be copied as
  supposed domain evidence. A syntax reference needs an explicit boundary and should
  be selected/generated without becoming authority about the tenant's world.
- `journey_authoring.py` and `journey_runner.py`: explicit authored-pack snapshots
  already exist, but the path without a snapshot defaults to frozen PDLC. Distinguish
  an intentionally prepared PDLC story from a missing domain context; do not silently
  treat the latter as PDLC.
- `OperatorFlow.tsx` and API readiness: identity and lifecycle confirmations are always
  required. Identity matters generally; lifecycle should explain applicability using
  actual pack capabilities, including domains without lifecycle transitions.

Generic foundations worth preserving: registry-based pack composition, schema-driven
graph rendering, entity selection from pack keys, immutable composed-pack story
snapshots, and the same engine for validating authored packs. Domain-specific fixtures
are legitimate test content; they should not define the general UI or default semantics.

Also distinguish a domain assumption from an engine constraint. The current artifact
intent path needs domain edges. A domain with no evidenced relationship must not be
pressured to invent one merely to satisfy the engine. Explain the capability limit,
offer a conceptual-only draft or a deliberate scope change, and keep engineering
requirements separate from business clarification.

## Proposed shared experience

Four stages, with one contextual agent available throughout:

1. Describe this tenant: business goal, questions, scope, sources and permission.
2. Review the ontology: readable summary and graph, evidence, unresolved choices;
   ask questions and steer a proposed revision.
3. Try stories: review business outcomes, execute in isolation, compare observed
   results and investigate differences.
4. Review and hand off: approve the exact version and evidence package.

The graph is a persistent working artifact, not an illustration abandoned after one
step. The conversation is bound to a tenant, pack revision and selected object. Plain
questions are read-only. Proposed edits carry a before/after difference and affected
stories. Applying creates a new revision and invalidates only the evidence whose
subject changed, using server-enforced rules. Earlier approved versions remain available.

## AI-native features to prioritize

| Priority | Feature | Concrete operator benefit | Existing foundation / missing capability |
|---|---|---|---|
| First | Ask this ontology | “Why does this entity exist?”, “Where is this relationship supported?”, “Can this record reopen?” answered against the selected version and object. | Existing graph and facts; needs a read-only conversational endpoint and object-scoped evidence retrieval. Current author endpoint is a revision workflow, not this capability. |
| First | Decision cards chosen by the agent | A choice, recommendation, supporting source, and one example of each consequence; answer in business language. | Decisions exist; needs typed choices/effects and a component catalog. Keep free text and “I don’t know / request evidence”. |
| First | Assisted intake | Classify uploaded material, extract candidate concepts and missing contracts, highlight contradictions before asking for more. | Uploads and citations exist; needs a structured intake-analysis result and support for additional document types if promised. |
| Next | What-if preview | Compare two identity choices or a lifecycle change on a small example before applying either. | Diffs and sandbox exist; needs isolated proposal branches and comparative runs with version-bound results. Never describe an imagined graph as an observed result. |
| Next | Coverage-guided story proposals | Suggest untested event types, transitions, missing-field cases and business questions from the actual pack and goals. | Story authoring and checks exist; needs a coverage map and a grounded reason for each proposed test. Expected outcomes remain independently reviewed. |
| Next | Agent-guided failure investigation | Explain which event, rule or question configuration caused a mismatch and propose a targeted change. | Real results and guidance exist; needs scoped investigation and proposed correction artifacts. Never rewrite the expected answer merely to make a test pass. |
| Next | Visible, resumable work | Show actual stages, inputs used, checks completed, waiting-for-operator state, cancellation and revision history. | Jobs already expose attempts; finer stages require real backend events and explicit resume semantics. Do not fabricate progress or expose private reasoning traces. |
| Later | Multimodal intake and review | Read process diagrams or documents with page/region citations; optionally let an operator speak and confirm a transcript. | Requires extraction, previews, provenance and consent flows not currently implemented. Voice is an input option, never the only usable UI. |
| Later | New-source impact review | When a specification changes, identify affected concepts and stories and propose a revision. | Requires source versioning and dependency tracking; no automatic cross-tenant learning or activation. |

Useful generic components: evidence card, choice-with-consequences card, entity inspector,
relationship inspector, lifecycle diagram, before/after comparison, event timeline,
expected-versus-observed result card, and readiness summary. The agent selects content
and component type; the application validates payloads and owns actions, layout and
accessibility. Avoid arbitrary agent-generated JavaScript or an unpredictable redesign
of the navigation on every turn.

No framework swap is required to begin. A bounded server interface could expose
read_pack, explain_element, propose_revision, preview_change, validate_draft and
run_reviewed_story. These are proposed scoped capabilities; today the authoring agent
is tool-free. Introducing them would not authorize a shell, engine edits, live tenant
configuration changes or unchecked database access.

## Current external patterns worth evaluating

- [AG-UI](https://docs.ag-ui.com/introduction) describes an event-based connection
  between agents and interfaces, including state and interaction events. Consider it
  when adding streaming or steering; verify the particular adapter's implemented
  features because its overview includes both current and upcoming building blocks.
- [A2UI component catalogs](https://a2ui.org/concepts/catalogs/) constrain generated
  interfaces to an application's declared components and validate payloads. This
  matches the decision-card direction. Prototype with existing React components before
  committing to protocol adoption or a second rendering framework.
- [MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) provides a way
  to present interactive tools in supporting conversational hosts. It is an optional
  distribution path for a review surface, not a prerequisite for Engram's own UI.
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
  illustrate persisted pause/resume around human input. Evaluate that interaction
  requirement against the existing job/store mechanism before introducing a new
  orchestration framework.
- [Anthropic's agent engineering guidance](https://www.anthropic.com/research/building-effective-agents)
  supports starting with simple, composable patterns and adding complexity when
  justified. Its guidance does not establish that any Engram feature works.

These are research inputs to a proposal, not installed integrations or claims that a
library alone produces a good operator experience. Product-specific choices above are
our design recommendations, not conclusions established by those sources.

## Smallest useful sequence and acceptance

First slice: read-only Ask this ontology, contextual evidence, and a clear distinction
between asking and proposing a change. Then add typed decision cards and understandable
change consequences. Next integrate story review and coverage into the same workspace.
Only then assess streaming protocols, richer document intake and alternate hosts.

Before expanding, test the same interactions across PDLC, a payments/incident pack,
and a procurement pack, including a pack without lifecycle states and one with
insufficient relationship evidence. No domain-specific UI branch should be needed;
fixtures and labels are allowed to differ. A procurement trial would be a controlled
fixture exercise, not a claim of SAP Concur integration.

Run a real operator study after the heuristic review. Observe whether a person can:
- Start from supplied business documents without knowing Engram field names.
- Explain an entity's identity and one relationship in their own words.
- Ask a question without accidentally revising the pack.
- Understand the consequence of a proposed key or lifecycle change before accepting.
- Identify a deliberately wrong expected result, including a negative assertion.
- Recover from a failed agent call without losing work or changing expectations to pass.
- Explain the difference between pack validation, story success, approval and activation.

Measure unassisted task completion, requests for help, wrong approvals, repeated
questions, recovery success and time spent interpreting controls. Compare against the
current captured flow; do not invent success percentages or infer usability from
passing automated tests. Preserve server gates while improving how humans understand
the decisions those gates protect.
