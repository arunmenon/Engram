# G01 ingress implementation review

Scope: current diff in `src/context_graph/api/routes/webhooks.py` and `tests/unit/test_webhooks.py`, with targeted reads of tenant admission and Spanner duplicate contracts. Static review only; no cloud execution or implementation changes.

## Blocking findings

1. **P1 — malformed action escapes validation** (`webhooks.py:176`). A correctly signed pull-request body containing `"action": []` or `{}` raises `TypeError` in the new set membership check, before the exception handler at line 185. The endpoint returns 500 rather than rejecting malformed input. Minimal fix: validate action as a string before membership, or move the source-shape guard inside the guarded translation block. Add signed list/object action route tests asserting 422 and zero writes.

2. **P1 — identical signed retries can still conflict** (`webhooks.py:187`, `build_events:126`). Missing/invalid source timestamps fall back to `datetime.now(UTC)` on every request. The tenant writer fingerprints all public Event fields, including `occurred_at` (`domain/event_acceptance.py:152`), and Spanner rejects a changed fingerprint for the same event ID (`adapters/spanner/log.py:449`). A PR with valid required payload fields but missing/invalid `created_at` is thus accepted initially and returns 409 when the identical signed body is replayed. The nondeterministic timestamp fallback predates this diff, but newly routing through bound acceptance makes it observable and prevents the promised signed-body duplicate identity. Minimal fix: reject absent/invalid timestamps for translated deliveries before writing, or provide a deterministic documented timestamp rule. Test duplicate requests with absent/invalid timestamps against a bound writer.

3. **P1 — route policy overrides accepted duplicate authority** (`webhooks.py:193-194`). The new active-registry rejection occurs before the writer can recognize an accepted duplicate. An accepted PR replayed after its pack is removed returns 422, although the writer contract deliberately resolves existing identity before current admission policy (`domain/pack_admission.py` module contract; `adapters/spanner/log.py:440-475`). Minimal fix: let the bound writer resolve event-type admission and duplicates; do not reject an existing candidate on current registry membership in the route. Add a bound accepted-retry test across policy/registry removal. Previously this route silently filtered the event; the new 422 does not establish the required duplicate contract.

## Other checks

- HMAC verification precedes creation of the server-selected `webhook.<source>` principal; tenant ID comes from the bound app. No new header-controlled authority bypass found in this diff.
- GitHub PR translations emit a single event; no new G01 partial-write path found. The general per-event write loop predates this diff and is not atomic for future multi-event translators.
- The test diff only updates the expected trace ID. It does not cover the new malformed-input, tenant authority, rejection/outcome, or signed-retry behavior above.

Verdict: changes required before G01 ingress completion.

## Recheck and demonstration-script review

The three ingress findings above are **resolved by inspection**: action type is checked before set membership; timestamps require a valid explicit timezone; bound writers decide active-type admission after duplicate resolution. New malformed action/timestamp tests are present. No tests or cloud execution performed in this review.

Narrow review of `scripts/engram_goal01_pr_demo.py` found these remaining blockers:

1. **P1 — processing timeout can become a pass** (lines 353-373). Loop exhaustion is not rejected, and the post-loop assertions omit `all(lag == 0 for lag in lags)`. If projection finishes but another consumer never processes the event, pending rows can be empty and the scenario passes. Minimal fix: explicitly require the complete polling condition after the loop, persist per-consumer lags, and fail on timeout.

2. **P1 — response-derived expectations and incomplete storage assertions permit false passes** (lines 351-352, 374-428). Accepted IDs are taken from the response without comparing them to the predetermined normalized IDs. Ledger documents/acceptance are saved but never checked. Graph checks allow arbitrary extra Change/WorkItem nodes and edges among the allowed labels, and do not assert unchanged graph content for PR03/PR04 or absence of cross-repository evidence/ticket links for PR07. Cleanup's global allowlist includes future fixtures and cannot substitute for per-scenario forbidden-write checks. Minimal fix: derive cumulative expected IDs from fixtures, compare response IDs and ledger contents/authority, and compare exact per-step node/edge identities (plus unchanged duplicate/rejected snapshots), including PR01 repo/number and PR07 contamination exclusions.

3. **P1 — retrieval proves only seed presence and nonempty provenance** (lines 458-460). Stale title/status, unrelated provenance, missing merge/creation evidence, or missing APP-42 linkage can all pass. Minimal fix: assert current title/status and exact supporting event IDs for each scenario; explicitly check merge-ticket relationship/evidence for PR05, no-ticket behavior for PR06, isolation for PR07, and ordering-policy state for PR08 in retrieval responses.

4. **P1 — teardown can skip cleanup/restoration** (lines 481-510). A store close failure or HTTP shutdown timeout aborts the finally block before target freeze/cleanup, and an activation failure after freezing OLD leaves the predecessor frozen because restoration only handles epoch OLD+1. Cancellation of `asyncio.to_thread` also does not settle its SDK operation before inspecting local `active_owner`. Minimal fix: nest teardown so cleanup/recovery and evidence persistence still run after component shutdown errors; retain and settle mutation tasks, reconcile only exact intended ownership outcomes, and explicitly restore/recover the frozen-predecessor branch. Fail closed if restoration cannot be completed and record its exact state.

Target safeguards are otherwise appropriately narrow: fixed project/instance/database, exact predecessor CAS, empty-target activation, exclusive local lock, and cleanup refusing keys outside the predeclared manifest. Actual TCP ingress and five consumer `run()` tasks are present. No provider substitution beyond the disclosed token-client bootstrap was found; the unevaluated flag and single-bound-app limitation are disclosed.

Current verdict: ingress fixes accepted by inspection; demonstration script requires the four changes above before its passes can support G01 completion.

## Second script recheck

Polling timeout, response-independent IDs, exact domain node/edge identities, ledger content, duplicate/rejection invariance, and retrieved state/provenance checks now address the principal false-pass findings. Graceful worker settlement, shutdown-error accumulation, and exact-owner recovery substantially address teardown concerns. Static inspection only.

Two narrow gaps remain:

- **P1 — ambiguous initial freeze can escape recovery** (`engram_goal01_pr_demo.py:315-316`, cleanup guard near line 610). `active_owner` is assigned only after `freeze_target` returns. If its transaction commits but the SDK raises while reporting the result, `active_owner` remains None and cleanup skips exact-owner reconciliation, leaving OLD frozen. Minimal fix: persist/set a separate mutation-attempt flag before awaiting freeze, and use it to enter the existing exact-known-owner reconciliation. Do not enable recovery when predecessor/empty-target prechecks failed.
- **P2 — repository/number values lack independent assertions** (domain property checks near lines 477-487). Correct node IDs with wrong stored `repo`/`number` can pass: retrieval only compares these properties with the same stored values, and PR07 merely checks repositories differ. Minimal fix: compare every expected Change's stored repository and number against its source fixture before checking retrieval; this directly closes PR01's correct-identity and PR07's scoped-value requirements.

Once these two small changes are made, no additional safety/false-pass blockers were found in this narrow recheck. This is review of the harness, not evidence that G01 scenarios have run successfully.

## Final pre-checkpoint recheck

Both remaining findings are resolved by inspection: `mutation_attempted` is set before initial freeze and enables exact-known-owner reconciliation; every stored Change's repository/number is checked against source values. The new private `DemoAuthentication` entrypoint verifies the supplied bearer credential through `TenantCatalog.authenticate`, then invokes the actual `TenantResponseGuard`; the principal is not unconditionally injected. Webhook requests still reach the real HMAC handler. This is appropriately limited to the declared localhost single-bound experiment and proves no public dispatcher behavior.

No remaining blocking safety/false-pass findings in this small delta. **PR01 checkpoint execution may proceed within the existing authorized target/scope.** This clearance is static review only; runtime success and cleanup still require recorded execution evidence.

## Issue #45 resolved-seed parser review

Reviewed only the new `resolved_literals` parsing block in `retrieval/artifacts.py` and `tests/unit/test_resolved_artifact_seeds.py`; unrelated existing dirty hunks are outside scope. No blocking finding. Stripping requires a successfully resolved given reference, uses escaped literals with identifier boundaries and longest-first ordering, and changes only local seed-parser text. Tests cover same-repository sibling exclusion, retained legitimate traversal, independent ticket discovery, prefix boundaries, and unresolved-seed fallback. Original query and downstream traversal remain intact.

Static review clearance applies to the targeted G01 rerun; local regression and real-Spanner execution results remain separate evidence. Minor limitation: terminal punctuation included in the identifier boundary class (for example a period immediately after an ID) prevents stripping that occurrence; this does not affect the demonstrated exact-ID query and need not broaden this fix.

## Final G01 evidence review — 20261008-cloud-g01-all-02

**No blocking findings.** Reviewed the current demonstration script, resolved-seed parser/tests (including the corrected terminal-period boundary), and this run's manifest/observations. The script hash and every recorded runtime-source hash match the current files.

The retained evidence supports PR01–PR08 plus both prerequisites through actual TCP webhook ingress, bound Spanner ledger, five running consumer loops, graph observations, and structured artifact retrieval. Every step records five zero lags, no pending/dead-letter rows, and HTTP 200 retrieval; PR04 correctly records ingress 422. Independently checked PR03/PR04 storage invariance against PR02, final eight unique ledger events against expected normalized payloads, and authenticated source identities. PR05/PR08 retrieve the declared APP-42 link; PR06/PR07 retrieve only their intended Change without ticket edges. PR08 remains merged while its title follows the declared delivery-order policy.

Only core 1.1.0 and PDLC 1.8.0 are recorded; observed labels are Event, Change, WorkItem, and OntologyState. Cleanup records removal of eight events, thirteen nodes, fourteen edges, five consumer groups and eighty cursors; all seven tracked application tables are subsequently empty, the intended owner is active at epoch 18, and shutdown errors are empty. No direct graph/ledger fixture insertion or mocked worker/provider path was found.

Clearance is limited to G01's reconstructed public-REST webhook fixtures and explicitly seeded structured retrieval in one private bound app. It establishes neither unrestricted discovery nor public tenant isolation, optional-pack combinations, full compatibility, or LLM behavior. Review used retained local evidence only; no cloud rerun performed.
