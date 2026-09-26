# Programme plan — a memory ecosystem, built as parallel tracks

**Date:** 2026-09-26 (rewritten the same day; the first version was framed by one design partner's contract and is superseded). **Companions:** [operating-plan.md](operating-plan.md) for cadences, [discovery-plan.md](discovery-plan.md) for the hypothesis register, [c6-ecosystem-gap-analysis.md](c6-ecosystem-gap-analysis.md) for the component map.

## 0. The frame

We are building a **memory ecosystem for agents that do engineering work**: a substrate that keeps evidence, a set of mechanisms that decide what memory becomes, read strategies that turn it into context, a judgment layer, an outcome loop that lets it improve, and an interop layer so it lives among other stores. Engram is the substrate MVP and one cog. Everything else is either a research question, a greenfield lab, or a proving ground.

Proving grounds, in order of how much they tell us per week: (a) public benchmarks with executable oracles; (b) open coding-agent harnesses we can instrument ourselves (hooks in Claude Code, OpenHands, Aider-class tools); (c) our own agents doing our own work, dogfood; (d) the enterprise design partner, whose eleven-contract programme is the hardest and most informative environment but also the slowest. The design partner is **one** of four. Its contract details live in Appendix A and nowhere else in this document.

## 1. Eight research pillars (topic taxonomy, v2 after review 2)

Pillars are the labelling vocabulary and the grouping for the register. Beliefs are kept separately in [beliefs.md](beliefs.md) so that revising a belief never relabels the archive.

| Id | Pillar (topic label) | Thesis | Boundary |
|---|---|---|---|
| R1 | Evidence and reproducibility | Decisions need identifiable source evidence and an explicit replay guarantee | evidence identity and preservation; what was served and can it be reproduced |
| R2 | State evolution and lifecycle | Updates, supersession, consolidation and retirement need distinct semantics | durable state changes to memory: write gates, supersession, consolidation mechanisms, retention, suppression, erasure |
| R3 | Retrieval and context assembly | Select sufficient authorised evidence within a bounded budget | request-time evidence selection: hybrid retrieval, traversal, curation, stopping, budgets |
| R4 | Decision quality and abstention | Automate a decision only when its error costs and uncertainty are understood | rules, classifiers, NLI, rerankers, typed decision models, larger models and human review as candidate implementations; abstention; calibration; escalation |
| R5 | Learning from experience | Outcomes may improve future behaviour if attribution and transfer are valid | receipts joined to outcomes, negative evidence, procedure induction, transfer, harmful reinforcement, self-improvement levels |
| R6 | Evaluation and research integrity | Conclusions require traceable protocols, independent checks and uncertainty | whether an evaluation supports its conclusion: leakage, judge bias, statistics, cost accounting, replication |
| R7 | Interoperability and coordination contracts | Agents and stores need explicit, testable exchange and capability semantics | cross-store compatibility: interfaces, registries, replay levels, swap tests, mappings, multi-agent handoff contracts |
| R8 | Trust and governance | Evidence cannot authorise its own use, execution or promotion | identity, permissions, suppression, poisoned or injected evidence, execution authority, review ownership, recovery |

**Labelling rules.** Topic labels are not beliefs: an agent classifies a graph-retrieval paper under R3 whether it supports or contradicts our preferred design. Assign one **primary** pillar by the claim being tested and optional **secondary** pillars; add separate tags for mechanism, workload, lifecycle stage and evidence dimensions (directness, control quality, independence, reproducibility, applicability). A paper can contain several claims with different labels. Cross-cutting tags carried on every item: `shared_state` (multi-agent), `cost`. Vendors and models are source tags, never pillar boundaries. Current beliefs live in the [belief register](beliefs.md) and change only through revision events.

## 2. Tracks

Six tracks. Each has a mission, scope, pillars served, proving grounds, deliverables by week, and its first two weeks. Staffing assumption: one lead per track; leads may sit on a second track. If fewer, merge T3 labs into T2 and keep the gates.

### T0 · Intelligence (the scraping team)

**Mission.** A weekly, evidence-graded picture of what is moving across all seven pillars and the competitive landscape, delivered as proposal cards WS-T5 can test, not as links.

**Scrape.** X (watchlist below, always expand threads, quotes, links, images, capture engagement and time); arXiv daily cs.AI/cs.SE/cs.IR/cs.CL filtered by pillar keywords; GitHub releases and closed issues for the landscape set (Graphiti, Hindsight, Hippo-memory, Beacon, Mem0, MemOS, Letta, MemPalace, jevmem, agentrun, MGM, lintpal, plus OpenHands and Claude Code hooks ecosystems); vendor posts (TypeSafe, supermemory, vectorize, Zep, Datadog, Sentry engineering); benchmark changes (LongMemEval, LoCoMo, DreamBench-SWE, MemDelta, MemFail, MemTrace, MOOSEDev, GroupMemBench); funding and launch announcements in agent memory.

**Watchlist to start.** Authors and orgs behind every source in the pack; the Jev builder set; RSI authors; memory-benchmark authors; the memory-startup set (Mem0, Zep, Letta, supermemory, vectorize, MemOS). Keywords per pillar: R1 provenance, receipt, replay, snapshot, point-in-time, ledger; R2 supersede, consolidation, forgetting, reconsolidation, gated write; R3 curation, just-in-time, context engineering, graph RAG, stop rule; R4 Jev, System One, typed decision, noul, classifier-in-the-loop, calibration; R5 self-improving, skill evolution, procedural memory, outcome, RSI, harness; R6 memory benchmark, leakage, held-out, ablation; R7 memory interface, MCP memory, federation, knowledge gateway.

**Do not collect.** Re-posts with nothing new; threads without a primary source; anything from the design partner's internal systems.

**Triage rubric.** (1) cluster by source and claim; (2) primary source reachable, else park with retry; (3) verify the relevant table or method, not the abstract: baseline, intervention, units, n, dataset, model, budget, uncertainty, evaluation method, `unknown` where absent; (4) evidence dimensions: directness, control quality, independence (shared authors, orgs, datasets, harnesses), reproducibility, applicability; (5) primary and secondary pillar plus tags; (6) beliefs affected: supports, contradicts, or would create; (7) contradiction against the belief register. Engagement prioritises examination; it is never the sole reason to discard. Keep a bounded exploration sample of low-engagement items and audit misses monthly.

**Outputs.**
- *Evidence note*, one per **claim cluster** (ten posts repeating one benchmark are one result), the `evidence/sources/` template: metadata, TL;DR, claims, numbers table with n and conditions, implementable mechanism, limitations and counter-evidence, takeaways, open questions; verbatim quotes for anything numeric.
- *Proposal card* to T5 intake: `id · claim (falsifiable) · source + strength · pillar/component · bets affected · proposed arms, metric, kill · cost S/M/L · urgency`.
- *Trend object* per theme: `trend_id · window · claim_ids · independent source groups · observed volume · query/watchlist version · cap and coverage limits · counterevidence · maturity (attention | implementation | controlled evidence | independent replication | adoption) · beliefs affected · proposed action`. Volume is normalised for watchlist and query changes; an attention trend is market intelligence, not confirmation.
- *Weekly delta*, Monday noon, one page: belief revisions (with evidence refs), beliefs held, cards and decisions, verdicts, contradictions, trends by maturity, landscape diff, capture health (items, clusters, primary-source rate, cap hits, missed-item audit), operations (last successful run per role, backlog age, duplicates suppressed, missing references, retries, budget).
- *Monthly*: refresh `memory-research-landscape.md` and the contradictions table; a competitive one-pager (capabilities claimed vs shown, per system).

**Interfaces.** All through the Google Drive bus `research-bus` (ids and rules in [`../queue/README.md`](../queue/README.md)): cards and notes out, decisions and verdicts back, watch requests from any track. T5 answers each card within fourteen days. Success is measured by informative experiments and decisions changed, not by cards per week; a quiet week can be correct. Kill rule: no primary source after four weeks → opinion.

**Needs from the CTO.** The scraper's current flow, fields, volume, output location and readers; then T0's handbook is fitted to it in week 1.

**Weeks 1–2.** W1 install rubric and templates on the existing flow; expand watchlist across pillars; backfill 14 days; first delta Monday W2. W2 first cards; first competitive one-pager; open watch requests from T2–T4.

### T1 · Engram core (brownfield; pillar R1, serves all)

**Mission.** Make the MVP the trustworthy substrate: correct ledger at scale, scope on every record, receipts and retained served artifacts, point-in-time reads over its own data, a versioned public interface, the graph as a lineage/supersession/entity backend.

**Scope in.** P1–P5; receipt event types and replay CLI; `retrieve/write/snapshot` over PCG data (write kinds episode vs fact-as-proposal; snapshot by stream position); response schema with provenance, validity, bitemporal fields; SUPERSEDES with two-signal rule and superseded state; fixtures and seeded histories for T5. **Scope out.** Federation, model-assisted decisions, harness adapters beyond what the proving grounds need, decay tuning, consolidation summaries.

| Wk | Deliverable | Done when |
|---|---|---|
| 1 | P1 defects fixed with failing-then-passing tests; restart/replay, boundary-batch, payload round-trip, tenant-negative, archive-recovery tests | green on a fresh stack; ingest contract documented |
| 1–2 | Scope `{caller, space, tier}` on every record; tenant through entity resolution | no cross-scope leakage in a seeded test |
| 2 | `retrieval.receipt`, `decision.receipt`, `snapshot.manifest`; served artifact retained by hash; replay CLI | every context call emits a receipt; replay is byte-identical |
| 2–3 | Three verbs over PCG data; snapshot by position | conformance kit (T4) passes against PCG alone |
| 3–4 | Response schema (content, provenance, validity, freshness, confidence components, valid/observation time) | validated in the kit |
| 4–6 | Graph re-scoped as a backend; SUPERSEDES real; SIMILAR_TO/CAUSED_BY creation behind a flag | H2 and H7 arms runnable |
| ongoing | Seeded fixture sets (supersession, contradictions, unavailable source, second tenant, late fact) | accepted into the frozen harness |

**Weeks 1–2.** Days 1–2 reproduce and fix the three defects; days 3–5 scope schema and negative tests; week 2 receipts, replay CLI, first verbs, running endpoint to T4, first fixtures to T5.

### T2 · Memory mechanics lab (greenfield; pillars R2, R3)

**Mission.** Settle, with measurements, how memory should be written, updated, consolidated and read. This is where most of the research pack's open questions live and where the product's second-order differentiation will come from.

**Scope in.** Gated writes (proposal → judge → commit) and the certification path; two-signal supersession; consolidation split by mechanism (summary generation, topology reweighting, pruning, schedule) with on/off arms; forgetting as a cost/quality trade, never as a default; read-time curation with the served artifact retained; graph vs hybrid at matched units and tokens; typed supersession/completeness queries vs SQL vs top-k; stop rule vs fixed k. **Scope out.** The decision model itself (T3), the interface (T4).

**Proving grounds.** Public benchmarks first (DreamBench-SWE, LongMemEval-S knowledge-update subset, MOOSEDev question classes); then our own agents' histories; the design partner only where a mechanism needs real specs.

| Wk | Deliverable |
|---|---|
| 1–2 | Arms built on T5's harness for H1 (raw vs none vs hybrid), H7 (typed queries vs SQL vs top-k), H3 (extractive vs cached summary vs curated briefing with retained artifact) |
| 3–4 | H1, H7 verdicts; gated-write MVP behind a port (proposal state, judge port, commit, supersede) raced against the current extraction path |
| 5–6 | H2 (graph vs hybrid) and H8 (stop rule) verdicts; H3 verdict; consolidation mechanisms separated and instrumented for H9 |
| 7–12 | H9 by mechanism; forgetting as explicit lifecycle (expiry, suppression, archive) measured on cost; curate step promoted or demoted; certification path MVP |

**Weeks 1–2.** Agree arms and datasets with T5 on day 1; build H1/H7/H3 arms against T1's endpoint and the public sets; write the gated-write port spec.

### T3 · Decision-quality lab (greenfield; pillar R4)

**Mission.** Find which decisions can be automated at a known error cost, which stay rules, and where abstention is required; candidate implementations are rules, NLI, rerankers, typed decision models, larger models and human review. Deliver one scorer that survives an independent challenge.

**Scope in.** Scorer port (typed input; label + abstain + diagnostics; model/version/timing); rule baseline per decision; label sets split by project and time (write admission ≥90; supersession pairs; injection benign set ≥149 independent; listwise rerank pools); H5 with escalation evaluated on the borderline population; H10b; confidence exposed as components plus one named ordinal score; per-route confusion matrices; latency classes. **Scope out.** Anything in a serving path before a shadow result; fault attribution beyond proposal-with-review.

**Proving grounds.** Our own labelled sets from public benchmarks and dogfood first; partner material where permitted.

| Wk | Deliverable |
|---|---|
| 1 | Port spec; rule baselines for admission, route, rerank, supersession, injection; label schema agreed with T5 |
| 1–2 | Three label sets frozen and held out |
| 2–4 | H5: rules vs NLI/reranker vs typed model on admission, in shadow; cascade evaluated on borderline cases |
| 5–6 | H10b injection gate bound; listwise rerank vs RRF order in shadow; verdicts |
| 7–12 | One scorer in production shadow behind T4's port (admission or rerank); confidence components live in receipts; supersession battery |

**Rules.** No threshold copied from elsewhere; cheap battery first; every battery ships with shadow and a confusion matrix; models never override the deterministic set.

### T4 · Interop and proving grounds (greenfield; pillar R7, hosts R1 fixtures)

**Mission.** Make the substrate usable from real agents in real environments, and prove it can live among other stores: harness adapters for the open proving grounds, the federation gateway, registry, declared snapshot levels, swap test, and the design-partner pilot as one instance of all of that.

**Scope in.** Adapters: Claude Code hooks (prompt-submit retrieve-or-not, session-end write), OpenHands or equivalent, our own agents; the federation gateway (registry with manifests, deterministic scope resolver and live authorisation, RRF fusion baseline, normaliser, snapshot composer per level, receipt writer, admission that may be empty, fallback plane); conformance kit with adversarial fixtures; the design-partner pilot (Appendix A). **Scope out.** Model-assisted routing until T3 hands over a shadow-ready scorer.

| Wk | Deliverable |
|---|---|
| 1 | Snapshot levels written (L1 served-bundle replay, L2 frozen corpus, L3 cross-store instant); conformance fixtures F1–F10 (Appendix A) as a generic kit, partner-neutral; first open-harness adapter (Claude Code hooks) against T1's endpoint |
| 2 | Kit v0 runs against PCG alone; registry manifest format; scope resolver; design-partner P0 run if the owners meeting has happened, otherwise the kit runs against PCG plus one open backend (e.g. a local vector store) |
| 3–4 | Two backends registered; RRF fusion; normaliser; swap test green in CI; second open-harness adapter; dogfood on our own work begins |
| 5–6 | Receipts durable in at least one live harness; L1 replay live; partner backends registered if available |
| 7–12 | L2 where backends allow; PR-review re-resolution in whichever proving ground has reviews; capability negotiation; C9-style outcome join where the environment emits outcomes |

**Weeks 1–2.** Snapshot-levels note and fixture kit on days 1–3; Claude Code hook adapter by day 5; kit against PCG by day 10; the partner owners meeting scheduled in parallel, not on the critical path.

### T5 · Hypotheses, experiments and beliefs (pillar R6, serves all)

**Mission.** Own the register, the belief register, the frozen harness, the statistics, the datasets and the ledger; run the queue across all tracks; issue verdicts that reference run bundles and reviews; revise beliefs through events.

**Roles inside T5** (responsibilities, not seven agents; one scheduler can invoke bounded roles, with proposer, executor and evaluator inputs kept separate): *hypotheses/portfolio* (mapping to beliefs, dedup at claim level, experiment specs, queue decisions, prioritised by decision value against total cost with an exploration allowance); *independent challenger* (attribution, baselines, leakage, alternatives, budget; outcome `ready | revise | insufficient_evidence`; triggered for expensive runs, central-belief changes, novelty claims, contradictory sources, promotions, plus a random sample); *executor* (runs the frozen spec inside the standing budget policy, produces the `runs/` bundle, never certifies its own result); *verdict* (protocol compliance, statistics, disposition including `inconclusive`); *projector* (indexes, weekly delta, mirror). The external reviewer has offered to take the challenger role and later bounded execution.

**Scope in.** Register as experiment cards; intake from T0 cards and T1–T4 requests; harness freeze (real embeddings, query text embedded, intent from the classifier, scoring from the domain module, held-out split by project/time, frozen `evaluate()`); noise floor; clustered paired statistics, predeclared margins, locked final sets, sample-size table; the external experiment ledger; verdict publication; benchmark maintenance. **Scope out.** Building what is tested.

**Where.** The hypotheses agent writes decisions, experiment cards and verdicts to the Drive bus (`decisions/`, `experiments/`, `verdicts/`); a person merges accepted experiment cards into the register at the fortnightly review. **Formats.** *Experiment card:* the decision it could change and why now; competing explanations and the simplest credible baseline; frozen dataset, task-family split, scorer, code and config versions; primary metric, practical margin, uncertainty method, explicit positive / negative / inconclusive outcomes and the action each triggers; budget, dependencies, authorised executor, review requirement; links to prior attempts. *Verdict:* kill / promote / narrow-and-rerun / inconclusive; effect with clustered interval; cost; deviations; belief revisions issued; valid only with references to a complete run bundle and the required review. Templates on the bus and in `queue/`.

| Wk | Deliverable |
|---|---|
| 1 | Harness freeze; statistics gate; sample-size table (e.g. 149 benign cases for a 2 % false-block bound) |
| 1–2 | Noise floor from ≥5 runs; dataset ids frozen (DreamBench-SWE subset, LongMemEval-S knowledge-update, MOOSEDev classes, seeded histories from T1, label sets from T3) |
| 2 | Register rewritten as cards; weeks 3–6 queue published |
| 3–6 | Run and host H1, H7, H2, H8 (T2), H3 (T2), H5, H10b (T3); fortnightly verdicts |
| 6 | Gate report per track: decidable or not with the samples actually collected |
| 7–12 | H4 join coverage (observational), H9 by mechanism, H6 if H3 passed; second-half queue from review #2 |

### T6 · Positioning and market (CTO-owned, part-time)

**Mission.** Keep the company's claim narrower than its ambition and truer than its competitors': *authorised, replayable evidence for agents doing engineering work, across the stores a company already has.* Decide the name. Decide what is open source.

**Deliverables.** Week 1: working name and a one-page responsibility map (what Engram is, what the ecosystem is, what we do not claim). Week 2: competitive one-pager with T0 (claimed vs shown per system). Week 6: positioning revised after review #2; open-source decision (candidate: the conformance kit and the receipt/snapshot schemas, because standards spread by being adopted). Week 12: the quarter's evidence pack for whoever needs convincing next.

## 3. Interfaces, decision rights, what is not staffed

| From → To | Artefact | Cadence |
|---|---|---|
| T0 → T5, CTO | weekly delta, proposal cards, monthly competitive one-pager | Mon; monthly |
| T1 → T2, T3, T4 | running endpoint, verbs, receipts, snapshot by position, fixtures | wk 2, continuous |
| T2, T3 → T5 | experiment requests, arms, label sets | as ready |
| T5 → all | cards, verdicts, ledger, gate reports | fortnightly; wk 6, 12 |
| T3 → T4 | shadow-ready scorer behind the port | wk 7+ |
| T4 → T3 | receipts with model-vs-rule path; borderline cases | wk 5+ |
| T4 → T1 | kit results, schema changes, registry manifest | wk 2, continuous |
| CTO → all | bets re-ranked; scope; parked list | wk 2, 6, 12 |

**Decision rights.** T5 decides verdicts; disagreement files a new card. T1 decides ledger internals, not the shared schema. T2 decides mechanism designs behind ports; T4 decides what enters a serving path. T3 decides what goes to shadow. T4 with each proving ground's owner decides contract interpretation, recorded as ADRs. CTO decides scope, staffing, parking, at the three reviews.

**Not staffed this quarter.** Chat/Slack ingestion, governance console, automatic fault attribution, broad ontology, decay tuning. Procedural-memory induction (R5, H6) is staffed only if H3 passes at week 6; until then R5 is carried by T5's H4 join-coverage measurement and T4's outcome hooks.

## 3b. Standing policy for autonomous runs (CTO to set in week 1)

Permitted datasets; token and cost budget per run and per week; concurrency; environments; which runs require an independent review before execution. Routine runs proceed inside the policy; exceptions enter the review queue. The repository register is authoritative; the bus `experiments/` folder is its inbox.

## 4. Review #1 (week 2) asks

Send the full documents. Ask: which pillar is under-served by the tracks; which hypothesis to cut from weeks 3–6; whether week-6 gates are decidable with collectable samples; what T0 is structurally blind to; whether the proving-ground order (benchmarks → open harnesses → dogfood → partner) is right.

---

## Appendix A · Proving ground D: the enterprise design partner

Kept here so it informs the tracks without framing them. Details in the [transcriptions](pdlc-grounding/jetstream-reference-transcription.md) and the [gap analysis](c6-ecosystem-gap-analysis.md).

- **What it gives us:** a written knowledge contract (one interface, declared scope, integrate-not-absorb, swap test), a demand for point-in-time reads driven by a pinned-reviewer fitness function, a testable fault-adjudication rule, three real knowledge hubs to federate, three harnesses with no working memory, and a three-month window.
- **P0 owners meeting:** gateway owner, production knowledge-service owner, adopting harness owner, identity, evaluation contact, T1 and T4 leads. Leave with: the snapshot level the contract requires; an accountable owner; two backends and one harness; where the converged MCP surface lives. Pre-reads: responsibility map, snapshot-levels note, fixture list, kit skeleton.
- **Fixtures F1–F10** (generic; the same kit runs on every proving ground): F1 capture manifest/receipt/briefing; F2 source updated after capture → served bundle unchanged; F3 access revoked → typed denial, no leak; F4 late-arriving fact → excluded with observation time; F5 curator changed → original returned, re-curation versioned; F6 backend offline → explicit unavailable, partial labelled; F7 new question at same snapshot → L2 or explicit unsupported, never live; F8 adapter swap → harness unchanged, equivalent results; F9 second tenant → nothing crosses; F10 empty result → returned as empty with reason.
- **Pass:** zero violations, owner named, level ratified. **Honest fail modes:** a hub cannot support the level; security blocks retained copies; ownership unresolved.
- **Sequence within the partner:** P0 (wk 1–2) → kit and converged surface (wk 2–4) → two hubs, receipts, L1 replay (wk 5–6) → L2 where possible, review re-resolution, outcome join (wk 7–12).
