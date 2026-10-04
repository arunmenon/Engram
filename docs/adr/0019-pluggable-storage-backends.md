# ADR-0019: Pluggable Storage Backends — Ingestion and Retrieval Decoupled from Redis, Neo4j and Spanner

Status: **Proposed** (draft for review)
Date: 2026-10-04
Amends: ADR-0003 (dual store), ADR-0010 (Redis event store), ADR-0018 rule 11 (backend neutrality, generalised here to every store)
Related: `docs/research/2026-10/ontology/spanner-design-brief.md` (phase 0 of that plan is this ADR)

## Context

Engram must be able to swap its storage backends without changing ingestion, projection or retrieval: Redis or Spanner for the event ledger; Neo4j or Spanner Graph for the graph; and whatever serves keyword and vector search. Hexagonal ports exist (`ports/`), but measured on the current code, five kinds of coupling defeat them:

| # | Coupling | Where (measured 2026-10-04) |
|---|---|---|
| C1 | Workers talk to Redis directly | `worker/consumer.py` (7 raw calls: `XREADGROUP`, `XACK`, `XPENDING`, `XAUTOCLAIM`, …); `projection.py`, `extraction.py`, `enrichment.py` call `JSON.GET` / `XRANGE`; 6 worker modules import `redis.asyncio` |
| C2 | Backends are chosen in code, not configuration | `api/app.py` and `worker/__main__.py` import and construct `RedisEventStore` and `Neo4jGraphStore` by name |
| C3 | Retrieval logic lives inside a backend | `adapters/neo4j/retrieval.py` (727 lines) holds the backend-neutral pipeline: seed channels, fusion, PPR, MMR, Atlas assembly |
| C4 | Ports are shaped by today's backends | `GraphStore` 20 methods, `UserStore` 13, `MaintenanceStore` 10, many mirroring individual Cypher queries; keyword search sits on `EventStore.search_bm25` because RediSearch happens to hold it; vector search sits on the graph because Neo4j holds the index |
| C5 | Backend details leak into contracts | `global_position` is a Redis stream id (parsed in `adapters/redis/trimmer.py`); admin and health responses use keys `redis` and `neo4j`; settings are `RedisSettings`/`Neo4jSettings` at the top level |

## Decision

### 1. Five narrow storage capabilities, each a port

| Port | Responsibility | Today's backend | Candidate backends |
|---|---|---|---|
| `EventLog` | append (idempotent, returns an opaque `Position`); read by id; read a session in order; read after a cursor | Redis Streams + RedisJSON | Spanner, Postgres, Kafka + object store |
| `Subscription` | consumer groups over the `EventLog`: fetch next batch for a group, commit cursor, retry and dead-letter failed events | Redis consumer groups | Spanner checkpoints table, Pub/Sub, Kafka consumer groups |
| `GraphStore` | the generic operations of ADR-0018 (`upsert_nodes`, `upsert_edges`, `transition`, `get_node`, `neighbors(seeds, edge_types, direction, limit)`, `delete`), plus named query plugins | Neo4j | Spanner Graph, in-memory |
| `KeywordIndex` | index text fields; BM25-style search returning ids and scores | RediSearch | Spanner full-text, OpenSearch, Postgres FTS |
| `VectorIndex` | upsert embeddings; nearest neighbours by id | Neo4j vector index | Spanner vector index, pgvector, a vector database |

`ArchiveStore` (exists) stays as is. `UserStore` and `MaintenanceStore` are folded into `GraphStore` generic operations plus named query plugins over time; their current methods stay as thin wrappers until then (frozen-contract rule: nothing removed, only added).

All port types are backend-neutral: `Position` and `NodeId` are opaque ordered strings; no driver types, no query text, no backend error types cross a port.

### 2. Engram's own logic lives above the ports

- **Ingestion pipeline**: validate, then `EventLog.append`. Unchanged API.
- **Consumers**: one base class over `Subscription`; the four workers read events only through `EventLog`. No worker imports a backend library.
- **Projection**: the ADR-0018 generic projector, writing through `GraphStore`.
- **Retrieval engine**: moved out of `adapters/neo4j/retrieval.py` into a backend-neutral module (`retrieval/`), composing `KeywordIndex`, `VectorIndex` and `GraphStore.neighbors`, then fusion, PPR, MMR and Atlas assembly.

### 3. Capability declarations and fast paths

Each backend declares what it does natively (`native_vector`, `native_fulltext`, `multi_hop_in_one_query`, `transactions_across_ports`, `max_path_depth`). The core never assumes a capability it was not given. A backend may offer a **fast path** for a named operation (for example, one query that expands neighbours for 50 seeds); every named operation also has a **generic fallback** built from the basic port methods. So a new backend works on day one and gets faster as fast paths are added.

### 4. Selection by configuration, through a registry

```
CG_STORAGE__EVENT_LOG=redis          # redis | spanner | memory
CG_STORAGE__SUBSCRIPTION=redis
CG_STORAGE__GRAPH=neo4j              # neo4j | spanner | memory
CG_STORAGE__KEYWORD_INDEX=redis
CG_STORAGE__VECTOR_INDEX=neo4j
```

Backends register factories in a registry (`adapters/registry.py`; later Python entry points for out-of-tree backends). The API and worker entry points ask the registry; they never import an adapter by name. Each backend's settings live under its own section (`CG_REDIS__…`, `CG_NEO4J__…`, `CG_SPANNER__…`); existing variable names keep working.

### 5. One conformance suite per port

A backend is supported only if it passes the port's conformance suite: same inputs, same answers, including ordering within a session, idempotent append, cursor and retry behaviour, and graph answers on the PDLC question set. The suite runs in CI for every registered backend.

### 6. An in-memory reference backend

An in-memory implementation of all five ports serves three purposes: fast unit tests, a reference for the conformance suite, and proof that nothing above the ports secretly depends on Redis or Neo4j.

### 7. Moving between backends

- **Graph, keyword and vector indexes** are derived. Switching them is a rebuild by replaying the `EventLog` (and the archive) into the new backend, then switching configuration.
- **EventLog** is the source of truth. Switching it uses a generic copy tool built only on the `EventLog` port: read from the old backend in order, append to the new one with the old position kept as `legacy_position`, then dual-write and cut over (spanner-design-brief.md phase 3).

### 8. Enforced boundaries

CI fails if any module outside `adapters/` imports `redis`, `neo4j`, `google.cloud.spanner` or another backend library (ruff banned-imports or import-linter). Admin and health responses report `{"event_log": {"backend": "redis", …}, "graph": {"backend": "neo4j", …}}`; the old `redis`/`neo4j` keys stay for one deprecation period.

## Consequences

Positive:
- Swapping or adding a backend is configuration plus an adapter that passes the suite.
- Spanner, or any later choice, stops being a rewrite of Engram.
- Retrieval logic becomes testable without databases.

Negative:
- An abstraction cost. Generic fallbacks are slower than hand-tuned queries until fast paths exist.
- Some backend strengths, such as cross-port transactions in a single Spanner database, are used only through declared capabilities, never assumed.
- About 2–3 engineer-weeks of refactoring before any new backend:
  - workers onto ports (C1);
  - registry and entry points (C2);
  - retrieval extraction (C3);
  - keyword and vector ports split out (C4);
  - opaque positions and neutral health keys (C5);
  - in-memory backend and conformance suites.

## Order of work

1. Boundaries: workers and API onto ports; registry; import ban in CI; neutral health keys. No behaviour change.
2. Ports narrowed: `Subscription`, `KeywordIndex` and `VectorIndex` split out; retrieval engine extracted.
3. Proof: in-memory backend passes the conformance suites alongside Redis and Neo4j.
4. Then any new backend (Spanner first, per the design brief).

## Alternatives considered

- **Keep today's ports and only add a Spanner adapter.** Rejected: C1–C3 mean workers, startup and retrieval would still need editing, and the next backend would repeat it.
- **One generic "database" port for everything.** Rejected: ledger, subscription, graph and search have different guarantees. One port would either leak or reduce everything to the weakest store.
- **An ORM or graph abstraction library** (for example a multi-backend Cypher/GQL layer). Rejected for now: none covers ledger, subscription and search together, and it would add a dependency that becomes the new coupling.
