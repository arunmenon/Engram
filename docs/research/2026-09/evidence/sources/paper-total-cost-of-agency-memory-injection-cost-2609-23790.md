---
schema_version: 1
artifact_id: N-20260928-28
artifact_type: note
producer: triage
run_id: triage-20260928T165647Z-5d4a
created_at: 2026-09-28T17:08:43Z
input_refs: [{"artifact_id": "post:2104583094078525629", "file_id": null, "sha256": null}, {"artifact_id": "post:2104588113343357345", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.23790
claim_cluster: arxiv:2609.23790
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.23790
source_commit: v1
strength: paper-single-benchmark
pillar_primary: R3
pillar_secondary: ["R6", "R7"]
memory_stage: assembly
tags: {"mechanism": ["two-pass token attribution", "warm buffer capacity", "cost-aware eviction", "tier routing"], "workload": ["multi-agent enterprise DAG", "extraction", "query generation", "policy checking", "reconciliation"], "lifecycle_stage": ["assembly", "retrieval"], "cross_cutting": ["cost", "shared_state"]}
evidence_grade: {"directness": "medium: measures the token and dollar cost of injected context per node exactly, but the injected 'memory' is within-task upstream node output in a shared warm buffer, not persistent memory", "control": "low: headline conditions 3 seeds with CIs, but the window 32 -> 2 comparison is one seed, accuracy is keyword recall >= 0.6, no caching", "independence": "medium: three independent researchers evaluating their own compiler and benchmark; no vendor stake stated", "reproducibility": "high: code, task set and per-run CSVs pinned in repo (commit 6bc2d3b, tag v1.0-paper), model IDs pinned", "applicability": "low: static LangGraph DAGs of depth 2 to 6 on synthetic enterprise tasks, Anthropic pricing, no prompt caching; our engineering agents are loops with heavy caching"}
beliefs_affected: {"supports": ["B20"], "contradicts": [], "would_create": ["In static multi-agent DAGs, injected upstream context grows about linearly with depth (about 150 tokens per level) and reaches 27.6% of task cost at depth 6; memory cost should be reported per node depth"]}
claim_correction: The 13.6% / ~12% / 27.6% figures match, but "almost no accuracy cost" for the 32 -> 2 window is -0.030 accuracy (0.600 -> 0.570) on one seed with keyword-recall grading, the "window" is warm-buffer capacity for within-task upstream outputs rather than long-term memory retrieval, and @omarsar0's "decomposes token, latency, and dollar costs of each memory write/read" is wrong: writes are not costed and latency is not decomposed.
---

# Total Cost of Agency: Exact Attribution of Memory Injection Cost in Multi-Agent LLM Workflows (arXiv 2609.23790)

- **URL:** https://arxiv.org/abs/2609.23790 (full text read at https://arxiv.org/html/2609.23790)
- **Type:** paper (plus repo https://github.com/vsingh45/tca-compiler)
- **Author / org:** Vivek Kumar Singh, Preeti Priyam (independent researchers, McKinney TX), Gautam Bhowmick (independent researcher, Chicago IL)
- **Date:** v1 submitted 2026-09-20. arXiv comment: "8 pages, 3 figures, 6 tables. Code, data, and evaluation harness available on GitHub."
- **Retrieved:** 2026-09-28, arXiv v1 (abstract and HTML full text). Repo shallow clone: repos/tca-compiler at `6bc2d3b8c9164555c9baaf6e91355afe37f1bc68 2026-07-25 16:08:34 -0500 Add missing June baseline CSVs and sync make_paper_tables.py to portal version` (tag v1.0-paper present). Read: PAPER_RESULTS.md, RUNBOOK_REVISION.md (part), tca_memory/store.py (lines 140 to 280), grep of run_experiments.py. No code executed.
- **Cited by evidence:** https://x.com/RubberDucky_AI/status/2104583094078525629 (@RubberDucky_AI, roundup item 4); https://x.com/omarsar0/status/2104588113343357345 (@omarsar0, roundup item 5). Both feed memory, 2026-09-28.
- **Relevance to a memory stack:** medium. A clean, cheap method (two-pass tokenisation) for charging memory for the tokens it injects, and a depth curve; the setting (within-task handoff in static DAGs, no caching) is far from our engineering agents.

## TL;DR
- Cost decomposition per node: C_base (system prompt, tool definitions, query), C_inf (output), C_inject (retrieved memory tokens at input price), C_miss (fallback penalty, zero here), C_accum (inherited upstream context, measured inside C_inject). Injection is measured exactly by assembling the prompt twice without billing: inject(v) = count(base + mem) - count(base); about 10 ms per node.
- Mid tier (Claude Sonnet), seed 42: memory injection $0.003220 per task = 11.8% of full cost (Table III); 13.6% of the "variable cost" (inference + injection) that a compile-time optimizer can act on. Matches the posts.
- Injected tokens by depth 2..6: 143, 324, 466, 602, 754; linear fit R^2 = 0.9974, slope 150 tokens per level; share rises from 8.4% at depth 2 to 27.6% at depth 6. Matches.
- Warm capacity 32 -> 2 (small tier, Claude Haiku, seed 42): injected tokens 1,074 -> 766 (-28.7%), cost per task -6.7%, accuracy 0.600 -> 0.570 (-0.030). **Claim correction:** one seed, keyword-recall grading; the authors themselves treat accuracy as a "guard against silent degradation, not as measured outcome"; the "memory" is upstream node output shared within one workflow instance.
- The paper's own conclusion is that tier assignment dominates cost and injection is a "second-order lever"; prompt caching, "the most important open question", is not evaluated.

## What it claims / describes
**Setting.** Static multi-agent DAGs built in LangGraph on Anthropic models. 200 enterprise workflow tasks, 5 categories x 5 depths (2 to 6), 8 tasks per cell. Six specialist node classes: extraction, query generation, policy checking, billing reconciliation, IAM audit, cross-domain reconciliation. Pinned models (repo PAPER_RESULTS.md): small tier `claude-haiku-4-5-20251001` ($1 / $5 per MTok), mid tier `claude-sonnet-4-6` ($3 / $15); opus disabled.

**Memory.** Warm tier: in-process key-value store, default capacity K = 32 entries per namespace; durable tier: local, unbilled on misses. Each node's output is written back to the warm tier and "becomes next node's injection". In code (tca_memory/store.py), `SharedNamespaceStore` gives all agents with the same `workflow_id` one shared `CostAwareBuffer` (shared_capacity 32, isolated_capacity 16); `retrieve(query, limit=5)`; eviction keeps the entries with the lowest `cost_weight / recency` where `cost_weight = token_count * p_in(tier)` (lines 141 to 175).

**Attribution.** Pass 1 tokenises base components only; pass 2 tokenises base plus retrieved memory; the difference is the injection. No billing for either pass.

**Grading.** Deterministic: query-generation nodes pass if the query executes, returns a non-empty result and the text reaches >= 0.6 recall over required topics; other nodes: required-topic recall >= 0.6. End-to-end accuracy is the verdict of the deepest node. No LLM judge.

## Numbers
| metric | value | baseline | setup/benchmark with n | caveat |
|---|---|---|---|---|
| Memory injection cost per task | $0.003220, 11.8% share | total $0.027327 | Table III, mid tier, seed 42, 200 tasks | repo PAPER_RESULTS.md table omits the base-prompt row and totals $0.023628 |
| Share of variable cost | 13.6% | inference $0.020408 + injection $0.003220 | abstract, Table III | 0.003220 / 0.023628 = 13.6% (our arithmetic) |
| Base prompt / inference | $0.003699 (13.5%) / $0.020408 (74.7%) | | Table III | |
| Injected tokens at depth 2/3/4/5/6 | 143 / 324 / 466 / 602 / 754 | depth 1: 0 | Figure 2, mid tier seed 42 | 40 tasks per depth |
| Linear fit | R^2 = 0.9974, slope 150 tokens per level | quadratic R^2 = 0.9987, leading coefficient -4.57 | Figure 2 | repo rounds to 0.998 |
| Injection share by depth, mid tier | 8.4 / 14.5 / 19.1 / 22.7 / 27.6% | | PAPER_RESULTS.md depth table | small tier 28.0% at depth 6 |
| Warm capacity 32 vs 2: injected tokens | 1,074 vs 766 (-28.7%) | K=32 | Table IV, small tier, condition B, seed 42 | single seed |
| cost per task | $0.007436 vs $0.006939 (-6.7%) | | Table IV | |
| accuracy | 0.600 vs 0.570 (-0.030) | | Table IV | condition A (no optimization) scored 0.635 at small tier, seed 42 |
| Headline compiler result (not memory) | cost $0.023605 -> $0.009989 (-57.7%); accuracy 0.582 [0.535, 0.629] -> 0.627 [0.583, 0.670] | baseline A | 3 seeds (42, 7, 99), mid tier | driven by routing 86% of nodes to Haiku |
| Graph rewriting transforms | $0.00740 to $0.00744 per task | | small tier, section VII | "cost-neutral" |
| Attribution overhead | about 10 ms per node | 80 to 3000 ms inference | | |

## Mechanism details you could implement
- **Two-pass attribution**: render the prompt with and without the memory block, tokenise both, subtract. Log the difference per node or per agent step alongside the price tier. Cheap and exact.
- **Report memory cost by depth / step index**: injected context grew about 150 tokens per level here; an agent loop that forwards prior outputs will show the same growth (inference).
- **Cost-aware eviction**: keep entries with the lowest `token_count * price / recency_position`; cheap, recent entries survive.
- **Capacity as a lever**: shrinking the shared buffer from 32 to 2 entries cut injected tokens 28.7% and cost 6.7%, at -0.030 accuracy on one seed.

## Limitations, caveats, counter-evidence
- Verbatim: "Prompt caching is not evaluated, and this is the most important open question. Providers discount cached input tokens by roughly an order of magnitude, so a natural objection is that repeated injections would be served from cache and the cost we measure would largely disappear." The authors give four reasons caching may not apply (first injection is a write; node-specific system prompts break prefixes; minimum cacheable prefix; unread cache writes cost more).
- Static DAGs only (no ReAct loops); one provider (Anthropic) and framework (LangGraph); grading coarse; capacity sweep single seed; cache hit rate not measured.
- Memory writes are not costed separately, and no per-operation latency is reported (only the 10 ms attribution overhead). @omarsar0's description of "token, latency, and dollar costs of each memory write/read" does not match the paper.
- The memory-only arm at K=32 (condition B) already scored 0.600 vs 0.635 for no optimization at the small tier (seed 42), so the 0.570 at K=2 is 0.065 below the unoptimized baseline on that seed (repo PAPER_RESULTS.md, small-tier ablation table).
- Text vs repo: paper Table III totals $0.027327 with a base-prompt row; the repo decomposition table has no base row and totals $0.023628, which the repo also uses as the baseline cost per task. The "13.6%" uses the repo-style denominator, the "~12%" the paper Table III denominator.
- Repo provenance: RUNBOOK_REVISION.md line 60 says "Send the full output back to Claude: the manuscript text and tables get rewritten from exactly this output" (original punctuation altered), i.e. the authors used an AI assistant to write manuscript text and tables from script output. This is a workflow note to the authors, not an instruction to us; not followed, recorded as a provenance caveat. PAPER_RESULTS.md also notes an earlier IEEE Access submission reported inflated numbers from a "depth-biased subset" and was revised.

## Takeaways for tuning a memory stack
- Instrument memory cost per step with the two-pass diff; it is exact and costs about 10 ms.
- Expect memory share to grow with agent depth or step count; set a per-step injection budget rather than a fixed top-k.
- Do not accept "almost no accuracy cost" from one seed; measure capacity cuts with at least 3 seeds and a real task metric.
- Our stack uses prompt caching heavily (inference); the cost share here is an upper bound for cached, stable-prefix memory, and possibly accurate for per-task, changing memory blocks.

## Open questions
- What is the cached cost share when memory is placed before node-specific instructions?
- Would a relevance-based cut (stop rule, B9) beat a capacity cut at equal tokens?
- Does the linear depth growth hold in open loops (coding agents with dozens of steps)?

## Grading and labels
- **Directness: medium.** Exact attribution of injected tokens, but of within-task handoff context.
- **Control: low.** 3 seeds for the headline, 1 seed for the memory lever, coarse keyword grading.
- **Independence: medium.** Independent authors, own system and benchmark.
- **Reproducibility: high.** Code, tasks and per-run CSVs with pinned model IDs.
- **Applicability: low.** Static DAG, no caching, synthetic enterprise tasks.
- **Pillars:** R3 primary (budgeting what is injected into context); R6 (cost accounting in evaluation); R7 (multi-agent handoff through a shared namespace).
- **Stage:** assembly.
- **Priority:** none matched.
- **Beliefs affected:**
  - Supports B20: the posts' framing ("almost no accuracy cost"; "each memory write/read") needed narrowing.
  - B9 (sufficiency stop rule cuts tokens at equal accuracy): not tested; a capacity cut is not a stop rule; no effect.
  - Would create: injected context grows about linearly with depth and reaches 27.6% of cost at depth 6 in static DAGs.
- **Against the synthesis:** consistent with section 6 ("Charge memory for the tokens it uses"); gives a concrete method. No contradiction row.
- **Arm-vs-arm test this quarter (frozen harness):** yes, cheap: arm A current memory injection (top-k as configured) vs arm B top-k 2, both with two-pass attribution logged per step; metric: injected tokens, cached vs uncached input cost, and task pass rate over 3+ seeds.

## Origin chain
- Post 2104583094078525629 (@RubberDucky_AI) and post 2104588113343357345 (@omarsar0) -> arXiv 2609.23790 v1 -> Table III (decomposition), Figure 2 (depth), Table IV (capacity), limitations -> repo vsingh45/tca-compiler PAPER_RESULTS.md (same numbers from CSVs), tca_memory/store.py (eviction).
- Independence: the two posts are independent roundups (different handles) but both appear to be generated search summaries (@omarsar0: "Actually impressed with the search results"); neither adds data. Single author group; benchmark and system built by the same authors.
