---
schema_version: 1
artifact_id: N-SURVEY-20261006-05
artifact_type: note
producer: triage
run_id: survey-20261006T054504Z-b489
created_at: 2026-10-06T06:50:00Z
idempotency_key: note:survey:huggingface:vllm-sr/Decision-2.0+torchcast-ai/torchcast-decision-27b
input_refs: []
pillar_primary: R9
pillar_secondary: []
memory_stage: all
priority: 2
beliefs_affected: {supports: [], contradicts: []}
evidence: {directness: medium, control: low, independence: low, reproducibility: medium, applicability: medium}
source_url: https://huggingface.co/vllm-sr/Decision-2.0-Nox-4B
found_via: survey
---

# Open-weight System One roster update, 2026-10-06: vLLM Semantic Router Decision 2.0 family and Torchcast Decision 27B

- **URL:** https://huggingface.co/vllm-sr/Decision-2.0-Nox-4B ; https://huggingface.co/vllm-sr/Decision-2.0-Vega-27B ; https://huggingface.co/torchcast-ai/torchcast-decision-27b ; HF API listing https://huggingface.co/api/models?search=Decision-2.0
- **Type:** vendor model cards (self-reported numbers)
- **Date:** cards and ports created 2026-10-03 to 2026-10-05
- **Retrieved:** 2026-10-06
- **Relevance:** high for priority 2; neither family is in known-notes or the 2026-10-04 roster.

## Roster rows
| Model | Size | Base | Licence | Hardware / latency | Published quality | Maintainer | vs Jev |
|---|---|---|---|---|---|---|---|
| Decision-2.0-Kai | 0.6B | not read | not read | ONNX port exists | not read | vLLM Semantic Router (vllm-sr) | not stated |
| Decision-2.0-Eos | 0.8B | not read | not read | ONNX, CoreML ports | not read | vllm-sr | not stated |
| Decision-2.0-Sol | 2B | not read | not read | ONNX, MLX 4-bit ports | not read | vllm-sr | not stated |
| Decision-2.0-Nox | 4B | Qwen/Qwen3.5-4B-Base | Apache-2.0 | "median of 12.9 ms per single-question request on a single GPU"; MLX 4-bit port | JevArena 63.6; human-labelled transfer 52.3; Jev Decision Index 43.8; vs Decider 4B 63.6 vs 61.9 (JevArena), 52.3 vs 55.5 (transfer); vs Jet v6.2 63.6 vs 60.4 | vllm-sr | not stated |
| Decision-2.0-Lux | 9B | not read | not read | GGUF, MLX ports | not read | vllm-sr | not stated |
| Decision-2.0-Vega | 27B | Qwen/Qwen3.8-27B | Apache-2.0 | "median of 71.4 ms per single-question request" | JevArena 74.0; Jev Decision Index 56.5; transfer 58.7% | vllm-sr | not stated |
| Torchcast Decision 27B | 27B | LoRA merged on StartLux-Decision-27B (Qwen-derived) | CC BY-NC 4.0 weights (non-commercial), Apache-2.0 code | NVIDIA GPU with at least 64 GB (54.7 GB bf16 weights); 33.0 ms single yes/no, 49.0 ms three questions; GGUF 12B/27B ports | Decision Index 0.2.1: 65.00 vs StartLux 63.88, Clef 61.21, Jev 1.13 57.91, Surogate Rune 26B-A4B v3 57.44; "ahead on 31 of the 38 index benchmarks" | Torchcast AI | yes, vendor head-to-head on Decision Index 0.2.1 |

Downloads at retrieval: Kai 725, Nox 474, Sol 456, Eos 443, Vega 389, Lux 372; Torchcast 27B 492, 12B GGUF 1016.

## Caveats
- All numbers self-reported. vllm-sr says training data was "audited at row level against all Index test items"; Torchcast trained on public train/dev splits of the index's source datasets (inference: in-distribution advantage on the index).
- "Jev Decision Index" (vllm-sr, Vega 56.5) and "Decision Index 0.2.1" (Torchcast, Jev 1.13 57.91) may be different versions; not comparable without checking.
- Torchcast's licence rules it out for a commercial product; the vllm-sr family is Apache-2.0 and spans 0.6B to 27B, the cleanest candidate set for self-hosting so far.
- vllm-sr cards use `trust_remote_code=True` (security review needed before running).
- Other new listings not read (budget): Phocinae-150M-Decision-v1, Vela-Decision-170M, diffcider-typed-decisions, ru-decision-4b, decisioncraft-kai-0.6b, ternary-bonsai decision LoRAs.

## Takeaways
- Add the vllm-sr Decision 2.0 family to the priority 2 comparison arm list, with Nox 4B as the cost point and Vega 27B as the quality point.
