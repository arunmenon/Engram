---
schema_version: 1
artifact_id: N-SURVEY-20260929-02
artifact_type: note
producer: triage
run_id: survey-20260929T054503Z-ed98
created_at: 2026-09-29T05:59:00Z
idempotency_key: note:survey:arxiv:2609.33843
input_refs: []
pillar_primary: R9
pillar_secondary: [R4, R6]
memory_stage: write_gate
priority: 2
beliefs_affected:
  supports: [B14]
  contradicts: []
evidence:
  directness: 4
  control: 5
  independence: 5
  reproducibility: 5
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.33843
secondary_sources:
  - https://arxiv.org/abs/2609.33401
found_via: survey
claim_cluster: local-recalibration-and-threshold-transfer-for-system-one-gates
revises_note: N-SURVEY-20260928-11
---

# Local recalibration of System One models: which method works, and do fitted thresholds hold? (Laya reproduction, arXiv 2609.33843, with the recalibration tables of arXiv 2609.33401)

- **URL:** https://arxiv.org/abs/2609.33843 (read: https://arxiv.org/html/2609.33843v1). Companion: https://arxiv.org/abs/2609.33401 (read: html v1), Tables 15 to 21.
- **Type:** paper (two independent papers, one claim cluster)
- **Author / org:** Gowthamkumar Nandakumar (declares no affiliation with Convai, the dataset publisher or TypeSafe); companion by Yixuan Liu (TraceStone; NTU Singapore)
- **Date:** 2026-09 (both)
- **Retrieved:** 2026-09-29
- **Cited by evidence:** survey run, R9 questions 1 and 4; changes N-SURVEY-20260928-11
- **Relevance to a memory stack:** high for any gate (write gate, recall gate, injection gate) that accepts a System One answer above a confidence threshold. PC-20260926-04, PC-20260928-05 and PC-20260929-01 all assume local recalibration will make those thresholds trustworthy.

## What this changes in an existing note
N-SURVEY-20260928-11 recorded Laya's card claim of ECE 0.081 after temperature refit against an independent median ECE of 0.275, and read that as "vendor calibration does not transfer; refit temperature locally". This reproduction, on the pinned `laya-typed-decisions` checkpoint (revision 1a793eb5) and pinned dataset (revision f7a2487e), adds three things:
1. The miscalibration is **under-confidence**, not over-confidence: mean confidence 0.553 vs accuracy 0.767 (signed gap -0.2142). The shipped temperatures (1.760 choice, 1.983 Noul, 1.251 score) soften, which is the wrong direction; the locally fitted temperature was T = 0.469 (sharpening).
2. **A single temperature works; isotonic does not generalise.** Isotonic had the best calibration-split NLL (0.4463) but the worst held-out NLL (0.7738, worse than identity 0.7027). The registered hypothesis that the frozen calibrator improves held-out NLL failed (delta NLL +0.071, CI [-0.087, +0.263], p = 0.446).
3. **A threshold fitted on a calibration split did not hold its error budget on test.** Registered H3a (accepted-set error at most 10%) failed: 0.0916 on the calibration split became 0.1399 on test.
The companion paper finds the same for Jev on security decisions: temperature scaling made Jev worse on two of three benchmarks.

## TL;DR
- Laya-typed-decisions reproduces the card on accuracy (0.7670 vs 0.766) and ECE-10 (0.2142 vs 0.213) but not soft accuracy (0.5086, CI excludes 0.471).
- Single temperature: held-out ECE15 0.2035 to 0.0372 at unchanged accuracy (0.762).
- Isotonic, the pre-registered winner on the calibration split, generalised worst.
- Escalating below tau = 0.70 keeps 67.2% coverage at 86.0% accepted-set accuracy; the 10% error target failed on test (14.0%).
- For Jev on security decisions (2609.33401), fitted temperatures were extreme (T = 10.93 on WAInjectBench, T = 0.05 on AgentHarm) and worsened ECE (0.104 to 0.134) or NLL (0.481 to 2.163). With a 1% miss limit, Jev automated 0.00% of WAInjectBench and 7.63% of R-Judge.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Laya accuracy | 0.7670 [0.7455, 0.7870] | card 0.766 | typed-decisions test, 2,000 decisions | labels from a ~4B teacher, mean of 3 samples at T=0.7 |
| Laya ECE-10 | 0.2142 | card 0.213 | same | |
| Laya soft accuracy | 0.5086 [0.4987, 0.5196] | card 0.471 | same | does not reproduce |
| Jev 1.13.0 on same set | accuracy 0.727, ECE15 0.144 | | third-party figure quoted in Table 3 | not run by the author |
| Laya Track B (retrained, 960 train) | acc 0.7710, NLL 0.6271, ECE15 0.1509 | released 0.7670 / 0.7069 / 0.2142 | Table 3 | accuracy delta +0.0040, p = 0.568 |
| ModernBERT-base specialist | acc 0.5425, ECE15 0.0728 | | Table 3 | different training method from card row |
| Held-out NLL, identity / temperature / isotonic | 0.7027 / 0.5364 / 0.7738 | | Table 4, 1,000-decision eval split | isotonic overfits |
| Held-out ECE15, identity / temperature / isotonic | 0.2035 / 0.0372 / 0.0505 | | Table 4 | |
| Escalation at tau* = 0.70 | coverage 0.672, accepted accuracy 0.8601 | random escalation | E5 | beats random by +0.0646, p <= 1e-4 |
| Accepted-set error, calib to test | 0.0916 to 0.1399 | target 0.10 | H3a | registered hypothesis failed |
| Refitting temperatures on training cases | test ECE15 0.0236 to 0.0873 | | Track B | 3.7x inflation: fit on held-out data only |
| Out-of-distribution claim verification | acc 0.617, AUROC 0.589, false acceptance 0.333 | | E10, exploratory | |
| Laya latency, batch 1 | p50 95.9 ms per case, 19.2 ms per decision, 54.3 decisions/s | | Apple M5 Max, MPS | |
| Jev ECE, security (2609.33401 T15) | 0.104 / 0.120 / 0.128 | Laya lowest on AgentHarm 0.072 | WAInjectBench / R-Judge / AgentHarm | T15 and T18 disagree for R-Judge (0.120 vs 0.137) |
| Jev after temperature scaling (T18) | ECE 0.104 to 0.134 (T=10.93); NLL 0.481 to 2.163 (T=0.05) | | WAInjectBench; AgentHarm | recalibration did not reliably help |
| Coverage at 1% miss limit (T19) | Jev 0.00%, Laya 5.02%, Nimble 0.74%, GPT-4.1 0.00% | | WAInjectBench, frozen policy | |
| R-Judge coverage, recalibrated, independent thresholds (T21) | Jev 47.03% at 0.00% misses, 1.80% false blocks | GPT-4.1 52.54%, 15.32% false blocks | | post-hoc analysis |

Pre-registration (2609.33843): frozen 2026-09-26 15:50 UTC; 24 confirmatory tests under BH-FDR q = 0.05; 22 executed, 20 rejected. H2 (calibration) and H3a (error budget) failed; H4 (external validity) not executed.

## Mechanism details you could implement
- Fit ONE temperature per decision type on a held-out calibration split; do not fit on training cases; prefer temperature to isotonic when the calibration split is about 1,000 decisions or fewer.
- Check the sign of the gap before assuming over-confidence: Laya is under-confident and needs sharpening.
- Report the accepted-set error on a split that was not used to pick the threshold; expect it to be worse (here 9.2% to 14.0%).

## Limitations, caveats, counter-evidence
- Synthetic benchmark with teacher-model labels; no human labels; one checkpoint.
- The escalation target is an oracle bound, not a real larger model.
- The security paper's selective-automation and recalibration analyses were added after the primary evaluation.
- Neither paper uses memory decisions (save/skip, relevance, staleness).

## Takeaways for tuning a memory stack
- Our planned isotonic recalibration (PC-20260926-04) should add a single-temperature arm and must evaluate threshold transfer on a split not used to fit.
- A write gate with a "1% error" promise cannot be certified from a calibration split of this size; budget for a larger held-out check or an explicit error margin.

## Open questions
- Does Jev on our memory decisions show over- or under-confidence?
- How many labelled decisions does a threshold need before its accepted-set error transfers within 2 points?
