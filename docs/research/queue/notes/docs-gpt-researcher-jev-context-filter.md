---
schema_version: 1
artifact_id: N-20260929-02
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104665229712035929", "file_id": null, "sha256": null}, {"artifact_id": "post:2104610254000635952", "file_id": null, "sha256": null}, {"artifact_id": "post:2104683753834709464", "file_id": null, "sha256": null}, {"artifact_id": "post:2104622195192234435", "file_id": null, "sha256": null}, {"artifact_id": "post:2104620304400265551", "file_id": null, "sha256": null}, {"artifact_id": "post:2104605702396285014", "file_id": null, "sha256": null}, {"artifact_id": "post:2104616779763060846", "file_id": null, "sha256": null}, {"artifact_id": "post:2104633039162630410", "file_id": null, "sha256": null}, {"artifact_id": "post:2104615607534490078", "file_id": null, "sha256": null}, {"artifact_id": "post:2104633707005165896", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:docs.gptr.dev/docs/gpt-researcher/gptr/context-filter
claim_cluster: url:docs.gptr.dev/docs/gpt-researcher/gptr/context-filter
feeds: ["memory", "decision"]
primary_source: https://docs.gptr.dev/docs/gpt-researcher/gptr/context-filter
source_commit: 0957c301ed06c2a5857b834358c7227c739041d4
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R3", "R6"]
memory_stage: reranking
priority: 1
tags: {"mechanism": ["pointwise-score-question", "absolute-threshold-admission", "post-retrieval-passage-filter", "bm25-relative-threshold-fallback", "fallback-chain"], "workload": ["web-research-reports", "simpleqa"], "lifecycle_stage": ["read"], "cross_cutting": ["llm-as-judge", "controlled-replay", "cost-accounting", "claim-correction"]}
evidence_grade: {"directness": "high: controlled replay of the same recorded pages isolates the filter step, the exact thing claimed", "control": "medium: search, scrape and writer held constant, but one run, n=28, baseline is text-embedding-3-small cosine at 0.42, no cross-encoder or listwise reranker arm, no gold-evidence recall metric", "independence": "medium: integrator (GPT Researcher) not the vendor (TypeSafe); any commercial relationship not stated; judges are OpenAI models that share no model with Jev but share a family with the writer", "reproducibility": "medium: scripts and per-run scores committed at a pinned commit; pages and reports not committed; needs OpenAI, Tavily and TypeSafe keys; model is jev-latest (unpinned)", "applicability": "medium-low: 1,000-char chunks of scraped web pages scored against research sub-queries; not code, reviews, incidents or long structured artifacts"}
beliefs_affected: {"supports": ["B11", "B14"], "contradicts": [], "would_create": ["On web research passages, an absolute threshold on a pointwise 4-level usefulness score (Jev, >= 1.5 of 3) beats cosine-similarity filtering on judged context precision (0.73 vs 0.46) and pairwise report preference (15-10-3) at equal total cost; most of the gain comes from the threshold, not the ranking"]}
claim_correction: Narrower. Jev replaced the embedding-similarity passage filter applied after Tavily search and scraping, not retrieval; "59% more relevant" is a precision ratio (share of kept passages judged relevant), relevant text volume was about the same; filter cost is about 2x embeddings though total report cost is equal; embeddings remain in use for user vector stores and section-overlap checks.
---

# GPT Researcher replaces its embedding passage filter with Jev (TypeSafe): controlled replay on 28 research tasks

- **URL:** https://docs.gptr.dev/docs/gpt-researcher/gptr/context-filter (same text in repo at `docs/docs/gpt-researcher/gptr/context-filter.md`); benchmark at https://github.com/assafelovic/gpt-researcher/tree/main/evals/context_filter
- **Type:** docs + repo (integrator's own benchmark)
- **Author / org:** GPT Researcher (assafelovic/gpt-researcher, Assaf Elovic); Jev is by TypeSafe
- **Date:** repo commit `0957c301ed06c2a5857b834358c7227c739041d4` committed 2026-09-26 19:56:07 +0300 ("Merge pull request #2173 from assafelovic/docs/homepage-restore-hero"); benchmark run date not stated
- **Retrieved:** 2026-09-29. Shallow clone at `repos/gpt-researcher` (commit above). Read: `docs/docs/gpt-researcher/gptr/context-filter.md`, `gpt_researcher/context/jev_filter.py`, `gpt_researcher/context/select.py`, `gpt_researcher/context/compression.py` (grep), `gpt_researcher/config/variables/default.py` (grep), `evals/context_filter/README.md`, `evals/context_filter/judge.py`, `evals/context_filter/replay.py` (lines 1-120), `evals/context_filter/results/summary_vs_embeddings.json`, README.md (grep). Live docs page fetched and matches the repo copy (same table, 73% vs 46%, 15 · 10 · 3).
- **Cited by evidence:** @assaf_elovic post 2104562754774303203 (quoted: "We replaced embeddings with Jev in GPT Researcher's RAG pipeline ... 59% more relevant context (73% vs 46%) ... Reports preferred 15 to 3 ... Same cost per report ... no longer needs embeddings at all"); posts https://x.com/i/status/2104665229712035929, /2104610254000635952, /2104683753834709464, /2104622195192234435; critics https://x.com/i/status/2104620304400265551, /2104605702396285014, /2104616779763060846, /2104633039162630410, /2104615607534490078, /2104633707005165896 (among them @scott_stouffer, @nlpnyc, @spyced; per-id handle mapping not given to me)
- **Relevance to a memory stack:** high. A shipped, default-on System One filter at the post-retrieval reranking/admission stage with a controlled replay, committed per-run scores, every threshold in config and a no-API fallback; the most concrete public evidence so far that a thresholded Jev score beats embedding similarity at this stage (on web text).

## TL;DR
- **Claim correction (narrower).** Jev did not replace retrieval. The pipeline is `search -> scrape pages -> CONTEXT FILTER -> passages` (docs "Where the filter sits"); Tavily search and scraping still produce the candidates, and Jev chooses which 1,000-char chunks the writer reads. The critics (@scott_stouffer, @spyced) are right: this is a post-retrieval filter/reranker, and what it replaced was cosine-similarity filtering with `text-embedding-3-small` at threshold 0.42, not a cross-encoder reranker (@nlpnyc is right that no Cohere-style reranker arm exists).
- One Jev `score` question per chunk, 4 levels, keep chunks with probability-weighted score >= `JEV_MIN_SCORE` 1.5 (of 3), up to 10 per sub-query. Every chunk is its own call, 64 concurrent.
- On 28 replayed tasks: judged context precision 73% vs 46% (embeddings), pairwise report preference 15 win / 10 tie / 3 loss (both orders must agree), SimpleQA 19/20 vs 18/20, total $0.115 vs $0.117 per report.
- "The threshold matters more than the ranking": Jev forced to fill 10 slots with no threshold drops to 50% precision (still 13 · 10 · 5 vs embeddings). BM25 with a relative threshold (the no-key fallback) gets 51% and 14 · 8 · 6.
- "59% more relevant" is a ratio of precisions. Jev sends less context (4.5k vs 7.6k tokens) with about the same relevant text ("≈ 3.3k vs 3.5k tokens"), so the gain is less noise, not more relevant content. Gold-evidence recall was never measured.

## What it claims / describes

**Pipeline position** (docs "Where the filter sits"). For each planned sub-query: search, scrape pages, then `select_context()` (`gpt_researcher/context/select.py`). "Each page is capped at 50,000 characters and split into 1,000-character chunks with 100 characters of overlap. The filter then chooses which chunks become context. Up to 10 are kept per sub-query for Jev and embeddings, and up to 25 for keyword." Sub-query contexts are joined and passed to the writer. Report chat uses the same function (the report treated as one page, the latest message as the query).

**Candidates.** All non-empty chunks of all scraped pages for the sub-query (`jev_filter.py` `_chunks()`, lines 152-155: `RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_size // 10)`). The docs' method section reports "a median of 4 filter calls, 10.5 pages and 168k characters per task". Candidates per sub-query are not stated; about 168k / 4 = 42k characters, roughly 45 chunks per sub-query (inference). The embeddings arm uses the same splitter (`compression.py` line 134, `chunk_size=1000, chunk_overlap=100`), so both arms see the same candidate pool.

**Modes** (`CONTEXT_FILTER`, docs "Modes"; `select.py` lines 6-10, 38-46): `auto` (default: `jev` when `TYPESAFE_API_KEY` is set, else `keyword`), `jev`, `keyword` (BM25), `embeddings` (cosine, needs an `EMBEDDING` provider; default `openai:text-embedding-3-small`, `SIMILARITY_THRESHOLD` 0.42 in `config/variables/default.py` lines 5-6), `none`.

**Fallback chain** (docs; `select.py` lines 79-101): `jev` falls back to `keyword` on `JevError` (missing key, network error, rate limiting after retries, malformed response); `embeddings` falls back to `keyword` if the model cannot be built. Small page sets (under 8,000 characters total and no more pages than the budget) pass through unfiltered in every mode.

**Jev call** (docs "How Jev is used"; `jev_filter.py` lines 36-41, 84-119): `POST https://api.typesafe.ai/v1/systemone`, one chunk per request, `state` = chunk text, `model` = `JEV_MODEL` default `jev-latest`, one `score` question named `usefulness` with instructions `f"How useful is this passage for answering the question: {query}"` (query = the sub-query) and criteria:
1. "Unrelated to the question"
2. "Same topic, but does not help answer the question"
3. "Partially answers the question or gives useful supporting facts"
4. "Directly answers the question with specific facts"

The response field used is `body["answers"]["usefulness"]["score"]`, "the probability-weighted level, from 0 to 3" (docs). Confidence and per-level probabilities are not used.

**Selection** (`jev_filter.py` lines 157-184): rank by score descending, ties by page order; `selected = [c.document for c in ranked if c.score >= self.min_score][:max_results]`. If nothing clears 1.5 the sub-query contributes no chunks (the code has no minimum-one rule; inference from lines 183-184). Docs: "A calibrated usefulness score can say 'nothing else on this page is worth including'; a similarity score can't."

**Benchmark method** (docs "The benchmark"; `evals/context_filter/README.md`):
1. Record: `collect.py` ran 28 tasks (20 SimpleQA questions, fixed seed, plus 8 open-ended research questions, listed in the docs) and recorded the exact pages reaching the filter per sub-query.
2. Replay: `replay.py` rebuilt each task's context from the same pages with each strategy; writer `gpt-5.4`, `report_type="research_report"`.
3. Judge (`judge.py`): precision = share of passages given to the writer that `gpt-5.4-mini` rates relevant, in one listwise prompt per report (passages truncated to 1,500 chars, "RELEVANT if it contains information that would help write an accurate answer to the research question; passages that are only on the same general topic ... are NOT relevant", lines 52-69), judged against the top-level research question, not the sub-query. Pairwise = `gpt-5.4`, both orders, win/loss only if both agree, criteria "factual accuracy and specificity first, then relevance (no padding or off-topic material), then completeness. Length alone is not a merit." SimpleQA graded with the repo's grader (`gpt-5.4`).

**Who judged what.** Relevance: `gpt-5.4-mini`. Preference and SimpleQA grading: `gpt-5.4`, the same model as the writer. Neither judge shares a model with Jev (TypeSafe). The docs admit "Reports were written and head-to-head judged by the same model family (`gpt-5.4`)".

## Numbers

| metric | value | baseline | setup/benchmark (n) | caveat |
|---|---|---|---|---|
| relevant passages (precision), Jev default | 73% (0.728 in `summary_vs_embeddings.json`) | embeddings 46% (0.457) | 28 tasks, judge gpt-5.4-mini | precision rewards keeping fewer chunks; recall not measured |
| head-to-head vs embeddings, Jev | 15 · 10 · 3 (win · tie · loss) | embeddings | 28 tasks, gpt-5.4 both orders | "sign test on the 18 non-ties, p ≈ 0.008" (docs); judge = writer model |
| SimpleQA correct | Jev 19/20, keyword 19/20, embeddings 18/20, unranked 19/20, no filter 20/20 | | 20 SimpleQA | docs: "SimpleQA is saturated ... differences of a question or two are noise" |
| filter time median | Jev 1.7s (p90 3.6s) at concurrency 64; 2.4s / 6.0s at 32 (README footnote) | embeddings 1.0s (p90 1.3s) | 28 tasks | "Jev adds about 0.7s at the median over embeddings, on a run of roughly two minutes" |
| context sent median | Jev 4.5k tokens | embeddings 7.6k, keyword 6.4k, unranked 8.0k, none 33.4k (max 107.7k) | 28 tasks | relevant text "≈ 3.3k vs 3.5k tokens" Jev vs embeddings |
| cost per report | Jev $0.115 | embeddings $0.117, keyword $0.116, none $0.192 | 28 tasks | filter-only cost Jev $0.0054 vs embeddings $0.0028 (README cost table; `mean_filter_cost` 0.00542 vs 0.00282) |
| Jev no threshold, top 10 | 50%, 13 · 10 · 5 | embeddings | 28 tasks | "the threshold is the source of the gain" |
| 3,000-char chunks, top 4 | 72%, 11 · 10 · 7 | embeddings | 28 tasks | "a third of the API calls; 1.2s median" |
| threshold 1.5, up to 30 | 74%, 13 · 8 · 7; SimpleQA 20/20 | embeddings | 28 tasks | "few extra chunks clear the threshold" |
| 3,000-char, threshold 1.0, up to 12 (`jev_broad`) | 76%, 7 · 1 · 0 | embeddings | 8 open-ended only | $0.191 per report |
| keyword BM25 top 10 / >=50% of best top 10 / >=50% up to 25 (shipped) | 40% 7·9·12 / 53% 7·13·8 / 51% 14·8·6 | embeddings | 28 tasks | 14-6 "directional (p ≈ 0.12)" |
| unranked control (round robin, 10 chunks) | 33%, 7 · 8 · 13 | embeddings | 28 tasks | shows ranking matters |
| Jev vs no filter | 6 / 12 / 10 (W/T/L) | none | 28 tasks | on open-ended, none beats Jev 6-0 with 2 ties (README "vs none" column, open-ended table) |
| no filter vs embeddings, open-ended | 8 · 0 · 0 | embeddings | 8 open-ended | 65% more cost overall, 83% on open-ended |
| Jev single call latency | about 0.33s warm; 0.45s at 13k tokens; 64 concurrent in about 1.1s | | docs "Throughput" | "Raising it to 128 made filtering no faster" |
| benchmark spend | about $41 tracked (Jev $0.59) + est. $8-15 judging | | all configurations | |

## Mechanism details you could implement
- Config surface (docs "Configuration reference"): `JEV_MIN_SCORE=1.5`, `JEV_CONCURRENCY=64`, `JEV_CHUNK_SIZE=1000`, `JEV_MODEL=jev-latest`, `KEYWORD_RELATIVE_THRESHOLD=0.5`, `KEYWORD_MAX_RESULTS=25`, `SIMILARITY_THRESHOLD=0.42`, `COMPRESSION_THRESHOLD=8000`.
- Question design: one `score` question with 4 concrete levels that separate "same topic" from "helps answer". Level 2 ("Same topic, but does not help answer") is the level that embeddings cannot distinguish (inference from the docs' framing). Use the probability-weighted score (0 to 3) and an absolute admission threshold between level 2 and 3 (1.5).
- Retry policy: 429 and 529 retried up to 3 times with backoff `0.5 * 2 ** attempt` seconds; any other status raises immediately (`jev_filter.py` lines 113-118). Per-call timeout 30 s.
- One semaphore per event loop shared across concurrent sub-queries (lines 43-53), so parallel sub-queries do not each open a full-width pool.
- Cost accounting from `usage.input_tokens` x $0.042/M, surfaced in `get_costs()`.
- Fallback that needs nothing: BM25 (k1 1.5, b 0.75, IDF over the sub-query's own chunks), keep chunks >= 0.5 x best score, up to 25; if no query term matches, use the pages' opening chunks (docs "How the keyword fallback works").
- Evaluation design worth copying: record candidates once, replay every filter on identical inputs, include an unranked control and a no-filter arm, pairwise judged in both orders with ties on disagreement.

## Limitations, caveats, counter-evidence
- Source-stated: 28 tasks, one writer model, one report type; detailed and deep research not replayed; writer and pairwise judge are the same model family; "pairwise results are directional evidence, not a leaderboard".
- The baseline is a weak one for a reranker comparison: cosine similarity with `text-embedding-3-small` at 0.42 (inference: an embedding bi-encoder is a first-stage retriever signal, not a reranker). No cross-encoder, Cohere rerank, LLM listwise rerank or Jev `choice` listwise arm was run, so the result does not show Jev beats a proper reranker (the critics' point stands).
- No gold-evidence recall metric. Precision is a ratio over kept chunks, so a filter that keeps fewer chunks is favoured. Relevant text was slightly lower for Jev (3.3k vs 3.5k tokens). This is the same failure mode our synthesis warns about (pruning drops gold evidence), not measured here.
- Precision is judged against the top-level question while the filter scored against sub-queries (judge.py uses `r['query']`); chunks useful for a sub-query angle may be judged irrelevant (inference).
- The docs call Jev's output "calibrated probabilities"; no calibration measurement is shown (relevant to B14).
- `jev-latest` is not pinned; single run, no seeds or variance reported for the filter arms.
- "No longer needs embeddings at all" (post) is broader than the docs: "Embeddings are still used for vector stores you pass in yourself (`vector_store=`). When an embedding model is available, they are also used to spot overlap between sections of detailed reports."
- "Beat embeddings on every quality measure": true on the three measures, but the SimpleQA difference is one question, which the source itself calls noise.
- "Same cost per report": true for total ($0.115 vs $0.117) because Jev sends less context to the writer; the filter step alone costs about 2x ($0.0054 vs $0.0028).
- Skipping the filter beat Jev on open-ended questions (Jev vs none 0 / 2 / 6 on the 8 open-ended), at 65-83% higher cost.

## Takeaways for tuning a memory stack
- At the post-retrieval admission step, an absolute threshold on a typed usefulness score is what does the work; top-k by any score (Jev no threshold 50%, BM25 top 10 40%) is close to or below embeddings. Test "threshold admission" separately from "ranking".
- Separate the ranker from the admission gate (consistent with B11): here the admission gate is allowed to return nothing per sub-query, which works for a research report with many sub-queries but is risky for a single build-time read where one missing constraint matters (inference).
- Before adopting, add the two arms this benchmark lacks: a cross-encoder reranker and a gold-evidence recall metric on our own artifacts.
- A cheap BM25 relative-threshold fallback (>= 0.5 of best, up to 25) matched or beat embeddings here; keep a no-API fallback behind any hosted System One filter.
- Pointwise scoring costs one call per chunk; at 1,000-char chunks and ~45 chunks per sub-query (inference) this is fine at $0.042/M, but latency tails (p90 3.6s) come from large pages. 3,000-char chunks cut calls by two thirds at 72% precision.

## Open questions
- Gold-evidence recall of Jev at 1.5 vs embeddings vs a cross-encoder at matched tokens: not measured.
- Candidates per sub-query and the distribution of kept chunks (how often zero are kept): not stated.
- Would a single listwise Jev `choice` call (B10) match pointwise scoring at fewer calls: not tested.
- Does 1.5 transfer to code, diffs, tickets and long structured specs, where chunk boundaries split meaning: unknown.
- Commercial relationship between GPT Researcher / Tavily and TypeSafe: not stated.

## Grading and labels
- Directness: high. The replay isolates exactly the filter step claimed.
- Control: medium. Same pages, same writer, unranked and no-filter controls; but one run, n=28, weak baseline, no recall metric, LLM judges.
- Independence: medium. Integrator, not vendor; relationship to TypeSafe not stated; judges are OpenAI models (no shared model with Jev), pairwise judge = writer model.
- Reproducibility: medium. Pinned commit, scripts and per-run scores committed; pages and reports not committed; `jev-latest` unpinned; requires paid keys.
- Applicability: medium-low. Web-page chunks and research reports, not engineering artifacts or build-time reads.
- Strength: repo-pinned.
- Pillars: R9 primary; R3, R6 secondary.
- Memory stage: reranking (post-retrieval filter and admission).
- Tags: mechanism pointwise-score-question, absolute-threshold-admission, post-retrieval-passage-filter, bm25-relative-threshold-fallback, fallback-chain; workload web-research-reports, simpleqa; lifecycle read; cross-cutting llm-as-judge, controlled-replay, cost-accounting, claim-correction.
- Beliefs supports: B11 (admission allowed to be empty is separate from ranking, and the threshold carries the gain); B14 (docs claim "calibrated probabilities" without showing calibration).
- Beliefs contradicts: none.
- Beliefs would_create: thresholded pointwise usefulness beats cosine filtering on web research passages (0.73 vs 0.46 precision, 15-10-3), threshold not ranking carries most of the gain.
- Contradiction: synthesis section 2 says "keep ranking on and pruning off by default"; here pruning by an absolute threshold is on by default and is the source of the gain in judged precision and pairwise preference. Scope differs (web research reports, many sub-queries, no gold-recall metric), so this is tension to test on our workload, not a refutation.
- Not contradicting B10: no listwise choice arm was run; pointwise score vs embeddings says nothing about choice vs yes/no.

## Origin chain
- @assaf_elovic post 2104562754774303203 (quoted by the cluster's posts) -> docs.gptr.dev context-filter page -> "Results" table and "Other Jev configurations tested" table; repo `evals/context_filter/README.md` "Quality" and "Cost and speed" tables; `evals/context_filter/results/summary_vs_embeddings.json`.
- Critic posts (@scott_stouffer, @nlpnyc, @spyced and others among ids 2104620304400265551 to 2104633707005165896) -> checked against docs "Where the filter sits", `select.py`, `replay.py` baseline definition: confirmed.
- Independence: author of the system, the benchmark and the post are the same team (GPT Researcher); the search provider (Tavily) is associated with the same author (inference, not stated in the source); judges are OpenAI models; no external replication. Shares no dataset with other Jev notes except SimpleQA as a public set.
