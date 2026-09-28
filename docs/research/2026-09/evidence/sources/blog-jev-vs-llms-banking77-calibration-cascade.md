---
schema_version: 1
artifact_id: N-20260926-08
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103460159796510873", "file_id": null, "sha256": null}, {"artifact_id": "post:2103619399274098692", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:towardsdatascience.com/jev-vs-llms-when-ai-moves-from-generation-to-decision-making
claim_cluster: url:towardsdatascience.com/jev-vs-llms-when-ai-moves-from-generation-to-decision-making
feeds: ["decision"]
primary_source: https://towardsdatascience.com/jev-vs-llms-when-ai-moves-from-generation-to-decision-making/
source_commit: n/a
strength: builder-report
pillar_primary: R4
pillar_secondary: ["R6"]
tags: {"mechanism": ["77-way choice classification", "confidence-threshold cascade", "calibration by bin"], "workload": ["intent classification of support messages"], "lifecycle_stage": ["read", "evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: accuracy with intervals, calibration by confidence bin and cascade counts on a public test set", "control": "medium: one open LLM baseline at temperature 0, same inputs, alternating blocks; no frontier LLM", "independence": "high: independent author, public dataset (Banking77, CC BY 4.0)", "reproducibility": "medium: public data and described code directory; no repo URL or commit captured", "applicability": "medium: large closed option sets resemble memory-kind and routing choices; single-turn short messages"}
beliefs_affected: {"supports": ["B13", "B14"], "contradicts": [], "would_create": ["Escalating low-confidence decision-model answers to a weaker general LLM can introduce more errors than it fixes (84 fixed, 211 introduced)"]}
claim_correction: none
---

# Jev vs LLMs: When AI Moves from Generation to Decision-Making (Towards Data Science, Banking77)

- **URL:** https://towardsdatascience.com/jev-vs-llms-when-ai-moves-from-generation-to-decision-making/
- **Type:** builder writeup
- **Author / org:** Nhu Hoang
- **Date:** 2026-09-25
- **Retrieved:** 2026-09-26 (web; no repository URL captured, article references an `experiments/` directory with run logs and request templates; typesafe-sdk 0.7.0)
- **Cited by evidence:** https://x.com/nhu_hoang/status/2103460159796510873 (@nhu_hoang), https://x.com/chien_vu1692/status/2103619399274098692 (@chien_vu1692, commentary)
- **Relevance to a memory stack:** medium-high. A public-dataset test of jev-1.13.0 with per-bin calibration and an actual confidence cascade, the design pattern (decide cheap, escalate when unsure) we plan for H5.

## TL;DR
- Banking77 test set, 3,080 messages, 77 intents. **Jev 81.1% (79.6 to 82.4) vs Qwen3-Coder-Next-80B-A3B 76.4% (74.8 to 77.8)**, +4.7 points (+3.7 to +5.7). Median latency about 245 to 249 ms for both.
- At confidence 1.00, Jev was right **97.1%** of the time on 1,516 messages (44 mistakes). In the 0.7 to 0.9 band, "average confidence was 0.81 but was correct only 53% of the time". **ECE 0.097.**
- Cascade (send Jev's low-confidence answers to Qwen) was worse than Jev alone: at the 1.00 threshold, "replacing Jev's low-confidence answers with Qwen fixed 84 mistakes, but introduced 211 new ones."
- Qwen produced 53 invalid labels (1.72%); Jev used more input tokens (2,288 vs 1,350).

## What it claims / describes
- Models: Jev 1.13.0 via TypeSafe API (one choice question over 77 options); Qwen3-Coder-Next-80B-A3B served locally with vLLM, 4-bit weights, temperature 0.
- Protocol: single pass, no retraining, alternating model blocks of 250 examples; no out-of-category option (Banking77 has known label issues).
- Cascade: pick a Jev confidence threshold; below it, use Qwen's answer.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| accuracy | 81.1% (79.6 to 82.4) | Qwen 76.4% (74.8 to 77.8) | 3,080 test messages | +4.7 (+3.7 to +5.7) |
| median latency | ~245 to 249 ms | same | | local Qwen vs remote API |
| input tokens | 2,288 | Qwen 1,350 | per request | option list cost |
| invalid outputs | 0 (typed) | Qwen 53 (1.72%) | | |
| accuracy at confidence 1.00 | 97.1% | | 1,516 messages, 44 mistakes | |
| 0.7 to 0.9 band | mean confidence 0.81, accuracy 53% | | | overconfident mid-range |
| ECE | 0.097 | | full range | "moderate miscalibration" |
| cascade at threshold 1.00 | 84 fixed, 211 introduced | Jev alone | | net -127 correct |

## Mechanism details you could implement
- Before building a cascade, compute on labelled data: for items below the threshold, how many does the fallback fix vs break. Only escalate to a fallback that is stronger than the primary on the borderline population (inference from the result).
- Look at calibration by bin, not only ECE: the mid band was the problem (0.81 confidence, 53% correct).
- A confidence-1.00 bucket (about half the data here) can be auto-accepted at about 97% accuracy; the rest needs a better fallback or a human.

## Limitations, caveats, counter-evidence
- Fallback was a coder model, not a frontier general LLM; a stronger fallback might help (inference).
- No out-of-scope option; Banking77 label noise not corrected.
- Single run; no repo commit captured.

## Takeaways for tuning a memory stack
- For H5 (two-tier escalation), measure fixes vs breaks of the escalation on the borderline population, not only final accuracy (matches B13 and jevmem's tier-2 regression).
- Recalibrate decision-model confidence locally; mid-range confidence can be badly overconfident.

## Open questions
- Would permutation averaging of the 77 options (N-20260926-09) change calibration? Not tested.
- Does a frontier fallback flip the cascade result? Not tested.

## Grading and labels
- Directness high; control medium; independence high; reproducibility medium; applicability medium.
- Pillar R4 (decision quality, calibration, escalation). Secondary R6.
- Beliefs: supports B13 (escalation not automatically better: 84 fixed vs 211 broken); supports B14 (ECE 0.097, mid-band overconfidence). Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
post 2103460159796510873 (@nhu_hoang) -> towardsdatascience.com article (2026-09-25) -> accuracy table, calibration section, cascade section -> this note. Independence: public Banking77 dataset; model under test jev-1.13.0 shared with N-20260926-06 and -07.
