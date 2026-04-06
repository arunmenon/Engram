# Autoresearch for Retrieval Scoring: How We Let an AI Agent Optimize Our Ranking Algorithm

In March 2026, Andrej Karpathy released [autoresearch](https://github.com/karpathy/autoresearch): a minimal loop where an LLM agent proposes changes to a training script, measures the result, and keeps improvements. The idea is simple: give an agent one editable file, one scalar metric, and a time-boxed cycle. Let it ratchet. As Karpathy [put it](https://x.com/karpathy/status/2031137476438548874): "Any metric you care about that is reasonably efficient to evaluate can be autoresearched by an agent swarm."

The pattern spread fast. The repo passed 60k GitHub stars within weeks. [Tobi Lutke ran it overnight at Shopify](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/) and reported 37 experiments yielding a 19% performance gain. Community ports appeared for MLX, WebGPU, Jetson, and domains from trading strategies to Spring Boot services.

But nearly every implementation targets the same thing: model training. We applied the pattern to something different: a retrieval scoring algorithm with no gradient signal, where the agent discovered that 5 edge types in our knowledge graph were silently degraded to near-zero weight -- a configuration gap invisible in our original test data. Fixing it, along with other targeted changes, improved retrieval quality by 5.5% over 19 autonomous cycles.

This post covers the protocol we built, what the agent found, and why the pattern works beyond model training.

## The problem: ranking nodes in a knowledge graph

We're building Engram, a context graph for AI agents. When an agent asks "why did this payment fail?", Engram retrieves the most relevant nodes from a knowledge graph and ranks them by a composite score:

```
numerator   = w_recency * decay(age) +
              w_importance * importance(node) +
              w_relevance * cosine_sim(query, node) +
              w_user_affinity * affinity(node)

composite   = numerator / (w_recency + w_importance + w_relevance + w_user_affinity)
```

The normalization by weight sum means the weights are relative, not absolute. Doubling all four changes nothing. What matters is the ratio between them.

After base scoring, a chain of post-processing hooks adjusts the ranking: penalizing out-of-scenario noise, boosting graph neighbors of top-ranked nodes, and diversifying results.

The scoring algorithm has 18 numeric parameters, 7 optional hooks (each with their own config), and the hooks themselves are editable Python code. That is a large, mixed search space. Manual tuning got us to a reasonable baseline, but we wanted to push further.

## The evaluation benchmark

We built a deterministic benchmark to make optimization reproducible:

- **287 nodes**, **418 edges**, **80 queries** across **10 fintech scenarios**
- 3 hand-crafted scenarios + 7 LLM-generated scenarios (GPT-5.4-mini with structured output)
- 8-dimensional deterministic embeddings (SHA-256 hashed, not semantic)
- Fixed evaluation time (2 hours after base timestamp)
- 8 intent types: `why`, `when`, `what`, `related`, `general`, `who_is`, `how_does`, `personalize`

The metric:

```
score = (1 - violation_rate) * mean_nDCG@10
```

The LLM-generated scenarios were critical. Our original 3-scenario, 59-node dataset was small enough that a tuned config could overfit to it. The extended dataset (287 nodes, 80 queries) resists overfitting because the 7 generated scenarios introduce edge types, node distributions, and query patterns that the hand-crafted scenarios never covered. This turned out to be the key insight of the whole experiment.

## The protocol: TASK.md as a constitution

The core innovation is not the AI agent or the scoring algorithm. It is the protocol document that governs the agent's behavior. We call it `TASK.md`, and it functions as a constitution for autonomous optimization.

### Structure

TASK.md has five sections:

**1. Rules (10 hard constraints)**

These are inviolable. The agent reads them first.

```markdown
1. ONE change per cycle. Never combine two untested ideas.
2. Always start from the last ACCEPTED state.
3. Record EVERY cycle -- even failures.
4. Read history BEFORE your first cycle.
5. Discard rejected changes completely.
6. Never modify dataset.py or run_eval.py.
7. Backup before code edits.
8. Pivot when stuck, don't stop.
9. Violation rate must stay < 0.1.
10. Do not hallucinate scores. Run the actual command.
```

Rules 1 and 5 enforce scientific method: isolate variables, don't carry forward failed ideas. Rule 8 prevents premature stopping. Rule 10 guards against a known LLM failure mode.

**2. The optimization loop (7 steps)**

```
Read History -> Reproduce Baseline -> Identify Weakest Link ->
Hypothesize ONE Change -> Test It -> Accept/Reject -> Record
```

Each step has explicit criteria. "Identify the Weakest Link" means looking at the per-intent nDCG breakdown and targeting the worst intent. "Accept or Reject" has a clear threshold: score improved AND violation rate below 0.1, or it gets discarded.

**3. Three-level search space**

This is where the protocol diverges from standard AutoML:

| Level            | Intervention             | Risk   | Example                        |
| ---------------- | ------------------------ | ------ | ------------------------------ |
| L1: Parameters   | CLI flags                | Low    | `--w_relevance=3.5`            |
| L2: Hook config  | Enable/configure hooks   | Medium | `--hook=edge_boost:max_hops=2` |
| L3: Code changes | Edit harness.py/hooks.py | High   | Modify intent weight mapping   |

The agent starts at L1 and escalates when stuck. Three consecutive rejections at the current level triggers escalation to the next level.

**4. Dead ends table**

Previously failed approaches, with explanations of why they failed:

```markdown
| Change                  | Result | Why it failed                     |
| ----------------------- | ------ | --------------------------------- |
| Z-score normalization   | -22%   | Destroys useful score spacing     |
| relevance_exponent      | -0.5%  | Over-amplifies noise in 8D embeds |
| Aggressive recency (>2) | -1.2%  | Crushes older relevant nodes      |
```

This is institutional memory. It prevents the agent from wasting cycles rediscovering known failures.

**5. Stopping criteria (stall detection)**

No fixed target score. Instead:

- Best score hasn't improved by more than 0.003 in the last 10 cycles
- All three levels have been attempted with no improvement in the last 10 cycles
- Hard cap: 50 total cycles

This prevents both premature stopping ("I hit 0.72, that's probably good enough") and infinite loops.

## What the agent found: 19 cycles in detail

Starting score: **0.6990** (baseline from 3-scenario tuning applied to the 10-scenario extended dataset).

To put this in context: the 0.6990 baseline was itself the product of 17 prior optimization cycles across three sessions, starting from a vanilla score of 0.46. Those earlier cycles discovered the scenario_focus hook (the single biggest unlock), centroid query embeddings, entity-aware edge boosting, and intent-selective MMR diversity. So the autoresearch run described here was optimizing an already-tuned system, which makes the +5.5% gain more meaningful than it might appear.

### The accepted trajectory

7 of 19 cycles were accepted. The 12 rejections (including a catastrophic -0.4087 from replacing the MMR reranker with RRF, and six consecutive failed attempts to fix the WHO_IS intent) are documented in the full research log.

| Cycle | Change                                                | Delta   | Cumulative |
| ----- | ----------------------------------------------------- | ------- | ---------- |
| 1     | Tightened RELATED cross-scenario penalty (0.8 to 0.5) | +0.0128 | 0.7118     |
| 2     | Deeper graph traversal (max_hops=2)                   | +0.0015 | 0.7133     |
| 5     | Removed HOW_DOES from relevance amplifier             | +0.0066 | 0.7199     |
| 12    | HOW_DOES-specific REFERENCES edge multiplier          | +0.0022 | 0.7221     |
| 14    | HAS_PROFILE edge weight (0.1 to 1.5)                  | +0.0027 | 0.7248     |
| 15    | RELATED_TO edge weight (0.1 to 1.0)                   | +0.0015 | 0.7263     |
| 17    | HAS_PREFERENCE edge weight (0.1 to 1.3)               | +0.0109 | 0.7372     |

Final score: **0.7372** (+5.5%)

Wall clock time: approximately 45 minutes for all 19 cycles. Each eval run takes ~3 seconds (deterministic, no GPU needed), so the bottleneck is the agent's reasoning time between cycles, not evaluation cost. Total LLM token usage was modest -- the TASK.md protocol, research log, and a few file reads per cycle.

### Three key discoveries

**1. Noisy embeddings break conventional amplification (Cycle 5, +0.0066)**

Our benchmark uses 8-dimensional SHA-256 hashed embeddings, not semantic embeddings. They are deterministic and reproducible, but they do not carry real semantic meaning. The standard approach for `how_does` queries was to multiply the relevance weight by `intent_relevance_bias=4.2`, amplifying the semantic signal.

But with noisy embeddings, amplifying relevance amplifies noise. The agent discovered this independently by observing that `how_does` performance improved when it _removed_ the relevance amplifier. This is a non-obvious insight: the correct move was subtraction, not addition.

**2. The missing edge types (Cycles 14-17, +0.0151 combined)**

This was the biggest systematic finding. The extended dataset introduced 5 graph edge types that the original 3-scenario config never encountered: `HAS_PROFILE`, `RELATED_TO`, `HAS_PREFERENCE`, `HAS_SKILL`, and `INTERESTED_IN`. The `edge_boost` hook had a default weight configuration:

```python
@dataclass
class EdgeBoostConfig:
    edge_type_weights: dict[str, float] = field(default_factory=lambda: {
        "CAUSED_BY": 1.5,
        "FOLLOWS": 1.0,
        "REFERENCES": 1.2,
        "SIMILAR_TO": 0.8,
    })
```

Any edge type not in this dictionary fell back to `0.1`. So `HAS_PROFILE`, `HAS_PREFERENCE`, and `RELATED_TO` edges, which are structurally important for person-centric and relation-centric queries, were being treated as nearly irrelevant.

The agent fixed three of the five, with `HAS_PREFERENCE` alone contributing +0.0109, the single largest gain in the entire run. The fourth (`HAS_SKILL`) was tried and rejected because the marginal gain didn't overcome cross-intent regressions.

This is exactly the kind of bug that manual review misses: the code worked fine on the original dataset because those edge types simply did not exist there.

**3. Strategy escalation surfaces structural issues (Cycles 6-11 to 12)**

Cycles 6 through 11 were six consecutive rejections targeting the `WHO_IS` intent. The agent tried parameter changes (L1), hook configuration changes (L2), and code changes (L3), all rejected. After the full escalation, it re-read the log, noticed a pattern (graph propagation gaps rather than scoring formula issues), and pivoted to intent-specific edge multipliers. Cycle 12 was accepted.

Without strategy escalation, the agent would have stopped after three rejections at L1. The protocol forced it to exhaust the intervention space before declaring stall, and that persistence led to the structural discoveries in Cycles 14-17.

## How this extends the Karpathy pattern

Karpathy's autoresearch has three primitives: one editable file (`train.py`), one scalar metric (`val_bpb`), and a time-boxed cycle (5 minutes of GPU training). Our implementation maps cleanly but extends the pattern in several ways:

| Karpathy's Original                 | Our Extension                                                                         |
| ----------------------------------- | ------------------------------------------------------------------------------------- |
| One editable file (`train.py`)      | Three-level search space: CLI params, hook configs, and code edits to two files       |
| One scalar metric (lower is better) | Composite metric with a safety constraint (`violation_rate < 0.1` as a hard gate)     |
| Fixed time budget (5 min)           | Deterministic eval (no time budget needed, exact reproducibility)                     |
| `program.md` with instructions      | `TASK.md` with rules + loop + escalation + dead ends + stall detection                |
| Agent proposes code diffs           | Agent starts with safe parameter tweaks and escalates to code changes only when stuck |

The key structural addition is **strategy escalation**. In Karpathy's original, the agent always operates at the same level (code edits). In our system, three consecutive rejections at the current level trigger escalation to the next level. This creates a natural risk gradient: the agent starts with safe, fast parameter changes and only reaches into the codebase when the parameter space is exhausted. That is important because code changes carry revert risk and take longer to evaluate.

The other addition is **institutional dead ends**. Karpathy's `results.tsv` logs outcomes but does not carry forward "don't try this" knowledge. Our dead ends table prevents the agent from retesting Z-score normalization (which caused a catastrophic -22% regression in a prior session) or aggressive recency weighting (which kills older relevant nodes). A [benchmark by Weco AI](https://www.weco.ai/blog/autoresearch-vs-classical-hpo) found that ~22% of autoresearch improvements come from changes outside the predefined search space. Dead ends make sure the agent spends its budget on that unexplored 22%, not re-exploring known failures.

## What makes this different from AutoML

Traditional AutoML (Optuna, Ray Tune, Hyperband) optimizes a predefined numerical search space with a surrogate model or bandit algorithm. Our setup differs in several ways:

**Mixed intervention types.** The agent can change numbers, reconfigure data processing pipelines, and edit source code. These are qualitatively different operations, not just different dimensions of the same parameter vector. The structural edge weight discovery (Cycles 14-17) is a change that no predefined search space would have included.

**No gradient signal.** nDCG@10 over 80 queries is a noisy, non-differentiable metric. The agent uses hypothesis-driven reasoning, not gradient descent or Bayesian optimization. It reads the per-intent breakdown, identifies the worst-performing category, and reasons about why it is failing.

**Institutional memory.** The dead ends table and full research log prevent the agent from repeating failed experiments. In AutoML, the search algorithm implicitly avoids revisiting bad regions. Here, the constraint is explicit and human-readable, and it persists across sessions.

**Strategy escalation with stall detection.** Instead of a fixed compute budget, the agent optimizes until it genuinely cannot make progress across all three intervention levels. This is a more natural stopping condition than "run for N trials."

**Empirical comparison with blind search.** Before adopting the autoresearch protocol, we ran a blind hill-climbing search (random parameter perturbation with greedy acceptance) on the original 3-scenario dataset. It plateaued at ~52% improvement. The LLM-driven protocol reached +76% on the same dataset by discovering structural changes (the scenario_focus hook, entity-aware edge boosting) that no parameter search would find. The gap comes from the 22% of improvements that require reasoning about code, not just perturbing numbers.

## Lessons learned

**1. The protocol matters more than the agent.** The 19-cycle extended run was executed by OpenAI Codex, but the prior 17 cycles that produced the 0.6990 baseline were a mix of Claude (manual sessions) and Codex (automated). Both agents followed the same TASK.md protocol and produced comparable quality of reasoning. The specific model matters less than the structure of the protocol.

**2. LLM-generated evaluation data surfaces real gaps.** The 7 generated scenarios introduced edge types and query patterns that exposed a real configuration bug (missing edge weights). If we had only optimized on the 3 hand-crafted scenarios, we would never have found this.

**3. One change per cycle is non-negotiable.** Several rejected changes (like Cycle 8, where `node_type_profile_bonus=2.0` caused a -0.0339 regression) would have been impossible to diagnose if combined with other changes. Isolation is tedious but essential.

**4. Most cycles will be rejected, and that is fine.** 12 of 19 cycles (63%) were rejected. The accepted changes were higher quality because of the strict accept/reject discipline. A 37% hit rate with clean signal beats a higher acceptance rate with ambiguous attribution.

**5. The 0.1 default weight is a silent killer.** When your system has a fallback path for unknown inputs (in our case, unrecognized edge types defaulting to weight 0.1), expanding your evaluation data will expose those defaults as bugs. The fallback looks reasonable in isolation but tanks performance when structurally important inputs hit it.

**6. Subtraction can outperform addition.** The relevance amplifier removal (Cycle 5) was counterintuitive. The conventional approach is to boost signals, not remove boosters. With noisy embeddings, removing a signal amplifier was the correct move because it stopped amplifying noise.

## What we would do differently

**Run with real embeddings to find the ceiling.** Our benchmark uses deterministic 8D SHA-256 hashed embeddings, which puts a hard ceiling on relevance-based improvements. The +5.5% gain was achieved despite the semantic signal being essentially random noise -- which is why the biggest wins came from graph structure (edge weights), not semantic tuning. Running the same protocol with real sentence-transformer embeddings would reveal whether the relevance-weight parameters become more impactful, and whether the graph-structural discoveries still hold. This is the most important next experiment.

**Automated regression detection.** Currently, the agent manually compares per-intent scores between cycles. A built-in regression checker (flag any intent that drops more than X%) would catch cross-intent damage earlier and speed up the reject decision.

**Parallel evaluation at L1.** Parameter changes are safe and independent. Instead of testing one parameter at a time, we could run a batch of 5-10 L1 changes in parallel, accept the best, and iterate. This would compress the L1 phase significantly.

**Structured dead ends with similarity matching.** The dead ends table is a flat list. With enough entries, the agent might miss that a proposed change is similar (but not identical) to a known dead end. Embedding the dead ends and computing similarity to new proposals would improve deduplication.

**Better stopping criteria.** Our stall detection uses a fixed window (10 cycles). A more sophisticated approach would track the improvement rate curve and detect when it asymptotes, similar to early stopping in training.

## The TASK.md pattern

The reusable artifact from this work is the TASK.md protocol itself. It is applicable anywhere you have:

1. A measurable metric (retrieval quality, latency, accuracy, cost)
2. A multi-level intervention space (parameters, configuration, code)
3. A deterministic evaluation benchmark
4. An LLM agent capable of reading code and running commands

The structure is straightforward:

```
TASK.md
├── Rules (hard constraints on agent behavior)
├── The Loop (step-by-step optimization cycle)
├── Three Levels (parameter → config → code, with escalation)
├── Dead Ends (institutional memory of failures)
├── Stopping Criteria (stall detection, not fixed targets)
└── Recording Format (structured log for every cycle)
```

The key design choice is that TASK.md is a living document. Dead ends accumulate across sessions. The starting baseline advances. The agent picks up where the previous session left off, with full context about what has already been tried.

## Final numbers

| Metric                 | Before | After   | Delta                      |
| ---------------------- | ------ | ------- | -------------------------- |
| Composite score        | 0.6990 | 0.7372  | +5.5%                      |
| Violation rate         | 0.000  | 0.000   | --                         |
| Cycles run             | --     | 19      | --                         |
| Accepted               | --     | 7       | 37%                        |
| Rejected               | --     | 12      | 63%                        |
| Biggest single gain    | --     | +0.0128 | Cross-scenario penalty     |
| Biggest structural fix | --     | +0.0109 | HAS_PREFERENCE edge weight |

The composite score improved from 0.6990 to 0.7372. The improvement came from two categories: fixing cross-scenario noise (Cycles 1-2, 5) and fixing missing edge type weights (Cycles 14-17). The agent identified both categories independently through the protocol's hypothesis-test-record loop.

5.5% on a retrieval benchmark may not sound dramatic. But for a scoring algorithm that had already been manually tuned across 17 prior optimization cycles, extracting another 5.5% through automated exploration -- and having the agent independently discover a structural configuration gap in the process -- validates the autoresearch pattern for retrieval system optimization.

We plan to continue running cycles from the current Cycle 19 baseline, and to repeat the experiment with real semantic embeddings to test whether the graph-structural discoveries transfer. The TASK.md and research log are in the [Engram repository](https://github.com/arunmenon/context-graph) if you want to adapt the protocol for your own system.

The protocol is the product. The agent is replaceable. The TASK.md is not.
