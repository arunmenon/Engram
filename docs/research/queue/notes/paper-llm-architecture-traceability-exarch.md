---
schema_version: 1
artifact_id: N-SURVEY-20261006-01
artifact_type: note
producer: triage
run_id: survey-20261006T054504Z-b489
created_at: 2026-10-06T06:30:00Z
idempotency_key: note:survey:arxiv:2511.02434
input_refs: []
pillar_primary: R10
pillar_secondary: [R9]
memory_stage: linking
priority: 3
beliefs_affected: {supports: [], contradicts: []}
evidence: {directness: high, control: medium, independence: medium, reproducibility: medium, applicability: medium}
source_url: https://arxiv.org/abs/2511.02434
found_via: survey
---

# Who's Who? LLM-assisted Software Traceability with Architecture Entity Recognition (ExArch, ArTEMiS)

- **URL:** https://arxiv.org/abs/2511.02434 (read: https://arxiv.org/html/2511.02434v2)
- **Type:** paper
- **Author / org:** Fuchß, Liu, Corallo, Hey, Keim, von Geisau, Koziolek (KIT, ARDoCo group)
- **Date:** v1 2025-11-04, v2 2026-03-19
- **Retrieved:** 2026-10-06
- **Cited by evidence:** survey run, R10 question 1
- **Relevance to a memory stack:** high; the closest published test of "LLM builds the intermediate model, then links design text to code", which is the design-to-code trace link in our PDLC ontology.

## TL;DR
- Linking architecture documentation (SAD) sentences to code files normally needs a hand-built architecture model (SAM). ExArch has an LLM extract component names from docs and code to build that model automatically.
- ExArch (GPT-4o) weighted-average F1 0.86 vs 0.87 for TransArC, which uses the hand-built model. Macro average is lower: 0.76 vs 0.82.
- ArTEMiS (GPT-5) links doc sentences to model entities at F1 0.81 average vs 0.80 for the older SWATTR; it wins on 2 of 5 projects and loses on 3.
- Gold standard is the group's own benchmark, revised by the authors after initial experiments.

## What it claims / describes
Two-step pipeline: (1) entity extraction: LLM names architecture components from documentation and from code package structure, names merged by normalized Levenshtein at t=0.5; (2) linking: sentences mapped to model entities (ArTEMiS uses text-embedding-3-large for entity matching), then model entities mapped to code files (TransArC style).

## Numbers
| Approach | MS | TS | TM | BBB | JR | Avg F1 | weighted Avg F1 |
|---|---|---|---|---|---|---|---|
| TransArC (manual SAM) | 0.68 | 0.83 | 0.80 | 0.84 | 0.94 | 0.82 | 0.87 |
| ExArch (GPT-4o) | 0.50 | 0.79 | 0.80 | 0.75 | 0.94 | 0.76 | 0.86 |
| ArDoCode | 0.09 | 0.31 | 0.53 | 0.13 | 0.80 | 0.37 | 0.62 |

| Project | SWATTR F1 | ArTEMiS (GPT-5) F1, 5 runs |
|---|---|---|
| MediaStore | 0.69 | 0.92 +/- 0.01 |
| TeaStore | 0.85 | 0.74 +/- 0.01 |
| TEAMMATES | 0.71 | 0.70 +/- 0.03 |
| BigBlueButton | 0.79 | 0.72 +/- 0.02 |
| JabRef | 0.95 | 0.98 +/- 0.02 |

Dataset sizes (gold links): MediaStore 59, TeaStore 707, TEAMMATES 8,097, BigBlueButton 1,529, JabRef 8,268. Weighted F1 is dominated by the two big projects. Models tried: GPT-3.5 through GPT-5, Codellama 13b, Llama 3.1 8b and 70b; per-model breakdown not extracted. Cost and latency: not stated in what was read. Judge: no LLM judge; scored against gold links.

## Mechanism details you could implement
- Build the node set first (components), then link. Extracting entities from both sides (docs and code structure) and merging by string similarity is cheap and nearly matches a hand-made model.
- Run nondeterministic LLM linkers several times and report variance (they ran 5).

## Limitations, caveats, counter-evidence
- Java/OO package structure only; production vs test code confused; LLMs poor at line numbers.
- Small projects swing hard (MediaStore 0.50 vs 0.68): the weighted average hides that.
- Authors revised their own gold standard after first experiments (inference: risk of tuning to the benchmark).

## Takeaways for tuning a memory stack
- For design-to-code links, an LLM-built intermediate node layer is close to hand-curated on large repos; on small repos expect a 0.1 to 0.2 F1 gap.
- Links through a typed intermediate node (component) are the pattern that works; direct text-to-code similarity (ArDoCode, 0.62) does not.

## Open questions
- Would a System One model doing the final link decision (step 2) match GPT-5? Not tested.
