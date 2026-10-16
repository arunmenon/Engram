---
schema_version: 1
artifact_id: N-20261010-01
artifact_type: note
producer: triage
run_id: triage-20261010T014501Z-4cec
created_at: 2026-10-10T01:54:06Z
input_refs: [{"artifact_id": "post:2103195865280328031", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x-article:2103187018423361536
claim_cluster: x-article:2103187018423361536
feeds: ["decision"]
primary_source: https://x.com/i/article/2103187018423361536
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R3", "R6"]
memory_stage: reranking
priority: 1
tags: {"mechanism": ["jev-rerank", "relevance-cutoff", "variable-k-context"], "workload": ["rag-support-bot", "enterprise-docs"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: the team ran both arms and reports measured deltas", "control": "medium: fixed-six baseline from the same candidate pool in the retrieval sweep, but the agent arm also fetched deeper", "independence": "medium: DocsBot is a Jev customer, not TypeSafe; synthetic public benchmark", "reproducibility": "low: no code, no raw numbers, only relative percentages", "applicability": "medium: RAG over noisy enterprise docs, not engineering-agent artifacts"}
beliefs_affected: {"supports": ["B9", "B11"], "contradicts": [], "would_create": ["Per-candidate rerank cost can exceed the answer-model savings it buys; compare arms on total serving cost per correct answer"]}
claim_correction: The post says Jev reranking gave better answers; the article shows the answer gain (+23.5% relative, 43 scorable questions) has a paired interval that includes zero, is confounded by deeper fetching, and total serving cost rose 67.1%.
---

# Better answers with Jev for reranking (DocsBot, X article by @uglyrobot)

- **URL:** https://x.com/i/article/2103187018423361536 (linked from https://x.com/uglyrobot/status/2103195865280328031)
- **Type:** X article (first-hand builder write-up)
- **Author / org:** @uglyrobot, DocsBot (a RAG support-bot product)
- **Date:** 2026-09-24
- **Retrieved:** 2026-10-10 via the fxtwitter mirror API (x.com returns 402 to us); version: article text as served on that date
- **Cited by evidence:** https://x.com/uglyrobot/status/2103195865280328031 (@uglyrobot)
- **Relevance to a memory stack:** high. A Jev (TypeSafe) relevance cutoff deciding how much context reaches the answer model is exactly our reranking plus assembly stage, and this is the first report we hold that carries the reranker's own bill into the comparison.

## TL;DR
- DocsBot replaced "always pass the top 6 chunks" with "Jev scores every candidate; keep chunks above a relevance cutoff; if none clears, keep the top one".
- 500-question retrieval sweep (EnterpriseRAG-Bench, synthetic, public): at cutoff 0.8, "gold-document discovery rose 7.4% while answer-context tokens fell 38.5%" (relative to fixed six from the same pool).
- 60-question agent run (43 gold-scorable): strictly correct answers +23.5%, evidence found on 21.7% more questions, 14.6% fewer searches, uncached answer-model input -50.1%, answer-model bill -35.9%, but **total serving cost including Jev +67.1%**.
- Claim correction: the answer gain is not significant ("Its paired uncertainty interval still includes no improvement") and the Jev arm also fetched candidates more deeply, so Jev cannot be credited alone.

## What it claims / describes
**Setup.** Hybrid search at alpha 0.5. Jev saw the full user question plus each candidate's title, URL and content. Chunks above the cutoff are kept; if none clears, the highest-scored one is kept, so context size varies per question.
**Test 1, retrieval sweep.** 500 questions; each cutoff compared with "the original first six chunks from the same candidate pool so that deeper fetching could not take credit". Gold-document discovery measured only on questions with a designated source document.
**Test 2, agent comparison.** "A fresh, 60-question agent comparison that followed each question through search decisions, tool calls, the final answer, model usage, and the Jev bill." Correctness judged on 43 core questions with sufficient gold evidence; "those gold chunks were the judge's authoritative source." Judge model: not stated. "In this agent test, the Jev variation also fetched candidates more deeply."
**Why cost rose.** "It scores the candidate pool before the cutoff removes anything, so sending fewer chunks to the answer model reduces its cost without erasing the cost of ranking those candidates on every search."
**Cutoffs.** 0.7: slightly more evidence, smaller savings. 0.9: far more pruning, discovery gain narrows. 0.8 best in both tests. "It is not a magic probability threshold."

## Numbers
All values are relative changes against fixed-six retrieval, "not an absolute accuracy score".

| metric | value | baseline | setup/benchmark (n) | caveat |
|---|---|---|---|---|
| gold-document discovery, cutoff 0.8 | +7.4% | fixed top 6, same pool | EnterpriseRAG-Bench, 500 questions (subset with designated source) | relative; absolute rates not given |
| answer-context tokens, cutoff 0.8 | -38.5% | fixed top 6 | same | |
| strictly correct answers | +23.5% | fixed six agent | 60-question agent run, 43 gold-scorable | "paired uncertainty interval still includes no improvement"; Jev arm fetched deeper |
| questions with designated evidence found | +21.7% | same | same | |
| document searches | -14.6% | same | same | |
| uncached answer-model input | -50.1% | same | same | |
| answer-model bill | -35.9% | same | same | |
| total serving cost incl. Jev | +67.1% | same | same | excludes vector-store billing |

## Mechanism details you could implement
- Score every retrieved candidate with one Jev relevance question (question + title + URL + content as state); keep score >= 0.8; floor of one chunk.
- Measure on the full agent trace, not the retrieval list: correctness, search turns, latency and the complete bill including the reranker.
- Fallback to original ranking when the reranker call fails.
- For multi-file questions, test the more permissive 0.7 cutoff separately.

## Limitations, caveats, counter-evidence
- Synthetic benchmark; no customer documents.
- Agent-arm confound: deeper candidate fetching in the Jev arm.
- 43 scored questions; interval includes zero; one example where the Jev answer "added a recovery step the evidence did not support".
- Only relative percentages; no absolute rates, no code, no per-question data.
- Judge model and whether it shares a model with the answer agent: not stated.
- Cost excludes vector-store billing; Jev price assumed list.

## Takeaways for tuning a memory stack
- A decision-model cutoff can shrink served context substantially (-38.5% tokens) while finding more gold evidence; that supports B9 (stop rule) at retrieval level.
- But rerank cost scales with candidate pool size, not served size. Any rerank arm we test must report total cost per correct answer, and pool size is a knob to sweep (inference).
- The 0.8 cutoff is workload-specific; fit our own.

## Open questions
- Absolute correctness and discovery rates; per-cutoff curve data.
- Total cost at a smaller candidate pool (for example 15 instead of 25).
- Agent-arm result with fetch depth matched.

## Grading and labels
- Directness high: they measured both arms. Control medium: retrieval sweep controls pool, agent run does not. Independence medium: customer, not vendor. Reproducibility low: no code or raw data. Applicability medium: support-doc RAG.
- Pillar R9 (Jev at the reranking stage), secondary R3 (assembly budget), R6 (cost accounting). Stage: reranking. Priority 1.
- B9 supports: a relevance cutoff cut context 38.5% with more gold evidence found. B11 supports in part: the floor of one chunk is a ranker that never returns empty. Would create: rerank cost can exceed answer-model savings.
- No contradiction rows.

## Origin chain
post 2103195865280328031 (@uglyrobot) -> X article 2103187018423361536 -> sections "The cutoff had a sweet spot" and "The agent got better answers. The bill still grew." -> this note. Independence: DocsBot and EnterpriseRAG-Bench are not shared with other notes on Jev reranking (hevmind, LanceDB, Hindsight).
