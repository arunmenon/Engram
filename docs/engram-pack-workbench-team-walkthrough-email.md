To: Engram team

Subject: Engram Pack Workbench — what it enables and how the operator workflow works

Date: 18 November 2026

Status: Internal walkthrough of the current implementation; not a production-readiness announcement

Hi team,

The Engram Pack Workbench gives an internal operator a place to turn a tenant’s business documents and example events into explicit rules, inspect those rules, test their consequences, and prepare a reviewed package for engineering handoff. The intended benefit is to make domain onboarding a shared activity between domain experts, operators and engineers, rather than requiring an engineer to translate every business decision directly into configuration. We have not yet measured a reduction in onboarding time or engineering effort.

This email walks through the product from the beginning. You do not need to know the pack format or the engine’s terminology to follow it.

Watch the accompanying videos:

- [Engram team walkthrough — v3](https://drive.google.com/file/d/1CtLJ5vULWYCSNukULQMLkBGyjCtOokFI/view) (20:48): a narrated walkthrough of saved screens explaining the framework and operator workflow.
- [Pack Workbench product-tour pilot — review draft](https://drive.google.com/file/d/1i-VlIAzktq66xG2_7J04TZUTZRkPg-P6/view) (4:44): a short product-tour pilot; pacing corrections are still pending.

Both videos are public to anyone with the link, with Viewer access; no access request is needed. This sharing setting was verified on 18 November 2026. These recordings are orientation material, not acceptance evidence, and still require a human audio check.

Engram connects records and events so that applications and agents can retrieve relevant context. Its context graph contains entities, their relationships and links back to the events that support them. But connecting data requires business decisions: which fields identify a person, whether an identifier is unique across business units, which state changes are permitted, and which sources should be trusted. A matching word or repeated number cannot settle those decisions by itself.

An **ontology pack** makes those domain rules explicit. It describes the kinds of records and relationships, their identity and lifecycle, the incoming event contracts, how events create or update the graph, and how questions retrieve records. Evaluation questions specify the outcomes we expect from representative data. The shared engine loads and checks the configuration and executes supported behavior. The workbench helps people author and review it.

That separation matters: a new domain can supply different rules while using the same engine. A pack can use capabilities the engine already supports; it cannot add arbitrary new processing behavior simply by describing it in YAML. Unsupported requirements still need an engineering decision.

Core supplies common definitions. Optional User and Memory packs add their respective capabilities, and domain packs describe a business area. The workbench’s available pack choices come from the server’s catalog. The current build exposes a CRM fixture-based example and software delivery (PDLC); procurement has been exercised as intake and unresolved authoring, and should not be described as a completed runnable procurement pack.

The responsibilities are distinct:

- The **domain expert** supplies business definitions, representative inputs and the intended answers.
- The **operator** configures the draft, resolves business decisions, reviews the agent’s proposal and accepts the test expectations.
- The **agent** explains supplied material and proposes packs, revisions or stories within the supported workflow.
- The **engine** checks and executes the configuration. A successful engine check establishes technical validity, not that the business interpretation is correct.
- The **engineer** handles unsupported capabilities and the operational work after handoff.

Today the agent is a constrained authoring and explanation service. It is not a coding agent that edits the engine, installs adapters, runs commands on production systems or deploys a tenant.

There are two ways into the workbench. Start a tenant draft to author a pack, or open a prepared story to explore an existing one. A **tenant draft** is a workspace containing the tenant’s inputs, proposal, review decisions, questions and results. A **story** is a saved sequence of events with expected outcomes at particular checkpoints. Opening a story does not run it.

For a new draft, the main path has six steps:

**Tenant setup → What describes their world? → How Engram understands them → Questions to answer → Test with examples → Approve and hand off.**

The next-action banner points to the current prerequisite. The readiness checklist distinguishes **Ready to build**, **Ready to test** and **Ready to hand off**. These are different milestones: enough information to draft rules is not necessarily enough to test or approve them. “Under the hood” is an optional technical view alongside the main path.

1. **Set up the tenant draft.**

   Give the draft a name and environment, and describe its scope. For example: “Track sales contacts, companies and deals; exclude billing.” The exclusions matter because they constrain what the agent should propose. Inspect existing domain packs and optional additions under the pack selector rather than assuming every draft starts from an empty vocabulary.

   Data handling comes before agent use. The operator chooses whether inputs may be used by the agent’s external service and confirms that sensitive material and secrets have been reviewed. Merely saving inputs is different from requesting an agent operation.

   Producer trust is a separate choice: which sources in the sample events should this test believe? Permission to send material to an agent does not make its event producer trusted, and test trust does not grant production access.

   Creating this workspace does not provision a production tenant or database. Save status and revision identify the draft being edited. The tenant card can remember where this operator left off in the same browser; that resume position is not a guarantee across browsers.

2. **Supply the material that grounds the pack.**

   The current upload flow accepts `.txt`, `.md` and `.json`. It categorizes material as a process document or glossary, an interface schema, or sample events. Format-based suggestions help organize inputs; the operator can correct them. A guessed category is not proof that the contents are complete or correct.

   Useful material includes:

   - Scope, process descriptions and a glossary: what the business tracks and what its terms mean.
   - Event or interface definitions: the fields a producer can actually supply.
   - Redacted or synthetic examples: creation, updates, state changes and missing-field cases.
   - Identity and lifecycle rules: when two events refer to the same record, and which transitions are allowed.
   - Questions and independently reviewed expected outcomes: what a useful answer should contain.
   - Source-trust decisions and data-handling constraints.

   These need not arrive as one perfect specification. Add what is available, then use the open questions to identify what is missing. However, a plausible sample is not a complete contract: the team must confirm required fields, identifier scope and update semantics.

   The sample inventory makes examples easier to inspect without reading raw JSON. It supports searching fields and values and shows repeated values with their surrounding context. Request 42 in unit east and request 42 in unit west is a useful example: the repetition might mean two distinct records, whereas two events for request 42 in the same unit might be updates. The agent needs the business rule to decide how to group them.

3. **Generate, inspect and steer the proposed pack.**

   Once the required inputs and permission are present, the operator can request a proposal. The UI shows the authoring job’s progress and attempt state. The agent proposes configuration; the engine checks it. The operator then reviews the summary, schema graph, record types, relationships, supporting source references, assumptions and remaining questions.

   The schema graph shows what the pack permits. It is not a graph of records already ingested. Likewise, a citation tells us where a proposal drew its support; the operator still needs to decide whether that source justifies the rule.

   The workbench supports asking about the whole pack, a record or a relationship, and explaining a particular problem. Where supported, identity or lifecycle options can include previews calculated against the supplied examples. Those previews are planned effects. If the examples do not exercise a starting state, the preview cannot establish that a proposed transition will behave correctly in that state.

   Steering is a deliberate sequence: **explain → prepare a request → edit it → send → inspect the returned proposal**. Preparing text changes neither the pack nor its acceptance status. Sending asks the agent to produce a revision for review. A returned revision is not automatically approved.

   For example, a domain expert may say: “A contact remains the same person when their email changes; use the stable contact identifier.” The operator can ask for that change while specifying that company and deal behavior should remain unchanged. The resulting change review is where we check whether the agent respected that scope. Deletions deserve explicit attention, and “Keep this data” prepares a request rather than silently restoring it.

   Recovery is part of this workflow. A failed authoring request should leave the prior proposal and the operator’s text available. Restored or stale requests require review against the current draft before sending. Editing inputs can invalidate earlier advice or results. These controls prevent an old explanation from being mistaken for a current recommendation; they do not eliminate every remaining usability issue.

   If a domain question is unresolved, the operator should provide an answer or supporting material, or leave it unresolved. We should not invent a relationship or weaken a requirement just to make validation pass.

4. **Define the outcomes that would make the pack correct.**

   In “Questions to answer,” write representative questions and review the records that should be returned. The UI offers named entity choices from the sample projection so operators do not have to memorize internal node IDs. Those choices are candidates produced by the proposed rules, not automatically correct answers. The expected result must come from domain knowledge or reviewed source material.

   Question settings can specify an answer type and optional starting records. Explicit starting points restrict discovery to the selected starting records; they are not a general security or tenant-isolation boundary, and traversal can still follow permitted relationships from them. Search configuration needs to match the question’s intended scope.

   Graph expectations can also state which entities must exist or must not exist after processing the examples. Review them before execution. If the selections change, the confirmation is cleared and must be given again for the saved selections. Otherwise, a tick made for one set of expectations could incorrectly appear to approve another.

   The questions edited here and the exported evaluation configuration are the same artifact. There should not be a separate, easier question set used just to make the demonstration pass. The currently supported question evaluations return sets of records; a scalar question such as “What is the total incident cost?” is not supported merely because it can be typed into the form.

5. **Run the examples and inspect what actually happened.**

   The sandbox runs the examples through the engine and compares the results with the reviewed expectations. The storage backend depends on how the workbench service is configured. Recorded verification covers isolated memory and a configured Spanner sandbox; a memory run should never be described as a live Spanner run. Spanner runs also have allocation and cleanup status that matters when reusing a database slot.

   Keep three views separate:

   - The **schema** describes allowed types and relationships.
   - A **planned change** describes what the rules would do to a sample.
   - The **observed graph** shows what a particular execution stored.

   The event selector lets the operator inspect the observed graph step by step, including admitted or rejected events. The question results compare expected records with returned records, and graph checks identify missing or forbidden entities. F1 combines whether the returned set includes the expected records and avoids extra ones; it measures those questions, not the completeness of the entire ontology.

   A failure can come from the pack, question configuration, sample coverage, an unsupported request or an engine problem. The operator should inspect the difference and its source before requesting a correction. Expected answers should not be rewritten merely to make the score green. A retained result from an earlier revision is historical evidence, not a passing result for the current draft.

6. **Approve a specific package for handoff.**

   After the current readiness gates and checks pass, the operator can approve the package. Approval records the operator, revision and a digest covering the content, proposal, validation and sandbox result. It refers to that reviewed state, not to any future edit.

   The handoff view includes the composed pack bundle and technical identifiers. Generated pack and evaluation YAML can be inspected, and “Download review package” exports the files with the draft record. Export itself is not proof of approval: a draft with an executable proposal can be exported before it has passed the approval gate. The receiver must inspect the recorded status.

   Approval does not restart services, provision databases or activate a tenant. There is no activation action in this workbench. Runtime rollout and any target-graph evaluation requirements remain separate operational work. An initial-draft change classification must also not be presented as a comparison against a tenant’s live configuration.

Prepared stories provide a second testing route, especially when a team already has an ontology and wants to explore it before authoring anything. The landing page offers four software-delivery stories: whether a requirement was implemented, reviewed and tested; whether design approval carries across revisions; which deployment shipped a change; and where a reference stops being trustworthy. It also offers 13 answer-oriented stories covering topics such as trust, paging, incomplete answers, work limits, rejected relationships and graph-versus-text-search comparison.

Within a story, inspect its inputs and expected checks, run it, step through the events, and review its coverage. No check, an unexecuted check, a passing check, a stale result, an unsupported question and a warning about assertion strength mean different things. For example, proving that a record is absent is weak evidence if no supplied event could create it. A large pass count does not establish comprehensive coverage.

The agent can help draft a new story or a follow-up outline, then propose events and checks for review. The operator reviews those expectations before saving a separate story workspace. Explaining an existing failed check is read-only; it must not silently change the expectation that failed. This lets us investigate the behavior while preserving the original failure.

For engineering inspection, “Under the hood” exposes the configuration behind these views: identity keys, lifecycle rules, event contracts, projection rules and related checks. The frontend calls the workbench’s administrative APIs; the service stores drafts and coordinates agent jobs, engine validation and sandbox execution. This is distinct from Engram’s runtime APIs that ingest and query a deployed tenant’s data. The browser is not directly editing a running engine’s pack files or caches.

Our current confidence is specific. M6 passed its independently reviewed technical scope, and its graph-confirmation clarity fix was subsequently rechecked. The records include guided live-agent revisions, controlled failure and recovery cases, and matching PDLC story outcomes on memory and Spanner. They do not establish general autonomous diagnosis, comprehensive cross-domain coverage or successful self-service by real operators. Real-operator sessions remain outstanding, along with recorded lower-severity findings.

One example illustrates why these boundaries matter: the CRM revision produced one observed contact for Ann after changing contact identity. Its F1 of 1.0 showed no regression on two existing questions; neither question directly tested Ann’s email change. The observed graph and those question scores support different conclusions, and we should explain both accurately.

For a first team session, I suggest starting with one prepared story, then creating a small draft with a process note, a schema, a few representative events and reviewed questions. Ask about one proposed rule, prepare a revision request, and deliberately inspect one failed or unsupported check. At the end, everyone should be able to answer: what changed when we prepared a request, what was actually tested, and what remains to be done after approval?

The accompanying recordings can help with orientation, but they are not acceptance evidence. The latest product-tour pilot still needs pacing corrections from Fable’s review, and the recordings require a human audio check. We should use the current product and the recorded verification reports to assess capability rather than treating a polished video as proof of readiness.

For readers who want to go deeper, these repository references provide the implementation plan and the acceptance boundaries described above:

- [Tenant administration and workbench plan](tenant-admin-workbench-plan.md) — design context; distinguish planned capabilities from shipped ones.
- [AI-native onboarding milestone plan](ai-native-onboarding-milestone-plan.md) — scope, milestones and historical verification checkpoints.
- [M6 independent review](review/2026-11-17-m6-fable-independent-review.md) — technical acceptance and remaining limitations.
- [Focused M6-1 recheck](review/2026-11-17-m6-1-fable-recheck.md) — confirmation-reset behavior and corrected CRM result wording.
- [Workbench UI](../demo/frontend/src/workbench/Workbench.tsx) and [administrative API](../src/context_graph/workbench/api.py) — current screens, readiness gates, approval and export behavior.

Thanks,

The Engram team
