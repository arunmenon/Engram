# Images transcribed

Transcriptions of the images in `evidence/media/` (26 in the original pass; 28 more files, 18 of them unique, added in the "Added 2026-09-26" section at the end): 18 attached to X posts cited as trend evidence in `reports/trends.md`, plus 8 embedded in two X Articles (see the "X Article images" section at the end). Each image was opened and read directly. Post text comes from `raw/evidence.json`; attachments and alt_text were checked against `raw/x_api_responses.json` (every media_key maps to the tweet id in its filename). Numbers that could not be read are marked "illegible". Where a chart value was read off an axis rather than printed, it is marked "approx.".

Only two images carry alt_text: `media/2103484608666829161-3_2103484605944803328.jpg` and `media/2103485602683355331-3_2103485599260737536.jpg`. All others have `alt_text: null`.

## Index

| file | handle | post URL | trend | what it shows (one line) |
| --- | --- | --- | --- | --- |
| media/2103449596819316742-3_2103449254731894784.jpg | @Muskanjain0401 | https://x.com/Muskanjain0401/status/2103449596819316742 | Decision models as the memory control plane | Hand-drawn chat where Jev keeps/drops each line; dropping "How about indian food?" breaks the meaning of "i love that stuff" |
| media/2103321890190491710-3_2103318655237017600.jpg | @typesafeai | https://x.com/typesafeai/status/2103321890190491710 | Typed-decision tier displacing LLM calls | Deel summary card: up to 59x cheaper, up to 4x faster, 6 of 8 quality checks at parity or better |
| media/2103321892421865838-3_2103318729505566720.jpg | @typesafeai | https://x.com/typesafeai/status/2103321892421865838 | Typed-decision tier displacing LLM calls | Bar chart: cost per decision vs frontier LLM, 59x / 49x / ~45x / 20x across 4 Deel tasks |
| media/2103321894661595551-3_2103318813655838720.jpg | @typesafeai | https://x.com/typesafeai/status/2103321894661595551 | Typed-decision tier displacing LLM calls | Bar chart: response-time speedup, 4x (live shadow) / 2.8x / 1.9x (offline) / parity |
| media/2103321896553210029-3_2103318942781698048.jpg | @typesafeai | https://x.com/typesafeai/status/2103321896553210029 | Typed-decision tier displacing LLM calls | Diverging bar chart: accuracy change in points, +36 to -16.6 across 8 checks |
| media/2103490167248212384-3_2103489775915376641.jpg | @tazr_dev | https://x.com/tazr_dev/status/2103490167248212384 | Typed-decision tier displacing LLM calls | Table of 6 Jev-style jobs in a coding agent with outcome, verdict and fire count |
| media/2103501823214780888-3_2103501739702050816.jpg | @rbro112 | https://x.com/rbro112/status/2103501823214780888 | Typed-decision tier displacing LLM calls | Eval UI: artifact evaluator PASS 1.00, LLM evaluator FAIL 0.00 with a written explanation |
| media/2103502247082766500-3_2103502233845604352.jpg | @rbro112 | https://x.com/rbro112/status/2103502247082766500 | Typed-decision tier displacing LLM calls | seer-evals PR bot table for malicious_issue_detection: 1,020.46 s head vs 847.24 s base |
| media/2103500863243460898-3_2103500857094688769.jpg | @kaixin_tai | https://x.com/kaixin_tai/status/2103500863243460898 | Typed-decision tier displacing LLM calls | Datadog Experiments page with six JEV_* evaluator metrics over 10 records |
| media/2103046874496172478-3_2103046868192075776.jpg | @sergeonsamui | https://x.com/sergeonsamui/status/2103046874496172478 | Memory that updates on read | Hippo-memory GitHub README: R@5 74.0% LongMemEval BM25-only; Jev reranker R@1 0.41 to 0.62; one retracted claim |
| media/2103285929846980736-3_2103285773135233024.jpg | @SakanaAILabs | https://x.com/SakanaAILabs/status/2103285929846980736 | Frozen-model self-improvement through harness and skills | Sakana RSI Lab timeline 2024 to 2026: LLM², AI Scientist v1/v2, DGM, ShinkaEvolve, ALE-Agent, Digital Red Queen, Nature |
| media/2103149797545013312-3_2103149712010559489.jpg | @SakanaAILabs | https://x.com/SakanaAILabs/status/2103149797545013312 | Frozen-model self-improvement through harness and skills | Portrait card welcoming Jürgen Schmidhuber as Chief Scientific Advisor |
| media/2103477899814924357-3_2103477776250810368.jpg | @vigram_void | https://x.com/vigram_void/status/2103477899814924357 | Frozen-model self-improvement through harness and skills | RRSI paper figure: evolve-split vs OOD gain scatter, plus held-out scores H0 / prior / RRSI on 3 benchmarks |
| media/2103477902423806251-3_2103477852570288128.jpg | @vigram_void | https://x.com/vigram_void/status/2103477902423806251 | Frozen-model self-improvement through harness and skills | RRSI schematic of one round: harness, proposer, leakage critic, evaluate, selection gate, rejected |
| media/2103478376983871562-3_2103248513471578112.jpg | @Benzinga | https://x.com/Benzinga/status/2103478376983871562 | RSI as an explicit oversight object | AI-generated robot-welder illustration with headline "Anthropic Warns AI Could Soon Build Better Versions Of Itself" |
| media/2103484608666829161-3_2103484605944803328.jpg | @EmmieHine | https://x.com/EmmieHine/status/2103484608666829161 | RSI as an explicit oversight object | Cover card "CHINA AI BULLETIN 12" (no data) |
| media/2103485602683355331-3_2103485599260737536.jpg | @AyushSin164510 | https://x.com/AyushSin164510/status/2103485602683355331 | RSI as an explicit oversight object | Three-card diagram of Amodei's three-step pacing plan; RSI "speed limit" sits in step 3 |
| media/2103493904830259709-3_2103493900836933632.jpg | @sahilkapur | https://x.com/sahilkapur/status/2103493904830259709 | RSI as an explicit oversight object | Text excerpt naming the first 10 House co-sponsors (includes Ocasio-Cortez and Khanna) |
| media/article-3_2103228826507497472.jpg | @Vectorizeio | https://x.com/Vectorizeio/status/2103230262607761659 | Decision models as the memory control plane | X Article cover: listwise Jev "rank" Choice, 250 options in 1 request, top-6 probabilities 0.41 to 0.06 |
| media/article-3_2103278997534916608.jpg | @DhravyaShah | https://x.com/DhravyaShah/status/2103314339239428201 | Decision models as the memory control plane | X Article cover: "I played with jev. it changes memory" (no data) |
| media/article-3_2103308612085174272.jpg | @DhravyaShah | https://x.com/DhravyaShah/status/2103314339239428201 | Decision models as the memory control plane | Table of the 8 chunking methods compared: what each does and which external API it calls |
| media/article-3_2103298687330119680.jpg | @DhravyaShah | https://x.com/DhravyaShah/status/2103314339239428201 | Decision models as the memory control plane | Scatter of rerankers on BEIR SciFact: nDCG@10 vs USD per query (log); Jev Score-10 measured at $0.00133/query |
| media/article-3_2103298194042163200.jpg | @DhravyaShah | https://x.com/DhravyaShah/status/2103314339239428201 | Decision models as the memory control plane | Claude Code terminal: supermemory hooks load 10 memories at SessionStart and recall 5 memories (242 tok) at UserPromptSubmit |
| media/article-3_2103311341222256640.jpg | @DhravyaShah | https://x.com/DhravyaShah/status/2103314339239428201 | Decision models as the memory control plane | Bar chart of chunking hit@1 at 160 and 320 chars; both Jev chunkers score 93% at 320 chars |
| media/article-3_2103310683777753088.jpg | @DhravyaShah | https://x.com/DhravyaShah/status/2103314339239428201 | Decision models as the memory control plane | Heatmap: answer found within a 640-char budget, by format (3) and language (6), for 8 chunkers |
| media/article-3_2103302515525931008.jpg | @DhravyaShah | https://x.com/DhravyaShah/status/2103314339239428201 | Decision models as the memory control plane | The same Indian/Mexican food Jev keep/drop diagram as media/2103449596819316742-3_2103449254731894784.jpg |
| media/2103554329139417547-13_2103551832333099008.jpg | @mika_systems | https://x.com/mika_systems/status/2103554329139417547 | Typed-decision tier displacing LLM calls | Video thumbnail: stylised "Jev + GPT-6 Astra / VOLUME ENGINE / LIVE FIELD" storm render with telemetry panels; no StarCraft footage or game data |
| media/2103513608399532143-13_2103485515614056448.jpg | @supermemory | https://x.com/supermemory/status/2103513608399532143 | Consolidation as a separate phase from ingestion | Video thumbnail: white frame, label "DREAMING", caption "when you go quiet, it dreams" (no data) |
| media/linked-13_2103485515614056448.jpg | @supermemory | https://x.com/supermemory/status/2103513608399532143 | Consolidation as a separate phase from ingestion | Byte-identical copy of the row above (linked from @DhravyaShah) |
| media/article-3_2101680910726737920.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | X Article cover: "JEV | FIELD GUIDE, FROM SETUP TO FIRST AGENT", "9-STEP BLUEPRINT", steps 1 to 9 (no data) |
| media/article-3_2101653152218947584.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Illustration: loop of cards eye, card tray, decision diamond (check/X), lever, checked document, plus a stop sign with a toggle (no text) |
| media/article-3_2101652984014721024.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Illustration: paper tape into a box tagged 1, 2, 2, 3 with three chutes; two end in X, one (pink path) in O (no text) |
| media/article-3_2101683694003994625.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | UI crop: "Join Our Waitlist", "Get early access to Jev", email field, submit |
| media/article-3_2101654948429672448.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Illustration: four-panel sheet (calculator and flowchart; bars and bell curve; handwritten notes and graph; envelope with fingerprint and person icon), no legible text |
| media/article-3_2101652984597729280.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Illustration: code printout under a magnifier, decision tree, shaded bell curve, triangle stamp; text illegible |
| media/article-3_2101652984815910912.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Illustration: database on a clipboard fanning out to five tags (tree, bars, check/X, shield, person); tag text illegible |
| media/article-3_2101652984023126016.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Illustration: code printout and three tags (checkbox list, ranked 1-2-3 bars, pie chart) wired into a two-slider switch box; code illegible |
| media/article-3_2101652984799150080.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Illustration: terminal printout then four checked steps (gear, cloud, share, document) leading to an envelope with a key (no text) |
| media/article-3_2101654479032455168.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Notebook: pseudo-code argmax and u - λ*r > thresh selection, E[v], Var[v], CE = E[v] - λ·Var[v]; option cards OPT A to OPT L, B/D/G/J ticked |
| media/linked-3_2101653152218947584.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101653152218947584.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2101652984014721024.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101652984014721024.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2101683694003994625.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101683694003994625.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2101654948429672448.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101654948429672448.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2101652984597729280.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101652984597729280.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2101652984815910912.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101652984815910912.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2101652984023126016.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101652984023126016.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2101652984799150080.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101652984799150080.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2101654479032455168.jpg | @mika_systems | https://x.com/mika_systems/status/2101686148338798610 | Typed-decision tier displacing LLM calls | Byte-identical copy of media/article-3_2101654479032455168.jpg (fetched via raw/linked_posts.json) |
| media/linked-3_2090499054585192449.jpg | @rvaniaaaa | https://x.com/rvaniaaaa/status/2090512486738845784 | Staleness and provenance as the core memory-write problem | Screenshot of Karpathy's llm-wiki.md gist page: 5,000+ stars, 5,000+ forks, "LLM Wiki" |
| media/linked-3_2097408592064442368.jpg | @slash1sol | https://x.com/slash1sol/status/2098013767627837827 | Staleness and provenance as the core memory-write problem | PICTURE 1 table: GPT-6 Astra vs Kimi K3 (release, context, price, weights, parallelism, access, cyber) |
| media/linked-3_2097409052695261184.jpg | @slash1sol | https://x.com/slash1sol/status/2098013767627837827 | Staleness and provenance as the core memory-write problem | PICTURE 2 bars: ARC-AGI-3 semi-private, 99.9% (provider adapter harness) vs 62.7% (ARC Prize standard harness) |
| media/linked-3_2097409223877607424.jpg | @slash1sol | https://x.com/slash1sol/status/2098013767627837827 | Staleness and provenance as the core memory-write problem | PICTURE 3: Astra one agent deep (40 min per OSWorld task, $50/M out) vs K3 swarm (~4,000 steps, $15/M out) |
| media/linked-3_2097409360527769600.jpg | @slash1sol | https://x.com/slash1sol/status/2098013767627837827 | Staleness and provenance as the core memory-write problem | PICTURE 4 table: 8 jobs, 3 won by Astra and 5 by K3, with the reason for each |
| media/linked-3_2097409501217304577.jpg | @slash1sol | https://x.com/slash1sol/status/2098013767627837827 | Staleness and provenance as the core memory-write problem | PICTURE 5 flow: Spec, K3 Agent Swarm, Astra gate, Deliverable |

---

# Trend: Decision models as the memory control plane

## Post: @Muskanjain0401, https://x.com/Muskanjain0401/status/2103449596819316742

- Evidence item: "Supermemory tests Jev across reranking, chunking, pre-extraction filtering and the recall/no-recall gate; reports up to 58% token reduction" (2026-09-25)
- Role in evidence.json: `post`
- Full post text:

> banger research just dropped!!🫪
>
> @DhravyaShah tested jev, @typesafeai's new decision model, across the whole memory pipeline: reranking, chunking, filtering context before extraction, and deciding when an agent should recall at all.
>
> did you know jev can cut 58% of the tokens going into memory extraction, but dropping one line like "how about indian food?" can turn "i love that stuff" into a memory about mexican food? decision models are insanely fast at yes/no calls and still need the full context to judge meaning.
>
> that's why @supermemory leans on learner-1, a small specialized model that makes observation cheap enough to skip the risky cut entirely :)

### `media/2103449596819316742-3_2103449254731894784.jpg`

alt_text: none.

Hand-drawn (Excalidraw-style) diagram. A rounded box holds a three-turn chat; each span is colour-highlighted, and a legend column on the right headed "Jev" gives Jev's keep/drop verdict per colour.

| Speaker | Highlighted span (verbatim) | Colour | Jev verdict |
| --- | --- | --- | --- |
| user | "Hey, i wanna eat!" | green | yes |
| assistant | "How about indian food?" | blue | no |
| assistant | "you have also been loving mexican food, so indian is worth trying." | yellow | yes |
| user | "i love that stuff. let's do it." | purple | yes |

Flow the diagram implies:
1. Jev scores each span yes (keep for extraction) or no (drop).
2. The assistant's proposal "How about indian food?" is scored "no" and dropped.
3. What remains mentions only Mexican food as a food the user loves, followed by "i love that stuff".
4. An extractor working on the filtered context would bind "that stuff" to Mexican food, which is the wrong memory.

What the image adds: the concrete failure. The post describes it in words; the image shows the exact per-span verdicts that produce it. The failure is a pre-extraction filter (write path) error, not a recall error. It contains no numbers; the 58% figure appears only in the post text.

Contradictions / caveats vs trends.md: trends.md says "reports up to 58% token reduction". The post says "can cut 58%", not "up to". The image argues against using Jev as a pre-extraction filter on its own, since the post concludes Supermemory "leans on learner-1" to "skip the risky cut entirely". So this item is partly counter-evidence for the thesis that extraction decisions move onto a decision model. The poster is @Muskanjain0401, not Supermemory; the research is attributed to @DhravyaShah.

---

# Trend: Typed-decision tier displacing LLM calls on bounded classification

## Post thread: @typesafeai on Deel (4 images)

- Evidence item: "Deel: repeat-question matching 70→97%, expense categorization 50→86%, up to 4× faster on shadowed live traffic" (2026-09-25), cited post https://x.com/typesafeai/status/2103321894661595551
- Attachment check: x_api_responses.json confirms each image belongs to the tweet in its filename. The images are a carousel spread over the thread, so each image does not always match the text of its own tweet. The "70% → 97%" text is attached to the speed chart, and the "up to 4×" speed text is attached to the quality chart.

### Post: https://x.com/typesafeai/status/2103321890190491710 (thread head)

> Observe the art of the @deel.
> And they came with receipts 💅
> Keep reading to find out how it's done. https://t.co/mW7FxGvCbI

#### `media/2103321890190491710-3_2103318655237017600.jpg`

alt_text: none.

Dark summary card.

- Title: "Right-sized models, production results"
- Subtitle: "4 AI use cases at Deel. Same task, same data, specialised classifier vs what runs today."

| Headline figure | Label |
| --- | --- |
| up to 59× | cheaper per decision |
| up to 4× | faster responses |
| 6 of 8 | quality checks at parity or better |

- Footer line 1: "Analytics · Support triage · Ticket classification · Expense categorisation"
- Footer line 2: "Head-to-head evals on real Deel data · TypeSafe Jev vs frontier LLMs"

What it adds: the 59× cost figure (the post text gives no cost number) and the "6 of 8" framing. That framing implies 2 of the 8 quality checks came out worse, which the post text never says.

### Post: https://x.com/typesafeai/status/2103321892421865838

> Some great use cases they measured:
> • Matching repeat analytics questions to approved answers
> • Picking 1 of 36 metrics
> • Blocking PII requests
> • Deciding when a support chat needs a human
> • Tagging tickets across a 3-level taxonomy
> • Sorting expenses into about 55 categories
> Every one is a pick from a known set.

#### `media/2103321892421865838-3_2103318729505566720.jpg`

alt_text: none.

Horizontal bar chart.

- Title: "How much cheaper"
- Subtitle / axis meaning: "Cost per decision, relative to the frontier LLM in use today"

| Task | Cost reduction vs frontier LLM |
| --- | --- |
| Analytics: picking the right metric | 59× |
| Support: escalate-to-human detection | 49× |
| Support: root-cause ticket tagging | ~45× |
| Analytics: PII guardrail | 20× |

- Footnote: "Root-cause figure estimated from per-token pricing."
- Footer: "Head-to-head evals on real Deel data · TypeSafe Jev vs frontier LLMs"

What it adds: per-task cost multipliers, 20× to 59×. The ~45× figure is estimated from pricing, not measured. Expense categorisation has no cost bar.

### Post: https://x.com/typesafeai/status/2103321894661595551 (the post trends.md cites)

> Jev generally out-performed frontier LLMs at a fraction of the price:
> Repeat-question matching: 70% → 97%
> Expense categorization: 50% → 86% (vs human reviewers)
> Escalation: same catches, fewer false alarms https://t.co/tBg4CIigz0

#### `media/2103321894661595551-3_2103318813655838720.jpg`

alt_text: none.

Horizontal bar chart.

- Title: "How much faster"
- Subtitle / axis meaning: "Response time, relative to the frontier LLM in use today"

| Task | Speedup vs frontier LLM |
| --- | --- |
| Support: escalation detection (live shadow) | 4× |
| Analytics: picking the right metric | 2.8× |
| Support: escalation detection (offline test) | 1.9× |
| Analytics: PII guardrail | parity (grey bar) |

- Footnote: "Live shadow: thousands of production conversations, run in parallel with the current model."
- Footer: "Head-to-head evals on real Deel data · TypeSafe Jev vs frontier LLMs"

What it adds: "up to 4×" covers one task only (escalation, live shadow). The same task scored 1.9× offline, and PII guardrail showed no speedup. The live-shadow sample is only "thousands of production conversations", with no exact count.

Contradiction: the next post in the thread says "Offline tests: 2 to 3×". The chart's offline escalation figure is 1.9×, just under that range. (2.8× for metric picking is inside it.)

### Post: https://x.com/typesafeai/status/2103321896553210029

> Speed was measured while shadowing live production traffic: up to 4× faster. Offline tests: 2 to 3×. https://t.co/SmlSLmW4rl

#### `media/2103321896553210029-3_2103318942781698048.jpg`

alt_text: none.

Diverging horizontal bar chart around a zero line.

- Title: "Where quality landed"
- Subtitle / axis meaning: "Accuracy change vs current approach, in points"

| Check | Accuracy change (points) |
| --- | --- |
| Expense categorisation* | +36 |
| Analytics: repeat-question matching | +26.7 |
| Analytics: declining when no answer exists | +8.3 |
| Analytics: metric pick, well-formed questions | +2 |
| Support: escalations caught (with fewer false alarms) | parity |
| Analytics: PII guardrail (100% both) | parity |
| Support: 3-level root-cause tagging | -3.6 (red) |
| Analytics: metric pick, messy real questions | -16.6 (red) |

- Footnote: "*vs today's rule-based receipt matching. All others vs the frontier LLM on the same task."
- Footer: "Head-to-head evals on real Deel data · TypeSafe Jev vs frontier LLMs"

What it adds: the two regressions (-3.6 and -16.6) behind the "6 of 8". The +26.7 and +36 point deltas match the post's 70→97 and 50→86.

Contradictions vs post and trends.md:
1. The post says expense categorization is "vs human reviewers". The chart footnote says expense is "vs today's rule-based receipt matching". So the 50→86 gain is not against a frontier LLM, and not clearly against humans.
2. "Jev generally out-performed frontier LLMs" leaves out that on messy real metric-pick questions, the case closest to open-ended input, Jev was 16.6 points worse. This supports the trend's own caveat that results get worse as inputs get less bounded.
3. The trends.md evidence line quotes only the two best numbers. The regressions are not recorded.

## Post: @tazr_dev, https://x.com/tazr_dev/status/2103490167248212384

- Evidence item: "Counter-evidence: 6 Jev-style fast actions tested in a coding agent and none survived; the decision was "too unreliable"" (2026-09-25)
- Role: `post`. It quotes https://x.com/tazr_dev/status/2103318291456610667.
- Full post text:

> I tested 6 Jev-style fast actions in tack coding agent yesterday.  None survived.
>
> I'm going to survey what's out there before taking another pass.
>
> Biggest blocker is d/jev is too unreliable, and the next step up is the actual agent. https://t.co/Kfm8QglCTX https://t.co/9kRapfIuB7

### `media/2103490167248212384-3_2103489775915376641.jpg`

alt_text: none.

Monospace terminal-style table (verbatim):

| Job | What it does | Outcome | Verdict | Count |
| --- | --- | --- | --- | --- |
| rank | picks next ready item | reordered 10 of 15 real choices | unproven | 60 |
| gate | do step, or re-plan | 4 of 8 re-plans changed the plan | costly, mixed | 19 |
| intent | new goal vs steering | 5 real routings, all plausible | little effect | 18 |
| suff | "is the plan enough?" | 2 of 6 flagged a re-plan | unproven | 6 |
| met | "is the goal done?" | p rose before each goal closed | promising | 7 |
| reflex | react to failed cmd | never fired | untested | 0 |

What it adds: per-job fire counts (110 in total) and verdicts. The post gives neither.

Contradictions vs trends.md:
1. "6 ... tested and none survived" overstates the result. `reflex` never fired (count 0, "untested"), so only 5 were exercised.
2. `met` is rated "promising", and the thread says "REPLAN still looks good to me". The verdicts are "unproven / mixed / little effect", mostly for lack of data, not measured failures. The thread says "GATE and SUFF need more data".
3. "Too unreliable" refers to d/jev as the tier; the table records no reliability metric (no accuracy or error rate). Weak counter-evidence: small samples (6 to 60 fires), not a clean negative result.

## Post thread: @rbro112 (Jev as eval judge)

- Evidence items: (a) "One week of Jev replacing Gemini 3.1 as a pass/fail eval judge: no meaningful accuracy change, ~200× cheaper ($0.01→$0.00005), ~50× faster (10 s→0.2 s median); cost is the judge's lost written reasoning", cited post https://x.com/rbro112/status/2103501576405172326 (no image). (b) "A second team independently reports that judge latency (10 s vs 0.2 s) decides whether evals run sparingly or become a gate on every PR", cited post by @hamzaashergill https://x.com/hamzaashergill/status/2103508434863657236 (no image). Both images are replies in rbro112's thread and appear as `thread` entries under both items.
- Head post text (2103501576405172326):

> It's been a week since I moved one of eval datasets from Gemini 3.1 to Jev by @typesafeai for LLM judging. The results so far:
>
> - No meaningful change in scoring accuracy
> - ~200× cheaper (~$0.01 → ~$0.00005 per judge)
> - ~50× faster (~10s → ~0.2s median)
> - ~50% fewer input tokens, 87% fewer output tokens
>
> But not everything's perfect, more details in the thread

### Post: https://x.com/rbro112/status/2103501823214780888

> Jev isn't an LLM, requiring us to change our judging to classify conclusions as pass/fail. We had to set probability thresholds for the pass/fail (what Jev calls nouls), as Jev's answers are always probabilities.
>
> The biggest loss is evidence when scores change (duh, it's not an LLM). I and other devs use this to help explain scoring changes:

#### `media/2103501823214780888-3_2103501739702050816.jpg`

alt_text: none.

Dark eval-UI panel headed "Evaluator Scores" (collapsible).

| Evaluator | Result | Score |
| --- | --- | --- |
| AutofixRcaArtifactEvaluator | PASS | 1.00 |
| AutofixRcaLlmEvaluator | FAIL | 0.00 |

Text under AutofixRcaLlmEvaluator (verbatim):

> The candidate RCA describes a KeyError related to 'unit_price' and 'price' in order_total, while the expected RCA describes an IndexError in reports.p95_latency due to an empty list from metrics.recent_latencies. The candidate completely misses the actual cause.

What it adds: a concrete sample of the written reasoning lost when an LLM judge is replaced. It also shows two evaluators disagreeing on one case: the artifact check passes and the LLM check fails. The dataset appears to be Autofix root-cause analysis. This is the pre-Jev (LLM judge) output, not a Jev result. Later in the thread (2103516147819987105), failed cases are passed back to an LLM for explanation, so the reasoning is not fully lost.

### Post: https://x.com/rbro112/status/2103502247082766500

> But perf improvements are the most impactful boost for us. Some of our existing datasets that don't use Jev take around ~15min (some longer!), making it tough to run on a PR.
>
> Speed is critical for us so we can run evals and not block our devs. Waiting 15 minutes+ on a PR is a productivity drain. This dataset is my next Jev target 👀

#### `media/2103502247082766500-3_2103502233845604352.jpg`

alt_text: none.

GitHub PR comment by "seer-evals" (Bot), "commented 2 days ago · edited". Status "Completed". Heading: "malicious_issue_detection (Comparison)".

| Run | Passed | Failed | Errored | Cost | Tokens | Duration |
| --- | --- | --- | --- | --- | --- | --- |
| Head | 304 | 2 | 0 | $0.14 | 379.5k | 1,020.46s |
| Base | 305 | 1 | 0 | $0.20 | 381.2k | 847.24s |
| Diff | -1 (red) | +1 (red) | 0 | -$0.06 (green) | -1.7k | +173.22s (red) |

What it adds: the actual baseline for "~15min". This non-Jev dataset takes 847 to 1,020 s (14.1 to 17.0 min) for 306 cases. Cost is only $0.14 to $0.20 per full run, so for this dataset latency matters far more than money. The figures come from an LLM-judged dataset and say nothing about Jev directly.

Caveat for evidence item (b): these screenshots come from rbro112, not from @hamzaashergill. Hamza's "we found the same" has no image or numbers behind it, so "a second team independently reports" rests on an unquantified reply.

## Post: @kaixin_tai, https://x.com/kaixin_tai/status/2103500863243460898

- Evidence item: "Datadog agent observability runs online and offline evals with Jev as the judge" (2026-09-25)
- Full post text:

> run cheap and fast online and offline evals with jev in datadog agent observability https://t.co/Q9qUx4mMRV

### `media/2103500863243460898-3_2103500857094688769.jpg`

alt_text: none.

Datadog "Experiments" page. Experiment name "support-agent-judged-by-jev-1789840964284", badge "1 RUN". Breadcrumb: "support-agent-judged-by-jev-1789840964284 → No comparable experiments". Buttons: "Set as Baseline", "View Related", "View Details".

Summary metric tiles:

| Metric | Headline value | Chart type |
| --- | --- | --- |
| JEV_AGREES_WITH_LABEL | 90% true | donut |
| JEV_ANSWERS_QUESTION | 0.528 avg | histogram, x axis 0 to 1 (ticks 0.5, 1), y axis 0 to 3 |
| JEV_CUSTOMER_IMPACT | 0.641 avg | histogram, x ticks 0.5, 1, y axis 0 to 3 |
| JEV_FAILURE_MODE | 90% none | donut |
| JEV_GROUNDED | 0.911 avg | histogram, x ticks 0.6, 0.8, 1, y axis 0 to 4 |
| JEV_HANDLED_CORRECTLY | 90% true | donut (tile cut off at right edge) |

Histogram bar heights (approx., read from axes): ANSWERS_QUESTION has one bar of 3 near 0 to 0.1, a plateau of 1 to about 0.7, a bar of 2 near 0.75 to 0.85, and 1 near 0.85 to 1. CUSTOMER_IMPACT has 3 near 0 to 0.1, 1 from about 0.1 to 0.5, a gap, 2 near 0.9 to 1.1, and 1 just above that. GROUNDED has 1 at about 0.6, 2 at about 0.65 to 0.7, 1 across 0.7 to 0.9, and 4 at about 0.95.

Records tab (tabs: Records, Config, Data Explorer, Tool Analysis PREVIEW). "10 records"; facet panel "Showing 3 of 9", Trace Status OK = 10, Span Errors in Trace min 0 max 0. Visible rows:

| RECORD ID | STATUS | JEV_AGREES_WITH... | JEV_ANSWERS_QU... | JEV_CUSTOMER_I... | JEV_FAILURE_MODE | JEV_GROUNDED |
| --- | --- | --- | --- | --- | --- | --- |
| cc24c434-de37-4a09-a1ba-6e0865b119ab | (blank) | true | 0.020 | 0.910 | none | 0.970 |
| 1bf7242f-b2f3-4844-95b7-09d030d2b624 | (blank) | true | 0.990 | 0.020 | none | 0.970 |
| c93bebed-af75-4e38-a895-e7a279ee4b06 | (blank) | false | 0.330 | 1.100 | none | 0.910 |
| aaf6b936-710b-4c30-a2e9-ab8b4723873c | (blank) | true | 0.020 | 1.060 | none | 0.910 |

Footer: "Copyright Datadog, Inc. 2026 - 35.139081205".

What it adds: Jev returns typed outputs, not only pass/fail. There are booleans (agrees_with_label, handled_correctly), a category (failure_mode) and continuous scores. The run is tiny: 10 records, one run, no baseline. No cost or latency is shown, so "cheap and fast" is not backed by this image.

Anomaly: JEV_CUSTOMER_IMPACT values of 1.100 and 1.060 exceed 1, so that metric is not a probability, even though rbro112 says Jev answers are always probabilities. It may be a regression-style or differently scaled output. Treat it with care.

---

# Trend: Memory that updates on read

## Post: @sergeonsamui, https://x.com/sergeonsamui/status/2103046874496172478

- Evidence item: "Hippo-memory: decay, retrieval strengthening and consolidation; LongMemEval R@5 = 74% with BM25 only" (2026-09-24)
- Full post text:

> Hippo-memory: biologically-inspired memory layer for AI agents with decay, retrieval strengthening, and consolidation. TypeScript, SQLite, zero runtime deps, MCP support for @claudeai Code and @cursor_ai. Hits R@5 = 74% on LongMemEval with just BM25.
>
> https://t.co/5T0LVkDffx https://t.co/m1KRZFYa7J

### `media/2103046874496172478-3_2103046868192075776.jpg`

alt_text: none.

Screenshot of the GitHub README for `kitfunso / hippo-memory`: ⭐ 756, language TypeScript. Watermark: "GITHUB.COM/KITFUNSO/HIPPO-MEMORY".

Header: "🦛 Hippo". Tagline (bold): "The secret to good memory isn't remembering more. It's knowing what to forget." Badges: "npm v1.45.0", "license MIT", "website hippo-memory.com". A broken image link reads "hippo init --scan ~ — initializing memory across all repos".

Intro (verbatim): "A memory layer for AI agents. Modeled on the hippocampus. Decay by default, strength through use, provenance on every memory. SQLite under the hood, zero runtime deps, works with every CLI agent you have."

Code block (verbatim):

```
npm install -g hippo-memory && hippo init --scan ~
```

"One command. Every git repo on your machine gets memory."

Config block (verbatim; the last line is cut off at the right edge):

```
Works with:    Claude Code, Codex, Cursor, OpenClaw, OpenCode, Pi, any MCP client
Imports from:  ChatGPT, Claude (CLAUDE.md), Cursor (.cursorrules), Slack, markdown
Storage:       SQLite backbone with markdown mirrors. Git-trackable, human-readable.
Dependencies:  Zero runtime deps. Node.js 22.16+. Optional embeddings: bring-your-own local Transformers.js (`npm
```

"Why this exists" (verbatim):

> Most "AI memory" systems save everything and search later. That's storage with semantic search bolted on. It's why your agent kept hitting the same deploy bug last week. And the week before. The system saw the failure four times. It had no way to know it should remember.
>
> Hippo applies the thing brains have been getting right for 500 million years. Memories decay over time. Retrieval makes them stronger. Three biological layers (buffer, episodic, semantic) consolidate during sleep. Hard lessons stick because you used them. Trivia fades because you didn't.
>
> It also fixes the portability problem. Your ChatGPT memories don't travel to Claude. Your `.cursorrules` don't travel to Codex. Hippo is one process behind every agent. CLAUDE.md, Cursor rules, ChatGPT exports, Slack history, all in one SQLite store, all queryable from any tool that speaks MCP or HTTP.

"Receipts" (verbatim):

> Numbers, not adjectives. Every claim links to the benchmark or the test that proves it. Every measurement we have ever published is indexed in `docs/evals/`, pre-registrations kept next to their results, including the runs that failed and the one claim we retracted.
>
> - **Sequential Learning Benchmark.** benchmarks/sequential-learning/. 50 tasks, 10 buried traps. Measures whether agents learn from past mistakes, not just retrieve text. v0.11.0 informal magnitude RETRACTED v1.7.9; mechanism remains shipped. See CHANGELOG.md v1.7.9 entry.
> - **R@5 = 74.0%** on LongMemEval. 500-question industry retrieval benchmark, BM25 only, no embeddings.
> - **R@1 0.41 to 0.62 with** `hippo recall "<query>" --reranker jev` on a private 300-query developer store (full eval). The opt-in TypeSafe Jev reranker, off by default, about 0.0004 USD a recall. 2000-draw paired bootstrap; the margin held in 20 of 20 seeds and a permutation null reached it in 0 of 200 runs. Ranking only: three graded tests did **not** show a better answer rate than the free local cross-encoder, and that negative result is in the same doc. What it buys today is a shorter context, 2 memories ranked by Jev answering as well as 5 ranked by the cross-encoder.
> - **10 of 10 incident scenarios beat transcript replay** on a staged Slack corpus (benchmarks/e1.3/). Recall surfaces the cause faster than scrolling the last N messages (faded, cut off at the bottom).

What the image adds beyond the post:
1. Exact figure R@5 = 74.0% on the 500-question LongMemEval, BM25 only, no embeddings.
2. A Jev reranker result (R@1 0.41 to 0.62, about $0.0004 per recall, 300 private queries). It belongs as evidence under "Decision models as the memory control plane", with its own negative result: no better answer rate than a free local cross-encoder in three graded tests. The gain is context size (2 memories vs 5).
3. A retracted claim: the Sequential Learning Benchmark result (the one that measures learning from mistakes, the part most relevant to the "updates on read" thesis) was retracted in v1.7.9.
4. Consolidation is described as three layers (buffer, episodic, semantic) that "consolidate during sleep".

Contradictions / caveats vs trends.md: R@5 = 74% is a pure retrieval score from BM25. It does not measure the decay/strengthening mechanism that puts Hippo under this trend. The benchmark that would test read-time updating (sequential learning) is the one whose magnitude was retracted. So the image does not support the idea that read-time updating improves outcomes. The trend's own watch question (the knowledge-update and abstention subsets) is not answered here.

---

# Trend: Frozen-model self-improvement through harness and skills

## Post: @SakanaAILabs, https://x.com/SakanaAILabs/status/2103285929846980736

- Evidence item: "Sakana's RSI Lab roadmap lists LLM² and the Darwin Gödel Machine (agents rewriting their own code)" (2026-09-25)
- Full post text:

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

### `media/2103285929846980736-3_2103285773135233024.jpg`

alt_text: none.

Horizontal timeline with year markers 2024, 2025 and 2026. Branding at bottom left: "RSI Lab / sakana.ai". Milestones in chronological order:

| Date (as printed) | Milestone | Sub-label / thumbnail |
| --- | --- | --- |
| (before 2024, red dot, no date) | born in Tokyo | Sakana fish logo |
| JUN 2024 | LLM² | "DiscoPOP · Oxford / Cambridge"; illustration of a fish-headed figure typing at a laptop |
| August 2024 | AI Scientist v1 | thumbnails of three paper pages (text illegible) |
| APR 2025 | Darwin Gödel Machine | "with UBC"; diagram described below |
| April 2025 | AI Scientist v2 | pipeline diagram described below |
| AUG 2025 | ShinkaEvolve | diagram titled "ShinkaEvolve: Open-ended and sample efficient program evolution" (inner labels mostly illegible; "Problems", "LLM Ensemble", "Best Score Solution" legible) |
| DEC 2025 | ALE-Agent | "1st of 804 · AtCoder AHC058"; leaderboard thumbnail |
| FEB 2026 | Digital Red Queen | dark grid visualization (no readable text) |
| March 26, 2026 | AI Scientist in *Nature* | Nature cover dated "March 26, 2026" |

Darwin Gödel Machine diagram, as a flow:
1. Left panel "Gödel": a box "code" above "Foundation Model".
2. "Task 1: solve downstream task" (arrow out to a pencil icon).
3. "Task 2: rewrite your own code" (arrow looping back into "code").
4. Right panel "+ Darwinian Exploration": a tree of agent variants labelled "Open-ended exploration of self-improving agents".

AI Scientist v2 diagram, as a flow:
1. Idea Generation: "LLM Idea/Plan Innovation" → "Novelty Check Sem. Scholar" → "Idea scoring / archiving".
2. Tree-Based Experimentation, four stages, each with "[Write to exp. log]" and "[Select Best Node]": "1. Preliminary Idea Investigation" → "2. Baseline Hyperparameter Tuning" → "3. Research Agenda Execution" → "4. Conducting Ablation Studies".
3. Paper Write-Up: "Plotting + VLM Feedback" → "Manuscript Template" → "Manuscript" → "LLM Paper Reviewing".

ALE-Agent leaderboard thumbnail: columns Rank / User / Score. Rank 1 is highlighted in a red outline and carries the Sakana logo; the user name reads approximately "fishylene". Ranks 2 to 7 are visible. All scores and other user names are illegible at this resolution.

What it adds: dates for each milestone, "1st of 804" for ALE-Agent (the post says only "beating hundreds of human experts"), and the DGM mechanism in two tasks (solve task; rewrite own code). The "double performance" claim appears only in the post, not in the image.

Caveat vs trends.md: the image says "rewrite your own code", which matches the claim. But LLM² (DiscoPOP) is about discovering preference-optimization algorithms used to train models. That changes weights and is not frozen-model harness work, so it is a weak fit for this trend's thesis. The DGM item fits better.

## Post: @SakanaAILabs, https://x.com/SakanaAILabs/status/2103149797545013312

- Evidence item: same as above (item 19); this post is both the `referenced` post and a `thread` entry.
- Full post text:

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

### `media/2103149797545013312-3_2103149712010559489.jpg`

alt_text: none.

Announcement card. Left half: a headshot photo of a grey-haired man against a green blurred background. Right half, text: "Welcoming / Jürgen Schmidhuber, / Chief Scientific Advisor". Bottom right: "sakana.ai" with the fish logo.

What it adds: nothing beyond the post. No data, no roadmap, no technical content. Not evidence for the harness thesis.

## Post: @vigram_void, https://x.com/vigram_void/status/2103477899814924357

- Evidence item: "Google paper has agents recursively rewrite their own harness (prompts, tools, memory, control flow, subagents); a builder reads it as a warning label" (2026-09-25)
- Full post text:

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
> this is making me rethink what "self-improving agent" should mean.
>
> maybe you don't want an agent that's infinitely willing to rewrite itself.
>
> you want one with an immune system against its own cleverness.
>
> https://t.co/vexdi1cmPt

### `media/2103477899814924357-3_2103477776250810368.jpg`

alt_text: none.

Two-part paper figure.

**Panel (a): scatter plot.** X axis: "relative gain on the evolve split (%)", ticks 0, 2, 4, 6. Y axis: "relative gain on OOD held-out (%)", ticks -5, 0, 5, 10. A dashed diagonal labelled "1:1 transfer" runs from (0,0) to about (6,6). A shaded band below y = 0 is labelled "gain does not transfer". Point positions below are read off the axes (approx.); none are printed:

| Method | Evolve-split gain (%) | OOD held-out gain (%) |
| --- | --- | --- |
| RRSI (blue star) | approx. 1.2 | approx. 10 |
| Meta-Harness | approx. 4.0 | approx. 2.4 |
| Unregularized | approx. 3.8 | approx. 1.6 |
| HarnessX | approx. 2.7 | approx. 0 |
| AHE | approx. 1.5 | approx. -1.3 |
| TTHE | approx. 1.9 | approx. -4.3 |

Caption (a), verbatim: "Evolve-split gain against out-of-distribution gain, one point per method. RRSI is the only method whose gain grows out of distribution."

**Panels (b) to (d): bar charts (printed values).**

| Panel | Benchmark | H₀ (unevolved) | prior (avg of prior methods) | RRSI | y-axis floor |
| --- | --- | --- | --- | --- | --- |
| (b) Coding | SWE-bench Verified | 82.0 | 82.3 | 83.8 | 80 |
| (c) Agentic workspace | OOD avg | 39.7 | 39.4 | 43.6 | 36 |
| (d) Engineering design | Frontier-Eng | 17.7 | 17.9 | 22.0 | 14 |

Caption (b to d), verbatim: "Held-out scores for the unevolved harness H₀, the average prior method and RRSI. RRSI beats the prior average by up to 22.9%." (22.0 / 17.9 = 1.229, consistent.)

What it adds:
1. The prior-method baseline. Unregularized/prior self-improvement barely moves held-out scores (82.3, 39.4, 17.9 vs H₀ 82.0, 39.7, 17.7), and on agentic workspace it is below H₀.
2. The overfitting evidence behind "the harness starts learning the test". Unregularized methods make the larger evolve-split gains (about 3.8 to 4%) but transfer little; AHE and TTHE go negative out of distribution.
3. The bars on truncated axes (floors 80, 36, 14) make gains look larger than they are. On SWE-bench Verified RRSI is +1.8 over H₀ and +1.5 over prior.

Contradictions vs the post: the image has no Terminal-Bench panel and no 74.2 → 80.2 figure. Its third benchmark is "Agentic workspace, OOD avg" (39.7 → 43.6). The image also names no model (Claude Opus 4.8 comes only from the post) and does not show the "36% fewer policy tokens" figure. Check the Terminal-Bench numbers against the paper (https://regularized-rsi.com/) before citing them. The trends.md line does not quote numbers, so there is no direct conflict there. The figure does bear on the trend's watch question about overfitting: evolved harnesses do overfit their own eval unless regularized.

### Post: https://x.com/vigram_void/status/2103477902423806251 (thread reply)

> https://t.co/UGJF5of9hI https://t.co/DUVWDeNGPt

(The first link expands to https://regularized-rsi.com/.)

#### `media/2103477902423806251-3_2103477852570288128.jpg`

alt_text: none.

Dark schematic of one RRSI round. Top left: "round 2 / T", "incumbent score 78.1%".

Components (verbatim labels):
- **Harness Hₜ**: stacked items "prompts", "tools", "control flow", "memory", "context". Caption: "EVERY COMPONENT STAYS EDITABLE".
- **Proposer** (highlighted): "edit budget bₜ" shown as 4 squares, 3 filled; "ledger Lₜ 4 entries"; a warning chip "stall → explore untried component". Caption: "PROPOSAL-SIDE REGULARIZATION".
- **Leakage critic**: "task names, answers, benchmark logic → ✕".
- **Evaluate**: "full evolve set, k trials".
- **Selection gate**: two rules, "Ŝ(H′) ≥ S* − δ noise floor" and "ΔC ≤ β₀ + β₁·ΔS cost rule". Caption: "SELECTION-SIDE REGULARIZATION".
- **rejected**: "critic 1 · floor 1 · cost 1".

Flow:
1. Harness Hₜ sends "feedback" (dashed arrow) to the Proposer.
2. Proposer, spending from its shrinking edit budget and reading the ledger, sends "candidates" to the Leakage critic.
3. Leakage critic rejects candidates that encode task names, answers or benchmark logic (dashed arrow down to "rejected"); the rest go to Evaluate.
4. Evaluate runs the full evolve set for k trials and passes estimated score and cost "Ŝ, Ĉ" to the Selection gate.
5. Selection gate admits a candidate only if its score clears the incumbent minus the noise floor δ and its added cost ΔC stays within β₀ + β₁·ΔS. Failures go to "rejected".
6. The gate also sends "prune stale components" back (dashed arrow) toward the Proposer.
7. "Hₜ₊₁ ← best admissible candidate" returns to the Harness.

Caption (verbatim): "One round of RRSI. The proposer spends a shrinking edit budget and reads the full ledger; the critic screens for leakage before anything is scored; the gate admits a candidate only if it clears the noise floor and pays for its tokens. Schematic; the real rounds are in the explorer below."

What it adds: the formal acceptance rules behind the post's plain-language list. The noise-floor inequality and the linear cost rule (tokens must be paid for by score gain) could be reused directly in a memory-stack self-tuning loop. The 78.1% incumbent score and the "rejected 1/1/1" counts are marked in the caption as schematic, not real results.

---

# Trend: RSI as an explicit oversight object

## Post: @Benzinga, https://x.com/Benzinga/status/2103478376983871562

- Evidence item: "Anthropic proposes an industry pause framework, citing systems that could accelerate their own development faster than humans can oversee" (2026-09-25)
- Full post text:

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

### `media/2103478376983871562-3_2103248513471578112.jpg`

alt_text: none.

AI-generated editorial illustration. A humanoid robot in a red work suit and welding helmet kneels and welds in a factory, with industrial robot arms behind it and a large dark rounded tile bearing "AI" at right. Small text top centre: "ADVANCED ROBOTICS ASSEMBLY - SECTOR 4." Top right credit: "IMAGE: NANO BANANA 2". Headline across the bottom (the part after "Warns" is in blue): "Anthropic Warns AI Could Soon Build Better Versions Of Itself, Calls For Industry-Wide Pause".

What it adds: no data. It is a stock illustration labelled as AI-generated. The media_key (…2103248513471578112) is older than the tweet id, so the graphic was reused from an earlier upload.

Contradiction: the headline says Anthropic "Calls For Industry-Wide Pause", but the post body says Anthropic argued for a coordinated pause mechanism to be set up in advance, and that "fully autonomous self-improving AI systems do not yet exist". trends.md ("proposes an industry pause framework") matches the body, not the headline. Do not cite the headline.

## Post: @EmmieHine, https://x.com/EmmieHine/status/2103484608666829161

- Evidence item: "A cross-industry paper maps five RSI levels; full meta-improvement has not been demonstrated" (2026-09-25). trends.md cites post 10/ (https://x.com/EmmieHine/status/2103484702451548176), which has no image. The image is on thread post 1/.
- Full text of post 1/ (image post):

> 1/ China AI Bulletin Issue 12 is out: developments from September 9–23 (plus the Trump–Xi summit). Xi and Trump discussed AI, but no AI agreement. Also: a proposed BRICS AI open-source zone and Alibaba says Qwen3.8-Max made progress toward recursive self-improvement. 🧵 https://t.co/acNnKeFMee

- Text of cited post 10/ for context:

> 10/ A cross-industry paper maps five levels of recursive self-improvement. Its authors say full meta-improvement has not been demonstrated; the strongest established level in software engineering is still narrower, with humans setting the objective and evaluation criteria.

### `media/2103484608666829161-3_2103484605944803328.jpg`

alt_text (verbatim): "China AI Bulletin 12 cover on a dark blue background"

Cover card on a solid dark blue background. Large bold light-blue text: "CHINA AI / BULLETIN 12". Behind it, in thin grey script: "China AI Bulletin". Bottom left: "CHINAAIBULLETIN.SUBSTACK.COM". Bottom right: the Substack bookmark logo.

What it adds: nothing beyond the newsletter name and URL. There is no content on the five RSI levels. The claim rests entirely on post 10/ text.

## Post: @AyushSin164510, https://x.com/AyushSin164510/status/2103485602683355331

- Evidence item: "A proposed US–China ladder includes a SALT-style "speed limit" on RSI" (2026-09-25). trends.md cites post 6/ (https://x.com/AyushSin164510/status/2103485608408629591), which has no image. The image is on thread post 1/.
- Full text of post 1/ (image post):

> 1/ 🧭 Anthropic CEO Dario Amodei now argues AI capability growth should be deliberately slowed so safety work can keep up.
>
> Why it matters: a frontier lab CEO proposing to pace his own industry, with a concrete three-step plan. https://t.co/5k8V27tWob

- Text of cited post 6/ for context:

> 6/ Four levels of agreement with China, in order of difficulty:
>
> 1. A ban on AI for bioweapons
> 2. Pre-release testing
> 3. A "speed limit" on recursive self-improvement (he compares it to SALT)
> 4. A full pause, which he calls unlikely any time soon

### `media/2103485602683355331-3_2103485599260737536.jpg`

alt_text (verbatim): "Three-card diagram titled 'The three-step pacing plan', from Dario Amodei's essay 'We Must Pace the Frontier', September 2026. Step 1, embedded evaluators: outside evaluators such as METR get employee-like access and can publish findings; each company does this, and Anthropic commits now, unilaterally. Step 2, democracies coordinate: labs in democracies set common safety standards and limits on unchecked progress, with government support. Step 3, global coordination: agreements with authoritarian governments where possible, easiest first: a bioweapons ban, pre-release testing, a 'speed limit' on recursive self-improvement, a full pause. Note: step 1 is the only one Anthropic can take alone; Amodei calls a full global pause unlikely any time soon."

Transcription:
- Kicker: "DARIO AMODEI · "WE MUST PACE THE FRONTIER" · SEP 2026"
- Title: "The three-step pacing plan"
- Subtitle: "Pacing = time to align and safeguard models and for third parties to confirm it; not halting training"

Flow (three cards, left to right):
1. **Embedded evaluators.** "Outside evaluators (e.g. METR) with employee-like access; can publish findings." "Who: each company. Anthropic commits now, unilaterally."
2. **Democracies coordinate.** "Labs in democracies set common safety standards and limits on unchecked progress." "Who: industry, with government support."
3. **Global coordination** (orange card). "Agreements with authoritarian governments where possible, easiest first: bioweapons ban, pre-release testing, an RSI "speed limit", a full pause." "Who: governments."

Below the cards: "Step 1 is the only one Anthropic can take alone. Steps 2 and 3 need industry and governments." and "Amodei calls a full global pause unlikely any time soon."

Source line: "Source: darioamodei.com/post/we-must-pace-the-frontier"

What it adds: the primary-source URL, and the definition that pacing is "not halting training". It places the RSI speed limit as the third of four items inside step 3, the step that depends most on others.

Caveats vs trends.md: the image does not name China (it says "authoritarian governments"), and the SALT comparison appears only in post 6/. No measurable trigger for the "speed limit" is given, which answers the trend's watch question in the negative for now. The phrase "US–China ladder" is an interpretation by the thread author and trends.md, not wording from the image.

## Post: @sahilkapur, https://x.com/sahilkapur/status/2103493904830259709

- Evidence item: "AOC and Ro Khanna co-sign the Sanders/Casar bill to ban "superintelligence" and RSI and create a cabinet-level Department of AI" (2026-09-25)
- Full post text:

> AI 2028 alert: @AOC and @RoKhanna have signed on to the Sanders/Casar bill to ban "superintelligence" and RSI, plus create a cabinet-level Department of AI. Maybe the most aggressive AI bill in Congress so far. https://t.co/Xmas8G8nnA https://t.co/rF0PtbKAfO

### `media/2103493904830259709-3_2103493900836933632.jpg`

alt_text: none.

Serif-text excerpt, apparently from a press release (verbatim):

> The first 10 co-sponsors from the U.S. House of Representatives are Representatives Yassamin Ansari (AZ-03), Alexandria Ocasio-Cortez (NY-14), Chris Deluzio (PA-17), Jesús "Chuy" García (IL-04), Adelita Grijalva (AZ-07), Val Hoyle (OR-04), Ro Khanna (CA-17), Stephen Lynch (MA-08), Analilia Mejia (NJ-11), and Nydia Velazquez (NY-07).

As a table:

| # | Representative | District |
| --- | --- | --- |
| 1 | Yassamin Ansari | AZ-03 |
| 2 | Alexandria Ocasio-Cortez | NY-14 |
| 3 | Chris Deluzio | PA-17 |
| 4 | Jesús "Chuy" García | IL-04 |
| 5 | Adelita Grijalva | AZ-07 |
| 6 | Val Hoyle | OR-04 |
| 7 | Ro Khanna | CA-17 |
| 8 | Stephen Lynch | MA-08 |
| 9 | Analilia Mejia | NJ-11 |
| 10 | Nydia Velazquez | NY-07 |

What it adds: the image names 10 House co-sponsors, not just AOC and Khanna, which makes it a broader coalition than the post implies.

Caveat vs trends.md: the image confirms only the co-sponsor names. It does not name the bill, and says nothing about a ban on "superintelligence" or RSI or a Department of AI. Those claims rest on the post text and its link alone.

---

## X Article images

Eight images embedded in two X Articles. Media keys and order come from `raw/articles.json` (`article.cover_media` and `article.media_entities`). The article payload has no image placeholders in its plain text. So each in-body image is placed in the article section its content belongs to (inference). The media_entities order (…308612, …298687, …298194, …311341, …310683, …302515) is not reading order: the media keys run in upload order, and none of the six images carries alt_text in the payload.

**Scope note:** the six Supermemory in-body images do **not** include a per-dataset BEIR table. The only reranking image is a SciFact cost-quality scatter. The NFCorpus, TREC-COVID, FiQA and SCIDOCS numbers behind "+0.05 to +0.17 nDCG@10" and "mean 0.612 vs 0.564" are not in any stored image or text.

### Article: "We Added Jev as a Reranker. Here's What We Learned" (@Vectorizeio, https://x.com/Vectorizeio/status/2103230262607761659)

- Evidence item: "Vectorize ships Jev reranking inside the Hindsight memory service" (2026-09-24), trend Decision models as the memory control plane.
- Source note: `sources/x-article-vectorize-hindsight-jev-reranker.md`

#### `media/article-3_2103228826507497472.jpg`

Role: article cover (`cover_media`). alt_text: none.

Left side: title "We Added Jev as a Reranker. Here's What We Learned." Subtitle: "Six lessons from shipping a model that returns typed decisions, not text."

Right side: a mock Jev response panel.
- Header: `"rank"` and `choice · 250 options · 1 request`

| Option | Probability |
| --- | --- |
| c0 | 0.41 |
| c1 | 0.23 |
| c2 | 0.14 |
| c3 | 0.09 |
| c4 | 0.07 |
| c5 | 0.06 |

- Footer: "probabilities sum to 1. that is the ranking."

What it adds: it illustrates the shipped listwise design, one `Choice` call over the whole pool with the probabilities as the ranking. The six shown probabilities sum to exactly 1.00, although the header says 250 options. That leaves nothing for the other 244, so this is an illustration, not a real response (inference). 250 is also the pool size above which the article says ranking switches to rounds. The image holds no benchmark numbers; the LoCoMo tables are in code blocks in the article text.

### Article: "Jev changes a lot in memory & context engineering. Here's exactly how." (@DhravyaShah, https://x.com/DhravyaShah/status/2103314339239428201)

- Evidence item: "Supermemory tests Jev across reranking, chunking, pre-extraction filtering and the recall/no-recall gate; reports up to 58% token reduction" (2026-09-25, cited post by @Muskanjain0401), trend Decision models as the memory control plane.
- Source note: `sources/x-article-supermemory-jev-memory-context.md`

#### `media/article-3_2103278997534916608.jpg`

Role: article cover (`cover_media`). alt_text: none.

White card with large black text: "I played with [Jev logo] jev. it changes memory". Bottom right: the "supermemory" logo. No data.

#### `media/article-3_2103298687330119680.jpg`

Role: media_entities[1]. Placed in section "Jev can make reranking better". alt_text: none.

Scatter plot.
- Title: "Rerankers on BEIR SciFact"
- Subtitle: "Quality vs list price. Jev is measured (BM25 top-100 → Score-10). Everyone else is published nDCG. Up and left is better."
- Y axis: "SciFact nDCG@10", ticks 0.66, 0.68, 0.70, 0.72, 0.74, 0.76.
- X axis: "USD per query to rerank 100 candidates (log)", ticks $0, $0.00001, $0.0001, $0.001, $0.01, $0.10.
- Legend: star = "Jev (this run)"; black dot = "API, published nDCG"; grey dot = "Self-host, published nDCG".
- Two vertical dotted lines with price-only labels: "Voyage rerank-3" (approx. $0.0011) and "Cohere 3.5" (approx. $0.002).
- Footnote (verbatim; the "$" signs seem to have been swallowed by the renderer): "BGE / Jina / monoT5: Abdallah et al. 2025. RankGPT-4: Sun et al. CF bge-reranker-base 0.00311/MTok. Jev0.042/MTok. Voyage & Cohere: price only, no public SciFact nDCG."

Only the Jev point has a printed value. The other values are read off the axes (approx.) unless the article text confirms them.

| Reranker | Type | SciFact nDCG@10 | USD per query (100 candidates) |
| --- | --- | --- | --- |
| Jev Score-10 (this run) | measured | approx. 0.746 | $0.00133 (printed) |
| monoT5 | self-host, published | approx. 0.766 (text: 0.766) | approx. 0.00014 |
| RankGPT-4 | API, published | approx. 0.756 (text: 0.756) | approx. 0.04 (text: ~$0.04/q) |
| mxbai-large | self-host, published | approx. 0.751 | approx. 0.0002 |
| jina-turbo | self-host, published | approx. 0.745 | approx. 0.00017 |
| bge-large | self-host, published | approx. 0.741 | approx. 0.00012 |
| bge-v2-m3 | self-host, published | approx. 0.735 | approx. 0.0001 |
| jina-tiny | self-host, published | approx. 0.734 | approx. 0.00015 |
| bge-reranker-base ("what we ship · CF") | API, published | approx. 0.706 | approx. 0.00007 |
| BM25+CE | self-host, published | approx. 0.688 | approx. 0.00005 |
| BM25 | (first stage) | approx. 0.665 | approx. 0.000002 |
| Voyage rerank-3 | price only | not plotted | approx. 0.0011 |
| Cohere 3.5 | price only | not plotted | approx. 0.002 |

What it adds:
1. Jev's measured cost: **$0.00133 per query to rerank 100 BM25 candidates**. This is the only measured Jev cost in the article's images.
2. Supermemory's production reranker is bge-reranker-base on Cloudflare ("what we ship · CF"). It scores about 0.706 on SciFact, roughly 0.04 below Jev.
3. On this chart Jev sits right of every self-hosted reranker and below monoT5, RankGPT-4, mxbai-large and (roughly level with) jina-turbo. Six self-hosted models cluster between about 0.734 and 0.766 at about a tenth of Jev's cost.

Contradictions vs the article text:
1. The text gives Jev's cost as "~$0.00037/q" and says "Cohere is $0.002/q (5× Jev)". The chart prints $0.00133/query, which would make Cohere only about 1.5× Jev. The two figures may use different candidate counts (the chart is explicitly 100 candidates), but the text does not say so.
2. The text gives Score-10 on SciFact as 0.751. The star is plotted at about 0.746 (approx. read, between the 0.74 and 0.76 gridlines). This may be only a reading error on my side, but it is worth checking before citing.
3. The text calls Jev's quality "much better than avg"; on this SciFact chart it is mid-pack among dedicated rerankers.

#### `media/article-3_2103308612085174272.jpg`

Role: media_entities[0]. Placed in section "Perfectly accurate chunking" (inference). alt_text: none.

Table (verbatim):

| Method | What this implementation does | External API for chunking? |
| --- | --- | --- |
| Fixed windows | Cuts sequentially at the character target. | No |
| Fixed + 20% overlap | Fixed windows that repeat one fifth of each chunk at the next boundary. | No |
| Recursive separators | Looks backward near the target for paragraph, line, sentence, and space separators, including several non-English punctuation marks. | No |
| Sentence packing | Uses `Intl.Segmenter` and packs sentence units until the size target. Oversize sentences may be split. | No |
| Markdown headings + sentences | Starts sections at Markdown `#` headings, then packs sentences. Plain or noisy headings receive no special treatment. | No |
| Embedding semantic | Embeds sentence units and favors boundaries with high adjacent embedding distance while respecting a size target. | OpenAI embeddings |
| Jev continuation | Jev judges whether the next sentence continues the preceding thought; low continuation favors a cut. | Jev |
| Jev boundary | Jev judges whether each sentence starts a new topic, thought, list, heading, or speaker turn; high boundary score favors a cut. | Jev |

What it adds: it answers the source note's open question about "jev continuation" versus "jev boundary". Continuation asks if the next sentence continues the thought, and a low score favours a cut. Boundary asks if a sentence starts a new topic, thought, list, heading or speaker turn, and a high score favours a cut. It also names the embedding baseline (OpenAI embeddings) and the sentence splitter (`Intl.Segmenter`).

#### `media/article-3_2103311341222256640.jpg`

Role: media_entities[3]. Placed in section "Perfectly accurate chunking" (inference). alt_text: none.

Grouped horizontal bar chart.
- Title: "Top retrieved chunk contains the answer (hit@1)"
- Subtitle: "72 questions across 36 documents in 6 languages, with markdown, plain and noisy formats"
- Legend: light bar = "160-char chunks", dark bar = "320-char chunks" (Jev rows in light and dark blue).
- X axis: 0% to 100%, ticks 0%, 25%, 50%, 75%, 100%.

| Method | hit@1, 160-char chunks | hit@1, 320-char chunks |
| --- | --- | --- |
| Fixed windows | 62% | 78% |
| Fixed + 20% overlap | 53% | 78% |
| Recursive separators | 57% | 89% |
| Sentence packing | 58% | 75% |
| Markdown headings + sentences | 58% | 62% |
| Embedding semantic | 76% | 81% |
| Jev continuation | 75% | 93% |
| Jev boundary | 82% | 93% |

What it adds: the chunking quality numbers the article text omits.
- At 320 chars, both Jev chunkers reach 93%. The best non-Jev chunker is recursive separators at 89%, a gap of 4 points. On 72 questions that is about 3 questions (93% ≈ 67/72, 89% ≈ 64/72; inference).
- At 160 chars, Jev boundary leads at 82%, with embedding semantic at 76%. Jev continuation (75%) is 1 point **below** embedding semantic.

Caveat vs the text: "Jev is pretty clearly the SOTA at chunking" holds for Jev boundary, but the margins are small on a 72-question benchmark. Jev continuation does not beat embedding chunking at 160 chars. Jev costs about 7 to 11x more (the article's cost chart: $0.080 to $0.087 vs $0.008 to $0.011 per 1k docs).

#### `media/article-3_2103310683777753088.jpg`

Role: media_entities[4]. Placed in section "Perfectly accurate chunking" (inference). alt_text: none.

Heatmap (blue = higher, pale/pink = lower).
- Title: "Answer found within a 640-character context budget (%), 160-char chunks"
- Column groups: "Format" (Markdown, Plain, Noisy) and "Language" (EN, ES, AR, HI, JA, ZH).

| Method | Markdown | Plain | Noisy | EN | ES | AR | HI | JA | ZH |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fixed windows | 83 | 79 | 75 | 50 | 75 | 83 | 75 | 100 | 92 |
| Fixed + 20% overlap | 75 | 75 | 71 | 83 | 25 | 58 | 75 | 100 | 100 |
| Recursive separators | 83 | 75 | 62 | 17 | 50 | 83 | 92 | 100 | 100 |
| Sentence packing | 92 | 83 | 79 | 100 | 33 | 92 | 83 | 100 | 100 |
| Markdown headings + sentences | 100 | 79 | 75 | 100 | 50 | 83 | 75 | 100 | 100 |
| Embedding semantic | 96 | 96 | 79 | 100 | 67 | 92 | 83 | 100 | 100 |
| Jev continuation | 92 | 88 | 92 | 75 | 100 | 92 | 75 | 100 | 100 |
| Jev boundary | 96 | 92 | 96 | 67 | 100 | 100 | 100 | 100 | 100 |

The chart shows six language columns, which matches the "6 languages" in the hit@1 subtitle.

What it adds:
1. **Noisy data** is where Jev pulls ahead: Jev boundary 96 and Jev continuation 92, against at most 79 for every non-Jev method.
2. **Spanish** drives much of the multilingual claim: both Jev chunkers score 100 there, against 25 to 75 for the others.
3. **English is Jev's weak spot.** Jev boundary scores 67 and Jev continuation 75, while sentence packing, markdown headings and embedding semantic all score 100. This contradicts a blanket "best chunker" reading.
4. JA and ZH are at or near 100 for every method, so they do not separate the chunkers.
5. Cell sizes are small: with 72 questions over 6 languages, each language cell is about 12 questions (one question ≈ 8.3 points), and each format cell is about 24 questions (one question ≈ 4.2 points). Every printed value fits those steps (inference).

#### `media/article-3_2103298194042163200.jpg`

Role: media_entities[2]. Placed in section "Having decisions in the harness made by Jev" (inference). alt_text: none.

Claude Code terminal screenshot (verbatim where legible; the right edge is cut off):

```
Claude Code v2.1.282
Opus 5.5 · Claude Max
~/code/supermemory-mono

Get to finished work sooner with Opus 5.5. Switch anytime with /model.
 └ SessionStart:startup says: ◪ supermemory · 10 memories loaded for mono

> what do you know about me
 └ UserPromptSubmit says: ◪ supermemory · recalled 5 memories (242 tok)

──────────────────────────── 1 new message ────
● Here's what I know about you, from my local memory notes and what supermemory surfa[cut off]

Who you are
- You're Dhravya Shah ([email address shown; omitted here]), founder of supermemory, working mai[cut off]
  covers the Cloudflare Workers API, the console, MCP, observatory, self-hosted an[cut off]
                                                   1 new message (click) ↓

>

◪ supermemory · saved 9s ago
▸▸ auto mode on (shift+tab to cycle) · ← 4 agents
```

What it adds: the two hook points the plugin uses. At `SessionStart:startup` it loads 10 memories for the project; at `UserPromptSubmit` it recalls 5 memories costing 242 tokens, close to the "avg tokens injected is 250" in the text.

Caveat: nothing in the screenshot shows Jev making the recall/no-recall decision. There is no probability, no decision label and no skipped recall. It shows the plugin's recall, not the Jev gate the section describes. The recall gate still has no quantitative evidence.

#### `media/article-3_2103302515525931008.jpg`

Role: media_entities[5]. Placed in section "Cleaning up context before observation" (inference). alt_text: none.

The same hand-drawn diagram as `media/2103449596819316742-3_2103449254731894784.jpg` (see the Muskanjain0401 entry above for the full transcription). Jev verdicts: "Hey, i wanna eat!" yes; "How about indian food?" no; "you have also been loving mexican food, so indian is worth trying." yes; "i love that stuff. let's do it." yes.

What it adds: it confirms that the Muskanjain0401 post reused this image from the Supermemory article. It illustrates the article's "The catch" paragraph on assistant turns, where trimming part of an assistant turn changes what "that stuff" refers to.

---

## Added 2026-09-26

Images that were in `media/` but not yet transcribed (28 files). They come from the new evidence items (mika_systems, supermemory, DhravyaShah) and from X Articles reached through linked posts (mika_systems' Jev guide, rvaniaaaa, slash1sol). Ten `linked-*` files are byte-identical (same MD5) to other files and are marked as copies rather than transcribed twice. Each unique image was opened and read directly. Media keys come from `raw/x_api_responses.json`, `raw/linked_posts.json` and `raw/articles.json`. None of these images has alt_text. Anything unreadable is marked "illegible". Where an image is placed in an article section, that placement is inference, because the article payloads have no image placeholders.

### Post: @mika_systems, https://x.com/mika_systems/status/2103554329139417547

- Evidence item: "Jev + GPT-6 Astra planner won 9/10 StarCraft II games vs the hardest built-in AI; Jev alone won 0/10 (5 setups, 50 matches)" (2026-09-25), trend Typed-decision tier displacing LLM calls on bounded classification.
- Source note: `sources/x-article-mika-jev-9-step-blueprint.md`

#### `media/2103554329139417547-13_2103551832333099008.jpg`

Role: thumbnail of the attached video (media_key 13_2103551832333099008, type video). alt_text: none. 960 x 1200.

A dark "telemetry dashboard" frame around a blurred storm-cloud render with lightning and rain streaks. Text, verbatim where legible:
```
Jev + GPT-6 Astra
VOLUME ENGINE / LIVE FIELD
LAYERS 03 / ACTIVE   PARTICLES 2,600   TRANSPORT ADVECTION   LIGHT MULTI SCATTER   BUFFER 360 / 960
01 SAMPLE  02 ADVECT  03 CONDENSE  04 SCATTER  05 IONIZE  06 DISCHARGE  07 TRACE  08 RECYCLE

field@terminal > inspect --transport --radiance                 PROCEDURAL TELEMETRY
01 / ROUTE GRAPH   LINKS 14 / 42   FLOW BIDIRECTIONAL   ROUTE / TRANSPORT
02 / CELL STATE    ALLOC 90/144    UPDATE 9 HZ   MODE STOCHASTIC   CELL / OCCUPANCY
03 / DEPTH TAPE    NEAR ... FAR    RANGE 0.5 / 60   WRAP CONTINUOUS   Z / DISTRIBUTION
04 / SCATTER FIELD POINTS 170      ROTATION ORBIT / XYZ   PHASE / PROJECTION
05 / PULSE SCOPE   SIGNAL RADIANCE PEAK 0.731   LIGHT / RESPONSE
06 / EVENT QUEUE   030 SAMPLE RUN, 029 TRACE OK, 028 RECYCLE OK, 027 FLASH OK, 026 SCATTER OK, 025 ADVECT OK, 024 SAMPLE RUN
                   QUEUE 30   STATE STREAMING   EVENT / DISPATCH
```
What it adds: nothing about StarCraft. The frame shows no game footage, no match results and no Jev or Astra decision data; the numbers are part of a procedural graphics display. Only the thumbnail is stored, so the rest of the video is unknown.

### Post: @supermemory, https://x.com/supermemory/status/2103513608399532143 (also linked by @DhravyaShah, https://x.com/DhravyaShah/status/2103522483630739793)

- Evidence items: "Supermemory "dreams": indexing finishes first, then a second phase groups related documents..." and "Supermemory decides dynamically when to dream instead of running on cron..." (2026-09-25), trend Consolidation as a separate phase from ingestion.
- Source note: `sources/consolidation-phase-supermemory-rauch.md`

#### `media/2103513608399532143-13_2103485515614056448.jpg`

Role: thumbnail of the attached video (media_key 13_2103485515614056448). alt_text: none. 1080 x 1080.

A white square. Top left, small grey monospace label: "DREAMING". Bottom centre, black text: "when you go quiet, it dreams". Nothing else.

What it adds: it repeats the idle trigger ("When you go quiet") from the post. It gives no threshold, timing or result.

#### `media/linked-13_2103485515614056448.jpg`

Byte-identical to `media/2103513608399532143-13_2103485515614056448.jpg` (same MD5). Fetched through `raw/linked_posts.json` because @DhravyaShah links the supermemory post.

### Article: "Jev: The 9-Step Blueprint for Building a Faster Decision Brain for AI Agents" (@mika_systems, https://x.com/mika_systems/status/2101686148338798610)

- Quoted by the StarCraft evidence post above. Source note: `sources/x-article-mika-jev-9-step-blueprint.md`.
- `media_entities` order: 3_2101653152218947584, 3_2101652984014721024, 3_2101683694003994625, 3_2101654948429672448, 3_2101652984597729280, 3_2101652984815910912, 3_2101652984023126016, 3_2101652984799150080, 3_2101654479032455168; `cover_media` 3_2101680910726737920.
- All of these except the waitlist crop are photographic-style illustrations (paper cards, pink string) with pseudo-text that cannot be read. None contains data. Each `media/linked-3_<key>.jpg` file is byte-identical to `media/article-3_<key>.jpg`.

#### `media/article-3_2101680910726737920.jpg`

Role: cover. alt_text: none.

Text: "JEV | FIELD GUIDE", "FROM SETUP TO FIRST AGENT", a pink tag "9-STEP BLUEPRINT", and a card "THE DECISION BRAIN FOR AI AGENTS". A string of beads numbered 1 to 9 runs along the bottom into a wheel whose centre is a gear with a brain icon; the wheel segments show icons (bar chart, list, network, dice and others). On the right, four outputs (magnifier, `</>`, globe, person) point to cards; the person path is pink and ends in a card with a check mark. What it adds: nothing beyond the title.

#### `media/article-3_2101653152218947584.jpg` (copy: `media/linked-3_2101653152218947584.jpg`)

Role: media_entities[0]. alt_text: none.

A loop of cards joined by pink arrows: an eye, a tray of stacked cards, a decision diamond branching to a check box and an X box, a lever, and a document with a check mark, which leads back to the eye. On the left, a red stop sign with a toggle switch; on the right, a string-tied bundle with a red wax seal. No legible text.

What it adds (inference): it matches the article's loop "observe → build allowlist → decide → execute → verify → observe again" plus the kill switch listed in Step 06.

#### `media/article-3_2101652984014721024.jpg` (copy: `media/linked-3_2101652984014721024.jpg`)

Role: media_entities[1]. alt_text: none.

A paper tape feeds a cardboard box with small labels "1", "2", "2", "3" on its side. Three chutes leave the box: the top and bottom end in cards marked X; the middle, traced by a pink arrow, ends in a card with a pink circle (O). Tabs "1", "2", "3" lie in the foreground. What it adds (inference): an illustration of a Choice picking one route out of three.

#### `media/article-3_2101683694003994625.jpg` (copy: `media/linked-3_2101683694003994625.jpg`)

Role: media_entities[2]. alt_text: none. A small UI crop, verbatim:
```
Sign In   Join Waitlist
Join Our Waitlist
Get early access to Jev
[your email]  submit
```
What it adds: it illustrates the article's instruction to join the TypeSafe waitlist first.

#### `media/article-3_2101654948429672448.jpg` (copy: `media/linked-3_2101654948429672448.jpg`)

Role: media_entities[3]. alt_text: none.

A four-panel folded sheet with a pink line of dots running across all panels and ending in a dashed arrow. Panel 1: a calculator, a flowchart, a gear and a padlock. Panel 2: cards with radio buttons and bars (one pink), a bell curve, a histogram with one pink bar, and a 3x3 grid with one hatched cell. Panel 3: handwritten notes (illegible), a network graph with a pencil, and a card with a mountain picture. Panel 4: an envelope sealed with a pink fingerprint, then a person icon above three circles and a box. What it adds (inference): the icons fit Step 08 ("Know where Jev breaks": arithmetic, generation, privacy), but nothing is labelled.

#### `media/article-3_2101652984597729280.jpg` (copy: `media/linked-3_2101652984597729280.jpg`)

Role: media_entities[4]. alt_text: none.

A code printout under a magnifying glass (text illegible), a decision tree of circles and squares, and a bell curve with a shaded region and an axis label (illegible). A pink thread connects a point in the code to a node in the tree, two points on the curve, and a stamp with a triangle. No data.

#### `media/article-3_2101652984815910912.jpg` (copy: `media/linked-3_2101652984815910912.jpg`)

Role: media_entities[5]. alt_text: none.

A clipboard with a sheet showing a database cylinder at the centre of a small diagram (labels illegible). Five pink strings fan out to five tags: a hierarchy with one pink node, three horizontal bars (one pink), a check mark over an X, a shield with a check, and a person with a pink dot. The text on each tag is dotted placeholder text (illegible). What it adds (inference): it matches Step 05's "ONE STATE" feeding several independent questions (team, urgency, refund, human review).

#### `media/article-3_2101652984023126016.jpg` (copy: `media/linked-3_2101652984023126016.jpg`)

Role: media_entities[6]. alt_text: none.

An open folder. Left: a printout of numbered pseudo-code lines (01 to 09 and so on; the code is illegible). Right: three clipped tags, one with a checkbox list (first box ticked in pink), one with ranked bars numbered 1, 2, 3, and one with a pie chart (one slice pink). Each tag is wired to a metal switch box with two sliders, which has a pink arrow leading right. A tracing-paper sheet on the left shows one input splitting into three boxes and rejoining. What it adds (inference): Choice, Score and probability outputs feeding code that acts, as in Steps 02 and 06.

#### `media/article-3_2101652984799150080.jpg` (copy: `media/linked-3_2101652984799150080.jpg`)

Role: media_entities[7]. alt_text: none.

A perforated printout of lines starting with ">" (illegible), then four tags in a row joined by pink arrows, each with a pink ticked box beneath: a gear, a cloud, a share/network icon, and a document. A dashed pink line leads to a glassine envelope containing a key. What it adds (inference): setup steps ending with the API key (Step 04).

#### `media/article-3_2101654479032455168.jpg` (copy: `media/linked-3_2101654479032455168.jpg`)

Role: media_entities[8]. alt_text: none.

An open notebook. Left page, handwritten, legible:
```
for i = 0; i < n; i++ {
  p = model[i].score();
  if (p > best) {
    best = p;
    choice = i;
  }
}

// evaluate
for (k : options) {
  u = expected(k);
  r = risk(k);
  if (u - λ * r > thresh) {
    select(k);
  }
}
```
Beside it a flow S0 → S1 → S2 → S3 with a dashed box "?", and notes "u : {...}", "r : {...}", "c : {...}", "t : {...}" (contents illegible). Below:
```
E[v] = Σ_{i=1}^{n} p_i · u_i
Var[v] = Σ_{i=1}^{n} p_i (u_i - E[v])^2
CE = E[v] - λ · Var[v]
λ ∈ (0,1)
if uncertain prefer robust else exploit

while (!converged) {
  θ = update(θ, grad);
  if (Δ < ε) break;
}
→ higher retun   (sic)
→ lower risk
→ more optionality
→ greater resilience
```
A small line chart sits under the loop. A tape strip across both pages carries a pink timeline with handwritten labels (illegible). Right page: twelve cards "OPT A" to "OPT L", each with bars for p, u, r, c and a checkbox; B, D, G and J are ticked. Along the bottom: a scatter plot with one pink point, a bar chart with a dashed threshold line and pink bars, and a tree with a pink path.

What it adds: decorative. The formulas (expected value minus a risk penalty over a threshold) are generic decision theory and are not Jev's API; the article never uses them.

### Linked post: @rvaniaaaa, https://x.com/rvaniaaaa/status/2090512486738845784 (X Article "The Second Brain Is Not a Storage System. It's a Compiler.")

- Reached through the post @tonygaorx replied to; trend Staleness and provenance as the core memory-write problem. Source notes: `sources/staleness-provenance-practitioners.md`, `sources/x-posts-new-jev-builders.md`.

#### `media/linked-3_2090499054585192449.jpg`

Role: the article's only `media_entities` image. alt_text: none.

A dark-theme screenshot of a GitHub gist page. Text, verbatim:
```
Instantly share code, notes, and snippets.
karpathy / llm-wiki.md
Created 4 months ago
Star 5,000+   Fork 5,000+
Code   Revisions 1   Stars 5,000+   Forks 5,000+
Embed  <script src="https://...   Download ZIP
llm-wiki
llm-wiki.md   Raw
LLM Wiki
A pattern for building personal knowledge bases using LLMs.
This is an idea file, it is designed to be copy pasted to your own LLM Agent (e.g. OpenAI Codex, Claude Code, OpenCode / Pi, or etc.). Its goal is to communicate the high level idea, but your agent will build out the specifics in collaboration with you.
```
What it adds: the source of the article's "LLM Wiki" idea. The star count is shown as "5,000+", matching the article's "5,000 stars".

### Linked post: @slash1sol, https://x.com/slash1sol/status/2098013767627837827 (X Article "$50 or $15: GPT-6 Astra vs Kimi K3, and Why the Smart Money Runs Both")

- Reached through the @virgilxbt post that @roscherveniak replied to, where it is billed as a "13-page breakdown of agent memory". The article is about model routing, not memory. Source notes: `sources/staleness-provenance-practitioners.md`, `sources/x-posts-new-jev-builders.md`.
- `media_entities` order: 3_2097408592064442368, 3_2097409501217304577, 3_2097409052695261184, 3_2097409360527769600, 3_2097409223877607424. The images are labelled PICTURE 1 to 5; by label, the reading order is …408592 (1), …409052 (2), …409223 (3), …409360 (4), …409501 (5).

#### `media/linked-3_2097408592064442368.jpg`

Role: PICTURE 1, "Two frontier models, side by side". alt_text: none.

| row | GPT-6 ASTRA | KIMI K3 |
|---|---|---|
| Released | 3 Sep 2026 | 16 Jul 2026 |
| Context | 1,050,000 tokens | 1,048,576 tokens |
| Price, in / out | $10 / $50 per M | $3 / $15 per M ($0.30 cached) |
| Weights | Closed, API only | Open, 2.8T parameters |
| Parallelism | One agent, Codex harness | Agent Swarm, up to 300 sub-agents |
| Access | Staged rollout, enterprise off by default | API, self-host, Kimi Code CLI (MIT) |
| Cyber | Critical tier, gated via Daybreak | Not gated |

Footer: "Same context window to the token. Everything else on the sheet points in different directions. One is a service you rent. One is a model you can hold."

#### `media/linked-3_2097409052695261184.jpg`

Role: PICTURE 2, "The number to read carefully". alt_text: none.

Label "ARC-AGI-3 SEMI-PRIVATE". Two bars: black "99.9%", captioned "OpenAI provider adapter harness / opaque reasoning state carried between calls"; red "62.7%", captioned "ARC Prize standard harness / each call independent, notes only". Right column "WHAT THE GAP MEANS": "The same model, same weights, same day. The 37-point difference is the wrapper: state that OpenAI's harness keeps between requests and that you cannot inspect or reproduce." "The best Astra lives inside OpenAI's scaffolding. Call it statelessly from your own stack and you get the red bar." Footer: "Both scores are real and ARC Prize accepts both. The point is who owns the scaffolding that turns 62.7 into 99.9, and it is not you."

What it adds for a memory stack: the only number in this batch about state carried between calls: 99.9% with carried state vs 62.7% with independent calls and notes only, on one benchmark, as reported by the article.

#### `media/linked-3_2097409223877607424.jpg`

Role: PICTURE 3, "Depth versus width". alt_text: none.

Left: a black circle "Astra / one agent, deep", captioned "One hard problem / computer use · 40 min per OSWorld task · $50 per M out". Right: a field of blue dots, captioned "Three hundred easy ones / Agent Swarm · ~4,000 steps · $15 per M out". Footer: "Astra is built to be one very capable agent driving a computer for forty minutes. K3 is built to be three hundred of them at once. Most real work is one of those shapes, and almost never both."

#### `media/linked-3_2097409360527769600.jpg`

Role: PICTURE 4, "Strength by strength". alt_text: none.

| THE JOB | WINS | WHY |
|---|---|---|
| Single hard problem | Astra | FrontierMath T4 97.6%, world-model behaviour on ARC-AGI-3 |
| Computer use, one agent | Astra | OSWorld 72.6% at ~40 min vs 65.7% at ~75 for its predecessor |
| Long-context retrieval | Astra | MRCR 100% to 512K, 96.3% to 1M |
| Wide parallel work | K3 | 300 sub-agents, ~4,000 coordinated steps, ~4.5x faster than one agent |
| Cost at volume | K3 | $3 / $15 vs $10 / $50, cached input at $0.30 |
| Owning the model | K3 | 2.8T open weights, self-host, fine-tune, run behind a firewall |
| Seeing what it does | K3 | Open weights and open CLI vs opaque reasoning state and gated tiers |
| Being able to use it today | K3 | Downloadable since July vs staged rollout, enterprise off by default |

Footer: "Three rows to Astra, five to K3, and none of them are the same row. Nobody who reads this table should conclude one model is better. They should conclude which one they need on Tuesday."

#### `media/linked-3_2097409501217304577.jpg`

Role: PICTURE 5, "The build that uses both". alt_text: none.

Flow of four boxes: "Spec / task, sources, output format" → "K3 Agent Swarm / 300 agents do the wide work" (caption "most of the tokens, at $15 out") → "Astra gate / one pass on the hard tail" (caption "few tokens, at $50 out, where one mistake costs more") → "Deliverable / graph, report, code". Footer: "Volume on the open model, judgement on the expensive one. You pay $50 a million only for the tokens that decide something."
