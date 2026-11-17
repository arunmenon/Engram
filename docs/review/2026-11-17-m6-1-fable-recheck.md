# M6-1 focused recheck (graph review reset)

## Verdict

**M6-1 is closed.** The M6-2 wording is corrected. The interaction can be recorded and shown in
operator sessions.

One low wording point is added (R-1). M6-3 to M6-10, earlier lows and the real-operator sessions stay
open. No agent, sandbox or Spanner call was made.

## Reproducibility

| Item | Value |
|---|---|
| Reviewer | Fable (Claude), independent recheck. Not the implementer. No fixes made. |
| Date | 2026-11-17, Asia/Kolkata |
| Branch, commit | feature/engram-walkthrough, HEAD 27b4ba8, large dirty and untracked tree |
| Bundle | `workbench-B1KO3MGA.js`, sha256 3da31aa9…a7528d, the bundle my page served |
| Changed source | `Workbench.tsx` 4186091e… and `OperatorFlow.tsx` 1ac08346…, matching the clarity manifest. `api.py` is unchanged from the M6 manifest, so the server rule is the same. |
| Engine | sha256:7ad0d16f…2c4e, from my own freshly started process |
| Service | http://127.0.0.1:8143, operator `fable-m6-1-review`, own SQLite store |
| Browser | Headed Chrome through Python Playwright, 1440x1000 and 430x900, zoom 100% |
| Copy | "Fable M6-1 graph confirmation", ID f6c71486, seeded from `M6/clarity-20261117/start.json` (sha256 ea99724c…), revision 2 to 8 |
| Evidence | `output/playwright/ai-native-onboarding/fable-m6-1-20261117/` |

## What I did and saw

| Step | Result |
|---|---|
| Ticked Acme and the review box, pressed Continue once | Acme saved; review flag cleared by the server, as before |
| Save notice | "Your graph selections were saved, but their review confirmation was cleared because the selections changed. Return to Questions to answer, review the saved selections and confirm them again." |
| Next-action banner | "Confirm your saved graph selections", with a "Go to questions to answer" button |
| Beside the disabled "Run the examples" | "Your graph selections are saved, but their review is not confirmed. Go to Questions to answer… tick 'I reviewed these graph expectations before execution.' Then continue here to run them." |
| Six seconds later | Notice, banner and inline text all still present |
| Reload at 430px | Banner and inline text still present; no horizontal overflow |
| Banner button by keyboard | Opens Questions to answer; Acme ticked, review box unticked |
| Ticked the review box, Continue | Review saved; banner "Run the example events"; Run enabled; warning gone |
| Added another entity after confirming | Review box unticks at once on screen; after saving, the flag is cleared and the banner asks for confirmation again |

Questions, sources and the proposal are unchanged. Only draft saves were sent. No sandbox run, no
approval. 19 frontend tests pass; no page errors.

## M6-2

The handoff now reads: "F1 1.0 shows no regression on two existing questions; neither tests Ann's
email change", and describes the chain as a guided revision. No question, expected answer or saved
result was changed. That resolves the claim.

## New low

| ID | Finding | Correction |
|---|---|---|
| R-1 | When a confirmed selection is changed and not yet saved, the banner already says "Your selections are saved, but their review is not confirmed." The same path with the Save button shows only "Saved." after saving; the banner and unticked box carry the message. | Banner for the unsaved state: "You changed your graph selections. Save and confirm them." |

## Verdicts

| Area | Verdict |
|---|---|
| Functionality | Pass: server gate unchanged, selection kept, confirmation required |
| Visual clarity | Pass: three consistent messages naming the same remedy, persistent across reload |
| AI helpfulness | Not applicable |
| Tested accessibility | Pass, narrow: 430px reflow and keyboard use of the banner button. Focus lands on the page body after that navigation, as elsewhere. |

My services on ports 8109, 8112, 8114, 8116, 8118, 8120, 8124, 8131, 8140 and 8143 are still running
and can be stopped.
