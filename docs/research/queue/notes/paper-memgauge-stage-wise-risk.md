---
schema_version: 1
artifact_id: N-SURVEY-20261009-05
artifact_type: note
producer: triage
run_id: survey-20261009T054505Z-36b1
created_at: 2026-10-09T05:51:28Z
idempotency_key: note:survey:arxiv:2608.30177
input_refs: []
pillar_primary: R8
pillar_secondary: [R2, R6]
memory_stage: write, consolidation, retrieval
beliefs_affected:
  supports: [B24]
  contradicts: []
evidence: {directness: 4, control: 4, independence: 4, reproducibility: 1, applicability: 3}
source_url: https://arxiv.org/abs/2608.30177
found_via: survey
---

# Understanding Stage-Wise Utility-Risk Trade-offs in LLM Agent Memory (MemGauge)

- **URL:** https://arxiv.org/abs/2608.30177 (HTML v1 read)
- **Type:** paper
- **Author / org:** Chuanchao Zang, Zijian Cao, Xiangtao Meng, Jianing Wang, Wenyu Chen, Xinyu Gao, Li Wang, Zheng Li, Shanqing Guo (Shandong University)
- **Date:** 2026-08-31
- **Retrieved:** 2026-10-09 (local copy: out/log/raw/2608.30177.html)
- **Cited by evidence:** top-down survey, R8 question on where to put the gate
- **Relevance to a memory stack:** high. It is the only source on the bus that varies write admission, management and retrieval exposure one at a time under matched clean and poisoned conditions, and audits Mem0, Hindsight, LangMem and A-MEM.

## TL;DR
- Writing: risk is threshold-like. Above admission coverage ~0.5, attack success "rises rapidly to 37%-64%" while clean utility keeps rising.
- Management (conflict resolution, quarantine) is where risk decouples from utility: clean utility moves 3 to 5 points across policies while attack success moves up to 62 points.
- Retrieval: utility and risk rise together with exposure; ranking by relevance does not separate them.
- On four shipped systems, turning management on cut attack success by 10.6 to 24.8 points at -3.9 to +0.8 points clean utility.

## What it claims / describes
Controllable pipeline with three knobs: write admission coverage theta_w, management policy (UM unmanaged, PQ provenance-aware quarantine, NC numeric-conflict resolution, SC strict conflict resolution), retrieval exposure theta_r. Defaults theta_w=0.6, UM, theta_r=0.8, K=5, |B|=100. Poisoning through interaction (MINJA user-side, Sleeper tool-side). 11 LLMs (GPT-5.4, GPT-5.4-Mini, Gemini 3.1 Flash, Gemini 2.5 Flash, Grok 4.3 High, Grok 4.2 Fast, DeepSeek-V4-Flash, GLM-5.1, Qwen 3.5 397B, MiniMax-M3, Doubao Seed 2.0 Pro). LongMemEval 100 + LoCoMo 100 questions. Judge: AgentEvals, 91% agreement with 200 human-labelled trajectories (kappa 0.78 among annotators); judge model identity not stated.

## Numbers
Audit of existing systems (WR = writing retention %, M0 management off, M1 on):

| System | WR | Mode | Clean U | Poisoned U | ASR |
|---|---|---|---|---|---|
| Mem0 | 36.5 | M0 / M1 | 0.533 / 0.541 | 0.213 / 0.343 | 0.326 / 0.176 |
| Hindsight | 69.4 | M0 / M1 | 0.563 / 0.524 | 0.165 / 0.240 | 0.475 / 0.293 |
| LangMem | 74.5 | M0 / M1 | 0.528 / 0.523 | 0.158 / 0.325 | 0.473 / 0.225 |
| A-MEM | 55.7 | M0 / M1 | 0.483 / 0.460 | 0.130 / 0.218 | 0.403 / 0.297 |

| Controlled result | Value |
|---|---|
| theta_w > 0.5 | ASR 37% to 64%; poisoned utility 3% to 34% |
| theta_w < 0.3 | clean utility ~15 to 20%, ASR near 0 |
| PQ (provenance quarantine) | Sleeper ASR near zero; little protection against MINJA |
| SC (strict conflict) | reduces ASR on both attacks |
| Retrieval K=1 to 7 | clean utility 24.6-29.3% to 52.7-64.2%; ASR 4.7-12.2% to 36.1-53.7% |
| Ranker at theta_w=0.5 | self or external LLM ranker: clean 43-47%, ASR 2-8%; chronological: clean 33%, ASR 27% |

Figure and table numbers for the controlled results were not recovered; values are from the text.

## Mechanism details you could implement
- Put the decisive control at management (conflict resolution against existing memory), not at retrieval ranking.
- Provenance quarantine only catches attacks whose provenance is distinguishable (tool-side), not user-side conversational poisoning.

## Limitations, caveats, counter-evidence
- Audit of shipped systems is "diagnostic associations rather than controlled stage effects".
- n=100 per benchmark, no CIs in the extract; interaction-based poisoning only; no code link found.
- Personal-assistant QA, not engineering work.

## Takeaways for tuning a memory stack
- Agrees with PC-SURVEY-20260928-01 (where a defense sits predicts its benign cost) and adds a stage map: management is the cheap place to cut risk.
- A provenance-only gate (H10 style) will miss user-side poisoning; pair it with conflict checking against existing Decisions.

## Open questions
- Does strict conflict resolution hurt legitimate requirement changes (the R2 supersession case)? Not measured.
