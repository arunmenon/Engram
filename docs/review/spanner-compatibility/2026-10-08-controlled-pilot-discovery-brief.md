# Controlled developer pilot: requested scope and prerequisite assessment

## Current pilot scope for stakeholder review — 15 October 2026

This section supersedes the historical prerequisite/status descriptions below. It is a scope proposal, not approval to run the pilot. No pilot run, deployment, database reset or new feature work is started by this review.

### Guide and execution entry — 15 October 2026

The stakeholder approved the eight-page pilot chapter and starting execution through readiness checks. [Open the versioned architecture/pilot guide](../../guide/engram-architecture.html): pilot pages20–27 include the49journey catalog,18shared probes, worker/read explanations and reproduction requirements. Source is docs/guide/engram-architecture.html; pilot content template and plain-language journey explanations live beside it. Rebuild embedded catalogs/navigation with `python3 scripts/build_pilot_guide.py` from the repository root. The HTML template is not a standalone guide.

The [first checkpoint specification](pilot-readiness-2026-10-15/entry-checkpoint.md) records exact approved targets, retained-state safeguards, real-provider limits, review and repeat instructions. It is an entry stage, not completion of the49-journey pilot. External cohort onboarding and independent developer reproduction remain required later.

15 October execution: the [entry checkpoint failed and stopped](pilot-readiness-2026-10-15/verification.md). Nine Events were accepted with actual providers, but the runner's completion-call ceiling and retained accelerated consolidation prevented full processing/retrieval verification. Original ledger/owners survived; older derived Summary content changed, failing the preservation oracle. A pending extraction remains retained. Reconcile the bounded consolidation/preservation/budget policy before recovery or retry; this is not a complete pilot result.

### What the recent projection work changes

The pilot asks whether developers can submit realistic activity, obtain the right knowledge and retrieve its evidence through supported Engram entry points. We reuse the verified foundation rather than repeat an open-ended assessment.

| Capability now established for bounded cases | Evidence | What the pilot still needs to establish |
|---|---|---|
| Typed Memory Episodes, Beliefs and Goals are produced and retrievable | [Memory verification](memory-episodes-verification.md), later Belief/Goal sections | Use them in connected developer journeys; keep explicit producer assertions separate from prose inference |
| User identity, profile/personalization consistency, corrections and retry receipts | [User verification](user-attachment-verification.md) | Realistic multi-session and multi-person examples using actual configured extraction, with visible sources and honest failures |
| Enrichment survives projection ordering and preserves later adjustments | [Enrichment verification](enrichment-ordering-verification.md) | Confirm annotations and processing visibility for the actual pilot inputs; no claim of smarter keyword/importance inference |
| Shared workers respect five selected configurations; Entity links preserve canonical IDs | [Composition verification](pack-combination-verification.md) | Meaningful combined journeys, correct enabled outputs and absence of disabled outputs |
| One public authenticated dispatcher serves two pinned databases with distinct packs | [Tenant isolation verification](tenant-isolation-verification.md) | Developer-facing configuration, launch/onboarding and simultaneous realistic use; bounded isolation evidence is not a complete hosted-service release |

### Pilot participants and selected configurations

Propose a small controlled cohort using two simultaneous tenants. Participant names, hosting location and access duration remain to be chosen in the final specification.

| Tenant | Selected packs | Existing approved target | Purpose |
|---|---|---|---|
| A | Core + User + Memory | engram-assess-1010a-pdlc | Personal context, preferences, explicit beliefs/goals and session recall |
| B | Core + PDLC + Memory | engram-g07-target | Connected development artifacts plus explicit memory and session recall; User stays disabled |

Core-only, Core+User and Core+PDLC remain targeted controls from the completed matrix. Do not change a live tenant's packs to simulate these controls or erase retained data. Any additional configuration run needs its own declared scope and safe dataset preparation. Both current targets contain retained verification data; preserve it by the existing verified export/ownership process before any approved replacement. Other databases remain protected.

### What each worker contributes

These are five shared worker loops, not one worker per pack. Applicability comes from selected capabilities and matching inputs. An acknowledgement can mean no applicable work; it is not proof an artifact was created.

| Worker | Why it is there | Pilot proof |
|---|---|---|
| Graph projection | Builds common Event/evidence graph; applies PDLC rules and explicit Memory Belief/Goal actions | Exact types, stable identities, properties and source links for submitted events |
| Session extraction | Extracts core Entities; adds User profiles/preferences/skills when User is selected | Actual configured model, canonical Entity links, correct User owner/supports; no User outputs for B |
| Enrichment | Annotates Events with event-type/tool keywords, hint/default importance and optional embeddings | Eventually stored annotations despite ordering; distinguish metadata from semantic inference |
| Consolidation | Builds Summaries and, with Memory, exact Episode membership snapshots | Documented schedule/threshold, complete stored evidence, timeline retrieval and safe cooperative stop |
| Pack extraction | Uses selected prose extraction profiles, such as supported PDLC decisions/design content | A matching profile actually ran and its validated result/evidence is retrievable; unmatched inputs produce no claimed extraction |

Episode creation is scheduled; small pilot fixtures need explicitly recorded cadence/threshold settings. Memory does not automatically convert a PR or ticket into a Goal. PDLC artifacts and Episodes meet through their supporting Events; additional semantic links require declared, tested rules. Beliefs/Goals use explicit supported event contracts. A stated or confirmed belief is an attributed assertion, not verified truth.

### Expanded parallel discovery — 15 October 2026

The [expanded discovery inventory](pilot-discovery-2026-10-15/README.md) supersedes the starter lists below as candidate coverage: **25 Tenant A journeys, 24 Tenant B journeys and 18 separately counted shared probes**. It maps diverse stories to inputs, workers, supported reads, evidence and prerequisites, distinguishing prior representative proof, new pilot proof, gaps and product decisions. The short lists below remain introductory examples. Discovery authorizes no execution or implementation; detailed scope/specification is the next review gate.

### Tenant A journeys and retrieval checks

1. Introduce Alice, her role, interest and short-answer preference. Retrieve the profile/current preference with actual supporting observation evidence.
2. Introduce Bob with overlapping interests and a different preference. Positively retrieve Bob, then verify Alice's reads exclude Bob's facts. This is logical owner scoping inside one tenant, not hierarchy authorization.
3. Continue Alice's activity across sessions. Retrieve relevant earlier context with attributable source Events.
4. Correct Alice's preference in one context. Retrieve the current value and correction/history; another context remains unchanged. The authorized correction target must be explicit; do not claim arbitrary prose always infers it correctly.
5. State, confirm and correct a Belief using the supported Memory contracts. Retrieve exact support, revision/history and confidence semantics; retries do not increase support.
6. Create a Goal and explicitly complete or abandon it. Retrieve the declared state and evidence; do not infer completion merely because a test passed.
7. Build temporal Episodes and Summaries. Retrieve exact membership; deliver a late bridging observation and show the new snapshot alongside preserved history.
8. Retry unchanged input, submit changed content under the same identity and send malformed input. Check duplicate/conflict/rejection behavior and absence of unintended effects.

Example questions: "What is Alice's current answer-length preference, and why?", "What changed?", "What goal was completed and which event says so?", "What happened in the earlier session?" Map each question to the actual supported endpoint and intent; require a defined answer or honest unsupported response. These are proposed questions, not claims of unrestricted natural-language understanding.

### Tenant B journeys and retrieval checks

1. Rebuild a coherent password-reset feature through Engram: product request, PRD and requirements, with an unrelated feature as a control.
2. Add HLD/LLD, version-specific approval and a revision that does not inherit approval.
3. Link explicit work tickets and PRs; include same PR numbers in different repositories.
4. Record requested changes and approval separately; record passing, failing and skipped test runs without treating coverage as passing.
5. Record release, failed/successful deployment and rollback using actual supported contracts.
6. Record an incident, explicit remediation/resolution and a lesson cited by a later specification.
7. Ask connected questions across the chain in both directions, with exact returned artifacts and evidence and no unrelated-feature leakage.
8. Add explicit Memory Belief/Goal events and time-based Episodes. Retrieve both domain and memory views; never invent an automatic requirement-to-belief or PR-to-goal relationship.

Example questions: "Which PR implements the expiry requirement?", "Who reviewed it and what test outcomes exist?", "Where was that change deployed?", "Which incident was explicitly remediated?", "Which later specification cites its lesson?" Freeze supported queries and expected answers before execution. Include natural-language discovery separately from exact-ID traversal so one cannot conceal a failure in the other.

### Shared operational and isolation cases

Use colliding identifiers/wording on both tenants, foreign-only positive/negative read controls, invalid credentials/roles and spoofed routing attempts. Keep both tenants active during representative interleaved journeys. Check duplicate processing, bounded cooperative worker interruption/restart, a provider failure and honest truncation relevant to the actual journeys. Required probes must name exact failure injection, expected effects and recovery; general crash/pending recovery is not inherited from the earlier bounded proof.

### Prerequisites before starting

- Select the exact code commit, frozen pack versions, supported event inventory, participants and deployment topology. The verification APIs/workers are stopped; there is no assumed running pilot endpoint.
- Provide a documented clean-checkout launch path for the catalog, tenant-bound APIs and all five workers per tenant; verify a developer can follow it without private harness knowledge or graph repair.
- Configure reachable endpoints, transport/access controls, credentials, trusted producer/source mapping, provider credentials and permitted costs. Spanner runtime permission is already evidenced; new deployment/provider credentials are not assumed available.
- Define per-person/application mapping to agent_id. It is not automatically authenticated human identity. Define api/admin roles explicitly: direct User endpoints currently require admin; do not grant broad admin merely to obtain a passing pilot.
- Record Episode schedule/threshold, timeouts, query bounds, processing-completion criteria and supported failure responses.
- Expose sufficient pilot diagnostics for accepted/processed/pending/failed outcomes. Cloud Monitoring export currently fails403; either establish a bounded operational alternative or treat required monitoring as a readiness blocker.
- Inspect relevant open correctness issues against the selected journeys. Identify demonstrated pilot blockers; do not queue the entire backlog or infer all reliability work is complete.
- Freeze expected/forbidden outputs, provider behavior and exact evidence before inputs. Preserve retained datasets, prepare approved targets safely and publish repeat instructions.

### Verification and approval gates

Each required journey follows authenticated Engram HTTP writes -> actual Spanner ledger -> actual applicable workers -> Spanner graph -> Engram reads. Use actual configured providers where extraction/summary quality is being tested; scripted provider/fault cases remain separately labeled and cannot replace the real-provider journey. Read-only storage audits supplement API proof. No direct artifact inserts or manual repair count.

Deliver per-scenario expected/actual results, payloads/responses, worker outcomes, exact graph/evidence, repeat commands, retained failures/data, Astra review, stakeholder demo and actual GitHub reconciliation. Review retrieval usefulness separately from lifecycle/storage correctness. Missing required evidence or a required failed case blocks that readiness claim. New scope goes into a bounded ticket rather than silently expanding the pilot.

Next gate: stakeholder reviews this scope; then prepare the detailed pilot specification/tickets and prerequisite readiness check. Execution and developer onboarding require explicit approval. Hierarchy policies (#49), ANN/load benchmarks (#48), migration, hot pack switching, unimplemented tenant maintenance/import/cursors/native webhook routing, every possible pack combination and forced-termination guarantees remain outside this proposal. Reassess separately if a pilot developer needs one of them.

## Historical assessment and planning record — superseded where noted

13 October follow-up: the bounded [Memory remediation](memory-episodes-verification.md) now implements and verifies Episodes, Beliefs and Goals. Belief/Goal acceptance passed 138 live checks across core-only, core+Memory and core+PDLC+Memory; earlier Episode acceptance remains separately recorded. Astra found no remaining blocker for this scoped implementation. Original no-producer findings below are historical and superseded by that evidence. User attachment, enrichment ordering and public/concurrent tenant readiness remain separate pilot prerequisites; the pilot has not started.

Status update, 10 October 2026: stakeholder confirmed G7 complete and authorized the pack-composition assessment, including reuse of only the assessment database after verified exports. The [local and live assessment](2026-10-10-pack-composition-assessment.md) now records all five configurations attempted: enrichment persistence failed in core/PDLC cases, both user-enabled runs failed on Entity-interest provenance, and useful Memory production remains blocked. Sequential reuse does not prove concurrent tenant isolation. No runtime fixes or developer pilot have started. Historical planning below is preserved.

## Grounding review — completed, code inspection only

The approved Astra medium review is [preserved in full](2026-10-08-astra-pilot-composition-assessment.md).
Reviewed source: `51a680adeca608618e0e7905991037349631994e`. No tests or cloud
runs were performed. The coordinating agent spot-checked the pack bundle, memory
manifest, public tenant factory and profile-key/read-filter references. Source
inspection is not reproduction of the suspected runtime failures.

### Historical implementation facts from the 8 October assessment

- Explicit optional pack selection and immutable active bundles exist. Core stays
  mandatory; specialized user extraction has an actual enable/disable gate. Older
  claims that memory/user always load are stale at this revision.
- The five worker loops are projection, session extraction, enrichment,
  consolidation and pack extraction. Core summaries come from consolidation;
  they are not memory Episode artifacts. Session extraction still extracts core
  entities with user disabled; pack extraction runs only selected prose profiles.
- Memory declares Belief/Goal/Episode vocabulary but has no registered producer or
  projection/extraction rules. Selecting it does not automatically turn a ticket
  into a Goal or a session into an Episode, or join memory to PDLC artifacts.
- Public `create_tenant_app` deliberately refuses startup. Private bound tenant
  machinery and database fences are not a supported public two-tenant service.
- User preference extraction is LLM-driven, not a deterministic preference command.
  Its user identity follows the triggering `agent_id`, not automatically the
  authenticated human or each person mentioned in prose. That is an application
  mapping to specify, not an authorization guarantee.
- Event retrieval has an Entity-vector channel. Artifact retrieval uses domain
  keys/text/traversal, with no vector seed channel in inspected code. User endpoints
  are a third relevant read surface; compare them with personalization retrieval.

| Requested combination | Code-grounded baseline | What remains to prove or specify |
|---|---|---|
| core alone | Core Event/Entity/Summary processing; user extraction gated off | Exact core outputs, provider behavior and both APIs' unsupported/fallback responses |
| core+user | Adds specialized profile/preference/skill processing and user reads | Canonical profile identity, extraction/correction/retry behavior and consistent retrieval |
| core+user+memory | Same implemented producers as core+user; memory adds vocabulary | Minimum useful memory behavior, producer and evidence contract; absence is not memory-value success |
| core+PDLC | Core plus declared domain projection and selected prose extraction | Broader worker-order, evidence and read behavior beyond bounded G1–G6 evidence |
| core+PDLC+memory | Same implemented producers as core+PDLC; no automatic memory/domain join | Chosen memory producer/meaning and explicit integration proof; do not invent a concurrent memory writer |

### Review findings and dispositions

All six additions below are accepted into the **assessment plan**, not authorized
fixes or confirmed cloud failures. Reuse the listed existing ownership after live
issue reconciliation; no issue has been filed, modified or closed by this integration.

| Finding | Impact on the requested pilot | Bounded next assessment step | Owning scope |
|---|---|---|---|
| Memory lacks a producer — code-established | Memory-added configurations cannot promise useful Belief/Goal/Episode output yet | Compare fresh matched configurations; confirm current absence, then propose one minimum useful memory contract for stakeholder choice | #35/#42 |
| Public tenant factory is disabled — code-established | Two databases alone do not supply the requested shared supported entrypoint | Specify API dispatch/bootstrap and worker binding/lifecycle; keep fail-closed behavior until prerequisites are proven | #43 |
| UserProfile schema uses user_id while storage uses profile_id — discrepancy inspected; runtime impact unverified | User endpoint may show a profile while composed personalization cannot find it | Compare one extracted profile's canonical key, user endpoint and personalization evidence | #42/#39 |
| Random fallback preference IDs, repeat counts and correction dictionaries — suspected failure sequence | Retry may duplicate observations; a correction may not supersede the intended preference | Force retry after write/before ACK and run same-key/opposite-polarity sessions; assert exact IDs/counts/evidence/supersession | #42/#37/#39 |
| Enrichment can run before Event projection — concrete code path; runtime effect unverified here | Zero lag may conceal missing annotations; partial writes need convergence proof | Hold projection, allow enrichment, resume; interrupt pack apply between stages; verify exact converged graph and evidence | Existing #29/#14/#10, reconcile actual acceptance |
| Session-wide evidence and retention need explicit policy | Returned evidence may be broader than a specific claim or later unavailable | One user-correction evidence query and one bounded PDLC retention case, with predeclared expected availability | #39/#19 |

Detailed file/line evidence, five-worker matrix, concrete supported user and PDLC
inputs, and two grounded diagrams are in the full report. Preserve its evidence
labels: code-established, inspected prior execution evidence, unverified.

### Changes to the proposed assessment execution

Run the decisive probes before promising the extensive pilot. Capture actual
settings, resolved manifests/handler digest and provider prerequisites per configuration.
Separate three verdicts: configuration resolves; useful output is produced; supported
public tenant execution exists. A loadable pack or zero-output extraction invocation
cannot substitute for the other verdicts.

Do not yet mark the requested matrix supported. In particular, bring back a bounded
product decision on useful memory behavior and a concrete tenant-runtime prerequisite
before implementing either. These findings narrow the assessment; they do not authorize
a new memory framework, removal of tenant guards, historical migration or runtime changes.
G07 remains the selected execution goal; the assessment/pilot gate remains separate.

## Product question

Can two developers use different tenant-selected pack combinations through the
same supported Engram entrypoints, obtain the right graph and answers for each,
and never expose one tenant's information or disabled capabilities to the other?
A single PDLC happy path or clean-start smoke test is insufficient for this pilot.

The user expanded the earlier one-team/core+PDLC-only pilot proposal. The new
proposal requires two tenants with different pack choices, extensive connected
journeys and retrieval verification. Earlier one-team advice does not supersede
this requirement. Core remains mandatory; other capabilities must be assessed,
not assumed optional or compatible because their schemas load.

## Sequence and stop boundaries

1. Execute and deliver G07 under its existing bounded specification, review,
   Spanner verification, stakeholder walkthrough and actual issue reconciliation.
2. Present a separate pack-composition/worker assessment goal. Ground its findings
   in the actual loader, admission, worker wiring, graph writes and both retrieval
   paths. Show supported, unsupported and unverified configurations and concrete
   blocking issues; do not start an open-ended foundational rewrite.
3. Prepare the two-tenant pilot specification and ticket breakdown from that
   evidence. Obtain approval for the selected fixes/runs before pilot execution.
4. Execute the approved pilot journeys through Engram on real Spanner, deliver
   verification/demo and a go/no-go decision for developer access. Do not call
   the pilot ready if required combinations or isolation cases remain blocked.

Existing G08–G13 cover related work. Reconcile their acceptance with this sequence
rather than creating a duplicate program or claiming these goals are complete.
Keep the retired broad goal paused. Historical migration and cross-version data
conversion remain excluded. No ANN/hierarchy-policy work is pulled into this goal.

## Configuration matrix for the prerequisite assessment

| Configuration | Why inspect it | What must be established before promising it |
|---|---|---|
| core + user | Initial tenant A selection, without memory or PDLC | Actual user dependencies, supported inputs/reads and absence of disabled outputs |
| core + user + memory | Tenant A with memory added | How specialized processing composes, shared entities/evidence and retrieval ownership |
| core + PDLC | Initial tenant B selection, without user or memory | Domain projection and retrieval without hidden user/memory assumptions |
| core + PDLC + memory | Tenant B with memory added | Whether the same events create domain and memory outputs correctly, without duplicate/conflicting writes or unsupported inference |

Also inspect core alone as a control, aligned with G08. Do not assume all listed
combinations will pass. Missing dependencies/capabilities must produce explicit
supported-combination restrictions or bounded remediation proposals, never silent
fallback to all packs. Use fresh isolated datasets for any later configuration
variation; do not turn this into disabled-historical-data migration.

## Questions the assessment must answer with code evidence

- What does each pack declare, what does it require, and what behavior remains
  specialized code? Show an actual resolved configuration, not just pack names.
- Enumerate the actual active worker loops. Start from the original four shared
  responsibilities (graph projection, session knowledge extraction, enrichment,
  consolidation), and include pack extraction and any additional active loop.
  Verify current names/ownership; do not assume the architecture still has exactly four.
- For every configuration and worker, identify its input assumptions, applicability,
  outputs/types/edges, provider needs, evidence writes and enabled/disabled behavior.
  Check full-worker versus sub-operation gating: disabling memory must not accidentally
  disable mandatory core evidence or leave user-specific writes active.
- Trace one concrete input per configuration from authenticated admission through
  ledger, worker dispatch, graph writes and retrieval. Distinguish observed execution
  from source inspection. Draw expected graph shapes with actual declared types after
  inspection; do not invent a shared user/memory/domain identity mapping.
- In core+PDLC+memory, does an event legitimately feed both behaviors? Which writes
  are independent, which share core identity/evidence, and what dependencies/order
  guarantees prevent duplicates, dropped evidence or conflicting lifecycle updates?
- Audit both event-memory and artifact retrieval: intent selection, seed discovery,
  vectors, hydration, traversal, ranking, evidence and fallback. Which paths assume
  optional types exist? Does resolved selection govern all paths, including caches?
- Verify tenant configuration and database binding across API, all workers and reads.
  Storage/database separation alone is insufficient if a process-global registry,
  source identity, cursor, cache, provider context or worker uses the wrong tenant.
- Assess startup/provider failure, worker interruption/recovery, pending deliveries,
  retention and processing visibility. Reuse existing issues; identify pilot blockers
  rather than making every reliability task a prerequisite without evidence.

Assessment deliverable: configuration × worker × write/read capability table;
plain-language graph diagrams; concrete code references and bounded probe evidence;
keep/fix/block decisions; required dependencies and proposed issue links; and the
smallest independently verifiable fixes. Inspection is not Spanner sign-off.

## Proposed pilot journeys to specify after assessment

Final pack selections depend on the assessment. Plan two simultaneously isolated
tenants with separate server-authorized Spanner databases. Start from tenant A's
user-oriented configuration and tenant B's PDLC-oriented configuration; include the
memory-added variants if supported. Do not silently shrink the requested matrix to
one tenant or remove memory to obtain a pass.

### Tenant A: personal context and memory where selected

Use synthetic but realistic conversations/events: a person states a preference,
corrects it later, discusses a goal and makes progress across sessions. Include a
second person and similarly worded facts as controls. First discover the actual
supported producer contracts and authoritative versus extracted semantics; a user
pack declaration does not guarantee a deterministic preference API.

Questions to freeze against supported behavior: “What is this person's current
preference and what evidence supports it?”, “What changed?”, “What were they trying
to accomplish?”, and “What relevant context came from the earlier session?”
With memory absent, unavailable memory behavior must have a defined response;
it must not run hidden memory processing or return another tenant's context.
Expected outputs, graph identities, confidence/status, evidence and permitted
retrieval paths must be explicit before execution. Do not invent auto-updating
profiles, goal completion or authenticated human assertions.

### Tenant B: a connected development journey and memory where selected

Rebuild through Engram: product request → PRD → requirements → HLD/LLD → explicit
work tickets/PRs → reviews and test runs → release/deployments → incident → explicit
remediation/resolution → lesson cited by a future specification. Reuse G1–G7
fixtures and supported mappings, adapting them into a coherent dataset without
copying graph rows or modifying retained demo data.

Questions include: “What implements this requirement?”, “Which tests failed or were
skipped?”, “Which release/deployment contained that change?”, “What incident occurred
there and what explicitly remediated it?”, and “Which later specification cited the
lesson?” If memory is enabled, define a separate cross-session contextual question
and verify how it relates to domain artifacts without inventing graph links.

### Both tenants: adversarial and operational cases

- Reuse identifiers, entity names and wording across the two databases deliberately.
  Query A with B artifact/event IDs, cursors and text, and vice versa. Verify denial
  or defined absence without leaking existence, content or evidence.
- Verify both retrieval APIs, vector/text seed discovery, graph expansion, hydration
  and supporting events. Scope response and no-write checks to actual contracts.
- Exercise workers concurrently with different bundles; verify per-tenant writes,
  pending/outcome state and restart recovery, plus cache/cursor boundaries.
- Include changed-content conflicts, unchanged retries, malformed inputs, missing
  references, late events and worker/provider failure relevant to the supported journeys.
- A developer must follow documented clean-checkout setup, authenticate, submit
  fixtures and retrieve results without manual graph repair. Record deployment topology
  honestly; separate database tests alone do not prove shared-runtime tenant dispatch.

## Pilot verification and retained-data boundaries

Predeclare exact payloads, source provenance, typed IDs, properties, graph deltas,
relationship directions, confidence/status and supporting Event sets. Fix original
questions and expected answers before runs; preserve failures and explain any oracle
correction. Each required case traverses Engram write API → real Spanner ledger →
ordinary workers → graph → Engram retrieval API, with observed worker outcomes.
No mocked storage, direct graph setup or manual fixes count as passing.

Protect retained G05 and G06 databases. Later assessment/pilot writes require explicitly
owned separate targets and real tenant bindings, no caller-supplied database routing.
Retain successful demonstration datasets until cleanup approval; keep credentials
outside git. New database resource availability is unverified at this planning stage.

Publish a verification document and stakeholder demonstration, expected/actual
per-case results, setup commands, code/config/source hashes, independent review,
actual issue reconciliation and explicit remaining limitations. Assess new feature
buckets without automatically expanding scope. A required failure/partial/blocked
case prevents the corresponding readiness claim; developer access is a separate
go/no-go decision, not inferred from this brief.

## Tracking

Existing ownership: #34 pack feature umbrella; #35 composition/capability contracts;
#42 optional memory/user behavior; #43 tenant-bound routing; #39 exact conformance;
#40 PDLC journeys; #41 real-Spanner compatibility. Inspect relevant live issues and
comments when drafting the assessment tickets. This brief creates no issue, closes
nothing and claims no new implementation or runtime verification.

## Follow-up: was memory projection removed by the refactor?

Expanded 10 October RCA: [branch/history call audit, timeline, cause and bounded corrective direction](2026-10-10-memory-producer-rca.md).

Stakeholder asked whether an existing memory producer was lost and should be restored.
The coordinating agent inspected history read-only after Astra's report; this section
is additional source/history evidence, not a new Astra review or runtime test.

Historical anchors:
- `d49ded4e0c92eab32b822197669254b31e14aed5`: original Memory Intelligence consolidation groups session events into episode-sized lists, then writes **Summary** nodes with scope `episode` and SUMMARIZES edges. It does not instantiate EpisodeNode.
- `797f79981a666805e21fd05b08ed0fe17f43c43e`: introduces Belief/Goal/Episode models, uniqueness constraints and merge helpers. Inspection found helper definitions but no worker/API producer callers for those three types. The ADR-0009 amendment describes the schema addition; that description is not proof of an event-to-artifact producer.
- `b4a94d9fa9486bb847b638b56df117071559ceb4` (parent of ontology phase0 `0507231`): pre-pack graph/Neo4j adapters have merge_belief_node, merge_goal_node and merge_episode_node; source searches found no production callers. Consolidation still writes episode-scoped Summary nodes.
- Current worker/consolidation.py retains group_events_into_episodes, create_summary_from_events(scope="episode") and write_summary_with_edges; current graph adapters retain the three memory-node merge helpers.
- Available worker history searched for those type names and merge calls did not show a removed producer. This bounds the conclusion to the inspected repository history; it does not establish behavior in an unavailable branch or external application.

Conclusion: **no evidence found that the pack refactor removed an active Belief/Goal/Episode producer**. The original agent-memory behavior included event/entity context, personalization and hierarchical summaries; these are not equivalent to materializing the later memory pack's three types. Existing low-level storage helpers are infrastructure, not a wired ingestion/worker path.

Best next assessment step: explicitly map original worker responsibilities to current
handlers and verify behavioral preservation for the requested compositions. Label
confirmed regressions restoration work; label previously unwired memory-type producers
new wiring. Do not build new producers under the mistaken premise that all prior
memory behavior disappeared. A source-preserved summary path still requires execution
verification, including evidence/retention and retry semantics.

If useful memory-type output is selected, prefer a bounded producer using the existing
worker/capability mechanism and graph ports. Episode/CONTAINS can reuse existing grouping
and summary work if its semantics are approved; Belief and Goal require explicit
admission/extraction, identity, lifecycle, confidence and provenance contracts. They do
not follow automatically from a summary, preference or PDLC ticket. Prove enabled and
disabled variants through actual Engram ingestion and retrieval on Spanner. No new worker
service or broad rewrite is justified by this historical check. Implementation is not
authorized by this section and remains separate from G07.
