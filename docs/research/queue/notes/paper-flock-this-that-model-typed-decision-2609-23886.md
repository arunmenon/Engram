---
schema_version: 1
artifact_id: N-20260926-21
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:18:28Z
input_refs: [{"artifact_id": "post:2103477316836016515", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.23886
claim_cluster: arxiv:2609.23886
feeds: ["memory", "decision"]
primary_source: https://arxiv.org/abs/2609.23886
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R4
pillar_secondary: []
tags: {"mechanism": ["typed decision head read from hidden state", "local 2B decision model", "Brier / NLL reporting"], "workload": ["small typed questions (geometry states)"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: accuracy, Brier and NLL per system, but on 68 questions", "control": "low: third-party set of 68 questions over 17 states; own suite built by the authors", "independence": "low: FLock.io authors releasing the model", "reproducibility": "medium: MIT weights on Hugging Face; test set published by a third party", "applicability": "low-medium: a local option for cheap typed decisions; the tested questions are geometry, not memory or code"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": []}
claim_correction: Posts present 0.941 vs 0.765 as beating commercial services; the comparison is 68 questions over 17 states from a third-party NanoJev geometry cohort (0.765 is hosted Jev), and the authors state that on the harder half of their own suite the model is not more accurate than frontier models.
---

# this-that-model-1.0: A typed decision model that decides in 30 ms (arXiv 2609.23886, FLock.io)

- **URL:** https://arxiv.org/abs/2609.23886 (HTML read); weights huggingface.co/flock-io/this-that-model-1.0 (MIT)
- **Type:** paper (vendor)
- **Author / org:** Zehua Cheng, Wei Dai, Jiahao Sun (FLock.io)
- **Date:** 2026-09-20
- **Retrieved:** 2026-09-26
- **Cited by evidence:** https://x.com/flock_io/status/2103477316836016515 (@flock_io)
- **Relevance to a memory stack:** low-medium. Another local typed-decision model with explicit Brier/NLL reporting; useful mainly as a calibration-reporting template and a local fallback candidate.

## TL;DR
- 1.88B parameters adapted from decider-2b; reads the answer "directly from the hidden state at a designated position" over predefined options.
- Table 1 on a third-party cohort (NanoJev's 68 geometry questions over 17 states, sent to hosted Jev and published): **accuracy 0.941, Brier 0.042, NLL 0.126, 30.9 ms per question**, $0.000014 per pass (electricity at 80 W and $0.30/kWh); hosted Jev 0.765. Also compared: claude-fable-5-1, glm-5.3, qwen3.8-max, NanoJev-0.6B, kimi-k3, deepseek-v4.1-flash, gpt-5.6 (their scores not captured).
- Against computed answer distributions (Table 2): accuracy 0.745, qL2 0.0248 near a 0.746 ceiling.
- Weakness: multi-step arithmetic 0.560 vs 0.98 to 1.00 for large systems; "on the harder half of our suite it is not" more accurate than frontier models.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| accuracy | 0.941 | hosted Jev 0.765 | 68 questions, 17 states | tiny, one domain |
| Brier / NLL | 0.042 / 0.126 | not captured for others | Table 1 | |
| latency | 30.9 ms | hosted: client-measured median | single consumer GPU | local vs network |
| cost per pass | $0.000014 | | electricity only | excludes hardware |
| distribution match | acc 0.745, qL2 0.0248 | ceiling 0.746 | Table 2 | |
| multi-step arithmetic | 0.560 | 0.98 to 1.00 | | |

## Mechanism details you could implement
- Report Brier and NLL alongside accuracy for any decision component; compare to hosted Jev on the same items.

## Limitations, caveats, counter-evidence
- 68-question comparison; own training suite (7,305 questions over 15 families, 60,200 generated) is in-distribution; vendor authors.

## Takeaways for tuning a memory stack
- A local typed-decision model is plausible as an offline fallback (the synthesis notes Jev fails closed), but must be validated on our questions; do not read 0.941 vs 0.765 as general.

## Open questions
- Performance on memory-write and relevance questions? Not tested.

## Grading and labels
- Directness medium; control low; independence low; reproducibility medium; applicability low-medium.
- Pillar R4. Beliefs: supports B14 (the hosted model's calibration is not a given; here a competitor reports its own Brier; hosted Jev's Brier not captured). Contradiction rows: none.

## Origin chain
post 2103477316836016515 (@flock_io) -> arXiv 2609.23886 (HTML) -> Table 1, Table 2, limitations -> this note. Independence: FLock.io authors; test cohort published by NanoJev (third party).
