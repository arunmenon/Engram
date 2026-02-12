# Redis Event Store Feasibility Analysis

**Date:** 2026-02-11
**Status:** Research Complete
**Context:** Evaluating Redis (specifically Redis Stack with Streams + JSON + Search) as a potential replacement for Postgres as the immutable event ledger in the context-graph system.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Redis Features for Event Sourcing](#redis-features-for-event-sourcing)
3. [Requirement-by-Requirement Analysis](#requirement-by-requirement-analysis)
4. [Recent Redis Developments (2025-2026)](#recent-redis-developments-2025-2026)
5. [Production War Stories](#production-war-stories)
6. [Performance Benchmarks](#performance-benchmarks)
7. [Architecture Patterns](#architecture-patterns)
8. [Risk Assessment](#risk-assessment)
9. [Recommendation](#recommendation)

---

## Executive Summary

Redis Streams provide strong primitives for high-throughput, low-latency event ingestion with append-only semantics, consumer groups, and range queries. However, replacing Postgres as the **source-of-truth immutable event ledger** introduces significant tradeoffs around durability, secondary indexing, GDPR compliance, and data lifecycle management. Redis excels as a high-performance event bus and short-term buffer, but falls short of Postgres for long-term durable event storage in several critical areas.

**Bottom line:** Redis can enhance the architecture as a complementary component (event bus / hot cache), but fully replacing Postgres as the sole event store carries material risks to data durability and queryability that conflict with core ADR requirements.

---

## Redis Features for Event Sourcing

### Redis Streams

Redis Streams are the primary data structure for event sourcing use cases:

- **Append-only log** with auto-generated time-based IDs (e.g., `1526919030474-0`)
- **Consumer groups** (Kafka-like) for fan-out message processing with acknowledgment tracking
- **XRANGE/XREVRANGE** for range-based retrieval by stream entry ID
- **XREAD/XREADGROUP** for cursor-based polling with optional blocking
- **XADD** is O(1) append operation
- **XTRIM** with MAXLEN and MINID for lifecycle management
- **Pending Entries List (PEL)** tracks unacknowledged messages per consumer

**Strengths:**
- Natural fit for append-only event ingestion
- Built-in consumer groups eliminate need for separate message broker
- Microsecond-latency reads and writes
- Auto-generated IDs provide implicit total ordering (on single node)

**Weaknesses:**
- No native secondary indexing on field values (cannot query by session_id, agent_id, etc.)
- XRANGE only filters by entry ID ranges, not by field content
- Memory-intensive: 100K messages can consume ~1.18GB depending on payload size
- Exact MAXLEN trimming has performance penalties due to macro-node structure

### Redis JSON (RedisJSON)

Structured document storage with JSONPath queries:

- Store events as JSON documents with full path-based access
- Supports nested objects, arrays, and atomic updates on sub-paths
- Can be combined with RediSearch for indexed queries

**Relevance:** Could store event payloads as JSON documents alongside Stream entries, enabling richer querying when paired with RediSearch.

### Redis Search (RediSearch)

Secondary indexing engine for JSON and Hash data:

- Create indexes on JSON fields using JSONPath expressions
- Supports numeric range queries, text search, tag filtering
- Indexing throughput: ~132K docs/sec at p50 latency of 0.4ms
- Supports aggregations and multi-field composite queries

**Relevance:** Solves the critical gap of querying events by `session_id`, `agent_id`, `trace_id`, and time ranges. However, RediSearch indexes JSON documents and Hashes, **not Stream entries directly**. This means a dual-write pattern (Stream + JSON document) would be required, adding complexity.

### Redis Persistence

Two persistence mechanisms:

| Mechanism | Description | Data Loss Risk |
|-----------|-------------|----------------|
| **RDB** (snapshots) | Point-in-time binary snapshots at intervals | Minutes of data between snapshots |
| **AOF** (append-only file) | Logs every write operation | Configurable via fsync policy |
| **Hybrid** (RDB + AOF) | Combines both for faster restarts + durability | Best of both, recommended for production |

**AOF fsync policies:**

| Policy | Durability | Performance Impact |
|--------|------------|-------------------|
| `always` | Highest (fsync every write) | Significant (~50-80% throughput reduction) |
| `everysec` (default) | Up to 1 second of data loss | Minimal impact |
| `no` | Up to 30 seconds of data loss (OS-dependent) | None |

**Critical comparison with Postgres:** PostgreSQL's WAL (Write-Ahead Log) provides true ACID durability -- every committed transaction is guaranteed on disk before acknowledgment. Redis with `appendfsync always` approaches this but at substantial performance cost, and still lacks transaction rollback semantics.

### Redis Cluster

Horizontal scaling via hash-slot-based sharding:

- 16,384 hash slots distributed across master nodes
- Automatic failover with replica promotion
- Hash tags `{tag}` force related keys to same slot

**Limitations for event sourcing:**
- **No cross-slot transactions**: Multi-key operations across different slots fail with CROSSSLOT error
- **Total ordering lost**: Ordering is only guaranteed within a single stream on a single node. In Active-Active clusters, subsequent XREADGROUP calls may return entries with decreasing IDs
- **Hot spot risk**: Using hash tags to co-locate session data can overload a single node
- **No native range partitioning**: Unlike Postgres table partitioning by `occurred_at`, Redis has no built-in range partitioning

### Redis Stack

Bundled distribution combining Streams + JSON + Search + TimeSeries + Graph (RedisGraph was deprecated in 2023). Provides the full feature set needed for an event store without separately managing modules.

### Auto Tiering (Redis on Flash)

For cost-effective large datasets:

- Stores hot data in RAM, warm data on SSD
- Up to 70% infrastructure cost reduction vs pure DRAM
- Configurable DRAM-to-SSD ratio
- Available in Redis Enterprise only (not open-source)

---

## Requirement-by-Requirement Analysis

### 1. Append-Only Immutable Event Records

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Append-only write | XADD is inherently append-only | INSERT-only table design | **Both satisfy** |
| Immutability | No built-in prevention of XDEL | `REVOKE UPDATE, DELETE` on table; triggers | **Postgres stronger** |
| Data integrity | No checksums on entries | WAL checksums, page checksums | **Postgres stronger** |

**Assessment: PARTIAL.** Redis Streams are append-only by nature, but there is no built-in mechanism to prevent `XDEL` on entries. Application-level discipline or ACLs are required. Postgres offers stronger immutability guarantees through SQL-level permissions.

### 2. Idempotent Ingestion (ON CONFLICT DO NOTHING)

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Built-in dedup | Redis 8.6+ idempotent XADD (pid/iid-based) | `ON CONFLICT (event_id) DO NOTHING` | **Different mechanisms** |
| UUID-based dedup | Requires separate SET/check before XADD | Native with UNIQUE constraint | **Postgres simpler** |
| Atomicity | MULTI/EXEC or Lua script needed | Single atomic INSERT | **Postgres simpler** |

**Assessment: ACHIEVABLE WITH CAVEATS.** Redis 8.6 added idempotent message production, but it uses producer-ID / ingestion-ID pairs, not arbitrary UUIDs. To achieve `ON CONFLICT DO NOTHING` semantics with `event_id` as the dedup key, you would need either:
- A Lua script that checks a Set for the event_id, then conditionally XADDs
- A two-step check-and-insert pattern using MULTI/EXEC
Both add complexity and have edge cases around failures between the check and the write.

### 3. Deterministic Replay via Total Ordering (global_position BIGSERIAL)

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Auto-incrementing position | Stream entry IDs (ms-timestamp + seq) | BIGSERIAL global_position | **Both provide ordering** |
| Guaranteed monotonic | Yes, on single node | Yes, always | **Redis limited in cluster** |
| Gap-free sequence | IDs may have gaps (time-based) | BIGSERIAL is gap-free | **Postgres stronger** |
| Cross-region ordering | Not guaranteed in Active-Active | WAL-based logical replication | **Postgres stronger** |

**Assessment: GOOD ON SINGLE NODE, PROBLEMATIC IN CLUSTER.** Redis Stream IDs provide total ordering on a single node, which works well for the projection worker's cursor-based polling. However, IDs are time-based (not sequential integers), which means:
- IDs have gaps (based on timestamp jumps)
- In clustered / Active-Active deployments, ordering guarantees break down
- The projection worker would need to use Stream entry IDs as cursors instead of integer positions

### 4. GDPR Compliance (Forgettable Payloads / Crypto-Shredding)

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Separate PII store | Can use separate JSON keys | Separate table | **Both satisfy** |
| Key deletion | DEL on encryption key | DELETE on key table | **Both satisfy** |
| Audit trail | No built-in audit | `pg_audit` extension | **Postgres stronger** |
| Reliable deletion | Memory + AOF; need to ensure key is purged from all persistence layers | Single DELETE with WAL guarantee | **Postgres more reliable** |

**Assessment: ACHIEVABLE BUT RISKIER.** The crypto-shredding pattern works with Redis (store encrypted payloads, delete the key to "forget" the data). However, ensuring the encryption key is truly purged from all Redis persistence layers (RDB snapshots, AOF, replicas) requires careful operational procedures. Postgres provides stronger guarantees that a DELETE is durable and replicated.

### 5. Durable Persistence (Source of Truth)

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Default durability | In-memory, persistence optional | Disk-first, WAL-based | **Postgres far stronger** |
| Best-case durability | AOF `always` fsync | WAL with synchronous commit | **Comparable but Postgres proven** |
| Crash recovery | Replay AOF (can be slow for large datasets) | WAL replay (fast, well-tested) | **Postgres more mature** |
| Replication durability | Async by default; WAIT command for sync | Synchronous replication option | **Postgres more configurable** |
| Data on disk format | Proprietary (RDB/AOF) | Standard (heap files + WAL) | **Postgres more portable** |

**Assessment: SIGNIFICANT CONCERN.** This is the most critical gap. Redis was designed as an in-memory data structure store with optional persistence. Even with AOF `always`, Redis lacks:
- True write-ahead logging (AOF is a redo log, not a WAL)
- Page-level checksums for data corruption detection
- Proven crash recovery in the way Postgres has been battle-tested over 25+ years
- Standard data format for third-party backup/restore tools

For a system where events are the "source of truth" that can never be lost, this is a material risk.

### 6. Event Schema with Typed Fields

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Schema enforcement | None (schemaless) | Column types + constraints | **Postgres far stronger** |
| UUID validation | Application-level only | UUID type with validation | **Postgres stronger** |
| NOT NULL constraints | Application-level only | Column constraints | **Postgres stronger** |
| Foreign keys | Not supported | Full FK support | **Postgres stronger** |

**Assessment: REDIS WEAKER.** Redis has no built-in schema enforcement. All type validation, constraint checking, and referential integrity must be handled at the application layer (e.g., Pydantic models). This increases the risk of malformed events entering the store, especially from multiple producer services.

### 7. Query by session_id, agent_id, trace_id, Time Ranges

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Time range query | XRANGE by entry ID (time-based) | WHERE occurred_at BETWEEN ... | **Both support** |
| Filter by session_id | Requires RediSearch index on JSON docs | WHERE session_id = ... (B-tree index) | **Postgres simpler** |
| Filter by agent_id | Requires RediSearch index on JSON docs | WHERE agent_id = ... (B-tree index) | **Postgres simpler** |
| Composite queries | RediSearch FT.SEARCH with multiple predicates | Composite B-tree indexes | **Postgres more mature** |
| Query planning | No query planner | Sophisticated cost-based planner | **Postgres far stronger** |

**Assessment: ACHIEVABLE WITH REDIS SEARCH BUT MORE COMPLEX.** Native Redis Streams cannot query by field values -- only by entry ID ranges. To support the required query patterns, you would need:
1. Store events as both Stream entries (for ordering/consumer groups) AND JSON documents (for RediSearch indexing)
2. Create RediSearch indexes on session_id, agent_id, trace_id, and occurred_at fields
3. Accept the dual-write complexity and potential consistency issues

With Postgres, these queries work natively with standard B-tree indexes on a single table.

### 8. Cursor-Based Polling by global_position (Projection Worker)

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Cursor mechanism | XREAD with last-seen entry ID | `WHERE global_position > $cursor` | **Both work** |
| Blocking poll | XREAD BLOCK natively supported | Requires polling loop or LISTEN/NOTIFY | **Redis stronger** |
| Consumer groups | Built-in XREADGROUP with ack tracking | Application-level cursor management | **Redis stronger** |
| Exactly-once delivery | PEL + XACK provides at-least-once | Application-level with transaction | **Redis stronger** |

**Assessment: REDIS EXCELS HERE.** This is Redis Streams' strongest capability. Consumer groups with XREADGROUP, blocking reads, pending entry tracking, and acknowledgment provide a superior experience compared to Postgres polling. The projection worker would benefit significantly from these features.

### 9. Range Partitioning by occurred_at (Data Lifecycle)

| Aspect | Redis | Postgres | Verdict |
|--------|-------|----------|---------|
| Time-based partitioning | No native support; manual stream rotation | `PARTITION BY RANGE (occurred_at)` native | **Postgres far stronger** |
| Partition pruning | N/A | Automatic in query planning | **Postgres stronger** |
| Partition drop (archival) | DEL on entire stream key | `DROP PARTITION` (instant) | **Different, both work** |
| Automated lifecycle | TTL on stream key only (entire stream) | pg_partman extension for automation | **Postgres more flexible** |

**Assessment: SIGNIFICANT GAP.** Redis has no native range partitioning. To implement time-based data lifecycle:
- You would need to create separate stream keys per time bucket (e.g., `events:2026-02-11`, `events:2026-02-12`)
- Application logic must route writes to correct stream and merge reads across streams
- XTRIM with MINID can prune old entries, but does not free memory efficiently due to the radix-tree/macro-node internal structure
- Postgres native partitioning is vastly superior for this use case

---

## Recent Redis Developments (2025-2026)

### Redis 8.x Feature Timeline

| Version | Release | Relevant Features |
|---------|---------|-------------------|
| **Redis 8.0 GA** | 2025 | 30+ performance improvements, up to 87% faster commands, 2x throughput, 18% faster replication |
| **Redis 8.2** | 2025 | XACKDEL, XDELEX, improved XADD/XTRIM for multi-consumer-group coordination |
| **Redis 8.4** | 2025 | XREADGROUP extension: consume idle pending AND new messages in single command |
| **Redis 8.6** | 2025-2026 | **Idempotent message production** (at-most-once XADD with producer-ID dedup) |

### Key Improvements for Event Sourcing

1. **Idempotent XADD (8.6):** Native deduplication at the stream level using producer-ID (pid) and ingestion-ID (iid) pairs. Redis tracks recently seen iids per pid, with configurable maxsize and duration parameters. This is a significant step toward the idempotent ingestion requirement, though it uses a different dedup mechanism than UUID-based ON CONFLICT.

2. **Combined pending + new reads (8.4):** XREADGROUP can now handle recovery of pending entries and consumption of new entries in a single command, simplifying projection worker logic.

3. **Multi-consumer-group coordination (8.2):** New XACKDEL and XDELEX commands allow acknowledging and deleting entries atomically, simplifying cleanup when multiple consumer groups process the same stream.

4. **Overall performance (8.0):** Redis Query Engine (RediSearch) delivers up to 16x more query processing power, improving the viability of RediSearch-based secondary indexing.

---

## Production War Stories

### Learning.com Event Sourcing with Redis (Multi-Year Production)

Key lessons from a team that ran Redis event sourcing in production:

1. **Event data explosion:** Event sourcing produces enormous data volumes. Storing all of it in Redis (in-memory) became cost-prohibitive with thousands of concurrent users.

2. **Separation of concerns:** The team initially coupled messaging (pub/sub) with event persistence. They later separated these -- **using Postgres for event persistence and Redis only for messaging**. This reduced costs and improved queryability.

3. **Data loss with pub/sub:** Redis pub/sub is fire-and-forget; if subscribers are offline, events are lost. Streams mitigate this, but the lesson stands: Redis messaging requires careful reliability engineering.

4. **Cost at scale:** In-memory storage for event data with high write volumes became the dominant infrastructure cost. Auto Tiering (Redis on Flash) can reduce this by 70%, but it requires Redis Enterprise licensing.

### General Industry Patterns

- Most production event sourcing implementations use a **relational database (Postgres, SQL Server) for the event store** and Redis/Kafka for the messaging/streaming layer.
- Organizations that started with Redis-only event stores frequently migrated to a hybrid approach with a relational database for persistence.
- Redis excels as a **hot cache or event bus** sitting in front of a durable store.

---

## Performance Benchmarks

### Redis Streams Write Throughput

| Scenario | Throughput | Latency |
|----------|-----------|---------|
| 1 producer, 1 consumer | 1.2M msg/sec | 0.5ms p50 |
| 1 producer, 10 consumers | 3.0M msg/sec | 0.8ms p50 |
| 1 producer, 50 consumers | 7.5M msg/sec | 1.5ms p50 |
| Real-world (10K msg/sec, 2 cores) | 10K msg/sec sustained | <2ms p99.9 |

### Comparison with Postgres

| Operation | Redis Streams | Postgres |
|-----------|--------------|----------|
| Single event append | ~1 microsecond | ~0.1-1ms (with WAL fsync) |
| Batch append (1000 events) | ~100 microseconds | ~5-20ms |
| Read by position (cursor poll) | ~10 microseconds (XREAD) | ~0.5-2ms (index scan) |
| Read by field value (session_id) | N/A native; ~1ms via RediSearch | ~0.5-2ms (B-tree index) |

**Summary:** Redis is 10-100x faster for raw append and cursor-based read operations. The gap narrows significantly when Redis needs RediSearch for field-based queries, and when Redis is configured with `appendfsync always` for durability (which can reduce throughput by 50-80%).

---

## Architecture Patterns

### Pattern A: Redis as Sole Event Store (Full Replacement)

```
Agent -> API -> Redis Stream (XADD) + Redis JSON (JSON.SET)
                     |                        |
              Consumer Group              RediSearch Index
                     |                        |
              Projection Worker          Query API (FT.SEARCH)
                     |
                   Neo4j
```

**Pros:** Single data store, lowest latency, simplest infrastructure
**Cons:** Durability risk, operational complexity for lifecycle management, cost at scale, no schema enforcement

### Pattern B: Redis as Event Bus + Postgres Persistence (Hybrid)

```
Agent -> API -> Redis Stream (XADD) -----> Postgres (INSERT)
                     |                          |
              Consumer Group              B-tree Indexes
                     |                          |
              Projection Worker          Query API (SQL)
                     |
                   Neo4j
```

**Pros:** Best of both worlds -- Redis speed for ingestion/streaming, Postgres durability for persistence
**Cons:** Dual-write complexity, must handle Redis-to-Postgres sync failures, more infrastructure

### Pattern C: Redis as Hot Cache / Projection Layer

```
Agent -> API -> Postgres (INSERT, source of truth)
                     |
              LISTEN/NOTIFY or polling
                     |
              Redis Stream (short-term buffer)
                     |
              Consumer Group -> Projection Worker -> Neo4j
                     |
              Redis JSON + RediSearch (hot query cache, TTL-based)
```

**Pros:** Postgres remains source of truth, Redis accelerates the projection pipeline and recent-event queries
**Cons:** Added infrastructure, cache invalidation complexity

---

## Risk Assessment

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Data loss on crash** (AOF everysec = up to 1s of events lost) | Events are source of truth; any loss corrupts lineage | Use `appendfsync always` (heavy perf cost) or accept Postgres as backup |
| **No schema enforcement** | Malformed events enter store, corrupt downstream projections | Strict application-layer validation (Pydantic), but no database-level safety net |
| **Memory cost at scale** | Event stores grow unbounded; in-memory cost becomes prohibitive | Auto Tiering (Enterprise only), or aggressive trimming (loses immutability) |
| **Cluster ordering loss** | Total ordering breaks in multi-node/Active-Active setups | Stay single-node (limits scalability) or accept weaker ordering |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Dual-write complexity** (Stream + JSON for queryability) | Consistency issues if one write succeeds and other fails | Lua scripts or MULTI/EXEC for atomicity |
| **No native range partitioning** | Data lifecycle management requires application-level stream rotation | Custom stream-per-timewindow pattern |
| **RediSearch not indexing Streams directly** | Must maintain separate JSON documents alongside Stream entries | Accept the operational overhead |
| **Operational maturity** | Redis as event store is less battle-tested than Postgres | Invest in monitoring, backup procedures, and recovery testing |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Consumer group complexity** | Learning curve for XREADGROUP/XACK patterns | Well-documented; libraries exist |
| **Redis version dependency** | Idempotent XADD requires Redis 8.6+ | Pin version; feature is stable |

---

## Recommendation

### For the Context-Graph Project Specifically

Given the ADR requirements -- particularly the emphasis on **traceability**, **immutable events as source of truth**, **GDPR compliance**, and **data lifecycle management** -- the recommendation is:

**Do NOT replace Postgres with Redis as the sole event store.**

Instead, consider **Pattern B or C** where Redis enhances the architecture:

1. **Keep Postgres as the immutable event ledger** (source of truth). It provides ACID durability, schema enforcement, secondary indexing, range partitioning, and 25+ years of proven crash recovery.

2. **Add Redis Streams as the projection pipeline.** Replace the current "async worker polls Postgres" pattern with:
   - Postgres INSERT triggers a lightweight notification
   - Redis Stream acts as the event bus between Postgres and the projection worker
   - Consumer groups provide reliable, scalable message delivery to the Neo4j projector
   - Blocking XREAD eliminates polling overhead

3. **Optionally add Redis JSON + RediSearch as a hot cache** for recent event queries, with TTL-based expiry to manage memory.

### If Redis-Only is Strongly Desired

If there is a strong preference for Redis-only (e.g., to reduce infrastructure complexity), the minimum requirements would be:

- Redis Enterprise with Auto Tiering (for cost-effective storage at scale)
- `appendfsync always` for durability (accept the throughput reduction)
- Redis Stack (Streams + JSON + Search) for full queryability
- Single-node deployment or carefully designed stream partitioning for ordering guarantees
- Strict Pydantic validation at the API layer to compensate for lack of schema enforcement
- Custom stream rotation for data lifecycle management
- Regular RDB backup export to object storage as a safety net
- Acceptance that durability guarantees are weaker than Postgres

### Summary Scorecard

| Requirement | Redis Alone | Redis + Postgres | Postgres Alone |
|-------------|-------------|-----------------|----------------|
| Append-only immutable events | Partial | Full | Full |
| Idempotent ingestion | Achievable (complex) | Full | Full |
| Total ordering / replay | Good (single node) | Full | Full |
| GDPR / crypto-shredding | Achievable (risky) | Full | Full |
| Durable persistence | Weak-to-Moderate | Full | Full |
| Schema enforcement | None (app-level) | Full | Full |
| Query by session/agent/trace | Achievable (RediSearch) | Full | Full |
| Cursor-based polling | Excellent | Excellent | Good |
| Range partitioning | Manual | Full | Full |
| Write throughput | Excellent | Excellent | Good |
| Operational maturity | Moderate | High | High |

---

## Sources

- [Redis Streams Documentation](https://redis.io/docs/latest/develop/data-types/streams/)
- [Redis Persistence Documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [Redis 8 GA Announcement](https://redis.io/blog/redis-8-ga/)
- [Redis 8.6 Idempotent Streams](https://redis.io/blog/announcing-redis-86-performance-improvements-streams/)
- [Redis Cluster Specification](https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/)
- [Redis Auto Tiering](https://redis.io/auto-tiering/)
- [RediSearch JSON Indexing](https://redis.io/docs/latest/develop/data-types/json/indexing_json/)
- [Building an Event Store with Redis Streams (2026)](https://oneuptime.com/blog/post/2026-01-21-redis-event-store-streams/view)
- [Redis Streams Event Sourcing Guide (2026)](https://oneuptime.com/blog/post/2026-01-25-redis-streams-event-sourcing/view)
- [A Year with Redis Event Sourcing - Lessons Learned](https://medium.com/lcom-techblog/a-year-with-redis-event-sourcing-lessons-learned-6736068e17cc)
- [Redis as Event Store for Microservices](https://redis.io/blog/use-redis-event-store-communication-microservices/)
- [Redis Streams and the Unified Log](https://brandur.org/redis-streams)
- [Redis ACID Transactions](https://redis.io/glossary/acid-transactions/)
- [GDPR in Event-Driven Systems](https://event-driven.io/en/gdpr_in_event_driven_architecture/)
- [Redis Streams vs Kafka](https://mattwestcott.org/blog/redis-streams-vs-kafka)
- [Redis Streams Memory Management](https://medium.com/@yudhasubki/designing-systems-for-efficiency-redis-streams-memory-management-strategies-36e2865f928d)
