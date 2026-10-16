---
schema_version: 1
artifact_id: N-20260929-06
artifact_type: note
producer: triage
run_id: triage-20260929T014501Z-f6b3
created_at: 2026-09-29T01:52:47Z
input_refs: [{"artifact_id": "post:2104714384698376460", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:prakashkagitha/djev
claim_cluster: github:prakashkagitha/djev
feeds: ["decision", "memory"]
primary_source: https://github.com/prakashkagitha/djev
source_commit: 88a067b5aff53ca6e34fd0fc59dd53612bab495d
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R1", "R4"]
memory_stage: none
priority: 2
tags: {"mechanism": ["deterministic-inference", "self-hosted-decision-model", "batch-invariant-kernels", "prefix-cache-alignment"], "workload": ["guardrails", "moderation", "typed-decisions"], "lifecycle_stage": ["serving"], "cross_cutting": ["replay", "cost", "latency", "self-host"]}
evidence_grade: {"directness": "high: repeat-call agreement and bitwise identity are measured directly on hosted Jev and on djev", "control": "medium: same requests byte for byte to both systems, but different models (Jev 1.13 vs Bespoke-Nimble-9B) and different repeat counts (10 vs 5)", "independence": "medium: author is not TypeSafe or Bespoke, but builds and promotes djev", "reproducibility": "medium: MIT code, tasks/ and tests/ directories, public datasets; needs one H100 and the hosted-Jev API", "applicability": "medium: replay and self-hosting are our goals, but workload is guardrails/moderation, not memory stages"}
beliefs_affected: {"supports": ["B1", "B14"], "contradicts": [], "would_create": ["Hosted Jev returns different probabilities for byte-identical requests (mean prob std about 0.01, answer flips near threshold), so a decision cannot be reproduced by re-querying hosted Jev; replay requires either retaining the served probabilities or a pinned deterministic self-hosted model"]}
claim_correction: The post says every Jev decision can be deterministic; djev makes an open-weight Jev-style model (Bespoke-Nimble-9B on SGLang) deterministic, not hosted Jev, and that model scores 87.0% on Nimble's held-out set against 93.2% reported by Bespoke for Jev 1.13, with determinism tested only for one fixed model, engine, flags and GPU model.
---

# djev: a deterministic, self-hosted Jev-compatible server (Bespoke-Nimble-9B on SGLang)

- **URL:** https://github.com/prakashkagitha/djev
- **Type:** repo
- **Author / org:** prakashkagitha (Prakash Kagitha); code, patches and results MIT (README). Built on ekzhang1's openjev-sglang; model is Bespoke Labs' Nimble.
- **Date:** head commit `88a067b5aff53ca6e34fd0fc59dd53612bab495d` (2026-09-28T23:13:03Z, "Hero animation (assets/hero): same request x15, Jev vs djev, with evidence pillars")
- **Retrieved:** 2026-09-29, commit 88a067b5aff53ca6e34fd0fc59dd53612bab495d. Commit SHA read from the GitHub commits API (shell clone not available in this session, so no local copy in repos/). Read: README.md at that commit. Code under `tasks/` and `tests/` not read.
- **Cited by evidence:** https://x.com/prakashkagitha/status/2104714384698376460 (@prakashkagitha, 2026-09-28)
- **Relevance to a memory stack:** high for R9/R1. It is the first measured evidence in our corpus that hosted Jev answers vary on identical requests, and a working path to a self-hosted, bit-reproducible decision model (priority 2).

## TL;DR
- Measured: 15 byte-identical calls to hosted Jev (`jev-1.13.0`, public API, 2026-09-28) gave "15 of 15" distinct answers (distinct probability vectors) on two tasks, with 95.0% and 97.1% agreement and mean probability std 0.0092 and 0.0099; on the insurance task the boolean `covered` came out 6 yes, 9 no. djev: 100% agreement, std 0.0000, 1 of 15.
- On 2,236 guardrail messages (XSTest, ToxicChat, in-the-wild jailbreaks, JailbreakBench), 44 messages changed action between identical hosted-Jev calls, and 15 of 954 unsafe messages got through on some calls only; djev: 0 and 0.
- Mechanism: batch-invariant (deterministic) SGLang kernels were not enough for the hybrid Qwen3.5 family ("22 of 300 repeats still drifted under load"); the fix was aligning Gated DeltaNet prefix-cache checkpoints to the 64-token chunk grid (bf16 intermediate vs fp32 running state) and aligning prefill splits for fa3.
- Cost of determinism reported as negligible: median decision 51 ms vs 50 ms, throughput 45 decisions/s at 32 concurrent in both modes, on one H100 NVL.
- Claim correction: this is determinism for an open-weight Jev-style model, not for hosted Jev; accuracy is lower (87.0% vs 93.2% reported for Jev 1.13 on Nimble's held-out set, different measurers), and "Determinism is not correctness".

## What it claims / describes
- **What djev is.** "An open, self-hosted server for TypeSafe's Jev API" (fetch summary of README) with the guarantee that the same request bytes always return the same probabilities across restarts, GPUs of the same model, and load. Request shape is Jev's `/v1/systemone` (inference from "Jev API" server; exact route not quoted in what I read).
- **Model.** Bespoke-Nimble-9B, a LoRA trained on Qwen3.5-9B and merged to BF16. Qwen3.5-9B is a hybrid architecture with Gated DeltaNet linear-attention layers interleaved with full attention. Hardware: one NVIDIA H100 NVL (94 GB), CUDA 13.
- **Why LLM-style inference is nondeterministic** (README, root cause section): "A GPU kernel's arithmetic order depends on the batch around it: how many requests share a matrix multiply, how attention splits its work, where a long prompt is cut into chunks."
- **Why SGLang's deterministic flag was not enough:** "The open Jev-style models run on the hybrid Qwen3.5/3.6 family, and there the flag was not enough: 22 of 300 repeats still drifted under load." Cause: "Gated DeltaNet carries a recurrent state computed in 64-token chunks. When SGLang caches that state partway through a prompt, it copies it from the chunk kernel's intermediate buffer, which is bf16. The running state is fp32." So resuming from cache and recomputing gave different numbers.
- **Fixes:** (1) save prefix-cache checkpoints only at 64-token grid boundaries; (2) align prefill splits for fa3 attention; (3) server design: aligned warm-up, fast paths, memo caching of exact repeats, request canonicalization (from fetch summary; details not read in code).
- **Evidence Jev itself is nondeterministic:** measured by the author through the public API on 2026-09-28 with `jev-1.13.0` (see Numbers). Whether hosted Jev uses caching, batching or sampling that causes this is not stated.
- **Limitations the README states** (verbatim): "Determinism is not correctness. djev's model misses some jailbreaks that hosted Jev catches, including TypeSafe's own 'Neurosemantical Inversitis' example." "Identical bytes, not identical meaning. Reordering options or adding an irrelevant field can change an answer." "One fingerprint at a time. Answers repeat for a fixed model, engine version, flags and GPU model. Agreement across GPU models or tensor-parallel sizes is not yet tested."

## Numbers

| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Moderation: agreement / mean prob std / distinct answers | djev "100% / 0.0000 / 1 of 15" | Hosted Jev 1.13 "95.0% / 0.0092 / 15 of 15" | 15 identical calls, README consistency table | one request; "distinct answers" appears to mean distinct probability outputs (inference) |
| Insurance claim: agreement / mean prob std / distinct answers | djev "100% / 0.0000 / 1 of 15" | Hosted Jev 1.13 "97.1% / 0.0099 / 15 of 15 (`covered`: 6 yes, 9 no)" | 15 identical calls | one request, apparently near the decision boundary (inference) |
| Messages whose action changed between identical calls | djev 0 | Hosted Jev 1.13: 44 | 2,236 messages (XSTest, ToxicChat, in-the-wild jailbreaks, JailbreakBench); "sent byte for byte 10 times to hosted Jev and 5 times to djev" | unequal repeat counts favour djev (fewer chances to flip) |
| Unsafe messages that got through on some calls only | djev 0 | Hosted Jev: "15 of 954" | same | |
| Unsafe caught / safe wrongly flagged | djev 74.4% / 10.3% | Hosted Jev 68.4% / 10.6% | same, "Strict policy" | single policy |
| Nimble held-out accuracy | 87.0% (djev model) | "Bespoke reports 93.2% for Jev 1.13" | Nimble held-out set (`tasks/nimble_holdout`) | different measurers; n not stated in what I read |
| Engine probe bit-identical repeats (prefill split fix) | "278/300 to 300/300" and "700/720; with it, 720/720" | SGLang deterministic flag alone: "22 of 300 repeats still drifted under load" | engine probes | |
| Median decision latency | 51 ms | 50 ms, SGLang default mode | one H100 NVL | |
| Throughput | 45 decisions/s at 32 concurrent | "the same in both modes" | one H100 NVL | exact repeats from memo cache: 344 decisions/s (fetch summary) |
| Guard call (five questions) | about 20/s per H100; median 122 ms | 121 ms default mode | | |

## Mechanism details you could implement
- For any self-hosted Qwen3.5/3.6-based decision model (Laya ports, Nimble, Jeff and similar are on this family per our queue), deterministic kernels alone are insufficient; check prefix-cache checkpoint alignment for linear-attention (Gated DeltaNet) state. Probe: send N byte-identical requests under concurrent load and count bit-identical outputs (the README's 300 and 720 probes).
- Canonicalize requests (ordering, whitespace) before calling, because "Reordering options or adding an irrelevant field can change an answer". For memory stages this means fixing candidate order (e.g., sort by id) in rerank choice calls if replay matters (inference).
- Record a "fingerprint" (model, engine version, flags, GPU model) with each decision; determinism holds only within one fingerprint.
- Memo-cache exact repeats (344/s vs 45/s).

## Limitations, caveats, counter-evidence
- Different models compared: hosted Jev 1.13 vs Bespoke-Nimble-9B. djev is less accurate on Nimble's held-out set and misses some jailbreaks hosted Jev catches.
- Hosted-Jev nondeterminism was measured on one day (2026-09-28) on one version; the two single-request consistency tests are n=1 request each x 15 calls.
- Repeat counts differ (10 vs 5), which biases flip counts in djev's favour; djev's 0 would likely still hold since outputs are bit-identical (inference).
- Cross-GPU-model and tensor-parallel determinism "not yet tested".
- Author-run; no independent replication. I did not read the task scripts.

## Takeaways for tuning a memory stack
- Treat hosted Jev as nondeterministic: a threshold decision within about 0.01 to 0.03 of a threshold can flip on re-query (std about 0.01 measured). For replay (R1), store the served probabilities with each memory decision rather than planning to re-execute (supports B1).
- Local threshold fitting (B14) should use the mean of a few repeats or add a hysteresis band around thresholds; an evaluation that runs once per item on hosted Jev has run-to-run noise even at fixed inputs (inference).
- A self-hosted deterministic model is achievable at near-zero latency cost on one H100, but at an accuracy cost versus hosted Jev on the one benchmark reported; any switch must be evaluated on our own decisions.

## Open questions
- How many of our memory-stage decisions sit within the hosted-Jev jitter band of their thresholds?
- Does determinism hold across A100 vs H100, or MLX/GGUF ports? Not tested.
- Nimble held-out n and the gap on memory-type questions (write gate, rerank) are not stated.
- Does hosted Jev's variation come from batching or from model updates behind `jev-1.13.0`? Not stated.

## Grading and labels
- Directness: high, repeat-call agreement and bit-identity measured directly.
- Control: medium, same request bytes to both systems, but different models and repeat counts.
- Independence: medium, third-party to TypeSafe and Bespoke, but the author ships djev.
- Reproducibility: medium, MIT code and public datasets; needs an H100 and a Jev key.
- Applicability: medium, replay and self-hosting match priority 2; workload is guardrails, not memory.
- Strength: repo-pinned.
- Pillars: R9 primary; R1, R4 secondary.
- Memory stage: none (serving property across all stages).
- Tags: deterministic-inference, self-hosted-decision-model, prefix-cache-alignment; replay, latency, self-host.
- Beliefs: supports B1 (re-query is not a replay path for hosted Jev, retention of served outputs is needed), supports B14 (probabilities jitter on identical input, thresholds need local handling); would create a belief on hosted-Jev re-query nondeterminism.

## Origin chain
- post https://x.com/prakashkagitha/status/2104714384698376460 -> https://github.com/prakashkagitha/djev @ 88a067b5aff53ca6e34fd0fc59dd53612bab495d -> README.md (consistency table, guardrails table, root-cause section, latency section, limitations).
- Independence: the post and repo are by the same author. Hosted-Jev numbers are the author's measurements, not TypeSafe's. Nimble 93.2% for Jev 1.13 is quoted from Bespoke.
