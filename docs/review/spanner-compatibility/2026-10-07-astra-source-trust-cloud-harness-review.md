# Authenticated source trust cloud harness review

2026-10-07 — Astra low, source-only pre-cloud review. No tests/cloud executed.

**Verdict: P2 cancellation-result correction required before execution.**

`verify_source_trust` in `scripts/engram_spanner_source_trust_cases.py` directly returns `await_settled(...)` without the explicit cancellation-failure checkpoint used by the acceptance and interpretation wrappers. Cancellation can allow the shielded case to finish and clean up, then propagate CancelledError past the outer harness's `except Exception`, leaving only successful recorded checks. Catch CancelledError after settlement, append a passed:false cancellation check, persist, and rethrow. Keep settlement intact. Add or reuse a focused wrapper regression establishing cancellation cannot leave a green result.

The other reviewed safety boundaries are consistent with this bounded experiment. Initial authority is the hard-coded epoch-6 predecessor corroborated by retained evidence and live equality, not newly adopted observed identity. Freeze and activation use exact transactional CAS; activation requires all seven application tables empty within that transaction. Consecutive epochs, unchanged owner coordinates and reconstructed target binding are enforced. All intended owners/configuration/cleanup keys are durable before effects.

Cleanup freezes only the known experimental owner, checks all present primary keys are within the registered set in the same transaction, and deletes only those keys. Unexpected owner or unexpected rows refuse. Restoration requires empty tables and advances to the predefined latest-core epoch-8 binding; preactivation recovery uses the separately predefined core epoch-7 intent. No source database or DDL mutation path was identified.

Fixture identities agree with Change composite keys and Decision content hashes. Four synthetic normalized events feed real ledger/subscriptions and direct projection/extraction consumer methods, with exactly two deterministic model answers. Graph trust and the four exact DERIVED_FROM edges are asserted against authoritative accepted sources; payload/model agent-name spoofing cannot be counted as authority. This does not run consumer loops/process factories or native webhook translation, and does not grant historical compatibility. The protected-target concurrency assumption remains the existing experiment lock and exclusive reserved-target use.

Final verdict after correction still requires registered preflight evidence. No cloud success, production activation, general retrieval evidence, or full-feature completion is established here.

## Cancellation correction recheck

**P2 resolved in source.** The source-trust wrapper now waits for settlement, records an explicit failed cancellation checkpoint, persists and rethrows CancelledError. The parameterized interpretation/source-trust wrapper regression asserts cleanup precedes persistence and the failed check is present. Existing SDK-thread settlement behavior is unchanged.

**Approve the bounded harness source, subject to successful registered preflight completion.** No remaining source blocker identified; local run03 was reported in progress and no terminal result is assumed here. No tests/cloud executed by reviewer. All original activation, ownership, exact-cleanup and scope restrictions remain applicable.

## Recorded bounded cloud evidence

Read-only inspection of `20261007-cloud-authenticated-source-trust-01` observations, case attempt and schema evidence supports the stated bounded result: **12/12 checks passed**. Four receipts alternate two authenticated source identities (four events, not four distinct producers). The stored Change pair and extracted Decision pair each contain trusted/untrusted outputs matching those receipts; four exact DERIVED_FROM links identify the accepted Events. The model was the deterministic stub, and consumer methods ran directly rather than through worker loops/process factories.

Cleanup records removal of **4 Events, 8 graph nodes, 4 graph edges, 2 groups and 32 cursors**, with no remaining deliveries/DLQ. All seven application tables return to their empty baseline. The same owner coordinates are active at epoch **8**, with the predefined latest-core digest `sha256:f57ffb649f7ab0197d21f45b9397203887f8cb103e32efd784f4e52ce4c3f7b1`; schema and source preservation checks pass. No discrepancy affecting the bounded claims was identified.

Local `20261007-local-empty-target-activation-03` provides the separately recorded helper/preflight result. **Final verdict: approve the tested bounded harness and restoration evidence.** This is synthetic normalized PDLC source-trust evidence, not whole-issue #5 completion, native webhook acceptance, historical compatibility, production activation, or general Spanner compatibility closure. Reviewer made no further cloud calls or test runs.
