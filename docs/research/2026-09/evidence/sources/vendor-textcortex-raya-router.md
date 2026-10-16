---
schema_version: 1
artifact_id: N-20260927-07
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103902544351404055", "file_id": null, "sha256": null}, {"artifact_id": "post:2103140962427871423", "file_id": null, "sha256": null}, {"artifact_id": "post:2103902547887243442", "file_id": null, "sha256": null}, {"artifact_id": "post:2103476730874785925", "file_id": null, "sha256": null}, {"artifact_id": "post:2103478844141527225", "file_id": null, "sha256": null}, {"artifact_id": "post:2103477090716676237", "file_id": null, "sha256": null}, {"artifact_id": "post:2103141083370950900", "file_id": null, "sha256": null}, {"artifact_id": "post:2103477341473382586", "file_id": null, "sha256": null}, {"artifact_id": "post:2103861739401949607", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:textcortex/raya
claim_cluster: hf:textcortex/raya
feeds: ["decision"]
primary_source: https://huggingface.co/TextCortex/raya
source_commit: unknown (model card revision not shown)
strength: vendor-benchmark
pillar_primary: R4
pillar_secondary: ["R7"]
tags: {"mechanism": ["fine-tuned encoder decision model", "soft labels from two annotators", "3-tier routing"], "workload": ["multilingual chat prompts", "WildChat-1M"], "lifecycle_stage": ["decision"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: model card table on the same 563-prompt set as the router blog", "control": "medium: same eval set and three question shapes as the Jev comparison; eval set built by the same author, overlap with training not stated beyond 'shards never used for training'", "independence": "low: author built both the benchmark and the fine-tune", "reproducibility": "medium: Apache-2.0 open weights, training folder published; revision not recorded", "applicability": "medium: shows a small local model can match a hosted decision API on one narrow decision after fine-tuning"}
beliefs_affected: {"supports": ["B14"], "contradicts": [], "would_create": ["A fine-tuned 3-tier router on an mmBERT-base encoder matched or beat Jev on score-shaped routing (80.3% vs 70.5%) but not on choice-shaped routing (81.0% vs 84.2%), on the author's own 563-prompt set"]}
claim_correction: "Beats Jev on difficulty scoring: 80.3% vs 70.5%" is true only for the score-shaped question; on both choice-shaped questions Jev is higher (84.2% vs 81.0% rubric choice, 84.5% vs 80.8% minimal choice). The post's "~30 ms vs ~330 ms" is stated as "17 ms (1x GPU, in-process)" on the model card; CPU latency figure not on the card read
---

# Raya: fine-tuned open router based on Laya (TextCortex/raya on Hugging Face)

- **URL:** https://huggingface.co/TextCortex/raya (training recipe at https://huggingface.co/TextCortex/raya/tree/main/training)
- **Type:** repo (model card)
- **Author / org:** TextCortex (Jay Derinbogaz); Apache-2.0
- **Date:** posts 2026-09-24 to 2026-09-26; model card revision not shown
- **Retrieved:** 2026-09-27 (model card page; revision unknown)
- **Cited by evidence:** @cderinbogaz https://x.com/cderinbogaz/status/2103902544351404055 , https://x.com/cderinbogaz/status/2103140962427871423 , https://x.com/cderinbogaz/status/2103902547887243442 , https://x.com/cderinbogaz/status/2103861739401949607 and thread posts 2103476730874785925, 2103478844141527225, 2103477090716676237, 2103141083370950900, 2103477341473382586
- **Relevance to a memory stack:** medium. Evidence that a narrow typed decision can be moved to a small local encoder with modest labelled data, which matters for data-residency constraints on hosted decision APIs (memory text leaving our infrastructure is a known cost in the synthesis section 5).

## TL;DR
- Base: `convaiinnovations/laya` (multilingual mmBERT-base encoder), fine-tuned for 3-tier routing (small / medium / frontier).
- Training data: WildChat-1M first-turn prompts + synthetic hard prompts + in-house routing data; "soft labels from two blind annotators; 50/50 target where they disagreed". Size not stated.
- On the 563-prompt set of N-20260927-06: difficulty score 80.3% (Raya) vs 70.5% (Jev) vs 61.6% (Laya stock); rubric choice 81.0% vs 84.2% vs 47.1%; minimal choice 80.8% vs 84.5% vs 55.2%.
- Latency: "17 ms (1x GPU, in-process)" vs "~330 ms (hosted API)".
- Card limitations: 2 to 3 tiers for chat/assistant traffic only; not for safety moderation; not validated on multi-turn context.

## What it claims / describes
- An open-weights router for EU deployment where Jev is unavailable. Test set: 563 prompts, 14 languages, about 40 per language, "75% natural + 25% hard-leaning"; gold tier = the tier two independent blind annotators (Claude Opus and Sonnet) both assigned; test shards "never used for training".

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| accuracy, difficulty-score shape | Raya 80.3% | Jev 70.5%; Laya stock 61.6% | 563 prompts, model card | same author built the set |
| accuracy, rubric choice | Raya 81.0% | Jev 84.2%; Laya 47.1% | same | Jev higher |
| accuracy, minimal choice | Raya 80.8% | Jev 84.5%; Laya 55.2% | same | Jev higher |
| latency | 17 ms, 1x GPU in-process | Jev ~330 ms hosted | model card | post says ~30 ms on CPU; not verified |

## Mechanism details you could implement
- Fine-tune a small multilingual encoder on soft labels (average of two annotators; 50/50 where they disagree) for one fixed decision; keep test shards disjoint from training.
- Compare against the hosted decision model on each question shape separately; the win may be shape-specific.

## Limitations, caveats, counter-evidence
- Card: "For 2-3 model tiers for chat/assistant traffic. Not for safety moderation or more than 3 tiers. Not validated on multi-turn context."
- Training set size not stated; in-house data not released; overlap statement is only "shards never used for training".
- Jev comparison numbers come from the author's earlier run (N-20260927-06), not rerun on the card.
- Headline in the post compares Raya's best shape to Jev's worst shape (score).

## Takeaways for tuning a memory stack
- For a single, stable typed decision (for example our admission or recall gate) a fine-tuned local encoder is a realistic fallback to a hosted decision API when data cannot leave our infrastructure; budget a labelled set per decision.
- Always compare like-for-like question shapes.

## Open questions
- Training set size and label source mix; performance on the disagreement prompts excluded from gold.
- CPU latency and cost at production volume.

## Grading and labels
- Directness high; control medium; independence low; reproducibility medium; applicability medium.
- Pillars: R4 primary (candidate implementation of a typed decision); R7 secondary (deployment and data-residency constraint on a hosted API).
- B14 supports: fit decisions locally rather than trusting vendor behaviour; here local fitting closed most of the gap.
- Would create: fine-tuned encoder matched a hosted decision model on one shape but not others (one author's set).
- No contradiction rows.

## Origin chain
posts by @cderinbogaz (2103140962427871423 weights link; 2103902544351404055 headline; 2103902547887243442 recipe link; thread 2103476730874785925 etc.; 2103861739401949607 asking @theo to benchmark Raya) -> Hugging Face model card TextCortex/raya -> metrics table and limitations -> this note. Independence: same author and eval set as N-20260927-06.
