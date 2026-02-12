# Cluster 3: Neuroscience-Inspired Memory Patterns for AI

## Research Summary

This report synthesizes three papers exploring how neuroscience memory mechanisms — hippocampal indexing, consolidation, replay, forgetting, and complementary learning systems — can be translated into computational architectures for AI agent memory. Each paper is analyzed for its neuroscience foundations and then mapped to concrete architectural patterns applicable to our context-graph project.

---

## Paper 3.1: AI Meets Brain — A Unified Survey on Memory Systems from Cognitive Neuroscience to Autonomous Agents

- **Authors**: Jiafeng Liang, Hao Li, Chang Li, Jiaqi Zhou, Shixin Jiang, Zekun Wang, Changkai Ji, Zhihao Zhu, Runxuan Liu, Tao Ren, Jinlan Fu, See-Kiong Ng, Xia Liang, Ming Liu, Bing Qin
- **Date**: December 29, 2025
- **Link**: https://arxiv.org/abs/2512.23343

### Key Contributions

This survey provides the most comprehensive bridge between cognitive neuroscience memory research and LLM-based agent memory systems published to date. It establishes a parallel taxonomy of memory types, storage mechanisms, and management lifecycles across biological and artificial systems.

### Neuroscience Memory Taxonomy

The survey identifies the following memory classification with biological and agent analogs:

**Biological Memory Types:**

| Type | Duration | Capacity | Function |
|------|----------|----------|----------|
| **Short-term / Working Memory** | 15-20 seconds | 4-9 items (Miller's 7 +/- 2) | Rapid environmental response, active manipulation |
| **Episodic Memory** | Minutes to lifetime | Vast | Specific events with temporal/spatial context; "mental time travel" |
| **Semantic Memory** | Minutes to lifetime | Vast | Factual knowledge, concepts, rules; context-free |
| **Procedural Memory** | Minutes to lifetime | Skill-based | Motor skills, learned behaviors; implicit |

**Agent Memory Analogs:**

| Biological Type | Agent Implementation | Scope |
|----------------|---------------------|-------|
| Short-term / Working | Context window, active attention buffer | Inside-trail (single trajectory) |
| Episodic | Tool-augmented logs: tasks attempted, tools invoked, results | Cross-trail (persists across trajectories) |
| Semantic | Knowledge repository: facts, concepts, rules without tool dependency | Cross-trail |
| Procedural | Skill libraries: semantic vectors as keys, executable code as values | Cross-trail |

**LLM-Specific Memory:**
- **Parametric Memory**: Encoded in network weights (slow to update, broad coverage)
- **Working Memory**: Context window contents (fast, limited capacity)
- **Explicit External Memory**: RAG-based retrieval systems (extensible, requires indexing)

### Hippocampal-Neocortical Consolidation

This is the central biological mechanism with the most direct relevance to our architecture.

**Biological Process:**
1. New information is initially encoded in distributed neocortical regions
2. Signals converge in the hippocampus for integrated processing
3. The hippocampus functions as an **index** that reactivates distributed memory traces
4. During rest/sleep, hippocampus and neocortical regions show coordinated reactivation (replay)
5. Through **systems consolidation**, memories gradually shift from hippocampal dependence to neocortical sustenance
6. Rehearsal strengthens memories mainly in neocortical and hippocampal-neocortical interaction regions

**Key Insight — Hippocampal Indexing Theory:**
The hippocampus does not store the full memory. It stores an index — pointers to the distributed cortical representations that together constitute the memory. Retrieval involves reactivating this index, which in turn reactivates the distributed cortical pattern.

**Mapping to Agent Systems:**
- **Fast Learning Phase** (Hippocampal): Hierarchical memory trees and temporal flows capture raw experiences rapidly
- **Consolidation Phase** (Neocortical): Recursive summarization abstracts raw data into structured, reusable forms
- Chen et al.'s hierarchical memory tree structure — "constructing a pyramid-like index through upward recursive summarization" — directly parallels hippocampal indexing

### Complementary Learning Systems (CLS) Theory

The survey implicitly describes CLS throughout:

| System | Biological Substrate | Characteristics | Agent Analog |
|--------|---------------------|-----------------|--------------|
| **Fast/Flexible** | Hippocampus | Rapid formation of specific neural representations; detailed episodic capture | Inside-trail memory; fine-grained procedural steps; event ledger |
| **Slow/Stable** | Neocortex | Consolidates abstract patterns; resistant to interference | Cross-trail memory; generalized strategies; knowledge graphs |

The tension between these systems manifests in agents as the balance between:
- **Immediate context** (high-priority items in active, persistently firing state)
- **Background knowledge** (items outside attention stored silently but still retrievable)

### Memory Management Lifecycle

**Biological Lifecycle:**
1. **Encoding (Formation)**: Information rapidly encoded into neural representations
2. **Consolidation (Storage)**: Hippocampal replay writes cross-event structures into medial prefrontal cortex
3. **Retrieval**: Contextual cues activate hippocampal index, which reactivates distributed cortical patterns
4. **Reconsolidation (Update)**: Retrieval opens a plasticity window — traces can be updated, strengthened, or weakened
5. **Forgetting (Decay)**: Adaptive elimination of low-value information to reduce cognitive load

**Agent Lifecycle:**
1. **Memory Extraction**: Raw information distilled into structured records (flat, hierarchical, or generative paradigms)
2. **Memory Updating**: Dynamically refreshed within trajectories, maintained across them
3. **Memory Retrieval**: Similarity matching or multi-factor approaches
4. **Memory Application**: Contextual augmentation or parameter internalization

**Extraction Paradigms (with increasing sophistication):**
- **Flat**: Linear memory with timestamps and importance scores (Park et al., Generative Agents)
- **Hierarchical**: Pyramid indexing through recursive summarization (Chen et al.)
- **Generative**: LLM-based synthesis of memory content

### Memory Replay Mechanisms

**Biological Replay:**
- During rest, hippocampus and relevant neocortical regions show coordinated reactivation
- Replay writes cross-event structures into medial prefrontal cortex
- Serves both consolidation (strengthening) and integration (cross-linking) functions

**Agent Replay Analogs:**
- **Experience Replay** (RL-style): Yu et al.'s long-range text stream management — agents autonomously retain and overwrite memory
- **Reflection-based Replay**: ExpeL extracts processed insights from training tasks; Reflexion uses language feedback for self-optimization; ReasoningBank synthesizes reasoning strategies from successes and failures
- **Dynamic Consolidation**: MEMORYLLM constructs a fixed-size memory pool in latent space, balancing new and old knowledge

### Working Memory Capacity Limits (Miller's 7 +/- 2)

**Biological Constraint:**
- Short-term memory maintains only 4-9 pieces of information simultaneously
- When capacity is approached, the brain dynamically reallocates resources, prioritizing task-relevant information
- Prefrontal cortex regulates storage by setting priorities and allocating limited memory resources across items

**Agent Manifestation:**
- The "lost-in-the-middle" phenomenon in LLMs: quadratic attention complexity causes information in the middle of long contexts to be less attended
- Mitigation strategies:
  - **Importance scoring**: Park et al.'s memory objects with timestamps and importance scores
  - **Virtual context management**: Packer et al.'s paging between main context and archival external storage
  - **Gist memory**: Lee et al.'s compressed indices with on-demand raw text retrieval
  - **Context folding**: Ye et al.'s agents that actively restructure their history, deciding which spans to preserve or compress

### Emotional Salience and Priority Weighting

**Biological Mechanism:**
- Prefrontal cortex regulates memory storage by setting priorities
- High-priority items maintained in active, persistently firing state
- Emotional events receive enhanced encoding and preferential consolidation

**Agent Analogs:**
- Explicit importance weighting in memory objects
- SAGE agent: borrowed from the Ebbinghaus forgetting curve, adaptively eliminates low-value information
- Task-relevance scoring as a proxy for emotional salience

### Memory Reconsolidation

**Biological Process:**
The retrieval process itself opens a plasticity window during which underlying memory traces can be updated, strengthened, or weakened. This means memories are not fixed after initial consolidation — they become labile again upon retrieval.

**Agent Analog:**
- Reflexion: agents reflect on themselves and update contextual memory through language feedback
- ExpeL: extracts insights from training tasks, enhancing abstraction upon each retrieval
- Autonomous evolution: Xu et al.'s dynamic mechanism triggers link generation and memory evolution without predefined rules

### Forgetting as Active Process

**Biological Basis — Ebbinghaus Forgetting Curve:**
- Memory retention R = e^(-t/S) where t = time elapsed, S = memory strength
- Retention declines exponentially unless reinforced through spaced repetition
- Forgetting is not failure — it is an adaptive mechanism that maintains efficiency

**Agent Implementation:**
- SAGE agent explicitly applies Ebbinghaus curve-inspired adaptive elimination of low-value information
- MEMORYLLM: fixed-size memory pool that balances new and old knowledge, suppressing disordered growth
- Agents must possess forgetting and dynamic evolution mechanisms similar to humans to maintain efficiency and relevance

### Biological-to-Computational Mapping Summary

| Biological Mechanism | Computational Analog | Implementation Pattern |
|---------------------|---------------------|----------------------|
| Hippocampal fast encoding | Append-only event ledger | Postgres immutable events |
| Neocortical slow consolidation | Graph projection, knowledge base | Neo4j derived projection |
| Hippocampal indexing | Hierarchical summarization, KG triples | Graph node indexing with provenance |
| Systems consolidation | Async projection worker | Worker polls events, MERGE into graph |
| Memory replay | Experience replay, reflection | Periodic re-processing of events |
| Working memory limits | Context window management | Bounded query results, pagination |
| Importance weighting | Priority scoring | Event importance metadata |
| Reconsolidation | Update-on-retrieval | Mutable graph nodes from immutable events |
| Forgetting curve | TTL-based decay, importance pruning | Temporal decay scoring on graph queries |

---

## Paper 3.2: HiMeS — Hippocampus-Inspired Memory System for Personalized AI Assistants

- **Authors**: Hailong Li, Feifei Li, Wenhui Que, Xingyu Fan
- **Date**: January 6, 2026
- **Link**: https://arxiv.org/abs/2601.06152

### Key Contributions

HiMeS introduces a dual-memory AI assistant architecture that directly implements hippocampus-neocortex cooperation for personalized dialogue systems. It demonstrates that biologically-inspired memory separation (short-term vs. long-term) with an RL-trained compression/retrieval module substantially outperforms conventional RAG pipelines.

### Architecture Overview

**Two-Module Design:**

1. **Short-Term Memory (STM) Module** — Hippocampal analog
   - Compresses recent dialogue into refined retrieval queries
   - Proactively pre-retrieves documents from knowledge base
   - Trained via supervised fine-tuning (SFT) then reinforcement learning (GRPO)

2. **Long-Term Memory (LTM) Module** — Neocortical analog
   - Distributed storage of user-specific historical interactions
   - Hierarchical topic-based indexing (Atomic Topic Modeling with 16 categories)
   - Re-ranks retrieved documents using attention-inspired scoring

### Biological Mapping

| Brain Region | HiMeS Component | Function |
|-------------|-----------------|----------|
| **Hippocampus** | Short-term memory extractor | Rapid encoding, compression of recent experience, bridging to retrieval |
| **Prefrontal Cortex** | Query rewriting policy | Contextually grounded retrieval decisions, working memory management |
| **Neocortex** | Long-term partitioned storage | Distributed, topic-organized persistent memory with reactivation |

### Short-Term Memory: RL-Trained Query Compression

**Two-Stage Training Pipeline:**

**Stage 1 — Supervised Fine-Tuning (SFT):**
- Multi-agent simulation generates synthetic training examples from raw dialogues
- Persona modeling creates realistic dialogue-rewriting pairs
- Trains the rewriter to produce queries that "contain all key information from historical dialogue with no redundancy/ambiguity/errors/repetition"

**Stage 2 — RL Optimization (GRPO):**
- Group Relative Policy Optimization — compares samples within groups rather than using separate value networks
- **Reward Signal (HSER — Hard Supervised Explicit Reward):**
  - `reward = Rouge_L_F1 + alpha * ExactMatch + beta * Hit`
  - Rouge-L F1: semantic similarity to ground truth
  - Exact Match: binary correctness
  - Hit: whether response appears in RAG-retrieved content
- Lightweight — no separate value network needed

**Pre-Retrieval Mechanism:**
The rewritten query directly triggers document retrieval. The rewriter learns to produce queries that will yield the best retrieval results, effectively implementing anticipatory memory access similar to hippocampal pre-activation.

### Long-Term Memory: Distributed Cortical Storage

**Atomic Topic Modeling (ATM):**
- Partitions user queries into 16 categories covering topics likely in daily conversation
- Subcategories provide granular organization
- Hierarchical tree indexing enables fast, accurate retrieval

**Re-Ranking Algorithm (Attention-Inspired):**
1. Retrieve top-n historical queries similar to current query
2. Chunk retrieved documents
3. Compute attention scores: `score_i = mean(sim(embed(chunk_i), embed(history)))`
4. Re-rank chunks, selecting top-k highest-scoring content
5. Simulates cortical reactivation — historical patterns activate and enhance current retrieval

### Memory Consolidation Process

1. Recent dialogue (short-term experience) undergoes compression into refined queries
2. Queries pre-retrieve relevant documents from knowledge base
3. Historical queries (long-term memory) activate and re-rank retrieved content
4. The combined short-term + long-term signal produces the final context
5. Over time, historical interactions accumulate in the distributed store, simulating consolidation

### Experimental Results

| Configuration | Contextual Alignment | Question Relevance |
|--------------|---------------------|-------------------|
| Native RAG baseline | 20.24 | 70.52 |
| STM alone (STM RAG) | 43.12 | 79.00 |
| LTM alone (LTM RAG) | 21.84 | 70.77 |
| **HiMeS full system** | **55.55** | **90.93** |

Key finding: STM alone provides a massive improvement (+113% contextual alignment), confirming that hippocampal-style compression is the most impactful component. LTM alone provides marginal gains. But the full system combining both achieves the best results — both memory systems are complementary.

**Cross-LLM Transfer:** HiMeS maintains performance across DeepSeek-V3, Qwen3-235B, and Kimi-K2 with no significant degradation, validating the memory system's independence from the underlying language model.

### Architectural Lessons for Context Graph

1. **Compression before retrieval**: The STM module shows that compressing/rewriting queries before retrieval is more effective than naive retrieval. For our system: the projection worker could generate compressed summaries of event sequences that serve as efficient retrieval keys.

2. **Dual-path retrieval**: Combining a fast recent-context path (STM) with a slow historical-context path (LTM) is directly analogous to our Postgres (fast writes, recent events) + Neo4j (consolidated graph, historical patterns) architecture.

3. **RL for retrieval policy**: The reward function combining semantic similarity + exact match + retrieval hit is a pattern we could adopt for tuning retrieval relevance in graph queries.

4. **Topic-based partitioning**: ATM's 16-category organization suggests that agent memory benefits from domain-aware partitioning rather than flat storage. Our graph could use typed node hierarchies.

---

## Paper 3.3: HiCL — Hippocampal-Inspired Continual Learning

- **Authors**: Kushal Kapoor, Wyatt Mackey, Yiannis Aloimonos, Xiaomin Lin
- **Date**: August 19, 2025 (revised November 20, 2025)
- **Link**: https://arxiv.org/abs/2508.16651

### Key Contributions

HiCL provides the most detailed computational mapping of hippocampal circuitry to a working system. It demonstrates that mirroring the brain's trisynaptic circuit (EC -> DG -> CA3 -> CA1) as a software pipeline effectively mitigates catastrophic forgetting in continual learning, achieving near state-of-the-art results at lower computational cost.

### Hippocampal Circuit to Architecture Mapping

| Brain Region | HiCL Component | Function | Mathematical Operation |
|-------------|---------------|----------|----------------------|
| **Entorhinal Cortex (EC II/III)** | Grid-cell encoding layer | Structured relational priors via sinusoidal basis | g_m = sin(W_m * f + phi_m), concatenated |
| **Dentate Gyrus (DG)** | TopK sparse layer (5% activation) | Pattern separation — creates orthogonal codes to prevent interference | z = ReLU(W_DG * g + b), p_sep = TopK(LayerNorm(z), k) where k = floor(0.05 * dim(z)) |
| **CA3** | Two-layer MLP (512, 256) | Pattern completion — nonlinear task-specific refinement | p_comp = LN(ReLU(W_2 * ReLU(W_1 * p_sep + b_1) + b_2)) |
| **CA1** | Integration block | Signal fusion before output | u = [p_sep; p_comp] (concatenation) |
| **Trisynaptic circuit x N** | Multiple experts | Task-specific subnetworks | N parallel pipelines |
| **Hippocampal replay** | Prioritized replay buffer (200-500 samples/task) | Memory consolidation during offline phase | Prioritized sampling for replay |

### Grid-Cell Encoding (Entorhinal Cortex)

**Biological Basis:**
Grid cells in the medial entorhinal cortex fire in hexagonal patterns as an animal navigates space, providing a multi-scale spatial coordinate system. They enable the brain to create structured relational representations.

**Computational Implementation:**
- M=4 parallel 1x1 convolutions with learned phase offsets applied to backbone features
- Formula: g_m = sin(W_m * f + phi_m) for m = 1,...,4
- Final encoding: g = [g_1; g_2; g_3; g_4] (concatenation)
- Purpose: "hexagonal-style embedding enhances discrimination and imposes structured relational priors"

**Architectural Lesson:** Encoding incoming information through multiple parallel sinusoidal bases creates structured, discriminative representations. For agent memory, this suggests that events should be encoded through multiple independent "lenses" (temporal, semantic, relational) before storage.

### Dentate Gyrus Pattern Separation

**Biological Basis:**
The dentate gyrus receives inputs from the entorhinal cortex and creates sparse, orthogonal representations. This prevents interference between similar but distinct memories — two similar experiences are mapped to very different neural patterns.

**Computational Implementation:**
- ReLU projection: z = ReLU(W_DG * g + b_DG)
- Layer normalization then TopK selection: p_sep = TopK(LayerNorm(z), k)
- Sparsity ratio: k = floor(0.05 * dim(z)) — only 5% of neurons activate
- Creates "quasi-orthogonal sparse codes" that naturally modularize representations

**Architectural Lesson:** When storing events in a graph, similar events should be given distinct representations to prevent confusion during retrieval. This maps to ensuring events maintain unique identities (UUIDs, distinct provenance chains) even when semantically similar.

### CA3 Autoassociative Memory (Pattern Completion)

**Biological Basis:**
CA3 is a recurrent network that can reconstruct complete memory patterns from partial cues — the basis of content-addressable memory. Seeing a fragment of a past experience can reactivate the full memory.

**Computational Implementation:**
- Two-layer MLP: p_comp = LN(ReLU(W_2 * ReLU(W_1 * p_sep + b_1) + b_2))
- Takes the sparse DG output and produces a completed, refined representation
- Episodic traces stored implicitly through prototype maintenance via exponential moving averages

**Architectural Lesson:** Graph queries should support pattern completion — given a partial context (a few nodes), the system should be able to reconstruct the full relevant subgraph. This is exactly what our lineage queries do: given a starting node, traverse the graph to recover the full provenance chain.

### DG-Gated Mixture of Experts (Task Routing)

**Biological Basis:**
Different hippocampal circuits specialize for different types of memories. The dentate gyrus helps route incoming information to the appropriate specialized circuit.

**Computational Implementation:**
- **Prototype Maintenance:** u_i <- (1 - mu) * u_i + mu * p_sep^(i), where mu = 0.01 (exponential moving average)
- **Similarity Scores:** s_i = cos(p_sep^(i), u_i) — cosine similarity between current DG codes and expert prototypes
- **Gating Variants:**
  - Soft gating: alpha_i proportional to exp(s_i / tau)
  - Hard gating: alpha_i = 1 if i = argmax_j(s_j), else 0
  - Top-2 or hybrid over top-k similarities
- Key advantage: "eliminates the need for a learned gating network" — routing is based on direct similarity to prototypes

**Architectural Lesson:** Different types of agent interactions (tool calls, observations, decisions) should be routed to specialized processing pipelines. The event_type field in our schema could serve as the routing signal, with specialized graph projections for different event categories.

### Elastic Weight Consolidation (Cortical Consolidation)

**Biological Basis:**
The neocortex slowly consolidates knowledge, protecting important learned patterns while integrating new information. Important synaptic connections are more resistant to change.

**Computational Implementation:**
- EWC loss weighted by inter-task similarity (lambda_ewc = 0.1)
- Full loss: L = lambda_1 * L_phase1 + lambda_2 * L_phase2 + lambda_3 * L_EWC + lambda_4 * L_replay
- Selectively protects parameters that are important for previous tasks
- Inter-task similarity weighting allows related tasks to share more freely while protecting unrelated knowledge

**Architectural Lesson:** When consolidating events into the graph, important relationships (high-traffic paths, frequently queried lineage chains) should be more resistant to pruning or simplification than rarely-accessed ones. This suggests weighted importance scores on graph edges.

### Catastrophic Forgetting Prevention (Three-Pronged)

1. **Sparse DG Separation**: Orthogonal representations reduce task interference (map: distinct event identities prevent confusion)
2. **Prototype-Based Gating**: Routes inputs to appropriate experts, minimizing crosstalk (map: event-type-based routing to specialized projections)
3. **Replay + Consolidation**: Phase II consolidation with contrastive prototypes reinforces current-task alignment while suppressing interference (map: projection worker replays events to strengthen graph structure)

**Phase II Contrastive Loss:**
L_contrastive = (1 - cos(p_sep^(t), u_t)) + sum_{j != t}[max(0, cos(p_sep^(j), u_j) - m)]

This pushes same-task representations closer to their prototype while pushing different-task representations apart — margin m = 0.2.

---

## Cross-Paper Synthesis: Neuroscience Patterns for Agent Memory

### Pattern 1: Dual-Store Architecture (CLS Theory)

All three papers validate the Complementary Learning Systems principle:

| Fast System (Hippocampal) | Slow System (Neocortical) |
|--------------------------|--------------------------|
| Rapid, detailed encoding | Gradual abstraction and consolidation |
| Specific episodes | General patterns |
| High plasticity, interference-prone | Stable, interference-resistant |
| Index-based (pointers to distributed traces) | Content-based (distributed representations) |

**Context-Graph Mapping:**
- **Postgres (Hippocampal)**: Immutable event ledger, append-only, fast writes, stores raw episodes with full detail. Events include precise timestamps, tool calls, payloads — the "index" that points to what happened.
- **Neo4j (Neocortical)**: Derived graph projection, consolidated relationships, optimized for queries. Represents abstracted structure — node types, edge relationships, lineage paths.
- **Projection Worker (Consolidation Process)**: Async worker that polls Postgres events and MERGEs into Neo4j — this IS the systems consolidation process. It transforms raw episodic records into structured relational knowledge.

### Pattern 2: Memory Replay and Consolidation

**Biological Mechanism:** During rest, the hippocampus replays recent experiences, gradually writing structural knowledge into the neocortex.

**Computational Implementation:**
- HiMeS: Historical query reactivation re-ranks current retrieval (replay enhances current performance)
- HiCL: Prioritized replay buffer (200-500 samples/task) reinforces past knowledge
- Survey: MEMORYLLM's fixed-size memory pool balances new and old knowledge

**Context-Graph Implementation:**
- The projection worker already implements replay — it reads events from Postgres and projects them into Neo4j
- **Enhancement opportunity**: Periodic "re-consolidation" passes that re-process old events with updated graph structure, potentially discovering new cross-event relationships
- **Priority replay**: Events with high importance scores or frequent query involvement should be prioritized in re-consolidation

### Pattern 3: Hippocampal Indexing (Sparse Pointers to Distributed Content)

**Biological Mechanism:** The hippocampus stores an index — sparse pointers to distributed cortical representations. It does not store the full memory content.

**Computational Implementations:**
- HippoRAG (referenced in survey): LLM extracts KG triples, uses Personalized PageRank for retrieval
- Survey: Chen et al.'s hierarchical memory tree with recursive summarization
- HiCL: Sparse DG codes (5% activation) serve as compact indices for routing

**Context-Graph Implementation:**
- Events in Postgres contain `payload_ref` — a reference to the full payload, not the payload itself. This IS hippocampal indexing.
- Graph nodes in Neo4j store type, attributes, and provenance metadata — structural indices, not full content
- Retrieval starts from the graph index (Neo4j) and can dereference to full events (Postgres) when needed
- **Enhancement opportunity**: Build hierarchical summarization layers in the graph — session summaries, agent-level summaries — following the pyramid indexing pattern

### Pattern 4: Pattern Separation and Completion

**Biological Mechanism:**
- **Pattern Separation** (DG): Similar inputs mapped to orthogonal representations to prevent confusion
- **Pattern Completion** (CA3): Partial cues reconstruct full memories

**Computational Implementation (HiCL):**
- DG: TopK sparsity with 5% activation creates quasi-orthogonal codes
- CA3: MLP-based completion from sparse to full representation

**Context-Graph Implementation:**
- **Pattern Separation**: Each event has a unique `event_id` (UUID) and `global_position` (BIGSERIAL). Even near-identical events are distinguished by their provenance (agent_id, session_id, trace_id, occurred_at). The graph enforces distinct node identities.
- **Pattern Completion**: Lineage queries implement pattern completion — given a single node, traverse edges to recover the full context chain. Given a `session_id`, reconstruct the complete session graph. Given a `trace_id`, recover the full trace lineage.

### Pattern 5: Forgetting as Active Process

**Biological Mechanism:**
- Ebbinghaus curve: R = e^(-t/S) — retention decays exponentially with time
- Forgetting is adaptive — it reduces cognitive load and maintains efficiency
- Spaced repetition counters decay by scheduling reviews at near-forgetting points

**Computational Implementations:**
- SAGE: Ebbinghaus-inspired adaptive elimination of low-value information
- MEMORYLLM: Fixed-size memory pool with balance between new and old
- HiCL: EWC protects important weights while allowing less important ones to drift

**Context-Graph Implementation:**
- The event ledger itself is immutable — we never delete events (this is the "hippocampal" record)
- But the graph projection (Neo4j) CAN implement forgetting:
  - **Temporal decay scoring**: Older graph relationships scored lower in query results unless they have high importance
  - **Access-frequency weighting**: Frequently queried paths maintain high scores; rarely accessed paths decay
  - **Bounded query results**: Already enforced — depth limits, node count limits, timeouts
  - **Importance-weighted retention**: High-provenance-quality paths (verified, corroborated) resist decay more than low-quality ones
- Formula for graph-level decay: `relevance = base_importance * e^(-t/S) + access_boost * recency_factor`

### Pattern 6: Working Memory Capacity Management

**Biological Mechanism:**
- Miller's 7 +/- 2: Working memory holds 4-9 chunks simultaneously
- Brain dynamically reallocates memory resources, prioritizing task-relevant information
- Prefrontal cortex sets priorities across limited memory resources

**Computational Manifestation:**
- LLM "lost-in-the-middle" phenomenon
- Context window as working memory analog

**Context-Graph Implementation:**
- **Bounded queries**: All graph queries enforce depth, node count, and timeout limits (already in design)
- **Atlas response pattern**: Returns paginated results with `has_more` flag — the agent doesn't receive everything, just a working-memory-sized chunk
- **Priority-based context assembly**: When assembling session context, prioritize:
  1. Recent events (temporal recency)
  2. High-importance events (importance scoring)
  3. Directly relevant events (query relevance)
  4. Provenance-rich events (traceability quality)
- **Chunking**: Group related events into coherent "episodes" before returning to the agent, mirroring biological chunking that extends effective working memory capacity

### Pattern 7: Reconsolidation on Retrieval

**Biological Mechanism:**
When a memory is retrieved, it enters a labile state and can be modified before being re-stored. This is reconsolidation — memories are not fixed, they evolve with each access.

**Context-Graph Implementation:**
- Events in Postgres are immutable — they are never modified (this is correct; the raw record must be preserved)
- But the graph projection CAN be updated on query:
  - **Query-triggered enrichment**: When a lineage path is queried, the system could add metadata (query count, last accessed, relevance score) to graph nodes/edges
  - **Derived annotations**: Graph nodes could accumulate derived properties (importance score, access frequency) that are updated each time they participate in a query result
  - **Provenance evolution**: As new events reference old ones (via `parent_event_id`), the graph evolves — old nodes gain new edges, changing their structural importance
- This preserves immutability (raw events unchanged) while allowing the derived graph to evolve — exactly like biological reconsolidation modifies memory traces without changing the original experience

### Pattern 8: Multi-Expert Routing (Specialized Processing)

**Biological Mechanism (HiCL):**
Different hippocampal circuits specialize for different memory types. The dentate gyrus routes incoming information to the appropriate expert circuit based on similarity to learned prototypes.

**Context-Graph Implementation:**
- **Event-type routing**: Different `event_type` values (e.g., `tool.invocation`, `agent.decision`, `observation.received`) could trigger different projection strategies
- **Specialized graph projections**: Different event types might project into different subgraph structures optimized for their query patterns
- **Query routing**: Different query types (lineage vs. session context vs. subgraph) already route to different API endpoints and graph traversal algorithms

---

## Architectural Recommendations for Context-Graph Project

Based on the neuroscience patterns above, here are specific recommendations:

### 1. Formalize the CLS Architecture

Our existing Postgres + Neo4j + Projection Worker architecture already implements CLS. Formalize this by:
- Documenting Postgres as the "hippocampal" fast-write episodic store
- Documenting Neo4j as the "neocortical" consolidated query store
- Documenting the projection worker as the "consolidation" process
- This framing guides future design decisions (e.g., "should this be in Postgres or Neo4j?" becomes "is this a fast episodic capture or a consolidated query pattern?")

### 2. Implement Hierarchical Summarization (Hippocampal Indexing)

Add summarization layers to the graph:
- **Event level**: Raw events (already exists)
- **Episode level**: Groups of related events within a trace, with summary metadata
- **Session level**: Session-wide summaries with key outcomes and patterns
- **Agent level**: Cross-session agent knowledge summaries
- Each level serves as an index to the level below, following the hippocampal indexing pattern

### 3. Add Importance Scoring and Temporal Decay

Implement on graph nodes and edges:
- **Base importance**: Derived from event metadata (explicit importance flag, event type weight)
- **Access frequency**: Incremented on each query participation
- **Temporal decay**: Apply Ebbinghaus-inspired decay: `relevance = importance * e^(-t/S) + access_boost`
- **Query-time scoring**: Use combined relevance score to rank results within bounded queries

### 4. Implement Replay/Re-Consolidation

Add a periodic re-consolidation process:
- Re-processes historical events to discover cross-event relationships
- Updates graph structure with new edges identified by analyzing event sequences
- Prioritizes re-processing of high-importance or frequently-queried event chains
- Runs during "idle time" — analogous to sleep replay

### 5. Bounded Context Assembly (Working Memory)

When returning context to agents:
- Enforce working-memory-inspired limits on response size
- Chunk related events into coherent episodes
- Rank chunks by combined relevance (recency + importance + query relevance)
- Return top-k chunks with pagination for additional context
- This prevents agent context window overflow while maximizing information density

### 6. Pattern Separation in Event Storage

Ensure events maintain distinct identities:
- UUID-based `event_id` for uniqueness (already designed)
- Rich provenance metadata (agent_id, session_id, trace_id, occurred_at) for disambiguation
- Idempotent ingestion (ON CONFLICT DO NOTHING) prevents duplication while preserving separation

---

## Key Takeaways

1. **Our architecture is already neuroscience-aligned.** The Postgres (fast/episodic) + Neo4j (consolidated/relational) + Projection Worker (consolidation process) maps directly to the hippocampal-neocortical Complementary Learning Systems model.

2. **Hippocampal indexing = our provenance model.** Events contain references (`payload_ref`, `parent_event_id`) that serve as indices to distributed content — exactly the hippocampal indexing pattern.

3. **The projection worker IS memory consolidation.** Async polling of events and MERGE into the graph is computationally equivalent to hippocampal replay writing structural knowledge into the neocortex.

4. **Forgetting is a feature, not a bug.** Temporal decay scoring on graph queries implements adaptive forgetting — recent and important information is prioritized, while stale information gracefully degrades.

5. **Bounded queries implement working memory limits.** Our depth/node-count/timeout limits on graph queries mirror the biological constraint that working memory has finite capacity, forcing prioritization.

6. **Reconsolidation = graph evolution from immutable events.** The graph projection can evolve (nodes gain new edges, importance scores update) while the underlying event ledger remains immutable — matching how biological reconsolidation modifies memory accessibility without changing the original trace.

---

## References

- Liang et al. (2025). "AI Meets Brain: Memory Systems from Cognitive Neuroscience to Autonomous Agents." arXiv:2512.23343.
- Li et al. (2026). "HiMeS: Hippocampus-inspired Memory System for Personalized AI Assistants." arXiv:2601.06152.
- Kapoor et al. (2025). "HiCL: Hippocampal-Inspired Continual Learning." arXiv:2508.16651.
- Gutierrez et al. (2024). "HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models." NeurIPS 2024. arXiv:2405.14831.
- Kumaran et al. (2016). "What Learning Systems do Intelligent Agents Need? Complementary Learning Systems Theory Updated." Trends in Cognitive Sciences.
- Teyler & DiScenna (1986). "The Hippocampal Memory Indexing Theory." Behavioral Neuroscience.
- Ebbinghaus (1885). "Memory: A Contribution to Experimental Psychology." (Forgetting curve: R = e^(-t/S))
