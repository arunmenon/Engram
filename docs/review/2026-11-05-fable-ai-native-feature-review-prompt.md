# Fable: independent product and architecture review

Work in `/Users/arunmenon/projects/Engram`. Review the proposed AI-native ontology
onboarding features before implementation. This is a second opinion on the product
choices and their feasibility, not a request to approve a feature list or write code.

## Read in this order

1. `docs/ai-native-onboarding-feature-brief.md` — the primary decision brief, feature
   IDs F1–F9, operator context, scope boundaries, dependencies and proposed sequence.
2. `docs/review/2026-11-05-operator-flow-ai-native-review.md` — stage-by-stage evidence,
   domain assumptions, current external references and proposed four-activity flow.
3. `output/playwright/operator-usability-20261105/` — seven actual-screen text captures
   and screenshots. These document one saved Northstar draft, not all possible states.
4. `docs/review/2026-11-05-agentic-onboarding-remediation-independent-review.md` and
   `docs/review/2026-11-05-onboarding-remediation-disposition.md` — existing findings,
   corrections and verification limits. The disposition is an implementation report,
   not an independent re-review or proof of human usability.

Consult current code selectively to verify feasibility and hidden assumptions:
- Frontend: `demo/frontend/src/workbench/OperatorFlow.tsx`, `Workbench.tsx`,
  `JourneyAuthor.tsx`, `JourneyWorkspace.tsx`, `EntityPicker.tsx`, `PackGraph.tsx`.
- Backend: `src/context_graph/workbench/models.py`, `api.py`, `authoring.py`,
  `draft_stories.py`, `journey_authoring.py`, `journey_runner.py`, `store.py`.
- Domain/runtime files only where necessary to verify a claimed capability.

Working tree is extensively dirty/untracked. Do not assume `git diff` contains the
whole implementation or that all dirty files belong to this work. Record current
HEAD and any differences from the supplied documents that affect your conclusions.

## User intent and non-negotiable boundaries

The primary user is an internal human operator managing many tenants. They may know
the domain but not Engram, graph query configuration or pack internals. They want to
understand the ontology, ask questions about it and steer changes in business terms.

The flow must be ontology-agnostic, while its content adapts to the selected pack and
actual evidence. PDLC, payments/incidents and procurement are examples. Do not endorse
hardcoded workflow assumptions simply because they work for these examples.

The agent prepares, explains and proposes; Engram validates and executes; the operator
makes consequential business decisions and reviews outcomes. Asking a question must
not change a pack. No silent approval, expectation rewriting, source authority changes,
production activation or cross-tenant context reuse.

“AI-native” is not equivalent to chat everywhere, generated UI everywhere, unlimited
autonomy or adopting a fashionable framework. Challenge novelty without demonstrated
operator value. Preserve good deterministic controls where they are easier to use.

## Assess these dimensions

1. **Operator clarity and density.** Does each feature remove cognitive work, or add a
   new surface/choice? What must a first-time operator understand to succeed? Is the
   four-activity flow useful, or should the existing sequence be improved instead?
2. **Domain independence.** Look for assumptions about IDs, event-driven ingestion,
   relationships, lifecycle transitions, producer trust and expected-answer formats.
   Distinguish true engine limits from incidental PDLC/incident hardcoding. A pure
   catalog ontology or one without lifecycle states is an important counterexample.
3. **Agent/human division of work.** What should the agent infer, propose, ask or never
   decide? Does “recommendation” pressure the operator into trusting unsupported claims?
   Are source-backed outcomes genuinely independent of the generated interpretation?
4. **Feature value and overlap.** For every F1–F9, choose keep/change/defer/drop with a
   concrete reason, dependencies and an operator-visible acceptance criterion. Consider
   whether F1, F2 and F6 are views of one shared capability rather than separate products.
5. **Interaction and state.** Review selection-linked conversation, read-only questions,
   proposed edits, apply/undo, revisions, stale responses, interruption, resumption,
   accessibility and switching tenants. Do not assume a streamed event grants authority.
6. **Feasibility and proportionality.** Check what the repo already supports versus
   what the brief proposes. Identify the smallest adequate implementation path. Does
   the first slice need tools, new storage or a new protocol, or can existing mechanisms
   suffice? Distinguish estimates from verified facts.
7. **Technology choices.** Are A2UI, AG-UI, MCP Apps or a different orchestrator warranted
   for an actual requirement? They are alternatives/candidates, not an approved stack.
   If relying on current capability claims, verify them using primary documentation
   and distinguish released support from examples, proposals and roadmap items.
8. **Validation.** What observation would demonstrate real improvement? Automated
   correctness checks, an agent performing the UI, and novice human comprehension are
   different kinds of evidence. Give a realistic cross-domain operator study and
   failure tests; do not invent measured scores or conversion gains.

## Concrete challenges to answer

- Should we build F1 first, or is F3 intake the prerequisite? Defend the order.
- What should a read-only answer return when no source supports the explanation?
- How can an operator see a proposed change's consequences without implying that a
  hypothetical graph was actually executed?
- How should multiple conflicting sources be resolved and recorded?
- How do we avoid replacing a dense form with a dense conversation and many cards?
- What happens to a pending answer/proposal when the pack or source changes?
- Which components can remain fully domain-independent, and which content needs a
  domain pack's metadata? What metadata is genuinely missing today?
- What must we NOT build in the first slice?

## Deliverable

Save your review to:
`docs/review/2026-11-05-ai-native-onboarding-feature-review.md`

Include:
1. A clear verdict and the three most important changes to the proposal.
2. Findings ordered by consequence, with source/section references, likely operator
   misunderstanding or engineering failure, and the smallest concrete correction.
3. An F1–F9 disposition table: keep/change/defer/drop, rationale, prerequisites and
   acceptance evidence. You may recommend merging or deleting features.
4. A stage-by-stage domain-assumption audit, separating code restrictions, illustrative
   copy, legitimate domain fixtures and general engine constraints.
5. Your recommended first slice and sequence, including what is explicitly excluded.
6. A small cross-domain operator study: tasks, failure cases, observations and criteria
   for stopping or revising the design. Include a task that detects an incorrect answer
   or relationship, not just a happy-path demo.
7. Open questions that truly need a product decision, and what you could not verify.

Review only. Do not implement the redesign, modify packs/expected answers, overwrite
existing reviews or alter live drafts/databases. Use isolated local checks if needed.
Do not initiate new paid-provider or cloud-write runs for this design review. If a
fresh live run or human study is needed, state it as a verification gap.

Keep the review independent. Prefer a justified smaller plan to polite endorsement
of all features. A coding-agent conversion is not a requirement of this brief.
