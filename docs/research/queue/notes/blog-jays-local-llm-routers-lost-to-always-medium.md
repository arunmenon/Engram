---
schema_version: 1
artifact_id: N-20260927-06
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2102727172473360583", "file_id": null, "sha256": null}, {"artifact_id": "post:2102727269815107972", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:jays.fyi/blog/local-llm-routers-lost-to-always-answering-medium
claim_cluster: url:jays.fyi/blog/local-llm-routers-lost-to-always-answering-medium
feeds: ["decision"]
primary_source: https://jays.fyi/blog/local-llm-routers-lost-to-always-answering-medium
source_commit: n/a
strength: builder-report
pillar_primary: R4
pillar_secondary: ["R6", "R7"]
tags: {"mechanism": ["model routing", "difficulty tiering", "choice vs score question shape", "constant-class baseline", "probability-threshold escalation"], "workload": ["multilingual chat prompts", "WildChat-1M"], "lifecycle_stage": ["decision"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-model accuracy on the same 563 prompts with three question shapes", "control": "medium: constant 'medium' and prompt-length baselines included; gold labels are LLM-assigned and filtered to agreement cases", "independence": "medium: TextCortex engineer, not a vendor of any tested model (later released a competing fine-tune, see N-20260927-07)", "reproducibility": "low: WildChat source named, but benchmark code and label file not linked in the article read", "applicability": "medium: routing decision on single prompts; our routing is over agent steps with context"}
beliefs_affected: {"supports": ["B13"], "contradicts": [], "would_create": ["For 3-tier prompt routing, stock open System-One models (Laya, Von) scored near or below a constant 'medium' answer; any router evaluation needs a constant-class baseline"]}
claim_correction: "A hardcoded string beat the open models in 4 of 6 runs" matches the article; the post's "Jev: 84.5%" is on the agreement-filtered gold set, which the author says "flatters Jev"; Jev's score-shaped question reached only 70.5%
---

# Local LLM routers lost to always answering "medium" (jays.fyi, Jay Derinbogaz)

- **URL:** https://jays.fyi/blog/local-llm-routers-lost-to-always-answering-medium
- **Type:** builder writeup
- **Author / org:** Jay (Cem) Derinbogaz, TextCortex
- **Date:** 2026-09-23
- **Retrieved:** 2026-09-27 (web page)
- **Cited by evidence:** @cderinbogaz https://x.com/cderinbogaz/status/2102727172473360583 and https://x.com/cderinbogaz/status/2102727269815107972
- **Relevance to a memory stack:** medium. A clean example of why every decision-model evaluation needs a constant-class baseline, and of question shape (choice vs score) moving accuracy by 14 points on the same model.

## TL;DR
- 563 WildChat prompts in 14 languages, gold tier (small / medium / frontier) = the tier both Claude Opus and Claude Sonnet assigned; distribution 225 small, 317 medium, 21 frontier.
- Best accuracy: Jev 84.5% (rubric choice), Laya 61.6%, Von 58.8%, constant "medium" 56.3%, prompt-length rule 54.7%. "Four of the six Laya and Von runs lost to it [the constant router]."
- Question shape matters: Jev 84.5% (described choice), 84.2% (minimal choice), 70.5% (numeric difficulty score mapped to tiers).
- Frontier prompts (n=21): Jev choice routed only 6 to frontier; a probability threshold (> 0.2 on frontier) caught 14/21 with 18/563 escalations.
- Latency: Jev about 330 ms median (mostly network) vs 56 to 170 ms for local models.

## What it claims / describes
- Task: route each prompt to the cheapest tier that will still answer it well.
- Data: WildChat-1M (ODC-BY); 563 prompts kept where two annotators agreed; labels from Claude Opus and Claude Sonnet; inter-rater agreement 77.5% (kappa 0.60).
- Three question shapes per prompt (5,067 calls total): Q1 described rubric choice ("Pick the cheapest tier that will still answer it well" with examples), Q2 minimal labels ("Simple", "moderately complex", "very hard"), Q3 numeric difficulty score mapped to tiers.
- Failure modes: Von Q2 sent 550/563 prompts to "medium"; Von Q3 never answered "small" and sent 139 to frontier (actual 21); Laya Q1 sent 86 to frontier (about 6 correct). Von and Laya "overspend on 20 to 55% of prompts".
- Motivation: Jev has no EU deployment, so TextCortex cannot use it; the author later fine-tuned Laya (Raya, see N-20260927-07).

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| accuracy, Jev Q1 | 84.5% | constant "medium" 56.3%; length rule 54.7% | 563 prompts, 14 languages | gold = agreement subset; "84% flatters Jev" |
| accuracy, Jev Q2 / Q3 | 84.2% / 70.5% | | same | score shape loses 14 points |
| accuracy, Laya best | 61.6% (Q1) | 56.3% | same | |
| accuracy, Von best | 58.8% | 56.3% | same | |
| runs losing to constant | 4 of 6 open-model runs | | | |
| per-language Q1 | Jev 74 to 92%; Von 42 to 69%; Laya 29 to 67% | | about 40 prompts per language (inference from 563/14) | small per-language n |
| frontier catch with threshold | 14/21 caught, 18/563 escalated | Jev Q1 argmax: 6/21 | threshold > 0.2 | frontier n = 21 |
| latency | Jev ~330 ms median | Laya/Von 56 to 170 ms local | | network included for Jev |

## Mechanism details you could implement
- Always report a constant-majority-class router and a trivial heuristic (prompt length) next to any learned router.
- Prefer a described choice question over a numeric score mapped to buckets for this kind of decision (84.5% vs 70.5% on the same model here).
- For rare expensive classes, escalate on probability mass (frontier probability > 0.2) rather than argmax; here that multiplied frontier recall from 6/21 to 14/21 for 18 escalations.

## Limitations, caveats, counter-evidence
- Author: "84% flatters Jev. The gold set is the prompts both annotators agreed on, the easier ones."
- Labels are model-predicted (Claude Opus / Sonnet), not validated by running the tiers.
- Frontier sample n = 21.
- Jev version unspecified.
- No code or label file linked in the article read, so the benchmark cannot be rerun from the source.

## Takeaways for tuning a memory stack
- Any admission, recall-gate or rerank decision we automate should be benchmarked against "always the majority answer" first (R6 hygiene).
- Question shape is a first-class hyperparameter; test choice vs score on our own labels before fixing it.
- Threshold on the minority class's probability when misses are expensive; this matches B13's advice to evaluate the borderline population.

## Open questions
- Accuracy on the full 77.5%-agreement pool, including disagreement prompts?
- Does routing accuracy translate into answer quality and cost when tiers are actually run?

## Grading and labels
- Directness high; control medium; independence medium; reproducibility low; applicability medium.
- Pillars: R4 primary (automated decision, escalation threshold); R6 secondary (baseline design, label quality); R7 secondary (EU deployment constraint for a hosted decision API).
- B13 supports: escalation on a probability threshold over the borderline/rare population beat argmax.
- Would create: open System-One routers near a constant baseline; constant-class baseline mandatory.
- No contradiction rows.

## Origin chain
posts 2102727172473360583 and 2102727269815107972 (@cderinbogaz) -> jays.fyi blog (2026-09-23) -> results summary, per-run breakdown, frontier analysis, stated limitations -> this note. Independence: same author and same 563-prompt set as the Raya model card (N-20260927-07); gold labels from Anthropic models.
