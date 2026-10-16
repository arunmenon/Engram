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


## P01 final composite evidence review

Astra accepted the bounded P01 composite evidence with no technical blocker. Continuation07 passed243checks, all166observed provider calls returned and shutdown was clean. A appended0Events; B appended9. Both owners, old source rows/material graph and exact oldEpisode memberships remained intact; pending/DLQ empty. All 176source audit checks match1536ed0. The crosswalk records169matched step admissions across28event types, not169journeys.

Continuation06 remains failed; its157individually completed steps/three intermediate reads are reused alongside the selected07 proof. Distinct Change/TestCaseCQ1 scopes and AQ06 retained-global discovery remain explicit. No unchanged161-input, native-webhook, whole-pilot or independent-human-reproduction pass follows. Bounded issues69/70/72 may close after evidence/dispositions are pushed; umbrellas stay open.


## P03 first-phase preparation review

Astra found no necessary blocker in the prepared eight User stories plus third-person and Mercury controls (20inputs), named-context and name-ambiguity diagnostic read recording. HTTP200 is recorded as an observed diagnostic, not semantic context/disambiguation success. Explicit supported correction and alternate-context/history proof remain required before P03 closure. No P03 live run has started.

## P02 retained candidate starvation RCA

P02firstattempt failed H09-proposed-coverage: actual extraction created proposals but no requiredVERIFIES. Original fullprompt was not captured. Astra independently found alphabetical shared30candidate exhaustion in retained baseline. Root reconstruction invokes actual _known_items from executedf500f8a over the saved baseline plus frozen accepted projections:11DesignElement+13Requirement+6Spec, freshRequirement offered, freshTestCase absent. This is deterministic source-grounded diagnosis, not captured-prompt or live acceptance proof.

Astra recommended persisted registry-valid explicit endpoint priority within unchanged limit, then existing lexical fill. Implemented and38targetedtests passed, including35retainedmatch actualworkerprompt, absentendpoint rejection and candidatebound. Ruff/mypy passed. Futurefreshpackprompt capture added. #73 is a nativechild of63; #71and73 remainopen pending review/live evidence. Original P02 attempt stays failed.


Astra implementation recheck for#73: no blocker. Explicit persisted endpoints precede lexical fill while retaining eligibility,total bound and normal validation. Regression covers crowding,bothendpoints and nonexistentendpointrejection. Capture covers successful freshfixturepackcalls; failedprovidercalls still lackcapturedinputs and requireseparateP10support. FreshP02 execution appropriate; originalfailedrecord remainsfailed.


## P02 composite Decision contrast and retained-read checkpoint

Rerun02 passed its19individualinputs and26readchecks, includingactualVERIFIES fromcapturedfreshprompt. FinalDecisioncheck failed: H09producedConstraint,notDecision. Keepthatfailure. Astra approvedreusing run01'sactualLunaDecision ratherthannewinput/outcomechasing. Reviewerverifiedrecordedstatementhash=f2ce754572855ce5a92504eaf265af89dbdcb2a2fbbb9f45bee96cd93486cce4,finalstatusproposed,methodextracted,DERIVED_FROMexactoldH09. Frozenreadplanrequirespublicstatus/sourcecontrast withrun02explicitacceptedDecision; bothfailedrunsremainfailed.

Astrareviewed worker-free retained-read mode: selectedgroupswithzeroinputs only, realpublicAPI/binding/baseline/conservation, explicitzeroworkers/providers anddistinctverdict. No launchblocker. This doesnotre-executeingestion/workers; originalactualprocessing/modelproofislinked. Fivefixture/provenancechecksandruffpassed; requestcontractsvalidatedbeforelaunch.


## P02 final composite evidence acceptance

Astra found no blocker to boundedP02completion or#71/#73closure. Run02 remainsfailed solelyfinalDecisioncontrast;253checks,173returnedprovidercalls,cleanshutdown. Run03passed33retained-readchecks,0inputs/workers/providers. Bothfinalledger/owner/materialgraph/oldEpisodeconservationandpending/DLQchecks pass. Actualfreshprompt/output/SpannersavededgeproveproposedVERIFIES. Run01actualDecisionplusrun03publicstatus/sourcecontrast completesfourhistoryscenarios. Neitheroriginalrunpassedunchanged;run02H09producednoDecision;inferrededgehasnodirectEventpointer. Umbrellasstayopen.

## P03 pending-source recovery harness review

Bounded static review of the frozen pilot-p03-1016-02 plan and recovery admission/final conservation found one launch blocker: `material_node` exempts `user_extraction_owner` on the exact recovery trigger, but `verified_recovered_user_receipt` does not validate that private field. `receipt_from_event` validates the receipt owner, not the separate Event property. Require the property to equal `user:` plus the trigger agent ID, with a wrong-private-owner regression, before accepting recovery.

The remaining reviewed scope is appropriately narrow: tenant-specific original pending trigger, absent prior receipt/owner, exact frozen two-input window and hash, normal worker startup drain, no re-ingestion of Tara, and final domain receipt validation. Eight new inputs are separate; the original failed run and prior Entity mutations remain retained. Preference correction remains a separate required phase. No cloud calls or runtime edits performed by this review.

P03 recovery recheck: the private Event owner now must equal `user:` plus the exact trigger agent ID, and the added negative regression alters only that private owner and requires rejection. The conservation closure also binds the tenant-specific trigger set explicitly. The identified launch blocker is resolved; no remaining blocker in this bounded static review. This permits recovery execution, not a live recovery or P03 completion claim.

## P03 explicit preference correction acceptance plan

The bounded plan is acceptable with one conservation condition: any existing owner-profile exception must be derived from the verified applied receipt, not a blanket allowance for communication_style, technical_level or updated_at. Permit only fields actually produced and supported by that receipt, with their exact expected values, the exact support-event union, and the runtime-defined timestamp. If no persona is produced, permit no profile mutation. Keep all other profile fields unchanged. Omitting the name from the source is not a substitute for this check.

Freeze the canonical negative identity (including about_entity) before execution; require a negative-statement source quote, exact correction receipt and SUPERSEDES source, old superseded_by, preserved old evidence, and unchanged design-review preference. Active-preference and composed reads must exclude the old preference; historical export must retain it and expose the new evidence. This proves a producer-declared normalized correction, not natural-language canonicalization. No repeated wording adjustment or runtime change is authorized by this review.

## P03 decoded receipt and retained verification recheck

No launch blocker found in the bounded implementation/plan review. Recovery helpers now decode live and saved Spanner cells through the existing codec before validating receipt and source hashes; tests cover real float encoding and tampering. `verify_user_inputs` is mutually exclusive with recovery, validates the already-applied receipt at startup and final verification, and does not receive the mutable receipt exemption. Frozen 03 has zero new inputs and selects worker-free retained reads; frozen 04 contains the eight separate new inputs. The failed 02 remains the original startup-recovery attempt; 03 can prove retained receipt/public reads, not another recovery. Correction 05 was outside this review.

P03 acceptance-envelope reconstruction recheck: source confirms bound `SpannerEventLog._validated_document` attaches the validated acceptance receipt before the User input window is hashed. Including decoded saved Events acceptance in reconstructed documents corrects an omitted part of that input, rather than weakening the hash oracle. Current helper and regression include that envelope. Freeze 03's expected hash by computing from the original saved source/acceptance records; preserve 02's original plan and failure. No new blocker for this bounded correction. This is a reconstruction of the bound document representation, not a replacement for runtime acceptance validation.

P03 recovery status recheck: `plan_user_extraction` writes the separate `user_extraction_status=applied` alongside receipt and owner. The recovery-only exact-trigger exemption now includes that field, preflight requires no prior status, and final validation requires exactly `applied`; the wrong-status regression rejects `prepared`. No blocker. Retained verification receives no exemption. The original 02 failure and original two-field preservation diagnostic remain unchanged evidence.

## P03 prepared attribution prompt and correction harness review

No blocker found in the prepared owner-attribution prompt change; it distinguishes explicit indifference, absence and an owner's preference about another person without changing schema/source validation. Correction conservation computes exact old/profile updates rather than blanket exclusions. One launch blocker remains in the prepared correction oracle: the receipt's replacement identity is validated, but persisted replacement properties are checked only for owner/support/count. Require the stored Preference's frozen identity fields and materialized evidence fields to equal the validated replacement, and assert negative polarity plus frozen key/context in the active public response. Otherwise an expected ID with incorrect stored/public preference semantics can pass the current ID-only checks. Reviewed temporary prepared files only; no runtime edits or cloud calls.

P03 prepared correction recheck: identified blocker resolved. Stored replacement fields now match the validated receipt; ABOUT and DERIVED_FROM assertions follow the actual materializer representation, including evidence quote and extraction trigger. The active public response checks frozen identity fields. The Rust control explicitly requires extracted Rust, a new source REFERENCES edge, and unchanged name/type/first_seen/stored mention_count, closing the general conservation allowance for this case. No remaining blocker in this bounded static recheck; live evidence remains required.

## P03 bounded #74/#75 evidence disposition

Reviewed actual results and final snapshots: 02 remains failed with `UserExtractionConflictError: Stored User extraction result hash differs`, including tenant-A finalization error; its original Tara extraction-applied check passed, all 63 provider calls returned, shutdown was clean, and final A pending/DLQ were empty. Do not describe 02 as having passed all conservation checks: the representation exception prevented its A checks from completing. 03 passed all 37 retained-read checks with zero workers/providers, exact already-applied receipt/source validation, public source position and owner exclusion, and both tenants' final conservation/Episode/queue checks.

This composite evidence supports bounded closure of #74 (confidence-spread rejection) and #75 (receipt codec/bound-source reconstruction), without converting 02 to a pass or claiming a second recovery. #65 and #76 await their separate live controls; P03 remains incomplete pending the attribution/correction batch.

## P03 #77 canonical correction and pending recovery implementation review

No blocker found in the bounded worktree review. Selection uses immutable original contexts, preserves exact-context-first behavior, rejects ambiguous fallback and conflicting candidate assignments, validates metadata types, and computes IDs/references after canonicalization. Undeclared preference handling and graph application ownership/context checks remain intact.

Frozen 08 has zero new steps and the exact two retained correction inputs; existing pending admission/receipt guards apply. Recovery uses the saved pre-worker baseline for exact predecessor/profile changes, preventing an already-mutated live baseline from hiding effects. Provider observation now matches raw message text and includes recovery inputs, without changing model requests. This permits launch, not acceptance: original 06 stays failed and actual correction lifecycle/public reads/final conservation remain required.

## P03 retained correction/public-read follow-up review

No launch blocker found in prepared read patches and frozen 09. Shared post-state verification retains exact replacement semantics, receipt and lifecycle/evidence checks; the mutation wrapper alone requires an active predecessor/fresh replacement and computes permitted changes. Verified groups are excluded from mutation exceptions, and retained recovery inputs are not resubmitted. Preferences/export use the existing admin credential; composed reads remain ordinary API requests. Frozen 09 combines retained correction and two natural-question groups with zero new inputs. Original 08's 403/failure remains retained; the new checkpoint can establish public verification, not another correction application.

## P03 final bounded composite verdict

P03 bounded composite completion is supported. Final review confirmed saved 06 remains failed (113 checks, 215 provider calls); its Rust origin/stored-count reobservation check passed. Saved 08 remains failed (26 checks, 85 calls), with the sole failed check at the unauthorized preferences read, while both tenants' final conservation, Episode membership and empty-queue checks passed. Saved 09 passed all 60 retained-read checks with zero provider calls, including public negative identity, historical revisions, composed current correction/design context, natural-question retained-source reads and final conservation. All three saved source audits contain 176 passing file checks; shutdown errors are empty. Earlier failed attempts retain their original verdicts.

This supports closure of #65 for the observed typed/raw Entity origin and self-edge mutation paths, #76 for the exercised attribution/absence controls, #77 for explicit canonical correction preparation/recovery, and #78 for authorized public correction verification. It does not certify universal Entity identity behavior or deterministic model attribution. Original first-attempt Rust mutations remain retained, not repaired. Named-context selection and Mercury disambiguation remain diagnostics; explicit producer correction is not automatic prose canonicalization. Overall pilot, stakeholder/human reproduction and remaining milestones are not complete.

### P04 design and prepared harness

Astra low: no design or launch blocker. Require unchanged stale-action subject and all incident edges, exact bound acceptance/position/consumer and Event conflict diagnostic, exact declared DLQ set with zero pending/lag, intermediate progress-before-completion read, cross-session identity and other-owner/session exclusions, and malformed admission no-write proof. Current harness satisfies these bounded checks. Acceptance epoch and disposition epoch are distinct; bound DLQ metadata does not retain arbitrary `memory_reason`, so reason is checked on the Event. Future runs must explicitly admit this verified retained negative from immutable proof; baseline emptiness currently prevents accidental acceptance. No runtime policy changes.

### P04 final evidence acceptance

Astra low: P04 can be marked complete for its bounded scope. Saved evidence confirms 260 passing checks,208 returned actual provider calls, clean shutdown, ten zero-lag workers and final preservation for both tenants. Progress audit shows unchanged active Goal state/evidence before explicit completion; stale action records conflict/state_conflict and its retained expected DLQ. All 176 recorded source hashes match 8dd7903. No acceptance blocker. Keep explicit-action/no-prose-inference limits and require proof-backed admission of this negative before future retained runs. Overall pilot remains open.

### P05 design and harness acceptance

Astra low: no launch blocker. Proof-backed retained-DLQ admission checks successful prior evidence and exact current source/acceptance/position/diagnostic/fields, requires preservation throughout and rejects extra failures. Worker selection derives from writes/recovery, runs all five expected identities per selected tenant and rejects inactive-tenant pending work. P05 checks unchanged active Goal privately/publicly after each PDLC input, explicit completion only and noncontradictory correction in storage/public history. Preflight `trace` correction preserves required nodes/links and matches traversal semantics. No runtime or oracle waiver. Final live evidence still pending.

### P05 final evidence acceptance

Astra low: P05 can be marked complete for its bounded scope. Goal state/evidence stays exactly unchanged after Change creation, merge and passing test; only explicit completion changes it. Correction records SUPERSEDES without CONTRADICTS. P04's negative fields and all A fingerprints remain identical. All 246 checks pass, five B workers have zero lag, all 126 calls returned, shutdown is clean, and both tenants' preservation checks pass. All 176 recorded hashes match fa0b9d4. No blocker. This proves coexistence, not automatic cross-pack semantic inference; overall pilot remains open.
