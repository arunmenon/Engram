# Pilot model-only resume review — 16 October 2026

Astra (`gpt-6-astra`, low effort) reviewed the bounded transition design, runtime diff, operator and entry-runner changes. Static review only; the reviewer made no cloud/provider calls.

The approved design permits only llm.model_id changes, one predecessor and one epoch advance. The successor digest pins the grant purpose and explicitly enumerated predecessor acceptance epochs. Original acceptance stays unchanged; reads, source trust and subscription completion recognize the grant, while every effect still uses the successor owner fence. Prepared User results remain reusable; no durable prepared pack-output receipt is claimed. The protected owner digest supplies the grant pin without another table.

Findings/dispositions:

- Recompute and verify predecessor/successor contracts before activation, including corrupt internal snapshots: addressed with digest checks and regression tests. Normal ActiveBundle registry views are independent copies; the corruption test does not claim they are mutable live contracts.
- Partial two-database activation needs retry recovery: addressed with saved exact-plan resume, application fingerprint checks and validation of both plans before either CAS. Already activated exact successor is idempotent; no extra epoch.
- Old Episode membership cannot be checked only as a subset: addressed with full CONTAINS/DERIVED_FROM row-set equality for existing Episode IDs, plus an added-membership regression. New Episodes remain allowed.

Final reviewer disposition: bounded static-review blockers resolved; acceptable to proceed with authorized cutover/pilot subject to root tests. This is not final live evidence review or full-pilot completeness sign-off.

## Corrective entry-run review

Live entry03 failed owner exclusion and preservation checks; it remains failed. #64 tracks foreign-owner Event expansion through shared Entities. The corrected User-pack personalize/who_is path scopes candidates before fusion, explicit seeds, cross-session Events and neighbor Events. A mixed-intent test revealed Episode expansion also needs owner scope; it now rejects a mixed-owner snapshot as a unit rather than altering its membership. General graph reads are unchanged. Astra reviewed that bounded fix and found no further critical gap after the Episode correction.

#65 tracks repeated Entity observation overwriting first_seen/classification and resetting mention metadata. Core GraphOperations.merge_entity_node now uses existing atomic create-only defaults for origin/classification/count fields, updating last_seen/embedding separately. Astra verified Spanner's inherited implementation remains processing-fenced and transactional; no critical gap found. Name ambiguity and deliberate reclassification remain separate.

The old pending Bob delivery was completed under Luna, adding its previously absent prepared/applied User receipt; this is retained recovery evidence, not an exemption retroactively added to entry03. Fresh corrective-run baselines include that completed state. The review accepted rerun subject to root's tests; no live-result endorsement yet.

## Provider observation timing

Entry04's primary checks passed, but its pre-shutdown provider-return assertion ran while consolidation still had an invocation in flight. Its final record contains 41 returned calls and no failed/incomplete call; the failed verdict remains. Astra reviewed moving the unchanged provider-return requirement after stop_demo awaits consumer tasks: this permits ordinary in-flight work to finish, while failures, incomplete calls, shutdown errors and preservation violations still fail. No blocker found in that bounded correction. A fresh-namespace entry05 provides separate acceptance evidence; it does not relabel entry04.
