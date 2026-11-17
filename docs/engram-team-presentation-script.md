# Engram team presentation — speaker script and storyboard

Status: **draft for Fable and user review**, 2026-11-17. A 24-slide HTML/PDF draft (17 main slides plus seven appendices) is now at `output/presentation/engram-team-20261117/`, created after the user's explicit instruction to work on the presentation. No voice track or new recording is claimed. Follows the four-act revision with an early architecture overview. M6-1 is independently closed; M6-2 wording is corrected. Real-operator sessions and earlier lows remain open. Two-Ann and one-Ann frames still need capture/rehearsal on the recording build; the draft uses a labelled explanatory summary.

## Production rules

Audience: mixed engineering, product and domain teams; no Engram knowledge assumed. Speak the “Narration” paragraphs; production notes and footers are not extra narration unless identified. Do not read code names or status tables aloud exhaustively.

Use the same small strip throughout: **events → pack rules → stored graph → answers**. Highlight the current step. Authoring sits above the strip; it changes a draft of the rules rather than directly writing live tenant data. Introduce the strip progressively on slide 2, so the viewer does not meet every term at once.

Use text labels, not colour alone: **Operator supplied / Agent proposed / Engine checked / Test observed**. Use restrained colours consistently. Each slide has a positive headline and a compact “Shows / Does not show” footer. Important limits also appear in narration at the moment a viewer could misunderstand them.

Before/after graphics must name their evidence level. The initial two Anns come from a planned sample projection; the final one Ann is observed in a recorded graph. Do not silently equate them. Never describe an observed outcome as a pre-reviewed assertion.

The draft has approximately 2,700 spoken words: about 20–23 minutes at 120–135 words per minute. Target 35–40 minutes including non-narrated demonstration actions, audience questions and reading pauses. Clip narration is already included in this word count and must not be added a second time. This is not a measured runtime. Rehearse the actual transcript and clips before promising a duration; do not pad prose or accelerate narration to force the estimate. Clip narration below is part of the transcript, not a second voice track to play over it.

## Act 1 — The problem

### 1. Why did Ann become two people?

**Audience question:** Why do these rules matter?
**Takeaway:** A wrong identity rule can split one person's records.
**Visual:** Two synthetic CRM events, same contact ID C1, different email. Then two separately labelled panes: “Baseline — planned sample projection: two contacts” and “Revised pack — recorded graph: one contact.” Capture IDs/emails legibly; do not show the final pane until the relevant line.

**Narration**

“Ann changes her email address. Our CRM still knows she is the same person: both events carry the same permanent contact identifier. But imagine the rule reading those events uses email to identify a person. The new address then looks like a new contact.

That is the problem in this example. In the baseline's planned result, Ann appears twice. After a reviewed change to the rule, a recorded test run shows one contact for Ann.

The events did not need better wording. We needed a clearer rule for what makes someone the same person over time.

Engram gives us a way to make those rules explicit, connect the resulting records, and inspect what happened. The workbench helps an operator create and test those rules with an agent. Today, we will follow that loop, including the places where the operator must decide and the places where a test does not prove as much as its score might suggest.”

**Footer:** Shows: synthetic CRM example and recorded guided revision. Does not show: autonomous diagnosis or a dedicated identity-change test.
**Source:** M6 final `copies-start.json`, `live-revision-result.json`, `live-flow-sandbox.json`; Fable M6 review.
**Transition:** “First, here is the whole system in one picture.”

### 2. What does Engram do with events?

**Audience question:** Where do packs and the engine fit?
**Takeaway:** Packs describe supported rules; the engine applies them.
**Visual:** Build the strip one step at a time. Beneath “pack rules,” reveal core, optional memory/user, and a domain pack. Keep the deeper worker/API/storage diagram for slide 15.

**Narration**

“An event says that something happened. A contact was added, a request was approved, or a change was reviewed. The pack says how to read that event: which record it belongs to, which details to update, and which relationships or states it may change.

The engine applies those supported rules. It stores records and their connections in a graph, which retrieval can use to find context for a question. That is what we mean here by a context graph. Source links let us inspect which events supported a record.

Every configuration includes core, the shared foundation. Optional memory and user packs declare additional concepts, such as beliefs and goals, or preferences and skills. A domain pack adds the rules for a particular business area. Selecting a pack does not make every declared feature automatically executable; the engine must support the behavior.

Graph-based retrieval and temporal agent-memory research provide useful context for this design. The appendix names the papers and the differences. We are not claiming their algorithms or benchmark results as Engram's results.

Keep this picture in mind. The workbench helps us prepare and test the rules above this pipeline.”

**Footer:** Shows: design overview. Does not show: deployment, universal extraction or research-benchmark equivalence.
**Sources:** core/memory/user pack declarations; workbench engine/authoring/sandbox; research appendix A.
**Act-break question:** “What would you need to know to decide whether two records represent the same thing?” Allow an answer; connect it to the source system's identity rule.

## Act 2 — One full loop with Ann

### 3. Start a tenant draft

**Takeaway:** Define whose rules and data we are working with before using the agent.
**Visual:** Tenant setup screen. Highlight name/environment, scope, data handling, then producer trust. Use an identified CRM copy; do not create or change a live tenant for filming.

**Narration**

“A tenant is the organization or workspace whose configuration and data we are managing. Here, we start a draft for that tenant. The name and environment help us recognize the work, but creating this card does not deploy a service or create a tenant database.

We first describe the scope. For this example, we want accounts, contacts and deals, and we want a contact's history to stay together when email changes.

We also decide whether this material may be sent to the agent's external service and confirm that sensitive details have been reviewed. That permission is separate from producer trust. Permission controls whether we may send material to the agent. Producer trust identifies which declared event sources this test treats as trusted.

The draft can select available packs and optional add-ons. Core stays underneath. We will return to runtime tenant boundaries later. For now, every action is preparing a draft, with no production activation.”

**Footer:** Shows: tenant draft setup. Does not show: provisioning or deployed isolation.
**Sources:** workbench Content/capabilities/catalog; tenant API runbook.
**Transition:** “The next question is what we give the agent to work from.”

### 4. What does the operator supply?

**Takeaway:** Give rules, actual fields, examples and desired outcomes—not just a domain name.
**Visual:** Four rows using verbatim excerpts from the saved CRM sources: definition, contract, event history, reviewed questions. Keep full documents in optional detail.

**Narration**

“The operator brings four kinds of material into this example. First is a written definition: contacts keep their permanent CRM identifier when email changes. That tells us the intended business rule.

Second is the interface contract. It tells us which fields the source actually sends, including the contact identifier and email. Third is the event history. It contains Ann's original contact event and another event with her new email, so we can exercise the rule rather than discuss it only in prose.

Fourth are the questions and expected outcomes that make the pack useful. Those expectations need to come from reviewed business requirements. They must not simply be whatever the agent's proposed pack happens to produce.

Other domains may also need identity scope, allowed state changes, rules for missing fields and conflicting updates. You can add material in stages. Enough to sketch concepts is not necessarily enough to run a test or approve a package. The readiness checks make those distinctions visible.”

**Footer:** Shows: saved synthetic CRM source material. Does not show: globally representative samples or independently established business truth.
**Sources:** M6 final starting snapshot, source IDs `spec`, `schema`, `samples`; questions.
**Transition:** “Before generating rules, let us see what the sample data can tell us—and what it cannot.”

### 5. Inspect the data — Clip 1

**Takeaway:** Repeated identifiers need surrounding context.
**Visual/actions:** Explicit “Switching to procurement intake” card. Open source inventory; search 42; expand the repeated value to show east and west; pause at least five seconds. Show an absent search value and its empty state. End on the identity question, not on an invented procurement graph.

**Narration**

“This is a different domain: procurement. It gives us the reverse of Ann's problem. Ann is one person who could be split into two. Here, two requests could be merged if we use a number that is only unique within a business unit.

Search for 42. The inventory shows the value and the surrounding fields: one example belongs to east, another to west. We do not need to read raw JSON to find that distinction.

The inventory also reports missing and empty fields. Its role is to show what the samples contain. A repeated value could be an update to the same record, or it could identify different records in different scopes. Samples alone cannot decide that business rule.

Source categories can be corrected, and the original text is retained. The category suggestion is based on format; it is not a claim that the system has understood every rule in the document.”

**Footer:** Shows: deterministic inventory, saved source material. Does not show: an executable procurement pack.
**Sources:** M5 clarity acceptance in Fable M6 review; M6 final intake result. Visible clip label: “Synthetic procurement intake; no agent call for inventory.”
**Audience prompt:** “What extra fact would settle whether these are one request or two?” Expected discussion: source-system identity scope, not sample count alone.
**Transition:** “Back to Ann: we do have an explicit identity rule, so we can compare the proposal with it.”

### 6. Review what the agent proposes

**Takeaway:** Review meaning and support, not only whether the file loads.
**Visual:** CRM proposal summary → source excerpt → Contact node → limitation. Reveal pack anatomy progressively as five review questions, not a paragraph of settings.

**Narration**

“The screen is called ‘How Engram understands them.’ Think of it as proposal review. Start with the plain-language summary and the records and relationships in the diagram. Then inspect where an important statement came from.

The ontology is the explicit definition of those record types, relationships and rules. We review five concerns: what the records are and how they are identified; what events can arrive; how events update the graph; what state changes are allowed; and how questions retrieve records.

In Ann's baseline, the proposal uses email to identify a contact. The source definition says the permanent CRM identifier should do that job. That difference is the point to discuss with the agent.

The engine checks whether the proposed pack is supported and structurally valid. It cannot establish that every business decision is correct merely because validation passes. Source references help us inspect the proposal, but a citation alone is not proof that the proposed rule follows from it.”

**Footer:** Shows: proposal and source comparison. Does not show: independent business approval.
**Sources:** baseline pack/source snapshot; review screen; validator.
**Transition:** “We can ask about that specific issue and prepare a change without editing YAML.”

### 7. Ask and steer — Clip 2

**Takeaway:** Explanation and revision are separate, reviewable actions.
**Visual/actions:** Open baseline limitation explanation; show actual response; enter operator answer; prepare request; distinguish operator wording/generated instruction; review and send; show saved revision and change list. Clip is a recorded live interaction on synthetic data; condensed waiting labelled. Do not imply a new live call during playback.

**Narration**

“This is a guided revision. The baseline already names the identity problem, so we are not testing whether the agent discovers it unaided.

First we ask for an explanation. The agent connects the email-based identity rule with the risk of separate contact records. That answer does not change the pack.

The operator then states the desired outcome: keep a person's history together when their email changes; use the permanent identifier from the CRM; preserve the deal rules and question behavior.

Before sending, we see the prepared request. The operator's words remain separate from the instruction prepared for the agent. The preview describes what may be affected, not a guaranteed result. Only the explicit send starts revision work.

The returned pack changes Contact identity to the permanent identifier. The recorded comparison confirms that the deal lifecycle, deal projection rules and normalized retrieval settings remain unchanged. We still have to review and test this revision. A completed agent job is not an approval.”

**Footer:** Shows: one guided live revision. Does not show: general autonomous diagnosis or guaranteed scope preservation on every call.
**Sources:** final live explanation/request/revision and preservation proof. Technical wording visible in the actual response must not be replaced by fabricated cleaner text.
**Transition:** “That was a case with enough information. What happens when the information is missing, or the call fails?”

### 8. Missing information and recoverable failure

**Takeaway:** Keep uncertainty and the operator's work visible.
**Visual:** Procurement unresolved proposal still, then separate “Controlled provider failure” CRM recovery still. Do not animate one artifact turning into the other.

**Narration**

“In the procurement example, the material does not establish every relationship and policy. The proposal asks about the supplier connection, the scope of request identity, and conflicting reopening rules. It does not produce a runnable pack by inventing those answers.

If the operator does not know, the question stays unresolved. The current flow also explains when applying answers is disabled. This is a boundary to understand, not a reason to type a guess merely to continue.

Now consider a different kind of problem: a request fails. This controlled failure example shows the answer, prepared request and prior pack retained. The operator can restore input after reload and must review the request again before retrying.

Advice also belongs to a particular draft revision. If sources change, an old explanation must not silently become current guidance. Stopping a wait is not necessarily proof that remote work has stopped. The interface and the recording should be honest about that distinction.”

**Footer:** Shows: unresolved procurement and separately controlled recovery. Does not show: universal missing-fact detection or all cancellation races.
**Sources:** M6 procurement artifacts; recovery evidence; independent Fable M6 review. Partial source-race observation remains in appendix, not narrated as a browser 409 reproduction.
**Transition:** “Once a proposal is supported and reviewed, we need a definition of a correct result.”

### 9. Test with reviewed questions and events

**Takeaway:** Write and review the expected outcome before running the test.
**Visual/actions:** CRM question and expected entity selection; graph expectations; show the reviewed reset guidance if selections change; run/result still; step through an event into the observed graph. No agent generation of a new oracle during this scene.

**Narration**

“Questions to answer is where we define useful outcomes. For this CRM example, one question asks which account deal D-7 belongs to. The expected answer is Acme. Another asks who works at Globex, with Bo's stable contact identifier as the expected result.

The entity picker helps us select records without remembering technical IDs. Those candidates come from a planned projection, so choosing them still requires comparison with the business source material.

We also review which graph records must exist. If we change the selections, their review confirmation must be made again. The interface now says what was saved, what was cleared and which box to confirm. Run remains disabled until the required review is recorded.

The sandbox processes the example events and compares observed results with the reviewed expectations. Keep three pictures separate: the schema shows what is allowed, the planned change shows what a rule would write, and the observed graph shows what this run actually stored.”

**Footer:** Shows: reviewed example execution in isolated memory. Does not show: production answers or independent correctness of candidate expectations.
**Sources:** final CRM sandbox; M6-1 independent recheck and current bundle. Acme graph assertion was author-reviewed before execution.
**Transition:** “The score is perfect here. Let us be precise about what that means.”

### 10. What does the score prove?

**Takeaway:** A passing score only covers the questions actually checked.
**Visual:** Two existing questions next to their F1 results; separate pane for Ann's recorded contact. Label “Checked: existing questions” and “Observed: one Ann contact.” No green badge saying “identity change proven.”

**Narration**

“Neither of these questions asks about Ann's email change. So what does F1 one mean?

For these two questions, the retrieved answer sets match the expected answer sets. That is useful regression evidence: this revision did not break those examples. It is not a direct test of the identity change we requested.

Separately, the recorded graph shows one contact for Ann. That observation supports our inspection of the revised behavior, but it was not the subject of a dedicated, reviewed email-change assertion in this run.

To make that stronger claim in a future test, we would first specify the expected result: the repeated permanent identifier updates one person despite the changed email, with the intended history and relationships. Then we would run and check it. We would not invent that expectation after seeing the result and call it an original test.

The distinction matters because a high score can be completely accurate and still answer a narrower question than the one we care about.”

**Footer:** Shows: no regression on two existing questions; one Ann observed. Does not show: a dedicated identity-change test.
**Source:** Fable M6-2 and corrected handoff.
**Audience prompt:** Ask the score question before the second paragraph; allow five seconds of silence.
**Transition:** “After review and testing, what exactly do we approve?”

### 11. Approve and hand off

**Takeaway:** Approval identifies a tested artifact; it does not activate a tenant.
**Visual:** Approved package, composed bundle, optional artifact-identity disclosure. Draw an explicit boundary after handoff; no animated deployment beyond it.

**Narration**

“Approval records the pack and the inputs and engine identity associated with this work. The package can be inspected and handed to the person responsible for operational use.

This screen is deliberately explicit: nothing is deployed or activated by approving it. A draft workspace, an approved package and a running tenant are different states.

There is another distinction after deployment. A pack still needs to answer well on the tenant's actual graph. That requires the appropriate recorded evaluation on that data. A new tenant may not have enough history yet. We should not confuse runtime configuration being active with its questions being ready to serve.

The workbench demonstrated here does not perform that production activation. It prepares a reviewable artifact. The engineering appendix describes the operational boundary and the changes that can require replay or rebuilding, without suggesting those operations happen when we press Approve.”

**Footer:** Shows: approved handoff artifact. Does not show: provisioning, runtime activation or target-data readiness.
**Sources:** approved-package record; capability response; operational runbook. Do not imply the UI compares against a deployed approved version when classification is initial.
**Act-break question:** “Can this approved package answer live queries immediately?” Expected answer: approval alone establishes no live activation or target-data evaluation.

## Act 3 — The same loop elsewhere

### 12. Run a prepared story

**Takeaway:** A story tests an ordered sequence against a pinned pack.
**Visual:** “Switching to software delivery — PDLC.” Story question, event timeline, checks and backend labels. Show saved memory and Spanner results side by side with their identities, not an unperformed toggle/run.

**Narration**

“Now we move to software delivery. The question is whether a requirement was implemented, reviewed and tested. Answering that requires several events and relationships, not one isolated sample.

A story packages that sequence with checkpoints and expected answers. The prepared PDLC story already contains those inputs. An operator can run it, step through the events and inspect the results without authoring the ontology again.

For this recorded story, the same pack and engine produced 111 passing checks in memory and on Spanner. The Spanner run also verified cleanup before releasing its sandbox database.

Memory and Spanner are different storage implementations beneath the engine. Matching results on this story are valuable integration evidence. They are not proof that every PDLC story, every backend or a deployed shared service behaves identically. We also retained the earlier timeout instead of replacing its record with the successful rerun.”

**Footer:** Shows: one frozen PDLC story, matched outcomes and verified Spanner cleanup. Does not show: exhaustive PDLC or deployment coverage.
**Sources:** final PDLC/memory results, preservation proof, epoch 33 cleanup.
**Transition:** “Prepared stories are one starting point. We can also ask the agent to propose a new one.”

### 13. Create a new story with the agent

**Takeaway:** Generated tests need review as much as generated rules do.
**Visual:** Saved fixture-author outline → events/checks → per-check review → saved workspace. Persistent “Saved fixture-author result” label; do not stage a live-provider run.

**Narration**

“The operator begins with a situation to explore. For example, what should happen when a request is resolved twice, or when a relationship arrives after the record it refers to?

The authoring flow can propose an outline, concrete events and checks. IDs, ordering and state transitions need to fit the pack. Each expected outcome must be reviewed before the story is saved for execution.

This scene shows a saved result from a fixture author. It demonstrates the authoring and review interface, not the quality of a live agent's story generation. The successful live pack revision we saw earlier does not establish that separate capability.

Coverage helps us decide what to try next: which events or behaviors have no check, which checks exist but have not run, and which results are current or stale. A passing story covers its assertions. It does not establish that everything in the domain has been tested.”

**Footer:** Shows: fixture story authoring and review. Does not show: live story-authoring reliability or exhaustive coverage.
**Sources:** Fable M4 polling review saved artifacts; coverage implementation.
**Transition:** “Some of the most useful stories are the ones that explain a failure clearly.”

### 14. Learn from a failed or weak check — Clip 3

**Takeaway:** Keep failures and unsupported questions visible; inspect before changing anything.
**Visual/actions:** Explicit “Incident operations fixture.” Show 4 passed, 2 failed, 1 unsupported. Expand wrong-title card and wrong-account question. Hold each difference five seconds. Show unsupported total, read-only explanation area and preserved rerun. Do not alter the oracle.

**Narration**

“This is an incident-operations fixture with deliberate failures. The title check shows the expected title beside the title that was recorded. The answer check shows an incident from the wrong account. We can see what differed without opening raw JSON.

The total-cost question is different: it is unsupported by this record-set question mechanism. That is not a successful answer and is counted separately.

The guidance helps us decide where to inspect: the source data, mapping, graph or question scope. An agent explanation can help, but it is not a verified diagnosis and cannot edit the story from this panel.

There is also a subtler problem: a weak assertion can pass without establishing useful behavior. Checking that an impossible record is absent is not strong proof. The UI flags known weak cases; the review records remaining limits.

When we rerun this story unchanged, the same failures remain. We do not turn a red result green by quietly rewriting what we expected.”

**Footer:** Shows: controlled failure inspection and unchanged rerun. Does not show: universal weak-test detection or live-agent diagnosis.
**Sources:** final failure-rerun and independent Fable M6 review.
**Transition:** “We have now seen the operator loop. Let us expand the system picture underneath it.”

## Act 4 — Where we are

### 15. Under the hood: from event to answer

**Takeaway:** Authoring, execution and storage have distinct responsibilities.
**Visual:** Grow the slide-2 strip into API admission → event ledger → projection worker → stored graph → retrieval. Pack configuration feeds validation/projection/retrieval. Agent sits in the authoring lane, outside deterministic processing. Show storage adapter beneath ledger/graph without implying all capabilities share one universal storage contract.

**Narration**

“At the front of the execution path, admission checks whether an event is supported and whether its payload satisfies the declared contract. Accepted events enter the ledger. A worker processes them using the pack's rules.

Those rules identify records, update properties, apply allowed state transitions and connect records. Source links let us trace a projected record back to supporting events. Retrieval then uses the relevant supported settings to find records for a question.

The pack is configuration written in YAML. Shared Python structures define what it may contain, and the engine checks and executes the supported parts. These are not separate Python classes for every tenant's YAML file.

The agent is outside that execution path in this walkthrough. It helps draft or explain configuration; it does not decide each deterministic projection by improvising at runtime. A request for behavior the engine does not support becomes engineering work.

Storage adapters handle the underlying persistence. The Spanner sandbox results demonstrate the tested integration, while the engine and pack supply the domain behavior.”

**Footer:** Shows: supported execution architecture. Does not show: arbitrary YAML capabilities or an unrestricted coding agent.
**Sources:** engine/composition/admission/projector; workbench execution and Spanner pool; study guide reconciled to current code. Optional note: processed versus explicit ledger-only events, in appendix B.
**Transition:** “The final boundary is whose configuration and data each operation belongs to.”

### 16. Tenants and what stays separate

**Takeaway:** Domain configuration and tenant isolation are related but different concerns.
**Visual:** Four-row table: CRM guided draft, procurement incomplete draft, PDLC prepared story, incident fixture. Columns: purpose, pack/artifact, source material, trust and questions. Separate runtime panel: authenticated tenant identity → pinned configuration → assigned resources. Avoid drawing four deployed databases for four draft cards.

**Narration**

“The workspaces we used serve different purposes. CRM demonstrates a guided pack revision. Procurement contains unresolved input. PDLC has a prepared software-delivery story. Incident operations supplies a controlled failure scenario.

They are not four equivalent production deployments. Their labels, packs, inputs and test results tell us what each artifact can demonstrate.

At runtime, authenticated tenant identity must determine the appropriate configuration and database resources. A caller should not gain another tenant's data simply by naming it in a request. Those boundaries belong to the runtime API and storage controls; draft ownership alone does not prove them.

The configuration also needs to compose correctly. Core is shared, optional add-ons have their own declarations, and domain dependencies and names must be compatible. The workbench catalog currently includes PDLC and a CRM example adapted from a test fixture. A saved authored pack is a separate artifact, and the incomplete procurement draft is not a shipped procurement ontology.”

**Footer:** Shows: configuration comparison and runtime contract. Does not show: deployment of these workspaces or a new multi-tenant production test.
**Sources:** catalog/pack files, tenant runbook, source records.
**Transition:** “That brings us to what we can confidently say today—and what we want the team to try.”

### 17. What is verified, and what should the team try?

**Takeaway:** Technical acceptance is useful evidence, not a substitute for operator understanding.
**Visual:** Separate rows for UI fixtures, guided live CRM, incomplete procurement, memory/Spanner integration and real humans. Avoid an overall readiness percentage. Link the review and appendix.

**Narration**

“M6 passed independent review for its bounded technical scope. The recorded evidence includes a guided live CRM revision, unresolved procurement input, repeatable PDLC execution and recovery and failure checks in the UI. The graph-review reset guidance has also passed its focused independent recheck.

Those statements have specific limits. The CRM questions show no regression, not a dedicated test of Ann's identity change. Live story authoring is not established by the fixture demonstration. The earlier Spanner timeout is retained, with its cause still unknown, despite a successful later run and verified cleanup.

Real-operator sessions are still outstanding. We have not established that unfamiliar people can use every part of the flow unaided.

For the team, the next useful task is concrete: bring a small domain definition, actual event contracts and redacted examples. Review one consequential identity or state decision, write an expected outcome before running it, and see whether the interface lets you explain both the result and its limits. Tell us where you needed help—not just whether the screen looked polished.”

**Footer:** Shows: independently accepted bounded technical evidence. Does not show: full self-service, production readiness or human-usability acceptance.
**Sources:** independent M6 and M6-1 reviews; milestone ledger.
**Closing discussion:** Which part of your domain would make a useful first story? What fact would an agent have to ask you rather than infer?

## Appendix A — Research basis and limits

These are related research directions, not evidence that Engram is an implementation of each paper. Primary abstracts checked for this draft; no paper performance numbers are transferred to Engram.

| Primary source | Relevant research idea | Engram connection and boundary |
| --- | --- | --- |
| [GraphRAG: From Local to Global](https://arxiv.org/abs/2404.16130) | Builds a graph index and community summaries to support corpus-level questions. | Relevant motivation for using relationships in retrieval. The pack workbench demonstration does not establish GraphRAG community-summary retrieval or its reported results. |
| [HippoRAG](https://arxiv.org/abs/2405.14831) | Combines knowledge graphs with Personalized PageRank for retrieval across connected information. | Relevant comparison for graph-based retrieval. No claim that the demonstrated artifact-query path implements HippoRAG's algorithm or reproduces its benchmarks. |
| [Zep temporal knowledge graph architecture](https://arxiv.org/abs/2501.13956) | Integrates changing conversational/business information with historical relationships. | Related motivation for retaining context and history. Engram's demonstrated event ledger, source links and lifecycle rules do not establish equivalent temporal semantics or benchmark performance. |

Repository research context: `docs/research/cluster1-context-graphs.md`, `docs/research/ontology-cognitive-multigraph.md`. Those are historical design research, not current capability inventories. Review any additional research claims against primary sources and the actual path used in the demo.

## Appendix B — Pack anatomy and engine reference

A compact, illustrative example to explain configuration, not a substitute for the complete executable CRM pack:

```yaml
# Excerpt only: not a runnable standalone pack.
types:
  nodes:
    Contact:
      key: [contact_id]
      properties:
        contact_id: string
        email: string
```

Speaker note: “The key says which incoming changes belong to one record. Email is a property that may change. Event contracts and projection rules are still needed; the excerpt alone cannot ingest an event.”

For detailed questions, inspect: `domain/ontology.py` for the shared pack format; `ontology/loader.py` and `domain/pack_bundle.py` for loading/composition; `domain/pack_admission.py` for accepted/explicit handling; `domain/pack_projection.py` for planned writes and guards; `domain/pack_intents.py` and the actual artifact query path for retrieval. Paths are relative to `src/context_graph/`.

Explain contract, mapping and lifecycle with separate excerpts from the actual selected pack. Do not show speculative fields as active behavior. Provenance is not a replacement for semantic correctness; some declarations are inert or limited as recorded by engine warnings. Extraction is not an authoring capability demonstrated in these scenes.

## Appendix C — Composition and tenancy

Core is always active and defines shared event/entity/summary concepts and interfaces. Memory declares beliefs, goals and episodes; user declares profile/preferences/skills/behavior concepts and has specialized processing configuration. This is not a promise that selecting an add-on runs all its processing in the workbench sandbox.

Dependencies and global-name checks apply to the whole composed bundle. Runtime tenant routing, credentials, roles, pinned configuration and assigned database resources are described in `docs/runbooks/tenant-api.md`; verify the selected construction path before adding further claims. Workspace owner isolation and runtime data isolation are distinct checks.

## Appendix D — Agent boundary and recovery

The agent receives server-assembled context and proposes artifacts within a constrained workflow. Semantic validation belongs to the engine. Operators review consequential decisions, removals and expected outcomes. Permission to send source excerpts is required before provider calls. Explanations are revision-bound; they cannot be reused as authority after relevant changes.

Show the existing safe-retry sequence rather than a generic spinner. Cancellation, stopped waiting and actual remote completion are distinct. The recorded source-race check is mixed UI/API evidence: no old answer displayed and a subsequent stale API 409; the initial browser response was not observed. Do not narrate it as a reproduced browser 409.

## Appendix E — Test interpretation

- Schema graph: allowed types/relationships. Planned delta: rule's intended writes for an event. Observed graph: saved result of a run.
- Pack samples test supplied events and questions. An event story tests ordered behavior. A pre-seeded graph fixture tests retrieval and does not prove ingestion.
- Mean F1 compares returned and expected record sets across the selected questions. It is not “percent of all domain behavior correct.”
- Explicit starting records suppress additional seed discovery in that mode; they do not automatically prevent traversal through a shared node. Do not present them as account isolation.
- Weak-check warnings do not establish exhaustive semantic test quality. Keep known lows in the linked review.
- Spanner evidence includes slot identity, epoch, run identity and verified cleanup. It is not inferred from a memory run.

## Appendix F — Handoff and change management

Show artifact identity under the engineer disclosure if asked. A draft revision number is not a promise of deployed pack version changes. Explain additive, mapping and breaking classifications as engine concepts, with replay/rebuild implications, without implying the current workbench performs those operations or compares against an actual active tenant bundle.

Approval freezes a reviewable handoff package. Runtime activation and target-graph evaluation remain separate operational concerns. Do not demonstrate a fake activation button or imply an empty graph has passed production evaluation.

## Appendix G — Evidence and recording sheet

Use `docs/engram-pack-workbench-team-presentation-plan.md` for the full requirement coverage and named artifacts. The revised slide mapping is: baseline 1/12→1; 2/3/4→2; 6→3; 7→4; 8→5; 3/9→6; 10→7; 11→8; 12→9/10; 16→11; 13→12; 14→13; 15→14; 4→15; 5→16; 17→17. Required appendices A–G remain present.

| Capture | Required start/end state | Source | Status |
| --- | --- | --- | --- |
| Ann baseline | Email-keyed pack; two planned contacts for Ann | M6 final starting snapshot, identified baseline copy | Capture/rehearsal pending on recording build |
| Ann observed | Revised contact_id key; one Ann in recorded graph | M6 final live-flow-sandbox result | Capture/rehearsal pending; entity-list count alone is not the recorded-graph frame |
| Clip 1 | Procurement sources → repeated 42 with east/west | M5 clarity / M6 intake artifacts | Accepted behavior; final capture pending |
| Clip 2 | CRM explanation → prepared request → saved live revision | M6 final live-chain artifacts | Recorded source available; final edit/capture pending |
| Review reset | Selection change → explicit notice → confirmation → Run enabled | Fable M6-1 recheck, bundle B1KO3MGA | Independently closed; final capture pending |
| PDLC | Frozen story → 111 results and cleanup | M6 final memory/Spanner results | Recorded evidence; final framing pending |
| Story author | Saved fixture outline/checks/review | Fable M4 polling artifacts | Fixture label required; final still pending |
| Clip 3 | Existing incident failures → readable differences → same rerun | M6 failure-rerun / Fable M6 | Accepted bounded behavior; final capture pending |

Do not recreate research diagrams as if measured product outputs. Every final clip needs captions, readable holds, backend/agent labels and a still fallback. Preserve input and output artifact identity when condensing waits. Keep credentials and internal tokens out of recordings. Use the saved screen title as the chapter name where appropriate.

## Review request and gate

Fable should review this transcript for narrative clarity, factual accuracy, terminology, omitted baseline coverage, clip feasibility and unsupported claims. In particular: early overview versus late architecture depth; the planned/observed Ann distinction; the narrow F1 claim; accurate guided-agent labeling; add-on declarations versus runnable sandbox capabilities; and research comparison versus implementation claims.

The user subsequently authorized draft presentation production. The deck and script still need Fable review before final recording. No new live calls or production deployment are implied by presentation work. Real-operator sessions remain separate. Earlier product lows, including the unsaved-selection banner wording, are not silently closed by presentation work.
