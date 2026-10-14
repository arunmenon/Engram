# UUID Event subgraph access verification — issue #61

## What this fixes

An Event received through Engram has a UUID identity. Subgraph retrieval used to look for IDs starting with `evt` when updating access metadata. As a result, an Event could be returned successfully while its stored access count remained zero.

The fix checks the returned node's validated `Event` type after pagination. Each returned Event receives one increment and a request-time `last_accessed_at`. Entities and pack artifacts keep their existing properties. No new table, service, or access-accounting abstraction was added.

## Frozen scenarios and acceptance path

The runner saves payloads, expected identities and effects, selected configurations and source hashes before exporting/resetting the existing assessment database. The prior owner/fingerprints must match, and export readback/digest verification must pass before exact-key reset. Final data is retained.

Authenticated HTTP `/v1/events` → Spanner Events ledger → five real worker loops → Spanner graph → authenticated HTTP `/v1/query/subgraph`.

Each configuration receives two observations and a session-end event, plus an unrelated owner/session observation. The real extraction worker creates an Entity from explicitly scripted external provider output. The real consolidation worker can create summaries and, when Memory is selected, an Episode. Scripted provider output makes this an accounting test, not an LLM quality evaluation. Workers stop and join through their normal lifecycle before read accounting is compared; this avoids concurrent projection/summarization changes obscuring read effects.

| Case | What we ask Engram to do | Required result |
|---|---|---|
| AC01 | Retrieve the session twice | All three UUID Events return; each count advances once per read; timestamp falls inside that request |
| AC02 | Return Events together with an Entity, and an Episode with Memory selected | Only Events receive access metadata; non-Event properties stay unchanged |
| AC03 | Read one-node cursor pages until an Event page is reached | That returned Event advances once; all other Event counts stay unchanged on that page |
| AC04 | Read a cursor page beyond the bounded result set | Empty answer; no access writes |

Every read checks exact allowed Event identities and provenance, unchanged non-access Event properties, unchanged unreturned/non-Event node properties, all six other application-table fingerprints, and every physical GraphNodes column except the JSON properties compared separately. Unpaged reads must be untruncated. The unrelated owner/session Event stays unchanged throughout. This is a controlled fixture exclusion check, not a guarantee that session filtering constrains every retrieval channel.

## Review and local verification

The initial regression failed because UUID Event reads recorded no access. The runtime correction is one line in `retrieval/engine.py`. Tests exercise UUID identities, repeated reads and pagination, plus an Event/Entity key collision and an Entity with an `evt` prefix through the public composed graph/read interfaces.

The first pagination fixture incorrectly assumed seed-only behavior and then seed-first ranking. Before cloud execution, the fixture was corrected to include a real neighbor and the existing neighbor-boost ordering. The access-count oracle was retained. Astra then required an Event page, a genuinely empty cursor page instead of an empty-session assumption, and complete table/physical-column checks. These were applied before the live run.

Review: [Astra preflight](subgraph-access-review/astra-preflight.md). Runtime source, tests and live evidence require final independent review before issue closure.

## Stakeholder walkthrough

1. Open the run's `manifest.json`: see the two pack selections, four source payloads per selection and the expected accounting effects declared before execution.
2. In the configuration record, inspect the four `/v1/events` requests and successful responses. Compare `processed_baseline.events` and the four expected UUIDs: these are real accepted ledger entries.
3. Inspect `processed_baseline.nodes`: all four Event projections, the extracted Entity and optional Episode were produced by real workers. Worker joins and zero pending/DLQ are recorded.
4. Compare the first and repeated subgraph responses with `read_snapshots`: each of the three returned Events advances by one each time; timestamps are request-bounded. Entity/Episode/Summary properties and unrelated data remain unchanged.
5. Inspect AC03's actual one-node Event page: only that Event advances. Inspect AC04's empty cursor page: nothing changes.
6. Check the final retained record, independent post-process readback, Astra verdict and GitHub reconciliation. Passing this slice closes only #61; broader feature umbrellas remain open.

## Limits

Two sequential private bound configurations: Core and Core+PDLC+Memory. This does not prove concurrent counter increments, all pack combinations, the public multi-tenant dispatcher, concurrent tenant isolation, all retrieval endpoints or pilot readiness. No historical migration. Existing potential read/modify/write concurrency behavior is unchanged; sequential exact increments are the bounded claim.

## Repeat safely

Run `scripts/engram_subgraph_access_demo.py` with a new `--run-id` and the current `--previous-record` for the authorized assessment target. It refuses evidence overwrite, wrong target or mismatched owner/fingerprints. It exports and verifies the previous retained dataset before reset. Do not reuse an obsolete retained record or reset a protected goal/production database. Repeating changes the retained assessment dataset and must remain within the authorized slice.

## Results and issue reconciliation

Run: [subgraph-access-1014-01](runs/subgraph-access-1014-01/manifest.json), 2026-10-14. Both configurations passed on the first cloud attempt.

| Configuration | Assertions | Unpaged response | One-node response | Final source Event counts |
|---|---:|---|---|---|
| Core | 97 | Three Events + Entity | Session-end Event | 2, 2, 3 |
| Core+PDLC+Memory | 131 | Three Events + Entity + two Episode/Summary snapshots | Second observation Event | 2, 3, 2 |

AC04's empty cursor page did not change any count. Both configurations returned an Event on the first one-node page, so the bounded fallback pagination loop was not needed. Each unrelated Event remained at baseline. Multiple Memory snapshots reflect consolidation as the session grew; this test checks their access metadata remains unchanged, not a new assertion that the full Memory lifecycle has been reevaluated.

Evidence: [Core](runs/subgraph-access-1014-01/core.json), [composed](runs/subgraph-access-1014-01/pdlc-memory.json), [retained owner/fingerprints](runs/subgraph-access-1014-01/pdlc-memory-retained.json). Prior epoch37 data was exported and verified before reset to38; Core data was exported and verified before reset to39. Final composed data is retained.

Local targeted regression: 25 passed; affected Memory/User/engine tests: 89 passed. The first broad run exposed23 test-helper failures: those helpers passed `selected.reads`, a read-only GraphOperationReads, instead of the production `ComposedGraphReads(selected)` wrapper that deliberately permits access accounting. The old UUID omission masked this setup error. Only the three test construction sites were corrected; no Memory/User expected behaviors were removed. Both broad logs are retained. Final broad rerun: **2834 passed, 13 skipped**, excluding the previously documented `test_pdlc_end_to_end.py` evaluation-gate file. Ruff and runtime mypy passed.

The fresh-process audit initially hit an audit-script-only None comparison for the baseline last_accessed_at; the comparator was corrected, with the failed audit log retained. It did not require data repair, changes to runtime or a new cloud run. Monitoring export still reports403; no monitoring readiness claim.

Fresh-process readback matched retained owner epoch39, every application-table fingerprint and the full retained snapshot. All217 runtime/YAML/script hashes matched the frozen run. The audit independently checked both export digests and every saved read's Event deltas/non-Event preservation: [post-process audit](runs/subgraph-access-1014-01/post-process-recheck.json). Final independent verdict and GitHub reconciliation follow below.
