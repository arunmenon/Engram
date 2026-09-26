# Brief for the signals agents: what we are building and what we need from you

*Drop-in context for the fetch/digest/curation pipeline and the two agents that will join it (triage, hypotheses). Written 2026-09-26. Read this before the prompts; the prompts tell you how, this tells you why.*

## 1. What we are building

We are building a **memory ecosystem for AI agents that do engineering work**: coding agents, review agents, incident agents. Not a chat-memory product. The core question is how an agent can carry evidence, decisions and lessons across tasks and sessions in a way that is **auditable** (every served memory can be traced to its source and replayed), **safe to update** (memories change through gated proposals, never silent edits), and **useful at build time** (a reviewer can reproduce exactly what a spec was written against).

We have an MVP called Engram: an immutable, positioned event ledger with provenance on every record, a derived graph for lineage and supersession questions, and a retrieval API. It is one component. Around it we are building, or deciding whether to build: a federation layer over a company's existing knowledge stores; a receipt and replay discipline; gated write and supersession mechanics; read-time curation; a small typed-decision layer; an outcome loop; and an evaluation harness that produces numbers we trust.

We are a research-driven company. **We do not ship a mechanism because a paper or a vendor says it works.** We test it on a frozen harness against a baseline with a predeclared kill criterion. Your job is to feed that machine with things worth testing, and to keep our beliefs honest.

## 2. The seven pillars (use these as your labels)

| Id | Pillar | What we believe today | What would change our mind |
|---|---|---|---|
| R1 | Evidence substrate | Raw, positioned, provenance-carrying events are the bank; receipts and replay make memory auditable | a system that gets reproducible retrieval without retaining served artifacts; evidence that provenance does not reduce downstream errors |
| R2 | Update mechanics | Writes are proposals judged independently; supersede, never delete; scheduled consolidation and forgetting are unproven | a measured on/off result for consolidation or forgetting at matched budget, either direction |
| R3 | Read strategy | Task-conditioned read-time curation beats write-time distillation; the graph is an index for lineage/supersession, not the default read surface; stop rules over fixed k | graph lift over hybrid retrieval at matched tokens; curation failing on long structured artifacts |
| R4 | Judgment layer | Small typed decision models (yes/no, choice, score) belong at closed-menu decisions, rules first, never generation, never alone in an open loop; calibration is claimed, not shown | calibration data; a decision model beating rules on error cost in a build-time setting; escalation tiers that help on the borderline population |
| R5 | Outcome and procedural memory | Learning from outcomes needs receipts joined to results; raw trajectories often beat distilled skills; feedback-loop rate is unmeasured anywhere | any system reporting the rate at which wrong memories get reinforced; delayed-outcome attribution that works |
| R6 | Evaluation science | Nothing counts without a frozen judge, held-out split, clustered paired statistics and a cost charge; most published memory numbers do not survive a primary read | benchmarks that measure reproducibility, abstention, contradiction handling, or cost |
| R7 | Interop and federation | Memory lives among other stores: one scoped interface, registry of backends, declared point-in-time levels, swap-testable | anyone shipping point-in-time snapshots over heterogeneous stores; memory interface standards gaining adoption |

Two topics you were already covering fit inside these: **Jev / System One** is R4 (and touches R3 and R6 when used as a reranker or judge); **RSI** is R5 plus the oversight questions in R6.

## 3. What counts as evidence, and what does not

**Counts, in descending strength:** a paper with an ablation; a paper with one benchmark; a repository read at a pinned commit; a vendor benchmark with stated conditions; a builder report with numbers; an opinion from someone who has shipped the thing.

**Does not count:** a repost; a thread with no primary source; a claim whose only support is a screenshot you cannot read; "we found" with no n, no baseline, no conditions; announcements of intent.

**Always capture with numbers:** n, baseline, conditions, cost, latency, and whether the judge and the system share a model. Quote numbers verbatim. If the text and a table disagree, say so.

**Contradictions are the most valuable thing you can find.** When a new item disagrees with something already in `evidence/memory-stack-synthesis.md` or a held belief in the table above, that goes at the top of your output, not in a footnote.

## 4. What to look for, by pillar

- **R1:** retrieval receipts, replay, "snapshot", "point-in-time", provenance chains, signed catalogues, event-sourced memory, immutable logs for agents.
- **R2:** supersession, contradiction handling, write gates, certification workflows, consolidation and "dreaming", forgetting and decay, reconsolidation on read, any on/off measurement.
- **R3:** just-in-time or task-conditioned context, context engineering, graph RAG results with matched budgets, stop rules, sufficiency controllers, summaries as cache vs read surface.
- **R4:** Jev and System One, typed decisions, classifier-in-the-loop, calibration reports, escalation tiers, listwise vs pointwise reranking, decision models failing.
- **R5:** self-improving agents, skill and workflow induction, procedural memory, outcome-linked reinforcement, negative evidence, RSI taxonomies and oversight.
- **R6:** new or revised memory benchmarks, critiques of benchmarks, leakage findings, reproducibility, cost-aware evaluation, judge design.
- **R7:** memory interfaces and MCP memory servers, knowledge gateways, federation over multiple stores, interoperability contracts, what Mem0 / Zep / Letta / supermemory / vectorize / MemOS / Graphiti / Hindsight ship and claim.

Also watch the **landscape**: launches, funding, pricing and positioning changes among memory vendors and coding-agent harnesses (Claude Code, Codex, Cursor, OpenHands, Aider). We need to know who claims what and who shows what.

## 5. How to present findings

Three outputs, in this order of priority. Formats are in `2026-09/t0-intelligence-handbook.md` §3.

1. **Evidence note** for anything at vendor-benchmark strength or above, or anything that contradicts a held belief. Same template as `evidence/sources/`.
2. **Proposal card** only when a note implies an arm-versus-arm test we could run this quarter: claim, arms, dataset, metric, margin, kill criterion, cost. A card without a note is not allowed.
3. **Weekly delta** on Mondays: beliefs changed, beliefs held, cards, verdicts, contradictions, landscape diff, capture health.

Keep the daily digest and hub as they are. The digest is the narrative; notes and cards are the evidence.

## 6. How this reaches the experiment queue

The bus is a shared Google Drive folder, `research-bus` (folder ids in `docs/research/queue/README.md`). You upload with the same helper that publishes the hub data, conversion disabled, and you list folders by parent id.

- You write **notes** to `notes/`, **cards** to `cards/` (once, never edited), **triage logs** to `triage-log/`, and the Monday **delta** to `delta/`.
- The hypotheses agent, on the same machine on its own schedule, reads `cards/` and answers each with a file in `decisions/` (`accepted`, `merged`, `rejected`, with a reason) within fourteen days; accepted cards get an experiment card in `experiments/`; when an experiment closes, a verdict lands in `verdicts/`.
- You read `verdicts/` and `decisions/` so the weekly delta can report them. Anyone can drop a request in `watch/`; you answer with `WR-….answer.md` pointing to a note, a card, or "nothing found".
- Nothing is edited or deleted after upload. Status is the newest decision file. `index.json` at the root is a convenience the last writer regenerates.
- The delta job mirrors the whole folder into the repository's `docs/research/queue/` every Monday, so history and review live in git.

You do not decide what gets tested; you decide what is worth a card. The hypotheses agent does not read raw items; it reads cards.

## 7. Things we already know, so you do not re-report them

The evidence catalogue in `evidence/` holds 38 items and 30 source notes as of 26 September, including Jev-Mem, REALM, EvoSkill, RRSI, Beacon, Hindsight, Hippo, jevmem, agentrun, the supermemory and vectorize articles, and the RSI taxonomy. Read the synthesis and the contradictions table before your first run. New posts about those sources are only worth a note if they add numbers, a contradiction, or a shipped change.

## 8. What we will measure about you

Primary-source rate of the clusters you triage; cards per week and how many get accepted; median days from card to decision; contradictions surfaced; queries that hit the fetch cap. First-month targets are in the handbook §7. The point is not volume. Three cards a week that survive are worth more than thirty that do not.
