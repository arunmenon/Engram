---
artifact_id: N-SURVEY-20260927-04
artifact_type: note
producer: triage
run_id: survey-20260927T044739Z-8de9
created_at: 2026-09-27T04:53:14Z
idempotency_key: note:survey:arxiv:2505.16067
input_refs: []
pillar_primary: R5
pillar_secondary: [R2]
beliefs_affected:
  supports: []
  contradicts: [B17]
  note: measures error propagation from ungated self-written memories across four agents, a close proxy for the feedback-loop rate B17 says is unreported; does not report the exact H4 metric
evidence:
  directness: 4
  control: 4
  independence: 4
  reproducibility: 3
  applicability: 3
  scale: 1-5, 5 best
source_url: https://arxiv.org/abs/2505.16067
found_via: survey
---

# How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior

- **URL:** https://arxiv.org/abs/2505.16067 (HTML v2 read); ACL 2026 long paper (https://aclanthology.org/2026.acl-long.27/)
- **Type:** paper
- **Author / org:** Zidi Xiong, Yuping Lin, Wenya Xie, Pengfei He, Zirui Liu, Jiliang Tang, Himabindu Lakkaraju, Zhen Xiang
- **Date:** v2 10 Oct 2025; ACL 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, R5 question on B17 (feedback-loop rate) and H4
- **Relevance to a memory stack:** high. A controlled study of what happens when an agent stores its own executions as memory with and without an outcome evaluator.

## TL;DR
- "Experience-following": when the task input is similar to a retrieved record, the output is similar to that record's output (near-linear input-similarity vs output-similarity curves).
- Consequence 1, error propagation: wrong stored executions are retrieved as demonstrations and copied, and the copies are stored in turn.
- Storing every execution (add-all) scored below never adding anything (fixed memory) on all four agents.
- Evaluator-gated addition recovers and exceeds the fixed baseline; a strict (ground-truth) evaluator is best.
- History-based deletion (remove records with poor downstream utility) adds a few points on top.

## What it claims / describes
Four agents: RegAgent (synthetic regression), EHRAgent (health-record QA), AgentDriver (driving planning), CIC-IoT (network intrusion). Addition policies: fixed memory, add-all, selective via coarse evaluators C1 to C3, selective via strict evaluator. Deletion: periodic (retrieval frequency), history-based (utility), combined. Coarse evaluators for the three non-regression agents are LLM judges (GPT-4o-mini, GPT-4.1-mini, GPT-4.1-mini fine-tuned on 300 trajectories); the strict evaluator uses ground truth. Whether the agent backbone is the same model family as the judge: unknown from the text read.

## Numbers

Table 1, addition (verbatim values as extracted; C2 column not captured):

| Agent | Fixed | Add-all | Coarse C1 | Coarse C3 | Strict |
|---|---|---|---|---|---|
| RegAgent SR | 67.53 | 55.48 | 63.18 | 67.35 | 70.95 |
| EHRAgent ACC | 16.75 | 13.05 | 26.19 | 34.66 | 38.50 |
| AgentDriver SR | 40.11 | 32.32 | 36.92 | 47.37 | 51.00 |
| CIC-IoT ACC | 71.50 | 59.90 | 74.00 | 79.50 | 85.40 |

Table 2, deletion on top of strict addition:

| Agent | No del | Periodic | History | Combined |
|---|---|---|---|---|
| RegAgent SR | 70.95 | 67.65 | 69.80 | 66.58 |
| EHRAgent ACC | 38.67 | 38.59 | 42.06 | 42.34 |
| AgentDriver SR | 51.00 | 50.94 | 51.81 | 49.97 |
| CIC-IoT ACC | 85.40 | 80.80 | 89.60 | 85.50 |

Note: EHRAgent "No del" is 38.67 in Table 2 but Strict is 38.50 in Table 1; the text and tables disagree slightly on the same condition (possibly a different run).

Error propagation (Figure 4, described, not tabulated): for AgentDriver with add-all, the gap to an error-free-memory variant widens over about 2,000 executions; with strict addition the agent first lags, then closes the gap and surpasses the error-free variant. Exact per-step values not captured.

Seeds, variance, cost, latency: not stated in the text read.

## Mechanism details you could implement
- Gate memory addition on an outcome evaluator; a cheap judge fine-tuned on 300 labelled trajectories (C3) got most of the way to the strict evaluator.
- History-based deletion: track, per record, the correctness of the tasks it was retrieved for; delete records whose downstream error is high. The paper's Figure 6 reports deleted records had higher error than retained ones.
- Periodic (frequency-based) deletion hurt or did nothing in 3 of 4 agents; frequency of retrieval is not a good utility proxy (consistent with "reinforce on helped, not returned").

## Limitations, caveats, counter-evidence
- Non-coding domains; no build-time engineering tasks.
- Only add and delete; no summarisation, merging or reflection.
- Does not report the rate at which wrong records gain retrieval weight, because there is no reinforcement weight in these systems; error propagation is measured as downstream performance.

## Takeaways for tuning a memory stack
- B17's statement "not reported by any system in our survey" stays literally true for the survey, but a peer-reviewed measurement of the harm it guards against exists: ungated self-written memory lowered success by 7.8 to 12.2 points (RegAgent 67.53 to 55.48; CIC-IoT 71.50 to 59.90) versus not learning at all.
- H4 needs a third arm: add-all (no outcome gate). It is the realistic default of many systems and the paper shows it is below no-learning.
- History-based deletion is a concrete, outcome-linked forgetting rule to test alongside H4's reinforcement policies.

## Open questions
- Does the error-propagation effect hold when memories are raw event ledgers rather than whole (input, output) demonstrations?
- Same-model judge vs independent judge was not separated.
