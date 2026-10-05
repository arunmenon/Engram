---
schema_version: 1
artifact_id: N-SURVEY-20260930-02
artifact_type: note
producer: triage
run_id: survey-20260930T054503Z-298f
created_at: 2026-09-30T05:55:30Z
idempotency_key: note:survey:arxiv:2608.13883
input_refs: []
pillar_primary: R7
pillar_secondary: [R6]
memory_stage: evaluation
priority: 4
beliefs_affected:
  supports: [B22, B20]
  contradicts: []
evidence: {directness: medium, control: medium, independence: low, reproducibility: medium, applicability: medium}
strength: vendor-benchmark
source_url: https://arxiv.org/abs/2608.13883
found_via: survey
---

# MemoryLake on MemoryArena: A Matched Study of Agent Memory Backends (with the MemoryArena benchmark it runs on)

- **URL:** https://arxiv.org/abs/2608.13883 (HTML v1 read: https://arxiv.org/html/2608.13883v1). Benchmark paper read alongside: https://arxiv.org/abs/2602.16313 (HTML v1), site https://memoryarena.github.io/
- **Type:** paper (vendor-authored study) plus benchmark paper
- **Author / org:** Chaoqun Zhan, Qiang Zhou, Guannan Li, Zhenqiang Huang, Qianjin Wang ("MemoryLake Team"). MemoryArena: Zexue He, Yu Wang and others (Stanford, UCSD, UIUC, Princeton, Pittsburgh, 2077AI), ICML 2026.
- **Date:** 2026-08-14 (study); 2026-02-18 (benchmark)
- **Retrieved:** 2026-09-30 (local copy: out/log/raw/2608.13883.html)
- **Cited by evidence:** survey run survey-20260930T054503Z-298f, R7 question 1 (swap test evidence) and R6 question 3 (benchmark map)
- **Relevance to a memory stack:** high for the swap-test failure modes it records; medium for the ranking, which is vendor-run with overlapping intervals.

## TL;DR
- Four memory backends are plugged into one agent harness at one integration point: MemoryLake, Mem0, vector RAG (text-embedding-3-small) and a long-context control. Agent framework, requested model alias (gpt-5-mini), task samples and scoring code are shared.
- The swap was not clean. Unmodified Mem0 scored 0/20 on progressive retrieval because the harness writes whole agent traces and Mem0's API "rejects any single write above 100,000 tokens"; the environment step returned 500 and the query was skipped after three retries. A per-write cap inside the Mem0 adapter moved it to 3/20.
- The harness also silently dropped samples: when the agent returned no answer, about 9 MB was sent to the judge, which returned 400, and "the query disappears from the results rather than scoring zero".
- Headline: macro success rate 20.5 % for MemoryLake against 13.6 % for the best comparator. The authors state that "marginal Wilson intervals overlap" and "no statistical-win claim is made". Single run per system.
- On MemoryArena itself (benchmark paper), memory systems average lower task success than plain long context or plain retrieval: memory agents 0.12, long context 0.17, RAG 0.20 average success rate.

## What it claims / describes
MemoryArena is "a unified evaluation gym for benchmarking agent memory in multi-session Memory-Agent-Environment loops": ordered, interdependent subtasks where a result from an earlier session becomes a premise or constraint later. Domains and sizes (benchmark paper): bundled web shopping (150 tasks, 6 subtasks each), group travel planning (270 tasks, 5 to 9 subtasks), progressive web search (256 tasks, 2 to 16 subtasks), math formal reasoning (40 tasks), physics formal reasoning (20 tasks). Average 6.9 sessions and 57 action steps per task. Tasks are human-crafted, built on WebShop, TravelPlanner, BrowseComp-Plus and derivation chains from research papers. No software engineering domain. Metrics: success rate (SR, whole task) and progress score (PS, fraction of subtasks).

The MemoryLake study holds the agent and scoring fixed and changes the memory integration. Coverage is partial: all 40 math, all 20 physics, 30 of 270 travel groups, all 150 shopping bundles, 20 of 221 released progressive queries. The output-token budget was raised from the upstream 15,000 to 32,000 for all four systems.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Math SR | MemoryLake 9/40 (22.5 %, Wilson [12.3, 37.5]) | Mem0 8/40; vector RAG 7/40; long context 5/40 | gpt-5-mini alias, single run | margin of 1 task |
| Physics SR | MemoryLake 12/20 (60.0 %, [38.7, 78.1]) | long context 9/20; vector RAG 8/20; Mem0 6/20 | same | margin of 3 tasks |
| Travel SR | 0/30 for all four ([0.0, 11.4]) | n/a | 30 of 270 groups | floor |
| Shopping SR | 0/150 for three systems; long context 1/150 | n/a | | floor |
| Progressive retrieval SR | MemoryLake 4/20; Mem0 3/20 (capped re-run; unmodified 0/20); vector RAG 2/20; long context 2/20 | n/a | 20 of 221 queries | margin of 1 task |
| Macro average SR (post hoc, equal weight) | MemoryLake 20.5 % | long context 13.6 %; vector RAG 13.5 %; Mem0 13.0 % (unmodified 10.0 %) | five domains | not a paired test |
| Progressive, MemoryLake on full set | 26.7 % (n=221, [21.3, 32.9]) | no comparator on full set | | |
| Mem0 write sizes on progressive | median 58,217 tokens over 132 writes, maximum 216,751 | API limit 100,000 tokens per write | | cause of the 0/20 |
| Slot coverage, progressive | MemoryLake 93.7 %; Mem0 unmodified 22.5 %; Mem0 capped 84.5 %; vector RAG 64.8 %; long context 94.4 % | n/a | | denominators differ across systems |
| MemoryArena paper, average SR | long context 0.17; memory agents 0.12 (Letta 0.15, Mem0 0.13, Mem0-g 0.14, ReasoningBank 0.08); RAG 0.20 (BM25 0.19, MemoRAG 0.22, GraphRAG 0.19) | n/a | GPT-5.1-mini agent | benchmark authors' run |
| MemoryArena paper, latency per subtask | long context GPT-5.1-mini 74.2 s; Letta 132.8 s; Mem0 114.8 s; MemoRAG 102.8 s; GraphRAG 90.2 s | n/a | average over domains | |
| Cost, tokens, latency in the MemoryLake study | not stated | | | the authors say resource use is not matched or reported |

Judge: the benchmark's own scoring scripts. Math, physics and progressive retrieval use an LLM judge; the judge model is not named in what was read. MemoryLake's internal operations and the agent share the gpt-5-mini alias. Embedders differ: MemoryLake uses bge-m3, the vector RAG arm uses text-embedding-3-small ("did not run an embedder-matched control").

Text versus table: the abstract reports 13.6 % for "the best comparator"; the table shows that comparator is the long-context control, not a memory system. Consistent, but the abstract does not say so.

## Mechanism details you could implement
Swap-test failure classes this study exposes, each of which a contract test can check before any score is compared:
1. **Payload limits.** A backend that rejects large writes turns into skipped tasks, not an error the harness reports. Test: write the largest payload the harness can produce and require a typed error, not a dropped sample.
2. **Backend-specific patches.** The cap was added "inside the Mem0 integration, gated on the backend name". An adapter that needs a backend-named branch is a contract violation to record.
3. **Silent sample loss.** A scorer that fails on one item must score it zero or fail the run. Compare denominators across arms before comparing rates (the study reports slot coverage for this reason).
4. **Unmatched embedder.** Two arms with different embedders cannot attribute a difference to the memory structure (the MemDelta finding already in the landscape, reproduced here by admission).
5. **Unmatched resources.** Tokens, auxiliary model calls, latency and cost were not recorded per arm.

## Limitations, caveats, counter-evidence
- Conflict of interest, stated: "All authors are affiliated with MemoryLake, a commercial memory system, and the compared systems are third-party baselines."
- Stated: "Small samples and no paired inference"; intervals overlap; single run; partial and non-random coverage of two domains.
- Stated: model snapshot ids and decoding settings are not available; "run reconstructed from public configuration alone will not reproduce these scores".
- Stated: the MemoryLake engine is proprietary. The companion repository (https://github.com/memorylake-ai/memorylake-memoryarena-benchmark) holds manifests, per-instance scored outputs and aggregation scripts. It does not re-run the judges.
- MemoryArena paper: the claim that systems "with near-saturated performance on existing long-context memory benchmarks like LoCoMo perform poorly" is qualitative; no LoCoMo score is reproduced next to the MemoryArena scores.
- (inference) Two of five domains sit at the floor (0 of 30 and 0 of 150), so the macro average is driven by three small domains.

## Takeaways for tuning a memory stack
- B22's swap test needs explicit contract checks for payload size, error semantics and sample accounting. This study shows all three fail in practice on a public harness.
- For our PDLC memory benchmark: score interdependent multi-session tasks with executable or structural oracles, publish denominators per arm, and keep a plain long-context and a plain retrieval arm. On MemoryArena those two arms match or beat the memory products.
- Do not quote the 20.5 % against 13.6 % as a win for structured memory. The authors do not.

## Open questions
- Would an embedder-matched and token-matched rerun keep the ordering?
- Which MemoryArena domain is closest to build-time engineering work? None is; sequential formal reasoning (derivation chains where a later step depends on an earlier result) is the nearest in structure.
