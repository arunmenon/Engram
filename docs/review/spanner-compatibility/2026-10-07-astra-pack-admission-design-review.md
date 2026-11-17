# Pack contracts at authenticated admission

2026-10-07. Read-only design review of payload contracts, ontology declarations, ingest routes, authenticated writers and Spanner acceptance. No implementation, tests or cloud calls. Terminal-disposition cloud evidence belongs to its separate slice.

## Decision and minimal ownership

Compile one immutable `AdmissionPolicy` from the exact active bundle, with methods returning a structured decision for `(Event, original_payload, authenticated_source)`. It resolves event ownership, supported handling, payload contract and source authorization. Keep this pure domain logic, independent of HTTP and storage. Cache validators by immutable contract/bundle content; `PayloadContract.validate_payload` currently rebuilds its Pydantic model for each call.

Use the policy at the **authenticated writer/bound ledger append boundary**, not only in `routes/events.py`. `get_event_writer` already creates an immutable request writer through AdmissionBindable; retain that seam. Bind the policy to the store's pinned bundle/digest and fail bound construction if missing or mismatched. Every direct bound `append`, `append_batch` and `append_batch_outcomes` must invoke the same policy before any new Event row is inserted. Routes reuse the policy for per-input diagnostics, without maintaining a second set of rules. Keep the transaction-local tenant/source check and receipt stamping in Spanner; pure prevalidation does not replace the admission fence.

No PDLC-specific branches or adapter generator are needed. Core is mandatory; selected PDLC, CRM and unfamiliar packs get behavior from their declarations and existing projection/extraction providers.

## Event admission rules

`OntologyRegistry.accepts_event_type` currently rejects undeclared names only inside loaded closed namespaces. Disabling PDLC makes `pdlc.*` open again. Bound admission must instead positively resolve an active event declaration, or a **deliberately configured core open namespace**. Preserve needed core tool/agent events through an explicit core policy, not “anything outside loaded domains.” Unknown/unselected domain events reject before append. If a server catalog knows the owner is disabled, return `pack_inactive`; otherwise `event_unsupported`. Do not discover/load arbitrary packs from event names.

For each active declared event distinguish:

- **Processed:** a supported enabled projection rule or extraction profile subscribes. Contract-valid admission means eligible for processing, not that an artifact already exists or a conditional rule will necessarily write one.
- **Intentionally ledger-only:** an explicit manifest declaration says retain the valid event without domain interpretation. Add the smallest explicit marker, such as `handling: ledger_only`, to EventDef. Reject contradictory use with processing subscriptions; a manifest note or absence of rules is not enough.
- **Unsupported:** no supported processing and no explicit ledger-only declaration. Reject with a stable reason rather than returning an ambiguous success. Provider availability is checked at bundle construction.

Do not declare all 23 PDLC events “projected” merely because contracts exist. Produce a declaration-derived inventory of contract, enabled consumers and handling for every event; resolve unmapped items explicitly. The current EventDef has contract/aliases/note only. CRM fixture events are currently `{}` with no contracts; add bounded contracts and version the pack before claiming CRM validation. Existing optional contracts can remain schema-compatible for unbound legacy use, but bound domain admission must reject unsupported contractless events or fail bundle readiness with a clear inventory. Do not silently substitute an unconstrained contract.

## Payload and error semantics

The prototype is **strict observational validation**. Run it on the supplied normalized source payload, but persist and fingerprint that original payload. Do not serialize the Pydantic validation result: optional missing fields can have internal defaults, and rewriting would erase the omission/null distinction. `additional_fields: preserve` retains unknown fields; all retained values must also satisfy global finite JSON/fingerprint/body-size bounds. Contract declaration depth/field bounds do not alone bound arbitrary extra payload contents.

Normalization means verified source translation into the pack's documented shape, not coercing invalid generic input. Missing/null payload fails an object contract; `{}` succeeds only if its declarations allow it. Preserve explicit null versus omitted fields and strict boolean/integer/number distinctions. Current core events without a payload contract retain their deliberate generic JSON behavior.

Return sanitized errors with original input index, event ID when available, canonical event type, stable reason code and field path. Pydantic error input/context may contain secrets; expose neither. Contracts must not execute code, fetch remote references or rewrite authenticated identities.

Single, batch and NDJSON import share the same checked-input representation. Keep one outcome per original input; stable sorting for import changes append order, not result identity. Validate all items locally before submitting valid ones; map store created/duplicate/conflict/failed outcomes back through original indexes. Invalid siblings do not disappear, become storage failures or prevent valid siblings according to existing partial-success semantics. Reject mismatched event/payload list lengths at internal boundaries rather than silently filling payloads with None.

**Duplicates need a deliberate ordering:** a same-source, same-request historical retry must retain its original acceptance even if today's payload contract differs. Compute the fingerprint, then let the transaction distinguish existing identity from new admission; contract rejection applies to new insertion. A prevalidation error cannot automatically override an already accepted matching request. Different payload/source remains conflict, and stale runtime fencing always applies. If this first slice retains exact-contract-only activation, document that limitation and test duplicates under the unchanged bundle; do not introduce an incompatible cross-version retry promise accidentally.

## Authenticated source trust and pinned contracts

`PackProjector.plan` currently derives trust from `event.agent_id in trusted_sources`, and pack extraction repeats that check. Reserving `webhook:` only in a generic HTTP route does not secure direct adapters or other allowlisted agent IDs. Resolve authorization/trust from the accepted server-owned `source_id` and pinned source policy. Pass explicit verified provenance into projection/extraction; agent_id remains descriptive. Do not promote trust because current configuration now trusts an old source that was untrusted at acceptance: either persist the admission trust decision/policy revision or resolve it against the exact immutable accepted bundle snapshot. Unverifiable provenance is not trusted.

Receipt bundle_digest already pins exact manifest contracts and engine revision; no new per-pack version column is necessary now. `PayloadContract.version=1` identifies contract syntax, not a particular event schema revision. Contract declaration/handling changes require pack version changes and bundle identity changes. Existing accepted-document validation and future replay grants must keep the original contract provenance. Alias handling must likewise be explicit: generic ingestion accepts canonical declared names; verified translators may map declared source aliases, without changing original source evidence.

## Admission paths and bounded sequence

1. Implement pure compiled policy, event handling inventory and sanitized indexed decisions; wire ordinary single/batch API plus **all bound ledger append variants** to it. Add PDLC/CRM/unfamiliar declaration cases. Keep unbound compatibility explicit.
2. Make projection and pack extraction consume authenticated receipt provenance, and resolve the known webhook retry-normalization issues. Only then claim source-trust enforcement.
3. Reuse the gateway for authorized imports and verified source adapters. Bound import currently returns 503 and signed tenant webhooks remain unavailable: keep those refusals until their identity/streaming/normalization contracts are implemented. Unbound webhook code currently appends through raw event_store and filters translated event types itself; when enabled for tenants it must use the authenticated gateway and report unsupported translations explicitly. Raw migration imports/bare entries remain forbidden, never unstamped alternate admission.

The first slice is complete only as **bound generic admission enforcement**, not all-source ingestion. Full feature acceptance includes every enabled ingress, all 23 PDLC event outcomes, CRM and an unfamiliar pack through admission→projection/extraction→retrieval, including contract-invalid payloads, inactive/unknown events, deliberate ledger-only events, spoofed trust, duplicates/conflicts and original-index batch results. Test no append for rejected inputs, receipt digest consistency, omission/null preservation, and direct-adapter bypass attempts. Real cloud and source-adapter journeys remain separate evidence gates.
