# Replacement graph completeness

Issue: #12, ARCH-8-003, pillar 8. Branch: fix/12-rebuild-completeness.
Base: b917a0750141bdfe34d5374c0c87dc8d59df9a1e, after merged PR138.

## Product flow and accepted default

An operator explicitly creates a replacement tenant graph from source events under chosen pack rules. Required event documents can have expired while their ledger entries remain. A narrow passing question set, or --skip-gate, previously allowed such a replacement to report success. This slice makes incomplete processing fail closed and keeps questions separate from data completeness.

Required scope here is retained ledger entries observed in this run. This does not attest already trimmed events, all-time tenant history or the consistency of a separately assembled source. A complete source must be supplied before claiming those broader scopes. No automatic migration, tenant activation, live cutover or archive scanning is added.

The conservative implementation has no partial-history normal-use bypass. Graphs with missing required data remain diagnostic and unusable by normal workers. Skipping question checks on an otherwise complete graph retains its existing diagnostic-processing permission. The user was asked whether deliberately limited history should also be admitted; that optional product decision has not been received. No silent acceptance is inferred. If wanted, normal use of limited history needs an explicit history scope and answer limitations; this PR must not claim to deliver that separate policy.

## Implementation

RebuildReport separates projection_complete, evaluation_passed (null for skipped), and overall passed. Missing required documents or failed writes prevent overall success regardless of question scores or diagnostic skip. Reported history_basis is retained-ledger. Counts are full; missing-position examples and persisted failure lists are capped at 100.

The rebuild records an in-progress/incomplete marker before event writes. Exceptions, cancellation and runtime fences leave it blocked. Known source-policy mismatches are checked before target writes using the existing replay-authority check. Successful completion records completeness, counts, missing positions, write failures and the independent evaluation result. Existing completed-version metadata on a target describes this rebuild attempt while its incomplete marker is set; it is not proof of applied completion.

Worker reconciliation and effective readiness refuse known incomplete builds even with allow_breaking. This includes legacy rows with nonzero missing_documents. Evaluation cannot clear an unusable target. A clean diagnostic skip with complete processing still follows its existing processing permission and unevaluated-answer policy. Legacy gate_skipped:true plus gate_passed:false is also known incomplete, because that historical pair proves failed required writes. Existing version/readiness behavior outside incompleteness remains covered by regressions.

The rebuild-specific consumer records missing positions at both ledger scan and actual document fetch, counting each position once across retries. It retains the original worker's planning, accepted-record verification and fence handling. No new projector, storage framework, deployment mechanism or dependency is introduced.

## Verification and guardrails

Tests exercise public rebuild, reconcile, read_state/status and CLI run_rebuild with real planners and memory ports. They cover real retention expiry with passing questions and skipped questions, override refusal, OSError/cancellation/fence interruption and restart, document loss between scan and projection, CLI nonzero status, archive-assisted recovery into a fresh source/target, and known authority mismatch before writes. Source IDs and business payloads are compared across recovery; the original expired source remains unchanged. Filesystem archive plus unbound memory import proof is not tenant-bound archive recovery or production cutover acceptance.

Final selected regression: 787 passed. PDLC and CRM memory controls: 2 passed, 4 external cases deselected. Ruff/format and mypy on three runtime files pass. Python 3.14.2 local only; no Python 3.12 CI, live backend or product-provider call. Existing source packs and business question expectations are untouched. The previous readiness unit test intentionally expected missing-history workers to remain permitted because #126 deferred that policy here; it is updated to assert the now-approved #12 refusal, not to conceal a regression.

Red/green logs are retained under output/implementation/ontology-v2/slice12. The first CLI check used identical live target settings and correctly refused them; the corrected fixture names an isolated memory target. That harness refusal is not evidence of a product defect. Actual red traces reproduce missing-document false success, startup-override bypass, missing progress markers, and the scan/fetch race.

## Evidence limits and review checkpoint

Completeness here cannot discover history already absent from the ledger before the run. General replay convergence, source snapshot/cutover coordination and proof of all-time history remain separate (#36/#13/#43 and required-history design). Recovery from interruption and write faults uses a fresh empty target with the recovered source. A completed target whose evaluation alone failed can still be rebuilt in place; known incomplete or interrupted targets cannot, including with --force. This deliberately gives up unsafe same-target continuation rather than claiming general convergence. Archive recovery also uses a fresh source and target. No general in-place data repair or version-pinned historical graph capability is claimed.

[Fable round 1](replacement-graph-completeness-fable-round1.md) requested revision. Codex reproduced the same high finding independently: after a missing-document build, source trim allowed a rerun to erase the recorded failure. The smaller fresh-target alternative was selected. Rebuild refuses reusing any known incomplete/interrupted target, even with --force, preserves its failure evidence, and requires recovered required source plus a fresh target. The new source-trim test covers forced and ordinary retries; write-failure and interruption tests prove fresh recovery. The earlier same-target interruption expectation was changed intentionally for this stricter recovery contract.

The legacy skipped/failed-write pair now counts as incomplete, so the processing override cannot admit it. Evaluation uses an explicit persisted evaluation_status (passed/failed/skipped), avoiding backend omission of None. Recorded evaluations update that status, and public tests exercise pass, skip, failed evaluation and passing reevaluation. The rebuild report adds a full distinct failed-event count, with a capped persisted sample. The missing-position collector still grows with observed missing positions; its resource bound remains a #123 follow-up, not a claimed fix. Existing dead-letter collection is also unbounded.

[Fable round 2](replacement-graph-completeness-fable-round2.md) accepts the final candidate with no blockers. It verified all five source/test hashes, reran 91 focused tests and the static checks, and independently probed the corrected recovery/legacy/gate cases. Both allowed review rounds are complete; no third was invoked. Reported costs were $2.98 and $2.56, within the $5 per-call caps. At most two calls at $5 each; stop early if accepted, use a second only for needed recheck, no automatic third. No commit/PR/merge/deployment acceptance claimed yet.

## Upgrade and operational notes

A legacy target with missing_documents greater than zero now refuses worker startup under either override. A skipped legacy rebuild with gate_passed:false is also known to have failed writes and is blocked. Legacy gated failures without processing evidence remain ambiguous; the existing normal failure gate is preserved. No operator should repair data by clearing metadata flags.

An incomplete/interrupted target must be left as evidence or separately discarded through an authorized process; rebuild into a fresh empty target from recovered required history. Even --force does not waive this rule. A forced attempt against a live-recorded graph marks it rebuilding before data writes, so interruption blocks the live worker; this PR does not make force safe for production cutover or provide rollback. No such operation was run.

Fresh targets only prove the retained entries supplied and observed in that run. Data trimmed before a run or ahead of its cursor is not observed, and this PR adds no source snapshot lease, all-time manifest or deployment coordination. Accepted limited-history normal use remains unsupported; partial targets stay diagnostic/blocked. The unanswered optional question is not treated as authorization for a bypass.

Final static-check correction: the nullable evaluation-status lookup key was normalized to a string immediately after starting the final review. The manifest was updated before acceptance. Earlier mypy output had one typing error; only the subsequent clean result is final evidence. Valid passed/failed/skipped behavior is unchanged.

## Final review limits and operational follow-ups

Fable's broader offline run passed 2,973 with 6 failures and 1 collection error in untouched paths: five absent-procurement-fixture failures, a duplicate-ingest status assertion, and an import/collection error. It did not reproduce these on this slice's base, so their pre-existing status is inferred, not proven here. The accepted 787-test selection is green; no full-suite green claim is made.

If evaluation itself raises after a completed projection, the unfinished attempt still requires a fresh target. A previously complete target can become incomplete when required documents expire before its next rebuild. Both behaviors deliberately fail closed. A completed target retried over a smaller source can retain older rows and report only the new run's event count; general convergence remains #36. Ambiguous legacy gated failures cannot be retrospectively separated into data versus question failures.

The --force option still bypasses the old emptiness/live-target guards for targets without known incomplete metadata. The new incomplete-target refusal cannot be bypassed, but this does not prove every forced target is empty or safe. Recovery guidance means a verified fresh empty target, not manually clearing its state node. Two concurrent builds into the same target are not excluded by this read/write marker; orchestration and cutover remain separate.

The internal missing-position set and existing dead-letter collector are not bounded by the capped output samples. This remains a nonblocking resource follow-up, related to the aggregate-bounds work #123, not a claimed memory-bound fix.

## Accepted code/test identity

- `src/context_graph/ontology/rebuild.py`: `df058ca904cc6c7d593d33b5313b58a0ca231e11fd0da49f6ec77f9b56d00d23`
- `src/context_graph/ontology/versioning.py`: `cb299d940f17b169245d94eb77600f1aac28b35a44b5d30a925d1bfd80a7bdb2`
- `tests/unit/test_rebuild_completeness.py`: `a5d101a32d006cc8e67fff64f935cb4294ba45ddf2a6c11499659deb506f3dc3`
- `tests/unit/test_ontology_readiness.py`: `1fb5815581812d1102d63986601b5872a700c90b4e990db1793e6f572cfe6476`
- `src/context_graph/ontology/__main__.py`: `9089a78bcb897eff6d5746facb261bdb75091a5e1adfa0c4d6f7b0fdc2b59a90`
