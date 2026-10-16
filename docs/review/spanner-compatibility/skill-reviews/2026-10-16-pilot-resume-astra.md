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

## Pack JSON-output correction

Entry05 failed after a required PDLC answer was malformed JSON and rejected. #66 tracks expressing that output requirement at the provider boundary. The existing LLM client now has opt-in JSON output, enabled only for pack extraction. User extraction already used JSON mode; Summary/HyDE free text is unchanged. Existing parsing, schema, source and proposal validation remain mandatory. The runner fails promptly on terminal invalid required output rather than waiting for an impossible applied outcome. Astra's static review found no blocker; fresh validated live outputs remain required.

## Broader runner and repeated consolidation calls

Astra inspected the broader runner and found concrete harness defects: success-state rejection, duplicate provenance expectations, omitted normalized GitHub check inputs required by existing query oracles, missing settled no-write proofs, missing per-source model outcomes, weakened cumulative graph checks, retained artifact collisions, and weak User semantic checks. These were corrected before live spectrum execution. A final source-equality check was scoped to declared artifacts; model proposals retain separate source checks and records. This is static review, not broader live acceptance.

Astra also accepted process-local reuse of successful consolidation text, keyed by scope, scope ID, exact source membership and exact prompt. Summary/evidence writes and maintenance still execute; failed or empty output is not reused. The change addresses observed repeat calls without imposing a provider-call cap. Forty targeted fixture-integrity, summary-worker/shutdown and model request tests passed; mypy passed on the changed runtime files. Entry06 independently passed 58 live checks with 57 returned provider calls and no shutdown errors. Full spectrum execution and final evidence review remain pending.

## Retained global discovery and substantive summaries

Spectrum01 retained its failed CQ6 verdict. The seedless question remained `fifteen minutes`; an exact-new-17-artifacts oracle was invalid after independently matching retained features existed. Astra accepted a documented global-discovery correction: preserve the required chain, unrelated exclusions, directed links, source proof and nontruncation; independently compute eligible matching components from the pre-query graph and declared allowed links. No returned-ID whitelist, question rewrite or new seed is used.

Astra traced an active summary gap: generation received graph metadata but no ledger prose. The bounded correction uses existing fenced ledger document reads, verifies matching source IDs/session/owner, defers generation when required sources are unavailable, and includes explicitly clipped source content and IDs in the prompt. It preserves graph-selected membership and existing writes/maintenance/cache behavior. Static review found no runtime blocker. The real-model contrast probe ties stored Summary text to a returned provider output with exact matching source inputs; adversarial tests reject negated, swapped and contradictory completion claims. The probe is narrow and does not replace independent review of actual text.

Targeted consolidation, Episode, fixture and oracle checks passed (92 before the final two inverse-oracle counterexamples; all five fixture/oracle tests then passed). Live source-content verification remains pending in the continuation. Entry06 is explicitly historical dirty-worktree evidence; its Git revision alone does not reconstruct its uncommitted harness. Spectrum01 was launched from committed7c1c9d5 and every recorded source hash matched before subsequent changes. No unavailable historical source reconstruction is claimed.

## One-branch reconciliation and transport continuation

The stakeholder requested all work from the last two to three weeks on one branch. Astra rechecked the completed lineage evidence: all 368 recovered files are tracked with matching hashes; all 1,884 old-primary inventory refs resolve to recorded blobs; all 47 historical contents match SHA-256 values; the three stated patch-equivalent replacements match stable patch IDs; the pending-drain function AST matches at original and replacement commits. No remaining blocker in this bounded lineage review. Research preservation does not establish research validity or pilot completion.

Continuation02 remained failed after an HTTP ReadError during an incident read. Planning/connected evidence and partial incident data remain retained. The next attempt disables pooled idle loopback connections in the harness, without automatic retries, changed API paths, response waivers or source repair. Astra found no concrete blocker in this bounded setting. A keep-alive race is only a possible explanation, not an established RCA; a later successful run establishes behavior under the new configuration.

## Retained proposal oracle and coverage review — continuation04

Astra accepted the bounded oracle correction: continuation03 produced two design-source proposals and one prose-source proposal, all preexisting content-hash identities with DERIVED_FROM the exact current source Events. Require persisted allowed output for each source and successful pack outcomes; retain evidence checks for fresh proposals. Public reads may select historical provenance, so distinguish returned provenance policy from membership in the current source-evidence set. Continuation03 stays failed. No new design-applicability claim follows.

A separate source-grounded completeness pass found that the suite, even if continuation04 passes, establishes selected journeys rather than the complete49-candidate/18-probe catalog. Most consequential missing gates: bounded reads, late-Episode history, dependency handling, demonstrated vector contribution, complete tenant routing/overlapping-identity controls, independent reproduction and extension. User context selection/correction, ambiguous Entity names, prior-session recall, stale Memory confirmation, agent/session scope, noncompletion controls and targeted refusal cases require individual observed verdicts. Existing component proofs must remain separately labeled. External cohort deployment, hierarchy authorization, ANN load, migrations and forced-crash guarantees remain separate.

## Continuation04 commit-ticket RCA

Continuation04 stopped at catalog:B04-commit after the incident family passed38inputs. The expected IMPLEMENTS edge exists; a second edge points to literal WorkItem:jira|RESET-17. The pilot generator had renamed structured key RESET-17 to <run-id>/RESET-17, while the existing committed-event regex ([A-Z][A-Z0-9]+-\d+) recognizes the trailing RESET-17 in prose. These are distinct identities. This is a fixture namespacing defect; no runtime/parser defect or waiver is established.

Astra accepted replacing RESET-1/17/18 consistently with a unique Jira-compatible uppercase project key, retaining ordinary document namespaces and exact unexpected-edge assertions. The regression invokes the actual PDLC PackProjector and checks exact IMPLEMENTS targets, alongside two-run disjoint identity checks. Seven targeted tests passed. Continuation04 remains failed, with clean shutdown and preservation checks passed. Continuation05 uses a fresh full catalog namespace and reuses the unsubmitted Memory/User/summary fixtures; completed incident evidence is retained separately.

## Continuation05 skipped-test oracle reconciliation

Astra found the same C01-skipped missing-source_event_id failure in historical 20261009-cloud-g07-all-01/observations.json, with g07_required_path:false. That record cannot establish a past pass. Current EXECUTES schema declares no evidence properties, RAN_AGAINST declares only commit_sha, and the original rules match. This is an unsupported oracle expectation, not an established regression.

Corrected the shared skipped fixture and normalized-webhook helper: exact directed links and commit_sha remain required; actual TestRun/TestCase DERIVED_FROM membership, public source Event and accepted receipt position remain checked by the pilot. Skipped/finished distinctions, missing optional links, forbidden VERIFIES and duplicate no-write checks remain. Eight targeted tests passed, including actual PackProjector property/source conformance for catalog accepted inputs. Astra accepted the bounded correction without pack fields or binding changes. Continuation05 remains failed after28catalog inputs, with clean shutdown. Continuation06 selects fresh catalog fixtures and the unsubmitted Memory/User/summary groups; incident evidence is retained from continuation04.

## Approved batch plan review

Arun approved P01–P12 for autonomous sequential checkpoints. Astra's scope review required four clarifications, folded into completion-goals.md: nonexistent-claim/trusted-source probes, explicit cross-session agent-scoped Goal with second-owner control, executable User context/ambiguity diagnostics, and bounded provider-failure/stale-startup procedures with restoration and unchanged owner. Existing legacy freeze/reactivation operators are not authorized by this plan. Independent human reproduction remains separately labeled.

## P02 source-only extraction endpoints

Astra confirmed TestCase was unreachable in normal PDLC extraction candidate discovery: only link target types were searched, while TestCase is only a VERIFIES source and is neither proposable nor owned by eligible prose Events. Regression reproduced missing prompt identity and rejected link. The profile now derives registry-permitted source+target types; the worker uses the same bounded search, key eligibility, trust and endpoint validation. Astra implementation review: no blockers.92 relevant local tests passed. Live P02 proof pending; P01 continuation06 retains original259df1c executed source.

## P02 fixture/oracle review

19 explicit inputs and seven read checks preflight accepted payload contracts and actual projection/retriever behavior locally. The scripted local proposed VERIFIES is fixture consistency proof only, not live model evidence. Future live runner requires an applied extraction outcome and exact persisted proposed edge metadata, plus missing/proposed-only/confirmed completeness channel counts and exact source/receipt membership. Astra found a reused Decision identity risk: current DERIVED_FROM membership is required, while public provenance must resolve to an accepted source belonging to that Decision rather than necessarily selecting the newest Event. Corrected accordingly. Explicit-seed trace questions are labeled traversal controls; natural discovery remains P08. P02 live run pending P01.

## P01 normalized actor and selected continuation

Continuation06 matched157catalog steps and passed intermediate reads before the first final normalized-check fixture was refused422: webhook:github is reserved for signed webhook routes. API guard is correct. Pilot-only frozen normalized copies now use pilot.normalized-github and omit native expected_authority; native helper remains unchanged. Regression invokes actual actor guard for all4inputs and preserves reserved-prefix rejection.

Astra accepted a fresh11-step mixed finished/skipped+normalized family plus separate reserved-actor422control, preserving the full10-node CQ1 query on fresh IDs. Earlier157steps/intermediatequeries remain individually satisfied evidence in a failed overall run.12remaining retained reads include explicitly partial CQ1 (only never-admitted normalized runs removed) and separately labeled AQ06 retained-global discovery: unchanged seedless question, pre-query declared relevance, Request+Spec and directed returned REFINES chain, exact accepted sources, forbidden controls and nontruncation. It does not certify newest-namespace exact3 discovery.

Astra reviewed --journeys-only implementation and frozen P01 continuation plan: no launch blocker. It preserves full authenticated setup, fresh IDs, worker setup, exact ledger/owner/oldEpisode conservation and cooperative shutdown; removes unrelated entry inputs/checks and provider minimum; records distinct mode/verdict.12local fixture tests passed. Source audit validated every continuation06 recorded source hash against its original executed Git revision; later P02 development is separate. P01 acceptance remains pending composite live evidence and final reconciliation.

## P01 final preflight dispositions

Astra confirmed the original Change-seeded CQ1 cannot establish a no-reference run: sibling-drift correctly prevents Change→linkedTestRun→TestCase→otherTestRun expansion. Preserve Change-linked outcomes with explicit no-reference exclusion; add TestCase-seeded all-execution query and assert absent RAN_AGAINST on the no-reference run. Applied to fresh and retained verification groups; original local oracle failure retained. No retriever change. Fresh mixed-verification and P02 preflight now pass actual projection/retriever checks;13retained queries also pass a separately labeled local reconstruction from archived Spanner snapshot (not live acceptance). The continuation has12fresh inputs and15final reads.
