---
schema_version: 1
artifact_id: N-SURVEY-20261003-06
artifact_type: note
producer: triage
run_id: survey-20261003T054505Z-3590
created_at: 2026-10-03T06:00:00Z
idempotency_key: note:survey:arxiv:2605.27220
input_refs: []
pillar_primary: R4
pillar_secondary: [R3, R6]
memory_stage: recall_gate
beliefs_affected:
  supports: [B13, B9]
  contradicts: []
evidence: {directness: medium, control: medium, independence: high, reproducibility: low, applicability: medium}
source_url: https://arxiv.org/abs/2605.27220
found_via: survey
---

# The Coverage Illusion: From Pre-retrieval Routing Failure to Post-retrieval Cascades in a Production RAG System

- **URL:** https://arxiv.org/abs/2605.27220 (HTML v1 read via fetch summary; headline numbers verified present in local copy out/log/raw/2605.27220.html)
- **Type:** paper
- **Author / org:** Zafar Hussain, Kristoffer Nielbo (Aarhus University)
- **Date:** 2026-05-26
- **Retrieved:** 2026-10-03
- **Cited by evidence:** survey run, B13, B9; recall-gate design
- **Relevance to a memory stack:** medium. Production query logs show that deciding before retrieval what a query needs fails, while escalating after seeing what retrieval returned is cheap and better.

## TL;DR
- Danish National Encyclopedia (about 240,000 articles), 1,000 real user queries plus 3 x 1,000 synthetic; oracle label = best of five workflows per query.
- Pre-retrieval routers (rules 38.4% accuracy; TF-IDF, GBM, MiniLM classifiers) capture under 5% of the augmentation-free opportunity (ceiling 33.6%).
- Post-retrieval cascade (Hybrid, then QE-CE, then HyDE, escalating only when retrieval returns zero documents) escalates 27.8% of real queries, beats always-HyDE on composite 4.084 vs 3.944, and cuts latency 96.2 s to 65.6 s (31.8%).
- Synthetic queries make 90%+ look like they need augmentation; real users need it far less (the "coverage illusion").

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Composite (faithfulness + relevance, 1 to 5) | cascade 4.084 | always-HyDE 3.944; oracle 4.404 | real queries, n=1,000 | judge Qwen3-32B, generator Gemma-4-26B (different models) |
| Latency | 65.6 s | 96.2 s | | |
| Escalation rate | 27.8% | 100% | oracle 33.6% | |
| Coverage | Hybrid alone 72.2% | always-HyDE 86.4% | | |
| Judge vs human | Spearman 0.59 to 0.78; MAE 0.17 to 0.21 | | 100 pairs, 3 annotators | |
| has_sources flag | explains 69 to 83% of composite variance | | Appendix G | |

Possible inconsistency: best router composite 4.269 described as +0.011 over HyDE, which does not fit HyDE 3.944 (likely a different split; unverified).

## Mechanism details you could implement
- Escalation trigger = retrieval returned nothing usable; no trained model needed.

## Limitations, caveats, counter-evidence
- The trigger is "any sources returned", not a graded sufficiency judgment; encyclopedia QA, not engineering work. No code or data release stated.

## Takeaways for tuning a memory stack
- Supports B13 (escalate the borderline population, measured on real traffic) and the direction of B9: a decision made after seeing retrieved evidence beats one made from the query alone.
- Warns our PDLC benchmark against synthetic queries: they inflate how often hard retrieval is needed (priority 4).
- H8 should include a trivial post-retrieval trigger arm (empty or low-score hits) as the floor a learned sufficiency stop must beat.

## Open questions
- Would a graded sufficiency score beat the empty-hits trigger in this setting?
