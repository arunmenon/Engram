# Protected control-schema harness review

2026-10-07. Read-only inspection of scripts/engram_spanner_tenant_control.py and its referenced recovery/schema contracts. No tests/cloud executed.

**Verdict: approve this bounded inspect/prepare harness for the separately authorized reserved target; no blocking destructive-action or recovery defect identified.**

The harness refuses any database basename except `engram-compat-target`; project/instance are taken from the explicit credential configuration and recorded as the full target. The only mutation is the exact additive TenantControl CREATE statement. There is no ownership bootstrap/adoption, application-row write, reset or deletion. Existing tables are fingerprinted in a shared snapshot before work and checked again in finally; existing DDL must remain a subset afterward.

Tracking and durable attempt registration precede SDK calls. The submitted flag is fsynced before the single update RPC, preventing automatic resubmission after response loss. Resume requires the same target, statement and digest and only GETs the recorded operation. Returned name/database/ordered single statement are checked with the strict formatting matcher. No instance listing or automatic replacement ID exists. Pending polling has bounded iterations/RPC timeouts, persists pending state, and exits as a failed run rather than success on exhaustion. Exact operation recovery remains available after uncertain submission, timeout or observation failure.

Success requires control-schema verification, preservation checks and recorded cleanup/source checks; failures return nonzero after tracker completion. SDK cleanup is attempted independently of the preservation check. Redaction excludes the access token from errors, and original application contents are retained only as counts/hashes in exported evidence.

Audit limitations: the allowlist constrains database basename, not a hardcoded project/instance, so the registered full resource must be checked against the authorized target before invocation. The attempt records `done` before inspecting an operation's error; terminal failure is therefore established by the failed observation/error code, not by that state string alone. A resumed pending operation is not successful until terminal success and schema validation occur. Local inspection does not prove actual permissions, DDL execution, row preservation or readiness; it authorizes no additional scope and establishes no tenant ownership or service isolation.

## Recorded CREATE TABLE canonicalization recheck

Read-only inspection approves the narrow trailing-comma reconciliation. `control_statement_matches` removes only the comma immediately before the column-list close followed by PRIMARY KEY, then uses the existing complete-token matcher. Field names/types/nullability/table/primary-key tokens remain subject to equality. Harness validation still requires the exact operation name, database and single statement, while retaining observed metadata in evidence.

The recorded prepare-02 metadata shows the server's trailing column-list comma and done=true. Inspected `20261007-local-control-canonical-01/pytest.txt`: **66 passed**, 1.37 seconds, including the recorded-format and semantic-change cases. **Approve resuming the same recorded operation `engram_control_fc2f04084b0b4829a2a4c475c6dde46c` through exact GET and physical-schema verification; no new submission is needed.** No tests/cloud executed by this reviewer. Terminal error inspection and successful schema verification still determine the resumed run's outcome; prior failed runs are not relabeled successful.

## Bounded real-adapter verification review

2026-10-07. Read-only review of the new verify phase and tenant-control cases. **Changes requested before execution: P2 durable recovery receipt.** No tests/cloud executed.

`verify_fences` retains the exact fixture/group keys and control identity only in in-memory evidence, which the outer harness writes in finally. Bootstrap happens even before fixture evidence is assembled. A hard interruption after bootstrap, freezing or writes can therefore leave persistent ownership/state and application fixtures without a durable record of the exact environment-derived bundle digest, epoch and cleanup keys. Pass a durable checkpoint callback/destination into the helper, persist owner intent plus exact typed fixture/group keys before bootstrap/first write, and checkpoint each operator transition. Keep the actual owner row authoritative during recovery; do not infer an epoch or adopt unrelated data.

The normal-flow assertions otherwise follow the bounded scope: active adapter writes/delivery, admission refusal while draining with processing allowed, frozen zero-effect hashes, controlled delayed stale write refusal after monotonic epoch advance, renewed pending-work recovery and wrong-owner refusal. Cleanup deletes exact typed nodes/edge/event IDs and one owned group under the current verified fence, retains ownership and never decreases epoch. Operator transitions are explicitly harness-only CAS operations; this is not simultaneous contention or a production activation implementation.

A useful assertion refinement is to hash application state immediately around the final wrong-tenant refusal as well: later deletion of the fixture could hide an unintended effect if that operation were to raise after writing. Existing frozen/stale zero-effect checks already use the stronger before/after pattern. Successful cleanup must still be established by the main all-application-table fingerprint; a cleanup callback returning alone is insufficient preservation evidence. Full API/worker-process and two-tenant acceptance remain excluded.

## Verification checkpoint recheck

The durable-recovery P2 is **resolved**. The helper now receives the harness's atomic/fsync JSON writer and persists exact owner identity/digest/epoch, observed prior ownership and deterministic fixture/group keys before bootstrap. Each operator CAS has a durable expected-state/next-state intent followed by observed-current-state persistence. Cleanup intent and completion are likewise checkpointed. The database control row remains authoritative after an interrupted transition.

The final wrong-tenant refusal now compares application fingerprints before cleanup, and positive ledger/graph cases read back their expected values. **Approve the bounded verify harness for separately authorized tracked execution.** No tests/cloud executed by this reviewer. Actual effect-free refusals, successful cleanup and retained active ownership still require run evidence; this is not production activation or concurrent-contention acceptance.

## Seven-path snapshot verification addendum

2026-10-07, read-only pre-cloud review. **P2 assertion correction requested before executing this expanded evidence case.**

At `scripts/engram_spanner_tenant_control_cases.py:166`, the positive `read_paths` branch discards every operation result and unconditionally records success. In particular, subscription `lag()` intentionally returns `None` on an ordinary backend/query failure, so the active/draining permission observation can false-pass without a successful application read. Capture results and assert an integer lag (zero is expected after the two deliveries); also verify the exact fixture row/document on graph point and ledger document reads and meaningful counts for the query paths. Empty dead-letter results are valid for this fixture.

The refusal branch correctly requires `TenantFenceError`, rather than treating arbitrary failures as success. Active external, draining external refusal/processing permission, frozen processing refusal and old-epoch refusal each exercise all seven snapshot paths. Fixture adapters explicitly use processing mode, retaining the intended drain behavior. Existing durable ownership/transition receipts, protected target, exact cleanup and final all-table fingerprint remain unchanged; no new destructive-effect or cleanup defect was found.

This finding concerns truthful positive evidence, not an identified runtime fencing defect. After correcting the positive checks, the bounded tracked fixture may proceed; it cannot establish API final-response authorization, cross-channel activation races, cache hits, pagination or streaming safety. No tests or cloud calls executed by reviewer.

### Positive snapshot oracle recheck

The seven-path positive-evidence P2 is **resolved**. Successful operations now require graph/ledger integer counts of at least two, the exact typed Event row, the exact ledger fixture ID/payload, exact owned delivery positions with count one, an empty dead-letter list, and strictly integer zero lag. Results are persisted before recording each check. Draining processing observations now follow acknowledgement of A and therefore correctly expect only B pending. A degraded `None` lag can no longer pass.

**Approve this bounded expanded fixture for separately authorized tracked cloud execution.** No remaining blocker identified in the correction; no tests/cloud calls executed by reviewer. Existing protected-target, durable recovery, monotonic epoch, exact cleanup and preservation requirements remain in force. This does not establish external API response, cache, cursor or streaming authorization.
