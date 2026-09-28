---
schema_version: 1
artifact_id: N-20260926-07
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103052792147456510", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.24052
claim_cluster: arxiv:2609.24052
feeds: ["decision"]
primary_source: https://arxiv.org/abs/2609.24052
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R4
pillar_secondary: ["R6"]
tags: {"mechanism": ["typed schema extraction", "gated dependent questions", "isotonic and Platt recalibration", "selective risk / review budget"], "workload": ["structured coding of long free-text reports"], "lifecycle_stage": ["write", "evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: F1 against 2,416 human judgments and per-variable ECE/Brier tables", "control": "medium: two frontier LLM baselines with an exact McNemar test and cross-fitted recalibration; LLM baselines prompted to state probabilities", "independence": "medium: academic transport-safety authors, no stated vendor tie", "reproducibility": "medium: authors state code, schema and aggregates are released; repo URL and commit not captured", "applicability": "medium: typed extraction from long narratives resembles typed-decision capture from long artifacts; domain is crash reports"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Decision-model calibration varies by model, not by paradigm; cross-fitted isotonic/Platt recalibration on local labels cut calibration error about 3.3x"]}
claim_correction: none
---

# Calibrated Decisions at Scale: Converting Police Crash Narratives into Probabilistic Crash Variables with a System One Model (arXiv 2609.24052)

- **URL:** https://arxiv.org/abs/2609.24052 (HTML read)
- **Type:** paper
- **Author / org:** Amir Rafe, Subasish Das (affiliations not captured)
- **Date:** 2026-09-21
- **Retrieved:** 2026-09-26; no repository URL captured (authors state all code, schema, runner metrics and aggregated results are released)
- **Cited by evidence:** https://x.com/HEI/status/2103052792147456510 (@HEI, arXiv feed bot)
- **Relevance to a memory stack:** medium-high. The most detailed calibration audit of jev-1.13.0 we have, with a working recalibration recipe and a review-budget formula for "flag, then human-check" pipelines.

## TL;DR
- 499,500 Texas crash narratives screened with a 10-question schema ($25.23), 195,857 coded with a 27-question typed schema ($30.22): realised **$0.154 per 1,000 narratives**; projected $774 for all 5,018,080.
- Against 2,416 human judgments on 400 narratives: **F1 0.908**; median latency 0.20 s; mean 3,673 tokens per narrative.
- Frontier LLM baselines (prompted to "state a probability and use the full range"): one gained **0.059 F1** over Jev, the other no significant difference (exact McNemar).
- Calibration vs coded fields (Table 4): ECE 0.0122 to 0.0455, Brier 0.0031 to 0.0197, **calibration slopes 0.51 to 1.24**. "Calibration varies by model rather than by paradigm."
- Cross-fitted recalibration (isotonic and Platt, fit on one half, scored on the other, 50 bidirectional repeats) "reduces calibration error by a factor of 3.3".

## What it claims / describes
- **Schema:** 27 typed questions: 16 binary presence, 8 categorical with closed option sets, 3 ordinal; 7 gated dependent variables (asked only if the gate is present, threshold tau = 0.5).
- **Output:** probabilities on a two-decimal grid (0.01 to 1.00), single parallel pass, no generated text.
- **Token model (Eq. 3):** T(k, l) = 3,562 + 122k + 0.236 l (k questions, l narrative length), R^2 = 0.975: schema overhead dominates cost. Break-even screening threshold q* = 0.58 to 0.67.
- **Grid floor (Proposition 1):** for variables with base rate below the 0.01 grid step, attainable calibration error is 0.0046 to 0.0057 whatever the model.
- **Selective risk (Eq. 16 to 18):** precision and risk defined over flagged records only, so a target precision converts to a share of flagged records to review: 0.8% of flagged records per variable at 90% target precision.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| F1 vs human | 0.908 | | 2,416 judgments, 400 narratives, stratified with weights | humans saw twice-redacted text, Jev owner-redacted |
| frontier LLM A | +0.059 F1 over Jev | Jev 0.908 | same set | model names not captured |
| frontier LLM B | n.s. | Jev | exact McNemar | |
| ECE vs coded fields | 0.0122 to 0.0455 | | Table 4 | coded fields are incomplete references |
| Brier | 0.0031 to 0.0197 | | Table 4 | |
| calibration slope | 0.51 to 1.24 | 1.0 ideal | Table 4 | |
| per-variable ECE vs human | 0.008 to 0.022 | | Table 5 | median human/coded error ratio 1.0 |
| recalibration | ~3.3x lower calibration error | raw | cross-fitted halves, 50 repeats | same labels |
| cost | $0.154 per 1,000 narratives | | 499,500 screened, 195,857 coded | |
| latency | median 0.20 s | | | |
| review budget | 0.8% of flagged records per variable | | 90% target precision | |

## Mechanism details you could implement
- **Two-stage screen then code:** a cheap short schema decides whether the expensive schema is worth running (break-even q* 0.58 to 0.67 here). Same shape as a recall/no-recall gate in front of retrieval.
- **Gated dependent questions:** ask follow-ups only when the parent probability is >= 0.5.
- **Cross-fitted recalibration:** fit isotonic or Platt on half the labelled data, evaluate on the other half, swap, repeat; report slope as well as ECE.
- **Review budget from target precision:** compute the share of flagged items a human must check at a given precision, instead of a global threshold.
- **Know the grid floor:** with a 0.01 probability grid, rare events (<1% base rate) cannot be calibrated below about 0.005 ECE.

## Limitations, caveats, counter-evidence
- Paper's list: grid-resolution floor for rare variables; coded fields are incomplete (agreement vs accuracy kept separate); human/Jev input asymmetry (redaction); "No prompt order or wording bias testing performed on typed interface"; prevalence estimates from a 150,000-narrative random stratum only.
- The missing order-bias test matters: N-20260926-09 shows jev-1.13.0 choice probabilities can be heavily skewed by option identity (inference: relevant to the categorical questions here).
- One domain, one decision model version.

## Takeaways for tuning a memory stack
- Plan to recalibrate any decision-model gate on our own labels; expect slopes far from 1 before recalibration.
- Price typed extraction by schema size: the fixed 3,562-token overhead dominates, so batch questions per state.
- Use a selective-risk review budget for human review of memory writes.

## Open questions
- Which frontier LLM beat Jev by 0.059 and at what cost? Names not captured.
- Does recalibration hold across months (drift)? Not tested.

## Grading and labels
- Directness high; control medium; independence medium; reproducibility medium (release stated, commit not captured); applicability medium.
- Pillar R4 (typed decisions, calibration, abstention/review). Secondary R6 (evaluation against incomplete references).
- Beliefs: supports B14 (calibration is not guaranteed by the vendor: slopes 0.51 to 1.24; fit locally; recalibration helps 3.3x). Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
post 2103052792147456510 (@HEI) -> arXiv 2609.24052 (HTML) -> model and schema section, Tables 4 and 5, recalibration section, cost section, limitations -> this note. Independence: no shared authors with other notes; same model version (jev-1.13.0) as N-20260926-06 and N-20260926-08.
