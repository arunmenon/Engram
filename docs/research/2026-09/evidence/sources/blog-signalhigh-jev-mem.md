# Jev-Mem: System-One-Controlled Agentic Memory (SignalHigh summary)

- **URL:** https://signalhigh.centritude.com/post/jev-mem-system-one-controlled-agentic-memory-for-efficient-a-47
- **Type:** vendor blog (paper-summary aggregator post)
- **Author / org:** SignalHigh; individual author not stated
- **Date:** Sep 23, 2026
- **Retrieved:** 2026-09-26 (fetched live with WebFetch; no local copy)
- **Cited by evidence:** Decision models as the memory control plane / 2026-09-23 LFrefman; 2026-09-24 runbywren (the blog is a secondary summary of the same paper, arXiv 2609.23986)
- **Relevance to a memory stack:** low. It is a short restatement of the abstract with no mechanism detail; use the paper note (sources/paper-jev-mem-2609.23986.md) instead.

## TL;DR

- Restates the abstract of Jev-Mem: a lightweight System-One controller handles memory organization and retrieval; a System-Two LLM handles complex reasoning and answer synthesis.
- Repeats the headline numbers: 0.777 LLM-as-a-Judge on LoCoMo, +11.0% over the strongest baseline, 6.6x build speedup (158 s), 36.7% lower query latency (0.93 s).
- Links the paper (Hugging Face papers page 2609.23986) and the code repo (github.com/libingzheren/Jev-Mem).
- Adds nothing quantitative or mechanistic beyond the abstract.

## What it claims / describes

- Sections: Overview, Core Innovation, Performance Metrics, Significance, Resources.
- Core claim: conventional agent memory relies on expensive LLM generation for memory management; Jev-Mem uses a lightweight controller for (1) memory typing and relational organization during construction, (2) query routing and retrieval-budget allocation during retrieval, (3) graph traversal, candidate scoring, and adaptive stopping. "Only complex reasoning triggers System-Two invocation."
- Significance paragraph: for developers building long-horizon agents, Jev-Mem "offers improved recall quality alongside substantially reduced computational overhead and response times."

## Numbers

| Metric | Value | Baseline | Setup/benchmark | Caveat |
|---|---|---|---|---|
| LLM-as-a-Judge overall | 0.777 | strongest baseline (not named) | LoCoMo | Matches paper (baseline is MAGMA, 0.700) |
| Relative improvement | 11.0% | strongest baseline | LoCoMo | Matches paper |
| Memory construction | 158 s, 6.6x speedup | fastest competitor (not named) | LoCoMo | Matches paper (competitor is Nemori, 1044 s) |
| Query latency | 0.93 s, -36.7% | not named | LoCoMo | Matches paper (baseline is MAGMA, 1.47 s) |

## Mechanism details you could implement

- None beyond the list of controlled decisions above. No thresholds, prompts, schemas, budgets, or memory types are given. See the paper note for all of these.

## Limitations, caveats, counter-evidence

- Where it agrees with the paper: all four numbers and the list of System-One responsibilities match the abstract exactly.
- Where it adds or diverges:
  - It says "improved recall quality"; the paper reports an LLM-as-a-Judge answer-correctness score, not a recall metric (inference: loose wording, not a separate claim).
  - It omits that the model is gpt-4o-mini, that only one benchmark (LoCoMo) is reported, that there are no ablations or cost/token figures, that the baselines are A-MEM, MemoryOS, Nemori and MAGMA, and that Jev-Mem is not best on the Temporal category (0.637 vs 0.650 for MAGMA).
  - It does not mention that Jev is a proprietary TypeSafe AI decision model, or that the paper's text and table disagree on several per-category numbers.
- No critique or independent evaluation is offered.

## Takeaways for tuning a memory stack

- Treat as a pointer only; the implementable content (thresholds, prompts, budget math) is in the paper's Section 3 and Appendix B.
- The headline numbers are faithfully copied, so this blog is not independent confirmation of them.

## Open questions

- None raised by the blog itself. The open questions (ablations, LongMemEval, cost per query, threshold transfer) are listed in the paper note.

---
