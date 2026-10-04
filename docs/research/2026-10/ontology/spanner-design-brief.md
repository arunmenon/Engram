# Design brief: Engram on Spanner (event ledger and graph)

**Date:** 2026-10-04 · **Status:** revised after one review pass (§11) · **Supersedes nothing**; consolidates [spanner-graph-gap-analysis.md](spanner-graph-gap-analysis.md) and [spanner-everywhere.md](spanner-everywhere.md) into one design.
**Decision asked:** whether to move Engram's two stores, the Redis event ledger and the Neo4j graph, to Cloud Spanner, and if so, in what order and under which design choices.

## 1. Scope

In scope: the event ledger (Redis Streams, RedisJSON, RediSearch, Lua), the four consumer groups that read it, the graph projection (Neo4j), vector and keyword search, retention and archiving, local development and tests.
Out of scope: the HTTP API contract (unchanged except the `global_position` format; note `api/app.py`, `api/routes/admin.py`, `health.py` and `events.py` use Redis directly and move behind the ports in phase 0), LLM and embedding services, the ontology packs themselves (ADR-0018), connectors.

## 2. Today

| Part | Code | Interface | Notable features used |
|---|---|---|---|
| Event ledger | `adapters/redis/` (store, indexes, retention, trimmer, `lua/ingest.lua`), about 1,170 lines | `ports/event_store.py`, 9 methods | `XADD` with entry id as `global_position`; Lua dedup; RedisJSON; RediSearch (filters and BM25); stream trimming; hot/cold tiers; GCS archive |
| Consumers | `worker/consumer.py` (385 lines) and four workers | base class, **plus direct Redis access** | `XREADGROUP`, `XACK`, `XPENDING`, `XAUTOCLAIM`; all four workers also call `JSON.GET` and extraction calls `XRANGE` on `events:session:{id}` directly, bypassing the `EventStore` port |
| Graph | `adapters/neo4j/` (5 files, about 3,850 lines, 68 hand-written queries) | `ports/graph_store.py`, `user_store.py`, `maintenance.py` | `MERGE` upserts, `UNWIND` batches, variable-length paths, `OPTIONAL MATCH`, one vector index, `DETACH DELETE`; no APOC, no GDS |
| Retention today | `ingest.lua` caps the global stream (`MAXLEN ~`, ADR-0014); session streams expire; older events archived to GCS | | the Redis ledger is a hot window plus an archive, not full history; a full rebuild replays the archive |
| Local dev | `docker/` (Redis Stack, `neo4j:5-community`) | | Phase 0 infra tests are frozen |

## 3. Target

One Spanner instance, **Enterprise edition** (required for Spanner Graph, full-text search and vector search), regional configuration, one database with:

```
Events              (event_id PK, shard INT64 = hash(session_id) mod N, commit_ts TIMESTAMP (allow_commit_timestamp),
                     batch_index INT64, event_type, session_id, agent_id, trace_id, occurred_at, payload JSON,
                     envelope JSON, legacy_position STRING)
  index EventsByShardTime (shard, commit_ts, batch_index, event_id)   -- sharded to avoid a monotonic-key hotspot
  index EventsBySession   (session_id, occurred_at)
  full-text index on searchable payload fields             -- replaces RediSearch BM25
ConsumerCheckpoints (consumer_group, shard PK, checkpoint_ts, updated_at)
ConsumerFailures    (consumer_group, event_id PK, attempts, last_error, next_retry_at)   -- replaces XPENDING/XAUTOCLAIM
Nodes / Edges       schemaless node and edge tables + CREATE PROPERTY GRAPH (see the graph gap analysis §3)
```

`global_position` becomes an opaque, ordered string: `<commit_ts, fixed-width UTC to nanoseconds>/<batch_index zero-padded>/<event_id>`. `batch_index` keeps the order of events submitted together, which share one commit timestamp.

## 4. Gap table

| # | Capability | Redis / Neo4j today | Spanner design | Effort | Risk |
|---|---|---|---|---|---|
| G1 | Append with total order | stream entry id | commit timestamp + event id; reads ordered by (commit_ts, event_id) | M | M: format change visible to API clients |
| G2 | Idempotent ingest | Lua dedup script, which returns the existing position for a duplicate | read-write transaction: read by `event_id`; if present return its position, else insert and return the position built from the commit response's timestamp | S | L |
| G3 | Consumer groups | XREADGROUP / XACK; one global stream in order | per-group, per-shard checkpoint; each poll is a strong read, whose returned read timestamp T bounds the batch (checkpoint < commit_ts ≤ T); process, then set checkpoint = T. **Ordering guarantee: in order within a session** (shards are by session), not across sessions, which no consumer relies on today (FOLLOWS is per session); to be confirmed per worker in phase 0 | L | **H**: correctness-critical new code |
| G4 | Stuck and failed messages | XPENDING / XAUTOCLAIM | `ConsumerFailures` table with retry schedule and a dead-letter state; a checkpoint never waits on a failed event | M | M |
| G5 | Session and filter reads | RediSearch indexes | secondary indexes | S | L |
| G6 | Keyword search (BM25) | RediSearch | Spanner full-text search (`SEARCH`, `SCORE`) | M | M: ranking differs; retrieval evals re-run |
| G7 | Retention tiers and trimming | stream capped and trimmed, session streams expire, GCS archive (ADR-0014) | **keep today's model**: hot window in Spanner with a row deletion policy that only removes rows already archived to GCS; tiered storage for the warm part. Keeping full history in Spanner instead is a separate decision with unbounded storage cost | M | M |
| G8 | Graph upserts | `MERGE` | DML `INSERT OR UPDATE` / mutations; "set on create" via `INSERT OR IGNORE` + `UPDATE` in one transaction | M | M |
| G9 | Graph traversal | Cypher | GQL quantified paths; `TRAIL` where edge uniqueness matters | M | M: silent result differences |
| G10 | Vector search | Neo4j vector index | vector index + `APPROX_COSINE_DISTANCE` | M | L |
| G11 | Constraints | uniqueness only (Community) | primary keys, `NOT NULL`, foreign keys | S | L (improvement) |
| G12 | Async client | async Neo4j and Redis drivers | `google-cloud-spanner` 3.71 ships an `_async` package (unverified as a supported API); fallback: sync client in a thread pool, which needs session-pool sizing and must not block the consumers' event loops; prototype in phase 0 | M | M |
| G13 | Local dev and CI | containers | Spanner emulator for functional tests. The emulator runs read-write transactions one at a time, so concurrency and fault tests need a real instance (free trial); its support for property graphs, full-text and vector search is unverified | M | M |
| G14 | Backups and recovery | Redis persistence; Neo4j rebuild from ledger | backups; point-in-time recovery needs version retention raised from the 1-hour default (up to 7 days), which costs extra storage: an explicit setting to decide with cost; graph still rebuildable from ledger plus archive | S | L |
| G15 | As-of snapshot reads | ledger position | stale reads at a timestamp, only within the version retention set in G14; otherwise by ledger position as today | S | L |

S, M, L = small, medium, large.

## 5. Design decisions

- **D1. Position format.** Commit timestamp, batch index and event id, fixed-width, exposed as an opaque string. Keep the old Redis id in `legacy_position` for every migrated event, so existing provenance references stay resolvable. Old and new positions are not string-comparable; across the migration boundary, order comes from the ledger (all migrated events precede all new ones, see phase 3), never from comparing strings. API clients must not parse positions; inside Engram only `adapters/redis/trimmer.py` does, and it is replaced.
- **D2. Consumer model: polling with checkpoints, not change streams.** Each poll is a strong read; Spanner returns the timestamp it read at, and that read sees every commit at or before that timestamp, so using it as both the batch bound and the new checkpoint skips nothing (to verify, §9). Never use the client's clock as T. Change streams scale further but need partition tracking and an extra reader process. Revisit if polling load or latency becomes a problem.
- **D3. Hotspot avoidance and ordering.** Never key or index by a monotonically increasing value alone. The ledger key is `event_id` (random UUIDs). The time index leads with `shard = hash(session_id) mod N` (N = 16 to start), so one session's events stay in one shard and in order; consumers poll each shard. A very busy single session would concentrate on one shard; acceptable at today's scale, revisit with load tests.
- **D4. Graph layout:** schemaless Nodes and Edges tables with dynamic labels and JSON properties, hot fields as real columns (graph gap analysis §3). A new ontology pack needs no DDL.
- **D5. Projection stays asynchronous.** Ledger and graph share a database, but the graph is still a derived, rebuildable projection (ADR-0005). There are no cross-store transactions in the write path.
- **D6. Backend neutrality first** (ADR-0018 rule 11, extended to the ledger). All new code uses the `EventStore` and `GraphStore` ports only. Each backend passes one conformance suite: same events in, same answers out.

## 6. Migration plan

| Phase | Work | Exit check |
|---|---|---|
| 0 | Ports hardened: add the reads workers do directly today (event document by id, a session's events in order, events after a checkpoint) to `EventStore`; refactor all four workers and the API's admin and health routes onto the ports; positions treated as opaque; conformance suite for both ports; emulator in CI; async-client prototype | no direct Redis calls outside `adapters/redis/`; suite green on Redis + Neo4j |
| 1 | Spanner graph adapter (generic operations from ADR-0018) | suite green on Neo4j and Spanner Graph; graph rebuilt from the Redis ledger matches Neo4j's answers on the 30 PDLC questions |
| 2 | Spanner ledger adapter and checkpoint consumer | suite green on the emulator; fault and concurrency tests pass **on a real instance** (consumer crash mid-batch, duplicate ingest, a failing event retried and dead-lettered, concurrent producers, session order preserved) |
| 3 | Data migration and dual run: first copy the Redis hot window (and, if wanted, the GCS archive) into Spanner in legacy order, keeping `legacy_position` and using `batch_index` to preserve order inside each copy batch; **only after the copy completes**, start dual-writing new events, so every migrated event precedes every new one; soak and compare consumer outputs | zero divergence over the soak; retrieval evals within agreed tolerance (BM25 ranking change) |
| 4 | Cut over reads, then writes; keep Redis read-only for one retention period; decommission | rollback rehearsed before cutover |

Rough effort: about 3–4 engineer-weeks for phases 0–1 (phase 0 grew: workers and API routes move behind the ports) and 3–4 for phases 2–3. These are estimates, not measurements.

## 7. Cost (Enterprise edition, regional; prices and the edition requirement come from search extracts and are unverified until checked in the pricing calculator)

| Item | Price | Note |
|---|---|---|
| Compute, smallest instance (100 processing units) | about $0.12 per hour, about $90 per month | scale by processing units under load |
| Storage | $0.39 per GB-month (SSD) | bounded if today's hot-window-plus-archive model is kept (G7); raised version retention for PITR adds to it (G14) |
| Spike or experiment | $0 on a free trial instance; about $1 per working day on the smallest paid one | see the gap analysis §7 |

## 8. Risks

| Risk | Mitigation |
|---|---|
| Consumer correctness (G3, G4) regresses | fault-injection tests in phase 2; dual run in phase 3; Redis kept read-only until confidence |
| Silent query differences (G9) | conformance suite compares answers, not only success |
| Retrieval quality shifts (G6) | re-run retrieval evals; accept or tune before cutover |
| API clients parse positions (D1) | announce opaque positions now; keep `legacy_position` |
| Write hotspots (D3) | sharded time index; load test in phase 2 |
| Emulator gaps (G13) | confirm features early; free trial instance as fallback |
| GCP lock-in | ports kept; Redis and Neo4j adapters kept buildable until a decision to drop them |

## 9. To verify before sign-off

That Spanner Graph, full-text search and vector search all need Enterprise edition; list prices; Exact `DYNAMIC LABEL` syntax and label cardinality; full-text and vector features on the emulator; stability of the async Python client; whether commit-timestamp ordering in a strong read holds as assumed for D2 (read-your-commits at timestamp T); edition availability and org policy in `portiq-mvp`.

## 10. Decision asked

1. Is GCP the target platform? If yes, option C (staged, graph first, ledger second). If no, Spanner graph only, or stay on Redis + Neo4j.
2. Approve D1–D6 as the design baseline.
3. Spanner access in `portiq-mvp` (Enterprise edition or a free trial instance).

## 11. Review pass (2026-10-04)

One independent review (Fable 5.1, short pass). Its 12 findings were checked against the code and all applied:

| # | Finding | Severity | Change made |
|---|---|---|---|
| 1 | sharding by event id would break per-session order | blocking | shard by session (D3); ordering guarantee stated (G3) |
| 2 | workers and API routes read Redis directly, bypassing the port | blocking | confirmed in `worker/*.py` and `api/`; phase 0 now moves them behind the ports; effort raised |
| 3 | "strong read at T" was contradictory | should-fix | D2 uses the read timestamp Spanner returns |
| 4 | duplicate ingest must return the existing position | should-fix | G2 read-then-insert |
| 5 | old and new positions don't compare | should-fix | D1 fixed-width format; ordering across the boundary from the ledger |
| 6 | bulk copy and dual-write would interleave | should-fix | phase 3: copy completes before dual-write; `batch_index` keeps batch order |
| 7 | emulator runs transactions one at a time | should-fix | phase 2 exit tests on a real instance |
| 8 | 7-day PITR is not the default | should-fix | G14 makes retention an explicit cost decision |
| 9 | the ledger is already trimmed and archived today | should-fix | confirmed in `ingest.lua`; G7 keeps the hot-window-plus-archive model |
| 10 | async client claim unverified | minor | marked unverified; prototype in phase 0 |
| 11 | edition and price claims unverified | minor | labelled unverified |
| 12 | API files use Redis directly | minor | listed in scope |

Reviewer's verdict: fit for a decision-maker once findings 1–6 were fixed. They are.
