# Walkthrough narration review

Date: 2026-11-04. Scope: the narration and screen copy of the framework-first review cut (`output/video/engram-framework-walkthrough-20261104/`, 9:38, 23 chapters). Sources read: `scripts/video/record_opening.py` (SCENES), `scripts/video/record_workbench.py` (UI scenes 1 to 17), `docs/engram-pack-framework-overview.html`, the assembled `transcript.txt`, `docs/engram-video-narration.md`, `docs/review/2026-11-03-video-rehearsal.md`. Consequential claims were checked against the working tree (pack YAML, loader, ontology model, projection, retrieval, workbench, tenant API) and against the filmed run records. The video itself was not watched; anything that depends on what the camera framed is listed in section G. No code, pack, expectation or recording was changed. The proposed voiceover is in `2026-11-04-walkthrough-narration-proposed.md`.

## Source synchronisation

- The assembled transcript matches the current SCENES text word for word (diffed), and the UI scene text matches `record_workbench.py`. The transcript does not lag the scripts.
- The label the feedback quotes, "Why the workbench exists", does not appear in any current source. The current screen 05 reads "The operator's workspace" with the subtitle "Define the understanding. Then prove it with examples." The feedback applies to that subtitle and to the same register throughout.
- The MP4 chapter titles (`chapters.txt`: Purpose, Composition, Definition, Processing, Workbench, Readiness, Prepared Pdlc, Agent Workflow, Handoff) are the recorder's anchor names, not the on-screen navigation labels (What packs do, Core, add-ons and domain packs, ...). A viewer scrubbing chapters sees a third vocabulary.
- The long narrative (`engram-video-narration.md`) still describes a 40 to 45 minute cut with chapters 7b and 8 that this cut does not contain; its "Rehearsal update" paragraphs are the only parts that describe this cut. It should say at the top which cut it governs.

## A. Verdict

Not yet. The walkthrough is honest and technically careful, but it teaches the engine's vocabulary before it gives the viewer a reason to need it. A newcomer hears seven definitions (event, graph, ontology, pack, framework, interpretation, understanding) in the first 33 seconds over a static diagram, meets "tenant", "bundle", "dependencies" and "name collisions" at 40 seconds, and only reaches a concrete thing, an incident on a checkout service, at 1:12. After that the material is good: the incident example carries through contracts, identity, the runtime flow, the questions, the sandbox run and the rejected event, and the evidence labelling is exemplary. The mental model a viewer should leave with can be stated in four sentences, and the current script never states it:

1. Engram stores a customer's events and builds a graph of the things those events describe, so questions can be answered with evidence.
2. A pack is the rulebook for one customer's world: what the things are, how to tell two apart, which events are accepted, what each event changes, and where to start looking for an answer.
3. The workbench is where an operator builds that rulebook from the customer's own documents and example events, and proves it by running those events and checking the answers.
4. Approving a pack freezes it with its proof. Putting it to work for a customer, and confirming it answers well on that customer's real data, are separate steps that this video does not perform.

The revised sequence in section C opens with the identity trap (one incident number, two accounts) as a 20-second hook, states those four sentences, and then goes through the same material in the same order the operator meets it.

## B. Findings, prioritised

Severity: **blocker** (will mislead or lose a newcomer), **major** (hurts comprehension or accuracy), **minor** (polish).

### B1 (blocker) The opening defines six abstractions before any example

Quoted (scene 1): "Engram turns events into connected knowledge. An event is a report of something that happened. A graph represents things and the relationships between them. But records alone do not explain what counts as the same thing, which connections matter, or what a change means. An ontology makes those meanings explicit. A pack packages that understanding as definitions and rules that Engram can execute. The framework lets different domains use the same engine while keeping their interpretation explicit, versioned, and testable."

Likely misunderstanding: "connected knowledge", "meanings", "understanding", "interpretation" are four words for the same thing and none is observable. A newcomer cannot picture what Engram outputs or what a pack contains.

Replacement: open on the incident (section C, chapter 0), then: "Engram keeps every event a customer's systems send, and builds a graph from them: the incidents, the services, and which affects which. A pack is the rulebook that tells Engram how to read one customer's events: what the things are, how to tell two of them apart, and what each event changes." The word "ontology" is said once, as the name engineers use for the rulebook's definitions.

### B2 (blocker) "Understanding" is used as a noun for the pack, the model and the operator's mental state

Quoted: HTML 05 "Define the understanding. Then prove it with examples."; scene 5 "The workbench is where an operator defines and tests that understanding"; scene 6 "journeys to test how understanding changes over time"; UI nav "How Engram understands them".

Likely misunderstanding: the viewer cannot tell whether "understanding" is a file, a database, or an opinion. "Define the understanding" sounds like philosophy, which is the feedback received.

Replacement: use "pack" for the artefact and say what it does. HTML 05 subtitle: "Build the pack from the customer's material. Then run their example events and check the answers." Scene 6: "A story is a fixed sequence of events with checks after each one, so we can see the graph change step by step."

### B3 (blocker) Composition (core, memory, user, tenant, bundle) comes before the viewer has seen one pack

Quoted (scene 2): "Core is always present. It defines common concepts such as events, and interfaces that domain models can use. Memory and user are optional packs ... A tenant is the customer context in which a compatible set of packs is selected. Dependencies and name collisions must be checked across that set."

Likely misunderstanding: the viewer does not yet know what a pack is, so "optional packs", "interfaces", "dependencies" and "name collisions" have nothing to attach to. "Tenant" is introduced here and then every UI scene says "customer".

Accuracy check: core is always loaded (`ontology/loader.py:11,31,218`); memory adds Belief, Goal, Episode; user adds UserProfile, Preference, Skill, Workflow, BehavioralPattern (`memory.pack.yaml`, `user.pack.yaml`); both require `core>=1.0`; duplicate pack names and property conflicts are refused (`domain/ontology.py:669-671, 962`). All true.

Replacement: move this to after "What a pack defines", cut it to four sentences, and show it on the real pack-selection screen (UI scene 3) instead of a diagram: "Every customer gets the core pack; it defines events and the shared building blocks. Two optional packs exist: memory, for beliefs, goals and episodes, and user, for profiles and preferences. Northstar needs neither. Engram checks the chosen packs together: each must have what it requires, and two packs cannot define the same name." Keep the isolation sentence (B9).

### B4 (major) "Evidence" means three different things

Quoted: scene 4 "with evidence linking the result to its source" (provenance edges); UI scene 4 "Authoring begins with evidence" (source material); UI scene 6 "reviews the evidence, assumptions, and limitations" (the proposal's citations); UI scene 11 "binds the reviewed pack to its evidence" (test results).

Replacement: "source material" or "the customer's documents and example events" for inputs; "where this came from" or "citations" for the proposal's grounding; "the link back to the event that created it" for provenance; "test results" or "the proof" for sandbox outcomes. Reserve "evidence" for the handoff package if at all.

### B5 (major) "Model" means the domain model and the language model within one minute

Quoted: UI scene 2 "whether its inputs may be sent to the configured model"; UI scene 5 "This is saved assistant-authored work, not a new model call"; UI scene 5 "The diagram describes allowed relationships"; scene 5 "the model says what is allowed".

Replacement: "the assistant" for the language model everywhere ("may be sent to the assistant", "not a new assistant run"); "the pack" or "the pack's diagram" for the domain model. The three-way comparison becomes: "The pack's diagram shows what is allowed. The planned change shows what one event should write. The observed graph shows what was actually stored."

### B6 (major) The activation sentence overstates what exists

Quoted (scene 6 and HTML 06): "Activation is a separate operational step that binds the runtime to the approved configuration" and HTML "Bind the runtime to the approved configuration through the supported operational procedure."

Accuracy check: no activation operation exists. The workbench reports activation as unavailable (`workbench/api.py:242, 262`); the tenant API factory "starts no workers and performs no pack activation" and its catalog "is fixed for the process lifetime. Configuration changes require coordinated drain and restart" (`docs/runbooks/tenant-api.md`). "The supported operational procedure" implies a documented runbook step that does not exist.

Replacement: "Putting an approved pack to work for a customer is a separate operations change: the customer's service is started with that pack pinned in its configuration. This workbench has no button for it, and this video does not perform it." Mark as **proposed/not demonstrated** in the shot list.

### B7 (major) The intent-readiness sentence is a design statement delivered as fact

Quoted: "An empty new tenant can therefore be activated while its intents remain pending."

Accuracy check: the gate is real. The artifact route returns 409 for an intent whose pack has no recorded passing evaluation on that graph (`api/routes/artifacts.py`), and the lifecycle rehearsal showed 409, then evaluate, then 200, on a leased Spanner sandbox in-process (rehearsal doc). "Activated while pending" is not something anyone has done, because activation does not exist.

Replacement: "Even after that, each kind of question stays switched off until its test questions have been run and recorded against the customer's own graph. A brand-new customer has an empty graph, so that check comes later." Say "we rehearsed this gate on a sandbox, not on a customer service" if the scene shows it.

### B8 (major) Screen 05 and scene 5 compress the whole workbench into one sentence of nouns

Quoted: "Start with the customer scope, specifications, interface definitions, and representative events. The assistant proposes a model and mappings grounded in those inputs. The operator resolves questions about identity, lifecycle, and trust, then reviews the questions and expected answers."

Likely misunderstanding: nothing here is an action the viewer could picture. "Interface definitions" is not what the screen calls it (the screen says "Interface schemas" and the material kinds are specification, schema, samples).

Replacement: narrate the four screen boxes as four things the operator does: "You write what the customer wants tracked. You add their documents, their event schema and some real example events. The assistant reads those and proposes the pack, and shows you where each idea came from. You answer the questions it could not settle from the material, for instance whether the same incident number can exist in two accounts."

### B9 (keep, but say it once) The isolation sentence is correct and important

Quoted: "Pack selection defines the model. Authentication and database boundaries provide tenant isolation." and UI scene 3 "Runtime authentication and database binding are separate controls."

Keep in plain words, once, on the pack-selection screen: "Choosing packs decides what Engram understands. It does not decide who can see what. Each customer's data sits in its own database and callers are identified by their credentials; those are separate controls and this video does not change them."

### B10 (major) Scene 7 claims a control the camera may not show

Quoted (UI scene 7): "Explicit starting points restrict discovery; they do not establish a security boundary."

Accuracy check: implemented. `seed_mode: explicit` exists on the query, route, eval set, workbench question and journey options; the filmed draft (revision 43) has it set on both questions, and the run scored F1 1.0 on Spanner (`output/video/workbench-20261104-134354/northstar-result.txt`). The UI control is a checkbox inside the collapsed "Starting point (optional)" section (`Workbench.tsx:1526-1558`); the script navigates to the page but does not expand it.

Likely misunderstanding: "discovery" has not been defined; the viewer does not know Engram finds starting points from words in the question. Replacement: "Each question names where Engram should start: the US checkout service, or the EU one. We also tick the box that says start only there, so a word like checkout in the question cannot pull in the other account's service. That controls where the search starts. It is not a wall between accounts: anything linked to the starting point can still be reached." Footage: expand the section so the checkbox and its explanatory sentence are visible (section E).

### B11 (major) Scene 17/22 narration contradicts the action

Quoted (transcript, Agent Workflow): "The assistant workflow asks for a situation and domain rules, proposes an outline, then generates events and expected outcomes after review. ... This screen contains saved authoring history." The scripted action is clicking "Create a new story with the assistant", which opens the authoring form.

Likely misunderstanding: the viewer is told they are looking at history while looking at an empty form, or vice versa. Which it is cannot be settled without the video (section G). Replacement: narrate what the form is for, and state separately that the story shown in the previous scene was made with it in an earlier session.

### B12 (major) The change classification will be read as "compared with the last approved version"

Quoted (UI scene 11): "The composed bundle is shown here, along with its change classification."

Accuracy check: the workbench classifies every draft against nothing (`workbench/engine.py:131`, `classify_change(None, registry)`), so the label is always "initial". Replacement: "Engram also labels what kind of change this pack is. For a first pack that is simply 'initial'. Later versions are classified as additive, mapping or breaking, which decides whether the graph must be rebuilt." Mark the later-versions sentence as implemented in the engine, not shown here.

### B13 (minor) "Add-ons" versus "roots"

The screen label is "Advanced · existing packs and optional roots"; the narration says "add-ons"; the HTML says "Optional add-ons". Pick "optional packs" and change the screen label when the UI is next touched.

### B14 (minor) "Journey" versus "story"

The opening says "journey" four times; every UI label says "story" ("Run this story", "Story timeline", "Create a new story with the assistant"). Use "story" throughout; say once that engineers call it a journey.

### B15 (minor) "Tenant" versus "customer"

Opening: tenant. UI: customer. HTML: both. Use "customer" throughout and say once, at handoff, that the running service for a customer is called a tenant.

### B16 (minor) Pace and inspection time

Synthetic voice at 134 to 154 words per minute, sentences up to 27 words, and no silent gaps. Scenes with tables (Reviewed Answers, Example Results, Rejected Event, PDLC Results, Timeline) run 15 to 23 seconds with four to six sentences each, leaving no time to read the table the narrator refers to. The opening scenes are 33 to 47 seconds of continuous speech over a static diagram. Target: 120 to 130 words per minute, sentences of at most 18 words, and a 4 to 6 second pause after every "here is" or "notice" line.

### B17 (minor) Assertions about the assistant's abilities

Quoted (UI scene 4): "it cannot infer reliable identities from a few example names alone." This is advice to the operator stated as a property of the assistant. Replacement: "Five sample events cannot tell anyone whether an incident number is unique. That is why the documents and the schema matter, and why you will be asked."

### B18 (minor) "Decisions to review · 0 unanswered" while narrating consequential decisions

The scene focuses on a heading that says zero decisions are open while the narrator says identity and lifecycle are consequential decisions. Narrate what the answered decisions were, or focus a screen that shows them.

### B19 (minor) Retrieval sentence is accurate but opaque

Quoted (scene 3): "Retrieval configuration guides which entities and relationships to consider for a question." Replacement: "The pack also says where to start looking for each kind of question. For 'which incidents affect this service', start at the service and follow the affects link backwards."

## C. Revised chapter sequence and screen labels

| # | Chapter (on screen and in MP4 chapters) | Footage | Time |
|---|---|---|---|
| 0 | One incident, two accounts | Still: two incident cards, both "INC-1042", one US, one EU; a wrong answer shown | 0:25 |
| 1 | What Engram does, and what a pack is | Overview screen 01, redrawn with the incident as the example | 0:45 |
| 2 | What a pack defines | Overview screen 03 | 0:55 |
| 3 | One event, start to finish | Overview screen 04 | 0:50 |
| 4 | Which packs a customer uses | UI: pack-selection screen (old UI scene 3), replaces overview screen 02 | 0:35 |
| 5 | The workbench: build the pack from the customer's material | UI scenes 1, 2, 4, 5, 6 | 2:10 |
| 6 | The workbench: prove it with examples | UI scenes 7, 8, 9, 10 | 1:50 |
| 7 | Prepared stories, and writing a new one with the assistant | UI scenes 12 to 17 | 1:50 |
| 8 | Approve, hand off, and what happens after | UI scene 11 plus overview screen 06 | 1:00 |

Total about 10:20 at the slower pace, with pauses.

Screen labels for `engram-pack-framework-overview.html` (navigation and section titles):

| Current | Proposed |
|---|---|
| What packs do | What Engram does, and what a pack is |
| Records need meaning before they become useful context. | Events are reports. Answers need the things behind them. |
| Core, add-ons and domain packs | Which packs a customer uses |
| Shared foundation. Optional additions. Domain meaning. | One required pack, two optional packs, and the customer's own pack |
| Inside a domain pack / Make the interpretation explicit. | What a pack defines / Things, keys, events, changes, starting points |
| How events become answers / Follow one event into an answer. | One event, start to finish (keep subtitle) |
| Create and test a pack / The operator's workspace / Define the understanding. Then prove it with examples. | Build the pack, then prove it / Build the pack from the customer's material. Then run their example events and check the answers. |
| Review and hand off / Approval, activation and answer readiness are distinct. | Approve and hand off / Three separate steps: approve, put to work, confirm it answers well |
| Provide evidence | Add the customer's material |
| Review proposals | Review what the assistant proposed |
| Define answers | Write the questions and the right answers |
| Run examples | Run the example events |
| Model / Planned change / Observed graph | The pack's diagram / What one event should write / What was actually stored |
| 1. Reviewed version | 1. Approve: freeze the pack with its proof |
| 2. Runtime activation | 2. Put to work: start the customer's service with this pack (an operations change, not shown) |
| 3. Answer readiness | 3. Confirm it answers: run the test questions on the customer's own graph (a later check) |

Workbench UI labels referred to by the narration stay as they are, except the ones already listed in `docs/workbench-storyboard.md`; the narration in the proposed script uses the labels as they are on screen today.

## E. Visual and footage changes

1. New 25-second opening still for chapter 0: two incident cards with the same number in different accounts, and the wrong three-incident answer beside the right two-incident answer. Label it "illustration".
2. Redraw overview screen 01 so the three boxes carry the incident example (event: "incident.opened, INC-1042, US, checkout"; graph: "INC-1042 (US) affects checkout (US)"; answer: "Which incidents affect US checkout? INC-1042, INC-1043").
3. Drop overview screen 02 from the cut; its content moves to the real pack-selection screen. If kept as a still, retitle per section C.
4. Scene 7: expand "Starting point (optional)" before narrating the starting point, so the checkbox and its sentence are on screen for at least five seconds.
5. Scenes 9, 10, 14, 15: hold the result table or timeline for five seconds of silence before the narrator interprets it; the current scene windows do not leave time to read.
6. Scene 6: focus a screen region that shows the answered identity and lifecycle decisions, not the "0 unanswered" heading.
7. Scene 11: frame the change classification label so the word "initial" is readable when the narrator mentions it.
8. Scene 17: decide whether the shot shows the saved story or the empty authoring form, and match the line (B11).
9. MP4 chapter titles: use the on-screen chapter names from section C.
10. Add a persistent corner caption on scenes 1 to 4 ("Illustration, not a product screen") and on scenes 5 and 16 ("Saved assistant history, not a live run"), so the honesty statements do not depend on the narration alone.

## F. Comprehension questions

1. **Northstar has incident INC-1042 in both the US and the EU account. What stops Engram merging them?** The pack's key for Incident includes the account, so "US, INC-1042" and "EU, INC-1042" are two different things. Misconception to prevent: Engram works it out from the data on its own.
2. **If the pack loads without errors, does Engram answer the customer's questions correctly?** No. Loading proves the pack is well formed. The answers are checked by running the example events and comparing each question's result with the reviewed expected answer; the report card shows the score. Misconception: a green "pack check" is the proof.
3. **Does choosing the core, memory and user packs for a customer keep that customer's data separate from others?** No. Pack choice decides what Engram understands. Separation comes from each customer having its own database and from callers' credentials; those are separate controls. Misconception: packs are a security setting.
4. **After approval, is the pack serving the customer?** No. Approval freezes the pack with its proof. Putting it to work means starting the customer's service with that pack configured, an operations change not shown in the video. Even then, each kind of question stays off until its test questions have passed on that customer's own graph. Misconception: approve equals live.
5. **The Northstar run and the PDLC story both passed on a Spanner sandbox. What does that show, and what does it not?** It shows the pack's rules, the storage path and the retrieval worked for those events and those questions on a real database. It does not show how a deployed service authenticates callers, how it behaves on the customer's real volume, or anything about other questions. The assistant screens were saved history, not a run performed during filming. Misconception: sandbox pass equals production proof.

## G. Claims not verified

- Whether the camera showed the "Starting point (optional)" section expanded in scene 7, and therefore whether the explicit-start checkbox was visible when narrated.
- What scene 17/22 actually framed: the saved story page or the empty "Create a new story" form.
- Whether the references story truly "starts with an empty sandbox graph" (its starting state was not read).
- The exact spoken timing per sentence; the figures in B16 derive from chapter lengths and word counts, not from listening.
- Whether every overview-screen diagram fits with the proposed longer subtitles at 1920 by 1080; only the rehearsal note says the current ones fit.
- The behaviour of a tenant service after a pack is approved, beyond what `docs/runbooks/tenant-api.md` states; no activation path exists to verify.

Verified against code or records: core always loaded; memory and user contents; dependency and name-conflict checks; lifecycle transition guard (`only_from`, used by Northstar's resolve rule); admission and contract checks before the ledger; provenance edges from graph nodes to events; explicit starting-point mode and its use on the filmed draft; Northstar F1 1.0 and PDLC 13/0/0/0 on Spanner with verified cleanup; the 409 evaluation gate; change classification always "initial" in the workbench; activation unavailable in the workbench and absent from the tenant API factory.

## Smallest set of changes before the next recording

1. Replace the six opening narrations in `record_opening.py` SCENES with chapters 0 to 3 of the proposed script, and drop or retitle the composition screen (B1, B2, B3).
2. Retitle the overview page sections and the three result boxes per section C, in particular the screen 05 and 06 subtitles (B2, B6).
3. Fix the two accuracy sentences: activation (B6) and change classification (B12); label intent readiness as rehearsed on a sandbox (B7).
4. Apply the vocabulary rules to every UI scene narration: assistant not model, customer not tenant, story not journey, material/citations/link/results instead of evidence (B4, B5, B14, B15).
5. Expand the starting-point section in scene 7 and add five-second holds on the four result scenes (B10, B16).
6. Resolve the scene 17 framing and line (B11), and set MP4 chapter titles to the on-screen names.

Everything else in this review can follow in a later cut without misleading a viewer.
