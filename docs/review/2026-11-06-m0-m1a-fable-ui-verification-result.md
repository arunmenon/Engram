# Independent verification of Engram M0 and M1a — UI result

Reviewer: Claude Fable 5.1 (independent, review only). Date: 2026-11-06.
Script followed: `docs/review/2026-11-06-m0-m1a-fable-ui-verification.md`.
Evidence: `output/playwright/ai-native-onboarding/fable-m0-m1a-20261106/` (README has the
screenshot index; `screens/shot-NN.jpg` below refers to that folder).

Constraints honoured: no product code or expected answers edited, no pack approved, no
tenant activated, no live provider called, ports 8104/8101/5174 untouched, no service
restarted. The 8102 fixture returns canned output and is not counted as reasoning. The
uncoached persona pass was done before reading the detailed criteria and without reading
implementation code.

## 1. Verdicts

| Scope | Verdict | One-line basis |
|---|---|---|
| M0 deliverables | **PARTIAL** | Tests, probes and CRM adaptation are real and reproducible; "baseline" rests on simulated personas, historical PDLC/Northstar results, an unset independent reviewer and an unbuilt procurement pack. |
| M1a functionality | **PASS with two REVISE items** | Explain, prepare, send, stale fencing, consent gate, cancel and single-submission all behaved as specified. Two defects: save-race loses the operator's answer, and restore-after-reload leaves a prepared request the operator cannot see or clear from the inline panel. |
| M1a usability | **REVISE** | A domain operator can answer and prepare a request, but cannot tell what the request will change, is misdirected by the next-action banner, sees duplicated controls, and loses place on long pages. |
| M1a AI-native helpfulness | **REVISE (bounded)** | On 8102 the explanation turns an engine error into a business statement with evidence and an editable instruction. On 8103 the agent question is useful once, then the follow-up repeats itself. Nothing previews consequences; the inline flow mostly wraps operator words in boilerplate. |
| "Safe request preparation" claim | **ACCEPT** | No unintended submission, no consent bypass, no stale-result use, one call per click, draft unchanged until an explicit send. |
| "Self-serve issue resolution" claim | **DO NOT ACCEPT** | The operator ends with a prepared sentence, not a resolved issue; consequence, grounding and recovery still need engineering help in the cases exercised. |

Decision in section 8: accept M1a only for the narrower claim, with five named changes
before the broader claim is re-reviewed.

## 2. Environment, build, drafts, method

See the evidence README for the table. Summary: HEAD 27b4ba86 (dirty tree, 519 entries;
`tests/fixtures/workbench/` and `tests/unit/test_workbench_explain.py` untracked, so the
tested explain behaviour is not yet committed). Frontend bundle `workbench-HsHYTt5P.js`
on both fixture servers. Engine revision sha256:6b54ae55…. 8102 is the canned fixture agent
(operator fixture-reviewer); 8103 is the controlled fixture (operator domain-study) whose
author fails if invoked. Browser method: Claude-in-Chrome on the user's Chrome for every
task; one headed Playwright run only for the 430px keyboard pass. Failure injection was an
in-page fetch patch, not server changes. Isolated copies were created with the script's
setup command; revisions moved 2→4 (delivery), 2→2 (crm), 2→3 (save-race). Both 8102
drafts stayed at revisions 4 and 2.

Tooling miss to disclose: my first attempt to type into "Your answer" used a coordinate
click that did not focus the textarea; the keystrokes scrolled the page to the bottom and
the text was lost (shot-04). I repeated with the element reference. This is not a UI
defect and is not counted below.

## 3. Uncoached persona outcomes

Personas are simulated by the reviewer; no human timings or quotes are claimed.

### Persona A — delivery team lead, isolated delivery copy (8103)

Task: resolve the open item about failed and rerun TestRuns.

| Measure | Observed |
|---|---|
| Actions to reach the issue | 4 (open draft, read setup, step 2, step 3) |
| Actions to a prepared request | 12 including one recovery from the lost text |
| Hesitations | 3: banner pointed to "Add the missing tenant evidence → Go to what describes their world?" instead of the item; "Review my request" vs "Send request" vs "Send changes to the agent" at the bottom; whether "Leave unresolved" would discard the answer |
| Help needed | None to prepare; engineering help needed to know what the pack would do with the answer |
| Outcome | Request prepared, deliberately left unresolved; revision stayed 2; only polling GETs, no explain or author call (shot-05, 06, 09) |

What the persona could not do: say what "release readiness uses the latest completed
attempt" would change in the pack, or whether the issue text ("TestRun", "TestCase")
matches the team's vocabulary. Incident placeholders ("Incident runbook · section 2",
"Insert an example event") appear in a delivery draft.

### Persona B — CRM operations analyst, isolated CRM copy (8103)

Task: answer the contact-identity item in CRM terms.

| Measure | Observed |
|---|---|
| Actions to a prepared request | 7 |
| Hesitations | 2: the pack's current rule ("Contact — Identified by email") is only visible under the graph below the issue; unsure whether a prepared request means the proposal was adopted |
| Help needed | Found "Technical details" alone; engineering not required to prepare |
| Outcome | Request prepared with CRM wording, revision 2, no agent call (shot-10 to 12) |

### Persona C — operator inspecting fixtures on 8102

Explanation-review draft: found the unsupported-setting problem under "Engram's pack checks
need attention", asked for an explanation in one click, read "This is a configuration
problem; it does not mean your incident data is wrong", expanded evidence and the exact
instruction, pressed "Propose this change" and saw the editable request without a send
(shot-43 to 45; network: one POST /explain, no /author). Procurement draft: with no pack
built, "Explain this" on the authoring failure produced a business reading ("could not
match its supporting quotations … your saved inputs are still available") and a retry
instruction that preserves the seven questions (shot-46, 47). 8102 output is canned, so this
shows the presentation path works, not that an agent reasons.

## 4. UI-01 to UI-08

| Task | Verdict | Evidence and notes |
|---|---|---|
| UI-01 Find the issue, decide where to start | REVISE | Issue is reachable in 3 clicks, but the NEXT ACTION card on every step says "Add the missing tenant evidence" and links to step 2 (shot-00 to 03, 37). The readiness checklist on 8102 correctly says "Revalidate after the engine changed" and does not claim samples exist (shot-42). Tenant cards say "Continue at Tenant setup" regardless of where the issue is (shot-40). |
| UI-02 Answer and review in place | PASS | Prepared request appears inline under the item with a live "Request prepared here. Review it before sending." status; a second Review with edited text is refused with "Your revision request already has text…" and the edit is kept (shot-05, 13). Request text is operator words plus boilerplate; the same text is mirrored into the bottom "What should change?" box with its own send button (shot-33, 34). |
| UI-03 Optional help, grounding, uncertainty | PASS on 8102 / REVISE on 8103 | 8102: issue-specific "What this means", "Why the agent says this" with the recorded engine check and supported settings, "Inspect the exact revision request", "Propose this change" (shot-43 to 45). 8103: one click, one POST, loading state with "Stop waiting", result asks a grounded question about stable identifiers (shot-14, 15); but "Ask a different question" returns the identical answer and does not echo the question (shot-16, 17, scripted fixture limit), and no engine-vs-source distinction is shown. Prepared request header changes to "Regarding this question: …" which later becomes stale. |
| UI-04 Material detour, deferral, discard | PASS | Material screen says "Your question and explanation are saved while you add material"; answer and request survive the return (shot-07, 08). "Leave unresolved" says nothing was sent or approved. "Clear prepared request" removes both copies, keeps the answer, but scrolls the page to the graph (shot-18). |
| UI-05 Saved evidence invalidates explanations | REVISE | After adding a source (rev 3): Explain and Review disabled, "Update the proposal before asking about it.", explanation removed, stale banner shown, server returns 409 "Draft changed. Reload before continuing." for a revision-2 explain, cross-token call 401 (shot-19 to 23). Defect: the typed "Your answer" is lost, while the prepared request that quotes the now-removed agent question stays sendable with no stale label. |
| UI-06 Failure, cancel, reload, explicit send | PASS with one REVISE | Delayed explain + "Stop waiting": clear message, late response never rendered (shot-24 to 26). Provider 502: inputs retained, revision unchanged, but the raw text "FABLE controlled provider error" is shown to the operator (shot-27). Intercepted /author 503: exactly one POST per click, alert "FABLE controlled 503: authoring service unavailable", request retained and editable, deliberate retry made a second call (shot-35, 36). Note: the UI saves the draft before sending, so a failed send still bumps the revision (2→3) and triggers the "earlier proposal" banner and disabled Explain. Reload: token is in memory so sign-in repeats; the draft reopens scrolled mid-page with the "Restore what you typed?" prompt out of view (shot-29, 30); Restore puts text only into the bottom "What should change?" box and "Your answer" is not recovered; "Review my request" is then refused with "already has text" while no request or clear control is visible in the inline panel (shot-31, 32). |
| UI-07 Consent, tenant boundary, neutrality | PASS | With Permission set to "Keep inputs local — do not call the agent" (saved as rev 4): Explain, Review, Send, Apply and Check disabled; remedy text "Allow provider use and confirm redaction in Tenant setup first." (shot-37). Switching delivery → CRM → delivery showed no leaked answers or requests (shot-38). Sign out cleared all `engram-edit:*` sessionStorage keys; step-position keys remain in localStorage (non-sensitive). CRM and delivery use the same interaction; procurement is honest about having no pack. |
| UI-08 Keyboard and narrow width | PASS with notes | 430px: no horizontal overflow (scrollWidth 430), visible 3px focus outline on every stop, Tab from "Your answer" lands on "Review my request", Enter prepares the request and a polite live region announces it (`narrow-check.json`, narrow-430-prepared.png). Notes: focus drops to body after preparing, so a keyboard user must tab back into the panel; page height grows from 3347 to 4309px; the request textarea is 249px wide and needs internal scrolling (scrollHeight 363 vs 183). |

Not exercised: live provider reasoning (forbidden), real human operators, a successful
author round trip on 8103 (author fails by design), explanation of a limitation on 8102
beyond the invalid setting and authoring failure, cross-tab restore after sign-out
(storage is cleared, so nothing to restore), screen-reader output, a true Playwright trace
of the main pass (extension screenshots and network logs stand in).

## 5. Prioritised findings

Severity anchors: **High** = data loss, unintended submission, consent/stale bypass or a
blocked operator; **Medium** = operator needs engineering help or is likely to act on the
wrong thing; **Low** = friction.

| # | Sev | Screen / control | Observed | Operator consequence | Smallest correction | Recheck |
|---|---|---|---|---|---|---|
| 1 | High | Step 3 inline panel after a save that bumps the revision (UI-05, UI-06 send) | "Your answer" is cleared; prepared request stays sendable and quotes the removed agent question; no stale label on it | Typed policy is lost; a stale instruction can be sent as current | Retain the answer text across revision change; mark the prepared request stale and require re-review before send | Repeat UI-05 on a fresh copy; expect answer retained and Send disabled until Review |
| 2 | High | Reload → "Restore what you typed?" → Restore | Text restored only into bottom "What should change?"; inline panel shows no request; "Review my request" refused with "already has text" and no clear control in view | Operator is stuck without knowing where the text went | Restore into the inline panel for the matching item, or show the request and Clear control wherever the refusal appears | UI-06 reload step; expect request visible and clearable next to the refusal |
| 3 | Medium | NEXT ACTION card, all steps (8103 copies) | "Add the missing tenant evidence → Go to what describes their world?" while the open item is on step 3 | First-time operator leaves the issue to add sources | When unresolved review items exist, name the item and link to it; demote evidence collection to the readiness checklist | UI-01 on delivery copy; expect card to name the TestRun item |
| 4 | Medium | Step 3, "Your request to the agent" | Request is operator words wrapped in boilerplate; no statement of which pack element may change | Cannot judge consequence; "Review my request" reviews wording, not effect | Show the affected pack rule or entity next to the request (e.g. "May change: TestRun → Release readiness rule") and label what is unverified | Persona A; expect the consequence line to be present |
| 5 | Medium | Step 3, duplicated send paths | Inline "Send request to the agent" and bottom "Send changes to the agent" carry the same text | Two ways to submit the same job; unclear whether both would send twice | Collapse the bottom section when an inline request exists, or make it read-only with a link to the inline panel | UI-02; expect one enabled send control |
| 6 | Medium | Provider error alert | Raw provider text ("FABLE controlled provider error") shown verbatim | Operator sees engineering wording with no next step | Wrap in "The agent could not answer. Your inputs are kept. Try again or leave unresolved." and keep the raw text under a disclosure | UI-06 502 case |
| 7 | Medium | Failed send after revision bump | A failed /author still saved the draft (rev 2→3) and raised "This is an earlier proposal…" with Explain disabled | Operator cannot explain the item after a failed send without a fresh proposal | Either save only on success, or keep Explain enabled against the saved revision | UI-06 503 case; expect Explain enabled after failure |
| 8 | Medium | 8103 "Ask a different question" | Same answer returned regardless of question; question not echoed | Follow-up feels ignored | Fixture limit, but the UI should echo the question above the answer so the mismatch is visible | UI-03 step 3 |
| 9 | Low | Delivery draft content | Incident placeholders and "TestRun/TestCase" wording in a delivery domain | Vocabulary mismatch for the team | Domain-aware placeholders; use the tenant's terms from sources | Persona A |
| 10 | Low | Scroll behaviour | Clear prepared request and the post-reload open scroll to the graph or mid-page; restore prompt out of view | Loses place; may miss the prompt | Keep scroll position on clear; scroll restore prompt into view or anchor it to the panel | UI-04, UI-06 |
| 11 | Low | Keyboard focus after prepare | Focus returns to body | Extra tabbing at 430px | Move focus to the "Request to send" textarea | UI-08 |
| 12 | Low | Tenant cards | "Continue at Tenant setup" for every draft | Misleading entry point | Derive the label from the next action | UI-01 |

## 6. AI-native assessment (section 5 of the script)

| Capability | Observed | Credit |
|---|---|---|
| Issue-specific explanation | 8102: explanation names the recorded engine check, says the data is not wrong, and proposes a specific instruction. 8103: generic "Help the agent understand this" question, same for any follow-up | Useful on 8102 (canned); partial on 8103 |
| Business-language clarification | Operators typed team policy in their own words; nothing demanded engine syntax | Credit |
| Grounded uncertainty | 8103 asked for a stable identifier and history behaviour, which is a real missing decision; no invented relationship seen | Credit, once |
| Explain-or-propose with explicit control | Prepare, edit, clear, send and accept are separate; "No change has been applied" is explicit | Credit, with finding 5 (duplicate send) |
| Context continuity | Same-revision return retains work; stale fencing works server-side and in the UI | Partial: findings 1 and 2 lose the operator's text |
| Safe failure recovery | Clear failures, retained request, deliberate retry | Partial: findings 6 and 7 |
| Domain-agnostic operation | Delivery and CRM use the same flow; procurement is honest about no pack | Credit; placeholders leak incident wording (finding 9) |

What still feels like a form around agent output: the inline "Your request to the agent"
panel. It restates the operator's sentence with fixed boilerplate, offers no preview of
effect, and its only "review" is re-reading the words. The 8102 explanation path is the
one place where the UI adds information the operator did not already have, and that path
is canned on both fixtures, so live helpfulness remains unproven here.

### 6a. Clutter and intuitiveness by screen

| Screen | Clutter reading | Intuitiveness reading | Evidence |
|---|---|---|---|
| Tenant list (8102/8103) | Moderate: a large "See how a prepared pack behaves" story panel sits above the draft cards | Cards say "Continue at Tenant setup" for every draft, so the entry point does not reflect the real next step | shot-40 |
| Tenant setup / step 2 | Low | Next-action card dominates and sends the operator to add evidence even when the issue is elsewhere | shot-00, 01, 37 |
| Step 3 "How Engram understands them" | High: next-action card, readiness checklist, review item with its own panel, pack overview, technical details, stale banner, schema graph, recorded decisions, pack checks, accept button, change-request section and engineer section in one column (page height 2800 to 4300px) | Three send-shaped controls (Review my request, Send request to the agent, Send changes to the agent) and two text boxes holding the same text; the operator must infer which one matters | shot-02 to 06, 33 to 35, narrow-430-full.png |
| Inline explanation result (8103) | Low | Clear loading and result states; the result header reuses the question but the follow-up repeats the same answer | shot-14 to 17 |
| Inline explanation result (8102) | Moderate: "What this means", evidence, next step and exact instruction stack under the item, with raw JSON in "Supported engine settings" | The order explanation → evidence → instruction → propose reads naturally; JSON is behind a disclosure | shot-43 to 45 |
| Add supporting material | Low | Saves context visibly and returns cleanly | shot-07, 08 |
| Restore prompt after reload | Low on its own | Out of view on open, and its result lands in the wrong box | shot-29 to 32 |
| 430px view | Moderate: the request textarea needs internal scrolling and every section stacks | Tab order follows reading order; focus is visible | narrow-430-prepared.png |

Net reading: the step 3 page is the clutter problem. Everything is present, but optional
detail is not optional enough, and the same action is offered in two places.

## 7. M0 evidence and claim reconciliation

| Claim or artefact | Status | Note |
|---|---|---|
| 506 unit tests pass (pytest.log, manifest 435 files at 27b4ba8) | Confirmed from documents | Not re-run by me; the M1a README reports 521/525 with the untracked explain tests |
| Capability probes | Confirmed | No-intent, relationship-free lookup passes; only a named intent without edges fails. The plan's "every question requires a domain relationship" wording must not be repeated |
| CRM contract adaptation | Partial | Two questions covered; three answer.reasons cases outside the carrier; reviewer field unset, so author-reviewed only |
| Procurement pack | Unverified | Inputs present; HarborWorks rev 24 and the 8102 recovery fixture both show the authoring failure with no pack |
| PDLC 111 checks, Northstar success | Historical | Recorded under an earlier engine; the UI itself says revalidate (shot-42) |
| Operator baseline | Simulated only | README heading "Operator baseline protocol (not yet run)" contradicts the later persona reports; the personas are AI walkthroughs, not recruited humans |
| "M0 complete" (earlier chat statement) | Overstated | Complete: tests, probes, CRM adaptation, persona walkthroughs. Partial: expectation review. Unverified: human baseline, procurement, fresh PDLC run |

Inherited versus introduced: findings 3, 9, 10 (scroll), 12 and the raw-error wording
are inherited from M0 screens the personas already flagged (generic next action, stale
success labels, density). Findings 1, 2, 4, 5, 7, 8 and 11 are introduced by the M1a
inline review and explain controls.

Scope gaps: no human operators, no live agent, no end-to-end author success on 8103, no
tenant activation path exercised, no screen-reader pass.

## 8. Decision

**Accept M1a for the narrower claim only:** operators can safely prepare, inspect, defer,
clear and deliberately send a request, with consent and stale-revision fencing enforced,
on fixture agents. **Do not accept** the "self-serve issue resolution" or "AI-native
helpfulness" claims yet.

Named changes before re-review, in order: finding 1 (answer loss and stale request after
revision change), finding 2 (restore puts text where the operator cannot act on it),
finding 3 (next-action card misdirects), finding 4 (no consequence preview), finding 5
(duplicate send paths). Findings 6 and 7 should ride along in the same fix. Re-run UI-01,
UI-02, UI-05 and UI-06 on fresh isolated copies after the changes; the rest of this
report can stand.
