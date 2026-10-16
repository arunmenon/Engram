# Presentation plan: five worker deep dives

## Purpose and scope

Explain the five existing worker roles to a first-time reader, one dedicated HTML page per role. Only one role is graph projection in the narrow sense; session extraction, enrichment, consolidation and pack extraction are distinct jobs. Preserve the user's “projection layers” mental model while naming those differences clearly.

Primary audience: product stakeholder and junior engineer. Secondary audience: pack author and operator. Readers should understand what executes, what controls it, what reaches Spanner, where models participate, and which claims are supported. Avoid assuming all combinations work because the engine is shared.

This deliverable is a presentation/content plan and independent review. It does not implement runtime changes, run cloud experiments, start the composition assessment/pilot, or mark any goal complete.

## Teaching sequence on every dedicated page

1. **Purpose first:** one plain sentence explaining why the job exists and how it differs from adjacent jobs.
2. **Where it runs:** Engram Python process, consumer role/group, interfaces, Google SDK and tenant database. Pack selection configures supported behavior; deployment starts the worker.
3. **When it acts:** delivery, batch flush, session trigger, timer or matching profile. Show a legitimate no-work case.
4. **Flow diagram:** accepted event identity → document read → trigger/rule decision → computation → applicable storage operations → acknowledgement. Model calls are a separate visible branch, with the returned result and checks shown. Diagrams must follow real control flow, not force every role into this template.
5. **Before / after example:** small payload excerpt, rules or model input, conditional result, graph/table changes. State what was supplied versus inferred. Fundamental example first; a PDLC example second.
6. **Pack applicability table:** core; core+user; core+memory; core+PDLC; core+PDLC+memory; core+user+memory. For each distinguish producer availability, applicability to this event, and evidence of execution. No implied automatic Memory producers.
7. **Read consequence:** which written fields/nodes/edges a relevant retrieval path can use. Explicitly distinguish stored embedding from an eligible ANN-indexed node.
8. **Failure / progress:** no match, unavailable provider, malformed result, storage failure, missing projected target and write-before-ACK window as applicable. Explain when processing may finish without outputs; do not promise unconditional live retries.
9. **Evidence box and learning check:** source references, specific existing run/test evidence where directly relevant, what remains unverified, and two questions a reader should now answer.

## Dedicated page plans

| Page | Content and example | Diagrams and delivery | Critical limits to show |
|---|---|---|---|
| Graph projection | Core Event creation and activity links; deterministic pack rule interpretation; identity/reference handling; staged writes and flush. Example: explicit failed-test payload produces TestRun/TestCase and supplied relationships. | Numbered trigger-to-flush flow; payload/rule/node-edge strip; separate write-completion and ACK steps. | No LLM for deterministic facts. Domain rules must exist. Placeholders are not observed facts. Shared worker does not establish all-pack correctness. |
| Session extraction | Session collection at session_end or configured turn threshold; model call; entity resolution; optional user extraction/writers. Example: session mentions Billing and a preference. | Trigger decision tree; model request/result branch; conditional Event→REFERENCES→Entity and Entity→HAS_PREFERENCE→Preference→DERIVED_FROM→Event fragments. | A single event often waits. User behavior disabled when user absent. User identity derives from agent_id. Preference provenance is session-wide; source_quote/evidence_quote mismatch means quote loss on this path. No implicit Belief/Goal/Episode. |
| Enrichment | Keywords from event type/tool; importance; optional embedding provider and fallback. Example: pdlc.testcaserun.finished outcome remains producer-supplied while the Event gains annotations. | Before/after Event record; deterministic branch versus embedding-service branch; graph-target prerequisite. | Embedding service is not a generative LLM decision. Event embedding is not Entity ANN eligibility. Missing provider or embedding failure can leave keyword/importance enrichment only. Independent ordering must be assessed. |
| Consolidation | Ordinary events are skipped as triggers; timer or explicit consolidation trigger; accumulated activity, episode grouping, summaries and maintenance. Optional LLM summaries and code fallback where supported. | Separate timer lane and message lane; summary generation / graph persistence; Summary→SUMMARIZES→Event example. | Grouping into episodes does not create Memory Episode nodes. Actual summarization/retention eligibility matters. No one-summary-per-event promise; no assumption every domain fact survives summary text. |
| Pack extraction | Match declared sources/profile; gather text/known items; construct prompt; model response parsing and allowed proposal planning; apply via storage interfaces. Example: design prose yields allowed Decision/Constraint proposal; test-run event has no matching profile. | Match/no-match fork; model boundary and validation boundary; declared-fact versus proposed-link comparison. | PDLC never_propose types remain forbidden. Proposed is not confirmed. Model unavailable and malformed answer have different handling; malformed JSON may log and ACK without artifact writes. No relevant text may yield nothing. |

## Pack truth and evidence rules

Use three independent questions rather than a single “works” checkbox:

- **Implemented:** which capability/rule/profile the current source supplies, with references.
- **Applicable:** whether the selected bundle and this particular input/trigger would use it.
- **Verified:** a named test/run and the precise output it checked, otherwise “not established by this documentation review.”

Core handlers exist for activity projection, entity extraction, enrichment, summaries and retention. User declares specialized user.extract.v1. Domain projection/extraction uses supported generic handlers. Memory declares types without a registered producer. Dependency validity does not prove operational readiness or tenant safety. Unbound processes resolve configuration independently; a bound runtime supplies the pinned bundle.

Existing journey evidence must not be used to imply every worker output was verified: zero lag and ACK are not semantic proofs. Report any missing runtime evidence as a bounded probe proposal, not a newly executed result.

## Integrating with the guide

Keep the high-level page-six explanation before the worker names and diagram. Make page seven a short “choose a worker” overview with links to the five dedicated pages. Move the long worker details into those pages rather than duplicate them. Keep the 15 PDLC journey examples as a later comparative reference, after the individual mechanisms. Regenerate navigation and cross-page links by stable page identifiers rather than fragile numeric offsets when adding pages.

Use a consistent visual language: boxes for application/storage components, diamonds or clearly labelled forks for decisions, solid arrows for actual call/control paths, dashed arrows for conditional relationships, labelled parallel lanes for independent workers. Define terms at first use. Provide concise diagrams plus prose explaining why each step exists; do not compress full explanations into tiny SVG labels.

## Astra review ask — low effort

Assess this plan and the existing guide against the actual worker construction, processing functions, capability resolution, pack declarations and available evidence. Read-only. Do not implement or run cloud tests.

Return:

1. Whether each proposed page will teach a junior engineer the high-level purpose and low-level execution without oral explanation.
2. Concrete factual corrections and omitted branches, with code references.
3. Whether “across packs” is accurately scoped; identify any unsupported claims or evidence conflation.
4. Per-page suggestions for example choice, diagram structure and explanation order.
5. A bounded approved/revise verdict and the smallest necessary plan edits.

Focus on delivery quality as well as technical accuracy. Preserve the five-page scope and avoid inventing new runtime abstractions.

## Astra low-effort assessment applied

Astra recommended keeping the five-page structure and adding: projection partial-success/dead-letter handling; exact enrichment model input and split failure handling; consolidation scopes/maintenance/eligibility/error behavior; process-local session delivery counts and resolution steps; pack extraction provenance, missing endpoints and persisted-edge distinctions. These corrections are included in the five dedicated pages. Six combinations are labelled selected comparisons, with runtime verification not established by this documentation review.

## Interactive teaching revision and Astra recheck

Five worker lessons now begin with purpose/job/result, followed by cumulative four-stage graph examples. Astra found them materially clearer and requested factual corrections. Applied: session-wide entity REFERENCES; ledger payload versus graph Event distinction; importance reassertion rather than first creation; applicability-column admission scope; source Event prerequisite for pack extraction; explicit session Summary scope; repository-scoped test identity and full event name. This was a read-only content/source review, not rendered visual QA or runtime verification. Stage controls were exercised using a lightweight DOM test harness.
