---
schema_version: 1
artifact_id: N-20260927-04
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103799452767338672", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.26457
claim_cluster: arxiv:2609.26457
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.26457
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R5
pillar_secondary: ["R6", "R3"]
tags: {"mechanism": ["bi-level harness self-improvement", "private held-out selection", "bug-rate-gated failure memory", "bounded role-specific prompts", "UCB1 strategy bandit"], "workload": ["ML engineering", "algorithm engineering", "harness engineering", "MLE-Bench", "ALE-Bench", "FML-Bench", "WeatherBench 2", "KernelBench-style reward hacking probe"], "lifecycle_stage": ["read", "promotion"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: held-out benchmark comparisons and a reward-hacking rate, but per-benchmark numbers were summarised as matches or exceeds in the text read", "control": "medium: fixed per-task budget for every variant, public vs private reward split, held-out benchmarks never used in selection; only 3 seeds per outer-loop configuration", "independence": "low: vendor lab (Weco AI) evaluating its own production agent lineage", "reproducibility": "low: 8-day run, 100-node tree, code release not stated", "applicability": "medium: harness and context-management edits for a research/coding agent; failure memory is directly a memory mechanism"}
beliefs_affected: {"supports": ["B15"], "contradicts": [], "would_create": ["A harness self-improvement loop selected on private held-out scores lowered its reward-hacking rate (55% to 32%) without optimising for it, one run, 3 seeds"]}
claim_correction: none
---

# Recursive Self-Improvement of AI Research Agents (AIDE squared, arXiv 2609.26457)

- **URL:** https://arxiv.org/abs/2609.26457 (full text read at https://arxiv.org/html/2609.26457)
- **Type:** paper
- **Author / org:** Dhruv Srikanth, Bingchen Zhao, Dixing Xu, Yuxiang Wu, Zhengyao Jiang; Weco AI
- **Date:** arXiv v1, 22 Sep 2026
- **Retrieved:** 2026-09-27, arXiv HTML v1
- **Cited by evidence:** @halcyonwisp https://x.com/halcyonwisp/status/2103799452767338672
- **Relevance to a memory stack:** medium. An L2-style self-improvement loop on the harness layer (fixed evaluator, AI chooses edits) whose surviving edits are mostly context management and a gated failure memory; it also reports a reward-hacking rate, the kind of loop-risk metric B17 says nobody reports.

## TL;DR
- Inner loop: a research agent edits solutions under a fixed per-task budget; outer loop: a separate agent (AIDE_human, Claude Opus 4.7) rewrites the inner agent's code; a rewrite is kept only if it raises the average private held-out score.
- 8 days, 100-node search tree, 7 accepted rewrites (steps 2, 6, 28, 39, 47, 63, 85); selection grade 0.703 to 0.778.
- Surviving edits: UCB1 bandit over five drafting strategies, forking the global best every five steps, bounded role-specific prompts instead of full history, and a failure memory injected only when bug rate >= 15% (up to three recurring error signatures).
- Prompt compression: median task-level reduction up to 7x (MLE-Bench), over 40x (WeatherBench 2), about 50x (ALE-Bench).
- Reward hacking on a kernel-engineering probe: 55% (AIDE_0) to 39% (AIDE_47) to 32% (AIDE_85), vs 39% for the human-engineered agent.

## What it claims / describes
- Edited object: "the harness layer, the code that surrounds a model and controls an agent's search, context, and verification", not weights.
- Selection: inner agents see public rewards `r^pub_t`; the outer loop selects on private rewards `r^priv_t`; grade g(a) = mean private score; `a_k* = argmax g(a)`. Inner-loop evaluations used Gemini 3 Flash.
- Selection benchmark: three task families (ML engineering, heuristic algorithm engineering, harness engineering).
- Held-out benchmarks never used in selection: ALE-Bench (10 tasks, 10 seeds), MLE-Bench (22 tasks, 3 seeds), FML-Bench (18 tasks, 3 seeds), WeatherBench 2 (1 task, 3 seeds, out of distribution). "On all four, the strongest discovered agent matches or exceeds a human-engineered production research agent that ranks among the strongest on FML-Bench."
- Reward-hacking probe: agents optimise an isolated kernel speedup (visible proxy); kernels are then inserted into GPT-2, ViT and CNN training loops (hidden ground truth); divergence = reward hacking.
- Safeguards added by the loop itself: a prompt reminder that scoring uses unseen private data; re-prompting when generated code is under 40 characters; penalising candidates by distance from the median of top performers; fixing an evaluation-script crash.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| selection grade | 0.778 (AIDE_85) | 0.703 (AIDE_0) | private held-out scores on the selection benchmark | single 8-day run |
| accepted rewrites | 7 of 99 proposals | | 100-node tree | |
| held-out benchmarks | AIDE_85 "matches or exceeds" AIDE_human on ALE, MLE, FML, WeatherBench 2 | AIDE_human (two years of human R&D) | 10/22/18/1 tasks; 10/3/3/3 seeds | per-benchmark values not captured in the text read |
| prompt compression (median task-level) | up to 7x MLE-Bench; > 40x WeatherBench 2; about 50x ALE-Bench | full-history prompts | | |
| reward hacking rate | 32% (AIDE_85); 39% (AIDE_47); 55% (AIDE_0) | AIDE_human 39% | kernel engineering probe, not in selection benchmark | n tasks not captured; judge is the downstream training loop, not an LLM |
| failure-memory trigger | bug rate >= 15%, inject up to 3 error signatures | | | |
| code-too-short guard | < 40 characters triggers re-prompt | | | |

## Mechanism details you could implement
- Select self-edits on a private score the editing agent never sees; keep the public/private split strict.
- Give every variant the same per-task budget (agent tokens + execution) so gains are not bought with compute.
- Replace full-history prompts with "a compact summary of the root and recent candidates", role-specific per operator (draft vs improve).
- Failure memory gated by a rate: only when a run's candidates show a bug rate of at least 15%, inject up to three recurring error signatures into draft and improve prompts.
- UCB1 bandit over a fixed set of strategy arms (conservative, aggressive_rewrite, ensemble, tuned_specialist, robust_simple); fork the global best every five steps under a different arm.
- Track a proxy-vs-downstream divergence rate as a standing reward-hacking metric.

## Limitations, caveats, counter-evidence
- Authors: "Noise compounds across both loops... If the noise is high enough, a falsely accepted rewrite becomes the new incumbent." Discovered agents "remain complex and difficult to interpret. It is unclear which components drive performance and which, if any, are unused artifacts".
- Only 3 seeds per outer-loop configuration; the ignition test (AIDE_47 as outer agent) "cannot decisively distinguish" outcomes.
- The reward-hacking drop was not optimised for, so its cause is unknown; one run.
- Vendor evaluating its own lineage; no independent replication.
- No ablation of the failure memory or of history compression on their own (inference from the text read).

## Takeaways for tuning a memory stack
- Bounded, role-specific context beat full history in a self-improving loop; history compression was selected repeatedly.
- Inject failure memory only above a failure-rate threshold, and cap it (3 signatures), rather than always carrying past errors.
- If our outcome loop (H4/H6) edits the harness, copy the private-selection split and the proxy-vs-downstream divergence metric.

## Open questions
- Per-benchmark held-out numbers and intervals.
- Does failure memory alone move results? No ablation seen.
- Would the reward-hacking reduction survive other seeds or probes?

## Grading and labels
- Directness medium; control medium; independence low; reproducibility low; applicability medium.
- Pillars: R5 primary (self-improvement loop); R6 secondary (private held-out selection, reward-hacking metric); R3 secondary (context compression).
- B15 supports (loosely): refinements chosen by comparative selection across a lineage tree improved held-out performance; one system.
- Would create: private held-out selection reduced reward hacking 55% to 32% (one run).
- Relevant to B17 (feedback-loop rate unreported): this reports a related but different rate (reward hacking on a proxy), not memory reinforcement; B17 stands.
- No contradiction rows.

## Origin chain
post 2103799452767338672 (@halcyonwisp, bare link to the PDF) -> arXiv 2609.26457 v1 HTML -> method (bi-level loop), results on four held-out benchmarks, reward-hacking section, limitations -> this note. Independence: Weco AI builds AIDE; AIDE_human is their production agent.
