---
schema_version: 1
artifact_id: N-20260926-14
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2102930096827118053", "file_id": null, "sha256": null}, {"artifact_id": "post:2102914556427436180", "file_id": null, "sha256": null}, {"artifact_id": "post:2103322751411097952", "file_id": null, "sha256": null}, {"artifact_id": "post:2103054339296403850", "file_id": null, "sha256": null}, {"artifact_id": "post:2103054230236123256", "file_id": null, "sha256": null}, {"artifact_id": "post:2103006942302245333", "file_id": null, "sha256": null}, {"artifact_id": "post:2103789967369748607", "file_id": null, "sha256": null}, {"artifact_id": "post:2103415120403865886", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:contrastive-lm/clm
claim_cluster: github:contrastive-lm/clm
feeds: ["decision"]
primary_source: https://github.com/contrastive-lm/clm
source_commit: bb42c6c5bf914fd449bed2f6ca65be80602cb1f7
strength: vendor-benchmark
pillar_primary: R4
pillar_secondary: ["R3"]
tags: {"mechanism": ["contrastive state-action encoder", "cached action embeddings", "verifier ranking of candidate solutions"], "workload": ["tool calling", "computer use", "coding-agent verification (Terminal-Bench, DeepSWE)"], "lifecycle_stage": ["read", "evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: README reports task scores and speedups; per-task Jev numbers not captured", "control": "low: small held-out sets (30 and 38 tasks), author-run comparison, no intervals", "independence": "low: authors of CLM compare against a competitor", "reproducibility": "medium: Apache-2.0 code and weights at a pinned commit", "applicability": "medium: verifier ranking of coding-agent candidates is close to our review agents; small n"}
beliefs_affected: {"supports": ["B12"], "contradicts": [], "would_create": ["On long-horizon coding tasks a decision model used as a verifier over candidate solutions can score below pass@1 (Jev, per CLM authors); a contrastive encoder trained on agent trajectories did better"]}
claim_correction: Posts say CLM "matches or outperforms Jev" at up to 9x lower latency; the README's 9x is the best case across four zero-shot tasks, the agentic speedup is 4.1 to 5.7x, and the agentic accuracy wins are on 30 and 38 held-out tasks where, per the README, Jev "fails to serve as a verifier ... scoring below pass@1".
---

# Contrastive Language Models (CLM): a contrastive System One model (contrastive-lm/clm)

- **URL:** https://github.com/contrastive-lm/clm (weights: huggingface.co/Contrastive-LM/CLM-v0.1-8B)
- **Type:** repo + weights (paper not linked in the fetched README)
- **Author / org:** Contrastive-LM (posts by @TarunSures41845 and @jackyk02, with @hangoo_kang)
- **Date:** HEAD `bb42c6c5bf914fd449bed2f6ca65be80602cb1f7` (2026-09-24) via GitHub API
- **Retrieved:** 2026-09-26 (README via raw.githubusercontent.com; not cloned)
- **Cited by evidence:** https://x.com/hxiao/status/2102930096827118053 (@hxiao, Jina: "not really listwise architecture"), https://x.com/TarunSures41845/status/2102914556427436180, https://x.com/rami_decodes/status/2103322751411097952, x:2103054339296403850, x:2103054230236123256, x:2103006942302245333, https://x.com/compassinai/status/2103789967369748607, https://x.com/overshadowed_x/status/2103415120403865886
- **Relevance to a memory stack:** medium. A second "System One" design with a different architecture (bi-encoder, cached action embeddings) and a claim that Jev fails as a verifier on long-horizon coding tasks, which bears on where decision models work.

## TL;DR
- CLM-8B: each encoder is "a frozen LLM backbone plus a 20M-parameter trainable projection head", trained with bidirectional InfoNCE; "pre-trained on 60M Nemotron Q&A pairs, mid-trained on 30M synthetic hard negatives, and post-trained on 1M agentic trajectories" (post-training mix 40% Nemotron DQA replay, 60% trajectories).
- Zero-shot: "on par with Jev across computer-use, gaming and tool-calling tasks with up to 9x lower latency" (T-Rex, BFCL v4, WikiRacing, Super Mario).
- As a verifier ranking multiple candidate solutions (fine-tuned heads): **Terminal-Bench 2.1 87.6%** (30 held-out tasks, Fable 5 candidates) and **DeepSWE 81.6% (31/38)** (Opus 5 candidates), 4.1 to 5.7x faster than Jev, on an H100.
- README caveat: "Jev fails to serve as a verifier for these long-horizon tasks, scoring below pass@1."
- @hxiao (Jina): actions are "independently encoded, so not really listwise".

## What it claims / describes
- States and actions are embedded separately; action embeddings can be cached and reused across contexts, which is where the speedup is largest ("when action sets are large or actions are reused").
- Verifier use: generate several candidate solutions with a frontier model, rank them with CLM, submit the top one.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| zero-shot parity with Jev | "on par" | Jev | T-Rex, BFCL v4, WikiRacing, Super Mario | per-task numbers not captured |
| latency advantage, zero-shot | up to 9x | Jev | same | best case |
| Terminal-Bench 2.1 (verifier) | 87.6% | Jev below pass@1 (per README) | 30 held-out tasks, Fable 5 candidates | fine-tuned heads |
| DeepSWE (verifier) | 81.6% (31/38) | same | 38 held-out tasks, Opus 5 candidates | |
| agentic speed | 4.1 to 5.7x faster than Jev | | H100 | |

## Mechanism details you could implement
- For choosing among many reusable actions (tools, memory ids, skills), a bi-encoder with cached action embeddings is cheaper than a per-call cross-attending decision model (inference from the architecture).
- Verifier ranking of N candidate patches with a trained head, if a held-out set shows it beats pass@1.

## Limitations, caveats, counter-evidence
- Author-run comparison; 30 and 38 task held-out sets; no intervals (one DeepSWE task = 2.6 points).
- Jev's verifier numbers and pass@1 baselines are not given as numbers in the captured README.
- Independent encoding of actions cannot model interactions between candidates (the @hxiao point); a listwise reranker may do better when candidates are near-duplicates (inference).

## Takeaways for tuning a memory stack
- Do not assume a decision model that ranks short options well will rank long code patches well; test it against pass@1 on our own review set.
- For memory-id or skill selection over a large, stable catalogue, cached-embedding scoring is an alternative worth a latency comparison.

## Open questions
- Per-task zero-shot numbers vs Jev? Not captured.
- Is there a paper with ablations? Not linked.

## Grading and labels
- Directness medium; control low; independence low; reproducibility medium (commit bb42c6c5); applicability medium.
- Pillar R4 (decision models as candidate implementations; where they fail). Secondary R3 (candidate scoring).
- Beliefs: supports B12 in spirit (a fast decision model alone does not carry open-ended long-horizon work; here it failed as a verifier per the CLM authors). Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
eight posts (above) -> github.com/contrastive-lm/clm @ bb42c6c5 README -> "Zero-Shot Evaluation" and "Agentic Benchmarks" sections -> HF org page (two models) -> this note. Independence: CLM authors vs TypeSafe; no shared authors with other notes.
