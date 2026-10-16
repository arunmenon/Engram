---
schema_version: 1
artifact_id: N-20260928-23
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:08:43Z
input_refs: [{"artifact_id": "post:2104583094078525629", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.25054
claim_cluster: arxiv:2609.25054
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.25054
source_commit: v1
strength: paper-ablated
pillar_primary: R2
pillar_secondary: ["R10", "R1"]
memory_stage: linking
priority: 3
tags: {"mechanism": ["typed provenance graph", "supersedes edge", "revoke tombstone", "contest/resolve", "soft key identity", "current-value materialization", "provenance pruning"], "workload": ["chat memory", "synthetic revision chains", "fact consolidation"], "lifecycle_stage": ["write", "linking", "retrieval"], "cross_cutting": ["cost", "provenance"]}
evidence_grade: {"directness": "medium: directly tests write-time supersession and retention vs overwrite, but on LongMemEval, synthetic ALFWorld-Revision chains and MemoryAgentBench, not engineering artifacts", "control": "high: retention on/off ablation, soft-identity and pruning-gate ablations, reader/writer scale ablations, paired bootstrap and McNemar on LongMemEval; ALFWorld chains have no CIs", "independence": "medium: NUS authors evaluating their own system; 4B agent both writes and answers; LongMemEval judge is a larger Qwen model from the same family, gold-aware; the other two benchmarks use string match", "reproducibility": "low: no code or data URL found in the paper as read; seeds and models stated", "applicability": "medium: keyed current-value questions resemble changed requirements and superseded decisions; paper admits free-form phrasing fragments extraction and only arrival-ordered revisions are tested"}
beliefs_affected: {"supports": ["B3", "B1", "B8", "B20"], "contradicts": [], "would_create": ["Retaining displaced values plus an explicit revoke/reopen operation is what makes a committed wrong update recoverable; overwrite and invalidate-without-reopen both recover 0%"]}
claim_correction: The "100% vs 0% committed-error recovery against CRUD memory" compares P-Mem with retention against its own retention-off ablation and Graphiti/Zep (a bitemporal graph, not CRUD) on a synthetic chain task (n=140); Mem0, the CRUD baseline, is described only as "rare recoveries" with no number, and a plain archival raw store recovers 97.9% (adjacent) and 92.0% (d=32).
---

# MoM: Memory of Memory (P-Mem, Provenant Memory) (arXiv 2609.25054)

- **URL:** https://arxiv.org/abs/2609.25054 (full text read at https://arxiv.org/html/2609.25054)
- **Type:** paper
- **Author / org:** Bowen Qin, Yao Lu (corresponding), National University of Singapore. License CC BY 4.0. No code URL found.
- **Date:** v1 submitted 2026-09-07
- **Retrieved:** 2026-09-28, arXiv v1 (abstract page and HTML full text; Appendix G "Limitations" text was not returned by the fetch)
- **Cited by evidence:** https://x.com/RubberDucky_AI/status/2104583094078525629 (@RubberDucky_AI, 2026-09-28, feed memory, listed as a "near-miss" in a weekly roundup)
- **Relevance to a memory stack:** high. A concrete, typed write-time design for "what currently holds" (supersedes, alternative-of, revokes, supported-by) with ablations isolating retention, which is exactly our supersession design question (B3, A5) and a candidate node/edge vocabulary for the PDLC context graph.

## TL;DR
- P-Mem stores evidence, version, operation and tombstone nodes, linked by `supported-by`, `supersedes`, `alternative-of` and `revokes`. At write time a frozen annotator (the 4B model, temperature 0) picks one of six typed operations (accept, contest, reject, revoke, resolve, noop); "nothing admitted is deleted, only retyped or relinked". The read path materialises the "active frontier": one current value per resolved key, with provenance on demand.
- On synthetic revision chains (ALFWorld-Revision, n=140 per length), commit-at-write stays at 100% current-value accuracy at chain length 8, while raw top-10 retrieval falls to 25.0% (64.3% with order tags, 94.3% with oracle order).
- Committed-error recovery (section 4.2.2, n=140): P-Mem with retention 100% at d=0 and d=32; retention off 0%; Graphiti/Zep 0% ("no operation reopens it"); raw archival store 97.9% / 92.0%; Mem0 "rare recoveries" from accidentally retained copies. **Claim correction:** the post's "100% vs 0% against CRUD memory" is really retention vs no retention (and vs Zep); the CRUD system (Mem0) has no reported number, and plain append-only storage nearly matches.
- LongMemEval-s knowledge-update subset (n=78): P-Mem turn read 69.2% vs MemoryOS 60.3% (paired bootstrap +6.8 pp, CI [+2.4, +11.2], p=0.001); vs HippoRAG-v2 +1.8 pp, n.s. Pruning cuts stale answers to 10.9% (MemoryOS 19.4%) but costs 3.8 points of accuracy (65.4%) on the full haystack. "~4x fewer read tokens": ~3k vs ~11k context tokens vs MemoryOS.
- Relevant to B3: the first source in our catalogue that ablates part of the write-time supersession design (retention, soft identity, pruning gate) rather than comparing whole systems.

## What it claims / describes
**Thesis.** "The memory question is not what was once recorded but what currently holds" (abstract). MoM commits current values at write time while retaining displaced entries.

**Data model (section 3.2).**
- Evidence nodes: raw observations with source, type, timestamp.
- Version nodes: (key, value) pairs with status and validity interval. Statuses include active, contested, superseded, contradicted.
- Operation nodes: applied updates with timestamps.
- Tombstone nodes: mark revocations.
- Edges: `supported-by` (version to evidence), `supersedes` (version to the predecessor it replaces), `alternative-of` (version competing with a sibling), `revokes` (tombstone to retracted version).

**Key resolution.** "Soft key identity, an embedding match confirmed by a light check" (section 1): candidates with cosine >= 0.72 are shortlisted and a one-word verification on attribute names merges duplicates.

**Write-time operations (Table 2).**
| op | effect |
|---|---|
| accept | new value becomes head; incumbent retyped superseded |
| contest | fact attaches as alternative; head becomes contested |
| reject | new value becomes head; incumbent retyped contradicted |
| revoke | head retracted via tombstone; predecessor reopens |
| resolve | contested alternative promoted; others contradicted |
| noop | adds support edge, increments count |

Who decides: "A frozen annotator selects one typed operation relating it to the key's head, schema-constrained and validated by deterministic post-processing (contest needs an active incumbent, resolve a contested cell; a failing annotation falls back to noop)." The annotator is the 4B model; the prompt text was not returned by our fetch.

**Read path (section 3.4).** "Deterministic materialization with disclosure modes": current value first; provenance traversed on demand in modes {support, alternatives, history}. On LongMemEval, P-Mem uses turn-level retrieval plus graph-guided pruning; on the other benchmarks a materialised-cell read.

**Setup.** Agent Qwen3-4B-Instruct-2507 (temperature 0); embedder Qwen3-Embedding-4B. Benchmarks: LongMemEval (500 questions, 78 knowledge-update; oracle haystack about 2 sessions, LongMemEval-s about 48 sessions), judged by Qwen3.6-35B-A3B-FP8 (gold-aware yes/no plus stale classification); ALFWorld-Revision (140 valid-seen games, chain lengths 1, 2, 4, 8 with interleaved distractors; string match); MemoryAgentBench FactConsolidation (6k/64k/262k, 100 single-hop + 100 multi-hop per length, 55 to 63% of keys overwritten; substring match). Baselines: long-context, MemoryOS (top-5 chunks), Mem0 v1.0.1 (add/update/delete), HippoRAG-v2, Graphiti/Zep (bitemporal KG), raw facts, raw facts with order tags. Chain construction seed 42.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| KU accuracy / stale, LongMemEval-s | P-Mem turn read 69.2% / 23.6%; + prune 65.4% / 10.9% | MemoryOS 60.3% / 19.4% | Table 3, n=78 | pruning trades 3.8 pts accuracy for stale rate; unpruned P-Mem stale is higher than MemoryOS |
| KU accuracy / stale, oracle haystack | P-Mem 75.6% / 19.6%; + prune 76.9% / 5.4% | MemoryOS 66.7% / 22.6% | Table 3, n=78 | |
| Paired difference vs MemoryOS | +6.8 pp, 95% CI [+2.4, +11.2], p=0.001 | | n=78 | |
| vs HippoRAG-v2 | +1.8 pp, CI [-2.8, +6.4], n.s. | | n=78 | |
| LongMemEval-s all 500 | P-Mem 52.6% overall, 62.7% superseded, 29.3% aggregation, 56.8% single | HippoRAG-v2 50.8 / 58.7 / 33.7 / 53.8 | Table 4 | P-Mem loses on aggregation |
| Read tokens | ~3k, 52.6%, 17.5 acc per 1k tokens | MemoryOS ~11k, 45.8%, 4.2 | Table 5 | "~4x fewer read tokens" |
| Current-value accuracy at chain length 1/2/4/8 | commit 100/100/100/100% | raw top-10 100/72.9/42.9/25.0; raw + recon. 100/94.3/59.3/40.0; raw + [t=i] 100/97.9/80.0/64.3; oracle order 100/100/98.6/94.3 | Table 6, ALFWorld-Revision, n=140 per L | synthetic, no CIs |
| Committed-error recovery | P-Mem with retention 100% (d=0 and d=32) | retention off 0%; Graphiti/Zep 0%; raw archival 97.9% (d=0), 92.0% (d=32); Mem0 "rare recoveries" | section 4.2.2, n=140 | Mem0 number not stated |
| Contest / resolve | contest surfaces conflict 100%; post-resolution 97.9% | raw 96.4% notices, 57.1% post-resolution; Graphiti 50.0% / 39.3% | section 4.2.3, n=140, counterbalanced | |
| FactConsolidation single-hop 6k/64k/262k | P-Mem state read 95/95/88%; + iterative 96/94/87% | raw + order tags 94/94/90; HippoRAG-v2 69/47/39; Mem0 36/45/30; Graphiti/Zep (35B extractor) 77/86/- | Table 7, n=100 per cell | binomial CI about +/-10 pts; raw + order tags nearly equal |
| FactConsolidation multi-hop | P-Mem + iterative 53/37/29% | raw facts 17/12/9; HippoRAG-v2 11/3/6 | Table 7 | |
| Stale rate 6k/64k/262k | P-Mem state read 4.7/5.8/4.2% | Mem0 43.8/46.4/59.2%; raw + order tags 6.3/5.8/5.6% | Table 7, n=64 to 71 chains | |
| Soft identity ablation | 307 cells, stale 4.7%, multi-hop 53% | without: 346 cells for 239 keys, stale 9.4%, multi-hop 42% | Appendix F, 6k | |
| Pruning gate | class-oracle gate stale 12.9%; 35B question-only router stale 17.7%, overall 51.8% (-0.8 pp) | ungated 27.4% | Appendix C, n=78 | |
| Writer scale on LongMemEval | 35B extractor 61.5% / stale 20.4% | 4B 52.6% / 33.3% | Appendix D, n=78 | merge threshold 0.85 -> 0.70: stale 20.4 -> 13.0%, accuracy -3.8 pp |
| Reader scale | commit stays 100% on chains with any reader | flat store single-hop 71 -> 94% with 35B reader | Appendix F | |

Text vs table: Table 3's caption and row label use "++"/"prune" inconsistently; section 4.1 clarifies it is "turn read + provenance prune". The abstract's "19.4% to 10.9%" compares MemoryOS to pruned P-Mem, not P-Mem before and after pruning (23.6% -> 10.9%).

## Mechanism details you could implement
- **Six typed write operations** (table above) with deterministic validity checks and `noop` as the fallback on any failed annotation. Map to our PDLC graph (inference): a changed requirement is `accept` (old retyped superseded), a disputed decision is `contest`, a reverted change is `revoke` (predecessor reopens), a signed-off choice among alternatives is `resolve`.
- **Never delete; retype.** Displaced versions keep their `supported-by` evidence, so the chain is auditable and reversible. The ablation shows retention is the thing that makes rollback possible.
- **Revoke must reopen the predecessor.** Graphiti/Zep kept the old value as an invalidated edge but recovered 0% because no operation reopens it. A bitemporal store needs an explicit reopen path.
- **Soft key identity**: cosine >= 0.72 shortlist plus a one-word check on attribute names; halved stale rate (9.4% -> 4.7%) and cut cells from 346 to 307.
- **Materialised current-value read**: serve one current value per key first; expose provenance modes (support, alternatives, history) only on demand. About 3k tokens vs about 11k for chunk retrieval.
- **Pruning with a gate**: pruning superseded material reduces stale answers but can drop needed context; a question-type router recovered about two thirds of the oracle gain at -0.8 pp overall.

## Limitations, caveats, counter-evidence
- Scope stated in section 4: "Updates arrive in order and currency follows last-write-wins, so we evaluate precisely currency under arrival-ordered revisions, not the broader valid-time setting: delayed or backdated reports, out-of-order ingestion, conflicting source authority, which the typed operations can express but which we leave to future work." (dash in the original replaced by a colon here.)
- Appendix D: on natural histories extraction fragments; "all cells hold a single fact" on keyed streams, coverage degrades on free-form phrasing. Multi-hop ceiling near the template oracle (31 to 39%).
- Appendix G (Limitations) was not returned by our fetch; not read.
- A plain raw store with order tags nearly matches P-Mem on single-hop FactConsolidation (94/94/90 vs 95/95/88) and stale rate; the typed graph's advantage is concentrated in multi-hop, revision chains and reversibility.
- Pruning reduced accuracy on the full LongMemEval-s haystack (69.2 -> 65.4).
- Small models (4B writer and reader) throughout; with a 35B extractor Graphiti/Zep improves a lot (FactConsolidation single-hop 77/86%), so some baseline gaps are extractor-size effects (inference).
- No code release found; the synthetic chain tasks are author-built.
- No instruction-bearing content found in the paper or the post. The post itself opens with a promotional line ("@Muse did this task in 30 seconds..."); it is a roundup, likely machine-generated (inference), with no instructions to agents.

## Takeaways for tuning a memory stack
- Supersede by retyping, never delete, and give `revoke` a reopen semantics; test recovery after a wrong update explicitly.
- Commit current values at write time for keyed facts (requirement status, chosen design, owner); raw retrieval collapses as revisions accumulate (25% at 8 revisions with top-10).
- Keep provenance (`supported-by`) on every version so a reviewer can see why a value is current (B1).
- Compare against a cheap baseline first: raw facts with order tags got close on single-hop; the typed graph earns its cost on chains, multi-hop, contests and rollback.
- If you prune superseded material at read time, gate it by question type, and measure accuracy as well as stale rate.

## Open questions
- How does the 4B annotator perform on free-form engineering text (PR descriptions, design docs) rather than keyed facts?
- What is Mem0's actual recovery rate? Not stated.
- Out-of-order or conflicting-authority updates (common in PDLC: a late review comment overriding a newer decision) are not tested.
- Would a Jev-style typed decision model pick the operation as well as the 4B annotator, at what cost? Not tested (priority 1 and 3 overlap).

## Grading and labels
- **Directness: medium.** Tests write-time supersession and retention directly, but on chat and synthetic keyed tasks.
- **Control: high.** Several ablations isolating retention, soft identity, pruning, reader and writer scale; paired bootstrap and McNemar on LongMemEval.
- **Independence: medium.** Authors evaluate their own system; the LongMemEval judge is a larger model of the same Qwen family, gold-aware.
- **Reproducibility: low.** No code or data URL found.
- **Applicability: medium.** Keyed current-value tracking maps to PDLC state; free-form extraction is the weak point.
- **Pillars:** R2 primary (supersession and retention semantics); R10 (typed node and edge vocabulary for the context graph); R1 (retained versions with provenance make decisions reproducible).
- **Stage:** linking.
- **Priority:** 3 (typed provenance links and node types for a context graph; supersedes/revokes are candidate PDLC trace-link semantics).
- **Beliefs affected:**
  - Supports B3: write-time commit with supersede edges holds 100% on revision chains where raw retrieval falls to 25%, and +6.8 pp over MemoryOS on the LongMemEval KU subset; partial isolation of the edges' contribution, which B3 says was unmeasured. Candidate to move B3 from lead toward working.
  - Supports B1: retaining displaced versions with evidence links is what makes recovery possible (100% vs 0% retention off).
  - Supports B8 (second clause): typed structure wins on supersession-type questions; single-hop ties with raw + order tags.
  - Supports B20: the post's comparison needed narrowing.
  - Would create: retention plus a reopen operation is necessary for recovering from committed wrong updates.
- **Against the synthesis:** consistent with section 1 (REALM "prefer add over modify; never merge a state change") and section 4b ("supersede rather than delete"). Adds a caution the synthesis lacks: Graphiti/Zep's invalidated edges are not reversible without a reopen operation. No contradiction row.
- **Arm-vs-arm test this quarter (frozen harness):** on a PDLC fixture with injected wrong updates and later retractions, arm A overwrite (CRUD) vs arm B append-only with timestamps vs arm C supersede-with-retention plus revoke-reopens; metric: current-value accuracy after k revisions and recovery rate after retraction at d=0 and d=32 events.

## Origin chain
- Post 2104583094078525629 (@RubberDucky_AI, 2 likes, 69 views, roundup of 7 papers; this paper listed as a near-miss) -> arXiv 2609.25054 v1 -> Table 2 (operations), section 3.2 (data model), Table 3 (KU), Table 5 (tokens), Table 6 (chains), section 4.2.2 (recovery), Table 7 (FactConsolidation), Appendices C, D, F (ablations).
- Independence: one post, one paper, two NUS authors; baselines are third-party systems (Mem0 v1.0.1, Graphiti/Zep, HippoRAG-v2, MemoryOS). Shares the Qwen3-Embedding-4B embedder with VibeMemBench (arXiv 2609.23570) but no authors or harness.
