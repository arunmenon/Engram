# Tenant admin/workbench review disposition

Date: 2026-10-30. Scope: revisions to `docs/tenant-admin-workbench-plan.md` only; no runtime, fixture or UI implementation and no new runtime test results.

| Review finding | Disposition |
|---|---|
| Missing deployment evaluation gate | Accepted: section 9 marks activation succeeded once runtime and required workers confirm the binding; recorded target evaluation and observed intent readiness are a separate gate. A new tenant can activate with intents pending while producers populate its graph. Section 7 requires the target dataset/expected IDs to be reviewed; synthetic expectations cannot silently unlock production. Tenant-bound evaluation adapter compatibility is a phase 0 prerequisite. |
| Change class/procedure/version bump | Accepted: backend classifier drives review. Initial/additive only in the first admin release; mapping replay and breaking rebuild are explicitly deferred. Additive engine capability does not imply shared-service hot reload. |
| Retrieval authoring | Accepted: Intents and questions owns retrieval configuration; Evaluation owns execution/results. Intent examples are not automatically scored questions. |
| Multi-pack composition | Accepted: explicit built-in roots, private catalog, dependency resolution, global-name checks and whole-bundle approval. |
| Event handling/contracts | Accepted: dedicated contracts surface, processed/ledger_only/unsupported decisions, reviewed sample-derived contracts and handler checks. |
| Two question stores | Accepted: one versioned evaluation artifact consumed by UI, sandbox and deployment gate. Any target-specific revision is explicit and reviewed. |
| CRM first rather than PDLC | Qualified acceptance: small CRM-based executable slice, full PDLC later; preserve PDLC domain walkthrough. Existing CRM fixture has six events without payload contracts, so adapting it and proving tenant-bound execution are prerequisites, not existing evidence. PDLC expectation failures do not alone establish that its ontology is broken. |
| Environment, processing failures, inert fields, extraction, deletion, retention, accessibility | Accepted in sections 5, 8 and 10. New extraction authoring deferred; preserve inherited sections read-only. |
| Mapping by example, key evidence, lifecycle, footgun lint, answer explanations, coverage, proposal diffs | Accepted. Sample uniqueness and regex timing are bounded evidence; missing runtime attribution stays unavailable until instrumentation exists. |
| YAML synchronization cost | Accepted: parsed canonical configuration and generated read-only YAML initially. |

Source checks: `src/context_graph/domain/pack_versioning.py`, `src/context_graph/ontology/evaluation.py`, `docs/runbooks/pack-authoring.md`, and `tests/fixtures/packs/crm/crm.pack.yaml`. The current PDLC file has **25 declared event types in 1,357 lines**, not 84; coverage must be computed from the selected bundle, not hardcoded from the review. Evaluation passes by mean F1 against the configured threshold, not necessarily perfect results on every question. The revised plan requests both per-question diagnostics and the aggregate decision.

Deferred features are visible scope boundaries, not closed implementation findings: mapping replay/rebuild UI, editable YAML round trips, extraction authoring, expanded explanation instrumentation and automatic environment promotion.
