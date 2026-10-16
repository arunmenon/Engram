---
schema_version: 1
artifact_id: N-20260926-12
artifact_type: note
producer: triage
run_id: triage-20260926T105956Z-8af2
created_at: 2026-09-26T11:09:01Z
input_refs: [{"artifact_id": "post:2103499768031015283", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.15364
claim_cluster: arxiv:2609.15364
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.15364
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R5
pillar_secondary: ["R6"]
tags: {"mechanism": ["exploration before tasks", "curriculum / actor / verifier agents", "frozen environment memory", "broad-then-deep exploration"], "workload": ["computer use (OSWorld 2.0)", "Agents' Last Exam"], "lifecycle_stage": ["write", "read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: scores with and without the RSI stage, but partial scores dominate and n is small", "control": "low: baselines are frontier models, not other memory or self-improvement methods; ablation on 4 tasks; no leakage analysis", "independence": "medium: academic authors, no ties to our sources", "reproducibility": "low: no code link captured, exploration cost not quantified, single runs", "applicability": "medium: learning an unfamiliar environment before work resembles onboarding an agent to a new repository"}
beliefs_affected: {"supports": ["B17"], "contradicts": [], "would_create": []}
claim_correction: The abstract says RSIAgent lifts open models "to outperform frontier closed-source models including GPT-6"; on Agents' Last Exam binary accuracy GPT-6 Astra (52.24%) still beats RSIAgent full (50.75%), and most of the OSWorld gain over Kimi-K3 comes from the framework without the RSI stage (58.30 -> 71.97 partial), with RSI adding 7.01 points on OSWorld and 1.07 on ALE.
---

# RSIAgent: Autonomous Exploration for Recursive Self-improvement in New Environments (arXiv 2609.15364)

- **URL:** https://arxiv.org/abs/2609.15364 (HTML read)
- **Type:** paper (50 pages)
- **Author / org:** Sibo Zhu, Shicheng Fan, Xinyue Wang, Wenyi Wu, Kun Zhou, Biwei Huang (affiliations not captured)
- **Date:** v1 2026-09-14, revised 2026-09-18
- **Retrieved:** 2026-09-26; no code link captured
- **Cited by evidence:** https://x.com/rohanpaul_ai/status/2103499768031015283 (@rohanpaul_ai)
- **Relevance to a memory stack:** medium. A training-free loop that explores a new environment, verifies outcomes and stores environment-specific knowledge as a frozen memory reused at task time; the "RSI" label is marketing for an exploration-to-memory write path (inference).

## TL;DR
- Three agents (curriculum, actor, verifier) explore an unfamiliar environment "broad-then-deep" and retain "environment-specific knowledge" as reusable procedures and causal relationships; memory is then frozen and reused, no weight updates.
- OSWorld 2.0 (82 tasks, partial score): Kimi-K3 58.30 -> RSIAgent without RSI 71.97 -> full **78.98**; GPT-6 Astra 72.60; Claude Opus 5 70.19.
- Agents' Last Exam (67 tasks, binary): Kimi-K3 40.30 -> without RSI 49.25 -> full **50.75**; GPT-6 Astra **52.24**; Claude Opus 5 46.27.
- Ablation on only 4 OSWorld tasks: full 74.54 vs broad-only 65.52 vs deep-only 56.50.
- No leakage analysis between explored environment and test tasks; exploration cost not quantified.
- **Claim correction:** see frontmatter; the RSI stage itself adds 7.01 (OSWorld partial) and 1.07 (ALE binary) points.

## What it claims / describes
- **Broad-then-deep exploration:** parallel broad discovery (8 nominal projects mentioned for the broad stage), then sequential deep investigation of edge cases.
- **Verifier** validates outcomes before knowledge is retained (a gated write).
- **Frozen memory:** stored knowledge is reused downstream without further updates. Storage format and retrieval mechanism are not detailed in the fetched text.

## Numbers
| metric | value | baseline | setup (n) | caveat |
|---|---|---|---|---|
| OSWorld 2.0 partial score | 78.98 | Kimi-K3 58.30; w/o RSI 71.97; GPT-6 Astra 72.60; Opus 5 70.19 | 82 tasks (0808 offline) | Table 1 |
| OSWorld binary accuracy | 42.68 | w/o RSI 37.80; Opus 5 34.72 | 82 | Astra binary not reported |
| ALE partial score | 84.82 | Kimi-K3 71.60; w/o RSI 83.75; Astra 82.26; Opus 5 79.54 | 67 tasks (near-term) | |
| ALE binary accuracy | 50.75 | Kimi-K3 40.30; w/o RSI 49.25; Astra 52.24; Opus 5 46.27 | 67 | Astra higher |
| ablation, mean score | full 74.54; broad-only 65.52; deep-only 56.50 | | 4 OSWorld tasks | tiny n |
| exploration cost | not quantified | | | |

With n = 67, one task is 1.49 points of binary accuracy, so the 1.07 RSI-stage gain on ALE is below one task's difference (inference: 50.75 - 49.25 = 1.50 is one task).

## Mechanism details you could implement
- Before first real work in a new environment (repo), run a bounded exploration phase with a verifier that only stores knowledge it confirmed; freeze it for the task phase.
- Separate breadth (parallel discovery) from depth (edge cases) in the exploration budget.

## Limitations, caveats, counter-evidence
- No comparison with other memory or self-evolving methods (e.g. skill induction such as N-20260926-01).
- No analysis of overlap between explored states and test tasks (possible leakage).
- Small benchmarks, single runs, partial scores emphasised.
- Wrong-memory reinforcement rate not reported (B17).

## Takeaways for tuning a memory stack
- An "explore then freeze" onboarding memory for a new repository is a plausible arm, but this paper does not isolate its value well: most of the lift is the framework, not the retained knowledge.
- If we test it, include a leakage control (explored environment must not contain test answers).

## Open questions
- What does the retained memory look like and how large is it? Not detailed.
- Exploration token cost vs gain? Not quantified.

## Grading and labels
- Directness medium; control low; independence medium; reproducibility low; applicability medium.
- Pillar R5 (self-improvement via retained experience; L2-L3 on the RSI ladder at most, fixed evaluator). Secondary R6 (evaluation claims narrowed).
- Beliefs: supports B17 (no feedback-loop or wrong-memory rate reported). Claim correction on "outperform GPT-6".
- Contradiction rows: none.

## Origin chain
post 2103499768031015283 (@rohanpaul_ai) -> arXiv 2609.15364 (HTML) -> Table 1, ablation section, method description -> this note. Independence: no shared authors with other notes.
