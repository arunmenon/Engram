# Authenticated source trust handoff

2026-10-07. Read-only review; no implementation, tests or cloud calls. Scope is replacing agent-name trust for bound pack processing, preserving legacy unbound behavior.

## Verdict

Bound trust must be `validated acceptance.source_id ∈ pinned authenticated-source allowlist`, never `event.agent_id ∈ trusted_sources`. Current `PackProjector.plan` derives trust from agent_id (`domain/pack_projection.py:301`), and `PackExtractionConsumer._extract` repeats it (`worker/pack_extraction.py:138`). Existing ledger validation proves receipt/content consistency, but returning a JSON `document["acceptance"]` does not make arbitrary dictionaries supplied to planners authoritative.

Use a small typed internal handoff, without changing public Event or introducing an orchestration layer:

```text
VerifiedSourceProvenance:
  event_id, request_digest
  tenant_id, binding_id, database_resource
  accepted_epoch, bundle_digest, engine_revision
  source_id
```

Produce it only while reading the authoritative Events acceptance column through the bound, fenced ledger, after `validate_accepted_document`. Keep it outside payload/document JSON. A typed object is a programming boundary, not a cryptographic defense against malicious Python code; the security boundary is the authenticated store read and trusted composition.

The smallest clean port addition is an internal accepted-record read returning `(event/document, provenance)` together; support batch reads and replay entries. Preserve existing public `get_documents` and unbound callers. A narrow accepted-reader protocol plus an optional provenance field on internal LogEntry is sufficient; avoid a wholesale event-port rewrite. Bound worker factories require that protocol and fail if absent. Do not reconstitute “verified” provenance merely by parsing a caller-supplied document acceptance field. Returning a plain JSON receipt may remain useful for audit, but it is not the trusted planner input.

## Concrete callsites

Make `PackProjector` accept an immutable trust policy with explicit legacy or authenticated mode. `plan(event, document, *, provenance=None)` remains compatible for unbound use; authenticated mode requires matching typed provenance before planning. Check event ID, accepted contract identity and fingerprint association so a valid token for event A cannot authorize event B or changed payload. Missing/malformed/mismatched provenance raises a control refusal; it does not fall back to agent_id or silently produce an untrusted empty plan.

`worker/__main__.py:100,129` currently constructs projectors from settings.trusted_sources. Bound construction must provide the pinned authenticated policy and require verified records. `ontology/runtime.configured_projector` retains legacy construction only for unbound callers; callers with a binding must use explicit bound composition.

`ProjectionConsumer._fetch_events` and predecessor fetch obtain accepted records before Event projection; its pack-plan call at `projection.py:201` passes provenance explicitly. `PackExtractionConsumer.process_message` obtains the same record, and `_extract` resolves trust through the same policy before calling `profile.plan(..., trusted=...)`. Remove its separate agent-based bound check. The model cannot choose trust through its answer. `ontology/versioning.replay` must pass ledger-provided provenance too; rebuild/evaluation helpers cannot construct authenticated trust from a copied dictionary. Fail bound replay that lacks an accepted-reader source.

Keep native Entity/user extraction behavior unchanged unless it writes a property interpreted as source trust; audit any such write through the same rule. Pack plans already apply context trust to Sourced nodes and non-provenance edges. Preserve their existing confidence/link-admission limits: authenticated origin does not imply factual truth or authorize bypassing inactive pack gates.

## Configuration and temporal semantics

Add an explicitly named `trusted_source_ids` setting for authenticated producer IDs, validated with the source_id grammar. Keep `trusted_sources` as the legacy agent-ID setting. Both policy and exact source-ID list must be pinned into the tenant bundle digest. An empty authenticated list means all admitted sources are untrusted, not “use legacy defaults.”

Current legacy defaults such as `webhook:github` contain a colon, while source_id forbids it. Do not silently rewrite that to `webhook_github` or infer an alias. Operators explicitly map a verified producer/install to an admitted source_id and separately decide whether it is trusted. Credential rotation retaining source_id preserves trust; another source with the same agent_id does not inherit it. Trust is tenant-scoped, even when two tenants use the same source_id spelling.

For now the accepted bundle/engine must exactly match the processing interpretation, with permitted epoch-only advancement. The existing immutable policy therefore evaluates old receipts consistently. A trust-list change creates a new digest; do not reinterpret older receipts under the new allowlist. Changed-contract replay remains blocked until an explicit historical-policy/compatibility grant is implemented. Revoking a credential prevents new admission but does not automatically rewrite historical trust. Retroactive trust revocation is a separate explicit policy/migration decision.

## Evidence and producer boundaries

The core Event projection currently constructs EventNode from the public Event and drops receipt evidence. Persist a bounded server-owned audit subset on the core Event node—authenticated source_id, accepted bundle digest/epoch and binding identifier—or provide equivalent authoritative provenance lookup when returning DERIVED_FROM evidence. Do not put secrets or the whole raw receipt into general graph attributes. Domain trust must be explainable from the referenced Event without treating its descriptive agent_id as authentication. Add any persisted graph properties to the owning core schema/version, not ad hoc undocumented fields.

All admitted producers use this same path: generic API/batch source grants today; verified webhook binding and trusted import only when those routes are deliberately enabled. Disabled bound webhook/import paths stay disabled. An inactive pack cannot become enabled because its producer is trusted; trust is applied after active declaration/provider admission. An event with no domain rules still needs valid bound provenance for its core projection/disposition; do not skip verification merely because the pack planner returns no work.

## Focused acceptance

- Same agent_id with trusted and untrusted authenticated source IDs yields different correct trust; forged webhook agent names, payload source_trust and document receipt copies cannot grant trust.
- Trusted source with an arbitrary descriptive agent_id remains trusted; rotated credentials retaining source_id behave identically. Legacy unbound tests retain old agent-based behavior.
- Missing/wrong-type provenance, another event's provenance, payload mutation, foreign tenant/binding, changed bundle/engine and future epoch refuse without derived writes or terminal disposition.
- Epoch-only old receipts succeed under the same policy; allowlist change blocks old-contract processing rather than silently changing trust. Missing authenticated allowlist never uses legacy colon IDs.
- Projection, extraction, replay and predecessor/core evidence carry matching source attribution; model-supplied trust is ignored. Inactive packs remain inactive and no-rule events still validate authoritative provenance.

Required choices are explicit producer IDs/trust grants and whether core evidence is persisted or resolved from the ledger. The typed handoff and exact-policy rule can proceed without enabling new producer paths or historical trust migration. Local tests and real bound Spanner provenance journeys remain separate evidence gates.
