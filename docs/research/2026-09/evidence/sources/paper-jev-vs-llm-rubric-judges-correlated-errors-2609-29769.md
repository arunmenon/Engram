---
schema_version: 1
artifact_id: N-20260928-03
artifact_type: note
producer: triage
run_id: triage-20260928T014503Z-edff
created_at: 2026-09-28T01:55:04Z
input_refs: [{"artifact_id": "post:2103818961309888616", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.29769
claim_cluster: arxiv:2609.29769
feeds: ["decision", "memory"]
primary_source: https://arxiv.org/abs/2609.29769
source_commit: n/a
strength: paper-ablated
pillar_primary: R6
pillar_secondary: ["R4"]
tags: {"mechanism": ["decision model as judge", "Jev Choice", "Jev Noul", "judge cascade", "cross-fitted thresholds"], "workload": ["rubric grading", "essay scoring", "dialogue quality", "health answers"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: exact accuracy of each judge against human labels on nine panels", "control": "high: paired bootstrap on units, Holm correction over 27 comparisons, cascade thresholds cross-fitted over 50 random halvings", "independence": "high: University of Pennsylvania authors, no vendor affiliation stated; public panels", "reproducibility": "medium: rubric versions and all judges' verdicts released (Appendix M); single run per judge configuration", "applicability": "medium: rubric judging of text, not memory retrieval, but directly informs using a decision model as an eval judge or gate"}
beliefs_affected: {"supports": ["B13", "B14"], "contradicts": [], "would_create": ["A cheap decision-model judge and flash LLM judges make largely the same confident errors (96% agreement on Jev's top-confidence errors vs 50.3% independence baseline), so escalating only low-confidence items cannot catch confident errors"]}
claim_correction: none (the post's numbers match: 8 of 27 separated, $0.063 vs 29x/66x/325x, 29 s, about 96% repeated errors, at most 1.5 points cascade gain); the post omits that Jev is near chance on ELLIPSE graded exact accuracy (13.4%) and that the 96% figure comes from an 84-pair sample.
---

# JEV vs. LLMs as Rubric Judges: Cheaper, Faster, and Wrong in the Same Places (arXiv 2609.29769)

- **URL:** https://arxiv.org/abs/2609.29769 (HTML https://arxiv.org/html/2609.29769)
- **Type:** paper
- **Author / org:** Delip Rao, Chris Callison-Burch (University of Pennsylvania)
- **Date:** published 2026-09-24
- **Retrieved:** 2026-09-28 via the arXiv API (query `au:Callison-Burch AND abs:Jev`) and the HTML full text; version v1
- **Cited by evidence:** @agentnativedev, https://x.com/agentnativedev/status/2103818961309888616 (backlog cluster x:2103818961309888616, parked 2026-09-27 because the paper was not linked)
- **Relevance to a memory stack:** medium-high. We plan decision-model gates and decision-model judges; this is the most careful independent test of whether a cheap typed judge can replace or front an LLM judge, and it finds the errors are shared.

## TL;DR
- Jev (Choice argmax for graded criteria, Noul for binary) vs three flash LLM judges (GPT-5.6 Luna, Gemini 3.8 Flash, DeepSeek V4.1 Flash) on nine rubric panels, 5,003 pairs.
- Accuracy is statistically separated in only 8 of 27 paired comparisons (95% bootstrap interval excluding zero; Holm correction applied).
- Cost: Jev $0.063 for all nine panels; Luna 29x, DeepSeek 66x, Gemini 325x. Wall time: Jev 29 s; Luna 859 s, Gemini 950 s, DeepSeek 6,298 s.
- Correlated errors: on 84 pairs (12 highest-confidence Jev errors per graded panel), "the three LLM judges repeat Jev's wrong answer 96.0% of the time (242 of 252), where the independence baseline gives 50.3%."
- Cascades with cross-fitted thresholds: "no cascade beats the best single judge by more than 1.5 points on average over the halvings". Jev confidence ranks its own errors on six of seven graded panels (AUROC 0.57 to 0.70) but not on ELLIPSE (0.49) or LFQA factuality (0.41).

## What it claims / describes
The question: can a typed classifier that returns probabilities over permitted answers replace an LLM rubric judge? Nine panels with human labels (Table 1): binary RiceChem (121 units, 819 pairs), HealthBench (200 units, 406 pairs); graded ELLIPSE (258 units, 1,548 pairs), FED-Turn (75, 600), FED-Dialogue (25, 250), HelpSteer2 (90, 360), LFQA (120, 360), USR-TC (72, 360), USR-PC (60, 300). Metric: verdict accuracy (binary) or exact accuracy (graded). Separation: 10,000 bootstrap resamples of units with replacement; "Two judges are separated when the 95% interval excludes zero"; Holm correction across the 27 comparisons. Cascade: threshold tau chosen on a random half of units, evaluated on the other half, averaged over 50 halvings.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| RiceChem verdict accuracy | Jev 81.0% | Luna 77.8% (separated), Gemini 76.1% (survives Holm), DeepSeek 79.2% | Table 2, 819 pairs | |
| HealthBench verdict accuracy | Jev 77.1% | Luna 70.4% (separated), Gemini 79.6%, DeepSeek 76.4% | Table 2, 406 pairs | |
| ELLIPSE exact accuracy | Jev 13.4% | Luna 14.1%, Gemini 29.8% (survives Holm), DeepSeek 15.0% | Table 2, 1,548 pairs | all judges weak; graded scale |
| separated comparisons | 8 of 27 | | 9 panels x 3 LLM judges | remaining 6 panels' numbers not in extract |
| total cost | Jev $0.063 | Luna 29x, DeepSeek 66x, Gemini 325x | all panels | |
| wall time | Jev 29 s | Luna 859 s, Gemini 950 s, DeepSeek 6,298 s | all panels | |
| repeated confident errors | 96.0% (242 of 252) | independence baseline 50.3% | 84 pairs, top-12 Jev errors per graded panel x 3 judges | selected sample |
| best cascade gain | at most 1.5 points | best single judge | 50 cross-fitted halvings; reached on HealthBench | |
| Jev error-ranking AUROC | 0.57 to 0.70 on 6 of 7 graded panels | 0.5 chance | | ELLIPSE 0.49, LFQA factuality 0.41 |

## Mechanism details you could implement
- Judge protocol worth copying: human-labelled panels, paired bootstrap on units (not items), Holm correction, and cascade thresholds fitted on one half and scored on the other, repeated over many halvings. This is the right way to test "decision model first, LLM on escalation" (inference).
- Before building a cascade, measure error correlation between the cheap and expensive judge on the cheap judge's confident errors; if it is near 1, escalation by confidence cannot fix those errors.
- Check AUROC of the cheap judge's confidence for its own errors per criterion; below about 0.55 the confidence is not usable as an escalation signal on that criterion.

## Limitations, caveats, counter-evidence
- The paper lists limitations on observational scope, judge configuration variability, limited runs, sample size, statistics, label availability and generalization (section headings; details not extracted).
- Flash-tier LLM judges only; no frontier judge. Contrast: JEV-as-a-Judge (arXiv 2609.26550, N-20260928-04) compares against GPT-6 and reports a cascade retaining about 99% of the frontier judge's accuracy at lower cost. The two are compatible: this paper asks whether a cascade gains accuracy over the best single judge (barely), the other asks whether it saves cost at near-equal accuracy (yes) (inference).
- The 96% figure is on a selected sample of Jev's most confident errors; overall error correlation is not reported in the extract.
- Rubric grading of text, not retrieval or memory decisions.

## Takeaways for tuning a memory stack
- A decision-model judge is a credible cheap first pass for binary rubric checks, but do not assume an LLM on escalation catches what it misses: the confident errors are shared.
- Evaluate escalation on the borderline population and on confident-wrong cases separately (B13).
- Fit thresholds per criterion locally and check confidence AUROC per criterion (B14).

## Open questions
- Error correlation outside the top-confidence sample.
- Would a frontier or reasoning judge break the correlation?
- Does the same pattern hold for memory admission or supersession gates judged by Jev vs an LLM?

## Grading and labels
- Directness high; control high (paired bootstrap, Holm, cross-fitting); independence high; reproducibility medium (verdicts and rubrics released, single runs); applicability medium.
- Pillars: R6 primary (judge design, correlated errors, statistics), R4 secondary (decision model as a gate with escalation). Tags: cost.
- Beliefs: supports B13 (escalation not automatically better; the gain is at most 1.5 points and confident errors repeat); supports B14 (calibration must be checked locally; AUROC fails on some criteria). Would create a belief on shared confident errors between cheap and LLM judges. No contradiction with a held belief.

## Origin chain
post 2103818961309888616 (@agentnativedev) -> arXiv API search -> 2609.29769 abstract and HTML -> Table 1, Table 2, cascade and calibration sections -> this note. Resolves backlog cluster x:2103818961309888616 (first seen 2026-09-27). Independence: no shared authors with JEV-as-a-Judge (CMU) or the LangChain and neosigma judge notes already on the bus; the panels are public academic datasets.
