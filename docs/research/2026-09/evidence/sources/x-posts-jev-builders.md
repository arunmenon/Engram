# X posts: builders using Jev (linked posts + cited evidence posts)

- **URL:** multiple (listed per post below)
- **Type:** X post (plus one X article, by kylejeong)
- **Author / org:** vtrivedy10 (LangChain), kylejeong (Browserbase), motherduck, tazr_dev, rbro112 (Sentry), akshay_pachaar, hamzaashergill, typesafeai (TypeSafe AI, maker of Jev), LFrefman
- **Date:** 2026-09-18 to 2026-09-25
- **Retrieved:** 2026-09-26 (local copies: raw/linked_posts.json, raw/evidence.json; images in media/). Post texts are quoted verbatim. HTML entities in the API payload (`&amp;`, `&gt;`) are decoded to `&` and `>`. `t.co` links are kept as they appear.
- **Cited by evidence:**
  - Decision models as the memory control plane: 2026-09-23 LFrefman; 2026-09-24 typesafeai (quoting Vtrivedy10); and the akshay_pachaar linked post (Beacon), which relates to the 2026-09-25 ethanwalkerman evidence.
  - Typed-decision tier displacing LLM calls on bounded classification: 2026-09-21 typesafeai (MotherDuck); 2026-09-24 typesafeai (JevSearch); 2026-09-25 typesafeai (Deel); 2026-09-25 tazr_dev; 2026-09-25 rbro112; 2026-09-25 hamzaashergill.
- **Relevance to a memory stack:** medium-high. These are the field reports on where a fast typed-decision model works (judging, classifying, reranking, write-gating) and where it does not (fine-grained control inside a coding agent loop).

## TL;DR
- **Eval judging is the strongest field result.** rbro112 (Sentry) moved one eval dataset from Gemini 3.1 to Jev and reports no meaningful accuracy change, about 200x lower cost, about 50x lower latency, and a > 0.8 probability threshold. The loss is the written reasoning, so failures are passed to an LLM to explain. hamzaashergill independently says the speed decides whether evals become a per-PR gate.
- **Counter-evidence.** tazr_dev tested 6 Jev-style fast actions inside a coding agent loop (rank, gate, intent, suff, met, reflex) and "None survived". Only `met` ("is the goal done?") looked promising.
- **Relevance and reranking.** Vtrivedy10 (LangChain) trusts Jev's semantic matching over dot-product similarity: use it as the similarity metric on small data and as a reranker on big data. JevSearch has Jev rescore the top 25 web results, and it often promotes URLs from outside the original top 5.
- **Bounded classification in production (vendor-reported).** Deel: repeat-question matching 70% to 97%, expense categorisation 50% to 86%, up to 59x cheaper, up to 4x faster, 6 of 8 quality checks at parity or better. Two regressions: -3.6 points and -16.6 points (messy real questions). MotherDuck: 100k rows in 40 s for $0.50 vs 32 min and $37.
- **Memory write-gating.** Beacon uses Jev to decide which agent sessions to promote into reusable skills (579 sessions, 5 harnesses). Jev-Mem (LFrefman) uses a System-One controller for memory routing and budgeting, with LoCoMo 0.777 claimed (+11%).

## What it claims / describes

### A. Linked X posts (raw/linked_posts.json)

**1. Vtrivedy10 (Viv, applied research @LangChain Labs), 2026-09-23T17:14:19Z, https://x.com/Vtrivedy10/status/2102808794493321714** (122,517 impressions, 735 likes, 932 bookmarks). The post includes an image (media 3_2102808790710030337, not stored locally).
> Jev for RAG
>
> in almost all cases you trust the semantic matching capability of Jev more than dot product similarity
>
> very useful as the direct similarity metric in small data cases
>
> and a great reranker with big data https://t.co/7tMQE5sv26

Quoted by typesafeai, 2026-09-24T16:53:32Z (https://x.com/typesafeai/status/2103165951781032167): "Keep cooking, most best practices with Jev have yet to be discovered! https://t.co/YR9UcneWdz"

**2. kylejeong (Kyle Jeong, growth engineering @browserbase), 2026-09-23T00:52:39Z, https://x.com/kylejeong/status/2102561749404971460** (with a video, not stored)
> I built JevSearch, search the web & validate your results with Jev.
>
> Give a query and selection criteria, use @browserbase search to get the t25 results, then Jev scores and returns the t5 results.
>
> Jev often chooses urls outside of the initial top 5 as more relevant. https://t.co/jT3sM3vWYl https://t.co/NRc4KLyD0v

Quoted by typesafeai, 2026-09-24T20:21:23Z (https://x.com/typesafeai/status/2103218258405118035): "Relevance is great, but relevance to what? Jev gives you search intelligence that no canned SEO can 🪱 its way into. https://t.co/6RwRen3I05"

No figure is given for how often "often" is.

**3. kylejeong X article "Jev wasn't built to make Agents", 2026-09-21T18:53:17Z, https://x.com/kylejeong/status/2102108924677927169** (article https://x.com/i/article/2101856134483353600; 170,476 impressions). This is a long article, so it is summarised here with key passages verbatim. Its 5 images are not stored.
- TypeSafe's description, quoted: "a class of AI models built to make fast, structured decisions that software can use directly. A System One model evaluates a state and returns typed answers and probabilities." According to TypeSafe's benchmarks, Jev is "20-200x faster and 40-400x cheaper than LLMs."
- Primitives:
  - "Choice is a question type that selects one option from a defined set (of max 255) whose answer includes the selected option, a probability for each option, and confidence."
  - "Score rates content against ordered, descriptive levels whose answer includes a score, a probability for each level, and confidence."
  - "Noul asks the model to evaluate a yes/no question and return the probability that the answer is yes."
- Training: "Jev is trained with RLCD (reinforcement learning from calibrated decisions)". It "can also generate output in parallel". TypeSafe's CEO, Diogo Almeida, is described as ex-OpenAI and as having helped create RLHF and ChatGPT.
- Stance: "Jev is not very good as a standalone agent. We've tried to build versions of it, both Jev only and LLM + Jev." "Without reasoning or generative capabilities, using it as a standalone agent is just pure ignorance." Recommended uses are support routing, invoice processing, security alert triage, or "an agent monitor".
- Pricing and limits: "Jev 1.13.0 costs $42/btok (or $0.042/mtok) input and $0 for output tokens." "The context window is 64k tokens per request, where state + the longest question must fit in 32k tokens."
- Stagehand integration (`act`):
  1. Jev classifies the instruction into an action (click, fill, scroll).
  2. Stagehand builds a candidate list with nearby page context.
  3. Jev answers "which candidate is best" and "does any candidate match" "with an acceptance threshold of 0.7".
  4. If accepted, Stagehand executes.
  5. Otherwise it "falls back to an LLM".
  - Result: "Act median latency drops from 1.97 seconds to 0.46 seconds which is about 4.3× faster (or 77% less time)." PRs: https://github.com/browserbase/stagehand/pull/2951, /2953, /2993.
- API sample (verbatim input and output from the article's code block, abridged to the structure):
```json
{"model": "jev-latest",
 "state": "Hi, I was charged twice for my monthly subscription. Could you refund the extra charge? My account is working fine.",
 "questions": {
   "department": {"type": "choice", "instructions": "Which team should handle this message?",
     "criteria": {"billing": "Charges, payments, subscriptions, and refunds", "technical": "Bugs, errors, and broken features", "account": "Login, passwords, and account access"}},
   "requests_refund": {"type": "noul", "instructions": "Is the customer explicitly requesting a refund?"},
   "frustration": {"type": "score", "instructions": "How frustrated does the customer sound?",
     "criteria": ["Calm: politely describes the issue without expressing frustration", "Frustrated: expresses annoyance or dissatisfaction", "Very frustrated: expresses strong anger or threatens to leave"]}}}
// Output
{"model": "jev-1.13.0",
 "answers": {"department": {"type": "choice", "choice": "billing", "confidence": 1, "probabilities": {"technical": 0, "account": 0, "billing": 1}},
   "requests_refund": {"type": "noul", "noul": 0.99},
   "frustration": {"type": "score", "score": 0, "legend": {"0": "Calm: ...", "1": "Frustrated: ...", "2": "Very frustrated: ..."}, "confidence": 1, "probabilities": {"0": 1, "1": 0, "2": 0}}},
 "usage": {"input_tokens": 442, "output_tokens": 72},
 "request_id": "playground_12bbfa4198be5ca4de9818a45c0906a2055",
 "evaluation_time_ms": 163.01120699790772}
```

**4. motherduck, 2026-09-21T16:47:35Z, https://x.com/motherduck/status/2102077291081896307** (207,255 impressions)
> Text classification in MotherDuck just got ~50x faster at ~1% of the cost.
>
> prompt_jev() is a SQL function powered by Jev, TypeSafe's new system one model. 100k rows: 40s, $0.50, frontier-LLM accuracy. The LLM took 32 min and $37.
>
> Read on:
>
> https://t.co/XIE2cw6rUS https://t.co/CdP1q8OwDe

Quoted by typesafeai, 2026-09-22T01:21:27Z (https://x.com/typesafeai/status/2102206611024716181):
> Jev makes it easy to add natural language intelligence into the key parts of any application at scale, far cheaper and faster than has ever been possible.
>
> 50x faster.
> 100x cheaper.
> Reliable as duck. https://t.co/tY5PwtzlIn

typesafeai thread reply (2026-09-22T05:02:54Z): "@PawelJLisowski The cost of intelligence is too damn high! We've only scratched the surface on what we can optimize."

Full details are in sources/motherduck-prompt-jev.md. The "LLM" in the post is gpt-5.6-terra: 88% accuracy, $37.58, 31m 59s. Jev scored 89%, on AG News.

**5. tazr_dev (Trent Zock-Robbins), 2026-09-25T02:58:53Z, https://x.com/tazr_dev/status/2103318291456610667** (video, not stored)
> And now I present to you:
>
> A "beautiful rendition" of world of warcraft in three.js by Qwen 3.8 27b... (having removed the conical trees)
>
> While using a custom vibe coded harness and, pointlessly, djev. https://t.co/m0qzeNhMqF

**6. rbro112 (Ryan Brooks), 2026-09-24T22:26:53Z, https://x.com/rbro112/status/2103249840646029811** (reply in a conversation with @grichadev; linked from rbro112's own thread)
> @grichadev Wait but Jev was supposed to change everything

The parent tweet is not in the payload, so the context is not available.

**7. akshay_pachaar (Akshay, co-founder @dailydoseofds_), 2026-09-23T16:20:32Z, https://x.com/akshay_pachaar/status/2102795260296593567** (114,042 impressions, 1,482 bookmarks; video not stored). Full long-form text (note_tweet):
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
> (don't forget to star it ⭐)
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

The repo is http://github.com/Asymptote-Labs/agent-beacon (t.co expanded). The quoted article is https://twitter.com/703601972/status/2101037514945597645 (not retrieved).

### B. Evidence posts (raw/evidence.json)

**rbro112 (Ryan Brooks, Staff Eng @sentry on AI/ML, "all things evals"), 2026-09-25T15:07:11Z, https://x.com/rbro112/status/2103501576405172326** (2,549 impressions). The post quotes his own 2026-09-18 post 2101029904578158781, whose text is "👀👀 https://t.co/rtx7Vcu5Zc".
> It's been a week since I moved one of eval datasets from Gemini 3.1 to Jev by @typesafeai for LLM judging. The results so far:
>
> - No meaningful change in scoring accuracy
> - ~200× cheaper (~$0.01 → ~$0.00005 per judge)
> - ~50× faster (~10s → ~0.2s median)
> - ~50% fewer input tokens, 87% fewer output tokens
>
> But not everything's perfect, more details in the thread

Thread (in order):
- 15:08:10Z: "Jev isn't an LLM, requiring us to change our judging to classify conclusions as pass/fail. We had to set probability thresholds for the pass/fail (what Jev calls nouls), as Jev's answers are always probabilities.\n\nThe biggest loss is evidence when scores change (duh, it's not an LLM). I and other devs use this to help explain scoring changes:" The attached image (media/2103501823214780888-3_2103501739702050816.jpg) shows an "Evaluator Scores" panel. AutofixRcaArtifactEvaluator: PASS, 1.00. AutofixRcaLlmEvaluator: FAIL, 0.00, with this written explanation: "The candidate RCA describes a KeyError related to 'unit_price' and 'price' in order_total, while the expected RCA describes an IndexError in reports.p95_latency due to an empty list from metrics.recent_latencies. The candidate completely misses the actual cause."
- 15:09:51Z: "But perf improvements are the most impactful boost for us. Some of our existing datasets that don't use Jev take around ~15min (some longer!), making it tough to run on a PR.\n\nSpeed is critical for us so we can run evals and not block our devs. Waiting 15 minutes+ on a PR is a productivity drain. This dataset is my next Jev target 👀" The attached image (media/2103502247082766500-3_2103502233845604352.jpg) shows a seer-evals bot comment for `malicious_issue_detection`:

  | Run | Passed | Failed | Errored | Cost | Tokens | Duration |
  |---|---|---|---|---|---|---|
  | Head | 304 | 2 | 0 | $0.14 | 379.5k | 1,020.46s |
  | Base | 305 | 1 | 0 | $0.20 | 381.2k | 847.24s |
  | Diff | -1 | +1 | 0 | -$0.06 | -1.7k | +173.22s |

  (inference: this is the slow, non-Jev dataset he refers to, about 15 to 17 minutes per run.)
- 15:12:54Z: "@miguelbetegon @typesafeai Sounds familiar https://t.co/zrWjSlZogQ" (this links to his own post "@grichadev Wait but Jev was supposed to change everything").
- 15:15:11Z: "@typesafeai Decision/classifier models are not new, Jev just made it dead simple to integrate in existing workflows.\n\nGiven how easy this was to integrate, we're going to expand Jev grading across all our evals (and maybe even AI products 👀).\n\nMore to come, but great work @typesafeai"
- 16:05:05Z: "@kn_neeraj1 @virtualmilin @typesafeai Should've touched on that but was trying to be brief, we pass a failed conclusion to an LLM to explain.\n\nSo Jev lets us get the pass/fail conclusion, and if the conclusion is failed we'll pass just those scores to the LLM to explain.\n\nNot perfect, but best bang-for-buck so far."
- 17:17:33Z: "@skobyn @typesafeai We didn't have a \"threshold\" for Gemini - we just let the LLM determine if the input passed/failed a specific criteria for better or worse.\n\nJev inherently uses probability of pass/fail, so we set an arbitrary threshold of something like > 0.8, which works well enough so far."
- 18:01:35Z: "@The_cryptobear @typesafeai Yep, for nouls the criteria for true/false (pass/fail) is specified to the request input: https://t.co/vFSjHVJpkV\n\nWe copied the criteria over 1:1 from our Gemini judge." (link: https://docs.typesafe.ai/primitives/noul#request-structure)

**hamzaashergill (Hamzaa Shergill), 2026-09-25T15:34:26Z, https://x.com/hamzaashergill/status/2103508434863657236** (reply to rbro112; 1 impression)
> @rbro112 @typesafeai The 50x faster number is the one that changes behavior, not just cost. When judging takes 10 seconds, you run it sparingly; at 0.2 seconds it becomes a gate on every PR. We found the same in our evals: the judge's speed determines whether the team actually uses it.

No numbers of his own are given. The "second team" claim rests on "We found the same".

**tazr_dev (Trent Zock-Robbins; bio: "veteran swe, ex-chemist ... localmaxxing Qwen 27B on 4 × 3090"), 2026-09-25T14:21:51Z, https://x.com/tazr_dev/status/2103490167248212384** (187 impressions). The post quotes the WoW three.js post (A.5 above).
> I tested 6 Jev-style fast actions in tack coding agent yesterday.  None survived.
>
> I'm going to survey what's out there before taking another pass.
>
> Biggest blocker is d/jev is too unreliable, and the next step up is the actual agent. https://t.co/Kfm8QglCTX https://t.co/9kRapfIuB7

Attached table (media/2103490167248212384-3_2103489775915376641.jpg), transcribed:

| Job | What it does | Outcome | Verdict | Count |
|---|---|---|---|---|
| rank | picks next ready item | reordered 10 of 15 real choices | unproven | 60 |
| gate | do step, or re-plan | 4 of 8 re-plans changed the plan | costly, mixed | 19 |
| intent | new goal vs steering | 5 real routings, all plausible | little effect | 18 |
| suff | "is the plan enough?" | 2 of 6 flagged a re-plan | unproven | 6 |
| met | "is the goal done?" | p rose before each goal closed | promising | 7 |
| reflex | react to failed cmd | never fired | untested | 0 |

Thread:
- 14:30:56Z: "I hope to find a fit for INTENT, MET, and REFLEX. I'm running tack agent as my doom oracle now."
- 14:31:26Z: "REPLAN still looks good to me, but I need to have a better contract for it."
- 14:34:02Z: "GATE and SUFF need more data as well. I wish I got a win here.\n\nTime to improve my testing methods and find another angle."

The poster writes "djev" and "d/jev" and calls the actions "Jev-style". It is not stated whether this is TypeSafe's hosted Jev or a local or distilled substitute. (inference: "d/jev" may be a distilled or local stand-in, given the local-model bio.) Sample sizes are tiny (0 to 60 invocations).

**typesafeai: Deel thread, 2026-09-25T03:13Z** (vendor-reported case study)
- Post 1 (https://x.com/typesafeai/status/2103321890190491710): "Observe the art of the @deel.\nAnd they came with receipts 💅 \nKeep reading to find out how it's done. https://t.co/mW7FxGvCbI". The image card reads: "Right-sized models, production results. 4 AI use cases at Deel. Same task, same data, specialised classifier vs what runs today. up to 59× cheaper per decision; up to 4× faster responses; 6 of 8 quality checks at parity or better. Analytics · Support triage · Ticket classification · Expense categorisation. Head-to-head evals on real Deel data · TypeSafe Jev vs frontier LLMs."
- Post 2 (https://x.com/typesafeai/status/2103321892421865838): "Some great use cases they measured:\n• Matching repeat analytics questions to approved answers\n• Picking 1 of 36 metrics\n• Blocking PII requests\n• Deciding when a support chat needs a human\n• Tagging tickets across a 3-level taxonomy\n• Sorting expenses into about 55 categories\nEvery one is a pick from a known set." The image "How much cheaper" gives cost per decision relative to the frontier LLM in use today: picking the right metric 59×; escalate-to-human detection 49×; root-cause ticket tagging ~45× ("estimated from per-token pricing"); PII guardrail 20×.
- Post 3, the cited evidence post (https://x.com/typesafeai/status/2103321894661595551): "Jev generally out-performed frontier LLMs at a fraction of the price:\nRepeat-question matching: 70% → 97%\nExpense categorization: 50% → 86% (vs human reviewers)\nEscalation: same catches, fewer false alarms https://t.co/tBg4CIigz0". The image "How much faster" gives response time relative to the frontier LLM: escalation detection (live shadow) 4×; picking the right metric 2.8×; escalation detection (offline test) 1.9×; PII guardrail parity. Footnote: "Live shadow: thousands of production conversations, run in parallel with the current model."
- Post 4 (https://x.com/typesafeai/status/2103321896553210029): "Speed was measured while shadowing live production traffic: up to 4× faster. Offline tests: 2 to 3×. https://t.co/SmlSLmW4rl". The image "Where quality landed" gives the accuracy change vs the current approach, in points: expense categorisation +36 (vs "today's rule-based receipt matching"); repeat-question matching +26.7; declining when no answer exists +8.3; metric pick on well-formed questions +2; escalations caught (with fewer false alarms) parity; PII guardrail parity (100% both); 3-level root-cause tagging **-3.6**; metric pick on messy real questions **-16.6**. "All others vs the frontier LLM on the same task."
- Note the mismatch in the post text: "Expense categorization: 50% → 86% (vs human reviewers)", while the image footnote says the +36 is vs rule-based receipt matching. Both are recorded as stated.

**typesafeai: JevSearch quote, 2026-09-24**. Covered in A.2 above.

**LFrefman (display name "Git_Shark"; bio: "The AI projects and news you should not missed"), 2026-09-23T23:56:10Z, https://x.com/LFrefman/status/2102909921553727522** (64 impressions)
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

Link: https://signalhigh.centritude.com/post/jev-mem-system-one-controlled-agentic-memory-for-efficient-a-47 (an aggregator page, not retrieved here). A separate evidence item (runbywren) ties this to arXiv 2609.23986.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Judge cost | ~$0.00005 per judge | ~$0.01 (Gemini 3.1) | Sentry, one eval dataset, 1 week | about 200x cheaper |
| Judge latency | ~0.2 s median | ~10 s | same | about 50x |
| Judge tokens | ~50% fewer input, 87% fewer output | Gemini 3.1 | same | |
| Judge accuracy | "No meaningful change" | Gemini 3.1 | same | Not quantified |
| Pass threshold | > 0.8 ("arbitrary") | LLM decided pass/fail directly | Noul | |
| Slow non-Jev eval | ~15 min+ per PR; 847 to 1,020 s in the screenshot | | malicious_issue_detection, 306 cases | Not a Jev result |
| tazr_dev fast actions | 0 of 6 survived | the agent itself | tack coding agent, 1 day | n = 0 to 60 per job |
| rank | reordered 10 of 15 real choices | | n=60 | unproven |
| gate | 4 of 8 re-plans changed the plan | | n=19 | costly, mixed |
| Stagehand act median latency | 0.46 s | 1.97 s (LLM) | Browserbase early testing | 4.3x; threshold 0.7; LLM fallback |
| Jev price | $0.042/MTok input, $0 output | Fable 5.1 $10/MTok input | kylejeong article | |
| Jev context | 64k per request; state + longest question <= 32k | | | |
| Sample call latency | 163 ms, 442 in / 72 out tokens | | playground | Single sample |
| JevSearch | top-25 rescored to top-5; "often" picks from outside the original top 5 | Browserbase search order | | Not quantified |
| MotherDuck | 100k rows, 40 s, $0.50, 89% | 32 min, $37 (gpt-5.6-terra 88%) | AG News | |
| Deel repeat-question matching | 97% (+26.7 pts) | 70% (frontier LLM) | Deel data | Vendor-reported |
| Deel expense categorisation | 86% (+36 pts) | 50% (rule-based or human reviewers; the sources conflict) | about 55 categories | Vendor-reported |
| Deel declining when no answer exists | +8.3 pts | frontier LLM | | |
| Deel metric pick | +2 pts (well-formed); **-16.6 pts (messy real questions)** | frontier LLM | 1 of 36 metrics | |
| Deel 3-level root-cause tagging | **-3.6 pts** | frontier LLM | | |
| Deel cost | 20x to 59x cheaper | frontier LLM | | root-cause figure estimated |
| Deel speed | up to 4x (live shadow); 2 to 3x offline; PII parity | frontier LLM | thousands of live conversations | |
| Beacon | 579 sessions across 5 harnesses normalised | | | No quality metrics |
| Jev-Mem | LoCoMo LLM-judge 0.777 (+11.0%); build 158 s (6.6x); query 0.93 s (-36.7%) | strongest baseline / fastest competitor | LoCoMo | Secondhand aggregator post |

## Mechanism details you could implement
- **Judge pattern (Sentry):** convert an LLM-judge criterion 1:1 into a Noul `criteria` true/false. Threshold at P > 0.8. Only for failures, send the scores to an LLM to generate an explanation. This keeps explanations while paying LLM prices only on the failure tail.
- **Rescore-then-select (JevSearch):** retrieve the top 25 cheaply, have Jev score each against the query plus explicit selection criteria, and return the top 5. This maps onto memory recall: retrieve top-k by vector or BM25, then decision-model select (inference).
- **Accept-or-fallback (Stagehand):** Jev picks the best candidate and answers "does any candidate match". Accept at >= 0.7, otherwise fall back to an LLM. This is a template for "decision model first, LLM on low confidence".
- **Write-gate (Beacon):** keep the full raw session history, and let the decision model decide promote / review / discard for distilled lessons and skills.
- **Loop-control probes (tazr_dev):** `met` ("is the goal done?") showed probability rising before each goal closed, so it may work as a stopping signal. `rank`, `gate`, `intent` and `suff` showed no clear benefit.

## Limitations, caveats, counter-evidence
- tazr_dev: 0 of 6 fast actions survived in a coding-agent loop; "too unreliable". It is unclear whether hosted Jev was used ("d/jev", "Jev-style"). The sample is tiny.
- kylejeong: "Jev is not very good as a standalone agent", tried both Jev-only and LLM + Jev.
- rbro112: the explanation for why a score changed is lost. The threshold is arbitrary. Only one dataset has moved so far. His "Wait but Jev was supposed to change everything" reply lacks its parent context.
- Deel: vendor-published with no methodology beyond "head-to-head evals on real Deel data". There are two regressions (-16.6 on messy real questions, -3.6 on 3-level tagging), and the baseline for expense categorisation is inconsistent between post text and image.
- Jev-Mem figures come from a low-reach aggregator account, secondhand.
- hamzaashergill offers no data of his own.

## Takeaways for tuning a memory stack
- Use a decision model as the **judge** in memory evals (grounded recall, correct no-recall, contradiction handling). The field evidence here is the most consistent: it is cheap and fast enough to gate every change. Keep an LLM explainer for failures only.
- Use it for **closed-set picks** over memory: memory type, route, keep/discard, which of k candidates. Expect degradation on messy, free-form inputs and deep taxonomies (Deel -16.6 and -3.6).
- Prefer **retrieve-wide then decision-select** (top-25 to top-5) over relying on cosine order alone.
- For **write gating**, keep raw history and gate only promotion into durable memory, as Beacon does.
- Do not expect a decision model to replace in-loop agent control (planning, re-planning, sufficiency). The only tentatively positive loop signal is "is the goal done?".
- Always put an LLM fallback or review path behind a confidence threshold (0.7 in Stagehand, 0.8 at Sentry).

## Open questions
- What are the Sentry accuracy figures (agreement rate with Gemini, flip rate)?
- Did tazr_dev use hosted Jev, and would listwise framing (as in Vectorize's article) rescue `rank`?
- How often does JevSearch pick from outside the top 5, and is it more accurate?
- Can Jev-Mem's LoCoMo 0.777 and 6.6x build speedup be independently reproduced (arXiv 2609.23986)?
- What quality metrics does Beacon's write gate achieve on its 579 sessions?

---
