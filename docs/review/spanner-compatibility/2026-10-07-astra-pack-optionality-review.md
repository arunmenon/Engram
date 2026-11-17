# Pack optionality: grounded platform review

Date: 2026-10-07. Astra review requested at medium effort. Scope: current working tree, including uncommitted pack-contract/Spanner changes. Read-only runtime review; only this report and adjacent local probe artifacts were written. No external services, credentials, cloud calls, or GitHub mutations.

## Decision

**Approve required core + optional memory/user + selectable compatible domain packs as the target. Do not describe it as integrated support today.** The four packs are complementary, with conditional dependencies; they are not mutually exclusive product alternatives. Memory, user and PDLC each declare core as their dependency. PDLC has no declared memory/user dependency, and direct schema composition confirms core+PDLC is valid.

“Domain-only” can mean **core+PDLC, with memory/user features disabled**. It cannot mean zero shared infrastructure: event ingestion/ledger, Event provenance, shared Entity references/interfaces/edges, projection, graph access, retrieval and processing state remain necessary. Current core is substantial: Event, Entity, Summary, agent/tool event vocabulary and retrieval intents, plus shared interfaces. A separate minimal kernel is a possible future product choice, **not required for the smallest coherent implementation**.

Configuration today adds domains to an inseparable core+memory+user base. Schema selection alone would leave specialized writers, reads and maintenance active. Preserve specialized built-in code and put explicit capability gates around its construction and output boundaries; do not rewrite it into declarative YAML simply to claim uniformity.

## Configuration and evidence matrix

| Requested configuration | Direct schema-only result | Supported loader/runtime selection today | Target condition |
|---|---|---|---|
| Default settings | All four, 28 node types | All four loaded | Preserve default or deliberately migrate it |
| Empty domain list | Core+memory+user, 11 types via loader | Valid; does not disable built-ins | Explicitly document empty-domain semantics |
| Core alone | Composes, 3 types | Loader also adds memory/user | Core services with gated optional writers/reads |
| Core+PDLC only | Composes, 20 types | Loader produces all four | Valid target after coherent gating |
| Core+memory | Composes, 6 types | Loader adds user | Identify actual memory producers; schema is not behavior |
| Core+user | Composes, 8 types | Loader adds memory | Preserve user extraction without requiring memory |
| All built-ins + domain | Composes, 28 types for PDLC | Current deployment pattern | Supported capabilities and conformance still required |
| PDLC, memory or user without core | Rejected | Loader resolves core automatically | Core remains required |
| Missing pack / core>=99 dependency | Rejected locally | Missing file/version validation works | Retain fail-closed checks |
| Two tenants with different selections | Two configuration objects can be constructed | No tenant-aware dispatch/storage/auth support established | Separate isolated deployments first, or explicit multitenancy project |

The direct constructor bypasses the production loader. Its success is schema evidence only. All runtime claims above describe inspected wiring, not new execution/cloud acceptance.

## Prioritized findings

**PO-01 — P0: pack selection is not a feature execution boundary.** `ontology/loader.py:32,203` always prepends core/memory/user; `settings.py:570` explicitly defines additive configuration. Only projection and pack extraction obtain a configured projector in `worker/__main__.py:87,118`; extraction, enrichment and consolidation are constructed independently of optional-pack capability decisions. `worker/extraction.py:232` writes profiles/preferences/skills/interests through UserStore and combines these with core entity resolution. Simply omitting user schema cannot prevent those writes, particularly in generic Spanner storage. Gate user output and API/read availability while preserving core entity extraction if selected. Reject an incompatible worker configuration before opening stores.

A significant nuance: consolidation groups events into Python “episodes” but writes **core Summary/SUMMARIZES**, not memory Episode nodes (`worker/consolidation.py:220,246,270`). Searching current source finds memory merge_belief/goal/episode affordances in adapters, not worker callers. Do not equate the memory schema with a fully implemented memory producer, and do not turn off core summaries/retention merely because memory is disabled.

**PO-02 — P0 for multitenancy: a registry is not a tenant boundary.** API startup installs one ontology and retrieval composition (`api/app.py:98,118,139`); runtime cache keys only configuration (`ontology/runtime.py:20`). Authentication checks shared API/admin keys and returns no tenant context (`api/dependencies.py:98,119`). Spanner keys are event_id, (label,node_id), edge endpoints and consumer group names, with no tenant dimension (`adapters/spanner/schema.py:43,79,103`). NodeRef has no tenant (`ports/pack_graph.py:31`); ontology state is one `OntologyState:active` (`ontology/versioning.py:47`). Session IDs and user IDs derived from agent IDs also do not establish isolation (`worker/extraction.py:235`). Two processes pointed at the same stores with different pack lists are not isolated tenants. Use separate complete store/resource sets for deployment-level selection. Shared-process multitenancy needs authenticated routing and scoped ledger, graph, deliveries, caches, search, admin, retention, replay and ontology/evaluation state—not a request header plus registry lookup.

**PO-03 — P1: disabled domains can still enter as open events.** `domain/ontology.py:656,676` closes namespaces only for loaded domain packs; the local probe confirms `pdlc.unknown` is accepted with PDLC unloaded and rejected with PDLC loaded. Unknown domains remain accepted. Establish an explicit distinction between generic/ledger-only event admission and activated domain interpretation. An unloaded domain must not silently appear to be accepted for domain processing. Source trust also remains tied to event.agent_id in `domain/pack_projection.py:301`; tenant selection cannot inherit that as authenticated ownership. Reuse #4/#5/#35 rather than inventing a second ingress mechanism.

**PO-04 — P1: schema extensibility and operational extensibility differ.** Spanner’s JSON graph tables need no per-pack DDL, and `adapters/graph_ops.py:593` has a no-op ensure_pack_schema. This is storage flexibility, not registry enforcement. Fixed label/key maps and edge endpoint fallbacks remain (`graph_ops.py:68–140`), including UserProfile keyed by profile_id while its YAML declares user_id (`ontology/packs/user.pack.yaml:5,19`). Statistics and orphan cleanup use fixed label lists (`graph_ops.py:845,954`), so domain coverage is incomplete. Event retention deletes Events based on age/importance/access (`graph_ops.py:930`), while PDLC depends on Event provenance. Optionality acceptance must verify evidence survives the selected maintenance policy and distinguish supported domain lifecycle behavior from declarations. `domain/ontology.py:713` explicitly reports inert embedding, decay and other declarations. Do not promise domain embeddings or decay merely because YAML loads or a generic vector index exists.

**PO-05 — P1: there are two deliberately different retrieval contracts.** Event retrieval consumes registry intents but keeps specialized event/seed algorithms (`retrieval/engine.py:112`; `adapters/graph_ops.py:1430` user_profile seed strategy). Artifact retrieval selects non-OPEN_PACKS seed types and edges and applies domain admission/plugins (`retrieval/artifacts.py:229,376,733`). `domain/pack_intents.py:52,57` partitions intents using the fixed core/memory/user category. Removing a pack must consistently remove its query/API capability and prevent historical disabled data appearing through traversals. Selecting a domain does not make every built-in endpoint a generic domain query. Keep both engines; define and test the supported cross-pack joins and read filters.

**PO-06 — P1: activation changes need data/interpretation policy.** Reconcile records one composed ontology and canonical pack snapshots (`ontology/versioning.py:93,117`), with existing breaking-change/replay mechanisms. That is useful foundation, not a complete disable/re-enable contract. Decide whether disabling stops new interpretation only, hides existing artifacts, retains their evidence, or triggers deletion; whether re-enable catches up; and which historical version interprets missed events. Check dependent/subscribing packs and source/property ownership before activation changes. Avoid treating allow_breaking as a disable protocol. Existing #35/#36 and historical #11/#12/#13 own most of this work.

## Smallest coherent implementation boundary

1. Introduce an explicit deployment selection distinguishing required core, selected optional built-ins and domains; preserve existing additive environment semantics through a deliberate compatibility default. Resolve dependencies once into an immutable active bundle and executable capability set shared by API and workers.
2. Add a small capability-to-worker/output mapping. Keep projection’s core Event stage and domain projector, retain specialized user extraction with a user gate, retain Event enrichment and core summaries/retention under their actual capabilities, and activate declared pack extraction only with a supported profile. Do not claim unused memory adapter methods constitute implemented behavior. Fail startup for required unavailable capabilities.
3. Use that same selection at ingress, API/query exposure and graph write/read boundaries. Make disabled-domain admission deliberate, enforce source/subscriber permissions, and scope operational statistics/maintenance to supported selected types without inventing generic lifecycle algorithms.
4. Start with one bundle per isolated deployment/store set. If same-process tenant variation is a real requirement, design it explicitly before marketing tenant isolation. Pin accepted events and processing obligations to interpretation identity; specify historical-data and activation transitions using existing versioning/replay mechanisms.

## Decisive acceptance tests

- Run the matrix through real composition roots with in-memory recording ports first: assert enabled worker outputs, absent optional labels/edges and intended API/read behavior, not merely node-type counts. In core+PDLC, a session-end event must not write user data; core projection/provenance and PDLC projection/retrieval still work.
- Preserve user extraction in core+user; show the exact implemented memory behavior in core+memory. Test core summary/retention separately from memory Episode schema.
- Assert unloaded domain, unknown namespace, missing dependency/version, unsupported required capability, external subscriber and stale API/worker bundle outcomes before append/processing.
- Seed historical disabled-pack data and cross-pack edges: test both retrieval paths, stats, retention, re-enable/catch-up and dependency removal. Assert exact IDs, evidence and no unintended writes/deletes.
- If multitenancy is selected, collide event/session/agent/domain IDs across tenants and verify API, graph/search, consumers, replay/admin, evaluation state and cleanup isolation. Configuration-object independence is insufficient.
- Reuse #39 conformance and #40 full PDLC journeys for exact artifacts/evidence, then #41 for real Engram→Spanner signoff. Local tests cannot establish cloud transaction/index/auth/operational behavior.

## Tickets and product choices

Keep #34 as umbrella; extend #35 with dependency resolution, active bundle/capability agreement and optional built-in activation. Keep update/subscriber ownership in #36, reusable matrix in #39, complete PDLC behavior in #40 and cloud proof in #41. Existing source trust, ingress, retention and replay issues retain their boundaries.

Only two narrowly new tickets are justified if not already represented: **“Make built-in memory/user capabilities optional across composition, reads and maintenance”** (the concrete execution work under #34/#35), and **“Define deployment isolation versus authenticated tenant-specific pack activation”** (decision/design, implementation only if shared-process multitenancy is chosen). Do not create another generic pack engine umbrella or duplicate conformance ticket.

Product decisions needed: default selection/migration; whether domain-only includes core event summaries/enrichment; disabled-data visibility and catch-up; source/subscriber ownership; and separate deployments versus true multitenancy. A core-kernel split can wait unless an actual deployment requires removing current core vocabulary/behavior.

## Local verification and limitations

Adjacent `2026-10-07-astra-pack-optionality-local-probe.py` and `.json` contain bounded configuration/schema probes, executed with `/private/tmp/engram-ontology-review-venv/bin/python`, `PYTHONPATH=src`. The probe covers default/empty/subset/all selections, missing dependencies, invalid version and two configuration objects. One development attempt tried mutating a frozen PackHeader and failed locally; the final probe uses immutable model copies and completed successfully. No worker, API, storage or cloud journey was executed, and no broad test suite was needed for this architectural verdict. Master-plan/context claims were treated as scope/history, not fresh proof. This review does not sign off Spanner compatibility or optional-pack runtime support.
