# M4 focused re-review (M4-1, M4-2, M4-3)

## Verdict

**M4-1, M4-2 and M4-3 are fixed.** Existing expectations, recorded outcomes and pinned packs were not
rewritten on any copy.

**One new medium finding should be fixed before M5 (RR-1).** On a generated follow-up story, the review
ticks are cleared about every 1.5 seconds by the page's background refresh. A person cannot tick 15
boxes and save in that time. The code is unchanged since my first M4 review; I missed it then because my
script ticked and saved inside one refresh. The fix is one line and the recheck is one wait.

Three low findings are added to the tracked list. M4-4 to M4-12, the live-agent verification and the
M0, M2b, M3 and M6 gates stay open.

Fixture agent and fixture story author only. Nothing here is evidence of live reasoning, Spanner
execution or human comprehension.

## Reproducibility

| Item | Value |
|---|---|
| Reviewer | Fable (Claude), independent re-review. Not the implementer. No fixes made. |
| Date | 2026-11-13, Asia/Kolkata |
| Prior familiarity | I wrote the first M4 review and know this screen. I read the failed cards in the browser before reading the remediation report or changed code. Simulated persona, not human comprehension. |
| Branch, commit | feature/engram-walkthrough, HEAD 27b4ba8, large dirty and untracked tree |
| Bundle | `workbench-CjVMcSvA.js`, sha256 15ee7021…1aae2, referenced by the served `workbench.html` |
| Source hashes | `story_inspection.py`, its test file, `JourneyWorkspace.tsx` and `types.ts` match the remediation manifest |
| Seed snapshot | `M4/remediation-20261113/copies-start.json`, sha256 fce453ce…0939c, same before and after |
| Engine | sha256:60aa5533…6c04a, read from my own freshly started process; matches the manifest |
| Service | http://127.0.0.1:8120, operator `fable-m4rr-review`, own SQLite store |
| Browser | Headed Chrome through Python Playwright, 1440x1000 and 430x900, zoom 100% |
| Agent, storage | Fixture explainer and fixture story author (real `validate_variant`); real isolated-memory runs |
| Evidence | `output/playwright/ai-native-onboarding/fable-m4rr-20261113/` |
| Not exercised | Live provider, Spanner, the rest of the M4 matrix, screen reader, human participants |

### Copies

| Copy (names prefixed "Fable M4RR") | ID | Start to end revision | Events, expectations, result, pack snapshot |
|---|---|---|---|
| Support failed cards | c4418a8c | 2 to 2 | equal to start |
| Support pending brief | 2aa7bbac | 2 to 7 | equal to start |
| Support passing control | 737a78bc | 2 to 2 | equal to start |
| CRM control | b9abc885 | 2 to 2 | equal to start |
| Fable recheck variant (created in the product) | 5223a8b7 | 2 to 7 | inherited events and expectations equal the parent |

## M4-1: weak assertions, fixed

All six cases went through the real validator and runner, then through coverage inspection
(`vacuity-matrix.json`), and again through the product form into a saved, run story (`r2c.json`).

| Case | Validator | Run | Coverage label |
|---|---|---|---|
| Absence of a record that never appears | accepted | passed | Review assertion strength |
| Question that only forbids such a record | accepted | passed | Review assertion strength |
| Absence of an undeclared field | accepted | passed | Review assertion strength |
| Wrong expected answer, threshold zero | accepted | passed | Review assertion strength |
| Only the record type asserted | accepted | passed | Review assertion strength |
| Only the key field asserted | accepted | passed | Review assertion strength |
| Control: real title asserted | accepted | passed | Passing check |

- **Not rewritten:** every expectation after the run equals what was submitted, and the seven inherited
  outcomes are unchanged (two failed, one unsupported).
- **Wording:** conservative. "This record never appears in the observed story. Its absence alone does
  not show that a creation or removal rule was exercised." It does not claim the record is impossible.
- **Earlier flags still hold:** new empty property checks and impossible endpoint types are refused; the
  inherited empty check and the missing-endpoint check are flagged, not rewritten.
- **In the browser:** the "Every defined check" list shows all six as "Review assertion strength" with
  the reason, the question-intent row shows the same, and the result banner warns that some assertions
  may pass without testing the behaviour.

## M4-2: pending brief, fixed

**Story with no reviewed origin** (`r2.json`). I typed a marked rule into the follow-up brief and
proposed an outline.

- The failed title, failed answer and unsupported cards all keep "No reviewed domain specification is
  attached to this story".
- The explain call for both failed checks sent a null specification. My marked rule appears nowhere in
  the context or the response, before the outline, after it, and after the variant was saved.
- The typed rule stayed in the form.

**Story with an accepted origin** (`r3.json`). The saved variant carries the rule that was accepted
through outline review and per-check review.

- Its failed cards do not show the missing-specification warning, and the explain call sends the
  accepted rule as source.
- I then typed a different marked rule as a pending replacement brief and proposed an outline. The
  explain call still sent the accepted origin rule; the replacement text appears nowhere in the context,
  the response or the failed cards.

## M4-3: expected versus recorded, fixed

Read with "For engineers" closed (`r1.json`, screenshots):

- **Title:** "Expected title: A different reviewed title. Recorded: Payments outage."
- **Wrong account:** "Expected answers: Incident · other-account / INC-1042. Found: Incident · payments
  / INC-1042."

I could name both differences from the card alone. At 430px the line wraps cleanly with no horizontal
overflow. Raw JSON is still there, collapsed under "For engineers · expected and observed evidence".
Reading changed nothing (revision 2 to 2).

## New findings

### RR-1, Medium: review ticks are cleared by the background refresh

- **State:** "Create a new story with the agent", after "Generate events and expected results".
- **Reproduction:** tick the per-check review boxes and wait. `r2d.json`: all 15 ticks set, save button
  enabled; one second later all ticks are cleared and the button is disabled, with no operator action.
- **Cause:** `JourneyAuthor.tsx` line 28 resets ticks whenever the `proposal` object changes. The page
  polls every 1.5 seconds and each poll delivers a new object with the same content.
- **Consequence:** a person cannot complete the review and save a follow-up story with more than a few
  checks. The gate itself is not weakened; it is unreachable at human speed.
- **History:** `JourneyAuthor.tsx` and `Workbench.tsx` have the same hashes as in my first M4 review. Not
  a regression from this remediation. My first review and the implementer walkthrough both ticked and
  saved by script inside one interval.
- **Correction:** reset on a change of proposal content or draft revision, not object identity.
- **Verify:** tick every box, wait ten seconds, confirm ticks and the enabled save button remain; confirm
  ticks still clear after a new generation.

### Lows, tracked

| ID | Finding | Correction |
|---|---|---|
| RR-2 | Neighbouring weak cases still read "Passing check" (`vacuity-adjacent.json`): a threshold of 0.01 with one of four expected answers found; a property check on only `source_trust`; a question that requires its own starting record and forbids a record that never appears. | Flag very low thresholds and system-only fields; treat a required starting record as no assertion. |
| RR-3 | The check card for a weak assertion is still headed "PASSED", and the headline counts it in "11 passed". The warning is inside the card and in the banner. | Head the card "PASSED · review strength" or count flagged passes separately. |
| RR-4 | With no reviewed origin, the agent still receives a `specification` item of kind source whose text is the word "null". | Omit the item or label it as absent. |

## Checks and limits

- **Tests:** 190 workbench unit, 12 story-inspection and 18 frontend helper tests pass.
- **Page errors:** none in any pass.
- **Harness note:** to get past RR-1 my script ticked and saved within one refresh. That is a script
  workaround, not evidence that the path works for a person.
- **Scope:** the rest of the M4 safety matrix was not rerun; those results stand within their earlier
  scope.

## Verdicts

| Area | Verdict | Scope |
|---|---|---|
| Functionality | Revise | M4-1 and M4-2 pass; RR-1 blocks human completion of the follow-up review |
| Visual clarity | Pass | M4-3 on the two failed cards at 1440px and 430px |
| AI helpfulness | Not exercised | Fixture agent only |
| Tested accessibility | Pass | 430px reflow of the changed cards; nothing else retested |

## Before M5

Fix RR-1 and rerun the one wait test. M4 then passes its bounded fixture scope. Still open: RR-2 to
RR-4, M4-4 to M4-12, live-agent verification, and the M0, M2b, M3 and M6 gates.

My services on ports 8109, 8112, 8114, 8116, 8118 and 8120 are still running and can be stopped.
