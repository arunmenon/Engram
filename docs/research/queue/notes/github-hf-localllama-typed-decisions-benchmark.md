---
schema_version: 1
artifact_id: N-20260928-13
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104385446465990800", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:datasets/LocalLLaMA/typed-decisions
claim_cluster: hf:datasets/LocalLLaMA/typed-decisions
feeds: ["decision"]
primary_source: https://huggingface.co/datasets/LocalLLaMA/typed-decisions
source_commit: f7a2487edd7a043a5441a5e9ccc7fe5ddbd9ebe8
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R6", "R4"]
memory_stage: evaluation
priority: 2
tags: {"mechanism": ["typed decisions", "soft gold distributions", "teacher labelling", "calibration metrics"], "workload": ["agent-trace observability", "customer service", "invoice processing", "security incidents"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: dataset, leaderboard and a measured Jev run are on the card", "control": "medium: fixed test split and reference ceilings, but gold is a 4B-class teacher, not humans, and specialist vs generalist rows are mixed", "independence": "medium: states it is not affiliated with TypeSafe; the top row is a commercial model (meraGPT Decider 1) whose relation to the card author is not stated", "reproducibility": "high: data, splits and scoring formulas published at a pinned revision", "applicability": "medium: typed questions over one state match our gates, but workflows are synthetic business ones, not engineering memory"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["On synthetic typed workflows, accuracy saturates near teacher self-agreement (0.735); Jev 1.13 scores 0.727 and several open or commercial decision models match or exceed it, so this benchmark cannot separate strong models"]}
claim_correction: The post says "Jev 1.13.0 scores 0.727 there"; the card agrees (measured 2026-09-18), but the od1-typed-decisions model card reports Jev 1.13 at 0.741 "measured 2026-09-25" on the same 2,000 decisions, so two Jev numbers circulate for the same split.
---

# Typed Decisions (LocalLLaMA/typed-decisions): a benchmark for System One decision models, with a measured Jev 1.13 row

- **URL:** https://huggingface.co/datasets/LocalLLaMA/typed-decisions
- **Type:** dataset card and leaderboard (Hugging Face)
- **Author / org:** LocalLLaMA (HF account); licence Apache-2.0; the card states: "This benchmark is independent. It is not affiliated with TypeSafe and it does not reproduce their Jev model."
- **Date:** revision `f7a2487edd7a043a5441a5e9ccc7fe5ddbd9ebe8`, last modified 2026-09-25T07:49:05Z
- **Retrieved:** 2026-09-28, raw `README.md` via curl (leaderboard, "What a score here means", "Two ways to be scored", "Baseline results").
- **Cited by evidence:** @sandeep85das 2026-09-28 https://x.com/sandeep85das/status/2104385446465990800 ("typed-decisions on Hugging Face has the harness included (we published it; Jev 1.13.0 scores 0.727 there)"); the benchmark is also the evaluation for Julia-1 (N-20260928-15) and od1 (N-20260928-14).
- **Relevance to a memory stack:** medium-high. It is becoming the shared yardstick for Jev vs open-weight decision models (priority 2), and its card is unusually honest about what a score means, which we should copy for our own benchmark.

## TL;DR
- 1,600 synthetic cases in four workflows (agent-trace observability, customer service, invoice processing, security incidents), 5 typed questions per case (`noul`, `choice`, `score`); test split = 400 cases, 2,000 decisions. `state` + `questions` is exactly a `POST /v1/systemone` body.
- Gold = mean of 3 samples from "a teacher endpoint of roughly 4B-class capability" at temperature 0.7. "A score measures agreement with that teacher. It does not measure correctness."
- Reference points: majority 0.520, "perfect scenario understanding" 0.704, teacher self-agreement 0.735. "Around 0.75 is saturation." "A score much above 0.75 means a model has learned the teacher's quirks rather than the task."
- Measured Jev 1.13.0 (2026-09-18, via the API, 400 cases, 0 errors): accuracy 0.727, KL 1.442, Brier 0.148, ECE 0.144, p50 710 ms per case, $0.016 total. Top zero-shot row: meraGPT Decider 1 at 0.768, KL 0.096, Brier 0.052, 526 ms.
- Jev picks the right label but its distributions are far from the soft gold (KL 1.442 vs ModernBERT's 0.223), "confident because it is usually correct" (ECE 0.144, overconfidence +0.023).

## What it claims / describes
**Construction ("How it was built").** 1) sample a latent skeleton of independent factors (topic, tone, tenure, severity, discrepancy type, whether a constraint was violated...); 2) render the state (free text written by a model conditioned on the skeleton, structured where the artefact is structured); 3) label with a teacher sampled 3 times at temperature 0.7, gold = mean distribution; 4) check diversity, balance, and "whether the gold actually tracks the input".

**Specialist vs generalist ("Two ways to be scored").** Specialist = fitted per workflow on the train split, cannot answer unseen questions; generalist = one model, arbitrary schemas, zero-shot. "A specialist number sitting next to a generalist number, unlabelled, misleads the reader."

**Criteria are input.** "Every option carries a written description in `criteria`. Those descriptions are part of the input. Strip them to a bare label list and you have a different, easier task."

## Numbers

Baseline results table (card, "Baseline results"; test split):

| model | kind | acc | soft acc | macro F1 | KL | Brier | ECE | score MAE | within 1 level | ms/case |
|---|---|---|---|---|---|---|---|---|---|---|
| Uniform | reference | 0.308 | 0.311 | 0.152 | 0.444 | 0.238 | 0.169 | - | - | 0 |
| Prior | reference | 0.470 | 0.430 | 0.207 | 0.347 | 0.189 | 0.088 | - | - | 0 |
| MiniLM-L6 (22M) | specialist | 0.587 | 0.506 | 0.424 | 0.262 | 0.143 | 0.108 | 0.515 | 0.864 | 22 |
| ModernBERT-base (149M) | specialist | 0.646 | 0.542 | 0.469 | 0.223 | 0.119 | 0.179 | 0.444 | 0.931 | 349 |
| Perfect scenario understanding | ceiling | 0.704 | - | - | - | - | - | - | - | - |
| TypeSafe Jev 1.13.0 | general | 0.727 | 0.580 | 0.613 | 1.442 | 0.148 | 0.144 | 0.391 | 0.952 | 710 |
| Teacher self-agreement | ceiling | 0.735 | - | - | - | - | - | - | - | - |
| meraGPT Decider 1 | general | 0.768 | 0.608 | 0.641 | 0.096 | 0.052 | 0.180 | 0.219 | 0.984 | 526 |

Leaderboard extras: Featherless Simple Jev (`Qwen3.6-35B-A3B-classifier`) 0.716, KL 0.488, Brier 0.176 (free demo endpoint). Prices per 1M input tokens: meraGPT $0.03, Jev $0.042. Per-question ceilings "from 0.560 on `agent_trace/urgency` to 0.937 on `customer_service/category`".

Other circulating numbers on this split (for comparison, not from this card): od1-typed-decisions 4B specialist 0.796; Laya typed-decisions specialist 0.769; Julia-1 (144M) 0.7315 with Jev "reference" 0.7270; od1 card's own Jev 1.13 measurement 0.741 (2026-09-25).

## Mechanism details you could implement
- Use soft gold (mean of several teacher samples) and report KL, Brier and ECE next to accuracy; note that the Prior row has the best ECE (0.088) "while knowing nothing", which is "the clearest argument for reading KL and Brier here instead of ECE".
- Publish three reference rows with every benchmark: majority/prior floor, factor ceiling, labeller self-agreement; interpret scores above self-agreement as fitting the labeller's quirks.
- Tag every result row as specialist (fitted) or generalist (zero-shot).
- Keep option criteria (written definitions) in the input; stripping them makes a different task.

## Limitations, caveats, counter-evidence
- Gold is a ~4B teacher, not humans; "A better model can score worse here. Anything right where the teacher is wrong gets penalised. The teacher missed a duplicate invoice whose ID literally matched a prior one."
- Saturated for strong generalists (Jev 0.727 vs 0.735 ceiling); rankings near the top mostly reflect agreement with teacher quirks.
- Synthetic, English, business workflows; no engineering-memory decisions (supersedes, implements, still-true).
- The top row is a proprietary model that the card calls "state of the art on this benchmark"; the card's relationship to meraGPT is not stated (inference: possible promotion).
- Two Jev accuracies exist (0.727 here, 0.741 on the od1 card) for the same split; the difference in call format is not explained.

## Takeaways for tuning a memory stack
- For our PDLC benchmark (priority 4), copy the card's honesty devices: floor, factor ceiling, labeller self-agreement, specialist/generalist tag, KL and Brier beside accuracy.
- Do not use this benchmark to pick between Jev and open-weight models for memory stages; it is saturated and teacher-labelled. Use our own human-labelled decisions.

## Open questions
- Why do the two Jev runs differ (0.727 vs 0.741)? Different prompts, criteria handling, or model drift behind `jev-latest`?
- Would a human-labelled subset reorder the top rows?

## Grading and labels
- Directness high; control medium; independence medium; reproducibility high; applicability medium.
- Pillars: R9 primary (comparison of System One models), R6 and R4 secondary. Memory stage: evaluation. Priority 2 (open-weight vs Jev comparison) and 4 (benchmark design). Products named: Jev, Laya, Julia-1, od1, meraGPT Decider 1.
- Beliefs: supports B14 (calibration must be measured locally: a third-party measurement shows Jev ECE 0.144 and KL 1.442 against soft teacher gold); would create the saturation belief in the frontmatter.
- Contradiction rows: none.

## Origin chain
- Post 2104385446465990800 (@sandeep85das, says "we published it") -> dataset card LocalLLaMA/typed-decisions@f7a2487 (Leaderboard, What a score here means, Baseline results) -> this note.
- Independence: the same split is used by od1 (mvbalaji) and Julia-1 (Supersonic Labs) cards; all three share the teacher labels, so their agreement is not independent evidence of real-world quality.
