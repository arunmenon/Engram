---
schema_version: 1
artifact_id: N-SURVEY-20260930-05
artifact_type: note
producer: triage
run_id: survey-20260930T054503Z-298f
created_at: 2026-09-30T05:57:40Z
idempotency_key: note:survey:arxiv:2608.18066
input_refs: []
pillar_primary: R6
pillar_secondary: [R5]
memory_stage: evaluation
beliefs_affected:
  supports: [B20, B16]
  contradicts: []
evidence: {directness: high, control: high, independence: high, reproducibility: high, applicability: medium}
strength: paper-ablated
source_url: https://arxiv.org/abs/2608.18066
found_via: survey
---

# On the Fragility of Self-Improving Agents: Variance, Task Order, and Underspecification

- **URL:** https://arxiv.org/abs/2608.18066 (HTML v2 read: https://arxiv.org/html/2608.18066v2); code https://github.com/SalesforceAIResearch/self-improve-fragility ; data https://huggingface.co/datasets/Salesforce/self-improve-fragility (neither cloned)
- **Type:** paper (independent re-evaluation)
- **Author / org:** Qinyuan Ye, Yu Li, Yada Pruksachatkun, Jiaxin Zhang, Chien-Sheng Wu (Salesforce AI Research)
- **Date:** 2026-08-18 (v1), 2026-09-06 (v2)
- **Retrieved:** 2026-09-30 (local copy: out/log/raw/2608.18066.html)
- **Cited by evidence:** survey run survey-20260930T054503Z-298f, R6 question 2 (statistics for small evals) and question 5 (how often a headline claim survives an independent read)
- **Relevance to a memory stack:** high for how H4 and H6 must be run. It re-evaluates two published learn-from-experience memory methods with repeated runs and shuffled task order, and the headline gains do not survive.

## TL;DR
- Two methods, Agent Workflow Memory (AWM) and ReasoningBank (RBank), re-run on WebArena (812 tasks), VisualWebArena (910) and SCUBA (267) with GPT-5-mini, three self-improving runs per experiment, ground-truth rewards (no LLM judge).
- In default task order, ReasoningBank gains +1.5 points on WebArena over no memory (56.3 against 54.8) and "a two-sided Welch's t-test on three runs gives p=0.23". AWM is below no memory on all three benchmarks.
- Under shuffled task order both methods fall below no memory on WebArena: 49.1 to 50.7 against 54.8.
- Adding a memory loop raised run-to-run variance in 17 of 24 domain cases (71 %); in 11 the relative increase exceeded 50 %. Best-to-worst gap across three runs reached 10.42 points.
- Supplying rubrics, environment feedback and a prompt change to memory construction recovers part of the loss (49.8 to 52.7 on one shuffle) and still leaves the agent under the no-memory baseline.

## What it claims / describes
Prior work evaluated these methods once, in the benchmark's default order. The default order groups related tasks, which the authors call "an implicit curriculum, acting as a hidden prerequisite for success". The re-evaluation widens two axes: (1) several self-improving runs to measure variance, (2) two random shuffles of the task stream.

The authors then read the generated memories and find "plausible yet inapplicable memories (e.g., recommending API usage in a browser-only environment)", which they attribute to underspecified tasks and environments. They test this by adding three kinds of information to memory construction:
- +Rub: evaluator rubric and score, for example "Evaluator: string_match | Score: 0.0 (FAIL)".
- +Env: environment feedback, for example "Action error: Failed to input text into index 41".
- +PMod: a prompt that lists what to include ("Procedural knowledge, reusable workflows, site navigation structure, UI interaction tips") and what to avoid ("API or programmatic solutions, visiting external websites, requesting human confirmation").

Rewards for memory construction are ground truth, chosen to avoid adding judge noise.

## Numbers
| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| WebArena, default order | AWM 54.1 %; RBank 56.3 % | no memory 54.8 % | GPT-5-mini, 3 runs | RBank +1.5, Welch p=0.23 |
| VisualWebArena, default order | AWM 54.5 %; RBank 55.6 % | 54.9 % | same | |
| SCUBA, default order | AWM 28.0 %; RBank 31.1 % | 29.7 % | same | |
| WebArena, Shuffle-1 | AWM 49.1 %; RBank 49.8 % | 54.8 % | 3 runs | below no memory |
| WebArena, Shuffle-2 | AWM 49.8 %; RBank 50.7 % | 54.8 % | 3 runs | below no memory |
| Abstract's summary of order effect | shuffled "degrades (-4.5%) instead of exhibiting the expected improvement (+1.5%)" | | | |
| Variance change when memory is added | increased in 17 of 24 cases; over +50 % relative in 11 | no-memory std per domain 0.30 to 2.77 points | 3 runs, 12 domains, 2 methods | |
| Largest best-to-worst gap | 10.42 points (RBank, WebArena Multisite; std 4.28) | no memory 2.08 (std 0.98) | 3 runs | |
| No-memory baseline spread | WebArena average pass 54.8 %; Pass@3 65.4 %; all three runs pass 43.3 % | | | 22 points between "any run passes" and "every run passes" |
| SCUBA Admin std | AWM 2.09; RBank 1.58 | no memory 0.30 | 3 runs | |
| RBank with +Rub, +Env, +PMod combined | Shuffle-1 52.7 % (from 49.8 %); Shuffle-2 about 51.8 %; default about 56 % | no memory 54.8 % | | figures read from a chart for the "about" values |
| Prior published numbers | AWM 36.3 % (Claude-3.5-Sonnet); RBank 53.9 % (Gemini-2.5-Pro, 684 tasks) | | | different backbones, not comparable |
| Cost, latency | not stated | | | |
| Judge shares a model with the system | no judge; benchmark ground-truth evaluators | | | |

Text versus table: the abstract says variance increases "in 71% of cases"; the table count is 17 of 24 (70.8 %). Consistent.

## Mechanism details you could implement
- Minimum protocol for any learn-from-experience arm: at least 3 full self-improving runs; report mean, standard deviation and best-to-worst gap per domain; repeat under at least 2 random task orders; test the gain against the no-memory arm (the authors use Welch's t-test on run means).
- Report three pass rates for the unchanged agent: average, any-run-passes and every-run-passes. The spread is the agent's own noise before memory is added.
- Feed the memory writer the evaluator's rubric outcome and the environment's error messages, and tell it what kinds of lesson are out of scope for the environment. This was the only intervention that moved the shuffled result.
- The paper's recommendation: "first piloting new methods on benchmarks with well-specified tasks, followed by stress-testing them on underspecified tasks".

## Limitations, caveats, counter-evidence
- Stated: web-browsing tasks, one primary model (supplementary runs on GPT-OSS-120B and Gemini-2.5-Pro, up to 6 runs).
- Stated: memory inspection was qualitative and covered a subset.
- Stated: "Underspecification only explains part of the performance degradation, and the reasons behind the remaining performance gap are still unknown."
- Three runs give a weak test; p=0.23 means the +1.5 is not shown, not that it is absent.
- (inference) Web navigation is not build-time engineering work. The order effect should carry over to any replayed task stream, because it is a property of learning from a stream, but its size on software tasks is unknown.
- Counter-evidence on the bus: CL-Bench (N-SURVEY-20260927-06) found naive in-context history had the highest gain. Both results point the same way: distilled lessons are fragile; neither shows that memory cannot help.

## Takeaways for tuning a memory stack
- H4 and H6 run on "a replayed task stream". The stream's order is a hidden variable. Run each arm under the original order and at least two shuffles, or the result may be a curriculum effect.
- The plan's noise-floor rule (run the unchanged stack at least 5 times) is necessary and not sufficient: the memory arm has its own, larger variance, so it needs its own repeated runs.
- The landscape lists ReasoningBank's item schema as a drop-in pattern for BehavioralPattern nodes. This re-evaluation finds its published gain is not significant in default order and negative under shuffling with GPT-5-mini. Treat the schema as untested.
- Give Consumer 4's lesson writer the outcome evidence (test results, error text) and an explicit scope, not only the trajectory.

## Open questions
- Does raw-trajectory retrieval (no distillation) show the same order sensitivity?
- How many runs are needed for a 2-point margin at the variances reported here? With a run-level std near 2 to 4 points, three runs cannot resolve it (inference).
- Does scoping a lesson to the task family that produced it (PC-20260927-01) remove the shuffled-order loss?
