# Cluster 2: Memory Architectures -- Compliance Audit

## Executive Summary

- **Total patterns checked**: 52
- **COMPLIANT**: 32
- **PARTIAL**: 14
- **GAP**: 6

The Engram codebase demonstrates strong alignment with the Cluster 2 research across memory tier architecture, decay scoring, consolidation, and the three-system model. The dual-store (Redis + Neo4j) architecture faithfully implements the Complementary Learning Systems (CLS) pattern. Scoring, forgetting, and tiered retention are well-implemented. Key gaps concentrate in three areas: (1) incomplete enrichment pipeline (embeddings, SIMILAR_TO edges, REFERENCES edges not yet implemented), (2) procedural memory / experiential hierarchy not yet modeled, and (3) LLM extraction client is a skeleton without actual API calls.

---

## Pattern-by-Pattern Audit

### Paper 2.1: Memory in the Age of AI Agents (Hu et al., 2025)

---

### Pattern 1: Three-Lens Framework (Forms, Functions, Dynamics)

**Research Requirement**: Memory should be understood through three lenses: Forms (how realized), Functions (what it stores), and Dynamics (lifecycle operators).

**Status**: COMPLIANT

**Evidence**:
- **Forms**: The system uses Token-Level Planar/Hierarchical memory via Neo4j graph (nodes, edges, hierarchical summaries). `src/context_graph/domain/models.py:136-150` defines 8 node types. `src/context_graph/domain/models.py:78-107` defines 16 edge types.
- **Functions**: Factual memory (entity nodes, knowledge graph), Experiential memory (event traces, workflow nodes), Working memory (context API response).
- **Dynamics**: Formation (event ingestion + validation), Evolution (consolidation worker, decay scoring, forgetting), Retrieval (intent-aware subgraph query, context assembly).

**Notes**: The three-lens framework is the organizational backbone of the architecture, formalized in ADR-0007 and ADR-0008.

---

### Pattern 2: Token-Level Memory (Flat / Planar / Hierarchical)

**Research Requirement**: Token-level memory should support flat (linear logs), planar (graphs), and hierarchical (multi-level) structures.

**Status**: COMPLIANT

**Evidence**:
- **Flat**: Redis Streams provide linear, append-only event logs. `src/context_graph/adapters/redis/store.py:143-179` (append method).
- **Planar**: Neo4j graph with typed edges provides relational structure. `src/context_graph/adapters/neo4j/queries.py:85-195` (16 edge type MERGE queries).
- **Hierarchical**: Summary nodes at episode/session/agent scope create multi-level abstraction. `src/context_graph/domain/consolidation.py:73-116` (create_summary_from_events with scope parameter). `src/context_graph/worker/consolidation.py:195-236` creates episode-level, session-level, and agent-level summaries.

---

### Pattern 3: Formation Operator (Active Transformation)

**Research Requirement**: Formation is "active transformation" not passive logging -- summarization, distillation, structuring, latent embedding.

**Status**: PARTIAL

**Evidence**:
- **Structuring**: Event validation and projection transform raw events into graph nodes/edges. `src/context_graph/domain/projection.py:101-123` (project_event).
- **Summarization**: Consolidation creates summary nodes. `src/context_graph/domain/consolidation.py:73-116`.
- **Distillation**: Keyword extraction from event types. `src/context_graph/worker/enrichment.py:113-122`.
- **Latent embedding**: NOT IMPLEMENTED. `src/context_graph/worker/enrichment.py:108` has `# TODO: Embedding computation (requires sentence-transformers, Phase 3+)`.

**Notes**: Missing embedding computation means the formation operator lacks the latent representation channel. This is a known TODO.

---

### Pattern 4: Evolution Operator -- Consolidation (Local / Cluster / Global)

**Research Requirement**: Three levels of consolidation: local (within-cluster merging), cluster (cross-subset aggregation), global (full-store reorganization).

**Status**: COMPLIANT

**Evidence**:
- **Local**: Episode-level summaries merge closely related events within a session. `src/context_graph/worker/consolidation.py:186-216` groups events into episodes by temporal gaps and creates per-episode summaries.
- **Cluster**: Session-level summaries aggregate across episodes. `src/context_graph/worker/consolidation.py:218-236` creates session-level summary.
- **Global**: Agent-level summaries span multiple sessions. `src/context_graph/worker/consolidation.py:109-154` creates agent-level summaries from all qualifying sessions. Also, importance recomputation from centrality at `src/context_graph/worker/consolidation.py:244-251`.

---

### Pattern 5: Evolution Operator -- Forgetting Strategies

**Research Requirement**: Five forgetting strategies: temporal decay, selective removal, adaptive policies, deduplication, periodic pruning.

**Status**: PARTIAL

**Evidence**:
- **Temporal decay**: Ebbinghaus curve implemented. `src/context_graph/domain/scoring.py:22-46` (compute_recency_score with e^(-t/S)).
- **Selective removal**: Cold-tier pruning based on importance AND access count. `src/context_graph/domain/forgetting.py:77-92` (should_prune_cold). `src/context_graph/adapters/neo4j/maintenance.py:178-220` (delete_cold_events).
- **Periodic pruning**: Consolidation consumer runs on 6-hour schedule. `src/context_graph/worker/consolidation.py:253-302` (_run_forgetting). Redis stream trimming at `src/context_graph/adapters/redis/trimmer.py:23-62`.
- **Deduplication**: Event-level dedup via Lua script sorted set. `src/context_graph/adapters/redis/store.py:143-179`.
- **Adaptive policies**: NOT IMPLEMENTED. No RL-driven or learning-based forgetting policies.

**Notes**: 4 of 5 strategies implemented. Adaptive (RL-driven) forgetting is explicitly deferred in ADR-0008 as a future optimization. This is a reasonable deferral given the research notes it requires training data from production usage.

---

### Pattern 6: Evolution Operator -- Updating (Conflict Resolution)

**Research Requirement**: Explicit revision mechanisms with rollback and audit trails, conflict resolution when new info contradicts existing memories.

**Status**: PARTIAL

**Evidence**:
- **Immutable events**: Source events are never mutated. `src/context_graph/adapters/redis/store.py` -- append-only.
- **Graph evolution**: Neo4j node properties (importance_score, access_count, last_accessed_at) are updated during enrichment and reconsolidation. `src/context_graph/adapters/neo4j/queries.py:262-279` (access count updates, enrichment updates).
- **Preference supersession**: `superseded_by` field on PreferenceNode. `src/context_graph/domain/models.py:370`.
- **Conflict resolution**: NOT EXPLICITLY IMPLEMENTED. No mechanism for detecting and resolving contradictions between old and new preferences beyond the superseded_by pointer.

**Notes**: The immutable event ledger provides implicit audit trails. Preference evolution via `superseded_by` is a basic form of updating. Full conflict resolution logic is not yet implemented.

---

### Pattern 7: Retrieval Operator -- Multi-Strategy

**Research Requirement**: Retrieval should support lexical, semantic, graph-based, generative, and hybrid strategies.

**Status**: PARTIAL

**Evidence**:
- **Graph-based**: Intent-aware traversal with edge-type-specific weights. `src/context_graph/adapters/neo4j/store.py:430-585` (get_subgraph with intent classification, seed node selection, neighbor traversal).
- **Lexical**: Keyword-based RediSearch queries. `src/context_graph/adapters/redis/store.py:256-288` (search with TAG filters).
- **Semantic**: NOT IMPLEMENTED. SIMILAR_TO edges not yet created (embedding computation TODO). `src/context_graph/worker/enrichment.py:109`.
- **Generative**: NOT IMPLEMENTED. No synthesis-based retrieval.
- **Hybrid**: Partial -- the system combines graph traversal with decay scoring but lacks the semantic/embedding component.

**Notes**: Graph-based retrieval is the strongest implemented strategy. Semantic retrieval is blocked on embedding computation.

---

### Pattern 8: Retrieval -- Proactive vs. Reactive

**Research Requirement**: Retrieval should support both proactive (system-initiated) and reactive (query-driven) modes.

**Status**: COMPLIANT

**Evidence**:
- **Reactive**: Standard query-driven retrieval via `/v1/query/subgraph` and `/v1/context/{session_id}`. `src/context_graph/api/routes/query.py:26-36`, `src/context_graph/api/routes/context.py:24-33`.
- **Proactive**: System surfaces contextually useful nodes not directly queried. `src/context_graph/adapters/neo4j/store.py:519-532` marks neighbor nodes as `retrieval_reason="proactive"` with `proactive_signal` values like "entity_context", "recurring_pattern", "causal_chain".
- **Response marking**: `src/context_graph/domain/models.py:462-463` -- AtlasNode has `retrieval_reason` ("direct" | "proactive") and `proactive_signal` fields.
- **Meta reporting**: `src/context_graph/domain/models.py:492` -- QueryMeta includes `proactive_nodes_count`.

---

### Pattern 9: Experiential Memory Hierarchy (Case -> Strategy -> Skill)

**Research Requirement**: Three-tier hierarchy of increasing abstraction: case-based (raw traces), strategy-based (abstracted workflows), skill-based (executable procedures).

**Status**: PARTIAL

**Evidence**:
- **Case-based**: Event traces are fully captured as immutable records. Redis event store + Neo4j Event nodes.
- **WorkflowAbstractionLevel enum**: `src/context_graph/domain/models.py:209-215` defines `CASE`, `STRATEGY`, `SKILL` levels matching the research hierarchy exactly.
- **WorkflowNode model**: `src/context_graph/domain/models.py:385-398` includes `abstraction_level`, `success_rate`, `execution_count`, `embedding`.
- **ABSTRACTED_FROM edge**: `src/context_graph/domain/models.py:106` links workflows at different abstraction levels.

**Gap**: The models exist but no extraction or detection logic populates them. Consumer 4 (consolidation) does not yet implement workflow detection. `src/context_graph/worker/consolidation.py` contains no workflow creation logic.

**Notes**: Schema is fully prepared (models, enums, edge types, Cypher MERGE templates at `src/context_graph/adapters/neo4j/queries.py:183-188`). Implementation of actual workflow detection/abstraction is a TODO.

---

### Pattern 10: Working Memory -- Capacity-Limited Scratchpad

**Research Requirement**: Working memory should be actively managed, capacity-limited, and support interference control with five patterns (input condensation, observation abstraction, state consolidation, hierarchical folding, plan-centric representations).

**Status**: PARTIAL

**Evidence**:
- **Capacity-limited**: Context API enforces `max_nodes` (default 100, max 500). `src/context_graph/api/routes/context.py:28-29`.
- **Priority-ranked**: Results sorted by composite decay score. `src/context_graph/adapters/neo4j/store.py:327-328`.
- **Input condensation**: Summary nodes compress event clusters. `src/context_graph/domain/consolidation.py:73-116`.
- **Hierarchical folding**: Three-level summaries (episode, session, agent). `src/context_graph/worker/consolidation.py:195-236`.

**Missing**: Observation abstraction, state consolidation, and plan-centric representations are not explicitly implemented. The working memory is assembled per-request but does not persist state between assemblies.

---

### Paper 2.2: Rethinking Memory Mechanisms (Huang et al., 2026)

---

### Pattern 11: Five Cognitive Memory Types

**Research Requirement**: Sensory, Working, Episodic, Semantic, Procedural memory types with distinct characteristics.

**Status**: COMPLIANT

**Evidence**: ADR-0007 explicitly maps all five types to system components:
- **Sensory**: API ingestion buffer (transient, sub-second). Implicit in FastAPI request lifecycle.
- **Working**: Context API response. `src/context_graph/api/routes/context.py` + `src/context_graph/adapters/neo4j/store.py:301-355`.
- **Episodic**: Redis event store. `src/context_graph/adapters/redis/store.py` (immutable, instance-specific, temporal ordering).
- **Semantic**: Neo4j graph projection. `src/context_graph/adapters/neo4j/store.py` (derived relational knowledge, multi-hop traversal).
- **Procedural**: Workflow/BehavioralPattern nodes. `src/context_graph/domain/models.py:385-412` (models defined, implementation deferred).

**Notes**: All five types are architecturally mapped. Procedural memory has schema support but no population logic.

---

### Pattern 12: Memory Operations Framework

**Research Requirement**: Five core operations: Storage/Index, Loading/Retrieval, Updates/Refresh, Compression/Summarization, Forgetting/Retention.

**Status**: COMPLIANT

**Evidence**:
- **Storage/Index**: Redis JSON + RediSearch indexing. `src/context_graph/adapters/redis/indexes.py`. Neo4j MERGE with uniqueness constraints. `src/context_graph/adapters/neo4j/queries.py:16-28`.
- **Loading/Retrieval**: Context assembly, subgraph query, lineage traversal. `src/context_graph/adapters/neo4j/store.py:301-585`.
- **Updates/Refresh**: Access count increment, importance recomputation from centrality. `src/context_graph/adapters/neo4j/store.py:288-299`. `src/context_graph/adapters/neo4j/maintenance.py:384-408`.
- **Compression/Summarization**: Episode/session/agent summary creation. `src/context_graph/domain/consolidation.py:73-116`. `src/context_graph/worker/consolidation.py:165-236`.
- **Forgetting/Retention**: Tiered retention with warm edge pruning, cold node deletion, archive removal. `src/context_graph/domain/forgetting.py:32-161`. `src/context_graph/worker/consolidation.py:253-302`.

---

### Pattern 13: Context Explosion Problem

**Research Requirement**: Dynamic memory architectures capable of intelligent store, load, summarize, forget, and refine operations to handle exponentially growing context.

**Status**: COMPLIANT

**Evidence**: The four-tier retention system (HOT/WARM/COLD/ARCHIVE) with active forgetting directly addresses context explosion:
- **Store**: Redis Streams + JSON for fast capture. `src/context_graph/adapters/redis/store.py:143-179`.
- **Load**: Decay-scored retrieval surfaces relevant nodes. `src/context_graph/domain/scoring.py:107-182`.
- **Summarize**: Hierarchical summarization replaces pruned clusters. `src/context_graph/worker/consolidation.py:195-236`.
- **Forget**: Multi-tier pruning. `src/context_graph/worker/consolidation.py:253-302`.
- **Refine**: Reconsolidation on retrieval (access_count bump, stability increase). `src/context_graph/adapters/neo4j/store.py:288-299`.

---

### Pattern 14: Agent-Centric vs. User-Centric Memory

**Research Requirement**: Both agent-centric (task execution support) and user-centric (personalization, preference tracking) memory dimensions.

**Status**: COMPLIANT

**Evidence**:
- **Agent-centric**: Event nodes capture agent actions, tool executions, causal chains. All core graph functionality.
- **User-centric**: Full personalization ontology with 5 node types (UserProfile, Preference, Skill, Workflow, BehavioralPattern) and 9 relationship types. `src/context_graph/domain/models.py:338-412`. `src/context_graph/adapters/neo4j/user_queries.py`. `src/context_graph/api/routes/users.py`.

**Notes**: ADR-0012 defines the complete user-centric memory dimension. Consumer 2 (extraction worker) populates user knowledge. `src/context_graph/worker/extraction.py:192-261`.

---

### Pattern 15: Memory Lifecycle (7 stages)

**Research Requirement**: Acquisition, Consolidation, Storage, Retrieval, Integration, Update, Decay/Forgetting.

**Status**: COMPLIANT

**Evidence**:
- **Acquisition**: Event ingestion via `/v1/events` API. `src/context_graph/adapters/redis/store.py:143-179`.
- **Consolidation**: Three-stage pipeline. `src/context_graph/worker/projection.py` (Stage 1), `src/context_graph/worker/enrichment.py` (Stage 2), `src/context_graph/worker/consolidation.py` (Stage 3).
- **Storage**: Dual-store Redis + Neo4j. Both adapter implementations.
- **Retrieval**: Multi-endpoint retrieval. `src/context_graph/adapters/neo4j/store.py:301-585`.
- **Integration**: Context API assembles working memory from graph. `src/context_graph/adapters/neo4j/store.py:301-355`.
- **Update**: Enrichment updates, access count bumps, centrality-based importance recomputation. `src/context_graph/worker/enrichment.py:58-106`. `src/context_graph/adapters/neo4j/maintenance.py:384-408`.
- **Decay/Forgetting**: Ebbinghaus curve + tiered retention + active pruning. `src/context_graph/domain/scoring.py:22-46`. `src/context_graph/domain/forgetting.py:32-161`.

---

### Pattern 16: Inter-Memory Type Interactions (Episodic -> Semantic Consolidation)

**Research Requirement**: Directional flows: Sensory -> Working -> Long-term (Episodic/Semantic). Episodic consolidates into Semantic. Procedural informed by both.

**Status**: COMPLIANT

**Evidence**: The architecture exactly implements this flow:
- **Sensory -> Working**: Raw API request -> context assembly. FastAPI ingestion -> `/v1/context/{session_id}`.
- **Working -> Episodic**: Events persisted to Redis. `src/context_graph/adapters/redis/store.py:143-179`.
- **Episodic -> Semantic**: Projection worker transforms events into graph. `src/context_graph/worker/projection.py`. Consolidation creates summaries. `src/context_graph/worker/consolidation.py`.
- **Procedural**: WorkflowNode and BehavioralPattern models designed to be informed by event patterns. Schema supports this but population logic is not yet implemented.

---

### Paper 2.3: Episodic Memory is the Missing Piece (Pink et al., 2025)

---

### Pattern 17: Five Properties of Episodic Memory

**Research Requirement**: Long-Term Storage, Explicit Reasoning, Single-Shot Learning, Instance-Specific Memories, Contextual Relations.

**Status**: COMPLIANT

**Evidence**: This is explicitly mapped in ADR-0007 and fully implemented:
- **Long-Term Storage**: Immutable Redis event ledger with retention ceiling of 90 days. `src/context_graph/settings.py:57` (`retention_ceiling_days = 90`).
- **Explicit Reasoning**: Events queryable via API; inspectable via lineage endpoint. `src/context_graph/api/routes/query.py`, lineage routes.
- **Single-Shot Learning**: Each event captured once; idempotent dedup via Lua script. `src/context_graph/adapters/redis/store.py:143-179`.
- **Instance-Specific**: Each event has unique `event_id` (UUID). `src/context_graph/domain/models.py:263`.
- **Contextual Relations**: Events carry `session_id`, `trace_id`, `parent_event_id`, `agent_id`, `tool_name`. `src/context_graph/domain/models.py:253-281`.

---

### Pattern 18: Three-System Architecture (Working + Episodic + Semantic/Parametric)

**Research Requirement**: In-Context Memory (Working), External Memory (Episodic), Parametric Memory (Semantic). With Encoding (b), Retrieval (c), and Consolidation (a) flows.

**Status**: COMPLIANT

**Evidence**: ADR-0003 and ADR-0007 explicitly map to this architecture:
- **In-Context (Working)**: API context window per-request. `src/context_graph/api/routes/context.py`.
- **External (Episodic)**: Redis event ledger. `src/context_graph/adapters/redis/store.py`.
- **Parametric (Semantic)**: Neo4j graph projection. `src/context_graph/adapters/neo4j/store.py`.
- **Encoding (b)**: Event ingestion writes to Redis (fast, single-shot). `src/context_graph/adapters/redis/store.py:143-179`.
- **Retrieval (c)**: Graph queries reinstate episodes into context. `src/context_graph/adapters/neo4j/store.py:301-585`.
- **Consolidation (a)**: Projection + enrichment + re-consolidation pipeline. `src/context_graph/worker/projection.py`, `src/context_graph/worker/enrichment.py`, `src/context_graph/worker/consolidation.py`.

---

### Pattern 19: Episode Segmentation

**Research Requirement**: Segmenting continuous agent experience into episodes using temporal gaps, model surprise, or event boundaries.

**Status**: COMPLIANT

**Evidence**:
- **Temporal gap segmentation**: `src/context_graph/domain/consolidation.py:35-70` (group_events_into_episodes) splits event streams into episodes by configurable temporal gaps (default 30 minutes).
- **Session boundaries**: Session start/end events (`system.session_start`, `system.session_end`) provide natural episode boundaries. `src/context_graph/domain/models.py:53-54`.
- **Parent-child chains**: `parent_event_id` provides causal episode structure.

**Notes**: Surprise-based segmentation (using model perplexity) is not implemented but is acknowledged as a future enhancement in the research mapping.

---

### Pattern 20: Consolidation -- Episodic to Parametric/Semantic

**Research Requirement**: External memory contents periodically merge into parametric/semantic memory through replay and generalization.

**Status**: COMPLIANT

**Evidence**:
- **Periodic replay**: Consolidation consumer runs on 6-hour schedule. `src/context_graph/settings.py:94` (`reconsolidation_interval_hours = 6`).
- **Episodic -> Semantic**: Events from Redis are processed into Neo4j summaries, entity relationships, and importance scores. `src/context_graph/worker/consolidation.py:81-163`.
- **Generalization**: Summary nodes abstract from specific events to session/agent-level knowledge. `src/context_graph/domain/consolidation.py:73-116`.
- **Reflection trigger**: When accumulated importance exceeds threshold (150), triggers consolidation. `src/context_graph/domain/consolidation.py:26-32`. `src/context_graph/worker/consolidation.py:89-95`.

---

### Pattern 21: Consolidation Timing and Triggers

**Research Requirement**: Determining when to consolidate -- scheduled intervals, importance thresholds, event-driven.

**Status**: COMPLIANT

**Evidence**:
- **Scheduled**: 6-hour consolidation cycle. `src/context_graph/settings.py:94`.
- **Importance threshold**: Reflection trigger at sum=150. `src/context_graph/domain/consolidation.py:26-32`. `src/context_graph/worker/consolidation.py:89-95`.
- **Event-driven**: Session extraction triggers on `system.session_end` event. `src/context_graph/worker/extraction.py:90-133`. Mid-session extraction triggers every N turns. `src/context_graph/worker/extraction.py:68-88`.
- **On-demand**: Admin API reconsolidate endpoint. `src/context_graph/api/routes/admin.py:83-178`.

---

## Cross-Paper Synthesis

---

### Pattern 22: Unified Memory Taxonomy (By Form, Function, Cognitive Type, Subject)

**Research Requirement**: Comprehensive taxonomy covering Form (token/parametric/latent), Cognitive Function (5 types), Purpose (factual/experiential/working), and Subject (agent/user-centric).

**Status**: COMPLIANT

**Evidence**: All four taxonomic dimensions are represented:
- **By Form**: Token-level planar (Neo4j graph) and hierarchical (summaries). `src/context_graph/domain/models.py`.
- **By Cognitive Function**: 5 types mapped in ADR-0007. `src/context_graph/domain/models.py:127-133` (RetentionTier), `src/context_graph/domain/models.py:136-150` (NodeType).
- **By Purpose**: Factual (entity nodes), Experiential (event traces, workflow nodes), Working (context API).
- **By Subject**: Agent-centric (event/tool tracking) + User-centric (personalization ontology). `src/context_graph/domain/models.py:338-412`.

---

### Pattern 23: Memory Lifecycle -- Unified View (Capture/Store/Evolve/Access/Decay)

**Research Requirement**: Consistent lifecycle across all three papers: Capture, Store, Evolve, Access, Decay.

**Status**: COMPLIANT

**Evidence**: See Pattern 15 above. All five lifecycle stages are implemented with clear component mappings. The four async consumers (`src/context_graph/worker/`) implement the full lifecycle.

---

### Pattern 24: Multi-Level Consolidation (CLS Model)

**Research Requirement**: Fast encoding (hippocampal), Replay (hippocampal offline), Consolidation (neocortical slow integration), Generalization (cortical schema formation).

**Status**: COMPLIANT

**Evidence**:
- **Fast encoding**: Redis sub-millisecond XADD. `src/context_graph/adapters/redis/store.py:143-179`.
- **Replay**: Consumer 1 reads stream entries and projects to Neo4j. `src/context_graph/worker/projection.py:57-107`.
- **Consolidation**: Consumer 4 creates summaries, recomputes importance. `src/context_graph/worker/consolidation.py:81-163`.
- **Generalization**: Agent-level summaries abstract across sessions. `src/context_graph/worker/consolidation.py:109-154`. WorkflowNode abstraction levels (case->strategy->skill) model the generalization pathway. `src/context_graph/domain/models.py:209-215`.

**Notes**: ADR-0003 amendment explicitly maps Redis=hippocampus, Neo4j=neocortex, projection worker=systems consolidation.

---

### Pattern 25: Convergent Decay Strategies

**Research Requirement**: Six strategies: temporal decay, importance-weighted retention, relevance-based pruning, consolidation-driven forgetting, deduplication, RL-driven forgetting.

**Status**: PARTIAL

**Evidence**:
- **Temporal decay**: Ebbinghaus curve. `src/context_graph/domain/scoring.py:22-46`.
- **Importance-weighted retention**: Cold-tier nodes protected by importance >= 5 OR access_count >= 3. `src/context_graph/domain/forgetting.py:77-92`.
- **Relevance-based pruning**: Warm-tier SIMILAR_TO edges pruned below similarity 0.7. `src/context_graph/domain/forgetting.py:61-74`.
- **Consolidation-driven forgetting**: Summary nodes created before clusters are pruned. `src/context_graph/worker/consolidation.py:253-263` ensures summaries exist before pruning.
- **Deduplication**: Event-level dedup via sorted set. `src/context_graph/adapters/redis/store.py:189-214`.
- **RL-driven forgetting**: NOT IMPLEMENTED. Explicitly deferred in ADR-0008.

**Notes**: 5 of 6 strategies implemented. RL-driven forgetting requires production training data.

---

## Concrete Algorithms and Scoring Functions

---

### Pattern 26: Park et al. Three-Factor Retrieval Scoring

**Research Requirement**: `score = alpha_recency * recency + alpha_importance * importance + alpha_relevance * relevance` with equal default weights.

**Status**: COMPLIANT

**Evidence**:
- **Formula**: `src/context_graph/domain/scoring.py:84-104` implements `compute_composite_score` with `w_recency`, `w_importance`, `w_relevance` (all default 1.0).
- **Plus extension**: Fourth factor `w_user_affinity` (default 0.5) per ADR-0008 amendment. `src/context_graph/domain/scoring.py:88,95-103`.
- **Settings**: `src/context_graph/settings.py:81-85` configures all four weights.

---

### Pattern 27: Park et al. Recency Scoring (0.995^hours)

**Research Requirement**: `recency = 0.995^hours_since_last_access`. Exponential decay at ~30% retention after 24h.

**Status**: COMPLIANT (enhanced)

**Evidence**: The implementation uses the Ebbinghaus curve `R = e^(-t/S)` which is a more sophisticated version of the Park et al. formula:
- `src/context_graph/domain/scoring.py:22-46` implements `compute_recency_score`.
- The Ebbinghaus curve subsumes Park et al.'s fixed decay rate with a variable stability factor S that increases with access count, implementing the "use it or lose it" dynamic.
- Default S_base = 168 hours (1 week), S_boost = 24 hours per access. `src/context_graph/settings.py:78-79`.

**Notes**: The implementation is strictly better than Park et al.'s fixed 0.995 decay rate because stability increases with successful recall, matching the MemoryBank Ebbinghaus model.

---

### Pattern 28: Importance Scoring (LLM-rated 1-10 scale)

**Research Requirement**: Importance rated on 1-10 scale, normalized to [0,1].

**Status**: COMPLIANT

**Evidence**:
- **Event schema**: `importance_hint` field (1-10, optional). `src/context_graph/domain/models.py:281`.
- **Normalization**: `src/context_graph/domain/scoring.py:49-62` normalizes to [0,1] with access and centrality boosts.
- **Enrichment-computed**: `importance_score` stored in Neo4j, computed from hint + heuristics. `src/context_graph/worker/enrichment.py:85-86`.
- **Centrality-based recomputation**: `src/context_graph/adapters/neo4j/maintenance.py:106-117` updates importance based on in-degree centrality.

---

### Pattern 29: Relevance Scoring (Cosine Similarity)

**Research Requirement**: `relevance = cosine_similarity(embed(memory), embed(query))`.

**Status**: PARTIAL

**Evidence**:
- **Function**: `src/context_graph/domain/scoring.py:65-81` implements `compute_relevance_score` with proper cosine similarity calculation.
- **Fallback**: Returns 0.5 (neutral) when embeddings are unavailable or mismatched. `src/context_graph/domain/scoring.py:74-75`.

**Gap**: Embeddings are never actually computed. `src/context_graph/worker/enrichment.py:108` has `# TODO: Embedding computation`. The relevance score always returns 0.5 in practice because `node_embedding` is always empty.

---

### Pattern 30: MemoryBank Ebbinghaus Forgetting Curve (R = e^(-t/S))

**Research Requirement**: `R = e^(-t/S)` where S (stability) increases with each successful recall.

**Status**: COMPLIANT

**Evidence**: Direct implementation:
- `src/context_graph/domain/scoring.py:22-46`: `R = math.exp(-t_hours / stability)` where `stability = s_base + (access_count * s_boost)`.
- Access-based reinforcement: Each retrieval bumps `access_count`. `src/context_graph/adapters/neo4j/store.py:288-299` (`_bump_access_counts`).
- `last_accessed_at` update enables recency to use the more recent of `occurred_at` and `last_accessed_at`. `src/context_graph/domain/scoring.py:39-41`.

**Notes**: This is one of the strongest compliance points. The implementation faithfully captures the Ebbinghaus model with access-based stability reinforcement.

---

### Pattern 31: Reflection Trigger (Importance Sum > Threshold)

**Research Requirement**: `if sum(importance_scores[recent_memories]) > threshold (150): trigger_reflection()`.

**Status**: COMPLIANT

**Evidence**:
- **Threshold check**: `src/context_graph/domain/consolidation.py:26-32` (`should_reconsolidate` with default threshold 150.0).
- **Configuration**: `src/context_graph/settings.py:91` (`reflection_threshold = 150`).
- **Consolidation consumer**: `src/context_graph/worker/consolidation.py:89-95` uses `count * 5` as importance sum proxy.
- **Admin endpoint**: `src/context_graph/api/routes/admin.py:112-113` applies threshold check.

**Notes**: The consolidation consumer uses `count * 5` as a rough importance proxy (average importance of 5 on a 1-10 scale). A more precise implementation would sum actual importance_score values from Neo4j nodes.

---

### Pattern 32: Reflection Process (Generate Higher-Level Inferences)

**Research Requirement**: Reflection: identify salient questions, retrieve evidence, generate higher-level inferences, store as new memory objects (hierarchical reflection trees).

**Status**: PARTIAL

**Evidence**:
- **Hierarchical summaries**: Episode -> session -> agent summaries form a reflection tree. `src/context_graph/worker/consolidation.py:195-236`.
- **SUMMARIZES edges**: Link summaries to source events. `src/context_graph/adapters/neo4j/maintenance.py:310-360`.
- **Deterministic summaries**: Current summaries are rule-based (event count + types + time range). `src/context_graph/domain/consolidation.py:73-116`.

**Gap**: No LLM-generated reflections. The `build_summary_prompt` function exists (`src/context_graph/domain/consolidation.py:119-156`) but is not called anywhere -- it's prepared for future LLM use. Summaries are purely structural, not semantic reflections.

---

### Pattern 33: Advanced Scoring -- Learned/Dynamic Weights

**Research Requirement**: MoE gate functions for dynamic weight learning; SAGE/MARK systems with trust/persistence scoring.

**Status**: GAP

**Evidence**: Not implemented. All scoring weights are static configuration values:
- `src/context_graph/settings.py:81-85` defines fixed weights.
- No learning mechanism adjusts weights based on retrieval success/failure.

**Notes**: This is explicitly deferred. ADR-0008 acknowledges RL-driven memory management as the frontier but notes it requires training data from production usage. Static weights are the correct starting point.

---

### Pattern 34: Experiential Memory Distillation Pipeline

**Research Requirement**: Case-based (raw traces) -> Strategy-based (abstracted workflows) -> Skill-based (executable procedures) with selection, abstraction, and verification at each level.

**Status**: GAP

**Evidence**:
- **Models**: `WorkflowAbstractionLevel` enum with CASE/STRATEGY/SKILL. `src/context_graph/domain/models.py:209-215`. `WorkflowNode` model. `src/context_graph/domain/models.py:385-398`. `ABSTRACTED_FROM` edge. `src/context_graph/domain/models.py:106`.
- **No implementation**: No code detects patterns in event sequences, abstracts them into strategies, or compiles them into skills. Consumer 4 does not process workflows.

**Notes**: Schema is fully prepared. Implementation requires significant pattern mining logic and is a future phase.

---

## Design Recommendations from Research Document

---

### Pattern 35: Event-as-Episode Design

**Research Requirement**: Event schema should capture all five properties of episodic memory.

**Status**: COMPLIANT

**Evidence**: See Pattern 17 above. All five properties are satisfied by the event schema.

---

### Pattern 36: Add Memory Scoring to Retrieval

**Research Requirement**: Implement three-factor scoring model for context retrieval.

**Status**: COMPLIANT

**Evidence**: Four-factor scoring implemented (recency + importance + relevance + user_affinity). See Pattern 26.

---

### Pattern 37: Add Decay/Forgetting to Graph Projection

**Research Requirement**: Tiered retention: Hot (<24h full detail), Warm (24h-7d summarized), Cold (>7d high-importance only), Archive (>30d removed from graph).

**Status**: COMPLIANT

**Evidence**:
- **Hot**: < 24h, all nodes/edges. `src/context_graph/settings.py:103`.
- **Warm**: 24h-7d, low-similarity edges pruned. `src/context_graph/settings.py:104,108`.
- **Cold**: 7-30d, low-importance/low-access nodes pruned. `src/context_graph/settings.py:105,111-112`.
- **Archive**: > 30d, removed from Neo4j. `src/context_graph/adapters/neo4j/maintenance.py:100-104,223-248`.
- **Implementation**: `src/context_graph/domain/forgetting.py:32-58` (classify_retention_tier). `src/context_graph/worker/consolidation.py:253-302` (_run_forgetting).

---

### Pattern 38: Implement Reflection as Consolidation Trigger

**Research Requirement**: When accumulated importance exceeds threshold, trigger consolidation.

**Status**: COMPLIANT

**Evidence**: See Pattern 31 above. Implemented via `should_reconsolidate` with configurable threshold (default 150).

---

### Pattern 39: Experiential Memory Hierarchy in Graph

**Research Requirement**: Map case-strategy-skill hierarchy to the graph with Case nodes (event traces), Strategy nodes (derived patterns), Skill nodes (compiled pipelines).

**Status**: PARTIAL

**Evidence**:
- **Case nodes**: Events are fully captured as Event nodes.
- **Strategy/Skill nodes**: WorkflowNode with abstraction_level field, ABSTRACTED_FROM edges. Models exist but no population logic.
- **SkillNode**: Defined at `src/context_graph/domain/models.py:374-383` with HAS_SKILL edges.

**Gap**: No workflow/pattern detection logic. No frequency analysis or outcome scoring to drive distillation.

---

### Pattern 40: Episode Segmentation

**Research Requirement**: Use session boundaries and parent-child relationships as natural episode boundaries. Consider surprise-based segmentation for long sessions.

**Status**: PARTIAL

**Evidence**:
- **Session boundaries**: system.session_start/end events. Mid-session extraction every N turns. `src/context_graph/worker/extraction.py:68-88`.
- **Temporal gap segmentation**: `src/context_graph/domain/consolidation.py:35-70` with configurable gap_minutes.
- **Parent-child chains**: parent_event_id provides causal structure.
- **Surprise-based**: NOT IMPLEMENTED. No model surprise detection.

---

## Key Gaps Identified in Research Document

---

### Pattern 41: Importance Scoring Field

**Research Gap**: "Events lack an importance/salience field."

**Status**: RESOLVED

**Evidence**: `importance_hint` on Event model (optional, 1-10). `src/context_graph/domain/models.py:281`. `importance_score` computed during enrichment. This gap was addressed during implementation.

---

### Pattern 42: Decay Mechanism

**Research Gap**: "Graph projection retains all events equally. Need tiered retention."

**Status**: RESOLVED

**Evidence**: Full Ebbinghaus decay scoring + four-tier retention. See Patterns 27, 30, 37.

---

### Pattern 43: Consolidation Triggers

**Research Gap**: "Projection worker runs on fixed polling. Need event-driven consolidation."

**Status**: RESOLVED

**Evidence**: Event-driven consolidation via Redis consumer groups (not polling). Session-end triggers extraction. Importance threshold triggers reflection. See Pattern 21.

---

### Pattern 44: Procedural Memory

**Research Gap**: "No mechanism to capture and optimize agent tool-use policies from event patterns."

**Status**: GAP

**Evidence**: Models defined (WorkflowNode, BehavioralPatternNode, SkillNode, ABSTRACTED_FROM, PARENT_SKILL, EXHIBITS_PATTERN edges) but no detection/extraction logic implemented.

---

### Pattern 45: User-Centric Memory Dimension

**Research Gap**: "Current schema is agent-centric. User-centric personalization would require additional modeling."

**Status**: RESOLVED

**Evidence**: Complete user personalization ontology. ADR-0012 defines 5 node types and 9 edge types. Implementation in `src/context_graph/adapters/neo4j/user_queries.py`, `src/context_graph/api/routes/users.py`, `src/context_graph/worker/extraction.py`.

---

### Pattern 46: Retrieval Scoring in Responses

**Research Gap**: "Graph queries return results without relevance/recency/importance ranking."

**Status**: RESOLVED

**Evidence**: All Atlas responses include per-node scores (decay_score, relevance_score, importance_score). `src/context_graph/domain/models.py:447-452` (NodeScores). `src/context_graph/domain/models.py:454-463` (AtlasNode with scores field).

---

## Additional Cross-Cutting Patterns

---

### Pattern 47: Reconsolidation on Retrieval

**Research Requirement**: Retrieval opens a plasticity window where memories can be updated. Access strengthens memories.

**Status**: COMPLIANT

**Evidence**:
- Access count increment on query. `src/context_graph/adapters/neo4j/store.py:288-299`.
- `last_accessed_at` timestamp update. `src/context_graph/adapters/neo4j/queries.py:262-273`.
- Stability increases with access (S_boost = 24h per access). `src/context_graph/domain/scoring.py:43` (`stability = s_base + (access_count * s_boost)`).

---

### Pattern 48: Memory State Evolution Formula (M_{t+1} = E(M_t, F(artifacts_t)))

**Research Requirement**: Memory evolves through application of Formation (F) and Evolution (E) operators.

**Status**: COMPLIANT

**Evidence**: The four-consumer pipeline implements this exactly:
- F(artifacts): Consumer 1 (projection) + Consumer 2 (extraction) transform artifacts into memory candidates.
- E(M_t, ...): Consumer 3 (enrichment) + Consumer 4 (consolidation) evolve the memory state with new candidates, decay, and pruning.

---

### Pattern 49: Embedding-Based Semantic Retrieval

**Research Requirement**: Use embedding similarity for semantic retrieval and SIMILAR_TO edge creation.

**Status**: GAP

**Evidence**:
- **Cosine similarity function**: Implemented. `src/context_graph/domain/scoring.py:65-81`.
- **SIMILAR_TO edge type**: Defined. `src/context_graph/domain/models.py:91`. Cypher template exists. `src/context_graph/adapters/neo4j/queries.py:99-104`.
- **Similarity threshold**: Configured at 0.85. `src/context_graph/settings.py:88`.
- **Embedding computation**: NOT IMPLEMENTED. `src/context_graph/worker/enrichment.py:108` has TODO.
- **SIMILAR_TO edge creation**: NOT IMPLEMENTED. `src/context_graph/worker/enrichment.py:109` has TODO.
- **REFERENCES edge creation**: NOT IMPLEMENTED. `src/context_graph/worker/enrichment.py:110` has TODO.

**Notes**: All the plumbing is in place (models, Cypher, scoring functions, thresholds). The missing piece is embedding model integration in the enrichment worker.

---

### Pattern 50: Entity Resolution

**Research Requirement**: Determining that different names refer to the same entity (e.g., "GPT-4" and "gpt-4o").

**Status**: COMPLIANT

**Evidence**: Three-tier entity resolution implemented:
- **Tier 1 (Exact match)**: Normalization + alias dictionary + exact match. `src/context_graph/domain/entity_resolution.py:94-129`.
- **Tier 2 (Fuzzy match)**: SequenceMatcher character-level similarity with configurable threshold (default 0.9). `src/context_graph/domain/entity_resolution.py:149-194`.
- **Domain alias dictionary**: 18 canonical names with aliases. `src/context_graph/domain/entity_resolution.py:31-49`.
- **Resolution actions**: MERGE, SAME_AS, RELATED_TO, CREATE. `src/context_graph/domain/entity_resolution.py:69-76`.

**Notes**: Embedding-based entity resolution (Tier 2b) is a future enhancement, noted as TODO.

---

### Pattern 51: Four-Factor Scoring with User Affinity

**Research Requirement**: Extended scoring beyond Park et al. to include user context (session proximity, retrieval recurrence, entity overlap).

**Status**: COMPLIANT

**Evidence**:
- Fourth factor `user_affinity` with weight 0.5. `src/context_graph/domain/scoring.py:84-104`.
- `compute_user_affinity` function with session_proximity (0.4), retrieval_recurrence (0.3), entity_overlap (0.3). `src/context_graph/domain/scoring.py:185-196`.
- Settings: `src/context_graph/settings.py:85` (`weight_user_affinity = 0.5`).

---

### Pattern 52: LLM-Based Knowledge Extraction

**Research Requirement**: Use LLM structured output for entity, preference, skill, and interest extraction from conversation text.

**Status**: GAP

**Evidence**:
- **Extraction models**: Fully defined (ExtractedEntity, ExtractedPreference, ExtractedSkill, ExtractedInterest, SessionExtractionResult). `src/context_graph/domain/extraction.py:93-154`.
- **Prompt construction**: `src/context_graph/adapters/llm/client.py:95-119` builds ontology-guided extraction prompts.
- **Validation pipeline**: Source quote validation, confidence priors, min thresholds. `src/context_graph/adapters/llm/client.py:149-246`.
- **Degenerate output detection**: `src/context_graph/adapters/llm/client.py:302-324`.
- **Actual LLM call**: NOT IMPLEMENTED. `src/context_graph/adapters/llm/client.py:286-299` returns empty results with a TODO comment.

**Notes**: The entire extraction framework is built -- models, prompts, validation, consumer wiring. Only the actual LLM API call (via instructor/litellm) is missing.

---

## ADR Alignment

| ADR | Research Patterns Addressed |
|-----|----------------------------|
| ADR-0001 | Patterns 17 (5 episodic properties), 18 (three-system architecture), bounded queries |
| ADR-0003 | Patterns 18, 24 (CLS model -- Redis=hippocampus, Neo4j=neocortex) |
| ADR-0004 | Patterns 17 (instance-specific, contextual relations), 41 (importance field) |
| ADR-0007 | Patterns 1 (three-lens), 11 (five cognitive types), 9 (experiential hierarchy), 22 (unified taxonomy) |
| ADR-0008 | Patterns 4 (consolidation levels), 5 (forgetting strategies), 26-31 (scoring), 37 (tiered retention), 47 (reconsolidation) |
| ADR-0009 | Patterns 7 (multi-strategy retrieval), 8 (proactive/reactive), 2 (multi-level structure) |
| ADR-0010 | Patterns 17 (long-term storage), 24 (fast encoding) |
| ADR-0011 | Patterns 14 (agent/user-centric), 50 (entity resolution) |
| ADR-0012 | Patterns 14 (user-centric memory), 45 (user personalization) |
| ADR-0013 | Patterns 3 (formation operator), 52 (LLM extraction), 20 (consolidation pipeline) |

---

## Gap Analysis

| Priority | Gap | Severity | Pattern(s) | Suggested Remediation |
|----------|-----|----------|------------|----------------------|
| **P0** | Embedding computation not implemented | HIGH | 3, 7, 29, 49 | Integrate sentence-transformers (all-MiniLM-L6-v2) in enrichment worker. Unblocks SIMILAR_TO edges, relevance scoring, and semantic retrieval. |
| **P0** | LLM extraction client returns empty results | HIGH | 52 | Wire instructor + litellm in `adapters/llm/client.py:extract_from_session`. The prompt, validation, and consumer pipeline are all ready. |
| **P1** | SIMILAR_TO and REFERENCES edges never created | MEDIUM | 7, 49 | Implement in enrichment worker after embedding computation. SIMILAR_TO requires pairwise cosine comparison. REFERENCES requires entity extraction from event payloads. |
| **P1** | Workflow/behavioral pattern detection not implemented | MEDIUM | 9, 34, 44 | Implement frequency analysis and outcome scoring in Consumer 4 to detect repeated event sequences and abstract into WorkflowNode instances. |
| **P2** | No surprise-based episode segmentation | LOW | 19, 40 | Add perplexity/surprise detection for long sessions. Current temporal gap segmentation is sufficient for most use cases. |
| **P2** | No RL-driven / adaptive forgetting policies | LOW | 5, 33 | Requires production usage data. Collect retrieval success metrics first, then train weight optimization. |
| **P2** | Consolidation importance proxy uses count*5 | LOW | 31 | Replace `count * 5` proxy in `worker/consolidation.py:94` with actual sum of `importance_score` values from Neo4j nodes for more accurate reflection triggers. |
| **P3** | No conflict resolution for contradictory preferences | LOW | 6 | Implement detection logic when new preference contradicts existing one (same key, opposite polarity). Use `superseded_by` chain. |
| **P3** | Summaries are rule-based, not LLM-generated | LOW | 32 | `build_summary_prompt` is ready at `domain/consolidation.py:119-156`. Wire to LLM for richer semantic summaries. |
