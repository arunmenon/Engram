---
schema_version: 1
artifact_id: N-20260928-15
artifact_type: note
producer: triage
run_id: triage-20260928T074501Z-535d
created_at: 2026-09-28T07:59:03Z
input_refs: [{"artifact_id": "post:2104415947260088450", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:SupersonicLabs/Julia-1
claim_cluster: hf:SupersonicLabs/Julia-1
feeds: ["memory"]
primary_source: https://huggingface.co/SupersonicLabs/Julia-1
source_commit: a85b127321d580d65176c89ced8273f305745d85
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: routing
priority: 2
tags: {"mechanism": ["encoder decision model", "option scoring", "hierarchical router", "ONNX WebGPU"], "workload": ["classification", "routing", "multilingual"], "lifecycle_stage": ["read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: correct/total counts per benchmark on the model card, with a metrics JSON", "control": "low: Jev numbers are supplied references, not a new Jev run; classification pilots are 100 examples; Banking77 used a top-16 shortlist", "independence": "medium: vendor (Supersonic Labs) grading its own model on a third-party benchmark", "reproducibility": "high: Apache-2.0 weights, inference code and pinned protocol links at a pinned revision", "applicability": "medium: small CPU-capable model for routing and gates; no memory-stage evaluation"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A 144M encoder decision model roughly matches Jev's typed-decisions accuracy (73.15% vs 72.70% reference) but falls far behind on long fine-grained label lists (Banking77 pilot 64/100 vs 87/100)"]}
claim_correction: The post says Julia-1 reports 73.15% "vs Jev's 72.70%" as if head to head; the card states "Jev numbers are supplied comparison references, not a new Jev run", the lead is 9 decisions of 2,000 (+0.45 pt), and the other comparisons are 100-example pilots.
---

# Julia 1 (Supersonic Labs): a 144M open-weight decision model compared with Jev

- **URL:** https://huggingface.co/SupersonicLabs/Julia-1 (vendor page https://supersoniclabs.ia.br/julia-1/)
- **Type:** model card with weights (Hugging Face) and vendor page
- **Author / org:** Supersonic Labs (@supersonicai); licence Apache-2.0; base `jhu-clsp/mmBERT-small`
- **Date:** HF revision `a85b127321d580d65176c89ced8273f305745d85` (2026-09-26T22:03:07Z); evaluation "Measured on 2026-09-24 with H200 BF16 inference and strict encoding"
- **Retrieved:** 2026-09-28: raw README.md via curl; vendor page via WebFetch.
- **Cited by evidence:** @aibuilderclub_ 2026-09-28 https://x.com/aibuilderclub_/status/2104415947260088450 quoting @supersonicai https://x.com/supersonicai/status/2103922653585162248
- **Relevance to a memory stack:** medium. A CPU and browser-capable open decision model for routing and simple gates; relevant to priority 2 (self-host, keep memory text in-house), weak on long label lists.

## TL;DR
- 144.3M parameters (mmBERT-small encoder plus a decision head), Apache-2.0, 550.5 MiB checkpoint; takes `state` + question + 2 to 20 options and returns one selected option with scores.
- Typed decisions: 73.15% (1,463/2,000) vs a supplied Jev reference 72.70% (+0.45 pt). By type: Choice 71.33% (428/600), Noul 80.67% (484/600), Score 68.88% (551/800).
- 100-example pilots: AG News 94 vs Jev 91; DAIR Emotion 86 vs Jev 48; Banking77 (72 labels, top-16 shortlist) 64 vs Jev 87.
- Speed (vendor page): Apple M4 33.15 ms median (28 to 51 decisions/s); Intel i5-1235U 89 to 294 ms; runs in the browser via ONNX Runtime WebGPU. API price stated as $0.025 per million input tokens. Training cost about US$104.08.
- No calibration metric is reported.

## What it claims / describes
- "At 144.3M parameters, it turns a state, a question, and possible answers into one clear decision. The same interface handles classification, routing, ordered scores, and Boolean decisions."
- "Julia compares the answers you provide; it cannot be counted on to supply missing facts, solve algebraic equations, or carry a long chain of calculations."
- Router: "The hierarchical `Router` can process larger choice lists by narrowing groups and reranking survivors, but each native model call still accepts 2-20 options; a grouped result is not a global probability distribution."
- Protocol: typed-decisions test cases; classification pilots "follow the pinned Jev benchmark protocol" (AbdelStark/jev-benchmarks@0d610cc) using BTZSC; "Abstentions count as incorrect."

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| typed decisions accuracy | 73.15% (1,463/2,000) | Jev reference 72.70% | typed-decisions test | Jev not re-run; benchmark card measured Jev 0.727 |
| Choice / Noul / Score | 71.33% / 80.67% / 68.88% | | same | |
| AG News, 4 labels | 94/100 | Jev 91 | pilot | n = 100 |
| DAIR Emotion, 6 labels | 86/100 | Jev 48 | pilot | n = 100 |
| Banking77, 72 labels | 64/100 | Jev 87 | pilot via top-16 shortlist | not a native 72-option call |
| MASSIVE, 52 locales | 71.50% (110,573/154,648) macro | none | 18 scenario labels | |
| MASSIVE en-US / pt-PT | 86.75% / 86.25% | | 2,974 per locale | |
| latency | 33.15 ms median, Apple M4 | | vendor page | |
| training cost | about US$104.08 (R$540) | | vendor page | |

## Mechanism details you could implement
- A small encoder that scores (state, question, option) and picks one; options capped at 20 per call, larger lists via a grouped router that narrows then reranks.
- Use strict encoding and keep options "clear and distinct"; evaluate on the exact questions you plan to use.
- ONNX export (Julia-1-ONNX repo) for browser or edge inference.

## Limitations, caveats, counter-evidence
- Card: "Ambiguous wording, unfamiliar domains, and long label lists can also cause mistakes"; "The 100-example pilots are encouraging signals, not guarantees for a new workflow."
- No probabilities calibration reported; a single selected option is the output focus, so it is unclear how usable its scores are as thresholds.
- Typed-decisions is saturated and teacher-labelled (see N-20260928-13); a 0.45 pt lead is 9 decisions.

## Takeaways for tuning a memory stack
- Candidate for cheap, local routing or recall-gate decisions with short option lists, not for rerank over dozens of memories (Banking77-style long lists are its weak spot).
- Any trial should measure calibration ourselves before using its scores as gate thresholds.

## Open questions
- How calibrated are its scores? How does it do as a pointwise memory reranker?

## Grading and labels
- Directness high; control low; independence medium; reproducibility high; applicability medium.
- Pillars: R9 primary, R4 secondary. Memory stage: routing. Priority 2. Products named: Jev, Julia-1.
- Beliefs: would create the belief in the frontmatter. No held belief is contradicted.
- Contradiction rows: none.

## Origin chain
- Post 2104415947260088450 (@aibuilderclub_) quoting @supersonicai 2103922653585162248 -> t.co/YJCdEeIBSo -> https://supersoniclabs.ia.br/julia-1/ -> HF card SupersonicLabs/Julia-1@a85b127 (Evaluation table) -> this note.
- Independence: shares the typed-decisions teacher labels with od1 and the benchmark card; Jev numbers are copied references.
