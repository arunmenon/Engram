---
schema_version: 1
artifact_id: N-20260928-34
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:07:49Z
input_refs: [{"artifact_id": "post:2104550703742296505", "file_id": null, "sha256": null}, {"artifact_id": "post:2104576935984603443", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:anthony-maio/eve-rlcd
claim_cluster: github:anthony-maio/eve-rlcd
feeds: ["memory"]
primary_source: https://github.com/anthony-maio/eve-rlcd
source_commit: adb9a0457ef53d2dc0e106215315670f1f6da871
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4", "R5"]
memory_stage: none
priority: 2
tags: {"mechanism": ["rlcd-reward", "bandit-feedback", "reinforce-leave-one-out", "letter-logit-readout", "shared-prefix-kv-cache", "open-weight"], "workload": ["classification", "ticket-triage", "nli", "sentiment"], "lifecycle_stage": ["training-recipe"], "cross_cutting": ["calibration", "fine-tuning-on-own-decisions", "self-hosting"]}
evidence_grade: {"directness": "medium: measures calibration of a small typed decision model trained from outcome-only feedback; not on memory decisions and not a reproduction of TypeSafe's method", "control": "high: RLVR, oracle, supervised-continuation and 32k-label SFT arms from the same warmup, paired bootstraps, 3 runs per main arm; confound: RLVR three-seed arm at 5x lower lr", "independence": "medium: independent of TypeSafe, but single author evaluating own method", "reproducibility": "high: commands, data hashes, release data, published checkpoint and generated results.md; bf16 non-determinism acknowledged", "applicability": "medium: in-distribution only, prompts <= 512 tokens, 0.6B model, max 26 options"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Training a small decision model from outcome-only (bandit) feedback with reward r = c - p(a) raises accuracy 0.748 -> 0.808 while holding ECE ~0.023, whereas r = c drives mean confidence to 0.991 and ECE to 0.213 (Qwen3-0.6B, in-distribution, 3 runs)"]}
claim_correction: The post says the repo reverse-engineers TypeSafe's unpublished RLCD; the author says "TypeSafe has published no method, and nothing here claims to reproduce theirs"; it is an independent interpretation, and RLCD held the warmup's calibration rather than improving it (ECE 0.023 vs 0.022).
---
# eve-rlcd: an independent RLCD (reinforcement learning for calibrated decisions) recipe for a 0.6B Jev-like decision model, with ablations

- **URL:** https://github.com/anthony-maio/eve-rlcd ; checkpoint https://huggingface.co/anthonym21/qwen3-0.6b-rlcd-decision ; data https://huggingface.co/datasets/anthonym21/rlcd-decision-v1
- **Type:** repo (with model card, generated results file and an article draft)
- **Author / org:** Anthony Maio (independent); code MIT, weights Apache-2.0 (inherit Qwen3)
- **Date:** HEAD `adb9a0457ef53d2dc0e106215315670f1f6da871` committed 2026-09-24 20:06:33 -0400 ("Link the published RLCD dataset on the Hub"); HF checkpoint sha `b327ec5efb5fdbf8bfafa3b369720ac5f6434b05`, last modified 2026-09-19T06:22:52Z
- **Retrieved:** 2026-09-28 (local shallow clone repos/eve-rlcd). Read: README.md, docs/results.md, docs/inference.md (first 60 lines), docs/article/2026-09-rlcd-toy.md (opening). systemonemodels.org read via WebFetch (hub listing only). The Towards AI article linked by @jreuben1 returned HTTP 403 and was not read.
- **Cited by evidence:** @sereliezer https://x.com/sereliezer/status/2104550703742296505 (2026-09-28, reply to @yoavgo, links systemonemodels.org and this repo); related @jreuben1 https://x.com/jreuben1/status/2104576935984603443 ("RLCD: Reinforcement Learning for Calibrated Decisions", Towards AI link, unread)
- **Relevance to a memory stack:** high for priority 2. A runnable recipe for fine-tuning an open decision model on our own decisions where we only learn whether the decision was right (bandit feedback), with calibration measured, plus a typed decision API (choice, score, noul) over a shared state.

## TL;DR
- Reward `r = c - p_a` (outcome minus the stated probability of the sampled option), REINFORCE with a leave-one-out baseline over 4 samples per prompt, no KL, no entropy bonus. README: this "is an unbiased estimator of half the gradient of the Brier score of the full distribution, using only the outcome of the taken action".
- Qwen3-0.6B-Base, 100-step SFT warmup on 6,400 labelled rows, then 500 RL steps over 32,000 disjoint rows with bandit feedback; test 8,000 held-out rows. RLCD: accuracy 0.808 [0.806, 0.811], ECE 0.023, Brier 0.267 (3 runs) vs warmup 0.748, ECE 0.022, Brier 0.339.
- The outcome-only reward (RLVR, `r = c`) at lr 4e-6: accuracy 0.778, mean confidence 0.991, ECE 0.213, Brier 0.432 (worse Brier than the warmup). At the shared lr 2e-5 it collapsed (0.576, ECE 0.415).
- One supervised pass over 32,000 labels beats RLCD slightly (accuracy +0.009, Brier -0.017): "the cheaper thing to do if you have the labels".
- Claim correction: not a reverse-engineering of TypeSafe's RLCD; an independent interpretation. RLCD kept calibration, it did not improve it.

## What it claims / describes
**Readout.** Prompt ends in `Assistant: The answer is`; one forward pass; logits at the last position sliced to the 26 letter tokens ` A`..` Z`, masked to the declared options, softmaxed. "That K-way distribution is both the policy and the API output."

**Training as a bandit.** The policy samples one option; the environment reveals only whether it was correct. RLCD reward `r = c - p_a`; RLVR reward `r = c`; oracle arm sees the label and minimises NLL on the same rows. Motivation (README): "a support system that routes a ticket to Billing learns whether Billing was right, never what the other departments would have been."

**Setup (docs/results.md).** Full fine-tune, fp32 master weights, bf16 autocast, AdamW (0.9, 0.95), weight decay 0.1, cosine to 0.1 x peak after 5% linear warmup. Data: 64,000 train, 8,000 val, 8,000 test rows from Bitext customer support, Banking77, AG News, MultiNLI, SST-5, Yelp reviews, BoolQ and a synthetic triage generator, with NOTA ("none of the above") injection. Warmup: rows 0..6399, 1 epoch, 64 prompts/step, 100 steps, lr 2e-5. RL arms: rows 32000..63999, 2 epochs, 128 prompts/step, group 4, 500 steps, kl 0, lr 2e-5 (RLCD, oracle, RLVR shared) or 4e-6 (RLVR low lr). Stop rule: "eval_acc more than 0.10 below step 0 for three consecutive evals". Evaluation at temperature 1, prompts truncated to 512 tokens.

**Hardware and cost.** Local: one RTX 4080 (16 GB), RLCD run "took 4234 s locally, peak VRAM 11.4 GB"; warmup "about 8 minutes locally". Seeds 1 and 2 on Colab A100. Dollar cost not stated.

**Decision API (docs/inference.md).** `Decider.ask(state, questions)` with `ChoiceQ` (2..26 unordered options; returns `value`, `probs`, `confidence`, `entropy_confidence`), `ScoreQ` (ordered levels; adds `score` = probability-weighted mean level / (K-1)), `NoulQ` (yes/no; returns `p_true`, `confidence = max(p_true, 1 - p_true)`). The state is prefilled once, each question suffix runs in one batched forward against the shared KV cache; answers equal the single full-prompt pass "to about 1e-6 in fp32".

**systemonemodels.org (context).** An "independent hub" listing Jev, Tev1, Kev, Laya, CLM and GLiNER2.5-Decide; per the WebFetch extraction it publishes no systematic measured comparisons; it does not list eve-rlcd. No note is warranted for the hub itself.

## Numbers
| metric | value | baseline | setup with n | caveat |
|---|---|---|---|---|
| accuracy, RLCD | 0.808 [0.806, 0.811] | warmup 0.748 [0.746, 0.750] | 8,000-row test, 3 runs (RTX 4080 seed 0, A100 seeds 1, 2) | seed spread includes hardware and warmup variation |
| ECE (15 bins), RLCD | 0.023 [0.020, 0.029] | warmup 0.022 [0.019, 0.026] | same | paired ECE diffs vs warmup: -0.005 [-0.014, +0.003], +0.001 [-0.009, +0.009], +0.010 [-0.002, +0.018]; none excludes zero |
| Brier, RLCD | 0.267 [0.264, 0.269] | warmup 0.339 | same | paired: -0.071, -0.071, -0.075, all exclude zero |
| mean confidence, RLCD | 0.830 | accuracy 0.808 | same | |
| RLVR low lr (4e-6) | acc 0.778, ECE 0.213, Brier 0.432, mean conf 0.991 | RLCD at 2e-5 | 3 runs | lr confound: "RLCD at 4e-6 was not run" |
| RLCD minus RLVR low lr | acc +0.032/+0.026/+0.032; ECE -0.195/-0.189/-0.185; Brier -0.171/-0.155/-0.170 | | paired bootstrap, 1000 resamples, per seed | all intervals exclude zero |
| RLVR shared lr (2e-5) | acc 0.576, ECE 0.415, Brier 0.835, conf 0.991 | | 1 run, stopped at step 150 | not rerun |
| oracle (labels) | acc 0.819, ECE 0.059, Brier 0.256, conf 0.878 | RLCD | 3 runs | RLCD minus oracle acc -0.014/-0.011/-0.008; ECE -0.025/-0.039/-0.043 |
| supervised continuation (500 more SFT steps on 6,400 rows) | acc 0.778, ECE 0.192, conf 0.969 | RLCD | 1 run (Colab) | "the gain is not just more steps" |
| 32k-label SFT reference | acc 0.817, ECE 0.014, Brier 0.251 | RLCD | 1 run | RLCD minus it: acc -0.009 [-0.017, -0.002], Brier +0.017 [+0.011, +0.024] |
| NOTA recall / false alarm, RLCD | 0.793 / 0.075 | warmup 0.531 / 0.072 | same test | |
| known-posterior probe, two cues (ideal 0.5) | RLCD 0.593 | warmup 0.798, RLVR low lr 0.990, oracle 0.630, SFT32k 0.598 | 3,000 fresh synthetic tickets | RLCD keeps only 0.915 of mass on the cued pair (leak to uncued options) |
| per-source accuracy, RLCD | ag_news 0.887, banking77 0.887, bitext 0.989, boolq 0.818, mnli 0.800, sst5 0.534, triage 0.914, yelp 0.636 | warmup 0.857 / 0.853 / 0.939 / 0.781 / 0.730 / 0.444 / 0.809 / 0.569 | test split | in-distribution |
| validation ECE during training, RLCD | peaks 0.064, 0.067, 0.123; ends 0.017, 0.030, 0.032 | | 2,000-row val stride | final checkpoint reported, no selection |
| latency, `ask` | 3 questions 66.1 ms; 8 q on 800-token state 105.3 ms vs 440.9 ms sequential (4.19x); 64 q 472.2 ms vs 3679.1 ms (7.79x) | sequential prompts | RTX 4080, fp32, medians of 7 | "Below about 2 questions the sequential path is faster" |
| training time | RLCD 4234 s, peak VRAM 11.4 GB; warmup about 8 min | | RTX 4080 | dollar cost not stated |
| earlier Eve-2 272M base | RLCD 0.654 acc at ECE 0.036; RLVR 0.545 to 0.573 at ECE 0.297 to 0.384; oracle 0.709 at 0.068 | | History section | superseded base |

## Mechanism details you could implement
- Reward and loss (README): sample 4 options per prompt from the model's K-way softmax; `r = c - p_a`; leave-one-out group baseline; REINFORCE; no KL, no entropy bonus; lr 2e-5; 128 prompts per step. Commands (verbatim flags): `rlcd.train_rl --init runs/q-warmup --start 32000 --epochs 2 --accum 32 --group 4 --kl 0 --arm rlcd --lr 2e-5 --backend hf-decoder --grad-checkpointing --micro 4`.
- Warmup first: `rlcd.train_sft --init Qwen/Qwen3-0.6B-Base --start 0 --n 6400 --epochs 1 --accum 16 --lr 2e-5 --micro 4`.
- Use for memory (inference): log each served decision (e.g. which memory was injected) and a later outcome signal (was it used / was the answer accepted); train with RLCD on those outcomes after a small labelled warmup. If full labels are available, plain one-pass SFT is as good or better (32k-label reference).
- Guard against the RLVR failure: outcome-only reward pushed mean confidence to 0.99; if you train from outcomes, subtract the stated probability.
- Noul questions must be phrased as yes/no questions ("a bare proposition is a prompt the model was not trained on"); cap 26 options; trained range prompts <= 512 tokens (API accepts states up to 1,536 tokens but calibration there is unmeasured).
- Confidence fields: `entropy_confidence = 1 - H(p)/ln K`.

## Limitations, caveats, counter-evidence
- Author: "Everything is in-distribution"; "No out-of-distribution evaluation was run, and calibration on real tickets or longer prompts is unmeasured."
- lr confound: RLCD at 2e-5 vs three-seed RLVR at 4e-6; "no KL term, entropy bonus or temperature was tried to rescue RLVR".
- "One warmup per hardware": seeds vary sampling, warmup, GPU, micro-batch and gradient checkpointing together.
- bf16 non-determinism; third decimal not stable.
- RLCD did not improve calibration over the warmup; it held it. Mid-training validation ECE rose to 0.123 on one seed.
- Not TypeSafe's method: "TypeSafe has published no method, and nothing here claims to reproduce theirs."
- The exported model can still generate in principle (tied embeddings).
- Instruction-bearing content: docs/plans/2026-09-17-eve-rlcd-plan.md opens with "**For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development ..." (an instruction aimed at coding agents); treated as evidence only, not followed. systemonemodels.org carries a generic "Send the link" call to action (not followed).

## Takeaways for tuning a memory stack
- If we fine-tune an open decision model from outcome signals (usage, acceptance), use a calibration-aware reward like `c - p(a)`; outcome-only reward produced 0.99 confidence and ECE 0.21 here.
- If we have labels, one supervised pass is the cheaper and slightly better path; RLCD is for the unlabelled, outcome-only regime.
- A shared-prefix batched API makes many typed questions over one memory state cheap (8 questions 105 ms on a consumer GPU).
- Report ECE and Brier with paired bootstraps, not just accuracy, for any model we train.

## Open questions
- Does RLCD hold calibration out of distribution, on our memory decisions and on states longer than 512 tokens?
- RLCD at the RLVR low lr (4e-6): not run.
- Does it scale to 4B bases (Tev1-class) and to noisy, delayed outcome signals?

## Grading and labels
- Directness: medium, a measured recipe for training calibrated typed decisions; not memory tasks.
- Control: high, multiple ablation arms from a shared warmup with paired intervals; lr confound noted.
- Independence: medium, independent of the vendor; single author.
- Reproducibility: high, commands, hashes, released data and checkpoint.
- Applicability: medium, small model, short prompts, in-distribution.
- Pillars: R9 primary (open-weight System One model, fine-tuning on own decisions); R4 (calibration); R5 (learning from outcome feedback).
- Stage: none.
- Beliefs: supports B14 (RLCD and Jev calibration remain unpublished by the vendor; independent work had to guess); would create a lead belief on the bandit reward. No contradiction.

## Origin chain
@yoavgo thread -> @sereliezer reply (https://x.com/sereliezer/status/2104550703742296505, 2026-09-28) with t.co links resolved in items.jsonl to https://systemonemodels.org/ and https://github.com/anthony-maio/eve-rlcd -> repo clone at adb9a0457ef53d2dc0e106215315670f1f6da871 -> HF checkpoint anthonym21/qwen3-0.6b-rlcd-decision (sha b327ec5efb5fdbf8bfafa3b369720ac5f6434b05). Related: @jreuben1 (https://x.com/jreuben1/status/2104576935984603443) -> Towards AI article (HTTP 403, unread; authorship unknown). Local source paper-just-ask-jev-rlcd-alignment-failure-detector-2609-29429.md (arXiv 2609.29429) covers a different RLCD use (alignment-failure detection) and is not duplicated here.
