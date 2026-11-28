# S3 (ARCH-2-001, issue 36) independent review, round 1 of 2: REVISE

The core ordering property held in everything I ran: no older event regressed a newer scalar, state or link value. REVISE is for the same-event replay guard, which is wrong in both directions once the pack version changes. This verdict covers S3 only; the parent S2 gate stays at REVISE and is not closed here.

## Source binding
- HEAD is `f49086c`, the worktree is clean, and all 14 manifest hashes match the files on disk (recomputed with `shasum -a 256`).
- The three final logs show completion: regression `1301 passed, 2 deselected`, conformance `111 passed, 222 deselected`, mypy `no issues found in 12 source files`.
- Those logs are tied to HEAD only by filename and the manifest; they embed no commit or hash themselves.

## Findings

### F1 (Medium, executed): a changed mapping can rewrite a field without explicit replay
- **Where:** `domain/write_order.py:173-182` (`permitted`), with ordinals assigned from plan list positions in `domain/pack_projection.py` `_stamp_write_order` (about 441-482).
- **Mechanism:** for the same event at the same authority, the ordinal is compared before the bundle. If the new mapping shifts the plan index upward, the `write_order_changed_effect_without_explicit_replay` check is never reached and the write proceeds.
- **Repro (memory):** apply the seq 2 event under `PACK` with the transition removed. Bump to 1.1.0, insert an `Account` upsert ahead of the `Payment` upsert, and change the `description` rule. A plain `apply_plan` of the same event is accepted and the stored `description` becomes `"reinterpreted rule"`.
- **Why the suite misses it:** `test_explicit_mapping_replay_...` (test file line 496) only covers the unshifted-ordinal case. With the transition kept, my first attempt was refused only because the state ordinal happened not to move.
- **Contract broken:** the doc says a contradictory effect from the same event is refused and reinterpretation needs a separately authorised replay.

### F2 (Medium, executed): an exact redelivery is refused after an additive pack bump
- **Where:** the same branch, `write_order.py:179-182`; the bundle is `registry.version` (`pack_projection.py:418`).
- **Mechanism:** a duplicate must match on bundle as well as mutation, so any version change turns an identical redelivery into an error.
- **Repro (memory):** apply the seq 1 event under 1.0.0. Bump to 1.0.1 by adding one unrelated `Account` property; `classify_change` reports `additive`. Re-applying the same event raises `write_order_changed_effect_without_explicit_replay`.
- **Impact:** an event applied but not acknowledged before a deploy is dead-lettered on redelivery through `worker/projection.py:280-299`, although it is fully applied. It fails closed, but the report is false, and the doc says exact repeated effects are no-ops.

**Smallest correction for F1 and F2 (one change in `permitted`):**
1. When event and authority match but the bundle differs and `reinterpret` is false, do not compare ordinals across bundles.
2. Treat an equal mutation digest as a duplicate no-op and a different digest as the refusal.
3. Reduce each event's effects to the final one per record and field before comparing, so multi-effect events do not refuse themselves.
4. If owner writes carry a version-stamped bookkeeping property such as `ontology_version` (I did not confirm this), exclude it from the comparison.

**Verification condition, on memory and the Spanner transaction fake:**
- The F2 repro returns normally, counts duplicates, and leaves stored rows and clocks unchanged.
- The F1 repro raises and leaves `description == "newer"`.
- The tests at lines 483 and 496 stay green.
- Add a test for the shifted-ordinal case with no transition in the rule.

### F3 (Medium, inspected only): extraction proposals bypass the ordered path
- **Where:** `domain/pack_extraction.py:493` and `:555` build `NodeWrite`/`EdgeWrite` with no order or placeholder flag, so they take the plain path at `worker/pack_projection.py:229` and `:249`. Nothing in `domain/ontology.py` stops a pack combining `ordering` with an extraction target.
- **Mechanism:** a proposal can create an unclocked real record of an ordered type. Every later owner event then hits `write_order_existing_data_needs_explicit_rebuild` (`write_order.py:136-137`), and a rebuild would recreate the same state.
- **Correction:** reject that combination at registry validation, or stamp such writes as placeholders.
- **Verification:** a pack test showing the refusal, or a stub-then-owner test on the extraction path.

### F4 (Low, executed): comma fractions bypass the microsecond limit
- **Where:** `write_order.py:35-37`; the precision check only matches `.`.
- **Repro:** `2026-01-01T00:00:00,1234567Z` and `...,1234568Z` are both accepted and truncated to `.123456`, while the `.` form is refused.
- **Impact:** two distinct instants collapse into an equal-authority conflict instead of the documented precision refusal. It fails closed.
- **Correction:** match `[.,](\d+)`, and add both comma forms to the invalid-timestamp parameters.

### F5 (Low, Neo4j by inspection only, never executed)
- **Lock litter:** `_ordered_tx` in `adapters/neo4j/pack_graph.py` (about 161-172) merges and increments `_write_lock` on every clock and claim key, but only clears it on rows `decide` changed (about 206-211). An edge skipped for a missing endpoint leaves an empty `ProjectionOrder` row with a growing counter.
- **Recovery create path:** at about 570-581 the plain create writes all edge properties before the ordered decision. If a clock survives a deleted edge, properties the clock would reject stay on the edge.

## Required behaviours that held

**Executed on memory:**
- All 49 focused cases pass on my run (`49 passed in 0.94s`), including the Spanner adapter cases over the transaction fake.
- **Deferred links (S2/S3 integration):** four delivery orders with disjoint fields kept both fields. Two orders writing the same field kept `"newer"`.
- **Fresh rebuild with a guarded transition out of ledger order:** at batch sizes 1 and 50 the report gives `projection_complete=False` and lists the dead-lettered position. The guard is not bypassed.
- **Stubs:** stub then owner then stale event then stub, and owner then stub then stale event, both end at `newer`/`succeeded`.
- **Reserved rows:** `ProjectionOrder` rows do not appear in memory `get_graph_stats`.

**Inspected:**
- Orphan cleanup is limited to five labels (`adapters/graph_ops.py:134`), so it cannot delete clocks or claims.
- Spanner reads clocks, claims, records and edges and writes them inside one `_transact`, preserving embeddings.
- The explicit replay path sets `reinterpreting=True` (`ontology/versioning.py:215`).
- Unordered writes still take the old plain path.

## Remaining limits
- **Rebuild convergence:** a ledger whose live graph was repaired by an explicit retry will not rebuild to the same state without repeating that retry. The same applies to a reversed guarded chain inside one batch. Both are reported honestly, but the doc does not state this.
- **Not examined:** how Spanner and Neo4j stats, migration comparison and export treat `ProjectionOrder` rows; errors raised by the ordered decision inside `settle_relationship_intent`; a record deleted while its clock survives.
- **Not run:** any real backend, CI on Python 3.12, live reasoning or human acceptance. My only evidence beyond the supplied logs is the 49-case run and the probes in `/tmp/s3probe/`; no repo file was edited.
