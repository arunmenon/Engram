# Bound tenant store construction review

2026-10-07. Tight read-only review of optional tenant binding in registry.open_stores, control-schema validation and recording tests. No tests/cloud executed.

**Verdict: changes requested for one mutable-configuration gap.**

**P2 — Use a private pinned settings value after validation.** `adapters/registry.py:135` compares the caller's Settings to the binding snapshot, but subsequent construction continues using that caller-owned object and its nested `storage`. The database-opening await yields before backend branches execute. A concurrent caller mutation can change `settings.storage.event_log` or `graph` to memory after validation: owner verification still checks the opened Spanner database, but later branches can construct unfenced memory adapters. Other provider/archive settings can drift similarly. After equality validation, assign a fresh private `tenant_binding.settings()` snapshot and use it throughout construction and subscription closures. Add an opener-barrier test that mutates the caller's nested settings during the await and confirms all constructed ports retain pinned configuration and the shared fence.

Other inspected behavior is sound within this slice: mismatched settings/bundle fail before opening databases; the bundle is taken directly from the binding; full database handle, control columns/types/nullability/key and active identity are verified before adapter construction. The same fence reaches graph, event log and deferred subscription construction. Failure during tenant verification closes the acquired database, while unfenced legacy construction retains its existing path. Schema validation performs no repair DDL and fails closed on unexpected physical definitions.

Registered run `20261007-local-tenant-store-01` is reported as 99 passed, 1 warning. Current tests cover initial configuration/identity/schema mismatch and cleanup, but not mutation between validation and asynchronous construction. This review does not establish read fencing, event envelopes, API/worker binding handoff or production isolation; the production tenant factory remains disabled.

## Remediation recheck

The P2 is **resolved**. After validating the supplied configuration/bundle, the bound path replaces caller settings with a fresh binding-owned snapshot before resolving backend selections or awaiting the opener. Subscription closures retain that private snapshot. The thread-barrier regression mutates all five caller port selections and database identity during the opener await, then verifies all constructed ports remain Spanner on the pinned database; the adjacent shared-fence test checks fence identity.

Inspected `20261007-local-tenant-store-02/pytest.txt`: **100 passed, 1 warning**, 4.26 seconds. No tests/cloud executed by this reviewer. **Current verdict: approve the bounded tenant store-construction integration; no outstanding reported blocker.** Production tenant service, read/envelope fencing and API/worker handoff retain their stated pending scope.
