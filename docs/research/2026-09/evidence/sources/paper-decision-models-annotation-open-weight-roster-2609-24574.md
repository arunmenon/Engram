---
schema_version: 1
artifact_id: N-SURVEY-20260928-11
artifact_type: note
producer: triage
run_id: survey-20260928T070101Z-8451
created_at: 2026-09-28T07:18:00Z
idempotency_key: note:survey:arxiv:2609.24574
input_refs: []
pillar_primary: R9
pillar_secondary: [R4, R6]
memory_stage: none
priority: 2
beliefs_affected:
  supports: [B14]
  contradicts: []
evidence:
  directness: 3
  control: 4
  independence: 5
  reproducibility: 4
  applicability: 2
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.24574
secondary_sources:
  - https://huggingface.co/convaiinnovations/laya
found_via: survey
claim_cluster: hosted-vs-open-weight-decision-models-head-to-head
---

# Evaluating Decision Models for Text Annotation in Computational Social Science (with Laya's own model card)

- **URL:** https://arxiv.org/abs/2609.24574 (HTML v2 read). Vendor card read for comparison: https://huggingface.co/convaiinnovations/laya
- **Type:** paper (independent evaluation) plus model card (vendor claim)
- **Author / org:** not stated in the extracted text
- **Date:** 2026-09-21 (v2)
- **Retrieved:** 2026-09-28
- **Cited by evidence:** survey run, R9 questions 1 and 2 (open-weight roster, head-to-head)
- **Relevance to a memory stack:** medium. Not memory tasks, but it is the only independent, pre-registered comparison found of Jev against eleven open-weight decision models and 19 LLMs under one protocol, with calibration and cascade cost.

## TL;DR
- Jev 1.13 trails the per-task best LLM on 14 of 15 evaluation tasks, median deficit 11.6 macro-F1 points, at a median 44 times lower measured cost (7,977 human-labelled items, 18 tasks).
- Calibration: Jev median ECE 0.157 [0.108, 0.233], better than the verbalised confidence of 16 of 19 LLMs, but three frontier models are better calibrated (Opus 5 0.066, Fable 5.1 0.073, Sonnet 5 0.075).
- Cascade: route low-confidence items to an LLM. With Gemini 3.8 Flash the cascade reaches 0.674 vs 0.678 for the LLM alone at 56% of its cost; with Gemma 4 31B, 0.638 vs 0.626 at 27% of cost (threshold 0.5).
- Confident failure: on empathy in peer-support dialogue, 78% of items get >= 0.9 confidence, with accuracy 0.383 against a 0.371 base rate: "confidence carries no information".
- Open-weight decision models mostly trail Jev on macro-F1 (only SemIf-4B at 0.550 is close to Jev's 0.581); the best open-weight LLM, Gemma 4 31B, beats Jev at 0.611.

## What it claims / describes
Mirrors Ziems et al. on 18 CSS classification tasks (10 utterance-level, 6 conversation-level, 2 document-level), using released test splits with human gold labels, zero-shot. Compares Jev 1.13 (via the OpenRouter decisions endpoint), an independent RLCD reimplementation on Qwen3-0.6B-Base, a no-training constrained-decoding ablation on the same base, 19 frontier and open-weight LLMs, and in Appendix B eleven open-weight decision systems released in the week after Jev.

## Numbers
Open-weight decision model roster as reported (Table 1 and 2, Appendix B; "not stated" where the paper excludes a system from the main grid):

| Model | Params | Base | Maintainer | Median macro-F1 | Median ECE | Hardware |
|---|---|---|---|---|---|---|
| Jev 1.13 (hosted) | not stated | not stated | TypeSafe | 0.581 | 0.157 | API |
| RLCD reimplementation | 0.6B | Qwen3-0.6B-Base | Anthony Maio | 0.361 | 0.128 | local HPC |
| No-training ablation | 0.6B | Qwen3-0.6B-Base | n/a | 0.278 | 0.144 | local HPC |
| Laya-0.4B | 0.4B | ModernBERT-large | NandhaKishorM (Convai Innovations) | not stated | 0.275 | local |
| Von-0.4B | 0.4B | ModernBERT-large | Victor Panisa | not stated | 0.301 | local |
| Verdict-0.15B | 0.15B | ModernBERT / GLiClass | Hemant Kumar | not stated | 0.086 | local |
| OpenDecision | not stated | not stated | Deepan Wadhwa | not stated | not stated | local |
| decider-0.8b | 0.8B | Qwen3.5-0.8B | Mark Marosi | not stated | 0.081 | local |
| decider-2b | 2B | Qwen3.5-2B | Mark Marosi | not stated | 0.134 | local |
| SemIf-4B | 4B | Qwen3.5-4B | Theodore Lee | 0.550 | 0.217 | local |
| Bespoke-Nimble-9B | 9B | Qwen3.5-9B | Bespoke Labs | not stated | 0.248 | local |
| Kev-0.8B / 4B / 9B | 0.8B / 4B / 9B | not stated | Jared Palmer | not stated | 0.153 / 0.171 / 0.173 | local |

A first extraction pass reported a macro-F1 range "from 0.217 (SemIf-4B)"; a second targeted read confirmed 0.217 is SemIf-4B's median ECE, not an F1, and SemIf-4B's median macro-F1 is 0.550. Aggregate macro-F1 for the other open-weight systems was not found in the accessible tables. The open-weight systems "were run 2026-09-20 to 2026-09-23". Latency: not stated for any model.

Vendor claim for comparison (Laya model card v0.3.20): 421M total parameters, Apache 2.0, typed-decisions accuracy 0.766 vs Jev 0.727, ECE 0.081 after temperature refitting ("Mean ECE 0.466 -> 0.081"), 32.8 to 39.5 ms on a Tesla T4, 193 to 464 ms on CPU. **Contradiction:** the independent paper measures Laya-0.4B median ECE 0.275 on human-labelled CSS tasks, more than three times the card's 0.081 (which was fitted and measured on the vendor's own typed-decisions set).

## Mechanism details you could implement
- Cascade with a confidence threshold between 0.5 and 0.9: coverage at 0.9 is a median 0.376 of items; thresholds must be fit per task.
- Per-task calibration check before trusting confidence: one task in 15 had near-chance accuracy at >= 0.9 confidence.

## Limitations, caveats, counter-evidence
- Social-science constructs, not engineering or memory decisions; applicability to our stages is low.
- Open-weight systems were added after pre-registration and cover 14 of 15 tasks (SemIf 13); their F1 is mostly not in the main grid.
- Licences of the eleven open-weight systems: not stated in the paper (Laya: Apache 2.0 per its card).

## Takeaways for tuning a memory stack
- Our standing open-weight roster (priority 2) now includes: Laya-0.4B, Von-0.4B, Verdict-0.15B, OpenDecision, decider-0.8b/2b, SemIf-4B, Bespoke-Nimble-9B, Kev-0.8B/4B/9B, plus the known Intern-Decision, this-that-model, CLM, Raya, RSI-Jev.
- The best-calibrated open-weight decision models here (decider-0.8b 0.081, Verdict-0.15B 0.086) are better calibrated than Jev (0.157) even where their accuracy is unknown. Calibration is a reason to test them at gate stages.
- Vendor-card calibration does not transfer: refit temperature on our own decisions (supports B14).
- A cascade is the default shape: System One first, LLM for low-confidence items, at a quarter to half of the LLM cost with equal accuracy.

## Open questions
- Per-model macro-F1 for the eleven open-weight systems (Appendix B full table) should be re-extracted by hand.
- Do the rankings hold on engineering decisions (link, supersede, stale)?
