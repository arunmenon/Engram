# Explicit runtime settings substrate review

2026-10-07. Tight read-only review of create_app/run_worker settings injection and focused tests against the tenant-routing design. No tests/cloud executed.

**Verdict: approve this factory-settings substrate; no blocking regression identified in the reviewed changes.**

`create_app(settings=...)` deep-copies the supplied configuration before constructing middleware. Its lifespan uses that same private object, so authentication, middleware policy, bundle selection and store construction no longer independently reread ambient configuration. Callers retain their original Settings without aliases to nested configuration collections. The default factory still accepts no arguments and resolves environment configuration when the app is created; subsequent environment changes do not reconfigure that app. Direct legacy lifespan use retains its Settings fallback.

`run_worker(..., settings=...)` makes a private deep snapshot at coroutine execution before constructing the consumer. Existing CLI invocation remains valid, and the existing finally closes successfully returned stores. This does not make multiple concurrent run_worker calls safe as independently managed tenant workers: signal handlers and logging configuration remain process-level, consistent with the current process-oriented entry point.

The two-app test exercises distinct authentication, colliding Event IDs, independently owned stores/retrievers, core-only composition, shared middleware/lifespan snapshot identity, and caller/environment mutations. The worker recording test exercises snapshot propagation and ordinary cleanup. Inspected `20261007-local-explicit-runtime-settings-01/pytest.log`: **64 passed, 22 warnings**. No test execution by this reviewer.

Nonblocking acceptance limits: the settings snapshot is private but remains mutable through app internals; it is not a frozen TenantBinding. Existing lifespan cleanup still needs separate partial-startup/exceptional-shutdown coverage before a dispatcher owns multiple children. The current tests do not establish those failure paths, default-factory environment timing explicitly, durable isolation, transactional fences, or real two-database routing. None is claimed by this factory-only slice. Production tenant service must remain disabled until the approved dispatcher/catalog and durable binding requirements are implemented.
