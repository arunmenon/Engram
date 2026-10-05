---
schema_version: 1
artifact_id: N-SURVEY-20260930-08
artifact_type: note
producer: triage
run_id: survey-20260930T054503Z-298f
created_at: 2026-09-30T05:59:40Z
idempotency_key: note:survey:arxiv:2603.28886
input_refs: []
pillar_primary: R7
pillar_secondary: [R3]
memory_stage: retrieval
beliefs_affected:
  supports: [B23]
  contradicts: []
qualifies_note: N-SURVEY-20260928-08
evidence: {directness: medium, control: medium, independence: medium, reproducibility: low, applicability: low}
strength: paper-single-benchmark
source_url: https://arxiv.org/abs/2603.28886
found_via: survey
---

# Calibrated Fusion for Heterogeneous Graph-Vector Retrieval in Multi-Hop QA (PhaseGraph)

- **URL:** https://arxiv.org/abs/2603.28886 (HTML v3 read: https://arxiv.org/html/2603.28886v3)
- **Type:** paper
- **Author / org:** Andre Bacellar (affiliation not stated)
- **Date:** 2026-03-30 (v1), 2026-09-18 (v3)
- **Retrieved:** 2026-09-30 (local copy: out/log/raw/2603.28886.html)
- **Cited by evidence:** survey run survey-20260930T054503Z-298f, R7 question 2 (fusion across heterogeneous evidence); bears on belief B23 and on note N-SURVEY-20260928-08
- **Relevance to a memory stack:** medium. It is the closest held-out test found of rank fusion (RRF, k=60) against score-calibrated fusion when one list comes from a vector index and the other from a graph walk. It does not test different evidence unit types.

## TL;DR
- Dense similarity and graph Personalized PageRank (PPR) scores have different shapes: "Dense similarity clusters in a narrow Gaussian (μ≈0.09, σ≈0.02), while PPR scores follow a power-law (most values ∼0.001, rare peaks ∼0.3)". The method maps each to percentile ranks before fusing.
- On held-out queries, both RRF and the calibrated fusion beat vector-only by 1 to 3 points. Neither beats the other: "thermo versus RRF is 7W/11L (p=.48) on MuSiQue and 3W/0L (p=.25) on 2Wiki".
- Percentile calibration was directionally better than min-max normalisation (53.8 against 52.7, 1 win and 6 losses for min-max, p=.125, not significant).
- Uncapped graph weight hurt: on the full corpus a graph-heavy setting scored 51.0 against 58.1 for vector-only (36 wins, 81 losses).
- This qualifies N-SURVEY-20260928-08, where a normalised convex combination beat RRF on every reported dataset. In a graph plus vector setting with passage units, a calibrated combination shows no paired advantage over RRF at k=60.

## What it claims / describes
Both retrievers return passages. The vector leg scores by cosine similarity; the graph leg scores passages by PPR over a HippoRAG2-style graph. Fusion steps:

1. Percentile rank per retriever: `p_i = |{j : s_j <= s_i}| / N`.
2. Energy: `E_i = -ln(p_i + eps)`, `eps = 1e-6`.
3. Temperature per retriever: `T = mean(E) / 2`.
4. Boltzmann probability: `P_i = exp(-E_i / T) / Z`.
5. Fused score: `alpha * P_vector + (1 - alpha) * P_graph + beta * 1[item in both lists]`, with `alpha` in {0.4, 0.7} tuned per corpus and `beta` in {0.5, 1.0, 1.5}.

RRF baseline: `score(d) = sum over retrievers of 1 / (k0 + rank(d))` with `k0 = 60`.

Data: MuSiQue, 11,654 passages, 486 tuning queries and 514 held-out queries, K=10. 2WikiMultiHopQA, 6,343 passages, 509 tuning and 491 held-out queries, K=5. Embedder: NV-Embed-v2 (4096 dimensions); secondary runs with text-embedding-3-small. Metric: LastHop@K (the final-hop supporting passage is in the top K). Tests: McNemar on paired wins and losses; Wilson intervals. Single run.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| MuSiQue LastHop@10, held-out n=514 | RRF 71.8 % (25 wins, 11 losses, p=.029); calibrated 71.0 % (15 wins, 5 losses, p=.041) | vector-only 69.1 % | NV-Embed-v2 | calibrated against RRF: 7W/11L, p=.48 |
| 2Wiki LastHop@5, held-out n=491 | RRF 53.0 % (8W/2L, p=.109); calibrated 53.6 % (11W/2L, p=.023) | vector-only 51.7 % | same | calibrated against RRF: 3W/0L, p=.25 |
| Ablation, 2Wiki held-out | percentile plus Boltzmann 53.8 %; min-max 52.7 % (1W/6L, p=.125); linear fusion after percentile 53.2 % (0W/3L, p=.250) | | n=491 | not significant |
| Hard slice, MuSiQue, 66 queries | RRF 74.2 % (23W/0L); calibrated 78.8 % (26W/0L); plus Ising term 80.3 % | vector-only 39.4 % | filtered for graph coverage | "favorable to graph methods by construction" |
| Full corpus, 500 queries, 6,841 passages | graph-heavy uncapped 51.0 % (36W/81L); capped alpha .7 60.4 % (16W/5L); plus entity disambiguation 62.6 % | vector-only 58.1 % | | R@5 not significant (7W/5L, p=.77) |
| Secondary embedder | calibrated does not confirm on held-out (5W/4L, p=1.0) | | text-embedding-3-small, MuSiQue-500 | |
| HotpotQA cross-check | 0W/0L | | | strong vector baseline |
| Cost, latency | not stated | | | |
| Judge | none for retrieval metrics; a 66-query QA check used one LLM, no repeated runs | | | |

Text versus table: the abstract quotes 2Wiki LastHop@5 "from 51.7% to 53.6%" and the table agrees; the ablation table's baseline row reads 53.8 % for the same configuration family. The 0.2-point difference is not explained in what was read.

## Mechanism details you could implement
- Percentile-rank normalisation per retriever is a drop-in alternative to min-max or z-score when score distributions differ in shape. It keeps order and discards magnitude, which places it between RRF and a raw-score combination.
- An overlap bonus (`beta`) for items returned by both legs.
- Cap the graph leg's depth or weight. The uncapped graph-heavy setting lost 7 points to vector-only.
- Evaluate fusion rules with paired win and loss counts on a held-out split, not only aggregate accuracy; at these sample sizes a 1-point difference is 5 queries.

## Limitations, caveats, counter-evidence
- Stated: "The MuSiQue margin should be read as fragile"; the result did not confirm with a second embedder.
- Stated: the hard slice is filtered in the graph method's favour.
- Single author, no affiliation, single run, no code URL found.
- Both legs return the same unit type (passages). The paper's "heterogeneous" refers to score distributions. It does not test B23's open clause, comparability across different evidence units (chunks, graph facts, summaries, code symbols).
- Multi-hop encyclopedic QA, not engineering artifacts.
- Against N-SURVEY-20260928-08 (Bruch et al.): that study found a tuned convex combination of normalised scores beat RRF on every dataset for lexical plus dense fusion. Here, for graph plus dense fusion, the calibrated combination and RRF are statistically level. The two are compatible if the advantage of score-based fusion depends on the legs being calibratable and on a larger tuning set.

## Takeaways for tuning a memory stack
- B23 stands: RRF at k=60 is a reasonable baseline when a graph leg is added, and a calibrated alternative did not beat it on held-out queries here. The open clause (heterogeneous units) remains untested by any source found this run.
- PC-SURVEY-20260928-03 proposes testing a normalised convex combination against RRF. When the graph leg is included in that test, expect a null and size the query set for paired counts (several hundred queries).
- If H2's graph arm is fused rather than traversed, cap the graph leg's weight and report a vector-only arm; uncapped graph weight is the failure case.

## Open questions
- What happens when the fused lists hold different unit types and lengths (a 40-token graph fact against a 600-token chunk)? Rank-based fusion treats them alike; a token budget does not.
- Does percentile calibration help when one leg is a BM25 score over code identifiers?
