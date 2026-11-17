# Tenant dispatcher substrate review

2026-10-07. Tight read-only inspection of private dispatcher, principal guards, pinned-bundle plumbing, API cleanup and focused tests. No tests/cloud executed.

## Verdict: changes requested for one pinned-worker path

**P2 — ExtractionConsumer reloads manifests after the factory selected a pinned bundle.** `worker/extraction.py:75` still calls `configured_bundle(settings.ontology)` inside construction. `worker/__main__.py` passes the pinned capability into the LLM flag and user-store argument but does not pass the bundle to ExtractionConsumer. If a binding's pack files disappear after capture, construction can fail after `open_stores`, before run_worker receives the store handle for its finally cleanup. Changed/cached manifests can also disable user writes contrary to the pinned capability. Add optional bundle injection to ExtractionConsumer, pass the exact resolved factory bundle, and use the existing configuration fallback only when no bundle was supplied. Test the extraction path with removed manifests and pinned user enablement, plus cleanup if construction fails. The projector-path regression does not cover this constructor.

## Assessed behavior

The public tenant factory unconditionally refuses service without durable prerequisites. The private dispatcher authenticates before selecting/entering request handling, rejects duplicate authorization headers and conflicting hints, supplies a server-owned Principal, and blocks the documented metrics/webhook paths. Bound child API/admin guards use same-tenant roles rather than optional legacy keys; unavailable tenant retrieval has no raw-store fallback. Unknown credentials never route to a default child.

Root startup enters child lifespans with AsyncExitStack and closes earlier children on partial failure. Shutdown marks the dispatcher unavailable, drains active requests, and closes children in reverse order; request counters decrement in finally. API lifespan now wraps initialization and serving in store cleanup, including failure after stores were acquired. Pinned API bundle wiring reaches store read composition and retrieval. Unpinned single-deployment factory/worker call forms remain accepted.

Inspected `20261007-local-tenant-dispatch-01/pytest.log`: **94 passed, 22 warnings**. Recording children exercise routing, role separation, rotation, rejected-request call counts, partial startup and draining; they do not establish every real child route's authorization. The private dispatcher assumes a trusted factory actually consumes the binding's settings/bundle; it does not validate that factory result against the binding. Drain currently waits indefinitely for hung requests; bounded cancellation/resource policy remains necessary before production service. Process-global worker signals remain outside a multi-worker-in-one-loop contract.

This review does not claim a production dispatcher, durable ownership/epoch fencing, cursor/source bindings, complete route audit or two-database isolation. The extraction correction is within the stated pinned-substrate contract, not a request to implement those deferred boundaries.

## Remediation recheck

Read-only inspection resolves the reported P2. ExtractionConsumer accepts the pinned bundle and only falls back to configured resolution when none is supplied. The worker builder forwards the same bundle used for LLM user capability and store composition, avoiding manifest reload and capability divergence. A single outer builder exception path closes any acquired stores on later construction failure; the former projection-specific close was removed, avoiding double cleanup.

Extended tests cover removed manifests across all five worker types, pinned user-enabled model/write agreement, and constructor failure cleanup for all five types. Inspected `20261007-local-tenant-dispatch-02/pytest.log`: **167 passed, 22 warnings**, 6.90 seconds. No tests/cloud executed by this reviewer.

**Current verdict: approve the private dispatcher and pinned-runtime substrate within its stated non-production scope; no outstanding reported blocker.** Durable tenant service remains disabled, and the lifecycle/route/fence acceptance limits noted above still apply.
