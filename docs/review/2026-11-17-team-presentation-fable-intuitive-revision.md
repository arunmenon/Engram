# Presentation content plan: proposed revision for intuitiveness

Applies to `docs/engram-pack-workbench-team-presentation-plan.md` (content baseline of 2026-11-17).
Author: Fable (Claude), 2026-11-17. This is a proposal for the user and the implementer. The plan
itself is not edited. Nothing here adds a capability claim; every claim boundary and demonstration
source in the baseline stays as written.

## Summary

The baseline covers the right content. It is hard to follow because it is organised as a requirements
checklist: each slide carries six to ten required items, four concept slides come before the first
screen, and the audience changes domain four times.

This revision keeps all 17 slides' content, the appendix, the three clips and the claim boundaries. It
changes five things:

1. One case, Ann's email change, carries the main arc.
2. Each concept is introduced where it is first used, not in a block at the start.
3. One picture is reused on every slide so the audience always knows where they are.
4. Concepts are shown as a wrong outcome next to a right one.
5. Each slide states its point positively and puts its limit in a fixed footer.

One trade-off to decide: the architecture and tenant slides move from the start to the end. Engineers
wait longer for them. The reused picture on slide 2 gives them the outline early.

This changes my earlier advice to open on request 42. That was written before M6 produced a CRM
revision that runs end to end. Request 42 stays, as the case the data cannot settle.

## Why Ann

- It is the only example that runs through the whole product: inputs, proposal, steering, test,
  approval.
- It has a before and after that can be shown on real screens. Under the email-keyed pack the sample
  entity list shows two Anns. In the recorded run after the revision there is one.
- Request 42 is the same question in reverse. Ann is one person wrongly split in two. Request 42 is
  two requests that could wrongly be merged. Showing both makes "how do we tell two records apart" a
  concrete idea.

## Five devices, used on every slide

| Device | What it is | Rule |
|---|---|---|
| The strip | events → rules (the pack) → graph → answer, with a lane underneath: operator, agent, engine, test | Introduced on slide 2. Every later slide shows it small, with the current position highlighted. |
| Four colours | operator said, agent proposed, engine checked, test observed | Same colours in slides, captions and clip overlays. |
| Before and after | wrong outcome beside right outcome | Two Anns and one Ann; expected and recorded; planned and stored. |
| Footer | "Shows:" and "Does not show:" in one line each | The title carries the positive point. Limits live in the footer and are gathered on slide 17. |
| Term budget | at most one new term per slide | Baseline slide 3 introduces about twelve. New terms are listed per slide below. |

One comparison is used throughout, and only one: the pack is the rulebook for reading a tenant's
events, and the engine applies it. Say once where it stops being true: the rulebook can only use rules
the engine already supports.

Domain changes are announced in one sentence each time, and there are four: procurement on slides 5
and 8, PDLC on slide 12, incident operations on slide 14.

## Revised sequence

Act lengths: problem 4 minutes, one full loop 18, the same loop elsewhere 8, where we are 6. Clips are
inside those times.

| # | Title | Content | Visual | New term | Baseline slides |
|---|---|---|---|---|---|
| **Act 1** | **The problem** | | | | |
| 1 | Why did Ann become two people? | The CRM sends the same contact twice with a new email. Identified by email, she becomes two contacts and her history splits. Glimpse of the result: one Ann. State Engram's purpose in one sentence. | Real sample list with two Anns; recorded graph with one. Labelled synthetic data, guided revision. | none | 1, part of 12 |
| 2 | What does Engram do with events? | The strip. Events arrive; the pack's rules say what each record is and how to tell two apart; the engine builds a graph of records and connections; questions are answered from it with links back to the source events. One sentence on research grounding, pointing to appendix A. | The strip, built in four steps, with Ann's two events flowing through it. | context graph, pack | 2, overview of 4 |
| **Act 2** | **One full loop with Ann** | | | | |
| 3 | Start a tenant draft | Name, purpose, permission to use the agent, review for sensitive data, trusted producers. Choosing packs: core is always present, memory and user are optional, a domain pack carries this tenant's rules. | Tenant setup screen, current action highlighted. | tenant | 6, composition from 3 |
| 4 | What does the operator supply? | CRM material as the worked example: the written definition, the event contracts, the test history, the questions. What each can establish and what samples cannot prove. | Worksheet with one real line per input. | source material | 7 |
| 5 | Inspect the data | Announce procurement. Category suggestions and corrections, saved text, inventory, search for 42 showing east and west. The reverse of Ann: here merging would be the mistake, and the samples cannot decide. | Clip 1. | none | 8 |
| 6 | Review what the agent proposes | Back to Ann. Plain summary, record graph, the review item "Contact currently uses email to identify a person", where each statement came from. Name the five parts of a pack as the things being reviewed: record types and identity, event contracts, mappings, states, retrieval settings. | Proposal screen with one source excerpt. | ontology (said once) | 9, pack anatomy from 3 |
| 7 | Ask and steer | Operator's words, prepared request, what it may affect, explicit send, revised pack and change list. Explanation is not revision. | Clip 2. Operator wording and generated wording kept visibly separate. | none | 10 |
| 8 | When information is missing or a request fails | Announce procurement. Supplier link missing, two policies in conflict, unit identity undecided: three questions, no invented answers. Then the controlled failure: text kept, pack kept, review before retry. | Unresolved proposal still; recovery still. | none | 11 |
| 9 | Test with reviewed questions and events | Questions with expected answers written first, entities chosen, review recorded, events run, expected beside retrieved, stored graph event by event. Planned change and stored result shown side by side. | CRM steps 4 and 5. | story is not introduced yet | 12 |
| 10 | What does the score prove? | Ask the room first. F1 1.0 on two questions, neither about Ann: no regression. One Ann in the stored graph: observed, not asserted. A candidate answer is not proof of the right answer. | The two questions beside the stored graph. | none | takeaway of 12, review probes |
| 11 | Approve and hand off | The approved package, its bundle and input identity. Approval freezes it. Activation and checking answers on the tenant's own data are separate and not available here. | Approved package screen with a labelled boundary. | none | 16 |
| **Act 3** | **The same loop elsewhere** | | | | |
| 12 | Run a prepared story | Announce PDLC. A story is ordered events with checks after each. 111 checks, same outcomes in memory and on Spanner, cleanup verified. This is where storage is introduced. | PDLC result with backend and cleanup labels. | story | 13, storage from 4 |
| 13 | Create a new story with the agent | Goal, outline, events, checks, a review tick per expected outcome, save, run. | Saved result from a fixture story author, labelled. | none | 14 |
| 14 | Learn from a failed or weak check | Announce incident operations. Wrong title, wrong-account answer, unsupported total; expected beside recorded; weak checks flagged; rerun keeps expectations. | Clip 3. | none | 15 |
| **Act 4** | **Where we are** | | | | |
| 15 | Under the hood: from event to answer | The strip expanded: admission, event ledger, projection, stored graph, retrieval. The pack supplies rules; the engine executes them; the agent's authoring loop sits outside execution. | Architecture diagram that visibly grows out of the strip. | none | 4 |
| 16 | Tenants and what stays separate | The four workspaces just seen, side by side: purpose, packs, inputs, producers, questions. Then runtime: authenticated routing, pinned configuration, database boundaries. A draft is not a deployed tenant. | Comparison table; draft and runtime boundary diagram. | none | 5 |
| 17 | What is verified, and what should the team try? | Status by domain and by kind of evidence: fixture, live, memory, Spanner, human. Operator sessions outstanding. Feedback tasks. | Evidence status table. | none | 17 |

## Coverage check against the baseline

Every row of the baseline's "Coverage agreement" table still has a home.

| Baseline requirement | Revised slides |
|---|---|
| Domain-agnostic value proposition before PDLC | 1 and 2; PDLC first appears on 12 |
| Architecture and study guide | 2 (outline), 15 (detail), appendix B and C |
| Research grounding | 2 (one sentence), appendix A |
| Packs, engine, core and add-ons | 2, 3, 6, 15; appendix B and C |
| Tenant configurations and isolation | 3, 16; appendix C |
| Inputs and onboarding order | 3 to 5; appendix D |
| Agent-assisted authoring and steering | 6 to 8; appendix D |
| Types, identity, contracts, mappings, lifecycle | 6; appendix B |
| Source references, trust, conflicts, unknowns | 3, 4, 6, 8 |
| Failed or stale request, restore, cancellation | 8; appendix D and G |
| Questions, entity selection, evaluation | 9, 10; appendix E |
| Planned versus stored graph | 9, 12, 14, 15 |
| Prepared and agent-assisted stories | 12, 13 |
| Negative scenarios, weak assertions, coverage | 13, 14; appendix E |
| Spanner integration and cleanup | 12, 17; appendix E |
| Approval, export, versioning, runtime boundary | 11, 16; appendix F |
| Domain diversification and artifact inventory | 5, 8, 12, 14, 16, 17 |

Nothing moves out of the deliverable. Two items move from a main slide to notes plus appendix: the
research discussion (one sentence stays on slide 2) and the pack dependency and name-collision rules
(appendix C).

## Questions to ask the room

Use the baseline's review probes aloud, one at each act break.

- After Act 1: what would you need to know to decide whether two records are the same thing?
- After slide 5: why can the samples not tell us whether east 42 and west 42 are one request?
- On slide 10: neither question mentions Ann. What does a perfect score tell us?
- After slide 11: can an approved package answer live queries?

These are teaching prompts, not evidence of comprehension.

## To confirm before the script is written

| Item | Why |
|---|---|
| Capture the two-Anns and one-Ann screens on the recording build | I saw two Anns in the sample entity list of the email-keyed baseline and one contact in the recorded run. The exact frames need a rehearsal on the final build. |
| M6-1 focused recheck | Slide 9 shows the graph review step. The reset guidance is implementer-verified only. |
| Slide 4 input lines | Take them from the CRM baseline's three sources as saved, not rewritten for the slide. |
| Decide the trade-off | Architecture and tenants at the end (this proposal) or at the start (baseline). |
| Timing rehearsal | Act 2 is nine slides and two clips in 18 minutes. If it runs long, slide 13 is the first candidate to become a still inside slide 12. |

All claim boundaries, clip sources and the production contract in the baseline apply unchanged. The
assembled deck and clips still need their own review.
