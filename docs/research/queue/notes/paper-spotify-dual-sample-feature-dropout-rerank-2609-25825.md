---
schema_version: 1
artifact_id: N-20260926-20
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:18:28Z
input_refs: [{"artifact_id": "post:2102608818266132858", "file_id": null, "sha256": null}, {"artifact_id": "post:2102687951381504200", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.25825
claim_cluster: arxiv:2609.25825
feeds: ["decision"]
primary_source: https://arxiv.org/abs/2609.25825
source_commit: n/a
strength: paper-ablated
pillar_primary: R4
pillar_secondary: ["R5", "R3"]
tags: {"mechanism": ["LLM cross-encoder rerank", "behavioural statistics in prompt", "dual-sample feature dropout", "shortcut learning"], "workload": ["personalised search reranking"], "lifecycle_stage": ["read"], "cross_cutting": []}
evidence_grade: {"directness": "high: offline NDCG and recall with and without the behavioural feature, plus an online A/B", "control": "high: alpha sweep including feature-only and no-feature arms, feature-removed stress test", "independence": "medium: Spotify authors on Spotify data", "reproducibility": "low: proprietary data and model", "applicability": "medium: usage or outcome statistics attached to memories (retrieval counts, success rates) are the same kind of behavioural shortcut feature"}
beliefs_affected: {"supports": ["B17"], "contradicts": [], "would_create": ["A reranker trained with outcome/usage statistics always present learns a shortcut and drops below the no-statistics model when the statistic is missing (0.526 vs 0.550 NDCG@7); training each example with and without the statistic removes most of that loss"]}
claim_correction: none
---

# Robust Fusion of Semantic and Behavioural Signals for LLM Reranking in Personalised Search (arXiv 2609.25825)

- **URL:** https://arxiv.org/abs/2609.25825 (HTML read)
- **Type:** paper
- **Author / org:** Aleksandr V. Petrov, Nathan Stein, Erik Lybecker, Emma Schuldt, Daniel Lazarovski, Hugues Bouchard, Mounia Lalmas (Spotify)
- **Date:** 2026-09-22
- **Retrieved:** 2026-09-26
- **Cited by evidence:** https://x.com/_reachsumit/status/2102608818266132858 (@_reachsumit)
- **Relevance to a memory stack:** medium. If we feed a reranker memory-level usage or outcome signals (how often a memory was recalled or led to success), this is the failure mode and a cheap fix.

## TL;DR
- 0.6B cross-encoder reranker; behavioural feature Query Slice Stats (QSS: historical query-item-country success rate, bucketed very_low to very_high) injected into the prompt.
- Loss = alpha * SFT(x+, y) + (1 - alpha) * SFT(x-, y), where x- is the same prompt with QSS removed.
- Table 2: alpha 0 NDCG@7 0.549 / Recall@7 0.685; **alpha 0.5 0.622 / 0.756**; alpha 1.0 0.618 / 0.750.
- **Shortcut:** with QSS always present in training (alpha 1.0), NDCG@7 falls to **0.526** when QSS is removed, below the no-QSS model (0.550); alpha 0.5 holds 0.547.
- Online A/B: about +2.05% search success (alpha 0.5) and +2.33% (alpha 1.0); aggregates did not significantly separate the two.

## What it claims / describes
- Baselines: random 0.010, BM25 metadata 0.105, monoT5 0.104, QSS-only 0.494 NDCG@7.
- The dual-sample scheme keeps the gain when the feature exists and robustness when it is missing (cold start, novel queries).

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| NDCG@7 alpha 0.5 | 0.622 | alpha 0: 0.549 | Table 2 | +13.3% |
| Recall@7 alpha 0.5 | 0.756 | 0.685 | Table 2 | |
| QSS removed, alpha 1.0 | 0.526 | alpha 0: 0.550 | stress test | shortcut |
| QSS removed, alpha 0.5 | 0.547 | alpha 1.0: 0.526 | | +4.0% relative |
| online search success | +2.05% (alpha 0.5), +2.33% (alpha 1.0) | control | A/B | variants not significantly different |
| long-tail gains | 0.42 to 0.44% | | | CIs near threshold |

## Mechanism details you could implement
- When a memory carries usage stats (recall count, success rate), train or prompt the ranker on paired views with and without them, and evaluate with the stats removed.

## Limitations, caveats, counter-evidence
- One behavioural feature; complete removal is a stress test; no learned fusion baseline; online test powered for aggregates only.

## Takeaways for tuning a memory stack
- Read-time strengthening (Hippo, REALM reweighting) turns usage into ranking signal; this paper shows a ranker can come to depend on that signal, which is how a wrong memory that is often recalled keeps winning (B17 feedback loop). Test rankers with usage signals ablated (inference).

## Open questions
- Does the shortcut appear with an un-trained decision model given usage stats in the state? Not tested.

## Grading and labels
- Directness high; control high; independence medium; reproducibility low; applicability medium.
- Pillar R4 (reranker decision quality and robustness). Secondary R5 (behaviour/outcome signals feeding ranking) and R3.
- Beliefs: supports B17 in spirit (feedback-loop reinforcement is unmeasured in memory systems; here a measured analogue: shortcut reliance on success statistics). Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
post 2102608818266132858 (@_reachsumit) -> arXiv 2609.25825 (HTML) -> setup, Table 2, online section, limitations -> this note.
