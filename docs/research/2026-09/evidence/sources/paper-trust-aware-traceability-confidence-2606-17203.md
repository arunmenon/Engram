---
schema_version: 1
artifact_id: N-SURVEY-20261001-01
artifact_type: note
producer: triage
run_id: survey-20261001T054505Z-09ae
created_at: 2026-10-01T05:58:00Z
idempotency_key: note:survey:arxiv:2606.17203
input_refs: []
pillar_primary: R10
pillar_secondary: [R4, R9]
memory_stage: linking
priority: 3
beliefs_affected:
  supports: []
  contradicts: []
contradicts_doc_claim: "pdlc-memory-layer.md section 2 and memory-research-landscape.md row 6.5: a calibrated confidence per trace link stops low-confidence upstream decisions from orphaning requirements downstream"
evidence:
  directness: 4
  control: 3
  independence: 3
  reproducibility: 1
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2606.17203
found_via: survey
claim_cluster: confidence-scored-trace-links-trust-aware-kg
---

# Trust-Aware Multi-Agent Traceability: Confidence-Calibrated Knowledge Graphs for Consistent Software Artifact Management (arXiv 2606.17203)

- **URL:** https://arxiv.org/abs/2606.17203 (read: https://arxiv.org/html/2606.17203v1; local copy `out/log/raw/arxiv-2606.17203.html`)
- **Type:** paper
- **Author / org:** not captured from the HTML read (inference: academic group working with automotive ASPICE / ISO 26262 material)
- **Date:** 2026-06-15 (v1)
- **Retrieved:** 2026-10-01 (local copy: out/log/raw/arxiv-2606.17203.html)
- **Cited by evidence:** survey run, R10 plan question 1 (confidence-scored trace links). Cited in our own `pdlc-memory-layer.md` section 2 and `memory-research-landscape.md` row 6.5 as the source for calibrated per-link confidence; the September survey recorded no numbers.
- **Relevance to a memory stack:** high. It is the source our PDLC design cites for confidence on IMPLEMENTS / VERIFIES / REFINES links, and the primary read narrows it substantially.

## TL;DR
- **The "calibrated" confidence is not shown to be calibrated.** The paper says it evaluates with "Expected Calibration Error and Brier score", but no ECE or Brier value appears in any table. Confidence is the LLM's own verbalised score in five bands; no post-hoc calibration (temperature or Platt scaling) is applied. The LLM and the embedding model are not named.
- **Confidence filtering lowered path completeness, the measure closest to "no orphaned requirements".** Conflict-aware path completeness was 100.00% with no consistency controls, 36.12% with no confidence filtering, 33.64% with the full stack (Table VI, averaged over five subsystems). The authors read this as the controlled graph "explicitly exposes structural inconsistencies"; it is not evidence that confidence prevents orphans.
- **The useful result is the threshold sweep (Table VII):** link-creation threshold 0.7 gives the best F1 (P 0.782, R 0.818, F1 0.796, review queue 23.0); 0.9 gives P 0.983 at R 0.340.
- Link prediction: full pipeline (embedding top-k then LLM multi-criteria judgement) F1 0.769 against embedding-only 0.707, LLM-only 0.669, TF-IDF 0.349 (Table II).
- Small: 535 artifacts, one automotive case study, no code or data release found, no cost or latency reported.

## What it claims / describes
A sequential multi-agent pipeline (requirements analysis, architecture, test generation, traceability linking) writes into a shared knowledge graph, which acts as "both centralized semantic memory and a coordination surface". Each link carries (y, c, j): a label, a confidence c in [0,1], and a justification.

Link prediction is two-stage:
1. Semantic retrieval: cosine similarity between sentence-encoder embeddings of source r and candidate c; keep top-k (k about 10 in context; exact value not stated as a parameter).
2. LLM multi-criteria analysis: the LLM "jointly evaluates" four criteria (requirement coverage, implementation specificity, terminology alignment, absence of contradiction) and returns label, confidence and justification.

Confidence bands given to the LLM: "0.90 to 1.00 clear/direct, 0.70 to 0.89 strong, 0.50 to 0.69 partial, 0.30 to 0.49 indirect, 0.00 to 0.29 no relationship".

Downstream agents read upstream confidence; a conflict detector (parameters tau and epsilon) flags divergence between stages; a link-creation threshold theta_create gates which predicted links are written.

Data: 535 artifacts from six automotive subsystems (AEB, LKA, BMS, IVI, V2X, DMS): 83 system requirements, 128 software requirements, 124 architectural components, 200 test specifications. Gold: "human-validated traceability matrices"; the number of gold links is not stated.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Link P / R / F1 / MAP, full pipeline | 0.900 / 0.687 / 0.769 / 0.905 | Embedding-only 0.829 / 0.637 / 0.707 / 0.913; LLM-only 0.705 / 0.699 / 0.669 / 0.796; TF-IDF 1.000 / 0.228 / 0.349 / 0.894 | Table II | LLM unnamed; n of gold links not stated |
| REF_BY (SysReq to SwReq) P / F1 / MAP | 1.000 / 0.842 / 0.875 | none | Table III | |
| IMP_BY (SwReq to Component) P / F1 / MAP | 0.833 / 0.833 / 0.939 | none | Table III | |
| VER_BY (SwReq to Test) P / F1 / MAP | 0.857 / 0.706 / 0.773 | none | Table III | verifies is the weakest link type |
| Conflict detection | TP 10, FN 0, zero false positives at (tau 0.5, epsilon 0.4) | 120 grid configurations | Table IV | only 10 positive conflicts; best of 120 configurations chosen on the same data |
| Final links / new links / inflation | 64.4 / 21.4 / 1.46 (full stack) | no controls 169.4 / 126.4 / 3.94; no confidence filtering 147.6 / 104.6 / 3.43; no conflict detection 65.6 / 22.6 / 1.48 | Table V, mean of 5 subsystems | |
| Conflict rate / mean severity / conflict-aware path completeness | 15.42% / 0.5207 / 33.64% (full stack) | no controls 0.00 / 0.00 / 100.00; no confidence filtering 3.97 / 0.6569 / 36.12; no conflict detection 0.00 / 0.00 / 100.00 | Table VI | completeness falls when filtering is on |
| theta_create 0.5 | P 0.461, R 0.892, F1 0.604, queue 63.0 | | Table VII | |
| theta_create 0.6 | P 0.612, R 0.881, F1 0.715, queue 43.2 | | Table VII | |
| theta_create 0.7 | P 0.782, R 0.818, F1 0.796, queue 23.0 | | Table VII | best F1 |
| theta_create 0.8 | P 0.925, R 0.651, F1 0.758, queue 7.0 | | Table VII | |
| theta_create 0.9 | P 0.983, R 0.340, F1 0.500, queue 0.0 | | Table VII | |
| theta_create 0.0 to 0.4 | P 0.28 to 0.34, R about 0.90, F1 0.43 to 0.49, queue 93 to 112 | | Table VII | |
| ECE, Brier | not reported | | | named as metrics in the contributions list only |
| Cost, latency | not reported | | | |

Text and tables: the abstract says "Ablation studies confirm that confidence calibration is essential for effective pipeline coordination"; the tables contain no calibration measurement, so the claim rests on the effect of filtering by confidence, not on calibration. Text line: "0.228 recall would leave 77% of requirements orphaned" refers to the TF-IDF baseline recall, not to the full stack.

## Mechanism details you could implement
- Retrieve-then-judge for trace links: embedding top-k (about 10) candidates per source artifact, then one judge call per pair returning label, confidence and a justification string.
- Four judging criteria, usable as the question set for a typed decision model: coverage, specificity, terminology alignment, absence of contradiction.
- A creation threshold on confidence, with sub-threshold links routed to a review queue; at 0.7 the queue was 23 links per subsystem on this data.
- Per-type evaluation: report REFINES, IMPLEMENTS, VERIFIES separately; VERIFIES (requirement to test) was hardest here.

## Limitations, caveats, counter-evidence
- Calibration is asserted, not measured. Verbalised LLM confidence is known to need fitting (inference, consistent with our notes on local recalibration, for example N-SURVEY-20260929-02 on arXiv 2609.33843).
- One domain, 535 artifacts, no released code or data found, model names not given: reproducibility is low.
- Hyperparameters (tau, epsilon, theta) were swept and the best reported on the same data; no held-out split is described.
- Authors' own limits: "bootstrap problem of confidence calibration in domains lacking ground truth remain open"; "Domain-expert parameter delta manually set rather than empirically tuned".
- No page content addressed instructions to an AI agent.

## Takeaways for tuning a memory stack
- Do not cite this paper as evidence that per-link confidence prevents orphaned requirements; its own completeness numbers go the other way. Measure orphan rate (requirements with no IMPLEMENTS or VERIFIES path) directly as a function of the link threshold.
- If links carry a confidence, fit the threshold on held-out labels; the 0.7 optimum here is specific to this unnamed LLM's verbalised scale.
- Report precision, recall, review-queue size and orphan rate together per threshold; the queue is the human cost.

## Open questions
- Which LLM and encoder were used, and what would ECE be for the verbalised bands?
- Would a decision model's probability (Jev Noul or an open-weight equivalent) give a better precision and recall curve than five verbalised bands? See the ordinal-scale bias note N-SURVEY-20261001-06 on band compression.
