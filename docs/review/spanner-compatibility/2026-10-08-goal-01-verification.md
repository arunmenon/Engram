# G01 verification and stakeholder demonstration

Status: all eight required scenarios PASSED on real Spanner; independent Astra review found no blocking findings; stakeholder delivery is tracked below. Only G01 is authorized. G02 remains stopped. This is PR-slice acceptance, not completion of #34 or Spanner umbrella #41.

## What this demonstrates

A signed GitHub-shaped message travels through the real source adapter and HTTP API into Spanner. Five ordinary worker loops consume the ledger. The projector creates the common Event and PDLC Change, preserves evidence, and the actual artifact retrieval API returns the stored artifact. There is no direct artifact insertion or mock Spanner provider. SQL observations inspect effects; cleanup removes registered test keys afterward.

The source is a public OpenDAL REST PR record reconstructed into webhook payloads, with isolated repository names and controlled timestamps. These are not captured webhook deliveries. Jira APP-42 is a synthetic prerequisite sent through the signed Jira API, not inserted into the graph.

Configuration: core@1.1.0 + pdlc@1.8.0; memory/user disabled. Single bound tenant `compat-control`; database `projects/portiq-mvp/instances/engram-experiment/databases/engram-compat-target`. All five storage ports use Spanner. Actual cached MiniLM embedding provider; PR mappings are deterministic and do not exercise LLM extraction. The disposable `serve_unevaluated` gate is enabled explicitly. This does not establish pack-wide evaluation.

## Recorded stakeholder demo

Read the following as the replay of a completed cloud run. Each row has the full source, normalized ledger record, accepted authority, worker lags, graph snapshot and retrieval response in [observations](runs/20261008-cloud-g01-all-02/observations.json); matching inputs and their hashes are in [fixtures](runs/20261008-cloud-g01-all-02/fixtures.json).

| Scenario | What we sent | What actually happened | Verdict |
|---|---|---|---|
| PR01 | Open PR 8382 in the isolated payments repository | HTTP 202; one open Change with the original title; retrieval returned it with its originating event | PASS |
| PR02 | Edit that PR's title | HTTP 202; same Change now has the edited title; both accepted events and evidence links remain | PASS |
| PR03 | Resend the identical body with a different delivery header | HTTP 202 and the same event identity; persistent ledger/graph state unchanged; retrieval unchanged | PASS |
| PR04 | PR payload without repository | HTTP 422; ledger/graph snapshot unchanged; existing Change still retrievable | PASS |
| PR05 | Create Jira APP-42 through its signed endpoint, then merge PR 8382 referencing APP-42 | HTTP 202; same Change becomes merged and has one confirmed, declared IMPLEMENTS link to WorkItem:jira|APP-42; retrieval includes the ticket | PASS |
| PR06 | Open and merge PR 8383 with no ticket reference | HTTP 202; separate merged Change; no invented ticket link and no unrelated Change in retrieval | PASS |
| PR07 | Open PR 8382 in the isolated billing repository | HTTP 202; distinct open Change; payments PR remains merged; no cross-repository Change/evidence contamination | PASS |
| PR08 | Deliver an older edit after the payments PR merged | HTTP 202; merged status retained and all evidence retained; title becomes the older edit's title according to the predeclared delivery-order policy | PASS |

PR05-ticket and PR06-open are two additional prerequisite checks, not extra required scenarios. All ten recorded checks passed. Five worker lag counters were zero after each request; shutdown had no errors or pending/dead-letter residue.

## Follow one event through Engram

1. **Input:** PR01 contains repository `g01/20261008-cloud-g01-all-02-payments`, number `8382`, title `ci(moonbit): update pinned MoonBit version`, action `opened` and a timezone-aware source time. HMAC authenticates the configured webhook source.
2. **Translation:** GitHub adapter emits `pdlc.change.created`; payload carries `repo`, `number`, `title`, `body`, `files`, and `head_sha`. Common envelope carries event/session/type/time and stable body-hash trace/reference. Transport delivery headers do not change the semantic identity.
3. **Admission and ledger:** bound source authority and the selected bundle validate the event before append. PR01's event is `47c79548-2a76-5f69-8d46-15a1f056e50d`. Its accepted metadata records tenant, database, binding, epoch 17, bundle digest, source and request digest. HTTP 202 means accepted into storage; worker checks establish processing separately.
4. **Workers:** actual projection, extraction, enrichment, pack_extraction and consolidation loops run. Core Event is the evidence spine. PDLC rules identify Change by `(repo, number)`, not PR number alone. Unselected memory/user artifacts are absent. These PR events do not trigger every possible worker behavior.
5. **Graph:** Change `Change:g01/20261008-cloud-g01-all-02-payments|8382` points through DERIVED_FROM to the accepted Event. Editing adds evidence and updates the same identity. Merge changes lifecycle and adds the explicitly declared ticket relationship.
6. **Retrieval:** authenticated HTTP artifact query uses explicit Change seed plus `trace` intent. The returned attributes are checked against stored graph values and provenance against accepted ledger events/positions. This proves structured seeded retrieval, not natural-language-only discovery or a generated answer.

For each checkpoint, the recorded scenario objects contain `input_sha256`, `response`, `storage.events` (envelope + acceptance), `storage.nodes`, `storage.edges`, `worker_lags`, and `retrieval` (request + full response). The script enforces exact expected domain artifacts/evidence rather than counting any nonempty response as success.

## Changes and why they were needed

- **Webhook admission:** missing repository and malformed fields now reject clearly. Source timestamps require an explicit timezone. Verified source authority reaches bound admission rather than bypassing pack validation.
- **Retry identity:** normalized trace/reference use signed-body identity. Resending one body with a different transport header no longer looks like conflicting event contents.
- **Retrieval #45:** the first full run found that an exact composite Change ID was also parsed as fuzzy repository text, pulling a sibling PR into the answer. Resolved explicit IDs are now removed only from secondary query-text parsing; independent references and normal relationship traversal remain. Six unit cases cover that boundary.
- **Demo runner:** actual HTTP server, all five workers, exact ledger/graph/retrieval assertions, pre-registered mutations, cancellation-safe cleanup and source fingerprints. Reused earlier tenant bindings, bundle contracts, admission, fences and Spanner adapters. The six hours of foundations were preserved and exercised, not rewritten or declared universally complete.

## Runs, review and retained failures

| Run | Outcome |
|---|---|
| cloud-g01-preflight-01 | Read-only target check; seven application tables empty. Probe-close stall recorded; no database writes |
| local-g01-ingress-01 | 30 webhook tests and lint passed |
| cloud-g01-pr01-01 | FAILED: runner assumed retrieval nodes were a list; API returns a dictionary. Cleanup completed |
| cloud-g01-pr01-02 | FAILED before writes: explicitly pinned predecessor digest did not match restoration intent |
| cloud-g01-pr01-03 | PR01 complete path passed; empty target restored at epoch 14 |
| cloud-g01-all-01 | FAILED: real sibling-PR retrieval contamination, filed as #45; cleanup restored epoch 16 |
| local-g01-seeds-red-01 | Reproduced #45 before fix; expected failing regression retained |
| local-g01-regressions-03 | 70 tests passed; lint clean; type checks clean for both changed runtime files |
| cloud-g01-all-02 | All eight scenarios and two prerequisites passed; empty target restored at epoch 18 |

Run IDs above have prefix `20261008-`; exact manifests/results/logs are under [runs](runs/). An initial exploratory 24-test execution was not pre-registered; disclosed as a process lapse and excluded from E2E proof. Independent review: [Astra scoped review and dispositions](2026-10-08-astra-g01-ingress-review.md). Final evidence review found no blocking findings and confirmed runtime hashes, scenario checks and cleanup.

## Limits that matter

- PR08 proves lifecycle preservation, not timestamp-based property ordering. Its late title wins by delivery order; `updated_at` can move backward. Broader projection ordering remains open. Artifact-level provenance selects a supporting latest-occurrence event; field-specific title provenance is not claimed.
- One bound tenant/database is tested. Public multi-tenant dispatcher, cross-tenant isolation, other pack combinations and all 23 PDLC events remain outside this slice.
- Old webhook normalization history/replay compatibility remains unproved. No broad #37 closure.
- Cloud Monitoring metrics export reported permission 403. Data-path acceptance passed; monitoring IAM is not signed off.
- #41's 65-scenario baseline is unchanged; G01 checks are separate and do not promote partial/blocked baseline rows.

## Repeatability and cleanup

The disposable target was empty before activation. Exact-key cleanup removed 8 Events, 13 GraphNodes, 14 GraphEdges, 5 ConsumerGroups and 80 ConsumerCursors. All seven application tables were empty afterward; owner restored active at epoch 18 and the explicitly intended core digest. Source database `engram` was not targeted. No database deletion or broad truncate was used.

[Manifest](runs/20261008-cloud-g01-all-02/manifest.json) records the actual dirty-worktree runtime hashes. [Executed source archive](runs/20261008-cloud-g01-all-02/executed-source.tar.gz) preserves the exact source, helper scripts, package configuration and fixtures; [archive file hashes](runs/20261008-cloud-g01-all-02/executed-source-sha256.json) allow verification. This preserves reused WIP foundations without misrepresenting them as completed or reviewed. Credentials are excluded. Use the existing prepared environment with dependencies and the cached embedding model. Extract the source archive into a separate checkout for an exact replay.

Refresh credentials with the authorized local token script without publishing its output. Then, after confirming the target is still reserved and empty and the known owner remains unchanged:

```bash
PYTHONPATH=src:scripts python scripts/engram_goal01_pr_demo.py \
  --run-id <unique-run-id> \
  --credentials <private-token-env-file> \
  --expected-epoch 18 \
  --expected-digest sha256:f57ffb649f7ab0197d21f45b9397203887f8cb103e32efd784f4e52ce4c3f7b1
```

A future run must pin its known predecessor; do not adopt whatever owner happens to be observed. Each completed run advances the owner epoch. Credentials and network access are required; do not substitute memory backends. Raw source requests and sanitized results are retained, not authorization headers/access tokens.

## GitHub reconciliation and bucket assessment

Pending publication links. Existing broad issues remain open unless their full acceptance has been met. #45 fits existing retrieval bucket 5 under #34 and Spanner evidence #41; no additional feature bucket is justified by this discovery.

## Stakeholder delivery and next-goal gate

This document is the recorded demonstration script. Live stakeholder sign-off is not assumed. Final delivery must explain all eight results and limitations and link the actual issue updates. G02 cannot start without explicit user approval; the original broad goal remains paused and retired from execution.
