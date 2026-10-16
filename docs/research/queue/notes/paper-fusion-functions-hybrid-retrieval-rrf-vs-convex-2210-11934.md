---
schema_version: 1
artifact_id: N-SURVEY-20260928-08
artifact_type: note
producer: triage
run_id: survey-20260928T055608Z-7419
created_at: 2026-09-28T06:42:00Z
idempotency_key: note:survey:arxiv:2210.11934
input_refs: []
pillar_primary: R7
pillar_secondary: [R3]
beliefs_affected:
  supports: []
  contradicts: [B23]
evidence:
  directness: medium (fusion of a lexical and a semantic ranker over documents; not heterogeneous memory units)
  control: high (same retrievers, parametric RRF with separate k per ranker, several normalisations, in-domain and zero-shot BEIR, sample-efficiency curves)
  independence: medium (Pinecone researchers; vendor of a vector DB, no stake in RRF vs CC)
  reproducibility: medium (public datasets, PISA BM25, all-MiniLM-L6-v2; code not checked)
  applicability: medium (Engram fuses BM25, vector and graph channels; the finding is about the fusion function itself)
source_url: https://arxiv.org/abs/2210.11934
found_via: survey
---

# An Analysis of Fusion Functions for Hybrid Retrieval

- **URL:** https://arxiv.org/abs/2210.11934 (HTML v2 read at https://arxiv.org/html/2210.11934v2); journal DOI https://doi.org/10.1145/3596512
- **Type:** paper
- **Author / org:** Sebastian Bruch, Siyu Gai, Amir Ingber (Pinecone; Gai UC Berkeley intern)
- **Date:** v1 2022-10-21, v2 2023-05-04
- **Retrieved:** 2026-09-28
- **Cited by evidence:** top-down survey, R7 question 1 (B23)
- **Relevance to a memory stack:** medium-high, the best-known controlled comparison of RRF against score fusion, and it finds RRF's default is neither parameter-free nor best

## TL;DR
- RRF is "sensitive to its parameters": with separate k per ranker, RRF(5,5) beats RRF(60,60) on MS MARCO, HotpotQA and Quora, and RRF(10,4) moves NDCG by up to 5 points in either direction depending on dataset.
- A convex combination of normalised scores (theoretical min-max, alpha = 0.8, "TM2C2") beats RRF(60,60) on every dataset reported, in-domain and zero-shot, by about 1.5 to 3 NDCG points.
- alpha converges "with less than 5% of the training data", regardless of domain shift.
- RRF "disregards the distribution of scores and, as such, discards useful information".

## What it claims / describes
f_RRF(q,d) = 1/(eta_Lex + rank_Lex(q,d)) + 1/(eta_Sem + rank_Sem(q,d)), default eta = 60 for both. f_Convex = alpha * f_Sem + (1 - alpha) * f_Lex after normalisation (min-max, theoretical min-max, z-score, or none). BM25 via PISA (k1 = 0.9, b = 0.4, top 1000); semantic all-MiniLM-L6-v2 (cosine, top 1000). Metric NDCG@1000 (NDCG@100 for SciFact and NFCorpus).

## Numbers
| Dataset | RRF(60,60) | RRF(5,5) | RRF(10,4) | TM2C2 (CC) |
|---|---|---|---|---|
| MS MARCO | 0.425 | 0.435 | 0.451 | 0.454 |
| HotpotQA | 0.675 | 0.693 | 0.621 | 0.699 |
| Quora | 0.877 | 0.885 | 0.896 | 0.901 |
| NQ | 0.514 | n/r | n/r | 0.542 |
| NFCorpus (zero-shot) | 0.312 | n/r | n/r | 0.327 |
| Fever | 0.721 | n/r | n/r | 0.744 |
n/r = not reported in the extract read. Values as extracted from the HTML (not re-verified cell by cell).

## Mechanism details you could implement
- Replace a fixed RRF k=60 with a normalised convex combination, alpha tuned on a small labelled set (the paper: under 5 % of training queries).
- If RRF is kept, tune k per channel; a single shared k is a choice, not a neutral default.

## Limitations, caveats, counter-evidence
- Two rankers over one document collection; Engram fuses heterogeneous evidence units (events, entities, graph paths), where score scales may be incomparable and CC needs per-channel normalisation that may not exist (inference).
- Not re-tested with modern embedders; results from 2022/2023.

## Takeaways for tuning a memory stack
- B23 says RRF k=60 is "a reasonable baseline". This source says the default k is a tuned-looking constant that was not best on any dataset here, and a one-parameter score fusion beat it everywhere with little data. RRF(60) remains an acceptable floor, but H2 should not treat it as the fusion arm to beat without a tuned CC arm.

## Open questions
- Does CC keep its edge when one channel (graph traversal) has no calibrated score?
