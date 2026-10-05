---
schema_version: 1
artifact_id: N-20260929-10
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104718259194904583", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:davidalmeida90/jev-for-finance
claim_cluster: github:davidalmeida90/jev-for-finance
feeds: ["decision", "memory"]
primary_source: https://github.com/davidalmeida90/jev-for-finance
source_commit: 6c014f48c7d0ce9a05b4511c1e5224c7184225a1
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R3"]
memory_stage: reranking
priority: 1
tags: {"mechanism": ["jev-choice-rerank", "jev-noul-sufficiency-check", "bm25-e5-rrf-candidates", "top2-passages"], "workload": ["document-qa", "financial-filings"], "lifecycle_stage": ["retrieval"], "cross_cutting": ["cost", "latency", "hosted-api-confidentiality"]}
evidence_grade: {"directness": "high: end-to-end accuracy, tokens, latency and cost measured for Jev RAG vs an agentic RAG baseline on the same 50 questions", "control": "medium: same questions and same answering LLM per row, but different retrieval scope (whole filings vs 30-passage pool) and author-written questions", "independence": "medium: independent builder, not TypeSafe, but author wrote questions and grading", "reproducibility": "medium: MIT repo with scripts, e2e logs and summary JSON; needs Jev and LLM API keys", "applicability": "medium: long structured documents (10-Ks) resemble our long artifacts, but single-fact lookup questions, not engineering-agent tasks"}
beliefs_affected: {"supports": ["B10", "B11"], "contradicts": [], "would_create": []}
claim_correction: 50/50 is for one answering model (DeepSeek Flash); the other three got 49, 48 and 45 of 50 (local Qwen 3.5 4B 45/50), "100x fewer tokens" counts tokens read by the answering LLM (840 vs 82,908), and "up to 18x cheaper" compares to the uncached agent cost ($0.0133 vs $0.0007; cached agent $0.0031), on 50 author-written questions over four latest 10-Ks, one run.
---

# Jev for Finance: Jev as a passage reranker and sufficiency check for RAG over 10-K filings

- **URL:** https://github.com/davidalmeida90/jev-for-finance
- **Type:** repo (with builder write-up at https://davidariasfinance.com/research/is-jev-efficient-for-rag/)
- **Author / org:** davidalmeida90 (David Arias, @Davidariasfin); MIT license (commit message)
- **Date:** head commit `6c014f48c7d0ce9a05b4511c1e5224c7184225a1` (2026-09-28T23:39:25Z, "MIT license; drop the article folder, link the write-up on davidariasfinance.com"); tests run "27 and 28 September 2026" (write-up)
- **Retrieved:** 2026-09-29, commit 6c014f48c7d0ce9a05b4511c1e5224c7184225a1 (SHA from GitHub commits API; no local clone, shell unavailable). Read: README.md, jev_rag.py at that commit, and the linked write-up. Not read: benchmark/*.py, e2e logs, *_summary.json.
- **Cited by evidence:** https://x.com/Davidariasfin/status/2104718259194904583 (@Davidariasfin, 2026-09-28)
- **Relevance to a memory stack:** high for priority 1. A measured Jev-at-rerank result on long structured documents with a sufficiency check and a comparison against local rerankers and an agentic baseline.

## TL;DR
- Pipeline: split the latest 10-K into 1,500-character passages; BM25 + e5 with reciprocal rank fusion picks 30; one Jev call with a `choice` ("Which passage states the information needed to answer the question?") and a `noul` ("Do these passages contain the answer to the question?"); if the noul < 0.5 rank the next 30 (max 2 rounds); the answering LLM reads only the top 2 passages.
- Retrieval only, correct passage ranked first, on the 50 questions: "BM25 34%, e5 embeddings 52%, BM25 + e5 40%, MiniLM reranker 54%, bge reranker 36%, Jev 90%."
- End to end with DeepSeek Flash: Jev RAG 50/50, 1 LLM call, 840 tokens, 2.0 s, $0.0007 vs agentic RAG 46/50, 4.7 calls, 82,908 tokens, 11.1 s, $0.0031 cached / $0.0133 uncached.
- Claim correction: 50/50 is one model; 49, 48, 45 for the other three; token and cost ratios are against the answering LLM's reads and the uncached agent price.
- Grading: regex on figures plus a hand read of every answer, 13 manual overrides "in both directions"; questions written by the author; single run.

## What it claims / describes
- **Candidate generation.** Fetch the latest 10-K from SEC EDGAR; split into 1,500-character passages (`STEP, K = 1500, 30` in jev_rag.py); rank with BM25 and e5 embeddings fused by RRF; take top 30.
- **Jev call** (jev_rag.py): endpoint `https://openrouter.ai/api/v1/systemone`, model `jev-latest`. Two questions in one call: `choice` "Which passage states the information needed to answer the question?" with one option per passage id (criteria "passage {pid}"), and `noul` "Do these passages contain the answer to the question?".
- **Stop / expand rule:** loop up to 2 rounds; break if `exists >= 0.5`, otherwise rank `ranking[rnd * K:(rnd + 1) * K]` (next 30). Final: `top2 = pick["ranked"][:2]` from the most recent Jev call. There is no "none" admission: the top 2 always go to the LLM.
- **Answer prompt** (verbatim): "You answer questions about SEC filings using only the passages given. Reply in one or two sentences with the figures and units; compute any change or ratio the question asks for. If the passages do not contain the answer, say so."
- **Baseline:** agentic RAG following the Vals AI Finance Agent design: LLM agent searches EDGAR, reads whole filings (up to 8 turns, max 3 filings), calculator tools, looping.
- **Questions:** 50 analyst-style questions over Apple, Microsoft, Nvidia, Amazon latest 10-Ks, "phrased the way an analyst asks them, often in words the filing never uses" (e.g., "What was Microsoft's bottom line in its latest fiscal year?", "Why did AWS sales grow?"). Per-company counts and whether questions were fixed before seeing Jev results: not stated.
- **Grading:** "A passage counts as correct when it contains the exact answer, a figure or a sentence, which is a strict rule." Answers "graded against the filing and then read by hand"; regex on figures, overrides in each script's `MANUAL` table ("13 overrides in the headline runs, in both directions").

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Correct passage ranked first | Jev 90% | BM25 34%, e5 52%, BM25 + e5 40%, MiniLM reranker 54%, bge reranker 36% | 50 questions, pool of 30 from BM25+e5 RRF | Jev saw up to 60 passages if expanded; rerankers' pool not stated |
| End-to-end correct, DeepSeek Flash | 50 of 50 | agentic RAG 46 of 50 | 50 questions, one run | author grading, 13 overrides across headline runs |
| End-to-end correct, Qwen 3.7 Flash | 49 of 50 | agentic 41 of 50 | same | |
| End-to-end correct, GPT-5 nano | 48 of 50 | agentic 34 of 50 | same | |
| End-to-end correct, Qwen 3.5 4B local (Ollama) | 45 of 50 | agentic not reported for this model | same | |
| LLM calls per question | 1 | 4.7 | DeepSeek Flash | |
| Tokens read per question | 840 (DeepSeek), 988 (Qwen 3.7), 815 (GPT-5 nano), 990 (local) | 82,908, 82,428, 64,634 | | whether Jev's own input tokens are counted is not stated |
| Latency | 2.0 s (DeepSeek), 12.6 s (local 4B) | 11.1 s | | |
| Cost per question | $0.0007 (DeepSeek), $0.0006 (local) | $0.0031 cached, $0.0133 uncached | Jev priced at "$0.042 per million tokens, and output is free" (write-up) | whether $0.0007 includes the Jev call is not stated |

## Mechanism details you could implement
- One Jev call carrying both a listwise `choice` (rank) and a pool-level `noul` (sufficiency) over up to 30 candidates; threshold 0.5 on the noul triggers a second page of 30. This is a concrete sufficiency stop rule (B9) combined with listwise rerank (B10).
- Rank and admit separately: the ranker has no "none"; top 2 always pass; the answering LLM is told to say so if the passages lack the answer (B11 split).
- Candidate pool from cheap hybrid retrieval; 1,500-char passages; top 2 passages to the reader.

## Limitations, caveats, counter-evidence
- 50 author-written questions, four "US large caps with clean, well-structured 10-Ks", latest filing only; historical-year questions need date parsing "not currently implemented".
- "Jev's existence check can sit close to its 0.5 threshold." No ablation of the sufficiency check (with vs without expansion).
- Baseline differs in scope (whole filings, EDGAR search) so the comparison is pipeline vs pipeline, not rerank vs rerank; the rerank comparison is the retrieval-only table.
- Hosted Jev: "Jev runs in TypeSafe's cloud", confidentiality concern; write-up also cites Jev's "documented weakness with numerical data".
- One run; no variance reported (and djev's note shows hosted Jev varies on identical requests).

## Takeaways for tuning a memory stack
- On long structured documents, a single Jev choice over 30 hybrid candidates put the right passage first 90% of the time vs 54% for MiniLM and 36% for bge rerankers here, consistent with Hindsight's rerank result (B10) on a different domain.
- A pool-level "does this contain the answer" noul is a cheap way to decide whether to page deeper; test it as our sufficiency stop, with an ablation.
- Top-2 passages were enough for single-fact questions; engineering questions spanning several artifacts will likely need more (inference).

## Open questions
- Does the Jev input token count (30 x 1,500 chars per call) enter the reported tokens and cost?
- How often did the 0.5 noul trigger expansion, and how often was it wrong?
- Per-company breakdown and question-writing protocol.
- Rerankers' pool size and inputs in the retrieval-only comparison.

## Grading and labels
- Directness: high, direct measurement of rerank accuracy and end-to-end outcome.
- Control: medium, same questions per row; baselines differ in scope; author-written set.
- Independence: medium, independent of TypeSafe; single author.
- Reproducibility: medium, scripts and logs in a pinned MIT repo.
- Applicability: medium, long documents but finance lookups.
- Strength: repo-pinned.
- Pillars: R9 primary; R3 secondary.
- Memory stage: reranking.
- Tags: jev-choice-rerank, jev-noul-sufficiency-check; cost, latency, hosted-api-confidentiality.
- Beliefs: supports B10 (listwise Jev choice beat local rerankers, 90% vs 54% top-1), supports B11 (ranker without "none", separate admission logic); B9 mechanism implemented but not ablated, so no support claimed.

## Origin chain
- post https://x.com/Davidariasfin/status/2104718259194904583 -> https://github.com/davidalmeida90/jev-for-finance @ 6c014f48c7d0ce9a05b4511c1e5224c7184225a1 -> README.md tables (main results, LLM comparison, retrieval-only sentence), jev_rag.py (request, thresholds, answer prompt) -> write-up https://davidariasfinance.com/research/is-jev-efficient-for-rag/ (dates, grading rule, Jev price, limitations).
- Independence: post, repo and write-up by the same author. In the triage queue this repo was grouped under cluster github:23blocks-os/ai-maestro (#32); split out here as its own claim cluster.
