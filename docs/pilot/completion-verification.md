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

The stale confirmation is expected to be admitted (201), then fail projection with `memory_status=conflict`, `memory_reason=state_conflict` and exactly one projection dead letter. Its immutable embedded acceptance, tenant/database/binding, consumer, Event identity and position must match the admitted source; target properties and all incident evidence/lifecycle edges must remain identical. All other deliveries must drain normally, with zero pending and lag. The negative audit record remains retained. Later milestones must explicitly admit this verified negative using its proof; the current baseline guard rejects any preexisting dead letters.

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

These are the executed coordinates, not an instruction to submit the same identities again. A new write reproduction needs fresh run/Event/owner/session identities, a fresh baseline and explicit admission of the preserved negative-test proof. The runner currently rejects preexisting dead letters; that intentional guard must be extended before the next retained run. Independent human reproduction remains a later milestone. Cloud Monitoring export still reports 403; this run does not establish monitoring export, automatic prose inference, calibrated confidence or full pilot readiness.
