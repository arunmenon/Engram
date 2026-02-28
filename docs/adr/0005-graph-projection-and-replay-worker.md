# ADR-0005: Asynchronous Projection Worker with Replay Support

Status: **Accepted — Amended**
Date: 2026-02-07
Updated: 2026-02-11
Extended-by: ADR-0008 (consolidation stages 2 and 3, decay, forgetting)

## Context
Graph queries should be fast and relationship-centric, while writes remain durable and append-only. Projection decouples ingest durability from graph query optimization.

Non-goals for MVP:
- Synchronous cross-store transaction coupling
- Real-time sub-second projection guarantees under all loads

## Decision

> **Note (ADR-0010):** The Decision text below reflects the original Postgres polling design. Per ADR-0010, the projection worker now uses Redis consumer groups (XREADGROUP) instead of Postgres polling. See the Amendments section for details.

A projector worker MUST asynchronously transform Postgres events into Neo4j nodes/edges.

The projector MUST:
- Be restart-safe
- Track processing position
- Support full replay/rebuild from event ledger
- Expose projection lag metrics

## Consequences
Positive:
- Better isolation of write and query concerns
- Recoverability after graph corruption or schema evolution
- Scalable projection pipeline patterns

Negative:
- Eventual consistency window
- Need monitoring for lag/failure handling
- Additional component to operate

## Alternatives Considered
1. Inline synchronous projection on ingest  
Rejected due to coupling, latency, and failure amplification.
2. Periodic batch-only projection
Rejected because latency may be too high for interactive agent workflows.

## Amendments

### 2026-02-11: Stage 1 Foundation for Multi-Stage Consolidation Pipeline

**What changed:** This ADR is now positioned as defining the foundational projection worker architecture and its Stage 1 (event projection) behavior. ADR-0008 extends this worker with two additional consolidation stages (enrichment and re-consolidation), decay scoring, and active forgetting.

**Relationship to ADR-0008:** The four requirements specified in this ADR (restart-safe, position tracking, replay support, lag metrics) apply to all stages of the consolidation pipeline defined in ADR-0008:
- **Stage 1 (this ADR)**: Event projection — reads events from the Redis global stream via consumer group (originally polled Postgres by `global_position`), MERGE into Neo4j with temporal and causal edges. Runs continuously.
- **Stage 2 (ADR-0008)**: Enrichment — derives keywords, embeddings, importance scores, similarity edges. Runs asynchronously after Stage 1 batches.
- **Stage 3 (ADR-0008)**: Re-consolidation — periodic cross-event relationship discovery, hierarchical summarization, active forgetting/pruning. Runs on configurable schedule.

**Replay vs. Re-consolidation:** Replay is a full-rebuild mechanism: reset the cursor to position 0 and re-project all events from the Postgres ledger. It is distinct from re-consolidation (ADR-0008 Stage 3), which is a periodic enhancement pass over existing graph structure. After a replay, enrichment (Stage 2) and re-consolidation (Stage 3) must also run to restore the full graph state — Stage 1 replay alone produces a structurally correct but unenriched graph.

**Metrics:** This ADR's "expose projection lag metrics" requirement maps to `consolidation_lag_seconds` (time since last projected event). See ADR-0008 for the complete metric catalog covering all consolidation stages, including `enrichment_lag_seconds`, `reconsolidation_last_run`, `graph_nodes_total`, `graph_nodes_pruned_total`, `reflection_triggers_total`, and `decay_score_p50`.

### 2026-02-11: Redis Streams Replace Postgres Polling

**What changed:** Postgres polling replaced by Redis consumer groups (XREADGROUP) per ADR-0010. Push-based delivery eliminates polling lag. Consumer group tracks position automatically. Crash recovery via Pending Entry List (PEL) replaces application-level cursor.

### 2026-02-28: Orphaned Message Recovery and Dead-Letter Queue (H4, H5)

**Orphaned message claiming (H4):** Before the PEL drain loop, the consumer
now calls `XAUTOCLAIM` to claim messages that have been idle in the PEL for
longer than `claim_idle_ms` (default: 5 minutes). This recovers messages
from crashed consumer instances. `XAUTOCLAIM` (Redis 6.2+) combines
`XPENDING` + `XCLAIM` atomically and returns the claimed entries along
with their delivery counts.

**Dead-letter queue (H5):** During the PEL drain loop, each message's
delivery count is checked via `XPENDING ... <consumer>`. If a message has
been delivered more than `max_retries` times (default: 5), it is written to
a DLQ stream (`<stream>:dlq`) with metadata (original stream, entry ID,
group, consumer, delivery count) and then ACKed from the source stream.
This prevents permanently-failing messages from blocking the PEL drain on
every restart.

**Configuration:** New `ConsumerSettings` class with env prefix `CG_CONSUMER_`:
- `claim_idle_ms` (default 300000) -- min idle time before claiming
- `claim_batch_size` (default 100) -- max messages per XAUTOCLAIM
- `max_retries` (default 5) -- delivery attempts before dead-lettering
- `dlq_stream_suffix` (default `:dlq`) -- appended to source stream key

**Metric:** `engram_consumer_messages_dead_lettered_total{consumer}` counts
messages moved to the DLQ.

### Amendment: Hexagonal Port Protocols (Tier 1)

_Date: 2026-02-28_

Worker constructors now accept port protocol types instead of raw infrastructure drivers, enforcing hexagonal architecture boundaries. This decouples workers from concrete adapter implementations and enables testing with any protocol-conformant stub.

**Protocol-based worker constructors:**

| Worker | Before | After |
|--------|--------|-------|
| `ProjectionConsumer` | `Neo4jGraphStore` (concrete) | `GraphStore` (protocol from `ports/graph_store.py`) |
| `ConsolidationConsumer` | `AsyncDriver` (raw Neo4j) | `GraphMaintenance` (protocol from `ports/maintenance.py`) |
| `EnrichmentConsumer` | `AsyncDriver` (raw Neo4j) | `AsyncDriver` (unchanged — enrichment still uses raw driver for direct Cypher queries; protocol migration deferred) |

**New port protocols relevant to this ADR:**

- `GraphStore` (`ports/graph_store.py`): Covers `merge_event_node`, `create_edge`, `get_subgraph`, `get_lineage` — used by Consumer 1 (projection).
- `GraphMaintenance` (`ports/maintenance.py`): Covers `get_session_event_counts`, `write_summary_with_edges`, `delete_edges_by_type_and_age`, `delete_cold_events`, `delete_archive_events`, `update_importance_from_centrality` — used by Consumer 4 (consolidation).
- `HealthCheckable` (`ports/health.py`): Covers `health_ping` — used by health route for both stores.

**Dependency injection:** `api/dependencies.py` returns protocol types (not concrete adapters) to route handlers. DI functions like `get_graph_store() -> GraphStore` and `get_graph_maintenance() -> GraphMaintenance` ensure route files never import from `adapters/`.

**Impact on this ADR:**

- The "projector worker" described in the Decision section now receives its graph store via the `GraphStore` protocol, not a direct Neo4j driver reference.
- Replay support is unchanged — the `BaseConsumer` XREADGROUP lifecycle and PEL recovery still apply. The protocol boundary is at the graph write layer, not the stream read layer.
- The Stage 1/2/3 pipeline from the 2026-02-11 amendment now has explicit protocol boundaries: Stage 1 uses `GraphStore`, Stage 3 uses `GraphMaintenance`.

### Amendment: PEL-Safe Stream Trimming (Tier 1)

_Date: 2026-02-28_

Consumer 4 (consolidation) now performs PEL-safe stream trimming that
protects all consumer groups from data loss during `XTRIM`.

**What changed:** The `trim_stream()` function in `adapters/redis/trimmer.py`
accepts an optional `consumer_groups` parameter. When provided, it calls
`get_consumer_group_progress()` to find the oldest unprocessed entry across
all specified groups (via `XINFO GROUPS` + `XPENDING`), then computes
`min(age_cutoff, oldest_unprocessed)` as the safe trim point via
`compute_safe_trim_id()`.

The consolidation worker passes all 4 consumer group names:
`graph-projection`, `session-extraction`, `enrichment`, `consolidation`.

**Why this matters for ADR-0005:** The original Redis Streams amendment
(2026-02-11) established that crash recovery relies on the Pending Entry
List (PEL). If `XTRIM` removes entries that are still in a consumer group's
PEL, those entries are silently lost — the consumer will never process them
and cannot recover them. PEL-safe trimming closes this gap by ensuring the
trim point never advances past unprocessed entries for any group.

A warning is logged when consumer groups lag behind the age cutoff,
providing an early signal for operator intervention before the lag becomes
critical.
