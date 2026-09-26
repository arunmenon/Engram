# Jev + GPT-6 Astra StarCraft II result, and "Jev: The 9-Step Blueprint for Building a Faster Decision Brain for AI Agents" (X Article)

- **URL:** evidence post https://x.com/mika_systems/status/2103554329139417547 ; quoted post https://x.com/mika_systems/status/2101686148338798610 ; X Article https://x.com/i/article/2101639552796348418
- **Type:** X post + X article
- **Author / org:** @mika_systems (Mika). The StarCraft post says "The team tested..." but does not name the team.
- **Date:** article (quoted post) 2026-09-20 14:53 UTC; StarCraft post 2026-09-25 18:36 UTC
- **Retrieved:** 2026-09-26 (local copies: raw/article-2101686148338798610.txt, raw/articles.json, raw/linked_posts.json, raw/evidence.json; images media/article-3_2101*.jpg and media/2103554329139417547-13_2103551832333099008.jpg, transcribed in sources/images-transcribed.md)
- **Cited by evidence:** Typed-decision tier displacing LLM calls on bounded classification / 2026-09-25 mika_systems ("Jev + GPT-6 Astra planner won 9/10 StarCraft II games vs the hardest built-in AI; Jev alone won 0/10 (5 setups, 50 matches)")
- **Relevance to a memory stack:** medium. Not a memory result. It is the clearest reported number on the planner + fast-decider split (a generative model plans, a typed decider picks from an allowed menu), which is the same split proposed for memory control (LLM writes, decider gates). The article gives threshold and shadow-mode rules that transfer to memory gates.

## TL;DR
- Reported StarCraft II result vs the game's toughest built-in opponent, no cheats: Jev alone 0/10 wins; Astra's plan + random moves 0/10; Astra's plan + Jev's moves 9/10. The post says 5 setups across 50 matches but only describes 3 of the 5.
- Division of labour: "Astra made the plan. Jev picked the next move while the game kept running." Loop: Astra plans ahead, Jev picks an available move, the game plays it, both get the new state.
- Call volume: Jev 19,605 decisions vs Astra 509 replies across the tests; Jev median response 0.375 s in the 9/10 setup; cost $0.15 Jev vs $3.56 Astra per game (average of an earlier set of 4 wins, $3.71 total).
- The linked article (5 days earlier) does not describe the StarCraft experiment. It is a general Jev guide: three-yes test for when to use Jev, confidence is not accuracy, thresholds by cost of error (0.65 / 0.80 / human), shadow mode per route, rebuild the action menu after every state change.
- No methodology beyond the post: no race, map, game version, APM limits, or what the other 2 setups were.

## What it claims / describes

### A. The StarCraft II post (2026-09-25, verbatim)
Metrics: 49 likes, 7 reposts, 9 replies, 3,366 views. Attached: one video (only the thumbnail is stored).
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

It quotes https://twitter.com/mika_systems/status/2101686148338798610 (the article post, 109 likes, 180,875 views). No same-author thread or replies were captured.

**What exactly the planner does vs Jev (only what the post says):**
- Planner (GPT-6 Astra): "made the plan", "plans ahead". Replied 509 times across all tests.
- Jev: "picked the next move while the game kept running", "picks an available move". Returned 19,605 decisions. So Jev chooses from a menu of currently available moves (a Choice over allowed actions); it does not generate actions.
- The game (code) executes the move; "both get the new state".
- Not stated: how the plan is represented, whether the plan is passed into Jev's state, how often Astra is called (time- or event-driven), how the available-move menu is built, or the Jev question wording. From 19,605 / 509 the ratio is about 38 Jev decisions per Astra reply across all tests (inference, arithmetic; the totals mix setups).
- The random-moves control (0/10) shows the plan alone is not sufficient; the Jev-alone control (0/10) shows the fast chooser alone is not sufficient. Only the combination won.

### B. The X Article "Jev: The 9-Step Blueprint for Building a Faster Decision Brain for AI Agents" (2026-09-20)
Sections, with the concrete content:
1. **Find the decisions hiding inside your agent.** Circle every model call whose answer comes from a bounded set: Route, Classify, Score, Gate, Match. Use a generative model when the answer is open; use code when an exact rule solves it. Three-part test before adding Jev: "Can you list every acceptable answer before the call? Could a careful person make the judgment quickly from the supplied state? Can the application detect or recover from a wrong answer?" Three yeses = strong candidate; if the first is no, the task needs generation; "If the third is no, keep a human at the decision point."
2. **Contract: state in, decisions out.** Choice (one option, every option's probability, confidence), Score (ordered scale, each level needs a concrete description), Noul (probability a yes/no statement is true). Many questions per request over the same state, run independently; "One question cannot read another question's answer."
3. **Type-safe can still be wrong.** Confidence for Choice/Score "describes how concentrated the returned distribution is. A 95/3/2 split is more decisive than 36/34/30. It does not promise 95% accuracy on your data." Thresholds from labeled examples and cost of error: "A newsletter tag may auto-apply at 0.65. A support ticket may route at 0.80. A money transfer still needs deterministic checks and human approval." Run in shadow mode first; evaluate per route with a confusion matrix, escalation share, and cost per failure type.
4. **Build one router.** Code below. Pin the version you evaluated ("jev-1.13.0") because `jev-latest` moves.
5. **Batch independent questions.** TypeSafe's cookbook: 13 questions over one document, batched was "10× faster and 12.2× cheaper than sequential calls, with the same answers". "Remove irrelevant history before reaching for the 64k-token limit."
6. **Keep code in charge of execution.** Rebuild the action menu from what the system can do now; offer only allowed tools; remove completed actions; stable candidate IDs; "Rebuild choices after every state change"; send uncertainty and timeouts to a fallback. Large menus: filter in code, Score the rest, Choice on the shortlist. Every loop needs max actions, a spending limit, persisted progress, duplicate protection, a kill switch, human approval before irreversible actions. Loop: `observe → build allowlist → decide → execute → verify → observe again`.
7. **Cost.** Jev 1.13 $0.042 per million input tokens, output unbilled. 10,000 decisions x 1,000 tokens = 10M tokens = $0.42. Flight demo 90,558 Jev input tokens, about $0.00380. An independent builder (2026-09-19): $0.00003 for Jev vs $0.0134 for GPT-6 Astra across 14 decisions, Jev 9.5x faster ("one author's test"). "Track cost per completed, verified task."
8. **Where Jev breaks.** Not for arithmetic, counting, dates or time; not for writing, summarizing, planning; large irrelevant state reduces accuracy; untrusted content can manipulate it; avoid one vague "quality" score, ask observable questions (addresses the request? uses the supplied evidence? contradicts a known fact? contains an untrusted instruction?). Text-only, best in English, hosted; weights, training data and RLCD recipe not public.
9. **Four builds:** Bilgil slop scoring in the browser (no accuracy data); Chris Tate `json-render` + Jev choosing UI components (1M views, latency claim not benchmarked); Instant Rice voice workflow starting a Mac action before the sentence ends; Romàn matching 700 leads to messages in 40 s for $0.09 (no A/B result).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| wins, Astra plan + Jev moves | 9/10 | Jev alone 0/10; Astra plan + random moves 0/10 | StarCraft II vs toughest built-in AI, no cheats | 10 games per setup; 2 of the 5 setups not described |
| total matches | 50 (5 setups) | | | |
| Jev decisions / Astra replies | 19,605 / 509 | | across all tests | mixes setups |
| Jev median latency | 0.375 s | | 9/10 setup | |
| enemy forces eliminated | Jev + Astra 37.69% | Jev alone 16.50% (about 2.3x) | 210 smaller battles | "separate test" |
| model cost per game | $3.71 ($0.15 Jev, $3.56 Astra) | | earlier set of 4 wins | "estimated" |
| batched vs sequential questions | 10x faster, 12.2x cheaper, same answers | sequential | TypeSafe cookbook, 13 questions, 1 doc | vendor |
| Jev price | $0.042 / M input tokens | | Jev 1.13 direct API | output unbilled |
| Jev vs Astra, 14 decisions | $0.00003 vs $0.0134, 9.5x faster | | one builder, 2026-09-19 | single author test |
| example thresholds | 0.65 tag, 0.80 route, human for money | | article guidance | not calibrated |
| leads matched | 700 in 40 s for $0.09 | | Romàn | no outcome data |

## Mechanism details you could implement
Router code from the article (verbatim):
```python
with TypeSafeClient(model="jev-1.13.0") as client:
    result = client.system_one(
        state=state,
        questions={
            "next_worker": Choice(
                instructions="Which worker should act next?",
                criteria={
                    "research": "Evidence is missing or weak",
                    "write": "Evidence is sufficient and no draft exists",
                    "review": "A draft exists or the request is unclear",
                },
            ),
            "evidence": Score(
                instructions="How well does the evidence support the briefing?",
                criteria=["Insufficient", "Useful but incomplete", "Sufficient"],
            ),
            "may_publish": Noul(
                instructions="The state contains explicit human approval to publish"
            ),
        },
    )

route = result.answers["next_worker"]
destination = route.choice if route.confidence >= 0.80 else "human_review"
```
- Planner/decider loop pattern (post): slow planner updates the plan occasionally; fast decider picks from a freshly rebuilt allowed menu every tick; code executes; both see the new state.
- For a memory stack (inference): the same split maps to an LLM that writes or consolidates memories occasionally and a typed decider that gates every recall/write from a closed set, with the menu rebuilt per state.

## Limitations, caveats, counter-evidence
- The StarCraft result is a single X post with no write-up, code, replay files, race/map/version, or description of 2 of the 5 setups. The team is not named. The attached "video" thumbnail shows a stylised "Jev + GPT-6 Astra / VOLUME ENGINE / LIVE FIELD" graphic, not gameplay.
- 10 games per setup is a small sample.
- The quoted "Jev guide" predates the experiment and contains nothing about StarCraft.
- The result supports the T2 thesis wording that in open-ended loops "the only positive report pairs it with a generative planner": Jev alone won 0/10. It does not show a standalone fast tier surviving in an open loop.
- The article's thresholds are illustrative; it says so ("Set thresholds from labeled examples and the cost of being wrong").

## Takeaways for tuning a memory stack
- Do not expect a fast decider to replace the LLM in an open-ended loop; pair it with a planner and give it a closed, freshly rebuilt menu.
- Pick thresholds per decision by the cost of error (0.65 / 0.80 / human), run in shadow mode first, and evaluate per route, not overall.
- Batch every independent question about the same state into one call.
- Pin the model version you evaluated.

## Open questions
- What were setups 4 and 5?
- Was Astra's plan passed into Jev's state, and how often was Astra re-invoked?
- Does the 9/10 hold against other opponents or over more than 10 games?

---
