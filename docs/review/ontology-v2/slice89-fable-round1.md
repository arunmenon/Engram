# Slice 89, Fable review round 1 of 2

**Verdict: accept with minor corrections. No material findings.** The test changes are correct, not weakened, and scoped as authorized. Three small documentation corrections are worth closing before round 2.

## What I ran versus what I only read

Ran in `the isolated slice89 worktree` with `PYTHONPATH=src` and the Engram virtualenv; `context_graph` resolves to the worktree's `src/`:

- **Two changed test files:** 65 passed.
- **Seven-file regression selection named in `slice89.md`:** 216 passed.
- **CRM control:** `tests/unit/test_pack_toy_end_to_end.py -k memory` gave 1 passed, 2 deselected.
- **Lint:** `ruff check` and `ruff format --check` on the two test files pass; `git diff --check` is clean.
- **Scope:** `git diff ad71ea42 -- src tests/fixtures docs/research` is empty, so runtime, packs and payload fixtures are byte-identical to base.
- **Target branch:** `integration/engram-ontology-v2` (local and origin) is at `ad71ea42`, the same as the base.
- **Candidate identity:** the sha256 of `git diff` equals that of `candidate-round1.patch`.
- **In-memory probes (no file edits):** loaded the shipped PDLC pack and both CRM variants, and replayed the new test's logic against mutated fixture lists.

Read only: `baseline.txt`, `after.txt`, `regression.txt`, `crm-memory.txt`, `candidate-round1.json`. I did not re-run the base-state failure; the 26 baseline failures are taken from `baseline.txt` (1 PDLC load test plus 25 parametrized admission cases, 26 failed and 38 passed).

## Standards and spec checks

- **Version and dependencies:** the shipped pack is `2.1.0` and loads as `core, memory, user, pdlc`. The order assertion is unchanged and the pin at `tests/unit/test_ontology_packs.py:154` is correct.
- **Node catalogue:** the 18-name literal equals the loaded pack's node types exactly. `DesignApproval` is source-justified: declared at `pdlc.pack.yaml:91`, with an `APPROVES` edge (line 158) and a projection rule for `pdlc.design.approval_recorded` (line 1135). A named set is stricter than the old count, since it catches renames and swaps.
- **Event catalogue:** the pack declares 25 events, the fixture has 25 unique cases, and the compiled policy has 25 `pdlc` entries. Replaying the new test's logic, a missing fixture, a duplicate fixture and an extra fixture each fail.
- **Handled versus unsupported:** the per-event test body is unchanged apart from removing `assert len(rules) == 23`, and all 25 cases now execute. The split is 20 processed and 5 unsupported, and the 5 unsupported are exactly the events with no projection rule. Flipping any case's classification fails all 25, so those assertions are not vacuous.
- **CRM identity:** both files are `crm` `1.0.0`. The fixture has 0 of 6 payload contracts and the workbench variant has 6 of 6. `registry.version` differs between them (`sha256:5fdb09b6f10611af` versus `sha256:ca309e3160707654`, core only) and changes again with the default built-ins (`sha256:5f33badbdb5bbccc`), so the runbook's advice to record selected packs alongside the digest is justified.

## Minor findings

1. **`docs/review/ontology-v2/slice89.md:24` has a dangling promise.** It says the CRM control "is recorded below when complete", but nothing is recorded below. The record therefore claims less than the evidence shows. Smallest correction: replace it with the actual result and command (`tests/unit/test_pack_toy_end_to_end.py -k memory`: 1 passed, 2 deselected; the Redis/Neo4j and Spanner parametrizations were not run).

2. **`docs/runbooks/pack-authoring.md:9-10` understates the variant difference.** A semantic diff of the two loaded packs shows the workbench variant adds a `payload_contract` and an explicit `handling: processed` on all six events; nothing else differs. Smallest correction: "adds payload contracts and explicit `handling: processed`". Optionally note that workbench runs record `bundle_digest` (`workbench/engine.py:133`), which wraps `registry.version` plus processing bindings.

3. **`slice89.md` formatting breaks the parent `CLAUDE.md` rule against em dashes (lines 20-22) and fuses numbers into words.** Examples: "version1.8.0", "asserted23", "CRM1.0.0", "—26 failed,38 passed". In an evidence record this makes figures harder to read. Smallest correction: restore the spaces and replace the em dashes with colons.

## Observations needing no change

- **`tests/unit/test_pack_admission.py:78` (`compiled == declared`) is a weak check.** The inventory is built by iterating `registry.event_types`, so it only fails if the compiler drops or misattributes a `pdlc` event. The independent oracle is line 77 against the fixture file.
- **The event catalogue no longer has a literal pin.** A coordinated removal of an event from both the pack and the fixture would pass. That is acceptable: it needs a deliberate two-file edit, and the literal count is what went stale in the first place.
- **The removed comment explaining the old 16-to-17 node history has no replacement.** A one-line note that `DesignApproval` came with the 2.x design-approval rules is optional.

## Missing acceptance evidence

- No retained output for the ruff and `git diff --check` claims (I reproduced them, so retain or cite).
- No retained output for the intermediate "after first correction" state; `after.txt` is the final 65-pass state, which is sufficient if the doc says so.
- Baseline failure IDs live only in local evidence outside the repository. The doc says "local", which is honest, but PR readers cannot see them.

## Round 2 focus

Close findings 1 to 3, re-hash the candidate, and confirm the 65 and 216 results still hold. Nothing broader is warranted.
