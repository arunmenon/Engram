# Redis as Event Store: Architectural Impact Analysis Across ADRs

**Date:** 2026-02-11
**Status:** Analysis Complete
**Scope:** Impact assessment of replacing Postgres with Redis as the event ledger across ADR-0001 through ADR-0009
**Companion:** See `redis-event-store-feasibility.md` for Redis Streams technical feasibility

---

## Executive Summary

Replacing Postgres with Redis as the event store is **technically feasible but architecturally risky** for this system's core design principles. Redis Streams provide append-only, ordered, consumer-group-capable message logs that map surprisingly well to several event ledger requirements. However, the traceability-first architecture -- with its emphasis on immutable source-of-truth durability, deterministic replay, and long-term retention -- pushes against Redis's fundamental design as an in-memory store.

**Verdict: A hybrid approach (Redis hot tier + durable cold store) is more viable than full Postgres replacement.** The analysis below details the impact on each ADR.

### Impact Severity Summary

| ADR | Title | Impact Level | Primary Concern |
|-----|-------|-------------|-----------------|
| 0001 | Traceability-First | **HIGH** | Source-of-truth durability guarantees weaken |
| 0002 | Python+FastAPI Stack | **LOW** | Library swap (asyncpg -> redis-py); straightforward |
| 0003 | Dual Store | **MODERATE** | CLS model still holds; role semantics shift |
| 0004 | Event Ledger | **HIGH** | Idempotent ingestion and global_position require redesign |
| 0005 | Projection Worker | **LOW-MODERATE** | Consumer groups are a natural fit; cursor model changes |
| 0006 | Query API | **LOW** | API contract unchanged; underlying implementation shifts |
| 0007 | Memory Tiers | **MODERATE** | Redis as episodic memory is a partial fit |
| 0008 | Consolidation/Decay | **HIGH** | Long-term retention in-memory is cost-prohibitive |
| 0009 | Multi-Graph Schema | **LOW** | Mostly Neo4j-focused; minimal Redis impact |

---

## ADR-0001: Traceability-First Context Graph

### Current Assumption
> "Postgres is source of truth" -- immutable append-only event ledger with deterministic replay via `global_position` ordering.

### Impact: HIGH

**Can Redis be a reliable source of truth?**

Redis provides two persistence mechanisms:
- **RDB (snapshotting):** Point-in-time snapshots at configurable intervals. Data loss window equals the interval between snapshots (typically 1-60 seconds).
- **AOF (Append-Only File):** Write-ahead log. With `appendfsync always`, every write is synced to disk -- zero data loss but significant throughput penalty (~80% reduction). With `appendfsync everysec` (default), up to 1 second of data can be lost on crash.

**Comparison with Postgres:**
| Property | Postgres | Redis (AOF always) | Redis (AOF everysec) |
|----------|----------|-------------------|---------------------|
| Durability guarantee | Full ACID, WAL-synced | Durable but slower | ~1s data loss window |
| Crash recovery | WAL replay, proven | AOF rewrite, less battle-tested for critical data | Same |
| Replication | Synchronous replication available | Async replication only (data loss on failover) | Same |
| Data integrity validation | checksums, pg_verify_checksums | CRC64 on RDB; no built-in page-level verification | Same |

**Traceability implications:**
1. **Deterministic replay** (Core Commitment #4): Redis Streams assign auto-incremented IDs (`<millisecondsTime>-<sequenceNumber>`) that serve a similar role to `global_position`. However, Redis Stream IDs are not gap-free BIGSERIAL values -- they are timestamp-based. Replay ordering is preserved but ID semantics differ.
2. **Append-only immutability** (Core Commitment #1): Redis Streams are append-only by design -- entries cannot be modified after insertion. `XADD` only appends. `XDEL` exists but only marks entries as deleted (they remain in the stream until `XTRIM`). This aligns well with immutability requirements, but `XDEL`/`XTRIM` capabilities mean immutability is a convention, not a guarantee enforced by the engine.
3. **Source-of-truth confidence**: Postgres has decades of production track record for ACID-critical workloads. Redis's durability story, while improved, is fundamentally "bolted on" to an in-memory design. For a system whose core differentiator is traceability and provenance, this is a meaningful risk.

**Assessment:** The append-only model of Redis Streams aligns well with the immutable event ledger concept. However, the durability guarantee weakens compared to Postgres. The traceability-first principle demands that the source of truth be maximally durable -- Redis with `appendfsync always` approaches this but at a performance cost that negates Redis's primary advantage (speed).

**Recommended mitigation:** If Redis is adopted, treat it as a **hot event buffer** with async replication to a durable store (S3, object storage, or even Postgres) for the permanent source of truth. This preserves Redis's speed advantage while maintaining the durability guarantee.

---

## ADR-0002: Service Stack (Python + FastAPI)

### Current Assumption
> Stack uses `asyncpg` for Postgres connectivity.

### Impact: LOW

**Library replacement:**
| Current | Replacement | Maturity |
|---------|-------------|----------|
| `asyncpg` (Postgres) | `redis-py` (async mode, formerly `aioredis`) | Mature, well-maintained |
| Raw SQL queries | Redis commands (XADD, XREAD, XRANGE) | Simpler syntax |
| Alembic migrations | No migration framework needed (schema-less) | Reduced complexity |

`redis-py` (v5+) has native async support via `redis.asyncio`. It is actively maintained, widely used, and stable. The library maturity gap is minimal.

**Deployment model impact:**
- The multi-process model (API + projection worker + enrichment worker + re-consolidation worker) remains unchanged
- Redis connection pooling is simpler than Postgres connection pooling
- Container size decreases (no `asyncpg` + `libpq` dependencies; `redis-py` is pure Python)

**Assessment:** This is the lowest-impact ADR. The library swap is straightforward. If anything, the developer experience improves slightly because Redis commands are simpler than SQL queries for append/read patterns. The schema-less nature eliminates migration tooling (Alembic), which is both a benefit (less tooling) and a risk (no schema enforcement at the storage layer).

---

## ADR-0003: Dual Store (Postgres + Neo4j)

### Current Assumption
> "Postgres + Neo4j" dual-store architecture mapping to the Complementary Learning Systems (CLS) model: Postgres = hippocampus (rapid encoding), Neo4j = neocortex (consolidated knowledge), projection worker = systems consolidation.

### Impact: MODERATE

**Does the CLS model still hold with Redis?**

The CLS analogy maps based on functional roles, not specific technologies:
- **Hippocampus** (rapid encoding, detailed episodic traces): Redis Streams are *faster* at encoding than Postgres. Sub-millisecond append latency vs. single-digit millisecond for Postgres. The hippocampal analogy actually strengthens -- the hippocampus is a fast, temporary buffer, not a permanent archive.
- **Neocortex** (consolidated relational knowledge): Neo4j remains unchanged.
- **Systems consolidation** (async replay): Projection worker reads from Redis instead of Postgres. Consumer groups provide a natural fit.

**However, the analogy also reveals a problem:**

In neuroscience, the hippocampus is indeed temporary -- memories consolidate from hippocampus to neocortex and the hippocampal representation fades. The current architecture breaks with this model by making Postgres the *permanent* store. If we use Redis, the system more closely mirrors the biological model: Redis as temporary hippocampal buffer, with events eventually consolidated into Neo4j (neocortex) and archived to cold storage.

**The dual-store becomes a triple-store:**
```
Redis (hot hippocampus) --> Neo4j (neocortex) + Cold Archive (permanent record)
```

This is arguably a more faithful CLS implementation, but it adds operational complexity (three stores instead of two).

**Assessment:** The CLS model holds and may even be strengthened by Redis as the fast-encoding hippocampal buffer. But this requires acknowledging that the "source of truth" shifts from a single durable store (Postgres) to a distributed system (Redis hot + archive cold). The operational complexity increases unless Redis fully replaces Postgres without a cold archive -- which conflicts with ADR-0008's retention requirements.

---

## ADR-0004: Immutable Event Ledger with Idempotent Ingestion

### Current Assumption
> Idempotent ingestion via `ON CONFLICT DO NOTHING` on `event_id`. Global ordering via `global_position` (BIGSERIAL). Complete event schema with 8 required + 6 optional fields.

### Impact: HIGH

**Idempotent ingestion:**
- Postgres: `INSERT ... ON CONFLICT (event_id) DO NOTHING` -- built-in, atomic, single-statement deduplication
- Redis Streams: No built-in deduplication. `XADD` always appends. To achieve idempotency, options are:
  1. **Client-side dedup**: Check a Redis Set/Hash for `event_id` existence before `XADD`. Requires a separate data structure and is not atomic with the append (race condition window).
  2. **Lua script**: Atomic check-and-append in a Lua script. Achieves idempotency but adds complexity.
  3. **Custom ID**: Use `event_id` as the stream entry ID. Redis Streams allow custom IDs but they must be monotonically increasing within the stream -- UUIDs are not monotonically increasing.

  **Recommended approach**: Maintain a `dedup:events` Redis Set with `event_id` entries and use a Lua script for atomic check-then-XADD. Set TTL on dedup entries (e.g., 24 hours) to bound memory. This provides at-least-once delivery that is functionally equivalent to `ON CONFLICT DO NOTHING` but requires careful implementation.

**Global position (`global_position` BIGSERIAL):**
- Postgres BIGSERIAL: Gap-free, monotonically increasing, server-assigned
- Redis Stream IDs: `<millisecondsTime>-<sequenceNumber>` format. Monotonically increasing but:
  - Not gap-free (timestamps jump)
  - Time-based, not sequence-based
  - Multiple entries in the same millisecond get incrementing sequence numbers
  - If the server clock drifts backward, Redis forces the ID forward (preserving monotonicity)

  The Redis Stream ID serves the same ordering function as `global_position` for replay purposes. Deterministic replay works because `XRANGE` returns entries in ID order. However, the ID format changes from a simple integer to a compound timestamp-sequence string, which affects all code that references `global_position`.

**Event schema enforcement:**
- Postgres: Column types, NOT NULL constraints, CHECK constraints, FOREIGN KEYS enforce schema at write time
- Redis: No schema enforcement. Events are stored as field-value pairs in stream entries. Validation must happen entirely in the application layer (Pydantic models). This is already partially true (Pydantic validates before Postgres insert), but Redis removes the second layer of defense.

**Assessment:** Idempotent ingestion requires a non-trivial Lua-script-based solution. Global ordering works but with different ID semantics. Schema enforcement relies entirely on the application layer. These are solvable problems but they move complexity from the storage engine into the application code, which is the opposite direction from where reliability-critical systems should push complexity.

---

## ADR-0005: Projection Worker with Replay Support

### Current Assumption
> Worker polls Postgres by `global_position` cursor. Restart-safe, position-tracked, supports full replay.

### Impact: LOW-MODERATE

**Consumer groups are a natural fit:**

Redis Streams consumer groups provide exactly the pattern the projection worker needs:
- `XREADGROUP` blocks waiting for new entries (no polling needed)
- Consumer groups track the last-delivered ID per consumer (automatic position tracking)
- `XACK` confirms processing (enables restart safety)
- Pending Entry List (PEL) tracks unacknowledged entries for crash recovery
- `XREAD` with `0` as the starting ID enables full replay

**Comparison:**
| Feature | Postgres Polling | Redis Consumer Groups |
|---------|-----------------|----------------------|
| New event notification | Poll by global_position | XREADGROUP BLOCK (push-based) |
| Position tracking | Application-managed cursor table | Built-in per-consumer tracking |
| Restart safety | Resume from stored cursor | Resume from last ACK |
| Replay | Query from global_position = 0 | XRANGE from ID 0 |
| Multiple consumers | Multiple workers poll same table | Consumer group distributes entries |
| Backpressure | Query LIMIT clause | COUNT parameter on XREADGROUP |

Redis consumer groups are arguably a *better* fit for the projection worker pattern than Postgres polling. The push-based model eliminates polling lag. The built-in position tracking eliminates the cursor table.

**Multi-stage pipeline (ADR-0008):**
The three consolidation stages could each be separate consumer groups on the same stream:
- Stage 1 (projection): `XREADGROUP GROUP projection worker-1`
- Stage 2 (enrichment): Triggered after Stage 1 ACKs
- Stage 3 (re-consolidation): Periodic, reads by XRANGE

**Replay considerations:**
Full replay (re-projection from ID 0) works with `XRANGE 0 +`. However, if older entries have been trimmed (via `XTRIM` or `MAXLEN`), replay is only possible from the cold archive. This creates a dependency on the archive tier for replay completeness -- a significant change from the current model where Postgres contains the complete history.

**Assessment:** The projection worker actually benefits from Redis Streams. Consumer groups provide better primitives for this use case than Postgres polling. The risk is that replay becomes dependent on the archive tier if stream entries are trimmed.

---

## ADR-0006: Query API (Context Retrieval and Lineage)

### Current Assumption
> REST endpoints for event ingest, session context, subgraph query, lineage traversal. Atlas response pattern. Intent-aware retrieval.

### Impact: LOW

The Query API is largely decoupled from the event store choice because:

1. **Ingest endpoints** (`POST /v1/events`): Change from `INSERT INTO` to `XADD`. The API contract (request/response format) is unchanged.
2. **Context retrieval** (`GET /v1/context/{session_id}`): Reads from Neo4j, not directly from the event store. Unaffected.
3. **Subgraph query** (`POST /v1/query/subgraph`): Reads from Neo4j. Unaffected.
4. **Lineage traversal** (`GET /v1/nodes/{node_id}/lineage`): Reads from Neo4j. Unaffected.

The Atlas response pattern, intent-aware retrieval, edge-type weighting, and traversal bounds are all Neo4j-side concerns.

**Minor impact:** The `provenance.global_position` field in responses changes from an integer to a Redis Stream ID string (e.g., `"1707654321000-0"` instead of `12345`). This is a format change in the response payload that clients would need to accommodate.

**Assessment:** The API layer is well-isolated from the storage layer due to the port/adapter architecture. Redis adoption has minimal impact on the public API contract.

---

## ADR-0007: Cognitive Memory Tier Architecture

### Current Assumption
> Postgres = episodic memory (hippocampus). Four cognitive tiers: sensory, working, episodic, semantic.

### Impact: MODERATE

**Redis as episodic memory:**

The five properties of episodic memory (Pink et al., 2025) mapped against Redis:

| Property | Postgres Implementation | Redis Implementation | Fit? |
|----------|------------------------|---------------------|------|
| Long-term storage | Immutable append-only with BIGSERIAL | Stream with persistence (AOF) | **Partial** -- durable but memory-bound |
| Explicit reasoning | SQL queries via API | XRANGE/XREVRANGE queries | **Yes** -- queryable |
| Single-shot learning | Idempotent ON CONFLICT | Lua script dedup | **Yes** -- achievable |
| Instance-specific | UUID PK per event | Unique stream entry ID | **Yes** |
| Contextual relations | session_id, trace_id, parent_event_id FK | Stream fields (no FK enforcement) | **Partial** -- relations exist but not enforced |

**The hippocampal analogy shifts:**

As noted in ADR-0003 analysis, Redis more closely mirrors the biological hippocampus than Postgres does:
- Hippocampus: fast encoding, temporary storage, eventually consolidated to neocortex
- Redis: sub-ms writes, in-memory (temporary by nature), events consolidated to Neo4j

This is actually a *better* CLS mapping. But it requires accepting that the episodic store is temporary and the permanent record lives elsewhere (cold archive or Neo4j becoming the long-term store).

**Importance hint field:**
The `importance_hint` (SMALLINT, 1-10) maps trivially to a Redis Stream field. No schema enforcement at the storage level means the application layer must validate the range.

**Assessment:** Redis fits the hippocampal/episodic role well for the *encoding* and *short-term retention* aspects. It is a weaker fit for the *long-term storage* property of episodic memory. If the architecture accepts that episodic memory has a hot tier (Redis) and a cold tier (archive), the mapping works. This is a meaningful conceptual shift from "Postgres is the permanent episodic store" to "Redis is the fast episodic buffer with archival."

---

## ADR-0008: Memory Consolidation, Decay, and Active Forgetting

### Current Assumption
> Archive tier: "> 30 days -- removed from Neo4j entirely; retained in Postgres for replay." Postgres ledger is never pruned.

### Impact: HIGH

**This is the most problematic ADR for Redis adoption.**

**Memory cost at scale:**

Using the scale analysis from the original research (ADR-0001):

| Scale | Events/Month | Event Size | Monthly Data | Cumulative (1yr) | Redis Memory (1yr) |
|-------|-------------|------------|-------------|-------------------|-------------------|
| Startup (1K runs/day) | 750K | ~1.5 KB | ~1.1 GB | ~13 GB | ~20 GB (with overhead) |
| Growth (10K runs/day) | 7.5M | ~1.5 KB | ~11 GB | ~132 GB | ~200 GB (with overhead) |
| Enterprise (100K runs/day) | 75M | ~1.5 KB | ~112 GB | ~1.3 TB | ~2 TB (with overhead) |

Redis memory overhead is typically 30-50% above raw data size due to per-entry metadata, pointers, and internal structures.

**Cost comparison (monthly, 1 year of data retained):**

| Scale | Postgres (disk) | Redis (memory) | Cost Ratio |
|-------|----------------|---------------|------------|
| Startup | ~$20/mo (50 GB disk) | ~$150/mo (20 GB RAM) | 7.5x |
| Growth | ~$100/mo (250 GB disk) | ~$1,500/mo (200 GB RAM) | 15x |
| Enterprise | ~$500/mo (1.5 TB disk) | ~$15,000/mo (2 TB RAM) | 30x |

**The cost disparity grows super-linearly** because disk storage costs ~$0.10/GB/mo while RAM costs ~$7-10/GB/mo (cloud pricing).

**Retention tier implications:**

ADR-0008 defines four retention tiers:
| Tier | Policy | Redis Impact |
|------|--------|-------------|
| Hot (<24h) | Full detail | Redis excels here -- fast reads, all data in memory |
| Warm (24h-7d) | Low-importance edges pruned | Still in Redis; manageable |
| Cold (7-30d) | Only high-importance nodes retained | Can still be in Redis but growing |
| Archive (>30d) | "Retained in Postgres for replay" | **This tier must change** |

The archive tier explicitly relies on Postgres for long-term retention. If Postgres is removed entirely, the archive tier needs a new home:
- **Option A:** Redis with disk-based storage (Redis on Flash / Redis Enterprise with Auto Tiering) -- data moves to SSD but remains Redis-addressable
- **Option B:** S3/object storage -- cheapest long-term storage but requires a separate access layer
- **Option C:** Keep Postgres as the cold archive -- this becomes a hybrid approach, not a full replacement
- **Option D:** Parquet files on disk/S3 -- good for analytics replay but requires custom tooling

**Replay after archive:**
ADR-0008 states: "Forgetting operates on the Neo4j projection only -- the Postgres ledger is never pruned." With Redis, if entries are trimmed from the stream after archival, replay requires reading from the archive. This adds latency and complexity to the replay path.

**Assessment:** Redis is cost-prohibitive for long-term event retention at any meaningful scale. The archive tier must be handled by a different technology. This makes the "Redis replaces Postgres" narrative misleading -- in practice, Redis replaces Postgres for hot/warm events, but something else replaces Postgres for cold/archive. The system gains a component rather than losing one.

---

## ADR-0009: Multi-Graph Schema and Intent-Aware Retrieval

### Current Assumption
> Mostly Neo4j-focused: node types, edge types, intent-aware traversal, enrichment schema.

### Impact: LOW

ADR-0009 is almost entirely about the Neo4j projection schema and has minimal dependency on the event store choice.

**Minor impacts:**
1. **Provenance pointers**: The `provenance.global_position` field changes from integer to Redis Stream ID string. The `provenance.source` field would change from `"postgres"` to `"redis"` (or `"redis+archive"` for archived events).
2. **Schema migration path**: The re-projection strategy ("trigger full re-projection from Postgres events") works identically with Redis -- `XRANGE 0 +` replays the full stream. However, if older entries have been archived, re-projection requires reading from both Redis and the archive, which is more complex.
3. **Entity extraction during enrichment**: Stage 2 enrichment reads event payloads. Whether those come from Postgres rows or Redis Stream entries is an adapter-level concern.

**Assessment:** The multi-graph schema is insulated from the event store choice. Redis adoption has negligible impact on this ADR.

---

## Cross-Cutting Concerns

### Operational Complexity

| Aspect | Postgres | Redis | Assessment |
|--------|----------|-------|------------|
| Backup/restore | pg_dump, WAL archiving, PITR | RDB snapshots, AOF | Postgres is more mature |
| Monitoring | pg_stat_*, well-established tooling | INFO, MONITOR, Prometheus exporter | Comparable |
| High availability | Streaming replication, pg_auto_failover | Sentinel, Redis Cluster | Comparable |
| Data loss risk | WAL guarantees zero data loss | AOF everysec: ~1s window | Postgres is safer |
| Scaling | Vertical + read replicas | Vertical + Cluster (sharding) | Redis Cluster adds complexity |
| Schema management | Alembic migrations | None (schema-less) | Mixed -- less tooling but less safety |
| Expertise required | Widely known | Widely known | Comparable |
| Debugging data issues | SQL queries, pgAdmin | XRANGE, RedisInsight | Postgres is more flexible |

**For a small team**, the operational profile is roughly comparable for simple deployments. Redis may even be simpler initially (no migrations, simpler config). However, as data grows and the archive tier becomes necessary, the hybrid approach (Redis + archive) adds operational surface.

### What Happens at Scale?

**At 1M events (~40 days at startup scale):**
- Redis memory: ~1.5 GB (manageable, fits in a single small instance)
- Query performance: Excellent for XRANGE scans
- No archive pressure yet
- **Verdict: Redis works well**

**At 10M events (~13 months at startup, ~40 days at growth):**
- Redis memory: ~15 GB (requires a medium instance)
- Cost: ~$100-150/mo for the Redis instance alone
- Archive tier becomes relevant (events >30 days)
- **Verdict: Redis works but cost is noticeable; archival needed**

**At 100M events (~3.5 years at startup, ~13 months at growth, ~40 days at enterprise):**
- Redis memory: ~150 GB (requires a large/xlarge instance)
- Cost: ~$1,000-1,500/mo for Redis alone
- Must trim old entries aggressively; archive tier is mandatory
- XRANGE scans over large ranges become slow (O(N) with the entries returned)
- **Verdict: Redis alone is impractical; must be part of a tiered architecture**

### Hybrid Approach: Redis Hot + Cold Archive

The most viable architecture is a tiered model:

```
Events --> Redis Streams (hot: 0-7 days)
              |
              +--> Projection Worker (XREADGROUP --> Neo4j)
              |
              +--> Archiver Worker (XRANGE --> S3/Parquet or Postgres)
              |
              +--> XTRIM (remove entries older than retention window)

Replay: Redis (recent) + Archive (historical) --> Re-project into Neo4j
```

**Advantages of hybrid over pure Postgres:**
- Lower ingest latency (sub-ms Redis vs. single-digit-ms Postgres)
- Native consumer groups for projection worker
- Push-based notification instead of polling
- Simpler hot-path code (Redis commands vs. SQL)

**Disadvantages of hybrid vs. pure Postgres:**
- Three components (Redis + Archive + Neo4j) instead of two (Postgres + Neo4j)
- Replay requires stitching Redis + archive data
- Archive format must support the query patterns needed for replay
- More complex backup/disaster recovery story
- Two data stores for the event ledger (hot + cold) instead of one

---

## Recommendations

### 1. Do Not Replace Postgres Entirely

The traceability-first principle (ADR-0001) demands a maximally durable source of truth. Redis's durability story, while adequate for many use cases, introduces a data loss window that conflicts with the "immutable, deterministic replay" commitment. The cost of in-memory storage for long-term retention makes full replacement impractical beyond startup scale.

### 2. Consider Redis as an Ingest/Hot Buffer (If Speed Is a Bottleneck)

If Postgres ingest latency becomes a demonstrable bottleneck (unlikely at startup scale), add Redis as a hot buffer in front of Postgres:

```
Agent --> Redis Streams (buffer) --> Drain Worker --> Postgres (permanent) --> Projection Worker --> Neo4j
```

This preserves Postgres as the source of truth while gaining Redis's sub-ms ingest speed. The drain worker provides batched writes to Postgres for efficiency. This is additive (one more component) not substitutive.

### 3. If Adopting Redis, Accept the Hybrid Model

If the decision is to proceed with Redis, design for the hybrid model from day one:
- Redis Streams for hot events (configurable retention, default 7 days)
- Archiver worker drains events to S3/Parquet (or a lightweight append-only store)
- Replay reads from both Redis and archive
- The "source of truth" is the union of Redis + archive, not Redis alone

### 4. Re-evaluate When Postgres Polling Becomes Insufficient

The current polling model (ADR-0005) is adequate for startup and growth scale. When polling lag exceeds acceptable thresholds, consider:
1. Postgres LISTEN/NOTIFY (no new infrastructure)
2. Debezium CDC (Postgres -> Kafka/Redis Streams)
3. Redis Streams as an intermediary (Postgres -> Redis -> projection worker)

These are Phase 3 optimizations (ADR-0001) and should not drive Phase 2 architecture decisions.

---

## ADR Amendment Impact Summary

If Redis adoption proceeds, the following ADRs require amendments:

| ADR | Amendment Needed |
|-----|-----------------|
| 0001 | Redefine "source of truth" as Redis + archive union; acknowledge durability trade-off; update Phased Store Evolution |
| 0002 | Update dependency list: asyncpg -> redis-py; add archive client library |
| 0003 | Update dual-store to triple-store: Redis + Archive + Neo4j; update CLS mapping |
| 0004 | Redesign idempotent ingestion (Lua script); change global_position to Redis Stream ID; remove Postgres schema enforcement |
| 0005 | Replace polling with XREADGROUP; update replay to handle split Redis/archive source |
| 0006 | Update provenance.global_position format in Atlas responses |
| 0007 | Acknowledge Redis as temporary episodic buffer, not permanent episodic store |
| 0008 | Define archive tier technology; update "retained in Postgres for replay" to new archive target; add archiver worker |
| 0009 | Minimal -- update provenance.source field |

---

## Decision Framework

Use the following criteria to decide:

| Criterion | Favors Postgres | Favors Redis | Favors Hybrid |
|-----------|----------------|-------------|---------------|
| Durability | Strong | Weak | Medium |
| Ingest latency | Medium (~2-5ms) | Strong (<1ms) | Strong |
| Long-term storage cost | Strong | Weak | Strong |
| Operational simplicity | Strong (1 store) | Medium (1 store) | Weak (2+ stores) |
| Projection worker fit | Medium (polling) | Strong (consumer groups) | Strong |
| Replay simplicity | Strong (single source) | Weak (if trimmed) | Medium (stitched) |
| Schema enforcement | Strong (DB constraints) | Weak (app-only) | Medium |
| CLS model fidelity | Good | Better (biological) | Best |
| Small team viability | Strong | Medium | Weak |

**For a small team building an MVP, Postgres remains the simpler and safer choice.** Redis becomes attractive at scale when ingest throughput is a bottleneck, or when the projection worker's polling model is insufficient. The hybrid model is the most architecturally sound but also the most complex to operate.
