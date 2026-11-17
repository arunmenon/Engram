# Fable review request — Engram team presentation structure

Review the plan at:
`/Users/arunmenon/projects/Engram/docs/engram-pack-workbench-team-presentation-plan.md`

The user wants a detailed presentation explaining the entire pack workbench, its value proposition, its underlying framework and agent-assisted operator flow, with useful videos. They asked whether this should wait until M6. Review the proposed structure before slides and recordings are produced.

This is a read-only review. Do not change product code, packs, expectations, stored drafts, the proposed plan or prior reviews. Do not start provider/cloud runs. Save your review as:
`docs/review/2026-11-16-team-presentation-fable-review.md`

## Review approach

Read the plan first as a teammate new to Engram. Assume business/software knowledge but no knowledge of ontology packs, Engram terminology or prior milestones. Record where the story becomes confusing before inspecting implementation. Then use the referenced milestone/review documents and targeted current code to check consequential claims. Treat the plan as proposed content, not proof that every described demonstration exists.

Apply the explain-with-depth skill if available. Use ai-native-ui-review principles for proposed UI demonstrations. Do not conduct a broad new implementation audit. Identify required verification for later where evidence is unavailable.

## Questions to answer

1. Value: can a newcomer explain the business problem, why explicit domain rules matter, and what Engram/workbench contribute? Are there unsupported benefits, generic slogans or missing causal steps?
2. Framework: does the sequence teach context graph, packs, core/add-ons/domains, engine and tenant boundaries before relying on them? Are workbench and runtime responsibilities accurately separated?
3. Completeness: does it cover evidence intake, consent/trust, identity/lifecycle decisions, proposal inspection, citations, explanation, steering, revision recovery, prepared journeys, agent-assisted journey authoring, expected-answer review, execution, failure diagnosis and handoff without becoming a menu tour?
4. Agent assistance: can viewers distinguish operator facts, agent proposals, engine checks and actual test evidence? Is the constrained authoring loop described honestly, without implying an unrestricted coding agent? Is the help useful and observable rather than merely chat-shaped?
5. Domain breadth: do PDLC, sales and procurement demonstrate meaningful differences while preserving a coherent through-line? Should one example carry more of the story? Do not count an unresolved procurement draft as a finished executable pack or an incident fixture as payments.
6. Demonstrations: are the clips sufficient, reproducible and readable? Is anything narrated without a visible action/result? Does journey authoring need a fourth clip or can its saved example teach the mechanism clearly?
7. Evidence: check draft approval versus runtime activation versus intent readiness; fixture/live distinction; planned versus observed graph; memory versus Spanner; synthetic persona versus real human. Flag every proposed claim that must wait for M6.
8. Timing/density: is 22 slides in 35–40 minutes, including clips, realistic? Identify concrete cuts or moves to appendix without losing necessary mechanisms.
9. Language: use tenant consistently, agent for authoring assistance, domain terms before engine identifiers. Avoid abstract substitutes such as understanding/meaning when a concrete action or artifact can be named. Define necessary terms at first use.
10. Delivery gate: should content preparation proceed now? Which specific slides/clips or readiness claims must wait for M6 or independent acceptance? Distinguish an educational internal session from a release announcement.

Inspect the older video plan and narration review to prevent repeating known problems: abstract definitions before an example, activation overclaims, chapter/UI vocabulary drift, an empty form presented as authoring history, hidden controls narrated as demonstrated, and results that disappear too quickly to read.

## Required output

- Verdict: approve structure / approve with changes / revise.
- Prioritized findings with slide/section, likely audience misunderstanding, evidence where relevant, and the smallest correction.
- A compact coverage table for the complete operator journey; mark missing or duplicated coverage.
- Proposed revised sequence only if necessary, retaining useful parts rather than rewriting for taste.
- A claim/evidence table distinguishing supported now, verify before recording, and dependent on M6.
- Explicit answer on whether to wait for M6.
- Separate narrative clarity, technical accuracy, demonstration feasibility and evidence-honesty verdicts.
- State what you inspected and what remains unverified. Do not claim you watched videos or observed humans unless you did.

This checkpoint reviews the presentation plan. It does not accept outstanding product findings or substitute for the final deck/video review.
