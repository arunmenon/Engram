## Verdict: REVISE (narrow)

The separate `contributor_changes` axis is sound and I would keep it, but two attribution paths give wrong per-pack results against the S5 contract. Both have small fixes. One claim about rule transfer also needs scoping.

I reviewed the candidate at the manifest hashes (`pack_versioning.py` 8ffd097e…, test file 38f87890…, HEAD c831f18). The focus suite reproduces at 152 passed.

## Findings

### 1. MEDIUM: implicit provenance charges packs that did not cause the change
- **Where:** `src/context_graph/domain/pack_versioning.py:254-258`, with the fallback at `:325-326` and `:343-344`.
- **Witness:** core retargets `DERIVED_FROM.to` from `[Event]` to `[Entity]` with a major bump; `aa` is byte-identical; `bb` has a doc-only edit.
- **Result:** `pack_changes` and `contributor_changes` are both `{aa: breaking, bb: breaking, core: breaking}`. `bb` gets "a breaking change needs a major version" (shown for a patch bump; the merged kind is breaking, so a minor bump is refused too).
- **Why it is wrong:** the goal says not to charge an unchanged dependency. Base charged only core. The cause is that provenance membership comes from core's declaration, but line 255 treats it as the pack's own contribution.
- **Smallest fix:** count the implicit share only when the pack is in `from_packs`/`to_packs` on both sides. Otherwise charge the edge owner, and make the no-actor fallback charge `after.pack` instead of nobody.
- **Test to add:** this witness, asserting `aa` is absent from both maps and `bb` passes with a minor bump.

### 2. MEDIUM: extension withdrawal is not charged when the edge is removed in the same change
- **Where:** `pack_versioning.py:287-289`; the `continue` skips the contributor loop at `:291-305`.
- **Witness:** `aa` removes `RELATES` at 2.0.0 and `bb` drops its extension.
- **Result:** `contributor_changes == {}`, and `bb` is only asked for a minor bump.
- **Inconsistency:** when `aa` removes event `aa.observed` and `bb` drops its foreign rule, `bb` is charged breaking and a minor bump is refused. The same kind of forced withdrawal gets opposite answers.
- **Smallest fix:** move the contributor loop above the `after is None` check. `_endpoint_contribution` already returns empty sets when the edge is missing.
- **Alternative:** if forced withdrawals are meant to be exempt, exempt the rule path too and say so in the record.

### 3. LOW: "identical rule transfer needs no replay" is false when writes overlap
- **Where:** `pack_versioning.py:703-723`, the test at `tests/unit/test_contributor_version_impact.py:310`, and the "Implemented distinction" paragraph in the review record.
- **Witness:** `aa` and `bb` both set `Thing.label` on `aa.observed`; `aa`'s rule moves into `bb` after `bb`'s own rule.
- **Result:** the plan is `additive` with no replay and no problems, but the stored label for the same event changes from `N` to `L`. Last writer wins in pack order.
- **Origin:** the sorted comparison is in base, so S5 did not introduce it. S5 does now assert it as a property.
- **Smallest fix:** scope the test name and record to non-overlapping writes and log order sensitivity as a residual. A stronger fix is to treat a changed ordered rule list with an equal multiset as `mapping`.

### 4. LOW: withdrawing an extension the owner already declares still demands a major
- **Witness:** `cc` extends `RELATES` with `aa:Thing`, which `aa` itself declares, then removes it with a minor bump. Result: `cc` needs a major.
- **Assessment:** no bundle can observe a difference, since `cc` requires `aa`. It errs on the strict side and the administrative override covers it. Accept it or exempt owner-declared endpoints; either way, record the decision.

### 5. LOW: duplicated reasons
- **Where:** `pack_versioning.py:103`, `:327-328` and `:345-346`.
- **Result:** witness 1 prints "endpoints removed" three times, once per actor, plus three "contribution withdrawn" lines. These flow into refusal messages and the status payload.
- **Fix:** append the reason once and loop only over `pack_changes`.

## What holds
- **Rule aggregation:** the event-level comparison is the same multiset as base, so replay and rebuild outcomes are unchanged. Aggregate breaking always implies a breaking contributor.
- **S1 static-field gate:** the Counter logic is preserved per contributor and in aggregate.
- **Other owners:** link defaults, edge properties and admission changes still charge the owning pack.
- **Reconcile:** it only reads `kind`, `version_problems` and `replay_event_types`, so contributor compatibility is not a new breaking gate.
- **Status consumers:** `as_dict` gains one key; I found no strict consumer of it in `src`.

## On the extra machinery
`pack_changes` has no consumer other than `_check_versions` and `as_dict`, so folding the new axis into it would work mechanically. I would still keep it separate: status would otherwise show `kind: additive` next to `pack_changes: {bb: breaking}`, which reads as a rebuild requirement. `admission_changes` is the precedent.

## Evidence limits
- Memory backend and Python 3.14 only; no broad suite run by me.
- The transfer test passes only because the old owner rule was rewritten with qualified refs. Changing `Other` to `bb:Other` in a pack's own rule classifies as breaking; this is in base and errs strict.
- No tests cover edge removal with extensions, provenance, or one-sided (source-only or target-only) deltas.
- `focused-final.txt` records 151 passed, one behind the current 152.
- The review record is not hash-pinned in the manifest.
