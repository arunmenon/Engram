# Hindsight (vectorize-io/hindsight): agent memory service with retain / recall / reflect, observations, mental models, and a TypeSafe Jev reranker

- **URL:** https://github.com/vectorize-io/hindsight (Docker image `ghcr.io/vectorize-io/hindsight:latest`; docs https://hindsight.vectorize.io; paper https://arxiv.org/abs/2512.12818)
- **Type:** repo
- **Author / org:** Vectorize.io (MIT license)
- **Date:** commit `2fbc25e095991c04291ed5650a0af37a998cf0cf` (2026-09-25 19:24 +0200); release v0.10.1 (blog dated 2026-09-21); Jev reranker writeup dated 2026-09-24
- **Retrieved:** 2026-09-26 (local copy: /private/tmp/claude-501/-Users-arunmenon-projects-localai-signals/3f9824a6-23ac-471e-adc7-a1ca0ec806fd/scratchpad/repos/hindsight, shallow clone)
- **Cited by evidence:** "Memory that updates on read" / 2026-09-25 cai_smart ("recall isn't the same as learning"; retain / recall / reflect; 27k stars, 2.5k forks, v0.10.1, as stated in the post, not verified here); "Decision models as the memory control plane" / 2026-09-24 Vectorizeio ("Hindsight now includes @typesafeai Jev reranking capabilities")
- **Relevance to a memory stack:** high. Production-grade reference for multi-arm retrieval (semantic + BM25 + graph + temporal, RRF, cross-encoder, multiplicative boosts), LLM-driven consolidation into evidence-backed "observations", and the most detailed public writeup of using Jev as a listwise reranker plus relevance cut, with failed designs and numbers.

## TL;DR
- **Hindsight does NOT update memories on read.** Recall is read-only: no access counter, no reinforcement, no read-time decay write. A migration (`e4a7c1b9d2f6`, 2026-08-03) dropped the `memory_units.access_count` column because "no code path anywhere in the repo ever writes it" and "no query ever reads or orders by it". Its "learning" happens on the write side: background consolidation of new facts into observations (with `proof_count`), and background rewriting of mental models. This matters for the "updates on read" trend: Hindsight is a counter-example, or at most a "learns on write, not on recall" system.
- Recall = 4 parallel arms per fact type (semantic pgvector HNSW, BM25 tsvector, graph link-expansion, temporal), fused by RRF (k=60), capped at 300 candidates, reranked by a cross-encoder (default local `cross-encoder/ms-marco-MiniLM-L-6-v2`), then multiplied by recency, temporal-proximity and proof-count boosts (max about +21% / -19%), then trimmed to a token budget (default 4096).
- Jev (`typesafe` reranker provider, v0.10.1, opt-in) asks ONE `choice` question with every candidate as an option ("Which candidate answers the question: ..."), and optionally a second `score` question with 6 ordered depth levels to cut the tail. LoCoMo: recall@1 0.800 to 0.950 at 30 candidates, 0.583 to 0.783 at 240 candidates, and about 4x to 6x faster per query than the local MiniLM.
- Two failed Jev designs are documented with numbers: a "none of these" Choice option (35/200 queries returned empty) and a "nothing is relevant" Score level (7% empty, gold retention 0.81 to 0.65). Pruning, when on, costs 19% of gold evidence and caps recall at 12 results.
- Vendor-reported benchmarks: LongMemEval 91.4% (paper, v0.1.0) and 94.6% (v0.4.19, AMB harness), LoCoMo 92.0%, BEAM 10M 64.1%. README says the scores were independently reproduced by Virginia Tech's Sanghani Center and The Washington Post, and that other vendors' scores are self-reported.

## What it claims / describes
**Positioning (README).** "Most agent memory systems focus on recalling conversation history. Hindsight is focused on making agents that learn, not just remember." A Python server exposing HTTP (port 8888), a UI (port 9999), an MCP endpoint per bank (`http://localhost:8888/mcp/{bank_id}/`), and clients for Python, Node, Go and a CLI. Deployment paths: Docker (embedded Postgres "pg0"), docker-compose with external PostgreSQL, `pip install hindsight-api`, a Helm chart, embedded in-process (`pip install hindsight-all`), and a hosted Cloud offering. It supports 25+ LLM providers through `HINDSIGHT_API_LLM_PROVIDER`, including ollama, lmstudio, llamacpp, and `openai-codex` / Claude Code subscriptions.

**Memory types.** World facts, experiences (the agent's first-person history), observations (consolidated, evidence-backed beliefs), and mental models (standing answers to user-defined questions, rewritten in the background). Knowledge pages are "mental models with the mechanics hidden", organized in folders like a wiki and projectable to disk as markdown. Banks are isolated stores ("no cross-bank leakage") with disposition traits (skepticism, literalism, empathy, each 1 to 5) that shape reflect. An opt-in "Memory Defense" policy scans each retain for secrets and PII against 45 patterns and either redacts or blocks.

**Data model (code).** Table `memory_units` (`hindsight-api-slim/hindsight_api/models.py`, plus alembic migrations): `id`, `bank_id`, `document_id`, `text`, `embedding` (pgvector, HNSW `vector_cosine_ops`), `context`, `event_date`, `occurred_start`, `occurred_end`, `mentioned_at`, `fact_type` (CHECK in `'world','experience','observation'`), `metadata` JSONB, `created_at`, `updated_at`. Migrations add `search_vector` tsvector, `tags VARCHAR[]`, `proof_count INT DEFAULT 1`, `source_memory_ids UUID[]`, `history JSONB`, `observation_scopes JSONB`, `confidence_score`, `consolidated_at`, `consolidation_failed_at`, `invalidation_reason`, `invalidated_at`, `entity_ids UUID[]` and `chunk_id`. Observations live in `memory_units` with `fact_type='observation'`. Other tables: `documents`, `entities`, `unit_entities`, `entity_cooccurrences`, `memory_links` (`link_type IN ('temporal','semantic','entity','causes','caused_by','enables','prevents')`, `weight` in [0,1]), `banks`, `directives` (hard rules), and an `invalidated_memory_units` archive.

**Write path: retain.** An LLM extracts facts. The code schema (`engine/retain/fact_extraction.py`, `ExtractedFact`) has fields `what`, `when`, `where`, `who`, `why`, `fact_kind` ('event' or 'conversation'), `occurred_start`, `occurred_end`, `fact_type`, `entities` and `causal_relations`. Entities are resolved (trigram lookup by default) and links are built: entity links, temporal links ("stronger links for closer dates"), semantic kNN links at insert time (min similarity 0.7), and causal links. Defaults: chunk size 3000 chars, extraction mode `concise` (alternatives `verbose` and `custom`), causal-link extraction on, and an optional `retain_mission` to steer what gets extracted.

**Consolidation: observations (background, after retain).** Default on (`HINDSIGHT_API_ENABLE_AUTO_CONSOLIDATION`). For each batch of new facts (8 facts per LLM call by default), the consolidator recalls related existing observations (recall budget `low`, max 512 tokens) and asks an LLM to return `{"creates": [...], "updates": [...], "deletes": [...]}`, each entry with a required `reason`. Rules in `engine/consolidation/prompts.py` include "PREFER UPDATE OVER CREATE", "ONE OBSERVATION PER DISTINCT FACET", "PRESERVE HISTORY ... never DELETE", and "NO COMPUTATION ... never do arithmetic". On UPDATE, `proof_count` becomes the count of distinct source memory ids, the temporal span widens, and `updated_at = now()`. Near-duplicate observations are reconciled when cosine similarity is at least `CONSOLIDATION_DEDUP_THRESHOLD` (default 0.97): a focused LLM check decides merge or keep (Postgres only). Deleting source memories deletes derived observations and resets `consolidated_at` on the remaining sources so they re-consolidate.

**Read path: recall** (`engine/memory_engine.py::recall_async`, `engine/search/*`). The docstring describes "N*4-way parallel retrieval (N fact types x 4 retrieval methods)":
1. Semantic: pgvector ANN, `LIMIT recall_budget`, min similarity 0.3.
2. BM25: Postgres full-text, `LIMIT recall_budget`.
3. Graph: `link_expansion` retriever. Up to 20 semantic seeds (min similarity 0.3) are expanded through entity links (score `tanh(shared_entity_count * 0.5)`, per-entity cap 200, 10 s timeout), semantic kNN links (weight in [0.7, 1.0]) and causal links. The docs give `graph_score = entity + semantic + causal`, in [0, 3]. The code docstring says the causal score is "weight + 1.0 (boosted as highest-quality signal)", which does not match the docs table (docs versus code discrepancy, not resolved here).
4. Temporal: dates are extracted from the query or taken from `temporal_window`. 60 ANN candidates per fact type, 10 entry points, 8 coverage buckets, then spreading activation over links (min semantic similarity 0.1).
5. RRF fusion `score(d) = sum 1/(k + rank)`, k=60. Optional per-arm boosts are applied in rank space (`1/(k + rank/divisor)`, with divisor low=2, medium=4, high=8).
6. Trim to `RERANKER_MAX_CANDIDATES` (300). Full text is hydrated only now, then the cross-encoder reranks.
7. Combined scoring (below), then token truncation to `max_tokens`.
Budget levels map to a recall budget of 100 (low), 300 (mid, default) or 1000 (high). An adaptive mode sets it to `clamp(max_tokens x {2.5%, 7.5%, 25%}, 20, 2000)`. The docstring lists "Diversity: MMR with lambda=0.5", but no MMR implementation turned up when searching `engine/` (inference: the docstring is stale).

**Reflect.** An agentic loop (up to 10 iterations) with tools `search_mental_models`, `read_mental_models`, `search_observations`, `recall`, `expand` and `done`. Retrieval is hierarchical: mental models first, then observations, then raw facts. Freshness: an observation search reports `up_to_date` when there are 0 pending unconsolidated memories, `slightly_stale` when fewer than 10, and `stale` otherwise. A mental model is stale if new in-scope memories arrived since its last refresh. A stale layer is still shown but does not short-circuit, and the agent is expected to verify against raw facts. Citations are validated (only retrieved IDs can be cited).

**Mental models.** A user defines a question. Hindsight writes the answer and rebuilds it when in-scope memories change (on consolidation or on a schedule), optionally with incremental "delta" edits so the document does not drift. Reading one is a plain DB read with no LLM call. A separate LLM can be configured for refreshes (new in 0.10.1).

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Jev rerank recall@1 | 0.950 | 0.800 (local MiniLM) | LoCoMo, 30 candidates/query, gold = dataset evidence turns | vendor-run; number of questions not stated for this table |
| Jev rerank recall@5 | 0.966 | 0.876 | same | same |
| Jev rerank NDCG@10 | 0.957 | 0.850 | same | same |
| Jev rerank latency | 0.027 s/query | 0.12 s/query | same | Jev is a hosted API; hardware for local not stated |
| Jev rerank recall@1 / @5 / NDCG@10 | 0.783 / 0.903 / 0.856 | 0.583 / 0.719 / 0.682 | LoCoMo, 240 candidates/query, 60 questions | small n |
| Jev latency at 240 candidates | 0.063 s/query | 0.41 s/query | same | |
| Listwise vs per-candidate (Noul-style) | recall@1 0.94 | 0.87 | 200-question LoCoMo set, same model | "at a thirtieth of the calls" |
| "None of these" Choice option | 35/200 queries empty | 0 with Score cut | same 200-question set | failed design |
| "Nothing is relevant" Score level | 7% of queries empty; gold retention 0.81 to 0.65 | no such level | not stated | failed design |
| Pruning on (Score cut) | keeps 1.6 of 30; precision 0.051 to 0.850 (17x) | ranking only | 30-candidate run | cuts 19% of gold evidence; max 12 results; "300 down to 3" on a real bank |
| LongMemEval | 91.4% | Mem0 49.0%, SuperMemory 81.6% (as published by those vendors) | paper, v0.1.0 | README: reproduced by Virginia Tech Sanghani Center and The Washington Post |
| LongMemEval-s | 94.6% | SuperMemory 81.6, Zep 71.2, Mem0 67.6; Chronos 95.6, Mastra 92.8, Honcho 90.4 | v0.4.19, AMB harness, single-query mode | Vectorize runs AMB; the blog admits several systems sit at or above Hindsight |
| LoCoMo | 92.0% | not stated | v0.4.19, AMB | vendor |
| LifeBench / PersonaMem | 71.5% / 86.6% | not stated | v0.4.19, AMB | vendor |
| BEAM 10M | 64.1% | next best 40.6%; BEAM-paper RAG 24.9%, LIGHT 26.6% | blog 2026-04-02 | vendor |
| Recall boost range | max about +21%, min about -19% | CE score alone | `apply_combined_scoring` | by construction |
| Strategy boost `high` in score space (old bug) | recall@20 0.97 to 0.40 | | issue #3956 | motivated the rank-space boost |

## Mechanism details you could implement
**Combined scoring after the reranker** (`engine/search/reranking.py`):
```
recency_boost     = 1 + 0.2 * (recency - 0.5)
temporal_boost    = 1 + 0.2 * (temporal - 0.5)
proof_count_boost = 1 + 0.1 * (proof_norm - 0.5)
combined_score    = CE_normalized * recency_boost * temporal_boost * proof_count_boost
```
- `proof_norm = min(1, max(0, 0.5 + ln(proof_count)/10))`. It is 0.5 for non-observations, so the boost is neutral for them.
- The recency decay is computed at read time from timestamps and is never written back. Options: `linear` (default) `max(0.1, min(1, 1 - days_ago/365))`; `exponential` `0.5 ** (days_ago / 90)`, where the half-life age is neutral; or `none`. A coarse date ("in 2015") is aged from the end of its period and capped at neutral 0.5. The age used is `occurred_start`, falling back to `mentioned_at`, then `occurred_end`. Env: `HINDSIGHT_API_RECENCY_DECAY_FUNCTION`, `..._LINEAR_WINDOW_DAYS`, `..._HALFLIFE_DAYS` (per-bank overridable via `ScoringConfig` in `engine/memories/base.py`).
- For the passthrough `rrf` reranker, CE scores are seeded from RRF rank as `1 - 0.9*rank/(n-1)`, so the boosts do not turn the order into a pure recency sort.

**Jev request, rank question** (`engine/cross_encoder.py::TypeSafeCrossEncoder._rank_once`). The call is `POST {base_url}/v1/systemone` with a bearer API key:
```python
body = {
    "state": f"Question: {query}",
    "model": self.model,                      # "jev-latest"
    "questions": {"rank": {
        "type": "choice",
        "instructions": f"Which candidate answers the question: {query}",
        "criteria": {f"c{position}": docs[index] for position, index in enumerate(indices)},
    }},
}
probabilities = result["answers"]["rank"]["probabilities"]   # dict c0..cN -> p, sums to 1
```
**Jev request, cut question** (only when pruning is on). The model sees the top `SHORTLIST = 12` candidates, and the state is `"Question: {q}\n\nCandidates, already ranked best first:\n[1] ...\n\n[2] ..."`:
```python
"questions": {"depth": {"type": "score",
  "instructions": "How far down this ranked list does genuine relevance to the question extend? "
                  "Count a candidate as relevant only if it helps answer the question.",
  "criteria": ["Only the first candidate is relevant", "The first two are relevant",
               "The first three are relevant", "The first five are relevant",
               "The first ten are relevant", "All of the listed candidates are relevant"]}}
level = round(float(result["answers"]["depth"]["score"]))   # CUT_DEPTHS = [1, 2, 3, 5, 10, None]
```
- Response shape used in the tests: `{"answers": {qid: {...}}, "usage": {"input_tokens": ..., "output_tokens": ...}}`.
- Output scores are positions, not confidences: `(n - position)/n` for kept candidates and exactly `0.0` past the cut.
- Limits: `MAX_OPTIONS = 250` (Jev's limit is 255 options); `MAX_QUESTION_TOKENS = 26_000` (safety margin under Jev's 32k); query capped at 2,000 tokens; a 1-option Choice is rejected by Jev ("criteria must map 2 or more options"). Pools that are too large are packed into groups and ranked in parallel. The top `min(12, 250 // n_groups)` of each group go to a finals Choice, and non-finalists keep RRF order (#4599).
- Config (`config.py`): `HINDSIGHT_API_RERANKER_PROVIDER=typesafe`, `HINDSIGHT_API_RERANKER_TYPESAFE_API_KEY` (required), `..._MODEL` (default `jev-latest`), `..._BASE_URL` (default `https://api.typesafe.ai`), `..._TIMEOUT` (60.0 s), `..._MAX_CONCURRENT` (24), `..._PRUNE_CANDIDATES` (false). Fallback chain: `HINDSIGHT_API_RERANKER_<n>_PROVIDER`, with every other setting indexed the same way. The blog recommends `rrf` last. The reranker is server-level only: a bank can turn reranking off but cannot choose its own provider.

**Consolidation update SQL** (`engine/consolidation/consolidator.py` around line 410):
```sql
UPDATE memory_units SET text = $1,
  source_memory_ids = (SELECT array_agg(DISTINCT e) FROM unnest(source_memory_ids || $2::uuid[]) e),
  proof_count = (SELECT count(DISTINCT e) FROM unnest(source_memory_ids || $2::uuid[]) e),
  occurred_start = LEAST(...), occurred_end = GREATEST(...), mentioned_at = GREATEST(...), updated_at = now()
WHERE id = $3::uuid AND text = $4      -- optimistic concurrency on prior text
```

**Other key defaults** (`config.py`): LLM `openai` / `gpt-4o-mini` (fallback); local embeddings `BAAI/bge-small-en-v1.5`; local reranker `cross-encoder/ms-marco-MiniLM-L-6-v2`; reranker max candidates 300; consolidation batch 50, LLM batch 8, max attempts 3, dedup 0.97; observation and mental-model history each capped at 50 entries; `MAX_OBSERVATIONS_PER_SCOPE = -1` (unlimited); reflect max iterations 10; recall max query tokens 500. Configuration is hierarchical: global env, then tenant, then bank.

**Storage.** PostgreSQL 15+ with pgvector 0.5+ (HNSW and GIN tsvector; graph via recursive CTEs), or Oracle AI Database 23ai. Docs also mention `pgvectorscale` and `vchord` vector extensions. Development uses embedded pg0 on port 5555 with data in `~/.hindsight/pg0/`. The docs say Hindsight deliberately has no generic storage abstraction.

**Unused code worth noting.** `engine/reflect/observations.py::compute_trend` classifies evidence as STRENGTHENING (recent/old density ratio above 1.5), WEAKENING (below 0.5), NEW, STALE (no evidence in the last 30 days) or STABLE, using 30 and 90 day windows. No caller outside that file was found (inference: legacy or unused).

## Limitations, caveats, counter-evidence
- **For the "updates on read" trend:** there is no read-time write at all. Reinforcement comes only from new evidence at consolidation (`proof_count`), and it has a tiny effect on ranking (at most +/-5%). The module docstring still advertises "Dynamic weighting: Recency and frequency-based importance", but the frequency column was never written and has now been dropped. The "recall isn't the same as learning" framing in the cai_smart post refers to consolidation and reflect, not to recall-time updating.
- The Jev integration sends candidate memory text to a third-party hosted API ("no benchmark makes that acceptable" if data must stay on-prem). It fails closed after retries unless a fallback chain is configured, and it does not truncate candidate text below its 26k budget.
- Jev probabilities are normalised per call, so absolute score floors (`min_scores`) filter on rank position, not relevance, with this provider.
- All benchmark numbers are vendor-run. The AMB leaderboard is run by Vectorize, and the Jev numbers come from small LoCoMo subsets (60 to 200 questions). Per the cai_smart post, the project is pre-1.0 and the storage format may change.
- Consolidation is LLM-heavy (one call per 8 facts, plus dedup checks), so the cost of "learning" is paid on write (inference).
- Docs versus code discrepancies: the MMR step is described but not found in code; the causal link score is "weight + 1.0" in code but documented as [0, 1].

## Takeaways for tuning a memory stack
- If you want read-time reinforcement, Hindsight is not a template: it deliberately keeps recall read-only and puts learning in consolidation. That avoids the feedback loop the trend's "watch" item worries about (frequently recalled wrong memories getting reinforced) (inference).
- For a decision-model reranker, copy the listwise design: one Choice over the whole pool, and use rank positions, not probabilities, as scores. Reported gains are recall@1 +0.15 to +0.20 over MiniLM, and it is faster.
- If you add a relevance cut, use an ordered Score with coarse depth levels (1/2/3/5/10/all) and no "nothing relevant" escape hatch. Expect about 19% gold loss, so enable it only when the consumer is an LLM prompt.
- Fetch payloads only after fusion and the candidate cap (ids and scores in the arms, hydration right before rerank). This makes adding a remote reranker cheap.
- Use multiplicative, bounded secondary boosts (recency ±10%, temporal ±10%, evidence ±5%) on top of a relevance score rather than additive weights. Boost arms in rank space, not score space, to avoid lexicographic takeover under a hard candidate cap.
- Age coarse dates from the end of their period, capped at neutral.
- Keep observations as UPDATE-preferring, facet-scoped, evidence-linked records, with `proof_count` equal to the number of distinct sources, and prevent LLM arithmetic in consolidation.

## Open questions
- Does Jev reranking improve end-to-end QA accuracy (not only retrieval recall@k) on LongMemEval knowledge-update or abstention subsets? Not stated.
- Is Jev used anywhere besides reranking (consolidation gating, recall gating, write filtering)? No other Jev call sites were found in `hindsight_api`. Reranking is the only integration at this commit.
- Was the dropped `access_count` ever intended for use-based strengthening? The migration only says an `access_count_update` task "was never implemented".
- How does the Jev cut interact with reflect's multi-call loop (12-result ceiling per recall)? Not measured in the repo.

---
