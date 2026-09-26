# T0 Intelligence handbook — fitted to the X signals pipeline

**Date:** 2026-09-26. **Fits:** the pipeline described in [evidence/pipeline-flow.md](evidence/pipeline-flow.md) (fetch every 3 h, digest 30 min later, curation daily, hub publish manual; ~450–700 raw items/day, 5–25 insights/day; no per-item status, no queue, no weekly rollup). **Audience:** the agents that run this, and the one person who applies config.

## 0. Design decisions

1. **Do not touch the fetcher's logic.** It is deterministic and cheap. Three *request-parameter* changes are worth proposing through the normal curation route, because they remove the enrichment the evidence work had to do by hand: request `note_tweet` (full text for long posts), request `entities.urls` (expanded link targets instead of `t.co`), and request `conversation_id` (thread grouping). Same request count, more usable items.
2. **Do not overload the digest.** Its job is the daily narrative for the hub. Triage is a different job with a different output (notes and cards, not prose), so it gets its own scheduled agent.
3. **The handshake between scraping and the experiment queue is a directory under git, not a message.** Both sides are agents; git gives status, history, diff and review for free, and neither side needs the other to be online. The directory is `docs/research/queue/`. Its states are the contract (§4).
4. **Two schedulers, one directory.** A T0 *triage agent* writes into the queue; a T5 *queue agent* reads from it and writes back. Neither calls the other.
5. **Volume caps are a known floor.** Busy queries lose posts past 25 per run. Triage works on what arrived; curation proposes query splits when a query hits the cap three days running.

## 1. Jobs after this handbook

| Stage | Job | Schedule (IST) | Reads | Writes | Owner |
|---|---|---|---|---|---|
| 1 Fetch | existing | every 3 h | X API | `inbox/*.jsonl` | deterministic |
| 2 Digest | existing | +30 min | `inbox/` | reports, `insights.json`; moves to `processed/` | headless Claude |
| **2b Triage** | **new** `bin/triage_run.sh` + `bin/triage_prompt.md` | **daily 07:15** (after the 06:43 digest) and **13:15** | today's `processed/*.jsonl` (both feeds), `insights.json`, `trends.md`, `queue/watch/*.md`, `evidence/sources/` | `evidence/sources/*.md` (notes), `queue/cards/PC-*.md`, `queue/index.jsonl`, `queue/triage-log/YYYY-MM-DD.md` | headless Claude |
| 3 Curation | existing, plus one input | daily 22:17 | + `queue/triage-log/` cap counts and watch requests | `reports/curation-*.md` (now also proposes query splits and the three request params) | headless Claude |
| **2c Weekly delta** | **new** `bin/delta_run.sh` + `bin/delta_prompt.md` | **Mondays 08:15** | the week's triage logs, cards, verdicts, `insights.json`, `trends.md`, `voices-*.json` | `queue/delta/YYYY-WW.md`; refreshes the contradictions table monthly | headless Claude |
| 4 Publish | existing manual | on demand | | hub | owner |

The triage and delta jobs run in a checkout of this repository (`docs/research/`) so their outputs land in the same place the experiment queue reads. They commit to a branch and push; a human or the T5 agent merges.

## 2. Triage rubric (applied by 2b to every item, both feeds)

Runs over `processed/` items from the last 24 h. Fast path first, so most of 500 items cost nothing.

1. **Fast discard** (rule, no model): retweet-like text, no link and no number and no named system, engagement below a floor (e.g. views < 200 and likes < 3 after 3 h) unless the handle is on the watchlist. Log counts only.
2. **Cluster** by expanded link target (or `t.co` if unexpanded), quoted post, and near-duplicate text. One cluster = one candidate.
3. **Primary source reachable?** For each cluster, fetch the target: arXiv abstract page, GitHub README at HEAD (record the commit), vendor post, docs page. If none is reachable, **park** with reason. Items with only a screenshot of numbers are parked until the image is transcribed (the digest can be asked for that via a watch request).
4. **Type and strength:** paper with ablation › paper single benchmark › repo read at pinned commit › vendor benchmark › builder report with numbers › opinion. Record which.
5. **Pillar and component:** one of R1–R7 (see the programme plan) and a component from the ecosystem map. Unknown is allowed; "all" is not.
6. **Bet mapping:** supports / contradicts / would create, against the H-ids in the discovery plan. Contradictions go into the contradictions table as an open row.
7. **Note or not:** write an evidence note only for strength ≥ vendor benchmark, or for anything that contradicts a held belief. Everything else is a one-line entry in the triage log.
8. **Card or not:** write a proposal card only when the note implies an arm-vs-arm test we could run within the quarter. A note without a card is fine. A card without a note is not allowed.

Budget guard: at most 12 notes and 6 cards per run; the rest carry over with `deferred: true`.

## 3. Formats

**Evidence note.** The existing `evidence/sources/` template, unchanged: metadata (URL, type, date, commit or version, relevance), TL;DR, claims, numbers table with n and conditions, mechanism details, limitations and counter-evidence, takeaways, open questions. Verbatim quotes for anything numeric. File name `evidence/sources/<kind>-<slug>.md`.

**Proposal card** `queue/cards/PC-YYYYMMDD-NN.md`:

```yaml
---
id: PC-20260929-01
status: proposed            # proposed | accepted | merged | rejected | carded | withdrawn
created: 2026-09-29
source_note: evidence/sources/paper-xyz-2609.12345.md
source_posts: ["2103321894661595551"]
strength: paper-single-benchmark
pillar: R3
component: read-time curation
bets: {supports: [H3], contradicts: [], creates: []}
cost: S                     # S ≤ 2 person-days on the frozen harness; M ≤ 1 week; L more
urgency: none               # or one line: why now
decided_by: null            # T5 agent or person
decided_on: null
decision_reason: null
carded_as: null             # H-id or E-id once accepted
---
claim: <one falsifiable sentence>
proposed experiment: <arm A vs arm B · dataset · metric · predeclared margin · kill>
why it matters for us: <two sentences, pillar language>
```

**Queue index** `queue/index.jsonl`: one line per card, mirrored from the frontmatter, regenerated by whichever agent writes last. Fields: `id, status, pillar, component, bets, strength, cost, created, decided_on, carded_as`.

**Watch request** `queue/watch/WR-YYYYMMDD-NN.md`: `from: T2|T3|T4|T5|CTO · what: <source, system, question> · why · due: <week> · status: open|answered`. Answered by a note, a card, or a one-line "nothing found" in the triage log.

**Verdict** `queue/verdicts/<H-or-E-id>.md` (written by T5): `kill | promote | narrow-and-rerun · effect with clustered interval · cost delta · deviations from the card · one paragraph`. The triage agent reads verdicts so the weekly delta can report them.

**Weekly delta** `queue/delta/2026-W40.md`, one page: (1) beliefs changed, each with the note; (2) beliefs held under new evidence; (3) cards proposed / accepted / rejected this week with reasons; (4) verdicts landed; (5) contradictions opened or closed; (6) landscape diff: who shipped, raised, or published; (7) capture health: items, clusters, parked-for-no-source, queries at the cap; (8) open watch requests past due.

**Triage log** `queue/triage-log/YYYY-MM-DD.md`: counts per rubric step, the one-line entries for items that got no note, cap hits per query, deferred items.

## 4. The handshake: states and who moves them

```
T0 triage agent            queue/                       T5 queue agent
───────────────            ──────                       ──────────────
writes note ─────────────▶ evidence/sources/
writes card (proposed) ──▶ cards/PC-*.md ──────────────▶ reads new cards daily
                                                        decides within 14 days:
                           status: accepted   ◀──────── accepted  → converts to an experiment card in
                                                                     discovery-plan.md, sets carded_as
                           status: merged     ◀──────── merged    → points to the existing H/E it joins
                           status: rejected   ◀──────── rejected  → reason required
reads verdicts ◀────────── verdicts/<id>.md   ◀──────── writes verdict when the experiment closes
reads watch requests ◀──── watch/WR-*.md      ◀──────── any track files a watch request
answers in log/note/card ─▶
```

Rules: only T5 changes `status` past `proposed`; only T0 creates cards and notes; anyone files a watch request; every status change carries `decided_by`, `decided_on`, `decision_reason`; nothing is deleted, `withdrawn` is a state. The index is regenerated after every change so both sides can read one file.

Why not have the scraping agent decide? Because the digest already carries the narrative load, its outputs are prose, and it has no view of the harness, the register or the statistics. Why not have T5 read raw items? Because 500 items a day is T0's problem to compress. The card is the compression.

## 5. The T5 queue agent (scheduled, daily 09:15 IST)

Reads `queue/index.jsonl` for `proposed` cards; for each: check against the register for an existing H/E (merge), check cost against the current queue and the week-6 gates (accept or reject with reason), and for accepted ones write the experiment card into the register with dataset id, margin, sample-size note, dates. Writes verdicts when a run closes. Publishes a fortnightly verdict summary. This agent is one of the "team of agents"; the interactive Claude Code session reviews its decisions on the fortnightly cadence rather than making them.

## 6. Watchlist and queries to propose to curation this week

- Handles: the authors and orgs behind every source note in `evidence/sources/`; the memory-startup set (Mem0, Zep, Letta, supermemory, vectorize, MemOS); RSI authors; benchmark authors. Timelines are 4 % of volume today because only one handle is tracked; promote at least eight.
- Queries, grouped by pillar so cap hits are attributable: R1 `provenance OR "retrieval receipt" OR snapshot OR "point-in-time" memory agent`; R2 `supersede OR consolidation OR forgetting OR reconsolidation memory agent`; R3 `"context engineering" OR "just-in-time" OR "graph RAG" memory`; R4 `Jev OR "System One" OR "typed decision" OR noul` (already at the cap: split into `Jev memory` / `Jev eval` / `Jev harness`); R5 `"self-improving" OR "skill evolution" OR "procedural memory" agent`; R6 `LongMemEval OR LoCoMo OR "memory benchmark"`; R7 `"memory layer" MCP OR "knowledge gateway" OR federation agent`.
- Both feeds go through triage; the Decision Layer feed is the main source for R4.

## 7. Metrics the delta reports every week

Items fetched; clusters; primary-source rate; notes written; cards proposed, accepted, merged, rejected; median days from card to decision; verdicts landed; contradictions open; watch requests open and overdue; queries at the cap; API requests used. Targets for the first month: primary-source rate ≥ 60 % of clusters that reach step 3; ≥ 3 cards per week; median card-to-decision ≤ 7 days; zero cards older than 14 days without a decision.

## 8. Week 1 checklist

- [ ] Add `bin/triage_run.sh`, `bin/triage_prompt.md`, `bin/delta_run.sh`, `bin/delta_prompt.md`; launchd entries at 07:15, 13:15, Mon 08:15.
- [ ] Point the triage checkout at this repository; branch `queue/auto`; push after each run.
- [ ] Curation proposal: `note_tweet`, `entities.urls`, `conversation_id`; split the Jev query; promote eight handles.
- [ ] Backfill: run triage once over the last 14 days of `processed/` (expect a burst of notes; cap at 30, defer the rest).
- [ ] File the first watch requests from T2–T4 (§6 of the programme plan lists them).
- [ ] First delta the following Monday.
