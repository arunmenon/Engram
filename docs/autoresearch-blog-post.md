# How an AI Agent Found a Hidden Gap in Our Retrieval Scoring System

We used an AI agent to optimize a retrieval scoring algorithm for a knowledge graph. Over 19 autonomous cycles it improved ranking quality by 5.5% -- but the more interesting result was what it discovered along the way: five graph edge types in our system were silently degraded to near-zero weight because our original test data never exercised them. That structural gap was invisible to us. The agent found it by following a protocol we call TASK.md.

This post describes the protocol, the discoveries, and why the [autoresearch pattern](https://github.com/karpathy/autoresearch) -- Andrej Karpathy's minimal loop for autonomous optimization -- works for retrieval systems, not just model training.

## The system: ranking nodes in a knowledge graph

We're building Engram, a context graph for AI agents. When an agent asks "why did this payment fail?", Engram retrieves relevant nodes and ranks them:

```
numerator   = w_recency * decay(age) +
              w_importance * importance(node) +
              w_relevance * cosine_sim(query, node) +
              w_user_affinity * affinity(node)

composite   = numerator / (w_recency + w_importance + w_relevance + w_user_affinity)
```

The normalization by weight sum means the weights are relative, not absolute. Doubling all four changes nothing.

After base scoring, a chain of post-processing hooks adjusts the ranking: penalizing cross-scenario noise, boosting graph neighbors of top-ranked nodes, and diversifying results. The scoring algorithm has 18 numeric parameters, 7 optional hooks (each with their own config), and the hooks themselves are editable Python code.

## The benchmark

We built a deterministic evaluation setup:

- **287 nodes**, **418 edges**, **80 queries** across **10 fintech scenarios**
- 3 hand-crafted scenarios + 7 LLM-generated scenarios (GPT-5.4-mini with Pydantic structured output, human-reviewed for node diversity and edge coverage)
- 8 intent types: `why`, `when`, `what`, `related`, `general`, `who_is`, `how_does`, `personalize`

**An important caveat**: the embeddings are 8-dimensional SHA-256 hashes, not real semantic embeddings. This was deliberate -- it makes evaluation perfectly reproducible and cheap (~3 seconds per full run, no GPU needed), but it means cosine similarity carries no real semantic signal. What you gain in reproducibility, you lose in the relevance dimension. This constraint shaped the entire experiment: the biggest wins came from graph structure, not semantic tuning.

The metric: `score = (1 - violation_rate) * mean_nDCG@10`

The violation rate acts as a hard safety gate. Any run with violation rate above 0.1 is automatically rejected regardless of how much nDCG improved. In practice, no accepted run tripped the gate, but it constrained the search: several rejected changes (like replacing the MMR reranker with RRF) would have introduced violations if the gate were absent.

**Why the LLM-generated scenarios mattered**: our original 3-scenario, 59-node dataset was small enough for configs to overfit to it. The 7 generated scenarios introduced new edge types (`HAS_PROFILE`, `HAS_PREFERENCE`, `RELATED_TO`) and query patterns that the hand-crafted data never covered. This turned out to be the most consequential design decision in the whole experiment.

## The protocol: TASK.md

The core contribution is the protocol document, not the AI agent. TASK.md is a self-contained instruction sheet that any LLM agent can follow. It has five parts:

**10 rules** that constrain agent behavior: one change per cycle, always revert to last accepted state, record every experiment, never modify the evaluation harness, backup before code edits.

**A 7-step optimization loop**:

```
Read History -> Reproduce Baseline -> Identify Weakest Intent ->
Hypothesize ONE Change -> Test It -> Accept/Reject -> Record
```

**A three-level search space** with escalation:

| Level            | Intervention           | Risk   | Escalation trigger       |
| ---------------- | ---------------------- | ------ | ------------------------ |
| L1: Parameters   | CLI flags              | Low    | 3 consecutive rejections |
| L2: Hook config  | Enable/configure hooks | Medium | 3 consecutive rejections |
| L3: Code changes | Edit scoring code      | High   | 3 consecutive rejections |

**A dead ends table** listing previously failed approaches with explanations (institutional memory that persists across sessions).

**Stall-detection stopping criteria**: no fixed target score. The agent optimizes until the best score hasn't improved by more than 0.003 across 10 cycles at all three levels. Hard cap: 50 cycles.

## What the agent discovered

The 0.6990 starting score was already the product of 17 prior optimization cycles across three sessions (starting from 0.46), including both manual Claude sessions and automated Codex runs. So this was optimization on top of an already-tuned system.

### The accepted trajectory

7 of 19 cycles were accepted. 12 were rejected, including a catastrophic -0.4087 from replacing the MMR reranker, and six consecutive failed attempts to fix the WHO_IS intent.

| Cycle | Change                                                | Delta   | Score  |
| ----- | ----------------------------------------------------- | ------- | ------ |
| 1     | Tightened RELATED cross-scenario penalty (0.8 to 0.5) | +0.0128 | 0.7118 |
| 2     | Deeper graph traversal (max_hops=2)                   | +0.0015 | 0.7133 |
| 5     | Removed HOW_DOES from relevance amplifier             | +0.0066 | 0.7199 |
| 12    | HOW_DOES-specific REFERENCES edge multiplier          | +0.0022 | 0.7221 |
| 14    | HAS_PROFILE edge weight (0.1 to 1.5)                  | +0.0027 | 0.7248 |
| 15    | RELATED_TO edge weight (0.1 to 1.0)                   | +0.0015 | 0.7263 |
| 17    | HAS_PREFERENCE edge weight (0.1 to 1.3)               | +0.0109 | 0.7372 |

Total wall clock time: approximately 45 minutes for all 19 cycles. Each eval run takes ~3 seconds (no GPU), so the bottleneck is agent reasoning time. Estimated API cost: under $5 for the full run.

### Discovery 1: Amplifying noise hurts more than helping

The standard approach for `how_does` queries was to multiply the relevance weight by 4.2x. But with hashed embeddings, there is no real semantic signal to amplify. The agent discovered that removing the multiplier improved HOW_DOES from 0.6309 to 0.6839 (Cycle 5). The correct move was subtraction, not addition.

### Discovery 2: The missing edge types

This was the most important finding. The `edge_boost` hook had default weights for four edge types:

```python
edge_type_weights = {
    "CAUSED_BY": 1.5,
    "FOLLOWS": 1.0,
    "REFERENCES": 1.2,
    "SIMILAR_TO": 0.8,
}
```

Any unrecognized edge type fell back to `0.1`. The extended dataset introduced `HAS_PROFILE`, `RELATED_TO`, `HAS_PREFERENCE`, `HAS_SKILL`, and `DERIVED_FROM`. All five were treated as nearly irrelevant.

The agent fixed three of them across Cycles 14-17, with `HAS_PREFERENCE` alone contributing +0.0109 -- the single largest gain in the run.

Here is a concrete example. The query `at-personalize-01` asks:

> "Given Jordan's profile, which preferences and skills most influenced the response to this takeover?"

The expected top results include `pref-at-01`, `pref-at-02`, `skill-at-01`, `skill-at-02` -- all connected via `HAS_PREFERENCE` and `HAS_SKILL` edges. Before the fix, these preference and skill nodes were buried because the edge boost treating their connections as 0.1 weight meant graph propagation barely reached them. After adding `HAS_PREFERENCE: 1.3`, the preference node `pref-at-01` entered the top 10 and the query's nDCG improved from 0.32 to 0.41.

The code worked fine on the original dataset because those edge types did not exist there.

### Discovery 3: Strategy escalation prevents premature stopping

Cycles 6 through 11 were six consecutive rejections targeting WHO_IS. The agent tried parameter changes, hook configs, and code edits. All failed. Without the escalation protocol, it would have stopped. Instead, it re-read the full log, noticed the pattern was graph propagation gaps (not scoring formula issues), and pivoted to edge type weights. Cycles 14-17 followed.

## How this differs from AutoML and standard autoresearch

Karpathy's autoresearch has three primitives: one editable file, one scalar metric, one time-boxed cycle. Our setup extends the pattern in ways that matter for retrieval systems:

**Three-level search space with risk escalation.** Karpathy's agent always operates at the same level (code edits). Ours starts with safe parameter tweaks and only reaches into the codebase when parameters are exhausted. This controls blast radius while preserving the unbounded search space at L3.

**Institutional dead ends.** Karpathy's `results.tsv` logs outcomes but does not carry forward "don't try this" knowledge. Our dead ends table prevents retesting Z-score normalization (-22% regression) or aggressive recency weighting. Early benchmarks comparing autoresearch to classical HPO suggest that a significant fraction of gains come from changes outside the predefined search space -- architectural modifications that no parameter grid would include. Dead ends help the agent spend its budget on that unexplored territory.

**No gradient signal.** nDCG@10 over 80 queries is noisy and non-differentiable. The agent reasons about per-intent breakdowns, identifies the worst category, and hypothesizes targeted fixes. Traditional AutoML (Optuna, Ray Tune) cannot reason about _why_ a configuration is failing -- it can only explore _what_ to try next.

**Mixed intervention types.** The structural edge weight discovery (Cycles 14-17) is a change that no predefined parameter search space would have included. It required the agent to inspect the dataset's edge types, compare them against the hook's default config, and recognize the gap.

## Lessons learned

**The protocol matters more than the agent.** The 19-cycle run used OpenAI Codex; the prior 17 cycles used a mix of Claude and Codex. Both followed the same TASK.md and produced comparable reasoning quality.

**LLM-generated evaluation data surfaces real gaps.** If we had only optimized on the 3 hand-crafted scenarios, the missing edge types would never have been found.

**One change per cycle is non-negotiable.** Cycle 8 caused a -0.0339 regression from `node_type_profile_bonus=2.0`. Combined with another change, that would have been undiagnosable.

**Most cycles will be rejected.** 63% rejection rate. The accepted changes were higher quality because of strict accept/reject discipline.

**Default fallbacks are silent killers.** When your system has a fallback for unknown inputs (edge types defaulting to 0.1), expanding evaluation data will expose those defaults as bugs.

## What we would do differently

**Run with real embeddings.** The 8D hashed embeddings put a hard ceiling on relevance-based improvements. The +5.5% gain was achieved despite the semantic signal being random noise. Running the same protocol with sentence-transformer embeddings would reveal whether relevance-weight parameters become more impactful, and whether the graph-structural discoveries still hold.

**Parallel evaluation at L1.** Parameter changes are safe and independent. Running 5-10 L1 changes in parallel and accepting the best would compress the parameter phase significantly.

**Automated regression detection.** A built-in checker that flags any intent dropping more than X% would speed up reject decisions and catch cross-intent damage earlier.

## What makes this reproducible

Five properties made the loop deterministic:

1. **Fixed evaluation time** (2h after base timestamp, no wall-clock dependency)
2. **Deterministic embeddings** (SHA-256 hash, same input always produces same vector)
3. **Frozen dataset** (read-only, never modified during optimization)
4. **Exact command logging** (every cycle records the full copy-pasteable command)
5. **Single-change discipline** (one variable per cycle, clean attribution)

Any agent that can read files and run shell commands can reproduce this. The TASK.md protocol is the reusable artifact.

## Final numbers

| Metric              | Before | After   | Delta                      |
| ------------------- | ------ | ------- | -------------------------- |
| Composite score     | 0.6990 | 0.7372  | +5.5%                      |
| Violation rate      | 0.000  | 0.000   | --                         |
| Cycles run          | --     | 19      | --                         |
| Accepted            | --     | 7       | 37%                        |
| Biggest single gain | --     | +0.0109 | HAS_PREFERENCE edge weight |

The improvement came from two categories: fixing cross-scenario noise (Cycles 1-2, 5) and fixing missing edge type weights (Cycles 14-17). The agent identified both independently through the protocol's hypothesis-test-record loop.

We plan to continue running cycles from the current baseline and to repeat the experiment with real semantic embeddings. The TASK.md and research log are in the [Engram repository](https://github.com/arunmenon/context-graph) for anyone who wants to adapt the protocol.

The protocol is the product. The agent is replaceable. The TASK.md is not.
