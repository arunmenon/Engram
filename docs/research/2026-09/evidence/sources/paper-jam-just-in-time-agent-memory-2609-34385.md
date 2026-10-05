---
schema_version: 1
artifact_id: N-20260930-11
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:17:30Z
input_refs: [{"artifact_id": "post:2105115504226746670", "file_id": null, "sha256": null}, {"artifact_id": "post:2105164438051709321", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.34385
claim_cluster: arxiv:2609.34385
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.34385
source_commit: n/a
strength: paper-ablated
pillar_primary: R3
pillar_secondary: ["R2", "R6"]
memory_stage: retrieval
priority: 4
tags: {"mechanism": ["raw-history page store", "navigational summaries", "iterative agentic retrieval", "sufficiency stop", "trained retrieval policy"], "workload": ["chat memory", "long documents", "code QA transfer"], "lifecycle_stage": ["ingestion", "retrieval", "assembly"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high", "control": "medium", "independence": "low", "reproducibility": "medium", "applicability": "medium"}
beliefs_affected: {"supports": ["B7"], "contradicts": [], "would_create": ["An untrained iterative read loop over raw records does not reliably beat one-shot retrieval; the published gain comes mostly from training the retrieval policy"]}
claim_correction: none
---

# Just-In-Time Agent Memory with Runtime Agentic Research (JAM, arXiv 2609.34385)

- **URL:** https://arxiv.org/abs/2609.34385 (full text read at https://arxiv.org/html/2609.34385)
- **Type:** paper
- **Author / org:** Bingyu Yan, Chaofan Li, Hongjin Qian, Shuqi Lu, Chaozhuo Li, Zheng Liu (project lead). Beijing Academy of Artificial Intelligence; Peking University; Hong Kong Polytechnic University.
- **Date:** submitted 2026-09-28 (v1)
- **Retrieved:** 2026-09-30, arXiv HTML v1 (local copy of the HTML: repos/_src_arxiv_2609_34385.html). Code link in the abstract page: https://github.com/VectorSpaceLab/general-agentic-memory ("anonymized source code"); the repository was not cloned this run, commit unknown.
- **Cited by evidence:** https://x.com/GKwVDZgsWe5dQfF/status/2105115504226746670 (@GKwVDZgsWe5dQfF, paper brief), https://x.com/Lineumapp/status/2105164438051709321 (@Lineumapp, bare link). Also selected by the memory digest of 2026-09-30.
- **Relevance to a memory stack:** high. A controlled comparison of "keep the raw records and search them at question time" against write-time extraction systems (Mem0, A-MEM, MemoryOS, LightMem), with ablations that separate the storage layout from the trained search policy.

## TL;DR
- JAM stores complete raw sessions as files in a directory tree with short README summaries used only for navigation (the Memorizer). At question time a Researcher loops over three tools (`open`, `search`, `browse`) until a sufficiency check passes or 20 rounds are used.
- With a Qwen3.5-4B backbone, trained JAM reaches LongMemEval accuracy 65.20 against 56.20 for the paper's RAG baseline and 34.40 for Mem0; LoCoMo overall F1 52.09 against 43.37 (RAG) and 32.10 (Mem0). Table 1.
- The untrained version of the same loop is not better than RAG on LongMemEval: "w/o Training" scores 48.80 against RAG 56.20 (Tables 1 and 4). Most of the gain comes from training the Researcher (supervised fine-tuning, then GRPO), not from keeping raw logs.
- The summaries help a little and cost offline tokens: flat raw store 49.06 F1 on LoCoMo against 52.09 with the workspace, at 36,924.51 offline tokens per workspace (Table 8).
- The post's numbers match the paper. No claim correction.

## What it claims / describes

**Problem framing.** "Ahead-of-Time (AOT)" memory builds the memory before the request arrives and can discard detail that a later question needs. JAM is "query-conditioned context construction at runtime".

**Memorizer (write side).** Raw sessions are preserved as source files inside a hierarchical workspace. Each session gets a concise memo; each directory gets a README built from its children's memos or subfolders. Operations as written in the paper: `memorize(s_i, W_<i) -> mu_i` and `write(s_i, mu_i, W_<i) -> W_<=i`. Memo token sizes are not stated. The Memorizer backbone is Qwen3.5-4B by default; swapping it for Qwen3.5-122B-A10B or GPT-5.5 changes LoCoMo F1 by less than 1 point (Table 12).

**Researcher (read side).** An iterative think, explore, reflect loop. Tools:
- `open(p)`: read the README and the directory listing at path p.
- `search(k)`: hybrid BM25 plus dense retrieval (BGE-M3); top 5 from each, merged and deduplicated.
- `browse(p, k)`: read a path and extract the query-relevant information.
The loop stops when the sufficiency assessment (`Reflect`) is true or when the default budget of 20 action rounds is used.

**Training.** Base model Qwen3.5-4B.
1. Verified-trajectory supervised fine-tuning: a teacher (Qwen3.5-122B-A10B) generates trajectories, Gemini 3 Flash filters them. About 5 hours on 8 x H100 80GB.
2. Hint-guided GRPO from the SFT checkpoint: reward is source recall (retrieved evidence that is in the gold evidence set, divided by the gold set size); group size 8; learning rate 1e-6; KL coefficient 0.001; clip 0.2; 200 optimisation steps; about 6 hours on 8 x H100 80GB. The hint frequency value is not stated.

**Memory-Gym (training data).** Nine task types (single-hop: attribute extraction, concept explanation, condition localisation; multi-hop: comparison, provenance tracing, intersection selection; summarisation: state evolution, set enumeration, aggregation) across six domains (web, books, dialogue, news, academic papers, long documents). 28,276 candidates generated, 16,794 retained (59.4%). A human audit of 200 retained instances passed 95.0% on all applicable criteria (95% Wilson interval 91.0% to 97.3%). Contamination control, verbatim: "although LoCoMo is included as a dialogue-domain source, we do not use any released LoCoMo evaluation conversations, questions, answers, or supporting evidence. Instead, we generate new LoCoMo-style dialogue corpora using the official data-generation pipeline".

**Evaluation.** Four benchmarks: LoCoMo (F1), LongMemEval (accuracy), NarrativeQA (F1), HotpotQA (F1 at 56k, 112k and 224k context). "We use the official evaluation metric for each benchmark". Test set sizes are not stated in the text read. An extra LLM-judge table uses GPT-4o-mini at temperature 0 (Table 11), a different model from the backbone.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| LongMemEval accuracy, JAM trained | 65.20 | VANILLA 54.80, RAG 56.20, A-MEM 56.80, Mem0 34.40, MemoryOS 36.00, LightMem 52.40, MemAgent-14B 55.20 | Table 1, all on Qwen3.5-4B unless named; n not stated | which LongMemEval split is not stated in the text read |
| LoCoMo overall F1, JAM trained | 52.09 | VANILLA 42.45, RAG 43.37, A-MEM 41.17, Mem0 32.10, MemoryOS 31.67, LightMem 32.97, MemAgent 46.13, Memory-R1-GRPO 45.02 | Table 1 | Memory-R1 rows are copied from its own paper ("not publicly released") |
| LoCoMo subscores, JAM | SH 55.14, MH 40.21, TE 62.59, OD 25.12 | RAG: SH 49.04, MH 34.39, TE 44.11, OD 17.68 | Table 1 | Memory-R1-GRPO is higher on open domain (47.42) |
| NarrativeQA F1, JAM | 45.72 | VANILLA 31.23, RAG 32.86 | Table 1 | |
| HotpotQA F1 at 56k / 112k / 224k, JAM | 64.56 / 59.28 / 58.69 | VANILLA 63.56 / 53.04 / 36.97; RAG 49.97 / 44.83 / 49.87 | Table 1 | full-context VANILLA nearly ties at 56k |
| Ablation, w/o Training | LoCoMo 48.59, LME 48.80, NAQA 34.98, HotpotQA 45.44 | Full: 52.09, 65.20, 45.72, 60.84 | Table 4 | untrained loop is 7.4 points below RAG on LME |
| Ablation, SFT only | 50.70, 60.20, 41.59, 52.08 | Full | Table 4 | |
| Ablation, GRPO w/o Hint | 51.42, 62.40, 43.62, 55.64 | Full | Table 4 | |
| Ablation, w/o Memorizer | 49.06, 64.00, 38.87, 57.72 | Full | Table 4 | summaries matter most on NarrativeQA |
| Ablation, w/o Researcher | 43.30, 58.40, 32.51, 39.10 | Full | Table 4 | |
| Ablation, w/o BM25 / w/o Embedding | 45.90, 62.40, 38.88, 52.14 / 50.86, 61.80, 39.45, 58.13 | Full | Table 4 | BM25 matters more than dense on LoCoMo |
| Workspace vs flat raw store (LoCoMo) | F1 52.09 vs 49.06; online tokens per query 6720.61 vs 8174.29; online time 13.81 s vs 17.11 s; rounds 3.16 vs 3.57 | flat raw store | Table 8 | workspace costs 36,924.51 offline tokens and 79.53 s per workspace |
| Researcher rounds | LoCoMo mean 3.16 (median 3, P90 4); LongMemEval mean 3.82 (P90 6, budget exhausted 0.40%); HotpotQA mean 7.11 (P90 14, exhausted 4.70%) | 20-round cap | Table 9 | |
| Inference seed variability (3 runs, same checkpoint) | LoCoMo 51.96 +/- 0.80; LME 64.93 +/- 0.31; NAQA 44.77 +/- 1.24; HotpotQA 59.30 +/- 1.34 | | Table 10 | training seeds not varied |
| LLM-judge accuracy (GPT-4o-mini) | LoCoMo 79.16, NAQA 68.00, HotpotQA 69.79 | RAG 58.25 / 48.00 / 53.13; MemAgent 66.62 / 38.00 / 58.59 | Table 11 | no LongMemEval column in this table |
| Transfer to LongCodeQA (233 queries) | untrained 54.08, SFT only 65.67, SFT+RL 75.54 overall | | Table 3 | no code-specific training |
| Supervision source (SFT only) | Memory-Gym: LoCoMo 50.70, LME 60.20, NAQA 41.59, HotpotQA 52.08 | MemAgent data 48.60 / 55.20 / 31.98 / 54.53; Memory-R1 data 48.90 / 57.20 / 32.42 / 49.81 | Table 2 | |

Verbatim excerpt (Table 1 header as rendered in the HTML): the LongMemEval column is a single column "LME"; the 56k, 112k and 224k columns belong to HotpotQA.

## Mechanism details you could implement
- Store raw sessions as files; never rewrite them. Add one memo per session and one README per directory. Treat both as navigation aids, not as the answer source.
- Read loop with three tools and a hard cap: `open(path)`, `search(keywords)` (BM25 top 5 plus dense top 5, merged, deduplicated), `browse(path, keywords)`. Stop on a sufficiency check or at 20 rounds. In practice the loop stops early: median 3 rounds on the chat benchmarks.
- Reward for training the search policy: source recall against a gold evidence set. This needs gold evidence labels per question.
- Keep BM25: removing it cost 6.19 F1 on LoCoMo, removing the dense retriever cost 1.23.
- The summary builder can be a small model: a 4B Memorizer matched GPT-5.5 within about half a point on LoCoMo (Table 12).

## Limitations, caveats, counter-evidence
- The paper has no limitations section. The conclusion claims "a favorable quality-cost trade-off"; no table compares JAM's online latency with the one-shot baselines in the text read, only JAM against a flat store (Table 8). Online time is 13.81 s per query on LoCoMo.
- All training-free baselines run on a 4B backbone. Extraction-based systems (Mem0, MemoryOS, LightMem) may be handicapped by a small extractor (inference). Mem0 scoring below the full-context VANILLA row suggests the comparison measures small-model extraction as much as the architecture (inference).
- The gain depends on a trained Researcher. Untrained, the loop loses to RAG on LongMemEval (48.80 vs 56.20) and only modestly beats it on LoCoMo (48.59 vs 43.37).
- One lab (BAAI, the group behind BGE-M3, which is also the dense retriever). Memory-R1 numbers are not reproduced. Training seeds are not varied.
- LoCoMo is a generation source for the training data (new corpora from the official pipeline). The paper says evaluation items are excluded; style overlap remains (inference).
- Benchmarks are chat memory and long documents. The only engineering-adjacent result is LongCodeQA transfer.

## Takeaways for tuning a memory stack
- Raw records plus a read-time search loop is a serious alternative to write-time extraction, but do not expect the loop alone to help: measure an untrained loop against one-shot hybrid retrieval before building it.
- If a navigable summary layer is added, budget for it: about 37k offline tokens per workspace bought 3 F1 points and about 18% fewer online tokens on LoCoMo.
- A sufficiency stop with a round cap keeps the loop short on chat-style questions (median 3 rounds) and long on multi-hop questions (HotpotQA P90 14). Set the cap by question type.
- Source recall against gold evidence is a usable training and evaluation signal for a read policy; our P0 fixtures would need gold evidence labels to use it.

## Open questions
- How does JAM compare on latency and tokens with one-shot RAG at equal accuracy? Not reported.
- Does the trained Researcher transfer to long structured artifacts (requirements, design sections, tickets)? Only LongCodeQA is shown.
- Would a frontier backbone without training close the gap that training closes at 4B? Not tested.
- Is the sufficiency stop better than a fixed number of rounds? Not ablated.

## Grading and labels
- **Directness: high.** Tables with ablations read in the full text.
- **Control: medium.** Component ablations and three inference seeds; baselines share the 4B backbone but are not budget-matched, and one baseline is copied from another paper.
- **Independence: low.** Single lab; the dense retriever is the same group's model; no outside replication.
- **Reproducibility: medium.** Code link given as an anonymised release, commit not recorded; training needs 8 x H100.
- **Applicability: medium.** Chat and document benchmarks; one code QA transfer result; our workload is build-time reads over long structured artifacts.
- **Strength:** paper-ablated.
- **Pillars:** R3 primary (request-time evidence selection). Secondary R2 (write-time extraction versus raw retention), R6 (benchmark comparison on LongMemEval and LoCoMo). Memory stage: retrieval. Priority 4 (LongMemEval, LoCoMo).
- **Beliefs:**
  - B7 supports: read-time, query-conditioned construction beats write-time distillation systems on LoCoMo and LongMemEval in this setup; adds a second source to JITMem, still not on long structured artifacts.
  - B9 adjacent, not graded: a sufficiency stop exists and its round distribution is reported, but it is not ablated against a fixed budget.
  - Would create: the gain of an iterative read loop comes mostly from training the retrieval policy (untrained loop 48.80 vs RAG 56.20 on LongMemEval).
- **Contradiction rows:** none.

## Origin chain
- Post https://x.com/GKwVDZgsWe5dQfF/status/2105115504226746670 (states 65.2% vs 56.2% on LongMemEval, both Qwen3.5-4B) -> arXiv 2609.34385 v1 -> Table 1 (LME column), Table 4 (ablations), Table 8 (workspace cost) -> this note.
- Independence: authors at BAAI share an organisation with the BGE-M3 retriever used in the system. Datasets shared with earlier notes: LoCoMo and LongMemEval (also used by JITMem, note paper-just-in-time-memory-jitmem-2609-27334.md). No shared authors with JITMem found (inference from the author lists).
