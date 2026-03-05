# Cluster 3: Neuroscience Memory -- Compliance Audit

## Executive Summary

- **Total patterns checked**: 30
- **COMPLIANT**: 21
- **PARTIAL**: 7
- **GAP**: 2

The Engram codebase has strong alignment with the neuroscience-inspired memory patterns documented in Cluster 3. The Complementary Learning Systems (CLS) architecture is fully implemented as a Redis (hippocampal) + Neo4j (neocortical) dual store with an async projection worker serving as the consolidation process. Ebbinghaus-inspired decay scoring, multi-tier forgetting, hierarchical summarization, reconsolidation on retrieval, and bounded working-memory queries are all implemented. The primary gaps are in embedding-based operations (SIMILAR_TO edge creation, embedding computation) and the RL-trained query compression pattern from HiMeS.

---

## Pattern-by-Pattern Audit

### Paper 3.1 (Survey): AI Meets Brain

---

### Pattern 1: Hippocampal-Neocortical Consolidation
**Research Requirement**: New information is rapidly encoded in a fast store (hippocampus), then gradually consolidated into a slow, structured store (neocortex) through replay during rest. The hippocampus stores an index, not full content.
**Status**: COMPLIANT
**Evidence**:
- Redis as fast episodic store: `src/context_graph/adapters/redis/store.py:143-179` -- `append()` writes events to Redis Stream + JSON in sub-millisecond.
- Neo4j as consolidated semantic store: `src/context_graph/adapters/neo4j/store.py:100-121` -- `merge_event_node()` MERGEs into the graph projection.
- Projection worker as consolidation: `src/context_graph/worker/projection.py:30-107` -- `ProjectionConsumer` reads from Redis Stream, transforms events via domain projection, and writes to Neo4j.
- ADR-0003 explicitly maps: Redis = hippocampus, Neo4j = neocortex, projection worker = systems consolidation.
- Events contain `payload_ref` (a pointer, not full content) -- this IS hippocampal indexing: `src/context_graph/domain/models.py:269`.
**Notes**: The mapping is exact. Redis captures raw episodic detail (fast writes, immutable); Neo4j holds consolidated relational knowledge (query-optimized).

---

### Pattern 2: Complementary Learning Systems (CLS) Theory
**Research Requirement**: Two complementary systems: a fast/flexible one for rapid specific encoding and a slow/stable one for consolidated abstract patterns. The balance between immediate context and background knowledge must be managed.
**Status**: COMPLIANT
**Evidence**:
- Fast system (Redis): Append-only stream + JSON, sub-ms writes, full event detail. `src/context_graph/adapters/redis/store.py:95-179`.
- Slow system (Neo4j): MERGE-based idempotent writes, enriched nodes with importance/access/embedding properties, summary nodes for abstraction. `src/context_graph/adapters/neo4j/store.py:78-624`.
- The tension between immediate context and background knowledge is managed by the 4-factor decay scoring: `src/context_graph/domain/scoring.py:22-46` (recency), `49-62` (importance), `65-81` (relevance), `84-104` (composite with user_affinity).
- Settings explicitly reference CLS: `src/context_graph/settings.py:72-95` -- DecaySettings with s_base=168h (1 week), s_boost=24h.
**Notes**: ADR-0003 amendment explicitly documents the CLS mapping. ADR-0008 references the biological model.

---

### Pattern 3: Memory Management Lifecycle (Encoding -> Consolidation -> Retrieval -> Reconsolidation -> Forgetting)
**Research Requirement**: Five-stage lifecycle: encoding, consolidation, retrieval, reconsolidation (updating on retrieval), and active forgetting.
**Status**: COMPLIANT
**Evidence**:
- **Encoding**: Redis `append()` captures events immediately: `src/context_graph/adapters/redis/store.py:143-179`.
- **Consolidation**: 4-consumer pipeline (Consumers 1-4): `src/context_graph/worker/projection.py`, `extraction.py`, `enrichment.py`, `consolidation.py`.
- **Retrieval**: Intent-aware subgraph query: `src/context_graph/adapters/neo4j/store.py:430-585`, context assembly: `301-355`, lineage: `357-428`.
- **Reconsolidation**: Access count bump and last_accessed_at update on every query: `src/context_graph/adapters/neo4j/store.py:288-299` (`_bump_access_counts`), called from `get_context` (line 334), `get_lineage` (line 408), `get_subgraph` (line 558).
- **Forgetting**: Tiered retention enforcement in `src/context_graph/domain/forgetting.py:32-161` and `src/context_graph/adapters/neo4j/maintenance.py:142-248`. ConsolidationConsumer._run_forgetting: `src/context_graph/worker/consolidation.py:253-302`.
**Notes**: All five stages are implemented. The lifecycle is complete.

---

### Pattern 4: Memory Replay Mechanisms
**Research Requirement**: During rest, the hippocampus replays recent experiences to write structural knowledge into the neocortex. Replay serves consolidation (strengthening) and integration (cross-linking) functions.
**Status**: COMPLIANT
**Evidence**:
- The projection worker IS memory replay -- it reads events from Redis and replays them into Neo4j: `src/context_graph/worker/projection.py:57-107`.
- Re-consolidation (periodic replay) discovers cross-event relationships and creates summary nodes: `src/context_graph/worker/consolidation.py:81-163`. Runs on schedule (default 6h) and on reflection trigger.
- Priority replay via reflection trigger: `src/context_graph/domain/consolidation.py:26-31` -- `should_reconsolidate()` checks if importance sum exceeds threshold (150). Called in `worker/consolidation.py:94`.
- Centrality-based importance recomputation during replay: `src/context_graph/adapters/neo4j/maintenance.py:384-408` -- `update_importance_from_centrality()`.
**Notes**: Both continuous replay (Consumer 1) and periodic re-consolidation (Consumer 4) are implemented.

---

### Pattern 5: Working Memory Capacity Limits (Miller's 7+/-2)
**Research Requirement**: Short-term memory holds 4-9 items. Brain dynamically reallocates resources, prioritizing task-relevant information. LLMs suffer "lost-in-the-middle" phenomenon.
**Status**: COMPLIANT
**Evidence**:
- Bounded queries enforced universally: `src/context_graph/domain/lineage.py:12-27` -- `validate_traversal_bounds()` clamps max_depth (1-10), max_nodes (1-500), timeout_ms (100-30000).
- Default limits: max_depth=3, max_nodes=100, timeout_ms=5000: `src/context_graph/settings.py:115-127` (QuerySettings).
- Atlas response pattern with pagination: `src/context_graph/domain/models.py:499-515` -- `Pagination(cursor, has_more)`.
- Context assembly returns decay-scored top-N nodes: `src/context_graph/adapters/neo4j/store.py:326-328` -- sorts by composite decay_score descending, takes top max_nodes.
- QueryCapacity tracking in every response: `src/context_graph/domain/models.py:475-480` -- shows max_nodes, used_nodes, max_depth.
**Notes**: The system prevents context overflow by enforcing hard limits and ranking by relevance within those limits.

---

### Pattern 6: Emotional Salience and Priority Weighting
**Research Requirement**: Prefrontal cortex sets priorities; high-priority items maintained in active state; emotional events receive enhanced encoding and preferential consolidation.
**Status**: COMPLIANT
**Evidence**:
- `importance_hint` (1-10) on events: `src/context_graph/domain/models.py:281` -- ingested as event metadata.
- `importance_score` computed by enrichment, incorporating hint + access + centrality: `src/context_graph/domain/scoring.py:49-62` -- `compute_importance_score()`.
- Importance weighting in composite score: `src/context_graph/domain/scoring.py:84-104` -- `compute_composite_score()` with configurable weight_importance.
- High importance protects nodes from forgetting: `src/context_graph/domain/forgetting.py:77-92` -- cold tier spares nodes with importance_score >= 5.
- Centrality-based importance boost during re-consolidation: `src/context_graph/adapters/neo4j/maintenance.py:106-117` -- in-degree >= 10 gets importance 10, >= 5 gets 8, >= 3 gets 6.
**Notes**: Importance scoring serves as the computational analog of emotional salience.

---

### Pattern 7: Memory Reconsolidation
**Research Requirement**: Retrieval opens a plasticity window -- memories can be updated, strengthened, or weakened upon access. Memories are not fixed after initial consolidation.
**Status**: COMPLIANT
**Evidence**:
- Access count increment on every query: `src/context_graph/adapters/neo4j/queries.py:268-273` -- `BATCH_UPDATE_ACCESS_COUNT` increments `access_count` and updates `last_accessed_at`.
- Called from every query path: `store.py:334` (get_context), `store.py:408` (get_lineage), `store.py:558` (get_subgraph).
- Stability factor grows with access: `src/context_graph/domain/scoring.py:43` -- `stability = s_base + (access_count * s_boost)`. Each access adds 24h of stability.
- Recency computed from `max(occurred_at, last_accessed_at)`: `src/context_graph/domain/scoring.py:39-41` -- accessed nodes decay slower.
- Redis event ledger remains immutable: only Neo4j node properties change.
**Notes**: This exactly mirrors biological reconsolidation -- retrieval strengthens the memory trace without modifying the original record.

---

### Pattern 8: Forgetting as Active Process (Ebbinghaus Forgetting Curve)
**Research Requirement**: R = e^(-t/S) -- retention decays exponentially unless reinforced by spaced repetition. Forgetting is adaptive, maintaining efficiency and relevance.
**Status**: COMPLIANT
**Evidence**:
- Ebbinghaus curve implementation: `src/context_graph/domain/scoring.py:22-46` -- `compute_recency_score()` returns `math.exp(-t_hours / stability)`.
- Stability increases with access (spaced repetition): `stability = s_base + (access_count * s_boost)` at line 43.
- Four retention tiers: `src/context_graph/domain/forgetting.py:32-58` -- HOT (<24h), WARM (24h-7d), COLD (7-30d), ARCHIVE (>30d).
- Tier-specific pruning rules: WARM prunes low-similarity edges (line 61-74), COLD prunes low-importance AND low-access nodes (line 77-92), ARCHIVE removes entirely (line 143-159).
- Batch pruning: `src/context_graph/domain/forgetting.py:95-161` -- `get_pruning_actions()`.
- Neo4j maintenance implements the actual deletions: `src/context_graph/adapters/neo4j/maintenance.py:142-248`.
**Notes**: The implementation faithfully follows the Ebbinghaus model with the enhancement of access-reinforced stability.

---

### Pattern 9: Biological-to-Computational Mapping (Survey Table)
**Research Requirement**: The survey provides 9 biological-to-computational mappings.
**Status**: COMPLIANT
**Evidence**:

| Biological Mechanism | Required Implementation | Actual Implementation | Status |
|---------------------|------------------------|----------------------|--------|
| Hippocampal fast encoding | Append-only event ledger | Redis XADD + JSON.SET (`redis/store.py:143-179`) | COMPLIANT |
| Neocortical slow consolidation | Graph projection, knowledge base | Neo4j MERGE via projection worker (`neo4j/store.py:100-121`) | COMPLIANT |
| Hippocampal indexing | Hierarchical summarization, KG triples | Summary nodes (episode/session/agent scope) via `consolidation.py:73-116` | COMPLIANT |
| Systems consolidation | Async projection worker | 4 consumer groups (`worker/projection.py`, `extraction.py`, `enrichment.py`, `consolidation.py`) | COMPLIANT |
| Memory replay | Experience replay, reflection | Consumer 4 re-consolidation (`worker/consolidation.py:81-163`) | COMPLIANT |
| Working memory limits | Context window management | Bounded queries (`lineage.py:12-27`), Atlas pagination (`models.py:499-515`) | COMPLIANT |
| Importance weighting | Priority scoring | `importance_hint` on events + computed `importance_score` (`scoring.py:49-62`) | COMPLIANT |
| Reconsolidation | Update-on-retrieval | Access count bump on query (`neo4j/store.py:288-299`) | COMPLIANT |
| Forgetting curve | TTL-based decay, importance pruning | Ebbinghaus formula + 4-tier retention (`forgetting.py`, `maintenance.py`) | COMPLIANT |

---

### Paper 3.2 (HiMeS): Hippocampus-Inspired Memory System

---

### Pattern 10: Dual-Memory Architecture (STM + LTM)
**Research Requirement**: Two-module design: Short-Term Memory (hippocampal, compresses recent dialogue) and Long-Term Memory (neocortical, distributed topic-organized storage with re-ranking).
**Status**: COMPLIANT
**Evidence**:
- STM analog: Redis event stream with session-scoped retrieval (`redis/store.py:232-254` -- `get_by_session()`). Context assembly returns recent session events: `neo4j/store.py:301-355`.
- LTM analog: Neo4j graph with cross-session entities, preferences, skills, patterns. User query endpoints: `api/routes/users.py:33-136`.
- Both paths combined in subgraph query: `neo4j/store.py:430-585` -- seeds from session (STM), traverses cross-session graph (LTM).
**Notes**: The architecture naturally implements dual-memory: session-local (fast/recent) and graph-global (slow/historical).

---

### Pattern 11: RL-Trained Query Compression (HiMeS STM)
**Research Requirement**: HiMeS trains a rewriter via SFT + RL (GRPO) to compress dialogue into refined retrieval queries before retrieval.
**Status**: GAP
**Evidence**: No query compression or rewriting module exists in the codebase. The `query` field on `SubgraphQuery` (`models.py:543`) is passed directly to intent classification (`domain/intent.py:59-80`). No SFT/RL-trained compression is implemented or planned.
**Notes**: This is a research-frontier technique requiring training infrastructure. The research doc identifies this as an "enhancement opportunity" (Section 3.2, Lesson 1: "Compression before retrieval"). ADR-0013 defers RL-driven policies to future work. **Severity: LOW** -- the system functions well without this; it is an optimization for retrieval precision.

---

### Pattern 12: Atomic Topic Modeling (HiMeS LTM 16-Category Partitioning)
**Research Requirement**: HiMeS partitions user queries into 16 categories with subcategories for hierarchical tree indexing in long-term memory.
**Status**: PARTIAL
**Evidence**:
- Event type taxonomy provides structured categorization: `src/context_graph/domain/models.py:32-61` -- `EventType` enum with hierarchical dot-namespacing (agent.invoke, tool.execute, llm.chat, etc.).
- Preference categories provide user-knowledge partitioning: `src/context_graph/domain/models.py:190-199` -- `PreferenceCategory` with 6 categories (tool, workflow, communication, domain, environment, style).
- Entity type hierarchy: `src/context_graph/domain/models.py:63-76` -- `EntityType` with 6 types (agent, user, service, tool, resource, concept).
- No formal 16-category topic modeling or hierarchical tree indexing of queries.
**Notes**: The system has structured categorization but not HiMeS-style topic modeling. The combination of event types + entity types + preference categories provides equivalent organizational structure.

---

### Pattern 13: Attention-Inspired Re-Ranking (HiMeS LTM)
**Research Requirement**: Re-rank retrieved documents by computing attention scores: `score_i = mean(sim(embed(chunk_i), embed(history)))`. Historical patterns enhance current retrieval.
**Status**: PARTIAL
**Evidence**:
- Relevance scoring via cosine similarity exists: `src/context_graph/domain/scoring.py:65-81` -- `compute_relevance_score()`.
- User affinity considers retrieval history: `src/context_graph/domain/scoring.py:185-196` -- `compute_user_affinity()` with session_proximity, retrieval_recurrence, entity_overlap.
- Intent-weighted edge boosting during subgraph traversal: `neo4j/store.py:504-518` -- neighbor scores boosted by intent edge weight.
- No explicit attention-based re-ranking over historical queries.
**Notes**: The composite scoring (recency + importance + relevance + user_affinity) serves a similar purpose to attention-inspired re-ranking but is not a direct implementation.

---

### Pattern 14: Pre-Retrieval Mechanism (HiMeS)
**Research Requirement**: The STM rewriter triggers document retrieval proactively -- anticipatory memory access similar to hippocampal pre-activation.
**Status**: PARTIAL
**Evidence**:
- Proactive context surfacing implemented: `neo4j/store.py:519-532` -- nodes reached through graph traversal marked as `retrieval_reason: "proactive"` with `proactive_signal` (e.g., "recurring_pattern", "entity_context", "causal_chain").
- Meta includes `proactive_nodes_count`: `models.py:492`.
- No anticipatory pre-retrieval before the query is fully formed.
**Notes**: The system surfaces proactive context during retrieval but does not pre-retrieve before the query arrives. The proactive_signal mechanism is a form of pre-activation at retrieval time.

---

### Paper 3.3 (HiCL): Hippocampal-Inspired Continual Learning

---

### Pattern 15: Hippocampal Circuit Mapping (EC -> DG -> CA3 -> CA1)
**Research Requirement**: Map the trisynaptic circuit: Entorhinal Cortex (grid-cell encoding), Dentate Gyrus (pattern separation), CA3 (pattern completion), CA1 (integration).
**Status**: PARTIAL
**Evidence**:
- EC (structured encoding): Events encoded through multiple lenses -- temporal (occurred_at), semantic (embedding), relational (edges), importance (importance_score). EventNode at `models.py:289-307`.
- DG (pattern separation): Each event has unique UUID + global_position + rich provenance (agent_id, session_id, trace_id). Even identical events are distinguished: `models.py:253-281`.
- CA3 (pattern completion): Lineage queries reconstruct full context from partial cues: `neo4j/store.py:357-428` -- given one node_id, traverse CAUSED_BY chains to recover full provenance.
- CA1 (integration): Atlas response merges all signals: `models.py:506-515` -- nodes + edges + pagination + meta with scores, intents, seeds, capacity.
- No explicit sparse 5% activation or MoE routing.
**Notes**: The conceptual mapping holds but the specific mathematical operations (TopK sparsity, MLP completion, MoE gating) are not implemented -- they are neural network techniques not applicable to a graph database system.

---

### Pattern 16: Grid-Cell Encoding (Multi-Scale Representations)
**Research Requirement**: Encode information through multiple parallel "lenses" (sinusoidal basis functions) to create structured, discriminative representations.
**Status**: PARTIAL
**Evidence**:
- Events are encoded through multiple independent lenses:
  - Temporal: `occurred_at` timestamp, FOLLOWS edges with `delta_ms` (`projection.py:67-82`)
  - Semantic: `embedding` property (list[float]) on EventNode (`models.py:304`)
  - Relational: 16 edge types across 4 orthogonal views (`models.py:78-107`)
  - Importance: `importance_score` 1-10 scale (`models.py:305`)
  - Keywords: `keywords` list (`models.py:302`)
- No sinusoidal basis functions or grid-cell-style encoding.
**Notes**: The multi-lens encoding principle is followed conceptually through the rich node properties and multi-edge-type graph. The mathematical grid-cell implementation is not applicable to this architecture.

---

### Pattern 17: Dentate Gyrus Pattern Separation
**Research Requirement**: Similar inputs mapped to orthogonal representations to prevent confusion. Sparse, quasi-orthogonal codes with 5% activation.
**Status**: COMPLIANT
**Evidence**:
- UUID-based event_id ensures uniqueness: `models.py:263` -- every event has a unique UUID.
- Global_position provides total ordering: `models.py:270-273` -- Redis Stream entry ID.
- Rich provenance metadata disambiguates near-identical events: `models.py:264-268` (event_type, occurred_at, session_id, agent_id, trace_id).
- Entity resolution maintains distinct identities: `entity_resolution.py:94-129` -- exact match only MERGEs when both name AND type match; type mismatch produces SAME_AS edge (preserving distinction).
- Neo4j uniqueness constraints prevent node conflation: `queries.py:16-28` -- CONSTRAINT event_pk, entity_pk, summary_pk.
**Notes**: Pattern separation is achieved through UUID uniqueness, rich provenance, and strict entity resolution -- not through sparse neural coding, but the functional outcome is the same: similar-but-distinct events are never confused.

---

### Pattern 18: CA3 Pattern Completion
**Research Requirement**: Reconstruct complete memory patterns from partial cues -- content-addressable memory.
**Status**: COMPLIANT
**Evidence**:
- Lineage query reconstructs full causal chain from a single node: `neo4j/store.py:357-428` -- given one event_id, traverse CAUSED_BY chains to recover all ancestors.
- Session context assembly reconstructs full session from session_id: `neo4j/store.py:301-355` and `queries.py:225-228`.
- Subgraph query expands from seed nodes to full neighborhood: `neo4j/store.py:483-545` -- for each seed, traverse all neighbor edges.
- Entity lookup returns entity + all connected events: `neo4j/store.py:587-614` and `queries.py:254-260`.
**Notes**: Graph traversal IS pattern completion -- partial cues (a node ID) activate the full relevant subgraph.

---

### Pattern 19: DG-Gated Mixture of Experts (Task Routing)
**Research Requirement**: Different circuits specialize for different memory types. DG routes inputs to appropriate expert circuits based on similarity to prototypes.
**Status**: PARTIAL
**Evidence**:
- Event-type-based routing: Different event types trigger different processing in the 4-consumer architecture. `system.session_end` triggers Consumer 2 extraction (`worker/extraction.py:90-133`). All events go through Consumer 1 (projection) and Consumer 3 (enrichment). Consolidation triggers go to Consumer 4 (`worker/consolidation.py:73-79`).
- Intent-based query routing: Different query intents weight different edge types: `settings.py:163-253` -- INTENT_WEIGHTS matrix with 8 intents x 16 edge types.
- Seed strategy selection: `domain/intent.py:48-56` -- `_SEED_STRATEGIES` maps dominant intent to seed selection approach (causal_roots, temporal_anchors, entity_hubs, etc.).
- No prototype-based gating or similarity-to-expert routing.
**Notes**: The 4-consumer architecture provides specialized processing pipelines by event type/trigger. Intent-weighted retrieval provides query routing. Not a full MoE implementation but the functional outcome (specialized processing) is achieved.

---

### Pattern 20: Elastic Weight Consolidation (EWC)
**Research Requirement**: Important learned patterns should be protected during consolidation. Important synaptic connections are more resistant to change.
**Status**: COMPLIANT
**Evidence**:
- High-importance nodes resist pruning: `forgetting.py:77-92` -- cold tier only prunes nodes with importance < 5 AND access_count < 3.
- Access frequency protects nodes: `forgetting.py:92` -- meeting EITHER importance OR access threshold saves the node.
- Summary nodes preserve information before pruning: `worker/consolidation.py:195-236` -- episode + session summaries created BEFORE forgetting runs.
- Centrality-based importance update protects hub nodes: `maintenance.py:106-117` -- high in-degree nodes get boosted importance (10 for >= 10 edges).
- Configurable retention thresholds: `settings.py:97-112` -- all tier boundaries and minimum thresholds are tunable.
**Notes**: EWC's core principle (protect important, allow unimportant to drift) is implemented through importance-weighted retention tiers.

---

### Pattern 21: Catastrophic Forgetting Prevention
**Research Requirement**: Three-pronged prevention: (1) sparse separation, (2) prototype-based gating, (3) replay + consolidation.
**Status**: COMPLIANT
**Evidence**:
- **Separation**: UUID-unique events, entity resolution prevents conflation (`entity_resolution.py`, `queries.py:16-28`).
- **Routing**: Event-type routing to specialized consumers, intent-based query routing (`intent.py:59-80`, `settings.py:163-253`).
- **Replay + Consolidation**: 4-consumer pipeline with continuous projection (Consumer 1), periodic re-consolidation (Consumer 4), summary creation before pruning (`worker/consolidation.py:195-236`), and centrality-based importance reinforcement (`maintenance.py:384-408`).
- Immutable event ledger as ultimate protection: Redis never mutates events -- worst case, full re-projection rebuilds the graph.
**Notes**: The immutable event ledger provides an additional safety net not available in neural network systems: catastrophic forgetting in Neo4j is fully recoverable via re-projection.

---

### Cross-Paper Synthesis: 8 Patterns

---

### Pattern 22: Dual-Store CLS Architecture
**Research Requirement**: All three papers validate CLS. Fast system for rapid detailed encoding, slow system for gradual abstraction.
**Status**: COMPLIANT
**Evidence**: (Same as Patterns 1 and 2 above)
- Redis (fast/flexible): `adapters/redis/store.py`
- Neo4j (slow/stable): `adapters/neo4j/store.py`
- Projection worker (consolidation): `worker/projection.py`
- ADR-0003 amendment formally documents the CLS mapping.

---

### Pattern 23: Memory Replay and Consolidation
**Research Requirement**: Projection worker implements replay; enhancement opportunity for periodic re-consolidation.
**Status**: COMPLIANT
**Evidence**: (Same as Pattern 4)
- Continuous replay: `worker/projection.py`
- Periodic re-consolidation: `worker/consolidation.py:81-163`
- Reflection trigger: `domain/consolidation.py:26-31`
- Hierarchical summarization: episode -> session -> agent level (`worker/consolidation.py:105-154`)

---

### Pattern 24: Hippocampal Indexing (Sparse Pointers)
**Research Requirement**: Events contain pointers (payload_ref, parent_event_id), not full content. Graph nodes are structural indices.
**Status**: COMPLIANT
**Evidence**:
- `payload_ref` field: `models.py:269` -- reference to full payload, not payload itself.
- `parent_event_id` for causal chains: `models.py:277`.
- Graph nodes store type/attributes/provenance: `models.py:454-463` (AtlasNode).
- Summary nodes serve as hierarchical indices: `models.py:321-330` (SummaryNode with scope, scope_id, event_count).

---

### Pattern 25: Pattern Separation and Completion
**Research Requirement**: Separation: unique identities for distinct events. Completion: reconstruct full context from partial cues.
**Status**: COMPLIANT
**Evidence**: (Same as Patterns 17 and 18)
- Separation: UUID event_id, global_position, rich provenance, uniqueness constraints.
- Completion: Lineage traversal, session reconstruction, subgraph expansion.

---

### Pattern 26: Forgetting as Active Process
**Research Requirement**: Ebbinghaus curve R = e^(-t/S), adaptive forgetting, spaced repetition.
**Status**: COMPLIANT
**Evidence**: (Same as Pattern 8)
- `scoring.py:46` -- `math.exp(-t_hours / stability)`
- Stability grows with access: `stability = s_base + (access_count * s_boost)`
- 4-tier retention: `forgetting.py:32-58`

---

### Pattern 27: Working Memory Capacity Management
**Research Requirement**: Bounded queries, priority-based context assembly, chunking.
**Status**: COMPLIANT
**Evidence**: (Same as Pattern 5)
- Bounded queries: `lineage.py:12-27`, `settings.py:115-127`
- Priority-based assembly: decay-scored ranking in `neo4j/store.py:326-328`
- Pagination: `models.py:499-503`
- Episode grouping (chunking): `consolidation.py:35-70` -- `group_events_into_episodes()` with configurable gap_minutes

---

### Pattern 28: Reconsolidation on Retrieval
**Research Requirement**: Graph projection updated on query; access_count, last_accessed_at, stability factor updated. Immutable events preserved.
**Status**: COMPLIANT
**Evidence**: (Same as Pattern 7)
- `_bump_access_counts()`: `neo4j/store.py:288-299`
- `BATCH_UPDATE_ACCESS_COUNT`: `queries.py:268-273`
- Stability grows implicitly via s_boost * access_count in scoring formula
- Redis event ledger remains immutable

---

### Pattern 29: Multi-Expert Routing
**Research Requirement**: Different event types trigger different projection strategies; different query types route to different algorithms.
**Status**: PARTIAL
**Evidence**: (Same as Pattern 19)
- 4 specialized consumer groups
- Intent-weighted edge traversal with 8 intent types
- Seed strategy selection per intent
**Notes**: Functional routing exists but not a full MoE architecture with learned gating.

---

## Architectural Recommendations Compliance

---

### Recommendation 1: Formalize the CLS Architecture
**Research Requirement**: Document Redis as hippocampal, Neo4j as neocortical, projection worker as consolidation.
**Status**: COMPLIANT
**Evidence**: ADR-0003 amendment explicitly documents this mapping. ADR-0008 references the biological model. The research document's recommendation is fully realized in the ADR text.

---

### Recommendation 2: Implement Hierarchical Summarization
**Research Requirement**: Add summarization layers: event -> episode -> session -> agent.
**Status**: COMPLIANT
**Evidence**:
- Episode-level summaries: `worker/consolidation.py:195-216` -- grouped by temporal gaps, summary per episode.
- Session-level summaries: `worker/consolidation.py:218-236` -- session_summary covers all events.
- Agent-level summaries: `worker/consolidation.py:108-154` -- cross-session agent summaries.
- SummaryNode model with scope field: `models.py:321-330` -- scope can be "episode", "session", or "agent".
- SUMMARIZES edges link summaries to events: `maintenance.py:119-134`, `129-134`.

---

### Recommendation 3: Add Importance Scoring and Temporal Decay
**Research Requirement**: Base importance, access frequency, temporal decay formula, query-time scoring.
**Status**: COMPLIANT
**Evidence**:
- Base importance from hint: `scoring.py:59` -- defaults to 0.5 when no hint.
- Access frequency boost: `scoring.py:60` -- `min(0.2, log1p(access_count) * 0.05)`.
- Temporal decay: `scoring.py:46` -- `exp(-t_hours / stability)`.
- Query-time composite scoring: `scoring.py:84-104` -- weighted sum normalized by total weight.
- User affinity as 4th factor: `scoring.py:185-196`.

---

### Recommendation 4: Implement Replay/Re-Consolidation
**Research Requirement**: Periodic re-consolidation, cross-event relationship discovery, priority replay, idle-time execution.
**Status**: COMPLIANT
**Evidence**:
- Configurable schedule (default 6h): `settings.py:94` -- `reconsolidation_interval_hours: int = 6`.
- Re-consolidation in Consumer 4: `worker/consolidation.py:81-163`.
- Cross-event discovery via summary creation from episodes.
- Priority processing: high-importance sessions consolidated first via reflection trigger threshold check.

---

### Recommendation 5: Bounded Context Assembly (Working Memory)
**Research Requirement**: Enforce limits, chunk related events, rank by combined relevance, return top-k with pagination.
**Status**: COMPLIANT
**Evidence**:
- Hard limits: `settings.py:119-126` (max_max_depth=10, max_max_nodes=500, max_timeout_ms=30000).
- Episode chunking: `consolidation.py:35-70`.
- Ranked by decay score: `neo4j/store.py:326-328`.
- Pagination: `models.py:499-503`.

---

### Recommendation 6: Pattern Separation in Event Storage (30th pattern)
**Research Requirement**: UUID-based event_id, rich provenance metadata, idempotent ingestion.
**Status**: COMPLIANT
**Evidence**:
- UUID event_id: `models.py:263`.
- Rich provenance: session_id, agent_id, trace_id, occurred_at (`models.py:264-268`).
- Idempotent ingestion via Lua dedup script: `redis/store.py:157-168` -- uses dedup sorted set.
- Uniqueness constraints in Neo4j: `queries.py:16-28`.

---

## ADR Alignment

| ADR | Research Patterns Addressed |
|-----|---------------------------|
| ADR-0001 | Bounded queries (Pattern 5/27), provenance pointers (Pattern 24), immutable events (Pattern 1/22) |
| ADR-0003 | CLS dual-store architecture (Patterns 1, 2, 22), cognitive role mapping |
| ADR-0004 | Event schema with importance_hint (Pattern 6), payload_ref indexing (Pattern 24) |
| ADR-0005 | Projection worker as consolidation process (Patterns 1, 4, 23), replay support |
| ADR-0008 | Ebbinghaus decay (Pattern 8/26), reconsolidation (Pattern 7/28), forgetting tiers (Pattern 8/26), replay/re-consolidation (Pattern 4/23), reflection trigger, hierarchical summarization (Rec 2) |
| ADR-0009 | Multi-graph schema (Pattern 19/29), intent-aware retrieval, pattern completion via lineage (Pattern 18/25), working memory bounds (Pattern 5/27) |
| ADR-0010 | Redis as hippocampal fast store (Pattern 1/22), consumer groups as consolidation mechanism |
| ADR-0011 | Entity type hierarchy (Pattern 12), entity resolution for separation (Pattern 17/25) |
| ADR-0012 | User personalization nodes (Patterns 6, 10), preference stability/decay integration |
| ADR-0013 | 4-consumer extraction pipeline (Patterns 4, 19, 29), LLM-based knowledge extraction, provenance via DERIVED_FROM |

---

## Gap Analysis

### GAP 1: RL-Trained Query Compression (HiMeS Pattern)
- **Severity**: LOW
- **Pattern**: Pattern 11 -- RL-trained STM module that compresses dialogue into refined retrieval queries
- **Current State**: No query compression. Raw query text goes directly to intent classification via keyword matching (`domain/intent.py:59-80`).
- **Suggested Remediation**: This is a research-frontier technique. Could be approximated by:
  1. Adding an LLM-based query rewriting step before intent classification
  2. Using the existing embedding infrastructure (once implemented) for query-to-node matching
  3. Long-term: RL optimization of query rewriting using retrieval success as reward signal
- **Priority**: Post-MVP. The system functions well without this; it is a retrieval precision optimization.

### GAP 2: Embedding Computation and SIMILAR_TO Edge Creation
- **Severity**: MEDIUM
- **Pattern**: Patterns 13, 16 (attention-based re-ranking, multi-scale encoding) and cross-cutting (SIMILAR_TO edges are defined but not created)
- **Current State**: `EnrichmentConsumer` (`worker/enrichment.py:108-110`) has TODO comments for embedding computation and SIMILAR_TO edge creation. The `EventNode.embedding` field exists (`models.py:304`). The `MERGE_SIMILAR_TO` query exists (`queries.py:99-104`). The `compute_relevance_score()` function exists (`scoring.py:65-81`). But no embedding model is integrated and no SIMILAR_TO edges are actually created.
- **Suggested Remediation**:
  1. Integrate `sentence-transformers` (all-MiniLM-L6-v2) in Consumer 3
  2. Compute embeddings for each event's content
  3. Create SIMILAR_TO edges when cosine similarity > 0.85 (threshold already configured: `settings.py:88`)
  4. This unlocks the semantic view of the multi-graph and enables proper relevance scoring
- **Priority**: HIGH. Multiple neuroscience patterns (semantic similarity, attention-inspired re-ranking, multi-scale encoding) depend on embeddings being computed.

### PARTIAL Items (not full gaps but with room for improvement)

1. **Atomic Topic Modeling** (Pattern 12): The system has event types and preference categories but no formal topic-based partitioning. Consider adding a topic classification step in Consumer 2/3.

2. **Attention-Inspired Re-Ranking** (Pattern 13): Composite scoring serves a similar purpose but could be enhanced with explicit historical query context. The `user_affinity` sub-components (`scoring.py:185-196`) are defined but the actual computation of session_proximity, retrieval_recurrence, and entity_overlap from graph data is not yet wired up in query paths.

3. **Pre-Retrieval Mechanism** (Pattern 14): Proactive context surfacing exists at retrieval time but no anticipatory pre-retrieval before query arrival.

4. **Multi-Expert Routing** (Pattern 19/29): Functional routing through 4 consumers + intent weights, but no learned gating or prototype-based routing.

---

## Summary

The Engram codebase demonstrates exceptionally strong alignment with the neuroscience memory patterns from Cluster 3. The CLS dual-store architecture, Ebbinghaus decay scoring, multi-tier forgetting, hierarchical summarization, reconsolidation on retrieval, bounded working-memory queries, and pattern separation/completion are all implemented with clear traceability to the research. The two gaps (RL-trained query compression and embedding computation) are both acknowledged in the codebase (via TODOs) and in the ADRs (as future work items). The medium-severity gap (embeddings) should be prioritized as it unlocks the semantic dimension of the multi-graph schema that multiple neuroscience patterns depend on.
