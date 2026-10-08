# Tenant-specific hierarchies and policy-aware graph isolation

Feature ticket: https://github.com/arunmenon/Engram/issues/49 (under #43, within #34).

Initial design brief — proposed, not implemented or verified. Separate from G5. Related: #43 tenant/database routing, #34 pack composition, #39 conformance, #41 Spanner verification, #48 ANN experiments.

## Problem and concrete examples

Database-per-tenant remains the agreed outer isolation boundary. Inside a tenant, different teams may need different visibility even when they share a database and ontology packs. Tenant A might use company → division → team → project. Tenant B might use client → engagement → workspace and allow staff to belong to several engagements. Engram must not impose one fixed hierarchy on both.

Example: a Payments engineer can read the password-reset project but cannot read an HR incident. A company-level reviewer might see several projects, while an external contractor sees only one. Sharing a parent organization or a graph relationship must not itself grant access. A requirement linked to a restricted design must not expose that design's title, evidence, or summary through retrieval.

## Grounding in current Engram

`src/context_graph/tenancy.py` currently defines TenantBinding (tenant, database, active bundle, revision/epoch) and Principal (credential, tenant, api/admin roles, source identity). These inspected models do not express hierarchy membership or per-resource permissions. `src/context_graph/adapters/spanner/tenant_control.py` provides tenant binding/fence structures; those are not a within-tenant hierarchy policy model. This brief does not claim a complete authorization audit or a demonstrated exploit.

Extend the existing binding and authenticated-context approach rather than inventing a second engine or permission system per ontology. Core remains mandatory; selected optional packs define domain meaning, not independent security authority.

## Proposed flow

Authenticated caller → server-resolved tenant/database → current hierarchy memberships and action policy → authorized write or retrieval plan → tenant-bound Spanner operations → authorized artifacts and evidence.

Workers inherit persisted resource scope and processing authority, not an untrusted payload's claimed permissions. Before returning results, the request is evaluated against current access policy; replaying an old accepted event must not resurrect revoked access.

## Design requirements

| Area | Required behavior |
| --- | --- |
| Hierarchy model | Tenant-defined stable scope IDs and parent relationships; determine whether a tree is sufficient or multiple parents are needed. Reject cycles and cross-tenant parents. Keep membership separate from hierarchy structure. |
| Policy | Define read, write, link, share and administer actions. Explicitly settle inheritance, deny precedence, multiple memberships, default access and delegation before implementation. Unknown policy/scope fails closed. |
| Resource identity | Every protected event/artifact has explicit scope attribution, with deterministic handling of shared or multi-scope artifacts. Tenant-wide resources are deliberate, not an accidental fallback. Scope supplied by a producer must be authorized. |
| Relationships | Permission to read both endpoints does not necessarily authorize the relationship. Define edge visibility and creation rights; cross-scope links never grant access by themselves. |
| Admission | Authorize source and scope before ledger append; preserve trusted attribution for workers, receipts, duplicates and conflicts. Unauthorized requests must not mutate state or reveal a hidden resource through a conflicting-ID response. |
| Workers | Projection, extraction, enrichment and consolidation preserve scope. Derived artifacts inherit a defined restriction policy from their inputs. No mixed-scope summary may disclose restricted facts. Do not guess visibility from text or ontology type. |
| Retrieval | Apply authorization to seeds, traversal nodes/edges, text/vector search, hydration, evidence, summaries, ranking inputs, counts, exports and pagination. Final response filtering alone is insufficient. |
| Search | Measure eligible-corpus recall and top-k behavior under selective policies, linked to #44 and #48. Never silently search unauthorized vectors and treat post-filtering as proof of correct authorized search. Validate supported query/index strategies before promising performance. |
| Policy changes | Define scope moves, revocation and membership changes, cache invalidation, in-flight request behavior and the effective policy version. Cursor/cache identity must include the security context; stale contexts cannot widen access. |
| Operations | Scope admin, replay, retention, export and cleanup. Distinguish tenant administrators from cross-tenant operators; elevated operations are explicit and auditable. |
| API behavior | Decide safe forbidden/not-found responses and authorized completeness reporting. Avoid leaking hidden artifact existence, names, evidence or relationship counts. |

## Pack contract impact

A shared security contract applies to all packs, including built-in specialized workers. Packs may declare how their resources carry scope and how derived outputs inherit restrictions, but cannot override authenticated tenant or policy decisions. Unknown/unscoped outputs cannot become public automatically. Verify PDLC, core summaries, optional user/memory processing and an unfamiliar pack without adding pairwise pack branches.

## Smallest first design slice

Choose two representative tenant hierarchy shapes and one concrete policy for each. Inventory the real write/worker/read enforcement points using existing components. Specify resource and edge scope semantics and a minimal current-policy evaluation interface. Compare a tree-only design with multiple-parent support only if the customer examples require it. Do not add a separate policy service, database-per-team scheme or generic policy language without a demonstrated need.

Deliver a reviewed decision table, API/resource-context examples and executable acceptance fixtures before runtime implementation. This is an initial feature/design brief, not a commitment to every possible enterprise authorization model.

## Verification strategy

Use two real tenant databases with colliding resource IDs and different hierarchy shapes. Within each, use two teams plus a restricted project and test authorized and unauthorized callers. All functional acceptance uses Engram's real write, workers and read path on Spanner; direct database reads are diagnostic only.

Predeclare expected visible nodes, edges, evidence and forbidden effects for: parent/child inheritance, explicit deny, multi-membership, cross-scope links, unauthorized writes, forged scope claims, duplicate/conflict probes, scope moves, revocation, stale caches/cursors, missing/cyclic hierarchy, restricted evidence, mixed-scope summaries, selective ANN search, background processing and scoped admin operations. Test in-flight policy changes under the chosen consistency rule. Hidden resources must not appear in answer content, snippets, counts or errors. A restricted search returning fewer results must not be mislabeled complete without the defined evidence.

Record inputs, principals/scopes, effective policy versions, API responses, worker outcomes, visible/forbidden graph output and retrieval evidence. End with stakeholder walkthrough and issue reconciliation. No historical-data migration, Redis/Neo4j runs, resource provisioning or implementation is authorized by this brief.

## Decisions to resolve

1. Which customer examples need a tree versus multiple parents?
2. Are parents automatically allowed to read children, or only through explicit grants?
3. How are explicit denies, shared artifacts, edges and derived summaries handled?
4. What consistency promise applies to revocation and in-flight work?
5. Which existing identity system supplies authenticated memberships and who may manage policy?
6. Which bounded policy combinations can the Spanner search path enforce efficiently?

G5 continues under its existing scope. Hierarchy-aware isolation needs its own approved implementation goal and real verification; this document adds neither a G5 requirement nor a compatibility sign-off.
