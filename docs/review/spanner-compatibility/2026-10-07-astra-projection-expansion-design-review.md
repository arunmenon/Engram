# Projection expansion: bounded #36 correction

2026-10-07. Read-only review of the plan's “Projection semantics implementation start” section, pure projector, projection worker and apply_plans. No code changes, tests or cloud calls.

## Verdict

Approve strict key-list zipping and a fixed per-event planning limit as a bounded first correction. Two requirements block a complete implementation of that narrow claim: equal-length edge pairing must avoid its current quadratic nested scan, and the budget must cover **every** subscriber/rule and operation-producing path, not just direct upserts/edges. Keep #36 open for the explicitly excluded null/order/ownership/transaction semantics.

## Minimal mechanics

Introduce one dedicated deterministic `ProjectionExpansionError` carrying a stable reason code and safe counts/rule location, never payload values. Raise for unequal key-list lengths and budget overflow; do not append a reason to `plan.rejected` and return a partially built plan. `plan()` owns a fresh budget and discards its entire local plan on exception.

`_fan_out` currently uses `min(lengths)`. Require exactly one distinct list length when any lists exist. Equal lists zip, all-empty lists produce no rows, and scalars broadcast as before. Empty+nonempty refuses. Check cardinality before building row dictionaries or `_Keyed` lists. No-key-list/scalar behavior remains one row. This correction concerns key lists only: `_Keyed.pick`'s treatment of mismatched property lists is unchanged and must not be advertised as fixed.

Use a small local budget value, passed through the existing planning helpers or context, with a fixed 10,000 inclusive limit. `check_expansion(count)` checks a prospective temporary expansion before allocation; `reserve(count)` charges actual plan entries before append/extend. Keep these separate so references do not double-charge output operations. Count nodes, lifecycle states, direct edges, generated DERIVED_FROM edges, endpoint stub writes and deferred lookup instructions. Count repeated operations as planned, even when storage might later MERGE them to one row. An upsert plus provenance edge costs two, not one.

One budget spans `registry.rules_for(event_type)` in canonical order, including rules contributed by different subscribing packs. It must not reset per rule, endpoint, pack or list. Incremental aggregate checks prevent several individually small rules exceeding the event cap. Apply preallocation checks in `_keyed_refs`, list-valued `node_id` endpoints, lookup known endpoints and edge pairing; `_plan_transition` and `_plan_lookup` charge their emitted entries too.

For Cartesian edges calculate `len(sources) * len(targets)` before building pairs. Prefer lazy nested iteration after the cap check, avoiding an intermediate pairs list. For equal fanned endpoints, current code still executes S×T comparisons with `if s.index == t.index`; replace that with an index-based join. Preserve original `_Keyed.index`/`count`, since invalid keys may have been skipped. Zipping surviving arrays by position would create wrong cross-links. Build an index map of one side and emit matching original indices in the current source order. Equal fanned counts zip; otherwise Cartesian remains the explicit current rule.

Define prospective expansion checks conservatively: an oversized candidate list/product may refuse even when later coercion or endpoint permissions would discard some entries. This is necessary to bound attempted work before materialization; document it separately from the final emitted-operation count. Do not turn checks into silent truncation.

## Important limits and bypasses

`_eval` may allocate list values before `_fan_out`: expression wildcard `_walk`, regex captures, list-property coercion and match_any_prefix tuple construction are separate work. Check projector-owned copies before constructing them, including large prefix tuples. The 10,000 planned-operation limit does **not** bound input JSON size, all expression-evaluation memory, property value size or CPU. Existing ingress/expression limits continue to apply. Do not expand this patch into an expression-engine rewrite, but state this limit clearly.

`worker/pack_projection.apply_plans` flattens several event plans, then writes nodes/states before resolving lookups. Each lookup may produce up to lookup_limit actual edges. Thus 10,000 lookup instructions can produce substantially more than 10,000 edges, and a flush can exceed 10,000 operations across several valid events. The approved first claim is a **per-event deterministic plan** bound, not a bound on actual writes or the whole flush. Record those as remaining resource-control work. Do not add a late lookup-overflow refusal after nodes/states have already committed and describe it as no partial writes; solving that requires different preflight/application semantics.

Extraction creates ProjectionPlans through its own profile limits and does not pass through PackProjector.plan. Keep those existing limits distinct. If introducing a generic apply_plan guard, it must run before any writes, cover direct constructed plans, and avoid unexpectedly rejecting whole valid multi-event flushes under a per-event threshold. Such a guard is optional defense, not a substitute for preallocation checks in the planner.

## Deterministic disposition and compatibility

`ProjectionConsumer._flush_buffer` writes common Event/FOLLOWS/CAUSED_BY data first. `_apply_pack_rules` then plans each event; planning exceptions call `_pack_failed`, which dead-letters that event, and other valid plans may proceed. This can support the desired semantics: common evidence remains, **none of the rejected event's domain plan is submitted**, and valid sibling events continue. Catch/log the dedicated expansion error explicitly for stable diagnostics instead of presenting it as an opaque unexpected exception. Existing authenticated ACK/DLQ checks remain mandatory; a control refusal still propagates and must not become an expansion DLQ.

The final batch ACK currently includes entries already dead-lettered. Preserve/document the subscription's verified idempotent absent-pending behavior or omit terminally disposed IDs; do not count the event as successfully domain-projected. Tests must assert the recorded failure and pending/DLQ outcome, not just absence of graph nodes. Common event creation is not admission rejection. No claim of general atomicity follows: apply_plans storage failures can already leave partial domain effects before fallback.

These are engine interpretation changes: previously truncated or huge inputs now fail. Pin a new engine revision/binding digest for cloud execution and future bound runtimes. A constant-only change does not require changing pack YAML when its declarations are unchanged, but document the semantic correction and new limit. Do not backfill old receipts under the new engine through a compatibility shortcut. Existing exact-contract replay restrictions still apply; cloud activation must use the reviewed empty-target CAS flow or another explicitly compatible target.

## Acceptance

Local projector cases: equal/scalar/all-empty/mixed-empty/unequal key lists; exactly-at/one-over cap; provenance/stubs/states/lookups accounting; cumulative rules and multiple subscriber packs; unequal endpoint lengths retaining bounded Cartesian behavior; equal original counts with invalid-key gaps preserving index correlation; over-limit node_id references and products refused before allocation. Use small counters/spies to establish ordering of checks, not enormous allocations. Preserve PDLC and unfamiliar-pack expected plans.

Worker cases: one rejected and one valid event in a flush, no rejected domain calls submitted, common Event present, deterministic DLQ evidence, no spurious successful domain metric, and fence refusal leaving work recoverable. A late rule failure must discard earlier in-memory operations from the same event. Include replay/direct planner invocation so limits do not depend on HTTP validation.

Real Spanner acceptance: a small unfamiliar pack and exact registered fixtures demonstrate unequal-list failure, capped product failure, cumulative overflow and valid correlated/scalar cases. Verify common Event provenance and accepted receipt, zero rejected-event domain nodes/edges/states, valid sibling output, and exact terminal delivery effects. Use the pinned new interpretation and exact owned cleanup/restoration. This proves the bounded correction only; lookup expansion, null semantics, ordering and competing writers remain open #36 work.
