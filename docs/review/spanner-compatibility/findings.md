# Spanner compatibility findings and review dispositions

## Established findings

- Issues #4–#19 are open engine/integration findings; see the plan's mapping. Real-Spanner rechecks are pending. Memory or emulator proof is not cloud proof.
- #6 and #7 reproduced with Spanner emulator storage. Evidence is preserved under the retrospective emulator run; issue comments record the recheck.
- Ordinary startup does not consume the raw token environment variable; `schema.open_database` uses default SDK credentials. This is a credential prerequisite, not a demonstrated Spanner service failure.
- Cloud harness now exercises the existing disposable `engram` database. Initial journeys and boundary subchecks are executed; full scenario acceptance is still pending.
- Keymaker journeys are unspecified (APP-06 blocked). Simulation endpoint is stateless LLM-only and excluded from direct storage coverage.

## Suspected failures to verify

- Admin replay uses EventQuery occurrence-time pagination and structural projection only. LIFE-04 must probe timestamp ties across100-row boundaries, session interleaving, pack nodes and ontology state. Code inspection is not yet a portable failing reproduction.
- Native search/vector/index behavior, thread cancellation and full process startup differ from emulator assumptions; scheduled in SEARCH/MEM/OPS, not labelled as bugs yet.

## Independent review

Astra low-effort independent review completed. Four findings accepted: replay process bound, unread-vs-pending lag, per-destructive-case ownership guards and concrete inventory traceability. Plan and CSV corrected. Execution readiness remains conditional on the harness and isolated fixtures. No cloud writes authorized by a successful review alone; the user has requested the test work, but resource-isolation and credential gates still apply.

Review evidence: reviewer inspected `api/routes/admin.py:329–355`, `adapters/spanner/log.py:638`, `ports/subscription.py:97`, `adapters/spanner/subscription.py:328`, `scripts/spanner_probes.py:565`, and inherited `adapters/graph_ops.py` behavior. These review findings are plan requirements; suspected replay failure still needs reproduction.

## Cloud preflight 20261006-cloud-preflight-9c6120b9

Engram `open_stores` against the configured real database succeeded under explicit token SDK bootstrap: SpannerEventLog, SpannerGraphStore, all five ports Spanner; schema matched; both health probes true. No API/worker processes or model providers launched, and no writes/resource changes made. This is read-only connection proof, not full-flow acceptance or ordinary ADC proof.

Database discovery returned PermissionDenied. Disposable manifest-owned test databases and their provisioning/cleanup permissions remain unverified. Full acceptance and especially destructive scenarios are blocked until an isolated database is available and the executable journey harness is ready. Do not translate inability to list databases into an unsupported claim that all data access or database creation is denied.

The first bootstrap attempt rejected a non-environment explanatory line in the captured script output before any cloud calls. The parser was corrected to accept only the four expected assignment lines. No credentials were disclosed. Both attempts are recorded in runs.jsonl.

## Existing Engram database: read-only HTTP smoke

Run `20261006-cloud-api-readonly-ae2eb216` used the user's existing database with the real Engram API in a separate uvicorn process, ordinary lifespan/store composition, and explicit token SDK bootstrap. Six HTTP subchecks passed: health, ontology, admin stats, empty-session context, missing-node lineage and empty-session subgraph. Health/stats identified Spanner; retrieval returned the expected empty results. No providers invoked, test records ingested, workers launched, ontology state changed or cloud resources altered. Owned API process stopped. This is partial read-only smoke evidence; populated retrieval and all65 acceptance scenarios remain pending. Existing database existence is confirmed and is not a blocker to scoped/read-only checks; disposable ownership is still required before broad destructive cases.

## Journey harness race (first cloud batch)

Run `20261006-cloud-journeys-3fad4ab3` failed all three legacy-helper journeys. Inspection showed `_drain` queried lag before the worker created its group; Spanner's cursor join returns0 without cursors, so the helper stopped a worker before it consumed data. This is a harness false negative, not three proven product defects. The cloud runner now explicitly ensures the group before starting/polling the actual worker loop; next run uses new records and retains these failures. Added traceback evidence and runner-source snapshots.

## Disposable database authorization and successful journey recheck

User explicitly confirmed the existing `engram` database disposable. The guarded runner clears fixture rows in seven tables before each phase, preserves database/schema, and records affected rows. Run `20261006-cloud-journeys-59e6f628` passed agent-memory, signed PDLC (including pack extraction), and CRM journeys on all five real Spanner ports. These use real API handlers and worker loops in one process; separate-process and fault-path requirements remain open. The earlier drain-helper failure remains preserved, not counted as a product defect.

## Cloud ingestion boundaries

Run `20261006-cloud-boundaries-5778ddba`: six successful subchecks, five failed subchecks. Confirmed existing defects: #4 missing CRM key accepted HTTP201; #15 mixed naive/aware timestamps HTTP500; #16 gzip without trailer accepted HTTP201; #17 future signed GitHub event accepted HTTP202 and malformed nested repository shape HTTP500. Valid nested JSON/duplicate, mixed batch outcomes, empty/max+1 rejection, historical gzip NDJSON order/malformed line/retry, namespace/reserved identity, HMAC rejection, and health routes passed. Partial success does not close broader CSV rows. These failures are upstream ingestion defects reproduced with Spanner, not evidence of a native Spanner defect.

## Entity-interest extraction: new confirmed contract mismatch

Run `20261006-cloud-knowledge-ca060841` reaches real extraction writes from API-ingested session-end events. `worker/extraction.py` calls `write_derived_from_edge(source_id_field="entity_id")` for interests; `adapters/graph_ops.py` rejects it because `DERIVED_FROM_SOURCES` omits that field. Actual worker log shows ValueError after profile/entity/preference/skill/interest writes. The delivery stays pending and the drain cannot complete. This is shared graph-contract code exercised on Spanner, not yet asserted to be exclusive to Spanner. Scripted LLM output isolates the storage path; no paid provider is involved.

## Independent-process embedding prerequisite

Run `20261006-cloud-processes-7c6d0b2e` exposes a missing optional dependency: the embedder constructor logs initialized, but first `embed_text` imports sentence-transformers lazily and raises ModuleNotFoundError. Earlier initialization logs were not proof of embeddings being available; query fallback can mask this. Extraction cannot finish with its configured embedding path in this environment. Install the project's declared embedding extra into the temporary venv before the next new run; preserve the failed record. Native ANN acceptance is still unproved. Also corrected the test's expected admin-key rejection to HTTP401, as specified in `api/dependencies.py`; no product auth defect claimed.

## Knowledge phase results and issue tracking

`20261006-cloud-knowledge-ca060841`: extraction cannot drain because of [#20](https://github.com/arunmenon/Engram/issues/20); feedback audit/missing-node/resubmission checks, admin and timer summary creation, and user deletion preserving another user/shared skill/entity/ledger passed. Read/export assertions after the failed extraction drain were not reached. Timer summary creation alone does not prove the entire forgetting/archive/retention cycle completed. Existing #4/#15/#16/#17 now have cloud recheck comments. Reconciliation01 marks ING-01, ING-03, HOOK-03, EXT-02 and APP-01 failed; partial successful rows carry evidence but stay not_run until their full assertions are covered.

## Separate-process recheck harness correction

`20261006-cloud-processes-ff2de877` initialized all five workers, extracted the entity and user, and drained the storage work after installing embeddings. Its acceptance assertion still timed out because the test client used the ordinary API key to read a user profile, while all user routes require the admin key. This is a harness false negative: API correctly returned401. Corrected request headers for a new run; retained the failed attempt. Installation/model warmup produced384 dimensions, but native ANN validation is still pending until a successful populated process journey.

## Cross-process drain probe corrected

`20261006-cloud-processes-01e776a0` exited its readiness loop too early: `delivery_counts` is scoped to the subscription's consumer, and the harness queried a new monitor consumer rather than the real worker consumer. The extraction had written a profile but was still computing the entity vector when retrieval ran. This is another harness false negative, not a missing Entity product defect. New run probes each real worker consumer and requires startup pending-drain completion. Owned processes were stopped before reset.

## Cold query timeout and native ANN smoke

`20261006-cloud-processes-2212badc` reached drained worker groups, context and entity reads, but the first embedding-enabled subgraph request exceeded the client10-second limit while loading the query model. Kept as a measured cold-start failure; next run explicitly permits60 seconds for that request. No latency SLO or Spanner root cause is claimed. Read-only follow-up `20261006-cloud-search-cf3b5c0f` confirms the real forced ANN path returns the persisted Entity vector (score~0.99955). Only Entity nodes populate the dedicated embedding column by design; event embeddings remain in properties. One self-hit does not prove multi-vector recall or all search boundary cases.

## Expired cloud credential window

`20261006-cloud-processes-b4a91144` was blocked at initial schema access with real Spanner Unauthenticated / ACCESS_TOKEN_EXPIRED. No resets, worker launches or fixture writes occurred. This proves a real expiry response without backend fallback, but not recovery/ACK safety for an already-running worker. Token renewal is a separate new window using the user-provided local script, privately captured; no token content enters the ledger.

## Successful independent-process journey

`20261006-cloud-processes-98933a6e` passed the Engram API and five actual worker composition-root/loop processes, worker-group unread/pending drain, profile/entity/context/subgraph reads, API/admin-key separation and admin summary creation. It also passed persisted384-dimensional Entity vector self-hit via native forced ANN and native full-text search/session filtering. Scripted LLM omits interest to isolate #20; local embedding model is real. Owned API/workers stopped, with exit receipts retained. This closes these subchecks; it does not close all APP-01/BOOT/SEARCH/OPS requirements, such as crash/restart, live paid providers, multi-vector recall or every fault/limit case.

## Confirmed replay pagination failure — issue21

[#21](https://github.com/arunmenon/Engram/issues/21), run `20261006-cloud-replay-93151f94`:128 API-ingested timestamp-tied events; the exact admin EventQuery returns the identical100-ID list on the next page. The real replay endpoint did not complete within its30-second request limit. The owned API was terminated/killed and cleanup recorded. Timeout alone is not proof of the infinite loop; identical pages plus the inclusive cursor logic are the decisive evidence. Source database/schema were preserved; only disposable graph rows were cleared by replay. Pack restoration and interleaved-session lineage remain additional unexecuted LIFE-04 requirements.

## Real Spanner retention data loss — issue19

`20261006-cloud-retention-85231d1e`: API accepted a100-day-old event, projection held a pending delivery, consolidation timer archived then removed its document, and the actual projection startup/pending loop ACKed it without a graph Event. Both preservation assertions failed. FS gzip archive and before/after pending/document observations are retained. Adds real cloud proof to #19; archive restore/GCS/failure protection and other retention boundaries remain open. All fixture loops stopped before the next reset.

## Ontology rebuild/cutover prerequisite denied

`20261006-cloud-ontology-d985f707` attempted to provision a uniquely named manifest-owned second database for the legitimate rebuild CLI target. Real Spanner returned403 naming `spanner.databases.create` on `portiq-mvp/engram-experiment`. Receipt confirms created=false; no extra database/schema was created. ONT-03/ONT-04 are blocked for cloud execution. Existing issue13 remains a configuration-level ledger-cutover risk; it has not been cloud-reproduced here. No Redis/Neo4j runner or alternate memory graph is substituted.

## Admin route and prune checks

`20261006-cloud-admin-8ba62c96` passed API/admin/import/user authorization separation, missing-user semantics and Prometheus metrics. It also projected40-day/10-day/fresh low-importance events through the actual worker, proved dry-run preserves all three, then live cold/archive pruning removed exactly two and their incident edges while preserving the fresh Event and all three ledger documents. Warm-similarity pruning, truncated scans and large deletion transactions remain additional LIFE-03 requirements.

## Retrieval bugs6/7 confirmed through cloud artifact API

`20261006-cloud-artifacts-cc114156` passed baseline CRM competencies after actual API ingestion, projection and evaluation gating. Limiting graph calls to1 produced truncated coverage but returned Acme with `no_link` despite its confirmed deals (#6). Marking Deal:D-7 BELONGS_TO Acme rejected through the public graph write port still returned that rejected edge as evidence (#7). Exact HTTP answer JSON retained. Both are shared retrieval defects now confirmed on real Spanner. Alternate-valid-route, rejection combinations and other completeness budget cases remain in the matrix.

## User-created disposable target

User created the requested `engram-compat-target`. Run `20261006-cloud-ontology-9e43d094` still received403 `spanner.sessions.create` for the token service account before inspecting or modifying target schema/data. Preserved the user target. A separately tracked setup grants the existing `engram-experiment-sa` database-scoped `roles/spanner.databaseUser` only on this requested test target, using the local owner identity. No project/instance grant or new service-account key. Google documents this role as including queries/writes/schema updates: https://docs.cloud.google.com/spanner/docs/iam . Rebuild/cutover retry follows after the setup result.

## Rebuild passed; cutover13 now cloud-reproduced

`20261006-cloud-ontology-359246f7` initialized canonical schema only on the empty user-created target, preserved both databases, rebuilt11 CRM ledger events into the real second graph and passed CRM gate mean F1=1.0. Opening stores under target settings selected a0-event target ledger instead of the11-event source ledger (#13). Full report and target setup/reset receipt retained. ONT-03 provisioning/access blocker is resolved for this target; remaining rebuild fault/missing-history/interruption cases are not yet covered. ONT-04 fails on the fundamental ledger selection behavior; concurrent catchup/rollback remain pending.

## PDLC evaluation scope and larger-corpus retry

Run `20261006-cloud-pdlc-8c327a69` passed both signed eight-delivery PDLC fixture evaluation and real second-database rebuild evaluation: 11 competency questions each, mean F1=1.0. Its OpenDAL ingestion hit the real HTTP429 rate limit before projection/evaluation; this is an incomplete harness run, not a failed PDLC graph competency. Preserve the attempt. Retry uses bounded retries respecting the returned delay without disabling the limiter. The 292-delivery OpenDAL corpus covers change/release/revert data; Jira, review, CI and deployment relationships are covered by the small fixture, not asserted present in OpenDAL. No complete PDLC corner-case or separate-process sign-off yet.

## PDLC larger-corpus cloud result

`20261006-cloud-pdlc-b790ad36` completed all three subchecks: eight signed-delivery fixture plus extraction/artifact assertions; real second-database PDLC rebuild; and 292 OpenDAL signed deliveries through projection and recorded evaluation. Source/rebuilt small evaluations each passed all 11 questions at F1=1.0. OpenDAL passed its declared mean-F1 gate at 0.9118 against 0.90: 14 of 17 questions were exact; three returned extra lexical matches (`change-for-gcs-grpc` 0.3333, `change-for-gcs-compose` 0.6667, `release-for-gcs-grpc` 0.5). These are documented fixture retrieval limitations, not newly established Spanner-specific defects. The large subcheck took 473.14s, close to its 480s deadline; no latency SLO/performance sign-off. Both database schemas were preserved. A separate `pdlc-api` run checks the same populated corpus through HTTP and does not reset it.

## OpenDAL HTTP gating harness correction

`20261006-cloud-pdlc-api-37f0fdcb` verified 292 ledger entries and zero unread/pending projection work, and its graph evaluation passed at 0.9118. HTTP correctly reported PDLC pending because the large direct-loop harness had omitted the ontology reconciliation performed by the normal projection CLI. `evaluate_graph(record=True)` intentionally records only on a graph with the matching ontology state. This is a harness false negative, not a product gate defect. Retry invokes the CLI-equivalent schema/reconcile sequence before its consumer loop, evaluates/records, then checks HTTP answers. Earlier small-fixture and rebuild evaluations remain valid; the larger first evaluation was numerical proof, not proof of recorded version/gate state.

## PDLC HTTP completion and operational stats defect

`20261006-cloud-pdlc-api-64e30b68` passed zero unread/pending work (292 ledger events), matching-version recorded evaluation (mean F1=0.9118), and all 17 artifact HTTP competency requests (same mean F1). The final tracker subprocess SIGTRAP occurred after observations/cleanup/results input were written; its finish was reconciled via system Python without re-running any cloud work.

Corrected stats run `20261006-cloud-stats-a4a0c509` failed a genuine pack-count assertion: the PDLC target has 19 domain nodes plus OntologyState and 25 edges, while admin stats report only 9 Event nodes and 6 FOLLOWS edges. Fixed static type lists in shared GraphOps omit all pack counts. Filed [#22](https://github.com/arunmenon/Engram/issues/22). The older stats attempt was a harness KeyError, preserved separately. This is a shared defect reproduced on Spanner, not an assertion of Spanner-only causality.

## Resumed cloud batch, 13:30 UTC onward

Combined `20261006-cloud-combined-d3dac25e`: independent API/projection processes, 11 CRM imported events plus eight signed PDLC deliveries; both packs scored1.0, both HTTP fixture question sets and core memory context passed. APP-03 and APP-04 close their scoped journey assertions; adjacent fault/provider/pack-composition corners remain separate.

Recovery `20261006-cloud-recovery-dd24b1e3`: real kills at controlled before-graph/before-ACK boundaries recovered exactly one Event, zero pending and no DLQ. A synthetic one-shot transient write recovered in place; removed one-shot non-transient write remained pending (#14, cloud comment added). Concurrency `20261006-cloud-concurrency-daf16e16`: controlled A→1/B→2/A→3 live replica schedule reproduces incorrect FOLLOWS cache lineage (#18, comment added); abandoned15 deliveries recover across batch-size3 pending pages with15 Events/14 FOLLOWS/no DLQ.

Startup `20261006-cloud-startup-a9067dfe`: real invalid token/missing target fail closed; ordinary ADC absent (blocked, no credential configuration changes). Schema `20261006-cloud-schema-fd247214`: configured3 vs physical384 vectors accepted at healthy API startup, then native search length mismatch (#23). Matching names alone are insufficient schema handshake proof.

Endpoints `20261006-cloud-endpoints-fa84c6f7`: seven tied events retain nested JSON and context pages cover all seven; ANN4-vector self/near/top-k/threshold/native index assertions pass. Lineage returns4 under max_nodes3 and pagination terminates after four of seven (#24). Same-session vector isolation `20261006-cloud-vector-9f8fc3ca` returns positive native seeds but empty API nodes despite Event REFERENCES evidence (#25); graph seed channel is explicitly controlled empty, not a claimed cloud service outage. Earlier disconnected-vector fixture and wrong feedback expected200 were harness errors; corrected feedback expects201 and records the partial500 update, durable audit and repeated effect/new audit on retry. No atomic/idempotent feedback guarantee claimed.

Upgrades `20261006-cloud-upgrades-bdcddac8`: actual loaded custom pack, historical admin import, initial/additive projection and unsafe-version/breaking refusal passed; synthetic mapping-write failure records completion and no repair on retry (#11); populated incompatible target refused/preserved; public document expiry followed by real second-target rebuild falsely passes with missing_documents1 (#12). Prior `...upgrades-34db37fe` lacked the projector trusted_sources argument, a preserved harness setup error; no memory backend was instantiated.

Shutdown `20261006-cloud-shutdown-71530641`: after normal API lifespan, zero registered Spanner closers, no SDK Database.close invocation, session/renewal thread retained (#26). SDK local polling was shortened only for bounded test cleanup; owned SDK manually closed afterward. Earlier invalid health/detailed route attempt `...shutdown-9df04375` was terminated during default600s SDK cleanup; remote session deletion unverified. It is retained as a harness failure, not proof.

JSON `20261006-cloud-json-22af9759`: valid literal $float singleton objects accepted with201 are decoded into a number or become unreadable (#27). Both receipts preserve expected/stored/error shape. These are Spanner codec failures.

New issues23–27 and recheck comments11/12/14/18 are published. Source/target databases and schemas remain. No runtime source fixes or backend migration performed.

## Pack projection boundary rechecks

`20261006-cloud-pack-cases-143609a6`: unprefixed latest deployment selection across three out-of-order candidates with limit2 passed. Component prefix lookup beyond the two-candidate cap silently missed its TOUCHES edge (#8). Review changed Change.status without direct review-event DERIVED_FROM (#9). Actual pack extraction ran before actual projection, acknowledged the Decision, then projection did not restore its evidence (#10). Real Spanner/API/worker loops, scripted extraction output, explicit trusted test source; no source-identity authentication claim. These failures close failed rows, not remaining corner coverage.

## Consolidation cycle and commit harness correction

`20261006-cloud-maintenance-99735438` passed one actual timer cycle: six Summary nodes with evidence edges, importance recalculation for seven Events, one low-score warm edge removed/high-score edge retained, two old cold graph Events removed, connected Entity preserved/orphan Entity removed. Seven ledger documents retained, no cycle exception, consolidation pending0. The archive-deletion step saw zero remaining candidates because cold pruning removed both old nodes first; log trim/expiry/housekeeping returned0. This does not claim nonzero archive deletion or full CONS/LIFE closure.

`20261006-cloud-commit-cases-6773b3cc`: exact two-row estimated mutation boundary and synthetic third-chunk failure with safe retry passed. Concurrent/oversized cases had a harness mistake treating get_documents list as a map, after successful real writes; preserved as harness failures, corrected to ordered-list access in the next serial attempt. They are not new product findings.

## Further scoped passes

Corrected `20261006-cloud-commit-cases-61ce4449` passed concurrent same-ID/different-payload first-write-wins, exact two-row commit boundary/committed-prefix failure/retry, and single oversized configured-budget item delegation with lossless payload. The latter is documented adapter behavior, not proof of a hard configured byte cap or Spanner service-limit rejection.

`20261006-cloud-pack-policy-85dedd72` passed invalid model JSON ACK/no proposal, node cap1, confidence ceiling0.8, caller-supplied trust ignored/untrusted event source retained, invalid target link refusal, projection-first evidence, and preservation of existing accepted/trusted authoritative properties. Does not close #10, link-rejection combinations or provider-outage recovery.

`20261006-cloud-knowledge-safe-3709f47e` passed actual entity/user extraction, all read/export routes, shared-skill preservation during user deletion, feedback and admin/timer summaries. Interest creation was explicitly omitted to isolate #20; interest reads empty, not a successful interest-write test. Timer execution log has no consolidation_cycle_failed.

`20261006-cloud-keyword-features-5cb93390` passed native case, Unicode, punctuation, empty/zero-result and session-filter keyword queries; its three HTTP feature cases correctly returned422 because the harness omitted required agent_id. This is a preserved harness error; retry supplies the required field.

## Subscription and webhook progress

`20261006-cloud-subscriptions-7700ac35` passed delivery on all16 shards to two independent actual projection groups, late-group historical delivery, six pending pages (size3), partial ACK, persisted DLQ/ACK and blocking wakeup on new API ingress. Its uncertain-commit injection confirmed lossless duplicate retry after a real commit, but first response was generic500 despite neutral UnavailableError: [#28](https://github.com/arunmenon/Engram/issues/28). The error was synthetic; no real service outage claimed.

`20261006-cloud-keyword-features-601ffec7` corrected required agent_id and passed native keyword boundaries, keyword-only API hydration/session isolation, enabled PPR/MMR/HyDE smoke and synthetic keyword-failure/HyDE-timeout graph fallback. This is bounded feature execution evidence, not a retrieval quality benchmark.

`20261006-cloud-webhook-handlers-5556f879` reached signed Jira Closed status and failed a harness expectation that it emitted closed. The documented adapter closes only Done/Won't Do; Closed is passed through in an updated event. This is an unsupported vocabulary assumption, not a new product defect. Earlier normalized events and redelivery/body-hash identity/projected Event count passed. Corrected serial retry also adds every Jira work-type mapping and ignored handlers.

## Latest lifecycle and provider checks

`20261006-cloud-enrichment-cases-b8ea023e`: disabled/failed provider leaves real keywords/importance and ACKs without vector; three-dimensional Event vectors and zero384 vectors are stored in JSON and receive the documented neutral relevance0.5. Removed synthetic graph embedding-write fault remains pending (#14), so ENR-02 fails recovery.

`20261006-cloud-archive-restore-4eb8c0ac`: synthetic FS archive failure preserves both real ledger documents; success archives/expires exactly one100-day-old document, preserves fresh content, lists/restores gzip JSONL, deactivates old dedup via public housekeeping, prunes the old graph Event through admin API, imports the restored archive through admin API and projects it again. Nested0.125 payload retained. GCS is not configured in this deployment and is not substituted for this FS result.

`20261006-cloud-ordering-races-28efabf7`: actual enrichment-first loses keyword/vector despite ACK (#29), and a later accepted/projected causal parent does not repair child CAUSED_BY (#30). Both are silent common engine dependency gaps confirmed on real Spanner. New GitHub issues published.

`20261006-cloud-live-pack-463a33c4` passed one real existing configured model call through Engram PackExtractionConsumer with output capped256, retry0 and timeout30s. A Decision and direct source-event DERIVED_FROM persisted on Spanner; group pending0. This is live pack-extraction smoke, not full live entity/user extraction or a model quality benchmark. No model switched, credential printed or alternative storage used.

`20261006-cloud-user-feedback-f83b33b9` and its attempted feedback-only follow-up have a harness import error: EventQuery is a runtime domain model, not an export of ports.event_log. Import precedes reset/cloud calls inside the phase; initial store/schema startup still occurred. Corrected import and retry of the actual user/feedback journey follows. These are not BOOT product defects.

## User and feedback closure checks

`20261006-cloud-user-feedback-09524f75` passed active/superseded preferences, category filter, pattern/skill/interest reads, export provenance, deletion with the other user/shared resources preserved, and feedback upper/lower clamps, duplicate/overlapping/missing IDs and distinct resubmission audits. `20261006-cloud-user-delete-recheck-fb617e0d` independently read the final cloud fixture and confirmed all five owned profile/preference/pattern nodes and their edges absent, shared nodes and other user profile present, user tombstone REDACTED, and all five ledger Events retained. USER-02 and FB-01 scoped assertions close. This uses public UserStore fixture writes for native interest read/delete and does not resolve actual extraction's interest evidence failure #20. Stable ordering/creation through all app routes remains additional USER-01 coverage.

The two earlier import-error starts and `...user-feedback-788c18fa`'s incorrect interest method argument count are harness errors preserved separately. In the latter, feedback already passed. Corrected public method signature and ordered-list document reads were used in the final complete user/feedback run. No runtime source edits.

Compatibility status is **failed/incomplete**, not signed off. Reconciliation06 attaches the latest scoped passes and failures without treating partial rows as complete. Issues23–30 are new real-cloud discoveries in this resumed batch; common worker/API defects are distinguished from Spanner adapter failures and synthetic failure injection. The known issue14 retry defect is also reproduced on enrichment.

Cleanup limits: all owned child processes/loops have finish receipts and no run is active. Both user databases and schemas remain; last source fixture retained for review. The normal Stores.close SDK-session leak is unresolved (#26), so complete remote SDK session deletion is not asserted. No unrelated sessions were killed. Existing untracked uv.lock is untouched; no src changes, commit or push.

## Renewed credential window and remaining ingestion/context checks

Credential window renewed separately at 2026-10-06 16:22:36 UTC; no refresh inside a phase. `20261006-cloud-ingress-completion-6772f3ca` incorrectly expected an unknown namespace to be refused; unknown namespaces are allowed, so that assertion is a preserved harness error. Corrected `...ingress-completion-197593e8` passed configured batch max3/mixed envelope indices/conflicting duplicates, import max6/chunk2/malformed lines/100-day history/occurrence ties/input ordering, committed-prefix synthetic failure and duplicate-safe retry, plus raw and decoded gzip byte limits. Representative configured boundaries are exercised, not physical default1000/500000 count loads. Batch still accepts a missing required pack key (#4); comment published. ING-05 closes its declared scoped assertions; OPS load/timeout closure is separate.

`20261006-cloud-context-completion-6c14d9b2` passed tied-timestamp pagination, exactly-once access increments and empty missing session. Distinct timestamps repeat the newest event on page2 and omit three older events: [#31](https://github.com/arunmenon/Engram/issues/31). Configured 30ms query budget responds200 after703ms around a controlled120ms SQL delay: [#32](https://github.com/arunmenon/Engram/issues/32). This is a synthetic delay around actual Spanner SQL, not an observed cloud outage. Shared GraphOperationReads contradicts initial newest-first ordering and ignores timeout_s; Spanner SDK reads have no propagated deadline. Both issues include evidence, acceptance criteria and review scope.

## Consolidation, extraction, pack-output and evaluation completion checks

`20261006-cloud-consolidation-completion-59bb437b` passed threshold exclusion/admission, two temporal episodes, public manual trigger handling, deterministic repeated summary IDs and twelve SUMMARIZES edges, same-worker overlap exclusion, and a scripted provider exception followed by a successful later cycle. Existing timer-cycle evidence remains separate. Provider failure is logged and the cycle stops; no immediate fallback, distributed overlap guarantee or stream-delivery retry improvement is claimed.

`20261006-cloud-evaluation-completion-3a6830b2` passed PDLC pending/explicit409, automatic pending metadata, TTL expiry, retaining the last cached answer on a synthetic read failure, initial-read exception, and recovery. Expanded `...evaluation-completion-97ec1d55` passed these under combined PDLC+CRM, both packs' explicit pending/admitted responses, unknown-intent refusal, status-route namespace/weight definitions, missing/failing evaluation sets, no-record state preservation and failed-set recording. This uses deliberately empty graph data for the negative gate; populated successful gates were previously tested. ART-05 and ONT-01 declared assertions now close.

`20261006-cloud-extraction-completion-4f303033` had a harness-only Stores.user_store attribute error; the actual UserStore implementation is Stores.graph. Corrected `...extraction-completion-1ba7b6cd` passed actual LLMExtractionClient invalid JSON/items/provider-outage empty fallback with no invalid writes and real delivery ACK, mid-session interval2, exact/alias entity MERGE with four source REFERENCES, and repeated native SAME_AS cluster writes without duplicates/self-links. Semantic-resolution/reranking quality and interest failure #20 are not hidden by these passes; EXT-01 retains partial status pending semantic branch coverage.

`20261006-cloud-workload-completion-660c44b3` passed a bounded24-event/three-session projection backlog and26 context requests across two independent SDK-backed app lifespans, max concurrency2. Warm24-sample p50=0.645s, p95=0.943s, p99=0.959s. Both app instances shared one OS process and used ASGI transport; first-context-call samples are not full cold server/network startup measurements. No production SLO or throughput capacity claim; OPS-05 remains partial.

`20261006-cloud-pack-completion-3ff72cde` had an oracle mistake: numeric55 is intentionally coerced to text by the shared proposal coercer, so one valid proposed Decision remained. The no-answer check then incorrectly asserted an empty global graph instead of no new writes. Neither is a new defect. Corrected `...pack-completion-06299088` passed list/nonlist answer refusal, object-valued text/wrong confidence/forbidden type/missing required field rejection with no writes and ACK, and no-answer ModelUnavailableError without graph mutation. Together with the earlier bounded confidence/trust/link-policy run, PEXT-01 declared assertions close. Live delivery retry remains failed #14.

FS archive failure/success/list/restore/admin import/reprojection was fully checked in `...archive-restore-4eb8c0ac`; LIFE-02 closes the configured deployment's conditional assertions. GCS is not configured and remains untested; FS success is not GCS evidence.

## Admin pruning failure versus successful worker deletion

`20261006-cloud-retention-completion-bce5e865` surfaced real TypeError comparing None with a float through ASGI exception propagation. Corrected HTTP capture in `...retention-completion-3dbff638` confirms warm/cold, dry/live admin prune all return500 for legitimate mixed-age Events. [#33](https://github.com/arunmenon/Engram/issues/33) documents absent node similarity scores, their actual location on SIMILAR_TO edges, and the cross-tier action calculation. The phase separately confirms real scheduled forgetting removes two low-score edges/preserves one high-score edge and deletes exactly one archive-age graph Event while preserving all six ledger documents. This is a product API failure, not a harness error or Spanner service outage. Cold API mutation and truncated-scan/large-delete corners remain unexecuted beyond the failure.

Reconciliation08 closes ART-05, ONT-01, PEXT-01 and the deployment-conditional FS archive row LIFE-02, marks LIFE-03 failed33, and attaches the new scoped evidence to still-partial EXT/CONS/OPS rows. No claim that a reproduced failed row has every corner covered. Issues31–33 are published; no runtime fix made.

## Implementation started: adapter prerequisites23/26/27

Runtime changes are now authorized and implemented locally. Codec27 escapes literal singleton float/escape markers recursively, keeps generated-column root fields, preserves legacy numeric marker decoding and makes legacy nonnumeric markers readable. Historical numeric-marker intent is irrecoverably ambiguous; no automatic historical rewrite. Schema23 reloads actual DDL, checks vector length/COSINE definition and READ_WRITE index state before serving. SDK ownership26 registers cleanup, bounds the released3.71 per-manager maintenance polling sleep to1s, clears owned pools/cached transports and closes clients, including startup failure. Optional dependency minimum now3.71. This isolated private SDK compatibility seam awaits independent review; upstream main has interruptible waits but the published latest3.71 still sleeps.

Local regressions initially reproduced three codec and three handshake failures. After implementation27 focused tests and five mocked registry-startup checks pass; Ruff passes. Actual cloud JSON/schema/shutdown rechecks `...json-ed39a292`, `...schema-9f308301`, `...shutdown-30786378` pass. Combined `...foundation-recheck-a3fcfb53` source fingerprints remain unchanged during execution; ledger literal markers, dimension refusal and actual SDK shutdown pass. Its graph-property assertion is a harness error: PackGraph deliberately serializes nested property maps as JSON text via stored_values; next attempt uses that contract. This is not a new codec defect. Current scenario matrix remains historical/pending acceptance reconciliation; no issue closed and independent review still required.

Multiplexed session lifecycle correction: the installed SDK deliberately skips remote deletion of server-managed multiplexed sessions. Runtime proof therefore checks local manager/session references released and maintenance thread stopped, plus closing owned transports. It must not assert remote multiplexed-session deletion. Ordinary pool sessions still use explicit deletion via pool.clear. No unrelated session is deleted.

## Implementation ingress safety15/16/28

`20261006-cloud-ingress-safety-recheck-ea36e04b` passed all three scoped checks: explicit timezone refusal/UTC storage across single,batch,import; gzip completeness and trailing-data refusal before append; transient503/Retry-After plus original-ID retries for single/batch, including actual committed-but-uncertain Spanner writes. Source hashes stayed unchanged during execution. Prior `...ingress-safety-recheck-62a07579` had a harness expectation error: all-invalid batch correctly returns422, not201. It is retained as a failed harness attempt, not a new product defect.109 local regressions pass. Issues15/16/28 updated and remain open pending independent review/full acceptance.

Corrected combined adapter prerequisite run `20261006-cloud-foundation-recheck-2b1052d9` passed all five scoped checks including graph node/edge nested values under the existing stored_values contract. Historical65-scenario matrix is not reclassified by these subchecks; full compatibility remains unaccepted.

## Admin pruning33 implementation recheck

`20261006-cloud-retention-completion-27c3df0c` passes all three real Spanner checks: warm preview/live count2 from actual edges, native worker deletion preserving retention rules, cold preview/live count1 and ledger preservation.52 local admin/forgetting regressions pass; four new tests reproduced the failure before implementation. Cold live deletion is now bounded to the selected ID batch. Warm edge preview uses a named count operation sharing the generic deletion selector. No alternative backend runner used. Issue33 updated and open pending independent review, large cloud-batch coverage and full acceptance; historical matrix unchanged.

## Astra implementation review completed — 2026-10-07

Independent low-effort review reproduced P1 legacy literal reinterpretation27 and P2 cancelled acquisition leaking the eventual database26; both accepted and pending correction. Five other fixes pass scoped review, with26/28/33 coverage limits. Reviewer independently ran27 tests and two deterministic probes; no cloud calls. See2026-10-07-astra-implementation-review.md and source-pinned request. No issue closed or compatibility sign-off.

## Priority-bucket bulk reviews completed — 2026-10-07

Astra low reviewed buckets1–3 separately (22 issues) with unchanged source. Reports and summary persisted. Additional scope:33 retained-prefix scan starvation/unbounded reads;29 replay clears enrichment;10 model candidates require projection readiness;18 authoritative predecessor plus endpoint repair;7 completeness scope joins must reject inadmissible links;6 proposed_only also requires complete checks;25 typed identity/session isolation;32 native stream/retry termination. Existing issues carry follow-ups. These reviews include local backend-neutral probes but no new real-Spanner runs.

## Pack-neutral design introspection — 2026-10-07

Plan now distinguishes native source translation, event-owner contract validation, explicit cross-pack rule subscribers and independent worker applicability. Unknown/unloaded domain admission through the legacy open namespace path is reproduced by pure registry probe20261007-local-pack-neutral-design-01; strict new-domain acceptance needs explicit legacy exemptions. Added unfamiliar third-pack/no-engine-edit coverage and raw-source versus validated-event distinction. No runtime changes or cloud acceptance; new design not independently reviewed.
