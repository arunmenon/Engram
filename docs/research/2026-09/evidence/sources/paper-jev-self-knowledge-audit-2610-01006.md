---
schema_version: 1
artifact_id: N-SURVEY-20261004-05
artifact_type: note
producer: triage
run_id: survey-20261004T054506Z-478e
created_at: 2026-10-04T05:55:25Z
idempotency_key: note:survey:arxiv:2610.01006
input_refs: []
pillar_primary: R9
pillar_secondary: [R4, R2]
memory_stage: staleness
priority: 1
related_notes: [N-20260929-04, N-20260928-34]
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: medium (whether Jev's confidence signals missing knowledge, outdated knowledge or incomplete evidence; not tested on stored memories)
  control: high (about 575,000 calls, controlled pairs such as settled vs future, complete vs incomplete evidence, real vs made-up entities; option-code ablations; cross-fitted recalibration)
  independence: high (Synthpop.AI, no Jev affiliation)
  reproducibility: medium (code at github.com/Syntheme/beyond-answer-confidence, not pinned; hosted model can change)
  applicability: medium (the recall gate and staleness check use exactly this kind of confidence; questions are world knowledge, not project memory)
source_url: https://arxiv.org/abs/2610.01006
found_via: survey
---

# Beyond Answer Confidence: A Controlled Audit of Self-Knowledge in a Black-Box Decision Model (arXiv 2610.01006)

- **URL:** https://arxiv.org/abs/2610.01006 (HTML v1 read)
- **Type:** paper
- **Author / org:** Sharath M Shankaranarayana, Davor Runje, Jan Jannink (Synthpop.AI)
- **Date:** 2026-10-01
- **Retrieved:** 2026-10-04 (local copy: `out/log/raw/arxiv-2610.01006.html`)
- **Cited by evidence:** survey question R9-4 (does a System One model know when it does not know?)
- **Relevance to a memory stack:** high for the staleness and recall-gate stages. It shows which "do I know this / is this still true" signals from Jev can be trusted, and which cannot.

## TL;DR

- "On familiar, in-scope closed-choice questions like those tested, Jev's confidence can be used for abstention; a single call's aggregate calibration is close to that of three."
- Confidence does **not** detect outdated knowledge. On news after vs before the model's knowledge boundary, answer uncertainty separates the two at AUROC "0.385 (0.615 reversed)". An explicit `known` question reaches 0.91, but only because of dates: "explicit dates: date alone 0.997".
- Jev is confidently wrong when it has no information: "for a fair die it puts 0.80 on 'one' in every option order". The paper's own heading: "Jev does not play dice: 83% probability, 19% accuracy on a hidden fair die roll".
- Advice from the paper: add `settled` and `enough` questions where outcomes may be undetermined or the context incomplete. "do not rely on `known` to detect gaps in the model's memory". "give the current date when asking whether an outcome is settled, and state that retrieved context may be irrelevant".
- A "not known" option helps only when such questions are common: "it answers few such questions (about 7% past the boundary), is inconclusive at our panel's mix and costs accuracy when they are rare, and a simple rule that skips questions with the most recent dates comes within 0.01 to 0.02 of it".

## What it claims / describes

The audit covers Jev 1.13.0, queried 26 to 30 September 2026 in about 575,000 calls. It compares two signals: answer confidence (p_max), and explicit questions about knowledge state (`settled`, `enough`, `known`). These are tested over controlled pairs: settled vs future chance events, complete vs incomplete evidence, pseudo-word or look-alike made-up entities vs obscure real ones, and news before vs after the inferred knowledge boundary (change point 2024-11 on Daily Oracle). A second line of tests ablates what the option code carries, from nothing up to a name plus 8 examples, and also swaps the examples between options. Comparators are GLiNER2.5-Decide and a 5-member MiniLM ensemble (from the reader extract).

## Numbers

| Contrast | Answer-uncertainty AUROC | Explicit-question AUROC | Source check |
|---|---|---|---|
| Settled vs future chance | .96 | 1.00 | reader extract |
| Complete vs incomplete evidence | .85 | .95 (`enough`) | reader extract |
| Pseudo-word made-up vs obscure real entity | .78 | .88 | reader extract |
| Look-alike made-up vs obscure real | .76 | .74 | reader extract |
| News after vs before boundary | 0.385 (0.615 reversed) | 0.91 (`known`); date alone 0.997 | verified in Table 1 |
| Same, dates removed | .56 | .58 | reader extract |

| Other result | Value | Source check |
|---|---|---|
| Fair die, all 720 option orders | 0.80 on "one" (ideal .17) | verified |
| Option codes swapped with another option's examples | accuracy .001, ECE .904, p_max .932 (Banking77) | reader extract |
| 8 examples per option code | Banking77 acc .899, smECE .037; CLINC150 .979 / .016 | reader extract |
| Confident band after the boundary | accuracy 0.571 at p_max 0.9 to 1.0, vs 0.880 before | reader extract |
| Confident errors with a "not known" option, after the boundary | 0.1% (vs 17.3% base), coverage 6.6% | reader extract |
| Recalibration transfer | value-wise maps .066 in-sample to .170 cross-fitted | reader extract |
| Abstention on TriviaQA at p_max >= 0.9 | keeps 8,132 of 9,960 items with 20 errors | reader extract |

Judge: an AI assistant was the sole annotator for 240 date-masked news pairs in an exploratory analysis, with human checking "pending". Whether it shares a model with Jev is not stated, and it is not used for the headline results. Cost: Jev at USD 0.042 per million input tokens; total spend not stated.

## Mechanism details you could implement

- **For a staleness check:** do not ask the model whether it knows. Pass the memory's `recorded_at` and today's date, and ask a `settled` question ("has this been decided / is this still the case as of DATE?").
- **For a recall gate:** add an `enough` question ("does the retrieved context contain enough to answer?") and tell the model that retrieved context may be irrelevant.
- **Option design:** give each option a few examples. A bare name or opaque code is unsafe, and swapped examples are followed blindly with high confidence.
- **Thresholds:** set them per question wording on held-out data. Do not reuse a recalibration map across tasks.

## Limitations, caveats, counter-evidence

- One version of one closed model. The authors call the surface-cue controls exploratory. The knowledge boundary is an inferred accuracy change point, not a verified cutoff. Most benchmarks were converted to multiple choice.
- The tests use world knowledge, not project memory. Our staleness question is whether a stored fact about our code is still true, and that is decided against fresh evidence rather than the model's internal knowledge (inference). The transferable lesson is about which question wordings carry signal.

## Takeaways for tuning a memory stack

- At the staleness stage, a typed decision model has to be given the dates and the newer evidence. Its own confidence will not flag outdated content and can be inverted.
- At the recall gate, ask about evidence sufficiency explicitly. Answer confidence alone is a weaker signal (.85 vs .95 on complete vs incomplete evidence).
- Expect confident wrong answers when the input carries no information. Every gate needs a "none / not enough" option and a held-out threshold. This agrees with N-SURVEY-20261004-03.

## Open questions

- Does the `settled` wording, given both dates and the newer evidence, detect superseded design decisions in our graph better than an embedding-similarity staleness rule?
