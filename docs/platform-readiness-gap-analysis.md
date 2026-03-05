# Platform Readiness Gap Analysis — Consolidated Report

_Date: 2026-02-28_
_Branch: feat/retrieval-v2 (post Tier 1 hardening)_
_Analysts: 5-agent team (API, Data, Security, Observability, Testing)_

---

## Executive Summary

A comprehensive platform-readiness review across 5 dimensions identified **102 findings** (including 3 confirmed non-gaps). Of the **99 actionable gaps**, **19 are CRITICAL** and must be resolved before any production deployment.

| Dimension | CRITICAL | HIGH | MEDIUM | LOW | Total |
|-----------|----------|------|--------|-----|-------|
| API & Contract | 3 | 7 | 6 | 4 | 20 |
| Data & Resilience | 4 | 7 | 8 | 4 | 23 |
| Security & Auth | 4 | 7 | 6 | 4 | 21 |
| Observability & Ops | 5 | 8 | 7 | 4 | 24 |
| Testing & Quality | 3 | 5 | 4 | 1 | 13 |
| **Totals** | **19** | **34** | **31** | **17** | **101** |

*(Security dimension: 28 findings total, 3 confirmed NO GAP not counted above. Some findings overlap across dimensions.)*

### System Strengths

Before listing gaps, it's worth noting significant strengths identified:

1. **1,310 total tests** across server unit (740), server integration (87), server e2e (148), server infra (23), SDK (230), MCP (82)
2. **Lua-based atomic ingestion** with dedup + JSON.SET + XADD
3. **MERGE-based idempotent Neo4j writes** enabling safe replay
4. **PEL-based retry + dead-letter queue + XAUTOCLAIM** for consumer resilience
5. **PEL-safe stream trimming** protecting consumer groups during XTRIM
6. **Archive-before-delete** pattern preserving data beyond Redis retention
7. **Hexagonal architecture** with protocol-based ports and dependency injection
8. **All Cypher queries properly parameterized** — no injection risk
9. **Timing-safe API key comparison** via `hmac.compare_digest`
10. **Bounded query limits** enforced via `validate_traversal_bounds`

---

## Status Updates

### 2026-02-28 — SDK/MCP Security Hardening (ADR-0015 Amendment)

A 4-squad adversarial red team executed against the SDK (`engram`) and MCP server (`engram-mcp`) packages, adding **205 new adversarial tests** and **hardening 9 source files**. This partially or fully addresses the following gaps:

| Gap ID | Gap | Status | Notes |
|--------|-----|--------|-------|
| GAP-TEST-008 | Limited concurrency/race condition testing | **Partially closed** | 54 concurrency tests added (SDK/MCP). Server-side concurrency testing still needed. |
| GAP-TEST-011 | Narrow security test scope | **Partially closed** | 75 security + injection tests added (SDK/MCP). Server-side security tests still needed. |
| GAP-TEST-007 | No timeout behavior tests | **Partially closed** | SDK transport timeout, retry-after cap, sync client future timeout all tested. Server-side timeout tests still needed. |
| GAP-API-008 | Path parameters unvalidated | **Partially closed** | SDK client validates all path params (traversal, null bytes, CRLF, invisible unicode, length). Server-side validation still needed. |
| GAP-SEC-014 | API keys stored as `str` not `SecretStr` | **Partially closed** | SDK `EngramConfig.__repr__` now redacts keys. `_scrub_credentials()` strips keys from errors. Server-side `settings.py` still uses `str`. |
| GAP-OPS-010 | No sensitive field redaction in structlog | **Partially closed** | SDK errors scrub credentials and connection strings. MCP tool output scrubs file paths, stack traces, credentials. Server-side structlog redaction still needed. |

**New test counts (SDK/MCP only):**

| Package | Before | After | New |
|---------|--------|-------|-----|
| SDK (`engram`) | 91 | 230 | +139 |
| MCP (`engram-mcp`) | 16 | 82 | +66 |
| **Subtotal** | **107** | **312** | **+205** |

**Updated platform-wide test counts:**

| Layer | Tests |
|-------|-------|
| Server: unit | 740 |
| Server: integration | 87 |
| Server: e2e | 148 |
| Server: infra | 23 |
| SDK: unit + adversarial | 230 |
| MCP: unit + adversarial | 82 |
| **Total** | **1,310** |

**Source hardening applied:**
- Input validation at SDK boundary (path traversal, injection, size limits)
- Resource exhaustion caps (pagination limit, retry-after cap, future timeout)
- Credential protection (repr redaction, error scrubbing, env coercion)
- Concurrency safety (threading.Lock, asyncio.Lock across 5 files)

See [ADR-0015 Amendment: Security Hardening](/docs/adr/0015-sdk-and-integration-architecture.md#amendment-security-hardening-post-phase-2) for full details.

---

## Top 19 CRITICAL Gaps — Pre-Production Blockers

### P0-A: Data Safety & Durability

| ID | Gap | Risk | Fix Effort |
|----|-----|------|------------|
| GAP-DATA-001 | **No MAXMEMORY in Redis** — `noeviction` policy meaningless without ceiling; OOM-kill under load | Redis crash, data loss | S |
| GAP-DATA-013 | **No Redis↔Neo4j reconciliation** — no mechanism to detect or repair drift between stores | Silent data loss in graph | L |
| GAP-DATA-015 | **No backup/restore procedure** — "rebuildable from Redis" claim never tested | Disaster recovery untested | L |
| GAP-DATA-018 | **Lineage query unbounded path expansion** — `*1..10` always explores depth 10 regardless of requested depth | Neo4j CPU spikes, query timeout | S |

### P0-B: Security

| ID | Gap | Risk | Fix Effort |
|----|-----|------|------------|
| GAP-SEC-001 | **Auth disabled by default** — no startup guard when keys are unset in production | All endpoints exposed unauthenticated | S |
| GAP-SEC-012 | **Hardcoded Neo4j password** — default password committed to source control | Database accessible with public password | S |
| GAP-SEC-015 | **No TLS** — all traffic (including API keys) transmitted in cleartext | Network sniffing reveals credentials | M |
| GAP-SEC-018 | **No audit logging** — GDPR operations mixed with general logs, no tamper-evident trail | Cannot demonstrate GDPR compliance | M |

### P0-C: Observability

| ID | Gap | Risk | Fix Effort |
|----|-----|------|------------|
| GAP-OPS-001 | **Consumer lag gauge never populated** — defined but never set anywhere | Cannot detect stale graph data | S |
| GAP-OPS-011 | **No OpenTelemetry integration** — zero distributed tracing despite `trace_id` field | Cannot trace requests end-to-end | L |
| GAP-OPS-012 | **No SLI/SLO definitions** — no targets, no alerting rules, no burn rate calculations | Cannot make principled on-call decisions | M |
| GAP-OPS-021 | **Projection consumer in-memory session state** — `_session_last_event` dict limits to single instance | Cannot horizontally scale projection | M |
| GAP-OPS-023 | **No operational runbook** — zero ops documentation for incident response | High MTTR during incidents | M |

### P0-D: API & Contract

| ID | Gap | Risk | Fix Effort |
|----|-----|------|------------|
| GAP-API-006 | **Inconsistent error response shapes** — 4+ distinct error formats across endpoints | Clients cannot write reliable error handling | M |
| GAP-API-017 | **No contract/schema tests** — no snapshot tests, no Pact, no OpenAPI diff | Breaking changes undetected | M |
| GAP-API-018 | **No schema evolution strategy** — `schema_version` field exists but unused | Old events become unparseable after schema changes | L |

### P0-E: Testing

| ID | Gap | Risk | Fix Effort |
|----|-----|------|------------|
| GAP-TEST-001 | **CI doesn't run coverage** — `pytest-cov` configured but `--cov` never passed in CI | Coverage silently regresses | S |
| GAP-TEST-003 | **No load/performance tests** — no k6, locust, or latency baselines | Performance regressions undetected | M |
| GAP-TEST-009 | **No dual-store consistency verification** — never tested that Neo4j matches Redis | Silent data drift between stores | M |

---

## HIGH Gaps — Fix Within First Sprint (34 total)

### Security (7 HIGH)

| ID | Gap | Effort |
|----|-----|--------|
| GAP-SEC-002 | No OAuth2/JWT — only static API keys | L |
| GAP-SEC-003 | No key rotation mechanism | M |
| GAP-SEC-004 | No RBAC — only two-tier authorization | L |
| GAP-SEC-013 | No secrets manager integration | M |
| GAP-SEC-014 | API keys stored as `str` not `SecretStr` | S | *Partially closed — SDK config redacts keys in repr/str* |
| GAP-SEC-020 | No encryption at rest for Redis/Neo4j | M |
| GAP-SEC-022 | No vulnerability scanning in CI/CD | S |
| GAP-SEC-024 | GDPR delete does not clean Redis events | L |
| GAP-SEC-027 | API keys not hashed at rest | S |

### Data & Resilience (7 HIGH)

| ID | Gap | Effort |
|----|-----|--------|
| GAP-DATA-004 | Redis client has no connection pool config | S |
| GAP-DATA-006 | No retry logic in Redis adapter | M |
| GAP-DATA-007 | No retry logic in Neo4j adapter | M |
| GAP-DATA-008 | No circuit breaker for either store | M |
| GAP-DATA-011 | No Neo4j schema migration strategy | M |
| GAP-DATA-012 | No RediSearch index migration strategy | M |
| GAP-DATA-021 | Global stream MAXLEN defaults to 0 (uncapped) | S |
| GAP-DATA-023 | No graceful degradation when Neo4j is down | M |

### Observability (8 HIGH)

| ID | Gap | Effort |
|----|-----|--------|
| GAP-OPS-002 | No per-message processing duration metric | S |
| GAP-OPS-003 | No Redis operation metrics | M |
| GAP-OPS-007 | No liveness vs readiness probe distinction | S |
| GAP-OPS-009 | No structlog config in API process | S |
| GAP-OPS-017 | No Kubernetes manifests or Helm chart | L |
| GAP-OPS-018 | Dockerfiles missing production hardening | M |
| GAP-OPS-019 | Workers have no shutdown timeout | S |
| GAP-OPS-024 | Neo4j rebuild from Redis not implemented | M |
| GAP-OPS-026 | DLQ messages not monitored or alerted | M |
| GAP-OPS-027 | No consumer group info exported to Prometheus | M |

### API (7 HIGH)

| ID | Gap | Effort |
|----|-----|--------|
| GAP-API-001 | Endpoints missing `response_model` declarations | M |
| GAP-API-007 | No request body size limit | S |
| GAP-API-010 | User endpoints return unbounded results | M |
| GAP-API-011 | Entity endpoint returns unbounded connected events | M |
| GAP-API-013 | No idempotency key for admin POST endpoints | M |
| GAP-API-015 | No Content-Type enforcement on POST bodies | S |
| GAP-API-019 | Mixed return types across endpoints | M |
| GAP-API-020 | No common envelope for non-Atlas responses | M |

### Testing (5 HIGH)

| ID | Gap | Effort |
|----|-----|--------|
| GAP-TEST-004 | No contract/schema tests | M |
| GAP-TEST-006 | Incomplete error path coverage in workers | L |
| GAP-TEST-008 | Limited concurrency/race condition testing | M | *Partially closed — 54 SDK/MCP concurrency tests added* |
| GAP-TEST-011 | Narrow security test scope | M | *Partially closed — 75 SDK/MCP security+injection tests added* |
| GAP-TEST-002 | No coverage for integration/e2e tests in CI | S |

---

## Quick Wins — High Impact, Low Effort

These can be fixed in under a day each and address CRITICAL or HIGH severity:

| # | ID | Gap | Severity | Effort |
|---|-----|-----|----------|--------|
| 1 | GAP-SEC-001 | Add startup guard for auth keys in production | CRITICAL | S |
| 2 | GAP-SEC-012 | Remove hardcoded Neo4j default password | CRITICAL | S |
| 3 | GAP-DATA-001 | Add `maxmemory 2gb` to redis.conf | CRITICAL | S |
| 4 | GAP-DATA-018 | Fix lineage query path expansion bound | CRITICAL | S |
| 5 | GAP-OPS-001 | Wire up CONSUMER_LAG gauge in BaseConsumer | CRITICAL | S |
| 6 | GAP-TEST-001 | Add `--cov` to CI pytest command | CRITICAL | S |
| 7 | GAP-SEC-014 | Change API key fields to SecretStr | HIGH | S |
| 8 | GAP-SEC-022 | Add pip-audit to CI pipeline | HIGH | S |
| 9 | GAP-DATA-004 | Configure Redis connection pool limits | HIGH | S |
| 10 | GAP-DATA-021 | Set non-zero default for global stream MAXLEN | HIGH | S |
| 11 | GAP-OPS-002 | Add consumer message processing duration histogram | HIGH | S |
| 12 | GAP-OPS-007 | Add `/v1/health/live` and `/v1/health/ready` | HIGH | S |
| 13 | GAP-OPS-009 | Add structlog.configure() to API startup | HIGH | S |
| 14 | GAP-OPS-019 | Add shutdown timeout to worker runner | HIGH | S |
| 15 | GAP-API-007 | Add request body size limit middleware | HIGH | S |
| 16 | GAP-API-015 | Add Content-Type validation for POST bodies | HIGH | S |

---

## MEDIUM Gaps — Address in Backlog (31 total)

### Security (6)
- GAP-SEC-005: User routes have no per-resource authorization
- GAP-SEC-007: No request body size limit (overlaps GAP-API-007)
- GAP-SEC-009: Rate limiting is IP-based only
- GAP-SEC-010: In-memory rate limiter state not shared across replicas
- GAP-SEC-017: CORS production override unclear
- GAP-SEC-021: No PII classification or handling framework
- GAP-SEC-025: GDPR export may be incomplete
- GAP-SEC-028: No key expiry or revocation

### Data (8)
- GAP-DATA-002: Redis AOF fsync `everysec` — 1s data loss window
- GAP-DATA-005: Neo4j pool has no acquisition timeout
- GAP-DATA-009: Batch edge creation — large sessions may timeout
- GAP-DATA-010: Pipeline append_batch has no per-item error handling
- GAP-DATA-014: Consumer `_session_last_event` lost on restart
- GAP-DATA-016: Many short-lived Neo4j sessions per request
- GAP-DATA-019: Neighbor batch LIMIT applies globally, not per seed
- GAP-DATA-020: Entity fetch limited to 1000, non-deterministic

### Observability (7)
- GAP-OPS-004: No Neo4j connection pool metrics
- GAP-OPS-005: No consolidation cycle duration metric
- GAP-OPS-006: No event ingestion error rate metric
- GAP-OPS-008: Health check doesn't cover worker status
- GAP-OPS-010: No sensitive field redaction in structlog — *Partially closed: SDK/MCP scrub credentials from errors*
- GAP-OPS-014: No Grafana dashboard definitions
- GAP-OPS-020: API has no explicit graceful shutdown config
- GAP-OPS-022: Extraction consumer in-memory turn counts

### API (6)
- GAP-API-002: Missing OpenAPI examples
- GAP-API-003: Missing error response documentation
- GAP-API-004: No deprecation/version negotiation mechanism
- GAP-API-008: Path parameters unvalidated — *Partially closed: SDK client validates all path params*
- GAP-API-012: Admin prune details unbounded
- GAP-API-014: No Accept header handling

### Testing (4)
- GAP-TEST-005: No mutation testing
- GAP-TEST-007: No timeout behavior tests — *Partially closed: SDK transport timeout + retry-after tests added*
- GAP-TEST-010: GDPR tests don't cover cross-store cascade
- GAP-TEST-012: CI pipeline incomplete (no e2e, no caching)

---

## LOW Gaps — Track for Later (17 total)

- GAP-SEC-011: No connection-level DoS protection
- GAP-SEC-016: Missing security headers (HSTS, CSP)
- GAP-SEC-019: Auth failures logged without sufficient context
- GAP-SEC-023: Docker images unpinned
- GAP-DATA-003: Neo4j WAL not explicitly configured
- GAP-DATA-017: Worker startup partial cleanup
- GAP-DATA-022: Dedup set grows between cleanup cycles
- GAP-DATA-024: Workers have no backoff on repeated failures
- GAP-OPS-013: High-cardinality risk in HTTP metrics fallback
- GAP-OPS-015: No startup config validation log
- GAP-OPS-016: No `.env.example` or config documentation
- GAP-OPS-025: No feature flag system
- GAP-API-005: Hardcoded version in multiple places
- GAP-API-009: Intent param lacks enum validation
- GAP-API-016: Swagger UI enabled in production
- GAP-TEST-013: No API contract regression tests

---

## Cross-Cutting Themes

### 1. Operational Blindness
Consumer lag (OPS-001), no tracing (OPS-011), no SLOs (OPS-012), no runbook (OPS-023), no Redis metrics (OPS-003). The system runs but operators cannot see inside it.

### 2. Data Safety at Scale
No Redis memory ceiling (DATA-001), no reconciliation (DATA-013), no backup/restore (DATA-015), GDPR incomplete (SEC-024). The dual-store architecture is sound but its operational promises are untested.

### 3. Security Hardening for Multi-Tenant
Auth defaults to open (SEC-001), no RBAC (SEC-004), no TLS (SEC-015), no audit trail (SEC-018). Acceptable for single-tenant dev, but blocks any shared or public deployment.

### 4. API Contract Maturity
Inconsistent errors (API-006), no schema evolution (API-018), missing response models (API-001/019), no contract tests (API-017). The API works but is fragile for external consumers.

### 5. Resilience Under Failure
No retry (DATA-006/007), no circuit breaker (DATA-008), no graceful degradation (DATA-023), no shutdown timeout (OPS-019). The system assumes all dependencies are always available.

---

## Recommended Implementation Roadmap

### Phase 1: Quick Wins (1-2 days, 16 items)
All items from the Quick Wins table above. These are CRITICAL/HIGH severity with S effort.

### Phase 2: Pre-Production Blockers (1-2 weeks)
Remaining CRITICAL gaps:
- GAP-OPS-012: Define SLI/SLO targets
- GAP-OPS-023: Write operational runbook
- GAP-OPS-021: Document single-instance limitation or move state to Redis
- GAP-API-006: Standardize error response envelope
- GAP-API-017: Add schema snapshot tests
- GAP-SEC-015: TLS termination configuration
- GAP-SEC-018: Dedicated audit logger
- GAP-TEST-003: Load test baseline with k6/locust
- GAP-TEST-009: Dual-store consistency e2e test
- GAP-DATA-013: Periodic reconciliation job

### Phase 3: Production Hardening (2-4 weeks)
HIGH gaps:
- Retry + circuit breaker (DATA-006, DATA-007, DATA-008)
- Schema migration framework (DATA-011, DATA-012)
- Kubernetes manifests (OPS-017)
- Dockerfile hardening (OPS-018)
- Consumer monitoring (OPS-026, OPS-027)
- Response models + typed returns (API-001, API-019)
- Pagination for user/entity endpoints (API-010, API-011)
- Worker error path testing (TEST-006)
- Concurrency testing (TEST-008) — *SDK/MCP done; server-side remaining*
- Security test expansion (TEST-011) — *SDK/MCP done; server-side remaining*

### Phase 4: Enterprise Features (1-3 months)
- OAuth2/JWT (SEC-002)
- RBAC (SEC-004)
- Secrets manager (SEC-013)
- OpenTelemetry (OPS-011)
- Schema evolution (API-018)
- GDPR Redis cleanup (SEC-024)
- Neo4j rebuild script (OPS-024)

---

## Appendix: Individual Reports

| Report | Location | Findings |
|--------|----------|----------|
| API & Contract | `/tmp/claude/gap-analysis-api.md` | 20 gaps |
| Data & Resilience | `/tmp/claude/gap-analysis-data.md` | 23 gaps |
| Security & Auth | `/tmp/claude/gap-analysis-security.md` | 21 gaps (+ 3 confirmed non-gaps) |
| Observability & Ops | `/tmp/claude/gap-analysis-observability.md` | 27 gaps |
| Testing & Quality | `/tmp/claude/gap-analysis-testing.md` | 13 gaps |
