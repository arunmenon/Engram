# Runtime tenant binding handoff review

Date: 2026-10-07. Astra low, read-only source and recorded-evidence review; no tests or cloud calls executed by reviewer.

**Verdict: approve the bounded runtime handoff. No blocking findings.** This does not approve production tenant activation, read fencing, message envelopes, or complete tenant isolation.

Reviewed `TenantBinding.runtime_configuration`, registry reuse, API lifespan and private bound-child factory, worker builder/runner, and `test_runtime_tenant_binding.py` alongside existing store-binding regression coverage.

- `tenancy.py:151` validates any supplied settings by full value equality and any supplied bundle by pinned object identity, then returns a fresh settings value and the binding's bundle. The runtime does not retain the caller's mutable settings after validation. Registry reuse preserves the earlier protection against caller mutation during an awaited database open.
- `api/app.py:60` validates the bound configuration before constructing providers or stores, and forwards the binding and pinned bundle to `open_stores`. `_create_bound_child` supplies the binding's explicit settings and bundle at construction, so the supported private path does not resolve ambient ontology configuration. Legacy manual unbound lifespan settings fallback remains intact.
- `worker/__main__.py:81` applies the same validation before providers/store construction. All five worker branches forward the binding through store options; consumers and processing gates continue using the pinned bundle. `run_worker:263` selects binding configuration without constructing ambient `Settings`, and existing constructor-failure and runner-finally cleanup paths remain in place.
- `api/tenants.py:30` still rejects the public production factory unconditionally. The new private factory is a conformance entry point, not a production release switch.

Recorded evidence: `runs/20261007-local-runtime-binding-01/pytest.txt` reports **72 passed, 1 dependency deprecation warning**. Focused tests cover API handoff and pre-start settings mismatch, all five worker handoffs, ambient-setting independence, and cleanup after a fenced worker exit. The aggregate also includes catalog, dispatcher, explicit-settings, store-binding, and worker-fence regressions. These reference-port tests establish wiring and failure behavior, not cloud enforcement.

Minor coverage note: the API mismatch test asserts no store open; its title also promises no provider construction, which is established by source ordering rather than an explicit provider-spy assertion. This is not a release blocker for this scope.
