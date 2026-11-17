# Event acceptance foundation review

2026-10-07. Astra low, source-only review and recheck via existing composition substrate reviewer. Implementation and evidence remain local and uncommitted.

Scope: `domain/event_acceptance.py`, tenant producer identity/admission context, common normalized HTTP input guard, single/batch/import ingress tests, and changed non-object payload behavior. Persistence, atomic append, worker validation and Spanner compatibility were explicitly outside this review.

## Finding and disposition

P2: `EventAcceptance.envelope_version` initially defaulted missing versions to one, silently accepting an incomplete persisted receipt. Resolved by making the field required, explicitly supplying version one in server stamping, and adding a missing-version rejection regression. Astra source-only recheck approved the bounded foundation. Reviewer ran no tests or cloud calls.

Other inspected foundation semantics: immutable acceptance context, producer identity stable across credential rotation, complete normalized event/payload fingerprinting, separate duplicate and interpretation checks across epoch changes, and raw top-level spoofing/non-object payload rejection. These were approved within scope.

Integration obligation: translate `EventInterpretationError` into the established `RuntimeFencedError` control-refusal path before worker parse-error fallbacks, ACK or DLQ. Its domain ValueError inheritance alone does not provide worker safety.

## Executor evidence

- `runs/20261007-local-acceptance-contract-01`: retained failed first attempt, 11 failed/163 passed.
- `runs/20261007-local-acceptance-contract-02`: 174 passed/50 warnings; selected Ruff passed. Full current-worktree mypy failed with 54 errors across 13 files (152 checked), retained in `mypy.txt`. No errors reported in new `event_acceptance.py`; other unfinished worktree typing remains open.
- `runs/20261007-local-acceptance-contract-03`: after review fix, 175 passed/50 warnings; selected Ruff and scoped `event_acceptance.py` mypy passed. Scoped mypy used `--follow-imports=silent`, so it does not supersede the full-worktree failure.

These are local tests using reference storage/fakes; no Redis/Neo4j runners or cloud calls. No baseline scenario promoted, issue closed, public tenant service enabled or compatibility sign-off claimed.

## Next integration

Add immutable nullable acceptance storage through explicit additive Spanner DDL and handshake. Include receipt cost in transaction budgets. Pass authenticated immutable per-request authority to a fenced append, compare source/digest for database and same-chunk duplicate IDs, preserve original acceptance/position, and expose typed conflicts. Protect original event fields against enrichment mutation. Refuse unstamped imports/bare appends and unknown historical acceptance in bound mode. Validate authoritative receipt before every worker/history/replay interpretation; exact contract across epoch-only advancement remains supported, changed-contract activation needs explicit compatibility/replay policy. Finish real-Spanner verification only after those handoffs are wired.
