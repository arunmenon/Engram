---
schema_version: 1
artifact_id: N-SURVEY-20261003-07
artifact_type: note
producer: triage
run_id: survey-20261003T054505Z-3590
created_at: 2026-10-03T06:00:00Z
idempotency_key: note:survey:arxiv:2609.40241
input_refs: []
pillar_primary: R9
pillar_secondary: [R4]
memory_stage: reranking
priority: 1
beliefs_affected:
  supports: [B10]
  contradicts: [B10]
evidence: {directness: medium, control: medium, independence: high, reproducibility: medium, applicability: low}
source_url: https://arxiv.org/abs/2609.40241
found_via: survey
---

# Decision-Oriented Recommendation Reranking: An Empirical Study of Jev

- **URL:** https://arxiv.org/abs/2609.40241 (HTML v1 read; local copy out/log/raw/2609.40241.html)
- **Type:** paper
- **Author / org:** Hanjia Lyu (Singapore Management University), Yinglong Xia (Meta AI)
- **Date:** 2026-09-30
- **Retrieved:** 2026-10-03
- **Cited by evidence:** survey run, B10 / H5-rerank
- **Relevance to a memory stack:** medium. Independent (non-vendor) test of Jev's single `choice` call as a reranker against an open 7B model run both pointwise and listwise, at pool sizes 20 to 200.

## TL;DR
- Three Amazon Reviews 2023 domains (954, 1,000, 626 users); SASRec top-200 candidates; K in {20, 50, 100, 200}.
- Jev (one `choice` call per user, probabilities used as scores) has the best MRR at K=20 in all three domains (0.238 / 0.295 / 0.346).
- Open Qwen2.5-7B pointwise (K calls) beats Qwen2.5-7B listwise (one call) everywhere: listwise MRR is lowest of the LLM arms (0.199 / 0.213 / 0.245 at K=20). The single-call advantage in B10 is a property of the model's choice primitive, not of listwise prompting.
- At K=200 on Movies, no rerank (SASRec) beats Jev: MRR 0.093 vs 0.080, HR@10 0.170 vs 0.150.
- No calibration, abstention, cost or open-weight decision-model results.

## Numbers
| Metric | Jev | Qwen pointwise | Qwen listwise | SASRec (no rerank) | Setup |
|---|---|---|---|---|---|
| MRR K=20 / K=200, Movies | 0.238 / 0.080 | 0.232 / 0.061 | 0.199 / 0.039 | 0.117 / 0.093 | n=954 |
| MRR K=20 / K=200, Video Games | 0.295 / 0.095 | 0.259 / 0.070 | 0.213 / 0.033 | not extracted | n=1,000 |
| MRR K=20 / K=200, Books | 0.346 / 0.140 | 0.282 / 0.074 | 0.245 / 0.035 | not extracted | n=626 |
| HR@10 K=20 (Movies/VG/Books) | 0.587 / 0.648 / 0.684 | 0.575 / 0.612 / 0.644 | | | |
| Median latency ms | 349.888 to 967.347 (hosted, includes network) | 606.545 to 14,868.048 | 63.604 to 1,530.139 | about 1.1 | local A800-80GB; not hardware-normalised |

Text vs table: text says Jev latency stays "in the low-second range even at K=200"; Table 3 medians at K=200 are all under one second. Text claims "particularly strong relative performance at larger K"; Movies K=200 shows SASRec ahead.

## Mechanism details you could implement
- Jev call: one `choice` question with K items as alternatives; scores = returned probabilities, no post-processing.

## Limitations, caveats, counter-evidence
- Recommendation, not memory evidence; ground truth is one held-out item. Users filtered to those whose target is in SASRec top 200. No cross-encoder or larger LLM. Call counts and cost not stated.

## Takeaways for tuning a memory stack
- Supports B10 on a second domain and from a non-vendor team: Jev's single choice call beats per-item scoring by an open 7B at small pools.
- Contradicts the general reading of B10: "listwise beats pointwise" does not transfer to an ordinary open LLM, where listwise was worst. If we self-host (priority 2), H5-rerank must test pointwise and listwise separately for the open model.
- Large pools erode the gain and can fall below no rerank: cap the rerank pool (consistent with RSI-Jev v3.0 losing to no reranking).

## Open questions
- Does an open decision model with a choice head (Laya ports) behave like Jev or like Qwen listwise?
