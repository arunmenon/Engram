# M2b blockers: remediation and Fable re-review

M2a is independently accepted. M2b F1–F3 are implemented and pass the implementer checks below; M3 remains gated on independent re-review.

- **F1:** keep prepared request and answer while an author job runs or fails. Clear the submitted request only on successful completion, guarded by draft ID and a post-submission revision. A failure banner names the error and retry/clear remedy. Retrying requires explicit review against the current revision.
- **F2:** Keep this data creates a shared request naming the actual removed items. Focus moves to that editor; Clear is available. If another request exists, it is preserved and brought into the same visible review surface rather than overwritten.
- **F3:** review selections live with the draft's session recovery, outside the screen component. Navigation/reload retains them. A basis containing tenant, proposal, changes, stale status and server review prevents reusing them for a different review. Server approval checks are unchanged.
- **F10:** no validation result is labelled as missing and requiring recheck, rather than suggesting a failed pack check.

Evidence: `output/playwright/ai-native-onboarding/M2b/remediation-20261107/README.md`.
15 frontend tests, build and 13 targeted backend guard tests pass. Chrome fixture runs cover failed send and explicit retry, reload/sign-in/restore, removal request naming/focus/clear, acknowledgement navigation/reload and successful author completion. No originals, packs, expected answers or production stores changed. No live provider, Spanner or activation run.

## Copy to Fable

Independently re-review M2b F1–F3 in /Users/arunmenon/projects/Engram, using the ai-native-ui-review skill. Read your original report at docs/review/2026-11-06-m2a-m2b-fable-independent-review.md, this disposition and the evidence README above. Check the actual current bundle and backend; the README discloses the status-copy-only change between two test builds.

Use fresh reviewer-owned copies of the same identified snapshots. Do not mutate implementation drafts. Keep tokens inside automation. Reuse your isolated failure-author approach; no live/cloud run is required. No product or expectation edits during review.

1. Prepare a request and fail the author job. Verify exactly one inline request and the typed answer remain. Verify failure banner/reference, needs-review state, explicit retry and reload recovery. Also check successful completion clears only the submitted request and never newer input.
2. Keep a removed item. Verify the exact item is named, the shared editor is focused, no duplicate send editor exists, Clear works, and an existing request is not overwritten.
3. Tick policies, groups and removals. Continue/Back, sidebar round trip and reload/sign-in must retain them. Change the reviewed proposal or tenant: prior ticks must not transfer. Server acknowledgement/removal gates must still reject incomplete reviews.
4. Check the small F10 distinction between absent validation and actual failed checks.

Report functionality, clarity, AI helpfulness and tested accessibility separately. F4–F9/F04 remain open unless separately demonstrated; fixture authors do not prove reasoning. Save to docs/review/2026-11-07-m2b-blocker-fable-re-review.md with build/copy identities and evidence. State whether F1–F3 now permit M3 to start, and list remaining gates without broadening the scope.
