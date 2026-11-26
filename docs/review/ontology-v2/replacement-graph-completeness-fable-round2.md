**Verdict: accept.** The fresh-target default closes round 1's high finding, and I found no remaining blockers. Three stale lines in the report need correcting before commit.

## Candidate identity
- `versioning.py` and the manifest were both rewritten at 14:54, after this round started. The change is one line: `evaluation_status` is wrapped in `str()` in the status output.
- All five paths match the updated manifest, before and after my runs. Every test and probe below ran on that final content.
- Base is still `b917a07`, the worktree still shows the same 7 status entries, and I made no edits.

## Disposition of round 1 findings
1. **Trim clears a known-incomplete target: fixed.**
   - `rebuild` refuses any `incomplete_rebuild` target at the top of the function, before the force branch and before any write.
   - Your trim test proves the failed state is identical after forced and ordinary retries.
   - Interrupted and write-failed targets stay refused, and a fresh target recovers.
2. **Legacy skipped + failed pair: fixed.**
   - `gate_skipped: True, gate_passed: False` is refused by `reconcile` under both `allow_breaking` values and by a forced rebuild.
   - It has no false positives: `evaluate --record` never writes `gate_passed`, in base or in the candidate, so only a rebuild with failed writes can produce the pair.
3. **Stale evaluation result: fixed.** The status string tracks gated pass, skip, failed recorded evaluation and passing re-evaluation. A legacy row without the key reads as `None`.
4. **Counts: fixed as scoped.** The full failed-event count and the capped samples are in the report and state. The unbounded missing-position collector remains a #123 follow-up, as you state.

## Probes (memory backend, from stdin)
- **Question-only failure retries in place.** A complete build with failing questions is not marked incomplete. `reconcile` refuses it without the override and accepts it with, as before. An in-place retry with passing questions ends ready.
- **Gate independence holds in both directions.**
  - A skipped-gate complete build followed by a failing recorded evaluation stays processing-ready, not evaluation-ready and not incomplete.
  - `evaluate --record` on an incomplete build leaves the state byte-identical.
- **Legacy rows.**
  - `missing_documents: 2` is refused under both overrides.
  - A gated `gate_passed: False` row keeps the old override behaviour.
  - A skipped and passed row is still accepted.
- **Authority.** The check runs before any target write; your test confirms no state and no nodes.

## Follow-ups, not blockers
- **Evaluation crash strands a complete target.** If `run_gate` raises after a complete projection, the in-progress marker stays and the target needs a fresh rebuild even though its data is whole. This is consistent with the documented interruption contract, but worth one line in the notes.
- **In-place retry over a shrunk source.** A complete target retried after the source was trimmed to nothing reported `passed True, events 0` while still holding the first run's 2 nodes. Nothing is missing, but `rebuild_events` understates what the target holds. This belongs with convergence (#36).
- **Complete target can become blocked.** If a document expires before an in-place retry, the retry records incomplete and locks the target. That is fail-closed and correct, but an operator will see it as a ready target turning unusable.
- **Ambiguous legacy gated failures.** A base-era gated row with `gate_passed: False` may hide failed writes and can still be rebuilt in place. You document this limit.
- **"Fresh" is convention.** A stateless non-empty target is refused only without `--force`; nothing checks emptiness under force.

## Report corrections before commit
- "780 passed" should be 787.
- "mypy on two runtime files" should be three.
- "Final Fable recheck pending" should record this result.

## Tests
- **Focused:** the three files (`test_rebuild_completeness.py`, `test_ontology_readiness.py`, `test_pack_versioning.py`) give 91 passed.
- **Lint and types:** ruff check on all five files, ruff format on four (the three runtime files plus the new test) and mypy on the three runtime files pass.
- **Your evidence:** `regression-final.txt` ends at 787 passed and `memory-controls-final.txt` at 2 passed, 4 deselected. I read the tails and did not re-run that exact selection.
- **Broad offline run** (`tests/unit` + `tests/conformance`, not integration): 2973 passed, 6 failed, 1 collection error. These are the same seven as round 1, all in files this diff does not touch:
  - `test_empty_target_activation.py` fails at collection.
  - Five `test_procurement_pack.py` cases fail; `docs/examples/procurement/procurement_ops.pack.yaml` is absent.
  - `test_backend_end_to_end.py::...[memory]` fails on a duplicate ingest returning 409 instead of 201.
  - I did not run these at base, so "pre-existing" is inferred from the untouched files, not proven.

## Limits
- Memory backend only, Python 3.14.2. No Redis, Neo4j or Spanner run, so storing the new boolean and list properties on those backends is unproven.
- The refusal is a read followed by a write, so it does not exclude two concurrent rebuilds into the same target.
- Completeness still means retained entries observed in this run. Trimmed history, source snapshots, cutover and partial-history admission remain outside this slice, as the report says.
