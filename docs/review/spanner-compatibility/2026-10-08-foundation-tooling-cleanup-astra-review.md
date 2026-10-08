# Foundation tooling cleanup — scoped Astra review

Verdict: no blocking findings in the reviewed scripts diff, shared support module, or new support tests. This is a proportionate helper extraction, not a new runner framework. No runtime-source review or cloud acceptance is implied.

| Concern | Source assessment |
| --- | --- |
| Authentication | `engram_experiment_support.py:143` preserves catalog token authentication, rejection of duplicate authorization headers, tenant principal assignment and `TenantResponseGuard`. Each goal explicitly supplies its original token, matching its settings and HTTP client. Webhooks retain the existing handler authentication path. |
| Cancellation and shutdown | `await_settled` is moved unchanged. All three entrypoints still wrap execution with it. `stop_demo` at line 199 preserves stop → gather workers without cancellation → close stores → stop/wait server ordering and error accumulation. Each goal records errors and retains its final failure assertion before reporting success; ownership cleanup remains in the goal runner. |
| Evidence and oracles | Snapshot SQL, seven-table fingerprinting, durable JSON persistence and owner reads retain their previous fields and semantics. The diff leaves scenario, graph, retrieval, no-write and cleanup ownership assertions intact. |
| Dependencies and compatibility | The shared module imports no scenario runners and introduces no import cycle. Existing runner helper names remain explicit re-exports. Script execution retains sibling-import conventions; the new unit test uses the package-qualified support import. `CONTROL_COLUMNS` matches the existing control row order. |
| Scope and tests | The new tests target credential rejection, authenticated response checks, cancellation settlement, shutdown order and retained shutdown errors. They exercise behavior rather than merely mirroring the helper signatures. I inspected them without executing them. |

The helper's shutdown contract depends on the retained outer `await_settled` wrapper; this extraction does not introduce standalone cancellation shielding inside `stop_demo`. That existing composition remains intact.

Only this review document was written. No implementation changes, test execution, cloud calls or delegation were performed. Executor test results remain separate from this source review.
