# PDLC pack — real Spanner coverage

Baseline: `feature/engram-walkthrough`, `6a30dcfd376d21b2732ffc36b8ed8847abb2a9de`. Updated 2026-10-06. This is verified subcheck coverage, not complete compatibility sign-off.

| Check | Result | Evidence |
| --- | --- | --- |
| Eight signed GitHub/Jira deliveries, projection, artifact API checks and pack extraction | Passed; 11 evaluation questions, mean F1 1.0 | [Cloud fixture](runs/20261006-cloud-pdlc-b790ad36/pdlc-webhook-evaluation.json) |
| Replay/rebuild into the real second Spanner database | Passed; 11 questions, mean F1 1.0 | [Target evaluation](runs/20261006-cloud-pdlc-b790ad36/pdlc-target-evaluation.json) |
| OpenDAL signed ingestion → projection → graph evaluation | 292 deliveries/events; passed declared gate, 17 questions, mean F1 0.9118 ≥ 0.90 | [Graph evaluation](runs/20261006-cloud-pdlc-b790ad36/pdlc-opendal-evaluation.json) |
| Same OpenDAL questions through Engram artifact HTTP API | Passed declared gate; 17 questions, mean F1 0.9118; evaluation-pending cleared | [HTTP responses](runs/20261006-cloud-pdlc-api-64e30b68/pdlc-opendal-http-evaluation.json) |

The small fixture covers ticket/PR relationships, review and test completeness, release contents and deployments; its extraction assertions include inferred artifact evidence. OpenDAL covers releases, reverts and lexical feature/change lookup. OpenDAL has no Jira/review/CI/deployment data.

Fourteen OpenDAL answers were exact. Three returned extra matches: `change-for-gcs-grpc` F1 0.3333, `change-for-gcs-compose` 0.6667, `release-for-gcs-grpc` 0.5. The fixture documents these lexical limitations; passing its mean threshold does not establish perfect retrieval or a Spanner-specific root cause.

Both databases (`engram`, `engram-compat-target`) and their schemas were preserved. All five storage ports used real Spanner, with test-only token bootstrap. These PDLC runs use real API routes/worker loops in one process, not separate-process PDLC deployment proof. Scripted pack extraction avoids paid providers. The successful large subcheck took 473.14 seconds; no performance SLO is claimed.

Preserved retries: first large ingestion stopped at the normal HTTP429 limit; retry respected server delay. First HTTP run lacked the standard projection-CLI ontology reconciliation and correctly stayed gated; the corrected run performs reconciliation before evaluation. A final tracker subprocess SIGTRAP was reconciled from its already-written results, without cloud replay.

Remaining requirements are tracked in [scenarios.csv](scenarios.csv): separate-process PDLC restart/concurrency, negative webhook/payload cases, projection lookup/provenance/race cases, retrieval admission/completeness failures (#6/#7), combined-pack behavior, upgrade/rebuild fault cases and ledger-preserving cutover (#13). Existing passing checks do not close these requirements.

Operational follow-up: [issue #22](https://github.com/arunmenon/Engram/issues/22) records admin stats omitting PDLC node/relationship counts, verified separately on the rebuilt target. It does not invalidate the numerical or HTTP competency results.

## Resumed pack checks

Signed webhook sweep `20261006-cloud-webhook-handlers-53644154` passed46 mapping/ignored cases (GitHub PR/review/check outcome/release/deployment/issue actions, every Jira work-type mapping and supported status transition), plus body-hash redelivery/changed-content behavior and actual projection of all normalized events. Exact count/type/payload receipts are retained. Jira `Closed` is outside the documented closing vocabulary (Done/Won't Do), so it emits updated; the earlier expectation was a harness mistake, retained separately.

`20261006-cloud-pack-policy-85dedd72` passed invalid JSON ACK/no proposal, node cap1, confidence ceiling0.8, untrusted source retention despite model trust claims, invalid unknown-target link refusal and preservation of existing accepted/trusted authoritative properties. `20261006-cloud-live-pack-463a33c4` passed one real configured-model Decision proposal with source-event evidence and pending0; capped256 output tokens, retry0, no provider switch. These are scoped extraction proofs.

`20261006-cloud-pack-cases-143609a6` passed unprefixed latest deployment selection beyond limit2, but confirmed component prefix lookup omission (#8), missing review state-change provenance (#9) and extraction-first evidence loss (#10). PDLC is exercised on real Spanner, with unresolved semantic/dependency defects; it is not signed off.
