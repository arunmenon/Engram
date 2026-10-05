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
- **EventLog** is the source of truth. Switching uses a generic copy tool built only on the `EventLog` port: read in order, append to the new backend with the old position kept as `legacy_position`, complete the copy before new events reach the new backend, then cut over (spanner-design-brief.md phase 3). New events reach it by mirroring the old log in order, not by the API writing to both (see "Phase 3 implementation" below).

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
- **Keyword (BM25) channel:** RediSearch indexes `$.summary` and `$.keywords` on event documents, but ingested events never carry those fields (the `Event` model has neither), so the keyword seed channel finds nothing in practice. The memory backend mirrors this; the suite exercises the index by writing those fields directly. Making the channel useful needs a decision on what text events should carry. *(Resolved: see "Keyword channel fix" below.)*
- **PDLC question set:** "graph answers on the PDLC question set" (§5) waits for the ADR-0018 generic projector; the ontology packs are not implemented yet.
- **Generic operations:** the ADR-0018 generic graph operations (`upsert_nodes`, `neighbors`, …) and generic fallbacks for named operations are not added. Each backend implements the named operations directly; the memory backend shows what a fallback would compute.

## Step 4 implementation: Spanner on the emulator (2026-10-04)

Spanner is a registered backend for all five ports (`CG_STORAGE_*=spanner`), built to the Spanner design brief and verified on the Cloud Spanner emulator (1.5.58, `google-cloud-spanner` 3.71). No GCP resources were created.

| Item | Where | Notes |
|---|---|---|
| Schema | `adapters/spanner/schema.py` | One database. **Ledger:** `Events`, keyed by `event_id`, with a sharded time index `(shard, commit_ts, batch_index)` (D3), a session index, and a full-text search index over `summary` + `keywords`. **Consumer groups:** `ConsumerGroups`, `ConsumerCursors`, `ConsumerDeliveries`, `ConsumerDeadLetters`. **Graph:** schemaless `GraphNodes` / `GraphEdges` (JSON properties, dynamic labels) with `CREATE PROPERTY GRAPH EngramGraph` (D4), plus a cosine vector index on entity embeddings. `CG_SPANNER_CREATE_IF_MISSING` creates the emulator instance and database. |
| EventLog | `adapters/spanner/log.py` | Positions are `<commit ts to ns>/<batch index>/<event id>`, fixed width (D1). Append is one read-write transaction: a live duplicate returns its position, otherwise the row is written with the commit timestamp (G2). Redis's four retention structures map to four flags on one row; a row is deleted once all four are cleared (G7). Keyword search uses `SEARCH`/`SCORE` (G6). |
| Subscription | `adapters/spanner/subscription.py` | Per-group, per-shard cursors; a deliveries table replaces the pending list; claim, retry counts and dead letters as the port requires (G3, G4). Reads poll inside read-write transactions. Spanner locks the ranges a transaction reads, so a producer either commits before the read (and is seen) or after it with a later timestamp: the cursor never skips. This gives D2's guarantee without a separate read-timestamp step. |
| Graph | `adapters/spanner/graph.py`; shared `adapters/graph_ops.py` | The graph methods come from a new generic layer built on eight storage primitives, shared with the memory backend. These are §1's "generic fallbacks". Spanner supplies the primitives (key-range reads, index reads, mutations) and two native fast paths: lineage as a GQL `TRAIL` quantified path (G9) and entity similarity via `APPROX_COSINE_DISTANCE` on the vector index (G10). |
| Search | `adapters/spanner/search.py` | Keyword hits carry Spanner's native `SCORE`, normalised to [0, 1] by the best hit. |
| Errors | `adapters/spanner/errors.py` | google-api-core exceptions map to the neutral set. The error-translation decorator now also wraps inherited methods. |

**Results on the emulator:**
- All 85 conformance cases pass on Spanner (EventLog 18, Subscription 15, GraphStore 24, UserStore 8, GraphReads 17, search 3).
- The end-to-end run passes with every backend set to `spanner`: ingest through the API, the real projection and enrichment workers, then context, lineage, subgraph and health.
- Across all backends: 236 conformance cases pass, with the Redis event-log suite skipped here for lack of Redis Stack; 1444 unit plus conformance tests pass.

**Suite changes:** two assertions encoded Redis details and were relaxed to the port's contract:
- positions were parsed as `<ms>-<seq>`; positions are opaque;
- trim had to keep the group's last delivered entry, a quirk of `XTRIM MINID`.

**How to run locally:**
```
# download the emulator from storage.googleapis.com/cloud-spanner-emulator/releases/<version>/
./gateway_main --hostname 127.0.0.1 --grpc_port 9010 --http_port 9020
pip install -e ".[dev,spanner]"
CG_SPANNER_EMULATOR_HOST=127.0.0.1:9010 pytest tests/conformance -m integration -k spanner
```
`gcloud emulators spanner start` and the `gcr.io/cloud-spanner-emulator/emulator` image work too.

**Still needs a real instance** (design brief phase 2 exit):
- concurrency and fault tests: the emulator runs one read-write transaction at a time;
- load and hotspot checks for D3;
- full-text ranking compared with RediSearch BM25;
- approximate-vector recall at scale;
- confirming the Enterprise-edition requirement and prices.

**Not done:**
- data migration and dual run (brief phase 3): done below;
- the ADR-0018 generic projector for ontology packs;
- the 30 PDLC competency questions as graph conformance cases.

## Phase 3 implementation: migration and dual run (2026-10-04)

Built to the Spanner design brief's phase 3 and §7 above. It runs on the emulator and creates no GCP resources.

**Mirror instead of dual-write.** The brief asked for dual-writing new events once the copy completes. The tool instead **mirrors** the source log: it reads the source in order and imports into the target. The copy and the dual run are the same loop:
- *copy*: run it until caught up;
- *dual run*: keep it running.

The API keeps writing only to the source. Why:
- writes from the API to both stores could race the copy's tail and land out of order (review finding 6); reading the source in order cannot reorder anything;
- a target outage only delays the mirror, and ingest latency is unchanged;
- the target needs no write path of its own until cutover.

The cost: cutover (phase 4) needs a short ingest pause, so the mirror can drain before writes move to the target.

| Item | Where | Notes |
|---|---|---|
| Ordered read | `EventLog.read_after(position, limit)` → `LogEntry` | All three ledgers. Redis: `XRANGE` from an exclusive start. Spanner: `(commit_ts, batch_index, event_id)` order. Expired documents come back as `None` and are skipped. |
| Import | `MigrationTarget`: `append_imported`, `last_legacy_position`, `has_native_events` | Implemented by all three ledgers. One batch keeps source order (Spanner: one transaction with `batch_index`). The source position becomes `legacy_position`; the target assigns its own `global_position`. Imports are idempotent through the normal dedup. |
| Copy and mirror | `migration/mirror.py` (`LogMirror`) | **Checkpoint:** the target itself; a restart resumes after the target's newest `legacy_position`. **Refusal:** it will not start when the target holds native events, since copying then would place migrated events after new ones. |
| Comparison | `migration/compare.py` | **Ledger:** every source event is present, identical apart from position fields, with the right `legacy_position` and in source order. **Graph:** node and edge counts per type, per-session event counts, sampled sessions' event properties and edges, entities. **Retrieval:** the retrieval engine's context and lineage answers over each graph (nodes, edges, decay scores within 0.01). |
| CLI | `python -m context_graph.migration copy\|mirror\|compare --to <backend> [--graph]` | **Source:** the configured `CG_STORAGE_*`. **Target:** the same settings with every port on `--to`. **Exit codes:** 2 when refused; 1 when compare finds divergence. **Settings:** `CG_MIGRATION_*` (batch size, poll interval, sampled sessions). |

The target's graph is not copied. The projection worker, run against the target, builds it from the imported ledger (§7: derived stores are rebuilt).

**Results:**
- **Conformance:** `tests/conformance/test_log_migration.py` covers ordered reads, import order, `legacy_position`, idempotence and native-event detection. It passes on memory and Spanner (90 Spanner cases in all); the Redis cases skip here without Redis Stack, and mocked Redis unit tests cover the commands.
- **Unit:** `tests/unit/test_migration.py` covers copy, resume, refusal, expired documents, the live mirror, divergence detection, graph and retrieval comparison, and the absence of backend imports.
- **Dual run:** `tests/integration/test_dual_run.py` runs the primary as a memory ledger plus live Neo4j, and the secondary as Spanner on the emulator:
  - history is projected on the primary;
  - the copy runs;
  - the secondary's projection worker starts;
  - the mirror runs while new events, including a late event in a migrated session, arrive on the primary;
  - each side's real projection worker builds its graph.

  Ledger, graph and retrieval comparisons all report zero divergence.

**Found by the dual run** (existing worker behaviour, both since fixed; see "Projection worker fixes" below):
- the projection worker keeps each session's last event in memory, so a restart loses the FOLLOWS edge across it, and a rebuilt graph then differs from the live one;
- it flushes its micro-batch only when a later delivery arrives, so an idle tail stays unprojected.

**Also changed:** Spanner retention cutoffs (`trim`, `housekeep`) are now computed from the database clock. They compare commit timestamps, and a skewed application host (or a long-running emulator) otherwise trims or keeps the wrong rows.

**Not done:**
- Soak on real traffic, and the retrieval evals for the BM25 ranking change (brief phase 3 exit). The comparison isolates the graph, and keyword ranking is not compared.
- The GCS archive copy.
- Cutover and the rollback rehearsal (phase 4). The runbook is `docs/runbooks/storage-migration.md`.

## Keyword channel fix (2026-10-04)

The keyword (BM25) seed channel found nothing (see the step 3 findings) for two reasons:
- **Nothing to match:** only `summary` and `keywords` were indexed, and nothing writes them to the ledger. Enrichment writes keywords to the graph node only.
- **Every word had to match:** every backend required all query terms, so a natural-language question almost never matched.

| Change | Where | Notes |
|---|---|---|
| Search text at ingest | `domain/keyword_search.py` (`event_search_text`); `append` in the memory, Redis and Spanner logs | **Contents:** the tool name, then the payload's string values (`content`, `input`, `output` first, then the rest). **Where it lives:** stored as `search_text` on the event document. **Size cap:** `CG_KEYWORD_TEXT_MAX_CHARS` (8000), cut on a word boundary. **Immutability:** written once with the event and never changed afterwards, so the ledger stays immutable (ADR-0004). |
| Indexed on every backend | Redis `$.search_text` TEXT (weight 1.0, after `summary` 2.0 and `keywords` 1.5); Spanner `search_text` column in `text_tokens`; memory scoring | **Redis:** an existing index gets the field via `FT.ALTER` at start-up, and RediSearch re-scans existing documents. **Spanner:** the column is in the DDL for new databases. None exist outside the emulator, so there is no `ALTER` path. |
| Any-term queries | `domain/keyword_search.py` (`query_terms`); `search_bm25` / `search_scored` on every backend | **Terms:** lowercased word tokens, minus RediSearch's default stopwords plus question words, auxiliaries and pronouns, deduplicated, capped by `CG_KEYWORD_MAX_QUERY_TERMS` (16). **Matching:** a document matching any term is a hit, ranked by the backend: Redis BM25 (`(t1\|t2)`), Spanner `SCORE` (`t1 OR t2`), memory a saturating IDF-weighted count. **No terms:** a query of only stopwords searches nothing. |

**Tests:**
- **Conformance** (`test_search_indexes.py`):
  - a question matches events through their payload text, best match first;
  - the session filter and stopword-only queries behave;
  - `search_text` is stored at ingest.
- **Changed case:** "deploy rollback" now returns both deploy events, with the event that has both terms ranked first. It used to return only that event.
- **End to end** (memory and Spanner): through the API, the subgraph query's `bm25` channel returns seeds, and a question about one event's payload finds that event.
- **Redis:** mocked unit tests pin the `FT.SEARCH` query, the stored document and the `FT.ALTER` upgrade. Redis Stack was not available to run the conformance cases.

**Not done:**
- events ingested before this change have no `search_text`; there is no backfill, because no deployment holds history;
- ranking quality is unmeasured; the retrieval evals should cover the channel.

## Projection worker fixes (2026-10-04)

The two worker behaviours the dual run exposed:

- **Idle tail:** the projection worker flushed its micro-batch only when a later delivery arrived. When traffic stopped, up to 49 events stayed unprojected and unacknowledged. `BaseConsumer.run` now calls an `on_idle` hook when a read returns nothing. `ProjectionConsumer.on_idle` flushes a partial batch once the batch timeout has passed. Acks still follow a successful graph write, so a failed idle flush leaves the items pending. This came from a separate session and was cherry-picked.
- **FOLLOWS across restarts:** the worker found each session's previous event only in an in-process cache. After a restart, an eviction, or a second replica, the next event got no FOLLOWS edge. On a cache miss the worker now asks the ledger, which is the source of truth: it reads the session's event ids in log order (`EventLog.read_session_ids`) and fetches the document of the event just before this one. It returns none after a `system.session_end` or when that document has expired, exactly as an uninterrupted run would. A brand-new session costs one read of its own one-entry session index.

**Tests:**
- a restart mid-session gives the same FOLLOWS edges, including `delta_ms`, as one uninterrupted run;
- session end behaves the same on both paths;
- the restart test fails without the fix.

The dual-run test no longer flushes explicitly.

- **Pending drain spinning on a failing item** (cherry-picked from a separate session): on start-up, the consumer recovered its pending items by re-reading from the beginning until nothing came back. An item that kept failing came back on every read, so the drain spun, never dead-lettered it in that run, and never reached new items.
  - **New port argument:** `Subscription.read_pending` takes an optional `after` cursor. Each sweep reads every pending item once, and failures are retried in the next sweep.
  - **Retry limit:** delivery counts include failures seen in this run, so an item past `max_retries` is dead-lettered without a restart.
  - **Bound:** the drain ends after a clean sweep, at most `max_retries + 1` sweeps.
  - **Backends:** the original change covered Redis only. Memory and Spanner now implement the cursor too, and a conformance case pins it for every backend.


## Spanner commit budgets and database opening (2026-10-05)

From the maturity review (`docs/review/2026-10-05-maturity-review-guide.md`, items S5 and S7, review F1 and F4), before a first real-instance trial.

**Database opening** (`adapters/spanner/schema.py`):
- `CG_SPANNER_CREATE_IF_MISSING` used to create the database on any instance; only instance creation was limited to the emulator. It now creates the database on the emulator only. On a real instance it also needs `CG_SPANNER_ALLOW_CREATE_ON_INSTANCE=true`, and instances are never created.
- A missing database raises `SchemaMismatchError` at start-up instead of failing on first use.
- An existing database is checked against the schema the code expects: tables, columns, indexes (search and vector included) and the property graph, read from `INFORMATION_SCHEMA` and parsed from the DDL in `schema_statements`. Anything missing stops start-up with a list. Extra objects are allowed. `CG_SPANNER_CHECK_SCHEMA=false` turns the check off. There is still no `ALTER` path; the check makes a stale database visible.

**Commit budgets** (`adapters/spanner/commits.py`):
- Spanner refuses a commit over 80,000 mutations or 100 MiB, indexes included. Writes were sized by event or item count only.
- Every write that takes a caller's list is now split into transactions under `CommitBudget` (`CG_SPANNER_COMMIT_MAX_MUTATIONS`, 40,000; `CG_SPANNER_COMMIT_MAX_BYTES`, 50 MiB: half of each limit, since costs are estimates). Costs per row come from the schema: columns written plus the columns each index holds; bytes are the values written, counted again per index that stores them.
- **Ledger:** appends and imports are split in order. Commit timestamps keep the order across transactions. `append_batch_outcomes` reports events from a failed later transaction as `failed` and keeps the earlier ones; a failure in the first transaction writes nothing and raises, as before. `append_batch` and `append_imported` raise; the mirror resumes from its checkpoint.
- **Graph:** node, merge, state-change and edge writes are grouped by key, so one key's ordered updates share a transaction, and the groups are packed into budget-sized runs. Stored properties are only known inside the transaction, so a run whose actual rows exceed the budget raises `CommitTooLarge`, rolls back, and is split in two. A single key is written whatever its size. Detach-delete of a node whose incident edges do not fit deletes the edges first in their own transactions, then retries.
- **Retention:** `trim`, `expire`, `housekeep` and the purge ran one unbounded statement each. They now change `CG_SPANNER_RETENTION_BATCH_ROWS` (1,000) rows per transaction until none are left: select ids, then change those rows with the condition checked again. The emulator refuses DML whose subquery reads `Events` itself, hence the two steps. `expire` also reads and archives one batch at a time instead of loading every expired document.

**Tests:** `tests/unit/test_spanner_commits.py`. Unit tests cover budget arithmetic, the expected schema and the creation refusal with a mocked client. Emulator tests use tiny budgets so that every path has to split: ordered appends with a duplicate across transactions, a failed later transaction, retention in batches of two, per-key order in node writes, a run larger than estimated, transitions split by node, and a hub node delete.

**Not covered:** key size limits (8 KiB) are not checked, so an oversized key fails its transaction (and, in projection, dead-letters its event). The estimates have not been compared with Spanner's commit statistics; that is part of the real-instance trial.

## First real-instance trial (2026-10-05)

Results: `docs/review/2026-10-05-spanner-trial-results.md`; script: `scripts/engram_trial.py`.

- **What held.**
  - The schema applies, Enterprise features included.
  - Two consumer groups each got all 2,070 events from 8 concurrent producers, with nothing missing, duplicated or out of session order.
  - Spanner counted 28 mutations per Events row against our estimate of 33.
- **What a real instance showed that the emulator does not:**
  - **Some JSON numbers are refused.** About 1 in 1,000 ordinary floats fails as "cannot round-trip". JSON cells now carry non-integral floats as `{"$float": "<repr>"}`, encoded by `json_param` and decoded by `json_value`.
  - **Dynamic-label filters match nothing in GQL.** The lineage query now filters on the `label` and `edge_type` key columns.
- **Latency.** Each call took about 0.65 s or more from the trial client, including reads that found nothing. That bounds throughput more than Spanner capacity did, and needs a same-region client to measure properly.
