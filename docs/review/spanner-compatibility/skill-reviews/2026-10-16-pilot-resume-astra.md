# Pilot model-only resume review — 16 October 2026

Astra (`gpt-6-astra`, low effort) reviewed the bounded transition design, runtime diff, operator and entry-runner changes. Static review only; the reviewer made no cloud/provider calls.

The approved design permits only llm.model_id changes, one predecessor and one epoch advance. The successor digest pins the grant purpose and explicitly enumerated predecessor acceptance epochs. Original acceptance stays unchanged; reads, source trust and subscription completion recognize the grant, while every effect still uses the successor owner fence. Prepared User results remain reusable; no durable prepared pack-output receipt is claimed. The protected owner digest supplies the grant pin without another table.

Findings/dispositions:

- Recompute and verify predecessor/successor contracts before activation, including corrupt internal snapshots: addressed with digest checks and regression tests. Normal ActiveBundle registry views are independent copies; the corruption test does not claim they are mutable live contracts.
- Partial two-database activation needs retry recovery: addressed with saved exact-plan resume, application fingerprint checks and validation of both plans before either CAS. Already activated exact successor is idempotent; no extra epoch.
- Old Episode membership cannot be checked only as a subset: addressed with full CONTAINS/DERIVED_FROM row-set equality for existing Episode IDs, plus an added-membership regression. New Episodes remain allowed.

Final reviewer disposition: bounded static-review blockers resolved; acceptable to proceed with authorized cutover/pilot subject to root tests. This is not final live evidence review or full-pilot completeness sign-off.
