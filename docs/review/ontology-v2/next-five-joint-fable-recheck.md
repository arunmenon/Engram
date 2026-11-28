## Verdicts

- **S2 / PR146 at `1b65173`: REVISE.** Two silent-loss defects reproduce by probe. One was introduced by the B1 correction; the other is B2 left incomplete.
- **S3 / PR148 at `712f7be`: PASS for its bounded follow-up** (null-aware receipts and mutation hashes). It stacks on `1b65173`, and both S2 defects reproduce on the S3 head too, so it should not merge ahead of the S2 fix.

Identities check out: all three heads match their manifests, worktrees are clean before and after, and every manifest hash matches (27 / 17 / 46 files). I edited nothing in any repo; probes live in `/tmp/fable_probe/`.

## S2 required findings

**R1. A link write that fails after capture is lost on retry, and the run reports complete.**
- **Cause:** when both endpoints exist, `capture` settles the row terminal (`worker/relationship_recovery.py:161-191`) before the event's own edge write runs (`worker/pack_projection.py`, the `upsert_edges` call after `capture`). On retry, line 158 suppresses the write because the row already covers that order key.
- **Witness 1, new at `da116d0`:** a recovered edge, then explicit replay under a changed mapping with one injected `UnavailableError` on `upsert_edges`. The first replay reports `failed=1`. The second reports `failed=0, relationships_complete=True`, yet the edge lacks `note: 'new effect'`. At `5fe0ecd` the same retry writes the note.
- **Witness 2, already present at `5fe0ecd`, not in either earlier report:** a later ordinary event on a terminal row, same injected failure, then redelivery. Field `b` is never written and `finish()` is complete.
- **Smallest fix:** make the event's effect on the edge and the terminal status one atomic unit on the endpoints-present path, for example by having the settle transaction apply that pointer's fields.
- **Verification:** both witnesses end with the field present or a blocking row, on memory and the Spanner fake, and `test_redelivery_of_a_deferred_event_keeps_a_person_reviewed_relationship` still passes.

**R2. B2 only covers fields that have no recorded winner.**
- **Cause:** `domain/relationship_recovery.py:66` treats a field as covered if any winner is recorded, without comparing order keys.
- **Witness:** log positions 1 (`a=one`), 2 (`a=two`), 3 (`b=three`). Deliver 1 and 3 deferred, target arrives, recover, then deliver 2 for the first time. The edge keeps `a=one` and nothing is reported. With the target present first, the same delivery order gives `a=two`.
- **Smallest fix:** treat a field as covered only when its recorded winner is at or after the incoming order key. Fields with an older winner need ordinary overwrite, not fill-missing.
- **Verification:** the witness gives `a=two` in both orders on memory and the Spanner fake, and the existing disjoint-field test still passes.

## S2 corrections that held

- **B1 stranded row and retired truncated diagnostic:** the repo tests pass and the code reads correctly; the R1 crash window is the only gap.
- **B3:** deadlines return incomplete, non-fence recovery errors no longer fail the ACK, and configured bounds reach replay.
- **Monotonic terminal status:** present in all three adapters.
- **Nested-null effect hashing:** `test_nested_json_null_is_not_equivalent_to_a_missing_field_in_a_pinned_effect` passes and the code reads correctly; I ran no separate S2 null probe.

## S3 follow-up

Probed on memory and the Spanner adapter over the transaction fake:

| Case | Without replay | Explicit replay |
|---|---|---|
| `{x:null}` to `{}` | refused, `write_order_changed_effect_without_explicit_replay` | record and link become `{}` |
| `{}` to `{x:null}` | refused | both become `{x:null}` |
| `{a:{b:null}}` to `{a:{}}` | refused | both become `{a:{}}` |

- **Retries:** a same-bundle retry and an equivalent bundle bump are both no-ops in every case.
- **Receipt compatibility:** on identical plans in one process, the old and new algorithms give the same whole-plan receipt and recovery descriptor for scalar, lookup plus multi-effect, and added-absent-mapping plans. Per-field hashes match for null-free values.
- **Absent mapping:** it keeps the original receipt.

## Executed vs inspected

- **Executed:** 62 focused tests on the S2 tree and 132 across the three files on the S3 tree, plus the probes above on local Python 3.14.
- **Inspected only:**
  - Neo4j fill-missing and terminal-check Cypher.
  - The manifest logs (all show exit 0); I did not rerun the 1250 / 1323 / 1353 selections, conformance, mypy or lint.
  - The cumulative candidate `0d573b0`: no probes run there, but its recovery and projection file hashes match the S3 head, so it carries R1 and R2.
  - Original review reports: hashes match the manifests; I did not diff them against the raw originals.

## Retained lows and limits

- **Not exercised:**
  - R1 on S3 ordered links.
  - List-nested nulls: a list-valued `json` field was not stored at all in my probe.
- **New lows, code reading only:**
  - `semantic_digest` raises on NaN or Infinity; I did not check whether ingest can produce one.
  - A diagnostic already retired by replay is not re-raised if a live redelivery truncates again.
- **Earlier lows unchanged:** equal-position conflict fence, unbounded capture cost per flush, dangling optional rows, and reserved-row counts on memory and Spanner.
- **Evidence boundary:** as you stated it; no Neo4j or real Spanner execution, no CI 3.12.

Spend was about $3.4 of the $5 cap.
