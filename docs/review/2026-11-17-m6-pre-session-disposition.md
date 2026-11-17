# M6 pre-session disposition

Fable's independent report accepts bounded M6 technical scope and closes M5-1/2. Human sessions have not started. Original review and historical evidence are unchanged.

## M6-1 — Explicit review-reset recovery

Implemented in `Workbench.tsx` and `OperatorFlow.tsx` without changing server validation or saved expectations:
- When a submitted graph confirmation comes back cleared, the save notice explicitly says selections were saved but confirmation was cleared because the selections changed.
- The next-action banner says **Confirm your saved graph selections** and links to Questions to answer.
- The disabled Run button has a persistent adjacent explanation and the exact confirmation to tick. This survives reload; it is not only a transient toast or hidden checklist.
- Explicitly confirming the saved selection enables Run; the warning disappears.

Implementer Chrome check: fresh isolated copy on port 8141, operator `m6-clarity`, no provider or sandbox calls. Selecting Acme and ticking review in one save retained Acme and cleared confirmation as before. Notice, banner and inline remedy were visible. Reload and 430px layout passed; explicit re-confirmation enabled Run. No page errors. Frontend build and all 19 existing frontend tests passed. Evidence and hashes: `output/playwright/ai-native-onboarding/M6/clarity-20261117/`.

Status: independently closed by the subsequent Fable focused recheck (linked below). No human-comprehension claim.

## M6-2 — Correct the claim, preserve the oracle

Current handoff now states: **F1 1.0 demonstrates no regression on two existing CRM questions. One contact for Ann is observed in the recorded graph.** Neither question directly tests Ann's email change. The chain demonstrates a guided revision, not unprompted diagnosis. No question, expected answer, saved result or pack was changed to strengthen the claim retroactively.

A future direct email-change test must specify and review its expected identity/history outcome before execution. That additional test is not claimed here or required to reinterpret the existing score honestly.

## Focused Fable recheck

Use a fresh copy seeded from `clarity-20261117/start.json`, your own service/store/token, and the current bundle identified in `manifest.json`. Select Acme, tick graph review and Continue in one save. Confirm the selection stays, the tick clears, and all three messages explain the actual state. Reload at 430px; the banner and inline remedy must remain visible. Return, confirm the saved selection and Continue; Run must enable without changing the server gate or expectations. Read the corrected CRM wording above and in the M6 handoff. No live-agent or Spanner run is needed. Record acceptance separately from this implementer check.

M6-3 through M6-10, earlier lows, the imported-document compatibility observation and partial source-race evidence remain open with their original severity. This focused correction does not silently close them. Real-operator sessions remain the outstanding overall acceptance gate.

## Independent closure

`docs/review/2026-11-17-m6-1-fable-recheck.md` independently closes M6-1 and confirms M6-2 wording. The interaction may be recorded and used in operator sessions. The new low about saying selections are saved before an unsaved edit is persisted remains open. Earlier lows and real-operator sessions remain outstanding.
