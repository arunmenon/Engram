# Redis-Based Event Store: Architecture Design

**Date:** 2026-02-11
**Status:** Design Complete
**Author:** redis-architect
**Inputs:** redis-event-store-feasibility.md, redis-architectural-impact.md, ADR-0001 through ADR-0009

---

## Design Philosophy

The user wants Redis. This design optimizes for Redis's strengths -- sub-millisecond writes, native consumer groups, append-only streams, and real-time push-based delivery -- while honestly addressing the gaps with pragmatic mitigations. The result is a **Redis-only architecture** where Redis is the sole event store for both hot and cold tiers.

This is not "Redis as a buffer in front of Postgres." This is Redis as the event store, period. No S3, no Parquet, no external cold archive.

---

## 1. Redis Data Model

### Primary Data Structures

The event store uses three Redis data structures in concert:

#### 1.1 Redis Streams — Event Log (Total Ordering + Consumer Groups)

The Redis Stream is the backbone of the event store. Every event is appended via `XADD` with an auto-generated time-based ID that provides total ordering.

**Stream key:** `events:{session_id}`

One stream per session provides natural data locality for session-scoped queries while keeping individual stream sizes manageable.

**A global stream** `events:__global__` receives a copy of every event (via Lua script, atomic with the session stream write) to provide the total ordering needed for projection replay. This is the equivalent of `global_position`.

```
XADD events:__global__ * \
    event_id <uuid> \
    event_type agent.invoke \
    occurred_at 2026-02-11T10:30:00Z \
    session_id sess-abc \
    agent_id agent-1 \
    trace_id trace-xyz \
    payload_ref pr:evt:<uuid> \
    tool_name web_search \
    parent_event_id <uuid-or-empty> \
    ended_at <timestamp-or-empty> \
    status success \
    schema_version 1 \
    importance_hint 7
```

**Why per-session streams?** XRANGE on a global stream to find events for a single session requires scanning the entire stream. Per-session streams give O(N) reads where N is the number of events in that session, not in the entire system.

**Why also a global stream?** The projection worker needs total ordering across all sessions. Consumer groups on the global stream provide this.

#### 1.2 RedisJSON — Event Documents (Rich Querying via RediSearch)

Each event is also stored as a JSON document for secondary index queries:

**Key pattern:** `evt:{event_id}`

```json
{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "agent.invoke",
    "occurred_at": "2026-02-11T10:30:00.000Z",
    "occurred_at_epoch_ms": 1707644400000,
    "session_id": "sess-abc",
    "agent_id": "agent-1",
    "trace_id": "trace-xyz",
    "payload_ref": "pr:evt:550e8400-e29b-41d4-a716-446655440000",
    "tool_name": "web_search",
    "parent_event_id": "440e7300-d18a-31c3-b615-335544330000",
    "ended_at": "2026-02-11T10:30:01.200Z",
    "status": "success",
    "schema_version": 1,
    "importance_hint": 7,
    "stream_id": "1707644400000-0"
}
```

The `stream_id` field links back to the global stream entry for provenance.

#### 1.3 RediSearch Index — Secondary Queries

```
FT.CREATE idx:events ON JSON PREFIX 1 evt:
SCHEMA
    $.event_id        AS event_id        TAG
    $.event_type      AS event_type      TAG
    $.session_id      AS session_id      TAG
    $.agent_id        AS agent_id        TAG
    $.trace_id        AS trace_id        TAG
    $.tool_name       AS tool_name       TAG
    $.status          AS status          TAG
    $.parent_event_id AS parent_event_id TAG
    $.occurred_at_epoch_ms AS occurred_at_epoch_ms NUMERIC SORTABLE
    $.importance_hint AS importance_hint  NUMERIC SORTABLE
    $.schema_version  AS schema_version  NUMERIC
```

This enables all query patterns currently served by Postgres:
- `FT.SEARCH idx:events "@session_id:{sess-abc}"` — events by session
- `FT.SEARCH idx:events "@agent_id:{agent-1}"` — events by agent
- `FT.SEARCH idx:events "@trace_id:{trace-xyz}"` — events by trace
- `FT.SEARCH idx:events "@occurred_at_epoch_ms:[1707644400000 1707730800000]"` — time range
- `FT.SEARCH idx:events "@session_id:{sess-abc} @event_type:{tool.execute}"` — composite queries
- `FT.SEARCH idx:events "@session_id:{sess-abc}" SORTBY occurred_at_epoch_ms ASC` — ordered results

### Supporting Data Structures

#### 1.4 Deduplication Set

**Key:** `dedup:events`
**Type:** Redis Set (or Hash with TTL per member via sorted set)

Stores `event_id` values for deduplication. Uses a sorted set with score = ingestion timestamp, enabling periodic cleanup of old entries:

```
ZADD dedup:events <timestamp> <event_id>
```

Entries older than the dedup window (default: 24 hours) are pruned by `ZREMRANGEBYSCORE`.

#### 1.5 Forgettable Payloads (GDPR)

**Key pattern:** `pii:{pseudonym_id}`
**Type:** RedisJSON document, encrypted at rest

```json
{
    "pseudonym_id": "ps-abc-123",
    "encryption_key_ref": "kms:key:456",
    "payload": "<encrypted-blob>",
    "created_at": "2026-02-11T10:30:00Z",
    "data_subject_id": "user-789"
}
```

**Crypto-shredding:** To "forget" a data subject, delete the encryption key from the KMS and `DEL pii:*` matching the data subject. The encrypted payloads in event records become unreadable.

**Secondary index for erasure requests:**
```
FT.CREATE idx:pii ON JSON PREFIX 1 pii:
SCHEMA
    $.data_subject_id AS data_subject_id TAG
    $.pseudonym_id    AS pseudonym_id    TAG
```

This enables `FT.SEARCH idx:pii "@data_subject_id:{user-789}"` to find all PII records for a given data subject during an erasure request.

#### 1.6 Cursor Tracking

**Key:** `cursor:projection:{worker_id}`
**Type:** String (stores last processed global stream ID)

```
SET cursor:projection:worker-1 "1707644400000-0"
```

While consumer groups track position automatically, explicit cursor storage provides a backup for manual replay operations.

---

## 2. Idempotent Ingestion Pattern

Idempotent ingestion is implemented via a Lua script that atomically checks the dedup set and writes to all three structures (global stream, session stream, JSON document):

```lua
-- idempotent_ingest.lua
-- KEYS[1] = dedup:events (sorted set)
-- KEYS[2] = events:__global__ (global stream)
-- KEYS[3] = events:{session_id} (session stream)
-- KEYS[4] = evt:{event_id} (JSON document key)
-- ARGV[1] = event_id
-- ARGV[2] = current_timestamp_ms (for dedup score)
-- ARGV[3..N] = stream field-value pairs
-- ARGV[N+1] = JSON document string

local event_id = ARGV[1]
local timestamp = tonumber(ARGV[2])

-- Check dedup set
local exists = redis.call('ZSCORE', KEYS[1], event_id)
if exists then
    return {0, 'duplicate'}  -- Already ingested
end

-- Add to dedup set
redis.call('ZADD', KEYS[1], timestamp, event_id)

-- Append to global stream (auto-ID for total ordering)
local field_values = {}
for i = 3, #ARGV - 1 do
    table.insert(field_values, ARGV[i])
end
local stream_id = redis.call('XADD', KEYS[2], '*', unpack(field_values))

-- Append to session stream (same entry, same auto-ID approach)
redis.call('XADD', KEYS[3], '*', unpack(field_values))

-- Store JSON document (inject stream_id for provenance linkage)
local json_doc = ARGV[#ARGV]
-- We pass the stream_id back; the caller patches it into the JSON
redis.call('JSON.SET', KEYS[4], '$', json_doc)
redis.call('JSON.SET', KEYS[4], '$.stream_id', '"' .. stream_id .. '"')

return {1, stream_id}  -- Success, return the global stream ID
```

**Properties:**
- **Atomic:** The entire check-write-write-write runs as a single Redis command (Lua scripts are atomic)
- **Idempotent:** Duplicate `event_id` returns immediately without side effects
- **Total ordering preserved:** The global stream ID is auto-assigned by Redis
- **Consistent:** All three representations (global stream, session stream, JSON doc) are written atomically

**Dedup window cleanup (periodic):**
```
ZREMRANGEBYSCORE dedup:events -inf <timestamp_24h_ago>
```

This runs as a scheduled job (every hour) to keep the dedup set bounded.

**Note on Redis 8.6 idempotent XADD:** Redis 8.6's native idempotent production uses producer-ID/ingestion-ID pairs, not arbitrary UUIDs. Since our dedup key is `event_id` (a UUID), the Lua script approach is more appropriate. If future Redis versions support arbitrary dedup keys on XADD, the Lua script can be simplified.

---

## 3. Global Ordering and Cursor-Based Polling

### Global Position Semantics

The `global_position` concept maps to the Redis Stream entry ID on the `events:__global__` stream:

| Postgres Concept | Redis Equivalent |
|-----------------|-----------------|
| `global_position` (BIGSERIAL) | Stream entry ID (e.g., `1707644400000-0`) |
| Gap-free sequential integer | Timestamp-based with sequence suffix |
| `WHERE global_position > $cursor` | `XREAD ... $cursor` or `XRANGE $cursor + COUNT n` |
| Monotonically increasing | Monotonically increasing (single node) |

**Key difference:** Redis Stream IDs encode time information directly (milliseconds since epoch + sequence). This is actually richer than a bare integer -- you get both ordering AND timestamp in a single value. The projection worker's cursor is now a stream entry ID string rather than an integer.

### Projection Worker: Consumer Group Pattern

```python
# Projection worker using consumer groups
import redis.asyncio as redis

STREAM = "events:__global__"
GROUP = "projection"
CONSUMER = "worker-1"

async def run_projection_worker(r: redis.Redis):
    # Create consumer group (idempotent)
    try:
        await r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    while True:
        # Read new entries (blocking, 5s timeout)
        entries = await r.xreadgroup(
            GROUP, CONSUMER,
            streams={STREAM: ">"},  # ">" means only new, undelivered entries
            count=100,
            block=5000
        )

        if not entries:
            continue  # No new entries, loop back to block

        for stream_name, messages in entries:
            for msg_id, fields in messages:
                # Project to Neo4j
                await project_event_to_neo4j(fields)
                # Acknowledge processing
                await r.xack(STREAM, GROUP, msg_id)
```

**Advantages over Postgres polling:**
- **Push-based:** `XREADGROUP ... BLOCK` eliminates polling lag entirely
- **Built-in position tracking:** Consumer group tracks last-delivered ID automatically
- **Crash recovery:** Unacknowledged entries (PEL) are re-delivered on restart
- **Multi-worker scaling:** Multiple consumers in the same group auto-distribute entries

### Full Replay

For re-projection from the beginning:

```python
async def full_replay(r: redis.Redis):
    cursor = "0"
    while True:
        entries = await r.xrange(STREAM, min=cursor, max="+", count=500)
        if not entries:
            break
        for msg_id, fields in entries:
            await project_event_to_neo4j(fields)
            cursor = msg_id
```

If older stream entries have been trimmed, the JSON documents still exist in Redis. Full replay uses RediSearch to page through all events (hot and cold) sorted by `occurred_at_epoch_ms`. See Section 6 (Long-Term Retention).

---

## 4. Querying Patterns

### By Session

```
FT.SEARCH idx:events "@session_id:{sess-abc}" SORTBY occurred_at_epoch_ms ASC
```

Or directly from the session stream (faster for ordered sequential access):
```
XRANGE events:sess-abc - +
```

### By Agent

```
FT.SEARCH idx:events "@agent_id:{agent-1}" SORTBY occurred_at_epoch_ms DESC LIMIT 0 50
```

### By Trace

```
FT.SEARCH idx:events "@trace_id:{trace-xyz}" SORTBY occurred_at_epoch_ms ASC
```

### By Time Range

```
FT.SEARCH idx:events "@occurred_at_epoch_ms:[1707644400000 1707730800000]" SORTBY occurred_at_epoch_ms ASC
```

Or on the global stream (time-based IDs enable native range queries):
```
XRANGE events:__global__ 1707644400000 1707730800000
```

### Composite Queries

```
FT.SEARCH idx:events "@session_id:{sess-abc} @event_type:{tool.execute} @status:{success}" SORTBY occurred_at_epoch_ms ASC
```

### Lineage (Parent Chain)

Given an event, walk its `parent_event_id` chain:

```python
async def get_lineage_chain(r: redis.Redis, event_id: str, max_depth: int = 10):
    chain = []
    current_id = event_id
    for _ in range(max_depth):
        doc = await r.json().get(f"evt:{current_id}")
        if not doc:
            break
        chain.append(doc)
        parent_id = doc.get("parent_event_id")
        if not parent_id:
            break
        current_id = parent_id
    return chain
```

This traversal is O(depth) Redis round trips, which is fast for typical lineage chains (depth 3-10). For deeper traversals, the Neo4j projection handles it via graph traversal.

---

## 5. Durability Configuration

### Recommended Production Configuration

```
# redis.conf for event store

# Persistence: Hybrid RDB + AOF
save 900 1          # RDB snapshot every 15 min if >= 1 key changed
save 300 10         # RDB snapshot every 5 min if >= 10 keys changed
save 60 10000       # RDB snapshot every 1 min if >= 10000 keys changed

# AOF with everysec fsync (recommended balance)
appendonly yes
appendfsync everysec

# AOF rewrite thresholds
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 256mb

# Memory management
maxmemory-policy noeviction    # CRITICAL: never evict event data silently
```

### Durability Trade-off Analysis

| Configuration | Data Loss Window | Throughput Impact | Recommendation |
|--------------|-----------------|-------------------|----------------|
| `appendfsync always` | ~0 (approaching Postgres) | -50% to -80% | Only if regulatory requirement mandates zero data loss |
| `appendfsync everysec` | Up to 1 second | Minimal | **Recommended for most deployments** |
| RDB only | Minutes | None | Not acceptable for event store |

### Why `everysec` Is Acceptable

The 1-second data loss window is mitigated by:

1. **Idempotent producers:** Agents that lose connection and retry will re-send events. The dedup logic handles duplicates. The only events truly lost are those that Redis acknowledged but did not persist before crash -- the producer believes they succeeded but they are gone. This is a sub-second window.

2. **Neo4j as secondary record:** Once events are projected to Neo4j, the graph nodes exist independently. A lost Redis event means a gap in the event ledger but not necessarily a gap in the graph (if the projection worker already processed it before the crash).

3. **Replication:** With Redis Sentinel or Redis Cluster, a replica can be promoted on primary failure. The WAIT command can enforce synchronous replication for critical writes:

```
# After XADD, wait for at least 1 replica to acknowledge
WAIT 1 100  # Wait for 1 replica, 100ms timeout
```

### For Maximum Durability (When Required)

If the deployment requires Postgres-level durability guarantees:

```
appendfsync always
```

Combined with `WAIT 1 0` (synchronous replication, no timeout) after each ingest. This provides durability comparable to Postgres with synchronous commit, at the cost of throughput. Even with this cost, Redis ingest latency (~1-5ms with fsync) is comparable to Postgres (~2-5ms with WAL sync), so the net performance is similar rather than worse.

---

## 6. Long-Term Retention Strategy

### The Core Challenge

Keeping all events in Redis memory forever is cost-intensive at scale. The solution is a Redis-only tiered retention model where stream entries are trimmed after the hot window while JSON documents persist for cold queries.

### Tiered Retention Architecture

```
                    Hot (0-7 days)              Cold (7+ days)
                   ┌──────────────────┐       ┌──────────────────┐
  Events ─────────>│ Redis Streams    │──────>│ Redis JSON docs  │
  (XADD)           │ + JSON docs      │ trim  │ (streams trimmed)│
                   │ + RediSearch     │ ───>  │ + RediSearch     │
                   │ (full detail)    │       │ (queryable)      │
                   └──────┬───────────┘       └──────┬───────────┘
                          │                          │
                  Consumer Groups            FT.SEARCH queries
                  (projection worker)        JSON.GET lookups
                  XRANGE replay              Cursor-based replay
```

### How It Works

1. Events are ingested into Redis Streams (global + per-session) and JSON documents simultaneously via the Lua ingestion script
2. After the hot window (default: 7 days), a trimmer job removes old stream entries via `XTRIM` with `MINID`
3. JSON documents (`evt:{event_id}`) are NOT deleted — they remain in Redis, queryable via RediSearch
4. Cold events support the same query patterns as hot events via `FT.SEARCH idx:events`
5. Stream trimming reclaims ~40-60% of per-event memory (stream entries are redundant with JSON docs for query purposes)

### Implementation

#### Trimmer Worker

A periodic job trims stream entries beyond the hot window:

```python
HOT_WINDOW_DAYS = 7
RETENTION_CEILING_DAYS = 90  # Community Redis: delete JSON docs beyond this age

async def run_trimmer(r: redis.Redis):
    while True:
        # Trim global stream entries older than hot window
        hot_cutoff_ms = int((time.time() - HOT_WINDOW_DAYS * 86400) * 1000)
        await r.xtrim("events:__global__", minid=f"{hot_cutoff_ms}-0")

        # Trim per-session streams for completed sessions older than hot window
        # (completed = no new events in the hot window)
        for session_key in await get_old_session_keys(r, max_age_days=HOT_WINDOW_DAYS):
            await r.delete(session_key)

        # Community Redis only: prune JSON docs beyond the retention ceiling
        # (Skip this step if using Redis Enterprise Auto Tiering)
        ceiling_cutoff_ms = int((time.time() - RETENTION_CEILING_DAYS * 86400) * 1000)
        old_events = await r.ft("idx:events").search(
            f"@occurred_at_epoch_ms:[0 {ceiling_cutoff_ms}]",
            limit=1000
        )
        for doc in old_events.docs:
            await r.delete(doc.id)

        await asyncio.sleep(3600)  # Run every hour
```

#### Replay (Single Source)

Full replay reads from Redis only via RediSearch cursor-based pagination:

```python
async def full_replay(r: redis.Redis):
    # Use RediSearch to page through ALL events (hot + cold) in order
    offset = 0
    batch_size = 500
    while True:
        results = await r.ft("idx:events").search(
            "*",
            sort_by="occurred_at_epoch_ms",
            sort_order="ASC",
            offset=offset,
            num=batch_size
        )
        if not results.docs:
            break
        for doc in results.docs:
            event = json.loads(await r.json().get(doc.id))
            await project_event_to_neo4j(event)
        offset += batch_size
```

For hot-only replay (within the stream window), the more efficient `XRANGE` approach remains:

```python
async def hot_replay(r: redis.Redis):
    cursor = "0"
    while True:
        entries = await r.xrange("events:__global__", min=cursor, max="+", count=500)
        if not entries:
            break
        for msg_id, fields in entries:
            await project_event_to_neo4j(fields)
            cursor = msg_id
```

### Memory Management at Scale

| Strategy | When to Use | Cost Impact |
|----------|-------------|-------------|
| **Stream trimming** (default) | Always | Reclaims 40-60% of per-event memory after hot window |
| **Retention ceiling** (community Redis) | When total memory exceeds budget | Events beyond ceiling are deleted; Neo4j + summary nodes preserve semantics |
| **Redis Enterprise Auto Tiering** | Growth/enterprise scale | Cold JSON docs stored on SSD (10-20x cheaper than RAM); transparent to application |
| **Reduce hot window** | Memory pressure exceeds 80% | Shrink from 7 days to 3 days; stream entries trimmed sooner |

### Cost Projection

| Scale | Community Redis (90-day ceiling) | Redis Enterprise Auto Tiering (1 year) | vs. Postgres-only |
|-------|--------------------------------|----------------------------------------|-------------------|
| Startup (1K runs/day) | **~$30/mo** (2 GB RAM) | ~$30/mo | ~$20/mo (1.5x) |
| Growth (10K runs/day) | **~$200/mo** (16 GB RAM) | ~$120/mo | ~$100/mo (1.2-2.0x) |
| Enterprise (100K runs/day) | **~$1500/mo** (120 GB RAM) | ~$600/mo | ~$500/mo (1.2-3.0x) |

At startup scale, all-in-memory Redis is comparable to Postgres. At growth/enterprise scale, Redis Enterprise Auto Tiering is recommended to keep costs manageable. Community Redis deployments should tune the retention ceiling to stay within budget — events beyond the ceiling are lost from Redis but their semantic structure persists in Neo4j.

---

## 7. GDPR / Forgettable Payloads in Redis

### Architecture

The Forgettable Payloads pattern (ADR-0001 Core Commitment #5) adapts cleanly to Redis:

```
Event in Redis Stream/JSON:
    payload_ref: "pr:evt:550e8400..."  ──> points to encrypted payload

Encrypted Payload (RedisJSON):
    pii:ps-abc-123: {
        "encryption_key_ref": "kms:key:456",
        "payload": "<AES-256-GCM encrypted blob>",
        "data_subject_id": "user-789"
    }

Encryption Key (external KMS -- AWS KMS, HashiCorp Vault):
    kms:key:456: <AES-256 key material>
```

### Erasure Request Flow

1. Receive erasure request for `data_subject_id = user-789`
2. Query all PII records: `FT.SEARCH idx:pii "@data_subject_id:{user-789}"`
3. For each PII record, delete the encryption key from KMS
4. Delete the PII documents from Redis: `DEL pii:ps-abc-123 ...`
5. The event records in streams and JSON docs remain intact (immutable) but the payload is now unreadable (crypto-shredded)

### Ensuring Complete Erasure from Persistence Layers

**Concern:** After deleting PII keys from Redis, old RDB snapshots or AOF segments may still contain the plaintext key material.

**Mitigation:**
- PII encryption keys are stored in an external KMS, not in Redis. Redis only stores `encryption_key_ref` (a pointer), not the key itself.
- The encrypted payload blob in Redis is useless without the KMS key.
- After erasure, trigger an AOF rewrite (`BGREWRITEAOF`) to eliminate old AOF entries containing the deleted PII documents.
- Old RDB snapshots should be rotated with a retention policy (e.g., keep last 7 days of snapshots, delete older ones).
- Since all event data resides in Redis (no external archive), crypto-shredding is a single-store operation with no cross-system consistency concerns.

---

## 8. Event Schema Field Mapping

### Complete Mapping: ADR-0004 Schema to Redis Structures

| ADR-0004 Field | Redis Stream Field | RedisJSON Path | RediSearch Index | Notes |
|---------------|-------------------|---------------|-----------------|-------|
| `event_id` (UUID PK) | `event_id` | `$.event_id` | TAG | Dedup key in sorted set |
| `event_type` (STRING) | `event_type` | `$.event_type` | TAG | Dot-namespaced |
| `occurred_at` (TIMESTAMPTZ) | `occurred_at` | `$.occurred_at` + `$.occurred_at_epoch_ms` | NUMERIC (epoch_ms) | ISO string + epoch for range queries |
| `session_id` (STRING) | `session_id` | `$.session_id` | TAG | Also used as stream key suffix |
| `agent_id` (STRING) | `agent_id` | `$.agent_id` | TAG | |
| `trace_id` (STRING) | `trace_id` | `$.trace_id` | TAG | |
| `payload_ref` (STRING) | `payload_ref` | `$.payload_ref` | — | Not indexed (dereference only) |
| `global_position` (BIGSERIAL) | *Stream entry ID* | `$.stream_id` | — | Auto-assigned by Redis; stored as `stream_id` in JSON |
| `tool_name` (STRING, opt) | `tool_name` | `$.tool_name` | TAG | |
| `parent_event_id` (UUID FK, opt) | `parent_event_id` | `$.parent_event_id` | TAG | No FK enforcement; app-level validation |
| `ended_at` (TIMESTAMPTZ, opt) | `ended_at` | `$.ended_at` | — | |
| `status` (STRING, opt) | `status` | `$.status` | TAG | |
| `schema_version` (INT, opt) | `schema_version` | `$.schema_version` | NUMERIC | |
| `importance_hint` (SMALLINT, opt) | `importance_hint` | `$.importance_hint` | NUMERIC SORTABLE | 1-10 range validated by Pydantic |

### Schema Enforcement

Redis provides no schema enforcement. All validation is performed by the Pydantic v2 models at the API layer before any Redis write:

```python
class EventEnvelope(BaseModel, strict=True):
    event_id: UUID
    event_type: str = Field(pattern=r"^[a-z]+\.[a-z_]+$")
    occurred_at: datetime
    session_id: str = Field(min_length=1, max_length=255)
    agent_id: str = Field(min_length=1, max_length=255)
    trace_id: str = Field(min_length=1, max_length=255)
    payload_ref: str = Field(min_length=1)
    tool_name: str | None = None
    parent_event_id: UUID | None = None
    ended_at: datetime | None = None
    status: str | None = None
    schema_version: int = Field(default=1, ge=1)
    importance_hint: int | None = Field(default=None, ge=1, le=10)
```

**Defense in depth:** Even though Redis has no schema layer, the strict Pydantic model rejects malformed events before they reach Redis. Combined with the Lua script for atomic ingestion, the application layer provides equivalent validation to what Postgres constraints offered, minus the database-level safety net.

---

## 9. Operational Architecture

### Component Overview

```
┌──────────────┐     ┌─────────────────────────────────────────────┐
│  Agent / API │     │                 Redis Stack                  │
│  (FastAPI)   │────>│  Streams   │  JSON Docs  │  Search Index    │
│              │     │  (events)  │  (evt:*)    │  (idx:events)    │
└──────────────┘     └──────┬─────────────┬──────────────┬─────────┘
                            │             │              │
                     ┌──────▼──────┐      │       ┌──────▼──────┐
                     │ Projection  │      │       │  Query API  │
                     │ Worker      │      │       │ (FT.SEARCH) │
                     │ (consumer   │      │       └─────────────┘
                     │  group)     │      │
                     └──────┬──────┘   ┌──▼────────────┐
                            │          │ Trimmer Worker │
                     ┌──────▼──────┐   │ (XTRIM, DEL   │
                     │   Neo4j     │   │  old streams)  │
                     │ (semantic   │   └────────────────┘
                     │  memory)    │
                     └─────────────┘
```

### Process Model

| Process | Role | Redis Interaction |
|---------|------|-------------------|
| **API server** (FastAPI) | Event ingestion, query serving | Lua script XADD, FT.SEARCH, JSON.GET |
| **Projection worker** | Stage 1: event --> Neo4j | XREADGROUP on `events:__global__` |
| **Enrichment worker** | Stage 2: derive attributes | Reads Neo4j, writes Neo4j |
| **Re-consolidation worker** | Stage 3: periodic graph optimization | Reads Neo4j, writes Neo4j |
| **Trimmer worker** | Trim old stream entries, prune JSON docs beyond retention ceiling | XTRIM, DEL on old stream/JSON keys |

### Monitoring

| Metric | Source | Purpose |
|--------|--------|---------|
| `redis_stream_length{stream="events:__global__"}` | `XLEN` | Stream growth rate |
| `redis_consumer_lag{group="projection"}` | `XPENDING` | Projection lag |
| `redis_json_doc_count` | `FT.INFO idx:events` | Total event documents in Redis |
| `redis_memory_used_bytes` | `INFO memory` | Memory pressure |
| `redis_aof_rewrite_in_progress` | `INFO persistence` | AOF health |
| `trimmer_events_pruned_total` | Application counter | Events pruned beyond retention ceiling |
| `dedup_set_size` | `ZCARD dedup:events` | Dedup set growth |

---

## 10. Migration Path from Postgres

### Phase 1: Deploy Redis alongside Postgres (dual-write)
- API writes to both Postgres and Redis
- Projection worker reads from Redis (consumer group)
- Validate that Redis events match Postgres events
- Duration: 2-4 weeks

### Phase 2: Redis becomes primary
- API writes to Redis only
- Postgres is read-only (for validation and rollback safety)
- Duration: 2-4 weeks

### Phase 3: Decommission Postgres
- Stop Postgres
- Full replay from Redis to validate Neo4j projection
- Postgres data imported into Redis JSON docs as historical archive (one-time migration)
- Remove asyncpg dependency

### Rollback Plan

At any phase, rollback to Postgres by:
1. Re-enabling Postgres writes
2. Replaying any Redis-only events into Postgres via RediSearch export
3. Switching projection worker back to Postgres polling

---

## 11. Design Trade-offs Summary

### What We Gain with Redis

| Advantage | Quantified Impact |
|-----------|------------------|
| Ingest latency | 10-100x faster (sub-ms vs. 2-5ms) |
| Projection worker model | Push-based consumer groups vs. polling (eliminates lag) |
| Operational simplicity (hot path) | No SQL, no migrations, no Alembic |
| Crash recovery for workers | Built-in PEL + XACK vs. application-level cursor |
| Real-time event delivery | Blocking XREAD, zero-delay fan-out |

### What We Trade

| Trade-off | Mitigation |
|-----------|------------|
| Weaker durability than Postgres WAL | AOF everysec + replication as safety net |
| No schema enforcement at storage layer | Strict Pydantic validation at API layer |
| In-memory cost for long-term retention | Stream trimming + retention ceiling (community) or Auto Tiering (enterprise) |
| No native range partitioning | Per-session streams + time-based XTRIM |
| Idempotent ingestion complexity | Atomic Lua script (well-tested pattern) |
| global_position format change | Stream entry ID (richer -- includes timestamp) |
| Single-node ordering only | Acceptable for MVP; cluster ordering is a Phase 3 concern |

### What Remains Unchanged

- Neo4j as the semantic memory / graph projection store
- Three-stage consolidation pipeline (projection, enrichment, re-consolidation)
- Decay scoring and active forgetting (operates on Neo4j, not event store)
- API contract (Atlas response pattern, intent-aware retrieval)
- Forgettable Payloads / crypto-shredding pattern
- Bounded query enforcement
- W3C PROV-DM alignment
