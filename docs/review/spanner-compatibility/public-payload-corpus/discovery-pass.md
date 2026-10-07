# Bounded public payload discovery pass — 2026-10-07

Source acquisition/inspection only. No adapter, API, projection, model or Spanner execution; no compatibility statuses changed. Original files and URL/time/byte/hash provenance are in manifest.json. Public REST snapshots are not webhook deliveries.

| Material | Observed source | What it can ground | Remaining limitation |
|---|---|---|---|
| PR reviews | OpenDAL PR reviews: two APPROVED records | review identity/verdict and source mapping | Not captured submitted webhooks; other verdicts pending |
| CI checks |26 OpenDAL check runs with success, skipped, cancelled conclusions | finished/skipped normalization and nullable/provider fields | Failure/error outcomes and webhook wrappers pending;26 checks are not26 test passes |
| Commit | OpenDAL commit detail | commit identity/message/files mapping | No implemented source path is implied |
| Design RFC | OpenDAL object_reader RFC, corrected core/core/src/docs/rfcs path | design text, motivation, requirement content, linked PR/issue | RFC document alone does not prove an approval or revision event |
| Requirements tracking | OpenDAL issue7107, Cache Layer RFC tracking | structured issue plus requirements/implementation context | Ticket record is not automatically requirement.changed or request.created |
| Architecture decision | npryce/adr-tools accepted ADR0001 | decision statement/status/date example | Document-to-event adapter and timestamp policy pending |
| Deployments | Two github/docs deployment records and one failure status | deployment IDs, environment, status shape; negative/no-op case | Failure must not emit successful service.deployed; success/rollback/upgrade evidence pending |

Earlier issue/PR/release captures and292 git-derived reconstructed deliveries remain reusable. These sources span multiple repositories; they are separate examples, not one linked project's lifecycle. Do not join their identities or fabricate cross-source provenance.

Still missing: genuine incident/postmortem material, explicit request/approval and requirement-change transitions, design revisions, positive deployment, rollback and upgrade sources, plus source mappings/contracts/wrappers and all execution. A proposed GitHub incident-reports repo returned404; OpenDAL recursive tree exceeded the750KB bound. Both attempts remain recorded, as does the earlier wrong RFC directory. The corrected RFC document capture succeeded. Do not label empty API responses as coverage.

Next: classify each of23 declared PDLC events against acquired source material; retain partial acquisition status until its semantic fixture/oracle exists. Reconstruct only documented webhook fields/actions, label wrappers synthetic, and sign only with fixture secrets. Use exact adapter-to-contract and graph/evidence expectations, then tracked Engram→Spanner runs. Hashes verified after capture; no test pass is claimed.
