---
schema_version: 1
artifact_id: N-SURVEY-20260928-17
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: []
supersedes: null
idempotency_key: note:survey:docs:palantir.com/docs/foundry/ontology
claim_cluster: docs:palantir.com/docs/foundry/ontology
found_via: survey
source_url: https://www.palantir.com/docs/foundry/ontology/overview/
strength: vendor-docs (no benchmark)
pillar_primary: R10
pillar_secondary: ["R7", "R8", "R9"]
memory_stage: ingestion
priority: 3
tags: {"mechanism": ["object types", "link types", "interfaces", "action types", "submission criteria", "writeback", "object security policies", "ontology branching and proposals", "schema migrations", "typed SDK", "agent tools"], "workload": ["enterprise operational data", "agents acting on objects"], "lifecycle_stage": ["ingestion", "gated action", "schema evolution"], "cross_cutting": ["federation contract"]}
evidence: {"directness": "high for what the product does (the vendor's own reference docs), none for whether it works better than an alternative", "control": "none: no comparison or measurement", "independence": "low: vendor documentation", "reproducibility": "low: closed product; the docs are public and dated", "applicability": "medium: the kinetic half (actions with preconditions, action log, branching with edit migration) transfers directly to a PDLC memory; the hand-modelled, copy-and-index semantic half does not"}
beliefs_affected: {"supports": ["B25"], "contradicts": [], "would_create": ["A shared ontology used as a federation contract needs typed actions with declared preconditions and an action log, not only types and links; our ADR-0011 has none"]}
answers_watch_request: null
---

# Palantir Foundry Ontology, from Palantir's own documentation (semantic half, kinetic half, backing, permissions, versioning, SDK, agent tools)

- **URL:** https://www.palantir.com/docs/foundry/ontology/overview/ (plus 11 more pages on palantir.com/docs listed below)
- **Type:** vendor documentation
- **Author / org:** Palantir Technologies
- **Date:** living docs; retrieved versions mention the Object Storage V1 (Phonograph) deprecation date of June 30, 2026 and Global Branching general availability "the week of May 18, 2026" (search snippet)
- **Retrieved:** 2026-09-28 through a summarising fetch tool. Quoted text is what the tool returned as quotation; confirm against the live page before citing externally.
- **Cited by evidence:** CTO focus question, 2026-09-28 ("I know there's something from Palantir on ontology")
- **Relevance to a memory stack:** high for design, zero for measured effect. It is the most complete product definition of an ontology that agents both read and act through.

## TL;DR
- Palantir splits the Ontology into **semantic elements** (object types, properties, link types, interfaces) and **kinetic elements** (action types, functions). The overview page uses both headings.
- **Objects are indexed copies by default, not queries in place.** The Object Data Funnel "orchestrates writes into the Ontology by reading from datasources and user edits, then indexing this data into object databases". Search snippets also say objects can be "backed directly by virtual tables", which point at tables in outside platforms. Whether those are indexed too is not stated in what we read.
- **Actions are the kinetic contract.** An action type is "the definition of a set of changes or edits to objects, property values, and links that a user can take at once". It has parameters, rules, side effects (webhooks), **submission criteria** (preconditions) and an action log with undo.
- **The schema is versioned like code.** Ontology branches and proposals are "analogous to a Pull Request". In OSv2 a breaking change cannot be saved until every affected user edit has a migration instruction.
- **Agents get typed tools, not free text.** Agent Studio tools are Action ("execute an ontology edit"), Object Query, Function and others. An action tool "can be configured to run automatically or to run after confirmation from the user".

## What it claims / describes

**Semantic half.**
- Object types and properties. A backing datasource is selected, and columns are mapped to properties automatically or one by one.
- Primary keys must be unique per row and deterministic: "If the primary key is non-deterministic and changes on build, edits can be lost and links may disappear."
- Link types.
- **Interfaces**: "an Ontology type that describes the shape of a object type and its capabilities". They give polymorphism (for example `Airport`, `Manufacturing Plant` and `Maintenance Hangar` all implement `Facility`), with shared properties and link and action constraints. One of the listed use cases is "Consistent modeling across multiple source systems". Interface action type constraints are in beta.
- **Multi-datasource object types (MDO)**: one object type backed by several datasources, joined column-wise on the primary key. Each property comes from exactly one datasource. Only Foundry datasets or restricted views can back an MDO, streams cannot, and only in OSv2.

**Kinetic half.**
- Action types: rules create, modify or delete objects and links, or call a function (function-backed actions). Side effects are notifications and webhooks to external systems. Writeback datasets "reflect the most current object state including user edits". The action log supports audit and undo or revert.
- Submission criteria: "the conditions that determine whether an action can be submitted", with three condition types:
  - Current User (id, group, multipass attributes)
  - Parameter (for example an object's status)
  - Execution Context (inside an Ontology Scenario)
- "Every condition and logical operator on the root level has its own failure message." Criteria "do not support attachment and object set parameters".
- Functions: "authoring business logic with arbitrary complexity". AIP Logic is a function type. We did not fetch the AIP Logic page.

**Permissions.**
- By default, datasource permissions carry over: "Any user that has at least `Viewer` permissions on the dataset and its transactions will have access to all object instances created from that dataset."
- Object and property security policies add row, column and cell control, configured independently of the datasource. They support "Mandatory and classification based access controls".
- In an MDO, a user without access to one input datasource sees that datasource's properties "as `null`".
- Limit: these controls "do not extend to downstream outputs or exports".

**Versioning.**
- Branchable resources: object, action, link, interface and shared property types. Rule sets and type groups are not branchable.
- Rebase is manual, conflict by conflict. Merge happens after checks and approvals.
- OSv1 lost user edits on a breaking change. In OSv2 the breaking changes are:
  - changing input datasources
  - changing the primary key
  - changing a property's data type
  - renaming or deleting properties that have edits
  - changing struct field types
- The available migrations are drop edits, move edits, cast, and revert. There is a maximum of 500 migrations per operation.

**SDK (OSDK).** It generates "functions and types based on just the subset of the Ontology relevant to you" in TypeScript, Python and Java, plus an OpenAPI spec. The token is "scoped only to the ontological entities you want your application to access, in addition to the user's own permissions to the data".

## Numbers

| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| max properties per object type | 2,000 | n/a | object-backend overview | product limit |
| max objects edited per action | 10,000 (more on request) | n/a | same | |
| default Search Around limit | 100,000 objects | n/a | same | configurable |
| indexing scale | "Tens of billions of objects per object type" | n/a | same | vendor claim, no benchmark |
| max datasources per object type | 70 | n/a | MDO page | only datasources synced to object storage count |
| max schema migrations per operation | 500 | n/a | schema migrations page | |
| effectiveness of the ontology for agents | not stated | | | no published comparison found in the docs read |
| latency | not stated | | | |

## Mechanism details you could implement
- **Action type = typed parameters + rules + submission criteria + side effects + log entry.** For us, an action is something an agent proposes to do, such as "merge PR", "close ticket", "supersede decision" or "mark requirement verified". Its criteria are checked against the graph before the agent acts. This is the pre-action gate the PDLC layer lacks (pdlc-memory-layer section 2), in a form with a published shape.
- **Per-condition failure messages** give the agent a reason it can act on, not a bare refusal.
- **Interfaces as the federation type.** A `WorkItem` interface is implemented by a Jira issue, a GitHub issue and a Linear ticket. Each keeps its own source-specific object type, and the gateway plans and ranks over the interface.
- **Deterministic primary keys from the source**, never generated. Otherwise links vanish on rebuild. This matches our content-hash anchoring (EA-Graph) and the gateway's "source identity and deduplication" (component 17).
- **Breaking-change detection plus a mandatory migration instruction** before a schema change can be saved.
- **Null-on-no-access per property** in a joined object, which matches our "typed access failure, never substituted content" rule.

## Limitations, caveats, counter-evidence
- **No evidence of effect.** Nothing we read measures whether an ontology improves agent or analyst outcomes against a baseline.
- **Not federation without copying.** The default architecture indexes source rows plus user edits into Palantir's object databases. This contradicts the focus's framing that objects are "backed by source datasets without moving them". Virtual tables are the exception, and it is only partly described.
- **Hand-modelled per customer.** Types, keys and mappings are defined in Ontology Manager by people. Nothing in the docs read proposes or admits types from traffic.
- Permissions do not follow data into exports. Our replay and snapshot path needs a stronger rule.
- The summarising fetch tool may have paraphrased. The word "dynamic" for the kinetic elements was not confirmed as Palantir's.

## Takeaways for tuning a memory stack
- Add the kinetic half to ADR-0011 as typed Action nodes with preconditions, not as more edge types.
- Version the ontology with branch, proposal and migration. Refuse a schema change that has no migration for existing links and edits.
- Use interfaces over source-specific types as the gateway's normalised type, rather than forcing every hub into one flat type.
- Do not copy: hand modelling per customer, and copy-and-index as the default.

## Open questions
- Can objects backed by a virtual table be edited by actions, and are they indexed? Not stated in the pages read.
- AIP Logic internals and any published evaluation of agents using ontology tools: not fetched or not found.

Pages read (12): ontology/overview, object-backend/overview, action-types/overview, action-types/submission-criteria, object-permissioning/managing-object-security, object-permissioning/multi-datasource-objects, object-edits/schema-migrations, ontologies/branching-ontology, ontology-sdk/overview, agent-studio/tools, interfaces/interface-overview, object-link-types/create-object-type (all under https://www.palantir.com/docs/foundry/). Plus one fetch of data-integration/virtual-tables (content not returned) and one search.
