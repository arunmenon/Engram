# M4 RR-1 recheck (review ticks and polling)

## Verdict

**RR-1 is closed. M4 passes its bounded fixture scope and M5 may start.**

The M4-1, M4-2 and M4-3 verdicts stand. Still open: RR-2 to RR-4, M4-4 to M4-12, live-agent
verification, and the M0, M2b, M3 and M6 gates. Fixture story author only; this says nothing about live
reasoning, Spanner or human comprehension.

## Reproducibility

| Item | Value |
|---|---|
| Reviewer | Fable (Claude), independent recheck. Not the implementer. No fixes made. |
| Date | 2026-11-13, Asia/Kolkata |
| Branch, commit | feature/engram-walkthrough, HEAD 27b4ba8, large dirty and untracked tree |
| Bundle | `workbench-CjndwSEA.js`, sha256 1183bca7…74196, confirmed as the bundle the page served |
| Changed source | `JourneyAuthor.tsx` sha256 7e798c75…3b9b7. `Workbench.tsx` and `story_inspection.py` unchanged. |
| Service | http://127.0.0.1:8124, operator `fable-m4poll-review`, own SQLite store |
| Browser | Headed Chrome through Python Playwright, 1440x1000, polling active, one real click per box about 0.4 s apart |
| Copy | "Support review ticks", ID 74706ccc, revision 2 to 10; events, expectations, recorded result and pack snapshot equal to start |
| Evidence | `output/playwright/ai-native-onboarding/fable-m4poll-20261113/` |

## What I ran

| Step | Per-check ticks | Overall tick | Save button | Polls |
|---|---|---|---|---|
| Proposal generated (15 checks) | 0 of 15 | off | disabled | |
| Ticked every box | 15 of 15 | on | enabled | |
| Waited 12 seconds | 15 of 15 | on | enabled | 8 during the wait |
| Generated a new proposal (16 checks) | 0 of 16 | off | disabled | |
| Ticked every box again | 16 of 16 | on | enabled | |
| Waited 12 seconds | 16 of 16 | on | enabled | 8 during the wait |
| Saved | | | | `journey-accept` returned 201 |

- The save created one new workspace, "Fable poll recheck variant", with 16 checks marked reviewed.
- Polling ran throughout at a median gap of 1.55 seconds, 35 polls in total. Nothing was suppressed and
  the save was not raced.
- The fix resets on serialized proposal content, draft ID and revision, as described.
- 18 frontend tests pass. No page errors.
