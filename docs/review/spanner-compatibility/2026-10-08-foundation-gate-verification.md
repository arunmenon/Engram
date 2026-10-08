# Foundation handoff gate: verification and stakeholder walkthrough

Status: PAUSED AT STAKEHOLDER REQUEST. This is the bounded foundation gate approved before G04, not completion of #34 or #41. G04 has not started. Historical migration and cross-version upgrades remain excluded.

## What this gate changes

Previously, the walkthrough branch held the goal record while the snapshot held necessary runtime and helpers. This gate uses `feature/engram-verified-foundation`, based on snapshot `f6fd87ce1086522bdc6fea1846d92ab9d6f50f31`, as a self-contained checkout. Original branches and the original dirty working tree are preserved. The approved review/tooling checkpoint is published at source commit `b51437bec119a3ae4c50c75a8f076fb133c7473e`; this does not complete the paused cloud gate. See [publication and issue receipts](2026-10-08-foundation-gate-publication.json).

The [dependency inventory](2026-10-08-foundation-gate-dependencies.csv) and [import/subprocess graph](2026-10-08-foundation-gate-imports.json) identify the shared source and helper dependencies. Static imports overapproximate execution; imported alternative providers are not acceptance runners. The tracking script is an explicit subprocess dependency. Import probes confirm critical runtime and helpers resolve to this checkout, not the original working tree.

## Fresh environment and local checks

Repeat from the integration checkout:

```sh
uv sync --python 3.12 --frozen --extra dev --extra spanner --extra embedding --extra gcs
HF_HUB_OFFLINE=1 PYTHONPATH=src:scripts .venv/bin/python -m pytest -q tests/unit
.venv/bin/ruff check src
.venv/bin/mypy src
```

Python 3.12 is the verified interpreter prerequisite. Unqualified `uv sync` chose Python 3.14 and the locked torch wheel was unavailable on this Mac; [attempt 01](runs/20261008-local-foundation-gate-01/results.json) preserves that failure. Tests importing script helpers also need `scripts` on `PYTHONPATH`; the initial `src`-only collection failure is retained in attempt 02. These are explicit setup requirements, not cloud product passes. Local tests use fakes where appropriate and never count as Spanner acceptance.

| Check | Result | Evidence |
|---|---|---|
| Frozen Python 3.12 installation and critical import ownership | Passed | [Environment](runs/20261008-local-foundation-gate-02/resolved-environment.json) |
| Source lint | Passed | [Log](runs/20261008-local-foundation-gate-02/ruff.log) |
| Full source strict type check | Passed | [Log](runs/20261008-local-foundation-gate-02/mypy.log) |
| Full unit suite | Passed: 2,531 passed, 15 skipped, 170 warnings; first failure retained | [Retained failure](runs/20261008-local-foundation-gate-02/pytest-with-scripts.log), [recheck](runs/20261008-local-foundation-gate-03/pytest.log) |

Only two test files required corrections: PDLC version/node-count expectations now reflect committed 2.1.0 and DesignApproval; admission inventory compares the exact event set with all 25 independently authored fixtures instead of hardcoding 23. Per-event valid/unsupported assertions remain unchanged. Targeted recheck: 64 passed. Astra independently confirmed those corrections. No runtime source was changed by this gate.

## Independent review

[Scoped Astra review and prior-finding dispositions](2026-10-08-foundation-gate-astra-review.md): no new blocking source defect identified. It reconciles authoritative admission, immutable receipts, worker refusal/ACK/DLQ, same-snapshot Spanner ownership checks, response authorization, retrieval fixes and exact owned cleanup. Its source findings do not replace execution evidence. The subprocess inventory correction has been applied.

## Integrated Spanner reruns

Acceptance uses only `portiq-mvp/engram-experiment/engram-compat-target`. Credentials remain outside the repository. All three reruns use current PDLC 2.1.0 with mandatory core, optional memory/user disabled, authenticated private bound tenant `compat-control`, actual configured providers and all five actual worker loops. No direct artifact insertion or manual repair counts as success.

| Journey | Expected proof | Run/result |
|---|---|---|
| G01: PR activity | All eight original scenarios; exact ledger/graph/retrieval and forbidden effects | Passed: [10 checks including setup steps](runs/20261008-cloud-foundation-g01-02/observations.json); cleanup restored epoch32 |
| G02: planning | All 22 checks: versioned PRD/requirements/HLD/LLD, approval, revisions, rejection and retrieval | Interrupted at user request after 17 checks; [stop/cleanup record](runs/20261008-cloud-foundation-g02-01/user-stop.json); not a full pass |
| G03: implementation | All 28 checks: explicit ticket/code/review/test chain, failed and passing runs, isolation | Pending |

Repeat driver shape (replace the run ID and BOTH predecessor pins with the deliberately authorized current owner; do not use historical driver defaults):

```sh
HF_HUB_OFFLINE=1 PYTHONPATH=src:scripts .venv/bin/python scripts/engram_goal01_pr_demo.py --run-id UNIQUE_G01 --credentials /private/tmp/engram-spanner-token-env --expected-epoch CURRENT_EPOCH --expected-digest CURRENT_DIGEST
# After verified cleanup/restoration, use the observed authorized predecessor for G02, then G03.
# Drivers: scripts/engram_goal02_planning_demo.py and scripts/engram_goal03_implementation_demo.py
```

The credential script may bootstrap the token into a private 0600 file outside the repository; never publish its output. The goal drivers assert the project/instance and explicitly choose `engram-compat-target`, regardless of the credential file's database default. The first gate G01 attempt omitted the current digest and refused the old default before activation; its retained failed record demonstrates safe refusal, not an acceptance pass.

Each run must preserve observations, source hashes/archive, worker outcomes, retrieval responses and cleanup/restoration receipts. Owner epochs are explicit predecessor pins and may only advance serially after observed restoration. Earlier failed goal attempts remain preserved. A current-pack rerun is not historical migration.

## What the stakeholder demo will show

1. Start with an input payload and the authenticated Engram HTTP response.
2. Show its persisted Spanner event and receipt, then actual worker outcomes.
3. Show the expected domain artifacts, explicit relationships and evidence.
4. Ask the recorded retrieval questions through Engram; compare exact expected versus actual answers, including forbidden sibling leakage and honest failure results.
5. Show duplicate/rejection no-write checks and owned cleanup receipts.
6. Show what was reviewed, which GitHub issues received evidence, and what remains open.

## Issue reconciliation and limits

Progress/evidence updates posted to #34, #39 and #41; all remain open. See [comment receipts](2026-10-08-foundation-gate-publication.json). No existing umbrella closes on these bounded reruns. Assess any newly found defect separately with reproduction/evidence. No new feature bucket is implied merely by consolidating branches; distinct new scope would need explicit assessment. #45 and #46 retain their earlier closed fixes; the broader live-retry, retention, ordering, cutover, optional composition and public multi-tenant work remains open.

This verifies only the declared G01–G03 paths. It does not prove the original 65-scenario baseline, public tenant dispatch, all pack combinations, authenticated human review or external test execution. Producer review/test assertions remain assertions. G01 late-edit policy still preserves merged lifecycle while using delivery order for title/time. Unevaluated-bundle serving is explicitly enabled; no pack-wide evaluation claim. Monitoring export IAM failures must remain visible separately from the data path.

## Stakeholder pause checkpoint

No new runtime source changes during this gate. Two stale test assertions corrected and independently reviewed. At this pause checkpoint, gate branch changes/evidence were local and uncommitted. Publication of the subsequently approved cleanup does not complete the paused cloud gate. Existing original verified G01–G03 evidence remains intact. No automatic restart or G03/G04 execution.

## Approved tooling cleanup

Following the necessity decision table, the stakeholder approved keeping the safeguards, simplifying experiment tooling and deferring additional feature expansion. This authorizes the bounded local cleanup, not resumption of the cloud gate or G04.

Shared credential parsing, reserved-target settings, durable evidence writing, fingerprinting, owner observation and cancellation settlement now live in `scripts/engram_experiment_support.py`. The three goal drivers share authentication, snapshot observation and shutdown helpers. Old runner helper names remain explicit compatibility exports. Goal-specific fixtures, assertions, ownership resolution, cleanup intent and exact-key deletion checks remain in their existing files. Application source under `src/` is unchanged; no new dependency, framework or service was introduced.

The cleanup removes imports of historical scenario runners from goal driver dependencies. The [import/oracle checks](runs/20261008-local-foundation-tooling-01/import-and-oracle-checks.json) confirm CLI imports and preserve all 118 assertions (41 G01, 41 G02, 36 G03). New tests check authentication rejection, response authorization, cancellation settlement, shutdown ordering and error preservation. [Scoped Astra review](2026-10-08-foundation-tooling-cleanup-astra-review.md) found no blockers. Local verification passed: 2,539 unit tests, 15 skipped; helper/driver/test lint and import/oracle checks passed. Unit results are recorded in [the cleanup run](runs/20261008-local-foundation-tooling-01/pytest.log); no cloud acceptance is claimed for the refactored scripts.

No new feature bucket is needed: this is tooling simplification supporting existing #34/#39/#41. Their full acceptance remains open. The cloud gate remains paused, with the target empty at epoch34. Any later approved rerun must supply current epoch and digest explicitly. Recheck all three goal drivers after this shared-helper change, without historical migration scope.
