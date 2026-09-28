---
schema_version: 1
artifact_id: N-SURVEY-20260927-15
artifact_type: note
producer: triage
run_id: survey-20260927T054501Z-e1b9
created_at: 2026-09-27T05:53:00Z
idempotency_key: note:survey:arxiv:2411.04051
input_refs: []
pillar_primary: R1
pillar_secondary: []
beliefs_affected: {supports: [B2], contradicts: []}
evidence: {directness: 3, control: 2, independence: 4, reproducibility: 3, applicability: 3}
source_url: https://arxiv.org/abs/2411.04051
found_via: survey
strength: paper-single-benchmark
---

# Reproducible Hybrid Time-Travel Retrieval in Evolving Corpora

- **URL:** https://arxiv.org/abs/2411.04051 (read via https://arxiv.org/html/2411.04051, v1)
- **Type:** paper
- **Author / org:** Moritz Staudinger, Florina Piroi, Andreas Rauber (TU Wien, Vienna, Austria)
- **Date:** 2024-11-06 (arXiv v1); venue SIGIR-AP '24, December 9 to 12, 2024, Tokyo
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, pillar R1, beliefs B2 (supports, as a boundary case), B1 (qualifies, see Limitations)
- **Relevance to a memory stack:** high, it is the clearest measured demonstration that a BM25 channel cannot be replayed from retained documents alone because global statistics drift, and it shows one concrete two-store design for as-of re-execution

## TL;DR

- Two stores side by side: Lucene serves live queries fast; MonetDB (column store) holds a timestamped mirror of documents and per-term postings so that BM25 can be recomputed "as of" any past timestamp.
- Core claim (verbatim): "as global term statistics change when documents change or are added to a corpus, queries using typical ranked retrieval models are not even reproducible for the parts of the document corpus that have not changed."
- As-of reads are served by one store only (MonetDB). Lucene is not queried historically; it overwrites documents. So this is not a point-in-time read spanning heterogeneous stores; it is "mirror everything you need into one versioned store and re-execute there."
- Numbers on German Wikipedia (520,000 articles, 26 batches of 20,000): Lucene about 80 ms per query; MonetDB as-of re-execution 2,000 ms rising to 20 s at 520K docs; MonetDB index 4.05 GB vs Lucene 3.82 GB; 1 rank swap in 10,400 re-executed queries, caught by a stored result hash.
- No baseline against full snapshots or re-indexing; single corpus; BM25 only (dense retrieval explicitly future work).

## What it claims / describes

Problem framing: in domains that need citable, re-executable searches (systematic literature reviews, patent retrieval, academic and medical search), Boolean retrieval dominates because ranked retrieval is not reproducible over evolving collections. Even if a document did not change, its BM25 score changes when other documents are added or updated, because df, N and average document length are collection-global.

Architecture:
- Lucene is the primary engine for all normal queries. Documents go through Lucene preprocessing (tokenization, stemming, stopword removal), and the resulting vocabulary and term statistics are synchronized into MonetDB with timestamps.
- Update behavior (verbatim): "Lucene overwrites document representations in its index when documents get updated and reprocessed, with some terms possibly becoming unavailable. In such cases, in the MonetDB representation of the index, we mark the terms as deleted, with a deletion timestamp, and a new MonetDB entry is created."
- MonetDB schema (Figure 1 excerpt): Documents table `document_id, name, valid_from, valid_to, approx_len`; dictionary `term, df`; term statistics `document_id, term, tf`.
- BM25 is implemented in SQL. Statistics are computed at query time, not stored (verbatim): "we calculate the df at retrieval time for VCBR, and do not keep any pre-computed values in the database." N and avgdl are likewise derived from documents valid at the requested timestamp.
- Query store (verbatim): "a dedicated table together with a persistent identified (PID), the execution timestamp, hash keys of the document IDs of the ranked result set and other descriptive metadata required for citation purposes."
- Reproduction path: look up the query by PID, execute it against MonetDB filtered to the original execution timestamp, recompute the hash of the ranked document IDs, compare with the stored hash (verbatim): "After the re-execution, the hash is re-computed and verified against the hash key stored in the query store."

Lineage: the design implements the Research Data Alliance (RDA) Working Group on Data Citation recommendations (Rauber et al.), which require versioned and timestamped data, a query store, re-execution against the timestamp, result-set verification by hash, and persistent identifiers. The paper cites Rauber et al. (2021) as a meta-analysis of dynamic data citation implementations, and prior column-store IR work (Muehleisen et al. 2014) and Boesch (2017) on reproducible ranking from evolving collections. No later work from this group was fetched (budget); none is asserted here.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Corpus | 520,000 articles, German Wikipedia, May 2020 dump, 3.72 GB | n/a | inserted in 26 batches of 20,000 docs | simulated evolution by batch insertion, not real edits |
| Vocabulary | 7,787,028 unique terms; 159,150,478 total terms | n/a | full corpus | none |
| Lucene indexing time | "approximately 13 min per 20K documents", stable | n/a | per batch | hardware not stated |
| MonetDB indexing overhead | "linearly increasing, from initially 2:30 minutes to 8 minutes for the last batch" | Lucene 13 min/batch | per batch | grows with collection; no sharding ("no optimization such as sharding ... has been applied") |
| Storage | MonetDB 4.05 GB (Dict 194 MB; Docs 39 MB; Terms 3.82 GB) | Lucene index 3.82 GB | after all 520K docs | hybrid roughly doubles storage; text says "slightly larger than the Lucene index" |
| Live query latency | "approx. 80 ms per query" | n/a | Lucene, top-20 | roughly constant with corpus size |
| As-of re-execution latency | "from 2000 ms initially to 20 seconds against an index of 520,000 documents" | Lucene 80 ms | MonetDB, top-20, SQL BM25 | linear in collection size; authors call it acceptable because re-execution is rare |
| Query sets | 4 sets x 100 queries (1, 2, 5, 10 terms) | n/a | run after each of 26 batches, 10,400 queries total | query generation method not stated in what I extracted |
| Score deviation Lucene vs MonetDB | "in the range of 10^-5" | typical gap between adjacent ranked docs about 10^-2 | floating point differences | text only |
| Hash mismatches | "a single case occurred where two documents were sufficiently close in their score to be swapped" | n/a | 10,400 queries | detected by hash, not prevented |
| Hardware | not stated | | | |
| Code | "released as Open Source Software" at https://anonymous.4open.science/r/Hybrid-Information-Retrieval | | | anonymized review link, no pinned version |

## Mechanism details you could implement

- Keep BM25 statistics recomputable, not cached: store per-document `tf` rows and document `approx_len` with `valid_from/valid_to`, and derive df, N, avgdl with a timestamp filter at query time. This is the minimal state needed to make a lexical channel as-of readable (level L2) rather than only replaying the served list (level L1).
- Deletions and updates are tombstoned with a deletion timestamp and a new row, never overwritten. In an event ledger this maps directly: the ledger already has the history; the lexical projection must retain it too, or be rebuildable as of a ledger position.
- Query store row: PID, execution timestamp (for Engram, a ledger position is the better key than wall time), and a hash of the ranked document IDs. On replay, recompute and compare; treat a mismatch as a detected, reportable divergence rather than silently accepting.
- Split read paths: fast live engine for serving, slow versioned engine for audit and re-execution. Latency budget for the audit path can be orders of magnitude higher (80 ms vs 2 to 20 s here).
- Hash on IDs only, not scores, tolerates the 10^-5 floating point noise but still catches rank swaps between near-tied documents.

## Limitations, caveats, counter-evidence

- As-of capability lives in one store. Lucene cannot answer historically. The hybrid is two stores with one of them authoritative for history, so it does not contradict B2 (no first-class as-of read spanning heterogeneous stores).
- BM25 only. The authors list "reproducible dense retrieval" as future work, so vector channels are uncovered.
- Evaluation is a single corpus, batch-append simulation; no measured edits or deletions workload in the extracted results; no comparison with full snapshots, Lucene commit points, or re-indexing baselines.
- Lucene and MonetDB compute slightly different scores; reproduction is from MonetDB, so the "reproduced" list can differ from what Lucene actually served (1 swap in 10,400). (inference) For audit, the served list itself must also be retained, since re-execution in a different engine is not bit-identical to what the user saw.
- B1 qualification (inference): the paper stores both a hash of the served result and a versioned corpus. Retaining served artifacts with source version is enough to verify what was shown (L1), but the paper's central point implies it is not enough to re-run the retrieval or ask a new question as of that moment (L2), because unchanged documents rank differently once global statistics move. B1 is therefore not contradicted for "reproduce the decision from what was served", but it is insufficient for "re-derive or counterfactually probe the retrieval".
- Hardware not reported, so the latency numbers are not portable.

## Takeaways for tuning a memory stack

- (inference) Any BM25 channel over a growing memory (notes, commits, issue text) will reorder results for unchanged items as the corpus grows. An Engram replay that re-runs BM25 against the live index will not reproduce a past decision's context even if every retrieved item is byte-identical.
- (inference) Make the lexical projection ledger-position-addressable: either store tf and doc length rows with validity intervals (this paper), or rebuild statistics from the ledger prefix on demand.
- Keep a result hash per served bundle; it is cheap and detects divergence on replay.
- Budget: an as-of lexical path cost roughly 1x extra storage and 25x to 250x query latency here; acceptable for audit, not for serving.

## Open questions

- How much does rank order actually drift for a memory-sized corpus (thousands to hundreds of thousands of items) between adjacent ledger positions? The paper does not report drift magnitude, only reproduction fidelity.
- What query generation method was used for the 1, 2, 5, 10 term sets? Not captured.
- Does the group's later work extend to dense retrieval or cross-store citation? Not checked (fetch budget).
- Would Lucene commit points or segment snapshots give a cheaper single-engine as-of read? Not evaluated.

## Grading

- directness 3: directly about as-of re-execution of ranked retrieval, but in one store, so it informs B2 as a boundary case rather than testing it.
- control 2: single corpus, no baseline systems, simulated evolution, hardware unstated.
- independence 4: academic group with no stake in agent memory products.
- reproducibility 3: code released at an anonymized link and corpus is a public dump, but no pinned versions or hardware.
- applicability 3: the IDF drift mechanism transfers directly to BM25 channels in engineering-agent memory; architecture and latencies are search-engine specific.
