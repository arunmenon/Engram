# M1a: Fable UI findings — remediation and re-review

Date: 2026-11-06. Status: implemented and locally verified; independent re-review pending.
Source review: `2026-11-06-m0-m1a-fable-ui-verification-result.md` (unchanged).
This disposition does not accept full self-serve issue resolution or mark M0 complete.

## What changed

| Finding | Implemented behavior | Evidence / limit |
| --- | --- | --- |
| 1. Save loses human answer; old request remains sendable | Human answers use draft/issue identity, separate from revision-bound explanations. Requests retain origin, answer snapshot, revision and proposal. Changed revision, proposal or answer blocks Send until explicit current-draft review. | Source-save and failed-send Chrome paths; helper tests. |
| 2. Restore creates an invisible request | Recovery restores human answers and request into the inline review panel; recovered requests always need review. Older recovery records get a visible fallback panel with Clear. | Normal, answer-only and legacy recovery Chrome paths. |
| 3. Banner sends operator to wrong work | Current unresolved proposal items take priority over missing evidence after setup prerequisites. A prepared request links to its review. | Delivery banner names the actual TestRun policy issue. |
| 4. No consequence preview | Request review shows the operator's desired outcome and candidate current records, keys, states and event writers from the actual pack. It explicitly labels the exact change as unverified. | Delivery and CRM UI; derivation helper test. This is a grounded scope preview, not a semantic prediction or a proposed diff. |
| 5. Duplicate send paths | An attached request owns one inline editor and Send control. The general author editor links to that panel instead. Preparing another request cannot silently overwrite the first. | Chrome verifies absent duplicate send, visible existing-request link and Clear. |
| 6. Raw failure language | Plain recovery message keeps the answer/request. Raw details are collapsed for support. | Controlled HTTP 503 in Chrome; raw detail not visible by default. |
| 7. Fresh explain after failed instruction-only save | A fresh explanation may read a retained proposal when only the instruction changed. UI/context say that the instruction has not been applied. Source changes close that exception; later instruction-only saves cannot reopen it. | Backend fresh/stale/source-change test; Chrome failed-send path. Revision, consent and owner checks remain. |

The preview and request are generic across declared pack types. No delivery or CRM
business rule was added to product code. Fixture explanations remain canned and are
not evidence of live reasoning. The preview still uses declared type/event names; this
is a usability limit to assess during re-review, not a claim of completed simplification.

## Verification performed

- Headed Google Chrome, isolated port 8105: four grouped scenarios passed, zero page
  errors. Delivery and CRM; desktop 1440px and a 430px keyboard/overflow check.
- Reviewed desktop and narrow screenshots. Request focus, send controls and wrapping
  are visible; the narrow screen remains long. No screen-reader or human study claim.
- 98 backend tests passed in `test_workbench.py`, `test_workbench_explain.py` and
  `test_workbench_draft_stories.py`.
- 11 frontend helper tests passed. Workbench TypeScript + production build passed.
- Ruff passed on changed backend files/test; mypy passed on the two changed backend
  modules. These are targeted checks, not a full repository suite.
- No live provider, Spanner, activation, approval or expected-answer modification.

Evidence: `output/playwright/ai-native-onboarding/fable-remediation-20261106/`.
Includes browser script, four-case result JSON, backend test log and five screenshots.
The controlled author failure does not test successful authoring or issue resolution.

## Re-review script

Use isolated copies; preserve original 8102/8103 findings and 8101/8104 services.
The local review service is `http://127.0.0.1:8105/workbench.html`, when running.
Authentication file: `/tmp/engram-fable-remediation-token`; never include it in evidence.

1. Open **Remediation delivery**, step **How Engram understands them**. Confirm the
   next action names the release-test issue. Enter a domain answer under the issue,
   then **Review my request**. Inspect outcome/current rules/uncertainty. There should
   be one editable request and one send path, with focus in the request.
2. Reload and authenticate again. Reopen the same draft and restore. The answer and
   request must both be visible; Send must require explicit current-draft review.
   Clear must retain the domain answer and return focus there.
3. On a fresh CRM fixture copy, prepare an answer, add supporting material, and return.
   The answer/request must survive; the earlier explanation must disappear and the
   request must be labelled as needing review. Changed evidence must not be explained
   using an obsolete proposal.
4. With a controlled failed author start, verify the instruction save cannot leave the
   old request sendable. Read the plain error, inspect support details if desired,
   and confirm a new explanation identifies the retained proposal honestly.
5. Restore a legacy browser recovery record without request metadata. Confirm its
   inline fallback panel is visible and clearable; another preparation must lead to
   that panel, not an invisible-text dead end.
6. At 430px, tab through review/send/clear. Confirm visible focus and no horizontal
   overflow. Assess the density of current-rule detail separately from functionality.

Ask Fable to judge whether an operator can identify the issue, understand what remains
unknown, recover their words, and deliberately submit one request. Do not ask this
fixture run to prove agent reasoning, successful authoring, or independent expected
answers. Those remain separate acceptance evidence.

## Files changed for this remediation

Frontend: `Workbench.tsx`, `ExplainProblem.tsx`, `OperatorFlow.tsx`, `editing.ts`,
`types.ts`, new `RequestReview.tsx`, new `requestDraft.ts`, and request-draft helper tests.
Backend: `workbench/api.py`, `workbench/explain.py`, and `test_workbench_explain.py`.
The milestone plan's current status is corrected. No independent review was overwritten.
