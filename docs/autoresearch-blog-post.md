# How an AI Agent Found a Hidden Gap in Our Retrieval Scoring System

We used an AI agent to optimize a retrieval scoring algorithm for a knowledge graph. Over 19 autonomous cycles it improved ranking quality by 5.5% -- but the more interesting result was what it discovered along the way: five graph edge types in our system were falling through to a low default weight because our original test data never exercised them. That structural gap was invisible to us. The agent found it by following a protocol we call TASK.md.

This post describes the protocol, the discoveries, and what this experiment suggests about using agentic optimization loops -- inspired by Andrej Karpathy's [autoresearch pattern](https://github.com/karpathy/autoresearch) -- for retrieval scoring.

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

**An important caveat**: the node vectors are 8-dimensional SHA-256 hashes, not learned semantic embeddings. This was deliberate -- it makes evaluation perfectly reproducible and cheap (~3 seconds per full run, no GPU needed), but it means cosine similarity carries no real semantic signal. What you gain in reproducibility, you lose in the relevance dimension. This constraint shaped the entire experiment: the biggest wins came from graph structure, not semantic tuning.

The metric: `score = (1 - violation_rate) * mean_nDCG@10`

The violation rate acts as a hard safety gate. Any run with violation rate above 0.1 is automatically rejected regardless of how much nDCG improved. In practice, no accepted run tripped the gate, but it constrained the search: several rejected changes (like replacing the MMR reranker with RRF) would have introduced violations if the gate were absent.

**Why the LLM-generated scenarios mattered**: our original 3-scenario, 59-node dataset was small enough for configs to overfit to it. The 7 generated scenarios introduced new edge types (`HAS_PROFILE`, `HAS_PREFERENCE`, `RELATED_TO`) and query patterns that the hand-crafted data never covered. We used them to broaden structural coverage, not to replace human judgment on what "good retrieval" means -- the relevance grades and expected rankings were still reviewed manually. This turned out to be the most consequential design decision in the experiment.

## The protocol: TASK.md

The reusable contribution here is the protocol document, not any specific model. TASK.md is a self-contained instruction sheet that any LLM agent can follow. It has five parts:

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

The standard approach for `how_does` queries was to multiply the relevance weight by 4.2x. But with hash-based vectors, there is no real semantic signal to amplify. The agent discovered that removing the multiplier improved HOW_DOES from 0.6309 to 0.6839 (Cycle 5). The correct move was subtraction, not addition.

### Discovery 2: The missing edge types

![Scoring pipeline diagram showing the 0.1 fallback gap in edge_boost](autoresearch-scoring-pipeline.svg)

This was the most important finding. The `edge_boost` hook had default weights for four edge types:

```python
edge_type_weights = {
    "CAUSED_BY": 1.5,
    "FOLLOWS": 1.0,
    "REFERENCES": 1.2,
    "SIMILAR_TO": 0.8,
}
```

Any unrecognized edge type fell back to `0.1`. The extended dataset introduced `HAS_PROFILE`, `RELATED_TO`, `HAS_PREFERENCE`, `HAS_SKILL`, and `DERIVED_FROM`. All five were falling through to the 0.1 fallback.

The agent fixed three of them across Cycles 14-17, with `HAS_PREFERENCE` alone contributing +0.0109 -- the single largest gain in the run.

Here is a concrete example. The query `at-personalize-01` asks:

> "Given Jordan's profile, which preferences and skills most influenced the response to this takeover?"

The expected top results include `pref-at-01`, `pref-at-02`, `skill-at-01`, `skill-at-02` -- all connected via `HAS_PREFERENCE` and `HAS_SKILL` edges. Before the fix, these preference and skill nodes were buried because the edge boost treating their connections as 0.1 weight meant graph propagation barely reached them. After adding `HAS_PREFERENCE: 1.3`, the preference node `pref-at-01` entered the top 10 and the query's nDCG improved from 0.32 to 0.41.

The code worked fine on the original dataset because those edge types did not exist there.

### Discovery 3: Strategy escalation prevents premature stopping

Cycles 6 through 11 were six consecutive rejections targeting WHO_IS. The agent tried parameter changes, hook configs, and code edits. All failed. Without the escalation protocol, it would have stopped. Instead, it re-read the full log, noticed the pattern was graph propagation gaps (not scoring formula issues), and pivoted to edge type weights. Cycles 14-17 followed.

## How this differs from AutoML and standard autoresearch

Karpathy's autoresearch has three primitives: one editable file, one scalar metric, one time-boxed cycle. Our setup extends the pattern in ways that matter for retrieval systems:

**Three-level search space with risk escalation.** Karpathy's agent always operates at the same level (code edits). Ours starts with safe parameter tweaks and only reaches into the codebase when parameters are exhausted. Dead ends from prior sessions prevent retesting known failures like Z-score normalization (-22% regression).

**No gradient signal, but hypothesis-driven reasoning.** nDCG@10 over 80 queries is noisy and non-differentiable. The agent reads per-intent breakdowns and forms hypotheses about why a category is failing. Traditional AutoML tools can search parameter spaces efficiently, but they do not inspect artifacts or reason about root causes.

**Mixed intervention types.** The edge weight discovery (Cycles 14-17) required inspecting the dataset's edge types, comparing them against the hook's default config, and recognizing the gap. No predefined parameter search space would have included that change.

## Lessons learned

**The same protocol worked across agents.** The 19-cycle run used OpenAI Codex; the prior 17 cycles used a mix of Claude and Codex. In both cases, the same TASK.md structure produced comparable reasoning quality.

**One change per cycle is non-negotiable.** Cycle 8 caused a -0.0339 regression from `node_type_profile_bonus=2.0`. Combined with another change, that would have been undiagnosable.

**Most cycles will be rejected.** 63% rejection rate. The strict accept/reject discipline meant each accepted change had clean attribution.

## What we would do differently

**Run with real embeddings.** The 8D hash vectors put a hard ceiling on relevance-based improvements. The +5.5% gain was achieved despite the semantic signal being random noise. Running the same protocol with sentence-transformer embeddings would reveal whether relevance-weight parameters become more impactful, and whether the graph-structural discoveries still hold.

**Parallel evaluation at L1.** Parameter changes are safe and independent. Running 5-10 L1 changes in parallel and accepting the best would compress the parameter phase significantly.

**Automated regression detection.** A built-in checker that flags any intent dropping more than X% would speed up reject decisions and catch cross-intent damage earlier.

## What makes this reproducible

Five properties made the loop deterministic:

1. **Fixed evaluation time** (2h after base timestamp, no wall-clock dependency)
2. **Deterministic hash vectors** (SHA-256, same input always produces same vector)
3. **Frozen dataset** (read-only, never modified during optimization)
4. **Exact command logging** (every cycle records the full copy-pasteable command)
5. **Single-change discipline** (one variable per cycle, clean attribution)

Any sufficiently capable agent that can read files, run shell commands, and follow the protocol should be able to reproduce this setup.

## Final numbers

| Metric              | Before | After   | Delta                      |
| ------------------- | ------ | ------- | -------------------------- |
| Composite score     | 0.6990 | 0.7372  | +5.5%                      |
| Violation rate      | 0.000  | 0.000   | --                         |
| Cycles run          | --     | 19      | --                         |
| Accepted            | --     | 7       | 37%                        |
| Biggest single gain | --     | +0.0109 | HAS_PREFERENCE edge weight |

The gains came from two categories: fixing cross-scenario noise (Cycles 1-2, 5) and fixing missing edge type weights (Cycles 14-17). The agent identified both independently through the protocol's hypothesis-test-record loop. We plan to continue from the current baseline and repeat the experiment with real semantic embeddings. The TASK.md and research log are in the [Engram repository](https://github.com/arunmenon/context-graph).

The durable artifact from this work is the protocol. The value is in the procedure, not the model.
