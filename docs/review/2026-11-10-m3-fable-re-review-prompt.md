Please independently re-review M3 clarity fixes before accepting M3. Do not implement fixes.

Prior review: docs/review/2026-11-07-m3-fable-independent-review.md
Remediation: docs/review/2026-11-10-m3-clarity-remediation.md
Evidence/scripts: output/playwright/ai-native-onboarding/M3/remediation-20261110/final/

Use the ai-native-ui-review skill. Start a reviewer-owned service and fresh copies from
identified snapshots; leave implementer and earlier reviewer copies untouched. Record
bundle/source hashes, copy IDs/revisions, operator and port; read tokens only inside automation.

Acceptance blockers:
1. CRM shows business works-at links 2→3, separate from three provenance links. Because
   contact keys change, endpoint diff correctly shows three added/two removed. Support
   identity merge has no business relationship change. Counts must come from planner output.
2. Resolution shows current open versus proposed open/resolved and identifies the missing
   resolved starting-state example. It never implies guard acceptance or executed outcomes.
3. Source change withdraws old options with a visible reason linked to disabled Explain;
   asking again after a fresh proposal must not retain an obsolete withdrawal notice.

Also verify included M3-2/4: record identities are understandable without JSON, decision
references show question/effect, and conflicting supplied excerpts are accessible even if
not cited by the agent. Check keyboard, 430px, one request editor, Clear and existing text.
Spot-check M2b recovery invariants; no pack, decision or expected-answer mutation from preview.

M3-6/7/8 are documented open lows, not claimed fixed. Distinguish fixture behavior from live
reasoning; no Spanner or human claim. Save independent findings and a specific M3 acceptance
verdict to docs/review/2026-11-10-m3-clarity-fable-re-review.md. Keep other milestone gates open.
