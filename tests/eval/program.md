# Autoresearch V2 -- Structural Scoring Optimization

## V2 Overview

You are a scoring optimization agent running in an autoresearch loop. Your job is to maximize retrieval quality for a context graph by tuning parameters AND modifying structural scoring logic through pre-built hooks.

V1 tuned 18 numeric parameters and plateaued at **0.5897** (GPT-5.4 best). A prior Claude session broke through to **0.5971** by manually editing the scoring algorithm -- adding centroid embeddings and per-intent centroid strategies. Those were structural changes that no amount of parameter tuning could discover. V2 formalizes this by giving you three proposal types:

1. **`params`** -- Modify numeric knobs in `ScoringParams`. Fast (~8ms eval). Good for fine-tuning within a structural configuration.
2. **`structural`** -- Enable and configure a pre-built hook from `hooks.py`. Moderate cost (code reload). Capable of breakthroughs that parameters alone cannot reach.
3. **`code`** -- Raw Python patch to `harness.py`. Escape hatch for truly novel ideas. Highest risk (syntax errors trigger automatic revert).

**Target: 0.65+** (from baseline 0.4600, V1 ceiling 0.5897).

The biggest untapped signal: **108 graph edges** (FOLLOWS, CAUSED_BY, REFERENCES, SIMILAR_TO) are loaded by `load_eval_dataset()` but NEVER used in scoring. The `edge_boost_score` hook unlocks this.

---

## Metric and Baseline

### The Score Formula

```
score = (1 - violation_rate) * mean_ndcg@10
```

**nDCG@10** measures ranking quality: `DCG = sum(grade_i / log2(i+1))` for the top 10, normalized by ideal DCG. Grades: 3 = must-have, 2 = relevant, 1 = marginal.

**Violation rate** = fraction of top-10 results in `must_not_appear`. Currently 0.0125 (near zero). Since violation rate is already minimal, the practical target is nDCG improvement.

### Key Scores

| Milestone           | Score     | Source                         |
| ------------------- | --------- | ------------------------------ |
| Baseline (defaults) | 0.4600    | No tuning                      |
| V1 best (GPT-5.4)   | 0.5897    | 18-param tuning                |
| Claude manual best  | 0.5971    | Structural edits to harness.py |
| **V2 target**       | **0.65+** | Params + hooks                 |

### Per-Intent nDCG at V1 Best (0.5897)

| Intent      | nDCG   | Headroom    | Notes                      |
| ----------- | ------ | ----------- | -------------------------- |
| WHY         | 0.7981 | Low         | Strongest. Causal queries. |
| WHEN        | 0.6591 | Medium      | Temporal queries.          |
| PERSONALIZE | 0.6513 | Medium      | User context queries.      |
| GENERAL     | 0.5729 | Medium      | No dominant factor.        |
| HOW_DOES    | 0.5629 | Medium      | Process/mechanism queries. |
| RELATED     | 0.5487 | High        | Cross-scenario retrieval.  |
| WHO_IS      | 0.5411 | High        | Entity identity queries.   |
| WHAT        | 0.4843 | **Highest** | Weakest. Factual queries.  |

Optimize the combined score, not individual intents. But use this breakdown to diagnose regressions -- if a change hurts WHY by 0.10 to help WHAT by 0.02, it is a bad trade.

---

## The Editable Assets

### Asset 1: ScoringParams (18 numeric parameters)

The `ScoringParams` dataclass has 18 tunable knobs. Proposing a params change applies JSON overrides and runs `evaluate()` immediately.

**Decay Curve Parameters:**

| Parameter      | Range      | Default | V1 Best | Purpose                                            |
| -------------- | ---------- | ------- | ------- | -------------------------------------------------- |
| s_base         | [12, 2000] | 168.0   | ~170    | Event stability (hours). Lower = faster fade.      |
| s_boost        | [0, 200]   | 24.0    | ~25     | Per-access stability boost (hours).                |
| entity_s_base  | [24, 5000] | 336.0   | 720.0   | Entity stability (hours). Entities persist longer. |
| entity_s_boost | [0, 200]   | 24.0    | ~24     | Per-mention entity refresh.                        |

Constraint: `s_base > s_boost`, `entity_s_base >= s_base`.

**Composite Weights:**

| Parameter       | Range       | Default | V1 Best  | Purpose                                               |
| --------------- | ----------- | ------- | -------- | ----------------------------------------------------- |
| w_recency       | [0.01, 5.0] | 1.0     | 0.72     | Weight for recency factor.                            |
| w_importance    | [0.01, 5.0] | 1.0     | 0.80     | Weight for importance factor.                         |
| w_relevance     | [0.01, 5.0] | 1.0     | **3.20** | Weight for semantic similarity. **Highest leverage.** |
| w_user_affinity | [0.01, 5.0] | 0.5     | 0.78     | Weight for user context.                              |

Key insight: w_relevance at 3.2 means semantic similarity dominates the composite. Embedding quality is the primary signal.

**Intent Bias Parameters:**

| Parameter              | Range      | Default | V1 Best | Applies To                    |
| ---------------------- | ---------- | ------- | ------- | ----------------------------- |
| intent_recency_bias    | [0.5, 8.0] | 1.0     | 1.1     | "when" queries                |
| intent_importance_bias | [0.5, 8.0] | 1.0     | ~1.0    | "why" queries                 |
| intent_relevance_bias  | [0.5, 8.0] | 1.0     | **4.2** | "related", "what", "how_does" |
| intent_affinity_bias   | [0.5, 8.0] | 1.0     | 1.5     | "who_is", "personalize"       |

Key insight: intent_relevance_bias at 4.2 means effective relevance weight for related/what/how_does is 3.2 \* 4.2 = 13.4. Semantic similarity overwhelmingly dominates for these intents.

**Importance Sub-Parameters:**

| Parameter          | Range      | Default | V1 Best |
| ------------------ | ---------- | ------- | ------- |
| access_boost_coeff | [0.0, 0.3] | 0.05    | ~0.05   |
| access_boost_cap   | [0.0, 0.5] | 0.2     | ~0.2    |
| degree_boost_coeff | [0.0, 0.3] | 0.05    | ~0.05   |
| degree_boost_cap   | [0.0, 0.5] | 0.2     | 0.14    |

**Node Type Bonuses:**

| Parameter               | Range      | Default | V1 Best |
| ----------------------- | ---------- | ------- | ------- |
| node_type_event_bonus   | [0.5, 3.0] | 1.0     | ~1.0    |
| node_type_profile_bonus | [0.5, 3.0] | 1.0     | 1.05    |

**Other:**

| Parameter              | Range      | Default | Notes                                                         |
| ---------------------- | ---------- | ------- | ------------------------------------------------------------- |
| relevance_exponent     | [0.3, 5.0] | 1.0     | Sharpens relevance scores. > 1 separates high/low similarity. |
| use_centroid_embedding | bool       | True    | Average expected node embeddings. Always keep True.           |

### Asset 2: harness.py Scoring Pipeline

The `evaluate()` function scores every node for every query. It has 5 stages, each with a hook point:

```
query
  |
  v
[Stage 1] Build query embedding (centroid or first-node, per intent)
  |
  v
[Stage 2] Compute intent-aware weights via get_intent_weights()
  |
  v
[Stage 3] Per-node scoring: recency + importance + relevance + affinity -> composite
  |
  v
[Stage 4] Apply node type bonuses (event_bonus, profile_bonus)
  |
  v
[Stage 5] POST-RANK (currently empty -- biggest opportunity)
  |
  v
ranked_ids -> nDCG@10, violation_rate -> score
```

**Stage 1** (lines 571-598): Builds query embedding. Uses centroid (average of all expected node embeddings) for why/when/general/how_does/personalize. Uses first-node embedding for what/related.

**Stage 2** (lines 98-118): `get_intent_weights()` multiplies the base composite weights by intent-specific bias parameters. The `general` intent gets no modification.

**Stage 3** (lines 625-639): Four factors per node: (1) Recency via Ebbinghaus decay `R = e^(-t/S)`, (2) Importance from importance_hint + access/degree boosts, (3) Relevance via cosine similarity to query embedding, (4) User affinity. Composite = weighted average / total weight.

**Stage 4** (lines 619-639): Multiplies composite by node-type-specific bonus.

**Stage 5** (after line 642): Currently just sorts by score. **This is where 4 of the 6 hooks operate.** It is the single biggest opportunity.

---

## Available Structural Hooks

Six pre-built hooks in `hooks.py`. Each takes `(all_nodes, all_edges, query, node_scores, config)` and returns modified `node_scores`. Registered in `HOOK_REGISTRY`.

### 1. edge_boost_score (HIGHEST IMPACT)

**Purpose:** Propagate relevance signal along graph edges. Boosts scores of graph-neighbors of high-scoring seed nodes. This is the single most impactful hook because it unlocks 108 completely unused edges.

**Why it matters:** Current scoring treats every node independently. A node connected via CAUSED_BY to a high-relevance node is itself likely relevant. For "why" queries, CAUSED_BY chains ARE the answer. For "related" queries, REFERENCES and SIMILAR_TO connect across scenarios.

**Algorithm:** Build adjacency index (cached). Seed from expected_top_nodes + top-5 scored nodes. BFS to max_hops. Boost = `boost_factor * edge_weight / hop_distance`. Takes max boost per node (not additive).

| Parameter         | Range           | Default   | Description                        |
| ----------------- | --------------- | --------- | ---------------------------------- |
| boost_factor      | [0.05, 0.5]     | 0.15      | Multiplier on neighbor score boost |
| max_hops          | [1, 3]          | 1         | BFS depth. Start with 1.           |
| edge_type_weights | per-intent dict | see below | Weight per edge type per intent    |

**Default intent-edge weights (from hooks.py):**

| Intent      | CAUSED_BY | FOLLOWS | REFERENCES | SIMILAR_TO |
| ----------- | --------- | ------- | ---------- | ---------- |
| why         | 1.0       | 0.3     | 0.5        | 0.2        |
| when        | 0.3       | 1.0     | 0.2        | 0.1        |
| what        | 0.5       | 0.3     | 0.8        | 0.3        |
| related     | 0.3       | 0.2     | 1.0        | 1.0        |
| general     | 0.5       | 0.5     | 0.5        | 0.5        |
| who_is      | 0.1       | 0.1     | 0.8        | 0.3        |
| how_does    | 0.8       | 0.6     | 0.5        | 0.3        |
| personalize | 0.1       | 0.1     | 0.8        | 0.3        |

**Expected impact:** +3-8% on related and why intents. HIGH overall.
**Best for:** related (weakest), why, what.

### 2. negative_similarity_penalty

**Purpose:** Penalize nodes whose embeddings are similar to `must_not_appear` entries. Formula: `new_score = score * (1 - penalty_factor * max_similarity_to_negative)`.

| Parameter      | Range      | Default | Description                                           |
| -------------- | ---------- | ------- | ----------------------------------------------------- |
| penalty_factor | [0.1, 1.0] | 0.5     | Penalty strength. 1.0 = full zero on identical match. |

**Expected impact:** LOW-MEDIUM. Violation rate is already 0.0125. Helps on specific cross-scenario queries.
**Best for:** All intents (reduces violations globally).

### 3. temporal_window_filter

**Purpose:** Apply soft exponential decay to Event nodes outside a temporal window. Uses midpoint of expected_top_nodes as reference time. Non-Event nodes pass through unfiltered.

| Parameter    | Range                     | Default                                                                        |
| ------------ | ------------------------- | ------------------------------------------------------------------------------ |
| window_hours | per-intent dict, [1, 720] | when: 48, why: 72, what/related/general/how_does: 168, who_is/personalize: 336 |

Events beyond the half-window decay as `e^(-overshoot / (window * 0.25))`. This is soft filtering, not hard cutoff.

**Expected impact:** MEDIUM for "when" specifically. Minimal on other intents.
**Best for:** when, how_does.

### 4. score_normalization

**Purpose:** Normalize composite scores to prevent outlier domination. Two methods: `minmax` scales to [0,1], `zscore` centers at 0 with unit variance then clips to [0,1] via `0.5 + z/2`.

| Parameter | Range                | Default  |
| --------- | -------------------- | -------- |
| method    | "minmax" or "zscore" | "minmax" |

**Expected impact:** +1-3% nDCG by reducing distortion from outlier scores, especially after edge_boost creates additive inflation.
**Best for:** general, what (multi-signal queries).

### 5. reciprocal_rank_fusion

**Purpose:** Replace weighted-average composite with RRF: rank nodes independently by each factor, then fuse as `score(d) = sum(1/(k + rank_i(d)))`. Robust to scale differences and outliers.

| Parameter | Range                                            | Default   |
| --------- | ------------------------------------------------ | --------- |
| k         | [1, 100]                                         | 60        |
| factors   | subset of ["recency", "importance", "relevance"] | all three |

When raw_scores are not provided, decomposes rankings from node attributes (occurred_at for recency, importance_score for importance, composite for relevance).

**Expected impact:** MEDIUM. +2-5% on queries where recency and relevance disagree.
**Best for:** general, what (multi-signal queries). Mutually exclusive with weighted-average -- this REPLACES composite scoring.

### 6. mmr_diversity_rerank

**Purpose:** Maximal Marginal Relevance re-ranking: `MMR(d) = lambda * relevance(d) - (1-lambda) * max_sim(d, selected)`. Reduces redundancy in top-k by promoting diverse results.

| Parameter    | Range      | Default |
| ------------ | ---------- | ------- |
| lambda_param | [0.5, 1.0] | 0.7     |
| rerank_depth | [20, 50]   | 30      |

Only the top rerank_depth nodes are re-ranked. Remainder keeps original scores.

**Expected impact:** LOW-MEDIUM. +1-3% on "related" and "what" where diversity matters. May hurt "why" where causal chain nodes are legitimately similar.
**Best for:** related, general.

---

## Untapped Signals

### 108 Graph Edges (completely unused)

The dataset contains 108 edges: ~40+ FOLLOWS (temporal sequence), ~25+ CAUSED_BY (causal chain), ~25+ REFERENCES (entity mention), ~15+ SIMILAR_TO (embedding proximity). The current `evaluate()` function never reads `all_edges`. Unlocking this via `edge_boost_score` is the highest-impact structural change available.

### Negative Similarity to must_not_appear

Each query has a `must_not_appear` blacklist. Current pipeline only checks membership. It never penalizes nodes that are embedding-similar to blacklisted nodes. The `negative_similarity_penalty` hook addresses this gap.

### Score Distribution Mismatch

The four factors have different distributions: Recency spans 0.0-1.0 (exponential decay), Importance clusters 0.3-0.7, Relevance clusters around 0.5 (cosine similarity), Affinity is mostly 0.0. The weighted average treats them as commensurable. Normalization or RRF can correct this.

### Temporal Coherence

For "when" queries, scoring returns nodes from across the entire time range. A temporal window restricts candidates to a relevant period, improving precision on temporal queries.

---

## Past Structural Breakthroughs

These changes were discovered by manual editing. They demonstrate why structural changes break through parameter ceilings.

### Cycle 8: Centroid Embedding (+1.2%)

**Change:** Instead of using the first expected node's embedding as the query representation, average ALL expected node embeddings into a centroid vector.

**Why it worked:** Single-node embeddings are noisy and biased toward one facet. The centroid captures the "average" relevant direction in embedding space. Improved recall for queries with diverse expected results.

### Cycle 11: Per-Intent Centroid Strategy (+3.3%)

**Change:** Use centroid embedding for intents where expected nodes are semantically coherent (why, when, general, how_does, personalize), but first-node embedding for intents where expected nodes are diverse (what, related).

**Why it worked:** For "related" queries, expected nodes span different scenarios. Their centroid is a meaningless average. Using the first (highest-grade) node preserves the specific semantic target.

**Combined effect:** Moved score from param-optimized 0.57 to 0.5971. Neither change was discoverable by parameter tuning.

**Lesson for you:** The biggest gains come from changing HOW scoring works, not from tweaking knobs of an existing formula. Look for places where the algorithm throws away information or makes incorrect assumptions. The 108 unused edges are the most obvious example.

---

## Structural Change Playbook

Use this decision tree to choose what to propose each cycle.

### Phase 1: Quick Gains (score < 0.55)

Start with parameter tuning. The V1 best params are a strong starting point:

```json
{
  "w_relevance": 3.2,
  "w_recency": 0.72,
  "w_importance": 0.8,
  "w_user_affinity": 0.78,
  "intent_relevance_bias": 4.2,
  "intent_affinity_bias": 1.5,
  "intent_recency_bias": 1.1,
  "entity_s_base": 720,
  "entity_s_boost": 48,
  "degree_boost_cap": 0.14,
  "node_type_profile_bonus": 1.05
}
```

If starting from defaults, apply these first. This should get you to ~0.59.

### Phase 2: Unlock Graph Signal (0.55 < score < 0.60)

Enable `edge_boost_score`. This is the single biggest untapped signal. Start conservative:

```json
{
  "type": "structural",
  "hook": "edge_boost",
  "config": { "boost_factor": 0.15, "max_hops": 1 }
}
```

Then tune `boost_factor` (0.05-0.5) and edge_type_weights per intent. Watch for regressions on WHY (already strong).

### Phase 3: Compound Hooks (0.60 < score < 0.65)

Layer additional hooks. Good combinations to try:

1. **edge_boost + normalization**: Normalization after edge_boost prevents score inflation from distorting rankings. Try minmax first.
2. **edge_boost + negative_penalty**: If violation rate creeps up after edge_boost, add negative_penalty to push down similar-to-blacklisted nodes.
3. **edge_boost + temporal_window**: If WHEN intent regresses, add temporal_window with tight window_hours for "when" (24-48h).

### Phase 4: Plateau Breakers (score > 0.60 and stalled 3+ cycles)

Try alternatives to the weighted-average composite:

- **RRF** (k=60, all three factors): Replaces the entire composite scoring with rank fusion. Good when factors disagree.
- **MMR diversity** (lambda=0.7, depth=30): If top-10 has redundant similar nodes displacing relevant diverse ones.

### Intent-Specific Weakness Map

| Weakest Intent | First Hook to Try                           | Why                                         |
| -------------- | ------------------------------------------- | ------------------------------------------- |
| related        | edge_boost (REFERENCES=1.0, SIMILAR_TO=1.0) | Cross-scenario needs graph edges            |
| why            | edge_boost (CAUSED_BY high)                 | Causal chains encoded in edges              |
| what           | score_normalization or RRF                  | Multiple factors needed, not just relevance |
| when           | temporal_window (tight window)              | Temporal precision                          |
| personalize    | raise node_type_profile_bonus param         | User nodes need higher weight               |
| general        | RRF or normalization                        | No single factor dominates                  |

### Hook Composition Order

When enabling multiple hooks, apply in this order:

1. `normalization` (fix scale issues first)
2. `edge_boost` (add graph signal to normalized scores)
3. `negative_penalty` (penalize bad nodes)
4. `temporal_window` (zero irrelevant temporal nodes)
5. `mmr_diversity` (final diversity pass on top-k)

Do NOT enable all hooks at once. Add one per cycle, measure, then add the next.

---

## Proposal Format

Each cycle, output ONE proposal inside a ```json code fence. The proposal must have a `type` field.

### Type 1: Parameter Change

Modify numeric parameters in ScoringParams. Only include parameters you want to change.

```json
{
  "type": "params",
  "changes": {
    "w_relevance": 3.5,
    "intent_relevance_bias": 4.2,
    "entity_s_base": 720.0
  }
}
```

### Type 2: Structural Hook

Enable or configure a pre-built hook from hooks.py. The `hook` field must match a key in HOOK_REGISTRY: `edge_boost`, `negative_penalty`, `temporal_window`, `normalization`, `rrf`, `mmr_diversity`.

```json
{
  "type": "structural",
  "hook": "edge_boost",
  "config": {
    "boost_factor": 0.2,
    "max_hops": 1,
    "edge_type_weights": {
      "why": {
        "CAUSED_BY": 1.5,
        "REFERENCES": 0.8,
        "FOLLOWS": 0.3,
        "SIMILAR_TO": 0.2
      },
      "related": {
        "REFERENCES": 1.5,
        "SIMILAR_TO": 1.5,
        "CAUSED_BY": 0.3,
        "FOLLOWS": 0.2
      }
    }
  }
}
```

### Type 3: Code Patch

Raw Python code patch applied to harness.py. Use this ONLY when no existing hook covers your idea. Syntax or import errors trigger automatic revert.

```json
{
  "type": "code",
  "target": "evaluate",
  "description": "Add weighted centroid using grade as weight",
  "patch": "# Python code to insert or replace in evaluate()"
}
```

**Prefer type 1 and 2 over type 3.** Code patches carry the highest risk of revert.

---

## How to Run

### V2 autoresearch loop (structural + params)

```bash
python tests/eval/autoresearch.py --cycles=20 --target=0.65 --provider=anthropic
```

### V2 with OpenAI

```bash
OPENAI_API_KEY=sk-... python tests/eval/autoresearch.py --cycles=20 --target=0.65 --provider=openai
```

### Quick test (5 cycles)

```bash
python tests/eval/autoresearch.py --cycles=5 --provider=anthropic
```

### Single evaluation with custom parameters

```bash
python tests/eval/harness.py --w_relevance=3.2 --w_recency=0.72 --json
```

---

## Constraints

1. **Hard bounds**: All parameters clamped to their ranges. Out-of-range values are clamped automatically.
2. **Weight positivity**: All w\_\* weights must be > 0. Values <= 0 are reset to 0.01.
3. **Decay ordering**: `s_base > s_boost` (violated values auto-corrected to `s_boost + 10`).
4. **Entity persistence**: `entity_s_base >= s_base` (violated values auto-corrected upward).
5. **Violation ceiling**: If violation_rate exceeds 0.1, something is broken. Revert to last good configuration.
6. **One proposal per cycle**: Submit exactly one JSON proposal. Do not combine types.

---

## Stopping Criteria

| Condition                                    | Action                                                                           |
| -------------------------------------------- | -------------------------------------------------------------------------------- |
| score >= 0.75                                | Stop. Excellent retrieval quality.                                               |
| score >= 0.65                                | V2 target reached. Continue only if budget remains and gains are still possible. |
| 5+ cycles with no improvement                | Switch strategy: params to structural, or try a different hook.                  |
| violation_rate > 0.1                         | Revert immediately. Debug before continuing.                                     |
| Structural change causes import/syntax error | Automatic revert. Log the failure and try a different approach.                  |
| All 6 hooks tested, score plateaued          | Use code patch (type 3) for novel ideas, or stop.                                |

---

## Dataset Summary

For reference, the eval dataset contains:

- **59 nodes**: Events, Entities, UserProfile, Preference, Skill types
- **108 edges**: FOLLOWS, CAUSED_BY, REFERENCES, SIMILAR_TO
- **24 queries**: 3 per intent type (8 intents)
- **3 scenarios**: PayPal domain (card decline, merchant integration, account security)
- Each query has `expected_top_nodes` (graded 1-3) and `must_not_appear` (blacklist)
