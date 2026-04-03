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

Higher is better. Current best on extended: **0.6990**. Target: **0.75+**

## Dataset

**IMPORTANT: Use `--dataset=extended` for ALL eval runs.** This is mandatory.

The extended dataset has 287 nodes, 418 edges, 80 queries across 10 fintech scenarios (3 original + 7 LLM-generated). This is the primary benchmark. All scores in this document and in the research log refer to extended dataset runs.

| Mode           | Flag                       | Nodes   | Queries | Scenarios | Use for                               |
| -------------- | -------------------------- | ------- | ------- | --------- | ------------------------------------- |
| **Extended**   | **`--dataset=extended`**   | **287** | **80**  | **10**    | **ALL runs -- this is the benchmark** |
| Original       | `--dataset=original`       | 59      | 24      | 3         | Do NOT use -- leads to overfitting    |
| Generated-only | `--dataset=generated-only` | 228     | 56      | 7         | Optional -- test generalization only  |

## Quick Start

```bash
# Current best (extended dataset, score=0.6990)
uv run python tests/eval/run_eval.py \
  --dataset=extended \
  --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 \
  --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 \
  --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 \
  --node_type_profile_bonus=1.05 \
  --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.8 \
  --hook=negative_similarity:penalty_factor=0.2 \
  --hook=edge_boost:boost_factor=0.08,top_n_seeds=6 \
  --hook=mmr_diversity \
  --compare-baseline

# List available hooks
uv run python tests/eval/run_eval.py --list-hooks

# JSON output (for programmatic parsing)
uv run python tests/eval/run_eval.py --dataset=extended --json --compare-baseline
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

### Step 7: Sanity Check (optional)

If a change produces a surprisingly large gain (>3%), also run it on `--dataset=generated-only` to confirm it generalizes to the 7 new scenarios and isn't just lifting the 3 original ones.

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

These were discovered on the original dataset and verified on extended. Extended scores shown.

| Change                                         | Extended Score | Session         |
| ---------------------------------------------- | -------------- | --------------- |
| Tuned params + edge_boost                      | ~0.43          | Original C1     |
| scenario_focus hook                            | ~0.60          | Original C5     |
| Entity-aware edge_boost (skip Event neighbors) | 0.6719         | Original C11    |
| 2-hop traversal + same-scenario entity boost   | 0.6796         | Original C13-14 |
| MMR diversity (skip `what` intent)             | **0.6990**     | Original C15-17 |

**Key insights from prior optimization:**

- scenario_focus was the single biggest unlock. Hook ordering matters -- penalize before boosting.
- Entity-centric intents (who_is, related, personalize) need different edge_boost behavior than event-centric intents.
- MMR diversity helps RELATED but hurts WHAT -- intent-selective application is key.
- Current hook chain: `scenario_focus -> negative_similarity -> edge_boost -> mmr_diversity`

**Where the remaining gap is (extended dataset, score=0.6990):**

- RELATED=0.5577, HOW_DOES=0.6364, WHO_IS=0.6441 are the weakest intents
- Worst queries are in generated scenarios: lu-how-does-01 (0.13), cr-why-01 (0.20), ar-how_does-01 (0.32)
- The params and hooks were tuned for 3 original scenarios -- the 7 new scenarios likely need retuning

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
6. **Using `--dataset=original`** -- the 59-node dataset is for sanity checks only, not optimization. Always use `--dataset=extended`

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
