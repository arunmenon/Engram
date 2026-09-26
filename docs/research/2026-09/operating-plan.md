# Operating plan — memory ecosystem, Q4 2026

**Date:** 2026-09-26. **Owner:** CTO. **Horizon:** 12 weeks, reviewed at week 2, 6, 12. **Premise:** Engram is one cog (ledger, receipts, one backend). The product is authorised, replayable evidence for agents doing engineering work, across the stores a company already has. Track A below is the enterprise proving ground, one of four (benchmarks, open harnesses, dogfood, partner); see [programme-plan.md](programme-plan.md). Documents now earn their place only by changing a bet; the ratio flips to experiments first.

## 1. Four loops

| Loop | Cadence | Input | Output | Kill / promote rule |
|---|---|---|---|---|
| **Intelligence** | weekly, Mon | X scrape + arXiv (cs.AI/cs.SE, memory·provenance·agents) + GitHub releases of the 10 landscape systems + vendor changelogs | one-page delta: beliefs changed / held / to test, each mapped to an ecosystem component; catalogue-grade (primary read, strength, contradictions) | a belief with no primary source after 4 weeks is demoted to opinion |
| **Research** | fortnightly | [discovery plan](discovery-plan.md) register, [belief register](beliefs.md) | per hypothesis: kill / promote / narrow-and-rerun / inconclusive; belief revision events; experiment ledger entry | no verdict without a run bundle and, where required, an independent review; one attributable change per round |
| **MVP** | monthly | promoted hypotheses | one swappable component behind a port, raced against the incumbent on the frozen harness | keep only if it beats the incumbent at matched budget on the held-out split |
| **Course-correct** | weeks 2, 6, 12 | full documents (gap analysis, reconciliation, plan), not summaries | positioning revised; bets re-ranked; one claim dropped; one thing added | external reviewer rotates; every finding gets conceded/held with a reason |

## 2. Experiment queue, fast-tracked

Three parallel tracks instead of one serial sequence. Each track has one owner and a frozen harness. Nothing waits on a document.

| Track | Wk 1–2 | Wk 3–4 | Wk 5–6 | Gate at wk 6 |
|---|---|---|---|---|
| **A · Contract** (design partner) | **P0**: owners in one room; snapshot level ratified; Spec→PR-review replay over 2 real backends with mutation, revocation, curator change, outage, swap | conformance kit from P0 fixtures; PCG behind 3 verbs; MCP surface converged with the existing PAI gateway | second harness; receipts durable; L1 replay in the partner's flow | zero contract violations, an accountable owner named, or stop and rescope |
| **B · Retrieval** (harness) | P1–P3 repairs + statistics gate (clustered intervals, margins, locked final set) | **H1** raw ledger vs none vs hybrid, absolute-margin kill; **H7** typed supersession vs SQL vs top-k | **H2** graph vs hybrid at matched units and tokens; **H8** stop rule, non-inferiority | keep or demote the graph as a read surface; decide typed-query story |
| **C · Decisions & curation** | scorer port + rule baseline; labelled sets split by project/time | **H3** curation with retained artifact vs cached summary vs extractive; **H5** one scorer (write admission) in shadow | **H10a** source-change invalidation vs staleness sweep; **H10b** injection gate with ≥149 benign cases | one scorer earns production shadow, or none does |

Weeks 7–12: H4 observational only (receipt→outcome join coverage), H9 by mechanism, H6 only if H3 passed; certification path and supersession MVP; second external review at week 6 sets the week 7–12 queue. Parked until a pass unlocks them: chat ingestion, governance console, automatic fault attribution, broad ontology, procedural induction.

## 3. Calendar, first six weeks

| Week | A | B | C | Cross-cutting |
|---|---|---|---|---|
| 1 | owners meeting; fixture list; snapshot level ratified | harness freeze; stats gate; P1 fixes | scorer port spec; label collection starts | working name + responsibility map; intelligence delta #1 |
| 2 | P0 run #1; violations logged | P2–P3 done; noise floor measured | rule baselines for admission/route | **review #1** (gap analysis + reconciliation + this plan, full docs) |
| 3 | conformance kit v0; PCG behind verbs | H1 + H7 running | H3 arms built; labelled set frozen | ledger entries for every run |
| 4 | MCP convergence; Courier link demo | H1/H7 verdicts | H5 shadow starts | fortnightly research verdicts |
| 5 | second harness; receipts durable | H2 + H8 running | H10a/b running | MVP decision: which component ships behind a port |
| 6 | L1 replay live in partner flow | H2/H8 verdicts | H5/H10 verdicts | **review #2**; re-rank bets; set weeks 7–12 |

## 4. Rules that do not move

- Frozen judge, held-out split, external experiment ledger, one change per round, memory charged for its tokens.
- Deterministic first: scope, budgets, certified-write permission, expiry, exact-version checks, empty admission. Models shadow, never override.
- No claim of novelty or superiority without a primary source or our own paired measurement.
- Design-partner work is engineering for the partner. The ecosystem map and the research register are the company.

## 5. Review requested (week 2)

Send to the reviewer with the full documents. Ask for: (a) which track is under-resourced for its gate; (b) which hypothesis should be cut from weeks 3–6 to protect P0; (c) whether the week-6 gates are decidable with the sample sizes we can actually collect; (d) what the intelligence loop is structurally blind to.
