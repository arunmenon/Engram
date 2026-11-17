# AI-native onboarding: milestones and verification plan

Status: partially implemented; current evidence and remaining acceptance gates are below.
Date: 2026-11-05.
Owning proposal: `docs/ai-native-onboarding-feature-brief.md`, revised-scope section.
Independent design review: `docs/review/2026-11-05-ai-native-onboarding-feature-review.md`.

## Start here — execution handoff for a new goal thread

Workspace: `/Users/arunmenon/projects/Engram`. Baseline branch:
`feature/engram-walkthrough`; recorded HEAD `27b4ba861814163d4292a950ddaae484a4282d82`.
The tree has extensive pre-existing uncommitted/untracked work. Check current state;
do not reset, bulk commit or assume HEAD identifies the implementation. Read applicable
AGENTS.md instructions. User authorization: execute this plan sequentially, with a
user UI-review gate after each visible milestone. Two simulated browser personas are
explicitly authorized; real human recruitment is not required.

Precedence: latest user instructions, then the user-directed amendments and M0 verified
corrections in this document, then milestone details. The original human-study wording
retained in sections below is superseded; do not stop to recruit participants. Likewise,
do not repeat the superseded claim that every relationship-free question is unsupported.

Current state (reconciled with Fable verification, 2026-11-06):
- M0 is PARTIAL. The historical prepared PDLC 111-pass result is not reproduced by
  the fresh 110-pass/1-failure memory replay. Diagnosis now shows a backend difference:
  the historical run used Spanner, which detects changed-content conflicts; memory
  returns duplicate for an existing event ID. Current-engine Spanner revalidation
  remains unperformed. See the 2026-11-06 demo-blockers remediation record.
  Technical preparation and simulated baseline exist, but expectations
  remain author-reviewed, procurement has no runnable pack, and historical runs are
  not a current cross-domain baseline. Do not repeat the earlier completion claim.
- M1a safe request preparation was independently accepted; self-serve issue resolution
  was not. Fable independently accepted safe, recoverable, single-submission request preparation
  on fixture agents in `docs/review/2026-11-06-m1a-remediation-fable-re-review.md`.
  Full self-serve resolution and live reasoning are not accepted by that review.
- M1b live-provider technical evidence exists; UI review remains pending. See
  `output/playwright/ai-native-onboarding/M1b/live-northstar/README.md`.
  No additional live-provider run was made for the M1a recovery fixes.
- The current bounded disposition and exact re-review steps are in
  `docs/review/2026-11-06-m1a-fable-remediation.md`.
- Next: re-review the corrected M1a interactions. Do not advance milestones, treat
  simulated operators as human research, or label fixture explanations as live reasoning.
- Preserve original drafts, sources, packs and expected answers. This remediation uses
  isolated fixture copies on port 8105; no Spanner or deployment acceptance is claimed.

Read these handoff artifacts:
1. `docs/ai-native-onboarding-feature-brief.md` — revised scope; original proposal is historical.
2. `docs/review/2026-11-05-ai-native-onboarding-feature-review.md` — independent design review.
3. `output/playwright/ai-native-onboarding/M0/baseline-20261105/README.md`,
   `manifest.json`, `pytest.log`, `capability-probes.json`, `crm-workbench.json`,
   `crm-result.json` — baseline evidence, exact identities and remaining limits.
4. `output/playwright/ai-native-onboarding/M0/personas/summary.md`,
   `novice/report.md`, `experienced/report.md` — simulated findings and screenshot links.
5. `docs/review/2026-11-05-onboarding-remediation-disposition.md` — earlier delivered
   safeguards to reuse, not proof that this plan is already implemented.

Observed UI baseline defects: historical success competes with stale warnings; pool
availability conflicts visually with historical cleanup; generic next action obscures
missing evidence; Apply answers is ambiguous; rejection checks say expected acceptance;
procurement questions lack a story overview. Preserve distinctions between copy defects,
actual engine behavior and unexecuted cases when fixing these.

Known local entry points (verify availability rather than assuming running):
`http://127.0.0.1:5174/workbench.html`, backend port 8101. Operator token file
`.workbench/dev-token`: read directly into authentication, never print or record it.
Preserve `.workbench/drafts.sqlite3` and existing accepted drafts. Use isolated copies
for destructive/error scenarios. Existing browser environment:
`/tmp/engram-video-venv/bin/python`; repository test tools under `.venv/bin/`.
Current sandbox capacity may be unavailable: don't silently substitute memory and
claim Spanner acceptance. Agent service configuration must not be changed casually.

No Fable connector was available during preparation. If still unavailable, produce
an exact review handoff and evidence package; mark independent review pending until
returned. Simulated personas and implementation self-review do not substitute for it.
An older blocked Spanner goal belongs to the original thread; a new goal thread can
use this document without marking that old objective complete.

## M0 verified corrections (2026-11-05)

Current executable probes supersede broader engine-limit statements below. With the
copied incident fixture and its supplied seed, evaluation with no explicit intent
passes, including after removing domain edges and intents. A named absent intent is
rejected. Thus relationship-based **intent eligibility** must not be described as a
ban on every relationship-free node lookup. This does not prove arbitrary questions
or scalar/count answers are supported. See `output/playwright/ai-native-onboarding/M0/baseline-20261105/capability-probes.json`.

Procurement synthetic intake files already exist under `docs/examples/procurement`;
a runnable pack and its acceptance evidence have not been verified by M0. Earlier
statements that procurement material does not exist are superseded by this inventory.


## Operator simulation amendment (user-directed)

The user replaced the requirement to recruit two human operators with two simulated
personas exercising the real UI through computer use. This amendment supersedes
human-participation requirements in M0, H1 and M6 below; those original criteria remain
as historical design context, not execution blockers.

- Persona A: first-time internal tenant operator, business-literate, unfamiliar with
  Engram terminology. Persona B: experienced operations administrator managing tenants,
  familiar with source systems and approvals but not Engram syntax.
- Separate agent runs use only rendered UI for task decisions, not implementation
  code or each other's findings. Browser automation is an acceptable fallback when
  native computer use is unavailable. Record the actual interaction mechanism.
- Both attempt the same three baseline tasks: interpret a visible failure and its
  next action; distinguish inspection from applying a change; find how unsupported
  questions are explained. Missing failure/limitation scenarios are recorded as
  unavailable, never counted as passes. Preserve screenshots and action logs.
- H1 repeats those tasks after M1 on matching fixtures. Resolve observed critical
  confusion before M2. This is a simulated usability gate, not a human-comprehension
  result. A later real human study is optional additional evidence, not a prerequisite
  imposed on the user for this implementation.
- M6 reports technical verification, simulated usability findings, independent review
  and the user's milestone UI acceptance separately. Never describe agent personas as
  actual operators or independent human study participants. If no human study occurs,
  report “technically verified; simulated usability reviewed; human study not performed”.
  The previous label “technically verified; operator study pending” applies only when
  a real study is explicitly scheduled and remains pending.
- The user's post-milestone UI review gate remains in force. Simulated personas do
  not approve an ontology or product change on the user's behalf.

## Realistic scenario depth (user-directed)

The small incident example remains a focused regression case, not the main evidence
for operator usability. Simulated personas must also inspect involved business stories.
Use existing PDLC journeys and HarborWorks procurement materials as the substantive
exercise; distinguish inspecting a saved result from executing a fresh run.

### Procurement: purchase request through invoice evidence

Existing synthetic inputs in `docs/examples/procurement/` describe seven entity types,
seven relationships, 29 event records and seven frozen node-set questions. The three
stories cover a clean purchase, partial deliveries with invoice quantity mismatch,
and repeated document IDs across US/EU companies within one tenant. Events also
exercise retries, malformed input and a late rejection after approval. Keep those
facts, original expectations and source-assessment boundaries unchanged.

Operator tasks must span: follow a request to its order, line, receipts, invoice and
source match assessment; explain why both partial receipts remain; inspect the
rejected state transition without calling it ingest rejection; distinguish companies
with repeated IDs; identify which claim is supplied by the source and which graph
behavior Engram actually verifies. Matching arithmetic and payment execution are not
implemented by this pack and must not be implied.

The existing seven retrieval questions are primarily one-hop. Do not label them
multi-hop proof. Add separately versioned candidate journey checks/questions for
supported multi-hop paths only after validating engine capability and reviewing their
expected node sets against the event ledger. Unsupported aggregate/money questions
must receive an honest limitation rather than a fabricated answer. No original oracle
may be weakened to accommodate generation or retrieval.

### PDLC: connected delivery stories

Use existing frozen prepared stories to inspect connected events, checkpoints,
relationships, state transitions, provenance and retrieval expectations. Include a
failure/rejection or trust story as well as a successful path; select from actual
available UI entries. Save the chosen story ID and existing event/check counts.
Do not equate a large schema diagram with verified coverage.

### Evidence standard

Each simulated persona reports the story it inspected, task actions, visible inputs,
expected versus observed results available in the UI, and whether execution actually
occurred. Complexity must exercise meaningful operator decisions, time and exceptions,
not simply increase node count. New fixtures or generated packs require separate
validation and cannot be counted as current working UI capability until run. Carry
these richer tasks through M2–M6; retain small fixtures for targeted failure tests.

## Domain-team self-serve assessment framing (user-directed)

The user clarified that operators come from the respective domain teams. Evaluate
with a delivery lead, procurement specialist and customer-operations specialist who
understand their business rules but not Engram syntax. Self-serve means resolving
supported authoring/review/testing tasks without an engineer translating the UI;
it does not mean silently approving business assumptions or deploying production.

Test four questions: is the clarification understandable; can the operator answer
naturally; does preparing a request preserve meaning and make the next action clear;
do adding material, returning and leaving unresolved work without hidden effects?
Use actual browser interactions and distinguish fixed-response simulation from
live-agent reasoning. The current assessment uses PDLC and CRM pack snapshots plus
a procurement conceptual draft, not a claimed working procurement pack.

Record operator-facing evidence separately from platform setup prerequisites
(credentials, configured provider, pack catalog and sandbox capacity). Production
activation remains outside this workbench. User UI acceptance and M1b live-agent
verification are not replaced by persona simulations.

## Goal and boundaries

An operator can understand a tenant's proposed ontology, resolve supported decisions,
explain failures and test business questions without writing engine instructions.
The same workflow must operate on different supported domain packs. The agent
explains and proposes; Engram validates and executes; the operator accepts changes
and expected outcomes. Human comprehension must be measured separately from tests.

Keep the existing six-step navigation. Use existing authenticated REST APIs, typed
React components, author jobs, revision requests, validators and sandbox runner.
Do not introduce another agent framework, a general chat surface, a four-page rewrite,
branching execution, voice/PDF ingestion or source-version impact analysis.
Do not extend retrieval to scalar/count answers or fabricate relationships for
relationship-free packs. No production activation, recording or deployment is implied.

One parent objective, nine implementation milestones and an early human-feedback gate. Each milestone delivers visible
behavior with evidence; it is not complete merely because its helpers compile.
M0 -> M1a -> M1b -> H1 (human-feedback gate) -> M2a -> M2b -> M3 -> M4 -> M5 -> M6. Reuse earlier evidence only when the relevant
code and fixture identities still match. If a milestone exposes a prerequisite,
record the concrete failure and smallest correction before widening scope.

## Verification rules shared by every milestone

- Record HEAD and an exact changed-file digest manifest: HEAD alone cannot identify
  this heavily uncommitted tree. Record engine, pack, fixture and scenario identities.
- Keep input fixtures and operator-reviewed expectations separate from agent output.
  Never regenerate expectations to make a failing run pass.
- Save commands, results, API assertions and browser evidence under
  `output/playwright/ai-native-onboarding/<milestone>/<run-id>/`; redact credentials.
- Use focused regression tests and existing checks appropriate to the touched files.
  No test-count target substitutes for the named acceptance cases below.
- Mark evidence as automated, live-provider, real-Spanner, browser or human study.
  A fixture agent proves orchestration; it does not prove live agent behavior.
- Track status as planned / in progress / implemented / verified / independently
  reviewed. Human-study pending is a separate visible field, never silently passed.
- Explain citations establish traceability, not semantic truth. A plausible but
  unsupported explanation must be caught in review and adversarial fixtures.

## Post-milestone UI review gate

Required by the operator: after every milestone that changes visible behavior, review
how the feature looks and works before starting the next implementation milestone.
A backend-only milestone records “no visible change” and verifies its existing UI
entry point where applicable; do not invent a cosmetic deliverable.

For M1a, M1b, M2a, M2b, M3, M4 and M5:
1. Exercise the feature in the actual browser against the milestone build. Capture
   before/after views where applicable and a short ordered walkthrough showing the
   operator's task, action and result. Label fixture-agent versus live-agent evidence.
2. Show relevant normal, loading, empty, error, cancelled and stale states. Check
   information hierarchy, plain language, density, next-action clarity, preservation
   of typed input, keyboard/focus behavior and appropriate viewport layouts.
3. Check that explanation, proposed change, applied revision, planned effect and
   observed result are visually distinguishable. Review wording and examples for
   accidental domain-specific assumptions. Technical identifiers belong in details.
4. Publish a small review package: screenshots with captions, what changed, known
   limitations, defects with severity and an accessible local UI link when running.
   Screenshots alone do not prove the interaction works.
5. Present that package to the user for UI review before moving to the next milestone.
   Record their disposition and address requested changes. Do not count silence as
   acceptance. If a separate Fable visual review is requested, provide this same
   package and mark it pending until returned; do not claim an independent review
   from the implementation agent's own inspection.

Record UI review as pending / changes requested / accepted, with reviewer and evidence
link, alongside the milestone ledger. A milestone can be technically verified while
its UI review remains pending. M6 includes a final consistency review across the full
flow. This gate supplements H1 and the final human study; visual acceptance is not
proof of unassisted comprehension.

## M0 — Freeze the baseline and prepare honest acceptance fixtures

Objective: make the implementation and its verification reproducible before changing
behavior. This is a bounded inventory and fixture task, not a platform audit.

Work:
- Inspect current affected code and instructions; reconcile changed files against
  the design review. Preserve unrelated changes and prior immutable reviews.
- Reproduce the Northstar admission-rule issue from saved synthetic material in an
  isolated draft/fixture. Do not damage an accepted live draft to reproduce it.
- Record actual authentication, author-job, validation and sandbox interfaces to reuse.
- Verify the no-intent evaluation path and relationship-free behavior with focused
  executable checks; distinguish engine limits from UI restrictions.
- Inventory actual loadable packs: PDLC, Northstar incident material and CRM pack.
  Northstar is not a payment-transactions fixture. Procurement does not yet exist.
- Prepare CRM intake/events/contracts and answers; add small
  relationship-free/no-lifecycle, incomplete-evidence and wrong-answer variants.
  Do not represent these new fixtures as pre-existing production domains.

Acceptance:
- Fixtures have provenance, expected supported/unsupported behavior and a manifest.
  Each expectation records author, reviewer name/role, review date and evidence basis.
  If only the implementer or generating agent has reviewed it, label it author-reviewed;
  do not call it independent. A named reviewer other than the author must review
  expectations before they are used as independent acceptance evidence.
- Capture a baseline with two operators on the current flow, before UI changes:
  (1) explain the admission failure and identify a next step, (2) distinguish an
  explanation from applying a change, (3) recognize an unsupported question without
  inventing a relationship. Record the task script, help, completion, technical terms
  supplied and errors. Preserve the same tasks for H1; disclose repeat-task learning.
- A limitation table names event input, payload contracts, relationship-dependent
  artifact intents, node-set answers and lifecycle requirements based on current checks.
- The admission-rule failure and its desired business explanation are recorded.
- Existing targeted checks have a baseline; pre-existing failures are listed separately.

Evidence: baseline manifest, fixture inventory, focused checks, sample failure capture.
Exit: scenarios have known inputs, explicit expectation-review status and a captured
operator baseline. If participants are unavailable, record baseline pending rather
than substituting an agent simulation for it.

## M1a — Read-only explanation with a fixture agent

Objective: deliver the smallest usable explain path for existing validation problems
and limitations, verified deterministically before a live provider run.

Work:
- Assemble bounded context server-side under existing tenant/draft authorization:
  selected problem or limitation, relevant pack facts, source excerpts and engine output.
- Refuse the call before provider dispatch unless the draft's current data policy
  permits sending that material to the configured provider. Authorization and consent
  are separate checks. Test absent/revoked consent with zero provider invocations.
- Return typed `supported`, `unknown` or `engine_limit` answers with validated evidence
  references and an optional proposed instruction. Unsupported answers name missing
  information; they do not invent an explanation or a relationship.
- Display the answer beside its subject. “Propose this change” fills the existing
  revision box only; no submit, authoring, approval or expectation change is automatic.
- Bind to tenant, draft, revision and proposal digest. Any draft save invalidates the
  answer and its proposed action, including source edits. Check the fence again on
  completion and before using an instruction. No context fingerprint or selective
  invalidation in this slice. Do not save the answer in a way that bumps its own
  draft revision; transient UI answers may be discarded on reload.
- Capacity decision: synchronous explain requests, separate from the two author-job
  slots, with a dedicated non-queuing cap of two in-flight explain calls per service
  process and one per tenant. Excess requests receive a retryable busy response.
  Use a 30-second total deadline including at most one invalid-response retry, and
  an upstream timeout. Release capacity on every exit; suppress stale/cancelled output.
  Document that this is process-local admission control, not a distributed guarantee
  or a guarantee of provider quota isolation. Do not add a distributed scheduler.
- Move the cheap navigation fixes here: banner and readiness use the same next action
  and destination; cancelled author jobs show an explicit message. Reuse current
  progress display; no new progress orchestration. New controls must support keyboard
  use, visible focus and accessible status announcements.

Acceptance:
- Fixture-agent responses cover supported, missing evidence, conflicting evidence,
  engine limit and invalid citation cases; malicious source text grants no authority.
- Read-only calls leave pack, acceptance, validation and approval state unchanged.
- Wrong tenant/draft/subject is rejected; a save during a request makes its result unusable.
- Missing/revoked provider consent prevents dispatch. No consent bypass via explain.
- Concurrent explain calls respect both caps and do not consume author-job slots;
  verify an author job can be admitted while explain capacity is occupied.
- Timeout, busy and repeated clicks preserve prior accepted work and typed input.
- The proposed instruction can be inspected without submitting it.

Evidence: fixture-agent API tests, focused UI integration tests and browser capture.
Exit: a read-only explain path works with consent, revision fencing and bounded capacity.

## M1b — Live Northstar run and failure recovery

Objective: exercise the M1a path with a real agent and close observed failure behavior,
without adding a new conversation state model.

Work and acceptance:
- Run the isolated Northstar admission-rule case with provider permission. Record the
  exact operator-typed request and generated instruction accepted by the operator.
  Automated proxy: typed request contains no engine rule identifier, generated
  instruction contains the supported identifier, and the subsequent existing author
  workflow yields a validated correction. This does not prove human comprehension.
- Record retry attempts and outcomes. Cover provider outage, malformed output, total
  timeout, cancellation, reload and source/save races; no loss of the accepted proposal,
  prior review or typed revision request. Reject late responses, including after consent
  changes. Do not promise remote provider work stopped unless that is demonstrable.
- Confirm actual latency fits the initial deadline; a needed adjustment must cite
  observed timings and preserve a finite deadline and capacity bound.
- Complete explain -> inspect proposed instruction -> explicitly submit through the
  existing author path -> inspect validation. Separate fixture and live evidence.

Evidence: live request/instruction pair, validation result, browser capture and focused
failure checks. Exit: demonstrated live path and recoverable failure behavior.

## H1 — Formative operator gate before M2

Two operators perform the same three M0 tasks on the new flow without coaching.
Record each person's baseline and new result, help required, supplied engine terms,
wrong actions and their explanation of what changed. Repeated-task learning must be
reported; this small formative comparison is not a statistical usability claim.

Pass only when both can identify the next action, distinguish explain from apply,
and recognize the unsupported case without fabricating a relationship or receiving
engine syntax from the facilitator. Any failure triggers a targeted M1 fix and repeat
of the affected task before M2 starts. If operators are unavailable, H1 is pending;
automated browser tests cannot pass it. This is an explicit human-participation gate,
not an invitation to build the rest while waiting.

## M2a — Make pack selection catalog-driven

Objective: remove the backend PDLC restriction before testing cross-domain review UI.

Work:
- Replace the PDLC-only Content literal and capabilities list with a server-owned
  catalog of actually loadable packs. Preserve saved-draft compatibility, dependency
  and collision checks. No marketplace, arbitrary remote loading or new registry service.
- Use M0's adapted CRM contracts/events and record expectation-review status.
- Derive starter examples from supported contracts or omit the action. Do not silently
  use PDLC for a missing authored snapshot. Make lifecycle confirmation conditional
  on actual lifecycle declarations, on the server as well as in UI copy.

Acceptance: old PDLC drafts still load; CRM selection composes and passes tenant-bound
admission with its added contracts; authored Northstar still loads; unavailable packs,
missing dependencies and name collisions fail clearly; no-lifecycle packs do not
require lifecycle confirmation. Verify all affected Content/API/frontend carriers.

Evidence: compatibility and admission checks plus a small selection browser test.
Exit: backend selection and fixture prerequisites for M2b are satisfied.

## M2b — Make review readable and cross-domain

Objective: operators can inspect and question an ontology through the existing steps,
without PDLC-specific defaults or a wall of confirmations.

Work:
- Extend the same explain capability to selected nodes, edges and pack-level questions.
- In step 3, group “What the agent understood” separately from “Decide and accept”.
  Use progressive disclosure for citations and engineering details without hiding blockers.
- Place trusted-producer configuration in a clearly named setup section rather than
  among expected answers. Keep six top-level steps and preserve server trust gates.
- Preserve M1a's aligned banner/readiness behavior. Explain supplied-example runs
  versus saved-story runs at their entry points.
- Consume the M2a catalog and lifecycle applicability; do not repeat that backend change.

Acceptance:
- PDLC and CRM can use the same selection/review components; authored Northstar remains valid.
- CRM contract prerequisites are met before claiming tenant-bound admission success.
- No-lifecycle input does not force an irrelevant lifecycle attestation.
- Pack dependencies and name collisions are still checked across the selected bundle.
- Questions about a selected element cite its own revision/evidence; unsupported
  domain questions are labelled honestly. No domain-specific conditional is needed for explanation.
- Reopen, back/forward, polling and conflicts preserve input; next action has one meaning.

Evidence: compatibility checks for saved drafts, browser journeys on PDLC/CRM/Northstar,
unsupported-case browser capture, keyboard and focus checks on changed screens.
Exit: cross-domain behavior demonstrated, not inferred from generic component names.

## M3 — Help operators choose with planned consequences

Objective: an operator can resolve an identity or lifecycle decision using their own
samples and see what each supported option means before requesting a change.

Work:
- Add decision scope to the same explain endpoint and UI; no separate agent workflow.
- Present neutral options and evidence, without a default “recommended” badge.
- Where supported, validate candidate options through the existing engine planner.
  Show record/relationship/state differences labelled “planned, not executed”.
  Do not store competing branches or run comparative sandboxes.
- Preserve conflicting source excerpts and the operator's decision in review evidence.
  Accepted decisions enter the existing revision workflow and its acknowledgement gates.

Acceptance:
- An identity collision example shows deterministic separate-versus-merged records.
- A lifecycle option shows only transitions exercised by the supplied samples.
  If coverage is missing, report “cannot be planned from these samples”. A pack with
  no lifecycle does not require this decision.
- An option that cannot be planned is unavailable with a reason, not a simulated result.
- Choosing an option does not silently apply the pack or replace reviewed answers.
- Source edits or a new proposal invalidate obsolete options and planned effects.

Evidence: planner/API tests and browser decision walkthrough using reviewed samples.
Exit: operator can state the consequence before choosing; automated tests verify the
numbers, while comprehension remains a human-study item until M6.

## M4 — Explain failed checks and expose story coverage

Objective: the operator can distinguish a pack problem, a data problem, an expectation
problem and an unsupported question, then see what has actually been tested.

Work:
- Add failed-check scope to the shared capability with event, matching rule, reviewed
  expectation, observed output and deterministic failure guidance.
- Keep deterministic guidance first. When cause is ambiguous, say what evidence is
  missing. The agent never rewrites the oracle to pass the run.
- Add a deterministic coverage list inside the existing story workspace for events,
  transitions/rejection scenarios and questions. Distinguish no check, defined check,
  executed check, passing check and stale result; “passing” is not exhaustive coverage.
- Reuse existing outline/generate/review for an uncovered item. Operator reviews each
  assertion; empty, impossible and vacuous negative checks cannot count as proof.

Acceptance:
- Wrong expected account, unsupported scalar question, bad projection and missing
  source evidence produce appropriately different guidance or explicit uncertainty.
- Corrections identify which checks need rerunning and preserve approved expectations.
- Story snapshots stay pinned; a pack change makes old coverage visibly stale.
- An event merely appearing in a story is not reported as behavior fully verified.
- Reuse the remediation's existing negative-assertion type checks and per-check
  review. Verify the remaining semantic/vacuity gaps; extend only where a concrete
  case bypasses those checks. Impossible assertions are rejected or flagged, not celebrated.

Evidence: check-scoped API cases, coverage calculation tests and a browser failure-to-rerun journey.
Exit: one passing and one failing story are understandable with linked observed evidence.

## M5 — Add thin intake assistance

Objective: reduce intake busywork without pretending the agent can infer missing
business facts reliably before validation.

Work:
- Suggest source categories that the operator can correct; preserve original material.
- Surface deterministic sample inventory: event types, available fields, observed
  keys/collisions and missing values. Observed samples are not proof of global uniqueness.
- After proposal validation, explain missing-information items from actual engine
  problems and clarification questions. Reuse the shared explain/decision machinery.
- Preserve sensitivity checks before provider calls and existing per-tenant permissions.

Acceptance:
- Three mixed source inputs can be categorized, corrected and retained across reload.
- Missing relationships lead to a business clarification or unsupported status, not invention.
- Conflicting documents remain visible and require an explicit decision.
- No provider call precedes the required sensitivity consent.
- Known sample collisions are displayed correctly, and absence of collisions is qualified.

Evidence: deterministic inventory tests, browser incomplete-input recovery and a bounded
live-provider case distinct from the complete-input case.
Exit: the operator reaches a supported proposal or an honest unresolved state without
being asked to supply engine syntax.

## M6 — Verify the whole experience and obtain independent closure

Objective: demonstrate the intended operator behavior end to end and report limits
honestly before calling the improvement complete.

Technical acceptance:
- Run affected backend/frontend suites, typing, build and architecture checks required
  by the repo; record unrelated failures without relabelling the whole suite green.
- Use real browser/computer-use journeys: intake -> proposal -> explanation -> decision
  -> revision -> reviewed expectations -> sandbox -> failure explanation -> rerun -> handoff.
- Exercise PDLC, adapted CRM and Northstar with the same controls. Include no-lifecycle,
  relationship-free, incomplete-evidence, wrong-answer and source-edit-during-call cases.
- Use the existing real Spanner sandbox integration for compatible positive journeys;
  record database slot, pack/engine identities, observed results and verified cleanup.
  Do not claim Spanner coverage from memory runs or use production tenant data.
  Pool unavailable means that acceptance row is pending, never silently fallback-passed.
- Exercise live agent behavior on complete and incomplete non-PDLC evidence. Record
  attempts, repairs, operator help and cost/latency if available; distinguish agent
  recovery from an engineer supplying a fix.

Human acceptance (cannot be replaced by automated browser operation):
- Recruit 3–5 operators unfamiliar with the workbench; rotate available domains.
- Ask them to explain identity and its source; ask a read-only question; choose using
  planned consequences; reject a wrong expected answer/vacuous check; recover from a
  failed request; recognize unsupported retrieval; distinguish tested/approved/activated.
- Record unassisted completion, help requests, wrong approvals, lost input, recovery
  and technical vocabulary they had to supply. No facilitator coaching during a task.
- Any observed critical wrong approval requires a fix/retest before claiming usability
  readiness. Repeated confusion on the same concept requires wording/interaction change.
  A small study supplies formative evidence, not a statistical usability guarantee.

Independent review:
- Prepare a fixed manifest, milestone dispositions, evidence index and known limits.
- Request Fable to review the actual implementation and evidence against M0–M6 and
  N1–N11; preserve its independent report. If no connector is available, provide the
  exact handoff prompt and mark review pending. Do not substitute self-review.
- Resolve material defects and recheck affected cases. Update walkthrough wording only
  to behavior verified here; video recording remains a separate review-gated task.

Exit: technical verification and independent review complete; human comprehension
status explicitly reported. Full goal completion requires the human checks too. Until
then label the work “technically verified; operator study pending”, not “operator friendly”.

## Review traceability and checkpoint ledger

| Review finding | Owner milestone | Closure evidence |
|---|---|---|
| N1 engine vocabulary leak | M1b, H1, M6 | Live repair and unassisted operator task |
| N2 duplicated capabilities | M1a, M3, M4 | One context/answer contract, distinct scopes |
| N3 density/navigation | M0, M1a, H1, M2b, M6 | Browser flow and human task observations |
| N4 unsupported explanations | M1a | Unknown/limit and bad-citation cases |
| N5 recommendation bias | M3, M6 | Neutral options, operator choices |
| N6 invented consequences | M3 | Engine-derived planned effects |
| N7 domain restrictions | M0, M2a, M2b | Catalog, CRM admission and no-lifecycle checks |
| N8 true engine limits | M0, M1a, H1, M6 | Executable capability checks and honest UX |
| N9 speculative intake | M5 | Deterministic inventory, engine-derived gaps |
| N10 stale conversation | M1a, M1b, M3 | Source/draft changes and late-result tests |
| N11 nonexistent fixtures | M0, M6 | Fixture inventory and actual run identities |

All milestones currently planned. Maintain this table as implementation proceeds:

| Milestone | Implementation | Verification | Independent review | Evidence link |
|---|---|---|---|---|
| M0 | Partial; replay discrepancy open | Historical 506-check/probe evidence retained; fresh prepared PDLC implementation story is 110 passed / 1 failed versus historical 111 passed; fixture review pending | Pending | `output/playwright/ai-native-onboarding/M0/baseline-20261105/` |
| M1a | Revised; user UI re-review pending | 525 regression tests, 16 final explain tests, 7 frontend helpers, build/static checks and revised browser recovery checks passed | Pending | `output/playwright/ai-native-onboarding/M1a/README.md` |
| M1b | Technically verified; user UI review pending | Live repair validated on attempt 2; unchanged memory evaluation F1 1.0; 81 backend checks | Pending | `output/playwright/ai-native-onboarding/M1b/live-northstar/README.md` |
| H1 (simulated usability gate) | Not started | Pending | Pending | — |
| M2a | Independently accepted by Fable | Catalog/admission/compatibility checks; Chrome selection + reload + no-lifecycle case | Pass: Fable M2 review | `output/playwright/ai-native-onboarding/M2a/catalog-20261106/README.md` |
| M2b | Implemented interaction slice; acceptance partial | 99 backend tests, 13 frontend checks, CRM/PDLC/Northstar Chrome fixtures | Live wording and independent acceptance pending | `output/playwright/ai-native-onboarding/M2b/review-20261106/README.md` |
| M3 | Independently accepted for bounded fixture scope | Fable re-review on support/CRM copies | Live reasoning and human comprehension unverified; lows remain | `docs/review/2026-11-10-m3-clarity-fable-re-review.md` |
| M4 | Independently accepted, bounded fixture scope | Fable closes RR-1 with 12-second polling and save checks | RR-2–4 and M4-4–12 open; no live-agent, Spanner or human claim | `docs/review/2026-11-13-m4-poll-fable-recheck.md` |
| M5 | Independently accepted for bounded scope | Fable independent review; 194 backend and 19 frontend | M5-1/2 implementer fixes await focused recheck before human session; lows remain | `docs/review/2026-11-16-m5-fable-independent-review.md` |
| M6 | Independently accepted for bounded technical scope; operator study pending | Current PDLC Spanner 111 with cleanup; live CRM explain/revise/evaluate/handoff F1 1.0; intake, recovery and negative UI checks; 571 selected backend/architecture + 19 frontend tests | M5 clarity and M6-1 independently closed; M6-2 wording corrected; real-operator study and earlier lows remain | `docs/review/2026-11-17-m6-verification-handoff.md` |

## Execution and goal tracking

Work sequentially and continue authorized implementation without asking permission
for routine edits or local checks within a milestone. Honor the post-milestone UI
review gate before starting the next milestone. Publish milestone updates with changed behavior,
passed/failed cases and remaining uncertainties. Never infer user or operator
approval of an ontology from elapsed time or agent-generated expectations.

This document defines the new goal objectives. The thread's existing goal record is
an older blocked Spanner-integration goal; it has not been replaced, resumed or marked
complete by this planning task. Do not falsify that record to free a goal slot. The
new plan can be executed and tracked here independently; attaching it to a fresh goal
requires the existing goal to be legitimately resolved or a separate goal thread.

## Milestone-plan review disposition

The follow-up review is incorporated: M1 split into fixture/live slices; M2 split
into catalog/review UI; provider consent and capacity are specified in M1a; the live
acceptance proxy records both strings; M0/H1 provide early human comparison; fixture
reviewers are named or labelled author-reviewed; navigation/cancellation fixes move
earlier. Lifecycle previews require sample coverage, and negative-assertion checks
reuse delivered remediation. No implementation or fresh test run is claimed here.

## M1a implementation checkpoint

See `output/playwright/ai-native-onboarding/M1a/README.md` for UI evidence and limits.
The source fixture `tests/fixtures/workbench/explain-cases.json` records Northstar,
procurement quotation, PDLC disposition-label and missing-relationship cases with
author/reviewer fields. Reviewer remains unset; independent acceptance is not claimed.
The first code slice is ready for user UI review, not live-agent approval or final closure.

## M1a AI-native usefulness review

User requested outcome-based review of M1a. Verdict REVISE, recorded in
`output/playwright/ai-native-onboarding/M1a/README.md` under AI-native usefulness review.
Unknown-result recovery, bounded context completeness and job-error entry coverage
need correction. Existing safety mechanisms remain. Do not treat 521 tests or fixture
responses as proof of issue resolution. M1b remains behind user UI acceptance.

### M1a revision verification

Missing-information recovery, author-job failure explanations, bounded context retrieval
and focused/preserved revision handoff are implemented. See M1a README revision section
and `output/playwright/ai-native-onboarding/M1a/revised/`. The fixture-only UI review
includes procurement with no generated pack. No correction was auto-submitted and no
live provider/Spanner evidence is claimed. M1b still awaits user UI acceptance.

### Cross-domain self-serve assessment checkpoint

Actual browser simulations by delivery, procurement and customer-operations personas
are recorded in `output/playwright/ai-native-onboarding/M1a/domain-personas/assessment.md`.
The preparation path works with controlled responses; verdict REVISE for self-serve
readiness. Open-issue counts, large-pack discoverability, evidence round-trip continuity,
request preview and deferral semantics need correction. No live agent/authoring run or
production activation was tested; procurement remains a conceptual draft in this study.
User UI acceptance and M1b remain pending.

### M1a self-serve handoff fixes — 2026-11-05

The five domain-persona findings have a focused frontend correction: limitations
appear before the schema; recorded-decision counts no longer imply all issues are
resolved; same-revision explanation state survives the material detour with a return
action; the full prepared request is readable and focused at its beginning; deferral
explicitly retains any unsent request. Explanations are scoped to draft revision and
proposal and kept only in bounded session memory, cleared on sign-out. A source save
invalidates the displayed answer rather than reusing it.

Verification: frontend build/typecheck, 7 helper tests, headed Chrome recovery checks,
and delivery/CRM/procurement handoff rechecks passed. Procurement additionally saved
one simulated clarification in the isolated study database and verified invalidation.
No authoring, approval, live provider or sandbox execution was performed in this pass.
Evidence: `output/playwright/ai-native-onboarding/M1a/self-serve-fixes/`.
M1a is ready for user UI re-review, not accepted. M1b has not started.

### M1a focused operator-flow simplification plan

Observed in the delivery-persona review: answering requires several disclosure clicks,
the prepared request jumps to a distant form, setup guidance competes with the active
question, and the supposedly plain-language summary is mostly technical identifiers.

Implement within the existing explanation panel and authoring path:
1. Let operators answer a displayed limitation immediately. Optional explanation takes
   one click; follow-up questions remain available. Do not auto-call the provider.
2. Keep editable request review and explicit send in the same panel, using the existing
   authoring operation and consent/readiness checks. Preserve no-overwrite, revision
   fencing, cancellation, and same-revision navigation continuity. Label the business
   statement as operator input, never a claimed agent interpretation or verified fix.
3. Explain that the current question can be addressed now while other setup inputs
   remain necessary for testing. Collapse identifier/state detail under technical detail.
4. Verify delivery and CRM with fixture responses, failure/no-overwrite/stale behavior,
   and inspect desktop/narrow rendering. Record whether the next step is understandable.

No new chat backend, ontology-specific copy, automatic approval, or live resolution
claim. M1a user acceptance remains pending; M1b remains separate.

### M1a inline-flow outcome

Implemented the focused simplification above. The repeat simulated delivery-operator
review passes the bounded preparation/review task; CRM interaction checks also pass.
The same panel now contains the answer, editable request and explicit send. Failed
submission retains the request and permits retry; changed revisions invalidate old
explanations and reject preparation against stale context. No agent interpretation
or successful pack repair is claimed from a copied operator instruction.

Verification and remaining limits:
`output/playwright/ai-native-onboarding/M1a/inline-review/README.md`.
User UI acceptance remains pending. No live-provider run or M1b work was performed.


### M1b start authorized

User accepted moving forward from M1a and explicitly requested starting M1b.
M1a user UI gate is accepted for its bounded scope; previous pending entries above
are historical. M1b runs on port 8104 with an isolated control database and the real
configured provider. The saved complete-v2 Northstar invalid-admission case is copied;
source material and expected answers are preserved. No production activation or
Spanner claim is made. See the M1b evidence folder for all failed and successful runs.

### M1b stopping point

Live explain -> reviewed instruction -> browser author submission -> validated repair
has been demonstrated. Supplemental memory execution passes unchanged expectations.
Stop further provider iterations. The unrelated title-type change and inherited
removal warning remain visible and unapproved; see the M1b report. User UI review is
pending. No M2 work, pack acceptance, production activation or Spanner run is claimed.

## 2026-11-06 — Authorized M1b cross-domain UI verification

Use CRM/sales operations as the next contrasting live-agent case, alongside the existing
Northstar incident evidence and PDLC fixture UI checks. Northstar is not a payment-
transactions ontology; procurement is not yet a runnable-pack acceptance case.

The bounded CRM task is contact-history continuity after an email change, grounded in
synthetic policy/schema/sample inputs. Preserve original fixtures and expected answers;
create an isolated draft. Observe explain, one reviewed request, authoring outcome and
actual diff. A provider failure is a recorded result, not a reason for unbounded retries.

Presentation gate: one clear primary action; requested business outcome first; technical
keys/event names in a disclosure; uncertainty and failure state visible; no domain-specific
UI branching. Check desktop and narrow layout. Keep M1a acceptance separate from this run.

CRM cross-domain result: live explanation and one browser-submitted author request
completed; engine validation and two prewritten questions in supplemental memory
execution passed. One Ann remained after her email changed. See
`output/playwright/ai-native-onboarding/M1b/live-crm/README.md`. No UI sandbox/Spanner
run or pack approval occurred. Technical detail was collapsed in the shared request
preview and checked on CRM and delivery. Live explanation/result wording remains too
technical for presentation acceptance; unrequested text-search changes remain unapproved.


## 2026-11-06 — Whole existing-flow review using AI-native UI skill

Implementation-side review saved at
`docs/review/2026-11-06-full-flow-ai-native-ui-review.md`. This is not independent
milestone acceptance. CRM and delivery screens, new intake, selected recovery states
and a fresh prepared PDLC story were exercised on isolated copies. The story reports
110 passed / 1 failed (changed-content retry classified duplicate versus expected
conflict); diagnose before claiming it green. No oracle was changed.

Prioritize readable entity names and domain-neutral examples, then business-first agent
guidance, grouped review and optional technical navigation under M2b. Specific blocker
remedies/empty states belong to M4/M5/M6. Maintain the accepted bounded M1a behavior.
The report records every unexercised recovery/accessibility state and exact evidence.
No product code or production runtime changes were made by this review.


### Whole-flow review reconciliation after external spot-check

F04 is High for AI helpfulness and the first demo blocker, followed by F02/F03.
F02 includes the search control contradicting its “account, name or title” promise.
F01 is an engine-owner diagnostic and an unresolved M0 baseline replay, not an invitation
to alter the expectation. F05–F09 retain existing milestone ownership. The full-flow
review now records inspection-only methodology, revised operator-material vocabulary
counts and the specific disclosure change between the accepted and reviewed bundles.
No new runtime or UI execution was performed for this documentation reconciliation.

## 2026-11-06 — Autonomous execution authorization and verification gates

The user requested autonomous continuation with verification guardrails. Routine
implementation and local verification no longer wait for a user reply after each
slice. This supersedes the earlier mandatory user checkpoint for progression; it does
not authorize approval of a tenant pack, deployment, weakened safeguards, or claiming
independent acceptance from implementer checks.

Sequence: reconcile M1b/H1 evidence and the open F04 clarity finding; proceed to M2a
catalog, M2b readable review, M3 consequence previews, M4 failure/coverage assistance,
M5 intake assistance, then M6 integrated verification. Backend-independent M2a work may
be prepared while clarity acceptance remains open; do not claim H1 passed or ship the
operator journey with an unresolved high-severity usability blocker.

Per-slice objectives and acceptance cases remain those in the milestone sections.
Required checkpoints:
1. Record affected behavior, scope, baseline and independent-review status.
2. Run meaningful targeted backend/frontend checks and build the touched frontend.
3. Exercise changed UI in real Chrome on isolated copies, using at least CRM and
   delivery where domain neutrality is claimed; retain authored Northstar compatibility.
4. Exercise affected failure, stale, consent, reload/input recovery and cancellation
   states; label untested states. Check keyboard focus and narrow layout where relevant.
5. Preserve sources, expectations, original drafts and trust/approval boundaries.
   Live explanation, successful revision, sandbox evaluation and Spanner verification
   remain distinct evidence categories.
6. Record actual bundle/backend identity, copies and revisions, screenshots, outcome
   and remaining defects. Provide an independent review handoff after each slice.
7. Stop progression on data loss, unintended submission, boundary regression,
   unexplained semantic changes, or material acceptance failures. Diagnose the cause;
   never weaken expectations to pass. Do not enter repeated live retry loops.

Current status: M0 partial; M1a independently accepted for bounded safe preparation;
M1b has technical/live evidence but whole self-service is not accepted; F02/F03 have
implementer verification; F04 remains partial. Catalog inspection confirms the
PDLC-only literal in Content and capability response is still present. M2a is in
preparation, not implemented. F05–F09 remain scoped to their assigned milestones.

Goal tooling: the thread still holds an older blocked goal named “view”. It has not
been falsely completed or replaced. This plan is the execution ledger; a new tool goal
requires a fresh goal thread or legitimate resolution of that older goal.


### M2a implementation checkpoint — 2026-11-06

Local server-owned catalog now supplies Content selection, capabilities and UI options.
CRM is a packaged copy of the M0 adaptation with payload contracts, preserving original
fixture identity semantics and expected outcomes. Existing domain packs compose through
the existing loader alongside an authored pack; dependency, shadowing and collision
checks remain enforced. Unknown selections fail validation. Lifecycle confirmation for
the authored proposal is required only when it declares lifecycle states, on server and UI.
Unsupported generic example insertion was removed; operators supply actual source events.

117 targeted backend checks passed, then the final 11-test catalog suite passed including
one added combined-domain test. 13 frontend checks, build, lint and targeted typing passed.
Headed Chrome verified selection, keyboard toggle, save/reload with reauthentication,
old PDLC selection, narrow layout and no-lifecycle confirmation. No new provider/cloud run.
See `docs/review/2026-11-06-m2a-catalog-implementation.md` and its evidence README.
M2a is implemented and locally verified, not independently accepted. M0, H1 and F04
remain bounded/open as previously recorded; no automatic promotion to full self-service.


### M2b review interaction checkpoint — 2026-11-06

Separate understanding/review sections, grouped change acknowledgements (individual
removal confirmations preserved), source trust moved to Tenant setup, and optional
technical navigation implemented. One selector uses the existing read-only explanation
endpoint for pack, node and edge scopes, preserving consent, revision, capacity and
citation checks. Prepared requests from selected elements live in one shared visible
editor so switching the selection cannot strand the request. Clear returns focus to
the selector when its original answer is no longer mounted. Local-only consent now
aligns the prepared-request banner with disabled sending.

Chrome verified CRM, delivery and the final authored Northstar snapshot; no pack or
expected-answer edits. 99 targeted backend tests, 13 frontend helper tests, build,
lint and typing passed. Fixture explanations prove interaction only. Review pages
remain long (CRM 4,890px, delivery 4,362px at the recorded viewport). F04 live wording
remains open; this is not independent acceptance or full self-service closure.
Evidence: `output/playwright/ai-native-onboarding/M2b/review-20261106/README.md`.
Next bounded work is live wording/recovery review of this interaction, not expansion
into M3 while the high-severity operator-language concern remains unresolved.


### Fable M2 review and blocker remediation — 2026-11-07

Independent report: `docs/review/2026-11-06-m2a-m2b-fable-independent-review.md`.
M2a passes. M2b must not progress to M3 until F1 failed-send retention, F2 removal
request unification and F3 review-tick persistence pass re-review. F4–F9 and F04 remain
recorded follow-ups, not silently closed by technical checks.

Implemented the three blockers in the existing frontend state paths: retain prepared
requests through failed/cancelled jobs, clear submitted text only on successful
completion; use the shared editor for a named Keep-data request; preserve ticks in
per-draft session recovery with a proposal/review-bound basis. F10 now distinguishes
absent check results from actual failed checks. No backend gate or expected answer changed.

Implementer evidence: `output/playwright/ai-native-onboarding/M2b/remediation-20261107/README.md`.
15 frontend checks, build and 13 targeted backend guards passed. Real Chrome exercised
failure/retry/reload, named Keep-data request, navigation/reload ticks, successful author
completion and narrow layout with fixture authors. Independent re-review pending.


### M2b re-review accepted; M3 implementation — 2026-11-07

Independent Fable re-review `docs/review/2026-11-07-m2b-blocker-fable-re-review.md`
passes F1–F3 and explicitly permits M3. This supersedes the earlier blocker status,
without closing F04/F5, hidden catalog before demo, F6–F9 or M6 human comprehension.

M3 now implements decision-scoped options over the existing explain/request flow.
Real engine planning compares identity keys and existing transition guards/targets.
Missing coverage is unavailable. All effects are planned, not executed; preparation
never applies a pack or changes expected answers. The implementation is bounded to
20 sample events and two options. Support and CRM fixture browser checks are recorded;
live reasoning, successful authoring and human comprehension are not demonstrated.

Implementation report: `docs/review/2026-11-07-m3-decision-preview-implementation.md`.
Independent review ask: `docs/review/2026-11-07-m3-fable-review-prompt.md`.
M3 is ready for independent review of this bounded scope, not independently accepted.

### M3 independent review and clarity remediation — 2026-11-10

Fable review `docs/review/2026-11-07-m3-fable-independent-review.md` finds functionality
sound but withholds acceptance for M3-1/3/5 clarity. Those blockers and adjacent
M3-2/4 improvements are implemented and rechecked on support/CRM copies: named business
links separate from provenance, record key labels, current/proposed lifecycle rules with
sample limits, plain decision references/source excerpts, and visible stale-option remedies.
178 backend and 18 frontend checks pass; Chrome fixture evidence is recorded. No live-agent,
Spanner or human-comprehension acceptance is implied. M3-6/7/8 remain open low findings.

Report: `docs/review/2026-11-10-m3-clarity-remediation.md`.
Re-review ask: `docs/review/2026-11-10-m3-fable-re-review-prompt.md`.
M3 remains pending independent acceptance; M4 has not started. Other milestone gates unchanged.


### M3 accepted; M4 implemented for review — 2026-11-10

Fable independently accepts M3's bounded fixture scope in
`docs/review/2026-11-10-m3-clarity-fable-re-review.md`. M3-6/7/8 and RR-1 through RR-5
remain open low findings; other milestone gates remain unchanged.

M4 adds deterministic failure inspection guidance, a read-only failed-check scope on
the existing explain API, and a domain coverage list in the story workspace. Coverage
separates handling, rejection cases, state assertions and questions; it is not exhaustive
behavioral coverage. Root capabilities are outside the inventory. Empty/impossible new
assertions are rejected; legacy and weak negative assertions retain their original result
with explicit proof-strength warnings. Follow-up goals reuse outline/generate/review.

Real memory support/CRM runs and directed Chrome checks are recorded; fixture explanations
and outline calls are not live reasoning. Packs/stories/expected answers stay pinned.
Report: `docs/review/2026-11-10-m4-story-guidance-implementation.md`.
Review ask: `docs/review/2026-11-10-m4-fable-review-prompt.md`.
M4 requires independent review before M5. Human comprehension remains M6.

### M4 independent review and blocker remediation — 2026-11-13

Fable review `docs/review/2026-11-10-m4-fable-independent-review.md` withholds M4 acceptance
for weak assertions counted as proof (M4-1), pending follow-up text treated as reviewed
source (M4-2), and differences hidden in JSON (M4-3). These three are now corrected
and implementer-verified; focused independent re-review is pending. M4-4 through M4-12
remain open lows; other milestone gates unchanged. M5 has not started.

Report: `docs/review/2026-11-13-m4-blocker-remediation.md`.
Review ask: `docs/review/2026-11-13-m4-fable-re-review-prompt.md`.


### M4 independent blocker closure; polling correction — 2026-11-13

Fable re-review `docs/review/2026-11-13-m4-fable-re-review.md` independently closes
M4-1–3 and identifies RR-1: polling clears generated-story review acknowledgements.
The reset now binds to proposal content, draft ID and revision. A fresh implementer
Chrome run confirms 15 checks plus overall review survive ten seconds of real polling,
new generation clears them, and a second review survives ten seconds and saves (201).
Only JourneyAuthor.tsx product code changed. Build and 18 frontend checks pass.

Report: `docs/review/2026-11-13-m4-poll-review-remediation.md`.
Focused confirmation: `docs/review/2026-11-13-m4-poll-fable-recheck-prompt.md`.
M5 not started in this correction. RR-2–4, M4-4–12 and prior milestone limits remain open.


### M4 independently accepted; M5 started — 2026-11-13

Fable `docs/review/2026-11-13-m4-poll-fable-recheck.md` closes RR-1 after two
12-second/eight-poll checks and successful save. M4 passes bounded fixture scope.
M5 now adds thin, deterministic intake assistance in the existing six-step flow:
format-based category suggestions with operator correction and saved-sample inventory
from the existing evidence endpoint. No new agent workflow or inference of missing
business facts. Remaining M4 and earlier gates are carried forward unchanged.


### M5 deterministic intake verified; live gap recorded — 2026-11-13

Source suggestions and the existing server sample inventory are surfaced in intake.
Category correction/reload, original text, repeated identifiers and missing values pass
Chrome checks; 193 backend and 19 frontend tests pass. One live incomplete procurement
job preserves sources/questions and flags conflicting/missing evidence, but its key
pattern fails engine validation and business decisions still mention engine terms.
M5 is in progress, not accepted; no M6 start. See
`docs/review/2026-11-13-m5-intake-implementation.md` for evidence and remaining corrections.


### M5 recovery verification and Fable gate — 2026-11-16

Author guidance now includes actual regex/key lookup semantics and business-facing
clarification rules, including questions with no internal intent identifier. A fresh
live run on unchanged procurement evidence returns a conceptual proposal (pack=null)
and explicit supplier/policy/identity questions, rather than an invalid executable pack.
194 workbench tests pass. This demonstrates honest unresolved handling, not a working
procurement pack or repair of the old invalid artifact. Some technical effect wording
remains and is explicitly submitted for review.

Report: `docs/review/2026-11-16-m5-recovery-handoff.md`.
Fable checkpoint: `docs/review/2026-11-16-m5-fable-review-prompt.md`.
M5 requires independent acceptance before M6. No M6 work started; earlier open findings
and evidence boundaries remain unchanged.

## 2026-11-16 — M5 acceptance and pre-human checkpoint

Fable accepts M5 within its bounded scope. M5-1 repeated-value context and M5-2 duplicate answers/disabled-action guidance are implemented and browser-checked on isolated procurement and sales copies. Independent recheck is pending before human sessions. See `docs/review/2026-11-16-m5-clarity-fable-review-prompt.md`. Preserve M5 lows, earlier open gates, and the distinction between prompted compliance and unprompted live detection. M6 end-to-end, Spanner and real-human outcomes are not yet established.

## 2026-11-16 — M6 first technical pass

Current Spanner UI runs pass with verified cleanup on the registered slot. The same PDLC story still fails one memory duplicate/conflict check; expectations are unchanged. Live procurement asked unresolved business questions from a neutral instruction. Fresh CRM generated an engine-valid pack, but its inputs lacked the baseline referred to by “lifecycle remains unchanged”; this does not close the complete-input control. See `docs/review/2026-11-16-m6-first-pass.md` and its checkpoint review prompt. M6 remains in progress; M5 clarity recheck and human gates are not waived.

## 2026-11-17 — M6 verification handoff

Memory batch conflict reporting is corrected; the frozen PDLC expectations are unchanged. A fresh Spanner rerun passed 111 checks with verified cleanup at epoch 33 after a retained epoch-32 timeout. The complete live CRM explanation/revision/evaluation/handoff chain passed with F1 1.0 and preserved deal behavior. Fresh intake, unsupported/wrong-answer and recovery cases were exercised with their fixture/live boundaries recorded. See `docs/review/2026-11-17-m6-verification-handoff.md` and `docs/review/2026-11-17-m6-fable-review-prompt.md`. Independent acceptance, M5 clarity recheck and real-human sessions are pending; no deployment, activation or general self-service claim.

## 2026-11-17 — Independent M6 acceptance and pre-session corrections

Fable accepts M6 within its bounded technical scope and closes M5-1/2. Human sessions remain outstanding. M6-1 is addressed with explicit reset notice and persistent inline recovery guidance; focused independent recheck remains pending. M6-2 is resolved in the current handoff wording: F1 1.0 is no regression on two existing CRM questions; one Ann contact is observed, not a dedicated reviewed email-change assertion. No existing expectation was rewritten. Preserve M6-3–10 and earlier lows; see `docs/review/2026-11-17-m6-pre-session-disposition.md`.

## 2026-11-17 — Focused pre-session recheck accepted

Fable closes M6-1 and confirms M6-2 correction in `docs/review/2026-11-17-m6-1-fable-recheck.md`. The interaction can be recorded and used in operator sessions. Real-operator sessions remain outstanding; M6-3–10, earlier lows and the new unsaved-selection wording low remain open. Presentation scripting proceeds under the approved scope, with script review before production.
