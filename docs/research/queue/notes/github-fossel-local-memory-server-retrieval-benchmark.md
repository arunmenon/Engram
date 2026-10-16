---
schema_version: 1
artifact_id: N-20261006-01
artifact_type: note
producer: triage
run_id: triage-20261006T014850Z-6519
created_at: 2026-10-06T02:07:06Z
input_refs: [{"artifact_id": "post:2104680885677404548", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:7vignesh/fossel
claim_cluster: github:7vignesh/fossel
feeds: ["memory"]
primary_source: https://github.com/7vignesh/fossel
source_commit: 3c70faff2add336c8563c48febaf21f9169db319
strength: repo-pinned
pillar_primary: R3
pillar_secondary: ["R6", "R2"]
memory_stage: retrieval
priority: 4
tags: {"mechanism": ["fts5-bm25", "stemmed-prefix-tier", "weighted-rrf", "hashed-embeddings", "git-blob-staleness"], "workload": ["coding-agent-memory", "mcp-server"], "lifecycle_stage": ["retrieval", "staleness"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high", "control": "medium", "independence": "low", "reproducibility": "high", "applicability": "medium"}
beliefs_affected: {"supports": ["B23"], "contradicts": [], "would_create": ["keyword search with stemming carries most retrieval quality on coding-agent memory; adding a weak embedding leg via fusion trades hit@5 for hit@1"]}
claim_correction: none (the post says hybrid "wasn't better across the board"; the README shows hybrid wins hit@1, MRR and nDCG@10 but loses 3 points at hit@5 and recall@5, which matches)
---

# Fossel: a local-first MCP memory server for coding tools, with a committed retrieval benchmark (FTS vs vector vs hybrid)

- **URL:** https://github.com/7vignesh/fossel
- **Type:** repo
- **Author / org:** Vignesh (GitHub 7vignesh), solo builder
- **Date:** HEAD commit 2026-09-25; benchmark section is in the "[Unreleased]" changelog block
- **Retrieved:** 2026-10-06, commit 3c70faff2add336c8563c48febaf21f9169db319 ("docs: add MCP setup for Windsurf, Zed, Continue, and Cline (#43)"), local clone repos/fossel (read only, nothing executed)
- **Cited by evidence:** memory-trends 2026-09-29 "Builder self-benchmarks for coding"; https://x.com/Vignesh7123/status/2104680885677404548 (@Vignesh7123)
- **Relevance to a memory stack:** medium. A small but honest, reproducible retrieval benchmark on coding-agent memory (our workload class), with category breakdowns including a "superseded" category, plus a shipped git-blob staleness check.

## TL;DR
- On a committed set of 45 memories and 33 labelled queries (fictional e-commerce repo), plain FTS5/BM25 with a three-tier match strategy reaches 90.9% hit@5; hybrid (FTS + hashed-embedding vector, weighted RRF) reaches 87.9% hit@5 but wins hit@1 (78.8% vs 72.7%), MRR (0.832 vs 0.794) and nDCG@10 (0.809 vs 0.792).
- The largest single gain in the project was not semantic: a stemmed-prefix FTS tier added +9.1 points hit@5, and fixing an AND-only query bug moved FTS hit@5 from 45.5% to 81.8%.
- The RRF fusion weight is coupled to embedder quality; the optimum moved from 0.2 to 0.8 as the vector leg improved. Three ideas (cosine floor, adaptive fusion weights, RM3 expansion) were measured and removed.
- Ships "git-aware memory": records the blob sha of files a memory mentions and flags the memory as possibly stale when the file changes (flag only, no ranking change, unmeasured).
- The vector leg is a feature-hashing embedder (no model); results say nothing about a real embedding model. Synonym queries cap at 33.3% hit@5.

## What it claims / describes
Fossel is a stdio MCP server that stores per-repo conventions, bug fixes, decisions and reviewer patterns in SQLite with FTS5 and serves them via `get_context` / `search_memory` (12 MCP tools, 226 tests per fossel.app). Design constraint (AGENTS.md): "no LLM, no model download, no network at runtime."

Retrieval: FTS5 + BM25 with three match tiers: AND, then OR, then stemmed-prefix (conservative suffix stripping plus FTS5 prefix match; the stemmed tier "only ever appends to fill leftover result slots, so it can add recall but never displace an exact-token hit", CHANGELOG.md lines 33-41). Optional hybrid (`FOSSEL_EMBEDDINGS=1`): a deterministic feature-hashing embedding of token unigrams, bigrams and character n-grams, query-side IDF weighting, fused with FTS by weighted Reciprocal Rank Fusion (`src/lib/fusion.ts`). A pluggable external embedder (`FOSSEL_EMBEDDER_CMD`, JSONL batch protocol) exists but is not what the benchmark measures.

Benchmark (bench/README.md): `npm run bench` scores three modes (`fts`, `vector`, `hybrid`) on the `repo-memory` set; results snapshotted to `bench/results/repo-memory.json`; `bench:check` fails on drift. Two surfaces: "search" (pure ranking, used for the table below) and "context" (what `get_context` returns including recent-memory backfill). Design constraints: no pinned memories; memories inserted by direct SQL (bypassing type inference, date grounding and dedupe); recency order arranged so backfill cannot inflate numbers. Query categories: exact, identifier, path, ticket, paraphrase, synonym, multi, superseded ("an outdated memory is planted that outranks the current one lexically"). A LongMemEval-S adapter exists; no LongMemEval result is reported in the README.

Staleness (CHANGELOG "[Unreleased]", lines 9-20): migration 008 `memory_file_refs` records each referenced file's blob sha at write; `get_context` flags drifted memories with "may be stale: middleware.ts changed since this was written". Fails safe without git.

## Numbers
All from README.md "## Benchmarks" (lines 650-694) at commit 3c70faf, search surface, limit 10, n = 33 queries over 45 memories.

| Metric | Value | Baseline | Setup / benchmark (n) | Caveat |
|---|---|---|---|---|
| hit@1 | hybrid 78.8% | fts 72.7%, vector 51.5% | repo-memory, 33 q | single author-written set, no CIs |
| hit@5 | fts 90.9% | hybrid 87.9%, vector 72.7% | same | 1 query = 3.0 points |
| hit@10 | fts 90.9%, hybrid 90.9% | vector 84.9% | same | |
| recall@5 | fts 85.6% | hybrid 82.6%, vector 70.2% | same | |
| MRR | hybrid 0.832 | fts 0.794, vector 0.632 | same | |
| nDCG@10 | hybrid 0.809 | fts 0.792, vector 0.668 | same | binary relevance |
| hit@5, superseded category | 100% all modes | n/a | category size not stated | (inference) category too small or too easy to discriminate |
| hit@5, paraphrase | fts 90.0%, hybrid 80.0%, vector 50.0% | | ~10 q (inference from 10-point steps) | |
| hit@5, synonym | fts 33.3%, hybrid 33.3%, vector 0% | | ~3 q (inference) | "honest ceiling of the zero-dependency approach" |
| hit@5, multi | fts 100%, hybrid 100%, vector 66.7% | | | |
| stemmed-prefix tier | "+9.1 points of hit@5" | without tier | CHANGELOG line 38 | |
| AND-only bug fix | FTS hit@5 45.5% to 81.8%, MRR 0.455 to 0.743 | buggy get_context | CHANGELOG lines 73-79 | |
| query-side IDF | vector MRR 0.519 to 0.632 | no IDF | CHANGELOG line 48 | |
| cosine distribution | relevant median 0.291 (p25 0.204), irrelevant 0.143 (p75 0.211) | | CHANGELOG lines 98-100 | why the cosine floor was removed |
| fusion weight optimum | moved 0.2 to 0.8 | | bench/README.md lines 120-123 | coupled to embedder |
| get_context latency | "<100ms" at "1k memories" | none | fossel.app homepage | not in repo benchmark; machine not stated |

## Mechanism details you could implement
- Three-tier lexical match: AND, then OR fallback, then stemmed-prefix (`stem*`), each tier only appending to leftover slots. The stemmer must output a prefix of the input so `stem*` stays safe ("a classic stemmer mapping 'policies' to 'policy' would break it").
- Weighted RRF with the vector weight re-swept whenever the embedder changes (`npx tsx bench/sweep.ts`); every sweep prints an fts-only row from the same run as baseline.
- Query-side-only IDF: stored vectors remain a pure function of their own text so a new memory never invalidates the index.
- Embedding versioning derived from the embedder command string so swapping models triggers re-indexing.
- Write-time file blob sha references; read-time staleness advisory, flag only.
- Benchmark hygiene: bypass the write path when loading eval memories; report pure-search and assembled-context separately; commit result snapshots and fail CI on drift.

## Limitations, caveats, counter-evidence
- One author-written set of 33 queries; each query is about 3 points; no intervals or seeds (deterministic system, so seeds do not apply, but sampling uncertainty does). The 3-point hit@5 gap between fts and hybrid is one query.
- The "vector" leg is feature hashing, not a learned embedding; nothing here speaks to hybrid with a real embedder.
- Fictional repo; memories are short notes, not long structured artifacts.
- The superseded category scores 100% in every mode, so it does not test supersession handling under realistic pressure (inference).
- Staleness advisory is shipped but not measured.
- Same author built system and benchmark; no independent replication.

## Takeaways for tuning a memory stack
- Before adding embeddings, fix lexical matching (OR fallback, stemming): on this set those moved hit@5 by far more than hybrid did.
- If the reader of the context reads the first item most, judge hybrid by hit@1/MRR; if it reads the whole top-k, judge by recall@k. They can disagree.
- Treat the RRF weight as a function of the vector leg quality, not a constant (nuances B23's k=60 baseline).
- File blob sha references are a cheap staleness signal for code-anchored memories.

## Open questions
- Does the hit@1 win of hybrid hold with a real embedder and on a larger, non-author set?
- What does the LongMemEval-S adapter score?
- Does the staleness advisory change agent behaviour or accuracy?

## Grading and labels
- Directness high: the repo shows the table, eval set and harness. Control medium: same set, same run, fts-only baseline, ablations reported in changelog, but tiny n. Independence low: author built system and set. Reproducibility high: pinned commit, committed set and snapshot. Applicability medium: coding-agent memory notes, but short notes and a fictional repo.
- Pillar R3 (secondary R6 benchmark integrity, R2 staleness). Memory stage: retrieval. Priority: 4 (memory benchmarks; a repo-level coding memory set), not a System One item.
- Beliefs: supports B23 in its qualified form (RRF is a reasonable baseline but the fused leg weight must match leg quality); would create a belief that stemmed lexical search carries most retrieval quality on coding memory notes. Bears weakly on B8 (no graph tested). No contradiction.

## Origin chain
Post 2104680885677404548 (@Vignesh7123, reply to @here_is_dj, 2026-09-28) links fossel.app and a Drive file (a resume, previously checked) -> fossel.app homepage links github.com/7vignesh/fossel -> README.md "## Benchmarks" lines 650-694, CHANGELOG.md "[Unreleased]" lines 9-110, bench/README.md, bench/results/repo-memory.json at 3c70faf -> this note. Independence: single author; no shared dataset with other noted sources; LongMemEval adapter only.
