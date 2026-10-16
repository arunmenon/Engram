---
schema_version: 1
artifact_id: N-20260929-33
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104746239061586055", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.22592
claim_cluster: arxiv:2609.22592
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.22592
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R5
pillar_secondary: ["R6"]
memory_stage: evaluation
tags: {"mechanism": ["blueprint-first-task-generation", "programmatic-verifier", "llm-judge-process-score", "active-curriculum", "iterative-repair"], "workload": ["agent-rl-gyms", "productivity-tools", "temporal-reasoning"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["benchmark-construction", "difficulty-control", "cost-accounting"]}
evidence_grade: {"directness": "high: tables read from the arXiv HTML v1", "control": "low: no ablation of blueprint-first vs environment-first or curriculum on/off; one comparison gym (AWM) with different task counts", "independence": "low: single lab (Amazon AGI), LLM certification audits its own gyms", "reproducibility": "low: no code or data release stated", "applicability": "medium: blueprint-first construction transfers to building our PDLC memory benchmark; no memory-specific results"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Defining the solution space and gold derivation before materialising an environment yields verifiable generated tasks at 80 to 92 percent yield, but verifier precision and downstream held-out transfer are unmeasured"]}
claim_correction: The paper does not show that training on generated gyms improves held-out agent benchmarks; the only training result is one 8B model over 500 RL steps on 600 generated instruction-following tasks with no held-out evaluation, and no verifier precision or false-positive rate is reported.
---

# AutoGym: Blueprint-First Generation of Verifiable Agent Gyms

- **URL:** https://arxiv.org/abs/2609.22592 (HTML: https://arxiv.org/html/2609.22592)
- **Type:** paper
- **Author / org:** Aarati Andrea Noronha, Kavya Ravikumar, Carly Xiaoyu Lin; Amazon AGI (affiliation from the HTML version)
- **Date:** submitted 2026-09-18 (v1)
- **Retrieved:** 2026-09-29, arXiv v1 (abs + HTML). No local copy.
- **Cited by evidence:** feed memory; @omarsar0 post https://x.com/omarsar0/status/2104746239061586055
- **Relevance to a memory stack:** medium. Not about memory, but its blueprint-first recipe (gold solution space and derivation fixed before the environment is built, programmatic outcome checks, difficulty knobs, repair loop) is a direct template for generating our PDLC memory benchmark questions with verifiable gold answers.

## TL;DR
- A gym = task + executable environment + verifier. AutoGym first writes a blueprint (valid solution space, verification criteria, environment requirements, dependency structure), then materialises the environment, computes ground truth by executing the blueprint derivation against it, and repairs components that fail validation.
- Difficulty is steered by explicit parameters (topology tiers, capability axes, obfuscation 0.0 to 1.0, distractor budgets). Config C2 makes 39.0% of productivity tasks hard for Claude Opus 4.6 and 70.0% hard for gpt-oss-120b, vs 4.0% / 9.0% for the Agent World Model (AWM) baseline gym (Table 1).
- Quality evidence is yield after repair (C1 297/350 = 84.9%, C2 280/350 = 80.0%, temporal 92/100) plus an LLM "certification" rubric (e.g. interface realism 78.0/100). Human inspectors checked all retained tasks on three criteria, with no counts or error rates reported.
- Claim correction: no held-out agent benchmark (tau-bench, BFCL, AppWorld, WebArena) is evaluated. The only training evidence (Appendix G) is RL on an unnamed "8B checkpoint" over 500 steps on 600 curriculum-generated instruction-following tasks, "consistent improvement", without numbers in the text or a held-out test. No verifier precision, recall or false-positive rate is given.

## What it claims / describes
Abstract, first sentence (verbatim): "Training agents with reinforcement learning requires a gym, comprising a task, an executable environment in which the task can be attempted, and a verifier that reliably distinguishes success from failure." The rest of the abstract (paraphrase, extraction was not verbatim): manual gyms are costly and static; AutoGym generates complete gyms from minimal domain seeds via (1) blueprint-first generation, (2) explicit generation parameters controlling topology and difficulty, (3) active curriculum synthesis that adjusts parameters as model capability changes; shown on productivity and temporal-reasoning settings.

**Blueprint (sections 3.2 to 3.3).** Specifies, before any environment exists: entities, attributes, relationships and the conditions for correct outcomes (the valid solution space); outcome constraints (verification criteria); what must be instantiated; and information dependencies "without prescribing unique trajectories".

**Generation parameters (Appendix A).**
- Topology tiers: Tier 1 direct retrieval; Tier 2 multi-hop (2 to 4 hops), multi-constraint (2 to 5), list aggregation (3 to 20 elements); Tier 3 cross-source comparison (2 to 4 sources), parallel synthesis (3 to 5 entities), multi-hop + merge, complex comparison.
- Capability axes (orthogonal): quantitative computation, exhaustive aggregation, ranking/comparison, temporal reasoning, negative verification, implicit criteria, cross-source reconciliation.
- Obfuscation gradient 0.0 to 1.0: 0.0 to 0.3 moderate (domain hints kept), 0.4 to 0.6 goal only, 0.7 to 0.9 one or two business sentences, 1.0 "zero entity nouns".
- Distractors: persona (permission, privacy, role), content (near-matches, stale values, conflicting versions), tool (pagination, truncation, transient failures, rate limits).

**Iterative repair (section 3.4, verbatim):** "If validation reveals a missing resource, unreachable criterion, or inconsistent derivation, the responsible component is repaired and re-materialized. Agent failures on otherwise valid gyms do not trigger repair." Three repair iterations for C2 (Table 2).

**Verification (section 3.5, Appendix C).** Four signals: outcome correctness (programmatic check of values, classifications, entity sets, state changes; numeric tolerance of 1%); distractor resilience (programmatic); process quality (three-stage LLM judge: process judge, outcome judge, meta-judge); ground truth computed by executing the blueprint's derivation against the materialised environment, "not post-hoc".

**Active curriculum (section 3.6).** Multiple rollouts of the target model, aggregate success by capability dimension, analyse failure trajectories, then relax dimensions with success below 0.30 and strengthen those above 0.80, with bounds against oscillation, until stable or an iteration cap.

**Human inspection (section 4.1, verbatim):** "All retained tasks were independently validated by human inspectors who verified that (1) the ground truth is reachable from the materialized environment under the persona's access scope, (2) no distractor blocks all valid solution routes, and (3) verifier criteria match the intended task semantics." Number of inspectors and disagreement rate: not stated.

**Baseline gym (verbatim):** "Of 300 generated AWM tasks, 217 were retained after manual review for verifier correctness and environment consistency."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| hard / med / easy %, Claude Opus 4.6 | AutoGym C2: 39.0 / 10.0 / 51.0 (N=280) | AWM 4.0 / 6.0 / 90.0 (N=217); human expert-authored 21.5 / 12.4 / 66.1 (N=300) | Table 1, productivity gym; bands by mean verifier score, hard < 0.30, easy >= 0.80; 8 rollouts per task | difficulty is scored by the gym's own verifier |
| same, gpt-oss-120b | C2: 70.0 / 17.0 / 13.0 | AWM 9.0 / 13.0 / 78.0; human 40.0 / 20.0 / 40.0 | Table 1 | same |
| same, C1 (low difficulty) | Opus 10.0 / 34.7 / 55.3; gpt-oss 33.4 / 40.5 / 26.1 (N=297) | | Table 1 | |
| repair effect, C2 | before 57.0 / 13.0 / 30.0 (N=350) -> after 39.0 / 10.0 / 51.0 (N=280) | | Table 2, 3 iterations | repair removes tasks too (yield 80.0%), so the shift mixes fixing and filtering |
| yield after repair | C1 84.9% (297/350); C2 80.0% (280/350); temporal 92.0% (92/100) | AWM 217/300 retained by manual review | sections 4.1, 4.2 | yield is not verifier accuracy |
| LLM certification, productivity | scope 92.7, groundedness 91.4, scalability 90.0, task realism 89.0, environment realism 86.0, diversity 80.0, interface realism 78.0 | none | Table 3, 0 to 100, Appendix B rubric | LLM audit; no human agreement reported |
| LLM certification, temporal | 96.7, 93.4, 97.0, 98.0, 96.3, 85.0, 99.0 (same order) | none | Table 5 | authors attribute higher scores to simpler structure |
| temporal gym difficulty | Opus 6.5 / 4.3 / 89.2; gpt-oss 20.7 / 20.6 / 58.7 | | Table 4, 92 tasks | mostly easy for Opus |
| per-task cost | AutoGym mid-tier $2 to 5, frontier $3 to 8, 15.6 min | expert authoring $500 to $1000, 1 to 1.5 h | Table 8, Appendix F | expert cost basis not shown in the extraction |
| 50-task gym cost | mid-tier $100 to 150, frontier $150 to 200, 54 min at 20x parallelism | expert $25K to $50K, 2 to 4 weeks | Table 9 | |
| RL on generated gym | "consistent improvement over 500 steps" | none | Appendix G, 600 curriculum tasks, unnamed 8B checkpoint | no numbers in text (Figure 2 only), no held-out eval; limitations section describes it as "500 GRPO steps" in our extraction |
| verifier precision / false positives | none reported | | | |
| held-out benchmark transfer | none reported | | | |

## Mechanism details you could implement
- Write the gold first: for each benchmark item, declare entities, relations, success constraints and a derivation, materialise the store, then compute the gold answer by running the derivation against it. For us: a PDLC fixture where a question like "which tests verify requirement R-12 after decision D-7 superseded D-3" has its gold computed from the trace graph, not hand-written (inference).
- Use the knobs as benchmark strata: hops (2 to 4), constraints (2 to 5), aggregation list length (3 to 20), obfuscation of the query (0.0 to 1.0), and content distractors (near-matches, stale values, conflicting versions) which map directly onto staleness and supersession tests (inference).
- Difficulty bands by mean verifier score over 8 rollouts: hard < 0.30, medium 0.30 to 0.80, easy >= 0.80; curriculum relaxes below 0.30 and strengthens above 0.80.
- Repair only generator faults (missing resource, unreachable criterion, inconsistent derivation), never agent failures, to avoid tuning the benchmark to the model.
- Keep deterministic outcome checks programmatic (1% numeric tolerance), and restrict LLM judging to process quality.

## Limitations, caveats, counter-evidence
- Authors (section 5): interface realism is weakest (78.0) because of tool mocking with per-task databases and simplified schemas; open-ended tasks still rely on LLM judgment ("Eliminating LLM adjudication entirely for free-form tasks remains an open problem"); RL experiment limited to one 8B model over 500 steps; cloud-emulator substrate (Appendix E) not evaluated.
- No ablation isolates blueprint-first from environment-first; the AWM comparison differs in generator, domain coverage and task count (217 vs 280).
- "Harder" is measured by the same verifier that defines success; a buggy verifier also produces hard tasks (inference). Human inspection is binary pass/fail with no reported rates.
- No code or data release stated.

## Takeaways for tuning a memory stack
- Build our PDLC memory benchmark blueprint-first so gold answers are computed from the fixture, which reduces the label leakage risk we saw in our own harness (B19) (inference).
- Include "stale value" and "conflicting version" distractors as first-class strata; they are exactly the supersession and staleness cases our stack must handle.
- Report yield and human-audit disagreement separately from verifier accuracy; AutoGym shows that yield alone does not tell you verifier false-positive rates.

## Open questions
- What is the verifier's false-positive rate against human judgment? Not reported.
- Does RL on AutoGym tasks transfer to any held-out agent benchmark? Not reported.
- How many tasks did the human inspectors reject, and for which criterion? Not stated.

## Grading and labels
- Directness: high, tables read from arXiv HTML v1.
- Control: low, no ablations; baseline gym differs in more than one factor.
- Independence: low, single lab; certification is an LLM audit of its own output.
- Reproducibility: low, no release.
- Applicability: medium, construction method transfers to our benchmark; no memory results.
- Pillars: R5 primary (environments for learning from experience, curriculum); R6 secondary (verifier design, benchmark construction).
- Stage: evaluation.
- Tags: mechanism blueprint-first-task-generation, programmatic-verifier, llm-judge-process-score, active-curriculum, iterative-repair; workload agent-rl-gyms, productivity-tools, temporal-reasoning; lifecycle evaluation; cross-cutting benchmark-construction, difficulty-control, cost-accounting.
- Beliefs: supports none; contradicts none; B19 relevant as motivation only (gold computed from blueprint is a leakage countermeasure, untested here); B20 consistent (headline narrowed on primary read); would create a lead on blueprint-first verifiable task generation.
- Arm-vs-arm test implied: weakly yes (inference): generate a PDLC memory benchmark slice blueprint-first vs hand-authored, and compare how well each separates two memory configurations and how often a human auditor disputes the gold. The paper runs no such test.

## Origin chain
- @omarsar0 post 2104746239061586055 (feed memory) -> https://arxiv.org/abs/2609.22592 v1 -> https://arxiv.org/html/2609.22592 (tables, appendices) -> this note.
