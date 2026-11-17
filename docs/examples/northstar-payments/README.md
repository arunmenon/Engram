# Northstar Payments operator exercise

This is synthetic customer material for the local ontology workbench. No real customer information or credentials are included. The goal is to author a pack with the real configured model and test it through the UI before approving an artifact for handoff. This does not activate a runtime.

## The customer problem

Northstar operates checkout in US and EU accounts. Both accounts can have incident INC-1042. The graph must keep these incidents separate, link each to the correct checkout service, and preserve the original title when a resolution event omits it.

## Prepared inputs

1. `01-domain-spec.md`: business purpose, vocabulary, account-scoped identity, allowed lifecycle, missing-field behavior, event handling and expected question answers.
2. `02-event-contracts.json`: three event contracts, required payload fields and explicit processed versus ledger-only behavior.
3. `03-sample-events.json`: six chronological events. Three incidents open; one resolves; one comment is ledger-only; one malformed incident lacks its account and must be rejected.

## Walkthrough

Open http://127.0.0.1:5174/workbench.html and select **Northstar Payments — incident pilot**, environment **sandbox-training**.

1. **Customer setup.** Describe scope and exclusions. Confirm provider permission and sensitive-data review before generation; optional roots are under Advanced.
2. **Customer evidence.** Preview each file, confirm its category, then **Add and save source**. Specifications, schemas and sample events have distinct categories. Correct a saved category directly in the inventory; no re-upload is needed.
3. **Proposed model.** Request a proposal, inspect Incident → AFFECTS → Service, account-scoped identity, lifecycle and limitations. Resolve consequential questions. Supporting evidence contains citations and individual rejection controls. Technical inspection contains contracts, projection rules and planned deltas. Accept the model for testing after review; this does not approve deployment.
4. **Expected results.** Write the questions below and select incidents by readable labels. Starting entities and retrieval settings are optional details. Select required graph entities and sample producer trust, then review the expectations. Changing test expectations requires a new test, not another model generation.
5. **Test the model.** Run the isolated sandbox. Compare expected and retrieved answers, inspect event snapshots and rejected events. Discuss a failure with the assistant without changing the expected answers just to pass.
6. **Review and handoff.** Approval remains disabled until evidence passes. Approval pins the exact artifact; it does not activate a runtime. Revision history and technical fingerprints are expandable.

## Fixed evaluation cases

| Field | US case | EU case |
| --- | --- | --- |
| Question | Which incidents affect US checkout? | Which incidents affect EU checkout? |
| Intent | incidents_for_service | incidents_for_service |
| Seed node IDs | Service:us\|checkout | Service:eu\|checkout |
| Answer node type | Incident | Incident |
| Expected node IDs | Incident:us\|INC-1042, Incident:us\|INC-1043 | Incident:eu\|INC-1042 |

Required mean F1: **1.0** for these exact synthetic cases. IDs use the composite-key order specified in the source; inspect the generated model to confirm it follows this contract before running.

Required graph nodes: Incident:us|INC-1042, Incident:us|INC-1043, Incident:eu|INC-1042, Service:us|checkout, Service:eu|checkout.
Forbidden graph node: Incident:us|INC-BAD.
Producer IDs and trusted producer IDs: **northstar-monitor**. This simulated trust setting is not a production credential.

Manual graph checks supplement F1: US INC-1042 is resolved and retains “Payment authorization timeouts”; EU INC-1042 remains open; US INC-1043 remains open; the comment creates no domain node; the malformed event is rejected. A perfect question score alone would not establish these lifecycle properties.

## What to learn

- A specification explains meaning; a schema defines the interface; samples provide concrete cases. None replaces the others.
- Sample uniqueness does not prove global identity. Repeated numbers across accounts make the composite-key decision visible.
- Planned writes, observed stored results and approved artifacts are distinct stages.
- A generated pack is a proposal. Citations, decisions, engine validation and scenario evidence justify accepting it.

## Current execution status

Sources were uploaded manually and reclassified in the UI. The real configured model generated the first pack. Two explicit operator decisions clarified built-in provenance and Service.name; a revision was requested through the author panel. The revised pack passed engine validation and ran through the real memory ledger/projection/retrieval sandbox. Final mean F1 was **0.65** against required **1.0**, so approval remained disabled (original revision 35; reproduced at revision 49 after the UX redesign). Expected answers were not changed.

The US case retrieved three incidents instead of two (F1 0.8); the EU case retrieved three instead of one (F1 0.5). Source tracing found that `ArtifactRetriever._seeds` combines explicit seeds with text-derived seeds: checkout matches both accounts. A selected starting service is not an account filter. Both accounts belong to this same synthetic tenant; this is a retrieval-scoping failure, not evidence of cross-tenant data access.

Observed graph checks passed: three distinct incidents, two services, correct account-specific edges, US INC-1042 resolved with title preserved, other incidents remained open, comment left domain state unchanged, malformed opening rejected.

Evidence: `output/workbench/northstar/exercise-record.json` and `sandbox-result.jpg`. Real-model generation and revision were both triggered through the UI. The exercise is complete as a failing acceptance test; the pack is not approved. A strict-scope retrieval design or an explicit supported scope filter is needed before these questions can pass. Do not rewrite the questions or expected answers merely to obtain a green result.

Observed limitation to review: the proposed projection creates one AFFECTS link per opened event but does not enforce one-service cardinality if a later opened event changes the service. The synthetic fixture does not exercise that change. This limits the pilot; it is not a production readiness claim.

The redesigned real-agent run returned eight grouped evidence statements and explicitly identified the retrieval limitation instead of inventing a pack-level fix. Browser checks confirmed reviewed-answer edits preserve model acceptance, source category corrections persist immediately, and failed evaluation blocks handoff. Screenshots: `output/workbench/northstar/revised-model-review.jpg` and `revised-test-result.jpg`.

## Spanner UI rerun — 2026-11-03

Restored the archived incident-pilot artifact as a separate draft (`2d0d471f-5c61-4163-9849-85f6ab9d1245`), preserving the source pack and reviewed questions. The older, broader Northstar checkout draft remains untouched. Revalidated and invoked the sandbox through the workbench UI on `engram-sandbox-01` (epoch 7).

The run completed with verified cleanup. All required graph nodes exist, no forbidden node or dead letters were observed, US INC-1042 resolved while retaining its original title, and the two other incidents remained open. The malformed sixth event was rejected as payload_invalid. Retrieval reproduced the known mean F1 0.65 failure against 1.0: both questions returned all three incidents rather than the account-specific expected set. This is within-tenant retrieval scoping, not cross-tenant storage leakage. Approval remains blocked; pack and expected answers were not changed to pass.

Persisted evidence: `output/workbench/spanner/northstar-ui-result.json`, `northstar-ui-result.png`, and restoration identity in `northstar-draft.json`. This establishes the real UI → API → Spanner example path for this pack, not production activation or comprehensive procurement/payment-domain coverage.

## Explicit starting selections — 2026-11-03

The artifact retriever now supports `seed_mode: explicit` alongside the unchanged `discover` default. Through the UI, both incident-pilot questions were changed to **Only start from the entities I selected**, their review acknowledgments cleared, and their unchanged expected answers were re-reviewed. The unchanged pack was validated and the examples ran on the dedicated Spanner sandbox. Both questions returned exactly their expected incidents: mean F1 **1.0**, with verified cleanup. The draft remains unapproved and unactivated.

The prior 0.65 result remains valid evidence for discovery mode; it was not overwritten. The new record and screenshot are `output/workbench/seed-mode/northstar-ui-result.json` and `northstar-ui-passed.png`. A regression fixture preserves the original synthetic content and pack at `tests/fixtures/workbench/northstar-seed-mode.json`.

Explicit mode selects graph origins; it is not an account-isolation boundary. Traversal through shared neighbors can still cross account attributes, and the pilot's earlier cardinality limitation remains. Implementation scope, error behavior and the reviewer prompt are recorded in `docs/review/2026-11-03-seed-mode-implementation.md`.
