# PDLC ontology v1.0: one page for sign-off

**Date:** 2026-10-04 · **Pack:** [`pdlc.pack.yaml`](pdlc.pack.yaml) v1.0 · **Mechanism:** [ADR-0018](../../../adr/0018-ontology-packs.md) (ontology packs) · **Ingestion:** [connector design](connector-design.md)

## What you are approving

1. **The PDLC ontology v1.0:** 17 node types, 25 link types, grounded in OSLC, CDEvents, Backstage and OMG Essence, with PROV-O kept as the provenance foundation.
2. **ADR-0018:** ontologies as versioned packs, read by generic code; today's schema becomes the first pack; changes applied by rebuilding from the event log; all new code backend-neutral.
3. **The connector design:** tools feed Engram through the existing `/v1/events` API, with live and history imports sharing one path.

## The ontology

| Stage | Types |
|---|---|
| Intake | Request, Spec, Requirement, Decision, Constraint |
| Design | DesignElement |
| Work | WorkItem (epic, story, task, bug, production change) |
| Code | Change, Review |
| Verify | TestCase, TestRun |
| Ship | Release, Deployment |
| Operate | Component (service, library module, binding, website), Incident |
| Organisation and learning | Team, Lesson |

The key links are: implements, verifies, refines, includes, deploys, applies to, cites, amends, supersedes, touches, reverts, attributed to, raises, and learned from.

Rules that matter more than the type list:
- **Facts and guesses are kept apart.** A merged PR is a fact. "This PR caused that incident" is a guess with a confidence score. Guessed links are kept as proposals, never silently dropped or promoted.
- **Every item records where it came from** and whether that source is trusted.
- **Decisions are history; specs are the current contract.** Overturned decisions stay out of the agent's view unless it asks.

## How it was checked

| Check | Outcome |
|---|---|
| Standards names (CDEvents spec files, OSLC vocabularies) | all names exist; 5 corrections made |
| 30 questions from research, Jetstream and DORA | all answerable; every type and link needed by at least one |
| Real projects: OpenDAL (88 RFCs, 400 commits), Kafka (400 commits), GitLab (15 incidents) | 4 changes: Component, Release, Amends, spec-first for current state |

## What changed from the first draft (v0.1 → v1.0)

- Added: Release, Applies to, Cites, Touches, Reverts, Amends, Includes, Occurred on.
- Renamed: Service became Component.
- Decisions now carry validity dates.
- Links carry confidence, method and status.
- Every item records whether its source is trusted.

## Known limits

- Deployment, TestRun and Lesson have not been checked against real data. No CI, CD or postmortem source was reachable.
- The 30 questions stand in for user interviews.
- Team has the weakest evidence. It's kept because tools declare it cheaply.
- The ingest API has no redaction or payload size limit yet. Connectors must handle both until the API does.

## Graph backend: Spanner now or later?

**Recommendation: design for Spanner now, implement on Neo4j first, then add the Spanner adapter as soon as the generic operations settle (about week 3 of the build). Don't build both from day one.**

- **Nothing needs porting** if new code never writes Neo4j queries directly. Every new piece talks to the graph through about ten generic operations. ADR-0018 now requires this, designed to the stricter of the two databases (rule 11).
- **The Spanner adapter then implements those ten operations,** instead of rewriting 68 hand-written queries. That's the gap analysis's estimate of 4–6 weeks today versus 2–3 after packs.
- **Building both from day one would double the work** while the operations are still changing. The first two weeks will reshape them.
- **One check runs from the start:** a conformance test suite (same events in, same answers out) runs against Neo4j now and against the free Spanner emulator as soon as it can, so divergence shows up early.
- **Blocked on you:** whether `portiq-mvp` can get a Spanner instance with Enterprise edition (or a free trial instance). Without it, Spanner work stops at the emulator.

## Build plan after sign-off

| Weeks | Work |
|---|---|
| 1 | Pack loader and registry; today's schema as the core pack (no behaviour change); conformance suite skeleton |
| 2–3 | Generic graph operations and projector; PDLC pack live; GitHub and git connectors; backfill OpenDAL |
| 3–4 | Spanner adapter on the same operations, validated on the emulator, then the free trial if available |
| 4–5 | PDLC queries (trace, completeness, status, impact, preflight; time windows and "has no link" checks); run the 30 questions |
| 6 | Jira and GitLab connectors; LLM extraction of decisions and constraints; pack versioning and rebuild |

## Decisions needed from you

1. Approve the ontology v1.0, ADR-0018 and the connector design, or name changes.
2. Approve the Spanner approach (design now, adapter in weeks 3–4), or ask for both backends from day one.
3. Confirm Spanner access in `portiq-mvp` (edition, or free trial eligibility).
