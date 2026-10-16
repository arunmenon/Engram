---
schema_version: 1
artifact_id: N-SURVEY-20261011-05
artifact_type: note
producer: triage
run_id: survey-20261011T054529Z-bcaa
created_at: 2026-10-11T07:00:00Z
idempotency_key: note:survey:arxiv:2609.14913
input_refs: []
pillar_primary: R10
pillar_secondary: [R3]
memory_stage: linking
priority: 3
beliefs_affected: {supports: [B8], contradicts: []}
evidence: {directness: 2, control: 2, independence: 4, reproducibility: 2, applicability: 4}
strength: paper-single-benchmark
source_url: https://arxiv.org/abs/2609.14913
found_via: survey
answers_watch_request: null
---

# Externalizing Requirement-to-Repair Artifacts as Observable Traces for LLM-Based Program Repair (THEMIS, arXiv 2609.14913)

- **URL:** https://arxiv.org/abs/2609.14913 (HTML v1 read)
- **Type:** paper
- **Author / org:** Zewen Tao, Shin-nosuke Ishikawa (Rikkyo University)
- **Date:** 2026-09-14
- **Retrieved:** 2026-10-11
- **Relevance to a memory stack:** medium. An engineering agent that writes an explicit requirement-to-code graph before repairing, with a paired comparison on SWE-bench Lite; the graph's own contribution is not isolated.

## TL;DR
- Issue text is decomposed into RequirementNodes, mapped to code nodes (functions, classes, variables), and requirement-code pairs that mismatch become `VIOLATES` edges (high-signal, blocking) or `ADVISORY` edges (lower confidence).
- Paired 100 cases: THEMIS 19/100 resolved vs direct same-input 9/100; 10 THEMIS-only, 0 direct-only; risk difference +0.10, 95% CI [0.0412, 0.1588], exact McNemar p = 0.002.
- Full 300: 58/300 resolved (19.3%). Link accuracy not reported.
- Authors: the comparison "does not isolate the graph's causal contribution"; decomposition, mapping and flagging "are heuristic".

## Numbers

| Metric | Value | Baseline | Caveat |
|---|---|---|---|
| Resolved, paired 100 | 19/100 | direct 9/100 | differs in analyzer output, distillation, judge records, token budget, interface |
| Non-empty patches, paired 100 | 89/100 | 43/100 | baseline often produced no patch, which may explain most of the gap (inference) |
| Resolved, full 300 | 58/300 (19.3%) | none | gpt-5.1-codex-mini, one configuration |
| Resolved with complete audited field set vs incomplete | 22.0% (47/214) vs 12.8% (11/86) | | descriptive, not causal |
| Rationale names target vs not | 27.6% (37/134) vs 12.5% (10/80) | | target symbol written by the Judge after the edit |

Cost not reported. Judge and Developer share gpt-5.1-codex-mini.

## Limitations, caveats, counter-evidence
- Confounded arms; most of the difference is the baseline failing to emit patches (43/100), so this is weak evidence for the graph itself (inference).
- Python only, SWE-bench Lite, one model, one seed.

## Takeaways for tuning a memory stack
- The VIOLATES / ADVISORY split is a cheap two-level confidence on a trace link that an agent can act on (block vs warn); matches our "check before an agent acts".
- Does not change B8: still no matched-budget evidence that a graph beats flat retrieval for engineering agents.

## Open questions
- Graph-only ablation with everything else fixed; accuracy of the requirement-to-code links themselves.
