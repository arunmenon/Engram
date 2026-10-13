# Enrichment ordering — issue #29

Status: complete for the bounded enrichment slice, independently reviewed, published and reconciled in GitHub. Issue #29 is closed; broader umbrellas and separately discovered defects remain open. Failed cloud01 and cloud02 remain retained. Recorded stakeholder walkthrough provided here; no live stakeholder attendance or sign-off inferred.

## Outcome

An accepted event must receive its keywords, importance and optional embedding regardless of whether projection or enrichment runs first. Neither stale projection nor a duplicate enrichment delivery may reset later importance adjustments or access metadata. This is metadata reliability, not new entity extraction or smarter importance scoring. Core remains mandatory; optional packs do not disable common Event enrichment.

## Frozen acceptance

Public seams: authenticated HTTP ingestion/retrieval, real worker processing and subscription progress, graph port reads/writes. Reference tests supplement real Spanner. External embedding and storage failure injection is labeled; no acceptance artifact insert or repair.

| Case | Input / sequence | Required result |
|---|---|---|
| EN01 | observation.input, race-tool, hint7; enrichment before projection | No partial Event; delivery pending, then exact keywords observation/input/race-tool, importance 7, scripted384vector after projection |
| EN02 | Stop enrichment during EN01 dependency wait; fresh worker before projection | Same pending delivery recovered, no ACK/DLQ loss, eventual EN01 result |
| EN03 | Same metadata, distinct event; projection before enrichment | Initially empty keywords; final exact keywords, importance 7 and vector |
| EN04 | Duplicate exact EN03 HTTP body; public projection-worker replay | One ledger identity; intentional graph-port importance adjustment7→8, then preserve8 and positive access count through fresh-worker projection and enrichment replay; no extra artifacts/edges |
| EN05 | No hint; embedding service absent | Exact keywords, importance5; no invented embedding |
| EN06 | No hint; external embedding provider throws; replay EN03 | Keywords/default 5 on new event; EN03 existing embedding retained |
| EN07 | Hint7; graph vector storage transiently unavailable after keyword commit | Pending while vector missing, no ACK; recover exact vector without another provider call within delivery |

All seven cases run sequentially for Core, Core+User, Core+User+Memory, Core+PDLC, Core+PDLC+Memory. These observation events assess common enrichment under those selections; they do not prove every optional-pack producer. Reference cases additionally cover single/batch projection, adjusted importance, missing Event, missing ledger documents, restart and SDK transaction-current null/zero/adjusted importance. Event vectors are JSON properties; the dedicated Entity ANN embedding column must remain null for Events. No Event ANN claim. Declare vector fixture as 384 components of 0.25, fixed before execution. UUID5 IDs derive from run+configuration+case, fixed before API calls. No endpoint/response-derived oracle.

## Existing components and smallest change

Use current EnrichmentConsumer, BaseConsumer transient retries, graph store, existing Spanner transaction helpers and create-only `_merge_nodes`. No new table, service, queue or scoring framework. Projection writes source fields; its derived-field initial values apply only on creation. Annotation operations require the projected Event and initialize importance only when absent. Existing importance adjustments take precedence. Missing ledger documents are re-fetched inside retry, never treated as successful empty work. Optional provider absence/failure remains explicit degradation, not guaranteed vector repair.

## Execution / retention

Target exclusively projects/portiq-mvp/instances/engram-experiment/databases/engram-assess-1010a-pdlc. Previous retained User epoch29 owner and all fingerprints checked read-only and matched before implementation. Before each reset, verify owner/fingerprints, freeze, export, read back and hash; reset only registered keys. Keep the final dataset. Protect other goal and production databases. No historical migration.

Runner: scripts/engram_enrichment_ordering_demo.py. Independent Astra preflight is enrichment-ordering-review/astra-preflight.md. Implementation/harness and final evidence reviews required. Final command, results, failed attempts, stakeholder walkthrough and actual GitHub reconciliation will be appended after execution.

## Boundaries

Existing retry caps backoff, not elapsed dependency wait; a permanently absent prerequisite can block until stop. Repeated restart counts still interact with the pre-existing DLQ guard. General #14/#19 policy is separate. Healthy lock-based quiescence avoids but does not fix #60. Private bound API is not public/concurrent tenant isolation. Scripted embedding proves persistence, not semantic/model/ANN quality. No pilot or broader goal starts here.

## Failed attempt01 and disposition

Cloud01 passed both worker orders, pending/restart recovery and exact public annotations, then stopped at EN04: subgraph retrieval did not increment UUID Event access metadata. Source filters IDs by legacy evt prefix. Filed #61 under #34; unstarted and not fixed here. Preserve failed01 and owner30 data/export. EN04 positive access preservation remains required; the revised runner uses the existing authenticated GET /v1/context/{session_id} read, whose implementation records actual Event IDs, before the explicit graph-port importance adjustment. This is an explicitly disclosed input-path addition, not a weakened oracle or repaired graph. Cached-worker self-FOLLOWS remains tracked by #18; replay uses a fresh actual worker and exact edge checks.

## Stakeholder walkthrough

1. **Start with the event, not the graph.** Open the run manifest and first `/v1/events` request. It carries observation.input, tool race-tool and importance_hint7. The expected keywords are exactly observation/input/race-tool. The fixture embedding contains 384 values of 0.25. Enrichment is simple metadata annotation; the optional embedding model is substituted only to make persistence exact and repeatable.
2. **Watch the race deliberately.** In EN01, projection is held back. The saved pending observation names assessment-enrichment and the exact event ID; the graph has no partial Event. Unlike the original defect, enrichment cannot report completion and discard the work.
3. **Watch recovery.** EN02 stops the enrichment loop cooperatively and starts a fresh one. The same delivery remains pending until projection starts. Both workers then complete; the final Event has the exact annotations. The ledger event is retained, never deleted by ACK.
4. **Reverse the order.** EN03 creates the Event first, initially without keywords. Enrichment then supplies the same exact annotations. The authenticated subgraph answer includes the keywords, importance and correct session/agent provenance.
5. **Prove later work survives replay.** EN04 retrieves session context, creating a real positive access count, and intentionally adjusts importance 7→8 through the existing graph port (a declared stimulus, not a repair). Re-submit the identical HTTP event and reprocess its accepted delivery with a fresh actual projection worker. The ledger remains one identity; keywords, vector,8, summary and access state remain unchanged. A later enrichment delivery also leaves8 intact. The cached-worker predecessor defect remains separately open in #18.
6. **Make failures visible.** EN05 has no embedding provider: keywords/default 5 are valid but no vector is invented. EN06's provider throws: the same degradation applies, and an existing vector survives replay. EN07 holds vector storage unavailable after keywords are written: the delivery remains pending, then stores the exact vector when the injected outage ends, without repeating the provider call inside that delivery.
7. **Check the final boundaries.** All five workers settle with no pending or dead letters. Final data has exactly five accepted Events, five Event nodes, the one active OntologyState metadata node matching the selected bundle, and no edges (each has a separate single-event session), with exact submitted ownership/source fields. Events keep vectors in JSON; their physical Entity ANN column is null. Healthy quiescence precedes final snapshots. Previous datasets are verified exports, and the last one remains retained.

The steps above are the demonstration script. The accepted result records will supply actual IDs and expected-versus-actual values; an unrun or failed attempt is never substituted for an accepted result. A recorded walkthrough is distinct from an interactive live demo with the stakeholder.

## Verification methods and limits

The first local regression failed on the old code because EnrichmentConsumer.process_message returned while its Event did not exist. It passed after requiring the projected Event and retrying the write. Final targeted tests include 12 ordering/ownership cases, plus existing enrichment and reference graph conformance:51 passed, 48 external-backend cases skipped. The broad unit run passed 2819, skipped 13, with tests/unit/test_pdlc_end_to_end.py excluded for the previously documented evaluation-gate failure; two later missing-target SDK tests and stronger summary/access assertions passed in the targeted rerun. This is not an all-backend or full-baseline pass. Ruff and changed-source mypy checks passed.

No new feature umbrella is needed. #29 owns the enrichment fix under #34. #61 owns the separately discovered UUID subgraph access issue, #18 the cached replay predecessor issue, #60 shutdown safety, and #14/#19 general delivery/missing-document policy. These are not silently closed or implemented here. #39 and #41 receive only the bounded evidence; whole pack composition, concurrent tenancy and pilot remain unstarted.

## Failed attempt02 and oracle correction

Cloud02 passed all functional EN01–EN07 checks, including positive context-read access, importance 8, exact API annotations and partial vector-write recovery, then stopped at the final membership oracle. The harness incorrectly expected only business Event nodes; normal projection startup also records OntologyState:active. This is an oracle omission, not a production artifact leak. Before rerun03, explicitly admit exactly that one metadata identity and require its schema version and pack identities to equal the preselected bundle; continue rejecting every other unexpected node. Physical-column audit includes this metadata row, still requiring null Event ANN columns. Failed02 remains preserved; no runtime change or manual cloud repair was made.

## Implementation references

Runtime/harness commit: `79d8779` on feature/engram-memory-episodes. Runtime changes are six existing source files (119 additions and 55 removals); the larger commit includes the dedicated acceptance runner and regression tests. No table, service, dependency or pack-schema revision was added.

- worker/enrichment.py re-fetches missing accepted documents and retries prerequisite/storage failures in place; a successfully computed embedding is retained while its storage write retries. Provider exceptions remain distinct from storage exceptions.
- adapters/graph_ops.py uses the existing create-only merge for Event-derived fields and makes absent annotation targets explicit.
- adapters/spanner/graph.py requires the target and preserves transaction-current importance in the same read/write transaction.
- adapters/neo4j queries/store mirror the contract with ON CREATE defaults and checked MATCH updates; live Neo4j remains unverified.
- ports/graph_store.py documents ownership and missing-target behavior.

Accepted evidence uses actual UUID Event IDs, standard authenticated observation inputs and graph-port importance adjustment as an intentional test stimulus. Source hashes cover 215 runtime, YAML and script files, not merely the commit message. Failure artifacts are retained separately from accepted records.

## Accepted real-Spanner run

Run: enrichment-ordering-1013-03. All seven cases ran for each configuration below through authenticated HTTP, actual worker loops, real Spanner and Engram read APIs. EN04 additionally uses the public graph-port importance-adjustment stimulus, explicitly labeled above.

| Selected packs | Expected | Actual | Evidence |
|---|---|---|---|
| Core | EN01–EN07; exact annotations and final state | 58/58 PASS | [Core record](runs/enrichment-ordering-1013-03/core.json) |
| Core + User | Same common enrichment contract | 58/58 PASS | [User record](runs/enrichment-ordering-1013-03/user.json) |
| Core + User + Memory | Same common enrichment contract | 58/58 PASS | [User/Memory record](runs/enrichment-ordering-1013-03/user-memory.json) |
| Core + PDLC | Same common enrichment contract | 58/58 PASS | [PDLC record](runs/enrichment-ordering-1013-03/pdlc.json) |
| Core + PDLC + Memory | Same common enrichment contract | 58/58 PASS | [PDLC/Memory record](runs/enrichment-ordering-1013-03/pdlc-memory.json) |

Total: 290 assertions across 35 scenario executions, not 290 journeys. Each configuration ingested five distinct Events, with EN01/02 sharing the restart event and EN04 replaying EN03. Exact duplicate HTTP ingestion adds no event. Keywords are observation/input/race-tool; initial hint importance is 7, EN03 becomes 8 after the declared adjustment and remains 8; absent hints use 5. Scripted embeddings are exactly 384 values of 0.25. Provider-absent/failed new Events have no vector, while an existing vector remains intact. No partial Event node, unexpected domain/User/Memory artifact, invented edge, pending delivery, dead letter or shutdown error is accepted.

The final Core+PDLC+Memory dataset remains at epoch 36: five ledger Events, five Event graph nodes, one matching OntologyState metadata node and no graph edges. [Fresh post-process audit](runs/enrichment-ordering-1013-03/post-process-recheck.json) matched the owner and all table fingerprints, all five final/retained snapshots, all 215 runtime/script hashes and all five verified prior exports. No manual repair occurred. Previous User data and failed attempts were exported and verified before reuse.

Cloud Monitoring export still reports 403; this is not a telemetry-readiness claim. These are sequential private-bound configurations, not concurrent tenant isolation. The new UUID subgraph access issue #61 remains open; session context provides the supported access-count producer for this replay proof.

## Repeat safely

From this worktree, with the existing experiment credential and unchanged retained ownership:

```sh
PYTHONPATH=src:scripts /Users/arunmenon/projects/Engram-foundation-gate/.venv/bin/python \
  scripts/engram_enrichment_ordering_demo.py \
  --run-id enrichment-ordering-repeat-UNIQUE \
  --previous-record docs/review/spanner-compatibility/runs/enrichment-ordering-1013-03/pdlc-memory-retained.json
```

Use a new run ID. The runner refuses evidence overwrite or owner/data drift; it exports/verifies the prior dataset before reset and retains the final dataset. Do not rerun automatically after another slice changes the owner. No additional run is required for the accepted results above.

## Independent verdict

[Astra final completeness review](enrichment-ordering-review/astra-final-review.md) clears bounded #29 closure after reviewing all five configurations, actual responses, transaction ownership, pending/restart evidence, vectors, source hashes, exports and retained state. It excludes broader retry policy, shutdown, public/concurrent tenancy, all producer journeys, ANN quality, live Neo4j and pilot readiness.

## Published GitHub reconciliation

Runtime/harness: `79d8779`. Verification/reviews/raw evidence: `41f2e37`. Both pushed to `feature/engram-memory-episodes`.

| Issue | Before → after | What changed | GitHub update |
|---|---|---|---|
| [#29](https://github.com/arunmenon/Engram/issues/29) | OPEN → CLOSED | Bounded acceptance complete; body/checklists reconciled and issue closed | [Comment](https://github.com/arunmenon/Engram/issues/29#issuecomment-6152304048) |
| [#34](https://github.com/arunmenon/Engram/issues/34) | OPEN → OPEN | Bounded progress/evidence recorded; full issue scope remains | [Comment](https://github.com/arunmenon/Engram/issues/34#issuecomment-6152306116) |
| [#35](https://github.com/arunmenon/Engram/issues/35) | OPEN → OPEN | Bounded progress/evidence recorded; full issue scope remains | [Comment](https://github.com/arunmenon/Engram/issues/35#issuecomment-6152319847) |
| [#39](https://github.com/arunmenon/Engram/issues/39) | OPEN → OPEN | Bounded progress/evidence recorded; full issue scope remains | [Comment](https://github.com/arunmenon/Engram/issues/39#issuecomment-6152307013) |
| [#41](https://github.com/arunmenon/Engram/issues/41) | OPEN → OPEN | Bounded progress/evidence recorded; full issue scope remains | [Comment](https://github.com/arunmenon/Engram/issues/41#issuecomment-6152307863) |
| [#42](https://github.com/arunmenon/Engram/issues/42) | OPEN → OPEN | Bounded progress/evidence recorded; full issue scope remains | [Comment](https://github.com/arunmenon/Engram/issues/42#issuecomment-6152308741) |
| [#18](https://github.com/arunmenon/Engram/issues/18) | OPEN → OPEN | Fresh-worker proof only; cached predecessor bug remains | [Comment](https://github.com/arunmenon/Engram/issues/18#issuecomment-6152309481) |
| [#61](https://github.com/arunmenon/Engram/issues/61) | OPEN → OPEN | New confirmed UUID access defect, native child of #34; unimplemented | [Comment](https://github.com/arunmenon/Engram/issues/61#issuecomment-6152310375) |

Native #34 sub-issue links for #29 and #61 were re-read after updates. #60 remains OPEN and unchanged. No new umbrella is needed. Next slice and pilot are not started. The full reconciled state and links are saved in [GitHub reconciliation](enrichment-ordering-review/github-reconciliation.json).
