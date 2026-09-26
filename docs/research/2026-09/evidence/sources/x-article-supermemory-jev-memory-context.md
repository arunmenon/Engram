# Jev changes a lot in memory & context engineering. Here's exactly how.

- **URL:** https://x.com/i/article/2103277270773506048 (post: https://x.com/DhravyaShah/status/2103314339239428201)
- **Type:** X article (vendor builder writeup)
- **Author / org:** Dhravya Shah (@DhravyaShah), founder of Supermemory
- **Date:** 2026-09-25 (post created 2026-09-25T02:43:10Z)
- **Retrieved:** 2026-09-26 (local copy: raw/article-2103314339239428201.txt plus two code blocks in raw/articles.json). The cover image and 6 in-body images are stored as media/article-3_<media_key>.jpg and transcribed in sources/images-transcribed.md ("X Article images"). The images hold the chunking benchmark (method table, hit@1 chart, per-format and per-language heatmap) and a SciFact reranker cost-quality scatter. **They contain no per-dataset BEIR table**, so the NFCorpus, TREC-COVID, FiQA and SCIDOCS figures remain unavailable.
- **Cited by evidence:** Decision models as the memory control plane / 2026-09-25 Muskanjain0401 ("Supermemory tests Jev across reranking, chunking, pre-extraction filtering and the recall/no-recall gate; reports up to 58% token reduction").
- **Relevance to a memory stack:** high. A memory vendor tests a decision model at four points in the memory pipeline (rerank, chunk, pre-extraction filter, recall gate). It reports where the model helped and where it harmed meaning.

## TL;DR
- **Rerank:** Jev beat BM25 on every BEIR set tried (+0.05 to +0.17 nDCG@10). It beat bge-reranker-base on quality (mean 0.612 vs 0.564) but cost about 20x more. It lost to jina-reranker-turbo (0.612 vs 0.633). The author's verdict: "I'd stick to reranker for now".
- **Chunking:** Jev asks per sentence "does this continue the previous thought or start a new one", and those answers set the boundaries. The author calls it "pretty clearly the SOTA at chunking", including multilingual text. It is about 10x more expensive than rule-based or embedding chunking.
- **Pre-extraction filter:** a per-sentence Noul decides whether the sentence should go to the extractor at all. It saved **58% of content tokens** on their internal benchmark, but independent per-sentence cuts damage meaning. Conclusion: "Jev is not a very good compactor for memory."
- **Recall gate in the harness:** Jev decides at the Claude Code `UserPromptSubmit` hook whether memory should be injected for this prompt. It honours "without using memory, tell me..." with no tool call. The author calls this "the perfect solution for making ad-hoc decisions on the harness".
- **Correction to the citing claim:** the 58% figure applies only to the pre-extraction filter. The article does not report a token reduction for reranking, chunking or the recall gate.

## What it claims / describes
**The general memory pipeline (the author's model).** Every memory system they studied "at scale" (ChatGPT, Claude, Instinct, Openclaw, Hermes, Muse and customers), whether markdown-, graph- or fact-based, reduces to:
1. Finding relevant info / retrieval: some search step (grep or cosine similarity).
2. Chunking the data to do the observation (you cannot fit everything into another model call). This also applies to retrieval.
3. Observation / learning outside the main loop (on a schedule or trigger).
4. Harness-specific logic to bring the context back into the model.

Diagram from the article's code block (verbatim):
```
Raw data (messages, files, tool output) ────────────→ Current context
        │                                                    │
        └→ Chunking / batching [fit into one model call]     │
                      │                                      │
          Observation / learning [off-loop]                  │
          [background job, schedule, or trigger]             │
                      │                                      │
          Stored context                                     │
          [markdown files, vector DB, graph, KV]             │
                 │                    │                      │
       Summaries / profiles     Search / reads ←── query ────┤
       [one-pager, profile]     [grep, cosine, on demand]    │
                 │                    │                      │
                 └────────────────────┴──────────────────────┤
Harness injection [hooks, tools, system prompt, recaps] ─────┤
                                                             ↓
                                                       Agent's answer
```
The framing: Jev "is really good at taking decisions really fast, and can output structured choices and probabilities. Not text generation."

### 1. Reranking
- Benchmarks: public BEIR sets SciFact, NFCorpus, TREC-COVID, FiQA and SCIDOCS "and some more".
- Jev beat base BM25 every time, by +0.05 to +0.17 nDCG@10 ("which was expected").
- Variants tried:
  - "Noul-as-a-delete-gate failed (it kept nothing, for some reason)."
  - Noul-as-a-sort and Score-10 both worked, with almost the same results. Score-10 was the best Jev-only method (SciFact 0.751). (Score-10 is presumably a 10-level Score question; inference.)
- The comparisons are listed in the Numbers table below.
- The author contrasts this with turbopuffer's bakeoff (Jev vs Voyage/Luna, https://x.com/ErikKaum/status/2103169247102812334). That bakeoff used a "GPT-5.6 sol Golden set" as reference, whereas Supermemory used public benchmarks, and turbopuffer "never included BGE".
- Verdict, quoted: "reranker models are pretty good! Jev does score REALLY well here, but it's a bit more expensive and I'd stick to reranker for now. But in the decision models world, i can see it become SOTA." The author also asks whether reranker models could be used the way Jev is used, by reframing questions as rankings; this is left open.

### 2. Chunking
- The problem as stated: existing chunkers are "too expensive (embedding based), or too deterministic (markdown heading based) or too vibes-based (sliding window chunking, fixed length chunking)".
- The method: "ask whether each sentence continues the previous thought or starts a new one, then use those answers to choose chunk boundaries near a target size."
- Evaluation: an internal benchmark with messy data, markdown and multilingual data (code-mixed languages are called out as especially hard). The evaluation approach follows Chroma's chunking research (https://www.trychroma.com/research/evaluating-chunking).
- Claimed result: "Jev is pretty clearly the SOTA at chunking". The numbers are in the article's images (see Numbers): 72 questions across 36 documents in 6 languages. Both Jev chunkers reach 93% hit@1 at 320-char chunks, against 89% for the best non-Jev method. At 160 chars Jev boundary leads (82% vs 76%), but Jev continuation (75%) is 1 point below embedding semantic.
- Two Jev variants, as the method-table image defines them. **Jev continuation:** "Jev judges whether the next sentence continues the preceding thought; low continuation favors a cut." **Jev boundary:** "Jev judges whether each sentence starts a new topic, thought, list, heading, or speaker turn; high boundary score favors a cut."

### 3. Cleaning up context before observation (pre-extraction filter)
- Why memory generation is expensive, according to the author: (a) a model has to look through nearly all the context, so inference runs twice; (b) to register something, you need to know what is already learnt.
- "Most of the conversation or document is not even important for memory. It is headings, audio checks, 'no action items,' and talk that can stay searchable as source text."
- Method: split into sentences, then ask a yes/no Noul on each: "should this go to the extractor at all? remove everything else."
- Result: **58% of content tokens saved** on the internal benchmark.
- The catch, quoted: "removing some sentences independently seems to be the wrong direction, because of contextuality." Two examples:
  - Assistant turns: trimming parts of them damages their meaning. An in-body image of the article shows the case; the citing post reuses the same image. In "user: Hey, i wanna eat! / assistant: How about indian food? you have also been loving mexican food, so indian is worth trying. / user: i love that stuff. let's do it.", Jev marked "How about indian food?" as **no** and the rest as **yes**. Dropping that line makes "i love that stuff" attach to Mexican food.
  - Legal documents or conversations: an early line may look useless but be referenced later. "We could not reliably figure out how to give Jev this full context because it's classifying sentences."
- Conclusion: "as of right now, Jev is not a very good compactor for memory!" Supermemory instead relies on its small specialised observer model learner-1 (https://x.com/supermemory/status/2097035274094272935), which makes observation "insanely cheap anyways".

### 4. Decisions in the harness (recall / no-recall gate)
- Context: the Supermemory Claude Code plugin automatically injects memory. Average injection is 250 tokens, "and you'll always know when it does". Docs: https://supermemory.ai/docs/integrations/claude-code
- Experiment: Jev decides at the Claude Code `UserPromptSubmit` hook whether memory is needed for this query. It is still a hook that decides the injection, not a tool the model calls.
- The author's stance: "models are very bad at deciding _when_ some memory should be helpful, but are getting better at longer context." The author does not want the main model deciding when to bring in memory.
- Benefit claimed: users can say "without using memory, tell me..." and Jev decides not to recall, "without a tool call".
- No accuracy, latency or cost numbers are given for this gate. The article's Claude Code screenshot shows the plugin's hooks (`SessionStart:startup` loads 10 memories; `UserPromptSubmit` "recalled 5 memories (242 tok)"), but it shows no Jev decision.

## Numbers
| Metric | Value | Baseline | Setup / benchmark | Caveat |
|---|---|---|---|---|
| nDCG@10 gain over BM25 | +0.05 to +0.17 | BM25 first stage | SciFact, NFCorpus, TREC-COVID, FiQA, SCIDOCS | No per-dataset table in the text or in any of the article's images |
| Best Jev-only method (Score-10), SciFact nDCG@10 | 0.751 | | SciFact | |
| Noul as delete gate | kept nothing | | BEIR | Failed |
| Jev mean nDCG@10 | 0.612 | bge-reranker-base 0.564 | "3 overlapping sets" (not named) | |
| Cost per query | ~$0.00037/q | bge-reranker-base ~$0.00002/q | | about 20x more expensive |
| Jev mean nDCG@10 | 0.612 | jina-reranker-turbo 0.633 | | Jev loses |
| SciFact nDCG@10 | Jev 0.751 | monoT5 0.766, RankGPT-4 0.756 | SciFact | Jev slightly lower than both |
| Price | Jev $0.042/MTok | Voyage rerank-3 $0.05/MTok | list prices | |
| Price per query | Cohere $0.002/q (5x Jev); RankGPT-4 ~$0.04/q | | | |
| Chunking cost per 1k docs | jev continuation $0.080, jev boundary $0.087 | rule-based $0.008, embedding semantic $0.011 | internal | Jev about 7 to 11x more expensive |
| Pre-extraction token saving | 58% of content tokens | no filter | internal benchmark | Harms meaning (context loss) |
| Claude Code plugin injection | avg 250 tokens | | Supermemory plugin | This is not a Jev result |
| Claude Code plugin recall (screenshot) | 5 memories, 242 tok at UserPromptSubmit; 10 memories at SessionStart | | one session | No Jev decision visible |
| Jev reranking cost (image) | $0.00133 per query to rerank 100 candidates | | SciFact, BM25 top-100 → Score-10 | Conflicts with the text's ~$0.00037/q and "Cohere 5× Jev" |
| Chunking hit@1, 320-char chunks | Jev continuation 93%, Jev boundary 93% | best non-Jev: recursive separators 89% | 72 questions, 36 docs, 6 languages | 4-point margin ≈ 3 questions (inference) |
| Chunking hit@1, 160-char chunks | Jev boundary 82%, Jev continuation 75% | embedding semantic 76% | same | Jev continuation is 1 point below embedding |

### Figures transcribed from the article's images
Full transcriptions, including layout and verbatim captions, are in sources/images-transcribed.md ("X Article images"). Values marked approx. were read off chart axes.

**Rerankers on BEIR SciFact** (media/article-3_2103298687330119680.jpg). "Quality vs list price. Jev is measured (BM25 top-100 → Score-10). Everyone else is published nDCG." X axis: USD per query to rerank 100 candidates (log). Source footnote: "BGE / Jina / monoT5: Abdallah et al. 2025. RankGPT-4: Sun et al."

| Reranker | SciFact nDCG@10 | USD per query (100 candidates) |
|---|---|---|
| Jev Score-10 (measured) | approx. 0.746 (text says 0.751) | $0.00133 (printed) |
| monoT5 | approx. 0.766 | approx. 0.00014 |
| RankGPT-4 | approx. 0.756 | approx. 0.04 |
| mxbai-large | approx. 0.751 | approx. 0.0002 |
| jina-turbo | approx. 0.745 | approx. 0.00017 |
| bge-large | approx. 0.741 | approx. 0.00012 |
| bge-v2-m3 | approx. 0.735 | approx. 0.0001 |
| jina-tiny | approx. 0.734 | approx. 0.00015 |
| bge-reranker-base ("what we ship · CF") | approx. 0.706 | approx. 0.00007 |
| BM25+CE | approx. 0.688 | approx. 0.00005 |
| BM25 | approx. 0.665 | approx. 0.000002 |
| Voyage rerank-3 / Cohere 3.5 | price only, no nDCG | approx. 0.0011 / approx. 0.002 |

**Chunking methods compared** (media/article-3_2103308612085174272.jpg). Fixed windows; Fixed + 20% overlap; Recursive separators; Sentence packing (`Intl.Segmenter`); Markdown headings + sentences; Embedding semantic (OpenAI embeddings); Jev continuation; Jev boundary. Only the last three call an external API.

**Top retrieved chunk contains the answer (hit@1)** (media/article-3_2103311341222256640.jpg). 72 questions across 36 documents in 6 languages, with markdown, plain and noisy formats.

| Method | 160-char chunks | 320-char chunks |
|---|---|---|
| Fixed windows | 62% | 78% |
| Fixed + 20% overlap | 53% | 78% |
| Recursive separators | 57% | 89% |
| Sentence packing | 58% | 75% |
| Markdown headings + sentences | 58% | 62% |
| Embedding semantic | 76% | 81% |
| Jev continuation | 75% | 93% |
| Jev boundary | 82% | 93% |

**Answer found within a 640-character context budget (%), 160-char chunks** (media/article-3_2103310683777753088.jpg)

| Method | Markdown | Plain | Noisy | EN | ES | AR | HI | JA | ZH |
|---|---|---|---|---|---|---|---|---|---|
| Fixed windows | 83 | 79 | 75 | 50 | 75 | 83 | 75 | 100 | 92 |
| Fixed + 20% overlap | 75 | 75 | 71 | 83 | 25 | 58 | 75 | 100 | 100 |
| Recursive separators | 83 | 75 | 62 | 17 | 50 | 83 | 92 | 100 | 100 |
| Sentence packing | 92 | 83 | 79 | 100 | 33 | 92 | 83 | 100 | 100 |
| Markdown headings + sentences | 100 | 79 | 75 | 100 | 50 | 83 | 75 | 100 | 100 |
| Embedding semantic | 96 | 96 | 79 | 100 | 67 | 92 | 83 | 100 | 100 |
| Jev continuation | 92 | 88 | 92 | 75 | 100 | 92 | 75 | 100 | 100 |
| Jev boundary | 96 | 92 | 96 | 67 | 100 | 100 | 100 | 100 | 100 |

What the heatmap shows: Jev's lead is on noisy text (92 to 96 vs at most 79 for the others) and on Spanish (100 vs 25 to 75). On English, Jev is the weakest of the strong methods (Jev boundary 67, Jev continuation 75, vs 100 for sentence packing, markdown headings and embedding). JA and ZH are at or near 100 for everyone. Each language cell is about 12 questions (1 question ≈ 8.3 points); inference from 72 questions over 6 languages.

Chunking cost chart (verbatim code block):
```
cost per 1k docs

rule-based          $0.008  ██
embedding semantic  $0.011  ██▌
jev continuation    $0.080  ██████████████████▍
jev boundary        $0.087  ████████████████████
```

## Mechanism details you could implement
- **Semantic chunker:** for each sentence i, ask a Noul "does sentence i continue the previous thought (vs start a new one)?". Place boundaries at low-continuation points near a target chunk size. The exact prompt, threshold and target size are not stated.
- **Pre-extraction filter:** per-sentence Noul "should this go to the extractor at all?". Drop the sentences that fail, but keep the full source searchable as raw text. The article warns this breaks coreference and anaphora (for example "that stuff") and long-range references. (inference: a safer variant is to judge whole turns, or to include the preceding turn as state, or to use the filter only for routing and never delete.)
- **Recall gate:** a hook at `UserPromptSubmit` sends the prompt to Jev (probably a Noul along the lines of "does this query need memory?"; the exact question is not stated). Inject about 250 tokens of memory only on yes. Explicit user opt-out phrases are handled naturally.
- **Reranker variants:** Score with 10 levels, or Noul used for sorting, both work. Noul used as a keep/delete gate collapsed to keeping nothing. This matches the "escape hatch" failure Vectorize reports in its Hindsight article (inference, cross-source).

## Limitations, caveats, counter-evidence
- The author is openly biased: the post repeatedly promotes Supermemory ("all roads lead to using @supermemory").
- The chunking and filter results come from internal benchmarks with no released data. The chunking quality figures (in the images) rest on 72 questions, so the Jev margin at 320 chars (93% vs 89%) is about 3 questions. Jev does worst on English (67 to 75 vs 100 for three cheaper methods).
- The image and the text disagree on Jev's reranking cost: $0.00133/query for 100 candidates on the SciFact chart vs "~$0.00037/q" and "Cohere is $0.002/q (5× Jev)" in the text. The Score-10 SciFact point also plots at about 0.746, against 0.751 in the text.
- For reranking, Jev does not win on cost against BGE, and it loses on quality to jina-reranker-turbo, monoT5 and RankGPT-4 on SciFact.
- The recall gate has no quantitative evaluation. "Having jev decide _feels_ really good!" is a qualitative claim.
- The 58% saving comes with an admitted semantic-damage failure mode, and Supermemory does not use it in production (inference from "Jev is not a very good compactor for memory" and from the learner-1 pivot).
- "We also found ways to make supermemory _much_ cheaper through Jev... more about that soon". No details are given.

## Takeaways for tuning a memory stack
- The cheapest high-leverage place for a decision model is the **recall/no-recall gate in the harness hook** (before the main model), not inside the extractor.
- Do not delete sentences independently before extraction. If you filter, use turn-level or context-windowed judgements, and keep raw text searchable so dropped lines can still be recalled.
- For reranking, a dedicated cross-encoder is still competitive on cost and quality. Consider Jev only if you already pay for the call, or if you need typed decisions beyond ordering.
- Continuation-based boundary chunking is a strong option for messy and multilingual transcripts if you can afford about $0.08 per 1k docs.
- Avoid a Noul used as a keep/drop gate in reranking. It kept nothing, which is the same over-rejection failure seen elsewhere.

## Open questions
- What are the per-dataset BEIR numbers for NFCorpus, TREC-COVID, FiQA and SCIDOCS? No stored text or image gives them.
- Which candidate count gives the text's ~$0.00037/q, given that the chart shows $0.00133/query for 100 candidates?
- What does the gate question for `UserPromptSubmit` look like, and what are its false-negative and false-positive rates for recall?
- Would context-windowed filtering (sentence plus neighbours as state) keep most of the 58% saving without the meaning damage?
- What were the "ways to make supermemory much cheaper through Jev"?

---
