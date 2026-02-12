# Production Knowledge Extraction Pipelines: Comprehensive Deep Dive

**Date**: 2026-02-12
**Author**: researcher-2 (enhanced revision)
**Track**: Track 2 -- Production Extraction Pipelines
**Context**: Research for ADR-0013 Knowledge Extraction Pipeline design
**Use Case**: Conversational agents for SMB merchants (payments, disputes, invoicing, shipping, compliance)

---

## 1. Executive Summary

This report examines six production and research systems that extract structured knowledge from conversational data: **Zep/Graphiti**, **Mem0**, **Memoria**, **A-MEM**, **MAGMA**, and **Cognee**. Each solves the core problem of transforming unstructured conversation text into structured graph representations, but with fundamentally different architectural tradeoffs.

**Key findings**:

1. **LLM-based extraction is universal** -- every production system uses LLM prompting as the primary extraction mechanism. The differentiation is in what happens *around* the LLM: deduplication strategies, temporal handling, and conflict resolution.

2. **Separation of extraction concerns wins** -- Zep/Graphiti's evolution from a single "mega-prompt" to six separate extraction tasks (entity extraction, entity dedup, fact extraction, fact dedup, temporal extraction, fact expiration) is the most mature pattern. Parallelizable, testable, and more accurate.

3. **Entity resolution is the hardest unsolved problem** -- all systems struggle with entity deduplication at scale. Graphiti's entropy-gated fuzzy matching (MinHash/LSH/Jaccard with LLM fallback) is the most sophisticated approach. Mem0 relies primarily on embedding similarity with a 0.7 threshold.

4. **Conflict resolution determines system quality** -- the critical differentiator between toy demos and production systems. Mem0 uses LLM-based ADD/UPDATE/DELETE/NOOP classification. Graphiti uses temporal invalidation (bi-temporal edge tracking). Memoria uses exponential decay weighting. These approaches are complementary, not competitive.

5. **Token costs dominate operational expense** -- Graphiti's shift to deterministic front-ends (MinHash/LSH before LLM) reduced extraction costs significantly. Mem0 reports 90%+ token savings vs. full-context approaches. MAGMA achieves 95%+ token reduction through multi-graph traversal.

6. **No system provides event-level provenance** -- this is our key differentiator. Zep tracks episode source IDs on edges but lacks formal provenance chains. Mem0 tracks session IDs. Memoria stores source messages as metadata. None implements DERIVED_FROM-style edges to source events as specified in our ADR-0012.

**Recommendation for our system**: Adopt Graphiti's separated extraction pipeline pattern (Stage 1), Mem0's LLM-based conflict resolution taxonomy (ADD/UPDATE/DELETE/NOOP) extended with our `superseded_by` chain (Stage 2), Memoria's exponential decay weighting for preference ranking (Stage 3), and MAGMA's multi-graph traversal policy for retrieval. Add provenance tracing (DERIVED_FROM edges) as our differentiator across all stages.

---

## 2. System-by-System Deep Dives

### 2.1 Zep/Graphiti

**Repository**: [github.com/getzep/graphiti](https://github.com/getzep/graphiti) (20K+ stars)
**Paper**: [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956) (January 2025)
**License**: Apache 2.0 (open source)
**Status**: Production-deployed, commercially offered as Zep Cloud

#### Architecture Overview

Graphiti implements a temporally-aware dynamic knowledge graph with three hierarchical tiers:

1. **Episode subgraph** -- raw conversational episodes (messages) stored with timestamps
2. **Semantic entity subgraph** -- extracted entities with names, types, summaries, and 1024-dimensional embeddings
3. **Community subgraph** -- detected communities with map-reduce summaries for hierarchical retrieval

The graph uses Neo4j (or FalkorDB/Kuzu/Neptune) as the backend with episodic nodes (raw data), entity nodes (semantic subjects/objects), and typed edges connecting them.

#### Extraction Pipeline: Six Separated Tasks

Graphiti evolved from a single "mega-prompt" combining all extraction tasks to **six separate, parallelizable prompts**. This was the single most important architectural improvement, as noted by their engineering blog:

> "The first iteration combined multiple extraction tasks into one lengthy prompt that included the existing graph as input, the current and last 3 episodes for context, and 35 guidelines on setting fields. This approach couldn't scale as graphs grew larger, and its complexity led to slower processing and less predictable output due to more frequent hallucinations."

The six tasks in execution order:

| Stage | Task | Input | Output | Parallelizable |
|-------|------|-------|--------|----------------|
| 1 | Entity extraction | Current episode + last 4 messages | Candidate entity nodes | Yes (with #3) |
| 2 | Entity deduplication | Candidates + existing graph entities | UUID mapping (merged/new) | No (depends on #1) |
| 3 | Fact/Edge extraction | Episode + resolved entities | Candidate relationship edges | Yes (with #1) |
| 4 | Fact/Edge deduplication | Candidates + existing edges | Merged/new edges | No (depends on #2, #3) |
| 5 | Temporal extraction | Episode context + extracted facts | `valid_at`, `invalid_at` timestamps | No (depends on #3) |
| 6 | Fact expiration/invalidation | New facts + existing contradictory facts | Invalidated edges with `expired_at` | No (depends on #4) |

**Entity extraction prompt** (from `extract_nodes.py`):
- Instructs the LLM to extract significant entities, concepts, or actors
- "ALWAYS extract the speaker/actor as the first node"
- Explicitly excludes temporal information -- "Avoid creating nodes for temporal information like dates, times, or years (these will be added to edges later)"
- Uses full names, avoids abbreviations
- Uses a **reflexion loop**: iteratively validates completeness, prompting the model to identify missed entities until satisfied

**Fact extraction prompt** (from `extract_edges.py`):
- Extracts all factual relationships between given entities based on the current message
- Uses SCREAMING_SNAKE_CASE strings for `relation_type`
- The `fact` field closely paraphrases source sentences without verbatim quoting
- Considers temporal aspects when relevant

**Reflexion** (applied to both nodes and edges):
- Determines "which entities/facts have not been extracted from the given context"
- Iteratively validates completeness by comparing previous messages, current content, and already-extracted items
- This reflexion loop is a key differentiator -- it minimizes extraction omissions

**Key architectural insight**: Each task has its own separate prompt. This "not only makes the output faster, more accurate, and easier to test, but it also allows running many tasks in parallel if they don't directly depend on each other, significantly speeding up the process."

#### Entity Resolution: Entropy-Gated Fuzzy Matching

This is Graphiti's most sophisticated contribution -- a three-tier deduplication strategy that minimizes LLM calls:

**Tier 1 -- Exact Match Fast Path**:
- Aggressively short-circuits on normalized exact matches (lowercase + whitespace collapse)
- Zero compute cost; handles ~40-60% of deduplication in typical workloads

**Tier 2 -- MinHash/LSH Deterministic Fuzzy Matching**:
- Computes approximate Shannon entropy over characters in normalized entity names
- Low-entropy strings (short, repetitive like "AI", "US") are flagged as unstable for fuzzy matching and go directly to Tier 3
- For high-entropy names:
  - Builds 3-gram shingles from entity names
  - Computes MinHash signatures across multiple permutations
  - Buckets by fixed-size bands for locality-sensitive hashing (LSH)
  - Evaluates Jaccard similarity between shingle sets
  - Accepts matches above **0.9 threshold**

**Tier 3 -- LLM-Based Resolution**:
- Only invoked for ambiguous cases that pass Tier 2 but don't clearly match, or for low-entropy strings
- LLM compares extracted entity against candidate with structured comparison
- Generates an updated name and summary upon detecting duplicates

**Two-Pass Process**:
- First pass: resolves per-episode against the live graph
- Second pass: re-runs deterministic similarity across the union of results to catch intra-batch duplicates
- Both passes use the exact/MinHash/LSH/Jaccard path before involving an LLM

**Design rationale**: "LLM-only extraction created variance, retry loops, and token burn in high-throughput graph implementations, with every entity and edge resolution and deduplication requiring a model call. This got expensive fast." Adding deterministic, classical IR front-ends and only falling back to LLMs when necessary was the key cost optimization.

#### Conflict/Contradiction Handling: Bi-Temporal Edge Tracking

Graphiti implements **bi-temporal edge tracking** with four timestamps per edge:

| Timestamp | Timeline | Purpose |
|-----------|----------|---------|
| `created_at` (t'_created) | Transactional (T') | When fact was ingested into the system |
| `expired_at` (t'_expired) | Transactional (T') | When fact was deprecated in the system |
| `valid_at` (t_valid) | Event (T) | When fact became true in reality |
| `invalid_at` (t_invalid) | Event (T) | When fact stopped being true in reality |

When a new fact contradicts an existing one (detected by LLM comparison in Stage 6), the old edge gets `invalid_at` set to the new fact's timestamp and `expired_at` set to the current system time. The old fact is **not deleted** -- it remains in the graph for temporal reasoning.

**Temporal extraction** uses `t_ref` (the reference timestamp of the current episode) to resolve both:
- Absolute timestamps: "Alan Turing was born on June 23, 1912"
- Relative timestamps: "I started my new job two weeks ago" (resolved relative to `t_ref`)

This enables point-in-time queries: "What was true about merchant X on date Y?" (event timeline) and "What did we know about merchant X when we processed message Z?" (transactional timeline).

#### Hyper-Edges for Multi-Entity Facts

Graphiti supports **hyper-edges** -- facts involving more than two entities. Rather than modeling these as a single edge between two nodes, Graphiti creates multiple edges from the same extraction, each connecting a different pair of entities while sharing the same fact description.

Episodic edges (`E_e`) connect episode nodes directly to extracted entity nodes, maintaining provenance. Episodes and semantic edges maintain **bidirectional indices**: semantic artifacts can be traced back to source episodes for citation, and episodes can quickly retrieve their relevant entities and facts.

#### Community Detection

Communities are detected using **label propagation** (not Leiden), enabling "straightforward dynamic extension" as new data arrives. For each new entity node, the system "assigns the new node to the community held by the plurality of its neighbors."

Community nodes contain summaries derived through an iterative map-reduce-style summarization of member nodes and community names containing key terms and relevant subjects.

#### Performance Data

| Metric | Value | Source |
|--------|-------|--------|
| Deep Memory Retrieval (DMR) accuracy | 94.8% (GPT-4o) / 98.2% (GPT-4o-mini) | Zep paper Table 1 |
| LongMemEval accuracy | 71.2% (GPT-4o) / 63.8% (GPT-4o-mini) | Zep paper |
| LongMemEval improvement vs. baseline | +11.0pp (GPT-4o) | Zep paper |
| Retrieval latency (P95) | 300ms (open source) / <200ms (Zep Cloud) | Zep documentation |
| Latency reduction vs. full-context | ~90% | Zep paper |
| Context tokens (avg) | 1.6k (vs. 115k full-context) | Zep paper |
| Episode processing cost | 1 credit per 350 bytes | Zep Cloud pricing |
| LLM calls per episode | 5-8 | Source code analysis |
| Retrieval LLM calls | **0** (zero) | Architecture design |
| Graph backends | Neo4j, FalkorDB, Kuzu, Neptune | Docs |
| LLM providers | OpenAI, Anthropic, Gemini, Groq, Ollama | Docs |

**Key insight**: Zero LLM calls at retrieval time. Retrieval uses only hybrid search (semantic embedding + BM25 full-text + graph traversal via BFS), making it extremely fast and cost-efficient.

#### Merchant Domain Relevance

- **Stage 1 model**: Graphiti's separated 6-task pipeline maps directly to our Stage 1 event projection, though we need to add provenance (DERIVED_FROM edges) at each step
- **Entity resolution**: The three-tier deduplication strategy aligns with our ADR-0011 three-tier entity resolution (exact/close/related match)
- **Temporal handling**: Bi-temporal tracking is more sophisticated than our current model; we should adopt `valid_at`/`invalid_at` semantics for preference evolution (e.g., "merchant X preferred email notifications from Jan-March, then switched to SMS")
- **Community detection**: Maps to merchant segment identification (merchants with similar behavioral patterns)
- **Gap**: No formal user preference modeling, no skill/behavioral pattern extraction, no ontology-guided extraction

---

### 2.2 Mem0

**Repository**: [github.com/mem0ai/mem0](https://github.com/mem0ai/mem0) (30K+ stars)
**Paper**: [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413) (ECAI 2025)
**License**: Apache 2.0 (open source), commercial Mem0 Platform
**Status**: Production, Series A ($24M, October 2025)
**Funding**: Y Combinator, Basis Set Ventures, Peak XV Partners, GitHub Fund

#### Architecture Overview

Mem0 implements a dual-store architecture:
- **Vector store**: Embeddings for semantic similarity search (configurable: Qdrant, Weaviate, Pinecone, etc.)
- **Graph store**: Entity-relationship triples in Neo4j/Memgraph/Neptune/Kuzu

The system processes conversations through three sequential modules: **Extraction** -> **Update** -> **Summary Generation**.

```
Conversation Input (m_{t-1}, m_t)
    |
    v
[Phase 1: Extraction]
    |-- Inputs: (message_pair, conversation_summary S, last_10_messages)
    |-- LLM call: phi(P) -> candidate facts {w1, w2, ..., wn}
    |-- Output: JSON { "facts": ["fact1", "fact2", ...] }
    |
    v
[Phase 2: Update]
    |-- For each fact: embed -> vector similarity search (top s=10)
    |-- LLM tool-call: compare new facts vs. existing memories
    |-- Operations: ADD | UPDATE | DELETE | NOOP
    |-- Parallel write: vector store + graph store (if enabled)
    |
    v
[Graph Memory Extension (Mem0^g)]
    |-- EXTRACT_ENTITIES_TOOL: identify entities with types
    |-- RELATIONS_TOOL: establish entity relationships as triplets
    |-- Cosine similarity search (threshold 0.7) against existing nodes
    |-- BM25Okapi reranking on relationship triples
    |-- DELETE_MEMORY_TOOL_GRAPH: flag obsolete relationships
    |-- Persist: Neo4j nodes + edges with embeddings
```

#### Extraction Prompts (from source code)

Mem0 uses several core prompts defined in [`mem0/configs/prompts.py`](https://github.com/mem0ai/mem0/blob/main/mem0/configs/prompts.py):

**FACT_RETRIEVAL_PROMPT** (extraction):
- Role: "Personal Information Organizer, specialized in accurately storing facts, user memories, and preferences"
- Primary role: "extract relevant pieces of information from conversations and organize them into distinct, manageable facts for easy retrieval and personalization"
- Extracts: personal preferences, important personal details, plans/intentions, activity preferences, professional details, miscellaneous facts
- Output format: `{"facts": ["fact1", "fact2", ...]}`

**USER_MEMORY_EXTRACTION_PROMPT** (user-specific variant):
- Critical instruction: "GENERATE FACTS SOLELY BASED ON THE USER'S MESSAGES. DO NOT INCLUDE INFORMATION FROM ASSISTANT OR SYSTEM MESSAGES."
- Same JSON output format
- Ensures the system captures what the *user* said, not what the assistant inferred

**DEFAULT_UPDATE_MEMORY_PROMPT** (conflict resolution):
- Role: "Smart memory manager which controls the memory of a system"
- Receives: new extracted facts + top-10 similar existing memories
- LLM decides per-fact: ADD (new), UPDATE (modify existing by ID), DELETE (contradicts existing by ID), NONE (no change)
- Output: `{"memory": [{"id": "...", "event": "ADD|UPDATE|DELETE|NONE", "old_memory": "...", "new_memory": "..."}]}`

**Graph memory entity extraction** (at retrieval time, in `graph_memory.py`):
- Fixed prompt: "You are a smart assistant who understands entities and their types in a given text. Extract all the entities from the text. DO NOT answer the question itself if the given text is a question."
- **Limitation**: This graph search prompt is hardcoded and cannot be customized ([GitHub issue #3299](https://github.com/mem0ai/mem0/issues/3299)), limiting domain-specific entity extraction

**Custom prompts** are supported via `custom_fact_extraction_prompt` and `custom_update_memory_prompt` configuration parameters, enabling domain-specific extraction.

#### Graph Memory Implementation (Mem0^g)

When graph memory is enabled, Mem0 adds an additional extraction layer:

1. **Entity Extraction**: LLM tool call (`EXTRACT_ENTITIES_TOOL`) identifies entities and assigns types (Person, Location, Event, etc.) with three key components: entity type classification, embedding vector capturing semantic meaning, and metadata including creation timestamp
2. **Relationship Generation**: LLM tool call (`RELATIONS_TOOL`) generates triplets `(v_s, r, v_d)` where `v_s` and `v_d` are source/destination entities. For each potential entity pair, evaluates whether meaningful relationships exist and classifies with labels (e.g., `lives_in`, `prefers`, `owns`, `happened_on`)
3. **Deduplication**: Each entity is embedded and searched against Neo4j with cosine similarity (default threshold 0.7)
4. **BM25 Reranking**: Retrieved relationships are reranked using BM25Okapi scoring on relationship triple text
5. **Conflict Detection**: LLM identifies outdated relationships via `DELETE_MEMORY_TOOL_GRAPH`
6. **Storage**: Directed labeled graph `G = (V, E, L)` with nodes carrying type classifications, embeddings, and timestamps

**Retrieval** uses dual approach:
- **Entity-centric**: Identifies key query entities, locates corresponding nodes via semantic similarity, explores incoming/outgoing relationships to construct subgraphs
- **Semantic triplet**: Encodes queries as dense embeddings, matches against textual encodings of relationship triplets, returns matches exceeding relevance thresholds

#### Conflict Resolution: The UPDATE Phase

This is Mem0's most important contribution. The update module implements a four-operation taxonomy:

| Operation | Condition | Action |
|-----------|-----------|--------|
| **ADD** | New information, no semantic equivalent exists | Create new memory entry |
| **UPDATE** | Information exists but content differs, complementary | Augment existing memory |
| **DELETE** | New information contradicts existing memory | Remove outdated memory (or mark as invalid in graph) |
| **NOOP** | Information already captured | Skip, no modification needed |

**Graph-specific conflict resolution** (Mem0g):
- When new relationships are integrated, the system checks for conflicts with existing relationships
- LLM-based resolver marks obsolete relationships as **invalid rather than deleting them**
- This preserves temporal reasoning capability
- Uses tools: `ADD_MEMORY_TOOL_GRAPH`, `UPDATE_MEMORY_TOOL_GRAPH`, `DELETE_MEMORY_TOOL_GRAPH`, `NOOP_TOOL`

#### Performance Data

| Metric | Mem0 | Mem0^g (Graph) | Full Context |
|--------|------|----------------|-------------|
| Single-hop J-score | 67.13% | 65.71% | -- |
| Multi-hop J-score | 51.15% | 47.19% | -- |
| Temporal J-score | 55.51% | **58.13%** | -- |
| Open-domain J-score | 72.93% | **75.71%** | -- |
| Search latency (P95) | 0.200s | 0.657s | 17.117s |
| Total response latency (P95) | 1.440s | 2.590s | 17.117s |
| Tokens per conversation | ~7k | ~14k | ~26k |
| Token savings vs. full-context | ~73% | ~46% | baseline |
| Latency reduction (P95) | **91%** | 85% | baseline |
| LLM calls per message | 2-4 | 4-6 | 1 |
| Approx. cost per turn (GPT-4o-mini) | ~$0.001-0.003 | ~$0.003-0.005 | ~$0.004 |

**Key insight**: The graph-enhanced variant (Mem0g) improves temporal and open-domain accuracy at the cost of higher latency and token usage. The base Mem0 wins on single-hop and multi-hop tasks due to simpler retrieval paths. For our merchant use case, where temporal preference evolution matters (e.g., "merchant used to prefer email, now prefers SMS"), Mem0g's approach is more relevant.

#### Merchant Domain Relevance

- **Conflict resolution taxonomy**: ADD/UPDATE/DELETE/NOOP maps directly to our preference lifecycle (create/reinforce/supersede/ignore). Extend with SUPERSEDE instead of DELETE to maintain history via `superseded_by` chains
- **Dual-store pattern**: Vector + graph mirrors our Postgres (episodic) + Neo4j (semantic) architecture
- **Custom extraction prompts**: Essential for merchant domain -- we need to extract payment preferences, shipping preferences, compliance-related facts
- **Gap**: No formal ontology, no provenance chains, no decay model, no behavioral pattern detection, simplistic entity resolution (embedding similarity only, 0.7 threshold)

---

### 2.3 Memoria

**Paper**: [Memoria: A Scalable Agentic Memory Framework for Personalized Conversational AI](https://arxiv.org/abs/2512.12686) (December 2025)
**License**: Open-source Python library
**Status**: Research prototype with production aspirations
**Implementation stack**: SQLite3, ChromaDB, OpenAI text-embedding-ada-002, GPT-4-mini

#### Architecture Overview

Memoria implements four integrated modules targeting personalized conversational AI:

1. **Structured Conversation Logging** -- Database storage with timestamps, session IDs, raw messages, and extracted KG triplets
2. **Dynamic User Persona via KG** -- Weighted knowledge graph capturing user traits, preferences, and behavioral patterns as structured entities/relationships
3. **Session-Level Memory** -- Real-time summarization maintaining coherent understanding within sessions
4. **Seamless Retrieval** -- Context-aware response generation combining structured history and weighted KG data

```
User Message + Assistant Response
    |
    +---> [Session Summarization Module]
    |         |-- Check: does session summary exist?
    |         |-- If yes: LLM call to update summary with new message pair
    |         |-- If no: LLM call to create initial summary
    |         |-- Store: SQL database (SQLite3)
    |
    +---> [Knowledge Graph Extraction Module]
              |-- LLM: extract (subject, predicate, object) triplets FROM USER MESSAGES ONLY
              |-- Embed triplets as dense vectors (text-embedding-ada-002)
              |-- Assign timestamp and source message metadata
              |-- Store: ChromaDB (vectors) + structured triplet store
              |-- Apply Exponential Weighted Average for retrieval weighting
```

#### Extraction: Incremental KG Construction

Memoria extracts knowledge exclusively from **user messages** (excluding assistant responses) to ensure the representation accurately reflects user intent. The extraction process:

1. **Triplet extraction**: LLM-powered identification of (subject, predicate, object) triples from incoming user queries using GPT-4-mini
2. **Dual storage**: Raw triplets stored in SQL; embeddings with metadata (timestamps, usernames, source messages) stored in ChromaDB
3. **Incremental graph building**: New triplets are connected to existing nodes to form an evolving semantic structure. If no graph exists for the user, one is instantiated fresh
4. **User-only extraction**: "Constructed solely from the user's input, excluding assistant responses, to ensure that the representation accurately reflects the user's intent"

The KG captures:
- Recurring topics mentioned by the user
- User preferences inferred from conversational patterns
- Named entities identified during interactions
- Relationships and connections between user-stated facts

#### Weighted Retrieval: Exponential Weighted Average (EWA)

This is Memoria's key technical contribution -- a mathematically grounded recency-weighting scheme:

**Raw weight formula**:
```
w_i = e^(-alpha * x_i)
```

Where:
- `alpha > 0` is the decay rate (default: `alpha = 0.02` in experiments)
- `x_i` represents minutes elapsed since triplet creation

**Min-max normalization** prevents extreme suppression of older entries:
```
x_norm = (x - x_min) / (x_max - x_min)
```
This ensures x values fall within [0, 1], "allowing the system to retain a soft memory of long-past interactions."

**Normalized weight**:
```
w_tilde_i = e^(-alpha * x_norm_i) / SUM_j(e^(-alpha * x_norm_j))
```
Ensuring weights sum to 1.

**Retrieval**: Top-K matching with `K = 20`, weighted by recency scores.

**Conflict resolution**: "If conflicting triplets are retrieved, this weighting system enables the model to resolve discrepancies in favor of the most current knowledge." The mechanism is implicit -- newer facts get higher weights -- rather than explicit contradiction detection.

**Comparison with our ADR-0008 Ebbinghaus model**: Memoria's EWA is structurally similar to our `score = e^(-t/S)` formula but uses minutes instead of hours and has a single global decay rate instead of per-item stability factors. Our model is more sophisticated with reinforcement-based stability adjustment (`S += S_boost` on access) and category-specific initial stability values.

#### Performance Data

| Metric | Memoria | A-MEM (OpenAI) | A-MEM (SentenceTrans.) | Full Context |
|--------|---------|----------------|------------------------|-------------|
| Single-session accuracy | **87.1%** | 84.2% | 78.5% | 85.7% |
| Knowledge-update accuracy | **80.8%** | 79.4% | 76.2% | 78.2% |
| Single-session tokens | **398** | 900+ | 900+ | 115,000 |
| Knowledge-update tokens | **400** | 928-933 | 928-933 | 115,000 |
| Single-session latency | 260s | 252-290s | 252-290s | 391s |
| Knowledge-update latency | **320s** | 328-364s | 328-364s | 522s |
| Token reduction vs. full-context | **99.65%** | 99.2% | 99.2% | baseline |
| Latency reduction vs. full-context | 33.5% | -- | -- | baseline |
| Knowledge-update latency reduction | **38.7%** | -- | -- | baseline |

**Key insights**:
- 87.1% accuracy with only 398 tokens per retrieval (vs. 115K for full context) = 99.65% token reduction
- Weighted retrieval specifically helps with knowledge updates (contradictions), outperforming A-MEM by 1.4-4.6 percentage points
- The latency numbers are end-to-end for full benchmark evaluation, not per-query

**Evaluation methodology caveat**: Memoria's benchmarks use a **different methodology** than LoCoMo/LongMemEval used by other systems. Direct cross-system accuracy comparisons are unreliable. Memoria's benchmarks are closer to our personalization use case (testing preference recall and update).

#### Merchant Domain Relevance

- **EWA scheme**: Directly applicable to our Ebbinghaus decay model (ADR-0008). Memoria's `alpha = 0.02` and min-max normalization provides a validated implementation reference
- **User-only extraction**: Extracting only from user messages is smart for preference/intent capture. For merchant conversations: extract what the merchant says, not what the support agent replies
- **Triplet format**: (subject, predicate, object) maps cleanly to our (Entity)-[EDGE]->(Entity) graph model
- **Gap**: No formal entity resolution beyond embedding similarity, no temporal invalidation, no multi-agent support, no provenance chains, no community detection

---

### 2.4 A-MEM

**Paper**: [A-MEM: Agentic Memory for LLM Agents](https://arxiv.org/abs/2502.12110) (NeurIPS 2025)
**Repository**: [github.com/agiresearch/A-mem](https://github.com/agiresearch/A-mem)
**License**: Open source
**Status**: Research, accepted at NeurIPS 2025

#### Architecture Overview

A-MEM implements a **Zettelkasten-inspired** note-based knowledge system. Unlike graph-based systems (Graphiti, Mem0), A-MEM organizes knowledge as interconnected notes following Niklas Luhmann's Zettelkasten methodology:

- **Notes**: Atomic knowledge units containing raw content, timestamp, LLM-generated keywords, LLM-generated tags, context descriptions, dense embeddings, and initially empty link sets
- **Links**: Bidirectional connections between related notes enabling knowledge traversal
- **Tags**: Categorical labels for organization and retrieval

Each note contains: `<c_i, t_i, K_i, G_i, X_i, e_i, L_i>` (content, timestamp, keywords, tags, contextual description, embedding, links).

#### Memory Creation Pipeline

```
Agent Interaction (query + response)
    |
    v
[Note Construction -- Prompt Ps1]
    |-- LLM: generate structured note attributes
    |-- Output: {content, timestamp, keywords, tags, contextual_description, embedding, links=[]}
    |
    v
[Link Generation -- Prompt Ps2]
    |-- Embed new note
    |-- Cosine similarity search: find top-k nearest neighbor notes
    |-- LLM: analyze connections with neighbors
    |-- Create bidirectional links where meaningful similarities exist
    |
    v
[Memory Evolution -- Prompt Ps3]
    |-- For each linked neighbor note m_j:
    |-- LLM: should m_j's context/keywords/tags be updated?
    |-- If yes: update m_j attributes based on new information
    |-- Bidirectional: new notes influence old, old notes contextualize new
```

#### Knowledge Evolution (Bidirectional)

This is A-MEM's distinguishing feature. When new information arrives, the system does not just append -- it **actively evolves** existing knowledge:

- New memories trigger scanning of related notes for potential updates
- The system identifies which existing notes should be modified based on semantic relevance
- Changes propagate through the link network, ensuring consistency
- Old notes can be refined, merged, or deprecated as understanding deepens

**Evolution prompt** (Ps3, conceptual): "Determine which existing notes should be updated given this new information and suggest specific modifications."

This prevents knowledge stagnation -- the system revises understanding over time rather than accumulating redundant memories.

#### Contradiction Detection and Resolution

A-MEM's approach is **implicit through evolution** rather than explicit detection:

1. **Detection**: When storing new information, query existing memories for conflicting claims via embedding similarity
2. **Analysis**: LLM reasoning determines reliability, considering recency and source authority
3. **Resolution**: Update or flag contradictions; resolve through weighted integration of both sources
4. **Metadata tracking**: Record confidence scores and source information per memory

**Key difference from other systems**: A-MEM does not explicitly detect or resolve contradictions. Instead, memory notes evolve their contextual descriptions and tags to incorporate new information. If a merchant says "I prefer email notifications" and later "I prefer SMS notifications," both notes exist with bidirectional links, but there is no explicit mechanism to mark one as superseding the other.

**Link generation prompt** (Ps2, conceptual): "Find semantically related notes and propose bidirectional links with relationship types (e.g., supports, contradicts, extends)."

#### Retrieval

Multi-strategy retrieval combines:
- Vector similarity (embedding-based semantic search)
- Link traversal (following bidirectional connections from initial results)
- Tag filtering (categorical metadata narrows search space)
- Recency weighting (prioritizing recently updated notes)

Empirical evaluation: multi-strategy retrieval achieves **92% precision@5** vs. 71% for embedding-only approaches.

#### Performance Data

| Metric | A-MEM | Comparison |
|--------|-------|-----------|
| Multi-turn task improvement | +15-25% over no-memory baseline | Significant |
| Contradiction resolution success | 85%+ | Without intervention |
| Link quality (precision) | 0.78 | Semantic relationships |
| Retrieval precision@5 | 92% (multi-strategy) | 71% (embedding-only) |
| Knowledge retention | Consistent across 50+ turns | No degradation |
| LoCoMo judge score | 0.580 | vs. MAGMA's 0.700 |
| LLM calls per memory write | 3 | Note + link + evolution |

#### Merchant Domain Relevance

- **Bidirectional evolution**: Maps to our `superseded_by` preference chain pattern (ADR-0012). When a preference is contradicted, the old preference links to the new one rather than being deleted
- **Atomic notes**: The atomicity principle aligns with our fine-grained node types (each Preference, Skill, BehavioralPattern is an atomic knowledge unit)
- **Link typing**: "supports, contradicts, extends" relationship types could extend our edge vocabulary
- **Gap**: No graph structure (note-based, not graph-based), no temporal modeling, no entity resolution, no user-specific modeling, no multi-agent support

---

### 2.5 MAGMA

**Paper**: [MAGMA: A Multi-Graph based Agentic Memory Architecture for AI Agents](https://arxiv.org/abs/2601.03236) (January 2026)
**Status**: Research with open-source implementation
**Direct alignment**: Our ADR-0009 multi-view architecture was influenced by MAGMA

#### Architecture Overview

MAGMA represents memory as a directed multigraph `G_t = (N_t, E_t)` with **four orthogonal edge spaces** over a shared node set:

| Graph | Edge Type | Construction | Our ADR-0009 Analog |
|-------|-----------|-------------|---------------------|
| **Temporal** (`E_temp`) | Strictly ordered pairs `(n_i, n_j)` where `tau_i < tau_j` | Immutable chain based on timestamps | FOLLOWS |
| **Causal** (`E_causal`) | Directed edges representing logical entailment | Asynchronous consolidation: `S(n_j|n_i,q) > delta` | CAUSED_BY |
| **Semantic** (`E_sem`) | Undirected edges for conceptual similarity | `cos(v_i, v_j) > theta_sim` | SIMILAR_TO |
| **Entity** (`E_ent`) | Edges connecting events to abstract entity nodes | Structured extraction from event metadata | REFERENCES |

Each node stores: content (`c_i`), timestamp (`tau_i`), dense embedding (`v_i`), and attributes (`A_i`).

#### Extraction: Three Prompt Types

**1. Event Extraction Prompt (JSON-Structured)**:
- System instruction: "return ONLY a valid JSON object matching the specific schema below"
- Extracts: entities (proper nouns), topics, relationships (interactions), semantic facts (atomic facts), temporal strings, summaries, and speaker attribution
- Enforces explicit schema with strict validation
- "Ensures robustness against hallucination and parsing errors" via strict schema enforcement

**2. Query-Adaptive QA Prompt**:
- Dynamically injects instructions based on query classification (Multi-hop, Temporal, Open-domain, Factual)
- Uses context fusion with category-specific constraints

**3. Evaluation Prompt (LLM-as-Judge)**:
- Scores semantic fidelity on continuous scale [0.0, 1.0]
- Handles temporal flexibility, semantic equivalence, and adversarial cases

#### Dual-Stream Processing

**Fast Path** (synchronous, < 100ms):
- Event segmentation
- Vector indexing (embedding generation)
- Temporal chain construction (FOLLOWS-like edges)

**Slow Path** (asynchronous consolidation):
- LLM-powered JSON-structured event extraction
- Causal edge inference via local 2-hop neighborhood analysis
- Entity graph link establishment
- Workers dequeue events and "densify the graph structure"

This dual-stream model maps directly to our Stage 1 (fast path) and Stage 2/3 (slow path) consolidation architecture.

#### Policy-Guided Traversal (Retrieval)

Four-stage retrieval process:

**Stage 1 -- Query Analysis**: Decomposes query into intent classification (Why/When/Entity), temporal window, and dual representations (dense embedding + sparse keywords)

**Stage 2 -- Anchor Identification**: Uses Reciprocal Rank Fusion (RRF) across vector search, keyword matching, and temporal filtering:
```
S_anchor = TopK(SUM_m 1/(k + r_m(n)))  where m in {vec, key, time}, k=60
```

**Stage 3 -- Adaptive Traversal**: Heuristic beam search with dynamic transition scoring:
```
S(n_j | n_i, q) = exp(lambda_1 * phi(type(e_ij), T_q) + lambda_2 * sim(n_j, q))
```
Weight vector `w_Tq` prioritizes edge types based on intent -- high weights for CAUSAL edges on "Why" queries, high weights for TEMPORAL edges on "When" queries.

**Stage 4 -- Narrative Synthesis**: Topological sorting preserves relational dependencies; context scaffolding adds timestamps and reference IDs; salience-based token budgeting truncates low-probability nodes. Max traversal depth: 5 hops. Max nodes: 200.

#### Performance Data

| Metric | MAGMA | A-MEM | Nemori | MemoryOS | Full Context |
|--------|-------|-------|--------|----------|-------------|
| LoCoMo judge score | **0.700** | 0.580 | 0.590 | 0.553 | 0.481 |
| LongMemEval accuracy | **61.2%** | -- | 56.2% | -- | 55.0% |
| Build time (hours) | 0.39 | 1.01 | 0.29 | 0.91 | -- |
| Tokens/query | 3.37k | 2.62k | 3.46k | 4.76k | 101k |
| Query latency | **1.47s** | 2.26s | 2.59s | 32.68s | -- |
| Token reduction vs. full-context | **95%+** | 97%+ | 96%+ | 95%+ | baseline |

**Ablation study results** (LoCoMo judge score, removing one component at a time):

| Removed Component | Judge Score | Drop | Relative Impact |
|--------------------|------------|------|-----------------|
| Full MAGMA | **0.700** | -- | baseline |
| w/o Adaptive traversal policy | 0.637 | -0.063 | **Largest** -- intent-aware routing is critical |
| w/o Causal links | 0.644 | -0.056 | Second -- "why" reasoning |
| w/o Temporal backbone | 0.647 | -0.053 | Third -- chronological grounding |
| w/o Entity links | 0.666 | -0.034 | Smallest -- entity tracking |

**Key insight**: The ablation study confirms that **adaptive traversal policy** (intent-aware weighting) is the single most important component, providing the largest accuracy gain. This validates our ADR-0009 intent weight matrix design.

#### Merchant Domain Relevance

- **Multi-graph architecture**: Our five semantic views directly parallel MAGMA's four graphs. Ablation validates multi-graph approach with 18.6-45.5% improvements over monolithic stores
- **Intent-aware traversal**: Validates our intent weight matrix (ADR-0009). For merchants: "why was my payment declined?" traverses causal graph; "when did I change my shipping settings?" traverses temporal graph
- **Dual-stream processing**: Maps exactly to our Stage 1 + Stage 2/3
- **Causal inference**: 2-hop neighborhood analysis provides a concrete implementation pattern for our Stage 3 cross-session pattern detection
- **Gap**: No user modeling, no preference extraction, no entity resolution (assumes clean input), no conflict resolution, research-only

---

### 2.6 Cognee

**Repository**: [github.com/topoteretes/cognee](https://github.com/topoteretes/cognee) (8K+ stars)
**Paper**: [Optimizing the Interface Between Knowledge Graphs and LLMs for Complex Reasoning](https://arxiv.org/abs/2505.24478) (2025)
**License**: Apache 2.0 (open source)
**Status**: Production-ready, commercially offered

#### Architecture Overview

Cognee implements a four-stage modular pipeline:

1. **Add (Ingest)**: `cognee.add()` ingests data from 30+ sources (text documents, past conversations, files, images, audio transcriptions)
2. **Cognify (Graph + Embeddings)**: Extracts entities and relationships, builds triplets, chunks text, generates embeddings with optional temporal awareness (`temporal_cognify=True`)
3. **Memify (Optimize Memory)**: Post-processing pipeline that prunes stale nodes, strengthens frequent connections, applies ML-based enrichment
4. **Search (Contextual Retrieval)**: Combines vector search with graph traversal for context-rich answers

```
Raw Data (30+ source types)
    |
    v
[Add / Ingest]
    |-- cognee.add(): ingest from files, conversations, images, audio
    |-- Pythonic data pipelines with modular task composition
    |
    v
[Cognify / Graph + Embeddings]
    |-- Triplet extraction: (subject, relation, object) via LLM
    |-- Text chunking + embedding generation
    |-- Optional temporal_cognify=True for date tagging on edges
    |-- Dual representation: graph nodes/edges + vector embeddings
    |
    v
[Memify / Optimize Memory]
    |-- Stage 1: Read existing data into structured DataPoints
    |-- Stage 2: Apply memory logic, ML models, temporal reasoning
    |     |-- Strengthen frequently-accessed connections
    |     |-- Infer new links between related entities
    |     |-- Prune outdated/stale nodes
    |-- Stage 3: Write enhancements back to graph, vector store, metastore
    |
    v
[Search / Contextual Retrieval]
    |-- Mix vector search with graph traversal
    |-- Return context-rich answers with relationship context
```

#### Cognify: Extraction Stage

The Cognify stage transforms raw data into a hybrid knowledge representation:

- **Triplet extraction**: Converts data into (subject, relation, object) triplets using LLM-driven extraction with configurable providers (OpenAI, Ollama, etc.)
- **Dual representation**: Each document/fact is represented both as graph nodes/edges AND as vectors in a similarity index
- **Temporal awareness**: With `temporal_cognify=True`, the engine tags edges with event dates, enabling temporal queries
- **Modular task composition**: Developers can build custom "knowledge blocks" and compose extraction pipelines

#### Memify: Post-Processing Pipeline

The Memify Pipeline is Cognee's distinctive contribution -- a "memory enhancement layer" that operates after initial graph construction:

**Three stages**:
1. **Read**: Loads existing data into structured DataPoints from graph, vector store, and metastore
2. **Process**: Applies memory logic, ML models, and temporal reasoning to:
   - Strengthen connections that appear frequently
   - Infer new links between related entities
   - Prune outdated/stale nodes
   - Apply self-improvement heuristics
3. **Write**: Persists enhancements back to graph, vector store, and metastore

This operates incrementally without disrupting core workflows, running as a periodic background process. The Memify pattern aligns directly with our Stage 3 re-consolidation.

#### Performance Data

| Metric | Cognee 2025.1 | Mem0 2025.2 | LightRAG 2025.0 | Graphiti 2025.1 |
|--------|--------------|-------------|-----------------|-----------------|
| HotPotQA correctness (LLM-as-judge) | **0.93** | Lower | Lower | Lower |
| Multi-hop reasoning | Best | Good | Good | Good |

**Caveats**: These benchmarks are from Cognee's own evaluation (potential bias). Test uses only 24 HotPotQA questions with 45 repeated runs. Authors acknowledge: "LLM as a judge metrics are not reliable" and "F1 scores measure character matching and are too granular for semantic memory evaluation."

#### Merchant Domain Relevance

- **Memify pattern**: Periodic post-processing enrichment maps to our Stage 3 re-consolidation. The three-stage (read/process/write) pattern provides a clean implementation model for preference merging, behavioral pattern detection, and workflow extraction
- **30+ data source support**: Demonstrates value of modular ingestion -- merchants interact through multiple channels (web, mobile, API, phone)
- **Temporal cognify**: Temporal edge tagging is simpler than Graphiti's bi-temporal model but may suffice for merchant preference tracking
- **Gap**: Limited documentation on extraction specifics, no formal entity resolution, no user preference modeling, benchmarks are self-published

---

## 3. Cross-System Comparison Matrix

### 3.1 Architecture Comparison

| Feature | Zep/Graphiti | Mem0 | Memoria | A-MEM | MAGMA | Cognee |
|---------|-------------|------|---------|-------|-------|--------|
| **Knowledge representation** | Temporal KG (3 tiers) | Vector + Optional Graph | Weighted KG + Summaries | Zettelkasten notes | Multi-graph (4 views) | Hybrid KG + Vector |
| **Graph backend** | Neo4j/FalkorDB/Kuzu/Neptune | Neo4j/Memgraph/Neptune/Kuzu | ChromaDB (vector only) | In-memory | In-memory | Neo4j/Memgraph |
| **Primary extraction** | 6 separate LLM prompts | LLM function calling | LLM triplet extraction | 3 LLM prompts (Ps1-3) | LLM JSON schema | LLM triplet extraction |
| **Entity resolution** | 3-tier (exact/MinHash-LSH/LLM) | Embedding similarity (0.7) | Embedding similarity | Embedding + link traversal | None (assumes clean) | Basic |
| **Temporal model** | Bi-temporal (4 timestamps) | Session-based | Exponential decay (EWA) | Timestamp + recency | Strict temporal chain | Edge timestamp tags |
| **Conflict resolution** | Edge invalidation (temporal) | ADD/UPDATE/DELETE/NOOP | Decay-weighted (implicit) | Bidirectional evolution | Deferred to retrieval | Memify prune/strengthen |
| **User modeling** | No | Preferences (implicit) | User persona KG | No | No | No |
| **Provenance** | Episode source IDs on edges | Session IDs on memories | Source message metadata | Note source + timestamp | Node attributes | Chunk references |
| **Multi-agent** | Multi-tenancy (group_id) | user_id/agent_id scoping | No | No | No | No |
| **Community detection** | Label propagation + LLM summaries | No | No | No | No | No |
| **Open source** | Apache 2.0 | Apache 2.0 | Yes | Yes | Yes | Apache 2.0 |

### 3.2 Extraction Pipeline Comparison

| Pipeline Stage | Zep/Graphiti | Mem0 | Memoria | A-MEM | MAGMA | Cognee |
|---------------|-------------|------|---------|-------|-------|--------|
| **Entity extraction** | LLM + reflexion loop | LLM function calling (EXTRACT_ENTITIES_TOOL) | LLM triplet extraction (user msgs only) | LLM note construction (Ps1) | LLM JSON schema | LLM triplet extraction |
| **Relationship extraction** | Separate LLM prompt (extract_edges.py) | LLM RELATIONS_TOOL | Part of triplet extraction | Implicit via linking (Ps2) | Part of JSON extraction | Part of triplet extraction |
| **Entity deduplication** | MinHash/LSH/Jaccard (0.9) + LLM | Embedding cosine (0.7) | Embedding similarity | Embedding + link search | None | Basic |
| **Edge deduplication** | Embedding + RRF + LLM | LLM CRUD classification | Decay weighting | Note evolution (Ps3) | None | Memify pruning |
| **Temporal extraction** | Dedicated LLM task with t_ref | Timestamp metadata only | Timestamp + decay rate | Timestamp per note | Temporal parser (abs + relative) | Edge date tags |
| **Contradiction detection** | LLM comparison (Stage 6) | LLM update module | Implicit (newer = higher weight) | LLM evolution prompt | None | Memify process |
| **Confidence scoring** | None (binary valid/invalid) | None explicit | Implicit (EWA weights) | Note-level confidence | None | None |
| **Provenance tracking** | Episode UUIDs on edges | Session IDs on memories | Source message in metadata | Timestamp + source | Node attributes | Chunk references |
| **Reflexion/verification** | Yes (iterative completeness check) | No | No | No | No (retry on invalid JSON) | No |
| **Schema enforcement** | Pydantic models + entity ID validation | JSON via function calling | Triplet format | Free-form notes | Strict JSON schema | Triplet format |

### 3.3 Conflict Resolution Comparison

| Dimension | Zep/Graphiti | Mem0 | Memoria | A-MEM | MAGMA | Cognee |
|-----------|-------------|------|---------|-------|-------|--------|
| **Mechanism** | Temporal edge invalidation | LLM-decided CRUD | Exponential weighted average | Bidirectional note evolution | Query-time intent weighting | Memify prune/strengthen |
| **When resolved** | Write time | Write time | Retrieval time (via weights) | Write time (evolution) | Query time | Periodic batch (memify) |
| **Data preserved?** | Old edges preserved with t_invalid | UPDATE/DELETE modify/remove | All triplets preserved, weighted | Notes evolve but persist | All data preserved | Stale nodes pruned |
| **Handles contradictions?** | Yes (temporal invalidation) | Yes (LLM decides) | Yes (newer = higher weight) | Implicit (evolution) | Deferred to retrieval | Implicit (prune) |
| **Deterministic?** | Mostly (temporal rules) | No (LLM dependent) | Yes (mathematical formula) | No (LLM dependent) | N/A (query-time) | Partially |
| **History preserved?** | Full (invalidated edges remain) | Partial (UPDATE modifies) | Full (old triplets decay) | Full (notes evolve) | Full | Partial (pruned nodes lost) |

### 3.4 Performance Comparison

| Metric | Zep/Graphiti | Mem0 | Mem0^g | Memoria | A-MEM | MAGMA |
|--------|-------------|------|-------|---------|-------|-------|
| **Primary benchmark** | LoCoMo DMR | LoCoMo (multiple) | LoCoMo (multiple) | Custom (single-session) | LoCoMo | LoCoMo + LongMemEval |
| **Best accuracy** | 98.2% DMR | 67.13% single-hop J | 75.71% open-domain J | 87.1% single-session | 0.580 judge | **0.700 judge** |
| **Retrieval latency (P95)** | **300ms** | **200ms** | 657ms | N/A | N/A | 1.47s (avg) |
| **Response latency (P95)** | N/A | 1.44s | 2.59s | N/A | 2.26s | 1.47s |
| **Tokens per query** | 1.6k | ~7k | ~14k | **~400** | ~2.6k | ~3.4k |
| **Token reduction vs. full** | 98.6% | 73% | 46% | **99.65%** | 97% | 95% |
| **LLM calls per write** | 5-8 | 2-4 | 4-6 | 3 | 1-2 (fast) + N (slow) | 1-2 |
| **LLM calls per retrieval** | **0** | **0** | **0** | **0** | **0** | **0** |
| **Build time per session** | Real-time | Real-time | Real-time | Real-time | 1.01h (batch) | 0.39h (batch) |

### 3.5 Cost Comparison

| System | LLM Calls/Episode | Estimated Cost/1K Episodes (GPT-4o-mini) | Primary Cost Driver | Zero LLM Retrieval |
|--------|-------------------|----------------------------------------|--------------------|--------------------|
| **Zep/Graphiti** | 5-8 | ~$5-8 | Entity/edge extraction + reflexion | Yes |
| **Mem0** | 2-4 | ~$2-5 | Extraction + update classification | Yes |
| **Mem0^g** | 4-6 | ~$4-8 | Graph entity/relationship extraction | Yes |
| **Memoria** | 1-2 | ~$1-3 | Triplet extraction (minimal) | Yes |
| **A-MEM** | 3 | ~$3-7 | Note construction + evolution | Yes |
| **MAGMA** | 0 (fast) + 1-3 (slow) | ~$2-4 (amortized) | Slow-path consolidation | Yes |
| **Cognee** | 1-2 + periodic memify | ~$1-4 + memify overhead | Cognify + periodic memify | Yes |

*Calculation basis*: GPT-4o-mini at $0.15/1M input, $0.60/1M output. Using GPT-4o (~$2.50/1M input) increases costs by ~15-17x.

### 3.6 ADR-0012 Node Type Coverage

| ADR-0012 Node Type | Mem0 | Graphiti | Memoria | A-MEM | MAGMA | Cognee | Production Validation |
|-------------------|------|---------|---------|-------|-------|--------|----------------------|
| **Event** | Partial | Yes (episodes) | Partial | Partial | Yes | Partial | **Moderate** (2/6 first-class) |
| **Entity** | Yes (typed) | Yes (taxonomy) | Partial (in triplets) | No | Yes (entity graph) | Yes | **Strong** (4/6) |
| **Summary** | Yes (conversation) | Yes (entity + community) | Yes (session-level) | Yes (context descriptions) | Yes (per-event) | Yes | **Strong** (6/6) |
| **Preference** | Yes (implicit) | Partial (encoded in facts) | Yes (weighted triplets) | Partial (note content) | No | No | **Moderate** (2-3/6) |
| **UserProfile** | Partial (user_id scoping) | No | No | No | No | No | **None** |
| **Skill** | No | No | No | No | No | No | **None** |
| **Workflow** | No | No | No | No | No | No | **None** |
| **BehavioralPattern** | No | No | Partial (patterns mentioned) | Partial (emergent) | No | No | **None** |

**Critical insight**: Only **Entity**, **Summary**, and **Preference** extraction have production validation. **UserProfile**, **Skill**, **Workflow**, and **BehavioralPattern** are novel to our ontology with no production precedent. These require novel pipeline design with thorough evaluation methodology.

---

## 4. Lessons for Our System (Mapped to Stage 1/2/3)

### 4.1 Stage 1: Event Projection (< 500ms budget)

**Adopt from Graphiti**: Separated extraction tasks with parallel execution where possible.
**Adopt from MAGMA**: Fast-path synchronous processing for structural edges.

Recommended Stage 1 pipeline:

1. **Entity extraction** (single LLM call): Extract entities from event payload using a Graphiti-style prompt adapted for merchant domain (payments, disputes, shipping, compliance vocabulary)
2. **Entity resolution** (deterministic only): Exact-match at Stage 1 (normalized name + entity_type). This stays within 500ms budget. No LLM dedup at this stage
3. **Edge creation** (code, no LLM): Create REFERENCES edges from Event to resolved Entities with roles (agent, instrument, object, result)
4. **Explicit preference handling** (code, no LLM): If `event_type = user.preference.stated`, create Preference node with `source="explicit"`, HAS_PREFERENCE edge, ABOUT edge, and DERIVED_FROM edge
5. **Temporal chaining** (code, no LLM): Create FOLLOWS edges based on `occurred_at` ordering within session

**Critical: DERIVED_FROM edges at every step**. Every Entity, Preference, or relationship created in Stage 1 gets a DERIVED_FROM edge pointing to the source Event. This is our differentiator.

**Merchant-specific adaptations**:
- Entity types: merchant, payment_method, product, dispute, invoice, shipping_carrier, compliance_rule
- Extract tool usage from `tool.execute` events (which payment tools, which reporting tools)

### 4.2 Stage 2: Enrichment (batch, seconds per event)

**Adopt from Mem0**: LLM-based extraction with function calling for structured output, CRUD conflict resolution.
**Adopt from Memoria**: User-only extraction (extract from merchant messages, not agent responses).
**Adopt from MAGMA**: Strict JSON schema enforcement to prevent hallucination.
**Adopt from Graphiti**: Reflexion loops for extraction completeness verification.

Recommended Stage 2 pipeline:

1. **Implicit preference extraction** (LLM, session batch): Process accumulated merchant messages from a session:
   - Extract tool preferences (e.g., consistently using mobile app over desktop)
   - Extract communication preferences (e.g., asking for detailed explanations vs. brief answers)
   - Extract domain interests (e.g., frequently asking about international shipping)
   - Output as Preference nodes with `source="implicit_unintentional"`, `confidence=0.5`

2. **Skill assessment** (LLM, session batch): Analyze merchant messages for competency signals:
   - Fluent API discussion = high technical skill
   - Asking basic questions about CSV exports = lower data skill
   - Output as HAS_SKILL edges with `source="observed"`, proficiency score

3. **Entity resolution -- close matches** (embedding + MinHash): Run embedding similarity against existing entities:
   - Threshold > 0.9: Create SAME_AS edge with confidence
   - Use Graphiti's MinHash/LSH approach for candidate generation before embedding comparison
   - Merchant-specific: canonicalize product names, payment methods, business names

4. **Conflict resolution** (LLM): Adopt Mem0's taxonomy extended with SUPERSEDE:
   - **ADD**: New preference, no existing equivalent
   - **UPDATE**: Reinforce existing (observation_count++, confidence++, stability += S_boost)
   - **SUPERSEDE**: Contradicts existing. Create new Preference, set `superseded_by` on old one
   - **NOOP**: Already captured, skip

5. **Keyword/embedding generation**: Generate keywords and embeddings for Event nodes (can use smaller/cheaper models)

### 4.3 Stage 3: Re-Consolidation (periodic batch)

**Adopt from MAGMA**: Asynchronous causal edge inference via 2-hop neighborhood analysis.
**Adopt from Cognee**: Memify-style periodic enrichment (read/process/write pattern).
**Adopt from Memoria**: EWA decay weighting for preference ranking and pruning.
**Adopt from Graphiti**: Community detection for merchant segment identification.

Recommended Stage 3 pipeline:

1. **Cross-session preference merging**: Find duplicate preferences across sessions for same merchant. Merge using Memoria's EWA weighting enhanced with our Ebbinghaus per-item stability factors
2. **Behavioral pattern detection**: Analyze Event sequences across merchant sessions for:
   - Delegation (routes complex issues to specific agents)
   - Escalation (switches agents when payment issues arise)
   - Routine (always checks analytics before pricing changes)
   - Avoidance (never uses certain tools)
3. **Workflow extraction**: Identify repeated successful event sequences. Create Workflow nodes at "case" level (e.g., "dispute resolution workflow")
4. **Causal link inference**: Use MAGMA's 2-hop neighborhood analysis to discover CAUSED_BY relationships not captured in Stage 1
5. **Interest hierarchy propagation**: Propagate INTERESTED_IN edges to parent/child concepts with decayed weights (e.g., "interested in international shipping" implies interest in "shipping" parent concept)
6. **Preference conflict resolution**: Apply Ebbinghaus decay + source priority (explicit > implicit_intentional > implicit_unintentional > inferred) + observation count as tiebreaker

### 4.4 Retrieval (Zero LLM Calls)

**Adopt from Graphiti**: Zero LLM calls at retrieval time. Use hybrid search (semantic + BM25 + graph traversal).
**Adopt from MAGMA**: Intent-aware traversal with edge-type weights.

The context API should:
1. Classify query intent (who_is/how_does/personalize/why/when/what) using lightweight classifier
2. Select traversal weights from intent weight matrix (ADR-0009 + ADR-0012 extensions)
3. Use RRF across vector search, keyword search, and graph traversal to identify anchor nodes
4. Run bounded beam search with intent-weighted edge scoring (max depth 5, max nodes 200)
5. Return results with provenance annotations (DERIVED_FROM chains back to source events)

---

## 5. Gaps and Open Questions

### 5.1 No System Solves Merchant-Domain Extraction

All surveyed systems are domain-agnostic. None is optimized for merchant support (payments, disputes, invoicing, shipping, compliance). We need:
- Domain-specific entity types (merchant, payment_method, dispute, invoice, shipping_carrier)
- Merchant vocabulary in few-shot examples
- Domain-specific behavioral patterns (e.g., "dispute handling routine", "price-check-before-change" workflow)
- Compliance-aware extraction (identifying when merchants discuss regulatory requirements)

### 5.2 Confidence Calibration is Unsolved

No production system provides well-calibrated confidence scores:
- Graphiti: Binary valid/invalid (no confidence)
- Mem0: No explicit confidence scoring
- Memoria: Implicit weighting via decay (not calibrated confidence)
- A-MEM: Note-level confidence mentioned but not detailed
- MAGMA: No confidence scoring
- Cognee: No confidence scoring

Our ADR-0012 requires `confidence` on every Preference, Skill, and BehavioralPattern node. Recommended approach:
- Source-type defaults: explicit=0.9, implicit_intentional=0.7, implicit_unintentional=0.5, inferred=0.3 (per ADR-0012)
- Observation count reinforcement: confidence increases with repeated observations
- Self-consistency sampling for high-stakes extractions (extract N times, measure agreement)

### 5.3 Memory Hallucination is a Real Risk

Recent research ([HaluMem, 2025](https://arxiv.org/abs/2511.03506)) reveals that "existing memory systems tend to generate and accumulate hallucinations during extraction and updating stages, which subsequently propagate errors to the question answering stage." Systems show **recall < 60%** and **accuracy < 62%** in extended contexts.

Additional failure modes ([MongoDB Memory Engineering, 2025](https://www.mongodb.com/company/blog/technical/why-multi-agent-systems-need-memory-engineering)):
- **Context poisoning**: Hallucinations contaminate future reasoning
- **Context distraction**: Too much information overwhelms decision-making
- **Work duplication**: Agents repeat tasks without knowing others have completed them

Mitigation strategies:
- Graphiti's reflexion loop (re-prompt to check for missed entities)
- MAGMA's strict JSON schema enforcement
- Our Pydantic v2 strict mode validation at ingestion
- Confidence thresholds for graph insertion (reject extractions below minimum confidence)
- Source message metadata preservation for audit

### 5.4 Entity Resolution at Merchant Scale

For SMB merchants, entity resolution challenges include:
- Product name variations ("PayPal Here" vs "PayPal Zettle" vs "card reader")
- Business name variations (legal name vs. DBA vs. storefront name)
- Tool name evolution (product rebranding across versions)
- Multi-language entity references
- Payment method aliases ("Visa ending in 4242" vs "my business card")

Graphiti's 3-tier approach (exact/MinHash-LSH/LLM) is the best starting point. Add merchant-domain canonicalization rules for common variations.

### 5.5 Evaluation Methodology

No standard benchmark exists for merchant-domain conversational extraction. We need:
- A labeled dataset of merchant conversations with ground-truth preferences, skills, and patterns
- Competency questions: "Does the system correctly extract that Merchant X prefers email notifications for disputes?"
- Precision/recall metrics per extraction type (entity, preference, skill, pattern)
- End-to-end personalization quality metrics (does extracted knowledge improve agent responses?)

### 5.6 Multi-Language Extraction

Merchants converse in multiple languages. None of the surveyed systems explicitly addresses multilingual extraction. LLM-based extraction is inherently multilingual (frontier models handle 90+ languages), but:
- Entity resolution across languages is harder (same entity in English and Spanish)
- Preference expressions vary culturally
- Some extraction prompts may need language-specific adaptations

### 5.7 Novel Node Types Have No Production Precedent

**UserProfile**, **Skill**, **Workflow**, and **BehavioralPattern** extraction from conversations has no production reference architecture. These require:
- Novel prompt engineering and evaluation
- Conservative confidence thresholds until calibrated
- Human-in-the-loop review during initial deployment
- Gradual rollout with monitoring

---

## 6. References

### Production Systems -- Papers

- Rasmussen (2025). "Zep: A Temporal Knowledge Graph Architecture for Agent Memory." https://arxiv.org/abs/2501.13956
- Chhikara et al. (2025). "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory." ECAI. https://arxiv.org/abs/2504.19413
- Khant et al. (2025). "Memoria: A Scalable Agentic Memory Framework for Personalized Conversational AI." https://arxiv.org/abs/2512.12686
- Xu et al. (2025). "A-MEM: Agentic Memory for LLM Agents." NeurIPS 2025. https://arxiv.org/abs/2502.12110
- Jiang et al. (2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture for AI Agents." https://arxiv.org/abs/2601.03236

### Source Code and Documentation

- Graphiti GitHub: https://github.com/getzep/graphiti
- Graphiti extract_nodes.py: https://github.com/getzep/graphiti/blob/main/graphiti_core/prompts/extract_nodes.py
- Graphiti extract_edges.py: https://github.com/getzep/graphiti/blob/main/graphiti_core/prompts/extract_edges.py
- Graphiti dedupe_edges.py: https://github.com/getzep/graphiti/blob/main/graphiti_core/prompts/dedupe_edges.py
- Graphiti DeepWiki architecture: https://deepwiki.com/getzep/graphiti
- Graphiti blog -- LLM Data Extraction at Scale: https://blog.getzep.com/llm-rag-knowledge-graphs-faster-and-more-dynamic/
- Graphiti blog -- 20K Stars + MCP Server 1.0: https://blog.getzep.com/graphiti-hits-20k-stars-mcp-server-1-0/
- Mem0 GitHub: https://github.com/mem0ai/mem0
- Mem0 prompts source: https://github.com/mem0ai/mem0/blob/main/mem0/configs/prompts.py
- Mem0 Graph Memory docs: https://docs.mem0.ai/open-source/features/graph-memory
- Mem0 Custom Prompts docs: https://docs.mem0.ai/open-source/features/custom-update-memory-prompt
- Mem0 DeepWiki architecture: https://deepwiki.com/mem0ai/mem0
- Mem0 Architecture (Medium): https://medium.com/@zeng.m.c22381/mem0-overall-architecture-and-principles-8edab6bc6dc4
- A-MEM GitHub: https://github.com/agiresearch/A-mem
- Cognee GitHub: https://github.com/topoteretes/cognee
- Cognee Memify Pipeline: https://www.cognee.ai/blog/cognee-news/product-update-memify
- Cognee Memify docs: https://docs.cognee.ai/core-concepts/main-operations/memify
- Zep documentation: https://help.getzep.com/graphiti/getting-started/overview
- Zep pricing: https://www.getzep.com/pricing/
- Neo4j blog -- Graphiti Knowledge Graph Memory: https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/

### Benchmarks, Evaluations, and Comparisons

- Cognee AI Memory Tools Evaluation (Cognee, Mem0, Zep/Graphiti): https://www.cognee.ai/blog/deep-dives/ai-memory-tools-evaluation
- Cognee AI Memory Benchmarking (Cognee, LightRAG, Graphiti, Mem0): https://www.cognee.ai/blog/deep-dives/ai-memory-evals-0825
- Cognee Research and Evaluation Results: https://www.cognee.ai/research-and-evaluation-results
- Mem0 Research: https://mem0.ai/research
- Zep benchmark dispute (LoCoMo evaluation): https://github.com/getzep/zep-papers/issues/5
- LoCoMo benchmark: https://snap-research.github.io/locomo/
- Mem0 & Mem0-Graph breakdown: https://memo.d.foundation/breakdown/mem0
- From RAG to Graphs (Cognee + Memgraph): https://memgraph.com/blog/from-rag-to-graphs-cognee-ai-memory

### Memory System Surveys

- Hu et al. (2025). "Memory in the Age of AI Agents: A Survey." https://arxiv.org/abs/2512.13564
- Graph-based Agent Memory: Taxonomy, Techniques, and Applications (2026). https://arxiv.org/abs/2602.05665
- Huang et al. (2026). "Rethinking Memory Mechanisms of Foundation Agents." https://arxiv.org/abs/2602.06052
- Survey of AI Agent Memory Frameworks (Graphlit): https://www.graphlit.com/blog/survey-of-ai-agent-memory-frameworks

### Failure Modes and Quality

- HaluMem: Evaluating Hallucinations in Memory Systems of Agents (2025). https://arxiv.org/abs/2511.03506
- Why Multi-Agent Systems Need Memory Engineering (MongoDB, 2025). https://www.mongodb.com/company/blog/technical/why-multi-agent-systems-need-memory-engineering
- Memory for AI Agents: A New Paradigm of Context Engineering (The New Stack). https://thenewstack.io/memory-for-ai-agents-a-new-paradigm-of-context-engineering/
- Context Engineering -- LLM Memory and Retrieval for AI Agents (Weaviate). https://weaviate.io/blog/context-engineering
- Cognee vs Mem0 comparison: https://dasroot.net/posts/2025/12/cognee-vs-mem0-memory-layer-comparison-llm-agents/

### Deployment and Cost

- Mem0 pricing: https://mem0.ai/pricing
- Zep pricing: https://www.getzep.com/pricing/
- Mem0 funding ($24M Series A, Oct 2025): https://sacra.com/c/mem0/
- Graph Memory for AI Agents (Mem0 blog, Jan 2026): https://mem0.ai/blog/graph-memory-solutions-ai-agents
- AWS -- Build persistent memory with Mem0 Open Source: https://aws.amazon.com/blogs/database/build-persistent-memory-for-agentic-ai-applications-with-mem0-open-source-amazon-elasticache-for-valkey-and-amazon-neptune-analytics/
