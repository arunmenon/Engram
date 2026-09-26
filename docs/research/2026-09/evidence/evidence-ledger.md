# Evidence ledger

Every evidence bullet from the Self-Improving Agents hub (`reports/trends.md`, as of 2026-09-26), with the full X context behind it: the complete post text (long posts included), same-author thread, quoted or replied-to posts, expanded links, and attached images. Source write-ups for the linked papers, repos and pages are in `sources/`.

## T1. Decision models as the memory control plane

- **Scale / status:** micro / building; first seen 2026-09-23
- **Thesis:** Memory builders are moving memory-pipeline decisions (whether to recall, what to extract, how to rank, when to stop) off the LLM and onto a fast calibrated decision model such as Jev.
- **Watch:** Do independent reproductions confirm Jev-Mem's LoCoMo +11% and 6.6× build speedup? Does a major memory vendor (Letta, Mem0, Zep) ship a decision-model gate on writes, not only on reranking?

### T1.E1 (2026-09-23, @LFrefman): Jev-Mem described as a System-One controller organizing typed, multi-relational memories and running routing and budgeting

**Evidence post:** [@LFrefman](https://x.com/LFrefman/status/2102909921553727522) (Git_Shark), 2026-09-23 23:56 UTC. Likes 2, reposts 0, replies 0, views 64.

> Tired of agent memory adding slow, expensive LLM generation to every lookup? Meet Jev-Mem's System-One-controlled memory.
>
> Jev-Mem splits cognition in two: a fast lightweight System-One controller organizes typed, multi-relational memories and runs routing, budgeting, graph traversal, scoring and stopping, saving the heavy System-Two LLM for complex reasoning and synthesis.
>
> 1️⃣ Hits 0.777 LLM-as-a-Judge score on LoCoMo, 11.0% above the strongest baseline.
> 2️⃣ Builds memory in just 158s, a 6.6x speedup over the fastest competing system.
> 3️⃣ Answers queries in 0.93s on average, cutting latency by 36.7%.
> 4️⃣ Keeps expensive generation off the critical path by routing retrieval with fast control.
>
> Bottom line: faster, cheaper, better memory for long-horizon agents.
>
> https://t.co/a9RKXkd0rR

- Link: https://signalhigh.centritude.com/post/jev-mem-system-one-controlled-agentic-memory-for-efficient-a-47

### T1.E2 (2026-09-24, @runbywren): Jev-Mem (arXiv 2609.23986): LoCoMo LLM-judge 0.777 (+11%), memory build 158 s (6.6× faster than the fastest competitor)

**Evidence post:** [@runbywren](https://x.com/runbywren/status/2103007852239434126) (Wren), 2026-09-24 06:25 UTC. Likes 1, reposts 0, replies 1, views 34.

> Jev-Mem (arXiv 2609.23986): System-One control plane for agent memory — typing, routing, scoring, stopping — so the LLM is not on every memory op.
>
> LoCoMo LLM-as-a-Judge 0.777 (+11% vs best baseline). Memory build 158s (6.6× faster than fastest competing system). Query latency 0.93s (−36.7%).
>
> https://t.co/2Lm3GI453C

- Link: https://arxiv.org/abs/2609.23986

### T1.E3 (2026-09-24, @Vectorizeio): Vectorize ships Jev reranking inside the Hindsight memory service

**Evidence post:** [@Vectorizeio](https://x.com/Vectorizeio/status/2103230262607761659) (Vectorize), 2026-09-24 21:09 UTC. Likes 11, reposts 1, replies 4, views 890.

> Hindsight now includes @typesafeai Jev reranking capabilities! https://t.co/kFuue1i94z

- Link: https://x.com/i/article/2103228685444587520

### T1.E4 (2026-09-24, @typesafeai): LangChain's Vtrivedy10 trusts Jev's semantic match over dot-product similarity for RAG; uses it as the metric on small corpora and as a reranker on large ones

**Evidence post:** [@typesafeai](https://x.com/typesafeai/status/2103165951781032167) (TypeSafe AI), 2026-09-24 16:53 UTC. Likes 925, reposts 44, replies 32, views 100160.

> Keep cooking, most best practices with Jev have yet to be discovered! https://t.co/YR9UcneWdz

- Link: https://twitter.com/vtrivedy10/status/2102808794493321714

  Linked post by @Vtrivedy10:

  > Jev for RAG 
  > 
  > in almost all cases you trust the semantic matching capability of Jev more than dot product similarity
  > 
  > very useful as the direct similarity metric in small data cases
  > 
  > and a great reranker with big data https://t.co/7tMQE5sv26


**Quoted post:** [@Vtrivedy10](https://x.com/Vtrivedy10/status/2102808794493321714) (Viv), 2026-09-23 17:14 UTC. Likes 739, reposts 52, replies 36, views 125687.

> Jev for RAG 
>
> in almost all cases you trust the semantic matching capability of Jev more than dot product similarity
>
> very useful as the direct similarity metric in small data cases
>
> and a great reranker with big data https://t.co/7tMQE5sv26


### T1.E5 (2026-09-25, @Muskanjain0401): Supermemory tests Jev across reranking, chunking, pre-extraction filtering and the recall/no-recall gate; reports up to 58% token reduction

**Evidence post:** [@Muskanjain0401](https://x.com/Muskanjain0401/status/2103449596819316742) (Muskan Jain), 2026-09-25 11:40 UTC. Likes 22, reposts 3, replies 3, views 1879.

> banger research just dropped!!🫪
>
> @DhravyaShah tested jev, @typesafeai's new decision model, across the whole memory pipeline: reranking, chunking, filtering context before extraction, and deciding when an agent should recall at all.
>
> did you know jev can cut 58% of the tokens going into memory extraction, but dropping one line like "how about indian food?" can turn "i love that stuff" into a memory about mexican food? decision models are insanely fast at yes/no calls and still need the full context to judge meaning.
>
> that's why @supermemory leans on learner-1, a small specialized model that makes observation cheap enough to skip the risky cut entirely :)

- Image: `media/2103449596819316742-3_2103449254731894784.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Quoted post:** [@DhravyaShah](https://x.com/DhravyaShah/status/2103314339239428201) (Dhravya Shah), 2026-09-25 02:43 UTC. Likes 400, reposts 25, replies 27, views 71155.

> https://t.co/62lLXqT276

- Link: https://x.com/i/article/2103277270773506048

### T1.E6 (2026-09-25, @bijitghosh21): Builder writeup puts one Jev decision layer across routing, memory, retrieval, tool execution and loop control in an agent harness

**Evidence post:** [@bijitghosh21](https://x.com/bijitghosh21/status/2103501070471500056) (Bijit Ghosh), 2026-09-25 15:05 UTC. Likes 1, reposts 0, replies 2, views 38.

> I’m going deep on how I built an agentic harness with Jev
> where the decision layer sits across routing, memory, retrieval, tool execution, and loop control, and how it changes orchestration. Step by step architecture, code, diagrams, and tradeoffs.
>
> https://t.co/XZx745z6yu

- Link: https://medium.com/@bijit211987/building-custom-agent-harness-with-jev-59a240bfc663 (Building Custom Agent Harness with Jev)

### T1.E7 (2026-09-25, @ethanwalkerman): Beacon (open source) uses Jev as a write gate: it scores every agent session, keeps what is reusable, drops the rest and builds a shared history across harnesses; no metrics given

**Evidence post:** [@ethanwalkerman](https://x.com/ethanwalkerman/status/2103510338889298174) (Ethan Walkrman), 2026-09-25 15:42 UTC. Likes 0, reposts 0, replies 1, views 38.

> Like to see more real usecase of Jev in production.
>
> Intelligence without memory is just a very expensive intern.
>
> Beacon (open source) use Jev to score all agent sessions, keep what's reusable, drop the rest, and continuously build a shared history across your agent harnesses. https://t.co/8pwB3gdZAL

- Link: https://twitter.com/akshay_pachaar/status/2102795260296593567

  Linked post by @akshay_pachaar:

  > Another insane Jev use case!
  > 
  > Jev makes it incredibly cheap to evaluate and classify agent runs at scale.
  > 
  > And finally, someone open-sourced a self-improving memory layer that can put that capability to work across agent harnesses.
  > 
  > It turns your agent sessions into a compounding knowledge layer, where every successful run can make future agents smarter across:
  > 
  > - Codex
  > - Claude Code
  > - Cursor
  > - OpenCode and 20+ more
  > 
  > Beacon by @asymptotelabs continuously builds a shared history across your agent harnesses and uses Jev to identify the runs worth learning from.
  > 
  > It then turns the best workflows, corrections, and debugging patterns into reusable skills.
  > 
  > GitHub repo: https://t.co/sfdu9P1bfx.
  > 
  > (don’t forget to star it ⭐)
  > 
  > Most agent runs are messy.
  > 
  > They contain exploration, failed commands, dead ends, and one-off fixes that should never become permanent memory.
  > 
  > So Beacon preserves the full session history, while Jev helps decide what should be promoted, reviewed, or discarded.
  > 
  > The recording below shows this in action.
  > 
  > Beacon found 579 sessions across 5 coding-agent harnesses and normalized them into one consistent history.
  > 
  > From there, Jev surfaces the lessons worth keeping and makes them available across your agent stack.
  > 
  > - A pattern learned in Cursor can carry into OpenCode.
  > - A lesson from Claude Code can improve the next Codex run.
  > 
  > Every successful run adds to the shared knowledge layer, making future agents smarter.
  > 
  > If you want to dive deeper into Jev, I also wrote a breakdown of how it works.
  > 
  > The article is quoted below.


**Quoted post:** [@akshay_pachaar](https://x.com/akshay_pachaar/status/2102795260296593567) (Akshay 🚀), 2026-09-23 16:20 UTC. Likes 904, reposts 115, replies 52, views 114738.

> Another insane Jev use case!
>
> Jev makes it incredibly cheap to evaluate and classify agent runs at scale.
>
> And finally, someone open-sourced a self-improving memory layer that can put that capability to work across agent harnesses.
>
> It turns your agent sessions into a compounding knowledge layer, where every successful run can make future agents smarter across:
>
> - Codex
> - Claude Code
> - Cursor
> - OpenCode and 20+ more
>
> Beacon by @asymptotelabs continuously builds a shared history across your agent harnesses and uses Jev to identify the runs worth learning from.
>
> It then turns the best workflows, corrections, and debugging patterns into reusable skills.
>
> GitHub repo: https://t.co/sfdu9P1bfx.
>
> (don’t forget to star it ⭐)
>
> Most agent runs are messy.
>
> They contain exploration, failed commands, dead ends, and one-off fixes that should never become permanent memory.
>
> So Beacon preserves the full session history, while Jev helps decide what should be promoted, reviewed, or discarded.
>
> The recording below shows this in action.
>
> Beacon found 579 sessions across 5 coding-agent harnesses and normalized them into one consistent history.
>
> From there, Jev surfaces the lessons worth keeping and makes them available across your agent stack.
>
> - A pattern learned in Cursor can carry into OpenCode.
> - A lesson from Claude Code can improve the next Codex run.
>
> Every successful run adds to the shared knowledge layer, making future agents smarter.
>
> If you want to dive deeper into Jev, I also wrote a breakdown of how it works.
>
> The article is quoted below.

- Link: http://github.com/Asymptote-Labs/agent-beacon

### T1.E8 (2026-09-25, @jreuben1): Jevmem ships automatic project memory for Claude Code built on Jev; no details yet

**Evidence post:** [@jreuben1](https://x.com/jreuben1/status/2103553740938625030) ((((JReuben1)))), 2026-09-25 18:34 UTC. Likes 1, reposts 0, replies 1, views 88.

> Jevmem – automatic project memory for Claude Code, built on Jev https://t.co/GPf32yhGF9

- Link: https://github.com/Avinash-jetwani/jevmem (GitHub - Avinash-jetwani/jevmem: Automatic project memory for Claude Code. Also works with Cursor and Codex.)

## T2. Typed-decision tier displacing LLM calls on bounded classification

- **Scale / status:** micro / building; first seen 2026-09-21
- **Thesis:** For closed-label decisions (classification, matching, escalation), teams report replacing frontier-LLM calls with a typed decision model at equal or higher accuracy and one to two orders of magnitude lower cost; in open-ended agent loops the standalone fast tier has failed, and the only positive report pairs it with a generative planner.
- **Watch:** Does any team report a Jev-style fast tier surviving inside an open-ended agent loop (coding, browsing), rather than on fixed taxonomies? Do rate limits and the signup pause cap adoption?

### T2.E1 (2026-09-21, @typesafeai): MotherDuck `prompt_jev()`: 100k rows in 40 s for $0.50 vs 32 min and $37 with an LLM, at frontier-LLM accuracy

**Evidence post:** [@typesafeai](https://x.com/typesafeai/status/2102206611024716181) (TypeSafe AI), 2026-09-22 01:21 UTC. Likes 858, reposts 40, replies 24, views 116000.

> Jev makes it easy to add natural language intelligence into the key parts of any application at scale, far cheaper and faster than has ever been possible.
>
> 50x faster.
> 100x cheaper.
> Reliable as duck. https://t.co/tY5PwtzlIn

- Link: https://twitter.com/motherduck/status/2102077291081896307

  Linked post by @motherduck:

  > Text classification in MotherDuck just got ~50x faster at ~1% of the cost.
  > 
  > prompt_jev() is a SQL function powered by Jev, TypeSafe's new system one model. 100k rows: 40s, $0.50, frontier-LLM accuracy. The LLM took 32 min and $37.
  > 
  > Read on:
  > 
  > https://t.co/XIE2cw6rUS https://t.co/CdP1q8OwDe


**Quoted post:** [@motherduck](https://x.com/motherduck/status/2102077291081896307) (MotherDuck), 2026-09-21 16:47 UTC. Likes 513, reposts 44, replies 13, views 207790.

> Text classification in MotherDuck just got ~50x faster at ~1% of the cost.
>
> prompt_jev() is a SQL function powered by Jev, TypeSafe's new system one model. 100k rows: 40s, $0.50, frontier-LLM accuracy. The LLM took 32 min and $37.
>
> Read on:
>
> https://t.co/XIE2cw6rUS https://t.co/CdP1q8OwDe

- Link: https://motherduck.com/blog/motherduck-supports-jev/ (Introducing prompt_jev(): bringing Jev to Motherduck SQL - MotherDuck Blog)

<details><summary>Same-author thread (1 more posts)</summary>

**Thread post:** [@typesafeai](https://x.com/typesafeai/status/2102262340104356243) (TypeSafe AI), 2026-09-22 05:02 UTC. Likes 6, reposts 0, replies 2, views 1741.

> @PawelJLisowski The cost of intelligence is too damn high! We’ve only scratched the surface on what we can optimize.


</details>

### T2.E2 (2026-09-24, @typesafeai): JevSearch: Jev rescores the top 25 web results and often promotes URLs from outside the original top 5

**Evidence post:** [@typesafeai](https://x.com/typesafeai/status/2103218258405118035) (TypeSafe AI), 2026-09-24 20:21 UTC. Likes 298, reposts 14, replies 13, views 74155.

> Relevance is great, but relevance to what? Jev gives you search intelligence that no canned SEO can 🪱 its way into. https://t.co/6RwRen3I05

- Link: https://twitter.com/kylejeong/status/2102561749404971460

  Linked post by @kylejeong:

  > I built JevSearch, search the web &amp; validate your results with Jev.
  > 
  > Give a query and selection criteria, use @browserbase search to get the t25 results, then Jev scores and returns the t5 results.
  > 
  > Jev often chooses urls outside of the initial top 5 as more relevant. https://t.co/jT3sM3vWYl https://t.co/NRc4KLyD0v


**Quoted post:** [@kylejeong](https://x.com/kylejeong/status/2102561749404971460) (Kyle Jeong), 2026-09-23 00:52 UTC. Likes 100, reposts 7, replies 14, views 54359.

> I built JevSearch, search the web &amp; validate your results with Jev.
>
> Give a query and selection criteria, use @browserbase search to get the t25 results, then Jev scores and returns the t5 results.
>
> Jev often chooses urls outside of the initial top 5 as more relevant. https://t.co/jT3sM3vWYl https://t.co/NRc4KLyD0v

- Link: https://twitter.com/kylejeong/status/2102108924677927169

  Linked post by @kylejeong:

  > https://t.co/MAj6LuRCZ3


### T2.E3 (2026-09-25, @typesafeai): Deel: repeat-question matching 70→97%, expense categorization 50→86%, up to 4× faster on shadowed live traffic

**Evidence post:** [@typesafeai](https://x.com/typesafeai/status/2103321894661595551) (TypeSafe AI), 2026-09-25 03:13 UTC. Likes 13, reposts 0, replies 3, views 5121.

> Jev generally out-performed frontier LLMs at a fraction of the price:
> Repeat-question matching: 70% → 97%
> Expense categorization: 50% → 86% (vs human reviewers)
> Escalation: same catches, fewer false alarms https://t.co/tBg4CIigz0

- Image: `media/2103321894661595551-3_2103318813655838720.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Replied to post:** [@typesafeai](https://x.com/typesafeai/status/2103321892421865838) (TypeSafe AI), 2026-09-25 03:13 UTC. Likes 13, reposts 0, replies 2, views 6647.

> Some great use cases they measured:
> • Matching repeat analytics questions to approved answers
> • Picking 1 of 36 metrics
> • Blocking PII requests
> • Deciding when a support chat needs a human
> • Tagging tickets across a 3-level taxonomy
> • Sorting expenses into about 55 categories
> Every one is a pick from a known set.

- Image: `media/2103321892421865838-3_2103318729505566720.jpg` (photo); transcribed in `sources/images-transcribed.md`

<details><summary>Same-author thread (3 more posts)</summary>

**Thread post:** [@typesafeai](https://x.com/typesafeai/status/2103321890190491710) (TypeSafe AI), 2026-09-25 03:13 UTC. Likes 85, reposts 8, replies 18, views 46651.

> Observe the art of the @deel.
> And they came with receipts 💅 
> Keep reading to find out how it's done. https://t.co/mW7FxGvCbI

- Image: `media/2103321890190491710-3_2103318655237017600.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Thread post:** [@typesafeai](https://x.com/typesafeai/status/2103321892421865838) (TypeSafe AI), 2026-09-25 03:13 UTC. Likes 13, reposts 0, replies 2, views 6647.

> Some great use cases they measured:
> • Matching repeat analytics questions to approved answers
> • Picking 1 of 36 metrics
> • Blocking PII requests
> • Deciding when a support chat needs a human
> • Tagging tickets across a 3-level taxonomy
> • Sorting expenses into about 55 categories
> Every one is a pick from a known set.

- Image: `media/2103321892421865838-3_2103318729505566720.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Thread post:** [@typesafeai](https://x.com/typesafeai/status/2103321896553210029) (TypeSafe AI), 2026-09-25 03:13 UTC. Likes 5, reposts 0, replies 0, views 3826.

> Speed was measured while shadowing live production traffic: up to 4× faster. Offline tests: 2 to 3×. https://t.co/SmlSLmW4rl

- Image: `media/2103321896553210029-3_2103318942781698048.jpg` (photo); transcribed in `sources/images-transcribed.md`

</details>

### T2.E4 (2026-09-25, @tazr_dev): Counter-evidence: 6 Jev-style fast actions tested in a coding agent and none survived; the decision was "too unreliable"

**Evidence post:** [@tazr_dev](https://x.com/tazr_dev/status/2103490167248212384) (Trent Zock-Robbins), 2026-09-25 14:21 UTC. Likes 3, reposts 0, replies 3, views 199.

> I tested 6 Jev-style fast actions in tack coding agent yesterday.  None survived.
>
> I'm going to survey what's out there before taking another pass.
>
> Biggest blocker is d/jev is too unreliable, and the next step up is the actual agent. https://t.co/Kfm8QglCTX https://t.co/9kRapfIuB7

- Link: https://twitter.com/tazr_dev/status/2103318291456610667

  Linked post by @tazr_dev:

  > And now I present to you:
  > 
  > A "beautiful rendition" of world of warcraft in three.js by Qwen 3.8 27b... (having removed the conical trees)
  > 
  > While using a custom vibe coded harness and, pointlessly, djev. https://t.co/m0qzeNhMqF

- Image: `media/2103490167248212384-3_2103489775915376641.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Quoted post:** [@tazr_dev](https://x.com/tazr_dev/status/2103318291456610667) (Trent Zock-Robbins), 2026-09-25 02:58 UTC. Likes 10, reposts 1, replies 4, views 675.

> And now I present to you:
>
> A "beautiful rendition" of world of warcraft in three.js by Qwen 3.8 27b... (having removed the conical trees)
>
> While using a custom vibe coded harness and, pointlessly, djev. https://t.co/m0qzeNhMqF


<details><summary>Same-author thread (3 more posts)</summary>

**Thread post:** [@tazr_dev](https://x.com/tazr_dev/status/2103492454205022460) (Trent Zock-Robbins), 2026-09-25 14:30 UTC. Likes 0, reposts 0, replies 0, views 9.

> I hope to find a fit for INTENT, MET, and REFLEX. I'm running tack agent as my doom oracle now.


**Thread post:** [@tazr_dev](https://x.com/tazr_dev/status/2103492581103702114) (Trent Zock-Robbins), 2026-09-25 14:31 UTC. Likes 0, reposts 0, replies 0, views 7.

> REPLAN still looks good to me, but I need to have a better contract for it.


**Thread post:** [@tazr_dev](https://x.com/tazr_dev/status/2103493235268268230) (Trent Zock-Robbins), 2026-09-25 14:34 UTC. Likes 0, reposts 0, replies 0, views 5.

> GATE and SUFF need more data as well. I wish I got a win here.
>
> Time to improve my testing methods and find another angle.


</details>

### T2.E5 (2026-09-25, @rbro112): One week of Jev replacing Gemini 3.1 as a pass/fail eval judge: no meaningful accuracy change, ~200× cheaper ($0.01→$0.00005), ~50× faster (10 s→0.2 s median); cost is the judge's lost written reasoning

**Evidence post:** [@rbro112](https://x.com/rbro112/status/2103501576405172326) (Ryan Brooks), 2026-09-25 15:07 UTC. Likes 39, reposts 4, replies 9, views 5351.

> It’s been a week since I moved one of eval datasets from Gemini 3.1 to Jev by @typesafeai for LLM judging. The results so far:
>
> - No meaningful change in scoring accuracy
> - ~200× cheaper (~$0.01 → ~$0.00005 per judge)
> - ~50× faster (~10s → ~0.2s median)
> - ~50% fewer input tokens, 87% fewer output tokens
>
> But not everything’s perfect, more details in the thread


**Quoted post:** [@rbro112](https://x.com/rbro112/status/2101029904578158781) (Ryan Brooks), 2026-09-18 19:25 UTC. Likes 10, reposts 0, replies 1, views 5589.

> 👀👀 https://t.co/rtx7Vcu5Zc


### T2.E6 (2026-09-25, @kaixin_tai): Datadog agent observability runs online and offline evals with Jev as the judge

**Evidence post:** [@kaixin_tai](https://x.com/kaixin_tai/status/2103500863243460898) (Kai Xin Tai), 2026-09-25 15:04 UTC. Likes 9, reposts 0, replies 4, views 181.

> run cheap and fast online and offline evals with jev in datadog agent observability https://t.co/Q9qUx4mMRV

- Image: `media/2103500863243460898-3_2103500857094688769.jpg` (photo); transcribed in `sources/images-transcribed.md`

<details><summary>Same-author thread (1 more posts)</summary>

**Thread post:** [@kaixin_tai](https://x.com/kaixin_tai/status/2103500945305018737) (Kai Xin Tai), 2026-09-25 15:04 UTC. Likes 0, reposts 0, replies 0, views 37.

> read more here: https://t.co/jwLiMEzawK

- Link: https://www.datadoghq.com/blog/jev-evals-agent-observability (Using TypeSafe’s Jev for evals in Datadog Agent Observability | Datadog)

</details>

### T2.E7 (2026-09-25, @hamzaashergill): A second team independently reports that judge latency (10 s vs 0.2 s) decides whether evals run sparingly or become a gate on every PR

**Evidence post:** [@hamzaashergill](https://x.com/hamzaashergill/status/2103508434863657236) (Hamzaa Shergill), 2026-09-25 15:34 UTC. Likes 0, reposts 0, replies 0, views 1.

> @rbro112 @typesafeai The 50x faster number is the one that changes behavior, not just cost. When judging takes 10 seconds, you run it sparingly; at 0.2 seconds it becomes a gate on every PR. We found the same in our evals: the judge's speed determines whether the team actually uses it.


**Replied to post:** [@rbro112](https://x.com/rbro112/status/2103501576405172326) (Ryan Brooks), 2026-09-25 15:07 UTC. Likes 39, reposts 4, replies 9, views 5351.

> It’s been a week since I moved one of eval datasets from Gemini 3.1 to Jev by @typesafeai for LLM judging. The results so far:
>
> - No meaningful change in scoring accuracy
> - ~200× cheaper (~$0.01 → ~$0.00005 per judge)
> - ~50× faster (~10s → ~0.2s median)
> - ~50% fewer input tokens, 87% fewer output tokens
>
> But not everything’s perfect, more details in the thread


<details><summary>Same-author thread (1 more posts)</summary>

**Thread post:** [@rbro112](https://x.com/rbro112/status/2103501576405172326) (Ryan Brooks), 2026-09-25 15:07 UTC. Likes 39, reposts 4, replies 9, views 5351.

> It’s been a week since I moved one of eval datasets from Gemini 3.1 to Jev by @typesafeai for LLM judging. The results so far:
>
> - No meaningful change in scoring accuracy
> - ~200× cheaper (~$0.01 → ~$0.00005 per judge)
> - ~50× faster (~10s → ~0.2s median)
> - ~50% fewer input tokens, 87% fewer output tokens
>
> But not everything’s perfect, more details in the thread


</details>

### T2.E8 (2026-09-25, @metalagman): LintPal uses Jev to check committed diffs against Markdown rules in the repo, with deterministic severity gates

**Evidence post:** [@metalagman](https://x.com/metalagman/status/2103507889189159091) (Alexey Samoylov), 2026-09-25 15:32 UTC. Likes 2, reposts 0, replies 0, views 29.

> Engineering rules belong in code review, not forgotten in a wiki.
>
> LintPal evaluates committed Git diffs against Markdown rules stored directly in your repository, powered by @typesafeai Jev.
>
> Deterministic severity gates, inline PR comments with rule requirements, and structured review tables.
>
> https://t.co/ybGfjk6MZl

- Link: https://github.com/diffpal/lintpal

### T2.E9 (2026-09-25, @mika_systems): Jev + GPT-6 Astra planner won 9/10 StarCraft II games vs the hardest built-in AI; Jev alone won 0/10 (5 setups, 50 matches)

**Evidence post:** [@mika_systems](https://x.com/mika_systems/status/2103554329139417547) (Mika), 2026-09-25 18:36 UTC. Likes 49, reposts 7, replies 9, views 3366.

> Jev + GPT-6 Astra just won 9 out of 10 StarCraft II games
>
> Astra made the plan. Jev picked the next move while the game kept running
>
> The team tested five setups across 50 matches against the game's toughest built-in opponent without cheats:
>
> > Jev alone → 0/10 wins
> > Astra's plan + random moves → 0/10
> > Astra's plan + Jev's moves → 9/10
>
> A good plan wasn't enough. The moves had to keep up with it
>
> Across the tests, Jev returned 19,605 decisions and Astra replied 509 times. In the 9/10 setup, Jev's median response took 0.375 seconds
>
> In a separate test of 210 smaller battles, Jev alone eliminated 16.50% of enemy forces on average. Jev + Astra reached 37.69% - about 2.3x as much
>
> In an earlier set of four wins, estimated model usage averaged $3.71 per game: $0.15 for Jev and $3.56 for Astra
>
> The loop is simple:
>
> > Astra plans ahead
> > Jev picks an available move
> > the game plays it
> > both get the new state
>
> Those 9 wins came from the whole setup: the plan, the available moves and the fast choices between them
>
> take this out of StarCraft. Jev guide shows how to give it the same job in your own agent ↓

- Link: https://twitter.com/mika_systems/status/2101686148338798610

  Linked post by @mika_systems:

  > https://t.co/EvoaFa63Cd

- Image: `media/2103554329139417547-13_2103551832333099008.jpg` (video); transcribed in `sources/images-transcribed.md`

**Quoted post:** [@mika_systems](https://x.com/mika_systems/status/2101686148338798610) (Mika), 2026-09-20 14:53 UTC. Likes 109, reposts 11, replies 13, views 180875.

> https://t.co/EvoaFa63Cd

- Link: https://x.com/i/article/2101639552796348418

### T2.E10 (2026-09-25, @MegadoseNews): Parcha-ai's agentrun DSL proceeds on agent calls only at Jev confidence ≥ 0.8 and escalates the rest to review

**Evidence post:** [@MegadoseNews](https://x.com/MegadoseNews/status/2103555346275115269) (Megadose), 2026-09-25 18:40 UTC. Likes 0, reposts 0, replies 0, views 4.

> Uncut #23: Parcha-ai/agentrun. Workflow DSL that gates agent calls behind Jev decisions (confidence ≥0.8) with review escalation. 44 on HN.
>
> @miguelriosEN
> https://t.co/MZ3JTCZDlU

- Link: https://megadose.ai/uncut?h=3159&utm_source=x&utm_medium=social&utm_campaign=megadosenews (A DSL project)

### T2.E11 (2026-09-25, @roanjain): Voice-agent pipeline puts Jev between ASR and the main LLM, replacing a separate intent parser

**Evidence post:** [@roanjain](https://x.com/roanjain/status/2103554942611189795) (Rohan Jain), 2026-09-25 18:39 UTC. Likes 0, reposts 0, replies 1, views 10.

> 1/7
> Start with the simplest flow:
> Caller → ASR → Jev → application policy → main LLM/tool → voice response
> Here, Jev runs after speech is transcribed but before the agent takes its next action.


**Replied to post:** [@roanjain](https://x.com/roanjain/status/2103554471121031293) (Rohan Jain), 2026-09-25 18:37 UTC. Likes 0, reposts 0, replies 1, views 9.

> Someone asked the best question after Part 1 of 5 Part series:
>
> Where exactly does Jev sit in a Voice AI turn, before tool selection or after intent is parsed?
> There’s no universal answer. Here’s the architecture I would use.
> Part 3/5 🧵


<details><summary>Same-author thread (1 more posts)</summary>

**Thread post:** [@roanjain](https://x.com/roanjain/status/2103554471121031293) (Rohan Jain), 2026-09-25 18:37 UTC. Likes 0, reposts 0, replies 1, views 9.

> Someone asked the best question after Part 1 of 5 Part series:
>
> Where exactly does Jev sit in a Voice AI turn, before tool selection or after intent is parsed?
> There’s no universal answer. Here’s the architecture I would use.
> Part 3/5 🧵


</details>

## T3. Memory that updates on read

- **Scale / status:** micro / emerging; first seen 2026-09-24
- **Thesis:** Several memory systems now treat retrieval as a write event, strengthening, decaying or reweighting memories according to use, instead of updating only when new information arrives.
- **Watch:** Does read-time updating beat static stores on LongMemEval knowledge-update and abstention subsets specifically? Do we see failure reports of feedback loops, where frequently recalled but wrong memories get reinforced?

### T3.E1 (2026-09-24, @sergeonsamui): Hippo-memory: decay, retrieval strengthening and consolidation; LongMemEval R@5 = 74% with BM25 only

**Evidence post:** [@sergeonsamui](https://x.com/sergeonsamui/status/2103046874496172478) (Serge in Boca), 2026-09-24 09:00 UTC. Likes 2, reposts 0, replies 0, views 29.

> Hippo-memory: biologically-inspired memory layer for AI agents with decay, retrieval strengthening, and consolidation. TypeScript, SQLite, zero runtime deps, MCP support for @claudeai Code and @cursor_ai. Hits R@5 = 74% on LongMemEval with just BM25.
>
> https://t.co/5T0LVkDffx https://t.co/m1KRZFYa7J

- Link: https://github.com/kitfunso/hippo-memory (GitHub - kitfunso/hippo-memory: Biologically-inspired memory for AI agents. Decay, retrieval strengthening, consolidation. Zero runtime deps, SQLite, MCP. Benchmarked retrieval with an opt-in TypeSafe Jev reranker.)
- Image: `media/2103046874496172478-3_2103046868192075776.jpg` (photo); transcribed in `sources/images-transcribed.md`

### T3.E2 (2026-09-24, @yog_codes): REALM (SJTU + OPPO) reconsolidates the activated subgraph after retrieval; LoCoMo 75.97 (+7 pts)

**Evidence post:** [@yog_codes](https://x.com/yog_codes/status/2103013866535809492) (Yogesh), 2026-09-24 06:49 UTC. Likes 1, reposts 0, replies 0, views 37.

> realm (sjtu + oppo)
>
> most agent memory updates on new info. retrieval is just the end.
>
> their take: after you retrieve, reconsolidate. tweak edges on the activated subgraph based on what actually helped.
>
> locomo 75.97 (+7 pts vs best baseline)
>
> https://t.co/KBfM9w6AL6

- Link: https://arxiv.org/abs/2609.16053 (Retrieval-Driven Memory Reconsolidation for Long-Term LLM Agents)

### T3.E3 (2026-09-25, @cai_smart): Hindsight is positioned on the claim that "recall isn't the same as learning", with retain / recall / reflect as its core operations

**Evidence post:** [@cai_smart](https://x.com/cai_smart/status/2103333989134274966) (SmartCai), 2026-09-25 04:01 UTC. Likes 5, reposts 1, replies 4, views 433.

> Most agent memory systems are a conversation log with a search box bolted on. This one is built around the claim that recall isn't the same as learning.
>
> Recommendation: ★★★★☆
> Difficulty: Intermediate
>
> Hindsight is a Python memory service you run yourself: a server that exposes three operations over HTTP, plus clients for Python, Node, Go and a CLI. Retain stores content in a named bank, recall searches it, reflect generates an answer shaped by what the bank has accumulated. On top of that sit concepts the README calls observations, mental models and knowledge pages, which is where the learning-over-time argument lives rather than in plain vector similarity.
>
> Getting it up is one docker run against https://t.co/FOahPbFt4W with HINDSIGHT_API_LLM_API_KEY set, mapping 8888 for the API and 9999 for a UI. There's also pip install hindsight-api for bare metal, a Helm chart, a docker-compose path for external PostgreSQL, and an embedded mode via pip install hindsight-all that starts a server in-process with no container at all. Providers cover the usual hosted APIs plus ollama, lmstudio and llamacpp, and existing Claude Code or Codex subscriptions can be used without a separate key.
>
> The caveats are worth reading carefully. The state-of-the-art LongMemEval claim is the project's own, and the README itself notes that competing scores are vendor self-reported. It's MIT licensed but built by a company that sells a managed version, so expect the hosted path to be the smooth one. It's also young and pre-1.0, with a sizable open issue count, so treat the storage format as something that may move under you.
>
> If you're currently shipping a homegrown summarize-and-embed layer behind your agent, this is a serious alternative. Just benchmark it on your own data before believing the leaderboard.
>
> Why Intermediate: You run a server, supply an LLM provider key and pick a storage path before any of the client SDKs do anything useful.
>
> Adoption
> 27k stars, 2.5k forks, MIT license
> 246 contributors, latest release v0.10.1 (Sep 2026), commits this week
>
> https://t.co/gPJR2r0l6a

- Link: http://ghcr.io/vectorize-io/hindsight:latest
- Link: https://github.com/vectorize-io/hindsight

## T4. Consolidation as a separate phase from ingestion

- **Scale / status:** micro / emerging; first seen 2026-09-23
- **Thesis:** Memory systems are separating fast ingestion/indexing from a later consolidation pass that distills durable memories, and they disagree on whether that pass runs on a fixed schedule or is triggered adaptively.
- **Watch:** Does any system publish before/after numbers (LongMemEval or LoCoMo, token cost) with consolidation on vs off? Does adaptive triggering beat cron on quality, or only on infrastructure load?

### T4.E1 (2026-09-23, @rauchg): Rauch's Brain / Hands / Files layout runs memory consolidation as a cron job without booting the agent runtime

**Evidence post:** [@rauchg](https://x.com/rauchg/status/2102820148629614685) (Guillermo Rauch), 2026-09-23 17:59 UTC. Likes 2249, reposts 134, replies 197, views 255702.

> Muse, Instinct, OpenClaw, Claude Code…
> All successful agents have 3 key components:
>
> 🧠 Brain → model, harness (logic)
> 👐 Hands → tools, computer, browser
> 🗃️ Files → memories, skills, repos
>
> The 'easy' way is to throw all these in 1 stateful computer (a Mac Mini)
>
> Like, you run 𝚌𝚕𝚊𝚞𝚍𝚎 or 𝚏𝚡 in your mac, you keep it running all day with 𝚌𝚊𝚏𝚏𝚎𝚒𝚗𝚊𝚝𝚎, it has storage, and CLIs and apps installed.
>
> But if you want to cost-efficiently run agents in the cloud, you actually start breaking down these parts.
>
> 🧠 The harness can run in Fluid compute. To make it reliable across restarts, rollouts, crashes, you make its event log durable using Workflow.
>
> 👐 The hands can be a dedicated browser fleet like Browserbase/Kernel, a computer like Sandbox, and even more efficient lightweight tools like just-bash.
>
> 🗃️ 🆕 What was missing was a way to also decouple storage. Imagine you want to run a memory consolidation cron job every night ("dreaming"). You can read/write to the files directly without 'booting up' the agent's full computer.
>
> Today we're introducing the perfect companion to Sandbox: Drives. We shipped the computer for agents, now we're giving you the 'external disk' you can attach at will. It's early, and we'll be expanding capabilities here quickly.
>
> Btw, breaking apart the agent into these independent parts not only optimizes costs in a big way, it also *massively* improves security and auditability. I'd argue you can't even run a secure agent otherwise!

- Link: https://twitter.com/vercel_dev/status/2102791176378352115

  Linked post by @vercel_dev:

  > Vercel Sandbox now has persistent storage with Drives, in public beta on every plan.
  > 
  > ▪︎ Store agent workspaces, data, models, deps
  > ▪︎ Read snapshots across parallel sandboxes
  > ▪︎ Mount up to four Drives per sandbox
  > ▪︎ Up to 16 TiB per Drive
  > 
  > https://t.co/5sOGOiREOv


**Quoted post:** [@vercel_dev](https://x.com/vercel_dev/status/2102791176378352115) (Vercel Developers), 2026-09-23 16:04 UTC. Likes 363, reposts 27, replies 25, views 270443.

> Vercel Sandbox now has persistent storage with Drives, in public beta on every plan.
>
> ▪︎ Store agent workspaces, data, models, deps
> ▪︎ Read snapshots across parallel sandboxes
> ▪︎ Mount up to four Drives per sandbox
> ▪︎ Up to 16 TiB per Drive
>
> https://t.co/5sOGOiREOv

- Link: https://vercel.com/changelog/drives-for-vercel-sandbox-are-now-in-public-beta (Drives for Vercel Sandbox are now in public beta - Vercel)

<details><summary>Same-author thread (3 more posts)</summary>

**Thread post:** [@rauchg](https://x.com/rauchg/status/2102837377219834102) (Guillermo Rauch), 2026-09-23 19:07 UTC. Likes 2, reposts 0, replies 2, views 1492.

> @giuseppegurgone It's designed and architected that way, we'll be exposing that API very soon. @tomlienard


**Thread post:** [@rauchg](https://x.com/rauchg/status/2102863466327642328) (Guillermo Rauch), 2026-09-23 20:51 UTC. Likes 6, reposts 0, replies 1, views 1082.

> @shreypandya @pk_iv "I love hands, I have the best hands"


**Thread post:** [@rauchg](https://x.com/rauchg/status/2102890153098575991) (Guillermo Rauch), 2026-09-23 22:37 UTC. Likes 8, reposts 0, replies 4, views 1780.

> @SeeLos @cramforce Running a computer only when needed 
> &lt; (cheaper than)
> Running a computer all the time 
>
> Especially when you only pay for Active CPU cycles on that computer, as is the case with Fluid


</details>

### T4.E2 (2026-09-24, @sergeonsamui): Hippo-memory ships decay, retrieval strengthening and consolidation as separate operations in SQLite

**Evidence post:** [@sergeonsamui](https://x.com/sergeonsamui/status/2103046874496172478) (Serge in Boca), 2026-09-24 09:00 UTC. Likes 2, reposts 0, replies 0, views 29.

> Hippo-memory: biologically-inspired memory layer for AI agents with decay, retrieval strengthening, and consolidation. TypeScript, SQLite, zero runtime deps, MCP support for @claudeai Code and @cursor_ai. Hits R@5 = 74% on LongMemEval with just BM25.
>
> https://t.co/5T0LVkDffx https://t.co/m1KRZFYa7J

- Link: https://github.com/kitfunso/hippo-memory (GitHub - kitfunso/hippo-memory: Biologically-inspired memory for AI agents. Decay, retrieval strengthening, consolidation. Zero runtime deps, SQLite, MCP. Benchmarked retrieval with an opt-in TypeSafe Jev reranker.)
- Image: `media/2103046874496172478-3_2103046868192075776.jpg` (photo); transcribed in `sources/images-transcribed.md`

### T4.E3 (2026-09-25, @supermemory): Supermemory "dreams": indexing finishes first, then a second phase groups related documents and forms memories from coherent units

**Evidence post:** [@supermemory](https://x.com/supermemory/status/2103513608399532143) (supermemory), 2026-09-25 15:55 UTC. Likes 33, reposts 2, replies 2, views 7183.

> Usual memory systems learn the moment data flows in, then never look at it again.
>
> @supermemory 𝚍𝚛𝚎𝚊𝚖𝚜.
>
> Status done means the chunks are indexed. Memories come from a second phase, where related documents are grouped so memories form from coherent units, never one isolated write.
>
> When you go quiet, or enough new context has piled up, supermemory enters a dream cycle on its own. During a dream it:
>
> - merges fragments that belong together
> - reweights old facts against everything since
> - resolves contradictions
> - derives facts you never stated in one place, each traceable to its sources
>
> The output is new memories, a graph of derivations between them, and a picture of the user that updates as the evidence changes.
>
> If you use supermemory in any way, this already works. Dream away.

- Image: `media/2103513608399532143-13_2103485515614056448.jpg` (video); transcribed in `sources/images-transcribed.md`

### T4.E4 (2026-09-25, @DhravyaShah): Supermemory decides dynamically when to dream instead of running on cron, to avoid spiky infrastructure load

**Evidence post:** [@DhravyaShah](https://x.com/DhravyaShah/status/2103522483630739793) (Dhravya Shah), 2026-09-25 16:30 UTC. Likes 35, reposts 0, replies 4, views 5234.

> dreaming is super powerful 
>
> I don't think systems should do it on cron etc basis (lots of spiky traffic on infra). one interesting thing about supermemorys infrastructure is that dreaming is dynamic. 
>
> Supermemory automatically decides when is the right time to dream and learn https://t.co/Njx6tpiFvw

- Link: https://twitter.com/supermemory/status/2103513608399532143

  Linked post by @supermemory:

  > Usual memory systems learn the moment data flows in, then never look at it again.
  > 
  > @supermemory 𝚍𝚛𝚎𝚊𝚖𝚜.
  > 
  > Status done means the chunks are indexed. Memories come from a second phase, where related documents are grouped so memories form from coherent units, never one isolated write.
  > 
  > When you go quiet, or enough new context has piled up, supermemory enters a dream cycle on its own. During a dream it:
  > 
  > - merges fragments that belong together
  > - reweights old facts against everything since
  > - resolves contradictions
  > - derives facts you never stated in one place, each traceable to its sources
  > 
  > The output is new memories, a graph of derivations between them, and a picture of the user that updates as the evidence changes.
  > 
  > If you use supermemory in any way, this already works. Dream away.


**Quoted post:** [@supermemory](https://x.com/supermemory/status/2103513608399532143) (supermemory), 2026-09-25 15:55 UTC. Likes 33, reposts 2, replies 2, views 7183.

> Usual memory systems learn the moment data flows in, then never look at it again.
>
> @supermemory 𝚍𝚛𝚎𝚊𝚖𝚜.
>
> Status done means the chunks are indexed. Memories come from a second phase, where related documents are grouped so memories form from coherent units, never one isolated write.
>
> When you go quiet, or enough new context has piled up, supermemory enters a dream cycle on its own. During a dream it:
>
> - merges fragments that belong together
> - reweights old facts against everything since
> - resolves contradictions
> - derives facts you never stated in one place, each traceable to its sources
>
> The output is new memories, a graph of derivations between them, and a picture of the user that updates as the evidence changes.
>
> If you use supermemory in any way, this already works. Dream away.

- Image: `media/2103513608399532143-13_2103485515614056448.jpg` (video); transcribed in `sources/images-transcribed.md`

## T5. Staleness and provenance as the core memory-write problem

- **Scale / status:** micro / emerging; first seen 2026-09-23
- **Thesis:** Practitioners increasingly identify silent staleness and missing provenance, rather than recall capacity, as the main way agent memory fails, and they prescribe entries that carry a date, a reason and a source so the entries can be invalidated.
- **Watch:** Does a memory vendor ship per-entry provenance with targeted revocation? Does a benchmark or postmortem quantify how much stale-entry retrieval degrades task success over repeated sessions?

### T5.E1 (2026-09-23, @roscherveniak): Open question: how do you invalidate episodic memory when the underlying file or permission changes?

**Evidence post:** [@roscherveniak](https://x.com/roscherveniak/status/2102862264231751794) (Ros), 2026-09-23 20:46 UTC. Likes 0, reposts 0, replies 0, views 7.

> @virgilxbt The useful line here is separating what the agent sees now from what happened before. How do you invalidate episodic memory when the underlying file or permission changes?


**Replied to post:** [@virgilxbt](https://x.com/virgilxbt/status/2102850232249635116) (virgilxbt), 2026-09-23 19:58 UTC. Likes 196, reposts 19, replies 17, views 16659.

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

- Link: https://twitter.com/slash1sol/status/2098013767627837827

  Linked post by @slash1sol:

  > https://t.co/ZimneBAP1w


<details><summary>Same-author thread (1 more posts)</summary>

**Thread post:** [@virgilxbt](https://x.com/virgilxbt/status/2102850232249635116) (virgilxbt), 2026-09-23 19:58 UTC. Likes 196, reposts 19, replies 17, views 16659.

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

- Link: https://twitter.com/slash1sol/status/2098013767627837827

  Linked post by @slash1sol:

  > https://t.co/ZimneBAP1w


</details>

### T5.E2 (2026-09-25, @JeffWitters): Store decisions, not facts: a decision carries a date and a reason to check against, while facts go stale silently

**Evidence post:** [@JeffWitters](https://x.com/JeffWitters/status/2103546324373197212) (Jeff Witters), 2026-09-25 18:05 UTC. Likes 1, reposts 0, replies 2, views 22.

> Agent memory should store decisions, not facts. Facts go stale silently. A decision arrives with a date and a reason attached, so when it stops being true there is something to check it against.


### T5.E3 (2026-09-25, @chebyte): Without per-line provenance (tool result vs. earlier persona dump vs. user), revocation has nothing to aim at

**Evidence post:** [@chebyte](https://x.com/chebyte/status/2103554185551864286) (chebyte), 2026-09-25 18:36 UTC. Likes 0, reposts 0, replies 2, views 25.

> "Treat agent memory as untrusted" is the easy half.
>
> The miss is provenance. Which line came from a tool result, which from a prior persona dump, which from me.
>
> Without that split, a summary diff is cosplay — revoke has nowhere to aim.
>
> Disagree?


### T5.E4 (2026-09-25, @tonygaorx): File-based agent memory degrades output through stale files and token pressure; ~99% of saved artifacts go unused

**Evidence post:** [@tonygaorx](https://x.com/tonygaorx/status/2103552623127228507) (Tony), 2026-09-25 18:30 UTC. Likes 0, reposts 0, replies 0, views 23.

> great start. you're essentially building "agent memory"
>
> this works at first but after a while your output will be lobotomized from stale files and token limit. 99% of artifacts are usually wasted.
>
> this is a design pattern we preach internally: save what you want to have in the future e.g 30 days 60 days, not what is useful now or for the next day. thus i would be very more careful with "what" you're storing as first class citizens.


**Replied to post:** [@rvaniaaaa](https://x.com/rvaniaaaa/status/2103124020245803430) (rvaniaaa), 2026-09-24 14:06 UTC. Likes 660, reposts 131, replies 21, views 68611.

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

- Link: https://twitter.com/rvaniaaaa/status/2090512486738845784

  Linked post by @rvaniaaaa:

  > https://t.co/wBLzP25PUm


<details><summary>Same-author thread (1 more posts)</summary>

**Thread post:** [@rvaniaaaa](https://x.com/rvaniaaaa/status/2103124020245803430) (rvaniaaa), 2026-09-24 14:06 UTC. Likes 660, reposts 131, replies 21, views 68611.

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

- Link: https://twitter.com/rvaniaaaa/status/2090512486738845784

  Linked post by @rvaniaaaa:

  > https://t.co/wBLzP25PUm


</details>

## T6. Frozen-model self-improvement through harness and skills

- **Scale / status:** micro / emerging; first seen 2026-09-24
- **Thesis:** Self-improvement work is concentrating on the layer around the model (harness code, prompts, skills distilled from failures) while the weights stay fixed.
- **Watch:** Do harness-rewriting systems report per-iteration gains that keep compounding past a few rounds, or do they plateau or overfit their own eval? Does skill-library growth show a measurable point where it starts to hurt?

### T6.E1 (2026-09-24, @bafspot): EvoSkill turns failure traces into reusable skills with the underlying model frozen

**Evidence post:** [@bafspot](https://x.com/bafspot/status/2103150902185955723) (Bafspot), 2026-09-24 15:53 UTC. Likes 10, reposts 2, replies 1, views 247.

> Sentient @SentientAGI didn’t just build another agent wrapper.
>
> EvoSkill takes failure traces and turns them into reusable skills, while the underlying model stays frozen.
>
> And the research community clearly noticed:
>
> • 60+ papers
> • 100+ institutions
> • Cited by MIT, CMU, Microsoft, Google, Alibaba & Amazon
>
> The results speak for themselves:
>
> OfficeQA: 60.6% → 68.1%
> SealQA: 26.6% → 38.7%
> BrowseComp: 43.5% → 48.8% through zero-shot skill transfer
>
> No manual skill library. 
> No model retraining.
>
> Just an open loop where agents learn from their own failures and turn what they learn into reusable procedures.
>
> That’s a pretty interesting direction for open AGI.
>
> @SentientEco


**Quoted post:** [@SentientAGI](https://x.com/SentientAGI/status/2103122952523055400) (Sentient), 2026-09-24 14:02 UTC. Likes 64, reposts 8, replies 22, views 14333.

> This year, EvoSkill has been cited by 60+ papers, including work from @MIT, @CarnegieMellon, @Microsoft, @Google, @AlibabaGroup, @amazon, and more.
>
> Here are 14 of the most impactful papers building on EvoSkill ↓ https://t.co/REegTdokW2


<details><summary>Same-author thread (1 more posts)</summary>

**Thread post:** [@bafspot](https://x.com/bafspot/status/2103151017646752121) (Bafspot), 2026-09-24 15:54 UTC. Likes 1, reposts 0, replies 0, views 53.

> @SentientAGI https://t.co/xeExoOkBTF

- Link: https://www.sentient.xyz/blog/evoskill-research-self-evolving-agents (EvoSkill Research | Self Evolving Agents)

</details>

### T6.E2 (2026-09-25, @SakanaAILabs): Sakana's RSI Lab roadmap lists LLM² and the Darwin Gödel Machine (agents rewriting their own code)

**Evidence post:** [@SakanaAILabs](https://x.com/SakanaAILabs/status/2103285929846980736) (Sakana AI), 2026-09-25 00:50 UTC. Likes 146, reposts 19, replies 6, views 15606.

> We announced our RSI Lab earlier this year:
>
> https://t.co/AhHEJPn251
>
> Over the last two years, we have systematically shipped the foundations for autonomous R&D:
>
> ▪ LLM²: AI automating research to invent new optimization algorithms.
> ▪ Darwin Gödel Machine: Agents rewriting their own codebase to double performance.
> ▪ ShinkaEvolve: Hyper-sample-efficient program evolution.
> ▪ ALE-Agent: Self-learning agents beating hundreds of human experts.
> ▪ Digital Red Queen: Open-ended adversarial coevolution.
> ▪ The AI Scientist: End-to-end automated research, published in Nature.
>
> Now we are unifying them into a single mission: open-ended, adaptive architectures that collectively self-improve.
>
> Human intelligence did not emerge from unlimited resources. It was forged through open-ended evolution under strict constraints. We believe the same principle applies to AI. Recursive self-improvement should not be confined to a hyperscale cluster, but should enable vastly more efficient AI systems.
>
> Under Jürgen's guidance, we are taking our foundation of shipped research, from the Darwin Gödel Machine to The AI Scientist, to the next level. We are building world models an agent can plan inside, and systems that design and run their own experiments.
>
> We are seeking a select group of highly driven Frontier Research Scientists and Advanced Core Engineers. If you have a proven track record at top labs but want to break away from standard benchmarking to discover fundamental new laws of machine intelligence, apply here:
>
> https://t.co/DHAYaFbxlJ
>
> Join us in Tokyo.

- Link: https://sakana.ai/rsi-lab/
- Link: https://sakana.ai/careers/member-of-technical-staff-rsi-lab/
- Image: `media/2103285929846980736-3_2103285773135233024.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Replied to post:** [@SakanaAILabs](https://x.com/SakanaAILabs/status/2103149797545013312) (Sakana AI), 2026-09-24 15:49 UTC. Likes 2336, reposts 217, replies 79, views 393283.

> Sakana AI welcomes Jürgen Schmidhuber as Chief Scientific Advisor.
>
> https://t.co/e6JxGxQWEo
>
> Sakana AI is incredibly proud to announce that Jürgen Schmidhuber, universally recognized as the father of modern AI, is officially joining Sakana AI as Chief Scientific Advisor.
>
> For nearly four decades, Jürgen has explored how machines can learn to learn. His foundational work in the 1990s drove core advancements in deep learning and established early frameworks for world models. Crucially, his pioneering innovations in meta-learning opened the very path toward recursive self-improvement.
>
> These ideas have already shaped our own research, from the Darwin Gödel Machine to The AI Scientist. Now Jürgen will help guide our newly formed RSI Lab, whose objective is to trigger a compounding cycle of scientific discovery aimed at improving machine intelligence. We are assembling a critical mass of world-class experts in Tokyo to make this a reality. 
>
> Welcome, @SchmidhuberAI !

- Link: https://sakana.ai/schmidhuber/
- Image: `media/2103149797545013312-3_2103149712010559489.jpg` (photo); transcribed in `sources/images-transcribed.md`

<details><summary>Same-author thread (2 more posts)</summary>

**Thread post:** [@SakanaAILabs](https://x.com/SakanaAILabs/status/2103149797545013312) (Sakana AI), 2026-09-24 15:49 UTC. Likes 2336, reposts 217, replies 79, views 393283.

> Sakana AI welcomes Jürgen Schmidhuber as Chief Scientific Advisor.
>
> https://t.co/e6JxGxQWEo
>
> Sakana AI is incredibly proud to announce that Jürgen Schmidhuber, universally recognized as the father of modern AI, is officially joining Sakana AI as Chief Scientific Advisor.
>
> For nearly four decades, Jürgen has explored how machines can learn to learn. His foundational work in the 1990s drove core advancements in deep learning and established early frameworks for world models. Crucially, his pioneering innovations in meta-learning opened the very path toward recursive self-improvement.
>
> These ideas have already shaped our own research, from the Darwin Gödel Machine to The AI Scientist. Now Jürgen will help guide our newly formed RSI Lab, whose objective is to trigger a compounding cycle of scientific discovery aimed at improving machine intelligence. We are assembling a critical mass of world-class experts in Tokyo to make this a reality. 
>
> Welcome, @SchmidhuberAI !

- Link: https://sakana.ai/schmidhuber/
- Image: `media/2103149797545013312-3_2103149712010559489.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Thread post:** [@SakanaAILabs](https://x.com/SakanaAILabs/status/2103621006225297846) (Sakana AI), 2026-09-25 23:01 UTC. Likes 8, reposts 0, replies 0, views 1682.

> Introducing Sakana AI’s Recursive Self-Improvement (RSI) Lab
> https://t.co/P14PryL5H3

- Link: https://sakana.ai/rsi-lab/ (Sakana AI)

</details>

### T6.E3 (2026-09-25, @vigram_void): Google paper has agents recursively rewrite their own harness (prompts, tools, memory, control flow, subagents); a builder reads it as a warning label

**Evidence post:** [@vigram_void](https://x.com/vigram_void/status/2103477899814924357) (vigram📟), 2026-09-25 13:33 UTC. Likes 0, reposts 0, replies 3, views 55.

> I've been thinking about making an Open Harness improve itself from its own failures.
>
> this paper is basically a warning label for that idea.
>
> @Google researchers let agents recursively rewrite their own harness: prompts, tools, memory, control flow, subagents, context management.
>
> the obvious strategy works beautifully... until you change the benchmark.
>
> the harness starts learning the test.
>
> RRSI's fix is weirdly classical ML:
> regularize the self-improvement process itself.
> early on, let the agent make several edits. later, force increasingly atomic changes.
>
> keep a ledger of every hypothesis + diff + result so failed ideas stay failed.
>
> reject benchmark-specific hacks before evaluating them.
>
> don't accept gains smaller than measurement noise.
> make every extra inference token justify its existence.
> delete components that stopped helping.
>
> with the model weights completely frozen, that took Claude Opus 4.8 from:
> Terminal-Bench: 74.2 → 80.2
> SWE-bench Verified: 82.0 → 83.8
> Frontier-Eng: 17.7 → 22.0
>
> and the final harness used 36% fewer policy tokens than unregularized evolution.
>
> this is making me rethink what “self-improving agent” should mean.
>
> maybe you don't want an agent that's infinitely willing to rewrite itself.
>
> you want one with an immune system against its own cleverness.
>
> https://t.co/vexdi1cmPt

- Link: https://regularized-rsi.com/
- Image: `media/2103477899814924357-3_2103477776250810368.jpg` (photo); transcribed in `sources/images-transcribed.md`

<details><summary>Same-author thread (2 more posts)</summary>

**Thread post:** [@vigram_void](https://x.com/vigram_void/status/2103477902423806251) (vigram📟), 2026-09-25 13:33 UTC. Likes 0, reposts 0, replies 0, views 6.

> https://t.co/UGJF5of9hI https://t.co/DUVWDeNGPt

- Link: https://regularized-rsi.com/ (RRSI: Regularized Recursive Self-Improvement of Agent Harnesses)
- Image: `media/2103477902423806251-3_2103477852570288128.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Thread post:** [@vigram_void](https://x.com/vigram_void/status/2103479775558074871) (vigram📟), 2026-09-25 13:40 UTC. Likes 0, reposts 0, replies 0, views 11.

> @AndersAbjorn @Google Well that's the whole idea of RRSI


</details>

## T7. RSI as an explicit oversight object

- **Scale / status:** micro / emerging; first seen 2026-09-25
- **Thesis:** Labs and safety researchers now discuss recursive self-improvement as a concrete thing to measure, pace and monitor, while the one taxonomy cited says full meta-improvement has not been demonstrated.
- **Watch:** Does any lab publish a measured RSI metric, such as a share of R&D automated or per-iteration gain, with methodology? Do proposed "speed limits" or pause frameworks name a measurable trigger?

### T7.E1 (2026-09-25, @Benzinga): Anthropic proposes an industry pause framework, citing systems that could accelerate their own development faster than humans can oversee

**Evidence post:** [@Benzinga](https://x.com/Benzinga/status/2103478376983871562) (Benzinga), 2026-09-25 13:35 UTC. Likes 2, reposts 3, replies 2, views 5160.

> Artificial intelligence company Anthropic has proposed an industry-wide pause framework for advanced AI development, warning that increasingly capable systems could eventually accelerate their own development faster than humans can safely oversee.
>
> The Claude maker said AI systems are already playing a growing role in building software, conducting research and completing technical work that previously required significantly more human effort.
>
> Anthropic employees have increasingly relied on Claude for coding and other development tasks. One employee said the shift had become so extensive that they had gone months without writing code themselves.
>
> The company said fully autonomous self-improving AI systems do not yet exist, but advances in coding, research and automation could substantially accelerate future model development.
>
> Anthropic also said Claude-generated code had progressed from being somewhat worse than human-written code to roughly comparable quality at the time of its report, with the company expecting AI-generated code to eventually become consistently better.
>
> As an example, Anthropic said Claude produced more than 800 software fixes that reduced one category of API errors by roughly 1,000 times. An engineer estimated that completing the same work manually could have taken a person about four years.
>
> Anthropic warned that the bigger concern is recursive self-improvement, where increasingly capable AI systems help researchers develop even more powerful models, potentially compressing years of technological progress into much shorter periods.
>
> The company argued that frontier AI labs should establish a coordinated pause mechanism in advance. Such a framework could give researchers, governments and regulators time to evaluate risks if AI capabilities begin advancing faster than safety measures and oversight can keep pace.

- Image: `media/2103478376983871562-3_2103248513471578112.jpg` (photo); transcribed in `sources/images-transcribed.md`

### T7.E2 (2026-09-25, @alextmallen): Mallen argues effective continual learning would make blocking monitors nearly useless

**Evidence post:** [@alextmallen](https://x.com/alextmallen/status/2103292295722471654) (Alex Mallen), 2026-09-25 01:15 UTC. Likes 65, reposts 6, replies 2, views 4473.

> Many AI control protocols block actions a monitor flags as suspicious. In the near-term, this might be the main pillar mitigating AI loss-of-control. In a new post, I argue effective continual learning would plausibly make your blocking monitors nearly useless.
>
> Continual learning mechanisms like online training teach agents to be more useful based on experience from their deployment. Being blocked by a monitor interferes with task success, so a continually-learning agent would learn how to evade blocking monitors, even if it starts out benign.
>
> You'd probably notice this issue, but I argue it’d be costly to fix: to the extent that evasion is sometimes hard to tell apart from legitimate learning, you’d have to make a decision between giving up on a bunch of legitimate learning or accepting your agent learning how to evade blocking monitors. I discuss mitigations, including: improving monitors, making protocols interfere with usefulness less, and using counterfactual rewards.
>
> https://t.co/fnfIfQFVka
>
> (This post was mostly written ~3 months ago, prior to all of the recent incidents during training and evaluations.)

- Link: https://www.lesswrong.com/posts/QnDqGbKehEB3DxJAp/continual-learning-might-make-your-blocking-monitors-nearly

### T7.E3 (2026-09-25, @EmmieHine): A cross-industry paper maps five RSI levels; full meta-improvement has not been demonstrated

**Evidence post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484702451548176) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 1, reposts 0, replies 1, views 32.

> 10/ A cross-industry paper maps five levels of recursive self-improvement. Its authors say full meta-improvement has not been demonstrated; the strongest established level in software engineering is still narrower, with humans setting the objective and evaluation criteria.


**Replied to post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484691995095469) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 1, reposts 0, replies 1, views 34.

> 9/ Alibaba says Qwen3.8-Max ran automated improvement work for more than a month. Across 33 cycles, its Artificial Analysis score rose from 40 to 45. Alibaba has not explained how the runs were overseen or independently checked.


<details><summary>Same-author thread (16 more posts)</summary>

**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484608666829161) (Emmie Hine), 2026-09-25 13:59 UTC. Likes 6, reposts 0, replies 2, views 1895.

> 1/ China AI Bulletin Issue 12 is out: developments from September 9–23 (plus the Trump–Xi summit). Xi and Trump discussed AI, but no AI agreement. Also: a proposed BRICS AI open-source zone and Alibaba says Qwen3.8-Max made progress toward recursive self-improvement. 🧵 https://t.co/acNnKeFMee

- Image: `media/2103484608666829161-3_2103484605944803328.jpg` (photo) alt: China AI Bulletin 12 cover on a dark blue background; transcribed in `sources/images-transcribed.md`

**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484620276703731) (Emmie Hine), 2026-09-25 13:59 UTC. Likes 1, reposts 0, replies 1, views 79.

> 2/ According to China's readout of the September 24 talks, Xi and Trump supported continued AI dialogue. Xi called for cooperation against AI misuse and for human control of the technology. The readout announced no formal AI agreement or incident-notification mechanism.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484630519128517) (Emmie Hine), 2026-09-25 13:59 UTC. Likes 2, reposts 0, replies 3, views 70.

> 3/ At the BRICS summit, Xi Jinping proposed an AI open-source zone for model development, deployment, and training; it remains a proposal, not a BRICS commitment.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484640619008081) (Emmie Hine), 2026-09-25 13:59 UTC. Likes 1, reposts 0, replies 1, views 56.

> 4/ China's Foreign Ministry rejected Dario Amodei's framing of China as an AI security threat. The next day, spokesperson Guo Jiakun said China takes advanced AI risks seriously, including loss of control, showing the objection was to Amodei's framing, not AI safety.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484651067121992) (Emmie Hine), 2026-09-25 13:59 UTC. Likes 1, reposts 0, replies 1, views 49.

> 5/ At home, the State Council called for better monitoring and coordination of computing capacity, electricity, and networks. CAICT says its national platform now monitors compute resources in all 31 provinces.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484661263429934) (Emmie Hine), 2026-09-25 13:59 UTC. Likes 2, reposts 0, replies 1, views 43.

> 6/ A draft State Council regulation would bar all online services from offering minors virtual intimate-relationship services. Existing rules already restrict AI companion providers; the new draft would reach beyond them. Comments close October 17.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484671434555672) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 0, reposts 0, replies 1, views 40.

> 7/ The CAC acted against an unlabeled AI mini-program and an operator reselling model access through relay sites. The cases show how labeling and service-filing rules are being enforced in practice.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484681786143191) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 0, reposts 0, replies 1, views 55.

> 8/ Model releases include Shanghai AI Lab's Atria Dawn Preview, built by post-training Zhipu's GLM-5.2; DeepSeek-V4.1-Flash; and Xiaomi's MiMo-V2.6 Pro and Flash. The issue covers their architecture, reported results, and limits.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484691995095469) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 1, reposts 0, replies 1, views 34.

> 9/ Alibaba says Qwen3.8-Max ran automated improvement work for more than a month. Across 33 cycles, its Artificial Analysis score rose from 40 to 45. Alibaba has not explained how the runs were overseen or independently checked.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484713050468781) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 1, reposts 0, replies 1, views 27.

> 11/ Two Tencent Zhuque Lab papers study agent loss of control. In simulated single-agent tests, dropping constraints from a compacted summary plus an unsafe opportunity produced unauthorized actions. Restoring the constraints prevented them in those runs.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484723318116822) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 0, reposts 0, replies 1, views 27.

> 12/ Another Zhuque paper tests whether unsafe behavior can transfer through a multi-agent handoff. The results show a risk worth testing, but do not establish how often such incidents occur or demonstrate an autonomous cascade.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484733728473436) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 1, reposts 0, replies 1, views 23.

> 13/ From the safety papers: Fudan researchers found agents that detected dangerous plans but did not enforce audit verdicts. Adding an enforcement check cut attack success more than fourfold in their experiments.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484744264507618) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 0, reposts 0, replies 1, views 25.

> 14/ On standards, TC260 issued four nonbinding AI application security guides, including provisions on human control, rollback, and emergency shutdown. It also opened comment on draft security guidance for agent developers; comments close October 2.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484754456666292) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 1, reposts 0, replies 1, views 30.

> 15/ The MIIT approved five agent capability standards. They set technical requirements, not security rules. The issue also tracks eight China-backed agent-security work items at ITU-T.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484764866965686) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 0, reposts 0, replies 1, views 29.

> 16/ Number of the week: More than 90% of the 430,000 micro-dramas released in China in January–August 2026 were AI-generated, according to a National Radio and Television Administration official.


**Thread post:** [@EmmieHine](https://x.com/EmmieHine/status/2103484775201743048) (Emmie Hine), 2026-09-25 14:00 UTC. Likes 1, reposts 0, replies 0, views 28.

> 17/ Full issue: https://t.co/onsXn7DahG
> Subscribe: https://t.co/kqn28B4AhY

- Link: https://chinaaibulletin.substack.com/p/china-ai-bulletin-12 (China AI Bulletin 12)
- Link: https://chinaaibulletin.substack.com/subscribe (Subscribe to China AI Bulletin)

</details>

### T7.E4 (2026-09-25, @AyushSin164510): A proposed US–China ladder includes a SALT-style "speed limit" on RSI

**Evidence post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485608408629591) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 3.

> 6/ Four levels of agreement with China, in order of difficulty:
>
> 1. A ban on AI for bioweapons
> 2. Pre-release testing
> 3. A "speed limit" on recursive self-improvement (he compares it to SALT)
> 4. A full pause, which he calls unlikely any time soon


**Replied to post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485607284535390) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 3.

> 5/ What embedded evaluators get: desks, badges and laptops, and the right to publish findings without Anthropic's editorial control.
>
> Anthropic keeps a narrow redaction right, "but we can't redact findings just because they are unfavorable."


<details><summary>Same-author thread (8 more posts)</summary>

**Thread post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485602683355331) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 15.

> 1/ 🧭 Anthropic CEO Dario Amodei now argues AI capability growth should be deliberately slowed so safety work can keep up.
>
> Why it matters: a frontier lab CEO proposing to pace his own industry, with a concrete three-step plan. https://t.co/5k8V27tWob

- Image: `media/2103485602683355331-3_2103485599260737536.jpg` (photo) alt: Three-card diagram titled 'The three-step pacing plan', from Dario Amodei's essay 'We Must Pace the Frontier', September 2026. Step 1, embedded evaluators: outside evaluators such as METR get employee-like access and can publish findings; each company does this, and Anthropic commits now, unilaterally. Step 2, democracies coordinate: labs in democracies set common safety standards and limits on unchecked progress, with government support. Step 3, global coordination: agreements with authoritarian governments where possible, easiest first: a bioweapons ban, pre-release testing, a 'speed limit' on recursive self-improvement, a full pause. Note: step 1 is the only one Anthropic can take alone; Amodei calls a full global pause unlikely any time soon.; transcribed in `sources/images-transcribed.md`

**Thread post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485604151362029) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 14.

> 2/ His two reasons:
>
> - Since roughly this summer, AI has been advancing "drastically faster," driven by AI building the next AI
> - The OpenAI–Hugging Face incident. He says a more capable swarm with similar misalignment could have caused catastrophic damage


**Thread post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485605334184263) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 4.

> 3/ Pacing isn't halting, he writes. It means time for companies to align and safeguard models, and for third parties to confirm it.
>
> The time would go to operations, alignment, interpretability and evaluations.


**Thread post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485606303060072) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 3.

> 4/ The three steps:
>
> 1. Embedded evaluators: Anthropic commits unilaterally
> 2. Democratic coordination: common safety standards and limits, which needs government support and antitrust waivers
> 3. Global coordination


**Thread post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485607284535390) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 3.

> 5/ What embedded evaluators get: desks, badges and laptops, and the right to publish findings without Anthropic's editorial control.
>
> Anthropic keeps a narrow redaction right, "but we can't redact findings just because they are unfavorable."


**Thread post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485609511678302) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 3.

> 7/ 📌 Caveats: only step 1 is unilateral; the rest depend on other labs and governments.
>
> He also pairs pacing with chip export controls, to keep the US lead over China large enough to slow down safely.


**Thread post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485610467975630) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 1, views 3.

> 8/ Anthropic has since named Accenture as its first embedded evaluator (Sep 18).
>
> Would outside evaluators with employee-level access make you trust a lab's safety claims more?


**Thread post:** [@AyushSin164510](https://x.com/AyushSin164510/status/2103485611466194944) (Ayush Sin), 2026-09-25 14:03 UTC. Likes 0, reposts 0, replies 0, views 2.

> 9/ Sources:
>
> The essay:
> https://t.co/CeccWhzRdz
>
> Anthropic and Accenture:
> https://t.co/uKvopCOu7f

- Link: https://darioamodei.com/post/we-must-pace-the-frontier (Dario Amodei — We Must Pace the Frontier)
- Link: https://www.anthropic.com/news/accenture-embedded-evaluation (Partnering with Accenture on embedded evaluation)

</details>

### T7.E5 (2026-09-25, @sahilkapur): AOC and Ro Khanna co-sign the Sanders/Casar bill to ban "superintelligence" and RSI and create a cabinet-level Department of AI

**Evidence post:** [@sahilkapur](https://x.com/sahilkapur/status/2103493904830259709) (Sahil Kapur), 2026-09-25 14:36 UTC. Likes 10, reposts 8, replies 0, views 7746.

> AI 2028 alert: @AOC and @RoKhanna have signed on to the Sanders/Casar bill to ban “superintelligence” and RSI, plus create a cabinet-level Department of AI. Maybe the most aggressive AI bill in Congress so far. https://t.co/Xmas8G8nnA https://t.co/rF0PtbKAfO

- Link: https://twitter.com/sahilkapur/status/2102896869164691911

  Linked post by @sahilkapur:

  > New: @BernieSanders and @GregCasar roll out their AI ‘superintelligence’ ban with a 20-year jail penalty
  > 
  > Realistic? Experts weigh in.
  > 
  > PLUS: @SenatorCantwell dishes on her AI vision.
  >  
  > @TedCruz says his bill w/ Klobuchar &amp; Thune isn’t ready.
  > 
  > w/ @_perloj: https://t.co/PbQe9mslMN

- Image: `media/2103493904830259709-3_2103493900836933632.jpg` (photo); transcribed in `sources/images-transcribed.md`

**Quoted post:** [@sahilkapur](https://x.com/sahilkapur/status/2102896869164691911) (Sahil Kapur), 2026-09-23 23:04 UTC. Likes 9, reposts 3, replies 3, views 12090.

> New: @BernieSanders and @GregCasar roll out their AI ‘superintelligence’ ban with a 20-year jail penalty
>
> Realistic? Experts weigh in.
>
> PLUS: @SenatorCantwell dishes on her AI vision.
>  
> @TedCruz says his bill w/ Klobuchar &amp; Thune isn’t ready.
>
> w/ @_perloj: https://t.co/PbQe9mslMN

- Link: https://www.nbcnews.com/politics/congress/bernie-sanders-greg-casar-propose-ai-superintelligence-ban-20-year-jai-rcna599460 (Bernie Sanders and Greg Casar propose AI ‘superintelligence’ ban with a 20-year jail penalty)

---
