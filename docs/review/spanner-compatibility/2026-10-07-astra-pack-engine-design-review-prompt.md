# Astra medium review: forward-compatible pack/engine integration

Review Engram's proposed pack-aware ingestion/projection implementation design against current code, tests and public-source corpus. Central question: if someone authors an unfamiliar compatible ontology pack tomorrow, what guarantees the intended artifacts, evidence and retrieval behavior without engine changes?

Read-only review: no runtime edits, source downloads, cloud/model calls, credential access or service runners. You may write only the requested review report. Do not implement fixes, change issue statuses, or equate source acquisition/local tests with Spanner acceptance.

Read:
- docs/review/2026-10-06-spanner-compatibility-plan.md (especially design steps, full-pack scope, pack-neutral recheck and real-source experiment)
- docs/review/spanner-compatibility/pdlc-event-contract-inventory.csv and .json
- docs/review/spanner-compatibility/pdlc-payload-experiment-matrix.csv
- docs/review/spanner-compatibility/public-payload-corpus/manifest.json and discovery-pass.md; selectively inspect original samples
- docs/review/spanner-compatibility/implementation-waves.csv
- prior Astra bucket review reports as context, not approval of this new design.
Inspect relevant current source/tests to verify claims; cite paths and lines. Distinguish implemented, proposed, unresolved and missing evidence. Do not repeat all historical bugs unless the new design fails to address them.

Review dimensions:
1. Pack independence and capabilities: event ownership versus rule subscribers, unknown/unloaded types, supported DSL, required versus optional unsupported capabilities, pack dependencies, collisions and isolation. Trace an unfamiliar third pack; expose PDLC/CRM hardcoding.
2. Source-to-event contract: explicit adapter/binding responsibility, semantic identifiers/timezones/units, nested/list/null/extra fields, one delivery/multiple events, unsupported actions and unavailable source fields. Raw capture is distinct from accepted normalized events; no automatic interpretation assumptions.
3. Admission and trust: payload schema representation/load checks, source authentication and server metadata, consistent single/batch/import/webhook validation before writes, partial-storage receipts and same-ID retry. Check static mapping validation limits and semantic fixture requirements.
4. Event-to-artifact contract: exact node/relationship identity, properties, status transitions, conditional/fan-out writes, intentional no-op, extraction-only versus deterministic outputs, provenance and shared derived-field ownership. Can declared constraints and actual writes disagree? How is that detected?
5. Worker/completion contract: all five consumers, applicability, dependency order, durable retries and partial writes, missing-reference repair, concurrent workers, retention/DLQ and replay. Distinguish accepted, processed, failed and unknown without adding unnecessary infrastructure.
6. Artifact-to-evidence/retrieval contract: allowed/confirmed/rejected links, exact source evidence, typed/session isolation, incomplete search and negative claims, pagination/budgets/native deadlines. Verify pack questions and exact outputs, not merely counts/aggregate scores.
7. Version/history contract: source binding, payload contract and projection bundle revisions; rolling deployments, legacy schema-less events, pinned interpretation, replay, rebuild, migration/rollback. Determine which contracts are forward-looking and which compatibility promises remain unspecified.
8. Whole-PDLC/corpus/conformance: account for all23 events and seven with no deterministic domain rules. Public REST records, documents, reconstructed webhooks and synthetic examples are distinct; source examples do not prove approval/change transitions. Explicitly assess missing lifecycle sources. Define reusable pack conformance checks across authoring, load, activation, ingress, graph/extraction, retrieval and upgrade; static versus semantic versus runtime/cloud guarantees. Generality requires an unfamiliar pack as well as PDLC/CRM.
9. Spanner acceptance and delivery sequence: actual Engram-to-Spanner journeys for ports involved, crash/restart/replay/retry/order cases, exact artifacts/evidence, bounded runs/cleanup and existing ledger tracking. No Redis/Neo4j runners. Check slice dependencies and critical decisions; distinguish blockers, later work and unnecessary abstraction. Automatic adapter generation is a later reviewed PR experiment, not trusted runtime code generation.

Also assess this review prompt itself: identify missing dimensions or misleading assumptions and include them in the review. Do not silently expand into app-wide audit.

Deliver docs/review/spanner-compatibility/2026-10-07-astra-pack-engine-design-review.md:
- Verdict: ready, ready with conditions, or needs redesign; practical basis and evidence limits.
- Prioritized findings table: ID, severity/blocker, dimension, precise code/document evidence, concrete failure/new-pack example, recommended design change, existing issue if applicable. Recommendations are design-level and proportionate.
- Coverage table for all nine dimensions, unresolved decisions, required acceptance evidence; explicitly distinguish source inspection from tests executed.
- Forward-compatible pack conformance checklist and artifact expectations, including what cannot be guaranteed statically.
- Necessary implementation-slice changes, separating blockers from later improvements.
- Prompt coverage critique and any residual blind spots.
Keep the report focused and actionable. Do not claim complete lifecycle coverage, passing tests or compatibility without evidence. No issue closures.
