# Tenant A: expanded journey discovery — 15 October 2026

Read-only discovery at `92a6053`, `feature/engram-memory-episodes`. Proposed controlled configuration: Core + User + Memory, pinned database `engram-assess-1010a-pdlc`. This inventory defines candidate proof, not permission to execute or a pilot-readiness claim. No database/API tests, code changes or issue mutations were performed. The current section of [the discovery brief](../2026-10-08-controlled-pilot-discovery-brief.md#current-pilot-scope-for-stakeholder-review--15-october-2026) owns scope.

## How to interpret the inventory

Every write below means authenticated `POST /v1/events`, with a fresh UUID, `occurred_at`, `session_id`, `agent_id`, `trace_id`, `payload_ref` and the stated `payload`; shorthand `obs(text)` means `event_type=observation.input,payload={"content":text}`. `end` means `system.session_end` with empty payload. These are concrete event templates, not fully frozen execution fixtures. Freeze UUIDs, timestamps, accepted source/producer mapping and expected IDs before any run. Envelope contract: [models.py:315](../../../../src/context_graph/domain/models.py#L315); existing submitted prose examples: [engram_user_attachment_demo.py:298](../../../../scripts/engram_user_attachment_demo.py#L298).

`Q(intent, question, owner, session)` means `POST /v1/query/subgraph` with `query`, explicit `intent`, `agent_id=owner`, `session_id=session`, and a recorded answer budget. This returns an evidence subgraph; the human question does not promise a generated conversational answer or unrestricted language understanding. Query contract: [models.py:686](../../../../src/context_graph/domain/models.py#L686), [query.py:1](../../../../src/context_graph/api/routes/query.py#L1). Compare a separate natural-language-only query where usefulness matters; do not let exact seeds conceal discovery failure.

Priorities: **P0** required before claiming the selected personal-memory pilot works; **P1** diversity/usefulness proof; **P2** bounded exploration or product decision. Verdicts: **VR** = verified representative, with existing bounded evidence but still needs frozen pilot replay; **NP** = current contract requires new pilot proof; **G** = gap in demonstrated capability; **PD** = product decision before making a promise. Neither VR nor NP means a new scenario has passed.

All five shared loops must be launched, observed and drained. Worker notation below:

- **U**: graph projection writes common Events; session extraction performs core Entity and selected User extraction; enrichment annotates Events; consolidation produces eligible Summary/Episode snapshots; pack extraction is a no-op because these selected packs define no matching prose extraction profiles. No PDLC output is enabled.
- **M**: projection additionally applies explicit Memory action transaction/state/evidence; session extraction only has applicable work at its configured ordinary-turn/session-end triggers and may extract quoted User facts, but must not be credited with producing Beliefs/Goals; enrichment/consolidation apply as above; pack extraction remains no-op.
- **R**: rejected event must reach none of the workers; earlier accepted events still follow U/M. Acknowledgement alone never proves a worker created an artifact.

These worker contracts are grounded in [extraction.py:95](../../../../src/context_graph/worker/extraction.py#L95), [pack_extraction.py:133](../../../../src/context_graph/worker/pack_extraction.py#L133), [enrichment.py:32](../../../../src/context_graph/worker/enrichment.py#L32), [consolidation.py:125](../../../../src/context_graph/worker/consolidation.py#L125), and [Memory event handlers](../../../../src/context_graph/domain/memory_actions.py#L24). Enrichment keywords come from event type/tool, not smart understanding of the prose. Importance may subsequently change through consolidation; optional embeddings require declared provider configuration.

Common prerequisites (**B**): preserved retained dataset/owner/epoch, selected commit/packs and launch path, public authenticated tenant route, trusted producer and owner mapping, real provider credentials/cost limit for prose and Summary quality, recorded consolidation cadence/threshold, processing-completion criteria, bounded diagnostics, explicit roles. Direct User APIs currently require admin: choose an appropriate supported access route or treat the access requirement as a blocker; do not silently grant admin for the demo. `agent_id` is logical owner identity, not authenticated human identity. The APIs/workers from prior verification are stopped. All journeys inherit B.

Evidence anchors used below:

- **UA**: [User acceptance/implementation](../user-attachment-verification.md#scope-and-acceptance), [accepted results](../user-attachment-verification.md#accepted-execution-results). Real model proved profile/preference/Rust interest; correction and interruption isolated storage/worker semantics with frozen provider outputs.
- **ME**: [Episode semantics and bounds](../memory-episodes-verification.md#what-changed-and-why), [verification boundaries](../memory-episodes-verification.md#verification-boundaries).
- **MG**: [Belief/Goal contracts and accepted evidence](../memory-episodes-verification.md#beliefgoal-continuation--verified-bounded-implementation), [final walkthrough](../memory-episodes-verification.md#final-results-and-stakeholder-walkthrough). Structured producer assertions, not prose inference.
- **PC**: [composition cases](../pack-combination-verification.md#concrete-journeys-and-passfail-checks), [accepted rerun](../pack-combination-verification.md#accepted-rerun-results).
- **TI**: [public two-tenant results](../tenant-isolation-verification.md#live-results-and-stakeholder-walkthrough), [limits](../tenant-isolation-verification.md#limits-of-this-checkpoint). Frozen provider output proves routing/isolation, not model quality.

## Personalization across distinct application contexts

### A-01 — Code assistant onboarding with attributable interests

Alice starts a coding assistant session `a-code`: `obs("My name is Alice. I am a software engineer. I prefer short answers. I am interested in Rust language development.")`, then `end`.

Ask **“What answer style and interests should this assistant use for Alice, and where did they come from?”** via `Q(personalize,…,alice,a-code)` and authorized `GET /v1/users/user:alice/profile`, `/preferences`, `/interests`. Expect canonical `profile:user:alice`, supported preference and Rust interest, owner edges and actual quoted observation evidence; the empty end Event is not the fact source and internal extraction receipts stay private. Workers **U**. **P0 / VR**, UA01–02 and PC; prerequisite: real configured model and independently inspected frozen receipt/source quotations. Exact free-text extraction beyond that representative statement is not guaranteed.

### A-02 — Incident assistant and review assistant retain different styles

In `a-oncall`, Alice says “For incident support, I prefer terse numbered actions.” In `a-review`, she says “For design reviews, I prefer detailed explanations.” End both. These provide materially different application contexts, rather than one global preference.

Ask **“How does Alice want incident instructions versus design-review explanations?”** via owner-specific `/preferences` plus `Q(personalize,…,alice,a-oncall)` and a separate query for `a-review`. Freeze expected category/key/context/scope from the accepted extraction contract; prove which context filters personalization actually applies. Expect distinct attributable preferences with neither silently superseding the other; do not claim that the session parameter automatically enforces every Preference scope/context rule. Workers **U**. **P0 / NP**, User schema [user.pack.yaml:35](../../../../src/context_graph/ontology/packs/user.pack.yaml#L35), UA05. Prerequisite: explicit application-to-context mapping and separate real-model interpretation proof; contextual retrieval selection is a required pilot assertion, not inherited from storing two preferences.

### A-03 — Correct a support preference without changing review behavior

Continue A-02 with `obs("For incident support, I no longer prefer terse numbered actions; use a short explanatory paragraph.")`, then `end`. The producer/test specification must name the exact previous owner/category/key/scope/context target; arbitrary corrective prose alone is not an established reliable target selector.

Ask **“What is Alice's incident preference now, what changed, and does review guidance remain?”** Current `/preferences` and `Q(personalize,…)` must return the intended successor and unchanged review preference. Use exact predecessor/successor graph evidence/audit for history: the specialized active-only endpoint is not a general history API. Expect SUPERSEDES, original support retained, replacement supported only by correction observation; no replay in later windows. Workers **U**. **P0 / VR** for controlled correction semantics, **NP** for this real prose, UA05. Prerequisite: freeze target identity and choose history retrieval contract rather than invent an endpoint.

### A-04 — Learning coach distinguishes interest from demonstrated skill

Alice tells a learning coach `a-learn`: “I am interested in Rust, but I have only just begun learning it. I have used Python professionally for five years.” End the session.

Ask **“What does Alice want to learn, and what skills has she actually declared?”** via `/interests`, `/skills`, and `Q(personalize,…,alice,a-learn)`. Expect Rust interest and only model-supported Skill/assessment values with exact quotations. Rust interest must not be recast as expert proficiency; Python proficiency is an attributed model extraction, not a tested credential. Owner-qualified Skill identities must not be borrowed from another person's assessment. Workers **U**. **P1 / NP**, [User Skill/interest schema](../../../../src/context_graph/ontology/packs/user.pack.yaml#L58), UA controlled Python Skill case. Prerequisite: real-model oracle covering uncertainty/absence; prior skill replay proof does not establish this interpretation quality.

### A-05 — Research assistant disambiguates Mercury the project and planet

In `a-research`, Alice says “Mercury is our internal research project. Separately, I am reading about the planet Mercury.” Add “The Mercury project report is due Friday,” then end.

Ask **“Which Mercury references concern the project, and which concern astronomy?”** via `Q(general,…,alice,a-research)` with a separate exact Event-seeded evidence query. Expect canonical Entity targets to match actual resolved IDs and each REFERENCES/source link to the correct Event. Never silently fuse unrelated senses merely because names coincide. Workers **U**. **P1 / G** for reliable semantic disambiguation; PC's canonical ID remediation proves preservation of a resolved ID, not universal word-sense resolution. Prerequisite: declare desired Entity labels/identity policy and inspect real extraction/resolution; an honest ambiguous/missing answer is preferable to inventing certainty.

### A-06 — Same interests, different people, positive controls and attribution trap

Bob's learning session says “My name is Bob. I am interested in Rust. I prefer detailed examples.” Alice's A-01 remains present. End Bob's session.

Ask **“What does Bob prefer?”** with Bob's positive `/profile`, `/preferences`, `/interests` and `Q(personalize,…,bob,b-learn)`; then **“What does Alice prefer?”** with Alice's owner-scoped query. Expect separate profiles/preferences and owner-qualified Skills if any, shared topic Entity only where appropriate, and no Bob facts in Alice's personalized result. Workers **U**. **P0 / VR**, UA06, MG ownership. Prerequisite: explicit trusted person-to-agent mapping. This is logical within-tenant scoping, not hierarchy authorization or proof that Alice cannot submit Bob's identifier.

Add a separately labeled real-model attribution probe under **Alice's** `agent_id`: “Bob likes long explanations; I prefer short replies.” Ask **“Whose preference did each quote describe?”** and inspect exact User output/source. User ownership follows the triggering agent (`user:{agent_id}` in [extraction.py:354](../../../../src/context_graph/worker/extraction.py#L354)); mentioning Bob does not automatically route a preference to Bob's profile. **NP/G** for reliably excluding third-party statements from Alice's extracted preferences. Never count this as passing merely because all new outputs were mechanically attached to Alice. Keep shared Core Entity mentions separate from owner-qualified User facts; freeze an attribution rubric before this probe.

## Session recall and temporal evidence

### A-07 — Coding assistant resumes yesterday's investigation

Session `a-debug-1`: “I traced the intermittent timeout to the cache client; next I will inspect connection reuse.” End. Next day, distinct `a-debug-2`: “Resume yesterday's timeout investigation.” Do not encode the earlier prose as a structured Goal implicitly.

Ask **“What did Alice establish in yesterday's investigation?”** via `Q(when,…,alice,a-debug-1)` and separately test the unseeded resume question in `a-debug-2`. The explicit old-session query should return its supported Events/Summary/Episode; the new session must not acquire a session-scoped Memory merely because text asks to resume. Workers **U**. **P1 / NP** for old-session recall; **G/PD** for automatic discovery of the right earlier session. Prerequisites: application retains/chooses prior session ID or supplies an explicit supported retrieval strategy. Do not turn a same-owner cross-session expectation into an undocumented exhaustive-history promise. ME and [context route](../../../../src/context_graph/api/routes/context.py#L1).

### A-08 — Journal separates morning and afternoon episodes

Personal work journal `a-day`: observations at 09:00 (“Plan lab measurements”), 09:05 (“Calibrate sensor”), and 09:40 (“Review results”). Use exact occurrence times, then allow scheduled consolidation.

Ask **“What happened in the morning work blocks?”** through `Q(when,…,alice,a-day)`. Expect complete two-member and one-member Episode snapshots separated by a 35-minute gap, exact CONTAINS/DERIVED_FROM and Summary evidence; do not interpret temporal grouping as inferred project relationships or a closed session boundary. Workers **U**. **P0 / VR**, ME. Prerequisite: record nondefault small-fixture cadence/threshold or supply enough events for defaults (six-hour interval, threshold 150 with count × 5 proxy); HTTP acceptance does not imply immediate Episode availability.

### A-09 — Offline mobile note bridges two historical blocks

After A-08 is consolidated, submit an observation **occurred at 09:20** (“Check calibration drift”) that arrived late from the mobile journal. Wait for the next eligible consolidation.

Ask **“How does the late note change the timeline, and what earlier grouping was retained?”** via `Q(when,…,alice,a-day)`. Expect a new four-member membership snapshot plus preserved prior two-member and one-member snapshots, accurate timestamps and evidence. No deletion of old snapshots, duplicate membership within a snapshot, or claim that all returned Episodes form one nonoverlapping latest partition. Workers **U**. **P0 / VR**, ME late-bridge walkthrough. Prerequisite: freeze pre/post member sets and distinguish original event time from delivery time.

### A-10 — Two unrelated sessions have similar wording

Alice's `a-lab` and `a-home` both contain “Check the temperature sensor,” but their actual observations and times differ; each receives enough events to consolidate.

Ask **“What happened in the lab session?”** and **“What happened in the home session?”** via separate `Q(when,…)`/`GET /v1/context/{session_id}` positive controls. Expect exact own-session Episode/Summary/Event sets, with no other session's members. Similar text must not replace membership evidence. Workers **U**. **P0 / VR** for Episode session boundaries, ME; **NP** for session context usefulness. Prerequisite: distinct frozen IDs and a positive result for both sessions; a negative-only test is insufficient.

### A-11 — Summary is useful prose with inspectable evidence

Research notebook `a-study`: observations record a hypothesis, a measurement that challenges it, and a decision to retest. End and consolidate with the real configured Summary provider.

Ask **“What did the experiment show, and why are we retesting?”** via `Q(when,…,alice,a-study)` and source Event reads seeded by returned IDs. Expect actual stored Summary, exact supporting Events and complete Episode snapshot; score whether prose preserves the contradiction and uncertainty separately from membership correctness. No invented measurement, causal conclusion, Belief or Goal. Workers **U**. **P1 / NP**, ME proves real Summary path but not quality on this richer example. Prerequisite: qualitative rubric and exact input evidence; scripted Summary output cannot stand in for this journey.

## Beliefs: attributed epistemics rather than automatic truth

### A-12 — Work journal records a reported assumption

An authorized journal producer sends `memory.belief.stated` with `{key:"focus-time",scope:"session",belief_text:"Alice reports that late meetings reduce her focused coding time",category:"user_model",confidence:0.7}` in `a-journal`.

Ask **“What assumption did Alice report, with what confidence and evidence?”** via `Q(beliefs,…,alice,a-journal)`. Expect typed Belief, stated origin, exact text/category/confidence, initial confirmation_count 1, revision 0 and creation Event provenance. The report remains Alice's attributed assumption; confidence is declared contract data. Workers **M**. **P1 / VR** for structured stated semantics, **NP** for this application, MG and [stated contract](../../../../src/context_graph/ontology/packs/memory.pack.yaml#L182). Prerequisite: trusted producer/source attribution.

### A-13 — Research producer proposes an uncertain world-model belief

Producer explicitly sends `memory.belief.inferred` `{key:"sensor-drift",belief_text:"Sensor drift may explain the anomalous reading",category:"world_model",confidence:0.6}`; also retain the underlying notebook prose as separate observations. The producer is responsible for asserting this proposal; Engram does not infer it autonomously.

Ask **“Which explanations are only inferred proposals?”** with `Q(beliefs,…,alice,a-study)`. Expect inferred origin and zero confirmations; confidence exactly 0.6, not an implication of evidence count. The action's source Event is proof of the proposal; additional links to notebook observations require an explicit supported relationship, not narrative invention. Workers **M**. **P0 / VR**, MG; [memory_actions.py:112](../../../../src/context_graph/domain/memory_actions.py#L112). Prerequisite: distinguish producer reasoning from actual Engram source graph. Confidence over 0.8 must be rejected (A-23).

### A-14 — Deliberate confirmation and stale competing confirmation

For A-13, send `memory.belief.confirmed {key:"sensor-drift",expected_revision:0}`; replay the same Event unchanged. Then send two distinct confirmations both naming the resulting revision 1, using the frozen concurrency schedule if simultaneous handling is claimed.

Ask **“How many distinct confirmations actually applied, and which attempt conflicted?”** via `Q(beliefs,…)` plus processing-status/receipt audit. Expect zero-to-one support on first confirmation, no increment on duplicate, exactly one winning revision-one update, losing Event conflict disposition and no losing support edge. HTTP 201 alone is not an applied confirmation. Workers **M**. **P0 / VR**, MG parallel-consumer proof. Prerequisite: explicit revision oracle and exact expected DLQ/conflict records; general races or observed Spanner aborts are not inherited claims.

### A-15 — Revise a travel assumption without declaring contradiction

Travel-planning producer states `{key:"arrival-v1",belief_text:"Train expected at 18:00",category:"world_model",confidence:0.7}`, then states replacement `arrival-v2` with text “Train expected at 18:15.” Submit `memory.belief.corrected {key:"arrival-v1",replacement_key:"arrival-v2",expected_revision:0,contradicts:false}` in the same owner/session.

Ask **“What is the current arrival assumption and how did it change?”** via current `Q(beliefs,…)` and historical `Q(when,…)`. Expect predecessor omitted from current recall but preserved in history, SUPERSEDES and exact source receipts; no CONTRADICTS when false. A second bounded fixture may explicitly set true and require that edge. Workers **M**. **P0 / VR**, MG correction, [memory_actions.py:290](../../../../src/context_graph/domain/memory_actions.py#L290). Prerequisite: existing current replacement in identical owner/scope, exact revisions and explicit epistemic intent. Do not infer contradiction from similar wording.

### A-16 — Agent-wide capability assumption versus session-local hypothesis

In `a-device-1`, explicitly state agent-scoped capability Belief `{key:"offline-mode",scope:"agent",belief_text:"The client can retain notes offline",category:"capability",confidence:0.8}` and a default session-scoped `local-network` hypothesis. Query from distinct `a-device-2`, then Bob's session.

Ask **“Which of Alice's assumptions apply across sessions?”** via `Q(beliefs,…,alice,a-device-2)`; positively read local hypothesis in its original session, then Bob's own controls. Expect agent-scoped Belief across Alice's sessions, local one only in its source session, neither in Bob's Memory context. Workers **M**. **P0 / VR**, MG ownership, [memory_identity](../../../../src/context_graph/domain/memory_actions.py#L44), [retrieval ownership](../../../../src/context_graph/retrieval/memory_state.py#L20). Prerequisite: explicit agent mapping. This is a scope contract, not proof the client actually has that capability or human-level authorization.

## Goals: explicit commitments and alternatives

### A-17 — Study goal completes only on an explicit producer event

Learning producer creates `memory.goal.created {key:"chapter-3",description:"Complete chapter 3 exercises",priority:6}`. Send prose “The practice quiz passed” without a Memory lifecycle event; read the Goal. Then send `memory.goal.completed {key:"chapter-3",expected_revision:0}`.

Ask **“Is chapter 3 complete, and which event says so?”** via `Q(goals,…,alice,a-learn)` before and after. Expect active after quiz prose, completed only after explicit command, revision advanced and exact creation/lifecycle source evidence. No test-success-to-Goal inference. Workers **M**, prose follows **U**. **P0 / VR** for lifecycle semantics, **NP** for this combined story, MG. Prerequisite: authorized producer is responsible for the completion assertion; no automatic learning assessment is promised.

### A-18 — Abandon a household task without claiming success

Personal task assistant creates `memory.goal.created {key:"repair-printer",description:"Repair the old printer",priority:3}`, then `memory.goal.abandoned {key:"repair-printer",expected_revision:0}` after the user's explicit choice.

Ask **“Which task was abandoned rather than completed?”** via `Q(goals,…,alice,a-home)`. Expect status abandoned, two exact source Events and no completed status or fabricated success evidence; completion and abandonment are alternatives, not interchangeable terminal states. Workers **M**. **P1 / VR**, MG. Prerequisite: the chosen public read must visibly return abandoned status and evidence; freeze exact answer assertions rather than merely counting Goal nodes.

### A-19 — Replace a plan while retaining the rejected alternative

Travel producer creates active Goals `drive` (“Drive to the conference”) and `train` (“Take the train to the conference”). Send `memory.goal.superseded {key:"drive",replacement_key:"train",expected_revision:0}`. Do not silently choose a plan from a preference statement.

Ask **“What is the selected travel plan, and which plan did it replace?”** via `Q(goals,…)` plus historical `Q(when,…)`. Expect drive superseded, train still active, exact SUPERSEDES and lifecycle evidence; current recall omits predecessor while history preserves it. No automatic ranking, mutual-exclusion planning or goal optimization. Workers **M**. **P1 / VR**, MG. Prerequisite: replacement already active under same owner/scope and explicit producer decision; [supersession contract](../../../../src/context_graph/ontology/packs/memory.pack.yaml#L375).

### A-20 — A personal commitment can cross sessions without changing others

Create Alice's `scope:"agent"` Goal `reading-week` (“Read three papers this week”) in `a-study-1`. Read from `a-study-2`; create Bob's same key with different description and read Bob positively. Complete Alice's agent-scoped Goal from the second session with explicit scope and expected revision 0.

Ask **“What remains of Alice's weekly commitment, and what does Bob still intend?”** via separate `Q(goals,…)` queries. Expect Alice's single cross-session identity becomes completed, Bob's stays active with his own source, no cross-owner lifecycle mutation. Workers **M**. **P0 / NP** for this cross-session lifecycle combination, supported by MG ownership/lifecycle and identity code. Prerequisite: freeze owner/scope keys and trusted producer authority; logical scope must not be advertised as an authenticated human permission guarantee.

## Absence, failures and bounded answers

### A-21 — Silence is not a preference or a hidden commitment

New owner Carol says “I opened the editor and read the report.” End the session. No name/skill/preference or explicit Memory goal/belief statement is provided. A separate user supplies a real preference as positive control.

Ask **“Does Carol prefer terse answers, and what goal has she committed to?”** via `/preferences` and `Q(personalize,…)`/`Q(goals,…,carol,c-read)`. Expect no unsupported preference/Goal; only actual evidence and an honest empty/missing result. Do not insist profile Entity creation is absent if the implementation materializes a minimal owner. Workers **U**. **P0 / NP**, User extraction and explicit MG contracts. Prerequisite: real-model negative-evidence rubric; an empty response due to broken processing must be distinguished from valid absence through the positive control and completed-worker evidence.

### A-22 — Parent arrives late, versus never arrives

In a task assistant session, admit `memory.belief.confirmed {key:"delivery-window",expected_revision:0}` before its stated parent. Observe pending status, then admit `memory.belief.stated` with the same key, required text/category/confidence and owner/session. A separate missing key never receives a parent within the configured retry bound.

Ask **“Was the confirmation applied or is its source still unresolved?”** via `Q(beliefs,…)` and recorded worker diagnostics. Expect eventual exact parent-plus-confirmation evidence after arrival; exhausted missing reference dead-letters without partial Belief or invented support. Workers **M**. **P0 / VR**, MG missing-parent proof. Prerequisite: frozen retry schedule/bounds and named source IDs; this is bounded reference recovery, not a general crash/network recovery guarantee.

### A-23 — Duplicate identity, conflicting content, malformed or disabled input

Replay A-01's exact Event; change its payload under the same UUID; submit inferred Belief confidence 0.9, an update missing expected_revision, and an envelope missing session_id. Submit a PDLC typed event while A's PDLC pack is disabled. Preserve distinct before/after fingerprints.

Ask **“What accepted facts changed after these attempts?”** via exact Event-seeded `Q(general,…)` and relevant User/Memory queries. Expect duplicate with no support/count mutation; changed identity content refused as conflict; invalid/disabled inputs 422 and no ledger/artifacts. No attempt to turn declared `user.preference.*` names into a new typed User producer: User remains session-extraction driven. Workers **U/M** only for originally accepted input; **R** for refusals. **P0 / VR**, UA/PC/TI and [event ingestion contract](../../../../src/context_graph/api/routes/events.py#L1). Prerequisite: freeze actual public response/status semantics and record rejected IDs; disabled-control cases must not change tenant packs or reset retained data.

### A-24 — Dense history yields an honest bounded answer

Use a declared dense notebook with more than ten eligible Episode snapshots and enough Belief/Goal history to exceed a deliberately small answer budget. Ask once with `max_nodes:1`, then an ordinary recorded budget; do not assume cursor continuation can advance the Episode candidate window.

Ask **“Show everything Alice recorded and changed in this notebook.”** via `Q(when,…,alice,a-dense)` and separate `beliefs`/`goals` reads. Expect explicit truncation, respected node limit, no dangling edges or fabricated completeness; incomplete/invalid snapshots remain suppressed. Episode retrieval considers at most ten snapshots/500 aggregate member references, and Memory state candidate selection is also bounded. Workers **U/M** depending on submitted records. **P0 / VR** for small-budget behavior; **NP/G** for this dense history and exhaustive usefulness, ME/MG and [memory_state.py:169](../../../../src/context_graph/retrieval/memory_state.py#L169). Prerequisite: freeze expected candidate sets and diagnostics; exhaustive historical search/pagination is a product decision, not an accepted feature.

### A-25 — Repeated implicit preference and a paraphrase probe

In a code-review assistant session, Alice says “Could you keep that to three bullets?” and later “A quick list is easier for me to scan.” In the next session she asks a factual question without restating the format. End both sessions with the real configured extraction model; keep both actual quotations and any frozen output receipts.

Ask **“What evidence suggests Alice likes compact lists?”** via `Q(personalize,…,alice,a-review-next)` and authorized `/preferences`; separately ask the same question as “How should I format Alice's review feedback?” without an intent override. Inspect whether the model emitted one coherent implicit preference, multiple separately supported preferences, or none, and whether unseeded retrieval finds it. Counts must reflect distinct quoted accepted Events rather than wording frequency or reprocessing windows. Do not require semantic deduplication of independently worded model outputs, or promote a one-off request to a durable global preference without a declared rubric. Workers **U**. **P1 / NP** for real-model interpretation and paraphrase usefulness, **PD** for intended persistence/scope. User schema permits implicit/inferred preference sources, but UA's explicit short-answer example does not prove this behavior. Prerequisite: freeze the intended annotation rubric and score model extraction separately from evidence/count correctness and retrieval sufficiency.

An optional serialization variant may retain Unicode names/quoted text exactly in accepted Events and retrieved evidence. That is distinct from multilingual extraction or paraphrase quality, which needs its own declared model-quality oracle. No audio/image ingestion or upload capability is assumed.

## Coverage decisions before a detailed pilot specification

This yields 25 stable journeys across coding support, incident response, design review, learning, research, journaling, travel and household tasks. It deliberately separates real-model interpretation (A-01–07, A-11, A-21, A-25) from explicit producer assertions (A-12–20), deterministic time/membership (A-08–10), and operational/absence controls (A-22–24). Coverage includes recall, multi-session evidence, temporal reasoning inputs, updates and abstention/absence, plus diverse long-lived application contexts. These are coverage axes, not an Engram benchmark claim. Engram supplies graph/context: assess whether returned evidence suffices for a downstream answer separately from whether another model reasons correctly over it. Empty or incomplete graph results do not establish a built-in conversational “I don't know” response.

Priorities order specification/execution work; they do not authorize silently omitting the P1/P2 diversity or unresolved product decisions when reporting spectrum coverage.

The largest proof gaps are contextual personalization selection, automatic discovery of the relevant earlier session, semantic Entity ambiguity, rich real-model negative/uncertainty handling, and useful dense-history retrieval. Existing evidence does not justify promising these automatically. Freeze supported exact APIs and owner/context mapping, test the actual model and keep retrieval quality distinct from storage/lifecycle correctness. Preference history requires a concrete supported graph/evidence read; active `/preferences` alone does not meet “what changed?”.

For every required execution scenario, retain submitted bodies and HTTP responses, accepted ledger documents, worker completion/pending/failure state, exact expected/actual typed nodes/edges/properties, creation and lifecycle sources, forbidden-output checks, and independent decoded storage audit. A receipt may freeze model output, but neither a receipt nor a successful acknowledgement establishes useful retrieval. Real-model failures remain evidence. Keep public role/read usability and the existing Cloud Monitoring 403 readiness limitation visible through the shared operational plan.

No new hierarchy policies, migrations, hot pack switching, ANN/load benchmark, autonomous Goal inference, automatic truth verification or authenticated-human identity guarantee is introduced. Tenant A's disabled PDLC/prose-pack-extraction paths must stay no-op; cross-tenant colliding-ID probes belong to the shared Tenant A/B isolation inventory, grounded in TI rather than duplicated here. Participant choice, supported applications, access duration and exact deployment topology remain product decisions.
