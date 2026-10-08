# G04 verification and stakeholder demonstration

Status: IN PROGRESS, explicitly authorized. No end-to-end pass claimed yet; G05 unstarted. No foundation reruns or historical migration.

Scope and predeclared scenarios: [G04 specification](2026-10-08-goal-04-release-deployment.md). Independent design/implementation/harness review: [Astra review](2026-10-08-astra-g04-review.md). The existing reconciled foundation, auth, receipts, five ordinary workers, actual Spanner storage and artifact retrieval are reused. New work is limited to scoped PDLC deployment identity, failure and explicit release mapping, seed declaration, fixtures and G04 assertions using the existing demo harness. No new service/framework or generic retrieval change.

Target: projects/portiq-mvp/instances/engram-experiment/databases/engram-compat-target. Preflight confirms empty seven application tables, owner epoch40, unchanged core digest. Core1.1+PDLC3.0, memory/user off; private bound tenant compat-control, explicit unevaluated experiment gate, normalized producers. This does not establish public dispatcher or baseline65 compatibility. Monitoring IAM403 recorded separately.

Run evidence, scenario trace, exact expected/actual, graph diagram, repeat commands, cleanup, final Astra evidence review and GitHub reconciliation will be appended from retained execution. No pending deliverable counts as completed.
