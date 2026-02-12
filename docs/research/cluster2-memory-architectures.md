# Cluster 2: Agent Memory Architectures -- Tiers, Types, and Decay

## Research Report

**Researcher**: researcher-2
**Date**: 2026-02-11
**Papers Analyzed**: 3

---

## Table of Contents

1. [Paper 2.1: Memory in the Age of AI Agents](#paper-21-memory-in-the-age-of-ai-agents)
2. [Paper 2.2: Rethinking Memory Mechanisms of Foundation Agents](#paper-22-rethinking-memory-mechanisms-of-foundation-agents)
3. [Paper 2.3: Episodic Memory is the Missing Piece](#paper-23-episodic-memory-is-the-missing-piece)
4. [Cross-Paper Synthesis](#cross-paper-synthesis)
5. [Concrete Algorithms and Scoring Functions](#concrete-algorithms-and-scoring-functions)
6. [Mapping to Context-Graph Project](#mapping-to-context-graph-project)

---

## Paper 2.1: Memory in the Age of AI Agents

**Authors**: Yuyang Hu et al. (47 authors)
**Date**: December 15, 2025
**Link**: https://arxiv.org/abs/2512.13564
**Length**: 102 pages

### Key Contribution

This survey establishes a unified three-lens framework for understanding agent memory -- Forms, Functions, and Dynamics -- moving beyond the traditional short-term/long-term dichotomy that has proven insufficient for contemporary agent memory systems. It explicitly distinguishes agent memory from LLM memory, RAG, and context engineering.

### 1. Memory Forms (How Memory Is Realized)

The survey identifies three dominant physical instantiations of agent memory:

#### Token-Level Memory
Explicit, discrete, externally accessible storage materialized as interpretable text units. Three topological variants:

- **Flat (1D)**: Linear logs, text chunks, sequential buffers. Simple append-only structures.
- **Planar (2D)**: Trees, graphs, single-layer knowledge structures. Enables relational querying.
- **Hierarchical (3D)**: Multi-level pyramids, layered graphs enabling vertical abstraction across granularity levels.

**Trade-offs**: High interpretability and manual editability, but slower access and higher storage overhead compared to latent representations.

#### Parametric Memory
Knowledge embedded in model weights through training or fine-tuning:

- **Internal**: Core model parameters (base weights).
- **External**: Parameter-efficient adapters (LoRA, etc.) attached to base models.

**Trade-offs**: Fast inference, compact representation, but limited updatability and opacity regarding exactly what knowledge is encoded.

#### Latent Memory
Implicit state in hidden activations, KV caches, or learned embeddings:

- Enables efficient cross-modal integration without exposing interpretability.
- Machine-native retention with computational efficiency.
- Unclear persistence boundaries across tasks; potential information leakage risks.

### 2. Memory Functions (What Memory Stores)

A finer-grained taxonomy distinguishing three functional categories:

#### Factual Memory
Records knowledge from agents' interactions with users and the environment. Storage patterns progress through increasing structure:

```
Raw interaction logs --> Entity extraction --> Structured knowledge graphs
```

Examples: user preferences, discovered facts, entity profiles, environmental state.

#### Experiential Memory
Incrementally enhances the agent's problem-solving capabilities through task execution. Organized in a three-tier hierarchy of increasing abstraction:

| Tier | Description | Example |
|------|-------------|---------|
| **Case-based** | Concrete raw trajectories for replay | Full task execution traces |
| **Strategy-based** | Abstracted reusable workflows and insights | "When API fails, try fallback endpoint" |
| **Skill-based** | Executable code, tool APIs, procedures | Compiled tool-use sequences |

**Key insight**: Successful outcomes are distilled upward into reusable templates. This mirrors how human expertise develops from novice (case-based reasoning) to expert (skill-based fluency).

#### Working Memory
An actively managed scratchpad -- dynamic, capacity-limited, interference-controlled. Implements five patterns:

1. **Input condensation**: Compressing raw inputs to essential information
2. **Observation abstraction**: Summarizing environmental observations
3. **State consolidation**: Merging multiple state updates
4. **Hierarchical folding**: Nesting information at multiple granularity levels
5. **Plan-centric representations**: Organizing around current plans/goals

**Scope**: Single-episode context management and long-horizon reasoning within bounded windows.

### 3. Memory Dynamics (Lifecycle Operators)

Three temporal operators govern how memory evolves:

#### Formation Operator (F)
Transforms interaction artifacts into memory candidates. This is described as "active transformation" rather than passive logging:

- **Summarization**: Compressed knowledge extraction from raw traces
- **Distillation**: Essential pattern identification across experiences
- **Structuring**: Organization into schemas (entities, relations, events)
- **Latent embedding**: Continuous vector representation encoding

**Key distinction from simple logging**: "Raw interaction traces are compressed, summarized, or distilled into useful artifacts" -- formation is a creative, lossy transformation.

#### Evolution Operator (E)
Three branches manage memory integrity over time:

**Consolidation** (three levels):
- *Local*: Within-cluster merging of closely related memories
- *Cluster*: Cross-subset aggregation preserving diversity
- *Global*: Full-store reorganization for holistic coherence

**Updating**: Explicit revision mechanisms including model editing with rollback and audit trails. Supports conflict resolution when new information contradicts existing memories.

**Forgetting**: Modules managing recency, efficiency, and coherence:
- Temporal decay (recency-weighted selection)
- Selective removal (capacity management through low-utility item culling)
- Adaptive policies (learning-based determination of retention schedules)
- Deduplication (removing redundant entries)
- Periodic pruning cycles

The survey notes a shift from heuristic-based evolution (e.g., LRU caches) to **RL-driven memory management** where "the agent itself predicts the long-term utility of a memory trace."

#### Retrieval Operator (R)
Multi-stage pipeline:

1. **Timing/Intent**: When and why to retrieve (proactive vs. reactive)
2. **Query Construction**: Decomposition or rewriting of retrieval queries
3. **Strategy Selection**:
   - Lexical (keyword-based matching)
   - Semantic (embedding similarity search)
   - Graph (structured relationship navigation)
   - Generative (synthesis-based -- agent actively constructs a memory representation tailored to current reasoning context)
   - Hybrid combinations
4. **Post-Processing**: Filtering, compression, re-ranking

**Notable advance**: Generative retrieval, where the agent synthesizes a memory representation rather than simply looking up stored records.

### 4. Memory State Evolution (Formal)

The survey provides a high-level formal characterization:

```
M_{t+1} = E(M_t, F(artifacts_t))
```

Where:
- `M_t` = memory state at time t
- `F` = formation operator transforming raw artifacts into memory candidates
- `E` = evolution operator updating memory state with new candidates

The authors note a critical gap: "Lack of formal properties and guarantees for memory lifecycle operators F/E/R -- need to develop mathematical characterizations (monotonicity, stability, boundedness, convergence)."

### 5. Key Distinctions

| Concept | Description | Relation to Agent Memory |
|---------|-------------|-------------------------|
| **LLM Memory** | Architectural (attention, KV cache, sparsity) | Agent memory "fully subsumes" LLM memory |
| **RAG** | Stateless augmentation from static knowledge bases | Agent memory is "self-improving substrate" that evolves |
| **Context Engineering** | Optimizes what fits in context window | Agent memory is the long-lived store that *feeds* context engineering |

---

## Paper 2.2: Rethinking Memory Mechanisms of Foundation Agents

**Authors**: Wei-Chieh Huang et al. (60 authors)
**Date**: January 14, 2026 (revised February 9, 2026)
**Link**: https://arxiv.org/abs/2602.06052

### Key Contribution

Examines agent memory along three orthogonal dimensions -- substrate, cognitive mechanism, and subject -- while centering the "context explosion" problem as the driving force behind memory system design. Provides the most detailed cognitive-science-aligned taxonomy of memory types.

### 1. Memory Substrates: Internal vs. External

#### External Memory
- Stores knowledge **outside** the agent model's parameters or state
- Enables explicit read/write via retrieval and update operations
- Provides scalable, easy-to-update, cross-session retention
- Separates computation (in LLM parameters) from knowledge (in external database)

Four external substrate types:

| Substrate | Description | Use Case |
|-----------|-------------|----------|
| **Vector Index** | Embedding-based with ANN search (HNSW, IVF) | Similarity-based retrieval |
| **Text-Record** | Direct textual storage of interactions/histories | Audit trails, conversation logs |
| **Structural Store** | Graphs, tables, databases with explicit relations | Knowledge graphs, entity relations |
| **Hierarchical Store** | Multi-level organization enabling abstraction | Tiered memory with summarization |

#### Internal Memory
- Stored within model's parameters or state
- Three types:
  - **Weights**: Long-term parameter changes from fine-tuning
  - **Latent-State**: Hidden representations during inference
  - **KV Cache**: Transformer attention caches for multi-turn interaction

### 2. Cognitive Mechanism Taxonomy (Five Types)

This is the most detailed neuroscience-aligned taxonomy across the three papers:

#### Sensory Memory
- Briefly buffers raw perceptual input for downstream processing
- Minimal retention duration
- Functions as initial perception layer
- **Agent analog**: Raw input preprocessing, token-level buffering

#### Working Memory
- Operates under strict capacity constraints
- Supports online information manipulation, reasoning, and control
- Temporary retention during active processing
- **Agent analog**: Context window contents, active scratchpad

#### Episodic Memory
- Stores specific experiences situated in time and context
- Captures individual interaction instances with temporal grounding
- Instance-specific rather than generalized
- **Agent analog**: Interaction logs, task execution traces, session records

#### Semantic Memory
- Accumulates abstract facts and conceptual knowledge
- Independent of specific learning episodes
- Forms general knowledge structures
- **Agent analog**: Knowledge graphs, entity databases, learned rules

#### Procedural Memory
- Captures skills, habits, and action policies
- Expressed implicitly through performance rather than explicit recall
- Represents learned behavioral patterns
- **Agent analog**: Tool-use policies, prompt templates, fine-tuned weights

### 3. Memory Operations Framework

#### Core Operations (Single-Agent)

| Operation | Description |
|-----------|-------------|
| **Storage and Index** | Recording with organizational structure for future retrieval |
| **Loading and Retrieval** | Fetching relevant memories based on queries, similarity, or context |
| **Updates and Refresh** | Modifying existing memories to reflect new information |
| **Compression and Summarization** | Compressing experience into reusable knowledge |
| **Forgetting and Retention** | Selective deletion based on relevance, temporal decay, or explicit policies |

#### Memory Management Policies (Evolution)

Four policy classes for managing memory operations:

1. **Static prompt-based control**: Fixed rules governing memory operations
2. **Dynamic prompt-based control**: Adaptive rules adjusting to context
3. **Fine-tuning-based parameterized policies**: Learned policies encoded in adapter weights
4. **RL-based memory decision policies**: Reinforcement learning optimizing memory operations

### 4. Context Explosion Problem

**The central challenge**: As multi-session data from daily interactions or accumulated context from project work expands exponentially, reliance on a static memory mechanism is insufficient.

The solution direction: Dynamic memory architectures evolving "from a static, predefined, and simple mechanism towards a self-adaptive, self-evolving, and flexible unit" capable of intelligent store, load, summarize, forget, and refine operations.

### 5. Agent-Centric vs. User-Centric Memory

| Dimension | Agent-Centric | User-Centric |
|-----------|---------------|--------------|
| **Focus** | Supporting agent task execution | Supporting user needs and personalization |
| **Content** | Action policies, task knowledge, decision context | User preferences, profiles, behavioral history |
| **Scope** | Multi-agent coordination, shared workspace | Life-long personalization, interaction history |
| **Update trigger** | Task outcomes, environment changes | User feedback, preference drift |

### 6. Memory Lifecycle

The complete lifecycle:

1. **Acquisition**: Initial capture of sensory information and experiences
2. **Consolidation**: Processing raw memories into organized structures
3. **Storage**: Maintaining memories in appropriate substrates
4. **Retrieval**: Accessing relevant memories when needed
5. **Integration**: Combining retrieved memories with current processing
6. **Update**: Modifying memories based on new information
7. **Decay/Forgetting**: Gradual or explicit removal of outdated information

### 7. Inter-Memory Type Interactions

The taxonomy defines directional flows between memory types:

```
Sensory --> Working --> Long-term (Episodic / Semantic)
                              |
                    Episodic --consolidation--> Semantic
                              |
                    Procedural <-- informed by Semantic + Episodic
```

Working memory acts as the intermediary integrating multiple memory types during active reasoning.

---

## Paper 2.3: Episodic Memory is the Missing Piece

**Authors**: Mathis Pink, Qinyuan Wu, Vy Ai Vo, Javier Turek, Jianing Mu, Alexander Huth, Mariya Toneva
**Date**: February 10, 2025
**Link**: https://arxiv.org/abs/2502.06975

### Key Contribution

A position paper making a focused argument that episodic memory -- with five specific properties -- is the critical missing component for building long-term LLM agents. Provides the clearest definition of what episodic memory must entail and proposes a three-system architecture.

### 1. Five Key Properties of Episodic Memory

The properties cluster into two categories:

**Operational Properties** (how the system works with memory):

| Property | Definition | Agent Implication |
|----------|-----------|-------------------|
| **Long-Term Storage** | Capacity to retain knowledge across an organism's lifetime | Must support retrieval across any number of tokens without degradation |
| **Explicit Reasoning** | Ability to consciously reflect upon and reason about memory content | Agents must answer queries about stored info and use it in internal reasoning |
| **Single-Shot Learning** | Acquired from a single exposure, per complementary learning systems theory | Must encode and retain from singular occurrences without repeated training |

**Content Properties** (what the memory contains):

| Property | Definition | Agent Implication |
|----------|-----------|-------------------|
| **Instance-Specific Memories** | Stores information specific to an individual sequence of events with distinct temporal contexts | Preserves particularity; enables reasoning about specific past actions and consequences |
| **Contextual Relations** | Binds context (when, where, why) to memory content | Enables retrieval based on contextual cues; remembers circumstances, not just facts |

### 2. How Episodic Memory Differs from Other Types

| Property | Episodic | Semantic | Procedural | Working |
|----------|----------|----------|------------|---------|
| Long-Term Storage | Yes | Yes | Yes | **No** |
| Explicit Reasoning | Yes | Yes | **No** | Yes |
| Single-Shot Learning | Yes | **No** | **No** | Yes |
| Instance-Specific | Yes | **No** | **No** | Yes |
| Contextual Relations | Yes | **No** | **No** | Yes |

**Key insight**: Working memory satisfies four of five properties but lacks long-term persistence. Episodic memory uniquely combines working memory's operational richness with long-term durability.

### 3. Three-System Architecture

The paper proposes a unified architecture integrating three memory substrates:

```
+------------------+       (b) Encoding        +------------------+
|                  | ----------------------->   |                  |
|  In-Context      |                            |  External        |
|  Memory          | <-----------------------   |  Memory          |
|  (Working)       |       (c) Retrieval        |  (Episodic)      |
+------------------+                            +------------------+
                                                       |
                                                       | (a) Consolidation
                                                       v
                                                +------------------+
                                                |  Parametric      |
                                                |  Memory          |
                                                |  (Semantic)      |
                                                +------------------+
```

**Flow**:
- **(b) Encoding**: Limited in-context memory offloads content to external storage (fast, single-shot)
- **(c) Retrieval**: Stored episodes reinstated into in-context memory for reasoning
- **(a) Consolidation**: External memory contents periodically merge into parametric memory (slow, generalizing)

### 4. Episode Segmentation

A critical design question: When and how to segment a continuous stream of agent experience into episodes?

- LLMs can segment text into meaningful events similarly to humans
- Approaches leveraging **model surprise** to detect event boundaries and bundle related segments
- Long-context advances help capture high-fidelity contextual information compressible for future retrieval

### 5. Retrieval Strategies

Three approaches for reinstating episodic memories:

1. **Token prepending**: RAG-style prepending of retrieved text to input sequences
2. **Memory tokens**: Manipulating representational states via learned tokens within transformers
3. **Representation adaptation**: Modifying internal model representations based on retrieved content

### 6. Consolidation: Episodic to Parametric

- **Purpose**: Prevent external memory overflow; enable generalization from instances
- **Techniques**: Context distillation, parametric knowledge editing, localized fine-tuning
- **Challenge**: Determining consolidation timing; compressing multiple episodic instances into abstract parametric knowledge without catastrophic interference
- **Biological parallel**: Hippocampal replay during sleep -- episodic traces replayed and gradually absorbed into neocortical (semantic) representations

### 7. Limitations of Current Approaches

| Approach | Limitation |
|----------|-----------|
| **In-Context Only** | Computational costs scale with sequence length; irreversible info loss from KV-cache optimization; eventual forgetting in very long sequences |
| **External Memory Only** | Lacks rich contextual detail binding; no single-shot evaluation; no mechanism to update parametric memory |
| **Parametric Only** | Cannot achieve single-shot learning; lacks instance-specificity; knowledge editing causes interference |

### 8. Research Questions Framework

| RQ | Topic | Design Question |
|----|-------|-----------------|
| RQ1 | Storage Representation | Non-parametric RAG-like databases with metadata, or compressed parametric representations? |
| RQ2 | Episode Segmentation | How to detect event boundaries using model surprise? |
| RQ3 | Retrieval Mechanism | How to select and reintegrate relevant episodes via contextual cuing? |
| RQ4 | Long-Context Integration | How to combine external memory with extended context windows? |
| RQ5 | Consolidation Strategy | How to implement localized fine-tuning preventing catastrophic forgetting? |
| RQ6 | Evaluation | How to assess contextualized event recall after delays? |

---

## Cross-Paper Synthesis

### Unified Memory Taxonomy

Combining all three papers, the most comprehensive taxonomy is:

```
Agent Memory
├── By Form (Paper 2.1)
│   ├── Token-Level (Flat / Planar / Hierarchical)
│   ├── Parametric (Internal weights / External adapters)
│   └── Latent (Hidden states / KV cache / Embeddings)
│
├── By Cognitive Function (Papers 2.2 + 2.3)
│   ├── Sensory Memory (brief perceptual buffer)
│   ├── Working Memory (active scratchpad, capacity-limited)
│   ├── Episodic Memory (instance-specific, contextually-bound experiences)
│   ├── Semantic Memory (abstract facts, conceptual knowledge)
│   └── Procedural Memory (skills, habits, action policies)
│
├── By Purpose (Paper 2.1)
│   ├── Factual (knowledge from interactions)
│   ├── Experiential (case → strategy → skill hierarchy)
│   └── Working (dynamic scratchpad for current task)
│
└── By Subject (Paper 2.2)
    ├── Agent-Centric (task execution support)
    └── User-Centric (personalization, preference tracking)
```

### Memory Lifecycle -- Unified View

All three papers describe a consistent lifecycle with different terminology:

| Stage | Paper 2.1 | Paper 2.2 | Paper 2.3 |
|-------|-----------|-----------|-----------|
| **Capture** | Formation (F operator) | Acquisition | Encoding (b) |
| **Store** | Token/Parametric/Latent | Internal/External substrates | External memory |
| **Evolve** | Evolution (E operator) | Update, Compress, Forget | Consolidation (a) |
| **Access** | Retrieval (R operator) | Loading and Retrieval | Retrieval (c) |
| **Decay** | Forgetting (within E) | Forgetting and Retention | Parametric absorption |

### Consolidation Patterns -- Convergent View

All papers converge on a multi-level consolidation model inspired by Complementary Learning Systems (CLS) theory:

| Level | Biological Analog | Agent Implementation |
|-------|-------------------|---------------------|
| **Fast encoding** | Hippocampal rapid learning | Single-shot storage in external episodic store |
| **Replay** | Hippocampal offline replay | Background processing of stored episodes |
| **Consolidation** | Neocortical slow integration | Episodic-to-semantic abstraction; merging into knowledge graph or parametric memory |
| **Generalization** | Cortical schema formation | Extracting reusable strategies/skills from specific experiences |

### Decay and Forgetting -- Convergent Strategies

| Strategy | Description | Papers |
|----------|-------------|--------|
| **Temporal decay** | Exponential decay based on time since last access | All three |
| **Importance-weighted retention** | LLM-judged importance scores protect salient memories | 2.1, 2.2 |
| **Relevance-based pruning** | Low-relevance memories pruned during capacity management | 2.1, 2.2 |
| **Consolidation-driven forgetting** | Episodic memories absorbed into semantic store, then pruned | 2.1, 2.3 |
| **Deduplication** | Removing redundant entries | 2.1, 2.2 |
| **RL-driven forgetting** | Agent learns to predict long-term utility of memory traces | 2.1 |

---

## Concrete Algorithms and Scoring Functions

### Park et al. (2023) Retrieval Scoring -- Referenced by Papers 2.1 and 2.2

The foundational scoring formula from Generative Agents (Park et al., 2023), cited extensively by the surveyed papers:

```
score(memory, query) = alpha_recency * recency(memory)
                     + alpha_importance * importance(memory)
                     + alpha_relevance * relevance(memory, query)
```

**Component definitions**:

| Component | Formula | Details |
|-----------|---------|---------|
| **Recency** | `0.995 ^ hours_since_last_access` | Exponential decay; 0.995 per hour = ~30% retention after 24h |
| **Importance** | LLM-rated 1-10 scale | "1 = purely mundane (brushing teeth), 10 = extremely poignant (breakup)" |
| **Relevance** | `cosine_similarity(embed(memory), embed(query))` | Embedding-based semantic similarity |
| **Normalization** | Min-max scaling to [0,1] for each component | Ensures balanced contribution |
| **Weights** | alpha_recency = alpha_importance = alpha_relevance = 1 | Equal weighting in original paper |

### MemoryBank Ebbinghaus Forgetting Curve

```
R = e^(-t/S)
```

Where:
- `R` = memory retention strength (0 to 1)
- `t` = time elapsed since encoding
- `S` = memory stability (increases with each successful recall)

**Key mechanism**: Each time a memory is successfully recalled, its stability `S` increases, making it more resistant to future decay. This creates a "use it or lose it" dynamic.

### Reflection Trigger (Park et al.)

```
if sum(importance_scores[recent_memories]) > threshold (150):
    trigger_reflection()
```

**Reflection process**:
1. Identify salient questions from recent memories
2. Retrieve relevant records as evidence
3. Generate higher-level inferences via LLM
4. Store reflections as new memory objects (forming hierarchical reflection trees)

### Advanced Scoring (2024-2025 Evolution)

Recent systems replace fixed weights with learned functions:

```
# MoE (Mixture of Experts) gate function for dynamic weight learning
weights = MoE_gate(current_state, memory_state)
score = weights[0] * semantic_similarity
      + weights[1] * recency_score
      + weights[2] * importance_score
```

**SAGE/MARK systems** additionally incorporate:
- Ebbinghaus forgetting curves
- Explicit salience scoring
- Trust/persistence scoring per memory item
- Dynamic balance between short-term and long-term retention

### Experiential Memory Distillation Pipeline (Paper 2.1)

```
Case-based (raw traces)
    |-- frequency analysis / outcome scoring
    v
Strategy-based (abstracted workflows)
    |-- successful pattern extraction / generalization
    v
Skill-based (executable procedures)
```

Each level involves:
- **Selection**: Which cases to promote (based on success rate, novelty, coverage)
- **Abstraction**: Removing instance-specific details while preserving causal structure
- **Verification**: Testing abstracted strategy against held-out cases

---

## Mapping to Context-Graph Project

### How These Memory Models Map to Our Architecture

| Memory Concept | Context-Graph Component | Implementation Notes |
|----------------|------------------------|---------------------|
| **Episodic Memory** | Postgres immutable event ledger | Events are instance-specific, temporally ordered, contextually-bound records -- they ARE episodic memories. Each event captures who, what, when, where (agent_id, event_type, occurred_at, session_id, trace_id). |
| **Semantic Memory** | Neo4j graph projection | The graph IS semantic memory -- abstract relational knowledge derived from episodes. Entities, relationships, and attributes stripped of temporal specificity. |
| **Working Memory** | API session context endpoint | The `/v1/context/{session_id}` endpoint retrieves relevant context for active sessions -- this is the agent's working memory. |
| **Procedural Memory** | Not yet implemented | Could be tool-use patterns and action policies derived from event sequences. |
| **Sensory Memory** | Event ingestion buffer | Raw events arriving at `/v1/events` before processing. |
| **Memory Formation** | Event ingestion + validation | `domain/validation.py` transforms raw payloads into validated event records. |
| **Memory Consolidation** | Projection worker | `worker/projector.py` consolidates episodic events into semantic graph -- this IS episodic-to-semantic consolidation. |
| **Memory Retrieval** | Graph query endpoints | Subgraph queries and lineage traversals implement structured retrieval. |
| **Memory Decay** | Not yet implemented | Could add TTL-based pruning, importance scoring, and relevance-based retention. |

### Architectural Alignment with Three-System Model (Paper 2.3)

```
Context-Graph Architecture          <==>    Three-System Model
─────────────────────────────────          ─────────────────────
API Context Window (per-request)    <==>    In-Context / Working Memory
Postgres Event Ledger               <==>    External / Episodic Memory
Neo4j Graph Projection              <==>    Parametric / Semantic Memory
Projection Worker                   <==>    Consolidation Process
```

### Design Recommendations Based on Research

#### 1. Event-as-Episode Design
The event schema already captures the five properties of episodic memory identified in Paper 2.3:

- **Long-term storage**: Immutable Postgres ledger with BIGSERIAL ordering
- **Explicit reasoning**: Events are queryable and inspectable via API
- **Single-shot learning**: Each event is captured once (idempotent ON CONFLICT DO NOTHING)
- **Instance-specific**: Each event has a unique event_id with specific payload
- **Contextual relations**: Events carry session_id, trace_id, parent_event_id, agent_id, tool_name

#### 2. Add Memory Scoring to Retrieval
Implement the three-factor scoring model for context retrieval:

```python
def score_memory(event, query, current_time):
    recency = DECAY_FACTOR ** hours_since(event.occurred_at, current_time)
    importance = event.importance_score  # LLM-rated or rule-based
    relevance = cosine_similarity(embed(event), embed(query))
    return normalize(recency) + normalize(importance) + normalize(relevance)
```

#### 3. Add Decay/Forgetting to Graph Projection
The projection worker could implement tiered retention:

- **Hot tier** (< 24h): Full detail in graph
- **Warm tier** (24h - 7d): Summarized nodes, key relationships retained
- **Cold tier** (> 7d): Only high-importance nodes and structural edges retained
- **Archive** (> 30d): Removed from graph, retained in Postgres (source of truth)

#### 4. Implement Reflection as a Consolidation Trigger
When accumulated event importance exceeds a threshold, trigger a consolidation process:

```
if sum(importance[recent_events]) > REFLECTION_THRESHOLD:
    generate_higher_level_nodes()  # Create summary/insight nodes in graph
    update_entity_attributes()     # Enrich semantic graph with patterns
    prune_low_value_events()       # Remove from active graph projection
```

#### 5. Experiential Memory Hierarchy
Map the case-strategy-skill hierarchy to the graph:

- **Case nodes**: Direct event traces (already captured)
- **Strategy nodes**: Derived patterns from repeated successful event sequences
- **Skill nodes**: Compiled tool-use pipelines validated through repeated success

#### 6. Episode Segmentation
Use session boundaries and event parent-child relationships as natural episode boundaries. Consider adding surprise-based segmentation for long sessions:

```
episode_boundary = significant_change_in(
    agent_id, tool_name, event_type_namespace
)
```

### Key Gaps to Address

1. **No importance scoring**: Events lack an importance/salience field. Consider adding an `importance_score` field to the event schema or computing it during ingestion.

2. **No decay mechanism**: The graph projection retains all events equally. Need tiered retention in Neo4j based on recency and importance.

3. **No consolidation triggers**: The projection worker runs on a fixed polling interval. Need event-driven consolidation that responds to accumulated importance.

4. **No procedural memory**: No mechanism to capture and optimize agent tool-use policies from event patterns.

5. **No user-centric memory dimension**: The current schema is agent-centric. User-centric personalization would require additional modeling.

6. **No retrieval scoring**: Graph queries return results without relevance/recency/importance ranking. The Atlas response pattern should include scoring metadata.

---

## Summary of Key Findings

### The field is converging on a unified memory model with these properties:

1. **Multiple memory types are necessary** -- no single mechanism suffices. The five-type cognitive taxonomy (sensory, working, episodic, semantic, procedural) is well-supported across all papers.

2. **Episodic memory is the linchpin** -- it bridges fast single-shot learning and slow generalization through consolidation into semantic memory.

3. **Memory is a lifecycle, not a store** -- formation, evolution (consolidation + forgetting), and retrieval are equally important as storage.

4. **Decay must be active, not passive** -- importance-weighted, access-frequency-adjusted forgetting outperforms simple temporal decay.

5. **Consolidation is the key bridge** -- the episodic-to-semantic transition (hippocampal replay to neocortical integration) is the most important memory operation for long-term agents.

6. **Scoring should be multi-factor** -- recency, importance, and relevance combine for effective retrieval, with learned weights outperforming fixed weights.

7. **Our context-graph architecture maps naturally** -- Postgres (episodic) + Neo4j (semantic) + projection worker (consolidation) closely mirrors the three-system architecture recommended by Paper 2.3.
