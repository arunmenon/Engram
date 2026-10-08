# Issue tracker: GitHub

Repository: arunmenon/Engram (https://github.com/arunmenon/Engram). Use the authenticated gh CLI with explicit --repo arunmenon/Engram. Specs, feature umbrellas, sub-issues and defects live here; do not create a parallel local ticket tracker.

## Operations

- Read: gh issue view NUMBER --repo arunmenon/Engram --json number,title,body,labels,comments
- List: gh issue list --repo arunmenon/Engram --state open --json number,title,labels
- Create/edit/comment with body files for multiline prose; use existing labels. Bug fixes use bug; features/design experiments use enhancement. No triage skill or new triage labels are configured.
- Native sub-issues: read the child's numeric database id with gh api repos/arunmenon/Engram/issues/NUMBER; POST repos/arunmenon/Engram/issues/PARENT/sub_issues with sub_issue_id=ID.
- Dependencies: use native blocked_by relationships where supported, otherwise explicit Blocked by: #N text. Resolve the execution frontier from tickets landed on the integration branch, not only GitHub open/closed state.
- PRs as a request surface: no. PRs are not required to close work; do not merge into main automatically.

## Engram approval and verification rules

User instructions override skill defaults. Each implement-spec invocation covers only an explicitly approved goal and its named tickets. #34 or #41 alone does not authorize executing their entire backlog. Never advance to the next goal without explicit user approval.

Keep current completed work and existing issue links. Do not recreate tickets already tracked. Independent approved tickets may use separate worktrees; serialize overlapping files. Never let parallel agents share or mutate the reserved cloud database concurrently. Worktrees need explicit credential and fixture access; missing or skipped prerequisites are blocked, not passing.

Real acceptance follows Engram adapter/normalization → HTTP admission → real Spanner ledger → ordinary workers → Spanner graph → retrieval API with evidence. Local tests supplement acceptance. No direct artifact inserts, manual repairs or mocks count as cloud success. Historical migration and Redis/Neo4j runners are out of current goal scope.

Before closing a ticket, check its whole acceptance scope, independent review and applicable real-Spanner evidence. Partial goal coverage means an evidence update with remaining work; leave the issue open. A local implementation or merge alone is not completion. Do not close umbrellas from one journey's success.

End every goal with its verification document, stakeholder walkthrough, issue reconciliation and assessment of newly discovered gaps. Retain failed runs and exact predeclared expectations. A successful retained demo dataset needs explicit user approval before deletion or reuse. Consult docs/review/spanner-compatibility/goal-verification-standard.md and the current small-goal inventory.
