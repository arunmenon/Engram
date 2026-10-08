# G01 verification and stakeholder demonstration

Status: NOT RUN. Implementation execution and demonstration have not started. No results below are claimed as passing.

Specification: [G01 PR activity](2026-10-08-goal-01-pr-activity.md). Required standard: [goal verification and demonstration](goal-verification-standard.md).

## Stakeholder outcome

Demonstrate how a GitHub PR message becomes an accepted event in Spanner, how real workers build or update the PDLC Change, and how Engram retrieves that Change with evidence. Demonstrate duplicates, invalid inputs, missing ticket references, repository identity and late delivery as well as normal creation/merge.

## Scenario register

| Scenario | Expected outcome | Actual outcome | Verdict | Evidence |
|---|---|---|---|---|
| PR01 Open | Correct Change and originating-event evidence retrieved | Not run | NOT RUN | Pending |
| PR02 Title update | Same Change; new title; both events retained | Not run | NOT RUN | Pending |
| PR03 Duplicate | No additional logical event/artifact/relationship | Not run | NOT RUN | Pending |
| PR04 Incomplete payload | Clear rejection; no ledger/graph writes | Not run | NOT RUN | Pending |
| PR05 Merge with ticket | Same Change merged; explicit ticket link and evidence | Not run | NOT RUN | Pending |
| PR06 Merge without ticket | Merged Change; no invented ticket link | Not run | NOT RUN | Pending |
| PR07 Same number across repositories | Distinct Changes; no crossed updates/evidence | Not run | NOT RUN | Pending |
| PR08 Older update after merge | Declared ordering policy upheld; no silent state reversal | Not run | NOT RUN | Pending |

## To populate during execution for each scenario

Use the full trace and required fields in the standard: original attributed source fixture, exact normalized event, tenant/authentication/admission decisions, API request/response, authoritative ledger observation, worker processing, graph before/after, retrieval request/response with evidence, and forbidden-effect checks. Include actual identifiers and material values, not just assertions that a step passed. Record failed attempts and reruns.

## Implementation, configuration and review record

Pending: exact mappings and expected graph shape; code changes and reasons; pack/capability versions; target and provider details; source hashes; registered runs; final code fingerprint; review findings and dispositions; safe replay/cleanup commands. No live cloud verification has been performed for this goal.

## Stakeholder walkthrough

## GitHub reconciliation and feature-bucket assessment

Pending; no issue updates or new filings are claimed by this document. Before goal delivery populate:

| Umbrella / sub-issue | Status before → after | Acceptance verified and evidence | Remaining work | Actual GitHub update link |
|---|---|---|---|---|
| Pending scope mapping | Not assessed | Not run | Pending | None |

List new defects/features, existing-issue duplicate checks, actual new issue links and owning umbrellas. Assess whether discoveries fit #34/#41 and their existing sub-issues or require a distinct proposed feature bucket. Explain the decision, dependencies and any proposed scope change. No additional implementation is authorized by that assessment.

## Demonstration delivery

Pending. Walk through all eight scenarios, showing source → adapter → API → ledger → workers → graph → retrieval with evidence where applicable. Explain each result and any absence of writes. Provide a repeatable script, per-scenario results and limitations. Clearly label recorded versus live evidence. Demonstration delivered: NO. Stakeholder sign-off: NOT REQUESTED/NOT GIVEN.
