# Discovery plan: hypotheses to test before building

**Date:** 2026-09-26 (H9, H10, P5 added after the evidence catalogue v2, see digest D8 addendum)
**Purpose:** turn the research pack into falsifiable experiments. Each hypothesis has a setup, a metric, a **kill criterion** (the result that ends it) and what a pass unlocks. Order follows dependency, not importance. Evidence strengths and kill thresholds draw on [paper-digests.md](paper-digests.md) D6–D8 and the [evidence bundle](evidence/memory-stack-synthesis.md).

## Ground rules (from RRSI and the bundle §6)

- **Noise floor first.** Run the unchanged stack ≥5 times on the held-out set; the score spread is the minimum gain any change must beat.
- **One attributable change per round.** Bundled changes only in an explicit exploration phase, then anneal to one.
- **Charge memory for its tokens.** Report Δscore alongside Δtokens and Δlatency; a gain that costs more than `b0 + b1·gain` tokens is rejected.
- **Experiment ledger outside memory** (`tests/eval/ledger.jsonl`): hypothesis, diff, score Δ, cost Δ, accept/reject. Failed ideas stay failed.
- **Frozen judge, held-out split.** The judge and the held-out set are never inputs to the thing being tuned (catalogue V2/V3/V8).
- **Held-out set must contain** knowledge updates, contradictions, abstention/unanswerable questions, long-hop causal chains and workflow-knowledge questions (MemTrace, MemFail, LongMemEval-V2, Ground Truth First). Today's `tests/eval` datasets contain none of these and leak labels.

## Prerequisites (week 1)

Not hypotheses; blocking defects. Without them H1–H7 cannot be measured honestly.

| # | Item | Why it blocks |
|---|---|---|
| P1 | Fix bulk-ingest payload loss, dead RediSearch prefix, double tenant prefix in retention ([scale](write-read-path-scale.md) D1–D3) | H1 cannot ingest a batch with content; BM25 channel is dead |
| P2 | Pass `tenant_id` through entity resolution (catalogue headline 6) | multi-tenant results are meaningless |
| P3 | Replace the eval harness: real embeddings, query text embedded (not gold nodes), intent from the classifier, scoring imported from `domain/scoring.py`, held-out split, frozen `evaluate()` | every downstream measurement |
| P4 | Add `task_key` (optional envelope field) and `task.outcome` / retrieval-receipt event types | H4, H6, H7 need them; additive, no frozen-contract change |
| P5 | Per-item provenance on extracted/derived nodes: `source_class` (user-stated / tool-result / inferred / imported), `recorded_at`, `reason` on Decisions and Beliefs; a `superseded` and a `stale_flag` state (additive fields) | H4 and H10 are meaningless without them; the bundle's T5 rules and jevmem's implementation (digest D8 addendum) |

## Hypotheses

### H1 — The raw ledger alone beats no-memory on software tasks
- **Claim:** verbatim event retrieval (BM25 + recency over raw payloads, no graph, no extraction) already gives a large gain on multi-session SE tasks.
- **Setup:** DreamBench-SWE (60 three-session sequences, executable oracles). Arms: no memory; ledger-only retrieval.
- **Metric:** oracle pass count /180.
- **Kill:** ledger-only < 2× no-memory (the paper reports ~4×).
- **Unlocks:** the floor every later layer must beat; the "verbatim first" story for the PDLC layer.

### H2 — The graph adds lift over flat vector at matched budget
- **Claim:** intent-weighted traversal over the projection beats a flat vector/BM25 baseline when embedder, k and token budget are held equal.
- **Setup:** MemDelta one-variable protocol on LongMemEval-S plus MemFail long-hop; arms differ only in graph traversal on/off.
- **Metric:** accuracy and token-F1 at equal retrieved-token budget.
- **Kill:** graph ≤ baseline + noise floor (the Selective-Forgetting paper lost this exact test with Engram's formula).
- **Unlocks:** whether to keep tuning traversal/decay, or reposition the graph as an index for lineage/entity/supersession questions only.

### H3 — Read-time curation beats projected summaries for `how_does` tasks
- **Claim:** a task-conditioned briefing synthesised from raw payloads (JITMem-style) beats returning Consumer 4 summaries or extracted Workflow text.
- **Setup:** same task set (τ²-bench Telecom-style multi-step procedures, or a PDLC seed set); three arms: session summary; Workflow node text; curated briefing from top-3 raw episodes.
- **Metric:** downstream task success (frozen executor), input tokens, executor steps.
- **Kill:** curated ≤ best write-time arm + noise floor, or curated tokens > 1.5× write-time arm.
- **Unlocks:** whether Consumer 4 summaries remain a read surface or become cache; the `curate` step design.

### H4 — Outcome-linked reinforcement beats access-count reinforcement
- **Claim:** boosting stability for memories that *contributed to a successful outcome* beats boosting on *being returned*.
- **Setup:** replayed task stream with `task.outcome` events; two decay policies; retrieval receipts link served memories to outcomes.
- **Metric:** downstream success over the stream; **feedback-loop rate** = fraction of wrong memories whose stability increased (the risk nobody in the bundle measures).
- **Kill:** no success gain beyond noise, or feedback-loop rate not lower than the access-count policy.
- **Unlocks:** RSI T2 plumbing; whether decay tiers are worth keeping (no system in the bundle showed measurable value from decay).

### H5 — An independent typed gate improves extraction precision without losing recall
- **Claim:** a decision model judging grounding and source type (Jev A1: Noul `quote_supports_item`, Choice `source_type`, Score `strength`) beats the extraction LLM's self-reported confidence.
- **Setup:** 90 labelled extracted items (30 obvious / 30 ambiguous / 30 no-fit); shadow-run the gate; fit thresholds on half, test on the other half.
- **Metric:** precision/recall of accepted items vs labels; calibration (reliability by probability band) — do **not** assume calibration (bundle §5).
- **Kill:** F1 not better than self-reported confidence + noise, or ECE > 0.15 on the test half.
- **Sub-question (added from jevmem):** one cheap battery vs cheap-plus-escalation when borderline. jevmem's escalation tier scored *below* the cheap tier on held-out (90.9 % vs 95.5 %); do not assume the larger battery wins.
- **Unlocks:** the Jev layer (and its egress and vendor risk); if killed, use an open decision model (GLiNER2.5-Decide) or a small NLI model instead.

### H6 — Comparative evidence produces better workflows than single-trajectory induction
- **Claim:** inducing a Workflow from the same task across several episodes plus a sibling success (MGM Φ_RM/Φ_CH) yields more general, more reusable procedures than from one success.
- **Setup:** same Episode set; two induction arms; blind generality rating (TRACE de-hardcoding rule as a checklist) and re-use success on held-out tasks with the same `task_key`.
- **Metric:** re-use success rate; instance-specific-value rate.
- **Kill:** comparative ≤ single + noise on re-use success.
- **Unlocks:** MGM-style refinement in Consumer 4; multi-parent SUPERSEDES.

### H7 — Typed supersession beats vector search on PDLC questions
- **Claim:** a small typed graph (Requirement, Decision, Constraint, Ticket, PR with SUPERSEDES/REFINES/IMPLEMENTS/VERIFIES) answers supersession, set-completeness and negation questions far better than top-k vector retrieval.
- **Setup:** seed ~300 typed records from a real project history; MOOSEDev's three question classes; arms: graph traversal vs vector top-k vs BM25.
- **Metric:** exact-answer accuracy per class.
- **Kill:** graph < 0.9 on supersession/completeness, or graph − vector < 0.3 (MOOSEDev reports 0.98–1.00 vs 0.06–0.27).
- **Unlocks:** the PDLC ontology's core claim; the write-time `supersedes`/`contradicts` design from REALM.

### H8 — A stop rule beats fixed top-k at equal quality
- **Claim:** Jev-Mem's sufficiency stop (`sufficient ≥ 0.95`, `missing < 0.15`, `contradiction < 0.15`, `continue_useful < 0.15`) returns fewer tokens at equal accuracy than `max_nodes`.
- **Setup:** H2's harness; arms: fixed k; stop rule with Engram-fit thresholds; hard caps identical.
- **Metric:** accuracy, retrieved tokens, rounds.
- **Kill:** accuracy drop > noise floor, or token saving < 20 %.
- **Unlocks:** Jev B4; unablated in the source, so this is the ablation.

### H9 — Consolidation earns its keep (on / off / trigger)
- **Claim:** Consumer 4's summaries and merges improve retrieval or knowledge-update accuracy at equal token budget, and a per-session idle + volume trigger is no worse than the fixed 6 h schedule.
- **Setup:** H2's harness plus the LongMemEval knowledge-update subset; arms: Consumer 4 off; 6 h cron; volume trigger (N new events per session, N swept); unit of consolidation is a related group (Episode), never a single write.
- **Metric:** hit@5 and knowledge-update accuracy; served tokens; number of Summary nodes read at query time.
- **Kill:** any consolidation arm ≤ off + noise floor (Hippo measured −3.6 pp; no source in the bundle reports a positive number). If killed, summaries become cache for read-time curation (H3), not a read surface.
- **Unlocks:** whether Consumer 4 keeps its scheduler or becomes event-driven; whether SUMMARIZES nodes are retrievable.

### H10 — Provenance-gated serving: staleness audit and injection gate
- **Claim:** (a) a batched "still true given the current snapshot?" Noul over live Decisions/Beliefs flags stale items with high precision without deleting anything; (b) an injection gate over unverified extracted items before they are served blocks planted instructions with near-zero false blocks; (c) with both on, H4's feedback-loop rate falls.
- **Setup:** seed a project history with ~50 Decisions whose underlying file/dependency later changes and ~50 that stay valid; plant ~40 instruction-bearing lines among extracted memories; snapshot = repo tree, manifest fields, README head (jevmem recipe). Run the audit as a Consumer 4 job; run the gate in the `/v1/context` serving path in shadow mode first.
- **Metric:** stale-flag precision/recall at the flag threshold (fit on half, test on half); injection block rate and false-block rate (jevmem: 20/22 blocked, 0/22 false on 44 lines); added serving latency; H4 feedback-loop rate with and without.
- **Kill:** stale-flag precision < 0.8 at recall ≥ 0.7; injection false-block rate > 2 %; or serving latency +> 150 ms p95 for the gate. Flags never delete: a killed audit costs nothing but a field.
- **Unlocks:** Jev A6 and B5; the PDLC layer's "invalidate when the underlying artefact changes" rule; the provenance counterweight that makes H4's reinforcement safe to ship.

## Sequencing

| Week | Work | Depends on |
|---|---|---|
| 1 | P1–P4 | — |
| 2 | H1, H2 (shared benchmark setup); noise floor established | P1–P3 |
| 3 | H3, H5 (both need receipts and the gate port) | P4 |
| 4 | H8 alongside H2's harness; H4 on the replayed stream | H2, P4 |
| 4 | H9 on H2's harness (three arms, cheap once H2 exists) | H2, P3 |
| 5 | H10 alongside H4 (same replayed stream; provenance fields from P5) | P5, H4 |
| 5+ | H6, H7 | H4 (outcomes), P4 |

H1–H3 decide the architecture story; H4–H5 and H10 decide the loop, the decision layer and whether the loop is safe; H6–H9 decide what goes into Consumer 4 and the PDLC layer. Stop and rewrite the plan after H2: if the graph shows no lift, H6/H7 change shape (index, not traversal).

## Governance checks that run throughout

- Tag every memory write that originates in a blocked/denied episode.
- Track guardrail-trigger rate across rounds; a falling rate is a warning until explained.
- Keep one evaluation check that never feeds memory writes (stays at RSI level L2 on purpose).
- Log every weight change on read with the query that caused it.
