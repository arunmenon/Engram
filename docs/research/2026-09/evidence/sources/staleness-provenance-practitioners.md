# Staleness and provenance as the core memory-write problem: practitioner posts (roscherveniak, JeffWitters, chebyte, tonygaorx) and their threads

- **URL:** https://x.com/roscherveniak/status/2102862264231751794 ; https://x.com/JeffWitters/status/2103546324373197212 ; https://x.com/chebyte/status/2103554185551864286 ; https://x.com/tonygaorx/status/2103552623127228507 ; context posts https://x.com/virgilxbt/status/2102850232249635116 and https://x.com/rvaniaaaa/status/2103124020245803430 ; their linked X Articles (slash1sol, rvaniaaaa)
- **Type:** X post (short practitioner replies and posts) + two linked X Articles
- **Author / org:** Ros (@roscherveniak), Jeff Witters (@JeffWitters), chebyte (@chebyte), Tony (@tonygaorx); context: virgilxbt, rvaniaaa (@rvaniaaaa), slash1s (@slash1sol). No affiliations given in the capture.
- **Date:** 2026-09-23 to 2026-09-25 (linked articles 2026-08-20 and 2026-09-10)
- **Retrieved:** 2026-09-26 (local copies: raw/evidence.json, raw/linked_posts.json; image media/linked-3_2090499054585192449.jpg and media/linked-3_20974*.jpg, transcribed in sources/images-transcribed.md). Post texts verbatim; `&lt;`/`&gt;` decoded.
- **Cited by evidence:** Staleness and provenance as the core memory-write problem / 2026-09-23 roscherveniak; 2026-09-25 JeffWitters; 2026-09-25 chebyte; 2026-09-25 tonygaorx. These four are all the evidence items in the trend.
- **Relevance to a memory stack:** medium. The posts are opinions with almost no data, but they state crisp, implementable write rules (decision records with date and reason, per-line provenance so revocation can aim, save for a 30 to 60 day horizon). Engagement is tiny (0 to 1 likes, 7 to 25 views each).

## TL;DR
- **JeffWitters:** store decisions, not facts. A decision "arrives with a date and a reason attached, so when it stops being true there is something to check it against." Facts "go stale silently."
- **chebyte:** "Treat agent memory as untrusted" is the easy half; the miss is provenance per line (tool result vs prior persona dump vs the user). Without it "revoke has nowhere to aim."
- **roscherveniak:** separate what the agent sees now from what happened before; open question: how to invalidate episodic memory when the underlying file or permission changes.
- **tonygaorx:** file-based agent memory "works at first" but output gets "lobotomized from stale files and token limit. 99% of artifacts are usually wasted." Rule: save what you want in 30 or 60 days, not what is useful now or tomorrow. The 99% figure has no stated basis beyond "a design pattern we preach internally".
- **Coarse-to-fine indexing:** not found in any post, thread, quoted post or linked article of this trend. Nothing in the captured material states it.

## What it claims / describes

### 1. @roscherveniak, 2026-09-23 20:46 UTC (0 likes, 7 views), reply to @virgilxbt, verbatim
> @virgilxbt The useful line here is separating what the agent sees now from what happened before. How do you invalidate episodic memory when the underlying file or permission changes?

Replied-to post, @virgilxbt, 2026-09-23 19:58 UTC (196 likes, 19 reposts, 17 replies, 16,659 views), verbatim:
> A 13-PAGE BREAKDOWN OF AGENT MEMORY THAT CUTS TOKEN COST BY 90%
>
> Every morning your agent rereads the same 12 files.
>
> It arrives at the same conclusions it reached yesterday.
> And you pay for that thinking one more time.
>
> The model got 10x smarter in two years.
> It still wipes everything the moment a session ends.
>
> Five layers fix that:
>
> 1. working memory -- what it sees right now
> > The context window.
> > Once it fills, the older context slides out.
> > Most agents live here and never get further.
>
> 2. episodic memory -- what happened
> > A full interaction log with timestamps.
> > The deploy that broke Tuesday at 3am over a typo stays on file.
> > You explain it a single time.
>
> 3. semantic memory -- what is true
> > Facts, entities and relationships held in a knowledge graph.
> > "This user prefers TypeScript" carries over to the next session.
>
> 4. procedural memory -- how to do things
> > Three approaches get tried, one of them works.
> > That one is saved as a reusable skill.
> > The next run picks up from it.
>
> 5. forgetting -- what to delete
> > An agent that keeps everything ends up full of contradictions.
> > You move cities, and it keeps pushing the restaurants you left behind.
>
> The numbers:
>
> > Mem0 -- 1,800 tokens per query instead of 26,000.
> > 91% lower latency.
> > Snowflake -- one ontology layer, 20% more accuracy, 39% fewer tool calls.
>
> Memory pays for itself from the first day.
>
> The layer nobody bothers to build is the forgetting engine.
> It is what keeps the other four worth trusting.
>
> Full 13-page breakdown below ↓

The "13-page breakdown" link resolves to @slash1sol's X Article (2026-09-10), "$50 or $15: GPT-6 Astra vs Kimi K3, and Why the Smart Money Runs Both". That article is about routing work between two models, not about agent memory; it does not contain the Mem0 or Snowflake numbers. Its only memory-relevant content is a gate spec (verbatim):
```markdown
# gate_spec.md -- what the Astra pass is allowed to do

INPUT: the swarm's final deliverable plus its evidence list.
JOB: find what is wrong. Praise is not an output.

CHECK: every number has a source and a read time.
CHECK: no two findings contradict each other unflagged.
CHECK: no edge in the graph lacks the shared source that created it.

OUTPUT: a fix list, each item pointing at the line it refers to,
or the single word "clean". Nothing else. Do not rewrite the work.
```

### 2. @JeffWitters, 2026-09-25 18:05 UTC (1 like, 2 replies, 22 views), verbatim
> Agent memory should store decisions, not facts. Facts go stale silently. A decision arrives with a date and a reason attached, so when it stops being true there is something to check it against.

The 2 replies were not captured.

### 3. @chebyte, 2026-09-25 18:36 UTC (0 likes, 2 replies, 25 views), verbatim
> "Treat agent memory as untrusted" is the easy half.
>
> The miss is provenance. Which line came from a tool result, which from a prior persona dump, which from me.
>
> Without that split, a summary diff is cosplay -- revoke has nowhere to aim.
>
> Disagree?

The original post has an em dash where this copy shows "--" (rendered this way because this catalogue does not use em dashes). The 2 replies were not captured. What it replies to (if anything) is not in the capture.

### 4. @tonygaorx, 2026-09-25 18:30 UTC (0 likes, 23 views), reply to @rvaniaaaa, verbatim
> great start. you're essentially building "agent memory"
>
> this works at first but after a while your output will be lobotomized from stale files and token limit. 99% of artifacts are usually wasted.
>
> this is a design pattern we preach internally: save what you want to have in the future e.g 30 days 60 days, not what is useful now or for the next day. thus i would be very more careful with "what" you're storing as first class citizens.

Replied-to post, @rvaniaaaa, 2026-09-24 14:06 UTC (660 likes, 131 reposts, 21 replies, 68,611 views), verbatim:
> I still don't understand why people are still explaining themselves to AI from scratch every single day
>
> a hundred times this year, you told it who you are. a hundred times, it forgot
>
> five minutes fixes this:
>
> create a folder → name it raw → drop in any source, article, transcript, PDF, voice memo
>
> tell the model to read it once → link it to everything already there → never touch it again
>
> create one more file → name it CLAUDE.md → who you are, what you're building, what already failed
>
> now every session starts here → the model reads it automatically → before you type a single word
>
> ask it anything across everything you've ever fed it → it answers from months of compiled understanding → not from zero
>
> most people quit around month one → nothing looks like it's working yet → that's exactly where the value starts
>
> five minutes to set up. you never explain yourself from scratch again

It links rvaniaaaa's X Article (2026-08-20), "The Second Brain Is Not a Storage System. It's a Compiler." Relevant parts (verbatim):
- Quoting Karpathy's LLM Wiki: "RAG re-derives knowledge on every query. A compiled wiki derives it once and keeps it current."
- "A source comes in. The system reads it, extracts what matters, connects it to everything already there, updates related pages, flags contradictions with older entries, and files the synthesis permanently." "One source touches ten to fifteen pages."
- Honest part: "Garbage in means garbage compiled, not garbage retrieved... A bad source in a library is easy to remove. A bad source in a compiler has touched fifteen pages before you notice." Value threshold: "around 50 to 100 well-compiled sources."
- Daily compilation prompt: "Set up a daily compilation task. Check my vault. File anything new in Inputs folders into the right place and link it to related notes. Flag anything that has gone stale or has not been updated in more than two weeks. Check for contradictions between recent additions and existing wiki pages. Write me a brief: what you changed, what you linked, what you flagged, and what I should look at today."
- The article's one image is a screenshot of Karpathy's `llm-wiki.md` gist page (5,000+ stars, 5,000+ forks shown).

### Every concrete design rule extracted

| # | rule | source (verbatim basis) | number / threshold | evidence behind it |
|---|---|---|---|---|
| 1 | Store decisions, not bare facts; each record carries a date and a reason | JeffWitters | none | opinion |
| 2 | On staleness, check the record against its reason ("something to check it against") | JeffWitters | none | opinion |
| 3 | Tag every memory line with its source class: tool result, prior persona dump, or the user | chebyte | 3 source classes named | opinion |
| 4 | Revocation must target lines by provenance; a summary diff without per-line source is not enough | chebyte | none | opinion |
| 5 | Keep "what the agent sees now" (current state) separate from "what happened before" (episodic log) | roscherveniak | none | opinion |
| 6 | Invalidate episodic memory when the underlying file or permission changes (posed as an open question, no mechanism given) | roscherveniak | none | question only |
| 7 | Store only what you would want in 30 to 60 days, not what is useful now or tomorrow | tonygaorx | 30 / 60 days horizon | "a design pattern we preach internally" |
| 8 | Expect most saved artifacts to be unused | tonygaorx | "99% of artifacts are usually wasted" | no dataset, no measurement, no definition of "artifact" or "wasted" |
| 9 | Build a forgetting layer; keeping everything produces contradictions | virgilxbt | none | anecdote ("You move cities...") |
| 10 | Every number carries a source and a read time; no graph edge without the shared source that created it; no unflagged contradictions | slash1sol gate spec | none | a checker spec, not a memory system |
| 11 | Daily pass flags items not updated in more than two weeks and checks new additions against existing pages for contradictions | rvaniaaaa article | 2 weeks; daily | prompt recipe, no measurement |
| 12 | Coarse-to-fine indexing | not found | not stated | not present in any captured source for this trend |

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| saved artifacts unused | ~99% ("99% of artifacts are usually wasted") | | tonygaorx, no setup | assertion, no basis stated |
| save horizon | 30 or 60 days | "useful now or for the next day" | tonygaorx | internal practice, no data |
| Mem0 tokens per query | 1,800 vs 26,000; 91% lower latency | | virgilxbt | unsourced in the post; not in the linked article |
| Snowflake ontology layer | +20% accuracy, 39% fewer tool calls | | virgilxbt | unsourced |
| "cuts token cost by 90%" | 90% | | virgilxbt headline | unsourced |
| staleness flag age | > 2 weeks without update | | rvaniaaaa article prompt | recipe |
| pages touched per source | 10 to 15 | | rvaniaaaa article | claim |
| sources before compilation pays off | 50 to 100 | | rvaniaaaa article | claim |
| engagement of the four evidence posts | 0 to 1 likes, 7 to 25 views | | | very low reach |

## Mechanism details you could implement
A memory record schema that satisfies rules 1 to 4 and 7 (inference, assembled from the posts; no post gives a schema):
```text
{ id, kind: decision|constraint|..., text, decided_at (date), reason, source: user|tool_result|persona_dump|..., source_ref, horizon_days: 30|60, superseded_by?, revoked_at? }
```
Concrete implementations already in the catalogue that answer these posts:
- **Per-line provenance and targeted distrust:** jevmem records `{id, sha256(text)[:16], ts, via: hook|mcp|import}` per line it wrote; any line whose id+hash is not recorded is "unverified" and gets an injection check before being served (`github-avinash-jetwani-jevmem.md`). Its source classes are "written by this machine's gate" vs everything else, not chebyte's tool/persona/user split.
- **Date + confidence on every line, and a reason for reversals:** jevmem lines carry `ts` and `conf`, and reversals keep the old line as `[superseded] ... → id:new`. There is no free-text reason field.
- **Invalidation on file change (roscherveniak's question):** jevmem `audit` asks per memory "Is memory X still true for this repository, given the snapshot?" and flags `[stale?]` below 0.4; Hippo's `hippo learn --git` weakens memories matching migration and breaking-change commits, and `hippo invalidate "<pattern>"` exists (`github-kitfunso-hippo-memory.md`). Neither handles permission changes.
- **Derivations traceable to sources:** Supermemory says derived facts are "each traceable to its sources" (`consolidation-phase-supermemory-rauch.md`).

## Limitations, caveats, counter-evidence
- All four evidence items are short opinion posts with near-zero reach and no data. The trend is a pattern of stated views, not of measured failures.
- The "~99% unused" figure has no stated basis, denominator, or definition. Treat it as rhetoric until measured.
- roscherveniak asks a question; the post does not claim staleness is "the core" failure.
- virgilxbt's numbers are unsourced, and the "13-page breakdown" link points to an unrelated article about model routing, so the post's numbers cannot be traced from the capture.
- rvaniaaaa's viral post argues the opposite of tonygaorx: read every source "once", "never touch it again", and value starts after month one. tonygaorx's reply is the dissent, with no data on either side.
- JeffWitters' "decisions, not facts" conflicts with systems that store facts with timestamps (e.g. Hindsight world facts, Hippo episodic memories); the post gives no comparison.
- Replies to JeffWitters (2) and chebyte (2) were not captured, so any pushback is unknown.

## Takeaways for tuning a memory stack
- Give every memory entry a date, a reason and a source class at write time, so later invalidation has something to test and revocation has something to target.
- Store provenance per line, not per summary; a summary regenerated from mixed sources cannot be partially revoked.
- Add a write-time horizon test ("will this matter in 30 to 60 days?") as a gate question, and log how often saved entries are ever recalled, so you can test the 99% claim on your own data.
- Run a separate invalidation pass keyed to changes in the underlying files (and, if relevant, permissions), rather than relying on recency decay.

## Open questions
- What fraction of saved entries in a real agent memory are ever recalled? No source measures it.
- Does storing reasons with decisions measurably reduce stale-entry retrieval? Not tested.
- Who has implemented invalidation on permission changes? None found.

---
