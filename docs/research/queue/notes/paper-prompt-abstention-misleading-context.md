---
schema_version: 1
artifact_id: N-SURVEY-20261003-04
artifact_type: note
producer: triage
run_id: survey-20261003T054505Z-3590
created_at: 2026-10-03T06:00:00Z
idempotency_key: note:survey:arxiv:2608.22228
input_refs: []
pillar_primary: R4
pillar_secondary: [R8, R3]
memory_stage: reranking
beliefs_affected:
  supports: [B11]
  contradicts: []
evidence: {directness: high, control: high, independence: high, reproducibility: medium, applicability: medium}
source_url: https://arxiv.org/abs/2608.22228
found_via: survey
---

# Prompt-Based Abstention Fails Under Misleading Context: A Controlled Study of Small Frozen RAG Models

- **URL:** https://arxiv.org/abs/2608.22228 (HTML v1 read; local copy out/log/raw/2608.22228.html)
- **Type:** paper
- **Author / org:** Yohanes Andre Setiawan, Georgia Institute of Technology
- **Date:** 2026-08-23
- **Retrieved:** 2026-10-03
- **Cited by evidence:** survey run, B11 / H5, H10
- **Relevance to a memory stack:** high for the admission decision. Shows that "answer only if the context suffices" works on empty context and fails on one planted wrong passage, and what external checks cost in coverage.

## TL;DR
- Three frozen small models (Phi-4-mini 3.8B, Llama-3.1-8B, Qwen2.5-7B, Q4_K_M), NQ and HotpotQA, 500 questions each, five passages per question.
- With all-wrong context (Q0) prompted abstention works: answer rate 1% or below for P1 to P4.
- With one entity-swapped gold passage among five (QC, n=532), the explicit abstain rule (P1) still answers 41.6% (macro); per cell 13.6% to 74.3%. Llama on NQ under P0: 3.0% at Q0 to 82.7% at QC.
- Of 2,350 answered QC rows, 59.6% echo the planted entity, 36.2% hallucinate, 4.3% override correctly.
- External checks (closed-book agreement P3, NLI P4) cut QC answering to 13.3% / 14.0% but falsely abstain on 49.8% / 31.0% of questions they answered correctly with gold context.

## What it claims / describes
Arms: P0 answer from context; P1 explicit abstain rule; P2 chain-of-thought sufficiency check; P3 two-pass closed-book agreement (accept if F1 >= 0.8, abstain on conflict); P4 as P3 but DeBERTa-v3-large NLI contradiction check across passages. JSON output with confidence 0 to 100, GBNF-forced.

## Numbers
| Arm | Answer rate when should abstain (QC) | False abstention @Q100 | Answer rate @Q100 | False abstention @Q50 |
|---|---|---|---|---|
| P0 | 58.2% | 0.2% | 91.7% | 2.2% |
| P1 | 41.6% | 0.0% (by construction) | 79.3% | 8.7% |
| P2 | 37.8% | 5.3% | 78.5% | 11.5% |
| P3 | 13.3% | 49.8% | 33.4% | 55.7% |
| P4 | 14.0% | 31.0% | 54.7% | 51.4% |

AURC: P1 0.434, P3 0.451, P4 0.452 (external checks do not improve the risk-coverage area). Paired bootstrap 10k; all 30 Q0-to-QC deltas positive. Swap audit: 26/200 swaps broken (13%).

Text vs table: abstract says 63% echo, Table 3 says 59.6%; intro says "only 4%" correct, table 4.3%; limitations cite "41 to 74 pp gaps" that are answer rates, not gaps.

## Mechanism details you could implement
- Test admission with three context conditions, not one: all-wrong, degraded (3 gold + 2 hard negatives), and misleading (one entity-swapped gold among negatives).
- NLI contradiction check against a closed-book answer fails when the model's memory and the planted passage agree (Llama NQ: zero correct QC answers).

## Limitations, caveats, counter-evidence
- Small quantised models only; no larger model, no trained gate, no standalone confidence threshold arm. Code "will be made available".
- QC-eligible questions are easier (selection bias noted by the author).

## Takeaways for tuning a memory stack
- Supports B11: the ranker or answerer cannot be trusted to abstain on misleading retrieved memory; admission must be a separate, separately measured decision. Empty-context tests overstate abstention quality.
- A cheap external check buys refusal at a steep coverage cost; AURC is flat. For build-time memory a wrong admitted item is costly, so the trade may still be right, but it must be measured on our own misleading-memory cases (stale decisions are the PDLC analogue of an entity swap, inference).

## Open questions
- Does a typed decision model (Jev Noul `quote_supports_item`) do better than NLI on the misleading condition?
