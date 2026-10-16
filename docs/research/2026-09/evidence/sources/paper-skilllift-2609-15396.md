---
schema_version: 1
artifact_id: N-20260929-17
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104172198537855432", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.15396
claim_cluster: arxiv:2609.15396
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.15396
source_commit: 599358b4d4c4a27c0e004df8228ab93026600653
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R4", "R6"]
memory_stage: evaluation
tags: {"mechanism": ["skill-evolution", "surrogate-rubric", "rank-alignment", "kendall-tau", "bilevel-optimization", "non-decreasing-acceptance"], "workload": ["agent-skills", "coding-agent", "SkillsBench", "WildClawBench"], "lifecycle_stage": ["procedure-induction", "revision"], "cross_cutting": ["cost-accounting", "judge-shares-backbone", "no-held-out-split"]}
evidence_grade: {"directness": "medium: skills are procedural memory and the paper measures pass rate of evolved skills, but each skill is evolved and scored on the same task (test-time optimization), not transfer", "control": "medium: same seed skills and same backbone across arms, 3 rollout seeds, ablations in Table 3 and Table 8; no intervals, baselines run at reduced scale vs their published defaults (Appendix B)", "independence": "low: authors ran all baselines themselves; verifier, generator and rubricator use the same backbone LLM as the agent under test; oracle is the benchmark verifier", "reproducibility": "medium: code public (commit pinned), prompts in Appendix A, hyperparameters Table 5; repo domain config values differ from Table 5", "applicability": "medium: SkillsBench includes 16 SE tasks with deterministic verifiers; results are per-task skill tuning, not a shared skill library across tasks"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A surrogate rubric that is re-aligned to a sparse oracle by rank correlation (Kendall tau >= 0.9) can cut the oracle-plus-framework token cost of skill or procedure revision search by about 2.1x to 2.7x at equal target pass rate; without re-alignment the dense rubric adds only about 1 pp over static skills"]}
claim_correction: Post says "40-70% cheaper skill evolution"; the paper measures cumulative tokens to first reach the 0.9 quantile of pass rate on SkillsBench only (Figure 4, Table 7: baselines cost 2.13x to 2.74x SkillLift, i.e. about 53-64% lower, inference), against baselines that were given 2x SkillLift's budget; no cost comparison is reported for WildClawBench.
---

# SkillLift: Learning Dense Rubrics from Sparse Oracles for Efficient Skill Evolution

- **URL:** https://arxiv.org/abs/2609.15396
- **Type:** paper
- **Author / org:** Haoxiang Kang (Independent Researcher), Ming Wen (Fudan University, corresponding)
- **Date:** v1 submitted 14 Sep 2026 (arXiv stamp on PDF, cs.AI)
- **Retrieved:** 2026-09-29 (version v1; full PDF read locally at repos/2609.15396.pdf, 16 pages; code shallow clone at repos/SkillLift, commit 599358b4d4c4a27c0e004df8228ab93026600653, 2026-09-08, not executed). Earlier runs could not read arXiv HTML; this run read the PDF directly.
- **Cited by evidence:** https://x.com/rajeevchhajer/status/2104172198537855432 (@rajeevchhajer roundup, "40-70% cheaper skill evolution")
- **Relevance to a memory stack:** medium. A concrete recipe for evaluating proposed revisions to procedural memory (skills) with a cheap LLM rubric, and for keeping that rubric honest by periodically re-aligning its ranking to a costly ground-truth oracle. Directly relevant to how we would score candidate memory or procedure edits without paying a full agent rollout per edit.

## TL;DR
- Skill evolution is framed as bilevel optimization: an inner loop (Mode A) revises K skills against a frozen LLM-judged rubric of 5 to 15 signed binary criteria at zero oracle cost; an outer loop (Mode B) runs real oracle rollouts on the K skills plus the champion and revises the rubric until its ranking matches the oracle (Kendall tau >= theta_B = 0.9).
- On SkillsBench (87 tasks) and WildClawBench (60 tasks) with three backbones, SkillLift has the best overall score in all six model-benchmark combinations (Table 2), e.g. SkillsBench GPT-5.4-mini 62.5% vs SkillOpt 58.2% vs CoEvoSkills 52.5% vs human-written 41.4%.
- Ablation (Table 3): removing the rubricator (no oracle re-alignment) collapses SkillsBench overall to 42.5 / 59.8 / 65.5 vs full 62.5 / 75.1 / 74.3; replacing ranking alignment with score regression loses 2.7 to 5.3 pp.
- Claim correction: "40-70% cheaper" is token cost to first reach the 0.9 quantile of pass rate on SkillsBench, against baselines that were given 2x SkillLift's budget. Table 7 ratios (2.13x to 2.74x) imply roughly 53-64% lower (inference). No WildClawBench cost comparison.
- Key caveat: scores are "mean per-task best evolved-skill scores over 3 rollout seeds"; the skill is evolved on the same task it is scored on, with the champion picked by the oracle. This is per-task test-time optimization, not generalization to unseen tasks.

## What it claims / describes

**Problem.** Each oracle evaluation of a skill needs a full agent rollout, so text-space skill search sees few signals and falls back to patching observed failures. Pilot (Figure 1): 10 WildClawBench tasks, 10 rounds, 3 seeds; oracle tokens dominate and grow, best-worst gap stays large.

**Formulation** (Section 3, Eq. 1): minimize over rubric R the expected rank discrepancy D(sigma^R_t, sigma^O_t) between rubric-induced and oracle-induced rankings of candidate skills on task t, subject to S*(R) = argmax_S E_t[R(S)]. D is instantiated as 1 - tau (Kendall).

**Rubric** (Eq. 2): M binary criteria (c_i, p_i), p_i a nonzero signed integer (merit > 0, flaw < 0). A verifier LLM judges hits h_i in {0,1}. Score R(S_k) = (sum_i p_i h_i - S_min) / (S_max - S_min), S_max = sum of positive p, S_min = sum of negative p, so R in [0,1]. The hit vector is returned with the score so the generator can target missed criteria.

**Inner loop (Mode A, no oracle)** (Algorithm 1): score champion S* with R; the generator proposes K diverse revision directions d_k ("strategy optimization, tool-use policy, error handling") and derives K branches; each branch is refined and a revision is accepted only if its rubric score does not decrease. Stop when min_k R(S_k) >= theta_A or inner budget A_max is spent.

**Outer loop (Mode B, oracle)**: run the oracle on the K refined branches (the champion's oracle score is cached, so only K new rollouts), rank K+1 skills by oracle and by rubric, compute tau (Eq. 3). While tau < theta_B and revisions < B_max, a rubricator LLM revises R given both rankings, per-skill scores and hit vectors. If the budget runs out, keep the rubric with the highest tau. The champion is selected by oracle score, so a misaligned rubric can degrade guidance but not the final pick. With K = 3, tau takes only C(4,2)+1 = 7 discrete values, hence theta_B = 0.9 means near-perfect agreement.

**Rubricator asymmetry** (Appendix A): it may only add or strengthen positive binary criteria judgeable from skill text; it may not remove positive criteria. The authors state this biases the rubric toward stricter evaluation.

**Four LLM roles** (Table 4): Bootstrapper (task description, reference -> receipt of 5 to 15 binary criteria); Verifier (skill package, receipt -> criterion hits, rationale); Generator (skill, receipt, verifier hits -> revised skill package); Rubricator (skills, receipt, rank gap -> revised receipt). Rubricator and verifier run at temperature 0, generator at 0.7. All roles use the backbone under test ("framework role model: backbone LLM", Table 5).

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| SkillsBench overall pass, GPT-5.4-mini | 62.5% | SkillOpt 58.2%, CoEvoSkills 52.5%, human-written 41.4%, LLM-written 39.5%, no skill 29.9% | Table 2, n=87 tasks | per-task best evolved skill, mean over 3 rollout seeds; no intervals |
| SkillsBench overall, GLM-5.1 | 75.1% | SkillOpt 70.5%, CoEvoSkills 66.6%, human 58.4%, none 32.7% | Table 2, n=87 | same |
| SkillsBench overall, DeepSeek-V4-Pro | 74.3% | SkillOpt 69.0%, CoEvoSkills 66.3%, human 50.1%, none 26.9% | Table 2, n=87 | same |
| SkillsBench SE category, GPT-5.4-mini / GLM / DeepSeek | 54.2% / 66.7% / 64.6% | SkillOpt 52.1% / 66.7% / 60.4%; none 26.9% / 39.6% / 40.0% | Table 2, n=16 SE tasks | SE gain over SkillOpt is 0 to 4.2 pp |
| WildClawBench overall, GPT-5.4 / GLM-5.1 / DeepSeek | 68.4% / 66.5% / 62.4% | SkillOpt 64.3% / 62.0% / 59.5%; CoEvoSkills 62.2% / 55.9% / 54.7%; none 50.3% / 48.1% / 44.4% | Table 2, n=60 | same |
| gain over static skills | "+8.8 to +11.5 pp on WildClawBench and +16.7 to +24.2 pp on SkillsBench" | human-written / LLM-written | Section 4 text | |
| token cost to first reach 0.9 pass-rate quantile, baseline / SkillLift | SkillOpt 2.68x, 2.74x, 2.62x; CoEvoSkills 2.17x, 2.22x, 2.13x | SkillLift = 1x | Table 7, SkillsBench, GPT-5.4-mini / GLM-5.1 / DeepSeek-V4-Pro | baselines given 2x SkillLift's budget; tasks already at threshold or never crossing are excluded (Appendix B token protocol) |
| "reduces token overhead by 40-70%" | stated | SkillOpt, CoEvoSkills | Figure 4 caption, abstract | Table 7 ratios imply about 53-64% (inference) |
| ablation w/o rubricator | 42.5 / 59.8 / 65.5 | full 62.5 / 75.1 / 74.3 | Table 3, SkillsBench overall | "within 1.1-1.4 pp of the static baseline on GPT-5.4-mini and GLM" (Appendix C) |
| ablation w/o seed skills (K=1) | 57.5 / 71.3 / 67.8 | full as above | Table 3 | also changes population size, so not attributable to seed quality alone (Appendix C) |
| ablation w/ score regression instead of ranking | 59.8 / 72.4 / 69.0 | full as above | Table 3 | "costs 2.7-5.3 pp under identical oracle budget" |
| K, L sensitivity | K=4 best on some cells (e.g. SkillsBench GLM L=4: 79.2) ; K=3 chosen as cost-quality point | grid K, L in {2,3,4,8} | Table 8 | single-task-set grid, no seeds reported |
| case study (paratransit) | seed 0.0 -> 1.0 verifier score at 7.37M tokens | | Figure 6 | single task |
| case study (tictoc-unnecessary-abort-detection) | seed 0.00 -> 1.00, 8.4M tokens to first >= 0.9 | | Table 9 | single task |
| hyperparameters | L=3, K=3, Mode A iters 2, Mode B iters 2, theta_A=0.85, theta_B=0.90, theta_stop=0.90, oracle success threshold 0.80 | | Table 5 | repo config (configs/skillsbench/domains/software-engineering.yaml) uses skill_count 4, mode_a_iters 3, oracle_threshold 0.75, rank_alignment_threshold 0.8 |

## Mechanism details you could implement
- Rubric as signed binary criteria, points in -5..-1 or 1..5, 5 to 15 criteria, normalized to [0,1] by the min/max achievable sums (Eq. 2). Negative criteria "only for explicit unsafe or forbidden instructions present in the skill"; "Missing required behavior is a missed positive criterion, not a negative flaw" (Bootstrap prompt, Appendix A).
- Verifier rules worth copying (Appendix A): "Judge independently from observable package evidence only"; "Do not credit intent without executable workflow evidence"; "Indeterminate positive = false; flaw not present = false"; "Keep rationale below 120 words". The framework, not the verifier, computes the score from hit weights "preventing the verifier from gaming the formula".
- Acceptance rule: accept a revision only if rubric score does not decrease; reject no-op patches before scoring; documentation-only edits only for procedural misses; metadata-only edits invalid.
- Re-alignment trigger: Kendall tau between rubric and oracle ranking of K+1 skills < 0.9. The rubricator sees "a systematic discrepancy pattern" (which skills the rubric over- or under-rates) rather than single misjudged cases. Tied oracle score groups are treated as ties.
- Oracle calls scale O(L) instead of O(LT) because rubric scoring replaces per-edit rollouts (Table 1).
- Cost accounting (Appendix B): count oracle rollouts plus all framework calls (verifier, rubricator, reflection, surrogate verification) uniformly.

## Limitations, caveats, counter-evidence
- No held-out split in the reported protocol: each skill is evolved on its task and the reported score is the best evolved skill on that same task (Section 4 "Evaluation Protocol"). The repo has a split file (skilllift_eval/benchmarks/skillsbench_split_v1.json with training batches and a test list per domain), but the paper's Table 2 reports n per category summing to all 87 tasks, so how the split is used is not stated in the paper.
- The verifier, generator and rubricator all use the same backbone as the agent under test (Section 4 Hyperparameters). The rubric judge shares the model with the system being judged; only the outer oracle is independent (deterministic verifiers on SkillsBench; WildClawBench graders, details not stated in the paper).
- No confidence intervals or significance tests; 3 rollout seeds only.
- Baselines: "SkillOpt runs at reduced scale relative to its published defaults to match our per-task oracle budget" (Appendix B), even though baselines receive 2x SkillLift's token budget.
- Gains concentrate where correctness is code-checkable; Creative tasks barely move (+3.1 on GLM-5.1), authors attribute this to difficulty of binary criteria for subjective output (Section 4).
- Rubricator can only add or strengthen criteria, which the authors say biases toward stricter evaluation.
- Paper's Table 5 settings do not match the repo's per-domain YAML (see Numbers); which values produced Table 2 is not stated beyond Table 5.
- Instruction-bearing content: the appendix contains system prompts for the authors' own LLM roles; nothing aimed at a reader's AI agent. No instructions followed.

## Takeaways for tuning a memory stack
- If we score candidate memory or procedure edits with an LLM judge, calibrate it by rank agreement with a few real outcome evaluations (Kendall tau on a small candidate set), not by score regression; the paper's ablation says an unaligned dense judge gives roughly no gain (Table 3).
- Use signed binary criteria with points computed in code; keep the judge from computing the score.
- Treat "evolved on the task, scored on the task" results as an upper bound on per-task tuning, not evidence for a shared procedural memory; our synthesis rule (persist only if it beats the current best on a held-out split) is not tested here.
- The cost win comes from replacing per-edit rollouts with one judge call; the same pattern applies to evaluating memory-policy variants in our harness if a deterministic oracle (tests) exists.

## Open questions
- Does a SkillLift-evolved skill transfer to held-out tasks in the same domain? Not reported.
- How often does the rubric pass tau >= 0.9 within B_max revisions, and what tau is reached when it does not? Not reported.
- How much of the gain survives if the judge uses a different model family than the agent? Not tested.
- Variance across seeds and per-task intervals? Not reported.

## Grading and labels
- Directness: medium. Skills are procedural memory, but the measurement is per-task optimization, not reuse across tasks.
- Control: medium. Shared seeds and backbones, component ablations (Table 3), sensitivity grid (Table 8); no intervals; baselines at reduced scale.
- Independence: low. Author-run baselines; LLM judge shares the backbone with the agent; oracle is independent.
- Reproducibility: medium. Code at commit 599358b4, prompts and hyperparameters published; config mismatch with Table 5.
- Applicability: medium. SE subset (n=16) with deterministic verifiers resembles our coding workload; build-time reads and long structured artifacts not tested.
- Strength: paper-ablated.
- Pillars: R5 primary; R4, R6 secondary.
- Stage: evaluation (surrogate grading of candidate procedural-memory revisions).
- Tags: surrogate rubric, rank alignment, Kendall tau, skill evolution, judge shares backbone, no held-out split.
- Beliefs supports: none directly.
- Beliefs contradicts: none.
- Beliefs would_create: rank-aligned surrogate judges cut revision-search cost about 2.1x to 2.7x at equal target; unaligned judges add about 1 pp.
- Contradiction: B16 not contradicted. Evolved skills beat human-written and LLM-written static skills by 8.8 to 24.2 pp, but there is no raw-trajectory arm and no transfer test, so B16 ("raw trajectories often beat distilled skills") is untouched.
- Contradiction: none with the synthesis; tension with synthesis section 1 ("persists only if it beats the current best configuration on a held-out split"): SkillLift accepts on non-decreasing rubric score and picks the champion by oracle on the same task.

## Origin chain
- Post: @rajeevchhajer roundup (2104172198537855432), "40-70% cheaper skill evolution" -> paper abstract "achieves target performance at 40-70% lower token cost" -> Figure 4 and Table 7 (SkillsBench only, cost to first reach 0.9 quantile, baselines at 2x budget).
- Independence: two authors (independent researcher, Fudan). SkillsBench (Li et al. 2026) and WildClawBench (Ding et al. 2026) are third-party benchmarks; SkillOpt and CoEvoSkills reimplemented or run by the authors. The repo vendors bounded-edits and benchmark harness hardening; oracle harnesses OpenHands (SkillsBench) and OpenClaw CLI (WildClawBench).

## Arm-vs-arm test implied (no card written)
- Arms: A = procedure/lesson revisions accepted only after a full harness rollout per edit; B = SkillLift-style signed binary rubric judge with Kendall-tau re-alignment against rollouts every round.
- Dataset: a frozen set of our coding tasks with deterministic tests (e.g., 20 to 40 tasks), procedures evolved per task and, critically, also scored on held-out tasks.
- Metric: tokens to reach a fixed pass-rate target; held-out pass rate.
- Margin: B reaches the target at <= 0.6x A's tokens with held-out pass rate within 2 pp.
- Kill: tau rarely reaches 0.9, or held-out pass rate drops > 3 pp.
- Decision it changes: whether procedural memory edits can be screened by a judge instead of rollouts.
- Cost: L (needs per-task evolution loops and rollouts). Not recommended this quarter; procedural memory is deferred (B16).
