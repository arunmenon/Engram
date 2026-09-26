Text classification in MotherDuck just got about 50x faster at about 1% of the cost. Today we're shipping an integration with [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev), a new kind of AI model from TypeSafe AI. On a 100,000-row benchmark it matched frontier LLM accuracy in 40 seconds for fifty cents. The comparable LLM took more than half an hour and cost $37. When price gets that low and performance is this good, entire tables that were too expensive to handle are easily within reach. 

TypeSafe describes the state of AI today as "databases before SQL”, where we first need to understand the database before we can build the universal language on top. Their pitch for Jev is a frontier-intelligence function call: unstructured state goes in, typed probabilistic decisions come out. We read that and thought, well, this fits right into the universal language of SQL. It can be framed as a function that takes a text column and hands back a label, a score, or a yes/no with a confidence score - exactly how scalar functions today. There is no need to parse the response, and so it's immediately ready to filter, join, and aggregate in the same statement.

This combination of speed, accuracy, and cost together is what makes new workloads viable. LLMs can already classify text, but running it across a million rows is slow enough and expensive enough it is hard to see the value. The alternative, training an encoder like BERT, means collecting labeled examples and maintaining your own model. This is a big bet for something that may not work until it’s close to prod ready. `prompt_jev()` is configured with a few sentences, runs at analytics speed, and is extremely cost effective for the rows it labels. Below, it pulls the main complaint out of a table of support transcripts:


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

We think this is a very big deal for analytics. A database is, after all, an excellent place to store your million customer conversations. But it’s still really hard to figure out what your customers are complaining about. Before you can track which problems are getting worse, someone or something has to read those conversations and label them. Encoder models like BERT can efficiently classify over a large dataset, but first you have to collect labeled examples, fine-tune the model, and improve the model as new data comes in. This takes patience and expertise. On the other hand, LLMs enable you to just prompt for what you want instead, but running one across a meaningfully large dataset is slow, expensive, and error-prone.

`prompt_jev()` gives you LLM-style ergonomics with encoder-style efficiency, all at analytics scale. Here are some comparisons that made us excited:

| model | rows/s | accuracy | Retail cost/100k | wall time at 100k rows | 
| :---- | ----: | ----: | ----: | ----: |
| **Jev** | **2,484** | **89%** | **$0.50** | **40s** |
| gpt-4o-mini | 84 | 80% | $1.93 | 19m 45s |
| gpt-5-nano | 94 | 83% | $1.58 | 17m 49s |
| gpt-5.6-luna | 61 | 84% | $3.53 | 27m 25s |
| gpt-5.6-terra | 52 | 88% | $37.58 | 31m 59s |


_We benchmarked on 100,000 articles sampled from the training split of [AG News](https://huggingface.co/datasets/fancyzhx/ag_news), the four-class news topic dataset introduced by [Zhang, Zhao & LeCun (2015)](https://arxiv.org/abs/1509.01626), scoring each model against the ground truth._

What really excited us was that it exceed existing models by >25x across cost, accuracy, and speed dimensions. Furthermore, tests at 1m and 10m rows yielded similar performance (and in some cases even faster than our baseline presented above).

>   
`prompt_jev()` is available on all paid MotherDuck plans. Pick a question you’ve been putting off and try it on your own data\!

<admonition type="info" title="Upcoming Live Demo">

Join us for a live demo on Tuesday, September 29 at 9:30am PDT. Register here: https://luma.com/prompt_jev

</admonition>


## Dive into Jev
Use [our guide to learn how to use MotherDuck and Jev together](https://motherduck.com/docs/key-tasks/ai-and-motherduck/classify-text-with-prompt-jev/) for classifying text. Or play around with the Dive below to see what is possible.

<motherduck-dive dive-id="7f4fcf42-ac0a-4b41-ae0e-499b6b11a228"></motherduck-dive>

## Further Reading

* [MotherDuck docs on `prompt_jev`](http://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt-jev/)
* [Guide: Classifying text with Jev on MotherDuck](https://motherduck.com/docs/key-tasks/ai-and-motherduck/classify-text-with-prompt-jev/)

<details>

<summary>   And if you need some inspiration - run the benchmark yourself!</br></summary>

```sql
-- 1) Load AG News (train split) straight from Hugging Face and draw the 100k sample
CREATE TABLE ag_train AS
SELECT row_number() OVER () AS id, text, label
FROM 'hf://datasets/fancyzhx/ag_news/data/train-00000-of-00001.parquet';

CREATE TABLE sample_100k AS
SELECT * FROM ag_train USING SAMPLE 100000 ROWS (reservoir, 43);

-- 2) Classify every row with prompt_jev
CREATE TABLE preds AS
SELECT id, label,
       prompt_jev(text,
                  'Classify the topic of this news article.',
                  choice := ['World', 'Sports', 'Business', 'Sci/Tech']) AS result
FROM sample_100k;

-- 3) Score against the dataset labels
CREATE MACRO ag_name(l) AS ['World', 'Sports', 'Business', 'Sci/Tech'][l + 1];

-- overall accuracy (NULLs reported separately, never scored as wrong)
SELECT count(*)                                              AS n,
       count(*) FILTER (WHERE result.choice IS NULL)         AS nulls,
       round(avg((result.choice = ag_name(label))::INT), 4)  AS accuracy,
       round(avg(result.confidence), 3)                      AS mean_confidence
FROM preds;

-- per-class precision, recall, F1
WITH c AS (
  SELECT ag_name(label) AS truth, result.choice AS pred FROM preds WHERE result.choice IS NOT NULL
), k AS (SELECT unnest(['World', 'Sports', 'Business', 'Sci/Tech']) AS class)
SELECT class,
       count(*) FILTER (WHERE truth = class AND pred = class) AS tp,
       count(*) FILTER (WHERE truth <> class AND pred = class) AS fp,
       count(*) FILTER (WHERE truth = class AND pred <> class) AS fn,
       round(tp / (tp + fp), 4) AS "precision",
       round(tp / (tp + fn), 4) AS recall,
       round(2 * tp / (2 * tp + fp + fn), 4) AS f1
FROM k CROSS JOIN c GROUP BY class ORDER BY class;

-- confusion matrix
PIVOT (SELECT ag_name(label) AS truth, result.choice AS pred FROM preds)
ON pred USING count(*) GROUP BY truth ORDER BY truth;
```