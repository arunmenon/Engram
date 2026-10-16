---
schema_version: 1
artifact_id: N-SURVEY-20260928-20
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: []
supersedes: null
idempotency_key: note:survey:github:getzep/graphiti+docs:docs.cognee.ai/guides/ontology-support
claim_cluster: prescribed-vs-learned-types-in-memory-graphs
found_via: survey
source_url: https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types
strength: vendor-docs (no benchmark on typing)
pillar_primary: R10
pillar_secondary: ["R9"]
memory_stage: ingestion
priority: 3
tags: {"mechanism": ["Pydantic entity and edge types", "edge_type_map by endpoint pair", "excluded types", "OWL grounding with annotate or strict mode", "canonical renaming", "parent-class expansion"], "workload": ["agent memory graphs"], "lifecycle_stage": ["ingestion", "linking"], "cross_cutting": []}
evidence: {"directness": "medium: docs describe the typing mechanism, no measurement of its effect", "control": "none", "independence": "low: vendor docs (Zep, Topoteretes)", "reproducibility": "high: both open source (Graphiti Apache-2.0, 31.3k stars; Cognee open source)", "applicability": "high: the two closest memory products to ours, and both let the operator choose between a fixed type set and free extraction"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": []}
answers_watch_request: null
---

# Prescribed versus learned types in memory graphs: Graphiti custom entity and edge types, and Cognee's OWL ontology grounding

- **URL:** https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types ; https://github.com/getzep/graphiti ; https://docs.cognee.ai/guides/ontology-support
- **Type:** vendor documentation of open-source repos
- **Author / org:** Zep (Graphiti); Topoteretes (Cognee)
- **Date:** living docs, retrieved 2026-09-28
- **Retrieved:** 2026-09-28 (summarising fetch)
- **Cited by evidence:** CTO focus question 2; X post https://x.com/sebas5384/status/2103615379029606714 ("an ontology inside of a temporal graph like Graphiti + Neo4j")
- **Relevance to a memory stack:** high. These are the two memory products nearest to ours, and each exposes the ontology choice as configuration.

## TL;DR
- **Graphiti:** "Define entity and edge types upfront via Pydantic models (prescribed), or let structure emerge from your data (learned)."
  - `edge_type_map`, such as `("Person", "Company"): ["Employment"]`, restricts which relation types may join which endpoint types. The `("Entity","Entity")` key is the fallback.
  - `excluded_entity_types` suppresses extraction of listed types.
  - Protected attribute names: `uuid, name, group_id, labels, created_at, summary, attributes, name_embedding`.
- **Graphiti facts are bi-temporal**: "old facts are invalidated, not deleted". Types themselves are not versioned.
- **Cognee** "grounds extracted entities and types to your OWL ontology (classes and individuals), renaming matches to the canonical term and marking them `ontology_valid=True`". It reads only `owl:Class`, `rdf:type`, `rdfs:subClassOf` and `owl:ObjectProperty`, then "extends the extracted graph with the matched term's parent classes and object-property links".
- **Cognee modes**: in the default annotate mode, unmatched nodes stay. In `"ontology_mode": "strict"`, "a node survives only if the ontology matched either its type against a class or its name against an individual." The ontology is "parsed once at initialization", so there is no evolution.
- Neither publishes a number on whether typing helps retrieval or answer quality.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Graphiti typed vs untyped extraction | not stated | | | none published in docs read |
| Cognee strict vs annotate | not stated | | | none |
| Cognee fuzzy-match cutoff | "80% cutoff" | | Cognee blog, search snippet only | not on the docs page |

## Mechanism details you could implement
- An **endpoint-typed edge map** is a closed menu per node pair. That is the right shape for a System One link decision: given a Ticket and a Requirement, the allowed relations are {implements, affects, tracks, none}.
- **Three modes on one switch**:
  - prescribed only (strict)
  - prescribed plus unmatched kept and flagged (annotate)
  - learned
- This is the natural arm set for testing whether our PDLC types should be closed.
- **Canonical renaming on match** is the entity-resolution step: map extracted "auth service" onto the ontology individual `AuthService`.

## Limitations, caveats, counter-evidence
- No evidence either way on prescribed versus learned. The EvoOntology note (N-20260928-07) is the only measured source on evolving a type layer, and it is on data agents.
- Neither system has a gate that admits a new type into the ontology. Learned types in Graphiti simply appear.

## Takeaways for tuning a memory stack
- Ship PDLC types as a prescribed set with an `edge_type_map`, run in annotate mode (unmatched items kept and flagged), and log every unmatched item as a candidate for type admission.
- Our schema registry (gateway component 15) should hold the type set and the edge map. Extraction reads them; it does not own them.

## Open questions
- Does strict mode lose recall on engineering artifacts? Nobody has measured it. This is a candidate arm in a card.
