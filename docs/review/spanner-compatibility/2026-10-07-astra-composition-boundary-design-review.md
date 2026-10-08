# Composition boundary design review

2026-10-07. Read-only review of the current working tree; only this report was written. No cloud, services, GitHub changes, or test execution. This refines the adjacent pack-optionality review for the first runtime slice, not production signoff.

## Decision and minimal interface

Approve incremental deployment composition, with two boundaries: schema selection and executable runtime composition. Keep specialized built-in implementations. Do not introduce an orchestration service or combinations such as “core+PDLC mode.”

Recommended public interfaces:

```python
load_registry(names, search_dirs=None, *, builtin_packs=None) -> OntologyRegistry
resolve_bundle(registry, provider_catalog) -> ActiveBundle
configured_bundle(settings.ontology) -> ActiveBundle
```

`builtin_packs=None` preserves current memory/user defaults; `[]` selects no optional built-ins. Always include core. Validate optional built-in names against memory/user, deduplicate deterministically, and resolve the existing named dependency closure. A selected domain requiring user re-enables user: omission means “not a root,” not a denylist. Report requested roots and effective closure separately. Preserve protection against shadowing all three built-in files. `OntologySettings.builtin_packs` defaults to `[memory,user]`; existing `packs=[pdlc]` remains unchanged. Cache keys must include built-in selection; no truthiness fallback may turn `[]` into defaults.

Make `ActiveBundle` a frozen value containing the registry, effective pack identities, enabled processing IDs, query availability, and allowed node/edge types. Use tuples/frozensets or read-only mappings; a frozen dataclass wrapping the registry's mutable dictionaries is not deep immutability. Keep the existing direct `OntologyRegistry([...])` schema API and constructor-based tests working. Resolve runtime bundles separately; direct callers must not accidentally acquire default memory/user behavior. Production composition roots must always pass an explicit bundle.

Smallest new declaration shape:

```yaml
processing:
  requires: []
  enabled: [user.extract.v1]
```

`enabled` selects implemented processing handlers; each enabled ID implicitly requires engine support. `requires` only checks engine support and never starts processing. Use finite, exact versioned IDs initially, not another semver expression language. Existing `pack.requires` remains exclusively a pack/schema dependency. Do not add a pack-controlled `provides` mechanism: engine code owns a small provider catalog mapping supported IDs to handlers, owning schemas, prerequisites and outputs. Unknown IDs, unauthorized specialized handlers and unmet output/schema prerequisites fail before stores open. A domain cannot impersonate the user handler by naming its ID without its owning schema/provider contract.

Use existing nonempty projection rules and valid extraction profiles as the declarations for generic domain processing; normalize them centrally into `pack.project.v1`/`pack.extract.v1` bindings by pack. Repeating them in `processing.enabled` creates conflicting switches. Core's specialized Event projection, Entity extraction, enrichment and Summary/retention remain core facilities; memory declares no imaginary producer. Bundle query availability derives from active types/intents and available query providers, independently of whether an extraction writer is enabled.

## Blocking implementation details

1. **Selection must reach every composition root.** `ontology/runtime.py` currently caches only packs/directories. `worker/__main__.py` resolves a registry only for projection and pack extraction; other consumers open stores independently. Resolve/validate once before constructing any consumer or expensive provider. `_build_consumer` can remain the factory. A requested pack-extraction consumer with zero profiles should have an explicit disabled/no-work result before opening stores. Validate provider metadata centrally, but instantiate process-specific dependencies only for the selected worker.

2. **Entity extraction is core; user output is optional.** `worker/extraction.py:226` already isolates profile writes behind `UserStore`, while Entity resolution/references use graph access. Pass `user_store=None` when user extraction is disabled and retain core graph access. Also pass one immutable extraction-target policy to prompt construction and result filtering. Splitting `_ONTOLOGY_SCHEMA` alone is insufficient: `adapters/llm/client.py:520` separately demands persona/preferences/skills/interests in `_call_llm`. Both prompt messages, examples, parsing and output acceptance must follow the target policy. Test a noncompliant model returning user fields anyway. Do not remove legitimate person Entities simply because user profiles are disabled. Core consolidation writes Summary/SUMMARIZES, not memory Episode; keep its summaries and retention active without memory.

3. **Selection is not enforced by intents alone.** `api/app.py:98` builds both event and artifact retrievers, but event retrieval has fixed-table fallback for direct construction. Preserve that compatibility only outside explicit composed runtime. `RegistryIntents` filters loaded owners, while traversal, provided seeds, cross-pack edges and historical rows require active-type checks too. Enforce before expansion/ranking and at output, so inactive intermediates cannot influence visible answers. Validate specialized seed strategies and artifact plugins against the provider catalog. Both retrieval contracts remain separate.

4. **Historical APIs need an explicit result.** Gate user read endpoints centrally through their dependency on the bundle and return a stable `pack_inactive` response without querying storage. Historical disabled data stays stored and hidden from ordinary queries; disabling does not delete it. Privacy export/erasure and administrative cleanup need a deliberate historical-data path—do not accidentally strand them behind the ordinary user-read gate. Activation/catch-up and destructive cleanup remain separate work; `allow_breaking` is not an activation protocol.

5. **Declarations change versioned behavior.** `Pack.canonical_json()` serializes defaults; adding empty `processing` to the model can change every existing pack hash without any manifest edit. Preserve legacy canonical output for an empty absent-equivalent declaration, and test recorded snapshots. Explicit declarations require pack-version bumps. `domain/pack_versioning.py:_compare_packs` currently enumerates sections and would miss processing semantics: add explicit comparison. Added processing requires at least a minor version; removal or incompatible handler-major replacement is breaking. Existing reconciliation cannot replay specialized extraction merely because a declaration changed; flag transition work instead of claiming catch-up. Exact engine-handler versions and pack semantic versions serve different purposes.

## Sequencing and acceptance

**Safe now:** implement loader/settings selection, cache identity, strict processing declarations/provider validation and pure bundle resolution; keep default behavior and direct schema APIs compatible. Add worker user-output/prompt composition and core preservation as the first executable slice. Describe completion narrowly until API/retrieval gates land. No tenant dispatcher is needed: make the bundle explicit so forthcoming #43 can bind it to tenant-routed stores without ambient globals.

**Required before claiming runtime optionality:** both retrieval paths and ordinary user APIs enforce the same bundle; historical-data policy and worker/API identity agreement are tested. Selection on existing stores must still respect reconciliation's breaking-change guard. Fresh-store acceptance does not prove dynamic activation or tenant isolation.

Focused acceptance tests:

- Default, core-only, core+memory, core+user, core+PDLC and all packs through real composition factories with recording ports; reordered roots resolve identically, dependencies re-enable explicitly required built-ins, invalid selections fail before store opening.
- Core+PDLC session completion writes Entities/references and domain artifacts, never user outputs; core+user preserves profile/preferences/skills/interests. Check both session-end and mid-session triggers, both LLM messages and injected unwanted model fields.
- Memory off preserves Event enrichment, Summary/SUMMARIZES and core retention. Memory on does not advertise an unimplemented producer.
- Unsupported required capability, required-but-not-enabled capability, unsupported handler version, handler ownership mismatch, missing schema and zero domain profiles have explicit outcomes.
- Seed historical user/memory/domain rows and cross-pack edges; assert exact visible IDs in both retrievers, explicit seeds and direct user reads. Verify intended historical export/erasure access separately.
- Legacy snapshot canonical identity, explicit processing-version changes, removal classification, direct registry construction and explicit-empty settings/cache behavior retain their documented contracts.

These local tests establish composition behavior only. #39/#40 conformance and journeys, #41 Spanner evidence, and #43 tenant routing retain their separate completion boundaries.
