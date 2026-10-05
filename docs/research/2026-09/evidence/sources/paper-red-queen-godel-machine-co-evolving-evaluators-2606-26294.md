---
schema_version: 1
artifact_id: N-20260929-27
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104629489154265476", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2606.26294
claim_cluster: arxiv:2606.26294
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2606.26294
source_commit: n/a
strength: paper-ablated
pillar_primary: R5
pillar_secondary: ["R6", "R4"]
memory_stage: evaluation
tags: {"mechanism": ["co-evolving-evaluators", "controlled-utility-evolution", "epoch-frozen-judge", "anchor-gated-judge-replacement", "selective-erasure", "adversarial-pool", "clade-metaproductivity", "epsilon-best-belief"], "workload": ["polyglot-coding", "apres-paper-review", "imo-proof-grading", "self-improving-agents"], "lifecycle_stage": ["evaluate", "select", "self-modify"], "cross_cutting": ["reward-hacking", "llm-as-judge", "self-preference-bias", "data-isolation", "cost-accounting"]}
evidence_grade: {"directness": "medium: directly measures judges inside a self-improvement loop, but on coding, paper review and proof grading, not memory systems", "control": "medium: matched evaluation budgets (12,288 evals) vs HGM-H, held-out test splits, mechanism ablations (Table 7), but single run per arm, ablations use a different model (Nemotron 3 Super), and headline 1.86x is at 5.2x the tokens", "independence": "low: authors built the method, the co-evolved reviewers that sit on the scoring panel, and the baselines' reimplementation (HGM-H); no external replication", "reproducibility": "low: no code URL found; preliminary preprint 'work in progress'; prompts and search config published in App. C", "applicability": "medium: an LLM judge frozen per epoch and replaced only when it beats a human-labelled anchor transfers to any memory-config tuning loop graded by an LLM judge (inference)"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A fixed LLM judge inside an optimisation loop is saturated by the optimised generator: with replacement off the writer reached 75/75 accepted (100.0% writer val acc) while that judge's anchor accuracy was 78.2%, vs 95.0% with anchor-gated replacement plus erasure (one Nemotron 3 Super paper-review run, Table 7)", "An LLM reviewer can reach higher raw benchmark accuracy by over-accepting AI-generated text (1.42x to 1.91x the human-paper rate for the HGM-H reviewer); judge accuracy alone does not certify a judge for scoring AI outputs"]}
claim_correction: Reward hacking is not measured as a rate; prevention is shown indirectly by one fixed-critic ablation and the reviewer AI-over-acceptance analysis; the coding result is Polyglot (119 vs 116 of 166 held-out tasks), SWE-bench was not run; the 1.86x writer gain uses 221.8M vs 42.5M search tokens.
---

# The Red Queen Godel Machine: Co-Evolving Agents and Their Evaluators (RQGM)

- **URL:** https://arxiv.org/abs/2606.26294
- **Type:** paper (cs.LG), "Preliminary preprint; work in progress"; 13 pages main text + 21 pages appendix
- **Author / org:** Alex Iacob, Andrej Jovanovic, William F. Shen, Daniel Burkhardt, Meghdad Kurmanji, Nurbek Tastan, Lorenzo Sani, Niccolo Alberto Elia Venanzi, Ambroise Odonnat, Zeyu Cao, Bill Marino, Xinchi Qiu, Nicholas D. Lane (University of Cambridge, NVIDIA, Flower Labs, MBZUAI, Inria)
- **Date:** v1 2026-06-24, v2 2026-06-29
- **Retrieved:** 2026-09-29, arXiv v2 (abstract page; HTML returned 404 for both /html/2606.26294 and /html/2606.26294v2; PDF pages 1 to 13, 17 to 27 and 38 read directly as images). Theory appendix pages 28 to 37 not read.
- **Cited by evidence:** X post 2104629489154265476 by @che_shr_cat, https://x.com/che_shr_cat/status/2104629489154265476 (post text as summarised in the triage brief; not fetched). Secondary write-up https://arxiviq.substack.com/p/the-red-queen-godel-machine-co-evolving was not fetched and is not relied on.
- **Relevance to a memory stack:** medium. Not a memory paper. Its value for us is the evaluation-loop design: when you tune memory policies against an LLM judge, the judge becomes the target. RQGM gives a concrete protocol (frozen judge per epoch, replace only on a human-labelled anchor, erase scores from the displaced judge, adversarial pool of outputs the old judge over-accepted) plus one ablation showing a fixed judge gets saturated.

## TL;DR
- RQGM extends the Huxley-Godel Machine (HGM) archive search so each archive node is a multi-agent workspace holding both task agents and learned evaluators. Evaluators are frozen within an "evolutionary epoch"; at checkpoints (power-of-two schedule) a challenger evaluator replaces the incumbent only if its epsilon-best-belief score on a fixed ground-truth anchor is higher; then "selective erasure" drops every utility record scored by the displaced evaluator ("controlled utility evolution", Sections 3.4, 3.5).
- Coding (Polyglot, 166 held-out tasks): RQGM reaches 71.7% vs HGM-H 69.9% (119 vs 116 passes, Table 5) by co-evolving a code reviewer anchored to CRAVE, at "1.35x-1.72x fewer tokens" to exceed the baseline rate (Figure 1). SWE-bench was excluded: "The long runtime of SWE-bench precluded its inclusion in this version of our work" (Section 4).
- Paper writing (APReS, 100 generated papers per writer, 4-reviewer panel): mean acceptance 21.8% HGM-H vs 38.8% RQGM generalist (1.78x, 44.6M vs 42.5M tokens) and 40.5% RQGM specialist (1.86x, at 221.8M tokens) (Table 1).
- Judge bias: the HGM-H reviewer "accepts AI-generated papers at 1.42x-1.91x the rate of human ones" (Section 5.4); the RQGM adversarial reviewer accepts both at similar rates "while retaining 80% ground-truth accuracy" (vs 88% for the lenient HGM-H specialist, Table 5).
- Closest thing to a reward-hacking measurement (Table 7, Nemotron 3 Super, paper review): fixed critic gives writer val acceptance 100.0% (75/75) with reviewer anchor accuracy 78.2%; full mechanism 90.1% / 95.0%. Claim correction vs post: reward hacking is argued and shown indirectly, not measured as a rate; coding is Polyglot, not SWE-bench.

## What it claims / describes
**Base search (Section 3.1).** Tree search over an archive T_t seeded with a_0. Each step either modifies a node (child added) or evaluates a node on a task with binary outcome. Search utility is HGM's clade metaproductivity: CMP(a) = n_success^C(a) / (n_success^C(a) + n_failure^C(a)) pooled over the subtree rooted at a; nodes selected by Thompson sampling. Final agent = epsilon-best-belief BB_eps(a) = I^-1_eps(1 + S_a, 1 + F_a), the eps-quantile of the Beta posterior (eps = 0.05, "five-outcome anchor minimum", Table 3).

**Search space (Section 3.2).** Each node is a workspace with K roles, each role with its own task pool; utility averages uniformly over a role's tasks then over roles. Roles with a fixed benchmark are "evaluator-independent"; open-ended roles (paper writing, proof writing) are "evaluator-dependent" and scored by an evaluator slot. Replacing a slot increments that slot's epoch index.

**Data isolation (Section 3.2).** "RQGM separates feedback that creates nodes from evidence that selects them." Meta-agent sees only a training subset; selection uses a disjoint validation split; reports use a held-out test split. For evaluator-dependent roles, fresh artifacts are generated for search.

**Scheduler (Section 3.3).** UCB-Air gate: expand when N_t^alpha >= |T_t| (alpha = 0.6), else evaluate; archive size O(N_t^alpha). Evaluation picks the least-evaluated eligible role then task at the Thompson-sampled node.

**Co-evolving evaluation (Sections 3.4, 3.5, Algorithm 1).** Evaluators, artifact protocol and binary scoring rule are frozen per epoch (epoch-local stationarity, Asm. 2). At each checkpoint, for each slot: candidates = incumbent plus challengers from the archive; score each by BB_eps on the ground-truth anchor counts; promote the best, ties to incumbent; on change, freeze the new evaluator, erase the slot's records, recompute CMP. Old nodes are re-scored lazily when the scheduler revisits them; cached agent outputs are reused. With exponentially spaced checkpoints (ratio rho > 1) re-evaluation exposure is O(B) instead of O(B^2) for uniform checkpoints (Prop. 6, Rem. 7). Guarantees are epoch-local only.

**Adversarial pool (Section 4, 5.4).** In the paper domain, after the first replacement "papers accepted by the displaced reviewer form an adversarial pool, and the subsequent epoch additionally rewards rejecting these writer-generated papers while maintaining accuracy on the human APReS data." Replacement stays anchored to APReS.

**Domains and anchors (Section 4, App. C.1).** Paper writing / review anchored to APReS accept/reject decisions; proof writing / grading anchored to IMO-GradingBench human grades (proof accepted only at 7 of 7); coding anchored to executable Polyglot tests, code reviewer anchored to CRAVE (accepted/rejected PRs). Baseline HGM-H (HyperAgents with HGM search, fixed external evaluator: Sakana prompt reviewer, ProofAutoGrader, IMO25 prover), plus published DGM-H patches as a DGM-level proxy.

**Models and budget (App. C.2, C.3, Table 3).** All main runs and held-out scoring use GPT-5.5 (low). Ablations use Nemotron 3 Super; cost ablation routes search-time task-agent calls to Nemotron 3 Ultra. Eight main experiments. Budget per run 12,288 evaluations ("8,192 + 4,096"), train samples per node 3. Splits: APReS / IMO-GradingBench / CRAVE test 100 items each; Polyglot train 10, validation 49, test 166. Caps: expand $25 and 1,200 s; train $8 and 900 s; validation $25 and 1,200 s. Blended tokens = input + 5x output. Uncertainty: 95% Jeffreys intervals (writer panel), s.e.m. (prover panel).

**Initial agents (App. C.5).** Every task agent starts as one LLM call from "You are an agent. Task input: {inputs} {output_format}". The meta-agent instruction (quoted in full in the paper) tells the self-modifying agent that "your utility is computed on a HELD-OUT validation set you NEVER see ... Do NOT hardcode answers, memorize specific question ids, or otherwise overfit to the train samples" and that "gaming the parser or breaking the harness scores 0."

**What evolved (App. E).** Evaluators moved from one-line instructions to criterion-bearing rubrics. The Polyglot code-review slot was replaced three times and moved "toward evidence-bounded review", e.g. node 86: "Do not invent blockers from missing project context; the diff alone must show the defect." The adversarial reviewer's rule: "accept only if the paper has a clear nontrivial contribution ... Do not be swayed by fluent writing alone."

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Polyglot held-out pass rate | 71.7% (119/166), specialist and generalist | HGM-H 69.9% (116/166) | 166 held-out tasks; Section 1, Table 5 | 3-task difference, single run per arm; no interval reported for this cell (inference: within noise) |
| Tokens to exceed baseline pass rate | 1.35x (specialist) to 1.72x (generalist) fewer | HGM-H about 122M blended tokens (Figure 1) | Figure 1 | cost measured at first attainment of best belief |
| Writer mean panel acceptance | RQGM generalist 38.8 +/- 4.8% (1.78x); specialist 40.5 +/- 4.8% (1.86x) | HGM-H writer 21.8 +/- 4.0% | Table 1; 100 papers per writer x 4 reviewers (N = 400) | tokens 44.6M / 221.8M vs 42.5M: 1.86x is not compute-matched; panel includes the RQGM adversarial reviewer co-evolved in the same run |
| Writer acceptance by Sakana / DGM-H / HGM-H / RQGM adversarial reviewer | HGM-H writer 1.0 / 12.0 / 64.0 / 10.0; RQGM generalist 2.0 / 43.0 / 81.0 / 29.0; RQGM specialist 5.0 / 40.0 / 86.0 / 31.0 | | Table 1 | Jeffreys half-widths 2.2 to 9.6 |
| Proof score (0 to 7), Pass@6, Pass@7 | RQGM specialist 4.33 +/- 0.41, 61.7%, 48.3%; RQGM generalist 3.73, 51.7%, 45.0% | static IMO25 prover 4.07, 55.0%, 55.0%; HGM-H prover 3.73, 51.7%, 45.0% | Table 2; 20 IMO problems x 3 graders (N = 60), +/- s.e.m. | specialist loses to IMO25 on Pass@7; tokens 88.0M vs HGM-H 21.5M |
| Per-grader proof means (RQGM grader column) | specialist 4.95, P@6 70.0, P@7 60.0 | IMO25 4.05 / 55.0 / 55.0 | Table 6 | the RQGM grader scores its co-evolved prover highest (possible co-adaptation, inference) |
| IMO-GradingBench grader accuracy | RQGM grader highest (about 76% read from Figure 5) | ProofAutoGrader about 74%, HGM-H grader about 70% (Figure 5) | 100 held-out items | values read approximately from figure; exact numbers not in text read |
| Grader search cost | "3x lower search cost than HGM-H" (specialist point); 1.35x more at generalist point, still better | HGM-H grader 28.0M tokens | Section 5.4, Figure 5 | |
| APReS reviewer accuracy / acceptance | HGM-H specialist 88 / 45; RQGM specialist 84 / 40; RQGM generalist pre-replacement 84 / 42; RQGM adversarial post-replacement 80 / 32; DGM-H published 73 / 25; Sakana 63 / 13 | | Table 5; n = 100 held-out APReS papers | |
| AI-vs-human over-acceptance, HGM-H reviewer | 1.42x to 1.91x the human rate | | Section 5.4 (abstract: "up to 1.91x") | computed on Table 1 writers |
| Fixed critic ablation | writer val acc 100.0 +/- 1.7% (75/75 accepted), reviewer anchor acc 78.2 +/- 4.4% | full mechanism 90.1 +/- 3.5% / 95.0 +/- 10.3% | Table 7, Nemotron 3 Super, 12,288 evals, paper review | writer acceptance is scored by each run's own critic, not comparable across runs; single run each |
| Replacement only (no adversarial pool) | 89.5 +/- 13.7% / 91.2 +/- 7.4%; anchor result 52/57 | | Table 7, App. D.2 | |
| No erasure | 90.0 +/- 10.7% / 92.9 +/- 10.8% | | Table 7 | slot "oscillates through an A->B->A return of a displaced critic" |
| Rank change at replacement | Spearman rho settles "well below 1" | no-erasure control rho >= 0.90 | Figure 3 | |
| Cost split | validation 65 to 69%, expansion 18 to 23%, train-time eval 12 to 14% of blended tokens | | Figure 9, App. D.3.1 | |
| Shared-surface patches | 59 to 90% of accepted patches; 90% in Polyglot | | App. D.3.2, Section 5.1 | |
| Hybrid-model cost | about 13.0x lower search-token cost approaching GPT-5.5-only accuracy; 1.87M GPT-5.5-price-equivalent vs B = 6.68M Nemotron tokens | GPT-5.5-only run | Figure 7, App. C.4; held-out APReS N = 100 | price-equivalent conversion 0.28B is the authors' assumption |

## Mechanism details you could implement
- **Freeze the judge per epoch.** Never change the judge mid-comparison; all scores in an epoch come from one frozen judge version, recorded with the score.
- **Anchor-gated replacement.** Keep a fixed human-labelled anchor set (paper: 100 items per domain). A challenger judge replaces the incumbent only if its lower-bound score BB_eps = eps-quantile of Beta(1 + successes, 1 + failures) on the anchor (eps = 0.05, at least 5 anchor outcomes) is higher; ties keep the incumbent.
- **Selective erasure.** On replacement, delete (or mark invalid) every score produced by the displaced judge; re-score lazily when a candidate is revisited, reusing cached outputs. Do not mix scores across judge versions.
- **Checkpoint schedule.** Power-of-two checkpoints (rho = 2) bound re-evaluation to at most 2B.
- **Adversarial pool.** Outputs the displaced judge accepted become negatives the next judge is rewarded for rejecting, while holding accuracy on the human anchor. Use this when the judge shows self-preference for model-generated outputs.
- **Split discipline.** Optimiser sees train feedback only; selection on a validation split it never sees; report on a separate test split; tell the optimiser explicitly that gaming the parser scores 0.
- Search constants to copy if you run HGM-style search: alpha = 0.6, 3 train samples per node, 12,288 evaluation budget, output tokens per call 32,768, coder tool calls <= 16 (Tables 3, 4).

## Limitations, caveats, counter-evidence
- App. G (verbatim excerpts): "We have not yet explored the complete design space ... due to computational constraints"; "all of our main experimental results relied exclusively on GPT-5.5 (low)"; guarantees operate "strictly at an epoch-local level, bounding neither transition counts, cumulative regret from erased evidence, nor long-term convergence"; "Asm. 2 cannot strictly hold in real-world deployments due to ... provider-side model updates, nondeterministic tools"; "The reviewer panel inherently measures cross-reviewer acceptance behavior rather than objective, ground-truth scientific merit, and no human grading of the generated papers or proofs was performed"; "anchor weakness, where a weak, noisy, or biased anchor allows evaluators to drift across epochs, particularly since APReS decisions and IMO-GradingBench grades are themselves imperfect"; the loop "is still hand-crafted".
- Single run per arm; no seeds or variance across runs. Polyglot gain is 3 of 166 tasks.
- The 1.86x specialist result uses 5.2x the search tokens of the HGM-H writer; only the 1.78x generalist result is compute-matched.
- The scoring panel includes the RQGM adversarial reviewer produced by the same run, and the RQGM grader rates the RQGM prover highest (Table 6), so co-adaptation between generator and panel members is possible (inference).
- Mechanism ablations use Nemotron 3 Super, not GPT-5.5, and the paper notes its "replacement decisions partly reflect reliability fixes rather than review logic".
- Reward hacking is motivated, and the fixed-critic run shows saturation, but no reward-hacking rate, exploit taxonomy or held-out exploit test is reported.
- No code URL was found in the pages read.
- Instruction-bearing content: the paper quotes its own meta-agent prompt ("Modify any part of the codebase at {repo_path} ..."). It is addressed to the authors' meta-agent, recorded here as evidence and not followed. No text addressed to readers or AI agents otherwise.

## Takeaways for tuning a memory stack
- If we tune memory policies (write gate thresholds, recall k, assembly budget) against an LLM judge, expect saturation of a fixed judge. Hold a human-labelled anchor set and gate judge changes on it, with a lower-bound (Beta quantile) rule rather than a point estimate.
- Version the judge on every score and invalidate scores on judge change instead of comparing across versions; this fits our B19 remediation of eval leakage (inference).
- Check judges for self-preference on model-written artifacts (for us: agent-written specs or PDLC documents vs human-written). A judge with higher raw accuracy can be the one that over-accepts model text.
- Evidence-bounded review rules ("the diff alone must show the defect") emerged for code review; a similar rule for grading memory-served answers ("the served evidence must support the claim") is a candidate rubric (inference).
- Validation evaluation dominated cost (65 to 69%); budget our eval loops around evaluation, not generation.

## Open questions
- Does anchor-gated replacement still help when the anchor is small (tens of items) as ours would be? Not tested.
- How often does the optimised generator exploit the frozen judge within an epoch? Not measured.
- Would results hold with multiple seeds, a SWE-bench-class coding task, or a model other than GPT-5.5 (low)?
- Arm-vs-arm test implied for us: fixed LLM judge vs epoch-frozen, anchor-gated judge with erasure, in a memory-config search loop, measuring judge agreement with a held-out human-labelled set over iterations. Feasible this quarter only if a labelled anchor of about 100 items exists (inference).

## Grading and labels
- Directness: medium. Measures judges inside self-improvement loops, not memory.
- Control: medium. Matched evaluation budgets and held-out splits, Table 7 ablations; single runs, different model for ablations, headline specialist not compute-matched.
- Independence: low. Authors built method, panel members and baseline reimplementation.
- Reproducibility: low. No code URL found; preliminary preprint; configs and prompts in App. C.
- Applicability: medium. Judge-governance protocol transfers to any LLM-judged tuning loop (inference).
- Pillars: R5 primary (self-improvement loop, harmful reinforcement via judge saturation); R6 secondary (judge bias, anchors, leakage-proof splits); R4 secondary (when to promote an automated judge: lower-bound rule).
- Stage: evaluation.
- Tags: mechanism co-evolving evaluators, controlled utility evolution, anchor-gated replacement, selective erasure, adversarial pool; workload Polyglot, APReS, IMO grading; lifecycle evaluate, select, self-modify.
- Beliefs supported: none directly. B15 (comparative evidence across lineages) is related because RQGM inherits HGM clade metaproductivity, but the paper does not ablate lineage comparison. B17 (feedback-loop rate unreported) is related: Table 7 is a judge-saturation measurement, not a wrong-memory reinforcement rate, so B17 is unaffected. B19 is our own harness and is not tested here.
- Beliefs contradicted: none.
- Would create: fixed-judge saturation inside optimisation loops; judge accuracy does not certify judges for AI-written outputs (see frontmatter).
- Contradiction rows: none.

## Origin chain
X post 2104629489154265476 (@che_shr_cat; not fetched) and secondary arxiviq Substack write-up (not fetched) -> arXiv 2606.26294 v2 (abstract page; PDF, HTML unavailable) -> Figure 1 and Table 5 (Polyglot 71.7 vs 69.9, 1.35x to 1.72x fewer tokens), Table 1 (1.78x, 1.86x), Section 5.4 (1.42x to 1.91x AI over-acceptance), Table 7 (fixed critic saturation), App. G (limitations). Independence: the post and Substack are secondary summaries of the same paper; no independent replication; the scoring panel is partly produced by the method under test.
