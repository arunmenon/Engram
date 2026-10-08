# Tenant response cloud harness review

2026-10-07 — Astra low, read-only source review. No tests or cloud calls executed.

**Verdict: correct the manifest scope expression before execution (P2).** No additional mutation/cleanup blocker identified in the bounded response fixture.

**P2 — runtime/responses manifest construction fails and scope is inaccurate.** In `scripts/engram_spanner_tenant_control.py:133`, the string ending `exact metadata cleanup; ` is immediately followed by a parenthesized conditional expression. Python treats this as calling a string, causing TypeError when either phase constructs its manifest, before registration. Use explicit separate scope strings for runtime and responses. The responses description must not inherit the runtime claim of all five worker factories and metadata cleanup: this phase executes private API fixture routes and control transitions only.

The response helper durably records its observed owner and bounded intent before child startup/HTTP execution. Operator transitions persist expected state before CAS and observed state afterward. Existing explicit token/scripted-provider bootstrap and core-only runtime settings are preserved. The actual private child uses real registry control checks; fixture scope injects a trusted Principal, so this does not test credential authentication.

Positive HTTP assertions check concrete private/empty values. Cursor/import requests are refused, and the freeze case inspects ASGI response starts plus fixture-byte absence, not merely the final HTTP status. A second frozen request verifies the handler was skipped. Finally, recovery verifies owner identity/digest and bounded epoch expectation, advances epoch when reactivating frozen state, persists the recovered owner, and closes child lifespans. A new binding/child must return the expected positive response at the recovered epoch. Main application-table fingerprints and DDL/source checks remain the preservation oracle.

Nonblocking evidence improvement: persist response observations and handler calls during per-check checkpoints or finally, rather than only at successful completion. Otherwise a failed response assertion retains durable transition intent but loses the detailed captured ASGI messages useful for diagnosis.

The nominal cached case is a handler returning a fixed value without application-store reads; it proves the response guard covers that path, not behavior of a real cache implementation. No worker loops, real network HTTP process boundary, unsigned cursor acceptance, streaming import, production tenant activation, or absolute network/activation race protection is claimed.

## Manifest correction recheck

The manifest P2 is **resolved**. An explicit per-phase dictionary replaces the erroneous string-call expression; responses accurately excludes worker factories/loops and application-row writes. The new preflight regression constructs all three manifests using synthetic credentials and intercepts tracker registration, checking phase scope and token exclusion before cloud execution.

Inspected `20261007-local-tenant-response-03/pytest.txt`: **106 passed, 2 dependency warnings**. **Approve the bounded response fixture for separately authorized tracked cloud execution.** No remaining blocking finding; no tests/cloud calls executed by reviewer. The diagnostic-persistence suggestion and scope/linearization limits above remain applicable.
