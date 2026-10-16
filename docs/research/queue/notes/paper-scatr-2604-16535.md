---
schema_version: 1
artifact_id: N-20260929-18
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104596681861833156", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2604.16535
claim_cluster: arxiv:2604.16535
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2604.16535
source_commit: n/a
strength: paper-ablated
pillar_primary: R4
pillar_secondary: []
memory_stage: reranking
tags: {"mechanism": ["hidden-state-probe", "mlp-scorer", "best-of-n-selection", "weighted-majority-vote", "small-calibration-set"], "workload": ["math-reasoning", "code-generation", "humaneval", "kodcode", "aime", "math-500"], "lifecycle_stage": ["read"], "cross_cutting": ["cost", "open-weight-only", "calibration"]}
evidence_grade: {"directness": "medium: Tables 6 and 7 measure candidate selection accuracy directly, but for single-turn math and code answers, not memory items", "control": "high: same candidate pools, baselines (confidence-based, LoRA, ReasonFlux PRM) and oracle per cell; ablations on layer, calibration size, scorer design; 9 runs per cell", "independence": "low: author-run evaluation; ground truth is unit tests or exact match, so no LLM judge", "reproducibility": "high: code link (github.com/martaknezevic/SCaTR), seeds 32/42/52 stated, mean +/- sd; repo not cloned this run", "applicability": "low: needs hidden states, so open-weight models only; single-turn tasks; says nothing about hosted decision models such as Jev"}
beliefs_affected: {"supports": ["B14", "B13"], "contradicts": [], "would_create": ["A 2 to 7M-parameter MLP on the generator's penultimate-layer hidden state, fit on 164 to 1,000 labeled problems, selects among 16 candidates better than token-confidence baselines in 12 of 14 cross-dataset cells and close to LoRA; requires open weights"]}
claim_correction: Secondary summaries say SCATR beats confidence ranking "by up to 9% on coding and math" and present it as a recipe for Jev-style decision models; the +9.1 is points on one math cell (Qwen-30B-A3B, MATH-500 to AIME, 30-problem test sets), the coding maximum is +6.1, two math cells are negative (-3.5, -3.3), no calibration error is reported, and the paper never mentions Jev or decision models (only the author's post does).
---

# SCATR: Simple Calibrated Test-Time Ranking

- **URL:** https://arxiv.org/abs/2604.16535 (HTML: https://arxiv.org/html/2604.16535v2); paper spells it "SCaTR"
- **Type:** paper
- **Author / org:** Divya Shyamal (MIT), Marta Knezevic (EPFL), Lan Tran (EPFL), Chanakya Ekbote (MIT), Vijay Lingam (UT Austin), Paul Pu Liang (MIT). Code: https://github.com/martaknezevic/SCaTR (not cloned).
- **Date:** v1 2026-04-16, v2 2026-04-21
- **Retrieved:** 2026-09-29 (version v2)
- **Cited by evidence:** @thecekbote (Chanakya Ekbote, co-author), https://x.com/thecekbote/status/2104596681861833156: accepted to the Workshop on Efficient Reasoning at COLM 2026; "Which answer should you trust, and how do you make that decision cheaply?"; "That's also why we find the direction behind systems like Jev interesting". The COLM acceptance is stated only in the post; the arXiv v2 text read has no venue line.
- **Relevance to a memory stack:** low to medium. It is a clean, ablated recipe for fitting a small scorer on local labels to pick among candidates (the "fit locally" stance of B14), but it needs the generator's hidden states, targets single-turn math and code answers, and is not about memory items or System One models.

## TL;DR
- Scorer = shallow MLP (2 to 3 hidden layers, e.g. [512,256] or [1024,512,256], ReLU, sigmoid output) on the "final non-padding token embedding from the penultimate layer" of the model that generated each candidate. 2.1M to 6.6M parameters (Table 2).
- Trained on a small calibration set of the model's own rollouts labeled correct/incorrect (N = 16 per prompt; 164 HumanEval, 500 MATH or 1,000 KodCode problems), then tested cross-dataset (e.g. calibrate on HumanEval, test on KodCode).
- Code: Best-of-N argmax of the score; math: score-weighted majority vote.
- vs best token-confidence baseline: +0.2 to +9.1 points in 12 of 14 cells, -3.5 and -3.3 in two math cells (Tables 6, 7). Comparable to LoRA on the same calibration data with far fewer parameters; up to about 700x faster than the ReasonFlux 1.5B PRM at scoring (Table 2).
- **Claim correction:** "up to 9%" is one math cell with 30-problem AIME tests; "calibrated" is not measured (no ECE); Jev appears only in the author's post.

## What it claims / describes
Setting: parallel test-time scaling, N sampled candidates, choose one. Existing cheap selectors use token confidence; strong selectors use a process reward model (PRM) or fine-tuning.

1. Generate N = 16 rollouts per calibration prompt with the target model M; label each 1 if it passes tests (code) or exact-matches (math), else 0.
2. Extract the penultimate-layer hidden state at the last non-padding token for each rollout.
3. Train an MLP f with weighted cross-entropy, w = N0/N1 (negatives over positives); Adam, gradient clipping at norm 1.0, ReduceLROnPlateau, early stopping patience 10, max 100 epochs; 100 random hyperparameter configurations chosen by validation loss; 75/25 split by problem id.
4. At test time score each candidate; code takes `argmax_j s_j`, math aggregates scores per distinct answer (weighted vote).
5. Calibrate on one dataset and test on another in the same domain ("we train ... on one dataset and evaluate it on a different dataset from the same domain").

Baselines (Tables 6, 7): "Best CB" = best of four token-confidence aggregates (average trace confidence, bottom-10% group confidence, lowest group confidence, tail confidence; token confidence C_i = -1/k sum log P_i(j) over the top-k tokens); LoRA fine-tuning on the same calibration data; ReasonFlux PRM (1.5B); oracle (any correct candidate).

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Best-of-N acc, Qwen-30B-A3B, MATH-500 -> AIME (Table 6) | 42.4 +/- 5.5 | Best CB 33.3 +/- 3.3; PRM 37.8 +/- 5.1; LoRA not run; oracle 57.8 | AIME 2024/2025, 30 problems each | the "+9.1" headline; sd 5.5 on 30 problems |
| Qwen-30B-A3B, AIME -> MATH-500 (Table 6) | 91.3 +/- 0.5 | Best CB 85.0 +/- 1.6; PRM 88.9 +/- 0.2; oracle 93.2 | MATH-500, 500 | +6.3 |
| GPT-OSS-20B, MATH-500 -> AIME (Table 6) | 89.8 +/- 2.9 | Best CB 93.3 +/- 0.0; LoRA 94.8 +/- 2.4; PRM 92.2 +/- 1.9 | AIME | **-3.5**, SCaTR worst of four |
| GPT-OSS-20B, AIME -> MATH-500 (Table 6) | 95.0 +/- 0.5 | Best CB 94.6; LoRA 94.8; PRM 95.5 | MATH-500 | +0.4, PRM best |
| Qwen-1.7B, MATH-500 -> AIME (Table 6) | 48.9 +/- 3.1 | Best CB 52.2 +/- 5.1; LoRA 50.4; PRM 41.1 | AIME | **-3.3** |
| Qwen-1.7B, AIME -> MATH-500 (Table 6) | 88.3 +/- 0.7 | Best CB 88.1; LoRA 88.9; PRM 87.3 | MATH-500 | +0.2 |
| GPT-OSS-20B, KodCode -> HumanEval (Table 7) | 93.2 +/- 0.6 | Best CB 91.7; LoRA 92.3; PRM 89.8 | HumanEval, 164 | +1.5 |
| GPT-OSS-20B, HumanEval -> KodCode (Table 7) | 86.8 +/- 0.7 | Best CB 83.8; LoRA 85.2; PRM 82.5 | KodCode subset, 1,000 | +3.0 |
| OLMo-2-7B, KodCode -> HumanEval (Table 7) | 35.0 +/- 1.7 | Best CB 31.7; LoRA 37.7 +/- 2.7; PRM 32.9; oracle 73.4 | HumanEval | +3.3; LoRA higher |
| OLMo-2-7B, HumanEval -> KodCode (Table 7) | 33.1 +/- 0.9 | Best CB 27.0; LoRA 32.7; PRM 29.3; oracle 66.7 | KodCode | +6.1, coding maximum |
| Qwen-1.7B, KodCode -> HumanEval (Table 7) | 59.3 +/- 8.1 | Best CB 56.1; LoRA 63.8 +/- 9.2; PRM 60.4 | HumanEval | +3.2; sd 8.1 |
| Qwen-1.7B, HumanEval -> KodCode (Table 7) | 67.1 +/- 12.2 | Best CB 61.3 +/- 11.6; LoRA 68.3; PRM 64.5 | KodCode | +5.8; sd 12.2 |
| Qwen-30B-A3B, KodCode -> HumanEval / HumanEval -> KodCode (Table 7) | 90.4 / 88.2 | Best CB 90.0 / 87.0; PRM 87.6 / 84.6 | | +0.4 / +1.2 |
| Scorer inference latency (Table 2) | 0.18 to 0.20 ms | ReasonFlux PRM 25.2 to 137.4 ms | coding | e.g. 717.2x (GPT-OSS-20B, HumanEval) |
| Trainable parameters | 2.1M to 6.6M (Table 2) | LoRA; abstract claims "up to 8000x fewer" | | exact Table 9 row not verified; one row read as about 6,900x |
| Training compute vs LoRA (Table 8, text) | "up to 150x" less training latency | LoRA | | FLOP units not re-verified |
| Runs | "3 random seeds (32, 42, 52) across 3 training turns", averaged over 9 runs, mean +/- sd | | | sd is across scorer training runs, not candidate resamples (inference) |
| Calibration error of scorer | not reported | | | the "calibrated" in the name is not measured |

## Mechanism details you could implement
- Feature: one vector per candidate, penultimate layer, last non-padding token. Layer ablation (0.15L to 0.9L, L-1; Figure 5 left, Tables 11 to 13): no single layer uniformly best; L-1 has "relatively low variance".
- Scorer: MLP [512,256] class, ReLU, dropout, sigmoid. Table 3: transformer heads over last tokens, task-specific tokens, ensembles and best-layer selection gave no consistent gain: "added architectural complexity does not deliver consistent gains".
- Loss: class-weighted BCE with w = N0/N1; early stopping on validation loss.
- Calibration data: 164 to 1,000 problems x 16 rollouts; subsampling HumanEval to 16%, 41%, 82% "degrades gracefully" (Figure 5 right).
- Selection: argmax for single-answer tasks, score-weighted vote where answers can be grouped.

## Limitations, caveats, counter-evidence
- Paper: "SCaTR requires access to intermediate hidden representations, which restricts its applicability to only open-weight models. Our evaluation focuses on single-turn reasoning tasks; extending the method to multi-turn settings remains an open direction."
- Small test sets: AIME has 30 problems per year; cells with sd 5 to 12 points overlap the baseline.
- Two negative cells in math; LoRA beats SCaTR in 5 of 10 cells where LoRA was run (inference from Tables 6, 7).
- No calibration metric (ECE, reliability) for the scorer's outputs, so its scores should not be used as absolute thresholds without local fitting (inference).
- Candidates are final answers from the same model; ranking retrieved memory items written by others is a different problem (inference).
- No mention of Jev, System One or decision models in the paper.

## Takeaways for tuning a memory stack
- For an open-weight decision model (priority 2 candidates such as Laya or RSI-Jev), a probe on its own hidden state trained on a few hundred of our labeled decisions is a cheap alternative to LoRA fine-tuning; test it against the model's native output probability (inference).
- Keep the scorer simple; bigger heads did not help (Table 3), which matches B13's lesson that a larger battery is not automatically better.
- Expect cross-dataset transfer to be uneven: the same recipe lost 3.5 points on one pairing. Evaluate per stage and per workload.
- Do not treat scorer outputs as calibrated probabilities; fit thresholds locally (B14).

## Open questions
- Does a hidden-state probe on an open-weight decision model beat its native noul/choice probability on memory decisions (write gate, rerank)?
- Does it hold for multi-turn agent trajectories (the paper's own open direction)?
- How many local labels are needed for a stable probe on our decisions (their floor was about 26 problems x 16 rollouts, the 16% HumanEval subsample)?

## Grading and labels
- Directness: medium, direct selection accuracy, but on single-turn answers, not memory.
- Control: high, same pools, four baselines, oracle, ablations, 9 runs.
- Independence: low, authors' own evaluation; ground truth is programmatic (tests, exact match), no LLM judge.
- Reproducibility: high, code and seeds stated.
- Applicability: low, open-weight only, single-turn.
- Strength: paper-ablated.
- Pillars: R4 primary (choosing among candidates with a fitted scorer; calibration). No R9 secondary: the paper does not concern decision models.
- Stage: reranking.
- Priority: none. The priority 1 match term "Jev" appears only in the author's post, not in the paper.
- Tags: hidden-state-probe, mlp-scorer, best-of-n-selection; math, code; read; cost, open-weight-only, calibration.
- Beliefs: supports B14 (fit locally; no calibration metric shown even for a method named "calibrated"); supports B13 (more complex scorers gave no consistent gain, Table 3); B10 not tested (pointwise scoring only, no listwise comparison).
- Contradiction: none against B1 to B25. Contradiction with the 2026-09-28 brief line ("beats confidence-based ranking of candidates by up to 9% on coding and math ... a recipe for Jev-style decision models"): coding maximum is +6.1, math has two losses, and the paper does not discuss Jev.
- Arm-vs-arm test this quarter (no card written): arms A = open-weight decision model native choice/noul probability, B = MLP probe on the same model's penultimate hidden state fit on our labeled decisions; dataset = our labeled rerank or write-gate decisions (a few hundred); metric = recall@1 (rerank) or F1 (write gate) on a held-out split, 3 seeds; margin >= 3 points; kill if < 1 point or worse on any stage; decision changed = whether priority 2 tuning uses probes instead of LoRA; cost M, and only possible if an open-weight decision model is already served. Card recommendation: no card now; revisit when priority 2 self-hosting starts.

## Origin chain
@thecekbote post 2104596681861833156 (co-author; COLM 2026 Efficient Reasoning workshop acceptance; Jev framing) quoting his own 12-part thread -> arXiv 2604.16535v2 -> HTML Tables 2, 3, 6, 7, 8, Figure 5, Limitations. Independence: author self-report; the Jev link is the author's framing, absent from the paper. Numbers read from the HTML through a fetch summariser in two passes; Table 9 (parameter ratio) not independently verified.
