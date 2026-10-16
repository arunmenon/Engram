---
schema_version: 1
artifact_id: N-20260928-08
artifact_type: note
producer: triage
run_id: triage-20260928T014503Z-edff
created_at: 2026-09-28T01:55:04Z
input_refs: [{"artifact_id": "post:2104124392410124517", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:pavelravvich/jev-bench
claim_cluster: github:pavelravvich/jev-bench
feeds: ["decision"]
primary_source: https://github.com/PavelRavvich/jev-bench
source_commit: 8f5694d53550d56c8fc4f8a2cd48efc43da6de2f
strength: repo-pinned
pillar_primary: R4
pillar_secondary: ["R6"]
tags: {"mechanism": ["Jev noul", "Jev choice", "calibration", "verbalized confidence"], "workload": ["intent classification", "spam detection", "Banking77", "SMS Spam"], "lifecycle_stage": ["decision"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: accuracy, macro-F1, ECE, Brier, latency and cost per model from committed prediction files", "control": "medium: same messages, fixed seed 42, paired bootstrap CIs in the code; frontier model only on the first 130 or 135 messages and with errors", "independence": "high: individual author, no vendor affiliation stated", "reproducibility": "high: pinned commit, raw predictions and summaries committed, model versions recorded", "applicability": "low-medium: short-text classification, not memory decisions"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": []}
claim_correction: none; the post makes no numeric claim. New relative to the three Banking77 notes on the bus: an ECE measurement for Jev (0.071 on Banking77, 0.045 on SMS spam) against verbalized-confidence LLMs.
---

# jev-bench: TypeSafe Jev vs GPT-6 Luna and GPT-6 Astra on SMS Spam and Banking77 (PavelRavvich/jev-bench)

- **URL:** https://github.com/PavelRavvich/jev-bench (article https://medium.com/@pravvich/typesafes-jev-beyond-the-hype-an-independent-benchmark-8bdc1c99d000, not read)
- **Type:** repo
- **Author / org:** Pavel Ravvich (individual)
- **Date:** commit `8f5694d53550d56c8fc4f8a2cd48efc43da6de2f`, 2026-09-23 07:58:20 +0300 ("Independent benchmark of TypeSafe Jev vs cheap and frontier LLMs")
- **Retrieved:** 2026-09-28; README via WebFetch; shallow clone `repos/jev-bench`; read `results/*.json`. Code not executed.
- **Cited by evidence:** @PaulRavvich, https://x.com/PaulRavvich/status/2104124392410124517
- **Relevance to a memory stack:** low-medium. Adds an independent calibration measurement (ECE, Brier) for Jev, which bears on whether its probabilities can drive thresholds without local fitting.

## TL;DR
- 500 SMS Spam messages (71 spam; Jev noul) and 500 Banking77 test messages (77 classes; Jev choice). Jev `typesafe/jev-1.13-20260917` via OpenRouter Decisions API; GPT-6 Luna on all 500; GPT-6 Astra on the first 130 (Banking77) or 135 (spam) shared messages with minimal reasoning. LLM confidence is verbalized.
- Banking77: Jev accuracy 0.818, macro-F1 0.791, ECE 0.071; Luna 0.852 / 0.831 / 0.081; Astra 0.877 / 0.825 / 0.089 (n 130, 20 errors).
- Spam: Jev 0.980 / 0.958 / ECE 0.045 / Brier 0.0158; Luna 0.966 / 0.936 / ECE 0.0115 / Brier 0.0275; Astra 0.993 / 0.984 / ECE 0.0017 (n 135, 15 errors).
- Jev p50 about 366 to 373 ms vs LLMs about 1.65 to 2.19 s. Cost per 1,000: Jev $0.071 (Banking77) and $0.013 (spam); Luna $0.074 and $0.029; Astra $5.95 and $1.80. Whole experiment about $1.13.

## What it claims / describes
An independent head-to-head on two public classification sets, reporting accuracy, macro-F1, ECE, Brier, p50/p95 latency, cost per 1,000 calls, paired bootstrap CIs, selective accuracy and a Jev-to-frontier cascade (the cascade and CI values were not in the extracted text or the summary JSON read).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Banking77 accuracy | Jev 0.818 | Luna 0.852 (n 500); Astra 0.877 (n 130) | 77 classes | Astra subset and 20 errors |
| Banking77 macro-F1 | Jev 0.791 | Luna 0.831; Astra 0.825 | | |
| Banking77 ECE | Jev 0.071 | Luna 0.081; Astra 0.089 | | LLM confidence verbalized |
| spam accuracy | Jev 0.980 | Luna 0.966; Astra 0.993 (n 135) | 500 msgs, 71 spam | |
| spam ECE | Jev 0.045 | Luna 0.0115; Astra 0.0017 | | Jev least calibrated on spam |
| spam Brier | Jev 0.0158 | Luna 0.0275; Astra 0.0066 | | |
| latency p50 / p95 | Jev 373 / 487 ms (Banking77) | Luna 2,129 / 3,442 ms; Astra 2,181 / 3,781 ms | sequential requests from Israel | |
| cost per 1,000 | Jev $0.071 (Banking77), $0.013 (spam) | Luna $0.074, $0.029; Astra $5.95, $1.80 | OpenRouter prices | |

## Mechanism details you could implement
- Report ECE and Brier alongside accuracy for any decision component, and compare against verbalized-confidence LLMs on the same items.
- Seed and pin model versions per prediction (the repo records the exact version per row).

## Limitations, caveats, counter-evidence
- Author: "Small samples (500 / 130), one configuration per model, verbalized confidence for LLMs, sequential requests from Israel, minimal reasoning for the frontier model, public datasets that may be in training data".
- Astra comparisons are on a subset and include errors (20 and 15).
- Consistent with other Banking77 measurements already on the bus (blog-openrouter-jev-vs-opus-5-banking77.md, blog-jev-vs-llms-banking77-calibration-cascade.md): Jev somewhat below LLMs on Banking77 accuracy at far lower latency (inference from those notes' titles and this data).

## Takeaways for tuning a memory stack
- Jev's calibration is task-dependent: ECE comparable to an LLM on Banking77 but about 4x Luna's on spam. Fit thresholds locally (B14).
- For binary gates at high base rates, check Brier as well as ECE.

## Open questions
- Cascade and bootstrap CI values (in `make_tables.py` output, not read).

## Grading and labels
- Directness high; control medium; independence high; reproducibility high; applicability low-medium.
- Pillars: R4 primary (decision model accuracy and calibration), R6 secondary (small-sample, verbalized-confidence comparison). Tags: cost.
- Beliefs: supports B14 (calibration varies by task and must be measured locally). No contradiction. New relative to existing Banking77 notes: independent ECE and Brier numbers.

## Origin chain
post 2104124392410124517 (@PaulRavvich) -> repo at 8f5694d -> README and results/*.json -> this note. Independence: no shared author or harness with the OpenRouter or Towards Data Science Banking77 sources; same public dataset.
