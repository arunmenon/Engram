# ADR-0008: Memory Consolidation, Decay, and Active Forgetting

Status: **Accepted**
Date: 2026-02-11
Extends: ADR-0005 (projection worker)
Extended-by: ADR-0012 (user personalization consolidation), ADR-0013 (knowledge extraction pipeline)
Amended-by: ADR-0010 (Redis replaces Postgres)

## Context

The projection worker (ADR-0005) currently performs a single-pass transformation: poll Postgres events, MERGE into Neo4j. Research reveals this is only the first stage of a richer consolidation lifecycle. The biological model -- hippocampal replay during rest gradually writing structure into the neocortex -- maps to a multi-stage consolidation process with active forgetting.

Without decay and consolidation, the graph grows unboundedly. Every event is projected with equal weight, query performance degrades over time, and the semantic store loses its ability to surface what matters. The research consensus is clear: forgetting is a feature, not a bug.

### Research Basis

**Consolidation models:**
- MAGMA's slow-path consolidation worker infers causal and entity edges asynchronously, trading compute for relational depth (Jiang et al., 2026)
- HiMeS demonstrates that hippocampal replay (re-processing recent events to extract structure) combined with cortical storage produces 175% improvement in contextual alignment (Li et al., 2026)
- "AI Meets Brain" survey describes systems consolidation: memories shift from hippocampal dependence to neocortical sustenance through offline replay (Liang et al., 2025)
- HiCL's EWC protects important learned patterns while allowing less important ones to drift -- importance-weighted consolidation (Kapoor et al., 2025)

**Decay and forgetting models:**
- Park et al. (2023) retrieval scoring: `recency = 0.995^hours_since_last_access` -- exponential decay with access-based reinforcement
- MemoryBank Ebbinghaus curve: `R = e^(-t/S)` where stability S increases on each successful recall
- "Memory in the Age of AI Agents" identifies shift from heuristic-based to RL-driven forgetting (Hu et al., 2025)
- "Rethinking Memory Mechanisms" defines five forgetting strategies: temporal decay, selective removal, adaptive policies, deduplication, periodic pruning (Huang et al., 2026)

**Reconsolidation:**
- Biological reconsolidation: retrieval opens a plasticity window where memories can be updated (Liang et al., 2025)
- A-MEM's bidirectional evolution: new memories retroactively update attributes of existing ones (Xu et al., 2025)
- Reflexion/ExpeL: agents extract insights upon retrieval, enhancing abstraction with each access

**Reflection triggers:**
- Park et al. reflection: when `sum(importance[recent_events]) > 150`, trigger higher-level abstraction
- "Memory in the Age of AI Agents" describes three consolidation levels: local, cluster, global (Hu et al., 2025)

Non-goals for this decision:
- RL-driven memory management policies (future optimization)
- Parametric consolidation (fine-tuning agent weights from memories)
- Real-time consolidation on the ingestion critical path

## Decision

The projection worker MUST be extended from a single-pass projector to a multi-stage consolidation pipeline with active decay. The event ledger (Redis) remains append-only. All consolidation, decay, and evolution operate exclusively on the graph projection (Neo4j).

### Consolidation Stages

The projection worker MUST implement three stages, executed in order:

#### Stage 1: Event Projection (existing)

Reads new events from the Redis global stream via consumer group. For each event batch:
1. MERGE event nodes into Neo4j with core properties
2. Create temporal edges (`FOLLOWS`) based on session ordering
3. Create causal edges (`CAUSED_BY`) from `parent_event_id` references
4. Update cursor position

This stage is the fast-path consolidation -- it runs continuously.

#### Stage 2: Enrichment (new)

After event projection, a secondary pass enriches graph nodes with derived attributes:

| Derived Attribute | Source | Purpose |
|-------------------|--------|---------|
| `keywords` | Extracted from payload during projection | Keyword-based retrieval |
| `embedding` | Computed from event content | Semantic similarity edges |
| `importance_score` | Rule-based from event_type + payload heuristics | Decay weighting, retrieval ranking |
| `summary` | Compressed description of event | Hierarchical summarization |

Enrichment MUST:
- Run asynchronously after Stage 1 completes for a batch
- Never block event ingestion
- Store derived attributes as Neo4j node properties (not in the Redis event ledger)

Enrichment SHOULD:
- Generate semantic similarity edges (`SIMILAR_TO`) between events with `cosine(embedding_i, embedding_j) > threshold`
- Generate entity reference edges (`REFERENCES`) when events share entity mentions
- Use configurable thresholds for edge creation (default `similarity_threshold = 0.85`)

#### Stage 3: Re-Consolidation (new, periodic)

A periodic background process re-examines historical graph regions to discover cross-event relationships and perform structural optimization. This maps to hippocampal replay during rest.

Re-consolidation MUST:
- Run on a configurable schedule (default: every 6 hours)
- Process events in priority order: high-importance first, then high-access-frequency
- Be idempotent -- running re-consolidation on the same events produces the same result

Re-consolidation SHOULD:
- Discover new cross-session relationships (entity co-occurrence, semantic similarity)
- Generate hierarchical summary nodes (episode -> session -> agent level)
- Update importance scores based on graph centrality metrics
- Optimize graph topology by adding shortcut edges between frequently co-accessed nodes

### Decay Scoring

All graph queries MUST apply decay scoring to rank results. The scoring formula combines three factors, following the research consensus:

```
score(node, query, t_now) = w_r * recency(node, t_now)
                          + w_i * importance(node)
                          + w_v * relevance(node, query)
```

Where:

**Recency** (Ebbinghaus-inspired with access reinforcement):
```
recency(node, t_now) = e^(-t_elapsed / S)
```
- `t_elapsed` = hours since `max(node.occurred_at, node.last_accessed_at)`
- `S` = stability factor, starting at `S_base` (default 168 = 1 week half-life) and increasing by `S_boost` (default 24 hours) on each query access
- Using `last_accessed_at` means frequently queried nodes decay slower -- "use it or lose it"

**Importance** (normalized 0-1):
```
importance(node) = node.importance_score / 10
```

**Relevance** (query-dependent):
```
relevance(node, query) = cosine_similarity(node.embedding, query.embedding)
```
- Falls back to 0.5 (neutral) when embeddings are unavailable

**Default weights**: `w_r = 1.0, w_i = 1.0, w_v = 1.0` (equal weighting, tunable per deployment).

### Active Forgetting (Graph Pruning)

The graph projection MUST implement tiered retention to prevent unbounded growth. Forgetting operates on the Neo4j projection only -- the Redis event ledger is managed separately by the trimmer worker (see ADR-0010).

#### Retention Tiers

| Tier | Age | Policy |
|------|-----|--------|
| **Hot** | < 24 hours | Full detail: all nodes, all edges, all derived attributes |
| **Warm** | 24h -- 7 days | Full nodes retained; low-importance edges pruned (similarity edges with score < 0.7) |
| **Cold** | 7 -- 30 days | Only nodes with `importance_score >= 5` or `access_count >= 3` retained; summary nodes replace pruned clusters |
| **Archive** | > 30 days | Removed from Neo4j entirely; retained in Redis as cold JSON documents for replay |

#### Two Separate Tiering Systems: Neo4j vs Redis

**This ADR's retention tiers operate on the Neo4j graph projection.** ADR-0010 defines a separate tiering system for the Redis event store. These two systems use overlapping terminology ("hot", "cold") but have different time boundaries, different stores, and different purposes. Both run independently and in parallel.

| Aspect | Neo4j Retention Tiers (this ADR) | Redis Storage Tiers (ADR-0010) |
|--------|----------------------------------|-------------------------------|
| **Store** | Neo4j (semantic graph) | Redis (episodic event ledger) |
| **Purpose** | Control graph size and query performance; prune low-value nodes/edges | Control memory usage; trim stream entries, retain JSON docs |
| **Hot** | < 24 hours: all nodes, all edges, all derived attributes | 0-7 days: Streams + JSON + Search (full detail, real-time consumer groups) |
| **Warm** | 24h - 7 days: full nodes, low-importance edges pruned | (no equivalent -- Redis has no intermediate tier) |
| **Cold** | 7-30 days: only high-importance/high-access nodes retained; summary nodes replace clusters | 7+ days: JSON + Search only (stream entries trimmed via XTRIM) |
| **Archive / Gone** | > 30 days: removed from Neo4j entirely | > 90 days (community Redis): deleted from Redis entirely |
| **What survives** | Summary nodes in Neo4j preserve semantic structure | Neo4j graph projection preserves structure when raw events are deleted |
| **Managed by** | Re-consolidation periodic job (Stage 3 / Consumer 4) | Trimmer worker (ADR-0010) |

**How the two systems interact over an event's lifecycle:**

```
Day 0:   Event ingested → Redis Hot (Stream + JSON) + Neo4j Hot (full detail)
Day 1:   Redis still Hot → Neo4j transitions to Warm (low-value edges pruned)
Day 7:   Redis transitions to Cold (stream trimmed, JSON remains) → Neo4j transitions to Cold (only important nodes retained)
Day 30:  Redis still Cold (JSON remains) → Neo4j Archive (node removed, summary node persists)
Day 90:  Redis Gone (JSON deleted, community deployments) → Neo4j summary node is the sole surviving representation
```

The key insight: Redis and Neo4j decay at different rates because they serve different purposes. Redis preserves raw episodic detail (the "what happened" record). Neo4j preserves semantic structure (the "what it means" graph). An event can be alive in one store and dead in the other. The Neo4j summary nodes created during Stage 3 re-consolidation are the last line of defense -- they preserve the semantic essence of events long after both the Redis record and the Neo4j event node are gone.

Forgetting MUST:
- Run as part of the re-consolidation periodic job (Stage 3)
- Never delete events from the Redis event ledger (trimmer worker manages Redis retention separately)
- Create summary nodes before pruning clusters (preserving lineage paths)
- Log all pruning actions with event counts for monitoring

Forgetting SHOULD:
- Use the decay score to determine which nodes drop below the retention threshold at each tier boundary
- Protect nodes that are part of active lineage chains (nodes with high `CAUSED_BY` in-degree)
- Make tier boundaries and thresholds configurable per deployment

#### Reflection Trigger

When accumulated importance of recent events (since last reflection) exceeds a threshold, trigger an immediate consolidation pass:

```
if sum(importance_score for events since last_reflection) > REFLECTION_THRESHOLD:
    trigger_reconsolidation(scope="recent")
    generate_summary_nodes(scope="recent")
    last_reflection = now()
```

Default `REFLECTION_THRESHOLD = 150` (from Park et al., calibrated for ~15 high-importance events).

### Reconsolidation on Retrieval

When graph nodes participate in a query result, the system SHOULD update their metadata without mutating the source events:

- Increment `access_count` on queried nodes
- Update `last_accessed_at` timestamp
- Recalculate `stability` factor for decay scoring: `S_new = S_old + S_boost`

This implements the biological reconsolidation pattern: retrieval strengthens memories. The Redis event ledger remains append-only; only Neo4j node properties change.

### Monitoring

The consolidation pipeline MUST expose metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `consolidation_lag_seconds` | Gauge | Time since last projected event |
| `enrichment_lag_seconds` | Gauge | Time since last enrichment pass |
| `reconsolidation_last_run` | Gauge | Timestamp of last re-consolidation |
| `graph_nodes_total` | Gauge | Total nodes in Neo4j by tier |
| `graph_nodes_pruned_total` | Counter | Nodes pruned by forgetting |
| `reflection_triggers_total` | Counter | Times reflection threshold was crossed |
| `decay_score_p50` | Histogram | Distribution of decay scores at query time |

## Consequences

### Positive

- **Bounded graph growth**: Active forgetting prevents Neo4j from growing unboundedly
- **Relevance-ranked retrieval**: Decay scoring surfaces recent and important context, not just all context
- **Neuroscience-grounded design**: Consolidation stages map to well-studied biological mechanisms (replay, consolidation, reconsolidation)
- **Immutability preserved**: All evolution happens in the derived Neo4j projection; the Redis event ledger remains the append-only source of truth
- **Rebuildable**: Because Neo4j is derived, changing decay parameters or enrichment strategies requires only a re-projection, not a schema migration

### Negative

- **Increased worker complexity**: Three consolidation stages vs. current single-pass projection
- **Tuning burden**: Decay parameters (S_base, S_boost, tier boundaries, REFLECTION_THRESHOLD) require empirical calibration
- **Enrichment latency**: Embedding computation and similarity edge creation add processing time to the consolidation pipeline
- **Summary node quality**: Automated hierarchical summaries may lose important detail; quality depends on summarization strategy

### Risks to Monitor

| Risk | Mitigation |
|------|------------|
| Over-aggressive pruning loses important context | Start with conservative thresholds; monitor retrieval miss rate before tightening |
| Enrichment becomes a bottleneck | Batch embedding computation; use lightweight models (all-MiniLM-L6-v2); make enrichment depth configurable |
| Decay scoring penalizes infrequently-but-critical events | High importance_score protects critical events regardless of recency |
| Re-consolidation job takes too long | Enforce timeout per re-consolidation run; process in priority order so high-value regions are handled first |

## Alternatives Considered

### 1. No decay -- rely on bounded queries only
Rejected. Bounded queries limit result size but do not rank by relevance. Without decay, old irrelevant nodes compete equally with recent important ones for the bounded result set.

### 2. TTL-based pruning only (no scoring)
Rejected. Pure time-based TTL ignores importance. A 30-day-old high-importance event should persist longer than a 2-day-old low-importance observation.

### 3. LRU cache model
Rejected. LRU discards the least-recently-used regardless of importance. The Ebbinghaus model with importance weighting is strictly better -- it considers both recency AND value.

### 4. RL-driven decay policies
Deferred. Research (Hu et al., 2025) identifies RL-driven memory management as the frontier, but it requires training data (query logs, retrieval success metrics) that we do not yet have. Start with heuristic scoring; collect telemetry; consider RL optimization in a future phase.

## Research References

- Jiang et al. (2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture." arXiv:2601.03236
- Li et al. (2026). "HiMeS: Hippocampus-inspired Memory System." arXiv:2601.06152
- Liang et al. (2025). "AI Meets Brain: Memory Systems from Cognitive Neuroscience to Autonomous Agents." arXiv:2512.23343
- Kapoor et al. (2025). "HiCL: Hippocampal-Inspired Continual Learning." arXiv:2508.16651
- Hu et al. (2025). "Memory in the Age of AI Agents." arXiv:2512.13564
- Huang et al. (2026). "Rethinking Memory Mechanisms of Foundation Agents." arXiv:2602.06052
- Xu et al. (2025). "A-MEM: Agentic Memory for LLM Agents." arXiv:2502.12110
- Park et al. (2023). "Generative Agents: Interactive Simulacra of Human Behavior." UIST 2023.
- Ebbinghaus (1885). "Memory: A Contribution to Experimental Psychology."

## Amendments

### 2026-02-11: Cross-Reference Clarifications

**Importance scoring source:** Stage 2 enrichment computes `importance_score` as a Neo4j node property. When the ingested event includes an `importance_hint` (ADR-0004 amendment, ADR-0007), enrichment SHOULD use it as one input signal among graph-derived factors. When absent, enrichment computes importance entirely from heuristics (event_type weighting, payload analysis, graph centrality). The `importance_hint` is a seed; the Neo4j `importance_score` is the authoritative computed value.

**Relationship to ADR-0005:** This ADR extends the projection worker defined in ADR-0005 from a single-pass projector to a three-stage consolidation pipeline. ADR-0005's four foundational requirements (restart-safe, position tracking, replay support, lag metrics) apply to all three stages. See ADR-0005 amendment for the explicit stage mapping.

### 2026-02-11: Redis Adoption (ADR-0010)

Promoted to Accepted. Stage 1 projection worker now uses Redis consumer groups instead of Postgres polling. Redis serves as both hot and cold event storage — stream entries are trimmed after the hot window, but JSON documents persist for the full retention period, queryable via RediSearch.

Archive tier (>30 days) changes from "retained in Postgres for replay" to "retained in Redis as JSON documents (cold tier) for replay." For community Redis deployments without Auto Tiering, events beyond the retention ceiling (default: 90 days) are removed from Redis entirely. The Neo4j graph projection and summary nodes (Stage 3) preserve the semantic structure of pruned events, so the information persists at a higher abstraction level even when raw episodic records are removed.

Full replay reads from a single source (Redis) via `FT.SEARCH` sorted by `occurred_at_epoch_ms`. Retention tier boundaries and decay scoring unchanged.

### 2026-02-12: User-State-Aware Scoring

**What changed:** The decay scoring formula is extended with a fourth factor — **user context affinity** — that considers the user's retrieval history and graph neighborhood when ranking results. This supports the system-owned retrieval principle (ADR-0009 amendment: System-Owned Intent Classification).

**Rationale:** The existing three-factor scoring (`recency + importance + relevance`) is query-scoped: it ranks nodes based on how recent they are, how important they are globally, and how similar they are to the current query. It does not consider the user's specific context: what they've asked about before, what patterns exist in their graph, or what context proved useful in prior retrievals.

**Extended scoring formula:**

```
score(node, query, user, t_now) = w_r * recency(node, t_now)
                                + w_i * importance(node)
                                + w_v * relevance(node, query)
                                + w_u * user_affinity(node, user)
```

**User affinity** (normalized 0-1):

```
user_affinity(node, user) = weighted_mean(
    session_proximity(node, user),     # Is this node in or near the user's recent sessions?
    retrieval_recurrence(node, user),  # Has this node been surfaced to this user before?
    entity_overlap(node, user)         # Does this node share entities with the user's graph?
)
```

Where:

- **session_proximity**: Nodes in the user's current or recent sessions score higher. A node from Maria's Session 1 is more relevant to Maria than an identical node from another merchant's session. Computed as `1.0` for current session, `0.7` for sessions within 7 days, `0.3` for older sessions, `0.0` for other users' sessions (unless reached via SIMILAR_TO traversal).

- **retrieval_recurrence**: Nodes that were returned in a previous query during the same session and subsequently accessed again (high reconsolidation reinforcement) score higher. This captures "the system already surfaced this and it was useful." Computed from `access_count` relative to session-local retrieval history.

- **entity_overlap**: Nodes that share Entity references with the user's recent events score higher. If Maria has been discussing payment failures, any node referencing Entity:card_declined or Entity:payment gets a boost, even if the node itself is from a different user or session. Computed as `shared_entities / max(user_entities, node_entities)`.

**Default weight**: `w_u = 0.5` (lower than the other three factors at 1.0). User affinity is a **tiebreaker and booster**, not a primary ranking signal. Two nodes with similar recency, importance, and relevance should be differentiated by user context — but user affinity alone should not override a highly relevant, highly important node.

**When user context is unavailable** (e.g., anonymous queries, system-level admin queries): `user_affinity` falls back to `0.0`, and scoring degrades gracefully to the original three-factor formula.

**Impact on reconsolidation on retrieval (Section: Reconsolidation on Retrieval):** The existing side-effects (increment `access_count`, update `last_accessed_at`, recalculate `stability`) are unchanged. The `retrieval_recurrence` sub-factor of `user_affinity` reads these values but does not write additional state beyond what the existing reconsolidation already tracks.
