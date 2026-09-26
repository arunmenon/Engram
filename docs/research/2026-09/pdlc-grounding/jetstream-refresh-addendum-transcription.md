# Grounding document 2: "Jetstream / Company Knowledge — Refresh Addendum" — transcription (partial)

**Received:** 2026-09-26, as 16 photographs. **Appends to:** the consolidated reference transcribed in [jetstream-reference-transcription.md](jetstream-reference-transcription.md). **Method stated:** Confluence searched by ancestor across all five Jetstream pages, by space (SGD) and by full text; Jira re-checked on all five tracked keys; DeepInsights searched across all spaces. "Every claim below is sourced." Text in `[…]` is cut in the photo. Section 3 (TARS PRD) and the end of §4 were not captured.

> Same confidentiality note as the first transcription: internal programme content with named people; keep the branch private.

## 0. The one-line answer

**Nitin has published nothing new.** But two artifacts already sitting in his own space materially change the C6 picture, and neither is referenced anywhere in his five pages: **Sanctum MCP Gateway** — a working `retrieve` / `write` knowledge gateway with a live endpoint — and the **TARS PRD**, on which he is a named reviewer. Separately, the DeepInsights "black box" is substantially openable: two guides plus a closed Jetstream spike describe its tool surface, routes […]

## 1. Confluence — no change from Nitin

| Page | ID | Last updated | Change since 25 Sep |
|---|---|---|---|
| Project Jetstream | 3086518430 | 4 Sep 2026 | none |
| Inner Loop and Outer Loop: Component Architecture | 3119123013 | 22 Sep 2026 | none |
| Company Knowledge: Reference Architecture | 3119623953 | 24 Sep 2026 | none |
| Knowledge Ontology | 3120053683 | 22 Sep 2026 | none |
| Courier vs. Endzone | 3105194428 | 16 Sep 2026 | none |

## 2. NEW AND MATERIAL — Sanctum MCP Gateway

**Sanctum MCP Gateway** · 3118995045 · Lokit Kumar Paras · 23 Sep 2026 · space SGD · sits **inside the Jetstream page tree**.

Repo: `github.com/OnePayPal/Sanctum`. Live remote endpoint: `https://aiplatform.dev51.cbf.dev.paypalinc.com/byoa/sanctum-pai-8ce-96138/mcp/`. Local install documented. Page header: *"an evolving doc with pending discussions with inner and outer loop engineering efforts."*

**Why this matters.** This is **an implementation of the C6 interface shape**, built on the PAI side, published one day before Nitin's last edit to the Reference Architecture — and **the word "Sanctum" appears in exactly one page in the entire SGD space: its own.** None of the five Jetstream pages cite it. The Reference Architecture's eleven-repo due diligence does not include it, and its headline finding — *"the interface itself does not exist yet anywhere in the estate"* — is now at minimum contestable.

**Side-by-side against Nitin's proposal**

| Nitin's C6 proposal (§4.4) | Sanctum as built | Read |
|---|---|---|
| Three verbs: `retrieve`, `write`, `snapshot` | Two: `retrieve`, `write` (write marked WIP) | **`snapshot` absent again.** Independent confirmation it is the real gap, not a paper one |
| `scope` mandatory: caller identity, space/domain, classification tier | `domain` optional, defaults to `"auto"` = entire workspace | **Weaker.** Scope-by-default-open is the opposite of the contract's "scope declared per operation" |
| `kind` closed at fact / episode / document — skills explicitly *not* through C6 (Open Question 1, resolved "no") | `content_type = skill \| knowledge \| episode`; retrieve explicitly covers "skill catalog lookups" | **Direct conflict.** Sanctum routes skills through the knowledge interface. Nitin's resolved answer and the shipped code disagree |
| Gateway normalises response to content, provenance, freshness, confidence (§4.6) | `evidence[]` with `content`, `source`, `path`, `score`, `metadata`, `validity{status, last_updated, verified_by, expires_at}` | **Close match, arguably better specified.** `validity.status ∈ certified / uncertified / expiring_soon / expired / active` |
| Open: how does the gateway compute `confidence`? (TypeSafe Jev floated) | `score` is "rank-fused, not a raw similarity score, comparable across strategies" | **Partial answer, different technique.** Rank fusion, no external classifier call, no added latency budget problem |
| Ontology Dim. 1 — does every write start uncertified, or is there a fast path? | `skill` / `markdown` writes **always open a PR**, never direct-commit; facts land immediately as uncertified | **Answered one way in code**, ahead of the ontology page resolving it |
| Ontology Dim. 7 — cross-backend conflict resolution, unaddressed anywhere | "Cross-domain writes aren't supported — every write lands in exactly one `domain`" | Sidesteps rather than solves; single-domain writes are a conflict-avoidance strategy |
| Entitlement-aware retrieval is the core requirement (§3.5) | "Permissioning, access control at user and service account level are still under consideration" | **The gap.** `USER_NAME` is a self-asserted env var with no broker |

**The strategic read.** Note the PAI angle. Part 11 item 2 of the consolidated reference observes that the **PAI Context Graph does not appear in the eleven-repo due diligence at all**. Sanctum is `sanctum-pai`, served from the AI Platform BYOA surface. So the situation is not "C6 has no implementation" — it is **two implementations converging on the same shape from different orgs, neither aware of the other in writing**: AI Tech's Engram going to HRZ prod (`DTAITECH-1469`), and PAI's Sanctum already answering MCP calls. The unowned-contract problem just became an unowned-*arbitration* problem.

**Actionable:** this is the single highest-value thing to raise. Either Sanctum belongs in the due diligence as a twelfth repo and a live candidate, or there is a reason it was excluded that is not written down anywhere.

## 3. TARS PRD
*(not captured; the section ends "…of that overlap. Worth naming explicitly rather than letting two schemas ship.")*

## 4. DeepInsights — the black box, substantially opened

Reference Architecture Open Question 2 reads: *"production infrastructure with the closest contract shape, but its source has not been inspected. Backend or model for the gateway? Undetermined."* That can now be moved forward without source access.

**Scale and production status.** From `DTSPEAR-2002` (Spike: Compare GWS Harness stack to Courier/Endzone/GSE — Closed, Dmitrii Serikov):

> "Deep Insights — enterprise knowledge base indexing repos and wikis; serves context to agents over MCP. Claimed 3,900+ users, 5,600+ repos, 240+ products."

From `DTSPEAR-2029`, written after that spike closed:

> "Deep Insights is already integrated — both Endzone and GSE consume it in production today."

This is the fact that most changes the picture. The Courier vs. Endzone page (16 Sep) describes Endzone's retrieval as its own Confluence/repo/runbook embedding pipeline and says nothing about DeepInsights. If Endzone consumes DeepInsights in production, either the harness comparison is incomplete on that point or the integration post-dates it — worth reconciling, because Part 11 item 4 ("nothing currently fills the C6 slot") rests partly on that page.

**The tool surface — no longer opaque.** From *Deep Insights MCP Server Guide* (2670115217, Charlie Zang, 18 Aug) and *Deep Insights Agent Skills Guide* (3057628287): two routes, both evidence-first.

*Repository route:* `resolve_deep_insights_target(kind="repo")` → `get_repository_status` → `onboard_repository` (index-only, poll 15–30 s) → `get_repo_agent_wiki` → then the narrowest evidence tool: `explore_code`, `explore_code_symbol`, `search_code` (keyword mode for identifiers, hybrid for concepts), `list_code_inventory`, `read_code_file`. Plus `get_datadog_cross_repo_dependencies` for runtime dependencies and `chat_with_repository` last.

*Product route:* `list_products` (caller-scoped) → explicit user confirmation → `resolve_deep_insights_target(kind="product")` → `get_deep_insights_knowledge_tree` → `read_deep_insights_knowledge_page` (≤5 initially) → `search_product_code` / `chat_with_product` / `list_product_document_sources`.

**What this settles against C6**

| C6 requirement | DeepInsights evidence |
|---|---|
| One interface, not one store | **No.** ~50 tools (orchestrate-deep-insights pilot, 3032185370) with a skill layered on top to route among four flows. That skill exists *because* the surface is not one verb |
| Declared scope per call | **Yes, strongly.** Caller-scoped `list_products`; auth per repository or Product; mandatory explicit confirmation before Product evidence is retrieved |
| Provenance and freshness on every retrieval | **Yes.** Repo/branch/path/line-range citations required; Knowledge Tree carries statuses and freshness warnings; *"report Knowledge Tree freshness and missing prerequisites instead of filling the gap"* |
| Read/write separation | **Yes, absolute.** *"Do not generate a Product KB or Wiki, add Product sources, onboard repositories in the Product flow, or substitute generated artifacts for source evidence."* Index-only onboarding, never content generation |
| `snapshot` — versioned point-in-time view | **No.** Nothing resembling it. Freshness is surfaced as a warning, not pinned |

**Verdict for Open Question 2: backend, not gateway model.** DeepInsights is the strongest evidence-[…] *(rest not captured)*

---

## First read: what the addendum changes

1. **A PAI-side gateway already exists.** Sanctum is a live MCP `retrieve`/`write` surface inside the Jetstream page tree, from the same org as the PAI Context Graph. The gap analysis's "build the federation gateway" becomes **"Sanctum is the gateway shell; contribute what it lacks."** What it lacks is exactly this pack's core: `snapshot`, mandatory scope, receipts, entitlement brokering, and a closed `kind`. Building a second PAI gateway would repeat the AMS/Sanctum problem inside one org.
2. **`snapshot` is confirmed as the real gap by three independent absences**: the eleven-repo survey, Sanctum, and DeepInsights. Nobody has it. The ledger's positioned, immutable history plus a signed manifest is the one thing on the table that no other candidate can supply.
3. **Sanctum's response shape is better than the reference architecture's**, and the pack should adopt it: `evidence[]` with `validity{status, last_updated, verified_by, expires_at}` is `freshness` plus the certification state plus the staleness flag in one field. `score` as rank-fused position, not similarity, matches the evidence catalogue's rule that listwise scores are positions, not absolutes.
4. **Two conflicts to resolve, not paper over:** skills through the knowledge interface (Sanctum) vs. skills as a C4 sibling (Nitin, resolved "no"); and `domain="auto"` default-open vs. scope mandatory. The pack sides with the contract on both. The gateway's scope resolver and closed `kind` are contributions, not criticisms.
5. **DeepInsights is a backend, at scale, already in production behind Endzone and GSE.** ~50 tools, strong per-call scope, mandatory provenance, absolute read/write separation, no snapshot. It is the first-class registry entry for `kind=document` over code and wikis, and its "report freshness and missing prerequisites instead of filling the gap" rule is the same posture as the fault-adjudication rule. It also means Part 6's "Endzone has its own pipeline" is incomplete; the swap-test pair should be *DeepInsights vs. the PCG ledger behind Sanctum*, not Endzone's local KB.
6. **The PAI Context Graph is absent from the programme's due diligence.** With Sanctum also uncited, PAI has two artefacts the programme has not looked at. The actionable item in the addendum applies to both: get them into the twelfth and thirteenth rows, or learn why not.
7. **The arbitration problem is the real one.** AMS heading to HRZ prod, Sanctum live on BYOA, DeepInsights in production behind two harnesses, and C6 unowned. The gateway-level schema and the snapshot manifest are the neutral ground: they do not require any of the three to yield, they require each to be registered with a manifest and to be pinnable.
