# Independent five-combination preflight

2026-10-14. Read-only review of `engram_pack_combination_demo.py`, the verification plan and current contracts. **No-go for the draft cloud reset until the following harness corrections are made.** No runtime change or new combination-specific plumbing is warranted.

## Blockers

1. **User API authentication repeats the earlier known harness error.** The runner constructs `DemoAuthentication(..., token=AUTH)` with its default api-only role. User profile/preferences endpoints require admin, so the declared 200/404 assertions will encounter403. Use the previously reviewed explicit api+admin assessment principal through the real catalog; do not change production authorization.

2. **“Exact source evidence” is not yet exact.** Episode checks require expected links to exist but allow additional CONTAINS/DERIVED_FROM members; they accept any existing Summary without checking its identity, scope/range or exact Summary→Event membership. Decision checks only require one DERIVED_FROM edge. Belief/Goal checks validate support properties but not exact typed evidence or source receipts. Artifact API checks accept any truthy provenance, while Belief/Goal/Episode API checks only inspect one field or presence. Add exact per-artifact typed evidence sets and actual source owner/session binding; validate source receipt revisions for structured actions, and the relevant public evidence IDs/edges. Reuse independent identity formulas and frozen inputs, not production planners as the expected-value oracle.

3. **Final artifact boundaries remain under-specified.** There is no exact expected set for enabled User/PDLC outputs: an extra Decision/Change/Profile could pass. Require exactly the declared two Changes and one Decision, expected profile/preferences and no unrequested Skill/other optional outputs. Belief/Goal already have exact identity checks. Dynamic Episode/Summary history is legitimate, but validate every such snapshot against accepted session membership, stored Summary scope/range and exact evidence; require the predeclared full-membership snapshots as already planned. Do not reject legitimate intermediate history or whitelist arbitrary snapshots simply because they exist.

## Narrow proof corrections

- Fresh User applied-receipt replay compares only User node properties. Compare its full stable graph/evidence and receipt state (or all application fingerprints if this direct public-handler replay is expected to perform no writes). Extra owner/source/correction edges must not escape the replay oracle.
- Validate accepted Event source identity fields as well as keywords: agent/session/type/time/trace should match submitted bodies. The current no-unrelated-owner check defaults missing agent provenance to Alice, so it cannot itself prove owner binding; require actual provenance for Event nodes and explicit expected owner on relevant artifacts.
- The final read oracle ignores access fields on every Event, including unrelated/unreturned Events, and omits some physical table data. Either narrow the documented claim to non-access properties (prior #61 remains the focused accounting proof) or derive the allowed access changes from actual returned Event IDs and compare all other tables/columns. Do not imply complete access accounting from the present blanket exclusion.
- Preserve explicit rejection/duplicate fingerprints and completed worker joins. Those current whole-table checks are appropriate. The HTTP duplicate and frozen-receipt replay probes must remain labeled; they do not establish general interrupted-work recovery.

## Scope and safety

The five selected configurations, same producer payloads and shared production workers are appropriate for this composition checkpoint. Explicit Memory action producers remain separate from the frozen PDLC Decision proposal; the final exact Belief/Goal set should prevent invented conversion semantics. Final importance buckets6/7/8/10 are a disclosed consequence of existing consolidation, not a scoring-quality oracle. Core entities and summaries remain enabled everywhere.

The existing exact owner/fingerprint export-readback-digest-reset flow is proportionate. Retain the epoch39 data before the first reset and the final dataset afterward; retain failed runs and verify post-process state. The current production stop path supersedes the old external consolidation-lock workaround. Scripted external provider outputs prove integration/validation/writes, not model quality. This checkpoint must not close broad #34/#39/#41/#42 or imply public/concurrent tenant isolation, all possible pack combinations, general recovery or pilot readiness.

## Focused corrected-harness recheck

2026-10-14 — the principal role, exact optional artifact sets, source identity/receipt checks, exact typed evidence, full-fingerprint applied-receipt replay and public evidence assertions address the prior primary findings. **Two new Summary-oracle mismatches still block cloud execution:**

- The all-Summary audit requires `content == SUMMARY` for agent scope too. Consolidation creates agent summaries without calling the scripted provider; they use the existing deterministic producer. Restrict scripted-text equality to episode/session scopes and validate agent content under its actual contract.
- With Memory off, consolidation's episode Summary scope_id is `<session>-ep<index>`, not the Memory membership-hash Episode identity. The current all-Summary scope assertion requires the hash in every configuration and will reject valid Core/User/PDLC output. Validate the legacy scope for Memory-off fixtures (these compact single-episode sessions use index0) and the hashed scope only for selected Memory.

Neither correction requires runtime changes or weaker membership/evidence assertions. Final go remains pending these two bounded oracle corrections.

## Final pre-cloud disposition

2026-10-14 — **Go for the bounded five-configuration cloud verification.** Inspected the latest Summary audit: agent text is independently reconstructed from accepted count/types/time bounds; episode/session text uses the scripted expectation. Legacy Memory-off episode scope and Memory-on hashed identity are distinguished correctly while retaining exact membership checks. The physical-node-column read comparison and bundle/processing record strengthen the evidence boundary. No remaining concrete preflight blocker found; no runtime change is required.

This clears execution only. Final composition acceptance remains subject to all five actual results, honest failed-attempt dispositions, source stability, verified exports and final post-process owner/fingerprint retention. Broader isolation and pilot work remain separate.
