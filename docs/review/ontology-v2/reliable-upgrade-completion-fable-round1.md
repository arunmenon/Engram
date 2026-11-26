# Independent review: issue #11 reliable upgrade completion, round 1

## Verdict

**Accept for the bounded scope. No blocking issue found.** The mechanism meets the acceptance contract on the memory backend. Finding 1 needs an owner decision before the existing-data upgrade; the rest are PR-text items or small follow-ups. A second round is only needed if you change code for findings 1 or 2.

## Source identity

- Worktree `/Users/arunmenon/projects/Engram-slice11`, branch `fix/11-replay-completion`, HEAD `ebe27b1e56d0a1eb6bae053d64ac3c521d33dd8a`.
- Only the two declared files are modified, and both sha256 values match the manifest (`a1cd4cc5…` for `versioning.py`, `1ee091a5…` for the test file).
- Python 3.14.2, memory adapters only.

## Contract check

| Contract item | Result |
|---|---|
| Old bug reproduced by a checked-in regression | Yes. All 8 `TestReplayCompletion` tests fail against HEAD source; the main one fails with `DID NOT RAISE`. |
| Planning failure and graph-write failure do not complete | Yes. Version, packs and `eval_pending` are untouched; failures are recorded. |
| Restart retries; a permanent failure stays refused | Yes. Retry replays the whole ledger in order under the exact target. |
| Markers cleared only after success | Yes (`versioning.py:334-347`). |
| Successful replay still applies; equal version is a no-op | Yes. |
| Fence errors propagate and are never collected | Yes, including `CancelledError` and read interruption. See finding 2 for a side effect. |
| No bypass of the incomplete fence | None found. `allow_breaking` and `allow_version_problems` do not skip it, and `evaluate --record` does not clear it. |
| Evaluation gating preserved | Unchanged from HEAD. See the pre-existing note below. |

## Findings, ranked

**1. Medium: a missing document blocks the upgrade under normal retention, and the hint is not actionable** (`versioning.py:194-200`, `326-333`)

- Retention deletes documents by `occurred_at` (90 days by default) but trims log entries by position (7 days, held back for lagging groups). History imported or backdated beyond the ceiling therefore has log entries with no document after the next consolidation pass.
- I reproduced this with the real `MemoryEventLog.expire`: every attempt is refused with "Resolve the failures and restart with the same target packs". Nothing the operator can do resolves it; it clears only when the entries age out of the log.
- The prescribed escape, rebuild, counts `missing_documents` and records completion anyway (`rebuild.py:115`, `278-289`), so in-place replay is stricter than its own recovery path.
- The checked-in test only covers a synthetic, transient `None` from a monkeypatched `read_after`.
- This is fail-closed and within your stated design, so not a contract violation. But this slice is the prerequisite for the existing-data upgrade, which is where imported old history is most likely.
- Verification: either the PR states this refusal and its recovery, the hint distinguishes missing documents from failed events, and a test pins the `expire()` path; or the owner chooses a different policy for retention-expired entries.

**2. Low-Medium: the incomplete marker is written before the log-side authority precheck** (`versioning.py:287-297` versus `175-184`)

- A runtime refused with "Bound ledger requires authenticated replay policy" now leaves `replay_incomplete=True` plus its own target hash, with zero replay writes. At HEAD this path wrote nothing.
- Reproduced: the ticket title is unchanged, yet reverting to the base config is then refused with "may contain partial update writes".
- This is a state mutation by a runtime that fails authority, not a bypass.
- A related consequence, read from the code rather than run: if a fence fires because the tenant bundle advanced, the newly authorized runtime has a different target and can only rebuild.
- Verification: after a precheck `RuntimeFencedError`, the state carries no `replay_incomplete`. A fence raised from the first read may still leave the marker; that is by design.

**3. Low-Medium: status surfaces do not show the new state** (`ontology/__main__.py:144-165`, `api/routes/ontology.py:99-121`, outside the candidate files)

- Neither `status` nor `GET /v1/ontology` returns `replay_incomplete`, `replay_target_version` or `replay_failures`.
- With the config reverted during an incomplete replay, both report `change.kind: none` for a graph the worker refuses to start on.
- The hints tell operators to inspect the recorded failures and reuse the recorded target, but the only places to see them are the raw node and the logs.
- Verification: expose the three fields, or state the deferral to #126 in the PR.

**4. Low: legacy detection limits, for the PR text** (`versioning.py:242-256`)

- Detection needs a non-empty `replay_failures`. A falsely completed row that old code later re-recorded on any additive or mapping change has `[]` and cannot be detected.
- A detected row stops the projection worker at deploy even with no pack change, and there is no override; rebuild is the only way out.
- Recommend a pre-deploy scan of state nodes for non-empty `replay_failures`.

**5. Low: test coverage gaps**

- The "other target" refusal is not isolated. The only refusal test reverts to base, where `not plan.replay_event_types` also holds, so deleting the `replay_target_version != registry.version` clause would leave the suite green (by reading; I did not run that mutation). My probe with a third target that needs replay was refused correctly.
- The untouched-second-store assertion uses a store never passed to any code under test. It proves no shared global state in the memory adapter, not tenant isolation.

## Pre-existing, not introduced here

- **`eval_pending` dropped on success** (`versioning.py:345`, unchanged from HEAD): success writes only `plan.eval_required`. Reproduced: a prior `["demo"]` becomes `[]` after a successful mapping upgrade with no evaluation run. The new test asserts preservation during failure but not after success. Belongs to #126.
- **Replay covers only retained log entries:** events trimmed past the hot window are never remapped, so "complete" means complete over the retained log (#36).
- **No mutual exclusion between concurrent reconciles.** The interleavings I traced fail closed.
- **Forced in-place rebuild stays refused:** `rebuild --force` onto the same graph does not clear the markers, because the state write merges. Read from the code, not run.

## Tests actually run

- Seven unit files (`test_pack_versioning`, `test_pdlc_end_to_end`, `test_pack_toy_end_to_end`, `test_authenticated_source_trust`, `test_pack_composition`, `test_spanner_tenant_reads`, `test_hex_purity`): 579 passed, 4 skipped.
- `-k TestReplayCompletion` against a `git archive HEAD` copy of `src` in a temp directory (deleted afterwards): 8 failed, as expected.
- Four inline probes with no files written: retention-expired documents, authority precheck, third target, and `eval_pending` across success.
- I did not rerun your 611-test regression selection; `regression.txt` shows it passed.

## Remaining limits

- All evidence is from the memory backend. Merge semantics for the partial marker write were read for Neo4j (`SET n += row.props`) and the shared `graph_ops` path; Spanner's merge was not read or run.
- CI on Python 3.12 was not run.
- No live outage, Spanner recovery or tenant-routing proof.
- Partial in-place writes remain after a failure, as you stated. The recorded version is the last successful completion, not proof of rollback.
