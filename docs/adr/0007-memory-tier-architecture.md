# ADR-0007: Cognitive Memory Tier Architecture

Status: **Accepted**
Date: 2026-02-11
Extended-by: ADR-0008 (consolidation and decay), ADR-0012 (user personalization)
Amended-by: ADR-0010 (Redis replaces Postgres)

## Context

Recent research (Dec 2025 -- Feb 2026) across agent memory architectures, graph-based memory systems, and neuroscience-inspired AI consistently converges on a multi-tier cognitive memory model. The field has moved beyond simple short-term/long-term dichotomies to a five-type taxonomy grounded in cognitive neuroscience: sensory, working, episodic, semantic, and procedural memory.

Our existing dual-store architecture (Postgres event ledger + Neo4j graph projection + async projection worker) already implements the Complementary Learning Systems (CLS) pattern identified in neuroscience research -- but this alignment is implicit. This ADR makes it explicit and defines how each memory tier maps to system components.

### Research Basis

Nine papers across three research clusters inform this decision:

**Cluster 1 -- Graph-Based Memory:**
- Yang et al. (2026) survey identifies six cognitive memory types and five graph structures for agent memory
- MAGMA (Jiang et al., 2026) validates dual-stream write (fast ingestion + slow consolidation) mapping to our architecture
- A-MEM (Xu et al., 2025) demonstrates bidirectional memory evolution through interconnected knowledge networks

**Cluster 2 -- Memory Architectures:**
- "Memory in the Age of AI Agents" (Hu et al., 2025) proposes Forms/Functions/Dynamics framework with experiential memory hierarchy (case -> strategy -> skill)
- "Rethinking Memory Mechanisms" (Huang et al., 2026) provides the most detailed five-type cognitive taxonomy
- Pink et al. (2025) defines five properties of episodic memory and a three-system architecture (working + episodic + semantic)

**Cluster 3 -- Neuroscience:**
- "AI Meets Brain" (Liang et al., 2025) maps hippocampal-neocortical consolidation to agent memory lifecycle
- HiMeS (Li et al., 2026) validates dual-memory (hippocampal STM + neocortical LTM) with RL-trained consolidation
- HiCL (Kapoor et al., 2025) provides concrete hippocampal circuit mappings (DG pattern separation, CA3 completion, EWC consolidation)

### Key Finding

All three research clusters independently arrived at the same architectural conclusion: our Postgres + Neo4j + projection worker architecture maps directly to the hippocampal-neocortical Complementary Learning Systems model. This ADR formalizes that mapping.

Non-goals for this decision:
- Implementing parametric memory (fine-tuning agent weights)
- Multi-agent shared memory coordination protocols
- User-centric personalization memory

## Decision

The memory layer MUST implement four cognitive memory tiers mapped to existing system components. A fifth tier (sensory) is acknowledged but not implemented as a persistent store.

### Tier Definitions and Component Mapping

```
+-------------------------------------------------------------------+
|  Tier             | Component               | Characteristics     |
|-------------------|-------------------------|---------------------|
|  Sensory          | API ingestion buffer    | Transient, <1s      |
|  Working          | Context API response    | Session-scoped,     |
|                   | (per-request assembly)  | capacity-bounded    |
|  Episodic         | Redis event store       | Immutable, instance |
|                   |                         | -specific, temporal |
|  Semantic         | Neo4j graph projection  | Derived, relational |
|                   |                         | abstract knowledge  |
|  Procedural       | Neo4j pattern subgraph  | Tool-use policies,  |
|                   | (future)                | learned workflows   |
+-------------------------------------------------------------------+
```

### Tier 1: Sensory Memory (Ingestion Buffer)

- **Scope**: Raw events arriving at `/v1/events` before validation
- **Duration**: Sub-second; discarded after validation pass/fail
- **Implementation**: Request body buffering in FastAPI; no persistent storage
- **NOT a design target** -- exists implicitly in the HTTP request lifecycle

### Tier 2: Working Memory (Context Assembly)

The `/v1/context/{session_id}` endpoint MUST assemble a bounded, priority-ranked context window for the requesting agent. This is the agent's working memory.

Working memory MUST:
- Enforce capacity limits inspired by cognitive constraints (configurable `max_nodes`, default 100; `max_depth`, default 3)
- Prioritize by combined scoring: `score = w_recency * recency + w_importance * importance + w_relevance * relevance`
- Return results in the Atlas response pattern with provenance pointers
- Support pagination via cursor for overflow

Working memory SHOULD:
- Chunk related events into coherent episodes before returning (grouping by trace_id or parent_event_id chains)
- Include scoring metadata in the `meta` response field

### Tier 3: Episodic Memory (Postgres Event Ledger)

The Redis event store IS the episodic memory store. This tier satisfies all five properties of episodic memory (Pink et al., 2025):

| Property | Implementation |
|----------|---------------|
| Long-term storage | Immutable append-only ledger with Redis Stream entry ID ordering |
| Explicit reasoning | Events queryable via API; inspectable via lineage endpoint |
| Single-shot learning | Each event captured once; idempotent dedup via Lua script (ADR-0010) |
| Instance-specific | Unique event_id (UUID) with specific payload per event |
| Contextual relations | session_id, trace_id, parent_event_id, agent_id, tool_name bind context |

Episodic memory MUST:
- Remain immutable -- events are never modified or deleted (except GDPR erasure via Forgettable Payloads)
- Serve as the source of truth from which all other tiers are derived
- Support deterministic replay via `global_position` ordering

### Tier 4: Semantic Memory (Neo4j Graph Projection)

The Neo4j graph projection IS the semantic memory store -- abstract relational knowledge derived from episodic records, stripped of temporal specificity.

Semantic memory MUST:
- Be entirely derivable from the episodic tier (rebuildable from Redis events)
- Store relational structure: entity nodes, relationship edges, lineage paths
- Support multi-hop traversal for reasoning queries

Semantic memory SHOULD:
- Accumulate derived properties on nodes (importance scores, access frequency, keywords, embeddings) that evolve over time
- Support reconsolidation: graph nodes gain new metadata on query without mutating source events

### Tier 5: Procedural Memory (Future -- Neo4j Pattern Subgraph)

Procedural memory captures learned tool-use policies and action patterns. This tier is NOT part of the current MVP but MUST be accommodated in the schema.

Procedural memory SHOULD (future):
- Extract repeated successful event sequences into reusable workflow patterns
- Follow the experiential hierarchy: case-based (raw traces) -> strategy-based (abstracted workflows) -> skill-based (executable procedures)
- Be stored as specialized subgraph patterns in Neo4j with `WORKFLOW` and `STEP` node types

### Inter-Tier Flow

The memory lifecycle follows a directional flow consistent across all nine research papers:

```
Sensory --> Working --> Episodic --> Semantic
  (ingest)   (assemble)  (persist)   (consolidate)
                           |
                           +--> Procedural (future: pattern extraction)
```

The consolidation direction is:
1. Events ingested into Postgres (episodic capture -- fast, detailed)
2. Projection worker transforms events into Neo4j graph (semantic consolidation -- slow, abstracting)
3. Context API assembles working memory from both stores (retrieval -- bounded, ranked)

This maps to the neuroscience model:
- **Postgres = hippocampus** (rapid encoding, detailed episodic traces, index-based storage)
- **Neo4j = neocortex** (consolidated relational knowledge, query-optimized, gradually abstracted)
- **Projection worker = systems consolidation** (async replay writing structure from hippocampus to neocortex)

### Event Schema Extension

To support memory tier operations, the Postgres event schema SHOULD be extended with:

```
importance_hint  SMALLINT  DEFAULT NULL   -- caller-supplied importance estimate (1-10 scale)
```

This field:
- Is OPTIONAL on ingestion (backward-compatible)
- Represents a caller-supplied hint, not the authoritative importance score
- Can be populated by producers with domain knowledge (e.g., an agent knows a tool failure is important)
- Can be populated by the ingestion layer using rule-based heuristics (e.g., `tool.execute` events default to higher importance than `observation.received`)

**Dual-source importance semantics:** The authoritative `importance_score` is computed during enrichment (ADR-0008 Stage 2) and stored in Neo4j. Enrichment MAY use the Postgres `importance_hint` as one input signal among graph-derived factors (centrality, access frequency). When `importance_hint` is absent at ingestion, enrichment computes importance entirely from heuristics and graph context. See ADR-0004 amendment for the complete Postgres schema.

## Consequences

### Positive

- **Research-validated architecture**: Nine recent papers independently confirm our dual-store design aligns with Complementary Learning Systems theory
- **Clear component responsibilities**: Each system component has a defined cognitive role, guiding future design decisions ("is this episodic capture or semantic consolidation?")
- **Backward-compatible**: The tier model is an overlay on existing architecture; no breaking changes to event schema or API
- **Extensible**: Procedural memory tier provides a clear path for tool-use pattern learning
- **Shared vocabulary**: Teams can reason about memory operations using cognitive terminology anchored in literature

### Negative

- **Conceptual overhead**: Developers must understand the tier model to make informed design decisions
- **Importance scoring is approximate**: LLM-rated or rule-based importance scores are inherently noisy; scoring quality depends on heuristic design
- **Procedural tier deferred**: Tool-use pattern learning is valuable but not addressed in MVP; risk of scope creep if pursued prematurely

### Risks to Monitor

| Risk | Mitigation |
|------|------------|
| Tier boundaries become unclear as features grow | Document each new feature's tier assignment in design docs |
| Importance scoring adds ingestion latency | Make scoring async or rule-based (no LLM calls on critical path) |
| Working memory assembly becomes a bottleneck | Cache common session contexts; monitor p95 latency |

## Alternatives Considered

### 1. Simple short-term / long-term split
Rejected. Research consensus is that this dichotomy is insufficient (Hu et al., 2025; Huang et al., 2026). The five-type cognitive model provides finer-grained guidance for design decisions.

### 2. Flat memory with tagging
Rejected. Tagging memories as "episodic" or "semantic" without architectural separation loses the performance and isolation benefits of the dual-store design.

### 3. Three-tier model (working / episodic / semantic only)
Considered viable for MVP. However, explicitly acknowledging procedural memory as a future tier prevents schema decisions that would make it difficult to add later. The four-tier model (plus implicit sensory) costs nothing to define now.

## Research References

- Yang et al. (2026). "Graph-based Agent Memory: Taxonomy, Techniques, and Applications." arXiv:2602.05665
- Jiang et al. (2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture." arXiv:2601.03236
- Xu et al. (2025). "A-MEM: Agentic Memory for LLM Agents." arXiv:2502.12110
- Hu et al. (2025). "Memory in the Age of AI Agents." arXiv:2512.13564
- Huang et al. (2026). "Rethinking Memory Mechanisms of Foundation Agents." arXiv:2602.06052
- Pink et al. (2025). "Position: Episodic Memory is the Missing Piece for Long-Term LLM Agents." arXiv:2502.06975
- Liang et al. (2025). "AI Meets Brain: Memory Systems from Cognitive Neuroscience to Autonomous Agents." arXiv:2512.23343
- Li et al. (2026). "HiMeS: Hippocampus-inspired Memory System for Personalized AI Assistants." arXiv:2601.06152
- Kapoor et al. (2025). "HiCL: Hippocampal-Inspired Continual Learning." arXiv:2508.16651

## Amendments

### 2026-02-11: Importance Field Renamed and Phased Deployment Note

**Importance field:** The originally proposed `importance_score` Postgres field has been renamed to `importance_hint` to distinguish it from the enrichment-computed `importance_score` in Neo4j. See ADR-0004 amendment for the authoritative Postgres schema.

**Phased deployment alignment:** The tier architecture is a logical model that guides design decisions across all deployment phases. While this ADR describes the full four-tier system with both Postgres and Neo4j, the model remains valid during phased deployment:
- In the initial build with both stores: All four tiers are active as described.
- The transition to adding consolidation features (ADR-0008 Stages 2-3) does not require schema changes — it adds enrichment capabilities to events already being projected.
- The CLS mapping (Postgres=hippocampus, Neo4j=neocortex) reflects the target architecture that the project adopts from the initial build per ADR-0003 (Accepted).

### 2026-02-11: Redis Adoption (ADR-0010)

Promoted to Accepted. Tier 3 (Episodic Memory) implementation changes from Postgres to Redis per ADR-0010. CLS mapping updated: Redis = hippocampus (fast episodic encoding). Redis serves both hot and cold event tiers — stream entries provide the hot window with consumer group delivery, while JSON documents persist beyond the hot window for cold queries via RediSearch. Redis actually better fits the hippocampal model — fast temporary encoding that gradually consolidates to long-term semantic storage (Neo4j).
