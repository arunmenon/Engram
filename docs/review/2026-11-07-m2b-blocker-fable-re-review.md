# M2b blockers F1–F3 — Fable independent re-review

## Reproducibility header

- **Reviewer:** Claude Fable 5.1, independent re-review of the three blockers from `docs/review/2026-11-06-m2a-m2b-fable-independent-review.md`, following `docs/review/2026-11-07-m2b-blocker-remediation.md`. 2026-11-07, Asia/Kolkata. I read the disposition and the implementer README before testing; this is a directed recheck, not an uncoached first use.
- **Code:** HEAD `27b4ba8`, dirty tree. Changed frontend files match the remediation hashes (`Workbench.tsx` 9672e410…, `OperatorFlow.tsx` cb51f81f…, `RequestReview.tsx` 7427b758…, `editing.ts`, new `reviewTicks.ts`). Backend unchanged since my first review (`api.py` 91fa5e8d…, `explain.py` 20d32416…).
- **Bundle:** `workbench-vyj1HNRJ.js` sha256 `bd9f3076…`, the implementer's final build. Their failure/recovery screenshots used the earlier `BjBL0H8W` build; all my checks ran on `vyj1HNRJ`.
- **Service:** reviewer-owned process on port 8112 started from current source, fresh SQLite store, operator `fable-m2rr-review`, engine `sha256:bede13fb…`, fixture explainer and fixture author (fails by default; completes for the incident success-control copy). No live provider, Spanner, sandbox, approval or activation. Token read only inside automation.
- **Copies:** CRM from `crm-start.json` (97cea632 rev 2) 2→10; Northstar from `northstar-copy.json` (cadf742e rev 2) 2→4; Incident success control from `tests/fixtures/workbench/incident.json` 2→8. Implementer drafts untouched. Evidence: `output/playwright/ai-native-onboarding/fable-m2rr-20261107/`.
- **Coverage:** the four asks below in headed Chrome at 1440 and 430 px, server review-gate probes, 15 frontend helper tests and 24 targeted backend tests (all pass). **Not exercised:** live reasoning, cancellation, save during polling, legacy restore, sign-out clearing, screen reader, F4–F9/F04.

## Results

### 1. F1 — failed request recovery (`t1.json`, `t1-failed-send-full.png`, `t1-after-restore.png`)

- Prepared a request from CRM limitation 2 and sent it; the fixture author failed (rev 2→5). Exactly one "Request to send" editor remained, the typed answer stayed in the limitation box, focus stayed on the request. The banner read "The agent could not finish this request — The task stopped unexpectedly… Error reference 99220aee73fb. Your answer and request are kept. Review the retained request to retry, or clear it." The needs-review alert appeared and Send was disabled until "I reviewed this request against the current draft" was pressed.
- Explicit retry: after the gate, Send enabled; the second failure (rev 7) showed the same retained state with a new reference. `author-calls.jsonl` shows exactly two calls at that point.
- Reload and sign-in: the page offered "Restore what you typed?"; before restoring, the banner was the generic "Update the pack" and the pack-check line read "No current pack check result — check again before accepting". After "Restore my input" the request, answer, failure banner and gate were all back.
- 430 px at the failure state: no horizontal overflow, request editor present (page is 8,102 px tall, see note A).
- Successful completion (`t4.json`, `t5.json`, `t4-after-success.png`): on the incident control copy a prepared request was sent and completed (202, job `completed`, rev 5 then 8). The editor cleared only after completion, not on acceptance; "Cancel task" was offered while running. Unsubmitted newer text typed in the pack-question panel survived completion (the panel collapses on the revision change and shows the text again when reopened). My first success attempt on the CRM copy was rejected by the server with "The proposal quotes an earlier revision request" because my fixture returned the snapshot proposal; the UI treated it as a normal failure with the request retained. That is a fixture artefact, not a product defect.

**F1: fixed.**

### 2. F2 — single "Keep this data" editor (`t2.json`, `t2-keep-fresh-full.png`, `t2-keep-with-existing.png`, `t2-keep-narrow.png`)

- With no request pending, Keep produced exactly one "Request to send" editor whose text begins "Keep these items: nodes.Incident.state." The review region says "About: Keep removed items: nodes.Incident.state" and "Records mentioned: Incident"; the banner names the same subject. Focus moved to the editor. No "What should change?" editor or "Send changes to the agent" button exists on the page. "Clear prepared request" removed it and moved focus to the pack-question selector.
- With a request already prepared from limitation 2, Keep did not overwrite it: the existing request stayed, one editor, focus moved to it. Note B: nothing tells the operator that the removal was not added to that request.
- 430 px: one editor, focused, no overflow.

**F2: fixed.**

### 3. F3 — review ticks survive navigation and do not transfer (`t2.json`, `t3.json`, `t2-ticks-after-reload.png`, `t3-after-proposal-change.png`)

- Ticked both policy boxes, both change groups and the removal on Northstar; accept became enabled. All five ticks survived Continue→Back, a sidebar round trip through step 5, a tenant round trip through CRM (which showed no ticks of its own) and reload with sign-in. Note C: after reload the ticks were already shown before "Restore my input" was chosen.
- Basis change: a content-only save (API PUT, rev 2→3, proposal not stale) kept the ticks, which is correct because the proposal, changes and review were unchanged. A server-side proposal change (limitation appended, rev 3→4) cleared every tick within the polling interval and after reopening.
- Server gates on the new copies: accepting with one group missing → 409 "Acknowledge each pack change before accepting this revision"; removal omitted → 409 "Explicitly review each proposed data removal first"; unknown change → 422; unknown removal → 422 (`api-probes.json`). No review was submitted on any copy. The `reviewTicks.ts` basis includes draft id, proposal, change set, stale flag and server review, matching the disposition.

**F3: fixed.**

### 4. F10 — absent versus failed check

After a failed send and reload the status read "No current pack check result — check again before accepting" (`t1.json after_reload`); the code keeps "Engram's pack checks need attention" with the problem list for a real failure and "passed" otherwise. I did not produce a real failed validation on these copies; the wording distinction is confirmed from the observed absent-state text and the unchanged failure branch.

**F10: fixed as described.**

## Notes (not blockers)

- **A.** At 430 px the CRM review step with a failed request is 8,102 px tall; the retained request and banner are correct but far apart. Density stays with F8.
- **B.** Keep with an existing request preserves that request silently; a one-line status ("Your earlier request is kept; add the removed items to it or clear it first") would remove the guesswork.
- **C.** Restored ticks render before the operator answers the restore prompt; harmless because nothing is submitted, but inconsistent with how the request text waits for "Restore my input".
- **D.** After a successful completion the submitted limitation answer remains in its box. That is retained input, not loss, but the operator may wonder whether it was applied.

## Verdicts

- **Functionality: pass** for F1, F2, F3 and F10 on bundle `vyj1HNRJ` with fresh copies and server gates intact.
- **Visual clarity: pass for the changed states** (failure banner, Keep editor, check-status wording). F4, F8 and F9 remain open as recorded.
- **AI helpfulness: not exercised.** Fixture author and explainer only; F04/F5 remain open.
- **Accessibility (tested scope): pass.** Focus reaches the request editor after send, retry gate, Keep and Clear; 430 px layouts have no overflow; no screen-reader run or WCAG claim.

## Conclusion

F1–F3 no longer block. **M3 may start.** Remaining gates, unchanged in scope: F04/F5 operator-language findings need live evidence and operator-oriented review before any self-service claim; F4 (hidden catalog) before a demo; F6–F9 at their assigned milestones; human comprehension at M6. No product code or expected outcomes were changed by this review. My services on ports 8109 and 8112 are still running and can be stopped.
