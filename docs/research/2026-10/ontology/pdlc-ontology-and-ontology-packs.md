# PDLC ontology, and ontology as a first-class, pluggable part of Engram

**Date:** 2026-10-04
**Status:** proposal for review. Nothing in `src/` has changed.
**Companions:** [`pdlc.pack.yaml`](pdlc.pack.yaml) (draft PDLC pack in the proposed format), [ADR-0018 draft](../../../adr/0018-ontology-packs.md), [Spanner Graph gap analysis](spanner-graph-gap-analysis.md).

## 0. The short version

- **Today's ontology is agent-centric and hardcoded.** Its event types are OTel GenAI operations (`agent.invoke`, `tool.execute`, `llm.chat`), its entity types are `agent | user | service | tool | resource | concept`, and the rest is a user model (Preference, Skill, Workflow) and a memory model (Belief, Goal, Episode, Summary). It is wired into six places: frozen enums, a frozen constraints file, about 250 label references in hand-written Cypher, the extraction prompt, the intent-weight matrix, and the intent keyword lists.
- **A PDLC ontology is a different shape, not just more types.** Agent memory is mostly *extracted by an LLM from chat*. PDLC structure is mostly *declared by tools*: a PR is merged, a test run failed, a ticket moved. So the PDLC graph is built mainly by deterministic rules over webhook events, with the LLM used only for prose (decisions and constraints inside documents and threads). And PDLC questions start from artifacts ("what implements this requirement?"), while Engram's retrieval starts from events.
- **Proposal for the PDLC ontology:** reuse existing standards rather than invent. OSLC for artifacts and trace links, CDEvents for delivery events, Backstage for the software catalog and ownership, OMG Essence for lifecycle states, PROV-O kept as the foundation. An MVP of 16 node types and 18 edge types organised along the Jetstream spine (Request → Spec → Design → Work → Change → Verify → Deploy → Operate → back to Request).
- **Proposal for the platform:** make an ontology a versioned, declarative **pack**: types, event-to-graph mapping rules, an extraction profile, a retrieval profile, lifecycle and retention rules, and mappings to standards. One registry loads packs; generic projector, store and retrieval code read from it. Today's schema becomes the `core` pack. Importing a new domain becomes "add a pack, a source adapter and maybe a query plugin", instead of editing five frozen contracts.
- **Changing an ontology is safe because Neo4j is disposable.** A breaking pack change builds a fresh projection from the Redis ledger and switches over. This is the single biggest advantage Engram has for this requirement.
- **Spanner:** the gap analysis says the rewrite is concentrated in `adapters/neo4j` (about 3,850 lines). Doing the pack work first shrinks the Spanner port from "rewrite 68 hand-written queries" to "implement about ten generic operations plus a few plugins". Sequence: packs first, Spanner second.

## 1. Current state: where the ontology lives in code

### 1.1 What the ontology is today

| Module (ADR-0011 naming) | Node types | Edge types | Source |
|---|---|---|---|
| core | Event, Entity, Summary | FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES | ADR-0009 |
| entities | (Entity with `entity_type` ∈ agent, user, service, tool, resource, concept) | SAME_AS, RELATED_TO | ADR-0011 |
| user | UserProfile, Preference, Skill, Workflow, BehavioralPattern | HAS_PROFILE, HAS_PREFERENCE, HAS_SKILL, DERIVED_FROM, EXHIBITS_PATTERN, INTERESTED_IN, ABOUT, ABSTRACTED_FROM, PARENT_SKILL | ADR-0012 |
| epistemic, goals, episodes | Belief, Goal, Episode | CONTRADICTS, SUPERSEDES, PURSUES, CONTAINS | ADR-0009/0011 amendments |
| events | `agent.*`, `tool.*`, `llm.*`, `observation.*`, `system.*`, `user.preference.*` | | ADR-0011 §2 (OTel GenAI) |
| intents | why, when, what, related, general, who_is, how_does, personalize | | ADR-0009, ADR-0012 |

ADR-0011 already did the right foundational work: a PROV-O profile, PG-Schema as the formal schema, and a module structure. It treats modules as *documentation* units. This proposal turns them into *runtime* units.

### 1.2 Where it is wired in

| Place | What is hardcoded | Size | Frozen? |
|---|---|---|---|
| `domain/models.py` | `NodeType`, `EdgeType`, `EntityType`, `EventType`, `IntentType` enums and one Pydantic class per node type | 11 node classes, 20 edge types | yes (Phase 1) |
| `docker/neo4j/constraints.cypher` | one uniqueness constraint per label, one vector index on `Entity` | 11 constraints | yes (Phase 0) |
| `adapters/neo4j/queries.py`, `user_queries.py`, `maintenance.py` | Cypher with literal labels and relationship types | 68 query constants; about 234 label/type references | `store.py` frozen (Phase 2) |
| `adapters/llm/client.py` `_ONTOLOGY_SCHEMA` | the extraction prompt lists entity types, preference and skill taxonomies | one prompt | no |
| `domain/extraction.py` | `Literal[...]` types on extracted entities and preferences | 6 models | no |
| `settings.py` | intent × edge-type weight matrix | 81 enum references | yes (Phase 1) |
| `domain/intent.py` | keyword lists per intent | 8 intents | no (Phase 3 frozen: scoring only) |
| `worker/*.py` | routing on `event_type` strings (`system.session_end`, `system.*`) | a few lines | no |

### 1.3 Three properties that make PDLC hard today, and two that make it easy

Hard:
1. **Every node type has its own key name** (`event_id`, `entity_id`, `summary_id`, `user_id`, `preference_id`, …). Generic code cannot upsert or fetch "a node" without a per-type branch.
2. **Retrieval is event-seeded.** `GET_EVENT_NEIGHBORS_BATCH` starts from `(:Event {event_id})` and follows outgoing edges. A question that starts at a Requirement, a Service or a PR has no entry point.
3. **The only domain structure comes from LLM extraction.** Consumer 1 (`domain/projection.py`) projects Event nodes plus FOLLOWS and CAUSED_BY and nothing else. Everything typed comes from Consumer 2's LLM pass over chat. PDLC needs deterministic, rule-based projection of tool events.

Easy:
4. **The ledger is ontology-neutral.** An event is an envelope plus a payload reference. Nothing about the event store needs to know about Requirements or PRs.
5. **Neo4j is a rebuildable projection** (ADR-0003, ADR-0005). A new or changed ontology can be applied by replaying the ledger into a fresh graph. The Atlas response is also neutral: `node_type` is a string and `attributes` is a dict.

So the middle of the system (projection, extraction, Cypher, retrieval weights) is where the ontology is welded in. The edges (ledger in, Atlas out) are already generic.

## 2. What the research says a PDLC ontology should look like

### 2.1 Sources and what each contributes

| Source | What it is | What we take |
|---|---|---|
| **Jetstream spine** (internal grounding doc) | Request → Intake (Spec, Decompose, Sequence) → Change → Pull Request (adversarial review, merge) → CI → environment gate → Deploy → Observe → Detect → Diagnose → Mitigate → RCA → Escape back to Request | the backbone and the feedback loop; the four C6 call sites (Spec, Triage, Specification by reference, pinned review snapshot) |
| **OSLC** (OASIS Open Services for Lifecycle Collaboration) | interoperability standard for lifecycle tools: RM (Requirement, RequirementCollection), CM (ChangeRequest), QM (TestPlan, TestCase, TestScript, TestExecutionRecord, TestResult), AM | artifact types and the trace-link vocabulary (implements, validates, affects, tracks); forward plus back links |
| **CDEvents** (CD Foundation, spec v0.5) | common vocabulary for delivery events in six buckets: core (pipelineRun, taskRun), source control (repository, branch, change), CI (build, artifact), testing (testCaseRun, testSuiteRun), CD (environment, service), operations (incident, ticket); each event has id, source, type, timestamp, subject, and links of kind PATH, RELATION or END | the event type taxonomy for the ledger, and event chains (links) that map onto CAUSED_BY |
| **Backstage software catalog** | Domain, System, Component, API, Resource, User, Group with ownedBy, partOf, providesApi, dependsOn, memberOf | the "what exists and who owns it" layer |
| **OMG Essence** | seven alphas (Opportunity, Stakeholders, Requirements, Software System, Work, Team, Way of Working), each a state machine | lifecycle states as first-class data; progress = state transitions |
| **Palantir Foundry ontology** | object types, properties, link types, **action types** (governed edits), **interfaces** (shapes shared across types) | interfaces for generic retrieval; action types as the model for governed writes |
| **W3C PROV-O** (already adopted, ADR-0011) | Activity, Entity, Agent, derivation, revision | stays the foundation; every PDLC node keeps provenance back to events |
| 2026 literature already in the pack | TraceDev (requirement → design → code → test graph), MOOSEDev (supersession, completeness and negation questions at 0.98–1.00 vs 6–27 % for top-k vector), EA-Graph (content anchoring: a claim about code is unprovable once its anchor hash changes), ProjectMem (append-only typed dev events, pre-action warnings), trust-aware traceability (confidence on links) | which questions the graph must answer, and why links need confidence and anchors |

### 2.2 Design principles that fall out

1. **Reuse vocabularies; invent only the glue.** Engram should not publish its own word for "test case" or "change merged". Map to OSLC and CDEvents and keep the mapping in the pack.
2. **Keep three layers apart.**
   - *What happened*: events in the ledger (CDEvents-shaped for tools, OTel-shaped for agents).
   - *What exists*: artifacts and catalog items with lifecycle state (Requirement, Change, Service).
   - *What we believe*: claims with confidence and provenance (Decision, Constraint, Lesson, inferred trace links).
   Agent-centric Engram blurred these because nearly everything was a belief extracted from chat. PDLC makes the split unavoidable: a merged PR is a fact, "this PR probably caused that incident" is a belief.
3. **Lifecycle is state on the node; transitions are events.** `Requirement.status` moves proposed → accepted → implemented → verified → retired, and each move is an event in the ledger. "As of position X" snapshots then come for free.
4. **Every trace link carries confidence, method and provenance.** Declared links (a PR body says `Fixes JIRA-123`) get confidence 1.0 and `method: declared`. Inferred links (LLM or embedding) get a score and `method: inferred`, and never silently become declared.
5. **Claims are anchored to content.** A Decision about `payments/refund.py` stores the path and content hash it was made against. When the file changes, the claim becomes "unverified", not silently stale.
6. **Interfaces, not label explosions, drive generic code.** Retrieval and retention should ask "is this node `Lifecycled`? `Owned`? `Anchored`?" rather than enumerate 30 labels.
7. **The agent ontology stays.** Agents do PDLC work. An agent session's `tool.execute` event links to the Change it produced with the existing `REFERENCES {role: result}` edge. The PDLC pack sits beside the agent pack, joined through shared nodes.

### 2.3 Questions the PDLC graph must answer (drives the retrieval profile)

| Question | New intent | Traversal |
|---|---|---|
| Why does this code / decision exist? | `why` (exists) | Change → IMPLEMENTS → WorkItem → DECOMPOSES ← Spec ← REFINES Request; Decision → DECIDED_IN → Event |
| Trace this requirement end to end | `trace` | Requirement → REFINED_BY → DesignElement → IMPLEMENTED_BY → Change → DEPLOYED_IN → Deployment |
| Which requirements have no design, no test, no deploy? | `completeness` | set difference over REFINES, VERIFIES, DEPLOYS |
| What is the current, non-superseded decision on X? | `status` | SUPERSEDES chains plus validity windows |
| If I change this component, what is affected? | `impact` | DEPENDS_ON, PROVIDES_API, CONSTRAINS downstream |
| Before I do X, what should I know? | `preflight` | Lessons (avoid), open Incidents on the Service, failing TestCases, Constraints scoped to the target |
| Who owns this and who decided it? | `who_is` (exists) | OWNED_BY, DECIDED_BY |
| What did the Spec rely on when it was written? | (snapshot read) | C6 `snapshot(scope, as_of)`; the pack version is part of the snapshot manifest |

## 3. Proposed PDLC ontology (`pdlc` pack, MVP)

Full machine-readable draft: [`pdlc.pack.yaml`](pdlc.pack.yaml). Summary here.

### 3.1 Node types (16), grouped by spine stage

| Stage | Type | Key | Lifecycle states | Interfaces | Standard mapping |
|---|---|---|---|---|---|
| Intake | `Request` | source system id | new → triaged → accepted → rejected / done | Lifecycled, Owned | Essence Opportunity |
| Intake | `Spec` | doc id + version | draft → approved → superseded | Lifecycled, Anchored, Versioned | OSLC RequirementCollection |
| Intake | `Requirement` | spec id + local id | proposed → accepted → implemented → verified → retired | Lifecycled, Anchored | OSLC rm:Requirement, Essence Requirements |
| Intake | `Decision` | content hash | proposed → accepted → superseded → reversed | Lifecycled, Anchored, Claim | ADR |
| Intake | `Constraint` | content hash | active → relaxed → retired | Lifecycled, Claim, **non-compressible** | |
| Design | `DesignElement` | doc id + section path | draft → reviewed → approved → superseded | Lifecycled, Anchored, Versioned | OSLC am:Resource |
| Work | `WorkItem` | tracker key (e.g. JIRA-123) | open → in_progress → done → cancelled | Lifecycled, Owned | OSLC cm:ChangeRequest, CDEvents ticket |
| Change | `Change` | repo + PR number | open → reviewed → merged / abandoned | Lifecycled, Anchored | CDEvents change |
| Change | `Review` | change id + review id | commented → approved / changes_requested | | |
| Verify | `TestCase` | repo + test id | active → quarantined → retired | Lifecycled | OSLC qm:TestCase |
| Verify | `TestRun` | run id | queued → running → passed / failed / error | | OSLC qm:TestExecutionRecord, CDEvents testCaseRun |
| Deploy | `Deployment` | environment + artifact + time | started → succeeded / failed / rolled_back | Lifecycled | CDEvents service.deployed |
| Operate | `Service` | catalog name | experimental → production → deprecated | Owned, Lifecycled | Backstage Component, Essence Software System |
| Operate | `Incident` | incident id | detected → mitigated → resolved → postmortem_done | Lifecycled, Owned | CDEvents incident |
| Org | `Team` | catalog name | | | Backstage Group, Essence Team |
| Learn | `Lesson` | content hash | tentative → validated → deprecated | Claim | (new; outcome feedback) |

People stay as the existing `Entity(entity_type=user)` and `UserProfile`; agents stay as `Entity(entity_type=agent)`. Tier 2 types for later: Epic/Milestone (as WorkItem kinds), Build and Artifact (CI), Environment, System, API, Runbook, RCA/Postmortem, AcceptanceCriterion, Assumption.

### 3.2 Edge types (18)

| Edge | From → To | Properties | Mapping |
|---|---|---|---|
| `REFINES` | Spec → Request; Requirement → Spec; DesignElement → Requirement | | OSLC refines |
| `DECOMPOSES_INTO` | Spec / WorkItem → WorkItem | order | Jetstream Decompose |
| `IMPLEMENTS` | Change → WorkItem / Requirement / DesignElement | confidence, method | OSLC implementsRequirement |
| `VERIFIES` | TestCase → Requirement / Change | confidence, method | OSLC validatesRequirement |
| `EXECUTES` | TestRun → TestCase | | OSLC executesTestScript |
| `RAN_AGAINST` | TestRun → Change | commit sha | CDEvents testCaseRun subject |
| `REVIEWS` | Review → Change | | |
| `DEPLOYS` | Deployment → Change | | CDEvents service.deployed |
| `DEPLOYED_TO` | Deployment → Service | environment | |
| `DECIDED_BY` | Decision → Entity(user/agent) | | PROV wasAttributedTo |
| `CONSTRAINS` | Constraint → Requirement / DesignElement / Service / WorkItem | scope | |
| `DEPENDS_ON` | WorkItem → WorkItem; Service → Service | kind (blocks, needs) | Backstage dependsOn |
| `OWNED_BY` | Service / WorkItem / Request → Team / Entity(user) | | Backstage ownedBy |
| `AFFECTS` | Incident → Service | | CDEvents incident subject |
| `ATTRIBUTED_TO` | Incident → Change / Deployment | confidence, method | (belief, never declared by default) |
| `REMEDIATES` | Change → Incident | | |
| `RAISES` | Incident → Request | | Jetstream escape → intake feedback loop |
| `LEARNED_FROM` | Lesson → Incident / Change | | outcome provenance |

Reused from core without change: `SUPERSEDES` (extended to Decision, Spec, DesignElement), `CONTRADICTS` (Decision, Constraint), `DERIVED_FROM` (any PDLC node → the Event that observed it), `REFERENCES` (agent Event → PDLC node, role `object` or `result`), `CAUSED_BY` (event chains from CDEvents links), `SAME_AS` (cross-tool identity, e.g. a GitHub issue and a Jira ticket for the same work).

### 3.3 Events

Tool events follow CDEvents, mapped into Engram's dot pattern `^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$` under a `pdlc.` prefix, with the original CDEvents type kept in the payload:

| Engram `event_type` | CDEvents type | Projection |
|---|---|---|
| `pdlc.change.created` / `.reviewed` / `.merged` / `.abandoned` | `dev.cdevents.change.*` | upsert Change; transition state; IMPLEMENTS from `Fixes KEY-n` references |
| `pdlc.testcaserun.finished` | `dev.cdevents.testcaserun.finished` | upsert TestRun, EXECUTES, RAN_AGAINST |
| `pdlc.service.deployed` / `.rolledback` | `dev.cdevents.service.*` | upsert Deployment, DEPLOYS, DEPLOYED_TO |
| `pdlc.incident.detected` / `.resolved` | `dev.cdevents.incident.*` | upsert Incident, AFFECTS |
| `pdlc.ticket.created` / `.updated` / `.closed` | `dev.cdevents.ticket.*` | upsert WorkItem; transition state |
| `pdlc.request.created`, `pdlc.spec.approved`, `pdlc.requirement.changed`, `pdlc.design.section_changed`, `pdlc.decision.recorded` | none (CDEvents stops at the code boundary) | upsert intake artifacts with content hash |

CDEvents `links` (PATH, RELATION) become CAUSED_BY edges between events, so a deploy can be traced back to the change and the pipeline run without inference.

### 3.4 One worked example

A GitHub PR is merged. The webhook adapter writes this event to the ledger (payload abbreviated):

```json
{"event_type": "pdlc.change.merged", "session_id": "repo:payments", "agent_id": "github",
 "payload": {"cdevents_type": "dev.cdevents.change.merged.0.2.0", "repo": "payments", "number": 812,
             "title": "Refund retries respect idempotency key", "body": "Fixes PAY-341",
             "merge_sha": "9f2c…", "files": ["refund/retry.py"]}}
```

The `pdlc` pack's projection rule for `pdlc.change.merged` (no LLM, no code change) produces:

```
(:Change {key:"payments#812", status:"merged", title:…, merge_sha:"9f2c…"})
(:Change)-[:IMPLEMENTS {confidence:1.0, method:"declared"}]->(:WorkItem {key:"PAY-341"})
(:Change)-[:DERIVED_FROM]->(:Event {event_id:…})          // provenance
```

Two weeks later `pdlc.incident.detected` arrives for the `refunds` service. The incident is linked to the service deterministically (AFFECTS). Whether this Change *caused* it is a belief: an enrichment job proposes `ATTRIBUTED_TO {confidence: 0.62, method: "inferred"}` and a human or a typed gate confirms it. A later `preflight` question from an agent about editing `refund/retry.py` returns that incident and any Lesson learned from it.

## 4. Ontology as a first-class citizen: ontology packs

### 4.1 What a pack contains

A pack is one versioned directory (or YAML file) with seven sections. Each section feeds one runtime component.

| Section | Contents | Feeds |
|---|---|---|
| `types` | node types (key fields, properties with types, required fields, lifecycle state machine, interfaces, embed and text fields), edge types (endpoints, properties, cardinality, whether confidence and method are required) | registry, validation, DDL generation, Pydantic model generation |
| `events` | event types the pack owns, aliases to external standards (CDEvents, OTel) | ingest validation, OTel/CDEvents adapters |
| `projection` | rules: event type pattern → node upserts (key template, property paths into the payload) → edge upserts → lifecycle transitions | generic projector (deterministic Consumer 1 work) |
| `extraction` | which types the LLM may propose, descriptions, examples, confidence ceilings per source | generated extraction prompt and output schema (Consumer 2) |
| `retrieval` | intents (description, examples, keywords), intent → edge weights, seed node types per intent, traversal bounds, which fields are embedded or text-indexed | intent classifier, retrieval weights, index creation |
| `lifecycle` | decay class per type (Constraint pinned and non-compressible; TestRun short-lived), consolidation rules, retention tier overrides | decay scoring, consolidation, forgetting |
| `mappings` | PROV-O, OSLC, CDEvents, Backstage terms per type and edge; synonym lists (SKOS-style) for entity resolution | export, interop, entity resolution, C6 response normalisation |

Plus a header: `name`, `version` (semver), `requires` (other packs, e.g. `core>=1.0`), `owner`.

### 4.2 Runtime building blocks

```
             packs/*.yaml
                  │  load + validate + compose (core + user + pdlc + …)
                  ▼
          OntologyRegistry  ──────────────── version hash ──► stamped on every projection and C6 snapshot
     (domain/, pure Python)
      │        │         │          │            │
      ▼        ▼         ▼          ▼            ▼
  Generic   Extraction  Retrieval  Lifecycle   Schema/DDL
  Projector  profile    profile    rules       generator
  (rules →   (prompt +  (intents,  (decay,     (Neo4j constraints
   GraphOps)  schema)    weights,   retention)   and indexes today,
      │                  seeds)                  Spanner tables later)
      ▼
  GraphStore port: generic ops
    upsert_nodes(type, rows) · upsert_edges(type, rows) · transition(type, key, state)
    get_node(type, key) · neighbors(seed_ids, edge_types, direction, limit) · vector_seeds(type, vector, k)
      │
      ├── Neo4j adapter (generic Cypher with labels validated against the registry)
      └── Spanner adapter (later)

  Query plugins: packs may ship named, hand-written queries for things generic ops cannot express well
  (today's user_queries.py becomes the `user` pack's plugin).
```

Key decisions inside this:

1. **Uniform identity.** Every projected node gets `node_id` (deterministic: `<type>:<key>`) and `node_type`, alongside its existing per-type key (`event_id`, `entity_id`, …) for backward compatibility. Generic code only ever uses `node_id`.
2. **One primary label per node, interfaces in the registry.** Do not rely on Neo4j multi-labels (`:Artifact:Requirement`) for interface membership. Spanner's dynamic-label mode is built around a label column per row, so the portable choice is one label plus registry lookup.
3. **Labels are data, but never user input.** Generic Cypher interpolates labels and relationship types only after checking them against the registry, so there is no injection path. (Neo4j 5.26 also added dynamic labels in `MATCH`/`MERGE`; we run `neo4j:5-community`, so confirm the pinned minor before relying on it.)
4. **Retrieval can seed from any type.** The neighbour query takes `node_id` seeds and both directions, with edge types and weights from the active packs.
5. **Ontology version is part of the projection.** The registry hashes the composed packs. Each Neo4j database (or graph) records the hash it was built with. C6 snapshot manifests record it too, which answers the Jetstream question "does the schema live in a backend or the gateway?": it lives in a versioned pack, and the version travels with every snapshot.

### 4.3 How an ontology change is applied

| Change | Example | How it is applied |
|---|---|---|
| Additive | new node type, new edge type, new optional property, new intent | hot: reload registry, create constraints and indexes, new events project immediately; replay old events only if the new rule should cover history |
| Mapping change | a projection rule now reads a different payload field | replay affected event types into the live graph (MERGE is idempotent) |
| Breaking | rename a type, change a key, split a type, change edge direction | blue/green: build a fresh projection from the Redis ledger under the new pack version, run the eval suite against it, switch the read alias, drop the old graph |

The ledger never changes. This is why Engram can treat ontology as data where most graph systems cannot: the graph is a function of (events, pack version).

### 4.4 Impact of importing a new ontology, today vs with packs

| Layer | Today, to add PDLC | With packs |
|---|---|---|
| Ingest (API, ledger) | add `EventType` members (frozen enum) or rely on free strings | declare event types in the pack; ingest validates against the registry; nothing else changes |
| Source adapters | new webhook code per tool | same: one adapter per tool (GitHub, Jira, CI, PagerDuty) that emits CDEvents-shaped events; the adapter knows nothing about the graph |
| Projection | new consumer code; `domain/projection.py` only knows Event | write projection rules in the pack; the generic projector runs them |
| Graph schema | edit `constraints.cypher` (frozen) and `models.py` (frozen) | DDL generated from the pack |
| Store / queries | new Cypher module with literal labels | generic ops; optional query plugin for specialised reads |
| Extraction | edit the hardcoded prompt and `Literal` types | extraction profile generates prompt and schema |
| Retrieval | edit the intent-weight matrix (frozen settings) and keyword lists; add an artifact seed path | retrieval profile; seeds from any type |
| Decay / retention | edit per-label logic in `maintenance.py` | lifecycle section |
| API | new routes | none needed: Atlas is already generic; add `GET /v1/ontology` to list packs, types and version |
| Evaluation | none per domain | each pack ships a question set (MOOSEDev-style for PDLC) and must pass it before its retrieval weights are trusted |

What packs cannot remove: a source adapter per external tool, and an evaluation set per domain. Retrieval weights are domain knowledge and have to be measured, not guessed. Those are the honest costs of a new domain.

### 4.5 Format choice

Two options:
- **LinkML.** A real modelling standard that already generates Pydantic, JSON Schema, OWL and SHACL, and documents property-graph modelling. It has no native place for projection rules, intents or lifecycle; those would live in annotations.
- **Engram's own YAML manifest**, validated by a Pydantic meta-model in `domain/ontology.py`.

Recommendation: own manifest now, shaped so the `types` section converts cleanly to LinkML, and add a LinkML export later when an external consumer needs OWL or SHACL. Reason: the parts that make a pack useful to Engram (projection, retrieval, lifecycle) are exactly the parts LinkML does not model, and adding a code-generation dependency to the critical path is not worth it in phase 1.

## 5. Plan

| Phase | Weeks | Deliverable | Done when |
|---|---|---|---|
| 0 | 1 | `domain/ontology.py` meta-model + `OntologyRegistry`; today's schema written as `core`, `memory` and `user` packs | generated constraints equal `constraints.cypher`; registry type list equals the enums in `models.py`; no behaviour change |
| 1 | 2 | uniform `node_id`/`node_type` on new writes; generic `upsert_nodes`/`upsert_edges`/`transition` on the GraphStore port; generic projector; PDLC pack MVP; GitHub and Jira webhook adapters emitting `pdlc.*` events | replaying a public repository's history (python/peps, apache/kafka KIPs + Jira, already proposed for the experiment datasets) builds a PDLC graph with no hand-written Cypher |
| 2 | 2 | retrieval reads intents and weights from the registry; artifact-seeded neighbour query; PDLC intents (`trace`, `completeness`, `status`, `impact`, `preflight`) | a MOOSEDev-style question set over the seeded PDLC graph beats top-k vector retrieval on supersession, completeness and negation |
| 3 | 2 | extraction profile generation (Decision and Constraint from documents and threads); pack versioning; blue/green re-projection; `GET /v1/ontology` | a breaking pack change is applied by rebuild and switch with the eval suite as the gate |
| 4 | later | second backend behind the same generic port | see the Spanner gap analysis |

Contract-freeze note: `models.py`, `settings.py`, `store.py` and the Phase 0 infra files are frozen against signature and field changes. Every step above is additive: new files, new methods, new optional fields. The enums stay and become the generated constants of the `core` pack.

## 6. Decisions needed

1. Accept the pack approach and the draft [ADR-0018](../../../adr/0018-ontology-packs.md) (proposed, amends ADR-0011's module structure from documentation units to runtime units).
2. Accept the PDLC MVP type list in §3, or trim it. The smallest useful cut is Request, Requirement, Decision, Constraint, WorkItem, Change, TestRun, Deployment, Incident, Service.
3. Which tools emit first: GitHub and Jira are assumed. Confirm, or name the internal equivalents.
4. Where the PDLC pack's owner sits. The pack is reviewed like code; someone has to own its weights and its eval set.

## Sources

External: [CDEvents spec](https://github.com/cdevents/spec), [CD Foundation, CDEvents in action](https://cd.foundation/blog/2023/12/05/cdevents-in-action/), [OSLC specifications](https://www.open-services.net/specifications), [OSLC Change Management 3.0](https://docs.oasis-open.org/oslc-domains/cm/v3.0/cs01/part1-change-mgt/cm-v3.0-cs01-part1-change-mgt.html), [OSLC Quality Management](https://open-services.net/spec/qm/latest-draft), [Backstage system model](https://backstage.io/docs/features/software-catalog/system-model), [OMG Essence overview (Linköping course notes)](https://www.ida.liu.se/~TDDE46/theory/essence.pdf), [Palantir ontology core concepts](https://www.palantir.com/docs/foundry/ontology/core-concepts), [LinkML property-graph how-to](https://linkml.io/linkml/howtos/model-property-graphs.html), [LinkML Pydantic generator](https://linkml.io/linkml/generators/pydantic.html).
Internal: ADR-0009, ADR-0011, ADR-0012; `docs/research/2026-09/pdlc-memory-layer.md` (first PDLC sketch, superseded in part by §3 here); `docs/research/2026-09/pdlc-grounding/jetstream-reference-transcription.md` (spine, C6, ontology dimensions); `docs/research/ontology-*.md` (February ontology research).
