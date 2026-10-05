---
schema_version: 1
artifact_id: N-SURVEY-20260928-10
artifact_type: note
producer: triage
run_id: survey-20260928T070101Z-8451
created_at: 2026-09-28T07:14:00Z
idempotency_key: note:survey:arxiv:2609.26758
input_refs: []
pillar_primary: R9
pillar_secondary: [R4]
memory_stage: write_gate
priority: 1
beliefs_affected:
  supports: [B14]
  contradicts: []
evidence:
  directness: 5
  control: 5
  independence: 4
  reproducibility: 3
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.26758
found_via: survey
claim_cluster: option-name-polarity-overrides-rubric
---

# Type-Safe Is Not Error-Free: A Constrained Decision Head Follows the Option Name, Not the Rubric Bound to It

- **URL:** https://arxiv.org/abs/2609.26758 (HTML v2 read at https://arxiv.org/html/2609.26758)
- **Type:** paper
- **Author / org:** not stated in the extracted text
- **Date:** 2026-09-22 (v2)
- **Retrieved:** 2026-09-28
- **Cited by evidence:** survey run, R9 question 3 (failure modes)
- **Relevance to a memory stack:** high. Our planned write gate (H5: Noul `quote_supports_item`, Choice `source_type`) and staleness audit (H10) are yes/no style decisions with rubrics. This paper shows the option names, not the rubric text, drive the answer.

## TL;DR
- Swapping which option name is bound to which rubric, with everything else identical, flips 76.92% of answers when the names are yes/no, versus 6.50% (0/1) and 6.00% (A/B) neutral controls. "70.4 pp higher than for the 0/1 control (95% CI [67.6, 73.1])".
- AUC goes from 93.8% (aligned) to 23.2% (reassigned) with yes/no names: a systematic reversal, not noise.
- The hosted model (Jev) shows it too: AUC ".8146 to .5806" and 24x its test-retest floor (at most 1.33% flips between two identical runs).
- Random character strings as option names return every model to the neutral regime "without reducing accuracy".
- Type-error rate stays 0% throughout: schema conformance says nothing about whether the rubric was followed.

## What it claims / describes
Each option has a name and a textual rubric. The authors keep the question, state, rubric wording and the set of names fixed, and change only which name is attached to which rubric. If a model reads the rubric, the answer should follow the rubric; if it reads the name, it flips. Models: hosted Jev; Laya (Convai Innovations, ModernBERT-large); Open-Jev (com-kotobalabs, DeBERTa-v3-large). Data: 1200 binary questions from the Typed Decisions set (LocalLLaMA), four tasks of 300 each: invoice reconciliation, agent-trace triage, security-alert classification, customer-service escalation. Four predicates; the effect is at least 7.4x the neutral control on every predicate and grows with the number of options.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Flip rate, yes/no names reassigned | 76.92% | 0/1: 6.50%; A/B: 6.00% | 1200 binary workflow decisions | Table 1, open-weight model reported in table |
| AUC aligned vs reassigned, yes/no | 93.8% vs 23.2% | 0/1: 94.2% vs 92.4%; A/B: 94.2% vs 94.1% | same | |
| Excess flip, yes/no over 0/1 | 70.4 pp [67.6, 73.1] | | | |
| Hosted Jev AUC under swap | .8146 -> .5806 | test-retest floor <= 1.33% flips | | |
| Mean-pooling read-out family | flips 4.1x less often | last-token/marker read-out | | architecture dependence |
| Random-string names, Laya | 6.9% flips | 0/1 and A/B within 3.2 pp (7.9%) | | no accuracy loss |
| Laya, 3 to 16 options, neutral letters | changes 52.4% of decisions; accuracy 56.4% -> 27.8%; numbers change 55.8% | | 683 questions | multi-option instability even with neutral names |
| Recommended naming on Laya | 6.5% flips | 76.9% with yes/no | | |
| Type-error rate | 0% | | all conditions | |

## Mechanism details you could implement
- Recommended practice, quoted: "Use neutral option names and carry the meaning in the definitions."
- Test for the failure cheaply: for each binary decision template, run a swapped-binding copy; if answers track the name, the template is unsafe.
- For many-option Choice decisions (for example our `source_type` or edge-type choice), expect large instability even with neutral names on Laya; prefer several binary decisions or a hierarchical choice (inference).

## Limitations, caveats, counter-evidence
- Data are generic workflow decisions, not memory decisions.
- The swapped-binding condition is deliberately adversarial to the name's meaning; in normal use the names agree with the rubrics. The practical risk is rubrics that contradict or refine the natural meaning of the name (for example "yes = the quote does NOT support the item"), and many-option choices.
- Licence and release of the benchmark code: not stated in the extracted text.

## Takeaways for tuning a memory stack
- When we write Noul or Choice templates for write gating, linking and staleness, name options neutrally (A/B or random strings) and put all meaning in the rubric, or keep names and rubrics strictly aligned with natural polarity. Audit every template with a swapped-binding run.
- Do not use the 0% type-error rate as a quality signal.
- Edge-type choice among many PDLC link types (implements, verifies, refines, satisfies, blocks) on Laya-class models is likely unstable; test before relying on it.

## Open questions
- Does the effect appear on Jev when rubrics are long and domain-specific, as ours will be?
- Is there a read-out (mean pooling) open-weight model we could host that is less sensitive?
