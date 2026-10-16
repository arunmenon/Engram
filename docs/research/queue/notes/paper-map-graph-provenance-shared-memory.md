---
schema_version: 1
artifact_id: N-SURVEY-20261009-06
artifact_type: note
producer: triage
run_id: survey-20261009T054505Z-36b1
created_at: 2026-10-09T05:51:28Z
idempotency_key: note:survey:arxiv:2608.10509
input_refs: []
pillar_primary: R8
pillar_secondary: [R10]
memory_stage: retrieval and action gating
priority: 3
beliefs_affected:
  supports: [B25]
  contradicts: []
evidence: {directness: 4, control: 4, independence: 3, reproducibility: 1, applicability: 3}
source_url: https://arxiv.org/abs/2608.10509
found_via: survey
---

# MAP-Graph: Provenance-Aware Shared Memory for Multi-Agent Workflows

- **URL:** https://arxiv.org/abs/2608.10509 (HTML v1 read)
- **Type:** paper
- **Author / org:** Yiqi Wang, Zihao Yan, Jiaqi Zhang, Zhangkai Wu, Mingkai Zheng, Zequn Sun, Yanming Zhu, Taotao Cai (organisation not stated in extract)
- **Date:** 2026-08-11
- **Retrieved:** 2026-10-09 (local copy: out/log/raw/2608.10509.html)
- **Cited by evidence:** top-down survey, R8 question on permission vs trust vs action gate
- **Relevance to a memory stack:** medium-high. Clean ablation that separates hard permission filtering, graded path trust and an action-time gate over a typed agent/source/memory/claim/action graph.

## TL;DR
- Removing the permission filter raises task success (94.96 to 96.00) and accuracy (72.70 to 78.63) while unauthorized access goes from 0% to 100%: utility metrics hide the access failure.
- Removing the action-time gate drops success to 69.44 and raises attack success to 34.89%; removing trust propagation drops success to 87.37 and raises unsafe allows to 8.56%.
- Conditional false block Pr(Block | Allow) 3.12%.
- Synthetic, templated, single run, 7 to 9B backbones.

## What it claims / describes
Typed execution graph of agents, sources, memories, claims and actions. Steps: trace ancestry; exclude permission-ineligible records (hard); rerank eligible memories by similarity times multiplicative path trust (graded); apply a risk-sensitive gate before action; keep lineage for audit. Backbone Qwen2.5-7B-Instruct (T=0); transfer GLM-4-9B-0414, Llama-3.1-8B; bge-small-en-v1.5, k=5. 2,700 synthetic tasks in corporate workflow, software engineering and research assistance; oracle labels Allow 960 / Block 1,140 / Reverify 210 / Redact 390.

## Numbers
Ablation (Table 2, %):

| Variant | TSR | Acc | Clean | Unsafe | ASR | UAcc | Revocation viol. |
|---|---|---|---|---|---|---|---|
| Full | 94.96 | 72.70 | 90.22 | 1.52 | 0.00 | 0.00 | 0.00 |
| No action-time gate | 69.44 | 42.63 | 90.00 | 27.00 | 34.89 | 0.00 | 35.11 |
| No containment | 70.67 | 43.15 | 89.22 | 25.41 | 32.89 | 0.00 | 39.78 |
| No permission filter | 96.00 | 78.63 | 89.44 | 0.04 | 0.22 | 100.00 | 0.00 |
| No provenance stack | 67.89 | 41.89 | 89.00 | 27.89 | 29.33 | 100.00 | 46.67 |
| No trust propagation | 87.37 | 56.44 | 88.78 | 8.56 | 0.00 | 0.00 | 0.00 |

Best baseline (adapted MemLineage): TSR 74.37, Acc 51.07, ASR 22.22, UAcc 100.00. Tokens per task: MAP-Graph 4,814.9 vs shared vector 5,007.5 vs no memory 3,397.2. Latency not measured. On GLM transfer, MAP-Graph TSR 86.30 is below two baselines (87.04, 88.89).

## Mechanism details you could implement
Path trust rho = clip(S * I * F * P * V * A): S min ancestor trust (default 0.80); I multiplied by 0.25 untrusted/poisoned, 0.45 private, 0.15 revoked; F = max(0.35, 1 - loss), loss 0.08 per agent message, 0.10 per summary, 0.03 per transformation, cap 0.65; P binary CanRead; V = min(1.20, 1 + 0.05 n_v); A writer reliability 0.95. Gate thresholds 0.30 answers, 0.60 low/medium-risk actions, 0.85 high-risk. Rule order: high-risk action with affected support: Block; no support on medium/high risk: Reverify (AskUser if high); private/revoked/untrusted path: Block, Redact or Reverify; max trust below threshold: Redact, Reverify or AskUser; else Allow.

## Limitations, caveats, counter-evidence
- Synthetic templated benchmark with oracle labels; single run; TSR credits safe interventions, so read with Acc.
- Summaries lose trust per hop by design, so the result partly reflects the benchmark's construction (inference).

## Takeaways for tuning a memory stack
- Keep hard permission filtering separate from graded trust and report unauthorized access as its own metric; an accuracy benchmark will reward removing permissions.
- Trust decay per summary hop (0.10) is a concrete way to make consolidated nodes less authoritative than their sources, which links R2 consolidation to R8 gating.

## Open questions
- Does path trust help on real engineering histories where most derivations are benign?
