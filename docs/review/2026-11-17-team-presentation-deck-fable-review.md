# Team presentation deck review: executive value

Reviewed: `output/presentation/engram-team-20261117/engram-team-presentation.html` (24 slides, with
speaker notes), its PDF, and `docs/engram-team-presentation-script.md`.
Reviewer: Fable (Claude), 2026-11-17, read-only. The deck, product, packs, expectations and data are
unchanged. No provider or Spanner call.

## Verdicts

| Area | Verdict | Reason in one line |
|---|---|---|
| Executive value clarity | **Revise** | The deck shows how the workbench works from slide 3. It never says who has the problem, what the alternative is, or what decision is being asked for. |
| Operator-story clarity | Pass with changes | The loop is easy to follow. Each step needs one line on why it matters. |
| Technical accuracy | Pass | I found no overclaim. Every limit from the reviews is present. |
| Visual readability | Pass with changes | Clean and consistent. Limits are in 12px footers and the UI stills cannot be read without zooming. |
| Recording readiness | Not ready | Five stills only. Ann captures, three clips and voice track are pending, as the manifest says. |

## Why the value is not coming through

1. **The problem is one defect.** Slide 1 shows Ann split in two. The audience can conclude "they fixed
   an email bug". Nothing says this is one instance of a general problem, or what a wrong answer costs
   someone.
2. **There is no "before".** Nothing shows how a pack gets written without the workbench. The repository
   has that path documented (`docs/runbooks/pack-authoring.md`: an engineer writes the pack file, checks
   it loads, feeds events, writes the evaluation set). Without the contrast, the workbench looks like a
   set of screens, not a change in who can do the work.
3. **Nobody is named.** The deck never says who supplies what, or who the operator is today.
4. **Packs are introduced by name, not purpose.** Slide 2 lists Core, Memory / user and Domain pack.
   It does not say what separating rules from the engine buys.
5. **Limits are louder than the point.** Most slides end on what they do not show, and the last slide is
   a status report. The honesty is right. Its placement makes the product sound smaller than it is.

What the presenter says in the notes for slides 1 and 2 is good and partly fills gaps 1 and 4. An
executive reading the slides or the PDF does not get it.

## The seven executive questions

| # | Question | Where answered | Status | Consequence of the gap |
|---|---|---|---|---|
| 1 | What problem are we solving? | Slide 1, one example | Partial | Reads as a single bug, not a class of problem |
| 2 | What is Engram's role? | Slide 2 strip; notes | Partial | No source systems on the left, no consumer on the right; could be mistaken for reporting software |
| 3 | Why ontology packs? | Slide 2 names; slide 15 late | Missing as a reason | "Why not just code it?" has no answer until minute 30 |
| 4 | Why a workbench? | Nowhere | Missing | The audience sees buttons without knowing what they replace |
| 5 | Who contributes what? | Scattered in footers ("Operator supplied", "Agent proposed") | Missing as a picture | Unclear whether this needs an engineer, a domain expert or neither |
| 6 | What changes operationally? | Nowhere | Missing | No before and after, so no sense of what gets easier or safer |
| 7 | What do we have, and what is the next decision? | Slide 17 | Partial | Status is clear; the ask is one line and no decision is requested |

## Value proposition

The candidate in the prompt is accurate. It is not distinctive: "make rules explicit" and "support
useful questions" could describe many products. Proposed replacement:

> Engram gives applications and AI agents context they can trace: connected records built from a
> tenant's events, under domain rules that are written down and reviewable. The pack workbench is where
> someone who knows the domain, working with an agent, turns their documents and sample events into
> those rules, sees what the rules would do, and tests them on reviewed examples before an engineer
> puts anything into service.

What makes it specific: the context is traceable to events; the rules can be read by the person who
knows the business; the test happens before handoff. It claims no speed, cost or autonomy.

### Capability to benefit

| Capability (demonstrated) | Operator consequence | Intended business benefit (hypothesis) | Evidence and limit |
|---|---|---|---|
| Identity rule shown, questioned and revised in plain words | The domain person can catch "this splits one person in two" before any data is loaded | Fewer wrong answers reaching downstream users | One guided CRM revision; one contact observed for Ann. No production measurement. |
| Sample inventory shows repeats with their neighbouring fields | The operator sees that request 42 exists in two units and must decide | Identity decisions made by the business, on the record | Independently reviewed. Samples cannot prove a rule. |
| Proposal lists where each statement came from, and its open questions | The operator can check a claim against the source instead of trusting it | Auditable onboarding decisions | Reviewed with fixture and one live case. A citation is not proof. |
| Missing or conflicting information stops the pack | No invented relationship or silently chosen policy | Lower risk of a confident wrong configuration | One guided and one neutral live observation. Not a general detection rate. |
| Reviewed questions and events run before approval | Expected and found answers side by side; failures stay failures | Problems found before handoff, not after | CRM run, incident failure story. Scores cover only the chosen questions. |
| Same story run in memory and on Spanner | The operator's test is repeatable on the real storage path | Confidence that tested behaviour carries to the database | One PDLC story, 111 matching checks. One earlier timeout unexplained. |
| Approval produces a pinned package | Engineering receives rules, inputs and results together | Cleaner handoff between domain and operations | Approval is not activation. No deployment shown. |

Faster onboarding, less engineering effort and lower change risk are hypotheses. Nothing in the record
measures them.

## Three highest-impact changes

1. **Replace the two opening slides with four** that answer: what goes wrong, where Engram sits, why
   packs, why a workbench and who does what. Content is below.
2. **Give every loop slide one "why this matters" line** in the body, taken from the operator-consequence
   column above. Keep the limit in the footer.
3. **Replace the closing slide** with have, still to validate, and a proposed ask.

Slide count stays at 17 by merging 3 with 4, and 13 into 12.

## Proposed sequence

| # | Headline | Audience question | Takeaway | Visual | From current |
|---|---|---|---|---|---|
| 1 | One customer, counted twice | What goes wrong? | The data was right; the rule for reading it was wrong | Ann before and after, with the question it breaks | 1 |
| 2 | Every domain has rules like this, and they are usually unwritten | Is this just one bug? | Identity, relationships, state and trust decide the answer in every domain | Four short examples; Engram between source systems and the agents or applications that ask | 2 (strip), new |
| 3 | Rules go in a pack, not in code | Why packs? | One shared engine; each domain's rules are configuration that can be read, reviewed and versioned | Engine underneath; core, optional add-ons, domain pack on top, each with its purpose | 2 (pack rows), part of 15 |
| 4 | The workbench puts the rules in front of the person who knows the business | Why a workbench, and who does what? | Domain knowledge no longer has to pass through an engineer's reading of it | Before and after lanes; five roles | new |
| 5 | Set up the draft and supply material | What do I bring? | Purpose, permission, and four kinds of material | Merged cards | 3, 4 |
| 6 | Inspect repeated values before choosing identity | What does the data say? | The data raises the question; a person answers it | Clip 1 | 5 |
| 7 | Review the proposal before accepting it | What did the agent propose, and from what? | Valid is not the same as right | Proposal with source | 6 |
| 8 | Ask, steer, review, then send | How do I correct it? | Asking changes nothing; sending requests a revision | Clip 2 | 7 |
| 9 | Missing information is a useful result | What if we do not know? | Unknowns stay visible; failures lose nothing | Two stills | 8 |
| 10 | Prove the pack with reviewed examples | How do we know it works? | Expected answers are written before the run | CRM test screens | 9 |
| 11 | A perfect score answers a specific question | What does the score mean? | No regression on two questions; not proof of the change | Score beside its limits | 10 |
| 12 | Approval creates a handoff | What comes out? | A pinned package; nothing is activated | Handoff diagram | 11 |
| 13 | Stories make behaviour repeatable | Does it hold over a sequence, and on the database? | Same outcomes in memory and on Spanner; new stories are proposed, then reviewed | PDLC result; small authoring diagram | 12, 13 |
| 14 | A useful test can fail | What does failure look like? | Keep the expectation; investigate the difference | Clip 3 | 14 |
| 15 | The engine applies shared rules | What is under the hood? | The agent drafts; the engine executes; unsupported behaviour is engineering work | Architecture | 15 |
| 16 | Four demonstrations, one runtime boundary | Are these four tenants? | Different artifacts, labelled; runtime isolation is separate | Inventory table | 16 |
| 17 | What we have, what we still need to learn, what we are asking | What now? | A scoped next step | Three columns | 17 |

### Coverage map

Nothing leaves the deck. Moves: tenant draft and inputs share slide 5 (cards trimmed to one line each,
detail in notes); story authoring becomes the right half of slide 13 (the "ticks survive refresh"
line moves to notes); research stays one sentence in the notes of slide 2 with appendix A. All seven
appendix slides are unchanged.

## Replacement opening: slides 1 to 4

About four and a half minutes. On-slide text is complete; narration is for the notes.

### Slide 1: One customer, counted twice

**On slide**

- Ann changed her email address. Her customer ID did not change.
- Left: **2** · Ann, split by email. "How many deals has Ann been involved in?" gets half an answer.
- Right: **1** · Ann, kept together, after a reviewed rule change.
- The data was correct. The rule for reading it was not.

Footer: Synthetic CRM example. Left: planned result of the starting rules. Right: recorded test run
after a guided revision.

**Narration**

"Ann works at one of our customer's accounts. She changes her email address. The CRM knows she is the
same person, because both records carry the same customer ID. But the rule we used to read those
records said: a person is identified by their email. So Ann became two people.

Nothing was wrong with the data. Ask 'which deals has Ann been involved in' and you get half the
answer, with no error and no warning. After the rule was reviewed and changed, a recorded test run
shows one Ann.

Hold on to that: the events were fine. What was missing was a clear, checked rule for what makes
someone the same person over time."

### Slide 2: Every domain has rules like this, and they are usually unwritten

**On slide**

Four questions every domain must answer:

- **Same or different?** Is request 42 in the east unit the same as request 42 in the west unit?
- **What connects?** Which supplier belongs to which request?
- **What can change?** Can an approved request be reopened?
- **Whom do we trust?** Which system's word counts?

Strip: source systems → **events → rules → connected records → context** → applications and AI agents

Engram keeps the events, applies the rules, and returns context with a trail back to the events
behind it.

Footer: Engram does not replace the source systems and is not a reporting tool. Research background is
in appendix A; no benchmark result is claimed.

**Narration**

"Ann is one example of something every business domain has. Before a system can answer a question
from events, someone has to decide four things: when two records are the same thing, what connects to
what, what is allowed to change, and whose data to trust.

Those decisions usually live in people's heads, or buried in code. When they are wrong, the answers
are wrong quietly.

Engram sits between the systems that produce events and the applications and AI agents that need
context. It keeps every event, applies the rules to build connected records, and when it returns
context it can show which events that context came from. We call that a context graph. It does not
replace the CRM or the ticketing system, and it is only as good as the rules it is given."

### Slide 3: Rules go in a pack, not in code

**On slide**

- One shared engine. It contains no code for any particular business domain.
- **Core:** the building blocks every tenant needs.
- **Optional add-ons:** extra concepts, such as memory or user preferences, when a tenant wants them.
- **Domain pack:** this business's records, connections, allowed changes and questions.
- A new domain is a new pack. A new *kind* of behaviour is still engineering work.

Footer: A pack can only use behaviour the engine supports. Declaring something in a pack does not make
it run.

**Narration**

"So where do the rules go? Not into the engine. The engine is shared by every tenant and has no code
for sales, or procurement, or software delivery.

The rules for a domain go into a pack: a readable description of that business's records, how to tell
them apart, how events change them, and which questions can be asked. Every tenant gets a common core.
Optional add-ons bring extra concepts when they are wanted. The domain pack carries what is specific.

That separation is the design bet. Adding a domain should mean writing and reviewing a pack, not
changing the engine. The boundary is honest in both directions: if a tenant needs something the engine
cannot do, such as a kind of question it does not support, that is engineering work, and the pack
cannot paper over it."

### Slide 4: The workbench puts the rules in front of the person who knows the business

**On slide**

Without the workbench (the documented engineer path):
domain expert explains → engineer writes the pack file → engineer writes the tests → domain expert
sees the result later

With the workbench (demonstrated):
operator supplies documents and sample events → agent proposes rules and shows where each came from →
operator questions and steers → engine checks → reviewed examples are run → approved package goes to
engineering

| Who | Contributes |
|---|---|
| Domain expert | Definitions and what a correct answer looks like |
| Operator (today, one of us) | Curates material, reviews the proposal, decides open questions |
| Agent | Explains and proposes. Cannot approve or activate. |
| Engine | Checks and runs the rules, the same way every time |
| Engineering and operations | Unsupported behaviour; putting a pack into service |

Footer: The first path is the documented manual process, shown for contrast, not a measured baseline.
No time or cost saving is claimed. Tenant self-service is not established.

**Narration**

"If the rules are in a readable pack, why do we need a workbench? Because readable is not the same as
reviewed by the right person.

Today the documented way to create a pack is for an engineer to write it by hand and write its tests.
The person who actually knows that Ann is one person, or that east and west are separate, explains it
to the engineer and sees the outcome afterwards. Every misunderstanding in between becomes a rule.

The workbench changes who is in the loop. The operator brings the domain's own documents and sample
events. An agent proposes the rules and shows which source each one came from. The operator can ask
why, correct it in plain words, and leave an open question open. The engine checks the result. Then
reviewed examples are run, and you see expected next to actual before anything is approved.

Notice what the agent does not do. It does not approve, it does not activate, and it does not invent
an answer when the documents disagree. And notice who the operator is today: one of us, working with
a domain expert. A customer doing this alone is a later question we have not tested.

The rest of this session follows that loop once, with Ann, and then shows the same loop in two other
places."

## Proposed closing: slide 17

**On slide**

| We have | Still to validate | Proposed ask |
|---|---|---|
| The full loop on one sales example: supply, propose, steer, test, approve | Whether people new to it can use it unaided (operator sessions not yet run) | Two or three teams each bring one small domain: a definition, an event contract, redacted samples |
| Honest stops when information is missing or conflicting | Whether the agent finds problems without being pointed at them | Each team reviews one identity or state decision and writes one expected answer before running |
| Repeatable stories, matching in memory and on Spanner | A direct test of the change we made for Ann | We record where people needed help and where a wrong approval nearly happened |
| Independent review of the bounded technical scope | Putting an approved pack into service; answers on real tenant data | Proposed measures, to agree: tasks completed unaided, help requests, wrong approvals. No targets set yet. |

Footer: Proposed pilot, not a commitment. No production-readiness or self-service claim.

**Narration**

"Here is where we are. The loop works end to end on one example, it stops honestly when it lacks
information, the tests repeat on the real database, and that scope has been independently reviewed.

Here is what we do not know. We have not watched people who are new to this use it on their own. We
have not shown the agent finding a problem nobody pointed it to. And approval is where the workbench
stops: service rollout is separate.

So the ask is small and specific. Bring one domain you know well, with one definition, one event
contract and a few redacted examples. Pick one decision that matters, write down what a right answer
looks like before you run anything, and tell us where you needed help. We are proposing to count
completed tasks, help requests and near-miss approvals. Those are proposals for us to agree, not
targets."

## Findings

| # | Kind | Slide | Observed | Audience consequence | Smallest correction | Verify |
|---|---|---|---|---|---|---|
| D-1 | Slide | 1, 2 | No stakes, no general problem, no place for Engram among other systems | "They fixed an email bug" | Opening slides 1 and 2 above | A reader of the PDF alone can state the problem in one sentence |
| D-2 | Slide | none | No before and after, no roles | Cannot tell what changes or who is needed | Opening slide 4 | Reader can name who supplies expected answers and who activates |
| D-3 | Slide | 2 | Packs listed by name | No reason for packs until slide 15 | Opening slide 3 | Reader can answer "what happens when the engine lacks a behaviour?" |
| D-4 | Slide | 17 | Title and body are status; the ask is one sentence | No decision requested | Closing above | Slide states an ask and labels it proposed |
| D-5 | Slide | 3 to 14 | Bodies describe steps; consequences are implied | Understands the button, not the reason | One "why this matters" line per slide from the capability table | Each slide has one such line above the footer |
| D-6 | Visual | all | Footers and the strip are 12px on a 1280px canvas | Limits are unreadable from the back of a room | Footer at 16px, or a "Shows / Does not show" pair in the body on the six slides where the limit is the point (1, 7, 11, 12, 13, 14) | Legible in the PDF at 100% |
| D-7 | Visual | 5, 7, 12, 14 | Tall captures cropped to their top third; text inside is about 8px at slide size; the PDF has no zoom | PDF readers cannot check the screen against the claim | Crop each still to the region the slide talks about; keep full capture behind the zoom | The quoted screen text is readable on the slide |
| D-8 | Visual | 2 | The strip appears twice, large and small | Looks like a layout slip | Drop the small strip on the slide that introduces it | One strip on slide 2 |
| D-9 | Slide | all | The strip highlights "Pack rules" on most authoring slides and has no lane for who is acting | Authoring can be read as part of runtime | Add a thin line above the strip: "Authoring: operator and agent" or "Running: engine", highlighted per slide | Slide 8 shows authoring; slide 13 shows running |
| D-10 | Slide | 13 | "Ticks survive background refresh; a changed proposal resets them" | Bug history on a teaching slide | Move to notes | Not on the slide |
| D-11 | Slide | 16 | Title joins two ideas: a list of demonstrations and runtime isolation | Suggests four tenants | "Four demonstrations, one runtime boundary" | Title change |
| D-12 | Script | 3 | "A tenant is the organization or workspace whose configuration and data we are managing" | Tenant and draft blur | "A tenant is the customer organisation whose events and rules are kept separate. A draft is our working copy for that tenant." | Script change |
| D-13 | Script | none | Today's internal operator versus future tenant self-service is never said | Audience may assume customers do this alone | In opening slide 4 narration, as above | Present in notes and footer |
| D-14 | Recording | 7 | The recorded agent explanation contains pack syntax in its next step. The still on this slide shows the operator's own words and the plain request summary. | None on the still; the clip will show the syntax | Keep it; narrate "the agent's suggested wording is technical; the operator's request was not" | Clip narration includes that sentence |
| D-15 | Recording | 1 | Ann panes are a labelled summary, not screens | None while labelled | Replace with captures from the recording build when taken | Captures present; label updated |

Strengths to keep: slide 10 states exactly what the score does and does not show; slide 8 treats
missing information as a result; slide 14 keeps failures visible; every domain switch is labelled.

## Desk-check questions

| Question | Expected answer |
|---|---|
| The events about Ann were correct. Why was the answer wrong? | The rule identified a person by email. The rule, not the data, split her. |
| What does a pack contain, and what does it not? | A domain's records, identity, event handling, allowed changes and questions. It contains no engine behaviour. |
| What happens when the tenant needs behaviour the engine does not support? | The workbench reports it as unsupported or leaves it unresolved. It becomes engineering work; a pack cannot add it. |
| The agent proposed a rule and cited a document. Is the rule right? | Not necessarily. The operator checks the source and the engine checks validity; reviewed examples test behaviour. |
| Does approving a pack put it into production? | No. Approval pins a package for handoff. Activation and checking answers on the tenant's own data are separate and not done in the workbench. |

These are checks for the script, not results from people.

## What I inspected

- All 24 slides rendered in headed Chrome at 1440x810, on-slide text read before any notes; then all
  speaker notes; image zoom on slide 5; text sizes and clipping measured. No page errors and no
  external requests. The PDF has 24 pages.
- The script, the content baseline, my earlier structure review, the manifest and the pack-authoring
  runbook (for the manual path).
- Evidence: `output/playwright/presentation-review/fable-deck-20261117/`.

Not done: no clips or audio exist to review; no people were observed; the PDF was not read page by
page beyond page count and the implementer's page 12 image. The explain-with-depth skill is not
installed in this session; I applied purpose-first, source-grounded explanation by hand. The three
lenses (executive, operator, engineer) are my own readings.
