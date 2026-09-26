
# Scraping agent flow: how the X signals pipeline runs

Written 2026-09-26 from the code (`bin/*.py`, `bin/*.sh`), the launchd jobs and the batches on disk. The same pipeline code runs two feeds side by side. Only the config, prompts, paths and hub page differ.

| Feed | Folder | Focus | Hub page |
|---|---|---|---|
| Self-Improving Agents | `~/MemoryRSI-Signals/` | agentic memory, Jev, recursive self-improvement (RSI) | https://claude.ai/artifact/HoJHLMXZE8vrnvNdh8gEcz |
| Decision Layer Signals | `~/LocalAI-Signals/` | Jev, harnesses, model routing, search-rerank | https://claude.ai/artifact/WDZV229cKXswfW6PdA2W8v |

The memory-stack work draws on the **Self-Improving Agents** feed. Numbers below are given for both.

## 1. How it runs

It runs as three scheduled jobs per feed on one Mac (launchd, user `gui/501`), at local time (IST, UTC+5:30). Nothing runs in the cloud except the Claude calls, and nothing ever posts to X.

| Stage | Job | Schedule (Self-Improving Agents / Decision Layer) | What it does | Model |
|---|---|---|---|---|
| 1. Fetch | `bin/fetch_run.sh` runs `x_signals_fetch.py` | every 3 h at :13 / :03 (8 runs a day) | Calls the X API v2 with an app-only bearer token. For each handle in `config/handles.txt` (max 12) it pulls the user timeline, excluding replies and retweets. For each query in `config/queries.txt` (max 7) it runs a recent search (last 7 days only), with retweets and the @grok bot excluded in the query itself. It tracks a since-id per source, so each run returns only posts new since the last run. It fetches up to 25 posts per source per run, stops at 25 API requests per run, and short-circuits on a 402 (credits exhausted). It dedupes by post id within a batch and writes one JSONL batch to `inbox/`. It then rebuilds the hub page data and uploads it to Google Drive. | none (deterministic) |
| 2. Digest | `bin/digest_run.sh` runs a headless Claude Code session with `bin/digest_prompt.md` | every 3 h at :43 / :33, 30 min after each fetch | Reads every `inbox/*.jsonl` and selects what matters against the focus in the prompt. It writes the daily report and brief, grows `reports/glossary.md` (with mermaid diagrams) and the micro trends in `reports/trends.md`, and appends or merges today's insight items into `site/data/insights.json`. It then moves the consumed batches to `processed/`. Same-day re-runs merge; they never drop published items. | Claude (Opus-class), headless |
| 3. Curation | `bin/curation_run.sh` runs `discover_voices.py`, then a headless Claude session with `bin/curation_prompt.md` | daily 22:17 / 22:07 | Discovery lists everyone posting on the topics in the last 7 days and writes `reports/voices-<date>.json`. The curator then reviews a rolling 7-day window. It PROPOSES query and handle changes in `reports/curation-<date>.md` but never edits `config/`; the owner applies them by hand. It owns the macro trends and scores 3 to 6 month predictions in `trends.md`. | Claude (Opus-class), headless |
| 4. Publish | manual (the `/hub-publish` skill or a Claude session) | on demand | Headless sessions cannot publish artifacts, so the hub page is republished by hand. Between publishes, the page pulls fresher data from Google Drive through the viewer's Drive connector. | none |

**Failure behaviour:**
- A failed source is logged (`logs/fetch.log`) and skipped; the rest of the batch still writes.
- Its since-id stays put, so the next run catches up, up to the 25-post window.
- **Busy searches lose posts silently.** Each source returns at most 25 posts per run with no pagination, and the since-id then jumps to the newest post returned. When a query has more than 25 new posts in 3 hours, the older ones are never fetched. Across the first 8 batches of this feed, 20 source-batches hit the cap: the Jev query 7 times, "recursive self-improvement" 5, "agent memory" 4, and 4 other queries once each. So daily volume on busy topics is a floor, not a count.
- A 402 stops the fetch after 2 probe requests.
- Network errors do not short-circuit, so every source is attempted.
- Discovery failures are non-fatal: curation runs without them.

## 2. What each item carries (one JSON object per line in `inbox/` or `processed/`)

```json
{
  "id": "2103321894661595551",
  "url": "https://x.com/typesafeai/status/2103321894661595551",
  "handle": "typesafeai",
  "created_at": "2026-09-25T03:13:12.000Z",
  "text": "Jev generally out-performed frontier LLMs at a fraction of the price:\nRepeat-question matching: 70% → 97% ... https://t.co/tBg4CIigz0",
  "metrics": {"likes": 13, "reposts": 0, "replies": 2, "quotes": 0, "views": 4543},
  "source": "timeline:typesafeai",
  "quoted": {"handle": "...", "text": "...", "url": "https://x.com/.../status/..."}
}
```

| Field | Always present | Notes |
|---|---|---|
| `id` | yes | X post id (string). Unique within a batch; the same post can appear in two batches only if two sources both return it before either since-id moves. |
| `url` | yes | Canonical `x.com/<handle>/status/<id>`. |
| `handle` | yes | Author's @handle, without the @. |
| `created_at` | yes | ISO 8601 UTC. A source's first fetch backfills up to 25 older posts, so old timestamps in a batch mean backfill. |
| `text` | yes | Post text as the API returns it. **Posts longer than 280 characters are truncated**, because the fetcher does not request `note_tweet`. Median length is about 250 chars, and the longest seen is 738. |
| `metrics` | yes | `likes`, `reposts`, `replies`, `quotes`, `views`. `views` can be null. **This is a snapshot at fetch time**, usually minutes to hours after posting, so it undercounts. |
| `source` | yes | Which config line earned the post: `timeline:<handle>` or `search:<first 40 chars of the query>`. This is the key to per-query yield. |
| `quoted` | about 3 to 7% of items | `{handle, text, url}` of the quoted post, when the post quotes one. Timeline sources only; search results do not expand quotes. |

**What items do NOT carry**, and has to be fetched separately when it is needed (the evidence catalogue did exactly this via `bin/evidence_collect.py`):
- **Link targets:** links stay as `t.co` short links, so an item does not say whether it points to a paper, repo or blog.
- **Long-post full text:** `note_tweet` is not requested.
- **Media:** images and charts are not captured. They often hold the actual numbers, as they did in 26 of the catalogue's evidence posts.
- **Thread context:** no `conversation_id`, no replies, no same-author thread.
- **Author profile:** no bio or follower count; `reports/voices-<date>.json` has these for discovered authors.
- **Other metadata:** no language tag, no reply/retweet flags (replies and retweets are excluded at fetch time), and no topic labels or scores. All selection and judgment happen downstream in the digest.

## 3. Volume per day

Measured from `processed/*.jsonl` after each feed's focus started. The first days include first-fetch backfill and manual extra runs.

| Feed | Day | Items | Batches | Notes |
|---|---|---|---|---|
| Self-Improving Agents | 2026-09-25 | 469 | 5 | Day one: the first batch (198) was a full backfill. |
| Self-Improving Agents | 2026-09-26 (to 06:43) | 243 | 3 | Steady state: 60 to 94 per batch. |
| Decision Layer Signals | 2026-09-24 | 605 | 7 | First steady-state day. |
| Decision Layer Signals | 2026-09-25 | 715 | 9 | Includes 1 manual extra run. |
| Decision Layer Signals | 2026-09-26 (to 06:33) | 212 | 3 | 59 to 86 per batch. |

These are items fetched, not items posted: busy queries are capped at 25 per run (see section 1).

**Steady state for the Self-Improving Agents feed: about 45 to 105 items per batch, 8 batches a day, so roughly 450 to 700 raw items a day.** 96% come from search queries and 4% from timelines, because only one handle (`typesafeai`) is tracked so far; handle promotions from curation will shift that mix.

**How much survives the digest:**
- Each 3-hourly digest keeps 3 to 7 items plus a "Radar" list. They merge into about 5 to 25 insight items per day in `insights.json`.
- Trends get about 5 to 15 evidence bullets per day, each linked to a post.
- Curation's day-one yield estimate was about 15% of items cited somewhere.

Budget: about 9 X API requests per fetch for this feed (1 lookup + 1 handle + 7 queries), plus about 10 a day for discovery. That is about 80 requests a day, and the Decision Layer feed adds about 140.

## 4. Where output lands

```
~/MemoryRSI-Signals/
  config/queries.txt, handles.txt     what to fetch (edited by the owner only)
  inbox/signals-YYYYMMDD-HHMMSS.jsonl  fresh raw batches (fetch writes; digest consumes)
  processed/                          raw archive; every batch ever consumed
  reports/YYYY-MM-DD.md               daily digest: 3-7 items + Radar + query tuning notes
  reports/YYYY-MM-DD-brief.md         the same items, meaning-first, with a "So what"
  reports/glossary.md                 living glossary (Concepts / Systems & tools / Methods & papers / Benchmarks & evals)
  reports/trends.md                   micro trends (digest) + macro trends and outlook calls (curation), every evidence line linked
  reports/curation-YYYY-MM-DD.md      daily config review and proposals
  reports/voices-YYYY-MM-DD.json      who is posting on the topics, ranked
  site/data/insights.json             the insight archive the hub renders
  site/index.html                     generated hub page (never hand-edited)
  site/data/hub_data.json             the same data for the live Drive relay (gdrive:memory-rsi-hub-data.json)
  evidence/                           the memory-stack evidence catalogue (on demand, not scheduled)
  logs/fetch.log, digest.log, curation.log
```

State (since-ids, user-id cache) lives outside the folder in `~/.config/memory-rsi-signals/state.json`. The X token is shared between both feeds.

## 5. Who reads it today

| Reader | Reads | How |
|---|---|---|
| The digest agent (headless Claude) | `inbox/*.jsonl` | Every 3 h. It is the only consumer of raw items. |
| The curation agent (headless Claude) | `processed/`, `reports/`, `voices-*.json`, `config/` | Daily, to judge per-source yield. |
| The owner (one person) | the hub page (Insights, Trends, Glossary, Raw feed tabs, with search), sometimes the report files | On demand. Proposals in the curation report are applied by the owner. |
| Claude sessions on request | anything in the folder | For example, the evidence catalogue, and this document. |

**No team reads it today.** There is no alerting, no ticket or queue integration, no per-item status (seen, triaged, acted on), no reviewer assignment, and no weekly rollup. The digest runs 8 times a day and curation daily. The only week-scale view is curation's rolling 7-day window, and it is about config yield, not content.

## 6. Hooks for fitting a triage rubric, note template and weekly delta

These are observations from the code, offered as fitting points; nothing here is built yet.
- **Triage rubric:** apply it where the digest selects items, in the "Select what matters" step of `digest_prompt.md`, or as a separate pass over `inbox/` before the digest. Each raw item has only the fields above. A rubric that needs link targets, images or thread context needs an enrichment step first; `bin/evidence_collect.py` shows how, at about 1 API request per 100 posts plus 1 per thread.
- **Note template:** the digest items (`reports/YYYY-MM-DD.md`) and the insight objects (`{date, sowhat, items:[{headline, body, links:[{handle,url}]}]}`) are the current "note" units. The source-note template used for the evidence catalogue (`evidence/raw/SOURCE_NOTE_TEMPLATE.md`) is a deeper per-source format.
- **Weekly delta:** there is no week-over-week artifact today. The raw inputs for one exist:
  - `insights.json`, dated per day
  - `trends.md`, where evidence bullets are dated and statuses change
  - the dated daily curation reports
  - `voices-*.json`, dated, for who is rising
- **Stable ids:** the post `id` is the natural key for item-level status. Trend names in `trends.md` are the natural key for trend-level deltas.

