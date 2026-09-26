# Introducing prompt_jev(): bringing Jev to Motherduck SQL

- **URL:** https://motherduck.com/blog/motherduck-supports-jev/
- **Type:** vendor blog
- **Author / org:** Hamilton Ulmer (Software Engineer), MotherDuck
- **Date:** 2026-09-21 (dateModified 2026-09-23)
- **Retrieved:** 2026-09-26 (local copy: raw/web/motherduck-supports-jev.md, the article markdown extracted from the page's `__NEXT_DATA__`)
- **Cited by evidence:** Typed-decision tier displacing LLM calls on bounded classification / 2026-09-21 typesafeai quoting @motherduck ("MotherDuck `prompt_jev()`: 100k rows in 40 s for $0.50 vs 32 min and $37 with an LLM, at frontier-LLM accuracy")
- **Relevance to a memory stack:** medium. This is a bulk text classification benchmark, not a memory benchmark. It is useful for sizing the cost and throughput of batch memory classification (tagging, backfilling, re-labelling a memory store).

## TL;DR
- `prompt_jev()` is a MotherDuck SQL scalar function that sends a text column to Jev. It returns a label, a score, or a yes/no with confidence, as a struct you can filter, join and aggregate on directly.
- On 100k AG News rows: **Jev 89% accuracy, 2,484 rows/s, $0.50, 40 s**. The best LLM (gpt-5.6-terra) scored 88% at $37.58 and took 31m 59s.
- Tests at 1M and 10M rows yielded "similar performance (and in some cases even faster than our baseline presented above)".
- It is available on all paid MotherDuck plans.

## What it claims / describes
- Framing: Jev is a "frontier-intelligence function call: unstructured state goes in, typed probabilistic decisions come out". It maps onto a SQL scalar function, so "There is no need to parse the response".
- Positioning: it offers LLM-style ergonomics (configured with a few sentences) with encoder-style efficiency. There is no need to train and maintain a BERT classifier.
- Example (verbatim):
```sql
SELECT
    conversation_id,
    prompt_jev(
        transcript,
        'Identify the customer''s main complaint',
        choice := [
{label: 'billing', description: 'Payments, invoices, and refunds'},
{label: 'technical', description: 'Errors, outages, and integrations'},
{label: 'sales', description: 'Pricing and upgrades'},
{label: 'account', description: 'Cancellations and account administration'}
	  ]
    ) AS classification
FROM customer_conversations;
```
- The signature, as seen in the examples: `prompt_jev(text_column, instruction_string, choice := [...])`. `choice` accepts either a list of strings or a list of `{label, description}` structs. The result has fields `result.choice` and `result.confidence`. Syntax for score or yes/no modes is not shown in the article (see the linked docs: http://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt-jev/, not retrieved).

## Numbers
Benchmark (verbatim table). Setup: "100,000 articles sampled from the training split of AG News, the four-class news topic dataset ... scoring each model against the ground truth."

| model | rows/s | accuracy | Retail cost/100k | wall time at 100k rows |
| :---- | ----: | ----: | ----: | ----: |
| **Jev** | **2,484** | **89%** | **$0.50** | **40s** |
| gpt-4o-mini | 84 | 80% | $1.93 | 19m 45s |
| gpt-5-nano | 94 | 83% | $1.58 | 17m 49s |
| gpt-5.6-luna | 61 | 84% | $3.53 | 27m 25s |
| gpt-5.6-terra | 52 | 88% | $37.58 | 31m 59s |

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Headline speed | "about 50x faster" | LLM | AG News 100k | 40 s vs 31m 59s is about 48x (gpt-5.6-terra) |
| Headline cost | "about 1% of the cost" | LLM | AG News 100k | $0.50 vs $37.58 is 1.3% |
| Claimed margin | ">25x across cost, accuracy, and speed dimensions" | | | The accuracy gain is +1 point vs terra, so ">25x" cannot apply to accuracy literally (inference) |
| Scale | 1M and 10M rows "similar performance" | 100k | | No numbers given |

## Mechanism details you could implement
The reproducible benchmark SQL (verbatim, abridged to the key steps; the full script is in the local copy):
```sql
CREATE TABLE sample_100k AS
SELECT * FROM ag_train USING SAMPLE 100000 ROWS (reservoir, 43);

CREATE TABLE preds AS
SELECT id, label,
       prompt_jev(text,
                  'Classify the topic of this news article.',
                  choice := ['World', 'Sports', 'Business', 'Sci/Tech']) AS result
FROM sample_100k;

-- overall accuracy (NULLs reported separately, never scored as wrong)
SELECT count(*) AS n,
       count(*) FILTER (WHERE result.choice IS NULL) AS nulls,
       round(avg((result.choice = ag_name(label))::INT), 4) AS accuracy,
       round(avg(result.confidence), 3) AS mean_confidence
FROM preds;
```
- NULL results are possible and are counted separately, not scored as wrong. How many NULLs occurred is not stated. (inference: accuracy may therefore be computed over non-NULL rows, which could inflate it slightly.)
- The script also computes per-class precision, recall and F1 and a confusion matrix, but those results are not published in the post.

## Limitations, caveats, counter-evidence
- AG News is an easy four-class topic task. There is no evidence about harder, contextual judgements such as memory relevance or contradiction (inference).
- Retail pricing; exact prompts for the LLM baselines are not stated.
- The NULL rate is not reported.
- The 1M and 10M results are asserted without figures.

## Takeaways for tuning a memory stack
- For bulk offline passes over a memory store (tagging memory type, topic, PII flags, stale or durable classification), a typed decision model can cost well under 1% of a frontier LLM at similar accuracy on simple closed label sets.
- Keep confidence alongside the label, and treat NULL or low confidence as a separate bucket to review.
- Validate on your own label set. Simple topic classification is not the same as memory-relevance judgement.

## Open questions
- What are the NULL rate and the per-class F1?
- How does accuracy hold on multi-level or context-dependent labels?
- What are the syntax and behaviour of score and yes/no modes?

---
