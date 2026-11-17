# Agent-assisted onboarding: independent review

Reviewed 2026-11-04 on branch `feature/engram-walkthrough`, HEAD `27b4ba8`
(`27b4ba861814163d4292a950ddaae484a4282d82`). The working tree carried 505 modified
or untracked paths; every file under review is untracked relative to HEAD:
`src/context_graph/workbench/`, `demo/frontend/src/workbench/`,
`demo/frontend/tests/`, `tests/unit/test_workbench.py`,
`tests/unit/test_workbench_journeys.py` and the assessment
`docs/review/2026-11-04-agentic-onboarding-review.md`. Line numbers below refer to
the working-tree copies at review time.

This review verifies the existing assessment against the code rather than endorsing
it. No product code, pack, fixture, expected answer or runtime data was changed. No
live model call, Spanner run, cloud provisioning, activation or approval of any real
draft was performed. One temporary Vite config was created in `demo/frontend` for the
browser walkthrough and deleted afterwards; the probe SQLite store and launcher live
in the session scratchpad only.

## A. Executive verdict

**What exists today.** A constrained, tool-free LLM authoring loop wrapped in a
deterministic engine harness. The operator supplies scope, policy, sources (spec,
schema, samples), decisions and an evaluation oracle through a six-step UI. The server
sends the whole intake plus the Proposal and Pack JSON schemas and a syntax example to
one chat completion with JSON output, validates the returned proposal (exact-quote
citations, Pydantic Pack, real loader composition, admission policy, projection
planning on the samples) and lets the model repair twice more. The operator then
answers questions, accepts facts and the pack, chooses expected answers from the
engine's planned projection, picks trust, runs an isolated sandbox (memory or a
leased Spanner database), and approves. Approval pins a digest; export serializes
pack and evaluation YAML. Nothing activates a runtime.

**Is it a coding agent?** No. `ModelAuthor` (`authoring.py:92-253`) calls
`litellm.acompletion` with `response_format={"type":"json_object"}`, no tools, no
filesystem, no shell, no repository. The only file I/O is the server writing a
temporary YAML copy of the proposed pack so the real loader can compose it
(`engine.py:47-52`). The model never sees or edits files. The story-generation
workflow (`journey_authoring.py`) is the same pattern with a two-call budget.

**What an operator can complete end to end.** With a configured provider: intake,
proposal, decision round-trips, fact and pack review, oracle selection, sandbox run,
approval and export of pack/evaluation YAML. I exercised that full path in Chrome
against a fixture author (no model calls) with the in-memory sandbox: 19 revisions,
two author calls, two sandbox runs (one failed, one passed), approval, export.
Prepared PDLC stories and assistant-generated PDLC story variants also work, but only
for the frozen PDLC bundle.

**What remains incomplete.**

- A failed revision request strands a previously accepted and validated proposal
  (new, high; finding B1).
- Revisions can change identity, lifecycle, mapping, handling and retrieval behaviour
  with an empty "removed data" list and a passing validation (confirms and extends
  assessment finding 3; B2).
- Expected answers are chosen from the proposed pack's own planned projection and are
  then sent back to the author, so the oracle is not independent of the thing under
  test (B3).
- Operator decisions reach the pack only through the prompt; nothing checks that the
  executable pack reflects them, and answering the two standing policy questions
  forces another model call even when the pack already embodies them (B4, B5).
- Story generation cannot be invoked on an authored draft at all; it requires a
  prepared PDLC journey record (B6).
- Grounding is citation existence, not semantic support; a one-character quote
  satisfies it (B7).
- Sandbox failure guidance points at pack or engine corrections even when the cause
  is oracle scoping (B8).

## B. Prioritized findings

Severity reflects consequence for a real new-domain onboarding, not exploitability.

### B1. High: a failed revision request strands an accepted, validated proposal

- **Trigger.** Operator has a proposal with `validation.passed` and
  `review.pack_accepted`. They ask for a change (or apply answers). The provider call
  fails (outage, rate limit, timeout, three failed repairs).
- **Expected.** The previously accepted proposal remains usable; the failure is shown
  and the operator can retry later or proceed with the prior pack.
- **Actual.** `launch()` clears `review`, `validation` and `sandbox` and sets
  `proposal_stale=True` before the job starts (`api.py:625-629`). Only the success
  branch restores `proposal_stale=False` (`api.py:491-499`). On failure the record
  keeps the old proposal but marked stale; `/review` returns 409 "Generate a proposal
  for the current inputs first" (`api.py:676-677`); readiness lists "Regenerate the
  proposal after input changes" although no input changed.
- **Reproduced.** Probe P4 (scratchpad `probe_onboarding.py`): after a
  `ConnectionError` from the author double, `job=failed`, `proposal_stale=True`,
  `review=None`, `validation=None`, review request 409.
- **Consequence.** Any provider failure blocks the operator until a later provider
  call succeeds. With the provider down there is no way to accept, test or approve the
  pack they had already reviewed.
- **Smallest fix.** Snapshot `review`, `validation`, `proposal_stale` in `launch()`
  for `kind == "author"` and restore them in the failure and cancellation branches of
  `finish_job()` when `record["proposal"]` is unchanged. Add a test: author success,
  review, failing author, review again succeeds.

### B2. High: behaviour-changing revisions pass review with an empty removal list

- **Trigger.** A revision (or an in-call repair) keeps every node, property, state,
  event and intent name but changes a key, drops a transition or its guard, changes
  `lifecycle.initial`, changes an event's handling to `ledger_only`, or rewrites
  retrieval weights and seed types.
- **Expected.** The operator is shown what changed before accepting.
- **Actual.** `pack_items()` inventories names only (`changes.py:11-28`). Probe P2 on
  fixture copies: key `account+id -> id`, transition removed, transition guard removed,
  initial state changed, `incident.resolved` handling `processed -> ledger_only`, and
  retrieval weights/seed types changed all yield `removal_inventory=[]` and
  `validate passed`. Two edits were caught, but by sample admission expectations, not
  by the diff: deleting the projection section (admission becomes `unsupported`
  because a processed event without consumers is downgraded, `pack_admission.py:136`)
  and dropping `required` on `account` (the `expect_admitted=false` sample then
  admits). Through the API (probe P5) a key-changing revision was stored with
  `repair_removals=[]`, `validation.passed=True`, and `/review` accepted it with 200.
  The UI's "In plain words" cards show only the current key (`OperatorFlow.tsx:325-329`)
  with no comparison to the previous proposal, although the previous proposal is
  retained in `authoring_context.proposal` (`api.py:593-603`).
- **Consequence.** The identity rule, the state machine and the retrieval policy can
  change between proposals without a review prompt. After a key change the previously
  chosen expected IDs become dangling (probe P5: planned IDs became
  `Incident:INC-1042` while `expected_nodes` still held `Incident:payments|INC-1042`);
  this is only caught at sandbox time as a missing node, and only if the operator had
  selected that node.
- **Smallest fix.** Compute a structural diff between `authoring_context.proposal.pack`
  and the new pack over keys, interfaces, lifecycle (initial, states, transitions and
  `only_from`), event handling and contract requiredness, projection rules per event,
  and retrieval (seed types, intents, weights). Put it in the proposal record next to
  `repair_removals`, require explicit acknowledgement in `/review` the same way
  removals are required (`api.py:681-684`), and flag expected IDs that no longer appear
  in planned writes.

### B3. Medium: the evaluation oracle is derived from the system under test

- **Trigger.** Operator chooses expected answers and required nodes.
- **Expected.** Expected answers are independent evidence of correct behaviour.
- **Actual.** Candidate entities come from `validation.samples[].planned.nodes`
  (`EntityPicker.tsx:10-32`), that is, the proposed pack's own planned projection.
  A wrong key rule produces wrong candidate IDs which the operator then "confirms".
  The author also receives `inputs.questions` including `expected` and
  `seed_node_ids` (`authoring.py:178`, probe P3), so a revision can shape identity to
  reproduce the expected IDs. The author's output schema cannot change the questions
  (`models.py:83-97`), which is the right boundary, but the candidate list is not
  independent.
- **Consequence.** A generated pack plus an operator-confirmed oracle built from that
  pack's output confirms the generator's interpretation rather than the customer's.
- **Smallest fix.** Label candidates with the key fields that produced them and show
  the source sample record beside each; add a second candidate source that is pack
  independent (the sample payload field values the operator says identify the thing),
  and when the key changes, show the operator the old and new ID for the same sample
  record. Do not send `expected` and `seed_node_ids` to the author; send only query
  text and intent.

### B4. Medium: operator decisions are enforced by prompt only

- **Trigger.** Operator records identity and lifecycle answers and any assistant
  question answers, then applies them.
- **Expected.** The executable pack is checked against the recorded decisions.
- **Actual.** Decisions travel as free text in `inputs.decisions`
  (`authoring.py:178`). `verify_proposal` and `validate` never reference them. A
  fact with `basis: "operator"` needs no decision reference (probe P1c). The only
  enforcement is that every assistant `decisions[]` id has an answer
  (`api.py:102-104`).
- **Consequence.** "Do operator answers reliably affect the executable pack?" is
  answered only by the model's compliance. The operator cannot see which pack element
  implements which answer.
- **Smallest fix.** Add an optional `decision_id` to `Fact` and require every
  operator-basis fact to reference a recorded decision; require the proposal to list,
  per node, the decision id that justified its key and lifecycle (a small map in the
  proposal, validated against `content.decisions`). Keep it declarative; no tools
  needed.

### B5. Medium: standing policy questions force a model round-trip and appear before any proposal

- **Trigger.** New draft, step 3.
- **Browser observed.** "Decisions to review · 2 unanswered" (identity, lifecycle) is
  shown before the first proposal exists. After the proposal arrived (which already
  carried `key: [account, id]` and a lifecycle), typing both answers made the accept
  button inert with "Your answers are pending. Apply them together before accepting
  or testing this pack." Acceptance required "Apply answers with the assistant",
  which is another author job (`OperatorFlow.tsx:295, 314-315, 449-450`;
  `Workbench.tsx:213-224`). The round-trip returned an identical pack.
- **Source.** `readiness()` always requires both keys (`api.py:105-107`);
  `ModelReview` synthesizes both questions regardless of the proposal
  (`OperatorFlow.tsx:296-312`); `save()` marks any decision change as
  `pending_decisions` (`api.py:423-424`).
- **Consequence.** Every onboarding pays at least two model calls, and domains with
  no stateful types must still answer a lifecycle question. Confirms assessment
  finding 7, with the extra cost of the forced call.
- **Smallest fix.** Treat the two standing answers as review attestations, not model
  inputs: record them without setting `pending_decisions`, show beside each the pack
  elements they attest (key fields, lifecycle block), and only require the lifecycle
  attestation when a node declares a lifecycle. Keep `pending_decisions` for
  assistant-raised questions.

### B6. Medium: story generation is unreachable for an authored pack

- **Trigger.** Operator wants generated stories and checks for a newly authored
  domain pack.
- **Actual.** `/journey-outline` requires `record["journey"]` and a configured model
  (`api.py:289-290`); only `/admin/journeys/{name}` creates such records, and only
  for the PDLC catalogue (`api.py:248-283`). `propose_journey` reads
  `fixtures/pdlc/pdlc.pack.yaml` (`journey_authoring.py:142, 218`) and
  `validate_variant` pins the frozen registry and `pack: "pdlc"`
  (`journey_authoring.py:68-69, 76, 109-112`; `journey_runner.py:46-57`).
- **Consequence.** The product goal "prepare representative stories and tests" is met
  for PDLC only. Confirms assessment finding 1 and sharpens it: it is not merely tied
  to PDLC, it cannot be started from a customer draft.
- **Smallest fix.** Parameterize `propose_journey`/`validate_variant` by a composed
  registry and pack digest from the draft's validated bundle (`engine.composed`), add
  a `/journey-outline` path for drafts with `validation.passed`, and keep the
  reviewed-expectations gate. Prove one non-PDLC story end to end before claiming it.

### B7. Low: citation validity is substring membership with no minimum length

- **Actual.** `verify_proposal` checks `citation.quote not in sources[id]`
  (`authoring.py:77-82`); `Citation.quote` has `min_length=1` (`models.py:66`).
  Probe P1: an unsupported explanation with a real quote passes; a one-character
  quote passes; an operator-basis fact with no decision reference passes.
- **Consequence.** The "From a source" pill in the UI (`OperatorFlow.tsx:394-401`)
  can be earned by any excerpt. Confirms assessment finding 2.
- **Smallest fix.** Minimum quote length (for example 12 characters or 3 tokens), one
  quote per cited concept term, and show the quote in context (surrounding sentence)
  so a reviewer can judge support. Semantic support stays a human review step.

### B8. Low: failure guidance misattributes oracle-scoping failures

- **Browser observed.** My first run failed with mean F1 66.7% against 80% because
  the question retrieved `Incident` plus the `Service` it affects while the expected
  set held only the Incident. The next-action card read "Investigate the failed
  checks ... request a correction or engineering help", and the warning said "A
  correction may require engine work, not just a pack edit" (`Workbench.tsx:1946-1968`).
  The actual fix was setting "Answer type" to Incident under "Technical details ·
  internal IDs"; the rerun scored 1.0. "Discuss this failure with the assistant"
  pre-fills an author instruction and would spend a model call.
- **Consequence.** Operators are steered to re-author a correct pack.
- **Smallest fix.** When every unexpected answer shares a node type absent from the
  expected set, say so and offer the answer-type filter and explicit seed mode inline
  on the result row before offering the assistant.

### B9. Low: context budget and composition context are not managed

- **Actual.** The author receives the entire `Content` (up to 20 sources of 40,000
  characters, `models.py:18, 40`), both JSON schemas, the syntax example and sample
  statistics (`authoring.py:163-180`); the fixture intake alone produced a 23.9 KB
  user message (probe P3). No truncation or selection exists. Selected packs reach
  the model as names only: with `existing_packs=["pdlc"]` the message contained no
  PDLC type definitions (probe P3). Composition conflicts surface only from the real
  loader during repair.
- **Consequence.** Large intakes fail at the provider with the generic "format or
  pack checks" reason (`job_errors.py:68-72`) rather than a size message; composing
  with PDLC is trial and error. Confirms assessment findings 5 and 6.
- **Smallest fix.** Pre-check an estimated token size before launch and refuse with a
  specific message; include a compact inventory of selected-pack node, edge and intent
  names (not full YAML) in the prompt.

### B10. Low: single-domain composition only

- **Actual.** `Content.existing_packs` is `list[Literal["pdlc"]]` with `max_length=1`
  (`models.py:36`); `/admin/capabilities` advertises `packs: ["pdlc"]`
  (`api.py:239`).
- **Consequence.** A customer with two authored domains cannot compose them in the
  workbench. Intentional scope limitation, worth stating in the UI.

### B11. Informational: scope wording edits invalidate the proposal

- `save()` treats `scope` like sources (`api.py:414`): any edit to the scope text sets
  `proposal_stale` and clears review and validation. Reasonable for meaning changes,
  surprising for typo fixes. Documented behaviour, not a defect.

## C. Disposition of the existing assessment

| Assessment claim | Disposition | Evidence |
|---|---|---|
| Pack authoring uses a tool-free LLM returning structured JSON | Confirmed | `authoring.py:194-201`: `acompletion`, `json_object`, no tools |
| Backend validates and allows up to three repair attempts | Partially correct | Three calls total: one initial plus two repairs (`authoring.py:191`). Repair feedback also includes exact-quote and type guidance (`231-252`) |
| Model has no shell, repository or filesystem workspace | Confirmed | Only server-side temp YAML for loader composition (`engine.py:47-52`) |
| Pack/evaluation YAML serialized by the server | Confirmed | `api.py:757-759`; export has no approval gate (probe P6) |
| Pack authoring does not generate sample events or reviewed oracle | Confirmed, with a correction | `Proposal` has no questions or samples (`models.py:83-97`). But the candidate oracle shown to the operator is the pack's own planned projection and the author receives the expected IDs (B3) |
| Separate story authoring is tied to the frozen PDLC pack | Confirmed and understated | Also cannot be started from an authored draft; needs a prepared journey record (B6) |
| Citation verification checks exact excerpts, not support | Confirmed and understated | One-character quotes pass (B7) |
| Removal tracking misses keys, mappings and retrieval | Confirmed and extended | Also misses transitions, guards, initial state and handling; validation catches projection deletion and requiredness only through sample admission expectations (B2) |
| Operator initiates sandbox; author does not run semantic tests | Confirmed | `api.py:719-726`; the UI's failure button only pre-fills an author instruction and the next author call receives `authoring_context.evaluation` (`api.py:600-602`) |
| 45 tests passed; not proof of live-model or browser quality | Confirmed | Rerun: 45 passed (two files); 58 with execution and storage views; 18 more in pool, Spanner API and journey suites; 6 frontend node tests; `tsc` clean |
| Path step 6: engine-failing proposal saved with limitations, later gates block | Confirmed | `authoring.py:224-229`; `api.py:500-507, 109-110` |
| Path step 7: source changes clear prior author context | Confirmed, nuance | Only sources clear it (`api.py:417`); scope, roots and existing-pack changes mark stale but keep context |
| Finding 3: workbench classifies against None, label is always initial | Confirmed | `engine.py:131`; browser shows "Engine change class: initial" |
| Finding 5: schema input is JSON text with parse check only | Confirmed | `api.py:405-408` |
| Finding 6: in-process asyncio jobs, two maximum, restart marks interrupted | Confirmed | `api.py:610-613`; `store.py:96-113` |
| Finding 7: identity and lifecycle always required, synthesized in UI | Confirmed and extended | Forced author round-trip and pre-proposal display observed in browser (B5) |
| Verdict: "useful foundation ... not a complete general-domain agent" | Confirmed | See A |
| Recommendation: fix diff/grounding, connect story generation, then one fresh non-PDLC onboarding | Agreed, with B1 added ahead of it | B1 is a correctness defect that blocks recovery and was not in the assessment |

Overstatements in the assessment: none material. Omissions: B1 (stranded proposal on
failure), B3 (oracle derived from the pack under test), B5 (forced model call for
standing answers) and B8 (failure guidance).

## D. Recommended end-to-end onboarding flow

| Step | Operator | Assistant (model) | Deterministic engine |
|---|---|---|---|
| 1 Scope and policy | Writes scope; grants provider permission; confirms redaction | | Stores draft; enforces permission gate (`api.py:645-648`) |
| 2 Evidence | Adds spec, schema, samples | | Parses samples, computes field statistics, parse-checks schema |
| 3 First proposal | Optional focus instruction | Proposes facts, questions, conceptual or executable pack from evidence (no tools) | Verifies citations, Pack schema, composes with selected packs, admission, projection plan; up to two repairs |
| 4 Decisions | Answers only assistant-raised questions; attests identity/lifecycle against the shown pack elements (B5) | Applies answers in a revision | Checks every operator-basis fact references a decision (B4); computes structural diff against the previous pack (B2) |
| 5 Review | Reads diff, facts, limitations; accepts or rejects | | Blocks acceptance until diff items and removals are acknowledged |
| 6 Oracle | Writes questions; selects expected answers with key provenance shown; sets answer type/seed mode; selects required nodes; sets trust | Never sees expected IDs (B3) | Offers candidates with the sample record and key fields that produced them; flags dangling IDs |
| 7 Sandbox | Runs | | Projects samples, runs evaluation, reports per-question diagnostics with scoping hints (B8) |
| 8 Failure loop | Chooses "adjust oracle" or "ask for a pack correction" | Receives evaluation and diff; proposes a corrected pack; cannot touch the oracle | Re-runs diff and validation; review gate again |
| 9 Stories (future) | Reviews outline and generated events | Proposes outline and events against the draft's composed registry (B6) | Validates against the draft bundle; runs journey; expectations stay operator-reviewed |
| 10 Approval and handoff | Approves | | Pins digest over content, proposal, validation, sandbox; exports YAML; no activation |

## E. Ordered implementation plan

Essential correctness fixes (no new agent infrastructure):

1. **Restore state on failed or cancelled author jobs (B1).** Acceptance: after a
   provider failure the prior proposal keeps `review`, `validation` and
   `proposal_stale=False`; `/review` succeeds; a unit test covers success, failure,
   review.
2. **Structural pack diff and acknowledgement (B2).** Acceptance: the eight probe
   variants each produce at least one diff entry; `/review` with `pack_accepted` is
   409 until every diff entry is acknowledged; expected IDs absent from planned writes
   are listed in readiness.
3. **Decision linkage (B4).** Acceptance: operator-basis facts without a valid
   `decision_id` fail `verify_proposal`; the UI shows, per node, which decision set its
   key and lifecycle.
4. **Standing answers as attestations (B5).** Acceptance: recording identity and
   lifecycle answers does not set `pending_decisions`; lifecycle attestation is
   required only when a node declares a lifecycle; the fixture path needs one author
   call, not two.
5. **Oracle independence (B3).** Acceptance: the author message contains no
   `expected` or `seed_node_ids`; candidates show the key fields and source record;
   a key change shows old and new IDs for the same record.
6. **Citation floor and context (B7).** Acceptance: quotes shorter than the floor are
   rejected with the existing citation failure reason; the UI shows the sentence
   around each quote.
7. **Failure diagnostics (B8) and size pre-check (B9).** Acceptance: a run whose
   unexpected answers all share one node type shows the answer-type hint; an intake
   above the budget is refused before launch with a specific message.

Optional agent infrastructure, only after the above:

8. **Draft-scoped story generation (B6).** Acceptance: one non-PDLC pack authored in
   the workbench gets an outline, generated events and reviewed checks, and the
   journey runs on the memory sandbox and on Spanner.
9. **Bounded feedback loop.** Keep the model tool-free; expose the evaluation report,
   diff and validation problems as structured context (already partly done through
   `authoring_context`) with an explicit iteration cap and an operator checkpoint
   between iterations.

## F. Architecture assessment

**A. Current constrained generation-and-validation loop.** The engine owns every
semantic check; the model only emits JSON. This is the correct shape for the stated
goal: packs are declarative, the loader and projector already provide
ground truth, and the dangerous surface (expectations, activation) is kept outside the
model's schema. Its weaknesses (B1 to B5, B7, B8) are harness defects, not a
capability ceiling.

**B. Assistant with bounded tools (inspect draft, validate pack, run sandbox).**
Tools would let the model iterate without operator clicks. Everything those tools
would return is already computed deterministically and can be fed back as context
(`authoring_context` does this for validation problems and evaluation). The benefit
is latency and fewer operator round-trips; the cost is a model that runs sandboxes
unattended and a stronger temptation to tune toward the oracle. Not needed to reach
the product goal.

**C. Coding agent with an isolated workspace and execution tools.** Justified only
when the deliverable includes code: new expression functions, a source adapter, a
loader change, or engine work discovered during onboarding ("a correction may require
engine work"). None of that is the operator's job and none should ship through an
onboarding UI. YAML output alone does not justify it; the server already serializes
YAML from validated JSON.

**Recommendation.** Stay with A and fix the harness (plan items 1 to 7). Add the
draft-scoped story workflow (item 8) in the same tool-free style. Revisit B only if
operators demonstrably need unattended iteration after the diff and oracle fixes;
reserve C for an engineering workflow outside the workbench.

## G. Verification matrix

| Behaviour | Source reviewed | Locally tested | Live model | Browser tested | Notes |
|---|---|---|---|---|---|
| Tool-free JSON authoring, three-call budget, 80 s per call, 12k tokens | Yes | Yes (unit tests mock `acompletion`) | No | No | `authoring.py:190-201` |
| Citation existence, one-character quotes, operator facts without decision | Yes | Yes (probe P1) | n/a | No | |
| Removal inventory blind to keys, transitions, guards, initial, handling, retrieval | Yes | Yes (probe P2, P5) | n/a | No | Projection deletion and requiredness caught by sample admission |
| Model message contents, no selected-pack definitions, expected IDs sent | Yes | Yes (probe P3) | No | No | 23.9 KB message for fixture intake |
| Stranded proposal after failed revision | Yes | Yes (probe P4) | No | No | |
| Export before approval | Yes | Yes (probe P6) | n/a | Yes (button present pre-approval) | |
| Full operator path with fixture author and memory sandbox | Yes | Yes | No | Yes | Draft `da988b76…` in scratchpad store: 2 author jobs, 2 sandbox runs, approval digest, export YAML |
| Standing identity/lifecycle questions shown pre-proposal; forced apply round-trip | Yes | No | No | Yes | |
| Sandbox failure on oracle scoping; guidance text; fix via answer type | Yes | No | No | Yes | F1 0.667 then 1.0 |
| Spanner sandbox, pool leasing, cleanup | Partly (`sandbox.py`, `execution.py`) | Yes (unit, 18 tests with fakes) | n/a | No (not rerun; earlier rehearsal docs cover it) | Deliberately not exercised against the live pool on port 8101 |
| Live-provider proposal quality, repair behaviour, prompt compliance | No | No | No | No | Unverified; the 2026-11-03 rehearsal recorded one real-provider story outline needing a second attempt |
| Story generation for a non-PDLC pack | Yes (impossible by construction) | n/a | No | No | B6 |
| Frontend unit tests (editing, results) | Yes | Yes (6 pass, `node --test`) | n/a | n/a | `tsc -p tsconfig.workbench.json` clean |
| Large-intake behaviour near 20 × 40,000 characters | Yes | No | No | No | Unverified assumption: provider error maps to a generic reason |
| Restart recovery of running jobs | Yes | Yes (existing unit test) | n/a | No | |

Commands run:

```
.venv/bin/python -m pytest tests/unit/test_workbench.py tests/unit/test_workbench_journeys.py -q            # 45 passed
.venv/bin/python -m pytest tests/unit/test_workbench.py tests/unit/test_workbench_journeys.py \
    tests/unit/test_workbench_execution.py tests/unit/test_workbench_storage_views.py -q                  # 58 passed
.venv/bin/python -m pytest tests/unit/test_workbench_pool_config.py tests/unit/test_workbench_pool_provision.py \
    tests/unit/test_workbench_spanner_api.py tests/unit/test_workbench_spanner_pool.py \
    tests/unit/test_implementation_journey.py tests/unit/test_planning_journey.py -q                      # 18 passed
node --test tests/workbench-editing.test.ts tests/workbench-results.test.ts   (in demo/frontend)           # 6 pass
node node_modules/typescript/bin/tsc -p tsconfig.workbench.json --noEmit     (in demo/frontend)           # exit 0
.venv/bin/python <scratchpad>/probe_onboarding.py                                                           # P1–P6 above
```

Remaining verification that only a live run can provide: one fresh onboarding with a
configured provider on a non-PDLC domain, recording how many repair attempts fire, how
often the model honours "decisions: []" after answers are applied, and whether the
limitations list is used honestly when engine checks fail three times. Run it after
plan items 1, 2 and 5 so that the diff and oracle changes are what gets observed.
