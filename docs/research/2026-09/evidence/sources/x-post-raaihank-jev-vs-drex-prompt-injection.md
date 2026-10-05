---
schema_version: 1
artifact_id: N-20261004-02
artifact_type: note
producer: triage
run_id: triage-20261004T014502Z-25fb
created_at: 2026-10-04T01:52:17Z
input_refs: [{"artifact_id": "post:2103850658118140131", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x:2103850658118140131
claim_cluster: x:2103850658118140131
feeds: ["decision"]
primary_source: https://x.com/raaihank/status/2103850658118140131
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R8", "R4"]
memory_stage: safety
priority: 1
tags: {"mechanism": ["prompt-injection-classifier", "threshold-tuning", "system-one-decision-model"], "workload": ["injection-detection"], "lifecycle_stage": ["safety"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: first-hand counts in the post, dataset and per-sample results not published", "control": "medium: 1,000 identical samples for both models, threshold sweep reported, but Drex needed retries on 328 rate-limited calls", "independence": "high: builder unaffiliated with TypeSafe or NaceAI (inference from profile)", "reproducibility": "low: dataset source and prompts not stated", "applicability": "medium: an injection gate is the R8 safety stage we plan for served memory, but the samples are generic prompts, not memory lines"}
beliefs_affected: {"supports": ["B24", "B14"], "contradicts": [], "would_create": ["On a 1,000-sample generic prompt-injection set, Jev catches more attacks than Drex (373 vs 271 of 408) at the price of more false alarms (97 vs 53 of 592); the right threshold is workload-specific"]}
claim_correction: none (counts recompute to Jev 86.8%; Drex recomputes to 81.0% vs the stated 81.1%, a 0.1 point gap not explained in the post)
---

# Jev vs Drex as a prompt-injection detector on 1,000 samples (Raihan Kabir, TypeSafe Jev vs NaceAI Drex)

- **URL:** https://x.com/raaihank/status/2103850658118140131
- **Type:** X post (builder benchmark; numbers in post text, video attached)
- **Author / org:** Raihan Kabir (@raaihank), builder of humanpanel.ai
- **Date:** 2026-09-26
- **Retrieved:** 2026-10-04 via the fxtwitter mirror API (full post text); attached video not viewed; version n/a
- **Cited by evidence:** @raaihank 2103850658118140131
- **Relevance to a memory stack:** medium, an independent head-to-head of two decision models as an injection gate, the gate type B24 proposes for served memory

## TL;DR
- 1,000 identical samples (408 attacks, 592 benign): accuracy Jev 86.8% vs Drex 81.1% (post).
- Jev catches more attacks (373 vs 271) and raises more false alarms (97 vs 53) (post). Recomputed: recall 91.4% vs 66.4%, false-positive rate 16.4% vs 9.0%.
- With tuned thresholds: Drex 83.4% at 0.43, Jev 87.9% at its best cutoff; AUC 0.95 vs 0.90 (post).
- Latency median 385 ms vs 421 ms; cost per 1K $0.02 vs $0.008 (post).
- Failure modes differ: Drex misses role-play attacks; Jev over-flags some creative writing (post).

## What it claims / describes
The builder sent the same 1,000 samples to Jev-latest and Drex-latest, reading each model's probability that a sample is an attack, and reported accuracy at the default cutoff, the best cutoff, AUC, latency and cost. Verbatim: "Bottom line: Jev favors attack detection; Drex favors lower false alarms and cost. Caveat: Drex rate-limited 328 calls, requiring retries."

Not stated: the dataset source (public set or self-built), the question phrasing sent to each model, Jev's best cutoff value, how many seeds or repeats, whether retried Drex calls were identical requests.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Accuracy (default cutoff) | Jev "86.8%" | Drex "81.1%" | 1,000 samples, 408 attacks / 592 benign | Drex recomputes to 81.0% from the counts |
| Attacks caught | "373" | "271" | of 408 attacks | recall 91.4% vs 66.4% (computed) |
| False alarms | "97" | "53" | of 592 benign | FPR 16.4% vs 9.0% (computed) |
| Accuracy at tuned cutoff | Jev "87.9% at its best cutoff" | Drex "83.4% accuracy at a 0.43 threshold" | same set | cutoff chosen on the test set itself (inference: optimistic) |
| AUC | "0.95" | "0.90" | same set | no interval |
| Median latency | "385ms" | "421ms" | API calls | Drex had 328 rate-limited calls |
| Cost per 1K | "$0.02" | "$0.008" | API pricing | |

## Mechanism details you could implement
- Ask the decision model a yes/no "is this an attack" question and read the probability, then pick the cutoff per workload; the post shows a 2.3 point gain for Drex from moving the cutoff to 0.43.
- Run two gates with different failure modes (one misses role-play, one over-flags creative writing) as a union or with disagreement escalation (inference).
- Report recall and false-alarm rate separately: accuracy hides that Jev blocks 1 in 6 benign items at default settings.

## Limitations, caveats, counter-evidence
- The best cutoffs were picked on the evaluation set (inference: optimistic for both).
- Dataset provenance unknown; generic prompts, not memory lines or tool outputs.
- 16.4% false-positive rate would be costly on served memory where a block removes evidence (B11 logic, inference).
- Compare the jevmem gate in B24: 20/22 blocked, 0/22 false blocks on a tiny author set; this larger set shows a much higher false-alarm rate for Jev at default.
- Bus note github-jooray-hermes-firewall.md covers another Jev injection gate; this is an independent second data point.

## Takeaways for tuning a memory stack
- An injection gate on memory must be tuned for false blocks, not accuracy; plan a cutoff sweep on our own memory lines.
- Expect a default Jev gate to over-block creative or narrative text; engineering artifacts with quoted prompts may trigger it (inference).

## Open questions
- What is Jev's false-block rate on engineering memory (design docs, tickets, code comments that quote prompts)?
- Does an ensemble of Jev and a cheaper gate beat either alone at a fixed false-block budget?

## Grading and labels
- Directness: medium. Control: medium. Independence: high. Reproducibility: low. Applicability: medium (reasons in frontmatter).
- Pillars: R9 primary, R8 and R4 secondary. Stage: safety. Priority 1. Products: Jev (TypeSafe), Drex (NaceAI).
- Beliefs: supports B24 (decision-model gate on injection is workable) while showing a false-alarm rate B24's tiny set did not; supports B14 (fit thresholds locally: both models gain from a tuned cutoff).
- Contradiction rows: none (B24's 0/22 false blocks is on a different set; not a contradiction, a caution).

## Origin chain
Post 2103850658118140131 (numbers in text) is the only source; no dataset or repo linked. Independence: one builder, one dataset, both vendors' public APIs.
