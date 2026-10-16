---
schema_version: 1
artifact_id: N-SURVEY-20260928-18
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: []
supersedes: null
idempotency_key: note:survey:docs:learn.microsoft.com/fabric/iq/ontology
claim_cluster: docs:learn.microsoft.com/fabric/iq/ontology
found_via: survey
source_url: https://learn.microsoft.com/en-us/fabric/iq/ontology/overview
strength: vendor-docs (preview, no benchmark)
pillar_primary: R10
pillar_secondary: ["R7"]
memory_stage: ingestion
priority: 3
tags: {"mechanism": ["entity types", "typed directional relationships with attributes", "data bindings with identity keys and provenance", "query federation to native engines", "materialised instance graph on a refresh schedule", "rules via Activator"], "workload": ["enterprise analytics", "data agents"], "lifecycle_stage": ["ingestion", "retrieval"], "cross_cutting": ["federation contract"]}
evidence: {"directness": "high for design, none for effect", "control": "none", "independence": "low: vendor docs", "reproducibility": "low: preview product", "applicability": "medium: relationship attributes (confidence, effectiveAt) and 'which source created it and when it was true' on instances match our trace-link design; the refresh-scheduled materialised graph is a staleness risk for build-time agents"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": []}
answers_watch_request: null
---

# Microsoft Fabric IQ ontology: entity types bound to OneLake data, typed relationships with attributes

- **URL:** https://learn.microsoft.com/en-us/fabric/iq/ontology/overview
- **Type:** vendor documentation (feature "in preview")
- **Author / org:** Microsoft
- **Date:** ms.date 2025-10-06, updated 2026-08-28
- **Retrieved:** 2026-09-28 (summarising fetch; quotes as returned)
- **Cited by evidence:** CTO focus question 2
- **Relevance to a memory stack:** medium. It is the second large vendor to ship an "ontology for agents" layer, and its binding model is the clearest public spec of mapping source columns to shared types with provenance.

## TL;DR
- Entity type: "the reusable logical model of a real world concept". Property: "a named fact about an entity, with a declared data type". Relationship: "a typed, directional link between entity types or instances", with attributes "(like distance, confidence, or effectiveAt) and cardinality rules".
- Instances "keep[s] track of which source created them and when they were true".
- A data binding "connects your ontology's definitions ... to concrete data living in OneLake, including lakehouse tables, eventhouse streams, and Power BI semantic models". It covers "identity keys, how columns map to properties", "schema evolution rules, data quality checks ... and provenance".
- Queries are routed to native engines ("GQL for Graph in Microsoft Fabric and KQL for Eventhouse"). But the "ontology graph is a queryable instance graph built from your data bindings" and it "follows a scheduled data refresh". Upstream changes "need to be manually refreshed before they're visible".
- Rules and actions come through Fabric Activator ("define conditions and actions on top of your business entities"). This is from search snippets of the Fabric blog, not fetched.

## What it claims / describes
A shared semantic layer that Fabric data agents consume, with NL2Ontology turning questions into queries. Public MCP endpoints are described as planned (search snippet only).

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| any effectiveness or latency figure | not stated | | | none published |

## Mechanism details you could implement
- A **relationship with `confidence` and `effectiveAt` as first-class attributes** is exactly the shape of our trace links (IMPLEMENTS with a confidence, VERIFIES with a last-result time).
- **Instance-level provenance** ("which source created them and when they were true") is our bitemporal requirement (gateway component 19) stated as an ontology rule.
- **Bindings as a separate artifact from types.** The same `Requirement` type can bind to Jira in one tenant and to Azure DevOps in another. This is the "mapping" piece the gateway registry lacks.

## Limitations, caveats, counter-evidence
- A preview product. No evaluation.
- It is not purely federated. The instance graph is materialised on a schedule, so it can be stale between refreshes (inference: bad for a build-time agent that needs current ticket state).
- It is tied to OneLake.

## Takeaways for tuning a memory stack
- Put `confidence`, `valid_from` and `source` on every link type in the ADR-0011 amendment.
- Model bindings (source field to property, identity key) as versioned registry artifacts, one per backend.

## Open questions
- How "schema evolution rules" work in bindings is not described on the overview page.
