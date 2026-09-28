---
schema_version: 1
artifact_id: N-SURVEY-20260927-16
artifact_type: note
producer: triage
run_id: survey-20260927T054501Z-e1b9
created_at: 2026-09-27T05:53:00Z
idempotency_key: note:survey:arxiv:2607.26520
input_refs: []
pillar_primary: R1
pillar_secondary: []
beliefs_affected: {supports: [B2], contradicts: []}
evidence: {directness: 3, control: 2, independence: 3, reproducibility: 1, applicability: 2}
source_url: https://arxiv.org/abs/2607.26520
found_via: survey
strength: paper-single-benchmark
---

# A Graph-Native Bitemporal Memory Store for Conversational AI Agents

- **URL:** https://arxiv.org/abs/2607.26520 (read via https://arxiv.org/html/2607.26520v1)
- **Type:** paper
- **Author / org:** Alp Niksarli, Gopesh Baheti (affiliation not captured)
- **Date:** 2026-07-29 (arXiv v1)
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, pillar R1, beliefs B2
- **Relevance to a memory stack:** medium, it is a measured as-of semantic retrieval path in an agent memory store, but inside a single natively versioned store, and it quantifies a failure mode of as-of vector search

## TL;DR

- Agent-local Neo4j property graph with HNSW vector indexes and a full bitemporal model (valid time and transaction time as closed-open intervals) on immutable versioned content nodes.
- Exposes a "time-travel" retrieval path: vector search over all versions, over-fetch 10x k, then Cypher post-filter on `valid_at` and transaction time. The vector index itself is not versioned; only filtered.
- On 60 sampled LongMemEval questions: current-state path 46.7% R@10 overall; time-travel path 80% R@10 on knowledge-update (same as current-state) but drops temporal-reasoning from 50% to 37.5%, attributed to "post-filter dilution".
- Single store (Neo4j). Embeddings come from an external, unversioned service (Amazon Titan Embed Text v2 via Bedrock). Does not contradict B2.
- No code released; n = 10 per question type.

## What it claims / describes

Schema: `:Memory` identity nodes (persistent identity) linked by `HAS_VERSION` to `:MemoryVersion` content nodes that carry the embedding and two intervals: valid time `[valid_from, valid_to)` ("when the fact was true in the world") and transaction time `[tx_from, tx_to)` ("when the database recorded it"); null upper bound means open. `RELATED_TO` edges between memories are created at write time using cosine similarity over 1024-dimensional embeddings. History is never physically overwritten.

Two retrieval paths:
1. Current-state: HNSW search over nodes labeled `:CurrentVersion` only.
2. Time-travel: HNSW search over the full `memory_version_embedding` index, over-fetching 10x k candidates, then post-filtering with Cypher, verbatim: `WHERE ($valid_at IS NULL OR (v.valid_from <= $valid_at AND (v.valid_to IS NULL OR v.valid_to > $valid_at)))` plus the corresponding transaction-time condition. Composite B-tree indexes on temporal columns accelerate the filter.

External dependencies: Amazon Titan Embed Text v2 (1024-d, AWS Bedrock) and Anthropic Claude (API or Bedrock).

## Numbers

LongMemEval, 60 questions sampled with seed=42, 10 per type from the 500-question benchmark. R@10t is the time-travel path.

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| R@10 overall, current-state | 46.7% (R@1 26.7%, R@5 46.7%) | none external | 60 questions | no comparison to other memory systems |
| knowledge-update R@10 | 80.0% current-state; 80.0% time-travel | each other | n=10 | abstract says "rising to 80% on knowledge-update" |
| temporal-reasoning R@10 | 50.0% current-state; 37.5% time-travel | each other | n=10; time-travel "computed over 8 non-null results (2 correctly returned empty)" | denominators differ (10 vs 8), so the drop is 5/10 vs 3/8 (inference from the footnote) |
| single-session-user R@10 | 90.0% | n/a | n=10 | time-travel not reported |
| multi-session R@10 | 30.0% | n/a | n=10 | requires counting across sessions |
| single-session-assistant R@10 | 20.0% | n/a | n=10 | assistant turns not indexed |
| single-session-preference R@10 | 10.0% | n/a | n=10 | synthetic summaries |
| Over-fetch factor | 10x k (100 candidates for k=10) | n/a | time-travel path | fixed, not tuned in reported results |
| Latency, storage, hardware | not stated | | | |
| Code | "No repository URL provided" | | | |

## Mechanism details you could implement

- Identity node plus immutable version nodes with two closed-open intervals is a straightforward bitemporal projection of an event ledger (transaction time corresponds to ledger position).
- Maintain a separate "current" label or index for the hot path, and a full-history vector index for as-of queries.
- Post-filter dilution fix proposed by the authors (verbatim): "Re-rank retrieved memories after filtering by combining cosine similarity with closeness to `valid_at`, instead of relying only on the initial vector search score."
- (inference) Alternative fix: pre-filter (filtered HNSW or per-epoch indexes) rather than post-filter, so the ANN candidate pool is drawn from versions valid at the target time.

## Limitations, caveats, counter-evidence

- Single store. As-of semantics are native to Neo4j here; nothing spans heterogeneous backends. This is another instance of the "native versioned store does it within one store" counter-evidence class already noted for B2, so it supports B2 as stated.
- The vector index is not versioned, and embeddings come from a hosted model that is not pinned in any way I extracted. (inference) If the embedding model version changes, the same as-of query would produce different candidates, so this is an L1.5 at best: the corpus rows are frozen, but the scoring function is not.
- n=10 per type; the 50% to 37.5% difference is 5 of 10 vs 3 of 8 and is not statistically meaningful on its own.
- No external baselines, no latency or storage numbers, no code.
- Several question types are out of reach for pure retrieval by the authors' own account (multi-session aggregation 30%, assistant content 20%).

## Takeaways for tuning a memory stack

- (inference) An as-of read built as "search the whole history, then filter by time" measurably changes what comes back compared to the current-state read even when the right item exists, so an F7 fixture over a natively versioned backend should check the retrieval pipeline shape, not only that the store holds history.
- (inference) Frozen corpus (L2) needs frozen scoring too: for vector channels that means pinning the embedding model and index parameters to the snapshot, analogous to frozen BM25 statistics in 2411.04051.
- A current-state label or index plus a full-history index is a cheap pattern to keep the hot path unaffected by history size.

## Open questions

- How does as-of recall change with over-fetch factor, or with pre-filtering instead of post-filtering?
- Is the embedding model version recorded per version node? Not stated in what I extracted.
- What are the storage and latency costs of the full-history index?

## Grading

- directness 3: implements and measures an as-of retrieval path in agent memory, but only in one store, so it does not test the cross-store part of B2.
- control 2: 60 questions, 10 per type, no external baselines, differing denominators.
- independence 3: independent authors with no evident vendor stake, but self-evaluated system.
- reproducibility 1: no code, hosted embedding model, hardware unstated; only the sampling seed is given.
- applicability 2: conversational memory benchmark, not engineering or build-time tasks; the dilution mechanism transfers, the numbers do not.
