---
schema_version: 1
artifact_id: N-SURVEY-20261011-03
artifact_type: note
producer: triage
run_id: survey-20261011T054529Z-bcaa
created_at: 2026-10-11T06:50:00Z
idempotency_key: note:survey:github:instax-dutta/sysone-bench
input_refs: []
pillar_primary: R9
pillar_secondary: [R6]
memory_stage: evaluation
priority: 2
beliefs_affected: {supports: [], contradicts: []}
evidence: {directness: 4, control: 4, independence: 4, reproducibility: 4, applicability: 2}
strength: repo-pinned
source_url: https://huggingface.co/convaiinnovations/laya/discussions/20
found_via: survey
answers_watch_request: null
---

# Independent sealed head-to-head: Laya 0.3.11 0.686 vs Jev 1.13.0 0.907 vs Qwen2.5-1.5B constrained decoding 0.605 (sysone-bench)

- **URL:** https://huggingface.co/convaiinnovations/laya/discussions/20 ; repo github.com/instax-dutta/sysone-bench, report `results/v2/report-20260926/REPORT.md` ; write-up github.com/NandhaKishorM/laya/issues/555
- **Type:** builder writeup with pinned code
- **Author / org:** saidutta69 (Hugging Face), no affiliation with Laya or TypeSafe stated
- **Date:** about 2026-09-26
- **Retrieved:** 2026-10-11
- **Relevance to a memory stack:** medium. The best-controlled Laya vs Jev comparison found: same inputs, paired bootstrap, multiple-comparison correction, CPU-only open model.

## TL;DR
- 1,190 sealed cases (digests published, verified before and inside the container), 9 suites, scored split 952 cases / 1,240 decisions, seed 42, same order for every model.
- Overall accuracy: laya 0.6863, Jev 0.9065, Qwen2.5-1.5B PCD 0.6048.
- Jev beats laya on 8 of 9 suites after Holm correction; triage (+0.0573, Holm p 0.0627) not claimed.
- Calibration close for all three (choice ECE 0.0009 to 0.0028). Latency p50/p95: Jev 314/387 ms (network), laya 588/1,364 ms (4 CPUs), PCD 3,948/13,471 ms.

## Numbers (verbatim)

| Suite | n | laya | Jev | Qwen PCD | Jev minus laya | 95% CI | Holm p |
|---|---|---|---|---|---|---|---|
| triage | 192 | 0.8750 | 0.9323 | 0.7812 | +0.0573 | [+0.0052, +0.1094] | 0.0627 |
| guardrails | 96 | 0.7604 | 1.0000 | 0.2917 | +0.2396 | [+0.1562, +0.3229] | 0.0004 |
| moderation | 144 | 0.7569 | 0.9444 | 0.7292 | +0.1875 | [+0.1250, +0.2500] | 0.0004 |
| agnews | 160 | 0.8500 | 0.9875 | 0.9125 | +0.1375 | [+0.0813, +0.1938] | 0.0004 |
| emotion | 192 | 0.6562 | 0.8438 | 0.4115 | +0.1875 | [+0.1198, +0.2552] | 0.0004 |
| banking77 (12 intents) | 96 | 0.8125 | 0.9479 | 0.5833 | +0.1354 | [+0.0625, +0.2188] | 0.0051 |
| mnli | 120 | 0.5583 | 0.8667 | 0.3417 | +0.3083 | [+0.2083, +0.4083] | 0.0004 |
| sst5 | 120 | 0.3333 | 0.6500 | 0.5250 | +0.3167 | [+0.2083, +0.4250] | 0.0004 |
| multilingual intent (EN checkpoint) | 120 | 0.4500 | 1.0000 | 0.6833 | +0.5500 | [+0.4583, +0.6417] | 0.0004 |
| All | 1,240 | 0.6863 | 0.9065 | 0.6048 | | | |

Intervals: 20,000-replicate state-cluster bootstrap; p from 20,000 permutations, Holm across nine suites. Hardware: CPU only, 4 CPUs, 12 GB cap. laya weights commit 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851.

## Mechanism details you could implement
- The harness pattern itself: sealed manifest with byte digests, per-run `summary.json`, report that "regenerates byte-identically", fail closed if model revision cannot be resolved. Reusable for our own Jev vs open-weight runs.
- Adapter findings: laya exposes no revision attribute; probabilities rounded to 4 decimals (sum 0.9999); extra fields (`action`, `legend`, `confidence`) to project away.

## Limitations, caveats, counter-evidence
- Gold labels: one reviewer corrected AI-drafted answers; `"independent_human_review": false`, `"adjudication": false`. The author warns against comparing with outcome-graded evaluations.
- Laya multilingual, typed-decisions and Router checkpoints not tested; multilingual row is the English checkpoint on non-English text.
- Generic classification suites, not memory decisions (inference).
- Laya's own published claim (typed-decisions checkpoint 0.766 vs Jev 0.727) was seen only in search snippets; per the snippet the 0.766 is fine-tuned on the benchmark's training split and zero-shot base is 0.362. Not fetched.

## Takeaways for tuning a memory stack
- Laya zero-shot is not a substitute for Jev on wide label sets; if we want an in-house model, start from Kev 9B or Clef-flash (N-SURVEY-20261011-02) or fine-tune.
- Copy the sealed-manifest discipline for our own comparison.

## Open questions
- Laya after fine-tuning on our own decisions: the gap to close is 0.22 overall.
