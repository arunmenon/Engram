# Controlled developer pilot: requested scope and prerequisite assessment

Status: stakeholder requirements captured. This is a discovery brief, not a
completed assessment, approved implementation specification or pilot-readiness
claim. G07 is selected first. Do not automatically start this assessment, G08 or
the pilot when G07 ends; present the assessment scope at that checkpoint.

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
