# Cluster 1: Context Graphs and Graph-Based Memory for Agents

**Researcher**: researcher-1
**Date**: 2026-02-11
**Papers**: 3 papers covering graph-based memory taxonomies, multi-graph architectures, and Zettelkasten-inspired agentic memory

---

## Paper 1.1: Graph-based Agent Memory: Taxonomy, Techniques, and Applications

- **Authors**: Chang Yang et al. (18 authors)
- **Date**: February 5, 2026
- **Link**: https://arxiv.org/abs/2602.05665
- **Venue**: Survey paper

### Key Contributions

This paper provides the most comprehensive survey to date on graph-based memory for LLM agents. It introduces a three-dimensional taxonomy and a four-stage lifecycle framework that gives us a shared vocabulary for reasoning about agent memory systems.

### Taxonomy Framework

The survey classifies agent memory along three axes:

**Axis 1 -- Temporal Scope**
- **Short-term memory**: Recent, immediately relevant information with rapid access and limited capacity. Includes current conversation context, active reasoning traces, transient variables. Typically discarded after task completion.
- **Long-term memory**: Persistent information across sessions including accumulated knowledge, historical interactions, learned patterns, and user preferences.

**Axis 2 -- Content Character**
- **Knowledge memory** (passive/static): Objective, global, verifiable information functioning as an internal reference library. Pre-loaded, slowly updated, context-independent. Examples: product databases, scientific principles.
- **Experience memory** (proactive/dynamic): Personal logbook recording specific interactions, observations, and action outcomes. Dynamic, personalized, task-specific. Examples: dialogue history, execution logs, learned preferences.

**Axis 3 -- Cognitive Function** (six types)
| Cognitive Type | Description | Graph Mapping |
|----------------|-------------|---------------|
| Semantic | Factual, decontextualized knowledge | Knowledge graphs with entity-relation triples |
| Procedural | Skills, routines, immutable rules | DAGs encoding workflow sequences |
| Associative | Latent links between concepts | Weighted undirected edges, hypergraphs |
| Working | Immediate mental scratchpad | In-memory subgraph, context window |
| Episodic | Chronological sequence of past sessions | Temporal graphs with timestamps |
| Sentiment | Emotional tone or interaction quality | Node attributes or edge weights |

### Graph Architecture Types

The survey identifies five primary graph structures for agent memory:

**1. Knowledge Graphs (KGs)**
- Represent information as triples: (head entity, relation, tail entity)
- Encode general world facts and domain-specific concepts
- Support efficient multi-hop queries
- Systems: Mem0 uses LLM extraction to convert conversations into entity-relation triplets

**2. Temporal Graphs**
- Extend triples to quadruples: (subject, relation, object, timestamp)
- Implement bi-temporal modeling distinguishing:
  - **Valid time**: when an event actually occurs
  - **Transaction time**: when it is recorded in the system
- Systems: Graphiti tracks both creation and expiration timestamps, enabling contradiction resolution through temporal invalidation rather than overwrites

**3. Hierarchical Structures (Trees/DAGs)**
- Organize information into multi-level parent-child relationships
- Dynamic routing of new information through the hierarchy
- Systems: MemTree clusters similar content under existing nodes with recursive parent summarization

**4. Hypergraphs**
- Hyperedges connect arbitrary numbers of nodes
- Preserve n-ary relations without decomposition into binary edges
- Prevent sparsity and semantic fragmentation
- Systems: HyperGraphRAG uses dual-retrieval for facts and associated entities

**5. Hybrid Architectures**
- Combine multiple structures for complementary strengths
- Systems: Optimus-1 pairs a Hierarchical Directed Knowledge Graph (static game mechanics) with a vector-based experience pool (dynamic trajectories)

### Memory Lifecycle (Four Stages)

**Stage 1: Extraction** -- transforms raw data into memory content
- Textual sources: NER, relation extraction, semantic embeddings, summarization
- Sequential trajectories: Event segmentation, timestamping, dynamic state snapshots
- Multimodal: Vision-language descriptions, audio captioning, joint embeddings

**Stage 2: Storage** -- organizes extracted content using appropriate graph patterns
- Knowledge memory maps to KGs for relational structure
- Experience memory maps to hierarchical or temporal graphs for evolution tracking

**Stage 3: Retrieval** -- six operator categories:
| Operator Type | Mechanism | When to Use |
|---------------|-----------|-------------|
| Similarity-based | Vector embedding matching (top-k) | General semantic recall |
| Rule-based | Symbolic filters, deterministic constraints | Precise lookups |
| Temporal-based | Time-window filtering, decay ranking | Recent/historical queries |
| Graph-based | Intra-layer entity expansion + inter-layer traversal | Multi-hop reasoning |
| RL-based | Learned action-value functions optimizing task rewards | Complex optimization |
| Agent-based | Planning loops with tool calls and external APIs | Open-ended retrieval |

**Stage 4: Evolution** -- two paradigms:
- **Internal self-evolving**: Introspective refinement via:
  - *Consolidation*: Merging similar events into schema nodes (generalization)
  - *Graph reasoning*: Abstracting higher-level patterns from raw trajectories
  - *Reorganization*: Topology optimization -- restructuring edges to shorten path length between frequently associated concepts
  - *Decay/pruning*: Algorithms (e.g., PageRank variants, decay functions) evaluate node utility; rarely accessed or low-contribution nodes are pruned or compressed
- **External self-exploration**: Grounding memory through environmental interaction
  - Reactive feedback-driven adaptation
  - Proactive active inquiry

### Memory Consolidation Mechanisms

The survey describes consolidation analogous to human sleep-based memory consolidation:
- Generalization via graph merging of similar distinct events into schema nodes
- Abstraction extracting higher-level patterns from raw trajectories
- Conflict resolution identifying and invalidating contradictory triples
- Topology optimization creating shortcuts between frequently co-accessed concepts

### Provenance and Lineage Patterns

The survey highlights temporal metadata as the primary provenance mechanism:
- Graphiti's bi-temporal approach (valid time + transaction time) enables systems to resolve contradictions through temporal invalidation rather than overwrites, maintaining a faithful history of state changes
- No explicit event-sourcing or append-only provenance patterns are discussed (this is a gap our project can fill)

### Evaluation Dimensions

Three quality metrics:
1. **Retrieval effectiveness**: Success in surfacing relevant information
2. **Graph structural quality**: Coherence, consistency, completeness
3. **Task-level utility**: Impact on downstream agent performance

Benchmarks span seven application scenarios: Interaction, Personalization, Web, LongContext, Continual Learning, Embodied Environments, Tool/Workflow Execution.

### Strengths and Limitations

**Strengths**: Most comprehensive taxonomy to date; clear lifecycle framework; covers five graph types with real system examples; identifies consolidation as critical missing piece in most systems.

**Limitations**: Largely descriptive -- does not propose a unified architecture; limited coverage of provenance/lineage tracking; no discussion of event sourcing patterns; decay function specifics remain abstract.

---

## Paper 1.2: MAGMA -- A Multi-Graph based Agentic Memory Architecture

- **Authors**: Dongming Jiang, Yi Li, Guanpeng Li, Bingzhe Li
- **Date**: January 6, 2026
- **Link**: https://arxiv.org/abs/2601.03236
- **Venue**: Preprint

### Key Contributions

MAGMA is the standout architecture in this cluster. It decouples memory into four orthogonal graph views and introduces a dual-stream write pipeline (fast path / slow path) that maps remarkably well to our Postgres event ledger + Neo4j graph projection architecture.

### Architecture (Three Layers)

```
+---------------------------+
|      Query Process        |  Intent-aware router, adaptive traversal, context synthesis
+---------------------------+
|    Data Structure Layer   |  Time-variant directed multigraph G_t = (N_t, E_t)
|  [Temporal][Causal][Semantic][Entity] + Vector DB
+---------------------------+
|    Write/Update Process   |  Fast path (synaptic) + Slow path (consolidation)
+---------------------------+
```

### Graph Schema (Four Orthogonal Views)

Each event-node is defined as: `n_i = <c_i, tau_i, v_i, A_i>` where:
- `c_i`: Event content (observations, actions, state changes)
- `tau_i`: Discrete timestamp
- `v_i`: Dense embedding (R^d) indexed in vector database
- `A_i`: Structured metadata (entity references, temporal cues, contextual descriptors)

**Temporal Graph (E_temp)**
- Strictly ordered pairs (n_i, n_j) where tau_i < tau_j
- Immutable chronological backbone -- ground truth for "when" queries
- Once written, temporal edges are never modified

**Causal Graph (E_causal)**
- Directed edges where relevance score S(n_j | n_i, q) > delta
- Inferred asynchronously by the consolidation module
- Supports "why" queries through cause-effect chains

**Semantic Graph (E_sem)**
- Undirected edges where cos(v_i, v_j) > theta_sim
- Connects conceptually similar events via embedding similarity

**Entity Graph (E_ent)**
- Connects event nodes to abstract entity nodes
- Solves the object permanence problem across disjoint timeline segments
- Enables "who/what" queries by tracking entities across time

### Dual-Stream Write Pipeline

This is the most architecturally significant pattern for our project:

**Fast Path (Synaptic Ingestion)** -- on the critical path, non-blocking:
1. Event segmentation
2. Temporal backbone update (previous node -> current node edge)
3. Vector indexing in database
4. Enqueue event for async processing

No LLM reasoning occurs here. The agent remains responsive.

**Slow Path (Structural Consolidation)** -- async background worker:
1. Analyze local neighborhood (2-hop radius) of recent events
2. Use LLM to infer latent causal and entity connections
3. Construct high-value edges: `E_new = Phi_LLM_reason(N(n_t), H_history)`
4. Trade compute time for relational depth

**Direct parallel to our architecture**:
| MAGMA | Our Project |
|-------|-------------|
| Fast path (synaptic ingestion) | Postgres event ledger (append-only, non-blocking) |
| Slow path (structural consolidation) | Async projection worker (Postgres -> Neo4j) |
| Immutable temporal backbone | Immutable event records with global_position |
| LLM-inferred causal/entity edges | Graph projection with MERGE-based Cypher |

### Retrieval Pipeline (Four Stages)

**Stage 1 -- Query Analysis**: Decomposes queries into:
- Intent classification (Why / When / Entity)
- Temporal parsing
- Representation extraction

**Stage 2 -- Anchor Identification**: Uses Reciprocal Rank Fusion (RRF) across:
- Dense semantic retrieval
- Lexical keyword matching
- Temporal filtering
- RRF constant k=60

**Stage 3 -- Adaptive Traversal**: Beam search with intent-aware transition scoring:
```
S(n_j | n_i, q) = exp(lambda_1 * phi(type(e_ij), T_q) + lambda_2 * sim(n_j, q))
```
- Structural alignment `phi`: Adaptive weight vector specific to intent T_q
  - Causal edges weighted 3.0-5.0 for "why" queries
  - Temporal edges weighted 0.5-4.0 for "when" queries
  - Entity edges weighted 2.5-6.0 for "who/what" queries
- Max traversal depth: 5 hops
- Node budget: 200 nodes
- Retains top-k nodes with highest cumulative scores

**Stage 4 -- Narrative Synthesis**: Topological sorting, timestamp/reference annotation, token budgeting via salience scores.

### Performance Results

**LoCoMo Benchmark**:
| Method | Judge Score | Build Time | Tokens/Query | Latency |
|--------|-------------|------------|--------------|---------|
| Full Context | 0.481 | N/A | 8.53k | 1.74s |
| A-MEM | 0.580 | 1.01h | 2.62k | 2.26s |
| Nemori | 0.590 | 0.29h | 3.46k | 2.59s |
| **MAGMA** | **0.700** | 0.39h | 3.37k | **1.47s** |

- 18.6% to 45.5% improvement over baselines
- Adversarial category: 0.742 vs 0.325-0.616
- Multi-hop reasoning: 0.528 vs 0.495-0.569

**LongMemEval (100K+ tokens)**:
- 61.2% average accuracy
- Token reduction: 0.7-4.2K tokens/query vs 101K full context (95% reduction)
- 40% faster latency than A-MEM

**Ablation**: Removing adaptive policy causes largest drop (0.700 -> 0.637); causal and temporal links are non-substitutable reasoning axes.

### Implementation Details

- Vector DB: all-MiniLM-L6-v2 (384-dim default) or text-embedding-3-small (1536-dim)
- LLM backbone: GPT-4o-mini with temperature=0.0
- Storage: Abstracted backends (in-memory vs production graph/vector databases)
- Open-sourced on GitHub

### Strengths and Limitations

**Strengths**: Cleanest separation of concerns across graph types; dual-stream write path directly maps to event sourcing + projection; intent-aware retrieval is powerful; strong empirical results; open source.

**Limitations**: LLM-dependent consolidation (slow path requires inference calls); entity resolution across graphs could be fragile; no explicit decay/forgetting mechanism; hyperparameter-heavy (intent weights, thresholds).

---

## Paper 1.3: A-MEM -- Agentic Memory for LLM Agents

- **Authors**: Wujiang Xu, Zujie Liang, Kai Mei et al.
- **Date**: February 17, 2025 (revised through 2025, accepted NeurIPS 2025)
- **Link**: https://arxiv.org/abs/2502.12110

### Key Contributions

A-MEM brings a Zettelkasten-inspired approach to agent memory, where each memory is a richly-attributed note that participates in a dynamically evolving knowledge network. Its key innovation is bidirectional memory evolution -- new memories can retroactively update existing ones.

### Architecture: Zettelkasten Memory Network

Each memory note `m_i` has seven components:
| Field | Type | Description |
|-------|------|-------------|
| `c_i` | string | Original interaction content |
| `t_i` | timestamp | Interaction timestamp |
| `K_i` | list[string] | LLM-generated keywords (3+ minimum) capturing key concepts |
| `G_i` | list[string] | LLM-generated tags for categorization (domain, format, type) |
| `X_i` | string | LLM-generated contextual description (1 sentence: topic, arguments, audience) |
| `e_i` | vector | Dense embedding for similarity matching |
| `L_i` | set[note_id] | Set of linked memories |

### Graph Schema

A-MEM implements a flexible, non-rigid graph structure:

- **Nodes**: Individual memory notes with multi-faceted attributes (the seven fields above)
- **Edges**: Dynamic semantic links established between related memories through embedding similarity + LLM analysis
- **"Boxes"**: Conceptual groupings where related memories become interconnected through similar contextual descriptions. Memories can exist in multiple boxes simultaneously (soft clustering, not partitioning).

### Memory Lifecycle Operations

**1. Memory Creation (Ingestion)**
When new content arrives:
1. LLM generates keywords `K_i`, tags `G_i`, and contextual description `X_i`
2. Text encoder produces embedding `e_i`
3. Note is stored with all seven attributes
4. Triggers linking and evolution (below)

**2. Memory Linking**
Two-phase process:
- Phase A: Embedding-based retrieval identifies candidate related notes (cosine similarity, top-k)
- Phase B: LLM-driven analysis determines which connections are meaningful -- goes beyond simple similarity to identify common attributes and causal relationships

**3. Memory Evolution (Bidirectional Update)**
This is the signature mechanism:
- When new memory `m_new` is linked to existing memory `m_j`:
  - `m_j`'s contextual description, keywords, and tags are updated to reflect the new relationship
  - Evolved memory `m_j*` replaces original in the collection
  - Enables discovery of higher-order patterns across multiple memories
- Evolution is **bidirectional**: new memories update old ones, creating a continuously refining network

**4. Memory Retrieval**
- Encode query using identical text encoder
- Compute cosine similarity against all note embeddings
- Return top-k relevant memories (typical k=10)
- Related memories within same "boxes" are auto-accessed as bonus context

### Continuous Refinement (Not Discrete Consolidation)

Unlike MAGMA's explicit consolidation worker, A-MEM uses continuous refinement:
- The memory network continuously refines and deepens understanding over time
- Memory evolution enables existing memories to dynamically adapt as new experiences are analyzed
- No explicit merge/prune operations -- the network organically strengthens important connections

### Performance

**LoCoMo dataset (GPT-4o-mini)**:
- Multi-hop F1: 27.02 (vs LoCoMo 25.02, MemGPT 26.65)
- At least 2x better performance on multi-hop questions
- Token efficiency: 1,200-2,520 tokens vs 16,910 (85-93% reduction)

**DialSim**: F1 3.45 vs 2.55 (LoCoMo), 1.18 (MemGPT)

**Scalability**: Retrieval time scales from 0.31us (1K memories) to 3.70us (1M memories)

**Processing**: 5.4s per memory (GPT-4o-mini), 1.1s (Llama 3.2 1B on single GPU)

### Implementation Details

- Text encoder: all-minilm-l6-v2 (sentence-transformers)
- Models tested: GPT-4o/4o-mini, Qwen 2.5, Llama 3.2, DeepSeek-R1-32B, Claude variants
- Deployment: Ollama (local), LiteLLM (structured outputs), official APIs

### Strengths and Limitations

**Strengths**: Elegant Zettelkasten metaphor; bidirectional evolution is unique and powerful; rich multi-faceted note attributes; scales well (sub-microsecond retrieval at 1M notes); works across many LLM backends.

**Limitations**: No explicit decay/forgetting; evolution requires LLM calls per ingestion (latency cost); flat graph structure (no hierarchy); embedding-only retrieval may miss structural relationships; no temporal or causal edge types.

---

## Cross-Paper Synthesis

### Architectural Pattern Comparison

| Dimension | Survey (1.1) | MAGMA (1.2) | A-MEM (1.3) |
|-----------|-------------|-------------|-------------|
| Graph type | Taxonomy of 5 types | Four orthogonal typed graphs | Flat semantic network |
| Node schema | Varies by system | `<content, timestamp, embedding, metadata>` | 7-field note (content, time, keywords, tags, context, embedding, links) |
| Edge types | Varies | Temporal, causal, semantic, entity | Semantic similarity only |
| Write path | N/A (survey) | Dual-stream (fast + slow) | Single-stream with async evolution |
| Retrieval | 6 operator categories | Intent-aware beam traversal | Embedding similarity + box grouping |
| Evolution | Consolidation + decay + pruning | Async LLM consolidation | Bidirectional note updates |
| Decay | Mentioned (PageRank, decay functions) | Not implemented | Not implemented |
| Provenance | Bi-temporal metadata | Immutable temporal backbone | Timestamps only |

### Key Design Patterns for Our Context-Graph Project

#### Pattern 1: Dual-Stream Write (from MAGMA)

MAGMA's fast path / slow path maps directly to our Postgres + Neo4j architecture:

```
Event Ingest (Fast Path)          Projection Worker (Slow Path)
========================          ==============================
Append to Postgres ledger    -->  Poll new events from Postgres
  - event_id, event_type          - Read event batch
  - occurred_at, session_id       - Transform to graph operations
  - payload_ref                   - MERGE nodes and edges in Neo4j
  - global_position (BIGSERIAL)   - Infer relationships (causal, entity)
                                  - Update cursor position
Non-blocking, immutable           Async, eventually consistent
```

**Recommendation**: Adopt this pattern as-is. Our existing architecture already embodies it. Enhance the projection worker to produce typed edges (temporal, causal, semantic, entity) rather than a single edge type.

#### Pattern 2: Multi-Typed Edge Projection (from MAGMA + Survey)

Rather than projecting all relationships as generic edges, produce four edge types in Neo4j:

- `FOLLOWS` (temporal): Based on occurred_at ordering within a session
- `CAUSED_BY` (causal): Inferred from parent_event_id + payload analysis
- `SIMILAR_TO` (semantic): Based on embedding similarity of event payloads
- `REFERENCES` (entity): Based on shared entity mentions across events

**Recommendation**: Start with temporal and causal edges (derivable from event metadata alone), then add semantic and entity edges as enhancement.

#### Pattern 3: Immutable Temporal Backbone (from MAGMA)

MAGMA's temporal graph is immutable once written -- exactly matching our append-only event ledger principle. The temporal backbone serves as ground truth that other edge types are layered on top of.

**Recommendation**: Model `global_position` as the temporal ordering. The Postgres ledger IS the temporal backbone. Neo4j temporal edges are projections of this ordering.

#### Pattern 4: Memory Note Enrichment (from A-MEM)

A-MEM's seven-field note structure suggests enriching our event records with derived attributes:

| A-MEM Field | Our Equivalent |
|-------------|----------------|
| `c_i` (content) | `payload_ref` (event payload) |
| `t_i` (timestamp) | `occurred_at` |
| `K_i` (keywords) | Derived: extract from payload during projection |
| `G_i` (tags) | Derived: event_type hierarchy (dot-namespaced) |
| `X_i` (context description) | Derived: LLM-generated summary during projection |
| `e_i` (embedding) | Derived: embed payload during projection |
| `L_i` (links) | Neo4j edges to related events |

**Recommendation**: Keep the Postgres ledger lean (raw events). Derive enriched attributes during projection and store them as Neo4j node properties.

#### Pattern 5: Bidirectional Evolution (from A-MEM)

When new events arrive that relate to existing graph nodes, those existing nodes should be updated (in Neo4j, not Postgres) with refined context. This enables the graph to represent the current understanding, not just the historical record.

**Recommendation**: Implement as a secondary projection pass: after MERGE-ing new events, run an evolution step that updates contextual descriptions and keywords on related existing nodes. The Postgres ledger remains immutable; evolution happens only in Neo4j.

#### Pattern 6: Intent-Aware Retrieval (from MAGMA)

MAGMA's query classification (Why/When/Who-What) with intent-specific edge weights is directly applicable:

```python
# Example: retrieval weights by query intent
INTENT_WEIGHTS = {
    "why":    {"CAUSED_BY": 5.0, "FOLLOWS": 1.0, "SIMILAR_TO": 2.0, "REFERENCES": 2.0},
    "when":   {"CAUSED_BY": 1.0, "FOLLOWS": 4.0, "SIMILAR_TO": 0.5, "REFERENCES": 1.0},
    "what":   {"CAUSED_BY": 2.0, "FOLLOWS": 1.0, "SIMILAR_TO": 3.0, "REFERENCES": 6.0},
    "general":{"CAUSED_BY": 2.0, "FOLLOWS": 2.0, "SIMILAR_TO": 2.0, "REFERENCES": 2.0},
}
```

**Recommendation**: Implement intent classification in the API layer. Pass intent to the graph query engine to weight edge traversal in Cypher queries.

#### Pattern 7: Memory Tier Mapping (from Survey)

Map the survey's six cognitive memory types to our graph structure:

| Memory Tier | Our Implementation |
|-------------|-------------------|
| Working memory | Current session context (bounded subgraph query) |
| Episodic memory | Session-scoped temporal chains in Neo4j |
| Semantic memory | Cross-session entity and concept nodes |
| Procedural memory | Tool usage patterns and workflow sequences |
| Associative memory | Semantic similarity edges across sessions |

**Recommendation**: Use session_id to scope episodic memory. Cross-session entity resolution creates semantic memory. Tool usage sequences create procedural memory. These emerge naturally from typed edge projection.

#### Pattern 8: Bounded Traversal with Budget (from MAGMA)

MAGMA enforces max depth (5 hops) and node budget (200 nodes) during traversal. This aligns with our bounded query principle.

**Recommendation**: Already part of our design. Confirm these as sensible defaults: max_depth=5, max_nodes=200, timeout per query.

### Gaps Identified (Opportunities for Our Project)

1. **Event sourcing as provenance**: None of these papers use true event sourcing with an immutable ledger as the source of truth. Our architecture (Postgres ledger + Neo4j projection) is ahead of the literature here. We should emphasize this as a differentiator.

2. **Decay and forgetting**: Both MAGMA and A-MEM lack explicit decay mechanisms. The survey mentions PageRank variants and decay functions but gives no specifics. Our project should implement configurable decay (time-based exponential decay, access-frequency weighting) in the Neo4j projection.

3. **Rebuild-from-events**: No paper discusses rebuilding the graph from the event log. Our "Neo4j is disposable and rebuildable" principle is unique and valuable -- it means we can re-project with different schemas, edge types, or enrichment strategies without losing data.

4. **Multi-agent provenance**: These papers focus on single-agent memory. Our schema already includes agent_id and trace_id, enabling multi-agent provenance tracking that no paper addresses.

---

## Summary of Recommendations for Context-Graph Project

| Priority | Recommendation | Source |
|----------|---------------|--------|
| P0 | Adopt multi-typed edges in Neo4j projection (temporal, causal, semantic, entity) | MAGMA |
| P0 | Confirm dual-stream write architecture (Postgres fast path + Neo4j slow path) | MAGMA |
| P1 | Add intent-aware retrieval with edge-type weighting | MAGMA |
| P1 | Enrich Neo4j nodes with derived attributes (keywords, tags, embeddings) during projection | A-MEM |
| P1 | Implement memory tier scoping (working/episodic/semantic/procedural) via session and entity resolution | Survey |
| P2 | Add bidirectional evolution pass in projection worker | A-MEM |
| P2 | Implement configurable decay functions for edge/node relevance scoring | Survey |
| P2 | Build bounded traversal with intent-specific depth/budget defaults | MAGMA |
| P3 | Leverage rebuild-from-events for schema evolution and re-projection | Original (gap in literature) |
| P3 | Multi-agent provenance tracking using agent_id + trace_id | Original (gap in literature) |
