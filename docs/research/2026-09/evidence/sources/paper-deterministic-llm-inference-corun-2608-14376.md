---
schema_version: 1
artifact_id: N-SURVEY-20260927-13
artifact_type: note
producer: triage
run_id: survey-20260927T054501Z-e1b9
created_at: 2026-09-27T05:53:00Z
idempotency_key: note:survey:arxiv:2608.14376
input_refs: []
pillar_primary: R1
pillar_secondary: []
beliefs_affected: {supports: [], contradicts: [B1]}
evidence: {directness: 4, control: 4, independence: 4, reproducibility: 2, applicability: 3}
source_url: https://arxiv.org/abs/2608.14376
found_via: survey
strength: paper-ablated
---

# CoRun: Padding is Simple and Efficient for Deterministic LLM Inference (with supporting sources on inference nondeterminism)

- **URL:** https://arxiv.org/abs/2608.14376 (read via https://arxiv.org/html/2608.14376v1); supporting: https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/ ; https://github.com/thinking-machines-lab/batch_invariant_ops (linked from the blog, not fetched) ; https://arxiv.org/abs/2601.19934 (abstract page only)
- **Type:** paper (primary), vendor research blog (supporting), paper abstract (supporting)
- **Author / org:** Shiju Zhao, Jiacheng Yang, Qihang Chen, Junhao Hu, Jiaqi Zheng, Guihai Chen, Xusheng Chen (Nanjing University State Key Lab for Novel Software Technology; Hunyuan Team, Tencent; Peking University). Blog: Horace He with others at Thinking Machines Lab. 2601.19934: Claire Nicholson.
- **Date:** CoRun arXiv v1 dated 14 Aug 2026; blog 10 Sep 2025; 2601.19934 submitted 12 Jan 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** top-down survey, pillar R1, belief B1
- **Relevance to a memory stack:** high, it sets the conditions under which a recorded served context can be re-run to the same model output, which decides whether P0 "reproduce a decision" can mean re-execution or only re-inspection.

## TL;DR
- Same prompt at temperature 0 does not give the same output on a standard serving engine: the Thinking Machines blog reports 80 unique completions out of 1000 for one prompt on Qwen3-235B-A22B-Instruct-2507 on vLLM; with batch-invariant kernels all 1000 were identical.
- Root cause per the blog: server load changes batch size, and non-batch-invariant kernels change the floating-point reduction order; it is "not concurrency plus floating point" per se.
- CoRun (vLLM 0.25.0) gets determinism by padding decode to a fixed shape (max concurrency 256) plus isolated prefill and position-invariant kernels; it reports 15 to 324% higher throughput than vLLM batch-invariant mode, 51.8% lower mean TTFT and 48.6% lower mean TPOT than batch-invariant mode.
- CoRun's determinism guarantee is scoped to the same hardware, kernel versions, numerical formats and tensor-parallel degree; the paper explicitly does not claim cross-hardware reproducibility.
- For hosted APIs, the blog states LLM APIs are "not deterministic in practice" even at temperature 0; none of the sources says any hosted API is deterministic. (inference) An engineering agent on a hosted API cannot re-run a served context to the same output; recorded output is required.

## What it claims / describes
CoRun (primary). The paper distinguishes batch invariance (a request's output does not change with batch size) from position invariance (output does not change when the request moves between slots of a same-sized batch). Its claim is that full batch invariance, as implemented by batch-invariant kernels, is expensive, while position invariance plus a fixed execution shape is cheap. Three components:
1. Isolated prefill: "A prompt can retain its natural length, but its execution shape no longer depends on the lengths or arrival times of other requests."
2. Fixed-shape decode: "CoRun pads the active batch to the maximum concurrency and replays one fixed-size CUDA Graph." Config quoted: `cudagraph_mode=full_decode_only`, `cudagraph-capture-sizes 256`, `max-num-reqs 256`.
3. Position-invariant kernels: "Position invariance allows a request to move between batch slots, but requires the overall execution shape to remain fixed."
Formal guarantee stated as Y(x,s;C,p,a) = Y(x,s;C',p',a') for arbitrary co-runners C, positions p and arrival orders a (x = input, s = seed). Contract scope: it "does not claim reproducibility across hardware architectures, kernel versions, numerical formats, or tensor-parallel degrees."
Baselines: STD = default vLLM (nondeterministic), BI = vLLM batch-invariant mode, plus discussion of LLM-42 (verified speculation / rollback approach). Workloads: BurstGPT (Azure OpenAI production traces, prompts and responses up to 8K tokens), Blazedit (code editing, long inputs and outputs), synthetic fixed lengths (in = 128/512/2048/4096, out = 32/128); "300 requests from each workload". The paper cites Atil et al. as observing "output variation across all tested hosted models" with "a gap of up to 70% between the best and worst task outcomes available across repeated runs."

Thinking Machines blog (supporting). Explains that nearly all inference endpoints are nondeterministic because "the load (and thus batch-size) nondeterministically varies", and that batch-invariant RMSNorm, matmul and attention kernels fix it. Also shows true on-policy RL with KL divergence "flat at 0" when sampler and trainer are bitwise identical. Code: thinking-machines-lab/batch_invariant_ops.

2601.19934 (supporting, weak for this note). Abstract only was retrieved: tests gpt-4o-mini and llama3.1-8b at temperature 0.0 and 0.7 across five prompt categories, measuring unique output fractions, lexical similarity and word counts; states "nondeterminism persists even at temperature 0.0, with distinct variability patterns by model size, deployment, and prompt type." The unique-output fractions requested were not in the retrieved content, so no numbers are reported here.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Unique completions at temperature 0 | "80 unique completions, with the most common of these occurring 78 times" | n/a | TML blog; Qwen/Qwen3-235B-A22B-Instruct-2507; prompt "Tell me about Richard Feynman"; 1000 samples; 1000 max tokens; vLLM | one prompt; GPU not stated in extract |
| First divergence | identical for first 102 tokens, first divergence "at the 103rd token" | n/a | same | one prompt |
| Unique completions with batch-invariant kernels | "all of our 1000 completions are identical" | 80 unique without | same | same hardware/software presumably (not stated) |
| Wall time, 1000 sequences | 26 s | vLLM default | TML blog; Qwen-3-8B; output 90 to 110 tokens | GPU not stated in extract |
| Wall time, deterministic unoptimized | 55 s | 26 s | same | about 2.1x slower |
| Wall time, deterministic + improved attention kernel | 42 s | 26 s | same | about 1.6x slower |
| Determinism check, CoRun | "All 32 prompts pass for each of the three models" (identical token sequences, exactly matching sampled-token log probs, isolated vs batched) | isolated execution | vLLM batch-invariance test harness; temperature 0.6; seed 42; up to 8 output tokens; Qwen3-235B-A22B, DeepSeek-V3, Hy3 | only 8 output tokens per prompt; 32 prompts; single hardware/software stack |
| Throughput vs BI | 15 to 324% higher (paper: "improves throughput by 15 [to] 324% over BI", range dash normalised) | BI (vLLM batch-invariant) | BurstGPT, Blazedit, synthetic; 300 requests each | per-cell table values not extracted |
| Throughput vs STD | "Aggregate throughput more than doubles for every evaluated model" (relative to BI); DeepSeek-V3 in=4096/out=128: "CoRun even exceeds STD" | STD | as above | other STD gaps not extracted |
| Decode throughput | "83% of STD's peak" | STD | decode-intensive | 17% below nondeterministic peak |
| Mean TTFT | reduced 51.8% | BI | as above | vs BI, not vs STD |
| Mean TPOT | reduced 48.6% | BI | as above | vs BI, not vs STD |
| Single step latency (Qwen3) | STD 19.4 ms, BI 88.4 ms, CoRun 32.6 ms | STD and BI | one decode step | CoRun about 1.7x STD |
| Operator overhead of BI | Mean/RMSNorm/Softmax 2.12 to 5.61x; MatMul "36.2x" at max reduction dimension | non-invariant kernels | microbenchmarks | operator-level only |
| BI serving throughput loss (as cited) | "reduce serving throughput by up to 74%" | STD | CoRun's characterisation of batch-invariant kernels | cited claim, conditions not extracted |
| BurstGPT, BI completion time | "approximately 40 seconds to finish prefill and 124 seconds to finish decode" | n/a | BurstGPT | CoRun equivalent not extracted |
| Low concurrency failure | "When the padding size exceeds 64 in this single-request experiment, CoRun falls below BI" | BI | single request | padding waste at light load |
| LLM-42 rollback ratio | "45.41%" | n/a | Qwen3-30B-A3B MoE | cited as LLM-42 weakness |
| Hardware | not stated (GPU type and count not found in extracted text) | | | major reproducibility gap |
| Hosted API behaviour | TML: APIs "still not deterministic in practice" at temperature 0; CoRun cites Atil et al. up to 70% best-to-worst task outcome gap across repeated runs on hosted models | | | no source measures a hosted API as deterministic |

## Mechanism details you could implement
- Self-hosted deterministic serving: vLLM batch-invariant mode or batch_invariant_ops (about 1.6x to 2.1x wall time in the TML 8B test), or CoRun style fixed-shape padding (paper reports much lower cost, but no code statement was found).
- Pin the determinism key: model weights hash, engine version (e.g. vLLM 0.25.0), kernel versions, dtype, tensor-parallel degree, GPU architecture, sampler seed, temperature. CoRun's guarantee is void if any of these differ, so a replay record must store them.
- Seeded sampling is compatible: CoRun validates at temperature 0.6 with seed 42, so determinism does not require greedy decoding once kernels are invariant.
- Verification pattern: compare token sequences and per-token log probs between isolated and batched execution (vLLM harness), which a memory stack can reuse as a replay check.

## Limitations, caveats, counter-evidence
- CoRun determinism evidence is thin: 32 prompts, up to 8 output tokens each. Long-output determinism (agent-scale, thousands of tokens) is not shown in the extracted text.
- GPU type and count were not found in the text, and no code availability statement exists; results cannot be reproduced as published.
- Guarantee is same-stack only; cross-hardware, cross-version, cross-TP reproduction is explicitly out of scope. (inference) Any provider upgrade, even on a self-hosted cluster, breaks re-execution of old records.
- Padding costs at light load (falls below BI when padding exceeds 64 in a single-request test) and still trails STD in decode (83% of peak).
- The TML numbers are a single prompt and a single model per experiment; GPU not captured in my extract.
- 2601.19934 numbers were not retrieved (abstract only); treat it as directional.
- (inference) Hosted frontier APIs (the setting of most engineering agents) expose no batch-invariance control, and their model snapshots are retired; no source here claims any hosted API is deterministic. Some providers expose a seed parameter, but none of these sources tests it.
- No instructions aimed at an AI reader were found in these pages.

## Takeaways for tuning a memory stack
- (inference) For B1: retaining served artifacts with source position and version is sufficient for re-inspection only if the model output is also recorded. It is not sufficient for re-execution on hosted APIs, and on self-hosted engines it is sufficient only when the inference stack is batch invariant (or CoRun style) and the full stack fingerprint is retained.
- P0's "reproduce a decision" should be defined as: return the exact authorised served artifact plus the recorded model output and the model/stack fingerprint; re-run is an optional, separately graded check.
- Record stack fingerprints alongside served artifacts (model id and snapshot, engine, dtype, TP, GPU, seed, temperature) so that a later reviewer knows whether re-execution is even meaningful.
- Cost signal: deterministic self-hosted inference costs roughly 1.6x to 2.1x wall time (batch-invariant, TML 8B) or about 1.7x per-step latency vs STD (CoRun 32.6 ms vs 19.4 ms), so it is a policy choice, not free.

## Open questions
- What GPU was CoRun run on, and does its guarantee hold for multi-thousand-token outputs typical of code agents?
- Does any hosted provider offer a bitwise-deterministic mode or snapshot retention sufficient for re-execution months later?
- What are 2601.19934's unique output fractions for gpt-4o-mini at temperature 0 (hosted) vs llama3.1-8b?
- How often does output divergence flip a Spec-to-PR-review decision (semantic) rather than just token text?

## Grading
- directness 4: directly measures whether the same input yields the same output under realistic serving, the exact premise behind "reproduce a decision" by re-run; it does not test agent decisions.
- control 4: STD, BI and LLM-42 baselines, operator microbenchmarks and three workloads; determinism test itself is small.
- independence 4: academic and Tencent authors evaluating their own system against open baselines, no LLM judge; TML blog is independent confirmation of the phenomenon.
- reproducibility 2: CoRun has no code statement and hardware not found in text; TML has public code.
- applicability 3: relevant for self-hosted agent stacks; most engineering agents use hosted APIs where these fixes are unavailable.
