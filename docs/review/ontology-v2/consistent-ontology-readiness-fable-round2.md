# Round 2 verdict: ACCEPT

No blockers remain. All four round 1 findings and the Codex finding are fixed. What is left is one untested line, one runtime consequence to state plainly in the record, and upgrade notes.

## Verification

- **Hashes:** all seven manifest hashes match, including the untracked `tests/unit/test_ontology_readiness.py`. The base is still `7ebe37b` and the worktree is untouched.
- **Focused tests:** 70 passed on the final files (my rerun). `green-review.txt` predates the last `versioning.py` edit by about two minutes, so my rerun is the one that counts.
- **Final logs:** `regression-final.txt` (701 passed) and `memory-controls-final.txt` (2 passed, 4 deselected) both postdate the last source edit.
- **Broader selection:** 1153 passed, 5 failed, 2 skipped. The 5 failures are the same `test_procurement_pack.py` cases round 1 saw failing on base. I excluded `test_empty_target_activation.py`, which had a collection error in round 1.
- **Static checks:** ruff check and format, and mypy on the 5 runtime files, pass on the final files.

## Finding dispositions

| # | Disposition | Evidence |
|---|---|---|
| 1. Recovery after a blocked evaluate | Fixed | A blocked `evaluate --record` leaves the state identical. Letting it record again fails the three-step test. |
| 2. Blanket version-mismatch block | Fixed | Both skew directions return no pending packs. Restoring the blanket block fails the skew test. Unloadable definitions block all packs. |
| 3. Missing history | Resolved as the deferred option | The worker reconciles with and without the override. Removing the eligibility term fails the test. |
| 4. Failed marker lost under override | Fixed | Restoring the `applied == "rebuild"` condition fails the restart test. |
| 5. Minor items | Addressed | Refusal wording, the unknown-status shape and the `allow_breaking` field are all present. |
| Codex: label hides changed definitions | Fixed | Removing either the pending clause or the `plan.kind == "none"` readiness term fails the test. |

## Remaining notes, none blocking

- **Untested line:** the `rebuild.py` pending clear is not covered. Removing it leaves all 70 tests green, because the three-step test no longer writes `eval_pending` at step 2. The code is correct: a clean skip, a failing recorded evaluate, then a corrected rebuild ends with no pending packs. That sequence would make a covering test.
- **Missing history is a runtime change, not only a diagnostic:** on a graph with a nonzero recorded `missing_documents`, every pack intent returns 409; base served them.
  - `evaluate --record` refuses to record on such a graph and exits 1.
  - The only ways out are a complete-history rebuild or `CG_ONTOLOGY_SERVE_UNEVALUATED`.
  - The record says this in one clause, and it fits the issue's "passing questions do not repair unavailable history". "No retention policy introduced" holds for workers only.
  - The record should state the upgrade effect, since `rebuild` still reports `passed: true` and exits 0 on such a graph.
- **Upgrade effects of the stricter failed marker:** any graph with a historical `gate_passed: false` now refuses worker start without the override. That includes skipped builds with dead letters and failures that an override update hid on base. This is intended and fails closed.
- **Legacy skipped builds:** a skipped build that base already evaluated keeps `gate_skipped: true`, so it returns 409 until `evaluate --record` is rerun once.
- **Stale version label (diagnostic only):** if the label is stale but the definitions match, status reports `processing_ready: false` indefinitely while the worker reconciles as a no-op. This needs corrupted metadata to occur.
- **Redundant terms:** the `state.packs is None` clause in `pending_for_state` and the `missing_documents` term in `evaluation_ready` are redundant; removing either changes no test.
- **Record is stale:** it still says "Final independent recheck pending".

## Limits

- Everything ran offline on Python 3.14.2; nothing ran on Python 3.12 or against a live backend.
- I did not rerun the base comparison this round.
- Mutation copies and probe scripts are under `/tmp/slice126-r2`.
