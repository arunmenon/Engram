# M5 thin intake assistance — implementation and open live gate

M4 is independently accepted in `2026-11-13-m4-poll-fable-recheck.md`.
M5's deterministic intake changes are implemented and verified. **M5 is not complete:**
the bounded live incomplete-input case exposed invalid generated pack syntax and
engine-vocabulary leakage. M6 has not started.

## Reproducibility

Codex implementer-directed verification, 2026-11-13 Asia/Kolkata; not independent,
uncoached or a human study. Branch feature/engram-walkthrough, HEAD 27b4ba8; large
pre-existing dirty/untracked tree, no commit or deployment.

Fresh service `http://127.0.0.1:8125/workbench.html`, operator m5-implementer, separate
SQLite store at /tmp/engram-m5-intake/drafts.sqlite3. Final bundle
`workbench-DP1IaDfs.js`; exact source/build/engine hashes and copy identities in
`output/playwright/ai-native-onboarding/M5/intake-20261113/manifest.json`.
Headed Chrome through Python Playwright, 1440×1000 and 430×932, default zoom.
Tokens read within automation, never printed. No reviewer process/store was changed.

Intake checks make no provider calls. The separate, explicitly consented procurement
author job used the previously documented provider model gpt-5.2-2025-12-11, with
synthetic material only. No Spanner, sandbox execution, activation or approved pack.

## Delivered

- Format-based category suggestions for pasted text and files. Clear event envelopes
  suggest samples; recognized JSON/OpenAPI declarations suggest schemas; prose suggests
  process material. Ambiguous JSON remains undecided. The operator can override every
  suggestion. Pasting does not silently override a selected category.
- Existing source correction/save/reload retained. Original source text is unchanged.
- Saved sample inventory reuses the existing authenticated evidence endpoint and
  parser. Added event counts, missing fields and empty values to its existing present,
  distinct and repeated counts. No separate parser or agent pipeline.
- Existing intake screen shows event groups with searchable, disclosed top-level payload
  fields. It explains that repeated IDs may be updates or collisions and sample uniqueness
  does not guarantee a global key. This does not infer a business identity or composite key.
- Inventory is bound to saved revision and tenant. Unsaved changes are labelled; obsolete
  responses cannot replace the current inventory. No provider is involved in categorization
  or inventory. Existing consent, owner isolation, validation, clarification and explanation
  machinery is reused.

Product files: authoring.py (existing evidence statistics), Workbench.tsx (wiring),
intake.ts and IntakeEvidence.tsx. The existing six-step flow is preserved.

## Checks actually performed

- 193 workbench backend tests pass, including three new inventory cases covering
  missing/null/empty values, zero/false preservation, repeated identifiers and no source
  mutation. Ruff and targeted mypy pass.
- 19 frontend helper tests pass; TypeScript and production build pass. New helper test
  covers category suggestions and ambiguous/invalid event shapes.
- Chrome: three mixed inputs, category correction, reload/sign-in, original text equality,
  event/field counts, search and 430px overflow. Initial mixed-input smoke used matching
  structures; a subsequent final-bundle sales case used contact continuity across changed
  email and company fields, unlike procurement's unit-scoped requests/value omissions.
  These are synthetic domain input cases, not evidence of two production-ready packs.
- Conflicting documents both remain in the evidence list. No POST author/explain request
  occurs during intake. An author POST before consent is refused with 409.
- Final-bundle procurement inventory and completed live-result screens captured without
  another provider call. Desktop/narrow screenshots inspected.
- One initial browser locator required correction (select label exact matching); retained
  in browser-attempt1.txt. No product behavior was bypassed.

## Live incomplete-input result — not an acceptance pass

The operator supplied purchase-request examples with repeated IDs across units, conflicting
reopening policies, and a question about suppliers without any supplier-link source.
One author job was launched through the UI after policy permission and redaction confirmation.
It completed in 96.5 seconds, with attempt 3 observed. No second author job was submitted.

What worked: sources and the saved canonical questions/expected answers stayed unchanged.
The proposal explicitly retained the unresolved supplier relationship and the contradictory
reopening policies as decisions/limitations. It did not invent a supplier edge. The existing
validation gate refused the generated pack.

What failed: the PurchaseRequest key pattern failed validation (`expected } at position 17`).
One decision effect asks for an "edge name"; another mentions Lifecycled and projections.
These are exactly the engine-language burden M5 must avoid. A successful author job is
not a valid or accepted pack. This is not evidence of self-service issue resolution.

The first live-summary comparison used abbreviated pre-save question input; it was corrected
against the canonical saved input (server defaults included). The saved questions are equal.
The first screenshot preceded the last UI poll; live-incomplete-result-final.png captures
the completed result. No second provider call was used to obtain it.

## Remaining work and verification boundary

1. Resolve the live key-pattern authoring failure through the existing repair/explanation
   flow; avoid asking an operator to edit engine syntax. Preserve the question and evidence.
2. Remove engine vocabulary from business clarification effects while keeping technical
   detail available separately. Do not paper over a rejected pack with an apparent success.
3. Recheck one bounded incomplete-input recovery and submit M5 for independent review.

Functionality: deterministic intake verified; live completion gate pending.
Visual clarity: intake fields/results inspected; live decision wording needs improvement.
AI helpfulness: one real invocation, unresolved; no general readiness claim.
Accessibility: native controls and 430px no-overflow checked; no screen reader/WCAG claim.
Recovery coverage: reload/sign-in and tenant navigation exercised; save-during-edit,
failed-send restoration, legacy recovery, sign-out clearing, cancellation and late provider
responses were not re-exercised. Earlier results remain scoped to their original runs.

M4 RR-2–4/M4-4–12 and M0/M2b/M3/M6 gates remain open. No approved artifacts or live data changed.
