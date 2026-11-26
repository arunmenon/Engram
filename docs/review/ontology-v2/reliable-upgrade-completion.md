# Reliable upgrade completion

Issue: https://github.com/arunmenon/Engram/issues/11
Finding: ARCH-8-001. Owning pillar: 8, domain onboarding and pack evolution.
Component: ontology engine reconciliation and replay completion.
Branch: `fix/11-replay-completion`.
Base: `ebe27b1e56d0a1eb6bae053d64ac3c521d33dd8a`, the unmerged pack-test-baseline PR #136.
Integration target after that prerequisite merges: `integration/engram-ontology-v2`.

## What changes for operators

When an existing tenant adopts changed pack mappings, Engram may reprocess stored events. Previously it could record the new pack as complete even when some events failed. Restarting then skipped the unfinished work. This fix refuses completion after failures and retries the same target after a temporary fault is resolved.

This is one promise: no false completion of partially processed work. It does not automatically migrate every historical record, choose whether history should stay pinned, or add workbench activation controls.

## Implementation

Only `src/context_graph/ontology/versioning.py` changes runtime behavior. Its existing replay helper now counts unavailable event documents as failures because their event types cannot be established. Reconciliation records an incomplete attempt before graph writes; event-planning or graph-write failures keep the prior completed pack snapshot and evaluation metadata and refuse startup. Read errors, cancellation and authority fences propagate. Success records the target snapshot and clears only the transient replay markers. No table, service, feature flag or dependency is added.

An interrupted attempt can already have changed graph data. The saved old version is the last successful completion, not a rollback guarantee. Restarting with different packs, including reverting to the old configuration, is refused while the incomplete marker remains. Retry uses the exact content-derived target hash. Historical rows created by the old bug, with a completed target plus recorded failures, fail closed rather than silently returning a no-op.

For a temporary storage fault, resolve the fault and restart with the same target packs. For permanently unprocessable history or a legacy falsely completed row, inspect the failures and use a separately verified fresh-projection recovery procedure. Do not clear metadata by hand or treat a code/configuration rollback as data repair. Full rebuild correctness, replay convergence and reader/worker cutover remain tracked separately in #12, #36 and #126. This slice does not certify those procedures.

## Verification

Tests use the actual planner, memory ledger and memory graph. Fault injection is limited to storage and ledger port boundaries. Checks exercise temporary graph failure across repeated starts and recovery, permanently failing strict-property planning, unavailable event documents, read interruption, cancellation, authority failures, legacy state, an unchanged isolated store, successful property remapping, lifecycle ordering, evaluation-state retention and successful no-op.

Before the fix, checked-in regressions reproduced false completion after a write failure, interruption without a durable incomplete marker, missing documents counted as completed, and legacy failure rows returning no-op. Raw red/green traces are retained locally under `output/implementation/ontology-v2/slice11/`. The independent reviewer is asked to challenge these mechanisms rather than accept the implementer's summary.

Local candidate checks:

- Versioning suite: 46 passed, including eleven new replay-completion cases.
- Affected eight-file regression selection: 615 passed. This overlaps the versioning suite; counts are not additive.
- Ruff check and format check on both changed files; mypy on the changed runtime module; whitespace check.

Run tests from the task worktree with `PYTHONPATH=src` and the existing project virtualenv. The regression selection is:

```sh
PYTHONPATH=src python -m pytest tests/unit/test_pack_versioning.py tests/unit/test_pack_projection.py tests/unit/test_strict_pack_properties.py tests/unit/test_worker_fences.py tests/unit/test_runtime_tenant_binding.py tests/unit/test_tenant_store_binding.py tests/unit/test_spanner_event_interpretation.py tests/unit/test_hex_purity.py -q
```

These are local Python 3.14.2 checks with memory and fake-adapter boundaries, not Python 3.12 CI, a live Spanner outage, a deployment or a human study. The existing API `return`-in-`finally` syntax warning is outside the changed paths. Pack fixtures, event bytes and business expected answers are unchanged. The dirty integration checkout is not part of this candidate. Current CI does not automatically run on this integration target.

## Independent review and delivery

[Fable round 1](reliable-upgrade-completion-fable-round1.md) accepts the bounded core mechanism and requested clearer handling of retention-expired documents and authority prechecks. Codex reproduced both observations, then corrected them: a known authority mismatch now fails before any attempt marker; missing-document refusal explicitly warns that retry cannot restore expired history and rebuilding alone is not proof of recovery. Real retention-expiry and unchanged-state authority tests now pin these behaviors. An additional test isolates refusal of a different replay target. [Fable round 2](reliable-upgrade-completion-fable-round2.md) independently accepts the final source hashes with no remaining blocker. It reran the versioning suite (46 passed), the eight-file selection (615 passed), and mutation checks proving the other-target and authority-precheck tests detect removal of the corresponding guards. Both allowed rounds are complete; no third was used.

Disposition of the remaining review notes:

- Status visibility is deferred explicitly to #126: CLI status and the ontology API do not yet show the new replay markers. Their `change.kind: none` after a configuration revert must not be treated as worker readiness. Failure logs and recorded state are the current diagnostic sources.
- Legacy detection requires surviving non-empty `replay_failures`; it cannot identify rows whose evidence was already erased by old code. Before deployment, inspect authorized existing-state snapshots for recorded failures and plan recovery for affected stores. A detected row will block startup even without a new pack change. No override is added.
- Evaluation-pending metadata is retained on failures. Successful reconciliation still uses the existing `plan.eval_required` behavior, which can drop older pending entries. That pre-existing issue belongs to #126 and is not certified fixed here.
- Complete replay here means processing the available retained log; it does not prove that already trimmed historical events were reconstructed. Missing documents that still have log entries refuse completion, including after real retention expiry. Full history completeness belongs to #12/#36.
- The untouched second memory store is a shared-state control, not tenant-routing or live isolation proof. The two-round cap was honored. Reported review-call costs were $3.00 and $1.25 (rounded), within the $5 per-call caps. Do not equate implementation or an open draft PR with independent acceptance, merge or deployment. The colleague controls merge; issue #11 stays open until that process is complete.

Remaining nonblocking notes: the missing-document hint emphasizes permanent retention expiry even for a transient unavailable document, and the second-store test variable still says `other_tenant`. Neither changes the accepted runtime outcome; no additional runtime edits were made after final acceptance. The local `versioning-final.txt` trace is the earlier 43-test candidate, not final evidence; use the 615-test final regression log and Fable's final independent 46-test run.

## Reviewed source identity

- `src/context_graph/ontology/versioning.py`: `73cb29ea895da18fd521fb82a16cda5830b047ca8f102195e3bbd4f995703898`
- `tests/unit/test_pack_versioning.py`: `af31b23825fcc2544f82fc72672152b1ed108045feebf172eec160eb60c49333`
