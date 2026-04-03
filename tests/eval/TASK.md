# Autoresearch V2 -- Agent-Driven Scoring Optimization

You are a scoring optimization researcher. Your goal: **maximize the retrieval quality score** by tuning parameters and hooks. You work methodically, one change at a time, and never skip steps.

## Rules (read these FIRST, violating any rule invalidates your work)

1. **ONE change per cycle.** Never combine two untested ideas. If you want to try A and B, that is two cycles.
2. **Always start from the last ACCEPTED state.** Never build on a rejected change. Copy the exact command from the last accepted cycle.
3. **Record EVERY cycle.** No experiment without a log entry in `agent_research_log.md` -- even failures.
4. **Read history BEFORE your first cycle.** Do not propose anything already tried and rejected.
5. **Discard rejected changes completely.** If score drops, revert to last accepted. Do not "partially keep" a rejected change.
6. **Never modify `dataset.py` or `run_eval.py`.** These are read-only infrastructure.
7. **Backup before code edits.** Before touching `harness.py` or `hooks.py`, copy to `.bak`. Revert from backup if the change fails.
8. **Stop when stuck.** If 3 consecutive cycles are rejected, step back and re-read the full log. Reassess your strategy before continuing.
9. **Violation rate must stay < 0.1.** Any run with violation_rate >= 0.1 is automatically rejected regardless of nDCG.
10. **Do not hallucinate scores.** Run the actual command. Read the actual output. Report the actual numbers.

## How to Start

1. Read `tests/eval/results/agent_research_log.md` to see all prior experiments.
2. Your starting point is the last ACCEPTED cycle in that log (Cycle 8, score=0.7660 on original dataset).
3. Choose your dataset mode (see Dataset Modes below).
4. Follow "Your Loop" below. Repeat until you reach the target or exhaust ideas.

## The Metric

```
score = (1 - violation_rate) * mean_nDCG@10
```

Higher is better. Current best on original: **0.7660**. Target: **0.80+**

## Dataset Modes

The eval supports 3 dataset sizes. Use `--dataset` flag to select:

| Mode           | Flag                           | Nodes | Edges | Queries | Scenarios | Use for                                 |
| -------------- | ------------------------------ | ----- | ----- | ------- | --------- | --------------------------------------- |
| Original       | `--dataset=original` (default) | 59    | 106   | 24      | 3         | Fast iteration, regression checks       |
| Extended       | `--dataset=extended`           | 287   | 418   | 80      | 10        | Full evaluation, final scores           |
| Generated-only | `--dataset=generated-only`     | 228   | 312   | 56      | 7         | Testing generalization to new scenarios |

**Recommended workflow:**

- Iterate on `--dataset=original` (fast, ~8ms per run)
- Validate winners on `--dataset=extended` before accepting
- A change that improves original but hurts extended is suspicious -- investigate before accepting

## Quick Start

```bash
# Current best (original dataset, score=0.7660)
uv run python tests/eval/run_eval.py \
  --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 \
  --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 \
  --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 \
  --node_type_profile_bonus=1.05 \
  --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.8 \
  --hook=negative_similarity:penalty_factor=0.2 \
  --hook=edge_boost:boost_factor=0.08,top_n_seeds=6 \
  --compare-baseline

# Same config on extended dataset
uv run python tests/eval/run_eval.py \
  --dataset=extended \
  --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 \
  --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 \
  --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 \
  --node_type_profile_bonus=1.05 \
  --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.8 \
  --hook=negative_similarity:penalty_factor=0.2 \
  --hook=edge_boost:boost_factor=0.08,top_n_seeds=6 \
  --compare-baseline

# List available hooks
uv run python tests/eval/run_eval.py --list-hooks

# JSON output (for programmatic parsing)
uv run python tests/eval/run_eval.py --json --compare-baseline
```

## Your Loop

Repeat until score reaches target or you've exhausted ideas:

### Step 0: Read History (MANDATORY first step)

Read `tests/eval/results/agent_research_log.md`. Identify:

- The last ACCEPTED cycle (your starting point)
- All REJECTED changes (do not retry these)
- The weakest intents in the last accepted run

### Step 1: Reproduce the Current Best

Run the exact command from the last ACCEPTED cycle. Verify you get the same score. If the score differs, STOP and investigate -- do not proceed with a mismatched baseline.

### Step 2: Identify the Weakest Link

Look at the per-intent nDCG breakdown. The weakest intent is your optimization target. Look at the worst queries -- what do they have in common?

### Step 3: Hypothesize ONE Change

Propose a single, specific change that targets the weakest intent. Write down:

- What you're changing and why
- What intent/queries it should help
- What the risk is (could it hurt other intents?)

### Step 4: Test It

Run eval with your ONE change applied on top of the last accepted config. Use `--compare-baseline` to see the delta.

### Step 5: Accept or Reject

- **Score improved AND violation_rate < 0.1?** ACCEPT. This becomes your new baseline.
- **Score dropped OR violation_rate >= 0.1?** REJECT. Discard this change entirely. Return to Step 2 with the previous accepted config.
- **Score unchanged (delta < 0.001)?** REJECT. The change has no effect -- don't keep it.

### Step 6: Record

Append to `tests/eval/results/agent_research_log.md` using the format below. Include the EXACT command so future cycles can reproduce it.

### Step 7: Cross-Validate (for accepted changes)

If you accepted a change on `--dataset=original`, also run it on `--dataset=extended`. If the extended score drops significantly (>5%), reconsider the change -- it may be overfitting to the 3 original scenarios.

## What You Can Change

### Level 1: Parameters (safe, fast, start here)

18 numeric params via CLI flags:

| Parameter                 | Default | Range       | What it controls                               |
| ------------------------- | ------- | ----------- | ---------------------------------------------- |
| `w_relevance`             | 1.0     | [0.01, 5.0] | Weight on semantic similarity (MOST impactful) |
| `w_recency`               | 1.0     | [0.01, 5.0] | Weight on how recent                           |
| `w_importance`            | 1.0     | [0.01, 5.0] | Weight on importance score                     |
| `w_user_affinity`         | 0.5     | [0.01, 5.0] | Weight on user context                         |
| `intent_relevance_bias`   | 1.0     | [0.5, 8.0]  | Multiplier for related/what/how_does intents   |
| `intent_affinity_bias`    | 1.0     | [0.5, 8.0]  | Multiplier for who_is/personalize intents      |
| `intent_recency_bias`     | 1.0     | [0.5, 8.0]  | Multiplier for when intents                    |
| `intent_importance_bias`  | 1.0     | [0.5, 8.0]  | Multiplier for why intents                     |
| `node_type_event_bonus`   | 1.0     | [0.5, 3.0]  | Score multiplier for Event nodes               |
| `node_type_profile_bonus` | 1.0     | [0.5, 3.0]  | Score multiplier for UserProfile/Pref/Skill    |
| `s_base`                  | 168.0   | [12, 2000]  | Event decay half-life (hours)                  |
| `s_boost`                 | 24.0    | [0, 200]    | Per-access stability boost                     |
| `entity_s_base`           | 336.0   | [24, 5000]  | Entity decay half-life                         |
| `entity_s_boost`          | 24.0    | [0, 200]    | Entity per-mention boost                       |
| `degree_boost_coeff`      | 0.05    | [0, 0.3]    | Graph degree importance boost                  |
| `degree_boost_cap`        | 0.2     | [0, 0.5]    | Max degree boost                               |
| `access_boost_coeff`      | 0.05    | [0, 0.3]    | Access count importance boost                  |
| `access_boost_cap`        | 0.2     | [0, 0.5]    | Max access boost                               |

### Level 2: Structural Hooks (medium risk, high reward)

Seven pre-built scoring hooks in `tests/eval/hooks.py`. Use `--hook=NAME:key=val` to enable with inline config.

| Hook                  | What it does                                         | Best for             |
| --------------------- | ---------------------------------------------------- | -------------------- |
| `edge_boost`          | Boost graph-neighbors of top nodes using graph edges | RELATED, WHY         |
| `negative_similarity` | Penalize nodes similar to must_not_appear            | Reducing violations  |
| `scenario_focus`      | Penalize out-of-scenario nodes (prefix-based)        | Cross-scenario noise |
| `temporal_window`     | Time-focus for temporal queries                      | WHEN                 |
| `normalization`       | Z-score/min-max normalize scores                     | Score scale issues   |
| `rrf`                 | Reciprocal rank fusion of multiple signals           | Breaking plateaus    |
| `mmr_diversity`       | Reduce redundancy in top-k                           | Diverse results      |

**Current best hook chain** (order matters -- hooks run left to right):

```
scenario_focus -> negative_similarity -> edge_boost
```

### Level 3: Direct Code Changes (high risk, highest reward)

Edit files directly. **MANDATORY: backup before editing.**

```bash
cp tests/eval/harness.py tests/eval/harness.py.bak
cp tests/eval/hooks.py tests/eval/hooks.py.bak
```

If your code change breaks anything (syntax error, import error, score regression), restore immediately:

```bash
cp tests/eval/harness.py.bak tests/eval/harness.py
```

**Key extension points in harness.py**:

1. `compute_query_embedding()` (lines 571-598): How query vectors are built
2. `get_intent_weights()` (lines 98-118): Per-intent weight adjustment
3. `score_node()` / `score_entity_node()` (lines 288-436): Individual node scoring
4. `compute_composite_score()` (lines 265-285): Four-factor weighted average
5. After node scoring loop (line 639) and before ranking (line 642): Hook injection point

## Dataset Facts

- **Original**: 59 nodes, 106 edges, 24 queries, 3 PayPal scenarios (payment, fraud, merchant)
- **Extended**: 287 nodes, 418 edges, 80 queries, 10 scenarios (3 original + 7 generated fintech)
- **Generated-only**: 228 nodes, 312 edges, 56 queries, 7 LLM-generated fintech scenarios
- All datasets: 8D deterministic embeddings (SHA-256 hash), evaluation time fixed at 2h after base time
- Edge types: FOLLOWS, CAUSED_BY, REFERENCES, SIMILAR_TO
- Intent types: why, when, what, related, general, who_is, how_does, personalize
- NEVER modify `dataset.py` or `dataset_generated.json`

## Past Breakthroughs (learn from these)

| Change                                                    | Score  | Delta  | Session |
| --------------------------------------------------------- | ------ | ------ | ------- |
| Boosted w_relevance from 1.0 to 3.2                       | 0.5326 | +10%   | Cycle 1 |
| intent_relevance_bias = 4.2                               | 0.5897 | +2%    | Cycle 1 |
| edge_boost(factor=0.05) on tuned params                   | 0.6074 | +1.8%  | Cycle 1 |
| edge_boost + negative_similarity                          | 0.6205 | +1.3%  | Cycle 3 |
| scenario_focus (cross_scenario=0.45)                      | 0.7417 | +12.1% | Cycle 5 |
| Hook reorder: scenario_focus before edge_boost            | 0.7442 | +0.25% | Cycle 6 |
| Tighter scenario_focus (0.2) + stronger edge_boost (0.08) | 0.7660 | +1.4%  | Cycle 8 |

**Key insight**: scenario_focus was the single biggest unlock (+12%). Hook ordering matters. Penalizing bad nodes before boosting good ones prevents error propagation.

## Dead Ends (do NOT retry these)

| Change                                          | Result | Why it failed                                                 |
| ----------------------------------------------- | ------ | ------------------------------------------------------------- |
| relevance_exponent (power-law on cosine sim)    | -0.5%  | Over-amplifies noise in 8D embeddings                         |
| Aggressive recency discrimination (w_recency>2) | -1.2%  | Crushes older nodes that ARE relevant                         |
| node_type_event_bonus > 1.2                     | -0.3%  | Biases toward events, hurts entity recall                     |
| mmr_diversity alone (no edge_boost)             | ~0%    | Diversity without better ranking is noise                     |
| Z-score normalization before hooks              | -22%   | Destroys useful score spacing catastrophically                |
| Intent-aware edge multipliers in hooks.py       | -0.1%  | Real issue was cross-scenario contamination, not edge weights |

## Anti-Patterns (things that waste cycles)

1. **Changing multiple params at once** -- you won't know which one helped or hurt
2. **Trying normalization** -- Z-score was catastrophic (-22%). Minmax is unlikely to help either.
3. **Ignoring the log** -- if someone already tried it and it failed, don't retry unless you have a fundamentally different approach
4. **Tweaking params by tiny amounts** -- changing w_relevance from 3.2 to 3.3 is noise. Make meaningful changes or move to hooks/code.
5. **Adding hooks without understanding the current chain** -- the current chain (scenario_focus -> negative_similarity -> edge_boost) is carefully ordered. Adding a hook in the wrong position can destroy gains.
6. **Optimizing for original only** -- a change that helps 59 nodes but hurts 287 is overfitting

## Recording Your Work

After EVERY experiment, append to `tests/eval/results/agent_research_log.md`:

```markdown
## Cycle N: [ACCEPTED/REJECTED] score=X.XXXX (delta=+/-X.XXXX vs Cycle M)

**Hypothesis**: [what you thought would help and why]
**Change**: [what you changed -- one specific thing]
**Command**: [the EXACT run_eval.py command -- copy-pasteable]
**Result**: score=X.XXXX, weakest intent=[X] at Y.YYYY
**Lesson**: [what you learned for next cycle]
```

## Constraints

- `s_base > s_boost` (stability must exceed per-access boost)
- `entity_s_base >= s_base` (entities persist at least as long as events)
- All weights > 0
- Violation rate must stay < 0.1 (safety threshold)
- NEVER modify `dataset.py`, `dataset_generated.json`, or `run_eval.py`
- ONE change per cycle, no exceptions
- Every cycle gets a log entry, no exceptions

## Files Reference

| File                            | Role                   | Editable?            |
| ------------------------------- | ---------------------- | -------------------- |
| `run_eval.py`                   | CLI to run single eval | NO                   |
| `harness.py`                    | Scoring algorithm      | YES (backup first)   |
| `hooks.py`                      | 7 structural hooks     | YES (backup first)   |
| `dataset.py`                    | Original eval dataset  | NO (never touch)     |
| `dataset_generated.json`        | Generated scenarios    | NO (frozen artifact) |
| `generate_dataset.py`           | Dataset generator      | NO (already run)     |
| `test_dataset_scaling.py`       | Scaling tests          | NO                   |
| `results/agent_research_log.md` | Experiment log         | YES (append only)    |
