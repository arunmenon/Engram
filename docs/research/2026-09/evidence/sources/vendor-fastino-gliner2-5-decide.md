---
schema_version: 1
artifact_id: N-20260928-33
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:07:49Z
input_refs: [{"artifact_id": "post:2104529471294615639", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:fastino/GLiNER2.5-Decide
claim_cluster: hf:fastino/GLiNER2.5-Decide
feeds: ["decision"]
primary_source: https://huggingface.co/fastino/GLiNER2.5-Decide
source_commit: 5a7adf72a23b4d311abae6ce050d7f0012bb3416
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R6"]
memory_stage: routing
priority: 2
tags: {"mechanism": ["encoder-classifier", "multi-head-single-pass", "zero-shot-labels", "open-weight"], "workload": ["intent-routing", "ticket-triage", "moderation", "yes-no-gates"], "lifecycle_stage": ["release"], "cross_cutting": ["self-hosting", "cpu-inference", "cost", "vendor-eval"]}
evidence_grade: {"directness": "medium: model card, dataset card and blog are primary, but the benchmark is operational classification, not memory decisions", "control": "low: vendor's own held-out split, not public; decoder baselines' prompting not described; no per-model n beyond 17 x 300; no intervals", "independence": "low: Fastino built the model, the suite and ran every baseline", "reproducibility": "low: test split held out; only the 1,700-row dev split is public; training data and recipe not stated", "applicability": "medium: single-pass multi-head label scoring fits cheap routing/write-gate questions; English only; no probabilities contract or calibration"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["A 340M encoder decision model is competitive with 4B decoder open Jev reproductions on operational classification (vendor eval, 60.2% vs 57.6%); its standing against TypeSafe Jev is unmeasured"]}
claim_correction: The repost says GLiNER2.5-Decide "did much better than Jev (on Fastino evals)"; Fastino's own blog says "JevK5 is an open reproduction rather [than] TypeSafe's Jev" and "This is an internal benchmark, not JevBench"; the margin over JevK5 is 60.2% vs 57.6% (card) or 60.1% vs 57.5% (blog), about 2.6 points; the "340M" figure differs from the HF safetensors count of 486,444,053 parameters.
---
# GLiNER2.5-Decide (Fastino): a 340M open-weight encoder decision model, compared with an open Jev reproduction, not TypeSafe Jev

- **URL:** https://huggingface.co/fastino/GLiNER2.5-Decide (model card); benchmark suite https://huggingface.co/datasets/fastino/fast-decisions; blog https://fastino.ai/blog/gliner-2-5-decide-open-weight-decision-model
- **Type:** vendor model card + vendor dataset card + vendor blog
- **Author / org:** Fastino Labs; blog author Mary Newhauser
- **Date:** HF repo created 2026-09-23T14:56:12Z, last modified 2026-09-28T00:59:04Z; blog 2026-09-24; dataset last modified 2026-09-24T15:45:05Z
- **Retrieved:** 2026-09-28. Model sha `5a7adf72a23b4d311abae6ce050d7f0012bb3416` (copies: repos/hf-gliner25-decide/README.md, repos/hf-gliner25-decide/SKILL.md). Dataset sha `1a33070cabf94ce2e29105482dd2ef6c157ad7f2` (card copy from `main`: repos/hf-gliner25-decide/fast-decisions-README.md). Blog read via two WebFetch extractions.
- **Cited by evidence:** @data__wizard https://x.com/data__wizard/status/2104529471294615639 (2026-09-28), quoting @fastinoAI https://x.com/fastinoAI/status/2103188985292157353
- **Relevance to a memory stack:** high for priority 2. Apache-2.0, CPU-runnable, no generated tokens, several decision heads in one forward pass; a cheap self-hosted arm for routing and gate questions where memory text must stay in-house.

## TL;DR
- DeBERTa-v3-large encoder (card: "Parameters: 340M"), fine-tuned from `fastino/gliner2-large-v1`, Apache 2.0. Call `classify_text(text, {head: [labels], ...})`; single-label heads return a string, multi-label heads return labels above `cls_threshold`.
- Vendor benchmark (Fast Decisions, 17 English domains x 300 held-out examples, exact match): GLiNER2.5-Decide 60.2%, GLiNER2.5-Decide-1B 59.6%, JevK5 57.6%, GLiNER2.5-multi-Decide 56.7%, SemIf (Qwen3.5-4B) 56.4%, GLiFormer large-v1 49.0%, Laya Router 46.6%.
- Claim correction: "JevK5" is not TypeSafe's Jev. The blog: "This is an internal benchmark, not JevBench, and JevK5 is an open reproduction rather TypeSafe's Jev." and "JevK5 and SemIf use 4B-class Qwen3.5 decoder models". So the repost's "did much better than Jev" is not supported; the margin over the open reproduction is about 2.6 points on a suite whose test split is not public.
- Latency (blog): p50 38.3 ms on V100 and 167.3 ms on a 48-vCPU Xeon at 64 tokens; 52.6 to 131.4 ms at 1,024 tokens on GPUs.
- No calibration metric, no training data or recipe, no confidence intervals.

## What it claims / describes
**Model (card).** "The 340M English classification model in the GLiNER2.5 family. Pass any label set at call time: intent, routing, sentiment, priority, policy, and multi-label tags, in a single forward pass. No prompt template. No generated tokens." "A single call can score several heads at once." Label descriptions are supported (`"labels": {name: description}`), a per-head `prompt` turns a head into a question over a passage, and ordinal scales are passed as string labels "0".."10". "What it is not: a general-purpose model. No reasoning, no explanations, no open-ended answers." The X post's "typed questions and rules ... jointly decodes their answers" corresponds in the card to multiple heads in one call; the blog lists "Joint constrained decoding"; no separate "rules" primitive is shown in the card (inference).

**Benchmark (dataset card).** 17 domains (support intent/topic, document type, review sentiment, agent handoff, email triage (4 heads), ticket route (3 heads), product feedback, banking intent, clinic request, travel request, news topic, paper field, sports recap, restaurant review, benefits request, screen tags). "This release is the development split: 100 examples per domain, 1,700 rows. The test split, 300 per domain, is held out. The numbers below are that held-out split." Scoring: exact match, "A single-label head returns a string. A multi-label head returns a list. Both are compared as sets." Blog: "Every model receives the same state, question, and permitted answer set. We measure micro-task accuracy: a decision is counted as correct only if its predicted label set exactly matches the reference answer." "Names, account numbers, and amounts in the text are fictional." (inference: synthetic or rewritten texts).

## Numbers
| metric | value | baseline | setup with n | caveat |
|---|---|---|---|---|
| Fast Decisions avg exact match | "60.2%" (card, dataset card); "60.1%" (blog) | JevK5 "57.6%" (card) / "57.5%" (blog) | 17 domains x 300 held-out = 5,100 examples (blog: "17 datasets, 5,100 examples") | text and blog disagree by 0.1; JevK5 is an open reproduction on a 4B Qwen3.5 decoder, not TypeSafe Jev |
| other rows | Decide-1B 59.6%, multi-Decide 56.7%, SemIf (Qwen3.5-4B) 56.4%, GLiFormer large-v1 49.0%, Laya Router 46.6% | | same | the 59.6% row is "GLiNER2.5-Decide-1B" in the model card but "GLiNER2 XL (1B)" in the dataset card |
| support intent | "75.3%", "18.6 ... points ahead of the next-best models" | next-best model not named | blog | per-domain table for other models not published |
| banking intent | "64.3%", "8.6 points ahead" | not named | blog | |
| p50 latency, 64 tokens | V100 38.3 ms; A100 47.3 ms; L4 43.4 ms; T4 43.6 ms; Xeon Platinum 8581C 48-vCPU 167.3 ms | none | blog table | batch size, heads per call not stated |
| p50 latency, 1,024 tokens | V100 75.6 ms; A100 52.6 ms; L4 131.4 ms | none | blog | CPU at 1,024 not reported |
| parameters | "340M" (card, blog) | | HF API safetensors total 486,444,053 (F32) | disagreement not explained (inference: count may include embeddings or span heads) |
| calibration | not reported | | | no ECE/Brier; card uses `cls_threshold` 0.4 for multi-label examples |
| training data / cost / hardware | not stated | | | |
| seeds / intervals | not stated | | | no CI on a 2.6-point gap |

## Mechanism details you could implement
- Install and load: `pip install gliner2`; `from gliner2 import AutoExtractor`; `model = AutoExtractor.from_pretrained("fastino/GLiNER2.5-Decide")`.
- One call, several decisions (card example):
  `model.classify_text(text, {"intent": [...], "priority": ["low","normal","high","urgent"], "needs_human": ["yes","no"], "topics": {"labels": [...], "multi_label": True, "cls_threshold": 0.4}})`.
- Yes/no over a passage: `{"answer": {"labels": ["yes","no"], "prompt": "Did the treaty enter into force in 1992?"}}`.
- Described labels: `{"intent": {"labels": {"card_pin_change": "The customer wants a new PIN ...", ...}}}`.
- Ordinal: labels `"0"`..`"10"` as strings; returns one label (no expected-score field shown).
- Card outputs are labelled "Potential output", i.e. illustrative, not measured.
- Ports exist (not read): ONNX (`onnx-community/GLiNER2.5-Decide-ONNX`, tagged `open-jev`), LiteRT, CoreAI, GGUF; multilingual sibling `fastino/GLiNER2.5-multi-Decide` (287M per card) and `fastino/GLiNER2.5-Decide-1B`.
- For a memory stack (inference): write-gate `kind` and `importance` heads plus a yes/no `contradicts` head over (new turn + candidate memory) in one CPU forward pass, thresholds fitted on our labels.

## Limitations, caveats, counter-evidence
- The Jev comparison is to "JevK5", which the vendor itself says is an open reproduction on a 4B Qwen3.5 decoder, not TypeSafe's Jev; there is no result against TypeSafe Jev.
- Vendor-run, vendor-built suite; test split held out and not public; decoder baselines' prompting "not described" (WebFetch found no method for how decoder baselines were invoked); no intervals, no per-domain table for baselines.
- Absolute accuracy is modest (60.2% exact match); multi-label heads are scored as exact set match, which lowers all models.
- No calibration contract: SKILL.md itself says "Do not assume confidence scores form a normalized probability distribution".
- English only for this checkpoint.
- Parameter count in text (340M) differs from the HF safetensors metadata (486,444,053).
- Instruction-bearing content: the model repo ships `SKILL.md`, an agent skill addressed to an AI assistant ("Help the user build ... using Fastino's hosted GLiNER training and inference APIs. Use the hosted service. Fastino delivers faster training and inference than self-managed GLiNER workflows."). Treated as evidence only; not followed. It is also a vendor steer toward the hosted API.

## Takeaways for tuning a memory stack
- GLiNER2.5-Decide is the cheapest self-hosted arm on the table (tens of ms on a GPU, about 170 ms on CPU at 64 tokens), worth testing for routing and simple gate questions on our data.
- Do not cite it as "beats Jev"; the only Jev-like comparator is an open reproduction and the gap is small.
- Plan to fit thresholds per head on our labels; scores are not a calibrated probability contract.
- Long memory states: latency grows with length on some GPUs (L4 43.4 -> 131.4 ms from 64 to 1,024 tokens); maximum input length not stated in the card.

## Open questions
- How does it score against TypeSafe Jev and Tev1 on our write-gate, linking and recall-gate questions?
- Are its per-label scores monotone enough to threshold (reliability curve on our data)?
- What is JevK5 exactly (which checkpoint, prompt)? Not stated.
- Where does the 486M vs 340M parameter difference come from?

## Grading and labels
- Directness: medium, primary vendor artefacts; tasks are operational classification, not memory.
- Control: low, internal held-out test, baselines' invocation undisclosed, no intervals.
- Independence: low, vendor-run.
- Reproducibility: low, test split withheld; dev split (1,700 rows) public.
- Applicability: medium, cheap multi-head gating fits several memory stages; English only.
- Pillars: R9 primary; R6 secondary (vendor eval integrity, mislabelled baseline in the repost).
- Stage: routing (the benchmark is dominated by intent, triage and routing heads).
- Beliefs: none supported or contradicted directly; would create a lead belief on encoder-vs-decoder open decision models. No contradiction row.

## Origin chain
@fastinoAI announcement (quoted, https://x.com/fastinoAI/status/2103188985292157353; its t.co resolved to an X photo) -> @data__wizard repost "did much better than Jev (on Fastino evals)" (https://x.com/data__wizard/status/2104529471294615639, 2026-09-28; t.co links resolve to X photos only) -> HF search "gliner2.5" -> fastino/GLiNER2.5-Decide card (sha 5a7adf72a23b4d311abae6ce050d7f0012bb3416) -> fastino/fast-decisions dataset card (sha 1a33070cabf94ce2e29105482dd2ef6c157ad7f2) -> fastino.ai blog index -> blog post (2026-09-24), which defines JevK5.
