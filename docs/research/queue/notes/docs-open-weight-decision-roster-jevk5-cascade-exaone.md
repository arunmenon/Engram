---
schema_version: 1
artifact_id: N-SURVEY-20261004-01
artifact_type: note
producer: triage
run_id: survey-20261004T054506Z-478e
created_at: 2026-10-04T05:55:25Z
idempotency_key: note:survey:huggingface:alibiserikbay/JevK5-9B
input_refs: []
pillar_primary: R9
pillar_secondary: [R6]
memory_stage: none
priority: 2
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: medium (decision quality on public suites, not on memory-stage decisions)
  control: medium (pre-registered epoch rule and threshold rule, one seed, small dev slices)
  independence: low (all numbers self-reported by the model authors; Jev figure is JevBench's published number)
  reproducibility: high (weights, runtimes and per-row results public at pinned revisions)
  applicability: medium (self-hostable on one 19 to 32 GB GPU; English only; no engineering-agent workload measured)
source_url: https://huggingface.co/alibiserikbay/JevK5-9B
found_via: survey
also_read:
  - https://huggingface.co/chaoliangUNSW/Jev-Style-Cascade-9B
  - https://huggingface.co/carrtesy/EXAONE-4.0-1.2B-JEV
  - https://huggingface.co/GhostScientist/jev-decisions-v1-model (card is a stub, no numbers)
---

# Open-weight System One roster update, 2026-10-04: JevK5-9B v0.3.3, Jev-Style-Cascade-9B, EXAONE-4.0-1.2B-JEV

- **URL:** https://huggingface.co/alibiserikbay/JevK5-9B ; https://huggingface.co/chaoliangUNSW/Jev-Style-Cascade-9B ; https://huggingface.co/carrtesy/EXAONE-4.0-1.2B-JEV
- **Type:** model cards (open weights) with self-reported evaluations
- **Author / org:** alibiserikbay (runtime github.com/allebee/jevk5); chaoliangUNSW (author of Jev-Style-2B-Decision-v3, see N-SURVEY-20260929-08); carrtesy (individual)
- **Date:** JevK5-9B v0.3.3 card current on 2026-10-04; Cascade-9B created 2026-10-02; EXAONE-JEV v0.2 2026-10-03
- **Retrieved:** 2026-10-04 (local copies: `out/log/raw/hf-jevk5-9b.md`, `out/log/raw/hf-cascade9b.md`, `out/log/raw/hf-exaone.md`)
- **Cited by evidence:** survey roster sweep (Hugging Face models API, `search=jev&sort=createdAt`, 40 newest)
- **Relevance to a memory stack:** high for priority 2: the strongest Apache-2.0 self-hostable decision model now on the board, plus the first open cascade, and a clear warning that the public JevBench items no longer separate open models from Jev.

## TL;DR

- **JevK5-9B v0.3.3** (Apache-2.0, LoRA merged into Qwen3.5-9B, about 19 GB bf16, 16 ms p50 on an idle H100): JevBench public items easy 1.000, standard 0.958, hard 0.775. Not yet on the Decision Index or JevBench board. Training labels partly from GPT-6 Luna (licence caveat).
- **Jev-Style-Cascade-9B** (Apache-2.0, no new weights): the 2B answers first and passes questions below confidence 0.75 to JevK5-9B. "JevBench public items (231) **87.9 %** (203 / 231), Jev 1.13.0's published figure on the same items is 86.6 %". But on the Decision Index 0.2.1 its offline forecast is "**46.08**", against Jev's 57.91 (figure from the EXAONE card's reference row).
- So on the same week, an open 9B ties or passes Jev on JevBench's 231 public items and trails it by about 12 points on the 150k-row Decision Index. The public JevBench items are close to saturated as a separator (inference).
- **EXAONE-4.0-1.2B-JEV v0.2**: Decision Index 27.72, JevBench public 67.5%; non-commercial licence (EXAONE NC), so not a candidate for us; useful as a documented recipe (236k rows, full fine-tune, two-order reads).
- None of the three reports a memory-stage or engineering-agent workload. "Real-world workflow performance against Jev has not been measured" (JevK5-9B card).

## What it claims / describes

**JevK5-9B v0.3.3.** Qwen3.5-9B with a rank-16 LoRA on attention projections, merged. One forward pass, "zero generated tokens": a softmax over answer-letter logits divided by a fitted temperature (1.316); over 16 options a "knockout" readout in groups of 16 with a second temperature (1.05). Serves a TypeSafe-style `/v1/systemone` endpoint via `jevk5-serve`. Trained on 47,460 rows: 17,408 teacher questions (3,270 from self-hosted Qwen3.6-27B, 14,138 from GPT-6 Luna via OpenAI's API, kept only when two independent teacher answers agreed with the intended one) and 30,052 public train-split items from 26 datasets. Cross-entropy on option-letter logits, 1.5 epochs, lr 3e-5, inputs up to 2,048 tokens. "No JevBench item ... and no output of Jev was used for training, tuning or selection." Rows were dropped for exact match or "any shared 8-word sequence" against test and validation text of 35 Decision Index benchmarks.

Epoch count chosen by a rule fixed before results: adopt only if the mean of three dev metrics beats 1 epoch by at least 0.02 and none drops by more than 0.03. "This is one seed per setting, and each index source in the dev set has about 40 rows."

**Jev-Style-Cascade-9B.** Tier 1 is Jev-Style-2B-Decision-v3 (Qwen3.5-2B fine-tune). Confidence per question is `(k · p_max − 1) / (k − 1)` for k options, `|2 · P(true) − 1|` for true/false; at τ = 0.75 or above the 2B answer stands, else JevK5-9B answers. τ was chosen by a pre-declared rule: "pick the τ with the lowest expected latency whose calibration accuracy stays within 1.0 point of JevK5-9B alone", on a 4,992-question set from 29 public datasets, deduplicated against Decision Index and JevBench. Both models resident on one 32 GB GPU (29.7 GB after start-up, peak 31.8 GB).

**EXAONE-4.0-1.2B-JEV v0.2.** Full fine-tune of EXAONE-4.0-1.2B on 235,843 public train rows (17,687 dropped for overlap with Decision Index or JevBench). Reads each question twice with options in given and reversed order and averages ("removes most position bias; about 2x compute"). Per-type temperatures (noul, 2-option, 3 to 5, 6+).

## Numbers

| Model | Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|---|
| JevK5-9B v0.3.3 | JevBench public easy / standard / hard | 1.000 / 0.958 / 0.775 | JevK5 4B v0.3: 1.000 / 0.944 / 0.784 | 231 public items, JevBench runner, `jevk5_direct` adapter | self-run; against 4B "9 fixed and 9 broken (p = 1.0)" |
| JevK5-9B v0.3.3 | hard-tier ECE | 0.071 | 4B 0.054; v0.3 9B 0.126 | same | |
| JevK5-9B v0.3.3 | held-out teacher questions (362) | 0.848 | v0.3 9B 0.851 | unseen domains (leases, permits, manufacturing QC) | ECE 0.043 vs 0.032 |
| JevK5-9B v0.3.3 | hand-written hard set (64) | 0.859 | v0.3 9B 0.781 | | 55 of 64 |
| JevK5-9B v0.3.3 | bev-decision-150K test sample | 0.698, ECE 0.033 | v0.3 9B 0.700 | 2,500 rows, 4,723 questions | by type: choice 0.732, yes/no 0.774, score 0.482 |
| JevK5-9B v0.3.3 | BANKING77 / CLINC150 (151 options) | 0.754 / 0.804 | 4B 0.652 / 0.700 | 500 train-split items each, knockout readout | CLINC out-of-scope recall 0.59, precision 0.84 |
| JevK5-9B v0.3.3 | latency | p50 16 ms, p95 18 ms (easy, standard); hard p50 42 ms, p95 223 ms | | H100, batch 1, CUDA graphs, idle GPU | |
| JevK5-9B GGUF | agreement with bf16 on JevBench public | Q8_0 229/231, Q5_K_M 228/231 | | llama.cpp | Q4_K_M lost 5 hard items (0.775 to 0.730), not published |
| JevK5 0.2.2 (4B, older) | Decision Index | 36.31, 15th of 49, ECE 0.031 (4th best) | | index rerun | "Accuracy drops sharply on JevBench's fresh sealed decisions (measured for JevK5 v0.2)" |
| Cascade-9B | JevBench public (231) | 87.9% (203/231), ECE 0.026 | Jev 1.13.0 published 86.6% (0.8658); JevK5-9B alone 203/231, ECE 0.034; 2B alone 170/231 | harness fstandhartinger/jevbench @ bb05a335, one run 2026-10-02 | "not a board row; the board's ranking also uses sealed items" |
| Cascade-9B | calibration set accuracy (4,992 q) | 73.1% | JevK5-9B alone 74.1%; 2B alone 66.2% | 29 public datasets | the 2B settled 42.8%; 9B called on 55.5% of requests |
| Cascade-9B | Decision Index 0.2.1 | 46.08 (offline forecast) | 2B alone 34.83; Jev 57.91 (EXAONE card reference row) | composed from two public per-row result sets, official kit @ 87d4650 | forecast, not a board entry |
| Cascade-9B | latency | median 29.0 ms (JevBench), 37.5 ms (calibration set), p95 673.6 ms; 25,275-token request 2.4 s | JevK5-9B alone 28.1 ms | RTX 5090, one request at a time | cascade does not save latency over JevK5-9B alone on JevBench |
| EXAONE-1.2B-JEV v0.2 | Decision Index 0.2.1 | 27.72 | v0.1 21.64; Decider 2B 28.97; Tev1-4B 29.24; Jev 57.91 | 150,317 rows, local kit checked against board (Decider 2B rerun 29.22 vs board 28.97) | self-reported |
| EXAONE-1.2B-JEV v0.2 | JevBench public | 67.5% (easy 100%, original 90.3%, hard 38.7%) | | | |
| EXAONE-1.2B-JEV v0.2 | tev1 holdout (3,784) | 83.85%, ECE 0.013 | Jef Qwen3.5-4B 88.85% | | out-of-domain ECE about 0.22 on Decision Index |
| EXAONE-1.2B-JEV v0.2 | When2Call | fell "from 50 to 29" | v0.2 hard-label baseline | | learned to pick a tool, not to decline |

Judge and system share a model: not applicable (all metrics are exact-match against gold labels). Cost per decision: not stated by any card; hardware is stated.

## Roster rows (to merge into the R9 open-weight list)

| Name | Size | Licence | Hardware | Best published quality | Head-to-head with Jev | Maintainer |
|---|---|---|---|---|---|---|
| JevK5-9B v0.3.3 | 9B (Qwen3.5-9B + merged LoRA) | Apache-2.0 (training labels partly GPT-6 Luna, OpenAI terms) | CUDA GPU about 19 GB bf16; GGUF Q8_0/Q5_K_M for llama.cpp incl. Apple GPUs | JevBench public hard 0.775; BANKING77 0.754 | none direct; not on Decision Index yet | alibiserikbay, runtime allebee/jevk5 |
| JevK5 (4B) v0.3 | 4B | Apache-2.0 | about 9 GB bf16 | v0.2 Decision Index 36.31 | JevBench v1.4 ranked v0.2 "#2 of 76 systems" (public items) | same |
| Jev-Style-Cascade-9B | 2B + 9B | Apache-2.0 (inherits JevK5's Luna caveat) | one 32 GB GPU | JevBench public 87.9%, DI forecast 46.08 | 87.9% vs Jev 86.6% on public items only | chaoliangUNSW |
| EXAONE-4.0-1.2B-JEV v0.2 | 1.2B | EXAONE NC (non-commercial) | A40 measured | DI 27.72 | DI 27.72 vs Jev 57.91 | carrtesy |

Also seen in the sweep (no card numbers read, low downloads, not graded): jevling-e2b-v1, granite-jev-1b-research, JEV-27B-VL (GGUF/FP8/NVFP4 quantisations by Atlas3D), NeoHorse-Jev-4B, jev-decisions-v1/v2 (GhostScientist, stub card), Canopy-Jev-27B, sysone-laya-typed-decisions-onnx.

## Mechanism details you could implement

- Confidence cascade: `conf = (k*p_max - 1)/(k - 1)`; keep the small model's answer at `conf >= 0.75`; otherwise call the larger model on the same state; fall back to the other tier if one errors. Choose τ by a written rule (lowest latency within 1 point of the large model's accuracy) on a held-out set.
- Two-order read: score options in given and reversed order and average the distributions; costs about 2x.
- Separate calibration temperatures per question type and per option-count band; refuse to serve uncalibrated (the cascade refuses to load without `jevk5_config.json`).
- Contamination filter: drop any training row sharing an 8-word sequence with evaluation text.
- Inputs over 16,384 tokens are refused by JevK5, not truncated; the cascade accepts up to 25,600.

## Limitations, caveats, counter-evidence

- All numbers are self-reported; the only Jev comparison is to JevBench's published public-item figure, and the board's ranking uses sealed items too.
- The two yardsticks disagree on the gap to Jev: near parity on JevBench public items, about 12 points behind on the Decision Index (46.08 forecast vs 57.91). The JevK5 card itself warns of a sharp drop on fresh sealed decisions.
- One seed; about 40 dev rows per index source ("noisy (about ±0.15)").
- Licence risk: JevK5 training labels include GPT-6 Luna outputs under OpenAI terms. For a product that wants clean provenance this matters (inference).
- English only. Dates and numbers weak (hard tier 0.47). Score-type questions weak (0.482 on bev-decision).
- No measurement on memory-stage decisions (write gate, linking, staleness) or engineering artifacts.

## Takeaways for tuning a memory stack

- For a self-hosted System One today, JevK5-9B on one 24 GB GPU (or Q8_0 GGUF) is the most permissive and best-documented candidate; run it against Jev on our own decisions before trusting any public board.
- Do not use JevBench public items to choose between Jev and open models; they no longer separate them. Use our own labelled memory decisions plus the Decision Index as a breadth check.
- The cascade pattern (small model first, escalate when unsure) is cheap to reproduce and gives a tunable latency and quality knob at a memory stage.

## Open questions

- How large is the Jev gap on our own write-gate and linking decisions, where options are few and states are code and design text?
- Does the GPT-6 Luna label provenance block commercial use for us?
- Does the cascade's 0.75 threshold transfer to our decisions, or must τ be refit per stage?
