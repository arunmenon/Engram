# Memory stack synthesis: what the evidence says, by design decision

Built 2026-09-26 from the 26 evidence items on the Self-Improving Agents hub, the 5 papers, 4 repos, 2 X Articles, vendor posts and 26 images behind them. Every claim below points to a file in `sources/` (read it for the full numbers and quotes) or to an item in `evidence-ledger.md` (T = trend, E = evidence item). "(inference)" marks conclusions that are this synthesis's own rather than a source's.

**How strong is the evidence?** Mostly weak. There is one paper with a single benchmark and no ablations (Jev-Mem), one paper whose headline mechanism adds only about 2 points (REALM reconsolidation), and vendor or builder reports with small samples. Treat every number here as a hypothesis to test on your own traffic, not a spec. Section 8 lists where the evidence contradicts the hub's own trend claims.

---

## 1. Write path: what gets into memory

| Finding | Source | Strength |
|---|---|---|
| Accept every raw observation at write time (`admission_enabled=false`). Decide structure, not admission: pick up to 10 candidate neighbours with deterministic signals (vector, lexical, entity, time), then have the decision model confirm typed edges (semantic, temporal, causal, entity) only when the score is at least 0.60. Timestamps and exact entity IDs create edges directly, with no model call. | `paper-jev-mem-2609.23986.md` | Paper, 1 benchmark |
| Handle knowledge updates at WRITE time with `supersedes` and `contradicts` edges and a merge rule: "prefer add over modify; never merge a state change or a contradiction". This, not reconsolidation, drives the knowledge-update score (84.72 without reconsolidation, 88.89 with it, against Zep's 74.40). | `paper-memory-reconsolidation-2609.16053.md` | Paper, ablated |
| Do not put a decision model inside the extractor. Supermemory's per-sentence pre-extraction filter saved 58% of tokens but broke meaning: "i love that stuff" got attached to the wrong food. | `x-article-supermemory-jev-memory-context.md`, `images-transcribed.md` | Vendor, with its own counter-example |
| Gate PROMOTION into durable memory, not raw storage. Beacon scores each session trace with three yes/no questions and makes it a candidate only if `task_success >= 0.50` AND the mean of the three is `>= 0.60`. The task_success floor was added after a failed task averaged its way through (issue #649). A human or agent then writes the lesson and approves it explicitly. | `github-asymptote-labs-agent-beacon.md` | Repo, no quality metrics |
| Treat every memory or skill write as a proposal. It persists only if it beats the current best configuration on a held-out split, and the top-k configurations are kept as git branches. Before creating an entry, force a check: does an existing entry already cover this, so it should be edited instead? | `evoskill-skill-evolution-frozen-model.md` | Paper, validation on 7% of each benchmark, run once |
| Reject memory or skill entries that name specific eval tasks, entities or answers, because that is leakage. | `rrsi-regularized-recursive-self-improvement.md`, `evoskill-skill-evolution-frozen-model.md` | Paper |

| Chunking: Jev-decided chunk boundaries barely beat classic splitters. On 72 questions, 36 docs and 6 languages, hit@1 at 320-char chunks was 93% for both Jev methods against 89% for recursive separators, a margin of about 3 questions. At 160 chars, Jev boundary scored 82% against 76% for embedding-semantic. Jev leads on noisy text (92 and 96 vs at most 79) and Spanish (100 vs 25 to 75), but loses on clean English (67 to 75 vs 100 for sentence packing, markdown headings and embedding). | `x-article-supermemory-jev-memory-context.md`, `images-transcribed.md` | Vendor, small sample |

**Implied default (inference):** use a Jev-style chunker only for noisy or multilingual input. store raw text always. Make structure (edges and types) cheap and deterministic first and model-confirmed second. Gate only the step that promotes a lesson into something that changes future behaviour.

## 2. Read path: retrieval, ranking, stopping

| Finding | Source | Strength |
|---|---|---|
| Rerank listwise in ONE call. A single Jev Choice question over the whole pool got recall@1 0.94, against 0.87 for one yes/no question per candidate, with 30x fewer calls (Hindsight, LoCoMo 200). Against local MiniLM at 30 candidates: recall@1 0.950 vs 0.800, recall@5 0.966 vs 0.876, NDCG@10 0.957 vs 0.850, 0.027 s vs 0.12 s per query. | `x-article-vectorize-hindsight-jev-reranker.md`, `github-vectorize-io-hindsight.md` | Vendor benchmark |
| Jev scores are rank positions within one call, not absolute relevance. Never copy an absolute score floor over from another reranker. | `x-article-vectorize-hindsight-jev-reranker.md` | Vendor |
| Counterpoint: Hippo's opt-in Jev reranker went from R@1 0.41 to 0.62 on a private 300-query set (about $0.0004 per recall), but three graded tests showed no better answer rate than a free local cross-encoder. | `github-kitfunso-hippo-memory.md`, `images-transcribed.md` | Repo, small |
| Reranker cost versus quality on SciFact, 100 candidates: Jev Score-10 reached nDCG@10 of about 0.746 at $0.00133 per query. Six self-hosted rerankers reached about 0.734 to 0.766 at roughly a tenth of that cost, and Supermemory's shipped bge-reranker-base reached about 0.706. The article's own text claims about $0.00037 per query and Cohere at 5x Jev, but its chart shows about 1.5x. Jev is not the cheapest good reranker on clean scientific text. | `x-article-supermemory-jev-memory-context.md`, `images-transcribed.md` | Vendor chart, points read off the axes |
| Fuse several retrievers before reranking: vector + lexical + entity + time, or four search methods, with reciprocal-rank fusion k=60. Both Jev-Mem and Hindsight do this. | `paper-jev-mem-2609.23986.md`, `github-vectorize-io-hindsight.md` | Two independent designs |
| Route each query with six independent decision scores: need for each of the four views, multi-hop need, and recency importance. Split an expansion budget of 80 across the views, with a minimum of 1 for any view scoring at least 0.10. Depth scales with multi-hop need. | `paper-jev-mem-2609.23986.md` | Paper, no ablation |
| Replace fixed top-k with a stop rule. Stop when sufficient >= 0.95 and missing < 0.15 and contradiction < 0.15, or when continue_useful < 0.15. Hard caps: depth 8, 60 nodes, 2400 edges, 16 controller calls, 15 s. Beam of 10 per round. | `paper-jev-mem-2609.23986.md` | Paper |
| REALM's agentic loop: a sufficiency controller expands at most 5 nodes, falls back to the top unexpanded nodes, and relaxes seed filters in steps so a search never returns empty. Associative edges are about 35% of the graph but about 12% of evidence, so down-weight them. | `paper-memory-reconsolidation-2609.16053.md` | Paper |
| Never give a recall gate or cutoff a "nothing relevant" option. A "none of these" option emptied 35 of 200 queries. A "nothing" level emptied 7% and cut gold retention from 0.81 to 0.65. Always return at least one memory. Pruning lifts precision (0.051 to 0.850) but drops 19% of gold evidence and caps results at 12, so keep ranking on and pruning off by default. | `x-article-vectorize-hindsight-jev-reranker.md`, `x-article-supermemory-jev-memory-context.md` | Vendor, two teams |
| Put the decision model on the recall/no-recall gate, i.e. whether to retrieve at all. Supermemory runs it in a `UserPromptSubmit` hook and it honours "without using memory". It works qualitatively; no numbers are given. | `x-article-supermemory-jev-memory-context.md` | Vendor, qualitative |

## 3. Update on read (reconsolidation)

The trend "Memory that updates on read" (T3) is **weaker than the hub states**:

- **Hindsight does not update on read.** Recall writes nothing, and a 2026-08-03 migration dropped the unused `access_count` column. Its learning happens at write time, when an LLM merges facts into observations and mental models. Recency and evidence boosts are computed at read time but never stored. (`github-vectorize-io-hindsight.md`)
- **Hippo does update on read.** Each recall adds 1 to the retrieval count, resets the decay clock and adds 2 days of half-life. Strength = `0.5^(days/(hl*rewardFactor)) * (1+0.1*log2(n+1)) * valence`, halved per net "bad" mark (capped at 3). But the repo's own audits found that age decay had no measurable effect and sleep consolidation cost 3.6 points. LongMemEval never exercises decay, and the magnitude of the Sequential Learning Benchmark was retracted in v1.7.9. (`github-kitfunso-hippo-memory.md`)
- **REALM (arXiv 2609.16053) does reconsolidate,** but only by reweighting or adding edges, never by rewriting node content or deleting edges. An LLM auditor labels each recalled node as key evidence, supporting, misleading or unrelated. The updates are bounded: `w += eta*c*(1-w)` to strengthen and `w -= eta*c*(w - w_min)` to weaken, a new edge starts at c (or 0.8c), and eta < 1. Retrieval uses the weights: access = 0.6*sim + 0.4*w, final = 0.8*access + 0.2*sim, K = 10. Measured gain from reconsolidation: +2.01 on LoCoMo, +2.13 on LongMemEval. The paper gives three conflicting versions of the update formula, and never states w_min, eta, or whether the feedback includes gold answers. (`paper-memory-reconsolidation-2609.16053.md`)

**Feedback-loop risk (the trend's watch question) is unmeasured everywhere.** REALM uses the same GPT-4o-mini model to answer and to audit. In Hippo, a wrong memory nobody marks still gets strengthened on every read. Nobody reports the rate of this. (inference) If you add read-time strengthening, log every weight change with the query that caused it. Cap strengthening from a single source. Evaluate on the LongMemEval knowledge-update subset specifically, and on an abstention set you build yourself (REALM excluded abstention).

## 4. Consolidation and forgetting

| Finding | Source |
|---|---|
| Every 20 writes, run a non-destructive consolidation decision: keep_separate, merge, promote or uncertain. Call the LLM summarizer only when merge or promote scores at least 0.85 and contradiction is below 0.85. Raw observations are always kept. | `paper-jev-mem-2609.23986.md` |
| No source implements real forgetting. Jev-Mem records obsolescence but never acts on it. REALM has no decay. Hindsight has none. Hippo has decay but its own audit found no measurable effect. | all four memory sources |
| Prune components whose recent measured gain is zero or less. Keep a ledger of hypothesis, diff, score change, cost change and accept/reject outside the memory itself, so failed ideas stay failed. | `rrsi-regularized-recursive-self-improvement.md`, `evoskill-skill-evolution-frozen-model.md` |
| Raw trajectories often beat distilled skills, and generated skills sometimes make results worse. This comes from papers cited in the EvoSkill roundup. | `evoskill-skill-evolution-frozen-model.md` |

## 5. Decision model (Jev) as the control plane: how to call it

- **API:** `POST https://api.typesafe.ai/v1/systemone` with body `{state, model, questions}`. The question types are `noul` (yes/no), `choice` (up to 255 options) and `score` (2 to 10 levels). A noul answer is only `{"type":"noul","noul":P}`, with no confidence field; choice and score answers add probabilities and confidence. jev-1.13.0 costs USD 0.042 per million input tokens and output is free. Context is limited to 64k or 32k. (`docs-typesafe-jev-api.md`)
- **Phrasing that works:** ask each control question as a yes/no proposition with explicit true and false criteria, and batch every question that shares a state into one call. Jev-Mem uses 2 calls per write, and 1 plus up to 2 per retrieval round. (`paper-jev-mem-2609.23986.md`)
- **Calibration:** claimed by the vendor, but no calibration metric is published. Jev-Mem's authors say the scores are not calibrated probabilities, yet they apply hard thresholds anyway. Datadog shows JEV_CUSTOMER_IMPACT values of 1.100 and 1.060, which are above 1 and so cannot be probabilities. Fit thresholds on your own data. (`docs-typesafe-jev-api.md`, `paper-jev-mem-2609.23986.md`, `images-transcribed.md`)
- **Operating advice from Datadog:**
  - Log raw probabilities, not pass/fail.
  - Pin the model version.
  - Keep thresholds in code.
  - Add an explicit "unclear" option where it is safe to. Section 2 explains why a recall gate must not get a "nothing" option.
  - Send a minimal state, because irrelevant state lowers accuracy.

  (`datadog-jev-evals-agent-observability.md`)
- **Vendor-listed failure modes:** poor date comparison, context rot, and trusting state that should be treated as hostile. (`docs-typesafe-jev-api.md`)
- **Where it fails:**
  - tazr_dev tried 6 Jev-style fast actions in a coding agent and dropped them all. Only "is the goal done?" looked promising. Note that `reflex` never fired, so most verdicts rest on small samples.
  - Deel regressed by 16.6 points on metric picks from messy real questions, and by 3.6 on 3-level root-cause tagging.

  (`x-posts-jev-builders.md`, `images-transcribed.md`)
- **Operational constraints:** it is a hosted API, so memory text leaves your infrastructure. It fails closed. Keep a fallback (RRF or an LLM) behind a confidence threshold. (`x-posts-jev-builders.md`)

## 6. Evaluating the memory stack

- **Strongest field evidence:** Sentry (rbro112) used Jev as a pass/fail eval judge in place of Gemini 3.1 for a week. Accuracy showed no meaningful change, cost fell about 200x ($0.01 to $0.00005) and latency about 50x (10 s to 0.2 s median). The pass threshold is > 0.8, and an LLM explains only the failures. A full run costs $0.14 to $0.20, so latency, not money, decides whether evals can gate every PR. (`x-posts-jev-builders.md`, `images-transcribed.md`)
- **Noise floor:** run the unchanged stack several times and use the score spread as the minimum gain a change must beat. Charge memory for the tokens it uses: cost change at most b0 + b1 times gain. Allow bundled changes early, then one attributable change per round (RRSI's annealed edit budget). (`rrsi-regularized-recursive-self-improvement.md`)
- **Benchmark coverage gaps in the sources:**
  - Jev-Mem reports only LoCoMo, despite saying "two benchmarks".
  - REALM excludes unanswerable questions.
  - Nobody tests abstention, feedback loops or forgetting.

  (inference) Build a held-out set with knowledge updates, contradictions and questions that should be refused.

## 7. Self-improvement and oversight: why this matters for memory

- A memory that learns from outcomes is a self-improvement loop, and it will learn to route around guardrail blocks and denials even with no bad intent (Mallen). Countermeasures:
  - Tag writes that came from blocked episodes.
  - Track the guardrail-trigger rate over time; a falling rate is a warning sign, not a success.
  - Keep at least one check that never feeds memory writes.
  - Use the fact that memory, unlike weights, can be audited and deleted.

  (`continual-learning-blocking-monitors-mallen.md`)
- Place your stack on the B0 to L5 ladder from arXiv 2609.11873 (summarised in `china-ai-bulletin-12-rsi-levels.md`). EvoSkill and RRSI sit at L2: a fixed objective and evaluator, with the AI choosing the edits. Learning from live deployment is L4. (inference) Keep the evaluator fixed and outside the memory's write path to stay at L2 on purpose.
- Regulatory context (low relevance): the Sanders and Casar superintelligence-ban bill, the Amodei essay and Sakana's RSI lab. (`sanders-casar-superintelligence-ban.md`, `amodei-pace-the-frontier-and-accenture-evaluation.md`, `sakana-rsi-lab.md`)

## 8. Where the evidence contradicts the hub's trend claims

| Hub claim | What the sources actually show | Source |
|---|---|---|
| T1: Jev-Mem LoCoMo 0.777 (+11%), 158 s (6.6x) | The numbers match. But the build-time comparison is against Nemori and the latency comparison against MAGMA, only one benchmark is reported, there are no ablations, and the text and tables disagree in 4 places. | `paper-jev-mem-2609.23986.md` |
| T1: Supermemory "up to 58% token reduction across reranking, chunking, filtering, gate" | The 58% applies ONLY to the pre-extraction filter, which also produced a wrong memory. No token numbers are given for the other techniques. | `x-article-supermemory-jev-memory-context.md` |
| T1: bijitghosh21 "one Jev layer across routing, memory, retrieval..." | The article covers routing, gating, approvals, recovery and verification. There is no memory or retrieval, and no numbers. | `medium-bijit-jev-agent-harness.md` |
| T1: Beacon "Jev as a write gate" | It is a candidate filter in front of human review, and there are no quality metrics. | `github-asymptote-labs-agent-beacon.md` |
| T2: Deel "70 to 97%, 50 to 86% (vs human reviewers), up to 4x faster" | The chart also shows regressions of -16.6 and -3.6. The expense baseline is rule-based matching, not human reviewers. "4x" is one task in live shadow (1.9x offline for the same task). | `images-transcribed.md` |
| T2: tazr_dev "none survived, too unreliable" | `reflex` never fired and `met` looked promising. The verdicts rest on small samples, not measured failure rates. | `images-transcribed.md`, `x-posts-jev-builders.md` |
| T2: hamzaashergill "second team independently reports..." | There is no independent data; the post reuses rbro112's screenshots. | `images-transcribed.md` |
| T3: Hindsight updates on read | It does not (see section 3). | `github-vectorize-io-hindsight.md` |
| T3: Hippo 74% R@5 | An old v0.11 BM25-only number. Current scores are 98.0 to 99.8% per haystack, and decay was never exercised. | `github-kitfunso-hippo-memory.md` |
| T3: REALM LoCoMo +7.17 over MAGMA | Correct, but reconsolidation adds only +2.01. LongMemEval is +1.31 over Zep, and it falls below Zep without reconsolidation. | `paper-memory-reconsolidation-2609.16053.md` |
| T4: EvoSkill OfficeQA 68.1% | The paper says 67.9%. Validation used 17 examples, each configuration was run once, and there is no per-skill pruning. | `evoskill-skill-evolution-frozen-model.md` |
| T4: RRSI Terminal-Bench 74.2 to 80.2 | Confirmed in the paper. Frontier-Eng is only "+4.3 Medal points"; 17.7 to 22.0 is unconfirmed. The project page and the abstract disagree on the benchmark count and the token savings. | `rrsi-regularized-recursive-self-improvement.md` |
| T5: Benzinga 800 fixes / 1,000x / four person-years | Not in the Amodei essay text. The original source is unidentified. | `amodei-pace-the-frontier-and-accenture-evaluation.md` |

## 9. A starting configuration to test (inference, assembled from the above)

1. **Store:** keep raw observations always. Build a typed graph with deterministic edges (time, exact entities) plus model-confirmed edges (confirm at score >= 0.60 from up to 10 candidates). Write `supersedes` and `contradicts` edges at write time.
2. **Retrieve:** fuse vector, BM25, entity and time with RRF k=60, then rerank listwise in one decision-model call. Always return at least 1 result, and keep pruning off.
3. **Gate:** run a recall/no-recall decision in front of retrieval. Promote a lesson into durable memory only on task_success >= 0.50 AND quality mean >= 0.60, then review it.
4. **Stop:** use a sufficiency rule with hard caps rather than a fixed top-k.
5. **Update on read:** reweight edges only, with bounded updates, and never rewrite content. Log every change and measure the rate of feedback loops.
6. **Consolidate:** merge or promote non-destructively every N writes, and only above 0.85.
7. **Evaluate:**
   - Use a fast decision-model judge on every change.
   - Set the noise floor from repeated baseline runs.
   - Build a held-out set with knowledge-update, contradiction and abstention questions.
   - Keep an experiment ledger outside memory.
   - Keep one guardrail that never feeds memory.
