# S3 (issue 36) round 2 of 2: PASS for bounded S3

F1, F2 and F3 are corrected, and I found no material adjacent regression. No required findings remain. This verdict covers S3 only; parent S2 acceptance and its low findings stay open and are not closed here.

## Source binding
- HEAD is `33e809e`, and the worktree was clean before and after my runs.
- All 16 manifest hashes match the files on disk (recomputed with SHA-256).
- The round 1 report is present at the manifest hash.
- Each `round2-*.txt` log references HEAD, and `round2-verification.json` records exit code 0 and unchanged sources for all six checks.
- Of those six checks I reran only the focused file: `64 passed in 1.03s`.

## Disposition of round 1 findings

| Finding | Status | Basis |
|---|---|---|
| F1 changed mapping rewrites without replay | Corrected | Executed, memory and Spanner fake |
| F2 exact redelivery refused after additive bump | Corrected | Executed, memory and Spanner fake |
| F3 extraction bypasses ordered path | Corrected | Executed (validation), inspected (write path) |
| F4 comma fractions | Corrected | Suite test only; `write_order.py:35` inspected |
| F5 Neo4j lock litter and recovery create | Corrected by inspection | Never executed |

**F1 and F2 mechanism (`write_order.py:144-155`, `pack_projection.py:484-512`):** the claim per record and authority value now holds the whole-plan semantic digest. The comparison happens before any ordinal logic, so shifted ordinals no longer matter.

**Executed probes beyond the suite** (`/tmp/s3probe2/`, identical results on memory and the Spanner adapter over the transaction fake):
- **Partial write, then additive bump:** with nodes and states committed and edges not, the retry under 1.1.0 skipped the record and wrote the missing edge (`description == "newer"`). A second retry returned 0.
- **Later traffic after the no-op:** seq 3 applied under the new bundle. Seq 2 retries, and a first-arrival seq 1, changed nothing.
- **Edge-only and transition-only mapping changes without replay:** both raised `write_order_changed_effect_without_explicit_replay`; the stored record and link were unchanged.
- **New mapped field absent from the payload:** an exact retry is a no-op, not a false refusal.
- **One flush of `[seq2, seq1, seq2]`:** ends at `newer` / `succeeded`.

**F3 (`ontology.py:1360-1372`):**
- **Refused:** `derived_proposals` naming `Payment`.
- **Accepted:** `never_propose` naming `Payment`, and `propose` naming the unordered `Account`.
- **Consistency:** the edge check mirrors `allows` (`ontology.py:737`), including the pack wildcard.
- **Ordered target:** an extraction edge from an unordered source into an ordered target is accepted. By inspection it cannot recreate the defect, because endpoints only resolve to local proposals or known ids, so no node of an ordered type is created.

**Recovery refusal (`worker/relationship_recovery.py:263-275`), executed on memory only:**
- **Setup:** a pending required `POSTED_TO` link, plus an injected surviving edge clock with no edge.
- **Result:** `finish()` returned `complete=False, blocking=1` on two consecutive attempts.
- **State:** the intent status was `write_order_edge_missing_but_clock_survives`, and no edge was created.

**Inspected only:**
- **Atomicity:** nodes and states for a flush go through one `apply_ordered_mutations` call (`worker/pack_projection.py:218-224`), and Spanner runs it in one transaction (`spanner/graph.py:754`). A committed claim therefore cannot hide an unapplied state change.
- **Neo4j locks:** `_ordered_tx` clears locks on untouched existing rows and deletes empty shells (`neo4j/pack_graph.py:247-258`).
- **Neo4j recovery create:** it passes `newly_created`, so a surviving clock raises inside the transaction.
- **Pending pointers:** `merge_relationship_intent` relaxes only `bundle` and `event_generation`, and only when `ordered_effect_digest` is set. Unordered effects keep the parent behaviour.

## Residuals (all Low, none required)
1. **Re-keyed mapping (executed):** if a changed mapping lands the same event entirely on records with no prior claim, it is accepted without replay. My probe created `Payment:A1` beside an untouched `Payment:P1`. No protected field regressed, so the ordering contract holds. The record should state this limit.
2. **Missing test:** my grep found no test of the worker's ordered-refusal `except` branch. My probe is the only execution of it, and only on memory. A memory and Spanner-fake test would close this.
3. **Stale version stamp (executed):** after a no-op retry or unchanged replay, the ordered node keeps its earlier `ontology_version`. No code under `src/` reads that stamp.
4. **Stub behaviour change (inspected):** plain stubs are now create-only for unordered types too, on every backend. A reference no longer refreshes `node_type` or `ontology_version` on an existing record. The supplied 1316-case regression log passes.
5. **Storage-loss corners (inspected):** if a claim survives while both the record and its clock are gone, a combined node-and-edge call could record an edge receipt without the edge. The worker never makes that call shape. The Neo4j recovery create has the analogous corner.
6. **Not supplied or not run:**
   - Real Neo4j, Spanner or Redis.
   - CI on Python 3.12.
   - Regression, conformance, mypy and lint, which I did not rerun.
   - Live reasoning or human acceptance.
   - Automatic repair of reversed guarded chains, which the record now states as a limit.

No repo file was edited; probes live only in `/tmp/s3probe2/`.
