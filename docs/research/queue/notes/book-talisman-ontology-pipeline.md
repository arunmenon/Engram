---
schema_version: 1
artifact_id: N-SURVEY-20260928-27
artifact_type: note
producer: triage
run_id: survey-20260928T164932Z-talis
created_at: 2026-09-28T16:49:32Z
input_refs: []
supersedes: null
idempotency_key: note:survey:book:talisman-ontology-pipeline
claim_cluster: prescribed-vs-learned-types-in-memory-graphs
found_via: CTO link (X post by @KirkDBorne, 2026-09-27)
source_url: https://technicspub.com/ontology-pipeline/
source_posts: ["https://x.com/KirkDBorne/status/2104215082825646580"]
strength: opinion (practitioner framework from 25 years of library and enterprise practice; no measurement)
pillar_primary: R10
pillar_secondary: ["R9"]
memory_stage: ingestion
priority: 3
tags: {"mechanism": ["controlled vocabulary", "metadata application profile", "taxonomy", "thesaurus (SKOS broader, narrower, related, altLabel)", "RDFS ontology", "layered knowledge graph"], "workload": ["enterprise knowledge infrastructure"], "lifecycle_stage": ["ingestion", "linking"]}
evidence: {"directness": "low: a method, not a result", "control": "none", "independence": "medium: an independent practitioner, though the framework is trademarked and sold (book, studio)", "reproducibility": "high: open standards (SKOS, SKOS-XL, Dublin Core, RDFS, ISO 25964, ANSI/NISO Z39.19)", "applicability": "high for our cross-tool mapping problem"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A shared, governed vocabulary across tools makes type mapping and same-item matching cheaper and more accurate than mapping raw tool names straight onto ontology types."]}
answers_watch_request: null
---

# Ontology Pipeline: build the word list before the ontology (Jessica Talisman, book, 2026)

- **URL:** https://technicspub.com/ontology-pipeline/ ; framework essay https://jessicatalisman.substack.com/p/the-ontology-pipeline (2025-05-26) ; https://www.ontologypipeline.com/
- **Type:** book (Technics Publications) and the author's essays
- **Author:** Jessica Talisman, semantic engineer and information architect (library science background)
- **Found via:** the CTO, from a post by @KirkDBorne (28.5K views, 846 bookmarks) quoting the publisher's description
- **Retrieved:** 2026-09-28 (summarising fetch of the essay and the publisher page; the Amazon link was not opened)

## For a busy reader
Most teams jump straight to drawing an ontology. This book argues you cannot: you first need an agreed word list (one name per thing, synonyms resolved), then standard fields, then a hierarchy, then a thesaurus that records which words mean the same or related things, and only then the ontology and the graph. Each layer is cheap and checkable, and each makes the next one possible. For us this names the layer our ontology research skipped: between "Jira calls it a Story, GitHub an issue, Linear a ticket" and our shared type "work item" there has to be a governed thesaurus. It is a method with no measurements, so treat it as a design idea to test, not evidence.

## The framework
Six stages, in order, each preparing the ground for the next:
1. **Controlled vocabulary:** deduplicated, defined terms with synonyms resolved (ANSI/NISO Z39.19).
2. **Metadata standards:** an application profile of fields (Dublin Core Terms), so values can be validated.
3. **Taxonomy:** parent and child classes (SKOS).
4. **Thesaurus:** broader, narrower, related and alternative labels, which handle ambiguity (SKOS, SKOS-XL; ISO 25964).
5. **Ontology:** classes, subclasses, domains and ranges (RDF Schema; OWL where logic is needed).
6. **Knowledge graph:** the assembly of all five layers, queried with SPARQL and validated with SHACL. The layers stay separate, which the author says makes broken logic easier to find.

Her main claim: ontology construction is "nearly impossible" when the underlying data is not logically structured, and skipped stages fail later, often visibly in AI projects. She asserts that language models need clean, semantically enriched data, but gives no numbers, benchmarks or case studies.

## What it means for us
- **The missing layer.** Tonight's synthesis (N-SURVEY-20260928-26) proposes shared kinds ("work item") and per-tool bindings. Talisman's order says the binding should go through a thesaurus: each tool's issue types, statuses, labels and link names become alternative labels of one preferred concept, with a scope note. The ontology then maps concepts, not raw strings.
- **Where Jev fits.** The thesaurus becomes the closed menu for the Choice decisions at G7 (type a field or item) and G13 (same item across tools): preferred label plus alternative labels plus scope note, instead of a bare type name. Exact label matches can be resolved deterministically before any model runs.
- **Fixed list versus learned kinds (card PC-SURVEY-20260928-10).** The thesaurus gives new words a place to land first: a new label becomes an alternative label of an existing concept, and becomes a new type only if the gate admits it. That is a softer, cheaper gate than admitting new ontology types directly.
- **Our standards are compatible.** ADR-0011 is a PROV-O profile; SKOS and Dublin Core sit beside it without conflict. OSLC link names (N-SURVEY-20260928-19) are a controlled vocabulary for links.

## Limits
- No measurement anywhere in the material read. The claim that AI projects fail from skipped stages is the author's experience, not data.
- The framework is trademarked and sold (book, studio), so the author has an interest in it.
- Written for enterprise knowledge management; how much of it a PDLC memory needs (for example, full SKOS-XL label records) is untested.
