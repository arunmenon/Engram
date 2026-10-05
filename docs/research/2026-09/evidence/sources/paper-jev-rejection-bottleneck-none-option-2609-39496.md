---
schema_version: 1
artifact_id: N-SURVEY-20261001-05
artifact_type: note
producer: triage
run_id: survey-20261001T054505Z-09ae
created_at: 2026-10-01T06:14:00Z
idempotency_key: note:survey:arxiv:2609.39496
input_refs: []
pillar_primary: R9
pillar_secondary: [R4, R2]
memory_stage: staleness
priority: 1
beliefs_affected:
  supports: [B11]
  contradicts: []
belief_effect_detail: "B11 says admission must allow empty. This shows that adding a 'none' option to a Choice question is not enough to get an empty answer when the decision needs arithmetic: correct rejection 7%. Per-candidate Boolean verification (99%) or a fitted threshold (79%) is needed."
evidence:
  directness: 4
  control: 4
  independence: 4
  reproducibility: 2
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.39496
found_via: survey
claim_cluster: jev-choice-none-option-rejection-failure-arithmetic
---

# When the Right Answer Is Missing: An Arithmetic-Dependent Rejection Bottleneck in Jev (arXiv 2609.39496)

- **URL:** https://arxiv.org/abs/2609.39496 (read: https://arxiv.org/html/2609.39496v1; local copy `out/log/raw/arxiv-2609.39496.html`)
- **Type:** paper (report)
- **Author / org:** Jike Zhong, Ming Li, Yuxiang Lai
- **Date:** 2026-09-30
- **Retrieved:** 2026-10-01
- **Cited by evidence:** survey run, R9 plan question 2 (decisions at the gate and linking stages). Bears directly on card PC-20261001-02 (pre-computing dates and version numbers for memory checks).
- **Relevance to a memory stack:** high for staleness and recall gates. "Is any of these stored facts still current given today's version / date?" with a "none" option is exactly the failing shape.

## TL;DR
- Jev picks the right numeric answer when it is present (99%) but, when it is absent, picks the "none" option only **7%** of the time, even with the explicit rejection option TypeSafe recommends. Label wording made no difference: "None" 99/7, "Other" 99/9, "None of the above" 99/6 (present/absent %).
- The same model, asked per candidate with native Boolean verification, rejects all three wrong candidates on **99%** of answer-absent cases. The failure is in the Choice interface, not in the model's ability to check.
- Rejection collapses at two operations: one operation 100/66, two operations 98/4 (50 paired cases). Magnitude matters even for one-digit vs two-digit sums: rejection 56% (1 to 9) vs 8% (10 to 99) with selection at 100%.
- It extends beyond bare sums: purchase totals 94/24; time calculation and capacity rounding (18/20 present vs 2/20 absent) and calendar arithmetic show gaps; state tracking, set intersection, rule chains and scheduling were perfect in both conditions.
- A threshold chosen on 20 development problems per task raised rejection from 7% to **79%** while answer-present accuracy went 99% to 97%, with no retraining or extra calls.
- Qwen3.5-9B with reasoning got 100/100 on arithmetic and purchase menus; slower and more tokens (cost not given).

## What it claims / describes
Paired problems: each answer-present menu has a twin where the correct value is removed and distractors at offsets {-2, +1, +3} remain, with a rejection option added. The model is the hosted Jev API (the reference list cites the "Jev 1.13 jaggedness" page, accessed 2026-09-25; exact version string not given). Controls show decomposition alone does not fix it, and supplying the computed result "largely restores rejection".

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Arithmetic menu, present / absent | 99% / 7% | | 100 paired problems (a+b-c) | |
| Rejection label "None" / "Other" / "None of the above" | 99/7, 99/9, 99/6 | | same | |
| Purchase totals (q*p+s) | 94% / 24% | | 100 pairs | |
| Boolean verification, answer-absent | 99% correct rejection of all 3 candidates | | same arithmetic cases | answer-present Boolean cell reported as 97% in the results table summary |
| Operation depth 1 / 2 | 100/66, 98/4 | | 50 pairs | |
| Magnitude 1 to 9 / 10 to 99 | selection 100/100, rejection 56% / 8% | | 100 fresh cases per band | |
| Capacity rounding | 18/20 vs 2/20 | | pilot, 20 pairs | small n |
| State tracking, set intersection, rule chains, scheduling | perfect both ways | | pilot, 20 pairs each | |
| Unit conversion / fraction comparison | 20/20 both; 20/20 vs 19/20 | | pilot | |
| Fitted threshold on rejection | 7% to 79% rejection; present 99% to 97% | | tau in {0, .01, ..., 1}, 20 dev problems per task, 100 test | |
| Qwen3.5-9B with reasoning | 100/100 arithmetic and purchase; lookup 99/94 | | same cases | 7 lookup errors from truncation; cost not stated |

## Mechanism details you could implement
- Do not rely on a Choice question with a "none" option to reject when the decision depends on computation (date differences, version ordering, counts, rounding). Ask per candidate with a Boolean question instead, or compute the value outside the model and put it in the state.
- If Choice-with-none must be used, fit a threshold on the top option's probability using a small labelled development set (20 per task sufficed here) and treat "below threshold" as none.

## Limitations, caveats, counter-evidence
- Hosted API only; no weights or activations; no code URL found.
- Arithmetic and near-arithmetic tasks; text-only memory decisions (is this note about the same requirement?) are not tested, and symbolic tasks passed.
- Pilot families have 20 pairs each.
- No page content addressed instructions to an AI agent.

## Takeaways for tuning a memory stack
- Staleness and recall gates over memories often involve dates and versions ("superseded after v2.3?", "older than the last deploy?"). Pre-compute those comparisons (as PC-20261001-02 proposes) or use per-memory Boolean questions; this paper is direct evidence that the Choice-with-none shape fails there.
- This is the admission side of B11: a gate that must be able to return nothing needs a Boolean or thresholded design, not a "none" option.

## Open questions
- Does the same gap appear for non-numeric absence ("none of these memories is about this requirement")? Not tested.
- Do open-weight decision models (Laya, Bongard, decider-2b) show the same Choice-with-none failure?
