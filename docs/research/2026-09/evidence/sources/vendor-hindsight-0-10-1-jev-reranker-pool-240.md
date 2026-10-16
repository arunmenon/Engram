---
schema_version: 1
artifact_id: N-20260927-13
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2102100813531218191", "file_id": null, "sha256": null}, {"artifact_id": "post:2102100818002371024", "file_id": null, "sha256": null}, {"artifact_id": "post:2102100824088334341", "file_id": null, "sha256": null}, {"artifact_id": "post:2102100819428491657", "file_id": null, "sha256": null}, {"artifact_id": "post:2102100816479862955", "file_id": null, "sha256": null}, {"artifact_id": "post:2102100820888113655", "file_id": null, "sha256": null}, {"artifact_id": "post:2102100822507098201", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:hindsight.vectorize.io/blog/2026/09/21/version-0-10-1
claim_cluster: url:hindsight.vectorize.io/blog/2026/09/21/version-0-10-1
feeds: ["memory", "decision"]
primary_source: https://hindsight.vectorize.io/blog/2026/09/21/version-0-10-1
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R4
pillar_secondary: ["R3", "R7"]
tags: {"mechanism": ["listwise-choice-rerank", "candidate-pruning", "bank-export-import"], "workload": ["chat-memory", "LoCoMo"], "lifecycle_stage": ["read", "rerank"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: release notes show a results table, not raw runs", "control": "medium: same candidate pools and questions for both rerankers, but only one baseline (MiniLM)", "independence": "low: vendor measuring its own integration on a benchmark it already reports", "reproducibility": "low: no commit, no per-query outputs, pool-240 subset selection not described", "applicability": "medium: rerank over large recall pools is our read path, but chat-memory questions, not engineering artifacts"}
beliefs_affected: {"supports": ["B10", "B11", "B14"], "contradicts": [], "would_create": []}
claim_correction: The post says the gap "widens as the pool grows"; the 240-candidate result is on 60 questions, not the 200 of the 30-candidate result, so the two rows are not a paired comparison.
---

# Hindsight 0.10.1 release notes: Jev listwise reranker at 30 and 240 candidates, bank clone/export/rename

- **URL:** https://hindsight.vectorize.io/blog/2026/09/21/version-0-10-1
- **Type:** vendor blog (release notes)
- **Author / org:** Vectorize (vectorize-io), Hindsight team
- **Date:** 2026-09-21
- **Retrieved:** 2026-09-27 (WebFetch of the release page; no commit or tag recorded in the page)
- **Cited by evidence:** release thread by @vectorizeio, 2026-09-21: https://x.com/vectorizeio/status/2102100813531218191 , https://x.com/vectorizeio/status/2102100818002371024 , https://x.com/vectorizeio/status/2102100824088334341 (+4 more in the thread). Backlog cluster from CKPT-triage-20260927T022455Z (deferred by budget).
- **Relevance to a memory stack:** medium-high. First vendor number for a one-call listwise rerank at a production-sized pool (240 candidates), plus the pruning cost (19% of evidence lost) that motivates keeping pruning off.

## TL;DR
- Hindsight 0.10.1 ships a TypeSafe Jev reranker (`HINDSIGHT_API_RERANKER_PROVIDER=typesafe`) that asks "one question with every candidate as an option" (listwise Choice), default model `jev-latest`.
- LoCoMo, 200 questions, 30 candidates: recall@1 0.950 vs 0.800 for local MiniLM; recall@5 0.966 vs 0.876; NDCG@10 0.957 vs 0.850; 0.027 s vs 0.12 s per query. These pool-30 numbers were already in `github-vectorize-io-hindsight.md`.
- **New relative to the existing note:** at 240 candidates (60 questions) recall@1 0.783 vs 0.583, recall@5 0.903 vs 0.719, NDCG@10 0.856 vs 0.682, 0.063 s vs 0.41 s per query.
- Optional pruning (`..._PRUNE_CANDIDATES=true`) raises precision 0.051 to 0.850 but cuts 19% of evidence. The page states scores "are rank positions, not confidences".
- Claim correction: the "gap widens as the pool grows" framing compares a 200-question row with a 60-question row; not paired, no intervals.

## What it claims / describes
Reranker provider for Hindsight's recall pipeline. Instead of scoring each candidate independently, the recall pipeline sends one Jev request whose single question has every candidate as an option; the returned distribution is used as the ranking. Because the distribution is over options within one call, the page warns that scores "are rank positions, not confidences" (do not threshold them like a cross-encoder score).

Configuration flags (verbatim names): `HINDSIGHT_API_RERANKER_PROVIDER=typesafe`, `HINDSIGHT_API_RERANKER_TYPESAFE_API_KEY`, `HINDSIGHT_API_RERANKER_TYPESAFE_MODEL`, `HINDSIGHT_API_RERANKER_TYPESAFE_BASE_URL`, `HINDSIGHT_API_RERANKER_TYPESAFE_TIMEOUT`, `HINDSIGHT_API_RERANKER_TYPESAFE_MAX_CONCURRENT`, and the optional `HINDSIGHT_API_RERANKER_TYPESAFE_PRUNE_CANDIDATES=true`.

Other changes in the release: "Clone a bank in a single API call"; "Unified export and import with an explicit transfer scope"; "Rename a bank in place with `hindsight-admin`"; "Retain on chunked documents stops rebuilding the prompt"; "Bank lists are no longer slow"; "Archive creation doesn't block the event loop"; non-English content keeps its own script; truncated Anthropic responses fixed (from the X thread).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| recall@1 | 0.950 | MiniLM 0.800 | LoCoMo, 200 questions, 30 candidates | already in existing note; single run, no interval |
| recall@5 | 0.966 | 0.876 | same | |
| NDCG@10 | 0.957 | 0.850 | same | |
| latency per query | 0.027 s | 0.12 s | same | Jev is a hosted call; how 0.027 s is below typical Jev round trip (hundreds of ms in other sources) is not stated (inference: amortised or batched timing) |
| recall@1 | 0.783 | MiniLM 0.583 | LoCoMo, 60 questions, 240 candidates | new; 60 questions, subset selection not stated |
| recall@5 | 0.903 | 0.719 | same | |
| NDCG@10 | 0.856 | 0.682 | same | |
| latency per query | 0.063 s | 0.41 s | same | |
| precision with pruning | 0.850 | 0.051 without | pruning flag on | "cut 19% of evidence" |

Judge: not applicable (retrieval metrics against LoCoMo evidence labels). Model version: `jev-latest` (not pinned in the page). Cost: not stated.

## Mechanism details you could implement
- One Choice question over all candidates (up to 240 in the reported run). Jev supports up to 255 options per choice (from `docs-typesafe-jev-api.md`), so 240 is near the ceiling (inference).
- Treat the output as a ranking, never as a relevance probability; no absolute floor.
- Pruning is a separate, opt-in switch; the vendor's own number is a 19% evidence loss, which matches the synthesis rule "keep ranking on and pruning off by default".
- Bank portability (clone, export/import with transfer scope, rename) is an interoperability surface: a memory bank as a movable unit (R7).

## Limitations, caveats, counter-evidence
- No commit, no per-query results, no intervals, one run.
- The 240-candidate row uses 60 questions; how they were chosen is not stated. Not paired with the 200-question row.
- Only baseline is local MiniLM; no pointwise-Jev arm at 240, no purpose-built reranker (Voyage, Cohere). hev/reranker (`github-hev-reranker-jev-as-a-reranker.md`, and `blog-hevmind-jev-as-a-reranker.md` this run) found per-document Nouls beat one Choice when many documents are relevant (NFCorpus 0.358 vs 0.316); LoCoMo questions typically have few gold items, which favours Choice (inference).
- Latency figures are lower than every other Jev latency in the catalogue (164 to 345 ms p50 round trips elsewhere); measurement method not stated.

## Takeaways for tuning a memory stack
- If you rerank a recall pool with a decision model, the listwise one-call shape keeps a 20-point recall@1 lead over a small cross-encoder even at 240 candidates on LoCoMo, per the vendor.
- Keep pruning off; if you turn it on, measure evidence retention, not precision.
- Never threshold listwise scores.

## Open questions
- Pool-240 on the full 200 questions, with intervals?
- Listwise Choice vs pointwise Noul at 240 candidates, and on multi-gold questions?
- Answer-level effect (does recall@1 +0.2 change answer accuracy)?

## Grading and labels
- Directness: medium, a table in release notes, not raw outputs.
- Control: medium, same pools for both arms, one weak baseline.
- Independence: low, vendor on its own product.
- Reproducibility: low, no commit or per-query data.
- Applicability: medium, large-pool rerank is our read path, but chat memory.
- Strength: vendor-benchmark. Pillar R4 (rerank design as a decision implementation); secondary R3 (read path), R7 (bank export/import).
- Beliefs: supports B10 (listwise Choice beats a local baseline at 30 and 240, but no pointwise arm here); supports B11 (pruning loses 19% of evidence); supports B14 (vendor itself says scores are rank positions, not confidences).
- Contradiction rows: none.

## Origin chain
@vectorizeio thread (2102100813531218191 and 6 replies) -> release page hindsight.vectorize.io/blog/2026/09/21/version-0-10-1 -> "Reranker" section tables (30 and 240 candidates) -> this note. Independence: same vendor and benchmark (LoCoMo) as `github-vectorize-io-hindsight.md` and `x-article-vectorize-hindsight-jev-reranker.md`; not an independent replication. Answers part of WR-20260926-05 (pool-30 and pool-240 values).
