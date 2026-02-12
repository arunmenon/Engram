# ADR-0010: Redis as Event Store

Status: **Accepted**
Date: 2026-02-11
Amends: ADR-0001 (item 6, Phased Store Evolution), ADR-0003 (dual-store roles), ADR-0004 (event ledger implementation)
Related: ADR-0005 (projection worker), ADR-0007 (memory tiers), ADR-0008 (retention tiers)

## Context

The current architecture specifies Postgres as the immutable event ledger and source of truth (ADR-0001, ADR-0003, ADR-0004). Research into Redis capabilities for event sourcing -- specifically Redis Stack (Streams + JSON + Search) -- reveals that Redis provides superior primitives for the event ingestion and projection pipeline:

1. **Redis Streams are append-only logs** with auto-generated time-based IDs, providing the same total ordering guarantee as Postgres BIGSERIAL for single-node deployments.

2. **Consumer groups** (XREADGROUP with blocking reads, automatic position tracking, crash recovery via Pending Entry List) are a better fit for the projection worker than Postgres polling. They eliminate polling lag entirely and provide built-in restart safety.

3. **Sub-millisecond ingest latency** (10-100x faster than Postgres INSERT with WAL sync) benefits real-time agent observability use cases.

4. **Redis 8.x improvements** (2025-2026) strengthen the event sourcing story: idempotent XADD (8.6), combined pending + new reads (8.4), atomic acknowledge-and-delete (8.2), and 16x query engine performance (8.0).

However, Redis introduces trade-offs in three areas:

- **Durability**: Redis persistence (AOF) is less battle-tested than Postgres WAL for source-of-truth data. With `appendfsync everysec`, up to 1 second of data can be lost on crash. With `appendfsync always`, durability approaches Postgres but throughput drops 50-80%.

- **Long-term retention cost**: In-memory storage is 15-30x more expensive than disk-based Postgres at growth/enterprise scale. Keeping all events in Redis indefinitely is cost-prohibitive.

- **Schema enforcement**: Redis has no built-in schema validation, constraints, or foreign keys. All enforcement must be at the application layer.

These trade-offs are addressable through architectural mitigations rather than being fundamental blockers.

### Research Basis

This decision is informed by two research reports:
- [Redis Event Store Feasibility](../research/redis-event-store-feasibility.md) -- Redis Streams capabilities, production war stories, performance benchmarks, requirement-by-requirement analysis
- [Redis Architectural Impact](../research/redis-architectural-impact.md) -- ADR-by-ADR impact assessment, cost projections, operational complexity comparison

Non-goals for this decision:
- Multi-region active-active event ingestion (single-node ordering is sufficient for MVP)
- Real-time stream processing beyond projection (Kafka-style complex event processing)
- Eliminating all other persistence (Neo4j remains the semantic memory store)

## Decision

Redis Stack (Streams + JSON + Search) MUST replace Postgres as the sole event store. Redis MUST serve as both the hot and cold tier for event retention, with stream trimming and JSON document retention providing the tiered storage model.

### Core Architecture

The event store uses three Redis data structures in concert:

1. **Redis Streams** — append-only event log providing total ordering and consumer group delivery
2. **RedisJSON documents** — structured event records enabling rich secondary queries
3. **RediSearch indexes** — secondary indexes on session_id, agent_id, trace_id, event_type, and time ranges

Events are written atomically to all three structures via a Lua script that also performs deduplication.

### Data Model

**Global stream** (`events:__global__`): Receives every event. Provides total ordering (equivalent to `global_position`). Consumer groups for the projection worker read from this stream.

**Per-session streams** (`events:{session_id}`): One stream per session for efficient session-scoped reads without scanning the global stream.

**JSON documents** (`evt:{event_id}`): One document per event, indexed by RediSearch for field-based queries.

**Dedup set** (`dedup:events`): Sorted set of event_id values with TTL-based cleanup, enabling idempotent ingestion.

### Idempotent Ingestion

Ingestion MUST be idempotent. A Lua script atomically:
1. Checks the dedup sorted set for the `event_id`
2. If absent, writes to the global stream, session stream, and JSON document in a single atomic operation
3. Returns the auto-assigned stream entry ID (the new `global_position`)

Duplicates are rejected without side effects, providing semantics equivalent to Postgres `ON CONFLICT (event_id) DO NOTHING`.

### Global Position

The `global_position` concept maps to the Redis Stream entry ID on `events:__global__`:

- Format: `<milliseconds_timestamp>-<sequence_number>` (e.g., `1707644400000-0`)
- Monotonically increasing on a single node
- Encodes both ordering AND timestamp (richer than bare BIGSERIAL)
- Deterministic replay via `XRANGE events:__global__ 0 +`

The `provenance.global_position` field in API responses (ADR-0006 Atlas pattern) changes from an integer to a string containing the stream entry ID. Clients SHOULD treat this as an opaque cursor, not parse its internal format.

### Projection Worker

The projection worker (ADR-0005) MUST use Redis consumer groups instead of Postgres polling:

- `XREADGROUP GROUP projection worker-1 BLOCK 5000 STREAMS events:__global__ >` for push-based delivery
- `XACK` after successful Neo4j projection
- Pending Entry List provides automatic crash recovery
- No application-level cursor table required (consumer group tracks position)

This is a strict improvement over the Postgres polling model: zero polling lag, built-in position tracking, and automatic crash recovery.

### Querying Patterns

The RediSearch index on JSON documents supports all query patterns currently served by Postgres:

| Query | Implementation |
|-------|---------------|
| Events by session | `FT.SEARCH idx:events "@session_id:{sess-abc}"` or `XRANGE events:sess-abc - +` |
| Events by agent | `FT.SEARCH idx:events "@agent_id:{agent-1}"` |
| Events by trace | `FT.SEARCH idx:events "@trace_id:{trace-xyz}"` |
| Time range | `FT.SEARCH idx:events "@occurred_at_epoch_ms:[start end]"` or `XRANGE events:__global__ start end` |
| Composite | `FT.SEARCH idx:events "@session_id:{s} @event_type:{tool.execute}"` |
| Parent chain | Sequential `JSON.GET evt:{parent_event_id}` traversal |

### Durability Configuration

Redis MUST be configured with hybrid persistence (RDB + AOF):

- `appendonly yes` with `appendfsync everysec` as the default
- `maxmemory-policy noeviction` (never silently evict event data)
- `WAIT 1 100` after critical writes when a replica is available

The 1-second data loss window under `appendfsync everysec` is mitigated by:
1. Idempotent producers can retry after connection loss
2. Replication with WAIT provides synchronous acknowledgment when needed

Deployments with regulatory requirements for zero data loss SHOULD use `appendfsync always`, accepting reduced throughput.

### Long-Term Retention (Redis-Only Tiered Architecture)

Redis serves as both the hot and cold tier. The tiered model uses stream trimming to manage memory while retaining JSON documents for cold queries.

| Tier | Duration | Storage | Access Pattern |
|------|----------|---------|----------------|
| **Hot** | 0-7 days | Redis Streams + JSON + Search (full detail) | Real-time queries, consumer groups, stream-based replay |
| **Cold** | 7+ days | Redis JSON + Search only (stream entries trimmed) | RediSearch queries, JSON.GET lookups, replay via FT.SEARCH |

**How it works:**
1. Events land in Redis Streams (global + per-session) and JSON documents simultaneously via the Lua ingestion script
2. After the hot window (default: 7 days), a trimmer job removes old stream entries via `XTRIM` with `MINID` on the global stream and `DEL` on completed per-session streams
3. JSON documents (`evt:{event_id}`) are NOT deleted — they remain in Redis, queryable via RediSearch
4. Cold events are fully queryable via `FT.SEARCH idx:events` with the same query patterns as hot events

**Full replay** reads from a single source: `FT.SEARCH idx:events "*" SORTBY occurred_at_epoch_ms ASC` pages through all events (hot and cold) using RediSearch cursor-based pagination.

**Memory management at scale:**
- Stream trimming after 7 days reclaims ~40-60% of event memory (stream entries are redundant with JSON docs)
- JSON documents are more memory-efficient than stream entries for long-term storage
- Redis Enterprise Auto Tiering (formerly Redis on Flash) SHOULD be used at growth/enterprise scale to store cold JSON documents on SSD (10-20x cheaper than RAM)
- Community Redis deployments SHOULD monitor `redis_memory_used_bytes` and reduce the hot window or prune old JSON documents if memory pressure exceeds 80% of `maxmemory`

**Cost at scale:**

| Scale | Redis (all-in-memory, 30-day retention) | Redis Enterprise Auto Tiering (1 year) | Notes |
|-------|----------------------------------------|----------------------------------------|-------|
| Startup (1K runs/day) | ~$30/mo | ~$30/mo | Fits in RAM at startup scale |
| Growth (10K runs/day) | ~$200/mo | ~$120/mo | Auto Tiering moves cold to SSD |
| Enterprise (100K runs/day) | ~$1500/mo | ~$600/mo | Auto Tiering essential at this scale |

For community Redis deployments without Auto Tiering, configure a retention ceiling (default: 90 days). Events older than the ceiling are deleted from Redis entirely. The Neo4j graph projection retains the semantic structure of pruned events, and summary nodes (ADR-0008 Stage 3) preserve the information at a higher abstraction level.

### GDPR / Forgettable Payloads

The Forgettable Payloads pattern (ADR-0001 Core Commitment #5) adapts to Redis:

- PII payloads stored as encrypted RedisJSON documents (`pii:{pseudonym_id}`)
- Encryption keys in external KMS (not in Redis)
- Crypto-shredding: delete KMS key, then delete PII documents from Redis
- RediSearch index on `data_subject_id` enables efficient erasure lookups
- Since all event data resides in Redis, crypto-shredding is a single-store operation — no cross-system consistency concerns

After erasure, `BGREWRITEAOF` eliminates deleted PII from the AOF file.

### Schema Enforcement

Redis provides no storage-level schema enforcement. Validation MUST be performed entirely by Pydantic v2 models at the API layer (strict mode) before any Redis write. This is a defense-in-depth reduction compared to Postgres (which provided database-level constraints as a second validation layer), accepted as a trade-off for Redis's operational simplicity and performance.

### CLS Model Update

The Complementary Learning Systems mapping (ADR-0007) updates:

| Cognitive Role | Previous (Postgres) | New (Redis) |
|---------------|--------------------|----|
| Hippocampus (fast encoding, episodic traces) | Postgres event ledger | Redis Streams + JSON (hot) + Redis JSON (cold, stream-trimmed) |
| Neocortex (consolidated relational knowledge) | Neo4j | Neo4j (unchanged) |
| Systems consolidation (async replay) | Projection worker (Postgres polling) | Projection worker (Redis consumer groups) |

Redis more closely mirrors the biological hippocampus: fast encoding with eventual consolidation to long-term storage. The hot/cold tiering within Redis parallels the hippocampal model where detailed episodic traces are gradually consolidated (stream entries fade, but the JSON record persists until semantic consolidation into Neo4j is complete).

## Consequences

### Positive

- **10-100x faster event ingestion**: Sub-millisecond Redis XADD vs. single-digit-millisecond Postgres INSERT with WAL sync
- **Zero-lag projection delivery**: Consumer group push model eliminates the polling overhead and latency of the Postgres-based projection worker
- **Built-in crash recovery**: Pending Entry List tracks unacknowledged entries automatically; no application-level cursor management
- **Simpler hot-path code**: Redis commands (XADD, XREADGROUP, FT.SEARCH) are simpler than SQL with connection pools, transactions, and migration tooling
- **No migration tooling**: Schema-less Redis eliminates Alembic and migration management
- **Better CLS fidelity**: Redis as fast temporary buffer with stream trimming more closely matches the hippocampal encoding model
- **Single event store**: All events reside in Redis (no cross-system consistency concerns for archival or replay)
- **Simpler replay**: Full replay reads from one source (Redis) instead of stitching across tiers

### Negative

- **Weaker durability guarantee**: AOF `everysec` has a 1-second data loss window on crash (mitigated by idempotent producers and replication)
- **No storage-level schema enforcement**: All validation is application-layer only (mitigated by strict Pydantic models)
- **Higher memory cost at scale**: Keeping all events in Redis (even cold) requires more memory than a disk-based cold archive (mitigated by Redis Enterprise Auto Tiering for SSD-backed cold storage; community deployments use a configurable retention ceiling)
- **Retention ceiling for community Redis**: Without Auto Tiering, events older than the retention ceiling (default: 90 days) are deleted from Redis entirely, losing raw episodic detail (mitigated by Neo4j graph projection and summary nodes preserving semantic structure)
- **Idempotent ingestion requires Lua script**: More complex than `ON CONFLICT DO NOTHING` (mitigated by the script being a well-tested, static artifact)
- **Single-node ordering constraint**: Total ordering of stream IDs is only guaranteed on a single Redis node (acceptable for MVP; cluster ordering is a future concern)
- **Dual-write within Redis**: Events written to both Streams and JSON docs (atomic via Lua script, but adds internal complexity)

### Risks to Monitor

| Risk | Trigger | Mitigation |
|------|---------|------------|
| Data loss on Redis crash | Post-mortem reveals lost events in the 1s AOF window | Switch to `appendfsync always` for critical deployments; add WAIT for sync replication |
| Redis memory pressure from event accumulation | `redis_memory_used_bytes` exceeds 80% of `maxmemory` | Reduce hot window; reduce retention ceiling; enable Redis Enterprise Auto Tiering; prune old JSON docs |
| Cold JSON document volume exceeds RAM | Total JSON document count grows beyond available memory | Enable Auto Tiering (SSD-backed cold); reduce retention ceiling; accept that events beyond ceiling are lost from Redis but preserved as Neo4j graph structure |
| Malformed events enter Redis (no DB constraints) | Downstream projection failures from bad data | Add integration tests that bypass API validation to verify Lua script rejects known-bad payloads |
| RediSearch index size grows with cold documents | FT.SEARCH latency exceeds acceptable thresholds | Monitor index size; consider dropping cold documents from the search index and querying cold events by direct key lookup |
| XRANGE performance degrades on large streams | p95 XRANGE latency exceeds 10ms on global stream | Aggressive XTRIM to keep stream within bounds; rely on RediSearch for non-sequential queries |
| Cluster ordering breaks (future scaling) | Total ordering violations when moving to Redis Cluster | Design stream partitioning strategy before scaling; accept ordering within partition only |

## Alternatives Considered

### 1. Keep Postgres as the sole event store
This is the current architecture and the simplest option. Postgres provides ACID durability, schema enforcement, and mature tooling. However, the polling-based projection worker introduces latency, and Postgres is overqualified for an append-only write workload that benefits from Redis's streaming primitives. **Not selected** because Redis's consumer groups, sub-millisecond writes, and push-based delivery provide meaningful operational improvements for the event ingestion and projection pipeline.

### 2. Redis as a buffer in front of Postgres (additive)
Add Redis Streams between the API and Postgres: events land in Redis first, a drain worker persists them to Postgres, and the projection worker reads from Redis. This preserves Postgres as the source of truth while gaining Redis's ingest speed. **Not selected** because it adds a component without removing one -- the system becomes API + Redis + Postgres + Neo4j (four components). The user's goal is to use Redis as the event store, not as a buffer.

### 3. Redis with `appendfsync always` (maximum durability)
Configure Redis with `appendfsync always` to approach Postgres-level durability. This eliminates the data loss window but reduces throughput by 50-80%, negating Redis's primary performance advantage. **Not selected as default** but documented as an option for deployments with regulatory zero-data-loss requirements. Even with `always`, ingest latency (~1-5ms) is comparable to Postgres.

### 4. Redis Enterprise with Auto Tiering
Use Redis Enterprise's Auto Tiering (formerly Redis on Flash) to store hot data in RAM and cold data on SSD transparently. **Recommended for growth/enterprise deployments** where the all-in-memory approach becomes cost-prohibitive. Community Redis deployments use a retention ceiling instead. See the Long-Term Retention section for cost projections.

### 5. Redis Streams only (no JSON + Search)
Use Redis Streams as the sole data structure, without RedisJSON documents or RediSearch indexes. Query by session/agent/trace would require scanning streams. **Rejected** because the required query patterns (by session_id, agent_id, trace_id, time range, composite) cannot be efficiently served by stream range queries alone. RediSearch on JSON documents provides the secondary indexing that the query API requires.

## Impact on Existing ADRs

### ADR-0001: Traceability-First Context Graph
- **Core Commitments 1-5**: Unchanged. Append-only events, causal lineage, provenance pointers, deterministic replay, and Forgettable Payloads are all preserved with Redis implementations.
- **Complexity Constraint item 6**: Superseded. The event store is now Redis-only instead of Postgres.
- **Phased Store Evolution**: Updated. Phase 1 is Redis + Neo4j. Phase 2 adds enrichment pipeline. Phase 3 adds Redis Cluster for horizontal scaling.

### ADR-0003: Dual Store
- **Role mapping updates**: The dual-store is Redis (episodic, hot + cold) + Neo4j (semantic). The CLS model is preserved and strengthened.

### ADR-0004: Event Ledger and Idempotent Ingestion
- **Implementation changes**: `ON CONFLICT DO NOTHING` becomes a Lua script with dedup set. `global_position` (BIGSERIAL) becomes Redis Stream entry ID (string). Postgres column constraints become Pydantic-only validation.
- **Schema definition unchanged**: All fields defined in ADR-0004's amendment (8 required + 6 optional) map directly to Redis Stream fields and JSON document properties.

### ADR-0005: Projection Worker
- **Improved**: Postgres polling replaced by Redis consumer groups (XREADGROUP). This is the single largest operational improvement. Push-based delivery, built-in position tracking, and automatic crash recovery via PEL.

### ADR-0002, ADR-0006, ADR-0009: Minimal impact
- ADR-0002: `asyncpg` replaced by `redis-py` (async mode). Alembic removed.
- ADR-0006: `provenance.global_position` format changes from integer to stream ID string.
- ADR-0009: `provenance.source` changes from `"postgres"` to `"redis"`.

### ADR-0007: Memory Tiers
- Episodic memory (Tier 3) implementation changes from Postgres to Redis (all tiers). The cognitive model is preserved; the fast-encoding hippocampal analogy is strengthened.

### ADR-0008: Consolidation and Decay
- Archive tier changes from "retained in Postgres for replay" to "retained in Redis JSON documents for replay (cold tier)."
- Events beyond the retention ceiling (community Redis) are removed from Redis entirely; Neo4j graph projection and summary nodes preserve the semantic structure.
- Retention tier boundaries remain configurable. Redis handles all event storage tiers.

## Research References

- [Redis Event Store Feasibility Analysis](../research/redis-event-store-feasibility.md)
- [Redis Architectural Impact Analysis](../research/redis-architectural-impact.md)
- [Redis Architecture Design](../research/redis-architecture-design.md)
- [Redis Streams Documentation](https://redis.io/docs/latest/develop/data-types/streams/)
- [Redis 8.6 Idempotent Streams](https://redis.io/blog/announcing-redis-86-performance-improvements-streams/)
- [Building an Event Store with Redis Streams](https://oneuptime.com/blog/post/2026-01-21-redis-event-store-streams/view)
