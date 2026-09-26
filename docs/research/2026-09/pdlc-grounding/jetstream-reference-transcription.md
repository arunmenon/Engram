# Grounding document: "Nitin jetstream artifacts reference" — transcription (partial)

**Received:** 2026-09-26, as 11 photographs of a Markdown artifact rendered on screen. **Coverage:** §0 Orientation, Part 1 (§1.1–1.5, partially cut at column edges), Part 2 §2.1–2.3 (spine, Inner Loop steps, C1–C11 contracts; holder column cut). Not yet received: the rest of Part 2 (Outer Loop, decision S0), Part 3 (Company Knowledge reference architecture: the C6 proposal, 11-repo due diligence, retrieve/write/snapshot), the Knowledge Ontology (11 dimensions), and Courier vs. Endzone (how the two harnesses retrieve today). Text in `[…]` is cut off in the photo; text in `[word?]` is a reconstruction.

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

**Transcription ends here** (2026-09-26, second batch).

---

## First read: what these pages change for Engram (to be revised when the rest arrives)

0. **C6 is the whole game, and it is unowned.** "C6 Memory and Knowledge: one interface for agent read/write/retrieve, scoped per operation" has **no ratified holder**; so does C9 (evidence and eval), and C9 depends on an unowned autonomy-gate pipeline. Every contract is "one interface and one test". The Inner Loop's Spec step "resolves needed knowledge through C6". So the PDLC layer is not a schema Engram proposes; it is a **candidate implementation of C6** with a conformance test, and the self-review step's **assumptions ledger** ("ambiguity resolved by inference gets recorded, not silently discarded") is the first concrete write-side artefact the contract needs to carry. Engram's ledger-first design, per-operation scoping (tenant + run + stage), and provenance block map directly onto "scoped per operation". C9's signals (agreement, autonomy, quality, speed, cost per stage) are the outcome events P4 asks for; if C6 and C9 land together, the retrieval-receipt → outcome loop is a contract obligation rather than an Engram feature. C8 says OpenTelemetry GenAI spans are mandatory, which settles the ingest format question raised in digest D3 (Beacon's OTel-normalised JSONL).
1. **Memory is declared out of scope for consolidation.** The programme's own text says memory systems "stay independent", and the stream-03 row names two of them and says they stay separate (the second name is cut at "Eng…"; if it is Engram, Engram is already on the programme's map). Positioning follows: Engram is not a candidate for the shared foundation, it is an independent capability that must conform to the interoperability contracts. The contract that matters is **C6** (Company Knowledge), whose proposal is the most recently edited page. Everything in [pdlc-memory-layer.md](../pdlc-memory-layer.md) about "ontology enforcement" has to be expressed as *what flows through C6*, not as Engram's private schema.
2. **The spine is the PDLC ontology's backbone**, and it is richer than requirement → HLD/LLD → tickets → PR. Stages: Request, Spec, Decomposition, Sequence, Change (review-ready), Pull Request, adversarial review, Merge, Tier 1 / Tier 2 CI, environment gate, Deploy, Observation, Detection, Diagnosis, Mitigation, RCA, Escape. The **feedback edge (escapes, RCA → INTAKE) is the outcome loop** the discovery plan's P4 (`task_key`, `task.outcome`) exists for: an RCA that points back at a Request is negative evidence attached to the Decision and Change that produced it.
3. **The architecture track is a Decision ledger by definition** — "decisions recorded as they are made rather than published once as a document". That is the T5 rule (decision + date + reason) already adopted in digest D8, and it is a concrete first tenant for Engram's Decision/SUPERSEDES machinery: an append-only queue of component definitions, interfaces and contracts, with supersession, that any harness can query.
4. **Harness-agnostic is the programme's rule, not just Engram's.** Endzone, Courier and GSE are named; the "Courier vs. Endzone – how the two harnesses actually retrieve today" page is the one that decides the read-path design and where the retrieve-or-not gate (Jev B0) lives. Get that page before designing adapters.
5. **Scale targets are now stated.** Stream 01 targets on the order of a thousand implementations with 100 concurrent; that is the write-path load Engram's ledger must take, and it makes the three confirmed defects in [write-read-path-scale.md](../write-read-path-scale.md) blocking rather than cosmetic.
6. **"Stream's own measures are an open question."** The discovery plan's metrics (ledger-vs-no-memory oracle pass rate, knowledge-update accuracy, feedback-loop rate, stale-flag precision) are a direct contribution to stream 03, and stream 04 is the telemetry backbone they should land on.
7. **The commitment window is 3 months and one adopting organisation.** The discovery plan's five-week sequence fits inside it only if P1–P3 start now.

**Still needed from the document:** the rest of Part 2 (Outer Loop, the "distinction" paragraph, decision S0 and the autonomy-gate pipeline), the C6 proposal and its retrieve/write/snapshot operations (this is the API Engram has to present), the 11 ontology dimensions (the node/edge vocabulary), and the Courier vs. Endzone retrieval comparison.
