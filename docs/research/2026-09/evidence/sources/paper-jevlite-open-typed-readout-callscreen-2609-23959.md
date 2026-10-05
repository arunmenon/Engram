---
schema_version: 1
artifact_id: N-SURVEY-20260928-12
artifact_type: note
producer: triage
run_id: survey-20260928T070101Z-8451
created_at: 2026-09-28T07:21:00Z
idempotency_key: note:survey:arxiv:2609.23959
input_refs: []
pillar_primary: R9
pillar_secondary: [R4]
memory_stage: none
priority: 2
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 3
  control: 3
  independence: 4
  reproducibility: 3
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.23959
found_via: survey
claim_cluster: self-hosted-typed-readout-recipe
---

# Open-Jev Judgments on CallScreenBench: Calibrated One-Pass Scam Screening with a Small Language Model (JevLite)

- **URL:** https://arxiv.org/abs/2609.23959 (HTML read at https://arxiv.org/html/2609.23959)
- **Type:** paper
- **Author / org:** not stated in the extracted text
- **Date:** 2026-09-21
- **Retrieved:** 2026-09-28
- **Cited by evidence:** survey run, R9 question 4 (tuning a decision model on our own decisions)
- **Relevance to a memory stack:** medium. A complete, small, self-hostable recipe for a Jev-style typed read-out trained on about 3,000 of one's own decisions, with an honest comparison showing a plain encoder is nearly as good.

## TL;DR
- JevLite: Qwen3-4B with LoRA (rank 16, alpha 32, dropout .05, all attention and MLP projections), temperature-scaled softmax over two answer-label logits as P(scam). Trained on 3,187 turn-prefix decisions from 40 scenarios.
- Held-out (577 decisions, 41 scenarios): 3-seed ensemble AUROC 97.4%, ECE 5.2%, non-inferior to an LLM judge (MiniMax-M3, AUROC 94.7%) at a pre-registered .02 margin; zero false alarms on 12 legitimate scenarios versus the judge's 82.3% accuracy there.
- Latency 64.5 ms median (p95 110.5 ms) on one RTX 3090, versus 317 ms for the same backbone fine-tuned to generate its answer.
- A fine-tuned ModernBERT-large encoder (AUROC 94.8%, ECE 4.2%) is "not significantly worse". The authors say the gain is in read-out and calibration, not accuracy.
- The recipe was chosen after about ten recipes were scored on the test set (winner's curse admitted).

## What it claims / describes
Typed decision read-out without a vendor: declare the options as label tokens, fine-tune a small generative backbone with LoRA, read the softmax over the option-label logits in one forward pass, fit one temperature per model on validation negative log-likelihood, and average three seeds. Labels come from scenario ground truth plus teacher labels from MiniMax-M3 on train and validation only.

## Numbers
| System | AUROC | Accuracy | ECE | Brier | Latency |
|---|---|---|---|---|---|
| JevLite (3-seed ensemble) | 97.4% | 92.7% | 5.2% | 6.1 | 64.5 ms median, RTX 3090 |
| Single seed (mean of 3) | 97.2% | 92.3% | 4.7% | 6.3 | not stated |
| ModernBERT-large (+aux heads) | 94.8% | 90.6% | 4.2% | 6.9 | not stated |
| Qwen3 fine-tune (label-token, generative) | 95.0% | 89.2% | 5.0% | 8.1 | 317 ms median |
| LLM judge (MiniMax-M3) | 94.7% | 87.0% | 5.4% | 9.5 | about 30x slower at the median |

Training cost and time: not stated. Hosted Jev comparison: none. Release: code, LoRA adapters, per-decision predictions and 82 generated test calls "will be released"; licence not stated. All callers are synthetic.

## Mechanism details you could implement
- LoRA r=16, alpha=32, dropout 0.05 on all attention and MLP projections of a 4B backbone; label-token logits softmax; per-model temperature on validation NLL; 3-seed mean.
- A ModernBERT-large classifier head is the cheaper baseline to beat; it runs on CPU-class hardware (inference).

## Limitations, caveats, counter-evidence
- Test-set exposure during recipe selection; synthetic data; one binary task; no comparison with Jev or Laya.

## Takeaways for tuning a memory stack
- Priority 2 (run our own, tune on our decisions) looks feasible with a few thousand labelled decisions per decision type, one consumer GPU, and sub-100 ms latency, if our decisions are binary and the domain is narrow.
- Always include a fine-tuned encoder arm; here it matched the bespoke recipe within noise.

## Open questions
- How many labelled link or staleness decisions do we need before a fine-tuned encoder matches Jev on our data?
