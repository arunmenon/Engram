---
schema_version: 1
artifact_id: N-20261010-04
artifact_type: note
producer: triage
run_id: triage-20261010T014501Z-4cec
created_at: 2026-10-10T01:54:06Z
input_refs: [{"artifact_id": "post:2102810316497371268", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x-article:2102806912278339584
claim_cluster: x-article:2102806912278339584
feeds: ["decision"]
primary_source: https://x.com/i/article/2102806912278339584
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4", "R8"]
memory_stage: safety
priority: 2
tags: {"mechanism": ["logprob-readout", "temperature-scaling", "option-rotation", "fine-tuned-encoder", "confirm-gate"], "workload": ["network-management-agent", "edge-device"], "lifecycle_stage": ["act"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: measured accuracy, ECE, AUROC and latency per backend", "control": "high: identical held-out rows across backends, grouped folds, out-of-fold temperature", "independence": "high: no vendor tie; uses open Laya, openJev-verdict, open-jev-deberta", "reproducibility": "low: library jevlet mentioned but no link found; authored rows LLM-generated, human review pending", "applicability": "high: calibrated yes/no gate beside a generative agent, self-hosted, our exact open-weight question"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["Zero-shot open-weight Jev reproductions are not usable as gates on a 24-option domain catalog; a fine-tuned 150M encoder beats a 4B logprob readout as router but cannot learn exact-match gating"]}
claim_correction: none
---

# Serving the Jev interface locally: typed, calibrated decisions beside a 4B agent on a Qualcomm NPU (@imdasein), with Laya and open Jev reproductions

- **URL:** https://x.com/i/article/2102806912278339584 (post https://x.com/imdasein/status/2102810316497371268)
- **Type:** X article (first-hand experiment write-up)
- **Author / org:** @imdasein (independent builder)
- **Date:** 2026-09-23
- **Retrieved:** 2026-10-10 via the fxtwitter mirror API; article text as served
- **Cited by evidence:** https://x.com/imdasein/status/2102810316497371268 (@imdasein)
- **Relevance to a memory stack:** high for priority 2. A careful, self-hosted comparison of four ways to serve Jev-style typed decisions (LLM logprob readout, zero-shot open encoders including Laya, a fine-tuned 150M encoder, rules), with calibration measured on the builder's own labelled rows.

## TL;DR
- Zero-shot open Jev clones do not transfer to a 23-command catalog: best gate AUROC 0.76 (Laya English), and Laya typed-decisions accepted 101 of 156 dangerous swaps; openJev-verdict-2.0 collapses to one label above about six options (command 0.0%).
- A 4B (Qwen3-4B) next-token logprob readout gives a strong gate (AUROC 0.952 on 939 pairs; ECE 0.108 to 0.030 after temperature scaling) but raw confidences are dangerous: 23 of 40 command errors sat above 0.9.
- ModernBERT-base fine-tuned with the typed-decisions recipe (round 2, shuffled question order, 8 epochs) beats the 4B readout as a router on identical held-out rows (command 77.8% vs 69.8%) at 126 ms per yes/no on CPU, but fails to learn the gate (AUROC 0.53 to 0.65).
- Prompt wording moved raw P(yes) on correct proposals from 0.21 to 0.82; "If you did not fit the threshold on your own labeled rows, you do not have one."

## What it claims / describes
Workload: a network-management assistant on a Qualcomm QCS9075 board; Qwen3-4B-Instruct-2507 (4-bit, NPU) picks a tool and parameters; a human confirms every write. The paraphrase accuracy is 77%. The study adds a typed decision layer: a router battery (tool 8-way, command 24-way, is_write, touches_poe_power) and a gate battery (does the proposed call match the request). Evaluation set: 65 canonical + 195 paraphrases + 259 authored rows (81 adversarial confusables, 54 symptom-first, 76 out-of-scope, 48 other-tool), splits grouped by seed request; authored rows LLM-generated and LLM-verified, "human review is pending". Backends: (1) llama-server next-token logprob readout with 3 option rotations averaged; (2) zero-shot openJev-verdict-2.0 (151M), Laya (421M, two checkpoints), open-jev-deberta-v3-large, NLI DeBERTa baseline; (3) fine-tuned ModernBERT-base; (4) rules.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| text-label tool choice on production path | 88.7% | model's own tool call 93.3% | 195 paraphrases, on board | negative: routing through same model buys nothing |
| readout command 24-way accuracy | 84.6%; ECE 0.133 to 0.070; confident errors 23 to 12 of 40 | | 260 eval requests | temperature about 3.4 out-of-fold |
| readout gate AUROC | 0.952; ECE 0.108 to 0.030 | | 939 pairs | dangerous swaps accepted 1 of 156 |
| gate on real confusions at p<0.5 | flags 15 of 20; false-flags 30 of 151 correct | | real generative calls | product trade-off |
| Laya English, gate AUROC | 0.76 | readout 0.952 | 939 pairs, zero-shot | flags 1 of 20 real confusions at 0.5 |
| Laya typed-decisions | tool 61.7%, command 51.4%, is_write 81.1%, AUROC 0.73 | | 519 rows | |
| openJev-verdict-2.0 command | 0.0% | | 260 rows | collapses above about 6 options |
| fine-tuned encoder r2 vs 4B readout, command | 77.8% vs 69.8% | r1 65.1% | 126 held-out rows | identical rows |
| fine-tuned encoder gate AUROC | 0.53 to 0.65 | 4B readout 0.95; Qwen3.5-0.8B 0.88 | held-out pairs | balanced model accepts 79% of wrong-port proposals |
| latency on board CPU | encoder 126 ms per yes/no; 4B readout 1.24 s per question, gate 3.1 s | Laya 352 ms per NOUL | QCS9075 Kryo CPU | co-tenancy with NPU agent "free" |

## Mechanism details you could implement
- Logprob readout: question, option legend with single-token labels and answer format as a fixed system prompt (prefix-cached); state as user message; read first-token distribution; average 3 cyclic option rotations.
- Fit one temperature out-of-fold with folds grouped by seed (paraphrases leak across folds otherwise).
- Fine-tune recipe: state, instructions, options packed; span-mean head; cross-entropy plus Brier; shuffle question order in training (span heads are position-aware: 65% vs 78%).
- Split by role: encoder for per-turn router (ms), decoder readout for per-write gate (seconds).
- Ask hierarchically when options exceed about six for zero-shot encoders.

## Limitations, caveats, counter-evidence
- Single builder, single domain; authored rows not human-reviewed.
- Code and data said to be published but no link was in the article text we read.
- Jev itself not run (cloud-only; board offline); comparisons are to open reproductions.

## Takeaways for tuning a memory stack
- For self-hosting (priority 2), do not expect off-the-shelf Laya or openJev ports to work zero-shot on our catalogs; budget for fine-tuning on our own decisions.
- Treat any confidence as uncalibrated until fitted on our labels; this is direct support for B14.
- Exact-match checks (does the memory cite this id, this value) may need a decoder readout, not a small encoder.

## Open questions
- Would Jev (hosted) do better zero-shot on the 24-way catalog?
- Repository link for jevlet and data.

## Grading and labels
- Directness high, control high, independence high, reproducibility low, applicability high.
- Pillar R9, secondary R4, R8. Stage: safety (pre-write gate). Priority 2.
- B14 supports: raw confidences badly miscalibrated until locally fitted; wording moves P(yes) 0.21 to 0.82.
- Would create: zero-shot open reproductions fail on large catalogs; fine-tuned small encoder routes well but does not gate.

## Origin chain
post 2102810316497371268 (@imdasein) -> X article 2102806912278339584, Results 1 to 8 -> this note. Independence: uses public checkpoints (heman10x/rlcd-modernbert-151m, convaiinnovations/laya, com-kotobalabs/open-jev-deberta-v3-large); no shared authors with other notes.
