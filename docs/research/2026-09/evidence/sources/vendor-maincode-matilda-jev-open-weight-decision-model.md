---
schema_version: 1
artifact_id: N-20261001-04
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105230308132225289", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:Maincode/matilda-jev-v1
claim_cluster: hf:Maincode/matilda-jev-v1
feeds: ["memory"]
primary_source: https://huggingface.co/Maincode/matilda-jev-v1
source_commit: 9ea24216382bcccec524dd0b3a4a481aff48c127
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R7"]
tags: {"mechanism": ["open-weight decision model", "255-option readout", "stored calibration temperature", "Jev-compatible /v1/systemone server"], "workload": ["general typed decisions"], "lifecycle_stage": ["none"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: weights, runtime and a score table are published, but the scores are carried over from an earlier evaluation not rerun on this package", "control": "low: one aggregate leaderboard score, no comparison model in the card, no per-dataset table", "independence": "low: vendor-reported on a third-party index; no outside rerun", "reproducibility": "medium: Apache-2.0 weights and runtime at a pinned revision; Decision Index 0.2.1 harness not linked", "applicability": "medium: Jev-compatible request shape makes it a drop-in self-hosted arm, but 26.1B parameters and about 49 GiB bf16 need a large accelerator"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["An Apache-2.0, Jev-API-compatible decision model (MATILDA-jev, 26.1B) is self-hostable today and reports 59.26 on Decision Index 0.2.1; whether that beats Jev on our decisions is untested"]}
claim_correction: The post's "median decision latency of 56.8ms on a single AMD MI355X across 150,317 evaluation requests" is not on the model card at the pinned revision; the card states the 150,317 requests only as the Decision Index 0.2.1 evaluation and gives no latency.
memory_stage: none
priority: 2
---

# MATILDA-jev (Maincode): an Apache-2.0, Jev-compatible open-weight decision model, 26.1B, Decision Index 59.26

- **URL:** https://huggingface.co/Maincode/matilda-jev-v1
- **Type:** vendor (model card and weights)
- **Author / org:** Maincode (Australia)
- **Date:** repository created 2026-09-30T08:21:46Z; revision 9ea24216382bcccec524dd0b3a4a481aff48c127, last modified 2026-09-30T22:37:42Z
- **Retrieved:** 2026-10-01 (README.md and config.json read at the pinned revision via the Hugging Face raw endpoint; file list via the HF API). Weights not downloaded; nothing executed.
- **Cited by evidence:** @MaincodeAU, 2026-09-30, https://x.com/MaincodeAU/status/2105230308132225289 ("Today we are open-sourcing Matilda Jev, Australia's first decision model ...")
- **Relevance to a memory stack:** high for priority 2. A self-hostable decision model with the same request shape as Jev (`POST /v1/systemone`, `choice` / `noul` / `score`, probabilities and confidence per answer) means a hosted vs in-house arm can be swapped by base URL.

## TL;DR
- Open weights, Apache-2.0 (card `license: apache-2.0`), 26.1B parameters, bf16 about 49 GiB before runtime overhead; custom `MatildaJevModel` classes (`trust_remote_code=True`) plus a bundled server `maincode_jev_serve`.
- Scores carried over from an earlier run: "The original identical weights were evaluated with Decision Index 0.2.1 over 150,317 requests ... the full benchmark was not rerun for the configuration aliases." Decision Index 59.26, raw 68.89, breadth 58.06; areas: Knowledge and Reasoning 43.52, Language 66.36, Retrieval and Classification 61.34, Tools and Automation 77.72, Arts and Human Taste 43.65 ("chance-corrected skill multiplied by 100").
- No comparison to Jev, Liquid d1, Laya or others on the card. Posts this run quote d1 58.9 vs Jev 57.9 on the same index (not verified: the index page returned 401, and its version is not stated), so MATILDA's 59.26 cannot be ranked against them yet.
- **Claim correction:** the 56.8 ms median latency in the post is not on the card. Training data and base model are not disclosed.
- Validation on the card is a packaging check (25/25 smoke questions, 23 requests matched original probabilities exactly), not a benchmark.

## What it claims / describes
"MATILDA-jev is Maincode's one-pass decision model. It scores the options supplied in a `choice`, `noul` (yes/no), or ordered `score` question. It accepts text or JSON state and optional images. This is a decision checkpoint with a 255-option readout, not a text-generation checkpoint." The package "includes the backbone weights, decision readout, tokenizer, preprocessing configuration and calibrated temperature"; the runtime "loads both the backbone and `readout.safetensors`, and applies the stored temperature."

Serving: `python -m maincode_jev_serve.server --checkpoint ./matilda-jev-v1 --model-name matilda-jev-v1 --host 127.0.0.1 --port 8000`; API at `/v1/systemone`, optional auth via `MJ_API_KEY`. Recorded example: a `choice` over `card_delivery | duplicate_charge | cash_withdrawal` returns `probabilities`, `choice: duplicate_charge`, `confidence: 0.9957`, `usage: {input_tokens: 100, output_tokens: 0}`.

Architecture (config.json): hidden size 5120, intermediate 17408, head_dim 256, a repeating pattern of three `linear_attention` layers then one `full_attention` (`full_attention_interval: 4`), `image_token_id` present (vision input). Inference: a hybrid linear-attention multimodal backbone of the Qwen3.5/3.6 family, but the card does not name a base model.

The post adds: "conditioned for Australian deployment and post-trained with our own specialised recipe", "Post-trained end-to-end on our local infrastructure".

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Decision Index | 59.26 | none on card | Decision Index 0.2.1, 150,317 requests (card, "Previously reported results") | carried over, not rerun on this package |
| raw / breadth | 68.89 / 58.06 | none | same | |
| Knowledge and Reasoning | 43.52 | none | same | chance-corrected x100 |
| Language | 66.36 | none | same | |
| Retrieval and Classification | 61.34 | none | same | the area closest to rerank and filter stages |
| Tools and Automation | 77.72 | none | same | |
| Arts and Human Taste | 43.65 | none | same | |
| parameters / memory | 26.1B / about 49 GiB bf16 | | card | |
| packaging validation | 25/25 smoke questions; 23/23 requests matched original probabilities (max difference 0) | | AMD MI355X, Python 3.12, Transformers 5.17.0, PyTorch 2.14.0 | "not a full benchmark rerun" |
| median latency (post only) | 56.8 ms | n/a | single MI355X, 150,317 requests (post) | not on the card |
| d1 vs Jev on the same index (posts only) | 58.9 vs 57.9 | n/a | @CoderGeeta 2105104332756754743 | index page 401, version unknown |

## Mechanism details you could implement
- Self-hosted arm for any Jev-shaped experiment: same JSON (`state`, `questions` keyed by id with `type`, `instructions`, `criteria`), same answer shape (probabilities per option, choice, confidence), zero output tokens.
- Calibration is a single stored temperature applied by the runtime; fit our own temperature or a local head on our labelled decisions before using thresholds (inference, consistent with B14).
- The card exposes `AutoModel` hidden states and a training constructor in USAGE.txt, so fine-tuning on our own decisions is possible in principle (not read).

## Limitations, caveats, counter-evidence
- No base model, no training data statement, no limitations section, no comparison table (card).
- Scores are a single aggregate on an index we could not open; per-dataset results, seeds and judge are unknown.
- 26.1B and about 49 GiB bf16 is far heavier than Jev-like 0.6B to 4B open models (Intern-Decision, Tev1-4B, od1); per-call cost in-house needs a large GPU (inference).
- The card text says to authenticate "while the repository is private", although it was publicly readable on 2026-10-01.
- Single vendor announcement; no third-party usage found in this run's queue or pool.

## Takeaways for tuning a memory stack
- Add MATILDA-jev as a candidate arm in any Jev vs open-weight comparison on our own decisions (priority 2); the API compatibility makes the swap a base-URL change.
- Do not rank it against Jev or d1 from leaderboard numbers until the same index version and request set are confirmed.
- Its weakest areas on the index (Knowledge and Reasoning 43.52) are the ones closest to contradiction and supersession questions (inference); measure those stages specifically.

## Open questions
- Which Decision Index version and request set produced the posts' d1 58.9 and Jev 57.9?
- What is MATILDA's latency and cost per decision on a commodity GPU, and does a quantised build keep its probabilities?
- What is the base model and its licence chain?

## Grading and labels
- **Directness: medium.** Weights and runtime are real and pinned; scores are carried over.
- **Control: low.** No comparator on the card.
- **Independence: low.** Vendor-reported.
- **Reproducibility: medium.** Pinned revision, Apache-2.0, runtime bundled; benchmark harness not linked.
- **Applicability: medium.** Drop-in API; heavy hardware.
- **Pillars:** R9 primary (which open-weight System One model can sit at our stages); R7 secondary (Jev-compatible interface). **Memory stage:** none. **Priority:** 2.
- **Beliefs:** no register belief covers open-weight availability; would create the belief in the frontmatter. **Contradictions:** none.

## Origin chain
Post @MaincodeAU 2105230308132225289 (2026-09-30, no link) -> hf:Maincode/matilda-jev-v1 found via the Maincode organisation page -> README.md at 9ea2421 ("Validation", "Previously reported results", "Download and serve") and config.json -> this note. Independence: the Decision Index is a third-party index (Hugging Face) but the scores are self-reported; no shared authors with other open-weight decision models on the bus.
