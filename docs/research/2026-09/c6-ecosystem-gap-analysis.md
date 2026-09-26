# Gap analysis: from the PAI Context Graph to a C6 memory ecosystem

**Date:** 2026-09-26. **Inputs:** the Jetstream grounding document ([transcription](pdlc-grounding/jetstream-reference-transcription.md)), this pack's research ([README](README.md)), the evidence catalogue ([D8](paper-digests.md)). **Level:** architecture and components, not code. A code reset is assumed; what this repo has is treated as *capabilities and design decisions*, not files. **Assumption (set 2026-09-26):** a System One decision model is available inside PayPal, either Jev under an enterprise arrangement or an open equivalent hosted locally. Data-egress and vendor questions are out of scope for this analysis.

**Naming.** "PAI Context Graph" (PCG) is this repository. "AMS" is AI Tech's `agenticmemoryservice`, which the programme calls Engram. "Gateway" is the C6 adapter layer that the document says does not exist anywhere.

---

## 0. Note after the refresh addendum (same day)

The [refresh addendum](pdlc-grounding/jetstream-refresh-addendum-transcription.md) adds two facts. Neither reduces the scope of this analysis; both add integration points to it.

- **Sanctum MCP Gateway** (PAI, live on BYOA) has `retrieve` and a WIP `write`, an `evidence[]` response with a `validity` block, rank-fused scores, `domain` default-open, `content_type` that includes `skill`, no `snapshot`, no receipts, and permissioning "under consideration". It is an early PAI artefact that proves the MCP-projected surface works and gives a response shape worth adopting. It is not a gateway in the sense of §3: no registry, no scope resolver, no fusion across backends, no snapshot composition, no receipts. **Every layer and component below still has to be built.** Sanctum is where the L9 MCP projection and the response schema should converge, so the two PAI efforts ship one surface rather than two.
- **DeepInsights** is a production backend behind Endzone and GSE with strong per-call scope, mandatory provenance and absolute read/write separation, ~50 tools, no snapshot. It is a first-class **registry entry** for `kind=document` over code and wikis and the right second backend for the swap test. It is not a gateway and does not want to be one.

So the plan is unchanged in shape: the PCG's ledger is the core; the ten layers and sixteen components are built around it; and the result is **married to what PayPal is already building** at three seams: Sanctum for the MCP surface and response schema, DeepInsights and AMS as registered backends with manifests, and the harnesses through C4 injection. `snapshot` is now confirmed absent in three independent places, which makes it the clearest thing the ledger contributes, but it is one component of sixteen, not the whole contribution.

## 1. The target is an ecosystem, not a store

The document defines C6 backward from its callers: one interface, declared scope per call, integrate-not-absorb, backend independence proven by a swap test, three verbs, `snapshot` as the largest gap, a normalised response of content + provenance + freshness + confidence, a fault-adjudication rule, and a knowledge-gap write-back path. It also names at least eight knowledge holders that already exist and will keep existing: AMS, DeepInsights, `knowledge-service`, `biso_knowledgebase`, `dejavu-toolkit`, `eaintelligencemcpserv`, Endzone's embedded KB, and the systems of record themselves (Jira, Confluence, Slack, GitHub, runbooks, backlog KB, skill packs).

So the target is a **federated memory stack** with ten layers. Every layer is required by something the document says; none is optional.

| # | Layer | Required by (document) | What it does |
|---|---|---|---|
| L0 | Systems of record | §4.1 "the store stays where it already lives" | Jira, Confluence, Slack, GitHub, runbooks, backlog. Never absorbed. |
| L1 | Capture | C8 (OTel GenAI spans), §2.2 assumptions ledger, §2.5 Operating signals | Harness hooks, span ingest, assumptions-ledger writes, Outer Loop outcome events (escapes, RCA, CFR, disposition) |
| L2 | Ledger | §4.4 `snapshot`, §4.7 replay | Immutable, positioned, tenant-scoped event log. The substrate for point-in-time reads and receipts. |
| L3 | Backends (hubs) | §4.2, §4.6 "each backend keeps its own storage and retrieval" | PCG graph, AMS, DeepInsights, knowledge-service, biso, Endzone KB, dejavu catalog, ticket corpus |
| L4 | **Federation gateway** | §4.1–4.6 (the whole C6 proposal) | Scope/entitlement, routing by kind+scope, fan-out, fusion, rerank, normalisation, snapshot composition, receipts, injection gate, budgets |
| L5 | Read-time curation | §3.3 Spec step "what knowledge a run needs before Design starts" | Task-conditioned briefing from raw evidence (JITMem, digest D6) |
| L6 | Write and certification | §4.4 write, §4.7 knowledge-gap → candidate Fact, §5.1 "both loops contribute" | episode → candidate fact → certified fact; supersession; gated updates |
| L7 | Evidence and eval (C9) | C9, §3.4 fault adjudication, §4.5 pinned reviewer config | Receipts joined to outcomes; adjudication; buildability with pinned snapshot; noise floor |
| L8 | Governance | C10 identity, `scope.classification_tier`, "entitlement-aware" | Entitlements, classification tiers, retention, GDPR, audit, staleness sweeps, RSI-L2 oversight |
| L9 | Harness adapters | C4 injection, C5 MCP-as-CLI, Part 6 | Courier, Endzone, GSE integrations; MCP-projected CLI in front of REST |

## 2. Where the PCG stands, layer by layer

Legend for *Gap*: **Have** (design exists and holds up), **Extend** (exists, needs a contract-shaped change), **Absent** (nothing to build on). *Elsewhere* names an existing hub that already has the piece, since the document's method is to reuse what exists.

| Layer | C6 requirement | PCG today (as design) | Gap | Elsewhere | Typed decision? |
|---|---|---|---|---|---|
| L0 | Integrate, do not absorb | Ingests agent events only; no SoR connectors | **Absent**: Jira/Confluence/Slack/GitHub/runbook connectors that emit *events with source position* rather than copies | Endzone has Confluence/GitHub/runbook ingest; Courier has Jira/Slack fetch | No |
| L1 | OTel GenAI spans as the capture format (C8) | Own event envelope (ADR-0004), Beacon-style JSONL noted as candidate | **Extend**: span → event mapping is the ingest adapter; envelope stays | Beacon (OTel-normalised) | No |
| L1 | Assumptions ledger | Nothing | **Absent**: an `assumption` record type (ambiguity, resolution, inferred-vs-asked, spec/tribal flag) written at self-review | Nobody | A1-style grounding check |
| L1 | Outer Loop outcome events | `task_key`, `task.outcome` proposed (discovery P4), not built | **Absent**: escape, CFR, RCA, disposition, spec-attributed fault, per-stage C9 signals with a join key | Datadog holds the raw telemetry | No |
| L2 | Positioned immutable ledger | Redis Streams, Lua dedup, `global_position`, hot/cold tiers | **Have** (fix the three scale defects) | AMS has none of this; Endzone has none | No |
| L2 | Tenant / scope on every record | Tenant prefix (ADR-0018), entity resolution tenant-blind | **Extend**: scope = tenant + space/domain + classification tier + caller identity | AMS has space-scoping and certification | No |
| L3 | PCG as one backend | Graph projection, intents, decay, Atlas | **Have** as a backend; **demote** as the read surface. The graph answers lineage, supersession, entity and "why" questions; it is not the default `retrieve` | — | No |
| L3 | Other backends | None registered | **Absent**: backend registry with capability manifests (kinds served, scopes, freshness SLA, snapshot support, entitlement model) | Each hub is a manifest entry | No |
| L4 | One interface, three verbs | REST `/v1/events`, `/context`, `/subgraph`, `/lineage` | **Extend**: `retrieve/write/snapshot` as the public verbs over the full gateway (§3); converge the MCP projection with Sanctum's so PAI ships one surface | Sanctum (two verbs, early, live); DeepInsights (many tools, backend) | — |
| L4 | `scope` mandatory, entitlement-aware | Tenant only | **Absent**: scope resolver against C10 identity and classification tiers; least-privilege intersection across hubs (Sanctum is default-open here too) | DeepInsights does per-call scope well (model to copy) | Deterministic only. **Never a model call.** |
| L4 | Routing by `kind` + scope | Intent classifier (8 intents, keyword) | **Extend**: intent becomes one input; route is a *closed menu over the registry* | — | **Yes** (Choice over backends, see §3) |
| L4 | Fusion across backends | Single-store retrieval | **Absent**: RRF k=60 across backends, then one listwise rerank | Hindsight, Jev-Mem designs | **Yes** (listwise Choice, ≥1 result) |
| L4 | Response normalisation: content, provenance, freshness, confidence | Atlas node has content + provenance + scores | **Extend**: adopt Sanctum's `evidence[]` + `validity{status, last_updated, verified_by, expires_at}`; the staleness audit (A6) writes `validity`; `score` stays rank-fused | Sanctum (better specified than the reference architecture) | **Yes** for confidence (Score), with a local fallback |
| L4 | `snapshot(scope, as_of)` | Stream position exists; no verb, no manifest, no signing | **Extend** for PCG-held data (position pin); **Absent** for external backends (materialise-and-sign) | dejavu-toolkit's Ed25519 versioned catalog | No |
| L4 | Receipts and replay | Nothing | **Absent**: retrieval receipt (scope, snapshot, backends asked, items served, distributions) as a ledger event; replay tool | Nobody | No |
| L4 | Injection gate on served memory | Nothing | **Absent** (Jev B5) | jevmem pattern | **Yes** (Noul) |
| L4 | Budgets, stop rule | `max_nodes`, `max_depth` | **Extend**: per-call token/latency budget; sufficiency stop across federation rounds | Jev-Mem design | **Yes** (B4) |
| L5 | Task-conditioned briefing | Consumer 4 summaries (write-time) | **Extend**: `curate` step over raw evidence at Spec time; summaries become cache | Nobody | Retrieve-or-not gate (B0) |
| L6 | fact vs episode write; certified callers only | Everything is an event; extraction self-certifies | **Extend**: `write(kind=episode)` = append event; `write(kind=fact)` = proposal → gate → certified, with source class and reason | AMS has a certification path | **Yes** (A1 acceptance, A5 supersede) |
| L6 | Knowledge-gap → candidate Fact | Nothing | **Absent**: adjudication result becomes a proposal on the certification path | — | **Yes** (adjudication) |
| L6 | Supersession, never delete | Belief/SUPERSEDES designed, never created | **Extend**: two-signal supersede, old stays, excluded from default recall | Endzone `inactive:` flags | **Yes** (A5) |
| L6 | Procedural knowledge | Workflow nodes designed, never induced | **Extend**, but note: skills do **not** flow through C6. Workflows surface as `episode`/`fact`, not skill files | lep-tools handles skills | Comparative induction (D2) |
| L7 | Fault adjudication | Nothing | **Absent**: three-way label (spec / tribal / harness) from assumptions ledger + replayed receipt | — | **Yes** (Choice, the cleanest one in the set) |
| L7 | Buildability with pinned snapshot | Nothing | **Absent**: eval harness that pins model, prompt, snapshot id, thresholds | outer-loop-problems.md defines it | Jev as pass/fail judge (Sentry pattern) |
| L7 | Outcome-linked receipts | Nothing (H4) | **Absent** | — | No |
| L7 | Noise floor, held-out, one change per round | Eval harness leaks labels (V1–V8) | **Replace** | — | No |
| L8 | Classification tiers, entitlements | Tenant policy (ADR-0016/0029), GDPR crypto-shred | **Extend**: tier is a scope field and a routing constraint | C10 holder | No |
| L8 | Staleness sweep, provenance per item | Decay by age only | **Absent** (A6, P5) | jevmem pattern | **Yes** (Noul batch) |
| L8 | Oversight | None | **Absent**: blocked-episode tagging, guardrail-trigger rate, one check outside the write path | — | No |
| L9 | C4 capability injection, no credentials in harness | SDK/plugins call REST directly with keys | **Extend**: platform-injected scoped capability; MCP-projected CLI (C5 pattern) | MCP Hub | No |
| L9 | Courier adapter | None | **Absent**, and small: resolve ticket links through C6, store snapshot id in the Spec | Courier stubs exist | B0 gate lives here |
| L9 | Endzone adapter | None | **Absent**: Endzone KB as a registered backend *and* Endzone as a caller; the swap-test pair | Endzone KB | B0 gate |
| — | Conformance kit (swap test) | None | **Absent**. **This is the deliverable that makes anything "C6".** | — | No |

**Count:** 3 Have, 14 Extend, 17 Absent. The absent set is mostly *around* the store: capture, federation, receipts, adjudication, eval, adapters. That is the point: the PCG's ledger and provenance are the right core, and almost everything that makes it an ecosystem is missing.

## 3. The federation gateway, and where a System One model goes in it

The document's rule is that memory systems stay independent and the store stays where it lives. So the gateway is not a consolidation; it is a **query planner over a registry of heterogeneous backends** with a normalised output and a snapshot discipline. Its components:

1. **Backend registry.** One manifest per hub: kinds served (fact/episode/document), scopes and tiers it may serve, freshness SLA, whether it supports `as_of` natively, its entitlement model, cost and latency profile, health. Manifests are versioned and are part of the snapshot.
2. **Scope resolver.** Caller identity (C10) → allowed spaces, tiers, backends. Deterministic. Runs first, and its output is the *closed menu* every later decision chooses from.
3. **Planner.** Given (query, scope, kind, budget): which backends, in what order, with what per-backend budget, how many rounds. This is where the harness's intent (LLM-set) meets per-item choices (decider-set), the planner + decider split that won in the evidence.
4. **Fan-out and fusion.** Parallel calls with budgets; RRF k=60; deterministic dedup by content hash and source id.
5. **Rerank and admission.** One listwise decision over the fused pool; always ≥1 item; no "none" option; pruning off by default.
6. **Normaliser.** Every item → {content, provenance (source system, source id, source position/version, backend, retrieved_at), freshness, confidence, ontology tags (dims 3, 5, 6, 10)}.
7. **Snapshot composer.** For backends with positions (PCG ledger, dejavu catalog): pin the position. For backends without (Confluence pages, most hubs): **materialise** the returned items into the ledger and pin *that*. The snapshot manifest is the set of per-backend pins plus content hashes, signed (dejavu's Ed25519 pattern). `as_of` resolves against manifests, never against live backends.
8. **Receipt writer.** Every `retrieve` and `snapshot` emits a ledger event: scope, plan, backends asked, items served, distributions, budget used. This is what adjudication replays.
9. **Served-memory guard.** Injection gate and classification-tier redaction on the way out.
10. **Fallback plane.** Every model-backed decision has a rule-based fallback and a latency budget; on timeout the rule runs and the receipt records which path was taken.

### 3.1 Typed decisions in the gateway

The gateway is the best place in the whole stack for a decision model, because every choice it makes is over a **closed, freshly rebuilt menu** (the registry after scope resolution, the fused candidate pool, the fixed ontology tags). That is exactly the shape the evidence says works, and none of it requires the model to generate anything.

| # | Decision | Shape | State | Menu | Fallback | Latency class |
|---|---|---|---|---|---|---|
| G1 | Retrieve at all? | Noul `memory_would_help` + Score `budget` | prompt/spec excerpt, stage, kind | — | always retrieve with small budget | sync, harness hook (B0) |
| G2 | **Route**: which backends | one Choice per backend `worth_querying` batched in one call, or Score over the menu | query, scope, kind, backend manifests | registry after scope resolution | query all in-scope backends up to budget | sync, ≤300 ms |
| G3 | Per-backend budget split | Score `expected_yield` (2–5 levels) | same | same | equal split | same call as G2 |
| G4 | **Listwise rerank** across fused pool | Choice over candidates | query, intent, candidates[] | fused pool (≤ ~40) | RRF order | sync, ≤500 ms |
| G5 | Sufficiency / stop | Nouls `sufficient`, `missing`, `contradiction`, `continue_useful` | query, selected items, round | — | hard caps | sync per round |
| G6 | **Confidence** per served item | Score over {content, provenance, freshness, agreement with other items} | item + neighbours | 5-level | provenance-derived heuristic | sync, batched with G4 |
| G7 | Ontology tagging (dims 3, 5, 6, 10) at serve time | Choice per dimension | item | fixed tag sets | untagged | async or batched |
| G8 | Injection / untrusted content | Noul `contains_instructions_for_automated_system` | item text | — | serve with "facts not instructions" frame | async at ingest; cached by hash |
| G9 | Write admission: fact vs episode vs none; certified? | Choice `kind` + Noul `quote_supports` + Choice `source_class` | record, caller, evidence | closed | episode only | async |
| G10 | Supersession | Choice `relation ∈ {same, supersedes, contradicts, unrelated}` + named target | pair | candidates sharing entity | none (keep both) | async |
| G11 | **Fault adjudication** | Choice `{spec, tribal, harness}` | assumptions-ledger entry, replayed receipt, failure | 3 options | human | async |
| G12 | Staleness ("still true given snapshot?") | Noul, batched 60 per call | item + current source snapshot | — | age-based flag | scheduled |
| G13 | Cross-hub duplicate / conflict | Noul `same_claim` + Choice `which_is_authoritative` | two items + manifests | 2 options | prefer higher-tier source | async, cached |

Rules that carry over unchanged from the evidence: fit every threshold on the programme's own labelled set (≥ 40 labels per battery before refitting); log raw distributions in the receipt; pin the model version and record it in the snapshot manifest; shadow each decision per route before enabling; never copy a threshold from another system; the cheap battery first, escalation only when borderline and only if the held-out split shows it helps.

### 3.2 Operating the decision plane

With the model available in-house, the remaining engineering questions are latency and fallback, not access. Each decision in §3.1 carries a latency class and a rule fallback; the gateway records in the receipt which path ran. The document's own note that a typed classifier "adds a synchronous external call with no retry or latency budget yet defined" is answered per decision: a budget in the low hundreds of milliseconds for the synchronous ones (G2–G6), no retry on the hot path, batch every question that shares a state into one call, and asynchronous or scheduled execution for the rest (G7–G13). Pin the model version and record it in the snapshot manifest so buildability scores do not drift when the decider changes.

## 4. Components that do not exist anywhere yet

These are the pieces neither the PCG nor any named hub has. They are the build list, independent of which backend wins.

1. **Conformance kit**: the three verbs as an executable spec, a scope schema, the response schema, and the swap test (run the same harness against two backends, assert identical harness code and equivalent results). Ship this first; it is what makes a thing "C6".
2. **Backend registry and manifests** (§3, item 1).
3. **Scope resolver** (§3, item 2).
4. **Snapshot service**: manifest format, signing, materialisation for position-less backends, `as_of` resolution, retention of manifests.
5. **Receipt store and replay tool**: the ledger event types plus a CLI that reproduces what a scope saw at a snapshot.
6. **Assumptions ledger**: record type, write API at self-review, link to Spec and Change.
7. **Outcome ingest**: Outer Loop signals (escape, CFR, RCA, disposition accuracy, spec-attributed fault) with a join key to Specs, Changes and receipts. Source: Datadog via OTel; the Miro admission/build-success/completion contracts are the natural carrier once adopted.
8. **Certification path**: candidate fact → review (human or agent) → certified fact, with source class, reason, recorded_at; supersession instead of edit.
9. **Fault-adjudication service**: G11 over assumptions ledger + replayed receipt; writes the three-way label as a C9 signal and opens a candidate Fact on "tribal".
10. **Read-time curate step** for the Spec call site.
11. **Staleness sweep and freshness field**.
12. **SoR connectors that emit positioned events** (Slack first, since neither harness serves it; then Confluence page versions, Jira transitions, GitHub PR events, runbook regenerations).
13. **Harness adapters**: C4 capability injection, MCP-projected CLI, Courier link resolution, Endzone dual role (backend and caller).
14. **Eval harness with pinned reviewer config** and the RRSI discipline (noise floor, held-out, one change per round, external ledger).
15. **Ontology schema registry**, gateway-held and versioned with the manifest, starting with the four dimensions the response must carry.
16. **Governance console**: entitlements, tiers, receipts audit, staleness flags, guardrail-trigger rate, blocked-episode tags.

## 5. What the PCG keeps, and what it stops claiming

**Keep:** the positioned immutable ledger and its dedup; the provenance block; the Atlas response (it is already most of the normalised shape); intent classification as a planner input; entity resolution (with tenant); the ports-and-adapters structure (it is the swap test's friend); multi-tenancy; GDPR crypto-shred; the graph as a *lineage, supersession and entity* backend.

**Stop claiming:** the graph as the default read surface (H2 unproven, and the document's callers want briefings, links and snapshots, not traversals); four-tier decay as a differentiator (no evidence anywhere, H4/H9 will decide); "memory system" as the category (the programme has several; the category that is empty is *federation with snapshots and receipts*); the name.

## 6. Sequence inside the three-month window

| Weeks | Deliverable | Proves |
|---|---|---|
| 1–3 | Conformance kit (three verbs, scope schema, response schema aligned with Sanctum's `evidence[]`/`validity`); PCG behind all three verbs with snapshot by position; Courier link-resolution demo with snapshot id in the Spec | The interface exists; `snapshot` exists; a harness uses it with no credential |
| 3–5 | Registry with manifests; DeepInsights as second backend; **swap test passes**; RRF fusion; receipts; MCP projection converged with Sanctum | Backend independence; federation over two real backends; one PAI surface |
| 5–7 | Snapshot materialisation for position-less backends (Confluence via Endzone's ingest); PR-review re-resolution of the Spec's snapshot; assumptions ledger | The pinned-reviewer fitness function can run |
| 6–9 | G2/G4/G6 in shadow with receipts; rule fallbacks and latency budgets; fault adjudication (G11) on a labelled set | Where a decision model earns its place, measured, not assumed |
| 8–11 | Certification path; supersession; knowledge-gap write-back; staleness sweep; Slack connector | Both loops contribute knowledge, not just consume it |
| 10–12 | C9 signals joined to receipts; eval harness with pinned config; noise floor; H1/H2/H4 first numbers | Stream 03's "own measures" exist |

Discovery hypotheses map onto this: H1/H2 in weeks 5–7 once two backends are live; H5 (typed gate) and H10 (provenance/injection) in weeks 6–9; H4 and H9 after outcomes flow.

## 7. Questions to take to the programme

1. Who ratifies C6, and would a running conformance kit with a passing swap test be accepted as the ratification artefact?
2. Schema location: gateway-held (this analysis) vs backend-held (§5.4 leans AMS). The swap test cannot pass with a backend-held schema.
3. Snapshot semantics for external systems of record: is materialise-and-sign acceptable for Confluence and Jira content, and what retention applies to materialised copies per tier?
4. Decision-model hosting: which team operates the in-house System One endpoint, and what latency and model-pinning guarantees does it give the gateway?
5. AMS's role: a certified-fact backend behind the gateway, with its certification path reused for L6? That turns the name collision into a division of labour.
5b. Sanctum: converge on one PAI MCP surface and one response schema? Who owns the merged surface? Why are neither Sanctum nor the PCG in the due diligence?
6. Outcome signals: will the Outer Loop adopt the admission/build-success/completion contracts, and can they carry a receipt id?
7. Latency budget per call site: the Spec step can afford seconds; the C4-injected `retrieve` inside an Endzone loop cannot.
