# Second-opinion guide: ontology packs and ingestion review (2026-10-05)

This guide is for an independent reviewer (a person or a coding agent) checking a review we already ran. Read it top to bottom before opening any code.

## Your job

A review of the code at commit `0c2ce19` (branch `claude/wonderful-ramanujan-2cxghz`) produced 24 findings in three areas, listed below. For each finding:

1. **Verify it against the code.** Open the cited files and lines (they may have drifted a few lines), and decide one of:
   - `CONFIRMED`: the claim and its failure scenario hold.
   - `PARTLY`: the mechanism is real but the scenario, scope or severity is wrong. Say what is wrong.
   - `REJECTED`: the claim is false, or the code already handles it. Cite the code that shows it.
2. **Check the severity** and propose a different one if you disagree.
3. **Check the proposed fix.** Say whether it would work, what it would break, and whether there is a simpler fix.

Then look for **what the review missed** in the same three areas: up to 5 new findings, held to the same standard of evidence.

Rules:

- **Read-only.** Do not change, commit or push repository files. Scratch scripts go outside the repo or in a temp directory.
- **Evidence or nothing.** Every verdict cites `path:line`. A finding you could not check is `UNVERIFIED`, with the reason. Do not guess.
- **Reproduce where it is cheap.** The memory backends run without any services.

## Setup

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest tests/unit tests/conformance -q -m "not integration"   # about 1,700 tests, about 25 s
```

Neo4j, Redis and Spanner are not needed. Findings about those adapters are checked by reading the code.

Background reading, in this order:

1. `CLAUDE.md`: architecture, principles, project map.
2. `docs/adr/0018-ontology-packs.md`: the pack design and its implementation notes.
3. `src/context_graph/ontology/packs/core.pack.yaml` and `pdlc.pack.yaml`.

Key modules:

| Concern | Files |
|---|---|
| Pack model, composition, validation | `src/context_graph/domain/ontology.py`, `src/context_graph/ontology/loader.py` |
| Rule expressions | `src/context_graph/domain/pack_expressions.py` |
| Projection | `src/context_graph/domain/pack_projection.py`, `src/context_graph/worker/projection.py`, `src/context_graph/worker/pack_projection.py` |
| Retrieval | `src/context_graph/retrieval/artifacts.py`, `src/context_graph/domain/pack_intents.py` |
| Versioning and gate | `src/context_graph/domain/pack_versioning.py`, `src/context_graph/ontology/versioning.py`, `src/context_graph/ontology/evaluation.py`, `src/context_graph/ontology/rebuild.py` |
| Ingest API | `src/context_graph/api/routes/events.py`, `src/context_graph/api/routes/webhooks.py`, `src/context_graph/api/rate_limit.py`, `src/context_graph/api/middleware.py` |
| Ledger adapters | `src/context_graph/adapters/redis/store.py`, `src/context_graph/adapters/redis/lua/ingest.lua`, `src/context_graph/adapters/spanner/log.py`, `src/context_graph/adapters/memory/log.py` |
| Graph adapters | `src/context_graph/adapters/neo4j/pack_graph.py`, `src/context_graph/adapters/spanner/graph.py`, `src/context_graph/adapters/graph_ops.py` |

## Area 1: How packs compose

Base packs `core`, `memory` and `user` always load. Extension packs (today only `pdlc`) come from `CG_ONTOLOGY_PACKS` and `CG_ONTOLOGY_PACK_DIRS`. All names share one global namespace.

| ID | Sev | Claim | Where to look |
|---|---|---|---|
| 1.1 | Medium | A file in `CG_ONTOLOGY_PACK_DIRS` named `core.pack.yaml` (or `memory`, `user`) silently replaces the built-in base pack, because pack directories are searched first. The projection code still writes the schema hardcoded in `domain/models.py`, so the registry, `GET /v1/ontology` and the graph disagree. | `ontology/loader.py` `find_pack` (about line 171); `worker/projection.py` |
| 1.2 | Medium | The common layer is only half in packs. The interfaces `Lifecycled`, `Owned`, `Sourced` and `Claim` are declared in `pdlc`, not `core`, and interface names are global, so a second domain pack declaring `Sourced` cannot load next to `pdlc`. The semantics are hardcoded: the properties `status`, `source_trust` and `link_status`, the edges `SUPERSEDES` and `DERIVED_FROM`, the states `{superseded, reversed}`, and the admission rule keys. `graph_ops.py` keys `UserProfile` by `profile_id` while the user pack says `user_id`. | `packs/pdlc.pack.yaml:38-44`; `domain/ontology.py:743-748`; `retrieval/artifacts.py` (`SUPERSEDED_STATES`, `_admit`); `domain/pack_projection.py`; `adapters/graph_ops.py:70-99` |
| 1.3 | Medium | Regex denial of service. Pack expression patterns are checked only for syntax, and matching runs with no time limit on up to 100,000 characters. `regex($.body, '^(a+)+$')` on 26 characters took about 2.4 s, doubling per character, and a hang stalls the projection consumer. | `domain/pack_expressions.py` (`MAX_TEXT_LENGTH`, `_call`) |
| 1.4 | Low | Typos are ignored silently: a misspelled `plugin:` value, a misspelled admission key, and a transition to an unknown state (dropped without a log). | `domain/ontology.py` (`IntentDef.plugin`); `retrieval/artifacts.py` `_admit`; `domain/pack_projection.py` transitions |
| 1.5 | Low | When two packs have rules on the same event, they run in `CG_ONTOLOGY_PACKS` order, which the version hash does not record. | `domain/ontology.py` `projection_rules`; the version hash |
| 1.6 | Low | No reserved names: a pack may declare a type named `OntologyState`, or events in another pack's namespace. | `adapters/neo4j/ontology_schema.py:32-35` |

Reproduce 1.1:

1. Copy `src/context_graph/ontology/packs/core.pack.yaml` into a temp directory and change one `why` intent keyword.
2. Call `load_registry(["pdlc"], search_dirs=[tmp])` and confirm it loads without error.
3. Classify "why did it fail" with `RegistryIntents`.

Reproduce 1.3: build a `PackProjector` from a toy pack whose rule uses `regex($.body, '^(a+)+$')`, then time `plan()` on bodies of `'a' * n + 'b'` for n = 20 to 26.

## Area 2: A brand-new pack, end to end

The question: if someone writes a new pack tomorrow (say `crm`), does it work in ingestion and retrieval without code changes?

| ID | Sev | Claim | Where to look |
|---|---|---|---|
| 2.1 | High | Two domain packs that both declare the conventional interfaces (`Sourced`, `Lifecycled`) cannot be active together: `CG_ONTOLOGY_PACKS=pdlc,crm` fails at startup. This is the same root cause as 1.2. | `domain/ontology.py:743-747` |
| 2.2 | High | Question seeding is tuned to PDLC. Key tokens must look like `PAY-341` (`[A-Z][A-Z0-9]+-\d+`), a path, a version, or `#N` on an integer key. "which account does deal D-1 belong to" seeds nothing. | `retrieval/artifacts.py` (`_KEY_TOKEN`, `_NUMBER_REF`, `_seeds`) |
| 2.3 | High | Webhooks and trust are PDLC-only in code. `/v1/webhooks/{source}` knows only `github` and `jira`; the default trusted sources are those two; generic ingest refuses `webhook:` agent ids. A new pack's events are therefore all untrusted, and PDLC-style admission rules hide them from answers. | `api/routes/webhooks.py:56-57, 94-97, 132, 148`; `settings.py` (`trusted_sources`); `api/routes/events.py:88` |
| 2.4 | Medium | Provenance is opt-in. `DERIVED_FROM` edges are written only if the pack adds `DERIVED_FROM` under `extends_core_edges`; otherwise provenance is silently missing, which breaks design principle 1. | `domain/pack_projection.py` (about line 365) |
| 2.5 | Medium | Superseded detection and admission rule names are hardcoded. A lifecycle state such as `replaced` is served as current. | `retrieval/artifacts.py` (`SUPERSEDED_STATES`, `_admit`) |
| 2.6 | Medium | The eval gate (ADR-0018 decision 10) is not enforced on first deploy. `eval_required` is set only when a pack is added relative to a recorded state, so on a fresh graph a new pack's intents go live with no eval. | `domain/pack_versioning.py` `_compare_packs` (about line 305); `ontology/versioning.py` reconcile on `initial` |
| 2.7 | Medium | These pack fields are declared and validated but do nothing at runtime: `embed_fields`, `derived_proposals`, `lifecycle.decay`, `terminal_states_reduce_importance`, `link_policy.read_time_threshold`, `mappings`. | `grep -rn embed_fields src` (only `domain/ontology.py`); `worker/enrichment.py` |
| 2.8 | Low | No test runs a non-PDLC pack end to end; `ArtifactRetriever` is exercised only with PDLC data. | `tests/unit/` |

Reproduce area 2:

1. Write a minimal `crm.pack.yaml` modelled on the `pdlc` structure:
   - node types `Account`, `Contact` and `Deal`, with a lifecycle on `Deal`;
   - edges `BELONGS_TO` and `WORKS_AT`;
   - events `crm.deal.created` and `crm.deal.closed`, each with a projection rule;
   - one intent;
   - `DERIVED_FROM` under `extends_core_edges`.
2. Load it with `load_registry(["crm"], search_dirs=[tmp])`, project a few events with `PackProjector` into `MemoryGraphStore` (copy the patterns in `tests/unit/test_pack_projection.py`), and query with `ArtifactRetriever` (patterns in `tests/unit/test_pdlc_retrieval_eval.py`).
3. Then try `load_registry(["crm", "pdlc"])`, and run `rebuild()` with and without a `crm.eval.yaml` (pattern in `tests/unit/test_pdlc_opendal_eval.py`).

## Area 3: Bulk ingestion

Today's bulk path is `POST /v1/events/batch` (at most 1,000 items, per-item errors, one `append_batch` store call), followed by asynchronous projection workers. These figures were measured on the memory backend:

| Measure | Result |
|---|---|
| Ingest, 2,000 events | 0.16 s |
| Projection, core events | 0.04 graph calls per event |
| Projection, PDLC events | 4.04 graph calls per event |

| ID | Sev | Claim | Where to look |
|---|---|---|---|
| 3.1 | High | Pack projection runs per event: each pack event's plan becomes about four graph transactions (upsert nodes, change states, lookups, upsert edges), never combined across the 50-event flush. | `worker/projection.py` (loop over `pack_events`, about line 166); `worker/pack_projection.py` `apply_plan`; `adapters/neo4j/pack_graph.py:83-100` |
| 3.2 | High | `to_latest` lookups take at most `lookup_limit` (1,000) matches in key order, then pick the newest of that subset, so with more than 1,000 candidates the edge can point at the wrong node (only a warning is logged). Lookup fields are not indexed: Neo4j filters without an index, and Spanner reads every node of the label and filters in Python. | `worker/pack_projection.py:60-76`; `adapters/neo4j/pack_graph.py` `find_nodes`; `adapters/spanner/graph.py:214-221`; `adapters/neo4j/ontology_schema.py:50-55` |
| 3.3 | High | Event order is arrival order, not `occurred_at`. Concurrent batches for one session interleave, and `FOLLOWS` follows arrival order. No one-writer-per-session contract is documented. | `adapters/redis/lua/ingest.lua:47-54`; `worker/projection.py:134-136, 195-205` |
| 3.4 | Medium | On a cache miss, finding the previous event in a session reads the whole session stream (`XRANGE - +`), so long sessions cost O(n²). | `adapters/redis/store.py:643-657`; `worker/projection.py:199` |
| 3.5 | Medium | Documents are fetched with one call per event per flush. | `worker/projection.py:246`; `adapters/redis/store.py:628-632` |
| 3.6 | Medium | Trusted (PDLC) history cannot be bulk-imported: the batch endpoint refuses `webhook:` agent ids, and webhooks take one delivery per request. | `api/routes/events.py:88-89`; `api/routes/webhooks.py:174-177` |
| 3.7 | Medium | The rate limit counts requests, not events (120 per minute per IP), and is per process. | `api/rate_limit.py:84-96`; `api/middleware.py:133`; `settings.py` |
| 3.8 | Medium | The ingest routes have no body-size cap, timeout or gzip support; the webhook route's size cap is not reused. | `api/routes/events.py:121, 169`; `api/routes/webhooks.py:79-90` |
| 3.9 | Low | Redis returns the string `"DEDUP"` as a `global_position` for a duplicate. A store error mid-batch returns a bare 500 although the Redis pipeline is not transactional. Dedup entries are pruned after the retention window, so re-importing older history duplicates it. | `adapters/redis/lua/ingest.lua:40`; `adapters/redis/store.py:260-292, 297-320` |
| 3.10 | Low | The flush size (50) and timeout are class constants, while the subscription reads 10 at a time. | `worker/projection.py:50-51`; `worker/consumer.py:50` |

Reproduce 3.1: count graph calls by wrapping `MemoryGraphStore` methods with a counter, then project 200 `pdlc.change.merged` and `pdlc.service.deployed` events through `ProjectionConsumer` (pattern in `ontology/rebuild.py` `project_ledger`).

Reproduce 3.2: the `OCCURRED_ON` rule (`pdlc.pack.yaml`, `pdlc.incident.detected`) matches on `environment` and `artifact_id` together, so the candidates are redeployments of one artifact to one environment.

1. Create 1,005 `Deployment` nodes with the same `environment` and `artifact_id`, with key order differing from `started_at` order.
2. Ingest a `pdlc.incident.detected` event, leaving `CG_ONTOLOGY_LOOKUP_LIMIT` at its default of 1,000.
3. Check which deployment `OCCURRED_ON` points at.
4. Also judge how realistic this is (challenge question 2) and whether other `to_latest` or `match` rules have wider candidate sets.

## Questions we especially want challenged

1. **Fix for 1.2 / 2.1.** Is moving the shared interfaces and their semantics into `core` the right fix, or is per-pack interface scoping (`pdlc:Sourced`) better? What breaks in `pdlc` either way?
2. **Severity of 3.2.** Is it a correctness bug at realistic scale, or does `match` on `environment` plus `artifact_id` narrow candidates enough in practice?
3. **Ordering in 3.3.** Should the system sort by `occurred_at` (an import mode), or is "one writer per session" the right contract?
4. **The proposed import endpoint.** Is an admin-keyed `POST /v1/events/import` (gzip NDJSON, trust by credential, streamed per-item status) the right shape, or should bulk import go through the `migration` package instead?

## What to return

Return one Markdown report in this format:

```markdown
## Verdicts
| ID | Verdict | Severity (ours → yours) | Evidence | Notes on the fix |
|---|---|---|---|---|
| 1.1 | CONFIRMED | Medium → Medium | ontology/loader.py:171 | ... |
...

## Missed findings
1. **[Severity] Title.** Claim. Evidence `path:line`. Failure scenario. Suggested fix.

## Answers to the challenge questions
1. ...

## Reproductions run
- What you ran, and the result (paste the key output lines).
```

Keep it under 1,500 words. Every verdict carries evidence, and every `REJECTED` or `PARTLY` says what the review got wrong.
