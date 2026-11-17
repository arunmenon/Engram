# Proposed voiceover: Engram walkthrough, framework-first cut

Date: 2026-11-04. Companion to `2026-11-04-walkthrough-narration-review.md`. Ready to read aloud at about 125 words per minute. `[hold 5s]` means the narrator stops and the screen stays still. Lines in square brackets that begin with "If" are conditional on the filmed run and must match the report on screen. Nothing here claims a live activation, a fresh assistant run, or behaviour of a deployed service.

Vocabulary used throughout: customer (not tenant, until chapter 8), pack (not ontology, model or bundle), the assistant (not the model), story (not journey), material, citations, link back, results (not evidence), the pack's diagram / what one event should write / what was actually stored.

---

## Chapter 0. One incident, two accounts (0:25)

Screen: illustration still. Two incident cards, both numbered INC-1042, one marked US, one marked EU. Beside them, a wrong answer listing three incidents and a right answer listing two.

> A payments company runs a checkout service in the United States and another in Europe. Both report incidents, and both number them from one. So there is an incident forty-two in each account, and they have nothing to do with each other.
>
> Ask "which incidents affect US checkout?" and a system that goes by names alone answers with three incidents. The right answer is two.
>
> Everything in this video is about getting that answer right, and being able to show why it is right.

---

## Chapter 1. What Engram does, and what a pack is (0:45)

Screen: overview 01, redrawn with the incident example in the three boxes.

> Engram keeps every event a customer's systems send. An event is one report: an incident opened, an incident resolved, a comment added.
>
> From those events Engram builds a graph: the incidents, the services, and which affects which. Every item in the graph links back to the event that created it, so an answer can always show its source.
>
> [hold 4s]
>
> Events do not say how to read them. Nothing in "incident forty-two" says whether the account is part of its identity. That is the pack's job. A pack is the rulebook for one customer's world: what the things are, how to tell two of them apart, which events are accepted, what each event changes, and where to start looking for an answer.
>
> Engineers call the definitions in a pack an ontology. In this video we will just say pack.
>
> One Engram engine serves many customers. Each customer has its own pack, written down, versioned and tested, instead of rules hidden in code or in a prompt.

---

## Chapter 2. What a pack defines (0:55)

Screen: overview 03. Four boxes: things and keys; event contracts; mapping rules; starting points. Footer line about questions and expected answers.

> Here is what the Northstar pack defines.
>
> First, the things and their keys. There are incidents and services. An incident's key is its account plus its number, so US forty-two and EU forty-two stay apart. A service's key is its account plus its name. An incident can be open or resolved, and the pack says that only an open incident may become resolved.
>
> [hold 3s]
>
> Second, event contracts. For "incident opened", the account, the number, the service and the title must be present. An event missing its account is refused before it touches the graph.
>
> Third, mapping rules. "Incident opened" creates or updates the incident, creates or updates the service, and links them with "affects". "Incident resolved" moves the incident to resolved and must not touch the service. "Incident comment" is kept in the event history and changes nothing in the graph.
>
> Fourth, starting points. For "which incidents affect this service", start at the service and follow the affects link backwards to the incidents.
>
> [hold 3s]
>
> Alongside the pack sit the customer's questions with their reviewed right answers. They are how we test the pack.
>
> A pack only uses features the engine already has. It cannot add new processing code.

---

## Chapter 3. One event, start to finish (0:50)

Screen: overview 04, the five-step flow. Narrator names each box as it is highlighted.

> Follow one event: incident forty-two opened against US checkout.
>
> Admission. Engram checks who sent it and whether it meets the contract. A refused event is recorded as refused; it does not vanish.
>
> Ledger. The accepted event is kept, unchanged, for good.
>
> Worker. A background process reads the event and applies the mapping rules: upsert the incident, upsert the service, link them.
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

## Chapter 4. Which packs a customer uses (0:35)

Screen: the workbench pack-selection panel on the Northstar draft ("Advanced · existing packs and optional roots"), already open.

> This is the operator workbench, and this panel shows which packs Northstar uses.
>
> Every customer gets the core pack. It defines events and the shared building blocks other packs reuse. Two optional packs exist: memory, which adds beliefs, goals and episodes, and user, which adds profiles and preferences. Northstar needs neither. Its own pack is the one we just looked at.
>
> Engram checks the chosen packs together. Each must have what it requires, and two packs cannot define the same name.
>
> Choosing packs decides what Engram understands. It does not decide who can see what. Each customer's data sits in its own database, and callers are identified by their credentials. Those are separate controls, and this video does not change them.

---

## Chapter 5. The workbench: build the pack from the customer's material (2:10)

### 5a. Customers (0:25)

Screen: the "All customers" page with the Northstar card and the prepared stories.

> Each card here is one customer draft. A draft holds the customer's material, the pack the assistant proposed, the questions, and the test results. Below the cards are prepared stories: finished packs with saved event sequences you can run without building anything.
>
> A draft is a workspace. Creating one does not create a database for the customer and does not put anything live.

### 5b. Who is this customer (0:25)

Screen: Northstar, step 1.

> Northstar is a synthetic example: a payments company, checkout incidents in two accounts, from opened to resolved. On-call scheduling and automated fixes are out of scope, and the scope says so.
>
> Before any material leaves this screen, the operator decides whether it may be sent to the assistant, and confirms it has been checked for sensitive data. The environment label, sandbox training, says what this draft is for.

### 5c. What describes their world (0:25)

Screen: step 2, the three sources listed.

> Three pieces of material. A process document, which explains the vocabulary and the rules in prose. The event schema, which lists the fields each event carries. And sample events, including one with a missing account, so we can see refusal work.
>
> You need all three. Prose does not say which field is the key. Five samples cannot tell anyone whether a number is unique. The assistant reads all of it and will ask when the material does not settle a point.

### 5d. How Engram understands them (0:30)

Screen: step 3, the proposal and the pack's diagram. Corner caption: saved assistant history.

> What you see is the pack the assistant proposed in an earlier session. It is saved history; no assistant run happens in this recording.
>
> The incident's key is account plus number. The service's key is account plus name. That is what keeps the two checkout services apart.
>
> [hold 4s]
>
> This diagram shows what the pack allows: the kinds of things and the links between them. It is not a picture of stored data; we will see stored data after the run.

### 5e. Decisions and the pack check (0:25)

Screen: the proposal's decisions and citations, then the "Check this pack with Engram" result.

> Each claim in the proposal shows where it came from: a quote from the document, or an answer the operator gave. The assistant could not settle two things from the material alone, whether an incident number repeats across accounts and what happens when a resolution omits the title, and the operator answered both.
>
> [hold 3s]
>
> "Check this pack with Engram" loads the pack into the engine and tries every sample event against its contracts. A pass here means the pack is well formed. It does not mean the answers are right. That comes next.

---

## Chapter 6. The workbench: prove it with examples (1:50)

### 6a. Questions the customer will ask (0:35)

Screen: step 4, with the "Starting point (optional)" section expanded on the first question.

> Two questions, written in the customer's words, each with its right answer picked from the sample events by name. US checkout should return incidents forty-two and forty-three. EU checkout should return only its own forty-two.
>
> [hold 5s]
>
> Each question also names where Engram should start: the US checkout service, or the EU one. And this box says start only there. Without it, the word "checkout" in the question could pull in the other account's service as a second starting point. That is a control on where the search begins. It is not a wall between accounts: anything linked to the starting point can still be reached.
>
> Finally, trust. Only events from the producer we name here count as facts. Naming it in a draft grants nothing in production.

### 6b. Run the examples (0:20)

Screen: step 5, the run button, then the capacity panel.

> Now we run it. Engram replays the six sample events through admission, the ledger, the worker and the graph, on a Spanner database reserved for tests, then answers both questions. The database is cleaned and released afterwards.
>
> The wait is cut in this video. No customer service is touched.

### 6c. The results (0:30)

Screen: "Example checks passed", the question table.

> [hold 5s]
>
> [If the filmed report shows 100%:] The report card: both questions returned exactly the reviewed answers, an average score of one hundred percent against a required one hundred. The score compares the actual answers with the written ones, not just their counts.
>
> This is proof for these six events and these two questions, on this database. It says nothing about questions we did not write.

### 6d. The refused event and the graph, step by step (0:25)

Screen: the "Executed event" selector set to event six, then the observed graph.

> The sixth event is missing its account, and the report shows it as refused. That is the intended outcome, and it stays visible instead of disappearing into a pass count.
>
> [hold 4s]
>
> The selector steps through the events. After each one you can see what was actually stored: here, after the first event, one incident, one service, and the affects link between them. This is stored data, not the pack's diagram.

---

## Chapter 7. Prepared stories, and writing a new one with the assistant (1:50)

### 7a. A prepared story (0:30)

Screen: "PDLC · references journey", the "Run this story" page.

> Northstar was built from scratch. Software delivery, the PDLC pack, is a finished pack that ships with stories already written.
>
> A story is a fixed sequence of events with checks after each one. This story tests reference boundaries: when a change mentions a ticket, Engram must link to that ticket and not to its neighbours, and every reference must carry its full identity. The story starts with an empty test graph.

### 7b. Run it (0:20)

Screen: run button clicked; wait cut.

> Running a story needs no assistant. The pack and the expected outcomes are pinned; Engram replays the events on a Spanner test database, exactly as before.

### 7c. The result (0:25)

Screen: "All checks passed", then "Story timeline".

> [hold 5s]
>
> [If the filmed report shows 13/0/0/0:] Thirteen checks passed, none failed, none unsupported, no errors, on Spanner. Unsupported would mean a check this test harness cannot run; it is never counted as a pass.
>
> The timeline ties each event to its checks and to the graph after that step, so a failure can be read at the step where it happened. Other prepared stories cover implementation, planning and release, and each has its own result.

### 7d. A story written with the assistant (0:35)

Screen: the saved variant story, then the "Create a new story with the assistant" form. Corner caption on the variant: saved assistant history.

> Two different jobs use the assistant. Building a pack changes what Engram understands. Writing a story creates a test for a pack that already exists.
>
> This story was written with the assistant in an earlier session, and is shown as saved history. It copies the reference story and adds one exact retry of its last event, to check that a retry changes nothing.
>
> [hold 3s]
>
> This is the form it came from. You describe the situation and the rules that must hold. The assistant proposes an outline; you correct it; it then writes the events and the checks; you review them and save the story separately, so the original stays intact. If a story fails, the question is whether the pack, the events or the expectation is wrong. The expectation is not edited to turn the result green.

---

## Chapter 8. Approve, hand off, and what happens after (1:00)

### 8a. Approve and hand off (0:30)

Screen: Northstar, "Approve and hand off". Change classification label visible.

> Back to Northstar. Approval freezes one exact package: the material, the pack, the operator's decisions, the questions, and this run's results. Change any of them and the results go stale and must be rerun.
>
> Engram also labels what kind of change the pack is. For a first pack that is simply "initial". Later versions are classified as additive, mapping or breaking, which decides whether the graph must be rebuilt.
>
> We leave the approve button alone in this video.

### 8b. What approval does not do (0:30)

Screen: overview 06, retitled "Three separate steps".

> Three separate steps, and this video performs only the first.
>
> One: approve, which we just saw. Two: put the pack to work. That means starting this customer's service, called a tenant, with the approved pack pinned in its configuration. It is an operations change; this workbench has no button for it. Three: confirm it answers. Each kind of question stays switched off until its test questions have been run and recorded against the customer's own graph. A brand-new customer has an empty graph, so that check comes later. We rehearsed that gate on a test database, not on a customer service.
>
> What you have seen: a customer's events, a pack built from their material with the assistant, proof by running their examples on a real database, and a package ready to hand off. What you have not seen: a live service, or the assistant running during this recording.

---

## Word counts and timing

About 1,300 words of narration plus roughly 60 seconds of holds, about 10:20 at 125 words per minute. Chapter 0 is new footage; chapters 1 to 3 and 8b are the overview stills; everything else is the existing workbench footage with the reframing listed in the review's section E.
