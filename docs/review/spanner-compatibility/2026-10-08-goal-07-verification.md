# G07 verification and stakeholder walkthrough

Status: LOCAL IMPLEMENTATION REVIEWED; CLOUD NOT RUN. A–D runtime changes
and the local 28-event catalog are integrated on feature/engram-g07-event-coverage.
Astra medium preimplementation review is recorded; final runtime and harness reviews cleared the scoped findings.
Cloud acceptance and stakeholder sign-off remain pending. G08 has not started.

[Specification and proposed slices](2026-10-08-goal-07-event-coverage.md) ·
[28-event baseline matrix](2026-10-08-g07-event-coverage.csv) ·
[Required verification standard](goal-verification-standard.md)

## What the demonstration will explain

Can Engram turn each declared PDLC event into its promised observable result,
including requests, decisions, ticket transitions, commits, skipped tests,
rollbacks and upgrades, and retrieve that result with evidence on real Spanner?
Event coverage does not prove every schema relationship or every lifecycle state.

## Verification register

Each individual subcase must get its own actual results/evidence row when fixtures
are frozen. The ranges below are planning groups, not completed tests or a fixed
cloud check count. Expand generated validation/retry/conflict cases before running.

| Cases | Expected stakeholder-visible result | Actual | Verdict |
|---|---|---|---|
| A01–A02 | Exact Request and approved Spec→Request trace, independent source scopes | Not run | NOT RUN |
| A03–A04 | Explicit scoped decisions and revision/supersession evidence | Not run | NOT RUN |
| A05 | Minimal valid request is retrievable; malformed identity cannot write | Not run | NOT RUN |
| B01–B02 | Ticket progress, parent link, independent done/cancelled outcomes | Not run | NOT RUN |
| B03 | Abandon/reopen works; late abandonment does not undo merge | Not run | NOT RUN |
| B04 | Commit with PR reference creates scoped Change and declared ticket link | Not run | NOT RUN |
| B05–B06 | No-PR commit is explicit ledger-only; reviewer text is not invented authenticated approval | Not run | NOT RUN |
| C01–C02 | Normalized and GitHub skipped/neutral cases create skipped TestRuns with evidence | Not run | NOT RUN |
| C03–C04 | Optional links stay absent, invalid outcomes reject, separate finished outcomes remain honest | Not run | NOT RUN |
| D01–D03 | Rollback names exact attempt, preserves history and changes no colliding deployment | Not run | NOT RUN |
| D04 | Unknown target is visibly reference-only, later fill retains rollback evidence/state | Not run | NOT RUN |
| D05–D06 | Upgrade is a distinct successful deployment assertion; malformed rollback targets cannot write | Not run | NOT RUN |
| E: final catalog | Every final declared event has positive full-path evidence on the frozen pack | Not run | NOT RUN |
| E: admission | Per-event retries/conflicts and required-field/nested validation match unchanged table fingerprints | Not run | NOT RUN |
| E: retrieval | Exact artifacts/edges/provenance, forward/reverse and natural-language questions, unrelated controls | Not run | NOT RUN |
| E: safety | G05/G06 unchanged, ownership fences held, ordinary workers stopped cleanly | Not run | NOT RUN |

## Evidence required for each scenario

Record the raw source or labeled normalized fixture and hash; adapter output where
applicable; exact authenticated API request/response; tenant/binding/database/epoch
and bundle; accepted ledger event and authoritative source identity; worker outcomes,
lag, pending/dead letters and applicable extraction; graph before/after typed IDs,
properties, edges and source-event provenance; original retrieval question and exact
expected/actual answer; forbidden effects; relevant logs and failed attempts.

Use normal Engram read/write flows. Read-only Spanner snapshots verify storage;
they do not replace the retrieval API. Rejections, conflicts and duplicates require
unchanged full-table fingerprints. No direct artifact setup or manual repair counts.
Unknown-ID queries follow the actual discovery API contract; candidate absence is
separate from requiring an entire discovery response to be empty.

## Reproduction and retention

Execution commit, final pack/bundle/hash, fixture hash, provider configuration,
exact command, target ownership/epoch and run IDs: **not yet assigned**.
Separate target: `engram-g07-target`. Read-only preflight returned `PermissionDenied`;
no database creation, DDL, fixture ingestion or cloud acceptance has occurred.
Do not reuse or alter retained G05 `engram-compat-target` or G06 `engram-g06-target`.
Successful G07 data will be retained pending explicit cleanup approval. Failed runs
must preserve evidence and clean only their own registered disposable keys.
No token or credential belongs in this record or git.

## Stakeholder demonstration order

1. Show the request entering Engram and its exact connection to an approved Spec.
2. Show the decision, its explicit scope and later replacement with evidence.
3. Show ticket progression, PR abandonment/reopening and a commit-derived ticket link.
4. Show a skipped test beside a failed and successful run, without conflating outcomes.
5. Show the exact rolled-back deployment and the separate upgrade; explain reference-only targets.
6. Show the final complete catalog and selected exact retrieval answers, including unrelated controls.
7. Show the actual issue reconciliation, independent review and retained-data receipt; stop before G08.

This is a planned walkthrough, not a delivered recorded or live demo.

## GitHub reconciliation and feature-bucket assessment

Preparation owner: #39 under #34; journey scope #40, projection semantics #36,
admission #37 and cloud verification #41. No issue is closed by preparation.
Slices A–E are published as #54–#58. #54–#57 are under #40; #58 is under #39
and natively blocked by all four implementation issues. All remain open. At delivery include actual before/after states,
comment URLs, satisfied/remaining acceptance, new defects and scope changes.

No separate feature bucket is proposed now: declared PDLC-event completion fits
#39/#40 under #34. Any larger commit identity, native adapter, live deployment-state
or inference feature discovered later is assessed explicitly, not silently included.

Independent review, implementation delta, cloud run receipts, failed-attempt
corrections, issue completion and stakeholder sign-off: **pending, not claimed**.

Preparation tracking: [actual #39 update](https://github.com/arunmenon/Engram/issues/39#issuecomment-6064974375). This is a preparation comment, not completed-goal reconciliation.

## Local checkpoint (not cloud acceptance)

- Integration d75e4ec: PDLC 5.0.0; runtime/research copies identical; 28 declared events, all with deterministic mappings.
- 151 catalog and G07 unit checks passed; 27 affected ontology checks passed. These verify contracts/plans/public retrieval seams, not real-Spanner execution.
- Request mapping and seed, strict skipped TestRun projection, no-PR commit guard, and exact rollback action/upgraded deployment declarations integrated.
- Cloud fixture/oracle and runner reconciliation and final independent review are complete. The full tracked Spanner write-to-read run remains outstanding.
- G05/G06 have not been written or cleaned by this goal. No G07 issue is closed.

- Astra scoped runtime review found a UTC-overflow admission defect. Fixed in d379637 with observational date-time validation; 167 focused contract/deployment/catalog checks passed. Astra rechecked the correction: P2 resolved, no further runtime blockers, 233 scoped local checks passed. Harness/cloud proof remains outside that review.
- Matrix preserves the original 4.2.0 baseline columns and now identifies the 5.0.0 G07 target separately; every cloud status remains NOT RUN.
- Slice issue progress comments are preserved in the ticket receipt file. Updates are evidence checkpoints, not closure.

## Final local gate — ready to execute after database access

Runtime commit: `c8eb4f5`. PDLC **5.0.0**, same **28** event types. All mapped
positive paths have independently authored fixture expectations. No cloud case is
promoted from earlier goals or from these local checks.

The combined plan has **623 HTTP steps and 15 retrieval checks (638 planned checks)**:
99 expected HTTP201 cases (including unchanged retries), 30 HTTP409 conflicts,
490 HTTP422 rejection cases, and four signed webhook HTTP202 posts (two deliveries
plus their unchanged replays). Nested probes cover all 38 required child fields;
15 valid populated parents are retained in the fixture audit. No nested branch is
silently unpopulated. These are **planned counts, not passed cloud counts**.

Local selected tests: **234 passed**. Astra's final recheck: **57 targeted tests
passed**, zero authored-observation mismatches and zero unregistered artifacts.
[Runtimes recheck](2026-10-08-astra-g07-runtime-recheck.md),
[initial harness findings](2026-10-08-g07-spec-review.md),
[resolved harness findings](2026-10-08-g07-spec-recheck.md), and
[standards review](2026-10-08-g07-standards-review.md) preserve the review trail.
The two P3 standards heuristics are deferred: existing repeated goal-membership
checks and small CLI-validation duplication do not block correctness, and a wider
runner refactor is outside this bounded functional goal. No documented-standard
violation was found. Literal fixture independence is retained deliberately.

The ledger-only commit now has a public `/v1/query/subgraph` Event read. It checks
the available event envelope and provenance; that API does not expose raw payload
or payload_ref. Exact payload verification remains a separate ledger observation.
No new Event API or full-content retrieval claim is introduced.

### Commands after access is available

Refresh the existing private token file using the token script; never commit it.
Use a fresh run ID for each preparation or execution and retain every failure.

```sh
PYTHONPATH=src:scripts .venv/bin/python scripts/engram_goal07_prepare.py --credentials /private/tmp/engram-spanner-token-env --run-id <fresh-preparation-id>
PYTHONPATH=src:scripts .venv/bin/python scripts/engram_goal07_event_demo.py --credentials /private/tmp/engram-spanner-token-env --run-id <fresh-execution-id> --expected-epoch <prepared-owner-epoch> --expected-digest <prepared-owner-digest>
```

Read the successful preparation receipt for the exact owner epoch and digest;
do not guess or adopt observed state after a failed/unknown operation. Both commands
read-only guard G05 and G06 before and after. G07 successful data is retained.

Current external blocker: read-only `get_database` returned `PermissionDenied` for
`engram-g07-target`. Ensure that database exists and the configured experiment
service account has its required database permissions. No G07 DDL or data write has
been attempted. All #54–#58 remain open; #34/#41 compatibility sign-off is unchanged.
G08, the composition assessment and the developer pilot have not started.

Final GitHub progress reconciliation: [actual comment receipts](2026-10-08-g07-final-github-reconciliation.json) for #54–#58 and affected #34/#36/#37/#39/#40/#41. All remain open.
