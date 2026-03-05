# ADR-0014: Archival and Lifecycle Management

Status: **Accepted**
Date: 2026-02-23
Extends: ADR-0008 (memory consolidation and decay), ADR-0010 (Redis event store)

## Context

Production review of the consolidation and event store subsystems identified seven lifecycle gaps that, left unaddressed, will cause unbounded resource growth, irreversible data loss, or silent data corruption. Each gap is enumerated below with its operational risk.

### Gap 1: No Consolidation Trigger

The ConsolidationConsumer (Stage 3) waits for messages on the `consolidation_trigger` stream. No component ever publishes to that stream automatically. The worker sits idle indefinitely unless an operator manually sends a trigger via the admin API. In practice, Stage 3 never runs and events are never consolidated, pruned, or summarized.

**Risk**: Graph grows unbounded; decay scoring degrades; summary nodes are never created.

### Gap 2: Dedup Set Grows Unbounded

The `cleanup_dedup_set()` method exists on the Redis event store but is never called by any worker or scheduled task. The `dedup:events` sorted set accumulates one entry per ingested event and is never trimmed.

**Risk**: OOM after months of continuous ingestion. At 1K events/day the set reaches ~365K entries/year; at 100K events/day it reaches ~36.5M entries/year.

### Gap 3: Global Stream Never Capped

`XADD` to `events:__global__` has no `MAXLEN` parameter. While `XTRIM` is called during the hot-to-cold transition, no cap prevents the stream from growing during the hot window.

**Risk**: Unbounded stream memory growth during burst ingestion periods before the next trim cycle.

### Gap 4: Session Streams Never Cleaned

Per-session streams (`events:session:{session_id}`) are created during ingestion but never deleted. Completed sessions leave orphaned streams indefinitely.

**Risk**: Redis key count explosion. Each session creates a new stream key. At 100 sessions/day, 36,500 orphaned keys accumulate per year.

### Gap 5: No Archive-Before-Delete

When events reach the 90-day retention ceiling (community Redis), the trim cycle deletes JSON documents directly. Raw event data is permanently lost. The only surviving representation is Neo4j summary nodes, which are lossy abstractions.

**Risk**: Irreversible data loss. Compliance audits, debugging, and full replay become impossible for events older than 90 days.

### Gap 6: append_batch Sequential

The `append_batch()` method calls `append()` sequentially in a loop -- one Redis round-trip per event. For a 100-event batch, this takes 100+ ms on typical network latency.

**Risk**: Batch ingestion latency scales linearly with batch size. 100ms+ for modest batches; seconds for large session-end batches.

### Gap 7: Lua string.gsub Fragile

The Lua ingestion script uses `string.gsub` to patch `global_position` into the JSON string before writing. If the event payload itself contains the string `"global_position"`, the regex can match the wrong location, corrupting nested data.

**Risk**: Silent data corruption on events whose payloads reference the `global_position` field name.

## Decision

### 1. Archive-Before-Delete

Events MUST be exported to an archive store before deletion from Redis. The archive preserves raw event data beyond the Redis retention ceiling.

**Production**: Google Cloud Storage (GCS) or S3-compatible object store. Events are exported as compressed JSONL files (`.jsonl.gz`), partitioned by date: `archive/{year}/{month}/{day}/events_{timestamp}.jsonl.gz`.

**Development**: Local filesystem archive under a configurable directory (default: `./archive/`).

The archive store is defined by an `ArchiveStore` protocol in `ports/archive.py`:

```python
class ArchiveStore(Protocol):
    async def archive_events(self, events: list[dict], partition_key: str) -> str: ...
    async def list_archives(self, prefix: str) -> list[str]: ...
    async def restore_archive(self, archive_id: str) -> list[dict[str, Any]]: ...
    async def close(self) -> None: ...
```

Two adapters implement this protocol:
- `adapters/fs/archive.py` — local filesystem (development)
- `adapters/gcs/archive.py` — Google Cloud Storage (production, future)

The trim cycle in the consolidation worker becomes: **query expired events -> export to archive -> delete from Redis**. If the archive export fails, the deletion MUST NOT proceed.

### 2. Consolidation Scheduling

The ConsolidationConsumer MUST self-trigger via an in-process asyncio timer. The timer fires every `reconsolidation_interval_hours` (default: 6 hours, configurable via `CG_RECONSOLIDATION_INTERVAL_HOURS`).

The existing manual trigger via the `consolidation_trigger` stream is preserved for on-demand use via the admin API.

Concurrent consolidation runs are guarded by an `asyncio.Lock`. If a timer fires while a previous run is still in progress, the new run is skipped and a warning is logged.

```
Timer (6h) ──┐
              ├──> acquire lock ──> run consolidation ──> release lock
Manual msg ──┘
```

### 3. Stream Capping

The Lua ingestion script MUST accept an optional `MAXLEN` parameter for `XADD` on the global stream. The cap uses approximate trimming (`MAXLEN ~`) for performance.

Configuration: `CG_REDIS_GLOBAL_STREAM_MAXLEN` (default: `0` = uncapped). Recommended production value: `1000000` (1M entries).

When set to 0, no MAXLEN argument is passed to XADD (current behavior). When non-zero, XADD includes `MAXLEN ~ {value}`.

### 4. Session Stream Cleanup

The consolidation worker MUST clean up per-session streams whose newest entry is older than `session_stream_retention_hours` (default: 168 hours / 7 days, configurable via `CG_SESSION_STREAM_RETENTION_HOURS`).

Cleanup procedure:
1. Scan for keys matching `events:session:*`
2. For each stream, read the last entry via `XREVRANGE {key} + - COUNT 1`
3. If the entry timestamp is older than the retention threshold, delete the key via `DEL`
4. Log the number of streams cleaned per cycle

### 5. Dedup Set Maintenance

The `cleanup_dedup_set()` method MUST be called during every consolidation trim cycle. This removes entries from the `dedup:events` sorted set that are older than the dedup window (default: 24 hours).

The call is added to the consolidation worker's trim phase, after session stream cleanup and before archive-and-delete.

### 6. Lua Script Hardening

The `string.gsub` JSON patching for `global_position` MUST be replaced with a two-step write:

1. `JSON.SET evt:{event_id} $ {json_string}` — write the full document without `global_position`
2. `JSON.SET evt:{event_id} $.global_position {stream_id}` — set the field by JSON path

This eliminates regex-based string manipulation and makes the write immune to payload content.

The two JSON.SET calls remain within the same Lua script, preserving atomicity.

### 7. Batch Optimization

`append_batch()` MUST use `asyncio.gather()` with a concurrency semaphore (default: 50) to execute event ingestion calls concurrently:

```python
semaphore = asyncio.Semaphore(50)

async def _throttled_append(event):
    async with semaphore:
        return await self.append(event)

results = await asyncio.gather(*[_throttled_append(e) for e in events])
```

This reduces batch latency from `O(n * RTT)` to approximately `O(RTT)` for batches up to the semaphore limit, and `O(ceil(n/50) * RTT)` for larger batches.

## Lifecycle Diagram

The complete event lifecycle across both stores, incorporating all fixes:

```
Day 0:    Redis HOT (Stream + JSON) + Neo4j HOT
Day 7:    Redis COLD (stream trimmed) + Neo4j WARM
Day 30:   Neo4j COLD -> Summary nodes replace raw events
Day 60:   Redis JSON -> EXPORT to GCS as .jsonl.gz -> DELETE from Redis
Day 90:   Only Neo4j Summaries + GCS archive survive
Day 365+: GCS lifecycle policy moves to Coldline/Archive class
```

Key transitions:
- **Day 0-7**: Full detail in both stores. Stream entries provide consumer group delivery; JSON documents provide query access.
- **Day 7**: Stream entries trimmed (XTRIM). Session streams for completed sessions deleted. JSON documents remain for cold queries.
- **Day 30**: Neo4j consolidation replaces raw event nodes with summary nodes. Graph structure preserved at higher abstraction.
- **Day 60**: Consolidation worker exports expired Redis JSON documents to archive (GCS/filesystem), then deletes them. Dedup set entries cleaned.
- **Day 90**: Redis retains only events from the last 90 days. Older events exist only as Neo4j summaries and GCS archive files.
- **Day 365+**: GCS lifecycle policies transition archive files to cheaper storage classes (Nearline -> Coldline -> Archive).

## Configuration Summary

| Setting | Env Variable | Default | Description |
|---------|-------------|---------|-------------|
| Reconsolidation interval | `CG_RECONSOLIDATION_INTERVAL_HOURS` | 6 | Hours between automatic consolidation runs |
| Global stream maxlen | `CG_REDIS_GLOBAL_STREAM_MAXLEN` | 0 | Approximate MAXLEN for XADD (0 = uncapped) |
| Session stream retention | `CG_SESSION_STREAM_RETENTION_HOURS` | 168 | Hours before orphaned session streams are deleted |
| Archive backend | `CG_ARCHIVE_BACKEND` | `filesystem` | Archive store backend (`filesystem` or `gcs`) |
| Archive path | `CG_ARCHIVE_PATH` | `./archive/` | Local filesystem archive directory |
| Archive GCS bucket | `CG_ARCHIVE_GCS_BUCKET` | _(none)_ | GCS bucket for production archive |
| Batch concurrency | `CG_BATCH_CONCURRENCY` | 50 | Semaphore limit for asyncio.gather in append_batch |

## Consequences

### Positive

- **Bounded resource growth**: Stream capping, session cleanup, and dedup maintenance prevent unbounded memory and key count growth in Redis.
- **Data safety**: Archive-before-delete ensures raw event data survives beyond the Redis retention ceiling. Full replay remains possible from archive files.
- **Production readiness**: Automatic consolidation scheduling eliminates the operational burden of manual triggers. The system self-maintains without operator intervention.
- **Correctness**: Lua script hardening eliminates the data corruption risk from regex-based JSON patching.
- **Performance**: Batch optimization reduces ingestion latency for multi-event operations by up to 50x for large batches.
- **Compliance**: Archived events support audit and regulatory requirements that demand long-term data retention.

### Negative

- **Archive store dependency**: Production deployments require a GCS bucket (or S3-compatible store) for durable archival. This adds an infrastructure component beyond Redis and Neo4j.
- **Added complexity**: Seven interacting lifecycle mechanisms (timer, cap, cleanup, archive, dedup, Lua fix, batch) increase the surface area for bugs and misconfiguration.
- **Archive consistency**: If the archive export succeeds but the subsequent Redis delete fails (e.g., due to crash), events may be archived but not deleted, requiring idempotent cleanup on the next cycle.
- **Timer drift**: The asyncio timer may drift under heavy load. Consolidation runs are best-effort periodic, not precisely scheduled.

### Risks to Monitor

| Risk | Trigger | Mitigation |
|------|---------|------------|
| Archive export fails silently | Events deleted without successful archive | Export-then-delete with failure abort; monitor archive write success rate |
| Consolidation lock contention | Timer fires faster than consolidation completes | Skip-and-warn on lock contention; alert if consecutive skips exceed 3 |
| Session stream scan performance | Large number of session keys | Use SCAN with COUNT hint; batch cleanup across multiple cycles |
| Semaphore too low for burst ingestion | Batch latency still high under load | Make semaphore configurable; monitor p95 batch latency |
| GCS archive grows unbounded | No lifecycle policy configured | Document GCS lifecycle policy in deployment guide; alert on archive size |

## Alternatives Considered

### 1. External scheduler (cron/Celery) for consolidation
Rejected. Adding an external scheduler introduces a new infrastructure dependency. An in-process asyncio timer is simpler, has no deployment overhead, and is sufficient for a single-process consolidation worker.

### 2. Redis Streams as archive (separate Redis instance)
Rejected. Redis is not cost-effective for cold archival storage. Object storage (GCS/S3) is 100-1000x cheaper per GB for data accessed infrequently.

### 3. PostgreSQL as archive store
Rejected. The project has already migrated away from PostgreSQL (ADR-0010). Reintroducing it solely for archival adds operational complexity. Object storage is simpler for write-once, read-rarely workloads.

### 4. No archive — accept data loss at 90 days
Rejected. While Neo4j summary nodes preserve semantic structure, raw event data is required for compliance audits, debugging, and potential re-projection with updated logic. The cost of object storage archival is negligible compared to the risk of irreversible data loss.

---

### 2026-02-23 Amendment: Graph & Vector Index Lifecycle (Gaps 8-10)

#### Gap 8: Neo4j Orphan Node Cleanup

When Event nodes are DETACH DELETEd during cold/archive tier forgetting,
dependent nodes (Entity, Preference, Skill, Workflow, BehavioralPattern)
may lose all their edges and become orphaned.

**Decision**: After every forgetting cycle, run an orphan detection query
that finds nodes of these 5 types with zero relationships and deletes them.
Uses plain Cypher `WHERE NOT (n)--()` (compatible with Neo4j Community).
Batched in groups of 500 to avoid long transactions.

Node types exempt from orphan cleanup: UserProfile, Summary.
UserProfile nodes are long-lived identity anchors. Summary nodes are
the intended survivors of event deletion.

#### Gap 9: Entity Embedding Lifecycle (Resolved)

Entity embeddings are stored as properties on Neo4j Entity nodes (`embedding`
field), not in a separate Redis index. When Entity nodes are `DETACH DELETE`d
during orphan cleanup (Gap 8), their embedding properties are automatically
removed. No separate embedding cleanup step is needed.

This gap was resolved by the Neo4j-only embedding migration (see ADR-0009
amendment, 2026-02-25).

#### Gap 10: Neo4j Event Property Export Before Graph Deletion

The Redis archive (GCS) stores the raw event JSON documents. Neo4j Event
nodes have additional derived properties (importance_score, access_count,
centrality-based scores) that are not in the Redis document.

**Decision**: Do NOT export Neo4j event properties to GCS. Rationale:
- The Redis JSON document is the source of truth (ADR-0003)
- Neo4j properties are derived/computed and can be recomputed from events
- Adding a Neo4j-to-GCS export path adds complexity for marginal value
- Summary nodes already capture the semantic essence of deleted events

This is an explicit non-goal to keep the architecture simple.

### 2026-02-28: Rate Limiting & PEL-Safe Trimming (Tier 1)

_Date: 2026-02-28_

Stream trimming is now PEL-safe, and the API surface is rate-limited to
prevent burst ingestion from overwhelming lifecycle management.

**PEL-safe stream trimming (new):**

`trim_stream()` in `adapters/redis/trimmer.py` now accepts an optional
`consumer_groups` parameter. Two new helper functions support this:

- `get_consumer_group_progress(redis_client, stream_key)` — queries
  `XINFO GROUPS` to enumerate all consumer groups on the stream, then
  `XPENDING` for each group to find the oldest pending (unacknowledged)
  entry. Falls back to `last-delivered-id` when no entries are pending.
  Returns `dict[str, str]` mapping group name to oldest unprocessed ID.

- `compute_safe_trim_id(age_cutoff_id, group_progress)` — returns
  `min(age_cutoff_id, oldest_unprocessed_across_all_groups)`. When a
  consumer group is lagging behind the age cutoff, the trim point is moved
  forward to preserve unprocessed entries. A warning is logged with the
  identity and position of each lagging group.

The consolidation worker (`worker/consolidation.py`) passes all 4 consumer
group names to `trim_stream()` during the `_trim_redis()` step:
`graph-projection`, `session-extraction`, `enrichment`, `consolidation`.

**Rate limiting (new):**

A token bucket rate limiter (`api/rate_limit.py`) with LRU-bounded per-client
tracking protects ingestion endpoints. Standard tier: 120 RPM; admin tier:
30 RPM; health/metrics: exempt. Configurable via `CG_RATELIMIT_*` env vars.
`RateLimitMiddleware` returns 429 with `Retry-After` header on exhaustion.

New Prometheus counter: `engram_rate_limit_exceeded_total{tier}`.

**Impact on this ADR:**
- Gap 3 (stream capping) is further hardened: even with MAXLEN on XADD, the
  periodic XTRIM now respects consumer group progress, ensuring no entry is
  trimmed before all 4 consumer groups have processed it.
- The rate limiter bounds burst ingestion volume, reducing the risk that
  stream capping or trim cycles fall behind during traffic spikes.
