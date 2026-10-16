---
schema_version: 1
artifact_id: N-20260927-08
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103836188977279136", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:hev/reranker
claim_cluster: github:hev/reranker
feeds: ["decision", "memory"]
primary_source: https://github.com/hev/reranker
source_commit: 1eb47266270b32b2a3667f9fb89646378ca9c9d6
strength: repo-pinned
pillar_primary: R4
pillar_secondary: ["R3", "R6"]
tags: {"mechanism": ["decision-model reranker", "per-document Noul vs single Choice", "absolute probability scores", "BM25 top-30 shortlist", "paired bootstrap"], "workload": ["BEIR SciFact", "BEIR NFCorpus", "BEIR FiQA"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: nDCG@10, P@1, MRR, latency and cost per system on the same shortlists", "control": "high: every reranker permutes the same BM25 top-30; paired per-query bootstrap; position-bias and determinism checks; Choice vs Noul on the same model", "independence": "medium: independent builder (Adam Hevenor), not TypeSafe; public BEIR sets", "reproducibility": "high: pinned commit, prompt.yaml, schema and 90-line wrapper published, jev-1.13.0 named", "applicability": "medium: document reranking on public IR sets, not chat memory or engineering artifacts"}
beliefs_affected: {"supports": ["B11"], "contradicts": ["B10"], "would_create": ["Per-document Noul scoring in one request beats a single Choice over the pool when many candidates are relevant (NFCorpus 0.358 vs 0.315) and is within 0.01 when one is (SciFact); Noul scores are absolute and comparable across calls"]}
claim_correction: the post's comparator "Mixedbread's listwise reranker at 0.511" is not in the repo tables at the pinned commit (hosted mxbai-rerank-large-v2 averages about 0.476 there); the blog was updated 2026-09-24, after the pinned commit of 2026-09-17
---

# Jev as a reranker (hev/reranker, Adam Hevenor)

- **URL:** https://github.com/hev/reranker (blog: https://hevmind.com/writing/jev-as-a-reranker/)
- **Type:** repo (plus builder writeup)
- **Author / org:** Adam Hevenor (hevmind); PyPI package `hev-rerank`
- **Date:** blog 2026-09-17, updated 2026-09-24; RESULTS.md "Generated 2026-09-17. Jev model jev-1.13.0."
- **Retrieved:** 2026-09-27, commit `1eb47266270b32b2a3667f9fb89646378ca9c9d6` (2026-09-17 14:47:19 -0600, "Point package URLs and schema ids at github.com/hev/reranker"); local copy repos/hev-reranker. Read: README.md, RESULTS.md; blog page.
- **Cited by evidence:** @hevmind https://x.com/hevmind/status/2103836188977279136
- **Relevance to a memory stack:** high for the rerank design decision. It directly tests the question behind B10 (one Choice over the pool vs per-item questions) on public data with paired intervals, and gets a different answer when many candidates are relevant.

## TL;DR
- Every system reranks the same BM25 top-30 per query; nDCG@10 on SciFact (300 q), NFCorpus (323 q), FiQA (300 q).
- Jev with 30 Nouls in one state: 0.768 / 0.358 / 0.376 (mean about 0.501); Voyage rerank-3: 0.755 / 0.357 / 0.402 (about 0.504); Cohere v3.5: 0.745 / 0.340 / 0.374; GPT-5.6 Luna listwise 0.747 / 0.355 / 0.363; Opus 5 low effort listwise SciFact 0.756 at $28.40 per 300 queries.
- **Choice vs Noul:** one Choice over the documents is "+0.01 nDCG@10, +3 pts P@1" on SciFact (about one relevant doc per query) but "much worse when many are": NFCorpus (median 16 relevant per query) 0.315 Choice vs 0.358 Noul batch.
- Cost per 300 queries: Jev batch $0.13 to $0.19; Voyage about $0.15; Cohere $0.60; Mixedbread hosted $1.05. p95 for the 30-document state 0.8 to 1.8 s (higher than dedicated rerankers).
- Noul scores behave like absolute probabilities: documents scored >= 0.9 were relevant 76% of the time; < 0.1, 0.5% of the time (SciFact). Determinism: mean |delta| 0.004 over 900 re-issued pairs, zero top-1 changes.

## What it claims / describes
- State: `{"query": ..., "documents": {"D00": {...}, "D01": {...}, ...}}`; questions: one Noul per document id from `prompt.yaml`, domain-neutral wording, untuned per corpus. The blog quotes the Noul: "Document `documents.{id}` is relevant to `query`: it contains information that answers or directly addresses it." All questions in a request run in parallel, "so 30 documents cost about the same wall time as 5".
- Lists longer than `max_docs_per_call` (30) are split into concurrent calls under Jev's ~32k-token budget; "Scores across calls are comparable because each is an absolute probability."
- Optional `threshold=0.1` drops candidates the model is confident are irrelevant.
- Author's summary: "a general decision model with no reranker training lands in the same quality and price bracket as the best purpose-built rerankers, a third of Cohere's price... Voyage rerank-3 is as good and slightly cheaper".

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| nDCG@10 SciFact test | Jev batch 0.768; Jev per-pair 0.772; Jev Choice 0.760 | Voyage-3 0.755; Opus 5 low 0.756; Cohere 0.745; MiniLM 0.682; BM25 0.667 | 300 q, BM25 top-30 | RESULTS.md |
| nDCG@10 NFCorpus | Jev batch 0.358; Jev Choice 0.315 | Voyage-3 0.357; Cohere 0.339; Mixedbread 0.324; BM25 0.310 | 323 q, median 16 relevant per query | Choice loses 0.043 |
| nDCG@10 FiQA | Jev batch 0.376; Choice 0.358 | Voyage-3 0.402; Cohere 0.374 | 300 q | Jev loses to Voyage by about 0.02 |
| cost per run (300 q) | Jev batch $0.13 to $0.19; per-pair $0.23 to $0.30 | Voyage $0.15 to $0.23; Cohere $0.60 to $0.65; Mixedbread $1.05 to $1.13; Luna $0.49 to $0.76; Opus 5 $28.40 | list price x actual tokens | blog: $0.54 per 1,000 queries |
| latency p50 / p95 | Jev batch 208 to 238 ms / 0.8 to 1.8 s; per-pair 122 to 144 ms per call | Voyage 173 to 192 / 285 to 288 ms | laptop, network included | |
| calibration (SciFact) | score >= 0.9: 76% relevant; < 0.1: 0.5% relevant | | README | single corpus |
| determinism | mean abs delta 0.004, max 0.14, 0 top-1 changes | | 30 requests re-issued, 900 pairs | |
| position bias | per-doc Spearman 0.83 (30-Noul state), 0.92 (Choice); nDCG within 0.005 on reversal | | RESULTS.md validation | |
| significance | paired per-query bootstrap: at or above Cohere on all three (2 wins, 1 tie); vs Voyage: edge SciFact, tie NFCorpus, loss FiQA | | README | |

## Mechanism details you could implement
- Rerank by asking one yes/no (Noul) per candidate inside a single request, not one Choice over the pool, whenever several candidates can be relevant (typical for build-time evidence gathering). Keep Choice only when exactly one answer is expected.
- Because per-document probabilities are absolute, you can merge scores across split requests and across queries, and set an admission threshold separately from ranking (supports B11's rerank vs admission split).
- Batch 30 documents per call to stay inside the 32k-token budget; fan out per-pair calls if p95 matters (30x calls, p95 about 0.25 s per call).
- Watch for 429s: "sustained 429s appeared at ~24 requests in flight".

## Limitations, caveats, counter-evidence
- README limits: ~32k tokens per request (30 to 50 passages); undocumented rate limits; higher tail latency; hosted only, data leaves your environment.
- Blog: public benchmarks may be in training data; rerank depth fixed at 30 while hosted competitors accept deeper lists.
- Only BM25 first stage; no fusion (B23) first stage tested.
- The blog's "Mixedbread listwise 0.511" comparator is not in the pinned repo tables; treat it as unverified.
- Calibration figure from one corpus; not an ECE.

## Takeaways for tuning a memory stack
- For our rerank design, the question shape should follow the expected number of relevant items: per-item Nouls for multi-evidence reads, Choice for single-answer picks.
- Do not treat Jev rerank scores as within-call ranks only; with Noul they are usable absolute scores (this revises the synthesis section 2 row "Jev scores are rank positions within one call", which was about Choice).
- On cost, a hosted decision-model reranker here is priced like Voyage and a third of Cohere; the synthesis's "about 10x self-hosted" figure came from a different comparison (self-hosted models on SciFact at 100 candidates) and still stands for that setting.

## Open questions
- Does Noul-over-Choice hold on LoCoMo-style chat memory, where Hindsight found Choice better (B10)?
- Behaviour with fused first-stage candidates and deeper pools (100+)?
- Calibration across corpora (ECE)?

## Grading and labels
- Directness high; control high; independence medium; reproducibility high; applicability medium.
- Pillars: R4 primary (reranker as a candidate decision implementation; question shape); R3 secondary (read-time selection); R6 secondary (paired bootstrap, position-bias checks).
- B10 contradicts (scope): B10 says a single Choice over the pool beat per-item yes/no on LoCoMo-200. Here per-item Nouls in one request beat a single Choice by 0.043 nDCG@10 on NFCorpus (many relevant) and 0.018 on FiQA, and trail by about 0.01 on SciFact (one relevant). Open row: "Contradiction: B10 listwise Choice > per-item vs hev/reranker RESULTS.md NFCorpus/FiQA". Note the comparison differs: B10's pointwise arm was one call per candidate; here both arms are one request, so it contradicts the generalisation of B10, not its LoCoMo number.
- B11 supports: separate admission threshold (absolute probabilities) from ranking.
- B23: not tested (BM25-only first stage).
- Would create: per-item Noul beats Choice when many candidates are relevant.

## Origin chain
post 2103836188977279136 (@hevmind) -> hevmind.com blog (2026-09-17, updated 2026-09-24) -> github.com/hev/reranker at 1eb47266 -> README Results table, "The shape, and why", Limits; RESULTS.md per-corpus tables and validation (determinism, position bias) -> this note. Independence: builder independent of TypeSafe, Hindsight and Supermemory; BEIR data public; Jev jev-1.13.0.
