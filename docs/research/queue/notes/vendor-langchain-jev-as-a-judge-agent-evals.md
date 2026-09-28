---
schema_version: 1
artifact_id: N-20260926-10
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2101470551340421321", "file_id": null, "sha256": null}, {"artifact_id": "post:2101472983587909999", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:langchain.com/blog/jev-agent-evals-langsmith
claim_cluster: url:langchain.com/blog/jev-agent-evals-langsmith
feeds: ["decision"]
primary_source: https://www.langchain.com/blog/jev-agent-evals-langsmith
source_commit: n/a
strength: vendor-benchmark
pillar_primary: R6
pillar_secondary: ["R4"]
tags: {"mechanism": ["decision model as eval judge", "repeatability (per-case variance)", "pass/fail noul"], "workload": ["agent output grading"], "lifecycle_stage": ["evaluation"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: accuracy and variance tables, but on five test cases", "control": "low: five weather requests repeated 100 times each; repeats are not independent cases; LLM judges at provider defaults", "independence": "low: LangChain sells the LangSmith integration and co-markets with TypeSafe", "reproducibility": "low: examples in LangSmith, no public dataset or code captured", "applicability": "medium: judge speed and repeatability matter for gating every change in our harness, but the task is trivial"}
beliefs_affected: {"supports": ["B21"], "contradicts": [], "would_create": []}
claim_correction: The posts call Jev "a cheaper and more precise alternative to LLM as a judge"; the experiment is five weather-agent requests, each judged 100 times (500 decisions), so "100% accuracy" is agreement on 5 distinct cases and "precision" means lower repeat variance, not accuracy on a population.
---

# Jev-as-a-Judge for Agent Evals (LangChain blog)

- **URL:** https://www.langchain.com/blog/jev-agent-evals-langsmith
- **Type:** vendor blog
- **Author / org:** Daniel Shea, Sean Roche (LangChain)
- **Date:** 2026-09-20
- **Retrieved:** 2026-09-26 (web; langchain-typesafe==0.0.1a2 named; no code repo captured)
- **Cited by evidence:** https://x.com/sydneyrunkle/status/2101470551340421321 (@sydneyrunkle, quoting @LangChain x:2101454284927959080), https://x.com/sydneyrunkle/status/2101472983587909999 (@sydneyrunkle)
- **Relevance to a memory stack:** medium. The synthesis already treats a fast decision-model judge as the way to gate every change (Sentry, `x-posts-jev-builders.md`). This is the second vendor-side experiment; it adds a repeatability measure but its sample is five cases.

## TL;DR
- Weather agent built with Deep Agents v0.7.15; **five requests** stored as LangSmith examples; each judge scored each run 100 times for a quality score and a binary does_pass; human labels against the same rubric are the oracle.
- Binary agreement with the oracle over "all 500 repeated decisions": Jev 100%, GPT-5.6 Terra 99.8%, GPT-5.6 Luna 96.4%, Claude Sonnet 4.6 80.0%.
- Per-case variance of the quality score: Jev 0.0000149; Luna 433x, Terra 913x, Claude 92x higher.
- Cost: Jev $0.00035 per call ($0.34 total), 0.44 s average; Claude $28.17 total.
- **Claim correction:** n = 5 distinct cases. With zero errors on 5 independent cases the exact one-sided 95% upper bound on the error rate is 1 - 0.05^(1/5), about 45% (the rule of three in B21 gives 60% but is meant for larger n); the 500 repeats do not add independence.

## What it claims / describes
- Jev asked typed questions: score (rubric 1 to 5) for quality and noul for pass/fail; no thresholds stated for converting the noul probability into pass/fail.
- LLM judges called through LangSmith Gateway with provider defaults ("no temperature, top-p, seed, or max tokens specified").
- A combined accuracy x repeatability "signal value" table (Table 5) is given.
- Authors' own caveats: "This experiment cannot tell us why Jev's scores varied less"; a "narrow test" to be validated on "other agents and production workflows"; "low cost can amplify mistakes"; teams should "incorporate human review and judge alignment".

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| pass/fail agreement with human oracle | Jev 100% | Terra 99.8%, Luna 96.4%, Claude Sonnet 4.6 80.0% | 5 cases x 100 repeats | 5 independent cases |
| mean per-case variance, quality score | 0.0000149 | Luna 433x, Terra 913x, Claude 92x | 5 cases | LLMs at default temperature |
| cost per call | $0.00035 | | | |
| total cost | $0.34 | Claude $28.17 | 500 calls | |
| latency | 0.44 s average | other models in a figure only | | |

## Mechanism details you could implement
- Measure a judge's **repeatability** (variance of repeated scores on the same case) separately from accuracy; a deterministic-ish judge is useful for regression gating even when accuracy is uncertain.
- Decompose "is it good" into several typed rubric questions (echoed by @egafni in the queue, x:2101836614016397602).

## Limitations, caveats, counter-evidence
- Five cases; LLM judges at default temperature inflate their variance relative to temperature 0 (inference).
- No false-positive / false-negative breakdown; no hard or borderline cases.
- Vendor co-marketing (LangChain x TypeSafe).

## Takeaways for tuning a memory stack
- Do not treat this as accuracy evidence for a Jev judge. Treat it as evidence that a decision-model judge is highly repeatable and cheap; accuracy must come from our own labelled set of at least 50 to 150 cases (B21 sizes).
- If comparing judges, fix LLM temperature at 0 to get a fair repeatability comparison.

## Open questions
- Jev judge accuracy on a population of hard or borderline agent outputs? Not measured here.

## Grading and labels
- Directness medium; control low; independence low; reproducibility low; applicability medium.
- Pillar R6 (judge design; whether the evaluation supports "more precise"). Secondary R4.
- Beliefs: supports B21 (zero errors in n cases bounds the rate at about 3/n; here n = 5). New relative to local sources: a second vendor judge experiment besides Sentry, with a repeatability metric.
- Contradiction rows: none.

## Origin chain
posts 2101470551340421321 and 2101472983587909999 (@sydneyrunkle) -> LangChain post x:2101454284927959080 (not fetchable) -> langchain.com/blog index -> "Jev-as-a-Judge for Agent Evals" (2026-09-20) -> accuracy text, Table 1 (variance), Table 4 (cost), Table 5 -> this note. Independence: vendor and integration partner; no shared data with Sentry's report.
