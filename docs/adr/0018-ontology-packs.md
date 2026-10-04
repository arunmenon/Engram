# ADR-0018: Ontology Packs — Domain Ontologies as Versioned, Pluggable Runtime Modules

Status: **Approved** by the project owner, 2026-10-04 (recorded at their request; implementation notes below)
Date: 2026-10-04
Amends: ADR-0011 (module structure becomes runtime, not documentation-only), ADR-0009 (intent weights and seed types become pack data), ADR-0012 (the cg-user module becomes the `user` pack), ADR-0013 (extraction prompt and output schema are generated per pack)
Design note: `docs/research/2026-10/ontology/pdlc-ontology-and-ontology-packs.md`

## Context

Engram's ontology (ADR-0009, ADR-0011, ADR-0012) is agent-centric: OTel GenAI event types, six entity types, a user model and a memory model. It is hardcoded in frozen enums (`domain/models.py`), a frozen constraints file, about 68 hand-written Cypher queries with literal labels, the extraction prompt, the intent-weight matrix in `settings.py`, and intent keyword lists.

Two requirements now press on this:

1. **PDLC.** The product development lifecycle needs artifact types (Request, Spec, Requirement, Decision, Constraint, WorkItem, Change, TestRun, Deployment, Service, Incident, …), trace-link edges with confidence, lifecycle states, and deterministic projection from tool events (CDEvents-shaped webhooks) rather than LLM extraction from chat.
2. **Domain ontologies in general.** Engram should be able to take on a new domain ontology without editing the frozen core each time.

ADR-0011 already defined modules (cg-core, cg-events, cg-entities, cg-memory, …) as documentation units. Engram's ledger is ontology-neutral and its graph is a rebuildable projection (ADR-0003, ADR-0005), so the graph can be treated as a function of (events, ontology version).

## Decision

1. **An ontology is a pack**: a versioned, declarative manifest with sections `types`, `events`, `projection`, `extraction`, `retrieval`, `lifecycle`, `mappings`, plus a header (`name`, `version`, `requires`, `owner`). The meta-model is a Pydantic model in `domain/ontology.py` (pure domain, no framework imports).
2. **An `OntologyRegistry` composes the active packs** (always `core`; plus e.g. `memory`, `user`, `pdlc`), validates them (no dangling edge endpoints, no name collisions, declared events for every projection rule, known edges in every intent weight), and exposes lookups. It computes an **ontology version hash** of the composed packs.
3. **Today's schema becomes the `core`, `memory` and `user` packs.** The existing enums stay as the generated constants of these packs. No existing field or signature changes.
4. **Generic building blocks read from the registry**: a generic projector (projection rules → upsert/transition graph operations), generated extraction prompts and output schemas, registry-driven intents, weights and seed types, lifecycle and retention rules, and DDL generation per graph backend.
5. **Uniform identity**: every node written through the generic path carries `node_id` (`<type>:<key>`) and `node_type`, alongside existing per-type keys.
6. **One primary label per node.** Interface membership (Lifecycled, Owned, Anchored, Versioned, Claim) lives in the registry, not in extra labels, to stay portable across graph backends.
7. **The GraphStore port gains generic operations** (`upsert_nodes`, `upsert_edges`, `transition`, `get_node`, `neighbors`, `vector_seeds`) as new methods. Packs may ship named query plugins for reads the generic operations cannot express.
8. **Ontology changes are applied by projection, never by mutating the ledger.** Additive changes load hot. Mapping changes replay affected event types. Breaking changes build a fresh projection under the new version (blue/green) and switch after the pack's evaluation set passes.
9. **The ontology version is recorded** on every projection and in every C6 snapshot manifest.
10. **Every pack that adds retrieval intents ships an evaluation question set**, and its weights are not trusted in production until that set passes.
11. **Backend neutrality.** All new domain code (projector, PDLC queries, connectors) uses only the generic GraphStore operations, never backend query text. The generic operations are designed to the stricter of Neo4j and Spanner Graph semantics: one label per node, edge identity includes edge type, upserts are explicit (no reliance on Cypher `MERGE` behaviour), both edge directions are queryable, and history comes from the ledger. A backend conformance suite (same events in, same answers out) runs against Neo4j now, and against the Spanner emulator as soon as the generic operations are stable.

## Consequences

Positive:
- A new domain is a pack, a source adapter and an evaluation set, instead of edits to five frozen contracts.
- The graph backend sees a small generic surface, which reduces the cost of a second backend (see the Spanner gap analysis).
- Ontology version becomes explicit, which C6 snapshots and replay need.

Negative:
- A projection-rule mini-language must be specified, implemented and kept small. Risk: it grows into a programming language. Mitigation: rules cover upsert, edge, transition and simple payload functions only; anything else is a query plugin or code.
- Generic Cypher with registry-validated labels is less hand-tuned than today's queries; hot paths may need plugins.
- Retrieval weights for a new domain are unknown until measured.

## Alternatives considered

- **Keep extending enums per domain.** Rejected: every domain edits frozen contracts, and the agent-centric assumptions (event-seeded retrieval, LLM-only typing) remain.
- **Fully schemaless graph with no registry.** Rejected: loses validation, endpoint rules, lifecycle and retrieval semantics, which are the reasons Engram has an ontology.
- **LinkML as the pack format.** Deferred: strong for types and code generation but has no native home for projection, retrieval or lifecycle. The `types` section is kept LinkML-convertible.
- **RDF/OWL runtime.** Rejected for the same reasons as ADR-0011 alternative 2.

## Implementation notes

### Phase 0: packs load, nothing changes (2026-10-04)

| Item | Where | Notes |
|---|---|---|
| Pack format | `domain/ontology.py` | **Shape:** Pydantic models for every pack section; unknown keys are errors. **Names:** node types are PascalCase, edge types UPPER_SNAKE_CASE and properties snake_case, because these names reach backend query text. **Type references:** bare names mean the pack's own types, and `pack:Type` means another pack's. |
| Registry | `domain/ontology.py` (`OntologyRegistry`) | **Composition:** the active packs, always including `core`. **Checks:** required packs and versions; unique names across packs; edge endpoints; interfaces; and that key, text, embed and index fields are declared properties. **Projection rules:** declared events, keys matching the type's key, known properties, legal states, and edges allowed between the referenced types. **Retrieval:** weights name known edges and intents. **Lifecycle:** decay rules and terminal states name known types and states. **Reporting:** every problem is reported at once. **Version:** a hash of the composed packs that does not depend on load order. |
| Loader | `ontology/loader.py` | **Parsing:** strict YAML (see the review round below). **Resolution:** the base packs `core`, `memory` and `user` and every required pack are loaded automatically. **Settings:** `CG_ONTOLOGY_PACKS` names the packs added to the base packs, comma-separated, default `pdlc`; `CG_ONTOLOGY_PACK_DIRS`. |
| Today's schema as packs | `ontology/packs/core.pack.yaml`, `memory.pack.yaml`, `user.pack.yaml` | **Split:** `core` holds Event, Entity, Summary, the core edges and seven intents; `memory` holds Belief, Goal and Episode; `user` holds the ADR-0012 types and the `personalize` intent. **Identity:** existing types keep their unique property (`id_property`). `SUPERSEDES`, `CONTRADICTS` and `DERIVED_FROM` are declared in `core`, and other packs add endpoints (`extends_core_edges`). |
| Neo4j schema | `adapters/neo4j/ontology_schema.py` | Generates constraints and indexes from the registry. Types without an `id_property` get a uniqueness constraint on `node_id`. |
| PDLC pack | `ontology/packs/pdlc.pack.yaml` (the docs copy is kept identical) | **Fix:** loading found that `Constraint` and `Lesson` are keyed by `content_hash` without declaring it. Released as **1.0.1**, which adds only that property. **Types:** the pack has 17 node types; the design note's 16 predates `Release`. |

Exit checks (`tests/unit/test_ontology_packs.py`):
- the registry's node, edge, event and intent types equal the enums;
- each node type's properties equal its model's fields;
- the intent weights, keywords and seed strategies equal `settings.INTENT_WEIGHTS` and `domain/intent.py`;
- the OTel aliases equal `OTEL_TO_EVENT_TYPE`;
- the generated Neo4j statements equal `constraints.cypher`;
- the PDLC pack loads.

Validation and parsing cases are in `tests/unit/test_ontology_registry.py`.

Behaviour is unchanged: nothing reads the registry yet. Phase 1 wires it into projection.

#### Phase 0 review round

An independent reviewer reported 21 findings on commit `0507231` and reproduced all but two of them. What was done with each:

| # | Finding | Severity | Outcome |
|---|---|---|---|
| 1 | Malformed `admission` rule crashed the registry, and a string was iterated character by character | should-fix | Fixed: typed `AdmissionRuleDef`; `include_for_intents` must be a list |
| 2 | A transition did not say which node it moves (`pdlc.change.reviewed` moves a Change it does not upsert) | blocking for phase 1 | Fixed: the target is the rule's upsert of that type, else the first keyed edge endpoint of that type, else an explicit `transition.key`; an unresolvable transition is an error |
| 3 | An edge's `requires` was not checked against the rules that create it (`AFFECTS`) | should-fix | Fixed: required link fields get the declared-link defaults (confidence 1.0, method `declared`, link status from the link policy); any other required field must be set by the rule |
| 4 | Interface edges were not checked against the types using the interface (`Incident` is Owned, but `OWNED_BY` did not start from it) | should-fix | Fixed: now validated; PDLC 1.0.2 adds `Incident` to `OWNED_BY` |
| 5 | A node property conflicting with its interface's type won silently | should-fix | Fixed: reported as a conflict |
| 6 | Rule expressions and expression-valued transitions were not validated | should-fix | Fixed: every rule value is parsed at load (`domain/pack_expressions.py`); `$event` fields are checked against the envelope; `map(...)` target states are checked |
| 7 | No range checks on numbers (NaN or negative weights, `max_depth: -3`, `max_confidence: 7`, `retain_days: 0`) | should-fix | Fixed |
| 8 | `*` in an extension opened an edge to every pack's types | should-fix | Fixed: `*` means every type of the pack that wrote it |
| 9 | Event, interface, intent and state names were not shape-checked | should-fix | Fixed |
| 10 | Bare event references resolved to any pack's event | nit | Fixed: bare means the pack's own events. The module docstring now states which sections use global type names |
| 11 | Duplicate lifecycle states, a type both proposed and never proposed, and mappings for unknown types were accepted | nit | Fixed |
| 12 | Pydantic lax mode reversed the YAML boolean rule (`no` → False, `'30'` → 30), and explicit tags got past it | should-fix | Fixed: pack models are strict; explicit tags other than plain scalars, lists and maps are errors |
| 13 | `!!set` made the version hash depend on `PYTHONHASHSEED` | should-fix | Fixed: such tags are rejected |
| 14 | Aliases allowed unlimited expansion ("billion laughs") | should-fix | Fixed: aliases are rejected |
| 15 | YAML 1.1 octal and sexagesimal integers, and merge keys | nit | Fixed: integers and floats are decimal only (no `.nan`/`.inf`); `<<` is an ordinary key |
| 16 | `CG_ONTOLOGY_PACKS` needed JSON, and setting it dropped `memory` and `user` | nit | Fixed: comma-separated; `core`, `memory` and `user` are always active, and the setting names extra packs |
| 17 | Edge properties in `core` and `user` differed from what the code writes | should-fix | Fixed: declared from the code's writers (`similarity_score`, SAME_AS/RELATED_TO `justification`/`resolved_at`, DERIVED_FROM provenance fields, INTERESTED_IN and HAS_SKILL fields). Today's code does not go through pack validation |
| 18 | UserProfile is keyed by `user_id` in `constraints.cypher` but MERGEd by `profile_id` in code | should-fix | Not changed: this inconsistency predates the packs, and `constraints.cypher` is frozen. The pack follows the constraint file and says so; no pack rule writes UserProfile. A separate task was raised |
| 19 | PDLC promised `Sourced` on every node, but only `Release` declared it | should-fix | Fixed: PDLC 1.0.2 makes every type Sourced |
| 20 | `node_id` had no separator or canonical value form, and `embed_fields` create no vector index | nit, unverified | `node_id` is defined in phase 1 (projector). Vector indexes for pack types are left to phase 2 (retrieval) |
| 21 | Constraint and index names could collide | nit | Fixed: type names that differ only by case are rejected; every key constraint is `<type>_pk`; indexing the key or a field named `pk` is rejected |

Regression cases are in `tests/unit/test_ontology_registry.py::TestReviewFindings`.

