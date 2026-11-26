**Verdict: revise.** The bounded default is sound and honestly labelled, but one real contract gap needs a fix: a retry into the same target can clear recorded incompleteness when the source window shrinks. Everything else I checked holds; the other findings are low.

## Findings

### 1. High: retention trim between attempts clears a known-incomplete target
- **Where:** `rebuild.py:256-272` reads the prior state only for the version/applied guards. `rebuild.py:298-301` and `326-348` then overwrite `missing_documents`, `rebuild_missing_positions`, `rebuild_failures` and `rebuild_complete` from this run's observations alone.
- **Repro (memory backend, real `expire` and `trim`, no overrides):**
  1. Ticket 2 ingested 3 days ago, Ticket 1 today; `expire(max_age_days=1)` returns `(0, 1)`.
  2. First `rebuild`: `passed False, events 2, missing 1 ['1795392000000-0']`; `reconcile` refuses.
  3. Routine `log.trim(1, [])` drops 1 entry.
  4. Second `rebuild` into the same target, nothing recovered: `passed True, complete True, events 1, missing 0`.
  5. State now has `rebuild_complete True, missing_documents 0, eval_pending []`; Ticket 2 is absent from the target.
  6. `reconcile` with no override is accepted; readiness shows `processing_ready True, evaluation_ready True, recorded_history_incomplete False`.
- **Why it is a bug, not a proof limit:** the target had recorded the missing position, and the rerun erased that record without recovering the event. The same path clears a prior `rebuild_failures` list. A fresh target after the trim reporting complete is the proof limit; this is not.
- **Fix (about 15 lines, no new infrastructure):**
  - When the prior state has `applied == "rebuild"`, carry its recorded missing and failed positions into the run.
  - Resolve a carried position only when `_fetch_batch` returns its document and it is not dead-lettered again.
  - If any carried position is unresolved, or the prior count exceeds the 100-item sample, stay incomplete and tell the operator to use a fresh target with a complete source.
  - The in-progress marker merges, so the prior lists survive an interrupted attempt and can be read at the start of each attempt.
  - Smaller alternative: refuse any reuse of a target recording missing documents or failures, including with `--force`. This costs the legitimate same-target retry after a corrected write fault.
- **Verification:** add the repro above as a test asserting not passed, `incomplete_rebuild`, and `reconcile` refused for both `allow_breaking` values. Add a write-failure variant and a positive case (fault removed, unchanged source, same target passes). `test_interrupted_build_stays_blocked_and_can_retry` must stay green.

### 2. Low-medium: a legacy failed-write record is still admitted by `allow_breaking`
- **Where:** `versioning.py:88-95`.
- **Repro:** a base-era record with `gate_skipped True, gate_passed False` and no `rebuild_*` keys is refused without the override and accepted with `allow_breaking=True`.
- **Why it is knowable:** under the base formula (`not dead_lettered and (gate_skipped or ...)`), that pair can only mean dead-lettered writes.
- **Fix:** add `gate_skipped is True and gate_passed is False` to `incomplete_rebuild`. The new code only produces that pair when incomplete, so there are no false positives.
- Legacy gated records with `gate_passed False` stay ambiguous between evaluation and write failure; that is a genuine proof limit.

### 3. Low: `evaluation_passed` goes stale
- **Where:** `rebuild.py:338` writes `None` for a skipped gate, but no backend writes `None` (`graph_ops.py:153-161`, `neo4j/pack_graph.py:71`).
- **Repro:** gated pass, then `--skip-gate` into the same target. The report says `None`; the stored value and status `graph.evaluation_passed` stay `True` alongside `gate_skipped True`.
- **Impact:** display only; no decision reads the field and readiness is still correct.
- **Fix:** store an explicit string (`passed` / `failed` / `skipped`) and have `evaluate --record` update it. Hiding the field in status while `gate_skipped` is set is not enough, because `evaluate --record` flips `gate_skipped` and would expose a stale `False`.

### 4. Low: unbounded collector and missing failure count
- `missing_positions` (`rebuild.py:88, 124, 192`) is a set of every missing position. Old ledgers where most documents have expired are the normal large case, and base held only a counter there. A count plus capped sample, with dedup scoped to one flush, would bound it. Acceptable as a follow-up.
- The report and state keep a capped failure sample but no full failure count, so "counts are full" in the record is true for missing documents only.

## Checked and holding
- **Gate versus data:** missing documents fail `passed` with a passing gate and with `--skip-gate`; the CLI exits 1; `evaluate --record` cannot clear an incomplete build.
- **Interruption:** an `OSError` mid-read leaves `rebuild_in_progress True` and blocks a worker restart even with `allow_breaking`; the retry completes (reproduced on a forced rebuild, see below). The candidate's own test also covers cancellation and fence.
- **Authority:** `check_replay_authority` runs before any target write; a `source_trusted` rejection in `_fetch_batch` becomes a dead letter or a fence, never a silent skip.
- **Scan/fetch race:** both observation points are keyed by position, so the set dedups correctly across per-event retries.
- **Callers:** the only `reconcile` caller is `worker/__main__.py:112`; the API route and CLI go through `status_for_state`.

## Behaviour to acknowledge (by design, not defects)
- **Legacy tenants hard-stop on upgrade.** A serving graph that was a legacy rebuild with `missing_documents > 0` now refuses worker start under both override values. It stays refused across later reconciles, and there is no exit without a recovered source. Since the partial-history question is unanswered, this needs an explicit release note.
- **Forced rebuild into a live-recorded graph.** If interrupted, `applied` flips to `rebuild` at the marker, the live worker is blocked, and a later unforced rebuild is no longer stopped by the live-projection guard. Base reached the same end state only on completion.

## Proof limits (correctly not claimed)
- Entries trimmed before a run, or ahead of the cursor during a run, are never observed.
- An interrupted attempt persists no missing list, so a trim before its retry is undetectable.
- The archive recovery test proves a fresh source and target only; it is not fenced production archive recovery.
- Nothing here establishes all-time history, convergence or cutover.

## Tests and identity
- **Hashes:** all four match the manifest before and after my runs; the worktree is unchanged (same 5 status entries). Repros ran from stdin, no files written.
- **Focused:** `test_rebuild_completeness.py`, `test_ontology_readiness.py`, `test_pack_versioning.py`: 84 passed.
- **Lint and types:** ruff check, ruff format and mypy on the two runtime files pass.
- **Your 780-test selection:** I confirmed the log tail only; I did not re-run that exact selection.
- **Broader offline run** (`tests/unit` + `tests/conformance`, not integration, Python 3.14.2): 2966 passed, 6 failed, 1 collection error. I did not run these at base.
  - `test_empty_target_activation.py` fails to import `engram_spanner_tenant_control_cases`.
  - Five `test_procurement_pack.py` cases fail on a missing `docs/examples/procurement/procurement_ops.pack.yaml`.
  - `test_backend_end_to_end.py::...[memory]` fails on a duplicate ingest returning 409 instead of 201, an ingest path this diff does not touch.

Round 2 only needs to recheck finding 1 with its new tests, plus 2 and 3 if taken.
