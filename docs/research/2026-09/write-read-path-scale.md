# Write path, read path and API surface: scale review

**Date:** 2026-09-25
**Code analysed:** `feature/autoresearch-eval-scoring` at `9df84ed` (application source identical to `dev`).
**Method:** static code reading by a code-analysis agent; the three highest-impact defects were re-verified by hand and are marked **confirmed**. Everything else is marked **reported** (read from code, not re-verified line by line, not run). No live Redis/Neo4j test was performed.

## Summary

The question asked was "how optimised are the write and read paths". The answer is that optimisation is not the first problem. Three core paths are broken in ways that make the current throughput and retention numbers meaningless, and ADR-0018 (billion-scale architecture) has no code behind its Phases A–D. Fixing the defects below comes before any tuning, and before any benchmark number is published.

## Confirmed defects (re-verified by hand)

| # | Defect | Where | Effect |
|---|---|---|---|
| D1 | **Batches of more than 10 events lose their payloads.** `append_batch` hands off to `append_batch_concurrent(events, tenant_id=…)` without the `payloads` argument. | `adapters/redis/store.py:301` → `:349-369` | Anything ingested in bulk (the LangChain callback uses `ingest_batch`) is stored with no conversation content, so session extraction later has nothing to read. |
| D2 | **The RediSearch index covers no documents.** The index is created with prefix `evt:`; keys are written as `t:{tenant}:evt:{id}`. | `adapters/redis/indexes.py:26,48`; `store.py:120-137` | BM25 seed channel, `get_by_session`, `search`, and admin `/replay` all return nothing. The `Event` model also has no `summary`/`keywords` fields, so the BM25 TEXT fields would be empty even with the right prefix. |
| D3 | **Redis retention never deletes JSON documents or session streams.** Consolidation passes an already tenant-prefixed key prefix (`t:{tid}:evt:`) into the trimmer, which prefixes it again → scan pattern `t:default:t:default:evt:*`. | `worker/consolidation.py:557-581` → `adapters/redis/trimmer.py:99,177,255` | Combined with `noeviction` and no `maxmemory` in `docker/redis/redis.conf`, Redis grows without bound. Only the global-stream XTRIM and dedup-ZSET cleanup work. |

## Write path, hop by hop (reported)

**HTTP → validation (sync).** `POST /v1/events` (`api/routes/events.py:87`) → Pydantic → `validate_event` → one `append`. `POST /v1/events/batch` (`:139`) validates in a Python loop, then one `append_batch`; max 1000. No LLM or embedding call on the request path. Rate limit is an in-process token bucket per uvicorn worker keyed on a spoofable `X-Forwarded-For`; a 1000-event batch costs one token, so single-event ingest is capped at ~2 req/s per client per worker (`api/middleware.py:139-178`).

**Redis Lua ingest.** One EVALSHA per event: `ZSCORE` dedup, `XADD` global stream (`MAXLEN ~500k`), `XADD` per-session stream (**no MAXLEN**), two `JSON.SET`, `ZADD` dedup. ≤10 events pipeline in one round trip; >10 fan out to N EVALSHAs under a semaphore of 50 with a pool of 20 (and lose payloads, D1). Keys carry no `{}` hash tags, so the 4-key script would fail with CROSSSLOT on Redis Cluster. The `MAXLEN ~500k` trim is **not pending-safe**: a consumer group more than 500k entries behind loses unprocessed entries.

**Consumer framework** (`worker/consumer.py`). Every group reads the whole tenant stream, `batch_size=10`, adaptive sizing never enabled. `XAUTOCLAIM` and the PEL drain run **once at startup**; a message that fails in the main loop stays pending until restart, and each failure sleeps the whole consumer for up to 60 s. Topology is one OS process per (consumer type, tenant); no tenant discovery.

**Projection.** Buffers to 100 but flushes every read round, so effective batch ≈10. One sequential `JSON.GET` per event (N+1). One UNWIND transaction for nodes, one per edge type. FOLLOWS predecessor comes from an **in-process LRU** — wrong or missing after a restart or with a second instance. `MERGE_EVENT_NODE` re-SETs `importance_score` and `access_count = 0`, so redelivery or replay wipes enrichment and access history.

**Enrichment.** Per event, no batching: 1 `JSON.GET`, 1 Neo4j tx, one single-text embedding (`embed_batch` exists, unused), 1 Neo4j tx, 1 `XACK`. Races ahead of projection: `MATCH (e:Event {event_id})` silently no-ops if the node isn't there yet. Event embeddings have no vector index and are returned in every `RETURN e`. **SIMILAR_TO edges are never created.**

**Extraction.** Every event costs a `JSON.GET` + `XACK` just to read its type. On `session_end`: unbounded `XRANGE`, sequential `JSON.GET` per event, one LLM call over the whole session (no chunking). Mid-session extraction every 50 turns re-extracts the *entire* session → LLM cost quadratic in session length. Writes: entity pool capped at an arbitrary 1000; per entity an embedding + vector search + second embedding + MERGE; then **one REFERENCES transaction per entity × per session event** (50 events × 8 entities = 400 transactions, against the ADR estimate of 5–15 edges). All entity-resolution calls are tenant-blind.

**Consolidation.** Runs on a 6 h timer. Every session with ≥30 events is re-summarised with the LLM **every cycle**, and again in the forgetting pass. Node count is an unlabelled `MATCH (n {tenant_id})` (AllNodesScan). Cold deletes and centrality updates run as single whole-tenant transactions; no `CALL {} IN TRANSACTIONS`. One `tx.run` per SUMMARIZES edge.

**Per-event steady-state cost:** ~8 Redis round trips, ~2.2 Neo4j write transactions plus ~E amortised from extraction, one CPU MiniLM embedding.

## Read path, hop by hop (reported)

**`GET /v1/context/{session_id}`** (`adapters/neo4j/store.py:751-936`): embed query (SentenceTransformer loads lazily on first request) → `GET_SESSION_EVENTS` → score in Python → **write** `BATCH_UPDATE_ACCESS_COUNT` (a write on every read, outside the circuit breaker) → `GET_SESSION_EDGES` → `GET_SESSION_NEIGHBORS` (`LIMIT 500`) → `GET_NEIGHBOR_INTER_EDGES`, which is `MATCH (a)-[r]->(b) WHERE coalesce(a.entity_id, …) = nid` with no label and no usable index — **a full scan per neighbour on every call**. `max_depth` is accepted and ignored. Pagination is broken: page 1 is `DESC`, cursor pages are `occurred_at > cursor … ASC`, so page 2 re-returns newer events.

**`POST /v1/query/subgraph`** (`adapters/neo4j/retrieval.py:98-272`): optional HyDE LLM call (2 s cap; `CG_HYDE_ENABLED` setting unused, request flag used instead) → embedding → keyword intent (LLM classifier off by default) → three seed channels in parallel (graph strategy query; vector KNN with **tenant filter applied after top-k**; BM25 — dead, D2) → RRF → seed fetch → cross-session expansion (unbounded through supernode entities before `LIMIT`) → 1-hop outgoing neighbour expansion with a `LIMIT` that is global across all seeds, and entity seeds never expanded (query matches `:Event` only) → PPR (off) → MMR (no-op) → offset pagination with full recompute per page. Access-count bump filters `nid.startswith("evt")`, but event ids are UUIDs, so it almost never fires.

**Lineage**: `[:CAUSED_BY*1..10]` enumerates every path to 10 hops *then* filters on depth; `LIMIT` counts paths not nodes; fetch is `LIMIT max_nodes+1` then sliced by offset, so **every page after the first is empty**.

**Caps/timeouts/caching**: route caps hard-coded (`max_nodes ≤ 500`, `max_depth ≤ 10`); `QuerySettings.max_max_*` not wired; per-query Neo4j timeout 5 s; no end-to-end deadline; no result/embedding/intent cache; 384-float embeddings pass into `AtlasNode.attributes` and bloat responses.

## API surface

| Method | Path | Purpose | Auth | Pagination | Note |
|---|---|---|---|---|---|
| POST | /v1/events | ingest one | api_key | – | |
| POST | /v1/events/batch | ingest ≤1000 | api_key | – | D1 |
| GET | /v1/context/{session_id} | session working memory | api_key | keyset (broken) | |
| POST | /v1/query/subgraph | hybrid intent retrieval | api_key | offset | |
| GET | /v1/nodes/{id}/lineage | CAUSED_BY chain | api_key | offset (broken past p1) | |
| GET | /v1/entities/{id} | entity + ≤100 events | api_key | none | |
| POST | /v1/feedback | ±1 importance; logs event | api_key | – | up to 200 sequential write txs |
| POST | /v1/admin/reconsolidate | summarise (sync) | admin | – | |
| GET | /v1/admin/stats | counts | admin | – | AllNodesScan |
| POST | /v1/admin/prune | warm/cold prune | admin | truncated flag | preview ≠ execution |
| POST | /v1/admin/replay | wipe + rebuild tenant graph | admin | – | relies on dead FT.SEARCH (D2) |
| GET | /v1/admin/health/detailed | | admin | – | |
| GET/DELETE | /v1/users/{id}/… | profile, preferences, skills, patterns, interests, export, erase | admin | none | |
| POST | /v1/simulate/turn | demo-only litellm SSE proxy | api_key | – | not a product route |
| GET | /health/*, /metrics | probes | none | – | |

Tenant: `X-Tenant-ID` header when `CG_TENANT_ENABLED`, else `default`. With `CG_AUTH_API_KEY` unset, auth is off.

**SDKs**: `engram` (httpx) wraps everything except `/feedback`, `/admin/replay`, `/simulate`. `engram-langchain` sends `max_nodes=1000`, which the server rejects (limit 500). `engram-crewai`: ingest + subgraph. `engram-mcp`: ingest, context, subgraph, lineage, users, delete. `kg-memory-mcp` is a standalone codebase/ADR indexer, not an Engram wrapper.

## ADR-0018 claims vs code

| ADR-0018 item | Reality |
|---|---|
| Phase A ShardRouter / `CG_NEO4J_SHARDS` | not implemented |
| Phase B FederatedGraphStore hot/cold | not implemented |
| Phase C Kafka event store | not implemented, no dependency |
| Phase D distributed graph | not implemented |
| Single Neo4j Community + single Redis Stack | true (heap 512 m, pagecache 128 m) |
| Pool size 50 | true |
| `noeviction` | true, but no `maxmemory` |
| 7-day hot trim | implemented, PEL-safe |
| 90-day ceiling / archive | setting exists; enforcement broken (D3) |
| Compaction | implemented; gated by a full-scan count; cross-reference guard dead |
| Growth model SIMILAR_TO 2–8, REFERENCES 5–15 per session | SIMILAR_TO never created; REFERENCES actually entities × events |
| Scale model tool | implemented (`tools/scale_model.py`) |

## Evaluation harness numbers (for the record)

Offline, pure Python; reimplements scoring; 8-d SHA-256 hash "embeddings"; query embedding built from gold nodes; intent from gold label. Metrics: nDCG@10, violation rate, P/R@10; objective `(1 − violations) × nDCG`. Reported: original dataset 0.46 → 0.53 (params only) → 0.60 (with structural changes); extended dataset (10 scenarios, 80 queries) 0.699 → 0.737 over 19 cycles. None of the tuned biases or hooks exist in `src/`. Given the label leakage these numbers do not measure the production retrieval path.

## Ranked risks and fix directions

1. **Redis retention no-op + no memory cap (D3).** Pass the base prefix once; set `maxmemory`; wire `trim_under_pressure`; prefer per-key TTLs to SCAN sweeps.
2. **Bulk ingest loses payloads (D1).** Thread `payloads` through, or pipeline in chunks of ~100.
3. **FT.SEARCH dead (D2).** Index on prefix `t:` (or per-tenant indexes); persist `summary`/`keywords`.
4. **Full scans on the hot read path.** Label-specific MATCHes on pk constraints for inter-edges; fix pagination direction; strip `embedding` from responses.
5. **Extraction write fan-out and tenant-blindness.** Link only events that mention the entity; single UNWIND; pass `tenant_id`; key `entity_id` by tenant.
6. **Stream design.** Put `event_type`/`session_id` in stream fields so consumers don't `JSON.GET` to filter; pipeline reads; make MAXLEN lag-aware; cap session streams.
7. **Consumer reliability.** Periodic XAUTOCLAIM/PEL rescan; fold enrichment into projection's UNWIND; SET importance/access only `ON CREATE`; don't clear the buffer before the write succeeds.
8. **Consolidation O(tenant) per cycle.** `consolidated_at` watermark; incremental; `CALL {…} IN TRANSACTIONS`; never re-summarise unchanged sessions.
9. **Horizontal scaling blocked.** Hash-tagged keys; FOLLOWS derived from the per-session stream, not an in-process cache; rate limiting in Redis; tenant discovery for workers.
10. **Read amplification.** Async/sampled access-count bumps; per-entity `CALL {… LIMIT k}` for cross-session fan-out; build lineage pattern at requested depth; larger vector top-k then tenant filter, or per-tenant index; per-seed neighbour limits; an end-to-end deadline.

The write path's structural strengths remain: one round trip per event on the request path, no LLM in the sync path, idempotent Lua ingest, replayable ledger. Those are worth keeping; the items above are what stands between them and a defensible scale claim.
