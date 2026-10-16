---
schema_version: 1
artifact_id: N-SURVEY-20261001-02
artifact_type: note
producer: triage
run_id: survey-20261001T054505Z-09ae
created_at: 2026-10-01T06:02:00Z
idempotency_key: note:survey:arxiv:2607.18886
input_refs: []
pillar_primary: R10
pillar_secondary: [R3, R6]
memory_stage: linking
priority: 3
beliefs_affected:
  supports: [B8]
  contradicts: []
evidence:
  directness: 3
  control: 3
  independence: 3
  reproducibility: 3
  applicability: 3
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2607.18886
found_via: survey
claim_cluster: tracedev-requirement-design-code-graph-validator
---

# TraceDev: A Traceability-Driven Multi-agent Framework for Requirement-to-Code Development (arXiv 2607.18886, ISSTA 2026)

- **URL:** https://arxiv.org/abs/2607.18886 (read: https://arxiv.org/html/2607.18886v1); code and data https://github.com/ISSE-Lab/ISSTA2026-TraceDev (commit pinning not checked)
- **Type:** paper
- **Author / org:** ISSE Lab (author names not captured)
- **Date:** 2026-07-21
- **Retrieved:** 2026-10-01
- **Cited by evidence:** survey run, R10 plan question 2. Listed in `memory-research-landscape.md` row 6.4 and `pdlc-memory-layer.md` section 2 with no numbers; this note adds them.
- **Relevance to a memory stack:** medium. It is the closest published system to "a requirement to design to code graph that agents read and repair", and it has an ablation that removes the graph's validator. It measures code generation, not memory recall, and has no test nodes in the graph.

## TL;DR
- A multi-agent pipeline keeps a traceability graph (requirement elements to design entities to code files) and a Validator walks it for missing or broken links, feeding defects back for repair.
- On two classic traceability datasets turned into generation tasks (ETOUR 58 use cases, SMOS 67), TraceDev roughly doubles task success over ChatDev and MetaGPT with the same base model (for example ETOUR, Gemini-2.5-Flash: 53.63% vs 23.40% vs 18.71%).
- Removing the Validator (the graph-walking agent) dropped ETOUR / DeepSeek-V3.2 success from 47.19% to 28.37% and semantic coverage from 54.78% to 39.91% (Figure 8).
- Removing the Tester hurt most (13.92% success), so the graph is not the only load-bearing part.
- Cost: about 109.5k tokens and 385 s per ETOUR task (Gemini-2.5-Flash), slower than ChatDev (219.5 s) at similar tokens.

## What it claims / describes
Nodes, verbatim from the paper's description:
- Requirements: "actors, entry/exit conditions, flow steps, and quality requirements" (from structured use cases).
- Design: "classes, methods, relations, and messages".
- Code: "each generated code file is modeled as a node".

Edges:
1. Requirement to design: "the LLM analyzes each requirement element ... and identifies relevant design entities".
2. Design to code: deterministic, "Abstract Syntax Tree (AST) parsing ... to analyze the generated code".

Agents: Designer, Coder, Validator (traverses the graph to find requirement elements without design or code coverage), Tester, Refiner. Repair is bounded to 3 iterations and test remediation to 5 attempts.

## Numbers

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Semantic coverage / success, ETOUR | 71.72% / 53.63% | ChatDev 47.29 / 23.40; MetaGPT 40.95 / 18.71 | Gemini-2.5-Flash, 58 use cases | coverage judged how is not captured in this read |
| Same, SMOS | 70.05% / 56.82% | ChatDev 42.49 / 24.74; MetaGPT 37.40 / 12.89 | Gemini-2.5-Flash, 67 use cases | |
| Same, ETOUR | 54.78% / 47.19% | ChatDev 41.58 / 16.52; MetaGPT 37.01 / 20.01 | DeepSeek-V3.2 | |
| Same, SMOS | 58.60% / 44.78% | ChatDev 31.46 / 16.80; MetaGPT 33.41 / 16.01 | DeepSeek-V3.2 | |
| Ablation without Validator | 39.91% / 28.37% | full 54.78 / 47.19 | ETOUR, DeepSeek-V3.2, Figure 8 | one dataset, one model, read from a figure |
| Ablation without Designer | 45.21% / 36.79% | same | same | |
| Ablation without Tester | 40.64% / 13.92% | same | same | largest drop |
| Ablation without Refiner | 43.13% / 28.27% | same | same | |
| Human executability rating | 3.60 to 3.66 | ChatDev / MetaGPT 2.03 to 2.9 | Krippendorff alpha 0.940 | scale not captured |
| Tokens / time per task | 109,541 / 385.06 s | ChatDev 98,766 / 219.50 s; MetaGPT 219,758 / 169.30 s | ETOUR, Gemini-2.5-Flash, Table 3 | |
| Trace-link precision / recall | not reported | | | the graph's own link accuracy is not measured |

## Mechanism details you could implement
- Split link creation by evidence type: model-decided for requirement to design (semantic), parser-decided for design to code (AST symbols). Only the first needs a decision model; the second is exact (inference: matches the LinkRank finding in N-SURVEY-20260929-06 that cheap structural signals carry much of the code side).
- A completeness walk as a first-class check: for each requirement element, is there at least one design entity and one code node reachable? This is the set-difference "completeness" retrieval mode in `pdlc-memory-layer.md` section 4.
- Bounded repair loops (3 and 5) keep cost finite.

## Limitations, caveats, counter-evidence
- Requires structured use cases; "non-use-case requirements ... require redesigning the schema".
- "Test cases not explicitly modeled in traceability graph", so VERIFIES links are absent.
- Graph errors propagate; link accuracy itself is not reported, so the gain cannot be split between "correct links" and "having a checklist".
- Ablation is one dataset and one model.
- No page content addressed instructions to an AI agent.

## Takeaways for tuning a memory stack
- Evidence that a completeness walk over trace links helps an agent finish the right work (success 28.37% to 47.19% when the Validator is present), at build time, on software tasks. This is a targeted graph result in the same family as B8's "typed questions (supersession, completeness) favour typed structure".
- Measure link accuracy separately from end-task success; TraceDev does not, and we should.
- Model test nodes; TraceDev's authors list their absence as a limitation.

## Open questions
- How accurate were the LLM-decided requirement to design links, and how much of the Validator's gain survives with noisier links?
- Does the completeness walk help when requirements are free text rather than structured use cases?
