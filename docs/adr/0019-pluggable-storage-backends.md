# ADR-0019: Pluggable Storage Backends — Ingestion and Retrieval Decoupled from Redis, Neo4j and Spanner

Status: **Proposed** (draft, revised after one review pass — see the end)
Date: 2026-10-04
Amends: ADR-0003 (dual store), ADR-0010 (Redis event store), ADR-0014 (archival, for retention), ADR-0018 rule 11 (backend neutrality, generalised here to every store)
Related: `docs/research/2026-10/ontology/spanner-design-brief.md` (phase 0 of that plan is this ADR)

## Context

Engram must be able to swap its storage backends without changing ingestion, projection or retrieval: Redis or Spanner for the event ledger; Neo4j or Spanner Graph for the graph; and whatever serves keyword and vector search. Hexagonal ports exist (`ports/`), but measured on the current code, eight kinds of coupling defeat them:

| # | Coupling | Where (measured 2026-10-04) |
|---|---|---|
| C1 | Workers talk to Redis directly | `worker/consumer.py` (7 raw calls: `XREADGROUP`, `XACK`, `XPENDING`, `XAUTOCLAIM`, …); `projection.py:162`, `enrichment.py:73`, `extraction.py:87,222` call `JSON.GET`; `extraction.py:196` calls `XRANGE` on the per-session stream; 6 worker modules import `redis.asyncio` |
| C2 | Backends are chosen in code, not configuration | `api/app.py` and `worker/__main__.py` import and construct `RedisEventStore`, `Neo4jGraphStore` and `RedisRetentionManager` by name; archive is the one store already chosen by configuration (`ArchiveSettings.backend = fs | gcs`) |
| C3 | The graph adapter is the composition root of retrieval | `Neo4jGraphStore` is constructed with the event store, embedding service, intent classifier and LLM client (`api/app.py:92-100`); `adapters/neo4j/retrieval.py` (727 lines) holds the backend-neutral pipeline (seed channels, fusion, PPR, MMR, Atlas assembly) and runs inline Cypher through the driver it carries |
| C4 | Ports are shaped by today's backends | `GraphStore` port has 20 methods, while the Neo4j adapter exposes 49 public methods, including merges absent from the port; `UserStore` 13 and `GraphMaintenance` 10 methods mirror individual queries; keyword search sits on `EventStore.search_bm25` because RediSearch holds it; vector search sits on the graph because Neo4j holds the index |
| C5 | Backend details leak into contracts | `global_position` is a Redis stream id (parsed in `adapters/redis/trimmer.py`); admin and health responses use keys `redis` and `neo4j` |
| C6 | **Query text crosses a port** | `GraphMaintenance.run_session_query(cypher, params)` (`ports/maintenance.py:78`) carries raw Cypher from `api/routes/admin.py:150,240,339` (including `MATCH (n) DETACH DELETE n`) and `worker/consolidation.py:175,186,234` |
| C7 | Retention is Redis-shaped | `ports/retention.py` takes `stream_key`, `key_prefix`, `dedup_key` |
| C8 | Generic consumer configuration lives in Redis settings | stream name, consumer group names and `block_timeout_ms` sit on `RedisSettings` (`CG_REDIS_` prefix) and every worker reads them there |

## Decision

### 1. Five storage ports, each with an explicit contract

| Port | Responsibility | Today's backend | Candidate backends |
|---|---|---|---|
| `EventLog` | append (idempotent, returns an opaque `Position`; a duplicate returns the existing position); `get_by_id` and `get_many(ids)`; `read_session(session_id)` in order; `read_after(cursor, limit)`; hot-tier retention: `trim(before: Position)`, `expire(before: datetime)` | Redis Streams + RedisJSON | Spanner, Postgres, Kafka + object store |
| `Subscription` | consumer groups over the `EventLog` (contract below) | Redis consumer groups | Spanner checkpoint table; Kafka or Pub/Sub only where they meet the contract |
| `GraphStore` | the generic operations of ADR-0018 (`upsert_nodes`, `upsert_edges`, `transition`, `get_node`, `neighbors(seeds, edge_types, direction, limit)`, `delete`), `ensure_schema()`, and named operations | Neo4j | Spanner Graph, in-memory |
| `KeywordIndex` | index text fields; search returning ids, rank and a score normalised to 0–1 | RediSearch | Spanner full-text, OpenSearch, Postgres FTS |
| `VectorIndex` | upsert embeddings (declared dimension); nearest neighbours returning ids, rank and a score normalised to 0–1 | Neo4j vector index | Spanner vector index, pgvector, a vector database |

`ArchiveStore` (exists) joins the same registry; its current `fs | gcs` setting becomes registry selection.

**Subscription delivery contract.**
- A delivered item is a batch of `(event_id, Position)`. Workers fetch event bodies with `EventLog.get_many`. This replaces the stream-id-then-`JSON.GET` pattern in C1.
- Delivery is at least once.
- Order is preserved within a session; there is no order across sessions. No worker relies on cross-session order today; this is confirmed per worker in step 1.
- Commits are per group.
- Failed events are retried on a schedule, then dead-lettered.
- A cursor never waits on a failed event.

**Named operations replace query text.** No port method takes query text. Each current `run_session_query` call becomes a named `GraphStore` operation, such as `session_agent`, `session_summary_candidates` and `delete_all`. The last is admin-only and guarded. Every named operation has a generic fallback built from the basic operations and may have a backend fast path.

**Contracts every port states**, and the conformance suite tests:
- **Errors:** one neutral exception set (`Conflict`, `NotFound`, `Unavailable`, `Timeout`, `InvalidRequest`). No driver exceptions cross a port.
- **Consistency:** read-your-writes is stated per port. For example, `EventLog.append` then `get_by_id` must see the event; graph projections are eventually consistent with the log.
- **Pagination:** each port declares its cursor type. Positions for the log, opaque tokens for graph and search. Offsets are never exposed.
- **Scores:** search ports return rank and a 0–1 score, so fusion (RRF) does not depend on BM25 versus cosine scales.

All port types are backend-neutral: `Position`, `NodeId` and cursors are opaque strings; no driver types, query text or backend errors cross a port.

`UserStore` and `GraphMaintenance` keep their current methods as thin wrappers over `GraphStore` generic and named operations (frozen-contract rule: nothing removed, only added; `run_session_query` is deprecated, not deleted, until its callers are gone).

### 2. Engram's own logic lives above the ports

- **Ingestion pipeline**: validate, then `EventLog.append`. Unchanged API.
- **Consumers**: one base class over `Subscription`; workers read events only through `EventLog`. No worker imports a backend library.
- **Projection**: the ADR-0018 generic projector, writing through `GraphStore`.
- **Retrieval engine**: moved out of `adapters/neo4j/retrieval.py` into a backend-neutral module (`retrieval/`). It owns its dependencies (embedding service, intent classifier, LLM client, the event log for bodies) and composes `KeywordIndex`, `VectorIndex` and `GraphStore`, then fusion, PPR, MMR and Atlas assembly. `GraphStore` constructors take only their own settings.

### 3. Capability declarations and fast paths

Each backend declares what it does natively:
- `native_vector`, `vector_dimensions`, `native_fulltext`;
- `multi_hop_in_one_query`, `max_path_depth`;
- `transactions_across_ports`, `max_batch_size`;
- `ordered_within_session`, `per_message_retry`.

The core never assumes a capability it was not given. A backend that cannot meet a port's contract (for example, a message bus without per-message retry for `Subscription`) is not a valid backend for that port. Fast paths are optional. Every named operation works through its generic fallback.

### 4. Selection by configuration, through a registry

New settings section, additive to the frozen `settings.py`, using the file's existing single-underscore style:

```
CG_STORAGE_EVENT_LOG=redis          # redis | spanner | memory
CG_STORAGE_SUBSCRIPTION=redis
CG_STORAGE_GRAPH=neo4j              # neo4j | spanner | memory
CG_STORAGE_KEYWORD_INDEX=redis
CG_STORAGE_VECTOR_INDEX=neo4j
CG_STORAGE_ARCHIVE=fs               # fs | gcs (absorbs ArchiveSettings.backend; old setting still honoured)
```

Backend-neutral consumer settings (stream name, group names, `block_timeout_ms`) move to `ConsumerSettings`, with the old `CG_REDIS_` names kept as aliases.

Backends register factories in `adapters/registry.py`; Python entry points can be added later for out-of-tree backends. The registry returns a `Stores` bundle, with one attribute per port. `api/dependencies.py`, `api/app.py` and `worker/__main__.py` use the bundle and never import an adapter by name. Health checks iterate over the bundle, so a store that is split out still gets a health entry.

### 5. One conformance suite per port

A backend is supported only if it passes the port's conformance suite. The suite covers:
- same inputs, same answers;
- idempotent append returning the existing position;
- order within a session, at-least-once delivery, retry and dead-letter;
- the error set, read-your-writes, cursor behaviour and score ranges;
- graph answers on the PDLC question set.

The suite runs in CI for every registered backend.

### 6. An in-memory reference backend

An in-memory implementation of all five ports serves three purposes: fast unit tests, a reference for the conformance suite, and proof that nothing above the ports secretly depends on Redis or Neo4j.

### 7. Moving between backends

- **Graph, keyword and vector indexes** are derived. Switching is a rebuild by replaying the `EventLog` (and the archive) into the new backend, then switching configuration.
- **EventLog** is the source of truth. Switching uses a generic copy tool built only on the `EventLog` port: read in order, append to the new backend with the old position kept as `legacy_position`, complete the copy before dual-writing new events, then cut over (spanner-design-brief.md phase 3).

### 8. Enforced boundaries

CI fails if any module outside `adapters/` imports `redis`, `neo4j`, `google.cloud.spanner` or another backend library (ruff banned-imports or import-linter). Admin and health responses report `{"event_log": {"backend": "redis", …}, "graph": {"backend": "neo4j", …}}`; the old `redis`/`neo4j` keys stay for one deprecation period.

## Consequences

Positive:
- Swapping or adding a backend is configuration plus an adapter that passes the suite.
- Spanner, or any later choice, stops being a rewrite of Engram.
- Retrieval logic becomes testable without databases.
- The admin graph wipe stops being raw query text.

Negative:
- An abstraction cost. Generic fallbacks are slower than hand-tuned queries until fast paths exist.
- Backend strengths, such as cross-port transactions in a single Spanner database, are used only through declared capabilities, never assumed.
- About 5–7 engineer-weeks before any new backend (see below), not the 2–3 first estimated.

## Order of work

| Step | Work | Behaviour change | Estimate |
|---|---|---|---|
| 1. Boundaries | `Stores` bundle and registry (archive included); `StorageSettings` and consumer-settings aliases; workers read through `EventLog` and a Redis-backed `Subscription` (C1, C8); retention behind `EventLog.trim/expire` (C7); neutral health keys alongside old ones (C5); CI import ban | none | 1.5–2 weeks |
| 2. Ports narrowed | named operations replace every `run_session_query` call (C6); `KeywordIndex` and `VectorIndex` split out with normalised scores (C4); retrieval engine extracted and given its own dependencies (C3); neutral exception set | admin wipe and consolidation queries move to named operations; responses must stay identical (checked by the suite) | 2–2.5 weeks |
| 3. Proof | conformance suites for all five ports; in-memory backend passes them alongside Redis and Neo4j | none | 1.5–2.5 weeks |
| 4. New backends | Spanner first, per the design brief | none for callers | per the brief |

## Alternatives considered

- **Keep today's ports and only add a Spanner adapter.** Rejected: C1–C3 and C6 mean workers, startup, retrieval and admin would still need editing, and the next backend would repeat it.
- **One generic "database" port for everything.** Rejected: ledger, subscription, graph and search have different guarantees. One port would either leak or reduce everything to the weakest store.
- **An ORM or graph abstraction library** (for example a multi-backend Cypher/GQL layer). Rejected for now: none covers ledger, subscription and search together, and it would add a dependency that becomes the new coupling.

## Review pass (2026-10-04)

One independent review (Fable 5.1, short pass). All 12 findings were checked against the code and applied:

| # | Finding | Severity | Change made |
|---|---|---|---|
| 1 | raw Cypher crosses `GraphMaintenance.run_session_query`, including an admin graph wipe | blocking | C6 added; named operations replace it in step 2 |
| 2 | the log-to-worker hand-off was undefined (workers fetch bodies with `JSON.GET`, session reads with `XRANGE`) | blocking | `get_many` and `read_session` on `EventLog`; explicit delivery contract |
| 3 | settings scheme conflicted with frozen `settings.py` style; consumer config lives in Redis settings | blocking | single-underscore `CG_STORAGE_*`; consumer settings moved with aliases (C8) |
| 4 | the graph adapter is the retrieval composition root | should-fix | C3 restated; retrieval engine owns its dependencies |
| 5 | retention port is Redis-shaped | should-fix | C7; `trim`/`expire` on `EventLog` |
| 6 | dependency wiring has no slot for split-out stores | should-fix | `Stores` bundle; health iterates it |
| 7 | score scales and cursor types unspecified | should-fix | normalised 0–1 scores plus rank; cursor type per port |
| 8 | error, consistency and schema-setup semantics missing | should-fix | neutral exception set, read-your-writes per port, `ensure_schema()` |
| 9 | archive already has its own backend switch | should-fix | archive joins the registry |
| 10 | capability list incomplete; some candidates can't meet the contract | minor | capabilities added; backends must meet the port contract |
| 11 | inventory measured the port, not the adapter | minor | 49 adapter methods vs 20 port methods noted |
| 12 | 2–3 weeks not credible; step 1 couldn't be "no behaviour change" | minor | re-estimated per step (5–7 weeks); query removal moved to step 2 |

Reviewer's verdict: fit to approve after fixing 1–3 and acknowledging 4–9 in the order of work. All twelve are now addressed.

## Step 1 implementation (2026-10-04)

Step 1 (boundaries) is implemented with no intended behaviour change. The status line above is left for the owner to change.

| Item | Where | Notes |
|---|---|---|
| `Subscription` port | `ports/subscription.py`; Redis: `adapters/redis/subscription.py` | XGROUP, XAUTOCLAIM, XPENDING, XREADGROUP, XACK, the DLQ stream and XINFO lag moved unchanged out of `worker/consumer.py`. `BaseConsumer` now takes a `Subscription` and imports no backend. |
| `EventLog` port (C1) | `ports/event_log.py` (extends the frozen `EventStore`); Redis: new methods on `RedisEventStore` | `get_documents(ids)` returns stored documents (event fields plus `payload`), because extraction needs payloads; this is the `get_many` of §1. `read_session_ids(session_id)` is the step-1 form of `read_session`. Same `JSON.GET`/`XRANGE` commands as before. |
| Retention (C7) | `EventLog.trim`, `expire`, `housekeep` | Consolidation passes ages and group names only. Keys, streams and the dedup set stay in the Redis adapter. `RetentionManager` and `RedisRetentionManager` remain (frozen) but nothing uses them. |
| Settings (C8) | `StorageSettings` (`CG_STORAGE_*`); `ConsumerSettings.source`, `group_*`, `block_timeout_ms` | A consumer value not set directly falls back to its old `CG_REDIS_*` name. `CG_STORAGE_ARCHIVE` falls back to `CG_ARCHIVE_BACKEND`. |
| Registry and `Stores` | `adapters/registry.py` | `open_stores()` validates backend names before connecting. Workers share one Redis client between the event log and subscriptions. `api/app.py` and `worker/__main__.py` no longer import storage adapters. Retrieval dependencies still reach the graph store through `graph_options` until step 2 (C3). |
| Health (C5) | `/v1/health`, `/v1/admin/health/detailed`, `/v1/admin/stats` | `event_log` and `graph` keys name the backend. The old `redis`/`neo4j` keys stay, marked deprecated. |
| Import ban (§8) | `tests/unit/test_hex_purity.py` | No module outside `adapters/` may import `redis`, `neo4j` or `google.cloud`, or a storage adapter by name. Enforced as a unit test, so it runs in CI. |

**Evidence of no behaviour change:**
- Consumer, projection, enrichment and extraction tests now build the workers over the Redis adapters with the same mocked Redis client. Their Redis-call assertions are unchanged.
- The retention commands are pinned in `tests/unit/test_redis_event_log.py`.
- A live run against `redis-server` matched: messages processed and acknowledged, the failing message dead-lettered, nothing left pending.

**Two existing bugs found, not fixed here:**
- The pending drain re-reads a message that keeps failing in a tight loop until the worker stops.
- The lag gauge never updates, because `XINFO GROUPS` returns the group name as bytes.

Both predate this change; they are queued separately.

**Remaining for step 2:**
- Consolidation still reads hot-tier ages from `settings.redis`.
- `Stores.graph` is typed as the Neo4j adapter, because callers use it as `GraphMaintenance` and `UserStore` too.

## Step 2 implementation (2026-10-04)

Step 2 (ports narrowed) is implemented. API responses are unchanged: existing retrieval, admin and worker tests pass unmodified, or with only their mock wiring changed.

| Item | Where | Notes |
|---|---|---|
| Neutral errors | `ports/errors.py`; `adapters/errors.py` (`translate_errors` class decorator); `adapters/{redis,neo4j}/errors.py` | `StorageError` with `ConflictError`, `NotFoundError`, `UnavailableError`, `StorageTimeoutError` (also a built-in `TimeoutError`) and `InvalidRequestError`. The `Error` suffix follows the repo's lint rule (N818). Public coroutine methods of every storage adapter translate driver exceptions and chain the original. Unhandled errors still become a 500, so responses are unchanged. |
| Named operations (C6) | `GraphMaintenance.session_agent_id`, `session_events`, `session_event_timeline`, `events_for_pruning`, `delete_all(confirm=True)` | The six raw-Cypher calls in consolidation and admin are gone. Each operation sends the same Cypher, pinned in `test_named_graph_operations.py`. `delete_all` refuses unless `confirm=True`. `run_session_query` stays on the frozen port, marked deprecated. A test fails if anything outside `adapters/` calls it. |
| Search ports (C4) | `ports/search.py` (`SearchHit(id, rank, score)`, `KeywordIndex`, `VectorIndex`); `adapters/search.py` | Scores are in 0–1. The vector index returns cosine (native). The keyword index derives its score from rank, because `search_bm25` returns no scores, and says so via `scores_are_native`. RRF fuses on rank only, so seeds are unchanged. |
| Retrieval engine (C3) | `retrieval/engine.py`, `retrieval/atlas.py`; `ports/graph_reads.py` (`GraphReads`); `adapters/neo4j/graph_reads.py`; `ports/retrieval.py` | `get_subgraph`, `get_context` and `get_lineage` moved unchanged into a backend-neutral engine. It composes `GraphReads`, `KeywordIndex` and `VectorIndex` and owns the embedding service, intent classifier, LLM client and settings. The Neo4j reads send the Cypher that was inline before. A test bans adapter imports from `retrieval/`, and engine tests run it on in-memory fakes. |
| Compatibility | `adapters/neo4j/retrieval.py`; `Neo4jGraphStore.get_*` | `RetrievalPipeline(RetrievalDeps(...))` is now a thin subclass of the engine, and the store's frozen query methods delegate to it. The existing pipeline, timeout and hybrid-retrieval tests pass unmodified. |
| API wiring | `api/app.py`, `api/dependencies.get_retrieval` | The app builds `RetrievalEngine` from the `Stores` bundle. The context, lineage and query routes depend on the `Retrieval` port; their HTTP contract is unchanged, but their injected dependency changed (`query.py` is a frozen file, and only that line changed). The graph store is opened with only its own settings (`Neo4jSettings`, `QuerySettings`). |
| Step-1 leftovers | `ports/graph_backend.py`; `RetentionSettings.log_*` | `Stores.graph` is typed `GraphBackend` (GraphStore + GraphMaintenance + UserStore + `reads`), and mypy confirms the Neo4j adapter satisfies it. Hot-tier ages moved to `CG_RETENTION_LOG_*`, falling back to the old `CG_REDIS_*` names. |

**Behaviour notes:**
- Workers now open the graph store with `QuerySettings`, so `CG_QUERY_DEFAULT_TIMEOUT_MS` also bounds the extraction worker's entity vector search. The defaults are unchanged.
- Consolidation skips a session whose events carry no `agent_id`. The field is required on ingest, so this cannot occur with valid data.

**Not done in step 2:**
- Generic fallbacks for named operations, built from the basic operations, come with the in-memory backend in step 3.
- `VectorIndex` covers queries only; embedding writes still go through `GraphStore.store_event_embedding`.
- The extraction worker still calls `search_similar_entities` directly (entity resolution, not retrieval).
- Not run against a live Neo4j: no Docker daemon in this environment. Equivalence rests on the pinned Cypher and the unchanged tests.

## Step 3 implementation (2026-10-04)

Step 3 (proof) is implemented: conformance suites for all five ports, and an in-memory backend that passes them alongside Redis and Neo4j.

| Item | Where | Notes |
|---|---|---|
| In-memory backend | `adapters/memory/` (`log.py`, `stream.py`, `subscription.py`, `graph.py`) | Every port, selected with `CG_STORAGE_*=memory`. Semantics mirror the Redis and Neo4j adapters operation by operation: MERGE, None-removes-property, missing endpoints, ordering, consumer groups, dedup, retention. Single process, not durable. |
| Conformance suites | `tests/conformance/` | EventLog (18 cases), Subscription (15), GraphStore + GraphMaintenance (24), UserStore (8), GraphReads (17, including the engine on each backend's reads), KeywordIndex / VectorIndex (3). Each runs per backend: memory always; Redis and Neo4j marked `integration`. |
| CI | `.github/workflows/ci.yml` (pending) | Intended: the unit job runs the memory suites, and the integration job runs the Redis Stack and Neo4j suites with `CG_CONFORMANCE_REQUIRE_SERVICES=1`, so a missing service fails rather than skips. Not yet in the workflow: the session's GitHub App may not edit workflow files, so the two steps must be added by a person (see the step-3 hand-off). |
| End-to-end proof | `tests/unit/test_memory_backend_end_to_end.py` | With every backend set to `memory`, events are ingested through the API and drained by the real projection and enrichment workers. Context, lineage, subgraph and health then answer through the real routes and engine. |

**Results in this environment:**
- **Memory:** every suite passes.
- **Neo4j 5.26** (in-process server from Maven Central's `neo4j-harness`): all 51 graph conformance cases pass, and all 69 existing Neo4j integration tests pass. This is the first live check of the step-2 Cypher.
- **Redis 7.0 (plain):** the Subscription suite passes.
- **Not run here:** the Redis event-log suite needs RedisJSON and RediSearch, which are not installable in this environment. CI's `redis-stack` service runs it.

**Defects the suites found, fixed here:**
- `RedisStreamSubscription.read_new(count, 0)` blocked forever, because `XREADGROUP BLOCK 0` means "wait indefinitely" in Redis while the port says "do not wait". `BLOCK` is now omitted when `block_ms <= 0`. Workers always pass a positive timeout, so production was not affected.
- `RedisStreamSubscription.lag()` always returned None: `XINFO GROUPS` returns the group name as bytes. Now decoded; the consumer-lag metric works.
- Step 2 removed `Neo4jGraphStore._bump_access_counts`, which an integration test still calls; restored as a delegate to the graph reads.

**Known gaps:**
- **Keyword (BM25) channel:** RediSearch indexes `$.summary` and `$.keywords` on event documents, but ingested events never carry those fields (the `Event` model has neither), so the keyword seed channel finds nothing in practice. The memory backend mirrors this; the suite exercises the index by writing those fields directly. Making the channel useful needs a decision on what text events should carry.
- **PDLC question set:** "graph answers on the PDLC question set" (§5) waits for the ADR-0018 generic projector; the ontology packs are not implemented yet.
- **Generic operations:** the ADR-0018 generic graph operations (`upsert_nodes`, `neighbors`, …) and generic fallbacks for named operations are not added. Each backend implements the named operations directly; the memory backend shows what a fallback would compute.
