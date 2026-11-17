# Tenant runtime harness review

2026-10-07 — Astra low; source review only. No tests or cloud calls executed.

**Verdict: approve the bounded pre-cloud harness; no blocking findings.** This approval covers private API lifespan and five worker factory construction/cleanup on the reserved target. It does not establish request handling, worker-loop behavior, production tenant activation, read fencing, or message-envelope enforcement.

Reviewed `scripts/engram_spanner_tenant_runtime_cases.py`, the control harness runtime phase, and the relevant factory/reconciliation paths.

- The outer harness restricts the full project/instance/database, registers before network calls, takes the existing compatibility lock, and fingerprints all application tables. Runtime has no DDL submission path; schema checks and the existing-DDL subset assertion remain in place. Source hashes include the new case file, bootstrap, and runtime Python/YAML.
- The case reconstructs the existing core-only binding at the observed active epoch and verifies its digest. Registry startup verifies the complete owner identity and physical database before constructing bound adapters. Explicit token credentials replace client construction during API and worker startup; providers are scripted or disabled. No requests or consumer loops execute.
- Before factory effects, the case refuses an existing exact `OntologyState:active` node and durably records the observed control row, metadata key, and restricted cleanup intent. Projection's initial ontology reconciliation writes this metadata without replaying ledger events; the generic Spanner schema hook does not create schema objects.
- API lifespan exit and each worker store `finally` perform cleanup. Factory failure cleanup remains provided by the reviewed runtime builders. The outer case checks unchanged control ownership before deleting only the initially absent metadata key under the same fence, verifies absence, and persists completion. The main harness independently compares all application rows afterward, including failure paths.
- Fence/database assertions inspect the actual constructed adapters. Bundle identity is directly asserted for the API; worker bundle forwarding is supported by the reviewed factory code and local handoff regressions, not a new direct consumer-bundle assertion in this cloud case. The closure records establish successful cleanup calls, not independent socket-leak instrumentation.

Nonblocking improvement: read back the newly created ontology metadata after projection construction and verify its recorded bundle version before deleting it. This would make the metadata-write observation explicit; the present experiment primarily proves startup and final preservation.

Ruff cleanliness was reported by the implementer. No runtime-phase cloud result is claimed by this review. The local process lock provides coordination for this reserved experiment, not cross-host exclusive ownership of the metadata key.
