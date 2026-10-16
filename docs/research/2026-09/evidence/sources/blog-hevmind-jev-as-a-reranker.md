---
schema_version: 1
artifact_id: N-20260927-22
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2104010850675945547", "file_id": null, "sha256": null}, {"artifact_id": "post:2104025279027159186", "file_id": null, "sha256": null}, {"artifact_id": "post:2104010209886929167", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:hevmind.com/writing/jev-as-a-reranker
claim_cluster: url:hevmind.com/writing/jev-as-a-reranker
feeds: ["decision"]
primary_source: https://hevmind.com/writing/jev-as-a-reranker/
source_commit: 1eb47266270b32b2a3667f9fb89646378ca9c9d6
strength: builder-report
pillar_primary: R4
pillar_secondary: ["R3", "R6"]
tags: {"mechanism": ["per-document-noul-rerank", "listwise-choice-rerank", "llm-as-reranker"], "workload": ["BEIR", "SciFact", "NFCorpus", "FiQA"], "lifecycle_stage": ["rerank"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: the blog reports a three-dataset mean table; the pinned RESULTS.md gives per-dataset rows", "control": "medium: every reranker permutes the same BM25 top-30 shortlist; Opus 5 refused 12/300 SciFact claims scored as zero", "independence": "low: author of the reranker library runs the comparison", "reproducibility": "medium: pinned RESULTS.md at 1eb4726 with determinism and position-bias checks; blog's newer rows (Jina, Qwen3-Reranker, BGE, mxbai v3.1) have no commit", "applicability": "medium: shortlist rerank is our read path; BEIR corpora, not engineering artifacts"}
beliefs_affected: {"supports": ["B11", "B14"], "contradicts": ["B10"], "would_create": []}
claim_correction: The post says Jev "scores higher (0.768)" than Opus 5 (0.756) on SciFact; the pinned README calls this a tie ("on quality except Opus 5, which it ties"), and the 0.756 counts 12 Opus refusals as zero (0.778 with BM25 order substituted on those queries, above Jev).
---

# "Jev as a reranker" (hevmind.com), with the pinned hev/reranker results it draws on

- **URL:** https://hevmind.com/writing/jev-as-a-reranker/
- **Type:** builder writeup
- **Author / org:** hev (@hevmind), author of the `hev-rerank` library (github.com/hev/reranker)
- **Date:** posted 2026-09-27 per the X post; blog date not captured
- **Retrieved:** 2026-09-27. Also read: https://raw.githubusercontent.com/hev/reranker/1eb47266270b32b2a3667f9fb89646378ca9c9d6/RESULTS.md and README.md at the same commit (saved under repos/hev-reranker-*-1eb4726.md).
- **Cited by evidence:** @hevmind https://x.com/hevmind/status/2104010850675945547 ; https://x.com/hevmind/status/2104025279027159186 ; https://x.com/hevmind/status/2104010209886929167 . Existing bus note on the repo: `github-hev-reranker-jev-as-a-reranker.md` (N-20260927-08). New here: the LLM-reranker and additional purpose-built reranker comparison, the Opus refusal caveat, and a contradiction row against B10.
- **Relevance to a memory stack:** medium. It is the only source in the catalogue that pits per-document Nouls against a single listwise Choice on corpora with many relevant documents, and it goes the other way from the LoCoMo result behind B10.

## TL;DR
- Blog (three-dataset mean nDCG@10, BM25 top-30): Jev batch 0.501 ($0.54/1k, p50 223 ms), Jev single 0.502 ($0.87/1k, 131 ms), Mixedbread mxbai-rerank-v3.1-listwise 0.511 ($1.42/1k, 217 ms), Voyage 0.504 ($0.50/1k, 185 ms), Jina 0.492 ($0.47/1k, 303 ms), Cohere 0.486 ($2.00/1k, 192 ms). Jev batch p95 about 1.4 s vs under 500 ms for purpose-built rerankers.
- LLM rerankers on SciFact: Opus 5 (low effort) 0.756 at $94.68 per 1,000 queries (the RESULTS.md run cost $28.40 for 300), 5.0 s p50; Jev 30 Nouls in one state 0.768 at about $0.60/1k, 224 ms.
- Pinned README: "Why not one Choice over the documents? It is slightly better when exactly one document is relevant (SciFact: +0.01 nDCG@10, +3 pts P@1) and much worse when many are (NFCorpus, median 16 relevant per query: 0.316 vs 0.358)."
- Contradiction: B10 (single Choice beat per-item yes/no on LoCoMo-200) does not generalise to multi-relevant corpora.

## What it claims / describes
State `{"query": ..., "documents": {"D00": {...}, ...}}`; one Noul per document from `prompt.yaml` in one request ("30 documents cost about the same wall time as 5"); score = Noul probability, so scores across calls are comparable. Lists longer than 30 are split into concurrent calls under Jev's ~32k-token budget. Optional `threshold=0.1` drops candidates the model is confident are irrelevant.

## Numbers

Pinned RESULTS.md (generated 2026-09-17, jev-1.13.0, BM25 top-K via rank_bm25, nDCG@10 via ir_measures):

| corpus (queries) | Jev 30 Nouls/state | Jev pair Noul | Jev Choice (generic) | Voyage rerank-3 | Cohere v3.5 | Opus 5 low | BM25 |
|---|---|---|---|---|---|---|---|
| SciFact test (300) | 0.768 | 0.772 | 0.760 | 0.755 | 0.745 | 0.756 | 0.667 |
| NFCorpus test (323) | 0.358 | 0.358 | 0.315 | 0.357 | 0.339 | not run | 0.310 |
| FiQA test (300) | 0.376 | 0.376 | 0.358 | 0.402 | 0.374 | not run | 0.234 |

Non-generic prompt variants on SciFact test: `jev_choice` 0.762 (P@1 0.710) vs `jev_batch` 0.756 (P@1 0.683), which is the README's "+0.01 nDCG@10, +3 pts P@1". With the generic prompt the direction reverses on SciFact test (Choice 0.760 vs batch 0.768). NFCorpus Choice is 0.315 in RESULTS.md and 0.316 in README.md at the same commit (rounding inside the source).

Validation (RESULTS.md): determinism, 900 Noul pairs re-issued, mean |delta| 0.004, max 0.14, zero top-1 changes; position bias, reversed order, per-doc Spearman 0.83 (30-Noul state) and 0.92 (Choice), nDCG@10 within 0.005; calibration (pair Nouls) p >= 0.9 judged relevant 76%, p < 0.1 0.5%; random permutation floor 0.12; "Claude Opus 5 refused 12/300 claims (safety classifier); scored as zero in the table, 0.778 with BM25 order substituted on those queries."

Intervals: the README says paired bootstrap per query was run and that RESULTS.md has "confidence intervals", but RESULTS.md at 1eb4726 contains no interval columns. Per-query outputs are not in these two files.

## Mechanism details you could implement
- For a reranker that does not know how many documents are relevant, ask one Noul per document in one batched state; use Choice only when exactly one answer is expected.
- Scores are absolute probabilities across calls (unlike listwise Choice ranks), so they can be merged across split calls and thresholded after local calibration (76% precision at p >= 0.9 here).
- Budget p95, not p50: Jev batch p95 was 0.8 to 1.8 s in these runs.

## Limitations, caveats, counter-evidence
- Author of the library runs the benchmark. The blog's newer rerankers have no pinned run.
- Opus refusals depress its SciFact score; with substitution it beats Jev (0.778).
- BEIR corpora are not engineering artifacts; 300 to 323 queries each; no answer-level evaluation.
- Hindsight 0.10.1 (`vendor-hindsight-0-10-1-jev-reranker-pool-240.md`) and the Vectorize article report listwise Choice beating pointwise on LoCoMo, where questions have few gold items; the two results are consistent with the relevant-count explanation (inference).

## Takeaways for tuning a memory stack
- Choose rerank shape by expected number of relevant items: Choice for single-answer lookups, per-item Noul for multi-relevant evidence gathering (the typical build-time read, inference).
- A decision-model reranker sits in the same quality bracket as Voyage and Cohere at similar cost; LLM rerankers cost 50 to 150 times more for no quality gain.

## Open questions
- Per-query paired intervals for Choice vs Noul on NFCorpus.
- The same comparison on a corpus of engineering artifacts with several relevant items per query.

## Grading and labels
- Directness: medium. Control: medium. Independence: low. Reproducibility: medium. Applicability: medium.
- Strength: builder-report (blog), backed by a repo-pinned results file. Pillar R4 (rerank design); secondary R3 (read path), R6 (refusal scoring, missing intervals).
- Beliefs: contradicts B10 in scope (listwise Choice loses to per-item Noul when many documents are relevant: NFCorpus 0.316 vs 0.358, FiQA 0.358 vs 0.376); supports B11 (the optional threshold drops only confident negatives; no "none" option); supports B14 (calibration measured locally: 76% at p >= 0.9).
- Contradiction row: B10, "a single choice call beat per-item yes/no (0.94 vs 0.87 recall@1) on LoCoMo-200" vs hev/reranker "much worse when many are relevant (NFCorpus 0.316 vs 0.358)"; open; B10 is already qualified to LoCoMo-200, so the row narrows its generalisation rather than overturning it.

## Origin chain
@hevmind posts (2104010850675945547 links the blog; 2104025279027159186 and 2104010209886929167 link the repo) -> hevmind.com/writing/jev-as-a-reranker -> github.com/hev/reranker RESULTS.md and README.md at 1eb47266270b32b2a3667f9fb89646378ca9c9d6 -> this note. Answers WR-20260927-03. Independence: same author as N-20260927-08; the B10 evidence (Hindsight) is a different vendor on a different benchmark.
