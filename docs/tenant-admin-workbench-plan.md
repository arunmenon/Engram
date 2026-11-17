# Tenant administration and ontology workbench

Status: proposal for review, 2026-10-30. No UI or admin-control API implementation is implied. Audience: internal operators managing multiple tenants. Packs authored here are private to one tenant. This plan carries forward the agreed shared Engram API, separate tenant databases, agent-assisted authoring, synthetic-data preview, and explicit activation.

## 1. Outcome and scope

An operator should be able to create a tenant draft, supply domain evidence, author or select packs, understand the resulting model, run representative events and questions in an isolated environment, review the evidence, and activate an approved version through a controlled runtime change.

Use PDLC for the operator-facing domain walkthrough, and a small contract-complete CRM fixture for the first executable authoring/sandbox slice. Adapt and verify that fixture before relying on it; full PDLC acceptance follows in phase 5. The workbench itself must support any compatible pack, without hardcoded PDLC node names. Do not promise arbitrary ontology imports, automatic source connector generation, hot reload, independent per-tenant process restart, or migration of existing historical data in the first release. Record unsupported requirements and route them to engineering.

An agent may propose and edit configuration and tests. It cannot grant itself access, change a tenant's active configuration, or modify Engram's interpreter as a side effect of authoring a pack.

## 2. Existing foundations and current limits

- `src/context_graph/tenancy.py`: immutable bindings, authenticated principals, credential grants and catalog checks. A binding pins settings, engine revision and pack contents; separate database resources are required.
- `src/context_graph/api/tenants.py`: public factory now creates a dispatcher with checked child lifespans. Catalog changes require restart. Startup failure and shutdown currently affect the entire dispatcher; do not display independent per-tenant restart as implemented.
- `ontology/loader.py`, `domain/ontology.py`, `domain/pack_bundle.py`, `domain/pack_admission.py`: pack parsing, composition, capability resolution and admission policy. Reuse these on the backend rather than duplicating their rules in the browser.
- `domain/pack_projection.py`, projection workers and graph ports: deterministic mapping execution. `ontology/evaluation.py` and artifact retrieval support question/expected-node evaluation.
- Existing runtime surfaces include event ingestion, ontology inspection and artifact queries. Draft management, authoring jobs, scenario execution, schema graph exploration and activation administration need new interfaces.
- Two real databases have been exercised through the public factory using in-process HTTP. This covers bounded routing, read separation and colliding event IDs, not deployed networking, full worker journeys or activation races. The full current unit run reported 2,508 passing, 26 failing and 15 skipped tests; PDLC expectation mismatches remain unresolved.
- `demo/frontend` contains React/Vite, Sigma/Graphology and graph interactions. Reuse selected components after extracting generic node/edge handling. Its fixed type lists, global stores and request logging are not production tenant boundaries and must not be copied unchanged.

Additional implementation anchors: `src/context_graph/domain/pack_versioning.py` owns change classification and version checks; `src/context_graph/ontology/evaluation.py` owns evaluation scoring; `docs/runbooks/pack-authoring.md` describes the recorded retrieval gate. These rules are backend contracts, not independently implemented UI heuristics. Prior test results are historical evidence, not a fresh passing baseline for this revised plan.

## 3. What the operator supplies

The first screen is a structured intake, with a conversation alongside it. Documents are evidence, not executable instructions. Uploaded content cannot override the agent's tool permissions or tenant scope.

| Input | Examples | Used for | Required before |
|---|---|---|---|
| Domain purpose and scope | Product delivery traceability; include requirements through deployments, exclude billing | Bound the model and avoid unrelated concepts | First draft |
| Source specifications | PRD, architecture notes, process definitions, glossary, data dictionary | Propose concepts, relationships and vocabulary | Grounded review; prose may begin with gaps |
| Source interface definitions | OpenAPI/JSON schema, webhook docs, normalized event contracts | Establish available fields and their types | Executable mappings |
| Representative records/events | Redacted create/update/close events, nested lists, missing fields | Ground mapping paths, identity and update behavior | Sandbox-ready draft |
| Identity and ownership rules | PR number unique per repository; requirement ID unique per spec revision | Select stable keys and authoritative writers | Approval |
| Lifecycle and change rules | Allowed states; reopen semantics; deletion, supersession, missing versus null | Define transitions and avoid accidental overwrites | Approval |
| Questions and expected outcomes | Which changes implement this requirement? Which requirements lack tests? | Retrieval intents and evaluation oracles | Evaluation |
| Trust/source policy | Named authenticated producer IDs and which may be trusted | Source grants and admission | Runtime readiness |
| Operational constraints | Data sensitivity, retention, expected volume, extraction permission | Sandbox/provider configuration and cost bounds | Running relevant jobs |

Minimum to begin: tenant, scope, and a specification or domain explanation. The UI allows a conceptual draft with incomplete inputs but labels it as such. Minimum to run: explicit input contracts, representative normalized events, resolved key decisions and supported mappings. Minimum to approve: reviewed expected results and all consequential assumptions resolved or explicitly documented as limitations consistent with acceptance.

Do not require operators to know YAML. Use questions such as: “Can ticket 42 exist in two trackers?” and “When title is absent, should the old title remain?” Explain the effect of each choice with an example.

### Concrete intake sequence (implementation contract)

The internal operator drives the workspace on behalf of the tenant. Intake is progressive, not a requirement to fill every field before seeing a model:

1. Create the tenant/environment draft and select roots/dependencies. No runtime resource is created.
2. Review data handling and redaction **before the first model call**; record scope and exclusions. Local-only intake must never call a provider.
3. Add a process document/glossary, interface schema or sample events in any order. A domain explanation plus schemas/samples can replace a formal specification. The evidence inventory identifies the source of each proposal.
4. Request a conceptual proposal when enough domain context exists. Show cited facts and inferences. Missing interfaces keep executable mappings unavailable.
5. Add representative events and schemas. Show field presence/distinct/repeated counts without claiming global uniqueness. Propose contracts and mappings; identify concepts with no actual source instead of inventing a writer.
6. Resolve identity, field omission/null, lifecycle, ownership and answer-semantics decisions with concrete effect examples. Changing evidence or decisions invalidates old review/run evidence; regenerate the proposal against the updated context.
7. Review questions, expected node IDs and graph expectations, and record producer/trust policy. Live credential grants are separate from sandbox trust simulation; sandbox trust-dependent answers must still use an explicit reviewed policy.
8. Review individual proposals and the executable pack, validate with the real engine, run the isolated scenario, inspect observed results and approve the exact artifact for operational handoff.

Keep the three readiness checklists visible throughout. A schema graph, planned delta, observed graph, approved artifact and live activation are distinct outcomes. Never use a fixture author or a local reference-backend run as evidence of live model quality or deployed isolation.

## 4. Grounding, assumptions and conflicts

Store every uploaded source with tenant ownership, version/content hash, filename and section/page or record pointer. The agent's proposed type, property, key or rule carries a source reference or an explicit label: operator decision, inferred proposal, or unresolved assumption. These references live in authoring metadata alongside the valid pack; do not invent unsupported YAML fields.

Example: a PRD mentions Requirements and DesignElements, while webhook examples contain repo and number. The agent can propose the two domain concepts from the PRD, but must obtain a stable requirement key and a source event that links it to a Change. It must not fabricate that linkage because a sentence says the team “tracks requirements.”

When sources disagree, show the conflicting excerpts and ask the operator to choose the applicable version or rule. Do not assume the newest file is authoritative. Changed sources mark affected proposals and tests for review. Parser failure, unreadable pages or incomplete extraction remain visible.

Support pasted text, Markdown/plain text and JSON events/schemas first. Add PDF/DOCX extraction with section/page citations as a subsequent intake increment; do not claim scanned-document understanding without an explicit supported OCR path. Connected-source imports follow later. Require review of sensitive material before it is sent to the chosen model provider; keep credentials out of inputs and model prompts.

## 5. Screens and operator journey

### Tenant list

Name, environment, operational status, active configuration version, pack summary, latest readiness issue and last change. Search/filter by status and pack. Actions: create draft tenant, inspect tenant, resume draft. No bulk activation in the first release.

Separate the logical tenant record from its environment deployment: each deployment owns its binding, database target, active bundle and readiness. Drafts, jobs and approvals identify both tenant and deployment explicitly. Environment is not just a label that redirects the same credential. Initially expose one configured deployment per tenant; do not imply automatic development-to-production promotion.

### Tenant detail

Always-visible tenant name and environment; active versus draft configuration is unmistakable.

- Overview: active binding, service readiness, worker health, last verified check and timestamp. Unknown/stale status is distinct from healthy.
- Packs: exact versions/digests, dependencies, enabled handling, evaluation status and unsupported declarations. Separate runtime readiness from intent-serving readiness.
- Sources/access: authenticated producer grants and trust policy, separately explained. Secret values are never displayed; secret references are shown.
- Draft changes: side-by-side semantic diff, author, grounding inputs, unresolved questions, relevant test run and approval.
- Activation: reviewed configuration, affected service scope, preflight results, drain progress, activation/recovery status.
- History: who created, edited, tested, approved and activated each exact version, including failures.
- Processing health: rejected ingestion, unsupported event types, worker failures and dead letters, with redacted error detail, timestamps and run/event links. Show missing telemetry as unavailable; new scoped read APIs are required. Reprocessing is a separate controlled action, not a default button.

Pack selection chooses from the engine's built-in catalog and approved versions private to this tenant. Show mandatory core, explicitly selected optional memory/user roots, selected domain packs, and the resolved `requires` dependency tree. Pin the complete bundle. Validate global type, edge, event, intent and interface names across the composed registry, dependency versions, handlers and forbidden built-in shadowing. A pack that validates alone may still fail composition; approval covers the whole bundle.

### Pack workbench

Header: tenant, deployment, draft revision, base active version and pinned engine target. Inputs and Review bookend five authoring concerns: **Types and lifecycle**, **Event contracts**, **Mappings**, **Intents and questions**, and **Evaluation**. Scenario execution lives in Evaluation, so there is one obvious home for test evidence. A collapsible agent panel remains available; forms work without chat.

- **Inputs:** versioned specifications and samples, citations and a decision queue. Each decision shows conflicting evidence and the effect of each choice. Each agent proposal is accepted or rejected separately; acceptance creates a new draft revision.
- **Types and lifecycle:** schema graph plus tables for properties, keys, interfaces and edges. Candidate keys show sample counts, distinct values, missing values and collisions, including composite-key alternatives. Sample uniqueness is evidence, not proof of global uniqueness. Show states and `only_from` guards as a state machine; explain that `superseded_states` affects retrieval visibility rather than deleting nodes.
- **Event contracts:** one row per declared event, representative payloads, required/optional fields, types and explicit handling: processed, ledger_only or unsupported. Infer a proposed contract from examples, then reconcile it against source specifications and operator decisions. Samples cannot prove optionality. Processed events require a compatible handler; an unmapped event is not silently ledger-only. Surface undeclared events and missing contracts before ingestion.
- **Mappings:** select an event and payload field, insert a supported expression, and inspect the planned delta. Provide the engine's value-language function palette with sample evaluation. Distinguish payload-relative paths from event-envelope references. Validate regex syntax and show measured sample execution against the engine's 0.25-second per-match limit; fast samples do not establish worst-case safety. Timeouts are failures, with dead-letter behavior explained. Coverage tables show events with handlers, explicit ledger-only/unsupported events, node types without known writers and edges never produced by the selected scenarios. Distinguish static absence of a writer from absence in sample execution; search/filter all views.
- **Intents and questions:** edit seed types, key patterns, intent examples/keywords, weights, depth, supported plugins such as `missing_links`, and admission rules. Link each evaluated question to its intent, expected node IDs, optional answer filters and threshold. Intent-classification examples are distinct from scored evaluation questions; do not mistake examples for an oracle. Explain trust-related exclusions and superseded-node filtering.
- **Evaluation:** run event sequences, inspect the observed graph, and compare expected/retrieved IDs, false positives/negatives, per-question F1 and aggregate threshold. Show traversal paths, weights and inclusion/exclusion reasons where runtime evidence exists; otherwise label unavailable and track instrumentation work. Weight edits invalidate relevant results and require a rerun. Include guards rejecting transitions and duplicate/malformed inputs.
- **Review:** a checklist of conceptual readiness, executable readiness and approval readiness from section 3. Show citations, unresolved assumptions, bundle composition, event/graph coverage, semantic diff, backend change class, required version bump, operational procedure and both sandbox and target-evaluation status. An approved draft is not yet an active, query-ready deployment.

Use a parsed pack as the canonical configuration model, with sidecar authoring metadata and one revision covering pack plus evaluation artifacts. Forms are views over that model; YAML is a generated, read-only preview/download in the first release. Preserve valid inherited fields and show unsupported-to-edit sections read-only. Two-way YAML editing is deferred until lossless round-trip behavior and revision conflicts are tested.

Inline diagnostics include a transition without an upsert (missing event provenance), a lifecycle without `Lifecycled`, and trust admission with no trusted producers (most unnamed nodes disappear from answers). Use actual loader validation severity; do not downgrade a rejected pack to a warning. Show loaded-but-inert fields, including relevant embedding/decay settings, with a visible capability badge based on the pinned engine. The agent cannot advertise these as working. New extraction-rule authoring is outside the first release; retain existing extraction sections read-only and expose any provider/handler requirements that affect execution.

Every graph has keyboard-accessible node/edge tables, search, clear labels and non-color status indicators. On small displays, panels stack or switch tabs. Large graphs are bounded and disclose truncation; users can narrow the view instead of rendering every node at once.

### First complete journey

Create tenant draft → attach specifications/examples → resolve identity questions → generate pack → inspect schema → review sample scenarios → run sandbox → inspect graph and query results → approve exact revision → activate through supported operational procedure → verify runtime and target-graph evaluation status before declaring the deployment ready.

## 6. Agent workflow and boundaries

1. Extract source facts and build a grounding inventory; record unread or unsupported inputs.
2. Propose a compact domain model and ask only decisions that affect identity, ownership, lifecycle, trust or answer semantics.
3. Generate the pack and companion scenario/evaluation artifacts in an isolated tenant/draft workspace. Proposals are individually reviewable diffs with citations; accepted changes remain subject to whole-bundle validation.
4. Run the actual engine's parser, composition and admission checks against the selected engine revision.
5. Propose positive, negative and sequence tests; the operator reviews their expected results.
6. Execute authorized sandbox runs, inspect failures and propose bounded revisions. Each revision invalidates relevant prior checks/approval.
7. Produce a review package: pack, grounding references, decisions, semantic diff and observed results.

Jobs have status, cancellation, limits on runtime/tool calls/model spend and a resumable record. Permit only workspace reads/writes and approved validator/test tools. No live database credentials, shell access to deployed runtimes, package installation or engine-code edits in the authoring job. Unsupported DSL/capability requests become engineering tasks. Operator approval governs live activation, even if the operator also authored the draft; separate reviewer roles can follow later.

## 7. Sandbox and graph preview

Distinguish three views:

- Schema graph: allowed types and relationships; no claim of executed behavior.
- Planned delta: deterministic projector output for a chosen event; no claim of committed writes or resolved database lookups.
- Observed graph: nodes/edges actually stored after processing, with available event provenance and processing outcomes.

The end-to-end runner uses real ingest → ledger → required workers → graph → retrieval in an isolated database using the pinned engine and bundle. LLM-derived artifacts are marked as proposals and the provider/model is recorded. A fast local planner preview is useful but cannot substitute for backend acceptance. Reuse existing journey machinery and exact-result assertions.

Scenario coverage includes creation, repeated identity, duplicate/conflicting event IDs, lifecycle transitions, missing/null fields, list expansion, invalid contracts, unavailable handlers, and trust-related admission. Include deliberately irrelevant data to test excluded query results. Expected graph deltas and forbidden effects are reviewed before execution, not silently regenerated after a failure.

The operator can step through event N and inspect input, handling status, planned/observed changes and evidence. Existing DERIVED_FROM edges support node provenance; do not claim exact event/rule attribution for every relationship or rejected transition without implemented instrumentation. Display unavailable attribution as unknown.

Jobs use unique run IDs and persist evidence before cleanup. Only run-owned fixtures may be deleted. Reuse a sandbox sequentially only with verified cleanup and explicit owner/configuration transition; never treat a partially cleaned graph as a fresh run. Current Spanner instance has a five-database limit: sandbox capacity must be checked before offering execution, and the console must explain busy/no-capacity states. No database per draft by default.

Synthetic tests demonstrate the chosen examples. Add representative redacted real producer events before declaring source readiness. Passing agent-generated synthetic tests alone is not sufficient evidence of domain correctness.

### One evaluation artifact, two execution contexts

The questions editor and `<pack>.eval.yaml` are two views of one versioned artifact, never independent stores. Approval pins its digest together with the pack, engine, scenario inputs and reviewed expected results. Both sandbox and deployment evaluation consume that artifact. Record the graph identity, data/checkpoint used and execution time separately for each run; a sandbox pass cannot clear the target graph's gate.

Expected node IDs must exist in the relevant dataset. Use stable source identities and an explicitly reviewed target data plan; never copy synthetic fixtures into production implicitly. If production expectations need different IDs or questions, create an explicit reviewed artifact revision and rerun affected checks. Missing target data means evaluation pending, not automatic success. Synthetic empty expectations cannot be used merely to unlock a new tenant. Initial ingestion may be available while retrieval intents remain pending.

## 8. Backend shape and proposed APIs

Use a separate operator-facing UI and a logically separate admin backend. Initially the admin backend can share the repository and deployment tooling with Engram; a separate microservice is not required. Authoring/test jobs run outside request handlers. Runtime API/worker processes consume approved bundles and never accept arbitrary code from the browser.

Proposed admin routes below do not exist yet:

| Operation | Proposed interface | Reuse / new work |
|---|---|---|
| List/create/inspect tenant drafts | `/admin/tenants` | New operator authorization and persistence |
| Read/update configuration draft | `/admin/tenants/{id}/drafts/{revision}` | New; optimistic revision checks |
| Add/read grounding material | `/admin/tenants/{id}/inputs` | New bounded upload/parser/source records |
| Start/poll/cancel authoring | `/admin/tenants/{id}/authoring-jobs` | New isolated job runner |
| Validate and inspect pack | `/admin/tenants/{id}/drafts/{revision}/validate` | Adapter over existing pack machinery |
| Start/poll sandbox scenario | `/admin/tenants/{id}/sandbox-runs` | Orchestrate existing ingest/workers/retrieval |
| Inspect model, graph delta and run evidence | `/admin/tenants/{id}/sandbox-runs/{run}` | New bounded result/exploration endpoints |
| Approve immutable candidate | `/admin/tenants/{id}/approvals` | New revision/digest-bound approval |
| Preflight/request/observe activation | `/admin/tenants/{id}/activations` | New operational workflow; not a cache write |

Existing runtime calls include `POST /v1/events`, batch ingestion, `GET /v1/ontology` and `POST /v1/query/artifacts`. Their runtime authorization still applies; the admin backend must resolve the tenant and appropriate sandbox/runtime credentials server-side. An operator-selected ID is not sufficient authorization. Existing tenant API/admin roles do not provide cross-tenant operator identity by themselves: add explicit operator access scope and audit actions.

Persist tenant drafts, input references, artifact versions, decisions, job/run records and approvals in a durable control store. Store large source artifacts separately behind tenant-scoped access. Record exact engine, pack and scenario digests on every run. Cache validated immutable bundles by content digest; the durable approved configuration remains authoritative. Cache invalidation alone is not activation.

Use one canonical backend validation contract. Browser checks improve editing feedback but cannot replace server-side parsing, permissions or activation checks. Redact provider errors and payloads from shared logs; the demo frontend's global API interceptors and stores require isolation before reuse.

Source retention is configured per tenant: record expiry, authorized viewers and provider handling. Deleting a source removes its content according to policy and leaves only permitted audit metadata; affected citations become unavailable. Do not keep document excerpts indefinitely inside job logs. Cancelled or abandoned drafts can be archived, their jobs stopped and run-owned sandbox data cleaned up. Tenant decommissioning first disables access and drains jobs/workers; data deletion is a distinct explicit operation with retention and ownership checks. No cascading database deletion from a draft-delete action.

## 9. Activation and failure behavior

Keep draft state, test state and runtime state separate. Suggested draft states: draft, validating, needs_decision, sandbox_failed, ready_for_review, approved. Runtime states should reflect observed control/service state, not optimistic UI labels. Activation requests have queued, preflight, draining, starting, runtime_verifying, succeeded or failed stages. Track intent readiness separately per pack: evaluation_pending, evaluating_target, ready, failed or not_applicable. The UI displays both outcomes; activation success alone does not mean intents are ready.

Approval pins the exact artifact/configuration digest and engine revision. Edits invalidate approval. Before activation, verify ownership, schema, composition, change classification/version bump, compatible handlers, required sandbox tests/evaluation, the approved target evaluation artifact and data plan, source grants and worker configuration. Stop on mismatch instead of adopting another owner or reconstructing a bundle from names alone.

The backend classifier compares the complete old and new registries. Display its reasons and version problems rather than inferring class from a textual diff:

| Class | Engine procedure | First admin release |
|---|---|---|
| Initial | Initialize a new graph under the approved bundle | Supported with owned target and readiness checks |
| Additive | Engine can reconcile additive changes without historical replay | Supported on populated tenants through coordinated binding/restart, not a promise of shared-API hot reload |
| Mapping | Replay affected event types; adding rules for existing events can require this | Blocked on populated tenants until a separately delivered replay workflow exists |
| Breaking | Fresh blue/green projection, evaluation and controlled switch | Blocked until rebuild, cutover and recovery are supported |

For stable versions, additive/mapping changes require a minor bump and breaking changes a major bump. Before 1.0, the classifier requires patch and minor respectively. Show no-change/initial explicitly. Adding a pack can require replay of existing ledger events; do not assume it is safe solely because the pack name is new. The classifier alone is not a complete authorization policy: admission-contract, trust and ownership changes also require their own compatibility checks.

Initial deployment uses coordinated drain/quiesce/restart. The current dispatcher lifecycle is shared: the UI must state whether an operation affects all hosted tenants. Do not offer isolated tenant restart until the backend supports it. Existing tenant data and old accepted events cannot simply be reinterpreted under a new bundle. Changes requiring replay/migration need a separately supported procedure; they are blocked rather than hidden behind a Save button.

Once runtime and required workers confirm the new identity and readiness, mark activation succeeded. For a brand-new tenant, ingestion can then populate the empty target graph while intent readiness remains evaluation_pending until the reviewed evaluation data is available. This is a valid activated state, not an activation failure.

To establish intent readiness, run and record the approved evaluation set on the deployment's graph using `python -m context_graph.ontology evaluate --record` or an equivalent supported adapter, scoped to the exact binding. Confirm the command's compatibility with tenant-bound execution in phase 0; do not bypass ownership or fencing to run it. Wait for the API's evaluation cache to observe the recorded result (default TTL is 30 seconds), then verify an actual intent query. Only then mark the affected intents ready; this does not change the already completed activation outcome. Packs without retrieval intents show evaluation as not applicable with a reason.

A changed retrieval section resets the gate. Until it passes, affected explicit intent queries can return 409 and responses report `meta.eval_pending`; show that clearly while distinguishing any still-available ingestion and unaffected querying. A failed or unavailable target evaluation leaves the deployment in a visible not-query-ready state and preserves its evidence. Evaluation failure does not retroactively fail a successful activation. Never use the development serve-unevaluated override to mark intents ready. A request accepted by the admin API is not activation success. On activation failure, retain evidence and expose the actual serving state. Do not promise one-click rollback: restoring an old bundle may be incompatible with new accepted data. Initially provide operator-directed recovery with validated preconditions.

## 10. Delivery sequence and acceptance

| Phase | Deliverable | Exit criteria |
|---|---|---|
| 0: Contracts and UX specification | Screen flows, input schema, state model, API contracts and scoped permissions | One PDLC example traced through target evaluation; classifier, bound evaluation adapter, environment scope and fixture prerequisites verified |
| 1: Tenant overview and drafts | Tenant list/detail, exact active identity, draft diff and read-only readiness | No cross-tenant fetch/cache bleed; unauthorized IDs refused; no mutation of active config from draft |
| 2: Grounded authoring | Inputs, citations, assumptions, constrained agent, canonical forms and read-only YAML | A small CRM-based fixture first gains reviewed payload contracts and passes tenant-bound admission/composition; specs and events then produce a loadable private draft with explicit identity decisions |
| 3: Executable workbench | Isolated scenarios, schema/planned/observed graphs, query evaluation and evidence | Contract-complete CRM journey exercises real workers, retrieval and recorded evaluation on each claimed backend; one question artifact, negative cases, cancellation and cleanup evidenced |
| 4: Approval and activation | Digest-bound review and operational transition UI | Initial/additive scope only; mapping/breaking blocked; stale approval refused; empty-target activation succeeds with intents pending; after reviewed data arrives, recorded target pass and observed intent query are required for intent readiness; failure recovery rehearsed |
| 5: Integrated acceptance | Two-tenant operator journey through deployed UI/admin/runtime | Full PDLC acceptance after reconciling stale expectations; cross-tenant identity/resource/link access refused; deployed worker and lifecycle behavior verified, including disclosed shared restart impact |

First vertical slice: one operator, one draft tenant, a small contract-complete CRM-based pack, pasted specification and JSON event examples, explicit identity review, deterministic graph preview and a real bounded sandbox run. The existing CRM fixture has no payload contracts and is not already proven for this bound workflow. PDLC remains the domain walkthrough and later full acceptance target; its reported failures must be diagnosed rather than called a broken ontology by inference. No broad connector marketplace or generic workflow framework is needed.

Automated coverage: unit tests for validation/state transitions; API integration tests for authorization and revision conflicts; browser tests for tenant switching and draft/run flows, keyboard navigation, focus handling, screen-reader labels, graph-table parity and non-color status; real-Spanner journeys for actual storage, worker and response isolation. Negative tests should change a condition: wrong tenant, stale draft revision, unsupported contract, unavailable worker, timeout or changed active configuration. Also test dependency/name collisions, missing target evaluation data, retrieval edits resetting the gate, regex timeout, undeclared events, contract failures, classification/version enforcement and inactive feature badges. Preserve prior failures and show exactly which backend/provider combination ran.

## 11. Decisions to settle during phase 0

Proposed defaults: internal operator login with explicitly assigned tenant scopes; tenant-private packs; one canonical draft per editing branch/revision; sequential bounded sandbox slots; normalized JSON ingestion first; dedicated model execution budgets; explicit approval before activation; no hot reload initially.

Still to specify: operator identity provider, control/artifact store location, model provider and allowed source-data handling, initial document formats beyond text/JSON, sandbox capacity/retention, who can approve, and operational restart ownership. These do not block wireframes or draft contracts, but must be settled before their dependent implementation.

Comprehension checks for design review: Can an operator explain why a key was chosen? Can they distinguish a schema edge from an observed edge? What happens when source documents disagree? Can a passed sandbox run be tied to exactly the approved pack? What prevents a tenant switch from displaying the previous tenant's graph? What does the UI show if the API starts but workers are not ready?
