# Native Entity ANN fixture review

2026-10-07. Narrow read-only review of the run-owned fixture script and harness verify phase. No tests/cloud executed; no cloud execution approval is inferred from this review.

## Verdict: changes requested

1. **P2 — Removal assertion cannot distinguish a missing removal.** In `scripts/engram_spanner_entity_ann_cases.py`, entity0 is first updated to the opposite query vector and verified absent at threshold 0.99. The following removal merely asserts it remains absent. Skipping the removal write entirely would pass. Restore a near vector and verify visibility before removing, or remove the still-visible entity1. Assert the physical embedding is NULL afterward, and check the expected remaining result. Preserve a separate update assertion.

2. **P2 — Attempt all exact cleanup operations and verify both rows and edges.** The fixture finally block awaits edge deletion before node deletion, so an edge-delete exception skips node cleanup. Its final assertion only checks nodes despite recording that nodes and edges were removed; the enclosing fingerprint also covers GraphNodes only. Attempt edge and node cleanup independently, retain any errors, and verify both owned typed key sets are absent before recording cleanup success. Do not claim preservation/cleanup when an assertion failure prevents the main after-fingerprint from running; record a best-effort post-cleanup fingerprint on that path too.

## Assessed setup

Ownership keys, query and expected vectors are written and fsynced before fixture writes. UUID-scoped typed keys and initial node collision check limit scope; no global reset or unrelated deletion is present. Two perturbed Entity vectors compete against 65 non-Entity vectors equal to the query, including a colliding Event ID. Generated membership and exact Entity-only distance checks establish the intended setup before native top-k assertions. Negative rows deliberately carry canonical-looking Entity IDs, preventing a broad ANN corpus from passing solely through post-query identity filtering. The exact baseline check also detects interference from existing closer Entities rather than silently attributing their absence to the implementation.

Native GraphVectorIndex results, typed Entity→evidence Event seeding, reconstructed adapter behavior and vector updates are checked separately. The graph adapter's fixture writes use the stated small budget; direct SQL negative injection bypasses that budget intentionally and is a bounded 65-row setup, not budget-conformance evidence. Verify requires an already compatible schema and performs no DDL repair. This fixture does not establish full startup, all-flow compatibility, complete mixed-ID Atlas behavior or broader tenant/retrieval acceptance.

## Fixture recheck

Removal finding is resolved: the still-visible second Entity is removed, neither fixture Entity may remain above threshold, and physical embedding NULL is asserted. Cleanup now independently attempts both typed deletes and retains errors; whole-edge-table equality adds preservation evidence.

**One concrete P2 remains before execution:** the new cleanup verification calls `graph._edges(src_keys=..., dst_keys=...)`, but `SpannerGraphStore._edges` accepts `sources` and `targets` lists. This always raises TypeError after deletions, preventing edge verification and the successful main fingerprint. Use `sources=event_keys, targets=entity_keys`. No tests/cloud executed during this recheck; approval remains pending this correction.

## Final harness disposition

Read-only recheck confirms the remaining cleanup call now uses the actual `sources`/`targets` signature. Both owned deletion attempts execute independently, node and edge absence is checked, and the whole-edge snapshot comparison verifies preservation. The removal check targets the still-visible second Entity and verifies its physical embedding is NULL. The main harness additionally attempts a node fingerprint in finally after a failed phase that has no after-hash, recording failure if preservation cannot be established.

**All reported fixture blockers resolved; approve the narrow fixture harness for separately authorized tracked execution.** No tests/cloud executed by this reviewer. This approves the setup/assertion/cleanup implementation only; actual ANN behavior and successful cleanup still require recorded run evidence.

## API startup phase addendum

2026-10-07. Read-only inspection of the new startup phase, helper and referenced process owner; no tests/cloud executed. **Approve the narrow startup harness implementation; no blocking finding identified.**

Two API processes run serially with independent process owners/PIDs. Each must return healthy status and explicit Spanner event-log/graph backend health, while its owned child remains alive. Finally cleanup stops the child, escalates to kill after bounded waits, closes its HTTP client and preserves per-launch logs/receipts before filenames are reused. The harness bounds the overall phase and compares graph-node fingerprints and physical DDL/readiness afterward, including best-effort node fingerprinting following a failed phase.

Run registration precedes cloud calls; runtime Python/YAML and referenced bootstrap/harness sources are hashed. The helper explicitly selects token authentication and labels the scripted-provider bootstrap accurately. No worker launch, ingestion request or global reset occurs in this phase. Ordinary consumer metadata writes are disclosed. This is approval of the harness, not recorded proof of successful startups, ADC authentication, worker restart, ANN behavior or platform-wide compatibility. Node fingerprints cover GraphNodes; they must not be reported as proof of zero writes across the entire database.

## Bounded bulk phase addendum

2026-10-07. Read-only inspection of `verify_entity_bulk`, its harness phase and transaction callback instrumentation. **Approve this narrow bulk harness; no blocking finding identified.** No tests/cloud executed by this reviewer.

Six UUID-owned typed Entity keys and original fixture values are persisted/fsynced before writes. The phase requires target readiness and the retained legacy vector index, then performs adapter inserts and vector replacements under mutation/byte estimates of 70/100,000. It verifies unchanged retained text, canonical IDs, updated JSON/physical vectors and generated membership. Callback observations reset for each SDK retry and are appended only after the transaction call succeeds, so failed/retried callbacks are not counted as separate successful commits. Assertions require the expected two-row batches and exact ordered keys for each write phase.

Finally restores original adapter methods, deletes only owned nodes and verifies absence; enclosing fingerprints check pre-existing GraphNodes preservation, including the failure path. The resulting evidence demonstrates bounded estimated-cost chunking with both indexes present. It does not measure exact service-side vector mutation costs, stress Spanner limits, establish rollback semantics beyond the recorded operations, or prove all storage flows. Bulk does not capture an edge hash; the shared cleanup wording should not be interpreted as evidence of one for this phase.
