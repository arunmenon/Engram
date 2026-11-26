# Round 1 verdict: REVISE

The core #126 outcome holds: failed and skipped builds no longer read as evaluated-ready, and the API, CLI, worker and artifact 409 agree on the cases the tests cover. Two real regressions against base and one policy decision need attention before the PR.

## Ranked findings

**1. Regression (medium): a corrected rebuild no longer restores query eligibility after `evaluate --record` ran on the failed build.**
- **Where:** `src/context_graph/ontology/__main__.py:187-197`.
- **Cause:** on a blocked build, `evaluate_graph` now writes `eval_pending` for every active pack and overwrites `gate`. `rebuild()` never resets `eval_pending`, so it survives a later passing rebuild.
- **Repro:** failed rebuild, then `evaluate_graph(record=True)` with a passing set, then a rebuild with a passing gate.
  - Candidate: recorded `eval_pending ['demo']`, `EvalPending ['demo']`, status "Pack evaluation is still pending", while the rebuild reports passed.
  - Base: `EvalPending []`.
- **Impact:** fails closed, but it breaks rebuild-only recovery and the `EvalPending` docstring ("cleared by ... a rebuild whose gate passes"). The CLI guidance says "rebuild", and the operator then needs a further evaluate.
- **Side effect:** the worker refusal then reads "evaluation gate failed (['demo:1.000'])", because the passing score replaced the failing evidence.
- **Fix, in scope:** do not record when the state is not processing-ready. `pending_for_state` already forces all packs pending there, so the write is redundant. Add the three-step sequence as a test.

**2. Regression (medium): any version mismatch now blocks every pack intent.**
- **Where:** `versioning.py:382` in `pending_for_state`.
- **Repro:** graph recorded under demo, API on demo plus one added node property (plan `additive`, `eval_required []`).
  - Candidate: `EvalPending ['demo']` in both skew directions.
  - Base: `[]`.
- **Impact:** every pack bump in a rolling deploy returns 409 for all artifact intents until both sides converge, plus the 30s TTL. This is outside #126 acceptance and conflicts with "preserve previous valid query behavior".
- **Test sensitivity:** deleting the clause leaves all 65 tests green.
- **Fix:** on mismatch, fall back to recorded pending plus `plan.eval_required`, and block everything only for breaking or unloadable plans. If the blanket block is intended instead, document it and test it.

**3. Decision needed: the missing-history block is unconditional and reaches into #12.**
- **Where:** `versioning.py:239-244`.
- **Why it matters:** expired documents are a designed state (`ports/event_log.py:33`, 90-day retention ceiling).
  - Any rebuild from an aged ledger becomes permanently unusable.
  - A deployed rebuilt graph with a nonzero recorded count will refuse at the next worker restart after upgrade.
  - No override applies, although the failed-gate case has one.
- **Contradiction:** the same graph still records `gate_passed: true` and the report says `passed: true`.
- **Test sensitivity:** only the reconcile half is tested; removing `missing_documents` from eligibility and `processing_ready` leaves all 65 green.
- **Options:** accept explicitly with an upgrade note and tests, or keep it as a status reason with `evaluation_ready: false` and leave worker blocking to #12.

**4. Pre-existing, newly mis-reported (low to medium): the failed marker is lost under the override.**
- **Repro:** failed rebuild, then `CG_ONTOLOGY_ALLOW_BREAKING` with any additive pack bump. Reconcile rewrites `applied`, so `failed_gate` becomes false.
- **Result:** status says `evaluation_ready: true`, "No recorded ontology blocker", and later reconciles pass without the override. No evaluation ever passed.
- **Classification:** base behaves the same for the worker and eligibility; the affirmative "ready" claim is new.
- **Fix:** drop the `applied == "rebuild"` condition in `failed_gate` (only rebuild writes `gate_passed`), or file a follow-up.

**5. Minor**
- The refusal at `versioning.py:247` still says "evaluation gate failed" for dead-letter-only and skipped builds where no gate ran.
- The read-failure readiness in `api/routes/ontology.py` omits `pending_packs`, `diagnostic_only` and `change`.
- The 409 remedy drops the `CG_ONTOLOGY_SERVE_UNEVALUATED` hint, and for a graph with no state it says "Initialize the projection" without naming an action.
- `processing_ready` reflects the calling process's `allow_breaking`, not the worker's.
- The implementation record still says review pending and totals to be recorded.

## Checked and coherent
- Authority fencing propagates in the API and `EvalPending`.
- A clean skip processes but stays diagnostic until a passing recorded evaluation.
- A successful replay keeps prior pending entries; reverting that line fails a test.
- `evaluate --record` exits 1 when nothing could be recorded.
- A skipped build with dead letters is refused.

## Tests run
All offline on Python 3.14.2.
- **Candidate:** the two scoped test files give 65 passed.
- **Base source, same tests:** 20 failed, 45 passed, so the new tests are sensitive to the change.
- **Affected selection** (`-k "ontology or artifact or pack or workbench or evaluation or rebuild or hex_purity"`): 1148 passed, 5 failed, 2 skipped. The 5 failures are in `test_procurement_pack.py` (missing `docs/examples/procurement/procurement_ops.pack.yaml`) and fail identically on base.
- **Collection error:** `test_empty_target_activation.py` fails on a `scripts` import; I did not check it against base.
- **Ruff:** passes on the four runtime files and the new test.
- **Manifest:** five of six hashes match; I did not confirm the `test_pack_versioning.py` entry.

## Limits
- I did not rerun mypy, the full suite, or the PDLC/CRM end-to-end controls.
- Nothing ran against a live backend.
- Repro and mutation copies live under `/tmp/slice126-review`; the worktree is untouched.
