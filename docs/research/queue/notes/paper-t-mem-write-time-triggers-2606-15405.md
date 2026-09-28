---
schema_version: 1
artifact_id: N-20260928-06
artifact_type: note
producer: triage
run_id: triage-20260928T014503Z-edff
created_at: 2026-09-28T01:55:04Z
input_refs: [{"artifact_id": "post:2104172198537855432", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2606.15405
claim_cluster: arxiv:2606.15405
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2606.15405
source_commit: dd9e1527bc75908485809580c9520af5a9a42879
strength: paper-ablated
pillar_primary: R3
pillar_secondary: ["R2", "R6"]
tags: {"mechanism": ["write-time triggers", "anticipatory indexing", "multi-view encoding", "RRF", "hierarchical retrieval"], "workload": ["conversational memory", "LoCoMo", "LoCoMo-Plus"], "lifecycle_stage": ["write-time enrichment", "read-time retrieval"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: LLM-judge accuracy on LoCoMo and LoCoMo-Plus with per-component ablations", "control": "medium: 8 ablations (Table 4) and many baselines, but baseline numbers largely from other papers and the LoCoMo judge shares a model family with answer generation", "independence": "medium: Tencent and HKUST(GZ); LoCoMo-Plus Cognitive subset is the only associative benchmark, so one lab's reading of it", "reproducibility": "medium: code released (Sherlockwz/T-Mem HEAD dd9e152), prompts in Appendix B; LoCoMo three runs, LoCoMo-Plus single evaluation", "applicability": "low-medium: chat memory with associative cues; our workload is engineering artifacts, and write cost is about 1.56M tokens per conversation"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Write-time LLM-generated anticipatory cues (triggers) make memories reachable from queries with no surface overlap; removing the associative triggers drops LoCoMo-Plus from 74.81 to 52.62 while barely moving LoCoMo (<0.4 points)"]}
claim_correction: The post summarises T-Mem as "index memories at write time for the future cues that will need them", which matches; it omits that the lift is concentrated on LoCoMo-Plus associative queries (LoCoMo overall 80.26 vs HyperMem 77.01) and that trigger construction costs 15.60M GPT-4.1-mini tokens for 10 conversations.
---

# T-Mem: Memory That Anticipates, Not Archives (arXiv 2606.15405)

- **URL:** https://arxiv.org/abs/2606.15405 (HTML https://arxiv.org/html/2606.15405); code https://github.com/Sherlockwz/T-Mem
- **Type:** paper + repo
- **Author / org:** Weidong Guo, Dakai Wang, Zixuan Wang, Hui Liu, Yu Xu (Tencent; The Hong Kong University of Science and Technology (Guangzhou))
- **Date:** v1 2026-06-13; v2 2026-09-08
- **Retrieved:** 2026-09-28, arXiv abstract and HTML; repo HEAD `dd9e1527bc75908485809580c9520af5a9a42879` (2026-09-09, "Replace Key Results table with LoCoMo gap chart in README") via GitHub API; repo not cloned
- **Cited by evidence:** @rajeevchhajer, https://x.com/rajeevchhajer/status/2104172198537855432 ("T-Mem: index memories at write time for the future cues that will need them")
- **Relevance to a memory stack:** medium. A concrete write-time enrichment mechanism with a clean ablation showing where it helps (associative queries) and where it does not (ordinary LoCoMo). Relevant to our "decide structure, not admission" write path.

## TL;DR
- Problem: retrieval is "reachability-bounded by the similarity between a query and stored content". Queries tied to a memory only by a latent arc ("associative") are missed.
- At write time an LLM (GPT-4.1-mini) generates four trigger families: for items, Entity ("Names the item with a superordinate concept") and Bridge ("Projects the item onto a situation in which knowing this item would matter", with a "<cue> -> <inference>" rationale); for scenes, Scene (situation, object, event, emotion) and Horizon (forward-looking dimensions).
- Retrieval: topic pre-filter (RRF over BM25 + dense), scene selection with multi-view encoding, item selection with trigger-aware indices ("nan-aware max across views"); triggers bypass the topic pre-filter above a hard cosine gate of 0.85.
- LoCoMo (LLM-judge accuracy): 80.26 vs best baseline HyperMem 77.01. LoCoMo-Plus: 74.81 vs HyperMem 48.63, GPT-4o zero-shot 21.05.
- Ablation (Table 4): "w/o ST + HT" drops LoCoMo-Plus 74.81 to 52.62 (-22.19) with under 0.4 points change on LoCoMo. Write cost: 9,689 calls, 15.60M tokens for 10 conversations (Mem0 12.20M).

## What it claims / describes
Episodic future thinking as an engineering pattern: at write time, rehearse each memory against the future contexts where it will be needed, and index those rehearsals (triggers) alongside the content. Two granularities (single facts and full exchanges), each with a descriptive and an associative trigger family, "so that every memory remains reachable from both surface-similar and relevance-bound queries".

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| LoCoMo overall (LLM judge) | 80.26 | HyperMem 77.01 (also Mem0, Zep, Memobase, MemU, Supermemory, MIRIX, MemOS) | 1,540 questions, 10 conversations, 3 runs | judge GPT-4o-mini shared with answer generation |
| LoCoMo single-hop / multi-hop / temporal / open-domain | 85.97 / 69.15 / 82.55 / 55.21 | | same | |
| LoCoMo token F1 | 51.96 | | same | |
| LoCoMo-Plus | 74.81 | HyperMem 48.63; GPT-4o 21.05 | Cognitive subset, single evaluation | judge Gemini-2.5-Flash, generator GPT-4o |
| LoCoMo to LoCoMo-Plus gap | 5.45 points | HyperMem 28.38; GPT-4o 45.09 | | |
| ablation w/o associative (ST + HT) | LoCoMo-Plus 52.62 (-22.19); LoCoMo < 0.4 change | full T-Mem | Table 4 | |
| ablations of descriptive components | 1.43 to 4.74 on LoCoMo; 0.25 to 2.99 on LoCoMo-Plus | | Table 4 | |
| construction model swap | -4.81 points with Qwen3-32B | GPT-4.1-mini | sensitivity | |
| write cost | 9,689 calls; 15.60M tokens for 10 conversations | Mem0 12.20M | | about 1.56M tokens per conversation |
| answer-time budget | "At a token budget below HyperMem's" higher accuracy on both | HyperMem | | exact tokens not in extract |

## Mechanism details you could implement
- For each stored item, one joint LLM call produces (a) a superordinate-concept label and (b) one or more "situation where this would matter" cues with a one-clause "<cue> -> <inference>" rationale. Index cues in their own vector/BM25 views; at query time take the max over views; allow a strong cue match (cosine >= 0.85) to bypass coarse topic filtering.
- For engineering memory, the analogue would be "when would a future task need this decision?" cues written at capture time (e.g. "when changing the storage engine", "when a flaky test appears in module X") (inference).
- Keep the cue generation deterministic enough to replay: store the cue text with the memory and the model version (inference, R1).

## Limitations, caveats, counter-evidence
- Authors: "The writing pipeline relies on a memory-construction LLM strong enough to follow structured-output instructions reliably ... Memory is built offline ... LoCoMo-Plus's Cognitive subset is to our knowledge the only public benchmark that directly probes the associative axis."
- The associative gain rests on a single benchmark subset evaluated once; the LoCoMo gain over HyperMem is 3.25 points with a judge that shares a model with generation.
- Write cost is higher than Mem0 and scales with memories written.
- Baseline numbers are partly taken from other papers (inference from the list of baselines; not verified per row).

## Takeaways for tuning a memory stack
- If our queries are often associative (a new task that needs an old decision without sharing words), write-time cues are a cheap-to-test addition to hybrid retrieval; if queries share identifiers and file paths, expect little gain (the LoCoMo result).
- Measure on a query set split into descriptive vs associative before adopting.

## Open questions
- Does trigger indexing help on engineering artifacts, where identifiers dominate?
- Replay: triggers are LLM output written at capture time; are they versioned?

## Grading and labels
- Directness high; control medium; independence medium; reproducibility medium; applicability low-medium.
- Pillars: R3 primary (reachability at read time), R2 secondary (what is written at capture), R6 secondary (single associative benchmark, shared judge). Tags: cost.
- Beliefs: would create a belief on write-time anticipatory cues for associative recall. Nothing contradicts B7 or B8: this is not graph traversal, and it is not task-conditioned read-time curation.

## Origin chain
post 2104172198537855432 (@rajeevchhajer) -> arXiv 2606.15405 abstract and HTML -> results tables, Table 4 ablations, efficiency section -> repo HEAD via GitHub API -> this note. Independence: no shared authors with other items in the same post.
