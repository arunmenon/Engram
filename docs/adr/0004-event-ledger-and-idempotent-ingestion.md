# ADR-0004: Immutable Event Ledger with Idempotent Ingestion

Status: **Accepted — Amended 2026-02-11**
Date: 2026-02-07
Updated: 2026-02-11
Extended-by: ADR-0007 (importance_hint field), ADR-0009 (enriched node properties)
Amended-by: ADR-0010 (event ledger moves from Postgres to Redis)

## Context
Agents and tools can retry, reorder, or duplicate calls. Ingestion must be robust under retries and partial failures without corrupting lineage.

Non-goals for MVP:
- Exactly-once delivery across all upstream systems
- Arbitrary schema-less payload ingestion

## Decision

> **Note (ADR-0010):** The Decision text below reflects the original Postgres design. Per ADR-0010, the event ledger has moved to Redis. Idempotent ingestion is now implemented via a Lua script with a dedup sorted set. See the Amendments section for the complete Redis implementation.

Ingestion MUST write immutable events to Postgres and MUST be idempotent.

Each event MUST include:
- `event_id`
- `event_type`
- `occurred_at`
- `session_id`
- `agent_id`
- `trace_id`
- `payload_ref`
- optional `tool_name`

The API MUST reject invalid envelopes and MUST safely deduplicate repeated `event_id` submissions.

## Consequences
Positive:
- Safe retries
- Stable replay and debugging semantics
- Cleaner downstream projection behavior

Negative:
- Requires strict client discipline around event identity
- Validation/versioning overhead for event contracts

## Alternatives Considered
1. Mutable event records  
Rejected because mutation breaks auditability and replay correctness.
2. Best-effort dedup without event IDs
Rejected due to ambiguity and collision risk.

## Amendments

### 2026-02-11: Complete Event Schema and Importance Hint

**What changed:** The event schema is expanded to serve as the single source of truth for all Postgres-persisted fields. Previously, several fields were defined only in the project CLAUDE.md but not in this ADR.

**Complete Postgres event schema:**

Required fields:
- `event_id` (UUID PK)
- `event_type` (STRING, dot-namespaced)
- `occurred_at` (TIMESTAMPTZ)
- `session_id` (STRING)
- `agent_id` (STRING)
- `trace_id` (STRING)
- `payload_ref` (STRING)
- `global_position` (BIGSERIAL, auto-assigned — total ordering for deterministic replay per ADR-0001)

Optional fields:
- `tool_name` (STRING)
- `parent_event_id` (UUID FK — enables CAUSED_BY edges per ADR-0009)
- `ended_at` (TIMESTAMPTZ — for span-style events with duration)
- `status` (STRING — event outcome: success, failure, timeout, etc.)
- `schema_version` (INTEGER — enables upcasting middleware for schema evolution)
- `importance_hint` (SMALLINT, 1-10, DEFAULT NULL — caller-supplied importance estimate per ADR-0007)

**Importance hint semantics:** The `importance_hint` field is an optional ingestion-time signal from the event producer. It is immutable once written, reflecting the caller's assessment at event time. The canonical `importance_score` is computed during enrichment (ADR-0008 Stage 2) and stored in Neo4j. The enrichment process MAY use the Postgres hint as one input signal among graph-derived factors. When the hint is absent, enrichment computes importance entirely from rule-based heuristics and graph context.

**Derived attributes exclusion:** The following attributes are computed during enrichment and stored only in Neo4j (not in Postgres): `keywords`, `embedding`, `summary`, `access_count`, `last_accessed_at`. See ADR-0009 for their definitions.

**Why:** The event schema was scattered across ADR-0004, CLAUDE.md, ADR-0007, and ADR-0009. This amendment consolidates it into ADR-0004 as the authoritative source. The `importance_hint` naming (rather than `importance_score`) avoids confusion with the enrichment-computed `importance_score` in Neo4j.

### 2026-02-11: Event Ledger Implementation Moves from Postgres to Redis

**What changed:** The event ledger implementation moves from Postgres to Redis per ADR-0010. The event schema fields themselves remain unchanged -- all 8 required and 6 optional fields defined above are preserved. Only the underlying storage and enforcement mechanisms change.

**Implementation changes:**
- **Idempotent ingestion**: `ON CONFLICT (event_id) DO NOTHING` is replaced by an atomic Lua script with a dedup sorted set (`dedup:events`). The Lua script checks the sorted set, and if the `event_id` is absent, atomically writes to the global stream, session stream, and JSON document. Duplicates are rejected without side effects.
- **`global_position`**: Changes from `BIGSERIAL` (auto-incrementing integer) to a Redis Stream entry ID (string, e.g. `"1707644400000-0"`). The entry ID is auto-assigned by Redis on the `events:__global__` stream and provides monotonically increasing total ordering on a single node. Clients SHOULD treat `global_position` as an opaque cursor.
- **Schema enforcement**: Postgres column constraints and database-level validation are replaced by Pydantic v2 strict mode validation at the API layer. This is a defense-in-depth reduction (single validation layer instead of two) accepted as a trade-off for Redis's operational simplicity and performance.
- **Storage format**: Postgres rows are replaced by RedisJSON documents (`evt:{event_id}`) indexed by RediSearch for secondary queries on `session_id`, `agent_id`, `trace_id`, `event_type`, and time ranges.

**What is preserved:** The event schema definition (field names, types, required/optional semantics), immutability guarantee (append-only, no mutation), idempotent ingestion semantics, and deterministic replay capability are all unchanged.
