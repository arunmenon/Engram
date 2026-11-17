# Team presentation plan review

Reviewed: `docs/engram-pack-workbench-team-presentation-plan.md` (proposed structure, no slides or
recordings yet). Reviewer: Fable (Claude), 2026-11-16, read-only. Nothing in the product, packs,
expectations, drafts, the plan or earlier reviews was changed. No provider or cloud run.

## Verdict

**Approve with changes.** The structure is honest about limits and covers almost the whole operator
journey. Six changes are needed before slides are drafted:

1. Put the record-42 example before the graph definition, and keep one example through the talk.
2. Name which runnable artefact each clip uses. Two clips as written have no confirmed source.
3. Use "story" for what the screen calls a story. The plan says "journey" throughout.
4. Add the two missing steps: testing the pack with reviewed questions, and recovering from a failed or
   stale request.
5. Cut from 22 slides to about 17. The framework block is one minute per slide for the densest content.
6. Stop using "evidence" for four different things.

**Wait for M6?** No, not for preparation or for an internal teaching session that labels its limits.
Yes for final recordings of live-agent behaviour, anything on Spanner, and any readiness or
self-service claim. Details are in the last two tables.

| Area | Verdict |
|---|---|
| Narrative clarity | Revise: ordering, vocabulary and density (findings 1, 3, 5, 6) |
| Technical accuracy | Pass with two items to verify before drafting (slides 6 and 21) |
| Demonstration feasibility | Revise: clip sources unconfirmed (finding 2) |
| Evidence honesty | Pass: the plan separates draft approval, activation, fixture, live, memory, Spanner and human evidence |

## What I inspected

- The plan, read first as a newcomer, before checking anything.
- `docs/review/2026-11-04-walkthrough-narration-review.md` (known problems), the outline of
  `docs/engram-video-walkthrough-plan.md`, the M6 section of the milestone plan,
  `docs/review/2026-11-16-m5-clarity-remediation.md` and my own M3 to M5 reviews.
- Targeted current code: pack directories, the workbench capability response, story and journey wording
  in the frontend source.

Not done: no videos watched, no humans observed, no new browser run, no audit of the older footage. The
explain-with-depth skill is not installed in this session, so I applied its intent by hand. The M5-1 and
M5-2 remediation has not been independently rechecked.

## Findings, prioritised

### 1. Slides 2 to 4: the definition comes before the example (major)

- **Likely misunderstanding:** slide 3 defines nodes, relationships and source links before the audience
  has a reason to care. This repeats B1 from the narration review. The plan's own prose says to open
  with the identity example, but the table puts it on slide 4.
- **Second problem:** the example changes shape. Slide 4 says "record 42 across two accounts", clip 1
  says "repeated 42 in different units", and the comprehension check says "account field". The
  procurement case that has units has no pack, so it cannot show "the consequence of an incorrect
  merge" in a real graph.
- **Correction:** slide 2 becomes the hook: request 42 in the east unit and request 42 in the west unit,
  and the question that goes wrong if they are merged. Draw the merge consequence as an illustration
  and say it is one. Then slide 3 builds the graph from those two requests. Use "unit" everywhere.

### 2. Clips 1 to 3 and slides 17, 21: no named runnable source (major)

| Item | Problem | Correction |
|---|---|---|
| Clip 1, "expose both units" | In the build I accepted for M5, the inventory showed counts only. Showing both units depends on the M5-1 fix, which has implementer checks only. | Record after the independent recheck, or narrate only what the accepted build shows. |
| Clip 2, explain to revision "with outcome" | The independently reviewed explain, steer and revise sequence used a fixture agent. The only live case on record ends unresolved, with no revision. | Decide now: fixture sequence labelled as fixture, or wait for M6 live evidence. Do not mix the two in one clip. |
| Clip 3, "deliberate failure" on a prepared PDLC story | Prepared PDLC stories pass. The reviewed failing story is the incident-operations fixture, which the plan says not to relabel. | Either show the incident fixture under its real name, or show a PDLC run plus the weak-assertion flag. Do not edit an expectation to manufacture a failure. |
| Slide 17, saved authoring example | The saved examples I reviewed came from a fixture story author. | Say "saved result from a fixture author" on the slide. |
| Slide 21, sales | The repository has a CRM fixture pack (accounts, people, deals) and a sales contact intake with no proposal. Neither is a workbench-authored sales pack. | State which one is shown. An intake draft is not a pack. |

### 3. "Journey" versus "story" (major)

- **Evidence:** the screens say "prepared stories", "Run this story", "What this story checks", "Plan a
  follow-up story", "Create a new story with the agent". "Journey" survives on one button ("Propose
  journey outline") and one progress message.
- **Likely misunderstanding:** viewers hear "journey" and see "story". The narration review called this
  vocabulary drift.
- **Correction:** say "story" in titles and narration. Mention once that one button still says journey.

### 4. Two operator steps are missing (major)

- **Testing the pack itself.** Steps 4 and 5 of the workbench ("Questions to answer", "Test with
  examples") let the operator write a question, record the expected answer from the source material,
  run the sample events and compare. The plan covers expected-answer review only inside story
  authoring. Add it to slide 13 or give it half of slide 16.
- **Recovery.** Slide 14 shows a successful request. It does not show what happens when the agent
  fails, the request goes stale, or the page is reloaded mid-answer. One screenshot and two sentences
  on slide 15 are enough: typed input is kept, the previous pack is kept, nothing is approved.

### 5. Timing: 22 slides will not fit (major)

About 30 minutes of speaking for 22 slides is 80 seconds each. Slides 5 to 9 teach packs, composition,
the engine, tenant scope and the workbench boundary in seven minutes with no screen shown.

| Change | Saves |
|---|---|
| Merge slides 1 and 2 into the hook | 1 slide |
| Slide 6 (core, add-ons, domain packs): two sentences on slide 5, detail to appendix | 1 slide |
| Merge slides 8 and 9 into one draft, configuration and runtime boundary slide | 1 slide |
| Slides 18 and 19 are one clip: one slide | 1 slide |
| Fold slide 21 into slide 22 as one row per domain | 1 slide |

That gives 17 slides. Keep slide 7 (one event traced through the engine); it is the mechanism the rest
depends on.

### 6. "Evidence" is used for four things (minor)

The plan uses it for source material (slide 11), proposal citations (13), test results (22) and the
handoff package (20). Use "source material", "where this came from", "test results" and "approved
package". This is B4 from the narration review.

### 7. Smaller points

- **Slide 20 and the last comprehension check:** "intent readiness" is never defined. Say it as an
  action: "checking that the pack answers well on the tenant's own data, which the workbench does not
  do".
- **Slide 13:** the screen is titled "How Engram understands them". Name the screen once, then describe
  it as the proposal review.
- **Slide 15:** "blank answers remain unresolved" is true, but in the accepted build the apply button
  stayed disabled with no reason until every decision had text. Show the remediated screen only after
  recheck.
- **Slide 6:** verify at drafting time. Current state: core, memory and user are roots; PDLC is the only
  domain pack shipped in the product; CRM is a test fixture.
- **Agent wording:** the responsibilities section is accurate. Add one visible line to slide 14 or 17:
  the live case on record followed an operator instruction that named the conflict; it does not show
  unprompted detection.

## Coverage of the operator journey

| Step | Slide | Status |
|---|---|---|
| Source intake and categories | 11 | Covered |
| Consent before the agent | 10 | Covered |
| Producer trust | 8 | Covered as a concept; no screen. Add to slide 10's screen. |
| Sample inventory | 12, clip 1 | Covered; depends on M5-1 recheck |
| Identity and state decisions | 4, 12, 15 | Covered; identity appears three times, state changes once |
| Proposal inspection and citations | 13 | Covered |
| Explanation | 14, clip 2 | Covered |
| Steering and review before send | 14 | Covered |
| Revision recovery | none | **Missing** |
| Questions and expected answers for the pack | 11 (mention only) | **Missing as a step** |
| Running sample events for the pack | none | **Missing** |
| Prepared stories | 16 | Covered |
| Agent-assisted story authoring | 17 | Covered, saved example |
| Expected-outcome review for a story | 17 | Covered |
| Execution, planned versus stored graph | 18, clip 3 | Covered |
| Failure diagnosis and weak assertions | 19 | Covered; failure source unconfirmed |
| Handoff | 20 | Covered |
| Domain comparison | 21 | Covered; duplicated by 22 |

## Proposed sequence (17 slides)

1. Request 42 in two units: the question that goes wrong
2. A graph built from those two requests
3. What a pack defines (core and optional packs in two sentences)
4. One event traced through the engine
5. Draft, tenant configuration and runtime: three different things
6. Start a tenant draft: purpose, permission, producer trust
7. Source material: what each kind establishes
8. Inspect sample data (clip 1)
9. Review the proposal: operator facts, agent proposals, engine checks
10. Ask and steer (clip 2)
11. Missing information, conflicts and recovery
12. Questions, expected answers and running the examples
13. Prepared stories
14. Author a new story
15. Run, compare and read a failed check (clip 3)
16. Approval and handoff: what is and is not available
17. What is verified, by domain, and what to try

## Claims and what supports them

| Claim or demonstration | Supported now | Verify before recording | Needs M6 |
|---|---|---|---|
| Category suggestions, correction, reload retention | Yes (M5 review) | | |
| Inventory counts and "samples cannot prove uniqueness" | Yes | | |
| Inventory shows which values repeat and their units | | Yes: M5-1 recheck | |
| Consent precedes any agent call | Yes (M3 to M5) | | |
| Explain, steer, revise with a fixture agent | Yes, as fixture | Label on screen | |
| Explain, steer, revise with a live agent | | | Yes |
| Honest unresolved proposal from a live agent | Yes, one guided case | State that it was guided | Unprompted detection |
| Prepared PDLC stories run in isolated memory | Yes | Build identity in notes | |
| Story authoring with per-check review and save | Yes, fixture author | RR-1 fix is in the recorded build | Live authoring |
| Failed check shows expected versus recorded | Yes, incident fixture | Name the fixture truthfully | |
| Weak assertions flagged | Yes for the reviewed cases | Three neighbouring cases still read as passing | |
| Approval pins the package; no activation in the workbench | Yes (capability response reports activation unavailable) | | |
| Pack answers well on tenant data | | | Yes |
| Any Spanner execution | | | Yes |
| Operators can use this unaided | | | Yes: human sessions |
| Sales or procurement pack built in the workbench | No | Choose the artefact actually shown | Complete non-PDLC case |

## Delivery gate

- **Now:** revise the structure, draft slides and speaker notes, capture screenshots on an identified
  build.
- **After the M5-1 and M5-2 recheck:** record clip 1 and the slide 15 screen.
- **Before M6, internal teaching session:** acceptable if slide 17 of the revised sequence is shown and
  each clip carries its fixture or live label.
- **After M6:** live-agent clips, Spanner, human-use statements, and any wording that sounds like a
  release.
- **Before sharing:** the assembled deck and clips need their own review; this checkpoint does not
  cover them.

Open product findings from M0 to M5 are unchanged by this review.
