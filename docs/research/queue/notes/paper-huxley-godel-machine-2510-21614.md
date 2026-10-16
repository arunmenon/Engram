---
schema_version: 1
artifact_id: N-SURVEY-20260927-12
artifact_type: note
producer: triage
run_id: survey-20260927T054501Z-e1b9
created_at: 2026-09-27T05:53:00Z
idempotency_key: note:survey:arxiv:2510.21614
input_refs: []
pillar_primary: R5
pillar_secondary: []
beliefs_affected: {supports: [B15], contradicts: []}
evidence: {directness: 2, control: 2, independence: 2, reproducibility: 4, applicability: 4}
source_url: https://arxiv.org/abs/2510.21614
found_via: survey
strength: paper-single-benchmark
---

# Huxley-Goedel Machine: Human-Level Coding Agent Development by an Approximation of the Optimal Self-Improving Machine

- **URL:** https://arxiv.org/abs/2510.21614 (read via https://arxiv.org/html/2510.21614 and the PDF, v3)
- **Type:** paper
- **Author / org:** Wenyi Wang, Piotr Piekos, Li Nanbo, Firas Laakom, Yimeng Chen, Mateusz Ostaszewski, Mingchen Zhuge, Juergen Schmidhuber (KAUST)
- **Date:** v3, 2025-10-29 (first posted October 2025)
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, pillar R5, beliefs B15
- **Relevance to a memory stack:** medium, it shows that pooling outcome statistics over a lineage (an agent plus all its descendants) ranks "which version to refine next" better than the version's own score, which maps onto choosing which Workflow version to refine; it does not test what content goes into a refinement.

## TL;DR
- Defines Clade-Metaproductivity (CMP): the expected best utility reachable within an agent's subtree of descendants, and estimates it by pooling pass/fail counts over the whole clade: CMP_hat(a) = n_success^C(a) / (n_success^C(a) + n_failure^C(a)).
- Metaproductivity-Performance Mismatch: Pearson correlation between each method's selection criterion and empirical CMP is 0.444 (SICA) and 0.285 (DGM) weighted on SWE-Verified-60, vs 0.778 for HGM's clade estimator; on Polyglot 0.274 / 0.383 vs 0.626 (weighted).
- Under a matched 800-evaluation budget, same initial agent and same LLMs: best-belief agent accuracy SWE-Verified-60 56.7% (HGM) vs 53.3% (DGM) vs 50.0% (SICA); Polyglot 30.5% vs 27.1% vs 25.4%; CPU-hours 517 vs 1231 (SICA "infinite loop") and 347 vs 2385 vs 572.
- Full SWE-bench Verified run (8000 evaluations): 61.4%; transferred to SWE-bench Lite 40.1% filtered / 49.0% standard (GPT-5-mini), 47.8% / 57% with GPT-5.
- Single run per method, no seeds or CIs, and no ablation that isolates the CMP estimator from HGM's other changes (decoupled expand/evaluate, per-task evaluation, asynchronous execution).

## What it claims / describes
Self-improving coding agent search is framed as a tree: each node is an agent (its own code repo); "expansion" makes a child by having an LLM self-modify a parent; "evaluation" runs an agent on a benchmark task. Prior systems (SICA, DGM) always expand then immediately evaluate the child on several tasks, and pick parents by their own benchmark score (SICA greedy on best performance; DGM probabilistic on score and number of children). The paper claims own-score is a weak proxy for the capacity to produce good descendants ("Metaproductivity-Performance Mismatch").

HGM's three subpolicies:
- Expansion: Thompson sampling over agents with Beta(tau(1 + n_success^C(a)), tau(1 + n_failure^C(a))) where counts are summed over the clade C(a). tau is an exploration-exploitation scheduler increasing with time (they use B/b with b the remaining budget).
- Evaluation: Thompson sampling with the agent's own counts, Beta(tau(1 + n_success(a)), tau(1 + n_failure(a))); each evaluation is a single agent-task pair; counts are propagated to the agent and all ancestors.
- Selection (expand vs evaluate): from infinite-armed bandits (UCB-Air): expand at time t if N_t^alpha >= |T_t| (alpha = 0.6).
- Final agent: "best-belief agent", argmax over the tree of I_epsilon(1 + n_success(a), 1 + n_failure(a)), the regularized incomplete beta function, epsilon = 1.
- Asynchronous implementation: expansions and evaluations run concurrently on all CPUs. Initial agent is expanded 5 times per process at start to avoid bias. Authors note an async bias: agents with few evaluations have inflated means because easy tasks finish first ("After having more than 50 evaluations, this bias is barely observed").
- Theorem 1: under their Assumption 1 (utility depends only on final agent, repeatable trials, proofs free, each self-modification costs one budget unit), access to a true CMP oracle is sufficient to implement the Goedel Machine.

Models: SWE-bench experiments use GPT-5 for expansion (self-modification) and GPT-5-mini for evaluation; Polyglot uses Qwen3-Coder-480B-A35B-Instruct (int4/int8 AutoRound quantized) for expansion and Qwen3-Coder-30B-A3B-Instruct for evaluation. Initial agent from DGM's official implementation: a single loop of LLM queries with file-edit and bash tools, one-hour limit per agent execution. For the full-Verified run the initial agent was modified (file-edit tool removed, bash only, five-hour limit) and starts at 53.2%.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Pearson corr, selection criterion vs empirical CMP, weighted | HGM 0.778; SICA 0.444; DGM 0.285 | SICA, DGM use agent's own benchmark score as CMP estimator | SWE-Verified-60 (60 tasks) | each method's correlation is computed on its own search tree after its own run, so the trees differ; single run; number of nodes not stated in main text |
| Same, unweighted | HGM 0.512; SICA 0.444; DGM 0.406 | same | SWE-Verified-60 | unweighted gap is much smaller (0.512 vs 0.444) |
| Same, weighted | HGM 0.626; SICA 0.274; DGM 0.383 | same | Polyglot | |
| Same, unweighted | HGM 0.873; SICA 0.274; DGM 0.357 | same | Polyglot | text says "0.8783" while the table says 0.873 (text/table disagreement) |
| Best-belief agent accuracy | HGM 56.7% (+16.7); DGM 53.3% (+13.3); SICA 50.0% (+10) | initial ancestor 40% | SWE-Verified-60, 800 evaluations max, same ancestor, GPT-5 / GPT-5-mini | 56.7 vs 53.3 is 2 of 60 tasks; single run; selected and scored on the same 60 tasks |
| CPU-hours for 800 evaluations | HGM 517; DGM 1231; SICA "infinite loop" | | SWE-Verified-60 | SICA hit "query length out-of-LLM-context-window" after 360 evaluations; 2.38x faster than DGM; speed comes largely from async parallelism, not CMP |
| Best-belief agent accuracy | HGM 30.5% (+10.2); DGM 27.1% (+6.8); SICA 25.4% (+5.1) | initial ancestor 20.3% | Polyglot, 800 evaluations, Qwen3-Coder | Polyglot task count not stated in main text; (inference) values are consistent with n = 59 (18/59, 16/59, 15/59, 12/59), i.e. HGM beats DGM by about 2 tasks |
| CPU-hours | HGM 347; DGM 2385; SICA 572 | | Polyglot | "6.86 times faster than DGM and 1.65 times faster than SICA" |
| Full SWE-bench Verified | 61.4% | initial agent 53.2% | 500 tasks, 8000 evaluations, GPT-5-mini agent | optimized and reported on the same 500 tasks; authors call it top GPT-5-mini system and top-10 overall |
| SWE-bench Lite filtered / standard | HGM agent 40.1 / 49.0; initial ancestor 34.8 / 44.0; SWE-agent + GPT-5-mini 39.6 / 47.6 | | 300 Lite tasks; filtered removes 93 overlapping with Verified (207 left) | SWE-agent+GPT-5-mini is the authors' local rerun; HGM vs SWE-agent is 40.1 vs 39.6 on filtered (about 1 task of 207) |
| Transfer to GPT-5 | HGM agent + GPT-5: 47.8 filtered / 57 standard; SWE-agent (best on leaderboard): 48.3 / 56.7 | | SWE-bench Lite | basis of "human-level" claim; essentially a tie |
| Total spend | "approximately $5000 USD to produce the experimental results, including all three methods" | | appendix C.2 | |
| Seeds / runs | not stated; single run per method implied | | | no error bars anywhere |
| Ablations | none in main text or appendices A to F that I read | | | no HGM-with-own-score arm; no sync vs async HGM arm |
| Latency | not stated beyond CPU-hours | | | |
| LLM judge | none; grading is benchmark test execution | | | |

## Mechanism details you could implement
- Clade-pooled success rate: for each version node, keep n_success and n_failure for the node and aggregated counts over its subtree. Propagate every outcome to all ancestors. Parent-to-refine score = pooled clade rate.
- Choose which node to refine by Thompson sampling from Beta(tau(1 + clade successes), tau(1 + clade failures)), with tau rising as budget depletes (explore early, exploit late).
- Decouple "create a new version" from "gather more evidence on an existing version": expand only when N_t^0.6 >= number of existing versions; otherwise spend one evaluation on one version-task pair, chosen by Thompson sampling on the node's own counts.
- Pick the final/served version by a lower-percentile posterior (incomplete beta), not by the raw mean, which protects against versions with few lucky evaluations.
- Appendix D leakage guard for measuring the estimator: when scoring a node's CMP estimate against its descendants' best, exclude the node itself and the child subtree containing the empirical maximum.

## Limitations, caveats, counter-evidence
- Not a controlled test of the lineage signal alone: HGM differs from DGM/SICA simultaneously in parent-selection signal (clade vs own score), evaluation granularity (single task, early stopping), expand/evaluate scheduling (UCB-Air), async execution, and final-agent selection rule. There is no ablation of HGM using own-score expansion, so the accuracy gains cannot be attributed to CMP. (inference)
- The MPM correlations are computed on three different trees (each method's own run), not by scoring the same set of agents with different estimators. HGM's tree is shaped by HGM's own policy, and HGM's estimator also uses more evaluations per clade, which mechanically reduces noise. (inference) A like-for-like test would score all three estimators on one shared tree.
- Also, CMP_hat pools descendants' outcomes while empirical CMP is the max over descendants; even with the Appendix D exclusions, some structural correlation between the two is expected. (inference)
- Effect sizes are small in task counts: +2 tasks on SWE-Verified-60 over DGM, about +2 on Polyglot, single run, no variance estimate. The SWE-Verified-60 and full Verified numbers are selected and reported on the same tasks; only the SWE-Lite filtered set (207 tasks) is held out.
- SICA baseline on SWE-Verified-60 failed (context overflow after 360 evaluations), so that comparison is partly a harness bug.
- Baselines were rerun by the authors with cheaper models (not DGM's original setup), which they state is for fairness, but it means published DGM numbers do not apply.
- B15 as stated is about "comparative evidence across lineages produces better refinements." HGM uses lineage evidence only to choose which parent to modify; the self-modification prompt itself is not given comparative cross-lineage evidence (as far as the main text and appendix describe). So it supports a narrower form: lineage-aggregated signals are better parent selectors than single-agent scores. (inference)
- No instructions aimed at the reader agent were found in the page or PDF.

## Takeaways for tuning a memory stack
- When Engram maintains versioned Workflows (induced, refined, re-induced), rank which version to refine next by the pooled success of the version plus all its descendant versions, not by its own last reuse score alone; use Thompson sampling rather than argmax.
- Separate "refine the Workflow" from "collect more reuse evidence on an existing Workflow," and gate new refinements on evidence volume (N^alpha >= number of versions).
- Serve the version with the best lower-percentile posterior, not the best mean, to avoid promoting versions with a few lucky runs.
- Treat HGM as design inspiration, not as proof that lineage signals work; the controlled ablation is missing and must be run by Engram if it matters.

## Open questions
- Does HGM with own-score expansion (everything else equal) lose the accuracy gain? Not reported.
- How many nodes were in each tree, and what are the confidence intervals of the correlations?
- Does the correlation advantage hold when all estimators are scored on the same tree?
- Do lineage signals help if fed into the refinement prompt (comparative content), not only into parent choice?

## Grading
- directness 2: measures lineage-pooled vs own-score as a parent-selection predictor, which is a narrower form of B15; it does not test comparative evidence as refinement input.
- control 2: matched ancestor, LLMs and 800-evaluation budget across methods, but single runs, no seeds, correlations on different trees, and no ablation isolating CMP from async and scheduling changes.
- independence 2: authors evaluate their own method and rerun baselines themselves (SICA partly failed); no LLM judge, grading is test execution.
- reproducibility 4: code at https://github.com/metauto-ai/HGM, models, hyperparameters (alpha 0.6, epsilon 1, tau = B/b) and cost ($5000) stated; quantized Qwen variant and GPT-5 API drift limit exact reruns.
- applicability 4: coding-agent self-improvement on SWE-bench Verified, Lite and Polyglot, directly the build-time coding setting, although it evolves agent code rather than memory.
