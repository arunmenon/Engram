# Narration review disposition

Status: text revision prepared for user review. No new video assembled from this
candidate; no runtime, pack or expected-answer changes.

Inputs: the review and proposed narration dated 2026-11-04 are preserved unchanged.
Output: `2026-11-04-walkthrough-narration-revised.md`.

## Accepted changes

| Review finding | Treatment in the revised script and shot list |
|---|---|
| B1–B3: abstractions and early composition | Begin with the general record-identity problem, then illustrate it with Northstar. Composition moves to the actual pack-selection screen. This preserves the user's request for a domain-agnostic premise. |
| B4–B5: evidence/model vocabulary | Use material, citations, source-event links and results for their separate meanings; use assistant and pack explicitly. |
| B6–B7: activation and readiness | Workbench activation is unavailable. Do not imply an activation operation or demonstrated deployment. State the artifact-intent evaluation gate separately. |
| B8–B9: operator actions and isolation | Describe inputs and review actions; explain pack selection versus credential/database controls on the selection screen. |
| B10: starting points | Expand the control and show its selected state; distinguish search scope from a security boundary. |
| B11: assistant form versus history | Saved story is labelled history. The next form is explained as a form; no generation is claimed. |
| B12: change classification | Explicitly say the workbench compares against no previous pack and displays initial. Do not narrate an approved-version comparison. |
| B13–B15: naming | Optional packs, customer and story in narration; existing UI headings remain exact where the shot plan references them. |
| B16: pacing | Retain silent holds and a 125-wpm target; replace unsupported duration estimates with a measured text count. |
| B17–B19: assumptions and concrete mechanisms | Avoid claiming samples establish uniqueness, show the actual saved decision, explain service-to-incident traversal. |

## Corrections to the proposed replacement

- “Every event” and “for good” overstate admission and retention. Say accepted events
  are stored in the event history.
- “Every item” and “always show its source” overstate provenance. Ground the claim
  in the incident/service example.
- The hook must show US INC-1042, US INC-1043 and EU INC-1042, not just two cards
  while comparing a three-result answer with a two-result answer.
- Speak the actual 1042/1043 identifiers consistently; do not call them 42/43.
- Do not claim the video performs approval while saying the button remains untouched.
- Source trust does not make every statement a fact.
- Do not turn preferred intake material into a universal three-document requirement.
- Do not narrate unverified historical assistant decisions or an empty starting graph.
- The proposed 1,300-word / 10:20 estimate is not reliable. The revised candidate is
  approximately 1,941 spoken words plus 43 seconds of holds: about 16:15 at 125 wpm,
  before navigation. Final timing must be measured from the approved narration.

## Verification and remaining gate

Source checks confirmed `classify_change(None, registry)` in workbench/engine.py,
activation unavailable in the workbench API, and the tenant runbook's statement
that the factory starts no workers and performs no pack activation. This is not a
claim that all external operational deployment procedures were surveyed.

Before recording: user reviews the revised text; reconcile the shot plan with
actual screens, expand starting points, switch from the rejected sixth event back
to the first event when describing its stored graph, and verify saved decision
and assistant form framing. Use identical visible titles and MP4 chapter names.
Keep numeric results conditional on what the filmed run reports. Recheck pacing,
layout and caption timing after recording. The review's unverified footage claims
remain open until that visual check; they are not closed by editing the script.
