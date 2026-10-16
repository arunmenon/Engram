---
schema_version: 1
artifact_id: N-20260927-19
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2103857662114865493", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.20519
claim_cluster: arxiv:2609.20519
feeds: ["decision", "memory"]
primary_source: https://arxiv.org/abs/2609.20519
source_commit: n/a
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R3", "R6", "R1"]
tags: {"mechanism": ["auto-research-loop", "held-out-validation", "online-context-compaction-cost-gate", "observation-handle-with-excerpt", "evidence-preserving-log-reducer", "action-fusion"], "workload": ["coding-agent", "EdgeBench", "Terminal-Bench"], "lifecycle_stage": ["harness-improvement", "context-assembly"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: tables for token traffic, cost and score per harness and per single mechanism on two backends", "control": "high: single-mechanism ablations, a frozen harness and acceptance rule, EdgeBench isolated from search", "independence": "medium: NVIDIA/academic authors; Pi baseline is their comparison point; no outside replication", "reproducibility": "medium: code at NVlabs/SoL-Pi per the paper, commit not read; seeds and variance not reported in the fetched text", "applicability": "high: observation handling, compaction and log reduction are exactly the context-assembly and receipt problems of an engineering agent"}
beliefs_affected: {"supports": ["B15", "B5"], "contradicts": [], "would_create": ["Harness-level efficiency mechanisms found by an auto-research loop on one backend transfer to another with smaller effect; combining individually good mechanisms can lower task score (EdgeBench 44.8 to 42.0) while halving tokens"]}
claim_correction: The brief (Flextor97) says "about 45 to 49% less token traffic vs Pi on EdgeBench at near the same score"; the efficiency configuration keeps 93.7% (GPT-5.6 Sol) and 94.3% (Opus 5) of Pi's score, a 2.8 and 2.5 point drop, and on Terminal-Bench 4 it solved 15 tasks vs Pi's 18.
---

# SoL-Pi: Recursively Scaling Auto-Research Loops for Efficient Agent Harness (arXiv 2609.20519)

- **URL:** https://arxiv.org/abs/2609.20519 (HTML: https://arxiv.org/html/2609.20519; code per paper: https://github.com/NVlabs/SoL-Pi ; page https://nvlabs.github.io/SoL-Pi/)
- **Type:** paper
- **Author / org:** Haozhe Liu, Tian Ye, Sensen Gao, Qihang Cao, Yitong Li, Mingchen Zhuge, Duomin Wang, Ruihua Zhang, Ping Luo, Jiawang Bian, Lei Zhu, Ligeng Zhu, Enze Xie, Song Han (NVLabs code release)
- **Date:** submitted 2026-09-17
- **Retrieved:** 2026-09-27 (abstract and HTML full text). Repository not cloned this run; commit not recorded.
- **Cited by evidence:** @Flextor97 DAILY AI BRIEF 2026-09-26 https://x.com/Flextor97/status/2103857662114865493 (backlog cluster url:alignment.openai.com/...; SoL-Pi split out as its own claim). Also resolves the source for the parked cluster x:2103798983227560292 (posts 2103798983227560292, 2103849256113115303: "SoL-Pi paper not linked", 2026-09-27 run).
- **Relevance to a memory stack:** high. A controlled, ablated harness self-improvement result where the surviving mechanisms are about what enters context: stable handles with excerpts for large observations, a cost-gated compaction, and a cheaper-model log reducer that produces a "compact receipt" with deterministic verification and fallback.

## TL;DR
- Loop: ~152 proposed directions in six families (context, progress, tools, delegation, prompt/policy, improvement/evaluation), ~500 executable environments, >3,000 runs, >60,000 agent-environment interactions. Accept rule: "Every capability metric must remain within its predeclared tolerance, and the candidate must improve at least one declared efficiency metric"; keep nondominated results.
- Held-out: "We reserve EdgeBench for final validation, keeping it isolated from the search process. The harness and acceptance rule are frozen before evaluation. Held-out results never feed back into the Auto-Research Loops."
- Four mechanisms survive: Action Fusion, Online Context Compact, ObservationPack, Evidence-Preserving Reducer.
- EdgeBench (51 tasks), GPT-5.6 Sol: Pi 2.1538B tokens, $1,339, score 44.833; SoL-Pi [Efficiency] 1.0990B, $894, 42.003 (49.0% fewer tokens, 33.2% cheaper, 93.7% of score). Opus 5 transfer: 44.7% fewer tokens, 33.5% cheaper, 94.3% of score.
- Single mechanisms can raise score: ObservationPack alone on GPT-5.6 Sol 47.208 (vs 44.833) at 2.0224B tokens; Action Fusion alone on Opus 5 50.482 (vs 44.756). Combining all four lowers score below baseline.

## What it claims / describes
**Mechanisms (verbatim where quoted):**
1. Action Fusion: "Combines a mutation and its follow-up command into one request, reducing API calls from three to two."
2. Online Context Compact: evaluated "at subtask completion" and applied "only when projected savings exceed the rewrite cost". The harness "estimates remaining model requests from the observed requests between completed steps and the number of unfinished steps. It caps this estimate by the requests that would fill the current context window at the observed growth rate. The cost gate compares projected input savings with the estimated extra cost of rewriting the prompt cache." Later compactions "account for unrecovered rewrite costs and require a larger savings margin." "It does not separately price the summarization call."
3. ObservationPack: "Sends large results in full for the first two provider requests, then replaces them with a stable handle and a 1 KB excerpt. Exact original chunks remain available on demand." Threshold 10 KiB.
4. Evidence-Preserving Reducer: "Compresses build and test logs of at least 4 KiB from a predefined set of commands", using "a lower-cost model to extract key evidence into a compact receipt" with "deterministic verification and fallback to the original on failure."

## Numbers

EdgeBench, 51 tasks, GPT-5.6 Sol:

| harness | tokens (B) | cost ($) | avg score | $/score |
|---|---|---|---|---|
| Pi | 2.1538 | 1,339 | 44.833 | 0.5855 |
| + Action Fusion | 1.8968 | 1,235 | 46.664 | 0.5190 |
| + Online Context Compact | 1.2881 | 935 | 41.993 | 0.4365 |
| + Evidence-Preserving Reducer | 1.9375 | 1,200 | 44.630 | 0.5274 |
| + ObservationPack (= SoL-Pi [Performance]) | 2.0224 | 1,271 | 47.208 | 0.5280 |
| SoL-Pi [Efficiency], all four | 1.0990 | 894 | 42.003 | 0.4174 |

Opus 5, no retraining of the harness:

| harness | tokens (B) | cost ($) | avg score |
|---|---|---|---|
| Pi | 2.3697 | 1,741 | 44.756 |
| + Action Fusion | 2.1016 | 1,605 | 50.482 |
| + Online Context Compact | 1.9152 | 1,537 | 49.155 |
| + Evidence-Preserving Reducer | 1.9131 | 1,456 | 43.405 |
| + ObservationPack | 1.4418 | 1,176 | 47.047 |
| SoL-Pi [Efficiency] | 1.3101 | 1,158 | 42.224 |

Terminal-Bench 4 (63 CPU-only tasks): Codex 18 solved, $272.35; Pi 18, $286.45; SoL-Pi 15, $211.12 (26.3% cheaper than Pi, 3 fewer solved). IMO 2026 (6 problems, GPT-5.6 Sol xhigh): Codex 5 passed $114.47; Pi 3, $75.95; SoL-Pi 3, $62.69.

Compaction cost accounting (GPT-5.6 Sol): cache-read traffic 2.1326B to 1.0605B tokens; cache-write 0.0141B to 0.0316B; total cost $1,339 to $894. Seeds, runs and variance: not reported in the fetched text. Judge: benchmark scoring (not described in fetched text).

## Mechanism details you could implement
- Observation handle: for tool outputs over 10 KiB, send in full for two turns, then replace with `{handle, 1 KB excerpt}`; keep the exact bytes retrievable by handle. This is a served-evidence receipt pattern (R1): the agent's context holds a pointer to an immutable artifact.
- Log reducer with receipts: a cheap model extracts key evidence from build/test logs >= 4 KiB into a compact receipt; verify deterministically (for example, that quoted lines exist in the original, inference about the check) and fall back to the raw log on failure.
- Compaction as a cost decision: compact only at subtask boundaries and only if projected input savings exceed prompt-cache rewrite cost; raise the margin after each compaction.
- Acceptance rule for harness changes: all capability metrics within predeclared tolerance and at least one efficiency metric improved; validation set isolated from search.

## Limitations, caveats, counter-evidence
- Verbatim: "Our current harness was updated from trajectories generated by a single LLM; on the other evaluated backend, its mechanisms trigger less often and less intensively." "Recursive efficient improvement ... is a long-term research vision rather than a compounding effect demonstrated by the present study." "Running complete auto-research loops in our environment is computationally expensive, making controlled comparisons of search breadth and depth under a fixed budget particularly challenging."
- Combining mechanisms is not additive for score: the efficiency configuration scores below every single-mechanism arm on both backends.
- Online Context Compact lowered score on GPT-5.6 Sol (41.993) but raised it on Opus 5 (49.155): backend-dependent.
- The 148 rejected directions are not itemised in the fetched text.
- No seeds or intervals in the fetched text; EdgeBench is 51 tasks.

## Takeaways for tuning a memory stack
- Treat large observations as stored artifacts with handles plus short excerpts; the paper's best single-mechanism score gain on GPT-5.6 Sol came from this.
- Gate compaction on cost, at subtask boundaries; a summary is a cache, not the read surface.
- A reducer that writes a verified receipt with fallback to the original is a concrete design for "summaries that can be replayed".
- Validate each mechanism alone and combined; the combination can cost score.

## Open questions
- Variance across seeds on EdgeBench?
- Does ObservationPack's on-demand retrieval of exact chunks get used, and how often?
- What exactly does the reducer's deterministic verification check?

## Grading and labels
- Directness: high. Control: high. Independence: medium. Reproducibility: medium. Applicability: high.
- Strength: paper-ablated. Pillar R5 (harness self-improvement loop with held-out validation); secondary R3 (context assembly under budget), R6 (frozen acceptance rule, isolation), R1 (handles and receipts for served observations).
- Beliefs: supports B15 (a broad search with comparative selection produced retained mechanisms; an L2-style fixed evaluator); supports B5 weakly (scheduled summarising consolidation is not free: online compaction lowered score on one backend). Would create: harness mechanisms transfer across backends with smaller effect, and combining them can lower score.
- Contradiction rows: none.

## Origin chain
@Flextor97 brief 2103857662114865493 -> arXiv 2609.20519 abstract -> HTML full text: loop design, Tables for EdgeBench, Opus 5 transfer, ablations, Terminal-Bench 4, IMO 2026, limitations -> this note. Independence: related to RRSI (`rrsi-regularized-recursive-self-improvement.md`) in goal (frozen model, evolving harness), different authors and benchmarks.
