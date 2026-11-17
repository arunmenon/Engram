# Fable review fixes and plain-language explanation

Review addressed: `2026-11-05-agentic-onboarding-remediation-independent-review.md`.
The independent review remains unchanged. Changes are local and uncommitted.

## What the findings mean

| Finding | Plain-language problem | Correction |
|---|---|---|
| R1 | The comparison could forget your last accepted pack. A model could undo an accepted change without asking you to review it. | Persist the accepted pack independently of temporary review flags. New comparisons use it until another pack is accepted. API regression covers accept → edit → regenerate → revert. |
| R2, R9 | A statement could display old trust settings or quote an old request as if they were current. | Revalidate provenance when saving; mismatches mark the proposal stale and clear review/validation. Older request quotes are labelled. Errors identify stale instruction/trust evidence. |
| R3, B7 | A citation consisting of “{” or “the” could pass, and an identity answer could be used to justify an unrelated relationship. | Require meaningful-length exact excerpts (20 characters), exclude identity/lifecycle-only edge support, and expose the supporting excerpts beside each relationship. This is stronger traceability, not proof that the statement means what the model claims. Human review remains essential. |
| R4 | “The wrong thing is absent” could pass because the model misspelled its ID or named a nonexistent relationship type. | Validate positive and negative assertion IDs, key arity, and declared node/edge types, including retrieval exclusions. Preserve raw core Event IDs only when backed by a declared Event type and an event in the story. |
| R5 | One checkbox could approve all answers written by the model itself. | Require acknowledgement of every generated check; enforce it server-side with revision fencing. UI shows a checkbox alongside each expectation. This requires review but does not prove the reviewer read it. |
| R6 | A clarification could hide other validation failures or ask the same relationship question twice. | Only use the conceptual fallback when missing intents are the sole engine failure. Replace overlapping relationship questions with the explicit question for the blocked intent. Other errors remain in the repair/validation path. |
| R7 | Starting-node IDs and answer types could reveal part of the answer to the authoring model. | Remove them from structured author inputs as well as expected answers. Free-text specifications can still reveal answers; this is not a universal redactor. |
| R8 | A tiny mapping edit appeared as a large before/after dump; removal of the pack had a blank label. | Diff projection rules by event when unique, otherwise by index; preserve a separate indication of reordering. Label whole-pack changes explicitly. Identity lists remain together so key order is visible. |
| R10 | Changing an answer or trusted-producer list could carry its old “reviewed” tick forward. | Reset the affected trust, graph or question confirmation on a saved value change. A subsequent explicit confirmation is required. |
| R11 | Workbench code imported database SDK classes where repository architecture rules prohibit them. | Move SDK construction/key-selection behind Spanner adapter functions. The hex-purity suite now passes. No database data was changed. |
| R14 | Repair instructions made the assistant think it could not quote JSON schemas. | Explain that literal JSON source substrings are allowed; response JSON escaping must preserve the original excerpt. |
| R16 | Two accept controls sent different information; one silently dropped earlier confirmations. | Remove the duplicate engineer-panel accept checkbox and direct acceptance through the guided review. |
| Additional UI notes | Cancellation had no message; failure guidance could imply changing expected answers just to pass. | Show cancellation status and clarify that only an operator may correct an expectation with a source-backed reason. |

## Verification so far

- All workbench unit suites plus the architecture-purity suite: **547 passed**.
- Seven frontend helper tests passed; workbench production build passed.
- Ruff passed; mypy passed on nine changed runtime modules.
- Actual Chrome check on an existing 16-check story: a blanket confirmation alone
  did not enable acceptance; acknowledging all checks did; unticking one blocked
  acceptance again. No story was saved or executed by this UI check.
- Fresh live-provider Chrome runs and their exact outcomes are recorded below when
  complete. Evidence lives in `output/playwright/onboarding-fable-remediation-20261105/`.

## Boundaries and remaining scope

These corrections do not turn citations into semantic proof, guarantee independent
human review, or establish unattended generation reliability. Context budgeting and
broader selectable-domain composition (B9/B10), scope-edit invalidation (B11), draft
export availability (R12), and snapshot-parent drift notices (R13) remain separate
product/design work. Saved story snapshots intentionally remain pinned. Existing
packs, expected answers, runtime data and independent review documents were not
rewritten to make tests pass. Test request payloads were updated for the new per-check
approval contract, and tests now expect changed oracle values to require review.
No fresh real-Spanner execution or production activation is claimed here.


## Live verification follow-up

The first fresh browser pair failed closed on invalid instruction quotations. Those
runs are retained under `complete/` and `incomplete/`; they are not counted as passing.
The agent's generation schema now explicitly requests `null` when no instruction
exists and a minimum-length exact excerpt otherwise, without making legacy records
unreadable. Separate diagnostics distinguish a short excerpt from an outdated one.

The second incomplete-input browser run (`incomplete-v2/`) completed after two
attempts with a conceptual draft and exactly one question asking for missing
relationship evidence or deferral. No invented executable pack, extra trust
confirmation, or browser error was reported. Its wording still includes engine
terminology; this is evidence of correct blocking behavior, not perfect conversational
copy. The prior JSON quotation blocker did not recur in this run.

User-facing terminology: the authoring service is called the **agent**, and the
artifact is the **pack**. Underlying model identity is relegated to technical details;
permission text continues to disclose that inputs go to an external service.


The complete `complete-v2/` case rendered trust and instruction evidence but failed
engine validation on an invented admission rule (`Sourced.trusted_producers`). The
agent now receives the actual `ADMISSION_RULES` vocabulary and supported setting
names from the engine, with a source-trust example. Review metadata is explicitly
separated from runtime rule names. No validator was loosened.

The operator then requested the supported admission rule through the UI. The revised
`complete-v3/` proposal passed engine validation with no blocking questions. Actual
Chrome evidence shows one reviewed-trust statement and two instruction-quote displays,
with no browser errors. The screenshot was visually inspected. This is a successful
operator-assisted revision, not evidence of unattended first-attempt success. Browser
locator retries did not count as agent successes; the successful browser transcript is
`/tmp/engram-remediation-complete-ui3b.log`, and durable results/screenshots are in
`complete-v3/`. Failed and intermediate provider responses remain in the evidence folder.

The quotation-schema and engine-vocabulary follow-up passed all 61 authoring/API tests;
the earlier all-workbench + hex-purity run passed 547. Remaining tests and final build
are recorded at handoff. No new Spanner scenario was run for these authoring corrections.


Final verification after the quotation/admission guidance and terminology changes:
**547 backend/architecture checks passed**, **7 frontend checks passed**, production
build and Ruff passed, and mypy passed for nine runtime modules. Logs are saved in
`output/playwright/onboarding-fable-remediation-20261105/checks/`. A post-fix file
manifest is `2026-11-05-onboarding-remediation-fixed-manifest.json`; the original
review manifest and independent review are unchanged. Temporary diagnostic capture
was removed from the running local backend after all authoring jobs finished.

This is an implementation disposition and verification record, not an independent
re-review. Broader composition and context-budget work remains as stated above.
