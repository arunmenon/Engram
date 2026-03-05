# Engram Architecture Review — Consolidated Report

**Date**: 2026-02-22
**Scope**: Full codebase (`src/context_graph/`), 50 source files, 34 test files, 13 ADRs
**Reviewers**: 8 specialized agents covering ADR compliance, hexagonal architecture, data store design, API patterns, worker concurrency, security & resilience, performance & scalability, and test coverage

---

## Executive Summary

The Engram codebase demonstrates **strong domain modeling** and **excellent ADR compliance** (10/13 fully compliant, 3 partial with acknowledged deferrals). The domain layer is pure with zero framework imports, and the event schema, graph schema, and intent system all match their ADR specifications exactly (8/8 node types, 16/16 edge types, 8/8 intent types, all frozen contracts preserved).

However, the review uncovered **systemic architectural gaps** in three areas:

1. **Security**: Zero authentication/authorization on all endpoints including GDPR delete/export (CRITICAL)
2. **Scalability**: Unbounded queries, missing indexes, N+1 patterns, and a full-stream scan in the extraction worker (CRITICAL)
3. **Hexagonal purity**: Routes and 3 of 4 workers bypass the port abstraction to access adapter internals directly (HIGH)

**Findings summary**: 7 CRITICAL, 15 HIGH, 24 MEDIUM, 21 LOW across all 8 review dimensions.

---

## Findings by Severity

### CRITICAL (7)

| # | Review | Finding | File(s) | Impact |
|---|--------|---------|---------|--------|
| C1 | Security | **No authentication or authorization on ANY endpoint** — all 18 routes are publicly accessible, including GDPR delete/export and admin operations | `api/` (all routes) | Anyone can delete user data, trigger reconsolidation, prune the graph, or export PII |
| C2 | Security | **GDPR DELETE without auth** — `DELETE /v1/users/{user_id}` performs cascade erasure with no identity verification | `api/routes/users.py:124` | Arbitrary user data deletion by enumerating user_ids |
| C3 | Security | **GDPR EXPORT without auth** — `GET /v1/users/{user_id}/data-export` exposes all stored PII without auth | `api/routes/users.py:109` | Full PII exposure (profile, preferences, skills, patterns) |
| C4 | Workers | **Consumer 3 enrichment writes silently fail** — `execute_write(lambda tx: tx.run(...))` creates a coroutine that is never awaited. All keyword/importance writes are no-ops | `worker/enrichment.py:89-99` | Enrichment data is permanently lost; nodes have no keywords or importance scores |
| C5 | Workers/Perf | **Consumer 2 full stream scan** — `XRANGE min="-" max="+"` on the global stream loads ALL entries into memory to find events for a single session | `worker/extraction.py:144` | OOM on production streams with 100K+ entries |
| C6 | Perf | **Admin prune loads all events** — `MATCH (e:Event)` with no LIMIT fetches every node in the graph | `api/routes/admin.py:232` | OOM or timeout on graphs with millions of events |
| C7 | Security | **Admin endpoints unprotected** — `POST /v1/admin/reconsolidate` and `POST /v1/admin/prune` can be invoked by anyone; prune with `dry_run=false` permanently deletes data | `api/routes/admin.py:83,211` | Unauthorized data destruction |

### HIGH (15)

| # | Review | Finding | File(s) |
|---|--------|---------|---------|
| H1 | Hex | **All 8 route files import concrete adapter types** — `Annotated[Neo4jGraphStore, ...]` instead of `Annotated[GraphStore, ...]`; defeats port abstraction | All route files |
| H2 | Hex | **Routes access private adapter attributes** (`_driver`, `_client`, `_database`) — 7 instances across health.py, admin.py, users.py | `api/routes/health.py`, `admin.py`, `users.py` |
| H3 | Hex | **3 of 4 workers bypass GraphStore port** — enrichment, consolidation, and extraction take raw `AsyncDriver` and import adapter modules directly | `worker/enrichment.py`, `consolidation.py`, `extraction.py` |
| H4 | Workers | **No XCLAIM for orphaned PEL messages** — if a consumer crashes, its pending messages are never reassigned to another instance | `worker/consumer.py` |
| H5 | Workers | **No retry limit / dead-letter queue** — a permanently failing message blocks PEL drain on every restart forever | `worker/consumer.py:126-131` |
| H6 | Workers | **Stream trimming races other consumers** — Consumer 4's `trim_stream` removes entries without verifying all groups have processed them | `worker/consolidation.py:308-318` |
| H7 | Security | **Cypher string interpolation** — `_MERGE_DERIVED_FROM % source_id_field` injects field names via Python `%` formatting (currently safe, structurally unsafe) | `adapters/neo4j/user_queries.py:122` |
| H8 | Security | **No rate limiting** on any endpoint | `api/` (all routes) |
| H9 | Security | **Hardcoded credentials** — `password: str = "engram-dev-password"` in settings and docker-compose | `settings.py:67`, `docker-compose.yml:31` |
| H10 | Security | **No Neo4j query timeouts** — `QuerySettings.default_timeout_ms` is defined but never passed to Neo4j session/transaction config | `adapters/neo4j/store.py` |
| H11 | Perf | **Missing Neo4j index on Event.session_id** — multiple critical queries filter on `session_id` without an index, causing full label scans | `docker/neo4j/constraints.cypher` |
| H12 | Perf | **N+1 in subgraph neighbor traversal** — separate Neo4j session + query per seed node (10 seeds = 10+ roundtrips) | `adapters/neo4j/store.py:470-490` |
| H13 | Perf | **Unbounded GET_EVENT_NEIGHBORS** — no LIMIT on neighbor results; a hub node could return thousands | `adapters/neo4j/queries.py:244-252` |
| H14 | Perf | **Redis append_batch is sequential** — 1000 events = 1000 sequential EVALSHA roundtrips instead of pipeline | `adapters/redis/store.py:181-187` |
| H15 | API | **Pagination never implemented** — cursor/has_more always empty; large result sets cannot be paged | `adapters/neo4j/store.py` (get_context, get_lineage, get_subgraph) |

### MEDIUM (24)

| # | Review | Finding |
|---|--------|---------|
| M1 | API | `timeout_ms` modeled but never enforced in Neo4j queries |
| M2 | API | Entities endpoint does not use Atlas response format (violates ADR-0006) |
| M3 | API | `max_depth` accepted but ignored in context endpoint |
| M4 | API | Seed strategy computed but never used in subgraph query |
| M5 | API | Inconsistent 404 handling (some endpoints return 404, others return empty 200) |
| M6 | API | Users/Admin routes break store encapsulation via private attributes |
| M7 | API | DELETE /v1/users returns 200 for non-existent users |
| M8 | Hex | DI functions return concrete types instead of protocol types |
| M9 | Workers | Consumer 1 `_session_last_event` unbounded memory growth |
| M10 | Workers | Consumer 1 loses FOLLOWS edge state on restart |
| M11 | Workers | Consumer 2 unbounded interest write loop (O(interests * events) individual writes) |
| M12 | Workers | Consumer 2 in-memory turn counts lost on restart |
| M13 | Workers | Consumer 4 double-consolidates sessions in same cycle |
| M14 | Workers | No SIGTERM/SIGINT signal handling for graceful shutdown |
| M15 | Workers | Consumer 3 no batch processing (ADR-0013 specifies per-event-batch) |
| M16 | Security | CORS wildcards on methods/headers (`allow_methods=["*"]`, `allow_headers=["*"]`) |
| M17 | Security | No request body size limits on event ingestion |
| M18 | Security | Error responses leak exception class names |
| M19 | Security | No circuit breaker pattern; slow Neo4j cascades to all requests |
| M20 | Security | Swallowed exceptions without traceback in admin/health routes |
| M21 | Security | No retry with backoff in API routes |
| M22 | Security | Lifespan shutdown has no try/finally (store cleanup may skip) |
| M23 | Perf | Session-per-operation in Neo4j (each operation creates/destroys a session) |
| M24 | Perf | Centrality recomputation scans all Event nodes (O(N * avg_degree)) |

### LOW (21)

| # | Review | Finding |
|---|--------|---------|
| L1 | Hex | `domain/consolidation.py` TYPE_CHECKING import from settings |
| L2 | API | User endpoints don't use Atlas format (design choice) |
| L3 | API | Subgraph traversal is single-hop only despite max_depth param |
| L4 | API | No request ID middleware for trace correlation |
| L5 | API | Limited OpenAPI response model documentation |
| L6 | Workers | Consumer 4 ACKs all events but only acts on triggers |
| L7 | Workers | Consumer 1 bypasses EventStore port for JSON.GET |
| L8 | Workers | No health check/heartbeat for consumers |
| L9 | Security | PII (user_id) in structured logs |
| L10 | Security | Raw `request.json()` bypasses FastAPI Pydantic validation |
| L11 | Security | Intent query param has no enum validation (500 instead of 422) |
| L12 | Security | User path parameters have no format validation |
| L13 | Security | Docker ports expose RedisInsight/Neo4j Browser externally |
| L14 | Security | Batch non-atomicity (partial success without indication) |
| L15 | Security | No dead letter queue for consumers |
| L16 | Perf | Memory leak in Consumer 2 `_session_turn_counts` |
| L17 | Perf | BaseHTTPMiddleware performance overhead |
| L18 | Perf | Redundant consolidation in forgetting step |
| L19 | Perf | Redis connection pool not explicitly bounded |
| L20 | Datastore | Lua `string.gsub` for JSON field patching in Redis |
| L21 | Datastore | Session streams have no TTL |

---

## Review Dimension Summaries

### 1. ADR Compliance (10 COMPLIANT, 3 PARTIAL, 0 GAP)

All 13 ADRs were verified against the implementation. Key findings:

- **All enums complete**: 8/8 node types, 16/16 edge types, 8/8 intent types
- **All frozen contracts preserved**: Phase 1 (models, ports, settings) and Phase 2 (adapters) interfaces unchanged
- **Event schema exact match**: All 14 fields (8 required + 6 optional) per ADR-0004
- **Atlas response pattern compliant**: Provenance, scores, retrieval_reason, meta with inferred_intents/seed_nodes/capacity
- **3 PARTIAL items** (all acknowledged deferrals):
  - ADR-0001: Forgettable Payloads pattern not yet implemented
  - ADR-0010: Redis `noeviction` policy requires infrastructure verification
  - ADR-0013: LLM client and NLI entailment are documented TODOs

### 2. Hexagonal Architecture

The domain layer is exceptionally clean — 10/11 domain files have zero framework imports. All 4 ports use `typing.Protocol` correctly and all adapter methods match port signatures.

However, **the port surface area is too narrow**. Later phases added operations (maintenance, user queries, enrichment) that don't fit the existing ports. Rather than extending ports or creating new ones, these were implemented as separate adapter modules accessed directly from routes and workers. This creates a "port bypass" pattern where 8 of 9 route files and 3 of 4 workers import concrete adapters.

**Recommendation**: Create additional ports (`MaintenancePort`, `UserQueryPort`, `HealthCheckPort`) to cover the operations currently accessed through adapter imports.

### 3. Data Store Design

**Redis**: Lua-script-based idempotent ingestion is well-designed. RediSearch indexes are properly defined. Tag escaping is correctly handled. One concern: `string.gsub` JSON patching in Lua is fragile.

**Neo4j**: All writes use MERGE (idempotent). All Cypher queries use parameterized patterns (no injection). Constraints file correctly limits to uniqueness constraints for Community Edition. **Critical gap**: No index on `Event.session_id` despite being used in most queries.

### 4. API & Query Patterns

The API follows REST conventions with clean DI and consistent error handling. The Atlas response pattern is well-implemented for the 3 graph query endpoints. Intent classification with edge weight boosting works correctly.

**Key gaps**: Pagination is defined in the response model but never actually implemented. `timeout_ms` and `max_depth` parameters are accepted but not enforced. Seed strategy selection is computed but never applied to subgraph queries.

### 5. Worker & Concurrency

The BaseConsumer implements a solid XREADGROUP lifecycle with PEL recovery. Consumer 1 (projection) is the gold standard — it correctly uses the GraphStore port with MERGE-based idempotent writes.

**Critical issues**: Consumer 3's enrichment writes silently fail (non-async lambda in `execute_write`). Consumer 2 scans the entire global stream instead of using indexed lookups. No XCLAIM mechanism for orphaned messages, no dead-letter queue, no retry limits.

**Cross-consumer race**: Consumers 1 and 3 process the same event concurrently. If Consumer 3's `UPDATE` executes before Consumer 1's `MERGE`, the node doesn't exist yet and the update is silently lost.

### 6. Security & Resilience

**OWASP assessment**: FAIL on A01 (Broken Access Control), A05 (Security Misconfiguration), A07 (Auth Failures). PASS on A03 (Injection), A08 (Data Integrity), A10 (SSRF).

The most critical finding is the complete absence of authentication/authorization. All endpoints including GDPR delete/export and admin operations are publicly accessible. This must be addressed before any deployment.

### 7. Performance & Scalability

**28 findings** across N+1 queries, unbounded collections, missing indexes, and missing batching. The two most impactful:

1. **Missing `Event.session_id` index** — Most queries filter on `session_id` but no index exists, causing full label scans on every request.
2. **Sequential Redis batch append** — 1000 events = 1000 roundtrips instead of a single pipeline operation.

Scoring is done in Python (all events loaded, scored, then truncated) rather than being pushed to Cypher with ORDER BY + LIMIT.

### 8. Test Coverage & Quality

**497 total tests** (420 unit + 77 integration). Domain layer coverage is excellent — all 10 domain modules have comprehensive tests with edge cases and boundary values.

**Biggest gap**: All 4 consumer workers have minimal or zero tests. BaseConsumer (XREADGROUP loop, PEL recovery, group creation) has zero tests. ProjectionConsumer and ConsolidationConsumer have zero tests. The enrichment worker test only covers `extract_keywords` (8 tests), not the full consumer lifecycle.

Test isolation is strong — all unit tests use in-memory stubs with no external dependencies. Integration tests properly clean up with `MATCH (n) DETACH DELETE n`.

---

## Prioritized Remediation Plan

### Phase A: Critical Fixes (Must Fix)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| A1 | Add auth middleware (API key + admin key) to all endpoints | M | Blocks C1, C2, C3, C7 |
| A2 | Fix Consumer 3 `execute_write` — replace lambda with async function | S | Unblocks C4 |
| A3 | Fix Consumer 2 — use `FT.SEARCH` or per-session stream instead of full `XRANGE` | S | Fixes C5 |
| A4 | Add LIMIT/pagination to admin prune query | S | Fixes C6 |

### Phase B: High-Priority Fixes

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| B1 | Add `Event.session_id` Neo4j index | S | Fixes H11 (biggest perf win) |
| B2 | Change route `Annotated[...]` aliases to use protocol types | S | Fixes H1, M8 |
| B3 | Create `MaintenancePort` and `UserQueryPort` to cover bypassed operations | M | Fixes H2, H3, M6 |
| B4 | Add XCLAIM mechanism for orphaned PEL messages | M | Fixes H4 |
| B5 | Add retry limit + dead-letter queue to BaseConsumer | M | Fixes H5 |
| B6 | Guard stream trimming with PEL checks across all consumer groups | S | Fixes H6 |
| B7 | Replace `%` string interpolation in `_MERGE_DERIVED_FROM` with parameterized Cypher | S | Fixes H7 |
| B8 | Pass `timeout_ms` to Neo4j session/transaction config | S | Fixes H10, M1 |
| B9 | Pipeline Redis batch appends | M | Fixes H14 |
| B10 | Batch subgraph seed lookup + neighbor traversal into single Cypher query | M | Fixes H12, H13 |
| B11 | Implement cursor-based pagination for Atlas endpoints | L | Fixes H15 |

### Phase C: Medium-Priority Improvements

| # | Fix | Effort |
|---|-----|--------|
| C1 | Add LRU eviction to worker in-memory dicts | S |
| C2 | Add SIGTERM/SIGINT signal handlers to BaseConsumer | S |
| C3 | Implement seed strategy selection in subgraph query | M |
| C4 | Add rate limiting middleware | S |
| C5 | Move hardcoded credentials to required env vars with `SecretStr` | S |
| C6 | Add worker unit tests (BaseConsumer, ProjectionConsumer, ConsolidationConsumer) | L |
| C7 | Extract shared integration test fixtures to `tests/integration/conftest.py` | S |

---

## Architecture Strengths

1. **Domain purity**: 10/11 domain modules have zero framework imports — exceptional for a Python codebase
2. **Immutable event ledger**: Append-only with Lua-script dedup; genuine CQRS with Redis as source of truth
3. **Comprehensive type system**: 8 node types, 16 edge types, 8 intent types — all with Pydantic v2 strict mode
4. **Intent-weighted traversal**: Edge weights dynamically adjusted based on query intent classification
5. **4-factor Ebbinghaus decay**: Principled memory scoring with recency, importance, relevance, and user affinity
6. **Idempotent graph writes**: All Neo4j operations use MERGE; safe for retries and replay
7. **ADR-driven design**: Every architectural decision documented and traceable to implementation
8. **Strong domain test coverage**: 420 unit tests with excellent edge case and boundary coverage

---

## OWASP Top 10 Summary

| Category | Status |
|----------|--------|
| A01: Broken Access Control | **FAIL** — No auth on any endpoint |
| A02: Cryptographic Failures | **PARTIAL** — Cleartext credentials in settings |
| A03: Injection | **PASS** — All queries parameterized |
| A04: Insecure Design | **PARTIAL** — Good separation, no threat model |
| A05: Security Misconfiguration | **FAIL** — Default creds, exposed mgmt ports, CORS wildcards |
| A06: Vulnerable Components | **N/A** — No dependency scan configured |
| A07: Auth Failures | **FAIL** — No auth mechanism exists |
| A08: Software/Data Integrity | **PASS** — Immutable event ledger |
| A09: Logging & Monitoring | **PARTIAL** — Good structlog, some swallowed exceptions |
| A10: SSRF | **PASS** — No outbound calls from user input |

---

*Generated from 8 independent review agents. Full per-dimension reports available in review archives.*
