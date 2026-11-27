**Verdict: REVISE (narrow).** The core S1 change is correct and its tests are sound, but one statically visible removal still gets accepted by normal reconcile and leaves the old value in place.

## Findings

### 1. Medium: literal-null assignment with default `on_null` is a removal the comparator accepts
- **Where:** `src/context_graph/domain/pack_versioning.py:519-523` (`entries` counts every `set` key as assigned), consumed at `:571`.
- **Witness:** old and new packs both require `pack.properties.v1`. Old has `set: {title: {value: $.title}}`; new is version 1.1.0 with `set: {title: {value: null}}` and the schema unchanged.
  - `classify_change` returns `mapping`, with no version problems and `replay_event_types={'demo.ticket.opened'}`.
  - `reconcile(..., allow_breaking=False)` accepts it and records the new version.
  - The original graph still has `title == "A"`; a fresh `rebuild` omits `title`.
- **Why it matters:** this is the S1 mismatch (the rule stops writing a declared field) reached through supported strict syntax. It is static, so it does not fall under the dynamic-value exclusion.
- **Smallest correction:** in `entries`, do not count a `set` entry as assigned when its dumped value is a dict with `value is None` and `on_null != "clear"`. Assigned to null-preserve then lands in the existing removed-assignment branch. `on_null: clear` must stay counted so the explicit-clear path remains mapping.
- **Verification:** add one stored-outcome test mirroring the node test: diagnostic replay retains "A", fresh omits it, `classify_change` is breaking, reconcile refuses, and state, node and documents are unchanged. Then rerun the six-file focused set.
- **Alternative:** if you decide null-preserve is intentional "keep existing", record it as an explicit bounded limit in the review doc. I recommend the code fix, since it is about three lines.

### 2. Low: edge test does not show replay retention
- **Where:** `tests/unit/test_removed_field_impact.py:133-172`.
- **Witness:** the test shows refusal and fresh absence, but not that replay keeps the edge value, which is the reason it is breaking rather than mapping. My probe confirms the memory graph retains `reviewer: 'Alex'` after old-then-new projection.
- **Correction:** add a disposable-graph replay assertion, as the node test has.

### 3. Low: review doc status is stale
- **Where:** `docs/review/ontology-v2/removed-field-impact.md:11` still says "Status: reproducing the defect."
- **Correction:** update it, and record the duplicate-part false-breaking bound described below.

## Checked and acceptable
- **Plain removal:** `set: {}` is breaking, and 1.0.0 to 1.1.0 raises a version problem.
- **Plain `title: null`:** rejected at pack validation, so there is no legacy-form bypass.
- **Explicit clear:** stays mapping and converges (replay and fresh both absent).
- **Changed expression:** stays mapping and converges on the fixture.
- **Duplicate same-identity parts:**
  - Dropping the part that set `summary` is caught as breaking; the older membership-based `missing` check alone would not catch it.
  - Moving `summary` into the sibling part is mapping, which is correct.
  - Dropping one of two parts that both set `title` is breaking. This is a conservative false-breaking case, bounded to duplicate identities.
- **Qualified versus bare type names:** these fall into the existing identity-changed breaking branch (read from the code, not run).
- **Schema and assignment removed together:** breaking, with both reasons listed.
- **Scope:** no growth. Transitions are excluded from property expansion, and the reconcile, version and `allow_breaking` paths are untouched.
- **Focused suite:** 145 passed on my run. Your `regression.txt` shows 955 passed, 4 deselected.

## Evidence limits
- Everything ran on the memory backend with local Python 3.14; nothing on CI 3.12 or a live backend.
- Neo4j edge writes use `r += row.props` (`adapters/neo4j/pack_graph.py:158`), which is consistent with retention, but I did not execute it. I did not inspect Spanner.
- Rule changes involving `when`, lookups, transition guards, and expressions that yield null at runtime were not assessed, per the contract.
- I did not exercise multi-pack rules on one event or the owner-pack attribution of the breaking note (S5).
- Probe scripts are in `/tmp/s1probe/`; nothing in the worktree was modified.
