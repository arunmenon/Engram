# Expanded controlled-pilot journey discovery

15 October 2026. Source baseline: `92a6053`, `feature/engram-memory-episodes`. Three parallel discovery tracks examined both tenants and shared coverage. This is a proposal, not executed pilot evidence or approval to implement. No database, runtime or GitHub issue was changed during discovery.

## Inventory

**49 candidate product journeys: 25 for Tenant A and 24 for Tenant B.** Separately, **18 shared verification probes** attach to the journeys. Assertions, duplicate inputs and exclusion controls do not inflate the product-journey count.

- [Tenant A — complete 25-journey catalog](tenant-a-discovery.md)
- [Tenant B — complete 24-journey catalog](tenant-b-discovery.md)
- [Shared coverage — 18 probes](shared-coverage-discovery.md)
- [External research and its limits](research-grounding.md)

Each entry gives the event sequence, supported read/question, expected knowledge and evidence, forbidden conclusions, worker applicability, prerequisites, priority and support verdict. Examples are templates; full requests and independently computed expected identities must be frozen before execution.

## Tenant A — Core + User + Memory

Use connected coding, learning, research, work-journal and personal-planning histories, with another owner as a positive isolation control. These situations test different knowledge behavior, rather than repeating a preference under different names.

| Family | Journeys | Example and retrieval purpose |
|---|---|---|
| Personalization and changing context | A-01–A-04 | Short incident responses versus detailed design reviews; correct one context without changing another. Retrieve exact preference support; interest must not become expertise. |
| Attribution and ambiguity | A-05–A-06 | Mercury the project versus Mercury the planet; Alice discussing Bob. Retrieve the right Entity and owner without absorbing someone else's preferences. |
| Recall, temporal grouping and summaries | A-07–A-11 | Resume yesterday's investigation; morning/afternoon work; late note bridging activity. Retrieve source Events, exact Episode membership and useful summaries. |
| Beliefs and revisions | A-12–A-16 | Work assumption, uncertain research hypothesis and revised travel assumption. Distinguish stated, inferred, confirmed and corrected assertions without claiming verified truth. |
| Goals and abandoned plans | A-17–A-20 | Complete a study objective explicitly, abandon a household task, replace a plan, retain a cross-session commitment. Retrieve lifecycle evidence without invented success. |
| Missing knowledge and boundaries | A-21–A-25 | Silence is not preference; missing versus late parent; duplicate/conflicting input; dense history; implicit preference and paraphrase. Return supported evidence or an honest limit. |

Explicit Belief/Goal events prove production and lifecycle correctness. Prose extraction and implicit personalization test model quality. One cannot substitute for the other. Contextual preference selection, earlier-session discovery and Entity ambiguity need fresh proof or a clear gap verdict.

## Tenant B — Core + PDLC + Memory

Use several coherent stories: audit-export feature, production hotfix/incident, library release, abandoned prototype and explicit development Memory. Connect artifacts within each story and retain unrelated stories as exclusion controls.

| Family | Journeys | Example and retrieval purpose |
|---|---|---|
| Planning, revisions and decisions | B01–B06 | Request → approved specification → requirements → HLD/LLD; architecture reversal; approved design revised. Retrieve exact revisions, rationale and approvals without inherited approval. |
| Implementation, review and tests | B07–B12 | Tickets/PRs, requested changes then approval, abandoned/reopened prototype, commit-only work, failing/passing/skipped tests and hotfix. Retrieve actual links and distinct outcomes. |
| Release, deployment and incidents | B13–B16 | Library without deployment; failed then successful production attempt; exact rollback; incident after upgrade. Publishing is not deployment and sequence is not cause. |
| Incomplete knowledge and collisions | B17–B20 | References arrive first; missing versus failing coverage; same PR numbers across repos; incident lesson cited later. Retrieve declared relationships and observed evidence. |
| Memory alongside development | B21–B24 | Correct engineering assumption; explicitly finish or abandon delivery Goal; recall planning/operations Episodes. No automatic PR-to-Goal or requirement-to-Belief link. |

The catalog maps all 28 declared PDLC events. That does not establish every schema relationship or lifecycle. General ownership/dependency links and file-to-service impact cannot be promised because types exist. Commit-only activity can remain ledger/Event-only. Model proposals remain separate from explicit accepted decisions.

## Shared coverage

| Dimension | Required distinction |
|---|---|
| Retrieval | Exact-ID traversal, key/title lookup, paraphrase, temporal context, current/history and unsupported-premise queries have separate results. |
| Workers | Exact outputs/evidence from projection, applicable extraction, enrichment, scheduled consolidation and matching pack extraction; ACK/zero lag alone is insufficient. |
| Providers | Actual models for extraction/summary usefulness; separately labeled frozen-output/fault checks. Entity-vector participation needs channel evidence; artifact retrieval has no artifact-vector channel. |
| Scope | Multiple A owners/sessions, B projects/repos/environments, colliding identifiers across both active tenants. Negative reads need positive controls in their rightful scope. |
| Failure/limits | Retry/conflict/rejection, missing references, provider failure, truncation and cooperative stop/restart. Do not infer general crash recovery. |
| Developer experience | Documented launch, appropriate roles, useful reads, visible failures and independent repetition. |

Engram returns graph/context evidence. A downstream generated answer, if included, needs a separate verdict. Source assertion, model proposal and independently verified fact remain distinguishable.

## Proposed order

1. **Freeze scope and prerequisites:** select required journeys explicitly, provider budget, roles/owner mapping, launch/access, consolidation cadence and retained-data preservation. Priority must not silently remove diversity.
2. **Establish one real-provider path per tenant:** useful User extraction and PDLC prose extraction through the public service, complete evidence and visible failures. This is a prerequisite check, not the whole pilot.
3. **Run the diverse families:** several connected histories, reads from different starting points and natural wording. Preserve failed natural queries beside precise traversal controls.
4. **Attach shared probes:** interleave tenants, reuse identifiers, exercise declared faults/bounds and independently repeat launch/read flows.
5. **Publish verification and demo:** per-journey expected/actual, provider-quality verdict, evidence, retained failures, repeat commands, Astra review and GitHub reconciliation. Stop at the agreed stakeholder approval gate.

Potential bounded decisions include contextual personalization, earlier-session discovery, ambiguity/attribution, useful summaries/proposals and incomplete evidence. Discovery exposes these questions; it does not authorize implementations. Catalogs label prior representative proof, current contracts needing new proof, gaps and product decisions. Tenant A/shared use P0 for required gates; Tenant B uses P0 for inherited prerequisites and P1 for central journeys. Compare using the sequence above rather than labels alone.

Hierarchy authorization (#49), ANN/load stress (#48), historical migration, hot pack switching, forced-crash guarantees and unsupported tenant maintenance/import/cursors/webhooks stay separate. Existing evidence retains its original limits. After stakeholder scope review, prepare the detailed specification and ticket breakdown. No pilot or onboarding begins automatically.

## Method

Applied **lean-exploration** for selective source/evidence reads and **smallest-complete-fix** for concrete outcomes using existing machinery. Three parallel agents covered both tenants and shared checks. Installed `to-tickets` and `implement-spec` were inspected but not invoked: ticket publication and implementation come later. Primary research contributes coverage dimensions, not benchmark pass claims.
