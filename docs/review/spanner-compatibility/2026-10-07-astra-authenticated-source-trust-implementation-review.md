# Authenticated source trust implementation review

2026-10-07 — Astra low, read-only source/evidence review. No tests/cloud executed.

**Verdict: P1 replay composition guard required.** Scope follows the authenticated-source-trust design; no full-feature or production activation approval.

## P1 — bound ledger can replay through a legacy agent-trusting projector

`src/context_graph/ontology/versioning.py:175` requires an accepted-record reader only when the supplied projector already requires provenance. Unlike both worker constructors, it does not reject `event_log.requires_source_provenance is True` paired with a legacy projector. A direct `replay_event_types` call with bound Spanner ledger and legacy PackProjector reads valid accepted content but then derives trust from descriptive `agent_id`, ignoring authenticated source_id. This can create trusted derived nodes/edges for an untrusted producer.

Add the symmetric bound-ledger/legacy-projector refusal before any reads. Test that combination stops with RuntimeFencedError and performs no ledger read or graph mutation. Preserve the current unbound legacy replay path.

## Remaining reviewed behavior

The authoritative accepted-record reader checks control and fetches document/receipt together, validates exact interpretation/content, and returns typed provenance outside JSON with requested order and duplicates preserved. Projector policy checks registry version, typed event/receipt association, exact authority and full normalized fingerprint before planning, including no-rule events. Projection and pack extraction reject bound-ledger/legacy-projector construction; active bound paths verify before graph or model work and use typed predecessor reads.

Authenticated trust uses only the explicitly pinned source-ID allowlist. Empty means untrusted; descriptive agent names and JSON receipt copies cannot grant trust. Policy changes alter binding digest and block old-contract interpretation, while epoch-only advance retains original source classification. Native extraction/consolidation and user-facing provenance explanation are not newly approved by this slice.

The new empty settings field intentionally changes existing binding identity. Existing epoch-6 cloud ownership must not be silently adopted; explicit transition evidence remains separate. Registry/factory policy construction is consistent with that boundary. Local run03 was inspected separately from prior retained failures; no cloud behavior was established by this review.

Recorded run03 currently ends **3 failed, 291 passed, 2 warnings**; therefore this review does not treat its test evidence as green. Resolve and retain a registered rerun alongside the replay guard correction.

## Replay guard recheck

**P1 resolved in source.** `replay_event_types` now rejects a provenance-required bound ledger paired with a legacy projector before any reads. The added regression asserts RuntimeFencedError, no `read_after` call, no graph calls and no transactions. Unbound legacy behavior is preserved.

Run04 is terminal: **2 failed, 293 passed, 2 warnings**. Both remaining failures are the trusted/untrusted parameterizations of `test_pack_extraction_uses_verified_source_not_spoofed_agent`, at the assertion inspecting `write.properties["source_trust"]`. This recheck therefore approves the guard correction but does not mark overall source-trust verification complete. Resolve the failed trust-output assertions and retain a successful registered rerun. No tests/cloud executed by reviewer.

## Final bounded local disposition

Inspected run05: **295 passed, 2 framework warnings**, selected Ruff clean and scoped mypy clean across seven source files. The extraction assertions now inspect create-only node defaults, matching the existing upsert contract. Both producer cases inject a model answer claiming `source_trust=trusted`; the expected untrusted default still follows authenticated provenance for the untrusted producer. Existing-node preservation semantics remain unchanged.

The replay guard and zero-read/write regression remain present. **Final verdict: approve this bounded authenticated source-trust implementation with local evidence; P1 resolved.** Earlier failed runs remain retained. No reviewer tests/cloud actions and no cloud acceptance, full-feature or production activation claim. New settings change the binding digest even with an empty allowlist; the old cloud owner requires a separately reviewed explicit transition, not automatic adoption. User-facing provenance explanation and other declared producer/replay compatibility gates remain pending.
