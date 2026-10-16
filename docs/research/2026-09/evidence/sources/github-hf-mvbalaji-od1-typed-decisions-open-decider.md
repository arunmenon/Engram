---
schema_version: 1
artifact_id: N-20260928-14
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104448047136866581", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:mvbalaji/od1-typed-decisions
claim_cluster: hf:mvbalaji/od1-typed-decisions
feeds: ["decision"]
primary_source: https://huggingface.co/mvbalaji/od1-typed-decisions
source_commit: 3e203a7a6edda2608e383cd373b93bd4e0d146ac
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: none
priority: 2
tags: {"mechanism": ["open-weight decision model", "soft-label fine-tuning", "two-model cascade", "early exit"], "workload": ["typed-decisions workflows"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-model tables, calibration bins, latency tables and overlap analysis on the model cards", "control": "medium: same 2,000-decision test split and formulas as the benchmark card, but baselines were called through a choice-wrapped interface and the checkpoint was evaluated without the yes/no definitions", "independence": "medium: individual builder, not TypeSafe; labels come from the shared benchmark teacher", "reproducibility": "high: weights, cards and inference code at pinned revisions (4B 3e203a7, nano v2 c4e855e)", "applicability": "medium: the recipe (fine-tune a 0.8B to 4B open model on your own typed decisions) is exactly priority 2; the workflows are not memory stages"}
beliefs_affected: {"supports": ["B13", "B14"], "contradicts": [], "would_create": ["A 4B open-weight model fine-tuned on about 5,400 in-domain typed decisions (0.21 H100-hours) outscores zero-shot Jev on those workflows (0.796 vs 0.727 or 0.741), at about 10 to 16 ms for one question on one H100"]}
claim_correction: The post reports the Nano specialist at 76.5% with 5.8 / 10.9 / 32.2 ms timings; the nano v2 card states 0.765 on the official split but says the v2 vs v1 improvement "is not statistically established" (paired +1.4 pt, 95% interval [-0.25, +3.0]) and that the test split "has been used to evaluate other models in our project, so treat comparisons on it as exploratory". The post also omits that Jev is a zero-shot generalist while od1 is fitted on the benchmark's train split.
---

# Open Decider od1-typed-decisions (4B) and od1-nano-v2 (0.8B): open-weight typed-decision specialists that beat Jev on typed-decisions

- **URL:** https://huggingface.co/mvbalaji/od1-typed-decisions and https://huggingface.co/mvbalaji/od1-nano-v2-typed-decisions
- **Type:** model cards with weights and inference code (Hugging Face)
- **Author / org:** mvbalaji (Balaji, "OpenDecider" experiments); licence Apache-2.0; bases Qwen/Qwen3.5-4B and Qwen/Qwen3.5-0.8B
- **Date:** 4B revision `3e203a7a6edda2608e383cd373b93bd4e0d146ac` (2026-09-27T14:33:10Z); nano v2 revision `c4e855eef8ebe28f54fbb89d55616e72b9afab81` (2026-09-27T15:57:22Z)
- **Retrieved:** 2026-09-28, raw README.md of both cards via curl (4B card read fully to the Requirements section; nano v2 card read to the Speed table).
- **Cited by evidence:** @DataBalaji 2026-09-28 https://x.com/DataBalaji/status/2104448047136866581
- **Relevance to a memory stack:** high for priority 2: a documented, cheap recipe for a self-hosted decision model in the Jev `/v1/systemone` shape, with calibration and latency measured.

## TL;DR
- od1-typed-decisions (4B specialist) scores 0.796 accuracy on the typed-decisions test split (2,000 decisions), KL 0.082, Brier 0.045, against Laya typed-decisions 0.769 (native), meraGPT Decider 1 0.768 and Jev 1.13 0.741 (this card's measurement; the benchmark card has 0.727).
- It is a specialist: fine-tuned on the benchmark's train split (1,080 records / 5,400 decisions) with cross-entropy against the soft gold, 0.21 GPU-hours on one H100. Jev is zero-shot. The card says to compare it with fitted models only.
- Under-confident rather than over-confident: answers at 0.6 to 0.7 were right 87% of the time, 0.7 to 0.8 96%, >= 0.8 100%; "none of its 407 errors had confidence >= 0.9".
- Latency on one H100 (bf16, batch 1, CUDA graphs): 10.7 ms p50 for a short state with 1 question, 126.1 ms for a medium state with 20 questions (Laya native: 15.9 and 41.4 ms). Per-question calls, so cost grows with question count, unlike Jev and Laya.
- The cascades (nano first, or early exit) saved little: 96.5% and 98.8% of requests escalated.

## What it claims / describes
- Interface: "give a model a state (text or JSON) and typed questions (`choice`, `noul` = yes/no, `score` = ordinal) and it returns every answer with a full probability distribution (plus an explicit `NOT_ANSWERABLE` outcome), in the Jev / TypeSafe `/v1/systemone` shape, many questions per call."
- Training (4B card, Training table): starting point od1-base (Qwen3.5-4B fully fine-tuned with the Open Decider recipe); data = typed-decisions train split, 1,080 records / 5,400 decisions, plus 120 records / 600 decisions for early stopping; labels = soft gold distributions ("cross-entropy against each decision's gold probabilities (equivalent to minimising KL(gold || model))"); LR 5e-6 (typed heads 3e-4), warmup 30, up to 3 epochs = 204 steps, 24,576-token batches, bf16, 8-bit AdamW, best step 200 (validation 0.828); compute 0.21 GPU-hours on one H100.
- Correction section (2026-09-27): an earlier card wrongly said hard labels; a controlled re-run reproduced validation 0.8267, KL 0.082.
- Input-format disclosure: the checkpoint was trained and evaluated without the true/false definitions that four of six yes/no question types carry; competitor runs also got bare yes/no options, except Laya native.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| accuracy, od1-typed-decisions 4B | 0.796 (choice 0.768, yes/no 0.867, score 0.765) | Jev 1.13 0.741 (0.727 choice, 0.817 yes/no, 0.694 score); Laya native 0.769; meraGPT 0.768 | typed-decisions test, 2,000 decisions / 400 cases | specialist vs zero-shot generalists |
| KL / Brier, 4B | 0.082 / 0.045 | Jev 1.442* / 0.148* (card's published values) | same | |
| accuracy, od1-nano-v2 0.8B | 0.765 (1,530/2,000) | nano v1 0.751 | same | v2-v1 +1.4 pt [-0.25, +3.0], not established |
| accuracy, other roster | Tev1-4B 0.690; CLM-8B 0.393; Laya base 0.353 | | same | choice-wrapped calls |
| by workflow, 4B | invoice 0.848, customer service 0.826, security 0.796, agent-trace 0.716 | | same | weakest: agent-trace urgency 0.57 |
| template overlap | 94 of 400 test states share >= 50% of 13-grams with train | | 4B card | nano: 0.776 on 306 lower-overlap states vs 0.751 all |
| calibration bins, 4B | 0.6-0.7: 87% right; 0.7-0.8: 96%; >= 0.8: 100% | | ECE 0.157 (15 bins) | under-confident |
| new workflows, nano v2 | 0.705 (832/1,180) vs v1 0.461; 4B 0.777 | | 236 cases, KYC, field service, inventory, adverse events | same teacher (Qwen3.5-27B-FP8), not human-reviewed |
| p50 latency 4B, short/1q | 10.7 ms | Laya native 15.9 ms | one H100, bf16, batch 1 | |
| p50 latency 4B, medium/20q | 126.1 ms | Laya native 41.4 ms | same | per-question passes |
| cascade two-model | 0.795, 96.5% escalated | accuracy mode 0.796 | test split | little saving |
| training compute | 0.21 GPU-hours, one H100 | | | |

## Mechanism details you could implement
- Recipe for our own decision model: take an open 0.8B to 4B base, fine-tune on our logged typed decisions with soft targets (average several labeller samples, or Jev probabilities as a teacher) using cross-entropy against the distribution; hold out by workflow; report KL and Brier.
- Serve with `OD1Model.load(path, dtype='bf16', device='cuda')` plus `enable_cuda_graphs()`; answers come back per question with a confidence.
- Fit a temperature < 1 on our own validation data if the model is under-confident ("sharpens the probabilities without changing any answer").
- Cascade thresholds (nano first, escalate if the lowest per-question confidence < 0.6) should be fitted on validation only; check the escalation rate before assuming savings.

## Limitations, caveats, counter-evidence
- Card limitations: fitted to the four workflows; English only; "The benchmark measures agreement with teacher-derived labels"; teacher self-agreement 0.735, so scoring above it is not "evidence of overfitting, nor of better real-world decisions"; "Baselines were called through a choice-wrapped interface ..., which may understate them. No frontier-LLM reference was run."
- Specialist vs zero-shot comparison flatters the specialist by design.
- The test split has been reused for model selection across the project (nano v2 card).
- No memory-stage decisions tested.

## Takeaways for tuning a memory stack
- The self-hosting goal (priority 2) looks cheap to attempt: a few thousand labelled in-domain decisions and under an H100-hour of training beat zero-shot Jev on its own workflows. The real cost is labelling our own decisions.
- Plan for many questions per state: od1 runs one pass per question, so 20 questions cost about 126 ms vs 41 ms for Laya's native call; a shared-encoder design matters for write-gate batches.

## Open questions
- Would a specialist trained on our memory decisions (store/skip, supersedes, still-true, rerank) beat Jev on held-out repositories, not only held-out cases?
- How much of the 0.796 comes from template overlap with the train split?

## Grading and labels
- Directness high; control medium; independence medium; reproducibility high; applicability medium.
- Pillars: R9 primary, R4 secondary. Memory stage: none (generic typed decisions). Priority 2. Products named: Jev, Laya, CLM, meraGPT Decider 1, Open Decider od1.
- Beliefs: supports B13 (escalating to a larger or second tier is not automatically better: the cascades gained nothing); supports B14 (calibration must be fitted locally; here the open model is under-confident, Jev over-sharp relative to soft gold); would create the self-hosted-specialist belief.
- Contradiction rows: none.

## Origin chain
- Post 2104448047136866581 (@DataBalaji, author) -> HF model cards mvbalaji/od1-typed-decisions@3e203a7 and mvbalaji/od1-nano-v2-typed-decisions@c4e855e (Results, Calibration, Training, Speed, Limitations) -> this note.
- Independence: same benchmark and teacher labels as N-20260928-13 and N-20260928-15; Laya numbers come from Laya's own checkpoint runs by this author.
