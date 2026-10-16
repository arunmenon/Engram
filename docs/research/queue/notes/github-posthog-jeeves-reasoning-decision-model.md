---
schema_version: 1
artifact_id: N-20260930-05
artifact_type: note
producer: triage
run_id: triage-20260930T014506Z-8351
created_at: 2026-09-30T01:57:27Z
input_refs: [{"artifact_id": "post:2105007388151681393", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:posthog/jeeves
claim_cluster: github:posthog/jeeves
feeds: ["decision"]
primary_source: https://github.com/PostHog/jeeves
source_commit: f04ec5567301450dcaae0210dd54deeb4f647f87
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4"]
tags: {"mechanism": ["reasoning before a pointer-head decision", "SFT plus CISPO RL", "temperature calibration on dev", "diffusion drafter speculative decoding", "Jev-compatible API"], "workload": ["classification", "policy decisions", "knowledge questions"], "lifecycle_stage": ["routing", "reranking", "write_gate"], "cross_cutting": ["cost"]}
memory_stage: none
priority: 2
evidence_grade: {"directness": "high: README tables report accuracy per benchmark for Jeeves, Jev and Kev on public items", "control": "medium: same public JevBench items for all three, but outside JevBench the Jev and Kev columns are numbers published by Kev on different items from the same sources", "independence": "medium: PostHog author, no TypeSafe tie; Jev numbers partly second-hand from Kev", "reproducibility": "high: pinned commit, MIT licence, training code, pinned dataset revisions, released 9B weights", "applicability": "medium: 9B model needs an H100 and 3.3 s median with thinking; too slow for per-turn memory gates, plausible for offline linking or consolidation (inference)"}
beliefs_affected: {"supports": ["B13"], "contradicts": [], "would_create": ["An open-weight 9B Jev-compatible model that reasons before deciding scores above hosted Jev on public JevBench (0.935 vs 0.866) but below it on knowledge questions and costs about 10x Jev's latency with thinking"]}
claim_correction: The post says "reasoning improves Jev-like decision models"; the repo shows it improves some tiers (JevBench hard 0.865 vs Jev 0.730) and worsens others (MMLU 0.793 vs 0.900, transfer overall 0.746 vs 0.800), at 3.3 s median and 17.1 s p90 latency with full thinking.
---

# Jeeves (PostHog): an open 9B Jev-compatible decision model that reasons before it decides

- **URL:** https://github.com/PostHog/jeeves (weights: https://huggingface.co/PostHog/jeeves)
- **Type:** repo (training code, eval code, released weights)
- **Author / org:** Nicholas P. Waltz, PostHog (citation block). MIT licence.
- **Date:** commit read `f04ec5567301450dcaae0210dd54deeb4f647f87` (2026-09-29 12:52:23 +0100, "remove expandable segments allocator")
- **Retrieved:** 2026-09-30 (local copy: repos/jeeves, shallow clone). Read: README.md. Code not executed.
- **Cited by evidence:** decision feed 2026-09-29, @iamwil (https://x.com/iamwil/status/2105007388151681393); decision digest 2026-09-30 "The competitor field widens".
- **Relevance to a memory stack:** medium. A self-hostable, Jev-API-compatible decision model with published calibration (ECE) and a reasoning knob; relevant to priority 2 (running the decision model in-house).

## TL;DR
- Qwen3.5-9B + LoRA (r=16) + a pointer head that scores each option; reasons in a `<think>` block, then re-reads the question and decides at a `<decide>` token. Softmax over option scores divided by a dev-fitted temperature.
- Test overall (out-of-domain and held-out): Jeeves 0.889 vs Jev 0.857 vs Kev-9B 0.822. JevBench public (231 items): 0.935 vs Jev 0.866. JevBench hard (111): 0.865 vs Jev 0.730. ECE on public JevBench: 0.037 vs Jev 0.049.
- Worse than Jev on knowledge and transfer: MMLU 0.793 vs 0.900; MMLU-Pro 0.739 vs 0.840; transfer overall 0.746 vs 0.800.
- Latency on one H100: about 0.3 s without thinking, 3.3 s median / 17.1 s p90 with full thinking; `max_think 768` + `nothink_threshold 0.9` gives 0.806 accuracy at 2.0 s / 5.6 s on 325 dev questions.
- Same request shape as Jev (`POST /v1/systemone`, noul / choice / score), plus a drop-in Python SDK.

## What it claims / describes
Problem statement (README): "Jev-like models give calibrated decision probabilities, but at low accuracy. A lot of pipelines therefore rely on a reasoning model as a fallback." Jeeves trains the reasoning into the decision model.

Prompt layout: `<state> ... <q> instructions <opt> option 1 </opt> ... <think>`, reasoning chain, then `</think>` and the question repeated, then `<decide>`. The pointer head scores each option as a scaled dot product between a query projection at `<decide>` and a key projection at that option's `</opt>`. Special markers use rare Qwen tokens (`<|fim_prefix|>`, `<|fim_middle|>`, `<|box_start|>`, `<|box_end|>`, `<|fim_suffix|>`); "Ablations found that using plain text like 'State' in the prompt instead worsened performance. Likewise, not repeating the questions after the reasoning block also decreases performance."

Training: SFT 2 epochs, 596 steps on 8 GPUs, 19,126 questions from 12 public datasets plus synthetic policy data, half with a reasoning chain sampled from the base model. CISPO RL: 9,992 questions, 8 rollouts each at temperature 1, 2,560-token thinking cap, a 624-step schedule stopped at step 402 ("keeps the best calibration and dev score. Past it, the head over-sharpens"). Calibration: one temperature fitted on dev. Diffusion drafter (block 4) speeds chain decoding 109 to 176 tokens/s for one question, about 960 tokens/s total for eight batched.

## Numbers
Accuracy with thinking, greedy, 2,560-token cap. "The Kev-9B and Jev columns are the numbers Kev publishes."

| bench | Kev-9B | Jev | Jeeves |
|---|---|---|---|
| Test overall (out-of-domain and held-out, item-weighted) | 0.822 | 0.857 | **0.889** |
| Transfer overall (MMLU-Pro and buried state) | 0.579 | **0.800** | 0.746 |
| JevBench overall (231 public items) | 0.715* | 0.866 | **0.935** |
| QNLI | 0.925 | 0.925 | 0.913 |
| SciQ | 0.963 | 0.988 | 0.991 |
| TweetEval offensive | 0.775 | 0.813 | 0.813 |
| PAWS | 0.763 | 0.788 | **0.875** |
| MMLU | 0.738 | **0.900** | 0.793 |
| Emotion | 0.600 | 0.588 | 0.647 |
| Held-out rule structures | 0.896 | 0.885 | **1.000** |
| Contrastive policies | 0.900 | 0.963 | **1.000** |
| MMLU-Pro (10-way) | 0.515 | **0.840** | 0.739 |
| Buried state | 0.740 | 0.700 | 0.759 |
| Unknowable answered at p >= 0.9 (lower is better) | **0.000** | 0.090 | 0.055 |
| JevBench hard (111 public items) | 0.451* | 0.730 | **0.865** |
| JevBench ECE (public items) | | 0.049 | **0.037** |

\* Kev-8B (Qwen3), no Kev-9B JevBench result published. Without thinking the same checkpoint scores 0.804 on the test split (2,962 items) vs 0.840 with it (note: this 0.840 differs from the 0.889 "Test overall" row; the README does not reconcile them, perhaps different weighting; unknown).

| setting (325 dev questions) | accuracy | mean reasoning tokens | median / p90 latency |
|---|---|---|---|
| full thinking | 0.825 | 1,138 | 3.3 s / 17.1 s |
| max_think 768, nothink_threshold 0.9 | 0.806 | 344 | 2.0 s / 5.6 s |
| no thinking | 0.775 | 0 | about 0.3 s |

## Mechanism details you could implement
- Two-speed decision: answer without thinking, and think only when the no-think confidence is below a threshold (`nothink_threshold 0.9`). This is the escalation-tier pattern inside one model.
- Repeat the question after the reasoning block before reading the decision; use dedicated marker tokens for state, question, option and decide positions.
- Fit a single temperature on a dev split and store it with the checkpoint; stop RL at the step with the best dev calibration.
- Jev-compatible server (`python -m inference.serve ... --port 8009`) and SDK (`jeeves_sdk.TypeSafeClient`) make it a candidate for a swap test behind a Jev client.

## Limitations, caveats, counter-evidence
- README limitations: knowledge questions trail Jev; slow tail with thinking (17 s p90); "The Kev and Jev comparisons outside JevBench use different items from the same sources"; no language-consistency reward, so chains are hard to interpret.
- The sealed JevBench judge tier is not included.
- Needs a CUDA GPU (FP8 kernel on Hopper). Example response shows 8,141.6 ms latency and 1,536 reasoning tokens for three questions.
- Author-run evaluation only; no independent replication. The example response is low-confidence (choice confidence 0.19), showing reasoning does not guarantee decisiveness.

## Takeaways for tuning a memory stack
- For offline stages (nightly linking, consolidation decisions, trace-link proposals) a reasoning decision model may be worth its latency; for per-turn gates it is not (inference from 3.3 s median).
- If we self-host, the no-think path (0.775 on dev at about 0.3 s) is the fair comparison to Jev at similar latency.
- Watch "unknowable answered at p >= 0.9": Jev 0.090, Jeeves 0.055, Kev 0.000. It is a direct measure of confident wrong answers on unanswerable items, useful for recall gates.

## Open questions
- Jeeves vs Jev on our own decisions (link / no link, supersedes / not), no-think and with thinking, including repeat-call determinism (local greedy decoding should be deterministic; inference).
- Why does "Test overall" read 0.889 in one table and 0.840 in the text?

## Grading and labels
- Directness high; control medium; independence medium; reproducibility high; applicability medium.
- Pillars: R9 primary (which System One model; open-weight alternative), R4 (escalation and abstention). Memory stage: none (generic decision model). Priority 2.
- Beliefs: supports B13 in spirit (more compute per decision is not automatically better: reasoning helps hard JevBench items and hurts knowledge items). Would create the belief stated in frontmatter.
- Contradiction rows: none. Existing catalogue: JevBench notes (`url:benchmarkheaven.com/jev-models`, `#v1-5`) report the benchmark this repo uses; Kev (jaredpalmer/kev) is not yet noted.

## Origin chain
@iamwil post (2105007388151681393) -> github.com/PostHog/jeeves at f04ec55 -> README Results table, Options table, Training and Limitations sections -> this note. Independence: PostHog author; Jev and Kev columns partly copied from Kev's published numbers; JevBench is a third-party benchmark (Benchmark Heaven).
