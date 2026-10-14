# Independent bounded tenant-isolation acceptance

2026-10-14. **Accepted for the tested public-dispatcher, separate-database/pack isolation and cooperative freeze/new-epoch restart slice. No remaining blocker found within that scope. This does not close all of #43 or approve a pilot.**

Evidence combines immutable main run `tenant-isolation-1014-03` (184 passing assertions) with the separately recorded `tenant-isolation-1014-restart-01` continuation (12 passing assertions), plus mismatched-owner startup and old-epoch worker refusal records. These are assertions, not196 independent journeys. Both phases show empty shutdown-error lists; the continuation passed after ten actual worker loops processed fresh HTTP-admitted Events and drained normally.

## Independently checked

- Actual public dispatcher, authenticated tenant-bound children, five real consumers per tenant, shared consumer-group names and overlapping Event/session/agent/artifact identities. Distinct Belief/Goal content remains in the corresponding database and public response. User enabled/PDLC disabled on A and PDLC enabled/User disabled on B follow their actual contracts. Public Memory provenance anchors to creation; exact typed evidence still includes lifecycle/confirmation sources. B's artifact provenance identifies the merge source.
- Auth/header/role/cursor/unsupported-route refusal evidence and quiesced no-effect comparisons; foreign-only PR Event positive on B and exclusion on A; independently tenant-scoped admin counts9/12 during the main phase. Held real retrieval returns503 after A freezes, while B remains usable. Both ownership-mismatch startup and obsolete-epoch worker startup fail without recorded application effects.
- All219 continuation source hashes match current files. All main source hashes except the deliberately revised runner match; the archived main runner matches its original frozen hash. The continuation changed harness synchronization/mode, not runtime semantics.
- Both main export digests and continuation predecessor-record digests match. Fresh-process audit reports exact retained owner, schema, full snapshot and all seven table fingerprints. Independently recomputed every application-table fingerprint from the separately saved raw tables and matched retained values.
- Independently compared exact final ledger ID sets and all submitted Event fields, decoding the documented float codec and comparing timestamps as instants. Acceptance tenant/database/binding/epoch matches each phase: A original inputs at51, restart inputs at52; B inputs at6. Checked final distinct Memory content, revision1, Belief count2 and completed Goals.

Final retained A is epoch52:11 Events,37 nodes,151 edges; B is epoch6:14 Events,50 nodes,176 edges. Each has five groups,80 cursor rows and zero pending/DLQ. Retention evidence covers the two explicitly approved targets only.

## Failed attempts and limits

Attempt01's Memory-provenance oracle and attempt02's unsupported A artifact `trace` expectation were harness mistakes, preserved with original runners/results. Main03's initial restart observation failed prematurely because zero lag did not imply projection completion. Both Events existed after its clean drain; the separate continuation used fresh inputs and waited for zero lag, zero pending and expected projected nodes. The original failure remains failed. No artifact repair or rewritten failed result is used for acceptance.

Recorded local validation is2856 passed/13 skipped with the previously identified PDLC evaluation-gate file excluded; runtime typing checks passed. This review did not rerun that broad suite.

Acceptance is representative database-per-tenant behavior under the tested credentials, pack configurations and cooperative lifecycle. It does not establish general pending recovery, draining-mode semantics, SIGKILL recovery, hierarchy authorization (#49), exhaustive administrative readiness, inference quality, every possible concurrency interleaving or pilot readiness. Keep #43 and the broader umbrella/readiness issues open as requested, with this bounded evidence linked. Earlier wider plan language must not be reported as fully executed.
