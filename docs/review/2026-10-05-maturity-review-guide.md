# Review guide: how mature is the offering on Spanner, and is it ready to share with the team? (2026-10-05)

This guide is for an independent reviewer (a person or a coding agent). It lists what has been built on the branch and why, what is known to be open, and the facts we checked about the branch's state. It ends with the question the review must answer: **is this ready to share with the team, and if not, what is the shortest path there?**

**Spanner is the target backend.** Redis and Neo4j are today's deployment, and the in-memory backend is the reference for tests. The plan is to run Engram on Cloud Spanner, with one database holding both the ledger and the graph. So weigh every finding by what it means on Spanner. Section "Spanner: the target backend" lists what exists there and what has never been tested. Review task F is the largest part of the review.

Read it top to bottom before opening any code.

## The question

"Share with the team" means three different things. Answer each one separately:

| Audience | What they will do | Ready means |
|---|---|---|
| **A. Engineers** | Review it, merge it, build on it | It can become a reviewable PR, or a series of PRs. CI passes. The code and docs let someone extend it without the author. |
| **B. Researchers** | Use the ontology packs, the eval sets and retrieval for experiments | They can run it locally, load a pack, ingest data, ask questions and measure answers, from the docs alone. |
| **C. Decision makers** | Understand what exists and what it can do | The claims in the docs match the code, and the limits are stated honestly. |
| **D. Platform (Spanner)** | Decide whether to provision a real Spanner instance and run it | It is known what would break or cost on real Spanner, and the first real-instance test plan is small and specific. |

For each audience, give a verdict:

- **Ready**;
- **Ready with caveats** (list them);
- **Not ready** (list the blockers, and the smallest set of changes that would make it ready).

## Rules

- **Read-only.** Do not change, commit or push repository files. Scratch work goes in a temp directory.
- **Evidence or nothing.** Cite `path:line`, a command and its output, or a commit for every claim. A claim you could not check is `UNVERIFIED`, with the reason.
- **No cloud resources.** Do not create a Spanner instance, database or any other GCP resource, and do not use any GCP project. Everything Spanner-related runs on the emulator or is answered from the code and Google's public documentation (cite the page).
- **Judge, don't redesign.** The question is maturity and shareability, not whether you would have built it differently. Note design concerns only when they block one of the audiences.

## Setup

```bash
git checkout claude/wonderful-ramanujan-2cxghz   # head 44aef1b at the time of writing
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest tests/unit tests/conformance -q -m "not integration"   # about 1,780 tests, about 35 s
```

Optional backends:

- **Neo4j:** run as `integration`.
- **Spanner (needed for task F):** the Cloud Spanner emulator, then the Spanner tests as `integration`:

  ```bash
  pip install -e ".[dev,spanner]"
  gcloud emulators spanner start   # or the gcr.io/cloud-spanner-emulator/emulator image, or gateway_main
  export CG_SPANNER_EMULATOR_HOST=127.0.0.1:9010
  pytest tests/conformance tests/unit -m integration -k spanner -q
  pytest tests/integration/test_dual_run.py -q          # Redis-to-Spanner migration path, memory + Neo4j as source
  ```

  The PDLC end-to-end test (`tests/unit/test_pdlc_end_to_end.py`) also has a `spanner` case. Each test creates a fresh database on the emulator (about 0.03 s).
- **Redis Stack:** needed for the Redis ledger. Plain Redis is not enough: the ingest script needs the JSON module.

## State of the branch (checked by us; please re-verify)

| Fact | Detail |
|---|---|
| Branch | `claude/wonderful-ramanujan-2cxghz`, 73 commits ahead of `main`, 0 behind. 276 files changed, about 51,000 lines added. Never merged; no PR open. |
| CI | `.github/workflows/ci.yml` runs only on pushes to `main` and on PRs to `main`, so **CI has never run on this branch**. CI on `main` has failed since at least 2026-02-13: `lint` and `integration-tests` fail, and `unit-tests` passes. |
| Lint and types, whole repo | `ruff check src/ tests/` reports 11 errors, all in `tests/e2e/` and `tests/infra/`, which this branch did not touch. `ruff format --check` flags `src/context_graph/api/routes/simulate.py`, also not touched. `mypy src/` reports 8 errors, in `api/routes/simulate.py`, `adapters/redis/store.py` (unused `type: ignore`) and `adapters/redis/trimmer.py`. The same counts exist without this branch's changes. Files changed by this branch are clean. |
| Tests | 1,977 passed and 28 skipped on memory, Neo4j and the Spanner emulator. One test is deselected in every run: `test_metrics.py::TestMetricsLabelCardinality::test_dynamic_route_uses_template_label` fails on a clean checkout too, independently confirmed. Redis Stack was not available, so the Redis ledger conformance tests skip, and the Redis-specific changes rely on unit tests over a mocked client. |
| Spanner coverage | Verified only on the emulator (1.5.58, `google-cloud-spanner` 3.71). **No real Spanner instance has ever run this code.** CI has no Spanner job (no emulator in `.github/workflows/`), so the Spanner tests run only when someone starts an emulator by hand. The OpenDAL eval (F1 0.91) and the throughput numbers (calls per event) were measured on the **memory** backend, not on Spanner. |
| Onboarding docs | No `README.md`. Entry points: `CLAUDE.md` (project guide), `docs/adr/` (ADR-0001 to ADR-0019), and `docs/runbooks/` (`storage-migration.md`, `pack-authoring.md`, `bulk-import.md`). |
| Earlier reviews | `docs/review/2026-10-05-ontology-ingestion-review-guide.md`: the first review round, verified independently. All five plan items it led to are now done (below). |

## Spanner: the target backend

### What exists

About 1,900 lines in `adapters/spanner/` (`schema.py` 178, `log.py` 783, `subscription.py` 344, `graph.py` 537, `search.py` 46, `errors.py` 31), built to `docs/research/2026-10/ontology/spanner-design-brief.md` (decisions D1 to D6, gaps G1 to G14). The ADR-0019 sections "Step 4 implementation" and "Phase 3 implementation" record what was done.

| Part | What | Why | Where |
|---|---|---|---|
| One database | Ledger, consumer-group state and graph in one Spanner database. Ledger and graph never share a transaction in the write path. | One managed store instead of Redis plus Neo4j. The graph stays a disposable, rebuildable projection (principle 3). | `schema.py` |
| Ledger | `Events`, keyed by `event_id`. A position is `<commit timestamp>/<batch index>/<event id>`, fixed width, so positions sort as strings (D1). The time index leads with `shard = crc32(session_id) mod N` (`CG_SPANNER_SHARDS`, 16) (D3). The event document is a `JSON` column. | Random-UUID keys and a sharded time index avoid a monotonic write hotspot. Sharding by session keeps one session's events in one shard, in order. | `schema.py`, `log.py:76-112` |
| Ingest and dedup | Each append is one read-write transaction: read the ids, then `insert_or_update` the new ones. Duplicates return the stored position, and repeats within a batch are `duplicate`. The batch is written whole or not at all. | Exactly-once by primary key, replacing the Redis Lua script. | `log.py:251-307` |
| Consumer groups | Polling (`CG_SPANNER_POLL_INTERVAL_MS`, 50) over `ConsumerCursors` (one row per group and shard), `ConsumerDeliveries` (pending entries), `ConsumerDeadLetters`. Every read runs **inside a read-write transaction**, relying on range locks so that a cursor never skips an event committed later with an earlier timestamp. | Replace XREADGROUP, XPENDING, XAUTOCLAIM and the DLQ stream. The design brief's D2 (a strong read plus the returned timestamp) was changed to this; see brief §12. | `subscription.py:1-22, 135-180` |
| Graph | Schemaless `GraphNodes(label, node_id, props JSON)` and `GraphEdges` with JSON props, and `CREATE PROPERTY GRAPH EngramGraph` with `DYNAMIC LABEL` and `DYNAMIC PROPERTIES` (D4). Indexes: nodes by `(label, session_id)`; edges by target and by type. Every `GraphBackend` method comes from the generic `adapters/graph_ops.py` over eight primitives. | A new ontology pack needs no DDL. | `schema.py`, `graph.py`, `adapters/graph_ops.py` |
| Native fast paths | Lineage as a GQL `TRAIL` quantified path (`CAUSED_BY{1,n}`). Entity similarity through a cosine vector index (`APPROX_COSINE_DISTANCE`, 10 leaves searched). | The two queries a generic primitive cannot do well. | `graph.py:66-90, 498-530` |
| Keyword search | A full-text search index over `summary`, `keywords` and `search_text`; `SEARCH` and `SCORE`; any-term queries. | Replaces RediSearch BM25. | `log.py:575-616`, `search.py` |
| Retention | `trim` and `expire` as DML, cutoffs from the database clock, keeping anything pending or not yet delivered for a group. | Keep the hot-window-plus-archive model (G7). A skewed app host must not trim fresh rows. | `log.py:632-760` |
| Migration | `python -m context_graph.migration copy`, `mirror`, `compare --to spanner`. Mirror reads Redis in order and imports with `legacy_position`. Cutover needs a short ingest pause. | Move a live Redis deployment without losing order. | `migration/`, `docs/runbooks/storage-migration.md` |
| Tests | 85 conformance cases pass on the emulator (EventLog 18, Subscription 15, GraphStore 24, UserStore 8, GraphReads 17, search 3). The end-to-end run and the PDLC end-to-end test pass with every port on Spanner. The dual run shows zero divergence. | The memory backend defines correct; Spanner must match it. | `tests/conformance/`, `tests/integration/test_dual_run.py` |

### What we know is unproven or weak on Spanner

| # | Item | Detail | Where |
|---|---|---|---|
| S1 | Concurrency and faults | The emulator runs one read-write transaction at a time. Concurrent producers, concurrent consumers, aborts and retries, and consumer crashes mid-transaction have never been exercised. | brief §12; ADR-0019 "Still needs a real instance" |
| S2 | Consumer reads take locks on the ledger | `read_new` scans the undelivered range across all shards inside a read-write transaction. On real Spanner this may contend with ingest (producers inserting into the locked ranges) and between consumers of different groups. The no-skip argument rests on range locks; it has not been checked against Spanner's documented locking. | `subscription.py:1-22, 135-180` |
| S3 | Full-label scans in the graph | `_find_nodes` reads every node of a label and filters in Python, unless the filter is `session_id`. `find_latest`, `find_nodes_matching` (pack lookups), `find_nodes`, and entity listing go through it. Batching (44aef1b) made this one read per flush, but each read is still the whole label: cost grows with graph size. There are no indexes on JSON properties. | `graph.py:200-221`, `graph_ops.py:683-715` |
| S4 | Edge scans | `_edges` with no source, target or type reads the whole `GraphEdges` table. | `graph.py:371-412` |
| S5 | Transaction limits | Imports append 500 events per transaction (`CG_INGEST_IMPORT_BATCH_SIZE`). Projection writes a flush (50, up to 500 suggested for backfills) of nodes and edges per transaction. Neither is checked against Spanner's commit limits (mutations per commit, commit size) with large payloads. | `settings.py:398-401`, `docs/runbooks/bulk-import.md` |
| S6 | Sync client in threads | The sync client runs in `asyncio.to_thread`. Thread pool size against Spanner session pool size, and behaviour under load, are unknown. | `log.py:182`, `graph.py:166` |
| S7 | Schema changes | The DDL creates new databases only. There is no `ALTER` path (for example `search_text` was added straight to the DDL), and no migration tool for Spanner schema. | `schema.py`; ADR-0019 "Keyword channel fix" |
| S8 | Measured on memory only | OpenDAL F1 and the throughput numbers come from the memory backend. Full-text ranking against BM25, approximate-vector recall, and latency per call on Spanner are unmeasured. | `tests/unit/test_pdlc_opendal_eval.py:22-23` |
| S9 | Edition and cost | Spanner Graph, full-text and vector search may need Enterprise edition. The prices in brief §7 (about $90 a month for 100 processing units) come from search extracts and are unverified. Storage grows with `document` JSON, the graph and index copies (`STORING (props)` on three indexes). | brief §7, §9 |
| S10 | Operations | No IAM or service-account setup, no instance provisioning (deliberately), no metrics for Spanner latency, aborts or CPU, no backup or PITR settings (G14). Credentials come from Application Default Credentials only. | `settings.py:525-551` |
| S11 | Blue/green rebuild | `ontology rebuild` needs a second, empty graph target. On Spanner the graph lives in the same database as the ledger, so a rebuild target means a second database, which has not been tried. | `ontology/rebuild.py:206-240` |
| S12 | CI | No CI job starts the emulator, so the Spanner adapter can regress silently. | `.github/workflows/` |

## What has been built, and why

Grouped by workstream, oldest first. "Why" is the problem each piece solved. Every row names where to look; the design records hold the full reasoning.

### 1. Pluggable storage backends (ADR-0019)

| What | Why | Where |
|---|---|---|
| Storage behind ports (`EventLog`, `Subscription`, `GraphBackend`, `KeywordIndex`, `VectorIndex`), opened only through `adapters/registry.py` (`CG_STORAGE_*`). | The core was welded to Redis and Neo4j; Spanner (one managed store for ledger and graph) needed a seam. | `ports/`, `adapters/registry.py`, `tests/unit/test_hex_purity.py` |
| Neutral storage errors; adapters translate driver errors. | Callers could not handle failures without importing driver types. | `ports/errors.py`, `adapters/errors.py` |
| Named graph operations instead of passing query text (`run_session_query` removed). | Cypher leaking through ports made other backends impossible. | `ports/graph_reads.py`, `retrieval/engine.py` |
| In-memory reference backend for every port, plus conformance suites. | One definition of correct behaviour that every backend must pass; fast tests. | `adapters/memory/`, `tests/conformance/` |
| Spanner backend for all ports (ledger, consumer groups, graph, full-text search), verified on the emulator. | The target managed store. | `adapters/spanner/` |
| Ledger copy, mirror (dual run) and comparison between backends. | Moving a live deployment from Redis to Spanner without downtime. | `migration/`, `docs/runbooks/storage-migration.md` |
| Keyword (BM25) channel: `search_text` built at ingest, any-term queries. | The keyword retrieval channel returned nothing. | `domain/keyword_search.py` |
| Worker fixes: `FOLLOWS` survives restarts, idle flush, the pending drain no longer spins. | Found while making workers backend-neutral. | `worker/projection.py`, `worker/consumer.py` |

### 2. Ontology packs (ADR-0018, phases 0 to 3)

| What | Why | Where |
|---|---|---|
| Pack format (YAML) and registry: types, edges, events, projection rules, intents, admission, extraction, lifecycle. Composed, validated, hashed. Today's schema expressed as base packs (`core`, `memory`, `user`). | A new domain needed code changes in many places. Packs make a domain data, not code. | `domain/ontology.py`, `ontology/loader.py`, `ontology/packs/` |
| Projection from packs: a rule value language, a generic `PackGraph` port, and GitHub and Jira webhooks that produce `pdlc.*` events. | The first domain, the product development lifecycle (PDLC), had to be fed by real tools. | `domain/pack_expressions.py`, `domain/pack_projection.py`, `sources/`, `api/routes/webhooks.py` |
| Artifact retrieval from packs: intents, seeds, weighted traversal, admission (superseded, untrusted, proposed), completeness as a set difference. | Questions about artifacts ("where is PAY-341 deployed", "which requirements have no tests") are not session-memory questions. | `retrieval/artifacts.py`, `api/routes/artifacts.py` |
| Extraction profiles (an LLM proposes only declared types), pack versioning (additive, mapping or breaking), reconcile at worker start, blue/green rebuild gated on evaluation sets, `GET /v1/ontology`. | Changing an ontology on a live graph safely, and keeping the LLM in a box. | `domain/pack_extraction.py`, `domain/pack_versioning.py`, `ontology/versioning.py`, `ontology/rebuild.py` |
| PDLC pack, now at 1.7.0. | The first real domain: requests to specs, changes, tests, releases, deployments, incidents and lessons. | `ontology/packs/pdlc.pack.yaml` |
| Evaluation sets: the webhook fixtures (F1 1.00), and the real Apache OpenDAL history (292 deliveries, F1 0.91 after three gap fixes). | Decision 10: retrieval weights are not trusted without a measured set. OpenDAL stands in for our own data. | `tests/fixtures/ontology/pdlc.eval.yaml`, `tests/fixtures/opendal/`, `ontology/evaluation.py` |

### 3. First review round, five plan items (all done)

Findings were verified independently (16 confirmed, 8 partly confirmed, 4 new). The IDs refer to the first guide.

| Item | What | Why | Commit |
|---|---|---|---|
| 1. Common layer | Shared interfaces moved into `core` (`Owned` stays in PDLC); provenance is automatic; lifecycles declare `superseded_states`; admission rules are validated and merged; base packs cannot be replaced from a pack directory. | Two domain packs could not be loaded together, and the base could be silently replaced. | `df1ed29` |
| 2. Projection correctness | Outages are retried in place instead of dead-lettered. `find_latest` orders in the backend and never looks past the event's time. Deployments seen before their merge are linked. Rule regexes have a 0.25 s limit. | Data loss during outages, wrong deployment links at scale, a worker hang. | `117db5d` |
| 3. A second pack works | The eval gate is enforced from the first deploy and in retrieval. Packs can declare key patterns. Hardening: plugin validation, canonical pack order, reserved names, namespace ownership, inert settings logged. An example `crm` pack runs end to end, and there is a pack author runbook. | "Will a new pack just work?" was unproven, and unevaluated weights were served. | `e7f48df` |
| 4. Projection throughput | Pack writes staged per flush, batched lookups (`find_nodes_matching`), one document read per flush, `previous_in_session`, and batch sizes as settings. On OpenDAL, graph calls per event fell from 5.01 to 0.14 and ledger calls from 1.01 to 0.03, with an identical graph. | Backfills were bound by about 4 round trips per event. | `44aef1b` |
| 5. Bulk import | Per-event `created`, `duplicate` or `failed` outcomes. Bodies bounded before and after gzip. `POST /v1/events/import`: admin key, NDJSON, ordering contract, streamed outcomes. Event quota, and a runbook. | There was no safe way to load history, and trusted history could not be bulk imported. | `eacfee6` |

## Known open items (our own list)

1. **CI.** Never run on this branch; `main` CI red since February (lint and integration).
2. **Size.** One 73-commit branch with about 51,000 added lines; no PR.
3. **No README;** onboarding is spread over `CLAUDE.md`, the ADRs and the runbooks.
4. **Redis Stack.** The Redis paths are not exercised against a real Redis Stack in our environment.
5. **Webhooks.** Sources are hardwired to GitHub and Jira (finding 2.3).
6. **Bare transitions.** A rule that only transitions a node writes no provenance.
7. **`UserProfile` key.** `profile_id` in `adapters/graph_ops.py` against `user_id` in the user pack (predates packs).
8. **Other failures.** Failures other than outages are retried only after a worker restart.
9. **Dedup window.** Dedup lasts only the retention window, not durably.
10. **Inert pack settings.** Declared but inert: `embed_fields`, `derived_proposals`, `lifecycle.decay`, `mappings`.
11. **Not real data yet.** Both eval sets stand in for our own data: the fixtures are synthetic, and OpenDAL is a public proxy.
12. **Pending behaviour changes.** PDLC intents need `evaluate --record` after upgrading; batch ingest status codes changed (422 or 503 instead of 201 when nothing is stored).
13. **Spanner.** S1 to S12 in "Spanner: the target backend": above all, never run on a real instance.

## What to review

### A. Re-verify the state facts

Re-run the commands behind each row of "State of the branch". Report any that differ.

### B. Maturity scorecard

Score each dimension from 1 (prototype) to 5 (production), with evidence and the single biggest gap:

1. **Correctness.** Do the core paths do what the docs say? Spot-check at least five rows of the "What has been built" tables against code and tests.
2. **Test coverage and honesty.** Do the tests exercise real behaviour, or mostly mocks? Are there skipped, deselected or pinned-but-wrong tests?
3. **Operability.** Can it be deployed, configured, observed (metrics, logs) and recovered? Read `settings.py`, the runbooks and the worker start-up.
4. **API stability.** Are breaking changes to clients documented and versioned?
5. **Security.** Auth on admin and import routes, trust granting, webhook signatures, and input bounds.
6. **Performance.** Are the measured numbers credible, and what is unmeasured? They were taken on the memory backend; say what they predict, or don't, for Spanner.
7. **Documentation and onboarding.** Can a new engineer start, and a researcher run an experiment, from the docs alone?
8. **Research readiness.** Are the eval sets and the metric (F1) adequate to trust retrieval weights? What is missing to evaluate on our own data?

### F. Spanner readiness (the largest task)

Run the Spanner tests on the emulator first (Setup), then answer each question with evidence. The question is not "does it pass on the emulator" (it does) but "what happens on a real instance".

1. **Schema review.** Read `adapters/spanner/schema.py` against Google's schema design guidance. Check keys and hotspots (D3), interleaving (none is used: should `GraphEdges` be interleaved in `GraphNodes`?), the three `STORING (props)` indexes, `STRING(MAX)` keys, and the generated `session_id` column. What would you change before the first real instance, given that there is no `ALTER` path yet (S7)?
2. **Consumer correctness (S1, S2).** Is the no-skip argument in `subscription.py:1-22` sound under Spanner's documented concurrency (commit timestamps, lock modes, aborts)? What contention should we expect between ingest and `read_new` at, say, 100 and 1,000 events per second? Is there a cheaper design that keeps the guarantee? Name the tests the first real-instance run must include.
3. **Query shapes (S3, S4).** List every graph read that scans a whole label or table, and the calls that reach it during projection (pack lookups) and retrieval (artifact word seeds, `CG_ONTOLOGY_RETRIEVAL_WORD_SCAN_LIMIT`). For each, give the fix: a generated column with an index, a JSON search index, or a native GQL query. Rank them by what breaks first as the graph grows.
4. **Limits (S5).** Estimate mutations and bytes per commit for a 500-event import chunk and a 500-event projection flush, from the column counts and indexes. Which settings must be capped on Spanner?
5. **Migration path.** Read `docs/runbooks/storage-migration.md` and `migration/`. Run the dual-run test. Is the Redis-to-Spanner path complete enough for a real cutover? Check position compatibility (`legacy_position`), the ingest pause, and rollback.
6. **Cost.** From brief §7 and Google's public pricing page (cite it), give a rough monthly figure for a minimal real deployment (one region, smallest compute, our expected data size). Say which edition is required for the property graph, full-text and vector features, and whether that changes the figure.
7. **Readiness verdict.** Pick one:
   - ready for a real-instance trial as is;
   - ready after named changes;
   - not ready.

   Then write the first real-instance test plan: its tests, its duration, and its rough cost. Keep it small enough for a trial instance.

### C. Cold-start test

Take the role of a new team member with only the repository. Using only the docs, try to:

1. run the tests;
2. start the API on the memory backend;
3. load the example `crm` pack (`tests/fixtures/packs/crm/`);
4. ingest its events;
5. ask an artifact question.

Then repeat steps 2 to 5 with every storage port on the Spanner emulator (`CG_STORAGE_*=spanner`, `CG_SPANNER_EMULATOR_HOST`, `CG_SPANNER_CREATE_IF_MISSING=true`). Note every point where you had to read code or guess. This is the most direct evidence for audiences A and B.

### D. Shareability verdict

For each audience (A, B, C, D), give a verdict, the blockers, and the smallest set of changes that would make it ready. Say whether the branch should go in as one PR or as several, and if several, propose the split.

### E. Next steps

Rank the open items above (1 to 12 and S1 to S12), plus anything you find, by what they unblock, with a rough size (S, M or L) for each.

## What to return

One Markdown report:

```markdown
## Verdict
| Audience | Verdict | Blockers | Smallest path to ready |
|---|---|---|---|
| A. Engineers | ... | ... | ... |
| B. Researchers | ... | ... | ... |
| C. Decision makers | ... | ... | ... |
| D. Platform (Spanner) | ... | ... | ... |

## State facts
| Fact | Confirmed / differs | Evidence |

## Maturity scorecard
| Dimension | Score (1-5) | Evidence | Biggest gap |

## Spanner readiness
| Question (F1-F7) | Finding | Evidence | Fix before a real instance? |

Readiness verdict: ...

First real-instance test plan:
| Test | What it proves | Duration | Rough cost |

## Cold-start log
1. Step, what happened, where the docs fell short.

## Spot-checks
| Claim (table row) | Holds? | Evidence |

## Ranked next steps
1. **[S/M/L] Title.** What it unblocks. Evidence.

## Anything else that would embarrass us if shared as is
```

Keep it under 3,000 words, at least a third of it on Spanner. Every verdict and score carries evidence.
