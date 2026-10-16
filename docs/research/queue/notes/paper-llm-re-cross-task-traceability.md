---
schema_version: 1
artifact_id: N-SURVEY-20261006-04
artifact_type: note
producer: triage
run_id: survey-20261006T054504Z-b489
created_at: 2026-10-06T06:45:00Z
idempotency_key: note:survey:arxiv:2608.21531
input_refs: []
pillar_primary: R10
pillar_secondary: [R6, R9]
memory_stage: retrieval
priority: 3
beliefs_affected: {supports: [], contradicts: []}
evidence: {directness: medium, control: low, independence: high, reproducibility: medium, applicability: high}
source_url: https://arxiv.org/abs/2608.21531
found_via: survey
---

# Large Language Models for Requirements Engineering: A Cross-Task Empirical Evaluation (traceability task)

- **URL:** https://arxiv.org/abs/2608.21531 (read: HTML v1)
- **Type:** paper
- **Author / org:** Dąbrowski, Mallya, Ferrari, Zadenoori, Yu
- **Date:** August 2026
- **Retrieved:** 2026-10-06
- **Cited by evidence:** survey run, R10 question 1
- **Relevance to a memory stack:** high on applicability: real project goals and GitHub tracking issues linked to chat discussions (Rust ecosystem), which is PDLC material, not curated benchmark text.

## TL;DR
- 9 traceability cases, 80,642 Zulip messages (384 to 39,343 per case); link a project goal or tracking issue to the relevant discussion messages.
- GPT-5.5 with chain of thought: P@5 0.73 (goal to chat), 0.91 (issue to chat). DeepSeek-R1: 0.73 and 0.62.
- Lightweight models (Llama 2/3, Mistral, Gemma, Phi-3) were dropped after a pilot because short context windows broke cross-artifact reasoning; no numbers given for them.
- Human-validated links, Cohen's kappa 0.83.

## Numbers
| Model, prompt | Goal-chat P@5 | Goal-chat NDCG@5 | Issue-chat P@5 | Issue-chat NDCG@5 |
|---|---|---|---|---|
| GPT-5.5 zero-shot | 0.64 | 0.94 | 0.78 | 0.94 |
| GPT-5.5 CoT | 0.73 | 0.91 | 0.91 | 0.98 |
| DeepSeek-R1 zero-shot | 0.53 | 0.80 | 0.67 | 0.94 |
| DeepSeek-R1 CoT | 0.73 | 0.89 | 0.62 | 0.89 |

Latency: "approximately 30 seconds to 2 minutes per query". Cost: not stated. Baseline (non-LLM retrieval): not stated in what was read. Judge: humans, second reviewer on 10%.

## Limitations, caveats, counter-evidence
- n = 9 cases; P@5 only, no recall. CoT hurt DeepSeek on issue-to-chat.
- The "small models are impractical" claim rests on a pilot with whole-thread context, not on a retrieve-then-decide design (inference: a System One model scoring candidate pairs after retrieval is untested here).

## Takeaways for tuning a memory stack
- Goal-level (fuzzy) links are much harder than issue-level links (0.73 vs 0.91 P@5): expect `satisfies`/`refines` to be weaker than `implements`.
- Whole-context frontier calls at 30 s to 2 min per query are a ceiling reference, not a production design.
