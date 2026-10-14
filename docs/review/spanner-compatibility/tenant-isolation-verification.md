# Between-tenant isolation verification

Status: accepted by Astra for the bounded two-tenant slice. Main184checks and restart continuation12checks passed; fresh-process audit passed. GitHub reconciliation is recorded below.

## Scope and user-visible result

Issue #43 under #34. One authenticated Engram entry point must serve two tenants with independently pinned packs and separate Spanner databases. Credentials select the tenant; event fields, headers and artifact identifiers cannot select another tenant's database. Workers must preserve the same binding. Hierarchy authorization (#49), developer pilot, historical migration, native webhooks and streaming imports are outside this slice; unsupported paths must refuse explicitly.

The user approved reusing `engram-g07-target` directly on 2026-10-14. No database creation or deletion is required. `engram`, `engram-compat-target`, and `engram-g06-target` remain protected.

## Database prerequisites and preservation

Both targets use project `portiq-mvp`, instance `engram-experiment`. Read-only preflight succeeded with operator and impersonated experiment runtime identities; records are in `runs/tenant-isolation-1014-preflight/`. Write access and schema compatibility must still be exercised, not inferred from successful reads.

| Tenant | Database | Packs planned | Observed predecessor |
|---|---|---|---|
| A | engram-assess-1010a-pdlc | Core + User + Memory | epoch48; 12 events,33nodes,89edges,5groups,80cursors; no pending/DLQ |
| B | engram-g07-target | Core + PDLC + Memory | epoch3; all7 application tables empty; one control row |

G07 backup is in `/Users/arunmenon/Downloads/engram-g07-backup-20261014/`: complete table export and18DDL statements, JSON readback and table rereads within the same consistent snapshot verified. Export SHA256 `856b66353c9ac6ff24b8db36cb0d607b20f12ae347b13dc99c6b19910592c3dc`. Native backups were refused by the free instance. Restore has not been tested. Backup and dataset are unchanged.

Before any reset/rebinding: pin exact predecessor owner and all application fingerprints; preserve verified complete export; refuse drift/unrecognized keys; write explicit operator intent; change ownership by guarded transaction with increasing epoch. Never let normal startup adopt a database. Reuse existing reset/activation logic only after checking its exact target and owner restrictions. Final acceptance data stays retained.

## Existing components and bounded work

Reuse TenantCatalog, TenantBinding, private authenticated dispatcher, pinned child app lifespans, TenantResponseGuard, durable TenantControl fences, all five real consumers and the existing Spanner adapters. Astra grounded the existing durable fences; the public `create_tenant_app` now uses the existing fenced child factory. Bound JSON cursors and unsupported tenant maintenance operations refuse before effects. No replacement routing framework was introduced. Existing helper single-target restrictions require an explicitly bounded two-target operator path.

## Frozen acceptance scenarios

Before live inputs, the runner must record exact payloads, IDs, expected writes, responses, returned nodes/edges/evidence and forbidden effects independently of observed output. All acceptance writes go through authenticated Engram HTTP, actual workers, Spanner and Engram reads. Direct database reads provide audit evidence only. Scripted external providers must be labeled; provider quality is not claimed.

1. Both tenants start together with their own durable owner and exact pack bundle. A missing/mismatched owner prevents startup; no default database fallback.
2. Submit identical event/session/agent/entity identifiers with distinct tenant content; verify independent ledger contents and graph evidence.
3. Tenant A creates and retrieves user profile/preferences with exact owner and sources. Tenant B's disabled User capability cannot create or expose User artifacts.
4. Tenant B creates and retrieves PDLC changes and links. Tenant A's disabled PDLC capability refuses unsupported inputs with no writes.
5. Both tenants create and retrieve explicit Memory artifacts with independently scoped evidence; no inference from absent producers.
6. Concurrent/interleaved ingestion and reads preserve exact tenant results. Include duplicate replay and conflicting duplicate payloads separately in each database.
7. Reuse consumer group names and event IDs deliberately; each tenant's cursors, pending deliveries, acknowledgements and retries affect only its own database.
8. Missing/invalid/duplicate credentials, spoofed tenant hints, unauthorized roles and caller database fields cannot switch tenants. Check both databases before/after rejected attempts.
9. Retrieval by exact IDs, text search, event subgraph and applicable artifact/User routes returns tenant-only data, edges, counts and evidence. Unknown foreign-only identifiers do not disclose foreign existence/content.
10. Admin stats uses tenant-specific roles and targets. `/v1/admin/prune`, `/v1/admin/replay`, `/v1/admin/reconsolidate`, streaming import, query-string/JSON cursors, unbound webhooks and global metrics refuse before effects. Other administrative operations are not claimed verified.
11. Hold an actual retrieved response before release, freeze A, require generic503 with no answer; reject subsequent reads/writes and old subscription ACKs while B remains usable. After full shutdown, reactivate A with the same binding/interpretation at the next epoch; reject old-epoch worker startup and verify restarted APIs plus all10workers processing fresh events. Durable draining mode and general pending retry recovery are not claimed.
12. Restart/drain supported lifecycles; in-flight work settles and both targets retain consistent state. Do not infer SIGKILL/general recovery from cooperative shutdown.

## Verification and stop gate

For every scenario record input, expected/actual response, ledger acceptance, worker outcomes, graph changes, retrieval evidence and all relevant forbidden effects. Track failed attempts and fixes without overwriting evidence. Capture source hashes, owner/bundle pins, table fingerprints, pending/DLQ and clean worker shutdown. Independent Astra design, implementation and final evidence review are required. Reconcile #43/#34/#39/#41/#42 with actual results; only close narrow issues whose full scope is met. Provide stakeholder walkthrough and repeat command. Stop after this slice for approval; do not start pilot or #49.

## Review and local verification

Astra design/implementation/harness dispositions are retained in [the independent review](tenant-isolation-review/astra-design-and-implementation.md). Targeted routing/query/control suite:205passed. Corrected prefixed response/query guards:19passed. Broad unit suite:2856passed,13skipped; the known `test_pdlc_end_to_end.py` evaluation-gate file was excluded as in the preceding checkpoint. Ruff passes; mypy reports no issues in3 runtime files. These local results are prerequisites, not cloud acceptance.

Attempt01:135assertions passed, then an incorrect newest-source Memory provenance expectation failed. Source inspection shows Memory provenance intentionally anchors to creation, with every lifecycle source still present in typed/public evidence. Attempt02:147assertions passed, then an incorrect200 expectation for Tenant A's unavailable PDLC artifact `trace` failed; the actual422 was correct. Both runs stopped cleanly with zero pending/DLQ and no shutdown errors. Original runner bytes and frozen source hashes were verified/preserved before corrections. Astra approved both contract corrections; no runtime changes or question substitutions masked those failures. Attempt03 preserves A's original `trace` as a422/no-effects negative and adds B's actual foreign-only PR Event UUID lookup, positive on B and non-leaking on A.

## Live results and stakeholder walkthrough

Main evidence: [tenant-isolation-1014-03](runs/tenant-isolation-1014-03/results.json). Restart continuation: [tenant-isolation-1014-restart-01](runs/tenant-isolation-1014-restart-01/restart-results.json). **184 main assertions +12 restart assertions passed**, plus separate mismatched-owner and old-epoch startup guards. [Fresh-process audit](runs/tenant-isolation-1014-restart-01/independent-post-process-audit.json) matched both final owners, all seven table fingerprints, complete saved snapshots, unchanged schema and219 current source hashes. Main runtime source hashes remain unchanged; the archived main runner matches its original hash.

| Demonstration | What happened in Engram | Evidence to inspect |
|---|---|---|
| One shared entry point, two tenants | Credential grants chose separate pinned child APIs and Spanner databases; all10real worker loops ran with the corresponding bindings | Main manifest/binding records and public-dispatcher-ready assertion |
| Overlapping identities | Both tenants used identical common Event UUIDs, session, agent, Entity and Memory identities. A retained fifteen-minute Belief/Goal content; B retained its distinct thirty-minute content | Exact ledger documents/acceptance authority, graph properties and public Memory responses |
| Different packs | A produced User profile and preference correction; B produced PDLC Changes/Decision. Disabled outputs stayed absent | User/PDLC selection assertions, profile/personalization, stored nodes |
| Real read-path proof | Memory responses included exact creation-based source provenance and complete evidence links. B retrieved merged Change with merge provenance | Memory/Goal/User/PDLC response assertions and request journal |
| Foreign-only lookup | B returned its PR Event and exact own ledger position; A excluded B-only PR/Change identities | Positive B and negative A Event lookup assertions |
| Authentication and capability failures | Unknown/missing/duplicate credentials, conflicting tenant hint, forged routing fields, conflicts, disabled PDLC input, unsupported trace/cursors/maintenance and wrong role were refused without unintended table changes | Rejection request journal and before/after fingerprints |
| Independent delivery state | Both databases used the same5group names and80cursors; acknowledgements and stored content remained independently scoped | Fresh raw ConsumerGroups/Cursors, typed sources and final fingerprints |
| Freeze during a read | A's actual retrieval was held before response release. Freezing A produced generic503 without the answer. A's reads/writes and all5old subscription ACKs refused; B continued reading | Held-response, stale-ACK, frozen-write/read and B-positive assertions |
| Ownership and restart | Wrong-owner startup failed without effects. After shutdown A advanced to epoch52; old-epoch worker startup refused. Restart continuation submitted new authenticated Events and required zero lag, zero pending and both exact projected Event nodes | Startup records, restart continuation and final snapshots |

The first restart observation in main attempt03 failed because the harness waited for lag alone: it checked before an in-flight projection completed. Both fresh Events were present after cooperative drain. That failed observation remains [retained](runs/tenant-isolation-1014-03/restart-disposition.json). Astra approved the corrected wait and a targeted continuation using exact saved owners/fingerprints, unchanged runtime code and new frozen Event IDs. **The continuation did not reset or rebind either database.**

Final retained state:

| Target | Packs | Active epoch | Events | Nodes | Edges | Groups / cursors | Pending / DLQ |
|---|---|---:|---:|---:|---:|---:|---:|
| engram-assess-1010a-pdlc | Core+User+Memory |52|11|37|151|5 /80|0 /0|
| engram-g07-target | Core+PDLC+Memory |6|14|50|176|5 /80|0 /0|

Main accepted9A and12B Events. Each target also retains the Event from the first restart observation and one new continuation Event; those explain the final11/14counts. Both public APIs and all worker loops are stopped cleanly. No database was created or deleted; the three other protected targets were not touched. Earlier datasets were exported and verified before exact-key resets.

### Repeating the demonstration

The saved request journals are the stakeholder walkthrough: inspect each frozen input, HTTP response, exact graph/source assertion and forbidden-effect check. The fresh audit can be repeated read-only from the repository root:

```sh
PYTHONPATH=src:scripts /Users/arunmenon/projects/Engram-foundation-gate/.venv/bin/python docs/review/spanner-compatibility/runs/tenant-isolation-1014-restart-01/post-process-audit.py
```

A fresh full demonstration is **mutating** and requires approval to reuse the retained targets. It exports/verifies both exact predecessor datasets before resetting; choose a new run ID and supply the saved predecessor directory:

```sh
PYTHONPATH=src:scripts /Users/arunmenon/projects/Engram-foundation-gate/.venv/bin/python scripts/engram_tenant_isolation_demo.py --run-id tenant-isolation-repeat-01 --previous-directory docs/review/spanner-compatibility/runs/tenant-isolation-1014-restart-01
```

### Limits of this checkpoint

This proves the selected two-tenant public-dispatcher path and pack/database isolation with frozen external model outputs. It does not prove prose/model quality, all pack combinations, general pending recovery, durable draining mode, forced process termination, hierarchy policies, all admin operations, public native webhook routing, streaming imports/cursors, ANN/load performance or the original65-scenario compatibility baseline. The unevaluated experimental-pack gate is explicitly enabled. Cloud Monitoring export still returns403; no monitoring-readiness claim. Administrative stats event counts were independently checked against each tenant's own main9/12events; this is not complete optional-type statistics coverage. #43 and the larger umbrellas remain open. Pilot execution requires separate approval.

Independent final review: [Astra accepted the bounded slice](tenant-isolation-review/astra-final-review.md), with no remaining blocker. This does not close #43 or authorize the pilot.
