Please confirm only RR-1 from docs/review/2026-11-13-m4-fable-re-review.md.

Change: JourneyAuthor.tsx resets acknowledgements on serialized proposal content,
draft ID and revision, rather than the proposal object's identity. Bundle is
workbench-CjndwSEA.js. Report: docs/review/2026-11-13-m4-poll-review-remediation.md.
Evidence: output/playwright/ai-native-onboarding/M4/poll-remediation-20261113/.

Use a fresh reviewer-owned copy/store and fixture agent. Generate a multi-check story,
tick every per-check review and overall review, wait at least ten seconds with polling
active, and confirm all ticks and Save remain. Generate a new proposal and confirm
both kinds of ticks clear and Save disables. Review again, wait, then save (201).
Do not suppress polling or race Save inside a refresh interval. Record the served
bundle, IDs/revisions, polling count and screenshots. Do not mutate implementer copies.

The prior M4-1–3 verdicts stand. Return whether RR-1 is closed and M5 may start;
keep the low findings and live/provider/Spanner/human limits open. No broad re-review
or new live/cloud run is requested.
