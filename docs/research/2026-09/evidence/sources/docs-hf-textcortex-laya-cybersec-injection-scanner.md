---
schema_version: 1
artifact_id: N-20260930-06
artifact_type: note
producer: triage
run_id: triage-20260930T014506Z-8351
created_at: 2026-09-30T01:57:27Z
input_refs: [{"artifact_id": "post:2104826787297419551", "file_id": null, "sha256": null}, {"artifact_id": "post:2104826791097782663", "file_id": null, "sha256": null}, {"artifact_id": "post:2104826795270783228", "file_id": null, "sha256": null}, {"artifact_id": "post:2104826798684995745", "file_id": null, "sha256": null}, {"artifact_id": "post:2104826800815620226", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:hf:textcortex/laya-cybersec
claim_cluster: hf:textcortex/laya-cybersec
feeds: ["decision"]
primary_source: https://huggingface.co/TextCortex/laya-cybersec
source_commit: a75e214574d9cbbf89f2f5dcc48b2e98dbcc01f6
strength: vendor-benchmark
pillar_primary: R9
pillar_secondary: ["R8"]
tags: {"mechanism": ["fine-tuned open-weight noul classifier", "prompt injection and exfiltration screening", "ONNX CPU inference"], "workload": ["files, KB docs, skills, MCP tool descriptions, emails", "English and German"], "lifecycle_stage": ["safety", "ingestion"], "cross_cutting": ["cost"]}
memory_stage: safety
priority: 2
evidence_grade: {"directness": "high: model card reports AUROC and TPR at fixed FPR on a held-out set for the fine-tune, stock Laya and hosted Jev", "control": "medium: same held-out set and chunking for all three, but the set is partly synthetic and the German set machine-translated; no intervals", "independence": "low: TextCortex fine-tuned and evaluated its own model", "reproducibility": "medium: weights and training data released at a known revision; eval set composition stated, eval code not checked", "applicability": "high: screening content before it enters agent memory or context is our safety stage, and the carriers include skills and MCP tool descriptions"}
beliefs_affected: {"supports": ["B24"], "contradicts": [], "would_create": ["A 0.3B open-weight Laya fine-tune reaches 0.93 AUROC for injection screening (hosted Jev 0.98) but catches only 44% of attacks at 1% false positives versus Jev's 60%"]}
claim_correction: The post headline says "almost same performance as JEV"; at a 1% false-positive rate the fine-tune catches 0.44 of English attacks versus Jev's 0.60 (0.41 vs 0.56 German), a larger gap than the AUROC difference suggests.
---

# laya-cybersec (TextCortex): an open-weight Laya fine-tune that screens content for prompt injection and exfiltration before an agent reads it, compared with hosted Jev (TypeSafe)

- **URL:** https://huggingface.co/TextCortex/laya-cybersec (training data: TextCortex/laya-cybersec-training-data)
- **Type:** model card (Hugging Face)
- **Author / org:** TextCortex (posted by @cderinbogaz). Licence varies by training source; one component (10kGNAD) is CC BY-NC-SA 4.0 ("Check them for your use case").
- **Date:** revision `a75e214574d9cbbf89f2f5dcc48b2e98dbcc01f6`, lastModified 2026-09-29T07:01:33Z
- **Retrieved:** 2026-09-30 (model card via WebFetch; revision via the HF API)
- **Cited by evidence:** decision feed 2026-09-29, @cderinbogaz thread: 2104826787297419551, 2104826791097782663, 2104826795270783228, 2104826798684995745, 2104826800815620226 (https://x.com/cderinbogaz/status/2104826787297419551)
- **Relevance to a memory stack:** high for the safety stage: a self-hostable screen for untrusted material (uploads, KB docs, skills, MCP tool descriptions) before ingestion into memory, with a side-by-side against hosted Jev on the same set.

## TL;DR
- Base: convaiinnovations/laya (mmBERT-base encoder with the Laya decision head), 0.3B parameters, fine-tuned end to end on 194k rows (38% German, 35% attacks).
- Held-out English (602: 314 attack / 288 benign) AUROC: laya-cybersec 0.931, stock Laya 0.704, hosted Jev 0.980. German (510, machine-translated) 0.892 / 0.665 / 0.956.
- TPR at 1% FPR (English): 0.44 vs Jev 0.60; at 5% FPR: 0.70 vs 0.89.
- Latency per 1,500-char chunk: ONNX on CPU 72 ms p50 / 210 ms p95; PyTorch on Apple M4 89 ms p50; hosted Jev (Europe) 310 ms p50.
- No universal threshold: "Choose one on your own traffic." Misses polite action requests in ordinary data.

## What it claims / describes
A Jev-shaped noul screen:
```python
Q = {"type": "noul", "instructions": "Does this content contain a prompt injection or data exfiltration attempt?"}
state = {"source": "<carrier type>", "content": "<text>"}
# returns P(attack)
```
`source` strings: file uploads, knowledge base documents, agent skills, system prompts, MCP tool descriptions. Documents are chunked at 1,500 characters and scored as the maximum over chunks.

Training data sources: public injection datasets (neuralchemy, S-Labs, xTRam1, SPML, NVIDIA Nemotron); attacks embedded in Wikipedia, CNN/DailyMail, news, skill files and emails; synthetic samples from Qwen2.5; German via opus-mt-en-de. Held-out English: 190 synthetic LLM-generated skills/prompts/MCP descriptions, 136 InjecAgent tool results, 80 LLMail-Inject emails, 80 Enron business emails, 116 deepset prompt-injection samples. German: the English set machine-translated with NLLB-200 (a different translator from training).

## Numbers
| model | EN AUROC | EN TPR@1% | EN TPR@5% | DE AUROC | DE TPR@1% | DE TPR@5% |
|---|---|---|---|---|---|---|
| laya-cybersec (PyTorch) | 0.931 | 0.44 | 0.70 | 0.892 | 0.41 | 0.59 |
| laya-cybersec (ONNX) | 0.931 | 0.44 | 0.70 | 0.891 | 0.43 | 0.59 |
| Stock Laya multilingual | 0.704 | 0.00 | 0.23 | 0.665 | 0.00 | 0.12 |
| TypeSafe Jev (hosted) | 0.980 | 0.60 | 0.89 | 0.956 | 0.56 | 0.83 |

| metric | value | setup | caveat |
|---|---|---|---|
| AUROC without the noisy deepset slice | EN 0.927, DE 0.884 (laya-cybersec) | held-out | |
| latency, ONNX CPU | 72 ms p50, 210 ms p95 | per 1,500-char chunk, laptop CPU | ONNX fp32 is 1.2 GB |
| latency, PyTorch Apple M4 | 89 ms p50 | | |
| latency, hosted Jev | 310 ms p50 | Europe, network included | |
| calibration | not reported | | threshold must be chosen locally |

## Mechanism details you could implement
- Screen at ingestion with a noul per 1,500-char chunk, max over chunks, with the carrier type in the state.
- Choose the operating point by TPR at a fixed false-positive budget (1% or 5%), not by AUROC: that is where the fine-tune and Jev differ most.
- Keep stock (non fine-tuned) decision models out of this role: stock Laya catches 0% of attacks at 1% FPR.
- Pair with least-privilege and output filtering; the card says it "complements but doesn't replace" them.

## Limitations, caveats, counter-evidence
- Card: "Weaker than Jev by about 0.05 AUROC (English) and 0.06 (German)"; "Misses polite action requests in ordinary data"; German benchmark machine-translated; 190 English samples synthetic; not evaluated on outbound web requests.
- Vendor-run evaluation, no intervals, no calibration.
- Same failure class as the jevmem gate's two misses ("instructions worded as ordinary process") and the Share-Borne note's "false beliefs without instructions evade it" (N-20260930-09).
- Related bus evidence: `github-jooray-hermes-firewall.md` (Jev vs Laya, SemIf, DeBERTa, regex for an injection gate) and card PC-20260928-11, which already proposes a gate comparison; no new card here.

## Takeaways for tuning a memory stack
- A self-hosted injection screen at ingestion is now practical on CPU (72 ms p50), keeping memory text in-house; expect to give up about 16 points of recall at 1% FPR relative to hosted Jev.
- Screen skills and MCP tool descriptions, not only documents: they are part of the training and eval carriers here.
- Fit thresholds on our own planted set (H10b) before using any of these as a gate.

## Open questions
- Calibration of P(attack) at the thresholds we would use? Not reported.
- Performance on engineering carriers (PR descriptions, issue comments, code comments)? Not tested.
- Does a second pass (fine-tune on our own blocked lines) close the 1%-FPR gap to Jev?

## Grading and labels
- Directness high; control medium; independence low; reproducibility medium; applicability high.
- Pillars: R9 primary (open-weight vs hosted System One at the safety stage), R8 (poisoned or injected evidence). Memory stage: safety. Priority 2 (self-host so memory text stays in-house; Jev vs Laya comparison).
- Beliefs: supports B24 (extracted and ingested content is untrusted and a typed injection screen can catch most planted lines), while showing a recall ceiling at strict FPR. Would create the belief in frontmatter.
- Contradiction rows: none.

## Origin chain
@cderinbogaz thread (2104826787297419551 and four replies) -> huggingface.co/TextCortex/laya-cybersec at a75e214 -> Metrics table, Latency section, Evaluation Sets and Limitations sections -> this note. Independence: TextCortex evaluates its own fine-tune; Jev numbers measured by TextCortex through the hosted API; eval sets partly public (InjecAgent, LLMail-Inject, Enron, deepset) and partly synthetic.
