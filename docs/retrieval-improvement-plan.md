# Retrieval Strategy Improvement Plan

## Executive Summary

The current Engram retrieval pipeline is structurally sound (intent classification, edge-weighted traversal, 4-factor scoring, Atlas response) but has 12 identified gaps, 2 critical. Embeddings exist in the system but are completely disconnected from the query path, and traversal is limited to single-hop despite a multi-hop architecture.

This plan synthesizes findings from three parallel research tracks:
1. **Codebase audit**: 12 ranked gaps in current implementation
2. **SOTA research**: 8 state-of-the-art strategies analyzed (GraphRAG, hybrid retrieval, multi-hop, adaptive, re-ranking, temporal, personalization, hierarchical)
3. **Competitive analysis**: 5 systems compared (Zep/Graphiti, Mem0, Cognee, Microsoft GraphRAG, LangMem)

---

## Current Architecture

```
Query → Intent Classification (keyword) → Seed Selection (recency-only)
      → 1-hop Neighbor Expansion → Edge-Weight Boosting → Decay Scoring → Atlas Response
```

### What Works Well
- 4-factor Ebbinghaus decay scoring (recency, importance, relevance, user_affinity)
- Intent weight matrix (8 intents x 16 edge types) — more sophisticated than any competitor
- Access count feedback loop (retrieval strengthens memory stability)
- Atlas response pattern with full provenance — unique differentiator vs Mem0/Cognee
- Bounded traversal (depth/node/timeout limits) prevents runaway queries
- 3-tier entity resolution (exact, alias, fuzzy) — competitive with Zep's approach

### Critical Gaps
| # | Gap | Severity | Location |
|---|-----|----------|----------|
| 1 | Embeddings disconnected from query path | CRITICAL | `store.py:323` — `score_node()` called without query_embedding |
| 2 | Single-hop-only traversal | CRITICAL | `store.py:502-564` — only direct neighbors of seeds |
| 3 | Seed selection ignores strategy dispatch | HIGH | `store.py:464-469` — always `ORDER BY occurred_at DESC` |
| 4 | Intent classification is fragile keywords | HIGH | `intent.py:59-80` — no semantic understanding |
| 5 | No cross-session retrieval | HIGH | `queries.py:289-291` — `WHERE session_id = $session_id` |
| 6 | Proactive surfacing is naive | HIGH | `store.py:529-532` — `score * (1 + weight * 0.1)` |
| 7 | No re-ranking pass | MEDIUM | Results returned in single-pass score order, no diversity |
| 8 | Entity nodes not scored/returned properly | MEDIUM | `store.py:517-518` — entity neighbors silently skipped |
| 9 | No summary-tier retrieval | MEDIUM | Summaries exist but not used in query path |
| 10 | User affinity always 0.0 | MEDIUM | `compute_user_affinity()` exists but never called |
| 11 | Edge weight matrix is static | LOW | No adaptation based on retrieval feedback |
| 12 | No temporal context windows | MEDIUM | Can't ask "what happened last Tuesday" |

---

## Target Architecture

```
Query → Intent Classification → Query Expansion (optional HyDE)
      → Parallel Retrieval:
      │  ├─ Vector KNN seeds (Redis FT.SEARCH)
      │  ├─ Graph seeds (intent-dispatched strategy)
      │  └─ Summary seeds (for broad/historical queries)
      → Multi-Hop BFS Expansion (PPR-weighted)
      → Cross-Session Entity Expansion
      → RRF Fusion + MMR Diversity
      → Atlas Response with provenance
```

Benchmark target: Zep/Graphiti's P95 300ms retrieval latency with hybrid search.

---

## Phase 1: Quick Wins (High Impact, Low Effort)

### 1.1 Wire Embeddings into Query Path

**Problem**: `score_node()` is called without `query_embedding`, so `relevance_score` is always 0.5 for every node. The embedding infrastructure (SentenceTransformerEmbedder, EntityEmbeddingStore, RediSearch vector index) already exists but is never used during retrieval.

**SOTA context**: Zep, Mem0, and Cognee ALL use vector similarity as a primary retrieval channel. We're the only system that doesn't.

**Solution**: Add optional `EmbeddingService` to `Neo4jGraphStore`. During `get_subgraph()` and `get_context()`, embed the query text and pass it to `score_node()`.

**Files to modify**:
| File | Change |
|------|--------|
| `adapters/neo4j/store.py` | Add `embedding_service` param to `__init__`, embed query in `get_subgraph()`/`get_context()`, pass to `score_node()` |
| `api/dependencies.py` | Wire embedding service into graph store |

**Complexity**: S
**Impact**: HIGH — relevance_score becomes meaningful, dramatic improvement in result quality

```python
# In get_subgraph():
query_embedding = None
if self._embedding_service and query.query:
    query_embedding = await self._embedding_service.embed_text(query.query)

# Then pass to score_node:
scores = score_node(props, query_embedding=query_embedding)
```

**Success metric**: relevance_score distribution shifts from flat 0.5 to spread [0.0, 1.0]

---

### 1.2 Implement Seed Strategy Dispatch

**Problem**: `select_seed_strategy()` in `intent.py` returns strategy names like `"causal_roots"`, `"entity_hubs"`, `"temporal_anchors"` — but `get_subgraph()` ignores them entirely and always uses `GET_SUBGRAPH_SEED_EVENTS` (most recent events).

**SOTA context**: RAP-RAG (2025) formalizes adaptive seed selection with a retrieval method portfolio. Our intent→strategy mapping is already designed — just not wired.

**Solution**: Implement the 6 seed strategies as Cypher queries and dispatch based on `select_seed_strategy()`.

**Files to modify**:
| File | Change |
|------|--------|
| `adapters/neo4j/queries.py` | Add seed queries per strategy |
| `adapters/neo4j/store.py` | Dispatch to correct seed query in `get_subgraph()` |

**Complexity**: M
**Impact**: HIGH — "why did X fail?" starts from causal roots, not just recent events

**New Cypher templates**:
```python
GET_SEED_CAUSAL_ROOTS = """
MATCH (e:Event {session_id: $session_id})
WHERE (e)<-[:CAUSED_BY]-()
WITH e, size([(x)-[:CAUSED_BY]->(e) | x]) AS caused_count
RETURN e ORDER BY caused_count DESC, e.occurred_at DESC
LIMIT $seed_limit
""".strip()

GET_SEED_ENTITY_HUBS = """
MATCH (e:Event {session_id: $session_id})-[:REFERENCES]->(ent:Entity)
WITH e, count(ent) AS entity_count
RETURN e ORDER BY entity_count DESC, e.occurred_at DESC
LIMIT $seed_limit
""".strip()

GET_SEED_TEMPORAL_ANCHORS = """
MATCH (e:Event {session_id: $session_id})
WHERE e.importance_score IS NOT NULL
RETURN e ORDER BY e.importance_score DESC, e.occurred_at ASC
LIMIT $seed_limit
""".strip()

GET_SEED_USER_PROFILE = """
MATCH (u:UserProfile)<-[:HAS_PROFILE]-(ent:Entity)<-[:REFERENCES]-(e:Event)
WHERE e.session_id = $session_id
RETURN e ORDER BY e.occurred_at DESC
LIMIT $seed_limit
""".strip()

GET_SEED_SIMILAR_CLUSTER = """
MATCH (e:Event {session_id: $session_id})-[:SIMILAR_TO]-(other:Event)
WITH e, count(other) AS sim_count
RETURN e ORDER BY sim_count DESC, e.occurred_at DESC
LIMIT $seed_limit
""".strip()
```

**Success metric**: Different intents produce different seed sets (verify via `meta.seed_nodes`)

---

### 1.3 Enable Cross-Session Entity Retrieval

**Problem**: All queries are scoped to `WHERE session_id = $session_id`. Zep, Mem0, and LangMem all support cross-session memory natively. We can't answer "what tools have I used before?".

**Solution**: When intent is `who_is`, `personalize`, or when query references entities, also fetch entity-connected events from other sessions.

**Files to modify**:
| File | Change |
|------|--------|
| `adapters/neo4j/queries.py` | Add `GET_ENTITY_CROSS_SESSION_EVENTS` query |
| `adapters/neo4j/store.py` | In `get_subgraph()`, add cross-session entity expansion step |

**Complexity**: M
**Impact**: HIGH — enables "what do you know about me?" type queries

```python
GET_ENTITY_CROSS_SESSION_EVENTS = """
MATCH (e:Event {session_id: $session_id})-[:REFERENCES]->(ent:Entity)
WITH DISTINCT ent
MATCH (other:Event)-[:REFERENCES]->(ent)
WHERE other.session_id <> $session_id
RETURN other ORDER BY other.occurred_at DESC
LIMIT $limit
""".strip()
```

**Success metric**: Queries with `personalize` or `who_is` intent return events from previous sessions

---

### 1.4 Score Entity Nodes Properly

**Problem**: Entity nodes discovered during neighbor expansion are added as edges but never scored or included as AtlasNodes (line 517-518: only `neighbor_event_id` nodes get scored).

**Solution**: Build AtlasNodes for Entity neighbors too, with appropriate scoring.

**Files to modify**:
| File | Change |
|------|--------|
| `adapters/neo4j/store.py` | Handle entity neighbors in `get_subgraph()` |
| `domain/scoring.py` | Add `score_entity_node()` variant |

**Complexity**: S
**Impact**: MEDIUM — entities become first-class results in subgraph queries

---

## Phase 2: Medium-Term (Architectural Changes)

### 2.1 Multi-Hop Traversal with PPR Scoring

**Problem**: Despite `max_depth` parameter being accepted and validated, traversal is always single-hop. `get_subgraph()` only calls `GET_EVENT_NEIGHBORS` once per seed.

**SOTA context**: PPR (Personalized PageRank) over the retrieval subgraph outperforms naive BFS expansion (Diffusion-Aided RAG, ACL 2025). The choice of graph expansion operator matters more than the graph structure itself.

**Solution**: Implement iterative BFS traversal up to `max_depth` with PPR-style scoring for neighbor prioritization. No GDS needed — iterative PPR works within our bounded traversal (max_depth 3-5).

**Files to modify**:
| File | Change |
|------|--------|
| `adapters/neo4j/store.py` | Replace single-hop loop with BFS + PPR scoring |
| `adapters/neo4j/queries.py` | Add variable-length path queries |
| `domain/scoring.py` | Add PPR-based neighbor score attenuation |

**Complexity**: L
**Impact**: CRITICAL — enables causal chain traversal, pattern discovery

**Algorithm**:
```python
async def _ppr_expand(self, seed_ids, max_depth, max_nodes, edge_weights, alpha=0.15):
    """PPR-weighted BFS expansion. alpha = teleport probability (damping)."""
    scores = {sid: 1.0 / len(seed_ids) for sid in seed_ids}
    visited = set(seed_ids)
    frontier = list(seed_ids)

    for depth in range(max_depth):
        if not frontier or len(visited) >= max_nodes:
            break
        next_frontier = []
        for node_id in frontier:
            neighbors = await self._get_weighted_neighbors(node_id, edge_weights)
            for neighbor in neighbors:
                if neighbor.id not in visited and len(visited) < max_nodes:
                    # PPR: score decays by (1-alpha) per hop, weighted by edge
                    hop_score = scores[node_id] * (1 - alpha) * edge_weights.get(neighbor.edge_type, 1.0)
                    scores[neighbor.id] = scores.get(neighbor.id, 0) + hop_score
                    visited.add(neighbor.id)
                    next_frontier.append(neighbor.id)
        frontier = next_frontier
    return scores
```

**Success metric**: `meta.capacity.max_depth > 1` in responses; causal chains visible in results

---

### 2.2 Hybrid Multi-Channel Retrieval with RRF Fusion

**Problem**: Retrieval uses only graph traversal. Zep uses 3 parallel channels (semantic + BM25 + BFS) with Reciprocal Rank Fusion. We have the infrastructure but it's not connected.

**SOTA context**: HybridRAG (2024) and Zep/Graphiti both show that combining vector similarity with graph traversal significantly outperforms either alone. Zep achieves 94.8% DMR with P95 300ms.

**Solution**: Run 3 retrieval channels in parallel, fuse with RRF:
1. **Vector KNN**: Redis FT.SEARCH with query embedding → top-K entity/event seeds
2. **Graph traversal**: Current intent-based seed → PPR expansion
3. **Keyword BM25**: Redis FT.SEARCH with query text → matching events

**Files to modify/create**:
| File | Change |
|------|--------|
| `domain/reranking.py` | NEW — RRF fusion + MMR diversity |
| `adapters/redis/embedding_store.py` | Add `search_events_by_embedding()` |
| `adapters/neo4j/store.py` | Run 3 channels, fuse results |

**Complexity**: L
**Impact**: HIGH — handles novel queries, improves recall and precision

```python
# domain/reranking.py
def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse multiple ranked lists using RRF. k=60 is the standard constant."""
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, node_id in enumerate(ranked_list):
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

def maximal_marginal_relevance(
    candidates: list[tuple[str, float]],
    embeddings: dict[str, list[float]],
    lambda_param: float = 0.7,
    top_k: int = 20,
) -> list[str]:
    """MMR: balance relevance vs diversity. lambda=0.7 favors relevance."""
    ...
```

**Success metric**: Queries with no keyword matches return relevant results; result diversity improves

---

### 2.3 Summary-Tier Hierarchical Retrieval

**Problem**: Summary nodes are created during consolidation but never used in the query path. For older sessions, raw events may be deleted but summaries survive.

**SOTA context**: GraphRAG's "roll-up and drill-down" — query community summaries first, expand to children. Deep GraphRAG (2025) adaptively decides whether to drill deeper or summarize. This is the biggest bang-for-buck for cross-session queries.

**Solution**: Implement hierarchical retrieval: (1) query Summary nodes by semantic similarity, (2) for matching summaries, expand via SUMMARIZES→Event children, (3) score and rank the expanded set.

**Files to modify**:
| File | Change |
|------|--------|
| `adapters/neo4j/queries.py` | Add `GET_SESSION_SUMMARIES`, `GET_SUMMARY_EVENTS` |
| `adapters/neo4j/store.py` | Add summary retrieval path in `get_context()`/`get_subgraph()` |
| `domain/scoring.py` | Add `score_summary_node()` |
| `worker/enrichment.py` | Generate embeddings for Summary nodes (for vector search) |

**Complexity**: M
**Impact**: HIGH — enables retrieval across full lifecycle, broad "what happened?" queries

**Success metric**: Historical queries return summary-backed results even after raw events are pruned

---

### 2.4 Populate User Affinity Scores

**Problem**: `user_affinity` is always 0.0. `compute_user_affinity()` has 3 sub-components (session_proximity, retrieval_recurrence, entity_overlap) but none are computed.

**SOTA context**: PersonaAgent (2025) encodes user behavior patterns into community structure for personalized retrieval. We already have the full user subgraph (UserProfile, Preference, Skill, BehavioralPattern, Workflow) — just not wired into scoring.

**Solution**: During retrieval, compute user affinity on-the-fly using user's entity graph.

**Files to modify**:
| File | Change |
|------|--------|
| `adapters/neo4j/store.py` | Compute user affinity during scoring |
| `adapters/neo4j/queries.py` | Add query for user entity overlap |

**Complexity**: M
**Impact**: MEDIUM — personalized ranking for returning users

---

### 2.5 Temporal-Aware Retrieval

**Problem**: No way to retrieve events from specific time ranges. All events decay equally regardless of node type.

**SOTA context**: Zep's bi-temporal model (t_valid/t_invalid + t_created/t_expired) is more sophisticated. Our Redis store already has both event time (occurred_at) and ingestion time (stream entry ID = global_position). Per-type decay rates are a trivial win — entities should decay slower than events.

**Solution**:
1. Per-node-type decay rates (entities: longer stability; events: shorter)
2. Temporal contiguity scoring (events near-in-time to seeds get a boost)
3. Time-range filtering in SubgraphQuery

**Files to modify**:
| File | Change |
|------|--------|
| `domain/scoring.py` | Per-type `s_base` values in `compute_recency_score()` |
| `domain/models.py` | Add `time_range` field to `SubgraphQuery` |
| `domain/intent.py` | Extract temporal expressions from query |
| `adapters/neo4j/queries.py` | Time-filtered seed queries |

**Complexity**: M
**Impact**: MEDIUM — enables "what happened last Tuesday?" queries; smarter decay

---

## Phase 3: Strategic (LLM Integration / New Infrastructure)

### 3.1 LLM-Based Intent Classification + Query Expansion

**Problem**: Keyword matching is fragile. "Show me the chain of events that led to the error" should map to `why` intent.

**SOTA context**: GraphRAG DRIFT uses HyDE (Hypothetical Document Embeddings) for query expansion — embed a hypothetical ideal answer rather than the raw query. This dramatically improves recall for underspecified queries. Combined with entity extraction from the query, this would transform our intent pipeline.

**Solution**: Replace keyword classification with LLM-based intent + entity extraction + optional HyDE expansion.

**Files to modify**:
| File | Change |
|------|--------|
| `domain/intent.py` | Add `classify_intent_llm()` async function |
| `domain/query_expansion.py` | NEW — HyDE generation, follow-up question generation |
| `adapters/llm/client.py` | Add intent classification + HyDE prompts |
| `adapters/neo4j/store.py` | Use LLM classification when available, keyword as fallback |

**Complexity**: M
**Impact**: HIGH — dramatically better intent understanding + recall

**Success metric**: Intent classification accuracy > 90% on test queries (vs ~60% with keywords)

---

### 3.2 LLM Re-Ranking with Cross-Encoder

**Problem**: Results are ranked by formula-based composite score with no diversity control.

**SOTA context**: Zep uses a 5-stage reranking pipeline (RRF → MMR → episode-mentions → node-distance → cross-encoder). Re^3 framework shows Retrieval→Reranking→Reasoning pipeline for knowledge graph QA.

**Solution**: After Phase 2's RRF+MMR algorithmic reranking, optionally add LLM cross-encoder for high-value queries.

**Files to modify**:
| File | Change |
|------|--------|
| `domain/reranking.py` | Add LLM re-ranking function |
| `adapters/llm/client.py` | Add re-ranking prompt |
| `adapters/neo4j/store.py` | Optional re-ranking step |

**Complexity**: L
**Impact**: HIGH for complex queries, diminishing returns for simple ones

---

### 3.3 Community Detection + Global Queries

**Problem**: Can't answer "what are the main themes across all sessions?" — everything is entity-scoped or session-scoped.

**SOTA context**: GraphRAG's Leiden hierarchical clustering + community summaries enables global reasoning. LazyGraphRAG achieves this at 0.1% of full GraphRAG indexing cost.

**Solution**: Run Leiden community detection on entity subgraph (Python-side, since Neo4j Community lacks GDS). Store community assignments. Generate community summaries via Consumer 4. Add global search endpoint.

**Files to create/modify**:
| File | Change |
|------|--------|
| `domain/community.py` | NEW — Leiden clustering via networkx/cdlib |
| `worker/consolidation.py` | Generate community summaries |
| `api/routes/query.py` | Add global search mode |

**Complexity**: L
**Impact**: HIGH for analytics/overview queries

---

### 3.4 Adaptive Strategy Router

**Problem**: Every query goes through the same pipeline. Simple lookups don't need multi-hop or re-ranking.

**SOTA context**: RAP-RAG (2025) formalizes this with a retrieval method portfolio + adaptive planner. Enterprise deployments show 30-40% cost reduction while maintaining accuracy.

**Solution**: Classify query complexity, route to appropriate pipeline.

| Complexity | Pipeline |
|-----------|----------|
| Simple lookup | Direct Cypher, no scoring |
| Single-session | Graph seeds + embedding scoring |
| Multi-session | Cross-session + vector search + RRF |
| Complex reasoning | Multi-hop + LLM re-ranking |

**Complexity**: M (builds on existing intent classification)
**Impact**: MEDIUM — better latency/cost for simple queries

---

### 3.5 Retrieval Feedback Loop

**Problem**: No learning from retrieval quality. Static weights and scoring.

**SOTA context**: Cognee's "self-improving memory" learns from feedback to auto-tune. Our access_count feedback loop is a primitive version.

**Solution**: Track which retrieved nodes agents actually use. Adjust scoring weights over time.

**Complexity**: L
**Impact**: MEDIUM (long-term)

---

## Implementation Priority Matrix

```
                    Impact
                    HIGH              MEDIUM            LOW
         ┌──────────────────────────────────────────────────┐
  LOW    │ 1.1 Wire Embeddings     1.4 Entity Scores       │
  Effort │                                                  │
         ├──────────────────────────────────────────────────┤
  MED    │ 1.2 Seed Dispatch       2.4 User Affinity       │
         │ 1.3 Cross-Session       2.5 Temporal             │
         │ 2.3 Summary Tier        3.4 Adaptive Router      │
         ├──────────────────────────────────────────────────┤
  HIGH   │ 2.1 Multi-Hop + PPR     3.5 Feedback Loop       │
         │ 2.2 Hybrid + RRF/MMR                             │
         │ 3.1 LLM Intent + HyDE                            │
         │ 3.2 LLM Re-Ranking                               │
         │ 3.3 Community Detection                           │
         └──────────────────────────────────────────────────┘
```

## Recommended Implementation Order

1. **1.1 Wire Embeddings** — Immediate, highest ROI. Single day.
2. **1.4 Score Entity Nodes** — Quick fix, prerequisite for later work
3. **1.2 Seed Strategy Dispatch** — Activates existing dead code
4. **1.3 Cross-Session Retrieval** — Unlocks key use case (Zep/Mem0 parity)
5. **2.1 Multi-Hop + PPR** — Fixes the most critical architectural gap
6. **2.2 Hybrid Vector+Graph + RRF/MMR** — SOTA retrieval pattern
7. **2.3 Summary-Tier Retrieval** — Full lifecycle retrieval
8. **2.4 User Affinity** — Personalization (ADR-0012 completion)
9. **2.5 Temporal-Aware** — Per-type decay + time-range queries
10. **3.1 LLM Intent + HyDE** — When LLM client is implemented
11. **3.2 LLM Re-Ranking** — After LLM intent proves value
12. **3.3 Community Detection** — Global query capability
13. **3.4 Adaptive Router** — Optimization once multiple strategies exist
14. **3.5 Feedback Loop** — Long-term learning

---

## Competitive Positioning

| Capability | Engram (Current) | Engram (After Plan) | Zep | Mem0 | Cognee | GraphRAG |
|---|---|---|---|---|---|---|
| Retrieval channels | Graph only | Vector+BM25+Graph (3-channel) | Semantic+BM25+BFS | Vector+Graph enrich | Vector+Graph | Community+Local+DRIFT |
| Intent classification | 8-type keyword | LLM + HyDE expansion | None | None | None | HyDE |
| Scoring model | 4-factor Ebbinghaus | + PPR + RRF/MMR | RRF/MMR multi-reranker | Vector sim + reranker | Opaque | Community hierarchy |
| Multi-hop traversal | No (1-hop) | Yes (PPR-weighted BFS) | BFS (shallow) | No | Limited | DRIFT (iterative) |
| Temporal awareness | occurred_at + decay | Per-type decay + ranges | Bi-temporal | Timestamp only | None | None |
| Cross-session | No | Yes (entity bridge) | Yes (full graph) | Yes (user_id) | Yes | No (corpus-level) |
| Summary retrieval | No | Yes (hierarchical) | No | No | No | Yes (community) |
| User affinity | Stub (always 0) | Real (3-component) | Implicit | user_id scoping | None | None |
| Proactive surfacing | Naive | PPR-weighted | None | None | None | N/A |
| Provenance | Full | Full | Timestamps | None | Invertible chunks | None |
| Re-ranking | None | RRF+MMR+LLM | RRF+MMR+5-stage | Reranker module | Not detailed | Map-reduce |
| Forgetting/decay | Ebbinghaus + tier | + per-type rates | Temporal invalidation | Manual (90d) | Self-tuning | None |
| Global queries | No | Yes (community) | No | No | No | Yes (Leiden) |
| No-LLM retrieval | Yes | Yes (Phase 1-2) | Yes | No | No | No |

**Key insight**: No competing system combines intent-aware graph traversal + hybrid vector search + PPR scoring + full provenance + hierarchical summary retrieval. Implementing phases 1-2 would make Engram's retrieval uniquely powerful.

**Unique advantages to preserve**:
- Provenance/traceability (no competitor matches this)
- Intent weight matrix (8x16, no competitor has intent-aware edge weighting)
- No-LLM fast path (Zep shares this; Mem0/Cognee/GraphRAG require LLM at retrieval)
- Ebbinghaus decay with access-count feedback (cognitively grounded, vs Zep's simpler temporal invalidation)

---

## Research Sources

### Papers
- "From Local to Global: A Graph RAG Approach" (Edge et al., 2024) — https://arxiv.org/abs/2404.16130
- "HybridRAG: Integrating Knowledge Graphs and Vector Retrieval" — https://arxiv.org/html/2408.04948v1
- "Retrieval-Reasoning Processes for Multi-hop QA" — https://arxiv.org/html/2601.00536v1
- Zep/Graphiti temporal KG — https://arxiv.org/abs/2501.13956
- Mem0 — https://arxiv.org/abs/2504.19413
- DRIFT Search — https://microsoft.github.io/graphrag/query/drift_search/
- LazyGraphRAG — https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/
- Diffusion-Aided RAG with PPR — https://aclanthology.org/2025.clicit-1.36.pdf
- RAP-RAG — https://www.mdpi.com/2079-9292/14/21/4269
- CompactRAG — https://arxiv.org/html/2602.05728

### Implementations
- Graphiti: https://github.com/getzep/graphiti
- Microsoft GraphRAG: https://github.com/microsoft/graphrag
- Mem0: https://docs.mem0.ai
- Cognee: https://www.cognee.ai
- LangMem: https://langchain-ai.github.io/long-term-memory/
