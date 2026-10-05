---
schema_version: 1
artifact_id: N-20260928-31
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:07:08Z
input_refs: [{"artifact_id": "post:2104534839676239926", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:towardsdatascience.com/a-new-kind-of-model-for-ai-decision-making
claim_cluster: url:towardsdatascience.com/a-new-kind-of-model-for-ai-decision-making
feeds: ["decision"]
primary_source: https://towardsdatascience.com/a-new-kind-of-model-for-ai-decision-making/
source_commit: 40442ad025406ae20c2614490f94bd775011dcee
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: none
priority: 1
tags: {"mechanism": ["jev-choice", "json-schema-enum-baseline", "confidence-buckets", "option-count-reduction", "mcnemar-paired-test"], "workload": ["intent-classification", "topic-classification"], "lifecycle_stage": ["decide"], "cross_cutting": ["calibration", "latency", "token-cost", "wilson-ci"]}
evidence_grade: {"directness": "medium: hosted Jev choice vs LLMs on typed classification with confidence; not memory decisions", "control": "high: same instruction, same bare label list, both format-constrained, same 1,000 test rows, Wilson CIs, a paired same-rows test for option count", "independence": "high: independent practitioner, not the vendor", "reproducibility": "high: notebooks and per-row prediction CSVs in a pinned repo; single run per model", "applicability": "medium: choice over many options is our linking and routing shape; banking intents are not engineering text"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Jev choice accuracy falls with option count faster than LLMs on the same rows (77 options: 83.4% vs 89.1% Luna; 7 options: 97.8% all), so prefilter the option list before a Jev choice call"]}
claim_correction: Post says Mansurova tries Jev for NPS topic modelling and LLM-as-a-judge; the article and code test only Banking77 intent classification (plus a 14-topic Stack Exchange control in the repo, not in the article); NPS and judge use are mentioned in the intro only. Jev trails both OpenAI models on 77 intents (79.0% vs 83.9% and 86.2%).
---

# "A new kind of model for AI decision-making" (Mariya Mansurova, Towards Data Science): TypeSafe Jev vs GPT Luna and Terra on Banking77

- **URL:** https://towardsdatascience.com/a-new-kind-of-model-for-ai-decision-making/ ; code https://github.com/miptgirl/miptgirl_medium/tree/main/jev
- **Type:** builder writeup (blog) with pinned notebooks and result files
- **Author / org:** Mariya Mansurova (Towards Data Science)
- **Date:** 2026-09-21 (per WebFetch of the article); code commit `40442ad025406ae20c2614490f94bd775011dcee`, 2026-09-18 08:51:17 +0100, "Merge pull request #2: Jev / TypeSafe classification benchmarks"
- **Retrieved:** 2026-09-28. Article read through three WebFetch calls (summarised by the fetch tool). Repo cloned at repos/miptgirl_medium; read jev/benchmark_banking77.ipynb, jev/benchmark_banking77_top7.ipynb, jev/benchmark_stackexchange.ipynb, jev/results/*_summary.csv.
- **Cited by evidence:** https://x.com/TDataScience/status/2104534839676239926 (@TDataScience, 2026-09-28)
- **Relevance to a memory stack:** medium. An independent, well-controlled measurement of Jev's `choice` question against LLMs with confidence buckets and an option-count ablation; it informs how many candidates to put in one Jev choice (linking, routing, recall choice) and whether its confidence can drive escalation.

## TL;DR
- Banking77, 1,000 rows sampled from the 3,080-row official test split (random_state 42, all 77 intents present). Zero-shot, same instruction and bare label names for all; Jev via `choice`, OpenAI via JSON-schema `enum`. Accuracy: gpt-5.6-luna 86.2% [83.9, 88.2], gpt-5.6-terra 83.9% [81.5, 86.1], jev-latest (jev-1.13.0) 79.0% [76.4, 81.4].
- Option count matters more for Jev: on 1,001 rows from the 7 largest intents, offering all 77 labels gives Jev 83.4% vs Luna 89.1% and Terra 88.8%; offering only the 7 gives 97.8% / 97.8% / 97.9%. Paired McNemar: Jev fixed 145, broke 1.
- Jev confidence is monotone with accuracy (buckets <=0.5: 35.0%, 0.5-0.7: 45.3%, 0.7-0.9: 61.9%, 0.9-1.0: 93.6%, n 60/106/189/645) but over-confident in the middle buckets; on the 77-label top-7 run mean confidence 0.891 vs accuracy 0.834.
- Latency (100 sequential uncached calls): Jev median 0.67 s, mean 0.70 s vs Luna 1.04 / 1.37 s and Terra 1.04 / 1.20 s. The article's "almost 2x faster" matches the mean, not the median (1.55x).
- Claim correction: the post frames it as NPS comment topic modelling and LLM-as-a-judge; neither was tested.

## What it claims / describes
The article introduces System One models, calls Jev via `POST https://api.typesafe.ai/v1/systemone`, and compares it with OpenAI "Luna" and "Terra" (the code names them `gpt-5.6-luna` and `gpt-5.6-terra`). Conclusions quoted by WebFetch: "On accuracy, Jev performs noticeably worse than both OpenAI models: 79.0%, compared with 83.9% for Terra and 86.2% for Luna." "When I reduced the task from 77 labels to just 7, the results improved significantly and were roughly on par with the OpenAI models." "Jev is almost 2x faster." "Jev uses significantly more tokens (about 2x more input tokens and 40x more output tokens)." The author calls "the well-calibrated confidence scores ... a big advantage" and expects "real-world gains to vary quite a lot by use case." NPS and LLM-as-a-judge appear only in the introduction and summary.

Method (benchmark_banking77.ipynb): 1,000 rows from the test split; the same instruction string for both sides; labels passed with no descriptions (`criteria: {label: None}`); 8 worker threads with a text-hash cache, 3 retries (Jev "returns a `503` when the model is briefly unavailable"); Wilson 95% intervals; a separate latency run of 100 sequential uncached calls per model; confidence buckets from Jev's `confidence`. OpenAI reasoning settings are not set in the code (defaults).

Option-count test (benchmark_banking77_top7.ipynb): train and test pooled (13,083 rows), 7 largest intents, 143 each, 1,001 rows; each row answered with the full 77-label list and with only the 7; McNemar on flipped rows.

Control task (benchmark_stackexchange.ipynb, in the repo, not in the article per WebFetch): 14 Stack Exchange topics, 280 rows (20 per topic).

## Numbers

| metric | value | baseline | setup with n | caveat |
|---|---|---|---|---|
| Banking77 accuracy, 77 labels | jev-latest 0.790 [0.7637, 0.8141] | gpt-5.6-luna 0.862 [0.8392, 0.882]; gpt-5.6-terra 0.839 [0.8149, 0.8605] | 1,000 test rows, zero-shot, one run (results/banking77_summary.csv) | Jev CI does not overlap Luna's |
| input / output tokens, 1,000 calls | Jev 1,040,811 / 828,290 | Luna 474,552 / 44,261; Terra 474,552 / 21,562 | same | Jev output is one probability per option; synthesis section 5 says Jev output is free, so token counts are not cost (inference) |
| top-7 rows, 77 labels offered | Jev 0.8342 | Luna 0.8911; Terra 0.8881 | 1,001 rows (results/banking77_top7_summary.csv) | pooled train+test rows |
| top-7 rows, 7 labels offered | Jev 0.978 | Luna 0.978; Terra 0.979 | same rows | |
| paired change 77 -> 7 labels | Jev +0.1438 (fixed 145, broke 1, p 0.0) | Luna +0.0869 (88/1); Terra +0.0909 (91/0) | McNemar, 1,001 shared rows | |
| 77-label errors outside the top 7 | Jev 159 of 166 (0.96) | Luna 99 of 109; Terra 102 of 112 | same | narrowing removes most errors |
| tokens per call, 77 vs 7 labels | Jev in 1045 / 398, out 831 / 114 | Luna in 479 / 133, out 40 / 31 | same | |
| Jev mean confidence vs accuracy | 77 labels 0.891 vs 0.834; 7 labels 0.982 vs 0.978 | n/a | same | over-confident at 77 options |
| Jev accuracy by confidence bucket | <=0.5: 0.350 (n 60); 0.5-0.7: 0.453 (106); 0.7-0.9: 0.619 (189); 0.9-1.0: 0.936 (645) | OpenAI returns no confidence | Banking77 1,000 rows | article gives no routing threshold |
| latency, sequential uncached | Jev mean 0.70 s, median 0.67, p90 0.79, max 2.23 | Luna 1.37 / 1.04 / 2.48 / 5.75; Terra 1.20 / 1.04 / 1.54 / 5.97 | 100 calls per model, one moment in time (notebook cell 30 output) | network measurement from the author's machine |
| Stack Exchange 14 topics | Jev 0.9464 [0.9135, 0.9673] | Luna 0.9679; Terra 0.9536 | 280 rows (results/stackexchange_summary.csv) | all CIs overlap; not in the article |
| Stack Exchange Jev buckets | 0.9-1.0: 0.996 (n 227); 0.7-0.9: 0.889 (27); 0.5-0.7: 0.545 (22); <=0.5: 0.750 (4) | | same | tiny low buckets |
| cost | not stated in text | | article cost comparison is image-only per WebFetch | not verified |

## Mechanism details you could implement
Jev request (benchmark_banking77.ipynb, verbatim):
```python
json={
    "state": text,
    "model": model,            # "jev-latest", resolved to "jev-1.13.0" in the response
    "questions": {
        "label": {
            "type": "choice",
            "instructions": instructions,
            "criteria": {label: None for label in labels},
        }
    },
}
```
Instruction: "Classify this banking customer support message into its intent category. Choose the single category that best matches what the customer is asking about." Response carries `choice`, `confidence`, a `probabilities` map with one entry per option, and `usage.input_tokens` / `usage.output_tokens`.

Evaluation hygiene worth copying: cache keyed by text hash plus model; Wilson intervals; latency measured separately from the threaded accuracy run; a paired same-rows test (McNemar) when changing one factor; an easy control dataset to tell "fine-grained discrimination" from "broadly weaker".

## Limitations, caveats, counter-evidence
- Single run per model; no repeated runs for Jev or OpenAI variance.
- Zero-shot with bare label names; neither side got label descriptions (Jev's `criteria` values were `None`), which may handicap Jev (inference; untested).
- Top-7 experiment pools train and test rows; fine for zero-shot, but not comparable to the 1,000-row test-split numbers (the notebook says so).
- Cost comparison in the article is image-only per WebFetch and was not verified; the article reasons about output tokens, while the synthesis says Jev output is free (inference: the cost claim may overstate Jev's cost).
- Model naming differs between article ("Luna", "Terra") and code (`gpt-5.6-luna`, `gpt-5.6-terra`).
- A different TDS Banking77 article is already in local sources (blog-jev-vs-llms-banking77-calibration-cascade.md, different URL); whether it shares an author was not checked. This note is a separate measurement.
- No instructions aimed at AI agents found in the article fetches or the notebooks read.

## Takeaways for tuning a memory stack
- Keep Jev `choice` option lists short: accuracy moved from 83.4% to 97.8% on the same rows when 77 options became 7. Prefilter candidates in code before a choice call (consistent with jevmem's cap of 200 ids and keyword prefilter).
- Jev confidence ranks errors well (93.6% accuracy in the 0.9-1.0 bucket covering 64.5% of calls) but is not a calibrated probability; fit escalation thresholds on your own data.
- Per-call latency about 0.67 s median from a client machine here, slower than the 0.3 to 0.4 s reported by jevmem and OpenGeni (inference: network and option count).

## Open questions
- Does giving label descriptions in `criteria` close the 77-label gap?
- What is the accuracy at, say, 10, 20 and 40 options on the same rows (the curve, not two points)?
- What is the cost per correct answer with actual Jev pricing?

## Grading and labels
- Directness: medium. Jev choice with confidence vs LLMs on typed classification; not memory.
- Control: high. Same instruction and labels, format-constrained both sides, Wilson CIs, paired option-count test.
- Independence: high. Independent practitioner.
- Reproducibility: high. Notebooks and per-row predictions pinned at `40442ad`.
- Applicability: medium. Many-option choice resembles our linking and recall choices.
- Pillars: R9 primary (Jev vs alternatives on quality, latency, confidence); R4 (confidence-based escalation).
- Stage: none (classification benchmark; closest memory analogue is a choice over candidates at linking or routing, inference).
- Tags: jev-choice, confidence buckets, option-count reduction, McNemar.
- B14 supports: Jev confidence is monotone but over-confident in the middle (0.7-0.9 bucket 61.9% accurate); thresholds must be fitted locally.
- would_create: Jev choice accuracy degrades with option count faster than LLMs; prefilter before choice.
- No contradiction row.

## Origin chain
@TDataScience post (2026-09-28) -> TDS article by Mariya Mansurova (2026-09-21, fetched) -> "all the code on GitHub": github.com/miptgirl/miptgirl_medium/tree/main/jev at `40442ad` -> notebooks and results/*.csv. Independence: independent of TypeSafe; single author.
