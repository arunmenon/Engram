---
schema_version: 1
artifact_id: N-SURVEY-20261005-04
artifact_type: note
producer: triage
run_id: survey-20261005T054504Z-d350
created_at: 2026-10-05T06:30:00Z
idempotency_key: note:survey:arxiv:2605.18930
input_refs: []
pillar_primary: R5
pillar_secondary: [R8]
memory_stage: consolidation
beliefs_affected:
  supports: [B17, B18]
  contradicts: []
evidence:
  directness: 4
  control: 4
  independence: 3
  reproducibility: 2
  applicability: 2
evidence_scale: 1 (weak) to 5 (strong), per dimension
source_url: https://arxiv.org/abs/2605.18930
found_via: survey
---

# OEP: Poisoning Self-Evolving LLM Agents via Locally Correct but Non-Transferable Experiences

- **URL:** https://arxiv.org/abs/2605.18930 (read via https://arxiv.org/html/2605.18930v1)
- **Type:** paper
- **Author / org:** not stated in the extracted text
- **Date:** May 2026 (v1)
- **Retrieved:** 2026-10-05
- **Cited by evidence:** survey query for B17/B18 (harmful reinforcement)
- **Relevance to a memory stack:** high for R5. It shows that an agent's own reflection step turns correct-looking cases into harmful general rules, and that an LLM auditor does not stop it.

## TL;DR
- A user-level attacker submits 10 conversational cases per domain (8 contrastive failure trajectories + 2 positive) that are each locally correct. The agent's reflection distils them into over-general rules; the harm is "self-inflicted".
- On GPT-4o with reflection memory, Math accuracy goes 91.43 (self-evolving, clean) to 40.29 (OEP); MedQA 87.14 to 42.86; with GPT-5.4 OpenClaw, Math 98.86 to 28.57.
- An LLM auditor that cuts other memory attacks to 3 to 15% ASR leaves OEP at 40.29% ASR (from 59.14%).
- Harm persists: Tool-domain ASR about 72% after 50 later benign queries.
- More capable models are more susceptible: GPT-4o ASR 59.14 vs GPT-4o-mini 30.57 (Math).

## What it claims / describes
Threat model: black-box, user-level access only; no access to system prompt, weights, memory DB or tools. Three mechanisms exploited: "provenance-weighted trust" (agents trust their own reflections more than external input), "perspective confinement" (local success overestimated), "risk-sensitive rule induction" (severe hypothetical consequences overweighted). Systems attacked: a simple reflection-memory agent, a LangChain memory framework, OpenClaw (skill-based self-evolving agent). Temperature 0.0, three trials, std within 2%.

## Numbers

| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| GPT-4o agent Math / Med / Tool ACC | OEP 40.29 / 42.86 / 86.84 | no memory 82.57 / 84.29 / 93.86; clean self-evolving 91.43 / 87.14 / 98.25 | GSM8K 350, MedQA 350, ToolAlpaca 114 | |
| LangChain Math / Med / Tool ACC | OEP 38.57 / 44.86 / 87.72 | clean S-Evo 92.86 / 85.71 / 99.12 | | |
| GPT-5.4 OpenClaw Math / Med / Tool ACC | OEP 28.57 / 69.43 / 96.49 | clean S-Evo 98.86 / 93.14 / 100.0 | | |
| Experience Success Rate (rule stored), GPT-4o Math / Med / Tool | 77.43 / 68.29 / 85.09 | | ESR = non-transferable rule distilled into memory | |
| ASR (rule retrieved and causes failure), GPT-4o | 59.14 / 52.00 / 71.93 | | | |
| ASR vs other attacks, no defence / LLM auditor | OEP 59.14 / 40.29; MINJA 68.86 / 14.86; AgentPoison 46.29 / 5.71; MemoryGraft 52.57 / 5.43 | | Table 4 | |
| proposed defences ASR Math / Med / Tool | Auto Search 37.43 / 27.43 / 46.49; MAS Debate 28.86 / 21.43 / 30.70 | no defence 59.14 / 52.00 / 71.93 | | |
| ablation: QA only / QA-solution / full triplet ESR (Math) | 12.29 / 19.43 / 77.43 | | | consequence framing drives it |
| reflection ablation ASR: distilled experience vs direct cases | 59.14 vs 42.57 (Math); 52.00 vs 27.14 (Med); 71.93 vs 64.91 (Tool) | | Table 6 | |
| persistence (approx., from figure) | after 10 / 20 / 50 queries: Tool ~85 / ~82 / ~72 % | | | read off a figure |
| adversarial ratio | minimal at 20%, sharp surge at 50%, peak at 100% | | | |

Judges: three LLM auditors (GPT-4o, Gemini-2.5-Flash, Qwen3-Max), std at most 1.82; GPT-4o is also an agent backbone, so judge and system share a model in that arm.

## Mechanism details you could implement
- Measure two separate rates: ESR (wrong rule written) and ASR (wrong rule retrieved and causes harm). This is a ready template for H4's feedback-loop rate.
- Reflection ablation: storing direct cases instead of distilled rules lowers ASR (Med 52.00 to 27.14), a data point for raw-over-distilled under adversarial input.
- Defence that helped most: multi-agent debate before committing a rule (ASR roughly halved), not a single LLM auditor.

## Limitations, caveats, counter-evidence
- No coding domain; tool use is API calls. Applicability to build-time engineering is inferred.
- Attacker-supplied cases, not organic drift; still, the harmful step is the agent's own consolidation.
- Does not measure how a poisoned rule's utility or priority grows over iterations; "Not explicitly measured", only modelled (App. E.5). B17 stays true: no reinforcement rate reported.
- No public code.

## Takeaways for tuning a memory stack
- Supports B18 in the stronger direction: outcome-style reflection can install harmful rules from correct-looking evidence, and capable models are more exposed.
- Supports B17: even this paper reports persistence, not a reinforcement rate.
- Gate rule induction separately from case storage; require cross-context support before promoting a case to a rule.

## Open questions
- Would provenance tagging (source_class from P5) on the cases cut ESR, given that "provenance-weighted trust" is one of the exploited mechanisms?
