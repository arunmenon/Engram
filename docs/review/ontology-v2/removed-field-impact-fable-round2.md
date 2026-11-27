**Verdict: PASS.** No unresolved blockers in the bounded S1. The medium finding and the edge-test low are closed; the doc low is still open in the file as it stands, which you said the final record will fix.

Reviewed files match `review-round2-manifest.json` (`pack_versioning.py` cf8ca3e5…, `test_removed_field_impact.py` ec2eb6ed…). The six-file focused set gave 146 passed on my single run.

## Closure of round-1 findings

1. **Medium, static null-preserve: closed.** `entries` (`pack_versioning.py:519-532`) now drops a `set` entry from the property targets when its value is a literal null and `on_null` is not `clear`, so it lands in the removed-assignment branch.
   - The new test `test_static_null_preserve_stops_writing_and_requires_reconstruction` asserts what I asked for: replay keeps "A", fresh omits it, classification is breaking, reconcile refuses, and state, node and source documents are unchanged.
   - `red-null-preserve.txt` shows that test failing before the correction.
2. **Low, edge replay retention: closed.** The edge test now projects old then new onto a disposable graph and asserts `reviewer == "Alex"` before the refusal and fresh-absence checks.
3. **Low, stale doc: not yet closed.** `docs/review/ontology-v2/removed-field-impact.md` still says "Eight new", "145 focused" and "Status: first Fable review running", and does not mention the null-preserve case. Non-blocking; the items to record are listed at the end.

## Independent probe (replay versus fresh, memory backend)

| Old → new assignment | Classified | Replay | Fresh | Result |
|---|---|---|---|---|
| real → `{value: null}` | breaking | A | absent | correct |
| real → `{value: null, on_null: preserve}` | breaking | A | absent | correct |
| real → `{value: ~}` | breaking | A | absent | correct |
| real → `{value: null, on_null: clear}` | mapping | absent | absent | explicit clear preserved |
| real → `{value: $.title, on_null: clear}` | mapping | A | A | correct |
| null-preserve → real | mapping | A | A | correct |
| null-preserve → `set: {}` | mapping | absent | absent | correct |
| real-with-clear → null-preserve | breaking | A | absent | correct |
| null-clear → null-preserve | breaking | absent | absent | conservative false-breaking |
| plain `$.title` → strict `{value: $.title}` | mapping | A | A | correct |
| real → `{value: $.absent_field}` | mapping | A | absent | diverges; dynamic, outside S1 |

An assignment with `value` omitted is rejected at pack validation, so there is no bypass through that form.

## Scope and preserved behaviour

- **Explicit clear:** stays a property target and stays mapping; `test_explicit_clear_remains_supported_in_place` still passes through real reconcile.
- **Original tests:** the diff against 9013a83 touches only `pack_versioning.py`, and the only new test file is `test_removed_field_impact.py`. Existing tests, fixtures and oracles are unchanged.
- **Scope:** no growth. Transitions remain excluded from property expansion, and the reconcile, version and `allow_breaking` paths are untouched.

## Exact limits

- **Environment:** memory backend and local Python 3.14 only. Nothing ran on CI 3.12, Neo4j, Redis or Spanner.
- **`on_null: refuse`:** with a literal null it is treated like preserve and classified breaking. That is the safe direction, but I read it from the code and did not execute it.
- **Dynamic null:** an expression that evaluates to null at runtime is still classified mapping and diverges, as the last table row shows. This is the stated S1 exclusion, not a defect in this slice.
- **Not assessed:** `when` conditions, lookups, transition guards, multi-pack rules on one event, and S5 owner attribution.
- **Larger regression:** I did not rerun it; your rerun stands on its own.

## For the final doc record

- Nine cases and 146 focused tests, with the null-preserve test and `red-null-preserve.txt` named.
- The conservative false-breaking cases: duplicate same-identity parts, and null-clear → null-preserve.
- The dynamic-null divergence as an explicit out-of-scope limit.
- The final status line with this verdict.

I ran the focused command once and made no edits to the worktree. I read "at most two calls" as two Fable review rounds, per the doc's "two calls at $5 each", not as a cap on tool calls; this round used four read-only tool calls.
