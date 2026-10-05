---
schema_version: 1
artifact_id: N-20260929-21
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104768786918195403", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:grivn/mnemon-memory-agent
claim_cluster: github:grivn/mnemon-memory-agent
feeds: ["memory"]
primary_source: https://github.com/Grivn/mnemon-memory-agent
source_commit: 392b276113ded01f2040fee40382b2aae8e492b4
strength: paper-ablated
pillar_primary: R9
pillar_secondary: ["R3", "R6", "R2"]
memory_stage: reranking
priority: 1
tags: {"mechanism": ["system-one-judge", "per-record-noul", "hybrid-retrieval-bm25-embeddings-rrf", "fill-view-by-rank", "no-longer-current-judgment", "background-consolidation-overlay-index", "planner-hyde"], "workload": ["chat-memory", "locomo", "longmemeval-s", "halumem", "beam"], "lifecycle_stage": ["read-time", "consolidation"], "cross_cutting": ["cost", "latency", "judge-shares-model", "copied-baselines", "single-run"]}
evidence_grade: {"directness": "medium: Jev-vs-LLM judging is measured directly on 14,359 records, but the 91.7% headline is a whole-system score with no Jev-removed or LLM-substituted arm", "control": "medium: component ablations with paired 95% CIs and McNemar tests, but each configuration ran once, identical reruns differed by up to 2.6 points, and the 14 baselines are copied from OmniMemEval with a different grader", "independence": "low: single author evaluates own system; primary grader gpt-4.1-mini is the same model that plans and answers; baselines table maintained by MemTensor (MemOS vendor); Jev-Mem rerun by the Mnemon author", "reproducibility": "high: run records, collect.py and datasets reproduce results.json byte for byte per README; HaluMem records and replica traces not included; live reruns need hosted Jev", "applicability": "low-medium: conversational chat memory only; the author's own long-task agent experiment found no stable Jev gain on delivery work closer to our PDLC workload"}
beliefs_affected: {"supports": ["B7", "B8", "B11", "B13"], "contradicts": ["B5"], "would_create": ["R9: on per-record relevance judgments over a retrieved pool, Jev separates gold evidence better than general LLM judges given the same proposition (AUC 0.942 vs 0.900 DeepSeek vs 0.853 gpt-4.1-mini, 14,359 records) at about 3-11x lower per-call latency; end-to-end effect of the substitution untested"]}
claim_correction: Rank 1 of 15 compares Mnemon graded by gpt-4.1-mini (its own planner and answerer) against 14 OmniMemEval numbers graded by gpt-4o-mini; Jev was never removed or substituted in the full system, so 91.7% is not attributable to Jev; token efficiency counts only the 3.8k answer context, not the 35-73k Jev tokens per question; 3-11x is per-call latency on 24 records.
---

# Mnemon: raw records judged at read time by Jev (System 1) with an LLM planner (System 2); 91.7% LoCoMo vs Mem0, Letta, Zep, supermemory, Hindsight

- **URL:** https://github.com/Grivn/mnemon-memory-agent (paper: `docs/paper/main.pdf`, LaTeX in `docs/paper/sections/`)
- **Type:** repo (frozen research snapshot plus unreviewed preprint "Mnemon: Raw Records, Fast Judgments, Slow Thoughts")
- **Author / org:** Guangren Wang (README citation block). Research branch `codex/jev-replica-practice` of dsh-mnemon, forked from dsh-mnemon v0.5.13; code MIT, paper all rights reserved. Relation of the author to TypeSafe: not stated.
- **Date:** snapshot of research branch at `50a6831d` (2026-09-29 per README "About this snapshot")
- **Retrieved:** 2026-09-29, commit `392b276113ded01f2040fee40382b2aae8e492b4` (2026-09-29 04:55:21 +0800, "Say where the research goes next: DSH as a micro agent kernel"); local shallow clone `repos/mnemon-memory-agent`. Read: README.md; docs/paper/sections/{protocol,system,analysis,limitations}.tex; docs/paper/tables/{ablation,system1,ours,heldout,self_reported}.tex; docs/paper/references.bib (OmniMemEval, Jev-Mem, Jev entries); docs/reports/phase02-20260925.md (sections 1-3); docs/reports/bench-full-20260924.md section 8; docs/reports/jev-long-tasks-20260923.md (header). Cross-checked OmniMemEval results page (1 WebFetch).
- **Cited by evidence:** post 2104768786918195403, @grivn_eth, https://x.com/grivn_eth/status/2104768786918195403 ("We improved our memory system Mnemon with a System 1 model: Jev from @typesafeai, which judges raw records better and 3-11x faster than LLMs. With Jev as its System 1, Mnemon scores 91.7% on LoCoMo, first of 15 systems answering with gpt-4.1-mini, at very high token efficiency.")
- **Relevance to a memory stack:** high. A fully specified read-time pipeline (plan, hybrid retrieve, Jev screen/judge, need loop, budgeted View) with component ablations and a direct Jev-vs-LLM judging comparison; a clear map of where a System One model sits (reranking/filtering, plus a "no longer current" staleness judgment at read time).

## TL;DR
- Jev sits at **read-time reranking/filtering**, not at the write gate: records are written raw (no LLM on the write path, one embedding). Per turn an LLM plans 5 searches and up to 3 needs; BM25 + embeddings fused by RRF build a pool of 48; Jev "screens" each record ("should the reply use this record?"), then "judges" candidates as needed / no longer current and fills a need table; rules loop up to 3 rounds and compose a View of at most 16 records and 12,000 chars (`docs/paper/sections/system.tex` lines 83-129).
- LoCoMo protocol: 1,540 non-adversarial questions (category 5 excluded), Mem0 lenient grading prompt, gpt-4.1-mini (temperature 0) answers and plans and is also the primary grader; DeepSeek-V4.1-Flash grades as second grader (91.4). Each configuration ran once; two identical runs of an earlier configuration differed by up to 2.6 points (limitations.tex line 7). Developed on LoCoMo and LongMemEval, so neither is held out.
- The "15 systems" comparison is **copied**: the other 14 numbers are OmniMemEval's (MemTensor), graded by gpt-4o-mini; the paper states a 1-2 point grader difference. MemOS is 88.83, 2.9 points below 91.7, which is close to the observed 2.6-point run-to-run spread (inference).
- **Claim correction:** there is no with-Jev vs without-Jev ablation in the full system ("no substitute was tested in the full system", limitations.tex line 11). The Jev evidence is a separate offline judging study: AUC 0.942 vs 0.900 (DeepSeek) and 0.853 (gpt-4.1-mini) on 14,359 records from 599 questions; "3-11x" is median per-call latency on 24 records (0.34 s vs 1.05 s and 3.74 s). "Token efficiency" is the 3.8k tokens sent to the answering model; Jev itself reads 35-73k tokens per question (README).
- Most transferable finding (B11): a Jev "needed >= 0.4" admission threshold lost evidence; filling the View to 8 records by Jev rank (min 0.1) raised the raw-record arm from 75.2% to 86.2% on a 210-question dev set (phase02 report). The author's own long-task agent experiment (576 inputs, 18 task flows including a web project and a technical research report) found "no evidence that JEV can stably improve full-task delivery quality" (translated).

## What it claims / describes

**Architecture** (system.tex, README "Approach"). Mnemon runs as a second DeepSeek Harness (DSH 0.1.5-rc.1) instance beside the main agent and publishes one "View" per user turn into the main agent's context.
- **Memory:** each session written as short `speaker: text` chunks headed by session number and date. "No LLM is on the write path of a record, and nothing about it is decided when it is written; the only computation is one embedding" (system.tex line 68).
- **Consolidation (background, off read path):** a small LLM (DeepSeek-V4.1-Flash without thinking) reads the journal once, in order, and folds it into an index of three item kinds, each linked to its records: events on topic timelines; dated value histories "marked where a value contradicts an earlier one"; standing instructions and preferences. "Items point to records and never replace them" (system.tex lines 72-73).
- **Plan (System 2):** two parallel LLM calls over the last six messages. Search plan: three searches "in the words a stored record would use" plus one HyDE hypothetical record; with the message itself, five searches. Need plan: at most three needs, marked `NEED` or `ALL` (every instance: counts, totals, lists). Neither call reads the journal.
- **Retrieve:** per search, BM25 and embedding rankings (nomic-embed-text, local) fused by RRF (k not stated in the sections read); pages merged into a pool with an equal per-search quota of top results, remaining slots by summed reciprocal rank; pool of 48.
- **Judge (System 1, Jev `jev-1.13.0` via `@typesafe-ai/sdk` 0.6.0):** screen each pooled record ("should the reply use this record?"); then judge View candidates "jointly and with the last six messages, as needed or no longer current (a later message or record explicitly changes, cancels or completes it)"; fill a need table ("does this record satisfy this need?"); then judge which index items the reply needs among items linked to judged records plus "the dozen nearest to the message". Counting, arithmetic, date comparison and multi-hop are explicitly left to System 2 because Jev "handles poorly" (system.tex line 99).
- **Rules:** use only Jev's decision at p >= 1/2 and its ranking. Budgets: 3 needs per turn, pages of 20 records or 12,000 chars, pool 48, 3 rounds, View 16 records and 12,000 chars. A proposition ("Calibration invariance") shows any strictly increasing remap of p fixing 1/2 leaves the View unchanged, so a different decision model that "orders and decides alike" needs no retuning.
- **Loop:** single need met once a record satisfies it; `ALL` needs page each search that found a new positive until none does; an unmet need follows its "lead" (top record in the need table): page the search that ranked it highest, then ask the planner for one new search, then drop.
- **View:** index blocks first (standing instructions, one-line topic directory, judged timelines and value histories), then records judged needed, then (when a need was named) the rest in Jev's ranking up to budget; records judged no longer current are excluded.

**Jev vs LLM judging study** (analysis.tex lines 4-8, tables/system1.tex). gpt-4.1-mini and DeepSeek were given "the proposition Jev answers, with the same dialogue and records" for 599 LoCoMo and LongMemEval questions (14,359 records, 1,004 gold evidence). Gold labels are the benchmark's evidence annotations (inference from "gold evidence"). How the 599 questions were sampled: not stated in the sections read.

**Jev-Mem comparison** (analysis.tex lines 17-27). The Mnemon author ran Jev-Mem's released code (default profile, Jev 1.13) under Mnemon's protocol: same 1,540 LoCoMo questions, gpt-4.1-mini answering once per question from the question alone, both graders; Jev-Mem's default best-of-three-against-gold selection and per-category prompt were disabled. The paper states: "this is not an ablation".

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| LoCoMo accuracy, standard setting | 91.7 (gpt-4.1-mini grader) / 91.4 (DeepSeek grader) | MemOS 88.83, Cognee 83.48, EverMemOS 82.75, Hindsight 81.99, Mem0 77.68, Letta 77.12, Supermemory 73.53, Zep 63.83 (README "Under one protocol") | 1,540 non-adversarial questions, gpt-4.1-mini answers and plans (temp 0); tables/ours.tex line 13 | single run; baselines copied from OmniMemEval graded by gpt-4o-mini; primary grader = Mnemon's own System 2 model |
| LongMemEval-S accuracy | 83.8 / 85.4 | MemOS 89.2 (rank 2 of 13) | 500 questions; tables/ours.tex line 14 | same caveats |
| context sent to answering model | 3.8k tokens per question (LoCoMo) | MemOS 5.4k, Hindsight 24.7k, Mem0 17.4k, Letta 14.2k, Supermemory 15.2k, Zep 1.9k | README table | excludes planner, Jev and consolidation tokens |
| Jev tokens read per question | "35-73k tokens of records, 9-19 times what the answering model reads" | | README "Every benchmark and tier" | not in the headline efficiency claim |
| ECI (LoCoMo) | 0.259 | 0.337 next (mem9) | ECI = (1 - accuracy) + context / c_full, c_full = 21,613 tokens | index ignores planner, Jev, consolidation costs |
| cost per 1,000 questions (LoCoMo) | $3.27 | | answer + planner + Jev at list prices (Jev $0.042/M input) | consolidation $0.013 per history extra |
| Jev calls (waves) per median question | 5 (4) on LoCoMo; 10 (7) on BEAM-10M | | tables/ours.tex | |
| Jev latency | "5-10 Jev calls in 4-7 sequential waves of about 0.34 s each: 1.4-2.4 s in all" | | README "Work per question" | one laptop, public APIs |
| AUC separating gold evidence, all / LoCoMo / LME | Jev called again 0.942 / 0.950 / 0.939 | DeepSeek (no thinking) 0.900 / 0.934 / 0.872; gpt-4.1-mini 0.853 / 0.919 / 0.798 | 599 questions, 14,359 records, 1,004 gold; tables/system1.tex | same proposition for all judges; prompt wording for LLMs not read |
| precision / recall at 0.5 | Jev 0.76 / 0.60 | DeepSeek 0.42 / 0.79; gpt-4.1-mini 0.45 / 0.68 | same | Jev more conservative at 0.5 |
| recall of gold in top 4 / 8 / 16 | Jev 0.88 / 0.95 / 0.99 | DeepSeek 0.89 / 0.95 / 0.99; gpt-4.1-mini 0.88 / 0.94 / 0.98 | same | ranking recall is essentially tied; the AUC gap is in the tail (inference) |
| median latency per call of 24 records | Jev 0.34 s | DeepSeek 1.05 s; gpt-4.1-mini 3.74 s | same | basis of "3-11x"; Jev also answers "no longer current" per record in that call |
| price per call | Jev 0.44e-3 $ | DeepSeek 0.66e-3 $; gpt-4.1-mini 1.70e-3 $ | same | list prices |
| Jev rerun stability | Spearman rho 0.89 with recorded scores | LLMs rho 0.50 / 0.48 vs recorded Jev scores | same | rho for LLMs is agreement with Jev, not self-consistency |
| ablation: consolidation (gpt-4.1-mini reader) | +2.5 [+1.1, +3.9]* LoCoMo; +4.4 [+0.7, +8.1]* LME | Mnemon without consolidation | paired, exact McNemar; tables/ablation.tex line 18 | labelled exploratory |
| ablation: hybrid retrieval (gpt-4.1-mini) | +1.4 [0.0, +2.8] LoCoMo; +1.0 [-2.0, +4.0] LME | BM25 only | tables/ablation.tex line 13 | not significant with this reader |
| ablation: loop and unsure fill (gpt-4.1-mini) | +0.7 [-0.5, +1.9] LoCoMo; +2.4 [-0.6, +5.4] LME | without | line 16 | not significant |
| ablation: no planner (gpt-4.1-mini) | -0.8 [-2.1, +0.5] LoCoMo; -5.8 [-9.2, -2.4]* LME | with planner | line 19 | |
| ablation: all together (gpt-4.1-mini) | +3.7 [+2.2, +5.2]* LoCoMo; +6.6 [+2.8, +10.4]* LME | cue recall over BM25 (S0) | line 20 | Jev present in both arms (inference from S0 definition "cue recall") |
| Mnemon vs Jev-Mem, LoCoMo | 91.7 vs 84.4 (gpt-4.1-mini grader); 91.4 vs 82.1 (DeepSeek); paired diff 7.3 points (95% CI 5.5-9.2) | Jev-Mem released code | 1,540 questions, one answer per question | "not an ablation"; Jev-Mem write-time cost $0.12 vs $0.013 per history |
| fill View by rank vs threshold (phase 2) | raw arm 75.2 -> 86.2 (+11.0, p < 0.001) on dev; LoCoMo raw 78.3% -> 88.2% on 1,390 non-dev questions | "needed >= 0.4" admission line | docs/reports/phase02-20260925.md "Conclusion" item 1 and section 3 | earlier configuration; reasoning model was DeepSeek per report header (inference: runs in DeepSeek off-peak) |
| full-context reference (phase 2) | 92.6% LoCoMo (1,390), 95.2% LME (440) | memory arms 84.1-88.2% | phase02 section 3 table | earlier configuration, not the paper's final protocol |
| full-context, continuous session (LoCoMo) | 93.2% | "JEV full scheme" 89.1%, "JEV cached scheme" 89.4% | bench-full-20260924.md section 8.2, 1,540 questions | earlier configuration |
| Jev on long agent tasks | main-model input -12.6%, known main cost -5.7%; turn-end median latency 35.69 s vs 32.96 s; normal completions 134/192 vs 148/192 | all-candidates arm | docs/reports/jev-long-tasks-20260923.md line 5; 576 user inputs, 3 scenarios, 2 runs per arm | author: "not a stable quality, cost or interaction-speed improvement" (translated) |
| run-to-run spread | "two identical runs of an earlier configuration differed by up to 2.6 points" | | limitations.tex line 7 | each configuration ran once |
| grader agreement | "96-97% of answers (Cohen's kappa 0.85-0.89)" | | protocol.tex line 17 | agreement between two graders, not vs humans |
| self-reported gpt-4.1-mini systems | SmartSearch 93.5, EverMemOS 93.05, H-Mem 92.01 on LoCoMo | | tables/self_reported.tex | own evaluations, judges differ; shows 91.7 is not the top published gpt-4.1-mini claim |

## Mechanism details you could implement
- Put the System One model on the **read path as a per-record screen and judge over a fixed pool** (48 records from 5 searches, BM25 + embedding RRF), not as a write gate. Write raw, dated records with one embedding.
- Judgment types that worked as typed yes/no: "should the reply use this record?"; "needed"; "no longer current (a later message or record explicitly changes, cancels or completes it)"; "does this record satisfy need N?"; "does the reply need index item X?". Keep counting, arithmetic, date comparison and multi-hop in the LLM.
- Rules consume only `p >= 0.5` and rank order, which makes the pipeline invariant to monotone recalibration (their Proposition 1). Useful if we swap Jev for an open-weight model (Laya, Intern-Decision): only order and the 0.5 decision need to match.
- **Do not admit by an absolute threshold alone:** after the needed set, fill the View up to a budget by Jev rank (phase 2 rule: fill to 8 records, needed >= 0.1, at most 2 per source first). Final budgets: View 16 records / 12,000 chars.
- Need-driven loop, 3 rounds max: `ALL` needs keep paging searches that yield new positives; unmet needs page the lead's best search, then one planner rewrite, then drop. Only unmet needs call System 2 again (6-31% of questions).
- Consolidation as an **overlay** index linked to records (timelines, value histories with contradiction marks, standing instructions), built once per record in the background; the View leads with index items Jev judges needed. This was the one component with CI above zero in every reader/benchmark cell.
- Cost accounting to copy: report context-to-answerer, Jev tokens, planner tokens and consolidation separately; ECI = (1 - a) + c / c_full.

## Limitations, caveats, counter-evidence
- **Judge shares a model with the system:** in the standard setting gpt-4.1-mini is planner, answering model and primary grader (protocol.tex lines 12-17; README components table). The second grader (DeepSeek) is also Mnemon's System 2 in the reasoning setting.
- **Copied baselines, different grader:** the 14 comparison numbers are OmniMemEval's (MemTensor, https://github.com/MemTensor/OmniMemEval/blob/main/docs/user_memory/results.md), answer model gpt-4.1-mini-2025-04-14, judge gpt-4o-mini-2024-07-18, category 5 excluded, 1,540 questions (confirmed by WebFetch). Run counts or seeds there: not stated. OmniMemEval is maintained by the MemOS vendor, which tops its own LongMemEval-S table (independence note). OmniMemEval says its results "are not a claim that every adapter has reached a globally optimal product-specific configuration".
- **Single runs, not held out:** each configuration ran once; 2.6-point run-to-run spread observed; "none of the benchmarks is held out" (limitations.tex line 5); consolidation designed after seeing HaluMem and BEAM-100K. Questions that failed or got an empty View "were answered once more" (protocol.tex line 26).
- **No Jev ablation in the system:** "no substitute was tested in the full system" (limitations.tex line 11). The 3-11x and AUC claims come from an offline judging study; end-to-end accuracy with an LLM judge is unknown.
- **Full context is stronger in the author's own earlier runs:** 92.6% (LoCoMo, phase 2) and 93.2% (continuous session) vs memory arms around 88-89% then; LoCoMo histories are only 13-25k tokens, so memory systems mainly buy cost, not accuracy, on it (inference).
- **Agent-task counter-evidence from the same author:** on long multi-source task flows (event planning, a static web project, a Yjs/Automerge/SQLite technical research report), "there is currently no evidence that JEV can stably improve full-task delivery quality" (jev-long-tasks-20260923.md line 3, translated); completions 134/192 with Jev vs 148/192 all-candidates. The author attributes part of this to stale Views not being replaced (line 7).
- Hosted proprietary dependency (Jev); raw records retain everything, so deletion and retention must cover records and index (limitations.tex).
- Only conversational memory in one Source was evaluated; document, task or log stores "are untested".
- Scan scope: README, paper sections and three reports read; the other ~2,000 files (run records, plugins) were not scanned. No text addressed to an AI agent was found in the files read.

## Takeaways for tuning a memory stack
- Place the System One model at **reranking/filtering of a retrieved pool** with per-record typed yes/no, and keep the write path raw. This is the most direct evidence for that placement so far, but only on chat memory.
- Split **ranking** from **admission**: rank with Jev, admit by budget with a low floor (0.1) rather than a 0.4 or 0.5 cutoff. The +11-point swing from this rule alone is larger than any other component effect reported.
- If we compare Jev with an LLM judge, compare on AUC and on top-k recall: top-4/8/16 recall was nearly tied (0.88/0.95/0.99 vs 0.88/0.94/0.98), so at our View budget the benefit may be mostly latency and cost, not selection (inference).
- Treat "rank 1 of 15" as a leaderboard claim with grader and run-variance caveats larger than several of the gaps.
- For PDLC artifacts, an overlay index of value histories with contradiction marks and standing instructions is the component worth prototyping; it is also the part with the only consistently significant gain.

## Open questions
- End-to-end accuracy and latency with gpt-4.1-mini or DeepSeek substituted for Jev in the screen/judge steps (the missing ablation).
- How were the 599 judging-study questions sampled, and what exact prompt did the LLM judges receive?
- Variance across repeated runs of the final configuration; human agreement with the graders.
- Does the pipeline hold on long structured documents (specs, ADRs) where "records" are sections rather than chat turns?
- RRF constant k and embedding model version details for exact replication.

## Grading and labels
- **Directness:** medium. Jev-vs-LLM judging is measured directly; the headline accuracy is whole-system without a Jev-removed arm.
- **Control:** medium. Paired CIs and McNemar on component ablations; but single runs, 2.6-point run spread, and cross-grader copied baselines.
- **Independence:** low. Author evaluates own system; primary grader equals System 2 model; baselines from a vendor-maintained harness; competitor rerun by the author.
- **Reproducibility:** high for the offline numbers (run records plus `collect.py` reproduce `results.json`); live reruns depend on hosted Jev; HaluMem and trace data missing.
- **Applicability:** low-medium. Chat memory only; the author's own long-task agent study is null for Jev.
- **Pillars:** R9 primary (which System One model at which stage); R3 (retrieval and assembly), R6 (evaluation integrity: grader overlap, copied baselines), R2 (consolidation overlay) secondary.
- **Stage:** reranking (Jev screen and judge over the retrieved pool); also touches staleness ("no longer current") and consolidation.
- **Tags:** system-one-judge, per-record-noul, hybrid RRF, fill-by-rank, overlay consolidation; chat-memory benchmarks; read-time; cost, latency, judge-shares-model, copied-baselines, single-run.
- **Supports B7:** read-time judging of raw records beat write-time organisation (Jev-Mem 84.4 vs 91.7, not an ablation; phase 2 raw vs notes +3.6 [+1.6, +5.9] on LoCoMo).
- **Supports B8:** Jev-Mem's write-time relation graph scored 7.3 points below hybrid retrieval plus read-time judging with the same decision model (whole-system comparison).
- **Supports B11:** an absolute "needed >= 0.4" admission line lost evidence; filling by rank added +11.0 on the dev set.
- **Supports B13 (weakly):** larger general LLMs were worse judges than Jev on the same proposition (AUC 0.900 and 0.853 vs 0.942).
- **Contradiction: B5** ("Scheduled summarising consolidation has no published on/off result; nearest measurements are negative"). Mnemon reports an on/off consolidation result that is positive in every cell (gpt-4.1-mini reader: +2.5 [+1.1, +3.9] LoCoMo, +4.4 [+0.7, +8.1] LME; tables/ablation.tex line 18). Qualifier: the consolidation is an overlay index that never replaces records, labelled exploratory, single runs. Suggested revision: narrow B5 to summarisation that replaces raw records.
- **Would create (R9):** Jev beats general LLM judges on per-record relevance AUC at 3-11x lower per-call latency; end-to-end effect untested.

## Origin chain
- post 2104768786918195403 (@grivn_eth, likely the author Guangren Wang (inference from handle and repo owner "Grivn")) -> https://github.com/Grivn/mnemon-memory-agent at `392b2761` -> README "Highlights" and results tables; `docs/paper/tables/ours.tex` (91.7, rank 1/15); `docs/paper/tables/system1.tex` (AUC, latency: basis of "3-11x"); `docs/paper/sections/protocol.tex` (1,540 non-adversarial, graders, baselines copied from OmniMemEval); `docs/paper/sections/limitations.tex` (single runs, no Jev substitute tested).
- Baseline numbers -> OmniMemEval `docs/user_memory/results.md` (MemTensor), verified by WebFetch for protocol and several entries (MemOS 88.83, Hindsight 81.99, Cognee 83.48, EverOS 82.75, Letta 77.12).
- Independence: post author = system author = evaluator; no external replication. Jev is TypeSafe's product; author affiliation with TypeSafe not stated. Shares the Jev decision model with Jev-Mem (arXiv 2609.23986) and jevmem; Jev-Mem comparison run by the Mnemon author.
