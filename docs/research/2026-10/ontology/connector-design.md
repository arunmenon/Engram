# Source connectors: getting PDLC data into Engram

**Date:** 2026-10-04 · **Status:** proposed with pack v1.0 · **Principle:** no one-off import scripts. History and live data take the same path into the same ingest API.

## The path

```
GitHub · Jira · GitLab · git · CI · CD · service catalog
        │  connector (one per source system; live mode and backfill mode share one mapping)
        ▼
POST /v1/events/batch   (existing API, existing Python SDK)
        ▼
Redis ledger (existing; immutable; duplicates dropped by event id)
        ▼
projection worker  +  PDLC pack rules (generic projector, ADR-0018)
        ▼
graph store through the generic GraphStore operations  ──  Neo4j now; Spanner later, same operations
        ▼
existing query APIs (/v1/context, /v1/query/subgraph, lineage) + PDLC named queries
```

## What each piece owns

| Piece | Owns | Does not own |
|---|---|---|
| Connector | talking to one tool; credentials; source conventions (Kafka `MINOR:`, `Reviewers:` trailers, OpenDAL conventional commits); turning records into `pdlc.*` events | the graph, the ontology, link inference |
| Ingest API (existing) | validation of the envelope; event types checked against the active packs; append to the ledger | anything domain-specific |
| PDLC pack | which nodes and links an event produces; lifecycle; retrieval intents | how a tool's API works |
| Projector (new, generic) | applying any pack's rules; provenance link to the source event | PDLC knowledge |

## Event envelope mapping (existing fields, no schema change)

| Envelope field | PDLC value | Example |
|---|---|---|
| `event_id` | UUIDv5 of (source system, record id, record version) | same PR merge always yields the same id, so re-imports are no-ops |
| `event_type` | `pdlc.<subject>.<predicate>` from the pack | `pdlc.change.merged` |
| `occurred_at` | the time in the source record, not the import time | merge time of PR 812 |
| `session_id` | the project: `repo:<owner>/<name>`, `jira:<project>`, `gitlab:<project>` | `repo:apache/opendal` |
| `agent_id` | the source system | `github` |
| `trace_id` | the work key the record belongs to | `KAFKA-17123`, or the PR id |
| `parent_event_id` | the event this one follows from, when the source says so (CDEvents links) | deploy event → pipeline-run event |
| `payload_ref` | the record's URL | PR page URL |
| `payload` | the normalised record; the original CDEvents type when there is one | title, body, files, linked issues |

## Two modes, one mapping

- **Live:** the connector receives webhooks (or polls) and posts events within seconds.
- **Backfill:** the connector walks the history (API pages, `git log`, changelog, RFC folder) and posts the same events with their original timestamps, in order, in batches. Importing OpenDAL's history is a backfill run, not a script.
- Both modes call the same `record → event` function, so a connector is tested once.

## Connector set, in order

| Order | Connector | Emits | Notes from step 2 |
|---|---|---|---|
| 1 | GitHub (PRs, issues, reviews, releases) | `pdlc.change.*`, `pdlc.ticket.*`, `pdlc.change.reviewed`, `pdlc.release.published` | must read PR pages and linked issues: for OpenDAL the implemented issue is in git only 3% of the time |
| 2 | git history + repository documents | `pdlc.change.committed`, `pdlc.decision.recorded` (RFC / ADR files), `pdlc.spec.approved` (spec files) | fallback when no PR API; reads trailers and conventions |
| 3 | Jira | `pdlc.ticket.*`, `pdlc.request.created` | Kafka links 62% of commits to Jira keys |
| 4 | GitLab (issues, merge requests, incidents) | `pdlc.ticket.*`, `pdlc.change.*`, `pdlc.incident.*` | incident service is in the title only, so AFFECTS is proposed, not declared |
| 5 | CI (GitHub Actions or internal) | `pdlc.testcaserun.finished` | not checked against real data yet |
| 6 | CD (deploy system) | `pdlc.service.deployed` / `rolledback` | not checked against real data yet |
| 7 | service catalog (Backstage, CODEOWNERS) | catalog sync events for Component and owners | fills `Component.path_prefixes` and owners |

Each connector carries a small per-source settings file (ticket-key patterns, "no ticket" markers, trailer names, path-to-component rules). Conventions live there, not in the pack or the core.

## Where connectors run

Outside Engram's core, next to the SDK (`sdk/engram-connectors/`), as a process that holds tool credentials and calls the ingest API. Engram itself never stores tool credentials. A webhook-receiving endpoint inside Engram (`/v1/sources/{source}/webhook`) can be added later for tools that can only push.

## Safety

- Every event records `source_trust` from the connector's allowlist (pack v1.0, R8 brief), never from content.
- Connectors only read from tools; nothing writes back.
- The ingest API has no payload redaction or size limit today. Connectors must strip secrets and personal data and cap payload size until the API enforces both; adding that to the API is a build item.
