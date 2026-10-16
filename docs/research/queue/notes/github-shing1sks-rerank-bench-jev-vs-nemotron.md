---
schema_version: 1
artifact_id: N-20260928-05
artifact_type: note
producer: triage
run_id: triage-20260928T014503Z-edff
created_at: 2026-09-28T01:55:04Z
input_refs: [{"artifact_id": "post:2104119229993939274", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:shing1sks/rerank-bench
claim_cluster: github:shing1sks/rerank-bench
feeds: ["decision", "memory"]
primary_source: https://github.com/shing1Sks/rerank-bench
source_commit: 0c22bb2235f38a773aac87ade5f7828dd30f7cbe
strength: repo-pinned
pillar_primary: R4
pillar_secondary: ["R3"]
tags: {"mechanism": ["listwise rerank", "pointwise rerank", "Jev choice", "Jev noul", "cross-encoder", "Nemotron VL"], "workload": ["document QA retrieval", "long documents", "multimodal pages"], "lifecycle_stage": ["read-time ranking"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: recall@k, MRR, nDCG and latency of each reranker on identical 30-candidate lists", "control": "medium: identical candidates and truncation across arms, embedding-only baseline, but one run and no variance estimates", "independence": "high: individual builder, no vendor affiliation to TypeSafe or NVIDIA stated; different dataset and author from Hindsight and hev/reranker", "reproducibility": "high: pinned commit, cached per-query artifacts, report regenerable without API access, 75 tests", "applicability": "medium: document QA chunks, not agent memory; 175 handmade queries"}
beliefs_affected: {"supports": ["B10"], "contradicts": [], "would_create": ["On document QA, an off-the-shelf multimodal cross-encoder (Nemotron VL) beat Jev listwise by 0.165 recall@1 (0.797 vs 0.632) on the same candidates, at higher tail latency"]}
claim_correction: The post says Jev is "2-10 times faster" but Nemotron "had an edge over accuracy"; the edge is large (recall@1 0.797 vs 0.632, MRR 0.918 vs 0.817), and the 2x median speedup (982 vs 1,935 ms) rises to about 13x only at p95 (1,421 vs 18,609 ms) on a free, queued endpoint.
---

# rerank-bench: Jev (listwise and pointwise) vs NVIDIA Nemotron VL cross-encoder (shing1Sks/rerank-bench)

- **URL:** https://github.com/shing1Sks/rerank-bench (report `docs/reports/rerank-bench-paper.pdf` / `.md`)
- **Type:** repo with technical report
- **Author / org:** shing1Sks (X: @ShreyashAtX); individual
- **Date:** commit `0c22bb2235f38a773aac87ade5f7828dd30f7cbe`, 2026-09-27 01:51:45 +0530 ("Merge pull request #1 from shing1Sks/dev")
- **Retrieved:** 2026-09-28; README via WebFetch; shallow clone `repos/rerank-bench`; read `docs/reports/evaluation-method.md` (sections 1 and 8). Code not executed.
- **Cited by evidence:** @ShreyashAtX, https://x.com/ShreyashAtX/status/2104119229993939274
- **Relevance to a memory stack:** high for rerank design. An independent, pinned comparison of the two Jev call shapes (one listwise choice vs per-candidate noul) plus a cross-encoder, on identical candidate lists.

## TL;DR
- 175 handmade queries over 12 real documents (1,992 chunks): 40 verbatim, 40 paraphrase, 30 reasoning, 20 negative, 20 structural, 25 graphical. 155 scorable (negatives have empty gold and return None on gold metrics).
- Candidates: top 30 chunks by embedding similarity per query, identical for every arm.
- Recall@1: embed-only 0.532, Nemotron VL 0.797, Jev listwise 0.632, Jev pointwise 0.597. MRR: 0.716 / 0.918 / 0.817 / 0.781.
- Jev listwise (one `choice` call over 30 candidates) beats Jev pointwise (30 parallel `noul` calls) on every metric, at 982 vs 7,687 ms p50 and $0.58 vs $0.92 per 1,000 queries: an independent replication of the call-shape direction in B10.
- Cross-encoder wins quality; Jev listwise wins tail latency (p95 1,421 ms vs 18,609 ms). Whole benchmark cost $0.26, zero errors.

## What it claims / describes
Four arms on the same candidates: `embed_only` (the order to beat), `nemotron_vl` (OpenRouter `POST /api/v1/rerank`, graphical queries also send the rendered PDF page image), `jev_listwise`, `jev_pointwise`. Listwise (evaluation-method.md): "One SystemOne `choice` call per query. The state contains the query and all 30 candidates (each truncated to 800 tokens ...). The single question offers every candidate id as a criterion; the model returns per-candidate probabilities and the arm sorts by them." Pointwise: "30 parallel SystemOne `noul` calls per query (thread pool, 8 workers), one per candidate: 'Does this passage answer the query? Passage: ...'". A judge layer (Jev as judge, seeded sample, seed 13) adds a pairwise view but "do[es] not carry conclusions on [its] own".

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| recall@1 | Jev listwise 0.632 | embed 0.532; Nemotron 0.797; Jev pointwise 0.597 | 155 scorable queries, 30 candidates | single run |
| recall@5 | Jev listwise 0.923 | embed 0.842; Nemotron 0.923; pointwise 0.890 | same | tie with Nemotron |
| recall@10 | Jev listwise 0.948 | embed 0.913; Nemotron 0.942; pointwise 0.932 | same | |
| MRR | Jev listwise 0.817 | embed 0.716; Nemotron 0.918; pointwise 0.781 | same | |
| nDCG@10 | Jev listwise 0.837 | embed 0.750; Nemotron 0.905; pointwise 0.805 | same | |
| latency p50 / p95 | listwise 982 / 1,421 ms | Nemotron 1,935 / 18,609 ms; pointwise 7,687 / 9,320 ms | residential US path | Nemotron on a free queued endpoint |
| cost per 1,000 queries | listwise $0.58 | pointwise $0.92; Nemotron $0 (free endpoint) | | |
| reasoning queries | max recall@1 0.417 (any arm) | | 30 queries | "unsolved" |
| graphical queries recall@1 | Nemotron 0.880 | embed 0.440 | 25 queries | multimodal advantage |
| noise floor | "a recall@1 difference of ~0.05 is within noise" | | n = 155 | author's caveat |

## Mechanism details you could implement
- Rerank call shape: one listwise `choice` over candidate ids with per-candidate text truncated to about 800 tokens; sort by returned probabilities. Avoid per-candidate noul fan-out (8x latency, 1.6x cost, lower quality here).
- Protocol worth copying for our H5-rerank: identical candidate sets per arm, identical truncation helper, negatives scored separately (empty gold returns None, "scoring negatives as" zeros would distort), per-query cache and committed artifacts.

## Limitations, caveats, counter-evidence
- Author (section 8): "Single run per configuration; no variance estimates. With n = 155 scorable queries, a recall@1 difference of ~0.05 is within noise; the headline gaps (0.10-0.27) are not." Listwise vs pointwise recall@1 gap is 0.035, within that noise; the latency and cost gaps are not (inference).
- Per-type cells are n = 20 to 40.
- Queries and documents handmade by the author; not agent memory; no "none relevant" handling tested for the rerankers (negatives excluded from gold metrics).
- Contrast with Hindsight's LoCoMo-200 numbers (Jev 0.94 recall@1; github-vectorize-io-hindsight.md): different data and no cross-encoder arm there, so not a contradiction.

## Takeaways for tuning a memory stack
- If using Jev to rerank, use the listwise shape (B10 direction replicated independently, on documents rather than chat memory).
- Include a cross-encoder arm in any rerank experiment: here it beat Jev listwise by a margin well above noise.
- Watch tail latency, not only p50, when choosing a hosted reranker.

## Open questions
- Does Jev listwise close the gap with a paid, low-latency cross-encoder endpoint?
- Behaviour with a "none" option on the 20 negative queries (relevant to B11).

## Grading and labels
- Directness high; control medium; independence high; reproducibility high; applicability medium.
- Pillars: R4 primary (reranker as a decision component), R3 secondary (read-time ranking under a candidate budget). Tags: cost.
- Beliefs: supports B10 (single choice call beat per-item yes/no on quality, latency and cost; now on a second dataset by an unrelated author). Would create a belief that a cross-encoder beats Jev listwise on document QA. No contradiction with a held belief. Relation to bus: complements github-hev-reranker-jev-as-a-reranker.md (N-20260927-08) and card PC-20260927-03 with another independent pinned benchmark; no new card.

## Origin chain
post 2104119229993939274 (@ShreyashAtX) -> repo at 0c22bb2 -> README results table, docs/reports/evaluation-method.md sections 1 and 8 -> this note. Independence: no shared author, dataset or harness with Hindsight, hev/reranker or jevmem.
