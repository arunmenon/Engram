---
schema_version: 1
artifact_id: N-20260928-30
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:08:43Z
input_refs: [{"artifact_id": "post:2104583094078525629", "file_id": null, "sha256": null}, {"artifact_id": "post:2104588113343357345", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.23315
claim_cluster: arxiv:2609.23315
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.23315
source_commit: v1
strength: vendor-benchmark
pillar_primary: R10
pillar_secondary: ["R6"]
memory_stage: retrieval
tags: {"mechanism": ["graph database engine", "bulk ingest", "point update", "multi-hop query", "total cost of ownership"], "workload": ["synthetic biomedical knowledge graph"], "lifecycle_stage": ["ingestion", "retrieval", "linking"], "cross_cutting": ["cost", "vendor conflict of interest"]}
evidence_grade: {"directness": "low: measures database latency and throughput on a static synthetic graph; no LLM, agent or memory workload is run", "control": "low: one harness on shared hardware, geometric means over 20 query shapes, no engine versions, hardware, repetitions or variance stated", "independence": "low: three of four authors are from Corvic AI, the subject system; conflict disclosed", "reproducibility": "low: no code, data generator or URL found", "applicability": "low: one synthetic dataset shape at 1.02M nodes; our graph workload (incremental agent writes, typed PDLC links) not represented"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": []}
claim_correction: @omarsar0's "7 graph DB engines ... for agent workloads" is wrong on both counts: the paper compares Corvic AI against seven other engines (FalkorDB and PuppyGraph partly or fully excluded, 7 engines in Table 1), and no LLM agent or agent-memory workload is run; the benchmark is a vendor (Corvic AI) evaluation on one synthetic biomedical graph.
---

# Graph Memory for LLM Agents: At What Cost? A Comparative Evaluation of Query, Ingest, and Update Performance Across Graph Database Engines (arXiv 2609.23315)

- **URL:** https://arxiv.org/abs/2609.23315 (full text read at https://arxiv.org/html/2609.23315)
- **Type:** paper (vendor-authored)
- **Author / org:** Donald Nguyen, Gurbinder Gill, Hadi Ahmadi (Corvic AI Research); Christopher J. Rossbach (UT Austin)
- **Date:** v1 submitted 2026-09-20; cs.DB, cs.AI
- **Retrieved:** 2026-09-28, arXiv v1 (abstract and HTML full text). No code or data URL found.
- **Cited by evidence:** https://x.com/RubberDucky_AI/status/2104583094078525629 (@RubberDucky_AI, "near-miss" in a roundup); https://x.com/omarsar0/status/2104588113343357345 (@omarsar0, roundup item 4). Both feed memory, 2026-09-28.
- **Relevance to a memory stack:** low. Storage-engine numbers only; useful as a sanity table if we pick a graph store for the context graph, not as evidence that graph memory helps agents.

## TL;DR
- 8 engines (Corvic AI, LoraDB, Ladybug, DuckPGQ, Memgraph, Neo4j, HugeGraph, FalkorDB; FalkorDB and PuppyGraph partly or fully excluded) on one synthetic biomedical graph (1.02 million nodes, 5.34 million node and edge rows), 20 query shapes, bulk ingest, point update and batch update.
- Abstract: "no system in this sample is categorically fastest". Bulk ingest spans 5.0k to 4.3M rows/s (860x), and ingest dominates total cost for workloads with fewer than roughly 10^5 queries per data refresh.
- Corvic AI (the authors' product) leads geometric-mean latency at 1.02M nodes (2.19 ms) and ingest (4.3M rows/s); it is not fastest on point updates (2.47 ms vs Memgraph 0.90, Ladybug 0.96).
- **Claim correction:** despite the title and the posts, no LLM or agent is run and there is no agent-memory workload (no incremental agent writes, no retrieval quality). Vendor benchmark with disclosed conflict.

## What it claims / describes
Graph databases for connected-data workloads that back LLM systems' "ontology" management. Queries: "one-hop and multi-hop neighborhood lookups, bounded-length path queries (chain_paths), set intersections, anti-joins (existence-negated lookups), grouped counting aggregations, top-k ranked retrieval (top_k_ordered), temporal range filters, unfiltered scans, and star/chain relational joins." Static pre-loaded graphs; latency reported as geometric mean over the 20 shapes at 1K, 10K and 1.02M nodes; correctness as queries answered correctly out of 20. A total-cost model gives a crossover in operations per refresh between engines. "All timings were collected under one measurement harness on shared hardware; we did not vary hardware configuration, concurrency level, or client-driver overhead."

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| GM latency @1K / @10K / @1.02M, Corvic AI | 1.16 / 1.04 / 2.19 ms, 20/20 correct | | Table 1, 20 query shapes | authors' product |
| LoraDB | 0.59 / 0.64 / 2.60 ms, 18/20 | | Table 1 | ingest 5,000 rows/s; point update 247.00 ms |
| Ladybug | 1.65 / 1.56 / 4.08 ms, 20/20 | | Table 1 | point update 0.96 ms |
| DuckPGQ | 1.37 / 1.56 / 4.18 ms, 20/20 | | Table 1 | batch 16,700,000 rows/s (highest) |
| Memgraph | 0.69 / 0.96 / 4.77 ms, 20/20 | | Table 1 | point update 0.90 ms (fastest) |
| Neo4j | 2.35 / 2.64 / 6.92 ms, 20/20 | | Table 1 | ingest 53,000 rows/s; point update 7.23 ms |
| HugeGraph | 15.98 / 19.76 / 61.81 ms, 19/20 | | Table 1 | batch DNF |
| Bulk ingest | Corvic 4,300,000; DuckPGQ 3,500,000; Ladybug 476,000; Memgraph 87,000; HugeGraph 64,000; Neo4j 53,000; LoraDB 5,000 rows/s | | Table 1 | 860x spread |
| TCO crossover | "q* ~ 38,304 point-update operations" (Corvic AI vs Memgraph) | | cost model | "fewer than roughly 10^5 queries per data refresh" |
| Hardware, versions, repetitions, variance | not stated | | | |

## Mechanism details you could implement
- For a context graph that is rebuilt or bulk-refreshed often and queried rarely, pick by ingest throughput; for one that is updated incrementally by agents (our case, inference), point-update latency matters more (Memgraph 0.90 ms, Ladybug 0.96 ms, Corvic 2.47 ms, Neo4j 7.23 ms, LoraDB 247 ms).
- Query-shape list above is a reasonable checklist for a context-graph read benchmark (multi-hop, anti-join, temporal range, top-k ordered).

## Limitations, caveats, counter-evidence
- Verbatim (limitations): "Eight engines and one synthetic dataset shape is not a comprehensive survey of the graph database market... our graph is generated, not drawn from a production biomedical corpus... FalkorDB and PuppyGraph results are partially or fully excluded... we did not vary hardware configuration, concurrency level, or client-driver overhead."
- Conflict of interest (section 7): "Corvic AI is both the subject system and the authors' own product; we have tried to offset this conflict of interest through full disclosure of the one workload where our system does not lead and by publishing the underlying comparison table."
- No engine versions, hardware or repetition counts; no code or data. No LLM-agent measurement despite the title.
- No instruction-bearing content found in the paper or posts.

## Takeaways for tuning a memory stack
- Treat this as vendor marketing with a usable table; it says nothing about whether graph memory improves agent outcomes (B8 unaffected).
- If we benchmark stores for the PDLC context graph, measure incremental point updates and typed-edge traversal on our own schema, not bulk ingest.

## Open questions
- Engine versions and hardware? Not stated.
- Behaviour under concurrent agent writes? Not tested.

## Grading and labels
- **Directness: low.** No agent or memory workload.
- **Control: low.** One harness, no variance.
- **Independence: low.** Vendor-authored.
- **Reproducibility: low.** No artifacts.
- **Applicability: low.** Synthetic static graph.
- **Pillars:** R10 primary (storage for the context graph); R6 (vendor benchmark integrity).
- **Stage:** retrieval.
- **Priority:** none claimed. The paper frames graph DBs as ontology storage, which touches priority 3's term "ontology" only in framing; the content is engine performance.
- **Beliefs affected:**
  - Supports B20: the posts described it as an agent-workload study; it is not.
  - B8 (graph traversal vs hybrid retrieval at matched tokens): not addressed.
  - Would create: none.
- **Against the synthesis:** nothing in the synthesis on storage engines; no contradiction.
- **Arm-vs-arm test this quarter (frozen harness):** no; at most a store micro-benchmark on our own schema, which is not an arm-vs-arm memory test.

## Origin chain
- Post 2104583094078525629 (@RubberDucky_AI) and post 2104588113343357345 (@omarsar0) -> arXiv 2609.23315 v1 -> Table 1 (per-engine results), TCO section, section 7 (conflict), limitations.
- Independence: both posts are search roundups with no added data. Three of four authors are from Corvic AI, the leading system in the paper.
