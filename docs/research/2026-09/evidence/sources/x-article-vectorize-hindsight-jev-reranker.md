# We Added Jev as a Reranker. Here's What We Learned

- **URL:** https://x.com/i/article/2103228685444587520 (announcing post: https://x.com/Vectorizeio/status/2103230262607761659)
- **Type:** X article (vendor engineering writeup)
- **Author / org:** Vectorize (@Vectorizeio), makers of the Hindsight memory service
- **Date:** 2026-09-24 (post created 2026-09-24T21:09:05Z)
- **Retrieved:** 2026-09-26 (local copy: raw/article-2103230262607761659.txt; the two results tables are only in the code blocks of raw/articles.json). The article has one image, the cover (media/article-3_2103228826507497472.jpg), and no in-body images. It is transcribed in sources/images-transcribed.md ("X Article images").
- **Cited by evidence:** Decision models as the memory control plane / 2026-09-24 Vectorizeio ("Vectorize ships Jev reranking inside the Hindsight memory service"). Announcing post text: "Hindsight now includes @typesafeai Jev reranking capabilities!"
- **Relevance to a memory stack:** high. A shipping memory service reports measured recall results and design failures from using a decision model as the recall reranker and relevance cutoff.

## TL;DR
- Hindsight 0.10.1 adds Jev (TypeSafe's "System One" decision model, which returns typed answers with probabilities and no text) as a reranker provider.
- **Listwise, not pairwise.** They ask one Jev `Choice` question with the whole candidate pool as options. On a 200-question LoCoMo set it scored recall@1 0.94, against 0.87 for one Noul call per candidate, using a thirtieth of the calls.
- **"Nothing is relevant" escape hatches failed twice.** A "none of these" Choice option returned empty results on 35 of 200 questions. A "nothing is relevant" level on the cut Score emptied 7% of queries and dropped gold retention from 0.81 to 0.65. The shipped design always keeps at least one candidate.
- **Ranking is on by default and the relevance cut (pruning) is off.** The cut raises precision from 0.051 to 0.850 (about 17x) but removes 19% of the gold evidence. It sees only the top 12 candidates.
- **The scores are rank positions normalised within each call, not confidences.** An absolute score floor copied from another reranker will filter on rank.

## What it claims / describes
**Jev primitives, as the article describes them:**
- `Choice` picks among unordered options and returns a probability for each.
- `Score` rates against ordered levels.
- `Noul` returns the probability that a yes/no proposition holds.

**Design 1 (built, then abandoned): pairwise Noul.** They asked "is this candidate relevant to this query?" once per candidate and sorted by probability. They describe this as "the pattern TypeSafe's own reranking material suggests". It was dropped because it is still pairwise: "Three hundred candidates means three hundred round trips and three hundred judgements that never see each other."

**Design 2 (shipped ranking): listwise Choice over the whole pool.** One request, whatever the number of candidates. The returned probabilities are the ranking. The design note they left in the code, quoted:
> "A Choice answers with a probability for every option, summing to 1, so handing it the whole pool returns the ranking in a single call. That beats scoring each candidate on its own: judged together the model only has to say which candidate beats which, instead of pinning every candidate to an absolute scale it must re-derive each time."

The general lesson they draw: "Relative judgement is an easier task than absolute judgement."

**The relevance cut ("where relevance stops"):**
- Attempt A was to add a "none of these" option to the Choice. It failed because "Choice options are unrivalled alternatives, not points on a scale, so 'none of these' is not competing with the candidates on relevance. It simply wins outright whenever the query is hard." 35 of 200 questions came back completely empty.
- Attempt B (shipped) is a `Score` with ordered levels. It sees the ranked shortlist and answers how far down relevance extends. The levels are in plain language: "only the first, the first two, the first three, the first five, the first ten, all of them". Because the model picks a level, "there is no threshold for us to tune."
- Attempt C was to add a "nothing is relevant" level to that Score. It emptied 7% of queries and dropped gold retention from 0.81 to 0.65, so that level was removed. "At least one candidate always survives, and no query comes back empty." Their rationale: recall runs on a pool that retrieval has already judged plausible, "so one weak memory the caller can dismiss beats silence."
- Their stated meta-lesson: "Twice in one feature, giving the model a clean way to answer 'nothing' made it answer 'nothing' far more often than the data justified."

**Ranking vs filtering defaults.** Ranking is on by default and pruning is off. Their framing: "Dropping most of the pool is a product decision about what your agent is for." Pruning is a good trade if the consumer is an LLM prompt and irrelevant memories waste context. It is a bad trade if a human reads the list, or if the agent needs "a needle that ranked fourteenth."

**Pipeline placement (Hindsight recall).** "The retrieval arms move ids and scores, not payloads." Full memory text is fetched ("hydration") only for candidates that survive fusion and the 300-candidate cap. That hydration step sits immediately before reranking, "because the reranker is the first stage that actually reads text." So a network reranker adds no extra fetch cost.

**Operational properties:**
- It is a hosted third-party API at TypeSafe's endpoint and needs an API key. Candidate memory text leaves your infrastructure.
- It fails closed. After its retry budget, a reranker that keeps erroring propagates the failure. They recommend a fallback chain with `rrf` last, so a bad day degrades to fusion order instead of failing the recall.
- The reranker is set at server level. A bank (tenant) cannot choose its own reranker, only turn reranking off.
- Jev's context is 32,000 tokens for state plus questions. The provider does not truncate candidate text before sending it.

## Numbers
Both tables are measured on LoCoMo, with gold defined as the dataset's own evidence turns, against the reranker Hindsight ships by default (local MiniLM).

**Table 1: 30 candidates per query (verbatim from the article's code block):**

| | recall@1 | recall@5 | NDCG@10 | s/query |
|---|---|---|---|---|
| `local` MiniLM (current default) | 0.800 | 0.876 | 0.850 | 0.12 |
| **Jev, ranking only (the default)** | **0.950** | **0.966** | **0.957** | **0.027** |

**Table 2 (verbatim). The caption line for this table is not in the X API payload.** The plain text ends at "30 candidates per query:", and this second code block follows with no heading. Its candidate count is not stated. (inference: lower absolute scores and higher latency suggest a larger candidate pool, but this is unconfirmed.)

| | recall@1 | recall@5 | NDCG@10 | s/query |
|---|---|---|---|---|
| `local` MiniLM | 0.583 | 0.719 | 0.682 | 0.41 |
| **Jev, ranking only** | **0.783** | **0.903** | **0.856** | **0.063** |

**Other figures from the text:**

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| recall@1, listwise Choice | 0.94 | 0.87 (one Noul call per candidate) | 200-question LoCoMo set, same model | Listwise uses 1/30 of the calls |
| Empty results with a "none of these" Choice option | 35 / 200 questions | n/a | LoCoMo 200 | Design abandoned |
| Empty queries with a "nothing is relevant" Score level | 7% | 0% (shipped design) | not stated | Gold retention fell from 0.81 to 0.65 |
| Candidates kept by the cut | 1.6 of 30 on average | 30 | 30-candidate run | |
| Precision of the survivors | 0.850 | 0.051 | 30-candidate run | about 17x |
| Gold evidence lost to the cut | 19% | 0% | 30-candidate run | This is why pruning is off by default |
| Real bank | 300 to 3 candidates | | production bank, not named | |
| Cut shortlist cap | top 12 | | | With pruning on, recall returns at most 12 results |
| Round-based ranking threshold | pools > 250 are ranked in rounds, then round winners are re-ranked | | | Rounds are not simply concatenated |
| Jev context limit | 32,000 tokens (state + questions) | | | No truncation of candidate text |
| Latency | 0.027 s/query vs 0.12 (Table 1); 0.063 vs 0.41 (Table 2) | local MiniLM | | Hosted API; network hop included (inference) |

**Cover image (media/article-3_2103228826507497472.jpg).** A mock Jev response illustrating the listwise design: `"rank"`, `choice · 250 options · 1 request`. Caption: "probabilities sum to 1. that is the ranking." Subtitle: "Six lessons from shipping a model that returns typed decisions, not text."

| Option | Probability |
|---|---|
| c0 | 0.41 |
| c1 | 0.23 |
| c2 | 0.14 |
| c3 | 0.09 |
| c4 | 0.07 |
| c5 | 0.06 |

The six shown probabilities already sum to 1.00, so with 250 options this is an illustration, not a measured response (inference). It contains no benchmark data.

## Mechanism details you could implement
- **Listwise rerank call:** a single Jev `Choice` request where the query is the question and each candidate memory is an option. Sort by the returned probability. For pools over 250, rank in rounds and then rank the round winners against each other.
- **Scores are rank-normalised:** "The top candidate is 1.0 and each next one is 1/n lower." A 0.7 means "the best of these," not "relevant". Scores cannot be compared across calls.
- **Relevance cut as an ordered Score:** levels are {only the first, first two, first three, first five, first ten, all}. There is no "none" level. The cut sees the top-12 shortlist and the depth is clamped to 12. Minimum output is 1 candidate.
- **Recall pipeline order:** parallel retrieval arms (ids + scores only), then fusion, then a 300-candidate cap, then hydration (fetch text once), then the reranker, then the optional cut.
- **Resilience:** a reranker fallback chain ending in `rrf` (reciprocal rank fusion order).
- Their stated rule for any typed-decision integration: look first for any option that lets the model say "nothing", because it will be over-selected.

## Limitations, caveats, counter-evidence
- Hosted third-party API: memory contents leave your infrastructure. Per the article, "no benchmark makes that acceptable" if self-hosting is a hard requirement.
- The reranker is server-level only, so there is no per-tenant choice.
- The evaluation is on LoCoMo only, against one baseline (local MiniLM). There is no comparison with other cross-encoders (for example BGE or Cohere) in this article. Their earlier cross-encoder post is linked but was not retrieved here: https://hindsight.vectorize.io/blog/2026/08/28/cross-encoder-reranking-agent-memory
- The second results table has no caption in the payload.
- The cut costs 19% of gold evidence, and the 12-result cap is a hard ceiling.
- No cost-per-query figure is given in this article.
- Vendor self-report; no independent reproduction (inference).

## Takeaways for tuning a memory stack
- If you use a decision model to rerank, prefer one listwise call over per-candidate yes/no scoring. It gave higher recall@1 (0.94 vs 0.87) with 30x fewer calls.
- Do not give a recall gate or cutoff an explicit "nothing relevant" option. It collapses toward empty results. Always return at least one candidate, and let the downstream LLM dismiss it.
- Keep ranking and pruning as separate switches. Turn pruning on only when the consumer is a context-limited LLM prompt and you can accept about 19% gold loss.
- Do not port absolute score thresholds between rerankers. With Jev listwise, the score is a rank position.
- Move ids and scores through retrieval, and hydrate text once, right before the first stage that reads text.
- Put a local fallback (RRF order) behind any network reranker.
- Watch the 32k token budget: long memories times a large pool can overflow the context, because Jev does not truncate candidate text.

## Open questions
- What pool size does Table 2 correspond to?
- What is the per-query cost of Jev listwise reranking at 30, 300 and 250+ candidates?
- How does listwise Jev compare with a strong cross-encoder (bge-reranker, Cohere, Voyage) on LoCoMo?
- Does round-based ranking for more than 250 candidates lose recall compared with a single call?
- Would a cut with more levels (for example "first 20") recover the 19% gold loss?

---
