---
schema_version: 1
artifact_id: N-SURVEY-20261001-04
artifact_type: note
producer: triage
run_id: survey-20261001T054505Z-09ae
created_at: 2026-10-01T06:10:00Z
idempotency_key: note:survey:arxiv:2609.37647
input_refs: []
pillar_primary: R9
pillar_secondary: [R4, R6]
memory_stage: none
priority: 2
beliefs_affected:
  supports: [B14]
  contradicts: [B14]
belief_effect_detail: "B14 says vendor calibration is claimed, not shown. This independent study shows Choice probabilities calibrated (pooled ECE 0.028 over 279,925 answers), so 'not shown' no longer holds for Choice; it supports the 'fit thresholds locally' half for binary and multi-label questions."
evidence:
  directness: 4
  control: 4
  independence: 4
  reproducibility: 5
  applicability: 2
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.37647
found_via: survey
claim_cluster: jev-zero-shot-37-datasets-vs-qwen-gemma
---

# Evaluating and Benchmarking the System One Model Jev (arXiv 2609.37647)

- **URL:** https://arxiv.org/abs/2609.37647 (read: https://arxiv.org/html/2609.37647v1). Code and harness: https://github.com/AppliedMachineLearning-Lab/jev-benchmarking ; all 346,009 raw responses: https://doi.org/10.5281/zenodo.23039006
- **Type:** paper
- **Author / org:** Tobias Deußer, Lorenz Sparrenberg, Rafet Sifa (Applied Machine Learning Lab)
- **Date:** 2026-09-29
- **Retrieved:** 2026-10-01
- **Cited by evidence:** survey run, R9 plan question 1 (head-to-head against open-weight models)
- **Relevance to a memory stack:** medium. Independent, large and fully released; the tasks are general NLP, not memory decisions, but it gives the first public calibration figures for Jev Choice at scale and shows how prompted open-weight generalists compare.

## TL;DR
- Jev (jev-1.13.0), zero-shot, one frozen template per dataset, full evaluation splits of 37 datasets: 346,009 requests, 217.9 million tokens, **US$9.15** total, mean 0.36 s per request at 1,100 requests per minute (32 concurrent connections).
- Against **Qwen3.8-27B** scored by exact next-token probability over the option codes: Jev wins 27 of 37 datasets and "none of Qwen's nine leads [are] outside the bootstrap intervals". Against **Gemma-4-E4B**: Jev wins all 37.
- Choice calibration: pooled ECE **0.028** over 22 Choice datasets and 279,925 answers (per dataset 0.003 to 0.279).
- Binary (Noul) probabilities rank well but sit badly against 0.5: mean P(yes) 0.465 vs observed 0.518; multi-label mean P(yes) 0.209 vs observed 0.041. Tuned thresholds: UNFAIR-ToS micro-F1 0.499 to 0.748; GoEmotions macro-F1 0.243 to 0.353; ToxicChat jailbreak F1 0.717 to 0.833 at threshold 0.85.
- Weak spots shared by all three models: low-resource languages, fine-grained labels, rubric scoring (SummEval fluency correlation 0.495; HelpSteer2 helpfulness 0.399), legal clauses needing domain knowledge (AGB-DE F1 0.204).

## What it claims / describes
A neutral benchmark of the hosted model across classification, routing, NLI, reading comprehension, commonsense, moderation, legal clause analysis and rubric scoring. Open models received the same question rendered as a chat prompt (state as JSON, instructions, options); the harness read "the model's exact next-token distribution, which we restrict to the codes and renormalize". Open-model compute: Gemma 6.4 A40 GPU-hours for 126M prompt tokens; Qwen 17.4 A100-80GB GPU-hours for 135M prompt tokens.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Datasets won vs Qwen3.8-27B | 27 of 37 | Qwen leads 9, none outside bootstrap CIs | zero-shot, same requests | one template per dataset, untuned |
| Datasets won vs Gemma-4-E4B | 37 of 37 | | same | |
| MMLU | 91.8% | Qwen 81.7%, Gemma 67.4% | | see contamination probe below |
| Belebele (122 languages) | 86.7% | Qwen 77.8%, Gemma 68.4% | | English 97.2%, median language 91.1%, Nigerian Fulfulde 37.4% |
| IMDB | 96.5% | Qwen 96.5%, Gemma 95.6% | | |
| ARC | 98.8% | Qwen 98.0%, Gemma 93.2% | | |
| Largest Jev margins over Qwen | WinoGrande +15.1, MMLU +10.1, Belebele +8.9 points | | | |
| Choice ECE, pooled | 0.028 | | 22 datasets, 279,925 answers | per dataset 0.003 (language ID) to 0.279 (Emotion) |
| Noul mean P(yes) vs observed | 0.465 vs 0.518 | | binary | slight under-confidence |
| Multi-label mean P(yes) vs observed | 0.209 vs 0.041 | | | over-predicts yes |
| UNFAIR-ToS micro-F1, 0.5 vs tuned threshold | 0.499 vs 0.748 | | threshold tuned on training data | |
| ToxicChat jailbreak F1 | 0.717 vs 0.833 (threshold 0.85) | | | |
| Fine-grained label accuracy | Emotion 58.5%, SST-5 57.9%, Financial PhraseBank 73.0% | | | |
| Rubric correlation | SummEval fluency 0.495, HelpSteer2 helpfulness 0.399 | | | |
| Cost, latency | US$9.15 for 346,009 requests (217.9M tokens at $0.042 per million input tokens); 0.36 s mean | open models: GPU-hours above | | open-model latency not stated in this read |
| MMLU probe | 94.3% on calculation-heavy subjects vs 91.3% others; 94.3% with options rotated; 31.5% with the question withheld | | | "rules out shallow memorization but not memorized question-answer pairs" |

## Mechanism details you could implement
- Score an open generalist as a decision model by restricting the next-token distribution to option codes and renormalising; this is the cheapest fair open-weight baseline for any Jev comparison we run.
- Always fit binary thresholds on our own labels; 0.5 is wrong for Noul and badly wrong for multi-label.
- Use the released Zenodo responses to calibrate expectations before spending on our own runs.

## Limitations, caveats, counter-evidence
- Prompted generalists, not decision-tuned open models: it says nothing about Laya, Jeff, Tev1, od1, Bongard or decider-2b, several of which tie or beat Jev on decision benchmarks (JevBench v1.5.0, N-20260929-09; Bongard, N-SURVEY-20261001-07).
- One template per dataset; no run-to-run variance; results specific to jev-1.13.0 ("jev-latest" will differ).
- Applicability to memory decisions is indirect: none of the 37 tasks is a memory write, link or staleness decision.
- No page content addressed instructions to an AI agent.

## Takeaways for tuning a memory stack
- For Choice-style memory decisions, Jev probabilities can be used as probabilities with a light local check; for Noul gates (save or skip, still true or stale), fit the threshold.
- A prompted 27B open generalist is not a substitute at equal quality; the open-weight path for keeping memory text in-house should start from decision-tuned open models, not general chat models.
- Rubric-style judgements (quality scores) are weak for all three models; avoid scale-based memory decisions where a binary or choice framing exists (see N-SURVEY-20261001-06).

## Open questions
- Does the Choice calibration hold on memory decisions with long states (several KB of retrieved context)?
- How do decision-tuned open models do on these 37 datasets with the same harness?
