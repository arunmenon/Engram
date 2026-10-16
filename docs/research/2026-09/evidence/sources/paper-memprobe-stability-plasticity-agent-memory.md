---
schema_version: 1
artifact_id: N-20260929-20
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104817738279796817", "file_id": null, "sha256": null}, {"artifact_id": "post:2104820679610949654", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.30558
claim_cluster: arxiv:2609.30558
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.30558
source_commit: 9068d8d9a2a47268fe6f7601b99a56a283c37be5
strength: paper-single-benchmark
pillar_primary: R6
pillar_secondary: ["R2", "R10"]
memory_stage: evaluation
priority: 4
tags: {"mechanism": ["supersession", "interference", "misinformation-source-credibility", "consolidation-strength", "reconsolidation", "shared-reader-protocol"], "workload": ["chat-memory", "incremental-ingestion", "knowledge-update"], "lifecycle_stage": ["linking", "staleness", "evaluation"], "cross_cutting": ["memory-benchmark", "paired-bootstrap", "bonferroni", "aggregate-metric-masking"]}
evidence_grade: {"directness": "high: directly measures whether memory systems keep current vs previous values after an update, the PDLC changed-requirement case", "control": "medium: fresh store per episode, one shared reader and typed scoring for all systems, paired episode bootstrap with Bonferroni; but one run per system, adapter choices differ per system (Mem0 get_all, Graphiti top-15 edges), Graphiti skipped about 178 of about 1100 session-adds", "independence": "medium: academic authors not affiliated with any evaluated vendor (inference, affiliations not listed on abs page); gold labels author-built, dialogue text GPT-5.4 assisted, no inter-annotator agreement found", "reproducibility": "high: MIT code, episodes, gold specs, per-system reports and bootstrap JSON at pinned commit; pip freeze and patches documented", "applicability": "medium: 56 synthetic chat episodes with atomic facts, not long structured PDLC artifacts; paradigms (interference, source credibility) map well to changed requirements and stale trackers"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Aggregate memory accuracy can hide opposite update policies: Graphiti and LangMem tie overall (62.5 vs 65.2, p=0.534) but differ on previous-value 96.4 vs 67.9 (p=0.002, Bonferroni over 18) while Graphiti trails on current-value 66.1 vs 80.4 (p=0.041, not Bonferroni significant); PDLC memory evals must report current-value and previous-value separately", "Under a shared Gemini reader and 56 diagnostic episodes, Mem0 (mem0ai 2.0.2, get_all retrieval) scored lowest of six incremental memory systems (41.5 overall; plasticity 28.6) and full-context (88.8) beat all six systems"]}
claim_correction: none (post numbers match Section 5.2 and repo JSON; adds that previous-value n is 28 probes per system and that Graphiti is worse than LangMem on current-value)
---

# MemProbe: stability-plasticity diagnostics for six incremental memory systems (Mem0, Zep/Graphiti, LangMem, Cognee, A-MEM, MemoryOS; Letta and Hindsight excluded)

- **URL:** https://arxiv.org/abs/2609.30558 (HTML v1 https://arxiv.org/html/2609.30558v1); code and data https://github.com/jq-ding/MemProbe
- **Type:** paper (arXiv cs.CL; comments: "Accepted by EMNLP 2026 Main") plus repo
- **Author / org:** Jiaqi Ding, Guorong Wu (affiliations not listed on the abs page)
- **Date:** v1 submitted 24 Sep 2026 21:10:36 UTC
- **Retrieved:** 2026-09-29. arXiv abs and HTML v1 via WebFetch. Repo shallow clone at `repos/memprobe`, commit `9068d8d9a2a47268fe6f7601b99a56a283c37be5` (2026-09-28 15:26:12 -0400, "Update LICENSE"). Read: README.md, IMPLEMENTATION_DETAILS.md, env/pip_freeze_full.txt (grep), results/suite56/analysis/pairwise_probe_bootstrap.json, results/suite56/analysis/paired_bootstrap_ci.json (grep), data/suite56 probe counts (grep). Second suite (`data/suite40`, `results/suite40`) not read.
- **Cited by evidence:** @runbywren, https://x.com/runbywren/status/2104817738279796817 and https://x.com/runbywren/status/2104820679610949654 (2026-09-29). Also mentioned in context/reports/memory-2026-09-29.md via the same post.
- **Relevance to a memory stack:** high for evaluation design. It is a ready-made, MIT-licensed diagnostic for exactly the questions our PDLC memory benchmark needs (did the system notice a changed value, does it still know the old value, does it weigh sources), with an adapter interface to plug in our own store.

## TL;DR
- 56 author-built diagnostic episodes (14 per paradigm: interference, misinformation, consolidation strength, reconsolidation window), 1,246 sessions, 224 probes; six incremental memory systems plus four reference baselines, all answered by one shared reader (gemini-3-flash-preview) with typed JSON scoring against gold, no LLM judge.
- Post claim verified: "The three mid-range systems (Graphiti, LangMem, MemoryOS) are statistically indistinguishable in overall accuracy (all pairwise p>0.37)" and "Graphiti preserves historical values far better than LangMem (previous-value 96.4 vs. 67.9, 95% CI [+9.1,+48.3], p=0.002)", "a gap that survives Bonferroni correction across all 18 system-probe comparisons" (Section 5.2). Repo JSON matches (pairwise_probe_bootstrap.json:21, :29, :57-66).
- The other side of the tradeoff: Graphiti trails LangMem on current-value (66.1 vs 80.4, difference -14.3, CI [-28.6, 0.0], p=0.041, not significant at the Bonferroni alpha 0.0028). Graphiti keeps history; LangMem overwrites.
- Overall ranking (Table 1): Oracle RAG 93.3, Full-context 88.8, A-MEM 88.4, Cognee 81.7, Time-aware RAG 68.8, Naive RAG 68.3, LangMem 65.2, Graphiti 62.5, MemoryOS 60.3, Mem0 41.5. Three of six memory systems score below naive RAG.
- Letta/MemGPT ("incompatible with our Gemini-controlled function-calling protocol") and Hindsight ("PostgreSQL/pgvector and glibc incompatibilities") were excluded (Appendix A.5); Zep is represented only by open-source graphiti-core on Kuzu, not Zep Cloud; supermemory not tested.

## What it claims / describes
**Framing.** Borrowed from cognitive psychology: a memory system must be plastic (accept valid updates) and stable (preserve what should not change, resist misinformation). Aggregate accuracy mixes the two. Abstract: "systems with similar aggregate scores exhibit distinct behavioral profiles."

**Paradigms** (Section 3, quoted from HTML):
- I Interference: "first learn an association AA-BB and later learn a competing association AA-CC. When probed... producing CC... reflects retroactive interference."
- II Misinformation: whether "conflicting values... from users, assistants, tools, retrieved documents, stale trackers... warrant revision" based on source credibility.
- III Consolidation strength: "Strongly reinforced memories are more resistant... update behavior should depend on prior support."
- IV Reconsolidation window: "Recalling a consolidated memory can temporarily make it modifiable... reactivation changes update sensitivity."

**Probes:** current-value, previous-value, change-detection, source, conflict-value, temporal. Metrics: Plasticity(S) = A(S; U) on probes where valid updates should be accepted; Stability(S) = A(S; P) on probes where memory should be preserved; UpdateError = 1 - Plasticity; PreserveError = 1 - Stability; SP-Balance = 2 x Plasticity x Stability / (Plasticity + Stability) (harmonic mean).

**Suite construction.** Multi-stage pipeline "separating experimental design from surface dialogue generation": fact-type design, value-pair design, latent specification, dialogue generation "with GPT-5.4 assistance", validation. Dialogue inspired by LongMemEval, LoCoMo and MemoryArena; "target manipulations and gold labels were author-constructed". 12 of 56 episodes are "split" episodes with `perturbation_p1` / `perturbation_p2` sessions (IMPLEMENTATION_DETAILS.md:31). A second suite (suite40, built with the authoring toolkit from LoCoMo/LongMemEval material, CC BY-NC 4.0) exists; its numbers were not retrieved.

**Common protocol** (IMPLEMENTATION_DETAILS.md:19-29): fresh isolated store per episode; incremental ingestion session by session "exactly as the memory system's API expects"; at probe time ask the system to retrieve (not answer), using the lowest-level context-only call where needed; unified reader `gemini-3-flash-preview` with a shared structured-JSON prompt (`READER_SYSTEM` + `_PROBE_SCHEMAS` in src/eval/protocol.py); scoring by `score_answer()` typed field comparison. "every memory system's internal LLM = gemini-2.5-flash; every reader = gemini-3-flash-preview". Non-GPT reader chosen because dialogue was GPT-5.4 generated, "to reduce generator and reader coupling".

**Per-system integration** (IMPLEMENTATION_DETAILS.md section 2):
- Mem0 `mem0ai==2.0.2`, Chroma, gemini embeddings (models/gemini-embedding-001, 768 dims), library default temperature; ingestion `m.add(messages, user_id=eid)` per session; retrieval `m.get_all(filters={"user_id": eid})`, i.e. all extracted facts, no search.
- LangMem `langmem==0.0.30`, `create_memory_manager(..., enable_inserts=True, enable_updates=True, enable_deletes=True)`, temperature 0.0, no embedder; `existing` memories carried forward across sessions; retrieval passes all final memories.
- Graphiti / Zep `graphiti-core==0.29.0` (pip freeze lists 0.29.2) with `kuzu==0.11.3` embedded graph DB; `add_episode(..., reference_time=base+timedelta(hours=i), group_id=eid)` per session; retrieval `g.search(query, group_ids=[eid], num_results=15)` returning `edge.fact` strings; two upstream-bug patches for Kuzu; "internal gemini-2.5 extraction produced malformed JSON on ~178/~1100 session-adds across 56 ep; these were skipped gracefully".
- Cognee `cognee==1.1.0`, `SearchType.GRAPH_COMPLETION`, `only_context=True`, `top_k=15`.
- A-MEM (WujiangXu/A-mem clone), `find_related_memories(probe_question, k=15)`, patched strict json_schema to json_object for Gemini.
- MemoryOS (BAI-LAB), `retriever.retrieve_context`, patched `reasoning_effort="none"` because gemini-2.5-flash returned empty content.
- Baselines: full-context reader; naive RAG (top-5 keyword); time-aware RAG (same retrieval, sessions labelled with true timeline position); oracle RAG (only non-filler sessions, a diagnostic upper bound).

**Statistics.** "Episode-level bootstrap intervals (2,000 resamples, fixed seed)"; paired episode-level bootstrap, "two-sided p = 2 min(P(d<=0), P(d>=0))", iters 2000, seed 42 (paired_bootstrap_ci.json:2-13); probe-level pairwise tests among Graphiti, LangMem, MemoryOS with Bonferroni alpha 0.002777 over 18 tests (pairwise_probe_bootstrap.json:9-16). One run per system; no repeated runs or seeds for the systems themselves were found.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| overall accuracy [95% CI] | A-MEM 88.4 [83.9, 92.4]; Cognee 81.7 [76.3, 86.6]; LangMem 65.2 [57.6, 72.3]; Graphiti 62.5 [55.8, 68.8]; MemoryOS 60.3 [53.6, 66.5]; Mem0 41.5 [35.7, 46.9] | Oracle RAG 93.3 [89.7, 96.4]; Full-context 88.8 [84.4, 92.9]; Time-aware RAG 68.8 [61.2, 75.9]; Naive RAG 68.3 [60.3, 76.3] | Table 1; 56 episodes, 224 probes, reader gemini-3-flash-preview | single run per system |
| Graphiti vs LangMem overall | LangMem - Graphiti = +0.0268, CI [-0.0625, 0.1116], p=0.534 | | paired episode bootstrap, 2000 iters, seed 42 (paired_bootstrap_ci.json:1756-1769) | "tied" |
| LangMem vs MemoryOS overall | +0.0491, CI [-0.0536, 0.1473], p=0.378 | | same (:1872-1885) | the minimum of the three pairwise p (source of "p>0.37") |
| Graphiti vs MemoryOS overall | +0.0223, p=0.6885 | | same (:2104-2117) | |
| previous-value accuracy | Graphiti 96.43, LangMem 67.86, MemoryOS 89.29 | | probe-level (pairwise_probe_bootstrap.json:21, :29, :37); 28 previous-value probes in suite56 (grep count of "previous_value" in data/suite56/episodes.jsonl) | 96.43 = 27/28 and 67.86 = 19/28 (inference) |
| Graphiti - LangMem, previous-value | +28.57, CI [9.09, 48.28], p=0.002 | Bonferroni alpha 0.00278 over 18 tests | pairwise_probe_bootstrap.json:57-66; Section 5.2 | survives Bonferroni per paper |
| current-value accuracy | Graphiti 66.07, LangMem 80.36, MemoryOS 60.71 | | pairwise_probe_bootstrap.json:20, :28, :36 | |
| Graphiti - LangMem, current-value | -14.29, CI [-28.57, 0.0], p=0.041 | Bonferroni alpha 0.00278 | pairwise_probe_bootstrap.json:46-55 | not significant after correction; direction opposite to previous-value |
| other probes, Graphiti vs LangMem | change-detection 69.6 vs 76.8 (p=0.3325); source 44.1 vs 44.1 (p=0.9975); conflict-value 42.9 vs 53.6 (p=0.358); temporal 45.5 vs 40.9 (p=0.565) | | pairwise_probe_bootstrap.json:22-33, :68-110 | |
| Plasticity / Stability / SP-Balance | A-MEM 91.1 / 85.7 / 88.3; Cognee 75.0 / 88.4 / 81.1; LangMem 63.4 / 67.0 / 65.1; Graphiti 58.9 / 66.1 / 62.3; MemoryOS 54.5 / 66.1 / 59.7; Mem0 28.6 / 54.5 / 37.5 | | Table 2 | PreserveErr and UpdateErr are 1 minus these |
| paradigm accuracy (Interference / Misinformation / Consolidation / Reconsolidation) | A-MEM 82.1 / 85.7 / 96.4 / 89.3; Cognee 80.4 / 80.4 / 85.7 / 80.4; LangMem 60.7 / 66.1 / 69.6 / 64.3; Graphiti 53.6 / 60.7 / 75.0 / 60.7; MemoryOS 66.1 / 55.4 / 57.1 / 62.5; Mem0 41.1 / 46.4 / 33.9 / 44.6 | Full-context 82.1 / 91.1 / 91.1 / 91.1; Oracle RAG 89.3 / 92.9 / 98.2 / 92.9 | Table 3; 14 episodes per paradigm | small n per cell |
| historical / source / temporal fidelity | A-MEM 100.0 / 64.5 / 68.0; Cognee 96.0 / 64.5 / 73.0; Graphiti 96.0 / 41.9 / 45.0; MemoryOS 89.0 / 33.9 / 55.0; LangMem 68.0 / 46.8 / 41.0; Mem0 71.0 / 17.7 / 36.0 | Full-context 100.0 / 66.1 / 77.0 | Table 5 | |
| reader ablation (Gemini -> Qwen3-32B overall) | A-MEM 88.4 -> 72.8; Cognee 81.7 -> 68.3; LangMem 65.2 -> 60.3; Graphiti 62.5 -> 61.6; MemoryOS 60.3 -> 51.8; Mem0 41.5 -> 41.5 | | reader-ablation table; "Spearman rho=0.94, Kendall tau=0.87" | ranking stable, absolute levels reader-dependent |
| split episodes | "Split current-value (Split CV) and change-detection (Split CD) accuracy remain stuck at 8.3%" | | Table 7, Section 5.5; 12 split episodes | which system/condition this refers to: not extracted |
| Graphiti ingestion failures | about 178 of about 1100 session-adds skipped (malformed JSON from gemini-2.5-flash extraction) | | IMPLEMENTATION_DETAILS.md:79 | about 16% of sessions missing from Graphiti's graph (inference) |
| cost / latency | not stated in paper extraction | | README has an "Expected runtime and cost" section heading | not read |

## Mechanism details you could implement
- **Probe design for a PDLC memory benchmark:** for each fact that changes (requirement R v1 -> v2), ask at least three probes: current-value ("what is R now?"), previous-value ("what was R before the change?"), change-detection ("did R change?"). Add source probes (who or which artifact changed it) and conflict-value probes (two sources disagree). Score each separately and report Plasticity, Stability and their harmonic mean (SP-Balance), not only overall accuracy.
- **Misinformation paradigm maps to trust ordering:** conflicting values arriving from users, assistants, tools, retrieved documents and "stale trackers" should update memory only when the source is credible; in PDLC terms, a stale ticket must not overwrite an approved design decision (inference on mapping).
- **Shared-reader protocol:** ask each store to retrieve context only; answer with one fixed reader and a structured-JSON schema; score typed fields against gold. This isolates memory quality from answer generation and avoids an LLM judge.
- **Paired episode-level bootstrap** with Bonferroni across system-probe comparisons; the repo ships `src/analysis/bootstrap.py paired` and `probe` commands.
- **Adapter interface** (README.md:127-143): implement `reset(episode_id)`, `ingest(session)`, `retrieve(question)` returning memory text for the shared reader, or `answer(probe)` if context cannot be exposed. Our store could be evaluated on suite56 directly.
- **Integration details that change outcomes:** Graphiti returns top-15 `edge.fact` strings without validity timestamps in this setup, so the reader sees old and new facts side by side, which plausibly explains high previous-value and weaker current-value (inference). Mem0 served all extracted facts via `get_all`, so its low score reflects extraction and update behaviour, not retrieval ranking (inference).

## Limitations, caveats, counter-evidence
- Author-stated (Limitations, verbatim): "MemProbe is a diagnostic framework rather than an exhaustive benchmark... the current evaluation still covers only a limited range of domains, languages, user histories and deployment settings. We use a unified reader and structured scoring protocol to enable controlled comparison across systems... although native end-to-end deployments may differ. Finally, because part of the dialogue surface form is generated with LLM, the suite may still contain generator-specific biases in wording, scenario realization, or interaction style."
- Small n: 28 previous-value probes per system; the 28.6-point gap is 8 probes (inference from 27/28 vs 19/28). 14 episodes per paradigm.
- One run per system; stochastic ingestion (Mem0 at library default temperature, A-MEM and MemoryOS at temperature 0.7 in patched calls) was not repeated, so run-to-run variance is not in the intervals (inference).
- Integration choices differ by system and several required patches; Graphiti lost about 178 of about 1100 session-adds to malformed extraction JSON; Graphiti version is 0.29.0 in the docs and 0.29.2 in the pip freeze. Results describe these configurations under Gemini models, not vendor-recommended deployments (Zep Cloud, Mem0 platform).
- Gold labels author-constructed; no inter-annotator agreement numbers were found in the extraction (appendix E sections on validation exist but figures were not extracted).
- Reader dependence: A-MEM drops 15.6 points with Qwen3-32B as reader while ranking correlation stays high.
- Episodes are chat dialogues with atomic facts, not long structured artifacts; nothing on build-time reads, trace links or multi-document supersession.
- No instruction-bearing content aimed at AI agents was found in the arXiv page or repo docs; one grep hit ("The AI agent is unable to translate...") is benchmark dialogue content inside a suite40 prompt cache, not directed at readers.

## Takeaways for tuning a memory stack
- In our PDLC memory benchmark, always split "current requirement" from "previous requirement" and "did it change" questions; a single accuracy number can hide a store that never overwrites (Graphiti-like) or one that forgets history (LangMem-like).
- Decide the product policy explicitly: engineering agents need both, current value by default and history on demand. A supersede-and-retain design with validity served to the reader (valid_at / superseded_by) is the design to test against overwrite-only (inference).
- Full-context (88.8) beat every incremental memory system except A-MEM (88.4, within CI), and naive RAG beat three of six. For small histories, raw context remains a strong baseline to include in any arm-vs-arm test.
- Do not adopt Mem0 defaults for update-heavy workloads without our own check: lowest overall (41.5) and plasticity (28.6) here, under a non-default Gemini configuration.
- Reuse the MemProbe adapter and bootstrap code rather than building a harness from scratch; add a PDLC suite built with its authoring toolkit.

## Open questions
- Does Graphiti's high previous-value with low current-value persist if the adapter passes edge validity (`valid_at`, `invalid_at`) to the reader, or uses Zep Cloud?
- How do Letta and Hindsight (excluded for integration reasons) and supermemory score on the same suite?
- What do the suite40 results and the appendix E validation show (numbers not retrieved)?
- Which system and condition does the "Split CV and CD stuck at 8.3%" figure refer to?
- How would these paradigms translate to long structured PDLC artifacts with explicit supersedes links (B3)?

## Grading and labels
- **Directness:** high. Measures update vs preserve behaviour, our changed-requirement and stale-memory questions.
- **Control:** medium. Shared reader, typed scoring, per-episode isolation, paired tests with Bonferroni; but single runs, heterogeneous adapters and Graphiti ingestion losses.
- **Independence:** medium. Academic authors, no vendor affiliation found (affiliations not listed); author-built gold labels; GPT-5.4 generated dialogue answered by a Gemini reader (generator and reader deliberately from different families); no judge model at all (typed matching).
- **Reproducibility:** high. MIT code, data, per-system reports, bootstrap outputs, pip freeze and patches at pinned commit; rerun needs a Gemini key.
- **Applicability:** medium. Synthetic chat episodes; paradigm design transfers to PDLC.
- **Pillars:** R6 primary (memory benchmark design, statistics); R2 (supersession, update vs preserve policy) and R10 (graph-based stores Graphiti and Cognee vs note stores) secondary.
- **Stage:** evaluation.
- **Tags:** mechanism supersession, interference, misinformation-source-credibility, consolidation-strength, reconsolidation, shared-reader-protocol; workload chat-memory, incremental-ingestion, knowledge-update; cross-cutting memory-benchmark, paired-bootstrap, bonferroni, aggregate-metric-masking.
- **Beliefs supports:** none directly.
- B3 (write-time supersede edges, REALM 84.7 vs Zep 74.4): not tested in isolation; MemProbe adds that Graphiti (Zep's open-source engine) preserves previous values (96.4) but updates poorly (plasticity 58.9) in a shared-reader setup; still whole-system evidence, consistent with B3's caveat.
- B4 (read-triggered reconsolidation mechanism): not tested; "reconsolidation window" here is a benchmark paradigm, not a mechanism toggle.
- B5 (scheduled summarising consolidation on/off): not tested; the consolidation paradigm probes reinforcement strength, not summarisation.
- B8 (graph vs hybrid retrieval): mixed and not at matched tokens (Cognee 81.7 and A-MEM 88.4 above naive RAG 68.3; Graphiti 62.5 below), so no update.
- **Beliefs contradicts:** none.
- **Would create:** aggregate accuracy hides update policy (report current-value and previous-value separately); Mem0 2.0.2 lowest under this protocol, full-context beats all but A-MEM.

## Origin chain
- post 2104817738279796817 (@runbywren) -> http://arxiv.org/abs/2609.30558 -> Section 5.2 sentences ("all pairwise p>0.37"; "previous-value 96.4 vs. 67.9, 95% CI [+9.1,+48.3], p=0.002"; Bonferroni over 18) -> repo results/suite56/analysis/pairwise_probe_bootstrap.json:21, :29, :57-66 and paired_bootstrap_ci.json:1756-1885 at commit 9068d8d9.
- post 2104820679610949654 (@runbywren, reply) -> no link; same numbers, same source (cluster x:2104820679610949654 in items.jsonl, belongs to this claim).
- Independence notes: both posts are by the same handle and add no independent evidence. Dialogue surface text draws on LongMemEval and LoCoMo material (shared datasets with most chat-memory benchmarks, including those behind B3/B4). All systems share Google models (gemini-2.5-flash internal, gemini-3-flash-preview reader, gemini-embedding-001), so results are conditioned on one vendor's models; no evaluated memory vendor authored the study.
