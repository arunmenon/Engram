# Spanner everywhere: replacing Redis as well as Neo4j

**Date:** 2026-10-04 · **Status:** analysis for a decision; nothing built · **Read with:** [Spanner Graph gap analysis](spanner-graph-gap-analysis.md), [ADR-0018](../../../adr/0018-ontology-packs.md)

## 0. First, what actually changes with the PDLC work (Neo4j or not)

Not everything changes. The two ends of Engram stay; the middle changes.

| Layer | Changes with packs + PDLC? |
|---|---|
| Ingest API (`/v1/events`, batch) | **no** (event types also checked against packs) |
| Event ledger (Redis today) | **no** (still append-only, still the source of truth) |
| Connectors | new (outside the core) |
| Projection (ledger → graph) | **yes**: generic projector reading pack rules |
| Graph storage | **yes**: generic operations, uniform node ids |
| Retrieval | **yes**: any node can be a starting point; PDLC named queries |
| Response format (Atlas) | **no** |

So "Spanner for the graph" swaps one part that is changing anyway. "Spanner for Redis" swaps a part that otherwise would *not* change. That's the core of the trade-off below.

## 1. What Redis does in Engram today

About 1,560 lines: `adapters/redis/` (store, indexes, retention, trimmer, Lua ingest script) and `worker/consumer.py`, behind the `EventStore` port (9 methods: append, append_batch, get_by_id, get_by_session, search, search_bm25, health, stream_length, close).

| Job | Redis feature | Spanner equivalent | Difficulty |
|---|---|---|---|
| Append-only ledger with a global position | Stream `XADD`; entry id = `global_position` | `Events` table; position = commit timestamp (+ event id to break ties). Key by `event_id`, not by time, to avoid a write hotspot; index on commit timestamp | medium: `global_position` changes format |
| Exactly-once ingest | Lua dedup script | primary key on `event_id` + `INSERT OR IGNORE`; atomic by construction | easy, and stronger |
| Event documents | RedisJSON | JSON column | easy |
| Session and filter queries | RediSearch secondary indexes | secondary indexes | easy |
| BM25 keyword search | RediSearch full-text | Spanner full-text search (`SEARCH`, `SCORE`); Enterprise edition, which Spanner Graph needs anyway | medium: ranking will differ, retrieval evals must be re-run |
| Four consumer groups, acks, retrying stuck messages | `XREADGROUP`, `XACK`, `XPENDING`, `XAUTOCLAIM` | **no direct equivalent.** Two options: (a) each consumer polls `Events` after its own checkpoint, read at a fixed timestamp, with a checkpoint table; (b) Spanner change streams (partitioned, ordered by commit time; the reader must follow child partitions) | **hard**: the consumer base class is rewritten |
| Hot/cold tiers, trimming, retention | stream trim, TTL, trimmer job, archive to GCS | row deletion policy (TTL), tiered storage, existing GCS archive adapter | medium |
| Speed on the hot path | sub-millisecond | single-digit milliseconds per read; a few ms per commit | acceptable for ingest and projection; adds a few ms to each context call |

## 2. What "Spanner everywhere" would give us

- **One database to run, secure, back up and pay for**, and one access model, instead of Redis plus Neo4j.
- **Ledger and graph in the same database.** Projection becomes a read and a write in one place. The design rule stays the same, though: the graph is derived from the ledger and can be rebuilt. Spanner does not change that rule.
- **Stronger guarantees than today.** Duplicate-free ingest by primary key, real transactions, enforced constraints, point-in-time recovery.
- **Native "as of" reads** for C6 snapshots, but only within Spanner's version retention window (up to 7 days). Snapshots older than that still come from ledger positions, as designed.
- **GCP alignment.** It fits if PayPal is standardising on GCP. That's an organisational question, not a technical one.

## 3. What it would cost

- **Engineering:** rewriting about 1,560 lines of Redis code plus the consumer base class, on top of the graph adapter. Rough estimate 3–4 engineer-weeks for the ledger side, after the graph side.
- **The consumer model is the hard part.** Redis gives consumer groups, acknowledgements and reclaiming of stuck messages for free. On Spanner we build them: a checkpoint per consumer, safe polling at a read timestamp, and retry of failed events. It's a known pattern (outbox-style polling), but it is new code in the most correctness-sensitive part of Engram.
- **`global_position` changes format.** It moves from a Redis stream id (`1707644400000-0`) to a commit timestamp plus id. It appears in every provenance block and every API response. Clients that parse it, and the frozen Phase 0 and Phase 1 contracts, are affected. It needs an ADR amendment and a compatibility period. Inside Engram only one place parses it as a Redis id (`adapters/redis/trimmer.py`, which would be replaced anyway), so the impact is on API clients, not on core code.
- **BM25 ranking changes,** so the retrieval quality numbers need re-measuring.
- **Lock-in.** Neo4j and Redis run anywhere, Spanner only on GCP. The emulator covers local development; change streams in the emulator need checking.
- **Money.** Redis self-hosted is cheap. Spanner Enterprise starts at about $90 a month for the smallest instance, plus $0.39 per GB-month. The ledger grows forever, so storage cost grows with it. Tiered storage and archiving to GCS limit that.
- **Frozen contracts and ADRs:** ADR-0003 (dual store) and ADR-0010 (Redis event store) would be amended, and the Phase 0 infra tests replaced.

## 4. Options

| Option | What | When it makes sense |
|---|---|---|
| A. Status quo | Redis ledger + Neo4j graph; packs and generic operations only | no GCP mandate |
| B. Spanner graph only | Redis ledger + Spanner Graph | Spanner wanted for graph scale or GCP, but keep the fast, proven ledger |
| **C. Spanner everywhere, staged** | graph on Spanner first (weeks 3–4), ledger on Spanner after, behind the existing `EventStore` port | **if the target is GCP-only operation** |
| D. Spanner everywhere at once | both replaced together | not recommended: two risky migrations at the same time, and nothing to compare against if results change |

**Recommendation: if GCP is the target platform, choose C. Otherwise, choose B or A.**

Why staged:
- The graph is being rebuilt anyway; the ledger is not.
- Doing the ledger second keeps a working Redis ledger to compare against.
- Each step has its own conformance suite: same events in, same answers out.
- Both stores already sit behind ports (`EventStore`, `GraphStore`), so each swap is an adapter and its tests, not a redesign.

## 5. What to do now, whichever option

1. Keep all new code behind the two ports (ADR-0018 rule 11 already says this for the graph; extend it to the ledger).
2. Stop new code from parsing `global_position` as a Redis id. Treat it as an opaque, ordered string. That keeps option C open at no cost.
3. Write the consumer-checkpoint design (option C's hard part) as a short ADR draft before anyone builds it.
4. Settle the GCP question with whoever owns platform direction. The answer chooses between B and C.
