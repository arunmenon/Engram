# Consistent ontology readiness

Issue: https://github.com/arunmenon/Engram/issues/126 . Findings ARCH-8-002/ARCH-8-015, pillar8.
Branch: fix/126-ontology-readiness. Base:7ebe37b9f760f17e80ae953b9a2d014a6059a966.
Integration target: integration/engram-ontology-v2. No merge/deployment approval is inferred.

## Operator outcome

After a failed or unfinished pack update, ontology status and query eligibility must explain the blocker. Processing permission is distinct from evaluated answer eligibility. A diagnostic build may process without claiming evaluated readiness. Passing questions do not repair failed execution or unavailable history. This slice improves those recorded-state signals; it is not live worker health, complete-history recovery or an activation UI.

## Runtime changes

The existing versioning module now supplies shared status_for_state and pending_for_state reports. API ontology status, CLI status, CLI evaluation/rebuild reports and effective artifact eligibility consume them. Status includes unfinished replay target/failures, reasons and the next action. API ordinary read failure is explicitly unknown/not-ready; authority fences propagate. Artifact409 replies explain the actual blocker.

A failed rebuild marker survives pack metadata updates and explicit processing overrides. A failed diagnostic build stays failed. A clean diagnostic skip permits processing but stays unevaluated until its reviewed evaluation is recorded. Evaluation refuses to record on an unusable projection, preserving the original failure evidence. A later successful rebuild clears its pending evaluation, so rebuild-only recovery actually works. Successful replay preserves pre-existing pending evaluation.

Readiness requires matching version AND canonical definitions. An inconsistent version label cannot hide changed definitions. Normal version skew preserves existing query eligibility from recorded pending plus plan.eval_required; this PR does not impose a blanket rolling-deploy query ban. Unloadable/corrupt definitions and explicit failure markers fail eligibility closed. Broader evaluation invalidation remains #87/#98.

## History, overrides and compatibility

Missing-history counts are disclosed as diagnostic/not-evaluation-ready and affect effective evaluation eligibility. Their unconditional worker block from the first candidate was removed after Fable review: deciding that broader retention/rebuild policy belongs to #12. Workers preserve the previous startup behavior for this count alone. Existing RebuildReport.passed still does not attest complete history. No claim of complete reconstruction, safe tenant rollout or automatic history repair is made.

allow_breaking remains an explicit processing override; it never makes failed data evaluation-ready, and the report identifies this process's policy setting. It does not prove the remote worker uses the same settings. serve_unevaluated preserves its explicit development bypass of artifact evaluation eligibility. EvalPending keeps its existing cache TTL and ordinary-read fallback; fences still propagate. No pack/event/oracle/dependency/UI changes or product-provider/cloud calls.

CLI status returns0 for a successful status read even when blocked. Evaluation keeps its existing list shape with additive readiness per report. With --record it exits1 if readiness remains blocked, even when question scores pass. Without --record it remains a diagnostic score command and explains blocked readiness. Rebuild adds readiness to its existing report; its existing passed/history behavior remains #12. Raw gate scores are distinct from readiness.

## Verification and independent review

Tests at public reconciliation/read_state, real rebuild/evaluate, API status/artifact requests and CLI commands use actual planners and memory stores. Fault injection stays at graph/store-opening boundaries. New temporary wrong/correct evaluation sets model failed and successful checks; existing business expected answers and source packs are unchanged.

The original actual regressions reproduced failed-build eligibility, disappearing pending evaluations, failed diagnostic readiness and API false-ready after config revert. The first CLI red trace contains a test-harness JSON parsing issue from pre-existing stdout logs, not product evidence. A first-candidate history-block test is superseded by the explicit #12 deferral. The second-pass tests reproduce canonical-definition mismatch, blocked corrected-rebuild recovery, compatible version-skew regression and failure-marker loss under override.

[Fable round1](consistent-ontology-readiness-fable-round1.md) requested revision. Codex dispositions:

1. Fixed recovery regression by refusing blocked evaluation writes and clearing pending only after a real successful non-skipped rebuild without known missing documents. Failed scores remain intact; corrected rebuild restores eligibility without another evaluate.
2. Removed blanket version-mismatch eligibility blocking. Both skew directions preserve prior eligibility behavior. Unloadable/corrupt definitions stay blocked. Full projection readiness remains distinct from compatible query eligibility.
3. Adopted the status-only history-policy option and deferred worker blocking/rebuild-completeness decisions to #12. Public tests verify worker permission, history disclosure and non-ready evaluation together.
4. Preserved failure markers independently of the applied-method field. Tests cover override plus additive pack change followed by normal restart refusal.
5. Clarified processing/evaluation refusal, unknown status shape and process-policy scope. Pending/skip remedies retain the existing evaluate command. The developer override remains documented; it is not universally suggested for data failures.

[Fable round2](consistent-ontology-readiness-fable-round2.md) accepts the final runtime with no blockers. Both allowed rounds are complete. Reported costs were$3.02 and$2.48, within the$5 per-call caps. At most2 Fable calls at$5 each; round2 is the last allowed call. Local evidence: output/implementation/ontology-v2/slice126. Python3.14.2 local only, no Python3.12 CI or live backend acceptance. Pre-existing missing procurement fixture failures found in the broad review are separate and unchanged; no fixtures were invented to hide them.

## Final verification and upgrade notes

The final12-file affected selection passes701 tests. PDLC and CRM memory walkthrough controls pass2, with4 external backend cases deselected. Fable independently reran70 focused tests, checked all7 manifest hashes, ran mutation checks for the review corrections, and passed Ruff/format and mypy on the5 runtime files. Its broader selection passed1153 with5 pre-existing procurement-fixture failures and2 skipped; one unrelated collection-error module was excluded. No full-suite green claim.

After final review, Codex added one test only for a clean diagnostic build, a failing recorded evaluation, then a corrected rebuild. The actual-source test passes; removing the pending-clear write in a temporary source copy makes that exact assertion fail. This covers the review's remaining untested line. Runtime hashes are unchanged, and no third review was invoked. This added test is Codex-verified, not independently rerun by Fable. The701-test run predates that test-only addition; its separate1-test result is retained. Red/green and mutation logs are in the local evidence folder.

Known upgrade consequences:

- A recorded missing_documents count now makes explicit pack intents return409 and prevents evaluate --record from clearing eligibility. Workers keep their old startup behavior for this count alone; rebuild can still report passed:true/exit0 while its readiness is diagnostic. Full-history recovery or the existing explicit development bypass are separate decisions. Deployments must inspect these counts; #12 owns the retention/rebuild policy.
- Any surviving gate_passed:false now retains the worker block unless the existing processing override is set. This includes failed diagnostic builds and failures previously hidden by metadata updates. Correct the underlying problem and rebuild; passing questions alone do not clear it.
- A legacy skipped build previously evaluated by the old code may need evaluate --record once more to clear its surviving gate_skipped flag.
- A corrupt stale version label with otherwise matching definitions stays conservatively not-ready even though the worker treats the definitions as a no-op. This diagnostic-only metadata repair case remains a low follow-up; no automatic metadata repair is introduced.

## Accepted runtime hashes

- `src/context_graph/ontology/versioning.py`: `d8640f52c6b6ac8fbe59b6182ab165823603cc37cb9d7033e513a0f2b5e6f9b1`
- `src/context_graph/ontology/__main__.py`: `c225451660d16bdf139a87b3a4e5b323a09a7f31e0ad7248ae77ef0d2b588177`
- `src/context_graph/api/routes/ontology.py`: `2e7527c33eb1e90f0a72df1c198bdb35d7961aaadfcd300514be471a6741ab46`
- `src/context_graph/api/routes/artifacts.py`: `7399686d1c5d0f7ba9f079d7b61db5ee4127766d63b120bbb09c87e8268f0ef1`
- `src/context_graph/ontology/rebuild.py`: `dcccb3eda7fca18211dcd035af1e4204a847cb6752295ec1d44eee08fa393e8a`
