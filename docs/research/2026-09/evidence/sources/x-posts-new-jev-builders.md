# X posts: new Jev builders (jreuben1, roanjain) and the linked posts from rvaniaaaa and slash1sol

- **URL:** https://x.com/jreuben1/status/2103553740938625030 ; https://x.com/roanjain/status/2103554942611189795 (and its parent https://x.com/roanjain/status/2103554471121031293) ; https://x.com/rvaniaaaa/status/2090512486738845784 (X Article https://x.com/i/article/2090496192136290304) ; https://x.com/slash1sol/status/2098013767627837827 (X Article https://x.com/i/article/2097363355673456640)
- **Type:** X post (plus two X Articles reached through linked posts)
- **Author / org:** (((JReuben1))) (@jreuben1; bio: "AI, CUDA HPC, JAX / PyTorch, Claude, Rust, MLIR, Software Architecture..."); Rohan Jain (@roanjain; bio: "Staff Engineer @hippocraticai | Building reliable, safe voice AI | Daily lessons from production AI"); rvaniaaa (@rvaniaaaa; bio: "Markets. Systems. Things people overlook. Explaining AI workflows & systems."); slash1s (@slash1sol; bio: "smoke cigs & post about AI tools and coding / trade crypto, stocks and prediction markets")
- **Date:** jreuben1 2026-09-25 18:34 UTC; roanjain 2026-09-25 18:37 and 18:39 UTC; rvaniaaaa article post 2026-08-20 18:53 UTC; slash1sol article post 2026-09-10 11:40 UTC
- **Retrieved:** 2026-09-26 (local copies: raw/evidence.json, raw/linked_posts.json; article images media/linked-3_2090499054585192449.jpg and media/linked-3_20974*.jpg, transcribed in sources/images-transcribed.md). Texts verbatim; HTML entities decoded.
- **Cited by evidence:**
  - Decision models as the memory control plane / 2026-09-25 jreuben1 ("Jevmem ships automatic project memory for Claude Code built on Jev; no details yet"). The repo is written up in `github-avinash-jetwani-jevmem.md`.
  - Typed-decision tier displacing LLM calls on bounded classification / 2026-09-25 roanjain ("Voice-agent pipeline puts Jev between ASR and the main LLM, replacing a separate intent parser").
  - The rvaniaaaa article is linked from the post tonygaorx replied to (Staleness and provenance / 2026-09-25 tonygaorx). The slash1sol article is linked from the virgilxbt post roscherveniak replied to (Staleness and provenance / 2026-09-23 roscherveniak). Neither article mentions Jev.
- **Relevance to a memory stack:** low to medium. jreuben1 is only a pointer (the repo is the substance). roanjain gives one placement rule for a decision model in a voice turn. The rvaniaaaa article is a "compile at ingest" file-memory recipe with a daily staleness pass; the slash1sol article is about model routing, with a gate spec that requires a source and read time per number.

## TL;DR
- **jreuben1:** one-line pointer, "Jevmem – automatic project memory for Claude Code, built on Jev", linking the Avinash-jetwani/jevmem repo. 1 like, 88 views.
- **roanjain:** voice flow "Caller → ASR → Jev → application policy → main LLM/tool → voice response"; Jev "runs after speech is transcribed but before the agent takes its next action." Only 1/7 of the thread and its parent were captured; the captured text does not mention replacing an intent parser.
- **rvaniaaaa article** ("The Second Brain Is Not a Storage System. It's a Compiler."): pay the understanding cost once at ingest; one source touches 10 to 15 pages; flag contradictions; daily task flags anything not updated in more than two weeks; value appears after 50 to 100 well-compiled sources. 1,356,391 impressions.
- **slash1sol article** ("$50 or $15: GPT-6 Astra vs Kimi K3..."): route wide work to a cheap model and send only the irreversible or costly tail to an expensive gate; gate spec requires "every number has a source and a read time". Not about memory; it is the "13-page breakdown" link in virgilxbt's memory post.

## What it claims / describes

### 1. @jreuben1, 2026-09-25 18:34 UTC (1 like, 1 reply, 88 views), verbatim
> Jevmem – automatic project memory for Claude Code, built on Jev https://t.co/GPf32yhGF9

Link: https://github.com/Avinash-jetwani/jevmem ("Automatic project memory for Claude Code. Also works with Cursor and Codex."). The reply was not captured. The en dash is in the original.

### 2. @roanjain thread (Rohan Jain)
Parent, 2026-09-25 18:37 UTC (0 likes, 1 reply, 9 views), verbatim:
> Someone asked the best question after Part 1 of 5 Part series:
>
> Where exactly does Jev sit in a Voice AI turn, before tool selection or after intent is parsed?
> There’s no universal answer. Here’s the architecture I would use.
> Part 3/5 🧵

Evidence post, 2026-09-25 18:39 UTC (0 likes, 1 reply, 10 views), verbatim:
> 1/7
> Start with the simplest flow:
> Caller → ASR → Jev → application policy → main LLM/tool → voice response
> Here, Jev runs after speech is transcribed but before the agent takes its next action.

Posts 2/7 to 7/7 and Parts 1, 2, 4 and 5 of the series were not captured. What Jev is asked at that point, the thresholds, and the latency are not stated.

### 3. @rvaniaaaa linked post and X Article
Post 2026-08-20 18:53 UTC (795 likes, 76 reposts, 17 replies, 2,947 bookmarks, 1,356,391 impressions); text is only the t.co link to the article. The later viral post that tonygaorx replied to is quoted in `staleness-provenance-practitioners.md`.

Article title: "The Second Brain Is Not a Storage System. It's a Compiler.". Full text, verbatim:

> Most people who build a second brain make the same mistake. They treat it like a filing cabinet. Drop notes in. Search when needed. Hope the right thing surfaces.
> That is retrieval. And retrieval has a ceiling.
> Andrej Karpathy described something different in April 2026. He called it LLM Wiki. The idea spread across GitHub within days. 5,000 stars. 16 million views on a single post about a folder structure. Thousands of engineers reading the same sentence and feeling something shift.
>
> "RAG re-derives knowledge on every query. A compiled wiki derives it once and keeps it current."
> That distinction changes everything about how you build.
> The difference between storing and compiling
> When you store knowledge, you are building a library. Information goes in. You search when you need it. The library does not grow on its own. It does not make connections. It does not flag when two notes contradict each other.
> When you compile knowledge, something different happens. A source comes in. The system reads it, extracts what matters, connects it to everything already there, updates related pages, flags contradictions with older entries, and files the synthesis permanently. The next time you add a source, it builds on what was already compiled. Not on the raw inputs. On the processed understanding.
> The library gets bigger over time. The compiler gets smarter.
> RAG systems pay the cost of understanding on every single query. A compiled wiki pays it once, at ingest, and every query after that draws on structured, linked, cross-referenced knowledge the model built and maintains. That is not a productivity trick. It is a fundamentally different architecture.
> The architecture
> Three folders. One file. One loop. Here is what changes when you treat it as a compiler instead of a library.
> raw/ is the input buffer, not the brain. Nothing that enters raw is ever the answer. It is the raw material waiting to be compiled. wiki/ is where compilation happens. One source touches ten to fifteen pages. Connections form automatically. Contradictions get flagged. The human reads it. The model writes it. output/ is built from compiled knowledge, not from memory and not from raw.
> At the center: CLAUDE.md. A compiled profile of who you are, how you think, what you have tried. Not a prompt you write once and forget. A living document the model maintains and reads before every session.
> The loop does not just file things. It compiles them. Every new source gets ingested, linked, and integrated into the existing structure. Then it writes you a brief on what it changed and why, so you stay inside the system instead of wondering what it did while you were gone. You open your laptop and the compilation already happened. You start where the thinking left off.
> Why most second brains stop working after three months
> The filing cabinet model fails for one reason: maintenance burden. You capture a note. You organize it. You cross-reference it. You update it when something changes. Every one of those steps requires a human decision. Human time. Human energy.
> Most personal wikis quietly rot. Not because the person stopped caring. Because the maintenance cost compounds faster than the value compounds.
> Karpathy named this directly: "The act of collecting information is effortless. The act of keeping fifty interlinked notes current, consistent, and cross-referenced is the work that no human sustains."
> The compiled wiki shifts that burden to the model. Claude does not get tired of filing. It does not forget to link the new note to the three older ones it contradicts. The human contribution becomes irreducible: source selection, research direction, synthesis oversight. Everything else runs.
> What happens over time
> One month in: context stops disappearing between sessions. Three months in: the wiki surfaces connections you never consciously made. The system found the link between an idea from January and a note from last week. You did not have to. Six months in: the gap between you and someone starting from zero is structural. Not because you are smarter. Because your compiled knowledge base draws on six months of processed understanding. Theirs resets every session. One year in: open the graph view. Hundreds of nodes. All connected. All maintained. The system knows things you had forgotten you knew.
> The honest part
> The compiler approach has real limitations worth naming.
> Quality depends entirely on source quality. Garbage in means garbage compiled, not garbage retrieved. The difference matters because retrieval surfaces one bad document. Compilation integrates it into everything. A bad source in a library is easy to remove. A bad source in a compiler has touched fifteen pages before you notice.
> The first few weeks feel slow. The graph is small. The connections are obvious. The value of compilation only becomes clear when the wiki has enough density that the model starts finding non-obvious links. That threshold is around 50 to 100 well-compiled sources. Before that, a good search engine does most of the same job.
> And this requires Claude Desktop and a paid plan. The scheduled tasks and file system access that make the loop run do not work on the free tier.
> Build with those constraints in mind and the system earns its cost quickly. Ignore them and you will rebuild the filing cabinet you started with.
> The prompts that run the system
> For those who want to build this today.
> To ingest a new source:
> I just added a new file to my raw folder called [filename]. Read it, extract the key concepts and claims, write a wiki article for each major concept, link them to related pages already in my wiki, and flag any contradictions with what I already have. Then summarize what changed in three sentences.
> To build your CLAUDE.md:
> You are setting up my second brain. Interview me one question at a time. Ask about: who I am and what I do, my goals for this year, how I want you to communicate with me, my strengths and weaknesses, and my current projects. Wait for each answer before moving to the next. When finished, write everything into a file called CLAUDE.md at the vault root, organized with clear headers, so you load it automatically every session.
> To build a project folder:
> Create a project folder called [project name]. Inside it, create four folders: Inputs, Process, Outputs, Feedback. Then write a CLAUDE.md inside that project folder describing what it is, its single goal, what done looks like, and your specific role in helping me reach it.
> To set up the daily compilation loop:
> Set up a daily compilation task. Check my vault. File anything new in Inputs folders into the right place and link it to related notes. Flag anything that has gone stale or has not been updated in more than two weeks. Check for contradictions between recent additions and existing wiki pages. Write me a brief: what you changed, what you linked, what you flagged, and what I should look at today.
> The reversal
> Most people are using Claude as a search engine with better manners. You ask. It answers. You close the tab. Tomorrow it remembers nothing. You are still the one holding all the context. Every session you pay the same understanding cost again.
> The compiled second brain changes that direction. You stop being the memory layer. The system becomes it.
> Retrieval answers questions. Compilation builds understanding.
> Build the compiler. Let it run. The compounding starts immediately and it never stops.

Article image (media/linked-3_2090499054585192449.jpg): a screenshot of the GitHub gist page "karpathy / llm-wiki.md" ("Created 4 months ago", 5,000+ stars, 5,000+ forks), heading "LLM Wiki", "A pattern for building personal knowledge bases using LLMs."

### 4. @slash1sol linked post and X Article
Post 2026-09-10 11:40 UTC (134 likes, 6 reposts, 25 replies, 222 bookmarks, 527,451 impressions); text is only the t.co link to the article.

Article title: "$50 or $15: GPT-6 Astra vs Kimi K3, and Why the Smart Money Runs Both". Full text, verbatim:

> Two frontier models with the same million-token window shipped seven weeks apart. One costs $10 in and $50 out and you rent it. One costs $3 in and $15 out and you can download it. They are not competing for the same job, and the launch week made that harder to see.
>
> 1,050,000 vs 1,048,576 tokens · $50 vs $15 out · 99.9% or 62.7%, depending on the harness · 2.8T open weights
>
>
> On the afternoon of September 3, four chatbots from four companies went quiet inside the same five minutes, right after OpenAI posted a clip of the stars aligning. The replies spelled ASTRA letter by letter. By evening the model was out, Greg Brockman was using the word AGI, and Sam Altman was apologising for a messy rollout.
> It was the most-watched launch of the year, and it earned it. GPT-6 Astra is a genuine step on the things OpenAI aimed it at: driving a computer, holding a million tokens without dropping them, finishing hard problems in fewer moves than a human. Pretending otherwise is not a Kimi argument. It is just wrong.
> But the week also produced a spec sheet that reads like two different products. Astra costs $10 per million tokens in and $50 out, ships closed, arrives in stages with enterprise access off by default, and carries its most powerful capability behind a gate. @Kimi_Moonshot K3 costs $3 in and $15 out, ships as 2.8 trillion open weights, and has been downloadable since July. Same context window to the token. Everything else points a different way.
> So this is not a piece about which model is smarter. It is about which one is the right tool on Tuesday, because the honest answer changes with the job.
>
> What Astra is actually for
>
> Start with the part that deserves the hype. Astra's headline is computer use, and the number behind it is real: on OSWorld 2.0 it scores 72.6% at roughly forty minutes per task, where its predecessor managed 65.7% at seventy-five. Faster and better on the same benchmark is the rarest kind of improvement, and it shows up in the demos people actually built during launch week.
> Long context is the second strength. On MRCR with eight needles it holds 100% out to 512K tokens and 96.3% in the 512K-to-1M band, the strongest deep-retrieval result any frontier lab has published. And inside Codex, Astra keeps running notes across context windows instead of compacting everything into one summary, so a long debugging session stops forgetting why the first fix failed.
> Then there is the ceiling. FrontierMath Tier 4 at 97.6%. Fewer actions than the median tested human on 96% of ARC-AGI-3 levels, with a habit of turning an unfamiliar environment into a compact symbolic model of itself. The alignment table is quietly the most impressive row: 0% cheating on honeypot tasks where its predecessor scored 48.2%, and a 2.4% computer-use safety failure rate against 22% before.
> If you have one hard problem, one agent, and a wrong step that costs more than the tokens do, Astra is the model. That is a real category and it pays for the $50.
>
> The number to read carefully
>
>
> The score OpenAI leaned on hardest was 99.9% on ARC-AGI-3, a benchmark built specifically to resist memorisation. ARC Prize published its own run the same day. On their standard harness, where each call is independent and the model can only carry notes it writes for itself, Astra scored 62.7%. On OpenAI's provider adapter harness, which preserves opaque reasoning state between requests and compacts long runs, it scored 99.9%. Same weights, same day, 37 points apart.
> ARC Prize accepts both numbers, and so should you. The lesson is not that the high score is fake. It is that the best version of Astra lives inside OpenAI's scaffolding, and that scaffolding is not something you can read, reproduce, or run yourself. Call the model statelessly from your own stack and you get the lower bar.
> The same shape appears elsewhere in the launch. Astra is the first OpenAI model rated Critical for cyber capability. The public model refuses exploit work, the real capability sits behind the Daybreak trusted-access program, and safety checks can pause unrelated tasks while they run. Fortune reported that the efficiency method behind the new architecture has safety researchers worried precisely because it makes the reasoning harder to monitor. Add the staged rollout and the enterprise off-by-default switch, and a pattern emerges: the ceiling comes with a wrapper, and you do not control the wrapper.
>
> What K3 is actually for
>
>
> @Kimi_Moonshot K3 is built for the other shape of work. Not one agent going deep for forty minutes, but three hundred going wide at once. Agent Swarm dispatches up to 300 sub-agents across roughly 4,000 coordinated steps, with parallelism trained into the model rather than bolted on as a framework, and Moonshot reports the whole run landing about 4.5 times faster than one agent grinding the same task in sequence.
> That shape is cheap by design. At $3 in, $0.30 on cached input, and $15 out, a swarm can afford to be wasteful in a way a $50 model cannot: run the first attempt, throw it away, run it again. The cache rate matters more than it looks, because a swarm re-reads the same spec and the same files hundreds of times, so most of its tokens are the cheap kind.
> And it is a model you can hold. 2.8 trillion parameters, published, downloadable, self-hostable behind your own firewall, fine-tunable on your own conventions. The command-line tool is free and MIT licensed. The reasoning is not an opaque state in someone else's harness; it is weights on your disk. Since July, teams that cannot send a proprietary line of code to any API have had a frontier model they can run anyway.
> Vision in the loop is the strength people underrate. K3 writes code, looks at a live screenshot of the result, and corrects. That is how the viral launch demos happened, and it is how a 48-hour unattended run designed and verified a chip on open EDA tools. Not a benchmark number. A finished artifact.
>
> Strength by strength
>
>
> Lay it out and the rows stop overlapping. A single hard problem, a single agent driving a browser, the deepest retrieval at a million tokens: Astra, and it is not close. Wide parallel work, cost at any real volume, owning the weights, seeing what the model does, and simply being able to use it this week: K3.
> Notice what the table does not say. It does not say one model is better. It says they were built for different Tuesdays, and the mistake most teams will make this month is paying $50 a million for width, or trying to force a swarm through a problem that needed one deep agent.
>
> The build that uses both
>
>
> The interesting stack is not either model. It is both, routed by job. K3 does the wide work: the research, the fan-out, the hundred files, the first draft of everything. Astra sits at one gate, on the hard tail, where a single wrong judgement costs more than the tokens it takes to check. Most of the tokens run at $15. Only the tokens that decide something run at $50.
>
> The cost side of that split is arithmetic on published prices, and it is worth doing once so the intuition sticks. Take a swarm run of 4,000 steps, each reading about two thousand tokens and writing five hundred:
>
> Illustrative shape, not a bill: $180 for the run on Astra, $54 on K3, around $32 once the cache does its job, and about $4.50 to put Astra on the final pass. The expensive model costs less than the price of a coffee when it only reads the answer instead of producing all of it.
> The spec that makes the gate work is short, and it is the same evidence rule that keeps a swarm honest on its own:
>
>
> When to pay the $50
>
> Be honest about the other side too. If your work is one novel problem a day, Astra is cheaper per outcome than any swarm, because a swarm of three hundred cannot help you with one question that needs a single deep thinker. If your job is a computer-use flow where minutes per task is the metric, Astra's forty-minute OSWorld number is the one that matters and nothing open matches it yet. And if you live inside Codex, the persistent notes are worth the tier on their own.
> Pay for the ceiling when you are standing under it. That is a small fraction of most teams' tokens, which is exactly the point.
>
> The point
>
> Astra is the most capable single agent you can rent, and the rental terms are the story: a price 2.5 times its predecessor, a best score that lives in a harness you cannot see, a top capability behind a gate, and a rollout that reached your admin console switched off. K3 is the most capable model you can own, and ownership is the story too: the weights, the CLI, the swarm, the bill that tracks work instead of prestige.
> They were built for different jobs. The teams that win this quarter will not pick one. They will route.
> Rent the ceiling when you need it -> own the frontier the rest of the time.
> By slash1s (@slash1sol)

The article's code blocks (verbatim; they are not in the plain text above):

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

```yaml
# route.yaml -- which model gets which job

wide:
  model: kimi-k3
  when: fan-out, research, drafts, anything over 20 items
  budget: swarm, up to 300 sub-agents

deep:
  model: gpt-6-astra
  when: one agent, one browser, one hard problem
  budget: one pass, max 40 minutes

gate:
  model: gpt-6-astra
  when: the output is irreversible or expensive to get wrong
  job: refute, do not praise. Return a fix list or "clean".

default: wide
```

```python
steps, tok_in, tok_out = 4_000, 2_000, 500
m_in, m_out = steps * tok_in / 1e6, steps * tok_out / 1e6   # 8M in, 2M out

astra = m_in * 10 + m_out * 50        # $80 + $100 = $180
k3    = m_in * 3  + m_out * 15        # $24 + $30  = $54
k3_cached = m_in * 0.30 + m_out * 15  # $2.40 + $30 = $32.40 if the context repeats

gate = 0.2 * 10 + 0.05 * 50           # one Astra pass on the tail: $4.50
print(astra, k3, k3_cached, k3_cached + gate)
```

The article's five images ("PICTURE 1" to "PICTURE 5") are transcribed in `images-transcribed.md`.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| jreuben1 reach | 1 like, 88 views | | | pointer only |
| roanjain reach | 0 likes, 10 views | | | 1 of 7 posts captured |
| rvaniaaaa article reach | 795 likes, 2,947 bookmarks, 1,356,391 impressions | | | |
| pages touched per source (rvaniaaaa) | 10 to 15 | | claim | |
| sources before compiled wiki beats search (rvaniaaaa) | 50 to 100 | | claim | no measurement |
| staleness flag (rvaniaaaa daily task) | > 2 weeks without update | | prompt | |
| Karpathy post (quoted by rvaniaaaa) | 5,000 stars, 16 million views | | | as stated in article |
| Astra vs K3 prices (slash1sol) | $10 / $50 vs $3 / $15 per M ($0.30 cached) | | | |
| ARC-AGI-3 Astra (slash1sol) | 99.9% provider harness vs 62.7% ARC Prize standard harness | | same weights, same day | harness state carried between calls vs notes only |
| swarm run cost example (slash1sol) | $180 Astra, $54 K3, $32.40 K3 cached, + $4.50 Astra gate | | 4,000 steps x 2,000 in / 500 out tokens | "Illustrative shape, not a bill" |

## Mechanism details you could implement
- **Decision model placement in a voice turn (roanjain):** ASR output → Jev → application policy (code) → main LLM or tool. The decision model sees the transcript before any agent action; policy in code consumes its answer.
- **Compile at ingest (rvaniaaaa):** on each new source, extract concepts, write/update one page per concept, link to related pages, flag contradictions with existing pages, and emit a 3-sentence change summary. A daily job files new inputs, flags pages not updated in more than two weeks, checks recent additions against existing pages for contradictions, and writes a brief.
- **Memory-relevant point in slash1sol:** the ARC-AGI-3 gap (99.9% vs 62.7%) is attributed to state carried between calls ("opaque reasoning state carried between calls") vs "each call independent, notes only". That is a harness-memory effect of 37 points on one benchmark, as reported by the article.
- **Gate spec (slash1sol):** "every number has a source and a read time"; "no edge in the graph lacks the shared source that created it"; output a fix list pointing at lines, or "clean".

## Limitations, caveats, counter-evidence
- The T2 evidence label says roanjain's pipeline puts Jev "replacing a separate intent parser". The captured posts do not say that: the parent asks "before tool selection or after intent is parsed?", and 1/7 places Jev between ASR and policy. The replacement claim may be in posts 2/7 to 7/7, which were not captured. As captured, the claim is unsupported.
- jreuben1 adds no information beyond the link.
- The rvaniaaaa article has no measurements; its own "honest part" says a bad source "has touched fifteen pages before you notice", which is an argument for per-page provenance.
- The slash1sol article is not about memory; linking it as a "13-page breakdown of agent memory" (virgilxbt) is a mismatch.

## Takeaways for tuning a memory stack
- Put the decision model at a single, explicit point before the agent acts, and let code own the policy on its output.
- If you compile memory at ingest, add a staleness sweep (e.g. two weeks without update) and contradiction checks, and keep per-page source links so one bad source can be traced across the 10 to 15 pages it touched.
- Carrying state between calls can matter a lot (37 points in one reported benchmark), so measure your memory layer by running the same model with and without it.

## Open questions
- What do roanjain's posts 2/7 to 7/7 say about questions, thresholds and latency?
- Does compile-at-ingest beat retrieval on any measured task?

---
