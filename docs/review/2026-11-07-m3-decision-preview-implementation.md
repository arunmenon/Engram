# M3 — choices with sample-based consequences

## Status and identity

Implementer verification, not independent acceptance. Date: 2026-11-07, Asia/Kolkata.
Branch: feature/engram-walkthrough; HEAD: 27b4ba8 (large pre-existing dirty/untracked tree).
Final frontend: workbench-BKiZRnVN.js. File SHA-256 values and draft identities are in
`output/playwright/ai-native-onboarding/M3/review-20261107/manifest.json`.
Isolated service: http://127.0.0.1:8113/workbench.html; operator m3-implementer.
Headed Google Chrome driven through Python Playwright; 1440×1000 and 430×932 at default zoom.
Fixture explainer, real pack parser/composition/admission/projector planner, SQLite draft
store. No graph sandbox, provider, Spanner, author submission or deployment run.
Fable services 8109 and 8112 were not changed.

M2b's F1–F3 were independently accepted in
`docs/review/2026-11-07-m2b-blocker-fable-re-review.md`; that opened M3.
This report does not close the remaining operator-language, catalog, density or human-study gates.

## What changed

A recorded decision now has the same Explain interaction as other review items.
The agent may return up to two neutral identity/lifecycle options with references.
Each option carries temporary, narrowly allowed rule edits. Engram validates the current
and candidate packs and plans the supplied events. Unsupported edits and insufficient
samples produce unavailable choices, never invented results.

Identity previews group sample events by generated record identifier. Lifecycle previews
show requested state changes and prior-state guards. These are explicitly **planned,
not executed**: the preview cannot prove that a stored record would pass a guard.
Relationships and exact rules are under technical disclosure. No option is preselected.

Prepare this choice uses the existing single request editor and revision checks. It records
the clicked choice, candidate edits and source-reference identities; source documents remain
in the draft, including disagreements. It does not change the pack, expected answers or
review confirmations. An existing request is preserved with an explicit explanation that
the new choice was not added. An oversized request is refused before preparation.

Scope is deliberately bounded: identity key edits and existing transition guards/targets,
at most two options and twenty representative events. It does not add lifecycle definitions,
store alternate packs, execute comparative sandboxes, or guarantee a successful author revision.
Timeouts stop waiting; a still-running read-only planner retains its capacity slot until it
finishes, so repeated timed-out calls cannot bypass the explanation limit.

## Verification

- Focused backend suite: 38 passed, including option references/scope, invalid candidates,
  no mutation, conflicting-source context, source revision fencing, missing coverage,
  sample bounds and timeout capacity retention.
- Full workbench unit suite: 177 passed; recorded in `backend-tests.txt`.
- Ruff and mypy passed for touched backend modules. Workbench TypeScript/Vite build passed.
- Existing frontend helper suite: 15 passed.
- Chrome fixture runs: support identity (2 records versus 1), support lifecycle guard
  preview, missing transition sample (unavailable), CRM contact history (2 contacts versus
  3 with email identity; WORKS_AT links change from 2 to 3).
- Keyboard activation prepared a request and focused its editor. A second choice preserved
  that request; Clear removed it. Exactly one request editor. No horizontal overflow at
  430px in the four cases. Screenshots inspected, including CRM and support narrow layouts.
- All four isolated draft records remained identical at revision 2 after browser checks,
  including their packs and expected answers. Source snapshots and full end records saved.

One browser assertion initially counted all CRM links as business relationships. The planner
also correctly produces provenance links; the check now explicitly counts WORKS_AT links.
No pack or evaluation expectation was changed to make that test pass.

## UI assessment and limits

Functionality: pass for the bounded fixture paths above; independent review pending.
Clarity: choices show concrete counts and sample membership with no default recommendation.
Missing samples now name the next action in the main view. Technical rule JSON is collapsed.
AI helpfulness: useful decision presentation is demonstrated; live generation/reasoning is
not tested. Human comprehension remains pending. Inherited CRM summary still contains engine
vocabulary and the full review page remains long; neither is claimed fixed by M3.
Accessibility: keyboard preparation/focus and narrow reflow tested; screen reader, contrast
and full keyboard task coverage not exercised.

Recovery matrix: existing-request preservation/clear exercised in browser; source-change
fencing and timeout capacity exercised in backend tests. Save during edit, reload/sign-in
restore, failed author send, legacy restore, consent change in browser, tenant recovery,
sign-out clearing, cancellation and late-response UI recovery not re-exercised for M3.
Existing regression tests pass; that is not a new browser claim.

This was a directed implementer check after implementation, not an uncoached persona study.
Synthetic support scenarios are purpose-built. CRM uses an isolated copy of the identified
M2b CRM snapshot with a new decision question; its existing pack and sample events are retained.
No procurement or live-provider generality claim is made.
