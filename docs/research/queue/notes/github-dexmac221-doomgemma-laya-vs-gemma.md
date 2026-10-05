---
schema_version: 1
artifact_id: N-20260928-22
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:07:08Z
input_refs: [{"artifact_id": "post:2104542537117564990", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:dexmac221/doomgemma
claim_cluster: github:dexmac221/doomgemma
feeds: ["decision"]
primary_source: https://github.com/dexmac221/doomgemma
source_commit: cdf2d040ea9ad2756f35a6daf3adf5f230a45ce4
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4", "R6"]
memory_stage: none
priority: 2
tags: {"mechanism": ["lora-fine-tune", "grammar-constrained-single-token-choice", "logprob-option-probabilities", "temperature-scaling", "system-one-encoder"], "workload": ["game-agent-action-choice", "multiple-choice-decision"], "lifecycle_stage": ["decide"], "cross_cutting": ["calibration", "latency", "self-host", "open-weight", "same-labels-comparison"]}
evidence_grade: {"directness": "medium: same-labels comparison of an open-weight System One model (Laya v3) and a LoRA-tuned Gemma on a typed multiple-choice decision, but a Doom game, not memory", "control": "medium: same 979 training labels, same 130 validation questions, same executor, same GPU for latency, oracle reference player; one training run per model, Laya not re-tuned", "independence": "medium: third party to both Laya and Gemma, but the author built the Gemma side", "reproducibility": "high: scripts, patch, per-game jsonl, calibration and latency json, adapters on Hugging Face, pinned commits", "applicability": "low: game control on a training map, not memory decisions; latency not stressed at 0.5 s cadence"}
beliefs_affected: {"supports": ["B14"], "contradicts": ["B12"], "would_create": ["On the same labels, a 27-minute LoRA on a small open LLM (Gemma 4 E2B) matches a task-tuned System One encoder (Laya v3) on outcome and beats it on single-decision accuracy and ECE; the System One architecture showed no intrinsic latency advantage at equal size"]}
claim_correction: "Over six seeds" means six game seeds (48-53) played by one trained model each (LoRA seed 771, trained once), not six training seeds; "better calibrated" is ECE 0.04 vs 0.06 on 130 questions (65 per fold); "~3x faster" is p50 23 ms vs 59 ms (llama.cpp) or 84 ms (direct) on an RTX 4070; Jev numbers are quoted from doomLaya, not reproduced.
---

# doomGemma: Laya v3 (open-weight System One) vs Gemma 4 E2B with LoRA on the same 979 Doom decisions

- **URL:** https://github.com/dexmac221/doomgemma
- **Type:** repo (with a Medium article, not read: HTTP 403)
- **Author / org:** dexmac221 (dexmac); code Apache-2.0; Gemma under the Gemma Terms of Use
- **Date:** measurements "25 September 2026" (docs/RESULTS.md line 3); commit `cdf2d040ea9ad2756f35a6daf3adf5f230a45ce4`, 2026-09-25 14:25:35 +0200, "Translate everything to English"
- **Retrieved:** 2026-09-28, shallow clone at repos/doomgemma. Read: README.md, docs/RESULTS.md, results/games_map01.jsonl, results/calibration_gemma4-e2b-lora.json, results/calibration_laya-v3.json, results/validation.json. Article https://medium.com/towards-artificial-intelligence/laya-vs-gemma-who-wins-the-doom-game-18d3b30f303b returned 403; not read.
- **Cited by evidence:** https://x.com/dexmac221/status/2104542537117564990 (@dexmac221, 2026-09-28)
- **Relevance to a memory stack:** medium. It is the cleanest same-labels comparison we have of an open-weight System One model (Laya) against a LoRA-tuned small generative LLM, with calibration, latency on equal hardware and outcome in a loop: the exact comparison CTO priority 2 asks us to run on our own decisions. The workload is not memory.

## TL;DR
- Same 979 training labels and 130 validation questions as Laya v3 (from azalio/doomLaya), same FreeDoom agent and executor. Gemma 4 E2B + LoRA (rank 16, 27 minutes as 3 epochs x 550 s, best epoch 2) reaches 0.98 validation accuracy vs Laya v3 0.82, and exits MAP01 6/6 vs 6/6 over game seeds 48-53 (mean 60.0 s vs 59.5 s).
- Calibration (15-bin ECE, 130 questions): doomGemma raw 0.04 vs Laya v3 raw 0.06; zero-shot Gemma E2B 0.38 ("probability 1.00 even when wrong").
- Latency on one RTX 4070: Laya v3 p50 23 ms; Gemma 3 270M + LoRA direct PyTorch 22 ms (as fast, but exits only 2/6); doomGemma E2B 59 ms via llama.cpp Q8_0 or 84 ms direct bf16. "At equal in-game result Laya is still about 3x faster."
- Claim correction: "six seeds" are game seeds of one trained model, not training seeds; ECE gap is on 130 questions; Jev figures (MAP01 seed 48 exit 69.0 s, 357 ms) are quoted from doomLaya, not reproduced.
- Single-question accuracy did not predict play: the 270M adapter scores 0.93 but the executor rejects its commands 60% of the time and it exits 2/6. Generalisation is unmeasurable: on MAP02 nobody exits, including the rule-based teacher.

## What it claims / describes
Question (docs/RESULTS.md section 1): does Laya's advantage come from the System One architecture or from being a small model trained on the task, and does a generic LLM trained on the same data do as well?

Setup (section 3): the agent turns game state into text and asks two multiple-choice questions, `command` (shoot enemy #N, pick up item #N, open the door, exit, retreat, explore, wait) and `weapon`. The executor aims, paths and presses buttons; "All choices belong to the model." Requests are asynchronous, at most every 0.5 s; the game does not wait for the model.

LLM bridge (`src/serve_llm.py`): same `/predict` API as Laya's server. "Each option becomes a letter, and a grammar allows a single token among the valid letters. Probabilities come from `top_logprobs`, renormalised over the options. It is single-pass scoring (prompt prefill plus one token), not free generation: no parsing errors."

Training (section 4): data `training/v3/train.json` (979) and `validation.json` (130), "the same as Laya v3"; game seeds 42 and 43 for training, 44 for validation, all MAP01; labels "assigned offline by game rules". LoRA rank 16, alpha 32, dropout 0.05, on q,k,v,o,gate,up,down; AdamW lr 1e-4, weight decay 0.01, accumulation 8, clip 1, seed 771; "loss on the answer letter only"; best epoch by validation kept. Deployment: merge, GGUF, Q8_0 (E2B 4.9 GB, 270M 292 MB). Laya v3 is azalio's published checkpoint, not retrained.

Hardware (section 3): Ryzen 5 5600X, RTX 4070 12 GB + RTX 2070 SUPER 8 GB, Ubuntu 24.04; "All comparable latencies measured on the 4070." Software pinned: doomLaya `b25edd3`, laya `42626c3`, llama.cpp `7077abbe1`, checkpoint hashes checked against SHA256SUMS.

## Numbers

| metric | value | baseline | setup with n | caveat |
|---|---|---|---|---|
| validation accuracy total (command / weapon) | doomGemma 0.98 (0.96 / 1.00) | Laya v3 0.82 (0.725 / 0.98) | 130 questions (80 command, 50 weapon); RESULTS.md 5.1; validation.json 0.9769 vs 0.8231 | labels from a rule-based teacher, MAP01 only |
| validation accuracy, others | doom-270M 0.93; Gemma E2B zero-shot 0.62; Laya base 0.48; Laya typed-decisions 0.48; Gemma 3 270M zero-shot 0.11 | | same | |
| raw ECE / tuned ECE | doomGemma 0.04 / 0.03 | Laya v3 0.06 / 0.11 | 15-bin ECE on max confidence, temperature by 2-fold CV on the 130 (RESULTS.md 5.2; json: 0.0431 vs 0.0601 raw) | "With 65 questions per half this is statistical noise" (on Laya's tuned ECE rising) |
| raw Brier | doomGemma 0.05 | Laya v3 0.26 | same | multi-class Brier |
| raw ECE zero-shot | Gemma E2B 0.38 (T 4.3-4.6); Laya base 0.085; Laya typed-decisions 0.24 | | same | Laya base low ECE from "low, uniform confidences"; contradicts Convai card "ships over-confident (mean ECE 0.466)" |
| MAP01 exits, game seeds 48-53 | doomGemma 6/6, mean 60.0 s (56.6-64.2) | Laya v3 6/6, mean 59.5 s (42.9-71.0); oracle 6/6, 81.6 s; doom-270M 2/6 | one game per seed per player, skill 3, 180 s limit (RESULTS.md 5.4) | seed 48 not in training data; 49-53 in neither; one trained model per arm |
| per-seed exit s, doomGemma (48..53) | 56.629, 58.0, 63.143, 64.171, 57.314, 60.743 | Laya v3: 71.029, 71.029, 47.371, 54.914, 42.914, 70.0 | results/games_map01.jsonl | Laya seeds 48 and 49 have identical exit_s 71.029 with different kills (15 vs 14) (observation, not explained) |
| latency p50 / p90 / p99 | Laya v3 own server 23 / 24 / 25 ms | doom-270M direct 22 / 23 / 24; doomGemma llama.cpp 59 / 109 / 118; doomGemma direct bf16 84 / 87 / 100 | 1,416 replayed game packets, 10 warm-up, RTX 4070 (RESULTS.md 5.3) | llama.cpp latency bimodal from prompt-cache reuse |
| decisions/s | Laya v3 41.8 | doom-270M direct 44.7; doomGemma 14.1 (llama.cpp), 12.0 (direct) | same | |
| in-game latency p50 | doomGemma 98.63-108.56 ms | Laya v3 37.48-38.41 ms (on the 2070S) | games_map01.jsonl | different GPUs in play |
| executor rejection ("rails") MAP01 | doomGemma 22% | Laya v3 13%; oracle 20.5%; doom-270M 60% | telemetry, RESULTS.md 5.6 | |
| MAP02 exits | 0/3 for every player including oracle | | 3 seeds, 300 s | yellow-key door (linedef special 27) makes the chain fail |
| LoRA training | 24.2M trained params, 550 s/epoch, best epoch 2 of 3, adapter 97 MB | 270M: 3.8M, 101 s/epoch, 5 of 5, 15 MB | RTX 4070 | "27-min" = 3 x 550 s (inference from the table) |
| Jev 1.13, MAP01 seed 48 | exit 69.0 s, 13 kills, 357 ms | | "doomLaya's figure, not reproduced" | paid API not re-run |

## Mechanism details you could implement
- Turn any small generative LLM into a typed choice model: map options to letters, constrain decoding with a grammar to one token among valid letters, read `top_logprobs`, renormalise over options (serve_llm.py). The bridge reads only the top 20 logprobs; options outside get 1e-4 (RESULTS.md section 7).
- LoRA recipe that matched Laya on 979 labels: rank 16, alpha 32, dropout 0.05, all attention and MLP projections, lr 1e-4, loss on the answer letter only, keep the best epoch by validation. 27 minutes on one consumer GPU.
- Calibration protocol: 15-bin ECE on max confidence plus multi-class Brier; fit temperature with 2-fold CV on the validation set so no number is measured on the data it was fitted on (calibrate.py).
- Latency protocol: replay recorded real request packets in sequence with 10 warm-ups, on one GPU, and report p50/p90/p99; beware prompt-cache effects that make a model look faster.
- Always run the label source (the rule-based teacher) through the same loop as a reference player; it exposed that MAP02 failure was the chain, not the models.

## Limitations, caveats, counter-evidence
- README "Limitations": training and validation on MAP01 only; 130-question validation set; labels from a rule-based teacher; "Laya v3 was trained by its authors with a different recipe and was not re-tuned here"; "Jev numbers are quoted from doomLaya and not reproduced"; Gemma 3 270M from an unsloth mirror.
- One training run per model (LoRA seed 771); the six "seeds" are game seeds. No variance over training seeds (inference: the tie could shift with a different LoRA seed or a re-tuned Laya).
- The bench does not stress latency: "The game asks for a decision every 0.5 s" (README finding 2).
- The "direct" 270M latency uses the author's own PyTorch script; Laya goes through its HTTP server, so "the comparison is conservative in Laya's favour" (section 7).
- Task is game action choice with 7 command options, far from memory decisions over long engineering artifacts (inference).
- Medium article not read (403); the note rests on the repo, which the post calls "Code and models".
- No instructions aimed at AI agents found in the files read.

## Takeaways for tuning a memory stack
- For CTO priority 2, the doomGemma protocol is a ready template: same labels, same validation set, same GPU, report accuracy, ECE/Brier with CV temperature, p50/p90/p99, and an end-to-end outcome metric.
- Expect task data to dominate architecture: with about 1k labelled decisions, a LoRA on a 2B-effective open LLM can match or beat a task-tuned System One encoder on accuracy and calibration. The cost is size (4.9 GB vs under 1 GB) and 2.5 to 3.7x latency.
- Zero-shot LLM probabilities are over-confident (ECE 0.38, T about 4.4); do not threshold them without fitting temperature.
- Per-decision accuracy can mislead: measure the downstream outcome (here exits; for memory, answer quality or wrong-memory rate).

## Open questions
- Does the tie hold across LoRA training seeds and a re-tuned Laya?
- How would Jev score on the same 130 questions (calibration and accuracy), measured rather than quoted?
- Is there a decoder between 270M and 2B that is both as fast and as good as Laya?
- Would the same result hold on memory decisions (save/skip, supersede, link) with our own labels?

## Grading and labels
- Directness: medium. Same-labels open-weight System One vs LoRA LLM, but a game task.
- Control: medium. Shared labels, validation, executor, GPU and an oracle reference; single training run per model; Laya not re-tuned.
- Independence: medium. Third party to Laya and Gemma, but author of the Gemma arm.
- Reproducibility: high. Pinned commits, scripts, per-game and per-model result files, adapters published.
- Applicability: low. Not memory; latency not stressed.
- Pillars: R9 primary (open-weight System One vs alternative on quality, calibration, latency, hardware, self-hosting); R4 (calibration), R6 (evaluation design).
- Stage: none (action choice in a game loop; not a memory stage).
- Tags: lora-fine-tune, grammar-constrained single-token choice, temperature scaling, self-host.
- B14 supports: calibration must be measured locally; Laya base's measured ECE contradicts its own model card, and zero-shot LLM confidences are unusable raw.
- Contradiction: B12 (qualified). A task-tuned System One model (Laya v3) without a planner exits MAP01 6/6, so "a typed decision model alone does not survive an open loop" does not hold here; but a rule executor does the pathing, it is the training map, and on MAP02 everyone fails.
- would_create: same labels, LoRA small LLM matches System One encoder; no intrinsic latency advantage at equal size.

## Origin chain
@dexmac221 post (2026-09-28) -> Medium article (403, not read) and https://github.com/dexmac221/doomgemma at `cdf2d04` -> docs/RESULTS.md sections 3 to 7 and results/*.json, *.jsonl -> upstream data and Laya v3 from azalio/doomLaya `b25edd3`. Independence: single author; Jev figure is secondhand from doomLaya.
