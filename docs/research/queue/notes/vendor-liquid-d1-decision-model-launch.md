---
schema_version: 1
artifact_id: N-20261007-01
artifact_type: note
producer: triage
run_id: triage-20261007T014503Z-bfb4
created_at: 2026-10-07T01:51:35Z
input_refs: [{"artifact_id": "post:2105085473928716488", "file_id": null, "sha256": null}, {"artifact_id": "post:2105064765345423671", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:www.liquid.ai/blog/d1-decision-model
claim_cluster: url:www.liquid.ai/blog/d1-decision-model
feeds: ["decision", "memory"]
primary_source: https://www.liquid.ai/blog/d1-decision-model
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R6"]
memory_stage: evaluation
priority: 2
tags: {"mechanism": ["typed decision model", "input-only billing", "vision decisions", "context compaction"], "workload": ["classification", "filtering", "code search", "coding-agent compaction"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: vendor post shows six application demos but the comparative scores are in charts not readable as text", "control": "low: one run per model, no intervals, part of the test items written after the d1 pipeline was fixed", "independence": "low: vendor evaluating its own model on its own tasks", "reproducibility": "low: test sets and harness not released as far as the page shows", "applicability": "medium: code search and coding-agent context compaction are close to our engineering-agent workload"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": []}
claim_correction: Posts say d1 is the first model to outperform Jev on Hugging Face's Decision Index; Liquid's own launch post (2026-10-05) says only that d1 "became the first model to rival Jev on text decisions" and gives no Decision Index score, no multilingual and no prompt-injection result.
---

# Introducing d1: The most capable decision model, now with vision (Liquid AI)

- **URL:** https://www.liquid.ai/blog/d1-decision-model
- **Type:** vendor blog
- **Author / org:** Liquid AI (individual authors not stated)
- **Date:** 2026-10-05 (blog index date "10.05.2026")
- **Retrieved:** 2026-10-07 via WebFetch (text only; charts not readable; version n/a)
- **Cited by evidence:** https://x.com/AGTPinsights/status/2105085473928716488 (@AGTPinsights), https://x.com/boyang_xie/status/2105064765345423671 (@boyang_xie), both quoting @liquidai https://twitter.com/liquidai/status/2105003472332693869
- **Relevance to a memory stack:** medium: an open competitor to Jev (a System One decision model) with a coding-agent context-compaction demo, but the comparative numbers are not verifiable from text.

## TL;DR
- Claim correction: the X posts (2026-09-29/30) say d1 "outperform[s] Jev on @huggingface's Decision Index" and wins on multilingual and prompt-injection. Liquid's launch post of 2026-10-05 says only "d1 became the first model to rival Jev on text decisions"; it does not mention Hugging Face, the Decision Index, multilingual or prompt injection (WebFetch check of the page text).
- The post's own comparison is against GPT-6.1 Sol and Claude Opus 5.5 on six applications: "d1 matches or beats GPT-6.1 Sol on four of them", at "19x to 200x less" cost. Per-application scores are in charts we could not read.
- Pricing "$0.04 per million input tokens", billed "on input tokens only, with no output tokens"; text decision latency "200 to 300 ms".
- The vendor discloses a test-set hygiene problem: "We wrote six of the 15 code questions and two of the four compaction sessions after d1's pipeline was set." Each application was run "once per model on October 5, 2026".
- Our community Decision Index note (N-20261002-01, Jev 57.91, no d1 row) remains the only readable yardstick; this post does not change it.

## What it claims / describes
d1 is a decision model: it returns a decision (classification, yes/no, choice) in one call with no generated output tokens, and now also accepts images. The post demonstrates six applications (as reported by WebFetch):
1. Visual inspection on four production lines (circuit boards, candles, cashews, chewing gum): sorts good and defective parts.
2. Smart filter: "It answers yes or no for each of 150 support tickets", scored by F1 against hand labels.
3. Code search: "It files search questions the same way, so keyword search only looks in one subfolder." 15 code questions.
4. Smart folders (details not extracted).
5. Web agent (details not extracted).
6. Context compaction: "d1 reads each tool output in a coding agent's session and keeps, trims, or drops it for the next task." Four compaction sessions.
Plus game demos (Tetris, Wordle, Quick, Draw!).
Available through the Liquid AI API, Vercel and OpenRouter; vision "coming to both soon" on the external platforms. Model size, parameter count and training method: not stated.

## Numbers
| metric | value | baseline | setup/benchmark (n) | caveat |
|---|---|---|---|---|
| applications where d1 matches or beats GPT-6.1 Sol | "four of them" | GPT-6.1 Sol | six applications, one run each | per-application scores in charts, not read |
| cost vs frontier | "19x to 200x less than both models" | GPT-6.1 Sol, Claude Opus 5.5 | not stated | depends on token mix |
| visual inspection accuracy | "85-97%" | not stated in text | 4 production lines, n images not stated | no baseline in text |
| support-ticket filter | F1 (value not extracted) | hand labels | 150 tickets | |
| context compaction | "removes 52% of the tokens and keeps every output the task needs" | no compaction | 4 sessions, 2 written after the pipeline was set | "needs" judged by whom: not stated |
| Tetris score | "70 to 81" (text vs text plus screen) | text only | n games not stated | |
| Wordle | "12 of 12 games in 3.8 guesses on average" | not stated | 12 games | |
| Quick, Draw! | "5.2 of 6 drawings (random guessing gets 0.6)" | random | 62 words, n rounds not stated | |
| text decision latency | "200 to 300 ms" | not stated | not stated | |
| price | "$0.04 per million input tokens", no output tokens | not stated | | images "1.5 tokens per 32x32-pixel patch", 1024x1024 = "1,536 tokens" |
| vs Jev | "first model to rival Jev on text decisions" | Jev | no number in text | Decision Index not named |

## Mechanism details you could implement
- Input-only billing means a decision call costs the same whatever the label set size (inference); worth comparing per-call cost against Jev on our routing and reranking calls.
- Context compaction as a per-tool-output keep / trim / drop decision before the next task is a concrete assembly-stage design: one decision per tool output rather than a summariser over the whole session.
- Code search via filing the question into one subfolder, then keyword search only there: a routing-before-retrieval pattern.

## Limitations, caveats, counter-evidence
- Single run per model on one day; no intervals, seeds or n for several tasks.
- The vendor admits writing 6 of 15 code questions and 2 of 4 compaction sessions after the d1 pipeline was set (risk of tuning to the test).
- No released test sets or harness seen.
- The Decision Index claim in the X posts is not on this page; the community Decision Index board (N-20261002-01) had no d1 row on 2026-10-02. The other pending cluster url:docs.liquid.ai/lfm/models/decision-models still lacks a readable d1 board score.
- Chart values not extracted; WebFetch summaries may omit text (inference).

## Takeaways for tuning a memory stack
- Do not cite "d1 beats Jev" from the X posts; the vendor's own claim is "rival".
- If testing a Jev alternative at the reranking or compaction stage, d1's price model is a candidate cost arm, but only on our frozen data.
- The keep / trim / drop compaction decision is worth an arm in any assembly-stage test (inference).

## Open questions
- What are the per-application scores for d1, GPT-6.1 Sol, Claude Opus 5.5 and Jev (charts)?
- Does a d1 score exist on any readable Decision Index board?
- Who judged "keeps every output the task needs" in compaction?

## Grading and labels
- Directness: medium, vendor demos shown, comparative values only in charts.
- Control: low, one run per model, partly post-hoc test items.
- Independence: low, vendor self-evaluation.
- Reproducibility: low, no released data or code seen.
- Applicability: medium, coding-agent compaction and code search resemble our workload.
- Pillars: R9 primary (which System One model), R6 secondary (evaluation integrity). Memory stage: evaluation. Priority 2 (open-weight and alternative System One models as comparison).
- Beliefs: supports B20 (headline claims narrow on a primary read: "outperform on Decision Index" narrows to "rival on text decisions"). No contradiction.

## Origin chain
@liquidai X post 2105003472332693869 (2026-09-29) -> quoted by @AGTPinsights 2105085473928716488 and @boyang_xie 2105064765345423671 -> Liquid AI blog index (liquid.ai/blog, entry 10.05.2026) -> https://www.liquid.ai/blog/d1-decision-model (sections "Introducing d1", "How the d1 decision model works", "d1 in action", "Availability and pricing", "Methodology") -> this note. Independence: all sources are Liquid AI; the two reposters add no data. Related bus note: vendor-jev-decision-index-community-leaderboard.md (N-20261002-01).
