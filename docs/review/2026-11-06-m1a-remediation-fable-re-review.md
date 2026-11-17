# M1a remediation — independent re-review (Fable)

Reviewer: Claude Fable 5.1. Date: 2026-11-06. Review only; no fixes implemented, no
pack, expected answer, approval or activation touched, no live provider or Spanner run.
Inputs: `2026-11-06-m0-m1a-fable-ui-verification-result.md` (my original review, unchanged),
`2026-11-06-m1a-fable-remediation.md`, `docs/ai-native-onboarding-milestone-plan.md`, and
`output/playwright/ai-native-onboarding/fable-remediation-20261106/`.
My evidence: `output/playwright/ai-native-onboarding/fable-rr-20261106/` (README lists the
environment, the five Fable-owned isolated copies with start and end revisions, and every
screenshot and JSON file; `sN-` prefixes below refer to it).

Method note: the service on 8105 was verified available first. The browser was headed
Google Chrome driven by Playwright, because the Claude-in-Chrome extension needs the token
typed through a tool call and the token file may not be printed. Scripts read the token
file directly; it appears nowhere in the evidence. Fixture explanations are canned and are
not treated as live reasoning, successful authoring or self-serve resolution.

## 1. Per-finding verdicts

| # | Original finding | Verdict | Evidence |
|---|---|---|---|
| 1 | Save bumps the revision, "Your answer" is lost, stale request still sendable | **Fixed** | S3 source save (rev 2→3): answer retained (96 chars), explanation removed, Explain and Review disabled with "Update the proposal before asking about it.", request marked "This request needs review…" and Send disabled until "I reviewed this request against the current draft" (s3-04). S4 failed send (rev 2→3): same retention and gate (s4-01). Server: stale explain → 409. |
| 2 | Restore after reload puts text where the operator cannot act on it | **Fixed** | S1: after reload and sign-in, "Restore my input" returns both the answer (123 chars) and the request (534 chars) into the inline panel (`inline_panel_has_request` = 1), Send disabled until review, Clear keeps the answer and focuses it (s1-05, s1-06). The "Restore what you typed?" prompt is still rendered above the fold at scrollY 0 but its box starts below the viewport on first paint (`restore_prompt_in_view` false); the operator sees it on the first scroll. Minor, see note A. |
| 3 | Next-action banner sends the operator to add evidence | **Fixed** | Delivery: "Review the open item" followed by the TestRun policy sentence. CRM: same pattern with the contact-identity sentence. On the material screen it becomes "Review your prepared request" with a return button (s1-01, s3-03). Exception: with provider permission set to local only, the banner reverts to "Add the missing tenant evidence" (s7-01); the panel remedy text still says what to do. See note B. |
| 4 | No consequence preview | **Partial** | "What this request may affect" now shows the operator's outcome in their words, the records mentioned, each record's current key, states and updating events, and an explicit "not verified yet" sentence (s1-02, s3-02). This separates current rules, requested outcome and unverified consequence as asked. It is still written in declared type and event names (`pdlc.testcaserun.finished`, `repo + test_id`), so a delivery lead reads it as engineering vocabulary. Functionally fixed; usability limit remains, as the remediation itself states. |
| 5 | Duplicate send paths | **Fixed** | Exactly one "Send request to the agent" and one "Request to send" textarea while a request exists; the bottom "Ask the agent to change this pack" section no longer offers its own send (s1-02-prepared-full). A second "Review my request" with a request present shows "Your revision request already has text…" plus a "Review or clear the existing request" button that focuses the request (S5). |
| 6 | Raw provider text in the failure alert | **Fixed** | Alert reads "The agent could not start. Your answer and request are kept. Review the saved draft, then retry when ready." The injected detail is hidden until "Error details for support" is expanded (s4-01, s4-02). |
| 7 | Failed send disables explanation of the retained proposal | **Fixed within its stated limit** | After the 503, Explain is enabled and the panel says "This explains the retained proposal. Your new request has not been applied yet." (s4-03). After a source change the same control is disabled and the server returns 409 "Wait for a current proposal before asking about it". The rule that a later instruction-only save cannot reopen the exception is covered by the backend test only; not exercised in the UI. |

No regression found against the original PASS items: consent gate still disables
Explain, Review, Apply and Check with the remedy sentence (s7-01); cross-token access
returns 401; one `/author` call per click, two after a deliberate retry (S4 `calls`);
no page errors in any scenario.

## 2. Verification checklist from the request

| Check | Result |
|---|---|
| Typed answers survive saves, reloads and failed sends | Yes (S3, S1, S4). Legacy records without answer data cannot restore the answer; the UI says the request was recovered and keeps the empty answer box (S5). |
| Restored requests appear in the inline review panel | Yes for current records (S1). Legacy records restore into a visible fallback panel above the issue list, outside the item panel, with review, send and clear controls (s5-01). |
| Draft or answer changes require re-review before sending | Yes. Send is disabled with the "needs review" notice after a source save, a failed send and a restore; one explicit click re-enables it (S1, S3, S4, S5). |
| No invisible-text dead end | Yes. The "already has text" refusal now carries a button that focuses the existing request (S5). |
| Banner names the current issue | Yes, except under the local-only consent state (note B). |
| One request editor and send path | Yes (S1, S6). |
| Preview distinguishes current rules, requested outcome, unverified consequence | Yes in structure; vocabulary is engineering-level (finding 4). |
| Failure messages explain recovery, technical detail secondary | Yes (S4). |
| Fresh explanation of a retained proposal only in the instruction-only case; source change and consent enforced | Yes in the UI and on the server for the cases run; the "cannot reopen after a source change" rule is backend-test evidence only. |

## 3. Simulated personas (not human research)

**Delivery lead (Fable RR — delivery).** Opened step 3 and read a banner that quoted the
exact policy gap, so no search was needed. Typed the team rule in plain words. The preview
told them which records are involved and that the exact change is not verified, but
"identified by run_id, updated by pdlc.testcaserun.finished" told them nothing they could
act on. They could reload, restore and clear without losing words. Actions to a reviewed
request: 5. Hesitation: 1, at the preview list. Engineering help needed: none to prepare;
still needed to judge whether "latest completed attempt" is representable.

**CRM analyst (Fable RR — source-save).** Asked for an explanation first; the fixture's
question ("Should contact history stay with the same person when their email changes?")
was a real missing decision and the panel now echoes what they asked. They answered, added
a synthetic policy note, returned, and found their answer kept, the old explanation gone,
and the request flagged for review. Actions: 9. Hesitation: 1, on whether "Update the
proposal before asking about it" was something they could do themselves (it is not; it
needs the agent run). Engineering help needed: none to recover.

## 4. Verdicts

| Scope | Verdict | Basis |
|---|---|---|
| Functionality | **PASS** | All seven items behave as the remediation describes on fresh isolated copies, with server-side fencing confirmed. |
| Usability | **PASS for the bounded M1a claim, with two low-severity notes** | Issue identification, retention, recovery and single submission are now achievable without engineering help. The preview and the legacy fallback still speak in engine vocabulary (notes A to C). |
| AI-native helpfulness | **REVISE, unchanged in kind** | The remediation improves control and continuity, not reasoning. The fixture question is useful once; the preview is a grounded scope list, not an effect prediction. Nothing here proves live reasoning, successful authoring or self-serve resolution, and the remediation does not claim it. |

Answers to the seven questions: (1) the issue is readable without engine terms, yes;
(2) what to provide and why is clear from the panel copy, yes; (3) agent knowledge versus
uncertainty is stated in the preview and in "This explains the retained proposal…", yes
within the fixture; (4) what the request may affect is listed but in engine names, partly;
(5) recovery without losing work or knowing internals, yes; (6) the interaction adds a
78-word preview and one extra confirmation click after any change, which is acceptable for
the safety it buys, but step 3 is now about 5600px tall at 1440px once a request exists;
(7) it moves the operator to a reviewable request, not to resolution.

## 5. Remaining defects and notes (smallest corrections only)

| Note | Severity | Reproduction | Smallest correction |
|---|---|---|---|
| A. Restore prompt below the fold on reopen | Low | S1: reload, sign in, open the draft; the "Restore what you typed?" box starts below the first viewport until the user scrolls (s1-04) | Scroll the prompt into view or render it before the step header |
| B. Banner reverts under local-only consent | Low | S7: set permission to local only, continue, open step 3; banner says "Add the missing tenant evidence" while the panel says "Allow provider use and confirm redaction in Tenant setup first." (s7-01) | Let the banner name the consent prerequisite when an open item exists |
| C. Legacy fallback shows placeholder words as the operator's outcome | Low | S5: restore a record without request metadata; the preview reads "Requested outcome — your words: Review the instruction below." and lists seven records (s5-01) | Omit the outcome line and the record list when the origin is unknown |
| D. Clear in the legacy panel returns focus to body | Low | S5 after clearing the fallback request | Focus "Your answer" as the inline panel already does |
| E. Preview vocabulary | Usability limit, acknowledged by the remediation | Any prepared request (s1-02) | Out of scope for M1a; carry to the catalog or later milestone rather than expand M1a |

Not exercised: live provider, successful author round trip, Spanner, human operators,
screen reader, the backend-only "cannot reopen after source change" rule, the implementer's
own five drafts (left at their recorded revisions).

## 6. M1a acceptance recommendation

**Accept M1a for the bounded claim**: an operator who knows their business can identify
the open item, answer in their own words, see what records a request may touch and what is
unverified, recover their words after a save, reload or failed send, and deliberately
submit one reviewed request on fixture agents. Notes A to D are low severity and can be
fixed without re-review; none should block acceptance.

**Do not extend the claim** to self-serve issue resolution, live reasoning, successful
authoring or independent expected answers. Those remain separate acceptance evidence, as
the remediation document already states. M0 remains partial as recorded in my original
review; nothing here changes that.
