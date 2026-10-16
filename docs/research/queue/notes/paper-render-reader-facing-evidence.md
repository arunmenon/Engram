---
schema_version: 1
artifact_id: N-SURVEY-20261007-02
artifact_type: note
producer: triage
run_id: survey-20261007T054506Z-c08e
created_at: 2026-10-07T06:08:00Z
idempotency_key: note:survey:arxiv:2608.23568
input_refs: []
pillar_primary: R6
pillar_secondary: [R3]
memory_stage: assembly
priority: 4
beliefs_affected:
  supports: []
  contradicts: []
evidence: {directness: 4, control: 4, independence: 4, reproducibility: 4, applicability: 3}
source_url: https://arxiv.org/abs/2608.23568
found_via: survey
---

# RENDER: Controlling Reader-Facing Evidence in LLM Memory Evaluation (arXiv 2608.23568)

- **URL:** https://arxiv.org/abs/2608.23568 (HTML v1 read)
- **Type:** paper
- **Author / org:** not stated in extract
- **Date:** 2026-06 (v1)
- **Retrieved:** 2026-10-07 (local copy: out/log/raw/2608.23568v1.html)
- **Cited by evidence:** survey
- **Relevance to a memory stack:** high; the text format in which memory is handed to the reader moves accuracy by tens of points, so a memory benchmark that does not fix the rendering compares templates, not memories.

## TL;DR
- At matched budget, "resolved packets beat recency-truncated raw dialogue by 42.4 to 72.6 points" on all 9 reader models (substring scorer).
- Among deployed-style templates, "best to worst spread is 24.6 to 48.8 points" per model. "LangChain summaries score 4.4 to 10.6%; MemGPT-style typed records score 14.8 to 33.0%."
- "Three models scoring 0% on formal ledger packets answer the same facts from natural-language entries" (reader summary: at 45.4 to 53.4 %).
- Recommendation: memory and RAG evaluations should report or control the reader-facing artifact.

## What it claims / describes
Holds the underlying evidence fixed (LongMemEval oracle tier, 500; LoCoMo, 200; HotpotQA as transfer) and varies only how it is rendered: P0, P1, P2 packet levels, deployed-memory templates, truncated raw dialogue. About 238,000 model calls over 9 readers (gpt-5.4-mini, gpt-5.2, gpt-5.2-pro, claude-sonnet-4, claude-opus-4.1, claude-opus-4.6, gemini-3-flash, gemini-2.5-flash-lite, gemini-3.1-flash-lite).

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| P2 packet vs truncated raw, matched budget | +42.4 to +72.6 pts | truncated raw | 9 readers, substring scorer | oracle evidence, not retriever errors |
| same, judge rescored | +48.4 to +80.2 pts (paired bootstrap 95 % CI) | truncated raw | claude-haiku-4-5 judge, 31,500 items | per reader summary, not verified verbatim |
| template spread | 24.6 to 48.8 pts per model | n/a | deployed-style templates | deterministic templates only |
| P0 / P1 | 0.0 to 0.6 % | n/a | answer not yet in packet | |
| scorer agreement | substring vs judge 87 to 88 %; EM vs judge 89 to 90 % | n/a | | |
| judge family overlap | Anthropic judge, 3 of 9 readers Anthropic | n/a | | authors report no systematic advantage on HotpotQA |
| cost, latency | not stated | | | |

## Mechanism details you could implement
- Record the exact reader-facing artifact (the served briefing) for every eval item and freeze the renderer as part of the harness.
- Avoid formal ledger syntax as the only rendering; some readers refuse on it.

## Limitations, caveats, counter-evidence
Word-level truncation, not tokenizer-level. Oracle conflict sets, not real retrieval. Refusal on ledger packets unexplained. Model-specific significance "mixed".

## Takeaways for tuning a memory stack
- Our briefing renderer is a variable at least as large as the retrieval choices H2 to H3 test; fix it or test it explicitly.
- For the PDLC benchmark: publish the rendered packet alongside each score.

## Open questions
- Does the effect hold with real retrieval errors and with code-heavy evidence?
