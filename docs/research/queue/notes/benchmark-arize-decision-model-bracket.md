---
schema_version: 1
artifact_id: N-SURVEY-20261011-02
artifact_type: note
producer: triage
run_id: survey-20261011T054529Z-bcaa
created_at: 2026-10-11T06:45:00Z
idempotency_key: note:survey:url:arize.com/blog/decision-model-benchmark
input_refs: []
pillar_primary: R9
pillar_secondary: [R6, R4]
memory_stage: evaluation
priority: 2
beliefs_affected: {supports: [B14], contradicts: []}
contradicts_notes: [N-SURVEY-20261011-01]
evidence: {directness: 4, control: 3, independence: 3, reproducibility: 3, applicability: 3}
strength: vendor-benchmark
source_url: https://arize.com/blog/decision-model-benchmark/
found_via: survey
answers_watch_request: null
---

# Arize decision-model bracket (October 2026): Jev 1.13, Clef 27B, Liquid d1, OpenAI Decisions, Jeeves 9B, Kev 9B, Strands 2B, Laya on hallucination, evaluator and routing tasks

- **URL:** https://arize.com/blog/decision-model-benchmark/
- **Type:** vendor blog (Arize sells evaluation tooling, not a decision model)
- **Author / org:** Jim Bennett, Arize AI
- **Date:** October 2026 (day not shown)
- **Retrieved:** 2026-10-11
- **Relevance to a memory stack:** high. The widest head-to-head of hosted and open-weight System One models run by a party that does not sell one, with held-out thresholds, CIs, calibration and a wording-flip test.

## TL;DR
- Clef 27B ties Jev 1.13 on accuracy (85.2% vs 85.5% hallucination; 91.5% vs 91.1% evaluators; 50/52 vs 49/52 routing) but has worse calibration (0.062 vs 0.023) and is slower and dearer on Workers AI (0.50 s vs 0.08 s p50; $0.223 vs $0.045 per 1,000).
- Best open model run locally: Kev 9B (88.7% evaluators, 76.8% hallucination). Laya: 59.8% / 57.3%, calibration error 0.330.
- Wording flip: asking the negated question ("Does it contain an unsupported claim?") collapses several models: Liquid ROC AUC 0.92 to 0.17, Jeeves 0.85 to 0.25, Strands 0.75 to 0.26, Kev 0.85 to 0.54. Jev 0.93/0.93 and Clef 0.92/0.91 hold.
- Jev was right every time it said 99% or more (14% of cases).

## What it claims / describes
Bracket of matches. Cloud conference (hosted APIs) and local conference (one MacBook Pro M4 Max, 36 GB). Each model gets its own yes/no cutoff "tuned on one half of the data and scored on the other, using a fixed random seed". A win on accuracy requires non-overlapping 95% CIs; ties broken by calibration. Calibration error = average gap between stated confidence and observed accuracy. Cost = list price times tokens.

## Numbers (verbatim from the full results table)

| Model | Halluc. (RAGTruth, 2,675 rows) | Evaluators (13 Phoenix suites, 655 cases) | Routing (52) | Cal. err. | p50 latency | Cost /1,000 |
|---|---|---|---|---|---|---|
| Jev 1.13 | 85.5% | 91.1% | 49/52 | 0.023 | 0.08 s | $0.045 |
| Clef 27B | 85.2% | 91.5% | 50/52 | 0.062 | 0.50 s | $0.223 |
| Liquid d1 | 84.8% | 87.6% | 48/52 | 0.051 | 0.20 s | $0.034 |
| OpenAI Decisions | 81.5% | 90.0% | 48/52 | 0.042 | 0.16 s | $0.090 |
| Jeeves 9B | 80.3% | 87.1% | 48/52 | 0.043 | 16.8 s | local |
| Kev 9B | 76.8% | 88.7% | 48/52 | 0.055 | 1.03 s | local |
| Strands 2B | 69.0% | 76.7% | 45/52 | 0.065 | 0.34 s | local |
| Laya | 59.8% | 57.3% | 40/52 | 0.330 | 0.04 s | local |

Reference: Opus 5 scored 86.6% on the hallucination task "at $14.30 per 1,000 judgments" (earlier benchmark). Wording-flip ROC AUC (supported / unsupported phrasing): Jev 0.93/0.93; Clef 0.92/0.91; OpenAI 0.90/0.89; Kev 0.85/0.54; Laya 0.64/0.36; Strands 0.75/0.26; Jeeves 0.85/0.25; Liquid 0.92/0.17. Laya on toxicity: 0.11 ("free of toxic content?") vs 0.87 ("contain toxic content?").

Judge and system share a model: no; labels come from RAGTruth and Phoenix datasets.

## Limitations, caveats, counter-evidence
- Routing n = 52; one answer is about 2 points; routing differences are noise (stated).
- Local and cloud latencies on different hardware (stated). Clef-flash not tested.
- Single snapshot; tasks are generic evaluation tasks, not engineering-agent memory decisions (inference).
- Code: PR #88522 in Arize-ai/arize; evaluator data in Arize-ai/phoenix. Not checked at a pinned commit.

## Contradiction
Contradicts the Clef vendor card (N-SURVEY-20261011-01) on latency (vendor: Clef 209.3 ms, Jev 524.1 ms median; Arize: Clef 0.50 s, Jev 0.08 s p50) and adds the calibration gap the vendor did not report. The deployments differ (vendor internal GPUs vs public Workers AI and TypeSafe API), so both can be true; the vendor latency should not be used for planning.

## Takeaways for tuning a memory stack
- Accuracy parity between Jev and the best open models is real on generic tasks; calibration and polarity robustness are where they separate.
- Any open model we adopt must pass a polarity test: ask each link or admission question both ways and require consistent answers.

## Open questions
- Does the polarity collapse appear on PDLC link questions ("does this PR implement R?" vs "does this PR fail to implement R?")?
