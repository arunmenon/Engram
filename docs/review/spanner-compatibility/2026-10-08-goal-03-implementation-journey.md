# G03 — Planning to code, review and verification on real Spanner

Status: VERIFIED in 20261008-cloud-g03-all-01; independent review cleared, publication and GitHub reconciliation complete. Authorized on 2026-10-08. Implement G03 only; G04 requires separate approval. Historical migration is excluded by the shared verification standard.

## Bounded outcome

Recreate a password-reset PRD, expiry Requirement, HLD and LLD through authenticated Engram HTTP. Explicit producer references connect a work ticket to the requirement and design, a PR to that ticket, two recorded reviews to that PR, and both failed and successful test runs to the same test and PR. Retrieve the exact chain and event evidence. Separate unrelated and unlinked examples must remain separate.

Reuse G02's actual API, five ordinary workers, Spanner ports, fenced disposable target and observed cleanup. Source payloads are synthetic normalized producer fixtures, not native source adapters or arbitrary raw interpretation. Real configured design extraction remains enabled and observed. No direct graph setup, mocked Spanner or manual repair counts as acceptance. Public tenant dispatch remains outside this single-bound experiment.

## Missing mappings and minimal proposed changes

The existing pack declares IMPLEMENTS and VERIFIES, but tickets do not map explicit requirements/design references, PR creation does not map explicit work-item references, and test events do not map declared requirement verification. Add optional bounded typed arrays using existing revision/identity conventions. Add the optional reviewer field to Review and its event mapping. Preserve existing contracts when new fields are absent. Pack 2.1 is additive; the event catalog stays25.

Trace retrieval must include REVIEWS, EXECUTES and RAN_AGAINST to expose actual reviews and test outcomes, in addition to existing IMPLEMENTS/VERIFIES/REFINES. Do not change generic traversal unless a reproduced defect requires it. Source assertions about reviewer identity and test outcomes are not independently authenticated human actions or tests executed by Engram.

## Predeclared scenarios

| Scenario | Input/action | Required observable result |
|---|---|---|
| IM01–04 | PRD, expiry requirement, HLD, LLD | Exact planning identities and REFINES links, source-event provenance and retrieval |
| IM05 | Ticket with explicit requirement and LLD references | WorkItem IMPLEMENTS exact Requirement and DesignElement |
| IM06 | PR with explicit ticket reference | Change IMPLEMENTS exact WorkItem; title/head SHA retained |
| IM07 | Changes-requested review by Alex, then approval by Robin | Two Review artifacts with their own reviewer/verdict and REVIEWS; no erasing the first review |
| IM08 | Failure then success for the same test at separate run IDs | Both TestRuns retain outcomes; EXECUTES to same TestCase, RAN_AGAINST correct Change, explicit VERIFIES Requirement |
| IM09 | Separate feature with colliding local requirement/ticket/PR numbers in separate identity scopes | No cross-feature links or leakage in focused trace; all exact stored identities remain separate |
| IM10 | PR without ticket reference; test without verification reference | Their own artifacts exist; no invented IMPLEMENTS/VERIFIES links |
| IM11 | Identical retry and changed-content same-ID retry | Duplicate no writes; conflict409 no writes |
| IM12 | Missing requirement revision, malformed ticket reference, unsupported review verdict or test outcome |422 before ledger append, persistent snapshot unchanged |
| IM13 | Requirement-, LLD-, PR- and TestCase-seeded trace plus text-only discovery | Required nodes/edges and exact event evidence; both review verdicts and both run outcomes remain visible; unrelated artifacts excluded; no truncation accepted |

Exact fixture identities, fields, responses, edges and negative expectations are persisted before cloud execution. Check every edge's direction, both test outcomes and commit SHA. Unlinked means absent explicit mapping, not a manufactured positive chain. Retain every failed run, review findings and corrective rerun.

## Completion and stakeholder demonstration

Final affected local checks plus all G03 real-Spanner scenarios must pass on final code. Record per-input request → auth/admission → ledger → five workers → graph → retrieval, actual live extraction outcomes, configuration/source fingerprints and owned cleanup. Independent review must clear design/code/evidence. Publish the verification document and recorded demonstration, update affected issues without premature broad closure, assess new defects/buckets, push evidence, then stop. Original65 baseline cases are not automatically promoted by these goal extensions. Migration-only cases remain deferred.

## Observed run

The predeclared23input checks and5finalretrieval checks all passed on real Spanner. Exact evidence is in [G03 verification](2026-10-08-goal-03-verification.md). Two real design-extraction calls completed; final cleanup restored core epoch30 and all7application tables empty. No historical migration work.
