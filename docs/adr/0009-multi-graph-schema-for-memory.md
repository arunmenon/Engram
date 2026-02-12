# ADR-0009: Multi-Graph Schema and Intent-Aware Retrieval for Agent Memory

Status: **Accepted**
Date: 2026-02-11
Extended-by: ADR-0011 (ontological foundation), ADR-0012 (user personalization ontology)
Amended-by: ADR-0010 (Redis replaces Postgres), ADR-0008 (user-state-aware scoring)

## Context

The current graph projection design (ADR-0005) creates a single relationship type between event nodes in Neo4j. Research demonstrates that decomposing the graph into orthogonal typed edge views -- temporal, causal, semantic, entity -- dramatically improves retrieval accuracy and enables intent-aware queries.

MAGMA (Jiang et al., 2026) achieves 45.5% higher reasoning accuracy and 95% token reduction by separating memory into four orthogonal graph views with policy-guided traversal. The Yang et al. (2026) survey identifies five graph architecture types, with hybrid multi-graph approaches outperforming monolithic designs across benchmarks. These findings directly inform how we should structure the Neo4j projection.

### Research Basis

**Multi-graph schema:**
- MAGMA: four orthogonal views (temporal, causal, semantic, entity) with intent-aware beam traversal
- Yang et al. survey: five graph types (KG, temporal, hierarchical, hypergraph, hybrid) -- hybrid approaches outperform single-type designs
- A-MEM: seven-field note schema with rich derived attributes (keywords, tags, contextual description, embedding, links)

**Intent-aware retrieval:**
- MAGMA: query intent classification (Why/When/Who-What) with edge-type-specific weights; causal edges weighted 3.0-5.0 for "why" queries, temporal 0.5-4.0 for "when", entity 2.5-6.0 for "who/what"
- Yang et al.: six retrieval operator categories (similarity, rule-based, temporal, graph-based, RL-based, agent-based)

**Node enrichment:**
- A-MEM's Zettelkasten model: content, timestamp, keywords, tags, contextual description, embedding, links
- HiMeS: compression before retrieval improves contextual alignment by 175%
- Survey: hierarchical summarization (event -> episode -> session -> agent) follows hippocampal indexing pattern

**Provenance gap:**
- No surveyed paper uses true event sourcing with an immutable ledger as provenance backbone
- Graphiti's bi-temporal tracking (valid time + transaction time) is the closest precedent
- Our `global_position` + immutable events + `parent_event_id` chains provide provenance that the literature lacks

Non-goals for this decision:
- Hypergraph or n-ary edge types (binary edges sufficient for MVP)
- RL-based retrieval optimization (requires training data from production usage)
- Vector database as a separate component (embeddings stored as Neo4j node properties)

## Decision

The Neo4j graph projection MUST use four typed edge categories and enriched node properties. The API layer MUST support intent-aware retrieval that weights edge types based on query classification.

### Graph Schema

#### Node Types

All projected nodes share a base property set, with type-specific extensions:

**Event Node** (`:Event`)
```
Properties:
  event_id         : STRING (PK, from Postgres)
  event_type       : STRING (dot-namespaced: agent.invoke, tool.execute, etc.)
  occurred_at      : DATETIME
  session_id       : STRING
  agent_id         : STRING
  trace_id         : STRING
  tool_name        : STRING (nullable)
  global_position  : STRING    # Redis Stream entry ID (e.g., "1707644400000-0")

  # Derived (populated by enrichment -- ADR-0008 Stage 2)
  keywords         : LIST<STRING>
  summary          : STRING
  embedding        : LIST<FLOAT> (384-dim or 1536-dim)
  importance_score : INTEGER (1-10)
  access_count     : INTEGER (default 0)
  last_accessed_at : DATETIME (nullable)
```

**Entity Node** (`:Entity`) -- derived during enrichment
```
Properties:
  entity_id   : STRING (PK, deterministic from name + type)
  name        : STRING
  entity_type : STRING (agent, tool, user, resource, concept)
  first_seen  : DATETIME
  last_seen   : DATETIME
  mention_count : INTEGER
```

**Summary Node** (`:Summary`) -- created during re-consolidation
```
Properties:
  summary_id   : STRING (PK)
  scope        : STRING (episode | session | agent)
  scope_id     : STRING (trace_id | session_id | agent_id)
  content      : STRING
  created_at   : DATETIME
  event_count  : INTEGER
  time_range   : LIST<DATETIME> [start, end]
```

#### Edge Types (Four Orthogonal Views)

Each edge type serves a distinct query purpose. This decomposition follows MAGMA's architecture and the survey's recommendation for hybrid multi-graph approaches.

**1. FOLLOWS (Temporal)**
```
(:Event)-[:FOLLOWS]->(:Event)
Properties:
  session_id : STRING
  delta_ms   : INTEGER (milliseconds between events)
```
- Created in Stage 1 (event projection)
- Based on `occurred_at` ordering within a session
- Immutable once created (temporal backbone, never modified)
- Supports "when" queries and session replay

**2. CAUSED_BY (Causal)**
```
(:Event)-[:CAUSED_BY]->(:Event)
Properties:
  mechanism : STRING (direct | inferred)
```
- `direct`: Created in Stage 1 from `parent_event_id` reference
- `inferred`: Created in Stage 2 (enrichment) from payload analysis
- Supports "why" queries and lineage traversal
- Aligns with W3C PROV-DM `GENERATED_BY` / `INFORMED_BY` vocabulary (ADR-0001)

**3. SIMILAR_TO (Semantic)**
```
(:Event)-[:SIMILAR_TO]->(:Event)
Properties:
  score : FLOAT (cosine similarity)
```
- Created in Stage 2 (enrichment) when `cosine(embedding_i, embedding_j) > 0.85`
- Undirected (symmetric similarity)
- Subject to warm-tier pruning (ADR-0008) -- low-score edges removed after 24h
- Supports "related" queries and associative retrieval

**4. REFERENCES (Entity)**
```
(:Event)-[:REFERENCES]->(:Entity)
Properties:
  role : STRING (subject | object | tool | target)
```
- Created in Stage 2 (enrichment) from entity extraction
- Connects events to shared entity nodes
- Solves object permanence: the same agent or tool across sessions is one entity node
- Supports "who/what" queries and cross-session entity tracking

**5. SUMMARIZES (Hierarchical)**
```
(:Summary)-[:SUMMARIZES]->(:Event)
(:Summary)-[:SUMMARIZES]->(:Summary)
```
- Created in Stage 3 (re-consolidation)
- Links summary nodes to the events or lower-level summaries they compress
- Enables hierarchical retrieval: query a summary, drill down to source events
- Preserves provenance: summary -> event -> Postgres source

### Intent-Aware Retrieval

The API layer MUST classify query intent and weight edge traversal accordingly. Intent classification determines which edge types are prioritized during graph traversal.

#### Intent Classification

Queries to `/v1/query/subgraph` and `/v1/nodes/{node_id}/lineage` SHOULD accept an optional `intent` parameter:

| Intent | Description | Primary Edge | Example Query |
|--------|-------------|--------------|---------------|
| `why` | Causal reasoning, root cause | CAUSED_BY | "Why did the agent choose tool X?" |
| `when` | Temporal ordering, sequence | FOLLOWS | "What happened before event Y?" |
| `what` | Entity identification, description | REFERENCES | "What tools were used in session Z?" |
| `related` | Associative, similar events | SIMILAR_TO | "Find events similar to this one" |
| `general` | Balanced traversal | All equal | Default when no intent specified |

#### Edge Weight Configuration

Traversal scoring function (applied in Cypher MATCH patterns):

```
traverse_score(edge, intent) = intent_weight[intent][edge.type]
                              * edge_quality(edge)
```

Default intent weight matrix:

```
INTENT_WEIGHTS = {
    "why":     {CAUSED_BY: 5.0, FOLLOWS: 1.0, SIMILAR_TO: 1.5, REFERENCES: 2.0, SUMMARIZES: 1.0},
    "when":    {CAUSED_BY: 1.0, FOLLOWS: 5.0, SIMILAR_TO: 0.5, REFERENCES: 1.0, SUMMARIZES: 0.5},
    "what":    {CAUSED_BY: 2.0, FOLLOWS: 1.0, SIMILAR_TO: 2.0, REFERENCES: 5.0, SUMMARIZES: 2.0},
    "related": {CAUSED_BY: 1.5, FOLLOWS: 0.5, SIMILAR_TO: 5.0, REFERENCES: 2.0, SUMMARIZES: 1.5},
    "general": {CAUSED_BY: 2.0, FOLLOWS: 2.0, SIMILAR_TO: 2.0, REFERENCES: 2.0, SUMMARIZES: 2.0},
}
```

ADR-0012 extends this matrix with three additional intents (`who_is`, `how_does`, `personalize`) and weights for all user personalization edge types (HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, DERIVED_FROM, ABSTRACTED_FROM, PARENT_SKILL, SAME_AS, RELATED_TO). See ADR-0012 Section 3 for the complete extended weight matrix.

Weights are configurable per deployment. MAGMA's ablation study shows removing adaptive intent weighting causes the largest performance drop (0.700 -> 0.637), confirming intent-aware traversal is the highest-value retrieval enhancement.

**Alternative retrieval algorithm: Personalized PageRank.** The intent weight matrix is a hand-tuned heuristic approach. Personalized PageRank (PPR) is a graph-theoretic alternative where query-relevant seed nodes propagate relevance scores through the graph topology, and the graph structure itself determines what's important. See Open Questions section for evaluation criteria.

#### Traversal Bounds

All traversals MUST enforce bounds (consistent with ADR-0001):

| Parameter | Default | Max |
|-----------|---------|-----|
| `max_depth` | 3 | 10 |
| `max_nodes` | 100 | 500 |
| `timeout_ms` | 5000 | 30000 |

### Node Enrichment Schema

During Stage 2 enrichment (ADR-0008), event nodes MUST be annotated with derived attributes following A-MEM's seven-field model:

| A-MEM Field | Neo4j Property | Derivation |
|-------------|---------------|------------|
| Content | (event payload via `payload_ref`) | Not stored in Neo4j; dereference to Postgres |
| Timestamp | `occurred_at` | Direct from event |
| Keywords | `keywords` | NLP extraction from payload content |
| Tags | `event_type` (dot-namespaced) | Direct from event |
| Context description | `summary` | LLM or rule-based compression |
| Embedding | `embedding` | Sentence-transformer encoding |
| Links | Neo4j edges | Four edge types above |

### Provenance in Query Responses

All query responses MUST include provenance pointers per the Atlas pattern (ADR-0006). Each node in the response MUST include:

```json
{
  "node_id": "...",
  "type": "Event",
  "attributes": { "event_type": "...", "tool_name": "...", ... },
  "provenance": {
    "event_id": "uuid",
    "global_position": "1707644400000-0",
    "source": "redis",
    "occurred_at": "2026-02-11T10:30:00Z",
    "session_id": "...",
    "agent_id": "...",
    "trace_id": "..."
  },
  "scores": {
    "decay_score": 0.87,
    "relevance_score": 0.92,
    "importance_score": 7
  }
}
```

The `scores` field is new -- it enables clients to understand why particular nodes were ranked highly, supporting the traceability-first principle.

### Schema Migration Path

Because Neo4j is a derived projection (ADR-0003), schema changes do NOT require data migration:

1. Update projection logic to produce new edge types / node properties
2. Trigger full re-projection from Postgres events
3. Neo4j rebuilds with the new schema

This is a unique advantage over systems where the graph is the primary store. The immutable Postgres ledger means we can re-project with different schemas, enrichment strategies, or edge-creation thresholds without losing data.

## Consequences

### Positive

- **Dramatic retrieval improvement**: MAGMA demonstrates 45.5% accuracy gain from multi-graph + intent-aware traversal
- **Query specificity**: "Why" queries traverse causal chains; "when" queries follow temporal backbone; "what" queries resolve entities -- each query type gets the most useful edges
- **Token efficiency**: Intent-aware traversal surfaces relevant nodes first, reducing context size passed to agents (MAGMA reports 95% token reduction)
- **Cross-session entity tracking**: Entity nodes solve the object permanence problem -- the same tool across sessions is one node
- **Hierarchical navigation**: Summary nodes enable agents to browse at the right granularity, drilling down when needed
- **Provenance preserved**: Every graph element traces back to immutable Postgres events via `event_id`
- **Schema evolution via re-projection**: No migration required; change projection logic and rebuild

### Negative

- **Enrichment compute cost**: Embedding generation, entity extraction, and similarity computation add processing overhead
- **Edge volume**: Four edge types multiply the number of relationships; requires monitoring and pruning (ADR-0008 warm-tier policy)
- **Intent classification accuracy**: Misclassified intent produces suboptimal edge weighting; may need fallback to "general" intent
- **Entity resolution quality**: Determining that "GPT-4" and "gpt-4o" reference the same entity family requires heuristics that may be imperfect

### Risks to Monitor

| Risk | Mitigation |
|------|------------|
| Embedding computation becomes bottleneck | Use lightweight model (all-MiniLM-L6-v2, 384-dim); batch computation; make async |
| Semantic edge explosion (too many SIMILAR_TO edges) | Enforce high similarity threshold (0.85); prune in warm tier; limit edges per node |
| Entity resolution errors create false connections | Start with high-confidence entity extraction only; add manual correction endpoint |
| Intent classification adds API latency | Pre-classify common query patterns; cache intent for repeated queries; make intent optional with "general" default |

## Alternatives Considered

### 1. Single edge type with metadata
Rejected. A single `RELATES_TO` edge with type metadata requires filtering at query time rather than traversal time. Multi-typed edges enable Cypher pattern matching to select the right edge type upfront, which is more performant for graph databases.

### 2. Separate Neo4j databases per graph view
Rejected. MAGMA's four views are orthogonal but share the same node set. Separate databases would require cross-database joins. A single Neo4j database with typed edges achieves the same logical separation with better query performance.

### 3. External vector database for semantic edges
Deferred. Storing embeddings as Neo4j node properties is sufficient at our expected scale. If embedding search latency exceeds acceptable thresholds (benchmark at 100K events), we can add a dedicated vector index (Neo4j's built-in vector index or an external Pinecone/Qdrant) without changing the graph schema.

### 4. Full knowledge graph extraction (NER + relation extraction)
Deferred for MVP. Full KG extraction from event payloads is high-value but high-complexity. Start with entity nodes (agents, tools, sessions) derived from event metadata fields. Expand to payload-content-based entities in a future phase.

## Open Questions

### 1. Personalized PageRank as Retrieval Algorithm

**Context:** Our current retrieval strategy uses a hand-tuned intent weight matrix — the caller declares an intent (`why`, `when`, `what`, `related`, `general`), and edge types receive static weights that bias the traversal. This works but has limitations: weights are heuristic (not learned), the matrix grows combinatorially as edge types increase (currently 16 edge types x 8 intents), and it cannot discover non-obvious multi-hop paths that the weight matrix doesn't anticipate.

**The alternative: Personalized PageRank (PPR).** PPR is a graph-theoretic retrieval algorithm validated at NeurIPS 2024 by HippoRAG (Ohio State NLP Group). Instead of hand-tuning which edges to follow, PPR:

1. Seeds relevance on query-matched nodes (entities extracted from the query, matched to existing graph nodes)
2. Propagates relevance through the graph topology via random walks with restart probability (typically α = 0.15)
3. Returns the top-K nodes by accumulated relevance score

The graph structure itself determines what's relevant — nodes with many connections to query-relevant nodes score higher, naturally handling multi-hop reasoning.

**HippoRAG results:** +7 F1 over NV-Embed-v2 on associative (multi-hop) benchmarks. HippoRAG 2 (Feb 2025) improved further with dual-node KG (passage + phrase nodes, analogous to our Event + Entity pattern) and LLM-based triple filtering.

**How PPR would integrate with our architecture:**

| Concern | Current (Intent Weights) | With PPR |
|---------|------------------------|----------|
| Query routing | Caller declares intent → static weight matrix | Extract entities from query → seed PPR on matched Entity/Event nodes |
| Edge weighting | Per-intent static weights (hand-tuned) | Edge types could still have base weights (teleport probability modifiers), but topology dominates |
| Multi-hop | Limited by max_depth (default 3) and heuristic weights | Natural — PPR propagates through arbitrary path lengths with diminishing relevance |
| Scalability | O(edges traversed) per query | O(edges * iterations) but converges fast; Neo4j has native graph algorithms library (GDS) with PPR implementation |
| Explainability | "This node was returned because CAUSED_BY edges had weight 5.0 for your 'why' intent" | "This node accumulated relevance 0.73 through 3 paths from your seed nodes" — less interpretable |
| Intent sensitivity | Very sensitive — different intents produce very different results | Less sensitive to declared intent; more sensitive to query content and graph structure |

**Implementation path (if adopted):**

```cypher
// Neo4j GDS Personalized PageRank
CALL gds.pageRank.stream('memory-graph', {
  maxIterations: 20,
  dampingFactor: 0.85,
  sourceNodes: $seed_node_ids,
  relationshipWeightProperty: 'weight'
})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).event_id AS event_id, score
ORDER BY score DESC
LIMIT $max_nodes
```

**Evaluation criteria before adoption:**

1. **Benchmark against intent weights** on a representative query set (50+ queries across all intent types). PPR should match or exceed intent-weighted retrieval on precision@K and recall@K.
2. **Latency impact**: PPR on Neo4j GDS adds ~10-50ms for graphs under 100K nodes. Verify this stays within the 5000ms timeout budget.
3. **Explainability tradeoff**: Intent weights produce interpretable results ("this was returned because of causal edges"). PPR produces a score but the *path* that generated it is less obvious. For a traceability-first system, this matters.
4. **Hybrid approach viability**: Use intent weights for simple queries (`why` → follow CAUSED_BY) and PPR for `general` or `related` intents where the optimal traversal isn't obvious. This preserves explainability for directed queries while gaining PPR's associative power for open-ended ones.

**Recommendation:** Defer to post-MVP. Implement intent-weighted traversal first (simpler, more interpretable, sufficient for initial use cases). Add PPR as a `retrieval_method: "ppr" | "intent_weighted"` parameter on `/v1/query/subgraph` when production query patterns reveal cases where intent weights underperform. The graph schema and API contract do not need to change — PPR is a retrieval algorithm swap, not an architectural change.

**References:**
- Xiong et al. (2024). "HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models." NeurIPS 2024. arXiv:2405.14831
- Xiong et al. (2025). "HippoRAG 2: Towards Factual and Comprehensive RAG." arXiv:2502.14802
- Neo4j GDS PageRank: https://neo4j.com/docs/graph-data-science/current/algorithms/page-rank/

## Research References

- Jiang et al. (2026). "MAGMA: A Multi-Graph based Agentic Memory Architecture." arXiv:2601.03236
- Yang et al. (2026). "Graph-based Agent Memory: Taxonomy, Techniques, and Applications." arXiv:2602.05665
- Xu et al. (2025). "A-MEM: Agentic Memory for LLM Agents." arXiv:2502.12110
- Pink et al. (2025). "Position: Episodic Memory is the Missing Piece for Long-Term LLM Agents." arXiv:2502.06975
- Hu et al. (2025). "Memory in the Age of AI Agents." arXiv:2512.13564
- Li et al. (2026). "HiMeS: Hippocampus-inspired Memory System." arXiv:2601.06152
- Liang et al. (2025). "AI Meets Brain: Memory Systems from Cognitive Neuroscience to Autonomous Agents." arXiv:2512.23343
- Xiong et al. (2024). "HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models." NeurIPS 2024. arXiv:2405.14831
- Xiong et al. (2025). "HippoRAG 2: Towards Factual and Comprehensive RAG." arXiv:2502.14802

## Amendments

### 2026-02-11: W3C PROV-DM Compatibility Mapping

ADR-0001 Section 10 specifies adoption of W3C PROV-DM vocabulary for provenance semantics. The edge types defined in this ADR serve as the operational graph vocabulary optimized for intent-aware traversal. The following table documents the mapping between ADR-0009 edge types and PROV-DM terms for interoperability:

| ADR-0009 Edge | PROV-DM Mapping | Notes |
|---------------|----------------|-------|
| `CAUSED_BY` | `wasGeneratedBy`, `wasInformedBy` | Direct causal lineage; primary provenance edge |
| `FOLLOWS` | (no direct mapping) | Temporal ordering; PROV-DM uses `qualifiedStart`/`qualifiedEnd` for temporal relations |
| `REFERENCES` | `wasAttributedTo`, `used` | Entity reference; maps to provenance attribution |
| `SIMILAR_TO` | `wasDerivedFrom` (loose) | Semantic similarity; weakest PROV-DM alignment |
| `SUMMARIZES` | `alternateOf`, `specializationOf` | Hierarchical compression; summary is an alternate representation |

ADR-0001's commitment to W3C PROV-DM is maintained as the conceptual provenance vocabulary. The ADR-0009 edge types are the operational vocabulary used in Neo4j graph traversal. Systems requiring PROV-DM interchange format can translate using this mapping table.

### 2026-02-11: Redis Adoption (ADR-0010)

Promoted to Accepted. Per ADR-0010, provenance.source in Atlas response changes from "postgres" to "redis". provenance.global_position format changes from integer to Redis Stream entry ID string. All Neo4j schema, edge types, intent weights, and retrieval patterns unchanged.

### 2026-02-12: System-Owned Intent Classification and Multi-Intent Retrieval

**What changed:** Intent classification moves from caller-provided to system-inferred. The `intent` parameter on `/v1/query/subgraph` and `/v1/nodes/{node_id}/lineage` becomes an optional hint, not a required input. The system owns the full retrieval intelligence pipeline.

**Rationale:** The context graph's contract is: *given user context, surface relevant high-quality context.* External agents are a black box — we cannot depend on them to classify intent correctly, extract the right seed entities, or decompose multi-faceted questions. Meanwhile, our system has the graph topology, user history, entity connections, and decay state — we are in the best position to determine what context to surface.

The information asymmetry is clear:

| Knowledge | External Agent | Context Graph |
|-----------|:-:|:-:|
| User's raw message | Yes | Yes (passed as `query`) |
| Full graph topology and entity connections | No | Yes |
| User's cross-session history and patterns | No | Yes |
| Node decay state (access frequency, importance) | No | Yes |
| Cross-user patterns (similar issues across users) | No | Yes |
| Retrieval history (what was surfaced before, was it useful) | No | Yes |

**Design changes:**

#### 1. Intent Classification Is Internal

The system MUST infer intent from the query text and user context. The process:

1. **Entity extraction**: Extract key entities from the query text. Match against existing Entity nodes in the graph via keyword and embedding similarity.
2. **Intent classification**: Classify query into one or more intents using the query text, extracted entities, and conversational context. Classification MAY use rule-based heuristics (keyword patterns: "why" → `why`, "when/before/after" → `when`, "what/which/who" → `what`) or LLM-based classification.
3. **Seed node selection**: Identify starting nodes for traversal from extracted entities, the user's Entity node (via `agent_id`/`session_id`), and recent high-importance events in the user's graph neighborhood.

The `intent` parameter on API endpoints becomes an **optional override**. When provided, it bypasses internal classification. When absent (the expected default), the system classifies internally.

#### 2. Multi-Intent Decomposition

Real user queries are rarely single-intent. "Why do my customers' payments keep failing?" contains:

- `why`: What's causing the failures? (causal chain)
- `when`: "keep failing" implies recurring pattern over time (temporal)
- `what`: "my customers' payments" implies entity-level context (which customers, which payments)

The system SHOULD decompose complex queries into multiple intents and run **parallel traversals** that are merged into a single result:

```
1. Classify query → {why: 0.7, when: 0.4, what: 0.5}  (confidence per intent)
2. For each intent above confidence threshold (default 0.3):
     Run weighted traversal from seed nodes with that intent's weight matrix
3. Merge result sets:
     - Union all reached nodes
     - For nodes reached by multiple traversals, combine scores:
       combined_score(node) = max(score_per_intent) + 0.2 * sum(other_scores)
     - Nodes reached by multiple intents rank higher (multi-signal confirmation)
4. Apply decay scoring (ADR-0008) to merged set
5. Return top max_nodes results
```

Nodes that appear in multiple intent traversals are **more likely to be relevant** — they're reachable via both causal and temporal paths, for example. The merge formula rewards this multi-signal confirmation.

#### 3. Proactive Context Surfacing

Beyond answering the explicit query, the system SHOULD surface **contextually useful nodes** that the user didn't ask for but the graph topology indicates are relevant:

- **Recurring patterns**: If the graph shows the user has encountered similar issues before (SIMILAR_TO edges to past sessions), include the resolution from the previous occurrence.
- **Entity context**: If the query involves an entity (e.g., a specific transaction) that has high-importance connections (e.g., a known systemic issue), include those connections even if the query didn't ask about them.
- **Retrieval history**: If a previous query in the same session returned nodes that were subsequently accessed again (high `access_count` boost from reconsolidation), those nodes are contextually anchored and SHOULD be included at reduced weight.

Proactive nodes MUST be marked in the response so the caller can distinguish them from directly-requested results:

```json
{
  "node_id": "...",
  "retrieval_reason": "proactive",
  "proactive_signal": "recurring_pattern",
  ...
}
```

vs. directly-requested nodes:
```json
{
  "node_id": "...",
  "retrieval_reason": "direct",
  ...
}
```

#### 4. Updated Intent Weight Matrix Usage

The intent weight matrix defined in the Decision section remains the traversal mechanism. What changes is **who selects which row(s) to use**:

| Before (caller-driven) | After (system-owned) |
|------------------------|---------------------|
| Caller passes `intent: "why"` | System infers `{why: 0.7, when: 0.4, what: 0.5}` |
| Single row from the weight matrix | Multiple rows, blended by confidence |
| One traversal per query | Multiple traversals merged |
| Caller picks seed nodes | System selects seeds from entity extraction + graph topology |
| Returns what was asked for | Returns what's needed (direct + proactive) |

The weight matrix values themselves are unchanged. The change is in orchestration, not in the traversal mechanics.

#### 5. Response Meta Extension

The `meta` field in Atlas responses MUST include retrieval reasoning:

```json
{
  "meta": {
    "query_ms": 145,
    "nodes_returned": 18,
    "truncated": false,
    "inferred_intents": {"why": 0.7, "when": 0.4, "what": 0.5},
    "intent_override": null,
    "seed_nodes": ["entity:card_declined", "entity:marias-bakery"],
    "proactive_nodes_count": 3,
    "scoring_weights": {"recency": 1.0, "importance": 1.0, "relevance": 1.0},
    "capacity": {"max_nodes": 100, "used_nodes": 18, "max_depth": 3}
  }
}
```

This preserves the traceability-first principle: the caller always knows *how* the system decided what to return. `inferred_intents` shows what the system understood. `seed_nodes` shows where traversal started. `proactive_nodes_count` shows how many results were system-initiated rather than query-matched.

#### Risks

| Risk | Mitigation |
|------|------------|
| Internal intent classification is worse than what a well-built agent provides | The `intent` parameter remains as an optional override; sophisticated callers can still drive intent explicitly |
| Multi-intent traversal increases query latency | Parallel traversals (not sequential); enforce per-intent timeout budget that sums to total `timeout_ms` |
| Proactive context is noise rather than signal | Mark proactive nodes clearly; start conservative (only surface recurring patterns with high confidence); collect feedback metrics |
| Entity extraction from query text is unreliable | Use embedding similarity as fallback when keyword matching fails; degrade gracefully to `general` intent with user's entity node as sole seed |
