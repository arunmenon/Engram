## Verdict: REVISE

Three defects block acceptance: two reproduced by offline probe, one established partly by probe and partly by code reading. This was the final permitted round, so they stay open.

**Freeze check:** all 27 manifest hashes match, HEAD is `5fe0ecd`, the worktree is clean, and I edited nothing. The focused run gives 85 passed. Two manifest files are outside the cb302ee diff (`pack_expressions.py`, `test_complete_identity_operands.py`); they are the S4 dependency and their hashes match. I did not check `evidence/contract-proposed.md`.

### Blockers

**B1. Explicit replay leaves a stale old-bundle row that blocks completion forever (reproduced).**
- **Where:** `worker/relationship_recovery.py:122-126`. With `reinterpreting` and a prior row from a different bundle, `prior` is set to `None`; if both endpoints now exist, the code hits `continue` and never replaces or settles the old row.
- **Witness:** `pending_links()`, then upsert the target without running a page, then `replay_event_types` under a pack with a changed edge `set`. The edge is written correctly (`note: 'new effect'`), but the row becomes `changed_bundle`, `relationships_complete=False`, `blocking=1`. A second replay gives the same result.
- **Impact:** `reconcile` raises `OntologyChangeRefusedError` on every restart although the graph is correct. This is reachable whenever the target arrives but the rotating page has not reached the row before a mapping change.
- **Smallest correction:** in that branch, still call `put_relationship_intent(..., reinterpret=True)` and then `_recover(current)`, so the row settles as `existing_relationship_kept` or `recovered`. Add this witness as a test.
- **Related, code reading only:** `blocked_lookup` rows are never superseded (`domain/relationship_recovery.py:44-45`), so one historical truncated lookup would block every later replay the same way.

**B2. An older event delivered for the first time after the row is terminal silently loses its disjoint properties (reproduced).**
- **Where:** `domain/relationship_recovery.py:48-50` returns `None`, and `worker/relationship_recovery.py:132` suppresses the normal write.
- **Witness:** position 2 (`second_note`) is deferred, the account arrives, a page recovers the edge, then position 1 (`first_note`) is delivered for the first time. The edge ends with `second_note` only, and nothing is counted or reported.
- **Control:** the same delivery order with the target present first, so no recovery row exists, yields both fields. This is a regression against base behaviour, not the S3 producer-clock question.
- **Reachability:** by code reading, `consumer.py:286-296` leaves a failed item pending while later items proceed. I did not drive it through the consumer.
- **Smallest correction:** on a terminal row, suppress an older incoming effect only if it is a retained pointer or every field it writes has a recorded later winner. Otherwise let the normal patch through for the uncovered fields. This needs per-field winner order keys kept on terminal rows, including after the reset at line 53; these are not payload values.

**B3. The elapsed-time bound raises instead of reporting incomplete, and in the live flush it runs before ACK (raise reproduced; flush consequence by code reading).**
- **Witness:** `finish()` with a slow store and a short timeout raises `TimeoutError`. `page()` uses the same `asyncio.timeout` construct.
- **Live flush:** `worker/projection.py` calls `page()` after the batch's own writes but before ACK. A timeout or any non-fence error from an unrelated row therefore fails a healthy batch. `consumer.py` then leaves it pending and dead-letters it after `max_retries`.
- **Rebuild and replay:** `project_ledger` and `replay_event_types` do not catch the timeout, so the run crashes rather than recording `relationship_scan_complete=False`.
- **Settings bypass:** `replay_event_types` in `ontology/versioning.py` constructs `RelationshipRecovery` and calls `finish()` with hardcoded defaults (5 s, 10,000 rows, page 100), ignoring `settings.ontology.recovery_*`.
- **Smallest correction:** catch the timeout inside `page()` and `finish()` and return `complete_scan=False`; keep the opportunistic page from failing the ACK (run it after ACK, or swallow non-fence errors); pass settings into `replay_event_types`.

### Low residuals

- **Terminal status can regress (code reading only).** `settle_relationship_intent` writes `status` whenever the generation matches, in all three adapters, with no terminal check. A stale concurrent settle of `missing_source` could turn `recovered` back into a blocking status. My probe for this hit a non-terminal row, so it is not demonstrated. Fix: return the stored status unchanged if it is already terminal.
- **Redelivery can stop the consumer.** `domain/relationship_recovery.py:73-75` raises `RuntimeFencedError` when a pointer at the same order key differs. The pointer includes `bundle` and `plan_digest`, and the ordinal depends on how many edges earlier lookups resolved. A crash between put and ACK across a bundle upgrade, or a lookup resolving differently on redelivery, would trip it.
- **Capture is unbounded per flush.** Each deferred edge costs a serial put plus get with no timeout, and every flush adds two reads over all candidate endpoints.
- **Dangling optional rows are never collected.** Each final pass re-derives all of them from the start, so a large dangling population turns into an incomplete scan via budget or B3.
- **Reserved-row exclusion from counts** is visible only in Neo4j `get_graph_stats`. I saw no equivalent for memory or Spanner and did not verify their counts.

### What held up

- Required rules accept only complete-key equality; prefix, non-key and latest are rejected.
- Optional candidates are pinned and rebuilt from the stored reference, not re-queried.
- Per-field compaction gives the same result as full replay in log order, including explicit clears.
- The compound generation fences concurrent replacement, and a superseded row forces `complete_scan=False`.
- Endpoint check, create-if-absent and status are one transaction in the memory, Spanner and Neo4j code as written.
- Direct writers without recovery refuse required missing links before any domain write.

### Evidence limits

- Everything ran on local Python 3.14 with the memory backend only; no real Spanner, Neo4j, Redis or CI 3.12.
- The Neo4j Cypher (MERGE with temporary token, cursor upsert under an unregistered label, constraint created only in `ensure_pack_schema`) and the Spanner transaction path were read, not executed.
- Spanner `position_order_key` assumes a fixed-width three-part position; I did not check legacy or imported position formats.
- I did not rerun the 1,240-test selection, the conformance suite, mypy, Ruff or the 54-run matrix.

Review spend was about $3.1 of the $5 cap.
