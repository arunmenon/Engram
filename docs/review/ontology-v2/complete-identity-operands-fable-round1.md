**Verdict: REVISE (narrow), round 1 of 2.** The core fix is correct and safe, but the diff introduces one regression that contradicts its own stated boundary, and two identity-merge paths remain open that need a fix or a recorded deferral.

## What holds

- **Core fix:** `$.merchant + ':' + $.payment_id` with `payment_id` missing, null or empty now raises `missing_identity_operand` before the plan returns. This covers node keys, transition keys and node-ID endpoints.
- **No partial effects:** the plan is built in memory, so nothing is written. The worker dead-letters only that event (`worker/projection.py:232`) and replay records it as failed (`ontology/versioning.py:233`).
- **Preserved behaviour:** zero/false, explicit `''` literals, empty fan-out, positional filtering and legacy property semantics all behave as claimed.
- **Evidence:** my focus run gave 123 passed in 1.32s. The three candidate file hashes match `review-manifest.json`, and `baseline.json` and `red-composite.txt` match the claims.
- **Regex boundary:** sound and honestly reported. The pdlc keys at `pdlc.pack.yaml:1155-1169` (`$.title + ' ' + $.body`) are structurally identical to a bad composite, so no structural rule separates them without breaking unchanged behaviour.

## Findings

**F1. Medium, new regression: `pack_expressions.py:350-358`.** The post-check applies cell-level incompleteness to pattern search text, so one empty list cell discards every extracted ID.
- Witness: `regex_all($.messages[*], '([A-Z]+-[0-9]+)')` on `["fix ABC-1", "", "see ABC-2"]` gives `['ABC-1','ABC-2']` in legacy mode and `None` in identity mode. As a key, the plan is empty; with full cells it yields `Payment:ABC-1`.
- This contradicts the claim that pattern search text uses ordinary semantics. The shipped pdlc keys I listed use scalar inputs, so it does not show up in existing tests.
- Smallest fix: for `regex`/`regex_all`/`match`, test only scalar absence (`first is None or first == ""`, or `_text(first)` being empty) instead of `_incomplete_identity(first)`. Add one test with a list containing an empty cell.

**F2. Medium, pre-existing but squarely in S4: `pack_expressions.py:112-116`.** A literal-led composite key is not detected as an expression and becomes a constant identity.
- Witness: key `'pay-' + $.payment_id` passes pack validation, and payloads `P1`, `P2` and `{}` all plan the same node `Payment:'pay-' + $.payment_id`. Every record merges.
- The scope report treats this as a test-harness error, but a pack author hits the same thing.
- Smallest fix: at pack validation, reject a key or `node_id` constant that contains `$.` or `$event`. Otherwise record an explicit deferral with an issue in the scope report.

**F3. Low-medium, residual: `pack_projection.py:647`.** `match` lookup values still use legacy semantics.
- Witness: `match: {description: "$.merchant + ':' + $.parent_id"}` with `parent_id` missing plans a lookup for `{'description': 'M1:'}`. The legacy property text `M1:` (asserted by the new test at line 108) is exactly what it would match, so the edge attaches to records sharing only the merchant.
- I found no shipped pack with a composite `match` value, so tightening should be behaviour-neutral for shipped packs.
- Smallest fix: evaluate `match` equality values with `identity=True` and treat the error as "finds nothing". Otherwise state the exclusion in the report.

**F4. Low, disclosure: regex wrapper bypass.** `regex($.merchant + ':' + $.payment_id, '(.+)')` still plans `Payment:M1:`. The report says this; the test name `..._cannot_hide_missing_input` overclaims for the regex rows. Add this witness as an explicit "known, pack-author responsibility" test or rename.

**F5. Low, undisclosed compatibility.**
- Events that previously projected with a fabricated key now dead-letter whole, including their valid upserts, and count as replay failures on rebuild. Shipped packs have no composite keys, so this affects third-party packs only.
- `sha256($.statement)` with an empty statement (`pdlc.pack.yaml:1250`) previously merged into one hash-of-empty Decision and now silently produces no record.
- Both are the intended direction, but the report says nothing about rebuild or dead-letter impact.

**F6. Low: `IdentityOperandError` carries no node type or key name.** The dead-letter log shows only `missing_identity_operand`. Re-raising from `_keyed_refs` with type and key name (no values) would make refusals diagnosable.

**F7. Low, evidence hygiene.** `focused-final.txt` ends "6 failed, 115 passed"; the passing artefact is `focused-reviewed.txt` (123 passed, written later). Rename or remove the stale file.

## Limits

- Whitespace-only and object operands are not treated as missing (`M1: ` and `M1:{}` become keys). This is outside the contract's "missing/null/empty" wording but worth a line in the report.
- By inspection only, not run: `_text` truncates at 100,000 characters before `sha256`, so two long statements sharing that prefix would collide. Pre-existing.
- Not traced: whether the rebuild gate refuses on replay failures, and how the workbench (`workbench/engine.py:117`, no try/except in that file) and `worker/pack_extraction.py:188` surface the new error.
- I did not rerun the broad suite; `regression.txt` shows 984 passed and I took that as given. Memory backend and Python 3.14 only.

Spend for this round: about $2.45 of the $5 cap.
