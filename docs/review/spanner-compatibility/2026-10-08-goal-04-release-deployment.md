# G04 — Changes, releases and deployment outcomes

Status: AUTHORIZED, implementation in progress. G04 only; stop before G05. No separate foundation track or G01–G03 reruns. Historical migration excluded.

## Outcome and bounded changes

A password-reset change ships in release v1.0.0, fails deployment to production, then succeeds on a distinct attempt; staging and an unrelated repo remain distinct. Engram must retain both attempts, explicit release/change/component links and the supporting events, and answer what shipped, where and with which outcome.

Reuse the reconciled foundation and shared experiment support. Actual authenticated HTTP → Spanner ledger → five ordinary workers → graph → artifact retrieval; normalized producer fixtures (no native deployment adapter claim). Read-only SQL verifies storage, never sets up artifacts. Exact owned cleanup, empty reserved target and pinned ownership required. Private bound tenant, core mandatory + PDLC; memory/user off; serve_unevaluated explicitly enabled, not a whole-pack or public-dispatch proof.

Before G04 the pack always treats service.deployed as succeeded, lacks failure projection and does not map a deployment to an explicit Release. Minimal PDLC 3.0 update (fresh dataset, no migration): scope Deployment identity by repo + service + environment + artifact_id + occurred_at to prevent cross-repo/service collisions; new service.deployment_failed event with the scoped identity contract; existing service.deployed remains success; optional release_version links DEPLOYS to Release in the event's repo; include Deployment as a retrieval seed. No invented mapping from arbitrary artifact SHA to release version. Distinct attempts use repo + service + environment + artifact_id + occurred_at; resending same ID/body is duplicate. Reject malformed references/outcomes before save. Release INCLUDES sections must be valid declared enum values. No new engine framework.

## Predeclared scenarios

Exact identities/fields/evidence expectations are in scripts/engram_goal04_fixtures.py, persisted before running.

| Scenario | Input | Required effect / forbidden effect |
|---|---|---|
| RD01–02 | Create and merge PR7 | One merged Change, source evidence; no Release or Deployment implied |
| RD03 | Publish v1.0.0 explicitly including PR7 | Release INCLUDES exact Change, section=fixed; no deployment implied |
| RD04 | Failed production deployment naming release and change | Deployment status failed; DEPLOYS Release and Change, DEPLOYED_TO Component; no success assertion |
| RD05 | Later successful attempt, same artifact/environment | Separate succeeded Deployment; failed attempt unchanged and still retrievable |
| RD06 | Successful staging deployment | Separate environment identity and edge; production attempts unchanged |
| RD07 | Identical retry / conflicting same-ID body | Duplicate201 / conflict409; full persistent snapshot unchanged |
| RD08 | Release before PR; deployment before release | Explicit identity-only placeholders visible, filled when real events arrive; declared edges preserved |
| RD09 | Release with no entries; deployment with no declared release/change and unknown SHA | Own artifacts only; no invented INCLUDES/DEPLOYS |
| RD10 | Other repo reusing PR7/version/artifact, other service | Exact scoped artifacts/links; focused retrieval excludes unrelated nodes |
| RD11 | Missing environment, invalid release reference type, malformed release entry/section, bogus deployment event type |422 before ledger; no persistent writes |
| RD12 | Release-, Change-, Deployment- and Component-seeded trace queries | Exact main shipped chain and both outcomes with provenance; no truncation; no unrelated repo/staging expansion when starting a production attempt unless explicitly required |

All inputs, graph nodes/edges/properties, ledger authority and DERIVED_FROM event links are checked after each request. Every scenario performs ordinary HTTP retrieval, including absence after rejected input. Final retrieval oracles fixed before execution; text discovery is not a substitute for exact traversal. Timeouts, incomplete workers, DLQ, missing evidence or manual repairs fail. Retain failed runs with reasons; expectation corrections require explicit recorded justification, not tailoring to pass.

## Completion

Targeted local contract/projection/retrieval tests, independent Astra design/implementation/harness review, full final-code cloud run, independent evidence review. Verification document includes step-by-step scenario traces, expected/actual, exact source hashes/archive, commands, graph explanation, recorded stakeholder demo and issue reconciliation (#34/#36/#37/#39/#40/#41 and new defects if found). Update only acceptance actually proved; assess new buckets. Commit/push records, report technical result and recorded walkthrough, then stop before G05. No broad issue closure or sign-off inferred.

## Astra design dispositions

Deployment identity now includes repo and service; fixtures deliberately collide all remaining fields. Changing identity warrants pack3.0, not a minor bump. Incident lookup remains outside G04, and incident isolation is not claimed. Deployment outcome comes from the event type; arbitrary extra payload fields are preserved and are not promised as rejected outcome overrides. An independent new attempt with the same repo/service/environment/artifact/timestamp remains indistinguishable under this timestamp-based contract; producers must provide distinct attempt timestamps. Broader native attempt-ID support is not inferred.

Retrieval sets are seed-specific: a single production attempt returns itself, Change, Release and Component, not sibling attempts. Release/Change queries may include staging and another service when connected by the same declared/commit link. A Component query can include a deployment from another repo if the producer explicitly uses the identical catalog service ID; this is a real shared identity, not tenant separation. Separate tenants are not part of G04. Exact sets live in fixtures. Graph storage must retain all DERIVED_FROM; API provenance is the latest source event only. Reference placeholders have no provenance until their own source arrives.
