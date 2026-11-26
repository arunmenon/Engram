# Slice 89, Fable review round 2 of 2

**Verdict: accept. No material findings, and no new minor work requested.** The three round 1 corrections are applied, the code under review is byte-identical to the recorded round 2 hashes, and the 65 and 216 results hold on this candidate. Acceptance of #89 is met within the slice's stated scope.

## Candidate identity

- **Commit:** `1026719bd0908d227936c068c427c9c5fc8d084a` on `fix/89-pack-test-baseline`, a single commit on base `ad71ea42c560685e89e295fcb8354a72f071b9dd`. The working tree was clean before and after my runs.
- **Target branch:** `integration/engram-ontology-v2` (local and origin) is still at `ad71ea42`, unmodified.
- **Code hashes:** sha256 of the committed blob and the working-tree file both equal `candidate-round2-code.json` for all three files:
  - `tests/unit/test_ontology_packs.py`: `56c28df6…053b60e1`
  - `tests/unit/test_pack_admission.py`: `f00e4d53…60666330`
  - `docs/runbooks/pack-authoring.md`: `cf8624cf…57299087`
- **Scope:** `git diff BASE..HEAD -- src tests/fixtures docs/research` is empty, so runtime source, packs and fixtures are byte-identical to base. The commit touches five files: two tests, the runbook and the two review records.

This verdict covers those three hashes at `1026719`. If report-only documentation is appended later, acceptance carries over only if the three hashes still match; I have not reviewed any later bytes.

## What I reran versus what I only read

Reran in this worktree with `PYTHONPATH=src` and the existing Engram virtualenv (Python 3.14.2). `context_graph` resolves to `<isolated slice89 worktree>/src/context_graph/__init__.py`.

| Check | Result |
| --- | --- |
| Two changed test files | 65 passed |
| Seven-file regression selection from `slice89.md` | 216 passed |
| `tests/unit/test_pack_toy_end_to_end.py -k memory` | 1 passed, 2 deselected, 2 warnings |
| `ruff check` and `ruff format --check` on the two test files | pass |
| `git diff --check BASE..HEAD` | clean |

Read only: `baseline.txt`, `after.txt`, `regression.txt`, `crm-memory.txt`, `ruff-check.txt`, `ruff-format.txt`, `diff-check.txt`. Their final lines agree with my reruns. I did not rerun the base-state failure; the 26 failed / 38 passed baseline remains Codex's evidence.

Not run: the Redis/Neo4j and Spanner parametrizations, the Python 3.12 CI job, and anything live or cloud.

## Round 1 corrections

1. **CRM result recorded: closed.** `slice89.md:24` now states the command and result, and that the two external-backend parametrizations were not run. This matches my rerun.
2. **Explicit `handling: processed` documented: closed.** The runbook now says the workbench variant adds payload contracts and explicit `handling: processed` for all six events. A semantic diff of the two YAML files confirms this is the whole difference: only `events` differs, and each of the six events differs in exactly `handling` and `payload_contract`. Both files are `crm` `1.0.0`.
3. **Formatting: closed.** Numbers are spaced and the em dashes in `slice89.md` are gone. The one em dash left in the diff is inside `slice89-fable-round1.md`, where it quotes the original defect; it needs no change.
4. **Evidence retention: closed.** The ruff and diff-check outputs are retained. The 26 baseline failing IDs in `slice89.md` are identical as a set to the `FAILED` lines in `baseline.txt`.

## Acceptance of #89

- **Shipped PDLC version and node catalogue:** the loaded pack is `2.1.0` with 18 node types, matching the pinned version and the 18-name set in the test. The named set is stricter than the old count.
- **Whole-event fixture coverage:** the pack declares 25 events and the fixture has 25 unique cases (20 `deterministic`, 5 `missing_mapping`). The new guard checks for duplicates, declared-versus-fixture equality and compiled-versus-declared equality.
- **Per-event unsupported/processed checks:** the parametrized test body is unchanged apart from removing the stale `len(rules) == 23`. All 25 cases now execute and pass.
- **Dependency ordering:** the `["core", "memory", "user", "pdlc"]` assertion is unchanged and passes.
- **CRM identity advice:** correct. Name and version alone do not distinguish the two variants, so recording path or purpose, `registry.version` and the selected packs is justified.

## Limits of this verdict

- The two review records in the PR are documentation. They are not production test output and not an authorization to merge, close the issue or deploy.
- The verification is local and on Python 3.14, not the Python 3.12 CI job or real backends.
- The round 1 observations stand as accepted trade-offs: `compiled == declared` is a weak check on its own, and the event catalogue has no literal pin.
- `slice89.md:30` still says "Round 2 remains pending". That is true of the reviewed bytes and is for the coordinator to update when persisting this report.

No third round is warranted on the evidence.
