## Verdict: PASS

No blockers. All four corrections hold under my own witnesses, run through the candidate and through base `c831f18` loaded in memory for comparison. Three low or cosmetic residuals should be recorded in the slice record; none needs a code change.

**Source identity:** HEAD is `c831f18`, and the three frozen files match `review-round2-manifest.json` (`d0abedca…`, `f324021a…`, `934e4799…`) both before and after my runs. The round-1 report in the worktree is byte-identical to the evidence copy (`1d0eda7d…`).

## Correction checks

| # | Correction | Result | Evidence |
|---|---|---|---|
| 1 | Implicit provenance counts only with participation on both sides; owner fallback | Holds | Core retarget with `aa` identical and `bb` doc-only minor gives `pack_changes` and `contributor_changes` of `{core: breaking}` only, no version problems. |
| 2 | Withdrawal checked before the removed-edge exit | Holds | Loop now sits above the `after is None` check (`pack_versioning.py:296-317`). Edge removed with `bb` at 1.1.0 is refused; with `bb` at 2.0.0 there are no problems. |
| 3 | Composed rule order preserved; changed order requires replay | Holds | Order-changing transfer gives `mapping` with replay of `aa.observed`, and `aa` needs a major. The stored-outcome test passes against real `project_ledger`, `rebuild` and `reconcile`. |
| 4 | Endpoint reasons emitted once; actor metadata separate | Holds | The core retarget prints one "contribution withdrawn" line and one "endpoints removed" line. Redundant extension withdrawal staying breaking is recorded in the doc. |

On correction 3, the flattened per-event order equals execution order because the registry appends rules pack by pack (`ontology.py:897-905`), so packs never interleave.

## Other checks requested

- **Unchanged owners:** not charged for a target-only withdrawal, for two contributors withdrawing (with `aa` doc-only minor accepted and `cc`'s minor refused), or for a foreign rule edit or removal.
- **Improvement over base:** a pack adding or removing one of several node types no longer charges core.
- **Global gates:** an aggregate breaking rule change always implies a breaking contributor. `reconcile` still reads only `kind`, `version_problems` and `replay_event_types`, and I found no consumer of `contributor_changes` elsewhere in `src`.
- **Version bumps:** the normal and pre-1.0 parametrised cases pass, and a pre-1.0 mapping change still accepts a patch.
- **Preservation controls:** 613 tests passed across the contributor, event-admission, link-default, removed-field, pack-versioning, rebuild-completeness, composition, readiness and hex-purity files. The 21 S5 tests pass.
- **Lint and types:** Ruff check, Ruff format check and mypy on the module pass.

## Residuals to record (non-blocking)

1. **LOW: a pack leaving provenance entirely still charges core.**
   - When `bb` drops its last node type or is removed from the bundle, `pack_changes` shows `core: breaking` even with core byte-identical. No version is demanded of an identical core.
   - If core has a concurrent doc-only minor bump, it is refused with "a breaking change needs a major version".
   - Base does the same and also charges `aa`, so this is narrowed, not introduced. It follows from the one-sided fallback I suggested in round 1.
   - Record it as a limit of the fallback; fixing it would mean unreviewed code.

2. **Cosmetic: wording.**
   - A pure reorder reports "projection of X added"; "reordered" would be accurate.
   - The doc's "even a transfer of disjoint writes conservatively requires replay" is true only when the composed order changes. An order-preserving transfer gives `additive` with no replay, with the old owner still needing a major. That is correct, because the projector ignores the owning pack (`pack_projection.py:374`).

3. **Cosmetic: stale evidence text.**
   - The doc cites 989 passed with four excluded, which is the round-1 `regression.txt`.
   - `regression-round2.txt`, written after the source freeze, records 1090 passed and 2 skipped.
   - The doc also omits `red-review-findings.txt`, `focused-round2.txt` and `regression-round2.txt` from its evidence list.

One behaviour change beyond attribution is disclosed and sound: reordering rules within a single pack is now `mapping` with replay, where base gave `additive` with none. At 1.0 and above it adds no version burden, since a minor is needed either way.

## Evidence limits

- Local Python 3.14.2 with memory adapters only. Nothing here is live Redis, Neo4j or Spanner evidence, Python 3.12 CI, or deployment acceptance.
- I did not rerun the 1090-test selection or the exact 155-test focus command; my 613-test run is a superset by file, not the recorded command.
- My witnesses are ad hoc and were not added to the suite. The whole-pack provenance case, the order-preserving transfer and the within-pack reorder have no committed tests.
- I did not test a bundle whose pack order changes with no content change.
- This review covers the manifest hashes above. Fixing the doc text for residuals 1–3 changes the doc hash and should be disclosed as not independently reviewed; any later code change is unreviewed, and no third call is available.
