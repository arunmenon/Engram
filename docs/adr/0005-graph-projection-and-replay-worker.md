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
