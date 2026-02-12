# Consolidated ADR Research Report

**Date**: 2026-02-07
**Scope**: Deep research across all 6 ADRs for the context-graph project

---

## Executive Summary

Six parallel research agents investigated the architectural decisions in ADRs 0001-0006. Key findings:

1. **The architecture is sound and fills a genuine gap** — no existing platform combines immutable event sourcing, graph-projected lineage, and provenance-annotated context retrieval.
2. **The ADR event schema should be enhanced** — add `parent_event_id`, `ended_at`, `status`, and `schema_version` to align with industry conventions (OpenTelemetry, Langfuse, LangSmith, OpenLineage).
3. **Polling + LISTEN/NOTIFY beats CDC for MVP** — simpler than Debezium/Kafka, sufficient for moderate event volumes, and trivially supports replay.
4. **Consider evaluating Apache AGE before committing to Neo4j** — if query patterns are mostly tree/DAG traversals of moderate depth, Postgres recursive CTEs or AGE may eliminate dual-store complexity.
5. **The API design should follow the Atlas pattern** — flat node maps + edges arrays + inline provenance, with three-layer query budgets (depth, node count, timeout).

---

## 1. Agent Traceability & Provenance (ADR-0001)

### Competitive Landscape

| Platform | Open Source | Trace Model | Immutable Ledger | Graph Projection | Provenance in Retrieval |
|---|---|---|---|---|---|
| LangSmith | No | Tree of Runs | No | No | No |
| Langfuse | Yes (MIT) | Tree of Observations | No | No | No |
| Arize Phoenix | Yes (Apache 2) | OTel Spans | No | No | No |
| AgentOps | No | Session Events | No | No | No |
| OpenLLMetry | Yes (Apache 2) | OTel Spans (lib only) | N/A | N/A | N/A |
| **context-graph** | Yes | **Immutable Event Ledger** | **Yes** | **Yes** | **Yes** |

**Key finding**: Every existing platform focuses on observability (look at what happened) but none close the loop into context retrieval with provenance. The context-graph architecture is architecturally novel.

### OpenTelemetry for LLM/Agent Systems

- The OTel **GenAI SIG** defines experimental semantic conventions: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, etc.
- Three competing convention sets exist: Official OTel GenAI SIG, OpenInference (Arize), and OpenLLMetry/Traceloop — converging but not yet unified.
- **Recommendation**: Support OTel span ingestion as an event source. Map OTel spans to the internal event format. This lowers integration friction for teams already using instrumented frameworks.

### W3C PROV Model Alignment

The W3C PROV data model maps remarkably well to agent traceability:

| PROV Concept | context-graph Equivalent |
|---|---|
| Activity | Tool call / Agent action event |
| Entity | Tool output / Retrieved document / Artifact |
| Agent | LLM agent / Tool |
| wasGeneratedBy | Event → Artifact |
| used | Event consumed Artifact |
| wasDerivedFrom | Artifact → Artifact lineage |

**Recommendation**: Adopt PROV-inspired relationship types in the Neo4j projection (`WAS_GENERATED_BY`, `USED`, `WAS_DERIVED_FROM`, `WAS_ASSOCIATED_WITH`).

### Context Graph vs Memory Systems

| Aspect | Memory-First (MemGPT/Zep/Mem0) | Traceability-First (ADR-0001) |
|---|---|---|
| Primary artifact | Memory entries | Immutable event records |
| Mutability | Mutable | Append-only |
| Source of truth | Current memory state | Event log |
| Provenance | Absent | First-class |
| Replay | Not supported | Deterministic rebuild |
| Trust model | "Agent decided to remember" | "Derived from event X via tool Y" |

**Key insight**: Memory features can be layered on top of a traceability substrate, but the reverse requires fundamental re-architecture.

---

## 2. Python + FastAPI Stack (ADR-0002)

### Framework Validation

FastAPI is confirmed as the correct choice:
- Ecosystem dominance (60k+ GitHub stars), Pydantic v2 (Rust-backed) for validation, native async
- Agent ecosystem fit (LangChain, LlamaIndex, CrewAI all use FastAPI)
- Throughput: ~10,000-18,000 req/sec with DB writes (4 workers) — sufficient for MVP and moderate scale

**Litestar** offers 10-20% better raw throughput but smaller ecosystem/hiring pool. Not worth the trade-off.

### Key Libraries and Versions

| Library | Purpose | Version |
|---|---|---|
| `fastapi` | HTTP framework | >= 0.115 |
| `pydantic` | Validation (Rust-backed v2) | >= 2.9 |
| `asyncpg` | Async Postgres driver | >= 0.29 |
| `neo4j` | Official Neo4j async driver | >= 5.25 |
| `orjson` | Fast JSON serialization | >= 3.10 |
| `structlog` | Structured logging | >= 24.4 |
| `prometheus-client` | Metrics | >= 0.21 |
| `alembic` | Postgres migrations | >= 1.13 |

### Recommended Project Structure

```
context-graph/
    pyproject.toml
    alembic.ini
    src/
        context_graph/
            settings.py               # Pydantic BaseSettings
            domain/                   # NO framework imports
                models.py             # Pydantic v2 domain models
                validation.py         # Event envelope rules
                projection.py         # Event → graph transform
                lineage.py            # Traversal algorithms
            ports/                    # typing.Protocol interfaces
                event_store.py
                graph_store.py
            adapters/
                postgres/
                    event_store.py    # asyncpg implementation
                    migrations/
                neo4j/
                    graph_store.py    # Neo4j async implementation
            api/
                app.py                # FastAPI factory (create_app())
                dependencies.py       # Depends() wiring
                routes/
                    events.py         # POST /v1/events, /v1/events/batch
                    context.py        # GET /v1/context/{session_id}
                    query.py          # POST /v1/query/subgraph
                    lineage.py        # GET /v1/nodes/{node_id}/lineage
                    health.py
            worker/                   # Separate process
                projector.py
                cursor.py
                cli.py
    tests/
        unit/
        integration/
    docker/
        docker-compose.yml
```

### Key Patterns

- **Lifespan context manager** (not deprecated `@app.on_event`):
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      app.state.pg_pool = await asyncpg.create_pool(...)
      app.state.neo4j_driver = AsyncGraphDatabase.driver(...)
      yield
      await app.state.pg_pool.close()
      await app.state.neo4j_driver.close()
  ```
- **Domain isolation**: `domain/` package has zero framework imports; enforced via linting
- **DI via Depends()**: Factory functions returning Protocol-typed objects
- **Projection worker**: Separate process, NOT FastAPI BackgroundTasks

---

## 3. Dual Store — Postgres + Neo4j (ADR-0003)

### Integration Pattern

**Recommended for MVP**: Direct polling projection worker (not CDC/Debezium).

| Approach | Complexity | Reliability | MVP Fit |
|---|---|---|---|
| Direct polling worker | Low | High | **Best** |
| Debezium + Kafka | Medium-High | Very High | Overkill |
| Application dual-write | Low | Poor | **Avoid** |

### Postgres Event Store Schema

```sql
CREATE TABLE context_events (
    event_id        UUID PRIMARY KEY,
    event_type      TEXT NOT NULL,
    schema_version  INT NOT NULL DEFAULT 1,
    occurred_at     TIMESTAMPTZ NOT NULL,
    ended_at        TIMESTAMPTZ,
    session_id      UUID NOT NULL,
    agent_id        TEXT NOT NULL,
    trace_id        UUID NOT NULL,
    parent_event_id UUID REFERENCES context_events(event_id),
    payload_ref     TEXT NOT NULL,
    tool_name       TEXT,
    status          TEXT CHECK (status IN ('ok', 'error', 'timeout')),
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    global_position BIGSERIAL NOT NULL  -- critical for projection worker
);

CREATE INDEX idx_events_global_position ON context_events (global_position);
CREATE INDEX idx_events_session_id ON context_events (session_id, occurred_at);
CREATE INDEX idx_events_trace_id ON context_events (trace_id);
CREATE INDEX idx_events_parent ON context_events (parent_event_id)
    WHERE parent_event_id IS NOT NULL;
```

**`global_position` (BIGSERIAL)** is the single most important column for the projection worker — provides a monotonic cursor.

### Neo4j Graph Schema

```cypher
(:Session {id, started_at, agent_id})
(:Agent {id, name})
(:ToolCall {id, tool_name, occurred_at, status})
(:Artifact {id, type, payload_ref})
(:Event {id, type, occurred_at, global_position})

(:Agent)-[:INITIATED]->(:Session)
(:Session)-[:CONTAINS]->(:Event)
(:Event)-[:INVOKED]->(:ToolCall)
(:ToolCall)-[:PRODUCED]->(:Artifact)
(:Event)-[:CAUSED]->(:Event)
(:ToolCall)-[:USED_CONTEXT]->(:Artifact)
```

### Alternatives to Neo4j Worth Evaluating

| Option | Eliminates Dual-Store | Graph Query Power | Operational Simplicity |
|---|---|---|---|
| Neo4j | No | Excellent | Medium |
| Apache AGE (Postgres extension) | **Yes** | Moderate | **High** |
| Memgraph | No | Excellent | Medium |
| Postgres recursive CTEs | **Yes** | Limited | **Highest** |

**Pragmatic recommendation**: Before going deep on Neo4j, prototype your top 3 graph queries using both Neo4j Cypher and Postgres recursive CTEs. If Postgres handles them well, defer Neo4j and simplify operations dramatically.

### Operational Concerns

- **Docker Compose from day one** — `docker compose up` as the single command for local dev
- **Neo4j is disposable** — it can always be rebuilt from Postgres events, simplifying backup strategy
- **Health checks** covering both stores and projection lag
- **Schema migrations**: Alembic for Postgres, numbered Cypher scripts for Neo4j

---

## 4. Event Ledger & Idempotent Ingestion (ADR-0004)

### Recommended Event Schema Enhancements

The ADR-0004 schema should be enhanced based on industry comparison:

| ADR-0004 Field | Status | Rationale |
|---|---|---|
| `event_id` | Keep | Aligned with all platforms |
| `event_type` | Keep | Aligned (use dot-namespaced: `agent.tool_call.started`) |
| `occurred_at` | Keep | Aligned |
| `session_id` | Keep | Aligned |
| `agent_id` | Keep | Good addition for multi-agent |
| `trace_id` | Keep | Aligned with OTel |
| `payload_ref` | Keep | Sound design (see payload storage below) |
| `tool_name` | Keep | Aligned for tool events |
| **`parent_event_id`** | **Add** | Critical for causal lineage (all platforms support parent-child) |
| **`ended_at`** | **Add** | Distinguishes point-in-time vs duration events |
| **`status`** | **Add** | `ok`/`error`/`timeout` — every tracing system has this |
| **`schema_version`** | **Add** | Essential for event evolution in append-only ledger |
| **`global_position`** | **Add** | BIGSERIAL for projection worker cursor |
| **`ingested_at`** | **Add** | Server-side timestamp, distinct from `occurred_at` |

### Idempotent Ingestion

```sql
INSERT INTO context_events (event_id, event_type, ...)
VALUES ($1, $2, ...)
ON CONFLICT (event_id) DO NOTHING
RETURNING event_id;
```

- `DO NOTHING` (not `DO UPDATE`) — events are immutable
- `RETURNING` clause detects whether insert happened (new) or was deduplicated
- No separate deduplication table needed

### Payload Storage

**Recommended**: Separate Postgres table for MVP, with `PayloadStore` abstraction for future S3 migration:

```sql
CREATE TABLE event_payloads (
    payload_id  UUID PRIMARY KEY,
    content     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- Same transactional boundary as events table (atomic writes)
- `payload_ref` format: `urn:payload:{uuid}`
- Abstract behind a `PayloadStore` Protocol so S3/MinIO migration is a config change

### Batch Ingestion

- All-or-nothing transactions for MVP (entire batch succeeds or fails)
- Multi-row INSERT with `ON CONFLICT DO NOTHING` for performance
- Max batch size: 1000
- Response includes per-event status (`created`/`duplicate`)
- HTTP 200 (processed), 400 (validation failure), 413 (too large)

### Event Versioning Strategy

- `schema_version` integer on each event
- **Upcasters**: Pure functions transforming v(N) → v(N+1) at read time
- No schema registry needed for MVP
- Document schemas in `schemas/` directory using Pydantic models

### Validation

- **Strict on envelope** (Pydantic v2, `extra="forbid"`, timezone-aware timestamps, regex-validated `event_type`)
- **Permissive on payload** (opaque data referenced by `payload_ref`)
- Validate entire batch before any writes
- Structured error responses with field paths

---

## 5. Async Projection & Replay (ADR-0005)

### Projection Trigger: Polling + LISTEN/NOTIFY

**Do NOT use CDC (Debezium/WAL) for MVP.** The event ledger table with `global_position` makes polling natural and sufficient.

```
Postgres INSERT → pg_notify('new_events') → Worker wakes →
SELECT WHERE global_position > checkpoint → Project to Neo4j →
Save checkpoint
```

| Factor | Polling + NOTIFY | CDC (Debezium) |
|---|---|---|
| Latency | Sub-second (NOTIFY wake-up) | Sub-second |
| Complexity | Very low | High (Kafka + Debezium) |
| Replay | Trivial (reset cursor to 0) | Requires snapshot + streaming |
| Operational risk | Minimal | Replication slot disk retention |

### Worker Architecture

**Custom asyncio worker** (not Celery/Faust/Temporal):

```python
class ProjectionWorker:
    # Poll events table in batches
    # LISTEN/NOTIFY for low-latency wake-up
    # UNWIND + MERGE for idempotent Neo4j writes
    # Checkpoint stored in Postgres
    # Graceful SIGTERM handling
```

Key properties:
- **Restart-safe**: Reads checkpoint on startup, resumes from there
- **Idempotent projection**: MERGE-based Cypher (replay-safe)
- **Batch processing**: 500 events/batch (steady-state), 2000-5000 during replay

### Checkpoint Storage

```sql
CREATE TABLE projection_checkpoints (
    projection_name    TEXT PRIMARY KEY,
    last_processed_id  BIGINT NOT NULL,
    projection_version TEXT NOT NULL,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

On startup, if code's projection version != stored version → auto-trigger full replay.

### Neo4j Write Pattern

```cypher
UNWIND $events AS evt
MERGE (e:ContextEvent {event_id: evt.event_id})
ON CREATE SET e.event_type = evt.event_type,
              e.occurred_at = evt.occurred_at
MERGE (s:Session {session_id: evt.session_id})
MERGE (a:Agent {agent_id: evt.agent_id})
MERGE (s)-[:CONTAINS]->(e)
MERGE (a)-[:EMITTED]->(e)
```

Required indexes for MERGE performance:
```cypher
CREATE CONSTRAINT event_id_unique FOR (e:ContextEvent) REQUIRE e.event_id IS UNIQUE;
CREATE CONSTRAINT session_id_unique FOR (s:Session) REQUIRE s.session_id IS UNIQUE;
CREATE CONSTRAINT agent_id_unique FOR (a:Agent) REQUIRE a.agent_id IS UNIQUE;
```

### Replay Strategy

**MVP**: Simple sequential replay — reset checkpoint to 0, clear Neo4j (`MATCH (n) DETACH DELETE n`), re-run projection loop. Accept downtime.

**Post-MVP**: Blue-green rebuild using Neo4j label namespacing (e.g., `ContextEvent_v2`) for zero-downtime rebuilds.

### Observability

Essential metrics (via `prometheus_client`):

| Metric | Type | Alert Threshold |
|---|---|---|
| `projection_lag_events` | Gauge | > 1000 events |
| `projection_lag_seconds` | Gauge | > 30 seconds |
| `projection_batch_duration_seconds` | Histogram | p99 > 5s |
| `projection_events_processed_total` | Counter | Rate drop to 0 |
| `projection_errors_total` | Counter | Any increase |

### When to Add a Message Queue

**Not for MVP.** Revisit when:
- 3+ independent consumers need the event stream
- Event volume exceeds 10K/sec
- Cross-service distribution needed

Then consider Redis Streams or NATS JetStream before Kafka.

---

## 6. Query & Lineage API (ADR-0006)

### API Design Philosophy

- **Structured REST endpoints** for MVP (not GraphQL, not Cypher-over-HTTP)
- **Atlas pattern**: Flat node map + edges array + provenance block (avoids deep nesting)
- **Three-layer query budget**: depth limit, node count limit, timeout

### `GET /v1/context/{session_id}`

Returns ordered context items for agent consumption:

```
GET /v1/context/{session_id}?limit=20&node_types=tool_call,observation&order=causal
```

Response:
```json
{
  "session_id": "sess-xyz",
  "context_items": [
    {
      "node_id": "node-001",
      "type": "ToolCall",
      "tool_name": "web_search",
      "occurred_at": "2026-02-07T10:15:00Z",
      "provenance": {
        "event_id": "evt-101",
        "agent_id": "agent-1",
        "trace_id": "trace-abc"
      }
    }
  ],
  "pagination": { "cursor": "...", "has_more": true },
  "meta": { "items_returned": 20, "query_ms": 45 }
}
```

Key: **Causal ordering** (topological sort) as default, not just chronological.

### `POST /v1/query/subgraph`

Structured query body:
```json
{
  "entry_points": ["node-abc-123"],
  "traversal": {
    "direction": "outbound",
    "max_depth": 4,
    "max_fan_out": 25,
    "edge_types": ["PRODUCED", "DERIVED_FROM"],
    "node_types": ["ToolCall", "Artifact"]
  },
  "filters": {
    "time_range": { "start": "...", "end": "..." },
    "agent_ids": ["agent-1"]
  },
  "budget": {
    "max_nodes": 200,
    "timeout_ms": 2000
  }
}
```

Response includes `truncated` boolean and `truncation_reason` when budget is hit.

### `GET /v1/nodes/{node_id}/lineage`

```
GET /v1/nodes/{node_id}/lineage?direction=both&depth=3&limit=50
```

Response: flat node map + edges array + per-node provenance (Atlas pattern).

### Bounded Retrieval Defaults

| Budget Layer | Default | Maximum |
|---|---|---|
| Depth limit | 3 | 10 |
| Node count | 100 | 1,000 |
| Timeout | 2,000ms | 10,000ms |
| Fan-out per node | 25 | 100 |

### Provenance in Responses

Every returned node carries inline provenance mapping back to source events:
```json
"provenance": {
  "event_id": "evt-001",
  "event_type": "tool_call_completed",
  "occurred_at": "2026-02-07T10:30:00Z",
  "session_id": "sess-xyz",
  "agent_id": "agent-1",
  "trace_id": "trace-abc"
}
```

### API Versioning

- URL path versioning (`/v1/`) — simple, industry-standard
- Design for additive evolution (clients MUST ignore unknown fields)
- Include `api_version` in response envelope
- Never remove/rename fields within a version

---

## Cross-Cutting Recommendations

### Immediate (MVP)

1. **Enhance event schema** — add `parent_event_id`, `ended_at`, `status`, `schema_version`, `global_position`, `ingested_at`
2. **Postgres event table** with `global_position BIGSERIAL` + `INSERT ON CONFLICT DO NOTHING`
3. **Separate payload table** with `PayloadStore` abstraction
4. **Polling + LISTEN/NOTIFY projection worker** (custom asyncio, not Celery)
5. **UNWIND + MERGE** for idempotent Neo4j writes
6. **Docker Compose** (Postgres 16 + Neo4j 5 Community + APOC) — single `docker compose up`
7. **Prometheus metrics** for projection lag from day one
8. **Structured REST API** with Atlas-pattern responses and three-layer query budgets

### Near-Term

9. **Evaluate Apache AGE** — prototype top 3 graph queries in both Neo4j and Postgres
10. **OTel ingestion adapter** — map OTel spans to event schema for ecosystem interoperability
11. **Event upcasting** — schema_version + pure-function upcasters at read time
12. **Projection rebuild CLI** — `python -m worker replay --from-scratch`

### Future Scale

13. **CDC (Debezium)** — when polling latency becomes a bottleneck
14. **Postgres partitioning** — monthly range partitions when > 50M events
15. **Worker sharding** — partition by session_id for parallel projection
16. **Message queue** — Redis Streams or NATS when 3+ consumers needed
17. **Blue-green projection rebuilds** — zero-downtime schema evolution

---

## Referenced Projects and Standards

| Project | Relevance |
|---|---|
| [OpenLineage](https://openlineage.io/) | Closest architectural precedent (event-sourced lineage) |
| [W3C PROV](https://www.w3.org/TR/prov-dm/) | Provenance vocabulary for graph relationships |
| [OpenTelemetry GenAI SIG](https://opentelemetry.io/) | Semantic conventions for LLM tracing |
| [message-db](https://github.com/message-db/message-db) | Reference Postgres event store schema |
| [Apache Atlas](https://atlas.apache.org/) | Lineage API design (flat map + edges) |
| [Marquez](https://marquezproject.ai/) | OpenLineage reference implementation |
| [DataHub](https://datahubproject.io/) | GraphQL lineage API with degree/paths |
| [Langfuse](https://langfuse.com/) | Open-source LLM observability (data model reference) |
| [Apache AGE](https://age.apache.org/) | Postgres graph extension (dual-store alternative) |
| [Memgraph](https://memgraph.com/) | Lightweight Neo4j alternative (Bolt-compatible) |
