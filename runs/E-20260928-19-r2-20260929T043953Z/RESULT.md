# E-20260928-19-r2: Jev as a filter that picks which code to show an agent

We asked 79 "where is this decided / what happens when" questions about the public Apache OpenDAL codebase. The correct lines of code were marked in advance. For each question we gathered up to 200 candidate 40-line code windows by keyword search. Then we let four methods choose which windows fill a 12,000-token pack. Jev, as used by the open-source genigrep tool, first judges which files matter, then which passages. The others are the same pipeline with plain keyword scores, raw keyword ranking, and a free local reranker model. Jev put the most correct code into the pack: 78% of the marked answer spans, against 61% for the same pipeline on keyword scores, 70% for raw keyword ranking and 69% for the local reranker. It also used about a third of the token budget (about 4,400 of 12,000 tokens) and cost about a quarter of a US cent per question. By the spec's rule the result is positive: Jev earns its place at the reranking stage for code evidence. One caution matters as much as the result. The keywords that came with the dataset were written by the same model that marked the answers. With those leaked keywords, raw keyword ranking finds 97% of the answers and beats Jev. So we used a second, blind keyword set for the decisive run, and any future test must use blind keywords too. Recommended next step: an agent-level cost test (Jev-filtered code packs against plain search in a coding agent), sized from these pack statistics. Keep the keyword guard: it costs nothing, although here it barely mattered.

## Numbers

Decisive run: blind keywords (claude-sonnet-5-5 saw only the question, the README and the directory tree). 79 questions (codeq-027 excluded: its answer sits in a file the secret scan flagged), 19 module clusters, 95% cluster bootstrap over modules (10,000 resamples). Mean pool 197 windows; the pool contains 80.6% of gold spans (the ceiling for every arm).

| Arm | Gold-span recall | Line recall | Full coverage | Mean pack tokens |
|---|---|---|---|---|
| A: keyword (IDF) order, lexical floor | 0.705 | 0.728 | 0.608 | 11,941 |
| **B: genigrep Jev file + passage scores** | **0.783** | **0.866** | **0.684** | 4,420 |
| B without the top-5 keyword guard | 0.778 | 0.857 | 0.684 | 4,099 |
| C: same pipeline, keyword scores instead of Jev | 0.605 | 0.657 | 0.443 | 6,405 |
| D: bge-reranker-v2-m3, local | 0.690 | 0.746 | 0.595 | 11,925 |

Paired differences in gold-span recall:
- B minus C: **+0.177 [+0.127, +0.265]** (at least 5 points, interval excludes zero).
- B minus A: **+0.078 [+0.034, +0.137]** (beats the floor).
- D minus B: **-0.093 [-0.193, -0.045]** (one-sided 95% lower bound -0.171, far below -0.03, so the local reranker is not non-inferior).
- B minus B without guard: +0.004 [0.000, +0.018] (the guard kept one or two spans; B11 weakly supported).
- Line recall: B minus C +0.210 [+0.164, +0.288]; D minus B -0.120 [-0.210, -0.065].

**Spec rule (`verdict.json`): positive** (validity: span agreement 0.93 first pass, keywords frozen before the pool and not written by a gold annotator, repository and engine config at the pins, secret-flagged share 0.85% <= 1%).

Jev run-to-run: re-scoring 20 questions changed no question's recall (mean absolute change 0.000); the packed windows overlapped 93% (Jaccard). Cost: 1,540 Jev requests, 6.15M input tokens, 0.26 USD for 79 questions plus 20 repeats; 1.7 s of Jev time per question.

Secondary run with the dataset's own keywords (written by claude-opus-5-5, the gold annotator): **invalid by the spec's rule**. Recall: A 0.968, B 0.905, C 0.854, D 0.795; B minus C +0.051 [-0.004, +0.131]; B minus A -0.063 [-0.117, -0.024]. The pool built from these keywords contains 99.3% of gold spans, against 80.6% for blind keywords: the keyword writer knew where the answers were.

## Weaker than the spec wanted

- **Model-written everything.** Claude wrote the questions, the dataset keywords and the gold spans; Codex reviewed (span F1 0.93 first pass, 0.99 final; 4 contested). The spec wanted two engineers for gold and a third, blind engineer for keywords. Blind keywords here come from a different Claude model with the same inputs the spec allows the keyword engineer.
- **Arm C is a re-expression, not a patch.** genigrep's file selection (lexical guard 5, minimum 8, maximum 16 files, T1 0.6) and passage filter (T2 0.5) are re-implemented in Python for C and for the selection step of B; Jev scoring itself runs through genigrep's own `JevJudge` and prompts at da10c5e (called with bun). No sub-questions are passed (the frozen questions have none).
- **Pool.** Windows are fixed 40-line windows around keyword hits plus one-hop universal-ctags definitions (up to 4 rare identifiers from each of the top 40 windows). genigrep's own window shaping and lead following are not used, by design.
- **Cross-encoder settings.** bge-reranker-v2-m3 ran in float16 on the Mac GPU with inputs cut at 512 tokens (a 40-line window mostly fits) because 1,024 tokens in float32 would have taken about 3 hours per pool. A longer cut might help D somewhat; it is unlikely to close a 9-point gap.
- **Packing tokens** are counted with tiktoken o200k_base over the rendered window block.
- **Policy gates** replaced by the CTO's fast-track queue and policy v2.

## Files

`verdict.json` (rule output, blind run), `engine_config.json`, `run_manifest.json`; per variant (`blindkw/`, `frozenkw/`): `questions.jsonl` (keywords used), `pool.jsonl`, `pool_manifest.json`, `pool_stats.jsonl`, `secret_scan.json`, `jev_calls.jsonl`, `jev_scores.json`, `cross_scores.json`, `packs/`, `coverage.csv`, `metrics.csv`, `rule_inputs.json`, `jev_repeat.jsonl`, `run_manifest.json`. Commands from `harness/`: `codeq_run.keywords`, `codeq_run.pool`, `codeq_run.arms {jev,cross,score}`.
