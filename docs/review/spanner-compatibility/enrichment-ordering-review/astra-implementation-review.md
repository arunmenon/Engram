# Independent #29 implementation and harness review

2026-10-13. **No-go for the draft cloud reset/run until the harness blockers below are corrected.** No new production correctness blocker found in the six-file annotation/projection diff. This is source review, not live acceptance; tests were inspected, not rerun.

## Source assessment

The implementation adopts the proposed ownership contract: both single/batch projection preserve derived fields via creation defaults; Spanner annotation existence/null-importance selection occurs in its transaction; Neo4j consumes a returned MATCH row and uses coalesce; Memory provides the reference behavior. Worker document reads and annotation writes retry transiently, while optional provider failure remains distinct. Vector storage retries reuse the computed vector within a delivery. No enrichment marker or new scheduler is introduced.

Spanner's transaction reads the existing row before insert_or_update, so concurrent deletion/adjustment participates in conflict detection; ordinary missing targets fail before a mutation. Existing non-null importance is omitted from the patch, including zero. Add a narrow SDK transaction test for this override (missing target, null versus zero/adjusted importance, embedding and unrelated-property preservation); the six new tests currently exercise Memory only. Also add the missing-ledger-document stop/recovery local regression, since that changed path is not covered by the draft cloud scenarios.

## Blocking harness findings

1. **Pending identity is not checked.** `scripts/engram_enrichment_ordering_demo.py::pending(eid)` ignores its argument and returns any enrichment delivery counts. EN01/02/07 can therefore accept a different pending delivery. Assert the exact admitted position/event identity and enrichment group, and no DLQ for that event while waiting. Save those observations explicitly.

2. **EN04 can introduce an unrelated self-FOLLOWS edge unnoticed.** It reuses the stopped projection worker with its session cache populated. `worker/projection.py::_previous_event` returns the cached Event itself; `domain/projection.py::project_event` adds FOLLOWS whenever sessions agree, without a distinct-ID check. The harness audits node fields and ledger count only. Use a newly constructed real worker for the scoped persisted-state replay and verify exact edges; separately disclose/file the cached replay defect rather than claim all duplicate projection semantics are fixed by #29. Do not add a hidden graph repair.

3. **Public and physical-vector oracles are incomplete.** `verify()` checks only HTTP node presence. Assert returned keywords, importance and owner/session against submitted fixtures, and check response truncation/capacity where relevant. `snapshot()` reads GraphNodes.props, not the dedicated embedding column used by vector search. Check both exact JSON vector and physical 384-vector via an independent read. Do not require exposing vectors in the public API if its contract intentionally omits them.

4. **Ownership/replay proof is weaker than the claim.** EN04 never changes importance from its source hint7 or summary from null, so those equality assertions cannot detect stale projection overwrites of changed state. The public retrieval should provide a positively nonzero access count before replay, and the snapshot must assert that fact. Exercise a supported importance-adjustment seam followed by reprojection and duplicate enrichment, expecting the adjusted value; label direct graph-port adjustment as such, not HTTP-produced state. Non-null summary/zero importance preservation can be a clearly separated local/SDK test where no bounded public producer exists.

5. **Final exactness is missing.** Reconstruct exact accepted ledger IDs and projected Event IDs from submitted accepted bodies, check source identity fields and final exact per-event annotations/vector, and verify expected edges. A raw snapshot plus prior per-step presence checks does not establish final completeness. Capture the final acceptance snapshot after healthy quiescence, or explicitly reconcile any final-versus-retained differences.

## Safety and scope

The export/owner-fenced reset machinery is reused. Healthy quiescence acquires the actual consolidation lock across cooperative stop and task joins, matching the previously reviewed #60 workaround. `stop(kind)` shields the task from wait_for cancellation; a timeout fails the run and final cleanup still joins it. Preserve that failure behavior and prohibit further reset on shutdown errors. This does not establish general shutdown safety or handle already detached SDK work.

All five workers are constructed, but observations alone do not invoke User extraction or Memory/PDLC producers. These runs can establish enrichment under five selected configurations, not revalidate those capabilities' full journeys. The external embedding provider is scripted; EN07 injects a transient storage-boundary failure after keywords commit. Keep both labels in accepted evidence. Existing retry-delay and repeated-restart DLQ limits remain accurately stated.

## Pre-cloud recheck addendum

2026-10-13: **Go for the bounded cloud verification run; final acceptance remains pending actual records.** Rechecked the corrected runner and new local test source. Exact group/event pending observations, fresh projection replay, deliberate graph-port importance adjustment to 8, positive access precondition, public annotation/owner checks and nontruncation are now present. The runner quiesces before its final five-ledger/five-Event/no-edge and exact per-event field audit. The same fresh projection worker is launched after replay; it does not create a sixth active consumer. The cached self-FOLLOWS defect remains tracked under #18, outside this fix.

Correction to the original vector recommendation: `_embedding_column` deliberately excludes Event labels. Exact Event JSON vector plus a null physical ANN column is the correct current contract. The revised runner explicitly audits both and makes no Event ANN claim. This corrects my earlier recommendation to expect a physical Event vector.

The added local missing-document test proves re-fetch/recovery, and the SDK transaction fixture exercises current null/0/9 importance without an outside snapshot. These are local boundary tests, not live concurrency proof. Existing healthy quiescence, retained-fingerprint checks and shutdown-error reset prohibition remain required. Keep the frozen EN04 expectation at adjusted importance 8 and label the intentional graph-port mutation. No remaining blocker found in this recheck for starting the run.

## Attempt01 access-metadata disposition

The saved failure is a separate public retrieval side-effect defect: `retrieval/engine.py` selects access-update IDs with `nid.startswith("evt")`, excluding the actual UUID Event IDs. This does not invalidate the earlier ordering/annotation observations, but attempt01 is not a completed acceptance run.

A declared graph read-port `record_access` call (or its `record_event_access` adapter delegate) is an acceptable bounded fixture producer for EN04, alongside the already declared importance adjustment. Verify its exact positive access increment and non-null timestamp, then preserve both through projection and enrichment replay. Keep the API UUID access gap separately tracked under #34, retain failed01 unchanged, and state explicitly that API reads did not produce this access state. This tests #29 field ownership without silently claiming the unrelated API metadata behavior is fixed. No blocker to rerun02 with that disclosed seam and unchanged export/retention safeguards.

## Attempt02 ontology-state disposition

The final-node oracle now explicitly permits exactly five fixture Events plus the one reserved `OntologyState:active` node, checks its registry version and selected pack identities against the bound bundle, and still rejects extra artifacts/edges. This matches the existing ontology versioning contract; it is a bounded oracle correction, not a runtime fix. The physical embedding-column check now expects six null columns. Failed02 must remain preserved and excluded from completed acceptance counts.

The revised EN04 access producer is stronger than the proposed graph-port fixture: authenticated session-context GET returns the Event and the existing positive stored-access assertion proves the side effect before replay. The distinct subgraph UUID-access bug remains #61. No additional blocker found in this final-assertion scan; proceed to03 under the unchanged export/reset safeguards.
