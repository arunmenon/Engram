---
schema_version: 1
artifact_id: N-SURVEY-20260927-02
artifact_type: note
producer: triage
run_id: survey-20260927T044739Z-8de9
created_at: 2026-09-27T04:53:14Z
idempotency_key: note:survey:arxiv:2606.15621
input_refs: []
pillar_primary: R1
pillar_secondary: [R5]
beliefs_affected:
  supports: []
  contradicts: [B1]
  note: same qualification as N-SURVEY-20260927-01; adds the positive result that batch-invariant kernels remove the noise on self-hosted inference
evidence:
  directness: 3
  control: 4
  independence: 4
  reproducibility: 4
  applicability: 2
  scale: 1-5, 5 best
source_url: https://arxiv.org/abs/2606.15621
found_via: survey
---

# Re-feeding Is Not Replaying: Measuring Replay Noise in Counterfactual Token-Credit Estimation

- **URL:** https://arxiv.org/abs/2606.15621 (HTML read at https://arxiv.org/html/2606.15621v1)
- **Type:** paper
- **Author / org:** Nils Matteson
- **Date:** 16 Jun 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, R1 replay question; also bears on R5 credit assignment
- **Relevance to a memory stack:** medium. It quantifies how far a "replay" of an LLM continuation drifts from the original on stock serving engines, and shows batch-invariant kernels drive that to zero.

## TL;DR
- Replaying from a fixed prefix by re-feeding it to the model is not the same as resuming the original decode state; on stock engines the resulting estimates differ well above a same-state replica floor.
- Excess disagreement over the replica floor: 14 to 28 percentage points (problem-clustered t = 2.9 to 6.4).
- "Two bit-identical request batches, submitted seconds apart with identical seeds, disagree on 9-23% of eligible per-pivot estimates and diverge on 2-14% of greedy probes."
- With batch-invariant kernels, disagreement was 0.0 % (n = 106).
- Averages are mostly safe (bias consistent with mean zero); selections made by thresholding are not.

## What it claims / describes
Counterfactual token credit: cut a transcript at a pivot token, substitute an alternative, replay continuations, compare outcomes. "Re-feeding" recomputes the prefix; "exact-resume" restores the decode-time state. The paper measures how often the two give different credit estimates, against a floor measured by running the exact-resume procedure twice.

## Numbers

Table 1 (verbatim):

| Configuration | Model | n | Re-feed (pol.) | Floor (pol.) | Excess | t_clust | z |
|---|---|---|---|---|---|---|---|
| Main pooled (t=.7, K=4) | Qwen2.5-7B-Inst | 636 | 33.8% (3.9) | 15.1% (1.1) | +18.7 | 5.51 | 8.61 |
| K=8 | Qwen2.5-7B-Inst | 490 | 35.7% (4.9) | 10.4% (1.0) | +25.3 | 6.36 | 9.68 |
| K=16 (10 prob.) | Qwen2.5-7B-Inst | 239 | 36.8% (5.9) | 23.0% (5.9) | +13.8 | 2.87 | 3.71 |
| Greedy cont. (t=0, K=1) | Qwen2.5-7B-Inst | 189 | 40.2% (0.5) | 13.8% (0.0) | +26.5 | 3.64 | 5.66 |
| GRPO ckpt (t=.7, K=4) | SimpleRL-Zoo-7B | 373 | 35.4% (3.8) | 9.1% (1.1) | +26.3 | 5.50 | 8.66 |
| Phi-4-mini (t=.7, K=4) | Phi-4-mini | 370 | 48.6% (6.2) | 20.8% (3.0) | +27.8 | 3.47 | 7.79 |
| Batch-invariant kernels | Qwen2.5-7B-Inst | 106 | 0.0% | 0.0% | 0 | n/a | n/a |

Other quoted results:
- "Resuming the decode-time state reproduces the first post-pivot token's logprob exactly (delta =0.0) at 61-94% of pivots across configurations, while re-feeding does so at 2.6-5.7%."
- "Probe sequences diverge within 32 greedy tokens at 22.8% of pooled pivots under re-feed versus 7.9% for the replica."
- Critical-token selection overlap (Jaccard) under re-feed vs exact-resume: 0.34 to 0.90, against replica ceilings 0.63 to 0.96.
- Strict polarity reversals: 0.5 to 6.2 % under re-feed vs 0 to 5.9 % floors.
- Pooled bias -0.011 (t = -1.23, 95 % CI [-0.029, +0.006]).

Cost and latency: not stated. Engines: "stock-engine configurations"; a first-pass summary mentioned vLLM and SGLang but this was not confirmed against the table text, so treat engine names and versions as unknown.

## Mechanism details you could implement
- If Engram ever needs re-execution replay (not artifact replay), serve the replaying model self-hosted with batch-invariant kernels; the paper's own row shows 0.0 % disagreement.
- Any procedure that selects items by threshold on a replayed score (e.g. "which memories contributed", H4 attribution) is fragile under replay noise even when averages are unbiased.

## Limitations, caveats, counter-evidence
- 7B-class open models only; no hosted frontier APIs.
- The task is token-level credit, not agent decisions; the transfer to agent-level replay is by analogy (inference).
- Batch-invariant row has n = 106 only.
- Code repository referenced in the PDF extraction as github.com/thaw-ai/thaw; not verified.

## Takeaways for tuning a memory stack
- Replaying "the same prompt" is not replaying the decision. Store model outputs in the receipt.
- Counterfactual attribution of outcomes to served memories (leave-one-out reruns) will carry 9 to 23 % run-to-run disagreement on stock engines; use batch-invariant inference or large replica counts when attribution results gate reinforcement (R5, H4).

## Open questions
- Size of the effect on hosted APIs where batch composition is uncontrolled (DFAH, N-SURVEY-20260927-01, suggests it is larger at the decision level).
