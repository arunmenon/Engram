# Engram operator walkthrough — narration and shot script

Terminology: A tenant is an isolated Engram environment with its own data and pack configuration. One customer may have several tenants, such as development and production. A tenant draft prepares configuration; it does not provision or activate a runtime.
Status: rehearsal draft, 2026-11-03. Companion to `engram-video-walkthrough-plan.md` and `workbench-storyboard.md`. This replaces neither the source pack nor its expected outcomes. The historical root-level `demo-video-script.md` is not the script for this recording.

Audience: a first-time internal operator. No graph, ontology or Engram knowledge assumed. Intended outcome: understand the architecture, distinguish a tenant draft from a deployed tenant, author a grounded pack, and interpret example-run evidence. Allow roughly 40–45 minutes including deliberate screen inspection; measure timing during rehearsal.

Production rules: start after authentication, keep developer tools closed, use synthetic material, and record each chapter separately. Label saved results with their run date and backend. Label edited-out model waits. Show only observed outcomes; the lines below describing results are conditional on the filmed run. Local synthesized narration is a production option, not a claim of a human narrator. Final recording follows the reviewed plan's script-review gate.

## 1. Why Engram needs a shared model — 3 minutes

Screen: the domain-agnostic overview in the study guide. Introduce no PDLC-specific entities until the shared foundation and composition are clear.

Narration:

“Organizations produce records in many systems. Applications and agents need more than a list of those records: they need to understand what each record describes, which records refer to the same thing, how things relate, and which evidence supports an answer.

“Engram retains events and builds connected, traceable context from them. An event is a report of something that happened. A graph is a view of things and their relationships. An ontology supplies explicit definitions for that view: the kinds of things, their identities, their relationships and, where relevant, their states.

“These definitions are critical because a connection can look plausible and still be wrong. Two records can share a name without describing the same thing. A mention can be weaker evidence than an explicit relationship. An old state can differ from the current state. Making those meanings explicit lets us inspect and test the interpretation instead of leaving it implicit in application code or prompts.

“A pack makes part of that model executable. It declares concepts, event contracts, mapping rules and retrieval configuration using capabilities supported by the engine. The engine supplies the reusable processing machinery. A pack describes how that machinery applies; it cannot invent a processing capability the engine does not have.

“Start with the common foundation. Core is required and defines shared concepts such as events and entities, together with reusable interfaces. The engine provides mechanisms for projection, provenance, lifecycle handling, source trust and retrieval. A domain must declare and configure the mechanisms it uses; their presence is not a guarantee that every model is correct.

“Memory and user are optional add-on packs. Memory adds concepts such as beliefs, goals and episodes. User adds profiles, preferences and related concepts. They extend the selected model when those capabilities are needed. They are not mandatory dependencies for every business domain.

“Domain packs then add the vocabulary and rules of a particular business area. We will examine two domain examples after this overview. Each uses the same engine and shared foundation, with its own identities, relationships and event mappings. Domain packs compose with optional add-ons; they do not replace the core or automatically inherit every add-on.

“The framework gives us a way to reuse the engine while making each domain's interpretation explicit, versioned and testable. An explicit model can still be wrong. That is why specifications, representative examples, operator review and evaluation are part of the workflow.

“First, let's see how the engine turns an event into queryable context. Then we will configure a tenant, inspect an existing domain pack, and use the assistant to build and test a model.”

Transition: shared foundation → event-to-answer flow → pack composition → tenant configuration → domain demonstrations. The two examples are demonstrations, not a claim that only two domain packs exist or that procurement is production-ready.

## 2. Follow one event — 5 minutes

Screen: selected sections of `docs/research/2026-10/walkthrough.html`: big picture, ingestion and retrieval. The guide is historical; verify visible labels against current code before capture. Avoid obsolete counts and claims that optional packs always load. Use an explicitly labelled explanatory diagram where the historical screen cannot be shown accurately.

Narration:

“An event is a report of something that happened. It identifies the subject, when the event occurred and the reported change. The pack determines which fields are required and how to interpret them.

“The ingestion path first checks whether the event is allowed and has the required shape. This matters because a missing identity field can connect evidence to the wrong thing. Rejected input must remain distinguishable from an accepted event.

“The ledger retains accepted event records. Processing then reads those events and applies the pack's mapping rules. Those rules describe which graph entities to create or update and which relationships to connect. This translation is called projection.

“The graph is the connected view we query. It is not a replacement for the original event. Evidence links let us trace a graph result back to the records that produced it. Separating retained events from the connected view also gives us a basis for rebuilding that view when the processing rules change, subject to the supported replay procedure.

“Retrieval takes a question and chooses starting entities and relationships to explore. The pack supplies domain-specific retrieval configuration. The engine returns relevant evidence under its limits and admission rules. This does not mean every question runs a language model, or that every connected record belongs in the answer.

“Storage is another boundary. The same processing concepts can be exercised with different adapters. A memory run is useful local evidence. A Spanner sandbox run exercises real database storage. Neither, on its own, proves every behavior of a deployed service.”

Pause and trace: event → admission → ledger → processing → graph → retrieval. Keep labels visible long enough to read.

## 3. What a pack contributes — 3 minutes

Screen: recap core and optional add-ons in the common/domain layer diagram. Only now introduce the pinned PDLC model and the synthetic Northstar incident model as two domain examples, followed by optional technical inspection.

Narration:

“An ontology describes the things in a domain and how they relate. A pack makes that model executable in Engram. It declares types and relationships, how to identify each thing, the events it accepts, rules that turn events into graph changes, and retrieval behavior.

“PDLC means product-development lifecycle. Its vocabulary includes software requirements, changes, reviews and tests. A different domain needs different concepts, but can use the same engine.

“Identity is especially important. A ticket number can repeat in another tracker. A change number can repeat in another repository. A key must include the scope that makes the identity meaningful. Otherwise the graph may combine unrelated records.

“The common layer provides shared foundations. Optional user and memory packs add their own capabilities; they are not automatically required for every domain. Pack dependencies and names must be checked together as a bundle.

“A lifecycle defines allowed state changes. A contract defines the event payload. A mapping defines the graph writes. These are related, but checking one does not prove the others are correct.”

## 4. Tenants, drafts and runtime tenants — 4 minutes

Screen: All tenants, then Tenant setup for the synthetic incident draft. Compare its purpose and environment with a prepared PDLC workspace. Show the persistent “Drafts stay separate” notice. Use a labelled tenant-binding diagram for runtime configuration.

Narration:

“This is the operator workbench. Each tenant card opens a draft workspace containing its inputs, pack proposal, questions and test evidence. The environment label helps us organize the work. Creating this card does not provision a production database or activate a tenant.

“A runtime tenant has a separate concern: authenticated credentials must route to the correct tenant configuration and storage. Its binding identifies the approved configuration and resources. The workbench prepares evidence for that operational handoff; it does not make that boundary disappear.

“The sandbox capacity panel describes databases reserved for examples. A run claims one exclusively, and cleanup returns it for reuse. These are not the tenant's live database. The number currently available is the number we can demonstrate, not a promise of unlimited capacity.”

## 5. Build a grounded ontology with the assistant — 8 minutes

Screen sequence: new synthetic incident draft → Tenant setup → What describes their world? → How Engram understands them. Use the existing reviewed incident exercise materials. Preserve existing successful workspaces; create a separate recording draft.

Narration while entering scope:

“Our next tenant wants to track checkout incidents across two accounts. We state the boundary: track incidents from opening to resolution; exclude on-call scheduling and automated remediation. Before a model call, we confirm what material may be sent and that these samples are synthetic or appropriately redacted.”

Narration during uploads:

“The process document explains the tenant's vocabulary and intended behavior. The event schema tells us which fields exist and what they mean. Sample events show concrete examples of those fields. We need all three perspectives: prose alone does not establish an executable mapping, and a few samples do not prove that an identifier is globally unique.

“We also supply the questions the tenant needs answered. Expected answers will be reviewed independently before execution. We do not let the observed result become its own definition of success.”

Action: start real-provider authoring. Show visible job progress; edit long waits with an on-screen notice. If using an existing proposal instead, label it saved authoring history and do not narrate a new call.

Narration on proposal:

“The assistant proposes a model from the supplied material. We inspect its explanation, the graph of types and relationships, and where the proposal came from. A citation is evidence for a proposal, not proof that the interpretation is correct.

“Here is a consequential decision: can incident 42 exist in both accounts? If it can, account identity must be part of the key. We answer in the tenant's terms, apply the answer, and inspect the resulting key. We also decide what happens when an update omits a title and whether a resolved incident can reopen.

“The operator remains responsible for those choices. An unresolved assumption stays visible. A repair that removes information requires review. The assistant's job is to make a draft and expose decisions, not to silently redefine the tenant's world.”

Action: inspect one sample's mapping under technical inspection. Contrast proposed graph change with actual stored results shown later. Do not read raw YAML line by line in the main story.

## 6. Questions, trust and proof — 4 minutes

Screen: Questions to answer → Test with examples.

Narration:

“We ask which incidents affect US checkout. We choose expected entities by their readable labels; the internal IDs are available for technical inspection. The expected answers belong to this saved evaluation artifact, so the operator form and export must agree.

“A starting entity tells retrieval where to begin. When we explicitly restrict the start to the selected service, discovery must not add a similarly named service from the other account. This controls the starting set. It does not create an account security boundary or prevent traversal through shared relationships.

“We specify which producer identities are trusted. Trust configuration affects which evidence can be admitted into answers; declaring it in a draft is not the same as provisioning production credentials.

“Before running, we review the expected graph outcomes. Then we run the actual examples and inspect the stored graph. The model diagram shows what is allowed. The planned change shows what a rule proposes for one event. The observed graph shows what was stored. These are different views.”

Conditional result narration: “This run reports [observed score] against [required threshold], on [reported backend]. Here are the expected and returned entities for this question. Here is the malformed event and its handling. Here is the cleanup outcome.”

Explain: “F1 compares expected and returned entities. Mean F1 on this small reviewed set is regression evidence, not a claim about every possible tenant question. A failed or errored question remains visible.”

## 7. Exercise the prepared PDLC stories — 6 minutes

Screen: implementation story, then planning, release and reference stories. Verify each run independently; do not carry one run's passing total into another story.

Narration:

“A prepared story packages ordered inputs and expected outcomes against a pinned pack. We can run it without asking an assistant to invent either the ontology or the answer.

“In the implementation story we follow the requirement through design, a ticket, a change, two reviews and test runs. At each step we can inspect the input, expected checks, handling and stored graph. A failed test followed by a successful run is different from erasing the failed test.

“The story also includes repeated local identifiers in unrelated scopes, exact retries and conflicting event identities. These are deliberate tests of identity and ledger behavior, not random extra data.

“The planning story examines design approval across revisions. The release story follows a change into deployment evidence. The reference story tests where a connection stops being trustworthy. Unsupported checks are labelled as unsupported; they are not passes.

“The question-focused stories test retrieval boundaries such as independent evidence, pagination, incomplete answers and rejected relationships. Graph-seeded tests can exercise retrieval without proving the ingestion path. We keep that distinction visible.”

Action: inspect one meaningful checkpoint in each story, one negative check, and one retrieval limit. Show full counts only from the current run. Historical memory failures may be shown as dated history, not asserted to remain current on Spanner.

## 7b. Pack lifecycle beyond the UI — 5 minutes

Screen: clearly marked technical appendix, using rehearsed CLI/API operations on disposable targets only. Exact commands and responses must be inserted after rehearsal; do not record invented terminal output.

Narration:

“The workbench is only part of the pack framework. The engine classifies a change and determines the corresponding version and operational procedure. An additive change, a mapping change and a breaking change have different consequences. Mapping changes may require replay; breaking changes may require a separate rebuilt graph and controlled cutover.

“A valid pack is not automatically ready to serve its intents. The approved evaluation set must be run and recorded against the relevant target graph. A fresh tenant can have its configuration activated while intent readiness remains pending until sufficient data exists. Activation success and answer readiness are separate outcomes.

“We show lifecycle operations here because the UI does not expose all of them. Declarations that load but have no runtime effect, and extraction or processing features outside this demonstration, must not be presented as working just because they appear in YAML.”

## 8. Create a new story with the assistant — 4 minutes

Screen: prepared story → Create a new story with the assistant → outline/decisions → generated variant → review → save → run.

Narration:

“Ontology authoring changes the model. Journey authoring creates examples that exercise a model. These are two different assistant workflows.

“Starting from this prepared PDLC story, we describe a variant: what happens, which outcomes should differ, and which boundaries must still hold. We review the outline before generating concrete events. IDs, ordering and references must be consistent; the expected outcomes must express our intent.

“We save the reviewed variant separately so the baseline stays available. Then we run it and inspect the results. If it fails, we determine whether the model, the event data or our expectation is wrong. We do not replace the expectation merely to get a green result.”

Rehearsal requirement: show an actual provider-authored variant and its result. Do not imply this PDLC journey flow is automatically available for every newly authored domain.

## 9. Review and handoff — 3 minutes

Screen: Approve and hand off; evidence identity and exports, if present. Do not activate a live tenant for filming.

Narration:

“The handoff is a specific version of the work: its inputs, pack, decisions, evaluation expectations and run evidence. If the model or inputs change, previous evidence can become stale and must be refreshed.

“Review answers three questions. Does the model represent the tenant's intended world? Do the examples support that interpretation? What operational work remains before the configuration can be used live?

“We have followed the complete path: evidence arrives as events, the pack turns it into connected knowledge, retrieval selects relevant context, and the workbench lets an operator build and test that behavior. The assistant accelerates the drafting; reviewed examples make the result inspectable.”

## Rehearsal ledger and remaining recording gates

- 2026-11-03: accessed the actual Chrome workbench with the existing local operator credential; no token captured.
- Landing page verified: four prepared PDLC stories, thirteen additional answer stories, saved synthetic tenant drafts, and a sandbox capacity panel reporting one slot.
- Implementation story verified before rerun: core 1.1.0 / pdlc 2.1.0, 23 deliveries and 111 declared checks. Prior displayed result was explicitly stale isolated-memory evidence.
- Fresh UI run failed with an authentication error (reference `52f9207cf9d8`). UI reported cleanup verified. This is failed rehearsal evidence, not a successful PDLC result.
- Local launcher reused its startup access token when constructing later clients. Updated the acceptance-only launcher to obtain a current token per client. No production authentication code changed.
- Retry through the same Chrome UI passed: 111 checks, zero failures, zero unsupported, zero errors; reported storage Spanner; cleanup verified; capacity returned to 1 of 1. Screenshot: `../output/video/rehearsal/pdlc-ui-passed.png`. This verifies this prepared story through the local UI/API and real storage, not deployed networking or all PDLC stories.
- Local speech synthesis and audio encoding were exercised: `../output/video/rehearsal/opening-voice-sample.m4a`, 22.55 seconds, macOS Daniel voice at 140 words/minute. This is a synthetic voice preview, not the final narration or an audio-quality signoff.
- Existing video plan contains historical statements now superseded by later Spanner evidence. Reconcile scene-by-scene before capture.
- Still required: current guide accuracy pass; remaining story and real-provider journey-authoring rehearsals; backend lifecycle command rehearsal; exact source/configuration manifest; complete shot timing; script review; voice/capture quality review; final recording, captions and visual/audio QA.
- Procurement is a separate workstream and is not a prerequisite for this video.

## Reviewer comprehension checks

1. If a draft card is saved, is a production tenant active? No: draft persistence is separate from runtime binding and activation.
2. If a sample field is unique in five events, is it a safe global key? Not necessarily: source identity scope must be established.
3. If one Spanner sandbox run passes, does that prove deployed tenant isolation? No: it establishes the scenarios and storage path exercised in that run.
4. If explicit seeds are used, can traversal still reach shared entities? Yes: strict starting selection is not a traversal security boundary.
5. If activation succeeds on an empty graph, must intent readiness already be green? No: target evaluation is a separate gate.

## Rehearsal update after scene runs

See `review/2026-11-03-video-rehearsal.md` for the detailed evidence and unresolved issues. Current verified UI results on Spanner: implementation 111 passed, planning 79 passed, references 13 passed, reviewed real-provider journey variant 15 passed; cleanup verified for each. Northstar's unchanged authored pack was revalidated and rerun with both questions at F1 1.0. The release scene failed tenant source-ID validation and must not be narrated as successful.

Chapter 8 now has a concrete sequence: outline format failure → corrected outline → review catches a missing unchanged checkpoint → regenerated proposal preserves all baseline events/checks → separate saved variant → 15 checks pass → delivery 8 visibly reports duplicate. Chapter 5 can show saved real-provider authoring history with that label; this rehearsal did not freshly generate the Northstar ontology.

Screen-and-voice preview: `../output/video/rehearsal/architecture-screen-voice-preview.mp4` (29 seconds, 1080p, real guide still frame and explicitly labelled synthetic narration). This is a production preview, not the finished walkthrough.

## Final rehearsal correction — release and evaluation gate

The release mismatch is resolved by sandbox-only synthetic source attribution, preserving the original event envelopes and frozen oracle. Its fresh UI result is **33 passed, 0 failed, 1 unsupported, 0 errors**, on Spanner with verified cleanup. The unsupported group covers original API/worker checks outside normalized replay. Keep that group visible in chapter 7; do not say all 34 checks passed.

Chapter 7b now uses `scripts/rehearse_workbench_lifecycle.py` on an exclusively leased sandbox: real artifact route returns 409 while PDLC evaluation is pending; the CLI's actual evaluate_graph routine evaluates all 11 frozen questions at mean F1 1.0 against 0.95 and records the result; the real route then returns 200. Cache refresh is explicit (TTL zero in the harness). Narrate it as an in-process route/CLI-routine integration rehearsal on durable Spanner, not a deployed API or the shell CLI entrypoint. Change-classification output is from candidate registries only, with no changes applied. Blue/green cutover stays a labelled architectural explanation; it was not performed for filming.

Use clearly labelled saved real-provider ontology-authoring history for chapter 5, followed by the fresh Northstar example replay. Chapter 8 supplies fresh model interaction, operator correction and execution. This avoids pretending an old proposal was generated during recording. The source/voice preview and this concrete script are the recording-review package under the video plan's step 4 gate.

## 2026-11-04 overview-cut revision: explain the framework before the UI

The short narrated review cut now opens with six dedicated screens in
`docs/engram-pack-framework-overview.html`; the exact recorded narration lives in
`SCENES` in `scripts/video/record_opening.py`. This supersedes the earlier
three-scene opening for this cut, not the longer feature walkthrough plan.

Audience remains a first-time operator. Teach events, graph, ontology and pack
before using them to explain the workbench. Sequence:

1. Why records need explicit meaning; why a reusable engine needs domain packs.
2. Required core, optional memory/user, domain packs and compatible tenant bundles.
3. What a domain pack defines, illustrated only now by an incident and service.
4. Admission → ledger → worker → graph → retrieval, following that same example.
5. Operator evidence → assistant proposals → reviewed questions → sandbox proof.
6. Journeys, reviewed versions, runtime activation and separate intent readiness.

Then show actual Northstar onboarding and results, the prepared PDLC reference
journey, saved assistant story authoring, and finally the Northstar handoff screen.
Moving handoff last makes the demonstrated story end with operational boundaries.
The opening diagrams are explicitly explanatory; they are not product screens or
execution evidence. The assistant material remains saved history. Reusing the
previously filmed Spanner runs does not claim new runs during this editorial
revision. No approval or activation is performed.

Grounding: current core/memory/user/PDLC pack declarations, the existing recorded
Northstar example, and the target-evaluation distinction already documented in
chapter 7. Do not imply add-ons are mandatory or that a pack supplies arbitrary
engine code. Do not conflate a selected bundle with tenant authentication.

Comprehension desk checks:
- Can another domain reuse the engine? Yes, through supported pack definitions;
  unsupported processing still requires engine development.
- Does a valid pack prove useful answers? No; reviewed questions and observed
  results are required to test the interpretation.
- Must an activated empty tenant have ready intents? No; evaluation on the target
  graph is a separate gate.
- Does the graph diagram in authoring show stored data? No; distinguish the model,
  a planned event change and the observed sandbox graph.
