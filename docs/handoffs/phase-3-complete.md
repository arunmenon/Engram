# Phase 3 Handoff: Graph Schema + API + Decay

**Status**: COMPLETE
**Date**: 2026-02-12
**Team**: engram-api (3 agents: domain-architect, data-engineer, api-engineer)

---

## Quality Gate Results

| Check | Result |
|-------|--------|
| `ruff check src/ tests/unit/` | PASS |
| `ruff format --check src/ tests/unit/` | PASS (48 files) |
| `mypy src/context_graph/` | PASS (37 source files, strict mode) |
| `pytest tests/unit -v` | PASS (228/228 tests in 0.25s) |
| `pytest tests/integration -v` | PASS (39/39 tests in 3.38s) |
| Docker services healthy | PASS (Redis + Neo4j) |

### Test Breakdown

| Test File | Tests | Coverage |
|-----------|:-----:|----------|
| `tests/unit/test_models.py` | 67 | Phase 1 domain models |
| `tests/unit/test_validation.py` | 20 | Phase 1 event validation |
| `tests/unit/test_projection.py` | 21 | Phase 2 projection logic |
| `tests/unit/test_api_events.py` | 14 | Phase 2 event endpoints |
| `tests/unit/test_scoring.py` | 67 | Ebbinghaus decay scoring |
| `tests/unit/test_intent.py` | 40 | Intent classification |
| `tests/unit/test_lineage.py` | 22 | Bounded traversal helpers |
| `tests/unit/test_enrichment.py` | 7 | Keyword extraction |
| `tests/unit/test_api_query.py` | 17 | Context/query/lineage/entity endpoints |
| `tests/integration/test_redis_store.py` | 12 | Redis EventStore against Docker |
| `tests/integration/test_neo4j_store.py` | 27 | Neo4j GraphStore against Docker |
| `tests/integration/test_neo4j_queries.py` | 7 | Neo4j traversal queries against Docker |
| **Total** | **267** | |

---

## Deliverables

### Domain: Decay Scoring (`domain/scoring.py`)

| Function | Purpose |
|----------|---------|
| `compute_recency_score` | Ebbinghaus R = e^(-t/S) with configurable stability |
| `compute_importance_score` | 1-10 base + access count boost + centrality boost |
| `compute_relevance_score` | Cosine similarity between query and node keywords |
| `compute_composite_score` | Weighted combination: recency * w_r + importance * w_i + relevance * w_v |
| `score_node` | End-to-end scorer: computes all 4 factors and returns NodeScores |

### Domain: Intent Classification (`domain/intent.py`)

| Function | Purpose |
|----------|---------|
| `classify_intent` | Keyword-based classification → dict of IntentType → confidence (0-1) |
| `get_edge_weights` | Maps inferred intents to per-EdgeType traversal weights from INTENT_WEIGHTS matrix |
| `select_seed_strategy` | Picks dominant intent → seed strategy (entity, temporal, causal, semantic, recent) |

### Domain: Lineage Traversal (`domain/lineage.py`)

| Function | Purpose |
|----------|---------|
| `validate_traversal_bounds` | Clamps depth/max_nodes/timeout to configured maximums |
| `build_lineage_cypher` | Generates parameterized CAUSED_BY chain traversal Cypher |
| `build_context_cypher` | Generates session context assembly Cypher |

### Consumer 3: Enrichment Worker (`worker/enrichment.py`)

| Component | Purpose |
|-----------|---------|
| `EnrichmentConsumer` | XREADGROUP consumer: reads events, extracts keywords, computes importance, writes to Neo4j |
| `extract_keywords` | Extracts keywords from event_type hierarchy and tool_name |
| TODO stubs | Embedding computation (SIMILAR_TO edges) and entity extraction (REFERENCES edges) for Phase 5 |

### Neo4j Store Extensions (`adapters/neo4j/store.py` — extended)

Phase 3 replaced NotImplementedError stubs with real implementations:

| Method | Implementation |
|--------|---------------|
| `get_context(session_id)` | Fetches session events, scores with decay, returns AtlasResponse |
| `get_subgraph(query)` | Intent-aware seed selection, neighbor expansion, scored ranking |
| `get_lineage(query)` | Bounded CAUSED_BY traversal with depth/node limits |
| `get_entity(entity_id)` | Entity lookup with connected events, returns EntityNode or None |

### Neo4j Query Templates (`adapters/neo4j/queries.py` — extended)

| Query | Purpose |
|-------|---------|
| `GET_SESSION_EVENTS` | Session events ordered by occurred_at |
| `GET_SESSION_EVENT_COUNT` | Count of events in a session |
| `GET_LINEAGE` | CAUSED_BY chain traversal with depth limit |
| `GET_EVENT_NEIGHBORS` | All outgoing relationships from an event |
| `GET_ENTITY_WITH_EVENTS` | Entity with REFERENCES edges from events |
| `UPDATE_ACCESS_COUNT` | Increment access_count + set last_accessed_at |
| `BATCH_UPDATE_ACCESS_COUNT` | Batch version via UNWIND |
| `UPDATE_EVENT_ENRICHMENT` | Set keywords + importance_score on event node |
| `GET_SUBGRAPH_SEED_EVENTS` | Seed events for subgraph query |

### API Routes (4 new endpoints)

| Route | Method | Purpose |
|-------|--------|---------|
| `/v1/context/{session_id}` | GET | Session working memory, decay-scored |
| `/v1/query/subgraph` | POST | Intent-aware subgraph query |
| `/v1/nodes/{node_id}/lineage` | GET | CAUSED_BY chain traversal |
| `/v1/entities/{entity_id}` | GET | Entity lookup with connected events |

---

## ADR Compliance

- [x] Ebbinghaus decay with configurable stability (ADR-0008)
- [x] Intent classification with 8 intent types (ADR-0009)
- [x] Intent-weighted edge traversal via INTENT_WEIGHTS matrix (ADR-0009)
- [x] Bounded queries: depth, max_nodes, timeout clamped to settings (ADR-0006)
- [x] Atlas response pattern for all graph query endpoints (ADR-0006)
- [x] Provenance on every returned node (ADR-0001)
- [x] Access count tracking for recency boost (ADR-0008)
- [x] Consumer 3 enrichment via XREADGROUP (ADR-0013)
- [x] Domain module has zero framework imports (ADR principle)

---

## Frozen Contracts (Phase 4+ MUST NOT modify existing signatures)

Previously frozen:
- Phase 1: `domain/models.py`, `ports/*`, `settings.py`
- Phase 2: `adapters/redis/store.py`, `adapters/neo4j/store.py` (base methods), `worker/consumer.py`

Newly frozen (Phase 3):
- `domain/scoring.py` — scoring function signatures
- `domain/intent.py` — classify_intent, get_edge_weights, select_seed_strategy signatures
- `domain/lineage.py` — traversal helper signatures
- `api/routes/query.py` — POST /v1/query/subgraph request/response shape
- `api/routes/context.py` — GET /v1/context/{session_id} request/response shape

Phase 4 MAY:
- Add new scoring factors to `scoring.py`
- Add new intent keywords to `intent.py`
- Extend Neo4j queries with maintenance/pruning queries
- Add admin API routes
- Implement consolidation worker (Consumer 4)
- Implement forgetting/retention tier enforcement

---

## Next Phase: Phase 4 — Memory Intelligence

### Team Composition
| Agent | Files |
|-------|-------|
| memory-architect | `domain/consolidation.py`, `domain/forgetting.py`, `worker/consolidation.py`, `adapters/neo4j/maintenance.py`, `adapters/redis/trimmer.py` |
| test-api-engineer | `api/routes/admin.py`, tests |

### Prerequisites
- Docker services running
- All Phase 3 contracts frozen
- Consumer 4 (consolidation) needs LLM adapter — placeholder until Phase 5
