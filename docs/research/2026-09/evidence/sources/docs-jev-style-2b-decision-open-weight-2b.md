---
schema_version: 1
artifact_id: N-SURVEY-20260929-08
artifact_type: note
producer: triage
run_id: survey-20260929T054503Z-ed98
created_at: 2026-09-29T05:59:00Z
idempotency_key: note:survey:huggingface:chaoliangUNSW/Jev-Style-2B-Decision-v3
input_refs: []
pillar_primary: R9
pillar_secondary: [R4]
memory_stage: none
priority: 2
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 3
  control: 2
  independence: 2
  reproducibility: 3
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://huggingface.co/chaoliangUNSW/Jev-Style-2B-Decision-v3
secondary_sources:
  - https://huggingface.co/api/models?search=jev&sort=lastModified&direction=-1&limit=60
  - https://huggingface.co/api/models?search=decision&sort=lastModified&direction=-1&limit=60
  - https://huggingface.co/api/models?search=system-one&sort=lastModified&direction=-1&limit=40
found_via: survey
claim_cluster: open-weight-system-one-roster-2026-09-29
---

# Jev-Style-2B-Decision-v3 and Jev-Style-0.8B-Decision-v3 (chaoliangUNSW): the most-downloaded new open-weight Jev-like models, with a vendor head-to-head against Jev

- **URL:** https://huggingface.co/chaoliangUNSW/Jev-Style-2B-Decision-v3 (model card). Roster search via the Hugging Face models API (three queries listed in the frontmatter)
- **Type:** repo (model card with self-reported numbers)
- **Author / org:** chaoliangUNSW (Hugging Face account; affiliation not stated beyond the handle)
- **Date:** not stated on the card as read; listed by lastModified in September 2026
- **Retrieved:** 2026-09-29
- **Cited by evidence:** survey run, R9 roster duty (priority 2)
- **Relevance to a memory stack:** medium. It is an Apache-2.0, 1.88B model that runs on a laptop with GGUF and MLX builds and publishes a same-benchmark comparison with Jev, Laya and Decider-2B. It is a candidate self-hosted arm for PC-20260929-04 and PC-SURVEY-20260928-06.

## TL;DR
- 1.88B parameters, full fine-tune of Qwen/Qwen3.5-2B, Apache-2.0; a 0.8B sibling; GGUF and MLX conversions (v1 GGUF 7,249 downloads, MLX 4,766, the highest of any Jev-like repo found).
- Vendor numbers on JevBench v1.4.1 (231 items): 2B v3 73.6%, 0.8B v3 64.1%, Jev 1.13 86.6%, Laya 58.4%, Decider-2B 71.0%. So 13 points behind Jev on the author's own run.
- Topic classification: tweet_topic 82.2 vs Jev 79.3; fin_topic 61.1 vs Jev 67.0.
- Needs its own runtime: stock llama.cpp and Ollama cannot produce the decision scores.
- The card says the full training recipe was not run.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| JevBench v1.4.1 accuracy | 2B v3 73.6%; 0.8B v3 64.1% | Jev 1.13 86.6%; Decider-2B 71.0%; Laya 58.4% | 231 items | self-reported; the known note "JevBench v1.5.0 (Benchmark Heaven)" showed open 12B models tying Jev |
| tweet_topic | 82.2 | Jev 79.3 | | self-reported |
| fin_topic | 61.1 | Jev 67.0 | | self-reported |
| Training | one A100 40GB, 60.0M tokens, 181,449 rows from 58 sources | | | one global temperature T=0.8279 |
| Latency, M1 Max, GGUF F16 | 0.52 s for 878 tokens, 1 question; 2.66 s for 10 questions; 16.2 s for 24k tokens, 0.17 s with precomputed state | | | |

Not zero-shot on 14 benchmarks per the card (trained on their training splits).

## Open-weight roster additions found by the same search (API metadata only, no quality numbers)
- llm-semantic-router "Decision-1.0" family: Kai-0.6B and Lex-0.6B (Vela-1.0-Encoder-307M lineage), Eos-0.8B, Sol-2B, Nox-4B, Lux-9B (Qwen3.5 bases); Apache-2.0; created 21 to 22 Sep.
- iapp/OpenThai-SystemOne: Qwen3.5 base, Apache-2.0, Thai; 7,979 downloads; GGUF, MLX, GPTQ, FP8, NVFP4 builds.
- pngwn/system-one-qwen3.5-4b-scorer: PEFT on Qwen3.5-4B, CC-BY-NC-4.0, ONNX and CoreAI ports.
- Others: rongxinzy/LightJev-0.6B-typed-decisions (Qwen3-0.6B); tasksource/tasksource-jev-nano-v0 (ModernBERT); BricksDisplay/jevling-0.8b (CC-BY-NC) and -2b; RowletQwQ/JevCodeLocator-0.6B (code retrieval); zyang94/tacet-2b-decision; flymy-ai/decision-4b-v1.4; Worthify/Decision-1 (gemma-4-12B-it); moganai/mogan-decision-31B-it (CC-BY-NC); dwidlee/systemone-lite-0.5b.
- JEV-9B GGUF appears with the same tag as autotrust JEV-27B (probably the same family).

## Limitations, caveats, counter-evidence
- Self-reported numbers on a leaderboard the author ran; no independent measurement; the 1.88B size matches this-that-model-1.0 (also "1.88B hybrid decoder" per 2609.32160), but the names differ and no link between them is stated.
- A custom runtime is a deployment cost.

## Takeaways for tuning a memory stack
- For a laptop or single-GPU self-hosted arm, Jev-Style-2B is now the most-used Apache-2.0 option, but expect a gap to Jev of the order of 13 points on general typed decisions; measure on our own decisions before assuming it.
- The roster is growing faster than evaluations of it: of the new models found, only Jev-Style publishes any comparison with Jev.

## Open questions
- Is Jev-Style-2B the same model as this-that-model-1.0?
