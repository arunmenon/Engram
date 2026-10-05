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

### Phase 1: packs drive projection, PDLC from GitHub and Jira (2026-10-04)

| Item | Where | Notes |
|---|---|---|
| Generic graph operations (decision 7) | `ports/pack_graph.py` (`PackGraph`, part of `GraphBackend`) | **Operations:** `upsert_nodes`, `upsert_edges`, `change_states`, `get_nodes`, `find_nodes` and `neighbors`, plus `ensure_pack_schema`. **Addressing:** a node is `NodeRef(label, key, key_property)`. Today's types keep their own id property; pack types use `node_id`. **Semantics:** written to the stricter of Neo4j and Spanner Graph, as decision 11 requires. |
| Implementations | `adapters/graph_ops.py` (memory, Spanner); `adapters/neo4j/pack_graph.py` | **Neo4j:** UNWIND-batched Cypher with labels interpolated only after a fixed-shape check, and values passed as parameters. `ensure_pack_schema` runs the generated constraints. **Conformance:** `tests/conformance/test_pack_graph.py` passes on memory, Neo4j and the Spanner emulator. |
| Expression language | `domain/pack_expressions.py` | **Syntax:** `$.path`, `$.list[*].field`, `$event.field`, `+`, `regex`, `regex_all`, `match`, `sha256`, `map`, `each`. **Checking:** parsed and validated when a pack loads. |
| Projector | `domain/pack_projection.py` (plans, no I/O); `worker/pack_projection.py` (applies) | **Node identity:** `node_id = <Type>:<v1>\|<v2>`, with values canonicalised by property type and `%`/`\|` escaped. **What each written node gets:** `node_type`, `ontology_version`, `updated_at`, the lifecycle's initial state, `source_trust` and `DERIVED_FROM` to the event. **References:** endpoints named by key are created as stubs if missing. **Fan-out:** lists fan out, zipped by position. **Matching:** lookups resolve `to_latest` and `match_any_prefix`. **Link fields:** declared-link defaults fill required link fields. |
| Wiring | `worker/projection.py`, `worker/__main__.py`, `ontology/runtime.py`, `api/app.py` | **Worker:** after the structural projection of a batch, events whose type has pack rules are planned and applied in log order. They are acknowledged only after the pack writes succeed. **Start-up:** the worker and the API load the configured registry, so an invalid pack fails start-up, and call `ensure_pack_schema`. The API logs the ontology version. |
| Ingest check | `api/routes/events.py`; `OntologyRegistry.accepts_event_type` | **Rule:** a namespace owned by a pack other than `core`, `memory` or `user` (today: `pdlc`) accepts only declared event types (422 otherwise). **Unchanged:** today's agent event namespaces stay open. |
| Source adapters | `sources/github.py`, `sources/jira.py` | **Translation:** pure functions from webhook payload to `pdlc.*` events, which keep their CDEvents type in `payload.cdevents_type`. **GitHub:** pull requests, reviews, check runs, releases, deployment statuses and issues. **Jira:** issue created and updated. |
| Webhook routes | `api/routes/webhooks.py`: `POST /v1/webhooks/github`, `POST /v1/webhooks/jira` | **Authentication:** HMAC-SHA256 signature with `CG_WEBHOOK_<SOURCE>_SECRET`, not the API key. **Responses:** 401 for a bad signature, 503 when the source has no secret, 413 above `CG_WEBHOOK_MAX_BODY_BYTES`. **Idempotence:** event ids derive from the delivery id, so a redelivery is deduplicated. **Trust:** events are ingested as `agent_id = webhook:<source>`, and `CG_ONTOLOGY_TRUSTED_SOURCES` marks their nodes trusted. |
| PDLC pack 1.1.0 | `ontology/packs/pdlc.pack.yaml` | Additive rules for events the adapters emit: `ticket.created`, `ticket.closed`, `change.updated`, `change.abandoned` and `incident.resolved`. The default `CG_ONTOLOGY_PACKS` is `pdlc`, so PDLC is active unless configured otherwise. |

Tests:
- `test_pack_expressions.py`;
- `test_pack_projection.py`, which runs every PDLC rule on the in-memory graph;
- `test_webhooks.py`, which uses sample payloads in `tests/fixtures/webhooks`, hand-written to GitHub's and Jira's documented shapes, not recorded;
- `test_pdlc_end_to_end.py`. Signed GitHub and Jira deliveries go through the real API into the ledger, the real projection worker builds the PDLC graph, and assertions read it through `PackGraph` only. It runs on memory, the Spanner emulator, and Neo4j with an in-memory ledger.

Not done in phase 1:
- **Real repository history:** replaying a public repository's history (the design note's exit check) needs that history fetched, and it was not. The end-to-end test uses sample deliveries.
- **File lists:** pull-request webhooks carry no file list, so `TOUCHES` needs files from another source. The rule and the prefix lookup are tested.
- **Component catalogue:** no adapter yet imports Backstage-style component catalogues (path prefixes, owners).

#### Phase 1 review round

An independent reviewer reported 12 findings on commit `1d17aa0`. It reproduced most of them, against the live Neo4j and Spanner emulator where relevant, and found no Cypher injection path. What was done with each:

| # | Finding | Severity | Outcome |
|---|---|---|---|
| 1 | Any API-key client could post events as `agent_id: webhook:github` and get `source_trust: trusted`, or overwrite webhook-created nodes | blocking | Fixed: `POST /v1/events` (single and batch) refuses agent ids under `webhook:`. Only the signed webhook routes use them |
| 2 | An integer above int64 (rounded through `float`) made Neo4j raise in `upsert_nodes` and blocked the whole batch; precision was lost above 2^53 | blocking | Fixed: integers are parsed exactly and bounded to int64, and anything else writes nothing. Pack-rule failures are now isolated per event (finding 11) |
| 3 | A non-ASCII signature header caused a 500 | should-fix | Fixed: the signature must be 64 hex digits and is compared as bytes |
| 4 | The body size was checked after reading the whole body | should-fix | Fixed: `Content-Length` is checked first, and the stream is cut off at the limit |
| 5 | Fan-out picked list elements by position among surviving rows, so a release with one PR, or with one PR number missing, lost its sections | should-fix | Fixed: each fanned node or edge carries its original position, and list values are zipped by it |
| 6 | `to_latest` and `match_any_prefix` lookups depended on backend order and the lookup limit | should-fix | Fixed: `find_nodes` returns nodes ordered by key on every backend, and the latest is chosen among all fetched matches, ties broken by key. Reaching `lookup_limit` is logged as a warning. Prefixes match only on path boundaries |
| 7 | A late or replayed `opened` delivery moved a merged change back to `open`; a captured body replayed under a new delivery id was ingested again | should-fix | Fixed: `pdlc.change.created` reopens only an abandoned change (PDLC 1.2.0), and event ids derive from the signed body, so replays deduplicate |
| 8 | PackGraph backends differed: which end `neighbors(both)` reports, dict values, the count for repeated edges, and `find_nodes` order | should-fix | Fixed: one rule for the reported end, nested values stored as JSON text everywhere, each edge write whose endpoints exist counts, and key order. Each is now a conformance case |
| 9 | Create-only defaults and status changes were read-then-write on Spanner, a race with two replicas | should-fix, unverified | Fixed: the shared layer has overridable `_merge_nodes` and `_apply_state_changes`, and Spanner runs each in one read-write transaction. The in-memory backend is single-process |
| 10 | GitHub release notes link PRs by URL, which was missed; "Non-breaking" counted as breaking | should-fix | Fixed: `#n` and `/pull/n` are both read; breaking is matched as a word. Missing review and run ids skip the event; deployments name the service by the repository's full name (nit) |
| 11 | One failing pack rule left the whole flush batch unacknowledged | should-fix | Fixed: each event's pack plan runs on its own. A failure is logged, counted and dead-lettered for that event only, and the batch is acknowledged |
| 12 | Nits | nit | Fixed: list text joined for regexes is bounded; the docstring states how edges pair fanned ends; `closed_namespaces` is cached. Not changed: `NEIGHBOR_SCAN_CAP`, `MAX_TEXT_LENGTH` and `LATEST_ORDER` stay module constants with comments, because adapters and the domain do not read settings. The rule of thumb that a bare `#n` may name an issue is documented in the adapter |

Regression cases:
- `tests/conformance/test_pack_graph.py::TestReviewFindings`;
- `tests/unit/test_pack_projection.py::TestReviewFindings`;
- `tests/unit/test_webhooks.py::TestReviewFindings`;
- `tests/unit/test_projection_worker.py::TestPackFailureIsolation`;
- the spoofing case in `tests/unit/test_pdlc_end_to_end.py`.

This round also adds `PackGraph.search_nodes`, which phase 2 needs, with conformance cases on all backends. It also releases PDLC 1.2.0:
- intent keywords;
- `change.merged` sets title, body and files;
- the reopen guard.

### Phase 2: retrieval from packs (2026-10-04)

| Item | Where | Notes |
|---|---|---|
| Registry intents | `domain/pack_intents.py` (`RegistryIntents`) | **Algorithm:** the same as `domain/intent.py` (keyword matches, normalised confidences, the fallback intent, per-edge weights, seed strategy), but from the active packs. **Equivalence:** with today's packs it equals the fixed tables (`tests/unit/test_pack_intents.py`). **Event retrieval:** `RetrievalEngine` takes `intents=` and the API passes the registry's event intents. PDLC adds weights to `why`/`who_is` and changes nothing else for event queries. |
| Artifact retrieval | `retrieval/artifacts.py` (`ArtifactRetriever`); `POST /v1/query/artifacts` | **Intents:** those weighting pack edges, classified from the pack keywords (PDLC 1.2.0) or given. **Seeds:** given node ids; key-like tokens (`PAY-341`, `refund/retry.py`, `v1.4.0`, `#7`), with a node's own key ranked first; then stemmed words, cut relative to the best match. **Traversal:** best-first and bounded, along the intent's weighted edges in its direction. **Admission:** the pack rules. A node is superseded when its status says so or another node `SUPERSEDES` it, and is kept only for intents the rule lists. Untrusted nodes need a trusted neighbour in the answer. Proposed links keep their confidence. **Completeness:** the `missing_links` plugin is a set difference reporting `no_link`, `proposed_only` and `confirmed`, scoped by seeds and by lifecycle states named in the question. **Provenance:** from each node's newest `DERIVED_FROM` event. **Output:** the Atlas pattern. |
| Graph operation | `PackGraph.search_nodes` | Case-insensitive term match in text and list fields, on memory, Neo4j and Spanner, with conformance cases. Spanner and memory scan the label, which is acceptable at PDLC scale; a full-text or vector index path is future work. |
| Settings | `CG_ONTOLOGY_RETRIEVAL_SEED_LIMIT`, `..._NEIGHBOR_LIMIT`, `..._SEED_MIN_RATIO` | Depth and node bounds come from `CG_QUERY_*`. |

Evaluation (`tests/unit/test_pdlc_retrieval_eval.py`), the design note's phase 2 exit check:
- **Graph:** a payments project built mostly by projecting PDLC events. Catalogue, requirement, test-link, design and contradiction records are upserted directly, standing in for the catalogue importer and extraction.
- **Questions:** in the MOOSEDev classes of supersession, completeness and negation.
- **Baseline:** top-k text retrieval over the same seed types. It is lexical because no embedding model runs in tests, so it stands in for vector retrieval.
- **Results:** mean F1 with retrieval vs baseline. Supersession 1.00 vs 0.53, completeness 1.00 vs 0.33, negation 1.00 vs 0.67.
- **Further checks:** trace, why, preflight, impact, trust and bounds behaviour. Artifact queries also run through the API in `test_pdlc_end_to_end.py` on memory, Spanner (emulator) and Neo4j.
- **Caveat:** the numbers come from a small hand-built project, not real data.

Competency questions:
- **Exercised by these tests:**
  - CQ05/CQ10 (completeness);
  - CQ06/CQ15 (supersession);
  - CQ08 (negation);
  - CQ11/CQ12 (completeness);
  - CQ13 (why);
  - CQ14 (preflight);
  - CQ19 (trace);
  - CQ29 (untrusted).
- **Not yet answerable:**
  - `aggregate` (CQ18, CQ21, CQ22), which needs counts;
  - `temporal` filters ("last quarter", "last week"), which need time-scoped queries;
  - `similarity` (CQ03, CQ26), which needs embeddings of pack types;
  - `snapshot` (CQ04, CQ28), which needs the pinned-position read.


#### Phase 2 review round

An independent reviewer reported 18 findings on commit `1c9c0cf`, each with a reproduction script. Most were about completeness questions and about limits that cut answers silently. Event retrieval (`RetrievalEngine`) showed no regression. What was done with each:

| # | Finding | Severity | Outcome |
|---|---|---|---|
| 1 | Completeness read every candidate's links in one call capped at the neighbour limit, so later candidates were reported `no_link` (100 requirements tested 3 times each: 33 false `no_link`) | blocking | Fixed: neighbour reads are paged. A call that fills the limit is split by node, then by edge type, and only one node and one edge type that still fill it are cut, which sets `truncated`. Used by completeness, traversal, supersession and provenance |
| 2 | With no seeds, completeness looked at only the first `max_nodes` subjects, before the state filter, and did not say so | blocking | Fixed: subjects are read per named lifecycle state (`find_nodes(status=...)`) up to `CG_ONTOLOGY_RETRIEVAL_SCAN_LIMIT` (5000). All are counted; at most `max_nodes` are returned, and `truncated` is set when either limit cuts |
| 3 | When an edge allows both directions (REFINES), the inbound one was picked; "untested" did not name TestCase | blocking | Fixed: an edge allowed both ways is read in both directions. Type words match with plural and verb endings and an `un` prefix ("untested", "unreviewed"). The strongest edge to the earliest-named related type wins |
| 4 | "Without an approving review" counted any review | should-fix | Fixed: when the question names an enum value of the related type ("approving" → `verdict: approved`), only links to nodes with that value count |
| 5 | Completeness skipped admission, so untrusted and superseded subjects were reported | should-fix | Fixed: superseded subjects and untrusted ones (unless asked for) are left out. A link to an untrusted node counts as `proposed_only` at best |
| 6 | Completeness scope was too wide from other seeds (any intent edge, depth 3, both ways) and too narrow from seeds of the subject type (the seed only) | should-fix | Fixed: from other seeds, the subjects one artifact edge away ("tickets shipped in #9"). From seeds of the subject type, their descendants along subject-to-subject edges ("under PAY-300"), or else the seeds themselves |
| 7 | An untrusted source could corroborate its own item: its event wrote the edge from the trusted epic; proposed links counted too | should-fix | Fixed: every edge a projection rule writes carries `source_trust` from the event's source. Only a confirmed link that a trusted source wrote, to a trusted node, corroborates. Edges written before this change carry no trust and count as trusted until the graph is rebuilt |
| 8 | Intent ties and keyword-less queries were resolved by registry order. A query matching no keyword turned on every intent (`why` dominant), with provenance and session edges | should-fix | Fixed: a tie prefers an intent with a plugin. With no keyword match there is no dominant intent: every artifact intent's edges are used in both directions, and superseded items stay out. Artifact traversal follows only edges that join two pack types, never `DERIVED_FROM`, `REFERENCES` or `FOLLOWS`. PDLC 1.3.0 adds paraphrase keywords (lack, nobody, uncovered, no review) |
| 9 | A repo token ranked every change in the repo above the `#8` it named | should-fix | Fixed: the key bonus applies only when the token is the node's most specific (last) key value. A `#n` match scores 2, plus 0.5 when the question also names its other key values |
| 10 | Caller-given seeds went through the seed-limit cut and ranking | should-fix | Fixed: given seeds are always kept, first. The seed limit applies to seeds found from the question |
| 11 | Event nodes had no provenance; `who_is` reached ownership through shared provenance events | should-fix | Fixed: an Event node is its own provenance, and provenance edges are no longer traversed (finding 8) |
| 12 | No timeout | should-fix | Fixed: the route applies `CG_QUERY_DEFAULT_TIMEOUT_MS` and returns 504 |
| 13 | Unbounded graph calls (400 `#n` references → 400 `find_nodes`) and term lists | should-fix | Fixed: at most `CG_ONTOLOGY_RETRIEVAL_MAX_TERMS` (16) key tokens, words and numbers each, and `CG_ONTOLOGY_RETRIEVAL_MAX_GRAPH_CALLS` (400) graph calls per request. Hitting either sets `truncated`. A `#n` is looked up only on a type's last key field |
| 14 | `neighbor_limit` cut traversal silently and by edge-type name; "best-first" was breadth-first by level | should-fix | Fixed: paging (finding 1), with edge types asked in weight order. Within a level, nodes are admitted in path-score order, so `max_nodes` keeps the best paths. The docstring says "level by level". The hardcoded ×10 for provenance is gone |
| 15 | Six hand-written questions phrased to match the pack keywords | should-fix | Partly fixed: the set adds three paraphrases ("lack test coverage", "nobody tests", "tickets with no merged change implementing them"), and fixtures for the cases that would have caught findings 1–7. The eval is still small and hand-built; real-project questions remain future work |
| 16 | Question-specific stop words | nit | Fixed: removed |
| 17 | Route constants hardcoded, extra fields accepted, whitespace queries accepted, untrusted items returned as `direct` | nit | Fixed: `CG_ONTOLOGY_RETRIEVAL_MAX_QUERY_LENGTH` and `..._MAX_SEED_IDS`; unknown fields are 422; the query is stripped, and empty is 422; untrusted items returned on request are marked `untrusted` |
| 18 | Event `RetrievalEngine`: no regression found | — | No change |

Eval after the fixes, mean F1 with retrieval vs the baseline:
- supersession: 1.00 vs 0.53;
- completeness: 1.00 vs 0.17 (six questions, including the three paraphrases);
- negation: 1.00 vs 0.67.

Regression cases:
- `tests/unit/test_pdlc_retrieval_eval.py::TestReviewFindings`;
- `tests/unit/test_artifact_route.py`.

### Phase 3: extraction profiles, pack versioning, `GET /v1/ontology` (2026-10-04)

| Item | Where | Notes |
|---|---|---|
| Extraction profiles | `domain/pack_extraction.py` (`ExtractionProfile`) | **Generated:** one profile per pack with an `extraction` section. It provides the prompt (the proposable node and link types with descriptions, fields, synonyms, confidence ceilings and allowed endpoints; the never-proposed types; the known items the text may link to; the text) and a JSON Schema that accepts only those types. **Checked:** `plan()` turns the model's answer into a `ProjectionPlan`. Content-addressed types are keyed by the SHA-256 of their first text field, as the pack's rules compute it, so an extracted decision and the same decision recorded by a tool are one node. Confidence is capped at the pack's ceiling. Links must be between types the edge allows and end at a proposed node or a listed known item. `link_status` is never `confirmed`, and `source_trust` comes from the event's source. **Never overwrites:** every property but identity is a create-time default, so a proposal never changes a node that exists. Everything else is dropped and reported |
| Pack extraction consumer | `worker/pack_extraction.py`; `python -m context_graph.worker --consumer pack_extraction` | Its own consumer group (`CG_CONSUMER_GROUP_PACK_EXTRACTION`), so model latency never holds back projection. **Known items:** the nodes the pack's rules make from the same event, plus nodes of the link target types that share words with the text (`PackGraph.search_nodes`). **Model:** the `TextGenerator` port (`LLMExtractionClient.generate_text`). A missing answer raises, so the event is retried and then dead-lettered; an answer that is not JSON is logged and acknowledged. **Limits:** `CG_ONTOLOGY_EXTRACTION_*` (proposals per event, text length, known items, search terms). Links to nodes projection has not written yet are dropped, because both endpoints must exist |
| Change classification | `domain/pack_versioning.py` (`classify_change`) | **`additive`:** new types, edges, properties, states, events, intents, or changed lifecycle and extraction. **`mapping`:** a projection rule added or changed for an event type, applied by replaying those types. **`breaking`:** removed types, edges, events, states or rules; changed keys, property types or initial states; narrowed endpoints. **Version check:** each pack's version must rise with its content: major for breaking (minor before 1.0), minor for mapping or additive. **Eval:** a changed retrieval section requires the pack's evaluation set. **Adding PDLC to a live graph** is `mapping`: before it was active, its namespace was open, so the ledger may already hold `pdlc.*` events |
| Recorded version and reconcile | `ontology/versioning.py` | **Recorded:** each graph stores one `OntologyState` node through `PackGraph`: version hash, the packs' canonical JSON, when, how it was applied, and gate results. **On start**, the projection worker runs `reconcile`: initial or additive is recorded; mapping replays the changed event types from the ledger, then records; breaking refuses to start and names the rebuild command, unless `CG_ONTOLOGY_ALLOW_BREAKING` is set |
| Blue/green rebuild | `ontology/rebuild.py`; `python -m context_graph.ontology rebuild --target CG_KEY=VALUE` | **Build:** the same `ProjectionConsumer`, reading the whole ledger in order through `LedgerReplay` (a read-once `Subscription`), into the graph that the settings with the `--target` overrides select. **Gate:** every active pack with intents must pass its evaluation set. **Record:** the result goes into the new graph's state. A target that holds another version is refused unless `--force`. **Switch:** deploy with the same overrides. Neo4j Community has no database aliases, so this is a settings change and a restart, not a server-side alias. Enrichment, extraction and consolidation workers are run against the new graph afterwards |
| Evaluation sets | `ontology/evaluation.py`; `python -m context_graph.ontology evaluate` | **File:** `<pack>.eval.yaml` in `--eval-dir`, `CG_ONTOLOGY_PACK_DIRS` or the built-in pack dir, with questions, expected node ids, how to read the answer (`node_type`, `reasons`) and `min_f1`. **Scoring:** mean F1 over the questions, run through `ArtifactRetriever`. **No built-in PDLC set:** the questions must be about the deployment's own data. A pack with intents and no set fails the gate (decision 10) |
| `GET /v1/ontology` | `api/routes/ontology.py` | **Describes:** the packs and version hash, node types (key, properties, interfaces, lifecycle), edge types (endpoints, properties), event types, intents (keywords, weights, plugin, direction) and the extraction profiles (sources, proposable types, output schema). **Graph:** the version the graph records and the change kind between it and the loaded packs. API key required |

Tests:
- `tests/unit/test_pack_extraction.py`: profile, prompt, schema validated with `jsonschema`, accepted and rejected proposals, never overwriting, and the consumer with a scripted model.
- `tests/unit/test_pack_versioning.py`: classification, version checks, reconcile with mapping replay and breaking refusal, rebuild with passing, failing, missing and skipped gates, and a refused target.
- `tests/unit/test_pdlc_end_to_end.py` adds the following on memory, Spanner (emulator) and Neo4j: reconcile; `GET /v1/ontology`; extraction from an `observation.input` event, which yields a proposed Decision linked to a component found by its words; and a gated rebuild of the same ledger into a fresh graph.

Still open:
- **Embeddings:** the extraction prompt offers known items by word match. A vector match over `embed_fields` needs embeddings for pack types (also needed by `similarity` questions).
- **Edge provenance:** a proposed link records its trust and method, but not which event proposed it.

#### Phase 3 review round

An independent reviewer reported 24 findings on commit `b223c58`, with reproduction scripts for the main ones. What was done with each:

| # | Finding | Severity | Outcome |
|---|---|---|---|
| 1 | A proposed link overwrote an existing one: a tool-declared `confirmed` link, or a person's `rejected` one, became `proposed` and `untrusted` | blocking | Fixed: `EdgeWrite.create_only` (a new field with a default) sets properties only when the edge is created. Neo4j uses `ON CREATE SET`; memory and Spanner skip edges that exist. Extraction writes links create-only. Conformance cases on all three backends |
| 2 | A mapping replay of only the changed event types applied their transitions over states set later (a resolved incident went back to `detected`) | blocking | Fixed: a mapping change replays every event type with pack rules, in log order, so later transitions apply again after earlier ones. Concurrent replays from replicas starting together are idempotent, but they can interleave with live events. **Operating rule:** roll out a mapping change with one projection replica first |
| 3 | A recorded state that no longer parses crashed the worker, and `ALLOW_BREAKING` could not get past it | blocking | Fixed: an unparsable state is classified `breaking` ("no longer loads"), refused, and can be overridden. `status` and `GET /v1/ontology` report it |
| 4 | The blue/green switch could lose the events written between the rebuild and the switch; the derived consumer groups never ran on green | blocking | Fixed by procedure, documented in the CLI and `rebuild.py`: deploy green with new consumer group names. New groups read the ledger from the start on every backend (checked in each subscription adapter). The projection group replays onto the rebuilt graph idempotently and then follows live events, and the derived groups build their part of green |
| 5 | A changed key expression, or a removed rule, was classified `mapping`, so a replay left duplicates | should-fix | Fixed: rules are compared by identity (the types, keys and endpoints they write). A lost identity is `breaking`; changed values, conditions or target states are `mapping` |
| 6 | Widening an enum, or widening endpoints to a pack wildcard, was `breaking` | should-fix | Fixed: enum subsets are additive, and endpoints are compared as the types they allow |
| 7 | With `ALLOW_BREAKING`, mapping changes were not replayed | should-fix | Fixed: any plan with changed rules replays, whatever its kind |
| 8 | Version problems were only logged; the docstring's patch exception was not implemented; pre-1.0 rules were too strict | should-fix | Fixed: `reconcile` refuses version problems unless `CG_ONTOLOGY_ALLOW_VERSION_PROBLEMS`. Before 1.0, breaking changes need a minor bump and everything else a patch. The patch exception was removed from the docstring |
| 9 | Decision 10 was not enforced on live graphs | should-fix | Partly fixed: `reconcile` records the packs whose retrieval changed as `eval_pending`, shown by `status` and `GET /v1/ontology`. `ontology evaluate --record` runs their sets on the live graph and clears it. Retrieval does not yet withhold pending weights; that is left to the operator |
| 10 | A rebuild whose gate failed was recorded, and nothing read the result | should-fix | Fixed: the projection worker refuses to start on a graph whose rebuild gate failed (overridable) |
| 11 | Weak rebuild target checks: a non-empty target without state was accepted; a misspelled `--target` key rebuilt into the live graph; the live graph itself was accepted | should-fix | Fixed: a `--target` key must name a setting. The CLI refuses a target that selects the configured graph. `rebuild` refuses a live projection (one a worker reconciled), and a graph that holds data but records no ontology, unless `--force`. Not fixed: the first start on a pre-phase-3 graph cannot know what it was built with, so it records `initial` |
| 12 | One failing event aborted a replay or a rebuild; expired documents went unreported | should-fix | Fixed: replay isolates and reports each failure. Rebuild retries a failed batch one event at a time, reports failing events (and then fails), and counts `missing_documents` |
| 13 | Eval-set errors came only after the full build | should-fix | Fixed: the sets are loaded and checked before the build; a missing or invalid set refuses the rebuild |
| 14 | Known-item lookup scans whole labels on each source event | should-fix | Not changed: it uses `search_nodes`, which, as phase 2 recorded, scans the label on memory and Spanner, bounded by `extraction_known_limit` results. An indexed (full-text or vector) path for pack types is the open item already listed |
| 15 | Proposals from a trusted source are marked `trusted` | design question | Kept, and documented: `source_trust` says who supplied the text, not how sure the inference is. An extracted node is `status: proposed` with `method: extracted` and a capped `confidence`. Extracted links are `proposed`, and those never corroborate (phase 2) |
| 16 | Extracted values were unbounded and loosely typed; self-loops and repeated refs were accepted | should-fix | Fixed: values are at most `CG_ONTOLOGY_EXTRACTION_MAX_VALUE_CHARS` (4000), objects and lists are refused where the type is scalar, self-links are refused, and a repeated ref is refused |
| 17 | Rolling back to an older image is refused as breaking | should-fix | Documented: a rollback is run with `CG_ONTOLOGY_ALLOW_BREAKING=true` (and, for a mapping, it replays) |
| 18 | Replicas starting together could create two `OntologyState` nodes on Neo4j | should-fix, unverified | Fixed: Neo4j gets an `ontologystate_pk` uniqueness constraint. It is generated only; the frozen `constraints.cypher` is unchanged |
| 19 | The extraction hash field came from `text_fields[0]`, not from the pack's rule; `sha256` truncates at 100k; `updated_at` format differed | nit | Fixed: the hashed property is read from the rule that keys the type by `sha256($.f)` and sets a property from `$.f`. Values are bounded below the truncation length. Times use projection's canonical form |
| 20 | Types with `id_property`, or a content key with no text field, would be built wrongly | nit | Fixed: such proposable types are left out of the profile (`skipped`) |
| 21 | Known-item labels were outside the data fence | nit | Fixed: known items are fenced like the text, and the prompt says fenced content is data |
| 22 | Small inefficiencies | nit | Partly fixed: link targets are computed once, and `GET /v1/ontology` reads the state once. `LedgerReplay` still lets the consumer fetch documents again |
| 23 | Magic numbers | nit | Fixed: the label length is a setting. The ref and word patterns are format constants, commented |
| 24 | Tests that could pass vacuously | — | Fixed: the end-to-end test rebuilds into a fresh Spanner database on the Spanner run (memory otherwise; Neo4j Community has one database) and compares the rebuilt graph with the live one (`migration.compare_graphs`). Its eval set has only non-empty answers. It shows the live graph is refused as a target. New regression cases cover findings 1–3, 5–8, 10–13 and 16 |

Regression cases:
- `tests/unit/test_pack_versioning.py::TestReviewFindings`;
- `tests/unit/test_pack_extraction.py::TestReviewFindings`;
- `tests/unit/test_ontology_cli.py`;
- `tests/conformance/test_pack_graph.py::TestCreateOnlyEdges`.

#### PDLC evaluation set for the fixtures (2026-10-05)

`tests/fixtures/ontology/pdlc.eval.yaml` holds 11 questions about the graph the webhook fixtures build: the deliveries `test_pdlc_end_to_end.py` sends.
- **Coverage:** 5 trace questions, 5 completeness questions and 1 preflight question.
- **Expected answers:** what is true of that data, not what retrieval returns today.
- **Where it runs:** the end-to-end test runs it as the rebuild gate on memory, Spanner (emulator) and Neo4j. Each question's F1 is pinned, so any change in an answer fails the test.
- **Not built in:** the questions are about fixture data, so they would be wrong for a real deployment, whose gate falls back to the built-in pack dir. A deployment still writes its own set.

At PDLC 1.3.0 the set scores a mean F1 of 0.85. An earlier version of this note said 0.76, which was an arithmetic error; the test then pinned each question's score but not the mean, and it now pins both. Three questions miss:
- **"Where is PAY-341 deployed?" (0.0):** a GitHub `deployment_status` names a commit, not PRs, so `change_numbers` is empty and `DEPLOYS` is never drawn. Linking a deployment to the change whose `merge_sha` it deployed needs a `match` lookup in the `service.deployed` rule. This is the pack's own example question for `trace`.
- **"What changes implemented PAY-341?" (0.67):** the trace also returns #8, reached through the release that includes both.
- **"What does PR #7 implement?" (0.67):** the trace also returns the parent epic PAY-300.

Writing the set found a trap: in YAML, ` #` starts a comment, so `query: What does PR #7 implement?` loaded as "What does PR". The loader now refuses an unquoted query containing ` #`, naming the line (`tests/unit/test_pack_versioning.py::TestEvalSetFiles`).

#### PDLC 1.4.0: deployments link the change they deployed (2026-10-05)

`pdlc.service.deployed` gains a `DEPLOYS` edge to each change in the same repo whose `merge_sha` equals the deployed commit. It is a `match` lookup, guarded by `when: $.artifact_id`.
- **Why:** a GitHub `deployment_status` names a commit, not PRs, so the existing `change_numbers` edge never formed. This fixes the eval set's `deployed-where` question (0.0 → 1.0), and the set's mean goes from 0.85 to 0.94. `min_f1` is now 0.9, and the end-to-end test pins the mean as well as each question.
- **Limit:** only changes already merged when the deployment is projected are linked. A merge event that arrives after its deployment is not linked until a replay.
- **Classification:** adding an edge to an existing rule was classified `breaking`, because a rule's parts were compared as one identity. That would have made every worker refuse to start on 1.4.0. Each part (upsert, transition, edge) is now compared on its own. A lost part is breaking; an added part is `mapping`. 1.3.0 → 1.4.0 is therefore `mapping`, so a live graph replays its pack events on upgrade, which links past deployments.
- **Tests:** `test_pack_projection.py::test_a_deployed_commit_links_its_merged_change` (before and after the merge, another repo with the same sha, an unknown sha) and `test_pack_versioning.py::test_adding_an_edge_to_a_rule_is_mapping_and_removing_one_is_breaking`.

#### Traversal drift rules (2026-10-05)

The two remaining misses in the fixture eval set were traversal drift, not missing links. Artifact traversal (`retrieval/artifacts.py::_drifts`) no longer takes these two steps:
- **Siblings:** leaving a reached node through the edge type it was entered by, in the same role. "What changes implemented PAY-341?" went PR #7 → release v1.4.0 → PR #8 through `INCLUDES` twice; sharing a release says nothing about the ticket.
- **Family of a reached node:** a step to a node of the same type, unless from a seed or continuing a chain of such steps. "What does PR #7 implement?" went PR #7 → PAY-341 → its epic PAY-300.
- **What is kept:** transitive chains (Requirement `REFINES` Spec `REFINES` Request: different roles), and families of seeds ("Trace PAY-300" still reaches its stories).

The fixture set now scores 1.00 (`min_f1` 0.95), and the Phase 2 evaluation is unchanged. Tests: `tests/unit/test_pdlc_retrieval_eval.py::TestTraversalDrift`, and the pinned scores in `test_pdlc_end_to_end.py` on memory, Spanner and Neo4j.
