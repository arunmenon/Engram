# Revised voiceover for approval: Engram walkthrough

Terminology: A tenant is an isolated Engram environment with its own data and pack configuration. One customer may have several tenants, such as development and production. A tenant draft prepares configuration; it does not provision or activate a runtime.
Date: 2026-11-04. Companion to `2026-11-04-walkthrough-narration-review.md`. Working candidate for user review; not yet approved for recording. Target about 125 words per minute; estimate duration from the actual word count. `[hold 5s]` means the narrator stops and the screen stays still. Lines in square brackets that begin with "If" are conditional on the filmed run and must match the report on screen. Nothing here claims a live activation, a fresh assistant run, or behaviour of a deployed service.

Vocabulary used throughout: tenant (defined at first use), pack (not ontology, model or bundle), the assistant (not the model), story (not journey), material, citations, link back, results (not evidence), the pack's diagram / what one event should write / what was actually stored.

---

## Chapter 0. One incident, two accounts

Screen: labelled illustration. Show three incidents: US INC-1042, US INC-1043 and EU INC-1042, linked to their respective checkout services. Illustrate the wrong answer containing all three and the expected US answer containing two. This is an example of the problem, not a new measured result.

> Different systems can use the same name or number for different things. Getting that distinction right matters before we answer any question.
>
> Here is one example. Northstar has checkout services in US and EU accounts. Both accounts have an incident numbered ten forty-two. The US account also has incident ten forty-three.
>
> Ask “which incidents affect US checkout?” In this example, the expected answer is the two US incidents. Matching the word checkout alone could also bring in the EU incident.
>
> Everything in this video is about getting that answer right, and being able to show why it is right.

---

## Chapter 1. What Engram does, and what a pack is

Screen: overview 01, redrawn with the incident example in the three boxes.

> Engram stores accepted events from a tenant's systems. An event is one report: an incident opened, an incident resolved, a comment added.
>
> From those events Engram builds a graph: the incidents, the services, and which affects which. For the incident and service in this example, links back to source events let us inspect where the records came from.
>
> [hold 4s]
>
> Events do not say how to read them. Nothing in "incident ten forty-two" says whether the account is part of its identity. That is the pack's job. A pack is the rulebook for one tenant's world: what the things are, how to tell two of them apart, which events are accepted, what each event changes, and where to start looking for an answer.
>
> Engineers call the definitions in a pack an ontology. In this video we will just say pack.
>
> The same engine supports different domains. Tenants select packs with written, versioned rules. A tenant can use an existing pack or author a new one.

---

## Chapter 2. What a pack defines

Screen: overview 03. Four boxes: things and keys; event contracts; mapping rules; starting points. Footer line about questions and expected answers.

> Here is what the Northstar pack defines.
>
> First, the things and their keys. There are incidents and services. An incident's key is its account plus its number, so US ten forty-two and EU ten forty-two stay apart. A service's key is its account plus its name. An incident can be open or resolved, and the pack says that only an open incident may become resolved.
>
> [hold 3s]
>
> Second, event contracts. The contract lists the required fields for each event. The account is required in this example. An event missing its account is refused before it touches the graph.
>
> Third, mapping rules. "Incident opened" creates or updates the incident, creates or updates the service, and links them with "affects". Other event rules describe state changes or explicitly keep an event in the history without creating domain records.
>
> Fourth, starting points. For "which incidents affect this service", start at the service and follow the affects link backwards to the incidents.
>
> [hold 3s]
>
> Alongside the pack sit the tenant's questions with their reviewed right answers. They are how we test the pack.
>
> A pack only uses features the engine already has. It cannot add new processing code.

---

## Chapter 3. One event, start to finish

Screen: overview 04, the five-step flow. Narrator names each box as it is highlighted.

> Follow one event: incident ten forty-two opened against US checkout.
>
> Admission. Engram checks who sent it and whether it meets the contract. The sandbox report shows refused input separately from accepted events. That does not mean refused input enters the ledger.
>
> Ledger. The ledger stores the accepted event as part of the event history.
>
> Worker. A background process reads the event and applies the mapping rules: create or update the incident, create or update the service, and link them.
>
> Graph. The incident and the service are now stored, with a link back to this event.
>
> Retrieval. A question arrives: which incidents affect US checkout? Engram starts at the US checkout service and follows the affects links.
>
> [hold 4s]
>
> Two things have to be right at once: the keys, so there is one US checkout service and one EU one, and the starting point, so the search begins at the right service. A name that merely looks similar is not enough. And whatever comes back, we compare it with the answer we wrote down beforehand.
>
> This diagram explains the mechanism. The screens that follow show real runs.

---

## Chapter 4. Which packs a tenant uses

Screen: the workbench pack-selection panel on the Northstar draft ("Advanced · existing packs and optional roots"), already open.

> This is the operator workbench, and this panel shows which packs Northstar uses.
>
> Every tenant gets the core pack. It defines events and the shared building blocks other packs reuse. The optional packs shown here are memory, which adds beliefs, goals and episodes, and user, which adds profiles and preferences. Northstar needs neither. Its own pack is the one we just looked at.
>
> Engram checks the chosen packs together. Each must have what it requires, and conflicting definitions are rejected.
>
> Choosing packs decides which rules Engram uses. It does not decide who can see what. Each tenant's data sits in its own database, and callers are identified by their credentials. Those are separate controls, and this video does not change them.

---

## Chapter 5. The workbench: build the pack from the tenant's material

### 5a. Tenants

Screen: the "All tenants" page with the Northstar card and the prepared stories.

> Each card here is one tenant draft. A draft holds the tenant's material, the pack the assistant proposed, the questions, and the test results. The page also offers prepared stories: finished packs with saved event sequences you can run without building anything.
>
> A draft is a workspace. Creating one does not create a database for the tenant and does not put anything live.

### 5b. Tenant setup

Screen: Northstar, step 1.

> Northstar is a synthetic example: a payments company, checkout incidents in two accounts, from opened to resolved. On-call scheduling and automated fixes are out of scope, and the scope says so.
>
> Before requesting assistant authoring, the operator confirms whether the material may be sent to the assistant and reviews its sensitivity. The environment label, sandbox training, says what this draft is for.

### 5c. What describes their world

Screen: step 2, the three sources listed.

> Three pieces of material. A process document, which explains the vocabulary and the rules in prose. The event schema, which lists the fields each event carries. And sample events, including one with a missing account, so we can see refusal work.
>
> These sources serve different purposes. A few samples alone cannot establish whether a number is always unique across accounts. The assistant reads all of it and will ask when the material does not settle a point.

### 5d. How Engram understands them

Screen: step 3, the proposal and the pack's diagram. Corner caption: saved assistant history.

> What you see is the pack the assistant proposed in an earlier session. It is saved history; no assistant run happens in this recording.
>
> The incident's key is account plus number. The service's key is account plus name. That is what keeps the two checkout services apart.
>
> [hold 4s]
>
> This diagram shows what the pack allows: the kinds of things and the links between them. It is not a picture of stored data; we will see stored data after the run.

### 5e. Decisions and the pack check

Screen: the proposal's recorded decisions and citations, then the pack-check result. Verify the specific saved decision is visible; do not narrate a historical assistant question without its record.

> Review the proposal's citations and the operator's recorded decisions. For example, the incident key includes its account. 
>
> [hold 3s]
>
> “Check this pack with Engram” runs the engine's pack checks. A pass here tells us the configuration passed those checks. It does not mean the answers are right. That comes next.

---

## Chapter 6. The workbench: prove it with examples

### 6a. Questions to answer

Screen: step 4, with the "Starting point (optional)" section expanded on the first question.

> Two questions, written in the tenant's words, each with its right answer picked from the sample events by name. US checkout should return incidents ten forty-two and ten forty-three. EU checkout should return only its own ten forty-two.
>
> [hold 5s]
>
> Each question also names where Engram should start: the US checkout service, or the EU one. The selected checkbox says to start only there. Without it, the word "checkout" in the question could pull in the other account's service as a second starting point. That is a control on where the search begins. It is not a wall between accounts: anything linked to the starting point can still be reached.
>
> Finally, the draft records which producers are trusted. Source trust affects configured handling and retrieval rules. It does not establish that every statement is true, and this draft grants no production access.

### 6b. Run the examples

Screen: step 5, the run button, then the capacity panel.

> Now we run it. Engram replays the six sample events through admission, the ledger, the worker and the graph, on a Spanner database reserved for tests, then answers both questions. We also check the report confirms database cleanup and release.
>
> The wait is cut in this video. No tenant service is touched.

### 6c. The results

Screen: "Example checks passed", the question table.

> [hold 5s]
>
> [If the filmed report shows 100%:] The report card: both questions returned exactly the reviewed answers, an average score of one hundred percent against a required one hundred. The score compares the actual answers with the written ones, not just their counts.
>
> This run supports these six events and these two questions on this database. It says nothing about questions we did not write.

### 6d. The refused event and the graph, step by step

Screen: the "Executed event" selector set to event six, then the observed graph.

> The sixth event is missing its account, and the report shows it as refused. That is the intended outcome, and it stays visible instead of disappearing into a pass count.
>
> [hold 4s]
>
> The selector steps through the events. After each one you can see what was actually stored: here, after the first event, one incident, one service, and the affects link between them. This is stored data, not the pack's diagram.

---

## Chapter 7. Prepared stories, and writing a new one with the assistant

### 7a. A prepared story

Screen: "PDLC · references journey", the "Run this story" page.

> Northstar was built from scratch. The software-delivery pack, called PDLC, has prepared stories we can run.
>
> A story is a fixed sequence of events with checks after each one. This story tests reference boundaries: when a change mentions a ticket, Engram must link to that ticket and not to its neighbours, and every reference must carry its full identity. The story runs in a reserved test workspace.

### 7b. Run it

Screen: run button clicked; wait cut.

> Running a story needs no assistant. The pack and the expected outcomes are pinned; Engram replays the events on a Spanner test database, exactly as before.

### 7c. The result

Screen: "All checks passed", then "Story timeline".

> [hold 5s]
>
> [If the filmed report shows 13/0/0/0:] Thirteen checks passed, none failed, none unsupported, no errors, on Spanner. Unsupported would mean a check this test harness cannot run; it is never counted as a pass.
>
> The timeline ties each event to its checks and to the graph after that step, so a failure can be read at the step where it happened. Other prepared stories cover implementation, planning and release, and each has its own result.

### 7d. A story written with the assistant

Screen: the saved variant story, then the "Create a new story with the assistant" form. Corner caption on the variant: saved assistant history.

> Two different jobs use the assistant. Building a pack defines the types and rules Engram will use. Writing a story creates a test for a pack that already exists.
>
> This story was written with the assistant in an earlier session, and is shown as saved history. It copies the reference story and adds one exact retry of its last event, to check that a retry changes nothing.
>
> [hold 3s]
>
> This form is used to request a new story. We are explaining the form, not running the assistant now. You describe the situation and the rules that must hold. The assistant proposes an outline; you correct it; it then writes the events and the checks; you review them and save the story separately, so the original stays intact. If a story fails, the question is whether the pack, the events or the expectation is wrong. The expectation is not edited to turn the result green.

---

## Chapter 8. Approve, hand off, and what happens after

### 8a. Approve and hand off

Screen: Northstar, "Approve and hand off". Change classification label visible.

> Back to Northstar. Approval records a reviewed package and its test results. The current screen shows what would be approved. We are inspecting it, not submitting approval.
>
> This workbench labels the pack “initial.” It currently compares against no prior pack. It is not showing a comparison with the last approved version. The engine has other change classifications, but this screen does not demonstrate them.
>
> We leave the approve button alone in this video.

### 8b. What approval does not do

Screen: overview 06, retitled "Three separate steps".

> Preparing a package, putting it into service, and checking answers on real data are different steps. This video runs examples and inspects the approval screen. It does not approve or deploy the package.
>
> The workbench has no activation operation. Configuring the service for a tenant is separate operational work, not a demonstrated handoff button or automated deployment.
>
> There is also a gate on pack-defined retrieval intents: named tasks used to answer questions. Those tasks need a recorded passing evaluation on the target graph. Earlier sandbox checks exercised that gate; this video does not demonstrate it on a tenant service.
>
> What you have seen: a tenant's events, a pack built from their material with the assistant, test results from running examples on a real database, and the screen used to review a package for handoff. What you have not seen: a live service, or the assistant running during this recording.

---

## Word counts and timing

Estimated spoken words: 1941. Explicit holds: 43 seconds.
At 125 words per minute this is approximately 16:15, before
navigation and additional visual inspection. This replaces the unverified 1,300-word
and 10:20 estimate. Measure actual synthesized speech before assigning scene windows.

## Recording gate and screen checks

This is a text candidate for approval, not a completed recording revision.
- Keep the opening's general problem statement before the illustrative incident.
- Show all three incidents so the two-versus-three answer comparison is visible.
- Move composition to the actual tenant pack-selection panel.
- Expand the first question's starting-point section; show the checked option.
- Show saved decision details, not a count of zero unanswered decisions.
- Hold results and timelines for five seconds before interpretation.
- Label the saved story separately from the new-story form.
- Show “initial” without implying comparison to a previously approved pack.
- Use the visible screen titles in the video chapter metadata.
- Match all numerical outcomes to the filmed run; no expectation edits for filming.
- Activation remains unavailable in this workbench. The evaluation gate is separate.
- Recheck visual fit and actual spoken pacing after script approval.
