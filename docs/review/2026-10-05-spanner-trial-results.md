# Spanner trial on a real instance: first results (2026-10-05)

First run of Engram against a real Cloud Spanner instance, the trial asked for by the maturity review (`2026-10-05-maturity-review-guide.md`, task F7). Capped at one hour by the owner; the measurements took about 4 minutes. Two bugs only a real instance shows were found and fixed in the same hour (below).

## Setup

| Item | Value |
|---|---|
| Instance | `engram-experiment` in `portiq-mvp`, provisioned by the owner. Edition and processing units not visible to the trial credential (`spanner.instances.get` denied). |
| Database | `engram`, provisioned empty by the owner. Engram's schema applied with `update_ddl` from `schema_statements` (43 s). |
| Credential | A one-hour OAuth access token. It lacked `monitoring.timeSeries.create`, so the client's built-in metrics export failed (harmless). |
| Client | `google-cloud-spanner` 3.71, sync client in threads, from a cloud container in an unknown region. Latencies include that network path. |
| Script | `scripts/engram_trial.py`: `--minutes 20 --ledger-seconds 120 --events 2000` at 8fb196b, then `--phases schema,graph` after each fix |

## Results

| Phase | Result |
|---|---|
| Schema | Accepted in full: property graph with dynamic labels and properties, full-text search index, vector index. `schema_differences` finds nothing missing (2.9 s, the first query on a new session). So the instance supports the Enterprise features. |
| Ledger | 8 producers, 40 sessions, batches of 10: **2,070 events in 38.5 s (54 events/s)**, no errors. Two consumer groups of two consumers each: **each group got all 2,070, none missing, no duplicates, no per-session order violations.** |
| Import | 500 events per call with 1 KiB and with 10 KiB payloads: one transaction each, **14,000 mutations (28 per event)**, about 2.2 s per call. Our estimate is 33 per event, so the estimate is safe (18% high). |
| Graph writes | 2,000 Event nodes plus 500 Entity nodes in flushes of 200, then 1,999 `CAUSED_BY` edges: node flush p50 0.69 s, edge flush p50 1.02 s. |
| Graph reads | After both fixes: `find_nodes_matching` over a 500-node label in 0.8 to 1.5 s (a full label scan, review S3); 10-hop GQL lineage in 0.7 to 1.2 s, 10 chains as on the emulator. |
| Vector search | Top-5 over 50 embedded entities in 0.41 to 0.46 s; the query vector is its own top hit. |
| Retention | Not run. The trial script deletes nothing. |

Latencies (ms):

| Call | n | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| `append_batch` (10 events) | 207 | 1,423 | 1,999 | 2,115 | 2,215 |
| `read_new` (up to 10) | 414 | 667 | 1,017 | 2,770 | 4,256 |
| `read_new`, nothing new | 36 | 645 | 659 | 662 | 662 |
| `ack` | 414 | 653 | 730 | 958 | 1,299 |
| node flush (200) | 10 | 694 | 760 | 760 | 760 |
| edge flush (200) | 10 | 1,018 | 1,052 | 1,052 | 1,052 |

## What this says

- **Correct under real concurrency, at this load.** S1 and S2 in the review guide (concurrency never tested; consumer reads lock the ledger) held for 8 producers and 4 consumers: nothing skipped, duplicated or reordered. This is far below the 100 and 1,000 events/s in the plan, so contention at load is still unmeasured.
- **Every call costs one or more round trips of about 0.65 s.** Even a read that finds nothing takes 645 ms. That is a read-write transaction from a distant client: begin, read and commit. Latency, not Spanner capacity, bounds throughput here: 54 events/s from 8 producers is 8 calls in flight at about 1.4 s each. Next: run from a client in the instance's region, and measure how much the read-write transaction in `read_new` costs against a strong read (review F2).
- **The commit budget estimate is conservative.** Spanner counted 28 mutations per Events row against our 33. Both payload sizes gave the same count: mutations count columns, not bytes.

## Bugs found and fixed

### 1. Real Spanner refuses some JSON numbers

- **Symptom.** Writing 50 Entity nodes whose `props` hold a 384-number embedding failed with `OutOfRange: 400 Error parsing JSON: Input number: 0.2002386475503002 cannot round-trip through string representation`. The emulator accepts the same write.
- **Measured.** We checked with `SAFE.PARSE_JSON` over number strings, in read-only queries:
  - 9 of 20,003 random floats were refused;
  - 40 of 30,000 at 12 significant digits, 53 at 13, 41 at 14, 42 at 15, and 18 at 17;
  - plain decimals such as `-0.707176497086` and `0.0928069675519494` were among them.

  Rewriting a refused value as `%.15g`, `%.17g` or fixed point did not reliably get it accepted. So no number format is safe, and rounding was tried and dropped.
- **Impact.** One refused number fails the whole write. That means an event whose payload carries one at ingest, or any node or edge with float properties (embeddings, scores). About 1 in 1,000 such values is refused.
- **Fix** (`adapters/spanner/log.py`).
  - `json_param` stores every non-integral float as `{"$float": "<repr>"}`, and `json_value` decodes it, so the round trip is exact.
  - Integers and integral floats stay JSON numbers.
  - SQL reads only `session_id` from `props`, and graph and ledger filters run in Python, so nothing that queries JSON numbers in SQL changes.
- **Verified.** On the real instance the graph phase passes, and an event whose payload holds the refused values is created and read back unchanged. Unit and emulator tests are in `tests/unit/test_spanner_commits.py`.
- **Note.** Databases written before this change hold plain numbers. They still read correctly, since only tagged objects are decoded.

### 2. Dynamic-label filters match nothing in GQL

- **Symptom.** The lineage query returned 0 chains on the real instance and 10 on the emulator, on the same data.
- **Measured.** On the real instance `LABELS(a)` returns `['Event', 'GraphNodes']`. Yet `(a:Event)`, `(a:event)` and `-[e:CAUSED_BY]->` each match nothing. Unlabelled patterns, the static labels (`:GraphNodes`, `:GraphEdges`) and predicates on the key columns (`a.label`, `e.edge_type`) do match.
- **Fix** (`adapters/spanner/graph.py`). The lineage query filters on the key columns: `TRAIL (start)-[e WHERE e.edge_type = 'CAUSED_BY']->{1,n}(ancestor) WHERE start.label = 'Event'`. The emulator accepts the new form, and the lineage conformance cases pass.
- **Verified.** It returns 10 chains on the real instance. Lineage was the only GQL query in the code.
- **Open.** We don't know why dynamic-label matching fails here. It might be the edition, a missing label index, or documented behaviour. Until it is understood, new GQL must filter on the key columns.

## Left on the instance

The trial wrote rows tagged `trial-`: about 3,070 events, 2,550 graph nodes, 2,000 edges, two consumer groups, and a few `TrialProbe` and `probe-` nodes. Nothing was deleted, and the schema stays applied. Dropping the database removes it all.
