# Controlled pilot completion: verification walkthrough

This is the checkpoint record for the [approved P01–P12 goals](completion-goals.md). Each goal records its own result. An input count is not a count of complete journeys, and a completed checkpoint is not acceptance of the whole pilot.

## P01 — PDLC catalog: complete, with a composite evidence verdict

### What this demonstrates

We send PDLC activity through the authenticated Engram write API, let the ordinary workers create the graph in retained Spanner, then ask Engram's public read API for the resulting artifacts and evidence. The catalog includes requests, decisions, tickets, pull requests, commits, tests, releases, deployments, rollbacks, malformed inputs and retries. A skipped test must remain skipped. An absent reference must not become an invented relationship.

This checkpoint uses two evidence records. It is **not** a claim that the original 161-input run passed unchanged.

The [per-type input crosswalk](../review/spanner-compatibility/runs/pilot-p01-1016-07/catalog-input-crosswalk.json) covers all 28 PDLC event types represented in the catalog. It links recorded scenarios and admission statuses to their original runs; projection, reads and preservation still depend on the full results below.

| Evidence | What actually happened | What it can establish |
|---|---|---|
| [Continuation06](../review/spanner-compatibility/runs/pilot-1016-continuation-06/results.json) | 157 catalog steps matched their individual checks; three intermediate reads passed. The next normalized input used a reserved native-webhook actor and was rejected. The overall run remains failed. | The recorded successful steps and intermediate states, with their individual source evidence. |
| [Selected continuation07](../review/spanner-compatibility/runs/pilot-p01-1016-07/results.json) | All 243 checks passed, including shutdown and preservation. Twelve requests produced nine new Events, two duplicates without material writes and one reserved-actor rejection without material writes. | The corrected normalized cases, explicit reserved-actor refusal and scoped reads, with final Astra review accepted. |

### What changed, and why

- **Ticket fixture identity (#69):** a slash prefix left a valid trailing Jira key in commit text. The fixture now uses a unique valid Jira key throughout, so its declared reference and the parser's reference identify the same ticket. The runtime parser was unchanged.
- **Skipped-test expectations (#70):** the old fixture expected properties that the pack did not declare on EXECUTES/RAN_AGAINST. Those unsupported property expectations were removed. Directed relationships, the declared commit SHA, artifact evidence and public source positions remain required.
- **Normalized input actor (#72):** independently authored normalized HTTP Events now use an ordinary producer actor. They do not claim native-webhook authority. A separate reserved-actor request must still be rejected with no material writes.

### Reads and their limits

The fresh verification graph has ten artifacts. Starting from its Change returns the nine explicitly linked artifacts; starting from its TestCase also reaches the no-reference TestRun, for ten. These are separate checks: sharing a test case does not create a missing Change relationship.

The thirteen retained catalog reads include an additional TestCase-scoped check. The earlier mixed graph lacks two normalized records that were never admitted, so its expected retained identities remain explicitly partial. The seedless request/spec question searches the retained dataset; it is checked against an independently constructed eligibility set and directed REFINES links, rather than being presented as an empty-database three-node result. Exact identity checks are recorded separately.

### Final conservation and review

1. All worker tasks finished; all 166 observed provider invocations returned; shutdown reported no errors. The invocation count includes consolidation of retained sessions and is not a count of catalog scenarios.
2. Exact ledger append and receipt/source checks passed. Tenant A appended no Events; B appended precisely the nine accepted unique Events.
3. Prior ledger records, tenant owners, material graph content and exact old Episode membership remained intact. Permitted Summary/importance refresh is recorded separately. Both pending-delivery and dead-letter sets ended empty.
4. All 176 recorded execution-source hashes match commit `1536ed0` in the [source audit](../review/spanner-compatibility/runs/pilot-p01-1016-07/recorded-source-audit.json).
5. Astra accepted the final composite evidence with no technical blocker. The bounded fixture issues #69, #70 and #72 are closed; #63 and broader #34/#39/#41/#42 remain open. Actual comments and reread states are in the [GitHub reconciliation](../review/spanner-compatibility/runs/pilot-p01-1016-07/github-reconciliation.json).

### Reproduction

Continuation07 executed source commit `1536ed0` on `feature/engram-memory-episodes`. Its [manifest](../review/spanner-compatibility/runs/pilot-p01-1016-07/reproduction-manifest.json) records the executed source hashes. The [frozen selected plan](pilot-p01-1016-07-journeys.json) contains the inputs and read expectations; it has no P02 business inputs.

Use a clean checkout of the recorded source and satisfy the credentials, model and binding prerequisites in the [team instructions](team-walkthrough.md). Stop competing workers. Inspect a fresh retained baseline, choose a new run ID/output directory, generate fresh fixture identities, then invoke `engram_pilot_first_run.py` with `--journeys-only` and that selected journey file. Reusing old Event identities tests retries rather than reproducing fresh creation. Do not reset a database or insert artifacts directly.

This establishes a technical verification record. A stakeholder walkthrough and an independent human reproduction remain separate deliverables.


## P02 — PDLC history: complete, with a composite evidence verdict

The first attempt sent eleven accepted inputs through the real flows. At H09, extraction applied but the expected proposed VERIFIES edge was absent. The [failed result](../review/spanner-compatibility/runs/pilot-p02-1016-01/results.json) stays failed; later hotfix inputs and final queries were not reached. All 171 observed provider invocations returned, shutdown was clean and final source/owner/material graph/oldEpisode preservation checks passed, with empty pending/DLQ. Those operational results do not repair the missing business relationship.

The candidate list is capped at30. The worker filled it by searching artifact types alphabetically. A [deterministic reconstruction](../review/spanner-compatibility/runs/pilot-p02-1016-01/candidate-reconstruction.json), using the saved baseline plus admitted projections and the original committed worker method, found 11 DesignElements, 13 Requirements and 6 Specs; the fresh Requirement was offered but its explicitly named TestCase was absent. This is source-grounded reconstruction, not a captured original provider prompt. The actual provider output proposed a Constraint, a Decision and a link to a historical DesignElement, not the required coverage link.

Issue[#73](https://github.com/arunmenon/Engram/issues/73), under#63, tracks candidate starvation. The fix offers existing registry-valid endpoint IDs explicitly named in the source before lexical fill. It keeps the same 30-candidate ceiling, type/key eligibility, persistence checks, trust and model-output validation. It creates no relationship by itself. The exact proposed-VERIFIES expectation remains unchanged.

Astra accepted the bounded implementation; 38 targeted tests, Ruff and mypy passed. The regression uses 35 historical matching DesignElements and checks the actual worker prompt, both fresh endpoints, the candidate bound and rejection of a nonexistent endpoint. The [corrected reconstruction](../review/spanner-compatibility/runs/pilot-p02-1016-01/candidate-reconstruction-corrected.json) now offers both endpoints. The new live run must still demonstrate an actual model proposal, saved edge/source evidence and public retrieval. Full fresh pack prompts are captured for that run. #71 and #73 remain open.


### P02 final walkthrough

| Scenario | Verified behavior | Evidence |
|---|---|---|
| Requirement revision | Existing work/tests remain linked to the original revision; the new revision does not inherit them. | Run02 individual input and read checks. |
| Coverage versus execution | Missing coverage, model-proposed coverage and confirmed coverage are distinguished. A failed test remains a failure; structural coverage does not become a pass. | Run02 captured real model prompt/output, stored proposed edge and completeness/public reads. |
| Hotfix traceability | Explicit work, review, test, merge, incident/remediation and deployment records have the declared identities and directed links. | Run02 individual input/read/source checks. |
| Proposal versus acceptance | Run01's actual model-produced Decision remains proposed; run02's explicit producer-recorded Decision is accepted. Public reads show each status and correct source position. | Run01 producer output/hash/membership, then run03 public contrast. |

[Run02](../review/spanner-compatibility/runs/pilot-p02-1016-02/results.json) matched all 19 individual inputs and 26 reads, then failed its final requirement that H09 also produce a Decision. Luna produced a Constraint and the exact coverage link, not a Decision. Its 253 checks include that one failure. All 173 provider invocations returned; shutdown and final conservation passed. This run stays failed.

[Run03](../review/spanner-compatibility/runs/pilot-p02-1016-03/results.json) passed 33 checks. It submitted no new Events and ran no workers or provider calls: it used the real authenticated public API to read already processed records. It verifies the retained run01 Decision and the run02 accepted Decision without chasing another model output. The original recorded statement hashes exactly to the proposed Decision identity and has DERIVED_FROM its exact admitted Event.

Run02 appended exactly 19 B Events and none in A. Run03 appended none in either tenant. Both retained owners, source rows, material graph and exact prior Episode membership, with empty pending/DLQ and clean shutdown. Each executed source set has176 hash checks matching its recorded commit: run02 `55dd7cb`, run03 `43fff58`. The [coverage audit](../review/spanner-compatibility/runs/pilot-p02-1016-02/proposed-coverage-audit.json) links the actual source invocation, returned relationship and saved edge.

Astra accepted the four bounded scenarios as composite proof, with no remaining blocker. #71 and #73 are closed for their bounded defects; broader umbrellas remain open. See the [GitHub reconciliation](../review/spanner-compatibility/runs/pilot-p02-1016-03/github-reconciliation.json). Neither original run passed unchanged. “Accepted” here is a producer-recorded decision, not authenticated human approval. Inferred relationship rows store status/trust/confidence but no direct source Event pointer; the run journal supplies invocation provenance, while artifact source provenance is checked through public reads. This limitation is retained.

Replay requires the common credentials/binding prerequisites, a pinned clean source checkout, fresh baseline and fresh fixture identities for write journeys. `--journeys-only` selects the frozen plan. A plan containing only retained reads produces the distinct `passed-retained-read-checkpoint` verdict and does not repeat original ingestion/model proof. See each run's manifest and frozen fixtures; do not rerun old Event identities and call that fresh creation.


## P03 — User stories: retained attempts and recovery history

The first Spanner attempt, `pilot-p03-1016-01` at `3d5a2e7`, remains failed. Six stories passed (coding, context-specific preferences, research, travel, work journal and household). Tara's paraphrased preference did not produce an applied receipt; the last three stories were not submitted. There were 101 recorded checks and 193 returned provider calls, with clean shutdown. One extraction delivery remains pending and no dead letter exists.

The actual Tara response contained two distinct, source-supported preferences. A confidence-score uniformity heuristic rejected it before normal validation. #74 tracks that defect. The fix makes uniformity diagnostic only, preserving schema, quoted-source and confidence-prior validation. #65 also recurred through the raw Entity merge path: Rust's original type/first_seen and an existing self-link were overwritten. Creation-only metadata is now preserved and same-identity resolution no longer rewrites a self-link. The failed mutation is retained; no manual restoration was performed.

The runtime and recovery checks passed 114 targeted local tests; a further wrong-private-owner regression passed. Ruff and targeted runtime mypy passed. These are implementation checks, not a live pass. Recovery must use the original pending Tara trigger through normal worker startup, with no new Tara Events. Only that tenant/trigger may acquire a valid applied receipt and matching private owner, with the frozen two-source hash/membership intact. All other private fields and source data remain subject to conservation. The frozen recovery plan adds eight new inputs for the three unsubmitted controls and a fresh Rust reobservation. Explicit canonical preference correction remains required separately before P03 completion.

Evidence: [original failed run](../review/spanner-compatibility/runs/pilot-p03-1016-01/results.json), [RCA](../review/spanner-compatibility/runs/pilot-p03-1016-01/failure-rca.json), [recovery plan](pilot-p03-1016-02-journeys.json). P04 onward has not started.


Recovery attempt02 remains failed. Its ordinary startup drain made a real Luna call and applied Tara's original receipt. All 63 observed provider calls returned, shutdown was clean, no new Events were submitted and both pending/DLQ sets ended empty. #75 tracks verification-runner representation errors: raw Spanner decimal encoding was passed into receipt validation, the reconstructed bound input omitted the attached acceptance receipt, and the original conservation allowance omitted the runtime's separate applied-status marker. Original02's plan and verdict remain unchanged.

The corrected verifier uses the existing storage decoder, reconstructs public bound documents from exact source/acceptance rows plus source positions, and validates private owner, status, receipt result hash and exact input membership/hash. Genuine Spanner JSON codec and tampering tests pass. The next worker-free checkpoint uses a hash independently reconstructed from unchanged attempt01 evidence, not copied from the actual result. It allows no receipt/status mutation. That checkpoint must verify public retrieval; the diagnostic receipt validation alone is not a pilot pass. Remaining stories and explicit correction are still pending.


Attempt03 passed 37 retained-read checks at `6085755`, with zero new inputs, workers or provider calls and clean shutdown. It validates original Tara's two distinct supported preference meanings, exact original input/receipt hashes, applied status and owner, public personalization/source positions, unchanged ledger/owners/material prior graph and old Episode membership, and empty pending/DLQ. Recovery execution belongs to failed02; successful receipt/read acceptance belongs to03. Neither failed original attempt is relabeled as passed. Remaining three controls, fresh Rust conservation and explicit correction still gate P03 completion.


Attempt04 passed the absence story but failed its unchanged third-person oracle: Luna attached Omar's trains preference to Leela and turned "I have not stated any travel preference" into a neutral preference. The actual output and failed verdict are retained; no immutable receipt was replaced or data manually deleted. #76 tracks the attribution defect. Existing User prompt instructions actively encouraged it through an all-information instruction, a mere-mention definition of neutral and unsupported few-shot inferences.

The bounded correction changes the User prompt: owner-specific personal facts, genuine indifference distinguished from absence, mentions distinguished from interest/expertise, and examples with names/topics different from the verification fixtures. Entity extraction remains available. No schema, confidence, source, authorization or negative assertion is weakened. Fresh controls include third-party refusal, explicit neutral indifference and an owner's real preference concerning another person, plus coding/paraphrase regressions and unsubmitted Mercury/Rust cases. Rust must show actual extraction/new REFERENCES while retaining exact origin fields and stored count. Prompt evidence will be captured. This is observed-case verification, not deterministic semantic attribution safety.

The explicit canonical correction plan separately checks actual negative source evidence, all frozen identity fields including about_entity, exact replacement identity, stored properties and ABOUT/DERIVED_FROM/SUPERSEDES evidence, current public preferences and historical export, unchanged other context and exact receipt-derived profile changes. No broad profile-field exemption is allowed. Astra reviewed the prepared implementation; live results remain pending.


Attempt06 at `36623ca` passed eight individual stories: third-party/absence/descriptive controls, explicit indifference, owner preference about another person, Rust preservation, coding and paraphrase. It remains failed at the final explicit correction: the actual model returned the correct negative assertion and quote but changed its descriptive context naturally. The domain incorrectly required that description to equal the producer's old positive identity label. #77 tracks this conflation. The correction trigger remains pending with no prepared receipt; its original source is unchanged. A final conservation did not finish because correction validation failed; do not infer a clean final pass from individual checks. Shutdown was clean and all 176 recorded source hashes match the executed commit.

The bounded fix preserves exact-context selection; only an unambiguous supported candidate may fall back to the explicit producer canonical context. Metadata types/conflicting assignments are checked, all selection uses immutable original descriptions, and canonicalization precedes IDs/references. Normal undeclared preferences and prepared receipts retain their behavior; graph application still checks owner/category/key/scope/context and successor state. Raw model output retains its descriptive wording; no new artifact property or source repair is introduced. Targeted regressions plus Ruff/mypy pass; Astra cleared implementation and recovery harness.

Frozen08 recovers the exact original correction through ordinary startup, with zero new inputs and the same semantic/identity/public-read oracles. It uses the pinned pre-worker baseline so actual correction/profile changes are compared against the correct original state. Frozen07 is a later worker-free natural-question checkpoint for Noor/Ada; attempt06's copied generic example questions prove owned context inclusion only. Neither checkpoint relabels attempt06 as passed. Provider capture now matches raw message text, fixing quote escaping that previously omitted correction input capture while retaining the actual output.


Attempt08 at `5c2fc7e` recovered the original correction through ordinary startup with zero new Events. Exact negative receipt identity, stored fields/evidence and permitted predecessor/profile updates passed. Final source/owner/material graph/old Episode preservation and empty pending/DLQ passed, with clean shutdown. It remains failed because the harness called the admin-protected preferences route with an API-only credential and correctly received403. #78 tracks this caller error; authorization policy is unchanged. Actual application belongs to08, not the later read checkpoint.

The read-only verifier separates already-applied correction validation from mutation-baseline checks, uses the existing authorized admin credential for protected User routes, retains ordinary API personalization, and applies no mutable baseline exceptions. Frozen09 combines that correction read with the two natural-question reads. It submits no Events and starts no workers/providers. Source quotes, exact identity, negative fields, lifecycle/source links, active/history and owner exclusions remain required. Astra cleared the bounded verifier; final public acceptance remains pending.


### P03 final stakeholder walkthrough — complete as composite evidence

This slice asks whether Engram can remember the right person's stated information, retrieve it with its actual sources, and apply an explicit preference correction without losing another context or its history. It uses Tenant A (Core+User+Memory), real Luna, authenticated HTTP, ordinary workers and retained Spanner. Tenant B is preserved alongside it.

| What we sent | What was verified |
|---|---|
| Maya: professional Python use, beginning Rust, explicitly not a Rust expert | Python skill is recorded without claiming Rust expertise. Repeated under the corrected prompt. |
| Ishan: short incident actions, detailed design reviews | Two distinct preference contexts and source evidence. Context-specific questions are diagnostic; automatic context selection is not claimed. |
| Nila: research answers should distinguish evidence/speculation and cite sources | Source-backed preferences are stored and returned for Nila. |
| Omar: train travel and connection-time needs | His stated travel preferences are retrievable for his owner identity. |
| Priya: work-journal guidance | Her stated preference is retained with its source. |
| Sam: household preferences and activity | Preferences do not silently become Memory Goals or Beliefs. |
| Tara: long text is difficult; two or three practical steps work better | Two distinct paraphrased preferences, exact source/owner, public retrieval. Original pending delivery was recovered; a fresh regression also passed. |
| No stated personal preference | No preference, skill or interest invented. |
| Leela describes Omar's preference and explicitly says it is not hers | No preference, skill or interest transferred to Leela. Mentioned people may remain Entities. |
| Dev describes a project and planet named Mercury | No personal preference/skill/interest inferred. Related-query behavior remains a recorded diagnostic, not a general disambiguation guarantee. |
| Noor explicitly accepts coffee or tea equally | A genuine neutral preference survives. The natural coffee/tea question is checked separately. |
| Ada prefers working with Omar | Ada's own positive preference survives with her source/owner; the natural working-with-Omar question is checked separately. |
| Ravi reobserves Rust | Actual extraction and new REFERENCES evidence, with exact prior name/type/first_seen/stored count preserved. |
| Ishan explicitly reverses his incident preference | One negative replacement, exact canonical identity and evidence; old positive revision superseded; design preference unchanged; active and historical public reads agree. |

The correction is a normalized producer action. Its metadata identifies the exact predecessor and canonical context; Luna supplies the supported negative assertion. The context label is an identity label, not the polarity of the current claim. We do not claim automatic correction detection from arbitrary prose.

The final public reads use the ordinary API role for personalization and the existing admin role for protected User preferences/export. Current preferences contain the negative incident preference and the unchanged design preference. Export retains the original positive preference, its successor and their source chains. The composed read excludes the superseded preference and returns exact source positions. No direct graph insert, source resubmission, reset or manual repair supplied a pass.

Attempt 09 at `3ab001b` passed 60 checks, with zero new Events, workers and provider calls, clean shutdown and both tenants' conservation/checks that old Episode memberships remain intact and pending/dead-letter deliveries are empty. Its [frozen plan](pilot-p03-1016-09-journeys.json), [results](../review/spanner-compatibility/runs/pilot-p03-1016-09/results.json) and [176-file source audit](../review/spanner-compatibility/runs/pilot-p03-1016-09/recorded-source-audit.json) make the read checkpoint repeatable. Actual extraction/application comes from the linked earlier worker runs, including 08; 09 is not another application.

Astra independently accepted bounded P03 completion and closure of #65/#76/#77/#78 for the exercised defect scopes. #74/#75 were accepted and closed earlier. Original attempts 01, 02, 04, 06 and 08 remain failed; their individual successful cases and later checkpoints form the composite evidence. The first attempt's overwritten Rust origin/self-link metadata remains retained and documented; no claim of unchanged original metadata across that failed attempt is made. Confidence/proficiency values are attributed model assertions, not calibrated measurements or verified qualifications.

To repeat: pin the recorded source, satisfy the common cloud/model/binding prerequisites in the team instructions, stop competing workers, inspect a fresh retained baseline, then use the frozen selected plan with `--journeys-only`. A write reproduction needs fresh Event/owner/session identities; retained verification intentionally uses already-applied inputs and starts no workers. Failed source records and exact hashes are kept. Independent human reproduction and the overall pilot remain incomplete. P04 is next.

## P04 — Tenant A Memory: predeclared execution contract

Frozen plan: [18 authored inputs](pilot-p04-1016-01-journeys.json), plus public current/history and cross-session/owner reads. It reuses the eleven Memory lifecycle actions and adds a stale confirmation, agent-scoped Goal creation, other-owner and session-scoped counterparts, ordinary progress, explicit completion in the second session, and malformed completion. All writes and acceptance reads use the public authenticated dispatcher, ordinary workers and retained Spanner; no database reset or source repair is allowed.

The stale confirmation is expected to be admitted (201), then fail projection with `memory_status=conflict`, `memory_reason=state_conflict` and exactly one projection dead letter. Its immutable embedded acceptance, tenant/database/binding, consumer, Event identity and position must match the admitted source; target properties and all incident evidence/lifecycle edges must remain identical. All other deliveries must drain normally, with zero pending and lag. The negative audit record remains retained. Later milestones must explicitly admit this verified negative using its proof; the P04 executed revision rejected any preexisting dead letters; P05 adds explicit proof-backed admission.

Completed Goals remain visible in `goals` context with their actual status; source inspection shows only superseded state is excluded from current Memory context. Public provenance anchors the original creation/stated Event, while directed evidence links retain subsequent actions. Cross-session reads must return the same agent-scoped identity and exclude the other owner's Goal; the first-session read must exclude the second-session-only Goal. Ordinary progress is read before completion and must leave Goal state and evidence unchanged.

Astra's bounded design and harness reviews found no launch blocker. Forty targeted local tests passed before the final additional public-edge/source checks; local checks do not certify Spanner. Live results are not yet available.

### P04 stakeholder walkthrough — complete

**Question:** does Memory keep the right belief/goal state, owner, scope and source history when explicit actions arrive, including a stale action and ordinary progress?

[Run `pilot-p04-1016-01`](../review/spanner-compatibility/runs/pilot-p04-1016-01/results.json), executing source `8dd7903`, passed **260 checks**. Eighteen inputs went through the authenticated public HTTP dispatcher: seventeen accepted Events and one malformed completion rejected with 422 and no material write. All ten ordinary workers ran against real Spanner; all final lags and pending sets were zero. All 208 actual `gpt-6-luna` calls returned and cooperative shutdown was clean. These background model calls are not evidence of automatic Memory inference: the tested Memory actions are explicit producer assertions.

| Input sequence | Actual result through storage and public reads |
|---|---|
| State, then confirm a belief | Stated origin, asserted confidence 0.7, confirmation count 1→2 and revision 0→1; exact source evidence retained. |
| Confirm using stale revision 0 | API201 records the audit Event; projection records `conflict/state_conflict` and the exact expected dead letter. Belief properties and all incident links remain unchanged. |
| Record an inferred replacement and explicit contradictory correction | Replacement keeps inferred origin and zero confirmations; old belief reaches revision 2 and is superseded. Declared SUPERSEDES/CONTRADICTS links cite the correction Event. Current belief reads omit the old assertion; history retains both. |
| Complete, abandon and replace three separate goals | Distinct completed/abandoned/superseded states with exact evidence; replacement is its own active Goal. |
| Same-key goals for one agent across sessions, a session-only counterpart, and another owner | Agent-scoped identity is reused across sessions; the session counterpart stays distinct. Both session reads exclude the other owner's Goal; the first excludes the second-session-only Goal. |
| Ordinary progress, then explicit completion in session two | Public progress read still shows the exact original active Goal, revision 0 and evidence count 1. Only the explicit completion changes it to completed/revision 1/count 2. Other owner/session goals stay active. |
| Malformed completion missing expected revision | API422; ledger and material graph unchanged after unrelated work settles. |

The [stale-action audit](../review/spanner-compatibility/runs/pilot-p04-1016-01/stale-action-audit.json) includes actual before/after public properties and incident edges, the immutable accepted delivery, its exact position and Event diagnostic. The [progress audit](../review/spanner-compatibility/runs/pilot-p04-1016-01/goal-progress-audit.json) shows creation, ordinary progress and explicit completion separately. The private storage comparisons additionally checked all subject properties and incident edges, rather than only selected status fields. Public reads checked directed lifecycle/action evidence and exact creation-source provenance positions.

Tenant A appended exactly 17 source Events; Tenant B appended none. Both tenants retained their ownership, all earlier source documents, material graph except the separately approved Summary/importance refresh, and exact old Episode membership. A retains exactly one negative-test delivery, `assessment-projection/dc1c59b9-2e0f-515f-896e-fa87f37a29a7`; B has no dead letters. This retained record is expected evidence, not unfinished successful work and not permission to ignore other failures. Subsequent goals need an explicit proof-backed declaration before startup. No runtime code, pack schema, database ownership or source repair changed for P04.

[The source audit](../review/spanner-compatibility/runs/pilot-p04-1016-01/recorded-source-audit.json) matches all 176 recorded file hashes to committed source `8dd7903`. Forty targeted local tests and Ruff passed; the cloud checks supply end-to-end acceptance. Astra independently reviewed the prepared harness and final evidence and found no blocker for this bounded scope. Broader pilot/feature issues remain open; see [issue reconciliation](../review/spanner-compatibility/runs/pilot-p04-1016-01/github-reconciliation.json).

Executed commands, from the pinned checkout with cloud impersonation, OpenAI credentials and both retained bindings available:

```sh
PYTHONPATH=src:scripts python scripts/engram_pilot_model_transition.py inspect \
  --binding-record docs/review/spanner-compatibility/runs/pilot-1016-model-transition-01 \
  --output docs/review/spanner-compatibility/runs/pilot-p04-1016-01-preflight
PYTHONPATH=src:scripts python scripts/engram_pilot_first_run.py \
  --run-id pilot-p04-1016-01 \
  --predecessor docs/review/spanner-compatibility/runs/pilot-p04-1016-01-preflight \
  --output docs/review/spanner-compatibility/runs/pilot-p04-1016-01 \
  --journey-file docs/pilot/pilot-p04-1016-01-journeys.json --journeys-only
```

These are the executed coordinates, not an instruction to submit the same identities again. A new write reproduction needs fresh run/Event/owner/session identities, a fresh baseline and explicit admission of the preserved negative-test proof. The P04 executed revision initially rejected preexisting dead letters. P05 adds explicit proof-backed admission for later retained runs, preserving the verified negative and rejecting unexpected failures. Independent human reproduction remains a later milestone. Cloud Monitoring export still reports 403; this run does not establish monitoring export, automatic prose inference, calibrated confidence or full pilot readiness.

## P05 — predeclared Memory/PDLC coexistence contract

Frozen plan: [16 explicit inputs](pilot-p05-1016-01-journeys.json) for Tenant B. The eleven Memory lifecycle actions remain, with correction explicitly declaring `contradicts=false`. A separate delivery Goal is created, followed by a PR creation, PR merge and successful test with exact TestRun→TestCase and TestRun→Change links. After each PDLC input, exact private Goal properties/incident links and a public active-state read must stay unchanged. Only the final explicit Memory completion may complete the Goal. Public history must show SUPERSEDES without CONTRADICTS for the corrected belief pair. Common session/narrative does not assert an automatic Memory-to-PDLC semantic relationship.

P04's expected negative is an explicit prerequisite: the frozen plan pins the successful results, source audit and stale-action audit by SHA256. Before startup the harness validates their actual passing verdict, preservation proof and exact current source, acceptance, position, diagnostic and dead-letter fields. The retained record must remain present and identical throughout; unexpected dead letters still fail. This extends the previous empty-baseline guard without weakening it into a broad exception.

Only Tenant B receives writes, so all five B workers run; both dispatcher bindings and both tenants' preservation checks remain. Any pending work in inactive A fails preflight. No worker is omitted for an active tenant, and no model-call cap, timer, runtime policy, pack schema or owner binding changes. The original P04 evidence remains tied to its ten-worker execution; future checks report actual selected-worker identities.

Thirty targeted local tests and Ruff pass. Local preflight exposed an oracle mismatch: `status` returns the seeded artifact without traversal. The related TestRun/TestCase/Change check now uses `trace`, retaining all required nodes and directed links. No cloud attempt was run with the earlier oracle. Astra reviewed design and the prepared harness, found no launch blocker and confirmed no runtime or oracle waiver. Live P05 results are not yet available.

### P05 stakeholder walkthrough — complete

**Question:** can Memory and PDLC share a tenant without confusing “code merged/tests passed” with “this Goal is complete,” or confusing a correction with an asserted contradiction?

[Run `pilot-p05-1016-01`](../review/spanner-compatibility/runs/pilot-p05-1016-01/results.json), executing `fa0b9d4`, passed **246 checks**. All sixteen authored inputs were accepted through the authenticated dispatcher into real Spanner. All five Tenant B workers ran and finished at zero lag; all 126 actual `gpt-6-luna` calls returned and shutdown was clean. No runtime, pack-schema or owner-binding change was required.

| What went in | What Engram stored and returned |
|---|---|
| Eleven explicit Memory lifecycle actions | Stated/inferred beliefs, confirmation, correction and distinct completed/abandoned/superseded Goals, with exact source evidence. |
| Correction declaring `contradicts=false` | Old belief is superseded, with a declared SUPERSEDES edge and its original evidence retained. No CONTRADICTS edge exists for the pair in storage or the public history response. |
| A delivery Goal, then PR creation | Change is open; the Goal stays active at revision 0/count 1, with exactly unchanged properties and incident evidence. |
| Merge that PR | Change becomes merged with the declared merge SHA; the Goal remains unchanged and publicly active. |
| Successful test against the merged code | TestRun has outcome `success`, EXECUTES its TestCase and RAN_AGAINST the Change with commit SHA `abc123`. The Goal still remains unchanged. |
| Explicit Goal completion | Goal becomes completed at revision 1/count 2. Its evidence consists of the creation and explicit completion actions; PR/test success did not supply implicit completion. |
| Public PDLC trace and Memory history reads | TestRun, TestCase and merged Change return with exact directed links/source positions; the Goal and corrected-belief history are separately retrievable through supported Memory reads. |

The [coexistence audit](../review/spanner-compatibility/runs/pilot-p05-1016-01/memory-pdlc-coexistence-audit.json) records the actual public Goal properties and incident edges at creation, after each PDLC action, and after explicit completion. Private checks also compared every Goal property and incident edge before/after each PDLC action. The [correction audit](../review/spanner-compatibility/runs/pilot-p05-1016-01/noncontradictory-correction-audit.json) contains the exact input, stored belief/relationship and public history response.

Tenant B appended exactly 16 source Events; A appended none. Both retained their owner, earlier source documents, material graph except approved derived refresh, and exact prior Episode memberships. B has no pending/dead-letter work. A has no pending work and retains exactly P04's verified negative. The [retained-negative audit](../review/spanner-compatibility/runs/pilot-p05-1016-01/retained-negative-audit.json) shows the pinned prerequisite and identical before/after fields; **all A table fingerprints are identical**. Only B needed processing workers; both tenants remained in dispatcher/preservation scope.

All 176 [recorded source hashes](../review/spanner-compatibility/runs/pilot-p05-1016-01/recorded-source-audit.json) match committed source `fa0b9d4`. Thirty targeted local tests and Ruff passed. Astra independently accepted the final bounded evidence with no blocker. Broader issues remain open; see [issue reconciliation](../review/spanner-compatibility/runs/pilot-p05-1016-01/github-reconciliation.json).

The exact executed write command was:

```sh
PYTHONPATH=src:scripts python scripts/engram_pilot_first_run.py \
  --run-id pilot-p05-1016-01 \
  --predecessor docs/review/spanner-compatibility/runs/pilot-p05-1016-01-preflight \
  --output docs/review/spanner-compatibility/runs/pilot-p05-1016-01 \
  --journey-file docs/pilot/pilot-p05-1016-01-journeys.json --journeys-only
```

The preceding inspect command uses the same retained model-transition binding record as P04 and a fresh `pilot-p05-1016-01-preflight` output. A new write reproduction needs fresh run/Event/owner/session identities and a fresh baseline. The selected JSON plan explicitly pins P04's successful negative-test evidence; it never derives an exception from whatever failed rows happen to exist. No original identities should be resubmitted and counted as new creation.

This proves **coexistence and explicit state transitions**, not an automatic semantic Goal→PR link, automatic prose inference, calibrated confidence, independent human reproduction or full pilot readiness. Same-session context provides the narrative grouping. Cloud Monitoring export still reports 403. P06 is next.

## P06 — predeclared late-activity Episode contract

Frozen plan: [eight source Events](pilot-p06-1016-01-journeys.json), four per tenant. Each primary session first receives activity at minute0 and minute40, separated by more than the current30-minute grouping gap. An unrelated session with the same owner/wording receives its own control Event. Both tenants must produce and publicly return the initial singleton Episodes before either late Event is admitted. The late Event has an occurrence time at minute20 but arrives after that publication; normal consolidation must produce a new three-member snapshot while preserving the earlier snapshots.

All business inputs use the authenticated API and ordinary ten-worker/Spanner path. Targeted SDK reads only wait for production; they do not substitute for public acceptance. Private checks require exact Episode identities, complete flags, source membership/methods, temporal bounds, Summary ownership/count/bounds/links and actual admitted positions. Public reads require exactly the chosen Episode and episode-Summary sets, exact directed membership and Summary targets, and exact source anchors/positions. Old Episode properties/membership and Summary structural fields must remain identical; approved Summary content/timestamp refresh remains separate.

Primary/control reads prove Episode membership/context isolation. General raw Event recall has different semantics and is recorded as a diagnostic rather than silently treated as a broader isolation pass. There is no new Session-end input that would alter membership. Both primary/control sessions qualify under the recorded reflection threshold5 and count×5 policy. Each phase has a bounded600-second materialization/public convergence deadline; timeouts fail, and all public attempts remain recorded. Unexpected Episode context or HTTP errors fail immediately. This is eventual production through existing workers, with no timer/model cap, owner transition, direct graph insert, repair or deletion.

Forty-six targeted local tests and Ruff pass. Astra's initial review found two public-oracle gaps (unexpected Episode context and extra Summary membership targets); both were fixed and covered by adversarial regressions. Astra's bounded recheck found no remaining launch blocker. P07's separate actual-model Summary-quality checks are unchanged; P06 does not count generic/fallback Summary text as a quality pass. Live P06 evidence remains pending.

## P07 predeclared verification contract — actual Summary meaning

P07 has four fresh cases: Tenant A and Tenant B each receive a forward story (“Investigation completed; rollout uncertain”) and an inverse story (“Investigation incomplete; rollout completed”). Each receives one additional progress record that explicitly does not change those outcomes. Eight source Events go through the authenticated API; normal consolidation produces the Episode and Summary. No P07 cloud input has been submitted at this preparation checkpoint.

The checks parse the actual provider prompt's JSON source lines and require the exact two admitted Event IDs and payloads, without extra or duplicate source Events. A returned `gpt-6-luna` call must supply the exact stored Summary text, and that same text must appear in the public temporal response. Fallback text cannot satisfy this proof. The existing narrow outcome/uncertainty oracle remains unchanged; this is not a general language-quality certification.

Each case must have a complete Episode with exact membership, bounds, Summary structure and directed links. Public Episode/episode-Summary sets must match that session exactly, excluding the opposite-outcome session. Member positions and snapshot source anchors must match actual admission receipts. General raw Event recall remains separately diagnosed. A 1200-second publication/convergence deadline accounts for retained-session scheduling and does not waive wrong membership, extra context or wrong content. Strict stored/public equality can conservatively fail during concurrent Summary refresh; retain that evidence rather than replace the observation with whichever text passes.

The frozen plan carries the exact successful P04 stale-action proof. The audit dead letter remains required and unchanged; arbitrary dead letters remain failures. Existing tenant ownership, source records, material graph and prior Episode memberships remain protected by the root harness. Final acceptance requires all relevant worker lags/pending work to settle, clean shutdown, retained raw evidence, source-commit audit, Astra evidence review and issue reconciliation. P07 has not passed until those results exist.

P07 preparation refinement: normal consolidation may publish a singleton while sequential source admissions are in progress. The only permitted historical contexts are the independently computed singleton snapshots of either of the two frozen source Events. If present, each must satisfy the full membership, bounds, Summary structure, directed-link and receipt-backed provenance checks; the final two-member snapshot remains mandatory. Extra session context remains a failure. No importance hints or runtime thresholds are changed: Astra confirmed current eligibility is event-count based, so hints would not solve this scheduling case. This preserves source-valid history rather than treating it as foreign context.

## P06 retained failed attempt and bounded retry

Run `pilot-p06-1016-01`, executed source `cd7291b`, is **failed**. Its 600-second initial publication deadline expired with readiness `[true, false]`: Tenant A had all required initial snapshots; Tenant B did not. Six source Events were accepted through the public API. Neither late bridge was submitted, and no membership or public-history assertion was waived. The log shows retained sessions being processed sequentially; B's first selection captured one primary Event before the second was projected, requiring a later cycle for the complete expected set. This is an observed scheduling limit, not a pass or a claim that the longer window guarantees completion.

The attempt shut down cooperatively without errors. All 224 actual Luna calls returned. Final owner/source ledger preservation, prior Episode membership, zero pending work and exact declared dead-letter checks passed on both tenants. All 177 executed source hashes match committed `cd7291b`. The failure audit, API receipts, snapshots and compressed raw log are retained under [the failed attempt](../review/spanner-compatibility/runs/pilot-p06-1016-01/failed-attempt-audit.json).

Astra accepted the smallest retry: fresh run `pilot-p06-1016-02`, identical eight scenarios and exact acceptance oracles, with the phase publication window predeclared as 1200 seconds. Existing data and the failed attempt remain. No source content, grouping rules, worker scheduling, binding, runtime threshold, pass criteria or business path changes. No recovery framework or direct graph repair. P07's first run receives the same predeclared operational window. Forty-one focused P06/P07/P04/P05/fixture tests passed after preparation; Ruff and whitespace checks passed. Live retry acceptance remains pending.

## P06 second retained failure and exact read-only checkpoint

Run `pilot-p06-1016-02`, executed source `e2beca2`, remains **failed**. It accepted all eight Events through authenticated APIs and ran all ten ordinary workers. Both tenants' initial private/public publication checks passed before the late inputs. The combined three-member snapshots were available on both tenants. A's private merged-history checks and preservation comparison passed, but its public read contained an additional same-session two-member snapshot (first Event plus the late bridge). The original oracle demanded only the two initial singletons and final merged snapshot, so it rejected that additional history.

Astra independently found that additional snapshot source-valid. Its identity, exact members, bounds, linked Summary, directed edges and public membership are checked in [the history-oracle audit](../review/spanner-compatibility/runs/pilot-p06-1016-02/history-oracle-audit.json). The count-then-limited-fetch consolidation path is a plausible explanation for the intermediate snapshot; the saved response establishes its membership, not its precise creation sequence. No foreign Episode is excused, and run02 is not relabeled as passed.

Run02 has 166 checks with one failure, 564 returned actual Luna calls, clean cooperative shutdown and passing final owner/ledger, material graph, old Episode membership and queue/dead-letter preservation checks. Its 178 executed source hashes match `e2beca2`. The failed run, original inputs, HTTP receipts, snapshots and raw log remain retained.

The frozen follow-up `pilot-p06-1016-03` is **worker-free and read-only**. It pins six original evidence files by hash and requires the named successful initial publication/source checks, final preservation checks, original ten worker identities, clean source audit and empty shutdown/finalization errors. It reconstructs all eight exact accepted inputs and positions and checks that both tenants' initial public reads preceded the late admissions.

Its candidates come only from the three frozen primary Events: three singletons, the two temporally connected pairs, and the full triple. The disconnected first+later pair is forbidden because its gap is 40 minutes. Each tenant's unrelated-session control is separate. The two original singletons and final triple remain mandatory. Every actually published optional candidate receives full identity, bounds, membership, Summary, directed-link and source-position validation. Original Episode properties and memberships must equal the saved pre-bridge proofs. Public reads must return the exact validated private history for the selected session, excluding the control in both directions. The query text stays unchanged.

A successful checkpoint would support a **composite P06 proof**: original API→worker→Spanner writes/public initial reads from run02, followed by exact retained public-history reads from run03. It cannot turn run02 into a pass or prove fresh worker behavior on the follow-up's source revision. No source resubmission, direct graph inserts, reset, migration or manual repair is performed.

## Bounded Summary-cache correction under #67

The retained preflight contains 95 Episode/session cache keys in A and 129 in B, before the new P06 sessions. The existing 128-entry LRU therefore has capacity pressure in B. Under stable cyclic traversal with successful outputs, a working set larger than that capacity can repeatedly evict itself. This does not attribute every live model call to eviction: cold calls, changed sources and failures are separate causes.

The regression reproduced two identical 65-session cycles making 260 calls. The smallest correction raises the existing bounded capacity to 256, with identical scope/identity/membership/prompt keys, worker-local lifetime, success-only caching and eviction semantics. It is a memory bound, not a model-call/spend cap. The corrected two cycles make 130 calls; changing one session's Episode and session prompts adds only two calls. Eviction and failure/empty-output tests remain enforced. There is no unlimited reuse or latency claim.

Astra cleared this narrow fix and the retained-history checkpoint. Fifty-five focused tests passed during preparation, followed by 30 targeted tests after the proof-loader refinements; those sets overlap and are not added together. Ruff/whitespace checks passed. The worker-free checkpoint cannot prove live cache benefit; that confirmation remains for the next actual worker run. #67 stays open pending that evidence.

## P06 verification walkthrough — late activity and Episode history

**Question:** when an older activity record arrives late, can Engram update its grouping without erasing what it previously published?

The grouping rule uses source timestamps: a gap greater than 30 minutes starts a separate Episode. For each tenant, we first submitted an activity at minute 0 and another at minute 40. They belong to one session but initially form two separate Episodes. We also submitted the same wording under the same owner in a different session as a negative control. The runner waited for the initial private structure and public reads before sending anything else.

Next, we submitted an Event whose source timestamp was minute 20. Its ledger receipt is newer, but its source time sits between the first two Events. Both gaps are now 20 minutes, so normal consolidation should publish a new three-member Episode. The two earlier Episodes must remain available with their original members and bounds. `complete=true` here means the snapshot's membership has been written; it does not mean a task or Goal completed.

| Input in each tenant | Expected observation |
|---|---|
| First activity, source minute 0 | One singleton Episode with the first Event as evidence |
| Later activity, source minute 40 | Another singleton Episode; both publicly retrievable |
| Same wording, unrelated session | A separate Episode context in that session's read, excluded from the primary Episode context |
| Late activity, source minute 20, sent after initial reads pass | A new three-member Episode; earlier two remain unchanged |

Tenant A also published a source-valid first+bridge snapshot along the way. It remains in history rather than being erased. The original three-snapshot-only oracle rejected it; Astra reviewed that failure and the follow-up validates every source-valid published snapshot. Tenant B has the initial two and final merged snapshot.

The late Event is not a data migration or manual repair. Every Event enters through the authenticated API; ordinary workers construct the graph in real Spanner; acceptance reads use the public API. The read-only SDK snapshots support diagnosis and exact storage checks.

For every snapshot we compare the declared identity, exact Event members, bounds, linked Summary structure, directed CONTAINS/DERIVED_FROM/SUMMARIZES edges and receipt-backed source positions. Public reads must return the exact expected Episode/episode-Summary history for the selected session. A generic raw Event recall result is separately diagnosed and is not used to claim strict session isolation for every retrieval channel. Summary text quality is the separate P07 check; P06 proves membership/history structure.

**Accepted result:** P06 is complete as a bounded composite proof, independently accepted by Astra. Original run02 supplies eight authenticated API admissions, ten ordinary workers, real Spanner materialization and both initial public checkpoints. Retained run03 passed all 271 checks with four public 200 reads, zero new inputs/workers/model calls and clean shutdown. Its 179 source hashes match `d429f96`. Both owners and source ledgers stayed unchanged; all prior material graph and Episode memberships were preserved.

| Public read | Expected and actual Episode context | Verdict |
|---|---|---|
| A primary session | Four Episodes and four linked episode Summaries: initial two + valid intermediate pair + merged triple | Pass |
| A control session | One control Episode and Summary; primary context excluded | Pass |
| B primary session | Three Episodes and three linked episode Summaries: initial two + merged triple | Pass |
| B control session | One control Episode and Summary; primary context excluded | Pass |

Repeat the exact public read checkpoint using the pinned run03 fixture and a fresh read-only preflight; the frozen evidence hashes must still match. [Composite audit](../review/spanner-compatibility/runs/pilot-p06-1016-03/episode-history-composite-audit.json), [actual public responses and checks](../review/spanner-compatibility/runs/pilot-p06-1016-03/results.json), [frozen read plan](pilot-p06-1016-03-journeys.json), [source audit](../review/spanner-compatibility/runs/pilot-p06-1016-03/recorded-source-audit.json). Original01/02 remain failed. This does not prove Summary meaning, live cache benefit, all-channel session isolation, overall pilot readiness or independent human reproduction. P07 is next.

To repeat the P06 retained-read checkpoint, use the repository's Python environment with dependencies installed, `gcloud` on PATH, the experiment service account authorized on both retained databases, and the existing pilot credentials/environment. The harness checks for an OpenAI credential even though this read-only mode makes no provider calls. Existing ownership/bindings must remain unchanged; the preflight refuses a mismatch. Choose fresh output names if these already exist. No database cleanup is part of this command pair.

```sh
PYTHONPATH=src:scripts python scripts/engram_pilot_model_transition.py inspect \
  --binding-record docs/review/spanner-compatibility/runs/pilot-1016-model-transition-01 \
  --output docs/review/spanner-compatibility/runs/p06-recheck-preflight

PYTHONPATH=src:scripts python scripts/engram_pilot_first_run.py \
  --run-id p06-recheck \
  --predecessor docs/review/spanner-compatibility/runs/p06-recheck-preflight \
  --output docs/review/spanner-compatibility/runs/p06-recheck \
  --journey-file docs/pilot/pilot-p06-1016-03-journeys.json --journeys-only
```

### P07 launch refinement — actual Episode call and cache observation

The four frozen cases and query text remain unchanged. The harness now observes each original consolidation summary call without replacing its provider, arguments or return value. It records tenant, Episode/session scope and identity, source IDs, prompt/output hashes and cache presence. A task-local correlation ID links an actual provider call to that exact summary invocation. P07 requires the actual matching Episode call, rather than accidentally crediting the separate session-summary call with the same source text. Public source members must also be typed Events.

For #67, cache presence alone is not proof of reuse: a successful same-key invocation must return the same text without a correlated provider call. The measured larger retained working set will be evaluated separately; no live benefit is claimed before that evidence. The observer is not a model replacement or a model-call/spend cap. Its tests preserve original call count/results, verify context at the actual invocation, and preserve exception propagation/context reset. Forty-eight targeted tests and Ruff/whitespace checks passed. Astra's bounded launch recheck found no blocker.

## P07 — Actual Summary meaning and cache reuse

**Complete for four frozen contrasts; Astra accepted final evidence.** Run `pilot-p07-1016-01` used committed source `cef29cc`, both retained tenant databases and all ten normal workers. All133 checks passed; eight source Events were accepted and four public temporal reads succeeded. All final worker lags were zero, shutdown errors were empty, and retained owners, source data, prior Episode memberships and the exact P04 negative delivery were preserved.

For each tenant, one session says the investigation completed while rollout remains uncertain; another reverses those outcomes. Each has a second progress-only record. Engram created complete two-member Episodes and Summaries. We checked the actual Episode-scoped Luna prompt contained exactly the accepted Event IDs and payloads, the stored text equaled the actual returned text, and the public response returned that same text with exact Episode members, links and source positions. All four independently declared meaning/uncertainty contrasts passed. Any optional earlier singleton snapshot was checked separately. This proves these four contrasts, not general Summary quality or all-channel session isolation.

The transparent observer also measured705 Summary invocations: A103 and B137 cold keys, plus214 and251 successful cache hits respectively. All240 cold Summary invocations had a matching actual provider call; all465 hits had no correlated provider call and retained the prior output hash. Four other provider calls bring the run total to244, all actual `gpt-6-luna` returns. This provides live proof for #67's bounded256-key worker-local cache fix. It does not establish persistence after restart, unlimited retained-size support or a latency/throughput guarantee. No model-call or spending cap was added.

Evidence: [results](../review/spanner-compatibility/runs/pilot-p07-1016-01/results.json), [cache audit](../review/spanner-compatibility/runs/pilot-p07-1016-01/summary-cache-audit.json), [committed source audit](../review/spanner-compatibility/runs/pilot-p07-1016-01/recorded-source-audit.json). All179 recorded source hashes matched the executed commit. Failed P06 attempts remain unchanged.

Repeat from a clean checkout at the pinned revision, after explicit fresh namespace/predecessor preparation: `PYTHONPATH=src:scripts python scripts/engram_pilot_first_run.py --run-id NEW-ID --predecessor FRESH-PREFLIGHT --output NEW-OUTPUT --journey-file FRESH-FROZEN-P07-JSON --journeys-only`. The saved fixture and original run ID are evidence, not reusable fresh identities. A stakeholder walkthrough and independent human reproduction remain separately tracked.

## P08 — Prepared retrieval discovery probes

The frozen `pilot-p08-1016-01-journeys.json` has nine source inputs: B's isolated Change→failed TestRun→TestCase chain, an unrelated Change, two isolated equal-title Changes admitted under different authenticated sources, and one service-description/session-end pair per tenant. Exact trace requires the declared directed links and failed outcome. One-node and one-hop reads separately verify truncation and the actual depth frontier. Ordinary title discovery and an independently authored paraphrase keep separate verdicts; a paraphrase miss is a capability gap, never evidence of successful semantic discovery.

Both tenant vector probes observe the exact serving request through actual embedding, executed native indexed Spanner query/results, Entity hit, REFERENCES-linked Event seed and public Event/provenance. This proves participation, not exclusive causation, ANN recall or performance. The observer forwards original results/errors and resets task context in finally. Trust checks compare verified acceptance source IDs, stored trust and seedless default/opt-in responses; explicit-seed lookup's admission exception is outside that exclusion assertion. Absent claims must not invent an identity or matching approval, while legitimate broad recall may remain. The P04 negative and retained owners/sources/Episode histories remain preservation requirements. Local focused validation:29 passed; final cloud results pending.

### P08 attempt01 — retained failure and reviewed correction

The nine source inputs were accepted. Exact traversal and directed links, failed TestRun state, node/depth budgets, ordinary wording, the frozen artifact paraphrase and authenticated trusted/untrusted comparisons passed. The run then failed `p08-vector-a endpoint/source closure`: the oracle demanded direct Event provenance from every returned node. All eight nodes without it were Entities, whose implemented evidence contract is instead an incoming REFERENCES link from an Event. The response has those links and no dangling edge. Astra confirmed the correction must validate stored Entity identity/attributes and an exact public REFERENCES edge present in the same-tenant snapshot, with its returned source Event's receipt validated. Other missing provenance stays invalid. The original attempt stays failed; unchanged public questions will be rerun without new business inputs.

Shutdown exposed a separate delay: consolidation continued starting retained sessions after stop. Issue [#79](https://github.com/arunmenon/Engram/issues/79), actually linked under #63, tracks a bounded cooperative-stop correction reviewed in principle by Astra: finish the current awaited session/SDK operation, then stop at a session/stage boundary. No running-process edit or SDK cancellation is allowed. One unrelated retained Episode summary call also returned an actual provider InternalServerError during shutdown; the run record retains it. No all-provider-success claim is made for this attempt. Final conservation/shutdown audit remains pending while the original cycle finishes.

The read-only follow-up will additionally freeze a descriptive Entity question without either service name. Its target return and correlated target-vector participation receive separate diagnostic verdicts for shared candidate C04. A named-vector success does not prove that descriptive discovery works; the original mandatory questions remain unchanged.

### P08 read-only attempt02 — actual publication defect surfaced

Run `pilot-p08-1016-02`, source `f57a64f`, remains **failed**:75 checks,11 public200 reads, zero new business inputs, workers or model calls. Corrected Entity evidence closure passed, as did A's native ANN→Entity→REFERENCES→Event participation. B's named-Entity proof failed. Final preservation/queue checks passed and shutdown was clean; all180 execution-source hashes match the commit. The original attempt01 remains failed for its two recorded reasons.

The provider actually returned all three B Entities, including OrionVault. Extraction logged OrionVault and payment reconciliation creation before the source Event's projection; only the later settlement-records Entity retained references. Spanner silently skips edge writes when an endpoint does not exist, and the extraction caller ignored the count. Later orphan cleanup deleted two unlinked Entities. Astra independently confirmed this source path; [#80](https://github.com/arunmenon/Engram/issues/80), under #63, tracks atomic Entity/source publication, same-result dependency retry and conditional orphan deletion. The exact observed write count was not instrumented; the RCA combines actual prompt/output, timing/final state and the recorded implementation path. No ANN/model-omission blame or successful B named-Entity claim is made.

A's no-name descriptive query returned its source Event but without target-Entity vector participation. This remains a C04 semantic-vector gap; arrival via another channel cannot rescue that proof. B's descriptive and absent-claim reads were not reached in attempt02. See [the bounded RCA](../review/spanner-compatibility/runs/pilot-p08-1016-02/entity-reference-rca.json). No direct graph repair will be used: after the fix, fresh affected journeys must pass through ordinary authenticated ingestion and workers.

Issue#79's cooperative-stop correction is implemented locally with26 focused tests passing after two decisive failures on the former code. It preserves the current awaited session and checks stop before starting later work; live P10 stop/restart verification is still pending, so the issue stays open.


### P08 publication correction — ready for live rerun

Issue #80 addresses the missing Entity/source links observed in P08. Entity publication now requires projected source Events and commits the Entity and its REFERENCES links together. A dependency retry reuses the primary extraction result. Orphan cleanup rechecks connectivity before deletion. Existing identity, origin, counts and reference properties are preserved; Neo4j creation defaults cannot overwrite a concurrent creator.

The final focused regression run passed 48 tests, affected-caller checks previously passed 96 tests (overlapping sets), and eight changed source files passed mypy. Astra accepted the bounded implementation recheck. These are local checks, not live proof. Original P08 attempts remain failed and unchanged. Fresh run `pilot-p08-1017-03` retains the same authored questions and named-Entity requirements, with fresh input identities. Descriptive discovery is separately reported and cannot substitute for a failed mandatory check.


### P08 attempt 03 — failed, retained

`pilot-p08-1017-03` ran source `3e412ea` through nine authenticated accepted inputs, ten ordinary workers and real Spanner. Both named native ANN → Entity → source Event checks passed, demonstrating the #80 publication correction in this slice. All 37 actual model calls returned and cooperative shutdown reported no errors. All 181 recorded source hashes match the executed commit. Final worker lags were not recorded after the early assertion; no zero-lag completion is claimed.

The attempt remains failed for two reasons. The absent-B query returned three identity-only references with lifecycle defaults and no source provenance (#82). Final conservation also found three retained A Summary scopes overwritten from agent to session because their IDs omitted scope (#81). No source ledger/owner or prior Episode membership was lost. The failed results, before/after states, raw log and source audit are retained. Its extra `descriptive_query` fixture field was not consumed by the harness, so this attempt supplies no descriptive Entity-query evidence.

Astra accepted bounded corrections: scope-qualified session/agent identities preserve legacy rows and Episode identity; unresolved reference outputs are explicitly labeled and omit unsupported lifecycle defaults. Reference integrity requires an actual accepted source projection declaring the exact stored/public edge, not arbitrary connectivity. Local checks: 60 consolidation/Memory tests; 57 retrieval/pilot tests before the final oracle addition; 20 final oracle tests including missing-label, business-property, wrong-edge and missing-receipt negatives (overlap is not additive). Three changed runtime files pass mypy. Fresh affected full-flow attempt 04 must prove live preservation; these local checks do not complete P08.


### P08 — bounded retrieval proof accepted

**What went in:** fresh run `pilot-p08-1017-04` ingested nine frozen inputs through the authenticated public dispatcher: a Change and failing test chain, unrelated control, trusted/untrusted equal-title Changes, and two tenant-specific service descriptions followed by session-end triggers. Both tenants used their retained databases and unchanged pack selections. Ten normal worker loops handled the deliveries; actual `gpt-6-luna` supplied extraction/summary results.

**What came back:** all 92 required checks passed across 22 HTTP requests. Exact retrieval preserved EXECUTES and RAN_AGAINST links, failed outcome and commit SHA. One-node/one-hop reads respected limits and reported truncation where required. Wording discovery found the authored artifact; the independent artifact paraphrase also found it. Seedless trust filtering excluded the uncorroborated untrusted Change unless explicitly requested, then labeled it. Both named service queries recorded actual indexed ANN results, matching Entity nearest hits, REFERENCES Event seeds and receipt-backed public Events. These prove channel participation, not unique causation or benchmark performance.

**References and absence:** the absent-claim query did not invent the named approval or absent identity. It could return legitimate broad recall, including three retained identity-only reference stubs. Those are now explicitly `reference_state=unresolved`; default lifecycle status is suppressed. The integrity check independently matches stored identity and declared edge to an accepted source projection. These references are not counted as observed business facts or invented direct provenance.

**Preservation:** final lags for all ten workers were zero; no pending deliveries or unexpected dead letters remained. The exact P04 negative record, owners, accepted sources and prior Episode membership were preserved. Legacy Summary scopes remained unchanged with the new scope-qualified identities. All 70 actual provider calls returned; cooperative shutdown had no errors. All 182 recorded source hashes match executed commit `87e7c06`. Astra accepted the bounded final evidence. #80, #81 and #82 are closed within their demonstrated scopes; umbrellas remain open.

**Still unresolved:** both extra descriptive queries omitted the Entity name and returned the correct source Event, but neither demonstrated named target Entity vector participation. They remain `C04-semantic-vector-gap`, tracked in #83. This does not establish general semantic Entity discovery. Attempts 01, 02 and 03 remain failed and unchanged; the scope corruption observed in attempt 03 is historical evidence, not retrospectively repaired.

**Repeat:** run the committed model-transition `inspect` preflight against the retained bindings, freeze fresh identities with `engram_pilot_retrieval_proof.freeze`, preserve these authored questions/oracles, then invoke `engram_pilot_first_run.py --journeys-only --journey-file <frozen JSON>`. The exact executed inputs, command arguments, HTTP replies, worker observations, native vector trace, state snapshots, source audit and issue reconciliation are in `docs/review/spanner-compatibility/runs/pilot-p08-1017-04/`. The fixture is `docs/pilot/pilot-p08-1017-04-journeys.json`. Reusing its IDs is a replay, not another fresh-run claim.


### P09 attempt 01 — harness failure retained

`pilot-p09-1017-01` executed source `75380a8` and stopped after one accepted A input. Its first read incorrectly used the PDLC artifact endpoint for Core+User+Memory, which correctly refused the unsupported intent with HTTP422. The attempt remains failed. All 182 source hashes match; four actual model calls returned, shutdown was clean, and final conservation checks passed. No tenant-isolation pass is claimed.

The harness now uses the supported session/agent-scoped `/v1/query/subgraph` Memory read with explicit `when` intent. That endpoint returns raw Goal identities, so frozen expectations use those raw IDs; artifact-style prefixes were also corrected. The collision descriptions, source/receipt checks, foreign-only positive/negative, replay, role and routing-refusal expectations remain unchanged. Seventeen local tests include actual Memory projection and retrieval for both tenant stories, rather than request-schema validation alone. Astra accepted the correction. Fresh attempt 02 requires live evidence; local tests do not complete P09.


### P09 attempt 02 — strict refresh-preservation failure retained

`pilot-p09-1017-02` executed source `6c25c17`. It passed interleaved same-identity/different-content reads, foreign-only positive/negative and exact duplicate receipts. The first admin request was correctly refused with HTTP403, but its before/after conservation proof caught one retained Episode temporarily changing `complete` from true to false during background Summary refresh. No oracle exception was added. The attempt remains failed, with its compressed before/after proof retained. Final source/owner/graph/Episode conservation recovered and passed; all 36 actual model calls returned and shutdown was clean. All 182 executed source hashes match.

Issue #84 fixes routine rematerialization: existing source/session/Summary validation remains first, then an already complete Episode must match every expected immutable property and the exact directed membership/evidence/Summary links. Overflow or mismatches cannot take the shortcut. Valid unchanged snapshots return without Episode or edge writes. Seventy affected Memory/consolidation/stop tests pass; mypy and Ruff pass, and Astra accepted the bounded review. Separate reads do not establish transactional immunity against concurrent deletion or repair. A fresh normal-worker P09 attempt is still required.


### P09 — tenant collision and refusal proof accepted

**What we sent:** `pilot-p09-1017-03` used source `8c7aa05`, with both tenant runtimes active on their retained Spanner databases. A and B received the same Event UUID, session, actor and Goal key, but different descriptions: a user-research workshop in A, a payment-settlement release in B. A third, B-only Goal supplied a positive foreign-data control. These are explicit Memory actions processed by deterministic graph projection; they do not require new model inference.

**What we read:** A's own Goal was read before B's write, then B's own Goal, then A again. Each returned its own description and exact accepted source position. The B-only Goal existed in B and was absent from A. Replays in each tenant returned the original receipt without material changes.

**What we refused:** ordinary API credentials could not read admin statistics (403); foreign/duplicate tenant headers and duplicate/missing/invalid credentials were rejected (401); reserved body routing fields were rejected (422); unsupported metrics and native webhook paths were refused (503). Each refusal was bracketed by saved before/after proofs for both databases. A rightful admin read worked (200); tenant/database query hints did not override A's credential binding. Bearer values were not recorded.

**Result:** 73 checks passed across 21 HTTP requests and three created inputs. All 11 compressed replay/refusal proofs re-audit as preserved. Ten final worker lags were zero; the exact P04 negative record remained, with no unexpected pending or dead letters. All 67 background provider calls returned; shutdown was clean. All 182 source hashes match the executed commit. Final source, owner, graph and prior Episode conservation passed. Astra accepted the evidence, and #84 is closed for routine refresh stability.

**Boundaries:** requests were deliberately interleaved while workers ran concurrently; this is not a simultaneous admission-burst or load benchmark. Internal domain/team/repo hierarchy policy remains parked in #49. The dispatcher ran on loopback, not an external cohort deployment. Attempts 01 and 02 remain failed. Separate reads in the Episode fast path do not promise transactional immunity against concurrent repair or deletion.

**Demo evidence and repeat:** `docs/review/spanner-compatibility/runs/pilot-p09-1017-03/` contains public replies, exact receipts, worker outcomes, state snapshots, compressed refusal/replay proofs, source audit and issue reconciliation. Freeze fresh identities with `engram_pilot_tenant_proof.freeze`, run the documented retained-binding preflight, then `engram_pilot_first_run.py --journeys-only --journey-file <frozen JSON>`. Do not reset either database or reinterpret replayed IDs as fresh admissions.


### P10 — frozen recovery verification plan (not yet run)

Six fresh inputs are frozen in `docs/pilot/pilot-p10-1017-01-journeys.json`. All admission and acceptance reads remain authenticated HTTP on retained Spanner; instance-only scheduling controls are explicitly recorded as test interventions.

| Probe | Observable pending/failure state | Required recovery |
|---|---|---|
| A Event projection held before processing | Accepted ledger record, enrichment pending, no Event node | Release projection; ordinary enrichment eventually writes the expected keywords |
| B Goal completion delivered before creation | Explicit `reference_missing` diagnostic, pending child, no Goal | Admit parent normally; observe active parent while child remains pending, then allow pending retry and require completed Goal |
| One marked A session extraction | Actual provider AuthenticationError from a known-invalid test credential; no applied receipt, delivery pending | B's positive read still works; old workers must join with A still pending/unapplied; fresh generation-1 extraction must succeed with the configured credential and exact original source window |
| Cooperative consolidation stop | One session job held at an explicit test barrier | Stop waits for release; current job completes, no later stopped-worker session begins; restart the same bindings |
| Stale startup | Recorded predecessor binding, not a new ownership transition | RuntimeFencedError before processing; exact owners and all table fingerprints unchanged |
| Recovered replays and reads | Exact accepted positions and recovered User receipt | A source Event/B completed Goal publicly present with exact provenance; User export contains the verified receipt and remains unchanged across duplicate replays |

Only the marked actual AuthenticationError is an expected provider failure; every other call must return. The configured model remains `gpt-6-luna`, with no artificial call/spend cap and no global credential change. Context is restored in `finally`. Pending retries are temporarily skipped by returning control so B can process its parent; delivery counts are not edited and the child is not acknowledged early. All barriers release on failure. The consolidation barrier proves cooperative completion of a held session job, not interruption of network I/O. Final conservation, exact P04 negative, zero pending/lag, source audit, Astra evidence review and issue reconciliation remain mandatory.

The bounded harness/source review is accepted; 43 focused tests and 11 existing harness tests passed, with six final control tests passing after integration. These local counts overlap and are not live recovery evidence.

### P10 — cooperative recovery proof accepted

Run `pilot-p10-1017-01`, executed source `9f0a337`, passed all 64 checks with six newly accepted inputs and twelve hashed intermediate snapshots. Of44 actual gpt-6-luna calls,43 returned and one deliberately marked generation-0 call received a real AuthenticationError. The failed extraction remained pending and unapplied when old workers joined; generation1 then produced the verified receipt from exactly the accepted source window. Public User export and source-backed subgraph reads expose the recovered result.

Delayed enrichment remained pending before its Event existed, then its annotations appeared after normal projection. A Memory completion arrived before its parent, stayed deferred, and converged after parent creation. Tenant B remained publicly usable during A's provider failure. Cooperative stop waited for a held ordinary consolidation job to finish and did not start a later stopped-session job. This does not prove forced-crash or interrupted-network recovery.

Both recorded predecessor bindings were rejected with RuntimeFencedError before effects. Exact owner records and all table fingerprints stayed unchanged. Replays retained original positions, both database snapshots were byte-identical, and public User outputs/receipts stayed stable. All ten final worker lags were zero, shutdown had no errors, and final source/retained graph conservation passed. A separate audit matched 183 execution source hashes against the committed revision and validated all 12 raw snapshot hashes. Astra accepted the bounded evidence; #79 is eligible for closure. Broader umbrellas remain open.

Evidence: [results](../review/spanner-compatibility/runs/pilot-p10-1017-01/results.json), [source audit](../review/spanner-compatibility/runs/pilot-p10-1017-01/recorded-source-audit.json), [stale-startup proof](../review/spanner-compatibility/runs/pilot-p10-1017-01/stale-startup-owner-table-proof.json), [Astra review](../review/spanner-compatibility/skill-reviews/2026-10-16-pilot-resume-astra.md).

### P11 — clean-checkout technical reproduction

Run `pilot-p11-1017-01` executed preparation commit `d9db077` in a clean detached checkout. It passed all 69 checks: eight authenticated HTTP requests, three newly accepted inputs,24 actual gpt-6-luna calls all returned, ten zero final lags, clean shutdown and final conservation. B's Change and its source were publicly visible before A's foreign-source exclusion. A's explicit Goal and exact source were returned through the supported Memory read. The added library Change had its independently declared identity/title/status/source and used the existing JSON runner without engine changes.

The published command block was extracted from the pinned team walkthrough and executed with only the documented Python/run-ID substitutions plus the local gcloud PATH. It explicitly reused the foundation-gate Python environment; it did not test fresh dependency installation. The post-run import audit verified 142 project modules came from the pinned checkout and matched committed bytes; package names/versions and Python details are retained. A fresh process matched 183 execution source hashes, verified all final checks and the three accepted inputs, and confirmed no tracked checkout source changed. It also compared the base and extended JSON: the original two inputs are unchanged and exactly one library story was added. This is agent technical reproduction, not an independent human/team run.

Evidence: [results](../review/spanner-compatibility/runs/pilot-p11-1017-01/results.json), [fresh-process audit](../review/spanner-compatibility/runs/pilot-p11-1017-01/fresh-process-audit.json), [import audit](../review/spanner-compatibility/runs/pilot-p11-1017-01/checkout-import-audit.json), [executed published commands](../review/spanner-compatibility/runs/pilot-p11-1017-01/published-command-execution.sh), [base fixture](../review/spanner-compatibility/runs/pilot-p11-1017-01/base-journeys.json), [extended fixture](../review/spanner-compatibility/runs/pilot-p11-1017-01/extended-journeys.json). Astra accepted the technical evidence and independently matched all 142 imported-file hashes. Issue reconciliation updates #63/#34/#39/#41/#42/#43 without closing their broader scope. Independent human repetition remains an external handoff milestone.

### P12 — final coverage and stakeholder handoff

The approved P01–P12 engineering batch is complete within its recorded limits. The [team walkthrough](team-walkthrough.md) supplies the demo sequence, exact reproduction prerequisites/commands and a runnable fresh-process audit. The [coverage map](coverage-map.md) and its JSON source cover all 25 A candidates,24 B candidates and18 shared probes. These67 rows are not67 passing journeys. Many catalog stories have component/partial proof; diagnostic and external prerequisites remain explicit. Astra corrected overbroad C03/C06 full labels to partial and accepted the final bounded claims.

The27-page HTML suite now shows each selected story's observed result and remaining boundary. Real-browser verification navigated every page, exercised all 67 catalog entries and both tenants' four worker teaching stages, and checked the reproduction page at 390px with no horizontal document overflow. Desktop/mobile screenshots were visually inspected. Eight local pilot-chapter links resolve. This is presentation/interaction evidence, not a new runtime journey or every-page mobile certification. See [quality findings and comprehension checks](handoff-quality-review.md) and [rendered evidence](../../output/playwright/p12/guide-validation.json).

GitHub reconciliation found stale open bug records #64/#66/#68. Astra compared each exact acceptance criterion with current source, regression review and already accepted corrective live evidence: owner-scoped reads (entry06/P03), pack-only JSON mode and source-backed model proposals (entry06/P01/P02), and ledger-content Summary hydration (P07). Each received evidence and was closed for its bounded defect. #79 cooperative stop was closed after P10; #80/#81/#82/#84 were already closed after their corrective proof. #83 descriptive Entity discovery remains open. #63 and broader #34/#39/#41/#42/#43 remain open. Hierarchy #49, ANN/load #48 and earlier #13/#14/#18/#19 are not closed by this batch. Exact comments and rechecked states are in [final issue reconciliation](final-issue-reconciliation.json).

**Separate verdicts:** engineering milestones complete with retained failures and known limits; stakeholder demo walkthrough delivered as a versioned artifact, synchronous attendance/acceptance not claimed; agent technical reproduction passed, independent human/team repetition not performed; external cohort deployment not performed. Data was retained, with the exact P04 negative delivery and historical failed-run evidence preserved. No migration, direct graph repair, arbitrary reset or broader forced-crash guarantee was introduced.

Everything lands on the one canonical branch `feature/engram-memory-episodes`. P10 executed 9f0a337; P11 executed d9db077. Final documentation changes introduce no new runtime behavior. Publication is verified against the remote branch after commit.

### Post-pilot issue85 — historical trace and approval integrity

An independent test exposed a gap beyond the prior bounded B03 checks: admission removed an explicitly requested old design and stranded its approval context. The [issue85 verification](issue85-verification.md) records the cause, deliberate trace/history decision, retained failures, 165 affected local tests and 95 final live checks across eight fixed public queries. Astra accepted the correction; no v2 approval is invented. These additional checks extend the recorded evidence rather than retroactively changing the earlier pilot coverage into a universal pass.

Customer-owned deployment portability is separately tracked in [the deployment brief](spanner-deployment-portability.md), issue86 under #34. Current settings/SDK selection are configurable; pilot operators remain deliberately Portiq-bound, and an actual non-Portiq customer-project proof is pending.
