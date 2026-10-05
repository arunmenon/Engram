# Review guide: how mature is the offering, and is it ready to share with the team? (2026-10-05)

This guide is for an independent reviewer (a person or a coding agent). It lists what has been built on the branch and why, what is known to be open, and the facts we checked about the branch's state. It ends with the question the review must answer: **is this ready to share with the team, and if not, what is the shortest path there?**

Read it top to bottom before opening any code.

## The question

"Share with the team" means three different things. Answer each one separately:

| Audience | What they will do | Ready means |
|---|---|---|
| **A. Engineers** | Review it, merge it, build on it | It can become a reviewable PR, or a series of PRs. CI passes. The code and docs let someone extend it without the author. |
| **B. Researchers** | Use the ontology packs, the eval sets and retrieval for experiments | They can run it locally, load a pack, ingest data, ask questions and measure answers, from the docs alone. |
| **C. Decision makers** | Understand what exists and what it can do | The claims in the docs match the code, and the limits are stated honestly. |

For each audience, give a verdict:

- **Ready**;
- **Ready with caveats** (list them);
- **Not ready** (list the blockers, and the smallest set of changes that would make it ready).

## Rules

- **Read-only.** Do not change, commit or push repository files. Scratch work goes in a temp directory.
- **Evidence or nothing.** Cite `path:line`, a command and its output, or a commit for every claim. A claim you could not check is `UNVERIFIED`, with the reason.
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
- **Spanner:** the emulator, with `CG_SPANNER_EMULATOR_HOST`.
- **Redis Stack:** needed for the Redis ledger. Plain Redis is not enough: the ingest script needs the JSON module.

## State of the branch (checked by us; please re-verify)

| Fact | Detail |
|---|---|
| Branch | `claude/wonderful-ramanujan-2cxghz`, 73 commits ahead of `main`, 0 behind. 276 files changed, about 51,000 lines added. Never merged; no PR open. |
| CI | `.github/workflows/ci.yml` runs only on pushes to `main` and on PRs to `main`, so **CI has never run on this branch**. CI on `main` has failed since at least 2026-02-13: `lint` and `integration-tests` fail, and `unit-tests` passes. |
| Lint and types, whole repo | `ruff check src/ tests/` reports 11 errors, all in `tests/e2e/` and `tests/infra/`, which this branch did not touch. `ruff format --check` flags `src/context_graph/api/routes/simulate.py`, also not touched. `mypy src/` reports 8 errors, in `api/routes/simulate.py`, `adapters/redis/store.py` (unused `type: ignore`) and `adapters/redis/trimmer.py`. The same counts exist without this branch's changes. Files changed by this branch are clean. |
| Tests | 1,977 passed and 28 skipped on memory, Neo4j and the Spanner emulator. One test is deselected in every run: `test_metrics.py::TestMetricsLabelCardinality::test_dynamic_route_uses_template_label` fails on a clean checkout too, independently confirmed. Redis Stack was not available, so the Redis ledger conformance tests skip, and the Redis-specific changes rely on unit tests over a mocked client. |
| Onboarding docs | No `README.md`. Entry points: `CLAUDE.md` (project guide), `docs/adr/` (ADR-0001 to ADR-0019), and `docs/runbooks/` (`storage-migration.md`, `pack-authoring.md`, `bulk-import.md`). |
| Earlier reviews | `docs/review/2026-10-05-ontology-ingestion-review-guide.md`: the first review round, verified independently. All five plan items it led to are now done (below). |

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
6. **Performance.** Are the measured numbers credible, and what is unmeasured (Neo4j and Spanner latencies, large graphs)?
7. **Documentation and onboarding.** Can a new engineer start, and a researcher run an experiment, from the docs alone?
8. **Research readiness.** Are the eval sets and the metric (F1) adequate to trust retrieval weights? What is missing to evaluate on our own data?

### C. Cold-start test

Take the role of a new team member with only the repository. Using only the docs, try to:

1. run the tests;
2. start the API on the memory backend;
3. load the example `crm` pack (`tests/fixtures/packs/crm/`);
4. ingest its events;
5. ask an artifact question.

Note every point where you had to read code or guess. This is the most direct evidence for audiences A and B.

### D. Shareability verdict

For each audience (A, B, C), give a verdict, the blockers, and the smallest set of changes that would make it ready. Say whether the branch should go in as one PR or as several, and if several, propose the split.

### E. Next steps

Rank the open items above, plus anything you find, by what they unblock, with a rough size (S, M or L) for each.

## What to return

One Markdown report:

```markdown
## Verdict
| Audience | Verdict | Blockers | Smallest path to ready |
|---|---|---|---|
| A. Engineers | ... | ... | ... |
| B. Researchers | ... | ... | ... |
| C. Decision makers | ... | ... | ... |

## State facts
| Fact | Confirmed / differs | Evidence |

## Maturity scorecard
| Dimension | Score (1-5) | Evidence | Biggest gap |

## Cold-start log
1. Step, what happened, where the docs fell short.

## Spot-checks
| Claim (table row) | Holds? | Evidence |

## Ranked next steps
1. **[S/M/L] Title.** What it unblocks. Evidence.

## Anything else that would embarrass us if shared as is
```

Keep it under 2,000 words. Every verdict and score carries evidence.
