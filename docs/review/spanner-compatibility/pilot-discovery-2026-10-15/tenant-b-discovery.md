# Tenant B controlled-pilot discovery — 15 October 2026

Read-only discovery at `feature/engram-memory-episodes`, HEAD `92a6053`. Proposed configuration: mandatory Core + PDLC + Memory; User disabled. This is a catalog of **24 candidate journeys**, not an executed pilot, approval to run, implementation plan or completion claim. Only this document is changed. No database operation, test execution, issue update or runtime change was performed.

The [current pilot scope](../2026-10-08-controlled-pilot-discovery-brief.md#current-pilot-scope-for-stakeholder-review--15-october-2026) asks for realistic connected developer activity through authenticated HTTP → Spanner ledger → applicable workers → graph → public reads. Existing bounded proofs supply reusable contracts, not automatic acceptance of these new stories. The stories below deliberately vary the product, failure and developer intent rather than repeat the password-reset demonstration.

## Evidence and interpretation

- **P**: current source of truth, [PDLC pack 5.0.0](../../../../src/context_graph/ontology/packs/pdlc.pack.yaml), especially `events`, `projection`, `extraction`, `retrieval`. **M**: [Memory pack 1.2.0](../../../../src/context_graph/ontology/packs/memory.pack.yaml), [atomic action producer](../../../../src/context_graph/domain/memory_actions.py), [Memory reader](../../../../src/context_graph/retrieval/memory_state.py), [Episode producer](../../../../src/context_graph/domain/episodes.py) and [reader](../../../../src/context_graph/retrieval/episodes.py).
- **G01**: [PR specification](../2026-10-08-goal-01-pr-activity.md), [verification](../2026-10-08-goal-01-verification.md), cleaned run: eight original scenarios/ten checks. **G02**: [planning specification](../2026-10-08-goal-02-planning-journey.md), [verification](../2026-10-08-goal-02-verification.md), cleaned run: 22 checks. **G03**: [implementation specification](../2026-10-08-goal-03-implementation-journey.md), [verification](../2026-10-08-goal-03-verification.md). **G04**: [release specification](../2026-10-08-goal-04-release-deployment.md), [verification](../2026-10-08-goal-04-verification.md), 31 checks. **G05**: [connected specification](../2026-10-08-goal-05-connected-journey.md), [verification](../2026-10-08-goal-05-verification.md), 39 checks. **G06**: [incident specification/ticket draft](../2026-10-08-goal-06-ticket-draft.md), [verification](../2026-10-08-goal-06-verification.md), 50 checks.
- **G07**: [28-event specification](../2026-10-08-goal-07-event-coverage.md), [verification](../2026-10-08-goal-07-verification.md), [catalog matrix](../2026-10-08-g07-event-coverage.csv). The stakeholder has explicitly confirmed G7 complete. This checked-in verification document is a stale historical index: it still says cloud not run and labels 638 checks planned. The final evidence index should link the latest G7 completion artifact; this does not reopen G7, require a G7 rerun or block discovery. G07-specific candidates below are current-contract/fresh-pilot-proof-needed, as are all new combined pilot stories; no planned count is promoted to a live result here.
- **MV**: [Memory verification, including subsequent Belief/Goal continuation](../memory-episodes-verification.md): 58 selected live Episode assertions and later 138 live Belief/Goal checks, separate scopes. **CV**: [pack composition verification](../pack-combination-verification.md): selected five configurations, scripted external extraction/summary output, actual workers. **TV**: [tenant isolation verification](../tenant-isolation-verification.md): 184 main + 12 restart checks, bounded public dispatcher, independently pinned databases. **EV**: [enrichment verification](../enrichment-ordering-verification.md).

`verified representative` means an earlier bounded run establishes the named behavior with its stated configuration/provider limits; the proposed new story still needs proof. `current contract / new proof` means source supports the path but the combined story or specific event coverage has no accepted live proof identified here. `gap` means the requested knowledge has no deterministic producer/read guarantee in this inventory. `product decision` means the scope/identity/provider acceptance needs choosing before promising behavior. No verdict means arbitrary natural-language understanding is established.

## Actual inventory and coverage limits

All **28 declared PDLC events have a projection entry** in current P. A valid commit without a trailing PR suffix is deliberately ledger/Event-only; the existence of a rule does not mean it creates a domain artifact. Event groups and candidate coverage:

| Event family | Exact declared suffixes after `pdlc.` | Candidates |
|---|---|---|
| Request and planning (7) | `request.created`, `spec.changed`, `spec.approved`, `requirement.changed`, `design.section_changed`, `design.approval_recorded`, `decision.recorded` | B01–B06, B17–B18 |
| Work (3) | `ticket.created`, `ticket.updated`, `ticket.closed` | B07, B09, B12, B17 |
| Changes and review (6) | `change.created`, `change.updated`, `change.reviewed`, `change.merged`, `change.abandoned`, `change.committed` | B07–B10, B12, B14, B19 |
| Test execution (2) | `testcaserun.finished`, `testcaserun.skipped` | B11–B12, B18 |
| Release and deployment (5) | `release.published`, `service.deployed`, `service.deployment_failed`, `service.rolledback`, `service.upgraded` | B13–B16, B19 |
| Operations and learning (5) | `incident.detected`, `incident.reported`, `incident.resolved`, `incident.remediation_recorded`, `incident.lesson_recorded` | B15–B16, B20 |

Memory declares eight explicit producer events: `memory.belief.{stated,inferred,confirmed,corrected}` and `memory.goal.{created,completed,abandoned,superseded}`. `inferred` is an explicit structured producer assertion, not automatic session inference. Episodes have no ingestion event here; scheduled consolidation produces exact temporal membership snapshots. Core observations/session activity supply the common evidence spine. B21–B24 combine these with domain journeys.

Declared schema exceeds deterministic event behavior. No listed event directly authors `DEPENDS_ON`, `OWNED_BY`, `ATTRIBUTED_TO`, `RAISES`, `SAME_AS`, `CONSTRAINS` or `DECIDED_BY`; a schema edge is not a promised producer. The prose profile may propose a Constraint node, but it does not list `CONSTRAINS` among proposable edges. `AMENDS` is a proposed prose link, whereas `decision.recorded` explicitly supports `SUPERSEDES` and `APPLIES_TO`. `TOUCHES` needs existing Component repo/path-prefix metadata; the deployment producer creates Component identity but does not populate a service catalog's path prefixes. Do not promise general file-to-service impact without a supported catalog producer and proof.

Lifecycle vocabularies are also broader than events. `request.created` leaves Request new; no automatic request triage/acceptance/done is promised. `requirement.changed` leaves Requirement proposed; IMPLEMENTS/VERIFIES do not promote it to implemented/verified. DesignApproval records an exact `APPROVES` assertion; it does not itself transition DesignElement to approved. `decision.recorded` accepts a Decision and supports supersession, not a dedicated reversal action. Authored Lessons stay tentative even with confirmed support. Incident resolution is explicit; mitigation/postmortem completion have no listed producer. Failed, cancelled, errored and skipped TestRuns remain distinct from success.

## Common payload, read and worker contract

Each sequence below denotes normalized `POST /v1/events` input, not a new native integration. Freeze full UUID envelope, timezone-aware `occurred_at`, `session_id`, `agent_id`, `trace_id`, `payload_ref`, source authority and payload using the [existing event API](../../../../src/context_graph/api/routes/events.py) and [Event model](../../../../src/context_graph/domain/models.py). The examples show domain payload fields; they are not complete request bodies. Native tenant webhooks remain unsupported in TV. Use unique event UUIDs per step, reuse the exact full request for a duplicate, and alter content under the same UUID only for an explicit conflict probe.

`A(intent, seeds, question)` means `POST /v1/query/artifacts` with `{query, intent, seed_node_ids}` ([route](../../../../src/context_graph/api/routes/artifacts.py)). Its PDLC intents are `incident`, `trace`, `completeness`, `status`, `impact`, `preflight`, plus supported core intent additions. `S(intent, owner, session, seeds, question)` means `POST /v1/query/subgraph` with `{query, intent, agent_id, session_id, seed_nodes}` ([route](../../../../src/context_graph/api/routes/query.py)). Use S for `beliefs`, `goals`, `when` and exact Event reads; do not send PDLC `trace` as the subgraph enum. `R(spec,version,local)` denotes `{spec_id,spec_version,local_id}`; `D(doc,section,version)` denotes `{doc_id,section_path,version}`. Freeze actual canonical node IDs using pack identity rules before execution. Artifact queries accept explicit IDs and independently support text seeding; test natural-language-only discovery separately from seeded traversal.

Every accepted step needs exact ledger receipt, projected Event, correct artifacts and complete stored source evidence; every rejection needs forbidden-write checks. P implicitly supplies artifact `DERIVED_FROM`; reference-only placeholders are not observed artifacts and have no observation provenance until filled. Artifact responses may attach newest source provenance rather than return every stored evidence edge; Memory provenance anchors to creation and exposes lifecycle evidence separately. Freeze expected **API** and independent storage evidence sets separately instead of assuming one equals the other. Domain graphs can exceed query depth/node budgets; record truncation and do not interpret omitted artifacts as absent. Public tenant cursors are refused.

Five loops are shared, always run tenant-bound, and an ACK is not an artifact proof:

- **G** graph projection: Core Event/evidence, matching deterministic PDLC rules, explicit Memory actions.
- **E** session extraction: Core Entities on applicable session extraction triggers; B has no User profile/preference/skill output. It is not a PDLC or Belief/Goal producer.
- **N** enrichment: event-type/tool keywords, hint/default importance and optional embeddings; event annotation is not semantic understanding (EV).
- **C** consolidation: scheduled Summaries and complete Memory Episode snapshots; record schedule/threshold/provider and wait for exact membership, not lag alone. Defaults are six hours/threshold150; earlier small-fixture proof used 20 seconds/threshold5, which is not default latency.
- **X+** pack extraction applies only to P's selected prose sources: `pdlc.design.section_changed`, `pdlc.spec.approved`, `observation.input`. Matching nonempty text calls the configured model and validator; allowed proposals are Decision/Constraint/Lesson and IMPLEMENTS/AMENDS/APPLIES_TO/VERIFIES within permitted endpoints. Inferred links remain proposed with confidence; they are not confirmed declarations. **X0** means no selected profile for the events in that journey. All other loops still run; E/C work is trigger/schedule dependent. A provider initialized or a no-op ACK is not X+ evidence. See [worker](../../../../src/context_graph/worker/pack_extraction.py) and [profile validator](../../../../src/context_graph/domain/pack_extraction.py).

All candidates inherit prerequisites **P0**: approved run/target preservation, exact source/bundle pins, public tenant launch/access/source mapping, five-loop diagnostics, query bounds, independent expected/forbidden sets, actual-provider versus scripted labeling and no User output. Additional prerequisites are named per candidate. Priority **P1** is a central pilot journey; **P2** extends useful breadth or checks a product boundary. Nothing authorizes execution.

## Family 1 — product planning, revision and decision history

### B01 — Bulk-export request becomes a traceable specification

- **Story / sequence:** Product asks for an auditable CSV export. Send `request.created {source_system:"product",external_id:"EXP-1",title:"Audit CSV export"}`; `spec.changed {doc_id:"export-prd",version:"1",title:"Audit export",acceptance_criteria:"Only workspace-authorized rows"}`; `spec.approved` for that revision with `request_system:"product",request_ids:["EXP-1"]`; `requirement.changed {spec_id:"export-prd",spec_version:"1",local_id:"authorization",statement:"Export only workspace-authorized rows"}`. Create separate `product/REPORT-1` request as a control.
- **Read / result:** A(`trace`, Request/Spec IDs, “Which approved specification refines EXP-1 and what requirements belong to it?”); separately text-only “Audit CSV export”. Expect Request, approved Spec, proposed Requirement, Spec→Request and Requirement→Spec `REFINES`, their exact Events. No inferred Request accepted/done, no authorization enforcement claim, no unrelated REPORT-1.
- **Workers:** G,N; E/C conditional; X+ on `spec.approved`, X0 on other steps. Preserve extraction proposals separately from declared trace.
- **Verdict / priority / prerequisites:** current contract / new proof for request trace (G07-A; planning component G02 representative), P1; P0 plus normalized product-source ownership and exact declared payload/read expectations.

### B02 — Feature architecture through explicit HLD and LLD

- **Story / sequence:** Build export streaming with bounded memory. After B01, send `design.section_changed D("export-hld","streaming","1")` with `kind:"hld",body:"Stream authorized rows in bounded batches",requirements:[R("export-prd","1","authorization")]`; then LLD D(`export-lld`,`cursor`,`1`) with `kind:"lld",body:"Advance cursor after durable batch write",refines_designs:[D("export-hld","streaming","1")]`, same requirement reference.
- **Read / result:** A(`trace`, authorization Requirement ID, “Which HLD and LLD refine this export requirement?”), then reverse seed LLD. Expect exact versioned DesignElements and declared `REFINES`, never a similarly worded analytics design. Extracted Decision/Constraint/links may be proposed only with own evidence and allowed types.
- **Workers:** G,N; E/C conditional; X+ on both design sources, require actual model/validator outcomes rather than initialized-client evidence.
- **Verdict / priority / prerequisites:** verified representative (G02/G03), fresh combined proof required, P1; P0+B01, real-provider quality expectations and proposal acceptance rubric.

### B03 — Approved design revised without inherited approval

- **Story / sequence:** Reviewer accepts export HLD v1. Send `design.approval_recorded {approval_id:"export-hld-v1-review",reviewer:"Priya",doc_id:"export-hld",section_path:"streaming",version:"1",verdict:"approved"}`; then design v2 with `supersedes_version:"1",body:"Use smaller batches under memory pressure"`. Later optionally approve v2 with a distinct approval_id.
- **Read / result:** A(`status`, both design revisions, “What is current and which exact revision did Priya approve?”); A(`trace`, v1, “Show its approval evidence”). Expect v2→v1 `SUPERSEDES`, approval→v1 `APPROVES`; no v2 approval before its own event, no cryptographic reviewer authentication, no DesignElement approved state invented from edge existence.
- **Workers:** G,N; E/C conditional; X+ only for revised design, X0 approval.
- **Verdict / priority / prerequisites:** verified representative (G02 approval/revision), P1; P0+B02; select whether approved-state wording is merely source assertion or a separately scoped product requirement.

### B04 — Design reversal recorded as explicit decision supersession

- **Story / sequence:** Team first selects synchronous exports, then chooses queued jobs. Send `decision.recorded {statement:"Export requests run synchronously",rationale:"Small initial datasets",applies_to_node_ids:[<export HLD v1>]}`; then `{statement:"Queue exports as background jobs",rationale:"Large workspaces exceed request deadlines",supersedes_hash:sha256(first statement),applies_to_node_ids:[<export HLD v2>]}`. Cite the current decision via `spec.approved.cited_node_ids` on a later export Spec revision.
- **Read / result:** A(`status`, both Decision IDs, “Which export decision is current and what did it replace?”); A(`status`, later Spec ID, “Which decision does this revision cite?”). Expect accepted current Decision, explicit `SUPERSEDES`, scoped confirmed `APPLIES_TO`, Spec→Decision `CITES` with pinned position. “Reversal” describes the human story; do not invent reversed lifecycle, `AMENDS` or causal link from rationale.
- **Workers:** G,N; E/C conditional; X0 decisions, X+ cited approved Spec. Deterministic and extracted matching text may share content-hash identity; inspect source set.
- **Verdict / priority / prerequisites:** current contract / new proof (P/G07-A), P1; P0+B03, independently precomputed statement hashes and exact referenced IDs.

### B05 — Requirement revision stays distinct through a scope change

- **Story / sequence:** Export initially permits all supported columns; privacy review narrows it. Send Spec v2 via `spec.changed {doc_id:"export-prd",version:"2",title:"Restricted audit export",supersedes_version:"1"}`; a new `requirement.changed R("export-prd","2","authorization")` with revised statement; HLD v2 references the new requirement explicitly. Retain v1 ticket/test references.
- **Read / result:** A(`status`, Spec v2, “What specification was superseded?”); A(`trace`, each Requirement revision in separate reads, “Which work/tests reference this exact revision?”). Expect distinct Requirement identities and explicit declared links, Spec supersession history. No inherited implementation/test coverage/approval, no automatic Requirement retirement or migration of links to v2.
- **Workers:** G,N; E/C conditional; X+ HLD, X0 spec.changed/requirement.changed.
- **Verdict / priority / prerequisites:** verified representative for versioning/controls (G02/G05); current contract / new proof for this revision-specific chain, P1; P0+B02 plus frozen v1/v2 read sets.

### B06 — Prose yields proposals with an honest confidence boundary

- **Story / sequence:** In a design review, submit `observation.input` text “For export jobs we choose bounded batches because memory is limited; avoid buffering whole workspaces.” Follow with a supported session-end trigger. Independently provide an explicit `decision.recorded` only if the producer actually asserts acceptance; do not use it to hide failed prose extraction.
- **Read / result:** A(`status` or `preflight`, known export design ID, “What proposed decisions or constraints affect this design?”), plus separate text-only discovery. Require actual X output, validated Decision/Constraint/Lesson if generated, own `DERIVED_FROM`, proposed allowed links/confidence. No guaranteed extraction of every clause, no inferred `CONSTRAINS`, no confirmed link from model confidence, no automatic Belief/Goal.
- **Workers:** G,N,E after trigger,C scheduled,X+ observation; no User outputs. Evaluate model quality separately from CV's frozen-output plumbing proof.
- **Verdict / priority / prerequisites:** product decision / new proof for useful prose acceptance; verified representative plumbing (CV/G02/G05), P1; P0, real model/cost credentials, rubric and expected honest empty/invalid/provider-failure responses.

## Family 2 — implementation, review and verification

### B07 — Work breakdown and explicit implementation trace

- **Story / sequence:** Split export work into a queue task and worker task. Send `ticket.created {tracker:"jira",key:"EXP-10",title:"Export delivery",work_type:"epic",status:"To Do"}` and child `EXP-11 {parent_key:"EXP-10",work_type:"task",requirements:[R("export-prd","2","authorization")],designs:[D("export-lld","cursor","1")],status:"To Do"}`; update child to `"In Progress"`; create/update `change {repo:"pilot/export",number:17,work_items:[{tracker:"jira",external_key:"EXP-11"}],head_sha:"exp17a"}`; close child with `status:"Done",resolution:"Implemented"`.
- **Read / result:** A(`trace`, Requirement and Change separately, “Which ticket and PR implement the exact export requirement?”). Expect parent→child `DECOMPOSES_INTO`, child→Requirement/Design and Change→child `IMPLEMENTS`, WorkItem done only from its event. Ticket done does not mean requirement verified or Goal completed; parent does not auto-complete.
- **Workers:** G,N; E/C conditional; X0 for all listed work/change events.
- **Verdict / priority / prerequisites:** verified representative explicit links (G03); current contract / new proof ticket lifecycle (G07-B), P1; P0+B05 and the frozen lifecycle/read oracle.

### B08 — Requested changes and approval are separate historical records

- **Story / sequence:** Export PR17 receives `change.reviewed {repo:"pilot/export",number:17,review_id:"review-a",reviewer:"Alex",verdict:"changes_requested"}`, update with new head SHA, then separate `review-b` by Robin with verdict approved; add a commented review if useful.
- **Read / result:** A(`trace`, PR17, “Who reviewed this export PR and what did each review say?”). Expect separate Review nodes, exact reviewer/verdict and `REVIEWS`, Change reviewed only where lifecycle allows. Do not erase changes_requested, invent an aggregate approval gate, or claim reviews are bound to a head SHA: this review payload has no reviewed-commit field.
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** verified representative (G03/G05), P1; P0+B07; product decision if current-commit approval is a pilot requirement rather than displaying declared review history.

### B09 — Abandoned prototype, reopen and merged-state guard

- **Story / sequence:** Search-ranking experiment PR18 is abandoned, later reopened, updated and merged. Send `change.created {repo:"pilot/search",number:18,title:"Ranking prototype"}` → `change.abandoned` → `change.created` → `change.updated` → `change.merged {merge_sha:"search18m"}` → late `change.abandoned`. Separately close a search ticket with `status:"Won't Do",resolution:"Experiment cancelled"`.
- **Read / result:** A(`trace`, PR18, “What is the prototype state and which events support it?”). Expect one Change, allowed abandon/reopen transitions, final merged state preserved against late abandonment; cancelled WorkItem distinct from done. This does not prove event-time ordering; older distinct updates may still overwrite text according to delivery-order policy (G01).
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** current contract / new proof (G07-B; G01 late-update representative), P2; P0, exact delivery order and lifecycle oracle frozen.

### B10 — Commit-only tooling work has a bounded knowledge model

- **Story / sequence:** A library maintainer sends `change.committed {repo:"pilot/sdk",subject:"fix(retry): respect retry budget (#31)",body:"SDK-31\nReviewers: Sam",files:["src/retry.py"]}`, after a real Jira SDK-31 ticket. Then send a no-PR commit `{repo:"pilot/sdk",subject:"MINOR: refresh generator",body:"SDK-32\nReviewers: Lee",files:["tools/generate.py"]}`.
- **Read / result:** A(`trace`, SDK PR31 ID, “Which declared ticket does this commit identify?”); S(`general`, owner/session, second Event UUID, “Show the generator activity Event”). Expect PR-suffix Change/ticket declaration; commit reviewer text may create bounded Review records but **no `REVIEWS` link or authenticated reviewer approval**. No-PR case is Event/ledger-only, no invented Change or ticket link; public Event view does not expose full raw payload/payload_ref. See [G07 commit tests](../../../../tests/unit/test_g07_ticket_lifecycle.py).
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** current contract / new proof, plus product decision if commit-only artifact retrieval is required (G07-B), P2; P0, accepted limits on Event-only recall.

### B11 — Regression failure, success and skipped execution remain honest

- **Story / sequence:** SDK retry requirement R(`sdk-prd`,`1`,`retry-budget`) is implemented by PR31. Send `testcaserun.finished` with `{repo:"pilot/sdk",test_id:"retry_budget",run_id:"sdk-run-fail",outcome:"failure",commit_sha:"sdk31a",change_number:31,requirements:[R(...)]}`; a distinct success run at `sdk31b`; `testcaserun.skipped {repo:"pilot/sdk",test_id:"retry_budget",run_id:"sdk-run-skip",outcome:"skipped",commit_sha:"sdk31c",change_number:31}`. Optional distinct finished cancel/error runs exercise remaining allowed outcomes.
- **Read / result:** A(`trace`, Requirement/PR31, “Which declared test checks the retry requirement, and what outcomes occurred?”). Expect TestCase `VERIFIES` only from supported explicit finished requirement reference, each TestRun `EXECUTES`, optional `RAN_AGAINST` with declared SHA, all outcomes distinct. VERIFIES denotes coverage, not passing; skip creates no requirement coverage; later success does not erase failure or prove all commits pass. TestRun identity is run_id alone: use unique run IDs within B.
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** verified representative finished failure/success (G03/G05); current contract / new proof skipped/cancel/error combinations (G07-C), P1; P0+SDK planning through normal events; exact SHA/outcome oracle.

### B12 — Production hotfix with independent operational and work claims

- **Story / sequence:** A billing rounding bug needs urgent correction. Create `ticket.created {tracker:"jira",key:"BILL-9",work_type:"bug",status:"In Progress",title:"Correct invoice rounding"}`; `change.created {repo:"pilot/billing",number:9,work_items:[{tracker:"jira",external_key:"BILL-9"}]}`; review, failure/success TestRuns at separate SHAs, merge, and ticket.closed Done. Do not manufacture a requirement if none was authored.
- **Read / result:** A(`trace`, BILL-9/PR9, “What review and test evidence exists for the hotfix?”); A(`completeness`, relevant seeds, “Which changes have no reviews?”). Expect real ticket/change/reviews/runs, confirmed explicit ticket link, honest absent requirement trace. Completeness means missing supported topology, not business readiness or all CI checks green.
- **Workers:** G,N; E/C conditional; X0. C may create a hotfix Episode from the source Events later.
- **Verdict / priority / prerequisites:** verified representative components (G03/G05), current contract / new proof hotfix composition, P1; P0, ticket-exemption/product acceptance for work without authored requirements.

## Family 3 — release, deployment and incident response

### B13 — Library release ships without implying a deployment

- **Story / sequence:** SDK PR31 merges with `merge_sha:"sdk31m"`; send `release.published {repo:"pilot/sdk",version:"2.3.0",has_breaking:false,entries:[{pr_number:31,section:"fixed"}]}`. Publish another release with empty entries as control.
- **Read / result:** A(`trace`, SDK Release, “Which changes are included in SDK2.3.0?”), reverse seed PR31. Expect Release→Change `INCLUDES` with section fixed and exact source Events. No Deployment because a library release is not a service deployment; no inferred inclusion from version wording, no guessed link for empty entries.
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** verified representative (G04/G05), P1; P0+B10/B11 and section enum validation expectations.

### B14 — Failed production release followed by a separate successful attempt

- **Story / sequence:** Export PR17 merges at exp17m; publish `pilot/export@1.0.0` explicitly including17. At t1 send `service.deployment_failed {repo:"pilot/export",service:"export-api",environment:"production",artifact_id:"exp17m",release_version:"1.0.0",change_numbers:[17]}`; at t2 send service.deployed with same payload; at t3 deployed to staging. Distinct `occurred_at` values identify distinct attempts.
- **Read / result:** A(`trace`, PR17/Release, “Where was export1.0.0 attempted, and which attempt failed?”). Expect distinct Deployment keys `(repo,service,environment,artifact_id,started_at)`, failed/succeeded statuses, `DEPLOYS` Change/Release and `DEPLOYED_TO` Component with environment. No merge/release⇒success, no failure erased by retry. Same exact key cannot distinguish independent attempts: producer timestamps are material.
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** verified representative (G04/G05), P1; P0+B07, timestamp/attempt normalization policy.

### B15 — Regression rollback targets the exact deployment attempt

- **Story / sequence:** A later export deployment at t4 regresses pagination. Send `service.rolledback {repo:"pilot/export",service:"export-api",environment:"production",artifact_id:"exp17m",target_started_at:t4}`. Keep t2 and another repository's same-SHA/time deployment as controls. Separately submit an unknown exact rollback target, then its matching deployment event to exercise reference fill.
- **Read / result:** A(`trace`, DeploymentRollback/Event-derived ID and target, “Which exact attempt was rolled back?”). Expect `DeploymentRollback` keyed by rollback Event UUID, `ROLLS_BACK` only to exact target, target rolled_back and retained history, no sibling-state changes. Unknown target is reference-only with no observed success before fill; later fill must preserve rollback evidence/state per current contract. Rollback does not assert a replacement version was deployed or an incident resolved.
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** current contract / new proof (G07-D), P1; P0+B14, exact canonical UTC target time, frozen unknown-target expectations.

### B16 — Upgrade plus incident occurrence is distinct from cause

- **Story / sequence:** Billing PR9 deploys, then `service.upgraded {repo:"pilot/billing",service:"billing-api",environment:"production",artifact_id:"bill9m",change_numbers:[9]}` at a new time. Send `incident.detected {repo:"pilot/billing",service:"billing-api",incident_id:"INC-9",description:"Invoice timeouts",environment:"production",artifact_id:"bill9m"}` after the upgrade, then `incident.reported` for the same identity; include an incident in another repo/service with same incident_id.
- **Read / result:** A(`incident`, INC-9, “Which deployment was this billing incident reported on?”). Expect upgrade `operation:upgrade`, succeeded deployment, Incident→Component `AFFECTS`, `OCCURRED_ON` scoped latest deployment at/before incident time; detected/report events share Incident identity. No `ATTRIBUTED_TO` cause inferred from proximity, and report text alone does not remediate/resolve anything. Component identity is catalog_name alone: choose explicit unique service names where actual components differ.
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** verified representative incident scope/occurrence (G06); current contract / new proof upgrade (G07-D), P1; P0+B12, normalized deployment time and service-catalog naming policy.

## Family 4 — missing knowledge, traceability and scope collisions

### B17 — References arriving before artifacts remain visibly incomplete

- **Story / sequence:** Search LLD D(`search-lld`,`ranker`,`1`) explicitly refines missing HLD D(`search-hld`,`ranking`,`1`); create search ticket SRCH-12 naming a missing Requirement R(`search-prd`,`1`,`latency`); then deliver the real HLD/Requirement and Spec through supported events. In a separate branch of this story, a task description says “depends on indexing task SRCH-13” without a supported dependency field.
- **Read / result:** A(`trace`, LLD/ticket, “Which referenced design and requirement have arrived?”), before/after. Expect identity-only stubs before observation, same IDs filled later, links retained, provenance only from actual artifact Events. A(`impact`, SRCH-12, “What depends on this task?”) cannot promise a DEPENDS_ON edge from description or arbitrary extra payload. No completion/content/source fabricated for a missing target.
- **Workers:** G,N; E/C conditional; X+ design, X0 ticket/requirement/spec.changed. X+ does not include DEPENDS_ON.
- **Verdict / priority / prerequisites:** verified representative reference filling (G02/G04); **gap** for deterministic dependency creation, P1; P0, late-order fixture and product decision whether dependency analysis is essential or explicitly out of pilot scope.

### B18 — Missing coverage differs from proposed coverage and failing execution

- **Story / sequence:** Create search requirements latency/quality/privacy under one Spec. Declare one test→latency requirement reference using testcaserun.finished outcome failure. Leave privacy with no test reference. For quality, a matching design prose event may yield an allowed proposed VERIFIES link only if the real provider actually emits and validates it; do not insert one manually or assume co-change creates it.
- **Read / result:** A(`completeness`, bounded Spec/requirements, “Which requirements have no tests or only proposed tests?”), plus A(`trace`, latency, “What happened when its test ran?”). Require classification by existing plugin semantics and exact edge status; no_link/proposed_only/confirmed must not be collapsed into passed/failed. No verdict that privacy is unimplemented merely because a bounded query omits it. The three-category model is a contract to verify, not a cloud result inherited from G07-C (which excludes whole-plugin proof).
- **Workers:** G,N; E/C conditional; X+ quality design only, otherwise X0.
- **Verdict / priority / prerequisites:** current contract / new proof for completeness usefulness, product decision for probabilistic proposed-only case, P1; P0, independently inspect/freeze plugin output semantics and actual provider expectation before claiming all categories.

### B19 — Same numbers across repositories and colliding deployment fields

- **Story / sequence:** Create/merge PR17 in `pilot/export` and `pilot/search` with different content/tickets; publish each repo's `1.0.0`; deploy each with same environment, artifact_id and occurred_at but distinct repo/service where applicable. Create an unrelated in-repo PR18 with overlapping “production export” wording. Also exercise a deployment before matching merge with declared merge SHA to test later match linking.
- **Read / result:** Separate A(`trace`, exact PR17 IDs, “Where is this exact change deployed?”), then text-only “export delivery”. Expect repo-scoped Changes/Releases and scoped Deployments, appropriate explicit/matching `DEPLOYS`, no loose-word widening into unrelated PR18 once exact identity resolves (G05). Same PR number is safe across repos; same TestRun run_id or approval_id within B is **not** repo-scoped and must be unique. No global same-number semantic joins.
- **Workers:** G,N; E/C conditional; X0.
- **Verdict / priority / prerequisites:** verified representative scoped identities, seed isolation and late deployment/merge linking components (G01/G04/G05), fresh combined proof required, P1; P0, collision matrix and canonical IDs frozen independently.

### B20 — Incident remediation, resolution and reused lesson form separate claims

- **Story / sequence:** For billing INC-9, create corrective PR10. Send `incident.remediation_recorded {change:{repo:"pilot/billing",number:10},incident:{repo:"pilot/billing",service:"billing-api",incident_id:"INC-9"}}`; merge PR10; inspect still-unresolved incident; send `incident.resolved {repo:"pilot/billing",service:"billing-api",incident_id:"INC-9",summary:"Timeout rate returned to baseline"}`; author `incident.lesson_recorded {statement:"Bound invoice fanout before enabling large workspaces",incident:{...},change:{repo:"pilot/billing",number:10},link_status:"confirmed"}`. Later approved Spec `billing-prd@2` names `lesson_refs:[{content_hash:sha256(lesson_event_uuid)+":authored"}]`.
- **Read / result:** A(`incident`, INC-9, “What corrective change and resolution were explicitly recorded?”); reverse A(`trace`, PR10, “Which incident does this fix declare?”); A(`incident`, later Spec/Lesson, “Which future specification cites this lesson?”) with separate bounded seeds if depth requires. Expect `REMEDIATES`, independent resolved lifecycle/source, tentative Lesson `LEARNED_FROM` Incident/Change and Spec `CITES` with pinned position. No fix⇒cause, merge⇒resolution, confirmed link⇒validated Lesson, or same prose⇒automatic lesson reuse. Relation-only Events need their own source_event_id/pinned_position evidence, not fabricated artifact observation provenance.
- **Workers:** G,N; E/C conditional; X+ later spec.approved only, other steps X0. Extracted Lessons and authored event-hash Lessons are not automatically semantic aliases.
- **Verdict / priority / prerequisites:** verified representative (G06), P1; P0+B16, exact authored hash computation and explicit reuse statement.

## Family 5 — explicit Memory and temporal recall alongside development

### B21 — A development assumption is stated, confirmed and corrected explicitly

- **Story / sequence:** During export planning owner `dev-export` states `memory.belief.stated {key:"batch-size",scope:"agent",belief_text:"Batches of 10000 fit the memory budget",category:"world_model",confidence:0.6}`; separately submits `memory.belief.inferred {key:"compression-benefit",scope:"agent",belief_text:"Compression may lower transfer cost",category:"world_model",confidence:0.4}`. Confirm batch-size with `expected_revision:0`; state replacement key `batch-size-small` with text “Use batches of 1000 under the measured budget”; correct old key with `expected_revision:1,replacement_key:"batch-size-small",contradicts:true`.
- **Read / result:** S(`beliefs`, dev-export, later session, no seeds, “What are my current export assumptions?”), then S(`when`, same owner, originating session, relevant IDs, “How did the batch-size assumption change?”). Expect agent-scoped current replacement, inferred origin with zero initial supporting confirmations, stated origin with one initial distinct support, confirmation/correction revisions, actual `SUPERSEDES`/explicit `CONTRADICTS` and evidence. No automatic Requirement→Belief or Decision→Belief edge; confidence is an assertion, not measured truth. Retry confirmation must not add support.
- **Workers:** G applies atomic Memory actions,N; E/C conditional; X0 Memory events. PDLC view remains separately retrievable.
- **Verdict / priority / prerequisites:** verified representative (MV/CV/TV), fresh developer-story proof required, P1; P0, owner/application mapping, exact replacement creation and state_revision oracle; no claim agent_id authenticates a human.

### B22 — Delivery goal completes only on its declared action

- **Story / sequence:** Send `memory.goal.created {key:"ship-export",scope:"agent",description:"Deliver export to production",priority:8}` under dev-export. Run B11/B14 passing tests and successful deployment. Read Goal still active; only then submit `memory.goal.completed {key:"ship-export",scope:"agent",expected_revision:0}`. Another owner may use the same key with different content as a positive isolation control.
- **Read / result:** S(`goals`, dev-export, next session, no seeds, “Is my export delivery goal complete, and which action says so?”); A(`trace`, export PR, “What deployment evidence exists?”). Expect explicit active→completed state/revision and exact lifecycle source; domain Events do not complete Goal. Evidence intersection may explain co-occurrence, but no invented Goal→Change/Requirement relationship or automatic PURSUES from an unauthored owner Entity.
- **Workers:** G,N; E/C conditional; X0 unless the separate domain journey has selected prose. C groups source Events by time, not goal causality.
- **Verdict / priority / prerequisites:** verified representative (MV/CV/TV), P1; P0+B14, owner scope and exact terminal-event authority.

### B23 — Abandoned and superseded plans preserve explicit history

- **Story / sequence:** Search prototype Goal `ranker-v1` is created then `memory.goal.abandoned {key:"ranker-v1",expected_revision:0}` in its session. Separately create `ship-search-v1` and replacement `ship-search-v2` under the same owner/scope, then `memory.goal.superseded {key:"ship-search-v1",expected_revision:0,replacement_key:"ship-search-v2"}`. Abandon the PDLC prototype Change via B09 separately; do not couple states.
- **Read / result:** S(`goals`, search owner/session, no seeds, “What search goals remain current?”) and S(`when`, same scope, old IDs, “Which goal was abandoned or replaced?”). Expect abandoned versus superseded statuses and evidence, replacement `SUPERSEDES` history, current recall excluding superseded records according to MV. Do not label abandoned active, infer completion, supersede an already terminal Goal, or invent goal linkage from matching PR title.
- **Workers:** G,N; E/C conditional; X0 for explicit Memory and Change lifecycle inputs.
- **Verdict / priority / prerequisites:** verified representative (MV), fresh combined proof required, P2; P0, same-owner replacement and exact revision expectations, session versus agent scope explicitly chosen.

### B24 — Session Episodes bridge planning and operations through actual Events

- **Story / sequence:** In `export-debug`, record design/change/test/incident/explicit Memory activity at minutes0 and5, then minute40. Require consolidation snapshots after each declared stage. Deliver a late `observation.input` at minute20 to bridge the temporal gap. End session through supported trigger; another session with overlapping export wording is a positive control.
- **Read / result:** S(`when`, export owner, export-debug, no seeds, “What happened during the export debugging session?”); separately A(`incident`/`trace`, exact domain IDs, “What does the domain evidence say?”). Expect exact source-event membership, Episode `CONTAINS`/`DERIVED_FROM`, stored Summary evidence and `SUMMARIZES` Episode, old and new membership snapshots retained after bridge. Require complete snapshots; no fabricated latest-only partition, thematic/causal episode claim, Episode→Change/Goal semantic edge, or foreign-session inclusion. Narrative Summary quality is separately evaluated against actual source Events.
- **Workers:** G,E on session trigger,N,C required; X+ observation/design and any approved Spec, X0 other inputs. Capture exact C cadence/threshold and source projection convergence; zero lag alone cannot establish the final Summary/Episode.
- **Verdict / priority / prerequisites:** verified representative (MV late bridge, composition and ownership controls), fresh multi-domain/provider quality proof required, P1; P0, elapsed-time fixture/cadence plan and distinct expected membership sets for each snapshot.

## Candidate selection, shared negatives and unresolved prerequisites

For a compact first implementation specification, retain B01–B08, B11–B16, B17–B22 and B24 as central P1 candidates; B09/B10/B23 add useful breadth without being silently treated as guaranteed full artifact support. These priorities do not authorize running any subset or waive required original scope. Several candidates share prerequisites and artifacts: export B01→B02→B03/B05→B07/B08→B14/B15; SDK B10→B11→B13; billing B12→B16→B20; explicit Memory B21–B24 overlays these through source Events, not invented joins. The search story supplies independent revisions, incomplete knowledge and cancellation controls.

Attach these shared negatives to actual journeys instead of padding the catalog with isolated checks:

1. Under TV's one public dispatcher, interleave representative B01/B14/B21 with Tenant A; reuse selected Event/session/agent/Entity/Memory identities with different tenant content. Positively retrieve each tenant's own data, then foreign-only Event/artifact lookup negatives. Same IDs across databases are safe by binding, not global merging. A has no PDLC; B has no User. Do not replace natural-language or exact-ID proof with the other.
2. Exact duplicate201 versus conflicting-ID409; malformed required/nested references422; disabled capability422, with independently frozen forbidden effects. A transport acceptance is not processing completion. Record expected Memory state conflicts separately from HTTP admission conflicts; action conflict may be a worker disposition after accepted ledger append.
3. Freeze a representative provider failure on B06/B24, selected model quality expectations, bounded truncation and cooperative stop/restart probes separately. Prior scripted provider and cooperative restart evidence is not general pending/SIGKILL recovery or real-provider quality proof. No public tenant cursor, native webhook routing, streaming import or unimplemented maintenance workaround.
4. P0 launch/onboarding, trusted source normalization, explicit `agent_id` policy, approval identity wording, real-provider access/costs, exact bundle/evaluation gate, diagnostics and retained-target preservation still need a reviewable final specification. Existing APIs/workers are stopped, TV datasets retained; no assumed live endpoint or authorized reset. Monitoring export403 remains a named readiness question if monitoring is required.

The most material new decisions are whether deterministic dependency/ownership/file-impact knowledge is required (current producer gaps), whether approvals must bind authenticated humans/current commit (not established by source fields), whether commit-only work needs a domain artifact (currently Event-only without PR suffix), and what real-provider usefulness means for proposed links and Summaries. Resolve those before promising their results. This document neither invents missing producers nor expands into migration, hierarchy authorization, ANN/load work or a new Memory framework.
