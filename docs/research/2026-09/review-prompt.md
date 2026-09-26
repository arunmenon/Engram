# Review request: Engram's direction, bets and evidence

*Prepared 2026-09-26 for an independent second opinion. Self-contained: everything a reviewer needs is in this document or linked from it. Please read the "What we want from you" section first.*

---

## What we want from you

You are reviewing an architecture direction for **Engram**, a memory infrastructure for AI agents, and the reasoning behind a proposed set of pivots. We want an adversarial, evidence-weighted critique, not agreement. Specifically:

1. **Are the bets right?** For each of the seven bets in §3, say whether the cited evidence actually supports it, whether we are over-reading thin evidence, and what evidence would change your mind.
2. **What are we missing?** Papers, systems or results from 2026 that contradict or materially strengthen a bet, especially anything on forgetting, feedback loops, abstention, or graph-vs-vector lift at matched budget.
3. **Are the pivots the right pivots?** §4 lists four pivots and three stops. Argue against each. Is there a pivot we should be making and aren't? Is any pivot premature given the implementation state in §2?
4. **Is the discovery plan sound?** §5 lists prerequisites and eight hypotheses with kill criteria. Are the kill criteria honest? Are the hypotheses ordered correctly? Which would you drop, merge or add? Is five weeks credible?
5. **Positioning.** §6 states the intended differentiation. Is it defensible against Mem0, Zep/Graphiti, Letta, Hindsight, Beacon, JITMem-style systems? Where is it a story rather than a moat?
6. **Steelman the opposite.** Give the strongest case that Engram should *not* pivot — that the February design (typed graph as the primary read surface, neuroscience-grounded decay as the differentiator) is right and the 2026 results are benchmark artefacts.

Please rate confidence per answer and distinguish "the evidence says" from "I think". Where you cite work we did not, give the URL.

---

## 1. What Engram is

Engram (working name "Context Graph" in the whitepaper) is a traceability-first memory layer for AI agents. Repository: https://github.com/arunmenon/Engram. Design intent:

- **Immutable event ledger** in Redis Streams as the source of truth. Every agent/tool action is an append-only event with `event_id`, `event_type`, `occurred_at`, `session_id`, `agent_id`, `trace_id`, `payload_ref`, `global_position`; idempotent ingest via a Lua script; never mutated. (ADR-0004, ADR-0010)
- **Derived graph projection** in Neo4j, disposable and rebuildable from the ledger. 11 node types (Event, Entity, Summary, UserProfile, Preference, Skill, Workflow, BehavioralPattern, Belief, Goal, Episode) and 20 edge types (FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES, SAME_AS, RELATED_TO, DERIVED_FROM, SUPERSEDES, CONTRADICTS, CONTAINS, …), grounded in W3C PROV-O. (ADR-0003, ADR-0009, ADR-0011, ADR-0012)
- **Four async consumers**: per-event structural projection; LLM extraction at session end (entities, preferences, skills, summaries); embedding enrichment; scheduled consolidation every 6 h (episode grouping, hierarchical summaries, workflow-pattern detection, importance recomputation, forgetting). (ADR-0005, ADR-0013)
- **Retrieval**: rule-based intent classification into 8 intents → seed-strategy dispatch → intent-weighted edge traversal → 4-factor decay scoring (Ebbinghaus recency with access reinforcement, importance, relevance, user affinity) → provenance-annotated "Atlas" response. Roadmap: hybrid retrieval (vector + BM25 + graph via RRF), PPR, HyDE. (ADR-0006, ADR-0008, ADR-0009)
- **Forgetting**: four retention tiers (hot / warm / cold / archive) with archive-before-delete. (ADR-0007, ADR-0008, ADR-0014)
- **Multi-tenancy, security, observability, billion-scale architecture** added March 2026 (ADR-0016–0018); a separate codebase has since added ADRs 0019–0030 (LLM gateway, evaluation suite, API v1 contract, grants, GDPR crypto-shred, tenant configuration, disaster recovery) that are not yet in this repository.

Primary references:
- Whitepaper (March 2026): `context-graph-whitepaper.docx` in the repo root; ADRs: https://github.com/arunmenon/Engram/tree/dev/docs/adr
- February 2026 research that grounded the ADRs (29 files): https://github.com/arunmenon/Engram/tree/main/docs/research — MAGMA, A-MEM, HippoRAG, HiMeS, Generative Agents, MemGPT/Letta, Zep/Graphiti, Mem0, Cognee, GraphRAG, PROV-O, PG-Schema, SHACL, Redis Streams feasibility.
- **September 2026 research restart** (the material this review is about): https://github.com/arunmenon/Engram/tree/claude/wonderful-ramanujan-2cxghz/docs/research/2026-09 — start with `README.md`, then `paper-digests.md`, `memory-research-landscape.md`, `rsi-positioning.md`, `jev-typed-decisions.md`, `judgment-points-catalogue.md`, `write-read-path-scale.md`, `pdlc-memory-layer.md`, `discovery-plan.md`, and the primary-source evidence catalogue under `evidence/`.

**New product requirement** driving this review: a knowledge/memory layer for the **product development lifecycle** — requirement → HLD/LLD → tickets → PRs — where agents work across hours, sessions and hand-offs and must know what was decided, why, on what evidence, what superseded it, and what happened when it was tried.

## 2. Implementation state (so the review is grounded in what runs, not what the ADRs say)

From static code review of branch `feature/autoresearch-eval-scoring` (same application source as `dev`), documented in `judgment-points-catalogue.md` and `write-read-path-scale.md`:

- **Confirmed defects**: batches of >10 events lose their payloads (extraction sees no content); the RediSearch index prefix doesn't match the key prefix, so BM25 search, `get_by_session` and admin replay return nothing; Redis retention double-prefixes keys and never deletes, with `noeviction` and no `maxmemory`.
- **Declared but not implemented**: nothing creates SIMILAR_TO edges or Belief, Goal, Workflow, BehavioralPattern or Episode nodes; belief-contradiction, entailment check and user-affinity scoring are never called; MMR runs but never changes ranking; ADR-0018's sharding/federation/Kafka phases have no code.
- **Silent failure**: any LLM extraction failure (including an open circuit breaker) returns an empty result and the message is acknowledged, so that session is never re-extracted.
- **No receipts**: almost no decision (intent, seed strategy, entity merge, supersession, deletion, extraction acceptance) is recorded with its inputs; model/prompt provenance on DERIVED_FROM is lost to a field-name mismatch.
- **Self-approval**: the extraction LLM assigns its own confidence and the source label that sets its confidence ceiling.
- **Tenant-blind entity resolution**: all tenants' entities resolve against and write into `default`.
- **Eval harness leaks labels**: query embedding built from gold nodes; intent taken from the gold label; 8-d SHA-256 "embeddings"; the LLM proposer could rewrite the judge. Reported autoresearch gains (0.699 → 0.737) do not measure the production path.
- **Neo4j deletion without archive** in cold/archive tiers; compaction's cross-reference guard matches the wrong edge direction and never protects anything.

A reviewer should assume the *ledger and ingest path* are real and sound in design, the *graph projection and retrieval* are partially real, and the *cognitive layer* (beliefs, workflows, episodes, principled forgetting) is design only.

## 3. The bets, and the evidence behind each

Evidence strength is our own grading: **strong** = multiple independent sources or ablated paper; **moderate** = one paper or one careful benchmark; **weak** = vendor/builder report or single unablated result. Full notes with numbers are in `paper-digests.md` (D1–D8) and `memory-research-landscape.md`.

### Bet 1 — Append-only raw ledger; never curate at write time *(keep; strengthened)*
- **Claim.** Store every observation losslessly; defer what-matters decisions.
- **Evidence.** JITMem (Salesforce, arXiv 2609.27334, https://arxiv.org/abs/2609.27334): write-time distillation before storage costs 1.7–8.2 SR; untrained read-time curation beats RL-trained write-time methods. Eywa (arXiv 2605.30771): "evidence before belief", 90 % LoCoMo. Mem0 v3 (Apr 2026) dropped UPDATE/DELETE — "memories accumulate" (https://mem0.ai/changelog). Jev-Mem (arXiv 2609.23986) sets `admission_enabled=false`. MemPalace, Instinct, ProjectMem (arXiv 2606.12329) all store verbatim. **Strong.**
- **Where we could be wrong.** JITMem's gains are on ALFWorld/WebShop/τ²; the SE domain is only covered by DreamBench-SWE (arXiv 2608.20664), where verbatim event memory scored 82/180 vs 21 no-memory but a Mem0 config scored 97.

### Bet 2 — The typed graph is an index and lineage structure, not the read surface *(pivot from "query-optimised projection")*
- **Claim.** Keep Neo4j for lineage, entity, supersession and negation questions; stop treating projected summaries/extractions as the only thing agents read.
- **Evidence for the graph's value.** MOOSEDev (arXiv 2608.13662): typed graph with supersession answers supersession/set-completeness/negation at 0.98–1.00 vs 0.06–0.27 for top-k vector. TraceDev (ISSTA 2026, arXiv 2607.18886). REALM (arXiv 2609.16053): write-time `supersedes`/`contradicts` edges drive knowledge-update score 84.7 → 88.9 vs Zep 74.4 (ablated). **Moderate–strong** for these question classes.
- **Evidence against the graph as primary read surface.** Selective Forgetting negative result (arXiv 2608.28978): a graph with almost exactly Engram's pruning formula (recency + access + centrality + age) lost to flat vector on LongMemEval at matched budget (F1 0.417 vs 0.468). MemDelta (arXiv 2606.29914): an 11-pt "graph wins" reversed to −1.2 when only the embedder changed. JITMem as above. Context Compaction Theory (arXiv 2608.01326): generation can need strictly less budget than selection. **Moderate.**
- **Where we could be wrong.** These are chat-memory benchmarks; PDLC questions may be exactly the class where the graph wins (MOOSEDev). That is H2 and H7.

### Bet 3 — Neuroscience-grounded decay is a hypothesis, not a differentiator *(demote)*
- **Claim.** Do not market or invest in tiered forgetting until it is shown to help.
- **Evidence.** In the evidence bundle no source implements forgetting that measurably helps: Jev-Mem records obsolescence and never acts on it; REALM and Hindsight have no decay; Hippo-memory's own audit found age decay had no effect and consolidation cost 3.6 points (https://github.com/kitfunso/hippo-memory). Selective Forgetting as above. Control-Plane Placement (arXiv 2606.15903) shows *where* the LLM sits determines which forgetting failures recover. **Moderate (absence of evidence, consistently).**
- **Where we could be wrong.** Benchmarks rarely exercise decay (LongMemEval never does). Microsoft's Human-Inspired Memory (arXiv 2605.08538) and RoMem (arXiv 2604.11544, per-relation volatility, 2–3× on temporal QA) suggest *specific* decay mechanisms may help even if uniform Ebbinghaus doesn't.

### Bet 4 — The missing primitive is the outcome loop: retrieval receipts + outcome events *(new)*
- **Claim.** Memory value comes from closing the loop from task outcome back to the memories that were served; Engram has no outcome signal today (only `access_count++` on return).
- **Evidence.** Every large 2026 result gates or trains on outcomes: JITMem (GRPO on immediate task reward), Recuris (arXiv 2608.24876, validation-gated patches, +17.8 τ²), TRACE (arXiv 2608.22793, contrastive rounds, Pass^3 59.9 → 94.5), Memp (arXiv 2508.06433, deprecate on failure), ReasoningBank (arXiv 2509.25140, judge → extract from success and failure), Mendel Gödel Machine (arXiv 2608.07645, selection on per-task outcomes; comparative evidence provably raises fix probability). Oblivion (arXiv 2604.00131): reinforce what *contributed*, not what was *retrieved*. Beacon (https://github.com/Asymptote-Labs/agent-beacon) gates promotion on `task_success`. Ungated evolution (A-MEM, HeLa-Mem) scores lowest. **Strong** that outcome gating matters; **weak** on the specific reinforcement formula (REALM's reconsolidation adds only +2).
- **Where we could be wrong.** Feedback loops (wrong memory recalled → reinforced) are unmeasured in every source; REALM uses the same model to answer and audit. H4 measures the loop rate explicitly.

### Bet 5 — Procedural memory (workflows, lessons, anti-patterns with outcome statistics and versions) is the product for the PDLC use case *(re-prioritise over the user-personalisation layer)*
- **Claim.** Workflow / Lesson nodes with per-task outcome records, multi-parent SUPERSEDES, and an `avoid` polarity are where value concentrates for repeated engineering work.
- **Evidence.** RSI taxonomy (Zheng, Sep 2026) and its Memory/Skill column; AWM (arXiv 2409.07429), Memp, ReasoningBank, HyperSkill (arXiv 2608.16114), SkillSmith (arXiv 2606.01314, anti-pattern veto), MediSkill-Evo (arXiv 2608.23397, typed validation), Evo-Harness (arXiv 2608.15071); LongMemEval-V2 (arXiv 2605.12493) now scores workflow knowledge; JITMem's τ² result: memory helps most where tasks need synthesised procedural guidance (Telecom +11), not fact lookup. MGM App. F.3/H: what evolution actually discovers is a *workflow*. **Strong** that this is where 2026 gains are; **moderate** that a versioned graph is the right store (nobody has built one; MOOSEDev is closest).
- **Where we could be wrong.** "Raw trajectories often beat distilled skills, and generated skills sometimes make results worse" (EvoSkill roundup, arXiv 2603.02766; JITMem). The answer may be "store trajectories + curate at read time" with workflows only as a cache — which is why Bet 6 and Bet 5 are tested together (H3, H6).

### Bet 6 — Read-time, task-conditioned curation over raw payloads, behind a retrieve-or-not gate *(new)*
- **Claim.** At task start, the graph selects evidence, an LLM writes a task-specific briefing from raw payloads, the briefing is ephemeral, its receipt is a ledger event.
- **Evidence.** JITMem (above; +16 SR, 5–7× smaller payloads, transfers across executors). MRAgent (arXiv 2606.06036, "reconstructed not retrieved"). Supermemory's harness-hook recall/no-recall gate (qualitative). Anthropic/OpenAI memory shifting away from session-end extraction. **Moderate** (one strong paper, one domain family).
- **Where we could be wrong.** Adds an LLM call at task start (Eywa's and our own zero-LLM read-path rule). We scope it to `how_does`-shaped requests behind a gate; τ² Airline/Retail showed no memory method beats no-memory on fact-shaped tasks.

### Bet 7 — A typed-decision tier (System-One / Jev-class) for closed-label memory decisions, never for open agent choices *(new, hedged)*
- **Claim.** Use a fast typed decision model as the independent judge for extraction acceptance, entity merges, supersession, delete/archive, promote/review/discard, listwise admission and stop rules — with receipts — and keep rules and an open model as fallbacks.
- **Evidence.** Jev-Mem (LoCoMo 0.777 vs 0.700 MAGMA, build 6.6× faster; **one benchmark, no ablations**). Hindsight listwise rerank recall@1 0.94 vs 0.87 per-candidate, 30× fewer calls (vendor). Sentry: Jev as eval judge, same accuracy, ~200× cheaper (one week, one team). Deel 70→97 % on bounded matching but −16.6 on messy metric picks. Negative: six fast actions inside a coding agent all dropped (small n); Beacon's "reason" field returned the literal string `"noul"` (issue #620); supermemory's sentence-level filter broke meaning; calibration claimed but unproven (Jev-Mem authors say scores aren't calibrated probabilities; Datadog logged values >1). Vendor docs: https://docs.typesafe.ai (US-hosted only, no ZDR on standard plans). **Weak–moderate**, and vendor-concentrated.
- **Where we could be wrong.** The whole tier could be replaced by a small NLI/reranker model or rules for most gates; the honest test is H5.

## 4. Proposed pivots and stops

**Pivots**
1. From "memory store" to "memory loop": receipts + outcome events first; everything else hangs off them.
2. From write-time abstraction as the read surface to read-time curation with the graph as selector; Consumer 2/4 outputs become retrieval cues and cached curations.
3. A typed-decision tier only where labels are closed; behind a port with rule and open-model fallbacks; every decision leaves a receipt.
4. Procedural memory first; user personalisation kept as a feature, not the lead.

**Stops**
- Don't build harness collectors (Beacon has 20+; ingest its OTel-normalised JSONL instead).
- Don't compete on reranking (dedicated rerankers match Jev at ~1/10 cost on clean text).
- Don't self-modify code in production (MGM/RRSI/Google harness-rewrite warnings; keep the evaluator outside the memory write path to stay at RSI level L2, arXiv 2609.11873).

**Explicit tension to resolve in an ADR.** ADR-0003 calls the Neo4j projection "query-optimised". For procedural memory the 2026 evidence says the query-optimal form is raw traces plus a task-conditioned reader; for lineage/supersession the typed graph wins. Both should be stated; the current ADR states only the first.

## 5. Discovery plan (summary; full version in `discovery-plan.md`)

**Ground rules** (RRSI, arXiv 2609.24972): noise floor from ≥5 baseline runs; one attributable change per round; charge memory for tokens; experiment ledger outside memory; frozen judge and held-out split containing knowledge updates, contradictions, abstentions, long-hop causal chains and workflow-knowledge questions.

**Prerequisites (week 1):** fix the three confirmed defects and tenant-blind resolution; replace the leaking eval harness; add `task_key` and `task.outcome` / retrieval-receipt event types (additive).

| H | Hypothesis | Benchmark | Kill criterion |
|---|---|---|---|
| H1 | Raw ledger alone beats no-memory on SE tasks | DreamBench-SWE | < 2× no-memory |
| H2 | Graph adds lift over flat vector at matched budget | MemDelta protocol on LongMemEval-S + MemFail long-hop | ≤ baseline + noise |
| H3 | Read-time curation beats projected summaries for `how_does` tasks | τ²-style procedures / PDLC seed set; 3 arms | ≤ best write-time arm, or >1.5× tokens |
| H4 | Outcome-linked reinforcement beats access-count reinforcement | replayed task stream with outcomes | no gain, or feedback-loop rate not lower |
| H5 | Independent typed gate beats self-reported extraction confidence | 90 labelled items, half for threshold fitting | F1 not better, or ECE > 0.15 |
| H6 | Comparative (multi-trajectory, sibling-success) workflow induction beats single-trajectory | same Episode set, re-use on held-out `task_key` | ≤ single + noise |
| H7 | Typed supersession beats vector on PDLC questions | ~300 typed records, MOOSEDev question classes | graph < 0.9, or graph − vector < 0.3 |
| H8 | Sufficiency stop rule beats fixed top-k | H2 harness | accuracy drop > noise, or < 20 % token saving |

Sequencing: week 2 H1+H2 (decide the architecture story); week 3 H3+H5; week 4 H8+H4; week 5+ H6+H7. Rewrite the plan after H2.

## 6. Intended positioning

"Engram is the substrate a self-improving agent's update mechanism writes into: an immutable trajectory ledger, a typed lineage index, outcome-linked receipts, gated and versioned procedural memory, and a task-conditioned read path — with every memory mutation auditable and reversible from the ledger." Claimed differentiators vs the field: (a) provenance and versioning as a *graph* with multi-parent lineage, not git history or overwrite; (b) outcome-linked rather than recall-linked reinforcement; (c) procedural memory with per-task outcome records and an `avoid` polarity; (d) a decision tier that leaves receipts; (e) a governance story (evolves data, never code; auditable; stays at RSI L2) that is now a selling point given the regulatory direction.

We suspect (a) and (e) are real, (b) and (c) are unbuilt by anyone and therefore unproven, and (d) is table stakes within a quarter.

## 7. Specific questions we'd like answered

1. Is there any published result showing tiered/decay forgetting **helping** end-task accuracy at matched budget? If not, is Bet 3's demotion too timid (should decay be removed from the roadmap entirely)?
2. JITMem's read-time-curation result: does it survive in domains with long, structured artefacts (design docs, PRs) rather than short trajectories? Any evidence either way?
3. For PDLC traceability specifically, is a property graph the right substrate, or would an event-sourced relational model with materialised views serve the same MOOSEDev question classes at lower operational cost?
4. Is the receipt/outcome-event design (ledger events linking served memories to outcomes) the right primitive, or is there a simpler signal we're overlooking?
5. Is the typed-decision tier worth its vendor and egress risk at all, given open alternatives (GLiNER2.5-Decide, small NLI/rerankers) and the calibration findings? What would a minimal, vendor-neutral version look like?
6. Given the implementation gaps in §2, is the right move to fix and extend this codebase or to restart the graph/consumer layers around the ledger? What would you keep?
7. What is the single experiment you would run first, and why is it not H1 or H2?

## 7b. Added after the programme documents arrived (26 Sep, later the same day)

Since §1–§7 were written, two things changed the context the bets have to serve. First, a second evidence pass (38 items, 6 repos read at pinned commits) added a worked per-turn save gate (`jevmem`), a "consolidation as a separate phase" trend with **no on/off measurement anywhere and one negative result**, and a "staleness and provenance" trend that is entirely practitioner opinion. Second, the internal programme that would adopt Engram published its knowledge contract: one interface with `retrieve / write / snapshot`, scope declared per call, "integrate the store, do not absorb it", a swap test as the conformance criterion, a normalised response of content + provenance + freshness + confidence, a **fault-adjudication rule** (was the missing piece spec-type, tribal, or a harness error, decided from an assumptions ledger), and a knowledge-gap loop that *replays what the interface returned* for a scope at a snapshot. `snapshot` — a versioned, signed point-in-time view — is stated to exist in no surveyed system. The programme also has several existing knowledge hubs (a production code-and-wiki knowledge service, a certified-fact memory service from another org, an early two-verb MCP gateway), so the memory layer is a federation over hubs, not one store. Please review the bets again through these lenses:

8. **Point-in-time reads as a research gap.** Nothing in the memory literature we surveyed treats reproducible retrieval (the same scope returning the same evidence for the same `as_of`) as a first-class property; benchmarks never measure it. Is that because it is trivial, unsolved, or unmeasured? Is an immutable positioned ledger necessary for it, or does a manifest of per-backend version pins over the backends' own versioning suffice? For backends with no versioning (wiki pages, ticket bodies), is materialise-and-sign a legitimate snapshot or a copy that violates "do not absorb"?
9. **Receipts joined to outcomes, at build-time latency.** Bet 4 (outcome-linked reinforcement) assumed a task score minutes later. In the programme, the outcome is an escape or an RCA days or weeks later, joined through a Spec id and a snapshot id. Does H4 survive that delay and that join? Does any published system produce a retrieval receipt at all, and is the fault-adjudication label (spec / tribal / harness) actually decidable from an assumptions-ledger entry plus a replayed receipt, or does it need the very knowledge that was missing?
10. **Federated retrieval across heterogeneous hubs.** The bets assumed one store. What does the literature on federated search and cross-collection fusion say about fusing a code-knowledge service, a certified-fact store, a ticket corpus and a raw event ledger under one token budget? Does reciprocal-rank fusion (k = 60, used by two independent designs in the evidence) hold when backends return different granularities (line ranges, facts, whole pages, episodes)? Where does a query planner over a registry become the new monolith?
11. **Consolidation and forgetting with no positive evidence.** The only consolidation measurement in either evidence pass is −3.6 points; no source shows decay or forgetting helping. Defend or kill scheduled consolidation and tiered decay as roadmap items. If kill, what replaces "summaries as a read surface" at the Spec call site?
12. **Staleness and provenance.** The rules we adopted (store decisions with date and reason; per-item source class; a periodic "still true given the current snapshot?" audit that flags, never deletes; an injection gate on served memory, since extracted items came from untrusted transcripts and are re-injected into prompts) rest on low-engagement posts and one repo's author-written eval (20/22 planted lines blocked, 0/22 false). What would count as evidence that any of these pays for itself, and which would you drop?
13. **Typed decisions at build time, not chat time.** The field rules we took — listwise choice over per-item yes/no (0.94 vs 0.87 recall@1, 30× fewer calls), never a "none relevant" option, pruning off by default, always return ≥1 — come from conversational memory benchmarks. Do they invert when a wrong retrieval costs a wrong implementation rather than a bad chat turn? Which of our planned decision points (route across backends, budget split, listwise rerank, sufficiency stop, per-item confidence, ontology tagging, injection gate, write admission, supersession, fault adjudication, staleness, cross-hub conflict) should *not* be a decision-model call? Is an ordinal "confidence" over (content, provenance, freshness, agreement) a real signal or rank position laundered into a number callers will read as a probability?
14. **Escalation tiers.** One repo's held-out result had the larger, more careful decision battery scoring *below* the cheap one (90.9 % vs 95.5 %). Does that generalise? What does it imply for any two-tier gate (cheap battery first, escalate when borderline), and how should escalation be validated before it is trusted?
15. **Read-time curation versus reproducibility.** Bet 1's read-time curation (JITMem) produces a task-conditioned briefing at the Spec step. PR review must later re-resolve *the same snapshot*. Can a curated briefing be both useful and replayable, or does curation have to be a deterministic function of (snapshot, task) with its own receipt? What breaks if the curating model changes between Spec and review?
16. **The graph, again, under the contract.** With a swap test as the conformance criterion, a backend-held schema fails by construction; the ontology (eleven dimensions, no schema yet) must live at the gateway. Does that settle Bet 2's question (graph as index for lineage/supersession/entity questions, not the read surface), or does it make the graph one backend among many with no privileged role? What, if anything, does a property graph contribute to a federation that a positioned ledger plus a signed manifest does not?
17. **Order of experiments, revised.** Given 8–16, re-answer question 7: what is the single experiment you would run first, and is it still not H1 or H2?

## 8. Source index (URLs)

Repository: https://github.com/arunmenon/Engram · September pack: https://github.com/arunmenon/Engram/tree/claude/wonderful-ramanujan-2cxghz/docs/research/2026-09

Papers: JITMem 2609.27334 · Mendel Gödel Machine 2608.07645 · Jev-Mem 2609.23986 · REALM 2609.16053 · EvoSkill 2603.02766 · RRSI 2609.24972 · RSI levels 2609.11873 · Eywa 2605.30771 · Agent Zero Memory 2608.29606 · MemIR 2605.25869 · Stored Is Not Supported 2609.02127 · Human-Inspired Memory (Microsoft) 2605.08538 · RoMem 2604.11544 · Nous 2606.22030 · MemTX 2607.23929 · TARL 2608.03699 · TEPA 2608.07429 · Oblivion 2604.00131 · Selective Forgetting (negative) 2608.28978 · Control-Plane Placement 2606.15903 · MemClaw 2606.24535 · MAP-Graph 2608.10509 · AkasicMEM 2609.25563 · MemReranker 2605.06132 · EARM 2608.22767 · Context Compaction Theory 2608.01326 · Governance Decay 2606.22528 · LongMemEval-V2 2605.12493 · MemTrace 2606.17328 · MemDelta 2606.29914 · MemOps 2607.12893 · MemFail 2605.26667 · Ground Truth First 2607.21962 · D²ACCI 2608.17756 · AuthMem-Bench 2608.01679 · DreamBench-SWE 2608.20664 · ANCHOR 2606.01208 · Shifty 2608.15948 · Alper 2605.25814 · ProjectMem 2606.12329 · EA-Graph 2608.04278 · MOOSEDev 2608.13662 · TraceDev 2607.18886 · Trust-Aware Traceability 2606.17203 · AWM 2409.07429 · Memp 2508.06433 · ReasoningBank 2509.25140 · Mem²Evolve 2604.10923 · HeLa-Mem 2604.16839 · HyperSkill 2608.16114 · Recuris 2608.24876 · Prime Agent 2608.23552 · TRACE 2608.22793 · SkillSmith 2606.01314 · MediSkill-Evo 2608.23397 · Evo-Harness 2608.15071 (all at `https://arxiv.org/abs/<id>`).

Systems: Beacon https://github.com/Asymptote-Labs/agent-beacon · Hindsight https://github.com/vectorize-io/hindsight · Hippo-memory https://github.com/kitfunso/hippo-memory · Graphiti releases https://github.com/getzep/graphiti/releases · MemOS https://github.com/MemTensor/MemOS · MemPalace https://github.com/mempalace/mempalace · Mem0 changelog https://mem0.ai/changelog · MGM code https://github.com/RealLcz/MGM · TypeSafe/Jev docs https://docs.typesafe.ai · Awesome RSI https://github.com/lobehub/awesome-rsi.

Field reports (secondary): supermemory on Jev in memory pipelines and the Instinct teardown (X, Sep 2026, Dhravya Shah); Sentry's Jev-as-judge week; Deel and MotherDuck Jev results; RSI taxonomy article (Yaowei Zheng, LlamaFactory, Sep 2026). Transcribed and source-noted in `docs/research/2026-09/evidence/`.
