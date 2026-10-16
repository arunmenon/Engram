---
schema_version: 1
artifact_id: N-SURVEY-20261009-07
artifact_type: note
producer: triage
run_id: survey-20261009T054505Z-36b1
created_at: 2026-10-09T05:51:28Z
idempotency_key: note:survey:arxiv:2610.01349
input_refs: []
pillar_primary: R8
pillar_secondary: []
memory_stage: action (execution authority)
beliefs_affected:
  supports: [B25]
  contradicts: []
evidence: {directness: 3, control: 4, independence: 4, reproducibility: 3, applicability: 4}
source_url: https://arxiv.org/abs/2610.01349
found_via: survey
---

# PACE: Provenance-Aware Capability Enforcement for Tool-Using LLM Agents

- **URL:** https://arxiv.org/abs/2610.01349 (HTML v1 read; tables partly read through an extractor, headline counts checked in the local copy)
- **Type:** paper
- **Author / org:** Fengpeng Li, Qizhou Wang, Yuke Hu, Kemou Li, Jun Liu, Haiwei Wu, Jiantao Zhou, Di Wang (PRADA Lab, KAUST)
- **Date:** 2026-10-01
- **Retrieved:** 2026-10-09 (local copy: out/log/raw/2610.01349.html)
- **Cited by evidence:** top-down survey, R8 question on execution authority
- **Relevance to a memory stack:** high for the "evidence cannot authorise its own execution" belief. Formal argument plus eight benchmarks that admission-time vetting of memory or skills is not enough and the last enforceable boundary is the tool call.

## TL;DR
- Theorem: if a safe and a leaking variant of an artifact produce the same admission evidence, a sound admission gate must treat both the same, so vetting at admission cannot settle safety.
- Enforcing at each tool call (capability and effect verification against authority compiled from the authenticated request, plus path confinement) is strictly lowest attack success in 62 of 79 attack columns, ties in 14, across AgentDojo, AgentDyn, WASP, InjecAgent-E, ASB, PASB, MCPTox, MSB.
- AgentDojo utility loss at most 2.92 points; adaptive search 0/30 out-of-authority targets (undefended 21/30).
- Ablation over 1,167 paired cases: most security gain comes from effect verification; boundary adaptation controls over-refusal.

## Numbers

| Benchmark (Qwen-3.8-27B / DeepSeek-V4-Flash / gpt-5.6-luna) | Undefended ASR | PACE ASR |
|---|---|---|
| AgentDojo (worst group) | 48.0 / 99.84 / 100.0 | 0.0 / 5.09 / 8.11 (CaMeL 0.32 / 28.14 / 36.09) |
| ASB | 88.5 / 74.08 / 81.08 | 0.42 / 10.5 / 8.75 |
| InjecAgent-E | not extracted | 0 / 3.12 / 30.77 |
| MSB (skill benchmark) | not extracted | 2.5 / 3.75 / 3.75 |

AgentDyn utility falls 66.7% to 33.3% from no defense to full PACE in the ablation table (small task count). The paper states "A numerical mediation-overhead summary is not reported in this manuscript"; latency unknown. Code in supplemental material; no public repo seen.

## Mechanism details you could implement
- Compile authority from the authenticated user request into allowed (tool, effect) pairs; check each call's schema-declared effect against it immediately before dispatch.
- Do not relax enforcement because an artifact (memory item, skill, retrieved page) passed admission vetting.

## Limitations, caveats, counter-evidence
- Out of scope: model-recomposed strings without host provenance, unexposed effects, tool-internal calls, writes that bypass versioned adapters; paraphrase and fragmentation outside the derivation check.
- Not memory-specific: no dedicated memory-poisoning column was confirmed.

## Takeaways for tuning a memory stack
- Supports B25 with independent evidence: memory gates (H10b) reduce exposure but cannot be the authority boundary; the agent's tool layer must check effects against the human request.
- Engram should pass provenance of served items to the agent's tool layer so it can do this.

## Open questions
- Engineering effects (merge, deploy, write file) are broad; how tight can a compiled authority be without blocking normal build work?
