**Verdict: PASS, round 2 of 2.** All seven round-1 findings are closed and I found no remaining blockers; one low-severity corner and a few report gaps are listed below as non-blocking.

## Verification

- **Hashes:** all four files in `review-round2-manifest.json` match the worktree, including `ontology.py`.
- **Focus run:** 157 passed in 1.86s on the six-file command you gave; the new file collects 29 cases.
- **Static checks:** ruff check, ruff format and mypy on the three runtime modules pass.
- **Old tests:** no tracked test file is modified; the only test change is the new untracked file.
- **Wider run (mine):** `tests/unit` plus `tests/conformance` gave 3039 passed and 237 skipped, with six failures and one collection error, none caused by this diff:
  - `test_backend_end_to_end[memory]` (409 on ingest) fails identically against an export of base `9013a83` source.
  - Five `test_procurement_pack.py` failures are a missing untracked file, `docs/examples/procurement/procurement_ops.pack.yaml`, absent from both checkouts.
  - `test_empty_target_activation.py` cannot import a helper that lives in `scripts/`.
- **Regression artefact:** `regression-final.txt` now reads 991 passed, 4 deselected.

## Closure of round-1 findings

| Finding | Status | My witness |
|---|---|---|
| F1 pattern list | Closed | `regex_all($.messages[*], …)` on `["fix ABC-1", "", "see ABC-2"]` and with a `None` cell gives `ABC-1`, `ABC-2`; all-empty, `[]` and missing give no record. |
| F2 literal-led constants | Closed | `'pay-' + $.payment_id` is rejected in upsert key, `match`, `match_any_prefix`, `node_id` and transition key; the same string in `set` still loads. |
| F3 lookup | Closed | A composite `match` or `match_any_prefix` with a missing or empty operand plans no lookup and records `missing_lookup_identity_operand (Payment.description)`; the complete case plans `M1:P0`. |
| F4 regex wrapper | Closed | Test renamed; the permissive-regex witness asserts `Payment:M1:` as a known boundary. |
| F5 disclosure | Closed | The report states whole-event dead-letter, replay failures, and no record for an empty dynamic hash. |
| F6 diagnostics | Closed | Errors read `missing_identity_operand (Payment.id)` and `(node_id)`, with no values. |
| F7 evidence hygiene | Closed | Failing logs are `intermediate-failures-1/2.txt`; the pass is `focused-r2-final.txt`. |

Compatibility at the seams:
- **Shipped packs:** I scanned 25 pack/ontology YAML files (900 key, match, prefix and node-ID values); none trips the new validation.
- **Default evaluation:** `evaluate()` without the identity flag is unchanged (`$.a + ':' + $.b` with `b` missing still gives `x:`).
- **Workbench:** `POST /admin/tenants/{id}/validate` catches the new error and returns it as a failed validation, not a 500.

## Non-blocking notes

1. **Fan-out corner, undisclosed, present since round 1 (I missed it then).** In identity mode `regex_all` on absent or empty scalar text returns `None` instead of `[]`.
   - Witness: key `{id: $.items[*], ticket: regex_all($.text, …)}` with `text` missing or `""` now gives no record, silently.
   - With `text` present but unmatched it still refuses with `unequal_key_lengths`. From the base code, base returned `[]` here and so refused both; I did not run this on base.
   - No identity is fabricated either way. Fix by returning `[]` for `regex_all`, or add a line to the report.
2. **Report is stale and unhashed.** `complete-identity-operands.md` still says "Full regression is rerunning" and "Final peer review is pending", and it is not in the manifest.
3. **F2 tightening has no escape form.** A genuine constant such as `US$.50` in a key or match is now rejected. The message does not name the offending field. A third-party pack with such a value fails at registry composition, so it will not load.
4. **Lookup refusal is soft.** A bad lookup operand drops only that lookup, and the rest of the event's plan still applies with a `pack_write_rejected` warning. A bad key or node ID refuses the whole event. The report implies this but does not state the asymmetry.
5. **Direct empty match value is unchanged.** `match: {description: $.d}` with `d == ""` still plans a lookup for `''`. This is pre-existing and outside S4's "hidden by construction" scope.
6. **`sha256` over a list with an empty cell gives no record.** This is consistent with the rule but has no test.

## Evidence limits

- Memory backend and the local venv only; no Redis, Neo4j, Spanner or CI 3.12 proof.
- The procurement pack could not be checked against the F2 tightening because the file is absent.
- Whitespace and object operands, the permissive-regex capture and the 100,000-character truncation remain as the report states.
- The base comparison used a temporary export of base source outside the repo, since removed; the worktree is unchanged.

Spend this round: about $2.90 of the $5 cap.
