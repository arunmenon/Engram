# ADR-0001 Scale, Performance, and Operational Analysis

**Date:** 2026-02-07
**Status:** Research Complete
**Related:** ADR-0001 (Traceability-First Context Graph)

---

## Executive Summary

The dual-store architecture (Postgres event ledger + Neo4j graph projection) is sound for an MVP and early growth stages. However, it introduces operational complexity that must be planned for. This analysis quantifies storage growth, projection lag, compliance challenges, Neo4j limits, failure modes, and cost at three scale tiers: startup (1K runs/day), growth (10K runs/day), and enterprise (100K runs/day).

**Key findings:**
- Storage grows linearly and predictably; partitioning needed around 100M-500M rows
- GDPR compliance requires crypto-shredding or forgettable payloads -- "immutable" needs qualification
- Projection lag of 100ms-5s is achievable with polling; sub-100ms requires CDC
- Neo4j handles the projected graph well up to ~100M nodes with proper memory sizing
- The projection worker is the single point of failure for graph freshness
- Monthly infrastructure cost ranges from ~$100 (startup) to ~$2,500+ (enterprise)

---

## 1. Event Storage Growth

### 1.1 Event Volume Modeling

A single AI agent run (e.g., LangChain/LangGraph agent) typically produces **10-50 spans/events**:

| Event Type | Count per Run |
|---|---|
| Session start/end | 2 |
| LLM call (input + output) | 2-10 |
| Tool invocations | 2-20 |
| Retrieval/search actions | 1-5 |
| Decision/routing events | 1-5 |
| Error/retry events | 0-5 |
| **Total** | **~10-50 (median ~25)** |

### 1.2 Storage Growth Projections

Assuming median 25 events/run and ~1.5 KB average event size (UUID fields, JSONB payload with tool inputs/outputs, timestamps, metadata):

| Scale Tier | Runs/Day | Events/Day | Events/Month | Raw Storage/Month | With Indexes (~2x) |
|---|---|---|---|---|---|
| **Startup** | 1,000 | 25,000 | 750,000 | ~1.1 GB | ~2.2 GB |
| **Growth** | 10,000 | 250,000 | 7,500,000 | ~11 GB | ~22 GB |
| **Enterprise** | 100,000 | 2,500,000 | 75,000,000 | ~112 GB | ~225 GB |

**Annual totals:**

| Scale Tier | Events/Year | Raw Storage/Year | With Indexes |
|---|---|---|---|
| **Startup** | 9M | ~13 GB | ~27 GB |
| **Growth** | 91M | ~137 GB | ~275 GB |
| **Enterprise** | 912M | ~1.4 TB | ~2.7 TB |

> **Note:** JSONB storage in Postgres does not deduplicate key names, resulting in roughly 2x overhead compared to normalized column storage. The `payload_ref` field (storing tool inputs/outputs as JSONB) dominates row size. Consider storing large payloads in object storage (S3) with a reference URI to keep row size small.

### 1.3 When to Partition

PostgreSQL handles unpartitioned tables well up to roughly **100M-500M rows**. Beyond that:

- Index maintenance (CREATE INDEX) can take hours
- Vacuum operations become expensive
- Sequential scans on the full table become impractical

**Recommendation:** Implement **range partitioning by `occurred_at`** (monthly partitions) from day one. The overhead is minimal and avoids a painful migration later. This aligns naturally with the append-only event pattern. Partition pruning ensures queries scoped to time ranges touch only relevant partitions.

For the enterprise tier (75M events/month), monthly partitions of ~75M rows each are well within Postgres's comfort zone. Consider BRIN indexes on `global_position` and `occurred_at` for efficient range scans.

### 1.4 Hot/Cold Storage Strategy

The Marten event sourcing framework demonstrates a pattern of dividing event storage into "hot" and "cold" partitions, moving archived event streams to separate table partitions. This is directly applicable:

- **Hot partition:** Last 30-90 days (active sessions, recent traces)
- **Cold partition:** Older events (audit/compliance, replay only)
- **Archive tier:** Events older than retention period moved to compressed Parquet in S3

---

## 2. Append-Only vs. GDPR/Retention

### 2.1 The Core Tension

ADR-0001 states events are **immutable and append-only**. GDPR Article 17 requires the **right to erasure** of personal data. These are in direct tension.

> "Immutable" is a design aspiration, not a legal defense. The system must support data deletion for compliance.

### 2.2 Compliance Patterns

Three established patterns exist for event-sourced systems:

#### Pattern A: Crypto-Shredding (Recommended)

Encrypt PII fields in event payloads with a **per-user encryption key** stored in a separate key management system (e.g., HashiCorp Vault, AWS KMS). On erasure request, destroy the key -- rendering encrypted fields unrecoverable.

**Pros:**
- Event structure remains intact; causal lineage preserved
- Backups automatically "forget" data when key is gone
- Replay still works (non-PII fields remain readable)

**Caveats:**
- Encrypted personal data is still legally personal data under GDPR, even without the key. Some regulators may not accept this alone.
- Per-field encryption adds ~3-5% latency overhead for writes
- Key management is an additional operational dependency

#### Pattern B: Forgettable Payloads (Pseudonymization)

Store PII in a separate **mutable reference store** (e.g., a `user_pii` table in Postgres). Events reference PII via a pseudonym/opaque user ID. On erasure, delete the PII row; events retain their structure with a dangling reference.

**Pros:**
- Cleanest GDPR compliance -- data is physically deleted
- No crypto overhead on the hot path
- No key management dependency

**Caveats:**
- Requires strict discipline that no PII leaks into event payloads
- Event payloads that captured tool outputs (e.g., "User John Smith at john@email.com requested...") need scrubbing

#### Pattern C: Tombstone Events

Append a "data-erased" tombstone event, then run a compaction job that redacts PII from historical events.

**Pros:**
- Maintains event ordering semantics

**Caveats:**
- Violates the "never mutate" principle (compaction rewrites events)
- Complex to implement correctly across replicas and backups

### 2.3 Recommendation

Use **Pattern B (Forgettable Payloads) as primary** with **Pattern A (Crypto-Shredding) as defense-in-depth** for any PII that inadvertently enters event payloads:

1. Design the event schema so `payload_ref` never contains raw PII
2. Store PII in a mutable reference table keyed by `agent_id` / `session_id`
3. Encrypt any potentially-PII fields in payloads with per-user keys as a safety net
4. Add a `data_classification` field to event schema for automated compliance scanning

### 2.4 Retention Policy

Implement configurable retention with TTL-based cleanup:

| Data Class | Retention | Action |
|---|---|---|
| Active sessions | Indefinite (until archived) | Live in hot partition |
| Completed sessions | 90 days hot, 1 year cold | Move to cold partition |
| Archived events | 7 years (audit) | Compressed in S3 |
| PII reference data | Until erasure request | Delete on request |

---

## 3. Projection Lag

### 3.1 Polling vs. CDC

The architecture specifies an **async projection worker that polls Postgres events**. Two approaches exist:

| Approach | Typical Lag | Throughput | Complexity |
|---|---|---|---|
| **Polling** (current design) | 500ms - 5s | ~5K-20K events/sec | Low |
| **LISTEN/NOTIFY + Polling** | 10ms - 500ms | ~5K-20K events/sec | Medium |
| **Debezium CDC** | 10ms - 100ms | ~6K-7K events/sec* | High |

> *Debezium's single-threaded Postgres connector is limited to ~7K events/sec. Polling with batch processing can actually achieve higher throughput for bulk operations.

### 3.2 Polling Design Recommendations

For the MVP, polling is the right choice. Optimize with:

1. **Cursor-based polling:** Track `global_position` (BIGSERIAL) as the cursor. Resume from last processed position on restart.
2. **Adaptive polling interval:** Start at 100ms; back off to 1-5s when idle; snap back to 100ms on new events.
3. **Batch processing:** Fetch 100-1000 events per poll cycle. Use Neo4j's `UNWIND + MERGE` for batch writes.
4. **Checkpoint persistence:** Store cursor position in Postgres (not Neo4j) to survive Neo4j restarts.

### 3.3 What Happens When Projection Falls Behind

If the projector crashes or Neo4j goes down, the projection queue grows. Recovery scenarios:

| Scenario | Queue Depth | Recovery Time | Impact |
|---|---|---|---|
| Brief Neo4j restart (5 min) | ~5K-25K events | 1-5 seconds | Minimal; batch catches up quickly |
| Extended outage (1 hour) | ~60K-250K events | 10-60 seconds | Graph stale but Postgres queries work |
| Full replay (day 1, small) | ~25K events | < 1 second | Fast initial projection |
| Full replay (1 year, growth) | ~91M events | 1-4 hours | Major; plan for maintenance windows |

**Key insight:** Because Neo4j projection uses `MERGE` (idempotent upserts), replay is always safe. The projector can be restarted from any checkpoint without data corruption.

### 3.4 Upgrade Path to CDC

If sub-100ms lag becomes critical (e.g., real-time agent dashboards), migrate to:

1. **Postgres LISTEN/NOTIFY** as a lightweight notification layer (add to polling worker)
2. **Debezium** with Kafka for full CDC if event volumes exceed 20K/sec or multiple consumers need the event stream

---

## 4. Neo4j at Scale

### 4.1 Capacity Limits

Neo4j's theoretical limits are very high (tens of billions of nodes). Practical limits depend on hardware:

| Metric | Practical Limit | Notes |
|---|---|---|
| Nodes | 100M-1B+ | Depends on RAM for page cache |
| Relationships | 1B-10B+ | Each relationship ~34 bytes in store |
| Properties | 10B+ | JSONB-equivalent maps stored per node |
| Query latency (local traversal) | 1-5ms | For bounded depth traversals (2-3 hops) |
| Query latency (unbounded) | 100ms-10s+ | Depends on graph density and depth |

### 4.2 Memory Sizing

Neo4j uses two memory pools:

- **JVM Heap:** For query execution, transaction state. Recommended 8-16 GB (avoid >31 GB due to compressed OOPs).
- **Page Cache:** For caching graph data on disk. Rule of thumb: `store_size + expected_growth + 10%`.

| Scale Tier | Estimated Graph Size | Recommended Page Cache | Total RAM |
|---|---|---|---|
| **Startup** | < 1 GB | 2 GB | 8 GB |
| **Growth** | 5-20 GB | 25 GB | 48 GB |
| **Enterprise** | 50-200 GB | 220 GB | 256 GB |

> **Important:** If the page cache is smaller than the graph store, Neo4j falls back to disk reads. For a traceability workload with random-access traversals, this causes severe latency spikes (10-100x).

### 4.3 Graph Pruning Strategy

The Neo4j projection is **disposable and rebuildable** (per ADR-0001). This is the key architectural advantage:

1. **TTL-based pruning:** Use APOC `ttl.expire` to mark nodes older than retention window. Default cleanup runs every 60 seconds.
2. **Session archiving:** When sessions are completed and aged out, delete their subgraphs from Neo4j. Events remain in Postgres.
3. **Graph compaction:** Periodically rebuild the Neo4j projection from scratch (e.g., monthly during maintenance window). This eliminates fragmentation and orphaned data.

**Recommendation:** Keep only the last 30-90 days of graph data in Neo4j. Older lineage queries can fall back to Postgres with recursive CTEs (slower but acceptable for historical analysis).

### 4.4 Query Performance Boundaries

Per ADR-0001, all graph queries enforce depth, node count, and timeout limits. Recommended defaults:

| Parameter | Default | Max Allowed |
|---|---|---|
| `max_depth` | 3 | 10 |
| `max_nodes` | 100 | 1,000 |
| `timeout_ms` | 5,000 | 30,000 |

These bounds are critical. Without them, a single deep traversal on a dense graph can consume all heap memory and crash the server.

---

## 5. Dual-Store Failure Modes

### 5.1 Failure Mode Analysis

| Failure | Impact | Detection | Recovery |
|---|---|---|---|
| **Neo4j down** | Graph queries fail; event ingestion unaffected | Health check on `/health` | Projection catches up on restart; consider Postgres-only fallback for reads |
| **Postgres down** | All writes fail; system fully degraded | Connection pool errors | Restart Postgres; no data loss (WAL recovery) |
| **Projector crash** | Graph becomes stale; events accumulate | Monitor projection lag metric | Restart projector; resumes from cursor checkpoint |
| **Projector falls behind** | Graph queries return stale data | Lag metric exceeds threshold | Scale projector batch size; add parallel workers per session |
| **Network partition (PG<->Neo4j)** | Projector stalls; graph stale | Projector error logs + lag metric | Self-heals when network recovers |
| **Neo4j data corruption** | Graph queries return wrong data | Consistency checks (sampling) | Wipe Neo4j; full replay from Postgres |
| **Postgres WAL disk full** | Writes fail; archiving stops | Disk usage alerts | Emergency cleanup; add storage |

### 5.2 Graceful Degradation Strategy

The architecture should support **three operating modes:**

1. **Full mode:** Both stores healthy. Graph queries served from Neo4j.
2. **Degraded mode (Neo4j down):** Event ingestion continues. Graph queries return HTTP 503 or fall back to limited Postgres-based lineage queries using recursive CTEs. Expose `X-Degraded: true` header.
3. **Emergency mode (Postgres down):** No writes possible. Neo4j serves stale read-only queries. Expose clear error state.

### 5.3 Operational Monitoring

Critical metrics to track:

| Metric | Alert Threshold | Tool |
|---|---|---|
| `projection_lag_seconds` | > 30s warning, > 300s critical | Prometheus gauge |
| `projection_lag_events` | > 10,000 events behind | Prometheus gauge |
| `event_ingestion_rate` | Sudden drop or spike | Prometheus counter |
| `neo4j_page_cache_hit_ratio` | < 95% | Neo4j metrics |
| `neo4j_heap_usage_percent` | > 80% | JMX / Prometheus |
| `postgres_connection_pool_usage` | > 80% | asyncpg metrics |
| `postgres_replication_lag` | > 1s (if replicated) | pg_stat_replication |

### 5.4 Idempotency and Recovery

The `MERGE`-based Cypher projection and `ON CONFLICT DO NOTHING` Postgres ingestion make the system naturally idempotent. This means:

- The projector can safely replay events without side effects
- Event ingestion can retry without creating duplicates
- Full Neo4j rebuild is always safe (just takes time)

The main risk is **partial projection of a batch** -- if the projector processes 500 events and crashes after writing 300 to Neo4j, the remaining 200 are lost from the graph until replay. **Mitigation:** Update the cursor only after the full batch is confirmed written to Neo4j.

---

## 6. Cost Modeling

### 6.1 Infrastructure Costs (Monthly Estimates, AWS)

#### Startup Tier (1K runs/day)

| Component | Specification | Monthly Cost |
|---|---|---|
| Postgres (RDS) | db.t3.medium, 100 GB gp3 | ~$70 |
| Neo4j (AuraDB Free or self-hosted) | t3.large, 8 GB RAM | ~$65-80 |
| Projection Worker | Small container (ECS Fargate, 0.5 vCPU) | ~$15 |
| Monitoring (CloudWatch + Prometheus) | Basic | ~$20 |
| **Total** | | **~$170-185/month** |

#### Growth Tier (10K runs/day)

| Component | Specification | Monthly Cost |
|---|---|---|
| Postgres (RDS) | db.r6g.large, 500 GB gp3, Multi-AZ | ~$350 |
| Neo4j (AuraDB Pro or self-hosted) | r6g.xlarge, 32 GB RAM | ~$260-400 |
| Projection Worker | Medium container (1 vCPU, 2 GB) | ~$30 |
| Monitoring | Prometheus + Grafana | ~$50 |
| S3 (cold storage/payloads) | ~100 GB | ~$3 |
| **Total** | | **~$700-850/month** |

#### Enterprise Tier (100K runs/day)

| Component | Specification | Monthly Cost |
|---|---|---|
| Postgres (RDS) | db.r6g.2xlarge, 2 TB io2, Multi-AZ | ~$1,200 |
| Neo4j (AuraDB Business or cluster) | r6g.4xlarge, 128 GB RAM | ~$800-1,200 |
| Projection Worker(s) | 2x medium containers | ~$60 |
| Monitoring + Alerting | Full stack | ~$100 |
| S3 (cold storage/payloads) | ~1 TB | ~$25 |
| **Total** | | **~$2,200-2,600/month** |

### 6.2 Comparison: Single-Store Alternatives

| Architecture | Startup/mo | Growth/mo | Enterprise/mo | Trade-offs |
|---|---|---|---|---|
| **Postgres + Neo4j** (proposed) | ~$180 | ~$800 | ~$2,400 | Best query flexibility; operational complexity |
| **Postgres only** (with recursive CTEs) | ~$70 | ~$350 | ~$1,200 | 50% cheaper; graph queries 10-100x slower |
| **Neo4j only** (events + graph) | ~$80 | ~$400 | ~$1,200 | Loses event sourcing benefits; no immutable ledger |
| **Postgres + Apache AGE** (graph extension) | ~$70 | ~$350 | ~$1,200 | Single store; less mature graph query engine |

### 6.3 Cost Optimization Recommendations

1. **Start with Postgres-only** for MVP if budget is tight. Add Neo4j when graph query latency becomes a bottleneck.
2. **Use `payload_ref` as an S3 URI** for large tool outputs. This keeps Postgres rows small (~500 bytes instead of ~1.5 KB), cutting storage costs by ~60%.
3. **Self-host Neo4j Community Edition** on a dedicated EC2 instance for development/staging. Use AuraDB only for production.
4. **Implement TTL-based pruning** in Neo4j to keep the graph small. A 90-day window keeps Neo4j costs ~4x lower than retaining all history.

---

## 7. Risk Summary

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Projection lag exceeds SLA | Medium | Medium | Monitor lag; adaptive polling; CDC upgrade path |
| GDPR erasure request with PII in events | High | High | Implement crypto-shredding + forgettable payloads from day 1 |
| Neo4j OOM on unbounded query | Medium | High | Enforce query bounds (depth, nodes, timeout) in API layer |
| Postgres storage exhaustion | Low | Critical | Partitioning + cold storage archival + disk alerts |
| Projector crash with partial batch | Medium | Low | Cursor-after-commit pattern; MERGE idempotency |
| Neo4j extended outage | Low | Medium | Postgres fallback for degraded reads |
| Cost overrun at enterprise scale | Medium | Medium | Payload offloading to S3; Neo4j TTL pruning |

---

## 8. Recommendations

### Must-Have for MVP

1. **Range partition the event table by `occurred_at`** from day one (monthly partitions)
2. **Enforce query bounds** (max_depth, max_nodes, timeout) on all graph queries
3. **Design event schema with no raw PII** -- use pseudonymized references
4. **Implement cursor-based projection** with checkpoint stored in Postgres
5. **Add `projection_lag_seconds` metric** and alert at >30s

### Should-Have for Growth

6. **Crypto-shredding** for defense-in-depth on event payloads
7. **Payload offloading** to S3 for tool outputs >1 KB
8. **TTL-based Neo4j pruning** (90-day rolling window)
9. **Degraded-mode API** that falls back to Postgres when Neo4j is down
10. **Adaptive polling** with LISTEN/NOTIFY for low-latency projection

### Nice-to-Have for Enterprise

11. **Debezium CDC** for sub-100ms projection lag
12. **Neo4j causal clustering** for read replicas and HA
13. **Automated graph rebuild** during maintenance windows
14. **Multi-region Postgres replication** for disaster recovery

---

## References

- [Event Storage in Postgres](https://dev.to/kspeakman/event-storage-in-postgres-4dk2)
- [PostgreSQL Partitioning for Billions of Rows](https://oneuptime.com/blog/post/2026-01-25-postgresql-optimize-billion-row-tables/view)
- [Handling Billions of Rows in PostgreSQL](https://www.tigerdata.com/blog/handling-billions-of-rows-in-postgresql)
- [GDPR in Event-Driven Architecture](https://event-driven.io/en/gdpr_in_event_driven_architecture/)
- [Event Sourcing for GDPR: How to Forget Data](https://dev.to/alex_aslam/event-sourcing-for-gdpr-how-to-forget-data-without-breaking-history-4013)
- [GDPR Compliant Event Sourcing with HashiCorp Vault](https://www.hashicorp.com/en/resources/gdpr-compliant-event-sourcing-with-hashicorp-vault)
- [Crypto-Shredding Pattern](https://verraes.net/2019/05/eventsourcing-patterns-throw-away-the-key/)
- [Debezium CDC Performance](https://debezium.io/blog/2025/07/07/quick-perf-check/)
- [Debezium for CDC: Pain Points and Limitations](https://estuary.dev/blog/debezium-cdc-pain-points/)
- [Postgres CDC Developer Reference](https://blog.sequinstream.com/a-developers-reference-to-postgres-change-data-capture-cdc/)
- [Neo4j Memory Configuration](https://neo4j.com/docs/operations-manual/current/performance/memory-configuration/)
- [Neo4j TTL with APOC](https://neo4j.com/labs/apoc/4.2/graph-updates/ttl/)
- [Neo4j Disaster Recovery](https://neo4j.com/docs/operations-manual/current/clustering/disaster-recovery/)
- [Neo4j Pricing](https://neo4j.com/pricing/)
- [PostgreSQL Hosting Pricing Comparison 2025](https://www.bytebase.com/blog/postgres-hosting-options-pricing-comparison/)
- [Event Sourcing Projection Patterns](https://event-driven.io/en/projections_and_read_models_in_event_driven_architecture/)
- [Event Sourcing Deduplication Strategies](https://domaincentric.net/blog/event-sourcing-projection-patterns-deduplication-strategies)
- [LangSmith Observability](https://www.langchain.com/langsmith/observability)
- [OpenTelemetry for LLM Applications](https://opentelemetry.io/blog/2024/llm-observability/)
- [Making Event Sourcing with Marten Go Faster](https://jeremydmiller.com/2025/06/02/making-event-sourcing-with-marten-go-faster/)
