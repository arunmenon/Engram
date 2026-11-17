# M6 independent review

## Verdict

**Technical acceptance: M6 passes its bounded scope. No blocking finding.**
**Human acceptance: not started. It is a separate, outstanding gate.**

M5-1 and M5-2 are fixed; that recheck is folded in here and is no longer pending.

Two things should be settled before the real-operator sessions:

1. **M6-1.** Choosing a graph expectation and ticking its review box in one save silently clears the
   tick. I reproduced it. Nothing unsafe happens, but "Run the examples" then stays disabled with no
   explanation on the screen.
2. **M6-2.** The live CRM chain scores F1 1.0 on two questions that do not test the change that was
   made. The recorded graph does show the change worked. The claim should say that, or a reviewed
   expectation for the changed behaviour should be added.

Everything here was checked with a refusing provider stub and recorded artifacts. I made no live-agent
or Spanner call. Live and Spanner results are judged from the implementer's records.

## Reproducibility

| Item | Value |
|---|---|
| Reviewer | Fable (Claude), independent review. Not the implementer. No product, pack or expectation changes. |
| Date | 2026-11-17, Asia/Kolkata |
| Prior familiarity | I reviewed M0 to M5. I did the four operator tasks in the browser before reading the M6 handoff, first-pass report or changed code; I had listed the evidence folder and snapshot names to seed my copies. Simulated persona, not human comprehension. |
| Branch, commit | feature/engram-walkthrough, HEAD 27b4ba8, large dirty and untracked tree |
| Bundle | `workbench-B3e2IkoC.js`, sha256 685aa77a…f6656, the bundle my page served |
| Source hashes | All 47 files in the final manifest match the working tree |
| Engine | sha256:7ad0d16f…2c4e, read from my own freshly started process; matches the manifest |
| Service | http://127.0.0.1:8140, operator `fable-m6-review`, own SQLite store |
| Browser | Headed Chrome through Python Playwright, 1440x1000 and 430x900, zoom 100% |
| Agent, storage | Refusing author and explainer stubs; isolated memory for the one story rerun |
| Evidence | `output/playwright/ai-native-onboarding/fable-m6-20261117/` |
| Not exercised | Live provider, Spanner, file chooser and PDF, cancellation and late completion, sign-out isolation, simultaneous tenants, screen reader, full keyboard pass, human participants |

### Copies

| Copy | Seeded from | Start to end revision | Unchanged |
|---|---|---|---|
| Fable M6 Procurement intake | blank | 1 to 6 | pasted texts equal after reload |
| Fable M6 Sales contact intake | blank | 1 to 4 | pasted texts saved as typed |
| Fable M6 Procurement unresolved | M5 recovery, bc627eac r7 | 2 to 3 | sources, questions, proposal |
| Fable M6 CRM baseline | M6 final start, 3efbc50c r2 | 2 to 5 | sources, questions, proposal |
| Fable M6 CRM recovery | M6 final start, 3efbc50c r2 | 2 to 5 | sources, questions, proposal |
| M6 frozen explanation recheck (approved package) | M6 final, 3efbc50c r13 | 2 to 2 | read only |
| Fable M6 Incident story | M6 fixtures, a6b552be r7 | 2 to 4 | events, expectations, pinned pack |

## Operator tasks

### 1. Procurement

- **Find request 42 without JSON:** yes. Searching "42" shows "Repeated value: 42 · 2 occurrences",
  then example 1 with unit east and example 2 with unit west, as labelled fields. The page states that
  a repeat "can be an update to the same record or a collision; the samples alone cannot decide".
- **Search:** "east" lists its three events; an absent value says "No samples match … Try another
  event, field or value." Zero, false, null, empty text and an empty payload are counted correctly.
- **Correct a category and reload:** corrected after saving; a full reload kept every name, category
  and text. No provider call during intake.
- **Incomplete input:** one answer box per recorded question (three, not six). After answering only the
  identity question the button reads disabled with: "Answer all recorded questions before applying
  them. Still unanswered: 2 recorded questions. If you do not know, leave the question blank."
  The answer survived polling, navigation and reload. Run, approve and complete stay disabled.
- **Hesitation:** I cannot apply the one answer I know until the other two are answered. The screen
  says so honestly, but the next-action banner still says "Review the agent's open questions".

### 2. CRM

- **Why an email change splits history:** stated on the first review item: "When Ann changes email,
  this can split her history into two contacts even though the CRM sends the same stable contact
  identifier." The sample entity list also shows two Anns under the email-keyed pack.
- **Business-language request:** I typed two plain sentences. "Review my request" made no call and
  showed "Requested outcome — your words", the records mentioned as "candidates to review, not
  confirmed changes", and "The exact field, event rule or answer behavior to change is not verified
  yet."
- **Failed send:** a double click produced one author call. After the stub refused: "The agent could
  not finish this request… Your answer and request are kept." Both texts were intact, the pack was
  unchanged, and resending required ticking "I reviewed this request against the current draft".
- **After reload:** answer and request restored; one request editor.
- **Planned versus tested:** clear on the approved copy. Step 5 shows "Example checks passed",
  expected versus retrieved per question, and "Observed graph, event by event".

### 3. Incident operations

- **Wrong title:** "Expected title: A different reviewed title. Recorded: Payments outage."
- **Wrong account:** "Expected answers: Incident · other-account / INC-1042. Found: Incident · payments
  / INC-1042."
- **Total cost:** "UNSUPPORTED… Scalar totals are not a supported record-set question." Counted
  separately from passes.
- **What to investigate:** "Where to inspect: graph or mapping" and "answer scope", with "Never change
  a reviewed expectation merely to make a check pass."
- **Rerun:** 4 passed, 2 failed, 1 unsupported before and after; expectations, events and pinned pack
  identical. No provider call.

### 4. Handoff

- **Activated?** No, and the screen says so three times: "It does not deploy or activate the tenant",
  "Activation is a separate operational step and is not available from this workbench".
- **Which artifact?** "Composed bundle: core 1.1.0 · crm 1.0.0", with engine and input hashes under
  "Verified engine and inputs". The approval digest, approver and approved revision are in the record
  and revision history, not on the main view (M6-8).

## Decisive checks

| Check | Result |
|---|---|
| 1. Memory event identity | Diff is 19 lines. Identical retry is a duplicate, changed payload or envelope is a conflict, server position is ignored, identity survives document expiry. Plain `append` keeps its old behaviour. 3 regression and 111 memory conformance tests pass. One compatibility change found (M6-4). No story expectation was edited: both PDLC runs use the same story. |
| 2. Explain scope | The server rule "options only for a recorded decision" and the read-only rule for failed checks are in `verify_answer`. The prompt now states the same. On my service a local-only draft still gets 409 for authoring and 403 for explain. The file is untracked, so I could not diff it against an earlier version. First rejected response and later success are both retained in the implementer evidence. |
| 3. Live CRM chain | Sources equal. Question text and expected answers equal. Deal lifecycle and deal rules equal. Contact key changed from email to contact_id, as requested. One unrequested change, listed in the change review: Contact text fields gained "email". See M6-2 and M6-3. |
| 4. Oracles | "Account:acme exists" was recorded before the run with its basis. Both question oracles are unchanged. All are implementer-reviewed; I did not review them as domain truth. |
| 5. Spanner | Epoch 32: cleanup hit DeadlineExceeded, no result published. Later status ready at epoch 32. Epoch 33: 111 checks, cleanup verified, slot released. Memory and Spanner runs have the same story, pack digest, engine and per-check outcomes. Root cause of the timeout is not established (M6-5). No rerun needed for this review. |
| 6. Failure and recovery | Confirmed on my copies (tasks 2 and 3). The no-state fixture is a team directory keyed by code with no states and no relationships; the relationship-free fixture is a question with no pack and a clarifying decision. They are different fixtures, not renames. The second comes from a deterministic helper, not a live agent. |
| 7. Source race | Evidence is partial, as the handoff says. I judge it not material to bounded acceptance: the server binds explanations to the revision and my M3 and M4 reviews saw stale and replaced requests refused. Keep it open; do not describe it as a reproduced browser 409. |
| 8. Graph review friction | Reproduced (M6-1). |
| 9. Tests and build | The same 571-test selection passes for me, plus 19 frontend tests. Bundle hash matches. The implementer's services were reused processes; mine was freshly started on the same sources. |

## Findings

### M6-1, Medium for human sessions: review tick cleared without a message

- **Reproduction:** on "Questions to answer", tick an entity under "Entities that must exist", tick "I
  reviewed these graph expectations before execution", save. The selection is saved; the tick is
  cleared; the only message is "Saved." A second tick and save sticks.
- **Cause:** the server resets the review flag whenever the selection changes in the same save. That is
  a safe default.
- **Consequence:** the operator believes the review is recorded, then finds "Run the examples"
  disabled. The reason is only in the readiness checklist.
- **Correction:** after such a save, say "Your selections changed. Confirm them again." next to the box.
- **Verify:** one save, message visible, tick visibly unticked, second tick sticks.

### M6-2, Medium for claims: the passing score does not test the change

- **Evidence:** the two questions are "Which account does deal D-7 belong to?" and "Who works at
  Globex?". Neither involves Ann or an email change. The graph assertion is "Account:acme exists".
- **What does show the change:** the recorded run ends with one contact for Ann (C1, new email, one
  works-at link). Under the email-keyed pack the sample list showed two.
- **Consequence:** "revision → evaluation (F1 1.0)" reads as if the evaluation confirmed the revision.
  It confirmed that nothing else broke.
- **Correction:** word the result as "no regression on two existing questions; one contact observed for
  Ann", or add an operator-reviewed expectation for Ann before the run. Do not add it after the fact
  to the recorded run.

### Lows

| ID | Finding | Correction |
|---|---|---|
| M6-3 | The live explanation and its generated instruction contain pack syntax: `type_settings.Contact.key = ["contact_id"]`. Cause and consequence are in plain words; the "next step" is not. The operator's own request was plain. | Keep syntax in technical details; this is prompt-only control today. |
| M6-4 | Memory backend: an imported document that fails current event validation now raises during import, where it was stored before. Found by direct probe; import routes may validate earlier. | Confirm parity with the other backends' import behaviour, or compute the fingerprint without strict validation for imports. |
| M6-5 | Spanner epoch 32: the operator message said the database was unavailable for reuse, yet the slot later read ready. The release only commits after proving the database empty, and acquisition checks emptiness again, so reuse was safe. The cause of the timeout is unknown. | Keep open. Record whether the release committed server-side. |
| M6-6 | The live CRM chain started from an implementer-built record whose limitation text already names the problem and the direction of the fix. It shows a guided revision, not diagnosis. Review and approval were completed within seconds by script. | State this wherever the chain is cited. |
| M6-7 | A partial set of answers cannot be applied. The reason is shown, but the next-action banner does not change. | Banner: "Answer or gather material for the remaining questions." |
| M6-8 | The handoff screen shows bundle versions and input hashes but not the approval digest, approver or approved revision outside the history list. | One line: approved by, when, revision. |
| M6-9 | After "Restore my input" on reload, "Resolve the saved-versus-typed changes… Compare with saved version" stays on screen. | Clear it once the operator has chosen. |
| M6-10 | Still present from M5: raw "Expecting value: line 1 column 1 (char 0)" when written rules are set to a JSON category; focus drops to the page body after "Add and save source". | As M5-5 and M5-8. |

## M5-1 and M5-2 recheck

| Finding | Status | Evidence |
|---|---|---|
| M5-1 inventory does not show which values repeat | Fixed | Search by value; repeated value with source name, example number and neighbouring fields; no-match message; disclosures open by keyboard with a visible focus ring; no overflow at 430px; both domains |
| M5-2 two answer areas, unexplained disabled button | Fixed | One box per recorded question; visible reason; typed answer kept through polling, navigation and reload; no send or approval; consent gate unchanged |

Not re-exercised for this recheck: legacy answer restoration, tenant switch while editing, sign-out
storage clearing, cancel and late responses.

## Verdicts

| Area | Verdict | Scope |
|---|---|---|
| Functionality | Pass | Intake, inventory, unresolved state, request preparation, failed send and recovery, failures kept on rerun, handoff gates; three domains on my copies |
| Visual clarity | Pass with M6-1 to fix before human sessions | Tested screens at 1440px and 430px |
| AI helpfulness | Pass, narrow | One guided live CRM revision and one guided unresolved procurement proposal, judged from records; syntax leakage in M6-3. Not general self-service. |
| Integration | Pass on recorded evidence | PDLC 111 checks on memory and Spanner with matching identities and verified cleanup; earlier timeout unexplained |
| Tested accessibility | Pass, narrow | Reflow, labelled controls, visible focus on inventory disclosures, link focus to the questions heading. No screen reader or full keyboard pass. |

## Before the operator sessions

1. Fix M6-1 and recheck with one save.
2. Reword or re-evidence the CRM result per M6-2.
3. Then run the 3 to 5 operator sessions described in the handoff. Until they happen, nothing here is
   evidence of human comprehension.

Still open and not closed by this review: M6-3 to M6-10, M5-3 to M5-9, M4 RR-2 to RR-4 and M4-4 to
M4-12, the M0, M2b and M3 lows, the partial source-race trace, and the unexercised recovery states
listed above.

My services on ports 8109, 8112, 8114, 8116, 8118, 8120, 8124, 8131 and 8140 are still running and can
be stopped.
