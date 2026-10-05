---
schema_version: 1
artifact_id: N-20260929-05
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104610851197985207", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:shanghua-gao/rsi-jev#v3-listwise-rl-rerank
claim_cluster: github:shanghua-gao/rsi-jev#v3-listwise-rl-rerank
feeds: ["memory"]
primary_source: https://github.com/Shanghua-Gao/RSI-Jev/blob/main/versions/v3.0.md
source_commit: 8f34a4f2afadba288e77905eeeec1f22ac3a0981
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R3", "R5", "R4"]
memory_stage: reranking
priority: 2
tags: {"mechanism": ["listwise-rl-ndcg-reward", "plackett-luce-sampling", "post-hoc-confidence-head", "per-candidate-rerank"], "workload": ["longmemeval", "hippo-memory-retrieval", "typed-decisions-suite"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: release notes and rl.md report the reranking table, paired counts and McNemar p directly", "control": "medium: v3.0 is compared with its own supervised parent and with no-rerank, but the RL-vs-SFT control is one seed on a different parent", "independence": "low: author-built model, author-built reranking corpus and evaluation, one lab", "reproducibility": "high: pinned commit, public checkpoint, corpus manifest with sha256, per-question verify files; the rerank corpus builder was not re-run end to end", "applicability": "medium: memory reranking on LongMemEval via hippo-memory is close to our read path, but chat memory, not engineering artifacts, and documents over 2,048 tokens are silently cut"}
beliefs_affected: {"supports": ["B14", "B11"], "contradicts": [], "would_create": ["An open-weight per-candidate decision-model reranker can score below the retriever's own order (R@1 0.308 vs 0.484 on LongMemEval via hippo-memory), so every reranker arm needs a no-rerank control"]}
claim_correction: The post says v3.0 finds the right memory first 60% more often with no regression elsewhere; the release shows +60% only against its own supervised parent (R@1 0.192 to 0.308), still well below no reranking at all (hippo's own order, R@1 0.484), with a suite cost of 0.0028 and 0.009 on MMLU-Pro.
---

# RSI-Jev v3.0: listwise RL finally beats supervised training for memory reranking, but the reranker still loses to no reranking

- **URL:** https://github.com/Shanghua-Gao/RSI-Jev (release notes `versions/v3.0.md`, RL write-up `docs/rl.md`)
- **Type:** repo (open-weight 2B typed-decision model, a Jev-style "System One" model, with training code and release notes)
- **Author / org:** Shanghua Gao (GitHub Shanghua-Gao; the "AutoScientists" research loop). Checkpoint on Hugging Face `shgao/rsi-jev-v3.0-qwen3.5-2b`.
- **Date:** release v3.0, docs dated 2026-09-28
- **Retrieved:** 2026-09-29, commit `8f34a4f2afadba288e77905eeeec1f22ac3a0981` (2026-09-28 12:33:44 -0400, "Merge pull request #6 from Shanghua-Gao/explore-data15-fix"), shallow clone in `repos/rsi-jev`. Read: `versions/v3.0.md`, `docs/rl.md`. Not read: code under `rsijev/`, `scripts/` (not executed).
- **Cited by evidence:** @GaoShanghua, https://x.com/GaoShanghua/status/2104610851197985207 ("RSI-Jev v3.0 is out, and this is the first version where RL actually helped ... find the right memory first 60% more often on a long-memory benchmark, with no regression elsewhere")
- **Relevance to a memory stack:** high. It is the most detailed public record of training an open-weight Jev alternative for the reranking stage, and its own numbers show the reranker scoring below the retriever's native order: a direct warning for any plan to put a decision model at the rerank stage without a no-rerank control.

**What is new relative to the existing bus note** (`note:github:shanghua-gao/rsi-jev`, filed for v2.1): the v3.0 release, a listwise RL stage aimed at reranking, the first LongMemEval reranking table for this model line (including the no-rerank baseline), a controlled 7-arm reconstruction of TypeSafe's undisclosed RLCD training, and the documented meaning of the `confidence` field.

## TL;DR
- **Claim correction.** "+60% right memory first" is v3.0 against its own supervised parent: hippo per-candidate R@1 0.192 to 0.308 on 500 LongMemEval questions. Hippo-memory's own retrieval order scores **0.484** R@1 and **0.752** R@5, so reranking with v3.0 (0.308 / 0.626) is **worse than not reranking**. The release states this itself (Section 6, "hippo's own retrieval order (0.484) is still ahead"). "No regression elsewhere" is slightly overstated: suite -0.0028, MMLU-Pro -0.009.
- RL beat supervised fine-tuning only when the reward carried information the labels lack: an NDCG@5 listwise reward over 16 candidates, +0.052 R@1 over pointwise SFT on the same rows (36 wins, 10 losses, z 3.9; one seed, different parent). Ten other RL setups (59 reward-trained arms in total) lost to or tied their SFT controls.
- On labelled per-item decisions, every RL reward made raw calibration worse; a cheap post-hoc confidence head brought all but one arm back to ECE 0.02 to 0.03, so "RL for calibration" disappears after a post-hoc fit.
- The API `confidence` is not the probability: it is Jev's peak statistic `(K * p_max - 1) / (K - 1)`; the release says to route on the probability of the option you act on (corroborates B14 and the separate harrisonsec calibration note from this run).
- Operational hazards for self-hosting: documents over 2,048 tokens are cut from the start silently (a query placed first is lost), structured criteria are rejected with 422, and `--accept-model` lets it answer requests naming `jev-1.13.0`.

## What it claims / describes
**Model.** Qwen3.5-2B-Base tower with an option scorer: "one forward pass, one probability per option, no generated text" (`docs/rl.md` line 12 to 13). Question types `noul`, `choice`, `score`, as in Jev.

**Training (v3.0.md Section 2).**
1. Stage 1, supervised, 16,416 steps: soft cross-entropy, bottom 8 of 24 layers at one tenth the learning rate; 266,131 questions from 36 sources (one in ten held out by hash of case id); a two-layer MLP combining option and cross-attention features (+0.002 on the suite alone); up to 160 options per question.
2. Stage 2, listwise reranking RL, 1,500 steps: for each query the scorer gives each of 16 candidates a relevance probability; 16 rankings are sampled from the Plackett-Luce distribution; each earns NDCG@5; REINFORCE with a leave-one-out baseline and a KL penalty (beta = 0.1) toward stage 1; supervised replay mixed into every step. RL data: 1,000 queries of 20 to 40 candidates from the train splits of MS MARCO, TopiOCQA and FiQA with BM25 hard negatives; "It never touches LongMemEval".
3. Confidence head refit on 9,862 held-out questions after dropping 534 whose document text also appears in a trained case; "It rescales each question's probabilities without changing which option wins."

**The RL search (docs/rl.md "What we tried").** Eleven setups, each against an SFT control on the same items and steps; only listwise reranking cleared its pre-registered bar. Their explanation: with a gold label, a reward built from it adds no information (the expected policy gradient equals a supervised gradient; with a KL anchor the optimum is closed-form `p* ∝ p_ref · exp(r/β)`), and a correctness reward on a sampled option pushes probabilities to 0/1.

**Reconstructing TypeSafe's RLCD.** TypeSafe describes Jev's training as RLCD (Reinforcement Learning for Calibrated Decisions) and "has not published how it works". The author ran one matrix (same checkpoint, a 13.8k-question slice, 1,500 steps per arm) over public reconstructions. Bandit RLCD "was killed by its pre-registered test". Their conclusion: Jev's RLCD, if it works, needs feedback labels do not contain, a separate confidence channel with its own gradient, or an effect on ordering of confidence.

**Error audit.** 680 wrong answers: lacks the knowledge 39%, question genuinely ambiguous 35%, prior bias 13%, gold label wrong 11%, input truncated 2% (`docs/rl.md` "What moved the model instead"). "Data did" move the model: suite 0.61 (v1.0) to 0.76.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| hippo per-candidate R@1 | v3.0 **0.308** | SFT parent 0.192; v2.1 0.186; **no reranking (hippo's own order) 0.484** | LongMemEval through hippo-memory retrieval, "500 questions, 40 candidates each, no prompt truncated" (v3.0.md 4.3) | reranker below no-rerank |
| hippo R@5 | v3.0 0.626 | parent 0.552; v2.1 0.512; no reranking 0.752 | same | same |
| RL vs parent, paired | "64 questions won, 6 lost, exact McNemar p = 2.4 × 10⁻¹³" | parent | same 500 | no matched SFT control for v3.0 itself |
| listwise RL vs pointwise SFT, same rows | R@1 0.246 vs 0.194 (+0.052, "36 wins, 10 losses, z 3.9"); R@5 0.614 vs 0.574 | parent 0.140 / 0.494 | 500 hippo-memory questions (rl.md table "Rewards labels can't express") | "one seed", "different parent from v3.0's" |
| same, with KL gate on | "+0.014" | | first run; gate skipped 49 to 83% of steps | superseded by rerun |
| whole-packet RL (document splitting) | packets split exactly 0.96 | packet SFT 0.97 | rl.md | no win |
| 15-benchmark suite mean | 0.756 | v2.1 0.736; v1.0 uncalibrated 0.622 | v3.0.md 4.2 | "none of these numbers is zero-shot": 10 of 15 benchmarks contribute training data |
| RL stage cost on suite | -0.0028 | parent | v3.0.md 4.2 | inside the allowed -0.003 |
| MMLU-Pro 1k | 0.364 | parent 0.373; v2.1 0.383 | v3.0.md table 3 and 4.2 | |
| suite ECE (after head / before) | 0.066 / 0.101 | v2.1 0.059 | v3.0.md 4.4 | held-out set 0.063 / 0.154; typed-decisions 0.091, MMLU-Pro 0.144, JevBench 0.129 |
| RLCD matrix, suite top-1 | SFT continuation 0.756; binary RL 0.751; Laya-style proper-score RL 0.586; RLCR 0.757; bandit RLCD 0.749; SFT on bandit feedback 0.755 | SFT continuation | 13.8k-question slice, 1,500 steps each (rl.md) | ECE raw/after head: SFT 0.060/0.020, binary 0.143/0.029, Laya-style 0.371/0.364, RLCR 0.129/0.029, bandit 0.140/0.027 |
| AURC, best objective vs parent | "AURC -0.002 (0.6 SE)" | parent | act/defer and confidence-ranking objectives | not significant |
| pure-chance items, mean prob on picked option | v3.0 0.480; v2.1 0.422 | truth for a fair die 0.17; rl.md reports Jev 0.83 on one die probe | 240 dice-style items (v3.0.md 4.4) | RL stage sharpens unknowable answers |
| negation consistency P(q)+P(not q) | v2.1 "about 0.65"; Jev "about 0.98" | ideal 1.0 | "an external probe" (rl.md) | v3.0 not reported |
| bundling independence | 0 flips / 640 | one question at a time | 16 questions on one document | holds |
| cross-GPU reproduction | typed-decisions 1.0000; MMLU-Pro 0.9990 on Blackwell | H200 original | verify.json, verify_blackwell.json | read MMLU-Pro as +/-0.001 |

## Mechanism details you could implement
- **Listwise reward for a reranker:** sample K rankings from Plackett-Luce over per-candidate probabilities, reward each with NDCG@5, REINFORCE with leave-one-out baseline, KL beta 0.1 to the SFT parent, supervised replay mixed in. Useful only when you train your own decision model on reranking data.
- **Do not use a tight KL gate:** "a KL gate tight enough to protect the parent (0.05) disables RL whenever the data is a new row type".
- **Calibrate post hoc, not with RL:** refit a confidence head on a held-out split with leaked documents removed (534 of about 10k dropped here). It rescales without changing the argmax.
- **Route on probability, not `confidence`:** `confidence = (K * p_max - 1) / (K - 1)`; it is a peak statistic over K options, not a calibrated probability of the chosen option (v3.0.md Section 5).
- **Self-hosting checks before use:** state longer than 2,048 tokens is truncated from its start; put the query last or keep state short. Structured criteria objects return 422. `--accept-model NAME` serves requests pinned to `jev-1.13.0` (a drop-in, but the answer names this model).
- **Regression probes worth copying into our own eval:** distinct P(true) over 360 yes/no questions (no ties), bundled-vs-single flip count, pure-chance sharpness, P(q)+P(not q).

## Limitations, caveats, counter-evidence
- The release's own Section 6: RL evidence is one seed; v3.0 has no matched SFT control; benchmark scores are not zero-shot; documents over 2,048 tokens lose their beginning; the rerank corpus builder was not re-run end to end; "One model, one size, one seed."
- v2.1 weaknesses carried over: leans to the more severe or expensive option on ordered choices, rarely picks "unknown" when the document cannot answer, inconsistent on negations. "Do not use it where an 'unknown' option has to be honoured without checking it on your own data."
- The reranker is scored per candidate (one relevance probability each), not with a single listwise `choice` call over the pool as Hindsight does with Jev (B10). The 0.308 vs 0.484 gap may be partly a per-candidate readout effect (inference).
- The Jev comparison numbers in rl.md (die 0.83, negation 0.98) come from probes that are not described in the files read.
- Counter-evidence context: the synthesis records Hippo's opt-in Jev reranker lifting R@1 from 0.41 to 0.62 on a private 300-query set. Here, on public LongMemEval through the same hippo retrieval, a 2B open-weight decision model lowers R@1 from 0.484 to 0.308 (different model, different set; not a contradiction of the Jev result).

## Takeaways for tuning a memory stack
- Any reranker arm (Jev, an open-weight decision model, a cross-encoder) must be compared with the retriever's own order at matched candidates; here the "improved" reranker is 0.176 R@1 below doing nothing.
- If we self-host a decision model for reranking (priority 2), expect to train it on reranking data with a listwise objective; pointwise SFT on per-item relevance leaves it far below the retriever.
- Calibrate our own decision model with a post-hoc head on held-out data; do not expect RL to deliver calibration.
- Never route on the `confidence` field of a Jev-compatible API; log and threshold the option probability.
- Keep reranker state under 2,048 tokens or put the query at the end when serving this line of models.

## Open questions
- What does v3.0 score with a single listwise `choice` over the 40 candidates instead of per-candidate scoring?
- How does Jev itself score on the same 500 x 40 hippo set against 0.484?
- Does fusing the decision-model score with the retriever score (instead of replacing the order) beat 0.484?
- How were the 500 LongMemEval questions and 40 candidates selected (`scripts/build_hippo_rr.py`, not read)?

## Grading and labels
- Directness: high; the release reports the reranking table, paired win/loss counts and test statistic.
- Control: medium; parent and no-rerank baselines on the same 500 questions, but the RL-vs-SFT control is one seed on a different parent.
- Independence: low; author's model, corpus, evaluation and write-up.
- Reproducibility: high; pinned commit, public weights, manifests with sha256, cross-GPU verification; one builder not re-run.
- Applicability: medium; memory reranking on LongMemEval, but chat memory and a 2,048-token limit.
- Strength: repo-pinned.
- Pillars: R9 primary (open-weight System One model at the reranking stage); R3, R5 (RL from a reward the labels lack), R4 secondary. Memory stage: reranking. Priority 2.
- Tags: listwise RL, Plackett-Luce, post-hoc confidence head, per-candidate rerank; LongMemEval, hippo-memory; cost.
- B14 supports: `confidence` is a peak statistic, RL worsened raw calibration, and a post-hoc head is needed; calibration has to be fitted locally.
- B11 supports (weakly): a decision-model rerank stage can lose gold evidence relative to the retriever's order.
- B10: no direct bearing (per-candidate scoring by a different model; not listwise Jev).
- Would create: "An open-weight per-candidate decision-model reranker can score below the retriever's own order (R@1 0.308 vs 0.484 on LongMemEval via hippo-memory), so every reranker arm needs a no-rerank control."
- Contradiction rows: none with a held belief.

## Origin chain
- Post @GaoShanghua 2104610851197985207 (2026-09-28) -> repo Shanghua-Gao/RSI-Jev at `8f34a4f` -> `versions/v3.0.md` Sections 2, 4.2, 4.3, 4.4, 5, 6 and `docs/rl.md` tables "What we tried", "Reconstructing Jev's RLCD", "Rewards labels can't express" -> this note.
- Independence: same author and loop as the earlier bus note on v2.1; the hippo-memory retrieval is kitfunso/hippo-memory (also a local source note, `github-kitfunso-hippo-memory.md`); the Laya-style arm reconstructs Laya's published objective, not Laya itself. No outside replication.
