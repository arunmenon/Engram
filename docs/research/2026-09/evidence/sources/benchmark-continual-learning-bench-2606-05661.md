---
artifact_id: N-SURVEY-20260927-06
artifact_type: note
producer: triage
run_id: survey-20260927T044739Z-8de9
created_at: 2026-09-27T04:53:14Z
idempotency_key: note:survey:arxiv:2606.05661
input_refs: []
pillar_primary: R5
pillar_secondary: [R3, R6]
beliefs_affected:
  supports: [B16]
  contradicts: []
  note: raw in-context history beats Mem0 extraction and ACE playbooks at matched model; memory modules "introduce spurious generalizations and stale beliefs"
evidence:
  directness: 4
  control: 4
  independence: 4
  reproducibility: 3
  applicability: 3
  scale: 1-5, 5 best
source_url: https://arxiv.org/abs/2606.05661
found_via: survey
---

# Continual Learning Bench: Evaluating Frontier AI Systems in Real-World Stateful Environments (CL-Bench)

- **URL:** https://arxiv.org/abs/2606.05661 (HTML v1 read); site https://www.continual-learning-bench.com ; leaderboard https://snorkel.ai/leaderboard/continual-learning-bench/
- **Type:** benchmark paper
- **Author / org:** Parth Asawa et al. (UC Berkeley Sky/SkyRL lab, Snorkel AI, UW-Madison)
- **Date:** 4 Jun 2026
- **Retrieved:** 2026-09-27
- **Cited by evidence:** digest D7 flagged CL-Bench as [fetch]; top-down survey R5 question on B16
- **Relevance to a memory stack:** high. The first expert-validated benchmark that scores a stateful system against the same system run stateless, with a software-engineering sequence, and it compares raw history with memory products.

## TL;DR
- Gain is measured per system against its own stateless run: g_t = r^sf_t - r^sl_t; normalised gain = (mean r^sf - mean r^sl) / (r_max - mean r^sl).
- Best normalised gain 25.4 +/- 3.6 % from naive ICL (full history in context) with Claude Sonnet 4.6.
- With GPT-5.4 held fixed: ICL 20.1 %, Mem0 20.2 %, ICL Notepad 7.8 %, ACE (playbook) 8.6 % gain; ACE cost $62.8 vs $18.4 for ICL.
- Authors: "memory modules introduce spurious generalizations and stale beliefs".
- Rewards are programmatic (IoU, step efficiency, profit, MAPE); no LLM judge.

## What it claims / describes
Six task sequences (software engineering "Codebase Adaptation", signal processing, epidemiological forecasting, database querying, poker, sales forecasting), 20 to 120 instances each, built around a latent structure a stateful system can learn online. 5 rollouts per task in possibly different orders; 95 % CIs from rollout variance. Systems: ICL (full history), ICL Notepad (agent keeps notes), Mem0 (k = 10), ACE (playbook updated after each instance), Claude Code and Codex (auto-compaction).

## Numbers

Table 1, "ICL is a strong baseline continual learning system" (verbatim):

| Rank | System | Model | Norm. reward (%) | Norm. gain (%) | Cost ($) |
|---|---|---|---|---|---|
| 1 | ICL | Claude Sonnet 4.6 | 22.3 +/- 4.1 | 25.4 +/- 3.6 | 30.4 |
| 2 | ICL | GPT-5.4 | 20.1 +/- 9.1 | 20.1 +/- 9.1 | 18.4 |
| 3 | Claude Code | Sonnet 4.6 | 19.0 +/- 7.1 | 23.9 +/- 5.7 | 38.6 |
| 4 | Mem0 | GPT-5.4 | 15.1 +/- 6.4 | 20.2 +/- 5.9 | 18.3 |
| 5 | ICL | Claude Opus 4.7 | 10.2 +/- 4.4 | 19.5 +/- 4.1 | 49.6 |
| 6 | ICL Notepad | GPT-5.4 | 8.0 +/- 3.3 | 7.8 +/- 3.0 | 14.3 |
| 7 | ICL | Gemini 3 Flash | 8.0 +/- 4.7 | 16.4 +/- 3.8 | 7.6 |
| 8 | Codex | GPT-5.4 | 6.6 | 14.6 | 27.2 |
| 9 | ACE | GPT-5.4 | 4.6 +/- 2.7 | 8.6 +/- 2.5 | 62.8 |
| 10 | ICL Notepad | Claude Sonnet 4.6 | 3.5 +/- 5.7 | 18.2 +/- 3.4 | 31.5 |
| 11 | ICL Notepad | Gemini 3.1 Pro | -0.2 +/- 3.4 | 9.4 +/- 3.0 | 13.3 |
| 12 | ICL | Gemini 3.1 Pro | -5.6 +/- 4.1 | 6.2 +/- 3.8 | 15.2 |

Caption (verbatim): "Normalized reward is averaged across the six benchmark tasks after subtracting the stateless GPT-5.4 baseline and scaling by the task-specific maximum reward." So "reward" is against a fixed GPT-5.4 stateless run and "gain" is against the same model's stateless run.

Codebase Adaptation: sequential bug-fix issues from jazzband/tablib (9 issues) and jd/tenacity (10 issues); reward = 1 - (steps_to_solve - 1)/max_steps if solved; r_max = 1.0. No separate per-domain table in the text read.

## Mechanism details you could implement
- The stateful-minus-own-stateless gain is the right metric for "did memory help" because it removes base-capability confounds. Engram's H1/H3 could report it directly.
- Codebase Adaptation is a ready, small, executable SE sequence usable as a second harness next to DreamBench-SWE.

## Limitations, caveats, counter-evidence
- Sequences of tens of instances; short relative to deployment horizons (authors).
- Context-based memory only; no parametric learning.
- Mem0 matches ICL on gain with GPT-5.4 (20.2 vs 20.1), so "raw beats extracted" holds for ACE and Notepad, not clearly for Mem0.
- Per-domain breakdown not seen; the SE task could behave differently from the average.
- Code release not confirmed in the text read.

## Takeaways for tuning a memory stack
- Supports B16 with frontier models and programmatic scoring: distilled playbooks (ACE) and self-kept notes gain less than raw history at similar or higher cost.
- The comparison Engram lacks is "raw history in context" as an arm; H3's arms are all derived (summary, Workflow text, curated briefing). Where history fits in the window, raw history is the baseline to beat.

## Open questions
- What happens once history exceeds the context window (the regime Engram exists for)? CL-Bench sequences are short enough that ICL fits.
