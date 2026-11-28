## Verdict: REVISE

The core mechanism is sound and delivers real recovery, not just reporting, for exact endpoints. Four semantic gaps would let the implementation pass its own tests while still producing order-dependent or falsely complete graphs. All four have small corrections, and none needs a new policy approval.

Everything below is from source at 9013a83 plus one memory-only probe (20 rebuilds, nothing written to disk). I make no claim about real Neo4j or Spanner behaviour.

## What holds

- **Failure is real and correctly diagnosed.** `upsert_edges` drops writes with a missing endpoint and returns only a count (`adapters/graph_ops.py:668-696`, `adapters/neo4j/pack_graph.py:155-158`). `ProjectionConsumer` then ACKs (`worker/projection.py:196-199`), so retry can never see the skipped link.
- **Storage reuse is justified.** `OntologyState` is already an internal node written through `PackGraph`, with its own Neo4j constraint (`ontology/versioning.py:48-49`, `adapters/neo4j/ontology_schema.py:33`). `ORPHAN_LABELS` is a fixed list, so orphan cleanup will not delete recovery rows.
- **Tenant isolation holds by construction.** Rows live in the tenant's own fenced database (`adapters/spanner/graph.py:159-213`).
- **Create-if-absent preserves reviewed edges.** `link_status` lives on the same (source, type, target) identity.
- **Relationship-only retry avoids the node/state overwrite problem.**

## Blockers

### B1. Required fan-out has no implementable meaning as written (item 7)

Probe, `to_each: {type: Account, match: {industry: $.industry}}`, with two accounts matching:

| Ledger order | Batch 1 | Batch 10 |
|---|---|---|
| A1, C, A2 | `[a1]` | `[a1, a2]` |
| C, A1, A2 | `[]` | `[a1, a2]` |
| A1, A2, C | `[a1, a2]` | `[a1, a2]` |

- In the first row the original lookup is non-empty, so an "empty lookup" trigger creates no intent and a2 is never recovered.
- "Stay eligible for rechecks" either makes every required lookup a permanent standing row, or resolves at first match and stays order-dependent.
- Match fields are mutable and nothing retracts a link, so a repeat build and a fresh build can still differ.

**Correction:** in S2, `required: true` is accepted only where the match covers the target type's full key by equality, with no prefix and no `to_latest`. That is at most one target with a derivable, immutable identity, and it is exactly the matrix's lookup form. Plan it as an exact-reference intent that waits for that node and never re-queries. Reject `required: true` on any other lookup at pack validation, with a named reason. Optional lookups stay untouched.

### B2. `to_latest` cannot be recovered by re-selection (item 8 leaves this open)

Probe, `to_latest` on Account, which orders by the `updated_at` fallback:

| Ledger order | Batch 1 | Batch 10 |
|---|---|---|
| A1, C, A1-updated | `[a1]` | `[]` |
| C, A1, A2 | `[]` | `[a1]` |
| A1, A1-updated, C (late) | `[]` | `[]` |

The order field is the node's last-write time, so a candidate leaves the `not_after` window as soon as it is touched again. A late re-query answers from current state, not as-of-event state, so the result depends on sweep timing. A required row here could wait forever at batch 10 while batch 1 completes.

**Correction:**
- Close the "assess a rebuild-final phase" question as not needed in S2.
- Evaluate `to_latest` selection exactly once, at original processing.
- Reject `required` with `to_latest` at validation (covered by B1).
- Where a lookup resolved candidates but the exact known end was missing, pin the candidate references chosen then and wait only for the known node. Apply the same rule to optional non-key lookups.
- If the original evaluation hit `lookup_limit`, record `ambiguous_or_truncated_lookup` and block completeness.

### B3. Completeness is ambiguous and can make rebuild unusable (items 1, 4, 9)

Item 1 defers unflagged exact endpoints; item 4 says "required unresolved rows block completeness". The contract does not say whether an unflagged dangling `node_id` blocks. `rebuild` refuses to reuse an incomplete target (`ontology/rebuild.py:268-272`), so blocking would turn every ledger with one dangling reference into a permanently incomplete target. That changes old meaning for packs that never opted in.

**Correction:**
- Blocking: `required: true` rows still waiting, truncated or unsupported rows, changed authority or bundle, missing source, and any row not examined since the ledger pass ended.
- Non-blocking but counted in `RebuildReport` and recorded state: unflagged exact rows still waiting.
- Rebuild termination: one full pass over the rows after the ledger pass is an exact fixed point, because recovery writes only edges and exact-reference rows depend only on node existence. If the budget ends first, the build is incomplete.

### B4. Create-only recovery reverses property order for the same edge

The normal path is last-in-log-order wins (`SET`). Two deferred events for the same (source, type, target), such as contact added then contact updated, recover as first-applied wins. Source-first and target-first ledgers then give the same edge with different properties, which the "actual properties as oracle" acceptance will catch.

**Correction:** among pending rows for one edge identity, apply only the one with the greatest original log position and mark the rest `superseded`. An edge that already exists is always kept, with terminal status `existing_relationship_kept`.

### B5. Status changes on non-definitive answers

Nothing stops a fenced-out or degraded worker from stamping rows `changed_authority` or `missing_source`.

**Correction:** `RuntimeFencedError` and transient errors propagate and leave the row byte-identical. Only a successful read with a definitive answer may change status. Redelivery of the original event upserts the row create-if-absent, so a resolved row never regresses to waiting.

## Smaller pins (not blockers, but put them in the contract)

- **Skip detection:** use existing `get_nodes` over the flush's edge endpoints after node upserts, then persist intents, then write edges, then ACK. Do not change the `upsert_edges` signature.
- **Atomic primitive:** a single create-if-absent operation that checks endpoints in the same atomic unit and returns created, exists or endpoint-missing per write. The generic path is read-then-write across awaits (`graph_ops.py:684-695`). Leave the extraction caller (`domain/pack_extraction.py:555`) unchanged.
- **Row identity:** hash of event ID, bundle digest, edge type, source reference and target reference, not the effect index.
- **Row content:** store the effect digest and references only. Re-derive properties from the re-fetched document, which item 5 already requires. Item 2 currently also stores property values, duplicating payload data that outlives event retention.
- **Removals:** on a create path they are vacuous, so drop them instead of raising an "unsupported" outcome that would block completeness.
- **Fairness across restart:** order the scan by least recently checked then key, or persist the cursor. An in-process rotating cursor starves rows behind page one.
- **Unresolvable inputs on required rules:** a missing match operand (`domain/pack_projection.py:652-653`) or malformed `node_id` (`:529-530`) gets a terminal blocking status. Unflagged rules keep today's silent drop.
- **Bundle change:** re-pin a row when the effect re-derived under the current bundle has the same digest; otherwise `changed_bundle`. Without this, every additive in-place upgrade strands all waiting rows.
- **Visibility:** exclude the internal label from migration compare and graph stats, or report it separately.

## Disclosure for you

The first `to_latest` row is an existing defect with every endpoint present: the edge vanishes at batch 10 and rebuild still reports complete. The first `to_each` row is the same class. Recovery cannot fix either, and the goal's "batch size" wording arguably covers them. S2 must record both witnesses and must not claim batch invariance for non-key or latest lookups. Whether they belong in S2 or S3 is your call.

## Acceptance conditions for the implementation review

1. The 18-case matrix is rerun with recovery. Node-ID and key-complete lookup forms give identical edge keys and properties across both orders, batches 1, 2 and large, and fresh, repeat and fresh-control runs. Keyed results are unchanged.
2. Pack validation rejects `required` on non-key, prefix and `to_latest` lookups. Existing pack digests are unchanged with the default omitted.
3. Same-edge test: two deferred events with different properties end with the later event's properties in both ledger orders.
4. A reviewed edge (`link_status` rejected or confirmed) and newer node or state values are byte-identical before and after recovery.
5. A ledger with an unflagged dangling `node_id` reaches `rebuild_complete` true with a reported waiting count. The same ledger with `required: true` is incomplete, and that persists in recorded state.
6. Restart: a new consumer over the same store recovers with no new events. Crash before ACK and crash after edge write give one edge and one row.
7. Injected fence and transient errors leave rows unchanged. A concurrent double sweep creates one edge.
8. With N permanently absent targets beyond one page, a later satisfiable row recovers within a bounded number of sweeps, including after restart.
9. The B1 and B2 probe ledgers are added as characterization, showing the unsupported forms are refused or explicit.
10. The memory conformance suite passes. Neo4j and Spanner are claimed only if actually run.

The second and final review should receive the diff, the rerun matrix, the cases above and the revised contract.
