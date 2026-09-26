# Grounding document: "Nitin jetstream artifacts reference" — transcription (partial)

**Received:** 2026-09-26, as 11 photographs of a Markdown artifact rendered on screen. **Coverage:** §0 Orientation, Part 1 (§1.1–1.5, partially cut at column edges), Part 2 §2.1–2.3 and §2.5–2.7 (spine, Inner Loop steps, C1–C11 contracts with holder column cut, Outer Loop stages, seams), Part 3 §3.1–3.5, Part 4 §4.1–4.8 (due-diligence table cut after the first row), Part 5 §5.1–5.4 (dimensions 3, 5, 6, 10 only), Part 6 in full. Not yet received: §2.4, the rest of the due-diligence table, ontology dimensions 1, 2, 4, 7, 8, 9, 11, Part 7 (Company Knowledge reference architecture: the C6 proposal, 11-repo due diligence, retrieve/write/snapshot), the Knowledge Ontology (11 dimensions), and Courier vs. Endzone (how the two harnesses retrieve today). Text in `[…]` is cut off in the photo; text in `[word?]` is a reconstruction.

> **Confidentiality note.** This is an internal-programme document of the user's employer with named people. It is stored here because it is the grounding for [../pdlc-memory-layer.md](../pdlc-memory-layer.md); keep the branch private.

## 0. Orientation — the five pages and how they nest

Nitin owns five Jetstream pages. They form a deliberate hierarchy, top to bottom:

```
Project Jetstream (3086518430)                        ← the programme
│   what Jetstream is · 5 workstreams · leadership · rules
│
├── Inner Loop and Outer Loop: Component Architecture (3119123013)
│   │   the two loops · C1–C11 contracts · Company Knowledge as stream 3
│   │
│   └── Company Knowledge: Reference Architecture (3119623953)
│           the C6 proposal · 11-repo due diligence · retrieve/write/snapshot
│
├── Knowledge Ontology (3120053683)
│       the 11 dimensions · what flows through C6        (sibling, not child)
│
└── Courier vs. Endzone – Knowledge Sources & Retrieval (3105194428)
        how the two harnesses actually retrieve today
```

| Page | ID | Last updated | Status |
|---|---|---|---|
| Project Jetstream | 3086518430 | 4 Sep 2026 | Living index, synced from the Jetstream Hub |
| Inner Loop and Outer Loop: Component Architecture | 3119123013 | 22 Sep 2026 | Draft |
| Company Knowledge: Reference Architecture | 3119623953 | **24 Sep 2026** | Draft — most recently edited |
| Knowledge Ontology: Classification, Ownership, […] | 3120053683 | 22 Sep 2026 | Draft, open questions unresolved |
| Courier vs. Endzone – Knowledge Sources & Retrieval | 3105194428 | […] | […] |

## PART 1 — The programme
*Source: Project Jetstream (3086518430)*

### 1.1 What Jetstream is

PayPal's **CTO-wide programme for building software with AI**, under the AI Engineering Enablement portfolio. It treats coding agents as first-class members of the delivery team across the full lifecycle — explicitly *"not an autocomplete layer inside the IDE."*

The strategy is deliberately not standardisation:

> "Rather than standardizing every team on one agent harness, the program builds the shared foundation underneath it: identity, security, enterprise integration, measurement, evaluation, and governance, plus the interoperability contracts that let any conforming harness (Endzone, Courier, GSE, and others already running inside PayPal) plug […]"

[… cut …] "ownership of intent, architecture, policy and accountability."

### 1.2 The consolidation framing — and the line that matters to us

> "Consolidation is the point of the program, and the Hub is direct about this: **it is not a shutdown list, it is decomposition and recombination**."

Things built once because there was nothing to share: identity, security, enterprise integration, infrastructure, cost accountability, governance, measurement, evaluation, telemetry.

Things that **stay independent**:

> "Capabilities teams rebuilt because they genuinely had varying needs, **domain-expertise skills and memory systems being the clear example, stay independent**."

And in the stream-03 description, stated again and by name: [… cut …]

Also: *"Existing project owners get a proposal, not a mandate, and the actual decomposition happens with the engineers who built the system."*

### 1.3 The numbers

| Metric | Value |
|---|---|
| Agentic engineering projects in the inventory | 50+ |
| Robust harnesses among them | 10 |
| Delivery streams plus architecture track | 5 + 1 |
| Engineers, approximately | 25–30 |
| Months from kickoff (the commitment window) | 3 |
| Organisations required to adopt (the commitment) | 1 |

### 1.4 The five workstreams

| Stream | Lead | Team | Focus (right edge cut in the photo) |
|---|---|---|---|
| 01 · Inner Loop | Mike Bukosky | 8–12 | Decomposes 8 harnesses into o[ne] reusable execut[ion] layer; remote execution with identity and aut[h], local client, disp[atch] API. **Target: 1,0[00 …] implementatio[ns …] 100 concurrent** |
| 02 · Outer Loop | Jon Barksdale | 8–10 | Ticket quality inbound, code re[view] and PR quality outbound, tele[metry] across PR-to-Pro[d …] Design (not buil[d]) […] Path to Producti[on] |
| 03 · Company Knowledge + Operational Feedback | Nitin Sharma | 4–6 (ML + SRE) | Routes domain-expertise skills i[nto] the agent loop; f[eeds] production sign[als] back. Memory systems and gat[eway?] registries sit her[e]. **Dobby and Eng[ram?] stay separate.** *Stream's own measures are an [open] question.* |
| 04 · Telemetry & Cost | Neil Openshaw | ~3, Steve Ray dedicated | Measurement backbone for ev[ery] other stream. Deliberately not distributed. |
| 05 · GTM: Product/User Fit & [Adoption] | Jake Smrek | ~3 | Adoption, onbo[arding], training. Also ru[ns] Jetstream ops a[nd …] architecture tra[ck] |

**The architecture track** is not a stream. *"A standing queue of concrete architectural decisions (component definitions, interfaces, contracts) recorded as they are made rather than published once as a document."* Coordinated under stream 05. Enterprise Architecture advises but **holds no sign-off on the platform boundary**. Staffed for senior engineers who want a say in the contracts without committing a full week.

### 1.5 Leadership

| Role | Owner |
|---|---|
| Executive Sponsor | Ryan Prichard |
| Engineering Lead | Nir Szilágyi |
| […] | […] |

## PART 2 — The architecture
*Source: Inner Loop and Outer Loop: Component Architecture (3119123013)*

### 2.1 The spine

```
REQUEST
  ↓
INTAKE           Spec → Decompose → Sequence
  ↓
INNER LOOP       Design → Implement → Self-review → Test
                 (opaque to the Outer Loop)
  ↓  review-ready change
PULL REQUESTS    Adversarial review → Merge
  ↓
CI/CD            Tier 1 checks → Tier 2 batched CI → per-environment gates
  ↓
OPERATING        Deploy → Observe → Detect → Diagnose → Mitigate → RCA
  ↓
  └── feedback (escapes, RCA) ──→ back to INTAKE
```

The distinction: *"The Inner Loop answers whether* […]" — [rest of the paragraph not captured]

### 2.2 Inner Loop — the four steps

- **Spec** — taken as given input; the Inner Loop *"does not renegotiate intent, acceptance criteria, or scope."* **Resolves needed knowledge through C6.**
- **Design** — translate the Spec into an implementation approach before any code.
- **Implement** — inside a declared run (C2) in a policy-bounded workspace (C3), on one of two harness backends.
- **Self-review** — the agent grades its own work against acceptance criteria. Distinct from adversarial outer-loop review. *"Any ambiguity the agent resolved by inference rather than by asking gets recorded to the **assumptions ledger** here, not silently discarded."*
- **Test** — exercised against acceptance criteria and the existing suite.

### 2.3 The eleven contracts

> "Eleven contracts, each one interface and one test. Two have no holder."

| Contract | Function | Held by (right edge cut) |
|---|---|---|
| C1 Model Access | Model calls route through one AI gateway; model choice is configuration, not code. | Harnes[s] Consoli[dation] |
| C2 Execution | A run is a declarative spec any conforming executor can satisfy. | Compu[te] and Ru[n …] |
| C3 Workspace/Sandbox | Each run declares filesystem/network/exec policy; executor enforces, fails closed. | Compu[te] and Ru[n …] |
| C4 Harness Capability | Harness declares what it consumes; platform injects it; harness never holds credentials. | Harnes[s] Consoli[dation], credent[ials], Identit[y] |
| C5 Tool Access | Tools reach the agent through one MCP gateway, projected as a CLI. | Identit[y], Creden[tials], Tool Ac[cess] |
| **C6 Memory and Knowledge** | **One interface for agent read/write/retrieve, scoped per operation.** | **NO HO[LDER]** |
| C7 Control Plane | One versioned REST API: dispatch, list, show, attach/stream, cancel, exit contract. | Control [Plane], Dispatc[h] |
| C8 Telemetry and Cost | OpenTelemetry GenAI spans; cost reported per team/step, by term. | Obligat[ion on all], no sing[le holder] |
| **C9 Evidence and Eval** | Every stage emits agreement, autonomy, quality, speed, cost signals; autonomy rises only after eval. | **NO HO[LDER]** |
| C10 Identity | SSO for humans, per-tenant isolation, broker-issued short-lived run credentials. | Control [Plane] (SSO); Identit[y] (run cre[dentials]) |
| C11 Onboarding | Thin CLI lets a local harness borrow cloud compute in minutes. | Develo[per …] Thin C[LI] |

**Unresolved:** C6 and C9 have no ratified holder. C9 also depends on the six-stage autonomy-gate pipeline, itself unowned (decision S0, […]

*(§2.4 not captured.)*

### 2.5 Outer Loop — four spine stages

| Stage | Key facets | Status |
|---|---|---|
| Intake | Triage, Specification, Decomposition, Value, Effort, Prioritization | Specification and Decomposition resolved; rest open |
| Pull Requests | Risk routing, AI review, disposition, auto-merge gating | Open; model defined, not calibrated |
| CI/CD | Tier 1 fast checks, Tier 2 batched CI, per-environment gates | Verification-vs-deploy boundary resolved |
| Operating | Detect, diagnose, mitigate, RCA (DORA + MTT* metrics) | Open; environment not fully characterised |

**Intake detail.** Specification *(resolved)*: intent, acceptance criteria, scope, dependencies; interactive creation; **references rather than inlines knowledge**; fitness is adversarial buildability pass-rate against a **pinned reviewer config** plus spec-attributed fault rate; ambiguities logged in an assumptions ledger. Decomposition *(resolved, soft boundary)*: Intake alone cuts a document into Specs; below the Spec, Intake and Inner Loop both split units, measured jointly. Value, Effort, Prioritization, Triage — all **open**.

**Pull Requests detail.** Allocation is risk-based: broad cheap AI review on everything, human escalation only where risk warrants, auto-merge once safety is demonstrated. Fitness is severity-weighted escape rate, bounded by a cost budget and a friction guard. **Binding rule: auto-merge requires proven disposition accuracy plus Operating's revert-plus-detection.**

**CI/CD detail.** Tier 1 (fast, per-PR): ML test selection, static analysis, lint; gates the merge queue. Tier 2 (batched, 5–15 min windows): full tests, perf with anomaly detection, contract tests, instrumentation checks. Per-environment gates: dev, staging, canary, prod verify independently; *"a lower-env escape becomes a new upstream gate."* **Resolved boundary:** CI/CD owns the pass/fail gate; Operating owns deploy/promote/rollout and canary/detection.

**Operating detail.** Telemetry runs through OpenTelemetry to Datadog. *"Site-level monitoring is consistent; team-level coverage is not. Auto-rollback exists in theory, not yet configured or tested."* Operating detection is ground truth for escape rate and DORA change-failure-rate. Metrics: MTTD/detection coverage · MTTI/diagnosis accuracy · MTTR/auto-mitigation rate · RCA completion rate.

### 2.6 The Outer Loop has no contract set

> "Nothing in `outer-loop/`, `program-management/`, or `shared/` defines an interface list for Intake, Pull Requests, CI/CD, or Operating the way `inner-loop/contracts.md` defines C1 through C11."

The word "contract" appears in the Outer Loop docs only in two non-architectural senses: the **spec contract** (the fixed schema a ticket must conform to) and ordinary **external-dependency** usage.

One unformalised analog: a Miro board from the Outer Loop workstream sketches three PR-lifecycle contracts — an **admission contract**, **build-success conditions**, and a **completion contract** tied to the latest commit SHA. Explicitly a whiteboard proposal, not adopted.

**Open question:** should the Outer Loop get its own numbered contract set? Not yet decided.

### 2.7 Cross-loop seams

- Intake ↔ Inner Loop: shared decomposition cut below the Spec
- Pull Requests ↔ Inner Loop: the revise/fix round-trip is Inner Loop work
- Pull Requests ↔ CI/CD: PRs decide what verification is needed; CI/CD runs it
- Pull Requests ↔ Operating: auto-merge depends on Operating's detect-plus-rollback
- CI/CD ↔ Operating: gate vs. deploy/rollout ownership; feedback on escapes
- Operating ↔ Intake: RCA and incident feedback re-enter as new Requests
- Inner Loop ↔ Company Knowledge: the Spec step draws on it through C6; **neither loop owns it**
- Intake ↔ Company Knowledge: Triage routing and Spec creation draw on it directly
- Pull Requests ↔ Company Knowledge: adversarial review runs with the same knowledge that crafted the spec, **pinned as a snapshot**

## PART 3 — Company Knowledge as the third stream
*Source: Component Architecture §5*

### 3.1 It is not a stage — it is a stream both loops call into

> "Company Knowledge is not a stage in either loop's spine. It is a separate Jetstream workstream that both loops call into directly, from three separate points."

Note the method: *"built the way any dependency gets defined before its own team has written a spec: **backward, from what the two loops that call into it already require**."*

### 3.2 What it provides

Domain and tribal knowledge — *"the facts a human author would fill in silently, and an agent with no organizational context cannot."*

**C6's test:** *a change of backend touches no harness code.*

C5 (Tool Access) names a candidate system in the same stream: the **MCP Hub**, which projects every tool as a CLI so tool-definition tokens stay near zero at session start.

### 3.3 The four call sites

| Caller | What it needs |
|---|---|
| Inner Loop, Spec step | Resolves what domain and tribal knowledge a run needs, before Design starts |
| Intake, Triage | The ticket corpus and org structure, to route correctly. *"Without it, routing accuracy has nothing to route against."* |
| Intake, Specification | A Spec references rather than inlines knowledge; Company Knowledge resolves that reference at build time |
| Pull Requests | Adversarial review runs with the same knowledge that crafted the spec, **pinned as a snapshot** |

*(text between §3.3 and §3.4 partly not captured; the fragment "[…] buildability scores stay comparable" precedes §3.4)*

### 3.4 The fault-adjudication rule

The one place the docs give Company Knowledge a **testable** failure mode:

| Outcome | Fault |
|---|---|
| Not recoverable, missing piece was **spec-type information** | The spec |
| Not recoverable, missing piece was **tribal knowledge** | Company Knowledge |
| Recoverable, but the agent chose wrong anyway | The harness |

> "This is what keeps 'Company Knowledge is cross-cutting' from becoming an excuse that absorbs every downstream failure: a gap only counts against Company Knowledge when the assumptions ledger shows the missing information was tribal, not structural."

### 3.5 What it would need to be

> "A single, entitlement-aware retrieval point that both loops can call at build time, that ingests the org's existing systems of record rather than becoming a new one, and that can be swapped or upgraded on the backend without either loop's code noticing."

**The assumption, stated as an assumption:**

> "**Assumption:** Engram, PayPal's certified context and knowledge layer (Engram - Home), matches that shape closely… **Whether Engram becomes the system that actually sits behind C6 is still open**; what Sections 5.1 through 5.3 fix is the shape whatever sits there has to have."

⚠ The "Engram" linked there is **AI Tech's `agenticmemoryservice` in the AITMCP space — not the PAI Context Graph.**

**Already live ahead of a formal owner:** *"the Outer Loop's Intake refine skill instructs the authoring agent to pull company knowledge that answers a* […]" *(rest not captured)*

## PART 4 — The C6 proposal
*Source: Company Knowledge: Reference Architecture (3119623953) — last edited 24 Sep*

### 4.1 The contract, verbatim

The only contract whose full text (statement + test) appears anywhere in Confluence:

> "An agent reads, writes, and retrieves through one interface. The scope of each operation is declared. The store stays where it already lives. We integrate with the store. We do not absorb it.
> **Test:** a change of backend touches no harness code."

Three obligations fall out: **one interface (not one store), declared scope per call, backend independence proven by a passing swap test.**

### 4.2 The headline finding

> "**No single repo is a ready-made C6 knowledge interface.** Engram is the strongest service candidate but is itself one backend, not the adapter layer the contract requires. DeepInsights is the strongest contract-shape prior art but is a black box from here. **The interface itself does not exist yet anywhere in the estate.**"

### 4.3 The eleven-repo due diligence

| Repo | Verdict | Notes (right edge cut) |
|---|---|---|
| `agenticmemoryservice` ("Engram") | Service | Closest ready backend. Jav[a], MySQL + Ver[…] |
| […] | | |

*(remaining due-diligence rows not captured)*

### 4.4 The proposed interface — three verbs

One MCP-projected surface, consistent with C5's "projected as CLI" pattern.

| Signature | Notes |
|---|---|
| `knowledge.retrieve(query, scope, kind)` | `kind` distinguishes semantic fact / episodic run-history / document-corpus search — *"different retrieval mechanics behind the same verb, not different verbs."* |
| `knowledge.write(record, scope, kind)` | Only certified callers write a `fact`; any caller writes an `episode`. *"This mirrors Engram's own Facts/Episodes split, which is the right split; it should not be flattened."* |
| `knowledge.snapshot(scope, as_of)` | A versioned, signed view of everything a scope could retrieve at a point in time. **"This verb does not exist in any repo surveyed as a first-class operation today… the single largest gap between what exists and what the C6 knowledge interface needs."** |

`scope` is **mandatory on every call**: at minimum caller identity, space/domain, classification tier.

### 4.5 Why snapshot is required — not invented for completeness

Driven by an already-decided fitness function in `outer-loop-problems.md`:

> "Buildability is a property of the spec *and* the knowledge configuration it runs in, never the spec alone."

> "[The adversarial buildability reviewer runs against] a **pinned reviewer config**: a fixed, versioned reviewer setup whose model version, prompt, Company-Knowledge snapshot, and thresholds are held constant, so buildability scores stay comparable across spec versions and over time."

> "If the C6 knowledge interface only exposes live retrieval, buildability scores drift for reasons that have nothing to do with the spec: the knowledge backend changed underneath the reviewer."

`dejavu-toolkit`'s Ed25519-signed versioned catalog is named as *"materially cheaper than designing a new one."*

### 4.6 The adapter layer

Each backend keeps its own storage and retrieval mechanics. The gateway routes by `kind` and scope, and **normalises the response shape: content, provenance, freshness, confidence.**

**Open question raised and left open:** how does the gateway compute `confidence`? One option floated — *"a typed, calibrated classifier (TypeSafe AI's Jev is one example of this model class) scoring each retrieval instead of a free-text judgment."* Notes it adds a synchronous external call with no retry or latency budget yet defined.

### 4.7 Integration points

| Point | How C6 is used |
|---|---|
| Inner Loop | Consumed through C4 — the harness declares it consumes memory/knowledge; the platform injects a scoped `knowledge.retrieve` capability witho[ut] the harness holding a credential. *No chan[ge] to C4's shape needed.* |
| Outer Loop, Triage | `knowledge.retrieve(kind=documen[t])` against the ticket-corpus backend |
| Outer Loop, Specification | Two distinct calls: the authoring agent cal[ls] `retrieve` while drafting; **the Spec artif[act] stores a `snapshot` id, not inlined conte[nt]** |
| Outer Loop, PR review | Re-resolves the Spec's snapshot id to chec[k] the diff against acceptance criteria and th[e] assumptions ledger |
| Knowledge-gap signal | Makes the fault-adjudication rule *executa[ble]*: because every retrieval is scoped and snapshotted, an adjudication agent can **replay what the interface returned** for a given scope at a given snapshot. Every confirmed gap is written back as a candid[ate] Fact through the certification path. |

### 4.8 Open questions on this page

1. **Does a "skill" request go through C6? — Resolved: no.** `contracts.md` (C4) lists skills as a sibling of memory, not a subset. `lep-tools` settles delivery: skill files are loaded by the agent loop via `route_to_expert`, never retrieved through a knowledge-query interface. `kind` stays closed at fact/episode/document. *A narrower question stays open* — whether skill-file **content** should live behind a versioned adapter even though **delivery** stays a C4 injection. Flagged for C4/C5's future holder.
2. **DeepInsights internals** — production infrastructure with the closest contract shape, but its source has not been inspected. Backend or model for the gateway? Undetermined.
3. **`knowledge-service`'s ownership and roadmap** — maintained by a separate team. Adopt as-is or fold its retrieval into Engram? *"An org question, not just a technical one."*
4. **`eaintelligencemcpserv`** — referenced but not present locally; needs its own pass.

**Explicitly out of scope:** the adapter interface's wire format (REST vs MCP tool schema vs both). Follow-ups expected for the wire-format spec and the DeepInsights due-diligence pass.

## PART 5 — The ontology
*Source: Knowledge Ontology (3120053683)*

### 5.1 Why it is a separate page

> "The reference architecture treats `knowledge.write` as a thin verb: certified callers write a `fact`, any caller writes an `episode`. **That split is not enough once both loops are expected to contribute knowledge, not just consume it.**"

The parent defines the interface and the backends. This page defines *what kind of thing flows through it*, independent of which backend stores it.

### 5.2 The eleven dimensions, grouped

**① What kind of thing is it?**

| # | Dimension | Content |
|---|---|---|
| 3 | Domain vs. practice | Domain-oriented (a business/product area) vs practice-oriented (how work gets done). *"These are not mutually exclusive… so this is a tag set, not a single enum."* |
| 5 | Format plurality | Structured facts · free-text documents · embedded chunks · possibly tabular or code-shaped. Distinct from `kind`, which is a routing concern. |
| 10 | Granularity | Field/fact vs document vs corpus. Due diligence found a mismatch: `biso_knowledgebase` is whole-file, `knowledge-service` is per-KB. The ontology should state a target the interface normalises toward. |

**② Where did it come from, and who controls it?** *(not captured: dimensions 1, 2, 4 and probably 11)*

**③** *(heading and dimensions 7, 8, 9 not captured; the last row ends "…where 7 or 8 leave ambiguity. TypeSafe's Jev named as one technique — 'a technique, not an answer to who owns this schema or when the check runs.'")*

**④ How is it found?**

| # | Dimension | Content |
|---|---|---|
| 6 | Retrieval and ranking as classification | Emergent classification: how something ranks at query time, especially for chunks never explicitly tagged. *"The ontology is not purely a write-time metadata schema."* **Open question:** *should ranking-derived classification be written back as explicit metadata, or stay purely a runtime signal?* |

### 5.3 Where it feeds back into the reference architecture

- Dimensions **1, 2** extend §1.3's `knowledge.write` and §1.6's write-back loop
- Dimension **4** extends §1.5 (`knowledge.snapshot`)
- Dimensions **3, 5, 6, 10** are new metadata the gateway's response normalisation must carry
- Dimensions **7, 8, 9** are **new and not yet reflected anywhere in the reference architecture**

### 5.4 Not yet resolved

> "This page raises the dimensions; it does not yet propose a schema. Next step is deciding which of these are mandatory metadata on every artifact versus backend-specific extensions, and **whether any existing repo (most likely Engram, given it already has certification and space-scoping) is the right place to hold this schema versus making it a gateway-level concern** that all backends normalize into."

Local source: `knowledge-memory-evals-docs/knowledge-ontology.md` in `jetstream-working-docs`.

## PART 6 — Harness reality check
*Source: Courier vs. Endzone (3105194428). Source-verified against both codebases — "No aspirational/README-only claims included."*

### 6.1 What each is

| | Courier | Endzone |
|---|---|---|
| One sentence | One Jira ticket → one PR, via a fixed scripted sequence | An always-on agent looping — reading, searching, editing, testing — choosing its own next action |
| Shape | A checklist, same order every run | Open-ended loop, no fixed step order |
| Error catching | Fixed checkpoints in the checklist (test-run, code-review, review-gate with up to 3 retries) | No checkpoints — an **acceptance gate** watches every action and intervenes on risky ones |
| Output | One PR plus a Jira comment | Usually a PR; can also update its own KB or comment |

### 6.2 Courier's retrieval — there isn't any

> "There is **no vector search, no embeddings, and no re-ranking** anywhere in this pipeline — every source is either linked in the ticket and fetched whole, or it doesn't exist as far as Courier is concerned."

It regex-scrapes the ticket body for Confluence and Slack URLs and fetches whatever it finds, concatenated as-is. *"A relevant doc that wasn't linked in the ticket is invisible to Courier."* The first point anything judges relevance is the coding agent itself, at implement time.

⚠ **Memory is wired in but inert.**

> "`memory-recall` and `memory-write` exist as real module classes with typed Zod schemas and a place in the executor pipeline — **they aren't missing, they're stubs.** `MemoryRecallModule.execute()` ignores its input and always returns `{ memories: [], context: "" }`; `MemoryWriteModule.execute()` always returns `{ stored: false }` without touching disk. Both carry the same comment: *'Deferred (Mastra integration not yet implemented).'*"

### 6.3 Endzone's retrieval — real, with a caveat

A genuine ingestion pipeline: Confluence pages chunked and embedded, repo `**/*.md` globbed and embedded, auto-generated runbooks re-indexed every 60 seconds, backlog issues chunked per (issue, state) with superseded versions flagged `inactive:`. **Slack is not ingested at all** — its one gap relative to Courier.

Ranking: over-fetch `top_k × 3`, drop inactive, then apply a priority boost —

```
score = similarity + 0.3 × (issue_priority ÷ max_priority_in_batch)
```

*"A high-priority backlog item can outrank something with higher raw similarity but lower ticket priority."*

⚠ **Memory is two disconnected systems, and the semantic half is dormant.**

> "The first is a plain scoped key-value store… It has a dormant semantic-search path: an `embedding` column and a cosine-similarity query using the sqlite-vec extension — but every one of the ~30 call sites that write a `Memory` row constructs it without ever setting `embedding`, so that column is always `NULL` and the search always falls back to plain recency ordering. It has never actually been semantic search in production."

A second system, the `KnowledgeWrite` tool, writes into the real embedded KB and *is* searched by similarity. *"The two systems share nothing — different tables, different search mechanics, different scoping rules — despite both being called 'memory.'"*

### 6.4 Knowledge source matrix

| Category | Courier | Endzone |
|---|---|---|
| Jira | Direct fetch (REST → MCP fallback) | Same, once at task creation, **no refresh** |
| Confluence | Only pages linked in the ticket; no search | Explicit URLs ingested into the vector KB |
| Slack | MCP-only, linked-in-ticket only | **Not implemented** |
| GitHub repos | Not a knowledge source | Cloned, docs chunked/embedded |
| Runbooks | Not present | Auto-generated, re-indexed every 60 s |
| Domain / skill packs | Filesystem lookup via env var | No equivalent |
| Backlog / plan issues | Not present | Own KB: as-is + proposed states, versioned |
| Agent-written memory | Stubbed | Two mechanisms; the searchable one is `KnowledgeWrite`, the other is dormant |
| Vector store / RAG | None | Implemented |

## PART 7 — Master list of open questions
Consolidated from all five pages.

### 7.1 Ownership and ratification
*(not yet captured)*

**Transcription ends here** (2026-09-26, sixth batch; Part 7 and ontology dimensions 1, 2, 4, 7, 8, 9, 11 still to come).

---

## First read: what these pages change for Engram (to be revised when the rest arrives)

> **⚠ Name collision, read first.** Inside the Jetstream pages, "Engram" means **AI Tech's `agenticmemoryservice`** (Java, MySQL + a vector store), "PayPal's certified context and knowledge layer". This repository is what the document calls the **PAI Context Graph**. Every sentence below that says "Engram" means this repository unless it says otherwise. Consequences: (a) the programme's "strongest service candidate" for C6 is the *other* Engram, and the due diligence rates it as a backend, not the adapter layer; (b) the stream-03 line "Dobby and Eng[ram] stay separate" almost certainly refers to that system too; (c) this repository has to be positioned by what it does, not by its name, and the name itself is a liability in any Jetstream conversation until it is disambiguated.


000000. **The harnesses have no working memory today, so the C6 adapter is greenfield on the read side.** Courier: no retrieval at all, memory modules are stubs returning empty. Endzone: a real embedded KB with a priority-boosted similarity score, but its "memory" is a key-value store whose semantic path has never run in production, and a second, unconnected `KnowledgeWrite` store. Consequences: (a) the B0 retrieve-or-not gate and the C4-injected `knowledge.retrieve` have **no incumbent to displace** in either harness; (b) Courier's "linked in the ticket or invisible" is exactly the Spec-references-knowledge model in §3.3 done by hand, so the first Courier integration is *resolve the ticket's links through C6 and add the snapshot id*, nothing more; (c) Endzone's per-(issue, state) chunking with `inactive:` flags on superseded versions is a hand-rolled SUPERSEDES edge, and its 60-second runbook re-index is a source-of-record ingest — both are things the ledger does natively; (d) Endzone's KB is the obvious **second backend for the swap test** (swap between the PAI Context Graph and Endzone's KB behind `retrieve`, harness code unchanged); (e) Slack is unserved by Endzone and only link-fetched by Courier, so a Slack-thread ingest is the one source both harnesses lack. On the ontology: dimension 6 ("retrieval and ranking as classification", write back or runtime signal?) is the H4 question in the programme's words — the pack's answer is *runtime signal plus receipt, never silent write-back* until H4/H10 show the feedback loop is safe; dimensions 3, 5, 6, 10 are response-normalisation metadata the Atlas node must carry; 7, 8, 9 are unreflected anywhere and the one visible fragment ties them to a typed check that names Jev "as a technique, not an answer to who owns this schema". §5.4 asks whether the schema lives in a backend ("most likely Engram", the *other* Engram) or in the gateway; the pack's position is **gateway-level, held in the adapter layer, versioned with the snapshot manifest**, because a backend-held schema fails the swap test.
00000. **The three verbs are the API, and `snapshot` is the gap this repo already fills.** `retrieve(query, scope, kind)`, `write(record, scope, kind)`, `snapshot(scope, as_of)`, with `kind ∈ {fact, episode, document}` closed and `scope` mandatory (caller identity, space/domain, classification tier). The document says outright that **no surveyed repo has `snapshot` as a first-class operation and it is the single largest gap.** An append-only Redis Stream with `global_position` *is* a point-in-time view; `as_of` maps to a stream position, the Neo4j projection is rebuildable to that position, and signing a manifest of (scope, position, content hashes) is a small addition. That is the demo that wins C6, and it needs the ledger, not the graph. The *fact/episode* split maps onto Engram's extracted-and-certified nodes vs raw Event/Episode records, so "certified callers write facts, anyone writes episodes" is the extraction gate (Jev A1) plus the certification path in §4.7. The normalised response shape — **content, provenance, freshness, confidence** — is the Atlas node minus `scores`, plus a `freshness` field (which the staleness audit A6 supplies) and a `confidence` that the page itself proposes to compute with a typed classifier and names Jev; the page also names the two risks this pack already has answers for: a synchronous external call with no retry or latency budget (jevmem's 2 s timeout, queue, rule fallback). The **knowledge-gap signal** closes the loop: every retrieval is scoped and snapshotted, so an adjudication agent can *replay what the interface returned* — that is the retrieval receipt (path-forward step 2) stated as a contract obligation, and "every confirmed gap is written back as a candidate Fact through the certification path" is the gated update mechanism (RSI T1). Two more design constraints: skills do **not** go through C6 (C4 delivery), so procedural memory (Workflow nodes) must be exposed as `episode`-kind evidence or as facts, not as skill files; and the wire format (REST vs MCP tool schema) is explicitly deferred, so the adapter should be built as an MCP-projected CLI in front of the existing REST per C5's pattern.
0000. **The C6 contract is now verbatim, and the gap it names is the opportunity.** "One interface, not one store; declared scope per call; backend independence proven by a passing swap test; the store stays where it lives, we integrate, we do not absorb." The headline finding is that **the interface does not exist anywhere in the estate**; the best candidates are a backend (`agenticmemoryservice`) and a black box (DeepInsights). So the winning move for the PAI Context Graph is not "be the best backend" but **be the C6 adapter layer with a swap test**, and be *one* backend behind it — which is exactly the `ports/` + adapters structure this repo already has (EventStore / GraphStore protocols, harness adapters in ADR-0015). "Ingests the org's existing systems of record rather than becoming a new one" fits an event ledger that projects from sources; it does not fit a system that wants to own the knowledge. The **fault-adjudication rule** (§3.4) is the first outcome label the PDLC layer must record: for every non-recoverable failure, was the missing piece spec-type or tribal, per the assumptions ledger? That is a closed three-way label, it is the C9 signal that scores Company Knowledge, and it is a natural Jev Choice with the assumptions-ledger entry as state. "Entitlement-aware" makes ADR-0016/0029 tenant policy a contract requirement, not an option.
0. **C6 is the whole game, and it is unowned.** "C6 Memory and Knowledge: one interface for agent read/write/retrieve, scoped per operation" has **no ratified holder**; so does C9 (evidence and eval), and C9 depends on an unowned autonomy-gate pipeline. Every contract is "one interface and one test". The Inner Loop's Spec step "resolves needed knowledge through C6". So the PDLC layer is not a schema Engram proposes; it is a **candidate implementation of C6** with a conformance test, and the self-review step's **assumptions ledger** ("ambiguity resolved by inference gets recorded, not silently discarded") is the first concrete write-side artefact the contract needs to carry. Engram's ledger-first design, per-operation scoping (tenant + run + stage), and provenance block map directly onto "scoped per operation". C9's signals (agreement, autonomy, quality, speed, cost per stage) are the outcome events P4 asks for; if C6 and C9 land together, the retrieval-receipt → outcome loop is a contract obligation rather than an Engram feature. C8 says OpenTelemetry GenAI spans are mandatory, which settles the ingest format question raised in digest D3 (Beacon's OTel-normalised JSONL).
00. **C6's four call sites define the read API backward.** (a) Spec step: "what domain and tribal knowledge does this run need" — a task-conditioned briefing before Design, which is exactly the read-time curate step (digest D6, H3). (b) Triage: ticket corpus + org structure for routing — an entity/ownership graph query, Engram's `who_is`/`related` intents over Entity and UserProfile. (c) Specification: **a Spec references knowledge by reference and Company Knowledge resolves it at build time** — the reference must be a stable id with a version, i.e. a node id plus `global_position`, which Engram's provenance block already is. (d) Adversarial review: **the same knowledge that crafted the spec, pinned as a snapshot** — a point-in-time read ("as of position X"), which the immutable ledger supports natively and a mutable vector store cannot; this is the strongest argument for the ledger-first design in the whole document. Two more facts: "neither loop owns it", and the stream is specified "backward from what the callers require" — so the PDLC layer's first deliverable is the C6 interface (`retrieve`, `write`, `snapshot`) plus its one conformance test, not an ontology.
000. **The Outer Loop supplies the outcome signals but has no contracts.** Escape rate (severity-weighted), change-failure rate from Operating detection, MTTD/MTTI/MTTR, RCA completion, spec-attributed fault rate, disposition accuracy — these are the outcomes a retrieval receipt should be joined to (H4). The Miro sketch of admission / build-success / completion contracts tied to a commit SHA is the natural place for a "which knowledge was served for this change" receipt. "A lower-env escape becomes a new upstream gate" and "RCA re-enters as a new Request" are the two negative-evidence edges the procedural-memory layer needs.
1. **Memory is declared out of scope for consolidation.** The programme's own text says memory systems "stay independent", and the stream-03 row names two of them and says they stay separate (the second name is cut at "Eng…"; if it is Engram, Engram is already on the programme's map). Positioning follows: Engram is not a candidate for the shared foundation, it is an independent capability that must conform to the interoperability contracts. The contract that matters is **C6** (Company Knowledge), whose proposal is the most recently edited page. Everything in [pdlc-memory-layer.md](../pdlc-memory-layer.md) about "ontology enforcement" has to be expressed as *what flows through C6*, not as Engram's private schema.
2. **The spine is the PDLC ontology's backbone**, and it is richer than requirement → HLD/LLD → tickets → PR. Stages: Request, Spec, Decomposition, Sequence, Change (review-ready), Pull Request, adversarial review, Merge, Tier 1 / Tier 2 CI, environment gate, Deploy, Observation, Detection, Diagnosis, Mitigation, RCA, Escape. The **feedback edge (escapes, RCA → INTAKE) is the outcome loop** the discovery plan's P4 (`task_key`, `task.outcome`) exists for: an RCA that points back at a Request is negative evidence attached to the Decision and Change that produced it.
3. **The architecture track is a Decision ledger by definition** — "decisions recorded as they are made rather than published once as a document". That is the T5 rule (decision + date + reason) already adopted in digest D8, and it is a concrete first tenant for Engram's Decision/SUPERSEDES machinery: an append-only queue of component definitions, interfaces and contracts, with supersession, that any harness can query.
4. **Harness-agnostic is the programme's rule, not just Engram's.** Endzone, Courier and GSE are named; the "Courier vs. Endzone – how the two harnesses actually retrieve today" page is the one that decides the read-path design and where the retrieve-or-not gate (Jev B0) lives. Get that page before designing adapters.
5. **Scale targets are now stated.** Stream 01 targets on the order of a thousand implementations with 100 concurrent; that is the write-path load Engram's ledger must take, and it makes the three confirmed defects in [write-read-path-scale.md](../write-read-path-scale.md) blocking rather than cosmetic.
6. **"Stream's own measures are an open question."** The discovery plan's metrics (ledger-vs-no-memory oracle pass rate, knowledge-update accuracy, feedback-loop rate, stale-flag precision) are a direct contribution to stream 03, and stream 04 is the telemetry backbone they should land on.
7. **The commitment window is 3 months and one adopting organisation.** The discovery plan's five-week sequence fits inside it only if P1–P3 start now.

**Still needed from the document:** §2.4, the rest of the eleven-repo table, ontology dimensions 1, 2, 4, 7, 8, 9, 11, Part 7 (master list of open questions) and its retrieve/write/snapshot operations (this is the API Engram has to present), the 11 ontology dimensions (the node/edge vocabulary), and the Courier vs. Endzone retrieval comparison.
