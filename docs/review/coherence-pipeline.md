# Coherence Review: Consolidation Pipeline Consistency

**Scope**: ADRs 0005, 0008, 0012, 0013
**Date**: 2026-02-12
**Reviewer**: coherence-reviewer agent

## Summary

ADR-0008 defines a three-**Stage** consolidation pipeline. ADR-0013 defines a three-**Consumer** extraction architecture. These are **partially overlapping but architecturally distinct** concepts that use different naming schemes for processes that share the same execution slots. The core problem is that ADR-0013 introduces a parallel taxonomy (Consumer 1/2/3) without explicitly reconciling it with ADR-0008's existing taxonomy (Stage 1/2/3). The two schemes are complementary in intent but have concrete contradictions in scope and naming.

---

## 1. Stage-to-Consumer Mapping Analysis

### 1.1 Stage 1 vs. Consumer 1: Graph Projection

**Verdict: Functionally identical. Naming inconsistency only.**

| Dimension | ADR-0008 Stage 1 | ADR-0013 Consumer 1 |
|-----------|------------------|---------------------|
| Name | "Event Projection" | "Structural Graph Projection" |
| Trigger | Reads events from Redis Stream via consumer group | Same |
| Operations | MERGE event nodes, create FOLLOWS + CAUSED_BY edges, update cursor | Event node creation, FOLLOWS edges, CAUSED_BY edges, session structure |
| LLM required | No | No |
| Latency | "fast-path, runs continuously" | "<50ms per event" |

**Differences:**
- ADR-0013 adds a **resilience fallback** (regex-based entity extraction) to Consumer 1 that ADR-0008 does not mention in Stage 1. ADR-0008 defines entity extraction (via REFERENCES edges) as a Stage 2 activity.
- ADR-0013 Consumer 1 handles **explicit preference events** (`user.preference.stated`) by parsing structured payloads directly into Preference nodes. ADR-0012 Section 6 also assigns explicit preference event processing to Stage 1. This is consistent between ADR-0012 and ADR-0013 but was not part of the original ADR-0008 Stage 1 definition.
- ADR-0013 Consumer 1 creates **session structure** (Session node + PART_OF edges), which ADR-0008 Stage 1 does not mention.

**Inconsistency severity: LOW.** The processes are the same. ADR-0013 adds scope to Consumer 1 (resilience fallback, explicit preference handling) that is a natural extension. The session structure (PART_OF edges) is new in ADR-0013 and not mentioned in ADR-0008 or ADR-0012.

### 1.2 Stage 2 vs. Consumer 2: The Major Divergence

**Verdict: These are DIFFERENT processes that occupy the same pipeline slot.**

| Dimension | ADR-0008 Stage 2 | ADR-0013 Consumer 2 |
|-----------|------------------|---------------------|
| Name | "Enrichment" | "Session Knowledge Extraction" |
| Trigger | "Runs asynchronously after Stage 1 completes for a batch" | Fires on `session.ended` event or every N turns |
| Operations | keywords, embeddings, importance_score, summary, SIMILAR_TO edges, REFERENCES edges | LLM extraction of preferences, skills, interests, entities from conversation text |
| LLM required | **Ambiguous** -- embeddings require a model; importance_score is "rule-based from event_type + payload heuristics"; summary implies LLM | **Yes** -- Haiku/Flash-class LLM for extraction |
| Latency | Not specified | "2-10s per session" |
| Input | Existing Neo4j nodes (enriching them with derived attributes) | Raw session transcripts from Redis |

**Critical differences:**

1. **Different input sources.** ADR-0008 Stage 2 enriches existing Neo4j nodes created by Stage 1. ADR-0013 Consumer 2 processes raw conversation text from Redis. These operate on fundamentally different data.

2. **Different operations.** ADR-0008 Stage 2 computes embeddings, keywords, importance scores, and similarity edges. ADR-0013 Consumer 2 does LLM-based extraction of preferences, skills, interests, and entities. There is almost zero overlap in what they do.

3. **ADR-0008 Stage 2 enrichment tasks are MISSING from ADR-0013.** The following ADR-0008 Stage 2 tasks are not assigned to any Consumer in ADR-0013:
   - `keywords` extraction (node property)
   - `embedding` computation (node property)
   - `importance_score` computation (node property)
   - `summary` generation (node property)
   - `SIMILAR_TO` edge creation (cosine similarity > threshold)
   - `REFERENCES` edge creation (shared entity mentions)

   These tasks are simply not mentioned in ADR-0013. They are not reassigned; they are absent.

4. **ADR-0012 bridges both but creates confusion.** ADR-0012 Section 6 "Stage 2: Enrichment (extended)" defines enrichment tasks that span both ADR-0008's enrichment model (tool preference from usage frequency, topic interest from co-occurrence, skill assessment from success/failure patterns) and ADR-0013's LLM extraction model (which subsumes some of these). ADR-0012 describes Stage 2 as doing "implicit preference inference" -- which ADR-0013 assigns to Consumer 2. But ADR-0012 also describes statistical/frequency-based tasks (tool usage frequency, topic co-occurrence) -- which ADR-0013 assigns to Consumer 3.

**Inconsistency severity: HIGH.** ADR-0008's Stage 2 (enrichment of existing graph nodes with embeddings, keywords, importance, similarity) and ADR-0013's Consumer 2 (LLM extraction from conversation text) are doing different things. Neither ADR explicitly addresses the other's tasks. The result is that ADR-0008 Stage 2 enrichment tasks (embeddings, keywords, importance, similarity edges) have no assigned Consumer in ADR-0013.

### 1.3 Stage 3 vs. Consumer 3: Partial Overlap with Scope Differences

**Verdict: Partial overlap. Consumer 3 handles a subset of Stage 3, and Stage 3 includes tasks not in Consumer 3.**

| Dimension | ADR-0008 Stage 3 | ADR-0013 Consumer 3 |
|-----------|------------------|---------------------|
| Name | "Re-Consolidation" | "Cross-Session Pattern Detection" |
| Trigger | "Configurable schedule (default: every 6 hours)" | "Scheduled daily or after N new sessions per user" |
| Operations | Cross-session relationships, hierarchical summary nodes, importance score updates from centrality, shortcut edges, **active forgetting/pruning** | Workflow extraction, behavioral pattern detection, cross-session preference merging, statistical frequency analysis |
| LLM required | Not specified (summary generation likely needs LLM) | Yes -- Sonnet-class |

**Overlapping tasks:**
- Cross-session relationship discovery (ADR-0008) overlaps with cross-session preference merging (ADR-0013)
- Both run on a periodic schedule

**Tasks in ADR-0008 Stage 3 NOT covered by ADR-0013 Consumer 3:**
- **Hierarchical summary node generation** (episode -> session -> agent level)
- **Importance score updates based on graph centrality metrics**
- **Shortcut edge optimization** between frequently co-accessed nodes
- **Active forgetting/pruning** (the entire retention tier enforcement from ADR-0008 Section "Active Forgetting")
- **Reflection trigger** processing (when accumulated importance > REFLECTION_THRESHOLD)

**Tasks in ADR-0013 Consumer 3 NOT described in ADR-0008 Stage 3:**
- **Workflow extraction** (detecting recurring step sequences) -- this is novel to ADR-0013
- **BehavioralPattern detection** (the six pattern types from ADR-0012) -- novel
- **Statistical/frequency-based extraction** (tool preference from usage frequency, no LLM) -- this was partly in ADR-0012 Stage 2 but ADR-0013 moves it to Consumer 3
- **Self-consistency sampling** for high-impact patterns

**Inconsistency severity: MEDIUM.** Active forgetting, summarization, importance updates from centrality, and reflection triggers are defined in ADR-0008 Stage 3 but have no home in ADR-0013's Consumer model. ADR-0013 does not claim to replace Stage 3 -- it describes Consumer 3 as handling "cross-session patterns." But the result is that the full Stage 3 scope is not covered.

---

## 2. Are Stages and Consumers the Same Thing or Different?

**They are different concepts applied to the same pipeline slots, but this is never stated explicitly.**

- **Stages** (ADR-0008) describe a **processing lifecycle** for the consolidation pipeline: what happens to events as they move from raw to enriched to consolidated. Stages define data transformations.

- **Consumers** (ADR-0013) describe **Redis Stream consumer groups**: independent processes that read from the same event stream and perform different work. Consumers define execution topology.

The mapping is:
- Consumer 1 (consumer group: "graph-projection") executes Stage 1 processing
- Consumer 2 (consumer group: "session-extraction") executes **some of** Stage 2 processing plus **new** LLM extraction work
- Consumer 3 (consumer group: "pattern-detection") executes **some of** Stage 3 processing plus **new** pattern detection work

The problem: ADR-0013 implicitly treats Consumers as a replacement for Stages but does not say so. It does not address the Stage 2/3 tasks that fall outside its Consumer definitions.

---

## 3. Specific Contradictions

### 3.1 Stage 2 Enrichment Tasks Are Orphaned

**ADR-0008** requires Stage 2 to compute: `keywords`, `embedding`, `importance_score`, `summary`, `SIMILAR_TO` edges, and `REFERENCES` edges on every event node.

**ADR-0013** does not assign these tasks to any Consumer. Consumer 2 does LLM extraction from text, not enrichment of existing graph nodes.

**Impact**: If the system is built to the ADR-0013 Consumer spec, it will not have embeddings, importance scores, similarity edges, or keyword extraction -- all of which ADR-0008 relies on for decay scoring (importance), retrieval ranking (relevance via embeddings), and graph connectivity (SIMILAR_TO edges).

**Recommendation**: Either (a) add a Consumer 2b (or extend Consumer 2) that performs the ADR-0008 Stage 2 enrichment tasks, or (b) explicitly amend ADR-0008 to reassign these tasks and explain where they now live.

### 3.2 Active Forgetting Has No Consumer

**ADR-0008** defines active forgetting (graph pruning by retention tier) as running "as part of the re-consolidation periodic job (Stage 3)."

**ADR-0013** Consumer 3 does pattern detection but never mentions forgetting, pruning, retention tiers, or summary node generation before pruning.

**Impact**: If only ADR-0013's Consumer 3 is implemented, the graph grows unboundedly -- the entire decay/forgetting mechanism from ADR-0008 is not executed.

**Recommendation**: Explicitly assign active forgetting to Consumer 3, or define a separate scheduled job/consumer for it.

### 3.3 Reflection Trigger Has No Consumer

**ADR-0008** defines a reflection trigger: when accumulated importance of recent events exceeds `REFLECTION_THRESHOLD = 150`, trigger an immediate re-consolidation pass.

**ADR-0013** does not mention reflection triggers. Consumer 3 runs on a fixed schedule (daily) or after N sessions, not on an importance-threshold trigger.

**Impact**: The importance-driven consolidation mechanism from ADR-0008 is not implemented in the ADR-0013 architecture.

**Recommendation**: Add the reflection trigger as an additional trigger mechanism for Consumer 3, or document that it is deferred.

### 3.4 Schedule Mismatch

**ADR-0008** Stage 3 runs "every 6 hours" by default.
**ADR-0013** Consumer 3 runs "daily" by default.

**Impact**: Low. These are configurable defaults, but the 4x frequency difference suggests different assumptions about processing cost and freshness requirements.

**Recommendation**: Reconcile to a single documented default with rationale.

### 3.5 ADR-0012 Stage 2 Tasks Reassigned to Consumer 3

**ADR-0012 Section 6** defines Stage 2 enrichment tasks including "tool preference inference" (frequency analysis), "topic interest inference" (co-occurrence), and "skill assessment" (success rate analysis). These are statistical/frequency-based, not LLM-based.

**ADR-0013** moves frequency-based extraction to Consumer 3 (see the `extract_tool_preferences_from_usage` code example in Section 5 and the statement "Separate extraction paths for text vs. behavioral data").

**Impact**: ADR-0012 says these run at Stage 2 cadence (after each batch). ADR-0013 says they run at Consumer 3 cadence (daily). This changes freshness: a tool preference inferred from frequency would appear in the graph within seconds/minutes under ADR-0012 Stage 2, but only after a daily batch under ADR-0013 Consumer 3.

**Recommendation**: Document the intended cadence for statistical enrichment tasks. If daily is acceptable, update ADR-0012 Section 6 to match. If not, keep them in a Consumer 2 post-processing step.

### 3.6 Importance Score Dependency Cycle

**ADR-0008** decay scoring formula requires `importance(node) = node.importance_score / 10`, computed by Stage 2 enrichment.

**ADR-0013** Consumer 2 does not compute importance scores. ADR-0013 Consumer 3 does not mention importance score computation either.

**Impact**: The decay scoring formula (used by all graph queries per ADR-0008) depends on a value that no Consumer computes. If importance_score is never set, decay scoring degrades to recency + relevance only, with importance contributing nothing.

**Recommendation**: Explicitly assign importance_score computation to a Consumer. The natural home is either Consumer 2 (post-extraction enrichment) or a separate enrichment consumer.

---

## 4. Metrics Consistency

**ADR-0008** defines these metrics:
- `consolidation_lag_seconds` -- time since last projected event
- `enrichment_lag_seconds` -- time since last enrichment pass
- `reconsolidation_last_run` -- timestamp of last re-consolidation
- `graph_nodes_total` -- total nodes by tier
- `graph_nodes_pruned_total` -- nodes pruned by forgetting
- `reflection_triggers_total` -- times reflection threshold was crossed
- `decay_score_p50` -- distribution of decay scores at query time

**ADR-0013** mentions `XPENDING` for consumer lag monitoring (Section 2) but does not define specific metric names.

**Assessment**: Not contradictory, but incomplete. ADR-0013's `XPENDING`-based lag monitoring is a mechanism, not a metric definition. It could naturally map to `consolidation_lag_seconds` (Consumer 1 lag), a new `extraction_lag_seconds` (Consumer 2 lag), and `pattern_detection_lag_seconds` (Consumer 3 lag). The ADR-0008 metric `enrichment_lag_seconds` has no clear Consumer owner since Stage 2 enrichment tasks are orphaned.

**Recommendation**: ADR-0013 should define Consumer-specific metrics that map to or extend ADR-0008's metric catalog.

---

## 5. ADR-0005 Consistency

**ADR-0005** (amended) positions itself as "Stage 1 Foundation" and references ADR-0008 for Stages 2 and 3. The four foundational requirements (restart-safe, position tracking, replay support, lag metrics) are stated to apply to all stages.

**ADR-0013** replaces the polling-based projection worker with Redis Stream consumer groups. ADR-0005's second amendment acknowledges this: "Redis Streams Replace Postgres Polling."

**Assessment**: ADR-0005 is consistent with both ADR-0008 and ADR-0013. The only gap is that ADR-0005's "replay support" requirement (reset cursor to position 0, re-project all events) needs to be re-described in terms of Redis Stream semantics. ADR-0013 Section 2 describes crash recovery via PEL but does not discuss full replay. ADR-0008's amendment on Redis notes that "Full replay reads from a single source (Redis) via `FT.SEARCH` sorted by `occurred_at_epoch_ms`."

**Inconsistency severity: LOW.** The concepts align; the mechanism description is scattered.

---

## 6. Recommendations

### 6.1 Reconcile Stage and Consumer Naming (Priority: HIGH)

ADR-0013 should include a section explicitly mapping Consumers to Stages:

```
| Consumer | ADR-0008 Stage | Overlap | Additional Tasks |
|----------|---------------|---------|------------------|
| Consumer 1 | Stage 1 | Full | + resilience fallback, explicit preference handling |
| Consumer 2 | Stage 2 (partial) | LLM extraction only | + session text extraction (new) |
| Consumer 2b or enrichment step | Stage 2 (remainder) | -- | embeddings, keywords, importance, similarity |
| Consumer 3 | Stage 3 (partial) | Cross-session patterns | + workflow/behavioral detection (new) |
| Consumer 3 or separate job | Stage 3 (remainder) | -- | forgetting, summarization, centrality, reflection |
```

### 6.2 Assign Orphaned Stage 2 Tasks (Priority: HIGH)

Embedding computation, keyword extraction, importance scoring, and SIMILAR_TO edge creation must be assigned to a Consumer. Options:
- **Option A**: Add these as a post-processing step within Consumer 2 (after LLM extraction, enrich the newly-created nodes)
- **Option B**: Create a dedicated Consumer 4 ("enrichment") that runs after Consumer 1 and Consumer 2
- **Option C**: Amend ADR-0008 to defer these tasks (but this breaks decay scoring)

### 6.3 Assign Active Forgetting (Priority: HIGH)

Active forgetting must run periodically. Options:
- **Option A**: Add it to Consumer 3's scheduled job
- **Option B**: Create a separate scheduled job/consumer ("retention-manager")

### 6.4 Define Consumer-Level Metrics (Priority: MEDIUM)

ADR-0013 should define metrics per consumer that map to ADR-0008's metric catalog.

### 6.5 Reconcile Scheduling Defaults (Priority: LOW)

Align ADR-0008's "every 6 hours" with ADR-0013's "daily" for the periodic batch process, or explain why they differ.

---

## 7. Conclusion

The ADR-0008 Stage model and ADR-0013 Consumer model are **complementary but incompletely reconciled**. Consumer 1 maps cleanly to Stage 1. Consumer 2 does new LLM extraction work that Stage 2 did not envision, while Stage 2's enrichment tasks (embeddings, importance, similarity) have no Consumer assignment. Consumer 3 does new pattern detection work while Stage 3's forgetting, summarization, and reflection trigger tasks have no Consumer assignment. ADR-0012 bridges both but creates additional ambiguity by assigning statistical tasks to "Stage 2" that ADR-0013 moves to Consumer 3.

The most important action is to explicitly reconcile the two naming schemes and ensure every task defined in ADR-0008 has a clear home in the ADR-0013 Consumer architecture. Without this, implementers will face ambiguity about what each Consumer must do, and critical functionality (decay scoring via importance, graph pruning via forgetting) may be omitted.
