---
schema_version: 1
artifact_id: N-20260930-02
artifact_type: note
producer: triage
run_id: triage-20260930T014506Z-8351
created_at: 2026-09-30T01:57:27Z
input_refs: [{"artifact_id": "post:2104953102831071283", "file_id": null, "sha256": null}, {"artifact_id": "post:2104973045245128999", "file_id": null, "sha256": null}, {"artifact_id": "post:2104979300558737678", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:lancedb.com/blog/how-jev-compares-to-other-rerankers
claim_cluster: url:lancedb.com/blog/how-jev-compares-to-other-rerankers
feeds: ["decision"]
primary_source: https://www.lancedb.com/blog/how-jev-compares-to-other-rerankers
source_commit: github.com/lancedb/research 99948ade6c0bcf8c96c17f314642a6855174269b (HEAD 2026-09-26, not read; results taken from the blog)
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R3", "R6"]
tags: {"mechanism": ["Jev noul relevance scoring per candidate", "prompt wording of relevance", "RRF hybrid baseline", "cross-encoder and ColBERT rerankers"], "workload": ["BEIR-style passage retrieval", "multi-hop QA"], "lifecycle_stage": ["reranking"], "cross_cutting": ["cost"]}
memory_stage: reranking
priority: 1
evidence_grade: {"directness": "high: the blog reports the reranking metric on the same candidates for every reranker", "control": "medium: same top-50 vector plus top-50 BM25 candidates and an RRF baseline for all; one run, no intervals; Jev prompt tuned on the test sets it reports", "independence": "medium: LanceDB is a database vendor with no stake in which reranker wins, but it integrates Jev in its product", "reproducibility": "medium: research repo at a known HEAD with pinned LanceDB revision; public datasets; Jev API scores vary between calls", "applicability": "medium: passage retrieval over public QA sets, not engineering artifacts or memory graphs"}
beliefs_affected: {"supports": ["B23", "B14"], "contradicts": [], "would_create": ["The relevance question given to a System One reranker changes accuracy by several points and can flip a loss against the RRF baseline into a gain; the question text is a tuned parameter"]}
claim_correction: The posts report HotpotQA Hit@1 63.52% to 72.87% vs no reranking and 85.24% with a better prompt; the blog also shows default-prompt Jev LOWERED HotpotQA hybrid Hit@10 below the RRF baseline (96.19% to 92.67%), and that Qwen3-4B (91.82%) and mxbai-large-v2 (93.25%) beat Jev's 85.24% Hit@1 on the same task.
---

# How Jev Compares to Other Rerankers (LanceDB blog): Jev (TypeSafe) against 19 reranker configurations on five datasets

- **URL:** https://www.lancedb.com/blog/how-jev-compares-to-other-rerankers
- **Type:** vendor blog (database vendor benchmarking a third-party model)
- **Author / org:** Taylor Smith and Ayush Chaurasia, LanceDB. Research code: https://github.com/lancedb/research
- **Date:** published 2026-09-29 (page metadata "datePublished 2026-09-29T21:11:02Z")
- **Retrieved:** 2026-09-30 (local copy: repos/lancedb.html; text extracted from the HTML because the page renders client side). Research repo HEAD `99948ade6c0bcf8c96c17f314642a6855174269b` (2026-09-26, "Merge pull request #9 from lancedb/ayush/base-reranker-benchmark") recorded via the GitHub API, not cloned or read.
- **Cited by evidence:** decision feed 2026-09-29: @lancedb (https://x.com/lancedb/status/2104953102831071283), @loldedxd (https://x.com/loldedxd/status/2104973045245128999), @BEBischof (https://x.com/BEBischof/status/2104979300558737678)
- **Relevance to a memory stack:** high. The widest public reranker comparison including Jev so far, with an RRF hybrid baseline like ours and a direct measurement of prompt sensitivity and score repeatability.

## TL;DR
- Same candidates for every reranker: top 50 vector (BAAI/bge-base-en-v1.5) + top 50 BM25, hybrid = deduplicated union of up to 100, baseline RRF. Five datasets: GooAQ (20,000 sampled queries vs 100,000 answers), NQ 3,452, HotpotQA 7,405, FiQA 648, SciDocs 1,000 queries.
- "No model wins everywhere." Hybrid Hit@10 leaders: Jev relevance prompt on GooAQ (92.59), jina-v3 on NQ (90.38), mxbai-large-v2 on HotpotQA (98.64), Qwen3-4B on FiQA (80.09) and SciDocs (71.60).
- Prompt matters: default Jev prompt ("answers or directly addresses the query") cut HotpotQA hybrid Hit@10 from RRF 96.19% to 92.67%; "Is the document relevant to the query?" raised it to 97.70% and Hit@1 72.87% to 85.24%.
- At Hit@1 Jev trails: HotpotQA 85.24% vs Qwen3-4B 91.82% and mxbai-large-v2 93.25% (they differ by only 0.94 points at Hit@10).
- Jev scores are rounded to 0.01 and not repeatable: "Rescoring produced identical values 74% of the time and values within 0.01 94% of the time." Jev p50 about 169 to 269 ms via API, p95 roughly 1.2 to 1.5 s.

## What it claims / describes
**Setup.** "LanceDB retrieved the same top 50 vector candidates and top 50 BM25 candidates for every reranker. Hybrid reranking used their deduplicated union, up to 100 passages; its baseline was reciprocal rank fusion (RRF). Embeddings came from BAAI/bge-base-en-v1.5. NQ and HotpotQA used an IVF_PQ index; the other datasets used exact vector search. No relevant document was inserted into the shortlist." Hit@k = percentage of queries with at least one labelled relevant document in the first k. GooAQ uses exact answer-string matches; BEIR sets use their relevance labels. "On HotpotQA, a hit does not mean that both supporting passages were retrieved."

**How Jev is used.** "LanceDB retrieves candidates, and Jev scores each one against a specific question. The application uses those scores to reorder results or apply a semantic filter." The question is plain language; the example is asking whether a guest review "supports a preference for quiet nights". Batched Jev requests are supported in the pinned LanceDB revision. The blog's figure describes per-review yes/no probability (a noul per candidate, inference from "scores each one").

**Prompt finding.** The default question in the benchmark's LanceDB version "asks whether a document answers or directly addresses the query. That can be too restrictive for multi-hop questions ... a useful bridge passage may identify an entity or establish a fact without answering the full question on its own." Changing to "Is the document relevant to the query?", counting partial help as relevant, "matched or beat the default" (figure: improves hybrid Hit@10 on all five datasets).

**Other findings.** Reranking helps BM25 most (NQ full-text Hit@10 48.61% to 69.81% with jina-v3; FiQA best 49.38% to 65.74%). "On both GooAQ and SciDocs, 13 of the original 19 configurations score below plain vector search at Hit@10." Qwen3-8B has no consistent advantage over 4B and takes about 1.5x as long. ColBERT token pooling by 2x roughly halves storage (GTE-ModernColBERT on GooAQ 13.7 KB to 6.9 KB per document) with Hit@10 89.39% to 89.27%.

## Numbers
Hybrid Hit@10 (%), p50 range across the five datasets (ms). Open models on one H100, one query at a time; Jev via API with eight queries and up to 32 requests in flight, network included.

| reranker | GooAQ | NQ | HotpotQA | FiQA | SciDocs | p50 ms |
|---|---|---|---|---|---|---|
| No reranker (RRF) | 81.91 | 72.25 | 96.19 | 66.51 | 58.80 | - |
| Jev default (API) | 92.17 | 86.88 | 92.67 | 78.40 | 64.70 | 173-269 |
| Jev relevance (API) | **92.59** | 87.40 | 97.70 | 78.70 | 65.90 | 169-235 |
| MiniLM-L6 | 83.70 | 80.82 | 97.39 | 66.20 | 52.80 | 19-91 |
| gte-modernbert | 87.05 | 83.52 | 97.70 | 75.62 | 60.10 | 37-165 |
| bge-v2-m3 | 87.52 | 88.44 | 98.53 | 69.75 | 56.20 | 38-149 |
| mxbai-large-v2 | 89.99 | 89.51 | **98.64** | 76.85 | 57.90 | 198-536 |
| Qwen3-0.6B | 86.69 | 84.82 | 98.26 | 74.38 | 61.80 | 161-446 |
| Qwen3-4B | 90.61 | 89.37 | 98.42 | **80.09** | **71.60** | 510-1,509 |
| Qwen3-8B | 91.22 | 88.73 | 98.38 | 79.94 | 69.20 | 750-2,327 |
| zerank-2 | 92.00 | 87.86 | 96.06 | 77.62 | 63.30 | 335-1,495 |
| jina-v3 | 90.59 | **90.38** | 98.57 | 74.07 | 66.70 | 100-449 |
| answerai-colbert-small 1x / 2x / 4x | 87.55 / 87.09 / 85.98 | 83.05 / 82.76 / 80.71 | 97.83 / 97.70 / 96.56 | 69.91 / 69.60 / 68.36 | 56.70 / 55.50 / 55.60 | 36-76 / 28-49 / 24-37 |
| gte-moderncolbert 1x / 2x / 4x | 89.39 / 89.27 / 88.47 | 84.41 / 84.50 / 82.94 | 98.07 / 97.96 / 97.15 | 73.30 / 73.15 / 72.07 | 58.80 / 58.50 / 57.60 | 39-70 / 35-52 / 33-42 |
| jina-colbert-v2 1x / 2x / 4x | 88.08 / 87.52 / 79.61 | 85.34 / 85.49 / 77.46 | 97.92 / 97.73 / 93.53 | 71.91 / 71.60 / 63.58 | 57.10 / 56.30 / 51.60 | 56-101 / 51-68 / 44-54 |

| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| HotpotQA hybrid Hit@1, Jev | 72.87% default, 85.24% relevance prompt | Qwen3-4B 91.82%, mxbai-large-v2 93.25% | 7,405 queries | the three differ by 0.94 points at Hit@10, 8.01 at Hit@1 |
| GooAQ vector Hit@10, Jev | 90.31% to 92.60% (+2.29) | vector baseline | 20,000 queries | |
| Jev latency | median "near 200 ms", p95 "roughly 1.2-1.5 seconds" | open models on H100 | API incl. network, rate-limited queries timed from last attempt | |
| Jev score repeatability | identical 74%, within 0.01 94% | | rescoring | ties broken by original candidate order |
| cost per query | not stated | | | |

## Mechanism details you could implement
- Candidate construction to copy: top 50 vector + top 50 BM25, dedup union (up to 100), RRF as the no-rerank baseline.
- Treat the relevance question as a hyperparameter: for multi-hop or bridge evidence, ask "Is the document relevant to the query?" and define partial help as relevant, rather than "does it answer the query".
- Jev scores are rounded to 0.01, so many ties: break ties by the original (RRF) order, and record that tie rule for replay.
- Evaluate at the cutoff you actually serve: Hit@10 hides an 8-point Hit@1 gap.
- Validate prompt and any score threshold "on held-out examples" (the blog's own advice); the blog's own relevance prompt was chosen with knowledge of the test sets (inference from the narrative).

## Limitations, caveats, counter-evidence
- One run per configuration, no confidence intervals; relevance prompt selected after seeing the HotpotQA failure (inference: optimistic for the prompt row).
- Different hardware and concurrency for Jev (API, 32 in flight) vs open models (H100, one at a time); timing excludes embedding and retrieval.
- Cost per query not reported; the post calls Jev "a good default reranker (based on cost and speed)" without a cost table in the blog.
- Hit@k counts any relevant passage; multi-hop completeness is not measured.
- Consistent with the synthesis finding that Jev is not the cheapest good reranker on clean text (`x-article-supermemory-jev-memory-context.md` SciFact numbers) and with `github-hev-reranker-jev-as-a-reranker.md`.

## Takeaways for tuning a memory stack
- Keep RRF hybrid as the baseline every reranker must beat per dataset: on HotpotQA default-prompt Jev lost to it.
- If Jev reranks linked evidence (bridge facts in the context graph), use a "relevant, even partially" question; a strict "answers the query" question drops bridge nodes.
- A self-hosted Qwen3-4B or mxbai-large-v2 reranker is a credible open-weight comparison arm with better Hit@1 on HotpotQA, at 0.5 to 1.5 s p50 on an H100.
- Store rerank scores and tie order in the receipt: Jev rescoring gives identical values only 74% of the time.

## Open questions
- Cost per 1,000 queries for each arm? Not stated.
- How does Jev rank at K=100 compare with a choice (listwise) call over the same pool? Only per-candidate scoring was measured (inference).
- Would the relevance prompt hold on held-out datasets not used to choose it?

## Grading and labels
- Directness high; control medium (same candidates and baseline, single run, prompt tuned on test sets); independence medium (vendor-neutral on rerankers, but a Jev integrator); reproducibility medium (repo and pinned LanceDB revision, public data, nondeterministic Jev scores); applicability medium (public QA passages).
- Pillars: R9 primary (Jev vs open rerankers at the reranking stage), R3 (retrieval assembly), R6 (evaluation cutoffs). Memory stage: reranking. Priority 1.
- Beliefs: supports B23 (RRF k=60 hybrid is a reasonable baseline: 13 of 19 configurations fall below plain vector search on two datasets, and default Jev falls below RRF on HotpotQA). Supports B14 (scores rounded and not repeatable, so absolute thresholds need local fitting). Would create: relevance-question wording is a tuned parameter of a System One reranker.
- Contradiction rows: none against held beliefs.

## Origin chain
@lancedb post (2104953102831071283) and @loldedxd (2104973045245128999), quoted by @BEBischof (2104979300558737678) -> lancedb.com blog (2026-09-29) -> summary table (hybrid Hit@10), "Jev" prompt section, latency section and repeatability paragraph -> this note. Independence: LanceDB authors; public datasets (GooAQ, BEIR NQ/HotpotQA/FiQA/SciDocs); no shared authors with TypeSafe or with hev/reranker.
