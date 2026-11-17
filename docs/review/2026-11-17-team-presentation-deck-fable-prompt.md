# Fable review request — executive context and the Engram workbench story

The user's primary feedback is: **the deck needs more executive-friendly context around the pack workbench; its value is not coming through.** Review the rendered presentation first as a product/business leader with no Engram knowledge, then as a domain operator, and finally as an engineer checking its claims. These are review lenses, not evidence from real participants.

Do not merely polish wording or check factual accuracy. Diagnose why the audience might understand the buttons yet still not understand why we built this product. Propose a concrete narrative correction with replacement slide content and narration. Do not change the deck, product code, packs, expectations or runtime data in this review. No live provider or Spanner calls are requested.

Use `explain-with-depth` if available. If unavailable, disclose that and apply purpose-first, source-grounded explanation principles. Preserve technical substance and material limits while moving secondary implementation detail into notes or the appendix.

## Open these artifacts

Repository: `/Users/arunmenon/projects/Engram`.

- Interactive standalone deck: `output/presentation/engram-team-20261117/engram-team-presentation.html`
- PDF: `output/presentation/engram-team-20261117/engram-team-presentation.pdf`
- Full narration / storyboard: `docs/engram-team-presentation-script.md`
- Content baseline: `docs/engram-pack-workbench-team-presentation-plan.md`
- Your structure review: `docs/review/2026-11-17-team-presentation-fable-intuitive-revision.md`
- Asset hashes / titles: `output/presentation/engram-team-20261117/manifest.json`
- Implementer browser checks: `output/presentation/engram-team-20261117/verification.json`

Open the HTML in Chrome. Use arrows or the slide picker, N for speaker notes, and click a UI still to inspect its full recorded source. There are 17 main slides and seven appendix slides. The PDF includes the slides, not the speaker notes. HTML is self-contained and makes no provider requests.

The connected Spaces document was created but its editor failed with `artifact_preparation_failed`; the local artifact runtime was unavailable. HTML and PDF are the fallback deliverables. Do not mistake the empty Spaces document for the deck.

## First pass: the executive story, before notes or implementation

Read the main slides without speaker notes first. Record what the deck itself communicates, then read the narration and identify what only the presenter supplies. An executive should not need to read a code appendix to understand the proposition.

Within the opening three to five minutes, can the audience answer these questions?

1. **What problem are we solving?** Business events contain fields, but useful answers depend on rules about identity, relationships, state and trust. How does a mistake affect an operational decision? Use Ann as an illustration, then make the broader problem explicit; do not let an email-key defect become the entire product rationale.
2. **What is Engram's role?** Explain a context graph through what it lets us connect and inspect. Show where it sits relative to source systems and downstream questions or agents. Do not imply the workbench replaces the source systems, is a generic BI product, or automatically solves every question.
3. **Why ontology packs?** Explain the separation of domain rules from the shared engine. What can be configured and reused, and what still needs engineering? Explain core, optional add-ons and domain extensions in terms of their purpose before their names.
4. **Why a workbench?** Why is an engine plus YAML insufficient for the intended operator? Connect the screens to making business rules visible, correcting the agent, reviewing consequences, testing examples and producing a traceable handoff. Describe these as supported mechanisms; do not claim measured reductions in onboarding time or defects.
5. **Who contributes what?** Domain experts provide definitions and intended outcomes; operators curate inputs and review proposals; the agent explains and proposes; the engine validates and executes; engineering/operations owns unsupported behavior and runtime rollout. Distinguish today's internal operator from an eventual tenant self-service user.
6. **What changes operationally?** Contrast a clearly labelled illustrative manual process with the demonstrated assisted loop. Show the artifacts and ownership at each handoff. Do not invent an observed customer baseline, labour savings or autonomous operation.
7. **What do we have today, and what is the next decision?** Separate implemented capabilities, recorded demonstrations, intended benefits and unverified outcomes. End with a useful team action or scoped pilot proposal, rather than a milestone scoreboard alone.

For each question, cite the slide that answers it, or mark it missing. Identify the audience consequence of each gap. Prioritize causal gaps over unfamiliar words.

### Candidate value proposition to challenge, not repeat uncritically

“Engram makes domain rules explicit so events can become connected records that support useful questions. The pack workbench lets an operator bring domain material, use the agent to propose those rules, inspect and steer the proposal, and test it against reviewed examples before handing it off.”

Check whether this is accurate, sufficiently concrete and distinctive. Improve it without adding claims of universal extraction, automatic domain expertise, measured ROI, completed activation or proven self-service.

Build a short **capability → operator consequence → intended business benefit → evidence/limit** table. For example, reviewed identity rules can prevent the demonstrated split-record interpretation; this is not proof of fewer production incidents. Treat faster onboarding, lower engineering effort and lower change risk as hypotheses unless there are measurements in the supplied record.

## Second pass: connect the value to the operator loop

For each act, record what you believe the audience has learned and any missing causal step. Can a newcomer explain: why identity rules matter; how a pack differs from the engine; what they must supply; how asking differs from sending; what review and tests prove; and what handoff does not do?

Check the 17-slide sequence against your four-act proposal, but do not preserve the previous structure at the expense of the user's new feedback. Prefer merging or reframing existing slides to adding a long abstract preamble. Keep the concrete opening, followed promptly by the domain-agnostic value and system context. Explain the tradeoff if changing the slide count is necessary.

Confirm the early overview and late architecture detail work together. Confirm all baseline topics and appendices have a home. Assess whether source material, citations, test results and handoff are named distinctly.

Review the AI-native story explicitly: does it show what the operator can ask, how the answer is grounded, how the operator steers it, what changes only after sending, and how uncertainty or failure is recovered? “We have an agent” is not a value proposition. Do not recast this constrained authoring loop as a coding agent or autonomous onboarding.

Check cross-domain credibility. Distinguish the executable CRM example and prepared PDLC story from procurement intake and the incident fixture. Explain how the same workflow accommodates different domain rules without implying that all showcased domains are equally complete.

## Third pass: inspect the rendered slides

- Read every slide at presentation size, including PDF. Flag clipping, tiny essential text, excessive density or a screenshot that does not support the adjacent statement. Check every image's enlargement and speaker notes.
- Evaluate whether the recurring events → rules → graph → answers strip helps, without implying authoring is runtime execution.
- Inspect the Ann opening: it is an explanatory summary, explicitly labelled baseline planned projection versus revised recorded graph. It is NOT a pair of fresh UI captures. Final recording-build captures remain pending.
- Slide 7 shows a saved guided live CRM request. The issue was pre-identified; no autonomous diagnosis claim. Recorded next-step text still contains engine vocabulary; judge it honestly.
- Slide 9 uses the independently rechecked confirmation-reset behavior. Do not reopen closed M6-1 without new evidence; the unsaved-selection wording low remains open.
- Slide 10: F1 1.0 means no regression on two existing questions, neither testing Ann's email change. One contact was observed, not checked by a dedicated reviewed assertion.
- Slide 12: 111 per-check outcomes match across recorded memory and Spanner runs. Passing totals include flagged weak checks. One story is not exhaustive PDLC coverage; the earlier timeout cause remains unknown.
- Slide 13 is a diagram of the fixture-author workflow, not a live-agent demonstration.
- Slide 14 is incident operations, not PDLC. Deliberate failures and unsupported scalar totals remain visible.
- Research appendix: comparison, not implementation or benchmark equivalence. Core is mandatory; add-on declarations do not promise all processing in this sandbox.
- Approval/handoff is not activation, and draft workspace cards are not proof of deployed tenant isolation.

## Current boundaries

This is a draft teaching deck with five recorded UI stills, not an edited video. Three final clips and voice-over remain pending. M6 passed bounded technical scope; real-operator sessions and earlier low findings remain open. No new live runs were performed for this deck. Technical browser checks are implementer-side checks, not independent acceptance.

## Deliverable

Write `docs/review/2026-11-17-team-presentation-deck-fable-review.md` with:

1. Separate verdicts for **executive value clarity**, operator-story clarity, technical accuracy, visual readability and recording readiness. Do not average them into a single score.
2. A gap table for the seven executive questions above, plus the capability-to-benefit table. Identify the three highest-impact changes.
3. A proposed revised slide sequence: headline, audience question, one takeaway, visual, and which current content moves or merges. Retain a coverage map so necessary topics are not lost.
4. **Ready-to-use replacement content for the opening three to five minutes**: concise on-slide text and natural speaker narration. Include the problem, domain-agnostic Engram context, why packs and why the workbench. Keep the concrete example and avoid a list of definitions.
5. Proposed closing content: what is available, what remains to validate, and the practical team ask. Label a proposed pilot or success metric as proposed; do not invent a commitment or measured outcome.
6. Findings with slide, observed issue, audience consequence, smallest correction and verification condition. Distinguish script, slide and recording issues.
7. Five comprehension questions with expected answers, including “What happens when the tenant needs behavior the engine does not support?” and “Does approving a pack put it into production?” These are desk-check criteria, not a human study.

The result should help us revise the deck, not launch another product redesign. Do not demand fresh product runs just to restate recorded claims. Do not hide material limitations to make the presentation sound stronger; equally, do not let historical review bookkeeping overwhelm the product story.
