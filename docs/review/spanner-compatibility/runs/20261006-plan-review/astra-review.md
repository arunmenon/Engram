# Astra independent review

Reviewer: gpt-6-astra, low effort. User-requested single independent pass, read-only code review. No cloud tests or edits by reviewer.

Disposition: accept coverage structure after corrections; execution readiness remains conditional on companion inventory and fixtures.

1. P1: Bound destructive admin replay independently of request timeout. api/routes/admin.py:329–355 and adapters/spanner/log.py:638 use inclusive occurrence-time pagination; >=100 tied timestamps may repeat a full page. Require process deadline/no-progress detection and assert pack/ontology recovery. Accepted; plan guards and LIFE-04 amended. Underlying failure remains suspected until reproduced.
2. P2: Subscription lag means unread work (ports/subscription.py:97; adapters/spanner/subscription.py:328), not pending deliveries. Accepted; SUB-01 and plan corrected with separate pending/ACK/DLQ assertions.
3. P2: Execute ownership checks before every destructive case and forbid legacy force rebuild against shared database (scripts/spanner_probes.py:565). Accepted; explicit guard requirements added. Executable full-flow guards remain a prerequisite, not verified.
4. P2: Inherited GraphOperations flows require traceability. Accepted; AST inventory covers public port contracts and routes, mapped to concrete scenario IDs. Results remain unexecuted; mapping alone is not full coverage certification.

Reviewer also confirmed all five worker composition roots, imports, user extraction/supersession/shared-resource deletion, feedback partial progress, archive state, ANN/native GQL and ontology CLI. Stateless simulation is explicitly outside direct storage scope.
