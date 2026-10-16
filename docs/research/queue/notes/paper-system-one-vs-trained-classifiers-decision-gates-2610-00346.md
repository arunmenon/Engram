---
schema_version: 1
artifact_id: N-SURVEY-20261004-03
artifact_type: note
producer: triage
run_id: survey-20261004T054506Z-478e
created_at: 2026-10-04T05:55:25Z
idempotency_key: note:survey:arxiv:2610.00346
input_refs: []
pillar_primary: R9
pillar_secondary: [R4, R6]
memory_stage: write_gate
priority: 2
related_notes: [N-20260928-13, N-SURVEY-20260929-08, N-20260930-01]
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: medium (automated decision gates over workflow, intent and social-science decisions; not memory decisions)
  control: high (one harness, same requests to all models, thresholds on disjoint data, paired intervals, frozen inputs with SHA-256)
  independence: high (university authors, no product; Jev and six open families)
  reproducibility: high (harness, frozen inputs, per-request answers and analysis code stated as released; seed 20260924; open checkpoints pinned by commit; URL not captured)
  applicability: medium (the gate pattern matches our write and recall gates; data is not engineering text)
source_url: https://arxiv.org/abs/2610.00346
found_via: survey
---

# Benchmarking System One decision models against trained classifiers and language models for automated decision gates (arXiv 2610.00346)

- **URL:** https://arxiv.org/abs/2610.00346 (HTML v1 read)
- **Type:** paper
- **Author / org:** Amir Rafe, Subasish Das (Texas State University)
- **Date:** 2026-09-29
- **Retrieved:** 2026-10-04 (local copy: `out/log/raw/arxiv-2610.00346.html`)
- **Cited by evidence:** survey question R9-2 (against which alternatives does a System One model win at a gate?)
- **Relevance to a memory stack:** high. It is the first controlled comparison that puts Jev, six open decision-model families, a larger LLM read through option likelihoods, and **small trained classifiers** on the same gate requests. That is the exact comparison the R9 thesis demands.

## TL;DR

- Abstract: "The ranking of the model classes depends on the conditions. With the task's own labels, small trained classifiers are the most accurate on intents and not significantly different from the best decision models on workflows."
- On CLINC-150, a logistic regression on small sentence embeddings reaches **0.948** and fine-tuned BERT-base **0.940**, against Jev's **0.913**. The embedding classifier is better calibrated as shipped (ECE 0.017).
- On typed-decisions workflows: Jev **0.732**, Qwen3.6-27B read through option-key likelihood **0.733**, best open decision model Kev-9B **0.712**, embedding soft-label regressions **0.702**. Without task labels the zero-shot entailment classifier reaches only 0.411.
- A threshold set on held-out data for 5% in-scope risk "still lets Jev accept 0.310 of out-of-scope requests". Swapping yes and no "flips 50.5 answers per hundred for Jev".
- Cascade: "this-that-model-1.0 escalates 0.25 of its decisions to the hosted model and reaches 0.927, against 0.913 for the hosted model alone, at 0.43 of the hosted cost". Only 2 of the 40-plus cascades tested show a gain whose interval excludes zero (from the reader extract; not re-verified).

## What it claims / describes

One harness sends the same semantic requests to eight decision-model checkpoints from six families and to two generative comparators. Supervised and zero-shot classifiers are scored on the same items.

- **Decision models:** Jev 1.13.0 (hosted); Laya English (ModernBERT-large, 421M); Laya multilingual (mmBERT-base, 322M); Kev-0.8B and Kev-9B (Qwen3.5 plus LoRA); decider-2b (Qwen3.5-2B-Base trained on CLINC train); this-that-model-1.0 (1.88B, adapted from decider-2b); Nimble-9B (Qwen3.5-9B plus LoRA).
- **Generative comparators:** Qwen3-14B (AWQ 4-bit, vLLM, L4) and Qwen3.6-27B FP8 (A100), each read both through JSON output and through option-key likelihood.
- **Classifiers:** BERT-base fine-tuned; logistic regression on BGE-small embeddings; DeBERTa-v3 zero-shot.
- **Data:** D1 is the synthetic typed-decisions set (4 workflows, 2,000 test decisions from 400 states). D2 is CLINC-150 (800 utterances, 600 in-scope, 200 out-of-scope). D3 is four social-science sets (derailment, power, emotion, politeness).
- **Hardware:** open models run single-request on a Colab L4 in eager PyTorch. Thresholds and temperatures are chosen on data disjoint from the scored items.

## Numbers

| Metric | Value | Baseline / comparator | Setup | Caveat |
|---|---|---|---|---|
| D1 typed-decisions accuracy | Jev 0.732 | Qwen3.6-27B likelihood 0.733; Kev-9B 0.712; embedding regressions 0.702; Qwen3-14B 0.680; DeBERTa zero-shot 0.411 | 2,000 decisions | Kev-9B vs Jev paired difference interval not captured |
| D1 other open models | Nimble-9B 0.685, this-that-model 0.597, decider-2b 0.588, Kev-0.8B 0.451, Laya English 0.366, Laya multilingual 0.349 | | | from the reader extract of Table 5, whose columns were misaligned. Laya rows are plausible given the 192-token limit (inference) |
| D2 CLINC-150 accuracy | Jev 0.913 | embedding LR 0.948; BERT-base 0.940; Qwen3.6-27B likelihood 0.912; Qwen3-14B 0.728; Qwen3.6-27B JSON 0.683; zero-shot entailment 0.507 | 600 in-scope | classifiers saw out-of-scope examples in training |
| Out-of-scope acceptance at 5% in-scope risk | Jev 0.310 | | held-out threshold | the extract reports 0.195 with an explicit out-of-scope option (not re-verified) |
| Yes/no swap flips per 100 | Jev 50.5 | fine-tuned checkpoints cut their backbones' social-science flips | | the extract reports Laya 91.3 and trained decoders 4.2 to 6.5 |
| Cost and latency | Jev median 138 ms at client, USD 0.0079 per 1,000 decisions at list price (typed-decisions) | Colab L4: Laya multilingual 32 ms to Nimble-9B 2,056 ms; GPU at assumed USD 0.48 per hour | single request | on CLINC-150 the hosted model costs 0.1095 per 1,000, presumably because 150-option prompts are longer (inference; the paper gives both figures in different tables) |
| Cascade on CLINC-150 | 0.927 at 0.43 of hosted cost, 25% escalated | Jev alone 0.913 | out-of-fold threshold | "8 more correct decisions out of 600" |
| Cascade on D1 | held-out threshold escalates 0.01 and returns 0.732 | an in-sample threshold "would report 0.746" | | warns against tuning thresholds in-sample |
| Weak-stage cascade | Kev-0.8B then verbal Qwen3.6-27B reaches 0.738 on CLINC-150 | "5.3 points above either alone and still far below the hosted model" | | |

Judge shared with system: not applicable (gold labels). Text vs table: the hosted cost per 1,000 differs between the D1 table (0.0079) and the CLINC worked example (0.1095). This looks like a workload difference rather than an error, but the paper does not reconcile the two figures in one place.

## Mechanism details you could implement

- **Gate design rules the paper derives:** declare an explicit out-of-scope (or "none") option; use neutral option identifiers rather than meaningful yes/no words; refit the temperature per task and per option count ("Stored temperatures fitted on few options raise calibration error with many options"); set thresholds on held-out data only.
- **Cascade:** a cheap first stage trained on the task, escalating its low-confidence items to the hosted model. The threshold is chosen out of fold.
- **Readout for a general LLM:** score each option key's likelihood instead of asking for JSON. For Qwen3.6-27B this lifted CLINC-150 from 0.683 to 0.912.

## Limitations, caveats, counter-evidence

- The authors flag that decider-2b's temperature pool contains 201 of the 800 test items, and that emotion results are contaminated by training exposure (both from the reader extract).
- Hosted latency is measured at the client, and open-model latency on a single L4 in eager mode. Speed comparisons are therefore not like for like.
- None of the decisions are memory decisions or engineering text. The workflow set is synthetic.
- Several per-model cells came from a misaligned extract and only the cells quoted above with verbatim sentences were re-verified in the HTML: 0.732, 0.712, 0.733, 0.702, 0.948, 0.940, 0.913, 0.310, 50.5, 0.927, 0.43.

## Takeaways for tuning a memory stack

- When we have our own labels for a gate (write gate, link-type choice), the arm that must beat Jev is a **logistic regression on embeddings trained on those labels**, not only a prompted LLM. That arm costs almost nothing to run and keeps memory text in-house.
- When we have no labels, a decision model is clearly better than zero-shot entailment. Jev and a larger open LLM read through option likelihood are level.
- Never trust an in-sample threshold. Add an explicit "none of these" option to every gate.

## Open questions

- On our own write-gate and link-type labels, how many labelled decisions does the embedding classifier need to match Jev? This paper gives a full training split, not a learning curve.
- Does the 0.310 out-of-scope acceptance appear on memory gates, where "store nothing" is the out-of-scope answer?
