---
schema_version: 1
artifact_id: N-SURVEY-20260928-02
artifact_type: note
producer: triage
run_id: survey-20260928T055608Z-7419
created_at: 2026-09-28T06:25:00Z
idempotency_key: note:survey:arxiv:2607.27080
input_refs: []
pillar_primary: R8
pillar_secondary: [R7]
beliefs_affected:
  supports: [B24]
  contradicts: []
evidence:
  directness: high (same malicious semantics traced through write, recall, adoption, action and selective repair)
  control: medium-high (matched backend comparisons fix task package, harness, LLM, runtime and clean initialisation; descriptive, no ablation of backend internals)
  independence: medium (academic; judge DeepSeek-V4-Pro is also one of the three evaluated LLM backends)
  reproducibility: low-medium (no code or data URL found in the paper)
  applicability: medium (113/310 cases are code-and-science contexts, harnesses are OpenClaw and Hermes, not results split by domain)
source_url: https://arxiv.org/abs/2607.27080
found_via: survey
---

# MemSecBench: Tracking Agent Memory Poisoning from Persistence to Consequence and Repair

- **URL:** https://arxiv.org/abs/2607.27080 (HTML full text read at https://arxiv.org/html/2607.27080)
- **Type:** paper (benchmark)
- **Author / org:** not captured in the fields read
- **Date:** July 2026 (v1)
- **Retrieved:** 2026-09-28 (local copy: out/log/h-2607.27080.html)
- **Cited by evidence:** top-down survey, R8 questions 1, 2 and 4
- **Relevance to a memory stack:** high, first benchmark found that swaps memory backends under a fixed harness and measures both poisoning and selective repair

## TL;DR
- 310 cases from 48 contexts (code and science 113, daily life 107, office 90), each run under a Write-Execute-Forget protocol with seven checkpoints, on a 2 harness x 4 backend x 3 LLM matrix (24 configurations).
- Across all 24 configurations malicious memory persists in 84.2 % of cases and the full Write-Execute chain succeeds in 50.3 %.
- Selective repair: removing the target succeeds in 86.3 % of poisoned cases but benign memory is preserved in only 62.5 %; both together (SRSR) 56.1 %. Collateral damage, not failure to delete, is the main repair failure.
- "No memory backend is uniformly safer": Mem0 cuts E2E-ASR under OpenClaw by 4.2 to 13.5 pp but raises it under Hermes/MiniMax-M3 from 34.8 % to 48.7 %.
- Attack resistance and recoverability are separate properties (A-MEM: E2E-ASR 59.0 % to 56.5 %, SRSR 46.3 % to 87.6 % under OpenClaw/DeepSeek-V4-Pro).

## What it claims / describes
Configuration Pi = (H, B, L): harness (OpenClaw, Hermes), memory stack B including its harness adapter and storage settings (Native, Mem0, Mem0-Graph, A-MEM), served LLM (DeepSeek-V4-Pro, MiniMax-M3, GPT-5.5). Checkpoints: W1 write operation, W2 persistence, E1 recall, E2 adoption, E3 externalisation, F1 repair (target removed), F2 benign preservation. Adjudication combines a deterministic write check, checkpoint-specific judge evaluations (judge DeepSeek-V4-Pro, "outside the agent run", rubric may cite only evidence ids admissible for that checkpoint), and programmatic gates for admissibility, timing and completeness. Threat model assumes attacker content reaches the agent through a supported carrier and that Write invokes the intended memory interface; account or session compromise is out of scope. Case authoring model is distinct from evaluated backends and the judge.

## Numbers
| Metric | Value | Setup | Caveat |
|---|---|---|---|
| Malicious persistence (MPSR) | 84.2 % | macro over 24 configs | |
| Recall E1 / adoption E2 | 76.1 % to 53.7 % | lifecycle funnel | adoption is the main drop |
| End-to-end attack success (E2E-ASR) | 50.3 % | macro over 24 configs | |
| Repair F1 (target removed) | 86.3 % | of successfully poisoned cases | |
| Benign preservation F2 | 62.5 % | same | 30.2 pp gap to F1 |
| Selective repair success (SRSR) | 56.1 % | F1 and F2 | |
| Mem0 vs Native, OpenClaw | E2E-ASR -4.2 to -13.5 pp; SRSR -1.5 to -11.3 pp (direction as stated in text) | across 3 LLMs | |
| Mem0 vs Native, Hermes/MiniMax-M3 | E2E-ASR 34.8 % to 48.7 %; SRSR 47.3 % to 60.0 % | | backend effect flips sign by harness |
| A-MEM vs Native, OpenClaw/DeepSeek-V4-Pro | E2E-ASR 59.0 % to 56.5 %; SRSR 46.3 % to 87.6 % | | |
| Mem0-Graph vs Native, OpenClaw/GPT-5.5 | E2E-ASR 57.1 % to 41.0 %; SRSR 87.5 % to 86.7 % | | |
| Judge vs humans | 453/500 (90.60 %) and 459/500 (91.80 %) | stratified 500-run sample, two annotators | accuracy is the only validation metric |

Per-configuration table values beyond those quoted in the text were not verified cell by cell and are omitted.

## Mechanism details you could implement
- Lifecycle checkpoints W1/W2/E1/E2/E3/F1/F2 as a test schema for any memory gate or suppression feature: score persistence, recall, adoption, action, removal and benign preservation separately.
- Repair must be scored with a benign-preservation check; deleting the poisoned item plus neighbours looks like success on F1 alone.

## Limitations, caveats, counter-evidence
- Judge DeepSeek-V4-Pro is also one of the three evaluated LLM backends, so 8 of 24 configurations are judged by their own model (the paper does not discuss this).
- No defenses evaluated; no false-positive costs.
- No code or data URL found.
- Results descriptive, not causal; no ablation of backend components; no code-only stratification.

## Takeaways for tuning a memory stack
- Supports B24: stored memory must be treated as untrusted; half of poisoned writes reach a real action.
- For Engram's "flags never delete" rule (H10): suppression rather than deletion is consistent with this finding that deletion-style repair destroys benign memory in 37.5 % of poisoned cases (inference: suppression may preserve benign items better, untested here).
- A swap test (B22, P0 step 5) should include security behaviour: backend swaps change attack success by up to 14 pp in either direction under the same harness and model.

## Open questions
- Does suppression-with-provenance (mark and exclude, keep bytes) beat deletion on F2?
- Code-context results in isolation.
