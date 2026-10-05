---
schema_version: 1
artifact_id: N-SURVEY-20260929-04
artifact_type: note
producer: triage
run_id: survey-20260929T054503Z-ed98
created_at: 2026-09-29T05:59:00Z
idempotency_key: note:survey:arxiv:2609.27678
input_refs: []
pillar_primary: R9
pillar_secondary: [R10, R2]
memory_stage: linking
priority: 1
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 3
  control: 3
  independence: 5
  reproducibility: 4
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.27678
found_via: survey
claim_cluster: system-one-entail-contradict-not-mentioned-decision
---

# Same Scores, Different Decisions: Evaluating JEV and Language Models for Legal Document Understanding (arXiv 2609.27678)

- **URL:** https://arxiv.org/abs/2609.27678 (read: https://arxiv.org/html/2609.27678v1); code https://github.com/ZF-Utokyo/Jev-Benchmark (pinning unknown)
- **Type:** paper
- **Author / org:** Fan Zhang, Yankai Chen, Zhuohan Xie and 11 others (U Tokyo, MBZUAI, McGill, HKBU, Fudan, UIUC, Columbia, HKU, UIC, others); includes Philip S. Yu and Preslav Nakov
- **Date:** 2026-09-23
- **Retrieved:** 2026-09-29
- **Cited by evidence:** survey run, R9 question 2 (pending lead from survey-20260928T070101Z-8451)
- **Relevance to a memory stack:** medium-high. The three-way ContractNLI decision (entailment / contradiction / not mentioned, given a document and a hypothesis) is the same shape as deciding a CONTRADICTS or SUPERSEDES link, or a "still true given the evidence?" staleness check. It is the closest published result to the linking stage for a System One model, and it includes open-weight Qwen3.5 4B and 9B arms.

## TL;DR
- Jev reached 77.38% accuracy (macro-F1 72.23) on the full ContractNLI test set (123 contracts, 2,091 judgments), below every frontier model (78.96 to 83.21) and the open-weight Qwen3.5-9B (79.15), above Qwen3.5-4B (74.22).
- Jev had the highest contradiction recall of all ten models: 77.27% vs 55.00% (Claude Sonnet 5) to 74.55% (GPT-6 Astra). It gives up not-mentioned recall (67.22%, lowest but one).
- Cost per contract: Jev $0.000228 vs Gemini 3.5 Flash-Lite $0.001353 (about 6x), Claude Sonnet 5 $0.011352 (about 50x), GPT-6 Astra $0.091890 (about 400x). Median latency 1.24 s.
- Stability over 4 conditions x 3 repeats on 30 contracts: Jev 23/30 all-correct with only 2 changed-valid answers, among the most stable; open Qwen models changed answers 8 times and produced invalid outputs.

## Numbers

| Model | Accuracy [CI] | Macro-F1 | USD / contract | Median s | Contradiction recall | Not-mentioned recall |
|---|---|---|---|---|---|---|
| Jev 1.13.0 | 77.38 [75.99, 78.81] | 72.23 | 0.000228 | 1.24 | 77.27 | 67.22 |
| Gemini 3.5 Flash-Lite | 82.54 | 76.96 | 0.001353 | 1.60 | 63.18 | 77.85 |
| Gemini 3.1 Pro Preview | 83.21 | 77.71 | 0.008474 | 3.73 | 61.36 | 79.40 |
| GPT-5.6 Luna | 78.96 | 73.77 | 0.000931 | 1.74 | 73.64 | 64.89 |
| GPT-5.6 Terra | 82.59 | 77.23 | 0.011839 | 11.61 | 71.36 | 77.41 |
| GPT-6 Astra | 81.83 | 76.55 | 0.091890 | 20.94 | 74.55 | 70.99 |
| Claude Haiku 4.5 | 79.44 | 74.46 | 0.005396 | 5.65 | 62.73 | 70.43 |
| Claude Sonnet 5 | 82.40 | 76.38 | 0.011352 | 3.27 | 55.00 | 80.40 |
| Qwen3.5-4B (open) | 74.22 (117/123 valid) | 71.67 | 0.053653 | 86.87 | 67.27 | 72.43 |
| Qwen3.5-9B (open) | 79.15 (122/123 valid) | 74.57 | 0.077361 | 134.64 | 73.64 | 74.64 |

Label mix: 968 entailment, 220 contradiction, 903 not mentioned. Entailment recall: Jev 86.88, others 77.48 to 93.60.

Stability panel (30 contracts, 12 runs each): Jev mean correct 79.44, all-12-correct 23/30, same-wrong 5, changed-valid 2, invalid 0. Sonnet 5: 86.67, 24, 1, 5, 0. Qwen3.5-4B: 77.50, 17, 2, 8, 3 invalid.

Dev set (30 contracts, 510 labels): Jev 77.06 acc, 1.25 s, $0.000250; Qwen3.5-4B 78.43 acc, 1.38 s, $0.000783; Qwen3.5-9B 78.63, 2.89 s, $0.001627.

## Mechanism details you could implement
- Three-way typed choice per (document, hypothesis); gold labels only, no LLM judge.
- A contradiction detector that must not miss contradictions (a SUPERSEDES/CONTRADICTS candidate generator) is the place where Jev's profile fits: highest contradiction recall, lowest cost. The not-mentioned class, which maps to "no link", is its weakest.

## Limitations, caveats, counter-evidence
- Authors: "123 contracts and a stability subset of 30 contract targets, all drawn from the same 17 hypothesis types"; "without a human performance comparison, new adjudication, or external-domain validation"; inference settings, wording, hardware and providers differ across models; Sonnet 5, Haiku 4.5 and Terra were added after inspecting earlier results.
- The open Qwen models' cost and latency jump between dev (1.38 s, $0.000783) and test (86.87 s, $0.053653) with no explanation; treat the test-set open-weight cost numbers as a serving artifact, not a property of the models (inference).
- Legal contracts, not engineering records. No pre-registration.

## Takeaways for tuning a memory stack
- First evidence of a System One model on a contradiction-type decision: it is 4 to 6 accuracy points behind frontier models but best at catching contradictions, at one sixth to one four-hundredth of the cost. That favours Jev as a high-recall candidate filter for CONTRADICTS links with an LLM or human confirming, not as the final decider.
- The open 9B model matched GPT-5.6 Luna on accuracy; a self-hosted arm is viable on quality if served properly.

## Open questions
- Does the contradiction-recall advantage hold for two engineering memories (a requirement and a later decision), where "not mentioned" is the dominant class?
