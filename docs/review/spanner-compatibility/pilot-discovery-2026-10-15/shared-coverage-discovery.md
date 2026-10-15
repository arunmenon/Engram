# Shared pilot coverage discovery — 15 October 2026

Read-only discovery at `92a6053`, for Tenant A (Core+User+Memory) and Tenant B (Core+PDLC+Memory). This proposes coverage and prerequisites; no pilot, database operation, test, implementation or GitHub mutation was performed. Applied lean-exploration and smallest-complete-fix guidance. Source inspection and recorded acceptance establish the starting point; proposed probes below are unexecuted.

## Recommendation and evidence boundary

Use several connected real-provider stories per tenant spanning the diverse families in the combined inventory, then attach shared boundary/failure sequences. Reuse those narratives' Events, actors, sessions and artifacts for the probes below. Do not create eighteen independent synthetic datasets or count every read/assertion variant as another user journey. A useful journey must change a user's knowledge/state and recover it with evidence; authentication, truncation and failure checks are probes attached to that journey.

The accepted [tenant isolation checkpoint](../tenant-isolation-verification.md) contains **184 main +12 restart assertions**, a fresh-process audit and all ten actual worker loops. External session-extraction, pack-extraction and summary model outputs were frozen. It proves bounded public routing, persistence, evidence and lifecycle behavior, not real-provider extraction, summary, semantic matching or paraphrase quality. Earlier [User acceptance](../user-attachment-verification.md) includes real-provider extraction, but does not substitute for simultaneous real-provider pilot use through the public dispatcher. Keep provider-quality results and deterministic fault-injection results separate in the final report.

The [current pilot brief](../2026-10-08-controlled-pilot-discovery-brief.md) supersedes its historical no-Memory-producer/public-factory-disabled descriptions. [Memory verification](../memory-episodes-verification.md), [composition verification](../pack-combination-verification.md) and the tenant checkpoint establish bounded producers and reads. APIs/workers are currently stopped; no reachable pilot deployment or provider budget is presumed.

## Existing processing and read surfaces

Five shared loops apply selected capabilities, rather than one loop per pack:

| Loop | A and B coverage | Distinguishing proof |
|---|---|---|
| Projection (P) | Core Event graph; explicit Memory actions in both; PDLC projection in B | Exact typed nodes, canonical identities, edges and lifecycle support, not merely ACK |
| Session extraction (S) | Core Entities in both; UserProfile/Preference/Skill only in A | Actual model request/result, validated output and canonical REFERENCES; B has no User output |
| Enrichment (E) | Event annotation and optional embeddings in both | Stored keywords/vector and ordering convergence; keywords/default importance are not semantic understanding |
| Consolidation (C) | Summary and Memory Episode in both | Recorded cadence/threshold, actual summary provider, exact immutable membership and completed writes |
| Pack extraction (X) | Only matching selected extraction profiles; supported PDLC prose in B | Matching profile invoked and validated proposal applied; unmatched input/ACK does not establish extraction |

[`ProcessingProvider`/`ActiveBundle`](../../../../src/context_graph/domain/pack_bundle.py) declares `event.project.v1`, `event.enrich.v1`, `entity.extract.v1`, `summary.consolidate.v1`, `event.retain.v1`, explicit `memory.episode.v1`/`memory.belief.v1`/`memory.goal.v1`, `user.extract.v1` and pack projection/properties/extraction handlers. A resolved bundle validates engine vocabulary, not external provider readiness or authorization. Event retention is a capability, not a sixth loop to introduce into this pilot.

Read contracts must remain distinguishable:

- [`GET /v1/context/{session_id}`](../../../../src/context_graph/api/routes/context.py): bounded session context, optionally query-guided. It is not exhaustive historical search.
- [`POST /v1/query/subgraph`](../../../../src/context_graph/api/routes/query.py): intent-aware Event/entity retrieval, explicit seeds, graph/vector/keyword fusion and optional query expansion. Configured providers and indexes determine available channels. Natural wording alone does not prove vector participation.
- [`POST /v1/query/artifacts`](../../../../src/context_graph/api/routes/artifacts.py): explicit artifact seeds, domain keys/numbers, text fallback and bounded domain traversal. [`ArtifactRetriever`](../../../../src/context_graph/retrieval/artifacts.py) has no artifact vector seed channel; unsupported semantic discovery must be reported honestly.
- [`/v1/users/{user_id}/...`](../../../../src/context_graph/api/routes/users.py): direct User reads currently require admin via application role policy. Compare authorized specialized reads with `intent=personalize`; define normal developer role access without silently granting admin.

Memory creation provenance deliberately anchors to creation, while typed/public evidence retains lifecycle sources. PDLC artifact provenance can point to the newest observing Event. Freeze these different contracts; do not require every artifact's provenance pointer to change on every update. Episode context considers at most ten snapshots and 500 aggregate member references; truncation must be visible and cursor advancement is not supported for this tenant path.

## Proposed shared journeys and probes

Priority: **P0** must be resolved or explicitly accepted before developer access; **P1** required for a useful declared pilot, with a scope decision if unavailable; **P2** optional extension. “Established” means bounded prior evidence exists, not that the proposed real-provider sequence passed. “Conditional” means exact configuration/contract must be frozen first. Every row requires authenticated HTTP writes → ledger → actual applicable loops → graph → Engram reads; storage audits supplement this path. Forbidden effects exclude documented read access counters and declared asynchronous baseline work, which must be accounted for separately.

### C01 — Clean-checkout onboarding and role separation — P0

**Sequence:** From the documented launch path, an operator supplies fixed catalog/bindings, credentials, trusted producer mapping and provider settings; start dispatcher plus five loops per tenant. A normal `api` developer submits a small observation and reads supported context. A separately scoped admin reads the User profile and tenant stats. Retry direct User read with `api` only.

**Expected/forbidden:** Document usable developer commands, correct tenant/capability identities and explicit authorization refusal for the last read. No private harness repair, automatic database adoption, generic admin grant or credential-based database override. **Verdict/prerequisite:** Conditional; publish launch/topology/role and `agent_id` mapping, reachable endpoints, TLS/access arrangements, provider credentials/cost bounds and safe retained-data preparation. **Axes:** lifecycle bootstrap; P/S/E/C/X readiness; role/read contracts.

### C02 — First real-provider write, useful read and processing visibility — P0

**Sequence:** Interleave A's Alice preference/interest introduction and B's supported design/decision prose. Capture provider requests/results and validation outcomes. Read each Event immediately after HTTP acceptance, then poll declared processing criteria and retrieve A's attributed preference/profile and B's extracted decision plus supporting Event.

**Expected/forbidden:** Explain accepted, applicable, processed, pending, failed and acknowledged separately. Exact owner, typed artifacts and canonical Entity links; a no-op X ACK in A is acceptable only when labeled inapplicable. No claim of successful extraction from acceptance, zero lag or ACK alone. **Verdict/prerequisite:** Bounded components established; simultaneous real-provider quality unproven. Freeze supported prose/profile and provider config, thresholds and per-stage diagnostics; Monitoring 403 needs an operational alternative. **Axes:** ingest→all applicable loops→reads; provider quality; observability.

### C03 — Exact identity versus wording discovery — P1

**Sequence:** Reuse C02 and a connected B requirement/PR. First read by exact Event/artifact seed; then domain key/title wording; then a meaning-preserving paraphrase with no ID. Run A earlier-session question similarly through subgraph/context. Preserve every query and classify actual seed channel.

**Expected/forbidden:** Report exact, lexical and paraphrase outcomes separately with attributable evidence and unrelated controls excluded. A successful explicit seed cannot rescue failed discovery. Do not describe B artifact text traversal as vector search or guarantee unrestricted natural language. **Verdict/prerequisite:** Exact/key/text established; paraphrase quality exploratory, with predeclared usefulness criterion and honest miss/unsupported verdict. **Axes:** read mode, multi-session, P/S/X output usefulness.

### C04 — Semantic Entity discovery with a real embedding provider — P1

**Sequence:** Introduce a distinctive Entity in each narrative; ask a related query without its exact token. Compare a supported vector-enabled read with a labeled channel-disabled control or recorded channel diagnostics using the same saved graph.

**Expected/forbidden:** Demonstrate real stored embeddings, actual vector candidates and grounded returned Events. No credit for a lexical hit alone; no ANN quality/load or artifact-vector claim. **Verdict/prerequisite:** Conditional on configured embedding/search/query-expansion support and inspectable channel evidence; semantic quality not established by frozen-provider acceptance. **Axes:** E/S, query provider, vector versus text.

### C05 — Two owners inside A, independent sessions and contexts — P0

**Sequence:** Alice and Bob receive overlapping interests and opposite response preferences using distinct declared `agent_id` mappings. Positively retrieve each, then ask Alice's personalization and session-scoped Memory questions; include Alice's second session and a distinct preference context.

**Expected/forbidden:** Alice's owner-scoped answer excludes Bob; same owner across sessions/context behaves according to the explicit requested scope. Positive Bob control proves absence is not empty storage. Tenant credentials do not authenticate the human behind arbitrary `agent_id`; generic tenant searches are not promised owner-exclusive unless the endpoint contract says so. **Verdict/prerequisite:** Bounded User/Memory ownership established; application actor mapping required. **Axes:** owner isolation versus tenant isolation; S/P; User/personalize/Memory reads.

### C06 — Cross-tenant collisions and foreign-only controls — P0

**Sequence:** Use identical Event/session/agent/Entity/Memory IDs and overlapping wording on A/B, with distinct content. Add one foreign-only B Event/artifact. Retrieve common and foreign-only IDs and text on each tenant while both remain active.

**Expected/forbidden:** Same IDs resolve only within the selected database; B's foreign-only positive becomes a non-leaking A empty/not-found/unsupported response per route. No foreign nodes, sources, edges, counts or existence hints. A's disabled PDLC route is separately labeled capability refusal, not the sole isolation proof. **Verdict/prerequisite:** Established bounded isolation; freeze exact route/status expectations. **Axes:** routing, all loops, exact/text/public reads, positive/negative controls.

### C07 — Same-identity retry, conflicting duplicate and malformed input — P0

**Sequence:** Replay one unchanged A and B Event after completion, then reuse each ID with changed content; send malformed Memory/PDLC contract and a disabled-pack input. Read exact ledger identity, resulting artifact support and receipt state.

**Expected/forbidden:** Unchanged retry follows idempotency contract; changed content conflicts; invalid/disabled input refuses without accepted ledger entries or artifact/support changes. Do not claim canonicalization of independently worded model results. **Verdict/prerequisite:** Established HTTP/receipt cases; cached-worker replay limitation #18 requires targeted assessment if retry can re-enter that path. **Axes:** admission, P/S/X receipts, identity, evidence counts.

### C08 — Correction, revision and temporal truth — P1

**Sequence:** Correct Alice's preference in one exact context; state/confirm/correct an explicit Memory Belief; revise B's approved design without reapproving the revision. Read current values, allowed history and each version's supporting Events.

**Expected/forbidden:** Intended preference is superseded, other context unchanged; Belief is an attributed assertion with declared confidence; revision does not inherit approval. No stale current value, false truth claim, unsupported automatic prose correction target or uniform newest-source provenance assumption. **Verdict/prerequisite:** Bounded building blocks established; freeze actual correction/version contracts and queries. **Axes:** P/S, current/history, context, lifecycle provenance.

### C09 — Explicit Goal transitions and absent automatic links — P1

**Sequence:** Create and complete or abandon a Goal on each tenant through explicit supported actions. In B, separately ingest passing tests/merged PR without a Goal action and ask Goal and artifact views.

**Expected/forbidden:** Declared transitions and evidence retrieved; tests/PR do not implicitly complete a Goal or create a requirement→Belief relation. Domain and Memory meet via supporting Events unless a supported explicit rule adds a link. **Verdict/prerequisite:** Explicit Memory established; automatic relationship unsupported. **Axes:** P, terminal lifecycle, negative inference, Memory/artifact reads.

### C10 — Late event and Episode snapshot history — P1

**Sequence:** Produce two timed activity clusters, allow configured consolidation, read Episodes/Summaries; deliver a late bridging Event and consolidate again. Ask earlier-session/timeline questions and retrieve both old and new snapshots.

**Expected/forbidden:** Exact saved membership/history persists, new grouping uses declared event-time policy, sources remain attributable and Summary text supported. No mutation of old membership, dropped late Event or extrapolation beyond candidate limits. **Verdict/prerequisite:** Bounded Episode snapshots established; record cadence/threshold/time basis and real summary provider. **Axes:** C/P, event time versus arrival, summary quality, historical reads.

### C11 — Missing evidence, unknown answers and trust — P1

**Sequence:** Ask B which requirement has an approving review/test when one has only a proposed link, one has a non-approving review and one lacks any link. Ask a completely nonexistent artifact/claim on both tenants. Include an untrusted source under existing trust contracts.

**Expected/forbidden:** Distinguish `no_link`, `proposed_only` and confirmed qualifying evidence; “no recorded qualifying evidence” is bounded to scanned scope, not proof no real-world review exists. Untrusted data is suppressed or visibly labeled according to the request. No fabricated approval, inference from skipped/failing tests, leaked foreign existence or unqualified exhaustive absence. **Verdict/prerequisite:** Artifact completeness/admission supported; freeze trust/source mapping and exact scope/limits. **Axes:** P/X, negative evidence, unknown, trust, completeness reads.

### C12 — Answer bounds and evidence closure — P0

**Sequence:** Read the same real narrative with sufficient budget, then `max_nodes=1` and one small declared depth bound; compare membership, truncation and evidence references. Add the ten-snapshot/500-member Episode bound only if the real fixture reaches it; otherwise cite prior bounded proof.

**Expected/forbidden:** Visible truncation whenever a bound omits candidates; no dangling returned graph edges, invented full-history/completeness claim or silent continuation promise. Evidence identifiers must resolve in the selected tenant; omission must not be reinterpreted as absence. **Verdict/prerequisite:** Established bounded truncation; freeze response contract and query limits. **Axes:** all reader types as applicable; budget, source integrity, unknown versus omitted.

### C13 — Concurrent writes, delivery state and useful read readiness — P0

**Sequence:** Interleave A/B writes and reads; briefly hold one applicable stage with a labeled deterministic barrier after acceptance. Resume, then require exact outputs and saved consumer-group/cursor/pending/ACK evidence per tenant before declaring complete.

**Expected/forbidden:** Readiness requires completed applicable work plus exact graph/source observations; lag zero alone is insufficient (the accepted restart initially observed this race). Same group names/IDs do not cross databases. No double support/application or falsely successful early read. **Verdict/prerequisite:** Bounded concurrency established; freeze polling predicates, timeouts and diagnostic access. Exact concurrent access-counter increments are not established by #61 and are not a new pilot guarantee. **Axes:** all loops, accepted/processed/ACK distinction, simultaneous reads, isolation.

### C14 — Real-provider failure visibility — P0

**Sequence:** For a fresh matched extraction request, cause an actual configured-provider failure in a bounded approved way (for example a dedicated denied test credential, with successful independent provider control). Capture actual response/error and worker/API diagnostics; restore authorized configuration and observe the declared recovery policy using supported delivery behavior.

**Expected/forbidden:** Record accepted Event separately from failed extraction; never return fabricated provider output or success. Other tenant stays usable. Credential/secret contents stay out of artifacts. Do not promise retry/redrive recovery until the exact policy is verified. **Verdict/prerequisite:** Not established by frozen providers. Requires dedicated configuration isolation, cost/time budget, observable outcome and a predeclared recovery/stop procedure. **Axes:** S/X/provider boundary, pending/failed, tenant availability. This is a real failure probe, not a quality journey or synthetic exception.

### C15 — Deterministic dependency and ordering fault probe — P1

**Sequence:** Separately label scripted faults: hold Event projection while enrichment sees accepted input; or submit a supported Memory confirmation before its parent. Record pending state, resume prerequisite and require converged Event annotations/lifecycle evidence.

**Expected/forbidden:** No premature ACK/completion claim, missing enrichment or orphaned support. A finite stop is mandatory if dependency never appears; existing general retry/dependency policy is not assumed solved. **Verdict/prerequisite:** Specific enrichment/Memory cases established; general #14/#19 permanently missing-dependency handling remains separate. Select one relevant ordering case rather than expanding to all failure permutations. **Axes:** P/E, receipts/pending, eventual convergence; deterministic faults only.

### C16 — Cooperative stop/restart and response fencing — P0

**Sequence:** With both narratives active, allow in-flight work, request cooperative shutdown, verify joins and stable post-stop fingerprints; restart exact owners/bundles and process fresh Events. If demonstrating tenant freeze, hold an actual read before release and freeze A while B reads continue; reuse the accepted bounded control procedure.

**Expected/forbidden:** No post-stop background mutation; exact final writes/sources visible after restart; stale owner/epoch ACK/startup/read refuses. No SIGKILL, partition, arbitrary pending-recovery or durable-draining guarantee inferred. **Verdict/prerequisite:** #60 and tenant restart/fence bounded proofs established; retain diagnostics and precise completion predicate. Freeze/reactivation is operator-controlled and only included if authorized in execution scope. **Axes:** all loops, lifecycle termination/restart, stale authority, read release.

### C17 — Spoofed routing, invalid roles and unsupported paths — P0

**Sequence:** Attach spoofed tenant/database hints to otherwise valid and invalid credentials, use wrong roles, then exercise documented unsupported tenant cursors, streaming import, native unbound webhook and admin maintenance paths with before/after audit.

**Expected/forbidden:** Explicit refusal before effects, no tenant fallback or global metadata disclosure. Query-string and JSON cursor variants are assertions of one unsupported-path probe; do not count as separate journeys. Maintenance includes prune/replay/reconsolidate; unsupported global metrics must not leak. **Verdict/prerequisite:** Established bounded refusal; freeze route/status matrix and compare state after quiescing unrelated activity. **Axes:** ingress, role/routing, unsupported control surfaces, forbidden writes.

### C18 — Evidence audit and independent repetition — P0

**Sequence:** After C02–C17, save input/response journals, exact expected/actual nodes/edges/evidence, provider settings/results, source/bundle hashes, processing/failure observations and final owners/fingerprints. Have a fresh process perform read-only reconciliation and a developer repeat the supported reads with their documented role.

**Expected/forbidden:** Creation/current/history/support pointers match their contracts and resolve to actual accepted source Events. Distinguish retained prior data from newly submitted counts. No graph repair, omitted failed attempt, evidence overwrite or claim of independent real-provider quality from a raw-table match. **Verdict/prerequisite:** Audit mechanism established; developer-readable documentation/access and reproducible provider evidence still required. **Axes:** end-to-end evidence integrity, role usability, source fidelity, repeatability.

## Small complete sequence and stop decisions

1. **Readiness:** C01; freeze contracts and fixtures for two connected narratives; resolve diagnostics/provider prerequisites. Do not spend on a broad backlog or rerun five pack configurations.
2. **Useful real-provider narratives:** C02 with C03–C05 and C08–C11 attached to A/B. Include one matched B pack extraction, real A User extraction, real Summary text, explicit Memory actions and canonical Entity evidence. C04 is required only for a declared semantic/vector promise; otherwise preserve an honest scope limitation.
3. **Shared safety/operability probes:** C06–C07, C12–C17 reuse the same graph, with isolated extra Events only where failures/late data require them. Real-provider failure C14 and scripted ordering C15 have separate results.
4. **Closure:** C18, independent review and stakeholder walkthrough. A required missing/failed probe blocks that particular readiness claim. Preserve failures and retained datasets. Execution/onboarding is separately approved; this discovery does not start either.

Use a coverage ledger with one narrative ID plus C-probe IDs, actual read modes and applicable worker outcomes. Report narrative count, probe count and assertion count independently. A different wording, limit, HTTP field or tenant mirror is an assertion variation unless it introduces a distinct lifecycle or user outcome.

## Known issues and exact remaining gaps

These are **local recorded states**, not a fresh live GitHub audit. Reconcile relevant current records before specification/execution; no issue writes were made.

| Record | Current local evidence and pilot implication |
|---|---|
| #18 cached projection predecessor/replay | [Enrichment verification](../enrichment-ordering-verification.md) and [shutdown reconciliation](../consolidation-shutdown-verification.md) retain OPEN; fresh-worker replay does not prove cached replay. C07/C13 must assess the actual retry path; no blanket reliability claim. |
| #14/#19 delivery/missing-document policy | Enrichment verification explicitly excludes general policy; retry caps backoff rather than elapsed dependency wait, so an absent prerequisite can wait until stop. C15 needs bounded timeout/failure visibility. Do not open an all-recovery workstream automatically. |
| #60 consolidation shutdown | **CLOSED**, superseding older User/enrichment open notes; [shutdown verification](../consolidation-shutdown-verification.md) provides bounded cooperative/synchronous SDK fencing proof. C16 is a real-journey regression, not an unresolved blocker or forced-kill demand. |
| #61 UUID Event subgraph access | **CLOSED**, superseding earlier enrichment notes; [access verification](../subgraph-access-verification.md) supports sequential exact increments. Concurrent read/modify/write counters remain outside that proof. |
| #62 canonical Entity identity; #20/#59 User provenance/personalization; #29 enrichment | Closed bounded defects in composition/User/enrichment records. Reuse exact canonical-ID, owner/evidence and ordering checks within the narrative; do not list stale defects as blockers. |
| #43/#34/#39/#41/#42 | Tenant reconciliation records OPEN umbrellas/broader scopes despite accepted bounded checkpoints. Open does not mean all work blocks this pilot; use demonstrated missing criteria only. |
| Cloud Monitoring export 403 | Current tenant/composition records retain failure. Define a bounded operational alternative that identifies per-Event accepted/pending/failed/processed outcomes, or block access if required visibility is absent. |
| Provider quality, launch, roles and unsupported semantic expectations | Real simultaneous provider journeys, clean-checkout onboarding and normal developer usability remain unproven. Direct User admin access and B artifact text-only seeding need explicit product decisions, not workaround assertions. |

Remaining out of scope: hierarchy policy #49, ANN/load stress #48, migration, hot pack switching, every pack combination, native webhook/import/cursor implementation, generalized maintenance, general pending/crash recovery and forced termination. If a participant needs one, record a bounded scope decision rather than silently incorporating the backlog.
