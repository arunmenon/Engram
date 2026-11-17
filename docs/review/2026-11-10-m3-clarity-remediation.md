# M3 clarity remediation

Implementer verification, not independent acceptance. 2026-11-10, Asia/Kolkata.
Based on `docs/review/2026-11-07-m3-fable-independent-review.md`; original review untouched.
Branch feature/engram-walkthrough, HEAD 27b4ba8, pre-existing dirty/untracked tree.
Final bundle **workbench-QDNA5dIB.js**. Hashes, snapshots and copy IDs/revisions:
`output/playwright/ai-native-onboarding/M3/remediation-20261110/final/manifest.json`.
Fresh isolated service on **8115**, operator m3-remediation, SQLite draft store,
fixture explainer, genuine engine planner. Headed Chrome/Playwright, 1440×1000 and
430×932, default zoom. Tokens read inside scripts, never printed. Fable's 8109,
8112 and 8114 services were not stopped or edited.

## Disposition

| Finding | Change | Verification |
|---|---|---|
| M3-1, blocker | Business links and engine DERIVED_FROM provenance links are separate. Main view lists named business counts and changed endpoints; provenance stays under technical details. | CRM: works at 2 → 3; 3 new endpoints, 2 removed because both contact keys change. Support: no business relationship change. |
| M3-3, blocker | Current and proposed targets/allowed starting states shown together. A changed starting state absent from the supplied prior requests and declared initial state is flagged. Explicitly says requests are not executed outcomes. | Resolution: allowed from open versus open, resolved; sample 3 does not exercise resolved as a starting state, with remedy to add that sequence. |
| M3-5, blocker | Withdrawn options get a visible explanation. Disabled Explain always shows its reason nearby and associates it via aria-describedby. Disabled Prepare also links to its reason. | Source edit observed by UI polling: options withdrawn, Explain disabled, update-proposal reason visible at 430px. |
| M3-2 | Records display their actual generated key fields and sample event names. No opaque ID parsing or invented label mapping. | Main view: account east / number 42; CRM contact numbers or email addresses. |
| M3-4 | Decision references show question/effect as text and are labelled Recorded decision. Supplied excerpts are available independently of which references the fixture agent cites. | Both conflicting account policies visible in the material disclosure; subject no longer appears as engine-check JSON. |

Lifecycle comparison is deliberately not a state simulator. Earlier requested states
are evidence about the supplied sequence, not proof that the engine accepted them.
A sandbox run is still needed to determine executed outcomes. No validation or
acceptance gate was weakened. Existing request/editor/authoring paths were not changed.

## Evidence and checks

- **178 workbench unit tests passed**, including 12 decision-preview tests.
- **18 frontend helper checks passed**; new cases cover relationship endpoint changes,
  lifecycle comparison/initial-state evidence and plain decision references.
- Workbench TypeScript/Vite build, Ruff and mypy on the changed backend module pass.
- Final-bundle Chrome checks pass on support identity, support resolution, missing
  resolution samples and CRM contact history. Prepare/keyboard focus, existing-request
  preservation, Clear and 430px reflow rechecked. Screenshots inspected for lifecycle
  comparison and stale-state readability.
- All packs, recorded decisions and questions equal their start snapshots. Two isolated
  support copies advance 2→3 solely for deliberate source-change/staleness probes;
  the other copies stay at revision 2. Full records and provenance hashes retained.

The source-edit probe changes the isolated draft store and observes normal UI polling;
it is not a test of the source upload/save form. This is a directed implementer recheck,
not an uncoached persona study or human comprehension evidence.

The first browser run had an incorrect assertion expecting one added endpoint. With
changed record keys, the real output replaces two links with three. The assertion was
corrected to check those endpoints, without altering packs or question expectations.
Final-bundle checks use a fresh support copy; earlier run evidence is retained.

## Remaining scope and verdicts

Functionality: pass for the focused fixture paths. Visual clarity: corrected states
inspected; independent acceptance pending. AI helpfulness with a live agent: not
exercised. Accessibility: keyboard prepare/focus and 430px no-overflow pass; disabled
reason associations checked, no screen-reader/WCAG claim.

M3-6 (stale request status), M3-7 (429 after Stop waiting), and M3-8 (generated choice
label/JSON in editable request) remain open low findings. No self-service, successful
live authoring or Spanner claim. M0, M2b F04/F5 and F4/F6–F9, and M6 gates remain.

Recovery coverage: source-change withdrawal and existing-request/Clear exercised in
browser. Reload/restore, failed send, consent changes, legacy restore, sign-out,
cancel/late response and save-during-edit not re-exercised in this focused pass.
Existing regression suites pass; this does not substitute for fresh browser evidence.

Next: focused independent re-review of M3-1/3/5 and the included M3-2/4 improvements.
M4 has not started.
