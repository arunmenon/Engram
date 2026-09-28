---
schema_version: 1
artifact_id: N-SURVEY-20260927-05
artifact_type: note
producer: triage
run_id: survey-20260927T044739Z-8de9
created_at: 2026-09-27T04:53:14Z
idempotency_key: note:survey:arxiv:2608.02508
input_refs: []
pillar_primary: R5
pillar_secondary: []
beliefs_affected:
  supports: []
  contradicts: [B17]
  note: reports how many positive utility updates planted noisy memories receive under outcome-linked (trajectory-indexed) reinforcement, i.e. a feedback-loop measurement
evidence:
  directness: 5
  control: 3
  independence: 3
  reproducibility: 3
  applicability: 3
  scale: 1-5, 5 best
source_url: https://arxiv.org/abs/2608.02508
found_via: survey
---

# RoMeRL: Balancing Feedback Coverage and the Memory-Reward Trap in Self-Evolving Agent Memory via Reduced-Order Utility States

- **URL:** https://arxiv.org/abs/2608.02508 (HTML v3 read); code https://github.com/YOUNG-fnxm/RoMeRL
- **Type:** paper
- **Author / org:** Yi Yang, Zhennan Chen, Yihong Zhuang, Tiehan Fan, Yinan Chen, Jian Li, Jian Yang, Ying Tai
- **Date:** v3, 10 Aug 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, R5 question on B17 and H4
- **Relevance to a memory stack:** high. It names and measures the exact failure H4 worries about: memories that do not help still get reinforced because they co-occur with successful outcomes.

## TL;DR
- "Memory-reward trap" (Definition 2, verbatim): "A memory m_i falls into a memory-reward trap if its interventional marginal utility is non-positive while its observational raw return exceeds the interventional baseline without that memory: theta_i <= 0, mu_i - v_i^0 = theta_i + a_i > 0."
- The criticised rule is the MemRL-style trajectory-indexed update, verbatim: "Q_{i,t+1} = Q_{i,t} + alpha * 1[m_i in S_t](r_t - Q_{i,t})": every retrieved memory is credited with the task reward.
- Controlled stress test: 10 % noisy entries in the first-round memory pool, ten rounds. Under MemRL, noisy entries received on average 3.7 positive utility updates; adding UCB exploration raised that to 7.2; RoMeRL 2.4.
- The same test reports final noise ratio (share of noisy entries left after round 10): 1.02 % MemRL, 1.20 % MemRL+UCB, 0.15 % RoMeRL.
- Outcome-linked reinforcement is necessary but not sufficient: joint credit over retrieved sets reinforces bystanders.

## What it claims / describes
Instead of a Q-value per memory entry, RoMeRL represents each task's utility-bearing state with a fixed number of semantic coordinates ("reduced-order utility states") so feedback is denser (each update touches shared coordinates) and less attributable to incidental co-retrieval. Rewards come from environment outcomes (SQL execution, OS state checks, simulator results), not an LLM judge.

## Numbers

Table 2, controlled MRT stress test (verbatim):

| Method | SR (%) | Noise updates | Noise ratio (%) |
|---|---|---|---|
| MemRL | 79.2 | 3.7 | 1.02 |
| MemRL + UCB | 78.4 | 7.2 | 1.20 |
| RoMeRL | 82.0 | 2.4 | 0.15 |

Definitions (verbatim): "Positive Noise Updates denotes the average number of positive utility updates received by noisy entries over the ten rounds"; "Final Noise Ratio denotes the percentage of noisy entries in the memory pool at the end of round 10". How noisy entries are constructed, which benchmark the stress test uses, and seeds: not stated in the text read.

Table 1, main results (key rows as extracted):

| Method | OS Last/CSR | DB Last/CSR | ALFWorld | AppWorld TGC/SGC | Overall |
|---|---|---|---|---|---|
| No memory | 0.646/0.550 | 0.883/0.827 | 0.861 to 0.788 | 0.238/0.224 | 0.672 |
| MemRL | 0.808/0.820 | 0.632/0.934 | 0.908 to 0.812 | 0.313/0.286 | 0.724 |
| RoMeRL | 0.824/0.838 | 0.680/0.952 | 0.968 to 0.826 | 0.306/0.326 | 0.753 |

Other: Cold-Q ratio (share of memories with no utility update since admission) about 29 % at start; MemRL 44.9 %, RoMeRL 9.0 %. Feedback density 4.96 to 29.93 updates (6.0x).

Models: DS-V4-flash (LifelongAgentBench OS/DB, 1,000 tasks), GPT-5.4-mini (ALFWorld, 3,553 training tasks), GPT-5.6-luna (AppWorld, 105 training tasks); Text-Embedding-3-Large. Variance, cost, latency: not stated in the text read.

## Mechanism details you could implement
- Metric for H4, ready to copy: plant a known fraction (10 %) of wrong memories, run the reinforcement policy for R rounds, report (a) mean positive updates per planted entry, (b) planted share remaining, (c) task success. This is B17's "feedback-loop rate" with an operational definition.
- Avoid crediting every served memory with the task reward. Either use interventional credit (leave-one-out) or share credit through a lower-dimensional state.
- Exploration (UCB) doubled noise reinforcement (3.7 to 7.2): exploration bonuses and outcome reinforcement interact badly.

## Limitations, caveats, counter-evidence
- Authors: "RoMeRL still relies on outcome-level rewards and therefore does not fully resolve causal credit assignment." Estimating their transition quantities needs "coordinate-level causal labels from paired counterfactual rollouts".
- Stress-test construction under-specified in what was read; single-table evidence for the noise metric.
- Author-run comparison against their own reimplementation of MemRL (independence limited).
- Note that noise ratio fell from 10 % to about 1 % under all methods, so planted noise was mostly pruned anyway; the harm is in how many updates it received before being pruned (inference).

## Takeaways for tuning a memory stack
- B17 should be restated: at least one published system (RoMeRL, Aug 2026) reports a planted-noise reinforcement rate for outcome-linked memory. It is still absent from the systems in the September survey.
- H4's claim "outcome-linked beats access-count" is incomplete: the outcome-linked arm itself has two variants (joint credit to all served memories vs per-memory interventional credit), and this paper shows they differ on the loop metric.

## Open questions
- Does the effect persist with a replay-noise-free attribution (see N-SURVEY-20260927-02 on replay disagreement in counterfactual credit)?
