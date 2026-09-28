---
schema_version: 1
artifact_id: N-20260927-17
artifact_type: note
producer: triage
run_id: triage-20260927T074501Z-b34f
created_at: 2026-09-27T07:58:26Z
input_refs: [{"artifact_id": "post:2103920794967691755", "file_id": null, "sha256": null}, {"artifact_id": "post:2103914756880888302", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:internlm/intern-decision
claim_cluster: github:internlm/intern-decision
feeds: ["decision"]
primary_source: https://github.com/InternLM/Intern-Decision
source_commit: 2f815802058b2464144218859ea9221c1bc0d2a8
strength: repo-pinned
pillar_primary: R4
pillar_secondary: ["R6"]
tags: {"mechanism": ["open-weight-decision-model", "temperature-calibration", "one-forward-pass-typed-answers"], "workload": ["typed-decisions", "tool-selection", "jailbreak-detection", "classification"], "lifecycle_stage": ["decide"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-suite accuracy, Brier and ECE for Jev and four open baselines, latency table, bundled eval records", "control": "medium: same suites for all arms, but baselines use default probabilities while Intern-Decision gets a fitted temperature, and Jev latency includes a network hop", "independence": "low: vendor-run comparison against competitors; training data undisclosed", "reproducibility": "medium: pinned commit, bundled evaluation records and scorer; weights on HF; training data and calibration split private; external baseline runners not included", "applicability": "medium: a self-hostable decision model with measured calibration is a candidate implementation for admission and rerank gates"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Third-party ECE for hosted Jev 1.13 is 0.095 on Jevbench-Hard (111 items) and 0.130 on a 96-case known-distribution pilot; an open 4B model with a fitted temperature reaches 0.065 and 0.089"]}
claim_correction: Posts present "4B beats Jev (90.0 vs 88.7)" and "44 ms vs Jev's 110 ms" as a like-for-like win; the README itself says "The protocols and scope differ", Intern-Decision gets a fitted temperature while baselines do not, Jev's 109.70 ms is a hosted call against a local RTX 4090 run, and Intern-Decision-4B is 6.4 points below Jev on WildJailBreak (89.86 vs 96.29).
---

# Intern-Decision (InternLM): open-weight 0.8B / 2B / 4B typed decision models

- **URL:** https://github.com/InternLM/Intern-Decision (weights: https://huggingface.co/collections/internlm/intern-decision)
- **Type:** repo
- **Author / org:** InternLM (Shanghai AI Laboratory lineage, org name only stated as InternLM). Apache-2.0 per posts; fine-tuned from Qwen3.5 with the vision tower and projector frozen.
- **Date:** commit 2f815802058b2464144218859ea9221c1bc0d2a8, 2026-09-26 16:58:43 +0800, "Swap Mario and browser demonstration positions"
- **Retrieved:** 2026-09-27 (shallow clone at repos/intern-decision). Read: README.md (Method, Results, latency, calibration benchmark, evaluation sections), docs/EVALUATION.md lines 180 to 204.
- **Cited by evidence:** @YashChaudharyAI https://x.com/YashChaudharyAI/status/2103920794967691755 ; @saiitoshii https://x.com/saiitoshii/status/2103914756880888302 (backlog, deferred by budget)
- **Relevance to a memory stack:** medium. A self-hostable decision model with published per-suite calibration, and (more useful to us) an outside measurement of hosted Jev's calibration error, which B14 said nobody had shown.

## TL;DR
- Method: "autoregressive masked language modeling"; the input carries a JSON skeleton with one `<decision>` token per field; "the logit immediately before a marker predicts that field's answer. All fields share one causal forward pass." Inference restricts logits to legal single-token answer symbols and softmaxes.
- Seven suites (10,751 rows, 12,351 decisions): Intern-Decision-4B average 90.02% vs Jev 88.74%; on "Typed Decision" 80.55 vs 73.35; ToolACE 96.45 vs 91.29; WildJailBreak 89.86 vs 96.29 (Jev ahead).
- Calibration on Jevbench-Hard (111 items): Jev ECE 0.094685, Brier 0.358420; Intern-Decision-4B (T = 1.992418) ECE 0.065267, Brier 0.346762.
- 96-case known-distribution pilot: Jev (`jev-1.13.0`) Brier / ECE 0.595 / 0.130; Intern-Decision-4B uncalibrated 0.628 / 0.213, calibrated 0.550 / 0.089. Temperature fitted on a separate calibration split, not this benchmark.
- Latency (RTX 4090, BF16, 289 input tokens, three fields in one pass): 4B mean 44.16 ms; Jev 109.70 ms mean (hosted).

## What it claims / describes
Open decision models that take a state, optional images and typed questions (`choice`, `score`, `noul`) and return a probability per option in one forward pass. The release includes training code, two inference backends, benchmark scoring, temperature calibration, a browser demo, the 96-case calibration benchmark with its generator and scorer, and the bundled evaluation records for the seven accuracy suites. Not included: "Training data, private calibration/validation records, images, preparation pipelines, and model weights" (weights are on Hugging Face). Temperature: "Fit one positive scalar per checkpoint by NLL on calibration data only"; "NLL-optimal temperature need not minimize ECE on another dataset."

## Numbers

| model | Easy | Original | Hard | Typed Decision | ToolACE | AG News | WildJailBreak | Average | Brier | ECE | T |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Jev | 100.00 | 98.61 | 72.07 | 73.35 | 91.29 | 89.57 | 96.29 | 88.74 | 0.358420 | 0.094685 | none |
| Laya | 95.83 | 72.22 | 28.83 | 35.95 | 63.87 | 92.84 | 14.84 | 57.77 | 0.804244 | 0.246455 | none |
| SemIf | 100.00 | 98.61 | 61.26 | 62.80 | 85.16 | 89.22 | 92.53 | 84.23 | 0.498012 | 0.112213 | 1.0 |
| Kev | 100.00 | 93.06 | 45.05 | 65.60 | 87.42 | 89.82 | 75.97 | 79.56 | 0.738253 | 0.262200 | 2.962195 |
| JevK5 | 100.00 | 97.22 | 73.87 | 64.50 | 80.97 | 89.13 | 90.45 | 85.16 | 0.366162 | 0.046672 | 1.532 |
| Intern-Decision-0.8B | 97.92 | 80.56 | 52.25 | 77.35 | 94.52 | 88.61 | 64.48 | 79.38 | 0.529519 | 0.065710 | 2.747761 |
| Intern-Decision-2B | 100.00 | 84.72 | 63.96 | 79.35 | 96.45 | 89.96 | 78.33 | 84.68 | 0.437256 | 0.100208 | 2.100509 |
| Intern-Decision-4B | 100.00 | 98.61 | 73.87 | 80.55 | 96.45 | 90.82 | 89.86 | 90.02 | 0.346762 | 0.065267 | 1.992418 |

Suite sizes: Jevbench Easy / Original / Hard 48 / 72 / 111; AG News 7,600; ToolACE 310; Typed Decision 400 rows, 2,000 decisions; WildJailBreak 2,210. Brier and ECE columns are Jevbench-Hard only (111 items), max(P) confidence, 10 equal-width bins. "Baselines use their reported/default probabilities; no additional temperature was fitted here."

| latency (RTX 4090) | mean | p50 | p95 |
|---|---|---|---|
| Jev | 109.70 ms | 106.30 ms | 146.70 ms |
| Intern-Decision-0.8B | 33.98 ms | 33.44 ms | 37.50 ms |
| Intern-Decision-2B | 33.28 ms | 33.15 ms | 33.55 ms |
| Intern-Decision-4B | 44.16 ms | 44.03 ms | 44.60 ms |

| pilot category (Brier / ECE) | 4B uncal. | 4B cal. | Jev |
|---|---|---|---|
| Direct randomness and support | 0.483 / 0.181 | 0.421 / 0.129 | 0.490 / 0.216 |
| Composed events and mixtures | 0.677 / 0.254 | 0.577 / 0.150 | 0.682 / 0.274 |
| History, conditioning, hidden state | 0.711 / 0.219 | 0.613 / 0.108 | 0.657 / 0.113 |
| Daily evidence and observation bias | 0.701 / 0.328 | 0.575 / 0.210 | 0.603 / 0.114 |
| Selective disclosure and probability puzzles | 0.540 / 0.119 | 0.510 / 0.049 | 0.483 / 0.138 |
| Sequential and combinatorial processes | 0.656 / 0.180 | 0.605 / 0.058 | 0.657 / 0.116 |
| Overall (pooled) | 0.628 / 0.213 | 0.550 / 0.089 | 0.595 / 0.130 |

"The paired option variants make this a small diagnostic study, not 96 independent trials."

## Mechanism details you could implement
- One causal pass answering several typed fields: put a `<decision>` marker per field in a JSON skeleton and read the logit before each marker, restricted to legal answer tokens.
- Calibrate a self-hosted decision model with a single temperature per checkpoint fitted by NLL on a disjoint calibration split; never reuse a temperature across checkpoints.
- Evaluate calibration on a known-distribution benchmark (questions with exact reference probabilities) in addition to label accuracy.

## Limitations, caveats, counter-evidence
- README: "The protocols and scope differ." Baselines receive no temperature fit; Intern-Decision does.
- Jev latency is a hosted round trip compared with local GPU inference (inference from the setup text: "Local measurements use one NVIDIA RTX 4090").
- EVALUATION.md: "This release does not include those baseline runners or historical responses, so the commands here regenerate Intern-Decision rows directly, not the complete external-baseline comparison from nothing." Jev row used `jev-1.13.0`; "a hosted service may change."
- Training data undisclosed, so contamination of Typed Decision or ToolACE test splits cannot be checked.
- Jev leads on WildJailBreak (96.29 vs 89.86): for an injection or jailbreak gate, the open 4B is worse.
- Calibration numbers come from 111 and 96 items.

## Takeaways for tuning a memory stack
- A self-hosted 4B decision model is within reach for admission, rerank and routing gates where data must not leave the building; measure it on your own labelled set and fit its temperature on a disjoint split.
- Do not use it as the injection gate without testing: the one security-flavoured suite favours Jev.
- Hosted Jev's calibration error measured by a third party is 0.095 to 0.130 on small sets: fit thresholds locally.

## Open questions
- Intern-Decision on engineering-agent decisions (tool call risk, supersession, staleness)?
- Jev with a fitted temperature on the same suites?

## Grading and labels
- Directness: high. Control: medium. Independence: low. Reproducibility: medium. Applicability: medium.
- Strength: repo-pinned. Pillar R4 (decision model implementation and calibration); secondary R6 (comparison protocol asymmetries).
- Beliefs: supports B14 (vendor calibration now measured by a third party, and it is imperfect: ECE 0.095 and 0.130). Would create: third-party calibration figures for Jev 1.13 and an open alternative.
- Contradiction rows: none. B14's "Against: none" row gains a measurement but the belief's direction holds.

## Origin chain
@YashChaudharyAI and @saiitoshii posts -> github.com/InternLM/Intern-Decision at 2f81580 -> README Results, latency and calibration tables; docs/EVALUATION.md section 6 -> this note. Independence: Laya, SemIf, Kev, JevK5 are community projects; SemIf and Kev also supply held-out sets to RSI-Jev (`github-shanghua-gao-rsi-jev.md`), so the open decision-model ecosystem shares benchmarks.
