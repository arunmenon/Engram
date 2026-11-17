# Agent-assisted onboarding remediation: independent review

Reviewed 2026-11-05. Review only: no product code, pack, fixture, expected answer,
draft database or earlier review was modified. No live provider call, Spanner run,
server restart or browser session against the live workbench was made.

## 1. Scope and identity

| Item | Value |
|---|---|
| Branch | `feature/engram-walkthrough` |
| HEAD | `27b4ba861814163d4292a950ddaae484a4282d82` (Publish G03 stakeholder verification and issue reconciliation) |
| Manifest | `docs/review/2026-11-05-onboarding-review-manifest.json`, 68 files, 0 hash drift at review time |
| Working tree | Every workbench file (`src/context_graph/workbench/`, `demo/frontend/src/workbench/`, `tests/unit/test_workbench*.py`, `tests/fixtures/workbench/`, `output/playwright/`, the review docs) is untracked. Dozens of unrelated tracked files are also modified. |

Baseline uncertainty: because the workbench has no git history, the "remediation
since November 4" cannot be isolated by diff. This review treats the November 4
independent review's findings B1–B11 and the assessment's follow-up sections as the
baseline, and judges the current file contents directly. Where a behaviour cannot be
attributed to the remediation versus earlier work, the closure table says so.

Inputs read: both November 4 reviews including all follow-up sections, the workbench
plan and storyboard, the manifest, every backend module listed in the prompt, the
frontend components via a delegated read, the five playwright evidence folders plus
`output/workbench/onboarding-hardening/`, and the test suites.

## 2. Verdict

The remediation is real and mostly server-enforced. Of the eleven November 4
findings, four are fixed, four are partially fixed and three remain open. The
architecture is still a constrained, tool-free LLM loop with the engine doing the
semantic checks, which remains the right shape for this product.

It is not yet a reliable operator-assisted onboarding flow, for three reasons:

1. **The new structural-change acknowledgement has a baseline hole.** After an
   operator accepts a pack and then answers an assistant question or edits a source,
   the next regeneration is diffed against the pack that preceded the accepted one,
   not the accepted pack. A revision that silently reverts an acknowledged change
   shows an empty change list and needs no acknowledgement. Reproduced through the
   API (finding R1). This is the same defect class as the November 4 high finding B2,
   reintroduced by the fix.
2. **Several of the new provenance guarantees are traceability, not grounding, and
   two of them go stale silently.** Any citation, any decision ID or any one-word
   instruction excerpt linked to an edge path satisfies the relationship gate (R3).
   A trust-evidence fact survives a change to the trusted producer list with no flag
   and can be approved (R2). A replaced revision request leaves facts quoting the old
   request with no marker (R9).
3. **Live evidence shows the complete-input path works and the incomplete-input path
   does not.** The Northstar run on a real provider and real Spanner is genuine and
   well recorded. Every incomplete-specification trial either fabricated a placeholder
   relationship, exhausted three attempts, or asked near-duplicate questions; the only
   Chrome authoring attempt after the trust change returned a conceptual draft blocked
   on how to quote a JSON source. The new trust label has never been rendered with a
   live trust fact.

Tests, lint, type checks and the frontend build pass as reported, with one exception
the assessment does not mention: the repository's hex-purity suite fails on two
workbench modules that import the Spanner client directly (R11).

## 3. Findings by severity

Severity reflects operator impact on the onboarding flow. "New" means introduced by
the remediation; "pre-existing" means present on November 4.

### R1. High (new): acknowledged-change baseline regresses after a review reset

- Where: `src/context_graph/workbench/api.py:573-577` (baseline selection in
  `finish_job`), `api.py:491-495` (`save` clears `review` on answer or source change).
- Trigger: accept pack Z; regenerate to A (diff Z→A shown, acknowledged, A accepted);
  answer an assistant question or edit a source (`review` becomes `None`); apply
  answers, model returns B.
- Observed: baseline is `proposal_change_base` (Z) because `review.pack_accepted` is
  gone. When B equals Z (the model reverts A's change), `proposal_changes` is empty,
  readiness has no acknowledgement item, and the pack can be accepted and run.
- Expected: the baseline is the last accepted pack (A) until a later pack is accepted.
- Impact: a revision applied after answering a question can undo an acknowledged
  identity, lifecycle, mapping or retrieval change without any review prompt. This
  is the "answer a question, apply it" path every onboarding uses.
- Evidence: probe (fixture author, temp store): `[B1 B(=Z) vs accepted A: changes
  shown] []`, `extra_note present in B: False`, no "Acknowledge" readiness item.
  `test_changed_pack_requires_acknowledgement_and_retry_cannot_hide_diff` covers only
  the unaccepted-retry path, not the accepted-then-reset path.
- Smallest correction: record `accepted_pack` (or the accepted proposal's pack) at
  review time, independent of `review`, and use it as the baseline whenever it exists;
  only advance it on a later `pack_accepted` review.

### R2. Medium (new): trust-evidence snapshot is not revalidated when trust settings change

- Where: `authoring.py:83-87` (check runs only during authoring), `api.py:467-510`
  (`save` leaves `proposal`, `review` and the trust fact untouched when `trusted_ids`
  or `trust_reviewed` change).
- Trigger: proposal contains a fact with `trusted_producers: ["pagerduty"]`; operator
  accepts; operator changes `trusted_ids` to `[]` and re-ticks trust review.
- Observed: `proposal_stale` false, review retained, fact still shows `["pagerduty"]`,
  no readiness item, sandbox runs, approval succeeds. Re-running `verify_proposal` on
  the saved state raises "trust evidence must match the reviewed producer settings",
  so the server knows the rule but never re-applies it.
- Impact: the "Reviewed trust settings" evidence shown to the operator and frozen in
  the approval digest can describe settings that are no longer in force.
- Evidence: probe P5c.
- Smallest correction: in `save`, when `trusted_ids` or `trust_reviewed` change and
  any fact carries `trusted_producers`, either mark the proposal stale or re-run
  `verify_proposal` and surface the mismatch as a readiness item.

### R3. Medium (pre-existing class, new gate): relationship grounding is satisfiable by any linked evidence

- Where: `authoring.py:126-153`.
- Observed (all accepted by `verify_proposal` + `verify_relationship_grounding`): an
  `AFFECTS` edge supported by a `source` fact citing the schema fragment `{`; by an
  `operator` fact citing the `identity` decision; by an `operator` fact with
  `instruction_quote: "the"`; by a `source` fact citing an unrelated runbook sentence
  through a child pointer `/types/edges/AFFECTS/from`.
- Impact: the gate stops the specific failure seen in `live-author.json` (an
  inference-only self-edge) but a model that has learned to attach a pointer to any
  fact will pass. The assessment acknowledges "traceability, not entailment"; the
  additional point is that the minimum evidence is one character, so the operator
  cannot rely on the gate to have filtered anything beyond basis labels.
- Smallest correction: require citation and instruction quotes of a minimum length
  (for example 20 characters, or a full sentence), reject facts whose only link to an
  edge is a decision ID of a different category (`identity`/`lifecycle`), and show the
  supporting quote next to each edge in the review UI so the operator judges it.

### R4. Medium (new): generated-story negative assertions are not shape-checked

- Where: `journey_authoring.py:127-148` (arity check covers positive IDs only),
  `journey_runner.py:177-220` (`node_absent` passes for any unknown ID; `edge_absent`
  passes for any unknown type).
- Observed: `validate_variant` accepts `node_absent` with `Incident:INC-1042` (wrong
  key arity), `edge_absent` with the undeclared type `DEPENDS_ON`, and `node_present`
  on an undeclared type `Ticket`. The run reports the two negatives as passed.
- Impact: the story evidence's "absence of cross-account AFFECTS links" style checks
  are only meaningful if their IDs and types are well formed. A model that mis-forms
  a negative check produces a green result that proves nothing. The live story's
  `node-absent-bad-incident` uses `Incident:|INC-BAD-1`, which happens to have the
  right arity, but nothing enforced that.
- Smallest correction: apply the arity check and a declared-type check to
  `node_absent`, `edge_absent`, `edge_present`, `edge_targets`, retrieval `forbidden`
  and `forbidden_edges` as well; reject undeclared node or edge types in any check.

### R5. Medium (pre-existing pattern): the story oracle is model-authored and accepted in one call

- Where: `journey_authoring.py:154-345` (the model writes events and expected checks
  from the brief), `api.py:404-446` (`journey-accept` flips
  `expectations_reviewed` for the whole variant).
- Observed: review before execution is server-enforced (`api.py:455-456`, probe
  P5e: 409 on an unreviewed baseline), but "review" is a single revision-fenced call
  with no per-check acknowledgement. The outline step asks the operator for decisions,
  and the system prompt tells the model to infer outcomes from the specification; the
  expected values are still produced by the same model that interprets the spec.
- Impact: for authored domains, story checks confirm the model's reading of the spec
  unless the operator reads each of the 16 checks. This is the story-side version of
  the November 4 B3 concern.
- Smallest correction: require acknowledgement of each generated check (as the pack
  diff now does) or at minimum of each evaluation/retrieval check's expected IDs.

### R6. Low (new): the clarification handler hides co-occurring engine problems and duplicates questions

- Where: `authoring.py:156-203`.
- Observed: with problems `["Question status: intent ... is not executable",
  "Sample 2: admission differs...", "incident.resolved: payload contract required"]`
  the handler returns a conceptual draft whose limitations mention only the intent;
  the other two problems appear nowhere. The model's own `relationship` question is
  kept and an engine question `retrieval-evidence-status` on the same concept is
  appended, so the operator sees two questions for one missing fact.
- Evidence: probe P3; `onboarding-trust-20261105/missing-relationship.json` shows
  exactly this pair (`edge_support` and `retrieval-evidence-status`).
- Impact: bounded. The hidden problems reappear on the next revision once edges
  exist; the duplicate question is friction and reads as the assistant not listening.
- Smallest correction: include the remaining `problems` in `limitations`; skip the
  engine question when the model already returned a decision whose text mentions the
  blocked question or the words relationship/edge; or replace the model's question.

### R7. Low (partial fix of B3): question seeds and answer type still reach the author

- Where: `authoring.py:214-220`.
- Observed: `author_inputs` removes `expected`, `reviewed`, `expectation_statement`,
  `expected_nodes`, `forbidden_nodes`, `graph_reviewed`, but sends `seed_node_ids`
  (`["Incident:payments|INC-1042"]`), `node_type`, `intent` and `seed_mode`.
- Impact: explicit seeds reveal the canonical ID syntax and key composition the
  operator chose, and in single-entity questions the seed often is the answer. In the
  live Northstar run the specification text itself states the expected incident, so
  the structured redaction was not the only channel either.
- Smallest correction: send only `query` and `intent`; let seeds and type be chosen
  after the proposal, which the UI already supports via the entity picker.

### R8. Low (new): structural diff granularity and wording

- Where: `changes.py:51-63`, `changes.py:93-96`.
- Observed: any edit inside the `projection` list is one change whose `before` and
  `after` are the whole list (576 characters for the fixture); appending a rule is
  the same single change. A revision that returns `pack=null` produces one change with
  path `[]` and summary " was changed. Review the before and proposed rule." The live
  run's panel had 20 checkboxes including `["projection"] changed`.
- Impact: the operator acknowledges "projection changed" without the system pointing
  at which rule, so the acknowledgement is only as good as a manual read of two list
  dumps. The blank-subject summary is a visible defect in the conceptual-revision case.
- Smallest correction: recurse into lists keyed by `event` (projection rules) and by
  index otherwise; special-case `path == []`.

### R9. Low (new): replaced revision requests leave unmarked stale quotes

- Where: `api.py:467-510` (`instruction` is not a model field, so no staleness),
  `authoring.py:77-82`.
- Observed: after accepting a proposal whose fact quotes "Add Sourced to Incident.",
  changing the instruction to "Rename Service to Component." keeps the proposal,
  review and quote with no readiness item. A later author job that reuses the old
  quote fails with the generic "did not meet the required format or pack checks"
  reason for non-model authors; for `ModelAuthor` it enters the repair loop and, after
  three attempts, reports "failed evidence or format validation", neither naming the
  quote rule (`job_errors.py:12-36` has no branch for instruction or trust evidence).
- Impact: low; new proposals are correctly prevented from reusing superseded quotes
  (server-enforced). The display of the old quote next to a new instruction is the
  usability gap.
- Smallest correction: mark facts whose `instruction_quote` is absent from the current
  instruction as "from an earlier request" in the record view; add failure reasons for
  the two new evidence rules.

### R10. Low (pre-existing): review flags are not invalidated server-side when their subject changes

- Where: `api.py:467-510`.
- Observed: `trust_reviewed`, `graph_reviewed` and `question.reviewed` arrive in the
  same `PUT` as the values they attest. The server never resets them when
  `trusted_ids`, `expected_nodes` or a question's `expected` change. The UI is
  responsible for unticking.
- Impact: an API client or a UI bug can carry "reviewed" over changed values. This
  is consistent with the operator being trusted, but it means the readiness checklist
  is not evidence that the current values were looked at.

### R16. Low (new): the engineer-panel accept checkbox bypasses the acknowledgement payload

- Where: `demo/frontend/src/workbench/Workbench.tsx:1360-1380`; the guided path's
  payload is at `Workbench.tsx:1217-1227`.
- Observed: "I reviewed and accept this pack proposal." posts `accepted_facts` and
  `pack_accepted` only. With pending changes or removals the server answers 409 (fails
  closed). With none, the call succeeds and replaces `review`, dropping
  `confirmed_policies`, so the identity and lifecycle items silently reappear in
  readiness after the operator had confirmed them.
- Impact: confusing rather than unsafe; the server gate holds. Two accept controls
  with different payloads is the underlying problem.
- Smallest correction: remove the engineer-panel checkbox or route it through the
  same `onAccept` handler.

### R11. Low (pre-existing, outside the remediation): hex-purity suite fails on workbench modules

- `tests/unit/test_hex_purity.py`: 2 failed, 417 passed. `workbench/pool_config.py`
  and `workbench/spanner_pool.py` import `google.cloud.spanner_v1`, which ADR-0019
  reserves for `adapters/`. The assessment's verification lists never ran this suite.
  Not an onboarding defect, but it is a failing repository gate in the reviewed tree.

### Informational

- R12. `GET /export` still returns pack and evaluation YAML before approval
  (`api.py:849-861`); the record shows `approval: null`. Unchanged from November 4.
- R13. A story workspace records `journey_pack_origin: {draft_id, revision}` but
  nothing flags that the parent moved on; the snapshot stays valid by design.
- R14. The Chrome trust attempt was blocked by the model's reading of the repair
  message "Quotes must exactly match source text, not paraphrases or decoded JSON
  fragments" (`authoring.py:427-429`). A raw substring of the JSON schema text would
  pass `verify_proposal`; the wording steers the model away from it. Prompt-only.
- R15. `Proposal.model_validate` keeps the caller's `pack` dict by reference; this
  review's own probe mutated a shared fixture through it. Harmless in the API, where
  every record is reloaded from JSON, but worth knowing for tests.

## 4. Closure of the November 4 findings

| Nov 4 finding | Status | Basis |
|---|---|---|
| B1 High: failed revision strands accepted proposal | **Fixed** | `launch` no longer clears state; `finish_job` publishes only on success (`api.py:579-591`). Probe P5b: after a provider failure, proposal/review/validation/sandbox/approval identical, approve readiness true, export still shows approval. Test `test_author_revision_preserves_prior_state_until_replacement` (8 cases). |
| B2 High: behaviour changes with empty removal list | **Partially fixed** | Structural diff and server-required acknowledgement exist (`changes.py:35-101`, `api.py:783-787`, readiness `api.py:110-113`); key, guard, handling, retrieval and removals are all covered (probe P1). But R1 regresses the baseline after any review reset, and R8 limits precision. |
| B3 Medium: oracle derived from the pack under test | **Partially fixed** | Structured expected IDs and the new `expectation_statement` are withheld (`authoring.py:214-220`); the UI collects the business expectation first; seeds and answer type still sent (R7); story oracle model-authored (R5). Legacy questions not retroactively independent. |
| B4 Medium: decisions enforced by prompt only | **Partially fixed** | `pack_paths` and `decision_ids` now resolve server-side (`authoring.py:75-108`); operator facts need a decision, instruction quote or trust snapshot. Relevance remains prompt-only (R3). |
| B5 Medium: standing questions force a model round trip | **Fixed** | `confirmed_policies` in the review body satisfies readiness without an author call (probe P5a: one author call, both policy items cleared, reset on regeneration). UI: two checkboxes; no "Apply answers" trigger. Policies are pack-wide booleans, not linked to elements. |
| B6 Medium: story generation unreachable for authored packs | **Fixed** | `POST /story-workspace` freezes the composed bundle with a pinned digest (`draft_stories.py`, `api.py:340-375`); parent revision unchanged; unreviewed baseline cannot run (probe P5e; `test_workbench_draft_stories.py`, 10 tests). Live Northstar story executed on Spanner. |
| B7 Low: citation validity is one-character substring | **Open** | `Citation.quote min_length=1` unchanged; `instruction_quote` has the same property (R3 shows `{` and `the` accepted). |
| B8 Low: failure guidance misattributes oracle failures | **Fixed (pending UI confirmation)** | `results.ts` distinguishes event failures, graph mismatches and answer-only failures; test "answer-only failure leads to question settings, not an assumed engine correction" passes. |
| B9 Low: no context budget or composition context | **Open** | `ModelAuthor` still sends every source in full; selected-pack definitions still arrive only as names. |
| B10 Low: single-domain composition | **Open** | `Content.existing_packs: list[Literal["pdlc"]]`, max 1 (`models.py:37`). |
| B11 Info: scope wording edits invalidate the proposal | **Open** | `scope` remains in `model_fields` (`api.py:480`). |

New regressions introduced by the remediation: R1, R2, R4, R6, R8, R9, R16. Pre-existing
issues still present: B7, B9, B10, B11, R3 (class), R5 (pattern), R10, R11.

## 5. Assessment of the ten change groups

Enforcement legend: **server** = rejected by the API or authoring validator;
**prompt** = instruction text only; **demonstrated** = seen in one or more model
responses but not enforced.

1. **Failed or cancelled jobs preserve state.** Server. Verified by probe and by the
   8-case test; revision fencing (`store.put` compare-and-swap, `report_attempt`,
   `ConflictError` swallow at `api.py:677-682`) rejects late completion. Stale
   evidence is handled by `save`, not by the job path, which is correct. One race:
   a `save` issued while a job is finishing can lose to the job's cancelled write and
   return 409; the operator reloads. Acceptable.
2. **Structural changes need acknowledgement.** Server for the acknowledgement
   (`api.py:783-787`), with exact-value IDs and stale-ID rejection (422 verified).
   Retry without acceptance keeps the baseline (test). **Defect R1** on the
   accepted-then-reset path; granularity R8.
3. **Attestations replace standing questions.** Server for readiness
   (`api.py:107-109`); confirmations reset with each proposal. The claim "decisions
   link to pack elements" is only true for facts (`pack_paths`/`decision_ids`); the
   identity and lifecycle confirmations are pack-wide booleans with no element
   reference. The UI label changes when no node has a lifecycle but the tick is still
   required. Partially meets intent.
4. **Expected IDs out of author prompts.** Server-side filtering in `author_inputs`;
   feedback reduced to scores and IDs. Seeds and answer type still sent (R7). Story
   prompts: the authored-domain baseline carries only operator samples and admission
   dispositions, so no business answers leak; the PDLC path sends the fixture baseline
   with its full expected checks (pre-existing, PDLC only). Evidence files confirm no
   prompt field stores expected IDs; the live spec text states the answer anyway.
5. **Story workspaces from authored packs.** Server: digest validated on every load
   (`snapshot_registry`), parent untouched, execution blocked until reviewed. The
   snapshot includes core and the authored pack (roots and existing packs when
   selected). Creation requires accepted + validated, not sandbox or approval, which
   is a reasonable choice but should be stated in the UI. No parent-drift flag (R13).
6. **Typed assertion schemas and envelopes.** Server: `EXPECTED_MODELS` strict,
   zero-based `after_step` consistent between model (`journeys.py:35-39`), validator
   and runner (`journey_runner.py:351`); contract violations need a 422 expectation at
   the right index; positive IDs arity-checked. PDLC fixtures still validate (journey
   suite passes). **Negative assertions and type existence are not checked (R4).**
   Failure guidance for malformed events is fixed wording without payload values
   (`job_errors.py:68-73`).
7. **Instruction quotes.** Server: exact substring of the current instruction, basis
   operator required, superseded quotes rejected in new proposals (test and probe).
   History kept in `author_messages` (last 20). Stale display R9; minimum length R3.
   UI explanation: see section 7.
8. **Edge grounding.** Server during generation only (`ModelAuthor` loop); not re-run
   at review or on non-model authors. Trust facts correctly excluded. Laundering is
   trivial (R3). The assessment's own limit statement is accurate; this review adds
   that the floor is one character and that unrelated decision IDs count.
9. **Clarification drafts.** Server (deterministic handler) for the specific
   edge-free, intent-rejected case on initial drafts; revisions with a prior pack go
   through normal repair and keep the pack (code path `authoring.py:396-403`).
   Questions and expected answers untouched (test). Conceals co-occurring problems
   for one round and duplicates questions (R6). The replayed live failure confirms the
   handler fires; the fresh trust run confirms the duplicate.
10. **Trust provenance.** Server: exact membership, reviewed-empty valid, unreviewed
    rejected, backwards compatible (`default=None`), excluded from edge grounding
    (test). Goes stale silently (R2). Ingest acceptance and retrieval trust are
    distinct in the engine: admission uses the payload contract only
    (`engine.py:81,98`); trust feeds the projector's Sourced marking and retrieval
    (`engine.py:82`, `sandbox.py:73-79`). The prompt tells the model not to promise
    ingest rejection, and the live limitations repeat that correctly. UI evidence:
    the label exists in code but has never been rendered with a live trust fact; the
    only trust indicator in any screenshot is the `source_trust: trusted` node
    property in the sandbox graph.

## 6. Verification performed

| Check | Result | Mode |
|---|---|---|
| `pytest` workbench, execution, draft_stories, journeys, spanner_api | 100 passed, 20.4 s | fixture authors, memory sandbox, Spanner test doubles |
| `pytest` storage_views, pool_config, pool_provision, spanner_pool | 15 passed | test doubles |
| `pytest tests/unit/test_hex_purity.py` | 2 failed, 417 passed (R11) | static |
| `ruff check` workbench + two test files | passed | static |
| `mypy` authoring, models, api, draft_stories, journey_authoring, changes | passed | static |
| `npm run build:workbench` | passed (tsc + vite), Node v23.8.0 | static |
| `workbench-editing.test.ts`, `workbench-results.test.ts` | 4/4, 3/3 passed | node |
| Offline probes P1–P6 and the baseline probe | see findings | fixture copies, temp SQLite stores, in-process ASGI, memory sandbox |
| Evidence inspection | six playwright folders and the hardening folder | saved files only |

Test counts: `test_workbench.py` 54, `test_workbench_draft_stories.py` 10, matching
the assessment's "54 authoring/API tests". Authors in those tests are local async
doubles or `ModelAuthor` with a patched `litellm.acompletion`; no test exercises a
provider.

What the saved evidence establishes, by mode:

- **Real provider, real Spanner, real browser:** the Northstar parent draft
  `684b9cdd…` (approved at r30 and again at r39 after an engine revalidation) and story
  `9622246a…` (16/16 checks, two Spanner runs, `cleanup: "verified"`, resource
  `engram-sandbox-01`). Provider identity is indirect: no draft stores a model name or
  usage; it appears in the story consent text and `verification-summary.json`.
  These predate `trusted_producers` and `instruction_quote`; no live fact carries
  either.
- **Real provider, Python author only:** every `onboarding-improvements-*` and
  `onboarding-trust` JSON. Direct-instruction cases validated in one attempt each
  and carry `instruction_quote`; `reviewed-trust.json` carries
  `trusted_producers: ["pagerduty"]`. Missing-relationship cases: placeholder edge
  (improvements), two questions incl. trust (grounded), three attempts exhausted
  (final), engine clarification (clarification replay), two near-duplicate
  relationship questions (trust).
- **Real browser, real provider, blocked:** `onboarding-trust/ui-authored.json`:
  three attempts, `pack: null`, one blocking question about quoting JSON, 14 proposed
  removals, no trust fact, no trust label on the page.
- **Fixture author, memory sandbox, real browser:** `onboarding-hardening/
  browser-result.json` (source links, accept, expectation field, story workspace,
  disabled run).

Not verified in this review and still needed: a live-provider authoring run on a
non-PDLC domain that renders the trust label and an instruction quote in the UI; a
live incomplete-specification run that yields exactly one clarification question; a
Spanner story run after R4 is fixed; and R1 against the real UI flow.

## 7. Explicit dispositions

- **Duplicate clarification questions.** Confirmed in code (`authoring.py:183-198`
  dedupes by ID only) and in evidence (`onboarding-trust/missing-relationship.json`).
  Open model-quality plus deterministic-handler issue (R6).
- **Exact-JSON-quote failures.** Confirmed in `ui-authored.json`. The validator would
  accept a raw substring of the schema text; the repair wording discourages it (R14).
  Open; prompt-only fix available, plus a UI hint that schema sources may be quoted
  verbatim.
- **Trust evidence UI coverage.** The label and producer list are implemented in
  `OperatorFlow.tsx` (see frontend notes below) and build-verified; no screenshot or
  live record shows it rendered. Unverified live; and R2 means what it would show can
  be stale.
- **Live non-PDLC behaviour.** Demonstrated end to end once (Northstar, complete
  inputs, before the last two provenance changes). Incomplete inputs: not reliable,
  per the assessment's own retained failures and this review's reading of them.

## 8. Operator experience notes (from the frontend read)

Source inspection only; no browser session was opened for this review. References
are to `demo/frontend/src/workbench/`.

- **Confirmations.** `OperatorFlow.tsx:304-310` renders two fixed checkboxes under
  "Confirm this pack": "I checked the fields that identify each entity in this pack."
  and either "I checked the states, transitions and update rules in this pack." or,
  when no node has a lifecycle, "I confirm this pack does not require lifecycle
  states; I checked its update rules." The copy says they do not request another
  assistant run. They are sent as `review.confirmed_policies`. The accept button is
  disabled until both are ticked with no inline explanation; the only hint is the
  readiness checklist. The "Answer the assistant's questions" next-action banner can
  appear while only a confirmation is missing, which wrongly suggests an author run.
- **Change panel.** `OperatorFlow.tsx:462-478`: "What changed in this pack", one
  article per change with category, summary, a collapsed "Inspect the changed rule"
  showing path, kind and raw before/after JSON, and a checkbox "I have reviewed this
  change". For a `["projection"]` change the before/after are the full rule lists
  (R8). The live run showed 20 such articles.
- **Removals.** A separate section "The assistant proposed removing data" with "I
  accept removing <item>" checkboxes and "Keep this data — prepare a revision
  request". Two acknowledgement mechanisms coexist for overlapping information.
- **Trust and instruction evidence.** `OperatorFlow.tsx:403-404` prints
  "Reviewed trust settings: <producers>" or "Reviewed trust settings: No producers
  marked as trusted", and "Your revision request: <quote>", inside the fact card,
  alongside citations and "Applies to" pack paths. There is no explanation that
  trust affects Sourced marking and retrieval rather than ingest acceptance; the only
  such statement is whatever the model writes in `limitations`. Nothing marks a
  quote whose request has since been replaced (R9), and nothing flags a trust
  snapshot that no longer matches the settings (R2).
- **Story workspace.** `Workbench.tsx:1884-1890`: "Create a story workspace for this
  pack", enabled when the draft is not dirty, not stale, has no pending decisions,
  validation passed and the pack is accepted; the help text says the pack and
  dependencies are pinned and expectations are reviewed before running. The
  workspace shows its origin only through `journey_pack_origin`; no drift notice.
- **Failure guidance.** `results.ts:32-45` orders the next step as dead letters →
  graph mismatch → question setup, and the "Discuss this failure with the assistant"
  button (`Workbench.tsx:1975-1987`) pre-fills an instruction that starts with
  question configuration and says to keep reviewed expected answers unchanged. This
  resolves B8 for the sandbox path. Two small inconsistencies remain: the
  deterministic guidance tells the operator to check "expected answers against the
  source material" while the assistant prompt forbids touching them, and the story
  workspace has no equivalent button.
- **Cancelled and failed jobs.** A failed author job shows "The task did not
  finish: … Your previous pack and its existing checks are retained" or the
  changed-inputs variant (`OperatorFlow.tsx:202-212`). A cancelled author job
  writes no `error`, so the authoring view shows nothing at all; only the story
  workspace has a "Cancelled" line.
- **Engineer panel.** A second accept checkbox and a second validate button exist
  beside the guided flow; the checkbox has a different payload (R16). The client
  re-implements readiness in `nextTask` (`OperatorFlow.tsx:7-107`), and its policy
  branch says "ask the assistant to apply it", which is wrong for confirmations.
- **Test coverage.** The two node test files cover only the pure helpers
  (`editing.ts`, `results.ts`). No test exercises gating, the review payload,
  confirmations, change acknowledgement or story-workspace enablement.
- **Export.** The export control remains available before approval; the record view
  carries `approval: null`.

## 9. What must change before calling this reliable

Essential, in order:

1. Fix the acknowledgement baseline (R1) and add a test for accept → answer → apply →
   revert.
2. Revalidate trust and instruction evidence on save, or mark it stale (R2, R9).
3. Shape-check negative story assertions and declared types (R4).
4. Raise the evidence floor for citations and instruction quotes and show the quote
   beside each edge in review (R3, B7).
5. Surface all engine problems in the clarification draft and suppress the duplicate
   engine question (R6).
6. Stop sending question seeds and answer type to the author (R7).
7. One fresh live run on a non-PDLC domain through the UI that shows a trust fact and
   an instruction quote rendered, and one incomplete-input run that ends in a single
   clarification question.

Worth doing but not blocking: per-check story acknowledgement (R5), list-aware diff
(R8), server-side reset of review flags (R10), hex-purity fix (R11), gating export on
approval (R12), removing the second accept control (R16), a cancelled-job message,
frontend tests for gating logic, context budgeting (B9).

Not needed: converting the loop to a coding agent. Every defect above is a harness
rule or a prompt wording issue; none requires tools, a shell or a workspace.
