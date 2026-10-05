---
schema_version: 1
artifact_id: N-20260928-25
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:06:21Z
input_refs: [{"artifact_id": "post:2104481408450204061", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:atlaso.ai/lab/memory-benchmark
claim_cluster: url:atlaso.ai/lab/memory-benchmark
feeds: ["memory"]
primary_source: https://www.atlaso.ai/lab/memory-benchmark
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R6
pillar_secondary: ["R3"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["bm25", "hybrid-retrieval", "freshness-decay", "no-llm-ingest", "llm-fact-extraction-baseline"], "workload": ["chat-memory"], "lifecycle_stage": ["ingestion", "retrieval", "assembly"], "cross_cutting": ["reader-matched", "multi-judge", "mcnemar", "reproduction", "correction-log", "cost-per-query"]}
evidence_grade: {"directness": "high: the page reports the matched-reader head-to-head the post cites, with counts", "control": "medium: reader (Qwen 3.5-9B) and judges held constant, McNemar on discordant pairs, but a single canonical run and a protocol iterated v1.1 to v1.8 before the headline", "independence": "low: Atlaso measures itself against a competitor it sells against", "reproducibility": "low: page points to github.com/atlaso-labs research/option3 paths, but no public repo in that org holds benchmark artifacts on 2026-09-28", "applicability": "low: chat QA with a 9B reader; not engineering-agent artifacts"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["Holding the reader model fixed changes memory-system rankings; mem0's published LongMemEval-S figure does not reproduce under its own judge (93.4 published vs 44.2 observed, vendor-run)", "Higher retriever recall@5 did not give higher QA accuracy and cost 3.4x the context tokens (MemPalace vs Atlaso, shared GPT-5 reader)"]}
claim_correction: The 53.6% vs 47.0% is a single run with a small Qwen 3.5-9B reader (absolute scores far below GPT-4o-reader leaderboards), Letta ties Atlaso exactly, Atlaso loses to mem0 on a LoCoMo adversarial subset (24.0% vs 35.5%), the page dates from May 2026 with an August 2026 correction, and the promised artifacts are not in any public atlaso-labs repo.
---

# Atlaso vs mem0: LongMemEval-S memory benchmark, reader-matched (Atlaso Labs)

- **URL:** https://www.atlaso.ai/lab/memory-benchmark (post link carried utm parameters, stripped)
- **Type:** vendor blog / lab page
- **Author / org:** Ashish Khandelwal, Atlaso Labs Inc.
- **Date:** published May 13, 2026; "Correction (August 2026)" note on the page
- **Retrieved:** 2026-09-28, web page, no version or commit. Also checked https://github.com/atlaso-labs (7 public repos: cursor, antigravity, codex, claude-code, cli, mcp, .github; none holds `research/option3/`).
- **Cited by evidence:** https://x.com/AtlasoLabs/status/2104481408450204061 (@AtlasoLabs, feed memory, 2026-09-28, vendor's own account)
- **Relevance to a memory stack:** medium. The design principle (hold the answering model constant, use several judges, report McNemar on discordant pairs) is what our frozen-harness arms need; the product numbers themselves are vendor-run and weakly reproducible.

## TL;DR
- Headline (Table 1): with Qwen 3.5-9B answering for both systems on all 500 LongMemEval-S questions, Anthropic Haiku 4.5 strict judge: Atlaso 53.6% (268/500) vs mem0-default 47.0% (235/500), +6.6pp; "McNemar on the 141 discordant pairs: chi2 = 7.26, p about 0.007". Direction holds under GPT-4o strict and GPT-5 permissive judges (calibrated F1 +6.3 and +7.4).
- Same protocol, wider field (Table 1b): Letta v0.16.7 53.6% (exact tie), Cognee 27.8%, LangMem v0.0.30 8.6%.
- mem0 published 93.4% does not reproduce: "we observe 44.2%, a 49.2 percentage point gap from the published number, under mem0's own scoring rule". The page admits this conflates judge methodology with pipeline configuration.
- Atlaso loses on a LoCoMo adversarial subset (Table 4): mem0-default 35.5% (71/200) vs Atlaso 24.0% (48/200).
- Claim correction: single canonical run, protocol iterated before the headline (not pre-registered), 9B reader, tie with Letta, loss on LoCoMo subset, and the artifacts the page lists are not in any public atlaso-labs repository.

## What it claims / describes
**Why reader-matched.** The post: "Memory benchmarks can mislead when the answering model changes between systems." The page holds the reader constant: "Qwen 3.5-9B produces the final answer for both arms". A GPT-5 reader configuration exists but is labelled separately.

**Judges.** Three LLM judges: Anthropic Haiku 4.5 ("strict, both raw accuracy and calibrated-abstention F1"), OpenAI GPT-4o (strict), OpenAI GPT-5 (permissive), plus mem0's verbatim judge prompt for the reproduction analysis only. None of the judges is the reader model (Qwen), so judge and reader do not share a model.

**Runs.** One canonical run under protocol v1.8; the protocol converged through public tags v1.1 to v1.8 (`prereg-option3-v1.8`). No confidence interval numbers are printed, although a bootstrap CI script is listed among artifacts.

**Atlaso mechanism (as described).** Zero LLM calls at ingestion ("deposits"); BM25 plus scope filtering at deposit granularity; hybrid retrieval (keyword plus embeddings with freshness decay); "contradiction-aware retrieval". The embedding model, decay function and top-k are not stated in what was extracted.

**mem0 configuration.** mem0 OSS default, extraction LLM gpt-4o-mini, "1 x gpt-4o-mini per turn" at ingestion. Full mem0 pipeline (platform) not reproduced.

**Retriever-reader swap (Table 2).** Shared GPT-5 reader, Atlaso retriever vs MemPalace retriever: the retriever with far higher R@5 answers worse and uses 3.4x the tokens. Per-category note: MemPalace's session-level retrieval drops 40 points on preference questions (56.7% -> 16.7%).

**Correction.** "Correction (August 2026). An earlier version of this page presented a four-judge head-to-head table as a shared-reader result." The page says the error was found through the `_returned_model` field per row. The atlaso-labs GitHub org page still links "Atlaso vs mem0, four judges on LongMemEval-S" (pre-correction framing, observed 2026-09-28).

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| accuracy, Haiku 4.5 strict | Atlaso 53.6% (268/500) | mem0-default 47.0% (235/500), +6.6pp | LongMemEval-S n=500, Qwen 3.5-9B reader both arms (Table 1) | single run; McNemar chi2 = 7.26, p about 0.007 on 141 discordant pairs |
| calibrated F1, Haiku 4.5 strict | 0.675 | 0.607, +6.8 | same | |
| calibrated F1, GPT-4o strict | 0.697 | 0.634, +6.3 | same | |
| calibrated F1, GPT-5 permissive | 0.677 | 0.603, +7.4 | same | |
| Letta v0.16.7, Haiku strict | 53.6% (268/500) | Atlaso 53.6%, "exact tie" | Table 1b | |
| Cognee | 27.8% (139/500) | -25.8pp | Table 1b | |
| LangMem v0.0.30 | 8.6% (43/500) | -45.0pp | Table 1b | Redis's page shows a 95.4% placeholder for LangMem, not comparable |
| mem0 published vs observed under mem0's judge | 93.4% published, 44.2% observed | 49.2pp gap | page text | conflates judge and pipeline; Redis lists mem0 "reported" at 49.0% instead |
| R@5 / QA / tokens per query / $ per query, Atlaso retriever | 64.9% (n=479) / 61.8% (n=500) / 7,128 / $0.0096 | MemPalace retriever 96.2% / 58.6% / 24,469 / $0.0348 | Table 2, shared GPT-5 reader | different reader than Table 1 |
| $ per query, full fixture | Atlaso $0.00030 | mem0 $0.0115 (99.3% = extraction) | Table 3, Qwen reader, n=500 | per query, not TCO; page says sign flips at frontier reader prices |
| $ per query, KU+TR slice | Atlaso $0.00031 | mem0 $0.00057 (90% = extraction) | Table 3, n=211 | |
| LLM calls at ingestion | 0 | 1 x gpt-4o-mini per turn | Table 3 | |
| LoCoMo adversarial subset | Atlaso 24.0% (48/200) | mem0-default 35.5% (71/200) | Table 4, n=200, one judge (Haiku 4.5 strict) | Atlaso loses by 11.5pp; "over-abstains, or returns the planted distractor" |
| retrieval ladder accuracy / evidence recall@k | no memory 5.7% / 0%; naive BM25 52.6% / 77%; Atlaso keyword only 55.9% / 82%; Atlaso hybrid 69.2% / 96%; gold evidence only 68.7% / 100% | | Table 5, n=211 subset, Qwen 3.5-9B reader, Haiku 4.5 strict | hybrid scores above the gold-evidence ceiling, within noise at n=211 (inference) |
| embeddings toggle | 11 questions won vs 1 lost | | McNemar chi2 = 6.75, p < 0.05 | subset size as in Table 5 (inference) |

## Mechanism details you could implement
- Benchmark protocol to copy: one fixed reader model for every memory backend; two or three judges from different vendors than the reader; report accuracy and an abstention-aware F1; McNemar on discordant pairs rather than comparing two percentages; store the actual returned model id per row (`_returned_model`) so reader mix-ups are detectable.
- Retrieval ladder as an ablation template: no memory -> naive BM25 over raw turns -> keyword with scope filter -> hybrid with embeddings -> gold evidence only. Report evidence recall@k next to accuracy on each rung.
- Write-side design: zero LLM calls at ingest, all intelligence at read (BM25 + embeddings + freshness decay). The trade stated on the page: Atlaso reads about 6x more context per query (about 3,000 vs about 500 tokens) but saves the per-turn extraction call.

## Limitations, caveats, counter-evidence
- Page's own list: mem0's full pipeline not reproduced; mem0-verbatim judge not run on every arm; "Pre-registration is a version trail, not a clean prior commit"; cost is per query, not TCO, and reader-dependent; single LoCoMo subset; a correction was required.
- Single canonical run; no seed variation; no printed intervals.
- 9B reader: absolute accuracies (47 to 54%) are far below GPT-4o-reader numbers (DaiDocs 83.00%, Redis 86.5%), so these results say nothing about ranking under frontier readers (inference). Table 2 uses a GPT-5 reader and is not comparable with Table 1.
- Reproducibility gap: the page lists `research/option3/judge.py`, `research/option3/runs/`, per-question JSONLs and a bootstrap CI script under `github.com/atlaso-labs`, but none of the seven public repositories in that org contains them (checked 2026-09-28). Artifacts may be private or elsewhere; not verified.
- Vendor comparing itself to a competitor; the only system it loses to on the headline benchmark is not in the headline (Letta ties).
- Date: the post (2026-09-28) presents a May 2026 page; the correction is from August 2026.
- No instruction-bearing content aimed at AI systems was found on the page or org listing.

## Takeaways for tuning a memory stack
- For our PDLC benchmark: freeze the reader and the judge, vary only the memory backend, and require a paired test. This page is a working example of how much reader choice changes a comparison.
- Retrieval recall is not the score: a 96.2% R@5 retriever answered worse (58.6%) than a 64.9% one (61.8%) at 3.4x the tokens. DaiDocs reports the same pattern (99% content recall, 72.18% accuracy on multi-session). Measure end-to-end with the reader in the loop, and count tokens.
- Write-time extraction dominates cost for mem0-style stores at small-reader prices (99.3% of mem0's per-query cost); at frontier reader prices the sign flips. Price both sides for our workload.
- Treat mem0 vendor numbers as unreproduced: 93.4% published vs 44.2% to 47.0% measured here.

## Open questions
- Where are the per-question JSONLs and judge prompts? Can the McNemar result be recomputed?
- Does the Atlaso > mem0 gap survive a GPT-4o or Claude reader on all 500 questions?
- Why does hybrid retrieval score above the gold-evidence ceiling (69.2% vs 68.7%): noise, or extra context helping the reader?

## Grading and labels
- Directness: high. The page gives the exact head-to-head with counts and tests.
- Control: medium. Reader and judges fixed, paired test, but single run and an iterated protocol.
- Independence: low. Vendor vs competitor.
- Reproducibility: low. Listed artifacts not found in public repos.
- Applicability: low. Chat memory, 9B reader.
- Pillars: R6 primary (reader-matched evaluation, reproduction of mem0's claim); R3 secondary (retrieval ladder, context tokens).
- Stage: evaluation.
- Tags: reader-matched, multi-judge, McNemar, BM25, hybrid retrieval, no-LLM ingest, cost per query.
- B20 supports: the post's headline narrows on a primary read (tie with Letta, loses on LoCoMo subset, small reader).
- Would create: "Reader-matched comparisons change memory-system rankings; mem0's published LongMemEval-S number does not reproduce (vendor-run)", grade lead.
- Would create: "Higher retriever recall@5 did not give higher QA accuracy at 3.4x tokens (shared GPT-5 reader)", grade lead.
- Contradiction: none with a belief. Cross-source disagreement: mem0's published LongMemEval figure is 93.4% here but Redis's leaderboard lists mem0 "reported" at 49.0%; LangMem 8.6% here vs a 95.4% placeholder on Redis's page.

## Origin chain
- Post https://x.com/AtlasoLabs/status/2104481408450204061 (@AtlasoLabs) -> https://www.atlaso.ai/lab/memory-benchmark -> Tables 1, 1b, 2, 3, 4, 5, limitations list, correction note -> artifact pointer github.com/atlaso-labs (research/option3), not found publicly.
- Independence: author and system owner are the same vendor. Shares the LongMemEval-S dataset with the Redis, DaiDocs and Acropolis notes in this run; shares no answer model with them (Qwen 3.5-9B vs GPT-4o or gemini-3.7-flash); uses GPT-4o as one of three judges, the same model family DaiDocs and Redis use as their only judge. MemPalace retrieval recall is also cited by DaiDocs (96.6% R@5 there vs 96.2% R@5 here, different units and n).
