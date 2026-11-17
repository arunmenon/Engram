# M3 clarity fixes: independent re-review

## Verdict

**M3 is accepted for its bounded fixture scope.** The three acceptance blockers (M3-1, M3-3, M3-5) are
fixed, and the included M3-2 and M3-4 improvements hold. I found no functional or safety regression.
Five new low-severity clarity notes are listed below; none blocks M3. M3-6, M3-7 and M3-8 stay open as
documented lows. Every other milestone gate stays open.

This acceptance covers fixture-agent behaviour with the genuine planner. It is not evidence of live
reasoning, successful live authoring, Spanner execution, self-serve readiness or human comprehension.

## Reproducibility

| Item | Value |
|---|---|
| Reviewer | Fable (Claude), independent re-review. Not the implementer. No fixes made. |
| Date | 2026-11-10, Asia/Kolkata |
| Prior familiarity | I wrote the original M3 review and read the changed code before this run. This is a directed recheck, not an uncoached first-use study. |
| Branch, commit | feature/engram-walkthrough, HEAD 27b4ba8, large dirty and untracked tree (workbench sources untracked) |
| Frontend bundle | `workbench-QDNA5dIB.js`, sha256 b4d481a1…, `workbench-CqPRbaYs.css`. All seven file hashes and three snapshot hashes match the implementer manifest. |
| Engine revision | sha256:7f033eeb… loaded by my service from current files |
| Service | http://127.0.0.1:8116/workbench.html, operator `fable-m3-rr`, own SQLite store, started after the last source write |
| Agent and storage | Fixture explainer, fixture author, genuine planner, SQLite drafts. No provider, sandbox or Spanner. |
| Browser | Headed Google Chrome through Python Playwright, 1440×1000 and 430×932, default zoom |
| Credentials | Generated and read inside scripts; never printed or passed through tool arguments |
| Evidence | `output/playwright/ai-native-onboarding/fable-m3rr-20261110/` |
| Preserved | Implementer service 8115 and its copies, and my earlier services and copies, were not touched |

### Reviewer-owned copies

| Copy | Draft ID | Source snapshot | Revisions | Why it moved |
|---|---|---|---|---|
| Fable RR — Support account identity | 3b3388e8 | copies-start.json 35fa93d7 | 2 → 12 | Two source edits, fixture author runs (three rejected or failed, two completed) |
| Fable RR — Support resolution rules | 76491e3c | copies-start.json 3631e937 | 2 → 2 | |
| Fable RR — Support missing transition sample | 160ffc1e | copies-start.json c97dcef5 | 2 → 2 | |
| Fable RR — Support source recheck | 74a83e0c | final-support-start.json 4a7f94ca | 2 → 5 | One source edit, two rejected fixture author runs |
| Fable RR — CRM contact history | 46ad5398 | crm-copy-start.json f4ad2f58 | 2 → 5 | One gated send to the failing fixture author |
| Fable RR — Support repeated resolution example | d3ae1a38 | Reviewer variant of 3631e937 with one added sample | 2 → 2 | |

Pack, recorded decisions and questions equal the start snapshot on all six copies. Review and approval
remain empty on all six. Source text differs only on the two copies where I edited it on purpose.

## Acceptance blockers

### 1. Relationship counts (M3-1): fixed

- CRM, "Start a separate history for each email": main view reads "works at: 2 → 3 (3 links added,
  2 removed)". Planner output has three WORKS_AT links after and two before, with all contact
  endpoints changed. The count matches the planner exactly.
- CRM, "Keep history by contact number": "works at: 2 → 2 (unchanged)".
- Provenance links appear only inside "Inspect current and proposed rules" as "3 before, 3 with this
  choice", labelled separate from business relationships.
- Support identity, both options: "No business relationship change in these examples." Planner
  reports zero business links before and after.

### 2. Lifecycle comparison (M3-3): fixed

- Resolution copy: "Sample 3: current rule requests “resolved”, allowed from open; proposed rule
  requests “resolved”, allowed from open, resolved." It then says the sample does not exercise the
  difference for starting state "resolved" and tells the operator to add a sequence with a record
  already in that state.
- The panel states it "does not execute state changes or confirm which requests would be accepted"
  and that "matching requests are not proof of matching results". Nothing reads as an accepted or
  executed transition.
- Reviewer variant with a second resolution of the same case: the missing-example note stays on
  sample 3 and is absent on sample 4, which is correct. The panel still makes no outcome claim.
- Missing-sample copy: Prepare is disabled, linked by `aria-describedby` to the reason and remedy.

### 3. Source change and withdrawal (M3-5): fixed

Run on one browser session against the identity copy (`r2c.json`):

| Step | Observed |
|---|---|
| Explained | Two options, Explain enabled, no notice |
| Source edited, seen by polling | Options removed. Explain disabled. Visible text: "Options withdrawn because the draft changed. Update the proposal before asking about it." The button's `aria-describedby` points at that text (role status). Same at 430px, no overflow. |
| Leave the step and return while stale | Notice and disabled reason persist |
| Explain called directly while stale | 409 |
| Fresh proposal through "Send changes to the agent" | Explain enabled. Notice changes to "Ask again to compare choices against the current draft." |
| Ask again | Options return. Notice gone. |
| Wait through polls, leave and return, 430px | Notice stays gone |
| Reload and sign in | No notice, no stale options |

## Included improvements

- **M3-2, fixed.** Records read "account: east · number: 42", "number: 42", "contact id: C1",
  "email: ann.new@acme.com". No operator needs the JSON to name a record.
- **M3-4, fixed.** The decision reference is labelled "Recorded decision" and shows the question and
  effect as a sentence. "Supplied material for this decision" lists both conflicting policy excerpts
  although the fixture agent cites only the decision. Its lead-in says the preview does not settle
  conflicting policies.

## Other checks

| Check | Result |
|---|---|
| Keyboard | Eight Tab stops from the answer to the second Prepare, visible 3px focus ring, Enter prepares, focus lands in "Request to send" |
| One request editor | Exactly one after prepare, restore and failed send |
| Existing text | A second choice is refused with "Your existing request is kept. This choice was not added." Edited text unchanged. |
| Clear | Editor removed |
| 430px | No horizontal overflow in any of the five explained states or the stale state |
| Reload and restore (M2b) | Restore offered, text returned, focus in the editor |
| Review gate (M2b) | Send disabled until "I reviewed this request against the current draft" |
| Failed send (M2b) | Request text retained after the fixture author failed; previous pack retained |
| No mutation from preview | Thirteen explain calls; pack, decisions, questions, review and approval unchanged on every copy |
| Fail closed on authoring | The server rejected two malformed fixture proposals (missing summary, no source citation) and kept the prior proposal |
| Tests | 178 workbench unit, 12 decision-preview, 18 frontend helper: all pass |

Not re-run in this pass: the adversarial explainer modes, timeout capacity, legacy restore, consent
change, sign-out clearing, review ticks and Keep this data. Those were covered on the previous bundle
in the first M3 review and the changed files do not touch them.

## New findings, all low

| ID | Component | Operator consequence | Smallest correction |
|---|---|---|---|
| RR-1 | Record list | Event names run straight into the sample numbers: "sample events 4, 12crm contact added". Reads as a typo. | Add a separator or put the event names on their own line. |
| RR-2 | Relationship line | "(3 links added, 2 removed)" gives no reason. The operator must infer that changing the contact key replaces Ann's and Bo's existing links. | Add a clause such as "because these contacts get new identities". |
| RR-3 | Stale remedy | The reason says "Update the proposal" but the control is named "Send changes to the agent". The Next action banner still says "Add the missing tenant evidence", as it did before the change. | Name the same control in the reason. Banner wording is inherited and belongs with the open M2b language items. |
| RR-4 | Lifecycle with a repeat example | Samples 3 and 4 show identical lines. Nothing says sample 4 is the one where the two rules can differ. | Without claiming an outcome, mark the sample that follows an earlier request for the changed starting state. |
| RR-5 | Supplied material | Excerpts are labelled by internal source id ("scope", "legacy") and include raw sample and schema JSON. | Show the document name; keep raw samples below the policy excerpts. |

Still open from the first review and not claimed fixed: M3-6 stale status messages, M3-7 the 429
wording after Stop waiting, M3-8 the generated "I chose" label and JSON inside the editable request.
I saw the M3-8 JSON again in this run.

## Verdicts

| Area | Verdict | Accepted scope |
|---|---|---|
| Functionality | Pass | Identity and lifecycle previews, missing coverage, withdrawal, prepare, recovery spot-checks, fixture agent |
| Visual clarity | Pass with lows | Comparison, lifecycle and stale states at 1440 and 430; RR-1 to RR-5 and M3-6 to M3-8 open |
| AI helpfulness | Not exercised | Fixture explainer only; no live agent |
| Accessibility | Pass, tested scope | Keyboard prepare and focus, disabled-reason associations, 430px reflow. No screen reader, contrast or WCAG claim. |

## Gates

M3 passes; M4 may start. Still open and unchanged: M0, M2b F04/F5, F4 and F6 to F9, and M6. The eight
low findings above remain tracked. No human comprehension evidence exists for M3.

My services on ports 8109, 8112, 8114 and 8116 are still running and can be stopped.
