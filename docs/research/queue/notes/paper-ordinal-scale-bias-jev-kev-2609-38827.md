---
schema_version: 1
artifact_id: N-SURVEY-20261001-06
artifact_type: note
producer: triage
run_id: survey-20261001T054505Z-09ae
created_at: 2026-10-01T06:18:00Z
idempotency_key: note:survey:arxiv:2609.38827
input_refs: []
pillar_primary: R9
pillar_secondary: [R4, R10]
memory_stage: linking
priority: 1
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 3
  control: 4
  independence: 4
  reproducibility: 3
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.38827
found_via: survey
claim_cluster: ordinal-scale-compression-decision-models
---

# More Choices, Fewer Decisions: Ordinal-Scale Bias in JEV-like Direct-Decision Models (arXiv 2609.38827)

- **URL:** https://arxiv.org/abs/2609.38827 (read: https://arxiv.org/html/2609.38827v1); code and data https://github.com/Glax147/jev_ordinal_scale_bia (pinning not stated)
- **Type:** paper
- **Author / org:** Tianxiang Gao, Jinzhe Li, Zhiyuan Li, Yi Chang, Yuan Wu
- **Date:** 2026-09-30
- **Retrieved:** 2026-10-01
- **Cited by evidence:** survey run, R9 plan question 2 and R10 plan question 1 (how link confidence should be asked for)
- **Relevance to a memory stack:** medium to high wherever we ask a decision model for a graded answer: link confidence bands (the five bands in N-SURVEY-20261001-01), staleness severity, importance scores.

## TL;DR
- On ordinal scales, decision models collapse onto fewer levels than the gold labels use. Across 36 ordinal datasets, final decisions used 67% to 76% of the effective gold support, vs 87% to 102% on four nominal tasks.
- Finer scales make it worse: from K = 2 to K = 14 levels, Jev 1.13's utilisation fell from 95.9% to 54.5%; open KEV-9B 96.1% to 74.9%; KEV-4B 97.9% to 68.4%; KEV-0.8B 77.3% to 26.5%.
- Concrete case: on ANLI, Jev put 38.8% of all predictions and 51.3% of its 1,603 errors on Neutral, with balanced gold labels and 74.95% accuracy.
- Candidate probabilities stay broad; the compression is at the final decision. Randomising candidate order weakens but does not remove it.
- It is learnable: targeted BA-LoRA post-training of KEV raised utilisation from about 46% to 85% on eight training-source scales; transfer to unseen scales was positive for KEV-4B (73.2% to 81.3%) and negative for KEV-0.8B (75.0% to 72.7%).

## What it claims / describes
Models: hosted `typesafe/jev-1.13-20260917`, and the open KEV family (KEV-0.8B, KEV-4B, KEV-9B, all Qwen3.5-based, published on Hugging Face; maintainer given as Jared Palmer; licence not stated in the paper). Scales were posed as candidates like "Level 01 of 14: 0<=s<0.101282", with positions randomised in the controlled runs. Utilisation R is the ratio of predicted to gold effective support; D_R is the absolute support deviation.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Ordinal utilisation U_arg, Jev 1.13 | 72.97% | nominal: not reported for Jev | 36 ordinal datasets | |
| Ordinal / nominal U_arg, KEV-0.8B | 66.87% / 83.34% | | 36 ordinal, 4 nominal | |
| Ordinal / nominal U_arg, KEV-4B | 65.32% / 94.79% | | | |
| Ordinal / nominal U_arg, KEV-9B | 70.46% / 95.70% | | | |
| D_R ordinal / nominal, Jev | 24.24 pp / 1.47 pp | | | |
| R at K = 2 vs K = 14, Jev 1.13 | 95.9% vs 54.5% | | equal-frequency binning, 3 ordinal sources | |
| R at K = 2 vs K = 14, KEV-9B / 4B / 0.8B | 96.1 vs 74.9 / 97.9 vs 68.4 / 77.3 vs 26.5 | | same | |
| ANLI Neutral share, Jev | 38.8% of predictions, 51.3% of 1,603 errors | gold 2,140 / 2,136 / 2,124 | 6,400 items | |
| BA-LoRA, KEV-4B, 8 training-source scales: R / accuracy | 45.7% to 83.9% / 17.3% to 32.7% | | | |
| BA-LoRA, KEV-4B, all 36 ordinal: accuracy / R | 33.4% to 37.9% / 65.3% to 79.3% | | | |
| Transfer to 28 unseen-source scales, R | KEV-4B 73.2% to 81.3%; KEV-0.8B 75.0% to 72.7% | | | |

## Mechanism details you could implement
- Prefer a binary question with a probability (and a fitted threshold) over a graded scale when the output feeds a threshold anyway. A five-band "link confidence" asked as a Choice will under-use the extreme or middle bands.
- If a scale is needed, keep K small (2 to 4) and check the predicted-vs-gold level distribution, not only accuracy.
- Open decision models can be post-trained to use a scale faithfully; this is a candidate fine-tune target if we self-host.

## Limitations, caveats, counter-evidence
- One hosted model and one open family on one backbone.
- SST-5, DBpedia-14 and IMDb appear in KEV's training sources (contamination risk on those three).
- Not a memory task; the link to trace-link confidence is our inference.
- No page content addressed instructions to an AI agent.

## Takeaways for tuning a memory stack
- For confidence-scored links, ask "does this PR implement this requirement?" as a Noul probability and threshold it locally, rather than asking for one of five confidence bands. Combined with N-SURVEY-20261001-01 (verbalised bands, never calibrated), this is the design reason for the arm in PC-SURVEY-20261001-01.
- When comparing Jev with an open-weight model on graded decisions, report level utilisation; accuracy alone hides this failure.

## Open questions
- Is KEV's licence compatible with self-hosting memory decisions? Not stated in the paper; check the model cards before use.
