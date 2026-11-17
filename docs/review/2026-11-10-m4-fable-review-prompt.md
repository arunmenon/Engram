Independently review M4 before acceptance. Do not implement fixes or modify original
packs, fixtures, expected answers or implementer/reviewer drafts.

Read project/frontend instructions and apply ai-native-ui-review. Sources:
- docs/ai-native-onboarding-milestone-plan.md (M4 acceptance)
- docs/review/2026-11-10-m4-story-guidance-implementation.md
- output/playwright/ai-native-onboarding/M4/review-20261110/final/ (manifest, snapshots,
  runnable fixture service/browser scripts, real memory results and screenshots)

Use a new port/store and fresh reviewer-owned copies. Capture source/bundle/snapshot
hashes and draft IDs/start/end revisions. Read credentials inside automation only.
Do the domain operator tasks before reading implementation details; disclose prior
familiarity and that simulated personas are not human comprehension.

Tasks:
1. Support operator: compare a passing story with the investigation story. Explain what
   failed, what remains unknown and which evidence to inspect next. Try the wrong-account
   answer, title mismatch, unsupported scalar and missing-endpoint negative assertion.
2. Ask about one failure. Before consent the call must be blocked; after explicit permission
   it must use the selected check's pinned evidence and remain read-only. Try malicious
   repair instructions, bad indexes, stale results, cross-owner access and result replacement
   during a call. Explain cannot rewrite an oracle or infer a cause without evidence.
3. Inspect the checkpoint graph. Plan a follow-up using the existing authoring form; typed
   material must survive and assertions still need review. Rerun without changing expectations:
   deliberate failures must stay failures. Also inspect a real passing CRM story.
4. Read coverage: an event delivered is not behavior proven. Distinguish defined, executed,
   passing, unsupported, no-check, stale and weak-proof cases. State assertions are not
   causal/guard completeness. Check search, expansion, root exclusion and complete check list.
5. Change the pinned story/pack identity on an isolated copy: stale results cannot support
   a fresh explanation or passing coverage. Never silently load a newer parent pack.
6. Test new empty property assertions and impossible relationship endpoint assertions.
   Preserve historical expectations; their limited proof strength must be flagged rather
   than rewritten. Look for remaining concrete vacuity bypasses and report exact scope.

Check keyboard, 430px, focus, density, terminology, actionable uncertainty and single
submission. Inspect the new tenant-card busy-state fix for navigation regressions.
Separate functionality, visual clarity, AI helpfulness and accessibility. Do not infer
live reasoning/Spanner/human readiness from fixture checks. Keep M0/M2b/M3/M6 gates open.

Save report: docs/review/2026-11-10-m4-fable-independent-review.md, with evidence directory.
State whether M4 passes its bounded scope and what must change before M5.
