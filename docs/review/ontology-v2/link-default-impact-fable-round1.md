## Verdict: PASS (round 1)

No blocking defects in scope. The 10-line change does what the policy says, and the downstream gates behave correctly. Two low-severity wording fixes are worth making but do not need a second round.

## What I verified

- **Original failure reproduced and closed.** The base classifier (loaded from `b0bfcf6`) returns `additive` / "documentation or vocabulary changed" for confirmed->proposed. The candidate returns `breaking` with a major-version problem for 1.0.0 -> 1.1.0.
- **Effective defaults are the right seam.** `link_defaults` is set in one place (`ontology.py:939-943`) and read by one writer (`pack_projection.py:557`). Extraction never reads it and always writes `proposed`.
- **Metadata no-ops stay quiet.** Implicit vs explicit `confirmed` is additive (tested). A change to `inferred_links_start_as` alone is also additive with no "defaults changed" reason (my witness, not in the tests).
- **Attribution is correct.** A pack's link policy only reaches its own edges, so `pack = after.pack` charges the right pack.
- **Gates hold.**
  - A recorded graph with a non-default value (`proposed`) round-trips through `record_state` / `read_state` and is refused on change.
  - Version problems refuse first, even with `allow_breaking=True`.
  - Status reports `change.kind=breaking` and `processing_ready=False`.
- **Admission slice is untouched.** `_compare_events` and `_check_versions` are not in the diff.
- **Tests and hashes.** The three focused files pass (85 passed), and the manifest hashes match both files.

## Findings (low, non-blocking)

1. **The code comment's rationale is partly wrong** (`pack_versioning.py:227-229`, repeated in `link-default-impact.md:9`).
   - Defaults only flow through projection edge writes, which are never create-only; only extraction uses `create_only` (`pack_extraction.py:555`). So the "create-only links" clause does not apply to defaults.
   - Witness on the memory backend, replaying in place under the new packs: the changed default converged (`link_status=proposed`); the removed default did not (stayed `confirmed`).
   - So removal is the demonstrated non-convergence. Treating value changes as breaking is a conservative choice, not a demonstrated necessity.
   - Smallest correction: reword to "a replay merges writes, so a removed default stays on existing links; convergence of changed values is not established across backends." Recheck: read-only.

2. **Contract docs are stale.**
   - The module docstring's `breaking` list (`pack_versioning.py:14-18`) omits effective link defaults.
   - `link-default-impact.md:13` still says "implementation starting."
   - Correction: one clause in the docstring and a status update. No recheck needed.

## Conservative limitations (policy as chosen, not defects)

- **Inert changes are also breaking.** A default change is breaking and needs a major bump even when every rule sets the field explicitly, or when no rule writes the edge.
- **`applies_to` additions are breaking.** Adding an edge to the policy's `applies_to` adds confidence/method defaults; before this slice that was additive.
- **Two cases are untested.** The `inferred_links_start_as` no-op and the `applies_to` route have no test; one parametrized case each would pin them.

## Broader existing gaps (outside this slice)

- **Rule-level equivalent is still a mapping change.** Dropping `set: {link_status: confirmed}` from a rule, so the edge falls back to a `proposed` default, classifies as `mapping` with in-place replay. By the same merge mechanism, a dropped `set` with no default behind it would stay on existing edges; I did not run that case.
- **The override records success without reconstruction.** With `allow_breaking=True`, reconcile records `applied=breaking`, links keep `confirmed`, and readiness reports processing and evaluation ready. The refusal hint still offers the override next to rebuild. You declared this unchanged.
- **Status values are not validated.** `declared_links_start_as: bogus` composes and becomes the default.

## Evidence limits

- Memory backend only, Python 3.14 locally; nothing run against Redis, Neo4j or Spanner.
- I did not rerun the broad suite; I only read the tail of `regression.txt` (895 passed).
- The replay witness is one event and one edge.
- The manifest does not cover the docs file.
- Spend was about $2.30 of the $5 cap.
