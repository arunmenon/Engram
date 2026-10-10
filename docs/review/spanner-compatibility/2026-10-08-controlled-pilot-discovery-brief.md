# Controlled developer pilot: requested scope and prerequisite assessment

Status update, 10 October 2026: stakeholder confirmed G7 complete and authorized the pack-composition assessment, including reuse of only the assessment database after verified exports. The [local and live assessment](2026-10-10-pack-composition-assessment.md) now records all five configurations attempted: enrichment persistence failed in core/PDLC cases, both user-enabled runs failed on Entity-interest provenance, and useful Memory production remains blocked. Sequential reuse does not prove concurrent tenant isolation. No runtime fixes or developer pilot have started. Historical planning below is preserved.

## Grounding review — completed, code inspection only

The approved Astra medium review is [preserved in full](2026-10-08-astra-pilot-composition-assessment.md).
Reviewed source: `51a680adeca608618e0e7905991037349631994e`. No tests or cloud
runs were performed. The coordinating agent spot-checked the pack bundle, memory
manifest, public tenant factory and profile-key/read-filter references. Source
inspection is not reproduction of the suspected runtime failures.

### Current implementation facts to carry into the assessment

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
