# T0 Intelligence handbook — fitted to the X signals pipeline

**Date:** 2026-09-26. **Fits:** the pipeline described in [evidence/pipeline-flow.md](evidence/pipeline-flow.md) (fetch every 3 h, digest 30 min later, curation daily, hub publish manual; ~450–700 raw items/day, 5–25 insights/day; no per-item status, no queue, no weekly rollup). **Audience:** the agents that run this, and the one person who applies config.

## 0. Design decisions

1. **Do not touch the fetcher's logic.** It is deterministic and cheap. Three *request-parameter* changes are worth proposing through the normal curation route, because they remove the enrichment the evidence work had to do by hand: request `note_tweet` (full text for long posts), request `entities.urls` (expanded link targets instead of `t.co`), and request `conversation_id` (thread grouping). Same request count, more usable items.
2. **Do not overload the digest.** Its job is the daily narrative for the hub. Triage is a different job with a different output (notes and cards, not prose), so it gets its own scheduled agent.
3. **The handshake between scraping and the experiment queue is a shared Google Drive folder, `research-bus`, not a message and not a git branch.** The Mac already uploads to Drive on every fetch; cloud sessions can read and write it; neither side needs the other online. Layout, folder ids and rules are in [`../queue/README.md`](../queue/README.md). The repository directory `docs/research/queue/` is a weekly mirror for history and review.
4. **Two schedulers, one folder, append-only.** A T0 *triage agent* writes cards and notes; a T5 *hypotheses agent* writes decisions, experiment cards and verdicts. Nobody edits another agent's file; status changes are new files. Neither calls the other.
5. **Volume caps are a known floor.** Busy queries lose posts past 25 per run. Triage works on what arrived; curation proposes query splits when a query hits the cap three days running.

## 1. Jobs after this handbook

| Stage | Job | Schedule (IST) | Reads | Writes | Owner |
|---|---|---|---|---|---|
| 1 Fetch | existing | every 3 h | X API | `inbox/*.jsonl` | deterministic |
| 2 Digest | existing | +30 min | `inbox/` | reports, `insights.json`; moves to `processed/` | headless Claude |
| **2b Triage** | **new** `bin/triage_run.sh` + `bin/triage_prompt.md` | **daily 07:15** (after the 06:43 digest) and **13:15** | today's `processed/*.jsonl` (both feeds), `insights.json`, `trends.md`; Drive `watch/`, `verdicts/`, `notes/` | Drive `notes/`, `cards/`, `triage-log/`, `index.json` | headless Claude |
| 3 Curation | existing, plus one input | daily 22:17 | + Drive `triage-log/` cap counts and `watch/` requests | `reports/curation-*.md` (now also proposes query splits and the three request params) | headless Claude |
| **2c Weekly delta** | **new** `bin/delta_run.sh` + `bin/delta_prompt.md` | **Mondays 08:15** | Drive `triage-log/`, `cards/`, `decisions/`, `verdicts/`; `insights.json`, `trends.md`, `voices-*.json` | Drive `delta/YYYY-WW.md`; mirrors the whole bus into the repo's `docs/research/queue/` and commits; refreshes the contradictions table monthly | headless Claude |
| **2d Hypotheses** | **new** `bin/hypotheses_run.sh` + `bin/hypotheses_prompt.md` | **daily 09:15** | Drive `cards/`, `decisions/`, `experiments/`; the register `2026-09/discovery-plan.md` (read-only checkout) | Drive `decisions/`, `experiments/`, `verdicts/`, `index.json` | headless Claude |
| 4 Publish | existing manual | on demand | | hub | owner |

All new jobs write to Drive with the same helper the fetcher uses for hub data, with conversion disabled. Only the delta job touches the repository, and only to mirror Drive into `docs/research/queue/` and commit. Experiment cards accepted by the hypotheses agent are merged into `discovery-plan.md` by a person at the fortnightly review, not by the agent.

## 1b. The bus: where each agent writes

Google Drive, owner's My Drive, folder `research-bus` (https://drive.google.com/drive/folders/1d3sOz2YROJTNtzLhyDFDUS-fH1KBmqim). The folder holds its own `README.md`, five templates and `index.json`; the repository mirror is `docs/research/queue/`.

| Folder | Id | Written by | Files |
|---|---|---|---|
| `cards/` | `1wCmR3VBI0GJThB7T9XtFdCkSg4VFkkjj` | triage | `PC-YYYYMMDD-NN.md`, once |
| `notes/` | `1xZZ6Jr878OtaCMohKvRi1VQX_m3gGcPL` | triage | `<kind>-<slug>.md`, once |
| `triage-log/` | `1IegV687s0fjdS8f3_SDI1GPfYat0HHrc` | triage | `YYYY-MM-DD.md` (second run of the day appends a new file `YYYY-MM-DD-2.md`) |
| `delta/` | `1m0zNCGTapSFEd9alpujJXXyX-BFuAqed` | delta | `YYYY-WW.md` |
| `decisions/` | `1Puptg6-Hj13TL6t2-zjBYll4BIq81Lt-` | hypotheses | `PC-YYYYMMDD-NN.<status>.json`, one per status change |
| `experiments/` | `1jtLlsldQNNYl3BDJ3ezq-q24T2b3lXao` | hypotheses | `<E-or-H-id>.md` |
| `verdicts/` | `1FZCKIEDjHGiEz0Ba8IToTrrNIDPkBNvJ` | hypotheses | `<E-or-H-id>.md` |
| `watch/` | `1Gnm5VMrQNxa9S2By0P5GzoUxr1gvIjVM` | anyone; triage answers | `WR-YYYYMMDD-NN.md`, `WR-YYYYMMDD-NN.answer.md` |
| root | `1d3sOz2YROJTNtzLhyDFDUS-fH1KBmqim` | last writer | `index.json` |

**Upload rules.** Plain `text/markdown` or `application/json`, conversion to Google Docs disabled, parent folder by id. List a folder by `parentId`, never by title search (the search index lags uploads by minutes). Never overwrite: a correction is a new file. If the existing hub uploader only handles its two JSON files, add `bin/bus_upload.py` around the same credentials with `upload(path, parent_id, mime)` and `list(parent_id)`.

**Register access for the hypotheses agent.** Default: a read-only clone of the Engram repository on the same Mac, refreshed by the runner before each run, reading `docs/research/2026-09/discovery-plan.md`. Alternative if git is unwanted on that machine: the Monday delta job uploads `discovery-plan.md` to the bus root and the agent reads it from there.

**Mirror.** The delta job downloads the whole bus into `docs/research/queue/` in the clone and commits on a branch the owner merges. That is the only write any of these agents makes to the repository.

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

**Proposal card** Drive `cards/PC-YYYYMMDD-NN.md` (written once; status lives in `decisions/`, so the frontmatter below has no mutable fields):

```yaml
---
id: PC-20260929-01
created: 2026-09-29
source_note: evidence/sources/paper-xyz-2609.12345.md
source_posts: ["2103321894661595551"]
strength: paper-single-benchmark
pillar: R3
component: read-time curation
bets: {supports: [H3], contradicts: [], creates: []}
cost: S                     # S ≤ 2 person-days on the frozen harness; M ≤ 1 week; L more
urgency: none               # or one line: why now
---
claim: <one falsifiable sentence>
proposed experiment: <arm A vs arm B · dataset · metric · predeclared margin · kill>
why it matters for us: <two sentences, pillar language>
```

**Decision** Drive `decisions/PC-YYYYMMDD-NN.<status>.json`, one file per status change, written only by the hypotheses agent: `{id, status, decided_by, decided_on, reason, carded_as?, merged_into?}`. The newest file for an id is the status; none means `proposed`.

**Experiment card** Drive `experiments/<E-or-H-id>.md`, written by the hypotheses agent for accepted proposals (template in `queue/experiments/TEMPLATE.md`); a person merges it into the register at the fortnightly review.

**Index** Drive `index.json` at the bus root: `[{id, status, pillar, component, bets, strength, cost, created, decided_on, carded_as}]`, regenerated from `cards/` + `decisions/` by whichever agent ran last. Convenience, never source of truth.

**Watch request** Drive `watch/WR-YYYYMMDD-NN.md`: `from: T2|T3|T4|T5|CTO · what · why · due: <week>`. Answered by a new file `watch/WR-YYYYMMDD-NN.answer.md` pointing at a note, a card, or saying "nothing found <date>".

**Verdict** Drive `verdicts/<H-or-E-id>.md` (written by the hypotheses agent; template in `queue/verdicts/TEMPLATE.md`): `kill | promote | narrow-and-rerun · effect with clustered interval · cost delta · deviations from the card · one paragraph`. The triage agent reads verdicts so the weekly delta can report them.

**Weekly delta** Drive `delta/2026-W40.md`, one page: (1) beliefs changed, each with the note; (2) beliefs held under new evidence; (3) cards proposed / accepted / rejected this week with reasons; (4) verdicts landed; (5) contradictions opened or closed; (6) landscape diff: who shipped, raised, or published; (7) capture health: items, clusters, parked-for-no-source, queries at the cap; (8) open watch requests past due.

**Triage log** Drive `triage-log/YYYY-MM-DD.md`: counts per rubric step, the one-line entries for items that got no note, cap hits per query, deferred items.

## 4. The handshake: files and who writes them

```
T0 triage agent                 Drive: research-bus/                 T5 hypotheses agent
───────────────                 ────────────────────                 ───────────────────
writes note ──────────────────▶ notes/<kind>-<slug>.md
writes card (once) ───────────▶ cards/PC-*.md ─────────────────────▶ reads cards with no decision file
                                                                     decides within 14 days, writes
                                decisions/PC-*.accepted.json ◀────── accepted  (+ experiments/<E>.md)
                                decisions/PC-*.merged.json   ◀────── merged    (merged_into: H-id)
                                decisions/PC-*.rejected.json ◀────── rejected  (reason required)
reads verdicts ◀─────────────── verdicts/<id>.md             ◀────── writes when an experiment closes
reads watch requests ◀───────── watch/WR-*.md                ◀────── any track or the CTO files one
answers ──────────────────────▶ watch/WR-*.answer.md
regenerates ──────────────────▶ index.json                   ◀────── regenerates
Monday: mirrors the tree ─────▶ repo docs/research/queue/ (git = archive)
```

Rules: only the hypotheses agent writes to `decisions/`, `experiments/`, `verdicts/`; only the triage agent writes to `cards/`, `notes/`, `triage-log/`; anyone writes to `watch/`; nothing is edited or deleted after upload; `withdrawn` is a decision file like any other; the register in the repository is changed only by a person at the fortnightly review, from `experiments/`.

Why not have the digest decide? It carries the narrative load, its outputs are prose, and it has no view of the harness, the register or the statistics. Why not have the hypotheses agent read raw items? Because 500 items a day is T0's problem to compress. The card is the compression.

## 5. The T5 hypotheses agent (scheduled, daily 09:15 IST, same machine)

Lists Drive `cards/` by parent id and `decisions/` by parent id; a card with no decision file is `proposed`. For each: check the register (read-only checkout of `2026-09/discovery-plan.md`) for an existing H or E (merge); check cost against the current queue and the week-6 gates (accept or reject, reason required); for accepted ones write `experiments/<E-id>.md` with dataset id, predeclared margin, sample-size note and dates, and a decision file with `carded_as`. Writes `verdicts/<id>.md` when a run closes. Regenerates `index.json`. It never edits the repository; a person merges `experiments/` into the register at the fortnightly review. This agent is one of the team of agents; the interactive Claude Code session reviews its decisions fortnightly rather than making them daily.

## 6. Watchlist and queries to propose to curation this week

- Handles: the authors and orgs behind every source note in `evidence/sources/`; the memory-startup set (Mem0, Zep, Letta, supermemory, vectorize, MemOS); RSI authors; benchmark authors. Timelines are 4 % of volume today because only one handle is tracked; promote at least eight.
- Queries, grouped by pillar so cap hits are attributable: R1 `provenance OR "retrieval receipt" OR snapshot OR "point-in-time" memory agent`; R2 `supersede OR consolidation OR forgetting OR reconsolidation memory agent`; R3 `"context engineering" OR "just-in-time" OR "graph RAG" memory`; R4 `Jev OR "System One" OR "typed decision" OR noul` (already at the cap: split into `Jev memory` / `Jev eval` / `Jev harness`); R5 `"self-improving" OR "skill evolution" OR "procedural memory" agent`; R6 `LongMemEval OR LoCoMo OR "memory benchmark"`; R7 `"memory layer" MCP OR "knowledge gateway" OR federation agent`.
- Both feeds go through triage; the Decision Layer feed is the main source for R4.

## 7. Metrics the delta reports every week

Items fetched; clusters; primary-source rate; notes written; cards proposed, accepted, merged, rejected; median days from card to decision; verdicts landed; contradictions open; watch requests open and overdue; queries at the cap; API requests used. Targets for the first month: primary-source rate ≥ 60 % of clusters that reach step 3; ≥ 3 cards per week; median card-to-decision ≤ 7 days; zero cards older than 14 days without a decision.

## 8. Week 1 checklist

- [ ] Add `bin/triage_run.sh`, `bin/triage_prompt.md`, `bin/delta_run.sh`, `bin/delta_prompt.md`; launchd entries at 07:15, 13:15, Mon 08:15.
- [ ] Reuse the hub-data Drive uploader for the bus; folder ids in `queue/README.md`; conversion disabled; list by parent id.
- [ ] Add `bin/hypotheses_run.sh`, `bin/hypotheses_prompt.md`; launchd 09:15; read-only checkout of the repository for the register.
- [ ] Curation proposal: `note_tweet`, `entities.urls`, `conversation_id`; split the Jev query; promote eight handles.
- [ ] Backfill: run triage once over the last 14 days of `processed/` (expect a burst of notes; cap at 30, defer the rest).
- [ ] File the first watch requests from T2–T4 (§6 of the programme plan lists them).
- [ ] First delta the following Monday.
