# Runbook: moving the event ledger to another backend

How to move Engram's ledger from one backend to another, for example Redis to Spanner, with the tools from ADR-0019 phase 3. The graph is not copied: the target's projection worker rebuilds it from the imported ledger.

Commands below use `--to spanner`. The source is whatever `CG_STORAGE_*` names today. The target takes the same settings with every storage port switched to `--to`, so its connection settings (`CG_SPANNER_*`) must be set too. `CG_MIGRATION_*` tunes batch size (500), poll interval (1000 ms) and the number of sessions sampled by the comparison (50; 0 means all).

## 0. Before you start

- The target database is empty, or holds only events imported by an earlier run. The tool refuses (exit code 2) when the target holds events that were not imported, because copying then would place migrated events after newer ones.
- Note the source's retention settings. Events whose document already expired are skipped and counted (`skipped_without_document`), never copied as empty.
- No Spanner resources are created by this tool unless `CG_SPANNER_CREATE_IF_MISSING=true`, which is meant for the emulator.

## 1. Copy

```
python -m context_graph.migration copy --to spanner
```

This copies everything the source holds, in source order, and prints a JSON report (`imported`, `skipped_without_document`, `batches`, `last_source_position`). It is safe to re-run: it resumes after the target's newest `legacy_position`, and imports are idempotent.

## 2. Dual run

```
python -m context_graph.migration mirror --to spanner
```

Run this as a long-lived process. It keeps importing new source events in order until SIGTERM, and resumes from the target's checkpoint after a restart. The API keeps writing to the source only.

Start the workers against the target as well (a separate deployment with `CG_STORAGE_*=spanner`). The projection worker replays the imported ledger from the start and then follows the mirror. Run enrichment and the other consumers there only if their outputs are part of the comparison.

## 3. Compare (repeat during the soak)

```
python -m context_graph.migration compare --to spanner --graph
```

This prints a JSON report and exits 1 on any divergence:

| Layer | Checked | Divergence kinds |
|---|---|---|
| ledger | every source event | `missing_in_target`, `legacy_position`, `document_differs`, `order` |
| graph | counts per node and edge type, per-session event counts, sampled sessions' events and edges, entities | `nodes_count`, `edges_count`, `session_event_count`, `event_missing_in_*`, `event_properties`, `edge_missing_in_*`, `entity` |
| retrieval | context per sampled session; lineage from every event with a parent | `context_nodes`, `context_edges`, `context_score`, `lineage_*` |

Read the report:
- `checked.ledger.native_in_target`: events written to the target directly. It should be absent before cutover.
- `checked.ledger.target_only`: imported events the source has since trimmed. Expected as the source's retention runs.
- Compare while the mirror and workers are caught up. Events still in flight show up as missing or count differences.

Fields each backend assigns for itself are ignored: positions, `occurred_at_epoch_ms` and access counters. Decay scores may differ by up to 0.01, because they depend on query time.

A projection-worker restart on either side no longer changes the graph, and an idle tail is flushed once the batch timeout passes. Divergence while both sides are caught up is a real difference.

Exit check (design brief phase 3):
- zero divergence over the soak;
- retrieval evals within the agreed tolerance. Keyword ranking changes from BM25 and is not covered by `compare`.

## 4. Cutover (phase 4, not yet automated)

1. Pause ingest on the API.
2. Wait for the mirror to import the last source event, then stop it.
3. Run a final `compare --graph`.
4. Switch the API and workers to the target (`CG_STORAGE_*`), and resume ingest.
5. Keep the source read-only for one retention period.

Rollback is not rehearsed yet, and the tool refuses to mirror back into a source that holds native events. Rehearse it before cutover (brief phase 4 exit).

## Local rehearsal

`tests/integration/test_dual_run.py` runs the whole sequence: a memory ledger and Neo4j as the source, the Spanner emulator as the target.

```
./gateway_main --hostname 127.0.0.1 --grpc_port 9010 --http_port 9020   # Spanner emulator
CG_SPANNER_EMULATOR_HOST=127.0.0.1:9010 pytest tests/integration/test_dual_run.py
```

It needs Neo4j at `CG_NEO4J_URI`, and skips when Neo4j or the emulator is unreachable.
