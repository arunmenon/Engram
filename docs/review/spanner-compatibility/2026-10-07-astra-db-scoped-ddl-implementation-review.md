# Database-scoped DDL implementation review

2026-10-07. Narrow read-only review against the approved DB-scoped recovery design. No tests, cloud operations or runtime edits by this reviewer. Recorded `20261007-local-ddl-recovery-01/tests.txt`: **88 passed, 10 deselected**, 1.98 seconds.

## Verdict: changes requested

1. **P2 — Persist the replay allowance across restarts.** `adapters/spanner/ddl_upgrade.py:128` bounds the loop to two iterations per invocation, but the attempt contains no durable submission/replay count. After two lost responses and absent GETs, restoring the saved uncertain attempt permits another two update RPCs, indefinitely. The approved contract permits one bounded identical replay and then stops unresolved. Persist consumed submission/replay allowance before each RPC; after it is exhausted, allow exact GET recovery but no further update. Add a process-restart regression proving restoring the exhausted attempt never submits again.

2. **P2 — Observation errors must not erase reconciliation requirements.** `ddl_upgrade.py:168` replaces every prior state with `observation_error`. An operation-name/metadata collision records `unresolved` with `observed=False`; a later denied GET overwrites that state, and a subsequent NotFound bypasses the terminal guard at line 141 and submits. Preserve durable unresolved/terminal state independently of the latest RPC error, or retain the prior state when logging observation failures. Regression: unresolved collision → GET permission failure → restored attempt with GET NotFound must issue zero updates. Terminal operation errors should likewise remain in the durable audit record rather than being replaced by transient observation details.

3. **P2 — Reload before recording the upgrade baseline DDL.** In `scripts/engram_spanner_entity_ann.py`, upgrade skips the planner before `evidence.update`, and evaluates `before_ddl=list(database.ddl_statements)` before `schema_differences` performs its reload. The fresh SDK database handle has no loaded physical DDL, so upgrade evidence records an empty/stale baseline even though the following handshake sees the real schema. Reload explicitly before capturing the baseline, or compute the handshake first and then capture the refreshed DDL. Add a fixture whose cached DDL differs from its reload result.

## Positive scope assessment

The attempt is registered and atomically/fsync-persisted before cloud calls; ordered statements and their digest are persisted before submission. Recovery uses the authenticated database-admin transport's exact-name GET, with no instance operation listing. Name/database/statements are checked before observation is accepted. Lost update responses retain the same ID and payload within an invocation; denied GET is distinguished from NotFound for that invocation. Observed operation disappearance fails closed. Linked retries require a remotely confirmed terminal failed predecessor. Native ANN/schema semantics and budget behavior are unchanged by this slice.

These findings concern durable recovery and audit fidelity only. No new cloud mutation should be inferred from local tests or this review; real operation/readiness and ANN compatibility acceptance remain separate.

## Remediation recheck

Read-only inspection resolves all three findings:

- The attempt now persists `submissions`, validates its bounds/type and consumes the allowance before each update RPC. Restored attempts with two consumed submissions may GET the original operation but cannot issue further updates; restart coverage verifies this.
- GET failures now populate `last_rpc_error` without replacing durable state or the primary error. The unresolved → permission failure → NotFound regression retains the reconciliation guard and performs no update.
- The harness explicitly reloads the database before capturing `before_ddl`, so the upgrade baseline uses loaded physical DDL.

Additional inspected tests cover persistence failure before submission and refusal to retry a pending predecessor. Recorded `20261007-local-ddl-recovery-02/tests.txt`: **92 passed, 10 deselected**, 1.93 seconds. No tests/cloud executed by this reviewer.

**Current verdict: approve the narrow DB-scoped recovery implementation; no outstanding findings from this review.** This is local implementation approval, not evidence of DDL submission, target readiness or real ANN compatibility.

## Formatting-only metadata reconciliation

Read-only recheck approves the narrow comparison change. `ddl_statement_matches` compares complete nonempty token sequences, preserving literal case, operators and parentheses; ordered statement count is still checked. The persisted request/digest remains exact and unchanged. The recorded `cloud-entity-ann-observe-01/comparison.json` shows matching operation/database, terminal completion with error code 0, and differences limited to whitespace around the index target and OPTIONS clause. This evidence supports reconciliation of that known operation, not submission of another request.

Recorded `20261007-local-ddl-recovery-03/tests.txt`: **93 passed, 10 deselected**, 1.95 seconds. **Approve resuming the same recorded operation through exact GET and target-schema validation; no new operation ID or DDL submission is warranted.** No tests/cloud executed by this reviewer. Target readiness and ANN acceptance still require their respective evidence.
