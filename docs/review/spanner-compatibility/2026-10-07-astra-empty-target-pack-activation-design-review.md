# Empty reserved target: bounded pack activation

2026-10-07. Read-only source/evidence review. No runtime edits, tests or cloud calls. This is an authorized disposable-target experiment design, not production activation or a historical replay grant.

## Verified starting evidence

`runs/20261007-cloud-writer-admission-01/schema-evidence.json` records `control_after` as tenant `compat-control`, binding `compat-control-binding`, database `projects/portiq-mvp/instances/engram-experiment/databases/engram-compat-target`, epoch **6**, state **active**, digest **sha256:7c4c2c9cb07539c5841b80b5cb5adfcb9b14d23f350258eb29f1c00325134b6d**. Its `after_rows` records zero rows in Events, GraphNodes, GraphEdges, ConsumerGroups, ConsumerCursors, ConsumerDeliveries and ConsumerDeadLetters. These are retained observations, not proof the target is still unchanged now.

`operator_transition` in `scripts/engram_spanner_tenant_control_cases.py:42` already performs full-row CAS and prevents frozen→active without advancing epoch, but cannot change the digest. Extend the **harness-only operator mechanism** with one bounded empty-target activation function. Do not create a production activation API just to run this experiment; public tenant startup and populated-history activation remain disabled.

## Minimal operator contract

```text
activate_empty_target(database, expected_frozen_owner, target_binding)
  -> exact intended active owner
```

Require the exact reserved database resource, unchanged tenant/database/binding identity, expected state=frozen, target epoch=expected epoch+1, and target digest computed from the reviewed immutable settings/bundle/engine revision. Use explicit validation exceptions, not Python asserts that disappear under optimization. The transaction reads the full TenantControl row, compares it to the persisted expected row, checks all seven application tables are empty using transaction-local reads, then updates only epoch/digest/state. No adoption, DDL, deletes or payload rewrites occur in this function.

The empty-table reads and control update must be in the same read-write transaction; a before-call snapshot is insufficient. A concurrent fenced writer either orders before freeze and causes the empty check to refuse, or is rejected by frozen/new authority. Unexpected rows—including receipts, dedup tombstones, subscription checkpoints, OntologyState or other graph metadata—refuse activation. Do not exempt “just metadata” to bypass historical compatibility.

The operator is privileged only for this recorded empty-target transition. Its authority is the exact pinned expected owner and intended successor, never whatever a fresh read happens to return. Normal processing fences correctly refuse frozen state and must not be weakened to implement the operator action.

## Harness sequence

1. Register the run before cloud calls. Durably record the retained-evidence path/hash, pinned epoch-6 owner, exact experimental and restoration settings snapshots, calculated digests, planned epoch sequence, source hashes, unchanged DDL fingerprint, fixture ownership manifest and cleanup scope. New `trusted_source_ids` intentionally changes the digest even when empty; calculate both new configurations explicitly. Fail if credentials target anything except the reserved resource.
2. Observe current owner/schema/rows and compare to the pinned expectations. Observation can confirm or reject the plan, never revise its authority. Close/quiesce any known old runtime. Since retained state is empty, a direct CAS active6→frozen6 is sufficient; do not invent a drain of nonexistent accepted work. If it is not empty, stop rather than invoking a production drain/replay policy.
3. Persist the freeze intent before mutation. Then persist the complete `frozen6 → active7` activation intent. Execute the empty-target CAS to select core+PDLC and explicit authenticated trusted producer IDs. Preserve optional memory/user exclusion. After commit, read exact control/schema evidence and construct the bound runtime only from the intended epoch-7 binding.
4. Run bounded projection/extraction trust cases through authenticated admission and verified accepted-record reads. Include trusted/untrusted source IDs using the same misleading agent_id, legacy webhook-like agent_id spoofing, fake receipt injection and provenance evidence. Use existing pinned receipt and read/write/terminal fences. If extraction uses a deterministic model stub, label evidence as real Spanner processing with stubbed model output rather than real LLM acceptance.
5. Stop and join all worker/task/SDK-thread work before cleanup. Persist and CAS active7→frozen7 so late epoch-7 writes cannot repopulate the target. Cleanup uses a separate explicit operator transaction that checks the exact frozen experiment owner and deletes **only registered experiment-owned keys**. It is not ordinary processing allowed in frozen state.
6. Verify all seven tables are empty again. Persist the restoration intent, then call the same empty-target helper for frozen7→active8 using **latest core-only configuration**, including its new empty trusted_source_ids field. Preserve full tenant/database/binding identity; retain the increased epoch. Restoration means a newly valid core-only binding, not restoring epoch6 or its obsolete digest. Record the final owner, zero-row fingerprints and unchanged DDL/source fingerprints.

Use exact registered successor rows if the experiment has an explicitly recorded additional epoch transition; never calculate recovery authority by incrementing a newly observed epoch. Prefer the simple 6→7→8 sequence above.

## Exact fixture cleanup and recovery

Register Event IDs, graph node/edge keys, consumer group/cursor/delivery/dead-letter keys, and any fixed-key OntologyState/evaluation rows the factory/reconcile path creates. Keys whose values derive from extraction output must be computed/registered before applying that output or captured through a bounded write ledger. A globally empty starting database is not permission for later blanket deletes. Validate ownership/expected values for fixed shared keys; unexpected rows halt cleanup/restoration. Preserve source database and schema entirely; disable archives for the experiment or give them a separately exact owned cleanup plan.

Persist mutation intent with atomic replace/fsync before each control change or cleanup, including exact expected/intended rows and keys. SDK transaction callbacks can retry; keep them deterministic with no evidence-file side effects inside callbacks. On timeout/cancellation/uncertain commit, join outstanding SDK work and inspect the exact known intent: expected state means the same CAS can be retried, intended state means completion can be recorded after verification, any third state means stop unresolved. Never adopt that third state, allocate a new epoch automatically or launch compensating cleanup against it.

If activation committed and fixtures exist, recovery resumes cleanup under the known experiment binding; it must not try to activate another digest over those rows. If cleanup partially committed across bounded chunks, replay only the recorded exact-key deletions with expected-owner checks. If uncertainty cannot be resolved, retain the last known intent and leave the target fenced rather than claiming restoration. Cleanup failure must remain visible even when test assertions also failed.

## Required local and real evidence

Local cases: stale owner; wrong resource/identity; non-frozen predecessor; nonconsecutive epoch; unexpected row in each of seven tables; concurrent insert/control retry; exact completed-intent recovery versus unknown state; cleanup unexpected keys/owner; cancellation with outstanding SDK work; and restoration digest differing from the legacy digest. Assert zero DDL, no broad deletion and unchanged schema.

Real run records each intent/observed owner, exact trust outputs and accepted provenance, stale-runtime refusals, fixture keys, successful empty-state restoration at the monotonic successor epoch and unchanged source/schema. This proves a controlled empty-target experiment only. It establishes no policy for populated pack activation, retrospective trust changes or cross-version replay.
