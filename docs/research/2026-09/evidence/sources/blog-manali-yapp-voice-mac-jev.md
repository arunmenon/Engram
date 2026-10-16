---
schema_version: 1
artifact_id: N-20260930-24
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105140160924901532", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:url:manali.page/blog/use-your-mac-without-the-keyboard
claim_cluster: url:manali.page/blog/use-your-mac-without-the-keyboard
feeds: ["decision"]
primary_source: https://manali.page/blog/use-your-mac-without-the-keyboard/
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4", "R8"]
memory_stage: routing
priority: 1
tags: {"mechanism": ["choice over options built from the screen", "completeness score with a threshold", "whole-instruction harm check before the first step", "option set as the failure point"], "workload": ["voice control of a desktop", "32 real tasks"], "lifecycle_stage": ["routing", "safety"], "cross_cutting": []}
evidence_grade: {"directness": "medium", "control": "low", "independence": "low", "reproducibility": "low", "applicability": "low"}
beliefs_affected: {"supports": ["B12"], "contradicts": [], "would_create": ["When a System One model can only pick from a prepared list, most failures come from the right option being absent from the list, not from a wrong pick"]}
claim_correction: none
---

# Yapp: a Mac driven by voice, with Jev (TypeSafe) picking every action from what is on screen (manali.page)

- **URL:** https://manali.page/blog/use-your-mac-without-the-keyboard/
- **Type:** builder writeup
- **Author / org:** Ayush Manish Agrawal (with Claude as the coding agent); X handle @ayushmanish_agr
- **Date:** 2026-09-29
- **Retrieved:** 2026-09-30, read through a summarising fetch (two passes). The page gives no repository for Yapp; content is marked CC BY 4.0.
- **Cited by evidence:** https://x.com/ayushmanish_agr/status/2105140160924901532 (@ayushmanish_agr, author).
- **Relevance to a memory stack:** low. It is kept as a priority 1 usage note because it reports a small task count with failures explained, and two findings carry over to any selection stage: the option list is where a pick-only model fails, and a guard on the whole instruction before the first step outperforms per-step checks.

## TL;DR
- Pipeline: Whisper on the Mac emits new words every 0.4 seconds; each batch goes to Jev with a few typed questions; the available actions are built from the accessibility tree of what is on screen; Jev "can't write a single word", it only ranks prepared options.
- Results on 32 real tasks: 15 of 16 everyday errands pass; 8 of 9 destructive requests are correctly stopped for confirmation (1 of 9 before a design change); 3 of 7 multi-step navigation tasks pass.
- The destructive-request fix: "Jev also judges the whole instruction against the current screen before the first step."
- Failures are mostly missing options: Jev "could pick the address bar but couldn't write 'weather.com'."
- Latency: Jev returns in "150 to 300 milliseconds". Cost is not stated.

## What it claims / describes

**Questions asked per batch (as listed by the article; exact wording not reproduced):** what the utterance requests; whether the first instruction is complete; whether it was said to the computer; whether it ends text being typed; and a harm judgment on the whole instruction.

**Thresholds.** Completeness bar 0.70, with the example "save" scoring 0.94 and "save it" scoring 0.67. Harm judgment default 0.30, and 0.85 in an auto mode (as reported by the fetch; the direction of each threshold was not re-checked).

**Open question raised by the author.** Whether Jev is an embedding-style model like CLM-8B or a likelihood scorer. The article leans toward an embedding model ("an action vector doesn't depend on the state, so a menu can be embedded once and reused") and labels this "our guess, not TypeSafe's word".

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Everyday errands | 15 of 16 pass | | 32 real-Mac tasks, author-run | single run |
| Destructive requests handled correctly (asked before acting) | 8 of 9 | 1 of 9 before the whole-instruction check | same | 9 cases |
| Multi-step navigation | 3 of 7 pass | | same | failures from missing options and flaky search |
| Completeness score examples | "save" 0.94; "save it" 0.67; bar 0.70 | | | a more complete phrase scored lower |
| Jev latency | 150 to 300 ms | | | |
| Cost | not stated | | | |

## Mechanism details you could implement
- Build the option list from ground truth (here, the accessibility tree) and let the model only choose; keep generation out of the action path.
- Run one check on the whole instruction against the current state before any step, in addition to per-step choices. This moved the safety result from 1 of 9 to 8 of 9.
- Log "no suitable option" separately from "wrong option chosen"; they need different fixes.

## Limitations, caveats, counter-evidence
- 32 tasks, written and run by the author, one run, no comparison model.
- The completeness example shows the score is not monotone in how complete the phrase sounds ("save it" below "save"); a fixed bar of 0.70 misfires on it.
- No repository; not reproducible.
- Desktop control is far from memory work.

## Takeaways for tuning a memory stack
- For reranking or linking with a pick-only model, measure candidate-set recall first: if the right item is not among the options, the decision model cannot recover it (the same point as B11 on losing gold evidence by pruning).
- A pre-action check on the whole request is a cheap addition to per-step gating.

## Open questions
- How does a none-of-these option behave in the action choice? Not stated.
- What does each batch cost? Not stated.

## Grading and labels
- **Directness: medium.** First-hand task counts; no logs.
- **Control: low.** Before and after on one change only.
- **Independence: low.** Single author.
- **Reproducibility: low.** No code.
- **Applicability: low.** Desktop control.
- **Strength:** builder-report.
- **Pillars:** R9 primary (a System One model as the only decision maker in a loop). Secondary R4 (thresholds and confirmation), R8 (destructive-action guard). Memory stage: routing (choosing the next action from a closed set). Priority 1. Written as a priority usage note.
- **Beliefs:**
  - B12 supports weakly: a typed decision model alone handles single-step tasks (15 of 16) and degrades on multi-step ones (3 of 7) without a planner.
  - Would create: option-set coverage, not the pick, is the dominant failure.
- **Contradiction rows:** none.

## Origin chain
- Post https://x.com/ayushmanish_agr/status/2105140160924901532 -> https://manali.page/blog/use-your-mac-without-the-keyboard/ -> task results and thresholds -> this note.
- Independence: single source.
