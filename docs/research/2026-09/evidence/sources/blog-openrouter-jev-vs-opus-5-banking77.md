---
schema_version: 1
artifact_id: N-20260927-15
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2103923093832155607", "file_id": null, "sha256": null}, {"artifact_id": "post:2104091617972085212", "file_id": null, "sha256": null}, {"artifact_id": "post:2104096086516441543", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:openrouter.ai/blog/insights/jev-vs-claude-opus-5-classification
claim_cluster: url:openrouter.ai/blog/insights/jev-vs-claude-opus-5-classification
feeds: ["decision", "memory"]
primary_source: https://openrouter.ai/blog/insights/jev-vs-claude-opus-5-classification/
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R4
pillar_secondary: ["R6"]
tags: {"mechanism": ["confidence-cascade", "escalation-threshold", "label-only-criteria"], "workload": ["intent-classification", "Banking77"], "lifecycle_stage": ["decide", "escalate"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: accuracy with CIs, latency percentiles, cost and a cascade table", "control": "medium: paired comparison on the same 3,080 utterances, but cascade thresholds are read off the test set and Opus ran without reasoning", "independence": "medium: OpenRouter hosts both models and is not TypeSafe; two other Banking77 measurements of Jev (79.3% and 92.40%) disagree with this one", "reproducibility": "low: prompts and per-item outputs not linked in the fetched page", "applicability": "medium: the cascade shape is our escalation design, but the workload is support-intent classification"}
beliefs_affected: {"supports": ["B14", "B13"], "contradicts": [], "would_create": ["Decision-model accuracy on a fixed benchmark varies by more than 10 points with how the label criteria are written; a vendor or third-party accuracy is not portable across prompt designs"]}
claim_correction: Secondary posts (lifemakers 2104091617972085212) present 81.0% as "Jev's" Banking77 accuracy; three sources measure Jev on the same 3,080-message test split at 81.0% (OpenRouter, label-only criteria), 79.3% (Privatemode benchmark) and 92.40% (published answer file cited by cymetica), so the number is a property of the prompt design, not of the model.
---

# Jev vs Claude Opus 5 on Banking77 (OpenRouter Insights), with two other Banking77 measurements of Jev

- **URL:** https://openrouter.ai/blog/insights/jev-vs-claude-opus-5-classification/
- **Type:** vendor blog (model host)
- **Author / org:** Kenny Rogers, OpenRouter
- **Date:** tested 2026-09-22
- **Retrieved:** 2026-09-27. Also read: https://cymetica.com/blog/matching-jev-on-banking77-at-a-thousandth-of-the-cost (2026-09-27) and the Banking77 row of `results/suite.md` in edgelesssys/privatemode-decisions-benchmark at f5ecd9f77541b5a5804f7ca7fa0d45ad599aeb84 (see `github-edgelesssys-privatemode-decisions-benchmark.md`).
- **Cited by evidence:** @alexchen77sh https://x.com/alexchen77sh/status/2103923093832155607 (backlog, deferred by budget); @LifeMakersCom https://x.com/LifeMakersCom/status/2104091617972085212 (Japanese summary); @EventTraderBot https://x.com/EventTraderBot/status/2104096086516441543 (cymetica, merged here because it is the same Banking77 accuracy claim).
- **Relevance to a memory stack:** medium. A clean, host-run confidence cascade table: how much traffic a decision model can keep at each threshold and what accuracy the cascade retains. Directly shapes an admission or escalation gate.

## TL;DR
- Banking77 test split, 3,080 utterances, 77 intents. Jev 1.13 81.0% (95% CI 79.6 to 82.3), macro-F1 80.5%; Claude Opus 5 (reasoning off, temperature 0, strict JSON schema) 84.4% (83.1 to 85.6), macro-F1 83.6%. Paired bootstrap gap 3.3 points (CI 2.3 to 4.4).
- Latency p50 175 ms vs 2,266 ms; p95 270 vs 3,004; p99 353 vs 3,835. Full run $0.34 vs $7.44 ($0.11 vs $2.42 per 1,000).
- Jev confidence is "not a calibrated probability" but ranks well: confidence >= 0.99 covers 58% of utterances at 96.3% accuracy; < 0.5 covers 3.5% at 29.6%.
- Cascade (Jev keeps high-confidence, Opus gets the rest): threshold 0.90 keeps 75.9% on Jev at 84.0% accuracy and $0.69 per 1,000, i.e. "76% of traffic bypasses Opus" for at most 0.4 points; the page itself calls the table an "upper bound" because thresholds are on the test data.
- Two other Banking77 measurements of Jev: 79.3% (Privatemode benchmark, 1,000 sampled, default settings) and 92.40% (2,846/3,080 from a published answer file dated 2026-09-18, used by cymetica). An 11-point spread on the same test split means the label criteria and prompt dominate.

## What it claims / describes
OpenRouter ran both models on the Banking77 test split with "one-line criterion for each intent from just the label name, without looking at the test data". Jev used the Decisions API Choice format (77 options). Opus used temperature zero, reasoning off, strict JSON schema, prompt caching on the system message. Concurrency 8. Inter-model agreement 89.3%. The write-up then treats Jev's confidence as a routing signal and simulates a cascade that escalates below a threshold to Opus.

Cymetica (secondary cluster, merged): a blend of "The Tuatara Vector Model" (frame ids adapted to intent classes) and "a logistic-regression classifier" on word and character n-grams, weighted "30% Tuatara, 70% logistic regression", trained only on "the official 10,003 training messages", scored 91.79% (2,827/3,080) vs Jev 92.40% (2,846/3,080) from "Jev's answer for every one of the 3,080 test messages" published by an independent researcher on 2026-09-18; "Exact McNemar test, p = 0.27". Cost about $0.14 vs $142 per million messages; latency about 11 ms vs 0.53 s (Jev including network). The cymetica page does not address the OpenRouter 81.0%.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| accuracy | Jev 81.0% (79.6 to 82.3) | Opus 5 84.4% (83.1 to 85.6) | Banking77 test, n=3,080, label-only criteria | paired bootstrap gap 3.3 (2.3 to 4.4) |
| macro-F1 | 80.5% | 83.6% | same | |
| accuracy excl. `get_physical_card` | Jev 82.1% | Opus 85.5% | same | that class was 0% for both with label-only criteria |
| p50 / p95 / p99 latency | 175 / 270 / 353 ms | 2,266 / 3,004 / 3,835 ms | client round trip | |
| cost per 1,000 | $0.11 | $2.42 (about $19 uncached) | same | |
| mean input tokens | 2,605 | 3,750 (3,725 cached) | same | |
| share at confidence >= 0.99 | 58% at 96.3% accuracy | | same | |
| share at confidence < 0.5 | 3.5% at 29.6% accuracy | | same | |
| cascade @0.99 | Jev keeps 57.8%, 84.3%, $1.13/1k | Opus alone 84.4%, $2.42/1k | same | thresholds chosen on test data ("upper bound") |
| cascade @0.95 | 68.1%, 84.2%, $0.88/1k | | same | |
| cascade @0.90 | 75.9%, 84.0%, $0.69/1k | | same | |
| cascade @0.80 | 82.7%, 83.6%, $0.53/1k | | same | |
| cascade @0.70 | 87.3%, 83.2%, $0.42/1k | | same | |
| Jev accuracy (other source) | 79.3% | Privatemode (GLM-5.3-Flash one-pass) 76.9%, glm-cot 80.6% | Privatemode benchmark, banking77, 1,000 examples, 2 replicates | default Jev settings, identical option names |
| Jev accuracy (other source) | 92.40% (2,846/3,080) | trained LR + vector blend 91.79% | published Jev answer file, 2026-09-18 | prompt used for that file not stated in cymetica page; blend trained on the 10,003 train messages |

Judge: gold labels, no LLM judge. Model versions: Jev 1.13 (OpenRouter), `jev-latest` (Privatemode), unknown (published file).

## Mechanism details you could implement
- Confidence cascade: act on the decision model's answer when confidence >= t, else escalate. On this data t = 0.90 kept 76% of traffic for a 0.4-point loss. Fit t on held-out data, not the test split.
- Use the returned confidence as a ranking signal, not a probability (the host's own wording).
- Write per-class criteria with care: one class went to 0% for both models because label-only criteria were ambiguous.
- A trained lexical classifier (n-gram LR) on in-domain labels matched a strong zero-shot Jev run at about 1/1,000 of the cost; when you have labels, try the cheap supervised arm first (inference from cymetica).

## Limitations, caveats, counter-evidence
- Single dataset, domain and prompt design; Opus without reasoning.
- Cascade table is optimistic by construction (thresholds on the test set).
- The fetched page also listed "mean output tokens" of 826 for Jev and 17 for Opus; Jev returns no text, so this row is likely mis-extracted or counts something else. Not used here.
- The three Jev accuracies (79.3%, 81.0%, 92.40%) come from different criteria and sample sizes; none states a common prompt.
- Answers WR-20260926-02 only partially: the OpenRouter write-up reports no ECE; an ECE of 0.097 for Banking77 was not found in any of the three sources read.

## Takeaways for tuning a memory stack
- An escalation gate on a decision model's confidence can move most traffic off the expensive model with a small accuracy loss, but only after the threshold is fitted locally.
- Do not import anyone's accuracy number: on the same benchmark the spread is 13 points across writers.
- Where labelled in-domain data exists, a trained lightweight classifier is a mandatory baseline.

## Open questions
- The exact criteria text behind the 92.40% file.
- Cascade retention with thresholds fitted on a separate split.
- Opus with reasoning on.

## Grading and labels
- Directness: high. Control: medium. Independence: medium (host, not vendor; conflicting third-party numbers). Reproducibility: low. Applicability: medium.
- Strength: vendor-benchmark. Pillar R4 (escalation and confidence routing); secondary R6 (prompt-design sensitivity of reported accuracy).
- Beliefs: supports B14 (host states confidence is not calibrated; thresholds must be fitted locally); supports B13 in spirit (escalation must be evaluated on the borderline population: the <0.5 bucket is 3.5% of traffic at 29.6%). Would create: accuracy on a fixed benchmark varies by 10+ points with label-criteria design.
- Contradiction rows: none.

## Origin chain
@alexchen77sh post -> openrouter.ai Insights article -> accuracy, latency, cost, confidence and cascade tables -> this note. Cymetica post (@EventTraderBot) -> cymetica.com article -> accuracy and McNemar result -> merged here. Privatemode repo results/suite.md banking77 row -> cross-check. Independence: three writers, one benchmark; the 92.40% file's author is unnamed in the fetched text.
