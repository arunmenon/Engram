# #86 — customer deployment implementation checkpoint

Date: 2026-10-17. Canonical branch: `feature/engram-memory-episodes`.

**Implemented and independently reviewed locally; customer deployment acceptance
is pending.** No non-Portiq target/credential method has been supplied. No cloud
resources were created, initialized, reset or modified in this slice. #86 stays open.

## What changed and why

The runtime already selected Spanner through settings, but the practical setup
scripts depended on Portiq experiments. A customer operator now has packaged
`context_graph.deployment` commands to prepare private pinned settings, inspect
safe metadata, emit schema, initialize exact database ownership, inspect delivery
state and launch the existing tenant API/five workers. The experiment guards stay
unchanged. No new storage tables beyond the existing schema, service, queue,
provisioning API or migration framework was introduced.

[Operator instructions](../deployment/customer-spanner.md) and
[example manifest](../deployment/customer-spanner.example.json) state prerequisites,
permissions, APIs, supported boundaries and repeat commands.

## Verification performed

| Check | Actual result | Meaning / limit |
|---|---|---|
| New deployment/verifier regressions | 42 passed | Configuration, delegation and failure oracles using local doubles |
| Existing tenant/catalog/dispatch/control/schema suites | 112 passed | Affected ownership and schema contracts remain passing locally |
| Ruff | Passed | Four new Python files |
| Mypy | Passed | Both packaged modules |
| Example `prepare`, `inspect`, `schema` | Executed successfully | No cloud calls; private artifact created and DDL printed, not applied |
| Private snapshot Git exclusion | Confirmed | Named `*.engram-resolved.json`; other secret filenames still need operator care |
| Astra low review and correction recheck | No remaining local checkpoint blocker | Not a customer deployment sign-off |
| Authorized non-Portiq HTTP → workers → Spanner → HTTP | **Not run** | Required before #86 closes |

Evidence: [local test log](../review/spanner-compatibility/runs/issue86-local-1017/pytest.txt),
[Ruff](../review/spanner-compatibility/runs/issue86-local-1017/ruff.txt),
[Mypy](../review/spanner-compatibility/runs/issue86-local-1017/mypy.txt),
[safe example inspection](../review/spanner-compatibility/runs/issue86-local-1017/example-inspect.json).
The private resolved artifact and generated DDL stayed outside Git. The placeholder
inspection describes a locally prepared example, not an existing customer resource.
A fresh dependency installation was not exercised in this checkpoint.

The tests prove ADC client selection uses the customer project/instance/database,
all five storage ports share its handle/fence, and API/worker startup rejects a
wrong owner and closes handles. They check source/settings drift, invalid schema
settings, duplicate mappings/groups, missing credentials, permissions, private
file handling and secret-safe failures. The smoke-runner regressions reject wrong
source, missing enrichment, receipt/replay/conflict/tenant-refusal failures,
missing storage readiness and a mismatched stored ledger position.

## Astra corrections

1. Consumer groups must be five distinct nonempty names. Otherwise workers could
   compete within one group and the verifier's dictionary could collapse checks.
2. Importance alone does not prove enrichment: projection copies the hint. The
   verifier now requires the known observation/input keywords written by enrichment.
3. Public provenance and replay must also match the inspected ledger position in
   the configured database, not merely agree with each other.

All three corrections have targeted regressions; Astra rechecked them and accepted
publication of this local implementation checkpoint.

## Repeat and demonstrate the outstanding gate

Use the operator guide on an authorized non-Portiq target. Show the resolved
inspection and exact confirmed resource, then launch the ordinary API and workers.
Run `python -m context_graph.deployment_verify` with that config, service origin,
tenant, full resource confirmation and a fresh private evidence filename.

The runner submits a fresh event over HTTP, retrieves its typed Event with exact
Spanner evidence and enrichment, corroborates the accepted ledger input/position,
checks five registered delivery groups with zero lag/pending/dead letters, tests
replay/conflict/wrong-tenant refusal and retains actual outputs or failure. It
makes no direct artifact inserts/repairs and deletes no test data. This is a Core
smoke proof; optional pack/model quality, ANN load and concurrent two-tenant access
need their own journeys. Keep the database and failed attempts for review.

Then provide the stakeholder walkthrough, independent evidence review and issue
reconciliation. Until that run exists, report #86 as implemented locally with an
external verification prerequisite, never as completed or PayPal-ready.

## Issue reconciliation

- #86: implementation/local evidence checkpoint; remains open for live proof.
- #34: owning pack-platform umbrella; progress evidence only, no umbrella closure.
- #41/#43/#63: related compatibility, tenant and handoff scope; this checkpoint does
  not claim those complete or replace their verification.
