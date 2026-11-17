# Entity-only ANN implementation review

2026-10-07. Independent read-only review of the narrow #44 implementation against the approved Entity ANN design and budget addendum. No tests, probes or cloud operations executed. Inspected local registered output `20261007-local-entity-ann-01/tests.txt`: **37 passed, 10 deselected**.

## Initial verdict: changes requested; see remediation disposition below

1. **P1 — Pending-operation detection uses the wrong SDK object shape.** `adapters/spanner/entity_index.py:upgrade_entity_index` builds pending names using `op.name` and `not op.done`. The installed SDK's `database.py:1131` delegates to `instance.py:664`; that implementation maps results through `_item_to_operation` and returns `google.api_core.operation.Operation`, not raw protobuf operations. Its `done` is a method and its name is `op.operation.name`. A bound method is truthy, so the current predicate never identifies a pending SDK operation. A retry after timeout can issue duplicate additive DDL while the original operation remains live. Call the SDK method and read the underlying operation name; cover real SDK-shaped operations, including live and completed operations, instead of MagicMock with a boolean `.done`. The timeout path already uses `operation.operation.name` correctly.

2. **P2 — Previous physical embeddings are absent from the transaction budget snapshot.** `adapters/spanner/graph.py:_upsert_nodes`, `_merge_nodes` and `_apply_state_changes` read only label/node_id/props, while `_node_rows` charges old embedding bytes from `previous.props.embedding`. The design explicitly includes historical/directly written physical embeddings that can differ from JSON. A physical vector with no matching JSON embedding will therefore be removed/replaced without charging its old vector/index bytes. This can underestimate the coexistence byte budget precisely for the historical state the migration preserves. Read the previous physical embedding column in these transactional snapshots and pass it independently into cost accounting. Add a byte-dominant fixture with physical embedding present, JSON embedding absent, and a property-only update or removal. Preserve the complete merged-row budget check and splitting behavior.

## Assessed behavior

The new index name preserves legacy coexistence; fresh DDL uses the generated Entity-only membership column and filtered index. The narrow token recognizer preserves literal case, checks supported membership semantics, matches the entire supported index definition, and rejects extra operators, wrong target/distance, ordinary name collisions and missing filter/storage components. Startup reloads physical DDL and checks index readiness; normal existing-database startup does not run repair DDL. The explicit admin planner operates without requiring the new startup handshake, supports valid column-only partial state, and refuses incompatible objects without DROP or rewrites. AlreadyExists handling reloads/revalidates rather than blindly succeeding. Pending-operation handling needs finding 1 fixed before safe retries.

Native ANN forces the filtered index and both membership predicates before distance ordering/top_k. Returned Entity IDs must be nonempty strings equal to the physical node ID; corrupt results are dropped and logged. This can underfill top_k and is not a promise of corrupt-row recall. Explicit mutation columns omit the generated membership column. Budget constants conservatively charge coexistence and old/new mutation work; full merged-row checking and increased delete allowances remain in place. Finding 2 concerns a missing old physical value, not those constants.

The Python admin API exists; an admin CLI remains pending as stated. Local mocked results do not establish real Spanner DDL canonicalization, index readiness/filter behavior, operation execution or actual commit accounting. No broader retrieval or compatibility acceptance is claimed.

## Remediation disposition

Read-only recheck of the two reported findings: **both resolved; approve the narrow Entity-only ANN implementation for local acceptance.**

- P1: pending inspection now invokes SDK `op.done()` and uses `op.operation.name`. The timeout/retry regression uses an actual `google.api_core.operation.Operation` wrapping a protobuf Operation, covering the object-shape defect that previous mocks missed.
- P2: upsert, merge and state-change transactions now read the physical embedding column alongside props and retain it separately in `previous_embeddings`. Final `_node_rows` budget checks count prior JSON properties and prior physical vectors independently. The two-key regression exercises physical vectors absent from JSON and verifies splitting when old-vector costs exceed the combined byte budget, including removal. Conservative replacement mutation allowance remains 34, node-delete allowance 4.

Inspected `20261007-local-entity-ann-02/tests.txt`: **77 passed, 10 deselected**, 2.06 seconds. No tests or cloud operations executed by this reviewer. These dispositions establish neither real Spanner schema/index behavior nor broader compatibility acceptance; explicit admin CLI and cloud acceptance retain their stated separate status.

## Admin harness review

Read-only inspection of `scripts/engram_spanner_entity_ann.py`, with no tests/cloud executed. The harness registers before SDK calls, holds the shared process lock, loads only the established credential assignments and omits the token from its manifest. Inspect performs reads only; upgrade invokes the approved explicit additive API, retains before/after physical graph fingerprints and target handshake evidence, and closes SDK resources. Recorded inspect observations confirm unchanged graph hash; local entity-ann-03 records **79 passed, 10 deselected**. Neither result establishes ANN compatibility.

**Harness disposition: two small corrections requested before the mutation run; underlying runtime approval unchanged.**

- **P2 — Signal failure to the invoking process.** Exceptions and failed fingerprint/cleanup checks are recorded, but main still exits successfully after tracker finish. Emit a nonzero exit after preserving evidence whenever any check fails. This keeps command success consistent with recorded acceptance and prevents automated invocation from treating a timeout or changed graph as success.
- **P2 — Attribute submitted DDL operations even on failure.** `operation_names` currently lists every historical database operation only after both applies succeed. It does not identify this run's submitted operation, and a non-timeout failed apply skips operation capture and post-state inspection entirely. Capture the submitted operation name at submission (preferred), or at least record baseline/after operation sets with attribution limitations and inspect operations/schema in failure cleanup. Preserve pending status without issuing retries. The design requires operation IDs for the migration evidence; a list of unrelated historical IDs is insufficient attribution.

An idempotence check should also assert the second returned DDL plan is empty, rather than marking it passed merely because the second call returned. All these changes concern reliable admin-run evidence, not additional cloud authorization or expanded migration scope.

### Admin harness recheck

Both harness findings are **resolved** by read-only inspection. After persisting evidence and finishing the tracker, any failed check yields exit 1. The upgrade API invokes an optional operation callback immediately after submission and before waiting; the script retains exact submitted names in evidence even when the result raises. The failed-DDL regression verifies callback ordering and preservation. The second apply now explicitly requires an empty DDL plan. Recorded entity-ann-04 output: **80 passed, 10 deselected**, 2.34 seconds; no tests/cloud executed by this reviewer.

**Approve this narrow admin harness for the separately authorized tracked migration.** This is an implementation disposition, not evidence that migration ran or that ANN compatibility passed. Failure evidence identifies the submitted operation for subsequent inspection; it does not assert successful post-migration state after an exception.
