# Phase 2 Handoff: Core Event Store + Projection

**Status**: COMPLETE
**Date**: 2026-02-12
**Team**: engram-core (4 agents: data-engineer, neo4j-engineer, domain-architect, api-engineer)

---

## Quality Gate Results

| Check | Result |
|-------|--------|
| `ruff check src/ tests/unit/` | PASS |
| `ruff format --check src/ tests/unit/` | PASS (35 files) |
| `mypy src/context_graph/` | PASS (29 source files, strict mode) |
| `pytest tests/unit -v` | PASS (122/122 tests in 0.22s) |
| `pytest tests/integration -v` | PASS (32/32 tests in 3.19s) |
| Docker services healthy | PASS (Redis + Neo4j) |

### Test Breakdown

| Test File | Tests | Coverage |
|-----------|:-----:|----------|
| `tests/unit/test_models.py` | 67 | Phase 1 domain models |
| `tests/unit/test_validation.py` | 20 | Phase 1 event validation |
| `tests/unit/test_projection.py` | 21 | Event-to-graph projection logic |
| `tests/unit/test_api_events.py` | 14 | API endpoints (unit) |
| `tests/integration/test_redis_store.py` | 12 | Redis EventStore against Docker |
| `tests/integration/test_neo4j_store.py` | 20 | Neo4j GraphStore against Docker |
| **Total** | **154** | |

---

## Deliverables

### Redis EventStore Adapter

| File | Purpose |
|------|---------|
| `adapters/redis/store.py` | EventStore implementation — append (Lua), get_by_id (JSON.GET), get_by_session (FT.SEARCH), search (composite FT.SEARCH) |
| `adapters/redis/lua/ingest.lua` | Atomic idempotent ingestion: dedup check + XADD + JSON.SET + ZADD in single Lua script |
| `adapters/redis/indexes.py` | RediSearch index definition: session_id, agent_id, event_type, tool_name (TAG), occurred_at_epoch_ms (NUMERIC SORTABLE) |

### Neo4j GraphStore Adapter

| File | Purpose |
|------|---------|
| `adapters/neo4j/store.py` | GraphStore implementation — merge_event_node, merge_entity_node, merge_summary_node, create_edge, create_edges_batch, ensure_constraints |
| `adapters/neo4j/queries.py` | Cypher query templates — MERGE patterns for all node types, typed relationship creation per EdgeType |

Phase 3+ methods (get_subgraph, get_lineage, get_context, get_entity) raise `NotImplementedError`.

### Domain Projection Logic

| File | Purpose |
|------|---------|
| `domain/projection.py` | Pure domain logic (zero framework imports): event_to_node, compute_follows_edge (with delta_ms), compute_caused_by_edge (mechanism=direct), project_event orchestrator |

### Consumer 1: Graph Projection Worker

| File | Purpose |
|------|---------|
| `worker/consumer.py` | Base consumer class: XREADGROUP lifecycle, ensure_group, graceful shutdown, error handling with PEL retry |
| `worker/projection.py` | ProjectionConsumer: deserialize events from stream, call projection logic, write to Neo4j, track prev_event per session for FOLLOWS edges |

### FastAPI Application

| File | Purpose |
|------|---------|
| `api/app.py` | Application factory with lifespan (Redis + Neo4j connection management), ORJSONResponse default |
| `api/routes/events.py` | POST /v1/events (single + validation), POST /v1/events/batch (batch with partial failure handling) |
| `api/routes/health.py` | GET /v1/health (Redis PING + Neo4j connectivity check) |
| `api/middleware.py` | Error handling (ValidationError → 422), request timing (X-Request-Time-Ms header) |
| `api/dependencies.py` | Dependency injection: get_settings, get_event_store, get_graph_store |

---

## ADR Compliance

- [x] Lua script performs dedup + dual-write atomically (ADR-0010)
- [x] global_position is Redis Stream entry ID string (ADR-0010)
- [x] MERGE-based Neo4j writes, never CREATE for existing nodes (ADR-0009)
- [x] Consumer uses XREADGROUP with XACK after success (ADR-0005)
- [x] FOLLOWS edges have session_id + delta_ms properties (ADR-0009)
- [x] CAUSED_BY edges have mechanism property (direct) (ADR-0009)
- [x] Idempotent — re-ingesting same event_id is a no-op (ADR-0004)

---

## Frozen Contracts (Phase 3+ MUST NOT modify existing signatures)

Previously frozen (Phase 1):
- `domain/models.py`, `ports/*`, `settings.py`

Newly frozen (Phase 2):
- `adapters/redis/store.py` — RedisEventStore class and method signatures
- `adapters/redis/lua/ingest.lua` — Lua script interface (KEYS/ARGV)
- `adapters/neo4j/store.py` — Neo4jGraphStore class and implemented method signatures
- `worker/consumer.py` — BaseConsumer class and lifecycle methods

Phase 3 MAY:
- Implement the NotImplementedError stubs in Neo4j store
- Add new methods to adapters
- Extend worker/consumer.py with new consumer subclasses
- Add new API routes

---

## Next Phase: Phase 3 — Graph Schema + API + Decay

### Team Composition
| Agent | Files |
|-------|-------|
| domain-architect | `domain/scoring.py`, `domain/lineage.py`, `domain/intent.py` |
| data-engineer | `adapters/neo4j/queries.py` (extend), `worker/enrichment.py` |
| api-engineer | `api/routes/context.py`, `api/routes/query.py`, `api/routes/lineage.py`, `api/routes/entities.py` |

### Prerequisites
- Docker services running
- All Phase 2 contracts frozen
- Phase 3+ methods in Neo4j store need implementation (currently NotImplementedError)
