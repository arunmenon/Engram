# Tenant read fencing: next slice

2026-10-07. Source-only follow-up after protected TenantControl, mutation fences and private bound factories. No tests, cloud calls or runtime edits. Public tenant startup remains disabled; this report does not remove its remaining gates.

## Minimal design

Add one synchronous `TenantFence.read(database, callback, operation=...)` helper: validate database identity, open a **strong `snapshot(multi_use=True)`**, check TenantControl in that snapshot, fully materialize callback results in the same snapshot, then close it. The extra control read makes the existing default single-use snapshots unsuitable. No lazy iterator may escape the callback. Without a tenant fence preserve current single-deployment behavior.

This guarantees that each data read is interpreted under its pinned binding/epoch/digest. Multiple calls may observe advancing application data within that epoch; they do not constitute a repeatable-data snapshot. A request-long shared Spanner snapshot across concurrent graph/vector/keyword calls is unnecessary for this slice and would add threading/lifetime complexity.

Add strict **active** checks before external request execution and immediately before releasing its completed response. The latter must use a fresh strong snapshot, not the last data snapshot or a TTL cache. Discard the response on stale identity, draining/frozen state, missing control, or inability to validate. A final valid check is the response's authorization linearization point: a transition afterward may occur while bytes travel. Absolute “no old bytes after activation” needs activation/request draining coordination and cannot be promised by another read alone.

Same binding epochs must not be reused after activation. If a drain/freeze transition may be reversed without increasing epoch, pre/post checks cannot detect an active→frozen→active interval. Either prohibit that ABA pattern by increasing the interpretation/control generation or add a monotonic serving generation checked throughout. Settle this invariant before claiming stable-epoch response behavior.

## Processing versus external reads

`TenantFence.check` currently permits processing in active/draining and read/admission only in active (`tenant_control.py:129–140`). Preserve that distinction: draining workers need ledger documents, entity matching, projection lookups, delivery counts and maintenance selection reads to finish accepted work; frozen or stale workers must stop.

The proposed shared low-level **processing** check is valid if those helpers are explicitly internal and every external path has the mandatory active pre/post boundary. It does not by itself authorize public reads. A small stricter alternative is an immutable `read_operation` chosen by existing factories—API=`read`, worker=`processing`—passed to graph/log/subscription adapters. Prefer this if direct engine/store callers are intended to have external semantics. Do not use a mutable store flag or request context to switch authorization. External admin reads use read semantics even when the same subscription methods also serve workers.

Registry startup currently checks `operation="read"` for every bound store (`adapters/registry.py:169–178`). Allow the explicit worker factory to verify processing state so a crashed old-epoch worker can restart during draining. API startup remains active-only. The pinned identity is identical in both modes; processing is not a bypass for stale epochs.

## Exact read surfaces

| Surface | Current path | Required treatment |
|---|---|---|
| Graph primitives and native vector/lineage | `graph.py:_query` (176), `_read` (188) | Both use the shared fenced snapshot helper. Generic composed reads ultimately reach these primitives; native ANN and lineage use `_query`. |
| Ledger query/keyword/retention scans | `log.py:_query` (254) | Same helper; keyword `search_scored/search_bm25` inherits it. Processing scans remain usable during draining. |
| Point/batch documents | `log.py:_documents` (544) | Fence its separate direct snapshot, including missing-record results. |
| Subscription observation | `subscription.py:delivery_counts`, `dead_letters`, `lag` (237/319/338) | Fence all three direct snapshots with caller-appropriate semantics. Mutation-backed read_new/read_pending already use `_transact`; retain those transaction fences. |
| Schema/control verification | schema and control-schema snapshots | Remain bootstrap/admin metadata checks, not an alternate application-data read path. Startup verification cannot replace runtime reads. |

Empty-input early returns and cached results may execute no snapshot. They still require the outer external response check, including empty queries, no artifact seeds, ontology/status responses and cached evaluation state. Health must distinguish a fenced runtime from ordinary backend unavailability. Root process liveness may stay data-free; tenant readiness must reflect authorization.

## Refusals must propagate

`RuntimeFencedError` is a control-plane refusal, not an optional retrieval-channel failure. Re-raise it before broad fallbacks in vector and BM25 helpers (`engine.py:615,631`); inspect `gather(return_exceptions=True)` results and re-raise a fenced member before fusing other channels. A successfully completed parallel channel must not conceal a fenced one. Artifact traversal normally propagates errors; verify wrappers/plugins preserve that property.

`graph.health_ping`, `log.health_ping` and `subscription.lag` currently catch Exception and return False/None. Re-raise control errors; retain fallback only for the failures those methods intentionally degrade. `EvalPending.packs()` also catches Exception; do not turn a control refusal into pending-pack fallback or a cached valid result. Audit admin route fallbacks, replay catch-and-continue and import per-event reporting at their existing boundaries. Map the propagated refusal to a stable sanitized 503 runtime-unavailable response; do not expose another database's control values.

Not all broad catches are store leaks: `engine.py:288,461` surround local base64/integer cursor decoding, with no store call. Narrow them to actual decoding errors when cursor handling is changed; they are not the urgent fencing gap. HyDE (`158`) and embedding (`673`) wrap optional model providers: preserve normal provider degradation, but re-raise RuntimeFencedError if providers can raise it. Avoid treating all exceptions as fatal simply to fix control errors.

## Response, streaming, cursor and cache boundaries

Implement a narrow bound-child external response guard; inject an async active-check callable from its stores. Before a completed nonstreaming response sends `http.response.start`, perform the fresh final check. Keep error responses sanitized and avoid recursive guarding of the refusal response. Direct retrieval calls used outside the HTTP child need an equivalent explicit entry/exit wrapper; otherwise describe them as internal processing APIs.

`events.py:447` returns StreamingResponse and executes imports while yielding. A final check after streaming cannot retract bytes. Keep streaming tenant import unavailable in this slice, or explicitly materialize a bounded result before sending any bytes; do not introduce an unbounded buffering proxy. Mutation fences still apply to every chunk, and discarding a response does not roll back already committed imports or access-count updates. Client retries must retain existing idempotence.

Child-local EvalPending caches remain keyed to the pinned bundle but cannot authorize a request without fresh control checks. Cache no positive active-state decision. Later caching must include binding/epoch/digest. Signed cursors bound to tenant/binding/epoch/query are required before public pagination: current context cursor is a base64 timestamp/ID, while subgraph/lineage use plain offsets. This slice may leave cursor redesign separate only while public tenant service stays disabled; reject tenant cursor use if it is exposed earlier. Public enablement also retains archive/webhook/replay and other outstanding gates.

## Focused acceptance

Test every 2+2+3 snapshot path: control and data share the same multi-use snapshot; stale/missing/frozen control prevents data access and materialization; worker draining succeeds while external draining refuses. Prove correct database handle checks and no cross-tenant reads with colliding IDs. Restart a bound worker during draining; reject wrong epoch.

Inject activation between keyword/vector/graph reads and after the final data read; both retrieval engines must discard answers. Test a fenced gather member alongside successful channels, EvalPending cache hits, empty/missing results, health/lag fallback and direct-wrapper calls. Assert no empty-success substitute and no worker ack/dead-letter caused by a fence refusal.

At ASGI level capture sent messages: no successful response start/body before final authorization, no leaked buffered data on refusal, and streaming import remains unavailable or bounded/materialized. Test stale/foreign cursors once implemented. Race generation changes and document the final-check linearization limit explicitly. Real Spanner concurrency acceptance follows local tests; existing mutation-fence evidence does not prove read consistency.
