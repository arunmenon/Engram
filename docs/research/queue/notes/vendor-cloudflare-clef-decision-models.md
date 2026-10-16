---
schema_version: 1
artifact_id: N-SURVEY-20261011-01
artifact_type: note
producer: triage
run_id: survey-20261011T054529Z-bcaa
created_at: 2026-10-11T06:40:00Z
idempotency_key: note:survey:hf:Cloudflare/clef-flash
input_refs: []
pillar_primary: R9
pillar_secondary: [R4]
memory_stage: none
priority: 2
beliefs_affected: {supports: [], contradicts: []}
evidence: {directness: 3, control: 2, independence: 1, reproducibility: 4, applicability: 3}
strength: vendor-benchmark
source_url: https://huggingface.co/Cloudflare/clef-flash
found_via: survey
answers_watch_request: null
---

# Clef and Clef-flash (Cloudflare): open-weight, Jev-compatible decision models, 27B and 9B, Apache 2.0

- **URL:** https://huggingface.co/Cloudflare/clef-flash ; launch post https://blog.cloudflare.com/clef-decision-models/ (datePublished 2026-10-01)
- **Type:** job/lab page (model card) plus vendor blog
- **Author / org:** Cloudflare
- **Date:** 2026-10-01
- **Retrieved:** 2026-10-11
- **Cited by evidence:** survey, R9 roster duty
- **Relevance to a memory stack:** high. The first open-weight System One model from a large infrastructure vendor, API-compatible with Jev, with a fine-tuning service. Directly serves priority 2 (run our own, keep memory text in-house).

## TL;DR
- Clef = frozen Qwen3.8-27B backbone plus a "small transformer head" that scores all options jointly; Clef-flash = same on Qwen3.5-9B. Apache 2.0, weights on Hugging Face, also hosted on Workers AI (`@cf/cloudflare/clef`, `@cf/cloudflare/clef-flash`).
- Interface is Jev's: `state` plus typed `questions` (`noul`, `choice`, `score`), returns "one logit per allowed option for each question". "There is no free-form text generation and no output parsing." Served at `/v1/systemone` via SGLang.
- Vendor's own Decision Index 0.2.1 run: Clef or Clef-flash top most rows; Jev leads on GPQA Diamond, MMLU-Pro, BBH, HoVer, When2Call, BRIGHT, ANLI, VAST, NLI4CT.
- Vendor latency: median 209.3 ms (Clef), 38.8 ms (Clef-flash), 524.1 ms (Jev). An independent run (N-SURVEY-20261011-02) measured Clef 27B at 0.50 s p50 on Workers AI and worse calibration than Jev.
- Training data not public ("our own internal synthetic datasets permutating field orders, prompts, and schema structures").

## What it claims / describes
Post-training of a frozen multimodal backbone with a joint option-scoring head. Training used a Brier loss "to refine probability calibration" and an RL objective called RLCD with "a reference penalty and partial credit for adjacent ordinal choices". Inputs: text, JSON, images, video. Clef context 64k (Jev 32k per the blog); Clef-flash context not stated; `encode_record` default `max_length` 16,384 tokens with `max_state_tokens`. Tested "with torch 2.11 and transformers 5.10.2 on a single H200"; SGLang recipes for H200, B200, B300. An RL fine-tuning service launches as a hands-on engagement with Cloudflare forward-deployed engineers; the goal is to "capture data, fine-tune, and redeploy the model, all on Cloudflare". Whether fine-tuned weights can be exported is not stated.

## Numbers (vendor internal run, Decision Index 0.2.1 suite; selected rows quoted verbatim from the card)

| Benchmark | Clef | Clef-flash | Jev | Kev 9B | Laya |
|---|---|---|---|---|---|
| BFCL (case exact) | 98.5 | 98.8 | 95.8 | 94.5 | 38.1 |
| ToolRet (nDCG@10) | 69.2 | 66.4 | 65.3 | 64.3 | 12.8 |
| BANKING77 (macro-F1) | 94.2 | 90.9 | 79.7 | 84.8 | 14.3 |
| CLINC150+OOS (macro-F1) | 97.4 | 66.8 | 89.3 | 79.0 | 3.2 |
| RouterBench (selected quality) | 79.7 | 79.9 | 79.9 | 80.0 | 57.1 |
| ContractNLI (macro-F1) | 81.4 | 84.3 | 71.7 | 57.8 | 29.0 |
| ANLI (macro-F1) | 69.8 | 59.1 | 74.8 | 56.3 | 48.7 |
| BRIGHT (nDCG@10) | 45.9 | 39.3 | 47.5 | 38.5 | 19.9 |
| RAGTruth (hallucination F1) | 79.4 | 35.6 | 76.5 | 46.2 | 48.8 |
| HoVer (accuracy) | 65.2 | 61.2 | 72.9 | 58.8 | 55.8 |
| When2Call MCQ | 72.4 | 65.6 | 81.0 | 49.6 | 11.9 |
| CRUXEval | 86.7 | 86.1 | 73.0 | 51.2 | 40.2 |
| Median latency (ms) | 209.3 | 38.8 | 524.1 | 51.4 | 5.8 |
| p95 latency (ms) | 238.6 | 122.4 | 536.0 | 187.9 | 222.5 |

Workflow evals (Typesafe Evals, "scored against consensus reference labels"): invoice exact actions Clef 64.7 / Clef-flash 57.1 / Jev 61.8; customer service 76.3 / 77.0 / 76.0; security incidents 62.9 / 61.7 / 61.7; agent trace observability primary action 68.5 / 69.8 / 71.6.

Hardware: VRAM not stated on the card or blog. Press reports (The Register via secondary sites, not fetched) quote 85 GB for Clef and 41 GB for Clef-flash from a Cloudflare PM. Pricing on the Arize benchmark page: Clef 27B $0.24 per M tokens on Workers AI.

## Mechanism details you could implement
- Drop-in for code already calling Jev: same question types and `/v1/systemone` path, so an A/B is an endpoint swap (inference).
- Self-host Clef-flash on one large GPU; memory text never leaves our hardware.
- Fit thresholds locally; the vendor reports no ECE despite the calibration claim.

## Limitations, caveats, counter-evidence
- Every number is a vendor internal run; not reproduced on the official Decision Index (stated by press and Gradually.ai).
- The Laya column (BFCL 38.1, CLINC 3.2) is far below what an independent sealed run measured for Laya (N-SURVEY-20261011-03), so the vendor's adapter for competitors may be weak (inference).
- Clef-flash collapses on some rows (CLINC150+OOS 66.8, RAGTruth 35.6), so "9B is enough" is task-dependent.
- Training data not released; "open-source" in Cloudflare's wording means open weights.
- Independent latency on Workers AI (0.50 s p50) disagrees with the vendor's 209.3 ms; calibration 0.062 vs Jev 0.023 (N-SURVEY-20261011-02).

## Takeaways for tuning a memory stack
- Add Clef-flash (self-hosted) and Clef (Workers AI) to any Jev comparison on our own link and admission decisions.
- Do not take the vendor's competitor columns as baselines.

## Open questions
- VRAM and throughput on hardware we own; quantised variants; whether the RL fine-tune can be done off-Cloudflare with the released head.
