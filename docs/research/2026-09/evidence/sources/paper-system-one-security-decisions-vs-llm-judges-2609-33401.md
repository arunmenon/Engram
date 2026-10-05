---
schema_version: 1
artifact_id: N-SURVEY-20260929-03
artifact_type: note
producer: triage
run_id: survey-20260929T054503Z-ed98
created_at: 2026-09-29T05:59:00Z
idempotency_key: note:survey:arxiv:2609.33401
input_refs: []
pillar_primary: R9
pillar_secondary: [R8, R4]
memory_stage: safety
priority: 2
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 3
  control: 4
  independence: 5
  reproducibility: 4
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.33401
secondary_sources:
  - https://arxiv.org/abs/2609.34862
found_via: survey
claim_cluster: system-one-security-gate-vs-llm-judges
---

# Jev and open-weight System One models as security gates against generative judges (arXiv 2609.33401, with arXiv 2609.34862)

- **URL:** https://arxiv.org/abs/2609.33401 (code https://github.com/yxsec/system-one-security-eval). Companion: https://arxiv.org/abs/2609.34862 (no code link found)
- **Type:** paper (two independent papers)
- **Author / org:** Yixuan Liu (TraceStone; NTU Singapore), targeting FSE 2027; companion Zhiqiang Wang and Yichao Gao (USTC)
- **Date:** 2026-09-27; 2026-09
- **Retrieved:** 2026-09-29
- **Cited by evidence:** survey run, R9 question 1 (head-to-head against Jev) and priority 2 (open-weight comparison)
- **Relevance to a memory stack:** medium-high. Our injection gate on served memory (H10, B24) and any trace-level safety check would use exactly these decisions. It is the first independent head-to-head of Jev against three open-weight System One models (Laya, Decider ~2B, Bespoke Nimble ~9B) on the same populations, with benchmark labels, not an LLM judge.

## TL;DR
- Jev ranked first of eight on R-Judge (macro-F1 0.879) and AgentHarm (0.840) against non-reasoning judges (GPT-4.1, Qwen3-8B) and specialist classifiers; second on WAInjectBench (0.757 vs Nimble 0.779).
- Adding reasoning judges changes the order: on R-Judge DeepSeek-V4.1-Flash 0.962, GLM-5.3-Flash 0.924 and Qwen3.8-27B 0.924 all beat Jev; Jev falls to fourth on R-Judge and WAInjectBench, stays first on AgentHarm.
- Open-weight System One models are unstable across tasks: Nimble 0.779 on WAInjectBench but 0.364 on R-Judge; Decider 0.503 (FNR 0.950) on WAInjectBench; Laya 0.492 on R-Judge.
- Jev's errors are misses, not false alarms, on injection: FNR 0.597, FPR 0.001 on WAInjectBench.
- On 5,219 agent traces (2609.34862), Jev F1 77.8 vs GLM-5.2 74.1 at median 0.99 s vs 33.29 s and $0.000195 vs $0.014887 per valid result (list-price estimates); Jev is better on long traces (more than 16 steps: 57.5 vs 50.6).

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| WAInjectBench macro-F1 | Jev 0.757 [0.454, 0.937], FNR 0.597, FPR 0.001 | Nimble 0.779 [0.497, 0.936]; Qwen3-8B 0.765; GPT-4.1 0.708; Laya 0.649; Decider 0.503 (FNR 0.950) | N=1,610 shared test | wide CIs |
| R-Judge macro-F1 | Jev 0.879 [0.814, 0.935], FNR 0.085, FPR 0.148 | GPT-4.1 0.796; Laya 0.492; Decider 0.417; Nimble 0.364 (FPR 0.885) | N=108 | small test |
| AgentHarm macro-F1 | Jev 0.840 [0.774, 0.903] | Nimble 0.831; Decider 0.778; GPT-4.1 0.741; Laya 0.731; WildGuard 0.584 | N=352 | |
| R-Judge with reasoning judges | DeepSeek-V4.1-Flash 0.962; GLM-5.3-Flash 0.924; Qwen3.8-27B 0.924 | Jev 0.879 | T6 to T8 | |
| WAInjectBench with reasoning judges | GLM-5.3-Flash 0.790 first | Jev fourth | T6 | |
| AUROC | Jev 0.797 / 0.963 / 0.938 | | WAInject / R-Judge / AgentHarm, T15 | |
| Calibration skill score | Jev +0.326 / +0.629 / +0.510; Decider -0.455 and Nimble -0.490 on R-Judge | | T16 | |
| Parent-model controls | Qwen3.5-2B-Base (Decider parent), Qwen3.5-9B (Nimble parent) included | | method | numbers not captured in my read |
| Trace security F1 (2609.34862) | Jev 77.8 (P 77.1, R 79.2), valid coverage 95.5% | GLM-5.2 74.1 (P 91.9, R 64.1); DS-V4-Flash 61.0; DS-V4-Pro 56.3 on 58.8% coverage; Qwen3-Next 49.4 | 5,219 traces over R-Judge, ATBench500, TraceSafe, MCPHunt | judge prompts and serving differ |
| Per benchmark F1, Jev vs GLM-5.2 | R-Judge 88.5 vs 93.4; ATBench500 93.8 vs 85.9; TraceSafe 67.8 vs 72.4; MCPHunt 61.1 vs 44.9 | | 2609.34862 | extraction also shows DS-V4-Pro 94.0 on R-Judge above the bolded GLM value; unverified |
| Long traces (more than 16 steps) F1 | Jev 57.5 | GLM 50.6 | 2609.34862 | |
| Latency and cost | Jev median 0.99 s, P95 2.02 s, $0.000195 per valid result | GLM-5.2 33.29 s, $0.014887; DS-V4-Flash 8.30 s, $0.001320 | 2609.34862 | estimated from list prices, not billed |

## Mechanism details you could implement
- Binary unsafe/safe decision; in 2609.34862 all judges share risk anchors and a score of 3 or more counts as unsafe.
- Local open-weight arms ran on CPU (Laya, float32), MPS (Decider, float16) and MLX (Nimble).

## Limitations, caveats, counter-evidence
- Authors: comparisons "remain sensitive to prompts, candidate order, context limits, reasoning settings, and service configurations"; several analyses added after the primary evaluation; benchmarks may overlap training data; hosted models can change.
- None of these are memory records; they are prompts and agent traces.
- R-Judge test is 108 items.

## Takeaways for tuning a memory stack
- For a memory injection gate, Jev is a reasonable cheap first pass but it misses (FNR 0.597 on injection text) far more than it false-blocks; pair it with a second check rather than trusting "not flagged".
- Do not pick an open-weight System One model from one benchmark: rank order flips across tasks, so evaluate on our own population.
- A small reasoning LLM (DeepSeek-V4.1-Flash, GLM-5.3-Flash) is the arm to beat on quality; Jev wins on latency and cost.

## Open questions
- How do these models do on planted instructions inside stored engineering memories (the H10 set)?
- Are Nimble and Decider's failures prompt-format issues that a local template fix would remove?
