# Artifact seed mode implementation and verification

Implements the accepted design in `2026-11-03-seed-mode-design-review.md`. Local working-tree changes, not a deployment or an independent implementation review. The working tree contains substantial unrelated work; review only the paths below.

## Behavior and scope

Artifact queries now accept `seed_mode: discover | explicit`, defaulting to `discover`. Explicit mode resolves every unique selection, preserves selection order and returns before text discovery. Empty, unparseable, absent/non-round-tripping, over-capacity and seed-resolution-budget failures raise `UnresolvedSeedsError` with a reason and affected IDs. The artifact route maps these to 422; the budget reason is distinct from invalid input. Graph failures and timeouts retain their existing handling. Budget exhaustion after resolution still produces a truncated response.

A separate guard prevents the completeness fallback from globally scanning when explicit mode has no scope. Discovery is unchanged except that cutting seeds to `max_nodes` now reports truncation. Strict responses identify `explicit_seeds` in metadata.

Mode travels through the HTTP request, workbench question, evaluation YAML/export, saved journey query options, and assistant journey examples. Old inputs default to discovery. Frozen release-journey serialization omits the new field if its original evaluation YAML omitted it, preserving the existing manifest digest. Neither the manifest nor frozen expectations changed.

Evaluation records resolution errors per question and continues the other questions. Any such error blocks the gate even if the mean F1 exceeds the threshold. A valid empty answer is scored normally. Journey retrieval checks record a failed check with the typed reason instead of crashing the journey.

The question editor offers **Only start from the entities I selected** beside the selected starting entities. Changing it clears the answer-review acknowledgment. Removing all selections while it is enabled leaves an explicit warning and allows switching it off; it does not silently fall back. Evaluation execution errors render as sentences instead of looking like ordinary answer mismatches.

This controls starting entities only. It does not constrain traversal across shared neighbors, change admission of explicitly selected untrusted nodes, solve pending inferred-intent widening, enforce account isolation, or alter the generic `/v1/query` engine. Pending inferred-intent widening remains a separate follow-up.

## Changed implementation paths

- `src/context_graph/retrieval/artifacts.py`: strict resolver, typed errors, completeness guard, metadata, truncation.
- `src/context_graph/api/routes/artifacts.py`: request carrier and error response.
- `src/context_graph/ontology/evaluation.py`: question carrier, per-question errors and gate.
- `src/context_graph/workbench/models.py`, `sandbox.py`: draft and evaluation export carriers.
- `src/context_graph/workbench/journeys.py`, `journey_runner.py`, `journey_authoring.py`: saved/assisted journey carriers and failure handling; legacy digest preservation.
- `demo/frontend/src/workbench/types.ts`, `Workbench.tsx`: option, review reset and result copy.
- New `tests/unit/test_artifact_seed_mode.py`, `tests/integration/test_artifact_seed_mode_spanner.py`, and `tests/fixtures/workbench/northstar-seed-mode.json`; additions to artifact-route, workbench and journey tests.

## Evidence

The Northstar fixture copies the saved synthetic draft's content and pack without modifying them. Tests change only the question mode in memory. The archived original result remains at `output/workbench/spanner/northstar-ui-result.json`.

Browser acceptance on the existing draft `2d0d471f-5c61-4163-9849-85f6ab9d1245` enabled explicit mode for both questions, confirmed review acknowledgments cleared, re-reviewed unchanged answers, validated the unchanged pack and ran the examples on the dedicated Spanner sandbox. Both questions matched exactly (mean F1 1.0). The database was cleaned and released. No approval/activation action was taken. Final refreshed UI evidence is revision 27, sandbox epoch 13, with the final server source fingerprint.

Evidence files live under `output/workbench/seed-mode/`. `northstar-ui-result.json` contains the complete saved record; `northstar-ui-passed.png` shows the UI result. The integration tests optionally persist full default/strict Northstar results and PDLC boundary metadata there.

The live integration suite uses only an explicitly supplied, registered disposable sandbox pool through its normal claim/fence/cleanup path. To reproduce with normal Google credentials:

```sh
ENGRAM_SEED_MODE_SPANNER_POOL=.workbench/spanner-pool-live.json \
ENGRAM_SEED_MODE_EVIDENCE_DIR=output/workbench/seed-mode \
.venv/bin/pytest tests/integration/test_artifact_seed_mode_spanner.py -q
```

Without the explicit pool setting, these tests skip. This session uses the existing gcloud login through the local acceptance launcher; tokens are neither printed nor included in evidence. The Spanner emulator was not running; the relevant adapter checks use real Spanner instead. Existing client metrics-export warnings were observed separately from passing data-plane assertions.

Broader regression limitation: `TestPdlcPack.test_loads_with_its_requirements` expects version 1.8.0 while the unchanged pack is 2.1.0 (also 2.1.0 in HEAD). This change does not update that unrelated assertion. Do not claim the entire repository suite is green.

## Verification results

- Focused engine, HTTP, workbench and frozen PDLC journey regression: **102 passed** (`output/workbench/seed-mode/local-regression.log`). This includes valid-empty vs error, 90%-mean-but-error gate rejection, selection order, no discovery/global scan, typed failures and all prepared retrieval variants.
- Broader ontology/CLI/OpenDAL and HTTP run: **42 passed, 1 failed**; the unrelated PDLC version assertion is described above (`broader-regression.log`). This overlaps the HTTP tests; do not add these counts as unique tests.
- Real Spanner: both Northstar modes passed their expected assertions (default 0.65, explicit 1.0); the separate PDLC missing-selection/order/completeness test passed after retry (`spanner-boundary-final.log`). All successful runs recorded verified cleanup and released slots. The first boundary attempt timed out creating a Spanner session before the assertions. The retry exposed missing constructor arguments in the new test harness, which were corrected; the final boundary run passed. Initial failures are preserved, not suppressed.
- Scoped Ruff and mypy passed; `npm run build:workbench` passed. The entire repository suite was not run.
- Browser exercised the new option, clearing/re-reviewing answers, save/validation and the successful Spanner run. The per-question error sentence is implemented and backed by error-carrier tests; a separate browser failure scenario was not run. No fresh model-authoring job was invoked for this engine-only correction.

## Claude implementation-review prompt

Review the artifact seed-mode implementation against `docs/review/2026-11-03-seed-mode-design-review.md` and this implementation note. Do not edit files or run cloud-mutating tests unless separately authorized. The working tree contains unrelated changes: restrict findings to the implementation paths listed above and their immediate callers.

Check that explicit mode disables every discovery path, rejects all unresolved selections without partial traversal, preserves order across adapters, cannot reach a completeness global scan, and reports truncation correctly. Check all carriers and legacy defaults, frozen journey digest preservation, per-question errors and the mean-F1 gate (an error must block even at 90% mean), and UI review reset/error handling. Verify actual tests and saved evidence rather than treating this note as proof. Keep origin selection separate from traversal isolation, admission, inferred pending-intent fallback and generic `/v1/query`. Report actionable findings with severity, file/line and a concrete failing scenario; distinguish unverified items from defects. Do not alter packs or expected answers to make tests pass.
