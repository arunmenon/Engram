# Programme plan — workstreams, charters, interfaces, first two weeks

**Date:** 2026-09-26. **Companion to:** [operating-plan.md](operating-plan.md) (cadences and gates) and [discovery-plan.md](discovery-plan.md) (the hypothesis register). This document is the concrete layer: who does what, with which inputs and outputs, in which format, and what each team does in weeks 1 and 2. Staffing assumption: five workstreams, each with a lead; a person may lead one and sit on another. Where staffing is thinner, merge WS3 into WS2 and WS4 into WS5 and keep the gates.

```
                 ┌──────────────────────────┐
   X / arXiv /   │ WS1  Intelligence        │  weekly delta + proposal cards
   GitHub / blogs│ (scraping team)          ├──────────────────────────────┐
                 └──────────────────────────┘                              ▼
                                                            ┌──────────────────────────┐
                 ┌──────────────────────────┐  experiment   │ WS5  Hypotheses &        │
                 │ WS2  Engram core         │  requests ───▶│      Experiments         │
                 │ (brownfield: ledger,     │◀── verdicts   │ (register, harness,      │
                 │  receipts, one backend)  │               │  statistics, ledger)     │
                 └──────────┬───────────────┘               └───────────┬──────────────┘
                            │ verbs, receipts, L1 snapshot               │ verdicts
                 ┌──────────▼───────────────┐               ┌───────────▼──────────────┐
                 │ WS3  Federation &        │  scorer port  │ WS4  Decision &          │
                 │      contract            │◀─────────────▶│      curation lab        │
                 │ (greenfield: gateway,    │               │ (greenfield: typed       │
                 │  registry, P0, swap)     │               │  decisions, curation)    │
                 └──────────────────────────┘               └──────────────────────────┘
                            ▲ design partner (owners, backends, harnesses)
```

---

## WS1 · Intelligence (the scraping team)

**Mission.** Turn the X scrape into a weekly, evidence-graded picture of what is moving in agent memory, provenance, typed decisions and self-improving agents, mapped onto our ecosystem components, so that WS5 receives testable proposals rather than links.

**In scope.** Collection, triage, primary-source reading, evidence notes, contradiction tracking, the weekly delta, proposal cards. **Out of scope.** Deciding what we build. Opinions without a primary source.

### What to scrape

| Source | What | Why |
|---|---|---|
| X | Accounts and keywords in the watchlist below; **always expand** threads, quoted posts, linked articles and images; capture engagement numbers and timestamps | It is where builders post before they write papers; the two evidence bundles came from here |
| arXiv | Daily listings for cs.AI, cs.SE, cs.IR, cs.CL filtered by: agent memory, episodic/procedural memory, provenance, retrieval receipts, reproducible retrieval, memory consolidation, forgetting, typed decision / classifier-in-the-loop, self-improving agents, harness evolution, traceability, requirements-to-code | Primary sources; the pack has ~60, needs the weekly stream |
| GitHub | Releases, changelogs, closed issues tagged memory/retrieval for the landscape set: Graphiti, Hindsight, Hippo-memory, Beacon, Mem0, MemOS, Letta, MemPalace, jevmem, agentrun, MGM, lintpal | Shipped behaviour beats announced behaviour |
| Vendor posts | TypeSafe docs and cookbook, supermemory, vectorize, Zep, Datadog, Sentry engineering, Vercel changelog | Field numbers and failure reports |
| Benchmarks | LongMemEval, LoCoMo, DreamBench-SWE, MemDelta, MemFail, MemTrace, MOOSEDev, GroupMemBench: new versions, leaderboard changes, critiques | Our harness depends on them |

**Watchlist to start** (extend weekly): the authors and orgs behind the sources above; the Jev builder set from the bundles (supermemory, vectorize, Asymptote Labs, jevmem, agentrun, mika_systems, rbro112/Sentry, Deel, MotherDuck, Datadog); RSI authors (Yaowei Zheng, Sakana, the MGM group); memory-benchmark authors. Keywords: "memory layer", "context graph", "provenance", "retrieval receipt", "snapshot", "point-in-time", "supersedes", "assumptions ledger", "Jev", "System One", "typed decision", "noul", "consolidation", "forgetting", "self-improving", "harness", "skills evolution", "traceability", "C6"-style contract language.

**Do not collect:** re-posts with no new content, engagement-bait threads without a primary source, anything from the design partner's internal systems.

### Triage rubric (applied to every item before it becomes a note)

1. **Primary source reachable?** paper, repo, docs, or a builder's own post with numbers. If not: park, do not summarise.
2. **Type:** paper (ablated / unablated), repo (read at pinned commit), vendor benchmark, builder report, opinion.
3. **Strength:** as in the evidence catalogue (paper with ablation > paper single benchmark > repo read > vendor benchmark > builder report with numbers > opinion).
4. **Component mapping:** which ecosystem layer or component it touches (ledger, gateway, snapshot, receipts, admission, curation, certification, scorer, consolidation, staleness, eval harness, harness adapters, ontology).
5. **Bet mapping:** which hypothesis in the register it supports, contradicts, or would create.
6. **Contradiction check:** does it disagree with something already in the catalogue? Log it in the contradictions table either way.

### Output formats

**Evidence note** (one per source that passes triage; the existing `evidence/sources/` template): metadata, TL;DR, claims, numbers table with n and conditions, mechanism details you could implement, limitations and counter-evidence, takeaways for our stack, open questions. Verbatim quotes for anything numeric.

**Proposal card** (only when an item implies a testable change; goes to WS5):

```
id: PC-<yyyymmdd>-<n>
claim: <one sentence, falsifiable>
source: <note id>, strength: <grade>
component: <layer/component>       bets: <H-ids affected>
proposed experiment: <arm A vs arm B, metric, what would kill it>
cost to test: <S/M/L>              urgency: <why now, or none>
```

**Weekly delta** (Monday, one page, to WS5 and CTO): (1) beliefs changed, each with the note that changed it; (2) beliefs held under new evidence; (3) new proposal cards; (4) contradictions opened or closed; (5) the landscape table diff (who shipped what); (6) items parked for lack of a primary source, count only.

**Monthly:** refresh `memory-research-landscape.md` and the contradictions table in `evidence/memory-stack-synthesis.md`.

### Interfaces and SLAs

- Deliver the weekly delta by Monday 12:00. Proposal cards go straight into WS5's intake; WS5 replies accept / merge / reject within the fortnight.
- WS5 and WS2–4 may file **watch requests** (a source, a system, a question) with a due week; WS1 acknowledges in the next delta.
- Kill rule: a belief with no primary source after four weeks is demoted to opinion in the ledger.

### What WS1 needs from the CTO before Monday

- The current scraper's flow, fields, volume and where output lands, so the triage rubric and note template are fitted to it rather than bolted on.
- Who reads the raw stream and who writes notes (two roles; can be the same person).
- Access to the `evidence/` folder as the note store, or an agreed alternative.

### Weeks 1–2

- W1: install the rubric and templates on the existing flow; expand the watchlist; backfill notes for anything in the last 14 days that passes triage; first delta Monday of W2.
- W2: first proposal cards; open watch requests from WS3 (DeepInsights and Sanctum public artefacts, dejavu-style signed catalogues, any "snapshot" or point-in-time retrieval work) and WS4 (typed-decision escalation results, injection-gate evaluations, curation replay).

---

## WS2 · Engram core (brownfield)

**Mission.** Make the existing MVP the trustworthy ledger, receipt and replay substrate of the ecosystem, and one registered backend behind the C6 verbs. Not the gateway, not the read surface of record.

**In scope.** Ledger correctness and scale, tenant/scope on every record, receipts as ledger events, retained served artifacts, L1 snapshot by position, the three verbs over PCG-held data, the Atlas response extended to the agreed schema, the graph as a lineage/supersession/entity backend. **Out of scope.** Cross-backend federation (WS3), model-assisted decisions (WS4), harness adapters beyond what P0 needs.

### Deliverables

| Wk | Deliverable | Done when |
|---|---|---|
| 1 | P1 fixes: bulk-ingest payload loss, RediSearch prefix, retention double prefix; plus restart/replay, boundary-batch, payload round-trip, tenant-negative, archive-recovery tests | tests green on a fresh stack; ingest contract documented |
| 1–2 | P2: tenant/scope through entity resolution; scope schema `{caller, space/domain, classification_tier}` on every record | tenant-negative tests pass; no cross-scope leakage in a seeded test |
| 2 | Receipt event types: `retrieval.receipt`, `decision.receipt`, `snapshot.manifest`; retained served artifact by hash | every `/context` call emits a receipt; replay CLI returns the served bundle byte-identical |
| 2–3 | `retrieve/write/snapshot` over PCG data; `write(kind=episode)` = append; `write(kind=fact)` = proposal state; `snapshot(scope, as_of)` = L2 by stream position for PCG-held data | conformance kit (WS3) passes against PCG alone |
| 3–4 | Response schema aligned with the agreed `evidence[]` + `validity` shape; bitemporal fields (valid time, observation time) | schema validated in the kit; Atlas kept as internal shape |
| 4–6 | Graph re-scoped: lineage, supersession, entity queries as a backend; SUPERSEDES with two-signal rule and `superseded` state; SIMILAR_TO/CAUSED_BY creation per the Jev-Mem recipe behind a flag | H7 arms runnable; H2 arm runnable |
| ongoing | Fixtures and datasets for WS5 (seeded histories with supersession, contradictions, unavailable sources, second tenant) | WS5 accepts them into the frozen harness |

**Kill/keep rules.** Keep the positioned ledger, provenance block, ports, tenancy, crypto-shred. Stop investing in decay tiers and consolidation summaries until H9 says otherwise. Do not build a second gateway.

### Weeks 1–2, concretely

- Day 1–2: reproduce the three confirmed defects with failing tests; fix; add the test list above.
- Day 3–5: scope schema; tenant through entity resolution; negative tests.
- Week 2: receipts and retained artifacts; replay CLI; first pass of the three verbs; hand WS3 a running PCG endpoint and WS5 the first seeded fixture set.

---

## WS3 · Federation and contract (greenfield, with the design partner)

**Mission.** Prove C6 is feasible and owned by running one real Spec-to-PR-review flow over two real backends, then grow the federation gateway from those fixtures: registry, scope resolver, fusion, normalisation, snapshot composition, receipts, swap test, one converged MCP surface.

**In scope.** P0, conformance kit, registry and manifests, scope resolver and live authorisation, RRF fusion baseline, snapshot levels and manifest, MCP projection converged with the existing PAI surface, Courier link-resolution adapter, Endzone/DeepInsights as registered backends. **Out of scope.** Model-assisted routing or rerank until WS4 hands over a shadow-ready scorer; ontology beyond the four response dimensions.

### P0 specification (week 1–2)

*Participants:* gateway owner, production knowledge-service owner, adopting harness owner, identity, C9 contact, WS2 lead, WS3 lead.
*Pre-meeting artefacts (WS3 prepares):* one-page responsibility map with working name; the three snapshot levels written out with what each backend can support; the fixture list below; the conformance kit skeleton.
*Decisions to leave the room with:* which snapshot level C6 requires; who owns C6 for the pilot; which two backends and which harness; where the converged MCP surface lives.

*Fixtures (each is a test with a pass condition):*

| # | Fixture | Pass |
|---|---|---|
| F1 | Retrieve for a Spec; capture manifest, receipt, served briefing | all three present, hashes match |
| F2 | Update a source item after capture; replay at review | served bundle returned unchanged; current content never substituted |
| F3 | Revoke reviewer's access to one served item; replay | typed denied result for that item; no leak in diagnostics |
| F4 | Late-arriving fact with valid time before `as_of`; replay | excluded, with observation time recorded |
| F5 | Change the curating model; replay | original briefing returned; re-curation is a new version, diffed |
| F6 | Take one backend offline; retrieve and replay | explicit unavailable; partial result labelled; receipt records it |
| F7 | New question against the same snapshot | answered from frozen corpus (L2) or explicitly unsupported for that backend; never from live |
| F8 | Swap backend adapters | harness code unchanged; content, provenance, abstention, scope, failure semantics, cost equivalent |
| F9 | Second tenant / other space | nothing crosses |
| F10 | Empty result | admission returns empty with reason; no forced item |

*Pass:* zero violations, an accountable owner, a ratified snapshot level. *Fail modes to report honestly:* a backend cannot support the ratified level; security blocks retained copies; ownership unresolved.

### Deliverables after P0

| Wk | Deliverable |
|---|---|
| 2–3 | Conformance kit v0 from F1–F10; registry manifest format; scope resolver (deterministic) |
| 3–4 | Two backends registered (PCG, DeepInsights); RRF k=60 fusion baseline; normaliser to the agreed schema; MCP projection converged with the existing surface; Courier link-resolution adapter storing a snapshot id in the Spec |
| 5–6 | Receipts durable in the partner flow; L1 replay live; second harness; swap test green in CI; snapshot manifest signed; capability negotiation per backend |
| 7–12 | L2 where backends allow; PR-review re-resolution; certification path hand-off to WS2; C9 signals joined to receipts |

### Weeks 1–2, concretely

- Day 1: responsibility map, working name, snapshot-levels note, fixture list to participants.
- Day 2–3: owners meeting; decisions recorded as ADRs.
- Day 4–10: run F1–F10 against PCG plus the second backend with whatever adapters exist, even crude ones; log every violation; kit skeleton grows from the fixtures.

---

## WS4 · Decision and curation lab (greenfield research MVPs)

**Mission.** Find out, with labelled data and shadow runs, which judgment points earn a typed decision model and which stay rules; and whether read-time curation can be both useful and replayable.

**In scope.** The scorer port and rule baselines; label collection; H3, H5, H10; the two-tier escalation question; supersession and write-admission batteries; staleness via source-change invalidation before any model sweep. **Out of scope.** Anything in the serving path without a shadow result; fault adjudication automation (proposal-only, with review).

### Deliverables

| Wk | Deliverable | Done when |
|---|---|---|
| 1 | Scorer port spec: typed input, label + abstain + diagnostics + model/version/timing; rule baseline per decision; latency classes | port compiles against a rule-only adapter |
| 1–2 | Label sets: write admission (≥90: obvious/ambiguous/no-fit, split by project and time), supersession pairs, injection benign set (≥149 independent) | frozen, held out from tuning |
| 2–4 | H5: rules vs NLI/reranker vs typed model on admission, in shadow, fit on half, test on the other; escalation evaluated on the borderline population | verdict with clustered intervals and error cost |
| 3–4 | H3: extractive bundle vs cached summary vs task-conditioned briefing, with the served artifact retained and replay checked | verdict on task success, omission rate, tokens, replayability |
| 5–6 | H10a source-change invalidation vs periodic sweep; H10b injection gate false-block bound | verdicts; gate ships only if the one-sided bound clears 2 % |
| 7–12 | One scorer in production shadow behind WS3's port (likely admission or listwise rerank); G6 confidence components; supersession battery | receipts show model vs rule path per call |

**Rules.** No threshold copied from another system. Every battery ships with a shadow phase and a per-route confusion matrix. Cheap battery first; escalation only if the borderline-population test says so.

### Weeks 1–2, concretely

- Day 1–3: port spec and rule baselines; agree the label schema with WS5.
- Day 4–10: collect and freeze the three label sets from the partner's real material where permitted, otherwise from seeded fixtures; build H3's three arms on WS5's harness.

---

## WS5 · Hypotheses and experiments

**Mission.** Own the register, the frozen harness, the statistics and the experiment ledger; run the queue; issue verdicts nobody can argue with.

**In scope.** The discovery plan as the single register; intake of proposal cards and experiment requests; dataset curation and held-out splits; the frozen `evaluate()`; noise floor; clustered paired statistics; the external experiment ledger; verdict publication; benchmark maintenance. **Out of scope.** Building the components under test.

### Intake and cards

**Experiment request** (from WS2–4) and **proposal card** (from WS1) both land in intake. WS5 converts accepted ones into an **experiment card**:

```
id: H<n> or E-<yyyymmdd>-<n>      owner: <WS>      track: A/B/C
claim · arms · dataset (frozen id) · metric · predeclared margin · sample size and power note
kill criterion · what a pass unlocks · cost (runs, tokens, people-days) · start/verdict dates
```

**Verdict** (published to the ledger and the weekly delta): kill / promote / narrow-and-rerun; effect with clustered interval; cost delta; deviations from the card; one paragraph of interpretation, no more.

### Deliverables

| Wk | Deliverable |
|---|---|
| 1 | Harness freeze: real embeddings, query text embedded (not gold), intent from the classifier, scoring imported from the domain module, held-out split by project/time, frozen `evaluate()`; statistics gate documented (clustered paired intervals, predeclared margins, locked final set, sample-size table) |
| 1–2 | Noise floor from ≥5 baseline runs; datasets: DreamBench-SWE subset, LongMemEval-S knowledge-update subset, seeded PDLC history from WS2, label sets from WS4 |
| 2 | Register rewritten as experiment cards; queue for weeks 3–6 published with owners and dates |
| 3–6 | Run H1, H7, H2, H8 (track B) and host H3, H5, H10 (track C); fortnightly verdicts; ledger current |
| 6 | Week-6 gate report per track: decidable or not, with the sample sizes actually collected |
| 7–12 | H4 join-coverage measurement (observational), H9 by mechanism, H6 if unlocked; second-half queue from review #2 |

### Weeks 1–2, concretely

- Day 1–3: harness freeze and statistics gate; publish the sample-size table (e.g. 149 benign cases for a 2 % false-block bound; paired n for a +10/180 margin at the measured noise floor).
- Day 4–7: noise floor; dataset ids frozen; intake open.
- Week 2: cards for H1, H7, H2, H8, H3, H5, H10 with dates; first fortnightly verdict meeting scheduled.

---

## Interfaces at a glance

| From → To | Artefact | Cadence |
|---|---|---|
| WS1 → WS5, CTO | weekly delta, proposal cards | Mon |
| WS2/3/4 → WS5 | experiment requests, fixtures, datasets, label sets | as ready |
| WS5 → all | experiment cards, verdicts, ledger | fortnightly |
| WS2 → WS3 | running PCG endpoint, verbs, receipts, L1/L2 snapshot | wk 2, then continuous |
| WS3 → WS2 | conformance kit results, schema changes, registry manifest | wk 2, then continuous |
| WS4 → WS3 | shadow-ready scorer behind the port | wk 7+ |
| WS3 → WS4 | receipts with model-vs-rule path, borderline cases for labelling | wk 5+ |
| CTO → all | bets re-ranked after each review; scope decisions | wk 2, 6, 12 |

## Decision rights

- WS5 decides verdicts. Nobody overrides a verdict; they file a new card.
- WS3 decides contract interpretation *with the partner's owner*; records it as an ADR.
- WS2 decides ledger internals; cannot change the agreed response schema alone.
- WS4 decides which decision goes to shadow; WS3 decides when it enters the serving path.
- CTO decides scope, staffing, and what is parked, at the three reviews.

## What is deliberately not staffed this quarter

Chat/Slack ingestion, governance console, automatic fault attribution, broad ontology, procedural-memory induction, decay tuning. Each has a named unlock in the register; none has a team until then.
