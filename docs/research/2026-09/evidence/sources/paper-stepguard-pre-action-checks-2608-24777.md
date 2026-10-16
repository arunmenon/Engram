---
schema_version: 1
artifact_id: N-SURVEY-20260928-23
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: []
supersedes: null
idempotency_key: note:survey:arxiv:2608.24777
claim_cluster: pre-action-checks (arxiv:2608.24777, arxiv:2503.18666, arxiv:2503.22738)
found_via: survey
source_url: https://arxiv.org/abs/2608.24777
strength: paper-ablated
pillar_primary: R9
pillar_secondary: ["R10", "R8", "R4"]
memory_stage: safety
priority: 1
tags: {"mechanism": ["4B step-level guard", "deterministic trigger-predicate-enforcement rules", "LTL policy circuits with rule retrieval by action"], "workload": ["tool-using agents", "code execution", "web agents"], "lifecycle_stage": ["gated action"], "cross_cutting": ["kinetic ontology"]}
evidence: {"directness": "medium: checks whether an agent step is unsafe, not whether a PDLC precondition holds", "control": "high: seven benchmarks, five baselines including GPT-5.4, online attack and utility measurement, latency (StepGuard); AgentSpec measures overhead in milliseconds", "independence": "medium: academic groups; StepGuard's training labels come from GPT-5.4, which is also its reference baseline", "reproducibility": "medium: public benchmarks; weights and commit not recorded", "applicability": "medium-high: the kinetic half of an ontology needs exactly this, a rule layer plus a fast model for the part rules cannot express"}
beliefs_affected: {"supports": ["B25"], "contradicts": [], "would_create": ["A 4B model can check an agent's next action about as well as a frontier model at about 0.6 s per call; deterministic predicates cost 1 to 3 ms but LLM-written rules reached only about 71% recall"]}
answers_watch_request: null
---

# Checking an action before the agent takes it: StepGuard (4B, arXiv 2608.24777), AgentSpec (rules, arXiv 2503.18666), ShieldAgent (policy circuits, arXiv 2503.22738)

- **URL:** https://arxiv.org/abs/2608.24777 ; https://arxiv.org/abs/2503.18666 ; https://arxiv.org/abs/2503.22738
- **Type:** paper (three, one cluster)
- **Author / org:** not captured in the extract
- **Date:** 2026-08-25 (StepGuard); 2025-07-31 (AgentSpec); 2025-11-27 version (ShieldAgent)
- **Retrieved:** 2026-09-28, arxiv HTML through a summarising fetch; numbers as extracted from the tables
- **Cited by evidence:** CTO focus question 4 (checking an action's preconditions before an agent acts, the kinetic half)
- **Relevance to a memory stack:** high for the design of a pre-action check. The PDLC version (does this action violate a linked requirement or constraint) is untested anywhere.

## TL;DR
- **StepGuard** is a 4B model (Qwen3-4B-Instruct) that judges each agent step.
  - Trajectory-level average (Table 1): 83.0 accuracy / 83.3 F1, against GPT-5.4 at 83.0 / 84.4, ShieldAgent-THU (7B) at 76.4 / 79.4 and LlamaGuard3-8B at 46.5 / 15.7.
  - Step-level average: 84.8 / 84.1, against TS-Guard at 84.0 / 79.9.
  - Online (Table 6): AgentDojo attack success 1.2 with utility 90.7. Mean attack success falls 77.3% at a 2.8-point utility cost.
  - Latency (Table 7): "599.9 ms and generates 195.5 tokens per guard call", which is "7.24% of the total AgentDojo task time".
- **AgentSpec** uses deterministic rules (trigger such as `before_action`, predicates, enforcement).
  - It prevents over 90% of unsafe executions on RedCode-Exec (750 cases, Table 3).
  - Overhead: parsing about 1.42 ms, predicates 1.11 to 2.83 ms, against agent tasks of 9.8 to 25.4 s.
  - Rules written by o1: 95.56% precision but 70.96% recall on embodied tasks (Table 6).
  - Safe-task completion falls from 58.62% to 54.26% (Table 4).
- **ShieldAgent** (GPT-4o) turns policies into rule circuits and retrieves only the rules relevant to the action (Table 2, 3,110 samples):
  - accuracy 90.4% and 91.7%
  - false positives 4.8%
  - 64.7% fewer API queries and 58.2% less inference time, against checking every rule

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| trajectory Acc / F1 | 83.0 / 83.3 | GPT-5.4 83.0 / 84.4 | StepGuard Table 1, 7 benchmarks | GPT-5.4 also produced the training labels |
| step Acc / F1 | 84.8 / 84.1 | TS-Guard 84.0 / 79.9 | Table 1 | |
| AgentDojo ASR / utility | 1.2 / 90.7 | not captured | Table 6 | |
| guard latency | 599.9 ms, 195.5 tokens | | Table 7 | hardware not captured |
| unsafe executions prevented | >90% | no enforcement | AgentSpec Table 3, 750 cases | 16 passed via user inspection |
| rule check overhead | 1.11 to 2.83 ms | | AgentSpec | deterministic |
| LLM-generated rule precision / recall | 95.56% / 70.96% | | AgentSpec Table 6, embodied | rules by o1 |
| ShieldAgent FPR | 4.8% | | Table 2 | GPT-4o backbone |
| ShieldAgent API query reduction | 64.7% | rule traverse | Table 2 | |

## Mechanism details you could implement
- Two tiers, as the evidence suggests:
  - Deterministic predicates written against the graph (for example, "any VERIFIES edge from a failing Test to a Requirement that this PR IMPLEMENTS", or "any active Constraint that CONSTRAINS a touched DesignElement"), in milliseconds.
  - A small typed model for preconditions stated in prose ("does this change respect the decision in ADR-12?"), in about 0.6 s.
- Retrieve only the rules attached to the action type (ShieldAgent). In an ontology this falls out for free: rules hang off the Action type, as Palantir's submission criteria do.
- A failure message per condition (Palantir), so the agent gets a reason.

## Limitations, caveats, counter-evidence
- All three test safety (harm, injection, unsafe code), not whether a lifecycle precondition holds. Whether "violates a linked constraint" is as learnable is untested (inference).
- StepGuard's teacher labels come from GPT-5.4, the same model it is compared with.

## Takeaways for tuning a memory stack
- The kinetic half has credible building blocks: millisecond rules plus a sub-second 4B checker. The open question is our precondition set, not the mechanism.

## Open questions
- Would a typed decision model (Jev Noul `action_violates_constraint`) match a 4B guard at lower latency? No source.
